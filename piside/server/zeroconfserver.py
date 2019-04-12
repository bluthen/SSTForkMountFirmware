#!/usr/bin/env python3

import logging
import socket
import sys
from time import sleep
import socket
import netifaces

from zeroconf import ServiceInfo, Zeroconf

# avahi-publish-service ssteq25r _sstmount._tcp 5000 "/"


def get_addresses():
    addresses = []
    for iface in netifaces.interfaces():
        if iface == 'lo':
            continue
        naddresses = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in naddresses:
            for a in naddresses[netifaces.AF_INET]:
                address = a['addr']
                if address:
                    addresses.append(address)
    return addresses


def main():
    services = {}
    try:
        while True:
            addresses = get_addresses()
            for address, zc in services.items():
                if address not in addresses:
                    unregister_service(zc[0], zc[1])
                    del services[address]
            for address in addresses:
                if address not in services:
                    print('Registering: ', address)
                    services[address] = register_service(address)
            sleep(1.0)
    finally:
        for address, zc in services.items():
            unregister_service(zc[0], zc[1])


def register_service(address):
    hostname = socket.gethostname()
    desc = {'path': '/'}
    info = ServiceInfo("_sstmount._tcp.local.",
                       hostname + "._sstmount._tcp.local.",
                       socket.inet_aton(address), 5000, 0, 0,
                       desc, hostname + ".local.")

    zeroconf = Zeroconf(interfaces=[address])
    zeroconf.register_service(info, allow_name_change=True)

    return zeroconf, info


def unregister_service(zeroconf, info):
    zeroconf.unregister_service(info)
    zeroconf.close()


if __name__ == '__main__':
    main()
