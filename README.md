# NM Data Officer Dashboard

Investment Data Health Dashboard for the Investment Data Office at Northwestern
Mutual. A **data governance and health dashboard** (not an analytics app) showing
data freshness, quality, portfolio coverage, lineage, and a Claude-powered
portfolio assistant across 6 NPORT-P filing periods (Feb 2025 – May 2026).

**Stack:** Streamlit · Snowflake (`NM_ANALYTICS.RAW_MARTS`) · Claude · NM theme

## Tabs

1. **Data Freshness** — latest filing, holdings-per-filing timeline, raw dataset & mart status
2. **Data Quality** — dbt test results (10 models, 46 tests), holdings trend, live null-rate check
3. **Portfolio Coverage** — portfolio-count trend, per-portfolio coverage matrix, sector-gap insight
4. **Data Lineage** — source → staging → intermediate → mart pipeline, source cards, lineage table
5. **Portfolio Assistant** — Claude text-to-SQL over the marts (`claude-sonnet-4-6`)

## Setup

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then fill in real values
streamlit run app.py
```

## Notes

- All "current/latest" queries use `MAX(filing_date)` — no dates are hardcoded.
- The Snowflake connection is created fresh per query (no `@st.cache_resource`);
  query results are cached for 5 minutes via `@st.cache_data`.
- If Snowflake is unreachable, data tabs fall back to the known filing calendar
  and show a non-fatal banner so the static tabs still render.
- dbt test counts (46/46) are hardcoded for the demo, per the PRD (out of scope: live dbt results).
- The PRD named `claude-sonnet-4-20250514`; that model is deprecated, so this
  app uses the current Sonnet, `claude-sonnet-4-6`.
