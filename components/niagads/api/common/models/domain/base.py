from niagads.api.common.models.domain.mixins import (
    DynamicMixin,
    ORMCompatabileMixin,
    ResultMetricsMixin,
)
from niagads.common.models.base import CustomBaseModel


class ORMCompatibleRecord(CustomBaseModel, ORMCompatabileMixin): ...


class DynamicRecordModel(CustomBaseModel, DynamicMixin): ...
