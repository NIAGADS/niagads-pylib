import json
from niagads.common.types import ETLOperation

from niagads.database.genomicsdb.schema.variant.documents import Variant
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import EnvVariableMixin, PathValidatorMixin
from niagads.etl.plugins.types import ETLLoadStrategy

from niagads.genomicsdb_etl.plugins.common.bases.features import (
    BaseFeatureLoaderParams,
    BaseFeatureLoaderPlugin,
)

from niagads.genomicsdb_etl.plugins.variant.base import VariantLookupMixin
from niagads.utils.sys import timer
from niagads.vcf.types import VCFEntry
from pydantic import Field

# need to filter consequences for variant allele != variant alt allele
# ditto for allele frequencies

# only is len(colocated_variant >  1)

# af in colocated-variants
# need to extract the most severe consequence (field most severe consequence map to each of the consequence types and find the first?)

# TODO: embedding strategy?

class AnnotatedVCFEntry(VCFEntry):
    most_severe_consequence: dict
    annotation: dict
    allele_frequencies: dict
    
    """
    {"KOREAN": 0.0109, "SGDP_PRJ": 1.0}
    {"dbGaP_PopFreq": 0.0}
    """

class VEPAnnotationLoaderParams(
    BaseFeatureLoaderParams, PathValidatorMixin, EnvVariableMixin
):
    file: str = Field(..., description="Full path to VEP annotation file (expect JSON output)")

    validate_file_exists = PathValidatorMixin.validator("file")


metadata = PluginMetadata(
    version="1.0",
    description="Load variants from VCF file into variant table",
    affected_tables=[Variant],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.UPDATE,
    is_large_dataset=True,
    parameter_model=VEPAnnotationLoaderParams,
    can_resume=True,
)


class VEPAnnotationLoader(BaseFeatureLoaderPlugin, VariantLookupMixin):
    _params: VEPAnnotationLoaderParams
    
    def extract(self):
        ...
        
    async def transform(self, data):
        ...
        
    async def load(self, session, entries):
        lookup_region = self._get_lookup_region(entries)
        self.logger.debug(f"Lookup Region: {str(lookup_region)}")
        reference_variants = await self._retrieve_variants_in_span(session, lookup_region)
        
        # variant_key = (entry.pos, entry.ref, entry.alt)
        # variant_id = reference_variants.get(variant_key)