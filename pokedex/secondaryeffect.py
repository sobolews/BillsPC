class SecondaryEffect(object):
    """
    Represents a secondary effect of a move, which may be applied (with `chance` probability)
    when the move is successful.
    """
    def __init__(self, chance, boosts=None, volatile=None, status=None, callback=None,
                 affects_user=False):
        self.chance = chance
        self.boosts = boosts
        self.volatile = volatile
        self.status = status
        self.callback = callback
        self.affects_user = affects_user

    def __str__(self):
        return (''.join(['%s%%, ' % self.chance,
                         '%s' % self.boosts if self.boosts else '',
                         '%s' % self.volatile if self.volatile else '',
                         '%s' % self.status if self.status else '',
                         'callback' if self.callback else ''])
                .join(['<SecondaryEffect: ', '>']))
