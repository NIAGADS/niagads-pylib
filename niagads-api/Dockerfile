# syntax=docker/dockerfile:1

FROM node:alpine as build

ARG BUILD=dev

# Install python/pip
ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python \
    && python3 -m ensurepip \
    && pip3 install --no-cache --upgrade pip setuptools  
    #\
#    && apt remove -y python3-pip        \
#    && apt autoremove --purge -y                         \
#    && rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/*.list

WORKDIR /app

RUN npm install && npm run start-$BUILD

CMD tail -f /dev/null


# COPY ./package.json /app/package.json
# COPY ./package-lock.json /app/package-lock.json

# RUN yarn install
# COPY . .
# RUN yarn build


# FROM nginx:alpine
# COPY ./nginx/nginx.conf /etc/nginx/conf.d/default.conf
# COPY --from=build /app/build /usr/share/nginx/html

# WORKDIR /app

# ADD requirements.txt .

# # install git & python dependencies
# RUN pip install --upgrade pip --no-cache-dir \
#     && pip install -r /app/requirements.txt --no-cache-dir

# ENV SERVICE_PORT=$PORT 

# CMD ls /app && gunicorn -w 4 --reload --bind 0.0.0.0:8000 'app:create_app(None)'
