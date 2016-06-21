# -*- coding: utf-8 -*-

import json
import logging

from . import logconf, requesthandler

from twisted.web import server, resource


log = logging.getLogger(__name__)
_handler = requesthandler.Handler()


class VDIResource(resource.Resource):

    isLeaf = True

    def render(self, request):
        if request.method == 'GET':
            data = {}
        else:
            datastr = request.content.getvalue()
            data = json.loads(datastr)
        data['client_ip'] = request.getClientIP()
        action = request.postpath[0]

        code, response = _handler.handle(request, action, data) 
        if code == -1: # Deferred
            return server.NOT_DONE_YET
        else:
            request.setResponseCode(code)
            return json.dumps(response)

