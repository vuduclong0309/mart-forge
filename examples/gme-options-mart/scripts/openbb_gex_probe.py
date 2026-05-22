#!/usr/bin/env python3
"""
OpenBB GEX Probe — attempts to fetch GME options chain data from each
available OpenBB provider and evaluates whether the returned fields are
sufficient to compute Gamma Exposure (GEX).

GEX formula (per contract):
    gamma * open_interest * 100 * spot^2 * 0.01 * sign(call=+1, put=-1)

Required fields: gamma, open_interest, underlying_price (spot).
Option type (call/put) is resolved via aliases: option_type, contract_type, type.

Usage (isolated venv via uv):
    uv venv /tmp/openbb-probe && source /tmp/openbb-probe/bin/activate
    uv pip install 'openbb>=4.5' openbb-tradier
    python scripts/openbb_gex_probe.py --pretty

Or via pip:
    pip install 'openbb>=4.5' openbb-tradier
    python scripts/openbb_gex_probe.py            # JSON to stdout
    python scripts/openbb_gex_probe.py --pretty    # human-readable
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

SYMBOL = "GME"
PROVIDERS = ["cboe", "yfinance", "intrinio", "tradier"]
GEX_REQUIRED_FIELDS = {"gamma", "open_interest", "underlying_price"}
OPTION_TYPE_ALIASES = ["option_type", "contract_type", "type"]


def _sanitize_exception(exc: Exception) -> str:
    return f"{type(exc).__name__}: {str(exc)[:300]}"


def _resolve_option_type_col(columns: set) -> str | None:
    for alias in OPTION_TYPE_ALIASES:
        matches = [c for c in columns if c.lower() == alias]
        if matches:
            return matches[0]
    return None


def probe_provider(obb, provider: str) -> dict:
    result = {
        "source": f"OpenBB obb.derivatives.options.chains('{SYMBOL}', provider='{provider}')",
        "provider": provider,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "command": f"obb.derivatives.options.chains('{SYMBOL}', provider='{provider}')",
    }

    if provider == "cboe":
        result.update(
            result="not_independent",
            reason="OpenBB cboe provider fetches from cdn.cboe.com — the same endpoint "
                   "as the primary ODS ingest. Cannot serve as independent reconciliation source.",
        )
        return result

    try:
        resp = obb.derivatives.options.chains(SYMBOL, provider=provider)
    except Exception as exc:
        msg = str(exc)
        if "credentials" in msg.lower() or "api_key" in msg.lower() or "unauthorized" in msg.lower():
            result.update(result="credentials_required", reason=msg[:300])
        elif "not available" in msg.lower() or "not supported" in msg.lower():
            result.update(result="not_available", reason=msg[:300])
        elif "not found" in msg.lower() or "no data" in msg.lower():
            result.update(result="no_data", reason=msg[:300])
        else:
            result.update(result="error", reason=msg[:300])
        result["exception"] = _sanitize_exception(exc)
        return result

    try:
        df = resp.to_df()
    except Exception:
        df = None

    if df is None or df.empty:
        result.update(result="no_data", reason="Provider returned empty result set")
        return result

    columns = set(df.columns.tolist())
    result["row_count"] = len(df)
    result["columns_returned"] = sorted(columns)

    missing = GEX_REQUIRED_FIELDS - columns
    option_type_col = _resolve_option_type_col(columns)

    if missing or option_type_col is None:
        missing_display = sorted(missing)
        if option_type_col is None:
            missing_display.append("option_type (or alias)")
        result.update(
            result="insufficient_fields",
            reason=f"Missing GEX-required fields: {missing_display}",
        )
        gamma_candidates = [c for c in columns if "gamma" in c.lower()]
        oi_candidates = [c for c in columns if "interest" in c.lower() or "oi" in c.lower()]
        spot_candidates = [c for c in columns if "underlying" in c.lower() or "spot" in c.lower()]
        type_candidates = [c for c in columns if "type" in c.lower()]
        result["field_hints"] = {
            "gamma_like": gamma_candidates,
            "oi_like": oi_candidates,
            "spot_like": spot_candidates,
            "type_like": type_candidates,
        }
        return result

    non_null_gamma = df["gamma"].notna().sum()
    non_null_oi = df["open_interest"].notna().sum()
    result["gamma_coverage"] = f"{non_null_gamma}/{len(df)}"
    result["oi_coverage"] = f"{non_null_oi}/{len(df)}"

    if non_null_gamma == 0:
        result.update(
            result="no_data",
            reason="gamma column exists but all values are null",
        )
        return result

    spot = df["underlying_price"].dropna().iloc[0] if df["underlying_price"].notna().any() else None
    if spot is None or spot <= 0:
        result.update(result="no_data", reason="underlying_price is null or non-positive")
        return result

    gex_df = df[df["gamma"].notna() & df["open_interest"].notna()].copy()
    sign = gex_df[option_type_col].apply(lambda t: 1 if str(t).lower() == "call" else -1)
    gex_df["gex"] = gex_df["gamma"] * gex_df["open_interest"] * 100 * (spot ** 2) * 0.01 * sign
    net_gex = float(gex_df["gex"].sum())

    result.update(
        result="pass",
        reason="GEX computable from OpenBB provider output",
        spot=float(spot),
        net_gex_openbb=net_gex,
        contracts_with_gamma=int(len(gex_df)),
    )
    return result


def main():
    parser = argparse.ArgumentParser(description="Probe OpenBB providers for GME GEX data")
    parser.add_argument("--pretty", action="store_true", help="Human-readable output")
    parser.add_argument("--providers", nargs="+", default=PROVIDERS, help="Providers to probe")
    args = parser.parse_args()

    try:
        from openbb import obb
    except ImportError:
        print(json.dumps({
            "error": "openbb not installed",
            "install": "pip install 'openbb>=4.5' openbb-tradier",
        }), file=sys.stderr)
        sys.exit(1)

    attempts = []
    for provider in args.providers:
        if args.pretty:
            print(f"Probing {provider}...", file=sys.stderr)
        attempts.append(probe_provider(obb, provider))

    output = {
        "probe_timestamp": datetime.now(timezone.utc).isoformat(),
        "openbb_packages": {
            "openbb": _pkg_version("openbb"),
            "openbb-derivatives": _pkg_version("openbb-derivatives"),
            "openbb-cboe": _pkg_version("openbb-cboe"),
            "openbb-yfinance": _pkg_version("openbb-yfinance"),
            "openbb-intrinio": _pkg_version("openbb-intrinio"),
            "openbb-tradier": _pkg_version("openbb-tradier"),
        },
        "symbol": SYMBOL,
        "gex_formula": "gamma * OI * 100 * spot^2 * 0.01 * sign(call=+1, put=-1)",
        "attempts": attempts,
    }

    indent = 2 if args.pretty else None
    print(json.dumps(output, indent=indent, default=str))


def _pkg_version(name: str) -> str:
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return "not installed"


if __name__ == "__main__":
    main()
