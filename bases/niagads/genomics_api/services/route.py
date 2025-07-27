from typing import Optional
from fastapi import HTTPException
from niagads.api_common.config import Settings
from niagads.api_common.models.core import ResultSize
from niagads.api_common.models.features.genomic import (
    AnnotatedGenomicRegion,
    GenomicFeature,
    GenomicRegion,
)
from niagads.api_common.models.records import Entity
from niagads.api_common.services.features import FeatureQueryService
from niagads.common.models.structures import Range
from niagads.database.schemas.dataset.track import Track, TrackDataStore
from niagads.exceptions.core import ValidationError
from niagads.api_common.models.features.feature_score import (
    GWASSumStatResponse,
    QTLResponse,
)
from niagads.api_common.models.services.query import (
    PreparedStatement,
    QueryDefinition,
    QueryFilter,
)
from niagads.api_common.parameters.internal import InternalRequestParameters
from niagads.api_common.parameters.response import ResponseContent
from niagads.api_common.services.metadata.query import MetadataQueryService
from niagads.api_common.services.metadata.route import (
    MetadataRouteHelperService,
)
from niagads.api_common.services.route import (
    Parameters,
    ResponseConfiguration,
)

from niagads.genome.core import GenomicFeatureType
from niagads.genomics_api.queries.track_data import (
    TrackGWASSumStatQuery,
    TrackQTLGeneQuery,
)
from niagads.utils.dict import all_values_are_none
from pydantic import BaseModel
from sqlalchemy import bindparam, text
from sqlalchemy.exc import NoResultFound


class QueryOptions(BaseModel):
    fetch_one: Optional[bool] = False
    counts_only: Optional[bool] = False
    raw_response: Optional[bool] = False
    range: Optional[Range] = None


class GenomicsRouteHelper(MetadataRouteHelperService):

    def __init__(
        self,
        managers: InternalRequestParameters,
        response_config: ResponseConfiguration,
        params: Parameters,
        query: QueryDefinition = None,
        id_parameter: str = "id",
    ):
        super().__init__(
            managers,
            response_config,
            params,
            [TrackDataStore.SHARED, TrackDataStore.GENOMICS],
        )
        self.__query = query
        self.__id_parameter: str = id_parameter

    def __build_counts_statement(self, opts: QueryOptions):
        statement: PreparedStatement = self.__query.get_counts_statement(
            self._parameters.get("filter")
        )

        return statement.build(self._parameters, self.__id_parameter)

    def __build_statement(self, opts: QueryOptions):
        filter: QueryFilter = self._parameters.get("filter")
        is_filtered = self.__query.allow_filters and filter is not None

        # Get the query string (with filter if needed)
        query: str = (
            self.__query.get_filter_query(filter) if is_filtered else self.__query.query
        )

        if self.__query.json_field is not None:
            query = query.format(field=self.__query.json_field)

        # Handle pagination/range
        if opts.range is not None and "rank_start" not in (
            self.__query.bind_parameters or []
        ):
            query += f" LIMIT {self._pageSize}"
            query += f" OFFSET {opts.range.start}"

        parameters = self._parameters.model_dump()
        if self.__query.bind_parameters is not None:
            if "rank_start" in self.__query.bind_parameters:
                parameters["rank_start"] = 0 if opts.range is None else opts.range.start
            if "rank_end" in self.__query.bind_parameters:
                parameters["rank_end"] = (
                    self._pageSize - 1 if opts.range is None else opts.range.end
                )

        # Handle filter parameter
        if is_filtered:
            parameters[filter.field] = filter.value

        # Create the PreparedStatement object and return the SQLAlchemy statement
        statement = PreparedStatement(
            query=query,
            bind_parameters=(
                self.__query.bind_parameters + [filter.field]
                if is_filtered
                else self.__query.bind_parameters
            ),
        )
        return statement.build(parameters, self.__id_parameter)

    def __process_query_result(self, result, opts: QueryOptions):
        if opts.counts_only and self.__query.counts_func is not None:
            return self.__query.counts_func(result)
        else:
            fetch_one = opts.fetch_one or self.__query.fetch_one
            if fetch_one or opts.counts_only:
                if self.__query.json_field:
                    result = result[0][self.__query.json_field]
                    if isinstance(result, list):
                        result = [dict(item) for item in result]
                    else:
                        result = [result]
                else:
                    result = [result[0]]
                if opts.counts_only:
                    return [ResultSize(num_results=len(result))]
                else:
                    return result

            else:
                return [dict(item) for item in result]

    async def __run_query(self, opts: QueryOptions):
        if (
            opts.counts_only
            and not self.__query.counts_func  # count by processing full response
            and not self.__query.json_field  # need to count w/in the json field after getting response
        ):
            statement = self.__build_counts_statement(opts)
        else:
            statement = self.__build_statement(opts)

        try:
            # .mappings() returns result as dict
            result = (await self._managers.session.execute(statement)).mappings().all()

            if len(result) == 0:
                raise NoResultFound()

            if all_values_are_none(result[0]):
                raise NoResultFound()

            return self.__process_query_result(result, opts)

        except NoResultFound as e:
            if self.__query.allow_empty_response:
                if opts.raw_response:
                    return result
                else:
                    return []
            else:
                if self.__query.entity is not None:
                    raise HTTPException(
                        status_code=404, detail=f"{str(self.__query.entity)} not found"
                    )
                else:
                    return []

    async def __get_paged_query_response(self):
        r_size: int = await self.__run_query(QueryOptions(counts_only=True))
        self._result_size = r_size["result_size"]
        self.initialize_pagination()
        return await self.get_query_response(
            QueryOptions(range=self.slice_result_by_page())
        )

    async def get_query_response(self, opts: QueryOptions = QueryOptions()):
        # fetchCounts ->  get counts only
        cached_response = await self._get_cached_response()
        if cached_response is not None:
            return cached_response

        result = await self.__run_query(opts)

        if opts.raw_response:
            return result

        if not self.__query.fetch_one and isinstance(result, list):
            self._result_size = len(result)
            if self._result_size > 0:  # not empty
                self.initialize_pagination()
                range = self.slice_result_by_page()
                result = result[range.start : range.end]

        return await self.generate_response(result, False)

    async def search_variant_records(self, opts: QueryOptions = QueryOptions()):

        gene_filter = self._parameters.get("gene")
        result = await self.get_query_response(
            QueryOptions(raw_response=False if gene_filter is None else True)
        )
        if gene_filter is None:
            return result

        filtered_result = [
            variant
            for variant in result
            if gene_filter
            in {
                variant.get("most_severe_consequence", {})
                .get("impacted_gene", {})
                .get("id"),
                variant.get("most_severe_consequence", {})
                .get("impacted_gene", {})
                .get("symbol"),
            }
        ]

        # still need to do pagination
        self._result_size = len(filtered_result)
        if self._result_size > 0:  # not empty
            self.initialize_pagination()
            range = self.slice_result_by_page()
            filtered_result = filtered_result[range.start : range.end]

        return await self.generate_response(filtered_result, False)

    async def get_region_record(self, opts: QueryOptions = QueryOptions()):
        cached_response = await self._get_cached_response()
        if cached_response is not None:
            return cached_response

        region_id = self._parameters.get("id")
        region = GenomicRegion.from_region_id(region_id)
        self._parameters.update("chromosome", str(region.chromosome))
        self._parameters.update("start", region.start)
        self._parameters.update("end", region.end)
        result = await self.__run_query(opts)

        # Transform result into feature_type: num_features pairs, summing over all feature subtypes
        feature_summary = {}
        for item in result:
            feature_type = item["feature_type"]  # Access feature_type field
            num_features = item["num_features"]  # Access num_features field
            feature_summary[feature_type] = (
                feature_summary.get(feature_type, 0) + num_features
            )

        max_span_size = Settings.from_env().MAX_SPAN_SIZE
        num_small_variants = (
            feature_summary["small_variant"]
            if "small_variant" in feature_summary
            else 0
        )
        if num_small_variants == 0 and not region.is_valid_range(max_span_size):
            num_small_variants = f"number of small variants not calculated for ranges > {max_span_size:,} bp"

        result = [
            AnnotatedGenomicRegion(
                id=region_id,
                location=GenomicRegion(
                    chromosome=region.chromosome, start=region.start, end=region.end
                ),
                num_small_variants=num_small_variants,
                num_genes=feature_summary["gene"] if "gene" in feature_summary else 0,
                num_structural_variants=(
                    feature_summary["structural_variant"]
                    if "structural_variant" in feature_summary
                    else 0
                ),
            )
        ]

        return await self.generate_response(result, False)

    async def get_feature_annotation(
        self, entity: Entity, opts: QueryOptions = QueryOptions()
    ):
        # verify feature; will raise a not found error
        if entity == Entity.GENE:
            await FeatureQueryService(
                session=self._managers.session
            ).get_gene_primary_key(self._parameters.get("id"))
        elif entity == Entity.VARIANT:
            await FeatureQueryService(
                session=self._managers.session
            ).get_variant_primary_key(self._parameters.get("id"))

        return await self.get_query_response(opts)

    async def __validate_track(self):
        result = await MetadataQueryService(
            self._managers.session, data_store=self._data_store
        ).get_track_metadata(tracks=[self._parameters.get("track")])
        if len(result) == 0:
            raise ValidationError(
                "Track not found in the NIAGADS Alzheimer's GenomicsDB"
            )

        return result[0]

    async def get_track_data_query_response(self):
        cached_response = await self._get_cached_response()
        if cached_response is not None:
            return cached_response

        # this will both validate and allow us to determine which kind of track
        result: Track = await self.__validate_track()
        # result: GenomicsTrack = await self.__run_query(QueryOptions(fetchOne=True))

        match result.experimental_design["data_category"]:
            case "QTL":
                self.__query = TrackQTLGeneQuery
                if self._response_config.content == ResponseContent.FULL:
                    self._response_config.model = QTLResponse
            case _ if result.experimental_design["data_category"].startswith("GWAS"):
                self.__query = TrackGWASSumStatQuery
                if self._response_config.content == ResponseContent.FULL:
                    self._response_config.model = GWASSumStatResponse
            case _:
                raise RuntimeError(
                    f"Track with invalid type retrieved: {result.track_id} - {result.data_category}"
                )

        match self._response_config.content:
            case ResponseContent.BRIEF | ResponseContent.COUNTS:
                counts = await self.get_query_response(
                    QueryOptions(counts_only=True, raw_response=True)
                )
                suffix = (
                    "qtls"
                    if result.experimental_design["data_category"] == "QTL"
                    else "significant_associations"
                )
                if self._response_config.content == ResponseContent.COUNTS:
                    return await self.generate_response(
                        {f"num_{suffix}": counts["result_size"]}
                    )
                else:
                    result[f"num_{suffix}"] = counts["result_size"]
                    return await self.generate_response(result)
            case _:  # FULL
                return await self.__get_paged_query_response()
                # return await self.get_query_response()
