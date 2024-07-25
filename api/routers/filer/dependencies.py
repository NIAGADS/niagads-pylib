from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, select, col, or_
from sqlalchemy import func
from typing import List

from api.dependencies.database import DBSession
from api.dependencies.filter_params import tripleToPreparedStatement
from .model import Track

ROUTE_PREFIX = "/filer"
ROUTE_NAME = "FILER Functional Genomics Repository"
ROUTE_ABBREVIATION = "FILER"
ROUTE_DESCRIPTION = {}

ROUTE_TAGS = [ROUTE_ABBREVIATION]

_BIOSAMPLE_FIELDS = ["life_stage", "biosample_term", "system_category",
                     "tissue_category", "biosample_display",
                     "biosample_summary", "biosample_term_id"]

TRACK_SEARCH_FILTER_FIELD_MAP = { 
    'biosample': 'biosample_characteristics',
    'antibody': 'antibody_target',
    'assay': 'assay',
    'category': 'data_category',
    'analysis': 'analysis',
    'classification': 'classification',
    'data_source': 'data_source',
    'feature': 'feature_type'
}


class Service:
    def __init__(self):
        self.__db = DBSession('filer')

    def get_count(self) -> int:
        statement = select(func.count(Track.track_id))
        with self.__db() as session:
            return session.exec(statement).first()
        
    def get_track_metadata(self, trackId: str) -> Track:
        ids = trackId.split(',')
        statement = select(Track).filter(col(Track.track_id).in_(ids))
        # statement = select(Track).where(col(Track.track_id) == trackId) 
        # if trackId is not None else select(Track).limit(100) # TODO: pagination
        with self.__db() as session:
            return session.exec(statement).all()


    def __add_biosample_filters(self, statement, triple: List[str]):
        conditions = []
        for bsf in _BIOSAMPLE_FIELDS:
            conditions.append(tripleToPreparedStatement([f'biosample_characteristics|{bsf}', "like" if triple[1] == 'eq' else "not like" , triple[2]], Track))
        
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
                    statement = statement.filter(
                        tripleToPreparedStatement(
                            [TRACK_SEARCH_FILTER_FIELD_MAP[phrase[0]], phrase[1], phrase[2]],
                            Track
                        ))
                
        return statement

    def query_track_metadata(self, assembly: str, filters: List[str]) -> List[Track]:
        # func.count(Track.track_id) if countOnly else Track
        statement = select(Track).filter(col(Track.genome_build) == assembly)
        statement = self.__add_statement_filters(statement, filters)
        with self.__db() as session:
            return session.exec(statement).all()