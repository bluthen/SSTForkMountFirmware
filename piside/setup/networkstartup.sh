#!/bin/sh
/usr/bin/python3 /root/ctrl_dnsmasq.py wlan0 disable
/usr/bin/python3 /root/ctrl_dnsmasq.py check_and_restart
sleep 5
/root/autohotspotcron

