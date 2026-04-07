import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import os

PROJECT_ID = "ecolinew"

@st.cache_resource
def get_client():
    """
    Returns a BigQuery client.
    Priority:
    1. Streamlit Cloud secrets (gcp_service_account section)
    2. BQ_KEY_PATH env var (local service account key file)
    3. Application Default Credentials (gcloud auth)
    """
    # 1. Streamlit Cloud secrets
    try:
        sa_info = st.secrets.get("gcp_service_account")
        if sa_info:
            creds = service_account.Credentials.from_service_account_info(
                dict(sa_info),
                scopes=["https://www.googleapis.com/auth/bigquery"],
            )
            return bigquery.Client(project=PROJECT_ID, credentials=creds)
    except Exception:
        pass

    # 2. Service account key file
    key_path = os.environ.get("BQ_KEY_PATH")
    if key_path:
        return bigquery.Client.from_service_account_json(key_path, project=PROJECT_ID)

    # 3. Application Default Credentials (local dev)
    return bigquery.Client(project=PROJECT_ID)


def run_query(sql: str) -> "pd.DataFrame":
    client = get_client()
    return client.query(sql).to_dataframe()
