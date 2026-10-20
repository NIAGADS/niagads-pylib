"""Run-local datasets and deterministic summaries for model/component boundaries."""

from niagads.api.common.types import ResponseContent
from niagads.common.core import ComponentBaseMixin
from niagads.open_access_api.ask.contracts import (
    SOURCE_CHART_TYPES,
    Presentation,
    ResultSet,
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
            raise ValueError("Result limit reached")
        self.results[result.id] = result
        return result

    def get(self, result_id: str) -> ResultSet:
        """Resolve only result IDs created by this run."""
        if result_id not in self.results:
            raise ValueError("Unknown result reference")
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
        return {
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
        }

    def validate_presentation(self, presentation: Presentation) -> Presentation:
        """Reject components referring to nonexistent or incompatible datasets."""
        result = self.get(presentation.result_id)
        if presentation.component == "association_source_bar":
            if (
                result.entity,
                result.annotation,
            ) not in SOURCE_CHART_TYPES or result.content != ResponseContent.SUMMARY:
                raise ValueError("Source chart requires an association summary")
        return presentation
