import logging
import socket
import select
import threading
import time
import sys


log = logging.getLogger(__name__)

buffer_size = 4096
delay = 0.005

class Forward(object):

    def __init__(self):
        self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self, host, port):
        try:
            self.forward.connect((host, port))
            return self.forward
        except Exception, e:
            log.error(e)
            return False

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

class FServer(threading.Thread):
    """
    transport data from one port to another using multi-thread
    """
    def __init__(self, host, port, dest, dport):
        threading.Thread.__init__(self)
        self.thread_stop = False
        self.input_list = []
        self.channel = {}
        self.forward_addr = []
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(300)
        self.forward_addr.append(dest)
        self.forward_addr.append(dport)

    def run(self):
        self.input_list.append(self.server)
        ss = select.select
        while not self.thread_stop:
            time.sleep(delay)
            inputready, __, __ = ss(self.input_list, [], [], delay)
            for self.s in inputready:
                if self.s == self.server:
                    self.on_accept()
                    break
                try:
                    self.data = self.s.recv(buffer_size)
                except socket.error, ex:
                    print "This is the exception", ex
                if len(self.data) == 0:
                    self.on_close()
                    break
                else:
                    self.on_recv(self.s, self.data)

    def on_accept(self):
        forward = Forward().start(self.forward_addr[0], self.forward_addr[1])
        clientsock, clientaddr = self.server.accept()
        if forward:
            log.debug("{} has connected".format(clientaddr))
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
            #for k in self.channel:
            #    print self.channel[k]
        else:
            log.warning("Cannot establish connection with remote server.")
            log.warning("Closing connection with client side: {}".format(clientaddr))
            clientsock.close()

    def on_close(self):
        #print "has disconnected"
        self.input_list.remove(self.s)
        self.input_list.remove(self.channel[self.s])
        out = self.channel[self.s]
        self.s.close()
        self.channel[self.s].close()
        del self.channel[out]
        del self.channel[self.s]
        self.stop()

    def on_recv(self, orisock, data):
        self.channel[orisock].send(data)

    def stop(self):
        self.thread_stop = True

class Singleton(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_inst'):
            cls._inst=super(Singleton, cls).__new__(cls, *args, **kwargs)
        return cls._inst

class ServerProxy(Singleton):
    """
    proxy class to generate port to port communication
    """
    server_list = {}
    def add_proxy(self, dest_ip, dest_port, localaddr=''):
        port = findFreePort()
        server = FServer(localaddr, port, dest_ip, dest_port)
        self.server_list[port] = server
        server.start()
        log.debug('proxy to {}:{} from {}:{}'.format(dest_ip, dest_port, localaddr, port))
        log.debug('connection count: {}'.format(len(self.server_list)))
        return port

    def delete_proxy(self, port):
        if port not in self.server_list:
            return
        self.server_list[port].stop()
        del self.server_list[port]
        log.debug('proxy on {} removed'.format(port))
        log.debug('connection count: {}'.format(len(self.server_list)))

    def kill_all(self):
        for port in self.server_list.keys():
            self.delete_proxy(port)
