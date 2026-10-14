"""The auth package commands."""

import typer

from app.auth.commands.purge_tokens import purge_tokens

app = typer.Typer(help="Manage authentication.", no_args_is_help=True)
app.command()(purge_tokens)
