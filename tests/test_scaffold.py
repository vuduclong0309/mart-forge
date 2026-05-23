"""Scaffold workflow tests.

Tests structural contract validation (not just approval-token presence),
rejection of incomplete BRD/TDD, and generation of a complete dbt skeleton
with SQL models, DQC assets, dashboard, and pipeline scripts.
"""

import json
from pathlib import Path

import pytest

from mart_forge.scaffold import scaffold, _is_signed, _validate_brd, _validate_tdd


VALID_BRD = """\
# Business Requirements — Test Mart

## B-1. Scope

This mart covers order processing for the generic test domain.

## B-2. Business Questions

| ID | Question | Priority |
|----|----------|----------|
| Q-1 | What is total daily revenue? | High |

## B-3. Metric Catalog

| Metric | source_type | link_status | Definition |
|--------|-------------|-------------|------------|
| M-1 Revenue | native | exact | Sum of order amounts from source |
| M-2 Margin | derived | proxy | Revenue minus cost, advisory comparison only |

## B-4. Source–Link Evidence

| Metric | Source | Link | Evidence |
|--------|--------|------|----------|
| M-1 | orders.csv | exact | Field mapping: amount -> revenue |
| M-2 | calculated | proxy | Derived from M-1 minus costs |

Sign-off: APPROVED
Grade: A
"""

VALID_TDD = """\
# Technical Design Document — Test Mart

## T-1. Version History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-01 | Test | Initial |

## T-2. Design Reasoning
Grain: one row per order line per day.

## T-3. Source Systems
CSV file ingestion.

## T-4. Data Flow
ODS -> DIM -> DWD -> DWS -> ADS

## T-5. Source Mapping
| source_column | target_column |
|---------------|---------------|
| order_id | order_id |

## T-6. ODS Contract
| Property | Value |
|----------|-------|
| Grain | One row per order line per pull_date |
| Logical Partition | pull_date |
| Incremental Strategy | delete+insert |
| Unique Key | order_id, pull_date |
| Backfill | Full reload per partition |
| Restatement | Re-pull same partition date |
| Provenance | provider, pull_ts_utc, quote_ts_utc, run_id |
| Idempotence | Re-running same partition produces identical output |

## T-7. ODS Table Design

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|------------|---------------|-------------|-------------|
| order_id | varchar | Order identifier | ORD-001 | not_applicable — direct field | orders.csv |
| amount | decimal | Order amount | 99.50 | not_applicable — direct field | orders.csv |

## T-8. DIM Table Design

| column_name | data_type | definition | example_value | calculation | data_source | source_type |
|-------------|-----------|------------|---------------|-------------|-------------|-------------|
| customer_sk | integer | Surrogate key | 1 | md5(customer_id) | derived | derived |
| customer_id | varchar | Natural key | CUST-001 | not_applicable — direct field | orders.csv | native |

Provenance columns: provider, pull_ts_utc, run_id

## T-9. DWD Table Design

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|------------|---------------|-------------|-------------|
| order_line_sk | varchar | Surrogate key | abc123 | md5(order_id, line_id) | derived |
| revenue | decimal | Line revenue | 50.00 | not_applicable — direct field | ods |

## T-10. DWS Table Design

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|------------|---------------|-------------|-------------|
| date_sk | integer | Date key | 20260101 | not_applicable — FK to dim_date | dim_date |
| daily_revenue | decimal | Total revenue | 1000.00 | sum(revenue) | dwd |

## T-11. ADS Table Design

| column_name | data_type | definition | example_value | calculation | data_source | BRD_ref | link_status |
|-------------|-----------|------------|---------------|-------------|-------------|---------|-------------|
| total_revenue | decimal | Dashboard revenue | 5000.00 | sum(daily_revenue) | dws | M-1 | exact |
| margin_pct | decimal | Margin percentage | 0.15 | not_applicable — placeholder | dws | M-2 | proxy |

## T-12. DQC Control Matrix
All 8 control classes addressed.

## T-13. Naming Conventions
Per mart-forge naming standard.

## T-14. Incremental Strategy
delete+insert on ODS/DWD layers.

## T-15. Pipeline Schedule
Daily at 06:00 UTC.

## T-16. Dashboard Specification
Sections: DQC scorecard, metric cards, trend chart, provenance.

## T-17. Sign-off Checklist
All items verified.

Sign-off: APPROVED
Grade: A
"""


@pytest.fixture
def mart_dir(tmp_path):
    return tmp_path / "test_mart"


@pytest.fixture
def signed_mart(mart_dir):
    mart_dir.mkdir()
    (mart_dir / "brd.md").write_text(VALID_BRD)
    (mart_dir / "tdd.md").write_text(VALID_TDD)
    return mart_dir


class TestPlaceholderRejection:
    """Minimal approval-token documents must be rejected."""

    def test_rejects_token_only_brd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(
            "# BRD\n\nSign-off: APPROVED\nGrade: A\n"
        )
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted a token-only BRD"
        assert any("B-" in e for e in result["errors"])

    def test_rejects_token_only_tdd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(
            "# TDD\n\nSign-off: APPROVED\nGrade: A\n"
        )
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted a token-only TDD"
        assert any("T-" in e for e in result["errors"])

    def test_rejects_partial_brd_missing_sections(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(
            "# BRD\n\n## B-1 Scope\nSome scope.\n\nSign-off: APPROVED\n"
        )
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted BRD missing B-2..B-4"

    def test_rejects_brd_with_unverified(self, mart_dir):
        mart_dir.mkdir()
        brd_with_unverified = VALID_BRD.replace("exact", "unverified")
        (mart_dir / "brd.md").write_text(brd_with_unverified)
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted BRD with unverified link_status"
        assert any("unverified" in e.lower() for e in result["errors"])

    def test_rejects_tdd_with_unverified(self, mart_dir):
        mart_dir.mkdir()
        tdd_with_unverified = VALID_TDD.replace("exact", "unverified")
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text(tdd_with_unverified)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted TDD with unverified"

    def test_rejects_brd_missing_source_type(self, mart_dir):
        mart_dir.mkdir()
        brd_no_source = (
            VALID_BRD
            .replace("source_type", "category")
            .replace("native", "field")
            .replace("derived", "field")
        )
        (mart_dir / "brd.md").write_text(brd_no_source)
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"], "Scaffold accepted BRD without source_type classification"


class TestHardGateRejection:
    def test_rejects_missing_brd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert any("BRD not found" in e for e in result["errors"])

    def test_rejects_unsigned_brd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text("# Draft BRD\nNo sign-off yet.\n")
        (mart_dir / "tdd.md").write_text(VALID_TDD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert any("not signed off" in e for e in result["errors"])

    def test_rejects_missing_tdd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert any("TDD not found" in e for e in result["errors"])

    def test_rejects_unsigned_tdd(self, mart_dir):
        mart_dir.mkdir()
        (mart_dir / "brd.md").write_text(VALID_BRD)
        (mart_dir / "tdd.md").write_text("# Draft TDD\nNo sign-off yet.\n")
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert any("not signed off" in e for e in result["errors"])

    def test_rejects_both_missing(self, mart_dir):
        mart_dir.mkdir()
        result = scaffold(mart_dir, "test-mart", "tst")
        assert not result["success"]
        assert len(result["errors"]) >= 2

    def test_no_files_created_on_rejection(self, mart_dir):
        mart_dir.mkdir()
        result = scaffold(mart_dir, "test-mart", "tst")
        assert result["files_created"] == []


class TestSuccessfulScaffold:
    def test_scaffold_succeeds(self, signed_mart):
        result = scaffold(signed_mart, "test-mart", "tst")
        assert result["success"], f"Scaffold failed: {result['errors']}"
        assert result["errors"] == []
        assert len(result["files_created"]) > 0

    def test_dbt_project_yml_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        dbt_project = signed_mart / "dbt_project.yml"
        assert dbt_project.exists()
        content = dbt_project.read_text()
        assert "test-mart" in content
        assert "model-paths" in content

    def test_profiles_yml_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        profiles = signed_mart / "profiles.yml"
        assert profiles.exists()
        content = profiles.read_text()
        assert "test-mart" in content
        assert "duckdb" in content

    def test_model_sql_files_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        for layer in ["ods", "dim", "dwd", "dws", "ads"]:
            layer_dir = signed_mart / "models" / layer
            assert layer_dir.is_dir(), f"Missing model directory: {layer}"
            sql_files = list(layer_dir.glob("*.sql"))
            assert len(sql_files) > 0, f"No SQL files in models/{layer}/"

    def test_model_sql_no_select_star(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        for layer in ["ods", "dim", "dwd", "dws", "ads"]:
            for sql_file in (signed_mart / "models" / layer).glob("*.sql"):
                content = sql_file.read_text()
                in_comment = False
                for line in content.splitlines():
                    stripped = line.strip()
                    if "{#" in stripped:
                        in_comment = True
                    if in_comment:
                        if "#}" in stripped:
                            in_comment = False
                        continue
                    if stripped.startswith("--") or stripped.startswith("{"):
                        continue
                    assert "select *" not in stripped.lower(), \
                        f"{sql_file.name} uses SELECT *: {stripped}"

    def test_schema_yml_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        schema = signed_mart / "models" / "schema.yml"
        assert schema.exists()
        content = schema.read_text()
        assert "tst_dim_date" in content

    def test_dashboard_created_with_visualization(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        app = signed_mart / "dashboard" / "app.py"
        assert app.exists()
        content = app.read_text()
        assert "test-mart" in content
        assert "streamlit" in content
        assert "st.header" in content or "st.title" in content
        assert "scorecard" in content.lower() or "quality" in content.lower()
        assert "provenance" in content.lower()

    def test_scorecard_json_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        scorecard = signed_mart / "dqc_scorecard.json"
        assert scorecard.exists()
        data = json.loads(scorecard.read_text())
        assert data["mart"] == "test-mart"
        assert isinstance(data["controls"], list)

    def test_dqc_update_script_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        dqc_script = signed_mart / "scripts" / "dqc_update.py"
        assert dqc_script.exists(), "Scaffold did not generate scripts/dqc_update.py"
        content = dqc_script.read_text()
        assert "scorecard" in content.lower()

    def test_pipeline_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        pipeline = signed_mart / ".github" / "workflows" / "daily.yml"
        assert pipeline.exists()
        content = pipeline.read_text()
        assert "test-mart" in content

    def test_pipeline_dqc_script_exists(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        pipeline = signed_mart / ".github" / "workflows" / "daily.yml"
        content = pipeline.read_text()
        if "scripts/dqc_update.py" in content:
            assert (signed_mart / "scripts" / "dqc_update.py").exists(), \
                "Pipeline references scripts/dqc_update.py but it was not generated"

    def test_seeds_created(self, signed_mart):
        scaffold(signed_mart, "test-mart", "tst")
        assert (signed_mart / "seeds").is_dir()


class TestSignOffDetection:
    def test_grade_a_is_signed(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\nGrade: A\n")
        assert _is_signed(doc)

    def test_approved_is_signed(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\nAPPROVED by reviewer.\n")
        assert _is_signed(doc)

    def test_unsigned_doc(self, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Doc\nDraft version, not approved.\n")
        assert not _is_signed(doc)

    def test_missing_doc_not_signed(self, tmp_path):
        assert not _is_signed(tmp_path / "nonexistent.md")
