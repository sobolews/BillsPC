from battle.battlepokemon import BattlePokemon

UNREVEALED = '<unrevealed>'

class UnrevealedPokemon(BattlePokemon):
    """
    A placeholder Pokemon object representing an unknown pokemon on the foe's bench.
    """
    def __init__(self):
        self.name = UNREVEALED
        self.is_active = False

    def not_implemented(self, *args, **kwargs):
        raise AssertionError('This pokemon has not been revealed yet')

    set_effect = has_effect = get_effect = remove_effect = clear_effects = \
    suppress_ability = unsuppress_ability = \
    calculate_stat = calculate_initial_stats = _calc_hp = calculate_evs_ivs = \
    is_immune_to_move = is_immune_to = take_item = set_item = use_item = not_implemented

    def _debug_sanity_check(self, engine):
        pass

    def cure_status(self):
        pass

    def is_fainted(self):
        return False

    def __str__(self):
        return '<unrevealed pokemon>'

    def __repr__(self):
        return 'UnrevealedPokemon(side=%d)' % self.side.index
