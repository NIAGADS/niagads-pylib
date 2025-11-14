from sqlalchemy import inspect, select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Union


class QueryMixin:
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
    ) -> List[Union[int, str]]:
        """
        Async return the primary key value for records matching given field values.
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
        return [row[0] for row in rows]  # list of PK values
