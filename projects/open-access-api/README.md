# Example usage

## Clone the repository

```bash
git clone https://github.com/NIAGADS/niagads-pylib.git
```

Navigate to this project folder (where the `pyproject.toml` file is)

Run:

``` shell
poetry build-project
```

## Set up the environmental variables

```bash
cp sample.env .env
```

Edit the `.env` file

## Build the docker image using the docker compose file:

```bash
docker compose up -d 
```
