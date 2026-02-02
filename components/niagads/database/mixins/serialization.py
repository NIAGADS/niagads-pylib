from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from sqlalchemy import ARRAY, Date, DateTime
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy_utils import LtreeType

COMPLEX_TYPES = (ARRAY, LtreeType, JSONB, JSON, Date, DateTime)


class ModelDumpMixin(object):
    """
    Mixin providing a method to dump model column-value pairs as a dictionary.
    Mirrors pydantic model_dump
    """

    def model_dump(self):
        """Return a dictionary of column names and their values for the model instance."""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

    @classmethod
    def json_schema(cls, make_fields_optional: bool = True):
        """
        Generate a JSON Schema for the SQLAlchemy model using marshmallow-sqlalchemy.
        This is meant to help w/ETL config files.  Ignores PKs, dates, and complex data types.

        Args:
            make_fields_optional (bool): If True, sets all fields as optional in the schema.

        Returns:
            dict: JSON Schema representing the model.
        """

        class _Schema(SQLAlchemyAutoSchema):
            class Meta:
                model = cls
                load_instance = True

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                # Remove primary key fields from the schema
                pk_names = [key.name for key in cls.__table__.primary_key.columns]
                for pk in pk_names:
                    self.fields.pop(pk, None)

                for column in cls.__table__.columns:
                    if isinstance(column.type, COMPLEX_TYPES):
                        self.fields.pop(column.name, None)
                    if "run_id" in column.name:
                        self.fields.pop(column.name, None)

                if make_fields_optional:
                    for field in self.fields.values():
                        field.required = False

        return _Schema().json_schema()
