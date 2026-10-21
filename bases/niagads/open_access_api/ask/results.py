"""Run-local datasets and deterministic summaries for model/component boundaries."""

from niagads.api.common.types import AnnotationKind
from niagads.common.core import ComponentBaseMixin
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.open_access_api.ask.contracts import PresentationIntent, ResultSet


class ResultStore(ComponentBaseMixin):
    """Own authoritative results for one agent run only."""

    def __init__(self):
        super().__init__()
        self.results: dict[str, ResultSet] = {}
        self.presentations: list[PresentationIntent] = []

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
            "fields": list(dict.fromkeys(key for row in result.rows for key in row)),
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

    def validate_presentation(self, intent: PresentationIntent) -> PresentationIntent:
        """Validate evidence ownership without enforcing frontend capabilities."""
        self.get(intent.result_id)
        return intent
