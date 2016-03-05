from __future__ import absolute_import
import json
import time
import getpass

import requests
from ws4py.client.threadedclient import WebSocketClient

from bot.battleclient import BattleClient
from misc.bashcolors import sent, received

if __debug__: from _logging import log

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
    def __init__(self, username=None, password=None, *args, **kwargs):
        super(Bot, self).__init__(*args, **kwargs)
        self.username = username or raw_input('Showdown username: ')
        self.password = password or getpass.getpass()
        self.latest_request = None
        self.battleclient = None
        self.battleroom = None
        self.logged_in = False

    def start(self, interactive=True):
        self.logged_in = False
        self.connect()
        if not interactive:
            self.run_forever()
        while not self.logged_in:
            time.sleep(0.1)

    def opened(self):
        print "Connected to %s" % self.url

    def send(self, msg, _=False):
        print sent(msg)
        super(Bot, self).send(msg)

    def received_message(self, msg_block):
        """
        Showdown sometimes sends multiple newline-separated messages in a single websocket message,
        so split them and process each one. 0-1 character messages can be ignored.
        """
        msg_block = str(msg_block)
        print received('\n'.join((msg_block, '-' * 60)))
        msg_block = msg_block.splitlines()

        # If there is no battle room for this message, instantiate one
        room = self.battleroom
        if msg_block[0].startswith('>battle') and (room is None or room != msg_block[0][1:]):
            if msg_block[1] == '|init|battle':
                self.battleroom = msg_block[0][1:]
                self.battleclient = BattleClient(self.username, self.battleroom, self.send)
                self.latest_request = None
            else:
                log.e('Battle message received for an inactive room:\n%s', msg_block)
                return

        # Save the most recent "request object"; use it to build team if client hasn't done so.
        if len(msg_block) > 1 and msg_block[1].startswith('|request|'):
            self.latest_request = json.loads(msg_block[1].split('|')[2])
            if self.battleclient.my_side is None:
                self.battleclient.build_my_side(self.latest_request)
            return

        for msg in msg_block:
            try:
                self.process_message(msg)
            except Exception:
                log.exception('Exception processing msg: %s', msg)
                print 'msg:\n%s' % msg

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
        while msg_type == '':
            msg.remove('')
            msg_type = msg[0]

        if msg_type in self.IGNORE_MSGS or msg_type in self.TODO_MSGS:
            return

        if msg_type in self.BATTLE_MSGS or msg_type.startswith('-'):
            return self.battleclient.handle(msg_type, msg)

        if msg_type == 'challstr':
            return self.handle_challstr(msg)

        log.e('Unhandled msg:\n%s', msg)

    BATTLE_MSGS = {
        'switch', 'turn', 'move', 'request', 'detailschange', 'faint', 'player', 'inactive', 'drag',
        'cant', '-item', '-enditem', '-ability', '-transform', '-start', '-end',
    }

    IGNORE_MSGS = {
        'updateuser', 'queryresponse', 'formats', 'updatesearch', 'title', 'join', 'gen', 'tier',
        'rated', 'rule', 'start', 'init', 'gametype', '-ability', 'variation', '-crit',
        '-supereffective', '-resisted', '-miss', '-immune', '-hint', '-center', '-message',
        '-notarget', '-hitcount', '-nothing', '-waiting', '-combine', 'chat', 'c', 'chatmsg',
        'chatmsg-raw', 'raw', 'html', 'pm', 'askreg', 'inactiveoff', 'join', 'j', 'leave', 'l', 'L',
        'spectator', 'spectatorleave', 'clearpoke', 'poke', 'teampreview', 'swap', 'done', '',
        'error', 'warning', 'gen', 'callback', 'debug', 'unlink', 'updatechallenges', '-fail',
        'users', ':', 'c:', 'expire', 'seed', 'choice', '-endability',
    }

    # TODO: implement (they get ignored for now)
    TODO_MSGS = {
        '-singleturn', '-singlemove', '-activate', '-sidestart', '-sideend', '-fieldstart',
        '-fieldend', '-fieldactivate', '-formechange', '-mega', 'win', 'tie', 'prematureend',
        'detailschange', 'deinit'
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
