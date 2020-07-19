#!/bin/bash

mkdir -p /ssteq/etc/

mv /etc/wpa_supplicant/wpa_supplicant.conf /ssteq/etc/
ln -s /ssteq/etc/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf

mv /etc/hostapd/hostapd.conf /ssteq/etc/
ln -s /ssteq/etc/hostapd.conf /etc/hostapd/hostapd.conf

mv /etc/network/interfaces.d/defaults /ssteq/etc
ln -s /ssteq/etc/defaults /etc/network/interfaces.d/defaults

mv /etc/hostname /ssteq/etc/
ln -s /ssteq/etc/hostname /etc/hostname

mv /etc/hosts /ssteq/etc/
ln -s /ssteq/etc/hosts /etc/hosts

chown -R root:root /ssteq/etc
chmod -R 755 /ssteq/etc

