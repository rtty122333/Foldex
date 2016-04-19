# -*- coding: utf-8 -*-

import logging
import re
import time
import subprocess

import openstack

from oslo_config import cfg
from openstack import connection

log = logging.getLogger(__name__)

opt_os_group = cfg.OptGroup(name='os',
                            title='Openstack related options')
os_opts = [
    cfg.StrOpt('admin_user', default='admin',
               help=('OpenStack admin usser')),
    cfg.StrOpt('admin_pass', default='123456',
               help=('OpenStack admin password')),
]

CONF = cfg.CONF
CONF.register_group(opt_os_group)
CONF.register_opts(os_opts, opt_os_group)


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
    # spice 端口号匹配样式
    spice_port_pattern = re.compile(r'-spice port=(?P<port>\d+),')

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


    def __init__(self, username, password, project=None):
        """使用用户名和密码创建会话。

        默认每个用户拥有独立的同名项目，也可以指定项目名称。
        自动进行身份验证，验证失败时抛出异常。
        """
        self.conn = connection.Connection(auth_url="http://localhost:5000/v3",
                project_name=username if project is None else project,
                username=username,
                password=password,
                user_domain_id='Default',
                project_domain_id='Default')
        try:
            self.token = self.conn.authorize()
            self.username = username
            Session.register(self)
        except openstack.exceptions.HttpException:
            raise AuthenticationFailure(username)

    def get_vms(self):
        """获取用户项目中的所有VM。

        返回每个VM的id，状态和浮动ip。
        """
        def get_floating_ips(networks):
            """从网络信息中提取浮动ip。"""
            result = []
            for name in networks:
                for address in networks[name]:
                    if address['OS-EXT-IPS:type'] == 'floating':
                        result.append(address['addr'])
            return result

        def get_spice_port(vm_id):
            ps = subprocess.Popen(['ps', '-ef'], stdout=subprocess.PIPE)
            qemu = subprocess.Popen(["grep", vm_id], stdin=ps.stdout, stdout=subprocess.PIPE)
            out = qemu.communicate()[0]
            m = self.spice_port_pattern.search(out)
            return m.group('port') if m else ''

        instances = self.conn.compute.servers() # instances 是 generator
        info = {}
        for vm in instances:
            info[vm.id] = {
                u'name': vm.name,
                u'status': vm.status,
                u'floating_ips': get_floating_ips(vm.addresses),
                u'spice_port': get_spice_port(vm.id)
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
            vm = self.conn.compute.get_server(vm_id)
            if vm.status == status:
                break
            if vm.status == 'ERROR':
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
        session = self.conn.session
        vm = self.conn.compute.get_server(vm_id)
        if vm.status == 'SHUTOFF': # 只在关机状态下执行
            log.info('Starting VM {}'.format(vm_id))
            body = {'os-start': ''}
            vm.action(session, body)
            self.wait_for_status(vm, 'ACTIVE', self.status_wait_timeout)
            log.info('VM {} powered on'.format(vm_id))

    def stop_vm(self, vm_id):
        """关闭用户的VM。

        返回时VM已关闭，或因错误无法关闭，或操作超时。
        后两者抛出VMError异常。
        """
        session = self.conn.session
        vm = self.conn.compute.get_server(vm_id)
        if vm.status == 'ACTIVE': # 只在开机状态下执行
            log.info('Shuting down VM {}'.format(vm_id))
            body = {'os-stop': ''}
            vm.action(session, body)
            self.wait_for_status(vm, 'SHUTOFF', self.status_wait_timeout)
            log.info('VM {} powered off'.format(vm_id))


class AdminSession(Session):
    """管理员会话类。

    为了能够获得相关信息，管理员需要在每个用户的项目中都拥有管理员权限。
    """

    def __init__(self, project):
        admin_user = CONF.os.admin_user
        admin_pass = CONF.os.admin_pass
        super(AdminSession, self).__init__(admin_user, admin_pass, project=project)

    def get_vm_host(self, vm_id):
        """获取VM所在服务器的名称和ip。"""
        vm = self.conn.compute.get_server(vm_id)
        host_name = vm['OS-EXT-SRV-ATTR:hypervisor_hostname']
        hypervisors = self.conn.compute.hypervisors()
        host = [hv for hv in hypervisors if hv.hypervisor_hostname == host_name][0]
        host = self.conn.compute.get_hypervisor(host.id)
        return host_name, host.host_ip

    def get_vms(self):
        """获取项目中的VM信息，包含VM所在服务器的名称和ip。"""
        vms = super(AdminSession, self).get_vms()
        for id in vms:
            hostname, host_ip = self.get_vm_host(id)
            vms[id][u'host_name'] = hostname
            vms[id][u'spice_ip'] = host_ip
        return vms

