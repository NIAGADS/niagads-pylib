import hashlib
import json
import logging
from typing import Union

from ga4gh.core import ga4gh_identify
from ga4gh.vrs.dataproxy import DataProxyValidationError, create_dataproxy
from ga4gh.vrs.extras.translator import AlleleTranslator
from ga4gh.vrs.models import (
    Allele,
    SequenceLocation,
    SequenceReference,
    LengthExpression,
    ReferenceLengthExpression,
    LiteralSequenceExpression,
)
from ga4gh.vrs.normalize import normalize as vrs_normalize
from niagads.common.core import ComponentBaseMixin
from niagads.common.genomic.regions.models import (
    OneBasedGenomicRegion,
    ZeroBasedGenomicRegion,
)
from niagads.common.variant.models.record import VariantRecord
from niagads.exceptions.core import ValidationError
from niagads.ga4gh.types import VariantNomenclature
from niagads.genome_reference.human import GenomeBuild, HumanGenome

# hopefullu disable seqrepo INFO notices for each request to the service
logging.getLogger("ga4gh.vrs").setLevel(logging.WARNING)
logging.getLogger("seqrepo").setLevel(logging.WARNING)


class PrimaryKeyGenerator(ComponentBaseMixin):
    def __init__(
        self,
        genome_build: GenomeBuild,
        seqrepo_service_url: str,
        debug: bool = False,
        verbose: bool = False,
        logger=None,
    ):
        super().__init__(debug=debug, verbose=verbose, logger=logger)
        # self.logger.propagate = True
        self._vrs_service: GA4GHVRSService = GA4GHVRSService(
            genome_build, seqrepo_service_url, debug=debug, verbose=verbose
        )

    @property
    def ga4gh_service(self):
        return self._vrs_service

    def set_primary_key(self, variant: VariantRecord, require_validation: bool = True):
        if variant.variant_class.is_structural_variant():
            self.sv_primary_key(variant)
        if variant.variant_class.is_short_indel():
            self.short_indel_primary_key(variant, require_validation=require_validation)
        else:  # SNV / MNV - no normalization necessary
            variant.id = variant.positional_id

    def sv_primary_key(self, variant: VariantRecord):
        """
        Generate a unique primary key for a structural variant (SV) using a hashed
        GA4GH VRS SequenceLocation.

        The primary key is constructed from the variant class, chromosome, and the
        first 8 characters of a SHA-512 hash of the serialized SequenceLocation.
        This ensures uniqueness and reproducibility for SVs.

        This is following convention adopted by gnomAD; trace from:
        # https://github.com/broadinstitute/gnomad-browser/blob/3acd1354137b28b311f24ba14cb77478423af0ac/graphql-api/src/graphql/resolvers/va.ts#L135

        Example:
            "DEL_CHR1_8A1B2C3D"

        Args:
            variant (Variant): The structural variant to generate a primary key for.

        Returns:
            str: Unique primary key string for the SV.

        Raises:
            ValueError: If the variant is not a structural variant.
        """
        if not variant.variant_class.is_structural_variant():
            # 'short indels' will end up here if too long to be indexed w/out hash
            raise ValueError(f"Invalid structural variant: '{variant}' ")

        location: SequenceLocation = self._vrs_service.create_vrs_sequence_location(
            variant.genomic_region.to_zero_based_region(),
            compute_id=False,
            normalize=False,
        )
        hashed_location_id = hashlib.sha512(
            json.dumps(location.model_dump(exclude_none=True)).encode("utf-8")
        ).hexdigest()

        primary_key = (
            f"{str(variant.variant_class)}_"
            f"{variant.chromosome.name.upper()}_"
            f"{hashed_location_id[:8].upper()}"
        )

        self.logger.debug(
            f"Primary Key for SV: {variant.variant_class} - {str(variant)} = {primary_key}"
        )

        variant.id = primary_key

    def short_indel_primary_key(
        self, variant: VariantRecord, require_validation: bool = True
    ):
        """
        Generate a primary key for a short indel variant.

        For indels where the combined length of ref and alt alleles is ≤ 10,
        returns a normalized positional variant string for human readability.
        For longer indels, falls back to the hashed SV primary key convention.

        Args:
            variant (Variant): The indel variant to generate a primary key for.
            require_validation (bool, optional): If True, validate reference allele
                against reference sequence. Default is True.

        Returns:
            str: Primary key string for the indel variant.

        Raises:
            ValueError: If the variant is not a short indel.
        """
        if not variant.variant_class.is_short_indel():
            raise ValueError(
                f"Invalid short insertion and/or deletion variant: '{variant}' "
            )

        primary_key = variant.positional_id
        if len(variant.ref) + len(variant.alt) > 10:
            # too long to be human readable and indexable
            # Hash the entire Allele (includes ref/alt), not just location
            allele = (
                variant.ga4gh_vrs.model_dump()
                if variant.ga4gh_vrs is not None
                else self._vrs_service.variant_to_vrs_allele(
                    variant,
                    require_validation=require_validation,
                    normalize=False,
                    as_json=False,
                ).model_dump(exclude_none=True)
            )

            hashed_allele_id = hashlib.sha512(
                json.dumps(allele).encode("utf-8")
            ).hexdigest()

            primary_key = (
                f"{str(variant.variant_class).replace('SHORT_', '')}_"
                f"{variant.chromosome.name.upper()}_"
                f"{hashed_allele_id[:8].upper()}"
            )

        self.logger.debug(
            f"Primary Key for {variant.variant_class} - {str(variant)} = {primary_key}"
        )

        variant.id = primary_key


class GA4GHVRSService(ComponentBaseMixin):
    """
    this normalizes, generates primary keys, and validates, standardizes using ga4gh.vrs
    """

    def __init__(
        self,
        genome_build: GenomeBuild,
        seqrepo_service_url: str,
        debug: bool = False,
        verbose: bool = False,
        logger=None,
    ):
        super().__init__(debug=debug, verbose=verbose, logger=logger)
        self._seqrepo_data_proxy = create_dataproxy(f"seqrepo+{seqrepo_service_url}")
        self._assembly: GenomeBuild = genome_build

        self._allele_translator = AlleleTranslator(
            data_proxy=self._seqrepo_data_proxy,
            default_assembly_name=str(self._assembly),
        )

    def validate_sequence(
        self,
        location: ZeroBasedGenomicRegion,
        sequence: str,
        fail_on_error: bool = True,
    ):
        """
        Validate that a given sequence matches the reference genome at the specified location.

        Args:
            location (ZeroBasedGenomicRegion): Genomic region with chromosome, start, and end coordinates.
            sequence (str): Sequence to validate against the reference genome.
            fail_on_error (bool, optional): If True, raise ValidationError on mismatch.
                If False, log a warning instead. Default is True.

        Raises:
            ValidationError: If the sequence does not match the reference genome
                and fail_on_error is True.
        """
        self.get_refget_accession(location.chromosome)  # verify chromosome
        start = location.start
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

    def variant_to_vrs_allele(
        self,
        variant: VariantRecord,
        require_validation: bool = True,
        normalize: bool = True,
        as_json: bool = True,
    ):
        if variant.variant_class.is_structural_variant():
            return self.sv_to_vrs_allele(variant, as_json=as_json)
        else:
            return self.variant_id_to_vrs_allele(
                variant.positional_id,
                variant_id_type=VariantNomenclature.POSITIONAL,
                require_validation=require_validation,
                normalize=normalize,
                as_json=as_json,
            )

    def sv_to_vrs_allele(
        self,
        variant: VariantRecord,
        as_json: bool = True,
    ):
        region: ZeroBasedGenomicRegion = OneBasedGenomicRegion(
            chromosome=variant.chromosome,
            start=variant.span.start,
            end=variant.span.end,
        ).to_zero_based_region()

        vrs_location = self.create_vrs_sequence_location(
            region, normalize=False, compute_id=False
        )

        if variant.variant_class == "DEL":
            state = ReferenceLengthExpression(length=variant.length)
        elif variant.variant_class == "INS":
            state = LiteralSequenceExpression(sequence=variant.alt)
        else:
            state = LengthExpression(length=variant.length)

        allele = Allele(location=vrs_location, state=state)
        allele.id = ga4gh_identify(allele)

        return allele.model_dump(exclude_none=True) if as_json else allele

    def variant_id_to_vrs_allele(
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
                VariantNomenclature.convert_positional_to_gnomad(variant_id),
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
        allele.id = ga4gh_identify(allele)
        return allele.model_dump(exclude_none=True) if as_json else allele

    def allele_to_positional_variant(self, vrs_allele: Allele) -> str:
        """
        Convert a GA4GH VRS Allele object to a positional variant string
        (chrom:start:ref:alt).

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

        chrm: HumanGenome = self.refget_to_chromosome(
            vrs_allele.location.sequenceReference.refgetAccession
        )

        if vrs_allele.state.type == "LiteralSequenceExpression":
            if vrs_allele.location.start == vrs_allele.location.end:
                # normalized insertion
                ref = "-"
            else:
                ref = self.get_sequence(vrs_allele.location)
            alt = vrs_allele.state.sequence.root
        elif vrs_allele.state.type == "ReferenceLengthExpression":
            if vrs_allele.state.sequence.root == "":  # bug, happens sometimes
                ref = self.get_sequence(vrs_allele.location)
            else:
                ref = vrs_allele.state.sequence.root * vrs_allele.state.length
            alt = "-"
        elif vrs_allele.state.type == "LengthExpression":
            raise ValueError(
                "Cannot convert: allele type is a `LengthExpression`.  "
                "Is this a structural variant?"
            )
        else:
            raise ValueError(
                f"Cannot convert: Unknown allele type: {vrs_allele.state.type}"
            )

        # ga4gh is zero-based so need to add one to change back
        # to 1-based positional id
        return f"{chrm.value}:{vrs_allele.location.start + 1}:{ref}:{alt}"

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
            variant_id = VariantNomenclature.convert_positional_to_gnomad(variant_id)

        if not VariantNomenclature.GNOMAD.is_valid(variant_id):
            raise ValueError(
                f"Cannot convert: invalid positional variant identifier {variant_id}."
            )

        allele: Allele = self.variant_id_to_vrs_allele(
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
            variant_id = VariantNomenclature.convert_positional_to_gnomad(variant_id)

        if not VariantNomenclature.GNOMAD.is_valid(variant_id):
            raise ValueError(
                f"Cannot convert: invalid positional variant identifier {variant_id}."
            )

        allele: Allele = self.variant_id_to_vrs_allele(
            variant_id,
            VariantNomenclature.GNOMAD,
            as_json=False,
            normalize=False,
            require_validation=False,
        )
        return self.allele_to_spdi(allele)

    def get_refget_accession(self, chromosome: HumanGenome):
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

    def get_sequence(self, location: Union[ZeroBasedGenomicRegion, SequenceLocation]):
        """
        Retrieve the reference sequence for a specified genomic region.

        Args:
            region (ZeroBasedGenomicRegion): Genomic region with chromosome, start, and end coordinates.

        Returns:
            str: Reference sequence string for the region.
        """
        is_genomic_region: bool = isinstance(location, ZeroBasedGenomicRegion)

        if is_genomic_region:
            if location.inclusive_end:
                raise ValueError(
                    "Must transform to zero-based coordinates before using GA4GH annotators"
                )
            refget_accession = self.get_refget_accession(location.chromosome)

        else:
            refget_accession = location.sequenceReference.refgetAccession

        if not refget_accession.startswith("ga4gh"):
            refget_accession = f"ga4gh:{refget_accession}"

        start = location.start
        return self._seqrepo_data_proxy.get_sequence(
            refget_accession, start=start, end=location.end
        )

    def refget_to_chromosome(self, refget_accession: str) -> HumanGenome:
        """
        Translate a GA4GH refget accession back to the chromosome identifier for the current assembly.

        Args:
            refget_accession (str): GA4GH refget accession string.

        Returns:
            str: Chromosome identifier for the current assembly.
        """
        if not refget_accession.startswith("ga4gh"):
            refget_accession = f"ga4gh:{refget_accession}"
        return HumanGenome(
            self._seqrepo_data_proxy.translate_sequence_identifier(
                refget_accession, self._assembly
            )[0].split(":")[1]
        )

    def create_vrs_sequence_location(
        self,
        region: ZeroBasedGenomicRegion,
        normalize: bool = True,
        compute_id: bool = True,
    ):
        """
        Create a GA4GH VRS SequenceLocation object for a given genomic region and
        optionally normalize and assign a GA4GH identifier.

        TODO: normalize should either adjust or raise errors if end
        coordinates are beyond sequence length). Need to test and decide how to handle

        This function constructs a SequenceLocation using the provided chromosome,
        start, and end coordinates, assigns a refget accession, and can optionally
        normalize the location and compute its GA4GH identifier.

        Args:
            region (ZeroBasedGenomicRegion): Genomic region with chromosome, start, and end coordinates.
            normalize (bool, optional): If True, normalize the SequenceLocation. Default is True.
            compute_id (bool, optional): If True, compute and assign a GA4GH identifier.
                Default is True.

        Returns:
            SequenceLocation: Normalized GA4GH VRS SequenceLocation object for the region
                (if normalize=True),
            otherwise the raw SequenceLocation object.
        """
        if region.inclusive_end:
            raise ValueError(
                "Must transform to zero-based coordinates before using GA4GH annotators"
            )

        refget_accession = self.get_refget_accession(region.chromosome).replace(
            "ga4gh:", ""
        )

        location = SequenceLocation(
            sequenceReference=SequenceReference(refgetAccession=refget_accession),
            start=region.start - 1,  # genomic regions are 1-based
            end=region.end,
        )
        if compute_id:
            location.id = ga4gh_identify(location)  # compute ga4gh identifier
        return vrs_normalize(location) if normalize else location

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
        allele: Allele = self.variant_id_to_vrs_allele(
            variant_id=variant_id,
            variant_id_type=VariantNomenclature.POSITIONAL,
            as_json=False,
            normalize=True,
            require_validation=require_validation,
        )

        return self.allele_to_positional_variant(allele)
