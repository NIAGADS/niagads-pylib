"""Create results schema(s)

Revision ID: 69d9fad432b9
Revises: 
Create Date: 2026-10-08 14:24:35.950136

"""

from alembic import op

revision = "69d9fad432b9"
down_revision = 'f7cc59350c59'
branch_labels = None
depends_on = None

def upgrade():
    with op.get_context().autocommit_block():
        op.execute("CREATE SCHEMA IF NOT EXISTS results")

def downgrade():
        op.execute("DROP SCHEMA IF EXISTS results CASCADE")
