import subprocess
import socket
import re
import tempfile
import os
import time

settings = None


def init(lsettings):
    global settings
    settings = lsettings


def valid_ip(address):
    # https://stackoverflow.com/questions/11264005/using-a-regex-to-match-ip-addresses-in-python
    try:
        socket.inet_aton(address)
        return True
    except:
        return False


def root_file_open(path):
    results = subprocess.run(['/usr/bin/sudo', '/bin/cat', path], stdout=subprocess.PIPE)
    stemp = tempfile.mkstemp(suffix='sstneworktmp')
    stemp = [os.fdopen(stemp[0], 'a+'), stemp[1], path]
    stemp[0].write(results.stdout.decode())
    stemp[0].seek(0)
    return stemp


def root_file_close(stemp, mode=755):
    stemp[0].close()
    subprocess.run(['/usr/bin/sudo', '/bin/cp', stemp[1], stemp[2]])
    subprocess.run(['/usr/bin/sudo', '/bin/chown', 'root', stemp[2]])
    subprocess.run(['/usr/bin/sudo', '/bin/chmod', str(mode), stemp[2]])
    os.remove(stemp[1])


def set_autohotspotcron(enabled):
    stemp = root_file_open('/root/autohotspotcron')
    ahc_file = stemp[0]
    ahc_file.truncate(0)
    if enabled:
        ahc_file.write("""#/bin/sh
/usr/bin/autohotspot > /dev/null 2>&1
""")
    else:
        ahc_file.write("""#/bin/sh
        /bin/true > /dev/null 2>&1
""")
    root_file_close(stemp)


def set_network_startup(hostpad_enabled):
    stemp = root_file_open('/root/networkstartup.sh')
    stemp[0].truncate(0)
    if hostpad_enabled:
        stemp[0].write("""#!/bin/sh
/root/ctrl_dnsmasq.py check_and_restart
service hostapd start
        """)
    else:
        stemp[0].write("""#!/bin/sh
        /root/ctrl_dnsmasq.py check_and_restart
                """)
    root_file_close(stemp)


def set_wifi_startup_mode(mode):
    if mode == 'always':
        set_autohotspotcron(False)
        set_network_startup(True)
        subprocess.run(['sudo', '/root/ctrl_dnsmasq.py', 'wlan0', 'enable'])
        subprocess.run(['sudo', 'service', 'hostapd', 'restart'])
    elif mode == 'clientonly':
        set_autohotspotcron(False)
        set_network_startup(False)
        subprocess.run(['sudo', '/root/ctrl_dnsmasq.py', 'wlan0', 'disable'])
    elif mode == 'autoap':
        set_network_startup(False)
        subprocess.run(['sudo', 'service', 'hostapd', 'stop'])
        subprocess.run(['sudo', '/root/ctrl_dnsmasq.py', 'wlan0', 'disable'])
        set_autohotspotcron(True)


def hostapd_read():
    ret = {'ssid': '', 'wpa2key': '', 'channel': ''}
    stemp = None
    try:
        stemp = root_file_open('/etc/hostapd/hostapd.conf')
        for line in stemp[0]:
            line = line.strip()
            if line.find('ssid=') == 0:
                ret['ssid'] = line.split('ssid=')[1]
            if line.find('wpa_passphrase=') == 0:
                ret['wpa2key'] = line.split('wpa_passphrase=')[1]
            if line.find('channel') == 0:
                ret['channel'] = line.split('channel=')[1]
    finally:
        if stemp and stemp[1]:
            stemp[0].close()
            os.remove(stemp[1])
    return ret


def set_ethernet_static(ip, netmask):
    stemp = root_file_open('/etc/network/interfaces.d/defaults')
    stemp[0].truncate(0)
    defaults = """auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp 

auto eth0:0
iface eth0:0 inet static
address %s
netmask %s
""" % (ip, netmask)
    stemp[0].write(defaults)
    root_file_close(stemp)
    # time.sleep(4)
    subprocess.run(['sudo', 'ip', 'addr', 'flush', 'eth0'])
    subprocess.run(['sudo', 'systemctl', 'restart', 'networking.service'])


def read_ethernet_settings():
    stemp = None
    found = False
    ret = {'ip': '', 'netmask': '', 'dhcp_server': False}
    try:
        stemp = root_file_open('/etc/network/interfaces.d/defaults')
        for line in stemp[0]:
            line = line.strip()
            if line.find('iface eth0:0 inet static') == 0:
                found = True
            if found and line.find('address') == 0:
                ret['ip'] = line.split(' ')[1]
            if found and line.find('netmask') == 0:
                ret['netmask'] = line.split(' ')[1]
    finally:
        if stemp and stemp[1]:
            stemp[0].close()
            os.remove(stemp[1])
    try:
        stemp = root_file_open('/etc/dnsmasq.conf')
        for line in stemp[0]:
            line = line.strip()
            if line.find('interface=eth0') == 0:
                ret['dhcp_server'] = True
    finally:
        if stemp and stemp[1]:
            stemp[0].close()
            os.remove(stemp[1])
    return ret


def set_ethernet_dhcp_server(enabled):
    if enabled:
        subprocess.run(['sudo', '/root/ctrl_dnsmasq.py', 'eth0', 'enable'])
    else:
        subprocess.run(['sudo', '/root/ctrl_dnsmasq.py', 'eth0', 'disable'])


def hostapd_write(ssid, channel, password=None):
    stemp = root_file_open('/etc/hostapd/hostapd.conf')
    stemp[0].truncate(0)
    hostapd_conf = """interface=%s
driver=nl80211
ssid=%s
hw_mode=g
channel=%d
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
rsn_pairwise=CCMP
ieee80211n=1          # 802.11n support
ht_capab=[HT40][SHORT-GI-20][DSSS_CCK-40]
wmm_enabled=1         # QoS support
"""
    hostapd_security = """wpa=2
wpa_passphrase=%s
wpa_key_mgmt=WPA-PSK
"""
    stemp[0].write(hostapd_conf % (settings['network']['wifi_device'], ssid, channel))
    if password:
        stemp[0].write('\n' + hostapd_security % (password,))
    root_file_close(stemp)


def wpa_supplicant_read(wpa_file):
    network_start_p = re.compile('\s*network\s*=\s*{\s*')
    network_end_p = re.compile('\s*}\s*')
    networks_raw = []
    strip_networks = []
    start = False
    for line in wpa_file:
        dline = line.strip()
        if network_start_p.match(dline):
            start = True
            network_raw = []
        elif network_end_p.match(dline):
            if len(network_raw) > 0:
                networks_raw.append(network_raw)
            start = False
        elif start and line.strip() != '':
            network_raw.append(dline)
        else:
            strip_networks.append(dline)
    strip_networks = '\n'.join(strip_networks)
    networks = []
    for network_raw in networks_raw:
        network = {}
        for line in network_raw:
            k, v = line.split('=', 2)
            network[k.strip()] = v.strip()
        networks.append(network)
    return {'networks': networks, 'other': strip_networks}


def wpa_supplicant_write(wpa_file, other, networks):
    wpa_file.truncate(0)
    wpa_file.write(other)
    wpa_file.write('\n')
    for network in networks:
        wpa_file.write('network={\n')
        for key, value in network.items():
            wpa_file.write("    %s=%s\n" % (key, value))
        wpa_file.write('}\n')


def wpa_supplicant_find(networks, ssid, mac):
    for network in networks:
        if network['ssid'] == ssid and network['bssid'] == mac:
            return networks.index(network)
    return -1


def wpa_supplicant_remove(networks, ssid, mac):
    for network in networks:
        if network['ssid'] == ssid and network['bssid'] == mac:
            networks.remove(network)
            return True
    return False


def current_wifi_connect():
    results = subprocess.run(['/sbin/iwconfig', settings['network']['wifi_device']], stdout=subprocess.PIPE)
    sout = results.stdout.decode().splitlines()
    essid_p = re.compile('.* ESSID:"(.+)".*')
    access_point_p = re.compile('.* Access Point: (\S+).*')
    ssid = None
    mac = None
    for line in sout:
        m = essid_p.match(line.strip())
        if m:
            ssid = m.group(1)
        m = access_point_p.match(line.strip())
        if m:
            mac = m.group(1).lower()
    return {'ssid': ssid, 'mac': mac}


def wifi_client_scan():
    subprocess.run(['sudo', '/sbin/wpa_cli', '-i', settings['network']['wifi_device'], 'scan'])
    results = subprocess.run(['sudo', '/sbin/wpa_cli', '-i', settings['network']['wifi_device'], 'scan_results'],
                             stdout=subprocess.PIPE)
    aps = []
    first = True
    for line in results.stdout.decode().splitlines():
        if first:
            first = False
            continue
        ap = line.split('\t')
        ap = {'mac': ap[0].lower(), 'freq': ap[1], 'signal': ap[2], 'flags': ap[3], 'ssid': ap[4]}
        aps.append(ap)
    return aps
