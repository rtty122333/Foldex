#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import logging.config
import random
import time
import sys, os.path as path 
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from server import user_monitor, logconf


logging.config.dictConfig(logconf.conf_dict)
log = logging.getLogger('server.test_os')

def test():
    umt = user_monitor.UserMonitor()
    umt.start()
    for i in range(3):
        for n in range(5):
            user = 'user-{}'.format(n)
            ip = 'ip-{}'.format(n)
            vm = 'vm-{}'.format(n)
            umt.update_connection(user, ip, vm)
            log.debug('-- [heartbeat] --> {} {} {}'.format(user, ip, vm))
            pause = random.randint(3, 10)
            time.sleep(pause)
    umt.stop()


if __name__ == '__main__':
    test()
