from misc.enum import BaseEnum

class Strategy(BaseEnum):
    RANDOM = ()
    MATRIX = ()

class BattleState(BaseEnum):
    NEW_BATTLE = ()
    NEW_TURN = ()
    MUST_SWITCH = ()
    POST_FAINT_SWITCH = ()
    DOUBLE_POST_FAINT_SWITCH = ()
    CHANCE_ACCURACY = ()
    CHANCE_SECONDARY = ()
