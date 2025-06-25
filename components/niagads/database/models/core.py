from niagads.common.core import NullFreeModel
from pydantic import ConfigDict


class ModelDumpMixin(object):
    def model_dump(self):
        """usage: track.model_dump()"""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }


class CompositeAttributeModel(NullFreeModel):
    model_config = ConfigDict(serialize_by_alias=True)
