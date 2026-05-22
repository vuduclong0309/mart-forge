"""
mart-forge dashboard template.

Reads the ADS one-big-table from a local DuckDB file and renders
metric cards with optional fact-check links.

Customization points (search "TEMPLATE"):
  - DB_PATH: path to the DuckDB database produced by `dbt run`
  - ADS_TABLE: name of the ADS model
  - _LATEST_COLUMNS: explicit column list to fetch from the ADS table
  - METRIC_CARDS: list of dicts defining each card
  - DQC_SCORECARD: path to dqc_scorecard.json

Usage:
  streamlit run app.py
"""

import json
import pathlib

import duckdb
import streamlit as st

# ── TEMPLATE: paths ─────────────────────────────────────────────────
DB_PATH = pathlib.Path(__file__).parent.parent / "target" / "{{ db_file }}"
ADS_TABLE = "{{ mart_prefix }}_ads_{{ ads_name }}"
DQC_SCORECARD = pathlib.Path(__file__).parent.parent / "dqc_scorecard.json"

# ── TEMPLATE: metric cards ──────────────────────────────────────────
# Each card: { "label": display name, "column": SQL column in ADS,
#              "fmt": Python format string, "verify_url": external URL }
METRIC_CARDS: list[dict] = [
    # Example:
    # {"label": "Revenue", "column": "daily_revenue", "fmt": "${:,.2f}",
    #  "verify_url": "https://example.com/revenue-check"},
]

# ── TEMPLATE: columns to fetch from ADS table ─────────────────────
# Replace with the actual columns from your ADS model.
# Example: _LATEST_COLUMNS = "pull_date, spot, max_pain_strike, pc_ratio"
_LATEST_COLUMNS = "{{ ads_columns }}"

st.set_page_config(page_title="{{ mart_name }} Dashboard", layout="wide")


@st.cache_resource
def get_db():
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=300)
def load_latest():
    db = get_db()
    return db.sql(
        f"SELECT {_LATEST_COLUMNS} FROM {ADS_TABLE} ORDER BY pull_date DESC LIMIT 1"
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
    if any(s == "fail" for s in statuses):
        return ":red[DQC: FAIL]"
    if any(s == "unavailable" for s in statuses):
        return ":orange[DQC: PARTIAL]"
    if any(s in ("exhausted", "waived") for s in statuses):
        return ":orange[DQC: PASS WITH WAIVERS]"
    return ":green[DQC: PASS]"


def main():
    scorecard = load_dqc()
    st.title("{{ mart_name }}")
    st.markdown(dqc_badge(scorecard))

    df = load_latest()
    if df.empty:
        st.warning("No data. Run `dbt run` first.")
        return

    row = df.iloc[0]
    cols = st.columns(len(METRIC_CARDS) or 1)
    for i, card in enumerate(METRIC_CARDS):
        with cols[i]:
            val = row.get(card["column"])
            formatted = card["fmt"].format(val) if val is not None else "N/A"
            st.metric(card["label"], formatted)
            if card.get("verify_url"):
                st.caption(f"[Fact-check ↗]({card['verify_url']})")


if __name__ == "__main__":
    main()
