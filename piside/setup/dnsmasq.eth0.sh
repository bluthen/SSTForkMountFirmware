#!/bin/sh
/bin/systemctl is-active dnsmasq-eth0.service || /bin/systemctl restart dnsmasq-eth0.service

