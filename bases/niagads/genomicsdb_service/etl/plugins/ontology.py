"""
Generic ETL plugin for loading ontology data from OWL files into the NIAGADS ontology graph schema.

- Parses OWL files (RDF/XML format) and extracts ontology terms, relationships, and metadata.
- Loads terms and relationships into the Reference.Ontology tables using SQLAlchemy.
- Not specific to any ontology; works with any OWL file conforming to standard structure.
"""

from enum import auto
from typing import Any, Dict, Optional, Type, List
from niagads.enums.core import CaseInsensitiveEnum
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.genomicsdb.models.admin.pipeline import ETLOperation
from pydantic import Field, BaseModel, field_validator
from rdflib import Graph, URIRef, RDFS, OWL
from rdflib.namespace import RDF
from sqlalchemy.orm import Session
from sqlalchemy import text

# Ontology OWL constants
IAO_DEFINITION_URI = "http://purl.obolibrary.org/obo/IAO_0000115"
OBOINOWL_EXACT_SYNONYM_URI = (
    "http://www.geneontology.org/formats/oboInOwl#hasExactSynonym"
)
OBOINOWL_IS_OBSOLETE_URI = "http://www.geneontology.org/formats/oboInOwl#is_obsolete"
OBOINOWL_REPLACED_BY_URI = "http://www.geneontology.org/formats/oboInOwl#replaced_by"


class OntologyTermRecord(BaseModel):
    term_id: str
    label: str = ""
    definition: str = ""
    synonyms: List[str] = []
    is_obsolete: bool = False
    replaced_by: str = ""
    term_kind: str

    @field_validator("synonyms", mode="before")
    @classmethod
    def ensure_list(cls, v):
        return v if isinstance(v, list) else [v] if v else []


class OntologyTermKind(CaseInsensitiveEnum):
    CLASS = auto()
    PROPERTY = auto()
    INDIVIDUAL = auto()

    @classmethod
    def from_rdf_type(cls, rdf_type):
        if rdf_type == OWL.Class:
            return str(cls.CLASS)
        elif rdf_type == OWL.Property:
            return str(cls.PROPERTY)
        elif rdf_type == OWL.NamedIndividual:
            return str(cls.INDIVIDUAL)
        else:
            raise ValueError(
                f"Unrecognized term type: {rdf_type}.  Expected one of {cls.list()}"
            )

    def __str__(self):
        return self.value.lower()


class OntologyLoaderParams(BasePluginParams, PathValidatorMixin):
    file: str = Field(description="Full path to the OWL file to load.")

    validate_file_exists = PathValidatorMixin.validator("file", is_dir=False)


@PluginRegistry.register(metadata={"version": 1.0})
class OntologyLoader(AbstractBasePlugin):
    _params: OntologyLoaderParams

    @property
    def streaming(self) -> bool:
        """
        Whether the plugin processes records line-by-line (streaming) or in bulk.
        """
        return True  # Set to True if plugin should stream records

    @property
    def affected_tables(self) -> List[str]:
        """
        List of database tables this plugin writes to.
        """
        return ["reference.ontology.term", "reference.ontology.triple"]

    @property
    def operation(self):
        """
        Get the ETLOperation type used for rows created by this plugin run.
        """
        # Import locally to avoid circular import
        from niagads.genomicsdb.models.admin.pipeline import ETLOperation

        return ETLOperation.INSERT

    @classmethod
    def parameter_model(cls) -> Type[BasePluginParams]:
        return OntologyLoaderParams

    @classmethod
    def description(cls):
        return """
        Generic OWL Ontology Loader
        Loads ontology terms and relationships from OWL files into the NIAGADS ontology graph schema.
        """

    def _extract_terms(self, g: Graph) -> List[OntologyTermRecord]:
        """
        Helper to extract ontology terms from graph.
        """
        terms = []
        for s in g.subjects():
            rdf_type = g.value(s, RDF.type)

            term = OntologyTermRecord(
                term_id=str(s),
                label=str(g.value(s, RDFS.label) or ""),
                definition=str(g.value(s, URIRef(IAO_DEFINITION_URI)) or ""),
                synonyms=[
                    str(o) for o in g.objects(s, URIRef(OBOINOWL_EXACT_SYNONYM_URI))
                ],
                is_obsolete=bool(g.value(s, URIRef(OBOINOWL_IS_OBSOLETE_URI)) or False),
                replaced_by=str(g.value(s, URIRef(OBOINOWL_REPLACED_BY_URI)) or ""),
                term_kind=OntologyTermKind.from_rdf_type(rdf_type),
            )
            terms.append(term)
        return terms

    def _extract_relationships(self, g: Graph) -> list:
        """
        Helper to extract ontology relationships from graph.
        """
        relationships = []
        for s, p, o in g.triples((None, None, None)):
            if g.value(s, RDF.type) == OWL.Class and g.value(o, RDF.type) == OWL.Class:
                relationships.append(
                    {
                        "source": str(s),
                        "predicate": str(p),
                        "destination": str(o),
                    }
                )
        return relationships

    def extract(self) -> Dict[str, list]:
        """
        Extract ontology terms and relationships from the OWL file.
        Returns a dict with 'terms' and 'relationships' lists.
        """
        g = Graph()
        g.parse(self._params.file)
        self.logger.info(f"Loaded OWL file: {self._params.file}")
        terms = self._extract_terms(g)
        relationships = self._extract_relationships(g)
        return {"terms": terms, "relationships": relationships}

    def transform(self, data: Dict[str, list]) -> Dict[str, list]:
        """
        Transform extracted ontology terms and relationships. (No-op for now)
        """
        # Add normalization/validation here if needed
        return data

    async def load(self, transformed: Dict[str, list]) -> int:
        """
        Persist transformed data using an async SQLAlchemy session.
        Tally all inserts using self.update_transaction_count for accurate ETL status reporting.
        Returns the number of rows persisted.
        """
        transaction_count = 0
        async with self._session_manager() as session:
            for record in transformed["terms"]:
                if self._insert_term(session, record.dict()):
                    transaction_count += 1
                    self.update_transaction_count(
                        ETLOperation.INSERT, "reference.ontology.term"
                    )
            for rel in transformed["relationships"]:
                if self._insert_triple(session, rel):
                    transaction_count += 1
                    self.update_transaction_count(
                        ETLOperation.INSERT, "reference.ontology.triple"
                    )
            # Commit logic is handled by the pipeline, not the plugin
        return transaction_count

    def get_record_id(self, record: OntologyTermRecord) -> str:
        """
        Return the unique identifier for a record (term_id).
        """
        return record.term_id

    def _insert_term(self, session: Session, args: Dict[str, Any]) -> bool:
        """
        Insert a term record. Returns True if inserted, False if conflict.
        """
        term_insert_sql = """
            INSERT INTO reference.ontology.term (
                term_id, label, definition, synonyms, is_obsolete, replaced_by, term_kind
            ) VALUES (
                :term_id, :label, :definition, :synonyms, :is_obsolete, :replaced_by, :term_kind
            );
        """
        try:
            session.execute(text(term_insert_sql), args)
            self.update_transaction_count(
                ETLOperation.INSERT, "reference.ontology.term"
            )
            return True
        except Exception as e:
            self.logger.warning(f"Conflict inserting term_id {args['term_id']}: {e}")
            return False

    def _insert_triple(self, session: Session, args: Dict[str, Any]) -> bool:
        """
        Insert a triple record. Returns True if inserted, False if conflict.
        """
        triple_insert_sql = """
            INSERT INTO reference.ontology.triple (
                source, predicate, destination
            ) VALUES (
                :source, :predicate, :destination
            );
        """
        try:
            session.execute(text(triple_insert_sql), args)
            self.update_transaction_count(
                ETLOperation.INSERT, "reference.ontology.triple"
            )
            return True
        except Exception as e:
            self.logger.warning(
                f"Conflict inserting triple ({args['source']}, {args['predicate']}, {args['destination']}): {e}"
            )
            return False
