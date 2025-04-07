from typing_extensions import deprecated
@deprecated("use Collections `defaultdict` instead (https://docs.python.org/3/library/collections.html#collections.defaultdict)")
class AutoVivificationDict(dict):
    """Implementation of perl's autovivification feature. Allows initialization of nested dicts on the fly
    see https://en.wikipedia.org/wiki/Autovivification """
    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value
