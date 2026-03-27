""" "alter_processstatus_constraint"

Revision ID: 316c03b524f6
Revises: fe5af73ec715
Create Date: 2026-03-26 22:25:07.203914

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import niagads.database.decorators
import pgvector.sqlalchemy.vector
import sqlalchemy_utils.types.ltree

# revision identifiers, used by Alembic.
revision: str = "316c03b524f6"
down_revision: Union[str, None] = "fe5af73ec715"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("check_status", "etlrun", schema="admin", type_="check")
    op.alter_column(
        "etlrun",
        "status",
        existing_type=sa.Enum(
            "SUCCESS",
            "FAIL",
            "RUNNING",
            name="ProcessStatus",
            native_enum=False,
            create_constraint=False,
        ),
        type_=sa.Enum(
            "SUCCESS",
            "FAIL",
            "IN_PROGRESS",
            name="ProcessStatus",
            native_enum=False,
            create_constraint=False,
        ),
        existing_nullable=False,
        schema="admin",
    )
    op.create_check_constraint(
        "check_status",
        "etlrun",
        "status in ('SUCCESS', 'FAIL', 'IN_PROGRESS')",
        schema="admin",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("check_status", "etlrun", schema="admin", type_="check")
    op.execute(
        "UPDATE admin.etlrun SET status = 'RUNNING' WHERE status = 'IN_PROGRESS'"
    )
    op.alter_column(
        "etlrun",
        "status",
        existing_type=sa.Enum(
            "SUCCESS", "FAIL", "IN_PROGRESS", name="ProcessStatus", native_enum=False
        ),
        type_=sa.Enum(
            "SUCCESS",
            "FAIL",
            "RUNNING",
            name="ProcessStatus",
            native_enum=False,
            create_constraint=False,
        ),
        existing_nullable=False,
        schema="admin",
    )
    op.create_check_constraint(
        "check_status",
        "etlrun",
        "status in ('SUCCESS', 'FAIL', 'RUNNING')",
        schema="admin",
    )
