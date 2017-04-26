# -*- coding: utf-8 -*-

import json
import logging
import requests
import subprocess
import time

from oslo_config import cfg

log = logging.getLogger(__name__)

# register config items and groups.
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
    """A class which converts a dict to an object (its instance)."""
    def __init__(self, dictobj):
        self.__dict__.update(dictobj)


class AuthenticationFailure(RuntimeError):
    def __init__(self, user):
        super(AuthenticationFailure, self).__init__('Authentication failure: {}'.format(user))


class InvalidTokenError(RuntimeError):
    def __init__(self, token):
        super(InvalidTokenError, self).__init__('Invalid token: {}'.format(token))


class VMError(RuntimeError):
    def __init__(self, msg):
        super(VMError, self).__init__(msg)


_vm_ips = {} # cache VM - ip relations for later lookup


class Session(object):
    """User session class, performs actions on behalf
    of the user.

    Attributes:
        host (str): initcloud host address.
        auth_url (str): initcloud login api url.
        query_url (str): initcloud VM query url.
        action_url (str): initcloud VM action url.
        client (obj): request sender object.
    """

    # VM status polling interval
    status_check_interval = 0.5
    # VM start waiting timeout
    status_wait_timeout = 10
    # Mapping of tokens and users
    token_map = {}

    @classmethod
    def get(cls, token):
        """Fetch a user session by its token.

        Args:
            token (str): session token.
        Raises:
            InvalidTokenError: if the token is not registered.
        """
        try:
            session = cls.token_map[token]
            return session
        except KeyError:
            raise InvalidTokenError(token)

    @classmethod
    def register(cls, session):
        """Register a user session with its token."""
        cls.token_map[session.token] = session


    def __init__(self, username, password):
        """Creates a session for user.

        Sends user authentication request to initcloud.

        Raises:
            AuthenticationFailure: if initcloud responds code other than 200.
        """
        self.host = 'http://{}:{}'.format(CONF.evercloud.host, CONF.evercloud.port)
        self.auth_url = '/'.join((self.host, 'login'))
        self.query_url = '/'.join((self.host, 'api', 'instances', 'vdi'))
        self.action_url = '/'.join((self.host, 'api', 'instances', 'vdi_action'))
        self.client = requests.session()
        self.client.get(self.auth_url, verify = False)
        csrftoken = self.client.cookies['csrftoken']
        login_data = {
            'username': username,
            'type': 'vdi_client', # login type (default=web)
            'password': password,
            'csrfmiddlewaretoken': csrftoken,
            'next': '/'
        }
        log.info("sending request to initcloud: [POST] {}, {}".format(self.auth_url, login_data))
        login_return = self.client.post(self.auth_url, data=login_data, headers={ 'Referer': self.auth_url })
        if login_return.status_code == 200:
            self.token = csrftoken
            self.username = username
            Session.register(self)
        else:
            raise AuthenticationFailure(username)

    def get_vms(self):
        """Get info of all VMs assigned to the user.

        Returns:
            dict: mapping of VM uuid and VM info.
        """

        log.info("sending request to initcloud: [GET] {}".format(self.query_url))
        instances = self.client.get(self.query_url)
        print(instances.content)
        # (workaround) initcloud login api always returns 200, has to
        # confirm if login succeeded here.
        if instances.status_code != 200:
            raise AuthenticationFailure(self.username)
        instances = json.loads(instances.content)
        info = {}
        for vmdict in instances['vminfo']:
            vm = dict2obj(vmdict)
            info[vm.vm_uuid] = {
                'internal_id': vm.vm_internalid,
                'name':        vm.vm_name,
                'status':      vm.vm_status,
                'public_ip':   vm.vm_public_ip,
                #'private_ip':  vm.vm_private_ip,
                #'host':        vm.vm_serverip,
                'policy':      vm.policy_device,
                'vnc_port':    vm.vnc_port,
                'device_id':   vm.device_id,
                'os':          'win'
            }
            _vm_ips[vm.vm_uuid] = vm.vm_public_ip
        return info

    def wait_for_status(self, vm_id, status, timeout):
        """Wait for the VM to reach the wanted state.

        Args:
            status (str): all possible values are ACTIVE, BUILDING, DELETED, ERROR, HARD_REBOOT, PASSWORD,
                PAUSED, REBOOT, REBUILD, RESCUED, RESIZED, REVERT_RESIZE, SHUTOFF,
                SOFT_DELETED, STOPPED, SUSPENDED, UNKNOWN, VERIFY_RESIZE
            timeout (int): wait for at most 'timeout' seconds.

        Raises:
            VMError: if the VM is in ERROR state or timed out.
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
        """Power the VM on.

        When the function returns, either the VM is already powered on
        or an error occurred.

        Raises:
            VMError: if an initcloud or openstack error occurred.

        Returns:
            dict: HTTP response code and messages.
        """
        vm = dict2obj(self.get_vms()[vm_id])
        if vm.status == 'SHUTOFF': # 只在关机状态下执行
            log.info('Starting VM {}'.format(vm_id))
            action = { 'instance': vm.internal_id, 'action': 'power_on' }
            log.info("sending request to initcloud: [GET] {}, {}".format(self.action_url, action))
            ret = self.client.get(self.action_url, params=action)
            ret = json.loads(ret.content)
            if ret.get('success', True) is False:
                info = {
                    'code': 500,
                    'res': {
                        'err': ret['msg']
                    }
                }
                return info
            if ret['OPERATION_STATUS'] == 1: # success
                try:
                    self.wait_for_status(vm_id, 'ACTIVE', self.status_wait_timeout)
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
        """Power the VM off.

        When the function returns, either the VM is already powered off,
        or an error occurred, or timed out.

        Raises:
            VMError: if an initcloud or openstack error occurred.
        """
        vm = dict2obj(self.get_vms()[vm_id])
        if vm.status == 'ACTIVE': # 只在开机状态下执行
            log.info('Shuting down VM {}'.format(vm_id))
            action = { 'instance': vm.internal_id, 'action': 'power_off' }
            log.info("sending request to initcloud: [GET] {}, {}".format(self.action_url, action))
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
    """Get VM public ip by its id."""
    return _vm_ips.get(vm_id, None)
