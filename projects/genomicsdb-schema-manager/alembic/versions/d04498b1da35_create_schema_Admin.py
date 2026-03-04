"""Create schema Admin

Revision ID: d04498b1da35
Revises: 
Create Date: 2026-03-03 22:39:14.140587

"""

from alembic import op

revision = "d04498b1da35"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    with op.get_context().autocommit_block():
        op.execute("CREATE SCHEMA IF NOT EXISTS Admin")

def downgrade():
    op.execute("DROP SCHEMA IF EXISTS Admin CASCADE")
