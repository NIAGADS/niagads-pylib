from fastapi import HTTPException
from niagads.api.common.models.features.genomic import GenomicFeature
from niagads.genomics.sequence.types import GenomicFeatureType
from sqlalchemy import bindparam, column, func, select, text
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession


class FeatureQueryService:
    def __init__(
        self,
        session: AsyncSession,
    ):
        self.__session = session

    async def get_gene_primary_key(self, id: str):
        stmt = select(func.gene_lookup(id))
        try:
            result = (await self.__session.execute(stmt)).scalar_one()
            if result is None:
                raise NoResultFound()
            return result
        except NoResultFound as err:
            raise HTTPException(status_code=404, detail="Gene not found")

    async def get_variant_primary_key(self, id: str):
        stmt = select(func.find_variant_primary_key(id))

        try:
            result = (await self.__session.execute(stmt)).scalar_one()
            if result is None:
                raise NoResultFound()
            return result
        except NoResultFound as err:
            raise HTTPException(status_code=404, detail="Variant not found")

    async def __get_feature_location(self, query: str, feature: GenomicFeature):
        bind_parameters = [
            bindparam(
                "id",
                (feature.feature_id),
            )
        ]

        statement = text(query).bindparams(*bind_parameters)
        result = (await self.__session.execute(statement)).fetchone()
        if result[0] is None:
            return None
        return f"{result[0]}:{result[1]}-{result[2]}"

    async def get_gene_location(self, gene: GenomicFeature):
        query = """SELECT g.chromosome,
        g.location_start AS start,
        g.location_end AS end
        FROM CBIL.GeneAttributes g
        WHERE upper(g.gene_symbol) = upper(:id)
        OR g.source_id = :id
        OR g.annotation->>'entrez_id' = :id"""

        result = await self.__get_feature_location(query, gene)
        if result is None:
            raise HTTPException(status_code=404, detail="`loc` feature not found")
        return result

    async def get_variant_location(self, variant: GenomicFeature):
        query: str = """ 
        SELECT v.annotation->>'chromosome' AS chromosome, 
        (v.annotation->>'position')::int AS start, 
        (v.annotation->>'position')::int + (v.annotation->>'length')::int AS end
        FROM get_variant_primary_keys_and_annotations_tbl(:id) v
        """

        result = self.__get_feature_location(query, variant)
        if result is None:
            raise HTTPException(status_code=404, detail="`loc` feature not found")
        return result

    async def get_feature_location(self, feature: GenomicFeature):
        match feature.feature_type:
            case GenomicFeatureType.GENE:
                return await self.get_gene_location(feature)

            case GenomicFeatureType.VARIANT:
                return await self.get_variant_location(feature)

            case GenomicFeatureType.REGION:
                return feature.feature_id

            case GenomicFeatureType.STRUCTURAL_VARIANT:
                raise NotImplementedError(
                    f"Mapping structural variant spans not yet implemented"
                )
