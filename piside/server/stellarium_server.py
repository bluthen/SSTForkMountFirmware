# A python server for the stellarium planetarium program
# it implements the stellarium Telescope Control plugin protocol.
# Based on pyindi stellarium
# https://sourceforge.net/p/pyindi-client/code/HEAD/tree/trunk/pip/pyindi-client/examples/pyindi-stellarium.py

import logging
import time
import calendar
import math
import traceback
import socket
import select
import control

from astropy.coordinates import SkyCoord
import astropy.units as u


gotoQueue = []

stelport = 10001
stelSocket = None
# current stellarium clients
stelClients = {}

killed = False


def to_be(n, size):
    b = bytearray(size)
    i = size - 1
    while i >= 0:
        b[i] = n % 256
        n = n >> 8
        i -= 1
    return b


def from_be(b):
    n = 0
    for i in range(len(b)):
        n = (n << 8) + b[i]
    return n


def to_le(n, size):
    b = bytearray(size)
    i = 0
    while i < size:
        b[i] = n % 256
        n = n >> 8
        i += 1
    return b


def from_le(b):
    n = 0
    for i in range(len(b) - 1, -1, -1):
        n = (n << 8) + b[i]
    return n


# Simple class to keep stellarium socket connections
class StelClient:
    def __init__(self, sock, clientaddress):
        self.socket = sock
        self.clientaddress = clientaddress
        self.writebuf = bytearray(120)
        self.readbuf = bytearray(120)
        self.recv = 0
        self.msgq = []
        self.tosend = 0

    def has_to_write(self):
        return self.tosend > 0

    def perform_read(self):
        # logging.info('Socket '+str(self.socket.fileno()) + ' has to read')
        buf = bytearray(120 - self.recv)
        nrecv = self.socket.recv_into(buf, 120 - self.recv)
        # logging.info('Socket '+str(self.socket.fileno()) + 'read: '+str(buf))
        if nrecv <= 0:
            logging.info('Client ' + str(self.socket.fileno()) + ' is away')
            self.disconnect()
            stelClients.pop(self.socket)
            return
        self.readbuf[self.recv:self.recv + nrecv] = buf
        self.recv += nrecv
        last = self.datareceived()
        if last > 0:
            self.readbuf = self.readbuf[last:]
            self.recv -= last

    def datareceived(self):
        global gotoQueue
        p = 0
        while p < self.recv - 2:
            psize = from_le(self.readbuf[p:p + 2])
            if psize > len(self.readbuf) - p:
                break
            ptype = from_le(self.readbuf[p + 2:p + 4])
            if ptype == 0:
                micros = from_le(self.readbuf[p + 4:p + 12])
                if abs((micros / 1000000.0) - int(time.time())) > 60.0:
                    logging.warning(
                        'Client ' + str(self.socket.fileno()) + ' clock differs for more than one minute: ' + str(
                            int(micros / 1000000.0)) + '/' + str(int(time.time())))
                targetraint = from_le(self.readbuf[p + 12:p + 16])
                targetdecint = from_le(self.readbuf[p + 16:p + 20])
                if targetdecint > (4294967296 / 2):
                    targetdecint = - (4294967296 - targetdecint)
                targetra = (targetraint * 24.0) / 4294967296.0
                targetdec = (targetdecint * 360.0) / 4294967296.0
                logging.info('Queuing goto (ra, dec)=(' + str(targetra) + ', ' + str(targetdec) + ')')
                gotoQueue.append((targetra, targetdec))
                p += psize
            else:
                p += psize
        return p

    def perform_write(self):
        global stelClients
        # logging.info('Socket '+str(self.socket.fileno()) + ' will write')
        sent = self.socket.send(self.writebuf[0:self.tosend])
        if sent <= 0:
            logging.info('Client ' + str(self.socket.fileno()) + ' is away')
            self.disconnect()
            stelClients.pop(self.socket)
            return
        self.writebuf = self.writebuf[sent:]
        self.tosend -= sent
        if self.tosend == 0:
            if len(self.msgq) > 0:
                self.writebuf[0:len(self.msgq[0])] = self.msgq[0]
                self.tosend = len(self.msgq[0])
                self.msgq = self.msgq[1:]

    def send_msg(self, msg):
        if self.tosend == 0:
            self.writebuf[0:len(msg)] = msg
            self.tosend = len(msg)
        else:
            self.msgq.append(msg)

    def send_eq_coords(self, utc, rajnow, decjnow, status):
        msg = bytearray(24)
        msg[0:2] = to_le(24, 2)
        msg[2:4] = to_le(0, 2)
        if utc != '':
            try:
                tstamp = calendar.timegm(time.strptime(utc, '%Y-%m-%dT%H:%M:%S'))
            except:
                tstamp = 0
        else:
            # Simulator does not send its UTC time, and timestamp are emptied somewhere
            tstamp = int(time.time())
        msg[4:12] = to_le(tstamp, 8)
        msg[12:16] = to_le(int(math.floor(rajnow * (4294967296.0 / 24.0))), 4)
        msg[16:20] = to_le(int(math.floor(decjnow * (4294967296.0 / 360.0))), 4)
        msg[20:24] = to_le(status, 4)
        self.send_msg(msg)

    def disconnect(self):
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except:
            traceback.print_exc()


def terminate():
    global killed
    killed = True


# how to get back this signal which is translated in a python exception ?
# signal.signal(signal.SIGKILL, terminate)
# signal.signal(signal.SIGHUP, terminate)
# signal.signal(signal.SIGQUIT, terminate)


# logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

# Create an instance of the IndiClient class and initialize its host/port members

# Whereas connection to the indiserver will be handled by the C++ thread and the
# above callbacks, connection from the stellarium client programs will be managed
# in the main python thread: we use the usual select method with non-blocking sockets,
# listening on the stellarium port (10001) and using buffered reads/writes on the
# connected stellarium client sockets.
def run():
    global gotoQueue, stelSocket, stelClients
    stelSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    stelSocket.bind(('', stelport))
    stelSocket.listen(5)
    stelSocket.setblocking(0)
    stelSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    status = 0
    try:
        while not killed:
            # try to reconnect indi server if server restarted
            for s in stelClients:
                # stelClients[s].sendEqCoords(indiTelescopeTIMEUTC, indiTelescopeRAJNOW, indiTelescopeDECJNOW, status)
                print('Sending scope coors to stellarium', len(stelClients))
                # TODO: Last Status thread safety
                ls = control.last_status
                if ls is not None and 'ra' in ls and 'dec' in ls and ls['ra'] and ls['dec']:
                    stelClients[s].send_eq_coords('', ls['ra'] * 24.0 / 360.0, ls['dec'], status)
            if len(gotoQueue) > 0:
                print('Sending goto (ra, dec)=' + str(gotoQueue[0]))
                # TODO: Send gotoQueue[0] to SSTEQ25
                ra = gotoQueue[0][0] * 360.0 / 24.0
                dec = gotoQueue[0][1]
                gotoQueue = gotoQueue[1:]
                coord = SkyCoord(ra=ra*u.deg, dec=dec*u.deg, frame='icrs')
                if control.slewtocheck(coord):
                    try:
                        control.slew(coord)
                    except control.NotSyncedException as e:
                        pass
            # logging.info('Perform step')
            # perform one step
            readers = [stelSocket] + [s for s in stelClients]
            writers = [s for s in stelClients if stelClients[s].has_to_write()]
            ready_to_read, ready_to_write, in_error = select.select(readers, writers, [], 0.5)
            for r in ready_to_read:
                if r == stelSocket:
                    news, newa = stelSocket.accept()
                    news.setblocking(0)
                    stelClients[news] = StelClient(news, newa)
                    print('New Stellarium client ' + str(news.fileno()) + ' on port ' + str(newa))
                else:
                    try:
                        stelClients[r].perform_read()
                    except:
                        stelClients.pop(r)
            for r in ready_to_write:
                if r in stelClients.keys():
                    try:
                        stelClients[r].perform_write()
                    except:
                        stelClients.pop(r)
            for r in in_error:
                print('Lost Stellarium client ' + str(r.fileno()))
                if r in stelClients.keys():
                    stelClients[r].disconnect()
                    stelClients.pop(r)
            time.sleep(0.5)
    except KeyboardInterrupt:
        logging.info('Bye')
    else:
        traceback.print_exc()

    stelSocket.shutdown(socket.SHUT_RDWR)
    stelSocket.close()
    for sc in stelClients:
        stelClients[sc].disconnect()
    stelSocket.close()
