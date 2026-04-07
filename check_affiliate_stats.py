"""
Quick script to pull last 3 months affiliate cancellation stats from BigQuery.
Run with: python3 check_affiliate_stats.py
"""
from google.cloud import bigquery
from google.oauth2 import service_account
import os

KEY_PATH = os.path.expanduser("~/.credentials/eco-affiliate.json")

creds = service_account.Credentials.from_service_account_file(
    KEY_PATH,
    scopes=["https://www.googleapis.com/auth/bigquery"],
)
client = bigquery.Client(project="eco-affiliate", credentials=creds)

sql = """
SELECT
  FORMAT_DATE('%Y-%m', DATE(lws.dt))  AS month,
  COUNT(*)                             AS total_clean_leads,
  COUNTIF(lws.cf_appointment_date IS NOT NULL)                       AS total_appts,
  COUNTIF(lws.status_with_cancelled = 'cancelled before appt')       AS cancelled_before,
  COUNTIF(lws.status_with_cancelled = 'cancelled')                   AS cancelled_after,
  COUNTIF(lws.status_with_cancelled = 'sold')                        AS sold,
  ROUND(
    COUNTIF(lws.status_with_cancelled = 'cancelled before appt') /
    NULLIF(COUNTIF(lws.cf_appointment_date IS NOT NULL), 0) * 100, 1
  ) AS cancel_before_pct
FROM `eco-affiliate.raw.leads_with_status` lws
WHERE DATE(lws.dt) BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH) AND CURRENT_DATE()
  AND (
    REGEXP_CONTAINS(REGEXP_REPLACE(COALESCE(lws.phone,''), r'[^0-9]',''), r'^[2-9][0-9]{9}$')
    OR (lws.email IS NOT NULL AND lws.email LIKE '%@%.%')
    OR lws.cf_appointment_date IS NOT NULL
    OR lws.cf_cancelled_date   IS NOT NULL
  )
GROUP BY 1
ORDER BY 1
"""

print("\n📊 Eco Affiliate — Last 3 Months Stats\n")
print(f"{'Month':<12} {'Leads':>8} {'Appts':>7} {'CancelBefore':>14} {'CancelAfter':>13} {'Sold':>6} {'CancelBefore%':>14}")
print("-" * 80)

df = client.query(sql).to_dataframe()
for _, row in df.iterrows():
    print(f"{row['month']:<12} {row['total_clean_leads']:>8} {row['total_appts']:>7} "
          f"{row['cancelled_before']:>14} {row['cancelled_after']:>13} "
          f"{row['sold']:>6} {row['cancel_before_pct']:>13.1f}%")

if not df.empty:
    avg = df['cancel_before_pct'].mean()
    total_cb = df['cancelled_before'].sum()
    total_appts = df['total_appts'].sum()
    overall = round(total_cb / total_appts * 100, 1) if total_appts > 0 else 0
    print("-" * 80)
    print(f"\n✅ Overall cancel-before rate (3 months): {overall}%")
    print(f"   Total cancelled before appt: {total_cb} / {total_appts} total appts\n")
