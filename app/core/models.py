"""
The core models.

Every table model must be imported here: Alembic autogenerate and the test
database setup import this module to populate ``SQLModel.metadata``.
"""

import app.commons.models  # noqa: F401  # side-effect: constraint naming convention

__all__: list[str] = []
