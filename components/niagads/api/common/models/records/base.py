from niagads.api.common.models.records.mixins import (
    CountsMixin,
    DynamicMixin,
    ORMCompatabileMixin,
)
from niagads.common.models.base import CustomBaseModel


class ORMCompatibleRecord(CustomBaseModel, ORMCompatabileMixin): ...


class DynamicRecord(CustomBaseModel, DynamicMixin): ...


class CountExtendedRecord(CustomBaseModel, CountsMixin): ...
