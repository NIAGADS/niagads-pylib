from datetime import datetime
from typing import Any, Dict, Union

from niagads.database.mixins.serialization import ModelDumpMixin
from sqlalchemy import DATETIME, exists, func, inspect, select
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class HousekeepingMixin(object):
    """
    Mixin providing common housekeeping fields for database models:
    - run_id: Foreign key to Core.ETLLog table
    - modification_date: Timestamp of last modification
    - is_private: Boolean flag for privacy
    """

    run_id: Mapped[int] = mapped_column(
        ForeignKey("admin.etloperationslog.etl_run_id"),
        nullable=False,
        index=True,
    )
    modification_date: Mapped[datetime] = mapped_column(
        DATETIME,
        server_default=func.now(),
        nullable=False,
    )
    # is_private: Mapped[bool] = mapped_column(nullable=True, index=True)


class RecordLookupMixin:
    @classmethod
    async def exists(cls, session: AsyncSession, fields: Dict[str, Any]) -> bool:
        """
        Async check if a record exists in the table based on a dict of {field: value}.
        Example: await Model.exists(session, {"field1": value1, "field2": value2})
        """
        stmt = select(
            exists().where(*(getattr(cls, k) == v for k, v in fields.items()))
        )
        result = await session.execute(stmt)
        return result.scalar() is True

    @classmethod
    async def get_primary_key(
        cls, session: AsyncSession, fields: Dict[str, Any]
    ) -> Union[int, str, None]:
        """
        Async return the primary key value for records matching given field values.
        Returns the PK value if exactly one match is found, None if no match, and raises an error if multiple matches are found.
        Raises an error if the primary key is not a single column.
        Example: await Model.get_primary_key(session, {"field1": value1})
        """
        mapper = inspect(cls)
        if len(mapper.primary_key) != 1:
            raise ValueError(
                "get_primary_key only supports single-column primary keys."
            )
        pk_col = mapper.primary_key[0].name

        stmt = select(getattr(cls, pk_col)).where(
            *(getattr(cls, k) == v for k, v in fields.items())
        )
        result = await session.execute(stmt)
        rows = result.all()
        if not rows:
            raise NoResultFound(f"No record found for {fields} in {cls.__name__}")
        if len(rows) > 1:
            raise MultipleResultsFound(
                f"Multiple records found for {fields} in {cls.__name__}"
            )
        return rows[0][0]


class DeclarativeTableBase(
    DeclarativeBase, ModelDumpMixin, HousekeepingMixin, RecordLookupMixin
): ...


class DeclarativeMaterializedViewBase(DeclarativeBase, ModelDumpMixin): ...
