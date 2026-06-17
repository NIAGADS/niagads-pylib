# need to filter consequences for variant allele != variant alt allele
# ditto for allele frequencies

# only is len(colocated_variant >  1)

# af in colocated-variants



from typing import Optional
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.variant.documents import Variant
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.types import ETLLoadStrategy
from pydantic import Field


class VEPJSONLoaderParams(BasePluginParams, PathValidatorMixin):
    is_adsp: Optional[bool] = Field(default=False, description="Insert novel variants only; skip flagging existing variants as is_adsp_variant")

    validate_file_exists = PathValidatorMixin.validator("file")

metadata = PluginMetadata(
    version="1.0",
    description="Load variants from VCF file into variant table",
    affected_tables=[Variant],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.LOAD,
    is_large_dataset=True,
    parameter_model=VEPJSONLoaderParams,
    can_resume=False, # TODO: implement resume
)
