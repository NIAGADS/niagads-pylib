class ModelDumpMixin(object):
    """Mixin class for dumping model attributes.

    This class provides a method to serialize the attributes of a model into a dictionary.
    """

    def model_dump(self):
        """Dump the model attributes into a dictionary.

        Returns:
            dict: A dictionary containing the model's attributes and their values.
        """
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }
