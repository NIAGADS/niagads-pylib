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

``` bash
cp sample.env .env
```

Edit the `.env` file

## Build the docker image

``` shell
docker build -t myimage .
```

## Run the image

``` shell
docker run -d --name mycontainer -p 8000:8000 myimage
```

The OpenAPI specification of this FastAPI app can now be accessed at `http://localhost:8000/vX/docs` where X is the major version.