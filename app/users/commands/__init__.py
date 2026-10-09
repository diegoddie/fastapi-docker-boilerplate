"""The users package commands."""

import typer

from app.users.commands.createsuperuser import createsuperuser

app = typer.Typer(help="Manage users.", no_args_is_help=True)
app.command()(createsuperuser)
