from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, select, col
from sqlalchemy import func

from api.dependencies.database import DBSession
from .model import Track

ROUTE_PREFIX = "/filer"
ROUTE_NAME = "FILER Functional Genomics Repository"
ROUTE_ABBREVIATION = "FILER"
ROUTE_DESCRIPTION = {}

ROUTE_TAGS = [ROUTE_ABBREVIATION]

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

        