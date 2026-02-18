"""extensions

Revision ID: 765dc0a086d4
Revises:
Create Date: 2026-02-17 23:23:27.049427

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "765dc0a086d4"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create extensions"""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS ltree")
    # op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # op.execute("CREATE EXTENSION IF NOT EXISTS plpython3u")
    # op.execute("CREATE EXTENSION IF NOT EXISTS ltree_plpython3u")
    # op.execute("CREATE EXTENSION IF NOT EXISTS jsonb_plpython3u")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgres_fdw")


def downgrade() -> None:
    """Downgrade schema."""
    pass
