"""
Pydantic models for Ensembl gene structures parsed from GFF3 files.

Represents the domain-specific structures: genes, transcripts, exons, CDS, and UTR regions.
"""

from typing import List, Optional, Dict, Any

from niagads.common.genomic.regions.models import GenomicRegion
from niagads.common.models.base import CustomBaseModel
from pydantic import Field


class ExonModel(CustomBaseModel):
    """
    Represents a single exon in a transcript.

    Captures the genomic coordinates and identification of the exon.
    """

    id: str = Field(
        title="Exon ID",
        description="Ensembl exon identifier",
    )
    location: GenomicRegion = Field(
        title="Location",
        description="Genomic coordinates of the exon",
    )
    rank: Optional[int] = Field(
        default=None,
        title="Rank",
        description="Exon rank within the transcript (1-based)",
    )

    def __str__(self) -> str:
        return self.id


class CDSRegion(CustomBaseModel):
    """
    Represents a coding DNA sequence (CDS) region within a transcript.

    Captures the genomic coordinates and reading frame phase.
    """

    location: GenomicRegion = Field(
        title="Location",
        description="Genomic coordinates of the CDS region",
    )
    phase: Optional[int] = Field(
        default=None,
        title="Phase",
        description="Reading frame (0, 1, or 2)",
    )

    def __str__(self) -> str:
        return str(self.location)


class UTRRegion(CustomBaseModel):
    """
    Represents an untranslated region (UTR) within a transcript.

    UTRs are exonic regions not translated into protein. They include
    5' UTR (before the start codon) and 3' UTR (after the stop codon).
    """

    location: GenomicRegion = Field(
        title="Location",
        description="Genomic coordinates of the UTR region",
    )
    region_type: str = Field(
        title="Region Type",
        description="UTR type: 5UTR or 3UTR",
    )

    def __str__(self) -> str:
        return f"{self.region_type}:{self.location}"


class CodonRegion(CustomBaseModel):
    """
    Represents a start or stop codon region.

    Captures the precise boundaries of translation initiation (start codon)
    or termination (stop codon).
    """

    location: GenomicRegion = Field(
        title="Location",
        description="Genomic coordinates of the codon",
    )
    codon_type: str = Field(
        title="Codon Type",
        description="Type of codon: start_codon or stop_codon",
    )

    def __str__(self) -> str:
        return f"{self.codon_type}:{self.location}"


class TranscriptModel(CustomBaseModel):
    """
    Represents a transcript (mRNA isoform) of a gene.

    Contains transcript-level information including location, biotype,
    and structural features (exons, CDS regions, UTRs, and codons).
    """

    id: str = Field(
        title="Transcript ID",
        description="Ensembl transcript identifier",
    )
    location: GenomicRegion = Field(
        title="Location",
        description="Genomic coordinates spanning all exons",
    )
    source: Optional[str] = Field(
        default=None,
        title="Source",
        description="Annotation source (e.g., ensembl, havana)",
    )
    biotype: Optional[str] = Field(
        default=None,
        title="Biotype",
        description="Transcript biotype (e.g., protein_coding, lncRNA)",
    )
    is_canonical: Optional[bool] = Field(
        default=None,
        title="Is Canonical",
        description="Whether this is the canonical transcript",
    )
    exons: List[ExonModel] = Field(
        default_factory=list,
        title="Exons",
        description="Exons in this transcript",
    )
    cds: List[CDSRegion] = Field(
        default_factory=list,
        title="CDS Regions",
        description="Coding DNA sequence regions",
    )
    utrs: List[UTRRegion] = Field(
        default_factory=list,
        title="UTR Regions",
        description="Untranslated regions (5' and 3' UTRs)",
    )
    codons: List[CodonRegion] = Field(
        default_factory=list,
        title="Codons",
        description="Start and stop codon locations",
    )
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        title="Additional Attributes",
        description="Other GFF3 attributes not explicitly modeled",
    )

    def __str__(self) -> str:
        return self.id


class GeneModel(CustomBaseModel):
    """
    Represents a gene with its associated transcripts.

    Contains gene-level information including identifiers, location,
    biotype, and associated transcripts with complete structural information.
    """

    id: str = Field(
        title="Gene ID",
        description="Ensembl gene identifier",
    )
    symbol: Optional[str] = Field(
        default=None,
        title="Gene Symbol",
        description="Official gene symbol (e.g., HGNC symbol)",
    )
    location: GenomicRegion = Field(
        title="Location",
        description="Genomic coordinates spanning all transcripts",
    )
    source: Optional[str] = Field(
        default=None,
        title="Source",
        description="Annotation source (e.g., ensembl, havana)",
    )
    biotype: Optional[str] = Field(
        default=None,
        title="Biotype",
        description="Gene biotype (e.g., protein_coding, lncRNA, pseudogene)",
    )
    description: Optional[str] = Field(
        default=None,
        title="Description",
        description="Human-readable gene description",
    )
    score: Optional[float] = Field(
        default=None,
        title="Score",
        description="Quality/confidence score for the gene feature",
    )
    transcripts: List[TranscriptModel] = Field(
        default_factory=list,
        title="Transcripts",
        description="Transcripts for this gene",
    )
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        title="Additional Attributes",
        description="Other GFF3 attributes not explicitly modeled",
    )

    def __str__(self) -> str:
        return self.symbol or self.id
