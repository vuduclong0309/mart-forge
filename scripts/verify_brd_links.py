#!/usr/bin/env python3
"""
BRD Section 2.7 link verification script.
Checks each candidate URL for correct asset (GME) and claimed metric visibility.
Outputs a JSON report that becomes the verification evidence appendix.
"""

import json
import time
from datetime import datetime, timezone

URLS_TO_CHECK = [
    {
        "card": "Spot Price",
        "metric": "spot",
        "url": "https://finance.yahoo.com/quote/GME/",
        "expect_asset": "GME",
        "expect_metric": "Price / quote",
    },
    {
        "card": "Max Pain / Max Pain Convergence",
        "metric": "max_pain_strike, max_pain_convergence_pct",
        "url": "https://swaggerstocks.com/options.php?ticker=GME",
        "expect_asset": "GME",
        "expect_metric": "Max Pain strike",
    },
    {
        "card": "Max Pain (alt)",
        "metric": "max_pain_strike",
        "url": "https://www.optionistics.com/quotes/stock-options/GME",
        "expect_asset": "GME",
        "expect_metric": "Max Pain",
    },
    {
        "card": "P/C Ratio, OI Daily Delta, Top OI Strikes",
        "metric": "pc_ratio, oi_daily_delta, top_oi_strike_1/2/3",
        "url": "https://www.barchart.com/stocks/quotes/GME/options",
        "expect_asset": "GME",
        "expect_metric": "Put/Call ratio, Open Interest",
    },
    {
        "card": "IV30, HV20, IV Rank, IV Percentile",
        "metric": "iv30, hv20, iv_rank, iv_percentile",
        "url": "https://marketchameleon.com/Overview/GME/IV/",
        "expect_asset": "GME",
        "expect_metric": "Implied Volatility, IV Rank, HV",
    },
    {
        "card": "IV Percentile (alt)",
        "metric": "iv_percentile",
        "url": "https://www.optionistics.com/quotes/stock-options/GME",
        "expect_asset": "GME",
        "expect_metric": "IV Percentile / IV Rank",
    },
    {
        "card": "Net GEX / Gamma Flip / Dealer Net Gamma (SqueezeMetrics — potential wrong-asset)",
        "metric": "net_gex, gamma_flip_point, dealer_net_gamma",
        "url": "https://squeezemetrics.com/monitor",
        "expect_asset": "GME",
        "expect_metric": "GEX for GME",
        "note": "SqueezeMetrics DIX tracks S&P 500 market-wide GEX, NOT individual stock GEX. Suspected wrong-asset link.",
    },
    {
        "card": "Social Mentions (alt — Reddit/ApeWisdom)",
        "metric": "social_mention_count",
        "url": "https://apewisdom.io/stocks/GME/",
        "expect_asset": "GME",
        "expect_metric": "Reddit mention count",
    },
    {
        "card": "Social Mentions (alt — Quiver Quant)",
        "metric": "social_mention_count",
        "url": "https://www.quiverquant.com/wallstreetbets/?ticker=GME",
        "expect_asset": "GME",
        "expect_metric": "WallStreetBets mention count, sentiment",
    },
]


def check_url(page, entry):
    """Check a single URL and return result dict."""
    url = entry["url"]
    result = {
        "card": entry["card"],
        "metric": entry["metric"],
        "url": url,
        "expect_asset": entry["expect_asset"],
        "expect_metric": entry["expect_metric"],
        "note": entry.get("note", ""),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "unverified",
        "http_ok": False,
        "page_title": "",
        "asset_visible": False,
        "metric_visible": False,
        "wrong_asset": False,
        "finding": "",
    }

    try:
        response = page.goto(url, timeout=20000, wait_until="domcontentloaded")
        result["http_ok"] = response is not None and response.status < 400

        # Get page title
        result["page_title"] = page.title()
        page_text = page.inner_text("body") if page.query_selector("body") else ""

        title_lower = result["page_title"].lower()
        text_lower = page_text[:5000].lower()

        # Check if GME appears anywhere on page
        result["asset_visible"] = "gme" in title_lower or "gamestop" in title_lower or \
                                   "gme" in text_lower or "gamestop" in text_lower

        # Check for wrong asset (SPY/SPX on a GME page)
        spy_mentioned = "spy" in title_lower or "/spy" in text_lower
        spx_mentioned = "s&p 500" in text_lower or "spx" in text_lower
        result["wrong_asset"] = (spy_mentioned or spx_mentioned) and not result["asset_visible"]

        # Check if metric is visible (rough text match)
        metric_keywords = {
            "spot": ["price", "quote", "last price"],
            "max_pain": ["max pain", "maximum pain"],
            "pc_ratio": ["put/call", "put call", "p/c ratio"],
            "iv30": ["implied volatility", "iv30", "iv rank"],
            "hv": ["historical volatility", "hv20", "realized vol"],
            "gex": ["gex", "gamma exposure", "gamma flip"],
            "mention": ["mention", "reddit", "wallstreet"],
            "sentiment": ["sentiment", "bullish", "bearish"],
        }
        for m_key, keywords in metric_keywords.items():
            if any(kw in text_lower for kw in keywords):
                result["metric_visible"] = True
                break

        # Build finding
        if not result["http_ok"]:
            result["status"] = "unverified"
            result["finding"] = f"HTTP error or timeout. Status: {response.status if response else 'timeout'}"
        elif result["wrong_asset"]:
            result["status"] = "wrong-asset"
            result["finding"] = f"Page shows SPY/S&P 500, not GME. Title: {result['page_title']}"
        elif not result["asset_visible"]:
            result["status"] = "unverified"
            result["finding"] = f"GME not visible on page. Title: {result['page_title']}"
        elif result["asset_visible"] and result["metric_visible"]:
            result["status"] = "exact"
            result["finding"] = f"GME and metric visible. Title: {result['page_title']}"
        else:
            result["status"] = "proxy"
            result["finding"] = f"GME visible but claimed metric not clearly found. Title: {result['page_title']}"

    except Exception as e:
        result["status"] = "unverified"
        result["finding"] = f"Error: {str(e)[:200]}"

    return result


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        return

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for entry in URLS_TO_CHECK:
            print(f"Checking: {entry['url']}")
            result = check_url(page, entry)
            results.append(result)
            print(f"  -> Status: {result['status']} | Finding: {result['finding'][:100]}")
            time.sleep(1)  # polite delay

        browser.close()

    # Write JSON report
    report = {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "tool": "playwright/chromium headless",
        "results": results,
    }

    output_path = "/Users/emberlockpc/Git/mart-forge/examples/gme-options-mart/brd_link_verification.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport written to: {output_path}")

    # Print summary
    print("\n=== SUMMARY ===")
    for r in results:
        print(f"[{r['status'].upper():12}] {r['card'][:50]:50} -> {r['url']}")


if __name__ == "__main__":
    main()
