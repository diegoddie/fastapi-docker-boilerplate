"""The template's prune script tests."""

import json
import shutil
import subprocess
from pathlib import Path

import prune
import pytest
from check_render import leftovers
from prune import REPLACEMENTS, Answers, MarkerError, prune_text

TEMPLATE_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch) -> frozenset[str]:
    """Pretend the template has two optional modules, payments and sentry."""
    known = frozenset({"template", "payments", "sentry"})
    monkeypatch.setattr(prune, "MODULES", known)
    return known


@pytest.fixture
def answers() -> Answers:
    """Return answers with characters that need escaping."""
    return Answers(
        project_name="Acme Billing API",
        project_slug="acme-billing-api",
        project_description='Invoices and "quotes": déjà vu.',
        author_name="Jane Doe",
        author_email="jane@example.com",
        copyright_year="2026",
        modules=frozenset(),
    )


def test_block_removed(modules: frozenset[str]) -> None:
    """Test a block of a module turned off goes, with its blank lines merged."""
    text = (
        "import os\n\n\n"
        "# copier:payments:start\n"
        "def pay() -> None:\n    pass\n"
        "# copier:payments:end\n\n\n"
        "def run() -> None:\n    pass\n"
    )
    assert prune_text(text, frozenset()) == (
        "import os\n\n\ndef run() -> None:\n    pass\n"
    )


def test_block_kept(modules: frozenset[str]) -> None:
    """Test a block of a module turned on stays, without its markers."""
    text = "a = 1\n# copier:payments:start\nb = 2\n# copier:payments:end\nc = 3\n"
    assert prune_text(text, frozenset({"payments"})) == "a = 1\nb = 2\nc = 3\n"


def test_negated_block(modules: frozenset[str]) -> None:
    """Test a negated block stays only when the module is off."""
    text = "# copier:!payments:start\nfree = True\n# copier:!payments:end\n"
    assert prune_text(text, frozenset()) == "free = True\n"
    assert prune_text(text, frozenset({"payments"})) == ""


def test_nested_blocks(modules: frozenset[str]) -> None:
    """Test an inner block goes with its outer block, or on its own."""
    text = (
        "# copier:payments:start\npay = 1\n"
        "# copier:sentry:start\nreport = 2\n# copier:sentry:end\n"
        "# copier:payments:end\n"
    )
    assert prune_text(text, frozenset({"sentry"})) == ""
    assert prune_text(text, frozenset({"payments"})) == "pay = 1\n"
    assert prune_text(text, frozenset({"payments", "sentry"})) == (
        "pay = 1\nreport = 2\n"
    )


@pytest.mark.parametrize(
    ("text", "kept", "removed"),
    [
        (
            "from app import core\nfrom app import payments  # copier:payments\n",
            "from app import core\nfrom app import payments\n",
            "from app import core\n",
        ),
        (
            "| Name | Use |\n|---|---|\n"
            "| Polar | payments <!-- copier:payments --> |\n",
            "| Name | Use |\n|---|---|\n| Polar | payments |\n",
            "| Name | Use |\n|---|---|\n",
        ),
    ],
    ids=["python", "markdown_table"],
)
def test_line_marker(
    modules: frozenset[str], text: str, kept: str, removed: str
) -> None:
    """Test a marked line stays without its marker, or goes."""
    assert prune_text(text, frozenset({"payments"})) == kept
    assert prune_text(text, frozenset()) == removed


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("# copier:billing:start\n# copier:billing:end\n", "unknown module 'billing'"),
        ("x = 1  # copier:billing\n", "unknown module 'billing'"),
        ("# copier:payments:end\n", "unexpected end of 'payments'"),
        (
            "# copier:payments:start\n# copier:sentry:end\n",
            "unexpected end of 'sentry'",
        ),
        ("# copier:payments:start\n", "'payments' is never closed"),
    ],
    ids=["unknown_block", "unknown_line", "end_only", "crossed", "unclosed"],
)
def test_bad_markers(modules: frozenset[str], text: str, error: str) -> None:
    """Test unknown modules and unbalanced blocks are errors, not silent."""
    with pytest.raises(MarkerError, match=error):
        prune_text(text, frozenset())


def test_answers_from_json() -> None:
    """Test the answers of Copier, with the database name derived from the slug."""
    answers = Answers.from_json(
        json.dumps(
            {
                "_commit": "v2.0.0",
                "project_name": "Acme",
                "project_slug": "acme-billing-api",
                "project_description": "Billing.",
                "author_name": "Jane Doe",
                "author_email": "jane@example.com",
                "copyright_year": 2026,
            }
        )
    )
    assert answers.db_name == "acme_billing_api"
    assert answers.copyright_year == "2026"
    assert answers.modules == frozenset()


def test_prune_the_template(tmp_path: Path, answers: Answers) -> None:
    """Test the template's identity is replaced in its real files, escaped."""
    for path in {replacement.path for replacement in REPLACEMENTS}:
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(TEMPLATE_ROOT / path, tmp_path / path)
    prune.prune(tmp_path, answers)
    pyproject = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "acme-billing-api"' in pyproject
    assert 'description = "Invoices and \\"quotes\\": déjà vu."' in pyproject
    assert 'title="Acme Billing API"' in (tmp_path / "app/main.py").read_text()
    assert "POSTGRES_DB=acme_billing_api" in (tmp_path / "compose.yaml").read_text()
    assert "Copyright (c) 2026 Jane Doe" in (tmp_path / "LICENSE").read_text()
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# Acme Billing API\n")
    assert "diegoddie" not in readme


def test_prune_stale_replacement(tmp_path: Path, answers: Answers) -> None:
    """Test a replacement whose text is gone fails instead of being skipped."""
    for replacement in REPLACEMENTS:
        (tmp_path / replacement.path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / replacement.path).write_text("renamed\n", encoding="utf-8")
    with pytest.raises(MarkerError, match="not found"):
        prune.prune(tmp_path, answers)


def test_check_the_template() -> None:
    """Test the template's own markers and replacements are consistent."""
    assert prune.check(TEMPLATE_ROOT) == []


def test_check_problems(tmp_path: Path) -> None:
    """Test bad markers and stale replacements are reported."""
    for replacement in REPLACEMENTS:
        (tmp_path / replacement.path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / replacement.path).write_text("renamed\n", encoding="utf-8")
    (tmp_path / "broken.py").write_text("# copier:template:start\n", encoding="utf-8")
    problems = prune.check(tmp_path)
    assert "broken.py: 'template' is never closed" in problems
    assert len(problems) == 1 + len(REPLACEMENTS)


def test_lock_without_uv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test generation still succeeds without uv, telling what to run."""
    monkeypatch.setattr(shutil, "which", lambda name: None)
    prune.lock(tmp_path)
    assert "run `uv lock`" in capsys.readouterr().err


def test_lock_with_uv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test the dependencies are re-locked in the project."""
    calls: list[tuple[list[str], Path]] = []

    def run(
        args: list[str], cwd: Path, check: bool
    ) -> subprocess.CompletedProcess[bytes]:
        """Record the command instead of running it."""
        calls.append((args, cwd))
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(subprocess, "run", run)
    prune.lock(tmp_path)
    assert calls == [(["/usr/bin/uv", "lock"], tmp_path)]


def test_main_usage(capsys: pytest.CaptureFixture[str]) -> None:
    """Test an unknown subcommand prints the usage."""
    assert prune.main(["unknown"]) == 2
    assert "Subcommands" in capsys.readouterr().err


def test_leftovers_none(tmp_path: Path) -> None:
    """Test a clean project passes, its answers pointing to the template."""
    (tmp_path / ".copier-answers.yml").write_text(
        "_commit: v2.0.0\n_src_path: gh:diegoddie/fastapi-docker-boilerplate\n"
    )
    assert leftovers(tmp_path) == []


def test_leftovers(tmp_path: Path) -> None:
    """Test the render check finds markers, identity and template-only files."""
    (tmp_path / ".copier").mkdir()
    (tmp_path / "app.py").write_text(
        "x = 1  # copier:template\nname = 'fastapi-docker-boilerplate'\n"
    )
    (tmp_path / "docs/adr").mkdir(parents=True)
    (tmp_path / "docs/adr/0001.md").write_text("The FastAPI Docker Boilerplate.\n")
    assert leftovers(tmp_path) == [
        ".copier exists",
        "app.py:1: marker left",
        "app.py:2: 'fastapi-docker-boilerplate' left",
        ".copier-answers.yml is missing",
    ]
