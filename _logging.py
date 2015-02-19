"""
Note: log imports and calls in this repo are wrapped in "if __debug__:" guards. Running through
a battle takes approximately twice as long if logging is turned on, so running with `python -O`
provides a significant speed increase.
"""
import logging
import os
import time
from datetime import datetime

LOG_DIR = os.path.expanduser('~/.BillsPC/logs/')
LOG_FILE = os.path.join(LOG_DIR, 'BillsPC-%s.log' % datetime.now().strftime('%Y.%m.%d-%H:%M:%S'))
LOG_FORMAT = "%(asctime)s %(levelname)s %(funcName)s:%(lineno)d: %(message)s"

def _create_logger():
    class MyFormatter(logging.Formatter):
        def formatTime(self, record, datefmt=None):
            ct = self.converter(record.created)
            t = time.strftime("%H:%M:%S", ct)
            return "%s.%03d" % (t, record.msecs)
    formatter = MyFormatter(LOG_FORMAT)

    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    logger = logging.getLogger('BillsPC')
    fh = logging.FileHandler(LOG_FILE)
    fh.setFormatter(formatter)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.setLevel(logging.DEBUG)

    logger.d = logger.debug
    logger.i = logger.info
    logger.w = logger.warn
    logger.e = logger.error
    logger.c = logger.critical
    logger.wtf = logger.error

    return logger

log = _create_logger()

def silence_console():
    log.handlers[1].setLevel(logging.WARNING)

