#encoding=utf-8

import json
import logging

from . import backend, httpserver, logconf, wsserver

from oslo_config import cfg
from twisted.internet import reactor
from twisted.web.server import Site
from autobahn.twisted.resource import WebSocketResource
from twisted.web.resource import Resource


log = logging.getLogger(__name__)

# register config items and groups.
opt_server_group = cfg.OptGroup(name='server',
                            title='Foldex Server IP Port')

server_opts = [
    cfg.StrOpt('host', default='127.0.0.1',
               help=('Host IP')),
    cfg.IntOpt('port', default=8893,
               help=('Host Port')),
]

CONF = cfg.CONF
CONF.register_group(opt_server_group)
CONF.register_opts(server_opts, opt_server_group)


class Server(object):
    """HTTP/Websocket server, providing api endpoints."""

    def run(self):
        """Start the server.

        Raises:
            Exception: if the server failed to start.
        """
        cfg.CONF(default_config_files=['/etc/foldex/foldex.conf'])
        host, port = CONF.server.host, CONF.server.port

        try:
            factory = wsserver.BroadcastPreparedServerFactory(u"ws://127.0.0.1:{}".format(port))
            factory.protocol = wsserver.WSServerProtocol
            wsresource = WebSocketResource(factory)

            backend.init_ws(factory)
            backend.start_heartbeat_monitor()

            root = Resource()
            root.putChild('ws', wsresource)
            root.putChild('v1', httpserver.VDIResource())
            site = Site(root)

            reactor.suggestThreadPoolSize(30)
            reactor.listenTCP(port, site)

            log.info("Serving HTTP/WS at port {}".format(port))
            reactor.run()
        except KeyboardInterrupt:
            log.info("Terminating...")
        except Exception as e:
            log.exception(e)
            log.error("Failed to start server")
            raise
        finally:
            backend.stop_heartbeat_monitor()
