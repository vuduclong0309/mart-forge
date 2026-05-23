#!/usr/bin/env python3
"""
Dashboard browser smoke test.

Starts the Streamlit dashboard, navigates with Playwright, and verifies
that key visualizations render nonblank.  Returns exit-code 0 on success.

Usage:
    pip install playwright && python -m playwright install chromium
    python smoke_test.py            # default: 8599
    python smoke_test.py --port 9000 --expect-source live

Requires:  playwright, streamlit, duckdb  (see requirements.txt + playwright)
The DuckDB warehouse must already exist (run ``dbt run --profiles-dir .``
in the mart directory first).
"""

import argparse
import contextlib
import re
import socket
import subprocess
import sys
import time

CHECKS_PASSED = 0
CHECKS_FAILED = 0


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _check(name: str, ok: bool, detail: str = ""):
    global CHECKS_PASSED, CHECKS_FAILED
    if ok:
        CHECKS_PASSED += 1
        print(f"  PASS  {name}")
    else:
        CHECKS_FAILED += 1
        msg = f"  FAIL  {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)


_LOCAL_URL_RE = re.compile(
    r'https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?',
    re.IGNORECASE,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--screenshot", default="smoke_screenshot.png")
    parser.add_argument("--timeout", type=int, default=30_000,
                        help="Page-load timeout in ms")
    parser.add_argument("--expect-source", choices=["fixture", "live", "any"],
                        default="fixture",
                        help="Expected source mode shown on the dashboard")
    args = parser.parse_args()

    port = args.port or _free_port()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed.  Run:")
        print("  pip install playwright && python -m playwright install chromium")
        sys.exit(2)

    app_py = str(__import__("pathlib").Path(__file__).with_name("app.py"))

    print(f"Starting Streamlit on port {port} ...")
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", app_py,
            "--server.port", str(port),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    url = f"http://localhost:{port}"

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 900})

            for attempt in range(20):
                try:
                    page.goto(url, timeout=5_000)
                    break
                except Exception:
                    time.sleep(1)
            else:
                print("ERROR: Streamlit did not start within 20 s")
                sys.exit(1)

            page.wait_for_load_state("networkidle", timeout=args.timeout)

            # Wait for actual dashboard content instead of relying on networkidle alone
            try:
                page.wait_for_selector(
                    "text=Market Summary", timeout=args.timeout, state="visible"
                )
            except Exception:
                pass  # check below will catch it

            try:
                page.wait_for_selector(
                    ".js-plotly-plot", timeout=args.timeout, state="visible"
                )
            except Exception:
                pass

            time.sleep(2)

            print("\nRunning checks …")

            title = page.title()
            _check("page-title", "GME" in title, f"got: {title!r}")

            body = page.text_content("body") or ""
            _check("has-title-text", "GME Options Dashboard" in body)
            _check("has-dqc-badge", "DQC:" in body)

            # Source mode check based on --expect-source
            if args.expect_source == "fixture":
                _check("has-fixture-warning",
                       "FIXTURE" in body or "DEMO" in body or "fixture" in body.lower(),
                       "fixture/demo banner expected")
            elif args.expect_source == "live":
                _check("has-live-banner",
                       "LIVE" in body or "DELAYED" in body,
                       "live/delayed data banner expected")
                _check("no-fixture-warning",
                       "FIXTURE" not in body and "DEMO MODE" not in body,
                       "fixture/demo banner should NOT appear in live mode")
            else:
                has_any = ("FIXTURE" in body or "DEMO" in body
                           or "LIVE" in body or "DELAYED" in body
                           or "unknown" in body.lower() or "stale" in body.lower())
                _check("has-source-indicator", has_any,
                       "expected some source mode indicator")

            _check("has-market-summary", "Market Summary" in body)
            _check("has-max-pain-section", "Max Pain" in body)
            _check("has-trend-section", "Trend Analysis" in body)
            _check("has-dqc-panel-label", "DQC Scorecard" in body or "Provenance" in body)
            _check("has-lineage", "gme_ads_market_dashboard" in body
                   or "Data Lineage" in body)

            plotly_charts = page.query_selector_all(".js-plotly-plot")
            _check("plotly-charts-rendered",
                   len(plotly_charts) >= 3,
                   f"found {len(plotly_charts)} plotly charts, expected >= 3")

            for idx, chart in enumerate(plotly_charts):
                box = chart.bounding_box()
                non_zero = box is not None and box["height"] > 50 and box["width"] > 100
                _check(f"chart-{idx}-nonblank", non_zero,
                       f"bbox={box}")

            # ── Source-link provenance guard ──────────────────────
            links = page.query_selector_all("a[href]")
            local_violations = []
            for link in links:
                href = link.get_attribute("href") or ""
                if _LOCAL_URL_RE.search(href):
                    text = (link.text_content() or "").strip()[:60]
                    if href != url and not href.startswith(url):
                        local_violations.append(f"{href} ({text})")
            _check("no-localhost-source-links",
                   len(local_violations) == 0,
                   f"found local URLs in source/fact-check links: {local_violations}")

            page.screenshot(path=args.screenshot, full_page=True)
            print(f"\nScreenshot saved to {args.screenshot}")

            browser.close()

    finally:
        proc.terminate()
        with contextlib.suppress(Exception):
            proc.wait(timeout=5)

    print(f"\n{'='*40}")
    print(f"  {CHECKS_PASSED} passed, {CHECKS_FAILED} failed")
    print(f"{'='*40}")
    sys.exit(1 if CHECKS_FAILED else 0)


if __name__ == "__main__":
    main()
