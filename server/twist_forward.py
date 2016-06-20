# -*- coding: utf-8 -*-

import logging
import socket
from portforward import ProxyFactory
from twisted.internet.protocol import Protocol,Factory
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint


log = logging.getLogger(__name__)


def findFreePort():
    """
    get a random avalible port
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        addr, port = s.getsockname()
        s.close()
    except socket.error as msg:
        log.error(msg)
        s.close()
    else:
        return port

class Singleton(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_inst'):
            cls._inst=super(Singleton, cls).__new__(cls, *args, **kwargs)
        return cls._inst

class Proxy():

    def __init__(self, dest_ip, dest_port, local_ip=''):
        self.tmpport = findFreePort()
        if self.tmpport != None:
            self.new_proxy = ProxyFactory(dest_ip, dest_port)
            self.endpoint = TCP4ServerEndpoint(reactor, self.tmpport)
            self.endpoint.listen(self.new_proxy)
        else:
            raise IOError,("Cannot find free port")

    def stop(self):
        self.new_proxy.doStop()

    def getport(self):
        return self.tmpport

class ForwardInst(Singleton):

    def __init__(self):
        self.forwardlist = {}

    def addProxy(self, dest_ip, dest_port, local_ip=''):
        self.proxyinst = Proxy(dest_ip, dest_port, local_ip)
        self.tmpport = self.proxyinst.getport()
        self.forwardlist[self.tmpport] = self.proxyinst
        log.debug('proxy to {}:{} from {}:{}'.format(dest_ip, dest_port, local_ip, self.tmpport))
        log.debug('connection count: {}'.format(len(self.forwardlist)))
        return self.tmpport

    def deleteProxy(self, localport):
        proxy = self.forwardlist.pop(localport, None)
        if proxy:
            proxy.stop()
            log.debug('proxy on {} removed'.format(localport))
            log.debug('connection count: {}'.format(len(self.forwardlist)))
        else:
            # 可能在同一个 localport 上被调用多次，不作处理
            pass
        
'''
test demo:
class StartForward(Protocol):

    def __init__(self, ports):
        self.ports = ports
        self.localinst = ForwardInst()
    def connectionMade(self):
        self.tmpport = self.localinst.addProxy('100.100.100.105',22)
        self.transport.write("on port %s " %self.tmpport)
        self.ports[self.tmpport] = self

class ForwardFactory(Factory):

    def __init__(self):
        self.ports = {}

    def buildProtocol(self, addr):
        return StartForward(self.ports)

reactor.listenTCP(8123, ForwardFactory())
reactor.run()
'''
