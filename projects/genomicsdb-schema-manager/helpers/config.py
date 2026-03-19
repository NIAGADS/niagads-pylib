from niagads.settings.core import CustomSettings


class Settings(CustomSettings):
    DATABASE_URI: str
    SCHEMA_DEFS: str = "niagads.database.genomicsdb.schema"
    PROJECT_ROOT: str
