# -*- coding: utf-8 -*-

import json
import logging
import time
import threading

from . import session

from collections import defaultdict


log = logging.getLogger(__name__)


class UserMonitor(object):

    class Record(object):
        def __init__(self):
            self.last_update = time.time()
            self.online = False
            self.vm = None
            self.vm_ip = None

    def __init__(self, wsf, timeout=30, interval=5):
        self.memo = defaultdict(self.Record)
        self.terminated = False
        self.refresher = threading.Thread(target=self.refresh_status)
        self.timeout = timeout
        self.refresh_interval = interval
        self.wsf = wsf

    def __del__(self):
        self.stop()

    def update_connection(self, user, client_ip='nochange', vm=None):
        rec = self.memo[user]
        if client_ip != 'nochange':
            rec.client_ip = client_ip
        rec.vm_changed = rec.vm != vm
        if rec.vm_changed and vm:
            rec.vm_ip = session.lookup_vm_ip(vm)
        rec.vm = vm
        rec.online = True
        rec.last_update = time.time()

    def status(self):
        for username in self.memo:
            user = self.memo[username]
            if user.online:
                yield username, user.vm, user.vm_ip, user.client_ip

    def refresh_status(self):
        while not self.terminated:
            now = time.time()
            for user in self.memo:
                rec = self.memo[user]
                online = now - rec.last_update < self.timeout
                if online != rec.online or rec.vm_changed:
                    rec.online = online
                    rec.vm_changed = False
                    if not online:
                        rec.vm = None
                    self.notify(user)
            time.sleep(self.refresh_interval)

    def notify(self, user):
        rec = self.memo[user]
        is_online, vm, vm_ip = rec.online, rec.vm, rec.vm_ip
        log.debug('======================= user {} status changed. [{}][{}]'.format(user, 'ONLINE' if is_online else 'OFFLINE', vm))
        self.wsf.broadcast(json.dumps({ 'action': 'notify', 'user': user, 'online': is_online, 'vm': vm, 'ip_addr': vm_ip}))

    def start(self):
        self.terminated = False
        self.refresher.start()

    def stop(self):
        self.terminated = True
        self.refresher.join()

