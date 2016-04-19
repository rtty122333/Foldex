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
        vms = admin.get_vms()
        info = {
            'vms': vms,
            'token': user.token
        }
        return info
    except session.AuthenticationFailure as e:
        log.error(e)
        raise


def request_connect(token, vm_id):
    try:
        user = session.Session.get(token)
        log.info('User {} attempt to connect to VM {}'.format(user.username, vm_id))
        info = user.start_vm(vm_id)
        return info
    except session.InvalidTokenError as e:
        log.error(e)
        raise
    except VMError as e:
        log.error('User {} attempt to connect to {} but failed: {}'.format(user.username, vm_id, e))
        raise


def start_heartbeat_monitor():
    _monitor.start()


def stop_heartbeat_monitor():
    _monitor.stop()


def heartbeat(token, from_ip, vm_id=None):
    try:
        user = session.Session.get(token)
        _monitor.update_connection(user.username, from_ip, vm_id)
    except session.InvalidTokenError as e:
        log.error(e)
        raise


def init_user(token, from_ip):
    try:
        user = session.Session.get(token)
        _monitor.update_connection(user.username, from_ip)
        _monitor.notify(user.username, True)
    except session.InvalidTokenError as e:
        log.error(e)
        raise
