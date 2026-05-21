"""mart-forge CLI: init, tdd, and scaffold commands."""

from __future__ import annotations

import shutil
from pathlib import Path

import click
import yaml
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

LAYER_ORDER = ["ods", "dim", "dwd", "dws", "ads"]

LAYER_MATERIALIZATION = {
    "ods": "view",
    "dim": "table",
    "dwd": "table",
    "dws": "table",
    "ads": "table",
}

DBT_PROJECT_TEMPLATE = """\
name: {profile}
version: "1.0.0"
config-version: 2

profile: {profile}

model-paths: ["models"]
seed-paths: ["seeds"]
test-paths: ["tests"]
analysis-paths: ["analyses"]

clean-targets:
  - target
  - dbt_packages

models:
  {profile}:
{model_layers}
"""

PROFILES_TEMPLATE = """\
{profile}:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "target/{db_name}.duckdb"
      schema: main
      threads: 1
"""

GITIGNORE = """\
target/
dbt_packages/
logs/
*.duckdb
*.duckdb.wal
__pycache__/
.user.yml
"""


def _find_templates_dir() -> Path:
    if TEMPLATES_DIR.is_dir():
        return TEMPLATES_DIR
    installed = Path(__file__).resolve().parent / "templates"
    if installed.is_dir():
        return installed
    raise click.ClickException(
        f"Cannot find templates directory (checked {TEMPLATES_DIR} and {installed})"
    )


def _doc_has_approval(path: Path) -> bool:
    """Return True if a markdown document has at least one approved sign-off row."""
    content = path.read_text()
    for line in content.splitlines():
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c]
        if len(cells) < 2:
            continue
        status = cells[-1].lower()
        if status in ("approved", "approved-with-conditions"):
            return True
    return False


def _require_approved(path: Path, doc_label: str, next_phase: str) -> None:
    """Abort with a helpful message if the document is missing or unapproved."""
    if not path.exists():
        raise click.ClickException(
            f"{doc_label} not found ({path.name}). "
            f"Complete the previous phase before {next_phase}."
        )
    if not _doc_has_approval(path):
        raise click.ClickException(
            f"{doc_label} ({path.name}) has no approved sign-off. "
            f"Get sign-off before proceeding to {next_phase}."
        )


@click.group()
@click.version_option(package_name="mart-forge")
def main() -> None:
    """mart-forge: Kimball data warehouse scaffolding."""


@main.command()
@click.argument("name")
@click.option(
    "--db-name",
    default=None,
    help="Database name for dbt profile (default: derived from NAME).",
)
@click.option(
    "--prefix",
    default=None,
    help="Model prefix, 3-5 chars (default: first 3 chars of NAME).",
)
def init(name: str, db_name: str | None, prefix: str | None) -> None:
    """Initialize a new mart-forge project directory.

    Creates NAME/ with mart.yml, dbt_project.yml, profiles.yml,
    and the standard Kimball layer directories.
    """
    project_dir = Path.cwd() / name
    if project_dir.exists():
        raise click.ClickException(f"Directory '{name}' already exists.")

    db_name = db_name or name.replace("-", "_") + "_db"
    prefix = prefix or name.replace("-", "_")[:3]
    profile = name.replace("-", "_")

    tpl_dir = _find_templates_dir()

    project_dir.mkdir()
    for sub in ["models", "seeds", "tests"]:
        (project_dir / sub).mkdir()
    for layer in LAYER_ORDER:
        (project_dir / "models" / layer).mkdir()
        (project_dir / "models" / layer / ".gitkeep").touch()

    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        keep_trailing_newline=True,
    )
    mart_tpl = env.get_template("mart.yml.template")
    rendered_mart = mart_tpl.render(
        mart={"name": name, "db_name": db_name, "prefix": prefix, "grain": "per-entity-per-day"},
        providers={"primary": "csv_seed"},
        schedule={"cron": "0 6 * * *", "timezone": "UTC"},
        dqc={
            "reconciliation": {
                "metric": "row_count",
                "source": "raw_seed",
                "tolerance": 0,
            }
        },
    )
    (project_dir / "mart.yml").write_text(rendered_mart)

    model_layers = "\n".join(
        f"    {layer}:\n      +materialized: {mat}"
        for layer, mat in LAYER_MATERIALIZATION.items()
    )
    dbt_project = DBT_PROJECT_TEMPLATE.format(
        profile=profile,
        model_layers=model_layers,
    )
    (project_dir / "dbt_project.yml").write_text(dbt_project)

    profiles = PROFILES_TEMPLATE.format(profile=profile, db_name=db_name)
    (project_dir / "profiles.yml").write_text(profiles)

    (project_dir / ".gitignore").write_text(GITIGNORE)

    brd_src = tpl_dir / "business-requirements.template.md"
    if brd_src.exists():
        shutil.copy2(brd_src, project_dir / "business-requirements.md")

    click.echo(f"Created mart-forge project in ./{name}/")
    click.echo(f"  mart.yml                  — edit grain, providers, schedule")
    click.echo(f"  business-requirements.md  — Phase A: fill and get sign-off")
    click.echo(f"  dbt_project.yml           — dbt config (profile: {profile})")
    click.echo(f"  profiles.yml              — local DuckDB connection")
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  cd {name}")
    click.echo(f"  # Fill business-requirements.md and get operator sign-off")
    click.echo(f"  mart-forge tdd --domain \"your data domain\"")
    click.echo(f"  # Fill tech-design-doc.md and get reviewer sign-off")
    click.echo(f"  mart-forge scaffold --domain \"your data domain\"")


@main.command()
@click.option(
    "--domain",
    required=True,
    help="Short description of the data domain (used in TDD header).",
)
def tdd(domain: str) -> None:
    """Generate Phase B artifacts (TDD + sign-off PRD) after BRD approval.

    Checks that business-requirements.md has an approved sign-off,
    then copies the TDD and sign-off PRD templates into the project.
    """
    brd_path = Path.cwd() / "business-requirements.md"
    _require_approved(brd_path, "Business Requirements Document", "TDD generation")

    tpl_dir = _find_templates_dir()

    tdd_src = tpl_dir / "tech-design-doc.template.md"
    tdd_dst = Path.cwd() / "tech-design-doc.md"
    if tdd_dst.exists():
        raise click.ClickException(
            f"tech-design-doc.md already exists. Remove it to regenerate."
        )
    if tdd_src.exists():
        shutil.copy2(tdd_src, tdd_dst)
    else:
        raise click.ClickException("TDD template not found in templates directory.")

    sign_off_src = tpl_dir / "sign-off-prd.template.md"
    sign_off_dst = Path.cwd() / "sign-off-prd.md"
    if sign_off_src.exists() and not sign_off_dst.exists():
        shutil.copy2(sign_off_src, sign_off_dst)

    click.echo(f"Phase B artifacts generated for domain: {domain}")
    click.echo(f"  tech-design-doc.md  — fill column-level specs and get sign-off")
    click.echo(f"  sign-off-prd.md     — project sign-off summary")
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  # Fill tech-design-doc.md and get reviewer sign-off")
    click.echo(f"  mart-forge scaffold --domain \"{domain}\"")


@main.command()
@click.option(
    "--domain",
    required=True,
    help="Short description of the data domain (used in model headers).",
)
@click.option(
    "--template",
    "template_name",
    default="default",
    help="Template set to use (default: 'default').",
)
@click.option(
    "--layers",
    default=",".join(LAYER_ORDER),
    help=f"Comma-separated layers to scaffold (default: {','.join(LAYER_ORDER)}).",
)
def scaffold(domain: str, template_name: str, layers: str) -> None:
    """Scaffold Kimball layer models from templates into the current project.

    Reads mart.yml in the current directory and generates SQL model files
    for each requested layer using the bundled templates.
    Requires an approved Tech Design Document (Phase B gate).
    """
    brd_path = Path.cwd() / "business-requirements.md"
    _require_approved(brd_path, "Business Requirements Document", "scaffold")

    tdd_path = Path.cwd() / "tech-design-doc.md"
    _require_approved(tdd_path, "Tech Design Document", "scaffold")

    mart_yml = Path.cwd() / "mart.yml"
    if not mart_yml.exists():
        raise click.ClickException(
            "No mart.yml found in current directory. Run 'mart-forge init' first."
        )

    with open(mart_yml) as f:
        config = yaml.safe_load(f)

    mart = config.get("mart", {})
    mart_name = mart.get("name", "unnamed")
    prefix = mart.get("prefix", "x")
    grain = mart.get("grain", "per-entity")

    tpl_dir = _find_templates_dir()
    requested_layers = [l.strip() for l in layers.split(",") if l.strip()]

    models_dir = Path.cwd() / "models"
    models_dir.mkdir(exist_ok=True)

    generated = []
    for layer in requested_layers:
        if layer not in LAYER_ORDER:
            click.echo(f"  skip unknown layer: {layer}", err=True)
            continue

        tpl_path = tpl_dir / "models" / layer / "template.sql"
        if not tpl_path.exists():
            click.echo(f"  skip {layer}: no template found", err=True)
            continue

        layer_dir = models_dir / layer
        layer_dir.mkdir(exist_ok=True)

        out_name = f"{prefix}_{layer}__example.sql"
        content = _render_model(tpl_path, prefix=prefix, grain=grain, domain=domain)
        out_path = layer_dir / out_name
        out_path.write_text(content)
        generated.append(f"  models/{layer}/{out_name}")

    if generated:
        click.echo(f"Scaffolded {len(generated)} model(s) for '{mart_name}':")
        for g in generated:
            click.echo(g)
        click.echo()
        click.echo("Templates contain TODO placeholders — fill in columns and logic.")
    else:
        click.echo("No models were scaffolded. Check --layers value.")


def _render_model(tpl_path: Path, *, prefix: str, grain: str, domain: str) -> str:
    header = (
        f"-- mart-forge scaffold | domain: {domain} | prefix: {prefix} | grain: {grain}\n"
        f"-- TODO: Replace placeholder columns with your actual schema.\n\n"
    )
    return header + tpl_path.read_text()
