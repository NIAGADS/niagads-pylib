from niagads.enums.core import CaseInsensitiveEnum
from niagads.genome.core import Assembly
from niagads.open_access_api_common.models.records.features.bed import BEDFeature
from niagads.open_access_api_common.models.records.track.track import TrackResultSize
from pydantic import BaseModel
from aiohttp import ClientSession
from typing import List, Union


class FILERApiEndpoint(CaseInsensitiveEnum):
    OVERLAPS = "get_overlaps"
    INFORMATIVE_TRACKS = "get_overlapping_tracks_by_coord"
    METADATA = "get_metadata"
    GENE_QTLS = "get_gene_qtls"

    def __str__(self):
        return f"{self.value}.php"


class FILERApiDataResponse(BaseModel):
    Identifier: str
    features: List[BEDFeature]


class ApiWrapperService:
    def __init__(self, session):
        self.__session: ClientSession = session

    def __map_genome_build(self, assembly: Assembly):
        """return genome build value FILER expects"""
        return "hg19" if assembly == Assembly.GRCh37 else "hg38"

    def __build_request_params(self, parameters: dict):
        """map request params to format expected by FILER"""
        requestParams = {"outputFormat": "json"}

        if "assembly" in parameters:
            requestParams["genomeBuild"] = self.__map_genome_build(
                parameters["assembly"]
            )

        if "track" in parameters:
            # key = "trackIDs" if ',' in params['track_id'] else "trackID"
            requestParams["trackIDs"] = parameters["track"]

        if "span" in parameters:
            requestParams["region"] = parameters["span"]

        return requestParams

    async def __fetch(
        self, endpoint: FILERApiEndpoint, params: dict, rawParams: bool = False
    ):
        """map request params and submit to FILER API"""
        try:
            requestParams = params if rawParams else self.__build_request_params(params)
            async with self.__session.get(
                str(endpoint), params=requestParams
            ) as response:
                result = await response.json()
            return result
        except Exception as e:
            raise LookupError(
                f"Unable to get FILER response `{response.content}` for the following request: {str(response.url)}"
            )

    async def __get_result_size(
        self, span: str, assembly: str, tracks: List[str]
    ) -> List[TrackResultSize]:
        # TODO: new FILER endpoint, count overlaps for specific track ID?
        if (
            len(tracks) <= 3
        ):  # for now, probably faster to retrieve the data and count, but may depend on span
            response = await self.__fetch(
                FILERApiEndpoint.OVERLAPS, {"track": ",".join(tracks), "span": span}
            )
            return [
                TrackResultSize(
                    track_id=t["Identifier"], num_results=len(t["features"])
                )
                for t in response
            ]

        else:
            response = await self.get_informative_tracks(span, assembly, sort=True)

            # need to filter all informative tracks for the ones that were requested
            # and add in the zero counts for the ones that have no hits
            informativeTracks = set(
                [t.track_id for t in response]
            )  # all informative tracks
            nonInformativeTracks = set(tracks).difference(
                informativeTracks
            )  # tracks with no hits in the span
            informativeTracks = set(tracks).intersection(
                informativeTracks
            )  # informative tracks in the requested list

            return [tc for tc in response if tc.track_id in informativeTracks] + [
                TrackResultSize(track_id=t, num_results=0) for t in nonInformativeTracks
            ]

    async def get_track_hits(
        self, tracks: List[str], span: str, assembly: str, countsOnly: bool = False
    ) -> Union[List[FILERApiDataResponse], List[TrackResultSize]]:

        if countsOnly:
            return await self.__get_result_size(span, assembly, tracks)

        result = await self.__fetch(
            FILERApiEndpoint.OVERLAPS, {"track": ",".join(tracks), "span": span}
        )

        try:
            return [FILERApiDataResponse(**r) for r in result]
        except:
            raise LookupError(
                f"Unable to process FILER response for track(s) `{tracks}` in the span: {span} ({assembly})"
            )

    async def get_gene_qtls(
        self, track: str, gene: str, countsOnly: bool = False
    ) -> FILERApiDataResponse:
        result = await self.__fetch(
            FILERApiEndpoint.GENE_QTLS, {"track": track, "gene": gene}, rawParams=True
        )

        try:
            item = {"Identifier": track, "features": result}
            return FILERApiDataResponse(**item)

        except:
            raise LookupError(
                f"Unable to process FILER response for QTL track `{track}` for the gene `{gene}`"
            )

    async def get_informative_tracks(
        self, span: str, assembly: str, sort=False
    ) -> List[TrackResultSize]:
        result = await self.__fetch(
            FILERApiEndpoint.INFORMATIVE_TRACKS, {"span": span, "assembly": assembly}
        )
        result = [
            TrackResultSize(track_id=t["Identifier"], num_results=t["numOverlaps"])
            for t in result
        ]
        return TrackResultSize.sort(result) if sort else result
