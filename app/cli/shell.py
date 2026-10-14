"""The cli package shell command."""

from typing import Any

import typer
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

import app.core.models as models
from app.core.config import settings
from app.core.database import session_manager


def get_shell_namespace() -> dict[str, Any]:
    """Return the names the shell starts with."""
    return {
        "settings": settings,
        "session_manager": session_manager,
        "session": AsyncSession(session_manager.aengine, expire_on_commit=False),
        "select": select,
        "col": col,
        **{name: getattr(models, name) for name in models.__all__},
    }


async def close_shell_session(session: AsyncSession) -> None:
    """Close the shell session and the database connections."""
    await session.close()
    await session_manager.aclose()


def shell() -> None:  # pragma: no cover
    """Open an IPython shell with the settings, the database and the models."""
    try:
        from IPython import start_ipython
        from IPython.core.async_helpers import get_asyncio_loop
    except ModuleNotFoundError as e:
        typer.secho(
            "IPython is not installed (it is in the `local` dependency group).",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1) from e
    namespace = get_shell_namespace()
    # Why: IPython empties the namespace when it exits.
    session = namespace["session"]
    typer.secho(f"Loaded: {', '.join(namespace)}.", fg=typer.colors.GREEN)
    typer.echo("Top-level await works: (await session.exec(select(User))).all()")
    start_ipython(argv=[], user_ns=namespace)
    # Why: the connections were opened in IPython's event loop (the one running
    # top-level await), so they must be closed there. IPython is untyped and
    # missing from the `test` image, where this ignore is unused.
    loop = get_asyncio_loop()  # type: ignore[no-untyped-call, unused-ignore]
    loop.run_until_complete(close_shell_session(session))
