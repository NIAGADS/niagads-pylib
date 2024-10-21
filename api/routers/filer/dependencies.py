from sqlmodel import select, col, or_, func, distinct
from sqlalchemy import Values, String, column as sqla_column
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from collections import OrderedDict

from niagads.filer.api import FILERApiWrapper
from niagads.utils.list import list_to_string
from niagads.utils.dict import rename_key

from api.internal.config import get_settings
from api.dependencies.database import DatabaseSessionManager
from api.dependencies.filter_params import tripleToPreparedStatement
from api.dependencies.shared_params import OptionalParams
from .models.track_metadata_cache import Track

ROUTE_PREFIX = "/filer"
ROUTE_NAME = "FILER Functional Genomics Repository"
ROUTE_ABBREVIATION = "FILER"
ROUTE_DESCRIPTION = {}
ROUTE_TAGS = [ROUTE_NAME]
__ROUTE_DATABASE = 'metadata'
ROUTE_SESSION_MANAGER = DatabaseSessionManager(__ROUTE_DATABASE)

_BIOSAMPLE_FIELDS = ["life_stage", "biosample_term", "system_category",
    "tissue_category", "biosample_display",
    "biosample_summary", "biosample_term_id"]

TRACK_SEARCH_FILTER_FIELD_MAP = { 
    'biosample': {
        'model_field' : 'biosample_characteristics', 
        'description': "searches across biosample characteristics, including, " +
            "but not limited to: biological system, tissue, cell type, cell line, " +
            "life stage; can be searched using ontology terms from UBERON (tissues), CL (cells), " + 
            "CLO (cell lines), and EFO (experimental factors); NOTE: biosample term matches are fuzzy and case insensitive"
        },
    'antibody': {
        'model_field': 'antibody_target',
        'description': "the antibody target, e.g. in a CHiP-SEQ experiment; " + 
            "we recommend searching for gene targets with `like` operator as many are prefixed"
    },
    'assay': {
        'model_field': 'assay',
        'description': 'type of assay'
    },
    'feature': {
        'model_field': 'feature_type',
        'description': "the type of functional genomics feature reported in the data track"
    },
    'analysis': {
        'model_field': 'analysis',
        'description': "type of statistical analysis, if relevant"
    },
    'classification': {
        'model_field': 'classification',
        'description': "specific categorization or classification of the data reported in the data track"
    },
    'category': {
        'model_field': 'data_category',
        'description': "broad categorization of the type of the data reported in the data track"
    },
    'datasource': {
        'model_field': 'data_source',
        'description': "original third-party data source for the track"
    },
}



class ApiWrapperService:
    _OVERLAPS_ENDPOINT = 'get_overlaps'
    _INFORMATIVE_TRACKS_ENDPOINT = 'get_overlapping_tracks_by_coord'
    
    def __init__(self):
        self.__request_uri = get_settings().FILER_REQUEST_URI
        self.__wrapper = FILERApiWrapper(self.__request_uri)
    
    def __validate_tracks(self, tracks: List[str]):
        service = MetadataQueryService(ROUTE_SESSION_MANAGER)
        service.validate_tracks(tracks) # raises error if invalid tracks found
        
    def __rename_keys(self, dictObj, keyMapping):
        for oldKey, newKey in keyMapping.items():
            dictObj = rename_key(dictObj, oldKey, newKey)
        return dictObj
    
    
    def __clean_hit_result(self, hitList):
        queryRegion = hitList[0]['queryRegion']
        hits = {record['Identifier']: record['features'] for record in hitList }
        hits.update({'query_region': queryRegion})
        return hits
        
    def get_track_hits(self, tracks: str, span: str):
        result = self.__wrapper.make_request(self._OVERLAPS_ENDPOINT, {'id': tracks, 'span': span})
        return self.__clean_hit_result(result)
    
    
    def get_informative_tracks(self, span: str, assembly: str, sort=False):
        result = self.__wrapper.make_request(self._INFORMATIVE_TRACKS_ENDPOINT, {'span': span, 'assembly': assembly})
        result = {track['Identifier'] : track['numOverlaps'] for track in result}
        # sort by most hits
        return OrderedDict(sorted(result.items(), key = lambda item: item[1], reverse=True)) if sort else result
    
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
            raise ValueError(f'Invalid track identifiers found: {list_to_string(result)}')
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
        for bsf in _BIOSAMPLE_FIELDS:
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

    async def query_track_metadata(self, assembly: str, 
            filters: List[str] | None, keyword: Optional[str], 
            options: OptionalParams) -> List[Track]:
        
        if (options.idsOnly and options.countOnly):
            raise ValueError("please set only one of `idsOnly` or `countOnly` to `TRUE`")
        
        target = Track.track_id if options.idsOnly \
            else func.count(Track.track_id) if options.countOnly else Track

        statement = select(target).filter(col(Track.genome_build) == assembly)
        if filters is not None:
            statement = self.__add_statement_filters(statement, filters)
        if keyword is not None:
            # TODO: add antibody targets to searchable text during cache build
            statement = statement.filter(or_(
                col(Track.searchable_text).regexp_match(keyword, 'i'),
                col(Track.antibody_target).regexp_match(keyword, 'i')))
            
        if not options.countOnly:
            statement = statement.order_by(Track.track_id)
            if options.limit:
                statement = statement.limit(options.limit)

        result = await self.__session.execute(statement)

        if options.countOnly:
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
            
        result = await self.__session.execute(statement)
        result = result.all()
        return {row[0]: row[1] for row in result} if inclCounts else list(result)


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
            
