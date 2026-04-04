"""
Gene Structure Loader Plugin
- Parse Ensembl GFF3 files and load gene, transcript, and exon records into gene structure tables.
"""

from enum import auto
from typing import Any, Dict, Iterator, List, Optional, Union

from niagads.common.genomic.regions.models import GenomicRegion
from niagads.common.models.types import Range
from niagads.enums.core import CaseInsensitiveEnum
from niagads.genome_reference.types import Strand
from niagads.utils.dict import info_string_to_dict
from niagads.utils.string import regex_replace
from niagads.utils.sys import read_open_ctx
from sqlalchemy import Enum


from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.gene.structure import (
    GeneModel,
    TranscriptModel,
    ExonModel,
)

from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)

from pydantic import BaseModel, Field, field_validator

from niagads.genome_reference.human import HumanGenome


class GFF3FeatureType(CaseInsensitiveEnum):
    GENE = auto()
    TRANSCRIPT = auto()
    EXON = auto()


GFF3_FIELDS = [
    "seqid",
    "source",
    "feature_type",
    "start",
    "end",
    "score",
    "strand",
    "phase",
    "attributes",
]


class GFF3Entry(BaseModel):
    id: str
    parent_id: Optional[str] = None
    chromosome: HumanGenome = Field(alias="seqid")
    source: str
    feature_type: GFF3FeatureType
    start: int
    end: int
    score: str
    strand: Strand
    phase: str
    attributes: dict
    line: str

    @field_validator("strand", mode="before")
    def validate_strand(cls, strand: str):
        return Strand(strand) if strand != "." else Strand.SENSE


# ----------- Plugin


class EnsemblGFF3LoaderParams(
    BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin
):
    """Parameters for Ensembl GFF3 gene structure loader plugin."""

    file: str = Field(..., description="full path to Ensembl GFF3 file")
    so_xdbref: str = Field(
        ...,
        description="external database reference for the sequence ontology `SO|version'",
    )

    validate_file_exists = PathValidatorMixin.validator("file")


metadata = PluginMetadata(
    version="1.0",
    description=(
        "ETL Plugin to load gene structures (genes, transcripts, exons) from an Ensembl GFF3 file"
    ),
    affected_tables=[ExonModel, TranscriptModel, GeneModel],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.INSERT,
    is_large_dataset=False,
    parameter_model=EnsemblGFF3LoaderParams,
)


@PluginRegistry.register(metadata)
class EnsemblGFF3Loader(AbstractBasePlugin):
    """
    ETL plugin for loading gene structures from an Ensembl GFF3 file.

    Parses gene, transcript, and exon features from a GFF3 file and loads them
    into the gene, transcript, and exon tables in the GenomicsDB database.
    """

    _params: EnsemblGFF3LoaderParams  # type annotation

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        # Cache for gene primary keys to avoid redundant database queries
        self.__gene_pk_ref = {}
        # Cache for transcript primary keys to maintain relationships with genes
        self.__transcript_pk_ref = {}
        # Mapping of transcript primary keys to their parent gene primary keys
        self.__transcript2gene_ref = {}
        # References for ontology terms
        self.__ontology_term_ref = {}
        # External database ID for sequence ontology
        self.__so_external_database_id = None
        # External database instance
        self.__external_database: ExternalDatabase = None

    @property
    def external_database_id(self):
        return self.__external_database.external_database_id

    async def on_run_start(self, session):
        if self.is_etl_run:
            # validate the xdbref against the database
            self.__external_database = await self._params.fetch_xdbref(session)

            self.logger.debug(
                f"external_database_id = {self.__external_database.external_database_id}"
            )

            # validate and fetch sequence ontology external database ref
            so_xbdref_param = ExternalDatabaseRefMixin(xdbref=self._params.so_xdbref)
            so_xdbref: ExternalDatabase = await so_xbdref_param.fetch_xdbref(session)
            self.__so_external_database_id = so_xdbref.external_database_id

    def get_record_id(
        self, record: Union[GeneModel, TranscriptModel, ExonModel]
    ) -> str:
        return record.source_id

    def __build_genomic_region(self, entry: GFF3Entry) -> GenomicRegion:
        """
        Create a GenomicRegion from GFF3 fields.
        """

        return GenomicRegion(
            chromosome=entry.chromosome,
            start=entry.start,
            end=entry.end,
            strand=entry.strand,
        )

    def extract(self) -> Iterator[GFF3Entry]:
        """
        Extract lines from GFF3, filtering out comments, non-primary sequence, and ignored feature types

        Yields:
            GFF3Entry
        """
        with read_open_ctx(self._params.file) as fh:
            for line_number, line in enumerate(fh, start=1):
                if line.startswith("#"):
                    continue

                if line_number % 100000 == 0:
                    self.logger.debug(f"Parsed {line_number} GFF3 entries")

                fields = line.rstrip("\n").split("\t")
                entry = dict(zip(GFF3_FIELDS, fields))

                try:  # skip non-primary assembly
                    HumanGenome(entry["seqid"])
                except:
                    continue

                entry["attributes"] = info_string_to_dict(entry["attributes"])

                if "exon_id" in entry["attributes"]:
                    entry_id = entry["attributes"].get("exon_id")
                    entry["feature_type"] = GFF3FeatureType.EXON

                else:
                    feature_id: str = entry["attributes"].get("ID")
                    if feature_id is None:  # some features do not have ids
                        feature_type = entry["feature_type"]
                    else:
                        feature_type, entry_id = feature_id.split(":")

                    try:
                        entry["feature_type"] = GFF3FeatureType(feature_type)
                    except:
                        continue

                parent_id: str = entry["attributes"].get("Parent")
                if parent_id is not None:
                    parent_id = parent_id.split(":")[1]

                yield GFF3Entry(
                    id=entry_id,
                    parent_id=parent_id,
                    line=line,
                    **entry,
                )

    def __create_gene_model(self, entry: GFF3Entry) -> GeneModel:
        gene_name = entry.attributes.get("description")
        if gene_name:
            # DEAD/H-box helicase 11 like 16 (pseudogene) [Source:NCBI gene (formerly Entrezgene)%3BAcc:727856]
            gene_name = regex_replace(r"\s*\[Source:[^\]]*\]", "", gene_name).strip()

        span: GenomicRegion = self.__build_genomic_region(entry)

        # DEVELOPER NOTE: ORM models do not validate until submitted
        # so we can leave off required fields (e.g., bin_index)
        # or assign the wrong values (e.g., biotype term instead of ontology_term_id)
        # as long as we update before submit
        gene = GeneModel(
            source_id=entry.id,
            gene_symbol=entry.attributes.get("Name"),
            gene_name=gene_name,
            chromosome=str(span.chromosome),
            strand=str(span.strand),
            span=Range(start=span.start, end=span.end),
            gene_type_id=entry.attributes.get("biotype"),
        )
        # self.__gene_count += 1
        # self.logger.debug(f"Gene: {gene.model_dump()}")
        return gene

    def __create_transcript_model(self, entry: GFF3Entry) -> TranscriptModel:
        is_canonical: bool = False
        if "tag" in entry.attributes:
            is_canonical = "Ensembl_canonical" in entry.attributes["tag"]

        span: GenomicRegion = self.__build_genomic_region(entry)

        transcript = TranscriptModel(
            source_id=entry.id,
            name=entry.attributes.get("Name"),
            is_canonical=is_canonical,
            gene_id=entry.parent_id,
            chromosome=str(span.chromosome),
            strand=str(span.strand),
            span=Range(start=span.start, end=span.end),
        )

        return transcript

    def __create_exon_model(self, entry: GFF3Entry):
        span: GenomicRegion = self.__build_genomic_region(entry)
        exon = ExonModel(
            id=entry.id,
            transcript_id=entry.parent_id,
            rank=entry.attributes.get("rank"),
            chromosome=str(span.chromosome),
            strand=str(span.strand),
            span=Range(start=span.start, end=span.end),
        )

        return exon

    def transform(self, entry: GFF3Entry):
        """
        Transform gene models from GFF3 parser into ORM model instances.

        Yields each gene with its transcripts and exons separately, maintaining
        foreign key dependencies while allowing the base plugin to handle batching.
        Each yield contains the complete data for one gene: the gene itself, its
        transcripts, and their exons.

        Args:
            records: Iterable of Pydantic GeneModel instances from extract()

        Yields:
            For each gene:
            - List with [GeneModel ORM]
            - List with all TranscriptModel ORM instances for that gene
            - List with all ExonModel ORM instances for that gene's transcripts
        """
        if entry.feature_type == GFF3FeatureType.GENE:
            return self.__create_gene_model(entry)

        # Handle transcript features (mRNA)
        elif entry.feature_type == GFF3FeatureType.TRANSCRIPT:
            return self.__create_transcript_model(entry)

        # Handle exon features
        elif entry.feature_type == GFF3FeatureType.EXON:
            return self.__create_exon_model(entry)

    async def __lookup_gene_biotype(self, session, biotype: str):
        """find ontology_term_id matching gene biotype"""
        try:
            ontology_term_id = self.__ontology_term_ref[biotype]
        except:
            ontology_term_id = await OntologyTerm.find_primary_key(
                session,
                filters={
                    "external_database_id": self.__so_external_database_id,
                    "term": biotype,
                },
            )
            self.__ontology_term_ref[biotype] = ontology_term_id
        return ontology_term_id

    async def load(
        self, session, records: list[Union[GeneModel, TranscriptModel, ExonModel]]
    ):
        for feature in records:
            feature.external_database_id = self.external_database_id
            feature.run_id = self.run_id

            feature.bin_index = await IntervalBin.find_bin_index(
                session, feature.chromosome, feature.span
            )

            if isinstance(feature, GeneModel):
                feature.gene_type_id = await self.__lookup_gene_biotype(
                    session, feature.gene_type_id
                )
                gene_pk = await feature.submit(session)
                self.__gene_pk_ref[feature.source_id] = gene_pk

            elif isinstance(feature, TranscriptModel):
                feature.gene_id = self.__gene_pk_ref[feature.gene_id]
                transcript_pk = await feature.submit(session)
                self.__transcript_pk_ref[feature.source_id] = transcript_pk
                self.__transcript2gene_ref[transcript_pk] = feature.gene_id

            elif isinstance(feature, ExonModel):
                feature.transcript_id = self.__transcript_pk_ref[feature.transcript_id]
                feature.gene_id = self.__transcript2gene_ref[feature.transcript_id]
                await feature.submit()

        return self.create_checkpoint(record=records[-1])
