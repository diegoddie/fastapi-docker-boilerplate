"""
The cli package main app.

Run it with ``just manage <group> <command>``,
e.g. ``just manage users createsuperuser``.
"""

import typer

import app.core.models  # noqa: F401  # side-effect: register every model
from app.users.commands import app as users_commands

cli = typer.Typer(help="Management commands.", no_args_is_help=True)
cli.add_typer(users_commands, name="users")

if __name__ == "__main__":  # pragma: no cover
    cli()
