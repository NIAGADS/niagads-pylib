from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, select
from sqlalchemy import func

from api.dependencies.database import DBSession
from .model import Track

ROUTE_PREFIX = "/filer"
ROUTE_NAME = "FILER Functional Genomics Repository"
ROUTE_ABBREVIATION = "FILER"
ROUTE_DESCRIPTION = {}

ROUTE_TAGS = [ROUTE_ABBREVIATION]

FilerDatabaseSession = DBSession('filer')

class Service:
    def __init__(self, session: Annotated[Session, Depends(FilerDatabaseSession)]):
        self.__session = session

    def get_count(self) -> int:
        statement = select(Track)
        return self.__session.exec(statement).first()