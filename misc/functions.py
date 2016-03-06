def clamp_int(num, lower, upper=float('inf')):
    assert lower <= upper, 'Wrong order: (%d %d %d)' % (num, lower, upper)
    assert isinstance(num, int)

    return min(upper, max(lower, num))

def gf_round(number):
    """
    GameFreak rounds *down* at 0.5
    """
    return int(number + 1) if number % 1 > 0.5 else int(number)

def priority(n):
    """Method decorator: set the priority attribute to n"""
    def decorator(method):
        method.priority = n
        return method
    return decorator

def attr(attribute, value):
    """Method decorator: set an function attribute"""
    def decorator(method):
        setattr(method, attribute, value)
        return method
    return decorator

def normalize_name(name):
    """
    Converts ('p2a: Galvantula' --> 'galvantula')
             ('Thundurus-Therian' --> 'thundurustherian')
             ('Bug Buzz' --> 'bugbuzz')
             ("Farfetch'd" --> 'farfetchd')
             ('ability: Slow Start' --> 'slowstart')
    etc.
    """
    return str(name).split(':')[-1].strip().lower().translate(None, " -'.")
