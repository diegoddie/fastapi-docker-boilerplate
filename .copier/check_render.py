"""
Check a generated project for leftovers of the template (run by its CI).

Usage: check_render.py <project directory>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from prune import BLOCK, LINE, MODULES, OPTIONS, enabled_modules, text_files

# The template's identity, which no generated project may keep (outside the
# ADRs, which record the history of decisions as written).
TEMPLATE_IDENTITY = (
    "fastapi-docker-boilerplate",
    "FastAPI Docker Boilerplate",
    "boilerplate_backend",
    "5432/boilerplate",
    "diegoddie",
    "Diego Lauricella",
    "diego.boost",
)
# The words that betray a module left in a project that turned it off.
MODULE_KEYWORDS = {
    "ai": ("anthropic", "langchain", "langfuse", "subtask"),
    "celery": ("celery", "valkey"),
    "payments": ("polar", "subscription"),
    "posthog": ("posthog",),
    "sentry": ("sentry",),
}
ANSWERS_FILE = ".copier-answers.yml"
# Why: the table of the options lists every module, those a project can turn on.
OPTION_ROW = re.compile(r"^\| `(?P<option>[a-z_]+)` \|")
TEMPLATE_ONLY_PATHS = (
    ".copier",
    "copier.yml",
    ".github/workflows/template.yml",
    "CHANGELOG.md",
    "docs/adr/0013-the-template-prunes-a-working-app.md",
)


def read_answers(path: Path) -> dict[str, object]:
    """Return the top-level answers of an answers file, booleans parsed."""
    answers: dict[str, object] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition(":")
        if separator and not line.startswith((" ", "#")):
            answers[key] = {"true": True, "false": False}.get(
                value.strip(), value.strip()
            )
    return answers


def leftovers(root: Path) -> list[str]:
    """Return what the template left in a generated project."""
    answers_path = root / ANSWERS_FILE
    answers = read_answers(answers_path) if answers_path.exists() else {}
    keywords = [
        keyword
        for module in sorted(MODULES - enabled_modules(answers) - {"template"})
        for keyword in MODULE_KEYWORDS.get(module, ())
    ]
    problems = [
        f"{path} exists" for path in TEMPLATE_ONLY_PATHS if (root / path).exists()
    ]
    for path in text_files(root):
        relative = path.relative_to(root)
        # Why: the answers point to the template on purpose (for updates).
        if relative.parts[:2] == ("docs", "adr") or relative.name == ANSWERS_FILE:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if BLOCK.match(line) or LINE.search(line):
                problems.append(f"{relative}:{number}: marker left")
            problems.extend(
                f"{relative}:{number}: {identity!r} left"
                for identity in TEMPLATE_IDENTITY
                if identity in line
            )
            option_row = OPTION_ROW.match(line)
            if option_row and option_row["option"] in OPTIONS:
                continue
            problems.extend(
                f"{relative}:{number}: {keyword!r} of a module turned off"
                for keyword in keywords
                if keyword in line.lower()
            )
    if not answers_path.exists():
        problems.append(".copier-answers.yml is missing")
    elif not {"_commit", "_src_path"} <= answers.keys():
        problems.append(".copier-answers.yml lacks _commit or _src_path")
    return problems


if __name__ == "__main__":
    found = leftovers(Path(sys.argv[1]))
    for problem in found:
        print(problem, file=sys.stderr)
    sys.exit(1 if found else 0)
