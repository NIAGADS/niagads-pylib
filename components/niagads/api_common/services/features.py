from fastapi import HTTPException
from niagads.genome.core import GenomicFeatureType
from niagads.api_common.models.features.genomic import GenomicFeature
from sqlalchemy import func, select, text, column
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

    async def get_gene_location(self, gene: GenomicFeature):
        stmt = select(func.gene_location_lookup(gene.feature_id))
        try:
            result = (await self.__session.execute(stmt)).scalar_one()
            if result is None:
                raise NoResultFound()
            return result
        except NoResultFound as err:
            raise HTTPException(status_code=404, detail="Gene not found")

    async def get_variant_location(self, variant: GenomicFeature):
        # FIXME: structural variants; just query DB
        if variant.feature_id.startswith("rs"):
            query = func.find_variant_by_refsnp(variant.feature_id, True).table_valued(
                column("chromosome"), column("position"), column("length")
            )

            stmt = select(
                (
                    query.c.chromosome
                    + ":"
                    + (query.c.position - 1).cast(text("TEXT"))
                    + "-"
                    + (query.c.position + query.c.length).cast(text("TEXT"))
                ).label("span")
            )
            try:
                result = await self.__session.execute(stmt)
                return result.scalar_one()
            except NoResultFound as err:
                raise HTTPException(status_code=404, detail="refSNP not found")

        else:
            [chr, pos, ref, alt] = variant.feature_id.split(":")
            start = int(pos) - 1
            end = start + len(ref)
            return f"{chr}:{start}-{end}"

    async def get_feature_location(self, feature: GenomicFeature):
        match feature.feature_type:
            case GenomicFeatureType.GENE:
                return self.get_gene_location()

            case GenomicFeatureType.VARIANT:
                return self.get_variant_location()

            case GenomicFeatureType.SPAN:
                return feature.feature_id

            case GenomicFeatureType.STRUCTURAL_VARIANT:
                raise NotImplementedError(
                    f"Mapping structural variant spans not yet implemented"
                )
