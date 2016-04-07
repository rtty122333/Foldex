#encoding=utf-8

import json
import logging
import BaseHTTPServer
import backend
import logconf
import serverRequestHandler

from oslo_config import cfg


log = logging.getLogger(__name__)

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


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    handler = serverRequestHandler.Handler()

    def do_GET( self ):
        log.debug("[GET request received]")
        datas = self.rfile.read(int(self.headers['content-length']))
        # print datas
        # print self.client_address
        # print self.path
        # print self.command
        self.handler.process_msg(self.path[1:],json.loads(datas),self.sendResult)


    def do_POST( self ):
        log.debug("[POST request received]")
        datas = self.rfile.read(int(self.headers['content-length']))
        self.handler.process_msg(self.path[1:],json.loads(datas),self.sendResult)

    def sendResult(self, code, msg):
        log.debug('result:',msg)
        self.send_response(code)
        self.send_header("Content-type", "text/html;charset=utf-8" )
        # f = open('C:/workspaces/workspace_python/client/client.py','r')
        # ct = f.read()
        msg=json.dumps(msg)
        self.send_header('Content-length', str(len(msg)))
        self.end_headers()
        self.wfile.write( msg )


class Server(object):
    def run(self):
        cfg.CONF(default_config_files=['/etc/foldex/foldex.conf'])
        host, port = CONF.server.host, CONF.server.port

        try:
            backend.start_heartbeat_monitor()
            s = BaseHTTPServer.HTTPServer((host, port), RequestHandler)
            log.debug("Serving at port {}".format(port))
            s.serve_forever()
        except KeyboardInterrupt:
            log.info("Terminating...")
        except Exception as e:
            log.debug(e)
            log.error("Failed to start server")
        finally:
            backend.stop_heartbeat_monitor()
