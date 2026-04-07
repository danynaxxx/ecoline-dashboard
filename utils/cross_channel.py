"""
Cross-channel analytics — Ecoline ↔ Affiliate overlap & attribution.
All heavy queries run against BigQuery, cached 1 hour.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
from utils.bq_client import run_query


# ─────────────────────────────────────────────
#  1. LOAD BOTH SIDES (leads + statuses)
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Loading cross-channel data…")
def load_cross_channel(start: date, end: date) -> pd.DataFrame:
    """
    Load leads from BOTH projects, tag each row with channel='eco' or 'aff',
    normalise phone/email for matching.  Returns one combined DataFrame.
    """
    eco_sql = f"""
    SELECT
        l.row_num,
        l.dt,
        l.phone,
        l.email,
        l.name,
        l.postal_code,
        l.utm_source,
        l.utm_campaign,
        ls.status_with_cancelled  AS status,
        ls.cf_booked_date,
        ls.cf_appointment_date,
        ls.cf_sold_date,
        ls.cf_cancelled_date,
        ls.cf_amount              AS amount,
        COALESCE(p.province, 'Unknown')           AS province,
        COALESCE(ccm.city, c.city, 'Unknown city') AS city,
        'eco' AS channel
    FROM `ecolinew.raw.leads` l
    LEFT JOIN `ecolinew.raw.leads_status` ls  ON l.row_num = ls.row_num
    LEFT JOIN `ecolinew.raw.city_map`     c   ON UPPER(SUBSTR(REGEXP_REPLACE(l.postal_code, r'\\s', ''), 1, 3)) = c.fsa_postal_code
    LEFT JOIN `ecolinew.raw.call_city_map` ccm ON LOWER(c.city) = ccm.cust_city_key
    LEFT JOIN `ecolinew.raw.province_map` p   ON UPPER(SUBSTR(REGEXP_REPLACE(l.postal_code, r'\\s', ''), 1, 1)) = p.postal_district
    WHERE DATE(l.dt) BETWEEN '{start}' AND '{end}'
      AND (
          REGEXP_CONTAINS(REGEXP_REPLACE(COALESCE(l.phone, ''), r'[^0-9]', ''), r'^[2-9][0-9]{{9}}$')
          OR (l.email IS NOT NULL AND l.email LIKE '%@%.%')
          OR ls.cf_appointment_date IS NOT NULL
      )
    """

    aff_sql = f"""
    SELECT
        lws.lead_row_num          AS row_num,
        lws.dt,
        lws.phone,
        lws.email,
        lws.name,
        lws.postal_code,
        lws.utm_source,
        lws.utm_campaign,
        lws.status_with_cancelled AS status,
        lws.cf_booked_date,
        lws.cf_appointment_date,
        lws.cf_sold_date,
        lws.cf_cancelled_date,
        lws.cf_amount             AS amount,
        COALESCE(lws.province, 'Unknown')   AS province,
        COALESCE(lws.city, 'Unknown city')  AS city,
        'aff' AS channel
    FROM `eco-affiliate.raw.leads_with_status` lws
    WHERE DATE(lws.dt) BETWEEN '{start}' AND '{end}'
      AND (
          REGEXP_CONTAINS(REGEXP_REPLACE(COALESCE(lws.phone, ''), r'[^0-9]', ''), r'^[2-9][0-9]{{9}}$')
          OR (lws.email IS NOT NULL AND lws.email LIKE '%@%.%')
          OR lws.cf_appointment_date IS NOT NULL
      )
    """

    eco = run_query(eco_sql, "ecolinew")
    aff = run_query(aff_sql, "eco-affiliate")

    df = pd.concat([eco, aff], ignore_index=True)
    if df.empty:
        return df

    df["dt"] = pd.to_datetime(df["dt"], utc=True)
    df["date"] = df["dt"].dt.date
    df["phone_clean"] = df["phone"].str.replace(r"[^0-9]", "", regex=True)
    df["email_clean"] = df["email"].str.strip().str.lower()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(float)

    return df


# ─────────────────────────────────────────────
#  2. OVERLAP SEGMENTATION
# ─────────────────────────────────────────────

def compute_overlap(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each unique lead (by phone_clean), determine segment:
      eco_only  — appeared only in eco
      aff_only  — appeared only in aff
      overlap   — appeared in both
    Returns per-lead summary with first touch dates, segment, funnel status.
    """
    if df.empty:
        return pd.DataFrame()

    # Pre-compute first touch per channel
    eco_first = (df[df["channel"] == "eco"]
                 .groupby("phone_clean")["dt"].min()
                 .rename("first_eco_dt"))
    aff_first = (df[df["channel"] == "aff"]
                 .groupby("phone_clean")["dt"].min()
                 .rename("first_aff_dt"))

    # Basic aggregation
    leads = df.groupby("phone_clean").agg(
        channels     = ("channel", lambda x: set(x)),
        has_appt     = ("cf_appointment_date", lambda x: x.notna().any()),
        is_sold      = ("status", lambda x: (x.str.lower() == "sold").any()),
        total_amount = ("amount", "sum"),
        province     = ("province", "first"),
        city         = ("city", "first"),
        n_touches    = ("row_num", "count"),
    ).reset_index()

    # Merge first-touch dates
    leads = leads.merge(eco_first, on="phone_clean", how="left")
    leads = leads.merge(aff_first, on="phone_clean", how="left")

    leads["segment"] = leads["channels"].apply(
        lambda c: "overlap" if len(c) > 1 else ("eco_only" if "eco" in c else "aff_only")
    )

    # Who came first for overlap leads
    leads["who_first"] = None
    mask_overlap = leads["segment"] == "overlap"
    leads.loc[mask_overlap, "who_first"] = leads.loc[mask_overlap].apply(
        lambda r: "eco" if r["first_eco_dt"] < r["first_aff_dt"]
                  else ("aff" if r["first_aff_dt"] < r["first_eco_dt"] else "same_day"),
        axis=1,
    )

    # Days between first touches
    leads["days_between"] = None
    leads.loc[mask_overlap, "days_between"] = leads.loc[mask_overlap].apply(
        lambda r: abs((r["first_aff_dt"] - r["first_eco_dt"]).days), axis=1
    )

    return leads


# ─────────────────────────────────────────────
#  3. LINEAR ATTRIBUTION
# ─────────────────────────────────────────────

def linear_attribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Linear attribution: each touchpoint gets equal credit.
    For a sold lead with 3 eco touches + 2 aff touches:
      eco gets 3/5 credit, aff gets 2/5 credit.
    Returns per-channel summary: attributed_leads, attributed_appts,
    attributed_sold, attributed_revenue.
    """
    if df.empty:
        return pd.DataFrame()

    # Count touches per lead per channel
    touches = df.groupby(["phone_clean", "channel"]).agg(
        n_touches = ("row_num", "count"),
    ).reset_index()

    # Total touches per lead
    total_touches = touches.groupby("phone_clean")["n_touches"].sum().rename("total_touches")
    touches = touches.merge(total_touches, on="phone_clean")
    touches["weight"] = touches["n_touches"] / touches["total_touches"]

    # Lead-level outcomes
    outcomes = df.groupby("phone_clean").agg(
        has_appt = ("cf_appointment_date", lambda x: x.notna().any()),
        is_sold  = ("status", lambda x: (x.str.lower() == "sold").any()),
        revenue  = ("amount", "sum"),
    ).reset_index()

    merged = touches.merge(outcomes, on="phone_clean")

    # Attributed values
    merged["weight"] = merged["weight"].astype(float)
    merged["attr_lead"] = merged["weight"]
    merged["attr_appt"] = merged["weight"] * merged["has_appt"].astype(float)
    merged["attr_sold"] = merged["weight"] * merged["is_sold"].astype(float)
    merged["attr_revenue"] = merged["weight"] * merged["revenue"].astype(float)

    result = merged.groupby("channel").agg(
        attributed_leads   = ("attr_lead", "sum"),
        attributed_appts   = ("attr_appt", "sum"),
        attributed_sold    = ("attr_sold", "sum"),
        attributed_revenue = ("attr_revenue", "sum"),
        total_touches      = ("n_touches", "sum"),
    ).reset_index()

    return result


# ─────────────────────────────────────────────
#  4. FIRST-TOUCH & LAST-TOUCH ATTRIBUTION
# ─────────────────────────────────────────────

def touch_attribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    First-touch and last-touch attribution models.
    Returns DataFrame with channel, model, attributed_sold, attributed_revenue.
    """
    if df.empty:
        return pd.DataFrame()

    # For each lead: first touch channel, last touch channel
    lead_touches = df.sort_values("dt").groupby("phone_clean").agg(
        first_channel = ("channel", "first"),
        last_channel  = ("channel", "last"),
        is_sold       = ("status", lambda x: (x.str.lower() == "sold").any()),
        revenue       = ("amount", "sum"),
    ).reset_index()

    # Revenue only counts for sold leads
    lead_touches["sold_revenue"] = lead_touches["revenue"] * lead_touches["is_sold"].astype(float)

    results = []
    for model, col in [("first_touch", "first_channel"), ("last_touch", "last_channel")]:
        grp = lead_touches.groupby(col).agg(
            attributed_sold    = ("is_sold", "sum"),
            attributed_revenue = ("sold_revenue", "sum"),
            total_leads        = ("phone_clean", "count"),
        ).reset_index().rename(columns={col: "channel"})
        grp["model"] = model
        results.append(grp)

    return pd.concat(results, ignore_index=True)


# ─────────────────────────────────────────────
#  5. CONVERSION BY TOUCHPOINT WINDOW
# ─────────────────────────────────────────────

def conversion_by_gap(overlap_df: pd.DataFrame) -> pd.DataFrame:
    """
    For overlap leads, group by days_between bucket and compute conversion rates.
    """
    if overlap_df.empty:
        return pd.DataFrame()

    ov = overlap_df[overlap_df["segment"] == "overlap"].copy()
    if ov.empty:
        return pd.DataFrame()

    ov["days_between"] = pd.to_numeric(ov["days_between"], errors="coerce")

    bins   = [0, 7, 14, 30, 60, 90, 180, 365, 9999]
    labels = ["0–7d", "8–14d", "15–30d", "31–60d", "61–90d", "91–180d", "181–365d", "365d+"]
    ov["gap_bucket"] = pd.cut(ov["days_between"], bins=bins, labels=labels, right=True)

    result = ov.groupby("gap_bucket", observed=True).agg(
        leads       = ("phone_clean", "count"),
        appts       = ("has_appt", "sum"),
        sold        = ("is_sold", "sum"),
        avg_revenue = ("total_amount", "mean"),
    ).reset_index()

    result["cr_appt"] = (result["appts"] / result["leads"] * 100).round(1)
    result["cr_sold"] = (result["sold"] / result["leads"] * 100).round(1)

    return result


# ─────────────────────────────────────────────
#  6. GEO OVERLAP
# ─────────────────────────────────────────────

def geo_overlap(overlap_df: pd.DataFrame, level: str = "province") -> pd.DataFrame:
    """
    Overlap analysis by geography.
    level: 'province' or 'city'
    """
    if overlap_df.empty:
        return pd.DataFrame()

    result = overlap_df.groupby(level).agg(
        total_leads   = ("phone_clean", "count"),
        eco_only      = ("segment", lambda x: (x == "eco_only").sum()),
        aff_only      = ("segment", lambda x: (x == "aff_only").sum()),
        overlap       = ("segment", lambda x: (x == "overlap").sum()),
        appts         = ("has_appt", "sum"),
        sold          = ("is_sold", "sum"),
        revenue       = ("total_amount", "sum"),
    ).reset_index()

    result["overlap_pct"] = (result["overlap"] / result["total_leads"] * 100).round(1)
    result["cr_appt"]     = (result["appts"] / result["total_leads"] * 100).round(1)
    result["cr_sold"]     = (result["sold"] / result["total_leads"] * 100).round(1)
    result = result.sort_values("total_leads", ascending=False)

    return result


# ─────────────────────────────────────────────
#  7. MONTHLY OVERLAP TREND
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Loading overlap trend…")
def load_monthly_overlap_trend() -> pd.DataFrame:
    """
    Monthly new overlaps (phone appears in both projects).
    Uses full history from 2024-01-01.
    """
    sql = """
    WITH eco AS (
      SELECT LOWER(TRIM(phone)) as phone,
             FORMAT_TIMESTAMP('%%Y-%%m', MIN(dt)) as first_month
      FROM `ecolinew.raw.leads_status`
      WHERE dt >= '2024-01-01' AND phone IS NOT NULL AND TRIM(phone) != ''
      GROUP BY 1
    ),
    aff AS (
      SELECT LOWER(TRIM(phone)) as phone,
             FORMAT_TIMESTAMP('%%Y-%%m', MIN(dt)) as first_month
      FROM `eco-affiliate.raw.leads_with_status`
      WHERE dt >= '2024-01-01' AND phone IS NOT NULL AND TRIM(phone) != ''
      GROUP BY 1
    )
    SELECT
      FORMAT_TIMESTAMP('%%Y-%%m', GREATEST(PARSE_TIMESTAMP('%%Y-%%m', e.first_month),
                                            PARSE_TIMESTAMP('%%Y-%%m', a.first_month))) as month,
      COUNT(*) as new_overlaps
    FROM eco e
    JOIN aff a ON e.phone = a.phone
    GROUP BY 1
    ORDER BY 1
    """
    return run_query(sql, "ecolinew")


# ─────────────────────────────────────────────
#  8. CANNIBALIZATION vs SYNERGY
# ─────────────────────────────────────────────

def cannibalization_analysis(overlap_df: pd.DataFrame) -> dict:
    """
    Compare conversion rates:
      - eco_only vs overlap (eco side)
      - aff_only vs overlap (aff side)
    If overlap CR > single-channel CR → synergy
    If overlap CR < single-channel CR → cannibalization
    """
    if overlap_df.empty:
        return {}

    segments = {}
    for seg in ["eco_only", "aff_only", "overlap"]:
        s = overlap_df[overlap_df["segment"] == seg]
        n = len(s)
        if n == 0:
            segments[seg] = {"leads": 0, "cr_appt": 0, "cr_sold": 0, "avg_touches": 0}
            continue
        segments[seg] = {
            "leads":      n,
            "cr_appt":    round(s["has_appt"].sum() / n * 100, 1),
            "cr_sold":    round(s["is_sold"].sum() / n * 100, 1),
            "avg_touches": round(s["n_touches"].mean(), 1),
            "total_revenue": s["total_amount"].sum(),
        }

    # Synergy score: how much better overlap converts vs weighted avg of single channels
    eco_cr = segments["eco_only"]["cr_appt"]
    aff_cr = segments["aff_only"]["cr_appt"]
    ovl_cr = segments["overlap"]["cr_appt"]
    weighted_single = (eco_cr + aff_cr) / 2 if (eco_cr + aff_cr) > 0 else 0
    synergy_lift = round(ovl_cr - weighted_single, 1) if weighted_single > 0 else 0

    return {
        "segments": segments,
        "synergy_lift_appt": synergy_lift,
        "verdict": "synergy" if synergy_lift > 0 else "cannibalization" if synergy_lift < 0 else "neutral",
    }
