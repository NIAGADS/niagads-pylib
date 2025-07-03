# mixins and base models
from niagads.common.models.core import TransformableModel
from niagads.utils.string import dict_to_info_string
from pydantic import model_serializer


class ModelDumpMixin(object):
    def model_dump(self):
        """usage: track.model_dump()"""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }
