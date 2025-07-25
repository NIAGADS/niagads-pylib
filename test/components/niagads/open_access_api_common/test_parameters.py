from niagads.api_common.parameters import core, response


def test_sample():
    assert core is not None
    assert response is not None


def test_response_params():
    x: core.EnumParameter = response.ResponseContent.exclude(
        "no summary", [response.ResponseContent.BRIEF]
    )

    assert "SUMMARY" not in x.get_description()
