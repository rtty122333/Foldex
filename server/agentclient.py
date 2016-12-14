# -*- coding: utf-8 -*-

import logging
import requests

log = logging.getLogger(__name__)

class AgentClient:

    def __init__(self, ip, port=9704):
        self.ip = ip
        self.port = port

    def get_storage_enabled(self):
        try:
            r = requests.get('http://{}:{}/usb_storage'.format(self.ip, self.port), timeout=5)
            return r.json()
        except requests.Timeout:
            return {'state': 'error', 'description': 'timeout'}

    def set_storage_enabled(self, enable):
        try:
            d = { 'enable': enable }
            log.info('[{}] set storage enable: {}'.format(self.ip, d))
            r = requests.post('http://{}:{}/usb_storage'.format(self.ip, self.port), json=d, timeout=5)
            return r.json()
        except requests.Timeout:
            return {'state': 'error', 'description': 'timeout'}

    def get_enabled_usb_devices(self):
        try:
            r = requests.get('http://{}:{}/usb_device'.format(self.ip, self.port), timeout=5)
            return r.json()
        except requests.Timeout:
            return {'state': 'error', 'description': 'timeout'}

    def enable_usb_devices(self, id_list):
        try:
            d = { 'update': id_list }
            log.info('[{}] set storage enable: {}'.format(self.ip, d))
            r = requests.post('http://{}:{}/usb_device'.format(self.ip, self.port), json=d, timeout=5)
            return r.json()
        except requests.Timeout:
            return {'state': 'error', 'description': 'timeout'}
