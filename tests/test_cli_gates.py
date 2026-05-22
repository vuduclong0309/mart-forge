"""Integration tests for BRD/TDD phase gates in the mart-forge CLI."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from mart_forge.cli import main


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def project_dir(tmp_path, runner):
    """Run `mart-forge init` inside a temp dir and return the project path."""
    os.chdir(tmp_path)
    result = runner.invoke(main, ["init", "mymart"])
    assert result.exit_code == 0, result.output
    proj = tmp_path / "mymart"
    os.chdir(proj)
    return proj


APPROVED_BRD_SIGNOFF = textwrap.dedent("""\
    ## 7. Sign-Off

    | Role | Name | Date | Status |
    |------|------|------|--------|
    | Operator (data owner) | Alice | 2026-01-01 | approved |
    | Consumer (primary user) | Bob | 2026-01-01 | approved |
""")

PENDING_BRD_SIGNOFF = textwrap.dedent("""\
    ## 7. Sign-Off

    | Role | Name | Date | Status |
    |------|------|------|--------|
    | Operator (data owner) | Alice | 2026-01-01 | pending |
    | Consumer (primary user) | Bob | 2026-01-01 | pending |
""")

APPROVED_TDD_SIGNOFF = textwrap.dedent("""\
    ## Sign-Off

    | Role | Name | Date | Status |
    |------|------|------|--------|
    | Tech lead / designer | Charlie | 2026-01-01 | approved |
    | Reviewer | Dana | 2026-01-01 | approved |
""")

BRD_MISSING_CONSUMER = textwrap.dedent("""\
    ## 7. Sign-Off

    | Role | Name | Date | Status |
    |------|------|------|--------|
    | Operator (data owner) | Alice | 2026-01-01 | approved |
""")

TDD_MISSING_REVIEWER = textwrap.dedent("""\
    ## Sign-Off

    | Role | Name | Date | Status |
    |------|------|------|--------|
    | Tech lead / designer | Charlie | 2026-01-01 | approved |
""")

BRD_DUPLICATE_OPERATOR = textwrap.dedent("""\
    ## 7. Sign-Off

    | Role | Name | Date | Status |
    |------|------|------|--------|
    | Operator (data owner) | Alice | 2026-01-01 | approved |
    | Operator (data owner) | Eve | 2026-01-02 | approved |
    | Consumer (primary user) | Bob | 2026-01-01 | approved |
""")

BRD_PARTIAL_APPROVAL = textwrap.dedent("""\
    ## 7. Sign-Off

    | Role | Name | Date | Status |
    |------|------|------|--------|
    | Operator (data owner) | Alice | 2026-01-01 | approved |
    | Consumer (primary user) | Bob | 2026-01-01 | pending |
""")

PENDING_TDD_SIGNOFF = textwrap.dedent("""\
    ## Sign-Off

    | Role | Name | Date | Status |
    |------|------|------|--------|
    | Tech lead / designer | Charlie | 2026-01-01 | pending |
    | Reviewer | Dana | 2026-01-01 | pending |
""")


# ── init creates BRD with pending sign-off ─────────────────────────────────

class TestInitCreatesBRD:
    def test_init_creates_business_requirements(self, project_dir: Path):
        brd = project_dir / "business-requirements.md"
        assert brd.exists(), "init must create business-requirements.md"

    def test_init_brd_has_pending_signoff(self, project_dir: Path):
        brd = project_dir / "business-requirements.md"
        content = brd.read_text()
        assert "| pending |" in content, (
            "BRD sign-off rows must default to 'pending'"
        )

    def test_init_message_says_fill_brd(self, tmp_path, runner):
        os.chdir(tmp_path)
        result = runner.invoke(main, ["init", "testmart"])
        assert "Fill business-requirements.md and get operator sign-off" in result.output
        assert "mart-forge scaffold" not in result.output, (
            "init must not suggest running scaffold directly"
        )


# ── scaffold without BRD ────────────────────────────────────────────────────

class TestScaffoldGateBRD:
    def test_scaffold_fails_when_brd_missing(self, project_dir: Path, runner):
        (project_dir / "business-requirements.md").unlink()
        result = runner.invoke(main, ["scaffold", "--domain", "test"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_scaffold_fails_when_brd_unapproved(self, project_dir: Path, runner):
        brd = project_dir / "business-requirements.md"
        brd.write_text(PENDING_BRD_SIGNOFF)
        result = runner.invoke(main, ["scaffold", "--domain", "test"])
        assert result.exit_code != 0
        assert "unapproved sign-off" in result.output

    def test_scaffold_fails_when_brd_has_no_signoff_rows(self, project_dir: Path, runner):
        brd = project_dir / "business-requirements.md"
        brd.write_text("# BRD\n\nNo sign-off section at all.\n")
        result = runner.invoke(main, ["scaffold", "--domain", "test"])
        assert result.exit_code != 0
        assert "no sign-off rows" in result.output


# ── scaffold without TDD ────────────────────────────────────────────────────

class TestScaffoldGateTDD:
    def test_scaffold_fails_when_tdd_missing(self, project_dir: Path, runner):
        brd = project_dir / "business-requirements.md"
        brd.write_text(APPROVED_BRD_SIGNOFF)
        result = runner.invoke(main, ["scaffold", "--domain", "test"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_scaffold_fails_when_tdd_unapproved(self, project_dir: Path, runner):
        brd = project_dir / "business-requirements.md"
        brd.write_text(APPROVED_BRD_SIGNOFF)
        tdd = project_dir / "tech-design-doc.md"
        tdd.write_text(PENDING_TDD_SIGNOFF)
        result = runner.invoke(main, ["scaffold", "--domain", "test"])
        assert result.exit_code != 0
        assert "unapproved sign-off" in result.output

    def test_scaffold_fails_when_tdd_has_no_signoff_rows(self, project_dir: Path, runner):
        brd = project_dir / "business-requirements.md"
        brd.write_text(APPROVED_BRD_SIGNOFF)
        tdd = project_dir / "tech-design-doc.md"
        tdd.write_text("# TDD\n\nNo sign-off section at all.\n")
        result = runner.invoke(main, ["scaffold", "--domain", "test"])
        assert result.exit_code != 0
        assert "no sign-off rows" in result.output


# ── scaffold succeeds only with both approved ───────────────────────────────

class TestScaffoldHappyPath:
    def test_scaffold_succeeds_with_approved_brd_and_tdd(
        self, project_dir: Path, runner
    ):
        brd = project_dir / "business-requirements.md"
        brd.write_text(APPROVED_BRD_SIGNOFF)
        tdd = project_dir / "tech-design-doc.md"
        tdd.write_text(APPROVED_TDD_SIGNOFF)
        result = runner.invoke(main, ["scaffold", "--domain", "test"])
        assert result.exit_code == 0, result.output
        assert "Scaffolded" in result.output


# ── tdd command gates on BRD ────────────────────────────────────────────────

class TestTddGateBRD:
    def test_tdd_fails_when_brd_missing(self, project_dir: Path, runner):
        (project_dir / "business-requirements.md").unlink()
        result = runner.invoke(main, ["tdd", "--domain", "test"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_tdd_fails_when_brd_unapproved(self, project_dir: Path, runner):
        brd = project_dir / "business-requirements.md"
        brd.write_text(PENDING_BRD_SIGNOFF)
        result = runner.invoke(main, ["tdd", "--domain", "test"])
        assert result.exit_code != 0
        assert "unapproved sign-off" in result.output

    def test_tdd_fails_when_brd_has_no_signoff_rows(self, project_dir: Path, runner):
        brd = project_dir / "business-requirements.md"
        brd.write_text("# BRD\n\nNo sign-off section.\n")
        result = runner.invoke(main, ["tdd", "--domain", "test"])
        assert result.exit_code != 0
        assert "no sign-off rows" in result.output

    def test_tdd_succeeds_with_approved_brd(self, project_dir: Path, runner):
        brd = project_dir / "business-requirements.md"
        brd.write_text(APPROVED_BRD_SIGNOFF)
        result = runner.invoke(main, ["tdd", "--domain", "test"])
        assert result.exit_code == 0, result.output
        assert (project_dir / "tech-design-doc.md").exists()


# ── role-aware approval gate ──────────────────────────────────────────────────

class TestRoleAwareApprovalGate:
    def test_brd_missing_consumer_role_blocked(self, project_dir: Path, runner):
        brd = project_dir / "business-requirements.md"
        brd.write_text(BRD_MISSING_CONSUMER)
        result = runner.invoke(main, ["tdd", "--domain", "test"])
        assert result.exit_code != 0
        assert "missing mandatory sign-off role" in result.output
        assert "consumer (primary user)" in result.output

    def test_tdd_missing_reviewer_role_blocked(self, project_dir: Path, runner):
        brd = project_dir / "business-requirements.md"
        brd.write_text(APPROVED_BRD_SIGNOFF)
        tdd = project_dir / "tech-design-doc.md"
        tdd.write_text(TDD_MISSING_REVIEWER)
        result = runner.invoke(main, ["scaffold", "--domain", "test"])
        assert result.exit_code != 0
        assert "missing mandatory sign-off role" in result.output
        assert "reviewer" in result.output

    def test_duplicate_approved_role_blocked(self, project_dir: Path, runner):
        brd = project_dir / "business-requirements.md"
        brd.write_text(BRD_DUPLICATE_OPERATOR)
        result = runner.invoke(main, ["tdd", "--domain", "test"])
        assert result.exit_code != 0
        assert "duplicate sign-off role" in result.output
        assert "operator (data owner)" in result.output

    def test_partial_approval_blocked(self, project_dir: Path, runner):
        brd = project_dir / "business-requirements.md"
        brd.write_text(BRD_PARTIAL_APPROVAL)
        result = runner.invoke(main, ["tdd", "--domain", "test"])
        assert result.exit_code != 0
        assert "unapproved sign-off" in result.output

    def test_fully_role_complete_and_approved_passes(self, project_dir: Path, runner):
        brd = project_dir / "business-requirements.md"
        brd.write_text(APPROVED_BRD_SIGNOFF)
        tdd = project_dir / "tech-design-doc.md"
        tdd.write_text(APPROVED_TDD_SIGNOFF)
        result = runner.invoke(main, ["scaffold", "--domain", "test"])
        assert result.exit_code == 0, result.output
        assert "Scaffolded" in result.output
