from niagads.common.core import ComponentBaseMixin
from niagads.enums.core import CaseInsensitiveEnum
from niagads.genomics.sequence.core import Assembly
import hashlib
import base64
from ga4gh.core import ga4gh_identify, ga4gh_serialize, ga4gh_digest
from ga4gh.vrs.extras.translator import AlleleTranslator, _DataProxy
from ga4gh.vrs.dataproxy import create_dataproxy
from ga4gh.vrs.models import SequenceLocation, SequenceReference, Allele
from ga4gh.vrs.normalize import normalize
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches


class VariantNomenclature(CaseInsensitiveEnum):
    HGVS = "hgvs"
    SPDI = "spdi"
    BEACON = "beacon"
    GNOMAD = "gnomad"
    NIAGADS = "niagads"

    _regexp_map = {
        "hgvs": RegularExpressions.HGVS,
        "spdi": RegularExpressions.SPDI,
        "beacon": RegularExpressions.BEACON_VARIANT_ID,
        "gnomad": RegularExpressions.GNOMAD_VARIANT_ID,
        "niagads": RegularExpressions.NIAGADS_VARIANT_ID,
    }

    def is_valid(self, variant_id: str) -> bool:
        return matches(self._regexp_map[self.value], variant_id)

    @classmethod
    def niagads2gnomad(cls, variant_id: str):
        if cls.NIAGADS.is_valid(variant_id):
            return variant_id.replace(":", "-")
        else:
            raise ValueError(
                f"Cannot convert: {variant_id} is not a valid NIAGADS variant identifier."
            )

    @classmethod
    def gnomad2niagads(cls, variant_id: str):
        if cls.GNOMAD.is_valid(variant_id):
            return variant_id.replace("-", ":")
        else:
            raise ValueError(
                f"Cannot convert: {variant_id} is not a valid GNOMAD variant identifier."
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


class GA4GHVRSService(ComponentBaseMixin):
    """
    this normalizes, generates primary keys, and validates, standardizes using ga4gh.vrs
    """

    def __init__(
        self,
        genome_build: Assembly,
        seqrepo_service_url: str,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        self._seqrepo_data_proxy = create_dataproxy(f"seqrepo+{seqrepo_service_url}")
        self._allele_translator = AlleleTranslator(data_proxy=self._seqrepo_data_proxy)
        self._genome_build = genome_build

    def translate_from(self, variant_id: str, id_type: VariantNomenclature):
        if id_type.is_valid(variant_id):
            if id_type == VariantNomenclature.NIAGADS:
                variant_id = VariantNomenclature.niagads2gnomad(variant_id)
            return self._allele_translator.translate_from(variant_id, id_type.value)
        else:
            raise ValueError(
                f"Cannot translate: {variant_id} is not a valid {id_type.name} variant identifier."
            )

    def translate_to(self, allele: Allele, id_type: VariantNomenclature):
        if id_type.value in ["spdi", "hgvs"]:
            return self._allele_translator.translate_to(allele, id_type.value)
        else:
            raise NotImplementedError(
                f"Cannot translate: ga4gh/vrs-python does not yet support translation to {id_type.name} nomenclature."
            )
