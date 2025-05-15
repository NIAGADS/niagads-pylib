from io import StringIO
from fastapi import Request, Response
import yaml

def get_openapi_yaml(request: Request) -> Response:
    """Get YAML-formatted openapi specification.

    Converts the API openapi JSON specification to yaml format and returns the formatted yaml

    adapted from https://github.com/tiangolo/fastapi/issues/1140#issuecomment-659469034
    """
    openapi_json = request.app.openapi()
    yaml_s = StringIO()
    yaml.dump(openapi_json, yaml_s)
    return Response(yaml_s.getvalue(), media_type="text/yaml")