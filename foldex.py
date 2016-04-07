# -*- coding: utf-8 -*-

import logging
import logging.config

from oslo_config import cfg
from server import server, logconf 


logging.config.dictConfig(logconf.conf_dict)
log = logging.getLogger('server.main')


def main():
    app = server.Server()
    app.run()


if __name__ == '__main__':
    main()

