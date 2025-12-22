import base64
import hashlib
from typing import Union

from ga4gh.core import ga4gh_identify
from ga4gh.vrs.dataproxy import create_dataproxy, DataProxyValidationError
from ga4gh.vrs.extras.translator import AlleleTranslator
from ga4gh.vrs.models import Allele, SequenceLocation, SequenceReference
from ga4gh.vrs.normalize import normalize
from niagads.common.core import ComponentBaseMixin
from niagads.enums.core import CaseInsensitiveEnum
from niagads.exceptions.core import ValidationError
from niagads.genomics.features.region.core import GenomicRegion
from niagads.genomics.features.variant.core import Variant, VariantType
from niagads.genomics.sequence.chromosome import Human
from niagads.genomics.sequence.core import Assembly
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches


class VariantNomenclature(CaseInsensitiveEnum):
    HGVS = "hgvs"
    SPDI = "spdi"
    BEACON = "beacon"
    GNOMAD = "gnomad"
    POSITIONAL = "positional"

    _regexp_map = {
        "hgvs": RegularExpressions.HGVS,
        "spdi": RegularExpressions.SPDI,
        "beacon": RegularExpressions.BEACON_VARIANT_ID,
        "gnomad": RegularExpressions.GNOMAD_VARIANT_ID,
        "positional": RegularExpressions.POSITIONAL_VARIANT_ID,
    }

    def is_valid(self, variant_id: str, fail_on_error: bool = False) -> bool:
        is_valid = matches(self._regexp_map[self.value], variant_id)
        if not is_valid and fail_on_error:
            raise ValueError(f"Invalid '{self.name}' variant: {variant_id}.")
        else:
            return is_valid

    @classmethod
    def gnomad2positional(cls, variant_id: str):
        if cls.POSITIONAL.is_valid(variant_id):
            return variant_id.replace(":", "-")
        else:
            raise ValueError(
                f"Cannot convert: '{variant_id}' is not a valid 'POSITIONAL' variant identifier."
            )

    @classmethod
    def positional2gnomad(cls, variant_id: str):
        if cls.GNOMAD.is_valid(variant_id):
            return variant_id.replace("-", ":")
        else:
            raise ValueError(
                f"Cannot convert: '{variant_id}' is not a valid 'GNOMAD' variant identifier."
            )


class PrimaryKeyGenerator(ComponentBaseMixin):
    def __init__(
        self,
        genome_build: Assembly,
        seqrepo_service_url: str,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        self._vrs_service: GA4GHVRSService = GA4GHVRSService(
            genome_build, seqrepo_service_url, debug=debug, verbose=verbose
        )

    def primary_key(self, variant: Variant):
        match variant.type:
            case VariantType.SV:
                return self.sv_primary_key(variant)
            case VariantType.INDEL | VariantType.DEL | VariantType.INS:
                pass
            case _:  # SNV or MNV
                pass

    def sv_primary_key(self, variant: Variant):
        if variant.type != VariantType.SV:
            raise ValueError(
                f"Invalid structural variant: '{variant.positional_id}' "
                "is identified as a '{variant.type.name}'."
            )

    def indel_primary_key(self, variant: Variant):
        if variant.type not in [VariantType.INDEL, VariantType.DEL, VariantType.INS]:
            raise ValueError(
                f"Invalid insertion and/or deletion variant: '{variant.positional_id}' "
                "is identified as a '{variant.type.name}'."
            )


class GA4GHVRSService(ComponentBaseMixin):
    """
    this normalizes, generates primary keys, and validates, standardizes using ga4gh.vrs
    """

    def __init__(
        self,
        assembly: Assembly,
        seqrepo_service_url: str,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        self._seqrepo_data_proxy = create_dataproxy(f"seqrepo+{seqrepo_service_url}")
        self._assembly: Assembly = assembly

        self._allele_translator = AlleleTranslator(
            data_proxy=self._seqrepo_data_proxy,
            default_assembly_name=str(self._assembly),
        )

    def validate_sequence(
        self, location: GenomicRegion, sequence: str, fail_on_error: bool = True
    ):
        """
        Validate that a given sequence matches the reference genome at the specified location.

        Args:
            location (GenomicRegion): Genomic region with chromosome, start, and end coordinates.
            sequence (str): Sequence to validate against the reference genome.
            fail_on_error (bool, optional): If True, raise ValidationError on mismatch.
                If False, log a warning instead. Default is True.

        Raises:
            ValidationError: If the sequence does not match the reference genome
                and fail_on_error is True.
        """
        self.get_refget_accession(location.chromosome)  # verify chromosome
        start = (location.start if location.zero_based else location.start - 1,)
        try:
            self._seqrepo_data_proxy.validate_ref_seq(
                f"{self._assembly}:{location.chromosome}",
                start,
                start + len(sequence),
                sequence,
                require_validation=fail_on_error,
            )
        except DataProxyValidationError:  # catch and reraise
            raise ValidationError(
                f"Invalid sequence: {sequence} does not match reference genome in the region: {str(location)}."
            )

    def create_vrs_allele(
        self,
        variant_id: str,
        variant_id_type: VariantNomenclature,
        require_validation: bool = True,
        normalize: bool = True,
        as_json: bool = True,
    ) -> Allele:
        """
        Convert a variant identifier to a GA4GH VRS Allele object.

        Args:
            variant_id (str): The variant identifier.
            variant_id_type (VariantNomenclature): the type of the variant identifier
            require_validation (bool, optional): If True, validate the input identifier before translation. Default is True.
                If false, invalid references sequences will be logged as warnings.
            normalize (bool, optional): If True, normalize the resulting Allele object. Default is True.
            as_json (bool, optional): If True, return the Allele as a JSON dict; otherwise, return the Allele object. Default is True.

        Returns:
            dict or Allele: GA4GH VRS Allele object as a JSON dict (if as_json=True) or as a model instance (if as_json=False).

        Raises:
            ValueError: If the variant_id is not valid for the given id_type.
            ValidationError: If require_validation is True and reference allele sequence does not match
                the reference genome.
        """

        variant_id_type.is_valid(
            variant_id, fail_on_error=True
        )  # validate variant string

        if variant_id_type == VariantNomenclature.POSITIONAL:
            allele = self._allele_translator.translate_from(
                VariantNomenclature.positional2gnomad(variant_id),
                VariantNomenclature.GNOMAD.value,
                require_validation=require_validation,
                do_normalize=normalize,
            )
        else:
            allele = self._allele_translator.translate_from(
                variant_id,
                variant_id_type.value,
                require_validation=require_validation,
                do_normalize=normalize,
            )
        return allele.model_dump(exclude_none=True) if as_json else allele

    def allele_to_positional_variant(self, vrs_allele: Allele) -> str:
        """
        Convert a GA4GH VRS Allele object to a positional variant string (chrom:start:ref:alt).

        Args:
            vrs_allele (Allele): GA4GH VRS Allele object.

        Returns:
            str: Positional variant string in the format 'chrom:start:ref:alt'.
        """
        if vrs_allele.location.end - vrs_allele.location.start >= 50:
            raise ValueError(
                "Cannot convert: unable to generate positional ID "
                "for structural variant (sequence length >= 50bp)"
            )

        chrm = self.refget_to_chromosome(
            vrs_allele.location.sequenceReference.refgetAccession
        )
        ref = self.get_sequence(vrs_allele.location)
        alt = vrs_allele.state.sequence
        return f"{chrm}:{vrs_allele.location.start}:{ref}:{alt}"

    def allele_to_hgvs(self, vrs_allele: Allele) -> str:
        """
        Convert a GA4GH VRS Allele object to an HGVS string.

        Args:
            vrs_allele (Allele): GA4GH VRS Allele object.

        Returns:
            str: HGVS representation of the allele.
        """
        return self._allele_translator.translate_to(
            vrs_allele, VariantNomenclature.HGVS.value
        )

    def allele_to_spdi(self, vrs_allele: Allele) -> str:
        """
        Convert a GA4GH VRS Allele object to an SPDI string.

        Args:
            vrs_allele (Allele): GA4GH VRS Allele object.

        Returns:
            str: SPDI representation of the allele.
        """
        return self._allele_translator.translate_to(
            vrs_allele, VariantNomenclature.SPDI.value
        )

    def positional_variant_to_hgvs(self, variant_id: str) -> str:
        """
        Convert a positional variant identifier to HGVS nomenclature.

        Args:
            variant_id (str): The variant identifier.

        Returns:
            str: HGVS representation of the variant.

        Raises:
            ValueError: If the input is not a valid identifier.
        """
        if VariantNomenclature.POSITIONAL.is_valid(variant_id):
            variant_id = VariantNomenclature.positional2gnomad(variant_id)

        if not VariantNomenclature.GNOMAD.is_valid(variant_id):
            raise ValueError(
                f"Cannot convert: invalid positional variant identifier {variant_id}."
            )

        allele: Allele = self.create_vrs_allele(
            variant_id,
            VariantNomenclature.GNOMAD,
            as_json=False,
            require_validation=False,
            normalize=False,
        )
        return self.allele_to_hgvs(allele)

    def positional_variant_to_spdi(self, variant_id: str) -> str:
        """
        Convert a positional variant identifier to SPDI nomenclature.

        Args:
            variant_id (str): The variant identifier.

        Returns:
            str: SPDI representation of the variant.

        Raises:
            ValueError: If the input is not a valid identifier.
        """
        if VariantNomenclature.POSITIONAL.is_valid(variant_id):
            variant_id = VariantNomenclature.positional2gnomad(variant_id)

        if not VariantNomenclature.GNOMAD.is_valid(variant_id):
            raise ValueError(
                f"Cannot convert: invalid positional variant identifier {variant_id}."
            )

        allele: Allele = self.create_vrs_allele(
            variant_id,
            VariantNomenclature.GNOMAD,
            as_json=False,
            normalize=False,
            require_validation=False,
        )
        return self.allele_to_spdi(allele)

    def get_refget_accession(self, chromosome: Human):
        """
        Get the GA4GH refget accession for a given chromosome.
        # TODO - handle refseq
        # TODO - test "M", might require "MT"

        Args:
            chromosome (Human): Chromosome object (e.g., Human chromosome enum).

        Returns:
            str: GA4GH refget accession for the chromosome.

        Raises:
            ValueError if chromosome cannot be mapped to a RefGet accession.
        """

        refget_accession = self._seqrepo_data_proxy.translate_sequence_identifier(
            f"{self._assembly}:{str(chromosome)}", "ga4gh"
        )[0]
        if not refget_accession:
            raise ValueError(
                f"Unable to map chromosome {chromosome} to a GA4GH RefGet Accession"
            )
        return refget_accession

    def get_sequence(self, location: Union[GenomicRegion, SequenceLocation]):
        """
        Retrieve the reference sequence for a specified genomic region.

        Args:
            region (GenomicRegion): Genomic region with chromosome, start, and end coordinates.

        Returns:
            str: Reference sequence string for the region.
        """
        if isinstance(location, GenomicRegion):
            refget_accession = self.get_refget_accession(location.chromosome)
        else:
            refget_accession = location.sequenceReference.refgetAccession
        return self._seqrepo_data_proxy.get_sequence(
            refget_accession, start=location.start, end=location.length
        )

    def refget_to_chromosome(self, refget_accession: str):
        """
        Translate a GA4GH refget accession back to the chromosome identifier for the current assembly.

        Args:
            refget_accession (str): GA4GH refget accession string.

        Returns:
            str: Chromosome identifier for the current assembly.
        """
        return self._seqrepo_data_proxy.translate_sequence_identifier(
            refget_accession, self._assembly
        )

    def create_vrs_sequence_location(self, region: GenomicRegion):
        """
        Create and normalize a GA4GH VRS SequenceLocation object for a given genomic region.

        TODO: normalize should either adjust or raise errors if end
        coordinates are beyond sequence length).  Need to test and decide how to handle

        Args:
            region (GenomicRegion): Genomic region with chromosome, start, and end coordinates.

        Returns:
            SequenceLocation: Normalized GA4GH VRS SequenceLocation object for the region.
        """
        refget_accession = self.get_refget_accession(region.chromosome)

        location = SequenceLocation(
            sequenceReference=SequenceReference(refgetAccession=refget_accession),
            start=region.start,
            end=region.length,
        )
        location.id = ga4gh_identify(location)  # compute ga4gh identifier
        return normalize(location)

    def normalize_positional_variant(
        self, variant_id: str, require_validation: bool = False
    ):
        """
        Normalize variant alleles for a positional variant identifier using
        GA4GH VRS.

        Variant normalization involves left/right-aligning indels,
        trimming common bases, and ensuring that the variant is described
        in the most parsimonious way possible.

        for details on GA4GH VRS allele normalization, see:
        https://vrs.ga4gh.org/en/latest/conventions/normalization.html

        Args:
            variant_id (str): The positional variant identifier to normalize.
            require_validation (bool, optional): If True, validate the input
                identifier and reference sequence. Default is False.

        Returns:
            str: Normalized positional variant string in the format
                'chrom:start:ref:alt'.

        Raises:
            ValueError: If the variant_id is not valid for the positional
                nomenclature.
            ValidationError: If require_validation is True and the reference
                sequence does not match the reference genome.
        """
        allele: Allele = self.create_vrs_allele(
            variant_id=variant_id,
            variant_id_type=VariantNomenclature.POSITIONAL,
            as_json=False,
            normalize=True,
            require_validation=require_validation,
        )
        return self.allele_to_positional_variant(allele)
