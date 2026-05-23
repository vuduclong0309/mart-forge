"""
GME Options Mart — Analytics Dashboard

Reads ADS/DWS/DWD outputs from the DuckDB warehouse produced by
``dbt run`` and renders interactive visualizations with DQC provenance
and BRD-verified fact-check links.

Educational Use Only / Not Financial Advice.
"""

import json
import os
import pathlib
import re

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml

# ── paths ──────────────────────────────────────────────────────────
BASE = pathlib.Path(__file__).parent.parent
DQC_SCORECARD = BASE / "dqc_scorecard.json"
BRD_VERIFICATION = BASE / "brd_link_verification.json"
DBT_PROJECT = BASE / "dbt_project.yml"

st.set_page_config(page_title="GME Options Dashboard", layout="wide")


# ── metric source classification ──────────────────────────────────

_METRIC_SOURCE = {
    "spot": "source_native",
    "max_pain_strike": "derived",
    "pc_ratio": "derived",
    "net_gex": "derived",
    "iv30": "derived",
    "hv20": "derived",
    "gamma_flip_point": "derived",
    "iv_rank": "derived",
    "iv_percentile": "derived",
    "oi_daily_delta": "derived",
    "dealer_net_gamma": "derived",
    "top_oi_strike_1": "derived",
    "top_oi_strike_2": "derived",
    "top_oi_strike_3": "derived",
    "social_mention_count": "unsupported",
    "social_sentiment_score": "unsupported",
}

_SOURCE_LABEL = {
    "source_native": "CBOE source",
    "derived": "model-derived",
    "comparator_only": "comparator",
    "unsupported": "fixture only",
}


# ── helpers ────────────────────────────────────────────────────────

def _resolve_db_path() -> str:
    try:
        if "db_path" in st.secrets:
            return st.secrets["db_path"]
    except Exception:
        pass
    env = os.environ.get("GME_DASHBOARD_DB_PATH")
    if env:
        return env
    return str(BASE / "target" / "gme_options.duckdb")


def _mask_connection_string(raw: str) -> str:
    masked = re.sub(r'(token=)[^&\s]+', r'\1***', raw, flags=re.IGNORECASE)
    masked = re.sub(r'(saas_mode=true&)[^&\s]*token[^&\s]*', r'\1token=***', masked, flags=re.IGNORECASE)
    return masked


@st.cache_data(ttl=300)
def _load_brd() -> dict:
    if not BRD_VERIFICATION.exists():
        return {}
    raw = json.loads(BRD_VERIFICATION.read_text())
    out: dict = {}
    for entry in raw.get("accepted", []):
        for m in entry["metric"].split("/"):
            out[m.strip()] = {
                "status": entry["status"],
                "url": entry["url"],
                "finding": entry.get("finding", ""),
            }
    for entry in raw.get("unsupported", []):
        out[entry["metric"]] = {
            "status": "unsupported",
            "url": None,
            "finding": entry.get("finding", ""),
        }
    for entry in raw.get("unverified", []):
        for m in entry["metric"].split(", "):
            m = m.strip()
            if m not in out:
                out[m] = {
                    "status": "unverified",
                    "url": entry.get("url"),
                    "finding": entry.get("finding", ""),
                }
    return out


_STATUS_ST_COLOR = {
    "exact": "green",
    "proxy": "orange",
    "comparator": "blue",
    "unsupported": "gray",
    "unverified": "red",
}


def _fact_caption(metric: str, brd: dict) -> str:
    parts = []
    source_type = _METRIC_SOURCE.get(metric)
    if source_type:
        label = _SOURCE_LABEL.get(source_type, source_type)
        if source_type == "derived":
            parts.append(f":blue[{label}]")
        elif source_type == "source_native":
            parts.append(f":green[{label}]")
        elif source_type == "unsupported":
            parts.append(f":gray[{label}]")

    info = brd.get(metric)
    if info:
        s = info["status"]
        color = _STATUS_ST_COLOR.get(s, "gray")
        url = info.get("url")
        if url:
            parts.append(f":{color}[{s}] [ref ↗]({url})")
        else:
            parts.append(f":{color}[{s}]")

    return " · ".join(parts)


# ── database ───────────────────────────────────────────────────────

@st.cache_resource
def _get_db():
    db_path = _resolve_db_path()
    return duckdb.connect(db_path, read_only=True)


# ── warehouse metadata ────────────────────────────────────────────

@st.cache_data(ttl=300)
def _load_warehouse_metadata() -> dict | None:
    try:
        df = _get_db().sql(
            "SELECT source_mode, primary_source_label, primary_source_url,"
            " data_as_of_date, warehouse_built_at_utc"
            " FROM gme_ads_warehouse_metadata LIMIT 1"
        ).fetchdf()
        if df.empty:
            return None
        row = df.iloc[0]
        return {
            "source_mode": row.get("source_mode"),
            "primary_source_label": row.get("primary_source_label"),
            "primary_source_url": row.get("primary_source_url"),
            "data_as_of_date": row.get("data_as_of_date"),
            "warehouse_built_at_utc": row.get("warehouse_built_at_utc"),
        }
    except Exception:
        return None


def _is_fixture_mode_from_yml() -> bool:
    if DBT_PROJECT.exists():
        try:
            cfg = yaml.safe_load(DBT_PROJECT.read_text())
            return bool(cfg.get("vars", {}).get("use_fixture", False))
        except Exception:
            pass
    return False


def _resolve_source_mode() -> tuple[str, str | None, str | None]:
    meta = _load_warehouse_metadata()
    if meta and meta.get("source_mode"):
        return (
            meta["source_mode"],
            meta.get("primary_source_label"),
            meta.get("primary_source_url"),
        )
    if _is_fixture_mode_from_yml():
        return "fixture", "Fixture / Illustrative Data (yml fallback)", None
    return "unknown", None, None


# ── data loaders ───────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_latest_ads() -> pd.DataFrame:
    return _get_db().sql(
        "SELECT * FROM gme_ads_market_dashboard"
        " ORDER BY pull_date DESC LIMIT 1"
    ).fetchdf()


@st.cache_data(ttl=300)
def load_history() -> pd.DataFrame:
    return _get_db().sql(
        "SELECT pull_date, spot, net_gex, pc_ratio, iv30, hv20"
        " FROM gme_ads_market_dashboard ORDER BY pull_date"
    ).fetchdf()


@st.cache_data(ttl=300)
def load_strike_gex() -> pd.DataFrame:
    return _get_db().sql(
        "SELECT strike, call_gex, put_gex, net_gex, total_oi, avg_iv, gex_rank"
        " FROM gme_dws_strike_gex_1d"
        " WHERE pull_date = (SELECT MAX(pull_date) FROM gme_dws_strike_gex_1d)"
        " ORDER BY strike"
    ).fetchdf()


@st.cache_data(ttl=300)
def load_oi_by_strike() -> pd.DataFrame:
    return _get_db().sql("""
        SELECT strike, option_type, SUM(open_interest) AS oi
        FROM gme_dwd_option_contract_di
        WHERE pull_date = (SELECT MAX(pull_date) FROM gme_dwd_option_contract_di)
          AND contract_class = 'standard'
        GROUP BY strike, option_type
        ORDER BY strike
    """).fetchdf()


@st.cache_data(ttl=300)
def load_max_pain_curve(expiry_filter=None) -> pd.DataFrame:
    expiry_clause = ""
    if expiry_filter is not None:
        expiry_clause = f"AND expiry = '{expiry_filter}'"
    return _get_db().sql(f"""
        WITH contracts AS (
            SELECT strike, option_type, open_interest
            FROM gme_dwd_option_contract_di
            WHERE pull_date = (SELECT MAX(pull_date) FROM gme_dwd_option_contract_di)
              AND contract_class = 'standard'
              {expiry_clause}
        ),
        candidates AS (
            SELECT DISTINCT strike AS candidate FROM contracts
        )
        SELECT
            c.candidate AS strike,
            SUM(CASE
                WHEN ct.option_type = 'call' AND ct.strike < c.candidate
                THEN (c.candidate - ct.strike) * ct.open_interest * 100
                WHEN ct.option_type = 'put'  AND ct.strike > c.candidate
                THEN (ct.strike - c.candidate) * ct.open_interest * 100
                ELSE 0
            END) AS total_pain
        FROM candidates c
        CROSS JOIN contracts ct
        GROUP BY c.candidate
        ORDER BY c.candidate
    """).fetchdf()


@st.cache_data(ttl=300)
def load_dqc() -> dict | None:
    if DQC_SCORECARD.exists():
        return json.loads(DQC_SCORECARD.read_text())
    return None


# ── DQC badge ──────────────────────────────────────────────────────

def _dqc_badge(scorecard: dict | None) -> str:
    if not scorecard:
        return ":gray[DQC: unknown]"
    statuses = [c["status"] for c in scorecard.get("controls", [])]
    if not statuses:
        return ":gray[DQC: UNKNOWN]"
    if any(s == "fail" for s in statuses):
        return ":red[DQC: FAIL]"
    if any(s in ("exhausted", "waived") for s in statuses):
        return ":orange[DQC: PASS WITH WAIVERS]"
    if any(s in ("unavailable", "pending") for s in statuses):
        return ":orange[DQC: PENDING]"
    if all(s == "pass" for s in statuses):
        return ":green[DQC: PASS]"
    return ":gray[DQC: UNKNOWN]"


# ── visualizations ─────────────────────────────────────────────────

def _render_metric_row(row: pd.Series, brd: dict):
    metrics = [
        ("Spot", "spot", "${:,.2f}"),
        ("Max Pain", "max_pain_strike", "${:,.0f}"),
        ("P/C Ratio", "pc_ratio", "{:.3f}"),
        ("Net GEX", "net_gex", "{:,.0f}"),
        ("IV30", "iv30", "{:.1%}"),
        ("HV20", "hv20", "{:.1%}"),
        ("Gamma Flip", "gamma_flip_point", "${:,.2f}"),
        ("IV Rank", "iv_rank", "{:.1%}"),
    ]
    cols = st.columns(len(metrics))
    for i, (label, col_name, fmt) in enumerate(metrics):
        with cols[i]:
            val = row.get(col_name)
            if pd.notna(val):
                formatted = fmt.format(val)
            else:
                formatted = "N/A"
            st.metric(label, formatted)
            cap = _fact_caption(col_name, brd)
            if cap:
                st.caption(cap)


def _render_gex_chart(df: pd.DataFrame, spot: float, gamma_flip):
    if df.empty:
        st.info("No strike GEX data available.")
        return

    colors = ["#28a745" if v >= 0 else "#dc3545" for v in df["net_gex"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["strike"], y=df["net_gex"],
        marker_color=colors, name="Net GEX",
        hovertemplate="Strike $%{x:,.0f}<br>Net GEX %{y:,.0f}<extra></extra>",
    ))
    fig.add_vline(x=spot, line_dash="dash", line_color="#007bff",
                  annotation_text=f"Spot ${spot:,.2f}")
    if pd.notna(gamma_flip):
        fig.add_vline(x=float(gamma_flip), line_dash="dot", line_color="#fd7e14",
                      annotation_text=f"Gamma Flip ${float(gamma_flip):,.2f}",
                      annotation_position="bottom right")
    fig.update_layout(
        title="Strike GEX Profile (model-derived from CBOE Greeks)",
        xaxis_title="Strike", yaxis_title="Net GEX",
        height=420, showlegend=False, margin=dict(t=40, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_oi_chart(df: pd.DataFrame, spot: float):
    if df.empty:
        st.info("No OI data available.")
        return

    calls = df[df["option_type"] == "call"].set_index("strike")["oi"]
    puts = df[df["option_type"] == "put"].set_index("strike")["oi"]
    all_strikes = sorted(df["strike"].unique())

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=all_strikes,
        y=[calls.get(s, 0) for s in all_strikes],
        name="Call OI", marker_color="#28a745",
    ))
    fig.add_trace(go.Bar(
        x=all_strikes,
        y=[puts.get(s, 0) for s in all_strikes],
        name="Put OI", marker_color="#dc3545",
    ))
    fig.add_vline(x=spot, line_dash="dash", line_color="#007bff",
                  annotation_text=f"Spot ${spot:,.2f}")
    fig.update_layout(
        title="Open Interest by Strike — standard contracts (CBOE source)",
        xaxis_title="Strike", yaxis_title="Open Interest",
        barmode="group", height=420, margin=dict(t=40, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_max_pain(df: pd.DataFrame, spot: float, max_pain, max_pain_expiry):
    if df.empty:
        st.info("No max-pain data available.")
        return

    expiry_label = ""
    if max_pain_expiry is not None and pd.notna(max_pain_expiry):
        expiry_label = f" — expiry {max_pain_expiry}"

    col_chart, col_table = st.columns([3, 1])

    with col_chart:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["strike"], y=df["total_pain"],
            mode="lines+markers", name="Total Pain",
            line=dict(color="#6f42c1"),
            hovertemplate="Strike $%{x:,.0f}<br>Pain $%{y:,.0f}<extra></extra>",
        ))
        fig.add_vline(x=spot, line_dash="dash", line_color="#007bff",
                      annotation_text=f"Spot ${spot:,.2f}")
        if pd.notna(max_pain):
            min_idx = df["total_pain"].idxmin()
            fig.add_annotation(
                x=df.loc[min_idx, "strike"],
                y=df.loc[min_idx, "total_pain"],
                text=f"Max Pain ${float(max_pain):,.0f}",
                showarrow=True, arrowhead=2, arrowcolor="#fd7e14",
                font=dict(color="#fd7e14", size=12),
            )
        fig.update_layout(
            title=f"Max Pain Curve — standard contracts{expiry_label} (model-derived)",
            xaxis_title="Strike", yaxis_title="Total Pain ($)",
            height=400, showlegend=False, margin=dict(t=40, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_table:
        st.markdown("**Top Strikes by Lowest Pain**")
        top = df.nsmallest(5, "total_pain")[["strike", "total_pain"]].copy()
        top.columns = ["Strike", "Pain ($)"]
        top["Strike"] = top["Strike"].map("${:,.0f}".format)
        top["Pain ($)"] = top["Pain ($)"].map("${:,.0f}".format)
        st.dataframe(top, use_container_width=True, hide_index=True)


def _render_iv_hv_trend(df: pd.DataFrame):
    if df.empty or len(df) < 2:
        st.info("IV/HV trend requires multi-day history (single fixture snapshot active).")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["pull_date"], y=df["iv30"],
        mode="lines+markers", name="IV30",
        line=dict(color="#007bff"),
    ))
    fig.add_trace(go.Scatter(
        x=df["pull_date"], y=df["hv20"],
        mode="lines+markers", name="HV20",
        line=dict(color="#fd7e14"),
    ))
    fig.update_layout(
        title="IV30 vs HV20 Trend (model-derived)",
        xaxis_title="Date", yaxis_title="Volatility",
        yaxis_tickformat=".0%", height=380,
        margin=dict(t=40, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_pc_trend(df: pd.DataFrame):
    if df.empty or len(df) < 2:
        st.info("P/C trend requires multi-day history (single fixture snapshot active).")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["pull_date"], y=df["pc_ratio"],
        mode="lines+markers", name="P/C Ratio",
        line=dict(color="#17a2b8"), fill="tozeroy",
    ))
    fig.add_hline(y=1.0, line_dash="dash", line_color="gray",
                  annotation_text="P/C = 1.0")
    fig.update_layout(
        title="Put/Call Ratio Trend (model-derived from CBOE OI)",
        xaxis_title="Date", yaxis_title="P/C Ratio",
        height=380, margin=dict(t=40, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_dqc_panel(scorecard: dict | None, brd: dict):
    with st.expander("DQC Scorecard & Data Provenance", expanded=False):
        if scorecard:
            st.markdown("#### Data Quality Controls")
            _DQC_ICON = {"pass": ":green[PASS]", "exhausted": ":orange[EXHAUSTED]",
                         "waived": ":orange[WAIVED]", "fail": ":red[FAIL]",
                         "pending": ":orange[PENDING]", "unavailable": ":gray[N/A]"}
            for c in scorecard.get("controls", []):
                badge = _DQC_ICON.get(c["status"], ":gray[?]")
                st.markdown(f"- **{c['class']}** {badge} &mdash; {c['description']}")
                if c.get("attempts"):
                    n_attempts = len(c["attempts"])
                    st.caption(f"  {n_attempts} reconciliation attempt(s) logged")
            st.caption(f"Scorecard generated: {scorecard.get('generated_at', 'unknown')}")
        else:
            st.warning("DQC scorecard not available.")

        st.markdown("---")
        st.markdown("#### Metric Source Classification")
        st.markdown(
            "| Type | Meaning |\n"
            "|---|---|\n"
            "| :green[source_native] | Value read directly from CBOE delayed quotes |\n"
            "| :blue[model-derived] | Computed by dbt models from CBOE inputs |\n"
            "| :orange[comparator] | External link for manual comparison only |\n"
            "| :gray[unsupported] | No live source; fixture data for CI |"
        )

        st.markdown("---")
        st.markdown("#### Fact-Check Reference Sources (BRD §2.7)")
        if brd:
            rows = []
            for metric, info in sorted(brd.items()):
                url = info.get("url") or "—"
                source_type = _METRIC_SOURCE.get(metric, "—")
                rows.append({
                    "Metric": metric,
                    "Source Type": source_type,
                    "Link Status": info["status"],
                    "Reference URL": url,
                    "Finding": (info.get("finding") or "")[:100],
                })
            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True, hide_index=True,
                column_config={
                    "Reference URL": st.column_config.LinkColumn("Reference URL"),
                },
            )
        else:
            st.info("BRD verification data not available.")

        st.markdown("---")
        st.markdown("#### Data Lineage")
        st.markdown(
            "| Visualization | Source Model | Layer | Metric Type |\n"
            "|---|---|---|---|\n"
            "| Market Summary (Spot) | `gme_ads_market_dashboard` | ADS | source_native |\n"
            "| Market Summary (others) | `gme_ads_market_dashboard` | ADS | model-derived |\n"
            "| Strike GEX Profile | `gme_dws_strike_gex_1d` | DWS | model-derived |\n"
            "| OI by Strike | `gme_dwd_option_contract_di` | DWD | source_native |\n"
            "| Max Pain Curve | `gme_dws_max_pain_by_expiry_1d` | DWS | model-derived |\n"
            "| IV/HV Trend | `gme_ads_market_dashboard` | ADS | model-derived |\n"
            "| P/C Ratio Trend | `gme_ads_market_dashboard` | ADS | model-derived |"
        )


# ── main ───────────────────────────────────────────────────────────

def main():
    scorecard = load_dqc()
    brd = _load_brd()
    source_mode, source_label, source_url = _resolve_source_mode()
    fixture_mode = source_mode == "fixture"

    st.title("GME Options Dashboard")
    st.markdown(
        f"{_dqc_badge(scorecard)} · "
        "Educational Use Only / Not Financial Advice"
    )

    if source_mode == "unknown":
        st.error(
            "**DATA SOURCE UNKNOWN** — The warehouse does not contain "
            "source-mode metadata (`gme_ads_warehouse_metadata` table missing "
            "or empty). This dashboard cannot confirm whether the data is "
            "fixture, live, or stale. Re-run `dbt run --profiles-dir .` to "
            "rebuild the warehouse with provenance metadata."
        )
    elif fixture_mode:
        st.warning(
            "**FIXTURE / DEMO MODE** — All values shown are derived from a "
            "static fixture snapshot (illustrative data, not live market prices). "
            "Set `use_fixture: false` in `dbt_project.yml` and re-run the "
            "pipeline for live delayed data from CBOE."
        )
    else:
        provider_link = ""
        if source_url:
            provider_link = f" Provider: [{source_label}]({source_url})."
        st.info(
            f"**LIVE DATA (DELAYED)** — Values are derived from {source_label}. "
            "Data may be 15+ minutes behind real-time. "
            "Not financial advice — verify independently before any decision."
            f"{provider_link}"
        )

    db_display = _mask_connection_string(_resolve_db_path())
    st.caption(f"Warehouse: `{db_display}`")

    df_latest = load_latest_ads()
    if df_latest.empty:
        st.warning("No data — run `dbt run --profiles-dir .` first.")
        return

    row = df_latest.iloc[0]
    data_date = row.get("pull_date", "N/A")

    meta = _load_warehouse_metadata()
    if meta and meta.get("warehouse_built_at_utc"):
        built = meta["warehouse_built_at_utc"]
        date_suffix = f" (built: {built})"
    else:
        date_suffix = ""

    if fixture_mode:
        mode_label = " (fixture snapshot — not current)"
    elif source_mode == "unknown":
        mode_label = " (source unknown — treat as stale)"
    else:
        mode_label = ""

    st.caption(f"Data as of: **{data_date}**{mode_label}{date_suffix}")

    # ── Market Summary ─────────────────────────────────────────
    st.subheader("Market Summary")
    _render_metric_row(row, brd)

    max_pain_expiry = row.get("max_pain_expiry")
    if max_pain_expiry is not None and pd.notna(max_pain_expiry):
        st.caption(
            f"Max pain shown for nearest standard expiry: **{max_pain_expiry}**. "
            "Per-expiry breakdown available in `gme_dws_max_pain_by_expiry_1d`."
        )

    # ── Strike-level Charts ────────────────────────────────────
    st.divider()
    spot = float(row.get("spot", 0))
    gamma_flip = row.get("gamma_flip_point")
    max_pain = row.get("max_pain_strike")

    col_gex, col_oi = st.columns(2)
    with col_gex:
        _render_gex_chart(load_strike_gex(), spot, gamma_flip)
    with col_oi:
        _render_oi_chart(load_oi_by_strike(), spot)

    # ── Max Pain ───────────────────────────────────────────────
    st.divider()
    st.subheader("Max Pain Analysis")
    expiry_for_curve = None
    if max_pain_expiry is not None and pd.notna(max_pain_expiry):
        expiry_for_curve = str(max_pain_expiry)
    _render_max_pain(load_max_pain_curve(expiry_for_curve), spot, max_pain, max_pain_expiry)

    # ── Trend Charts ───────────────────────────────────────────
    st.divider()
    st.subheader("Trend Analysis")
    history = load_history()
    col_iv, col_pc = st.columns(2)
    with col_iv:
        _render_iv_hv_trend(history)
    with col_pc:
        _render_pc_trend(history)

    # ── DQC & Provenance ───────────────────────────────────────
    st.divider()
    _render_dqc_panel(scorecard, brd)


if __name__ == "__main__":
    main()
