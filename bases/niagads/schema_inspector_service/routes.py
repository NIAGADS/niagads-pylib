"""Routes for schema inspector service - business logic layer"""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from niagads.genomicsdb.schema.registry import SchemaRegistry
from niagads.schema_inspector.models import InspectionResponse, SchemaInfo
from niagads.schema_inspector.utils import get_schemas_and_tables, get_table_info
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def create_router(templates_dir: str, session_manager) -> APIRouter:
    """
    Factory function to create router with configured templates directory.

    Args:
        templates_dir (str): Path to templates directory

    Returns:
        APIRouter: Configured router with templates
    """
    router = APIRouter()
    templates = Jinja2Templates(directory=templates_dir)

    @router.get("/", response_class=HTMLResponse, summary="Display inspection form")
    async def show_form(request: Request):
        """
        Display the schema inspection form with available schemas and tables.

        Args:
            request (Request): FastAPI request object

        Returns:
            HTMLResponse: Rendered HTML form page
        """
        schemas_data = get_schemas_and_tables()
        schemas = sorted(schemas_data.keys())

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "schemas": schemas,
                "schemas_data": schemas_data,
            },
        )

    @router.post(
        "/inspect",
        response_class=HTMLResponse,
        summary="Execute table inspection query",
    )
    async def inspect_table(
        request: Request,
        schema_name: Annotated[str, Form()],
        table_name: Annotated[str, Form()],
        run_id: Annotated[int | None, Form()] = None,
        session: AsyncSession = Depends(session_manager),
    ):
        """
        Execute inspection query and display results.

        Args:
            request (Request): FastAPI request object
            schema_name (str): Schema name to query
            table_name (str): Table name to query
            run_id (int | None): Optional run_id filter
            session (AsyncSession): Database session from dependency injection

        Returns:
            HTMLResponse: Rendered results page with query data
        """
        # Get table information
        table_info = get_table_info(schema_name, table_name)

        # Build the query
        schema_base = SchemaRegistry.get_schema_base(schema_name)
        metadata = schema_base.metadata

        # Find the table
        table = None
        for tbl in metadata.sorted_tables:
            if tbl.name == table_name:
                table = tbl
                break

        if table is None:
            raise ValueError(
                f"Table '{table_name}' not found in schema '{schema_name}'"
            )

        # Build SELECT statement
        query = select(table)

        # Apply run_id filter if provided and column exists
        if run_id is not None and table_info["has_run_id"]:
            query = query.where(table.c.run_id == run_id)

        # Apply limit
        limit = 1000
        query = query.limit(
            limit + 1
        )  # Fetch one extra to detect if there are more rows

        # Execute query
        result = await session.execute(query)
        rows = result.fetchall()

        # Determine if there are more rows
        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]  # Trim to limit

        # Convert rows to dictionaries
        row_dicts = []
        for row in rows:
            row_dict = {}
            for column in table_info["columns"]:
                value = getattr(row, column, None)
                # Convert to JSON-serializable format
                if value is not None:
                    if hasattr(value, "isoformat"):  # datetime objects
                        value = value.isoformat()
                    elif isinstance(value, (list, dict)):
                        value = str(value)
                row_dict[column] = value
            row_dicts.append(row_dict)

        # Build response
        inspection_result = InspectionResponse(
            schema=table_info["schema"],
            table=table_name,
            run_id=run_id,
            row_count=len(row_dicts),
            total_rows=len(row_dicts),  # Could query count(*) separately if needed
            columns=table_info["columns"],
            rows=row_dicts,
            has_more=has_more,
            limit=limit,
        )

        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "result": inspection_result.model_dump(),
            },
        )

    @router.get(
        "/api/schemas",
        response_model=SchemaInfo,
        summary="Get available schemas and tables (API)",
    )
    async def get_schemas():
        """
        API endpoint to retrieve available schemas and their tables.

        Returns:
            SchemaInfo: Dictionary mapping schemas to table lists
        """
        schemas_data = get_schemas_and_tables()
        return SchemaInfo(schemas=schemas_data)

    return router
