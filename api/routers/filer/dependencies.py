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

class Service:
    def __init__(self):
        self.__db = DBSession('filer')

    def get_count(self) -> int:
        statement = select(Track)
        with self.__db() as session:
            return session.exec(statement).first()