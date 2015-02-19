#!/usr/bin/env python
"""
Entry points for various BillsPC utilities.
"""
import argparse
import os
import sys
os.chdir(os.path.dirname(os.path.realpath(__file__)))

import cheatsheet

CHEATSHEET_HELP = cheatsheet.__doc__.splitlines()[1]
MINE_HELP = ("Generate rbstats.pkl by sampling teams from Pokemon Showdown's randombattle "
             "format. Sampling at least 100000 teams is recommended for good results (this may "
             "take a few minutes).")
RBSTATS_HELP = 'Interactively explore rbstats.pkl'
INTERACTIVE_HELP = ('Run a "MultiMoveTestCase" interactively. This allows you to simulate and '
                    'control both sides of a full battle. Useful for testing log output, manual '
                    'testing of damage calculation, etc.')
LOGBOT_HELP = ("Listen in on an active (client-side) Pokemon Showdown websocket, and save the "
               "traffic to a file. Used for development and debugging of the battle client and "
               "bot. Can be used with a local server or the official sim.")


class BillsParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)

def get_parser():
    parser = BillsParser(description='Issue `%(prog)s COMMAND --help` for help on each command')
    subparsers = parser.add_subparsers()

    cheatsheet_cmd = subparsers.add_parser('cheatsheet', help=CHEATSHEET_HELP)
    cheatsheet_cmd.set_defaults(invoke=cheatsheet.main)

    mine_cmd = subparsers.add_parser('mine', help=MINE_HELP)
    mine_cmd.set_defaults(invoke=mine)
    mine_cmd.add_argument('n_teams', type=int, nargs='?', default=100*1000,
                          help='Number of teams to sample')

    rbstats_cmd = subparsers.add_parser('rbstats', help=RBSTATS_HELP)
    rbstats_cmd.set_defaults(invoke=rbstats_)

    interactive_cmd = subparsers.add_parser('interactive', help=INTERACTIVE_HELP)
    interactive_cmd.set_defaults(invoke=interactive)

    logbot_cmd = subparsers.add_parser('logbot', help=LOGBOT_HELP)
    logbot_cmd.add_argument('-u', '--username', help='Showdown username')
    logbot_cmd.add_argument('-p', '--password', help='Showdown password')
    logbot_cmd.add_argument('-f', '--file', help='Log file to append to')
    logbot_cmd.add_argument('--url', help='Showdown server url',
                            default='ws://sim.smogon.com:8000/showdown/websocket')
    logbot_cmd.set_defaults(invoke=logbot)

    return parser

def rbstats_(args):
    from mining.statistics import RandbatsStatistics
    rbstats = r = RandbatsStatistics.from_pickle()
    import IPython
    IPython.embed()

def interactive(args):
    """
    Example usage: (see tests/multi_move_test_case.py for details)

    >>> self.reset_leads('charizard', 'blastoise', p0_ability='dryskin')
    >>> print self.charizard
    >>> self.charizard
    >>> self.choose_move(self.charizard, movedex['bellydrum'])
    >>> self.choose_move(self.blastoise, movedex['surf'])
    >>> self.run_turn()
    """
    from tests.multi_move_test_case import MultiMoveTestCase
    class InteractiveMultiMoveTestCase(MultiMoveTestCase):
        def runTest(self):
            pass
    t = self = InteractiveMultiMoveTestCase()
    from pokedex.moves import movedex
    from mining import create_pokedex
    pokedex = create_pokedex()
    import pokedex.enums
    # ugly hack to embed the entire public pokedex.enums namespace into the local scope
    locals().update({key: val for key, val in pokedex.enums.__dict__.items()
                     if not key.startswith('_')})
    t.setUp()
    import IPython
    IPython.embed()

def mine(args):
    from mining import collect_team_stats
    if args.n_teams > 1000:
        print 'This may take several minutes...'
    stats = collect_team_stats(args.n_teams)
    stats.to_pickle()

def logbot(args):
    from bot.logbot import LogBot
    try:
        with LogBot(logfile=args.file, username=args.username, password=args.password,
                    url=args.url) as bot:
            bot.start(interactive=False)
    except KeyboardInterrupt:
        print 'done'

if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    args.invoke(args)
