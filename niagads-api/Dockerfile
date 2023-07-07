FROM     python:3.10-alpine

# ARGS
ARG PORT 5000

# install git
RUN apk update && apk add git

# WORKDIR  /app
# COPY     ./myapp.py 	./
# COPY	./requirements.txt		./
# RUN     pip install --upgrade pip --no-cache-dir
# RUN		pip install –r /app/requirements.txt --no-cache-dir
# CMD		[“gunicorn”,”-w” “4”,”myapp:app”,”--bind” “0.0.0.0:8000”]