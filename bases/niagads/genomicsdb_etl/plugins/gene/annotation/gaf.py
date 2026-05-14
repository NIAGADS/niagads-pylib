"""
GO Annotation File (GAF) Loader Plugin

Loads Gene Ontology (GO) annotations from GAF 2.2 format files into the
GOAssociation and AnnotationEvidence tables, mapping gene references through
GeneXRef.
"""

from typing import Any, Dict, Iterator, List, Optional, Union


from niagads.common.models.annotations import (
    AnnotationEvidenceDescriptor,
    AnnotationEvidenceQualifier,
)
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.admin.catalog import TableCatalog
from niagads.database.genomicsdb.schema.admin.types import TableRef
from niagads.database.genomicsdb.schema.gene.annotation import (
    AnnotationEvidence,
    GOAssociation,
)
from niagads.database.genomicsdb.schema.gene.xrefs import GeneIdentifierType, GeneXRef
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    PathValidatorMixin,
    ResumeCheckpoint,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.utils.sys import read_open_ctx
from pydantic import BaseModel, Field, field_serializer, field_validator


class GAFEntry(BaseModel):
    db: str  # database name
    db_object_id: str  # source id
    db_object_symbol: str  # Gene symbol
    qualifier: Optional[str] = None
    go_id: str  # GO term ID
    db_reference: Optional[str] = None  # GO_REF:000...
    evidence_code: str  # IBA, IEP, etc.
    with_or_from: Optional[List[str]] = None
    aspect: str  # F (function), C (component), P (process)
    db_object_name: Optional[str] = None
    db_object_synonym: Optional[str] = None
    db_object_type: Optional[str] = None
    taxon: Optional[str] = None
    date: Optional[str] = None
    assigned_by: Optional[str] = None
    annotation_extension: Optional[str] = None
    gene_product_form_id: Optional[str] = None

    @field_validator("with_or_from", mode="before")
    @classmethod
    def split_with_or_from(cls, v):
        if v is None:
            return None
        return [x for x in v.split("|")]


class Evidence(AnnotationEvidenceDescriptor):
    evidence_code: str


class GOAssociationEntry(BaseModel):
    uniprot_id: str
    term_curie: str
    evidence: set[Evidence]

    # can't serialize this kind of set
    @field_serializer("evidence")
    def serialize_evidence(self, evidence, _info):
        if evidence is None:
            return evidence
        return list(evidence)


class GAFLoaderParams(BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin):
    """Parameters for GO Annotation File (GAF) loader plugin."""

    file: str = Field(..., description="Full path to GAF 2.2 file")

    go_xdbref: str = Field(
        ...,
        description="GO ontology external database reference (name|version) for "
        "mapping GO terms",
    )
    eco_xdbref: str = Field(
        ...,
        description="Evidence Code Ontology (ECO) external database reference "
        "(name|version) for mapping evidence codes",
    )

    validate_file_exists = PathValidatorMixin.validator("file")


metadata = PluginMetadata(
    version="1.0",
    description=(
        "ETL Plugin to load Gene Ontology (GO) annotations from GAF 2.2 files into "
        f"{GOAssociation.table_name()} and {AnnotationEvidence.table_name()}. "
        "Maps gene identifiers via UniProtKB"
    ),
    affected_tables=[AnnotationEvidence, GOAssociation],
    load_strategy=ETLLoadStrategy.BATCH,  # processing in bulk is the best way to handle duplicates
    operation=ETLOperation.INSERT,
    is_large_dataset=False,
    parameter_model=GAFLoaderParams,
)


@PluginRegistry.register(metadata)
class GAFLoader(AbstractBasePlugin):
    """
    ETL plugin for loading GO annotations from GAF 2.2 files into the
    gene.goassociation and gene.annotationevidence tables.

    Handles:
    - Parsing GAF 2.2 format files
    - Mapping UniProt IDs to genes via GeneXRef
    - Mapping GO IDs to ontology terms
    - Mapping evidence codes to ECO terms
    - Creating annotation evidence records with qualifiers and references
    """

    _params: GAFLoaderParams

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)

        self.__go_xdbr_id: int = None
        self.__eco_xdbr_id: int = None
        self.__external_database_id: int = None
        self.__goa_table_ref: TableRef = None

        self.__gene_pk_ref: Dict[str, int] = {}
        self.__evidence_code_pk_ref: Dict[str, int] = {}
        self.__go_curie_pk_ref: Dict[str, int] = {}

        self.__unmapped_genes: set[str] = set()

    async def on_run_start(self, session):
        """Fetch and cache ontology references and build gene lookup cache."""
        if self.is_etl_run:
            # Fetch external database references for the GO annotations
            self.__external_database_id = (
                await self._params.fetch_xdbref(session)
            ).external_database_id

            # Gene Ontology external_database_id
            xdbref_param = ExternalDatabaseRefMixin(xdbref=self._params.go_xdbref)
            self.__go_xdbr_id: int = (
                await xdbref_param.fetch_xdbref(session)
            ).external_database_id

            # ECO external_database_id
            xdbref_param = ExternalDatabaseRefMixin(xdbref=self._params.eco_xdbref)
            self.__eco_xdbr_id: int = (
                await xdbref_param.fetch_xdbref(session)
            ).external_database_id

            # going to have to pretty much match whole gene table, so cache it
            # to speed things up
            self.__gene_pk_ref = await GeneXRef.retrieve_gene_pk_mapping(
                session, gene_identifier_type=GeneIdentifierType.UNIPROT
            )

            # cache ontology mappings
            # map thru evidence codes
            self.__evidence_code_pk_ref = await OntologyTerm.retrieve_term_pk_mapping(
                session, ontology_ref=self.__eco_xdbr_id, map_thru_term=True
            )

            # map thru GO CURIES
            self.__go_curie_pk_ref = await OntologyTerm.retrieve_term_pk_mapping(
                session, ontology_ref=self.__go_xdbr_id
            )

            # Get table reference for annotation evidence
            self.__goa_table_ref = await TableCatalog.get_table_ref(
                session, GOAssociation
            )

            self.logger.info("Done Intitializing Caches")
            self.logger.info(f"Cached {len(self.__gene_pk_ref)} gene ID mappings")
            self.logger.info(
                f"Cached {len(self.__evidence_code_pk_ref)} evidence code mappings"
            )
            self.logger.info(f"Cached {len(self.__go_curie_pk_ref)} GO CURIE mappings")

    def extract(self) -> Iterator[GAFEntry]:
        """Extract GO annotations from GAF file."""
        fields = list(GAFEntry.model_fields.keys())
        entries = []
        with read_open_ctx(self._params.file) as fh:
            for line in fh:
                if line.startswith("!"):
                    continue
                values = line.strip().split("\t")
                entry = dict(zip(fields, values))
                entries.append(GAFEntry(**entry))

        return entries

    def __lookup_gene_pk(self, uniprot_id: str) -> Optional[int]:
        """Look up gene ID by UniProt identifier."""
        # Check cache first
        try:
            return self.__gene_pk_ref[uniprot_id]
        except:
            self.__unmapped_genes.add(uniprot_id)
            return None

    def __build_qualifiers(
        self, entry: GAFEntry
    ) -> Optional[AnnotationEvidenceQualifier]:
        """Build qualifiers dict for AnnotationEvidence."""

        qualifiers = {}

        if entry.qualifier:
            qualifiers["qualifier"] = entry.qualifier

        if entry.db_reference:
            qualifiers["reference"] = (
                entry.db_reference.split("|")
                if entry.db_reference is not None
                else None
            )

        if entry.with_or_from:
            if entry.with_or_from[0] != "":
                qualifiers["with_or_from"] = entry.with_or_from

        return AnnotationEvidenceQualifier(**qualifiers) if qualifiers else None

    async def transform(self, entries: List[GAFEntry]):
        """
        transform GAFEntry into a GOAssociationEntry
        """

        annotations: Dict[str, GOAssociationEntry] = {}
        for entry in entries:
            uniprot_id = entry.db_object_id
            key = f"{uniprot_id}|{entry.go_id}"

            evidence = Evidence(
                evidence_code=entry.evidence_code,
                qualifiers=self.__build_qualifiers(entry),
            )

            if key in annotations:
                annotations[key].evidence.add(evidence)
            else:
                annotations[key] = GOAssociationEntry(
                    uniprot_id=entry.db_object_id,
                    term_curie=entry.go_id,
                    evidence={evidence},
                )
        return list(annotations.values())

    async def __lookup_evidence_code(self, code: str):
        """find ontology_term_id matching evidence code"""
        # allow error to be raised if code is not found
        ontology_term_id = self.__evidence_code_pk_ref[code]
        return ontology_term_id

    async def __lookup_go_term_curie(self, curie: str):
        """find ontology_term_id matching go term curie"""

        # allow error to be raised if curie is not found
        ontology_term_id = self.__go_curie_pk_ref[curie]
        return ontology_term_id

    async def load(
        self, session, entries: List[GOAssociationEntry]
    ) -> ResumeCheckpoint:
        """
        Load GO annotations into GOAssociation and AnnotationEvidence tables.

        Args:
            session: AsyncSession for database operations
            records: List of GOAssociationEntry objects to load

        Returns:
            ResumeCheckpoint for resumable runs
        """
        # faster to do two bulk submits
        associations: dict[str, GOAssociation] = {}
        for entry in entries:
            # Lookup gene by UniProt ID
            gene_pk = self.__lookup_gene_pk(entry.uniprot_id)
            if gene_pk is None:
                self.inc_tx_count(GOAssociation, ETLOperation.SKIP)
                continue

            # Lookup GO term
            go_term_id = await self.__lookup_go_term_curie(entry.term_curie)

            # Create GOAssociation record
            key = f"{entry.uniprot_id}|{entry.term_curie}"
            associations[key] = GOAssociation(
                gene_id=gene_pk,
                go_term_id=go_term_id,
                external_database_id=self.__external_database_id,
                run_id=self.run_id,
            )

        await GOAssociation.submit_many(session, associations.values())

        annotation_evidence = []
        for entry in entries:
            try:
                key = f"{entry.uniprot_id}|{entry.term_curie}"
                association_pk = associations[key].go_association_id
            except:  # skipped gene
                self.inc_tx_count(AnnotationEvidence, ETLOperation.SKIP)
                continue

            for evidence_entry in entry.evidence:
                # Lookup ECO code
                evidence_code_id = await self.__lookup_evidence_code(
                    evidence_entry.evidence_code
                )
                evidence = AnnotationEvidence(
                    table_id=self.__goa_table_ref.table_id,
                    row_id=association_pk,
                    evidence_code_id=evidence_code_id,
                    qualifiers=evidence_entry.qualifiers.model_dump(
                        exclude_none=True, exclude_unset=True
                    ),
                    external_database_id=self.__external_database_id,
                    run_id=self.run_id,
                )

                annotation_evidence.append(evidence)

        await AnnotationEvidence.submit_many(session, annotation_evidence)

        return self.create_checkpoint(record=entries[-1])

    def get_record_id(self, record: GOAssociationEntry) -> str:
        """Return unique identifier for checkpoint."""
        return f"{record.uniprot_id}|{record.term_curie}"

    async def on_run_complete(self):
        """Log summary statistics after run completion."""
        total_unmapped_genes = len(self.__unmapped_genes)

        if total_unmapped_genes > 0:
            self.logger.warning(
                f"Could not map {total_unmapped_genes} UniProt identifiers to genes"
            )
            if self._verbose:
                self.logger.debug(f"Unmapped genes: {self.__unmapped_genes}")
