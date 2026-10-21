import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from niagads.api.common.services.gene import GeneEndpointService
from niagads.api.common.services.variant import VariantEndpointService


@pytest.mark.parametrize("service_class", [GeneEndpointService, VariantEndpointService])
@pytest.mark.parametrize("flank", [0, 25])
def test_feature_location_uses_first_raw_record(service_class, flank):
    service = service_class(context=None, parameters=None, response_config=None)
    service._lookup_records = AsyncMock(
        return_value={
            "identifier": [
                {"chromosome": "chr19", "span": "[90,201)"},
                {"chromosome": "chr19", "span": "[110,211)"},
            ]
        }
    )

    region = asyncio.run(service.get_feature_location("identifier", flank=flank))

    service._lookup_records.assert_awaited_once_with(["identifier"])
    assert str(region.chromosome) == "chr19"
    assert region.start == 90 - flank
    assert region.end == 200 + flank


@pytest.mark.parametrize("service_class", [GeneEndpointService, VariantEndpointService])
def test_feature_location_not_found(service_class):
    service = service_class(context=None, parameters=None, response_config=None)
    service._lookup_records = AsyncMock(return_value={"missing": []})

    with pytest.raises(HTTPException) as error:
        asyncio.run(service.get_feature_location("missing"))

    assert error.value.status_code == 404
