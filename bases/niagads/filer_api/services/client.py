from typing import List, Union

from aiohttp import ClientSession
from niagads.api.common.models.entities.region.features.bed import BEDFeature
from niagads.api.common.models.entities.track.records import TrackResultMetrics

from niagads.enums.core import CaseInsensitiveEnum
from niagads.genome_reference.human import GenomeBuild
from pydantic import AliasChoices, BaseModel, Field


class FILEREndpoint(CaseInsensitiveEnum):
    OVERLAPS = "get_overlaps"
    INFORMATIVE_TRACKS = "get_overlapping_tracks_by_coord"
    METADATA = "get_metadata"
    GENE_QTLS = "get_gene_qtls"

    def __str__(self):
        return f"{self.value}.php"


class FILERDataResponse(BaseModel):
    id: str = Field(..., validation_alias=AliasChoices("Identifier", "identifier"))
    features: List[BEDFeature]


class FILERTrackResultMetricsResponse(BaseModel):
    id: str = Field(..., validation_alias=AliasChoices("Identifier", "identifier"))
    count: int = Field(..., aliase="numOverlaps")


class FILERClientService:
    def __init__(self, session):
        self.__session: ClientSession = session

    def __build_request_params(self, parameters: dict):
        """map request params to format expected by FILER"""
        request_params = {"outputFormat": "json"}

        genome_build: GenomeBuild = parameters.get("genome_build", GenomeBuild.GRCh38)
        request_params["genomeBuild"] = genome_build.hg_label()

        if "track" in parameters:
            # FIXME: not sure about this -> key = "trackIDs" if ',' in params['track_id'] else "trackID"
            request_params["trackIDs"] = parameters["track"]

        if "span" in parameters:
            request_params["region"] = str(parameters["span"])

        return request_params

    async def __fetch(
        self, *, endpoint: FILEREndpoint, params: dict, raw_params: bool = False
    ):
        """map request params and submit to FILER API"""
        try:
            request_params = (
                params if raw_params else self.__build_request_params(params)
            )
            async with self.__session.get(
                str(endpoint), params=request_params
            ) as response:
                result = await response.json()
            return result
        except Exception:
            raise LookupError(
                f"Unable to get FILER response `{response.content}` for the following request: {str(response.url)}"
            )

    async def __get_result_size(
        self, *, span: str, assembly: str, tracks: List[str]
    ) -> List[TrackResultMetrics]:
        # TODO: new FILER endpoint, count overlaps for specific track ID?
        # for now, probably faster to retrieve the data and count, but may depend on span
        if len(tracks) <= 3:
            response = await self.__fetch(
                FILEREndpoint.OVERLAPS, {"track": ",".join(tracks), "span": span}
            )
            return [
                TrackResultMetrics(**FILERTrackResultMetricsResponse(**t))
                for t in response
            ]

        else:
            response = await self.get_informative_tracks(span, assembly, sort=True)

            # need to filter all informative tracks for the ones that were requested
            # and add in the zero counts for the ones that have no hits
            informative_tracks = set([t.id for t in response])  # all informative tracks
            non_informative_tracks = set(tracks).difference(
                informative_tracks
            )  # tracks with no hits in the span
            informative_tracks = set(tracks).intersection(
                informative_tracks
            )  # informative tracks in the requested list

            return [tc for tc in response if tc.id in informative_tracks] + [
                TrackResultMetrics(id=t, count=0) for t in non_informative_tracks
            ]

    async def get_track_overlaps(
        self, *, tracks: List[str], span: str, assembly: str, counts_only: bool = False
    ) -> Union[List[FILERDataResponse], List[TrackResultMetrics]]:

        if counts_only:
            return await self.__get_result_size(span, assembly, tracks)

        result = await self.__fetch(
            FILEREndpoint.OVERLAPS, {"track": ",".join(tracks), "span": span}
        )

        try:
            return [FILERDataResponse(**r) for r in result]
        except Exception:
            raise LookupError(
                f"Unable to process FILER response for track(s) `{tracks}` in the span: {span} ({assembly})"
            )

    async def get_informative_tracks(
        self, *, span: str, assembly: str, sort=False
    ) -> List[TrackResultMetrics]:
        result = await self.__fetch(
            FILEREndpoint.INFORMATIVE_TRACKS,
            {"span": span, "genome_build": assembly},
        )
        result = [
            TrackResultMetrics(id=t["Identifier"], count=t["numOverlaps"])
            for t in result
        ]
        return TrackResultMetrics.sort(result) if sort else result
