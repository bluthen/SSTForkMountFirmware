import socket
import traceback
import re
import uuid
import threading
import control
import pendulum
import settings
import typing
import sys
import time

DEBUG_PROT = False

ourport = 10002
kill = False
lx200Clients = {}
utctz = pendulum.timezone("UTC")
set_utc_offset = pendulum.from_timestamp(0, pendulum.now().timezone).offset_hours
localtime_daylight_savings = False
manual_slew_map = {"w": "left", "e": "right", "n": "up", "s": "down"}
slew_speed_map = {"S": "fastest", "M": "faster", "C": "slower", "G": "slowest"}
slew_speed = "fastest"
target = {"ra": None, "dec": None, "alt": None, "az": None}  # type: typing.Dict[str, typing.Optional[float]]
slew_intervals = {"n": None, "s": None, "e": None, "w": None}  # type: typing.Dict[str, typing.Optional[threading.Timer]]
slewing_time_buffer = False
slewing_time_buffer_timer = None  # type: typing.Optional[threading.Timer]
extra_logging = False

use_holders = True
datetime_holder = {
    "year": None,
    "month": None,
    "day": None,
    "hour": None,
    "minute": None,
    "second": None,
    "offset": None,
}  # type: typing.Dict[str, typing.Union[None, int, float]]
location_holder = {"lat": None, "lon": None}  # type: typing.Dict[str, typing.Union[None, float]]


def set_time(
    year=None, month=None, day=None, hour=None, minute=None, second=None, offset=None
):
    args = locals()
    for key in args.keys():
        if args[key]:
            datetime_holder[key] = args[key]
    if None not in datetime_holder.values():
        dh = datetime_holder
        dstr = pendulum.datetime(
            year=dh["year"],
            month=dh["month"],
            day=dh["day"],
            hour=dh["hour"],
            minute=dh["minute"],
            second=dh["second"],
            tz=dh["offset"],
        ).isoformat()
        return control.set_time(dstr)
    else:
        return True, "Waiting"


def set_location(lat=None, lon=None):
    args = locals()
    for key in args.keys():
        if args[key]:
            location_holder[key] = args[key]
    if None not in location_holder.values():
        control.set_location(
            location_holder["lat"], location_holder["lon"], 1000.0, "site1"
        )


def slew_commanded_delay_done():
    global slewing_time_buffer
    slewing_time_buffer = False


def slew_commanded():
    global slewing_time_buffer, slewing_time_buffer_timer
    # Cancel any pending timer from a previous slew command so it doesn't
    # prematurely clear the buffer for this new slew.
    if slewing_time_buffer_timer is not None:
        slewing_time_buffer_timer.cancel()
    slewing_time_buffer = True
    slewing_time_buffer_timer = threading.Timer(3, slew_commanded_delay_done)
    slewing_time_buffer_timer.start()


def ra_format(ra_deg, high_precision=True):
    ra = (24.0 / 360.0) * ra_deg
    remain = ra - int(ra)
    minutes = int(remain * 60)
    seconds = (remain - (minutes / 60.0)) * 60 * 60
    hours = int(abs(ra))
    if high_precision:
        return "%02d:%02d:%02d#" % (hours, minutes, seconds)
    return "%02d:%02d.%1d#" % (hours, minutes, int(10 * seconds / 60 + 0.5))


def dec_format(dec, high_precision=True):
    remain = abs(dec - int(dec))
    arcmin = int(remain * 60)
    arcsec = (remain - (arcmin / 60.0)) * 60 * 60
    deg = int(abs(dec))
    sign = "+" if dec > 0 else "-"
    if high_precision:
        return "%s%02d*%02d'%02d#" % (sign, deg, arcmin, arcsec)
    else:
        return "%s%02d*%02d#" % (sign, deg, arcmin)


def lon_format(lon, high_precision=True):
    remain = abs(lon - int(lon))
    arcmin = int(remain * 60)
    arcsec = (remain - (arcmin / 60.0)) * 60 * 60
    deg = int(abs(lon))
    sign = "+" if lon > 0 else "-"
    if high_precision:
        return "%s%03d*%02d'%02d#" % (sign, deg, arcmin, arcsec)
    else:
        return "%s%03d*%02d#" % (sign, deg, arcmin)


def az_format(az, high_precision=True):
    remain = abs(az - int(az))
    arcmin = int(remain * 60)
    arcsec = (remain - (arcmin / 60.0)) * 60 * 60
    deg = int(az)
    if high_precision:
        return "%03d*%02d'%02d#" % (deg, arcmin, arcsec)
    else:
        return "%03d*%02d#" % (deg, arcmin)


def ra_to_deg(hours, minutes, seconds=0.0):
    return (hours + minutes / 60.0 + seconds / 3600.0) * (360.0 / 24.0)


def dec_to_deg(sign, deg, minutes, seconds=0.0):
    deg = abs(deg)
    if DEBUG_PROT:
        print(deg, minutes, seconds, (deg + minutes / 60 + seconds / 3600))
    return sign * (deg + minutes / 60.0 + seconds / 3600.0)


class LX200Client:
    def __init__(self, socket_conn, client_address):
        self.client_id = str(uuid.uuid4())
        self.socket = socket_conn
        self.client_address = client_address
        self.buf = ""
        self.is_highprecision = False
        # self.re_autostar_settime_cmd = re.compile(":hI\\d{12}#")
        # self.re_select_ds_libary_cmd = re.compile(":Lo\\d#")
        # self.re_select_s_libary_cmd = re.compile(":Ls\\d#")

        self.re_guide_telescope = re.compile(":Mg([nsew])(\\d{4})#")
        # self.re_slew_telescope = re.compile(':M([nsew])#')

        # self.re_ra_rate_deg_cmd = re.compile(':RA(\\d\\d\\.\\d)#')
        # self.re_dec_rate_deg_cmd = re.compile(':RE(\\d\\d\\.\\d)#')

        self.re_set_target_object_alt = re.compile(":Sa([-+])(\\d\\d)[:*](\\d\\d)#")
        self.re_set_target_object_alt_hp = re.compile(
            ":Sa([-+])(\\d\\d)[:*](\\d\\d)[:'](\\d\\d)#"
        )

        # self.re_set_bright_limit = re.compile(':Sb([-+])(\\d\\d\\.\\d)#')
        # self.re_set_baud_rate = re.compile(':SB\\d#')

        self.re_set_handbox_date = re.compile(":SC ?(\\d\\d)/(\\d\\d)/(\\d\\d)#")

        self.re_set_target_obj_dec = re.compile(":Sd ?([-+])(\\d\\d)[:*](\\d\\d)#")
        self.re_set_target_obj_dec_hp = re.compile(
            ":Sd ?([-+])(\\d\\d)[:*](\\d\\d):(\\d+(\\.\\d+)?)#"
        )

        # self.re_set_selenographic_lat_moon = re.compile(':SEs(\\d\\d)\\*(\\d\\d)#')
        # self.re_set_selenographic_lon_moon = re.compile(':Ses(\\d\\d)\\*(\\d\\d)#')

        # self.re_set_faint_mag = re.compile(':Sf([-+])(\\d\\d\\.\\d)#')

        # self.re_set_field_diameter = re.compile(':SF(\\d\\d\\d)#')

        self.re_set_site_long = re.compile(":Sg([-+]?\\d+)[:*](\\d+)#")

        self.re_set_site_hours_add_utc = re.compile(":SG ?([-+])?(\\d+(\\.\\d+)?)#")
        self.re_set_dst = re.compile(":SH(\\d)#")

        # self.re_set_max_object_elevation = re.compile(':Sh(\\d\\d)#')
        # self.re_set_size_of_smallest_object = re.compile(':Sl(\\d\\d\\d)#')

        self.re_set_local_time = re.compile(":SL ?(\\d\\d):(\\d\\d):(\\d\\d)#")

        self.re_set_site_name = re.compile(":S([MNOP])(.+)#")

        self.re_set_altitude_low_limit = re.compile(":So(\\d\\d)\\*#")

        # self.re_set_backlash_home_sensor = re.compile(':Sp[BHS].*#')

        self.re_set_target_object_ra = re.compile(":Sr ?(\\d+):(\\d+\\.\\d+)#")
        self.re_set_target_object_ra_hp = re.compile(
            ":Sr ?(\\d+):(\\d+):(\\d+(\\.\\d+)?)#"
        )

        # self.re_set_largest_find = re.compile(':Ss(\\d\\d\\d)#')

        # self.re_set_local_sidereal_time = re.compile(':SS(\\d\\d):(\\d\\d):(\\d\\d)#')

        self.re_set_current_site_latitude = re.compile(":St([-+])(\\d\\d)[:*](\\d\\d)#")
        self.re_set_current_site_latitude_hp = re.compile(
            ":St([-+])(\\d\\d)[:*](\\d\\d)[:*](\\d\\d)#"
        )

        # self.re_set_current_tracking_rate = re.compile(':ST(\\d{4}\\.\\d{7})#')

        self.re_set_max_slew_degrees = re.compile(":Sw(\\d)#")
        self.re_set_target_azimuth = re.compile(":Sz(\\d\\d\\d)\\*(\\d\\d)#")

        # self.re_dec_pec_table_entry = re.compile(':VD(\\d{4})#')

        self.re_site_select = re.compile(":W(\\d)#")

        self.utc_offset = None

    def read(self):
        try:
            cmdbuf = ""
            while not kill:
                b = self.socket.recv(1024)
                # print('read2', b)
                if len(b) == 0:
                    # print('Socket done')
                    return
                buffer = b.decode("utf8").strip()
                # if DEBUG_PROT:
                #    print("Buffer ", buffer)
                for i in range(len(buffer)):
                    c = buffer[i]
                    if c == "\x06":  # Alignment Query
                        self.write(b"P")
                        continue
                    if len(cmdbuf) == 0 and c == ":":
                        cmdbuf = ":"
                    elif len(cmdbuf) > 0:
                        cmdbuf += c
                    if len(cmdbuf) > 2 and c == "#":
                        if DEBUG_PROT:
                            t = time.time()
                            print("Process: ", cmdbuf)
                        self.process(cmdbuf)
                        cmdbuf = ""
                        if DEBUG_PROT:
                            print("Process time:", time.time() - t)
                if len(cmdbuf) > 1024:
                    cmdbuf = ""
        except KeyboardInterrupt:
            raise
        except:
            traceback.print_exc()

    def process(self, cmd):
        global \
            set_utc_offset, \
            localtime_daylight_savings, \
            slew_speed, \
            target, \
            slew_intervals, \
            slewing_time_buffer
        # print('process', cmd)
        control.set_alive(self.client_id)
        if cmd == ":Aa#":  # Start automatic alignment sequence
            self.write(b"0")
        elif cmd == ":CM#":
            # Sychronize with current selected object coords PRIORITY DONE
            if target["ra"] and target["dec"]:
                control.set_sync(ra=target["ra"], dec=target["dec"], frame="tete")
                self.write(b"M31 EX GAL MAG 3.5 SZ178.0'#")
            elif target["alt"] and target["az"]:
                control.set_sync(alt=target["alt"], dec=target["az"], frame="altaz")
                self.write(b"M31 EX GAL MAG 3.5 SZ178.0'#")
            else:
                print("!!UNHANDLED CMD: ", cmd, file=sys.stderr)
        elif cmd[1] == "D":  # PRIORITY
            # If slewing hashes till how close we are? 0-8 #
            # Check three sources to avoid false "not slewing" reports:
            #   slewing_time_buffer: bridges the gap between :MS# and the slew
            #     thread setting control.slewing = True
            #   control.slewing: live flag set by the slew thread (no 1s delay)
            #   control.last_status["slewing"]: status snapshot updated every ~1s
            if slewing_time_buffer or control.slewing or control.last_status["slewing"]:
                self.write(b"\x7f\x7f#")
            else:
                self.write(b"#")  # or is it b'' ?
        elif cmd == ":FB#":  # Query focus busy status
            self.write(b"0")
        elif cmd[1] == "G":
            if cmd == ":Ga#":  # Get Local Telescope Time in 12 Hour Format
                # self.write(b'HH:MM:SS#')
                self.write(
                    pendulum.now(tz=set_utc_offset).strftime("%I:%M:%S#").encode()
                )
            elif cmd == ":GA#":  # Get Telescope Altitude
                # self.write(b'sDD*MM\'SS#')
                self.write(
                    dec_format(
                        control.last_status["alt"], self.is_highprecision
                    ).encode()
                )
            elif cmd == ":Gb#":  # Browser Brighter Mag Limit
                self.write(b"s10.1#")
            elif cmd == ":GC#":  # Get current date PRIORITY DONE
                # self.write(b'MM/DD/YY#')
                self.write(
                    pendulum.now(tz=set_utc_offset).strftime("%m/%d/%y#").encode()
                )
            elif cmd == ":Gc#":  # Telescope clock format
                self.write(b"24#")
            elif cmd == ":GD#":  # Telescope Declination PRIORITY DONE
                # self.write(b'sDD*MM\'SS#')
                reply = dec_format(
                    control.last_status["tete_dec"], self.is_highprecision
                ).encode()
                if DEBUG_PROT:
                    print("Reply ", reply)
                self.write(reply)
            elif cmd == ":Gd#":  # Currently selected target dec
                # TODO: Get slewto object
                self.write(b"sDD*MM'SS#")
            elif cmd == ":GE#":  # Get selnographic Latitude
                self.write(b"+999*99#")
            elif cmd == ":GF#":  # Get find field diameter
                self.write(b"100#")
            elif cmd == ":Gf#":  # browser faint mag limit
                self.write(b"s10.1#")
            elif cmd == ":GG#":  # utc offset time PRIORITY DONE
                # self.write(b'sHH.H#')
                s = ""
                if set_utc_offset > 0:
                    s = "+"
                if set_utc_offset.is_integer():
                    self.write(
                        (
                            "%s%02d#"
                            % (
                                s,
                                int(set_utc_offset),
                            )
                        ).encode()
                    )
                else:
                    self.write(
                        (
                            "%s%04.1f#"
                            % (
                                s,
                                set_utc_offset,
                            )
                        ).encode()
                    )
            elif cmd == ":Gg#":  # currente site longitude PRIORITY DONE
                # TODO: dec says east should be negative, is that true?
                # self.write(b'sDDD*MM#')
                lon = settings.runtime_settings["earth_location"].lon.deg
                # lon = -lon                 # if east should be negative
                # TODO: Can be high precision?
                self.write(lon_format(lon, False).encode())
            elif cmd == ":GH#":  # Daylight savings time setting
                # TODO: The settings of actual dst?
                self.write(b"1#")
            elif cmd == ":Gh#":  # High limit
                # self.write(b'sDD*')
                self.write(b"+90*")
            elif cmd == ":GL#":  # time 24 hour format PRIORITY DONE
                # self.write(b'HH:MM:SS#')
                self.write(
                    pendulum.now(tz=set_utc_offset).strftime("%H:%M:%S#").encode()
                )
            elif cmd == ":Gm#":  # distance to meridian
                self.write(b"sDD*MM'SS#")
            elif cmd == ":Gl#":  # search Large size limit
                self.write(b"100'#")
            elif cmd == ":GM#":  # Get Site 1 Name PRIORITY DONE?
                self.write(b"site1#")
            elif cmd == ":GN#":  # Get Site 2 name
                self.write(b"site2#")
            elif cmd == ":GO#":  # Get Site 3 name
                self.write(b"site3#")
            elif cmd == ":GP#":  # Get site 4 name
                self.write(b"site4#")
            elif cmd == ":Go#":  # Lower altitude limit
                self.write(b"00*#")
            elif cmd == ":Gq#":  # min quality for find
                self.write(b"SU#")
            elif cmd == ":GR#":  # telescope RA PRIORITY DONE
                # self.write(b'HH:MM:SS#')
                control.set_alive(self.client_id)
                reply = ra_format(
                    control.last_status["tete_ra"], self.is_highprecision
                ).encode()
                if DEBUG_PROT:
                    print("Reply ", reply)
                self.write(reply)
            elif cmd == ":Gr#":  # current target RA
                self.write(b"HH:MM:SS#")
            elif cmd == ":GS#":  # get sidereal time
                self.write(b"HH:MM:SS#")
            elif cmd == ":Gs#":  # smaller size limit returned by find
                self.write(b"100'#")
            elif cmd == ":GT#":  # Tracking rate in hz #PRIORITY DONE
                self.write(b"59.8#")
            elif cmd == ":Gt#":  # current site latitude # PRIORITY DONE
                # self.write(b'sDD*MM#') s is sign
                lat = settings.runtime_settings["earth_location"].lat.deg
                self.write(dec_format(lat, False).encode())
            elif cmd == ":GVD#":  # telescope firmware date
                self.write((control.version_date_str + "#").encode())
            elif cmd == ":GVN#":  # firmware number
                self.write((control.version_short + "#").encode())
            elif cmd == ":GVP#":  # Telescope product name
                self.write(b"SSTEQ25#")
            elif cmd == ":GVT#":  # telescope firmware time
                self.write(b"01:00:00#")
            elif cmd == ":GVF#":  # telescope firmware full
                self.write(("SSTEQ25 " + control.version + "#").encode())
            elif cmd == ":GW#":  # Scope alignment status
                # <mount><tracking><alignment>#
                # P - equatorial
                # T - tracking, N - not tracking
                # 0 - needs alignement, 1 - one star, 2 - two star, 3 - three stared
                self.write(b"PT0#")
            elif cmd == ":Gy#":  # objects returned by find/browse
                self.write(b"gpdco#")
            elif cmd == ":GZ#":  # Get telescope azimuth
                # self.write(b'DDD*MM\'SS#')
                self.write(
                    az_format(control.last_status["az"], self.is_highprecision).encode()
                )
            else:
                print("!!UNHANDLED CMD: ", cmd, file=sys.stderr)
        elif cmd[1] == "h":
            # if cmd == ':hN#':  # autostar sleep scope
            if cmd == ":hP#":  # slew to park position
                control.park_scope()
                slew_commanded()
            elif cmd == ":hS#":  # set current position as park position
                control.set_park_position_here()
            elif cmd == ":hW#":  # autostar wake up scope
                control.start_tracking()
            elif cmd == ":h?#":  # autostar query home status
                self.write(b"0")
            elif cmd[2] == "I":
                # m = self.re_autostar_settime_cmd.match(cmd)  # Autostar settime
                self.write(b"1")
            else:
                print("!!UNHANDLED CMD: ", cmd, file=sys.stderr)

        # :H#'  toggle 24 and 12 hour time format
        # :I#  # stop and restart scope -- kstars unpark
        elif cmd == ":I#":
            # TODO: Need to do more for kstars to know we are unparked.
            # self.process(':Q#')
            control.start_tracking()
            # self.write(b'0')
        elif cmd[1] == "L":
            # :LB# :LCNNNN# :LF#
            if cmd == ":Lf#":
                self.write(b"0#")
            elif cmd == ":LI#":
                self.write(b"NOTHING#")
            # :LMNNNN# :LN# :LoD#
            elif cmd[2] == "o":
                # m = self.re_select_ds_libary_cmd.match(cmd)
                self.write(b"0")
            elif cmd[2] == "s":
                # m = self.re_select_s_libary_cmd.match(cmd)
                self.write(b"2")
            else:
                print("!!UNHANDLED CMD: ", cmd, file=sys.stderr)
            # :LSNNNN#
        elif cmd[1] == "M":
            if cmd == "#MA#":  # Slew to target alt az
                self.write(b"0")
            elif cmd == ":MS#":  # slew to target object PRIORITY DONE
                # 0 slew is possible, 1<string># object below string, 2<string># object higher
                try:
                    if target["ra"] and target["dec"]:
                        control.set_slew(
                            ra=target["ra"], dec=target["dec"], frame="tete"
                        )
                        slew_commanded()
                    elif target["alt"] and target["az"]:
                        control.set_slew(
                            alt=target["alt"], az=target["az"], frame="altaz"
                        )
                        slew_commanded()
                    else:
                        self.write(b"1Unable to slew#")
                        return
                    self.write(b"0")
                except Exception:
                    traceback.print_exc()
                    self.write(b"1Unable to slew#")
            elif cmd[2] == "g":  # PRIORITY2
                # move guide telescope
                m = self.re_guide_telescope.match(cmd)
                direction = m.group(1)
                time_ms = m.group(2)
                control.guide_control(direction, int(time_ms))
            elif cmd[2] in ["n", "s", "e", "w"]:  # PRIORITY DONE
                # slew
                # Set interval
                # print('LX200 Manual Slew', slew_speed)
                if slew_intervals[cmd[2]]:
                    slew_intervals[cmd[2]].cancel()
                control.set_alive(self.client_id)
                control.manual_control(
                    manual_slew_map[cmd[2]], slew_speed, self.client_id
                )
            else:
                print("!!UNHANDLED CMD: ", cmd, file=sys.stderr)
        elif cmd == ":P#":
            self.write(b"LOW PRECISION")
        elif cmd[1] == "Q":
            # :$Q# :$QA+# :$QA-#
            if cmd == ":$QC#":
                self.write(b"00000#")
            # :$QGNNNNN# :$QP<p><n><n># :$QS+# :$QS-# :$QU+# :$QU-# :$QV+# :$QV-#
            elif cmd == ":$QW#":  # Write mount model to non-volatile memory
                self.write(b"0")
            # :$QZ+# :$QZ-#
            elif cmd[2] == "#":  # Halt all slewing PRIORITY DONE
                for d in ["n", "w", "s", "e"]:
                    if slew_intervals[d]:
                        slew_intervals[d].cancel()
                        slew_intervals[d] = None
                        control.manual_control(manual_slew_map[d], None, self.client_id)
                control.cancel_slews()
            elif cmd[2] in [
                "e",
                "n",
                "w",
                "s",
            ]:  # halt slew by direction # PRIORITY DONE
                if slew_intervals[cmd[2]]:
                    slew_intervals[cmd[2]].cancel()
                    slew_intervals[cmd[2]] = None
                control.manual_control(manual_slew_map[cmd[2]], None, self.client_id)
            else:
                print("!!UNHANDLED CMD: ", cmd, file=sys.stderr)
        # rotators :r+# :r-# :rn# :rh# :rC# :rc# :rq#
        elif cmd[1] == "R":
            # slew rate
            if cmd[2] in ["G", "C", "M", "S"]:  # Set guiding rate PRIORITY DONE
                slew_speed = slew_speed_map[cmd[2]]
            elif cmd[2] == "A":
                # m = self.re_ra_rate_deg_cmd.match(cmd)
                # dps = m.group(1)
                pass
            elif cmd[2] == "E":
                # m = self.re_dec_rate_deg_cmd.match(cmd)
                # dps = m.group(1)
                pass
            else:
                print("!!UNHANDLED CMD: ", cmd, file=sys.stderr)
            # set guide rate :RgSS.S#
        # Telescope set commands
        elif cmd[1] == "S":
            if cmd[2] == "a":  # PRIORITY2 DONE
                if self.re_set_target_object_alt_hp.match(
                    cmd
                ):  # high precision set target object
                    m = self.re_set_target_object_alt_hp.match(cmd)
                    sign = -1.0 if m.group(1) == "-" else 1.0
                    deg = m.group(2)
                    minute = m.group(3)
                    seconds = m.group(4)
                    target["ra"] = None
                    target["dec"] = None
                    target["alt"] = dec_to_deg(
                        sign, float(deg), float(minute), float(seconds)
                    )
                    self.write(b"1")
                elif self.re_set_target_object_alt.match(
                    cmd
                ):  # low precision set target object
                    m = self.re_set_target_object_alt.match(cmd)
                    sign = -1.0 if m.group(1) == "-" else 1.0
                    deg = m.group(2)
                    minute = m.group(3)
                    target["ra"] = None
                    target["dec"] = None
                    target["alt"] = dec_to_deg(sign, float(deg), float(minute))
                    self.write(b"1")
            elif cmd[2] == "b":
                # m = self.re_set_bright_limit.match(cmd)
                self.write(b"0")
            elif cmd[2] == "B":
                # m = self.re_set_baud_rate.match(cmd):
                self.write(b"1")
            elif cmd[2] == "C":
                m = self.re_set_handbox_date.match(cmd)
                month = int(m.group(1))
                day = int(m.group(2))
                year = int("20" + m.group(3))  # YY

                if not use_holders:
                    dstr = (
                        pendulum.now(tz=set_utc_offset)
                        .set(year=year, month=month, day=day)
                        .isoformat()
                    )
                    r = control.set_time(dstr)
                else:
                    r = set_time(year=year, month=month, day=day)
                if r[0]:
                    self.write(b"1Updating Planetary Data#                       #")
                else:
                    self.write("b0")
            elif cmd[2] == "d":  # PRIORITY DONE
                m = self.re_set_target_obj_dec_hp.match(cmd)
                if m:
                    sign = -1 if m.group(1) == "-" else 1.0
                    deg = m.group(2)
                    minutes = m.group(3)
                    seconds = m.group(4)
                    target["dec"] = dec_to_deg(
                        sign, float(deg), float(minutes), float(seconds)
                    )
                    target["alt"] = None
                    target["az"] = None
                    self.write(b"1")  # 0 if not accepted/valid
                else:
                    m = self.re_set_target_obj_dec.match(cmd)
                    sign = -1 if m.group(1) == "-" else 1.0
                    deg = m.group(2)
                    minutes = m.group(3)
                    target["dec"] = dec_to_deg(sign, float(deg), float(minutes))
                    target["alt"] = None
                    target["az"] = None
                    self.write(b"1")  # 0 if not accepted/valid
            elif cmd[2] == "E" or cmd[2] == "e":
                # m = self.re_set_selenographic_lat_moon.match(cmd)
                # m = self.re_set_selenographic_lon_moon.match(cmd):
                self.write(b"0")
            elif cmd[2] == "f":
                # m = self.re_set_faint_mag.match(cmd)
                self.write(b"1")
            elif cmd[2] == "F":
                # m = self.re_set_field_diameter.match(cmd)
                self.write(b"0")
            elif cmd[2] == "g":  # PRIORITY DONE
                m = self.re_set_site_long.match(cmd)
                deg = m.group(1)
                minutes = m.group(2)

                lon = dec_to_deg(1.0, float(deg), float(minutes))
                if lon > 180:
                    lon = 360.0 - 180
                else:
                    lon = -lon
                # print('LX200: Set Long', lon)
                try:
                    if not use_holders:
                        control.set_location(
                            settings.runtime_settings["earth_location"].lat.deg,
                            lon,
                            1000.0,
                            "site1",
                        )
                    else:
                        set_location(lon=lon)
                    self.write(b"1")
                except Exception:
                    traceback.print_exc()
                    self.write(b"0")
            elif cmd[2] == "G":  # PRIORITY
                m = self.re_set_site_hours_add_utc.match(cmd)
                sign = m.group(1)  # + or -
                hours = m.group(2)
                # They give us hours added to localtime to get UTC, so neg is positive for offset
                offset = float(hours) * (1.0 if sign == "-" else -1.0)
                doffset = set_utc_offset - offset
                if not use_holders:
                    dstr = pendulum.now().add(hours=doffset).isoformat()
                    r = control.set_time(dstr)
                else:
                    r = set_time(offset=offset)
                if r[0]:
                    set_utc_offset = offset
                    self.write(b"1")
                else:
                    self.write(b"0")
            elif cmd[2] == "H":
                m = self.re_set_dst.match(cmd)
                dst_enabled = m.group(1) == "1"
                localtime_daylight_savings = dst_enabled
                # TODO: Should this adjust localtime or utc_offset any?
                self.write(b"1")
            elif cmd[2] == "h" or cmd[2] == "l":
                # self.re_set_max_object_elevation.match(cmd)
                # self.re_set_size_of_smallest_object.match(cmd):
                self.write(b"0")
            elif cmd[2] == "L":  # PRIORITY DONE
                m = self.re_set_local_time.match(cmd)
                hour = int(m.group(1))
                minute = int(m.group(2))
                second = int(m.group(3))
                # print('Trying to set time')

                if not use_holders:
                    dstr = (
                        pendulum.now(tz=set_utc_offset)
                        .set(hour=hour, minute=minute, second=second)
                        .isoformat()
                    )
                    r = control.set_time(dstr)
                else:
                    r = set_time(hour=hour, minute=minute, second=second)
                if r[0]:
                    self.write(b"1")
                else:
                    self.write(b"0")
            # flexure correction :SM+# Sm-#
            elif cmd[2] in ["M", "N", "O", "P"]:
                m = self.re_set_site_name.match(cmd)
                site = m.group(1)  # M = site1, N=site2, O=site3, P = site4
                name = m.group(2)
                self.write(b"1")
            elif cmd[2] == "o":
                m = self.re_set_altitude_low_limit.match(cmd)
                alt = m.group(1)
                self.write(b"1")
            # Backlash :SpB<num><num>#, Home data :SpH<num><num>#, sensor offset :SpS<num><num><num>#
            elif cmd[2] == "p":
                # m = self.re_set_backlash_home_sensor.match(cmd)
                self.write(b"1")
            # :Sq#
            elif cmd[2] == "r":  # PRIORITY DONE
                m = self.re_set_target_object_ra_hp.match(cmd)
                if m:
                    hour = m.group(1)
                    minutes = m.group(2)
                    seconds = m.group(3)
                    target["ra"] = ra_to_deg(
                        float(hour), float(minutes), float(seconds)
                    )
                    target["alt"] = None
                    target["az"] = None
                    self.write(b"1")
                else:
                    m = self.re_set_target_object_ra.match(cmd)
                    hour = m.group(1)
                    minutes = m.group(2)
                    target["ra"] = ra_to_deg(float(hour), float(minutes))
                    target["alt"] = None
                    target["az"] = None
                    self.write(b"1")
            elif cmd[2] == "s":
                # m = self.re_set_largest_find.match(cmd)
                self.write(b"1")
            elif cmd[2] == "S":  # PRIORITY 3?
                # m = self.re_set_local_sidereal_time.match(cmd)
                # hour = m.group(1)
                # minute = m.group(2)
                # second = m.group(3)
                self.write(b"0")
            elif cmd[2] == "t":  # PRIORITY DONE
                m = self.re_set_current_site_latitude_hp.match(cmd)
                if m:
                    sign = -1 if m.group(1) == "-" else 1.0
                    deg = m.group(2)
                    minute = m.group(3)
                    seconds = m.group(4)
                else:
                    m = self.re_set_current_site_latitude.match(cmd)
                    sign = -1 if m.group(1) == "-" else 1.0
                    deg = m.group(2)
                    minute = m.group(3)
                    seconds = 0.0
                try:
                    lat = dec_to_deg(sign, float(deg), float(minute), float(seconds))
                    # print('Set lat:', lat)
                    if not use_holders:
                        control.set_location(
                            lat,
                            settings.runtime_settings["earth_location"].lon.deg,
                            1000.0,
                            "site1",
                        )
                    else:
                        set_location(lat=lat)
                    self.write(b"1")
                except Exception:
                    traceback.print_exc()
                    self.write(b"0")

            elif cmd[2] == "T":
                # m = self.re_set_current_tracking_rate.match(cmd)
                self.write(b"0")  # 0 invalid, 2 valid
            # increment rate, smart drive :ST+#, ST-#, STA- :STA+, :STZ-, :STZ+
            elif cmd[2] == "w":
                m = self.re_set_max_slew_degrees.match(cmd)
                deg = m.group(1)  # expect 2 through 8
                self.write(b"1")
            elif cmd == ":SyGPDCO#":
                self.write(b"0")
            elif cmd[2] == "z":
                m = self.re_set_target_azimuth.match(cmd)
                deg = m.group(1)
                minutes = m.group(2)
                self.write(b"1")
            else:
                print("!!UNHANDLED CMD: ", cmd, file=sys.stderr)
        # inc dec tracking :T+# :T-#, set lunar tracking :TL# custom tracking :TM#, sidereal tracking :TS#
        # toggle between high low precision positions :U#
        elif cmd == ":U#":
            self.is_highprecision = not self.is_highprecision
        elif cmd[1:3] == "VD":
            # m = self.re_dec_pec_table_entry.match(cmd)
            self.write(b"0.0000")
        elif cmd[1] == "W":
            m = self.re_site_select.match(cmd)
            site = m.group(1)  # 1 through 4
        elif cmd in [":??#", ":?+#", ":?-#"]:
            self.write(b"HelpText#")
        else:
            print("!!UNHANDLED CMD: ", cmd, file=sys.stderr)

    def write(self, data):
        self.socket.send(data)

    def fileno(self):
        return self.socket.fileno()

    def disconnect(self):
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except:
            traceback.print_exc()


def terminate():
    global kill
    kill = True


def main():
    global kill
    print("Starting LX200 Protocol server")
    oursocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    oursocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    oursocket.bind(("", ourport))
    oursocket.listen(5)
    count = 0
    try:
        while not kill:
            print("Before Accept")
            conn, addr = oursocket.accept()
            # Disable Nagle's algorithm so responses are sent immediately.
            # Critical for low-latency request/response protocols like LX200.
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            lx200Clients[count] = {"client": LX200Client(conn, addr), "thread": None}
            print(
                "New LX200 Proto client " + str(conn.fileno()) + " on port " + str(addr)
            )
            lx200Clients[count]["thread"] = threading.Thread(
                target=lx200Clients[count]["client"].read
            )
            lx200Clients[count]["thread"].start()
            count += 1
    except KeyboardInterrupt:
        print("Keyboard quiting")
        kill = True
    except:
        traceback.print_exc()

    oursocket.shutdown(socket.SHUT_RDWR)
    oursocket.close()
