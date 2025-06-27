# mixins for database models


class ModelDumpMixin(object):
    def model_dump(self):
        """usage: track.model_dump()"""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }
