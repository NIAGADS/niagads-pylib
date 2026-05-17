from niagads.api.common.models.domain.mixins import DynamicMixin
from niagads.common.models.base import CustomBaseModel


class DynamicRecordModel(CustomBaseModel, DynamicMixin): ...
