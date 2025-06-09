import re
import subprocess
import threading
import time
import traceback

from vmc_simulator import cb_sim


class VirtualMotorController():
    def __init__(self):
        self.__process_socat = None
        self.__thread_cb_sim = None
        self.port = None
        self.__ports = []
        self.__start_socat()
        self.__start_simulator(self.__ports[1])

    def __start_socat(self):
        self.__process_socat = subprocess.Popen(
            ['/usr/bin/socat', '-d', '-d', 'pty,raw,echo=0', 'pty,raw,echo=0'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        ports = []
        try:
            while True:
                output = self.__process_socat.stderr.readline()
                if not output:  # Break loop if no more output
                    break

                matches = re.findall(r'PTY is (\S+)', output)
                ports.extend(matches)
                if len(ports) >= 2:
                    break
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("Process interrupted by user.")

        if len(ports) < 2:
            raise Exception("socat did not return two virtual ports.")
        self.__ports = ports
        print('SOCAT Ports: ', self.__ports)
        self.port = ports[0]

    def __start_simulator(self, port):
        self.__thread_cb_sim = threading.Thread(target=cb_sim.main, args=(self.__ports[1],))
        self.__thread_cb_sim.start()

    def stop(self):
        self.__process_socat.terminate()
        self.__thread_cb_sim.terminate()
        self.__thread_cb_sim.join()


def main():
    try:
        vmc = VirtualMotorController()
        port1 = vmc.port
        print(f"Virtual Port 1: {port1}")
        time.sleep(5)
        vmc.stop()
    except Exception as e:
        traceback.print_exception(e)


if __name__ == '__main__':
    main()
