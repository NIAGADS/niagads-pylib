## print diff in metadata schema when model compared to database
## test script
import pprint

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from database.genomicsdb.schemas import Schema
from database.config import Settings

metadata: Schema = Schema.base("metadata").metadata
engine = create_engine(Settings.from_env().DATABASE_URI)

mc = MigrationContext.configure(engine.connect())

diff = compare_metadata(mc, metadata)
pprint.pprint(diff, indent=2, width=20)
