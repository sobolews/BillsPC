from showdowndata.miner import RandbatsStatistics

rbstats = RandbatsStatistics.from_pickle()

def rbstats_key(battlepokemon):
    """
    Get the rbstats key associated with a BattlePokemon. For use by clients of RandbatsStatistics.
    """
    if battlepokemon.can_mega_evolve or battlepokemon.is_mega:
        return battlepokemon.item.forme
    else:
        return '%sL%d' % (battlepokemon.base_species, battlepokemon.level)
