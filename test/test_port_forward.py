import port_forward
import time

if __name__ == '__main__':
    try:
        proxy = port_forward.ServerProxy()
        port1 = proxy.add_proxy('192.168.161.14', 3389)
        port2 = proxy.add_proxy('100.100.100.105', 22)
        print "proxy1: ", port1, "proxy2: ",port2
        time.sleep(60)
        proxy.delete_proxy(port1)
    except KeyboardInterrupt:
        print "Server stopped"
        sys.exit(1)

