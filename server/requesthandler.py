# -*- coding: utf-8 -*-

import logging
import traceback

from . import backend, session


log = logging.getLogger(__name__)

class Handler(object):
    """Request handler class, encapsulates handlers.

    Attributes:
        handlers (dict): an action to handler mapping.
    """

    def __init__(self):
        self.handlers = {}
        self.handlers['POST'] = {
            "login":    self.login,
            "logout":   self.logout,
            "conn":     self.connect_vm,
            "disconn":  self.disconnect_vm,
            "policy":   self.update_policy,
            "heartbeat":self.heartbeat,
            "settings": self.settings
        }
        self.handlers['GET'] = {
            "vdstatus": self.user_status
        }

    def handle(self, request, action, data):
        """Request triage. Calls handler corresponding to the action.

        Args:
            request (obj): the request object.
            action (str): api action (login, conn, etc.).
            data (dict): request data.
        Raises:
            Exception: if under layer handler raises.
        """
        method = request.method
        log.info('request received [{}] action: {}, data: {}'.format(method, action, data))
        try:
            return self.handlers[method].get(action)(data, request)
        except Exception as e:
            log.exception(e)
            errstr = "error processing {} action: {}".format(method, action)
            log.error(errstr)
            return 400, {'err': errstr}

    def login(self, data, request):
        """Authenticate in initcloud and fetch VM info.

        Returns:
            tuple: HTTP response code and messages.
        """
        log.debug('in login handler')
        try:
            res = backend.login(data[u'username'], data[u'password'])
            backend.init_user(res[u'token'], data[u'client_ip'])
            return 200, res
        except session.AuthenticationFailure:
            return 401, {'err': 'invalid username or password'}
        except Exception as e:
            log.exception(e)
            log.error('unidentified error occurred in login handler')
            return 500, {'err':'sth wrong when handle you msg'}

    def logout(self, data, request):
        """(TODO) Unused for now."""
        log.debug("in logout handler")
        return 200, data

    def connect_vm(self, data, request):
        """VM connection request handler."""
        log.debug('in connect_vm handler')
        try:
            backend.request_connect(data[u'token'], data[u'vm_id'], request)
            return -1, None # postpone the response to request_connect()
        except session.VMError as e:
            return 500, {'err': str(e)}

    def disconnect_vm(self, data, request):
        """VM disconnection request handler."""
        log.debug("in disconnect_vm handler")
        res = backend.disconnect(data[u'token'], data[u'vm_id'])
        return 200, res

    def heartbeat(self, data, request):
        """heartbeat handler."""
        log.debug("in heartbeat handler")
        if 'vm_id' in data:
            backend.heartbeat(data[u'token'], data[u'client_ip'], data[u'vm_id'])
        else:
            backend.heartbeat(data[u'token'], data[u'client_ip'])

        return 204, None

    def user_status(self, data, request):
        """User status query handler."""
        log.debug("user info requested")
        return 200, backend.user_status()

    def update_policy(self, data, request):
        """Client USB device policy request handler."""
        log.debug('in policy handler')
        try:
            backend.request_update_device_policy(msg['vm_id'], msg['storage'], msg['devices'])
            return 200, {'status': 'OK'}
        except Exception as e:
            return 500, {'err': str(e)}

    def settings(self, data, request):
        """Global settings query handler. OTP is the only option now."""
        log.debug("in settings handler")
        res = {}
        if 'query' in msg:
            queries = msg['query'].split(',')
            if 'otp' in queries:
                backend.settings_append_otp(res)
            return 200, res

