#!/usr/bin/python3
import sys
import shutil
import subprocess
import tempfile
import os


def check_and_restart():
    """
    Checks if any interface is uncommented if so restarts dnsmasq otherwise stops it
    """
    print("check_and_restart")
    try:
        subprocess.check_call(['/bin/grep', '-q', '^interface=', '/etc/dnsmasq.conf'])
        subprocess.call(['/bin/systemctl', 'restart', 'dnsmasq.service'])
        print("dnsmasq restart")
    except subprocess.CalledProcessError:
        subprocess.call(['/bin/systemctl', 'stop', 'dnsmasq'])
        print("dnsmasq stop")


def check_if_not_started():
    print("check_if_not_started")
    try:
        subprocess.check_call(['/bin/systemctl', 'is-active', 'dnsmasq.service'])
        print('=======================')
    except:
        subprocess.call(['/bin/systemctl', 'start', 'dnsmasq'])


def usage():
    print('Usage: %s [arguments]', (sys.argv[0],))
    print('')
    print('    wlan0|eth0 enable|disable')
    print('    check_and_restart')


def main():
    if len(sys.argv) not in (2, 3):
        usage()
        return
    iface = sys.argv[1]
    if len(sys.argv) == 2 and iface == 'check_and_restart':
        check_and_restart()
    elif len(sys.argv) == 3 and iface in ('wlan0', 'eth0'):
        dnsmasq = """
bogus-priv
bind-interfaces
except-interface=eth0
except-interface=lo
%s
dhcp-range=192.168.45.11,192.168.45.50,255.255.255.0,12h
dhcp-mac=set:client_is_a_pi,B8:27:EB:*:*:*
dhcp-reply-delay=tag:client_is_a_pi,2
"""
        enable = sys.argv[2] == 'enable'
        if enable:
            with open('/etc/dnsmasq_iface.%s' % iface, 'w') as f:
                pass
        else:
            try:
                os.remove('/etc/dnsmasq_iface.%s' % iface)
            except:
                pass

        currently_enabled = []
        with open('/etc/dnsmasq.conf', 'r') as f:
            for line in f:
                line = line.strip()
                findret = line.find('interface=')
                if findret == 0:
                    currently_enabled.append(line.split('=')[1])

        wanted_enabled = []
        for iface2 in ('wlan0', 'eth0'):
            if os.path.isfile('/etc/dnsmasq_iface.%s' % iface2):
                wanted_enabled.append(iface2)

        wanted_enabled = set(wanted_enabled)
        currently_enabled = set(currently_enabled)

        print(wanted_enabled, currently_enabled)

        if wanted_enabled != currently_enabled:
            s = ''
            for iface2 in wanted_enabled:
                s = s + 'interface=' + iface2 + '\n'
            stemp = tempfile.mkstemp(suffix='dnsmasq')
            os.close(stemp[0])
            stemp = [open(stemp[1], 'w'), stemp[1]]
            stemp[0].write(dnsmasq % s)
            stemp[0].close()
            shutil.copyfile(stemp[1], '/etc/dnsmasq.conf')
            os.remove(stemp[1])
            check_and_restart()
        elif wanted_enabled:
            check_if_not_started()
    else:
        usage()


if __name__ == "__main__":
    main()
