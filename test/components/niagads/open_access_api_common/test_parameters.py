from niagads.open_access_api_common.parameters import core, response


def test_sample():
    assert core is not None
    assert response is not None


def test_response_params():
    x: core.CustomizableEnumParameter = response.ResponseContent.exclude(
        "no summary", [response.ResponseContent.SUMMARY]
    )

    assert "SUMMARY" not in x.get_description()
