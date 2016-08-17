class EnumMeta(type):
    """ Enum metaclass. Creates a values dictionary with the attribute name as its own value """
    def __new__(mcs, name, bases, dct):
        for val in dct:
            dct[val] = val
        dct['values'] = {k: v for k, v in dct.items() if not k.startswith('__')}
        return type.__new__(mcs, name, bases, dct)

class NoCopy(object):
    def __deepcopy__(self, memo):
        return self

class BaseEnum(NoCopy):
    __metaclass__ = EnumMeta
