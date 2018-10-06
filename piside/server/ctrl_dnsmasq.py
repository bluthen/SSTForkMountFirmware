#!/usr/bin/python3
import sys
import fileinput
import subprocess


def check_and_restart():
    """
    Checks if any interface is uncommented if so restarts dnsmasq otherwise stops it
    """
    try:
        subprocess.check_call(['/bin/grep', '-q', '^interface=', '/etc/dnsmasq.conf'])
        subprocess.call(['/usr/sbin/service', 'dnsmasq', 'restart'])
    except subprocess.CalledProcessError:
        subprocess.call(['/usr/sbin/service', 'dnsmasq', 'stop'])


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
        enable = sys.argv[2] == 'enable'
        for line in fileinput.input('/etc/dnsmasq.conf', inplace=True):
            line = line.rstrip('\n')
            if line.find('interface=%s' % (iface,)) in (0, 1):
                if enable:
                    print('interface=%s' % (iface,))
                else:
                    print('#interface=%s' % (iface,))
            else:
                print(line)
        check_and_restart()
    else:
        usage()


if __name__ == "__main__":
    main()
