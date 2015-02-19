"""
Implementations of items go here.

TODO: implement items.
"""

class Item(object):
    choicelock = False
    is_mega_stone = False
    is_berry = False
    is_plate = False
    is_drive = False
    is_removable = True

    def __init__(self, name):
        self.name = name

class _tmp_DefaultDict(dict):
    """
    Placeholder itemdex.
    """
    def __getitem__(self, value):
        try:
            return dict.__getitem__(self, value)
        except KeyError:
            return Item('')

itemdex = _tmp_DefaultDict()
itemdex['safariball'] = Item('safariball')
