# 0013. The template prunes a working app

- Status: Accepted
- Date: 2026-10-21

## Context

The repository is both a showcase and the starting point of new projects. A new
project should get its own name and only the modules it asks for (background
jobs, Sentry, AI, payments), and should be able to take the template's later
improvements. A classic Copier template keeps its sources as Jinja templates:
they don't run, ruff, mypy and Dependabot can't check them, and they are hard
to read on GitHub.

## Decision

- `main` stays the complete, working app with every module, tested by its own
  CI. [Copier](https://copier.readthedocs.io/) generates a project from it.
- Generating **removes** what the answers leave out, never rewrites it:
  - whole directories and files of a module, through `_exclude` in `copier.yml`;
  - the lines of a module in shared files, between comment markers
    (`# copier:<module>:start` / `:end`, or `# copier:<module>` on one line;
    HTML comments in Markdown), removed by `.copier/prune.py`, run as a task;
  - the `template` pseudo-module marks what only the template needs (this ADR,
    the "Generate a project" section, the template's CI).
- The same script writes the project's name, description and author over the
  template's (an exact list of replacements), and re-locks the dependencies.
- Module code is always an addition (an import, a list item, a settings block,
  a router include), never an alternative to core code, so every generated
  variant is the tested app minus some blocks.
- The template's CI (`.github/workflows/template.yml`) generates projects from
  several answer sets and runs their own CI on each.
- Updates: `copier update` merges the template's changes into the project; the
  lock is never merged, but re-locked after the update.

## Consequences

- The repository reads and runs like any project; markers only appear where
  modules plug in (settings, routers, model registry, dependencies, docs), and
  are invisible in rendered Markdown.
- A forgotten marker shows up as an unused import, a type error or missing
  coverage in a generated variant, and `prune.py check` rejects unbalanced or
  unknown markers.
- Copier must run with `--trust`, since generation runs a script.
- An option that changes core behavior instead of adding code (e.g. "no
  authentication") does not fit and is left out.

## Alternatives considered

- **Jinja templates in a `template/` directory**: the most flexible, but the
  sources stop being a working, checked app.
- **Jinja only at the integration points**: each such file exists twice (the
  template and the working copy) and drifts.
- **GitHub's "Use this template"**: a one-time copy, with no questions and no
  updates.
