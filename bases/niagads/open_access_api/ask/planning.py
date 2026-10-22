"""Optional bounded interpretation within the retrieval agent's native tool loop."""

from __future__ import annotations

from typing import Annotated

from niagads.common.models.base import CustomBaseModel
from niagads.common.types import Entity
from niagads.enums.core import CaseInsensitiveEnum
from niagads.genome_reference.human import GenomeBuild
from pydantic import ConfigDict, Field
from pydantic_ai import ModelRetry, RunContext


class QueryIntent(CaseInsensitiveEnum):
    DISCOVER_RESOURCES = "discover_resources"
    RETRIEVE_DATA = "retrieve_data"
    LOOKUP_RECORD = "lookup_record"
    API_HELP = "api_help"
    CONVERSATION = "conversation"
    OTHER = "other"


class ConceptCategory(CaseInsensitiveEnum):
    ANNOTATION = "annotation"
    BIOSAMPLE = "biosample"
    SOURCE = "source"
    POPULATION = "population"
    PHENOTYPE = "phenotype"
    ASSAY = "assay"
    OTHER = "other"


class LocationKind(CaseInsensitiveEnum):
    GENE = "gene"
    SPAN = "span"
    VARIANT = "variant"


class SearchConcept(CustomBaseModel):
    """A positive user concept, not a resolved ontology term or verified match."""

    model_config = ConfigDict(extra="forbid")
    category: ConceptCategory
    text: str = Field(min_length=1, max_length=100)


class QueryLocation(CustomBaseModel):
    """An unresolved API loc input; omitted flank and assembly stay unspecified."""

    model_config = ConfigDict(extra="forbid")
    kind: LocationKind
    loc: str = Field(min_length=1, max_length=128)
    flank_bp: int | None = Field(default=None, ge=0)
    assembly: GenomeBuild | None = None


class QueryClarification(CustomBaseModel):
    """A missing or ambiguous interpretation that would change retrieval."""

    model_config = ConfigDict(extra="forbid")
    field: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=160)


class GeneEvidence(CaseInsensitiveEnum):
    FUNCTIONAL_ANNOTATION = "functional_annotation"
    MEMBERSHIPS = "memberships"
    XREFS = "xrefs"
    PUBLICATIONS = "publications"
    TRANSCRIPTS = "transcripts"
    EXONS = "exons"


class QueryPlan(CustomBaseModel):
    """Compact interpretation; not a workflow, capability declaration or evidence."""

    model_config = ConfigDict(extra="forbid")
    intent: QueryIntent
    goal: str = Field(min_length=1, max_length=320)
    entity: Entity | None = Field(
        default=None,
        description=(
            "Requested record type: tracks are datasets; collections group datasets."
        ),
    )
    concepts: list[SearchConcept] = Field(default_factory=list, max_length=6)
    constraints: list[Annotated[str, Field(min_length=1, max_length=160)]] = Field(
        default_factory=list, max_length=6
    )
    location: QueryLocation | None = None
    clarifications: list[QueryClarification] = Field(default_factory=list, max_length=2)
    exclusions: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list, max_length=4
    )
    gene_evidence: list[GeneEvidence] = Field(default_factory=list, max_length=6)
    tool_names: list[Annotated[str, Field(min_length=1, max_length=80)]] | None = Field(
        default=None, max_length=20, exclude=True
    )


PLANNING_INSTRUCTIONS = """Planning is optional; clear requests can retrieve directly.
For multi-step work, use tool_names in record_query_plan to select only tools
needed for the whole request, including dependencies and presentation. Choose
from registered tool names, not biological identifiers. The server then sends
only those tool definitions on subsequent calls. record_query_plan and
clarify_request always remain available. Update tool_names if new evidence
requires another capability; null restores the full catalog. Do not narrow
the user's request to match a selected tool set. Selecting tools is optional
and must not add a planning call to a request that needs no interpretation.
Use record_query_plan when decomposition of concepts, compound AND/OR constraints,
exclusions or scope materially helps. Resolve identifiers through tools first when
actual records are needed to interpret the next action. Preserve the whole goal,
including multiple evidence types, rather than narrowing it to one entity.
Record only a compact goal, useful flat concepts/constraints, unresolved scope and
necessary clarification/evidence hints. No recursive workflow or long reasoning.
Keep uncertain coordinates, IDs, assembly and distances unresolved; never invent
inputs or capabilities. Do not silently discard constraints to fit schema bounds.
The original request and returned evidence govern subsequent actions, not the
interpretation. Unsupported constraints must be reported as unapplied. Resource
exclusions, multi-concept resource filtering and location-aware track retrieval
are not implemented. Gene evidence fields can be selected later on each tool call;
transcript locations do not need exons. Clarify only material unresolved ambiguity.
Associations are annotations; variants are genomic entities that can be annotated,
not annotations themselves. A request for variant associations asks for association
evidence, not all variants. Represent associations as an annotation concept and
keep the gene, variant or region defining scope in location. Do not turn a locus
name into a request for gene records. For 'Plot all variant associations reported
for the BIN1 locus, grouped by population and disease or neuropathology', use
intent retrieve_data, annotation concept associations and location kind gene with
loc BIN1. Population and disease or neuropathology are grouping dimensions here,
not selection constraints without requested values.
"""


async def record_query_plan(ctx: RunContext[dict], interpretation: QueryPlan) -> dict:
    """Record validated scope when useful; never a prerequisite for retrieval.

    Native tool argument validation rejects invalid interpretations before this
    function runs. Validation exhaustion retains the native error and any results
    already retrieved; it does not fabricate a plan or silently switch strategies.
    """
    if interpretation.tool_names is not None:
        catalog = ctx.deps["_ask_tool_catalog"]
        unknown = set(interpretation.tool_names) - catalog
        if unknown:
            raise ModelRetry("Unknown tool names: " + ", ".join(sorted(unknown)))
    ctx.deps["query_plan"] = interpretation
    if interpretation.exclusions:
        ctx.deps["warnings"].append("Requested exclusions have not been applied.")
    report_plan = ctx.deps.get("report_plan")
    if report_plan is not None:
        report_plan(interpretation)
    result = {
        "status": "recorded",
        "interpretation": interpretation.model_dump(mode="json"),
    }
    if interpretation.tool_names is not None:
        result["tool_names"] = interpretation.tool_names
    return result
