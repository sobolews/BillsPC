from unittest import TestCase
from mock import Mock

from battle.enums import Type
from battle.types import effectiveness

class TestTypes(TestCase):
    def setUp(self):
        self.ferrothorn = Mock()
        self.ferrothorn.types = (Type.GRASS, Type.STEEL)
        self.arcanine = Mock()
        self.arcanine.types = (Type.FIRE, None)
        self.typeless = Mock()
        self.typeless.types = (Type.NOTYPE, None)

    def test_type_multiplier(self):
        assert effectiveness(Type.GRASS, self.ferrothorn) == 0.25
        assert effectiveness(Type.FIRE, self.ferrothorn) == 4
        assert effectiveness(Type.ICE, self.ferrothorn) == 1
        assert effectiveness(Type.FIGHTING, self.ferrothorn) == 2
        assert effectiveness(Type.STEEL, self.ferrothorn) == 0.5
        assert effectiveness(Type.NOTYPE, self.ferrothorn) == 1

        assert effectiveness(Type.WATER, self.arcanine) == 2
        assert effectiveness(Type.NORMAL, self.arcanine) == 1
        assert effectiveness(Type.FAIRY, self.arcanine) == 0.5
        assert effectiveness(Type.NOTYPE, self.arcanine) == 1

        assert effectiveness(Type.POISON, self.typeless) == 1
        assert effectiveness(Type.NOTYPE, self.typeless) == 1
