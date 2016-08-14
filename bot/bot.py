from __future__ import absolute_import
import json
import time
import getpass

import requests
from ws4py.client.threadedclient import WebSocketClient

from bot.battleclient import BattleClient
from misc.bashcolors import sent, received
from _logging import log

LOGIN_SERVER_URL = 'http://play.pokemonshowdown.com/action.php'
SERVER_URL = 'http://localhost:8000'


class Bot(WebSocketClient):
    """
    Encapsulates a user's connection to the Pokemon Showdown server.

    The Bot's responsibilities are:
    - Triage messages from the server and delegate to the appropriate room handler or ignore them
    - Create and delete rooms/handlers as needed
    - Handle 'challstr' messages to complete the login process

    TODO: allow simultaneous rooms? for chatbotting this is necessary, however the AI for battling
    is very CPU intensive; even one battle will pin resources so simultaneous battles is low
    priority.
    """
    def __init__(self, username=None, password=None, accept_challenges=False, make_moves=False,
                 show_calcs=False, *args, **kwargs):
        super(Bot, self).__init__(*args, **kwargs)
        self.username = ((username or raw_input('Showdown username: '))
                         .decode('utf-8').encode('ascii', 'ignore'))
        self.password = password or getpass.getpass()
        self.challenging = None
        self.accept_challenges = accept_challenges
        self.make_moves = make_moves
        self.show_calcs = show_calcs
        self.latest_request = None
        self.battleclient = None
        self.battleroom = None
        self.logged_in = False

    @property
    def battle_in_progress(self):
        return self.battleclient is not None and self.battleclient.win is None

    def start(self, interactive=True):
        self.logged_in = False
        self.connect()
        if not interactive:
            self.run_forever()
        while not self.logged_in:
            time.sleep(0.1)

    def opened(self):
        log.i("Connected to %s" % self.url)

    def send(self, msg, _=False):
        log.i(sent(msg))
        super(Bot, self).send(msg)

    def received_message(self, msg_block):
        """
        Showdown sometimes sends multiple newline-separated messages in a single websocket message,
        so split them and process each one. 0-1 character messages can be ignored.
        """
        msg_block = unicode(msg_block).encode('ascii', 'ignore')
        log.i(received('\n'.join((msg_block, '-' * 60))))
        msg_block = msg_block.splitlines()

        battleroom = self.battleroom
        if msg_block[0].startswith('>battle'):
            if battleroom != msg_block[0][1:]: # Instantiate new battle room
                if msg_block[1] == '|init|battle':
                    self.battleroom = msg_block[0][1:]
                    self.battleclient = BattleClient(self.username, self.battleroom, self.send,
                                                     self.make_moves, self.show_calcs)
                    self.latest_request = None
                    self.challenging = None
                else:
                    log.i('Battle message received for an inactive room:\n%s', msg_block)
                    return
            elif battleroom == msg_block[0][1:] and (msg_block[1].startswith('|expire') or
                                                     msg_block[1].startswith('|deinit')):
                self.battleroom = None
                self.battleclient = None
                self.send('|/leave %s' % battleroom)
                return

        # Save the most recent "request object"; use it to build team if client hasn't done so.
        # Set .request on the battleclient, because it occasionally needs to peek at the request
        # that it will process following this block
        if len(msg_block) > 1 and msg_block[1].startswith('|request|'):
            self.latest_request = self.battleclient.request = json.loads(msg_block[1].split('|')[2])
            if self.battleclient.my_side is None:
                self.battleclient.build_my_side(self.latest_request)
            return

        for msg in msg_block:
            try:
                self.process_message(msg)
            except Exception:
                log.exception('Exception processing msg: %s', msg)

        # Process the request after the next message is sent (the server always sends it one message
        # before I want to use it).
        if self.latest_request is not None and msg_block[0].startswith('>battle'):
            self.battleclient.handle_request(self.latest_request)
            self.latest_request = None

    def process_message(self, msg):
        if msg.startswith('>') or len(msg) < 2:
            return

        msg = msg.split('|')
        msg_type = msg[0]
        if msg_type == '':
            msg.remove('')
            msg_type = msg[0]

        if msg_type in self.IGNORE_MSGS:
            return

        if msg_type in self.BATTLE_MSGS or msg_type.startswith('-'):
            return self.battleclient.handle(msg_type, msg)

        if msg_type in self.BOT_MSGS:
            return getattr(self, 'handle_%s' % msg_type)(msg)

        log.e('Unhandled msg:\n%s', msg)

    BOT_MSGS = {'challstr', 'updatechallenges', 'popup'}

    BATTLE_MSGS = {
        'switch', 'turn', 'move', 'request', 'detailschange', 'faint', 'player', 'inactive', 'drag',
        'cant', '-item', '-enditem', '-ability', '-transform', '-start', '-end', '-activate',
        'callback', '-singleturn', '-singlemove', '-sidestart', '-sideend', '-fieldstart',
        '-fieldend', '-formechange', 'detailschange', '-mega', '-supereffective', '-resisted',
        '-miss', '-immune', '-fail', '-crit', 'win', 'tie', 'prematureend', 'replace'
    }

    IGNORE_MSGS = {
        'updateuser', 'queryresponse', 'formats', 'updatesearch', 'title', 'join', 'gen', 'tier',
        'rated', 'rule', 'start', 'init', 'gametype', 'variation', '-hint', '-center', '-message',
        '-notarget', '-hitcount', '-nothing', '-waiting', '-combine', 'chat', 'c', 'chatmsg',
        'chatmsg-raw', 'raw', 'html', 'pm', 'askreg', 'inactiveoff', 'join', 'j', 'leave', 'l', 'L',
        'spectator', 'spectatorleave', 'clearpoke', 'poke', 'teampreview', 'swap', 'done', '',
        'error', 'warning', 'gen', 'debug', 'unlink', 'users', ':', 'c:', 'expire', 'seed',
        'choice', '-endability', '-fieldactivate', '-primal', 'n'
    }

    def handle_challstr(self, msg):
        url = '%s/action.php' % LOGIN_SERVER_URL
        values = {'act': 'login',
                  'name': self.username,
                  'pass': self.password,
                  'challengekeyid': msg[1],
                  'challenge': msg[2]}

        r = requests.post(url, data=values)
        response = json.loads(r.text[1:])  # for reasons, the JSON response starts with a ']'

        self.send('|/trn %s,0,%s' % (self.username, response['assertion']))
        self.logged_in = True

    def handle_updatechallenges(self, msg):
        """
        |updatechallenges|{"challengesFrom":{"1raichu":"randombattle"},
                           "challengeTo":{"to":"0raichu","format":"randombattle"}}
        """
        challenges = json.loads(msg[1])
        challengeTo, challengesFrom = challenges['challengeTo'], challenges['challengesFrom']
        if challengeTo:
            log.i('Challenging %s to %s', challengeTo['to'], challengeTo['format'])
            self.challenging = challengeTo['to']
        else:
            self.challenging = None

        if challengesFrom and self.accept_challenges and not self.battle_in_progress:
            challenger = challengesFrom.keys()[0]
            self.send('|/utm null')
            self.send('|/accept %s' % challenger)
            log.i('Accepted challenge from %s', challenger)

    def send_challenge(self, opponent, cancel=False):
        if cancel:
            self.cancel_challenge(self.challenging or opponent)
        if not self.challenging:
            self.send('|/challenge %s, randombattle' % opponent)
            self.challenging = opponent

    def cancel_challenge(self, opponent):
        self.send('|/cancelchallenge %s' % opponent)

    def handle_popup(self, msg):
        log.i('Popup: %s', msg[1])


class InteractiveBot(Bot):
    """
    Usage:
    bot = InteractiveBot(url='ws://localhost:8000/showdown/websocket',
                         protocols=['http-only', 'chat'],
                         username='user', password='password')
    For smogon, use 'ws://sim.smogon.com:8000/showdown/websocket'
    """
    def start(self, interactive=True):
        super(InteractiveBot, self).start(interactive=True)
