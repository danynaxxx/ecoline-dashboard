import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from datetime import date, timedelta
from utils.bq_client import run_query

# ─────────────────────────────────────────────
#  ML MODEL  (lead-level close probability)
# ─────────────────────────────────────────────

def _load_ml_model():
    """Load logistic regression weights from ml_model.json."""
    path = os.path.join(os.path.dirname(__file__), "ml_model.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

_ML_MODEL = _load_ml_model()


def _sigmoid(z):
    return 1 / (1 + np.exp(-np.clip(z, -500, 500)))


def _bucket_days(d):
    if d <= 7:  return [1,0,0,0,0]
    if d <= 14: return [0,1,0,0,0]
    if d <= 21: return [0,0,1,0,0]
    if d <= 30: return [0,0,0,1,0]
    return             [0,0,0,0,1]


def _get_camp_type(utm_campaign, utm_medium):
    """Classify a lead's campaign type: LG, CONV, DIRECT, or OTHER."""
    camp = str(utm_campaign or "").upper()
    med  = str(utm_medium  or "").upper()
    if " LG " in camp or "-LG-" in camp or "LEAD" in camp or med == "LG":
        return "LG"
    if " CONV " in camp or "-CONV-" in camp or "CONVER" in camp or med == "CPC":
        return "CONV"
    if not utm_campaign and not utm_medium:
        return "DIRECT"
    return "OTHER"


def predict_upcoming_sales(upcoming_df: pd.DataFrame) -> dict:
    """
    Score each upcoming appointment individually using the trained logistic
    regression model and return the sum of probabilities as the predicted
    number of sales.

    Features: province, camp_type (LG/CONV/DIRECT/OTHER), city (top 22 + OTHER_CITY),
              days_booked_to_appt (bucketed), lead_month (sin/cos),
              days_lead_to_booked.

    Returns dict with keys: predicted, mean_prob, n_scored, model_version.
    Falls back to None if model is unavailable or df is empty.
    """
    if _ML_MODEL is None or upcoming_df.empty:
        return None

    m        = _ML_MODEL
    w        = np.array(m["weights"])
    b        = float(m["bias"])
    prov_idx = {v: i for i, v in enumerate(m["provinces"])}
    camp_idx = {v: i for i, v in enumerate(m["camp_types"])}
    city_idx = {v: i for i, v in enumerate(m.get("cities", []))}

    def encode_row(row):
        # Province
        prov_oh  = [0] * len(m["provinces"])
        prov_key = row.get("province", "Unknown")
        if prov_key in prov_idx:
            prov_oh[prov_idx[prov_key]] = 1
        elif "Unknown" in prov_idx:
            prov_oh[prov_idx["Unknown"]] = 1

        # Campaign type: LG / CONV / DIRECT / OTHER
        ct      = _get_camp_type(row.get("utm_campaign"), row.get("utm_medium"))
        camp_oh = [0] * len(m["camp_types"])
        if ct in camp_idx:
            camp_oh[camp_idx[ct]] = 1

        # City (top N + OTHER_CITY bucket)
        city_oh = [0] * len(city_idx)
        if city_idx:
            city_key = row.get("city", "Unknown city")
            if city_key not in city_idx:
                city_key = "OTHER_CITY"
            if city_key in city_idx:
                city_oh[city_idx[city_key]] = 1

        # Days booked → appointment
        booked_dt        = pd.to_datetime(row.get("cf_booked_date"))
        appt_dt          = pd.to_datetime(row.get("cf_appointment_date"))
        d_booked_to_appt = int((appt_dt - booked_dt).days) if pd.notna(booked_dt) and pd.notna(appt_dt) else 14

        # Days lead → booked
        lead_dt          = pd.to_datetime(row.get("dt"))
        d_lead_to_booked = int((booked_dt - lead_dt).days) if pd.notna(booked_dt) and pd.notna(lead_dt) else 3
        d_lead_to_booked = min(d_lead_to_booked, 30) / 30

        # Lead month
        lead_month = pd.to_datetime(row.get("dt")).month if pd.notna(row.get("dt")) else 6

        return prov_oh + camp_oh + city_oh + _bucket_days(d_booked_to_appt) + [
            np.sin(2 * np.pi * lead_month / 12),
            np.cos(2 * np.pi * lead_month / 12),
            d_lead_to_booked,
        ]

    features = []
    for _, row in upcoming_df.iterrows():
        try:
            features.append(encode_row(row))
        except Exception:
            features.append([0] * len(w))

    X     = np.array(features)
    probs = _sigmoid(X @ w + b)

    return {
        "predicted":     int(round(probs.sum())),
        "mean_prob":     round(float(probs.mean() * 100), 1),
        "n_scored":      len(probs),
        "model_version": m.get("version", "unknown"),
    }

# ─────────────────────────────────────────────
#  RAW DATA LOADERS  (cached 1 hour)
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Loading leads…")
def load_leads(start: date, end: date, project_id: str = "ecolinew") -> pd.DataFrame:
    # eco-affiliate: leads_with_status has lead_row_num (not row_num),
    # province & city already embedded — no JOINs needed
    if project_id == "eco-affiliate":
        sql = f"""
        SELECT
            lws.lead_row_num                    AS row_num,
            lws.dt,
            lws.phone,
            lws.email,
            lws.name,
            lws.postal_code,
            lws.utm_source,
            lws.utm_medium,
            lws.utm_campaign,
            lws.utm_content,
            lws.utm_term,
            lws.status_with_cancelled           AS status,
            lws.cf_booked_date,
            lws.cf_appointment_date,
            lws.cf_sold_date,
            lws.cf_cancelled_date,
            lws.cf_amount                       AS amount,
            COALESCE(lws.province, 'Unknown')   AS province,
            COALESCE(lws.city, 'Unknown city')  AS city
        FROM `eco-affiliate.raw.leads_with_status` lws
        WHERE DATE(lws.dt) BETWEEN '{start}' AND '{end}'
          AND (
              REGEXP_CONTAINS(REGEXP_REPLACE(COALESCE(lws.phone, ''), r'[^0-9]', ''), r'^[2-9][0-9]{{9}}$')
              OR (lws.email IS NOT NULL AND lws.email LIKE '%@%.%')
              OR lws.cf_appointment_date IS NOT NULL
              OR lws.cf_cancelled_date   IS NOT NULL
          )
        ORDER BY lws.dt
        """
    else:
        sql = f"""
        SELECT
            l.row_num,
            l.dt,
            l.phone,
            l.email,
            l.name,
            l.postal_code,
            l.utm_source,
            l.utm_medium,
            l.utm_campaign,
            l.utm_content,
            l.utm_term,
            ls.status_with_cancelled          AS status,
            ls.cf_booked_date,
            ls.cf_appointment_date,
            ls.cf_sold_date,
            ls.cf_cancelled_date,
            ls.cf_amount                       AS amount,
            COALESCE(p.province, 'Unknown')    AS province,
            COALESCE(ccm.city, c.city, 'Unknown city') AS city
        FROM `{project_id}.raw.leads` l
        LEFT JOIN `{project_id}.raw.leads_status` ls ON l.row_num = ls.row_num
        LEFT JOIN `{project_id}.raw.city_map`     c
            ON UPPER(SUBSTR(REGEXP_REPLACE(l.postal_code, r'\\s', ''), 1, 3)) = c.fsa_postal_code
        LEFT JOIN `{project_id}.raw.call_city_map` ccm
            ON LOWER(c.city) = ccm.cust_city_key
        LEFT JOIN `{project_id}.raw.province_map` p
            ON UPPER(SUBSTR(REGEXP_REPLACE(l.postal_code, r'\\s', ''), 1, 1)) = p.postal_district
        WHERE DATE(l.dt) BETWEEN '{start}' AND '{end}'
          AND (
              REGEXP_CONTAINS(REGEXP_REPLACE(COALESCE(l.phone, ''), r'[^0-9]', ''), r'^[2-9][0-9]{{9}}$')
              OR (l.email IS NOT NULL AND l.email LIKE '%@%.%')
              OR ls.cf_appointment_date IS NOT NULL
              OR ls.cf_cancelled_date   IS NOT NULL
          )
        ORDER BY l.dt
        """
    df = run_query(sql, project_id)
    df["dt"] = pd.to_datetime(df["dt"], utc=True)
    df["date"] = df["dt"].dt.date
    df["phone_clean"] = df["phone"].str.replace(r"[^0-9]", "", regex=True)
    df["source_type"] = "lead"

    # Classify campaign type from utm_campaign
    # Campaign names use " - LG - " (spaces around dashes), e.g.
    # "ACC7 - ALL REGIONS - LG - DCO - Spring installation"
    # "ACC4 - ALL REGIONS - CONV - Cost Cap 3 - TEST 2"
    def _camp_type(val):
        if pd.isna(val):
            return "Unknown"
        v = str(val).upper()
        if " LG " in v or "-LG-" in v or "LEAD" in v:
            return "LG"
        if " CONV " in v or "-CONV-" in v or "CONVER" in v:
            return "CONV"
        return "Other"

    df["campaign_type"] = df["utm_campaign"].apply(_camp_type)

    # Source label
    def _source(val):
        if pd.isna(val):
            return "Other"
        v = str(val).lower()
        if v in ("facebook", "fb"):
            return "META"
        if v == "tiktok":
            return "TikTok"
        if v == "activecampaign":
            return "Other"
        return "Other"

    df["source"] = df["utm_source"].apply(_source)
    return df



@st.cache_data(ttl=3600, show_spinner="Loading calls…")
def load_calls(start: date, end: date, project_id: str = "ecolinew") -> pd.DataFrame:
    # alias differs: ecolinew uses 'c', affiliate uses 'cws'
    _alias = "cws" if project_id == "eco-affiliate" else "c"
    province_case = f"""
        CASE TRIM(REGEXP_EXTRACT(TRIM({_alias}.name), r'\\b([A-Z]{{{{2}}}})\\s*$'))
            WHEN 'AB' THEN 'Alberta'
            WHEN 'BC' THEN 'British Columbia'
            WHEN 'MB' THEN 'Manitoba'
            WHEN 'NB' THEN 'New Brunswick'
            WHEN 'NL' THEN 'Newfoundland and Labrador'
            WHEN 'NS' THEN 'Nova Scotia'
            WHEN 'ON' THEN 'Ontario'
            WHEN 'PE' THEN 'Prince Edward Island'
            WHEN 'QC' THEN 'Quebec'
            WHEN 'SK' THEN 'Saskatchewan'
            WHEN 'YT' THEN 'Yukon'
            WHEN 'NT' THEN 'Northwest Territories'
            WHEN 'NU' THEN 'Nunavut'
            ELSE 'Unknown'
        END
    """
    # eco-affiliate: calls_with_status has status already embedded
    # calls_row_num matches ecolinew naming; need city_map JOIN for province
    if project_id == "eco-affiliate":
        sql = f"""
        SELECT
            cws.calls_row_num                           AS row_num,
            cws.dt,
            cws.phone,
            cws.email,
            cws.name,
            cws.source_name,
            cws.tracking_number,
            COALESCE(ccm.city, cws.cust_city)           AS city,
            {province_case}                             AS province,
            cws.first_call,
            cws.status_with_cancelled                   AS status,
            cws.cf_booked_date,
            cws.cf_appointment_date,
            cws.cf_sold_date,
            cws.cf_cancelled_date,
            cws.cf_amount                               AS amount
        FROM `eco-affiliate.raw.calls_with_status` cws
        LEFT JOIN `eco-affiliate.raw.call_city_map` ccm
            ON LOWER(TRIM(cws.cust_city)) = ccm.cust_city_key
        WHERE DATE(cws.dt) BETWEEN '{start}' AND '{end}'
          AND cws.first_call = TRUE
        ORDER BY cws.dt
        """
    else:
        sql = f"""
        SELECT
            c.calls_row_num                      AS row_num,
            c.dt,
            c.phone,
            c.email,
            c.name,
            c.source_name,
            c.tracking_number,
            COALESCE(ccm.city, c.cust_city)      AS city,
            {province_case}                      AS province,
            c.first_call,
            cs.status_with_cancelled             AS status,
            cs.cf_booked_date,
            cs.cf_appointment_date,
            cs.cf_sold_date,
            cs.cf_cancelled_date,
            cs.cf_amount                         AS amount
        FROM `{project_id}.raw.calls` c
        LEFT JOIN `{project_id}.raw.calls_status` cs ON c.calls_row_num = cs.calls_row_num
        LEFT JOIN `{project_id}.raw.call_city_map` ccm ON LOWER(TRIM(c.cust_city)) = ccm.cust_city_key
        WHERE DATE(c.dt) BETWEEN '{start}' AND '{end}'
          AND c.first_call = 'TRUE'
        ORDER BY c.dt
        """
    df = run_query(sql, project_id)
    df["dt"] = pd.to_datetime(df["dt"], utc=True)
    df["date"] = df["dt"].dt.date
    df["phone_clean"] = df["phone"].str.replace(r"[^0-9]", "", regex=True)
    df["source_type"] = "call"
    df["campaign_type"] = "Call"

    # Map call tracking numbers to their parent ad source.
    # source_name from the calls table tells us which DNI number was dialled.
    # Add new entries here when affiliate (or other) tracking numbers go live.
    def _call_source(val):
        if pd.isna(val):
            return "META"               # unknown → default to META (all current traffic is Meta)
        v = str(val).lower()
        if "facebook" in v or "fb" in v:
            return "META"
        if "affiliate" in v or "activecampaign" in v:
            return "Other"
        if "tiktok" in v:
            return "TikTok"
        return "META"                   # safe default until other sources are confirmed

    df["source"] = df["source_name"].apply(_call_source)
    df["city"] = df["city"].fillna("Unknown city")
    # Calls are already filtered to first_call=TRUE in SQL, so all are clean by definition
    df["is_clean"] = True
    return df


@st.cache_data(ttl=3600, show_spinner="Loading prediction history…")
def load_prediction_history(project_id: str = "ecolinew") -> pd.DataFrame:
    """
    For each past month: how many appointments were 'upcoming' at month end
    (scheduled after the last day of that lead month) and what actually happened.
    Used to calibrate the upcoming→sold prediction rate.
    Only loads months at least 2 months ago so the data is settled.
    """
    # eco-affiliate: leads_with_status is pre-joined, use l.* for all fields
    src_table = ("`eco-affiliate.raw.leads_with_status` l"
                 if project_id == "eco-affiliate"
                 else "`{p}.raw.leads` l LEFT JOIN `{p}.raw.leads_status` ls ON l.row_num = ls.row_num".format(p=project_id))
    alias = "l" if project_id == "eco-affiliate" else "ls"
    sql = f"""
    SELECT
      FORMAT_DATE('%Y-%m', DATE(l.dt))   AS lead_month,
      LAST_DAY(DATE(l.dt), MONTH)        AS month_end,
      COUNTIF({alias}.cf_appointment_date > LAST_DAY(DATE(l.dt), MONTH))
          AS upcoming_at_month_end,
      COUNTIF({alias}.cf_appointment_date > LAST_DAY(DATE(l.dt), MONTH)
          AND {alias}.status_with_cancelled = 'sold')
          AS upcoming_became_sold,
      COUNTIF({alias}.cf_appointment_date > LAST_DAY(DATE(l.dt), MONTH)
          AND {alias}.status_with_cancelled = 'cancelled before appt')
          AS upcoming_canc_before,
      COUNTIF({alias}.cf_appointment_date > LAST_DAY(DATE(l.dt), MONTH)
          AND {alias}.status_with_cancelled = 'cancelled')
          AS upcoming_canc_after,
      COUNTIF({alias}.cf_appointment_date > LAST_DAY(DATE(l.dt), MONTH)
          AND {alias}.status_with_cancelled = 'appointment')
          AS upcoming_still_pending
    FROM {src_table}
    WHERE DATE(l.dt) BETWEEN
        DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH), MONTH)
      AND
        LAST_DAY(DATE_SUB(CURRENT_DATE(), INTERVAL 2 MONTH))
      AND (
        REGEXP_CONTAINS(REGEXP_REPLACE(COALESCE(l.phone,''), r'[^0-9]',''), r'^[2-9][0-9]{{9}}$')
        OR (l.email IS NOT NULL AND l.email LIKE '%@%.%')
        OR {alias}.cf_appointment_date IS NOT NULL
        OR {alias}.cf_cancelled_date   IS NOT NULL
      )
    GROUP BY 1, 2
    ORDER BY 1
    """
    df = run_query(sql, project_id)
    if df.empty:
        return df
    df["upcoming_at_month_end"]  = df["upcoming_at_month_end"].astype(int)
    df["upcoming_became_sold"]   = df["upcoming_became_sold"].astype(int)
    df["upcoming_canc_before"]   = df["upcoming_canc_before"].astype(int)
    df["upcoming_canc_after"]    = df["upcoming_canc_after"].astype(int)
    df["upcoming_still_pending"] = df["upcoming_still_pending"].astype(int)
    # Real conversion rate: upcoming → sold (only for settled months where pending < 10%)
    df["conv_rate"] = df.apply(
        lambda r: round(r["upcoming_became_sold"] / r["upcoming_at_month_end"] * 100, 1)
        if r["upcoming_at_month_end"] > 0 else 0,
        axis=1,
    )

    # Seasonal rate: average conv_rate per calendar month (for settled months only)
    df["calendar_month"] = pd.to_datetime(df["lead_month"]).dt.month
    settled = df[df["upcoming_still_pending"] < df["upcoming_at_month_end"] * 0.10]
    seasonal = (
        settled.groupby("calendar_month")["conv_rate"].mean().round(1).to_dict()
    )
    df["seasonal_rate"] = df["calendar_month"].map(seasonal)
    df["seasonal_rate"] = df["seasonal_rate"].fillna(df["conv_rate"].mean().round(1))

    return df


@st.cache_data(ttl=3600, show_spinner="Loading spend…")
def load_spend(start: date, end: date, project_id: str = "ecolinew") -> pd.DataFrame:
    # eco-affiliate: no real ad spend — calculate as leads × $70 CAD per province
    if project_id == "eco-affiliate":
        AFFILIATE_CPL_CAD = 70.0
        sql = f"""
        SELECT
            DATE(lws.dt)                        AS date,
            COALESCE(lws.province, 'Unknown')   AS province,
            COUNT(*)                            AS lead_count
        FROM `eco-affiliate.raw.leads_with_status` lws
        WHERE DATE(lws.dt) BETWEEN '{start}' AND '{end}'
          AND (
              REGEXP_CONTAINS(REGEXP_REPLACE(COALESCE(lws.phone,''), r'[^0-9]',''), r'^[2-9][0-9]{{9}}$')
              OR (lws.email IS NOT NULL AND lws.email LIKE '%@%.%')
              OR lws.cf_appointment_date IS NOT NULL
              OR lws.cf_cancelled_date   IS NOT NULL
          )
        GROUP BY 1, 2
        ORDER BY 1
        """
        df = run_query(sql, project_id)
        if df.empty:
            return pd.DataFrame(columns=["date", "province", "spend", "clicks"])
        df["date"]   = pd.to_datetime(df["date"]).dt.date
        df["spend"]  = df["lead_count"].astype(float) * AFFILIATE_CPL_CAD
        df["clicks"] = 0
        return df[["date", "province", "spend", "clicks"]]
    else:
        sql = f"""
        SELECT date, province, spend, clicks
        FROM `{project_id}.raw.spend_geo_snap`
        WHERE source = 'facebook'
          AND date BETWEEN '{start}' AND '{end}'
        """
    df = run_query(sql, project_id)
    if df.empty:
        return df
    df["spend"] = df["spend"].astype(float)
    df["clicks"] = df["clicks"].astype(float)
    return df


# ─────────────────────────────────────────────
#  META DIRECT SPEND CACHE  (no Windsor delay)
# ─────────────────────────────────────────────

_CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "meta_spend_cache.json")


def _load_meta_spend_cache() -> pd.DataFrame | None:
    """
    Load daily spend from meta_spend_cache.json (written by scheduled sync task).
    Returns DataFrame with columns [date, source, spend, clicks] or None if unavailable.
    """
    try:
        if not os.path.exists(_CACHE_PATH):
            return None
        with open(_CACHE_PATH) as f:
            cache = json.load(f)
        rows = cache.get("data", [])
        if not rows:
            return None
        df = pd.DataFrame(rows)
        df["date"]   = pd.to_datetime(df["date"]).dt.date
        df["spend"]  = df["spend"].astype(float)
        df["clicks"] = df["clicks"].astype(int)
        df["source"] = "facebook"
        return df[["date", "source", "spend", "clicks"]]
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner="Loading daily spend…")
def load_spend_daily(start: date, end: date, project_id: str = "ecolinew") -> pd.DataFrame:
    """
    Load daily spend.
    - For eco-affiliate: spend is calculated as clean leads × $70 CAD (fixed price per lead).
      No real ad spend is shared — affiliate sells leads at a fixed rate.
    - For ecolinew: prefers Meta direct cache, falls back to BigQuery Windsor data.
    """
    # ── AFFILIATE: spend = leads × $70 CAD ─────────────────────────────────
    if project_id == "eco-affiliate":
        AFFILIATE_CPL_CAD = 70.0
        sql = f"""
        SELECT
            DATE(lws.dt)  AS date,
            COUNT(*)      AS lead_count
        FROM `eco-affiliate.raw.leads_with_status` lws
        WHERE DATE(lws.dt) BETWEEN '{start}' AND '{end}'
          AND (
              REGEXP_CONTAINS(REGEXP_REPLACE(COALESCE(lws.phone,''), r'[^0-9]',''), r'^[2-9][0-9]{{9}}$')
              OR (lws.email IS NOT NULL AND lws.email LIKE '%@%.%')
              OR lws.cf_appointment_date IS NOT NULL
              OR lws.cf_cancelled_date   IS NOT NULL
          )
        GROUP BY 1
        ORDER BY 1
        """
        df = run_query(sql, project_id)
        if df.empty:
            return pd.DataFrame(columns=["date", "source", "spend", "clicks"])
        df["date"]   = pd.to_datetime(df["date"]).dt.date
        df["spend"]  = df["lead_count"].astype(float) * AFFILIATE_CPL_CAD
        df["clicks"] = 0
        df["source"] = "affiliate"
        return df[["date", "source", "spend", "clicks"]]

    # ── MAIN (ecolinew): Meta cache + Windsor BQ ────────────────────────────
    cache_df = _load_meta_spend_cache()

    if cache_df is not None and not cache_df.empty:
        cached_dates = set(cache_df["date"].unique())
        all_dates    = set(pd.date_range(start, end).date)
        missing      = sorted(all_dates - cached_dates)

        parts = [cache_df[cache_df["date"].between(start, end)].copy()]

        if missing:
            bq_start = missing[0]
            bq_end   = missing[-1]
            sql = f"""
            SELECT date, source, spend, clicks
            FROM `{project_id}.raw.spend_snap`
            WHERE source IN ('facebook', 'tiktok')
              AND date BETWEEN '{bq_start}' AND '{bq_end}'
            """
            bq_df = run_query(sql, project_id)
            bq_df["spend"]  = bq_df["spend"].astype(float)
            bq_df["clicks"] = bq_df["clicks"].astype(float)
            bq_df["date"]   = pd.to_datetime(bq_df["date"]).dt.date
            bq_df = bq_df[bq_df["date"].isin(set(missing))]
            parts.append(bq_df)

        return pd.concat(parts, ignore_index=True)

    # Full fallback to Windsor BQ
    sql = f"""
    SELECT date, source, spend, clicks
    FROM `{project_id}.raw.spend_snap`
    WHERE source IN ('facebook', 'tiktok')
      AND date BETWEEN '{start}' AND '{end}'
    """
    df = run_query(sql, project_id)
    df["spend"]  = df["spend"].astype(float)
    df["clicks"] = df["clicks"].astype(float)
    return df


# ─────────────────────────────────────────────
#  DEDUP  (applied in Python for slider support)
# ─────────────────────────────────────────────

def apply_dedup(df: pd.DataFrame, dedup_days: int) -> pd.DataFrame:
    """
    Mark each lead as clean (is_clean=True) if no prior occurrence of the
    same identifier exists within dedup_days before it.

    Identifier priority:
      1. phone_clean  — valid 10-digit NA number  → primary dedup key
      2. email        — fallback when phone invalid, BUT only counted as clean
                        if the lead shows real CRM engagement (booked, cancelled,
                        sold). Email-only leads with status='lead' (never responded,
                        no phone) are marked NOT clean — they can't be meaningfully
                        contacted or tracked.
      3. row_num      — last resort (always unique → always clean)

    Hard overrides (applied after dedup):
      + Always clean if lead has cf_appointment_date or cf_cancelled_date
        (they demonstrably went through the funnel regardless of phone quality).
      − Never clean if invalid phone AND no CRM engagement AND no appt/cancellation
        (email-only leads that never responded at all).
    """
    df = df.sort_values("dt").copy()

    valid_phone = df["phone_clean"].str.match(r'^[2-9][0-9]{9}$', na=False)
    has_email   = df["email"].notna() & df["email"].str.contains("@", na=False)

    # CRM engagement = any status beyond the raw 'lead' state
    engaged_statuses = {"appointment", "cancelled", "cancelled before appt", "sold"}
    has_crm = (
        df["status"].isin(engaged_statuses)
        if "status" in df.columns
        else pd.Series(False, index=df.index)
    )
    has_appt_or_canc = (
        df["cf_appointment_date"].notna() | df["cf_cancelled_date"].notna()
    )

    # ── Dedup key ──────────────────────────────────────────────────────────
    df["_dedup_key"] = df["phone_clean"].where(valid_phone, other=None)
    df["_dedup_key"] = df["_dedup_key"].fillna(df["email"].where(has_email))
    null_mask = df["_dedup_key"].isna()
    df.loc[null_mask, "_dedup_key"] = "unique_" + df.loc[null_mask, "row_num"].astype(str)

    # ── Standard lookback dedup ────────────────────────────────────────────
    df["_prev_dt"]        = df.groupby("_dedup_key")["dt"].shift(1)
    df["_days_since_prev"] = (df["dt"] - df["_prev_dt"]).dt.days
    df["is_clean"] = df["_days_since_prev"].isna() | (df["_days_since_prev"] >= dedup_days)

    # ── Hard override +: appointment/cancellation → always clean ───────────
    # Exception: if this is a recent duplicate (within dedup window), dedup takes priority.
    # This prevents re-submits with appointments from bypassing deduplication.
    is_recent_dup = df["_days_since_prev"].notna() & (df["_days_since_prev"] < dedup_days)
    df.loc[has_appt_or_canc & ~is_recent_dup, "is_clean"] = True

    # ── Hard override −: invalid phone + no real engagement → NOT clean ────
    # Email-only leads that never booked, cancelled, or converted can't be
    # reliably tracked and likely never responded — exclude from clean count.
    bad_email_only = ~valid_phone & has_email & ~has_crm & ~has_appt_or_canc
    no_contact     = ~valid_phone & ~has_email & ~has_appt_or_canc
    df.loc[bad_email_only | no_contact, "is_clean"] = False

    return df.drop(columns=["_dedup_key", "_prev_dt", "_days_since_prev"])


# ─────────────────────────────────────────────
#  FUNNEL METRICS
# ─────────────────────────────────────────────

def compute_funnel(df: pd.DataFrame, appt_window=None) -> dict:
    """
    Compute funnel metrics. All metrics are keyed off LEAD DATE — df must already
    be filtered to the desired date range by lead submission date.

    appt_window:
      - None  → count ALL appointments for leads in the period, regardless of when
                 the appointment is/was scheduled (Overview mode, matches report.monthly).
      - int   → count only appointments within N days of lead submission (Funnel Analysis).
    """
    total = len(df)
    clean = int(df["is_clean"].fillna(False).sum()) if "is_clean" in df.columns else total
    is_clean_mask = df["is_clean"].fillna(False) if "is_clean" in df.columns else pd.Series(True, index=df.index)
    sold  = int(((df["status"] == "sold") & is_clean_mask).sum())

    appt_dt  = pd.to_datetime(df["cf_appointment_date"]) if "cf_appointment_date" in df.columns else pd.Series(pd.NaT, index=df.index)
    sold_dt  = pd.to_datetime(df["cf_sold_date"])        if "cf_sold_date"         in df.columns else pd.Series(pd.NaT, index=df.index)
    today_dt = date.today()

    # Effective appointment date: appointment date if available, else sold date
    effective_dt = appt_dt.fillna(sold_dt)

    # A record has an appointment if it was booked (cf_booked_date = the moment
    # the lead agreed on the call) OR is sold (sold records may lack a booked date).
    booked_dt = pd.to_datetime(df["cf_booked_date"]) if "cf_booked_date" in df.columns else pd.Series(pd.NaT, index=df.index)
    has_appt = df["cf_booked_date"].notna() | (df["status"] == "sold")

    if appt_window is None:
        # ── Overview mode: all appointments for these leads, any date ──
        in_window = has_appt
    else:
        # ── Funnel analysis: only appointments within N days of lead submission ──
        days_to_appt = (effective_dt - df["dt"].dt.tz_localize(None)).dt.days
        in_window = has_appt & (days_to_appt >= 0) & (days_to_appt <= appt_window)

    appts = int(in_window.sum())

    # Status breakdown — status_with_cancelled is the source of truth.
    # cf_cancelled_date mirrors cf_appointment_date so date comparisons are unreliable.
    canc_before = int((in_window & (df["status"] == "cancelled before appt")).sum())
    canc_after  = int((in_window & (df["status"] == "cancelled")).sum())

    # Upcoming: all appointments with CRM status still "appointment" (not yet resolved).
    # These include both future appointments AND past appointments where CRM hasn't
    # been updated yet (pending). Once CRM updates, they move to sold/cancelled.
    today_ts = pd.Timestamp(today_dt)
    upcoming = int(
        (in_window & (df["status"] == "appointment")).sum()
    )
    # Pending subset: appointment date already passed but CRM status not yet updated
    pending = int(
        (in_window & (df["status"] == "appointment") & (appt_dt < today_ts)).sum()
    )

    # Showed up: appointment happened (strictly before today) and not cancelled-before
    showed_up = int(
        (
            (in_window & df["status"].isin(["sold", "cancelled"])) |
            (in_window & (df["status"] == "appointment") & (appt_dt < today_ts))
        ).sum()
    )

    show_rate = round(showed_up / appts * 100, 1) if appts else 0
    cr_la     = round(appts / clean * 100, 1)     if clean  else 0
    cr_as     = round(sold  / showed_up * 100, 1) if showed_up else 0

    # Revenue: sum of amount for sold records
    revenue = 0.0
    if "amount" in df.columns:
        sold_mask = df["status"] == "sold"
        revenue = float(pd.to_numeric(df.loc[sold_mask, "amount"], errors="coerce").fillna(0).sum())

    return {
        "all_leads":   total,
        "clean_leads": clean,
        "appts":       appts,
        "upcoming":    upcoming,
        "canc_before": canc_before,
        "canc_after":  canc_after,
        "pending":     pending,
        "showed_up":   showed_up,
        "sold":        sold,
        "revenue":     revenue,
        "show_rate":   show_rate,
        "cr_la":       cr_la,
        "cr_as":       cr_as,
    }


# ─────────────────────────────────────────────
#  SPEND ATTRIBUTION  (province → city)
# ─────────────────────────────────────────────

def attribute_city_spend(
    leads_clean: pd.DataFrame,
    spend_df: pd.DataFrame,
    rolling_days: int = 7,
) -> pd.DataFrame:
    """
    Distribute province spend to cities proportionally
    based on clean lead share within each province.

    Returns a DataFrame with columns:
        province, city, est_spend
    """
    if leads_clean.empty or spend_df.empty:
        return pd.DataFrame(columns=["province", "city", "est_spend"])

    # Lead share per province-city
    city_leads = (
        leads_clean[leads_clean["is_clean"].fillna(False)]
        .groupby(["province", "city"])
        .size()
        .reset_index(name="city_leads")
    )
    prov_leads = city_leads.groupby("province")["city_leads"].transform("sum")
    city_leads["city_share"] = city_leads["city_leads"] / prov_leads

    # Total province spend in period
    prov_spend = spend_df.groupby("province")["spend"].sum().reset_index(name="prov_spend")

    merged = city_leads.merge(prov_spend, on="province", how="left")
    merged["est_spend"] = merged["city_share"] * merged["prov_spend"].fillna(0)
    return merged[["province", "city", "est_spend", "city_leads"]]


# ─────────────────────────────────────────────
#  META LIVE  (direct Meta API, no Windsor delay)
# ─────────────────────────────────────────────

# All Canadian ad accounts (USD accounts excluded from spend totals)
META_ACCOUNTS = [
    ("act_1530450337262776", "Ecoline Windows"),
    ("act_3985742841525170", "Ecoline Windows #2"),
    ("act_299067382210535",  "Ecoline Windows #3"),
    ("act_397070935676618",  "Ecoline Windows #4"),
    ("act_1678446012529816", "Ecoline Windows #6"),
    ("act_376703401210376",  "Ecoline Windows #5 Traffic Acc"),
    ("act_431398042145214",  "Ecoline Windows #7"),
    ("act_3306273819695862", "Ecoline Windows #8"),
    ("act_458399650269969",  "Ecoline Affiliate"),
]


def classify_campaign(name: str) -> dict:
    """
    Parse campaign name → city, region, scope, camp_type.

    Naming convention:  ACC# - [LOCATION] - [LG|CONV|TRAFFIC] - ...
    Location patterns:
      - Known city name           → scope = 'city'
      - Province name             → scope = 'province'
      - 'SMALL CITIES [PROVINCE]' → scope = 'sub_regional'
      - 'ALL REGIONS'             → scope = 'national'
    """
    import re

    if not name:
        return {"scope": "other", "location": "—", "camp_type": "OTHER"}
    n = name.upper()

    # Campaign type
    if " - LG" in n or "-LG-" in n or "LEAD GEN" in n:
        camp_type = "LG"
    elif " - CONV" in n or "-CONV-" in n or "CONVERSION" in n:
        camp_type = "CONV"
    elif "TRAFFIC" in n:
        camp_type = "TRAFFIC"
    else:
        camp_type = "OTHER"

    # Scope + location
    if "ALL REGIONS" in n or "WHOLE CANADA" in n:
        return {"scope": "national", "location": "All Canada", "camp_type": camp_type}

    if "SMALL CITIES" in n:
        # e.g. SMALL CITIES ALBERTA
        m = re.search(r"SMALL CITIES\s+([A-Z\s]+?)(?:\s+-|\s+LG|\s+CONV|$)", n)
        loc = m.group(1).strip().title() if m else "Unknown"
        return {"scope": "sub_regional", "location": loc, "camp_type": camp_type}

    # Known provinces
    provinces = [
        "ALBERTA", "BRITISH COLUMBIA", "MANITOBA", "ONTARIO", "QUEBEC",
        "SASKATCHEWAN", "NEW BRUNSWICK", "NOVA SCOTIA", "NEWFOUNDLAND",
        "PRINCE EDWARD ISLAND", "YUKON", "NORTHWEST TERRITORIES", "NUNAVUT",
    ]
    for prov in provinces:
        if f" - {prov} -" in n or n.endswith(f" - {prov}") or f" - {prov}\n" in n:
            return {"scope": "province", "location": prov.title(), "camp_type": camp_type}

    # Must follow ACC# naming convention — otherwise treat as other
    if not re.match(r"ACC\d+\s*-", name, re.IGNORECASE):
        return {"scope": "other", "location": "—", "camp_type": camp_type}

    # Extract location token — text between first and second ' - '
    parts = [p.strip() for p in name.split(" - ")]
    location = parts[1] if len(parts) >= 2 else "Unknown"
    # Strip trailing date stamps like 13/03/26
    location = re.sub(r"\s*\d{2}/\d{2}/\d{2}$", "", location).strip()

    # Is it a known province?
    if location.upper() in provinces:
        return {"scope": "province", "location": location.title(), "camp_type": camp_type}

    # USA: extract actual city name (e.g. ACC3 - USA - PORTLAND → Portland)
    if "USA" in n:
        city_part = parts[2].title() if len(parts) >= 3 else location.title()
        # strip trailing type tokens
        city_part = re.split(r"\s*-\s*(LG|CONV|TRAFFIC|ABO|CBO)", city_part, flags=re.IGNORECASE)[0].strip()
        return {"scope": "usa", "location": city_part, "camp_type": camp_type}

    return {"scope": "city", "location": location.title(), "camp_type": camp_type}


def load_meta_live(date_preset: str = "last_7d") -> pd.DataFrame:
    """
    Load campaign-level Meta insights from local cache file.
    Cache is refreshed by Claude on demand — no direct API calls needed.
    Returns a flat DataFrame with one row per campaign.
    """
    try:
        from utils.meta_client import load_from_cache
        rows, _ = load_from_cache(date_preset)
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        # Parse classification
        clf = df["campaign_name"].apply(classify_campaign).apply(pd.Series)
        df = pd.concat([df, clf], axis=1)
        # Extract leads from 'leads' field (may be null for non-lead campaigns)
        if "leads" in df.columns:
            df["leads_meta"] = pd.to_numeric(df["leads"], errors="coerce").fillna(0)
        else:
            df["leads_meta"] = 0
        # Numeric coercions
        for col in ["spend", "impressions", "clicks", "reach", "cpm", "cpc"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df
    except Exception:
        return pd.DataFrame()
