#!/usr/bin/env python3

""" Example of announcing a service (in this case, a fake HTTP server) """

import logging
import socket
import sys
from time import sleep

from zeroconf import ServiceInfo, Zeroconf

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) > 1:
        assert sys.argv[1:] == ['--debug']
        logging.getLogger('zeroconf').setLevel(logging.DEBUG)

    desc = {'path': '/'}

    info = ServiceInfo("_sstmount._tcp.local.",
                       "ssteq25._sstmount._tcp.local.",
                       socket.inet_aton("127.0.0.1"), 5000, 0, 0,
                       desc, "ssteq25.local.")

    zeroconf = Zeroconf()
    print("Registration of a service, press Ctrl-C to exit...")
    zeroconf.register_service(info)
    try:
        while True:
            sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        print("Unregistering...")
        zeroconf.unregister_service(info)
        zeroconf.close()
