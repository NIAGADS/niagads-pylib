from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, select, col, or_
from sqlalchemy import func, distinct, Values, String, column as sqla_column
from typing import List, Optional

from niagads.filer.api import FILERApiWrapper
from niagads.utils.list import list_to_string
from niagads.utils.dict import rename_key

from api.internal.config import get_settings
from api.dependencies.database import DBSession
from api.dependencies.filter_params import tripleToPreparedStatement
from api.dependencies.shared_params import OptionalParams
from .model import Track

ROUTE_PREFIX = "/filer"
ROUTE_NAME = "FILER Functional Genomics Repository"
ROUTE_ABBREVIATION = "FILER"
ROUTE_DESCRIPTION = {}

ROUTE_TAGS = [ROUTE_NAME]

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
    'data_source': {
        'model_field': 'data_source',
        'description': "original third-party data source for the track"
    },
}


class ApiWrapperService:
    _OVERLAPS_ENDPOINT = 'get_overlaps'
    
    
    def __init__(self):
        self.__request_uri = get_settings().FILER_REQUEST_URI
        self.__wrapper = FILERApiWrapper(self.__request_uri)
    
    def __validate_tracks(self, tracks: List[str]):
        service = CacheQueryService()
        service.validate_tracks(tracks) # raises error if invalid tracks found
        
    def __rename_keys(self, dictObj, keyMapping):
        for oldKey, newKey in keyMapping.items():
            dictObj = rename_key(dictObj, oldKey, newKey)
        return dictObj
    
    
    def __clean_hit_result(self, hitList):
        queryRegion = hitList[0]['queryRegion']
        hits = {record['Identifier']: record['features'] for record in hitList if len(record['features']) > 0}
        hits.update({'query_region': queryRegion})
        return hits
        
    def get_track_hits(self, tracks: str, span: str):
        result = self.__wrapper.make_request(self._OVERLAPS_ENDPOINT, {'id': tracks, 'span': span})
        return self.__clean_hit_result(result)

class CacheQueryService:
    def __init__(self):
        self.__db = DBSession('filer')

    def validate_tracks(self, tracks: List[str]):
        # solution for finding tracks not in the table adapted from
        # https://stackoverflow.com/a/73691503

        lookups = Values(sqla_column('track_id', String), name='lookups').data([(t, ) for t in tracks])
        statement = select(lookups.c.track_id).outerjoin(
            Track, col(Track.track_id) == lookups.c.track_id).where(col(Track.track_id) == None)
        with self.__db() as session:
            result = session.exec(statement).all()
            if len(result) > 0:
                raise ValueError(f'Invalid track identifiers found: {list_to_string(result)}')
            else:
                return True

    def get_count(self) -> int:
        statement = select(func.count(Track.track_id))
        with self.__db() as session:
            return session.exec(statement).first()
        
    
    def get_track_metadata(self, tracks: List[str]) -> Track:
        statement = select(Track).filter(col(Track.track_id).in_(tracks)).order_by(Track.track_id)
        # statement = select(Track).where(col(Track.track_id) == trackId) 
        # if trackId is not None else select(Track).limit(100) # TODO: pagination
        with self.__db() as session:
            return session.exec(statement).all()


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

    def query_track_metadata(self, assembly: str, filters: List[str] | None, keyword: Optional[str], options: OptionalParams) -> List[Track]:
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

        with self.__db() as session:
            result = session.exec(statement).all()
            if options.countOnly:
                return {'track_count': result[0] }
            return result
        
    def get_track_filter_summary(self, filterField:str, inclCounts: Optional[bool] = False) -> dict:
        modelField = TRACK_SEARCH_FILTER_FIELD_MAP[filterField]['model_field']

        valueCol = col(getattr(Track, modelField))
        if 'biosample' in modelField:
            valueCol = valueCol['tissue_category'].astext
        # statement = select(valueCol, Track.track_id).group_by(valueCol).count()
        statement = select(distinct(valueCol), func.count(Track.track_id)).where(valueCol.is_not(None)).group_by(valueCol) \
            if inclCounts else select(distinct(valueCol)).where(valueCol.is_not(None))
        with self.__db() as session:
            result = session.exec(statement).all()
            return {row[0]: row[1] for row in result} if inclCounts else list(result)

    def get_genome_build(self, tracks: List[str]) -> str:
        """ retrieves the genome build for a set of tracks; returns track -> genome build mapping if not all on same assembly"""
        statement = select(distinct(Track.genome_build)).where(col(Track.track_id).in_(tracks))
        with self.__db() as session:
            result = session.exec(statement).all()
            if len(result) > 1: 
                statement = select(Track.track_id, Track.genome_build).where(col(Track.track_id).in_(tracks)).order_by(Track.genome_build, Track.track_id)
                result = session.exec(statement).all()
                return {row[0]: row[1] for row in result}
            else:
                return result[0]