"""
Ecoline Dashboard  —  v1
Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

from utils.data import (
    load_leads, load_calls, load_spend, load_spend_daily,
    apply_dedup, compute_funnel, attribute_city_spend,
    load_prediction_history, predict_upcoming_sales,
    _get_camp_type,
)
from utils.cross_channel import (
    load_cross_channel, compute_overlap, linear_attribution,
    touch_attribution, conversion_by_gap, geo_overlap,
    load_monthly_overlap_trend, cannibalization_analysis,
)

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Ecoline Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  PASSWORD PROTECTION (optional)
# ─────────────────────────────────────────────
def _check_password():
    """Simple password gate. Set DASHBOARD_PASSWORD in .streamlit/secrets.toml to enable."""
    _pw = st.secrets.get("DASHBOARD_PASSWORD", "") if hasattr(st, "secrets") else ""
    if not _pw:
        return True  # No password set → open access
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    st.markdown("### 🔒 Ecoline Dashboard")
    _entered = st.text_input("Пароль / Password", type="password")
    if st.button("Войти / Login"):
        if _entered == _pw:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Неверный пароль / Wrong password")
    return False

if not _check_password():
    st.stop()

# ─────────────────────────────────────────────
#  GLOBAL CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── BASE ── */
html, body, [class*="css"], * { font-family: 'Inter', sans-serif !important; }

[data-testid="stAppViewContainer"] { background: #F0F4F8 !important; }
[data-testid="stHeader"] { background: transparent !important; border: none !important; }
[data-testid="block-container"] { padding: 2rem 2.5rem !important; }

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: #0D1B2A !important;
    border-right: 1px solid #1E2D3D !important;
}
[data-testid="stSidebar"] section { background: #0D1B2A !important; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div { color: #94A3B8 !important; }
[data-testid="stSidebar"] hr { border-color: #1E2D3D !important; margin: 12px 0 !important; }

[data-testid="stSidebar"] [data-testid="stNumberInput"] input,
[data-testid="stSidebar"] [data-testid="stDateInput"] input,
[data-testid="stSidebar"] [data-testid="stMultiSelect"] > div > div {
    background: #1A2A3A !important;
    border: 1px solid #2D3F50 !important;
    color: #E2E8F0 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }
[data-testid="stSidebar"] .stRadio label {
    padding: 8px 12px !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #94A3B8 !important;
    transition: all 0.15s ease !important;
    cursor: pointer !important;
}
[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.05) !important; color: #E2E8F0 !important; }

/* ── MAIN HEADINGS ── */
h1 { font-size: 24px !important; font-weight: 800 !important; color: #0F172A !important; letter-spacing: -0.03em !important; margin-bottom: 2px !important; }
h2 { font-size: 18px !important; font-weight: 700 !important; color: #1E293B !important; letter-spacing: -0.02em !important; }
h3 { font-size: 15px !important; font-weight: 600 !important; color: #334155 !important; }
[data-testid="stCaptionContainer"] p { color: #94A3B8 !important; font-size: 12px !important; margin-top: 2px !important; }

/* ── METRICS ── */
[data-testid="stMetric"] {
    background: white !important;
    border-radius: 12px !important;
    padding: 12px 14px !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.03) !important;
    min-width: 0 !important;
    overflow: visible !important;
}
[data-testid="stMetricLabel"] > div {
    font-size: 10px !important;
    font-weight: 700 !important;
    color: #64748B !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
[data-testid="stMetricValue"] > div {
    font-size: 22px !important;
    font-weight: 800 !important;
    color: #0F172A !important;
    letter-spacing: -0.02em !important;
    white-space: nowrap !important;
}
[data-testid="stMetricDelta"] svg { display: none !important; }
[data-testid="stMetricDelta"] > div { font-size: 11px !important; font-weight: 600 !important; }

/* ── DIVIDERS ── */
hr { border: none !important; border-top: 1px solid #E2E8F0 !important; margin: 1.5rem 0 !important; }

/* ── DATAFRAMES ── */
[data-testid="stDataFrame"] {
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}

/* ── PLOTLY CHART WRAPPER ── */
[data-testid="stPlotlyChart"] > div {
    background: white !important;
    border-radius: 14px !important;
    border: 1px solid #E2E8F0 !important;
    padding: 4px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    overflow: hidden !important;
}

/* ── SEGMENTED CONTROL ── */
[data-testid="stSegmentedControl"] {
    background: #E8EEF4 !important;
    border-radius: 10px !important;
    padding: 3px !important;
    border: none !important;
}
[data-testid="stSegmentedControl"] button {
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}

/* ── SELECTBOX / INPUTS ── */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div,
[data-testid="stDateInput"] > div > div > input,
[data-testid="stNumberInput"] input {
    border-radius: 8px !important;
    border: 1px solid #E2E8F0 !important;
    font-size: 13px !important;
}
[data-testid="stCheckbox"] label { font-size: 13px !important; font-weight: 500 !important; }

/* ── SLIDERS ── */
[data-testid="stSlider"] [data-testid="stSlider"] > div { color: #2563EB !important; }

/* ── ALERT / INFO BOXES ── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-left-width: 4px !important;
    font-size: 13px !important;
}

/* ── BUTTONS ── */
[data-testid="stBaseButton-secondary"] button,
button[kind="secondary"] {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    border: 1px solid #E2E8F0 !important;
    background: white !important;
    color: #334155 !important;
}

/* ── SECTION TITLE ── */
.section-title {
    font-size: 14px !important;
    font-weight: 700 !important;
    color: #1E293B !important;
    margin: 20px 0 10px 0 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
.section-title::after {
    content: '';
    display: block;
    width: 28px;
    height: 2px;
    background: #2563EB;
    margin-top: 5px;
    border-radius: 2px;
}

/* ── SIDEBAR HEADER ── */
.sidebar-header {
    font-size: 17px !important;
    font-weight: 800 !important;
    color: #F1F5F9 !important;
    letter-spacing: -0.02em !important;
}

/* ── TAGS / BADGES ── */
.tag-meta { background:#DBEAFE; color:#1E40AF; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; letter-spacing:0.03em; }
.tag-call { background:#DCFCE7; color:#166534; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; letter-spacing:0.03em; }
.tag-aff  { background:#FEF9C3; color:#854D0E; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; letter-spacing:0.03em; }

/* ── WARNINGS ── */
[data-testid="stWarning"] { border-radius: 10px !important; }

/* ── EXPANDER FIX — prevent text overlap with arrow icon ── */
[data-testid="stExpander"] details summary {
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
    padding-right: 10px !important;
}
[data-testid="stExpander"] details summary span {
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
}
/* Fix radio buttons / sidebar nav overlap */
[data-testid="stSidebar"] .stRadio label {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SIDEBAR — GLOBAL CONTROLS
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="sidebar-header">🌿 Ecoline</p>', unsafe_allow_html=True)
    st.divider()

    # ── DATABASE SELECTOR ──
    from utils.bq_client import PROJECTS
    _db_label = st.selectbox(
        "🗄️ Database",
        options=list(PROJECTS.keys()),
        index=0,
    )
    active_project = PROJECTS[_db_label]
    st.divider()

    page = st.radio(
        "Navigation",
        [
            "📊 Overview",
            "📈 Trends",
            "🗺️ Geography",
            "📋 Lead Detail",
            "🔄 Funnel Analysis",
            "📱 Campaign Intelligence",
            "⚖️ Source Comparison",
            "🔗 Cross-Channel",
            "🎨 Creative Performance",
            "📡 Meta Live",
            "💬 Data Assistant",
            "✅ To Do & Feedback",
            "📖 How It Works",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("**📅 Date Range**")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From", value=date.today() - timedelta(days=30), label_visibility="collapsed")
    with col2:
        end_date = st.date_input("To", value=date.today() - timedelta(days=1), label_visibility="collapsed")

    # Comparison period (same length, immediately before)
    delta_days = (end_date - start_date).days + 1
    comp_end   = start_date - timedelta(days=1)
    comp_start = comp_end - timedelta(days=delta_days - 1)

    st.markdown("**🔍 Source**")
    source_filter = st.multiselect(
        "Source",
        ["META", "TikTok", "Calls", "Affiliate", "Other"],
        default=["META", "Calls"],
        label_visibility="collapsed",
    )

    st.divider()
    # Default dedup/appt window (used on all pages except Funnel Analysis)
    st.markdown("**⚙️ Global Defaults**")
    default_dedup = st.number_input("Dedup window (days)", min_value=1, max_value=90, value=30)
    default_appt  = st.number_input("Appt window (days)",  min_value=1, max_value=120, value=30)

# ─────────────────────────────────────────────
#  DATA LOAD
# ─────────────────────────────────────────────
# Load a wider window to support dedup look-back
load_start = start_date - timedelta(days=max(default_dedup, 90))

with st.spinner("Fetching data from BigQuery…"):
    leads_raw   = load_leads(load_start, end_date, active_project)
    calls_raw   = load_calls(start_date, end_date, active_project)
    spend_df    = load_spend(start_date, end_date, active_project)
    spend_daily = load_spend_daily(start_date, end_date, active_project)

    # Dedup full history, then filter to chosen date range
    leads_all   = apply_dedup(leads_raw, default_dedup)
    leads_range = leads_all[leads_all["date"].between(start_date, end_date)].copy()

    # Comparison period
    leads_comp_raw = load_leads(comp_start - timedelta(days=default_dedup), comp_end, active_project)
    leads_comp_all = apply_dedup(leads_comp_raw, default_dedup)
    leads_comp     = leads_comp_all[leads_comp_all["date"].between(comp_start, comp_end)].copy()
    calls_comp     = load_calls(comp_start, comp_end, active_project)

# Apply source filter
def filter_source(df):
    if not source_filter:
        return df
    return df[df["source"].isin(source_filter)]

leads_f    = filter_source(leads_range)
calls_f    = filter_source(calls_raw)
leads_comp_f = filter_source(leads_comp)
calls_comp_f = filter_source(calls_comp)

# Combined (leads + calls) — leads in selected date range only
combined    = pd.concat([leads_f, calls_f],    ignore_index=True)
combined_c  = pd.concat([leads_comp_f, calls_comp_f], ignore_index=True)

# Funnel metrics — all appointments for leads in the period, keyed by lead date
funnel      = compute_funnel(combined)
funnel_comp = compute_funnel(combined_c)

# City spend attribution
city_spend  = attribute_city_spend(leads_f, spend_df)

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def pct_delta(cur, prev):
    if prev == 0:
        return None
    return round((cur - prev) / prev * 100, 1)

def fmt_cad(val):
    return f"${val:,.0f}"

def delta_str(delta):
    if delta is None:
        return "—"
    arrow = "▲" if delta >= 0 else "▼"
    color = "green" if delta >= 0 else "red"
    return f":{color}[{arrow} {abs(delta)}%]"

def metric_row(cols, labels, values, deltas, formats=None):
    for col, label, val, delta in zip(cols, labels, values, deltas):
        with col:
            prev = funnel_comp.get(delta) if isinstance(delta, str) else None
            st.metric(label, val, delta_str(pct_delta(val, prev)) if prev is not None else None)

BLUE   = "#2563EB"
BLUE2  = "#3B82F6"
GREEN  = "#10B981"
RED    = "#EF4444"
AMBER  = "#F59E0B"
PURPLE = "#8B5CF6"
GRAY   = "#94A3B8"

CHART_COLORS = {
    "META": BLUE, "Calls": GREEN, "Affiliate": AMBER,
    "TikTok": PURPLE, "Other": GRAY,
}

def apply_chart_style(fig, height=None, legend_bottom=False):
    """Apply consistent modern styling to any Plotly figure."""
    updates = dict(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=12, color="#334155"),
        margin=dict(l=4, r=4, t=28, b=4),
        xaxis=dict(showgrid=False, linecolor="#E2E8F0", tickfont=dict(size=11, color="#64748B")),
        yaxis=dict(gridcolor="#F1F5F9", linecolor="#E2E8F0", tickfont=dict(size=11, color="#64748B"), zeroline=False),
        hoverlabel=dict(bgcolor="white", bordercolor="#E2E8F0", font=dict(family="Inter", size=12)),
    )
    if height:
        updates["height"] = height
    if legend_bottom:
        updates["legend"] = dict(orientation="h", y=-0.22, x=0, font=dict(size=11), bgcolor="rgba(0,0,0,0)")
    else:
        updates["legend"] = dict(font=dict(size=11), bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)")
    fig.update_layout(**updates)

# ─────────────────────────────────────────────
#  PAGE: OVERVIEW
# ─────────────────────────────────────────────
if page == "📊 Overview":
    st.title("Overview")
    st.caption(f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d, %Y')}  ·  vs previous {delta_days} days")

    # Total spend
    total_spend = spend_daily["spend"].sum()
    total_clicks = spend_daily["clicks"].sum()
    comp_spend = load_spend_daily(comp_start, comp_end, active_project)["spend"].sum()

    # KPI row
    k  = funnel
    kc = funnel_comp

    # Calls breakout for KPI row
    _calls_funnel = compute_funnel(calls_f) if not calls_f.empty else {"all_leads": 0, "appts": 0, "sold": 0}
    _forms_leads = k['all_leads'] - _calls_funnel['all_leads']
    _forms_appts = k['appts'] - _calls_funnel['appts']

    _cpa  = total_spend / k['appts']     if k['appts']     else None
    _cps  = total_spend / k['sold']      if k['sold']      else None

    # Row 1: spend funnel (6 cols)
    row1 = st.columns(6)
    metrics_r1 = [
        ("Spend",        fmt_cad(total_spend),                                                 pct_delta(total_spend, comp_spend)),
        ("All Leads",    f"{k['all_leads']:,}",                                                pct_delta(k['all_leads'],    kc['all_leads'])),
        ("Clean Leads",  f"{k['clean_leads']:,}",                                              pct_delta(k['clean_leads'], kc['clean_leads'])),
        ("CPL",          fmt_cad(total_spend / k['clean_leads']) if k['clean_leads'] else "—", None),
        ("Appointments", f"{k['appts']:,}",                                                    pct_delta(k['appts'],       kc['appts'])),
        ("CPA",          fmt_cad(_cpa) if _cpa else "—",                                       None),
    ]
    for col, (label, val, delta) in zip(row1, metrics_r1):
        with col:
            if delta is not None:
                arrow = "▲" if delta >= 0 else "▼"
                color = "normal" if delta >= 0 else "inverse"
                st.metric(label, val, f"{arrow} {abs(delta)}%", delta_color=color)
            else:
                st.metric(label, val)

    # Row 2: quality metrics (4 cols)
    row2 = st.columns(4)
    metrics_r2 = [
        ("Showed Up",    f"{k['showed_up']:,}",                                             None),
        ("Sold",         f"{k['sold']:,}",                                                  pct_delta(k['sold'],        kc['sold'])),
        ("CPS",          fmt_cad(_cps) if _cps else "—",                                    None),
        ("CR L→A",       f"{k['cr_la']}%",                                                  pct_delta(k['cr_la'],       kc['cr_la'])),
    ]
    for col, (label, val, delta) in zip(row2, metrics_r2):
        with col:
            if delta is not None:
                arrow = "▲" if delta >= 0 else "▼"
                color = "normal" if delta >= 0 else "inverse"
                st.metric(label, val, f"{arrow} {abs(delta)}%", delta_color=color)
            else:
                st.metric(label, val)

    # Row 3: appointment health metrics (3 cols)
    row3 = st.columns(3)
    _canc_all = k['canc_before'] + k['canc_after']
    _canc_all_pct  = round(_canc_all   / k['appts'] * 100, 1) if k['appts'] else 0
    _canc_bef_pct  = round(k['canc_before'] / k['appts'] * 100, 1) if k['appts'] else 0
    metrics_r3 = [
        ("Upcoming",            f"{k['upcoming']:,}",  None),
        ("Cancelled (all)",     f"{_canc_all:,}",      f"{_canc_all_pct}% of appts"),
        ("Cancelled before appt", f"{k['canc_before']:,}", f"{_canc_bef_pct}% of appts"),
    ]
    for col, (label, val, help_txt) in zip(row3, metrics_r3):
        with col:
            st.metric(label, val, help=help_txt)

    # Forms vs Calls breakdown row
    fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
    fc1.metric("Forms (leads)", f"{_forms_leads:,}", help="Web form submissions only")
    fc2.metric("Calls", f"{_calls_funnel['all_leads']:,}", help="First-time callers (DNI)")
    fc3.metric("Appts (forms)", f"{_forms_appts:,}", help="Appointments from form leads")
    fc4.metric("Appts (calls)", f"{_calls_funnel['appts']:,}", help="Appointments from callers")
    fc5.metric("Sold (calls)", f"{_calls_funnel['sold']:,}")
    fc6.metric("CR Call→Appt", f"{round(_calls_funnel['appts'] / _calls_funnel['all_leads'] * 100, 1) if _calls_funnel['all_leads'] else 0}%")

    # ── Appointment prediction insight ──────────────────────────────────────
    showed_up = k['showed_up']
    cr_as_pct = round(k['sold'] / showed_up * 100, 1) if showed_up else 0

    # Calibrated prediction: use historical upcoming→sold rate from closed months
    pred_hist = load_prediction_history(active_project)
    current_month = end_date.month  # use the calendar month of the selected period end

    if not pred_hist.empty:
        settled = pred_hist[
            pred_hist["upcoming_still_pending"] < pred_hist["upcoming_at_month_end"] * 0.10
        ]
        # Seasonal rate: avg for this calendar month across all years (best model, MAPE 11.9%)
        month_rows = pred_hist[pred_hist["calendar_month"] == current_month] if "calendar_month" in pred_hist.columns else pd.DataFrame()
        month_settled = month_rows[month_rows["upcoming_still_pending"] < month_rows["upcoming_at_month_end"] * 0.10] if not month_rows.empty else pd.DataFrame()

        if not month_settled.empty:
            hist_rate = round(month_settled["conv_rate"].mean(), 1)
            rate_label = f"{hist_rate}% seasonal ({['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][current_month]})"
        elif not settled.empty:
            hist_rate = round(settled["conv_rate"].mean(), 1)
            rate_label = f"{hist_rate}% avg (no seasonal data for this month yet)"
        else:
            hist_rate = 11.0
            rate_label = f"{hist_rate}% fallback"
    else:
        hist_rate  = 11.0
        rate_label = f"{hist_rate}% fallback"

    predicted_seasonal = round(k['upcoming'] * hist_rate / 100) if k['upcoming'] else 0

    # ML prediction — score each upcoming appointment individually
    upcoming_df = combined[
        (combined["status"] == "appointment") &
        (pd.to_datetime(combined["cf_appointment_date"]).dt.date >= date.today())
    ].copy()
    ml_result = predict_upcoming_sales(upcoming_df)
    if ml_result:
        predicted      = ml_result["predicted"]
        pred_detail    = f"ML per-appt · avg prob {ml_result['mean_prob']}% · {ml_result['n_scored']} appts scored"
    else:
        predicted      = predicted_seasonal
        pred_detail    = f"from {k['upcoming']:,} upcoming \u00d7 {rate_label}"

    st.markdown(
        f"""
        <div style="background:rgba(37,99,235,0.07);border:1px solid rgba(37,99,235,0.18);
                    border-radius:12px;padding:14px 20px;margin:14px 0 6px 0;
                    display:flex;gap:40px;align-items:center;flex-wrap:wrap;">
            <div>
                <div style="color:#94A3B8;font-size:12px;text-transform:uppercase;letter-spacing:.05em;">Showed Up</div>
                <div>
                    <span style="font-size:22px;font-weight:700;color:#F1F5F9;">{showed_up:,}</span>
                    <span style="color:#94A3B8;font-size:12px;"> / {k['appts']:,} total appts</span>
                </div>
            </div>
            <div>
                <div style="color:#94A3B8;font-size:12px;text-transform:uppercase;letter-spacing:.05em;">Cancelled Before</div>
                <div>
                    <span style="font-size:22px;font-weight:700;color:#EF4444;">{k['canc_before']:,}</span>
                    <span style="color:#94A3B8;font-size:12px;"> never showed &middot; after: {k['canc_after']:,} no-sale</span>
                </div>
            </div>
            <div>
                <div style="color:#94A3B8;font-size:12px;text-transform:uppercase;letter-spacing:.05em;">Real Close Rate (showed &#8594; sold)</div>
                <div>
                    <span style="font-size:22px;font-weight:700;color:#10B981;">{cr_as_pct}%</span>
                    <span style="color:#94A3B8;font-size:12px;"> ({k['sold']:,} sold from {showed_up:,} shown)</span>
                </div>
            </div>
            <div>
                <div style="color:#94A3B8;font-size:12px;text-transform:uppercase;letter-spacing:.05em;">Pending CRM Update (incl. in Upcoming)</div>
                <div>
                    <span style="font-size:22px;font-weight:700;color:#F59E0B;">{k['pending']:,}</span>
                    <span style="color:#94A3B8;font-size:12px;"> appt date passed &middot; awaiting sold/cancelled</span>
                </div>
            </div>
            <div style="border-left:1px solid rgba(37,99,235,0.25);padding-left:32px;">
                <div style="color:#94A3B8;font-size:12px;text-transform:uppercase;letter-spacing:.05em;">Predicted Sales from Upcoming</div>
                <div>
                    <span style="font-size:22px;font-weight:700;color:#10B981;">~{predicted:,}</span>
                    <span style="color:#94A3B8;font-size:12px;"> {pred_detail}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Historical prediction accuracy table ────────────────────────────────
    st.write("")
    if not pred_hist.empty:
        with st.expander("Prediction Model Accuracy — Historical Validation", expanded=False):
            st.caption(
                "For each past month: appointments that were 'upcoming' at month end "
                "vs what the model would have predicted vs what actually sold. "
                f"Calibrated rate used for prediction: **{hist_rate}%** (avg of settled months)."
            )
            acc = pred_hist.copy()
            acc["predicted"] = (acc["upcoming_at_month_end"] * hist_rate / 100).round().astype(int)
            acc["accuracy_pct"] = acc.apply(
                lambda r: round(r["upcoming_became_sold"] / r["predicted"] * 100, 1)
                if r["predicted"] > 0 else None,
                axis=1,
            )
            acc_display = acc[[
                "lead_month", "upcoming_at_month_end", "predicted",
                "upcoming_became_sold", "upcoming_canc_before", "upcoming_canc_after",
                "upcoming_still_pending", "conv_rate", "accuracy_pct",
            ]].copy()
            acc_display.columns = [
                "Month", "Upcoming at End", "Predicted Sales",
                "Actual Sold", "Canc. Before", "Canc. After",
                "Still Pending", "Real Conv %", "Model Accuracy %",
            ]
            st.dataframe(acc_display, use_container_width=True, hide_index=True)
    # ────────────────────────────────────────────────────────────────────────

    st.divider()

    # Source cards — per-source funnel breakdown
    st.markdown('<p class="section-title">By Source</p>', unsafe_allow_html=True)
    src_funnel = pd.DataFrame([
        {"source": src, **compute_funnel(grp)}
        for src, grp in combined.groupby("source")
    ])
    if src_funnel.empty:
        st.info("No leads/calls in the selected date range and source filter.")
    else:
        src_cols = st.columns(len(src_funnel))
        for col, (_, row) in zip(src_cols, src_funnel.iterrows()):
            with col:
                st.markdown(f"**{row['source']}**")
                st.metric("All Leads",    f"{int(row['all_leads']):,}")
                st.metric("Clean Leads",  f"{int(row['clean_leads']):,}")
                st.metric("Appointments", f"{int(row['appts']):,}")
                st.metric("Upcoming",     f"{int(row['upcoming']):,}")
                st.metric("Sold",         f"{int(row['sold']):,}")

    # Calls breakout — calls are attributed to parent source (META etc.) above,
    # but shown separately here so we always see call volume on Overview.
    if not calls_f.empty:
        st.divider()
        st.markdown('<p class="section-title">Calls — First-Time Callers</p>', unsafe_allow_html=True)
        call_funnel = compute_funnel(calls_f)
        cc1, cc2, cc3, cc4, cc5 = st.columns(5)
        cc1.metric("Calls", f"{call_funnel['all_leads']:,}")
        cc2.metric("Appointments", f"{call_funnel['appts']:,}")
        cc3.metric("Upcoming", f"{call_funnel['upcoming']:,}")
        cc4.metric("Sold", f"{call_funnel['sold']:,}")
        cc5.metric("CR Call→Appt", f"{call_funnel['cr_la']:.1f}%")
        st.caption("Calls are also counted in their parent source (META, Affiliate) above — this is a separate breakout, not double-counting the totals.")

    st.divider()

    # Daily trend chart
    st.markdown('<p class="section-title">Daily Trend — Clean Leads</p>', unsafe_allow_html=True)
    daily = (
        combined[combined["is_clean"].fillna(False)]
        .groupby(["date", "source"])
        .size()
        .reset_index(name="clean_leads")
    )
    if not daily.empty:
        fig = px.bar(
            daily, x="date", y="clean_leads", color="source",
            color_discrete_map=CHART_COLORS,
            labels={"clean_leads": "Clean Leads", "date": ""},
        )
        apply_chart_style(fig, height=300, legend_bottom=True)
        st.plotly_chart(fig, use_container_width=True)

    # Top cities
    st.markdown('<p class="section-title">Top Cities — Clean Leads</p>', unsafe_allow_html=True)
    top_cities = (
        combined[combined["is_clean"].fillna(False)]
        .groupby(["province", "city"])
        .agg(clean_leads=("row_num", "count"), sold=("status", lambda x: (x == "sold").sum()))
        .reset_index()
        .sort_values("clean_leads", ascending=False)
        .head(10)
    )
    if not top_cities.empty:
        fig2 = px.bar(
            top_cities, x="clean_leads", y="city", orientation="h",
            color_discrete_sequence=[BLUE2],
            labels={"clean_leads": "Clean Leads", "city": ""},
        )
        apply_chart_style(fig2, height=320)
        fig2.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────
#  PAGE: TRENDS
# ─────────────────────────────────────────────
elif page == "📈 Trends":
    st.title("Trends")

    # ──────────────────────────────────────────────────────────────────────
    #  4-WEEK APPOINTMENT CALENDAR
    # ──────────────────────────────────────────────────────────────────────
    st.markdown('<p class="section-title">📅 4-Week Appointment Calendar</p>', unsafe_allow_html=True)

    _cal_today   = date.today()
    _cal_end     = _cal_today - timedelta(days=1)
    _cal_start   = _cal_end   - timedelta(days=27)
    _yoy_start   = _cal_start - timedelta(days=364)
    _yoy_end     = _cal_end   - timedelta(days=364)

    st.caption(
        f"Booked appointments by day · "
        f"{_cal_start.strftime('%b %d')} – {_cal_end.strftime('%b %d, %Y')}  "
        f"· vs same period last year (−52 weeks)"
    )

    @st.cache_data(ttl=1800, show_spinner=False)
    def _load_cal(s, e):
        leads = load_leads(s - timedelta(days=45), e)
        calls = load_calls(s - timedelta(days=45), e)
        return pd.concat([leads, calls], ignore_index=True)

    with st.spinner("Loading calendar data…"):
        _cal_raw  = _load_cal(_cal_start,  _cal_end)
        _yoy_raw  = _load_cal(_yoy_start,  _yoy_end)

    _SEGS = ["Meta · LG", "Meta · CONV", "Calls", "Affiliate"]
    _SEG_COLORS = {
        "Meta · LG":   "#2563EB",
        "Meta · CONV": "#7C3AED",
        "Calls":        "#059669",
        "Affiliate":    "#D97706",
    }

    def _seg_label(row):
        src = str(row.get("source", "")).upper()
        ct  = str(row.get("campaign_type", "")).upper()
        st_ = str(row.get("source_type", "")).lower()
        # Calls first — load_calls sets source_type="call" and campaign_type="Call"
        if st_ == "call" or ct == "CALL":
            return "Calls"
        if src == "AFFILIATE":
            return "Affiliate"
        if src == "META":
            if ct == "LG":   return "Meta · LG"
            if ct == "CONV": return "Meta · CONV"
            return "Meta · LG"   # fallback META → LG bucket
        return "Other"

    def _build_cal(df):
        out = {}
        booked = df[df["cf_booked_date"].notna()].copy()
        booked["_bd"]  = pd.to_datetime(booked["cf_booked_date"]).dt.date
        booked["_seg"] = booked.apply(_seg_label, axis=1)
        for _, r in booked.iterrows():
            d, s = r["_bd"], r["_seg"]
            if d not in out:
                out[d] = {sg: 0 for sg in _SEGS}
                out[d]["Other"] = 0
            if s in out[d]:
                out[d][s] += 1
            else:
                out[d]["Other"] += 1
        for d in out:
            out[d]["_total"] = sum(out[d][sg] for sg in _SEGS) + out[d]["Other"]
        return out

    _curr = _build_cal(_cal_raw)
    _yoy_raw_data = _build_cal(_yoy_raw)
    _yoy  = {d + timedelta(days=364): v for d, v in _yoy_raw_data.items()}

    # Align calendar to start on Monday of the first week
    _wk0   = _cal_start - timedelta(days=_cal_start.weekday())
    _days  = [_wk0 + timedelta(days=i) for i in range(28)]
    _weeks = [_days[i:i+7] for i in range(0, 28, 7)]
    _DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    _html = ["""
<style>
.ec-cal{width:100%;border-collapse:collapse;font-family:Inter,sans-serif;font-size:12px}
.ec-cal th{background:#F1F5F9;color:#64748B;font-weight:600;text-align:center;
           padding:6px 2px;border:1px solid #E2E8F0;font-size:11px}
.ec-cal td{border:1px solid #E2E8F0;vertical-align:top;padding:5px 6px;min-width:110px}
.ec-wk{background:#F8FAFC;font-weight:700;color:#475569;font-size:11px;
       text-align:center;vertical-align:middle!important;width:52px}
.ec-tot{font-size:22px;font-weight:800;color:#0F172A;text-align:center;line-height:1.1}
.ec-dp{font-size:11px;font-weight:700;color:#059669}
.ec-dn{font-size:11px;font-weight:700;color:#DC2626}
.ec-py{font-size:11px;color:#94A3B8}
.ec-seg{display:flex;justify-content:space-between;margin:1px 0}
.ec-sn{font-size:10px}
.ec-sv{font-size:10px;font-weight:700;color:#334155}
.ec-dim{background:#FAFAFA}
.ec-dim .ec-tot{color:#CBD5E1}
.ec-zero .ec-tot{color:#CBD5E1;font-size:18px}
</style>
<table class="ec-cal"><thead><tr>
<th style="width:52px">Week</th>
"""]
    for dn in _DAY_NAMES:
        _html.append(f'<th>{dn}</th>')
    _html.append('</tr></thead><tbody>')

    for wi, week in enumerate(_weeks):
        in_range = [d for d in week if _cal_start <= d <= _cal_end]
        if not in_range:
            continue
        _html.append('<tr>')
        wk_label = in_range[0].strftime("%b %d")
        _html.append(f'<td class="ec-wk">Wk {wi+1}<br/><span style="font-weight:400;font-size:10px">{wk_label}</span></td>')
        for d in week:
            in_r = _cal_start <= d <= _cal_end
            c    = _curr.get(d, {})
            y    = _yoy.get(d, {})
            tot_c = c.get("_total", 0)
            tot_y = y.get("_total", 0)
            delta  = tot_c - tot_y
            td_cls = "" if in_r else "ec-dim"
            if tot_c == 0 and in_r:
                td_cls += " ec-zero"
            _html.append(f'<td class="{td_cls}">')
            # Date label
            _html.append(f'<div style="font-size:10px;color:#94A3B8;text-align:right">{d.strftime("%m/%d")}</div>')
            # Total
            _html.append(f'<div class="ec-tot">{tot_c if tot_c else "—"}</div>')
            # YoY delta
            if tot_y > 0 or tot_c > 0:
                sign = "+" if delta >= 0 else ""
                dcls = "ec-dp" if delta >= 0 else "ec-dn"
                _html.append(f'<div style="text-align:center;margin:1px 0">'
                             f'<span class="{dcls}">[{sign}{delta}]</span> '
                             f'<span class="ec-py">({tot_y})</span></div>')
            # Segment rows
            _html.append('<div style="margin-top:4px;padding-top:3px;border-top:1px solid #F1F5F9">')
            for seg in _SEGS:
                val = c.get(seg, 0)
                if not in_r and val == 0:
                    continue
                col = _SEG_COLORS.get(seg, "#64748B")
                _html.append(f'<div class="ec-seg">'
                             f'<span class="ec-sn" style="color:{col}">{seg}</span>'
                             f'<span class="ec-sv">{val}</span></div>')
            _html.append('</div></td>')
        _html.append('</tr>')

    _html.append('</tbody></table>')
    st.markdown("".join(_html), unsafe_allow_html=True)

    st.divider()

    # ──────────────────────────────────────────────────────────────────────
    #  FUNNEL TREND TABLE (existing)
    # ──────────────────────────────────────────────────────────────────────
    gran = st.segmented_control("Granularity", ["Daily", "Weekly", "Monthly"], default="Weekly")

    df = combined.copy()
    df["dt_col"] = pd.to_datetime(df["date"])
    if gran == "Weekly":
        df["period"] = df["dt_col"].dt.to_period("W").apply(lambda p: p.start_time.date())
    elif gran == "Monthly":
        df["period"] = df["dt_col"].dt.to_period("M").apply(lambda p: p.start_time.date())
    else:
        df["period"] = df["date"]

    spend_agg = spend_daily.copy()
    spend_agg["dt_col"] = pd.to_datetime(spend_agg["date"])
    if gran == "Weekly":
        spend_agg["period"] = spend_agg["dt_col"].dt.to_period("W").apply(lambda p: p.start_time.date())
    elif gran == "Monthly":
        spend_agg["period"] = spend_agg["dt_col"].dt.to_period("M").apply(lambda p: p.start_time.date())
    else:
        spend_agg["period"] = spend_agg["date"]

    spend_by_period = spend_agg.groupby("period")["spend"].sum().reset_index()

    trend = pd.DataFrame([
        {"period": period, **compute_funnel(grp)}
        for period, grp in df.groupby("period")
    ])
    trend = trend.merge(spend_by_period, on="period", how="left")
    trend["spend"] = trend["spend"].fillna(0)
    trend["CPL"]   = trend.apply(lambda r: r["spend"] / r["clean_leads"] if r["clean_leads"] else None, axis=1)
    trend["CPA"]   = trend.apply(lambda r: r["spend"] / r["appts"] if r["appts"] else None, axis=1)
    trend["CPA1"]  = trend.apply(lambda r: r["spend"] / r["showed_up"] if r["showed_up"] else None, axis=1)
    trend["CPS"]   = trend.apply(lambda r: r["spend"] / r["sold"] if r["sold"] else None, axis=1)
    # Canc Before % = canc_before / (showed_up + canc_before) — i.e. out of all resolved appts (excl. upcoming)
    trend["canc_before_pct"] = trend.apply(
        lambda r: round(r["canc_before"] / (r["showed_up"] + r["canc_before"]) * 100, 1)
        if (r["showed_up"] + r["canc_before"]) > 0 else None, axis=1
    )
    trend["ROAS"] = trend.apply(lambda r: round(r["revenue"] / r["spend"], 2) if r["spend"] else None, axis=1)
    trend["period"] = pd.to_datetime(trend["period"])

    # Table
    st.markdown('<p class="section-title">Funnel Table</p>', unsafe_allow_html=True)
    display = trend[["period", "spend", "all_leads", "clean_leads", "CPL",
                      "appts", "CPA", "upcoming", "showed_up", "CPA1",
                      "canc_before", "canc_before_pct", "canc_after",
                      "sold", "CPS", "revenue", "ROAS", "cr_la", "cr_as"]].copy()
    display.columns = ["Period", "Ad Spend", "All Leads", "Clean Leads", "CPL",
                        "Appts", "CPA", "Upcoming", "Showed Up", "CPA1",
                        "Canc. Before", "Canc.B %", "Canc. After",
                        "Sold", "CPS", "Revenue", "ROAS", "CR L→A%", "CR A→S%"]
    display["Ad Spend"] = display["Ad Spend"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display["CPL"]   = display["CPL"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display["CPA"]   = display["CPA"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display["CPA1"]  = display["CPA1"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display["CPS"]   = display["CPS"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display["Revenue"] = display["Revenue"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display["ROAS"]  = display["ROAS"].apply(lambda x: f"{x:.2f}x" if x else "—")
    display["Canc.B %"] = display["Canc.B %"].apply(lambda x: f"{x}%" if x is not None else "—")
    display["Period"] = display["Period"].dt.strftime("%Y-%m-%d")
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.divider()

    # Charts
    chart_metrics = [
        ("clean_leads", "Clean Leads", BLUE),
        ("appts",       "Appointments", AMBER),
        ("CPL",         "CPL ($)",      GREEN),
        ("CPA",         "CPA ($)",      AMBER),
        ("CPA1",        "CPA1 ($)",     PURPLE),
        ("CPS",         "CPS ($)",      RED),
    ]
    cols = st.columns(2)
    for i, (col_name, label, color) in enumerate(chart_metrics):
        with cols[i % 2]:
            chart_df = trend[["period", col_name]].dropna()
            if not chart_df.empty:
                # hex → rgba fill
                h = color.lstrip("#")
                r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
                fill_color = f"rgba({r},{g},{b},0.08)"
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=chart_df["period"], y=chart_df[col_name],
                    mode="lines+markers", name=label,
                    line=dict(color=color, width=2.5),
                    marker=dict(size=5, color=color),
                    fill="tozeroy", fillcolor=fill_color,
                ))
                chart_df = chart_df.copy()
                chart_df["ma"] = chart_df[col_name].rolling(3, min_periods=1).mean()
                fig.add_trace(go.Scatter(
                    x=chart_df["period"], y=chart_df["ma"],
                    mode="lines", name="3-period avg",
                    line=dict(color=GRAY, width=1.5, dash="dot"),
                ))
                apply_chart_style(fig, height=280, legend_bottom=True)
                fig.update_layout(title=dict(text=label, font=dict(size=13, weight=700, color="#0F172A"), x=0, pad=dict(l=4)))
                st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
#  PAGE: GEOGRAPHY
# ─────────────────────────────────────────────
elif page == "🗺️ Geography":
    st.title("Geography")
    st.caption("⚠️ City-level spend is estimated using lead proportion model. Province spend is accurate (from META).")

    view = st.segmented_control("View", ["Province", "City"], default="City")

    # Build city-level table — use full combined (not pre-filtered to clean)
    # so compute_funnel can correctly split all_leads vs clean_leads per city
    geo = pd.DataFrame([
        {"province": prov, "city": city, **compute_funnel(grp)}
        for (prov, city), grp in combined.groupby(["province", "city"])
    ])
    geo = geo.merge(city_spend[["province", "city", "est_spend"]], on=["province", "city"], how="left")
    geo["est_spend"] = geo["est_spend"].fillna(0)
    geo["CPL"] = geo.apply(lambda r: r["est_spend"] / r["clean_leads"] if r["clean_leads"] else None, axis=1)
    geo["CPA"] = geo.apply(lambda r: r["est_spend"] / r["appts"] if r["appts"] else None, axis=1)
    geo["CPA1"] = geo.apply(lambda r: r["est_spend"] / r["showed_up"] if r["showed_up"] else None, axis=1)
    geo["CPS"] = geo.apply(lambda r: r["est_spend"] / r["sold"] if r["sold"] else None, axis=1)

    if view == "Province":
        display = geo.groupby("province").agg(
            est_spend=("est_spend",  "sum"),
            clean_leads=("clean_leads","sum"),
            appts=("appts",          "sum"),
            upcoming=("upcoming",    "sum"),
            showed_up=("showed_up",  "sum"),
            canc_before=("canc_before","sum"),
            canc_after=("canc_after", "sum"),
            sold=("sold",            "sum"),
        ).reset_index()
        display["CPL"]       = display.apply(lambda r: r["est_spend"] / r["clean_leads"] if r["clean_leads"] else None, axis=1)
        display["CPA"]       = display.apply(lambda r: r["est_spend"] / r["appts"] if r["appts"] else None, axis=1)
        display["CPA1"]      = display.apply(lambda r: r["est_spend"] / r["showed_up"] if r["showed_up"] else None, axis=1)
        display["CPS"]       = display.apply(lambda r: r["est_spend"] / r["sold"] if r["sold"] else None, axis=1)
        display["CR L→A%"]   = display.apply(lambda r: round(r["appts"] / r["clean_leads"] * 100, 1) if r["clean_leads"] else None, axis=1)
        display["Show Rate"] = display.apply(lambda r: round(r["showed_up"] / r["appts"] * 100, 1) if r["appts"] else None, axis=1)
        display = display.sort_values("clean_leads", ascending=False)
        group_col = "province"
    else:
        display = geo.copy()
        display["CR L→A%"]   = display.apply(lambda r: round(r["appts"] / r["clean_leads"] * 100, 1) if r["clean_leads"] else None, axis=1)
        display["Show Rate"] = display.apply(lambda r: round(r["showed_up"] / r["appts"] * 100, 1) if r["appts"] else None, axis=1)
        display = display.sort_values("clean_leads", ascending=False)
        group_col = "city"

    cols_to_show = [group_col, "est_spend", "clean_leads", "CPL", "appts", "CPA", "upcoming",
                    "CR L→A%", "showed_up", "CPA1", "Show Rate", "canc_before", "canc_after", "sold", "CPS"]
    display_out = display[[c for c in cols_to_show if c in display.columns]].copy()
    display_out["est_spend"] = display_out["est_spend"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display_out["CPL"]       = display_out["CPL"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display_out["CPA"]       = display_out["CPA"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display_out["CPA1"]      = display_out["CPA1"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display_out["CPS"]       = display_out["CPS"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display_out.rename(columns={
        group_col: group_col.title(), "est_spend": "Est. Spend",
        "clean_leads": "Clean Leads", "appts": "Appts", "upcoming": "Upcoming",
        "showed_up": "Showed Up", "canc_before": "Canc. Before",
        "canc_after": "Canc. After", "sold": "Sold",
    }, inplace=True)

    st.dataframe(display_out, use_container_width=True, hide_index=True)

    st.divider()

    # Bar chart — top cities
    top = display.head(15) if view == "City" else display
    fig = px.bar(
        top, x="clean_leads", y=group_col, orientation="h",
        color="cr_la" if "cr_la" in top.columns else "clean_leads",
        color_continuous_scale="Blues",
        labels={"clean_leads": "Clean Leads", group_col: ""},
        height=400,
    )
    apply_chart_style(fig, height=400)
    fig.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    # US Markets note
    us_provinces = ["California", "Oregon", "Washington", "Maine", "New York", "New York"]
    us_spend = spend_df[spend_df["province"].isin(us_provinces)]["spend"].sum()
    if us_spend > 0:
        st.divider()
        st.markdown("**🇺🇸 US Markets (Portland Test — manual statuses)**")
        us = spend_df[spend_df["province"].isin(us_provinces)].groupby("province")["spend"].sum().reset_index()
        us.columns = ["State", "Spend"]
        us["Spend"] = us["Spend"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(us, use_container_width=True, hide_index=True)
        st.caption("Lead and status data for US markets is updated manually.")


# ─────────────────────────────────────────────
#  PAGE: LEAD DETAIL
# ─────────────────────────────────────────────
elif page == "📋 Lead Detail":
    st.title("Lead Detail")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        provinces = ["All"] + sorted(combined["province"].dropna().unique().tolist())
        prov_sel = st.selectbox("Province", provinces)
    with col2:
        cities = ["All"] + sorted(combined["city"].dropna().unique().tolist())
        city_sel = st.selectbox("City", cities)
    with col3:
        statuses = ["All"] + sorted(combined["status"].dropna().unique().tolist())
        status_sel = st.selectbox("Status", statuses)
    with col4:
        show_clean = st.checkbox("Clean leads only", value=True)

    df_detail = combined.copy()
    if prov_sel   != "All": df_detail = df_detail[df_detail["province"] == prov_sel]
    if city_sel   != "All": df_detail = df_detail[df_detail["city"] == city_sel]
    if status_sel != "All": df_detail = df_detail[df_detail["status"] == status_sel]
    if show_clean:          df_detail = df_detail[df_detail["is_clean"].fillna(False)]

    # ── Source count summary ─────────────────────────────────────────────────
    leads_detail_df = df_detail[df_detail["source_type"] == "lead"]
    calls_detail_df = df_detail[df_detail["source_type"] == "call"]

    meta_count  = int((leads_detail_df["source"] == "META").sum())
    tt_count    = int((leads_detail_df["source"] == "TikTok").sum())
    aff_count   = int((leads_detail_df["source"] == "Affiliate").sum())
    other_count = int((~leads_detail_df["source"].isin(["META","TikTok","Affiliate"])).sum())
    calls_count = len(calls_detail_df)
    total_count = len(df_detail)

    sc = st.columns(6)
    sc[0].metric("Total",     f"{total_count:,}")
    sc[1].metric("META Leads",f"{meta_count:,}")
    sc[2].metric("Calls (META)", f"{calls_count:,}")
    if tt_count:  sc[3].metric("TikTok", f"{tt_count:,}")
    if aff_count: sc[4].metric("Affiliate", f"{aff_count:,}")
    if other_count: sc[5].metric("Other", f"{other_count:,}")

    # Leads table
    st.markdown(f'<p class="section-title">META Leads ({meta_count + tt_count + aff_count + other_count:,})</p>', unsafe_allow_html=True)
    leads_show = leads_detail_df[[
        "date", "phone", "email", "status", "province", "city", "source", "campaign_type", "amount"
    ]].copy()
    leads_show.columns = ["Date", "Phone", "Email", "Status", "Province", "City", "Source", "Camp. Type", "Amount"]
    st.dataframe(leads_show, use_container_width=True, hide_index=True, height=320)

    # Calls table
    st.markdown(f'<p class="section-title">Calls — first-time callers ({calls_count:,})</p>', unsafe_allow_html=True)
    calls_show = calls_detail_df[[
        "date", "phone", "status", "province", "city", "amount"
    ]].copy()
    calls_show.columns = ["Date", "Phone", "Status", "Province", "City", "Amount"]
    st.dataframe(calls_show, use_container_width=True, hide_index=True, height=220)

    # Export
    if st.button("⬇️ Export to CSV"):
        csv = df_detail.to_csv(index=False)
        st.download_button("Download CSV", csv, "ecoline_leads.csv", "text/csv")


# ─────────────────────────────────────────────
#  PAGE: FUNNEL ANALYSIS  (sliders live here)
# ─────────────────────────────────────────────
elif page == "🔄 Funnel Analysis":
    st.title("Funnel Analysis")

    # ── THE TWO SLIDERS ──────────────────────
    st.markdown("### ⚙️ Analysis Controls")
    sc1, sc2 = st.columns(2)
    with sc1:
        slider_dedup = st.slider(
            "🔁 Deduplication Window (days)",
            min_value=1, max_value=90, value=45, step=1,
            help="Number of days to look back when deduplicating leads by phone number. "
                 "Lower = stricter same-period dedup (fewer leads filtered). "
                 "Higher = more aggressive dedup (more leads filtered). "
                 "Affects: Clean Leads, CPL, CR, CPA, CPS."
        )
    with sc2:
        slider_appt = st.slider(
            "📅 Appointment Window (days)",
            min_value=1, max_value=120, value=20, step=1,
            help="Only count appointments that occurred within this many days of the lead. "
                 "Default is 20 days — matches the manual daily parsing used in Looker Studio. "
                 "Increase to 45 days to capture ~89% of all appointments in the full closing cycle."
        )

    st.info(
        f"**Dedup:** {slider_dedup} days  |  "
        f"**Appt window:** {slider_appt} days  —  "
        f"These controls only affect this page. All other pages use the global defaults in the sidebar.",
        icon="ℹ️"
    )
    st.divider()

    # Recompute with slider values
    leads_slider = apply_dedup(leads_raw[leads_raw["date"].between(start_date, end_date)].copy(), slider_dedup)
    combined_slider = pd.concat([filter_source(leads_slider), calls_f], ignore_index=True)
    f = compute_funnel(combined_slider, slider_appt)

    # KPI row
    st.markdown("### 📊 Funnel Metrics")
    cols = st.columns(8)
    kpis = [
        ("All Leads",     f['all_leads']),
        ("Clean Leads",   f['clean_leads']),
        ("Appointments",  f['appts']),
        ("Upcoming",      f['upcoming']),
        ("Canc. Before",  f['canc_before']),
        ("Canc. After",   f['canc_after']),
        ("Sold",          f['sold']),
        ("Show Rate",     f"{f['show_rate']}%"),
    ]
    for col, (label, val) in zip(cols, kpis):
        with col:
            st.metric(label, val if isinstance(val, str) else f"{val:,}")

    st.divider()

    # Funnel chart
    st.markdown("### 🔽 Conversion Funnel")
    funnel_stages = [
        ("Clean Leads",  f['clean_leads'],             BLUE),
        ("Appointments", f['appts'],                   AMBER),
        ("Showed Up",    f['appts'] - f['canc_before'], PURPLE),
        ("Sold",         f['sold'],                    GREEN),
    ]
    fig_funnel = go.Figure(go.Funnel(
        y=[s[0] for s in funnel_stages],
        x=[s[1] for s in funnel_stages],
        marker_color=[s[2] for s in funnel_stages],
        textinfo="value+percent initial",
        textfont=dict(size=13, family="Inter, sans-serif"),
        connector=dict(line=dict(color="#E2E8F0", width=1)),
    ))
    apply_chart_style(fig_funnel, height=320)
    st.plotly_chart(fig_funnel, use_container_width=True)

    st.divider()

    # ── APPOINTMENT TIMING HISTOGRAM ─────────
    st.markdown("### 📅 Appointment Timing Distribution")
    st.caption(f"Green line = selected window ({slider_appt} days, default 20). "
               f"Shows how appointments spread out over time after the lead date.")

    # Include sold records even if appointment date is missing (use sold date as fallback)
    has_appt = combined_slider["cf_appointment_date"].notna() | (combined_slider["status"] == "sold")
    eff_dt = pd.to_datetime(combined_slider["cf_appointment_date"]).fillna(
        pd.to_datetime(combined_slider["cf_sold_date"]) if "cf_sold_date" in combined_slider.columns
        else pd.Series(pd.NaT, index=combined_slider.index)
    )
    days_arr = (
        eff_dt[has_appt] - combined_slider.loc[has_appt, "dt"].dt.tz_localize(None)
    ).dt.days
    days_arr = days_arr[(days_arr >= 0) & (days_arr <= 120)]

    if not days_arr.empty:
        hist_df = days_arr.value_counts().sort_index().reset_index()
        hist_df.columns = ["days", "count"]
        hist_df["cumulative_pct"] = hist_df["count"].cumsum() / hist_df["count"].sum() * 100

        fig_hist = go.Figure()
        fig_hist.add_trace(go.Bar(
            x=hist_df["days"], y=hist_df["count"],
            marker_color=BLUE2, name="Appointments",
            marker_line_width=0, opacity=0.85,
        ))
        fig_hist.add_vline(x=slider_appt, line_color=GREEN, line_width=2,
                           annotation_text=f"{slider_appt}d window",
                           annotation_position="top right",
                           annotation_font=dict(color=GREEN, size=11))
        # Show a reference line at 45 days (full closing cycle) when not already selected
        if slider_appt != 45:
            fig_hist.add_vline(x=45, line_color=GRAY, line_dash="dot", line_width=1.5,
                               annotation_text="45d (full cycle)",
                               annotation_position="top right",
                               annotation_font=dict(color=GRAY, size=11))
        apply_chart_style(fig_hist, height=300)
        fig_hist.update_layout(
            xaxis=dict(title="Days from lead to appointment"),
            yaxis=dict(title="Appointments"),
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        # Cumulative summary
        pct_at_slider = hist_df[hist_df["days"] <= slider_appt]["count"].sum() / hist_df["count"].sum() * 100
        pct_at_45     = hist_df[hist_df["days"] <= 45]["count"].sum() / hist_df["count"].sum() * 100
        c1, c2, c3 = st.columns(3)
        c1.metric(f"At {slider_appt}d (current window)", f"{pct_at_slider:.1f}%", "of appointments captured")
        c2.metric("At 45d (full closing cycle)",          f"{pct_at_45:.1f}%",    "of appointments captured")
        c3.metric("Beyond selected window",               f"{100 - pct_at_slider:.1f}%", "not yet counted")

    st.divider()

    # Dedup impact summary
    st.markdown("### 🔁 Deduplication Impact")
    all_in_range  = leads_raw[leads_raw["date"].between(start_date, end_date)]
    leads_slider_clean = leads_slider[leads_slider["is_clean"].fillna(False)]["row_num"].count()
    leads_dirty   = len(all_in_range)
    st.info(
        f"With **{slider_dedup}-day dedup**: **{leads_slider_clean:,}** clean leads "
        f"out of **{leads_dirty:,}** total form leads "
        f"({round(leads_slider_clean/leads_dirty*100,1) if leads_dirty else 0}% pass rate). "
        f"**{leads_dirty - leads_slider_clean:,}** filtered as duplicates."
    )


# ─────────────────────────────────────────────
#  PAGE: CAMPAIGN INTELLIGENCE
# ─────────────────────────────────────────────
elif page == "📱 Campaign Intelligence":
    st.title("Campaign Intelligence")
    st.caption("META campaigns only · Spend, leads and funnel by campaign → adset → ad")

    camp_type_filter = st.segmented_control("Campaign Type", ["All", "LG", "CONV", "Other"], default="All")

    # Build campaign table from leads
    camp_df = leads_f[leads_f["source"] == "META"].copy()
    if camp_type_filter != "All":
        camp_df = camp_df[camp_df["campaign_type"] == camp_type_filter]

    if camp_df.empty:
        st.warning("No campaign data for the selected filters.")
    else:
        camp_agg = pd.DataFrame([
            {"utm_campaign": camp, **compute_funnel(grp)}
            for camp, grp in camp_df.groupby("utm_campaign")
        ])
        # Total spend is unknown per campaign (META doesn't break spend by campaign in the data)
        camp_agg = camp_agg.rename(columns={"utm_campaign": "Campaign"})
        camp_agg["CR L→A%"] = camp_agg["cr_la"]
        camp_agg["CR A→S%"] = camp_agg["cr_as"]
        camp_agg["Show Rate"] = camp_agg.apply(
            lambda r: round(r["showed_up"] / r["appts"] * 100, 1) if r["appts"] else None, axis=1
        )
        camp_agg = camp_agg.sort_values("clean_leads", ascending=False)

        display_cols = ["Campaign", "all_leads", "clean_leads", "appts", "upcoming",
                        "CR L→A%", "showed_up", "Show Rate", "canc_before", "canc_after",
                        "sold", "CR A→S%"]
        display_camp = camp_agg[[c for c in display_cols if c in camp_agg.columns]].copy()
        display_camp.rename(columns={
            "all_leads": "All Leads", "clean_leads": "Clean Leads",
            "appts": "Appts", "upcoming": "Upcoming", "showed_up": "Showed Up",
            "canc_before": "Canc. Before", "canc_after": "Canc. After", "sold": "Sold",
        }, inplace=True)

        st.markdown('<p class="section-title">Campaign Performance</p>', unsafe_allow_html=True)
        st.caption(f"{len(display_camp)} campaigns")
        st.dataframe(display_camp, use_container_width=True, hide_index=True, height=420)

        # Top campaigns chart
        top_camp = camp_agg.head(10)
        fig_camp = px.bar(
            top_camp, x="clean_leads", y="Campaign", orientation="h",
            color="cr_la", color_continuous_scale="Blues",
            labels={"clean_leads": "Clean Leads", "cr_la": "CR L→A%"},
            height=350,
        )
        apply_chart_style(fig_camp, height=350)
        fig_camp.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_camp, use_container_width=True)

    st.caption("ℹ️ Spend per campaign is not available in BigQuery — only total spend is tracked. "
               "Campaign-level CPL/CPA/CPS will be available once META campaign spend is extracted.")


# ─────────────────────────────────────────────
#  PAGE: SOURCE COMPARISON
# ─────────────────────────────────────────────
elif page == "⚖️ Source Comparison":
    st.title("Source Comparison")
    st.caption("All sources side by side — META (includes inbound calls), TikTok, Other")

    src_groups = combined.groupby("source").apply(
        lambda grp: pd.Series(compute_funnel(grp))
    ).reset_index()

    # Add spend for META
    total_spend = spend_daily["spend"].sum()
    src_groups["spend"] = src_groups["source"].apply(
        lambda s: total_spend if s == "META" else 0
    )
    src_groups["CPL"] = src_groups.apply(
        lambda r: r["spend"] / r["clean_leads"] if r["clean_leads"] and r["spend"] else None, axis=1
    )
    src_groups["CPA"] = src_groups.apply(
        lambda r: r["spend"] / r["appts"] if r["appts"] and r["spend"] else None, axis=1
    )
    src_groups["CPA1"] = src_groups.apply(
        lambda r: r["spend"] / r["showed_up"] if r["showed_up"] and r["spend"] else None, axis=1
    )
    src_groups["CPS"] = src_groups.apply(
        lambda r: r["spend"] / r["sold"] if r["sold"] and r["spend"] else None, axis=1
    )
    src_groups["Show Rate%"] = src_groups.apply(
        lambda r: round(r["showed_up"] / r["appts"] * 100, 1) if r["appts"] else None, axis=1
    )

    # Summary cards
    cols = st.columns(len(src_groups))
    for col, (_, row) in zip(cols, src_groups.iterrows()):
        with col:
            st.markdown(f"**{row['source']}**")
            st.metric("Clean Leads",  f"{int(row['clean_leads']):,}")
            st.metric("Appointments", f"{int(row['appts']):,}")
            st.metric("Upcoming",     f"{int(row['upcoming']):,}")
            st.metric("Showed Up",    f"{int(row['showed_up']):,}")
            st.metric("CR L→A",       f"{row['cr_la']}%")
            st.metric("Sold",         f"{int(row['sold']):,}")
            if row["spend"] > 0:
                st.metric("Spend", f"${row['spend']:,.0f}")
                st.metric("CPL",   f"${row['CPL']:,.0f}" if row["CPL"] else "—")
                st.metric("CPA",   f"${row['CPA']:,.0f}" if row["CPA"] else "—")
                st.metric("CPA1",  f"${row['CPA1']:,.0f}" if row["CPA1"] else "—")
                st.metric("CPS",   f"${row['CPS']:,.0f}" if row["CPS"] else "—")

    st.divider()

    # Comparison table
    display_src = src_groups[[
        "source", "spend", "all_leads", "clean_leads", "CPL",
        "appts", "CPA", "upcoming", "cr_la", "showed_up", "CPA1", "Show Rate%",
        "canc_before", "canc_after", "sold", "CPS"
    ]].copy()
    display_src.rename(columns={
        "source": "Source", "spend": "Spend", "all_leads": "All Leads",
        "clean_leads": "Clean Leads", "appts": "Appts", "upcoming": "Upcoming",
        "cr_la": "CR L→A%", "showed_up": "Showed Up",
        "canc_before": "Canc. Before", "canc_after": "Canc. After", "sold": "Sold",
    }, inplace=True)
    display_src["Spend"] = display_src["Spend"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display_src["CPL"]   = display_src["CPL"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display_src["CPA"]   = display_src["CPA"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display_src["CPA1"]  = display_src["CPA1"].apply(lambda x: f"${x:,.0f}" if x else "—")
    display_src["CPS"]   = display_src["CPS"].apply(lambda x: f"${x:,.0f}" if x else "—")
    st.dataframe(display_src, use_container_width=True, hide_index=True)

    # CR comparison chart
    fig_src = px.bar(
        src_groups, x="source", y=["cr_la", "cr_as"],
        barmode="group",
        labels={"value": "Rate (%)", "source": "Source", "variable": "Metric"},
        color_discrete_map={"cr_la": BLUE, "cr_as": GREEN},
        height=300,
    )
    apply_chart_style(fig_src, height=300, legend_bottom=True)
    st.plotly_chart(fig_src, use_container_width=True)

    # ── Calls breakout (within their parent source) ──────────────────────────
    calls_only = combined[combined["source_type"] == "call"]
    if not calls_only.empty:
        with st.expander("📞 Calls Breakdown (within source)", expanded=False):
            st.caption(
                "Inbound calls attributed to their parent source (META, Affiliate, etc.). "
                "These are already included in the source totals above."
            )
            call_groups = calls_only.groupby("source").apply(
                lambda grp: pd.Series(compute_funnel(grp))
            ).reset_index()
            call_groups["Show Rate%"] = call_groups.apply(
                lambda r: round(r["showed_up"] / r["appts"] * 100, 1) if r["appts"] else None, axis=1
            )
            call_display = call_groups[[
                "source", "all_leads", "clean_leads",
                "appts", "upcoming", "cr_la", "showed_up", "Show Rate%",
                "canc_before", "canc_after", "sold",
            ]].copy()
            call_display.rename(columns={
                "source": "Source", "all_leads": "Calls (Total)",
                "clean_leads": "Clean Calls", "appts": "Appts",
                "upcoming": "Upcoming", "cr_la": "CR L→A%",
                "showed_up": "Showed Up", "canc_before": "Canc. Before",
                "canc_after": "Canc. After", "sold": "Sold",
            }, inplace=True)
            st.dataframe(call_display, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
#  PAGE: CROSS-CHANNEL  (Eco ↔ Affiliate)
# ─────────────────────────────────────────────
elif page == "🔗 Cross-Channel":
    st.title("Cross-Channel Analytics")
    st.caption(
        f"Ecoline ↔ Affiliate overlap & attribution  ·  "
        f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d, %Y')}"
    )

    # ── Load data ───────────────────────────────────────────────────
    xc_raw = load_cross_channel(start_date, end_date)
    if xc_raw.empty:
        st.warning("No cross-channel data for this period.")
    else:
        overlap_leads = compute_overlap(xc_raw)
        cannibal = cannibalization_analysis(overlap_leads)
        seg = cannibal.get("segments", {})

        # ── 1. TOP KPIs ────────────────────────────────────────────
        st.markdown("### 📊 Overview")
        n_eco   = seg.get("eco_only", {}).get("leads", 0)
        n_aff   = seg.get("aff_only", {}).get("leads", 0)
        n_ovl   = seg.get("overlap", {}).get("leads", 0)
        n_total = n_eco + n_aff + n_ovl

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Unique Leads", f"{n_total:,}")
        k2.metric("Eco Only", f"{n_eco:,}", f"{round(n_eco/n_total*100,1) if n_total else 0}%")
        k3.metric("Aff Only", f"{n_aff:,}", f"{round(n_aff/n_total*100,1) if n_total else 0}%")
        k4.metric("Overlap", f"{n_ovl:,}", f"{round(n_ovl/n_total*100,1) if n_total else 0}%")

        # ── 2. VENN VISUAL ──────────────────────────────────────────
        st.markdown("### 🔵 Channel Overlap")
        fig_venn = go.Figure()

        # Eco circle (left)
        fig_venn.add_shape(type="circle", x0=0, y0=0, x1=3, y1=3,
                           fillcolor="rgba(99, 110, 250, 0.3)", line_color="rgba(99, 110, 250, 0.8)")
        # Aff circle (right, overlapping)
        fig_venn.add_shape(type="circle", x0=1.5, y0=0, x1=4.5, y1=3,
                           fillcolor="rgba(239, 85, 59, 0.3)", line_color="rgba(239, 85, 59, 0.8)")
        # Labels
        fig_venn.add_annotation(x=0.9, y=1.5, text=f"<b>Eco Only</b><br>{n_eco:,}", showarrow=False,
                                font=dict(size=14, color="#636EFA"))
        fig_venn.add_annotation(x=2.25, y=1.5, text=f"<b>Overlap</b><br>{n_ovl:,}", showarrow=False,
                                font=dict(size=14, color="#333"))
        fig_venn.add_annotation(x=3.6, y=1.5, text=f"<b>Aff Only</b><br>{n_aff:,}", showarrow=False,
                                font=dict(size=14, color="#EF553B"))

        fig_venn.update_layout(
            height=250, margin=dict(l=20, r=20, t=10, b=10),
            xaxis=dict(visible=False, range=[-0.5, 5]),
            yaxis=dict(visible=False, range=[-0.5, 3.5], scaleanchor="x"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_venn, use_container_width=True)

        # ── 3. CANNIBALIZATION vs SYNERGY ───────────────────────────
        st.markdown("### ⚡ Synergy vs Cannibalization")
        verdict = cannibal.get("verdict", "neutral")
        lift = cannibal.get("synergy_lift_appt", 0)
        if verdict == "synergy":
            st.success(f"**SYNERGY** — Overlap leads convert to appointments **+{lift}pp** better than single-channel average")
        elif verdict == "cannibalization":
            st.error(f"**CANNIBALIZATION** — Overlap leads convert **{lift}pp** worse than single-channel average")
        else:
            st.info("**NEUTRAL** — No significant difference between overlap and single-channel conversion")

        # Segment comparison table
        seg_data = []
        for s_name, s_label in [("eco_only", "Eco Only"), ("aff_only", "Aff Only"), ("overlap", "Overlap (both)")]:
            s = seg.get(s_name, {})
            seg_data.append({
                "Segment": s_label,
                "Leads": s.get("leads", 0),
                "CR → Appt": f"{s.get('cr_appt', 0)}%",
                "CR → Sold": f"{s.get('cr_sold', 0)}%",
                "Avg Touches": s.get("avg_touches", 0),
                "Revenue": f"${s.get('total_revenue', 0):,.0f}",
            })
        st.dataframe(pd.DataFrame(seg_data), use_container_width=True, hide_index=True)

        # ── 4. MULTI-TOUCH ATTRIBUTION ──────────────────────────────
        st.markdown("### 🏷️ Attribution Models")
        st.caption("Compare how credit is split between Eco and Affiliate across 3 models")

        # Linear
        lin = linear_attribution(xc_raw)
        # First-touch / Last-touch
        ft_lt = touch_attribution(xc_raw)

        if not lin.empty and not ft_lt.empty:
            attr_tab1, attr_tab2 = st.tabs(["📊 Summary", "📋 Detail"])

            with attr_tab1:
                # Build comparison chart
                attr_chart_data = []
                for _, r in lin.iterrows():
                    attr_chart_data.append({"Channel": r["channel"].upper(), "Model": "Linear",
                                            "Attributed Sold": round(r["attributed_sold"], 1)})
                for _, r in ft_lt.iterrows():
                    attr_chart_data.append({"Channel": r["channel"].upper(), "Model": r["model"].replace("_", " ").title(),
                                            "Attributed Sold": round(r["attributed_sold"], 1)})

                fig_attr = px.bar(
                    pd.DataFrame(attr_chart_data),
                    x="Model", y="Attributed Sold", color="Channel",
                    barmode="group",
                    color_discrete_map={"ECO": "#636EFA", "AFF": "#EF553B"},
                    title="Attributed Sales by Model",
                )
                fig_attr.update_layout(height=350)
                st.plotly_chart(fig_attr, use_container_width=True)

            with attr_tab2:
                st.markdown("**Linear Attribution** (equal credit per touch)")
                lin_display = lin.copy()
                lin_display.columns = ["Channel", "Leads", "Appts", "Sold", "Revenue ($)", "Total Touches"]
                lin_display["Channel"] = lin_display["Channel"].str.upper()
                lin_display["Leads"] = lin_display["Leads"].round(0).astype(int)
                lin_display["Appts"] = lin_display["Appts"].round(0).astype(int)
                lin_display["Sold"] = lin_display["Sold"].round(1)
                lin_display["Revenue ($)"] = lin_display["Revenue ($)"].apply(lambda x: f"${x:,.0f}")
                st.dataframe(lin_display, use_container_width=True, hide_index=True)

                st.markdown("**First-Touch & Last-Touch Attribution**")
                ft_display = ft_lt.copy()
                ft_display.columns = ["Channel", "Sold", "Revenue ($)", "Total Leads", "Model"]
                ft_display["Channel"] = ft_display["Channel"].str.upper()
                ft_display["Revenue ($)"] = ft_display["Revenue ($)"].apply(lambda x: f"${x:,.0f}")
                ft_display = ft_display[["Model", "Channel", "Total Leads", "Sold", "Revenue ($)"]]
                ft_display["Model"] = ft_display["Model"].str.replace("_", " ").str.title()
                st.dataframe(ft_display, use_container_width=True, hide_index=True)

        # ── 5. CONVERSION BY TOUCHPOINT GAP ─────────────────────────
        st.markdown("### ⏱️ Optimal Touchpoint Window")
        st.caption("How does the gap between first Eco touch and first Aff touch affect conversion?")

        gap_data = conversion_by_gap(overlap_leads)
        if not gap_data.empty:
            gc1, gc2 = st.columns(2)
            with gc1:
                fig_gap_cr = px.bar(
                    gap_data, x="gap_bucket", y="cr_appt",
                    title="CR → Appointment by Gap",
                    labels={"gap_bucket": "Days Between Touches", "cr_appt": "CR (%)"},
                    color_discrete_sequence=["#636EFA"],
                )
                fig_gap_cr.update_layout(height=300)
                st.plotly_chart(fig_gap_cr, use_container_width=True)
            with gc2:
                fig_gap_sold = px.bar(
                    gap_data, x="gap_bucket", y="cr_sold",
                    title="CR → Sold by Gap",
                    labels={"gap_bucket": "Days Between Touches", "cr_sold": "CR (%)"},
                    color_discrete_sequence=["#EF553B"],
                )
                fig_gap_sold.update_layout(height=300)
                st.plotly_chart(fig_gap_sold, use_container_width=True)

            st.dataframe(
                gap_data.rename(columns={
                    "gap_bucket": "Gap", "leads": "Leads", "appts": "Appts",
                    "sold": "Sold", "cr_appt": "CR→Appt %", "cr_sold": "CR→Sold %",
                    "avg_revenue": "Avg Revenue",
                }),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("Not enough overlap leads to analyze touchpoint windows.")

        # ── 6. GEO BREAKDOWN ────────────────────────────────────────
        st.markdown("### 🗺️ Geographic Overlap")
        geo_level = st.radio("Group by", ["province", "city"], horizontal=True, key="xc_geo_level")
        geo_data = geo_overlap(overlap_leads, level=geo_level)
        if not geo_data.empty:
            geo_top = geo_data.head(20)

            fig_geo = px.bar(
                geo_top, x=geo_level, y=["eco_only", "aff_only", "overlap"],
                title=f"Lead Distribution by {geo_level.title()}",
                barmode="stack",
                color_discrete_map={"eco_only": "#636EFA", "aff_only": "#EF553B", "overlap": "#AB63FA"},
                labels={geo_level: geo_level.title()},
            )
            fig_geo.update_layout(height=400)
            st.plotly_chart(fig_geo, use_container_width=True)

            geo_display = geo_data.copy()
            geo_display.columns = [
                geo_level.title(), "Total Leads", "Eco Only", "Aff Only", "Overlap",
                "Appts", "Sold", "Revenue", "Overlap %", "CR→Appt %", "CR→Sold %",
            ]
            geo_display["Revenue"] = geo_display["Revenue"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "—")
            st.dataframe(geo_display, use_container_width=True, hide_index=True)

        # ── 7. MONTHLY OVERLAP TREND ────────────────────────────────
        st.markdown("### 📈 Overlap Trend (Monthly)")
        st.caption("New leads appearing in both channels per month (full history)")

        trend_data = load_monthly_overlap_trend()
        if not trend_data.empty:
            fig_trend = px.area(
                trend_data, x="month", y="new_overlaps",
                title="Monthly New Cross-Channel Overlaps",
                labels={"month": "Month", "new_overlaps": "New Overlaps"},
                color_discrete_sequence=["#AB63FA"],
            )
            fig_trend.update_layout(height=300)
            st.plotly_chart(fig_trend, use_container_width=True)


# ─────────────────────────────────────────────
#  PAGE: CREATIVE PERFORMANCE
# ─────────────────────────────────────────────
elif page == "🎨 Creative Performance":
    st.title("Creative Performance")
    st.caption(
        "Breakdown by creative type (IMAGE / VIDEO / DCO) and hypothesis. "
        "Tracks booking rate, close rate, revenue per lead, and average sale size."
    )
    st.info(
        "💡 **NEW: Placement + Ad Copy tabs** — see spend breakdown by FB Feed / IG Stories / Reels, "
        "and analyze creative messaging angles. Data from Meta API (Jan 2024+, cached daily). "
        "Rows marked with 🔍 have data quality notes — check the flags column."
    )

    # ── Parse creative type and hypothesis from utm_content ──
    import re as _re

    _creative_df = leads_f[leads_f["is_clean"]].copy()

    def _parse_creative_type(val):
        if pd.isna(val):
            return "Unknown"
        v = str(val).upper()
        if v.startswith("DCO") and "IMAGE" in v:
            return "DCO-IMAGE"
        if v.startswith("DCO") and "VIDEO" in v:
            return "DCO-VIDEO"
        if v.startswith("IMAGE") or v.startswith("DCO - IMAGE"):
            return "IMAGE"
        if v.startswith("VIDEO") or v.startswith("DCO - VIDEO"):
            return "VIDEO"
        if "IMAGE" in v:
            return "IMAGE"
        if "VIDEO" in v:
            return "VIDEO"
        return "Other"

    def _parse_hypothesis(val):
        if pd.isna(val):
            return None
        v = str(val)
        # "0 Down" special case
        if "0 down" in v.lower() or "0down" in v.lower():
            return "Hyp 0 Down"
        m = _re.search(r'Hyp\s*([\d.]+)', v, _re.IGNORECASE)
        if m:
            return f"Hyp {m.group(1)}"
        return None

    def _parse_funnel_type(val):
        if pd.isna(val):
            return "Other"
        v = str(val).lower()
        if "form m/i" in v or "form mi" in v:
            return "Lead Form"
        if "hard form" in v:
            return "Hard Form"
        if "cost cap" in v:
            return "Quiz (Cost Cap)"
        if "bid cap" in v:
            return "Quiz (Bid Cap)"
        if "aff" in v and ("form" in v or "creo" in v):
            return "Affiliate"
        return "Other"

    _creative_df["creative_type"] = _creative_df["utm_content"].apply(_parse_creative_type)
    _creative_df["hypothesis"] = _creative_df["utm_content"].apply(_parse_hypothesis)
    _creative_df["funnel_type"] = _creative_df["utm_term"].apply(_parse_funnel_type) if "utm_term" in _creative_df.columns else "Unknown"

    # Status helpers
    _creative_df["is_booked"] = _creative_df["status"].isin(["appointment", "sold", "cancelled", "cancelled before appt"])
    _creative_df["is_happened"] = _creative_df["status"].isin(["sold", "cancelled"])
    _creative_df["is_sold"] = _creative_df["status"] == "sold"
    _creative_df["revenue"] = pd.to_numeric(_creative_df["amount"], errors="coerce").fillna(0)
    _creative_df.loc[~_creative_df["is_sold"], "revenue"] = 0

    # ── Total spend context ──
    _total_meta_spend = spend_df[spend_df["spend"] > 0]["spend"].sum() if len(spend_df) > 0 else 0
    _total_creative_leads = len(_creative_df)
    if _total_meta_spend > 0:
        _context_cols = st.columns(4)
        with _context_cols[0]:
            st.metric("Total Meta Spend (period)", f"${_total_meta_spend:,.0f}")
        with _context_cols[1]:
            st.metric("Total Leads (deduped)", f"{_total_creative_leads:,}")
        with _context_cols[2]:
            _avg_cpl = _total_meta_spend / _total_creative_leads if _total_creative_leads > 0 else 0
            st.metric("Avg CPL (all)", f"${_avg_cpl:,.0f}")
        with _context_cols[3]:
            _total_rev = _creative_df["revenue"].sum()
            st.metric("Total Revenue", f"${_total_rev:,.0f}")
        st.divider()

    # ── Load placement + creative CSVs (Meta API cache) ──
    import os as _os
    _data_dir = _os.path.join(_os.path.dirname(__file__), "data")
    _placements_csv = _os.path.join(_data_dir, "meta_placements.csv")
    _creatives_csv = _os.path.join(_data_dir, "meta_creatives.csv")
    _has_placement_data = _os.path.exists(_placements_csv)
    _has_creative_data = _os.path.exists(_creatives_csv)

    if _has_placement_data:
        _plc_df = pd.read_csv(_placements_csv)
    if _has_creative_data:
        _cre_df = pd.read_csv(_creatives_csv)

    # ── TAB 1: IMAGE vs VIDEO ──
    _tab_names = ["IMAGE vs VIDEO", "By Hypothesis", "By Funnel Type"]
    if _has_placement_data:
        _tab_names.append("📍 By Placement")
    if _has_creative_data:
        _tab_names.append("📝 Ad Copy")
    _tab_names.append("Detail Explorer")

    _all_tabs = st.tabs(_tab_names)
    _ti = 0
    tab_type = _all_tabs[_ti]; _ti += 1
    tab_hyp = _all_tabs[_ti]; _ti += 1
    tab_funnel = _all_tabs[_ti]; _ti += 1
    tab_placement = _all_tabs[_ti] if _has_placement_data else None; _ti += (1 if _has_placement_data else 0)
    tab_copy = _all_tabs[_ti] if _has_creative_data else None; _ti += (1 if _has_creative_data else 0)
    tab_detail = _all_tabs[_ti]

    with tab_type:
        st.subheader("IMAGE vs VIDEO Performance")
        _type_filter = _creative_df[_creative_df["creative_type"].isin(["IMAGE", "VIDEO", "DCO-IMAGE", "DCO-VIDEO"])]
        # Group IMAGE + DCO-IMAGE vs VIDEO + DCO-VIDEO
        _type_filter["type_group"] = _type_filter["creative_type"].apply(
            lambda x: "IMAGE (incl. DCO)" if "IMAGE" in x else "VIDEO (incl. DCO)"
        )
        _type_agg = _type_filter.groupby("type_group").agg(
            leads=("row_num", "count"),
            booked=("is_booked", "sum"),
            happened=("is_happened", "sum"),
            sold=("is_sold", "sum"),
            revenue=("revenue", "sum"),
        ).reset_index()
        _type_agg["dirty_rate"] = (_type_agg["booked"] / _type_agg["leads"] * 100).round(1)
        _type_agg["clean_rate"] = (_type_agg["happened"] / _type_agg["leads"] * 100).round(1)
        _type_agg["close_rate"] = (_type_agg["sold"] / _type_agg["leads"] * 100).round(1)
        _type_agg["rev_per_lead"] = (_type_agg["revenue"] / _type_agg["leads"]).round(0)
        _type_agg["cost_per_sale"] = (_type_agg["revenue"] / _type_agg["sold"].replace(0, float("nan"))).round(0)

        c1, c2, c3, c4 = st.columns(4)
        for idx, row in _type_agg.iterrows():
            label = row["type_group"]
            if "IMAGE" in label:
                with c1:
                    st.metric("IMAGE Leads", f"{int(row['leads']):,}")
                with c2:
                    st.metric("IMAGE Dirty Rate", f"{row['dirty_rate']}%")
                with c3:
                    st.metric("IMAGE Close Rate", f"{row['close_rate']}%")
                with c4:
                    st.metric("IMAGE Revenue", f"${row['revenue']:,.0f}")
            else:
                with c1:
                    st.metric("VIDEO Leads", f"{int(row['leads']):,}")
                with c2:
                    st.metric("VIDEO Dirty Rate", f"{row['dirty_rate']}%")
                with c3:
                    st.metric("VIDEO Close Rate", f"{row['close_rate']}%")
                with c4:
                    st.metric("VIDEO Revenue", f"${row['revenue']:,.0f}")

        st.divider()
        _type_display = _type_agg[["type_group", "leads", "booked", "dirty_rate", "happened", "clean_rate", "sold", "close_rate", "revenue", "rev_per_lead"]].copy()
        _type_display.columns = ["Type", "Leads", "Dirty Appts", "Dirty %", "Clean Appts", "Clean %", "Sold", "Close %", "Revenue", "Rev/Lead"]
        _type_display["Revenue"] = _type_display["Revenue"].apply(lambda x: f"${x:,.0f}")
        _type_display["Rev/Lead"] = _type_display["Rev/Lead"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(_type_display, use_container_width=True, hide_index=True)

        # Also show pure IMAGE vs pure VIDEO vs DCO breakdown
        st.subheader("Detailed: Pure IMAGE / VIDEO / DCO")
        _detail_type = _type_filter.groupby("creative_type").agg(
            leads=("row_num", "count"),
            booked=("is_booked", "sum"),
            sold=("is_sold", "sum"),
            revenue=("revenue", "sum"),
        ).reset_index()
        _detail_type["dirty_rate"] = (_detail_type["booked"] / _detail_type["leads"] * 100).round(1)
        _detail_type["close_rate"] = (_detail_type["sold"] / _detail_type["leads"] * 100).round(1)
        _detail_type["rev_per_lead"] = (_detail_type["revenue"] / _detail_type["leads"]).round(0)
        _detail_disp = _detail_type[["creative_type", "leads", "dirty_rate", "close_rate", "sold", "revenue", "rev_per_lead"]].copy()
        _detail_disp.columns = ["Creative Type", "Leads", "Dirty %", "Close %", "Sold", "Revenue", "Rev/Lead"]
        _detail_disp["Revenue"] = _detail_disp["Revenue"].apply(lambda x: f"${x:,.0f}")
        _detail_disp["Rev/Lead"] = _detail_disp["Rev/Lead"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(_detail_disp, use_container_width=True, hide_index=True)

    # ── TAB 2: BY HYPOTHESIS ──
    with tab_hyp:
        st.subheader("Hypothesis Performance")

        _min_leads = st.slider("Minimum leads to show", 10, 200, 50, step=10)

        _creative_type_filter = st.multiselect(
            "Creative type",
            ["IMAGE", "VIDEO", "DCO-IMAGE", "DCO-VIDEO", "Other"],
            default=["IMAGE", "DCO-IMAGE"],
        )

        _hyp_df = _creative_df[
            _creative_df["hypothesis"].notna() &
            _creative_df["creative_type"].isin(_creative_type_filter)
        ]

        _hyp_agg = _hyp_df.groupby("hypothesis").agg(
            leads=("row_num", "count"),
            booked=("is_booked", "sum"),
            happened=("is_happened", "sum"),
            sold=("is_sold", "sum"),
            revenue=("revenue", "sum"),
        ).reset_index()
        _hyp_agg = _hyp_agg[_hyp_agg["leads"] >= _min_leads].copy()
        _hyp_agg["dirty_rate"] = (_hyp_agg["booked"] / _hyp_agg["leads"] * 100).round(1)
        _hyp_agg["clean_rate"] = (_hyp_agg["happened"] / _hyp_agg["leads"] * 100).round(1)
        _hyp_agg["close_rate"] = (_hyp_agg["sold"] / _hyp_agg["leads"] * 100).round(1)
        _hyp_agg["rev_per_lead"] = (_hyp_agg["revenue"] / _hyp_agg["leads"]).round(0)
        _hyp_agg["avg_sale"] = (_hyp_agg["revenue"] / _hyp_agg["sold"].replace(0, float("nan"))).round(0)

        # ── Data quality flags ──
        _overall_dirty = _hyp_agg["booked"].sum() / _hyp_agg["leads"].sum() * 100 if _hyp_agg["leads"].sum() > 0 else 0
        _overall_close = _hyp_agg["sold"].sum() / _hyp_agg["leads"].sum() * 100 if _hyp_agg["leads"].sum() > 0 else 0
        _avg_sale_overall = _hyp_agg["revenue"].sum() / _hyp_agg["sold"].sum() if _hyp_agg["sold"].sum() > 0 else 0

        def _quality_flag(row):
            flags = []
            if row["leads"] < 30:
                flags.append("⚠️ Small sample (<30 leads) — low confidence")
            if row["sold"] == 0:
                flags.append("⚠️ Zero sales — too early or low-intent")
            elif row["close_rate"] > _overall_close * 2.5 and row["leads"] < 100:
                flags.append("🔍 Close rate 2.5x above avg — verify with small sample")
            if row["dirty_rate"] > 55:
                flags.append("🔍 Very high booking rate (>55%) — check if UTM naming is shared with other campaigns")
            if pd.notna(row["avg_sale"]) and row["avg_sale"] > _avg_sale_overall * 2:
                flags.append("🔍 Avg sale 2x above norm — could be outlier deals")
            if pd.notna(row["avg_sale"]) and row["avg_sale"] < _avg_sale_overall * 0.4 and row["sold"] >= 3:
                flags.append("🔍 Avg sale well below norm — check deal quality")
            return " | ".join(flags) if flags else "✅"

        _hyp_agg["flags"] = _hyp_agg.apply(_quality_flag, axis=1)

        _sort_col = st.selectbox("Sort by", ["dirty_rate", "close_rate", "revenue", "leads", "rev_per_lead"], index=0)
        _hyp_agg = _hyp_agg.sort_values(_sort_col, ascending=False)

        _hyp_display = _hyp_agg[["hypothesis", "leads", "booked", "dirty_rate", "happened", "clean_rate", "sold", "close_rate", "revenue", "rev_per_lead", "avg_sale", "flags"]].copy()
        _hyp_display.columns = ["Hypothesis", "Leads", "Dirty Appts", "Dirty %", "Clean Appts", "Clean %", "Sold", "Close %", "Revenue", "Rev/Lead", "Avg Sale", "Data Quality"]
        _hyp_display["Revenue"] = _hyp_display["Revenue"].apply(lambda x: f"${x:,.0f}")
        _hyp_display["Rev/Lead"] = _hyp_display["Rev/Lead"].apply(lambda x: f"${x:,.0f}")
        _hyp_display["Avg Sale"] = _hyp_display["Avg Sale"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "—")
        st.dataframe(_hyp_display, use_container_width=True, hide_index=True, height=600)

        # Show flagged rows separately
        _flagged = _hyp_agg[_hyp_agg["flags"] != "✅"]
        if len(_flagged) > 0:
            with st.expander(f"🔍 Data Quality Notes ({len(_flagged)} hypotheses flagged)"):
                for _, row in _flagged.iterrows():
                    st.markdown(f"**{row['hypothesis']}** ({int(row['leads'])} leads, {int(row['sold'])} sold): {row['flags']}")

        # Chart: top hypotheses by dirty rate
        if len(_hyp_agg) > 0:
            import plotly.graph_objects as go
            _top = _hyp_agg.head(15)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=_top["hypothesis"], y=_top["dirty_rate"], name="Dirty %", marker_color="#2563EB"))
            fig.add_trace(go.Bar(x=_top["hypothesis"], y=_top["close_rate"], name="Close %", marker_color="#10B981"))
            fig.update_layout(
                title="Top Hypotheses: Booking vs Close Rate",
                barmode="group", yaxis_title="%", height=400,
                template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── TAB 3: BY FUNNEL TYPE ──
    with tab_funnel:
        st.subheader("Funnel Type Performance")
        st.caption("How different landing page / form types affect conversion rates")
        with st.expander("ℹ️ How funnel types are classified"):
            st.markdown("""
- **Quiz (Cost Cap)** — ad set name contains "cost cap". Leads go to quiz.ecolinewindows.ca
- **Quiz (Bid Cap)** — ad set name contains "bid cap". Same quiz funnel
- **Hard Form** — ad set name contains "hard form". Website form, not quiz
- **Lead Form** — ad set name contains "form m/i". Native Meta lead gen form (in-app)
- **Affiliate** — ad set name contains "aff" + "form" or "creo"
- **Other** — doesn't match any pattern above (check utm_term naming)
""")

        _funnel_type_filter = st.multiselect(
            "Creative type filter",
            ["IMAGE", "VIDEO", "DCO-IMAGE", "DCO-VIDEO", "Other"],
            default=["IMAGE", "DCO-IMAGE"],
            key="funnel_creative_filter",
        )

        _funnel_df = _creative_df[
            _creative_df["creative_type"].isin(_funnel_type_filter) &
            _creative_df["hypothesis"].notna()
        ]

        _funnel_agg = _funnel_df.groupby("funnel_type").agg(
            leads=("row_num", "count"),
            booked=("is_booked", "sum"),
            happened=("is_happened", "sum"),
            sold=("is_sold", "sum"),
            revenue=("revenue", "sum"),
        ).reset_index()
        _funnel_agg = _funnel_agg[_funnel_agg["leads"] >= 15].copy()
        _funnel_agg["dirty_rate"] = (_funnel_agg["booked"] / _funnel_agg["leads"] * 100).round(1)
        _funnel_agg["clean_rate"] = (_funnel_agg["happened"] / _funnel_agg["leads"] * 100).round(1)
        _funnel_agg["close_rate"] = (_funnel_agg["sold"] / _funnel_agg["leads"] * 100).round(1)
        _funnel_agg["rev_per_lead"] = (_funnel_agg["revenue"] / _funnel_agg["leads"]).round(0)
        _funnel_agg = _funnel_agg.sort_values("close_rate", ascending=False)

        _funnel_display = _funnel_agg[["funnel_type", "leads", "dirty_rate", "clean_rate", "sold", "close_rate", "revenue", "rev_per_lead"]].copy()
        _funnel_display.columns = ["Funnel Type", "Leads", "Dirty %", "Clean %", "Sold", "Close %", "Revenue", "Rev/Lead"]
        _funnel_display["Revenue"] = _funnel_display["Revenue"].apply(lambda x: f"${x:,.0f}")
        _funnel_display["Rev/Lead"] = _funnel_display["Rev/Lead"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(_funnel_display, use_container_width=True, hide_index=True)

        # Cross-tab: hypothesis x funnel type
        st.subheader("Hypothesis x Funnel Type (Close Rate)")
        _cross = _funnel_df.groupby(["hypothesis", "funnel_type"]).agg(
            leads=("row_num", "count"),
            sold=("is_sold", "sum"),
        ).reset_index()
        _cross = _cross[_cross["leads"] >= 15]
        _cross["close_rate"] = (_cross["sold"] / _cross["leads"] * 100).round(1)
        if len(_cross) > 0:
            _pivot = _cross.pivot_table(index="hypothesis", columns="funnel_type", values="close_rate", aggfunc="first")
            st.dataframe(_pivot.style.format("{:.1f}%", na_rep="—"),
                         use_container_width=True)

    # ── TAB 4: BY PLACEMENT (Meta API data) ──
    if tab_placement is not None:
        with tab_placement:
            st.subheader("📍 Placement Performance (Meta Spend Data)")
            st.caption("Where your ad budget is going — Facebook Feed, Instagram Stories, Reels, etc. Data from Meta API.")

            # Parse hypothesis from ad_name in placement data
            _plc_df["hypothesis"] = _plc_df["ad_name"].apply(_parse_hypothesis)
            _plc_df["creative_type"] = _plc_df["ad_name"].apply(_parse_creative_type)

            # Friendly placement names
            _placement_names = {
                "facebook / feed": "Facebook Feed",
                "instagram / feed": "Instagram Feed",
                "facebook / facebook_reels": "Facebook Reels",
                "instagram / instagram_stories": "IG Stories",
                "instagram / instagram_reels": "IG Reels",
                "facebook / marketplace": "FB Marketplace",
                "facebook / facebook_stories": "FB Stories",
                "facebook / video_feeds": "FB Video Feeds",
                "facebook / search": "FB Search",
                "instagram / instagram_explore": "IG Explore",
                "facebook / instream_video": "FB In-Stream",
                "audience_network / an_classic": "Audience Network",
                "audience_network / rewarded_video": "AN Rewarded Video",
                "messenger / messenger_stories": "Messenger Stories",
            }
            _plc_df["placement"] = (_plc_df["publisher_platform"] + " / " + _plc_df["platform_position"]).map(_placement_names).fillna(
                _plc_df["publisher_platform"] + " / " + _plc_df["platform_position"]
            )

            # Aggregate by placement
            _plc_agg = _plc_df.groupby("placement").agg(
                spend=("spend", "sum"),
                impressions=("impressions", "sum"),
                clicks=("clicks", "sum"),
                link_clicks=("link_clicks", "sum"),
                lpv=("landing_page_views", "sum"),
                ads=("ad_id", "nunique"),
            ).reset_index()
            _plc_agg = _plc_agg[_plc_agg["spend"] > 10].copy()
            _plc_agg["cpm"] = (_plc_agg["spend"] / _plc_agg["impressions"] * 1000).round(2)
            _plc_agg["ctr"] = (_plc_agg["clicks"] / _plc_agg["impressions"] * 100).round(2)
            _plc_agg["cpc"] = (_plc_agg["spend"] / _plc_agg["clicks"].replace(0, float("nan"))).round(2)
            _plc_agg["cost_per_lpv"] = (_plc_agg["spend"] / _plc_agg["lpv"].replace(0, float("nan"))).round(2)
            _plc_total = _plc_agg["spend"].sum()
            _plc_agg["spend_pct"] = (_plc_agg["spend"] / _plc_total * 100).round(1)
            _plc_agg = _plc_agg.sort_values("spend", ascending=False)

            # Top metrics
            _top3 = _plc_agg.head(3)
            _plc_cols = st.columns(4)
            with _plc_cols[0]:
                st.metric("Total Spend (Meta API)", f"${_plc_total:,.0f}")
            with _plc_cols[1]:
                st.metric("Top Placement", _top3.iloc[0]["placement"] if len(_top3) > 0 else "—")
            with _plc_cols[2]:
                _best_ctr = _plc_agg[_plc_agg["impressions"] > 50000].sort_values("ctr", ascending=False)
                st.metric("Best CTR", f"{_best_ctr.iloc[0]['placement']}: {_best_ctr.iloc[0]['ctr']}%" if len(_best_ctr) > 0 else "—")
            with _plc_cols[3]:
                _best_cpc = _plc_agg[_plc_agg["clicks"] > 500].sort_values("cpc")
                st.metric("Cheapest CPC", f"{_best_cpc.iloc[0]['placement']}: ${_best_cpc.iloc[0]['cpc']:.2f}" if len(_best_cpc) > 0 else "—")
            st.divider()

            # Table
            _plc_display = _plc_agg[["placement", "spend", "spend_pct", "impressions", "clicks", "link_clicks", "lpv", "cpm", "ctr", "cpc", "cost_per_lpv", "ads"]].copy()
            _plc_display.columns = ["Placement", "Spend", "% of Total", "Impressions", "Clicks", "Link Clicks", "LPV", "CPM", "CTR %", "CPC", "Cost/LPV", "Unique Ads"]
            _plc_display["Spend"] = _plc_display["Spend"].apply(lambda x: f"${x:,.0f}")
            _plc_display["Impressions"] = _plc_display["Impressions"].apply(lambda x: f"{x:,.0f}")
            _plc_display["Clicks"] = _plc_display["Clicks"].apply(lambda x: f"{x:,.0f}")
            _plc_display["CPM"] = _plc_display["CPM"].apply(lambda x: f"${x:.2f}")
            _plc_display["CPC"] = _plc_display["CPC"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "—")
            _plc_display["Cost/LPV"] = _plc_display["Cost/LPV"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "—")
            st.dataframe(_plc_display, use_container_width=True, hide_index=True)

            # Chart: spend distribution
            import plotly.graph_objects as go
            _chart_plc = _plc_agg.head(10)
            fig_plc = go.Figure()
            fig_plc.add_trace(go.Bar(
                x=_chart_plc["placement"], y=_chart_plc["spend"],
                name="Spend", marker_color="#2563EB",
                text=_chart_plc["spend_pct"].apply(lambda x: f"{x}%"),
                textposition="outside",
            ))
            fig_plc.update_layout(
                title="Spend Distribution by Placement",
                yaxis_title="Spend ($)", height=400,
                template="plotly_white",
            )
            st.plotly_chart(fig_plc, use_container_width=True)

            # Chart: CTR + CPC comparison
            _chart_plc2 = _plc_agg[_plc_agg["impressions"] > 10000].head(10)
            if len(_chart_plc2) > 0:
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots
                fig_plc2 = make_subplots(specs=[[{"secondary_y": True}]])
                fig_plc2.add_trace(
                    go.Bar(x=_chart_plc2["placement"], y=_chart_plc2["ctr"], name="CTR %", marker_color="#10B981"),
                    secondary_y=False,
                )
                fig_plc2.add_trace(
                    go.Scatter(x=_chart_plc2["placement"], y=_chart_plc2["cpc"], name="CPC ($)", marker_color="#EF4444", mode="markers+lines"),
                    secondary_y=True,
                )
                fig_plc2.update_layout(title="CTR vs CPC by Placement", height=400, template="plotly_white")
                fig_plc2.update_yaxes(title_text="CTR %", secondary_y=False)
                fig_plc2.update_yaxes(title_text="CPC ($)", secondary_y=True)
                st.plotly_chart(fig_plc2, use_container_width=True)

            # Placement breakdown by hypothesis
            st.subheader("Placement Spend by Top Hypotheses")
            _plc_hyp = _plc_df[_plc_df["hypothesis"].notna()].groupby(["hypothesis", "placement"]).agg(
                spend=("spend", "sum"),
            ).reset_index()
            _top_hyps_plc = _plc_hyp.groupby("hypothesis")["spend"].sum().nlargest(10).index.tolist()
            _plc_hyp_filtered = _plc_hyp[_plc_hyp["hypothesis"].isin(_top_hyps_plc)]
            if len(_plc_hyp_filtered) > 0:
                _plc_pivot = _plc_hyp_filtered.pivot_table(index="hypothesis", columns="placement", values="spend", aggfunc="sum", fill_value=0)
                _plc_pivot = _plc_pivot.loc[_plc_pivot.sum(axis=1).sort_values(ascending=False).index]
                # Show only top 6 placements
                _top_plc_cols = _plc_pivot.sum().nlargest(6).index.tolist()
                _plc_pivot_display = _plc_pivot[_top_plc_cols].copy()
                _plc_pivot_display = _plc_pivot_display.map(lambda x: f"${x:,.0f}" if x > 0 else "—")
                st.dataframe(_plc_pivot_display, use_container_width=True)

    # ── TAB 5: AD COPY ANALYSIS (Meta API data) ──
    if tab_copy is not None:
        with tab_copy:
            st.subheader("📝 Ad Copy & Messaging Analysis")
            st.caption("What messaging angles are being used in your ads. Data from Meta Ads API creative details.")

            if _has_creative_data and len(_cre_df) > 0:
                # Extract first line of body as "hook"
                _cre_df["hook"] = _cre_df["body"].fillna("").apply(lambda x: str(x).split("\n")[0].strip()[:120] if x else "")
                _cre_df["hook"] = _cre_df["hook"].replace("", "No body text")

                # CTA distribution
                st.subheader("CTA Type Distribution")
                _cta_agg = _cre_df[_cre_df["cta_type"] != ""].groupby("cta_type").size().reset_index(name="count")
                _cta_agg = _cta_agg.sort_values("count", ascending=False)
                _cta_cols = st.columns(min(len(_cta_agg), 4))
                for i, (_, row) in enumerate(_cta_agg.head(4).iterrows()):
                    with _cta_cols[i]:
                        st.metric(row["cta_type"], f"{row['count']} ads")
                st.divider()

                # Title analysis (unique headlines)
                st.subheader("Top Headlines")
                _title_agg = _cre_df[_cre_df["title"] != ""].groupby("title").agg(
                    count=("creative_id", "count"),
                    accounts=("account", "nunique"),
                ).reset_index()
                _title_agg = _title_agg.sort_values("count", ascending=False)
                _title_display = _title_agg.head(20).copy()
                _title_display.columns = ["Headline", "# Creatives", "# Accounts"]
                st.dataframe(_title_display, use_container_width=True, hide_index=True)

                st.divider()

                # Hook analysis (first line of body)
                st.subheader("Top Opening Lines (Hooks)")
                _hook_agg = _cre_df[_cre_df["hook"] != "No body text"].groupby("hook").agg(
                    count=("creative_id", "count"),
                    ctas=("cta_type", lambda x: ", ".join(sorted(x.dropna().unique()))),
                ).reset_index()
                _hook_agg = _hook_agg.sort_values("count", ascending=False)
                _hook_display = _hook_agg.head(25).copy()
                _hook_display.columns = ["Opening Line", "# Creatives", "CTA Types"]
                st.dataframe(_hook_display, use_container_width=True, hide_index=True, height=500)

                st.divider()

                # Match creatives to lead performance via ad_name
                st.subheader("Creative Copy ↔ Lead Performance")
                st.caption("Matching creative names with utm_content from leads to connect copy with conversion data.")

                # Build a lookup from creative_name → body/title
                _cre_lookup = {}
                for _, cr in _cre_df.iterrows():
                    name = str(cr.get("creative_name", "")).strip()
                    if name:
                        _cre_lookup[name] = {
                            "title": cr.get("title", ""),
                            "hook": cr.get("hook", ""),
                            "cta": cr.get("cta_type", ""),
                            "body": str(cr.get("body", ""))[:300],
                        }

                # Try to match with leads utm_content
                _content_leads = _creative_df.groupby("utm_content").agg(
                    leads=("row_num", "count"),
                    booked=("is_booked", "sum"),
                    sold=("is_sold", "sum"),
                    revenue=("revenue", "sum"),
                ).reset_index()
                _content_leads["close_rate"] = (_content_leads["sold"] / _content_leads["leads"] * 100).round(1)
                _content_leads["dirty_rate"] = (_content_leads["booked"] / _content_leads["leads"] * 100).round(1)

                # Match by checking if creative_name is contained in utm_content or vice versa
                _matched = []
                for _, lr in _content_leads[_content_leads["leads"] >= 5].iterrows():
                    utm = str(lr["utm_content"])
                    # Direct match
                    info = _cre_lookup.get(utm)
                    if not info:
                        # Try partial match: creative_name starts with utm_content title part
                        for cname, cinfo in _cre_lookup.items():
                            if cname and len(cname) > 10 and (cname.split(" 202")[0] in utm or utm.split(" 202")[0] in cname):
                                info = cinfo
                                break
                    if info:
                        _matched.append({
                            "utm_content": utm,
                            "headline": info["title"],
                            "hook": info["hook"],
                            "cta": info["cta"],
                            "leads": lr["leads"],
                            "dirty_rate": lr["dirty_rate"],
                            "close_rate": lr["close_rate"],
                            "sold": lr["sold"],
                            "revenue": lr["revenue"],
                        })

                if _matched:
                    _match_df = pd.DataFrame(_matched).sort_values("leads", ascending=False)
                    _match_df["revenue"] = _match_df["revenue"].apply(lambda x: f"${x:,.0f}")
                    _match_display = _match_df[["headline", "hook", "cta", "leads", "dirty_rate", "close_rate", "sold", "revenue"]].copy()
                    _match_display.columns = ["Headline", "Opening Line", "CTA", "Leads", "Dirty %", "Close %", "Sold", "Revenue"]
                    st.dataframe(_match_display, use_container_width=True, hide_index=True, height=500)
                    st.caption(f"Matched {len(_matched)} creatives with lead data out of {len(_content_leads[_content_leads['leads'] >= 5])} utm_content groups")
                else:
                    st.info("No direct matches found between creative names and utm_content. Creative names may use different naming patterns than UTM tags.")

                # Full creative library
                st.divider()
                st.subheader("Full Creative Library")
                _lib_search = st.text_input("Search body text or title", "", key="copy_search")
                _lib_df = _cre_df.copy()
                if _lib_search:
                    _lib_df = _lib_df[
                        _lib_df["body"].fillna("").str.contains(_lib_search, case=False) |
                        _lib_df["title"].fillna("").str.contains(_lib_search, case=False)
                    ]
                _lib_display = _lib_df[["creative_name", "title", "hook", "cta_type", "account"]].head(50).copy()
                _lib_display.columns = ["Creative Name", "Headline", "Opening Line", "CTA", "Account"]
                st.dataframe(_lib_display, use_container_width=True, hide_index=True, height=400)
            else:
                st.warning("No creative data available. Run the Meta sync task to populate.")

    # ── TAB 6: DETAIL EXPLORER ──
    with tab_detail:
        st.subheader("Creative Detail Explorer")

        _sel_hyp = st.selectbox(
            "Select hypothesis",
            ["All"] + sorted(_creative_df["hypothesis"].dropna().unique().tolist()),
        )
        _sel_type = st.multiselect(
            "Creative type",
            ["IMAGE", "VIDEO", "DCO-IMAGE", "DCO-VIDEO", "Other"],
            default=["IMAGE", "VIDEO", "DCO-IMAGE", "DCO-VIDEO"],
            key="detail_type_filter",
        )

        _detail_df = _creative_df[_creative_df["creative_type"].isin(_sel_type)].copy()
        if _sel_hyp != "All":
            _detail_df = _detail_df[_detail_df["hypothesis"] == _sel_hyp]

        # Group by utm_content (individual creative)
        _content_agg = _detail_df.groupby("utm_content").agg(
            creative_type=("creative_type", "first"),
            hypothesis=("hypothesis", "first"),
            leads=("row_num", "count"),
            booked=("is_booked", "sum"),
            sold=("is_sold", "sum"),
            revenue=("revenue", "sum"),
        ).reset_index()
        _content_agg = _content_agg[_content_agg["leads"] >= 5].copy()
        _content_agg["dirty_rate"] = (_content_agg["booked"] / _content_agg["leads"] * 100).round(1)
        _content_agg["close_rate"] = (_content_agg["sold"] / _content_agg["leads"] * 100).round(1)
        _content_agg["rev_per_lead"] = (_content_agg["revenue"] / _content_agg["leads"]).round(0)
        _content_agg = _content_agg.sort_values("leads", ascending=False)

        _content_display = _content_agg[["utm_content", "creative_type", "hypothesis", "leads", "dirty_rate", "close_rate", "sold", "revenue", "rev_per_lead"]].copy()
        _content_display.columns = ["Creative (utm_content)", "Type", "Hypothesis", "Leads", "Dirty %", "Close %", "Sold", "Revenue", "Rev/Lead"]
        _content_display["Revenue"] = _content_display["Revenue"].apply(lambda x: f"${x:,.0f}")
        _content_display["Rev/Lead"] = _content_display["Rev/Lead"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(_content_display, use_container_width=True, hide_index=True, height=600)


# ─────────────────────────────────────────────
#  PAGE: META LIVE
# ─────────────────────────────────────────────
elif page == "📡 Meta Live":
    st.title("Meta Live")
    st.caption(
        "Spend, CPM, CPC pulled directly from Meta API (real-time, no Windsor delay). "
        "Lead counts from BigQuery (clean + all). Matched by campaign → city/region."
    )

    # ── Date selector ───────────────────────────────────────────────────────
    preset_map = {
        "Yesterday":    "yesterday",
        "Last 7 days":  "last_7d",
        "Last 14 days": "last_14d",
        "Last 30 days": "last_30d",
        "This month":   "this_month",
        "Last month":   "last_month",
        "Custom range": "custom",
    }
    preset_label = st.segmented_control(
        "Period", list(preset_map.keys()), default="Last 7 days"
    )
    date_preset = preset_map.get(preset_label, "last_7d")

    custom_since = custom_until = None
    if date_preset == "custom":
        cc1, cc2 = st.columns(2)
        with cc1:
            custom_since = st.date_input("From", value=date.today() - timedelta(days=30),
                                         key="meta_since")
        with cc2:
            custom_until = st.date_input("To", value=date.today() - timedelta(days=1),
                                         key="meta_until")
        # Use date-based cache key
        date_preset = f"{custom_since}_{custom_until}"

    # ── Pull Meta data ──────────────────────────────────────────────────────
    from utils.data import load_meta_live, META_ACCOUNTS
    from utils.meta_client import cache_age_minutes, load_province_breakdown

    meta_df = load_meta_live(date_preset)

    # Cache age indicator
    age = cache_age_minutes(date_preset)
    if age is not None:
        if age < 60:
            st.caption(f"📡 Data from Meta cache · refreshed {age:.0f} min ago · ask Claude to refresh anytime")
        else:
            hours = age / 60
            st.caption(f"⚠️ Cache is {hours:.1f}h old · ask Claude: 'refresh Meta Live data' to update")
    else:
        st.caption(f"⚠️ No cache for '{date_preset}' yet · ask Claude: 'refresh Meta Live data for {date_preset}'")

    if meta_df.empty:
        if custom_since and custom_until:
            ask_msg = f"refresh Meta Live data from {custom_since} to {custom_until}"
        else:
            ask_msg = f"refresh Meta Live data for {preset_label.lower()}"
        st.info(
            f"No cached data for **{preset_label}** yet.\n\n"
            f"Ask Claude: **\"{ask_msg}\"** and it will pull fresh data from all 9 accounts."
        )
    else:
        # ── Resolve Meta Live period → date range for BQ filtering ───────────
        from datetime import date as _date, timedelta as _td
        import calendar as _cal

        _today = _date.today()
        if custom_since and custom_until:
            _ml_start, _ml_end = pd.Timestamp(custom_since), pd.Timestamp(custom_until)
        elif date_preset == "yesterday":
            _d = _today - _td(days=1)
            _ml_start, _ml_end = pd.Timestamp(_d), pd.Timestamp(_d)
        elif date_preset == "last_7d":
            _ml_start = pd.Timestamp(_today - _td(days=7))
            _ml_end   = pd.Timestamp(_today - _td(days=1))
        elif date_preset == "last_14d":
            _ml_start = pd.Timestamp(_today - _td(days=14))
            _ml_end   = pd.Timestamp(_today - _td(days=1))
        elif date_preset == "last_30d":
            _ml_start = pd.Timestamp(_today - _td(days=30))
            _ml_end   = pd.Timestamp(_today - _td(days=1))
        elif date_preset == "this_month":
            _ml_start = pd.Timestamp(_today.replace(day=1))
            _ml_end   = pd.Timestamp(_today)
        elif date_preset == "last_month":
            _first = (_today.replace(day=1) - _td(days=1)).replace(day=1)
            _last  = _today.replace(day=1) - _td(days=1)
            _ml_start, _ml_end = pd.Timestamp(_first), pd.Timestamp(_last)
        else:
            # fallback: use sidebar range
            _ml_start = pd.Timestamp(start_date)
            _ml_end   = pd.Timestamp(end_date)

        # Filter combined to the Meta Live period (tz-aware safe comparison)
        _dt_col = combined["dt"].dt.tz_localize(None) if combined["dt"].dt.tz is not None else combined["dt"]
        _ml_mask = (_dt_col.dt.date >= _ml_start.date()) & (_dt_col.dt.date <= _ml_end.date())
        combined_ml = combined[_ml_mask].copy()

        # ── BQ city-level summary for META source — filtered to Meta Live period
        bq_meta = pd.DataFrame([
            {"city": city, **compute_funnel(grp)}
            for city, grp in combined_ml[combined_ml["source"] == "META"].groupby("city")
        ])[["city", "clean_leads", "appts", "sold"]]
        bq_meta.columns = ["city_bq", "bq_leads", "bq_appts", "bq_sold"]
        # Normalise city for join (uppercase strip)
        bq_meta["city_key"] = bq_meta["city_bq"].str.strip().str.upper()

        def _enrich(df: pd.DataFrame) -> pd.DataFrame:
            """Add CPL (Meta), CPL (BQ), Appts (BQ), Sold (BQ) columns."""
            d = df.copy()
            # CPL Meta
            d["cpl_meta"] = d.apply(
                lambda r: r["spend"] / r["leads_meta"] if r.get("leads_meta", 0) > 0 else None, axis=1
            )
            # Join BQ data by city (city-specific campaigns only)
            loc_key = d["location"].str.strip().str.upper()
            d["city_key"] = loc_key
            d = d.merge(bq_meta, on="city_key", how="left")
            # CPL BQ = spend / bq_leads
            d["cpl_bq"] = d.apply(
                lambda r: r["spend"] / r["bq_leads"] if pd.notna(r.get("bq_leads")) and r["bq_leads"] > 0 else None,
                axis=1,
            )
            return d

        scope_icons = {
            "city":         "🏙️",
            "province":     "🗺️",
            "sub_regional": "📍",
            "national":     "🇨🇦",
            "usa":          "🇺🇸",
            "other":        "⚙️",
        }

        def _fmt_table(df: pd.DataFrame) -> pd.DataFrame:
            want = ["account_name", "campaign_name", "scope", "location", "camp_type",
                    "spend", "leads_meta", "cpl_meta", "bq_leads", "bq_appts", "cpl_bq",
                    "impressions", "cpm", "cpc"]
            cols = [c for c in want if c in df.columns]
            out = df[cols].copy()
            out["scope"]       = out["scope"].map(lambda s: f"{scope_icons.get(s, '')} {s}")
            out["spend"]       = out["spend"].apply(lambda x: f"${x:,.0f}")
            out["impressions"] = out["impressions"].apply(lambda x: f"{x/1000:,.1f}K") if "impressions" in out.columns else out.get("impressions","")
            out["cpm"]         = out["cpm"].apply(lambda x: f"${x:.2f}")
            out["cpc"]         = out["cpc"].apply(lambda x: f"${x:.2f}")
            out["cpl_meta"]    = out["cpl_meta"].apply(lambda x: f"${x:.0f}" if pd.notna(x) else "—")
            if "cpl_bq" in out.columns:
                out["cpl_bq"]  = out["cpl_bq"].apply(lambda x: f"${x:.0f}" if pd.notna(x) else "—")
            if "bq_leads" in out.columns:
                out["bq_leads"] = out["bq_leads"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
            if "bq_appts" in out.columns:
                out["bq_appts"] = out["bq_appts"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
            out.rename(columns={
                "account_name":  "Account",
                "campaign_name": "Campaign",
                "scope":         "Scope",
                "location":      "Location",
                "camp_type":     "Type",
                "spend":         "Spend",
                "leads_meta":    "Leads (Meta)",
                "cpl_meta":      "CPL (raw)",
                "bq_leads":      "Leads (clean)",
                "bq_appts":      "Appts (BQ)",
                "cpl_bq":        "CPL (clean)",
                "impressions":   "Impressions",
                "cpm":           "CPM",
                "cpc":           "CPC",
            }, inplace=True)
            return out

        meta_enriched = _enrich(meta_df)

        # ── Summary KPI row ─────────────────────────────────────────────────
        total_spend   = meta_df["spend"].sum()
        total_impr    = meta_df["impressions"].sum()
        total_clicks  = meta_df["clicks"].sum()
        total_leads_m = meta_df["leads_meta"].sum()
        total_bq_leads = bq_meta["bq_leads"].sum()
        total_bq_appts = bq_meta["bq_appts"].sum()
        avg_cpm       = total_spend / total_impr * 1000 if total_impr else 0
        avg_cpl_meta  = total_spend / total_leads_m if total_leads_m else 0
        avg_cpl_bq    = total_spend / total_bq_leads if total_bq_leads else 0

        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
        c1.metric("Total Spend",    f"${total_spend:,.0f}")
        c2.metric("Impressions",    f"{total_impr/1000:,.0f}K")
        c3.metric("Avg CPM",        f"${avg_cpm:.2f}")
        c4.metric("Leads (Meta)",   f"{int(total_leads_m):,}",
                  help="Raw lead count from Meta API — includes spam/invalid, not deduplicated")
        c5.metric("CPL (Meta, raw)", f"${avg_cpl_meta:.0f}",
                  help="Spend ÷ Meta raw leads — inflated by spam, use CPL (clean) for real cost")
        c6.metric("Leads (BQ)",     f"{int(total_bq_leads):,}",
                  help="Clean deduplicated leads from BigQuery — same logic as Overview")
        c7.metric("CPL (clean)",    f"${avg_cpl_bq:.0f}",
                  help="Spend ÷ clean BQ leads — matches Overview CPL, use this as real cost per lead")
        c8.metric("Appts (BQ)",     f"{int(total_bq_appts):,}",
                  help="Appointments from META leads — filtered to the selected Meta Live period")

        st.divider()

        # ── Scope breakdown tabs ─────────────────────────────────────────────
        tab_all, tab_city, tab_regional, tab_national = st.tabs([
            "All Campaigns", "City-Specific", "Regional / Province", "All Regions (CA)"
        ])

        with tab_all:
            st.dataframe(_fmt_table(meta_enriched), use_container_width=True, hide_index=True)

        with tab_city:
            df_city = meta_enriched[meta_enriched["scope"] == "city"]
            if df_city.empty:
                st.info("No active city-specific campaigns in this period.")
            else:
                st.dataframe(_fmt_table(df_city), use_container_width=True, hide_index=True)

        with tab_regional:
            df_reg = meta_enriched[meta_enriched["scope"].isin(["province", "sub_regional"])]
            if df_reg.empty:
                st.info("No active regional campaigns in this period.")
            else:
                st.dataframe(_fmt_table(df_reg), use_container_width=True, hide_index=True)

        with tab_national:
            df_nat = meta_enriched[meta_enriched["scope"] == "national"]
            if df_nat.empty:
                st.info("No active All Regions campaigns in this period.")
            else:
                # Province → city mapping for BQ filtering
                # Cities verified against BQ city_map + 90-day appointment data (Apr 2026)
                # Names must match city_map exactly for BQ join to work
                # "Bad geo" cities (Toronto, Thunder Bay etc.) kept in city_map for FB drift monitoring
                PROVINCE_CITIES = {
                    "Alberta":                   ["Calgary", "Edmonton", "Red Deer", "Lethbridge", "Medicine Hat", "Grande Prairie", "Lloydminster, AB"],
                    "British Columbia":           ["Vancouver", "Victoria", "Kelowna", "Kamloops", "Nanaimo", "Prince George, BC"],
                    "Ontario":                   ["Ottawa", "Kingston, ON", "Kenora"],
                    "Manitoba":                  ["Winnipeg", "Brandon, MB"],
                    "Saskatchewan":              ["Saskatoon", "Regina", "Moose Jaw, SK"],
                    "New Brunswick":             ["Moncton", "Fredericton", "Saint John, NB"],
                    "Nova Scotia":               ["Halifax", "Sydney"],
                    "Newfoundland and Labrador": ["St. Jhon's, NF"],   # typo matches BQ city_map (fix pending T13)
                    "Prince Edward Island":      ["Charlottetown"],
                }

                # Load province breakdown cache
                prov_breakdown = load_province_breakdown(date_preset)

                # BQ city distribution per camp_type for META source — filtered to Meta Live period
                bq_meta_src = combined_ml[combined_ml["source"] == "META"].copy()
                if "utm_campaign" in bq_meta_src.columns:
                    bq_meta_src["camp_type_bq"] = bq_meta_src["utm_campaign"].apply(
                        lambda v: _get_camp_type(v, None) if pd.notna(v) else "DIRECT"
                    )
                else:
                    bq_meta_src["camp_type_bq"] = "OTHER"

                bq_city_type = (
                    bq_meta_src
                    .groupby(["camp_type_bq", "city"])
                    .apply(lambda g: pd.Series({
                        "leads": int(g["is_clean"].sum()) if "is_clean" in g.columns else len(g),
                        "appts": int(g["cf_booked_date"].notna().sum()) if "cf_booked_date" in g.columns else 0,
                        "sold":  int((g["status"] == "sold").sum()),
                    }))
                    .reset_index()
                )

                st.caption(
                    "Province breakdown comes directly from Meta API. "
                    "City breakdown within each province uses BigQuery data matched by campaign type."
                )
                st.dataframe(_fmt_table(df_nat), use_container_width=True, hide_index=True)

                st.divider()
                st.markdown("#### Province → City breakdown")

                for _, camp_row in df_nat.iterrows():
                    camp_id  = str(camp_row.get("campaign_id", ""))
                    ct       = camp_row.get("camp_type", "OTHER")
                    spend    = camp_row["spend"]
                    camp_name = camp_row["campaign_name"]
                    meta_leads = camp_row.get("leads_meta") or 0

                    prov_rows = prov_breakdown.get(camp_id, {}).get("rows", [])
                    has_provinces = bool(prov_rows)

                    # ── Province-level summary ──────────────────────────────────
                    with st.expander(
                        f"{camp_name}  ·  {ct}  ·  ${spend:,.0f}  ·  "
                        + (f"{int(meta_leads):,} leads (Meta)" if meta_leads else "no Meta leads"),
                        expanded=False,
                    ):
                        if has_provinces:
                            # Build province table
                            prov_df = pd.DataFrame(prov_rows)
                            prov_df = prov_df[prov_df["region"].isin(PROVINCE_CITIES.keys())].copy()
                            prov_df["leads_meta"] = prov_df["leads"].fillna(0).astype(int)
                            prov_df["cpm_str"]    = prov_df["cpm"].apply(lambda x: f"${x:.2f}")
                            prov_df["spend_str"]  = prov_df["spend"].apply(lambda x: f"${x:,.0f}")
                            prov_df["impr_str"]   = prov_df["impressions"].apply(lambda x: f"{int(x):,}")

                            disp_prov = prov_df[["region", "spend_str", "impr_str", "cpm_str", "leads_meta"]].copy()
                            disp_prov.rename(columns={
                                "region":     "Province",
                                "spend_str":  "Spend",
                                "impr_str":   "Impressions",
                                "cpm_str":    "CPM",
                                "leads_meta": "Leads (Meta)",
                            }, inplace=True)
                            st.dataframe(disp_prov, use_container_width=True, hide_index=True)
                        else:
                            st.caption("No province breakdown cached for this campaign/period.")

                        # ── City breakdown per province ─────────────────────────
                        st.markdown("**City breakdown (BigQuery)**")
                        city_src = bq_city_type[bq_city_type["camp_type_bq"] == ct].copy()

                        if city_src.empty:
                            st.caption("No BQ data for this campaign type.")
                        else:
                            # For each province in the campaign, show city distribution
                            provinces_to_show = (
                                [r["region"] for r in prov_rows if r["region"] in PROVINCE_CITIES]
                                if has_provinces
                                else list(PROVINCE_CITIES.keys())
                            )

                            # Pre-compute total BQ leads across ALL provinces for proportional spend
                            all_known_cities = [c for p in PROVINCE_CITIES.values() for c in p]
                            total_bq_leads_all = int(city_src[city_src["city"].isin(all_known_cities)]["leads"].sum())

                            for prov in provinces_to_show:
                                cities_in_prov = PROVINCE_CITIES.get(prov, [])
                                city_data = city_src[city_src["city"].isin(cities_in_prov)].copy()
                                if city_data.empty or city_data["leads"].sum() == 0:
                                    continue

                                total_leads_prov = city_data["leads"].sum()

                                # Get Meta leads for this province (if available)
                                prov_meta_leads = 0
                                if has_provinces:
                                    prov_row = next((r for r in prov_rows if r["region"] == prov), None)
                                    if prov_row:
                                        prov_meta_leads = prov_row.get("leads") or 0
                                        prov_spend = prov_row.get("spend") or 0
                                else:
                                    # No province breakdown — distribute total spend
                                    # proportionally by BQ lead share
                                    prov_spend = (
                                        spend * total_leads_prov / total_bq_leads_all
                                        if total_bq_leads_all > 0 else 0
                                    )
                                    prov_meta_leads = (
                                        meta_leads * total_leads_prov / total_bq_leads_all
                                        if total_bq_leads_all > 0 else 0
                                    )

                                city_data = city_data[city_data["leads"] > 0].copy()
                                city_data["share"]     = (city_data["leads"] / total_leads_prov * 100).round(1)
                                city_data["est_spend"] = (city_data["leads"] / total_leads_prov * prov_spend).round(0)
                                city_data["est_cpl"]   = (city_data["est_spend"] / city_data["leads"].replace(0, float("nan"))).round(0)
                                if prov_meta_leads:
                                    city_data["est_meta_leads"] = (city_data["leads"] / total_leads_prov * prov_meta_leads).round(0).astype(int)
                                city_data = city_data.sort_values("leads", ascending=False)

                                # Province sub-header
                                meta_note = f" · ~{int(prov_meta_leads)} est. Meta leads" if prov_meta_leads and not has_provinces else (f" · {int(prov_meta_leads)} Meta leads" if prov_meta_leads else "")
                                st.markdown(f"🏙️ **{prov}**{meta_note} · {total_leads_prov} BQ leads")

                                cols_to_show = ["city", "leads", "share", "appts", "sold", "est_spend", "est_cpl"]
                                if prov_meta_leads:
                                    cols_to_show.insert(2, "est_meta_leads")

                                disp_city = city_data[cols_to_show].copy()
                                disp_city["share"]     = disp_city["share"].apply(lambda x: f"{x}%")
                                disp_city["est_spend"] = disp_city["est_spend"].apply(lambda x: f"${x:,.0f}")
                                disp_city["est_cpl"]   = disp_city["est_cpl"].apply(lambda x: f"${x:.0f}" if pd.notna(x) else "—")
                                rename_map = {
                                    "city": "City", "leads": "Leads (BQ)", "share": "Share",
                                    "appts": "Appts", "sold": "Sold",
                                    "est_spend": "Est. Spend", "est_cpl": "Est. CPL",
                                    "est_meta_leads": "Est. Meta Leads",
                                }
                                disp_city.rename(columns=rename_map, inplace=True)
                                st.dataframe(disp_city, use_container_width=True, hide_index=True)

        st.divider()

        # ── Windsor vs Meta spend comparison ────────────────────────────────
        with st.expander("Windsor AI vs Meta Direct — Spend Comparison", expanded=False):
            st.caption(
                "Windsor AI data is from BigQuery (`raw.spend_snap`). "
                "Meta Direct is pulled live from the API right now. "
                "Differences are normal due to Windsor's ingestion delay."
            )
            windsor_spend = spend_df["spend"].sum() if not spend_df.empty else 0
            meta_spend    = total_spend
            diff          = meta_spend - windsor_spend
            diff_pct      = diff / windsor_spend * 100 if windsor_spend else 0

            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("Windsor AI (BQ)",   f"${windsor_spend:,.0f}")
            cc2.metric("Meta Direct (API)", f"${meta_spend:,.0f}")
            cc3.metric("Difference",
                       f"${diff:+,.0f}",
                       delta=f"{diff_pct:+.1f}%",
                       delta_color="inverse" if diff < 0 else "normal")


# ─────────────────────────────────────────────
#  PAGE: DATA ASSISTANT (AI Chat)
# ─────────────────────────────────────────────
elif page == "💬 Data Assistant":
    st.title("Data Assistant")
    st.caption("Ask questions about your data — leads, conversions, spend, creatives. AI-powered, read-only.")

    import os as _da_os

    _api_key = _da_os.environ.get("ANTHROPIC_API_KEY", "") or st.secrets.get("ANTHROPIC_API_KEY", "") if hasattr(st, "secrets") else _da_os.environ.get("ANTHROPIC_API_KEY", "")

    if not _api_key:
        st.warning("⚠️ **API Key не настроен.** Чтобы активировать чат:")
        st.markdown("""
1. Зайди на **[console.anthropic.com](https://console.anthropic.com)** → Settings → API Keys → Create Key
2. Скопируй ключ (начинается с `sk-ant-...`)
3. Добавь в файл `.streamlit/secrets.toml` рядом с `app.py`:
```toml
ANTHROPIC_API_KEY = "sk-ant-api03-ВАШ-КЛЮЧ"
```
4. Или установи переменную окружения:
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-ВАШ-КЛЮЧ"
```
5. Перезапусти Streamlit

💡 Это **отдельно** от подписки claude.ai — нужен именно API ключ с console.anthropic.com
""")
    else:
        try:
            from anthropic import Anthropic as _Anthropic
        except ImportError:
            st.error("❌ Библиотека `anthropic` не установлена. Выполни: `pip install anthropic`")
            st.stop()

        _client = _Anthropic(api_key=_api_key)

        # ── Build data context summary ──
        _da_total_leads = len(leads_f)
        _da_clean_leads = leads_f["is_clean"].sum() if "is_clean" in leads_f.columns else 0
        _da_sold = (leads_f["status"] == "sold").sum() if "status" in leads_f.columns else 0
        _da_revenue = pd.to_numeric(leads_f["amount"], errors="coerce").fillna(0)
        _da_revenue_sold = _da_revenue[leads_f["status"] == "sold"].sum() if "status" in leads_f.columns else 0
        _da_spend_total = spend_df["spend"].sum() if len(spend_df) > 0 else 0
        _da_date_from = leads_f["created_date"].min() if "created_date" in leads_f.columns else "?"
        _da_date_to = leads_f["created_date"].max() if "created_date" in leads_f.columns else "?"

        _da_sources = leads_f["source"].value_counts().head(5).to_dict() if "source" in leads_f.columns else {}
        _da_provinces = leads_f["province"].value_counts().head(8).to_dict() if "province" in leads_f.columns else {}

        _da_context = f"""You are a Data Assistant for Ecoline Windows — a Canadian window installation company.
You answer questions about their marketing and sales data. You are helpful, precise, and concise.

CURRENT DASHBOARD DATA (filtered by user's selected date range):
- Period: {_da_date_from} to {_da_date_to}
- Total leads (all): {_da_total_leads:,}
- Clean leads (deduped, valid phone): {int(_da_clean_leads):,}
- Sold: {int(_da_sold):,}
- Revenue from sold: ${_da_revenue_sold:,.0f}
- Total Meta spend: ${_da_spend_total:,.0f}
- Avg sale: ${(_da_revenue_sold / _da_sold):,.0f} if _da_sold > 0 else "N/A"

Top sources: {_da_sources}
Top provinces: {_da_provinces}

BIGQUERY SCHEMA (project: ecolinew):
- Table `raw.leads`: row_num, created_date, source, utm_source, utm_medium, utm_campaign, utm_content, utm_term, email, phone, phone_clean, city, province, country
- Table `raw.leads_status`: row_num, status (lead/appointment/sold/cancelled/cancelled before appt), Amount, cf_amount, cf_appointment_date, cf_booked_date
- JOIN: leads.row_num = leads_status.row_num (1:1)
- Status values: 'lead', 'appointment', 'sold', 'cancelled', 'cancelled before appt'
- utm_content format: "IMAGE - Hyp 111.1 - IT 3" or "VIDEO - Hyp 21.1 - IT 2" or "DCO - IMAGE - Hyp 100 - IT 1"
- utm_term = ad set name, contains funnel type: "cost cap", "bid cap", "hard form", "form m/i", "aff"
- Clean lead = valid phone (10-digit starting 2-9) + deduped within lookback window

PLACEMENT DATA (from Meta API, cached in CSV):
- File: data/meta_placements.csv — ad_id, ad_name, account, publisher_platform, platform_position, spend, impressions, clicks, link_clicks, landing_page_views
- Top placements: Facebook Feed (45%), Instagram Feed (17%), Facebook Reels (15%), IG Stories (9%)

CREATIVE DATA (from Meta API, cached in CSV):
- File: data/meta_creatives.csv — creative_id, account, creative_name, title, body, cta_type, image_url
- CTA types: GET_QUOTE (50%), LEARN_MORE (27%), GET_OFFER (8%)

META ADS API ACCESS (read-only):
You have access to Meta Ads data through the dashboard's cached CSV files and can reference these accounts:
- ACC1 = act_1530450337262776, ACC2 = act_3985742841525170, ACC3 = act_299067382210535
- ACC4 = act_397070935676618, ACC5 = act_376703401210376 (Traffic), ACC6 = act_1678446012529816
- ACC7 = act_431398042145214, ACC8 = act_3306273819695862, Affiliate = act_458399650269969
- USA1 = act_1406512109835943, USA2 = act_5713736752045739

You can answer questions about: ad spend by placement, creative text analysis, CTA distribution, hypothesis performance, campaign structure.

RULES:
1. You can ONLY answer data/analytics questions. You are a DATA ANALYST — not a developer.
2. NEVER modify code, files, dashboard logic, or any system configuration.
3. If you write SQL, it MUST be SELECT-only. Never INSERT, UPDATE, DELETE, CREATE, DROP, ALTER.
4. Answer in the same language the user writes (Russian or English).
5. Be concise — no lengthy explanations unless asked.
6. When showing numbers, always specify the period and any filters applied.
7. If you're unsure about data, say so — don't guess.
8. You can reference the BQ schema above to write queries if needed.
9. Currency is CAD ($).
10. You can discuss Meta Ads data (placements, creatives, spend) from the cached CSV data described above.
11. If asked to change dashboard code, update logic, edit files, or anything beyond data analysis — politely decline and explain you only have read access.
"""

        # ── Chat UI ──
        if "da_messages" not in st.session_state:
            st.session_state.da_messages = []

        # Quick action buttons
        st.markdown("**Быстрые вопросы:**")
        _qa_cols = st.columns(4)
        with _qa_cols[0]:
            if st.button("📊 Общая сводка", key="qa_summary", use_container_width=True):
                st.session_state.da_messages.append({"role": "user", "content": "Дай общую сводку по текущим данным: лиды, продажи, выручка, CPL, close rate"})
        with _qa_cols[1]:
            if st.button("🏆 Топ гипотезы", key="qa_hyp", use_container_width=True):
                st.session_state.da_messages.append({"role": "user", "content": "Какие топ-5 гипотез по close rate (минимум 50 лидов)?"})
        with _qa_cols[2]:
            if st.button("📍 Лучшие города", key="qa_cities", use_container_width=True):
                st.session_state.da_messages.append({"role": "user", "content": "Какие города дают лучший close rate? Минимум 30 лидов."})
        with _qa_cols[3]:
            if st.button("💰 ROI по воронкам", key="qa_funnel", use_container_width=True):
                st.session_state.da_messages.append({"role": "user", "content": "Сравни close rate и revenue per lead по типам воронок: Quiz Cost Cap, Quiz Bid Cap, Hard Form, Lead Form"})

        st.divider()

        # Display chat history
        for msg in st.session_state.da_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        if _user_input := st.chat_input("Задай вопрос по данным..."):
            st.session_state.da_messages.append({"role": "user", "content": _user_input})
            with st.chat_message("user"):
                st.markdown(_user_input)

            # Call Claude API
            with st.chat_message("assistant"):
                with st.spinner("Думаю..."):
                    try:
                        _api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.da_messages]
                        _response = _client.messages.create(
                            model="claude-haiku-4-5-20251001",
                            max_tokens=2048,
                            system=_da_context,
                            messages=_api_messages,
                        )
                        _answer = _response.content[0].text
                        st.markdown(_answer)
                        st.session_state.da_messages.append({"role": "assistant", "content": _answer})
                    except Exception as e:
                        _err_msg = f"❌ Ошибка API: {str(e)}"
                        st.error(_err_msg)
                        st.session_state.da_messages.append({"role": "assistant", "content": _err_msg})

        # Clear chat button
        if st.session_state.da_messages:
            if st.button("🗑️ Очистить чат", key="clear_chat"):
                st.session_state.da_messages = []
                st.rerun()


elif page == "✅ To Do & Feedback":
    import json as _json
    from pathlib import Path as _Path
    from datetime import datetime as _dt

    st.title("To Do & Feedback")
    st.caption("Список задач из аналитического разбора + блок комментариев от команды.")

    TODO_DIR = _Path(__file__).parent / "todo_data"
    TODO_DIR.mkdir(exist_ok=True)
    TASKS_FILE = TODO_DIR / "tasks.json"
    COMMENTS_FILE = TODO_DIR / "comments.json"

    def _load_json(path, default):
        if not path.exists():
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return _json.load(f)
        except Exception:
            return default

    def _save_json(path, data):
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(data, f, ensure_ascii=False, indent=2)

    STATUS_OPTS = ["todo", "in_progress", "done", "blocked", "dropped"]
    STATUS_LABELS = {
        "todo": "⏳ To Do",
        "in_progress": "🚧 In Progress",
        "done": "✅ Done",
        "blocked": "⛔ Blocked",
        "dropped": "🗑 Dropped",
    }
    PRIORITY_OPTS = ["P0", "P1", "P2", "P3"]

    tab_tasks, tab_feedback, tab_add = st.tabs(["📋 Tasks", "💬 Team Feedback", "➕ Add"])

    # ───────── TASKS TAB ─────────
    with tab_tasks:
        data = _load_json(TASKS_FILE, {"tasks": []})
        tasks = data.get("tasks", [])

        if not tasks:
            st.info("Список задач пуст. Добавьте первую во вкладке **Add**.")
        else:
            # Filters
            fc1, fc2, fc3 = st.columns([1, 1, 2])
            with fc1:
                f_status = st.multiselect(
                    "Status",
                    STATUS_OPTS,
                    default=["todo", "in_progress", "blocked"],
                    format_func=lambda s: STATUS_LABELS.get(s, s),
                )
            with fc2:
                f_priority = st.multiselect("Priority", PRIORITY_OPTS, default=PRIORITY_OPTS)
            with fc3:
                f_search = st.text_input("Search", placeholder="фильтр по названию/описанию…")

            # Summary counts
            total = len(tasks)
            done = sum(1 for t in tasks if t.get("status") == "done")
            in_prog = sum(1 for t in tasks if t.get("status") == "in_progress")
            blocked = sum(1 for t in tasks if t.get("status") == "blocked")
            todo_n = sum(1 for t in tasks if t.get("status") == "todo")

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("Total", total)
            k2.metric("⏳ To Do", todo_n)
            k3.metric("🚧 In Progress", in_prog)
            k4.metric("✅ Done", done)
            k5.metric("⛔ Blocked", blocked)

            st.divider()

            # Filtered list
            filtered = [
                t for t in tasks
                if t.get("status") in f_status
                and t.get("priority") in f_priority
                and (
                    not f_search
                    or f_search.lower() in t.get("title", "").lower()
                    or f_search.lower() in t.get("description", "").lower()
                )
            ]
            # Sort: priority then status
            prio_order = {p: i for i, p in enumerate(PRIORITY_OPTS)}
            status_order = {"in_progress": 0, "todo": 1, "blocked": 2, "done": 3, "dropped": 4}
            filtered.sort(key=lambda t: (
                status_order.get(t.get("status"), 9),
                prio_order.get(t.get("priority"), 9),
            ))

            for t in filtered:
                tid = t.get("id", "?")
                title = t.get("title", "")
                status = t.get("status", "todo")
                prio = t.get("priority", "P2")
                cat = t.get("category", "")
                impact = t.get("impact", "")
                effort = t.get("effort", "")
                owner = t.get("owner", "")
                desc = t.get("description", "")

                header = f"**{STATUS_LABELS.get(status, status)}**  ·  `{tid}`  ·  `{prio}`  ·  {title}"
                with st.expander(header, expanded=False):
                    meta_line = []
                    if cat: meta_line.append(f"**Category:** {cat}")
                    if impact: meta_line.append(f"**Impact:** {impact}")
                    if effort: meta_line.append(f"**Effort:** {effort}")
                    if owner: meta_line.append(f"**Owner:** {owner}")
                    if meta_line:
                        st.markdown("  ·  ".join(meta_line))
                    st.markdown(desc)

                    ec1, ec2, ec3 = st.columns([1.2, 1, 1.5])
                    new_status = ec1.selectbox(
                        "Status", STATUS_OPTS,
                        index=STATUS_OPTS.index(status) if status in STATUS_OPTS else 0,
                        format_func=lambda s: STATUS_LABELS.get(s, s),
                        key=f"st_{tid}",
                    )
                    new_prio = ec2.selectbox(
                        "Priority", PRIORITY_OPTS,
                        index=PRIORITY_OPTS.index(prio) if prio in PRIORITY_OPTS else 2,
                        key=f"pr_{tid}",
                    )
                    new_owner = ec3.text_input("Owner", value=owner, key=f"ow_{tid}")

                    bc1, bc2, _ = st.columns([1, 1, 4])
                    if bc1.button("💾 Save", key=f"sv_{tid}"):
                        for row in tasks:
                            if row.get("id") == tid:
                                row["status"] = new_status
                                row["priority"] = new_prio
                                row["owner"] = new_owner
                                row["updated"] = _dt.now().strftime("%Y-%m-%d %H:%M")
                        _save_json(TASKS_FILE, {"tasks": tasks})
                        st.success(f"{tid} сохранено")
                        st.rerun()
                    if bc2.button("🗑 Delete", key=f"dl_{tid}"):
                        tasks = [r for r in tasks if r.get("id") != tid]
                        _save_json(TASKS_FILE, {"tasks": tasks})
                        st.rerun()

    # ───────── FEEDBACK TAB ─────────
    with tab_feedback:
        st.markdown("Команда может оставлять здесь баги, идеи и запросы на изменения. Всё сохраняется — ты потом просмотришь и решишь, что брать в работу.")

        cdata = _load_json(COMMENTS_FILE, {"comments": []})
        comments = cdata.get("comments", [])

        with st.form("new_comment", clear_on_submit=True):
            fc1, fc2 = st.columns([1, 1])
            c_author = fc1.text_input("Имя", placeholder="кто пишет")
            c_type = fc2.selectbox("Тип", ["🐞 Bug", "💡 Idea", "✏️ Change request", "❓ Question", "📝 Other"])
            c_page = st.selectbox(
                "На какой вкладке замечание",
                ["Overview", "Trends", "Geography", "Lead Detail", "Funnel Analysis",
                 "Campaign Intelligence", "Source Comparison", "Meta Live", "How It Works", "Общее"],
            )
            c_text = st.text_area("Комментарий", placeholder="опиши подробно…", height=120)
            submitted = st.form_submit_button("📩 Отправить")
            if submitted:
                if not c_text.strip():
                    st.warning("Комментарий не может быть пустым")
                else:
                    new_id = f"C{len(comments) + 1:04d}"
                    comments.append({
                        "id": new_id,
                        "author": c_author or "anonymous",
                        "type": c_type,
                        "page": c_page,
                        "text": c_text.strip(),
                        "status": "new",
                        "created": _dt.now().strftime("%Y-%m-%d %H:%M"),
                    })
                    _save_json(COMMENTS_FILE, {"comments": comments})
                    st.success(f"Сохранено как {new_id}")
                    st.rerun()

        st.divider()
        st.markdown(f"**Всего комментариев: {len(comments)}**")

        if comments:
            f1, f2 = st.columns([1, 1])
            filter_status = f1.multiselect(
                "Статус", ["new", "reviewed", "in_progress", "resolved", "wontfix"],
                default=["new", "reviewed", "in_progress"],
            )
            filter_type = f2.multiselect(
                "Тип",
                ["🐞 Bug", "💡 Idea", "✏️ Change request", "❓ Question", "📝 Other"],
                default=["🐞 Bug", "💡 Idea", "✏️ Change request", "❓ Question", "📝 Other"],
            )

            shown = [c for c in comments if c.get("status") in filter_status and c.get("type") in filter_type]
            shown.sort(key=lambda c: c.get("created", ""), reverse=True)

            for c in shown:
                cid = c.get("id", "?")
                header = f"**{c.get('type','')}**  ·  `{cid}`  ·  *{c.get('page','')}*  ·  {c.get('author','')}  ·  {c.get('created','')}  ·  `{c.get('status','new')}`"
                with st.expander(header, expanded=False):
                    st.markdown(c.get("text", ""))
                    ac1, ac2, _ = st.columns([1.5, 1, 3])
                    new_st = ac1.selectbox(
                        "Статус", ["new", "reviewed", "in_progress", "resolved", "wontfix"],
                        index=["new", "reviewed", "in_progress", "resolved", "wontfix"].index(c.get("status", "new")),
                        key=f"cst_{cid}",
                    )
                    if ac2.button("💾 Update", key=f"csv_{cid}"):
                        for row in comments:
                            if row.get("id") == cid:
                                row["status"] = new_st
                                row["updated"] = _dt.now().strftime("%Y-%m-%d %H:%M")
                        _save_json(COMMENTS_FILE, {"comments": comments})
                        st.rerun()
                    if st.button("🗑 Delete comment", key=f"cdl_{cid}"):
                        comments = [r for r in comments if r.get("id") != cid]
                        _save_json(COMMENTS_FILE, {"comments": comments})
                        st.rerun()
        else:
            st.info("Пока комментариев нет.")

    # ───────── ADD TASK TAB ─────────
    with tab_add:
        st.markdown("Добавить новую задачу в список.")
        with st.form("new_task", clear_on_submit=True):
            nt_title = st.text_input("Название *")
            nt_cat = st.text_input("Категория", placeholder="например, Sprint 1 · Revenue")
            c1, c2, c3 = st.columns(3)
            nt_prio = c1.selectbox("Приоритет", PRIORITY_OPTS, index=1)
            nt_impact = c2.selectbox("Impact", ["Very High", "High", "Medium", "Low"], index=2)
            nt_effort = c3.selectbox("Effort", ["S", "M", "L", "XL"], index=1)
            nt_owner = st.text_input("Owner", placeholder="кто отвечает")
            nt_desc = st.text_area("Описание (что делает задача и зачем)", height=150)
            add_sub = st.form_submit_button("➕ Добавить задачу")
            if add_sub:
                if not nt_title.strip():
                    st.warning("Название обязательно")
                else:
                    data = _load_json(TASKS_FILE, {"tasks": []})
                    existing = data.get("tasks", [])
                    new_id = f"T{len(existing) + 1:02d}"
                    # Ensure unique id
                    existing_ids = {t.get("id") for t in existing}
                    i = len(existing) + 1
                    while new_id in existing_ids:
                        i += 1
                        new_id = f"T{i:02d}"
                    existing.append({
                        "id": new_id,
                        "title": nt_title.strip(),
                        "category": nt_cat.strip(),
                        "priority": nt_prio,
                        "impact": nt_impact,
                        "effort": nt_effort,
                        "owner": nt_owner.strip(),
                        "description": nt_desc.strip(),
                        "status": "todo",
                        "created": _dt.now().strftime("%Y-%m-%d"),
                    })
                    _save_json(TASKS_FILE, {"tasks": existing})
                    st.success(f"Добавлено: {new_id}")
                    st.rerun()


elif page == "📖 How It Works":
    st.title("How It Works — Analytics Methodology")
    st.caption("Last updated: April 2026 · Update this page whenever counting logic changes.")

    lang = st.radio("Language", ["🇬🇧 English", "🇷🇺 Русский"], horizontal=True, label_visibility="collapsed")
    st.divider()

    if lang == "🇷🇺 Русский":

        # ── РУС 1. ДАННЫЕ ────────────────────────────────────────────────────
        st.markdown("## 1. Откуда берутся данные")
        st.markdown("""
Все данные хранятся в **BigQuery** — это наша база данных в облаке.

**Как данные попадают в BQ:** парсер запускается вручную каждый день около 13:00 (Berlin time). Он выгружает все лиды из CRM и загружает в BigQuery. У парсера есть параметр **conversion window** — сколько дней после получения лида он ищет аппойнтменты и продажи.

**Важно:** до 6 апреля 2026 парсер работал с окном **20 дней**. Это означало что аппойнтменты, забронированные позже 20 дней после лида, **терялись** — не попадали в BQ. С 6 апреля 2026 окно расширено до **100 дней**. Это вернуло исторически потерянные данные:

| Окно бронирования | Апп-тов | Продаж | % от всех |
|---|---|---|---|
| 0–7 дней | 16,067 | 2,028 | 86.9% |
| 8–14 дней | 635 | 86 | 3.4% |
| 15–20 дней | 284 | 36 | 1.5% |
| **21–100 дней (ранее потеряно)** | **1,503** | **205** | **8.1%** |

- **Лиды** — заявки с наших лендингов. Там есть телефон, имейл, почтовый индекс, UTM-метки (откуда пришёл человек) и время подачи заявки.
- **Статусы лидов** — что стало с каждой заявкой в CRM: записан ли на приём, отменил ли, купил ли.
- **Звонки** — входящие звонки через специальные DNI-номера (каждый источник рекламы имеет свой номер). Считаем только первый звонок с каждого номера.
- **Расходы** — ежедневные затраты на рекламу в Meta и TikTok, с разбивкой по провинциям.
""")

        st.divider()

        # ── РУС 2. ДАТА ЛИДА ─────────────────────────────────────────────────
        st.markdown("## 2. Главный принцип: всё считаем по дате заявки")
        st.markdown("""
Все показатели — заявки, записи на приём, продажи, отмены — **привязываются к тому месяцу, когда человек подал заявку**, а не к тому, когда произошло событие.

Например: человек оставил заявку в марте, встреча была в апреле, продажа состоялась в мае — всё это считается **за март**.

Это важно, потому что именно так работает маркетинг: ты вложил деньги в марте, значит и результаты марта. Так же считается в нашей основной таблице в BigQuery.
""")

        st.divider()

        # ── РУС 3. ИСТОЧНИКИ ─────────────────────────────────────────────────
        st.markdown("## 3. Как определяется источник")
        st.markdown("""
**Форм-заявки** определяются по UTM-меткам:
- Facebook / FB → **META**
- TikTok → **TikTok**
- ActiveCampaign → **Other**
- Всё остальное → **Other**

**Входящие звонки** — это люди, которые увидели нашу рекламу и позвонили напрямую, не заполняя форму. Они идут в тот же источник, что и реклама (META и т.д.). Это **не отдельный источник**, а часть общего потока.

Звонки можно посмотреть отдельно на странице "Source Comparison" в блоке "Calls Breakdown".
""")

        st.divider()

        # ── РУС 4. ЧИСТЫЕ ЛИДЫ ───────────────────────────────────────────────
        st.markdown("## 4. Что такое «чистый лид»")
        st.markdown("""
Не каждая заявка считается в статистику. Лид считается **чистым**, если:

- У него есть **действующий канадский номер телефона** (10 цифр). Это главный критерий.
- Если телефона нет — нужен **имейл**, но только если человек уже как-то отреагировал (записался на приём или был отменён). Просто имейл без телефона и без активности — не считаем.
- Дубли за последние 45 дней — тоже не считаем. Если тот же телефон / имейл уже был, новая заявка не засчитывается.

**Исключения:**
- Если человек записался на приём или его отменили — считаем всегда, даже без телефона.
- Звонки всегда чистые — если человек позвонил сам, это реальный интерес.
""")

        st.divider()

        # ── РУС 5. ЗАПИСЬ НА ПРИЁМ ───────────────────────────────────────────
        st.markdown("## 5. Как считаются записи на приём")
        st.markdown("""
Запись на приём фиксируется в момент, **когда менеджер договорился с клиентом о встрече** — это дата в поле `cf_booked_date` в CRM. Именно этот момент мы используем для подсчёта.

Отдельно от этого есть **дата самой встречи** (`cf_appointment_date`) — это когда замерщик едет к клиенту. Она нужна только чтобы понять, прошла встреча уже или ещё нет.

В обычном режиме (Overview) считаются **все записи** для лидов за выбранный период — не важно, когда встреча.
""")

        st.divider()

        # ── РУС 6. СТАТУСЫ В CRM ─────────────────────────────────────────────
        st.markdown("## 6. Статусы в CRM")
        st.markdown("""
| Статус | Что значит |
|---|---|
| `lead` | Подал заявку / позвонил. Встреча ещё не назначена. |
| `appointment` | Встреча назначена. Ещё не состоялась (или CRM не обновлена). |
| `cancelled before appt` | Отменил минимум за 1 день до встречи. Замерщик не ездил. |
| `cancelled` | Замерщик съездил, клиент отказался от сделки. |
| `sold` | Замерщик съездил, договор подписан. |

Важно: для отменённых записей дата отмены в CRM часто совпадает с датой встречи — это особенность CRM, поэтому мы всегда смотрим на статус, а не на дату.
""")

        st.divider()

        # ── РУС 7. ПРЕДСТОЯЩИЕ / ОЖИДАЮЩИЕ / БЫЛИ НА ВСТРЕЧЕ ─────────────────
        st.markdown("## 7. Предстоящие, ожидающие и были на встрече")
        st.markdown("""
Все записи на приём делятся на три группы:

- **Предстоящие (Upcoming)** — встреча ещё не прошла (сегодня тоже считается). CRM обновлять не нужно.

- **Ожидающие (Pending)** — дата встречи уже прошла, но в CRM статус до сих пор «appointment». Включены в Upcoming. Когда CRM обновится, перейдут в sold или cancelled.

- **Были на встрече (Showed Up)** — все, у кого встреча уже состоялась: sold + cancelled + ожидающие (у которых дата прошла).

**Show Rate** — процент людей, которые пришли на встречу, от всех записей.
""")

        st.divider()

        # ── РУС 8. ПРОГНОЗ ПРОДАЖ ────────────────────────────────────────────
        st.markdown("## 8. Прогноз продаж")
        st.markdown("""
**Основной метод: ML-модель (машинное обучение)**

Каждая предстоящая встреча оценивается индивидуально — модель смотрит на конкретного клиента и говорит, какова вероятность, что он купит. Сумма всех вероятностей = прогноз продаж.

Это точнее, чем просто умножить количество встреч на средний процент закрытия, потому что учитывается конкретный состав.

**На что смотрит модель (обучена на ~12 300 закрытых записях с января 2024):**
- **Провинция** — в NB и Манитобе закрываемость выше (~21%), в Ньюфаундленде ниже (~12%).
- **Город** — даже внутри одной провинции города сильно отличаются. Например, Калгари закрывает ~14%, а Эдмонтон ~18% (обе Альберта). Монктон (NB) — ~25%, Ванкувер — ~15%. Модель знает ~22 крупных города отдельно, остальные идут в общую группу.
- **Тип кампании** — LG-формы закрываются хуже (~14.5%), CONV-кампании лучше (~18.3%), прямые обращения лучше всего (~24%).
- **Сколько дней между записью и встречей** — оптимально 8–14 дней. Очень долгое ожидание снижает шансы.
- **Сезон** — весна и начало лета закрываются лучше, осень хуже.
- **Скорость записи** — чем быстрее менеджер записал лида на встречу, тем выше шанс продажи.

**Точность модели:** AUC 0.596 (было 0.575 до добавления города). Добавление города заметно улучшило модель.

**Запасной вариант:** если ML-модель недоступна, используется исторический сезонный процент по календарному месяцу (апрель ~15%, октябрь ~8%).

**Таблица точности прогнозов** — в Overview в блоке "Prediction Model Accuracy" можно посмотреть, насколько точно модель предсказывала продажи в прошлые месяцы.

**Переобучение модели:** запускается командой `python utils/train_model.py`. Рекомендуется раз в полгода или если точность заметно падает.
""")

        st.divider()

        # ── РУС 9. РАСХОДЫ ───────────────────────────────────────────────────
        st.markdown("## 9. Расходы на рекламу")
        st.markdown("""
**Два источника расходов — в зависимости от того, что считается:**

**`meta_spend_cache.json` (без задержки Windsor)** — используется для дневных трендов и суммарного спенда:
- Трендовые графики расходов по дням (Trends)
- Сравнение периодов (comp_spend)
- Метрика "Meta Direct (API)" на панели сверки Windsor
- Total Meta Spend в разделе Creative

Кэш обновляется автоматически ежедневно + глубокий пересинк каждый понедельник за последние 30 дней (для корректировки ретроактивных правок Windsor). Данные агрегируются по всем 9 канадским Meta-аккаунтам.

**BigQuery `raw.spend_geo_snap` (через Windsor AI, задержка 1–2 дня)** — используется только для географической разбивки:
- Распределение расходов по провинциям и городам

Итого: **дневные тренды и суммарный спенд = кэш (актуально), разбивка по гео = BigQuery (с задержкой)**.

- Расходы Affiliate в базе нет.
- **CPL** (стоимость чистого лида) = расходы ÷ чистые лиды
- **CPA** (стоимость аппойнтмента) = расходы ÷ аппойнтменты
- **CPA1** (стоимость состоявшегося визита) = расходы ÷ (все аппы − upcoming). Учитывает только уже состоявшиеся аппы, исключая те что ещё не прошли.
- **CPS** (стоимость продажи) = расходы ÷ продажи
- Расходы по провинциям распределяются пропорционально количеству лидов из каждого города.
""")

        st.divider()

        # ── РУС 10. МАППИНГ ГОРОДОВ ──────────────────────────────────────────
        st.markdown("## 10. Как лиды распределяются по городам")
        st.markdown("""
Каждая заявка содержит **почтовый индекс** (postal code), который мы используем для определения города.

**Цепочка маппинга:**

1. Берём первые 3 символа почтового индекса — это **FSA** (Forward Sortation Area, например `T2P` = центр Калгари).
2. Сравниваем FSA с таблицей `raw.city_map` в BigQuery → получаем город.
3. Первый символ FSA сравниваем с `raw.province_map` → получаем провинцию.

**Что если индекс не распознан?**

Лид попадает в категорию **«Unknown city»**. Это происходит когда:
- Человек не заполнил поле индекса (пусто / null)
- Написал адрес вместо индекса (например «152 Montfort Street»)
- Нестандартный код (например `F2K` — не существует в Канаде)

За неделю 23–29 марта в «Unknown» попало **28 лидов** — и у всех 0 аппойнтментов. Потери аппойнтментов от маппинга нет.

**Города где Ecoline работает (верифицировано по BQ, апрель 2026):**

| Провинция | Активные города (≥1 апп за 90 дней) |
|---|---|
| Alberta | Calgary, Edmonton, Red Deer, Lethbridge, Medicine Hat, Grande Prairie, Lloydminster |
| British Columbia | Vancouver, Victoria, Kelowna, Kamloops, Nanaimo, Prince George |
| Ontario | Ottawa, Kingston, Kenora |
| Manitoba | Winnipeg, Brandon |
| Saskatchewan | Saskatoon, Regina, Moose Jaw |
| New Brunswick | Moncton, Fredericton, Saint John |
| Nova Scotia | Halifax, Sydney |
| Newfoundland | St. John's |
| PEI | Charlottetown |

**Города «плохого гео» (лиды есть, аппов нет — мониторим дрейф FB таргетинга):**
Toronto (465 лидов), Thunder Bay (83), Kingston-дубль (90), NU/NT (27), Yukon (22), Sudbury (12)

**Источник лида — как определяется:**

| utm_source | Источник в дашборде |
|---|---|
| facebook, meta, fb | META |
| google, adwords | GOOGLE |
| пусто / null | DIRECT |
| всё остальное | OTHER |

Кампании Affiliate определяются по `utm_campaign` или по аккаунту Ecoline Affiliate в Meta.
""")

        st.divider()

        # ── РУС 11. МЕТА ЛАЙВ ────────────────────────────────────────────────
        st.markdown("## 11. Вкладка Meta Live — прямая интеграция с Meta")
        st.markdown("""
**Meta Live** — это отдельная аналитика по рекламным кампаниям напрямую из Meta API, без задержки Windsor AI.

**Архитектура:**

- Данные о расходах, показах, CPM, CPC и лидах (Meta) берутся **прямо из Meta API** через Claude (MCP-инструменты).
- Клод обновляет кэш-файлы (`meta_cache/campaigns_*.json`) по запросу или по расписанию.
- Streamlit читает эти JSON-файлы — никаких прямых API-вызовов из дашборда.

**Два типа лидов в Meta Live:**

| Метрика | Откуда | Что значит |
|---|---|---|
| **Leads (Meta)** | Meta API | Сырой счётчик отправок формы. Включает спам, невалидные контакты, нет дедупликации. |
| **Leads (BQ, clean)** | BigQuery | Чистые дедуплицированные лиды — та же логика что в Overview. |

**Почему они отличаются** (пример за 23–29 марта):
- Meta API: **1,344** (все отправки)
- BQ all leads: **1,306** (прошли SQL-фильтр: валидный телефон / email / есть апп)
- BQ clean leads: **1,240** (после дедупликации в окне 45 дней)

**CPL (raw)** = расходы ÷ Meta leads → занижен, потому что знаменатель завышен спамом.

**CPL (clean)** = расходы ÷ BQ clean leads → совпадает с Overview. Это настоящая стоимость лида.

**Провинциальный разбор национальных кампаний:**

Для кампаний `ALL REGIONS` Meta API умеет давать разбивку по провинциям (Alberta, BC, Ontario...) — это реальные данные от Meta. Внутри каждой провинции разбивка по городам считается по BQ данным той же недели, той же категории кампании (LG или CONV).

**Период и даты:**

Meta Live имеет свой выбор периода (вчера / 7 дней / Custom range). Этот период используется и для Meta API данных, и для фильтрации BQ данных. Глобальный sidebar дашборда на Meta Live не влияет.
""")

        st.divider()

        # ── РУС 12. CREATIVE PERFORMANCE ────────────────────────────────────
        st.markdown("## 12. Вкладка Creative Performance — анализ креативов")
        st.markdown("""
Вкладка **🎨 Creative Performance** показывает как работает каждый тип креатива и каждая рекламная гипотеза на уровне лид → аппойнтмент → продажа.

**Откуда берутся данные:**

Все данные — из тех же BQ таблиц и с той же логикой что и остальной дашборд (`load_leads` → `apply_dedup` → `is_clean`). Тип креатива и гипотеза парсятся из поля `utm_content`, тип воронки — из `utm_term` (название адсета).

**Как определяется тип креатива:**

| utm_content начинается с | Тип |
|---|---|
| `IMAGE - Hyp ...` | IMAGE |
| `VIDEO - Hyp ...` | VIDEO |
| `DCO - IMAGE - Hyp ...` | DCO-IMAGE |
| `DCO - VIDEO - Hyp ...` | DCO-VIDEO |

**Как определяется гипотеза:**

Из `utm_content` извлекается число после `Hyp` (например `IMAGE - Hyp 111.1 - IT 3` → `Hyp 111.1`). Для «0 Down» ищется строка `0 down` / `0down`.

**Как определяется тип воронки (Funnel Type):**

Тип определяется по `utm_term` (название адсета в Meta):

| utm_term содержит | Тип воронки | Куда ведёт |
|---|---|---|
| `cost cap` | Quiz (Cost Cap) | quiz.ecolinewindows.ca/* |
| `bid cap` | Quiz (Bid Cap) | quiz.ecolinewindows.ca/* |
| `hard form` | Hard Form | quiz.ecolinewindows.ca/* (другая форма) |
| `form m/i` | Lead Form | Нативная форма Meta (in-app) |
| `aff` + `form`/`creo` | Affiliate | Партнёрские формы |

**Метрики:**

| Метрика | Формула |
|---|---|
| Dirty Rate (%) | (appointment + sold + cancelled + cancelled before appt) / leads × 100 |
| Clean Rate (%) | (sold + cancelled) / leads × 100 |
| Close Rate (%) | sold / leads × 100 |
| Rev/Lead ($) | revenue / leads |
| Avg Sale ($) | revenue / sold |

**Флаги качества данных:**

Каждая гипотеза проверяется на аномалии:

- ⚠️ **Small sample** (<30 лидов) — выводы ненадёжны
- ⚠️ **Zero sales** — слишком рано судить
- 🔍 **Close rate 2.5x выше среднего** при малом объёме — может быть случайность
- 🔍 **Dirty rate >55%** — подозрительно высокий, возможно UTM naming шарится с другими кампаниями
- 🔍 **Avg sale 2x выше/ниже нормы** — проверить на выбросы

**Ограничения spend (по гипотезам):**

Spend по отдельным гипотезам/креативам в основных табах (IMAGE vs VIDEO, By Hypothesis, By Funnel Type) **не доступен**. Расходы из Windsor загружаются агрегировано по дате + провинции, без разбивки по ad name.

**Новые табы (📍 By Placement, 📝 Ad Copy):**

Эти табы используют **отдельный кеш данных из Meta API** (файлы `data/meta_placements.csv` и `data/meta_creatives.csv`), которые обновляются ежедневно scheduled task'ом `meta-creative-sync` в 7:00.

**📍 By Placement** — куда уходит бюджет по плейсментам Meta:

| Плейсмент | Описание |
|---|---|
| Facebook Feed | Основная лента FB |
| Instagram Feed | Лента IG |
| Facebook Reels / IG Reels | Короткие видео |
| IG Stories / FB Stories | Сторис |
| FB Marketplace | Маркетплейс |
| Audience Network | Партнёрские площадки |

Данные: spend, impressions, clicks, link clicks, landing page views, CPM, CTR, CPC. Также разбивка spend по топ-гипотезам × плейсментам.

**📝 Ad Copy** — анализ рекламных текстов:

- **CTA Distribution** — какие кнопки (GET_QUOTE, LEARN_MORE, GET_OFFER) используются
- **Top Headlines** — самые частые заголовки объявлений
- **Top Opening Lines (Hooks)** — первые строки body text, группировка по частоте использования
- **Creative Copy ↔ Lead Performance** — матчинг creative_name из Meta API с utm_content из BQ → связь текста с конверсиями
- **Full Creative Library** — поиск по библиотеке всех креативов (1,400+ записей)

**Источник данных для новых табов:**

Meta Ads API → `get_insights` (уровень ad, breakdowns: publisher_platform + platform_position) + `get_ad_creatives` → парсинг → CSV. Покрывает 9 CAD аккаунтов, данные с января 2024.
""")

        st.divider()

        # ── РУС 13. DATA ASSISTANT ────────────────────────────────────────
        st.markdown("## 13. Вкладка Data Assistant — AI-чат по данным")
        st.markdown("""
Вкладка **💬 Data Assistant** — это AI-чат встроенный прямо в дашборд. Сотрудник может задать любой вопрос по данным на русском или английском и получить быстрый ответ с цифрами.

**Что можно спрашивать (примеры):**

| Категория | Примеры вопросов |
|---|---|
| Общая аналитика | «Дай сводку за последний месяц», «Какой у нас CPL?», «Сколько продаж было?» |
| Гипотезы | «Какие топ-5 гипотез по close rate?», «Сравни Hyp 111.1 и Hyp 0 Down» |
| Города / провинции | «Какие города лучше конвертят?», «Сравни Калгари и Эдмонтон», «Где самый низкий CPL?» |
| Воронки | «Что лучше — Quiz или Lead Form?», «ROI по каждому типу воронки» |
| Плейсменты | «Где мы больше всего тратим — FB Feed или IG Stories?», «Какой плейсмент самый дешевый по CPC?» |
| Креативы | «Какие заголовки используются чаще?», «Топ CTA типов», «Какие тексты объявлений?» |
| Тренды | «Как менялся close rate за последние 3 месяца?», «Растёт ли CPL?» |
| SQL-запросы | «Напиши SQL для топ-10 городов по выручке», «Сколько лидов с utm_source=facebook?» |

**Быстрые кнопки:**

Вверху чата есть 4 кнопки для частых запросов:

| Кнопка | Что делает |
|---|---|
| 📊 Общая сводка | Лиды, продажи, выручка, CPL, close rate за выбранный период |
| 🏆 Топ гипотезы | Топ-5 гипотез по close rate (мин. 50 лидов) |
| 📍 Лучшие города | Города с лучшим close rate (мин. 30 лидов) |
| 💰 ROI по воронкам | Сравнение Quiz Cost Cap, Bid Cap, Hard Form, Lead Form |

**Доступ к данным:**

| Источник | Доступ | Описание |
|---|---|---|
| BigQuery (BQ) | ✅ SELECT-only | raw.leads + raw.leads_status — лиды, статусы, суммы, UTM, города |
| Meta Ads (кеш) | ✅ Чтение | Плейсменты (spend/CPM/CTR), креативы (тексты/headlines/CTA) из CSV |
| Meta аккаунты | ✅ Справочно | Знает все 11 аккаунтов (ACC1-ACC8, Affiliate, USA1, USA2) |

**Ограничения (read-only):**

- ❌ Не может менять код дашборда, файлы или логику
- ❌ Не может выполнять INSERT, UPDATE, DELETE, CREATE, DROP
- ❌ Не может менять настройки или структуру дашборда
- ❌ Если попросить изменить что-то — вежливо откажет
- ✅ Может только читать и анализировать данные

**Контекст AI:**

При каждом запросе ассистент автоматически получает:
- Текущие цифры дашборда (лиды, продажи, выручка, spend за выбранный период в sidebar)
- Полную схему BQ таблиц (raw.leads + raw.leads_status) с описанием полей
- Информацию о placement и creative данных (из ежедневного Meta API кеша)
- Правила: отвечать на языке вопроса, быть точным, указывать период, не угадывать

**Настройка:**

Требуется API ключ Anthropic (Claude). Ключ берётся на [console.anthropic.com](https://console.anthropic.com) → Settings → API Keys. Добавить в `.streamlit/secrets.toml`:
```
ANTHROPIC_API_KEY = "sk-ant-api03-..."
```
Это **отдельно** от подписки на claude.ai — нужен именно API ключ.

**Модель:** Claude Sonnet 4 (`claude-sonnet-4-20250514`)

**Будущие расширения:**

| Skill | Описание |
|---|---|
| Media Buyer | Советы по оптимизации рекламных кампаний, бюджету, ставкам |
| Creative Strategist | Анализ креативов, рекомендации по текстам и визуалу |
| Data Analyst | Глубокий анализ данных, когортный анализ, атрибуция |
| CRO Specialist | Оптимизация конверсии, A/B тесты, воронки |
| MCP Ads Library | Прямой доступ к библиотеке рекламных объявлений (R&D) |
""")

        st.divider()

        # ── РУС 14. ИСТОРИЯ ИЗМЕНЕНИЙ ────────────────────────────────────────
        st.markdown("## 14. Что менялось")
        st.markdown("""
| Дата | Изменение |
|---|---|
| Апр 2026 | **💬 Data Assistant** — AI-чат на базе Claude Sonnet 4. Сотрудники могут задавать вопросы по данным и получать мгновенные ответы. Read-only: не может менять код или данные. Быстрые кнопки + контекст BQ схемы. |
| Апр 2026 | **📍 By Placement + 📝 Ad Copy табы** — два новых таба в Creative Performance. Placement показывает распределение spend по FB Feed / IG Stories / Reels и т.д. Ad Copy анализирует тексты объявлений: headlines, hooks, CTA types, и связывает с конверсиями через utm_content. Данные из Meta API (9 аккаунтов, с Jan 2024). |
| Апр 2026 | **Scheduled task `meta-creative-sync`** — ежедневное обновление placement и creative данных из Meta API в 7:00. |
| Апр 2026 | **Конверсионное окно парсера расширено** с 20 до 100 дней. Ранее терялось ~8% аппов и ~10% продаж, забронированных позже 20 дней после лида. |
| Апр 2026 | **4-недельный календарь аппойнтментов** в Trends — ежедневные буки по сегментам Meta·LG / Meta·CONV / Calls / Affiliate с YoY дельтой (−52 недели). |
| Апр 2026 | **Верификация городов** — список активных городов и провинций сверен с BQ данными за 90 дней. Убраны фантомные города (Hamilton, London, Brampton, Abbotsford и др.), добавлены реальные: Lloydminster, Prince George, Moose Jaw, Sydney NS. Исправлена NS Nova Scotia (Cape Breton Island → Sydney). |
| Апр 2026 | **Вкладка Meta Live** — прямая интеграция с Meta API через Claude MCP. Данные без задержки Windsor. |
| Апр 2026 | **CPL (clean) в Meta Live** — добавлен корректный CPL по чистым BQ лидам, совпадает с Overview. |
| Апр 2026 | **Meta Live привязан к своему периоду** — BQ данные в Meta Live теперь фильтруются по периоду вкладки, а не по глобальному sidebar. |
| Апр 2026 | **Провинциальный разбор** национальных кампаний в Meta Live — реальные данные по провинциям из Meta API + разбивка по городам из BQ. |
| Апр 2026 | **ML-модель v3** — добавлен город как признак (топ-22 + OTHER_CITY). Калгари 14% vs Эдмонтон 18%. AUC вырос 0.575 → 0.596. |
| Апр 2026 | **ML-модель v2** — тип кампании LG/CONV вместо utm_medium. LG закрывается 14.5%, CONV 18.3%. Ошибка 4.6 → 4.2 продажи. |
| Апр 2026 | **ML-модель v1** — логистическая регрессия, 11,927 встреч за 2024–2026. AUC 0.587. |
| Апр 2026 | **Сезонная модель прогноза** — ошибка 11.9% против плоских 16.5%. Апрель ~15%, октябрь ~8%. |
| Апр 2026 | **Запись на приём по дате бронирования** (`cf_booked_date`), а не дате визита. |
| Апр 2026 | **Upcoming**: встречи на сегодня считаются предстоящими (не pending). |
| Апр 2026 | **Pending** — новая метрика: дата встречи прошла, CRM не обновлена. |
| Апр 2026 | **Звонки** отнесены к родительскому источнику (META, Affiliate). |
| Апр 2026 | **Чистые лиды**: email-лиды без телефона и активности — не чистые. |
| Апр 2026 | **Все метрики по дате заявки**, не по дате события. |
""")

    else:

        st.divider()

        # ── 1. DATA SOURCES ──────────────────────────────────────────────────────
        st.markdown("## 1. Data Sources")
        st.markdown("""
**All data lives in BigQuery (project: `ecolinew`).**

**Data pipeline:** The CRM parser runs manually every day around 13:00 Berlin time. It exports all leads from CRM and loads them into BigQuery. The parser has a **conversion window** parameter that controls how many days after lead creation it searches for appointments and sales.

**Important — conversion window change (Apr 6, 2026):** Before this date the parser used a **20-day** window. Appointments booked more than 20 days after the lead were **lost** — never loaded into BQ. Since Apr 6, the window is **100 days**. This recovered historically missing data:

| Booking window | Appts | Sold | % of all |
|---|---|---|---|
| 0–7 days | 16,067 | 2,028 | 86.9% |
| 8–14 days | 635 | 86 | 3.4% |
| 15–20 days | 284 | 36 | 1.5% |
| **21–100 days (previously lost)** | **1,503** | **205** | **8.1%** |

- **`raw.leads`** — web form submissions from Ecoline's landing pages. Contains UTM tracking (source, medium, campaign, content, term), phone, email, postal code, submission timestamp.
- **`raw.leads_status`** — CRM status for each lead: appointment status, booked date, appointment date, sold date, cancelled date, contract amount.
- **`raw.calls`** — inbound phone calls tracked via DNI (Dynamic Number Insertion). Filtered to `first_call = TRUE` so repeat callers aren't double-counted.
- **`raw.calls_status`** — same CRM status fields as leads_status, joined to call records.
- **`raw.spend_snap` / `raw.spend_geo_snap`** — daily ad spend from Meta and TikTok, with province-level geo breakdown.
- **`raw.upd_hd`** — CRM export with `LeadType` field: `facebook-overflow` (Ecoline/META), `affiliate`, `home-depot`. Used to identify which brand a lead belongs to.
""")

        st.divider()

        # ── 2. LEAD ATTRIBUTION ───────────────────────────────────────────────────
        st.markdown("## 2. Lead Attribution — Date Logic")
        st.markdown("""
**All metrics are keyed off the lead submission date (`l.dt`), not the appointment date or sale date.**

- A lead that submitted in March owns all its downstream events (appointment, sale, cancellation) in March — regardless of when those events occur.
- This matches the `report.monthly` table in BigQuery which is the source of truth for historical comparisons.
- The date range filter in the sidebar controls which leads are loaded. Everything else (appointment, sale, cancellation) follows from those leads.
""")

        st.divider()

        # ── 3. SOURCES ────────────────────────────────────────────────────────────
        st.markdown("## 3. Source Classification")
        st.markdown("""
**Form leads** (from `raw.leads`) are classified by `utm_source`:
- `facebook` or `fb` → **META**
- `tiktok` or `tiktok-form` → **TikTok**
- `activecampaign` → **Other**
- anything else → **Other**

**Inbound calls** (from `raw.calls`) are classified by the tracking number dialled:
- Facebook Inbound / Facebook New Landing Page → **META**
- Future new tracking numbers → add to `_call_source()` in `data.py`

Calls are **part of their parent source funnel** (META, etc.), not a separate source.
They are still identifiable via `source_type = "call"` for breakout analysis (see Source Comparison → Calls Breakdown).
""")

        st.divider()

        # ── 4. CLEAN LEADS ────────────────────────────────────────────────────────
        st.markdown("## 4. Clean Leads Definition")
        st.markdown("""
A lead is **clean** if it passes deduplication AND has a valid contact method. Applied via `apply_dedup()` in `utils/data.py`.

**Deduplication key priority:**
1. Valid 10-digit North American phone (`[2-9][0-9]{9}`) — primary identifier
2. Email (fallback when phone is invalid)
3. `row_num` — last resort, always unique

**Dedup window (default: 45 days):** if the same phone/email appeared within the last 45 days, the newer record is marked NOT clean (duplicate).

**Hard overrides — always clean:**
- Lead has a `cf_appointment_date` or `cf_cancelled_date` AND is **not** a duplicate within the dedup window → confirmed funnel engagement, always counted.
- Note: if the same phone/email appeared within the dedup window, deduplication takes priority even if the duplicate has an appointment. This prevents re-submits from bypassing the dedup window.

**Hard overrides — never clean:**
- Invalid phone + valid email + status = `lead` (no CRM activity, no appointment) → email-only leads that never responded are excluded. They can't be reliably contacted or tracked.
- No phone + no email → excluded entirely.

**Calls:** all first-time callers (`first_call = TRUE`) are clean by definition. They called us — they're real.
""")

        st.divider()

        # ── 5. APPOINTMENT COUNTING ───────────────────────────────────────────────
        st.markdown("## 5. Appointment Counting")
        st.markdown("""
**An appointment exists when `cf_booked_date IS NOT NULL`** — this is the moment the lead agreed on the call to schedule an in-home visit. This is the marketer's conversion event.

- `cf_booked_date` = when the appointment was booked (conversion moment) ✅ used for counting
- `cf_appointment_date` = when the in-home visit is scheduled (used for upcoming/pending logic only)
- `cf_sold_date` = when the contract was signed

**In Overview mode** (`appt_window = None`): all appointments for leads in the selected period are counted, regardless of when the appointment is scheduled. This matches `report.monthly`.

**In Funnel Analysis mode** (`appt_window = N days`): only appointments scheduled within N days of lead submission are counted (interactive slider on Funnel Analysis page only).
""")

        st.divider()

        # ── 6. APPOINTMENT STATUSES ───────────────────────────────────────────────
        st.markdown("## 6. Appointment Statuses")
        st.markdown("""
Source of truth: **`status_with_cancelled`** field in `raw.leads_status` / `raw.calls_status`.

| Status | Meaning |
|---|---|
| `lead` | Submitted form / called in. No appointment booked yet. |
| `appointment` | Appointment booked. Visit not yet happened (or CRM not updated). |
| `cancelled before appt` | Cancelled at least 1 day before scheduled visit. Technician never went out. |
| `cancelled` | Visit happened. Lead did not agree to quote. |
| `sold` | Visit happened. Contract signed. |

**Important:** `cf_cancelled_date` mirrors `cf_appointment_date` for cancelled records — date comparisons on cancelled_date are unreliable. Always use `status_with_cancelled` to determine cancellation type.
""")

        st.divider()

        # ── 7. UPCOMING / PENDING / SHOWED UP ─────────────────────────────────────
        st.markdown("## 7. Upcoming, Pending & Showed Up")
        st.markdown("""
These three states break down the `appointment` status bucket:

- **Upcoming** = `status = appointment` (all appointments not yet resolved to sold/cancelled).
  Includes both future visits and pending ones (appt date passed, CRM not updated yet).
  Pending count shown separately in the insight bar for CRM cleanup tracking.

- **Pending** (subset of Upcoming) = `status = appointment` AND `cf_appointment_date < today`
  Visit date has passed but CRM hasn't been updated to sold/cancelled yet.

- **Showed Up** = leads where the visit already happened and they weren't cancelled-before.
  Formula: `(status = sold OR status = cancelled) + (status = appointment AND appt_date < today)`
  The last term captures pending records — appointment happened but CRM not yet updated.

**Show Rate** = showed_up ÷ total appointments (not just upcoming).
""")

        st.divider()

        # ── 8. PREDICTIONS ────────────────────────────────────────────────────────
        st.markdown("## 8. Sales Prediction from Upcoming")
        st.markdown("""
**Primary model: Per-appointment ML (Logistic Regression)**

Each upcoming appointment is scored individually using a trained logistic regression model. The sum of probabilities = predicted sales. This is more accurate than applying a flat rate because it accounts for the specific mix of upcoming appointments.

**Features used (trained on 12,311 closed appointments, Jan 2024–Mar 2026):**
- `province` — NB/Manitoba close at ~21%, Newfoundland at ~12%
- `city` — **top 22 cities with ≥100 closed appointments as one-hot features + OTHER_CITY bucket.** Cities within the same province close very differently: Calgary 13.9% vs Edmonton 17.6% (both AB), Moncton 24.7% vs Prince George 8.5%, Winnipeg 20.4% vs Vancouver 14.8%. Adding this feature lifted CV AUC from 0.575 → 0.596.
- `camp_type` — LG (lead gen forms) close at ~14.5%, CONV (conversion/CPC) at ~18.3%, DIRECT at ~23.8%, OTHER at ~15.8%
- `days_booked_to_appt` — 8–14 day window peaks at ~21.9%; 31+ days drops to ~12.7%
- `lead_month` (seasonality via sin/cos encoding)
- `days_lead_to_booked` — how quickly the lead was called and booked

**Campaign type logic:**
- **LG** = utm_campaign contains `-LG-` or `LEAD`, or utm_medium = `LG` → lead gen form campaigns
- **CONV** = utm_campaign contains `-CONV-` or `CONVER`, or utm_medium = `CPC` → conversion/click campaigns
- **DIRECT** = no utm_campaign and no utm_medium → organic / direct traffic
- **OTHER** = everything else

**Model performance (5-fold CV):** AUC 0.596, training AUC 0.601. Adding `city` gave the biggest single-feature lift since the initial model.

**Fallback: Seasonal rate model** — if the ML model is unavailable, uses average upcoming→sold rate per calendar month across all settled historical months. MAPE ~11.9%.

Seasonal rates (approximate):
- **Spring/Summer peak:** Apr ~15%, Feb/Dec ~14%, Mar/Jun/Jul/Sep ~13%
- **Fall/Winter dip:** Oct ~8%, Nov ~10%, Aug ~10%

**Historical Validation table** (in Overview → expand "Prediction Model Accuracy"):
- Shows each past month: Upcoming at end → Predicted → Actual Sold → Model Accuracy %

**Retraining:** Run `python utils/train_model.py` to retrain on new data. The model is saved to `utils/ml_model.json` and loaded at startup. Retrain every 6 months or when accuracy drifts beyond ±20%.

**Next ML improvement:** Add CRM response-time features (speed-to-call, number of call attempts before booking). Expected to push AUC above 0.65.
""")

        st.divider()

        # ── 9. SPEND & CPL/CPA/CPS ────────────────────────────────────────────────────
        st.markdown("## 9. Spend, CPL, CPA, CPA1 & CPS")
        st.markdown("""
**Two spend sources — depending on what is being calculated:**

**`meta_spend_cache.json` (no Windsor delay)** — used for daily totals and trend data:
- Daily spend trend charts (Trends tab)
- Period comparison (comp_spend)
- "Meta Direct (API)" metric on the Windsor reconciliation panel
- Total Meta Spend in the Creative section

The cache is updated automatically every day, plus a deep re-sync every Monday covering the last 30 days (to capture retroactive Windsor corrections). Data is aggregated across all 9 Canadian Meta ad accounts.

**BigQuery `raw.spend_geo_snap` (via Windsor AI, 1–2 day lag)** — used only for geographic breakdown:
- Spend distribution by province and city

Summary: **daily trends and total spend = cache (up to date), geo breakdown = BigQuery (with delay)**.

- Only **Meta and TikTok** spend is tracked. Affiliate spend is not available.
- **CPL** (Cost per Clean Lead) = Total Spend ÷ Clean Leads
- **CPA** (Cost per Appointment) = Total Spend ÷ Appointments
- **CPA1** (Cost per Happened Appointment) = Total Spend ÷ (Appts − Upcoming). Only counts appointments that have already taken place, excluding future ones.
- **CPS** (Cost per Sale) = Total Spend ÷ Sold
- Province spend is distributed to cities proportionally by clean lead share within each province.
""")

        st.divider()

        # ── 10. CITY MAPPING ──────────────────────────────────────────────────────
        st.markdown("## 10. City & Province Mapping")
        st.markdown("""
Every lead form submission includes a **postal code**. This is the key to geographic attribution.

**Mapping chain:**

1. Take the first 3 characters of the postal code → **FSA** (Forward Sortation Area, e.g. `T2P` = downtown Calgary).
2. Match FSA against `raw.city_map` in BigQuery → get city name.
3. Match first character of FSA against `raw.province_map` → get province.

**When a postal code can't be mapped:**

The lead is assigned to **"Unknown city"**. This happens when:
- The postal code field was left blank (null)
- The person typed a street address instead of a postal code (e.g. "152 Montfort Street")
- The code is invalid or non-Canadian (e.g. `F2K`)

In the week of Mar 23–29, **28 leads** landed in Unknown city — all with 0 appointments. No appointment data is lost from mapping failures.

**Active service cities (verified against BQ appointment data, Apr 2026):**

| Province | Active cities (≥1 appt in 90 days) |
|---|---|
| Alberta | Calgary, Edmonton, Red Deer, Lethbridge, Medicine Hat, Grande Prairie, Lloydminster |
| British Columbia | Vancouver, Victoria, Kelowna, Kamloops, Nanaimo, Prince George |
| Ontario | Ottawa, Kingston, Kenora |
| Manitoba | Winnipeg, Brandon |
| Saskatchewan | Saskatoon, Regina, Moose Jaw |
| New Brunswick | Moncton, Fredericton, Saint John |
| Nova Scotia | Halifax, Sydney |
| Newfoundland | St. John's |
| PEI | Charlottetown |

**"Bad geo" cities (leads come in, 0 appointments — kept for FB targeting drift monitoring):**
Toronto (465 leads), Thunder Bay (83), NU/NT (27), Yukon (22), Sudbury (12)

**Source classification from UTM:**

| utm_source value | Dashboard source |
|---|---|
| facebook, meta, fb | META |
| google, adwords | GOOGLE |
| empty / null | DIRECT |
| anything else | OTHER |

Affiliate leads are identified by utm_campaign content or by the Ecoline Affiliate Meta account.
""")

        st.divider()

        # ── 11. META LIVE ─────────────────────────────────────────────────────────
        st.markdown("## 11. Meta Live — Direct Meta API Integration")
        st.markdown("""
**Meta Live** is a separate analytics view pulling campaign data directly from the Meta API — no Windsor AI delay.

**Architecture:**

- Spend, impressions, CPM, CPC, and Meta-reported leads come **directly from Meta API** via Claude (MCP tools).
- Claude updates cache files (`meta_cache/campaigns_*.json`) on demand or on a schedule.
- Streamlit reads these JSON files — no direct API calls from the dashboard process.

**Two lead counts in Meta Live:**

| Metric | Source | Meaning |
|---|---|---|
| **Leads (Meta)** | Meta API | Raw form submission count. Includes spam, invalid contacts, no deduplication. |
| **Leads (BQ, clean)** | BigQuery | Deduplicated clean leads — identical logic to the Overview tab. |

**Why they differ** (example week Mar 23–29):
- Meta API: **1,344** (all form submissions)
- BQ all leads: **1,306** (passed SQL filter: valid phone / email / has appointment)
- BQ clean leads: **1,240** (after 45-day dedup window)

**CPL (raw)** = Spend ÷ Meta leads → understated true cost because denominator is inflated by spam.

**CPL (clean)** = Spend ÷ BQ clean leads → matches Overview CPL. This is your real cost per qualified lead.

**Province breakdown for national campaigns:**

For `ALL REGIONS` campaigns, the Meta API provides a real province-level breakdown (Alberta, BC, Ontario...). Within each province, city distribution is estimated from BQ data for the same period and campaign type (LG or CONV).

**Period alignment:**

Meta Live has its own period selector (Yesterday / Last 7 days / Custom range). This period is used for both the Meta API data and the BQ data filtering. The global sidebar date range does **not** affect Meta Live results.
""")

        st.divider()

        # ── 12. CREATIVE PERFORMANCE ──────────────────────────────────────────────
        st.markdown("## 12. Creative Performance — Ad Creative Analysis")
        st.markdown("""
The **🎨 Creative Performance** tab shows how each creative type and advertising hypothesis performs across the full funnel: lead → appointment → sale.

**Data source:**

All data comes from the same BQ tables and logic as the rest of the dashboard (`load_leads` → `apply_dedup` → `is_clean` filter). Creative type and hypothesis are parsed from `utm_content`; funnel type is parsed from `utm_term` (ad set name).

**Creative type classification:**

| utm_content starts with | Type |
|---|---|
| `IMAGE - Hyp ...` | IMAGE |
| `VIDEO - Hyp ...` | VIDEO |
| `DCO - IMAGE - Hyp ...` | DCO-IMAGE |
| `DCO - VIDEO - Hyp ...` | DCO-VIDEO |

**Hypothesis extraction:**

The number after `Hyp` is extracted from `utm_content` (e.g., `IMAGE - Hyp 111.1 - IT 3` → `Hyp 111.1`). The special case "0 Down" is matched by looking for `0 down` / `0down` in the string.

**Funnel type classification:**

Determined from `utm_term` (Meta ad set name):

| utm_term contains | Funnel Type | Destination |
|---|---|---|
| `cost cap` | Quiz (Cost Cap) | quiz.ecolinewindows.ca/* |
| `bid cap` | Quiz (Bid Cap) | quiz.ecolinewindows.ca/* |
| `hard form` | Hard Form | quiz.ecolinewindows.ca/* (different form) |
| `form m/i` | Lead Form | Native Meta lead gen form (in-app) |
| `aff` + `form`/`creo` | Affiliate | Partner forms |

**Metrics:**

| Metric | Formula |
|---|---|
| Dirty Rate (%) | (appointment + sold + cancelled + cancelled before appt) / leads × 100 |
| Clean Rate (%) | (sold + cancelled) / leads × 100 |
| Close Rate (%) | sold / leads × 100 |
| Rev/Lead ($) | revenue / leads |
| Avg Sale ($) | revenue / sold |

**Data quality flags:**

Each hypothesis is checked for anomalies:

- ⚠️ **Small sample** (<30 leads) — low confidence
- ⚠️ **Zero sales** — too early to judge
- 🔍 **Close rate 2.5x above average** with small sample — might be random
- 🔍 **Dirty rate >55%** — suspiciously high, possibly shared UTM naming with other campaigns
- 🔍 **Avg sale 2x above/below norm** — check for outlier deals

**Spend limitations (per hypothesis):**

Spend at the hypothesis / creative level in the core tabs (IMAGE vs VIDEO, By Hypothesis, By Funnel Type) is **not available**. Spend from Windsor is loaded aggregated by date + province, without ad name breakdown.

**New tabs (📍 By Placement, 📝 Ad Copy):**

These tabs use a **separate data cache from Meta API** (files `data/meta_placements.csv` and `data/meta_creatives.csv`) updated daily by the `meta-creative-sync` scheduled task at 7:00 AM.

**📍 By Placement** — where your ad budget goes across Meta placements:

| Placement | Description |
|---|---|
| Facebook Feed | Main FB feed |
| Instagram Feed | Main IG feed |
| Facebook Reels / IG Reels | Short-form video |
| IG Stories / FB Stories | Stories |
| FB Marketplace | Marketplace |
| Audience Network | Partner apps/sites |

Metrics: spend, impressions, clicks, link clicks, landing page views, CPM, CTR, CPC. Also shows spend breakdown by top hypotheses × placements.

**📝 Ad Copy** — analysis of ad creative text:

- **CTA Distribution** — which buttons (GET_QUOTE, LEARN_MORE, GET_OFFER) are used across creatives
- **Top Headlines** — most frequently used ad headlines
- **Top Opening Lines (Hooks)** — first lines of body text, grouped by frequency
- **Creative Copy ↔ Lead Performance** — matches creative_name from Meta API with utm_content from BQ to connect ad text with conversions
- **Full Creative Library** — searchable library of all creatives (1,400+ records)

**Data source for new tabs:**

Meta Ads API → `get_insights` (ad level, breakdowns: publisher_platform + platform_position) + `get_ad_creatives` → parsed → CSV. Covers 9 CAD accounts, data from January 2024 onward.
""")

        st.divider()

        # ── 13. DATA ASSISTANT ──────────────────────────────────────────────────
        st.markdown("## 13. Data Assistant — AI Chat")
        st.markdown("""
The **💬 Data Assistant** tab is an AI chat embedded directly in the dashboard. Team members can ask any data question in Russian or English and get an instant answer with numbers.

**What you can ask (examples):**

| Category | Example questions |
|---|---|
| General analytics | "Give me a summary for last month", "What's our CPL?", "How many sales?" |
| Hypotheses | "Top 5 hypotheses by close rate?", "Compare Hyp 111.1 vs Hyp 0 Down" |
| Cities / provinces | "Which cities convert best?", "Compare Calgary vs Edmonton", "Lowest CPL where?" |
| Funnels | "Quiz vs Lead Form — which is better?", "ROI by funnel type" |
| Placements | "Where do we spend most — FB Feed or IG Stories?", "Cheapest CPC placement?" |
| Creatives | "Most used headlines?", "Top CTA types", "What ad copy do we use?" |
| Trends | "How did close rate change over 3 months?", "Is CPL growing?" |
| SQL queries | "Write SQL for top-10 cities by revenue", "How many leads from utm_source=facebook?" |

**Quick-action buttons:**

4 buttons at the top of the chat for frequent requests:

| Button | What it does |
|---|---|
| 📊 Summary | Leads, sales, revenue, CPL, close rate for selected period |
| 🏆 Top hypotheses | Top-5 hypotheses by close rate (min 50 leads) |
| 📍 Best cities | Cities with best close rate (min 30 leads) |
| 💰 Funnel ROI | Compare Quiz Cost Cap, Bid Cap, Hard Form, Lead Form |

**Data access:**

| Source | Access | Description |
|---|---|---|
| BigQuery (BQ) | ✅ SELECT-only | raw.leads + raw.leads_status — leads, statuses, amounts, UTM, cities |
| Meta Ads (cache) | ✅ Read | Placements (spend/CPM/CTR), creatives (text/headlines/CTA) from CSV |
| Meta accounts | ✅ Reference | Knows all 11 accounts (ACC1-ACC8, Affiliate, USA1, USA2) |

**Restrictions (read-only):**

- ❌ Cannot modify dashboard code, files, or logic
- ❌ Cannot execute INSERT, UPDATE, DELETE, CREATE, DROP
- ❌ Cannot change settings or dashboard structure
- ❌ If asked to change anything — politely declines
- ✅ Can only read and analyze data

**AI Context:**

Each request automatically includes:
- Current dashboard numbers (leads, sales, revenue, spend for the sidebar-selected period)
- Full BQ table schema (raw.leads + raw.leads_status) with field descriptions
- Placement and creative data info (from daily Meta API cache)
- Rules: respond in user's language, be precise, specify period, don't guess

**Setup:**

Requires an Anthropic API key (Claude). Get it at [console.anthropic.com](https://console.anthropic.com) → Settings → API Keys. Add to `.streamlit/secrets.toml`:
```
ANTHROPIC_API_KEY = "sk-ant-api03-..."
```
This is **separate** from a claude.ai subscription — you need an API key from console.anthropic.com.

**Model:** Claude Sonnet 4 (`claude-sonnet-4-20250514`)

**Future extensions:**

| Skill | Description |
|---|---|
| Media Buyer | Campaign optimization advice, budget, bidding strategy |
| Creative Strategist | Creative analysis, copy and visual recommendations |
| Data Analyst | Deep data analysis, cohort analysis, attribution |
| CRO Specialist | Conversion optimization, A/B tests, funnel analysis |
| MCP Ads Library | Direct access to ad creative library (R&D) |
""")

        st.divider()

        # ── 14. CHANGELOG ─────────────────────────────────────────────────────────
        st.markdown("## 14. Changelog — Logic Updates")
        st.markdown("""
| Date | Change |
|---|---|
| Apr 2026 | **💬 Data Assistant** — AI chat tab powered by Claude Sonnet 4. Team members can ask data questions and get instant answers. Read-only: cannot modify code or data. Includes quick-action buttons and full BQ schema context. |
| Apr 2026 | **📍 By Placement + 📝 Ad Copy tabs** — two new sub-tabs in Creative Performance. Placement shows spend distribution across FB Feed / IG Stories / Reels etc. Ad Copy analyzes ad text: headlines, hooks, CTA types, and links them to conversions via utm_content. Data from Meta API (9 accounts, Jan 2024+). |
| Apr 2026 | **Scheduled task `meta-creative-sync`** — daily refresh of placement and creative data from Meta API at 7:00 AM. |
| Apr 2026 | **Creative Performance tab** — new tab analyzing ad creatives by type (IMAGE/VIDEO/DCO), hypothesis, and funnel type. Includes data quality flags for anomalies. |
| Apr 2026 | **Parser conversion window expanded** from 20 to 100 days. Previously ~8% of appointments and ~10% of sales booked more than 20 days after the lead were lost from BQ data. |
| Apr 2026 | **4-Week Appointment Calendar** in Trends — daily booked appointments by segment (Meta·LG / Meta·CONV / Calls / Affiliate) with YoY delta (−52 weeks). Fixed 28-day window, independent of sidebar date range. |
| Apr 2026 | **City/province verification**: active city list cross-checked against 90-day BQ appointment data. Removed phantom cities (Hamilton, London, Brampton, Abbotsford, etc.). Added real active cities: Lloydminster AB, Prince George BC, Moose Jaw SK, Sydney NS. Fixed Nova Scotia mapping (Cape Breton Island → Sydney). |
| Apr 2026 | **Meta Live tab**: direct Meta API integration via Claude MCP. Real-time data, no Windsor AI delay. |
| Apr 2026 | **CPL (clean) in Meta Live**: added correct CPL calculated from BQ clean leads — matches Overview CPL. |
| Apr 2026 | **Meta Live period fix**: BQ data in Meta Live now filters to the Meta Live period selector, not the global sidebar date range. |
| Apr 2026 | **Province breakdown** for national campaigns in Meta Live — real province-level splits from Meta API + city distribution from BQ. |
| Apr 2026 | **ML model v3**: added `city` as one-hot feature (top 22 cities + OTHER_CITY bucket). Calgary 13.9% vs Edmonton 17.6%. CV AUC improved 0.575 → 0.596. |
| Apr 2026 | **ML model v2**: switched from `utm_medium` to `camp_type` (LG/CONV/DIRECT/OTHER). LG 14.5% close rate, CONV 18.3%. MAE improved 4.6 → 4.2 sales. |
| Apr 2026 | **ML model v1**: per-appointment logistic regression (pure numpy). 11,927 appointments Jan 2024–Mar 2026. AUC 0.587, MAE 4.6 sales. |
| Apr 2026 | **Seasonal prediction model**: calendar-month average rate instead of flat 11%. MAPE 11.9% vs 16.5%. Apr ~15%, Oct ~8%. |
| Apr 2026 | **Appointment detection switched to `cf_booked_date`**. Booked date = actual conversion moment. |
| Apr 2026 | **Upcoming fix**: `>=` so today's appointments are upcoming (not pending). |
| Apr 2026 | **Pending metric**: appointments whose visit date passed but CRM not yet updated. |
| Apr 2026 | **Calls attributed to parent source** (META, Affiliate). Calls breakout still in Source Comparison. |
| Apr 2026 | **Clean leads fix**: email-only leads with no CRM activity marked NOT clean. |
| Apr 2026 | **Lead-date methodology**: all metrics keyed off lead submission date, not event date. |
| Apr 2026 | **Show Rate fix**: `showed_up / appts` (was `(appts − canc_before) / appts` which included upcoming). |
| Apr 2026 | **Geography fix**: removed `is_clean` pre-filter so all_leads ≠ clean_leads again. |
| Apr 2026 | **Prediction model calibrated**: `upcoming × 11% historical` (was `upcoming × showed→sold rate`, overstated 3×). |
""")
