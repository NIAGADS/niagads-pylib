from niagads.common.types import ETLOperation
from niagads.common.variant.models.record import VariantRecord
from niagads.database.genomicsdb.schema.variant.documents import Variant
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.variant.vcf_loaders.base import BaseVCFLoader, BaseVCFLoaderParams


class ADSPVariantRecord(VariantRecord):
    qc: dict


metadata = PluginMetadata(
    version="1.0",
    description="Load variants from VCF file into variant table",
    affected_tables=[Variant],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.LOAD,
    is_large_dataset=True,
    parameter_model=BaseVCFLoaderParams,
    can_resume=True,
)


@PluginRegistry.register(metadata)
class ADSPVCFLoader(BaseVCFLoader):
    ...
    