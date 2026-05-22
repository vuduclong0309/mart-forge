"""
GME Options Mart — Dashboard

Reads the ADS market dashboard from a local DuckDB file produced by
`dbt run` and renders metric cards with fact-check links to free
public reference sites.

Educational Use Only / Not Financial Advice.
"""

import json
import pathlib

import duckdb
import streamlit as st

DB_PATH = pathlib.Path(__file__).parent.parent / "target" / "gme_options.duckdb"
ADS_TABLE = "gme_ads_market_dashboard"
DQC_SCORECARD = pathlib.Path(__file__).parent.parent / "dqc_scorecard.json"

METRIC_CARDS = [
    {
        "label": "Spot Price",
        "column": "spot",
        "fmt": "${:,.2f}",
        "verify_url": "https://finance.yahoo.com/quote/GME",
    },
    {
        "label": "Max Pain",
        "column": "max_pain_strike",
        "fmt": "${:,.0f}",
        "verify_url": "https://swaggystocks.com/dashboard/options-max-pain/GME",
    },
    {
        "label": "P/C Ratio",
        "column": "pc_ratio",
        "fmt": "{:.3f}",
        "verify_url": "https://www.barchart.com/stocks/quotes/GME/options-overview",
    },
    {
        "label": "Net GEX",
        "column": "net_gex",
        "fmt": "{:,.0f}",
        "verify_url": "https://squeezemetrics.com/monitor/dix",
    },
    {
        "label": "IV30",
        "column": "iv30",
        "fmt": "{:.1%}",
        "verify_url": "https://marketchameleon.com/Overview/GME/IV/",
    },
]

PHASE1_CARDS = [
    {
        "label": "Gamma Flip",
        "column": "gamma_flip_point",
        "fmt": "${:,.2f}",
        "verify_url": "https://squeezemetrics.com/monitor/dix",
    },
    {
        "label": "HV20",
        "column": "hv20",
        "fmt": "{:.1%}" if True else "N/A",
        "verify_url": "https://marketchameleon.com/Overview/GME/IV/",
    },
    {
        "label": "IV Rank",
        "column": "iv_rank",
        "fmt": "{:.1%}",
        "verify_url": "https://marketchameleon.com/Overview/GME/IV/",
    },
    {
        "label": "IV Percentile",
        "column": "iv_percentile",
        "fmt": "{:.1%}",
        "verify_url": "https://www.optionistics.com/quotes/iv-rank",
    },
    {
        "label": "OI Daily Delta",
        "column": "oi_daily_delta",
        "fmt": "{:,.0f}",
        "verify_url": "https://www.barchart.com/stocks/quotes/GME/options-overview",
    },
    {
        "label": "Dealer Net Gamma",
        "column": "dealer_net_gamma",
        "fmt": "{:,.0f}",
        "verify_url": "https://squeezemetrics.com/monitor/dix",
    },
]

st.set_page_config(page_title="GME Options Dashboard", layout="wide")


@st.cache_resource
def get_db():
    return duckdb.connect(str(DB_PATH), read_only=True)


_LATEST_COLUMNS = ", ".join([
    "pull_date",
    "spot",
    "max_pain_strike",
    "max_pain_convergence_pct",
    "net_gex",
    "pc_ratio",
    "top_oi_strike_1",
    "top_oi_strike_2",
    "top_oi_strike_3",
    "gamma_flip_point",
    "iv30",
    "hv20",
    "iv_rank",
    "oi_daily_delta",
    "dealer_net_gamma",
    "iv_percentile",
])


@st.cache_data(ttl=300)
def load_latest():
    db = get_db()
    return db.sql(
        f"SELECT {_LATEST_COLUMNS} FROM {ADS_TABLE}"
        " ORDER BY pull_date DESC LIMIT 1"
    ).fetchdf()


_HISTORY_COLUMNS = "pull_date, spot, net_gex, pc_ratio, iv30, hv20"


@st.cache_data(ttl=300)
def load_history():
    db = get_db()
    return db.sql(
        f"SELECT {_HISTORY_COLUMNS} FROM {ADS_TABLE} ORDER BY pull_date"
    ).fetchdf()


@st.cache_data(ttl=300)
def load_dqc():
    if DQC_SCORECARD.exists():
        return json.loads(DQC_SCORECARD.read_text())
    return None


def dqc_badge(scorecard: dict | None) -> str:
    if not scorecard:
        return ":gray[DQC: unknown]"
    statuses = [c["status"] for c in scorecard.get("controls", [])]
    if not statuses:
        return ":gray[DQC: UNKNOWN]"
    if any(s == "fail" for s in statuses):
        return ":red[DQC: FAIL]"
    if any(s == "unavailable" for s in statuses):
        return ":orange[DQC: PARTIAL]"
    if any(s in ("exhausted", "waived") for s in statuses):
        return ":orange[DQC: PASS WITH WAIVERS]"
    if any(s == "pending" for s in statuses):
        return ":orange[DQC: PENDING]"
    if all(s == "pass" for s in statuses):
        return ":green[DQC: PASS]"
    return ":gray[DQC: UNKNOWN]"


def render_cards(cards, row):
    cols = st.columns(len(cards))
    for i, card in enumerate(cards):
        with cols[i]:
            val = row.get(card["column"])
            if val is not None and val == val:
                formatted = card["fmt"].format(val)
            else:
                formatted = "N/A"
            st.metric(card["label"], formatted)
            st.caption(f"[Fact-check ↗]({card['verify_url']})")


def main():
    scorecard = load_dqc()

    st.title("GME Options Dashboard")
    st.markdown(
        f"{dqc_badge(scorecard)} · "
        "Educational Use Only / Not Financial Advice"
    )

    df = load_latest()
    if df.empty:
        st.warning("No data — run `dbt run --profiles-dir .` first.")
        return

    row = df.iloc[0]
    st.caption(f"Data as of: **{row.get('pull_date', 'N/A')}**")

    st.subheader("Market Overview")
    render_cards(METRIC_CARDS, row)

    st.divider()

    st.subheader("Phase-1 Options Metrics")
    render_cards(PHASE1_CARDS, row)

    st.divider()

    st.subheader("Top OI Strikes")
    oi_cols = st.columns(3)
    for i, col_name in enumerate(["top_oi_strike_1", "top_oi_strike_2", "top_oi_strike_3"]):
        with oi_cols[i]:
            val = row.get(col_name)
            st.metric(f"#{i+1}", f"${val:,.0f}" if val is not None else "N/A")

    history = load_history()
    if not history.empty and len(history) > 1:
        st.divider()
        st.subheader("Trend")
        tab_spot, tab_gex, tab_pc, tab_iv, tab_hv = st.tabs(
            ["Spot", "GEX", "P/C Ratio", "IV30", "HV20"]
        )
        with tab_spot:
            st.line_chart(history.set_index("pull_date")["spot"])
        with tab_gex:
            st.line_chart(history.set_index("pull_date")["net_gex"])
        with tab_pc:
            st.line_chart(history.set_index("pull_date")["pc_ratio"])
        with tab_iv:
            st.line_chart(history.set_index("pull_date")["iv30"])
        with tab_hv:
            st.line_chart(history.set_index("pull_date")["hv20"])


if __name__ == "__main__":
    main()
