from bisect import bisect_right
from collections import OrderedDict
import hashlib
import json
import logging
from typing import Optional, Union

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
from niagads.common.variant.types import VariantClass
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
        bin_index_reference: Optional[dict] = None,
        debug: bool = False,
        verbose: bool = False,
        logger=None,
    ):
        super().__init__(debug=debug, verbose=verbose, logger=logger)
        # self.logger.propagate = True
        self._vrs_service: GA4GHVRSService = GA4GHVRSService(
            genome_build,
            seqrepo_service_url,
            bin_index_reference=bin_index_reference,
            debug=debug,
            verbose=verbose,
            logger=logger,
        )

    @property
    def ga4gh_service(self):
        return self._vrs_service

    def set_primary_key(self, variant: VariantRecord, require_validation: bool = True):
        if variant.variant_class.is_structural_variant():
            self.sv_primary_key(variant)
        elif variant.variant_class.is_short_indel():
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

        For indels where the combined length of ref and alt alleles is ≤ 20,
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
        if len(variant.ref) + len(variant.alt) > 50:
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


class BinCachedSeqRepoDataProxy:
    def __init__(
        self,
        data_proxy,
        genome_build: GenomeBuild,
        bin_index_reference: Optional[dict] = None,
        max_cached_bin_width: int = 1_000_000,
        max_cache_size: int = 8,
    ):
        self._data_proxy = data_proxy
        self._assembly = genome_build
        self._bin_index_reference = bin_index_reference
        self._max_cached_bin_width = max_cached_bin_width
        self._sequence_cache = OrderedDict()
        self._max_cache_size = max_cache_size
        self._refget_chromosome_cache = {}
        self._identifier_refget_cache = {}

    def __getattr__(self, name):
        return getattr(self._data_proxy, name)

    def validate_ref_seq(
        self,
        sequence_id: str,
        start_pos: int,
        end_pos: int,
        ref: str,
        require_validation: bool = True,
    ) -> None:
        correct_ref = self.get_sequence(sequence_id, start_pos, end_pos)
        if correct_ref != ref:
            err_msg = (
                f"Reference mismatch at {sequence_id} position {start_pos}-{end_pos} "
                f"(input gave '{ref}' but correct ref is '{correct_ref}')"
            )
            logging.getLogger("ga4gh.vrs.dataproxy").warning(err_msg)
            if require_validation:
                raise DataProxyValidationError(err_msg)

    def get_sequence(
        self, identifier: str, start: Optional[int] = None, end: Optional[int] = None
    ) -> str:
        if start is None or end is None:
            return self._data_proxy.get_sequence(identifier, start=start, end=end)
        if not isinstance(start, int) or not isinstance(end, int):
            return self._data_proxy.get_sequence(identifier, start=start, end=end)

        sequence_ref = self._resolve_sequence_reference(identifier)
        if sequence_ref is None:
            return self._data_proxy.get_sequence(identifier, start=start, end=end)

        chromosome, refget_accession = sequence_ref
        bin_match = self._find_cached_bin(chromosome, start, end)
        if bin_match is None:
            return self._data_proxy.get_sequence(identifier, start=start, end=end)

        bin_index, bin_start, bin_end = bin_match
        cache_key = (refget_accession, str(bin_index))

        cached = self._sequence_cache.get(cache_key)
        if cached is None:
            sequence = self._data_proxy.get_sequence(
                refget_accession, start=bin_start, end=bin_end
            )
            cached = (bin_start, bin_end, sequence)
            self._sequence_cache[cache_key] = cached
            if len(self._sequence_cache) > self._max_cache_size:
                self._sequence_cache.popitem(last=False)
        else:
            self._sequence_cache.move_to_end(cache_key)

        cached_start, _, sequence = cached
        return sequence[start - cached_start : end - cached_start]

    def _resolve_sequence_reference(
        self, identifier: str
    ) -> Optional[tuple[str, str]]:
        chromosome = self._identifier_to_chromosome(identifier)
        if chromosome is None:
            return None

        refget_accession = self._identifier_to_refget_accession(identifier)
        if refget_accession is None:
            return None

        return chromosome, refget_accession

    def _identifier_to_chromosome(self, identifier: str) -> Optional[str]:
        assembly_prefix = f"{self._assembly}:"
        if identifier.startswith(assembly_prefix):
            return identifier.split(":", maxsplit=1)[1]

        cache_key = (
            identifier if identifier.startswith("ga4gh:") else f"ga4gh:{identifier}"
        )
        if cache_key in self._refget_chromosome_cache:
            return self._refget_chromosome_cache[cache_key]

        try:
            chromosome = self._data_proxy.translate_sequence_identifier(
                cache_key, self._assembly
            )[0].split(":", maxsplit=1)[1]
        except Exception:
            return None

        self._refget_chromosome_cache[cache_key] = chromosome
        return chromosome

    def _identifier_to_refget_accession(self, identifier: str) -> Optional[str]:
        if identifier.startswith("ga4gh:"):
            return identifier

        if identifier.startswith("SQ."):
            return f"ga4gh:{identifier}"

        if identifier in self._identifier_refget_cache:
            return self._identifier_refget_cache[identifier]

        try:
            refget_accession = self._data_proxy.translate_sequence_identifier(
                identifier, "ga4gh"
            )[0]
        except Exception:
            return None

        self._identifier_refget_cache[identifier] = refget_accession
        return refget_accession

    def _find_cached_bin(
        self, chromosome: str, start: int, end: int
    ) -> Optional[tuple[str, int, int]]:
        if not self._bin_index_reference:
            return None

        chromosome_bins = self._bin_index_reference.get(chromosome)
        if not chromosome_bins:
            return None

        one_based_start = start + 1
        one_based_end = max(one_based_start, end)

        matches = []
        for level, level_bins in chromosome_bins.items():
            starts = level_bins["starts"]
            bins = level_bins["bins"]
            split_index = bisect_right(starts, one_based_start) - 1
            if split_index < 0:
                continue
            bin_start = starts[split_index]
            bin_end, bin_index = bins[split_index]
            if one_based_end <= bin_end:
                width = bin_end - bin_start + 1
                if width <= self._max_cached_bin_width:
                    matches.append((width, level, bin_index, bin_start, bin_end))

        if not matches:
            return None

        _, _, bin_index, bin_start, bin_end = min(matches, key=lambda match: match[0])
        return bin_index, bin_start - 1, bin_end


class GA4GHVRSService(ComponentBaseMixin):
    """
    this normalizes, generates primary keys, and validates, standardizes using ga4gh.vrs
    """

    def __init__(
        self,
        genome_build: GenomeBuild,
        seqrepo_service_url: str,
        bin_index_reference: Optional[dict] = None,
        debug: bool = False,
        verbose: bool = False,
        logger=None,
    ):
        super().__init__(debug=debug, verbose=verbose, logger=logger)
        seqrepo_data_proxy = create_dataproxy(f"seqrepo+{seqrepo_service_url}")
        self._seqrepo_data_proxy = BinCachedSeqRepoDataProxy(
            seqrepo_data_proxy,
            genome_build,
            bin_index_reference=bin_index_reference,
        )
        self._assembly: GenomeBuild = genome_build
        self._refget_accession_cache: dict = {}

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

    def snv_to_vrs_allele(self, variant: VariantRecord, as_json: bool = True):
        """
        Create a GA4GH VRS Allele for an SNV without seqrepo lookups.

        For SNVs, no normalization is needed—construct the Allele directly from
        the variant's ref/alt and cached refget accession for the chromosome.

        Args:
            variant (VariantRecord): SNV variant with ref and alt alleles.
            as_json (bool, optional): If True, return as JSON dict; otherwise return Allele object.
                Default is True.

        Returns:
            dict or Allele: GA4GH VRS Allele object.
        """
        region: ZeroBasedGenomicRegion = OneBasedGenomicRegion(
            chromosome=variant.chromosome,
            start=variant.span.start,
            end=variant.span.end,
        ).to_zero_based_region()

        vrs_location = self.create_vrs_sequence_location(
            region, normalize=False, compute_id=True
        )

        state = LiteralSequenceExpression(sequence=variant.alt)
        allele = Allele(location=vrs_location, state=state)
        allele.id = ga4gh_identify(allele)

        return allele.model_dump(exclude_none=True) if as_json else allele

    def variant_to_vrs_allele(
        self,
        variant: VariantRecord,
        require_validation: bool = True,
        normalize: bool = True,
        as_json: bool = True,
    ):
        if variant.variant_class.is_structural_variant():
            return self.sv_to_vrs_allele(variant, as_json=as_json)
        elif variant.variant_class == VariantClass.SNV:
            return self.snv_to_vrs_allele(variant, as_json=as_json)
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
            chrm, pos, ref, alt = variant_id.split(":")
            # basically save time of the refget accession lookup
            refget_accession = self.get_refget_accession(chrm).replace("ga4gh:", "")
            start = int(pos) - 1
            variant_json = {
                "refget_accession": refget_accession,
                "start": start,
                "end": start + len(ref),
                "literal_sequence": alt,
            }
            allele = self._allele_translator._create_allele(
                variant_json,
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
            ref = self.get_sequence(vrs_allele.location)
            if vrs_allele.state.length == 0:
                alt = "-"
            elif (
                vrs_allele.state.sequence is None
                or vrs_allele.state.sequence.root == ""
            ):
                repeat_length = vrs_allele.state.repeatSubunitLength
                repeat_sequence = ref[:repeat_length]
                alt = (
                    repeat_sequence * ((vrs_allele.state.length // repeat_length) + 1)
                )[: vrs_allele.state.length]
            else:
                alt = vrs_allele.state.sequence.root
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
        key = f"{self._assembly}:{str(chromosome)}"
        refget_accession = self._refget_accession_cache.get(key, None)
        if not refget_accession:
            refget_accession = self._seqrepo_data_proxy.translate_sequence_identifier(
                key, "ga4gh"
            )[0]
            self._refget_accession_cache[key] = refget_accession
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
            start=region.start,
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

    def fast_normalize_variant(self, positional_id: str) -> str:
        chrom, pos, ref, alt = positional_id.split(":")
        ref = "" if ref == "-" else ref
        alt = "" if alt == "-" else alt

        # trim shared suffix
        while ref and alt and ref[-1] == alt[-1] and (len(ref) > 1 or len(alt) > 1):
            ref = ref[:-1]
            alt = alt[:-1]

        # trim shared prefix
        while ref and alt and ref[0] == alt[0] and (len(ref) > 1 or len(alt) > 1):
            ref = ref[1:]
            alt = alt[1:]
            pos = int(pos) + 1

        return f"{chrom}:{pos}:{ref or '-'}:{alt or '-'}"
