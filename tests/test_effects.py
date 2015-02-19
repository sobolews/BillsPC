import inspect
from unittest import TestCase

from pokedex import effects, abilities, statuses, weather, baseeffect

class TestEffectDefinitions(TestCase):
    def setUp(self):
        self.all_effects = [effect_cls for module in (effects, abilities, statuses, weather)
                            for effect_cls in vars(module).items() if
                            inspect.isclass(effect_cls) and
                            issubclass(effect_cls, baseeffect.BaseEffect) and
                            effect_cls is not baseeffect.BaseEffect]

    def test_all_effects_have_source(self):
        for effect in self.all_effects:
            self.assertIsNotNone(effect.source)
