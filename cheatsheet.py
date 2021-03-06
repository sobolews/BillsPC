#!/usr/bin/env python
"""
A cheatsheet CLI for use while playing randombattle on Showdown.
Usage:
Type a pokemon, get move/ability/item probabilities, weakness/resistances, and stats.
"""
import cmd
import sys

from showdowndata import pokedex
from misc.multitabulate import multitabulate
from battle.enums import Type
from battle.types import effectiveness


class CheatSheetCli(cmd.Cmd):
    intro = """
    +---------------------------------------+
    |  Pokemon Showdown Cheatsheet MARK II  |
    +---------------------------------------+
    """
    prompt = 'pokemon> '

    def __init__(self, rbstats=None):
        cmd.Cmd.__init__(self)
        if rbstats is None:
            from showdowndata.rbstats import rbstats
        self.rbstats = rbstats
        self.completions = dict([(pokemon, pokemon) for pokemon in self.rbstats.counter])

        self.completions.update(dict([(pokemon.lower(), pokemon)
                                      for pokemon in self.rbstats.counter]))

        self.completions.update(dict([(pokemon.replace(char, ''), self.completions[pokemon])
                                      for pokemon in self.completions
                                      for char in [' ', ',', '.', '-', '. ']
                                      if char in pokemon]))

    def completenames(self, text, *ignore):
        if not text:
            return "Enter a pokemon."
        return sorted(list(set(self.completions[pokemon]
                               for pokemon in self.completions
                               if pokemon.startswith(text))))

    def default(self, line):
        try:
            pokemon = self.completions[line]
            print self.pprobability(pokemon).join(('\n', '\n'))
            print self.pweaknesses(pokemon), '\n'
            print self.pstats(pokemon), '\n'
        except KeyError:
            if line == 'EOF':
                print 'quit'
                sys.exit(0)
            print 'Not found: %s' % line

    def pstats(self, pokemon):
        bs = pokedex[pokemon].base_stats
        return '\n'.join([('{:<5}'*6).format('HP', 'Atk', 'Def', 'Spa', 'Spd', 'Spe'),
                          ('{:<5}'*6).format(bs['max_hp'], bs['atk'], bs['def'],
                                             bs['spa'], bs['spd'], bs['spe'])])

    def pweaknesses(self, pokemon):
        weaknesses = [type_.capitalize() if
                      effectiveness(type_, pokedex[pokemon]) == 2 else
                      self.bu(type_.capitalize()) for type_ in Type.values if
                      effectiveness(type_, pokedex[pokemon]) > 1]
        resistances = [type_.capitalize() if
                       effectiveness(type_, pokedex[pokemon]) == 0.5 else
                       self.bu(type_.capitalize()) for type_ in Type.values if
                       0 < effectiveness(type_, pokedex[pokemon]) < 1]
        immunities = [type_.capitalize() for type_ in Type.values if
                      effectiveness(type_, pokedex[pokemon]) == 0]
        return '\n'.join(['Weaknesses:  ' + ', '.join(weaknesses),
                          'Resistances: ' + ', '.join(resistances),
                          'Immunities:  ' + ', '.join(immunities)])

    def pprobability(self, pokemon):
        tables = []
        for category in ('Moves', 'Item', 'Ability'):
            probs = [(thing, '{:.0%}'.format(prob))
                     for thing, prob in
                     sorted(self.rbstats.probability[pokemon][category.lower()].items(),
                            key=lambda i: -i[1])]
            tables.append([[category, '']] + probs)
        return multitabulate(tables)

    def emptyline(self):
        pass

    def bu(self, string):
        """Return 'string' with bold/underline ANSI terminal escape codes"""
        return string.join(('\033[4m\033[1m', '\033[0m'))


def main(*args):
    try:
        CheatSheetCli().cmdloop()
    except KeyboardInterrupt:
        print 'quit'
        sys.exit(0)

if __name__ == '__main__':
    main()
