from niagads.database.core import DeclarativeModelBaseFactory

GeneSchemaBase = DeclarativeModelBaseFactory.create(schema="gene", housekeeping=True)
