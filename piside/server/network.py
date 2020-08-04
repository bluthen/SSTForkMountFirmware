import subprocess
import socket
import re
import tempfile
import os
import time

import simulation_helper
import settings


def valid_ip(address):
    # https://stackoverflow.com/questions/11264005/using-a-regex-to-match-ip-addresses-in-python
    try:
        socket.inet_aton(address)
        return True
    except:
        return False


def root_file_open(path):
    stemp = tempfile.mkstemp(suffix='sstneworktmp')
    os.close(stemp[0])
    if settings.is_simulation():
        path = './simulation_files' + path
        subprocess.check_call(['/bin/cp', path, stemp[1]], stdout=subprocess.PIPE)
    else:
        subprocess.check_call(['/usr/bin/sudo', '/bin/cp', path, stemp[1]])
    stemp = [open(stemp[1], 'a+'), stemp[1], path]
    stemp[0].seek(0)
    return stemp


def root_file_close(stemp, mode=755):
    stemp[0].close()
    if settings.is_simulation():
        subprocess.run(['/bin/cp', stemp[1], stemp[2]])
    else:
        subprocess.run(['sudo', 'mount', '-o', 'remount,rw', '/ssteq'])
        subprocess.run(['/usr/bin/sudo', '/bin/cp', stemp[1], stemp[2]])
        subprocess.run(['/usr/bin/sudo', '/bin/chown', 'root', stemp[2]])
        subprocess.run(['/usr/bin/sudo', '/bin/chmod', str(mode), stemp[2]])
        subprocess.run(['sudo', 'mount', '-o', 'remount,ro', '/ssteq'])
    os.remove(stemp[1])


def hostapd_read():
    ret = {'ssid': '', 'wpa2key': '', 'channel': ''}
    stemp = None
    try:
        stemp = root_file_open('/ssteq/etc/hostapd.conf')
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
    stemp = root_file_open('/ssteq/etc/defaults')
    stemp[0].truncate(0)
    defaults = """auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp 

auto eth0:0
iface eth0:0 inet static
address %s
netmask %s

auto wlan0
allow-hotplug wlan0
iface wlan0 inet dhcp
wpa-conf /etc/wpa_supplicant/wpa_supplicant.conf
""" % (ip, netmask)
    stemp[0].write(defaults)
    root_file_close(stemp)
    # time.sleep(4)
    if not settings.is_simulation():
        subprocess.run(['sudo', 'ip', 'addr', 'flush', 'eth0'])
        subprocess.run(['sudo', 'systemctl', 'restart', 'networking.service'])


def read_ethernet_settings():
    stemp = None
    found = False
    ret = {'ip': '', 'netmask': '', 'dhcp_server': False}
    try:
        stemp = root_file_open('/ssteq/etc/defaults')
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
    if not settings.is_simulation():
        if enabled:
            subprocess.run(['sudo', '/usr/bin/python3', '/root/ctrl_dnsmasq.py', 'eth0', 'enable'])
        else:
            subprocess.run(['sudo', '/usr/bin/python3', '/root/ctrl_dnsmasq.py', 'eth0', 'disable'])
        subprocess.run(['sudo', '/usr/bin/killall', 'wpa_supplicant'])
        subprocess.run(['sudo', '/bin/systemctl', 'daemon-reload'])
        subprocess.run(['sudo', '/bin/systemctl', 'restart', 'networking'])
        time.sleep(25)
        subprocess.run(['sudo', '/usr/bin/autohotspot'])


def hostapd_write(ssid, channel, password=None):
    stemp = root_file_open('/ssteq/etc/hostapd.conf')
    stemp[0].truncate(0)
    hostapd_conf = """country_code=US
interface=%s
ssid=%s
hw_mode=g
channel=%d
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
rsn_pairwise=CCMP"""  # Can't have whitespace
    hostapd_security = """wpa=2
wpa_passphrase=%s
wpa_key_mgmt=WPA-PSK"""
    stemp[0].write(hostapd_conf % (settings.settings['network']['wifi_device'], ssid, channel))
    if password:
        stemp[0].write('\n' + hostapd_security % (password,))
    root_file_close(stemp)
    # Make hostname the ssid also
    # TODO: Change /ssteq/etc/hosts
    stemp = root_file_open('/ssteq/etc/hostname')
    stemp[0].truncate(0)
    stemp[0].write(ssid + '\n')
    root_file_close(stemp)
    if not settings.is_simulation():
        subprocess.run(['sudo', '/bin/hostname', ssid])


def wpa_supplicant_read(wpa_file):
    network_start_p = re.compile('\\s*network\\s*=\\s*{\\s*')
    network_end_p = re.compile('\\s*}\\s*')
    networks_raw = []
    strip_networks = []
    network_raw = []
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
    wpa_file.write("""update_config=0
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
""")
    wpa_file.write('\n')
    for network in networks:
        wpa_file.write('network={\n')
        for key, value in network.items():
            wpa_file.write("%s=%s\n" % (key, value))
        wpa_file.write('key_mgmt=WPA-PSK\n')
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
    results = subprocess.run(['/sbin/iwconfig', settings.settings['network']['wifi_device']], stdout=subprocess.PIPE)
    sout = results.stdout.decode().splitlines()
    essid_p = re.compile('.* ESSID:"(.+)".*')
    access_point_p = re.compile('.* Access Point: (\\S+).*')
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


def wifi_client_scan_iw():
    if not settings.is_simulation():
        results = subprocess.run(
            ['sudo', '/sbin/iw', 'dev', settings.settings['network']['wifi_device'], 'scan', 'ap-force'],
            stdout=subprocess.PIPE)
    else:
        results = simulation_helper.iw_scan()
    aps = []
    first = True
    ap = None
    for line in results.stdout.decode().splitlines():
        line = line.strip()
        if line.find('BSS Load:') == -1 and line.find('BSS ') == 0:
            if ap:
                aps.append(ap)
            ap = {'mac': line[4:21], 'flags': '', 'ssid': '', 'freq': ''}
        elif line.find('freq: ') == 0:
            ap['freq'] = line.split(' ')[1]
        elif line.find('signal: ') == 0:
            ap['signal'] = float(line.split(' ')[1])
        elif line.find('SSID: ') == 0:
            ap['ssid'] = line.split(' ')[1]
        elif line.find('* Authentication suites: ') == 0:
            ap['flags'] = line.split(': ')[1]
    if ap:
        aps.append(ap)
    aps = sorted(aps, key=lambda k: k['signal'], reverse=True)
    return aps


def wifi_client_scan():
    # Doesn't work when wpa_suppliment is turned off
    subprocess.run(['sudo', '/sbin/wpa_cli', '-i', settings.settings['network']['wifi_device'], 'scan'])
    results = subprocess.run(
        ['sudo', '/sbin/wpa_cli', '-i', settings.settings['network']['wifi_device'], 'scan_results'],
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
