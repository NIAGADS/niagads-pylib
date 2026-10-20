# Open Access API

## Configure Docker and the API

Run these commands from `projects/open-access-api` in the monorepo checkout.
Poetry and Docker Compose are required.

```bash
cp docker.env.sample .env
cp dev.runtime.env.sample dev.runtime.env
```

Edit `.env` to set `KEYDB_DATA_DIR` to an existing host directory for
cache persistence, and configure the exposed ports. Set `API_VERSION` to
the version in this project's `pyproject.toml` so Docker selects the correct
wheel from `dist/`.

> Current **API_VERSION** = 2.0.0

Edit `{service_env}.runtime.env` (`service_env` = `dev` or `prod`) to configure the API's database connection and URLs.
Use the Compose service name `oaa-cachedb` for the cache hostname:

In development, make sure to update the `DATABASE_URI` to use the port of your database or database tunnel if you are not following project recommendations. In development, the database listener must be reachable from the container through `host.docker.internal`.

## Build the wheel and Docker image

```bash
poetry build
docker compose build oaa-service
```

Rebuild both after changing application code or project dependencies.

## Start the cache

```bash
docker compose up -d oaa-cachedb
```

## Start the API with its runtime environment

```bash
docker run -d \
  --name oaa-service \
  --restart always \
  --network oa-network \
  --add-host host.docker.internal:host-gateway \
  --env-file dev.runtime.env \
  -p 8000:8000 \
  oaa-service:2.0.0
```

Run this after starting the cache, which creates `oa-network`. Use the image
version matching `API_VERSION` in `.env`, and change the left side of
`-p 8000:8000` to your desired host port. For production, pass
`--env-file prod.runtime.env` instead.

After changing the runtime environment or rebuilding the image, remove the
existing API container before repeating the `docker run` command:

```bash
docker stop oaa-service
docker rm oaa-service
```

With the example port mapping, the API is available at `http://localhost:8000`.

View the API logs:

```bash
docker logs --tail 100 -f oaa-service
```
