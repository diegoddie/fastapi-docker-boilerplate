"""${message}.

Revision ID: ${up_revision}
% if down_revision:
Revises: ${down_revision | comma,n}
% endif
Create Date: ${create_date}

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
${imports if imports else ""}

revision: str = "${str(up_revision)}"
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    """Migrate forward."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Migrate backwards."""
    ${downgrades if downgrades else "pass"}
