# GenomicsDB Databaset Local Dev Environment

## PostgreSQL 17 Docker Setup

### 1. Configure Environment Variables

Copy** `sample.db.env` to `db.env` and `sample.env` to `.env` and set the following values:

* `POSTGRES_USER`: Set your desired PostgreSQL admin username.
* `POSTGRES_PASSWORD`: Set a password for the admin user.
* `POSTGRES_DB`: the database to be created: `genomicsdb_dev`.

* `POSTGRES_VOLUME_PATH`: Set the absolute path on your host machine for PostgreSQL data storage (e.g., `/home/youruser/pgdata`).
* `POSTGRES_HOST_PORT`: Set the host port to expose PostgreSQL (default: `5432`). Change this if you want to use a different port on your host.

> ** **COPY**, not rename.  If you rename the files you may accidentally end up removing the `sample` files from the repository.

**Note:**

- For Docker Desktop, ensure the selected path is within a file-shared directory (see Docker Desktop settings > Resources > File Sharing).

 The value of `POSTGRES_HOST_PORT` determines which port on your host machine will be mapped to the PostgreSQL service inside the container. If you change this value, connect to PostgreSQL using the new port.

- The target directory for `POSTGRES17_VOLUME_PATH` must be empty before the first or clean run to allow PostgreSQL to initialize a fresh database. 

### 2. Start Docker Compose (Detached)

Run the following command in this directory:

```bash
docker compose up db -d
```

This will start the PostgreSQL 17 service in detached mode.

### 3. Additional Notes

- If you need to reset the database, stop the container, delete all contents in the volume path, and restart Docker Compose.

- For more details on Docker Desktop file sharing, refer to the official Docker documentation.
