"""
List the projects the template's CI generates, as a GitHub Actions matrix.

Usage:

    matrix.py pairwise   the answer sets of .copier/answers/ (every change)
    matrix.py all        every combination of the options (weekly)
    matrix.py check      check the answer sets meet every pair of option values

Why: the options make 32 combinations; six answer sets, chosen so that every
value of an option meets every value of every other option, find the bugs
that need two modules together, at a fifth of the cost.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

from check_render import read_answers
from prune import OPTIONS

ANSWERS_DIR = Path(__file__).resolve().parent / "answers"
# The answer set whose identity the combinations of the weekly run share.
BASE = "acme"
CACHE_FROM = "*.cache-from=type=gha,scope=template-{name}"
CACHE_TO = "*.cache-to=type=gha,mode=max,scope=template-{name}"


def answer_sets() -> dict[str, dict[str, object]]:
    """Return the answer sets, by name."""
    return {path.stem: read_answers(path) for path in sorted(ANSWERS_DIR.glob("*.yml"))}


def uncovered_pairs(sets: list[dict[str, object]]) -> list[str]:
    """Return the pairs of option values that no answer set has together."""
    return [
        f"{first}={first_value} with {second}={second_value}"
        for (first, first_values), (second, second_values) in itertools.combinations(
            OPTIONS.items(), 2
        )
        for first_value, second_value in itertools.product(first_values, second_values)
        if not any(
            answers.get(first) == first_value and answers.get(second) == second_value
            for answers in sets
        )
    ]


def entry(
    name: str, args: str, answers: dict[str, object], cache: bool
) -> dict[str, object]:
    """Return a project of the matrix."""
    bake_set = [CACHE_FROM.format(name=name if cache else BASE)]
    if cache:
        # Why: the cache of every combination would not fit in GitHub's 10 GB.
        bake_set.append(CACHE_TO.format(name=name))
    return {
        "name": name,
        "args": args,
        "celery": answers.get("background_jobs") == "celery",
        "bake_set": "\n".join(bake_set),
    }


def pairwise() -> list[dict[str, object]]:
    """Return the projects of the answer sets."""
    return [
        entry(name, f"--data-file .copier/answers/{name}.yml", answers, cache=True)
        for name, answers in answer_sets().items()
    ]


def every_combination() -> list[dict[str, object]]:
    """Return a project for every combination of the options."""
    entries = []
    for values in itertools.product(*OPTIONS.values()):
        answers = dict(zip(OPTIONS, values, strict=True))
        name = "+".join(
            option if value is True else str(value)
            for option, value in answers.items()
            if value is True or value not in (False, OPTIONS[option][0])
        )
        args = f"--data-file .copier/answers/{BASE}.yml " + " ".join(
            f"--data {option}={str(value).lower()}" for option, value in answers.items()
        )
        entries.append(entry(name or "minimal", args, answers, cache=False))
    return entries


def main(argv: list[str]) -> int:
    """Print a matrix, or check the answer sets."""
    match argv:
        case ["pairwise"]:
            print(json.dumps({"include": pairwise()}))
        case ["all"]:
            print(json.dumps({"include": every_combination()}))
        case ["check"]:
            missing = uncovered_pairs(list(answer_sets().values()))
            for pair in missing:
                print(f"no answer set has {pair}", file=sys.stderr)
            return 1 if missing else 0
        case _:
            print(__doc__, file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
