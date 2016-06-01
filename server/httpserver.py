# -*- coding: utf-8 -*-

import json
import logging

import logconf
import requesthandler

from twisted.web.resource import Resource


_handler = requesthandler.Handler()


class VDIResource(Resource):

    isLeaf = True

    def render(self, request):
        if request.method == 'GET':
            data = {}
        else:
            datastr = request.content.getvalue()
            data = json.loads(datastr)
        data['client_ip'] = request.getClientIP()
        action = request.postpath[0]

        code, response = _handler.handle(request.method, action, data) 
        request.setResponseCode(code)
        return json.dumps(response)

