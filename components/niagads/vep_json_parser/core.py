"""
utils for parsing and manipulating the JSON output of [Ensembl's Variant
Effect Predictor (VEP) software](https://useast.ensembl.org/info/docs/tools/vep/index.html)
"""

import json
from typing import Optional, Union

from niagads.common.core import ComponentBaseMixin
from niagads.common.models.base import CustomBaseModel
from niagads.enums.core import CaseInsensitiveEnum
from niagads.genome_reference.human import HumanGenome
from niagads.utils.list import is_overlapping_list, qw
from niagads.vcf.types import VCFEntry
from pydantic import BaseModel, ConfigDict, field_validator

CODING_CONSEQUENCES = qw(
    "synonymous_variant missense_variant inframe_insertion inframe_deletion stop_gained stop_lost stop_retained_variant start_lost frameshift_variant coding_sequence_variant"
)


SCORE_FIELDS = [
    "cadd_raw",
    "cadd_phred",
    "enformer_sad",
    "enformer_sar",
]

IMPACTED_GENE_FIELDS = [
    "gene_symbol",
    "loftool",
]

EXCLUDED_ANNOTATION_FIELDS = [
    "hgnc_id",
    "uniparc",
    "gene_symbol_source",
]


class ConsequenceType(CaseInsensitiveEnum):
    TRANSCRIPT = "transcript"
    REGULATORY_FEATURE = "regulatory_feature"
    MOTIF_FEATURE = "motif_feature"
    INTERGENIC = "intergenic"


class MotifFeature(CustomBaseModel):
    id: str
    motif_name: str
    motif_pos: int
    motif_score_chang: float


class RegulatoryFeature(CustomBaseModel):
    id: str
    biotype: str


class GeneContext(CustomBaseModel):
    id: str
    gene_symbol: Optional[str] = None
    biotype: str
    loftool: Optional[float] = None
    gene_pheno: Optional[bool] = None


class ProteinContext(CustomBaseModel):
    id: str

    trembl: Optional[list[str]] = None
    swissprot: Optional[list[str]] = None

    protein_start: Optional[int] = None
    protein_end: Optional[int] = None
    amino_acids: Optional[str] = None
    hgvsp: Optional[str] = None

    sift_score: Optional[float] = None
    sift_prediction: Optional[str] = None
    polyphen_score: Optional[float] = None
    polyphen_prediction: Optional[str] = None


class TranscriptContext(CustomBaseModel):
    id: str

    canonical: Optional[bool] = None
    appris: Optional[str] = None
    tsl: Optional[int] = None
    strand: Optional[int] = None
    mane: Optional[list[str]] = None
    mane_select: Optional[str] = None
    ccds: Optional[str] = None

    distance: Optional[int] = None
    tssdistance: Optional[int] = None

    cdna_start: Optional[int] = None
    cdna_end: Optional[int] = None
    cds_start: Optional[int] = None
    cds_end: Optional[int] = None

    exon: Optional[str] = None
    intron: Optional[str] = None

    codons: Optional[str] = None
    hgvsc: Optional[str] = None

    gene: GeneContext
    protein: Optional[ProteinContext] = None


class Consequence(CustomBaseModel):
    consequence_type: ConsequenceType
    consequence_terms: list[str]
    impact: str
    is_coding: Optional[bool] = None
    hgvsg: Optional[str] = None
    feature: Optional[Union[TranscriptContext, RegulatoryFeature, MotifFeature]] = None

    flags: Optional[list[str]] = None


class PredictedAnnotation(CustomBaseModel):
    predictor_scores: Optional[dict] = None
    predicted_consequences: dict[str, list[Consequence]]


class VariantVEPAnnotationEntry(CustomBaseModel):
    positional_id: str
    chromosome: HumanGenome
    position: int
    ref: str
    alt: str

    most_severe_consequence: Optional[Consequence] = None
    allele_frequency: Optional[dict] = None
    predicted_annotations: Optional[PredictedAnnotation] = None


class VEPEntry(BaseModel):
    id: str
    seq_region_name: str
    start: int
    end: int
    strand: int
    allele_string: str
    assembly_name: str
    variant_class: str
    most_severe_consequence: str
    input: VCFEntry
    colocated_variants: Optional[list[dict]] = None
    transcript_consequences: Optional[list[dict]] = None
    regulatory_feature_consequences: Optional[list[dict]] = None
    motif_feature_consequences: Optional[list[dict]] = None
    intergenic_consequences: Optional[list[dict]] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("input", mode="before")
    @classmethod
    def parse_input_str(cls, v: str) -> VCFEntry:
        """transform VCF input string into VCFEntry object."""
        return VCFEntry.from_line(v)


class VEPJSONParser(ComponentBaseMixin):
    """class to organize utils for parsing VEP JSON output"""

    def __init__(self, debug=False, verbose=False, initialize_logger=True, logger=None):
        super().__init__(debug, verbose, initialize_logger, logger)

    def parse(self, vep_output: Union[dict, str]):
        vep_json = (
            vep_output if isinstance(vep_output, dict) else json.loads(vep_output)
        )

        raw_annotation = VEPEntry(**vep_json)
        chromosome = raw_annotation.input.chrom
        position = raw_annotation.input.pos
        ref = raw_annotation.input.ref

        variant_annotations: dict[str, VariantVEPAnnotationEntry] = {}
        for alt in raw_annotation.input.alt:
            allele_annotation = VariantVEPAnnotationEntry(
                positional_id=f"{chromosome}:{position}:{ref}:{alt}",
                chromosome=chromosome,
                position=position,
                ref=ref,
                alt=alt,
            )

            # allele frequencies
            if raw_annotation.colocated_variants:
                allele_annotation.allele_frequency = self.__extract_allele_frequencies(
                    raw_annotation.colocated_variants, alt, position
                )

            # predicted annotations
            allele_annotation.predicted_annotations = (
                self.__extract_predicted_annotations(raw_annotation, alt)
            )

            if allele_annotation.predicted_annotations is not None:
                allele_annotation.most_severe_consequence = (
                    self.__extract_most_severe_consequence(
                        allele_annotation.predicted_annotations.predicted_consequences
                    )
                )
            else:
                if allele_annotation.allele_frequency is None:
                    # if both frequencies and predicted annotations are none for this allele,
                    # there are no annotations
                    continue

            variant_annotations[alt] = allele_annotation
        return variant_annotations

    def __is_coding_consequence(self, conseqs):
        """returns True if any consequence term is a `CODING CONSEQUENCE`"""
        conseq_list = conseqs.split(",") if isinstance(conseqs, str) else conseqs
        return is_overlapping_list(conseq_list, CODING_CONSEQUENCES)

    def __extract_allele_frequencies(
        self, colocated_variants: dict, allele: str, position: int
    ):
        """extract frequencies from colocated_variants section - matching allele and end position

        "colocated_variants": [
                {
                        "frequencies": {
                                "G": {
                                        "gnomadg_amr": 0,
                                        "gnomadg_asj": 0,
                                        "gnomadg": 0,
                                        "gnomadg_eas": 0,
                                        "gnomadg_nfe": 0,
                                        "gnomadg_sas": 0,
                                        "gnomadg_afr": 0,
                                        "gnomadg_remaining": 0,
                                        "gnomadg_fin": 0
                                }
                        },
                        "strand": 1,
                        "seq_region_name": "7",
                        "start": 10091,
                        "allele_string": "A/C/G",
                        "end": 10091,
                        "id": "rs1410112108"
                }
        ]
        """

        for variant in colocated_variants:
            if variant["allele_string"] == "COSMIC_MUTATION":
                continue
            allele_freqs = variant.get("frequencies", {}).get(allele)
            if allele_freqs is not None and variant["end"] == position:
                # positional check is to weed out incorrectly matched normalized/overlapping variants
                return self.__organize_allele_frequencies(allele_freqs)
                # the same allele may occur in another colocated variant, but the freqs will be the same
        return None

    def __organize_allele_frequencies(self, frequencies: dict):
        """group frequencies by data source"""

        ESP_KEYS = ["aa", "ea"]

        gnomad = {}
        esp = {}
        genomes = {}

        key: str
        for key, value in frequencies.items():
            if value == 0:
                continue

            if "gnomad" in key:
                if "_" in key:
                    source, pop = key.split("_")
                else:
                    pop = "genomes"
                gnomad[pop] = value
            elif key in ESP_KEYS:
                esp[key] = value
            else:
                genomes[key] = value

        result = {
            k: v
            for k, v in [
                ("GnomAD", gnomad),
                ("1000Genomes", genomes),
                ("ESP", esp),
            ]
            if v
        }
        return result if result else None

    def __extract_predicted_annotations(self, entry: VEPEntry, allele: str):
        consequence_types: list[ConsequenceType] = [
            ConsequenceType(c) for c in ConsequenceType.list()
        ]
        predicted_consequences: dict[ConsequenceType, list[Consequence]] = {}
        predictor_scores = {}

        for ctype in consequence_types:
            conseq_array_name = f"{ctype.value}_consequences"
            raw_consequences = getattr(entry, conseq_array_name, None)
            if raw_consequences is None:
                continue

            matching = [
                c for c in raw_consequences if c.get("variant_allele") == allele
            ]
            if not matching:
                continue

            consequence_objs = []
            for raw_conseq in matching:
                # Extract and promote scores on first occurrence
                for score_field in SCORE_FIELDS:
                    if (
                        score_field not in predictor_scores
                        and score_field in raw_conseq
                    ):
                        predictor_scores[score_field] = raw_conseq[score_field]

                # Build feature object based on consequence type
                feature = None
                if ctype == ConsequenceType.TRANSCRIPT:
                    feature = self.__build_transcript_feature(raw_conseq)
                elif ctype == ConsequenceType.REGULATORY_FEATURE:
                    feature = self.__build_regulatory_feature(raw_conseq)
                elif ctype == ConsequenceType.MOTIF_FEATURE:
                    feature = self.__build_motif_feature(raw_conseq)

                # Create Consequence object

                is_coding = (
                    self.__is_coding_consequence(raw_conseq["consequence_terms"])
                    if ctype == ConsequenceType.TRANSCRIPT
                    else None
                )

                consequence = Consequence(
                    consequence_type=ctype,
                    consequence_terms=[
                        term.replace("_", " ")
                        for term in raw_conseq["consequence_terms"]
                    ],
                    impact=raw_conseq["impact"],
                    is_coding=is_coding,
                    hgvsg=raw_conseq.get("hgvsg"),
                    feature=feature,
                    flags=raw_conseq.get("flags"),
                )
                consequence_objs.append(consequence)

            if consequence_objs:
                predicted_consequences[conseq_array_name] = consequence_objs

        return (
            PredictedAnnotation(
                predictor_scores=predictor_scores if predictor_scores else None,
                predicted_consequences=predicted_consequences,
            )
            if predicted_consequences
            else None
        )

    def __build_transcript_feature(self, conseq: dict):
        gene = GeneContext(
            id=conseq["gene_id"],
            gene_symbol=conseq.get("gene_symbol"),
            biotype=conseq["biotype"].replace("_", " "),
            loftool=conseq.get("loftool"),
            gene_pheno=True if bool(conseq.get("gene_pheno", 0)) else None,
        )

        protein = None
        if "protein_id" in conseq:
            protein = ProteinContext(
                id=conseq["protein_id"],
                trembl=conseq.get("trembl"),
                swissprot=conseq.get("swissprot"),
                protein_start=conseq.get("protein_start"),
                protein_end=conseq.get("protein_end"),
                amino_acids=conseq.get("amino_acids"),
                hgvsp=conseq.get("hgvsp"),
                sift_score=conseq.get("sift_score"),
                sift_prediction=conseq.get("sift_prediction"),
                polyphen_score=conseq.get("polyphen_score"),
                polyphen_prediction=conseq.get("polyphen_prediction"),
            )

        return TranscriptContext(
            id=conseq["transcript_id"],
            canonical=bool(conseq.get("canonical", 0)),
            appris=conseq.get("appris"),
            tsl=conseq.get("tsl"),
            strand=conseq.get("strand"),
            mane=conseq.get("mane"),
            mane_select=conseq.get("mane_select"),
            ccds=conseq.get("ccds"),
            distance=conseq.get("distance"),
            tssdistance=conseq.get("tssdistance"),
            cdna_start=conseq.get("cdna_start"),
            cdna_end=conseq.get("cdna_end"),
            cds_start=conseq.get("cds_start"),
            cds_end=conseq.get("cds_end"),
            exon=conseq.get("exon"),
            intron=conseq.get("intron"),
            codons=conseq.get("codons"),
            hgvsc=conseq.get("hgvsc"),
            gene=gene,
            protein=protein,
        )

    def __build_regulatory_feature(self, conseq: dict):
        return RegulatoryFeature(
            id=conseq["regulatory_feature_id"],
            biotype=conseq["biotype"].replace("_", " "),
        )

    def __build_motif_feature(self, conseq: dict):
        return MotifFeature(
            id=conseq["motif_feature_id"],
            motif_name=conseq.get("motif_name", ""),
            motif_pos=conseq.get("motif_pos", 0),
            motif_score_chang=conseq.get("motif_score_change", 0.0),
        )

    def __extract_most_severe_consequence(
        self, conseqs: dict[ConsequenceType, list[Consequence]]
    ):
        """Retrieve the first (most severe) consequence from the consequences dict.

        Iterates through consequence types in definition order (transcript, regulatory,
        motif, intergenic) and returns the first consequence found.

        Args:
            conseqs: Dict mapping ConsequenceType to list of Consequence objects.

        Returns:
            First Consequence object found, or None if no consequences exist.
        """
        consequence_types = [f"{ct}_consequences" for ct in ConsequenceType.list()]
        for ctype in consequence_types:
            ctype_consequences = conseqs.get(ctype, None)
            if ctype_consequences is not None:
                return ctype_consequences[0]

        return None
