# ummm, this is weird, found here:
# http://code.activestate.com/recipes/52304-static-methods-aka-class-methods-in-python/
class Callable:
    def __init__(self, anycallable):
        self.__call__ = anycallable