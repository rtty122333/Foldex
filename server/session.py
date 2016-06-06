# -*- coding: utf-8 -*-

import logging
import re
import requests
import subprocess
import time

import openstack

from oslo_config import cfg
from openstack import connection

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
        auth_url = 'http://{}:{}/login'.format(CONF.evercloud.host, CONF.evercloud.port)
        self.client = requests.session()
        self.client.get(auth_url, verify = False) 
        csrftoken = client.cookies['csrftoken']
        login_data = {
            'username': username,
            'password': password,
            'csrfmiddlewaretoken': csrftoken,
            'next': '/'
        }
        login_return = client.post(auth_url, data=login_data, headers={ 'Referer' = auth_url })
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
        instances = self.client.get("http://{}:{}/api/instances/vdi/".format(CONF.evercloud.host, CONF.evercloud.port))
        info = {}
        for vmid in instances:
            vm = instances[vmid]
            vm = dict2obj(vm)
            info[vm.vm_uuid] = {
                'internal_id': vmid,
                'name':        vm.name,
                'status':      vm.vm_status,
                'public_ip':   vm.vm_public_ip,
                'private_ip':  vm.vm_private_ip,
                'host':        vm.vm_host,
                'policy':      vm.policy_device
            }
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
        vm = self.get_vms()[vm_id]
        if vm['status'] == 'SHUTOFF': # 只在关机状态下执行
            log.info('Starting VM {}'.format(vm_id))
            # TODO: adapt to evercloud
            body = {'os-start': ''}
            vm.action(session, body)

            self.wait_for_status(vm, 'ACTIVE', self.status_wait_timeout)
            log.info('VM {} powered on'.format(vm_id))

        info = {
            vm_id: {
                'status': 'ACTIVE',
                'vnc_port': 123, # TODO
                'spice_port': 123+1 # TODO
            }
        }
        return info

    def stop_vm(self, vm_id):
        """关闭用户的VM。

        返回时VM已关闭，或因错误无法关闭，或操作超时。
        后两者抛出VMError异常。
        """
        vm = self.get_vms()[vm_id]
        if vm['status'] == 'ACTIVE': # 只在开机状态下执行
            log.info('Shuting down VM {}'.format(vm_id))
            # TODO: adapt to evercloud
            body = {'os-stop': ''}
            vm.action(session, body)

            self.wait_for_status(vm, 'SHUTOFF', self.status_wait_timeout)
            log.info('VM {} powered off'.format(vm_id))

