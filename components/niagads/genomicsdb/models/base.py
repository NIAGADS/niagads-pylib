from niagads.genomicsdb.models.mixins import HousekeepingMixin, ModelDumpMixin
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class DeclarativeModelBaseFactory:
    """
    Factory for creating SQLAlchemy DeclarativeBase classes with optional schema and mixins.
    """

    @staticmethod
    def create(
        schema: str = None,
        incl_housekeeping: bool = True,
    ):
        """
        Create a DeclarativeBase class with optional schema and mixins.

        Args:
            schema (str, optional): The database schema to use for the model's metadata.
            incl_housekeeping (bool): Whether to include housekeeping fields (job_id, modification_date, is_private).

        Returns:
            DeclarativeBase: A new DeclarativeBase subclass with the requested mixins and schema.
        """
        bases = (ModelDumpMixin,)
        if incl_housekeeping:
            bases = (HousekeepingMixin,) + bases
        bases = bases + (DeclarativeBase,)

        class Base(*bases):
            if schema:
                metadata = MetaData(schema=schema)
            else:
                metadata = MetaData()

        return Base
