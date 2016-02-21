if __debug__: from _logging import log

from pokedex.enums import FAIL

class EffectHandlerMixin:
    """
    Provides common functionality to classes that register effect handlers.  Such classes must
    initialize an effect_handlers dictionary mapping handler name to list of bound handler methods.
    """
    def _set_handlers(self, effect):
        for name in effect.handler_names:
            method = getattr(effect, name)
            priority = getattr(method, 'priority', None)
            handlers = self.effect_handlers[name]
            if priority is None:
                handlers.append(method)
            else:
                for i, existing_effect in enumerate(self.effect_handlers[name][::-1]):
                    if priority <= existing_effect.priority:
                        handlers.insert(len(handlers) - i, method)
                        break
                else:
                    handlers.insert(0, method)

    def _remove_handlers(self, effect):
        for name in effect.handler_names:
            self.effect_handlers[name].remove(getattr(effect, name))

    def activate_effect(self, name, *args, **kwargs):
        """
        Call all bound handlers for the named effect type, with *args as the handler method's
        arguments. Handlers are already in sorted priority order, if applicable.

        When failfast is passed as a keyword arg, bail out and return FAIL as soon as any handler
        returns FAIL.
        """
        failfast = kwargs.get('failfast', False)
        for effect in self.effect_handlers[name][:]:
            if __debug__: log.d('effect %s of %r activated', name, effect.__self__)
            rv = effect(*args)
            if failfast and rv is FAIL:
                if __debug__: log.d('Effect %s was failed by %r', name, effect.__self__)
                return FAIL

    def accumulate_effect(self, name, *args, **kwargs):
        """
        Call all bound handlers for the named effect type, with *args as the handler method's
        arguments. The argument in the last position, args[-1], is the accumulator variable and will
        be modified and returned.

        Failfast works as for self.activate_effect
        """
        failfast = kwargs.get('failfast', False)
        accumulator = args[-1]
        for effect in self.effect_handlers[name][:]:
            if __debug__: log.d('effect %s of %r activated', name, effect.__self__)
            accumulator = effect(*(args[:-1] + (accumulator,)))
            if failfast and accumulator is FAIL:
                return FAIL
        return accumulator
