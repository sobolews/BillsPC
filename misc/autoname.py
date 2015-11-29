class AutoName(type):
    def __new__(mcs, name, bases, dct):
        dct['name'] = name.lower()
        return type.__new__(mcs, name, bases, dct)

    def __repr__(cls):
        return cls.__name__
