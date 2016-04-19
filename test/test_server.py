#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
import logging.config
import requests
import sys, os.path as path 
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from server import user_monitor, logconf


logging.config.dictConfig(logconf.conf_dict)
log = logging.getLogger('server.test_os')

def test_login(username, password):
    msg = {
        'username': username,
        'password': password
    }
    response = requests.get('http://127.0.0.1:8893/login', data=json.dumps(msg))
    code = response.status_code
    result = response.json()
    log.debug('[{}] {}'.format(code, result))
    return code, result


def test_prepare_vm(vm_id, token):
    msg = {
        'token': token,
        'vm_id': vm_id
    }
    response = requests.get('http://127.0.0.1:8893/conn', data=json.dumps(msg))
    code = response.status_code
    result = response.json()
    log.debug('[{}] {}'.format(code, result))
    return code, result


def test_heartbeat(vm_id, token):
    msg = {
        'token': token,
        'vm_id': vm_id
    }
    response = requests.get('http://127.0.0.1:8893/heartbeat', data=json.dumps(msg))
    code = response.status_code
    result = response.text
    log.debug('heartbeat: [{}] {}'.format(code, result))
    return code


def main():
    code, r = test_login('user1', '123456')
    if code == 200:
        token = r['token']
        vms = r['vms']
        for vm in vms:
            test_prepare_vm(vm, token)
            test_heartbeat(vm, token)


if __name__ == '__main__':
    main()
