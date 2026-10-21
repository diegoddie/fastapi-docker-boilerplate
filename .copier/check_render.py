"""
Check a generated project for leftovers of the template (run by its CI).

Usage: check_render.py <project directory>
"""

from __future__ import annotations

import sys
from pathlib import Path

from prune import BLOCK, LINE, text_files

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
ANSWERS_FILE = ".copier-answers.yml"
TEMPLATE_ONLY_PATHS = (
    ".copier",
    "copier.yml",
    ".github/workflows/template.yml",
    "docs/adr/0013-the-template-prunes-a-working-app.md",
)


def leftovers(root: Path) -> list[str]:
    """Return what the template left in a generated project."""
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
    answers = root / ANSWERS_FILE
    if not answers.exists():
        problems.append(".copier-answers.yml is missing")
    elif not {"_commit:", "_src_path:"} <= {
        line.split(" ", 1)[0]
        for line in answers.read_text(encoding="utf-8").splitlines()
    }:
        problems.append(".copier-answers.yml lacks _commit or _src_path")
    return problems


if __name__ == "__main__":
    found = leftovers(Path(sys.argv[1]))
    for problem in found:
        print(problem, file=sys.stderr)
    sys.exit(1 if found else 0)
