import abc
import re
import threading
import time
from abc import ABC
import uuid

import astropy.units as u
from astropy.coordinates import SkyCoord

import control
import db

import zeroconfserver
import network

import settings
import pynmea2
import pendulum

# TODO This global limits us to one handpad.
hserver = None
kill = False
client_id = str(uuid.uuid4())


def parse_gps(lines):
    # Example:
    # $GPRMC,035007.00,A,3855.98919,N,09514.94030,W,0.029,,310520,,,A*61
    # $GPGGA,035006.00,3855.98917,N,09514.94031,W,1,08,1.12,255.7,M,-28.4,M,,*61
    # TODO: Detect when we have no gps sats.
    rmc = pynmea2.parse(lines[0])
    gga = pynmea2.parse(lines[1])
    # print(rmc)
    # print(gga)
    # gga.altitude
    if gga.lat == '':
        # We've not got a satalite yet
        return None
    utc = pendulum.datetime(rmc.datestamp.year, rmc.datestamp.month, rmc.datestamp.day, rmc.timestamp.hour,
                            rmc.timestamp.minute, rmc.timestamp.second)
    return {'utc': utc,
            'location': {'lat': gga.latitude, 'long': gga.longitude, 'elevation': gga.altitude}}


def terminate():
    global kill
    kill = True


def get_menu(menu, menu_pos):
    k = list(menu.keys())[menu_pos[0]]
    m = menu[k]
    if len(menu_pos) == 1:
        return {k: m}
    return get_menu(m, menu_pos[1:])


def thinking(info_str):
    stop = {'stop': False, 'thread': None}

    def thinking2():
        hserver.clearln(1)
        hserver.clearln(2)
        hserver.clearln(3)
        hserver.println(info_str + '...', 0)
        while not stop['stop']:
            for i in range(4):
                hserver.println(info_str + ('.' * i), 0)
                time.sleep(0.3)
                if stop['stop']:
                    break

    t = threading.Thread(target=thinking2)
    t.start()
    stop['thread'] = t
    return stop


class ObjectSearchMenu:
    def __init__(self, search_kw):
        self.search_kw = search_kw

    def run_loop(self):
        # recv = hserver.send(json.dumps({'search_object': {'search': self.search_kw}}))
        pass


class GPSMenu:
    def __init__(self):
        pass

    def run_loop(self):
        hserver.clearall()
        hserver.println('Reading from GPS...', 0)
        count = 0
        while count < 10:
            lines = hserver.gps()
            if len(lines) > 0:
                if lines[0] == 'ERROR':
                    m = InfoMenu('Error in GPS read.')
                    return m.run_loop()
                # print(lines)
                info = parse_gps(lines)
                if info is None:
                    count += 1
                    time.sleep(10)
                    continue
                control.set_time(info['utc'].isoformat())
                control.set_location(info['location']['lat'], info['location']['long'], info['location']['elevation'],
                                     'GPS')
                m = InfoMenu('Time/Location Set')
                m.run_loop()
                TimeSiderealInfo().run_loop()
                return GeoInfo().run_loop()
            else:
                m = InfoMenu('Error in GPS empty.')
                return m.run_loop()
        m = InfoMenu('Error getting GPS')
        return m.run_loop()


class GPSDisplay:
    def __init__(self, info):
        self.info = info

    def refresh(self):
        self.print()

    def print(self):
        pass

    def run_loop(self):
        hserver.clearall()
        timestr = self.info['local'].isoformat().split('T')
        hserver.println("GPS Set " + timestr[0], 0)
        hserver.println(timestr[1], 1)
        hserver.println('{lat:.2f}d {lon:.2f}d '.format(
            lat=self.info['location']['lat'], lon=self.info['location']['lon']), 2)
        hserver.print('{elevation:.1f}m'.format(elevation=self.info['location']['elevation']), 3)
        while not kill:
            for hin in hserver.input():
                if hin:
                    if hin == 'E' or hin == 'S':
                        return 'base'
            time.sleep(0.1)


class NumInputMenu(ABC):
    def __init__(self, title, prefix, max_length):
        self.title = title
        self.prefix = prefix
        self.inputstr = ''
        self.selection = 0
        self.max_length = max_length
        self.inputs = [['0', '0'], ['1', '1'], ['2', '2'], ['3', '3'], ['4', '4'], ['DEL', 'DEL'],
                       ['5', '5'], ['6', '6'], ['7', '7'], ['8', '8'], ['9', '9'], ['OK', 'OK']]

    @abc.abstractmethod
    def selected(self):
        pass

    def reset(self):
        self.inputstr = ''
        self.selection = 0

    def print(self):
        if self.selection >= len(self.inputs):
            self.selection = len(self.inputs) - 1
        hserver.println(self.title, 0)
        hserver.println(' ' + self.prefix + ' ' + self.inputstr, 1)
        line = ''
        for i in range(min(6, len(self.inputs))):
            if i == self.selection:
                line += ' >' + str(self.inputs[i][0])
            else:
                line += '  ' + str(self.inputs[i][0])
        hserver.println(line, 2)
        line = ''
        if len(self.inputs) > 5:
            for i in range(6, min(12, len(self.inputs))):
                if i == self.selection:
                    line += ' >' + str(self.inputs[i][0])
                else:
                    line += '  ' + str(self.inputs[i][0])
        hserver.println(line, 3)

    def refresh(self):
        self.print()

    def input(self):
        refresh = False
        for hin in hserver.input():
            if self.selection >= len(self.inputs):
                self.selection = len(self.inputs) - 1
            refresh = True
            if hin == 'E':
                s = self.inputs[self.selection][1]
                if s == 'OK':
                    # obj_search = ObjectSearchMenu(self.prefix + self.inputstr)
                    # obj_search.run_loop()
                    ret = self.selected()
                    if ret == 'escape':
                        hin = 'S'
                    elif ret == 'base':
                        self.inputstr = ''
                        return 'base'
                    # Item selected
                elif s == 'DEL':
                    self.inputstr = self.inputstr[0:-1]
                    break
                elif len(self.inputstr) < self.max_length:
                    self.inputstr += str(s)
                    break
            if hin == 'S':
                return 'escape'
            elif hin == 'L':
                self.selection -= 1
                if self.selection < 0:
                    self.selection = len(self.inputs) - 1
            elif hin == 'U':
                self.selection = (self.selection + 6) % len(self.inputs)
                if self.selection < 0:
                    self.selection += 12
            elif hin == 'R':
                self.selection += 1
                if self.selection > len(self.inputs) - 1:
                    self.selection = 0
            elif hin == 'D':
                self.selection += 6
                self.selection = self.selection % len(self.inputs)
        if refresh:
            self.refresh()
        return "stay"

    def run_loop(self):
        self.refresh()
        while not kill:
            leave = self.input()
            if leave == 'base':
                return 'base'
            elif leave == 'escape':
                return 'stay'
            time.sleep(0.1)


def bl(s, d=2):
    ret = ''
    for i in range(d):
        if len(s) > i:
            ret += s[i]
        else:
            ret += '_'
    return ret


class ManualCoordRADec:
    def __init__(self):
        self.title = 'Goto: RA/Dec'
        self.prefix = ''
        self.max_length = 13
        self.cursor = 0
        self.inputstr = ''
        self.selection = 0
        self.inputs = []

    def reset(self):
        self.inputstr = ''
        self.selection = 0

    def coord_print(self):
        hserver.println('%sh%sm%ss %s%sd%sm%ss' % (
            bl(self.inputstr[0:2]), bl(self.inputstr[2:4]), bl(self.inputstr[4:6]), bl(self.inputstr[6:7], 1),
            bl(self.inputstr[7:9]), bl(self.inputstr[9:11]), bl(self.inputstr[11:13])
        ), 1)

    def print(self):
        self.line_maxes()
        if self.selection >= len(self.inputs):
            self.selection = len(self.inputs) - 1
        hserver.println(self.title, 0)
        self.coord_print()
        line = ''
        for i in range(min(6, len(self.inputs))):
            if i == self.selection:
                line += ' >' + str(self.inputs[i][0])
            else:
                line += '  ' + str(self.inputs[i][0])
        hserver.println(line, 2)
        line = ''
        if len(self.inputs) > 5:
            for i in range(6, min(12, len(self.inputs))):
                if i == self.selection:
                    line += ' >' + str(self.inputs[i][0])
                else:
                    line += '  ' + str(self.inputs[i][0])
        hserver.println(line, 3)

    def refresh(self):
        self.print()

    def selected(self):
        ra = float(self.inputstr[0:2]) + float(self.inputstr[2:4]) / 60. + float(self.inputstr[4:6]) / (60. * 60.)
        ra = ra * (360. / 24.)
        dec = float(self.inputstr[7:9]) + float(self.inputstr[9:11]) / 60. + float(self.inputstr[11:13]) / (60. * 60.)
        if self.inputstr[6] == '-':
            dec = -1.0 * dec
        m = SyncSlewMenu({'ra': ra, 'dec': dec, 'search': 'Slew To Coord'})
        return m.run_loop()

    def line_maxes(self):
        if len(self.inputstr) == 0:
            self.inputs = [['0', '0'], ['1', '1'], ['2', '2']]
        elif len(self.inputstr) == 1 and self.inputstr[0] == '2':
            self.inputs = [['0', '0'], ['1', '1'], ['2', '2'], ['3', '3'], ['DEL', 'DEL']]
        elif len(self.inputstr) in [1, 3, 5, 7, 8, 10, 12]:
            self.inputs = [['0', '0'], ['1', '1'], ['2', '2'], ['3', '3'], ['4', '4'], ['DEL', 'DEL'],
                           ['5', '5'], ['6', '6'], ['7', '7'], ['8', '8'], ['9', '9']]
        elif len(self.inputstr) == 6:
            self.inputs = [['+', '+'], ['-', '-'], ['DEL', 'DEL']]
        elif len(self.inputstr) == 13:
            self.inputs = [['DEL', 'DEL'], ['OK', 'OK']]
        else:
            self.inputs = [['0', '0'], ['1', '1'], ['2', '2'], ['3', '3'], ['4', '4'], ['DEL', 'DEL'],
                           ['5', '5']]

    def input(self):
        refresh = False
        for hin in hserver.input():
            refresh = True
            if self.selection >= len(self.inputs):
                self.selection = len(self.inputs) - 1
            self.line_maxes()
            if hin == 'E':
                s = self.inputs[self.selection][1]
                if s == 'OK':
                    # obj_search = ObjectSearchMenu(self.prefix + self.inputstr)
                    # obj_search.run_loop()
                    ret = self.selected()
                    if ret == 'escape':
                        hin = 'S'
                    elif ret == 'base':
                        self.inputstr = ''
                        return 'base'
                    # Item selected
                elif s == 'DEL':
                    self.inputstr = self.inputstr[0:-1]
                    break
                elif len(self.inputstr) < self.max_length:
                    self.inputstr += str(s)
                    if len(self.inputstr) == 8:
                        if self.inputstr[-1] == '9':
                            self.inputstr += '00000'
                    break
            if hin == 'S':
                return 'escape'
            elif hin == 'L':
                self.selection -= 1
                if self.selection < 0:
                    self.selection = len(self.inputs) - 1
            elif hin == 'U':
                self.selection = (self.selection + 5) % len(self.inputs)
                if self.selection < 0:
                    self.selection += 12
            elif hin == 'R':
                self.selection += 1
                if self.selection > len(self.inputs) - 1:
                    self.selection = 0
            elif hin == 'D':
                self.selection += 6
                self.selection = self.selection % len(self.inputs)
        if refresh:
            self.refresh()
        return "stay"

    def run_loop(self):
        self.refresh()
        while not kill:
            leave = self.input()
            if leave == 'base':
                return 'base'
            elif leave == 'escape':
                return 'stay'
            time.sleep(0.1)


class ManualCoordAltAz(ManualCoordRADec):
    def __init__(self):
        super().__init__()
        self.title = 'Goto: Alt/Az'
        self.inputstr = ''
        self.inputs = []

    def coord_print(self):
        hserver.println('%sd%sm%ss %sd%sm%ss' % (
            bl(self.inputstr[0:2]), bl(self.inputstr[2:4]), bl(self.inputstr[4:6]),
            bl(self.inputstr[6:9], 3), bl(self.inputstr[9:11]), bl(self.inputstr[11:13])
        ), 1)

    def selected(self):
        alt = float(self.inputstr[0:2]) + float(self.inputstr[2:4]) / 60. + float(self.inputstr[4:6]) / (60. * 60.)
        az = float(self.inputstr[6:9]) + float(self.inputstr[9:11]) / 60. + float(self.inputstr[11:13]) / (60. * 60.)
        m = SyncSlewMenu({'alt': alt, 'az': az, 'search': 'Slew To Coord'})
        return m.run_loop()

    def line_maxes(self):
        if len(self.inputstr) == 0:
            self.inputs = [['0', '0'], ['1', '1'], ['2', '2'], ['3', '3'], ['4', '4'],
                           ['5', '5'], ['6', '6'], ['7', '7'], ['8', '8'], ['9', '9']]
        elif len(self.inputstr) == 1 and self.inputstr[0] == '9':
            self.inputs = [['0', '0'], ['DEL', 'DEL']]
        elif len(self.inputstr) == 7 and self.inputstr[6] == '3':
            self.inputs = [['0', '0'], ['1', '1'], ['2', '2'], ['3', '3'], ['4', '4'], ['DEL', 'DEL'],
                           ['5', '5']]
        elif len(self.inputstr) in [1, 3, 5, 7, 8, 10, 12]:
            self.inputs = [['0', '0'], ['1', '1'], ['2', '2'], ['3', '3'], ['4', '4'], ['DEL', 'DEL'],
                           ['5', '5'], ['6', '6'], ['7', '7'], ['8', '8'], ['9', '9']]
        elif len(self.inputstr) == 6:
            self.inputs = [['0', '0'], ['1', '1'], ['2', '2'], ['3', '3'], ['DEL', 'DEL']]
        elif len(self.inputstr) == 13:
            self.inputs = [['DEL', 'DEL'], ['OK', 'OK']]
        else:
            self.inputs = [['0', '0'], ['1', '1'], ['2', '2'], ['3', '3'], ['4', '4'], ['DEL', 'DEL'],
                           ['5', '5']]


class MessierMenu(NumInputMenu):
    def __init__(self, title='Goto: Messier', prefix='M', max_length=3):
        super().__init__(title, prefix, max_length)
        self.prefix = prefix

    def selected(self):
        stop = thinking('Searching')
        dsos = db.search_dso(self.prefix + ' ' + self.inputstr)
        objects = {'Object Selection': {}}
        if len(dsos) > 1:
            for dso in dsos:
                # print(dso)
                dso['search'] = re.sub(r'(^\|)|(\|$)', '', dso['search'].strip())
                dso['search'] = dso['search'].replace('|', ',')
                objects['Object Selection'][dso['search']] = SyncSlewMenu(dso)
            stop['stop'] = True
            stop['thread'].join()
            m = Menu(objects)
            return m.run_loop()
        elif len(dsos) == 1:
            dso = dsos[0]
            dso['search'] = re.sub(r'(^\|)|(\|$)', '', dso['search'].strip())
            dso['search'] = dso['search'].replace('|', ',')
            stop['stop'] = True
            stop['thread'].join()
            menu = SyncSlewMenu(dso)
            return menu.run_loop()
        else:
            stop['stop'] = True
            stop['thread'].join()
            menu = InfoMenu('No object found', 'escape')
            return menu.run_loop()


class NGCMenu(MessierMenu):
    def __init__(self):
        super().__init__('Goto:NGC', 'NGC', 4)


class ICMenu(MessierMenu):
    def __init__(self):
        super().__init__('Goto:IC', 'IC', 4)


class Planet(MessierMenu):
    def __init__(self, planet):
        super().__init__('Goto:Planet', 'P', 1)
        self.inputstr = planet

    def selected(self):
        stop = thinking('Searching')
        planets = db.search_planets(self.inputstr)
        if len(planets) >= 1:
            dso = planets[0]
            dso['search'] = dso['name']
            stop['stop'] = True
            stop['thread'].join()
            menu = SyncSlewMenu(dso)
            menu.run_loop()
            return "base"
        else:
            stop['stop'] = True
            stop['thread'].join()
            menu = Menu({'No object found': {'Okay': {}}})
            menu.run_loop()
            return "base"

    def run_loop(self):
        return self.selected()


class Star(MessierMenu):
    def __init__(self, star):
        super().__init__('Goto:Star', 'S', 1)
        self.inputstr = star

    def selected(self):
        stop = thinking('Searching')
        stars = db.search_stars(self.inputstr)
        objects = {'Object Selection': {}}
        if len(stars) > 1:
            for star in stars:
                # print(star)
                star['search'] = star['bf'] + ',' + star['proper']
                objects['Object Selection'][star['search']] = SyncSlewMenu(star)
            stop['stop'] = True
            stop['thread'].join()
            m = Menu(objects)
            return m.run_loop()
        elif len(stars) == 1:
            star = stars[0]
            star['search'] = star['bf'] + ',' + star['proper']
            stop['stop'] = True
            stop['thread'].join()
            menu = SyncSlewMenu(star)
            return menu.run_loop()
        else:
            stop['stop'] = True
            stop['thread'].join()
            menu = InfoMenu('No object found', 'escape')
            return menu.run_loop()

    def run_loop(self):
        return self.selected()


class Menu:
    def __init__(self, menus, server=None):
        global hserver
        self.menus = menus
        self.base_menu = False
        if server:
            hserver = server
            self.base_menu = True
        self.menu_pos = [0]
        self.menu_selection = 0
        self.loop = False

    def print(self):
        menu = get_menu(self.menus, self.menu_pos)
        menu_key = list(menu.keys())[0]
        menu_split = list(menu.keys())[0].split('\n')
        menu_name = menu_split[0]
        menu_name2 = None
        if len(menu_split) == 2:
            menu_name2 = menu_split[1]
        menu_value = menu[menu_key]

        option_count = 3
        counter = 1
        hserver.println(menu_name, 0)
        if menu_name2:
            option_count = 2
            counter = 2
            hserver.println(menu_name2, 1)
        start = int(self.menu_selection / float(option_count)) * option_count
        for i in range(start, len(menu_value.keys())):
            key = list(menu_value.keys())[i]
            if i == self.menu_selection:
                hserver.println(' >' + key, counter)
            else:
                hserver.println('  ' + key, counter)
            counter += 1
            if counter > 3:
                return
        if counter < 4:
            for i in range(counter, 4):
                hserver.clearln(i)

    def refresh(self):
        self.print()

    def selected(self):
        """
        :return: "stay" to keep in menu when selected is done
                 "escape" to leave menu
                 "base" go to base menu
        """
        self.menu_pos.append(self.menu_selection)
        self.menu_selection = 0
        menu = get_menu(self.menus, self.menu_pos)
        menu_key = list(menu.keys())[0]
        menu_value = menu[menu_key]
        if not isinstance(menu_value, dict):
            ret = menu_value.run_loop()
            self.menu_pos = self.menu_pos[0:-1]
            self.menu_selection = 0
            return ret
        return "stay"

    def input(self):
        """
        :return: "stay" to keep in menu when selected is done
                 "escape" to leave menu
                 "base" go to base menu
        """
        refresh = False
        for hin in hserver.input():
            refresh = True
            # print('hin', hin)
            if hin == 'E':
                ret = self.selected()
                # print('Menu', self.base_menu, ret)
                if ret == 'base':
                    self.menu_selection = 0
                    self.menu_pos = [self.menu_pos[0]]
                    if not self.base_menu:
                        return 'base'
                elif ret == 'escape':
                    hin = 'S'
            if hin == 'S':
                self.menu_selection = 0
                if not self.base_menu and len(self.menu_pos) == 1:
                    return "escape"
                if len(self.menu_pos) > 1:
                    self.menu_pos = self.menu_pos[0:-1]
                    break
            elif hin == 'L' or hin == 'U':
                self.menu_selection -= 1
                menu = get_menu(self.menus, self.menu_pos)
                menu_name = list(menu.keys())[0]
                menu_value = menu[menu_name]
                if self.menu_selection < 0:
                    if self.loop:
                        self.menu_selection = len(menu_value.keys()) - 1
                    else:
                        self.menu_selection = 0
            elif hin == 'R' or hin == 'D':
                self.menu_selection += 1
                menu = get_menu(self.menus, self.menu_pos)
                menu_name = list(menu.keys())[0]
                menu_value = menu[menu_name]
                if self.menu_selection >= len(menu_value.keys()):
                    if self.loop:
                        self.menu_selection = 0
                    else:
                        self.menu_selection = len(menu_value.keys()) - 1
        if refresh:
            self.refresh()
        return "stay"

    def run_loop(self):
        self.refresh()
        while not kill:
            leave = self.input()
            if not self.base_menu:
                if leave == "base":
                    return "base"
                elif leave == "escape":
                    return "stay"
            time.sleep(0.1)


class SlewingMenu:
    def __init__(self, target):
        self.target = target

    def run_loop(self):
        hserver.clearall()
        hserver.println('Slewing...', 0)

        if 'ra' in self.target:
            coord = SkyCoord(ra=self.target['ra'] * u.deg, dec=self.target['dec'] * u.deg, frame='icrs').to_string(
                'hmsdms')
        else:
            coord = SkyCoord(alt=self.target['alt'] * u.deg, az=self.target['az'] * u.deg, frame='altaz').to_string(
                'dms')
            coord = ' '.join(reversed(coord.split(' ')))
        coord = re.sub(r'\.\d+s', 's', coord)
        hserver.println(coord, 1)

        ts = -1.0
        while not kill:
            for hin in hserver.input():
                if hin == 'S':
                    control.cancel_slews()
                    return 'canceled'
            if 'ra' in self.target:
                if time.monotonic() - ts >= 1.5:
                    ts = time.monotonic()
                    coord = SkyCoord(ra=control.last_status['ra'] * u.deg, dec=control.last_status['dec'] * u.deg,
                                     frame='icrs').to_string('hmsdms')
                    coord = re.sub(r'\.\d+s', 's', coord)
                    hserver.println(coord, 3)
            else:
                if time.monotonic() - ts >= 1.5:
                    ts = time.monotonic()
                    coord = SkyCoord(alt=control.last_status['alt'] * u.deg, az=control.last_status['az'] * u.deg,
                                     frame='altaz').to_string('dms')
                    coord = ' '.join(reversed(coord.split(' ')))
                    coord = re.sub(r'\.\d+s', 's', coord)
                    hserver.println(coord, 3)
            if not control.last_status['slewing']:
                return 'complete'
            time.sleep(0.25)


class SyncSlewMenu(Menu):
    def __init__(self, slew_object):
        self.object = slew_object
        if 'ra' in slew_object:
            coord = SkyCoord(ra=slew_object['ra'] * u.deg, dec=slew_object['dec'] * u.deg, frame='icrs').to_string(
                'hmsdms')
        else:
            coord = SkyCoord(alt=slew_object['alt'] * u.deg, az=slew_object['az'] * u.deg, frame='altaz').to_string(
                'dms')
            coord = ' '.join(reversed(coord.split(' ')))
        coord = re.sub(r'\.\d+s', 's', coord)
        m = {slew_object['search'] + '\n' + coord: {'Slew': {}, 'Sync': {}}}
        super().__init__(m)
        self.loop = True

    def selected(self):
        if self.menu_selection == 0:  # Slew
            if 'ra' in self.object:
                control.set_slew(self.object['ra'], self.object['dec'])
            else:
                control.set_slew(alt=self.object['alt'], az=self.object['az'])
            time.sleep(1)
            ret = SlewingMenu(self.object).run_loop()
            if ret == 'complete':
                InfoMenu('Slew Complete', 'base').run_loop()
            else:
                InfoMenu('Slew Interrupted', 'base').run_loop()
            return "base"
        elif self.menu_selection == 1:  # Sync
            stop = thinking('Syncing')
            if 'ra' in self.object:
                control.set_sync(self.object['ra'], self.object['dec'])
            else:
                control.set_sync(alt=self.object['alt'], az=self.object['az'])
            stop['stop'] = True
            stop['thread'].join()
            InfoMenu('Synced', 'base').run_loop()
            return "base"


class StatusMenu:
    def __init__(self):
        pass


class InfoMenu(Menu):
    def __init__(self, info, on_okay='escape'):
        super().__init__({info: {'Okay': {}}})
        self.on_okay = on_okay

    def selected(self):
        return self.on_okay


class IPMenu:
    def __init__(self):
        pass

    def input(self):
        for hin in hserver.input():
            if hin:
                if hin == 'E':
                    return "escape"
                if hin == 'S':
                    return "escape"
        return "stay"

    def run_loop(self):
        hserver.clearall()
        hserver.println('IP Status', 0)
        addresses = zeroconfserver.get_addresses()
        for i in range(min(3, len(addresses))):
            hserver.println(' ' + addresses[i], i + 1)
        while not kill:
            leave = self.input()
            if leave == "base":
                return "base"
            elif leave == "escape":
                return "stay"
            time.sleep(0.1)


class ManualSlewMenu:
    def __init__(self, speed):
        self.speed = speed
        self.last_pressed = ''

    def input(self):
        for hin in hserver.input():
            if hin == 'S':
                for d in ['up', 'left', 'down', 'right']:
                    control.manual_control(d, None, client_id)
                return "escape"
        pressed = hserver.pressed()
        control.set_alive(client_id)
        if len(pressed) > 0:
            if 'U' in pressed:
                # print('up pressed')
                control.manual_control('up', self.speed, client_id)
            if 'U' not in self.last_pressed and 'D' in pressed:
                # print('down pressed')
                control.manual_control('down', self.speed, client_id)
            if 'R' not in self.last_pressed and 'L' in pressed:
                # print('left pressed')
                control.manual_control('left', self.speed, client_id)
            if 'L' not in self.last_pressed and 'R' in pressed:
                # print('right pressed')
                control.manual_control('right', self.speed, client_id)
        if len(self.last_pressed) > 0:
            if 'U' in self.last_pressed and 'U' not in pressed:
                control.manual_control('up', None, client_id)
            if 'D' in self.last_pressed and 'D' not in pressed:
                control.manual_control('down', None, client_id)
            if 'L' in self.last_pressed and 'L' not in pressed:
                control.manual_control('left', None, client_id)
            if 'R' in self.last_pressed and 'R' not in pressed:
                control.manual_control('right', None, client_id)
        self.last_pressed = pressed
        return "stay"

    def run_loop(self):
        hserver.clearall()
        hserver.println(self.speed.capitalize() + ' Slew', 0)
        hserver.println('Press and hold', 1)
        hserver.println('Direction buttons', 2)
        ts = -1.0
        while not kill:
            if time.monotonic() - ts >= 0.5:
                ts = time.monotonic()
                coord = SkyCoord(ra=control.last_status['ra'] * u.deg, dec=control.last_status['dec'] * u.deg,
                                 frame='icrs').to_string('hmsdms')
                coord = re.sub(r'\.\d+s', 's', coord)
                hserver.println(coord, 3)
            leave = self.input()
            if leave == "base":
                return "base"
            elif leave == "escape":
                return "stay"
            time.sleep(0.25)


class WifiMenu:
    def __init__(self):
        pass

    def input(self):
        for hin in hserver.input():
            if hin == 'E':
                return "escape"
            if hin == 'S':
                return "escape"
        return "stay"

    def run_loop(self):
        hserver.clearall()
        hserver.println('Wifi Status', 0)
        wifi_info = network.current_wifi_connect()
        if wifi_info['ssid']:
            hserver.println(' Client Mode', 1)
            hserver.println('  ' + wifi_info['ssid'], 2)
        else:
            ap = network.hostapd_read()
            hserver.println(' AP Mode', 1)
            hserver.println('  ' + str(ap['ssid']), 2)
        while not kill:
            leave = self.input()
            if leave == "base":
                return "base"
            elif leave == "escape":
                return "stay"
            time.sleep(0.1)


class LocationPreset:
    def __init__(self, name, lat, long, elevation):
        self.lat = lat
        self.long = long
        self.elevation = elevation
        self.name = name

    def run_loop(self):
        control.set_location(self.lat, self.long, self.elevation, self.name)
        m = InfoMenu('Location Set')
        return m.run_loop()


class LocationPresets:
    def __init__(self):
        pass

    def run_loop(self):
        p = {}
        for preset in settings.settings['location_presets']:
            p[preset['name']] = LocationPreset(preset['name'], preset['lat'], preset['long'], preset['elevation'])
        m = {'Location Presets': p}
        return Menu(m).run_loop()


class ParkMenu:
    def __init__(self):
        pass

    def run_loop(self):
        stop = thinking('Parking')
        control.park_scope()
        time.sleep(1)
        while control.last_status['slewing']:
            time.sleep(0.25)
        stop['stop'] = True
        stop['thread'].join()
        hserver.clearall()
        hserver.println('Park Complete', 0)
        hserver.println('Turn off mount', 1)
        while True:
            time.sleep(1)


class Brightness:
    def __init__(self, level):
        self._level = 2
        if level == 'medium':
            self._level = 1
        elif level == 'low':
            self._level = 0

    def run_loop(self):
        hserver.set_brightness(self._level)
        m = InfoMenu('Brightness Set')
        return m.run_loop()


class TimeSiderealInfo:
    def __init__(self):
        pass

    def input(self):
        for hin in hserver.input():
            if hin == 'E':
                return "escape"
            if hin == 'S':
                return "escape"
        return "stay"

    def run_loop(self):
        hserver.clearall()
        hserver.println('Time/Sidereal Info', 0)
        ts = -1.0
        while not kill:
            if time.monotonic() - ts >= 1.0:
                ts = time.monotonic()
                tz = settings.runtime_settings['last_locationtz']
                if tz:
                    offset = 'UTC Offset: %.1f' % (pendulum.from_timestamp(0, tz).offset_hours,)
                    local = pendulum.now(tz).to_datetime_string()
                else:
                    offset = 'UTC Offset: 0.0'
                    local = pendulum.now('UTC').to_datetime_string() + 'Z'
                hserver.println(offset, 1)
                hserver.println(local, 2)
                hserver.println('Sidereal: ' + control.last_status['sidereal_time'], 3)
            leave = self.input()
            if leave == "base":
                return "base"
            elif leave == "escape":
                return "stay"
            time.sleep(0.1)


class MountPositionInfo:
    def __init__(self):
        pass

    def input(self):
        for hin in hserver.input():
            if hin == 'E':
                return "escape"
            if hin == 'S':
                return "escape"
        return "stay"

    def run_loop(self):
        hserver.clearall()
        hserver.println('Mount Position', 0)
        hserver.println('RA/DEC and Alt/Az', 1)
        ts = -1.0
        while not kill:
            if time.monotonic() - ts >= 1.5:
                ts = time.monotonic()

                coord = SkyCoord(ra=control.last_status['ra'] * u.deg, dec=control.last_status['dec'] * u.deg,
                                 frame='icrs').to_string('hmsdms')
                coord = re.sub(r'\.\d+s', 's', coord)
                hserver.println(coord, 2)
                coord = SkyCoord(alt=control.last_status['alt'] * u.deg, az=control.last_status['az'] * u.deg,
                                 frame='altaz').to_string('dms')
                coord = ' '.join(reversed(coord.split(' ')))
                coord = re.sub(r'\.\d+s', 's', coord)
                hserver.println(coord, 3)
            leave = self.input()
            if leave == "base":
                return "base"
            elif leave == "escape":
                return "stay"
            time.sleep(0.1)


class GeoInfo:
    def __init__(self):
        pass

    def input(self):
        for hin in hserver.input():
            if hin == 'E':
                return "escape"
            if hin == 'S':
                return "escape"
        return "stay"

    def deg_lat2str(self, lat):
        lat = float(lat)
        if lat < 0:
            latstr = 'S'
        else:
            latstr = 'N'
        lat = abs(lat)
        latd = int(lat)
        remain = lat - int(lat)
        latmin = int(remain * 60)
        latsec = int((remain - (latmin / 60.0)) * 60 * 60)
        return "{latstr:s}{latd:d}d{latmin:d}'{latsec:d}\"".format(latstr=latstr, latd=latd, latmin=latmin,
                                                                   latsec=latsec)

    def deg_long2str(self, long):
        long = float(long)
        if long < 0:
            longstr = 'W'
        else:
            longstr = 'E'
        long = abs(long)
        longd = int(long)
        remain = long - longd
        longmin = int(remain * 60)
        longsec = int((remain - (longmin / 60.0)) * 60 * 60)
        return "{longstr:s}{longd:d}d{longmin:d}'{longsec:d}\"".format(longstr=longstr, longd=longd, longmin=longmin,
                                                                       longsec=longsec)

    def run_loop(self):
        hserver.clearall()
        hserver.println('Geo Info', 0)
        hserver.println('RA/DEC and Alt/Az', 1)
        ts = -1.0
        while not kill:
            if time.monotonic() - ts >= 10:
                ts = time.monotonic()

                el = settings.runtime_settings['earth_location']
                hserver.println('   '+self.deg_lat2str(el.lat.deg), 1)
                hserver.println('   '+self.deg_long2str(el.lon.deg), 2)
                hserver.println('   %dm' % (int(el.height.value+0.5),), 3)
            leave = self.input()
            if leave == "base":
                return "base"
            elif leave == "escape":
                return "stay"
            time.sleep(0.1)


named_stars = ['Achernar', 'Acrux', 'Adhara', 'Albireo', 'Aldebaran', 'Alhna', 'Alioth', 'Alkaid', 'Alnilan', 'Alphard',
               'Altair', 'Antares', 'Arcturus', 'Atria', 'Avior', 'Bellatrix', 'Betelgeuse', 'Canopus', 'Capella',
               'Castor', 'Deneb', 'Deneb', 'Dubhe', 'El Nath', 'Fomalhaut', 'Gacrux', 'Hadar', 'Hamal',
               'Kaus Australis', 'Menkaliman', 'Miaplacidus', 'Mimosa', 'Mirfak', 'Mirzam', 'Nunki', 'Peacock',
               'Polaris', 'Pollux', 'Procyon', 'Regulus', 'Rigel', 'Rigil', 'Sargas', 'Shaula', 'Sirius', 'Spica',
               'Vega', 'Wezen']


def make_star_menus(stars):
    ret = {}
    for i in stars:
        ret[i] = Star(i)
    return ret


menu_structure = {
    "Main Menu": {
        "Manual Slew": {
            "Fastest": ManualSlewMenu('fastest'),
            "Fast": ManualSlewMenu('faster'),
            "Medium": ManualSlewMenu('medium'),
            "Slow": ManualSlewMenu('slower'),
            "Slowest": ManualSlewMenu('slowest')
        },
        "Goto": {
            "Solar System": {
                'Jupiter': Planet('jupiter'),
                'Mars': Planet('mars'),
                'Mercury': Planet('mercury'),
                'Moon': Planet('moon'),
                'Neptune': Planet('neptune'),
                'Pluto': Planet('pluto'),
                'Saturn': Planet('saturn'),
                'Sun': Planet('sun'),
                'Uranus': Planet('uranus'),
                'Venus': Planet('venus')
            },
            "Messier": MessierMenu(),
            "NGC": NGCMenu(),
            "IC": ICMenu(),
            "Star Name": make_star_menus(named_stars),
            "Manual Coords": {
                "RA/DEC": ManualCoordRADec(),
                "Alt/Az": ManualCoordAltAz()
            }
        },
        "Scope Info": {
            "Time/Sidereal": TimeSiderealInfo(),
            "Geo Info": GeoInfo(),
            "Mount Position": MountPositionInfo(),
        },
        "Settings": {
            "Brightness": {
                "High": Brightness("high"),
                "Medium": Brightness("medium"),
                "Low": Brightness("low")
            },
            "Network": {
                "IP Status": IPMenu(),
                "Wifi": WifiMenu()
            },
            "Time/Location": {
                'Presets': LocationPresets(),
                'GPS': GPSMenu()
            }
        },
        "Park": ParkMenu()
    }
}
