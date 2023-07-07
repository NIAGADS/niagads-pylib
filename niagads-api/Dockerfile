FROM     python:3.10-alpine

# ARGS
# allowable values for INIT_CACHEDB are 'all', 'filer', 'cache', 'none'
ARG INIT_CACHEDB "none"
ARG PORT 5000


WORKDIR /www

ADD requirements.txt .

# install git & python dependencies
RUN apk update && apk add git \
    && pip install --upgrade pip --no-cache-dir \
    && pip install -r /www/requirements.txt --no-cache-dir

RUN git clone https://github.com/NIAGADS/niagads-api.git
ADD api.env /www/niagads-api/config/.env

# initialize the cache
RUN if [ $INIT_CACHEDB != "none" ] ; then guicorn -w 4 app:create_app(initCacheDB="'$INIT_CACHEDB'") ; fi

CMD ["gunicorn", "-w", "4", "app:create_app(None)", "--bind" "0.0.0.0:$PORT"]
