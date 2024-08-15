# Middleware for choosing database based on endpoint

# TODO: connection pooling? 
# should I really be creatinig the engine for each request or should I bind models in an sqlalchemy config

from sqlmodel import Session, create_engine

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

class DBSession:
    def __init__(self, route: str):
        self.__connectionString = get_db_url(route)
        self.__engine = create_engine(self.__connectionString, echo=True, pool_size=50)
    
    def __call__(self):
        return Session(self.__engine)
