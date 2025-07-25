from typing import Any, Callable, Dict, List, Optional, Union
from niagads.api_common.models.records import Entity
from pydantic import BaseModel
from sqlalchemy import bindparam, text


class QueryFilter(BaseModel):
    field: str
    value: Union[str, int, bool, float]
    operator: str


class PreparedStatement(BaseModel):
    query: str
    bind_parameters: List[str]

    def build(self, parameters: Dict[str, Any], id_parameter: str):
        statement = text(self.query)
        bind_parameters = [
            bindparam(
                param,
                (
                    parameters.get(id_parameter)
                    if param == "id"
                    else parameters.get(param)
                ),
            )
            for param in self.bind_parameters
        ]

        statement = statement.bindparams(*bind_parameters)
        return statement


class QueryDefinition(BaseModel):
    query: Optional[str] = None
    counts_query: Optional[str] = None

    # function that takes a query result and calculates counts
    counts_func: Callable = None

    use_id_select_wrapper: bool = False
    allow_filters: bool = False  # if filter param is present, add filter wrapper
    fetch_one: bool = False  # always return exactly one result
    json_field: Optional[str] = None  # only return specific field, can be dynamic
    bind_parameters: Optional[List[str]] = None  # bind parameter names
    allow_empty_response: bool = False

    entity: Optional[Entity] = None  # for messaging

    def model_post_init(self, __context):
        if self.use_id_select_wrapper:
            self.query = "SELECT * FROM (" + self.query + ") q WHERE id = :id"
            if self.bind_parameters is not None:
                self.bind_parameters.append("id")
            else:
                self.bind_parameters = ["id"]
        if self.json_field:
            self.query = "SELECT {field} FROM (" + self.query + ") q"

    def get_filter_query(self, filter: QueryFilter):
        # do not fill in filter.value; leave for prepared statement using the bind parameter for security
        return f"SELECT * FROM ({self.query}) q WHERE {filter.field} {filter.operator} :{filter.field}"

    def get_counts_statement(self, filter: QueryFilter = None) -> str:
        """get/build the counts-only query
        implementing this as a function so it can be overridden for complex cases; i.e. if aggregation
        or filtering are needed
        """

        is_filtered = self.allow_filters and filter is not None

        if self.counts_query != None:
            return PreparedStatement(query=self.counts_query, bind_parameters=["id"])

        else:
            query = self.get_filter_query(filter) if is_filtered else self.query
            params = self.bind_parameters
            if is_filtered:
                params.append(filter.field)
            return PreparedStatement(
                query=f"SELECT count(*) AS result_size FROM ({query}) r",
                bind_parameters=params,
            )
