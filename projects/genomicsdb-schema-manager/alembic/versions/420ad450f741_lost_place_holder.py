from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import niagads.database.decorators
import pgvector.sqlalchemy.vector
import sqlalchemy_utils.types.ltree

# revision identifiers, used by Alembic.
revision: str = "420ad450f741"
down_revision: Union[str, None] = "7a08c8e32e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# this was lost due to a messed up merge
# I think it was about adding indexes for the gene table

# ran next revision on schema - all and it includes everything that should have happened
# here but was lost


def upgrade():
    None


def downgrade():
    None
