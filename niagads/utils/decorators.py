from functools import wraps

# adapted from https://stackoverflow.com/a/18078819
class hybridmethod(object):
    """
    decorator that lets you define a classmethod that can also operate as a regular member method
    (e.g., take cls or self as the object)
    Args:
        object: class or self; i.e., Pair.get() or p.get() if p is a Pair
    """
    
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls):
        context = obj if obj is not None else cls

        @wraps(self.func)
        def hybrid(*args, **kw):
            return self.func(context, *args, **kw)

        # optional, mimic methods some more
        hybrid.__func__ = hybrid.im_func = self.func
        hybrid.__self__ = hybrid.im_self = context

        return hybrid
