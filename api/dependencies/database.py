# Middleware for choosing database based on endpoint
# adapted from https://stackoverflow.com/a/73063895

# TODO: need to add app.add_middleware(DatabaseSelector) to main.py
# TODO: how would this change w/SQLModel?!
# https://github.com/tiangolo/fastapi/issues/2592 I think this solution is preferred; 
# I don't like the below that sets environmental variables

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

from api.internal.config import get_settings

def get_db_url(route: str = 'cache'):
    match route:
        case 'genomics':
            return get_settings().GENOMICSDB_URL
        case 'advp':
            return get_settings().GENOMICSDB_URL
        case 'cache':
            return get_settings().API_CACHEDB_URL
        case 'ontology':
            return get_settings().API_STATICDB_URL
        case 'filer': # filer
            return get_settings().API_STATICDB_URL 
        case _:
            raise ValueError('Need to specify endpoint database - one of: genomics, advp, cache, ontology, or filer')

def get_db(url: str = 'cache'):
    engine = create_engine(url, echo=True, pool_size=50)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        

class DBSession:
    def __init__(self, route: str):
        self.__connectionString = get_db_url(route)
        
    def __call__(self):
        get_db(self.__connectionString)