import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import os

# Default project
DEFAULT_PROJECT = "ecolinew"

PROJECTS = {
    "🏠 Ecoline Windows (Main)": "ecolinew",
    "🤝 Eco Affiliate": "eco-affiliate",
}

@st.cache_resource
def get_client(project_id: str = DEFAULT_PROJECT):
    """
    Returns a BigQuery client for the given project.
    Priority:
    1. Streamlit Cloud secrets (gcp_service_account / gcp_service_account_affiliate)
    2. BQ_KEY_PATH env var (local service account key file)
    3. Application Default Credentials (gcloud auth)
    """
    # 1. Streamlit Cloud secrets
    try:
        # Pick the right secret section based on project
        if project_id == "eco-affiliate":
            sa_info = st.secrets.get("gcp_service_account_affiliate")
        else:
            sa_info = st.secrets.get("gcp_service_account")

        if sa_info:
            creds = service_account.Credentials.from_service_account_info(
                dict(sa_info),
                scopes=["https://www.googleapis.com/auth/bigquery"],
            )
            return bigquery.Client(project=project_id, credentials=creds)
    except Exception:
        pass

    # 2. Local service account key file
    if project_id == "eco-affiliate":
        key_path = os.environ.get("BQ_AFFILIATE_KEY_PATH",
                                  os.path.expanduser("~/.credentials/eco-affiliate.json"))
    else:
        key_path = os.environ.get("BQ_KEY_PATH", "")

    if key_path and os.path.exists(key_path):
        return bigquery.Client.from_service_account_json(key_path, project=project_id)

    # 3. Application Default Credentials (local dev — works for main project only)
    return bigquery.Client(project=project_id)


def run_query(sql: str, project_id: str = DEFAULT_PROJECT) -> "pd.DataFrame":
    import pandas as pd
    from google.api_core.exceptions import NotFound, Forbidden
    client = get_client(project_id)
    try:
        return client.query(sql).to_dataframe()
    except NotFound as e:
        st.warning(f"⚠️ Table not found in **{project_id}**: {e.message.split(';')[0]}")
        return pd.DataFrame()
    except Forbidden as e:
        st.warning(f"⚠️ Access denied in **{project_id}**: check service account permissions.")
        return pd.DataFrame()
    except Exception as e:
        raise
