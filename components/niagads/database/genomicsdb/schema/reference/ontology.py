"""
SQLAlchemy ORM table definitions for ontology term reference tables.

Enables foreign key references from other tables to ontology terms.
Intended for use alongside the ontology graph schema for comprehensive ontology support.
"""

from typing import Union

from niagads.common.models.base import CustomBaseModel
from niagads.common.reference.ontologies.types import EntityTypeIRI
from niagads.common.search.models.record import SearchResultRecord
from niagads.common.search.types import MatchType
from niagads.common.types import Entity
from niagads.database.genomicsdb.schema.mixins import IdAliasMixin, SearchMixin
from niagads.database.genomicsdb.schema.reference.base import ReferenceTableBase
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from niagads.database.helpers import enum_column, enum_constraint
from niagads.utils.string import jaccard_word_similarity
from sqlalchemy import (
    TEXT,
    Boolean,
    Index,
    String,
    UniqueConstraint,
    and_,
    column,
    func,
    literal,
    or_,
    select,
    true,
    union,
    values,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column


class OntologyTermValidation(CustomBaseModel):
    valid: dict[tuple[str | None, str | None], dict]
    not_matched: list[dict]
    multiple_matches: list[dict]


class OntologyTerm(
    ReferenceTableBase, ExternalDatabaseMixin, IdAliasMixin, SearchMixin
):
    __tablename__ = "ontologyterm"
    _stable_id = "source_id"

    # moved below field definitions so we can reference synonyms in the index constructor
    __table_args__ = (
        *ExternalDatabaseMixin.__table_args__,
        UniqueConstraint("source_id", name="uq_ontology_term_id"),
        enum_constraint("entity_type", EntityTypeIRI, use_enum_names=True),
        # trgm indexes for fuzzy querying
        Index(
            "ix_ontology_term_term_trgm",
            "term",
            postgresql_using="gin",
            postgresql_ops={"term": "gin_trgm_ops"},
        ),
        Index(
            "ix_ontology_term_definition_trgm",
            "definition",
            postgresql_using="gin",
            postgresql_ops={"definition": "gin_trgm_ops"},
        ),
        # conditional trgm index on synonyms that concatenates all synonyms to gether
        Index(
            "ix_ontology_term_synonyms_trgm",
            "synonym_list_str",
            postgresql_using="gin",
            postgresql_ops={
                "synonym_list_str": "gin_trgm_ops",
            },
        ),
        ReferenceTableBase.__table_args__,
    )

    ontology_term_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    namespace: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    term: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    term_iri: Mapped[str] = mapped_column(String(250), index=False, nullable=False)
    entity_type: Mapped[str] = enum_column(EntityTypeIRI, use_enum_names=True)
    label: Mapped[str] = mapped_column(String(512), nullable=True)
    definition: Mapped[str] = mapped_column(TEXT, nullable=True)
    synonyms: Mapped[list[str]] = mapped_column(ARRAY(String(250)), nullable=True)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, nullable=True)

    # have to create this column (concenation of synonyms into a list) b/c
    # postgres treats array_to_string as stable, not immutable so can't index on it
    synonym_list_str: Mapped[str] = mapped_column(TEXT, nullable=True)

    # overloading from ExternalDatabaseMixin b/c cell ontology has some long ones
    source_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)

    @hybrid_property
    def curie(self):
        return self.source_id

    @curie.expression
    def curie(cls):
        return cls.source_id

    # -------------------------
    # Search
    # -------------------------

    @classmethod
    async def search(
        cls,
        session: AsyncSession,
        search_text,
        *,
        allow_fuzzy: bool = True,
        include_ontology: list[str] = None,
        exclude_ontology: list[str] = None,
    ) -> SearchResultRecord:

        # exact matches
        exact_term_match_cte = cls._build_match_cte(
            "exact_term_match",
            MatchType.EXACT_ID,
            OntologyTerm.term,
            OntologyTerm.term.ilike(search_text),
        )

        curies = [search_text.upper(), search_text.replace("_", ":").upper()]
        exact_curie_match_cte = cls._build_match_cte(
            "exact_curie_match",
            MatchType.EXACT_ID,
            OntologyTerm.source_id,
            func.upper(OntologyTerm.source_id).in_(curies),
        )

        # Expose `unnest(synonyms)` as a lateral table with a PostgreSQL-recognized `term` column.
        # this will allow us to return exactly which synonym was matched
        synonyms = (
            func.unnest(OntologyTerm.synonyms)
            .table_valued("term")
            .render_derived()
            .lateral()
        )
        exact_synonym_match_cte = cls._build_match_cte(
            "exact_synonym_match",
            MatchType.EXACT_SYNONYM,
            synonyms.c.term,
            synonyms.c.term.ilike(search_text),
            join_clause=(synonyms, true()),
        )

        wildcard_phrase = f"%{search_text}%"
        partial_term_match_cte = cls._build_match_cte(
            "partial_term_match",
            MatchType.PARTIAL_ID,
            OntologyTerm.term,
            OntologyTerm.term.ilike(wildcard_phrase),
        )

        partial_synonym_match_cte = cls._build_match_cte(
            "partial_synonym_match",
            MatchType.PARTIAL_SYNONYM,
            synonyms.c.term,
            synonyms.c.term.ilike(wildcard_phrase),
            join_clause=(synonyms, true()),
        )

        partial_definition_match_cte = cls._build_match_cte(
            "partial_annotation_match",
            MatchType.PARTIAL_DESCRIPTIVE,
            OntologyTerm.definition,
            OntologyTerm.definition.ilike(wildcard_phrase),
        )

        # fuzzy matches
        fuzzy_term_match_cte = cls._build_match_cte(
            "fuzzy_term_match",
            MatchType.FUZZY_ID,
            OntologyTerm.term,
            and_(
                OntologyTerm.term.op("%")(search_text),
                func.similarity(OntologyTerm.term, search_text) >= 0.5,
            ),
            score=func.similarity(OntologyTerm.term, search_text),
        )

        fuzzy_definition_match_cte = cls._build_match_cte(
            "fuzzy_definition_match",
            MatchType.FUZZY_DESCRIPTIVE,
            OntologyTerm.definition,
            and_(
                OntologyTerm.definition.op("%")(search_text),
                func.similarity(OntologyTerm.definition, search_text) >= 0.5,
            ),
            score=func.similarity(OntologyTerm.definition, search_text),
        )

        # the index on the synonyms column is to a concatenated string array
        # so we need to trgm match to whole array, but calculate
        # matched_text and score based on indivdiual synoynms
        # filter result (second where) for trgm matches against this
        # subset of synonyms
        fuzzy_synonym_match_cte = cls._build_match_cte(
            "fuzzy_synonym_match",
            MatchType.FUZZY_SYNONYM,
            synonyms.c.term,
            and_(
                # pre-filter (before join)
                OntologyTerm.synonym_list_str.op("%")(search_text),
                func.similarity(synonyms.c.term, search_text) >= 0.5,
            ),
            score=func.similarity(synonyms.c.term, search_text),
            join_clause=(synonyms, true()),
            post_action=lambda s: s.where(
                synonyms.c.term.op("%")(search_text)
            ).distinct(),
        )

        # UNION CTE across the types of searches
        if allow_fuzzy:
            matches_cte = union(
                select(exact_term_match_cte),
                select(exact_curie_match_cte),
                select(exact_synonym_match_cte),
                select(partial_term_match_cte),
                select(partial_synonym_match_cte),
                select(partial_definition_match_cte),
                select(fuzzy_term_match_cte),
                select(fuzzy_synonym_match_cte),
                select(fuzzy_definition_match_cte),
            ).cte("matches")
        else:
            matches_cte = union(
                select(exact_term_match_cte),
                select(exact_curie_match_cte),
                select(exact_synonym_match_cte),
                select(partial_term_match_cte),
                select(partial_synonym_match_cte),
                select(partial_definition_match_cte),
            ).cte("matches")

        # windowing functons to find the top ranked/scored hit per matching term
        # e.g., so that if a match is found to a term and its synonym, it is reported
        # correctly
        match_sort_order = (
            matches_cte.c.rank.asc(),
            matches_cte.c.score.desc(),
        )

        rank = (
            func.first_value(matches_cte.c.rank).over(
                partition_by=matches_cte.c.source_id, order_by=match_sort_order
            )
            - 1
        ).label("rank")

        score = (
            func.first_value(matches_cte.c.score)
            .over(partition_by=matches_cte.c.source_id, order_by=match_sort_order)
            .label("score")
        )

        match_type = (
            func.first_value(matches_cte.c.match_type)
            .over(partition_by=matches_cte.c.source_id, order_by=match_sort_order)
            .label("match_type")
        )

        matched_text = (
            func.first_value(matches_cte.c.matched_text.cast(String))
            .over(
                partition_by=matches_cte.c.source_id,
                order_by=match_sort_order,
            )
            .cast(String)
            .label("matched_text")
        )

        stmt = select(
            matches_cte.c.source_id.label("record_id"),
            matches_cte.c.external_database_id,
            func.jsonb_build_object(
                "label",
                matches_cte.c.term,
                "description",
                matches_cte.c.definition,
                "annotation",
                func.jsonb_build_object(
                    "iri",
                    matches_cte.c.term_iri,
                    "synonyms",
                    matches_cte.c.synonyms,
                ),
            ).label("record_details"),
            literal(str(Entity.ONTOLOGY_TERM)).label("record_type"),
            rank,
            score,
            matched_text,
            match_type,
        )

        # optionally filter for specific ontologies
        if include_ontology or exclude_ontology:
            filter_conditions = []

            if include_ontology:
                filter_conditions.append(
                    func.upper(ExternalDatabase.database_key).in_(
                        [ontology.upper() for ontology in include_ontology]
                    )
                )

            if exclude_ontology:
                filter_conditions.append(
                    func.upper(ExternalDatabase.database_key).notin_(
                        [ontology.upper() for ontology in exclude_ontology]
                    )
                )

            matches_subquery = stmt.subquery("matches")
            stmt = (
                select(matches_subquery)
                .join(
                    ExternalDatabase,
                    ExternalDatabase.external_database_id
                    == matches_subquery.c.external_database_id,
                )
                .where(and_(*filter_conditions))
                .distinct()
                .order_by(
                    matches_subquery.c.rank.asc(), matches_subquery.c.score.desc()
                )
            )

        else:
            stmt = stmt.distinct().order_by(rank.asc(), score.desc())

        # DEBUG - for optimizing the sql, prints with binds embedded
        # print("--------------QUERY-------------")
        # print(DatabaseSessionManager.compile_select_statement(stmt))
        # print("--------------------------------")

        result = await session.execute(stmt)
        rows = result.mappings().all()

        # if no matches will get one result with all fields except literals as NULL
        # if we filter for those, an empty result should be returned as []
        return [SearchResultRecord(**r) for r in rows if r["record_id"] is not None]

    @classmethod
    async def semantic_search(OntologyTerm, session, phrase, embed, *, limit=10):
        raise NotImplementedError()

    @classmethod
    async def semantic_search_by_embedding(
        cls, session, phrases, embeddings, *, limit=10
    ):
        raise NotImplementedError()

    # -------------------------
    # Term Lookups
    # -------------------------

    @classmethod
    async def validate_terms(
        cls,
        session: AsyncSession,
        terms: list[dict],
    ) -> OntologyTermValidation:
        """Validate ontology terms against the reference database.

        Args:
            session: SQLAlchemy async session used to resolve ontology terms.
            terms: Lookup dictionaries containing optional ``term`` and ``curie``
                values.

        """
        lookup_rows = []
        lookups = {}
        for lookup in terms:
            key = (lookup["term"], lookup["curie"])
            lookup_rows.append(key)
            lookups[key] = lookup

        lookup_values = values(
            column("lookup_term", String),
            column("lookup_curie", String),
            name="ontology_term_lookups",
        ).data(lookup_rows)

        stmt = select(
            lookup_values.c.lookup_term,
            lookup_values.c.lookup_curie,
            OntologyTerm.ontology_term_id,
            OntologyTerm.term.label("db_term"),
            OntologyTerm.source_id.label("db_curie"),
        ).select_from(
            lookup_values.outerjoin(
                OntologyTerm,
                or_(
                    and_(
                        lookup_values.c.lookup_curie.is_not(None),
                        OntologyTerm.source_id == lookup_values.c.lookup_curie,
                    ),
                    and_(
                        lookup_values.c.lookup_curie.is_(None),
                        OntologyTerm.term == lookup_values.c.lookup_term,
                    ),
                ),
            )
        )

        rows = (await session.execute(stmt)).mappings().all()

        valid = {}
        not_matched = []
        multiple_matches = {}

        for row in rows:
            key = (row["lookup_term"], row["lookup_curie"])
            lookup = lookups[key]
            term = lookup["term"]
            curie = lookup["curie"]

            if row["db_curie"] is None:
                error = "curie_not_found" if curie is not None else "term_not_found"
                not_matched.append({"lookup": lookup, "error": error})
            elif curie is None:
                match = {
                    "term": row["db_term"],
                    "curie": row["db_curie"],
                    "ontology_term_id": row["ontology_term_id"],
                }
                if key in multiple_matches:
                    multiple_matches[key]["matches"].append(match)
                elif key in valid:
                    multiple_matches[key] = {
                        "lookup": lookup,
                        "matches": [valid.pop(key), match],
                    }
                else:
                    valid[key] = match
            elif term is not None and row["db_term"] != term:
                not_matched.append(
                    {
                        "lookup": lookup,
                        "error": "term_does_not_match_curie",
                        "match": {
                            "term": row["db_term"],
                            "curie": row["db_curie"],
                            "ontology_term_id": row["ontology_term_id"],
                        },
                    }
                )
            else:
                valid[key] = {
                    "term": row["db_term"],
                    "curie": row["db_curie"],
                    "ontology_term_id": row["ontology_term_id"],
                }

        return OntologyTermValidation(
            valid=valid,
            not_matched=not_matched,
            multiple_matches=list(multiple_matches.values()),
        )

    @classmethod
    async def find_primary_key(
        cls,
        session: AsyncSession,
        term: str = None,
        curie: str = None,
        external_database_id: int = None,
        search_synonyms: bool = False,
        allow_multiple: bool = False,
    ):
        """wrapper for TransactionTable `find_primary_key` that allows searching of synonyms"""
        filters: dict = {}
        if term is not None:
            filters["term"] = term
        if curie is not None:
            filters["source_id"] = curie
        if len(filters) == 0:
            raise ValueError(
                "Must provide at least one of `term` or `curie` to look up an ontology term"
            )

        if external_database_id is not None:
            filters["external_database_id"] = external_database_id

        if not search_synonyms:
            return await super().find_primary_key.__func__(
                cls, session, filters=filters
            )
        else:
            if term is None:
                raise ValueError("Can only match synonyms if a `term` is provided.")
            stmt = select(OntologyTerm.ontology_term_id).where(
                OntologyTerm.synonyms.contains([term])
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            if not rows:
                raise NoResultFound(
                    f"No record found for {filters} in {cls.table_name()}"
                )
            if len(rows) > 1:
                if allow_multiple:
                    return rows
                else:
                    raise MultipleResultsFound(
                        f"Multiple records found for {filters} in {cls.table_name()}"
                    )
            return rows[0]

    @classmethod
    async def retrieve_term_pk_mapping(
        cls,
        session: AsyncSession,
        ontology_ref: Union[str, int],
        map_thru_term: bool = False,
    ):
        """Retrieve a mapping of Ensembl gene source IDs to primary key gene IDs.

        Args:
            session (AsyncSession): SQLAlchemy async session for database access.
            ontology_ref (str, int): Ontology reference.  Can be namespace (str) or external_database_id (int)
            map_thru_term (optional, bool): When True, map term (& synonyms) -> PK, When False map curie -> PK.  Defaults to False

        Returns:
            dict[str, int]: Mapping from lookup value to ontology_term_id (primary key).

        """

        if isinstance(ontology_ref, int):
            external_database_id: int = ontology_ref
        else:
            external_database_id: int = await ExternalDatabase.find_primary_key(
                session, filters={"database_key": ontology_ref}
            )

        mapping = {}
        if not map_thru_term:
            stmt = select(OntologyTerm.ontology_term_id, OntologyTerm.curie).where(
                OntologyTerm.external_database_id == external_database_id
            )
            records = (await session.execute(stmt)).all()
            for ontology_term_id, curie in records:
                mapping[curie] = ontology_term_id
        else:
            # also need to do labels and synonyms
            stmt = select(
                OntologyTerm.ontology_term_id,
                OntologyTerm.term,
                OntologyTerm.synonyms,
            ).where(OntologyTerm.external_database_id == external_database_id)
            records = (await session.execute(stmt)).all()

            # FIXME - raise an error?
            for ontology_term_id, term, synonyms in records:
                mapping[term] = ontology_term_id

                # these may introduce duplicates
                # give term priority
                if synonyms is not None:
                    for syn in synonyms:
                        if syn in mapping:
                            continue
                        mapping[syn] = ontology_term_id

        return mapping

    # -------------------------
    # Duplicate Term Handlers
    # -------------------------

    async def in_namespace(self, session: AsyncSession, namespace: str) -> bool:
        """
        Check if this term's IRI starts with the given namespace.

        Args:
            namespace (str): The namespace to check; may be an ontology code

        Returns:
            bool: True if term_iri starts with namespace, else False.
        """
        if namespace.startswith("http"):
            return self.term_iri.startswith(namespace)
        else:  # assume namespace ==  ontology code
            ontology: ExternalDatabase = await ExternalDatabase.fetch_record(
                session, {"external_database_id": self.external_database_id}
            )
            return ontology.database_key == namespace

    async def _update_definition(self, session: AsyncSession, definition: str) -> bool:
        self.definition = definition
        await self.update(session)
        return True

    async def resolve_synonyms(
        self, session: AsyncSession, new_synonyms: list[str]
    ) -> bool:
        """
        Merge new synonyms with existing synonyms, removing duplicates.

        Args:
            session (AsyncSession): SQLAlchemy async session.
            new_synonyms (list[str]): New synonym strings to merge.

        Returns:
            bool: True if synonyms were updated, False if new_synonyms was empty.
        """
        if not new_synonyms:
            return False
        if not self.synonyms:
            self.synonyms = sorted(new_synonyms)
        else:
            self.synonyms = sorted(list(set(self.synonyms) | set(new_synonyms)))

        await self.update(session)
        return True

    async def resolve_definition(
        self, session: AsyncSession, new_definition: str, namespace: str
    ) -> bool:
        """
        Select the preferred definition for a duplicate ontology term.

        Prefers the new definition if it comes from the source ontology. Otherwise,
        selects the new definition if it is sufficiently different and longer.
        If only one definition is present, returns the new one.

        Args:
            new_definition (str): Candidate definition string.
            namespace (str): Source ontology namespace for the new definition.

        Returns:
            True if definition was updated.  False otherwise.
        """
        if not new_definition:
            return False

        if not self.definition:
            return await self._update_definition(session, new_definition)

        # checking here to avoid the namespace lookup
        # unless necessary
        if new_definition == self.definition:
            return False  # no update needed

        # Prefer new if it comes from the source ontology for the term
        if await self.in_namespace(session, namespace):
            return await self._update_definition(session, new_definition)

        # otherwise, assume more comprehensive definition is correct
        similarity = jaccard_word_similarity(new_definition, self.definition)
        is_longer = len(new_definition) > len(self.definition)
        if similarity < 0.5 and is_longer:
            return await self._update_definition(session, new_definition)

        # Otherwise, keep existing
        return False
