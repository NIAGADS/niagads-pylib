"""Registered dashboard capabilities; mapping rules are shared with the client."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Literal

from niagads.common.models.base import CustomBaseModel
from pydantic import ConfigDict, Field

if TYPE_CHECKING:
    from niagads.open_access_api.ask.contracts import ResultSet


TABLE_TRANSLATORS = Literal[
    "search_matches_table",
    "gene_records_table",
    "variant_records_table",
    "track_records_table",
    "associations_table",
    "association_counts_table",
]


class TableParameters(CustomBaseModel):
    model_config = ConfigDict(extra="forbid")
    columns: list[str] | None = Field(default=None, min_length=1)


class CategoryParameters(CustomBaseModel):
    model_config = ConfigDict(extra="forbid")
    group_by: str = Field(min_length=1)


class EmptyParameters(CustomBaseModel):
    model_config = ConfigDict(extra="forbid")


class PresentationBase(CustomBaseModel):
    model_config = ConfigDict(extra="forbid")
    result_id: str = Field(min_length=1)
    title: str = Field(default="Retrieved evidence", max_length=160)
    slot: Literal["primary", "secondary"] = "primary"


class TablePresentation(PresentationBase):
    translator: TABLE_TRANSLATORS
    parameters: TableParameters = Field(default_factory=TableParameters)


class CategoryCountsPresentation(PresentationBase):
    translator: Literal["category_counts_bar"] = "category_counts_bar"
    parameters: CategoryParameters


class AssociationCountsPresentation(PresentationBase):
    translator: Literal["association_counts_bar"] = "association_counts_bar"
    parameters: EmptyParameters = Field(default_factory=EmptyParameters)


Presentation = Annotated[
    TablePresentation | CategoryCountsPresentation | AssociationCountsPresentation,
    Field(discriminator="translator"),
]


def field_spec(
    id: str,
    header: str,
    type: str = "text",
    *,
    paths: list[str] | None = None,
    required: bool = False,
    categorical: bool = False,
    projection: str = "scalar",
) -> dict:
    """Describe a curated field without frontend callbacks or arbitrary paths."""
    return {
        "id": id,
        "header": header,
        "type": type,
        "paths": paths or [id],
        "required": required,
        "categorical": categorical,
        "projection": projection,
    }


TABLE_RULES = {
    "search_matches_table": {
        "entities": ["gene", "track"],
        "annotation": None,
        "content": ["full"],
        "fields": [
            field_spec("id", "Record ID", required=True),
            field_spec(
                "label", "Label", paths=["label", "matched_record_details.label"]
            ),
            field_spec(
                "description",
                "Description",
                paths=["description", "matched_record_details.description"],
            ),
            field_spec("matched_text", "Matched text"),
            field_spec("matched_record_type", "Record type", categorical=True),
            field_spec("match_type", "Match type", categorical=True),
            field_spec("rank", "Search rank", "integer"),
            field_spec("score", "Semantic similarity", "float"),
        ],
    },
    "gene_records_table": {
        "entities": ["gene"],
        "annotation": "report",
        "content": ["full"],
        "fields": [
            field_spec("id", "Gene ID", required=True),
            field_spec("gene_symbol", "Gene symbol"),
            field_spec("gene_name", "Gene name"),
            field_spec("gene_type", "Gene type", categorical=True),
            field_spec("location", "Location"),
            field_spec("synonyms", "Aliases", projection="text_list"),
            field_spec(
                "associated_with_known_ad_locus",
                "Known AD locus",
                "boolean",
                categorical=True,
            ),
        ],
    },
    "variant_records_table": {
        "entities": ["variant"],
        "annotation": "report",
        "content": ["full"],
        "fields": [
            field_spec("id", "Variant ID", required=True),
            field_spec("ref_snp_id", "RefSNP ID"),
            field_spec("chromosome", "Chromosome", categorical=True),
            field_spec("position", "Position (BP)", "integer"),
            field_spec("ref", "Reference allele"),
            field_spec("alt", "Alternate allele"),
            field_spec("variant_class", "Variant class", categorical=True),
            field_spec(
                "is_adsp_variant", "Present in ADSP", "boolean", categorical=True
            ),
            field_spec(
                "is_structural_variant",
                "Structural variant",
                "boolean",
                categorical=True,
            ),
        ],
    },
    "track_records_table": {
        "entities": ["track"],
        "annotation": "report",
        "content": ["full"],
        "fields": [
            field_spec("id", "Track ID", required=True),
            field_spec("name", "Name"),
            field_spec("description", "Description"),
            field_spec("genome_build", "Genome build", categorical=True),
            field_spec("feature_type", "Feature type", categorical=True),
            field_spec(
                "data_source",
                "Data source",
                paths=["data_source", "provenance.data_source"],
                categorical=True,
            ),
            field_spec(
                "data_category",
                "Data category",
                paths=["data_category", "experimental_design.data_category"],
                categorical=True,
            ),
            field_spec(
                "assay", "Assay", paths=["experimental_design.assay"], categorical=True
            ),
            field_spec(
                "is_download_only", "Download only", "boolean", categorical=True
            ),
            field_spec("url", "Download", "link", paths=["url", "file_properties.url"]),
        ],
    },
    "associations_table": {
        "entities": ["gene", "variant", "region", "track"],
        "annotation": "associations",
        "content": ["full"],
        "fields": [
            field_spec("variant", "Variant ID", required=True),
            field_spec("chromosome", "Chromosome", categorical=True),
            field_spec("position", "Position (BP)", "integer"),
            field_spec("ref", "Reference allele"),
            field_spec("alt", "Alternate allele"),
            field_spec("pvalue", "Reported p-value", "pvalue"),
            field_spec("neg_log10_pvalue", "−log10(p)", "float"),
            field_spec("effect_direction", "Effect direction", categorical=True),
            field_spec("test_allele", "Test allele"),
            field_spec("track", "Source track ID"),
            field_spec("traits", "Traits", projection="traits"),
        ],
    },
    "association_counts_table": {
        "entities": ["gene", "variant", "region"],
        "annotation": "associations",
        "content": ["summary"],
        "fields": [
            field_spec("track", "Source track ID", required=True),
            field_spec("num_associations", "Associations", "integer", required=True),
        ],
    },
}


def table_translator(result: ResultSet) -> str | None:
    """Resolve only explicitly supported result signatures."""
    for name, rule in TABLE_RULES.items():
        if (
            result.entity.value in rule["entities"]
            and (result.annotation.value if result.annotation else None)
            == rule["annotation"]
            and result.content.value in rule["content"]
        ):
            return name
    return None


def field_value(row: dict, field: dict) -> Any:
    """Read registered paths only; explicit null remains missing."""
    for path in field["paths"]:
        value = row
        for key in path.split("."):
            value = value.get(key) if isinstance(value, dict) else None
        if value is not None:
            return value
    return None


def validate_rows(result: ResultSet, name: str) -> None:
    """Reject values incompatible with the registered component mappings."""
    for row in result.rows:
        for field in TABLE_RULES[name]["fields"]:
            value = field_value(row, field)
            if value is None:
                if field["required"]:
                    raise ValueError(f"Missing required field {field['id']}")
                continue
            projection = field["projection"]
            field_type = field["type"]
            valid = True
            if projection == "text_list":
                valid = isinstance(value, list) and all(
                    isinstance(v, str) for v in value
                )
            elif projection == "traits":
                valid = isinstance(value, dict) and all(
                    isinstance(terms, list)
                    and all(
                        isinstance(term, dict)
                        and isinstance(term.get("term", term.get("id")), str)
                        for term in terms
                    )
                    for terms in value.values()
                )
            elif field_type in {"text", "link", "pvalue"}:
                valid = isinstance(value, str)
            elif field_type == "boolean":
                valid = isinstance(value, bool)
            elif field_type == "integer":
                valid = isinstance(value, int) and not isinstance(value, bool)
            elif field_type == "float":
                valid = (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                )
            if not valid:
                raise ValueError(f"Invalid value for {field['id']}")
            if field["id"] == "num_associations" and value < 0:
                raise ValueError("Association counts must be nonnegative integers")
