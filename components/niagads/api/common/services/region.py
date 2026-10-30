from typing import Union

from niagads.api.common.models.annotations.associations import VariantAssociation
from niagads.api.common.models.entities.variant.records import Variant, VariantBrief
from niagads.api.common.models.records.types import DynamicRecord
from niagads.api.common.services.base import BaseEndpointService
from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.database.genomicsdb.schema.results.associations import (
    VariantAssociation as VAOrm,
)
from niagads.database.genomicsdb.schema.variant.documents import Variant as VariantORM


class RegionEndpointService(BaseEndpointService):
    """Resolve genomic region identifiers to feature locations."""

    async def get_feature_location(
        self, id: str, flank: int = 0
    ) -> OneBasedGenomicRegion:
        """Build a one-based region with optional flanking coordinates.

        Args:
            id (str): Region identifier in chrN:start-end or N:start-end format.
            flank (int): Number of bases to extend on each side of the region.

        Returns:
            OneBasedGenomicRegion: Region with the requested flanking bases.
        """
        feature_location = OneBasedGenomicRegion.from_region_id(id)
        if flank:
            feature_location.start -= flank
            feature_location.end += flank
        return feature_location

    async def fetch_variants(
        self,
        region_id: str,
        *,
        flank: int = 0,
        limit: int | None = None,
        counts_only: bool = False,
    ) -> Union[list[Variant], list[VariantBrief], int]:
        """Retrieve variant records within a region and optional flanks.

        Args:
            region_id (str): Region identifier to retrieve variants for.
            flank (int): Number of bases to extend on each side of the region.
            limit (int | None): Maximum number of variant records to retrieve.
            counts_only (bool): Return the total count instead of variant records.

        Returns:
            Union[list[Variant], list[VariantBrief], int]: Matching records using
                the configured response model, or the total matching count.
        """
        region = await self.get_feature_location(region_id, flank=flank)
        mappings = await VariantORM.retrieve_records_by_region(
            self._context.database_session,
            region,
            limit=limit,
            counts_only=counts_only,
        )
        if counts_only:
            return mappings
        return [
            self._response_config.record_model(**record, id=record["niagads_id"])
            for record in mappings[str(region)]
        ]

    async def fetch_associations(
        self, region_id: str, *, flank: int = 0, summary: bool = False
    ) -> Union[list[VariantAssociation], list[DynamicRecord]]:
        """Retrieve variant associations within a region and optional flanks.

        Args:
            region_id (str): Region identifier to retrieve associations for.
            flank (int): Number of bases to extend on each side of the region.
            summary (bool): Whether to return association counts by track.

        Returns:
            Union[list[VariantAssociation], list[DynamicRecord]]: Associations
                with track phenotypes, or per-track traits and association
                counts. Returns an empty list if no associations are found.
        """
        region = await self.get_feature_location(region_id, flank=flank)
        mappings = await VAOrm.retrieve_records(self._context.database_session, region)
        associations = mappings[str(region)]

        return self._generate_association_lookup_result(associations, summary=summary)
