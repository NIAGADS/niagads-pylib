"""
GFF3 file parser for Ensembl genomic annotation files.

Extends AbstractFlatfileParser to parse Ensembl GFF3 format files into
structured gene models (Gene, Transcript, Exon, CDS, UTR).

Reference: https://github.com/The-Sequence-Ontology/Specifications/blob/master/gff3.md
"""

from typing import Dict, Iterator, Optional, Any
from urllib.parse import unquote

from niagads.flatfile.base import AbstractFlatfileParser
from niagads.common.gene.models.structure import (
    GeneModel,
    TranscriptModel,
    ExonModel,
    CDSRegion,
    UTRRegion,
    CodonRegion,
)
from niagads.genome_reference.human import HumanGenome
from niagads.genome_reference.types import Strand
from niagads.common.genomic.regions.models import GenomicRegion


class EnsemblGFF3Parser(AbstractFlatfileParser):
    """
    Parser for Ensembl GFF3 files.

    Parses GFF3 format files and converts them into structured gene models
    (Gene, Transcript, Exon, CDS). Handles the hierarchical relationships
    between genes, transcripts, and their structural components.

    Attributes:
        _gene_cache: Cache of genes indexed by ID
        _transcript_cache: Cache of transcripts indexed by ID
        _feature_map: Map of feature ID to parent ID for hierarchy building
    """

    def __init__(
        self,
        file: str,
        *,
        encoding: str = "utf-8",
        debug: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the Ensembl GFF3 parser.

        Args:
            file: Path to GFF3 file
            encoding: File encoding (default: utf-8)
            debug: Enable debug logging
            verbose: Enable verbose logging
        """
        super().__init__(file=file, encoding=encoding, debug=debug, verbose=verbose)
        self._gene_cache: Dict[str, GeneModel] = {}
        self._transcript_cache: Dict[str, TranscriptModel] = {}
        self._feature_map: Dict[str, str] = {}  # child_id -> parent_id

    def is_ignored_line(self, line: str) -> bool:
        """
        Check if line should be ignored.

        Ignores empty lines and GFF3 directives (lines starting with '#').
        """
        stripped = line.strip()
        return stripped == "" or stripped.startswith("#")

    def _parse_attributes(self, attributes_str: str) -> Dict[str, Any]:
        """
        Parse GFF3 attributes field into key-value pairs.

        GFF3 attributes are semicolon-separated tag=value pairs where
        values may be URL-encoded.

        Args:
            attributes_str: Raw attributes string from GFF3 file

        Returns:
            Dictionary of parsed attribute key-value pairs
        """
        attributes = {}

        if not attributes_str or attributes_str == ".":
            return attributes

        try:
            pairs = attributes_str.split(";")
            for pair in pairs:
                pair = pair.strip()
                if not pair:
                    continue

                if "=" not in pair:
                    raise ValueError(f"Invalid attribute pair: {pair}")

                key, value = pair.split("=", 1)
                key = key.strip()

                try:
                    value = unquote(value.strip())
                except Exception as err:
                    if self.verbose:
                        self.logger.warning(
                            f"Failed to URL-decode attribute value '{value}': {err}"
                        )
                    value = value.strip()

                if "," in value:
                    value = [v.strip() for v in value.split(",")]

                attributes[key] = value

            return attributes

        except Exception as err:
            raise ValueError(
                f"Failed parsing attributes '{attributes_str}': {err}"
            ) from err

    def _create_genomic_region(
        self,
        seqid_str: str,
        start: str,
        end: str,
        strand: str,
    ) -> GenomicRegion:
        """
        Create a GenomicRegion from GFF3 fields.

        GFF3 uses 1-based, inclusive coordinates.

        Args:
            seqid_str: Chromosome/sequence name
            start: Start coordinate (1-based)
            end: End coordinate (1-based, inclusive)
            strand: Strand (+, -, or .)

        Returns:
            GenomicRegion with 0-based, half-open coordinates
        """
        try:
            seqid = HumanGenome(seqid_str)
        except ValueError as err:
            raise ValueError(f"Invalid chromosome '{seqid_str}': {err}") from err

        try:
            start_int = int(start) - 1  # Convert 1-based to 0-based
            end_int = int(end)  # End is already at correct position for half-open
        except ValueError as err:
            raise ValueError(
                f"Invalid coordinates: start={start}, end={end}: {err}"
            ) from err

        try:
            strand_obj = Strand(strand) if strand != "." else Strand.SENSE
        except ValueError as err:
            if self.verbose:
                self.logger.warning(f"Invalid strand '{strand}', using SENSE: {err}")
            strand_obj = Strand.SENSE

        return GenomicRegion(
            chromosome=seqid,
            start=start_int,
            end=end_int,
            strand=strand_obj,
        )

    def parse_line(self, line: str) -> Optional[tuple]:
        """
        Parse a single GFF3 line.

        Returns a tuple of (feature_type, attributes, location, phase, score, source)
        for building gene structures.

        Args:
            line: Single line from GFF3 file (tab-separated)

        Returns:
            Tuple of (feature_type, attributes_dict, location, phase, score, source) or None
        """
        fields = line.rstrip("\n").split("\t")

        if len(fields) != 9:
            raise ValueError(
                f"Invalid GFF3 line format: expected 9 tab-separated fields, "
                f"got {len(fields)}"
            )

        (
            seqid_str,
            source,
            feature_type,
            start,
            end,
            score,
            strand,
            phase,
            attributes_str,
        ) = fields

        location = self._create_genomic_region(seqid_str, start, end, strand)
        attributes = self._parse_attributes(attributes_str)

        phase_int = None
        if phase != ".":
            try:
                phase_int = int(phase)
                if phase_int not in (0, 1, 2):
                    raise ValueError(f"Invalid phase: {phase}")
            except (ValueError, TypeError) as err:
                if self.verbose:
                    self.logger.warning(f"Invalid phase '{phase}': {err}")

        score_float = None
        if score != ".":
            try:
                score_float = float(score)
            except (ValueError, TypeError) as err:
                if self.verbose:
                    self.logger.warning(f"Invalid score '{score}': {err}")

        return (feature_type, attributes, location, phase_int, score_float, source)

    def __iter__(self) -> Iterator[GeneModel]:
        """
        Iterate over parsed genes from the GFF3 file.

        Yields:
            Gene objects with associated transcripts, exons, and CDS regions
        """
        self._gene_cache = {}
        self._transcript_cache = {}
        self._feature_map = {}

        # First pass: parse all features and build structure
        with self.open_ctx() as fh:
            for line_number, raw_line in enumerate(fh, start=1):
                line = self.preprocess_line(raw_line)
                if self.is_ignored_line(line):
                    continue

                try:
                    result = self.parse_line(line)
                    if result is None:
                        continue

                    feature_type, attributes, location, phase, score, source = result
                    feature_id = attributes.get("ID")
                    parent_id = attributes.get("Parent")

                    if parent_id:
                        self._feature_map[feature_id] = parent_id

                    # Handle gene features
                    if feature_type == "gene":
                        gene_symbol = attributes.get("Name")
                        gene_desc = attributes.get("description")
                        gene_biotype = attributes.get("biotype")

                        # Collect non-standard attributes
                        standard_attrs = {
                            "ID",
                            "Parent",
                            "Name",
                            "description",
                            "biotype",
                        }
                        extra_attrs = {
                            k: v
                            for k, v in attributes.items()
                            if k not in standard_attrs
                        }

                        gene = GeneModel(
                            id=feature_id,
                            symbol=gene_symbol,
                            location=location,
                            source=source,
                            biotype=gene_biotype,
                            description=gene_desc,
                            score=score,
                            attributes=extra_attrs,
                        )
                        self._gene_cache[feature_id] = gene

                    # Handle transcript features (mRNA)
                    elif feature_type in ("mRNA", "transcript"):
                        transcript_biotype = attributes.get("biotype")
                        is_canonical = attributes.get("is_canonical")

                        # Collect non-standard attributes
                        standard_attrs = {"ID", "Parent", "biotype", "is_canonical"}
                        extra_attrs = {
                            k: v
                            for k, v in attributes.items()
                            if k not in standard_attrs
                        }

                        transcript = TranscriptModel(
                            id=feature_id,
                            location=location,
                            source=source,
                            biotype=transcript_biotype,
                            is_canonical=is_canonical == "1" if is_canonical else None,
                            attributes=extra_attrs,
                        )
                        self._transcript_cache[feature_id] = transcript

                        # Add to parent gene
                        if parent_id and parent_id in self._gene_cache:
                            self._gene_cache[parent_id].transcripts.append(transcript)

                    # Handle exon features
                    elif feature_type == "exon":
                        exon_rank = attributes.get("rank")
                        try:
                            rank_int = int(exon_rank) if exon_rank else None
                        except (ValueError, TypeError):
                            rank_int = None

                        exon = ExonModel(
                            id=feature_id,
                            location=location,
                            rank=rank_int,
                        )

                        # Add to parent transcript
                        if parent_id and parent_id in self._transcript_cache:
                            self._transcript_cache[parent_id].exons.append(exon)

                    # Handle CDS features
                    elif feature_type == "CDS":
                        cds = CDSRegion(location=location, phase=phase)

                        # Add to parent transcript
                        if parent_id and parent_id in self._transcript_cache:
                            self._transcript_cache[parent_id].cds.append(cds)

                    # Handle UTR features (5UTR or 3UTR)
                    elif feature_type in ("5UTR", "3UTR"):
                        utr = UTRRegion(location=location, region_type=feature_type)

                        # Add to parent transcript
                        if parent_id and parent_id in self._transcript_cache:
                            self._transcript_cache[parent_id].utrs.append(utr)

                    # Handle start and stop codons
                    elif feature_type in ("start_codon", "stop_codon"):
                        codon = CodonRegion(location=location, codon_type=feature_type)

                        # Add to parent transcript
                        if parent_id and parent_id in self._transcript_cache:
                            self._transcript_cache[parent_id].codons.append(codon)

                except Exception as err:
                    raise ValueError(
                        f"Failed parsing {self.file} at line {line_number}"
                    ) from err

        # Yield all genes with their transcripts
        for gene in self._gene_cache.values():
            yield gene

    def to_json(self) -> Iterator[str]:
        """
        Iterate over genes and yield JSON strings.

        Yields:
            JSON string for each Gene
        """
        for gene in self:
            yield gene.model_dump_json()
