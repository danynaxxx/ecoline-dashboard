import os
from google.cloud import bigquery
from google.oauth2 import service_account

KEY_PATH = os.path.expanduser("~/.credentials/eco-affiliate.json")

creds = service_account.Credentials.from_service_account_file(KEY_PATH)
client = bigquery.Client(project="eco-affiliate", credentials=creds)

sql = """
SELECT
    DATE(lws.dt)               AS lead_date,
    lws.name,
    lws.phone,
    lws.email,
    COALESCE(lws.province, 'Unknown') AS province,
    COALESCE(lws.city, 'Unknown')     AS city,
    lws.status_with_cancelled          AS status,
    DATE(lws.cf_appointment_date)      AS appt_date,
    DATE(lws.cf_sold_date)             AS sold_date,
    lws.cf_amount                      AS amount
FROM `eco-affiliate.raw.leads_with_status` lws
WHERE lws.status_with_cancelled = 'sold'
  AND DATE(lws.dt) BETWEEN '2026-02-23' AND '2026-03-01'
ORDER BY lws.dt
"""

rows = client.query(sql).to_dataframe()

print(f"\nSold leads (23 Feb – 1 Mar 2026): {len(rows)} total\n")
print(rows.to_string(index=False))
