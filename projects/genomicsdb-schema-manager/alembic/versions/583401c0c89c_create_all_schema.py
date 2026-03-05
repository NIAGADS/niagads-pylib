"""Create all schema(s)

Revision ID: 583401c0c89c
Revises: 
Create Date: 2026-03-04 20:03:24.683309

"""

from alembic import op

revision = "583401c0c89c"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    with op.get_context().autocommit_block():
        op.execute("CREATE SCHEMA IF NOT EXISTS gene")
        op.execute("CREATE SCHEMA IF NOT EXISTS ragdoc")
        op.execute("CREATE SCHEMA IF NOT EXISTS reference")
        op.execute("CREATE SCHEMA IF NOT EXISTS admin")
        op.execute("CREATE SCHEMA IF NOT EXISTS dataset")

def downgrade():
        op.execute("DROP SCHEMA IF EXISTS gene CASCADE")
        op.execute("DROP SCHEMA IF EXISTS ragdoc CASCADE")
        op.execute("DROP SCHEMA IF EXISTS reference CASCADE")
        op.execute("DROP SCHEMA IF EXISTS admin CASCADE")
        op.execute("DROP SCHEMA IF EXISTS dataset CASCADE")
