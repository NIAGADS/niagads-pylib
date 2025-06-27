# mixins and base models

from niagads.common.models.core import CompositeAttributeModel
from niagads.utils.string import dict_to_info_string
from pydantic import model_serializer


class ModelDumpMixin(object):
    def model_dump(self):
        """usage: track.model_dump()"""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }


class CompositeAttributeModel(CompositeAttributeModel):
    @model_serializer()
    def serialize_model(self, listsAsStrings: bool = False):
        if listsAsStrings:
            raise NotImplementedError(
                f"This is an abstract method; please implement a custom model serializer in the child class."
                f"See metadata.composite_attributes.Phenotype for an example."
            )
        return self.model_dump()

    def as_info_str(self):
        obj = self.serialize_model(listsAsStrings=True)
        return dict_to_info_string(obj)
