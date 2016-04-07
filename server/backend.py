# -*- coding: utf-8 -*-

import logging
import session
import user_monitor


log = logging.getLogger(__name__)

_monitor = user_monitor.UserMonitor(timeout=30, interval=5)

def login(username, password):
    log.info('User {} logging in'.format(username))
    try:
        user = session.Session(username, password)
        admin = session.AdminSession(username)
        info = admin.get_vms()
        info['token'] = user.token
        return info
    except session.AuthenticationFailure as e:
        log.error(e)
        raise


def request_connect(token, vm_id):
    user = session.Session.get(token)
    log.info('User {} attempt to connect to VM {}'.format(user.username, vm_id))
    try:
        user.start_vm(vm_id)
        return { vm_id: 'ACTIVE'}
    except VMError as e:
        log.error('User {} attempt to connect to {} but failed: {}'.format(user.username, vm_id, e))
        raise


def start_heartbeat_monitor():
    _monitor.start()


def stop_heartbeat_monitor():
    _monitor.stop()


def heartbeat(token, from_ip, vm_id=None):
    user = session.Session.get(token)
    _monitor.update_connection(user.username, from_ip, vm_id)
