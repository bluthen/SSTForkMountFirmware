#!/usr/bin/env python3

import re
import socket
from time import sleep

import ifaddr
from zeroconf import ServiceInfo, Zeroconf


# avahi-publish-service ssteq25r _sstmount._tcp 5000 "/"


def get_addresses():
    addresses = []
    adapters = ifaddr.get_adapters()
    prog = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    for adapter in adapters:
        iface = adapter.nice_name
        print(iface)
        if iface == 'lo':
            continue
        for ip in adapter.ips:
            address = ip.ip
            if isinstance(address, str) and prog.match(address):
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
