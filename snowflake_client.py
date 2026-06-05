"""
snowflake_client.py
Snowflake connection + query execution for the NM Data Officer Dashboard.

Connection pattern matches NM Portfolio Intelligence:
- Credentials come from st.secrets["snowflake"]
- client_session_keep_alive = True, login_timeout = 60
- NO @st.cache_resource on the connection — create a fresh one each time
- run_query() converts Decimal -> float and lowercases all column names
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd
import streamlit as st
import snowflake.connector

DATABASE = "NM_ANALYTICS"
SCHEMA = "RAW_MARTS"


def get_connection():
    """
    Open a fresh Snowflake connection from st.secrets["snowflake"].

    No @st.cache_resource — a new connection is created on each call so a
    dropped/expired session never leaves a stale cached handle behind.
    """
    cfg = st.secrets["snowflake"]
    return snowflake.connector.connect(
        account=cfg["account"],
        user=cfg["user"],
        password=cfg["password"],
        warehouse=cfg["warehouse"],
        database=cfg.get("database", DATABASE),
        schema=cfg.get("schema", SCHEMA),
        role=cfg.get("role", "SYSADMIN"),
        client_session_keep_alive=True,
        login_timeout=60,
    )


def _coerce(value):
    """Convert Snowflake Decimals to float; leave everything else untouched."""
    if isinstance(value, Decimal):
        return float(value)
    return value


def run_query(sql: str) -> pd.DataFrame:
    """
    Execute SQL and return a DataFrame.

    - All Decimal values are converted to float.
    - All column names are lowercased.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute(sql)
            columns = [c[0].lower() for c in cur.description]
            rows = cur.fetchall()
        finally:
            cur.close()
    finally:
        conn.close()

    data = [[_coerce(v) for v in row] for row in rows]
    return pd.DataFrame(data, columns=columns)


@st.cache_data(ttl=300, show_spinner=False)
def cached_query(sql: str) -> pd.DataFrame:
    """run_query() wrapped in a 5-minute data cache to avoid re-hitting Snowflake."""
    return run_query(sql)


def get_all_filing_dates() -> list[str]:
    """Sorted list of distinct filing dates (as ISO strings)."""
    df = cached_query(
        f"SELECT DISTINCT filing_date "
        f"FROM {DATABASE}.{SCHEMA}.MART_PORTFOLIO_SUMMARY "
        f"ORDER BY filing_date"
    )
    return [str(d) for d in df["filing_date"].tolist()]


def get_latest_filing_date() -> str:
    """MAX(filing_date) as an ISO string."""
    df = cached_query(
        f"SELECT MAX(filing_date) AS latest "
        f"FROM {DATABASE}.{SCHEMA}.MART_PORTFOLIO_SUMMARY"
    )
    return str(df["latest"].iloc[0])
