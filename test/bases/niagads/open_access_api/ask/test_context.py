"""Evidence retention and context reduction using a recorded APOE API response."""

import json
from copy import deepcopy

import pytest
from niagads.api.common.types import AnnotationKind
from niagads.common.types import Entity
from niagads.open_access_api.ask.contracts import ResultSet
from niagads.open_access_api.ask.results import ResultStore


@pytest.fixture
def gene_result(example_gene_record_mapping_response):
    return ResultSet(
        entity=Entity.GENE,
        annotation=AnnotationKind.REPORT,
        rows=example_gene_record_mapping_response["data"]["APOE"],
        parameters={"gene": "APOE"},
        sources=["ENSG00000130203"],
    )


def test_gene_summary_retains_annotation_evidence(gene_result):
    store = ResultStore()
    store.add(gene_result)
    original = deepcopy(gene_result.rows)

    summary = store.summary(gene_result.id, include_structure=False)
    preview = summary["preview"][0]
    annotations = summary["gene_annotations"][0]

    assert preview["gene_symbol"] == "APOE"
    assert preview["gene_name"] == "apolipoprotein E"
    assert preview["location"] == original[0]["location"]
    assert annotations["id"] == "ENSG00000130203"
    for field in ("functional_annotation", "memberships", "xrefs", "publications"):
        assert annotations[field] == original[0][field]
    assert "GO:0033700" in json.dumps(annotations)
    assert summary["parameters"] == {"gene": "APOE"}
    assert summary["limit"] == gene_result.limit
    assert summary["sources"] == gene_result.sources
    assert "gene_structure" not in annotations
    assert gene_result.rows == original


@pytest.mark.parametrize("include_structure", [False, True])
def test_structure_evidence_is_selective_without_changing_record(
    gene_result, include_structure
):
    structure = gene_result.rows[0]["gene_structure"]
    result = ResultSet(
        entity=Entity.GENE,
        annotation=AnnotationKind.STRUCTURE,
        rows=[structure],
        parameters={"gene": "APOE"},
    )
    store = ResultStore()
    store.add(result)
    original = deepcopy(result.rows)

    summary = store.summary(result.id, include_structure=include_structure)

    assert summary["transcript_count"] == len(structure["transcripts"])
    if include_structure:
        assert summary["transcripts"] == structure["transcripts"][:20]
        assert summary["transcripts"][0]["exons"]
        assert summary["transcripts_truncated"] == (len(structure["transcripts"]) > 20)
    else:
        assert "transcripts" not in summary
        assert "transcripts" in summary["omitted_fields"]
    assert result.rows == original
