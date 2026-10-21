"""Expose retrieved trait evidence without an unsupported phenotype placeholder."""

from niagads.open_access_api.ask.contracts import ResultSet
from niagads.open_access_api.ask.results import ResultStore


def test_association_summary_exposes_traits_beyond_the_record_preview():
    store = ResultStore()
    result = store.add(
        ResultSet(
            entity="gene",
            annotation="associations",
            parameters={"gene": "APOE", "flank": 10000},
            has_more=True,
            rows=[
                {
                    "variant": f"v{i}",
                    "track": "track-a",
                    "traits": {
                        "disease": [
                            {"curie": "MONDO:0004975", "term": "Alzheimer disease"}
                        ]
                    },
                }
                for i in range(5)
            ]
            + [
                {
                    "variant": "v6",
                    "track": "track-b",
                    "traits": {
                        "disease": [
                            {"curie": "MONDO:0004975", "term": "Alzheimer disease"}
                        ],
                        "population": [{"curie": None, "term": "Korean"}],
                    },
                },
            ],
        )
    )
    summary = store.summary(result.id)
    assert "rows" not in summary
    assert len(summary["preview"]) == 5
    assert summary["association_query"] == {"gene": "APOE", "flank": 10000}
    assert summary["association_traits"] == [
        {
            "context": "disease",
            "curie": "MONDO:0004975",
            "term": "Alzheimer disease",
            "tracks": ["track-a", "track-b"],
        },
        {
            "context": "population",
            "curie": None,
            "term": "Korean",
            "tracks": ["track-b"],
        },
    ]
    assert summary["has_more"] is True


def test_api_count_summary_retains_traits_without_recounting_associations():
    store = ResultStore()
    result = store.add(
        ResultSet(
            entity="gene",
            annotation="associations",
            content="summary",
            parameters={"gene": "TREM2"},
            rows=[
                {
                    "track": "track-1",
                    "num_associations": 1200,
                    "traits": {"disease": [{"curie": None, "term": "PSP"}]},
                }
            ],
        )
    )
    summary = store.summary(result.id)
    assert summary["association_traits"][0]["term"] == "PSP"
    assert summary["preview"][0]["num_associations"] == 1200
    assert result.rows[0]["num_associations"] == 1200


def test_missing_traits_are_not_fabricated_and_missing_source_stays_explicit():
    store = ResultStore()
    result = store.add(
        ResultSet(entity="gene", annotation="associations", rows=[{"variant": "v1"}])
    )
    assert store.summary(result.id)["association_traits"] == []
    result.rows.append(
        {"variant": "v2", "traits": {"disease": [{"term": "reported trait"}]}}
    )
    assert store.summary(result.id)["association_traits"][0]["tracks"] == [None]


def test_semantic_matches_do_not_become_association_trait_evidence():
    store = ResultStore()
    result = store.add(
        ResultSet(
            entity="gene",
            annotation=None,
            rows=[{"id": "g1", "traits": {"disease": [{"term": "unverified"}]}}],
        )
    )
    assert "association_traits" not in store.summary(result.id)
