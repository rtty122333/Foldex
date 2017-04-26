# -*- coding: utf-8 -*-

import json
import logging

from autobahn.twisted.websocket import WebSocketServerFactory, \
    WebSocketServerProtocol

from . import backend, logconf


log = logging.getLogger(__name__)


class WSServerProtocol(WebSocketServerProtocol):
    """WebSocket event handling."""

    def onConnect(self, request):
        """Registers client on connection."""
        log.debug("Client connecting: {0}".format(request.peer))
        self.factory.register(self)

    def onOpen(self):
        log.debug("WebSocket connection open.")

    def onMessage(self, payload, isBinary):
        """Handles received message."""
        if isBinary:
            log.debug("Binary message received: {0} bytes".format(len(payload)))
            # not expected, should raise
        else:
            msg = payload.decode('utf-8')
            log.debug("Text message received: {0}".format(msg))
            try:
                cmd = json.loads(payload)
            except ValueError:
                log.warning('Message is not valid JSON: {}'.format(msg))
            else:
                # process requests from frontend
                if cmd['action'] == 'disconnect':
                    vm_id = cmd['vm']
                    user = cmd['user']
                    backend.disconnect_user(user, vm_id)

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)

    def onClose(self, wasClean, code, reason):
        log.debug("WebSocket connection closed: {0}".format(reason))


class BroadcastServerFactory(WebSocketServerFactory):

    """Simple broadcast server broadcasting any message it receives to all
    currently connected clients.
    """

    def __init__(self, url):
        WebSocketServerFactory.__init__(self, url)
        self.clients = []

    def register(self, client):
        if client not in self.clients:
            log.info("registered client {}".format(client.peer))
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            log.info("unregistered client {}".format(client.peer))
            self.clients.remove(client)

    def broadcast(self, msg):
        """Broadcast message to all registered clients."""
        log.debug("broadcasting message '{}' ..".format(msg))
        for c in self.clients:
            c.sendMessage(msg.encode('utf8'))
            log.info("message sent to {}".format(c.peer))


class BroadcastPreparedServerFactory(BroadcastServerFactory):

    """Functionally same as above, but optimized broadcast using
    prepareMessage and sendPreparedMessage.
    """

    def broadcast(self, msg):
        log.debug("broadcasting prepared message '{}' ..".format(msg))
        preparedMsg = self.prepareMessage(msg)
        for c in self.clients:
            c.sendPreparedMessage(preparedMsg)
            log.info("prepared message sent to {}".format(c.peer))

