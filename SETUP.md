# Ecoline Dashboard — Setup Guide

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

## 2. BigQuery authentication

**Option A — Google Cloud CLI (easiest)**
```bash
gcloud auth application-default login
```
Then run the dashboard. No extra config needed.

**Option B — Service account key file**
```bash
export BQ_KEY_PATH="/path/to/your/service-account-key.json"
```
Or on Windows:
```cmd
set BQ_KEY_PATH=C:\path\to\your\service-account-key.json
```

## 3. Run the dashboard

```bash
streamlit run app.py
```

Opens at: **http://localhost:8501**

---

## What each page does

| Page | Description |
|------|-------------|
| 📊 Overview | Daily KPIs, source cards, top cities, daily trend chart |
| 📈 Trends | Weekly/Monthly funnel table + 4 trend charts with rolling average |
| 🗺️ Geography | Province & city breakdown with estimated spend attribution |
| 📋 Lead Detail | Filterable individual lead + call records, CSV export |
| 🔄 Funnel Analysis | **The two sliders** — dedup window + appointment window, funnel chart, timing histogram |
| 📱 Campaign Intelligence | Campaign → performance table, sortable by any metric |
| ⚖️ Source Comparison | META vs Calls vs Affiliate vs Other side by side |

---

## Global sidebar controls

- **Date range** — applies to all pages
- **Source filter** — META, TikTok, Calls, Affiliate, Other
- **Global defaults** — dedup window (default 45d) and appt window (default 45d) used on all pages except Funnel Analysis (which has its own sliders)

---

## The two sliders (Funnel Analysis page only)

**Slider 1 — Deduplication Window (1–90 days)**
- Moves the dedup threshold. At 10d = strict short-window, fewer leads filtered.
- At 60d = aggressive, more leads filtered.
- Session-only — doesn't change data on other pages.

**Slider 2 — Appointment Window (1–120 days)**
- Only appointments within this many days of the lead are counted.
- Your Looker default was 20 days → captures only ~55% of real appointments.
- Recommended default: 45 days → captures ~89%.
- Histogram shows exactly where appointments fall with a live marker.

---

## Deploying online (after local validation)

```bash
pip install streamlit
# Push to GitHub, then:
# 1. Go to share.streamlit.io
# 2. Connect your repo
# 3. Add BQ_KEY_PATH as a secret in the Streamlit Cloud settings
```
