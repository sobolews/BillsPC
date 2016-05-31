from functools import partial
import re

# strip ANSI escape characters from a string
strip_ANSI = partial(re.compile(r"""
    \x1b     # literal ESC
    \[       # literal [
    [;\d]*   # zero or more digits or semicolons
    [A-Za-z] # a letter
    """, re.VERBOSE).sub, "")

def received(s):
    return '\033[38;5;213m\033[2m%s\033[0m' % s

def sent(s):
    return '\033[38;5;2m%s\033[0m' % s

def active(s):
    return '\033[38;5;83m\033[2m%s\033[0m' % s
