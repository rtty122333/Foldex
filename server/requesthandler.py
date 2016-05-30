# -*- coding: utf-8 -*-

import logging
import backend
import session


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

    def handle(self, method, action, msgObj):
        log.debug('[{}] action: {}, msg: {}'.format(method, action, msgObj))
        try:
            return self.handlers[method].get(action)(msgObj)
        except Exception as e:
            log.error(e)
            log.error("unknown {} action: {}".format(method, action))
            return 400, {'err':'unknown {} action'.format(method)}

    def login(self, msgObj):
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
            return 500, {'err':'sth wrong when handle you msg'}

    # 未使用
    def logout(self, msgObj):
        log.debug("in logout handler")
        return 200, msgObj

    def connect_vm(self, msgObj):
        log.debug('in connect_vm handler')
        try:
            res = backend.request_connect(msgObj[u'token'], msgObj[u'vm_id'])
            #vm未开启时需要通知nova开启
            return 200, res
        except session.VMError as e:
            return 500, {'err': e}

    # 未使用
    def disconnect_vm(self, msgObj):
        log.debug("in disconnect_vm handler")
        return 200, msgObj

    def heartbeat(self, msgObj):
        log.debug("in heartbeat handler")
        if 'vm_id' in msgObj:
            backend.heartbeat(msgObj[u'token'], msgObj[u'client_ip'], msgObj[u'vm_id'])
        else:
            backend.heartbeat(msgObj[u'token'], msgObj[u'client_ip'])

        return 204, None

    def user_status(self, msg):
        return 200, backend.user_status()
