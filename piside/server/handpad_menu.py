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

# TODO This global limits us to one handpad.
hserver = None
kill = False
client_id = str(uuid.uuid4())


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


class NumInputMenu(ABC):
    def __init__(self, title, prefix, max_length):
        self.title = title
        self.prefix = prefix
        self.inputstr = ''
        self.selection = 0
        self.max_length = max_length

    @abc.abstractmethod
    def selected(self):
        pass

    def reset(self):
        self.inputstr = ''
        self.selection = 0

    def print(self):
        hserver.println(self.title, 0)
        hserver.println(' ' + self.prefix + ' ' + self.inputstr, 1)
        line = ''
        for v in range(0, 5):
            if v == self.selection:
                line += ' >' + str(v)
            else:
                line += '  ' + str(v)
        if self.selection == 11:
            d = ' >DEL'
        else:
            d = '  DEL'
        hserver.println(line + d, 2)
        line = ''
        for v in range(5, 10):
            if v == self.selection:
                line += ' >' + str(v)
            else:
                line += '  ' + str(v)
        if self.selection == 10:
            ok = ' >OK'
        else:
            ok = '  OK'
        hserver.println(line + ok, 3)

    def refresh(self):
        self.print()

    def input(self):
        hin = hserver.input()
        if hin:
            if hin == 'E':
                if self.selection == 10:
                    # obj_search = ObjectSearchMenu(self.prefix + self.inputstr)
                    # obj_search.run_loop()
                    ret = self.selected()
                    if ret == 'escape':
                        hin = 'S'
                    elif ret == 'base':
                        self.inputstr = ''
                        return 'base'
                    # Item selected
                elif self.selection == 11:
                    self.inputstr = self.inputstr[0:-1]
                elif len(self.inputstr) < self.max_length:
                    self.inputstr += str(self.selection)
            if hin == 'S':
                return 'escape'
            elif hin == 'L':
                if self.selection == 11:
                    self.selection = 4
                elif self.selection == 5:
                    self.selection = 11
                else:
                    self.selection -= 1
                    if self.selection < 0:
                        self.selection = 10
            elif hin == 'U':
                if self.selection == 11:
                    self.selection = 10
                elif self.selection == 10:
                    self.selection = 11
                else:
                    self.selection -= 5
                    if self.selection < 0:
                        self.selection += 10
            elif hin == 'R':
                if self.selection == 4:
                    self.selection = 11
                elif self.selection == 11:
                    self.selection = 5
                else:
                    self.selection += 1
                    if self.selection > 10:
                        self.selection = 0
            elif hin == 'D':
                if self.selection == 11:
                    self.selection = 10
                elif self.selection == 10:
                    self.selection = 11
                else:
                    self.selection += 5
                    self.selection = self.selection % 10
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


class ManualCoord:
    def __init__(self):
        self.title = 'Goto: Manual Coord'
        self.prefix = '%02dh%02m%02s %s02dd%02dm%02s'
        self.ra = ['00', '00', '00']
        self.dec = ['+', '00', '00', '00']
        self.max_length = 13
        self.cursor = 0
        self.inputstr = ''
        self.selection = 0

    def reset(self):
        self.inputstr = ''
        self.selection = 0

    def print(self):
        hserver.println(self.title, 0)
        hserver.println(' %sh%sm%ss %s%sd%sm%ss' % (
            bl(self.inputstr[0:2]), bl(self.inputstr[2:4]), bl(self.inputstr[4:6]), bl(self.inputstr[6:7], 1),
            bl(self.inputstr[7:9]), bl(self.inputstr[9:11]), bl(self.inputstr[11:13])
        ), 1)
        line = ''
        if len(self.inputstr) == 6:
            if self.selection == 0:
                line += ' >+'
            else:
                line += '  +'
            if self.selection == 1:
                line += ' >-'
            else:
                line += '  -'
            if self.selection == 2:
                line += ' >DEL'
            else:
                line += '  DEL'
            hserver.println(line, 2)
            hserver.clearln(3)
        elif len(self.inputstr) == 13:
            if self.selection == 0:
                line += ' >OK'
            else:
                line += '  OK'
            if self.selection == 1:
                line += ' >DEL'
            else:
                line += '  DEL'
            hserver.println(line, 2)
            hserver.clearln(3)
        else:
            r1, r2 = self.line_maxes()

            for v in range(0, r1):
                if v == self.selection:
                    line += ' >' + str(v)
                else:
                    line += '  ' + str(v)
            if self.selection == max(r1, r2):
                d = ' >DEL'
            else:
                d = '  DEL'
            hserver.println(line + d, 2)
            line = ''
            for v in range(5, r2):
                if v == self.selection:
                    line += ' >' + str(v)
                else:
                    line += '  ' + str(v)
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
            r1 = 3
            r2 = 0
        elif len(self.inputstr) == 1 and self.inputstr[0] == '2':
            r1 = 4
            r2 = 0
        elif len(self.inputstr) in [1, 3, 5, 7, 8, 10, 12]:
            r1 = 5
            r2 = 10
        else:
            r1 = 5
            r2 = 6
        return r1, r2

    def input(self):
        hin = hserver.input()
        if hin:
            r1, r2 = self.line_maxes()
            if hin == 'E':
                if len(self.inputstr) == 6:
                    if self.selection == 2:
                        self.inputstr = self.inputstr[0:-1]
                    elif self.selection == 0:
                        self.inputstr += '+'
                    elif self.selection == 1:
                        self.inputstr += '-'
                    self.selection = 0
                elif len(self.inputstr) == 13:
                    if self.selection == 0:
                        ret = self.selected()
                        if ret == 'escape':
                            hin = 'S'
                        elif ret == 'base':
                            self.inputstr = ''
                            return 'base'
                    elif self.selection == 1:
                        self.inputstr = self.inputstr[0:-1]
                else:
                    if self.selection == max(r1, r2):
                        self.inputstr = self.inputstr[0:-1]
                    else:
                        self.inputstr += str(self.selection)
                    self.selection = 0
            if hin == 'S':
                return 'escape'
            elif hin == 'L':
                if self.selection == max(r1, r2):
                    self.selection = r1 - 1
                elif self.selection == 0:
                    self.selection = max(r1, r2)
                elif self.selection == r1:
                    self.selection = max(r1, r2)
                else:
                    self.selection -= 1
            elif hin == 'U':
                if self.selection == max(r1, r2):
                    self.selection = max(r1, r2)
                else:
                    self.selection -= 5
                    if self.selection < 0:
                        self.selection += 10
                        if self.selection > r2:
                            self.selection = max(r1, r2)
            elif hin == 'R':
                if self.selection == r1 - 1:
                    self.selection = max(r1, r2)
                elif self.selection == max(r1, r2):
                    self.selection = r1
                else:
                    self.selection += 1
            elif hin == 'D':
                if self.selection == max(r1, r2):
                    self.selection = max(r1, r2)
                else:
                    self.selection += 5
                    self.selection = self.selection % max(r1, r2)
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
                print(dso)
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
                print(star)
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
        hin = hserver.input()
        if hin:
            print('hin', hin)
            if hin == 'E':
                ret = self.selected()
                print('Menu', self.base_menu, ret)
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


class SyncSlewMenu(Menu):
    def __init__(self, slew_object):
        self.object = slew_object
        coord = SkyCoord(ra=slew_object['ra'] * u.deg, dec=slew_object['dec'] * u.deg, frame='icrs').to_string('hmsdms')
        coord = re.sub(r'\.\d+s', 's', coord)
        m = {slew_object['search'] + '\n' + coord: {'Slew': {}, 'Sync': {}}}
        super().__init__(m)
        self.loop = True

    def selected(self):
        if self.menu_selection == 0:  # Slew
            stop = thinking('Slewing')
            control.set_slew(self.object['ra'], self.object['dec'])
            time.sleep(1)
            # TODO: Show coordinates while slewing
            # A way to interrupt slewing (esc key?)
            while control.last_status['slewing']:
                time.sleep(0.25)
            stop['stop'] = True
            stop['thread'].join()
            InfoMenu('Slew Complete', 'base').run_loop()
            return "base"
        elif self.menu_selection == 1:  # Sync
            stop = thinking('Syncing')
            control.set_sync(self.object['ra'], self.object['dec'])
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
        hin = hserver.input()
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
        hin = hserver.input()
        pressed = hserver.pressed()
        if hin:
            if hin == 'S':
                for d in ['up', 'left', 'down', 'right']:
                    control.manual_control(d, None, client_id)
                return "escape"
        if len(pressed) > 0:
            if 'U' in pressed:
                control.manual_control('up', self.speed, client_id)
            if 'D' in pressed:
                control.manual_control('down', self.speed, client_id)
            if 'L' in pressed:
                control.manual_control('left', self.speed, client_id)
            if 'R' in pressed:
                control.manual_control('right', self.speed, client_id)
        if len(self.last_pressed) > 0:
            if 'U' in self.last_pressed and 'U' not in pressed:
                control.manual_control('up', None, client_id)
            if 'D' in self.last_pressed and 'D' in pressed:
                control.manual_control('down', None, client_id)
            if 'L' in self.last_pressed and 'L' in pressed:
                control.manual_control('left', None, client_id)
            if 'R' in self.last_pressed and 'R' in pressed:
                control.manual_control('right', None, client_id)
        self.last_pressed = pressed
        return "stay"

    def run_loop(self):
        while not kill:
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
        hin = hserver.input()
        if hin:
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
                'Uranus': Planet('uranus'),
                'Venus': Planet('venus')
            },
            "Messier": MessierMenu(),
            "NGC": NGCMenu(),
            "IC": ICMenu(),
            "Star Name": make_star_menus(named_stars),
            "Manual Coords": ManualCoord()
        },
        "Settings": {
            "Network": {
                "IP Status": IPMenu(),
                "Wifi": WifiMenu()
            },
            "Location/GPS": {
                'Presets': {},
                'GPS': {}
            }
        },
        "Park": {}
    }
}
