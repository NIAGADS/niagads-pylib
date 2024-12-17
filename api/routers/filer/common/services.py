from fastapi.exceptions import RequestValidationError, ResponseValidationError
from sqlmodel import select, col, or_, func, distinct
from sqlalchemy import Values, String, column as sqla_column
from sqlalchemy.ext.asyncio import AsyncSession
from aiohttp import ClientSession
from typing import Any, Dict, List, Optional, Union

from niagads.utils.list import list_to_string
from niagads.utils.dict import rename_key

from api.common.enums import Assembly, ResponseContent
from api.config.settings import get_settings
from api.dependencies.parameters.filters import tripleToPreparedStatement
from api.models import BEDFeature, GenericDataModel


from .constants import TRACK_SEARCH_FILTER_FIELD_MAP, BIOSAMPLE_FIELDS, TRACKS_PER_API_REQUEST_LIMIT
from .enums import FILERApiEndpoint
from ..models.track_metadata_cache import Track


class ApiWrapperService:
    def __init__(self, session):
        self.__session: ClientSession = session
        
    def __map_genome_build(self, assembly: Assembly):
        ''' return genome build value FILER expects '''
        return 'hg19' if assembly == Assembly.GRCh37 \
            else 'hg38'

    def __build_request_params(self, parameters: dict):
        ''' map request params to format expected by FILER'''
        requestParams = {'outputFormat': 'json'}
        
        if 'assembly' in parameters:
            requestParams['genomeBuild'] = self.__map_genome_build(parameters['assembly'])

        if 'track' in parameters:
            # key = "trackIDs" if ',' in params['track_id'] else "trackID"
            requestParams['trackIDs'] = parameters['track']
            
        if 'span' in parameters:
            requestParams['region'] = parameters['span']

        return requestParams

    async def __fetch(self, endpoint: FILERApiEndpoint, params: dict):
        ''' map request params and submit to FILER API'''
        try:
            requestParams = self.__build_request_params(params)
            async with self.__session.get(str(endpoint), params=requestParams) as response:
                result = await response.json() 
            return result
        except Exception as e:
            raise LookupError(f'Unable to parse FILER response `{response.content}` for the following request: {str(response.url)}')
    
    async def __parallel_fetch(self, endpoint: FILERApiEndpoint, params: dict):
        """    tasks = []
        for c in colors:
            tasks.append(get(session=session, color=c, **kwargs))
        # asyncio.gather() will wait on the entire task set to be
        # completed.  If you want to process results greedily as they come in,
        # loop over asyncio.as_completed()
        htmls = await asyncio.gather(*tasks, return_exceptions=True)
        return htmls"""
        pass
        
    def __rename_keys(self, dictObj, keyMapping):
        for oldKey, newKey in keyMapping.items():
            dictObj = rename_key(dictObj, oldKey, newKey)
        return dictObj
    
    def __overlaps_to_features(self, overlaps) -> List[BEDFeature]:
        features = []
        for track in overlaps:
            f:dict
            for f in track['features']:
                f.update({'track_id': track['Identifier']})
                features.append(BEDFeature(**f))
        return features
    
    
    async def __count_track_overlaps(self, span: str, assembly: str, tracks: List[str]) -> List[GenericDataModel]:   
        response:dict = await self.get_informative_tracks(span, assembly, sort=True)   
        
        # need to filter all informative tracks for the ones that were requested
        # and add in the zero counts for the ones that have no hits
        informativeTracks = set([t['track_id'] for t in response]) # all informative tracks
        nonInformativeTracks = set(tracks).difference(informativeTracks) # tracks with no hits in the span
        informativeTracks = set(tracks).intersection(informativeTracks) # informative tracks in the requested list
        
        result = [GenericDataModel(tc) for tc in response if tc['track_id'] in informativeTracks] \
            + [GenericDataModel(track_id=t, num_overlaps=0) for t in nonInformativeTracks]
        
        return result
    
    def __sort_track_counts(self, trackCountsObj):
        return sorted(trackCountsObj, key = lambda item: item['num_overlaps'], reverse=True)


    async def get_track_hits(self, tracks: List[str], span: str, assembly: str, countsOnly: bool=False) -> Union[List[BEDFeature], List[GenericDataModel]]:
        if countsOnly:
            return await self.__count_track_overlaps(span, assembly, tracks)
        
        result = await self.__fetch(FILERApiEndpoint.OVERLAPS, {'track': ','.join(tracks), 'span': span})
        if 'message' in result:
            raise RuntimeError(result['message'])
        
        return self.__overlaps_to_features(result)


    async def get_informative_tracks(self, span: str, assembly: str, sort=False):
        result = self.__wrapper.fetch(FILERApiEndpoint.INFORMATIVE_TRACKS, {'span': span, 'assembly': assembly})
        result = [{'track_id' : track['Identifier'], 'num_overlaps': track['numOverlaps']} for track in result]
        # sort by most hits
        return self.__sort_track_counts(result) if sort else result



class MetadataQueryService:
    def __init__(self, session: AsyncSession):
        self.__session = session

    async def validate_tracks(self, tracks: List[str]):
        # solution for finding tracks not in the table adapted from
        # https://stackoverflow.com/a/73691503

        lookups = Values(sqla_column('track_id', String), name='lookups').data([(t, ) for t in tracks])
        statement = select(lookups.c.track_id).outerjoin(
            Track, col(Track.track_id) == lookups.c.track_id).where(col(Track.track_id) == None)
        
        result = (await self.__session.execute(statement)).all()
        if len(result) > 0:
            raise RequestValidationError(f'Invalid track identifiers found: {list_to_string(result)}')
        else:
            return True

    async def get_track_count(self) -> int:
        statement = select(func.count(Track.track_id))
        result = (await self.__session.execute(statement)).scalars().first()
        return result
        
    
    async def get_track_metadata(self, tracks: List[str], validate=True) -> List[Track]:
        statement = select(Track).filter(col(Track.track_id).in_(tracks)).order_by(Track.track_id)
        # statement = select(Track).where(col(Track.track_id) == trackId) 
        # if trackId is not None else select(Track).limit(100) # TODO: pagination
        if validate:
            await self.validate_tracks(tracks)

        result = (await self.__session.execute(statement)).scalars().all()
        return result
    
    
    def __add_biosample_filters(self, statement, triple: List[str]):
        conditions = []
        for bsf in BIOSAMPLE_FIELDS:
            conditions.append(tripleToPreparedStatement([f'biosample_characteristics|{bsf}', 
                "like" if (triple[1] == 'eq' or triple[1] == 'like') else "not like" , 
                triple[2]], Track))
        
        return statement.filter(or_(*conditions))


    def __add_statement_filters(self, statement, filters: List[str]):
        for phrase in filters:
            # array or join?
            if isinstance(phrase, list):
                # TODO: handle `or`;
                # `and` is handled implicitly by adding the next filter
                if phrase[0] == 'biosample':
                    statement = self.__add_biosample_filters(statement, phrase)
                else: 
                    modelField = TRACK_SEARCH_FILTER_FIELD_MAP[phrase[0]]['model_field']
                    statement = statement.filter(
                        tripleToPreparedStatement(
                            [modelField, phrase[1], phrase[2]],
                            Track
                        ))
                
        return statement

    async def query_track_metadata(self, 
            assembly: str, 
            filters: Optional[List[str]], 
            keyword: Optional[str], 
            responseType: ResponseContent,
            limit:int = None,
            offset:int = None) -> List[Track]:

        target = Track.track_id if responseType == ResponseContent.IDS \
            else func.count(Track.track_id) if responseType == ResponseContent.COUNTS else Track

        statement = select(target).filter(col(Track.genome_build) == assembly)
        if filters is not None:
            statement = self.__add_statement_filters(statement, filters)
        if keyword is not None:
            statement = statement.filter(or_(
                col(Track.searchable_text).regexp_match(keyword, 'i'),
                col(Track.antibody_target).regexp_match(keyword, 'i')))
            
        if responseType != ResponseContent.COUNTS:
            statement = statement.order_by(Track.track_id)

        if limit != None:
            statement = statement.limit(limit)
        
        if offset != None:
            statement = statement.offset(offset)

        result = await self.__session.execute(statement)

        if responseType == ResponseContent.COUNTS:
            return {'track_count': result.scalars().one() }
        else:
            return result.scalars().all()


    async def get_track_filter_summary(self, filterField:str, inclCounts: Optional[bool] = False) -> dict:
        modelField = TRACK_SEARCH_FILTER_FIELD_MAP[filterField]['model_field']

        valueCol = col(getattr(Track, modelField))
        if 'biosample' in modelField:
            valueCol = valueCol['tissue_category'].astext
        # statement = select(valueCol, Track.track_id).group_by(valueCol).count()
        statement = select(distinct(valueCol), func.count(Track.track_id)).where(valueCol.is_not(None)).group_by(valueCol) \
            if inclCounts else select(distinct(valueCol)).where(valueCol.is_not(None))
            
        result = (await self.__session.execute(statement)).all()
        return {row[0]: row[1] for row in result} if inclCounts else [value for value, in result]


    async def get_genome_build(self, tracks: List[str], validate=True) -> str:
        """ retrieves the genome build for a set of tracks; returns track -> genome build mapping if not all on same assembly"""
        
        if validate:
            await self.validate_tracks(tracks)
            
        statement = select(distinct(Track.genome_build)).where(col(Track.track_id).in_(tracks))

        result = (await self.__session.execute(statement)).all()
        if len(result) > 1: 
            statement = select(Track.track_id, Track.genome_build).where(col(Track.track_id).in_(tracks)).order_by(Track.genome_build, Track.track_id)
            result = (await self.__session.execute(statement)).all()
            return {row[0]: row[1] for row in result}
        else:
            return result[0]
            
