"""The template CI matrix tests."""

import json
import re

import matrix
import pytest
from matrix import (
    ANSWERS_DIR,
    OPTIONS,
    answer_sets,
    every_combination,
    pairwise,
    uncovered_pairs,
)

IDENTITY = {
    "project_name",
    "project_slug",
    "project_description",
    "author_name",
    "author_email",
    "copyright_year",
}


def test_options_are_the_questions() -> None:
    """Test the options are the questions of copier.yml, the identity apart."""
    text = (ANSWERS_DIR.parents[1] / "copier.yml").read_text(encoding="utf-8")
    questions = set(re.findall(r"^([a-z][a-z_]*):\s*$", text, flags=re.MULTILINE))
    assert questions - IDENTITY == set(OPTIONS)


def test_answer_sets_meet_every_pair() -> None:
    """Test every value of an option meets every value of every other option."""
    assert uncovered_pairs(list(answer_sets().values())) == []
    assert all(set(OPTIONS) <= set(answers) for answers in answer_sets().values())


def test_uncovered_pairs() -> None:
    """Test the missing pairs of two answer sets are reported."""
    everything = {"ai": True, "background_jobs": "celery", "payments": "polar"}
    nothing = {"ai": False, "background_jobs": "cron", "payments": "none"}
    missing = uncovered_pairs([everything | {"posthog": True, "sentry": True}, nothing])
    assert "ai=True with background_jobs=cron" in missing
    assert "ai=True with background_jobs=celery" not in missing


def test_pairwise() -> None:
    """Test each answer set is a project, its build cache kept."""
    projects = {project["name"]: project for project in pairwise()}
    assert projects["acme"] == {
        "name": "acme",
        "args": "--data-file .copier/answers/acme.yml",
        "celery": True,
        "bake_set": "*.cache-from=type=gha,scope=template-acme\n"
        "*.cache-to=type=gha,mode=max,scope=template-acme",
    }
    assert projects["todo"]["celery"] is False


def test_every_combination() -> None:
    """Test the 32 combinations, named by what they turn on, share one cache."""
    projects = every_combination()
    names = [project["name"] for project in projects]
    assert len(set(names)) == len(projects) == 2 ** len(OPTIONS)
    assert {"minimal", "ai+celery+polar+posthog+sentry", "celery"} <= set(names)
    assert sum(project["celery"] is True for project in projects) == len(projects) // 2
    minimal = projects[names.index("minimal")]
    assert minimal["args"] == (
        "--data-file .copier/answers/acme.yml --data ai=false "
        "--data background_jobs=cron --data payments=none --data posthog=false "
        "--data sentry=false"
    )
    assert minimal["bake_set"] == "*.cache-from=type=gha,scope=template-acme"


@pytest.mark.parametrize(
    ("argv", "code"), [(["pairwise"], 0), (["all"], 0), (["check"], 0), ([], 2)]
)
def test_main(argv: list[str], code: int, capsys: pytest.CaptureFixture[str]) -> None:
    """Test the subcommands print a matrix, check the sets, or the usage."""
    assert matrix.main(argv) == code
    out = capsys.readouterr().out
    if argv[:1] in (["pairwise"], ["all"]):
        assert json.loads(out)["include"]


def test_check_reports(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test check fails and names the pairs no answer set has."""
    monkeypatch.setattr(matrix, "answer_sets", lambda: {"todo": answer_sets()["todo"]})
    assert matrix.main(["check"]) == 1
    assert "no answer set has ai=True with" in capsys.readouterr().err
