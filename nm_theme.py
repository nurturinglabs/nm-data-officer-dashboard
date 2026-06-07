"""
nm_theme.py
Northwestern Mutual Streamlit Design System
Extracted from: nm-portfolio-intelligence.streamlit.app

Drop into any NM Streamlit project for instant brand consistency.

Usage:
    from nm_theme import (
        NM_BASE_CSS, COLORS, PIE_COLORS,
        nm_inject_css, nm_header, nm_kpi_card, nm_kpi_row,
        nm_chart_title, nm_plotly_layout, nm_bar_chart, nm_pie_chart,
        nm_table, nm_pill, nm_risk_pill, nm_port_card,
        fmt_aum, fmt_pct
    )
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def _render_html(html: str):
    """
    Render an HTML string via st.markdown.

    Streamlit's markdown renderer treats any line indented 4+ spaces as a code
    block, which displays raw HTML instead of rendering it. The HTML literals in
    this module are indented to match their surrounding Python, so we strip the
    per-line leading whitespace (harmless for these style-attribute divs) before
    rendering.
    """
    cleaned = "\n".join(line.lstrip() for line in html.splitlines())
    st.markdown(cleaned, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# BRAND COLORS  (extracted from deployed app)
# ─────────────────────────────────────────────────────────────────────────────

NM_NAVY        = "#003366"   # Primary — Dark Ocean Blue
NM_YELLOW      = "#FFB500"   # Primary — Chinese Yellow
NM_BLUE_DARK   = "#004D99"   # Badge blue background
NM_BLUE_MID    = "#1A6EB5"   # Chart secondary
NM_GOLD_DARK   = "#CC8800"   # Delta text / amber
NM_GOLD_LIGHT  = "#E6C200"   # Chart tertiary
NM_TEXT_MAIN   = "#0F1929"   # Primary text
NM_TEXT_MUTED  = "#6B7280"   # Muted labels
NM_TEXT_NAV    = "#93B8D8"   # Nav inactive
NM_TEXT_SUB    = "#6B8FC0"   # Header subtitle
NM_BG_PAGE     = "#F5F7FA"   # App background
NM_BG_CARD     = "#FFFFFF"   # Card background
NM_BG_STRIPE   = "#FAFBFD"   # Alternating table row
NM_BORDER      = "#E0E8F4"   # Card borders
NM_BORDER_GRID = "#F0F4FA"   # Grid / table row border
NM_GREEN_TEXT  = "#27500A"   # Success text
NM_RED_TEXT    = "#A32D2D"   # Danger text

# Chart color palette — use in order
COLORS = [
    "#003366",  # Navy
    "#FFB500",  # Yellow
    "#1A6EB5",  # Blue mid
    "#CC8800",  # Gold dark
    "#4D9FD6",  # Blue light
    "#E6C200",  # Gold light
    "#336699",  # Blue muted
    "#F0A500",  # Amber
    "#005599",  # Blue deep
    "#FFD060",  # Yellow light
]

# Pie chart palette — alternates navy/yellow family
PIE_COLORS = ["#003366","#FFB500","#1A6EB5","#CC8800","#4D9FD6","#E6C200","#336699","#F0A500"]


# ─────────────────────────────────────────────────────────────────────────────
# BASE CSS  (extracted verbatim from deployed app)
# ─────────────────────────────────────────────────────────────────────────────

NM_BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Inter:wght@400;500;600;700&family=DM+Mono&display=swap');
/* Body / data layer — clean humanist sans */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; font-size: 15px; }
.stApp, .stApp p, .stApp span, .stApp div, .stApp label { font-family: 'Inter', sans-serif; }
.stApp p { line-height: 1.5; }
/* Headline / label layer — condensed display, like the NM brand hero (Oswald ≈ NM headline face) */
.chart-title, .kpi-label, .tbl th, .nm-display {
    font-family: 'Oswald', 'Inter', sans-serif !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.block-container { padding-top: 0.5rem !important; padding-bottom: 1rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
div[data-testid="stVerticalBlock"] > div { gap: 0.4rem !important; }
div[data-testid="element-container"] { margin: 0 !important; }
.stPlotlyChart > div { margin: 0 !important; }
.stSelectbox { margin-bottom: 0 !important; }
.stTabs [data-baseweb="tab-list"] {
    gap: 0px; background: #fff; border: 2px solid #003366;
    border-radius: 10px; padding: 4px; margin-bottom: 12px; width: fit-content;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px; padding: 6px 20px; font-size: 14px;
    font-weight: 500; color: #003366; background: transparent; border: none;
}
.stTabs [aria-selected="true"] { background: #003366 !important; color: #FFB500 !important; }
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 12px !important; }
section[data-testid="stAppViewContainer"] { padding-top: 0 !important; }
section[data-testid="stAppViewContainer"] > div:first-child { padding-top: 0 !important; }
div[data-testid="stAppViewBlockContainer"] { padding-top: 0.5rem !important; }
#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
.stApp { background: #F5F7FA; }

/* Topbar */
.nm-topbar {
    background: #003366; padding: 14px 24px;
    border-radius: 12px 12px 0 0;
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 0;
}
.nm-topbar-title { font-size: 18px; font-weight: 500; color: #fff; margin: 0; }
.nm-topbar-sub { font-size: 12.5px; color: #B8D4F0; margin: 2px 0 0; }
.nm-badge { display: inline-block; font-size: 11px; font-weight: 500; padding: 3px 9px; border-radius: 20px; margin-left: 6px; }
.badge-green { background: #FFB500; color: #003366; }
.badge-blue  { background: #004080; color: #B8D4F0; }

/* KPI cards */
.kpi-card { background: #fff; border: 0.5px solid #E0E8F4; border-radius: 10px; padding: 14px 18px; border-left: 3px solid #1B4F8A; }
.kpi-label { font-size: 11.5px; color: #6B7280; text-transform: uppercase; letter-spacing: 0.07em; margin: 0 0 5px; }
.kpi-value { font-size: 30px; font-weight: 500; color: #0F1929; margin: 0 0 3px; }
.kpi-delta-up   { font-size: 12.5px; color: #003D00; margin: 0; }
.kpi-delta-flat { font-size: 12.5px; color: #6B7280; margin: 0; }

/* Portfolio cards */
.port-card { background: #fff; border: 0.5px solid #E0E8F4; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; cursor: pointer; transition: border-color 0.15s; }
.port-card:hover { border-color: #FFB500; }
.port-card.selected { border: 1.5px solid #FFB500; background: #F5F9FF; }
.port-name { font-size: 15px; font-weight: 500; color: #0F1929; margin: 0 0 3px; }
.port-meta { font-size: 12.5px; color: #6B7280; margin: 0 0 8px; }

/* Risk pills */
.risk-pill { display: inline-block; font-size: 11.5px; font-weight: 500; padding: 3px 9px; border-radius: 20px; }
.risk-agg  { background: #FCEBEB; color: #A32D2D; }
.risk-bal  { background: #E6F1FB; color: #003366; }
.risk-gro  { background: #FAEEDA; color: #633806; }
.risk-con  { background: #EAF3DE; color: #003D00; }

/* Chart cards */
.chart-card { background: #fff; border: 0.5px solid #E0E8F4; border-radius: 10px; padding: 16px 18px; margin-bottom: 12px; }
.chart-title { font-size: 16px; font-weight: 600; color: #0F1929; margin: 0 0 14px; }

/* Data table */
.tbl { width: 100%; border-collapse: collapse; font-size: 14px; }
.tbl th { padding: 9px 12px; text-align: left; font-size: 11.5px; color: #6B7280; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1.5px solid #003366; font-weight: 600; }
.tbl td { padding: 10px 12px; border-bottom: 0.5px solid #F0F4FA; color: #1A2840; }
.tbl tr:nth-child(even) td { background: #FAFBFD; }

/* Pills */
.pill { display:inline-block; font-size:11.5px; font-weight:500; padding:3px 9px; border-radius:20px; }
.pill-green  { background:#EAF3DE; color:#27500A; }
.pill-amber  { background:#FAEEDA; color:#633806; }
.pill-blue   { background:#E6F1FB; color:#0C447C; }
.pill-purple { background:#EEEDFE; color:#3C3489; }

/* Nav radio */
div[role="radiogroup"] {
    background: #003366 !important; padding: 0 !important;
    display: flex !important; align-items: center !important;
    height: 100% !important; gap: 0 !important;
}
div[role="radiogroup"] > label {
    padding: 10px 16px !important; font-size: 14.5px !important;
    font-weight: 500 !important; color: #B8D4F0 !important;
    border-bottom: 3px solid transparent !important;
    cursor: pointer !important; white-space: nowrap !important;
}
div[role="radiogroup"] > label:hover { color: #fff !important; border-bottom-color: #FFB50066 !important; }
div[role="radiogroup"] > label[data-checked="true"] { color: #FFB500 !important; border-bottom-color: #FFB500 !important; font-weight: 600 !important; }
div[role="radiogroup"] > label > div:first-child { display: none !important; }
.stRadio > label { display: none !important; }
.stRadio > div { background: #003366 !important; border-radius: 0 12px 12px 0 !important; padding: 0 20px !important; margin: 0 !important; }

/* Misc */
.mono { font-family: 'DM Mono', monospace; font-size: 11px; }
div[data-testid="stHorizontalBlock"] > div { gap: 10px; }
.stPlotlyChart { border-radius: 8px; overflow: hidden; }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #B8D0E8; border-radius: 10px; }
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────────────────────────────────────

# Load Google Fonts via <link> + preconnect. `@import` inside a Streamlit-injected
# <style> loads unreliably on Streamlit Cloud (a fresh client falls back to system
# fonts), so we use stylesheet links as the primary load path; the @import in
# NM_BASE_CSS stays as a fallback.
NM_FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" '
    'href="https://fonts.googleapis.com/css2?'
    'family=Oswald:wght@500;600;700&'
    'family=Inter:wght@400;500;600;700&'
    'family=DM+Mono&display=swap">'
)


def nm_inject_css():
    """
    Inject NM fonts + base CSS. Call once at top of app.py after set_page_config().

    Example:
        st.set_page_config(page_title="NM · My App", layout="wide")
        from nm_theme import nm_inject_css
        nm_inject_css()
    """
    st.markdown(NM_FONT_LINKS, unsafe_allow_html=True)
    st.markdown(NM_BASE_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# FORMATTING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def fmt_aum(v) -> str:
    """Format a dollar value as $XB / $XM / $XK."""
    if v is None or v == 0: return "N/A"
    if v >= 1e9: return f"${v/1e9:.1f}B"
    if v >= 1e6: return f"${v/1e6:.0f}M"
    if v >= 1e3: return f"${v/1e3:.0f}K"
    return f"${v:.0f}"


def fmt_pct(v, decimals: int = 2) -> str:
    """Format a percentage value."""
    return f"{v:.{decimals}f}%"


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

def nm_header(
    app_title: str,
    subtitle: str,
    tabs: list = None,
    active_tab: str = None,
    badges: list = None,
):
    """
    Full NM header with title, nav tabs, badges, and KPI row.
    Nav uses query_params — clicking a tab reloads with ?tab=TabName.

    Args:
        app_title:  App name shown after "Northwestern Mutual ·"
        subtitle:   Small descriptor (data source, date, stack)
        tabs:       List of tab name strings for nav links
        active_tab: Currently active tab name
        badges:     List of (label, style) — style: "green"|"blue"

    Returns:
        active_tab (str) — the currently selected tab

    Example:
        active_tab = nm_header(
            app_title="Portfolio Intelligence",
            subtitle="29 portfolios · SEC NPORT-P · Feb 2026",
            tabs=["Overview", "All portfolios", "Compare", "Risk", "Data quality"],
            badges=[("● dbt passing", "green"), ("Snowflake live", "blue")],
        )
    """
    # Resolve active tab from query params if not passed
    if active_tab is None and tabs:
        params = st.query_params
        active_tab = params.get("tab", tabs[0])
        if active_tab not in tabs:
            active_tab = tabs[0]

    # Badge HTML
    badge_styles = {
        "green": "background:#FFB500;color:#003366;font-weight:700;",
        "blue":  "background:#004D99;color:#B8D4F0;",
    }
    badge_html = ""
    if badges:
        for label, style in badges:
            s = badge_styles.get(style, badge_styles["blue"])
            badge_html += (
                f'<span style="{s}font-family:\'Oswald\',sans-serif;'
                f'text-transform:uppercase;letter-spacing:0.04em;'
                f'font-size:11px;padding:4px 10px;'
                f'border-radius:20px;">{label}</span>'
            )

    # Nav HTML
    nav_html = ""
    if tabs:
        def nav_link(label, active):
            if active:
                link_style = "color:#FFB500;font-weight:600;border-bottom:3px solid #FFB500;"
            else:
                link_style = "color:#93B8D8;border-bottom:3px solid transparent;"
            tab_param = label.replace(" ", "+")
            return (
                f'<a href="?tab={tab_param}" target="_self" '
                f'style="text-decoration:none;font-family:\'Oswald\',sans-serif;'
                f'text-transform:uppercase;letter-spacing:0.04em;font-size:14.5px;'
                f'padding:10px 16px 12px;'
                f'display:inline-block;{link_style};white-space:nowrap;">'
                f'{label}</a>'
            )
        nav_html = "".join([nav_link(t, t == active_tab) for t in tabs])

    nav_row = (
        f'<div style="display:flex;align-items:center;gap:0;margin:0 -8px;">'
        f'{nav_html}</div>'
    ) if nav_html else ""

    _render_html(f"""
    <div style="background:#003366;border-radius:12px;padding:16px 24px 0 24px;margin-bottom:16px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
        <div>
          <span style="color:#FFB500;font-family:'Oswald',sans-serif;font-weight:700;font-size:28px;text-transform:uppercase;letter-spacing:0.01em;">
            Northwestern Mutual
          </span>
          <span style="color:#B8D4F0;font-size:15px;font-weight:400;margin-left:10px;">
            · {app_title}
          </span>
          <p style="color:#6B8FC0;font-size:12.5px;margin:4px 0 0;">{subtitle}</p>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">{badge_html}</div>
      </div>
      {nav_row}
    </div>
    """)

    return active_tab


# ─────────────────────────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────────────────────────

def nm_kpi_row(metrics: list):
    """
    Render a grid of KPI cards — alternating navy/yellow top borders.
    All rendered as one HTML block (no Streamlit gap issues).

    Args:
        metrics: List of dicts with keys:
            label:  str  — uppercase label
            value:  str  — big display number
            delta:  str  — small subtext
            accent: str  — "navy"|"yellow" (optional, alternates by default)
            delta_style: str — "up"|"flat" (optional)

    Example:
        nm_kpi_row([
            {"label": "Total portfolios", "value": "29",    "delta": "Feb 2026 NPORT-P"},
            {"label": "Total holdings",   "value": "7,324", "delta": "↑ Full SEC data"},
            {"label": "dbt models",       "value": "10",    "delta": "46 tests passing"},
            {"label": "Data quality",     "value": "100%",  "delta": "✓ No failures"},
        ])
    """
    accent_map  = {"navy": "#003366", "yellow": "#FFB500"}
    delta_color = {"up": "#CC8800", "flat": "#6B7280", "success": "#27500A"}

    cards_html = ""
    for i, m in enumerate(metrics):
        accent = accent_map.get(m.get("accent"), "#003366" if i % 2 == 0 else "#FFB500")
        dc = delta_color.get(m.get("delta_style", "flat"), "#6B7280")
        cards_html += f"""
        <div style="background:#fff;border:2px solid {accent};border-top:5px solid {accent};
                    border-radius:10px;padding:16px 20px;">
          <p style="font-family:'Oswald',sans-serif;font-size:12px;color:#6B7280;
                    text-transform:uppercase;letter-spacing:0.07em;margin:0 0 8px;">{m['label']}</p>
          <p style="font-size:34px;font-weight:700;color:#003366;
                    margin:0 0 5px;line-height:1;">{m['value']}</p>
          <p style="font-size:12.5px;color:{dc};margin:0;font-weight:500;">{m.get('delta','')}</p>
        </div>"""

    n = len(metrics)
    _render_html(f"""
    <div style="display:grid;grid-template-columns:repeat({n},1fr);gap:12px;margin-bottom:16px;">
      {cards_html}
    </div>
    """)


# ─────────────────────────────────────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def nm_chart_title(title: str):
    """Render a chart section title in NM style."""
    st.markdown(
        f'<p style="font-family:\'Oswald\',sans-serif;text-transform:uppercase;'
        f'letter-spacing:0.04em;font-size:17px;font-weight:600;color:#0F1929;'
        f'margin:0 0 6px;">{title}</p>',
        unsafe_allow_html=True
    )


def nm_plotly_layout(height: int = 300, margin: dict = None) -> dict:
    """
    Standard Plotly layout for NM apps.
    All text black, white background, DM Sans font.

    Example:
        fig.update_layout(**nm_plotly_layout(height=350))
    """
    return dict(
        height=height,
        margin=margin or dict(l=0, r=50, t=10, b=0),
        paper_bgcolor="#fff",
        plot_bgcolor="#fff",
        font=dict(family="DM Sans", color="#111827"),
        xaxis=dict(
            showgrid=False,
            color="#111827",
            tickfont=dict(size=12, family="DM Sans", color="#111827"),
            zeroline=False,
        ),
        yaxis=dict(
            showgrid=False,
            color="#111827",
            tickfont=dict(size=12, family="DM Sans", color="#111827"),
            zeroline=False,
        ),
        showlegend=False,
    )


def nm_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color: str = "#003366",
    height: int = 240,
    pct_format: bool = True,
    decimals: int = 1,
) -> go.Figure:
    """
    Horizontal bar chart in NM style.

    Args:
        df:         DataFrame with x_col and y_col
        x_col:      Column for bar length (numeric)
        y_col:      Column for bar label (text)
        color:      Bar color (default NM navy)
        height:     Chart height in px
        pct_format: If True, format text labels as percentages
        decimals:   Decimal places for text labels

    Example:
        df = pd.DataFrame({"sector": [...], "pct": [...]})
        fig = nm_bar_chart(df, "pct", "sector")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    """
    fmt = f"{{:.{decimals}f}}%" if pct_format else f"{{:.{decimals}f}}"
    fig = go.Figure(go.Bar(
        x=df[x_col], y=df[y_col], orientation="h",
        marker_color=color,
        text=[fmt.format(v) for v in df[x_col]],
        textposition="outside",
        textfont=dict(size=10, color="#111827", family="DM Sans"),
    ))
    layout = nm_plotly_layout(height=height)
    layout["xaxis"]["showticklabels"] = False
    layout["xaxis"]["range"] = [0, df[x_col].max() * 1.35]
    fig.update_layout(**layout)
    return fig


def nm_pie_chart(
    df: pd.DataFrame,
    labels_col: str,
    values_col: str,
    height: int = 280,
) -> go.Figure:
    """
    Donut pie chart in NM style with navy/yellow palette.

    Example:
        df = pd.DataFrame({"name": [...], "pct": [...]})
        fig = nm_pie_chart(df, "name", "pct")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    """
    fig = go.Figure(go.Pie(
        labels=df[labels_col],
        values=df[values_col],
        hole=0.42,
        marker_colors=PIE_COLORS[:len(df)],
        textinfo="label+percent",
        textfont=dict(size=11, family="DM Sans", color="#111827"),
    ))
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=height,
        paper_bgcolor="#fff",
        plot_bgcolor="#fff",
        showlegend=False,
        font=dict(family="DM Sans", color="#111827"),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# TABLE
# ─────────────────────────────────────────────────────────────────────────────

def nm_table(rows: list, columns: list, title: str = None):
    """
    NM-styled data table with navy header border and alternating rows.

    Args:
        columns: List of header strings
        rows:    List of lists — one per row (can include HTML strings)
        title:   Optional card title above table

    Example:
        nm_table(
            columns=["Model", "Layer", "Tests", "Status"],
            rows=[
                ["stg_positions", "staging", "4/4",
                 nm_pill("● passing", "green")],
            ],
            title="dbt test results"
        )
    """
    header_cells = "".join(f'<th>{c}</th>' for c in columns)
    body_rows = ""
    for i, row in enumerate(rows):
        bg = f"background:{NM_BG_STRIPE};" if i % 2 == 0 else ""
        cells = "".join(f'<td>{v}</td>' for v in row)
        body_rows += f'<tr style="{bg}">{cells}</tr>'

    title_html = (
        f'<p class="chart-title">{title}</p>'
    ) if title else ""

    _render_html(f"""
    <div class="chart-card">
      {title_html}
      <table class="tbl">
        <thead><tr>{header_cells}</tr></thead>
        <tbody>{body_rows}</tbody>
      </table>
    </div>
    """)


# ─────────────────────────────────────────────────────────────────────────────
# PILLS
# ─────────────────────────────────────────────────────────────────────────────

def nm_pill(label: str, style: str = "blue") -> str:
    """
    Return HTML for an inline status pill.
    Use inside table cells or markdown blocks.

    Styles: "green" | "amber" | "blue" | "purple"

    Example:
        st.markdown(nm_pill("● passing", "green"), unsafe_allow_html=True)
        # Inside table: nm_table(..., rows=[[nm_pill("NEW","green"), ...]])
    """
    classes = {
        "green":  "pill pill-green",
        "amber":  "pill pill-amber",
        "blue":   "pill pill-blue",
        "purple": "pill pill-purple",
    }
    cls = classes.get(style, "pill pill-blue")
    return f'<span class="{cls}">{label}</span>'


def nm_risk_pill(profile: str) -> str:
    """
    Return HTML for a portfolio risk profile pill.

    Profiles: "Aggressive" | "Balanced" | "Growth" | "Conservative"

    Example:
        st.markdown(nm_risk_pill("Balanced"), unsafe_allow_html=True)
    """
    mapping = {
        "Aggressive":   "risk-pill risk-agg",
        "Balanced":     "risk-pill risk-bal",
        "Growth":       "risk-pill risk-gro",
        "Conservative": "risk-pill risk-con",
    }
    cls = mapping.get(profile, "risk-pill risk-bal")
    return f'<span class="{cls}">{profile}</span>'


# ─────────────────────────────────────────────────────────────────────────────
# PORTFOLIO CARD
# ─────────────────────────────────────────────────────────────────────────────

def nm_port_card(
    name: str,
    asset_class: str,
    period: str,
    aum: int,
    total_holdings: int,
    top_holding_pct: float,
    equity_pct: float = 0,
    risk_profile: str = "Balanced",
):
    """
    Portfolio summary card with equity bar, risk pill, AUM.

    Example:
        nm_port_card(
            name="Index 500 Stock Portfolio",
            asset_class="Domestic Equity",
            period="Mar 2025",
            aum=1800000,
            total_holdings=504,
            top_holding_pct=8.9,
            equity_pct=95.0,
            risk_profile="Aggressive",
        )
    """
    bar_w = min(int(equity_pct), 100)
    risk_map = {
        "Aggressive": "risk-agg",
        "Balanced":   "risk-bal",
        "Growth":     "risk-gro",
        "Conservative": "risk-con",
    }
    risk_cls = risk_map.get(risk_profile, "risk-bal")

    _render_html(f"""
    <div class="port-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <p class="port-name">{name}</p>
        <span class="risk-pill {risk_cls}">{risk_profile}</span>
      </div>
      <p class="port-meta">{asset_class} · {period}</p>
      <div style="background:#F0F4FA;border-radius:4px;height:5px;margin-bottom:7px;overflow:hidden;">
        <div style="width:{bar_w}%;height:100%;background:#003366;border-radius:4px;"></div>
      </div>
      <div style="display:flex;justify-content:space-between;">
        <span style="font-size:11.5px;color:#6B7280;">AUM <strong style="color:#0F1929;">{fmt_aum(aum*1000)}</strong></span>
        <span style="font-size:11.5px;color:#6B7280;">Holdings <strong style="color:#0F1929;">{total_holdings}</strong></span>
        <span style="font-size:11.5px;color:#6B7280;">Top <strong style="color:#0F1929;">{top_holding_pct:.1f}%</strong></span>
      </div>
    </div>
    """)


# ─────────────────────────────────────────────────────────────────────────────
# QUICK START TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

QUICKSTART = '''
"""
Quick start template for a new NM Streamlit app.
Copy this, replace placeholders, and go.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from nm_theme import (
    nm_inject_css, nm_header, nm_kpi_row,
    nm_chart_title, nm_plotly_layout, nm_bar_chart, nm_pie_chart,
    nm_table, nm_pill, nm_risk_pill, COLORS, fmt_aum
)

st.set_page_config(
    page_title="Northwestern Mutual · [App Name]",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

nm_inject_css()

active_tab = nm_header(
    app_title="[App Name]",
    subtitle="[Data source] · [Date] · [Stack]",
    tabs=["Overview", "Detail", "Data quality"],
    badges=[("● Live", "green"), ("Snowflake", "blue")],
)

nm_kpi_row([
    {"label": "Metric 1", "value": "X",   "delta": "context"},
    {"label": "Metric 2", "value": "Y",   "delta": "context"},
    {"label": "Metric 3", "value": "Z",   "delta": "context"},
    {"label": "Metric 4", "value": "W%",  "delta": "context"},
])

if active_tab == "Overview":
    nm_chart_title("My Chart")
    df = pd.DataFrame({"label": ["A","B","C"], "value": [30, 50, 20]})
    fig = nm_bar_chart(df, "value", "label", color=COLORS[0])
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

elif active_tab == "Detail":
    pass

elif active_tab == "Data quality":
    nm_table(
        columns=["Model", "Layer", "Tests", "Status"],
        rows=[["stg_positions", "staging", "4/4", nm_pill("● passing", "green")]],
        title="dbt test results",
    )
'''
