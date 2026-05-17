from abc import ABC, abstractmethod
from niagads.api.common.constants import DEFAULT_NULL_STRING
from niagads.common.models.base import CustomBaseModel
from niagads.utils.string import xstr


class AbstractViewMixin(ABC):
    @abstractmethod
    def to_table(self, id: str = None, title: str = None):
        """return a table view response"""
        pass
