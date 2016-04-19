#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import logging.config
import sys, os.path as path 
from oslo_config import cfg
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from server import session, logconf


logging.config.dictConfig(logconf.conf_dict)
log = logging.getLogger('server.test_os')


def test():
    user = session.Session('user1', '123456')
    admin = session.AdminSession('user1')
    vms = admin.get_vms()
    for id in vms:
        log.debug('{}: {}'.format(id, vms[id]))

        try:
            user.stop_vm(id)
            user.start_vm(id)
        except session.VMError as e:
            log.error(e)


if __name__ == '__main__':
    cfg.CONF(default_config_files=['/etc/foldex/foldex.conf'])
    test()
