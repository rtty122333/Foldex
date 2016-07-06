# -*- coding: utf-8 -*-

import json
import logging
import requests
import subprocess
import time

from oslo_config import cfg

log = logging.getLogger(__name__)

opt_ec_group = cfg.OptGroup(name='evercloud',
                            title='Evercloud related options')
ec_opts = [
    cfg.StrOpt('host', default='localhost',
               help=('Evercloud api host')),
    cfg.IntOpt('port', default=8081,
               help=('Evercloud api port')),
]

CONF = cfg.CONF
CONF.register_group(opt_ec_group)
CONF.register_opts(ec_opts, opt_ec_group)


class dict2obj(object):
    def __init__(self, dictobj):
        self.__dict__.update(dictobj)


class AuthenticationFailure(RuntimeError):
    """认证异常"""

    def __init__(self, user):
        super(AuthenticationFailure, self).__init__('Authentication failure: {}'.format(user))


class InvalidTokenError(RuntimeError):
    def __init__(self, token):
        super(InvalidTokenError, self).__init__('Invalid token: {}'.format(token))


class VMError(RuntimeError):
    """VM状态异常"""

    def __init__(self, msg):
        super(VMError, self).__init__(msg)


_vm_ips = {}


class Session(object):
    """用户会话类，以用户的身份执行操作。"""

    # 状态轮询间隔
    status_check_interval = 0.5
    # 等待状态超时时间
    status_wait_timeout = 10

    token_map = {}

    @classmethod
    def get(cls, token):
        try:
            session = cls.token_map[token]
            return session
        except KeyError:
            raise InvalidTokenError(token)

    @classmethod
    def register(cls, session):
        cls.token_map[session.token] = session


    def __init__(self, username, password):
        """使用用户名和密码创建会话。

        自动进行身份验证，验证失败时抛出异常。
        """
        self.host = 'http://{}:{}'.format(CONF.evercloud.host, CONF.evercloud.port)
        self.auth_url = '/'.join((self.host, 'login'))
        self.query_url = '/'.join((self.host, 'api', 'instances', 'vdi'))
        self.action_url = '/'.join((self.host, 'api', 'instahces', 'vdi_action'))
        self.client = requests.session()
        self.client.get(self.auth_url, verify = False) 
        csrftoken = self.client.cookies['csrftoken']
        login_data = {
            'username': username,
            'password': password,
            'csrfmiddlewaretoken': csrftoken,
            'next': '/'
        }
        login_return = self.client.post(self.auth_url, data=login_data, headers={ 'Referer': self.auth_url })
        if login_return.status_code == 200:
            self.token = csrftoken
            self.username = username
            Session.register(self)
        else:
            raise AuthenticationFailure(username)

    def get_vms(self):
        """获取用户项目中的所有VM。

        返回每个VM的id，状态和浮动ip。
        """
        instances = self.client.get(self.query_url)
        # (workaround) 登录 api 无论成功与否都返回 200，只能在这里增加判断
        if instances.status_code != 200:
            raise AuthenticationFailure(self.username)
        instances = json.loads(instances.content)
        info = {}
        for vmid in instances:
            vm = dict2obj(instances[vmid])
            info[vm.vm_uuid] = {
                'internal_id': vmid,
                'name':        vm.vm_name,
                'status':      vm.vm_status,
                'public_ip':   vm.vm_public_ip,
                'private_ip':  vm.vm_private_ip,
                'host':        vm.vm_host,
                'policy':      vm.policy_device,
                'vnc_port':    vm.vnc_port,
                'os':          'win'
            }
            _vm_ips[vm.vm_uuid] = vm.vm_public_ip
        return info

    def wait_for_status(self, vm_id, status, timeout):
        """等待指定VM达到需要的状态。

        如果VM处于错误状态或超时则抛出异常。
        status: 可能的值为 ACTIVE, BUILDING, DELETED, ERROR, HARD_REBOOT, PASSWORD,
                PAUSED, REBOOT, REBUILD, RESCUED, RESIZED, REVERT_RESIZE, SHUTOFF,
                SOFT_DELETED, STOPPED, SUSPENDED, UNKNOWN, VERIFY_RESIZE
        timeout: 超时时限，秒
        """
        now = time.time()
        deadline = now + timeout
        while now < deadline:
            vm = self.get_vms()[vm_id]
            if vm['status'] == status:
                break
            if vm['status'] == 'ERROR':
                raise VMError('VM is in error state.')
            time.sleep(self.status_check_interval)
            now = time.time()
        else:
            raise VMError('Action timeout.')

    def start_vm(self, vm_id):
        """启动用户的VM。

        返回时VM已启动，或因错误无法启动，或操作超时。
        后两者抛出VMError异常。
        """
        vm = dict2obj(self.get_vms()[vm_id])
        if vm.status == 'SHUTOFF': # 只在关机状态下执行
            log.info('Starting VM {}'.format(vm_id))
            action = { 'instance': vm.internal_id, 'action': 'power_on' }
            ret = self.client.get(self.action_url, params=action)
            ret = json.loads(ret.content)
            if ret['OPERATION_STATUS'] == 1: # success
                try:
                    self.wait_for_status(vm, 'ACTIVE', self.status_wait_timeout)
                    log.info('VM {} powered on'.format(vm_id))
                except VMError as e:
                    info = {
                        'code': 500,
                        'res': {
                            'err': str(e)
                        }
                    }
                    return info
            else:
                errmsg = 'Failed to start vm {}'.format(vm_id)
                log.warning(errmsg)
                raise VMError(errmsg)

        vm = dict2obj(self.get_vms()[vm_id])
        info = {
            'code': 200,
            'res': {
                vm_id: {
                    'status': 'ACTIVE',
                    'vnc_port': vm.vnc_port,
                    'spice_port': vm.vnc_port + 1
                }
            }
        }
        return info

    def stop_vm(self, vm_id):
        """关闭用户的VM。

        返回时VM已关闭，或因错误无法关闭，或操作超时。
        后两者抛出VMError异常。
        """
        vm = dict2obj(self.get_vms()[vm_id])
        if vm.status == 'ACTIVE': # 只在开机状态下执行
            log.info('Shuting down VM {}'.format(vm_id))
            action = { 'instance': vm.internal_id, 'action': 'power_off' }
            ret = self.client.get(self.action_url, params=action)
            ret = json.loads(ret.content)
            if ret['OPERATION_STATUS'] == 1: # success
                self.wait_for_status(vm, 'SHUTOFF', self.status_wait_timeout)
                log.info('VM {} powered off'.format(vm_id))
            else:
                errmsg = 'Failed to stop vm {}'.format(vm_id)
                log.warning(errmsg)
                raise VMError(errmsg)


def lookup_vm_ip(vm_id):
    return _vm_ips.get(vm_id, None)
