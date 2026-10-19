import asyncio
import json

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from niagads.api.common.exception_handlers import runtime_exception_handler


@pytest.mark.parametrize("explicit_cause", [False, True])
def test_runtime_handler_preserves_wrapped_request_validation(explicit_cause):
    errors = [
        {
            "type": "greater_than_equal",
            "loc": ("query", "flank"),
            "msg": "Input should be greater than or equal to 0",
            "input": "-1",
            "ctx": {"ge": 0},
        }
    ]
    with pytest.raises(RuntimeError) as caught:
        try:
            raise RequestValidationError(errors)
        except RequestValidationError as err:
            if explicit_cause:
                raise RuntimeError("Unexpected Error") from err
            raise RuntimeError("Unexpected Error")

    request = Request({"type": "http", "path": "/", "headers": []})
    response = asyncio.run(runtime_exception_handler(request, caught.value))

    assert response.status_code == 422
    detail = json.loads(response.body)["detail"]
    assert detail[0]["loc"] == ["query", "flank"]
    assert detail[0]["type"] == "greater_than_equal"
    assert detail[0]["input"] == "-1"


def test_runtime_handler_retains_internal_error_response():
    request = Request({"type": "http", "path": "/", "headers": []})
    response = asyncio.run(
        runtime_exception_handler(request, RuntimeError("Unexpected failure"))
    )

    assert response.status_code == 500
    assert json.loads(response.body)["detail"] == "Unexpected failure"
