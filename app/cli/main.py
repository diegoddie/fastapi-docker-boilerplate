"""
The cli package main app.

Run it with ``just manage <command>``, e.g. ``just manage seed`` or
``just manage users createsuperuser``.
"""

import typer

import app.core.models  # noqa: F401  # side-effect: register every model
from app.cli.purge import purge
from app.cli.seed import seed
from app.cli.shell import shell
from app.core.config import settings
from app.core.logs import configure_logging
from app.users.commands import app as users_commands

configure_logging(settings)

cli = typer.Typer(help="Management commands.", no_args_is_help=True)
cli.command()(purge)
cli.command()(seed)
cli.command()(shell)
cli.add_typer(users_commands, name="users")

if __name__ == "__main__":  # pragma: no cover
    cli()
