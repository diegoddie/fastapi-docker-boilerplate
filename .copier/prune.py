"""
Turn the template into a generated project: Copier runs this as a task.

The template is a working app with every optional module. In the files that
modules share, markers delimit what belongs to a module:

    # copier:<module>:start        (or <!-- copier:<module>:start --> in Markdown)
    ...
    # copier:<module>:end
    a_line()  # copier:<module>     (or <!-- copier:<module> --> anywhere in a line)

A condition ``!<module>`` keeps the code only when the module is off. The
``template`` module is always off: it marks what only the template needs.

Subcommands:

    prune.py prune '<answers as JSON>'   remove what the answers left out, set the
                                         project's name, description and author
    prune.py lock                        re-lock the dependencies with uv
    prune.py check                       check the markers and the replacements
                                         of the template (run by its CI)

Why: written for Python 3.10+ with the standard library only, because Copier
runs it with its own Python, before the project's environment exists.
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess  # nosec B404
import sys
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

# The optional modules, and the answers that turn each one on; "template" marks
# what only the template needs, so a generated project never has it.
MODULE_ANSWERS: dict[str, Callable[[Mapping[str, object]], bool]] = {
    "ai": lambda answers: answers.get("ai") is True,
    "celery": lambda answers: answers.get("background_jobs") == "celery",
    "payments": lambda answers: answers.get("payments") == "polar",
    "posthog": lambda answers: answers.get("posthog") is True,
    "sentry": lambda answers: answers.get("sentry") is True,
    "template": lambda answers: False,
}
MODULES = frozenset(MODULE_ANSWERS)

SKIPPED_DIRS = frozenset(
    {
        ".copier",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "htmlcov",
        "node_modules",
    }
)

BLOCK = re.compile(
    r"^\s*(?:#|<!--)\s*copier:(?P<condition>!?[a-z_]+):(?P<edge>start|end)"
    r"\s*(?:-->)?\s*$"
)
LINE = re.compile(
    r"\s*(?:#\s*copier:(?P<comment>!?[a-z_]+)\s*$|<!--\s*copier:(?P<html>!?[a-z_]+)\s*-->)"
)


class MarkerError(ValueError):
    """A marker is unbalanced or names an unknown module."""


@dataclass(frozen=True)
class Answers:
    """The answers that shape the generated project."""

    project_name: str
    project_slug: str
    project_description: str
    author_name: str
    author_email: str
    copyright_year: str
    modules: frozenset[str]

    @property
    def db_name(self) -> str:
        """Return the name of the database (and of the Docker image)."""
        return self.project_slug.replace("-", "_")

    @classmethod
    def from_json(cls, text: str) -> Answers:
        """Read the answers Copier passes to the task."""
        data = json.loads(text)
        return cls(
            project_name=data["project_name"],
            project_slug=data["project_slug"],
            project_description=data["project_description"],
            author_name=data["author_name"],
            author_email=data["author_email"],
            copyright_year=str(data["copyright_year"]),
            modules=enabled_modules(data),
        )


def enabled_modules(answers: Mapping[str, object]) -> frozenset[str]:
    """Return the modules that the answers turn on."""
    return frozenset(name for name, is_on in MODULE_ANSWERS.items() if is_on(answers))


def quoted(value: str) -> str:
    """Return a double-quoted string literal, valid in Python and in TOML."""
    return json.dumps(value, ensure_ascii=False)


@dataclass(frozen=True)
class Replacement:
    """An exact text of the template replaced by one built from the answers."""

    path: str
    old: str
    new: Callable[[Answers], str]


# Why: the identity of the template, replaced as exact strings so that a stale
# entry fails `check` instead of silently leaving the template's name behind.
REPLACEMENTS = (
    Replacement(
        "pyproject.toml",
        'name = "fastapi-docker-boilerplate"',
        lambda a: f"name = {quoted(a.project_slug)}",
    ),
    Replacement(
        "pyproject.toml",
        'description = "Production-ready FastAPI boilerplate: async SQLModel, '
        'PostgreSQL, uv, Docker and 100% test coverage."',
        lambda a: f"description = {quoted(a.project_description)}",
    ),
    Replacement(
        "pyproject.toml",
        'authors = [{ name = "Diego Lauricella", email = "diego.boost@gmail.com" }]',
        lambda a: (
            f"authors = [{{ name = {quoted(a.author_name)}, "
            f"email = {quoted(a.author_email)} }}]"
        ),
    ),
    Replacement(
        "pyproject.toml",
        'title = "FastAPI Docker Boilerplate - Coverage"',
        lambda a: f"title = {quoted(a.project_name + ' - Coverage')}",
    ),
    Replacement(
        "Dockerfile",
        'LABEL project="fastapi-docker-boilerplate"',
        lambda a: f"LABEL project={quoted(a.project_slug)}",
    ),
    Replacement(
        "app/main.py",
        'title="FastAPI Docker Boilerplate"',
        lambda a: f"title={quoted(a.project_name)}",
    ),
    Replacement(
        "compose.yaml", "boilerplate_backend", lambda a: f"{a.db_name}_backend"
    ),
    Replacement(
        "compose.yaml",
        "postgres:5432/boilerplate}",
        lambda a: f"postgres:5432/{a.db_name}}}",
    ),
    Replacement(
        "compose.yaml", "POSTGRES_DB=boilerplate", lambda a: f"POSTGRES_DB={a.db_name}"
    ),
    Replacement(
        ".env_template",
        "localhost:5432/boilerplate",
        lambda a: f"localhost:5432/{a.db_name}",
    ),
    Replacement(
        "LICENSE",
        "Copyright (c) 2025-2026 Diego Lauricella",
        lambda a: f"Copyright (c) {a.copyright_year} {a.author_name}",
    ),
    Replacement(
        "README.md", "# FastAPI Docker Boilerplate", lambda a: f"# {a.project_name}"
    ),
    Replacement(
        "README.md",
        "A production-ready starting point for FastAPI backends: async SQLModel on "
        "PostgreSQL, strict quality gates, and a Docker setup that runs the same way "
        "on your laptop, in CI and in production.",
        lambda a: a.project_description,
    ),
)


def is_kept(condition: str, modules: frozenset[str], where: str) -> bool:
    """Tell if the code under a condition stays, given the modules turned on."""
    name = condition.removeprefix("!")
    if name not in MODULES:
        raise MarkerError(f"{where}: unknown module {name!r}")
    return (name in modules) != condition.startswith("!")


def without_marker(line: str, marker: re.Match[str]) -> str:
    """Return a line without its line marker."""
    if marker["comment"]:
        ending = "\n" if line.endswith("\n") else ""
        return line[: marker.start()] + ending
    return line[: marker.start()] + line[marker.end() :]


def normalize_blank_lines(lines: list[str], cuts: set[int]) -> list[str]:
    """
    Merge the blank lines around each cut into one gap.

    Why: removed code usually sits between blank lines; keeping the larger gap
    of the two leaves the formatting the formatter expects.
    """
    for cut in sorted(cuts, reverse=True):
        before = 0
        while cut - before > 0 and not lines[cut - before - 1].strip():
            before += 1
        after = 0
        while cut + after < len(lines) and not lines[cut + after].strip():
            after += 1
        if cut == before:
            # Why: a cut at the start of a file leaves no leading blank lines.
            del lines[: cut + after]
        else:
            del lines[cut - min(before, after) : cut]
    return lines


def prune_text(text: str, modules: frozenset[str], where: str = "<text>") -> str:
    """Return a text without the code of the modules turned off, or markers."""
    kept: list[str] = []
    cuts: set[int] = set()
    open_blocks: list[tuple[str, bool]] = []
    keep = True
    for number, line in enumerate(text.splitlines(keepends=True), start=1):
        location = f"{where}:{number}"
        block = BLOCK.match(line)
        if block:
            condition = block["condition"]
            if block["edge"] == "start":
                open_blocks.append((condition, keep))
                keep = keep and is_kept(condition, modules, location)
            else:
                if not open_blocks or open_blocks[-1][0] != condition:
                    raise MarkerError(f"{location}: unexpected end of {condition!r}")
                inside_kept = keep
                _, keep = open_blocks.pop()
                if keep and not inside_kept:
                    cuts.add(len(kept))
            continue
        if not keep:
            continue
        marker = LINE.search(line)
        if marker is None:
            kept.append(line)
        elif is_kept(marker["comment"] or marker["html"], modules, location):
            kept.append(without_marker(line, marker))
        else:
            cuts.add(len(kept))
    if open_blocks:
        raise MarkerError(f"{where}: {open_blocks[-1][0]!r} is never closed")
    pruned = "".join(normalize_blank_lines(kept, cuts))
    # Why: the blank lines above a marker at the end of the file, removed with
    # its block or alone, would end it.
    return pruned.rstrip("\n") + "\n" if pruned != text and pruned.strip() else pruned


def text_files(root: Path) -> Iterator[Path]:
    """Yield the text files of a project, outside caches and tooling folders."""
    for path in sorted(root.rglob("*")):
        if not path.is_file() or SKIPPED_DIRS & set(path.relative_to(root).parts):
            continue
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        yield path


def prune(root: Path, answers: Answers) -> None:
    """Shape a freshly rendered project after the answers."""
    for path in text_files(root):
        text = path.read_text(encoding="utf-8")
        pruned = prune_text(text, answers.modules, str(path.relative_to(root)))
        if pruned != text:
            path.write_text(pruned, encoding="utf-8")
    for replacement in REPLACEMENTS:
        path = root / replacement.path
        text = path.read_text(encoding="utf-8")
        if replacement.old not in text:
            raise MarkerError(f"{replacement.path}: {replacement.old!r} not found")
        path.write_text(
            text.replace(replacement.old, replacement.new(answers)), encoding="utf-8"
        )


def lock(root: Path) -> None:
    """Re-lock the dependencies, so the lock matches the pruned pyproject.toml."""
    uv = shutil.which("uv")
    if uv is None:
        print("uv is not installed: run `uv lock` in the project.", file=sys.stderr)
        return
    result = subprocess.run([uv, "lock"], cwd=root, check=False)  # nosec B603
    if result.returncode:
        print("`uv lock` failed: run it again in the project.", file=sys.stderr)


def module_variants() -> list[frozenset[str]]:
    """Return the sets of modules to check: each one off in turn, then none."""
    optional = MODULES - {"template"}
    return [optional - {name} for name in sorted(optional)] + [frozenset()]


def python_errors(text: str, where: str) -> list[str]:
    """
    Return the variants in which a Python file would not compile.

    Why: a line marker on the last line of a statement the formatter split
    (``)  # copier:x``) would leave the rest of the statement behind.
    """
    errors = []
    for modules in module_variants():
        try:
            ast.parse(prune_text(text, modules, where))
        except SyntaxError as e:
            off = ", ".join(sorted(MODULES - {"template"} - modules))
            errors.append(f"{where}:{e.lineno}: invalid Python without {off}")
    return errors


def orphan_errors(text: str, where: str, markdown: bool) -> list[str]:
    """
    Return the line markers that would leave part of what they mark behind.

    Why: a line marker removes one line; a comment that explains it, or the
    rest of a Markdown list item it belongs to, would stay. Use a block.
    """
    lines = text.splitlines()
    errors = []
    for number, line in enumerate(lines):
        following = lines[number + 1] if number + 1 < len(lines) else ""
        if BLOCK.match(line) and following.startswith(("from ", "import ")):
            # Why: isort wants a blank line before the end marker of a block of
            # imports, which then stays between imports once the markers go.
            errors.append(f"{where}:{number + 1}: a block of imports: mark each line")
        marker = LINE.search(line)
        if marker is None or BLOCK.match(line):
            continue
        previous = lines[number - 1].strip() if number else ""
        if markdown and (line[:1].isspace() or following[:2] == "  "):
            errors.append(f"{where}:{number + 1}: line marker on a multi-line item")
        elif not markdown and previous.startswith("#") and "copier:" not in previous:
            errors.append(f"{where}:{number + 1}: the comment above stays behind")
    return errors


def check(root: Path) -> list[str]:
    """Return the problems of the template: bad markers, stale replacements."""
    problems = []
    for path in text_files(root):
        where = str(path.relative_to(root))
        text = path.read_text(encoding="utf-8")
        try:
            prune_text(text, MODULES, where)
        except MarkerError as e:
            problems.append(str(e))
            continue
        if "copier:" not in text:
            continue
        problems.extend(orphan_errors(text, where, markdown=path.suffix == ".md"))
        if path.suffix == ".py":
            problems.extend(python_errors(text, where))
    for replacement in REPLACEMENTS:
        if replacement.old not in (root / replacement.path).read_text(encoding="utf-8"):
            problems.append(f"{replacement.path}: {replacement.old!r} not found")
    return problems


def main(argv: list[str]) -> int:
    """Run a subcommand in the current directory."""
    root = Path.cwd()
    match argv:
        case ["prune", answers]:
            prune(root, Answers.from_json(answers))
        case ["lock"]:
            lock(root)
        case ["check"]:
            problems = check(root)
            for problem in problems:
                print(problem, file=sys.stderr)
            return 1 if problems else 0
        case _:
            print(__doc__, file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
