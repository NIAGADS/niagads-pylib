from fastapi import HTTPException
from niagads.api.common.models.annotations.associations import VariantAssociation
from niagads.api.common.models.records.types import DynamicRecord
from niagads.api.common.services.base import BaseEndpointService
from niagads.common.types import RecordRetrievalResult
from niagads.common.variant.models.record import VariantRecord
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.database.genomicsdb.schema.gene.documents import Gene as GeneORM
from niagads.database.genomicsdb.schema.results.associations import (
    VariantAssociation as VAOrm,
)


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

    async def fetch_gene_structure(self, gene_id: str) -> DynamicRecord:
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
        return DynamicRecord.model_validate(mappings[gene_id]["gene_structure"])

    async def fetch_associations(self, gene_id: str) -> list[VariantAssociation]:
        """Assemble variant associations with their track phenotypes.

        Args:
            gene_id (str): Identifier used to retrieve associations.

        Returns:
            list[VariantAssociation]: Associations with parsed alleles and track
                phenotypes, omitting None-valued input fields. Returns an empty
                list if no associations are found.
        """
        mappings = await VAOrm.retrieve_records(
            self._context.database_session, lookup_value=gene_id
        )
        associations = mappings[gene_id]
        if not associations:
            return []
        track_stable_ids = [a.get("track_stable_id") for a in associations]
        track_mappings = await Track.retrieve_records(
            self._context.database_session, track_stable_ids
        )
        track_traits = {}
        for track_stable_id, tracks in track_mappings.items():
            phenotypes = tracks[0]["participant_phenotypes"]
            track_traits[track_stable_id] = (
                {key: value for key, value in phenotypes.items() if value is not None}
                if phenotypes is not None
                else None
            )

        results = []
        for association in associations:
            variant = VariantRecord.from_positional_id(association["variant_stable_id"])
            record = {
                key: value
                for key, value in association.items()
                if key in VariantAssociation.model_fields and value is not None
            }
            results.append(
                VariantAssociation(
                    **record,
                    id=association["variant_stable_id"],
                    ref=variant.ref,
                    alt=variant.alt,
                    traits=track_traits[association["track_stable_id"]],
                )
            )
        return results
