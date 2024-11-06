from fastapi.exceptions import RequestValidationError, ResponseValidationError
from sqlmodel import select, col, or_, func, distinct
from sqlalchemy import Values, String, column as sqla_column
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Union
from collections import OrderedDict

from niagads.filer import FILERApiWrapper
from niagads.utils.list import list_to_string
from niagads.utils.dict import rename_key

from api.common.enums import ResponseContent
from api.internal.config import get_settings
from api.dependencies.parameters.filters import tripleToPreparedStatement
from api.common.helpers import Parameters
from api.response_models import BEDFeature, GenericDataModel

from ..models.track_metadata_cache import Track
from .constants import TRACK_SEARCH_FILTER_FIELD_MAP, BIOSAMPLE_FIELDS

class ApiWrapperService:
    _OVERLAPS_ENDPOINT = 'get_overlaps'
    _INFORMATIVE_TRACKS_ENDPOINT = 'get_overlapping_tracks_by_coord'
    
    def __init__(self):
        self.__request_uri = get_settings().FILER_REQUEST_URI
        self.__wrapper = FILERApiWrapper(self.__request_uri)
        
    def __rename_keys(self, dictObj, keyMapping):
        for oldKey, newKey in keyMapping.items():
            dictObj = rename_key(dictObj, oldKey, newKey)
        return dictObj
    
    def __overlaps2features(self, overlaps) -> List[BEDFeature]:
        features = []
        for track in overlaps:
            f:dict
            for f in track['features']:
                f.update({'track_id': track['Identifier']})
                features.append(BEDFeature(**f))
        return features
    
    
    def __countOverlaps(self, overlaps: List[dict]) -> List[GenericDataModel]:   
        return [GenericDataModel(track_id=track['Identifier'], num_overlaps=len(track['features'])) for track in overlaps]
    
    # TODO: async?
    def get_track_hits(self, tracks: List[str], span: str, countsOnly: bool=False) -> Union[List[BEDFeature], List[GenericDataModel]]:
        result = self.__wrapper.make_request(self._OVERLAPS_ENDPOINT, {'id': ','.join(tracks), 'span': span})
        if 'message' in result:
            raise RuntimeError(result['message'])
        
        if countsOnly:
            return self.__countOverlaps(result)
        return self.__overlaps2features(result)


    async def get_informative_tracks(self, span: str, assembly: str, sort=False):
        result = self.__wrapper.make_request(self._INFORMATIVE_TRACKS_ENDPOINT, {'span': span, 'assembly': assembly})
        result = [{'track_id' : track['Identifier'], 'num_overlaps': track['numOverlaps']} for track in result]
        # sort by most hits
        return sorted(result, key = lambda item: item['num_overlaps'], reverse=True) if sort else result



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
        
    
    async def get_track_metadata(self, tracks: List[str], validate=True) -> Track:
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
            
