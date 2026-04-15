"""
Gene Structure Loader Plugin
- Parse Ensembl GFF3 files and load gene, transcript, and exon records into gene structure tables.
"""

from enum import auto
from typing import Any, Dict, Iterator, Optional, Union

from niagads.common.genomic.regions.models import GenomicRegion
from niagads.common.models.types import Range
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.gene.structure import (
    ExonModel,
    GeneModel,
    TranscriptModel,
)
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.enums.core import CaseInsensitiveEnum
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genome_reference.human import HumanGenome
from niagads.genome_reference.types import Strand
from niagads.genomicsdb_etl.plugins.common.bases.features import (
    BaseFeatureLoaderParams,
    BaseFeatureLoaderPlugin,
)
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.utils.dict import info_string_to_dict
from niagads.utils.string import regex_replace
from niagads.utils.sys import read_open_ctx
from pydantic import BaseModel, Field, field_validator


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
    children: Optional[list] = []

    @field_validator("strand", mode="before")
    def validate_strand(cls, strand: str):
        return Strand(strand) if strand != "." else Strand.SENSE


# DEVELOPER'S NOTE: arbitrary_types_allowed=True must be used b/c types are ORM models
class TranscriptFeature(BaseModel, arbitrary_types_allowed=True):
    transcript: TranscriptModel
    exons: list[ExonModel] = []


class GeneFeature(BaseModel, arbitrary_types_allowed=True):
    gene: GeneModel
    transcripts: list[TranscriptFeature] = []


# ----------- Plugin


class EnsemblGFF3LoaderParams(BaseFeatureLoaderParams, PathValidatorMixin):
    """Parameters for Ensembl GFF3 gene structure loader plugin."""

    file: str = Field(..., description="full path to Ensembl GFF3 file")
    verify_biotypes_only: bool = Field(
        default=False, description="in `RUN` mode, only verify biotypes"
    )
    so_xdbref: str = Field(
        ...,
        description="external database reference for the sequence ontology `SO|version'",
    )

    validate_file_exists = PathValidatorMixin.validator("file")


metadata = PluginMetadata(
    version="1.0",
    description=(
        "ETL Plugin to load gene structures (genes, transcripts, exons) from an Ensembl GFF3 file. "
        "Recommended to run first with `--verify-biotypes-only --verbose` because Ensembl "
        "does not strictly adhere to the sequence ontology (SO)."
    ),
    affected_tables=[ExonModel, TranscriptModel, GeneModel],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.INSERT,
    is_large_dataset=False,
    parameter_model=EnsemblGFF3LoaderParams,
    can_resume=True,
)


@PluginRegistry.register(metadata)
class EnsemblGFF3Loader(BaseFeatureLoaderPlugin):
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

        # cache for ontology lookups
        self.__ontology_term_ref = {}
        # External database ID for sequence ontology
        self.__so_external_database_id = None

    async def on_run_start(self, session):
        await super().on_run_start(session)

        if self.is_etl_run:
            # validate and fetch sequence ontology external database ref
            so_xbdref_param = ExternalDatabaseRefMixin(xdbref=self._params.so_xdbref)
            so_xdbref: ExternalDatabase = await so_xbdref_param.fetch_xdbref(session)
            self.__so_external_database_id = so_xdbref.external_database_id
            self.logger.debug(f"SO XDBREF ID = {self.__so_external_database_id}")

    def get_record_id(
        self, record: Union[GeneModel, TranscriptModel, ExonModel]
    ) -> str:
        return record.source_id

    def __build_genomic_region(self, entry: GFF3Entry) -> GenomicRegion:
        """
        Create a GenomicRegion from GFF3 entry fields.
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
        skipped_line_count = 0
        parsed_gene_count = 0
        current_gene: GFF3Entry = None
        current_transcript: GFF3Entry = None
        with read_open_ctx(self._params.file) as fh:
            for line_number, line in enumerate(fh, start=1):
                gene_is_yielded: bool = False
                if line.startswith("#"):
                    skipped_line_count += 1
                    continue

                if line_number % 100000 == 0:
                    self.logger.info(f"Parsed {line_number} GFF3 entries")

                fields = line.rstrip("\n").split("\t")
                entry = dict(zip(GFF3_FIELDS, fields))

                try:  # skip non-primary assembly
                    HumanGenome(entry["seqid"])
                except:
                    skipped_line_count += 1
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
                        skipped_line_count += 1
                        continue

                parent_id: str = entry["attributes"].get("Parent")
                if parent_id is not None:
                    parent_id = parent_id.split(":")[1]

                feature = GFF3Entry(
                    id=entry_id,
                    parent_id=parent_id,
                    line=line,
                    **entry,
                )

                # let's collate the features and yield "genes"
                # this so child structures and their parents do not get
                # separated across commits, causing errors on rollback
                if feature.feature_type == GFF3FeatureType.GENE:
                    if current_gene is None:
                        current_gene = feature
                    # if we are seeing a new gene, return the old one
                    elif current_gene.id != feature.id:
                        gene_is_yielded = True
                        yield current_gene

                        parsed_gene_count += 1
                        current_gene = feature
                        current_transcript = None  # restart transcript tracking

                # collate transcripts
                if feature.feature_type == GFF3FeatureType.TRANSCRIPT:
                    if feature.parent_id != current_gene.id:
                        self.logger.exception(
                            f"transcript out of order : {feature.parent_id}"
                        )
                    if current_transcript is None:
                        current_transcript = feature
                    elif current_transcript.id != feature.id:
                        current_transcript = feature
                    current_gene.children.append(current_transcript)

                # collate exons
                if feature.feature_type == GFF3FeatureType.EXON:
                    if feature.parent_id != current_transcript.id:
                        self.logger.exception(
                            f"exon out of order : {feature.parent_id}"
                        )
                    current_transcript.children.append(feature)

        # residual; flag is extra sanity check to ensure against
        # duplicating final entry
        if not gene_is_yielded:
            parsed_gene_count += 1
            yield current_gene

        self.logger.info(
            f"Done Extracting records - Parsed {parsed_gene_count} Gene Features; "
            f"Skipped {skipped_line_count} lines."
        )

    def __create_gene_model(self, entry: GFF3Entry) -> GeneModel:
        # self.logger.debug(f"{entry.attributes}")
        gene_name = entry.attributes.get("description")
        if gene_name:
            # DEAD/H-box helicase 11 like 16 (pseudogene) [Source:NCBI gene (formerly Entrezgene)%3BAcc:727856]
            gene_name = (
                regex_replace(r"\s*\[Source:[^\]]*\]", "", gene_name)
                .strip()
                .replace("%2C", ",")
                .replace("%3B", ";")
            )

        gene_symbol = entry.attributes.get("Name")
        if gene_symbol is None:
            if gene_name is None:  # set them both
                gene_symbol = "novel gene"
                gene_name = "novel gene"
            elif "novel pseudogene" in gene_name:
                gene_symbol = "novel pseudogene"
            else:
                gene_symbol = "novel gene"

        span: GenomicRegion = self.__build_genomic_region(entry)

        gene_type: str = entry.attributes.get("biotype")
        if gene_type == "misc_RNA":  # this term does not exist in SO
            gene_type = "ncRNA_gene"  # but in Ensembl 115 all misc_RNA genes are ncRNA_gene typed

        # DEVELOPER NOTE: ORM models do not validate until submitted
        # so we can leave off required fields (e.g., bin_index)
        # or assign the wrong values (e.g., biotype term instead of ontology_term_id)
        # as long as we update before submit
        gene = GeneModel(
            source_id=entry.id,
            gene_symbol=gene_symbol,
            gene_name=gene_name,
            chromosome=str(span.chromosome),
            strand=str(span.strand),
            span=Range(start=span.start, end=span.end),
            gene_type_id=gene_type,
        )

        return GeneFeature(gene=gene)

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

        transcript_feature = TranscriptFeature(transcript=transcript)
        for exon in entry.children:
            transcript_feature.exons.append(self.__create_exon_model(exon))

        return transcript_feature

    def __create_exon_model(self, entry: GFF3Entry):
        span: GenomicRegion = self.__build_genomic_region(entry)
        exon = ExonModel(
            source_id=entry.id,
            transcript_id=entry.parent_id,
            rank=entry.attributes.get("rank"),
            chromosome=str(span.chromosome),
            strand=str(span.strand),
            span=Range(start=span.start, end=span.end),
        )

        return exon

    def transform(self, entry: GFF3Entry) -> GeneFeature:
        """
        Convert a parsed GFF3Entry gene record (with children) into a GeneFeature object.

        For a given gene entry, constructs a GeneFeature containing the ORM GeneModel,
        and for each transcript child, appends a TranscriptFeature with its ORM TranscriptModel
        and all associated ExonModel ORM instances.

        Args:
            entry: GFF3Entry representing a gene, with children as transcripts (each with exons).

        Returns:
            GeneFeature: Contains the ORM GeneModel, a list of TranscriptFeature objects (each with
            TranscriptModel and list of ExonModel instances).
        """

        # self.logger.debug(f"{entry.id}")
        gene_feature: GeneFeature = self.__create_gene_model(entry)
        for transcript in entry.children:
            gene_feature.transcripts.append(self.__create_transcript_model(transcript))

        return gene_feature

    async def __lookup_gene_biotype(self, session, biotype: str):
        """find ontology_term_id matching gene biotype"""
        try:
            ontology_term_id = self.__ontology_term_ref[biotype]
        except:
            try:  # look up in database
                ontology_term_id = await OntologyTerm.find_primary_key(
                    session,
                    term=biotype,
                    external_database_id=self.__so_external_database_id,
                )
                self.__ontology_term_ref[biotype] = ontology_term_id
                if self._verbose:
                    self.logger.info(f"Matched {biotype} - {ontology_term_id}")
            except:
                ontology_term_id = await OntologyTerm.find_primary_key(
                    session,
                    term=biotype,
                    external_database_id=self.__so_external_database_id,
                    search_synonyms=True,
                )
                self.__ontology_term_ref[biotype] = ontology_term_id
                if self._verbose:
                    self.logger.info(f"Matched {biotype} - {ontology_term_id}")

        return ontology_term_id

    def __set_common_attributes(
        self, feature: Union[GeneModel, TranscriptModel, ExonModel]
    ):
        feature.external_database_id = self.external_database_id
        feature.run_id = self.run_id
        feature.bin_index = self._find_bin_index(feature.chromosome, feature.span)

    def __count_skipped_gene(self, gene_feature: GeneFeature):
        self.inc_tx_count(GeneModel, ETLOperation.SKIP)
        self.inc_tx_count(
            TranscriptModel, ETLOperation.SKIP, len(gene_feature.transcripts)
        )
        num_exons = sum(
            len(transcript_feature.exons)
            for transcript_feature in gene_feature.transcripts
        )
        self.inc_tx_count(ExonModel, ETLOperation.SKIP, num_exons)

    async def load(self, session, records: list[GeneFeature]):
        gene_id = None
        for gene_feature in records:
            gene: GeneModel = gene_feature.gene

            if not self._resume:
                if gene.source_id != self._params.resume_after:
                    self.__count_skipped_gene(gene_feature)
                    continue
                else:
                    self.logger.info(
                        f"Resuming load after checkpoint {self._params.resume_after}:{gene.source_id}"
                    )
                    self._resume = True
                    continue  # checkpoint is last committed, so want to resume next

            if gene.gene_type_id == "artifact":
                self.__count_skipped_gene(gene_feature)
                self.logger.info(f"Skipping `artifact` gene: {gene.source_id}")
                continue

            gene.gene_type_id = await self.__lookup_gene_biotype(
                session, gene_feature.gene.gene_type_id
            )
            if self._params.verify_biotypes_only:
                continue

            gene_id = gene.source_id
            self.__set_common_attributes(gene)

            gene_pk = await gene.submit(session)

            exons = []
            exon_count = 0
            for transcript_feature in gene_feature.transcripts:
                transcript = transcript_feature.transcript
                self.__set_common_attributes(transcript)
                transcript.gene_id = gene_pk
                transcript_pk = await transcript.submit(session)

                for exon in transcript_feature.exons:
                    self.__set_common_attributes(exon)
                    exon.gene_id = gene_pk
                    exon.transcript_id = transcript_pk
                    exons.append(exon)
                    exon_count += 1

            await ExonModel.submit_many(session, exons)  # submit exons in batch

            if self._verbose:
                self.logger.info(
                    f"Loaded Gene {gene_id} - Transcripts = {len(gene_feature.transcripts)} | Exons = {exon_count}."
                )
        return self.create_checkpoint(record=records[-1].gene)
