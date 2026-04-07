import streamlit as st
from google.cloud import bigquery
import os

PROJECT_ID = "ecolinew"

@st.cache_resource
def get_client():
    """
    Returns a BigQuery client.
    Uses Application Default Credentials (gcloud auth application-default login)
    or a service account key file if BQ_KEY_PATH env var is set.
    """
    key_path = os.environ.get("BQ_KEY_PATH")
    if key_path:
        return bigquery.Client.from_service_account_json(key_path, project=PROJECT_ID)
    return bigquery.Client(project=PROJECT_ID)


def run_query(sql: str) -> "pd.DataFrame":
    client = get_client()
    return client.query(sql).to_dataframe()
