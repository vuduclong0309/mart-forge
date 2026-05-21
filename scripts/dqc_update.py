#!/usr/bin/env python3
"""Read dbt run_results.json and update dqc_scorecard.json with test outcomes."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CONTROL_CLASS_RULES = {
    "pk_integrity": {
        "singular": [],
        "generic_patterns": ["not_null_", "unique_"],
    },
    "fk_integrity": {
        "singular": [],
        "generic_patterns": ["relationships_"],
    },
    "freshness": {
        "singular": ["test_dqc_freshness"],
        "generic_patterns": ["not_null_.*pull_ts_utc"],
    },
    "completeness_volume": {
        "singular": ["test_dqc_completeness"],
        "generic_patterns": [],
    },
    "accepted_ranges": {
        "singular": ["test_dqc_accepted_ranges"],
        "generic_patterns": ["accepted_values_"],
    },
    "duplicate_detection": {
        "singular": ["test_dqc_duplicate_detection"],
        "generic_patterns": [],
    },
    "null_rate_threshold": {
        "singular": ["test_dqc_null_rate"],
        "generic_patterns": [],
    },
    "business_reconciliation": {
        "singular": ["test_dqc_reconciliation"],
        "generic_patterns": [],
    },
}


def classify_test(unique_id: str) -> str | None:
    """Map a dbt test unique_id to its DQC control class."""
    if not unique_id.startswith("test."):
        return None

    short = unique_id.split(".", 2)[-1] if unique_id.count(".") >= 2 else unique_id

    for cls, rules in CONTROL_CLASS_RULES.items():
        for pattern in rules["singular"]:
            if short == pattern or short.endswith(f".{pattern}"):
                return cls
        for pattern in rules["generic_patterns"]:
            if pattern.endswith("_") and pattern.rstrip("_") in short:
                return cls
            elif ".*" in pattern:
                prefix, suffix = pattern.split(".*", 1)
                if prefix in short and suffix in short:
                    return cls
    return None


def load_run_results(path: Path) -> tuple[dict, dict, str]:
    """Parse run_results.json -> (class -> [test_ids], class -> [failed_ids], generated_at)."""
    data = json.loads(path.read_text())
    generated_at = data["metadata"]["generated_at"]

    class_tests: dict[str, list[str]] = {cls: [] for cls in CONTROL_CLASS_RULES}
    class_failures: dict[str, list[str]] = {cls: [] for cls in CONTROL_CLASS_RULES}

    for result in data["results"]:
        uid = result["unique_id"]
        cls = classify_test(uid)
        if cls is None:
            continue
        class_tests[cls].append(uid)
        if result["status"] not in ("success", "pass", "warn"):
            class_failures[cls].append(uid)

    return class_tests, class_failures, generated_at


def update_scorecard(
    scorecard_path: Path,
    class_tests: dict[str, list[str]],
    class_failures: dict[str, list[str]],
    run_timestamp: str,
) -> dict:
    """Update scorecard with dbt test linkage and pass/fail status."""
    scorecard = json.loads(scorecard_path.read_text())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    scorecard["generated_at"] = now

    for control in scorecard["controls"]:
        cls = control["class"]
        linked = class_tests.get(cls, [])
        failures = class_failures.get(cls, [])

        control["linked_dbt_tests"] = sorted(linked)
        control["last_dbt_run"] = run_timestamp

        if "attempts" not in control:
            control["attempts"] = []

        if cls == "business_reconciliation" and control.get("status") == "exhausted":
            continue

        if failures:
            control["status"] = "fail"
        elif linked:
            control["status"] = "pass"
            control["verified_at"] = now

    return scorecard


def main():
    parser = argparse.ArgumentParser(description="Update DQC scorecard from dbt run results")
    parser.add_argument(
        "--run-results",
        default="target/run_results.json",
        help="Path to dbt run_results.json (default: target/run_results.json)",
    )
    parser.add_argument(
        "--scorecard",
        default="dqc_scorecard.json",
        help="Path to dqc_scorecard.json (default: dqc_scorecard.json)",
    )
    args = parser.parse_args()

    run_results_path = Path(args.run_results)
    scorecard_path = Path(args.scorecard)

    if not run_results_path.exists():
        print(f"ERROR: {run_results_path} not found. Run 'dbt test' first.", file=sys.stderr)
        sys.exit(1)
    if not scorecard_path.exists():
        print(f"ERROR: {scorecard_path} not found.", file=sys.stderr)
        sys.exit(1)

    class_tests, class_failures, run_timestamp = load_run_results(run_results_path)
    updated = update_scorecard(scorecard_path, class_tests, class_failures, run_timestamp)

    scorecard_path.write_text(json.dumps(updated, indent=2) + "\n")

    total = len(updated["controls"])
    passing = sum(1 for c in updated["controls"] if c["status"] in ("pass", "exhausted"))
    failing = sum(1 for c in updated["controls"] if c["status"] == "fail")

    print(f"DQC scorecard updated: {passing}/{total} controls passing", end="")
    if failing:
        print(f", {failing} FAILING", end="")
    print()

    sys.exit(1 if failing else 0)


if __name__ == "__main__":
    main()
