#encoding=utf-8

import logging
import backend
import session


log = logging.getLogger(__name__)


class Handler(object):
    def __init__(self):
        self.processFuncs={
            "login":    self.login,
            "logout":   self.logout,
            "conn":     self.connect_vm,
            "disconn":  self.disconnect_vm,
            "heartbeat":self.heartbeat
        }

    def process_msg(self,action,msgObj,cb):
        log.debug('action: {}, msg: {}'.format(action, msgObj))
        try:
            return self.processFuncs.get(action)(msgObj,cb)
        except Exception as e:
            log.error(e)
            log.error("unknown action: {}".format(action))
            return cb(400, {'err':'unknown action'})

    def login(self,msgObj,cb):
        log.debug('in login handler')
        try:
            res = backend.login(msgObj[u'username'], msgObj[u'password'])
            #请求keystone获得身份认证结果
            #认证通过请求vm信息
            #得到vm获取本地策略
            #返回认证结果+vm信息+本地策略
            #本地sessions更新接收heartBeat
            return cb(200, res)
        except session.AuthenticationFailure:
            return cb(401, {'err': 'invalid username or password'})
        except Exception as e:
            log.error(e)
            log.error('unidentified error occurred in login handler')
            return cb(500, {'err':'sth wrong when handle you msg'})
        

    def logout(self,msgObj,cb):
        log.debug("in logout handler")
        cb(msgObj)

    def connect_vm(self,msgObj,cb):
        log.debug('in connect_vm handler')
        try:
            res = backend.request_connect(msgObj[u'token'], msgObj[u'vm_id'])
            #vm未开启时需要通知nova开启
            cb(res)
        except session.VMError as e:
            cb(500, {'err': e})

    def disconnect_vm(self,msgObj,cb):
        log.debug("in disconnect_vm handler")
        #vm未开启时需要通知nova开启
        cb(msgObj)

    def heartbeat(self,msgObj,cb):
        log.debug("in heartbeat handler")
        backend.heartbeat(msgObj[u'token'], msgObj[u'ip'], msgObj[u'vm_id'])
        cb(204, None)


    def test(self):
        print "test"
