from collections import Counter
from typing import Union

from fastapi import HTTPException
from niagads.api.common.models.annotations.associations import VariantAssociation
from niagads.api.common.models.entities.gene.records import Gene
from niagads.api.common.models.records.types import DynamicRecord
from niagads.api.common.services.base import BaseEndpointService
from niagads.common.genomic.regions.models import OneBasedGenomicRegion
from niagads.common.models.types import Range
from niagads.common.types import RecordRetrievalResult
from niagads.common.variant.models.record import VariantRecord
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.database.genomicsdb.schema.gene.documents import Gene as GeneORM
from niagads.database.genomicsdb.schema.results.associations import (
    VariantAssociation as VAOrm,
)
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches


class GeneEndpointService(BaseEndpointService):
    _orm_model = GeneORM

    async def get_record_mappings(self, gene_ids: list[str]):
        """Resolve gene identifiers to configured response records.

        Args:
            gene_ids (list[str]): Gene identifiers to resolve.

        Returns:
            dict: Mapping of each identifier to its matching response records.
        """
        mappings: RecordRetrievalResult = await self._lookup_records(gene_ids)
        # self.logger.debug(mappings)
        return {
            k: [
                self._response_config.record_model(**mf) if mf else []
                for mf in mapped_features
            ]
            for k, mapped_features in mappings.items()
        }

    async def fetch_record(self, gene_id: str):
        """Retrieve response records matching a gene identifier.

        Args:
            gene_id (str): Gene identifier to resolve.

        Returns:
            list: Matching gene response records.

        Raises:
            HTTPException: If no matching gene is found, with status code 404.
        """
        # using mappings instead of fetch_record b/c fetching record is based
        # on exact match
        mappings = await self.get_record_mappings([gene_id])
        if not mappings[gene_id]:
            raise HTTPException(status_code=404, detail=f"Gene `{gene_id}` not found")

        # get_record_mappings handles building the 'records', so can just return
        # the mapped records
        return mappings[gene_id]

    async def get_feature_location(
        self, id: str, flank: int = 0
    ) -> OneBasedGenomicRegion:
        """Resolve the first matching record to a one-based region.

        Args:
            id (str): Gene identifier to resolve.
            flank (int): Number of bases to extend on each side.

        Returns:
            OneBasedGenomicRegion: Location with the requested flanking bases.

        Raises:
            HTTPException: If no gene matches the identifier.
        """
        mappings = await self._lookup_records([id])

        if not mappings[id]:
            raise HTTPException(status_code=404, detail=f"Gene `{id}` not found")
        mapped_feature = mappings[id][0]
        start, end = mapped_feature["span"][1:-1].split(",")

        feature_location = OneBasedGenomicRegion.from_database_range(
            chromosome=mapped_feature["chromosome"],
            span=Range(start=int(start), end=int(end)),
        )
        if flank:
            feature_location.start -= flank
            feature_location.end += flank
        return feature_location

    async def fetch_gene_structure(self, gene_id: str) -> list[DynamicRecord]:
        """Retrieve gene structure using a case-insensitive identifier lookup.

        Args:
            gene_id (str): Gene identifier to resolve.

        Returns:
            dict: Gene structure, or an empty dictionary if no gene is found.
        """
        # again using lookup so can deal w/case-insensitivity
        mappings: RecordRetrievalResult = await self._lookup_records([gene_id])
        if not mappings[gene_id]:
            return {}
        return [DynamicRecord.model_validate(mappings[gene_id][0]["gene_structure"])]

    async def fetch_associations(
        self, gene_id: str, *, flank: int = 0, summary: bool = False
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

        return self._generate_association_lookup_result(associations, summary=summary)
