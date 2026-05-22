"""
mart-forge dashboard template.

Reads the ADS one-big-table from a local DuckDB file and renders
metric cards with optional fact-check links.

Customization points (search "TEMPLATE"):
  - DB_PATH: path to the DuckDB database produced by `dbt run`
  - ADS_TABLE: name of the ADS model
  - METRIC_CARDS: list of dicts defining each card
  - DQC_SCORECARD: path to dqc_scorecard.json

Usage:
  streamlit run app.py [-- --columns col1,col2,...]
"""

import argparse
import json
import pathlib
import sys

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

# ── --columns override ─────────────────────────────────────────────
_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument(
    "--columns", default=None,
    help="Comma-separated column list to fetch instead of SELECT *",
)
_args, _ = _parser.parse_known_args(sys.argv[1:])
COLUMN_OVERRIDE: str | None = _args.columns

st.set_page_config(page_title="{{ mart_name }} Dashboard", layout="wide")


@st.cache_resource
def get_db():
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=300)
def load_latest():
    db = get_db()
    if COLUMN_OVERRIDE:
        cols = ", ".join(c.strip() for c in COLUMN_OVERRIDE.split(","))
    else:
        # SELECT * is intentional: ADS column sets vary per mart, so the
        # template cannot hard-code them.  Use --columns to restrict.
        cols = "*"
    return db.sql(
        f"SELECT {cols} FROM {ADS_TABLE} ORDER BY pull_date DESC LIMIT 1"
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
