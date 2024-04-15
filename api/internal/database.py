# Middleware for choosing database based on endpoint
# adapted from https://stackoverflow.com/a/73063895

# TODO: need to add app.add_middleware(DatabaseSelector) to main.py
# TODO: how would this change w/SQLModel?!
# https://github.com/tiangolo/fastapi/issues/2592 I think this solution is preferred; 
# I don't like the below that sets environmental variables


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_db():
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=True, pool_size=50)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DatabaseSelector(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        url_param = str(request.url).split("/")
        if "api" in str(request.url):
            url_param.remove("api")
        route_name = url_param[3]
        if route_name not in list(routeMap.keys()):
            SQLALCHEMY_DATABASE_URI = routeMap["base_mysql"]
        else:
            SQLALCHEMY_DATABASE_URI = routeMap[route_name]
        os.environ["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
        response = await call_next(request)
        return response