"""
Parameter mixin classes for GenomicsDB ETL plugins.

This module provides reusable mixins for handling plugin parameters in
GenomicsDB ETL workflows. Mixins defined here encapsulate parameter validation
and parsing for plugin development. Intended for use by
plugin authors to standardize common parameter handling across ETL plugin
implementations.

See project documentation for usage patterns and integration details.
"""

from niagads.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches
from pydantic import BaseModel, field_validator


class ExternalDatabaseRef(BaseModel):
    """
    Pydantic model for an external database reference.

    Attributes:
        name (str): Name of the external database.
        version (str): Version of the external database.
    """

    name: str
    version: str

    @classmethod
    def from_xdbref(cls, xdbref: str):
        """
        Create an ExternalDatabaseRef from a validated `name|version` (`xdbref`) string.

        Args:
            xdbref (str): The external database reference string in the format `name|version`.

        Returns:
            ExternalDatabaseRef: Instance with name and version populated.
        """
        name, version = xdbref.rsplit("|", 1)
        return cls(name=name, version=version)


class ExternalDatabaseRefMixin:
    """
    Mixin for handling external database reference parameters in ETL plugins.

    Attributes:
        xdbref (str): External database reference string in the format 'name|version'.
    """

    xdbref: str

    @field_validator("xdbref")
    def validate_xdbref_format(cls, value):
        if not matches(RegularExpressions.EXTERNAL_DATABASE_REF, value):
            raise ValueError(
                "`xdbref` must be in the format <name>|<version> (name can have spaces, version cannot)"
            )
        return value

    def xdbref_to_dict(self) -> ExternalDatabaseRef:
        """
        Split the xdbref string into name and version components.

        Returns:
            ExternalDatabseRef
        """
        return ExternalDatabaseRef.from_xdbref(self.xdbref).model_dump()

    def resolve_xdbref(self, session):
        """
        Verify that the xdbref matches to the database and
        return the primary key for the external database reference.

        Args:
            session: Database session/connection object.

        Returns:
            The primary key for the external database reference as returned by
            ExternalDatabase.get_primary_key.

        Raises:
            sqlalchemy.exc.NoResultFound: If no record is found for the xdbref.
            sqlalchemy.exc.MultipleResultsFound: If multiple records are found for the xdbref.

        References:
            See QueryMixin.get_primary_key for implementation details and error handling.
        """
        return ExternalDatabase.get_primary_key(session, self.xdbref_to_dict())
