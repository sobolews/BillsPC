from __future__ import absolute_import
from bot.bot import Bot, received

class LogBot(Bot):
    """
    Listens to an open showdown websocket connection, and logs activity to file and console.
    """
    def __init__(self, logfile=None, *args, **kwargs):
        super(LogBot, self).__init__(*args, **kwargs)
        self.logfile_path = logfile or ('./logbot.%s.log' % self.username)

    def __enter__(self):
        self.logfile = open(self.logfile_path, 'a')
        return self

    def __exit__(self, *exc_info):
        self.logfile.close()
        self.close_connection()

    def send(self, msg):
        super(LogBot, self).send(msg)
        self.logfile.write('>>> ' + msg + '\n')

    def received_message(self, msgs):
        self.logfile.write(str(msgs) + '\n' + '-'*60)
        print received(str(msgs) + '\n' + '-'*60)
        super(LogBot, self).received_message(msgs)

    def process_message(self, msg):
        if msg.startswith('|request|'):
            msg = '|request|...'

        self.logfile.write(msg + '\n')
        print received(msg)

        if msg.startswith('|challstr|'):
            self.handle_challstr(msg.split('|')[1:])
