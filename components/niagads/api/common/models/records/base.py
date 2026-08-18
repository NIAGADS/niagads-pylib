from niagads.api.common.models.data.mixins import (
    CountsMixin,
    DynamicMixin,
    ORMCompatabileMixin,
)
from niagads.common.models.base import CustomBaseModel


class ORMCompatibleRecord(CustomBaseModel, ORMCompatabileMixin): ...


class DynamicRecordModel(CustomBaseModel, DynamicMixin): ...


class CountRecordModel(CustomBaseModel, CountsMixin): ...
