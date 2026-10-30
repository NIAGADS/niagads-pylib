import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from niagads.common.search.types import MatchType
from niagads.common.types import Entity
from niagads.database.genomicsdb.schema.dataset.track import (
    Track,
    TrackConcept,
    TrackContext,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex


@pytest.mark.parametrize("allow_fuzzy", [False, True])
def test_search_compiles_one_query_with_only_requested_match_paths(allow_fuzzy):
    session = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = []
    session.execute.return_value = result

    assert (
        asyncio.run(Track.search(session, "Hippocampus", allow_fuzzy=allow_fuzzy)) == []
    )

    session.execute.assert_awaited_once()
    statement = session.execute.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert "upper(dataset.track.source_id) =" in sql
    assert "unnest(dataset.track.cohorts)" in sql
    assert "upper(" in sql and ".cohort) =" in sql
    assert "dataset.track.name ILIKE" in sql
    assert "dataset.track.description ILIKE" in sql
    assert "reference.ontologyterm.term ILIKE" in sql
    assert sql.count("reference.ontologyterm.term ILIKE") == 4
    assert "dataset.trackconcept" in sql
    assert "dataset.trackcontext" in sql
    assert "synonyms" not in sql
    assert "definition" not in sql
    assert "PARTITION BY matches.track_id" in sql
    assert "ORDER BY matches.rank ASC, matches.score DESC" in sql
    assert "SELECT DISTINCT matches.track_id" in sql
    assert "HIPPOCAMPUS" in compiled.params.values()
    assert "%Hippocampus%" in compiled.params.values()
    assert ("word_similarity(" in sql) is allow_fuzzy
    assert (" %> " in sql or " %%> " in sql) is allow_fuzzy


@pytest.mark.parametrize(
    "search_text, pattern",
    [
        ("100%_signal", "%100%_signal%"),
        (r"path\name", r"%path\name%"),
    ],
)
def test_search_preserves_input_in_substring_patterns(search_text, pattern):
    session = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = []
    session.execute.return_value = result

    asyncio.run(Track.search(session, search_text))

    compiled = session.execute.call_args.args[0].compile(dialect=postgresql.dialect())
    assert pattern in compiled.params.values()
    assert "ESCAPE" not in str(compiled)
    assert search_text.upper() in compiled.params.values()


def test_search_returns_typed_track_matches_with_nullable_description():
    session = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = [
        {
            "matched_record_id": "track-a",
            "matched_record_type": "track",
            "matched_record_details": {"label": "Track A", "description": None},
            "matched_text": "ADNI",
            "match_type": "EXACT_ID",
            "rank": 0,
            "score": 1.0,
        }
    ]
    session.execute.return_value = result

    matches = asyncio.run(Track.search(session, "adni"))

    assert len(matches) == 1
    match = matches[0]
    assert match.matched_record_id == "track-a"
    assert match.matched_record_type is Entity.TRACK
    assert match.matched_record_details.label == "Track A"
    assert match.matched_record_details.description is None
    assert match.matched_text == "ADNI"
    assert match.match_type is MatchType.EXACT_ID


def test_search_propagates_database_errors():
    session = AsyncMock()
    session.execute.side_effect = RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        asyncio.run(Track.search(session, "ADNI"))


def test_search_indexes_compile_for_postgresql():
    statements = [
        str(CreateIndex(index).compile(dialect=postgresql.dialect()))
        for model in (Track, TrackConcept, TrackContext)
        for index in model.__table__.indexes
    ]

    assert any("USING gin (name gin_trgm_ops)" in sql for sql in statements)
    assert any("USING gin (description gin_trgm_ops)" in sql for sql in statements)
    assert any("(upper(source_id))" in sql for sql in statements)
    assert any(
        "dataset.trackconcept (ontology_term_id, track_id)" in sql for sql in statements
    )
    assert any(
        "dataset.trackcontext (ontology_term_id, track_id)" in sql for sql in statements
    )
