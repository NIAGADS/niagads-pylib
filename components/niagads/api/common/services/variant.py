from typing import Union

from fastapi import HTTPException
from niagads.api.common.models.annotations.associations import VariantAssociation
from niagads.api.common.models.records.types import DynamicRecord
from niagads.api.common.services.base import BaseEndpointService
from niagads.common.types import RecordRetrievalResult
from niagads.common.variant.models.record import VariantRecord
from niagads.database.genomicsdb.schema.variant.documents import Variant as VariantORM
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches


class VariantEndpointService(BaseEndpointService):
    _orm_model = VariantORM

    async def get_record_mappings(self, variant_ids: list[str]) -> dict:
        """Retrieve variant records keyed by their requested identifiers.

        Args:
            variant_ids (list[str]): Variant identifiers to retrieve.

        Returns:
            dict: Mapping of each requested identifier to its response model.
        """
        mappings: RecordRetrievalResult = await self._lookup_records(variant_ids)
        return {
            k: [
                self._response_config.record_model(**mf) if mf else []
                for mf in mapped_features
            ]
            for k, mapped_features in mappings.items()
        }

    async def fetch_record(self, variant_id: str) -> list:
        """Retrieve a variant record or raise HTTP 404 when it is missing.

        Args:
            variant_id (str): Variant identifier to retrieve.

        Returns:
            list: Matching variant response records.

        Raises:
            HTTPException: If no variant matches the identifier.
        """
        mappings = await self.get_record_mappings([variant_id])
        if variant_id not in mappings:
            raise HTTPException(
                status_code=404, detail=f"Variant `{variant_id}` not found"
            )
        return [mappings[variant_id]]

    # TODO: resume from here -> SV logic -> lookup to get span
    async def fetch_associations(
        self, variant_id: str, *, flank: int = 0, summary: bool = False
    ) -> Union[list[VariantAssociation], list[DynamicRecord]]:
        """Assemble variant associations with their track phenotypes.

        Args:
            gene_id (str): Identifier used to retrieve associations.
            summary (bool): Whether to return association counts by track.

        Returns:
            Union[list[VariantAssociation], list[DynamicRecord]]: Associations
                with track phenotypes, or per-track traits and association
                counts. Returns an empty list if no associations are found.
        """
        is_structural_variant = matches(
            variant_id, RegularExpressions.STRUCTUAL_VARIANT_ID
        )
        if is_structural_variant:
            variant = await Variant.fetch_record()
        else:
            variant: VariantRecord = VariantRecord.from_positional_id(variant_id)
            span = variant.span

        gene_mapping = await self._lookup_records([gene_id])
        if not gene_mapping[gene_id]:
            return []
        else:
            gene_record = gene_mapping[gene_id][0]
            span: Range = gene_record["span"]
            # span in db is [); we want [,] so need to subtract 1
            region = OneBasedGenomicRegion.from_region_id(
                gene_record["gene_structure"]["location"]
            )
            region.start -= flank
            region.end += flank

        mappings = await VAOrm.retrieve_records(self._context.database_session, region)
        associations = mappings[str(region)]

        return await self._generate_association_lookup_result(
            associations, summary=summary
        )
