"""
mart-forge scaffold — Generate a dbt project from a signed BRD/TDD.

Enforces structural contract validation:
- BRD must have all mandatory sections (B-1..B-4) with metric catalog
- TDD must have all mandatory sections (T-1..T-17) with table coverage
- No unverified link_status at sign-off
- Explicit sign-off markers required
- Produces a complete dbt project skeleton with SQL models, DQC assets, and dashboard
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from mart_forge._resources import get_resource_root

SIGN_OFF_MARKERS = ["Grade: A", "Grade: B", "Sign-off:", "APPROVED", "Signed"]

BRD_REQUIRED_SECTIONS = ["B-1", "B-2", "B-3", "B-4"]
TDD_REQUIRED_SECTIONS = [f"T-{i}" for i in range(1, 18)]


def _is_signed(doc_path: Path) -> bool:
    if not doc_path.exists():
        return False
    content = doc_path.read_text()
    return any(marker in content for marker in SIGN_OFF_MARKERS)


def _validate_brd(brd_path: Path) -> list[str]:
    errors = []
    if not brd_path.exists():
        return ["BRD not found. Create a BRD before scaffolding (Phase A gate)."]

    content = brd_path.read_text()

    if not _is_signed(brd_path):
        errors.append("BRD exists but is not signed off. Get BRD approval before proceeding.")

    for section in BRD_REQUIRED_SECTIONS:
        if f"## {section}" not in content and f"# {section}" not in content:
            if section not in content:
                errors.append(f"BRD missing mandatory section {section}.")

    if "source_type" not in content and ("native" not in content or "derived" not in content):
        errors.append("BRD missing metric source_type classification (native/derived/hybrid).")

    if "link_status" not in content and not any(
        s in content for s in ["exact", "proxy", "unsupported"]
    ):
        errors.append("BRD missing link_status classification (exact/proxy/unsupported).")

    if "unverified" in content.lower():
        errors.append("BRD contains 'unverified' link_status — all links must be resolved before sign-off.")

    return errors


def _validate_tdd(tdd_path: Path) -> list[str]:
    errors = []
    if not tdd_path.exists():
        return ["TDD not found. Create a TDD before scaffolding (Phase B gate)."]

    content = tdd_path.read_text()

    if not _is_signed(tdd_path):
        errors.append("TDD exists but is not signed off. Get TDD approval before proceeding.")

    for section in TDD_REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"TDD missing mandatory section {section}.")

    table_sections = {"T-7": "ODS", "T-8": "DIM", "T-9": "DWD", "T-10": "DWS", "T-11": "ADS"}
    has_any_table = False
    for label, layer in table_sections.items():
        start = content.find(f"## {label}")
        if start < 0:
            start = content.find(label)
        if start < 0:
            continue

        next_num = int(label.split("-")[1]) + 1
        end = content.find(f"## T-{next_num}")
        if end < 0:
            end = content.find(f"T-{next_num}")
        if end < 0 or end <= start:
            end = len(content)

        section_text = content[start:end]

        has_column_spec = "column_name" in section_text
        is_na_only = not has_column_spec and (
            "not_applicable" in section_text.lower() or "n/a" in section_text.lower()
        )
        if is_na_only:
            continue

        has_any_table = True
        required_fields = ["column_name", "data_type"]
        for field in required_fields:
            if field not in section_text:
                errors.append(f"TDD {label} ({layer}) missing required field: {field}")

    if not has_any_table:
        errors.append("TDD has no table sections with column specifications — at least one layer required.")

    if "unverified" in content.lower():
        errors.append("TDD contains 'unverified' — all verifications must be resolved before sign-off.")

    return errors


def _check_gates(mart_dir: Path) -> list[str]:
    errors = []
    errors.extend(_validate_brd(mart_dir / "brd.md"))
    errors.extend(_validate_tdd(mart_dir / "tdd.md"))
    return errors


def scaffold(mart_dir: Path, mart_name: str, prefix: str) -> dict:
    """Generate a dbt project skeleton in mart_dir."""
    gate_errors = _check_gates(mart_dir)
    if gate_errors:
        return {"success": False, "errors": gate_errors, "files_created": []}

    resource_root = get_resource_root()
    templates_dir = resource_root / "templates"
    scripts_dir = resource_root / "scripts"
    files_created = []

    # dbt_project.yml
    dbt_project = mart_dir / "dbt_project.yml"
    dbt_project.write_text(
        f"name: '{mart_name}'\n"
        f"version: '1.0.0'\n"
        f"config-version: 2\n"
        f"profile: '{mart_name}'\n"
        f"\n"
        f"model-paths: ['models']\n"
        f"seed-paths: ['seeds']\n"
        f"test-paths: ['tests']\n"
        f"analysis-paths: ['analyses']\n"
        f"macro-paths: ['macros']\n"
        f"\n"
        f"clean-targets: ['target', 'dbt_packages']\n"
    )
    files_created.append("dbt_project.yml")

    # profiles.yml
    profiles = mart_dir / "profiles.yml"
    profiles.write_text(
        f"{mart_name}:\n"
        f"  target: dev\n"
        f"  outputs:\n"
        f"    dev:\n"
        f"      type: duckdb\n"
        f"      path: '{mart_name}.duckdb'\n"
        f"    ci:\n"
        f"      type: duckdb\n"
        f"      path: ':memory:'\n"
    )
    files_created.append("profiles.yml")

    # Model SQL files from templates
    for layer in ["ods", "dim", "dwd", "dws", "ads"]:
        layer_dir = mart_dir / "models" / layer
        layer_dir.mkdir(parents=True, exist_ok=True)
        template_sql = templates_dir / "models" / layer / "template.sql"
        if template_sql.exists():
            target_name = f"{prefix}_{layer}_template.sql"
            shutil.copy2(template_sql, layer_dir / target_name)
            files_created.append(f"models/{layer}/{target_name}")

    # Seeds directory
    seeds_dir = mart_dir / "seeds"
    seeds_dir.mkdir(exist_ok=True)
    dim_date_src = templates_dir / "seeds" / "dim_date.csv"
    if dim_date_src.exists():
        shutil.copy2(dim_date_src, seeds_dir / "dim_date.csv")
        files_created.append("seeds/dim_date.csv")

    # Tests directory with singular test template
    tests_dir = mart_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    singular_src = templates_dir / "tests" / "template_singular.sql"
    if singular_src.exists():
        shutil.copy2(singular_src, tests_dir / "template_singular.sql")
        files_created.append("tests/template_singular.sql")

    # schema.yml skeleton
    schema = mart_dir / "models" / "schema.yml"
    schema.write_text(
        f"version: 2\n"
        f"\n"
        f"models:\n"
        f"  - name: {prefix}_dim_date\n"
        f"    description: 'Date dimension (seed-backed)'\n"
        f"    columns:\n"
        f"      - name: date_sk\n"
        f"        tests:\n"
        f"          - not_null\n"
        f"          - unique\n"
        f"\n"
        f"seeds:\n"
        f"  - name: dim_date\n"
        f"    description: 'Calendar seed with business day flags'\n"
    )
    files_created.append("models/schema.yml")

    # Dashboard — copy template and substitute mart_name
    dash_dir = mart_dir / "dashboard"
    dash_dir.mkdir(exist_ok=True)
    dash_template = templates_dir / "dashboard" / "app.py"
    if dash_template.exists():
        dash_content = dash_template.read_text()
        dash_content = dash_content.replace("{mart_name}", mart_name)
        (dash_dir / "app.py").write_text(dash_content)
    else:
        (dash_dir / "app.py").write_text(_generate_dashboard_fallback(mart_name))
    files_created.append("dashboard/app.py")

    dash_reqs_src = templates_dir / "dashboard" / "requirements.txt"
    if dash_reqs_src.exists():
        shutil.copy2(dash_reqs_src, dash_dir / "requirements.txt")
    else:
        (dash_dir / "requirements.txt").write_text("streamlit>=1.30\nduckdb>=0.10\n")
    files_created.append("dashboard/requirements.txt")

    # DQC scorecard template
    scorecard = mart_dir / "dqc_scorecard.json"
    scorecard.write_text(json.dumps({
        "mart": mart_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "controls": [],
    }, indent=2))
    files_created.append("dqc_scorecard.json")

    # DQC update script (Finding #4 — pipeline references this)
    mart_scripts_dir = mart_dir / "scripts"
    mart_scripts_dir.mkdir(exist_ok=True)
    dqc_script_src = scripts_dir / "dqc_update.py"
    if dqc_script_src.exists():
        shutil.copy2(dqc_script_src, mart_scripts_dir / "dqc_update.py")
    else:
        (mart_scripts_dir / "dqc_update.py").write_text(
            '"""DQC scorecard update — generated by mart-forge scaffold."""\n'
            'print("Run mart-forge dqc-update or install mart-forge for full functionality.")\n'
        )
    files_created.append("scripts/dqc_update.py")

    # CI pipeline
    ci_dir = mart_dir / ".github" / "workflows"
    ci_dir.mkdir(parents=True, exist_ok=True)
    pipeline_src = templates_dir / "pipeline" / "daily.yml.template"
    if pipeline_src.exists():
        content = pipeline_src.read_text()
        content = content.replace("{Mart Name}", mart_name)
        content = content.replace("{cron_expression}", "0 6 * * *")
        (ci_dir / "daily.yml").write_text(content)
        files_created.append(".github/workflows/daily.yml")

    return {"success": True, "errors": [], "files_created": files_created}


def _generate_dashboard_fallback(mart_name: str) -> str:
    return (
        f'"""{mart_name} Dashboard — Generated by mart-forge scaffold."""\n\n'
        f'import streamlit as st\n\n'
        f'st.set_page_config(page_title="{mart_name} Dashboard", layout="wide")\n'
        f'st.title("{mart_name} Dashboard")\n'
        f'st.header("Data Quality")\n'
        f'st.info("Run `dbt test` then `dqc-update` to populate the scorecard.")\n'
        f'st.header("Metrics")\n'
        f'st.info("Metric cards generated from TDD dashboard specification.")\n'
        f'st.header("Data Provenance")\n'
        f'st.markdown("| Field | Description |\\n'
        f'|-------|------------|\\n'
        f'| provider | Data source identifier |\\n'
        f'| pull_ts_utc | When ingestion ran |")\n'
    )
