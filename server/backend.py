# -*- coding: utf-8 -*-

import logging
import session
import user_monitor
import port_forward

from oslo_config import cfg


log = logging.getLogger(__name__)

opt_server_group = cfg.OptGroup(name='server',
                            title='Foldex Server IP Port')

server_opts = [
    cfg.StrOpt('local_ip', default='192.168.1.41',
               help=('Local IP')),
]

CONF = cfg.CONF
CONF.register_group(opt_server_group)
CONF.register_opts(server_opts, opt_server_group)

_monitor = None
_proxy = port_forward.ServerProxy()

_local_ip = CONF.server.local_ip

_connections = {}

def init_ws(wsf):
    global _monitor
    _monitor = user_monitor.UserMonitor(wsf, timeout=30, interval=5)

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
        res = user.start_vm(vm_id)

        vm_info = user.get_vms()[vm_id]
        ip = vm_info['floating_ips'][0]
        log.debug('vm ip: {}'.format(ip))

        localport = _proxy.add_proxy(ip, 3389)

        res[vm_id]['rdp_ip'] = _local_ip
        res[vm_id]['rdp_port'] = localport
        log.debug('local ip: {}, local port: {}'.format(_local_ip, localport))
        _connections[vm_id] = localport
        return res
    except session.InvalidTokenError as e:
        log.error(e)
        raise
    except session.VMError as e:
        log.error('User {} attempt to connect to {} but failed: {}'.format(user.username, vm_id, e))
        raise

def disconnect(token, vm_id):
    log.debug('disconnecting vm: {}'.format(vm_id))
    localport = _connections[vm_id]
    _proxy.delete_proxy(localport)
    return {'status': 'OK'}

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
        _monitor.notify(user.username, is_online=True, vm=None)
    except session.InvalidTokenError as e:
        log.error(e)
        raise


def user_status():
    status = [{'user': t[0], 'vm': t[1]} for t in _monitor.status()]
    return status


def kill_all_proxy():
    _proxy.kill_all()
