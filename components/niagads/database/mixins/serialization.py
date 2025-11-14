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
