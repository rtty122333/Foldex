# -*- coding: utf-8 -*-

import logging
import requests

log = logging.getLogger(__name__)

class AgentClient:
    """Control client device policy through agent REST service.

    Attributes:
        ip (str): client ip.
        port (int): agent service port.
    """

    def __init__(self, ip, port=9704):
        self.ip = ip
        self.port = port

    def get_storage_enabled(self):
        """Get whether USB storage is enabled on current client.

        Returns:
            dict: agent api response or error message.
        """
        try:
            log.info('[{}] get storage enable'.format(self.ip))
            r = requests.get('http://{}:{}/usb_storage'.format(self.ip, self.port), timeout=5)
            res = r.json()
        except requests.Timeout:
            res = {'state': 'error', 'description': 'timeout'}
        except requests.ConnectionError:
            res = {'state': 'error', 'description': 'cannot connect to client agent'}
        except Exception:
            res = {'state': 'error', 'description': 'unexpected error'}

        log.info('result: {}'.format(res))
        return res

    def set_storage_enabled(self, enable):
        """Enable/disable USB storage on current client.

        Args:
            enable (bool): True to enable USB storage.
        Returns:
            dict: agent api response or error message.
        """
        try:
            d = { 'enable': enable }
            log.info('[{}] set storage enable: {}'.format(self.ip, d))
            r = requests.post('http://{}:{}/usb_storage'.format(self.ip, self.port), json=d, timeout=5)
            res = r.json()
        except requests.Timeout:
            res = {'state': 'error', 'description': 'timeout'}
        except requests.ConnectionError:
            res = {'state': 'error', 'description': 'cannot connect to client agent'}
        except Exception:
            res = {'state': 'error', 'description': 'unexpected error'}

        log.info('result: {}'.format(res))
        return res

    def get_enabled_usb_devices(self):
        """Get enabled USB device list on current client.

        Returns:
            dict: agent api response or error message.
        """
        try:
            log.info('[{}] get storage enable'.format(self.ip))
            r = requests.get('http://{}:{}/usb_device'.format(self.ip, self.port), timeout=5)
            res = r.json()
        except requests.Timeout:
            res = {'state': 'error', 'description': 'timeout'}
        except requests.ConnectionError:
            res = {'state': 'error', 'description': 'cannot connect to client agent'}
        except Exception:
            res = {'state': 'error', 'description': 'unexpected error'}

        log.info('result: {}'.format(res))
        return res

    def enable_usb_devices(self, id_list):
        """Set enabled USB device list on current client.

        Args:
            id_list (list): devices to be enabled.
        Returns:
            dict: agent api response or error message.
        """
        try:
            d = { 'update': id_list }
            log.info('[{}] set storage enable: {}'.format(self.ip, d))
            r = requests.post('http://{}:{}/usb_device'.format(self.ip, self.port), json=d, timeout=5)
            res = r.json()
        except requests.Timeout:
            res = {'state': 'error', 'description': 'timeout'}
        except requests.ConnectionError:
            res = {'state': 'error', 'description': 'cannot connect to client agent'}
        except Exception:
            res = {'state': 'error', 'description': 'unexpected error'}

        log.info('result: {}'.format(res))
        return res
