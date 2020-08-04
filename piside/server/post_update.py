import subprocess
import os
import tempfile


def boot_file_open(path):
    stemp = tempfile.mkstemp(suffix='sstneworktmp')
    os.close(stemp[0])
    subprocess.check_call(['/usr/bin/sudo', '/bin/cp', path, stemp[1]])
    stemp = [open(stemp[1], 'a+'), stemp[1], path]
    stemp[0].seek(0)
    return stemp


def boot_file_close(stemp, mode=755):
    stemp[0].close()
    subprocess.run(['sudo', 'mount', '-o', 'remount,rw', '/boot'])
    subprocess.run(['/usr/bin/sudo', '/bin/cp', stemp[1], stemp[2]])
    subprocess.run(['/usr/bin/sudo', '/bin/chown', 'root', stemp[2]])
    subprocess.run(['/usr/bin/sudo', '/bin/chmod', str(mode), stemp[2]])
    subprocess.run(['sudo', 'mount', '-o', 'remount,ro', '/boot'])
    os.remove(stemp[1])


def main():
    ntpstat = subprocess.run(['/bin/grep', 'net.ifnames=0', '/boot/cmdline.txt'])
    if ntpstat.returncode == 0:
        return
    else:
        stemp = boot_file_open('/boot/cmdline.txt')
        r = stemp[0].read().strip()
        r += ' net.ifnames=0\n'
        stemp[0].truncate(0)
        stemp[0].write(r)
        boot_file_close(stemp)


if __name__ == '__main__':
    main()
