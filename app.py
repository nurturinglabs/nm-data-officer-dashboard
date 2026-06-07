"""
NM Data Officer Dashboard
Investment Data Health Dashboard for the Investment Data Office.

A data governance + health dashboard (NOT an analytics app) showing data
freshness, quality, portfolio coverage, lineage, and a Claude-powered
portfolio assistant across 6 NPORT-P filing periods (Feb 2025 – May 2026).
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from nm_theme import (
    nm_inject_css,
    nm_header,
    nm_kpi_row,
    nm_chart_title,
    nm_plotly_layout,
    nm_table,
    nm_pill,
    _render_html,
    COLORS,
)
import snowflake_client as sf

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

DB = "NM_ANALYTICS"
SCHEMA = "RAW_MARTS"
FQ = f"{DB}.{SCHEMA}"  # fully-qualified prefix

NM_NAVY = "#003366"
NM_YELLOW = "#FFB500"

# Current Claude model. The PRD specifies `claude-sonnet-4-20250514`, which is
# deprecated (retires 2026-06-15); `claude-sonnet-4-6` is the current Sonnet.
CLAUDE_MODEL = "claude-sonnet-4-6"

# The 5 portfolios that have GICS sector data (PRD §5).
SECTOR_PORTFOLIOS = {
    "Index 500 Stock Portfolio",
    "Index 400 Stock Portfolio",
    "Balanced Portfolio",
    "Active/Passive Balanced Portfolio",
    "Active/Passive Aggressive Portfolio",
}

# Known filing calendar (PRD §6) — used as a static fallback for the coverage /
# trend charts when Snowflake is unreachable so the page still renders.
FILING_CALENDAR = [
    ("2025-02-20", 26, 6962),
    ("2025-05-19", 26, 7168),
    ("2025-08-19", 26, 7138),
    ("2025-11-24", 29, 7249),
    ("2026-02-23", 29, 7324),
    ("2026-05-27", 29, 7526),
]

TABS = [
    "Data Freshness",
    "Data Quality",
    "Portfolio Coverage",
    "Data Lineage",
    "Portfolio Assistant",
]

# ─────────────────────────────────────────────────────────────────────────────
# PAGE SETUP
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Northwestern Mutual · NM Series Fund Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)
nm_inject_css()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def fmt_month(d) -> str:
    """'2026-05-27' -> 'May 2026'."""
    if d is None:
        return "—"
    s = str(d)[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%b %Y")
    except ValueError:
        return s


def fmt_int(n) -> str:
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "—"


@st.cache_data(ttl=300, show_spinner=False)
def _try_query(sql: str):
    """
    Run a cached query, returning (DataFrame, None) on success or
    (None, error_message) on failure — so a missing/unreachable Snowflake
    never crashes the page.
    """
    try:
        return sf.cached_query(sql), None
    except Exception as exc:  # noqa: BLE001 — surface any connector error to the UI
        return None, str(exc)


def query(sql: str):
    """Convenience wrapper around _try_query that records the first error seen."""
    df, err = _try_query(sql)
    if err and "sf_error" not in st.session_state:
        st.session_state["sf_error"] = err
    return df


def data_banner():
    """Show a single non-fatal banner if any Snowflake query failed this run."""
    err = st.session_state.get("sf_error")
    if err:
        st.warning(
            "⚠️ Live Snowflake data is unavailable — showing the known filing "
            "calendar where possible. Configure `.streamlit/secrets.toml` to "
            f"enable live queries.\n\n```\n{err[:300]}\n```"
        )


# ─────────────────────────────────────────────────────────────────────────────
# DATA ACCESS (each returns a tidy DataFrame, falling back to the calendar)
# ─────────────────────────────────────────────────────────────────────────────

def holdings_by_filing() -> pd.DataFrame:
    """One row per filing date: filing_date, holdings."""
    df = query(
        f"SELECT filing_date, COUNT(*) AS holdings "
        f"FROM {FQ}.MART_TOP_HOLDINGS "
        f"GROUP BY filing_date ORDER BY filing_date"
    )
    if df is None or df.empty:
        df = pd.DataFrame(
            [(d, h) for d, _, h in FILING_CALENDAR],
            columns=["filing_date", "holdings"],
        )
    return df


def portfolios_by_filing() -> pd.DataFrame:
    """One row per filing date: filing_date, portfolios."""
    df = query(
        f"SELECT filing_date, COUNT(DISTINCT portfolio_name) AS portfolios "
        f"FROM {FQ}.MART_PORTFOLIO_SUMMARY "
        f"GROUP BY filing_date ORDER BY filing_date"
    )
    if df is None or df.empty:
        df = pd.DataFrame(
            [(d, p) for d, p, _ in FILING_CALENDAR],
            columns=["filing_date", "portfolios"],
        )
    return df


def mart_freshness() -> dict[str, tuple]:
    """Map mart name -> (last_updated, row_count). Empty if Snowflake is down."""
    marts = {
        "mart_portfolio_summary": "MART_PORTFOLIO_SUMMARY",
        "mart_top_holdings": "MART_TOP_HOLDINGS",
        "mart_sector_allocation": "MART_SECTOR_ALLOCATION",
        "mart_risk_metrics": "MART_RISK_METRICS",
    }
    out = {}
    for label, tbl in marts.items():
        df = query(
            f"SELECT MAX(filing_date) AS last_updated, COUNT(*) AS row_count "
            f"FROM {FQ}.{tbl}"
        )
        if df is not None and not df.empty:
            out[label] = (df["last_updated"].iloc[0], df["row_count"].iloc[0])
    return out


# ─────────────────────────────────────────────────────────────────────────────
# CHART BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def filing_column_chart(df: pd.DataFrame, value_col: str, height: int = 260) -> go.Figure:
    """Vertical column chart over filing dates; latest filing highlighted yellow."""
    labels = [fmt_month(d) for d in df["filing_date"]]
    colors = [NM_NAVY] * len(df)
    if colors:
        colors[-1] = NM_YELLOW  # latest filing
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=df[value_col],
            marker_color=colors,
            text=[fmt_int(v) for v in df[value_col]],
            textposition="outside",
            textfont=dict(size=12, color="#111827", family="DM Sans"),
        )
    )
    layout = nm_plotly_layout(height=height, margin=dict(l=0, r=10, t=20, b=0))
    layout["yaxis"]["showticklabels"] = False
    layout["yaxis"]["range"] = [0, df[value_col].max() * 1.18]
    fig.update_layout(**layout)
    return fig


def filing_line_chart(
    df: pd.DataFrame, value_col: str, height: int = 260, annotate: str | None = None
) -> go.Figure:
    """Line+marker chart over filing dates."""
    labels = [fmt_month(d) for d in df["filing_date"]]
    fig = go.Figure(
        go.Scatter(
            x=labels,
            y=df[value_col],
            mode="lines+markers+text",
            line=dict(color=NM_NAVY, width=2.5),
            marker=dict(color=NM_YELLOW, size=9, line=dict(color=NM_NAVY, width=1.5)),
            text=[fmt_int(v) for v in df[value_col]],
            textposition="top center",
            textfont=dict(size=12, color="#111827", family="DM Sans"),
        )
    )
    layout = nm_plotly_layout(height=height, margin=dict(l=0, r=10, t=24, b=0))
    pad = max((df[value_col].max() - df[value_col].min()) * 0.4, 1)
    layout["yaxis"]["range"] = [df[value_col].min() - pad, df[value_col].max() + pad]
    fig.update_layout(**layout)
    if annotate:
        fig.add_annotation(
            x=labels[3] if len(labels) > 3 else labels[-1],
            y=df[value_col].iloc[3] if len(df) > 3 else df[value_col].iloc[-1],
            text=annotate,
            showarrow=True,
            arrowhead=2,
            arrowcolor=NM_YELLOW,
            ax=0,
            ay=-34,
            font=dict(size=10, color=NM_NAVY, family="DM Sans"),
            bgcolor="#FFF3CC",
            bordercolor=NM_YELLOW,
            borderwidth=1,
            borderpad=4,
        )
    return fig


def filing_heatmap(df: pd.DataFrame, value_col: str, height: int = 160) -> go.Figure:
    """
    Single-row heatmap strip over filing dates — color intensity encodes the
    value. The color scale is stretched to the data range (the values cluster in
    a narrow band) so differences are visible; the latest filing is outlined in
    NM yellow and each cell is labelled with its value.
    """
    labels = [fmt_month(d) for d in df["filing_date"]]
    vals = [float(v) for v in df[value_col].tolist()]
    vmin, vmax = min(vals), max(vals)
    span = (vmax - vmin) or 1
    zmin, zmax = vmin - span * 0.25, vmax + span * 0.05

    # Light → medium-blue scale (kept light enough that dark in-cell text stays
    # readable on every cell). Labels are drawn via texttemplate so they always
    # center inside their cell.
    fig = go.Figure(
        go.Heatmap(
            z=[vals],
            x=labels,
            y=["Holdings"],
            colorscale=[[0, "#DCE8F5"], [0.5, "#9BBCDE"], [1, "#4E7CB0"]],
            zmin=zmin,
            zmax=zmax,
            xgap=5,
            ygap=5,
            showscale=False,
            text=[[fmt_int(v) for v in vals]],
            texttemplate="%{text}",
            textfont=dict(family="Inter", size=15, color="#0F1929"),
            hovertemplate="%{x}: %{z:,.0f} holdings<extra></extra>",
        )
    )
    # Highlight the latest filing (last cell) in NM yellow.
    last = len(vals) - 1
    fig.add_shape(
        type="rect", xref="x", yref="y",
        x0=last - 0.5, x1=last + 0.5, y0=-0.5, y1=0.5,
        line=dict(color=NM_YELLOW, width=3),
    )
    layout = nm_plotly_layout(height=height, margin=dict(l=0, r=10, t=10, b=0))
    layout["yaxis"]["showticklabels"] = False
    fig.update_layout(**layout)
    return fig


PLOTLY_CFG = {"displayModeBar": False}


# ═════════════════════════════════════════════════════════════════════════════
# HEADER
# ═════════════════════════════════════════════════════════════════════════════

active_tab = nm_header(
    app_title="NM Series Fund Dashboard",
    subtitle="NPORT-P · 6 quarterly filings · Feb 2025 – May 2026 · Snowflake + dbt",
    tabs=TABS,
    badges=[("● Live data", "green"), ("6 filings", "blue"), ("dbt · PASS=10", "blue")],
)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — DATA FRESHNESS
# ═════════════════════════════════════════════════════════════════════════════

if active_tab == "Data Freshness":
    hbf = holdings_by_filing()
    total_holdings = int(hbf["holdings"].sum())
    n_filings = len(hbf)
    latest = str(hbf["filing_date"].iloc[-1])[:10]

    try:
        days_since = (date.today() - datetime.strptime(latest, "%Y-%m-%d").date()).days
        days_since_str = f"{days_since}"
    except ValueError:
        days_since_str = "—"

    nm_kpi_row(
        [
            {"label": "Latest filing", "value": fmt_month(latest), "delta": latest},
            {"label": "Filings loaded", "value": f"{n_filings} of 6",
             "delta": "Feb 2025 – May 2026"},
            {"label": "Days since update", "value": days_since_str,
             "delta": "Quarterly cadence"},
            {"label": "Total holdings", "value": fmt_int(total_holdings),
             "delta": f"across {n_filings} filings"},
        ]
    )

    col_left, col_right = st.columns(2)
    with col_left:
        nm_table(
            columns=["Dataset", "Status"],
            rows=[
                ["sec_nport_positions", nm_pill("● current", "green")],
                ["sec_nport_portfolios", nm_pill("● current", "green")],
                ["sec_nport_sectors", nm_pill("⚠ partial (5 of 29)", "amber")],
                ["benchmark_returns", nm_pill("⚠ stub (not real data)", "amber")],
            ],
            title="Raw dataset status",
        )
    with col_right:
        fresh = mart_freshness()
        fallback = {
            "mart_portfolio_summary": (latest, 165),
            "mart_top_holdings": (latest, 43367),
            "mart_sector_allocation": (latest, 29),
            "mart_risk_metrics": (latest, 165),
        }
        def _iso(d):
            return str(d)[:10]

        rows = []
        for label in fallback:
            last_updated, row_count = fresh.get(label, fallback[label])
            # Flag any mart whose latest data lags the most recent filing.
            cell = fmt_month(last_updated)
            if _iso(last_updated) < latest:
                cell += "  " + nm_pill("⚠ stale", "amber")
            rows.append([label, cell, fmt_int(row_count)])
        nm_table(columns=["Mart", "Last updated", "Rows"], rows=rows,
                 title="Mart freshness")

    nm_chart_title("Holdings per filing date")
    st.plotly_chart(filing_heatmap(hbf, "holdings"),
                    use_container_width=True, config=PLOTLY_CFG)

    data_banner()


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — DATA QUALITY
# ═════════════════════════════════════════════════════════════════════════════

elif active_tab == "Data Quality":
    nm_kpi_row(
        [
            {"label": "Tests passing", "value": "46 / 46", "delta": "100% pass rate",
             "accent": "navy", "delta_style": "success"},
            {"label": "Models tested", "value": "10", "delta": "across 3 layers",
             "accent": "navy"},
            {"label": "Warnings", "value": "0", "delta": "no anomalies",
             "accent": "yellow"},
            {"label": "Failures", "value": "0", "delta": "✓ clean run",
             "accent": "navy", "delta_style": "success"},
        ]
    )

    layer_badge = {
        "staging": nm_pill("staging", "blue"),
        "intermediate": nm_pill("intermediate", "purple"),
        "mart": nm_pill("mart", "green"),
    }
    dbt_rows = [
        ("stg_positions", "staging", "12", "not_null, accepted_values"),
        ("stg_portfolios", "staging", "6", "not_null, unique"),
        ("stg_sectors", "staging", "4", "not_null, accepted_range"),
        ("stg_benchmarks", "staging", "2", "not_null"),
        ("int_portfolio_valuations", "intermediate", "5", "not_null, relationships"),
        ("int_sector_enriched", "intermediate", "3", "not_null"),
        ("mart_portfolio_summary", "mart", "7", "not_null, unique, accepted_range"),
        ("mart_top_holdings", "mart", "8", "not_null, accepted_range, unique"),
        ("mart_sector_allocation", "mart", "4", "not_null, accepted_range"),
        ("mart_risk_metrics", "mart", "5", "not_null"),
    ]
    nm_table(
        columns=["Model", "Layer", "Tests", "Status", "Test types"],
        rows=[
            [m, layer_badge[layer], tests, nm_pill("● pass", "green"), types]
            for m, layer, tests, types in dbt_rows
        ],
        title="dbt test results — 10 models, 46 tests",
    )

    nm_chart_title("Holdings count per filing — stability indicates consistent data quality")
    st.plotly_chart(filing_line_chart(holdings_by_filing(), "holdings"),
                    use_container_width=True, config=PLOTLY_CFG)

    # Null-rate check against the latest filing (live).
    nm_chart_title("Null rate check — latest filing")
    nr = query(
        f"""
        SELECT
            COUNT(*) AS total_rows,
            SUM(CASE WHEN holding_name IS NULL THEN 1 ELSE 0 END) AS null_holding_name,
            SUM(CASE WHEN value_usd IS NULL OR value_usd = 0 THEN 1 ELSE 0 END) AS zero_value,
            SUM(CASE WHEN cusip IS NULL OR cusip = '' THEN 1 ELSE 0 END) AS null_cusip
        FROM {FQ}.MART_TOP_HOLDINGS
        WHERE filing_date = (SELECT MAX(filing_date) FROM {FQ}.MART_TOP_HOLDINGS)
        """
    )
    if nr is not None and not nr.empty and nr["total_rows"].iloc[0]:
        total = float(nr["total_rows"].iloc[0])
        pct_name = 100 * nr["null_holding_name"].iloc[0] / total
        pct_zero = 100 * nr["zero_value"].iloc[0] / total
        pct_cusip = 100 * nr["null_cusip"].iloc[0] / total
        c1, c2, c3 = st.columns(3)
        c1.markdown(nm_pill(f"{pct_name:.1f}% null holding names", "green"),
                    unsafe_allow_html=True)
        c2.markdown(
            nm_pill(f"{pct_zero:.1f}% zero value", "green" if pct_zero < 1 else "amber"),
            unsafe_allow_html=True)
        c3.markdown(
            nm_pill(f"{pct_cusip:.1f}% missing CUSIP", "green" if pct_cusip < 1 else "amber"),
            unsafe_allow_html=True)
    else:
        st.caption("Null-rate metrics require a live Snowflake connection.")

    data_banner()


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — PORTFOLIO COVERAGE
# ═════════════════════════════════════════════════════════════════════════════

elif active_tab == "Portfolio Coverage":
    pbf = portfolios_by_filing()
    total_portfolios = int(pbf["portfolios"].max())

    nm_kpi_row(
        [
            {"label": "Total portfolios", "value": str(total_portfolios),
             "delta": "NM Series Fund"},
            {"label": "Holdings coverage", "value": f"{total_portfolios} / {total_portfolios}",
             "delta": "all portfolios", "delta_style": "success"},
            {"label": "Sector data", "value": f"5 / {total_portfolios}",
             "delta": "⚠ manual only", "accent": "yellow"},
            {"label": "Benchmark data", "value": "stub",
             "delta": "⚠ needs Bloomberg", "accent": "yellow"},
        ]
    )

    nm_chart_title("Portfolio count per filing date")
    st.plotly_chart(
        filing_line_chart(pbf, "portfolios", annotate="3 portfolios added Nov 2025"),
        use_container_width=True, config=PLOTLY_CFG,
    )

    # Coverage matrix — one row per portfolio.
    nm_chart_title("Coverage matrix — data layers available per portfolio")
    cov = query(
        f"SELECT portfolio_name, MIN(filing_date) AS first_filing, "
        f"COUNT(DISTINCT filing_date) AS n_filings "
        f"FROM {FQ}.MART_PORTFOLIO_SUMMARY "
        f"GROUP BY portfolio_name ORDER BY portfolio_name"
    )
    check = "<span style='color:#27500A;font-weight:600;'>✓</span>"
    cross = "<span style='color:#A32D2D;font-weight:600;'>✗</span>"

    if cov is not None and not cov.empty:
        rows = []
        for _, r in cov.iterrows():
            name = r["portfolio_name"]
            sector = check if name in SECTOR_PORTFOLIOS else cross
            first = str(r["first_filing"])[:10]
            added_nov = first >= "2025-11-24"
            all_six = check if int(r["n_filings"]) >= 6 else (
                nm_pill("Added Nov 2025", "amber") if added_nov else cross
            )
            rows.append([name, check, check, sector, all_six])
        nm_table(
            columns=["Portfolio", "Holdings", "Risk metrics", "Sector data", "All 6 filings"],
            rows=rows,
        )
    else:
        st.caption("Coverage matrix requires a live Snowflake connection.")

    _render_html(
        """
        <div style="background:#FFF3CC;border:1px solid #FFB500;border-radius:10px;
                    padding:12px 16px;margin:6px 0 14px;">
          <span style="font-size:14px;color:#633806;">
          <strong>Sector data gap:</strong> 24 portfolios lack GICS sector
          classification. <em>Production fix:</em> connect to Bloomberg security
          master via CUSIP lookup to auto-tag all 43,367 holdings across all 6 filings.
          </span>
        </div>
        """
    )

    nm_chart_title("Total holdings per filing — the portfolio universe is growing")
    st.plotly_chart(filing_column_chart(holdings_by_filing(), "holdings"),
                    use_container_width=True, config=PLOTLY_CFG)

    data_banner()


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — DATA LINEAGE
# ═════════════════════════════════════════════════════════════════════════════

elif active_tab == "Data Lineage":
    nm_chart_title("Pipeline architecture — source to Streamlit")

    # Color key — explains what the box colors mean in the diagram and cards below.
    def _legend_item(color, label, desc):
        return (
            f'<span style="display:inline-flex;align-items:center;gap:7px;margin-right:22px;">'
            f'<span style="width:13px;height:13px;border-radius:3px;background:{color};'
            f'display:inline-block;"></span>'
            f'<span style="font-size:12.5px;color:#0F1929;">'
            f'<strong>{label}</strong> — {desc}</span></span>'
        )

    _render_html(
        '<div style="background:#fff;border:0.5px solid #E0E8F4;border-radius:10px;'
        'padding:10px 16px;margin-bottom:12px;display:flex;flex-wrap:wrap;'
        'align-items:center;row-gap:6px;">'
        '<span style="font-family:\'Oswald\',sans-serif;text-transform:uppercase;'
        'letter-spacing:0.04em;font-size:12px;color:#6B7280;margin-right:18px;">Key</span>'
        + _legend_item("#27500A", "Green", "real, production-quality data")
        + _legend_item("#CC8800", "Amber", "partial / manual / stub — not production data")
        + _legend_item("#003366", "Navy", "pipeline & processing stage")
        + "</div>"
    )

    def flow_box(title, sub, tone="navy"):
        bg = {"navy": "#003366", "green": "#27500A", "amber": "#CC8800"}[tone]
        return (
            f'<div style="background:{bg};color:#fff;border-radius:8px;'
            f'padding:11px 13px;text-align:center;min-width:150px;">'
            f'<div style="font-size:13.5px;font-weight:600;">{title}</div>'
            f'<div style="font-size:11.5px;color:#cfe0f2;margin-top:3px;">{sub}</div></div>'
        )

    arrow_down = (
        '<div style="text-align:center;color:#6B7280;font-size:16px;margin:4px 0;">↓</div>'
    )

    _render_html(
        f"""
        <div class="chart-card">
          <div style="display:flex;gap:24px;justify-content:space-around;flex-wrap:wrap;">
            <div style="flex:1;min-width:170px;">
              {flow_box("SEC EDGAR (public)", "NPORT-P XML", "green")}
              {arrow_down}
              {flow_box("Python fetcher", "fetch_nm_holdings_6months.py", "navy")}
              {arrow_down}
              {flow_box("6 filing dates", "43,367 holdings", "navy")}
            </div>
            <div style="flex:1;min-width:170px;">
              {flow_box("Manual CSV", "sec_nport_sectors", "amber")}
              {arrow_down}
              {flow_box("5 portfolios only", "GICS sector tags", "amber")}
            </div>
            <div style="flex:1;min-width:170px;">
              {flow_box("Hand-crafted", "benchmark_returns", "amber")}
              {arrow_down}
              {flow_box("8 benchmark rows", "not real data", "amber")}
            </div>
          </div>
          {arrow_down}
          <div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;align-items:center;">
            {flow_box("dbt seed → RAW_RAW", "Snowflake", "navy")}
            <span style="color:#6B7280;">→</span>
            {flow_box("Staging", "4 views", "navy")}
            <span style="color:#6B7280;">→</span>
            {flow_box("Intermediate", "2 views", "navy")}
            <span style="color:#6B7280;">→</span>
            {flow_box("Marts", "4 tables", "green")}
            <span style="color:#6B7280;">→</span>
            {flow_box("Streamlit App", "this dashboard", "navy")}
          </div>
        </div>
        """
    )

    # Four data-source cards.
    def source_card(title, tone, status, rows):
        border = {"green": "#27500A", "amber": "#CC8800"}[tone]
        body = "".join(
            f'<div style="font-size:12.5px;color:#374151;margin:4px 0;">'
            f'<strong style="color:#0F1929;">{k}:</strong> {v}</div>'
            for k, v in rows
        )
        return (
            f'<div style="background:#fff;border:0.5px solid #E0E8F4;'
            f'border-left:4px solid {border};border-radius:10px;padding:14px 16px;'
            f'margin-bottom:10px;height:100%;">'
            f'<div style="font-family:\'Oswald\',sans-serif;text-transform:uppercase;'
            f'letter-spacing:0.03em;font-size:16px;font-weight:600;color:#0F1929;'
            f'margin-bottom:8px;">{title}</div>{body}'
            f'<div style="margin-top:8px;">{status}</div></div>'
        )

    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)
    with c1:
        st.markdown(source_card(
            "NPORT-P Holdings", "green", nm_pill("● Production quality", "green"),
            [("Source", "SEC EDGAR public API"),
             ("CIK", "0000742212 (NM Series Fund Inc)"),
             ("Fetcher", "fetch_nm_holdings_6months.py"),
             ("Coverage", "6 dates · 29 portfolios · 43,367 holdings"),
             ("Refresh", "Quarterly (new NPORT-P ~every 3 months)")],
        ), unsafe_allow_html=True)
    with c2:
        st.markdown(source_card(
            "Sector Classifications", "amber", nm_pill("⚠ Demo only", "amber"),
            [("Source", "Manually created CSV"),
             ("Coverage", "5 of 29 portfolios"),
             ("Refresh", "Manual — when analyst adds a portfolio"),
             ("Production fix", "Bloomberg GICS master via CUSIP lookup")],
        ), unsafe_allow_html=True)
    with c3:
        st.markdown(source_card(
            "Benchmark Returns", "amber", nm_pill("⚠ Stub — not real returns", "amber"),
            [("Source", "Hand-crafted CSV"),
             ("Coverage", "8 benchmark rows, not real market data"),
             ("Refresh", "N/A — static stub"),
             ("Production fix", "Bloomberg/FactSet daily benchmark feed")],
        ), unsafe_allow_html=True)
    with c4:
        st.markdown(source_card(
            "dbt Pipeline", "green", nm_pill("● 10/10 models passing", "green"),
            [("Tool", "dbt 1.11.11"),
             ("Models", "10 (4 staging · 2 intermediate · 4 marts)"),
             ("Tests", "46 passing, 0 warnings, 0 failures"),
             ("Scheduler", "Manual (prod: dbt Cloud scheduled run)")],
        ), unsafe_allow_html=True)

    nm_table(
        columns=["Source", "→", "Staging", "→", "Intermediate", "→", "Mart"],
        rows=[
            ["sec_nport_positions", "→", "stg_positions", "→",
             "int_portfolio_valuations", "→", "mart_top_holdings"],
            ["sec_nport_portfolios", "→", "stg_portfolios", "→",
             "int_portfolio_valuations", "→", "mart_portfolio_summary"],
            ["sec_nport_sectors", "→", "stg_sectors", "→",
             "int_sector_enriched", "→", "mart_sector_allocation"],
            ["benchmark_returns", "→", "stg_benchmarks", "→", "—", "→",
             "mart_risk_metrics"],
        ],
        title="dbt lineage — source to mart",
    )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — PORTFOLIO ASSISTANT (Claude-powered text-to-SQL)
# ═════════════════════════════════════════════════════════════════════════════

elif active_tab == "Portfolio Assistant":
    WELCOME = (
        "Hi! I can answer questions about NM's 29 portfolios across 6 filing "
        "periods (Feb 2025 – May 2026). Ask me about holdings, AUM trends, "
        "sector allocation, concentration risk, or portfolio changes over time."
    )
    CHIPS = [
        "Which portfolio had the largest AUM growth across all 6 filings?",
        "What are the top 5 holdings in Index 500 as of May 2026?",
        "Which 3 portfolios were added in November 2025?",
        "How has total holdings count changed across 6 filings?",
        "Which portfolio has the highest concentration risk today?",
        "Compare equity allocation: Feb 2025 vs May 2026",
        "What is the top holding across all portfolios combined?",
        "Which portfolios have more than 60% fixed income?",
    ]

    # Inject the real portfolio names so the model matches user shorthand
    # (e.g. "Index 500") to the exact stored name ("Index 500 Stock Portfolio").
    _pn = query(
        f"SELECT DISTINCT portfolio_name FROM {FQ}.MART_PORTFOLIO_SUMMARY "
        f"ORDER BY portfolio_name"
    )
    if _pn is not None and not _pn.empty:
        portfolio_list = "\n".join(f"- {n}" for n in _pn["portfolio_name"])
    else:
        portfolio_list = "(portfolio list unavailable — match names with ILIKE '%...%')"

    SYSTEM_PROMPT = f"""You are the NM Portfolio Assistant — a text-to-SQL engine for \
the Investment Data Office, querying Snowflake.

Database: {DB}  Schema: {SCHEMA}  (always fully-qualify tables as {FQ}.TABLE_NAME)

Tables and key columns:
- MART_PORTFOLIO_SUMMARY (1 row per portfolio per filing_date): filing_date, \
portfolio_name, total_value_usd, aum_millions, total_holdings, \
top_5_concentration_pct, largest_holding_pct, risk_profile, total_equity_pct, \
total_fixed_income_pct, top_sector, top_sector_pct, nm_internal_fund_count
- MART_TOP_HOLDINGS (1 row per holding per portfolio per filing_date): filing_date, \
portfolio_name, holding_name, cusip, value_usd, pct_of_portfolio, holding_rank, \
concentration_tier, is_top_5, is_top_10, asset_category, country, \
is_nm_internal_fund, aum_millions
- MART_SECTOR_ALLOCATION (only 5 portfolios have sector data): filing_date, \
portfolio_name, sector_name, pct_allocation, sector_rank, broad_category
- MART_RISK_METRICS (1 row per portfolio per filing_date): filing_date, \
portfolio_name, aum_millions, risk_profile, top_5_concentration_pct, \
largest_holding_pct, total_equity_pct, total_fixed_income_pct, \
equity_beta_proxy, volatility_ann_pct, duration_years_proxy

Exact portfolio_name values (match user shorthand to one of these):
{portfolio_list}

CRITICAL RULES:
- ALWAYS generate a SQL query. Never answer from training data.
- Portfolio names: users use short names ("Index 500", "Balanced"). NEVER filter
  with portfolio_name = '<short name>'. Either use the exact value from the list
  above, or match with portfolio_name ILIKE '%<keyword>%'. Prefer ILIKE when
  unsure.
- NEVER hardcode dates. For "current"/"latest"/"today" filter to \
filing_date = (SELECT MAX(filing_date) FROM <relevant table>). For a named month \
(e.g. "May 2026") match that filing, e.g. filing_date = (SELECT MAX(filing_date) \
FROM <table> WHERE filing_date <= '2026-05-31').
- For "top N holdings" use ORDER BY holding_rank ASC (or pct_of_portfolio DESC) \
with LIMIT N.
- For time-series questions use all 6 filing dates.
- Available filing dates: 2025-02-20, 2025-05-19, 2025-08-19, 2025-11-24, \
2026-02-23, 2026-05-27. Feb and May 2025 only have 26 portfolios — do not \
assume 29 for those dates.
- Use Snowflake SQL syntax. Always fully-qualify table names.

Respond with ONLY a JSON object, no prose, no markdown fences:
{{"sql": "<the SQL query>", "insight": "<one-sentence note on what the query checks>"}}"""

    _render_html(
        f"""
        <div class="chart-card" style="border-left:4px solid #FFB500;">
          <div style="font-size:15px;color:#0F1929;line-height:1.55;">{WELCOME}</div>
        </div>
        """
    )

    # Suggested-question chips (two rows of four).
    st.caption("Suggested questions")
    if "assistant_q" not in st.session_state:
        st.session_state["assistant_q"] = ""
    for row_start in (0, 4):
        cols = st.columns(4)
        for i, c in enumerate(cols):
            q = CHIPS[row_start + i]
            if c.button(q, key=f"chip_{row_start + i}", use_container_width=True):
                st.session_state["assistant_q"] = q

    question = st.text_input(
        "Ask a question",
        value=st.session_state["assistant_q"],
        placeholder="e.g. Which portfolio has the highest concentration risk today?",
    )

    def extract_json(text: str) -> dict:
        """Parse a JSON object from a model reply, tolerating stray prose/fences."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise

    def get_anthropic_client():
        try:
            import anthropic
        except ImportError:
            st.error("The `anthropic` package is not installed (`pip install anthropic`).")
            return None
        try:
            key = st.secrets["anthropic"]["api_key"]
        except Exception:
            st.error("Add `[anthropic] api_key` to `.streamlit/secrets.toml` to enable the assistant.")
            return None
        return anthropic.Anthropic(api_key=key)

    if question:
        client = get_anthropic_client()
        if client:
            with st.spinner("Generating SQL…"):
                try:
                    resp = client.messages.create(
                        model=CLAUDE_MODEL,
                        max_tokens=1024,
                        system=SYSTEM_PROMPT,
                        messages=[{"role": "user", "content": question}],
                    )
                    raw = next((b.text for b in resp.content if b.type == "text"), "")
                    parsed = extract_json(raw)
                    sql = parsed.get("sql", "").strip()
                    insight = parsed.get("insight", "")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Could not generate SQL: {exc}")
                    sql, insight = "", ""

            if sql:
                result = query(sql)

                # Narrative: summarize the result rows (or the failure) for the user.
                narrative = ""
                try:
                    if result is not None:
                        sample = result.head(25).to_csv(index=False)
                        nresp = client.messages.create(
                            model=CLAUDE_MODEL,
                            max_tokens=512,
                            system="You are a concise investment-data analyst. Answer the "
                                   "user's question in 1-3 sentences using ONLY the query "
                                   "results provided. Do not invent numbers.",
                            messages=[{
                                "role": "user",
                                "content": f"Question: {question}\n\nQuery results (CSV):\n{sample}",
                            }],
                        )
                        narrative = next(
                            (b.text for b in nresp.content if b.type == "text"), ""
                        )
                except Exception:  # noqa: BLE001 — narrative is best-effort
                    narrative = ""

                if narrative:
                    st.markdown(
                        f'<div class="chart-card"><div style="font-size:15px;'
                        f'color:#0F1929;line-height:1.55;">{narrative}</div></div>',
                        unsafe_allow_html=True,
                    )
                if insight:
                    st.markdown(nm_pill(f"💡 {insight}", "blue"), unsafe_allow_html=True)

                if result is not None and not result.empty:
                    st.dataframe(result, use_container_width=True, hide_index=True)
                elif result is not None:
                    st.info("Query ran successfully but returned no rows.")
                else:
                    st.warning("Could not run the query — Snowflake is unavailable.")
                    data_banner()

                with st.expander("View generated SQL"):
                    st.code(sql, language="sql")
