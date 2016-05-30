# -*- coding: utf-8 -*-

import json
import logging
import time
import threading

from collections import defaultdict


log = logging.getLogger(__name__)


class UserMonitor(object):

    class Record(object):
        def __init__(self):
            self.last_update = time.time()
            self.online = False
            self.vm = None

    def __init__(self, wsf, timeout=30, interval=5):
        self.memo = defaultdict(self.Record)
        self.terminated = False
        self.refresher = threading.Thread(target=self.refresh_status)
        self.timeout = timeout
        self.refresh_interval = interval
        self.wsf = wsf

    def __del__(self):
        self.stop()

    def update_connection(self, user, ip, vm=None):
        rec = self.memo[user]
        rec.ip = ip
        rec.vm_changed = rec.vm != vm
        rec.vm = vm
        rec.online = True
        rec.last_update = time.time()

    def get_status(self, user):
        return self.memo[user]

    def refresh_status(self):
        while not self.terminated:
            now = time.time()
            for user in self.memo:
                rec = self.memo[user]
                online = now - rec.last_update < self.timeout
                if online != rec.online or rec.vm_changed:
                    rec.online = online
                    rec.vm_changed = False
                    self.notify(user, online, rec.vm)
            time.sleep(self.refresh_interval)

    def notify(self, user, is_online, vm):
        log.debug('======================= user {} is now {}'.format(user, 'online' if is_online else 'offline'))
        self.wsf.broadcast(json.dumps({ 'action': 'notify', 'user': user, 'online': is_online, 'vm': vm }))

    def start(self):
        self.terminated = False
        self.refresher.start()

    def stop(self):
        self.terminated = True
        self.refresher.join()

