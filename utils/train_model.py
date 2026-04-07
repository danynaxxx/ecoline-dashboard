"""
Retrain the upcoming-appointment close-probability model.

Run from the project root:
    python utils/train_model.py

Pulls closed appointments from BigQuery, trains logistic regression,
saves weights to utils/ml_model.json.  Run every 6 months or when
prediction accuracy drifts.
"""

import json
import os
import sys
from datetime import date

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.bq_client import run_query


# ── 1. Pull training data ─────────────────────────────────────────────────────
print("Fetching training data from BigQuery…")

SQL = """
SELECT
  CASE WHEN ls.status_with_cancelled = 'sold' THEN 1 ELSE 0 END AS sold,
  COALESCE(p.province, 'Unknown') AS province,
  COALESCE(c.city, 'Unknown city') AS city,
  CASE
    WHEN UPPER(COALESCE(l.utm_campaign,'')) LIKE '%-LG-%'
      OR UPPER(COALESCE(l.utm_campaign,'')) LIKE '%LEAD%'
      OR UPPER(COALESCE(l.utm_medium,'')) = 'LG'  THEN 'LG'
    WHEN UPPER(COALESCE(l.utm_campaign,'')) LIKE '%-CONV-%'
      OR UPPER(COALESCE(l.utm_campaign,'')) LIKE '%CONVER%'
      OR UPPER(COALESCE(l.utm_medium,'')) = 'CPC' THEN 'CONV'
    WHEN l.utm_campaign IS NULL AND l.utm_medium IS NULL THEN 'DIRECT'
    ELSE 'OTHER'
  END AS camp_type,
  EXTRACT(MONTH FROM DATE(l.dt)) AS lead_month,
  LEAST(DATE_DIFF(ls.cf_booked_date, DATE(l.dt), DAY), 30) AS days_lead_to_booked,
  LEAST(DATE_DIFF(ls.cf_appointment_date, ls.cf_booked_date, DAY), 60) AS days_booked_to_appt
FROM `ecolinew.raw.leads` l
LEFT JOIN `ecolinew.raw.leads_status` ls ON l.row_num = ls.row_num
LEFT JOIN `ecolinew.raw.city_map` c
    ON UPPER(SUBSTR(REGEXP_REPLACE(l.postal_code, r'\\s', ''), 1, 3)) = c.fsa_postal_code
LEFT JOIN `ecolinew.raw.province_map` p
    ON UPPER(SUBSTR(REGEXP_REPLACE(l.postal_code, r'\\s', ''), 1, 1)) = p.postal_district
WHERE
  ls.status_with_cancelled IN ('sold', 'cancelled')
  AND ls.cf_booked_date IS NOT NULL
  AND ls.cf_appointment_date IS NOT NULL
  AND ls.cf_appointment_date < CURRENT_DATE()
  AND DATE(l.dt) >= '2024-01-01'
  AND DATE_DIFF(ls.cf_booked_date, DATE(l.dt), DAY) >= 0
  AND DATE_DIFF(ls.cf_appointment_date, ls.cf_booked_date, DAY) >= 0
"""

df = run_query(SQL)
print(f"  {len(df):,} rows loaded  |  close rate: {df['sold'].mean():.1%}")


# ── 2. Encode features ────────────────────────────────────────────────────────
provinces  = sorted(df["province"].unique().tolist())
camp_types = sorted(df["camp_type"].unique().tolist())

# Keep cities with >= 100 training rows as explicit features; rest → OTHER_CITY
city_counts = df["city"].value_counts()
top_cities  = city_counts[city_counts >= 100].index.tolist()
cities      = sorted(top_cities) + ["OTHER_CITY"]

prov_idx = {v: i for i, v in enumerate(provinces)}
camp_idx = {v: i for i, v in enumerate(camp_types)}
city_idx = {v: i for i, v in enumerate(cities)}


def bucket_days(d):
    if d <= 7:  return [1, 0, 0, 0, 0]
    if d <= 14: return [0, 1, 0, 0, 0]
    if d <= 21: return [0, 0, 1, 0, 0]
    if d <= 30: return [0, 0, 0, 1, 0]
    return             [0, 0, 0, 0, 1]


def encode_row(row):
    prov_oh = [0] * len(provinces)
    if row["province"] in prov_idx:
        prov_oh[prov_idx[row["province"]]] = 1

    camp_oh = [0] * len(camp_types)
    if row["camp_type"] in camp_idx:
        camp_oh[camp_idx[row["camp_type"]]] = 1

    city_key = row["city"] if row["city"] in city_idx else "OTHER_CITY"
    city_oh  = [0] * len(cities)
    city_oh[city_idx[city_key]] = 1

    d_lead = min(int(row["days_lead_to_booked"]), 30) / 30

    return (prov_oh + camp_oh + city_oh
            + bucket_days(int(row["days_booked_to_appt"]))
            + [
                np.sin(2 * np.pi * row["lead_month"] / 12),
                np.cos(2 * np.pi * row["lead_month"] / 12),
                d_lead,
            ])


X = np.array([encode_row(r) for _, r in df.iterrows()])
y = df["sold"].values.astype(float)
print(f"  Feature matrix: {X.shape}")


# ── 3. Train logistic regression ──────────────────────────────────────────────
def sigmoid(z):
    return 1 / (1 + np.exp(-np.clip(z, -500, 500)))


def train_lr(X, y, lr=0.1, epochs=400, l2=0.005):
    w = np.zeros(X.shape[1])
    b = 0.0
    for i in range(epochs):
        p = sigmoid(X @ w + b)
        e = p - y
        w -= lr * (X.T @ e / len(y) + l2 * w)
        b -= lr * e.mean()
        if (i + 1) % 100 == 0:
            loss = -(y * np.log(p + 1e-9) + (1 - y) * np.log(1 - p + 1e-9)).mean()
            print(f"  epoch {i+1:>4}  loss={loss:.4f}")
    return w, b


print("Training…")
w, b = train_lr(X, y)


# ── 4. Quick AUC on full data (training AUC — for sanity check only) ──────────
probs = sigmoid(X @ w + b)
order = np.argsort(-probs)
ys    = y[order]
n_pos = ys.sum(); n_neg = len(ys) - n_pos
tp = fp = auc_sum = 0
for v in ys:
    if v: tp += 1
    else: fp += 1; auc_sum += tp
train_auc = auc_sum / (n_pos * n_neg)
print(f"Training AUC: {train_auc:.3f}  (CV AUC expected ~0.587)")


# ── 5. Save model ─────────────────────────────────────────────────────────────
model = {
    "provinces":    provinces,
    "camp_types":   camp_types,
    "cities":       cities,
    "weights":      w.tolist(),
    "bias":         float(b),
    "train_rows":   int(len(df)),
    "train_auc":    round(float(train_auc), 3),
    "version":      str(date.today())[:7],  # YYYY-MM
    "description":  (
        "Logistic regression trained on closed appointments. "
        "Features: province, camp_type (LG/CONV/DIRECT/OTHER), "
        "city (top N with >=100 rows + OTHER_CITY), "
        "days_booked_to_appt (bucketed), lead_month (sin/cos), days_lead_to_booked."
    ),
}

out_path = os.path.join(os.path.dirname(__file__), "ml_model.json")
with open(out_path, "w") as f:
    json.dump(model, f, indent=2)

print(f"\nModel saved → {out_path}")
print(f"  Rows: {model['train_rows']:,}  |  AUC: {model['train_auc']}  |  Version: {model['version']}")
print(f"  Provinces: {len(provinces)}  |  Camp types: {len(camp_types)}  |  Cities: {len(cities)}  |  Features: {len(w)}")
