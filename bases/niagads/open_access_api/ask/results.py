"""Run-local datasets and deterministic summaries for model/component boundaries."""

from collections.abc import Sequence

from niagads.api.common.types import AnnotationKind
from niagads.common.core import ComponentBaseMixin
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.common.types import Entity
from niagads.open_access_api.ask.contracts import PresentationIntent, ResultSet
from niagads.open_access_api.ask.planning import GeneEvidence


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

    def summary(
        self,
        result_id: str,
        *,
        gene_evidence: Sequence[GeneEvidence | str] = (),
        transcript: str | None = None,
    ) -> dict:
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
                        "gene_symbol",
                        "gene_name",
                        "gene_type",
                        "location",
                        "associated_with_known_ad_locus",
                        "name",
                        "label",
                        "variant",
                        "track",
                        "description",
                        "num_associations",
                        "is_adsp_variant",
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
            "sources": result.sources,
            "parameters": result.parameters,
            "limit": result.limit,
            "preview": preview,
            "warnings": result.warnings,
            "fields": list(dict.fromkeys(key for row in result.rows for key in row)),
        }

        requested = {GeneEvidence(field).value for field in gene_evidence}
        if requested:
            summary["evidence_fields"] = sorted(requested)
        if result.entity.value == "gene" and result.annotation == AnnotationKind.REPORT:
            annotation_fields = {
                "functional_annotation",
                "memberships",
                "xrefs",
                "publications",
            }
            selected_fields = requested & annotation_fields
            summary["omitted_fields"] = sorted(
                {
                    field
                    for row in result.rows
                    for field in row
                    if field in annotation_fields | {"gene_structure"}
                }
                - selected_fields
            )
            if selected_fields:
                summary["gene_annotations"] = [
                    {
                        "id": row.get("id"),
                        **{
                            field: row[field]
                            for field in sorted(selected_fields)
                            if field in row
                        },
                        "unavailable_fields": sorted(selected_fields - row.keys()),
                    }
                    for row in result.rows
                ]
        if (
            result.entity.value == "gene"
            and result.annotation == AnnotationKind.STRUCTURE
        ):
            transcripts = [
                item for row in result.rows for item in row.get("transcripts", [])
            ]
            summary["transcript_count"] = len(transcripts)
            summary["omitted_fields"] = ["proteins"]
            if requested & {"transcripts", "exons"}:
                selected = transcripts
                if transcript is not None:
                    summary["requested_transcript"] = transcript
                    selected = [
                        item
                        for item in transcripts
                        if transcript in (item.get("id"), item.get("name"))
                    ]
                    if not selected:
                        summary["warnings"] = [
                            *result.warnings,
                            "Requested transcript was not found in the retrieved structure.",
                        ]
                fields = (
                    ("id", "name", "location", "exons")
                    if "exons" in requested
                    else ("id", "name", "location")
                )
                summary["transcripts"] = [
                    {key: item[key] for key in fields if key in item}
                    for item in selected[:20]
                ]
                summary["transcripts_truncated"] = len(selected) > 20
                if "exons" not in requested:
                    summary["omitted_fields"].append("exons")
            else:
                summary["omitted_fields"].append("transcripts")

        if result.entity == Entity.GENE and result.annotation == AnnotationKind.REPORT:
            summary["gene_evidence"] = [
                {
                    **{
                        key: row[key]
                        for key in ("id", "associated_with_known_ad_locus")
                        if key in row
                    },
                    **{
                        key: value
                        for key, value in (row.get("memberships") or {}).items()
                        if key == "curated_lists"
                    },
                }
                for row in result.rows
            ]
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
