# -*- coding: utf-8 -*-

import json
import logging
import time
import threading

from . import session

from collections import defaultdict


log = logging.getLogger(__name__)


class UserMonitor(object):
    """Tracks user connection using heartbeat messages.

    Attributes:
        memo (dict): manages all user records.
        terminated (bool): indicates whether the monitor should stop.
        refersher (obj): working thread, refresh users states regularly.
        timeout (int): timeout (seconds) value after which the user should
            be treated as disconnected if no heartbeat received.
        refresh_interval (int): the interval (seconds) between two status
            updates.
        wsf (obj): WebSocket broadcast server.
    """

    class Record(object):
        """User record, representing a connection.

        Attributes:
            last_update (time): time of last heartbeat arrived.
            online (bool): whether the user is currently online.
            vm (string): VM id, None if not connected.
            vm_ip (string): VM ip, None if not connected.
        """
        def __init__(self):
            self.last_update = time.time()
            self.online = False
            self.vm = None
            self.vm_ip = None

    def __init__(self, wsf, timeout=30, interval=5):
        """Create UserMonitor object.

        Args:
            wsf (obj): WebSocket broadcast server.
            timeout (int): timeout (seconds) value after which the user should
                be treated as disconnected if no heartbeat received.
            interval (int): the interval (seconds) between two status
                updates.
        """
        self.memo = defaultdict(self.Record)
        self.terminated = False
        self.refresher = threading.Thread(target=self.refresh_status)
        self.timeout = timeout
        self.refresh_interval = interval
        self.wsf = wsf

    def __del__(self):
        self.stop()

    def update_connection(self, user, client_ip='nochange', vm=None):
        """Update user info by heartbeat."""
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
        """Generates user info.

        Yields:
            tuple: user status info.
        """
        for username in self.memo:
            user = self.memo[username]
            if user.online:
                yield username, user.vm, user.vm_ip, user.client_ip

    def refresh_status(self):
        """Update user online status.

        If more than timeout value seconds has passed since last
        user update, mark the user as offline, otherwise mark it
        as online. If the status changed, broadcast the message
        to all connected WebSocket clients.
        """
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
        """Broadcast message to all connected WebSocket clients."""
        rec = self.memo[user]
        is_online, vm, vm_ip = rec.online, rec.vm, rec.vm_ip
        log.debug('======================= user {} status changed. [{}][{}]'.format(user, 'ONLINE' if is_online else 'OFFLINE', vm))
        self.wsf.broadcast(json.dumps({ 'action': 'notify', 'user': user, 'online': is_online, 'vm': vm, 'ip_addr': vm_ip}))

    def start(self):
        """Start the refresher thread."""
        self.terminated = False
        self.refresher.start()

    def stop(self):
        """Stop the refresher thread."""
        self.terminated = True
        self.refresher.join()

