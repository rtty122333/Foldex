import sys, os.path as path 
import time
from twisted.internet import threads, reactor
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from server import twist_forward

_proxy = twist_forward.ForwardInst()

if __name__ == '__main__':
    try:
        localport = _proxy.addProxy("192.168.1.222", 3389)
        print(localport)
        reactor.run()
    except KeyboardInterrupt:
        print("Server stopped")
        sys.exit(1)

