from astropy.coordinates import AltAz, ICRS, TETE, Longitude
from astropy.time import Time as AstroTime

import astropy.units as u
import astropy.units.si as usi

import settings
import skyconv_hadec
from skyconv_hadec import HADec
import typing
import pointing_model

model_real_stepper: typing.Union[None, pointing_model.PointingModelBuie, pointing_model.PointingModelAffine] = None

ALT_ATM_THRESHOLD = 6


def get_sidereal_time(obstime=None):
    """
    Get sidereal time (meridian ra) at a particular time (JNow).
    :param obstime:
    :type obstime: astropy.time.Time
    :return: meridian ra
    :rtype: Longitude
    """
    if not obstime:
        obstime = AstroTime.now()
    # We don't use astropy.time.Time.sidereal_time because it needs to have update iers tables
    frame_args = get_frame_init_args('altaz', obstime=obstime)
    return _altaz_to_tete(AltAz(alt=90.0 * u.deg, az=0 * u.deg, **frame_args))[0].ra


def _icrs_to_hadec(icrs_coord, obstime=None, pressure=None):
    """
    Transforms icrs coordinate to hadec.
    :param icrs_coord: The RADEC ICRS coordinate
    :param obstime: Observations time to get hadec
    :param pressure: If none uses pression from earth location
    :return: (hadec coordinate, bool if used atmospheric refraction)
    :rtype: (HADec, bool)
    """
    # If we are in low altitude we want to disable atmospheric refraction compensation
    if pressure is None:
        altaz, atm = _icrs_to_altaz(icrs_coord, obstime=obstime, pressure=0 * u.hPa)
        if not atm:
            pressure = 0 * u.hPa
    else:
        atm = int(pressure.value) != 0
    frame_args = get_frame_init_args('hadec', obstime=obstime, pressure=pressure)
    icrs_coord = skyconv_hadec.icrs_to_hadec(icrs_coord, skyconv_hadec.HADec(**frame_args))
    return icrs_coord, atm


def _altaz_to_hadec(altaz_coord):
    """
    Convert altaz coordinate to hadec.
    :return: (hadec coordinate, bool if used atmospheric refraction)
    :rtype: (HADec, bool)
    """
    # HADec to altaz should be direct conversion, refraction shouldn't matter
    # ICRS is just a intermediate, using pressure 0 for stability
    new_altaz_coord = _altaz_threshold_fix_pressure(altaz_coord)
    icrs, atm = _altaz_to_icrs(new_altaz_coord)
    hadec_coord = _icrs_to_hadec(icrs, obstime=altaz_coord.obstime, pressure=0 * u.hPa)[0]
    if altaz_coord.alt.deg > ALT_ATM_THRESHOLD and int(altaz_coord.pressure.value) > 0:
        frame_args = get_frame_init_args('hadec', frame_copy=hadec_coord)
        hadec_coord = skyconv_hadec.HADec(ha=hadec_coord.ha, dec=hadec_coord.dec, **frame_args)
    return hadec_coord, int(hadec_coord.pressure.value) != 0


def get_frame_init_args(frame, obstime=None, frame_copy=None, pressure=None):
    """
    Get some intial coordinate frame arguments.
    :param frame: Name of the frame to make arguments for.
    :type frame: str
    :param obstime: Observation time to set in frame
    :type obstime: AstroTime
    :param frame_copy: Frame to copy instead of using arguments or defaults.
    :param pressure: If none uses location
    :rtype: u.Quantity
    :return: Dictionary of coordinate frame arguments
    :rtype: dict
    """
    ret = {'location': settings.runtime_settings['earth_location'], 'obstime': obstime}
    if ret['obstime'] is None:
        ret['obstime'] = AstroTime.now()
    if frame == 'altaz' or frame == 'hadec':
        if pressure is None:
            ret['pressure'] = _earth_location_to_pressure(ret['location'])
        else:
            ret['pressure'] = pressure
        ret['obswl'] = 540 * u.nm
        ret['temperature'] = 20 * u.deg_C
        ret['relative_humidity'] = 0.35
    if frame_copy:
        for key in ret.keys():
            if hasattr(frame_copy, key):
                ret[key] = getattr(frame_copy, key)
    return ret


def _hadec_to_icrs(hadec_coord, pressure=None):
    """
    HADec to ICRS RADec
    :param hadec_coord:  The HADec coord
    :type hadec_coord: HADec
    :param pressure: A pressure to useduring conversion, if none uses hadec_coord.pressure.
    :type: pressure: u.Quantity
    :return: (ICRS coordinate, if atm refraction used)
    :rtype: (ICRS, bool)
    """
    # HADec to altaz should be direct conversion, refraction shouldn't matter
    atm = True
    new_hadec_coord = hadec_coord
    if pressure is None and int(hadec_coord.pressure.value) != 0:
        altaz = _hadec_to_altaz(hadec_coord)[0]
        if altaz.alt.deg <= ALT_ATM_THRESHOLD:
            atm = False
    else:
        atm = False
    if not atm:
        frame_args = get_frame_init_args('hadec', frame_copy=hadec_coord)
        frame_args['pressure'] = 0 * u.hPa
        new_hadec_coord = skyconv_hadec.HADec(ha=hadec_coord.ha, dec=hadec_coord.dec, **frame_args)
    return skyconv_hadec.hadec_to_icrs(new_hadec_coord, ICRS()), atm


def _hadec_to_altaz(hadec_coord):
    """
    HADec to AltAz coordinate.
    :param hadec_coord: HADec coord to convert.
    :type hadec_coord: HADec
    :return: (AltAz coordinate, if atm refraction used)
    :rtype: (AltAz, bool)
    """
    # HADec to altaz should be direct conversion, refraction shouldn't matter
    if int(hadec_coord.pressure.value) != 0:
        frame_args = get_frame_init_args('hadec', frame_copy=hadec_coord)
        frame_args['pressure'] = 0 * u.hPa
        new_hadec_coord = skyconv_hadec.HADec(ha=hadec_coord.ha, dec=hadec_coord.dec, **frame_args)
    else:
        new_hadec_coord = hadec_coord
    # ICRS is just intermediate pressure doesn't matter.
    icrs = _hadec_to_icrs(new_hadec_coord, pressure=0 * u.hPa)[0]
    altaz = _icrs_to_altaz(icrs, obstime=hadec_coord.obstime, pressure=0 * u.hPa)[0]
    if altaz.alt.deg > ALT_ATM_THRESHOLD and int(hadec_coord.pressure.value) > 0:
        frame_args = get_frame_init_args('altaz', frame_copy=hadec_coord)
        altaz = AltAz(alt=altaz.alt, az=altaz.az, **frame_args)
    return altaz, altaz.pressure.value != 0


def _ha_delta_deg(started_angle, end_angle):
    """
    Finds the degree difference between two angles ang1-ang2, then returns shortest side that will take you
    there - or +.
    :param started_angle: First angle
    :type started_angle: float
    :param end_angle: Second angle
    :type end_angle: float
    :return: The shortest difference between started_angle and end_angle.
    :rtype: float
    """
    end_angle = _clean_deg(end_angle)
    started_angle = _clean_deg(started_angle)

    d_1 = end_angle - started_angle
    d_2 = 360.0 + d_1
    d_3 = d_1 - 360

    return min([d_1, d_2, d_3], key=abs)


def _hadec_to_steps(hadec_coord, sync_info=None, ha_steps_per_degree=None, dec_steps_per_degree=None,
                    model_transform=False):
    """
    Takes HaDec coord and converts it to steps.
    :param hadec_coord:
    :type hadec_coord: HADec
    :param sync_info:
    :type sync_info: dict
    :param ha_steps_per_degree:
    :param dec_steps_per_degree:
    :param model_transform: If should use transform coordinate using model.
    :return: {'ha': Step counts get to disired HA, 'dec': Step counts to get to desired Dec}
    :rtype: dict
    """
    if not sync_info:
        sync_info = settings.runtime_settings['sync_info']
    if not ha_steps_per_degree:
        ha_steps_per_degree = settings.settings['ra_ticks_per_degree']
    if not dec_steps_per_degree:
        dec_steps_per_degree = settings.settings['dec_ticks_per_degree']
    if model_transform:
        hadec_coord = model_real_stepper.transform_point(hadec_coord)
    # TODO: Do we neeed something like ra_deg_d? Or stop it from twisting even with tracking?
    #  How does this affect the model?
    # d_ha = ha_dec_coord.ra.deg - sync_info['coord'].ha.deg
    d_ha = _ha_delta_deg(sync_info['coord'].ha.deg, hadec_coord.ha.deg)
    d_dec = hadec_coord.dec.deg - sync_info['coord'].dec.deg

    steps_ha = sync_info['steps']['ha'] + (d_ha * ha_steps_per_degree)
    steps_dec = sync_info['steps']['dec'] + (d_dec * dec_steps_per_degree)
    return {'ha': steps_ha, 'dec': steps_dec}


def _altaz_threshold_fix_pressure(altaz_coord):
    """
    Makes a new coordinate if alt is less than ALT_ATM_THRESHOLD that has no pressure in frame.
    :param altaz_coord: The coordinate to check
    :return: The original coordinate or a new one with pressure set to zero.
    :rtype: AltAz
    """
    new_altaz_coord = altaz_coord
    if altaz_coord.alt.deg <= ALT_ATM_THRESHOLD and int(altaz_coord.pressure.value) != 0:
        frame_args = get_frame_init_args('altaz', frame_copy=altaz_coord)
        frame_args['pressure'] = 0 * u.hPa
        new_altaz_coord = AltAz(alt=altaz_coord.alt, az=altaz_coord.az, **frame_args)
    return new_altaz_coord


def _altaz_to_icrs(altaz_coord):
    """
    Converts an AltAz coordinate to ICRS coordinate.
    :param altaz_coord: coordinate to convert
    :type altaz_coord: AltAz
    :return: (coordinate in ICRS, if atm refraction was used in conversion)
    :rtype: (ICRS, bool)
    """
    new_altaz_coord = _altaz_threshold_fix_pressure(altaz_coord)
    atm = int(new_altaz_coord.pressure.value) != 0
    icrs = new_altaz_coord.transform_to(ICRS())
    return icrs, atm


def _icrs_to_altaz(icrs_coord, obstime=None, pressure=None):
    """
    Convert a skycoordinate to altaz frame.
    :param icrs_coord: The coordinates you would want to covert to altaz, probably icrs frame.
    :type icrs_coord: ICRS
    :param obstime: The observation time to get altaz coordinates, defaults to astropy.time.Time.now()
    :type obstime: AstroTime
    :param pressure: Pressure to use otherwise uses from location
    :type pressure: u.Quantity
    :return: (AltAz coordinate, if atm refraction was used in conversion)
    :rtype: (AltAz, bool)
    """
    aa_frame = get_frame_init_args('altaz', obstime=obstime, pressure=0 * u.hPa)
    altaz = icrs_coord.transform_to(AltAz(**aa_frame))
    # TODO: For array coord can we just set the pressure to 0 where it alt is less than threshold instead of if any?
    if (altaz.alt.deg <= ALT_ATM_THRESHOLD).any() or (pressure is not None and int(pressure.value) == 0):
        return altaz, False
    aa_frame = get_frame_init_args('altaz', obstime=obstime, pressure=pressure)
    altaz = icrs_coord.transform_to(AltAz(**aa_frame))
    return altaz, True


def _tete_to_hadec(tete_coord):
    """
    Convert TETE Coordinate to HADec
    :param tete_coord: TETE Coordinate to convert
    :return: (HADec coordinate, if atm refraction used in conversion)
    :rtype: (HADec, atm)
    """
    icrs = tete_coord.transform_to(ICRS())
    altaz = _icrs_to_altaz(icrs, pressure=0 * u.hPa)[0]
    pressure = None
    if altaz.alt.deg < 0:
        pressure = 0 * u.hPa
    hadec, atm = _icrs_to_hadec(icrs, obstime=tete_coord.obstime, pressure=pressure)
    return hadec, atm


def _icrs_to_tete(icrs_coord, obstime=None):
    """
    Convert ICRS to TETE.
    :param icrs_coord: ICRS Coord to convert
    :param obstime: Time to use otherwise now.
    :type obstime: AstroTime
    :return: TETE Coordinate
    :rtype: TETE
    """
    frame_args = get_frame_init_args('tete', obstime=obstime)
    tete = icrs_coord.transform_to(TETE(**frame_args))
    return tete


def _tete_to_icrs(tete_coord):
    """
    Convert TETE coordinate to ICRS.
    :param tete_coord: The TETE coordinate to convert.
    :type tete_coord: TETE
    :return: ICRS Coordinate
    :rtype: ICRS
    """
    icrs = tete_coord.transform_to(ICRS())
    return icrs


def _hadec_to_tete(hadec_coord):
    """
    Convert HADec coordinate to TETE coordinate.
    :param hadec_coord: The HADec Coordinate to convert.
    :return: (The TETE Coordinate, if atm refraction was used in conversion)
    :rtype: (TETE, bool)
    """
    new_hadec_coord = hadec_coord
    if int(new_hadec_coord.pressure.value) != 0:
        altaz = _hadec_to_altaz(hadec_coord)[0]
        if altaz.alt.deg <= ALT_ATM_THRESHOLD:
            frame_args = get_frame_init_args('hadec', frame_copy=hadec_coord)
            frame_args['pressure'] = 0 * u.hPa
            new_hadec_coord = skyconv_hadec.HADec(ha=hadec_coord.ha, dec=hadec_coord.dec, **frame_args)
    atm = int(new_hadec_coord.pressure.value) != 0
    icrs = skyconv_hadec.hadec_to_icrs(hadec_coord, ICRS())
    tete = _icrs_to_tete(icrs, obstime=hadec_coord.obstime)
    return tete, atm


def _tete_to_altaz(tete_coord):
    """
    Convert TETE coordinate to AltAz coordinate.
    :param tete_coord: The TETE coordinate to convert.
    :type tete_coord: TETE
    :return: (AltAz coordinate, if atm refraction used)
    :rtype: (AltAz, bool)
    """
    frame_args = get_frame_init_args('altaz', obstime=tete_coord.obstime)
    frame_args['pressure'] = 0 * u.hPa
    altaz = tete_coord.transform_to(AltAz(**frame_args))
    if altaz.alt.deg <= ALT_ATM_THRESHOLD:
        return altaz, False
    frame_args = get_frame_init_args('altaz', obstime=tete_coord.obstime)
    return tete_coord.transform_to(AltAz(**frame_args)), True


def _altaz_to_tete(altaz_coord):
    """
    Convert AltAz coordinate to TETE
    :param altaz_coord: The coordinate to convert
    :type altaz_coord: AltAz
    :return: (TETE coordinate, if atm refraction used in conversion)
    :rtype: (TETE, bool)
    """
    new_altaz_coord = _altaz_threshold_fix_pressure(altaz_coord)
    frame_args = get_frame_init_args('tete', obstime=altaz_coord.obstime)
    return new_altaz_coord.transform_to(TETE(**frame_args)), int(new_altaz_coord.pressure.value) != 0


def to_altaz(coord, obstime=None):
    """
    Convert any type of coord to AltAz
    :param coord: coord to convert
    :param obstime: observation time
    :return: AltAz coordinate
    :rtype: AltAz
    """
    if coord.name == 'altaz':
        altaz = coord
    elif coord.name == 'icrs':
        altaz, atm = _icrs_to_altaz(coord, obstime=obstime)
    elif coord.name == 'tete':
        altaz, atm = _tete_to_altaz(coord)
    elif coord.name == 'hadec':
        altaz, atm = _hadec_to_altaz(coord)
    else:
        print('ERROR Unable to handle frame')
        return None
    return altaz


def to_icrs(coord):
    """
    Convert any coordinate to ICRS
    :param coord: The coordinate to convert
    :return: The ICRS Coordinate
    :rtype: ICRS
    """
    if coord.name == 'altaz':
        icrs, atm = _altaz_to_icrs(coord)
    elif coord.name == 'icrs':
        icrs = coord
    elif coord.name == 'tete':
        icrs = _tete_to_icrs(coord)
    elif coord.name == 'hadec':
        icrs, atm = _hadec_to_icrs(coord)
    else:
        print('ERROR Unable to handle frame')
        return None
    return icrs


def to_hadec(coord, obstime=None):
    """
    Convert any coordinate to HADec
    :param coord: The coordinate to convert
    :param obstime: Time to use or now or coord.obstime
    :return: HADec coordinate
    :rtype: HADec
    """
    if hasattr(coord, 'alt'):
        hadec, atm = _altaz_to_hadec(coord)
    elif coord.name == 'icrs':
        hadec, atm = _icrs_to_hadec(coord, obstime=obstime)
    elif coord.name == 'tete':
        hadec, atm = _tete_to_hadec(coord)
    elif coord.name == 'hadec':
        hadec = coord
    else:
        print('ERROR Unknown Coordinate')
        return None
    return hadec


def to_tete(coord, obstime=None, overwrite_time=False):
    """
    Convert any coordinate to TETE.
    :param coord: Coordinate to convert.
    :param obstime: Time to use or now or coord.obstime
    :param overwrite_time: If should overwrite coord.obstime with obstime arg.
    :return: TETE coordinate
    :rtype: TETE
    """
    if coord.name == 'altaz':
        if overwrite_time:
            frame_args = get_frame_init_args('altaz', frame_copy=coord)
            if obstime:
                frame_args['obstime'] = obstime
            altaz = AltAz(alt=coord.alt, az=coord.az, **frame_args)
            tete = _altaz_to_tete(altaz)
        else:
            tete = _altaz_to_tete(coord)
    elif coord.name == 'icrs':
        tete = _icrs_to_tete(coord, obstime=obstime)
    elif coord.name == 'tete':
        if overwrite_time:
            frame_args = get_frame_init_args('tete', frame_copy=coord)
            if obstime:
                frame_args['obstime'] = obstime
            tete = TETE(ra=coord.ra, dec=coord.dec, **frame_args)
        else:
            tete = coord
    elif coord.name == 'hadec':
        if overwrite_time:
            frame_args = get_frame_init_args('hadec', frame_copy=coord)
            if obstime:
                frame_args['obstime'] = obstime
            hadec = skyconv_hadec.HADec(ha=coord.ha, dec=coord.dec, **frame_args)
            tete = _hadec_to_tete(hadec)
        else:
            tete = _hadec_to_tete(coord)
    else:
        print('ERROR Unknown Coordinate')
        return None
    return tete


def to_steps(coord, sync_info=None, obstime=None, model_transform=False, ha_steps_per_degree=None,
             dec_steps_per_degree=None):
    """
    Takes a HaDec,TETE,IRCS,AltAz, or dict(steps) coordinate and converts to to steps.
    :param coord: RADec, AltAz, TETE, HADec, or dict {'ha': int, 'dec': int}
    :param sync_info: If none uses runtime sync_info
    :param obstime: If None uses now
    :type obstime: AstroTime
    :param model_transform: If true will send through pointing model if applicable.
    :param ha_steps_per_degree: If none uses settings
    :param dec_steps_per_degree: If None uses settings
    :return: dict {'ha': int, 'dec': int}
    :rtype: dict
    """
    if type(coord) is dict and 'ha' in coord:  # Already ha dec steps
        return coord
    if coord.name == 'tete':
        coord = to_tete(coord, obstime=obstime, overwrite_time=True)
    hadec = to_hadec(coord, obstime=obstime)
    ret = _hadec_to_steps(hadec, sync_info=sync_info, ha_steps_per_degree=ha_steps_per_degree,
                          dec_steps_per_degree=dec_steps_per_degree, model_transform=model_transform)
    return ret


def steps_to_coord(steps, frame='icrs', sync_info=None, obstime=None, inverse_model=False, ha_steps_per_degree=None,
                   dec_steps_per_degree=None):
    """
    Steps to hour angle dec.
    :param steps: keys ha, and dec
    :rtype steps: dict
    :param frame: One of, 'icrs', 'altaz', 'hadec', default 'icrs'
    :param sync_info: defaults to runtime_settings['sync_info']
    :param obstime: time of observation default now
    :param inverse_model: Should go through inverse model doing conversion
    :param ha_steps_per_degree: defaults to settings
    :param dec_steps_per_degree: defaults to settings
    :return: coordinate in specified frame
    """
    if not sync_info:
        sync_info = settings.runtime_settings['sync_info']
    if not ha_steps_per_degree:
        ha_steps_per_degree = settings.settings['ra_ticks_per_degree']
    if not dec_steps_per_degree:
        dec_steps_per_degree = settings.settings['dec_ticks_per_degree']
    d_ha = (steps['ha'] - sync_info['steps']['ha']) / ha_steps_per_degree
    d_dec = (steps['dec'] - sync_info['steps']['dec']) / dec_steps_per_degree

    ha_deg = _clean_deg(sync_info['coord'].ha.deg + d_ha)
    # print({'frame': frame, 'ha_deg': ha_deg})
    dec_deg, pole_count = _clean_deg(sync_info['coord'].dec.deg + d_dec, True)
    # print({'frame': frame, 'dec_deg': dec_deg})
    if pole_count % 2 > 0:
        ha_deg = _clean_deg(ha_deg + 180.0)
    # print({'frame': frame, 'dec_deg': dec_deg})

    frame_args = get_frame_init_args('hadec', obstime=obstime)
    hadec_coord = skyconv_hadec.HADec(ha=ha_deg * u.deg, dec=dec_deg * u.deg, **frame_args)
    # print('hadec_coord', hadec_coord)
    if inverse_model:
        if model_real_stepper.frame() == 'altaz':
            altaz_coord = _hadec_to_altaz(hadec_coord)
            altaz_coord = model_real_stepper.inverse_transform_point(altaz_coord)
            if frame == 'hadec':
                return _altaz_to_hadec(altaz_coord)
            elif frame == 'altaz':
                return altaz_coord
            elif frame == 'tete':
                return _altaz_to_tete(altaz_coord)
            else:
                return _altaz_to_icrs(altaz_coord)

        elif model_real_stepper.frame() == 'hadec':
            hadec_coord = model_real_stepper.inverse_transform_point(hadec_coord)
            if frame == 'hadec':
                return hadec_coord
            elif frame == 'altaz':
                return _hadec_to_altaz(hadec_coord)
            elif frame == 'tete':
                return _hadec_to_tete(hadec_coord)
            else:  # ICRS
                return _hadec_to_icrs(hadec_coord)


def _clean_deg(deg, dec=False):
    """
    Cleans up dec or ra as degree when outside range [-90, 90], [0, 360].
    :param deg: The degree to cleanup.
    :type deg: float
    :param dec: True if dec, false if ra.
    :type dec: bool
    :return: Cleaned up value. Second argument exists only when dec is True.
    :rtype: float, (int)
    """
    if dec:
        pole_count = 0
        while deg > 90 or deg < -90:
            if deg > 90:
                pole_count += 1
                deg = 90 - (deg - 90)
            if deg < -90:
                pole_count += 1
                deg = -90 - (deg + 90)
        return deg, pole_count
    else:
        if deg < 0:
            while deg < 0:
                deg += 360.0
        elif deg > 360.0:
            deg = deg % 360
        return deg


def _earth_location_to_pressure(earth_location=None):
    """
    Gives you expected absolute pressure at elevation.
    :param earth_location: astropy.coordinates.EarthLocation defaults to runtime_settings['earth_location']
    :return: pressure astropy.units.Quantity
    """
    if earth_location is None:
        earth_location = settings.runtime_settings['earth_location']
    height = earth_location.height.to_value(u.m)
    # https://www.engineeringtoolbox.com/air-altitude-pressure-d_462.html
    return 101325.0 * ((1.0 - 2.2557e-5 * height) ** 5.25588) * usi.Pa
