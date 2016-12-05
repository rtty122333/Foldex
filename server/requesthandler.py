# -*- coding: utf-8 -*-

import logging
import traceback

from . import backend, session


log = logging.getLogger(__name__)

class Handler(object):
    def __init__(self):
        self.handlers = {}
        self.handlers['POST'] = {
            "login":    self.login,
            "logout":   self.logout,
            "conn":     self.connect_vm,
            "disconn":  self.disconnect_vm,
            "heartbeat":self.heartbeat
        }
        self.handlers['GET'] = {
            "vdstatus": self.user_status
        }

    def handle(self, request, action, msgObj):
        method = request.method
        log.debug('[{}] action: {}, msg: {}'.format(method, action, msgObj))
        try:
            return self.handlers[method].get(action)(msgObj, request)
        except Exception as e:
            log.error(e)
            errstr = "error processing {} action: {}".format(method, action)
            log.error(errstr)
            return 400, {'err': errstr}

    def login(self, msgObj, request):
        log.debug('in login handler')
        try:
            # 请求keystone获得身份认证结果
            # 认证通过请求vm信息
            # TODO: 得到vm获取本地策略
            # 返回认证结果+vm信息+本地策略
            # 本地sessions更新接收heartBeat
            res = backend.login(msgObj[u'username'], msgObj[u'password'])
            backend.init_user(res[u'token'], msgObj[u'client_ip'])
            return 200, res
        except session.AuthenticationFailure:
            return 401, {'err': 'invalid username or password'}
        except Exception as e:
            log.error(e)
            log.error('unidentified error occurred in login handler')
            traceback.print_exc()
            return 500, {'err':'sth wrong when handle you msg'}

    # 未使用
    def logout(self, msgObj, request):
        log.debug("in logout handler")
        return 200, msgObj

    def connect_vm(self, msgObj, request):
        log.debug('in connect_vm handler')
        try:
            backend.request_connect(msgObj[u'token'], msgObj[u'vm_id'], request)
            return -1, None # 推迟到 request_connect 函数进行回复
        except session.VMError as e:
            return 500, {'err': str(e)}

    def disconnect_vm(self, msgObj, request):
        log.debug("in disconnect_vm handler")
        res = backend.disconnect(msgObj[u'token'], msgObj[u'vm_id'])
        return 200, res

    def heartbeat(self, msgObj, request):
        log.debug("in heartbeat handler")
        if 'vm_id' in msgObj:
            backend.heartbeat(msgObj[u'token'], msgObj[u'client_ip'], msgObj[u'vm_id'])
        else:
            backend.heartbeat(msgObj[u'token'], msgObj[u'client_ip'])

        return 204, None

    def user_status(self, msg, request):
        return 200, backend.user_status()
