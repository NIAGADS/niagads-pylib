# NIAGADS-API Docker Installation

## Requirements

* `docker`
* `docker-compose`
* if running on a Windows or Mac, the `project folder` needs to be in a directory for which `file sharing` has been enabled for `Docker Desktop`

## create a project folder

Suggested name: `niagads-api-<version>`, e.g.

```bash
mkdir niagads-api-alpha
```

## Clone the NIAGADS API code and the NIAGADS docker-repo from the `GitHub` repository into the project folder

```bash
cd niagads-api-<version>
git clone https://github.com/NIAGADS/niagads-api.git
git clone https://github.com/NIAGADS/docker-repo.git
```

## Set the `API` configuration

First create the `.env` file for the `niagads-api` app from the provided `sample.env` file:

```bash
cp niagads-api/config/sample.env niagads-api/config/.env
```

And then edit the `.env` file as follows:

* for development, set `FLASK_DEBUG=TRUE`

* update the `SQLALCHEMY_DATABASE_URI`, substituting the PostgreSQL connection string with the one provided to you.  

* set `GENOMICSDB_GRCh38` to `genomicsdb` or to specific `genomicsdb_clone_<date>` if in a development environment
* set `GENOMICSDB_GRCh37` to `genomicsdb37` or to a specific `genomicsdb37_clone_<date>` if in a develpoment environment

> NOTE: **Without** this connection string, database names, and access to the `GenomicsDB` database servers, you **can still deploy the API** to make queries against `FILER` (and `VariXam`, when in place).  **`ADVP` and `GenomicsDB` endpoints will fail**.

* set the `FILER_METADATA_TEMPLATE_FILE`.  Current file is: 

```GADB_metadata_V1_final_06132023.fixed_download_prefix.fixed_missing_wget.metadata.v1.2023_0523.tsv```

* set the `API_VERSION`.  Current `production` version is `alpha`

> NOTE: The API will prepend the version to the endpoints, so requests will be made to `https://api.niagads.org/<version>`, in `production` or to `http://localhost:$PORT/<version>` in `development`

## Set the `Docker` build environment

First create the `.env` file for the `docker-repo/niagads-api` project from the provided `sample.env` file:

```bash
cp docker-repo/niagads-api/sample.env .env
```

And edit the `.env` as follows:

* set the `PORT` value for the `niagads-api` application (e.g., will be deployed at `localhost:$PORT` on the host machine).  For the `AWS` servers, leave at default value `8081` 

* set the `APPLICATON_DIR` to the full path where the `niagads-api` code was placed, e.g., `<full_path_to>/niagads-api-<version>/niagads-api` 

* set `API_VERSION` to the same value as `API_VERSION` in the application config; this will be used to name the container and images

## Run  `docker-compose` to build the `API` docker container. 

```bash
docker-compose -f "niagads-api/docker-compose.yaml" up -d --build
```

> NOTE: depending on how `docker compose` was installed on your system, the command may be either `docker-compose` or `docker compose`

> NOTE: This will build and deploy the API service, but `FILER` queries and `pagination` will not work because the `cache DB` has not yet been instantiated.  See next section.

## Initialize the `FILER Metadata Query Cache`

On the host run the following:

```bash
docker exec init-beta python3 initialize_filer_cache.py --metadataTemplate /files/<file> --logFilePath /logs --connectionString postgresql://<user:pwd>@api-static-db:5432/apistaticdb --commit
```
