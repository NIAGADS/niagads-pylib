"""Run-local datasets and deterministic summaries for model/component boundaries."""

from niagads.api.common.types import AnnotationKind
from niagads.common.core import ComponentBaseMixin
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.open_access_api.ask.contracts import ResultSet
from niagads.open_access_api.ask.presentations import (
    TABLE_RULES,
    Presentation,
    table_translator,
    validate_rows,
)


class ResultStore(ComponentBaseMixin):
    """Own authoritative results for one agent run only."""

    def __init__(self):
        super().__init__()
        self.results: dict[str, ResultSet] = {}
        self.presentations: list[Presentation] = []

    def add(self, result: ResultSet) -> ResultSet:
        """Retain a result without sending its complete rows through the model."""
        if len(self.results) >= 12:
            raise RuntimeError("Result limit reached")
        self.results[result.id] = result
        return result

    def get(self, result_id: str) -> ResultSet:
        """Resolve only result IDs created by this run."""
        if result_id not in self.results:
            raise RuntimeError("Unknown result reference")
        return self.results[result_id]

    def summary(self, result_id: str) -> dict:
        """Expose identifiers and a small record preview to the agent."""
        result = self.get(result_id)
        preview = []
        for row in result.rows[:5]:
            preview.append(
                {
                    key: value
                    for key, value in row.items()
                    if key
                    in {
                        "id",
                        "name",
                        "label",
                        "variant",
                        "track",
                        "description",
                        "num_associations",
                    }
                    and isinstance(value, (str, int, float, bool))
                    and len(str(value)) <= 300
                }
            )
        summary = {
            "result_id": result.id,
            "entity": result.entity.value,
            "annotation": (result.annotation.value if result.annotation else None),
            "count": len(result.rows),
            "content": result.content.value,
            "page": result.page,
            "has_more": result.has_more,
            "sources": result.sources[:20],
            "preview": preview,
            "warnings": result.warnings,
            "presentations": self.capabilities(result_id),
        }

        if result.annotation == AnnotationKind.ASSOCIATIONS:
            summary["association_query"] = result.parameters
            summary["association_traits"] = self._association_traits(result)
        return summary

    def _association_traits(self, result: ResultSet) -> list[dict]:
        """Deduplicate reported terms with source tracks across this returned page."""
        annotations: dict[tuple[str, str | None, str], dict] = {}
        for row in result.rows:
            for context, terms in (row.get("traits") or {}).items():
                for value in terms:
                    term = OntologyTerm.model_validate(value)
                    key = (context, term.curie, term.term)
                    if key not in annotations:
                        annotations[key] = {
                            "context": context,
                            "curie": term.curie,
                            "term": term.term,
                            "tracks": {},
                        }
                    annotations[key]["tracks"][row.get("track")] = None
        return [
            {**annotation, "tracks": list(annotation["tracks"])}
            for annotation in annotations.values()
        ]

    def capabilities(self, result_id: str) -> list[dict]:
        """Advertise compatible translators and their registered field choices."""
        result = self.get(result_id)
        name = table_translator(result)
        if name is None:
            return []
        try:
            validate_rows(result, name)
        except ValueError:
            return []
        fields = TABLE_RULES[name]["fields"]
        grouping = [f["id"] for f in fields if f["categorical"]]
        capabilities = [
            {
                "translator": name,
                "columns": [f["id"] for f in fields],
                "required_columns": [f["id"] for f in fields if f["required"]],
                "group_by": grouping,
            }
        ]
        if grouping:
            capabilities.append(
                {"translator": "category_counts_bar", "group_by": grouping}
            )
        if name == "association_counts_table":
            capabilities.append({"translator": "association_counts_bar"})
        return capabilities

    def validate_presentation(self, presentation: Presentation) -> Presentation:
        """Reject selections referring to nonexistent or incompatible datasets."""
        result = self.get(presentation.result_id)
        name = table_translator(result)
        if name is None:
            raise ValueError("No registered translator supports this result")
        validate_rows(result, name)
        translator = presentation.translator
        fields = TABLE_RULES[name]["fields"]
        if translator == "category_counts_bar":
            grouping = {f["id"] for f in fields if f["categorical"]}
            if presentation.parameters.group_by not in grouping:
                raise ValueError("Grouping field is not registered for this result")
        elif translator == "association_counts_bar":
            if name != "association_counts_table":
                raise ValueError("Bar requires an association summary")
        else:
            if translator != name:
                raise ValueError("Table translator is incompatible with this result")
            columns = presentation.parameters.columns
            if columns is not None:
                allowed = {f["id"] for f in fields}
                required = {f["id"] for f in fields if f["required"]}
                if len(set(columns)) != len(columns) or not set(columns) <= allowed:
                    raise ValueError("Columns must be unique registered fields")
                if not required <= set(columns):
                    raise ValueError("Required identifier columns cannot be hidden")
        return presentation
