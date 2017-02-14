# -*- coding: utf-8 -*-

import json
import logging
import requests
import traceback

from . import session, user_monitor, twist_forward, agentclient

from oslo_config import cfg
from twisted.internet import threads, reactor


log = logging.getLogger(__name__)

opt_server_group = cfg.OptGroup(name='server',
                            title='Foldex Server IP Port')

server_opts = [
    cfg.StrOpt('local_ip', default='192.168.1.41',
               help=('Local IP')),
    cfg.BoolOpt('use_proxy', default=True,
               help=('Enable connection proxy')),
]

opt_client_group = cfg.OptGroup(name='client',
                            title='Client settings')

client_opts = [
    cfg.StrOpt('otp', default=False,
               help=('Enable otp')),
]

CONF = cfg.CONF
CONF.register_group(opt_server_group)
CONF.register_opts(server_opts, opt_server_group)
CONF.register_group(opt_client_group)
CONF.register_opts(client_opts, opt_client_group)

cfg.CONF(default_config_files=['/etc/foldex/foldex.conf'])

_monitor = None
_proxy = twist_forward.ForwardInst()

_local_ip = CONF.server.local_ip
_use_proxy = CONF.server.use_proxy

_connections = {}

def init_ws(wsf):
    global _monitor
    _monitor = user_monitor.UserMonitor(wsf, timeout=30, interval=5)

def login(username, password):
    log.info('User {} logging in'.format(username))
    try:
        user = session.Session(username, password)
        vms = user.get_vms()
        info = {
            'vms': vms,
            'token': user.token
        }
        return info
    except session.AuthenticationFailure as e:
        log.error(e)
        raise

def _update_device_policy(client_ip, policy, devices):
    ac = agentclient.AgentClient(client_ip)

    enable = bool(int(policy) & 0x01)
    result = ac.set_storage_enabled(enable)
    log.debug('enable storage: {}, response: {}'.format(enable, result))

    if not devices:
        devs = []
    else:
        devs = map(str.strip, str(devices).split(','))
    result = ac.enable_usb_devices(devs)
    log.debug('enable devices: {}, response: {}'.format(devs, result))
    return result

def _request_connect_cb(msg, user, vm_id, request):
    res = msg['res']
    if 'err' not in res:
        vm_info = user.get_vms()[vm_id]
        ip = vm_info['public_ip']
        log.debug('vm ip: {}'.format(ip))

        if _use_proxy:
            localport = _proxy.addProxy(ip, 3389)
            res[vm_id]['rdp_ip'] = _local_ip
            res[vm_id]['rdp_port'] = localport
            _connections[vm_id] = localport
            log.debug('local ip: {}, local port: {}'.format(_local_ip, localport))
        else:
            res[vm_id]['rdp_ip'] = ip #_local_ip
            res[vm_id]['rdp_port'] = 3389 #localport
        res[vm_id]['policy'] = vm_info['policy']

        # contact client agent
        client_ip = request.getClientIP()
        agentres = _update_device_policy(client_ip, vm_info['policy'], vm_info['device_id'])
        # TODO prevent connection if client agent failed
    else:
        log.error(res['err'])

    request.setResponseCode(msg['code'])
    request.write(json.dumps(res))
    request.finish()

def _err_handler(failure):
    failure.trap(Exception)
    traceback.print_exc()

def request_connect(token, vm_id, request):
    try:
        user = session.Session.get(token)
        log.info('User {} attempt to connect to VM {}'.format(user.username, vm_id))
        d = threads.deferToThread(user.start_vm, vm_id)
        d.addCallback(_request_connect_cb, user, vm_id, request)
        d.addErrback(_err_handler)
    except session.InvalidTokenError as e:
        log.error(e)
        raise
    except session.VMError as e:
        log.error('User {} attempt to connect to {} but failed: {}'.format(user.username, vm_id, e))
        raise
    except IOError as e:
        log.error('Cannot find free port: {}'.format(e))

def disconnect_user(user, vm_id):
    # 如果是前端请求断开连接，此函数会执行两次，
    # 一次是响应前端请求，一次是断开之后响应客户端请求
    log.debug('disconnecting vm: {}'.format(vm_id))
    if _use_proxy:
        localport = _connections[vm_id]
        _proxy.deleteProxy(localport)
    _monitor.update_connection(user, vm=None)
    _monitor.notify(user)
    return {'status': 'OK'}

def disconnect(token, vm_id):
    try:
        user = session.Session.get(token)
        return disconnect_user(user.username, vm_id)
    except session.InvalidTokenError as e:
        log.error(e)
        raise

def request_update_device_policy(vm_id, policy, devices):
    online_client = filter(lambda i: i['vm'] == vm_id, user_status())
    if online_client:
        client_ip = online_client[0]['client_addr']
        _update_device_policy(client_ip, policy, devices)

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
        _monitor.notify(user.username)
    except session.InvalidTokenError as e:
        log.error(e)
        raise


def user_status():
    status = [{'user': t[0], 'vm': t[1], 'ip_addr': t[2], 'client_addr': t[3]} for t in _monitor.status()]
    return status

def settings_append_otp(res):
    res['otp'] = CONF.client.otp
