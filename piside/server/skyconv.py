from astropy.coordinates import AltAz, ICRS, TETE
from astropy.time import Time as AstroTime

import astropy.units as u
import astropy.units.si as usi

import settings
import skyconv_hadec

model_real_stepper = None


def get_sidereal_time(obstime=None, earth_location=None):
    """
    Get sidereal time at a particular time and location.
    :param obstime:
    :type obstime: astropy.time.Time
    :param earth_location:
    :type earth_location: astropy.coordinates.EarthLocation
    :return:
    """
    if not obstime:
        obstime = AstroTime.now()
    # We don't use astropy.time.Time.sidereal_time because it needs to have update iers tables
    frame_args = get_frame_init_args('altaz', obstime=obstime, earth_location=earth_location)
    return _altaz_to_tete(AltAz(alt=90.0 * u.deg, az=0 * u.deg, **frame_args)).ra
    # if not location:
    #    location = settings.runtime_settings['earth_location']
    # t = AstroTime(obstime, location=location)
    # return t.sidereal_time('mean')


def _icrs_to_hadec(icrs_coord, obstime=None, earth_location=None):
    """
    Transforms icrs coordinate to hadec.
    :param icrs_coord: The RADEC ICRS coordinate
    :param obstime: Observations time to get hadec
    :param earth_location: Location of observation
    :return: new hadec coordinate
    """
    frame_args = get_frame_init_args('hadec', obstime=obstime, earth_location=earth_location)
    icrs_coord = skyconv_hadec.icrs_to_hadec(icrs_coord, skyconv_hadec.HADec(**frame_args))
    return icrs_coord


def _altaz_to_hadec(altaz_coord):
    """
    Convert altaz coordinate to hadec.
    :param altaz_coord: altaz SkyCoord
    :param obstime: Time of observation
    :param earth_location: Locatin of observation
    :return: hadec SkyCoord
    """
    icrs = _altaz_to_icrs(altaz_coord)
    return _icrs_to_hadec(icrs, obstime=altaz_coord.obstime, earth_location=altaz_coord.location)


def get_frame_init_args(frame, earth_location=None, obstime=None, frame_copy=None):
    ret = {'location': earth_location, 'obstime': obstime}
    if ret['location'] is None:
        ret['location'] = settings.runtime_settings['earth_location']
    if ret['obstime'] is None:
        ret['obstime'] = AstroTime.now()
    if frame == 'altaz' or frame == 'hadec':
        ret['pressure'] = _earth_location_to_pressure(ret['location'])
        ret['obswl'] = 540 * u.nm
        ret['temperature'] = 20 * u.deg_C
        ret['relative_humidity'] = 0.35
    if frame_copy:
        for key in ret.keys():
            if hasattr(frame_copy, key):
                ret[key] = getattr(frame_copy, key)
    return ret


def _hadec_to_icrs(hadec_coord):
    """
    HADec SkyCoord to ICRS RADec SkyCoord
    :param hadec_coord:  The HADec SkyCoord
    :return: SkyCoord in ICRS Frame as RADec
    """
    return skyconv_hadec.hadec_to_icrs(hadec_coord, ICRS())


def _hadec_to_altaz(hadec_coord):
    """
    HADec SkyCoord to AltAz SkyCoord.
    :param coord: HADec SkyCoord.
    :param obstime: Time of observation, default now
    :param earth_location: location of observation, default settings
    :return:
    """
    icrs = _hadec_to_icrs(hadec_coord)
    altaz = _icrs_to_altaz(icrs, earth_location=hadec_coord.location, obstime=hadec_coord.obstime)
    return altaz


def _ha_delta_deg(started_angle, end_angle):
    """
    Finds the degree difference between two angles ang1-ang2, then returns shortest side that will take you
    there - or +.
    :param started_angle: First angle
    :type started_angle: float
    :param end_angle: Second angle
    :type end_angle: float
    :return: The shortest difference between started_angle, end_angle.
    :rtype: float
    :Example:
        >>> import skyconv
        >>> skyconv._ha_delta_deg(359.0, 370.0)
        11.0
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
    Takes HaDec SkyCoord and converts it to steps.
    :param hadec_coord:
    :param sync_info:
    :param model_transform:
    :param ha_steps_per_degree:
    :param dec_steps_per_degree:
    :return:
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


def _altaz_to_icrs(altaz_coord):
    """
    Converts an alt-az coordinate to ICRS ra-dec coordinate.
    :param altaz_coord: coordinate to convert
    :return: astropy.coordinate.SkyCoord in ICRS frame.
    :Example:
        >>> import skyconv
        >>> from astropy.coordinates import EarthLocation, AltAz
        >>> from astropy.time import Time as AstroTime
        >>> import astropy.units as u
        >>> el = EarthLocation(lat=38.9369*u.deg, lon=-95.242*u.deg, height=266.0*u.m)
        >>> t = AstroTime('2018-12-26T22:55:32.281', format='isot', scale='utc')
        >>> b = AltAz(alt=80*u.deg, az=90*u.deg)
        >>> c = skyconv._altaz_to_icrs(b)
        >>> c.ra.deg, c.dec.deg
        (356.5643249365523, 38.12981040209684)
    """
    icrs = altaz_coord.transform_to(ICRS())
    return icrs


def _icrs_to_altaz(icrs_coord, earth_location=None, obstime=None):
    """
    Convert a skycoordinate to altaz frame.
    :param icrs_coord: The coordinates you would want to covert to altaz, probably icrs frame.
    :type icrs_coord: astropy.coordinates.SkyCoord
    :param earth_location: Location to base altaz on, defaults runtime_settings['earth_location']
    :type earth_location: astropy.coordinates.EarthLocation
    :param obstime: The observation time to get altaz coordinates, defaults to astropy.time.Time.now()
    :type obstime: astropy.time.Time
    :return: SkyCoord in altaz or None if unable to compute (missing earth_location)
    :rtype: astropy.coordinates.SkyCoord
    :Example:
        >>> import skyconv
        >>> from astropy.coordinates import EarthLocation, SkyCoord
        >>> import astropy.units as u
        >>> from astropy.time import Time
        >>> t = Time('2018-12-26T22:55:32.281', format='isot', scale='utc')
        >>> earth_location = EarthLocation(lat=38.9369*u.deg, lon= -95.242*u.deg, height=266.0*u.m)
        >>> radec = SkyCoord(ra=30*u.deg, dec=45*u.deg, frame='icrs')
        >>> altaz = skyconv._icrs_to_altaz(radec, earth_location, t)
        >>> altaz.alt.deg, altaz.az.deg
        (55.558034184006516, 64.41850865846912)
    """
    aa_frame = get_frame_init_args('altaz', earth_location=earth_location, obstime=obstime)
    altaz = icrs_coord.transform_to(AltAz(**aa_frame))
    return altaz


def _tete_to_hadec(tete_coord):
    icrs = tete_coord.transform_to(ICRS())
    hadec = _icrs_to_hadec(icrs, earth_location=tete_coord.location, obstime=tete_coord.obstime)
    return hadec


def _icrs_to_tete(icrs_coord, earth_location=None, obstime=None):
    frame_args = get_frame_init_args('tete', earth_location=earth_location, obstime=obstime)
    tete = icrs_coord.transform_to(TETE(**frame_args))
    return tete


def _tete_to_icrs(tete_coord):
    icrs = tete_coord.transform_to(ICRS())
    return icrs


def _hadec_to_tete(hadec_coord):
    icrs = skyconv_hadec.hadec_to_icrs(hadec_coord, ICRS())
    tete = _icrs_to_tete(icrs, obstime=hadec_coord.obstime, earth_location=hadec_coord.location)
    return tete


def _tete_to_altaz(tete_coord):
    frame_args = get_frame_init_args('altaz', earth_location=tete_coord.location, obstime=tete_coord.obstime)
    return tete_coord.transform_to(AltAz(**frame_args))


def _altaz_to_tete(altaz_coord):
    frame_args = get_frame_init_args('tete', earth_location=altaz_coord.location, obstime=altaz_coord.obstime)
    return altaz_coord.transform_to(TETE(**frame_args))


def to_altaz(coord, obstime=None, earth_location=None):
    if coord.name == 'altaz':
        altaz = coord
    elif coord.name == 'icrs':
        altaz = _icrs_to_altaz(coord, obstime=obstime, earth_location=earth_location)
    elif coord.name == 'tete':
        altaz = _tete_to_altaz(coord)
    elif coord.name == 'hadec':
        altaz = _hadec_to_altaz(coord)
    else:
        print('ERROR Unable to handle frame')
        return None
    return altaz


def to_icrs(coord):
    if coord.name == 'altaz':
        icrs = _altaz_to_icrs(coord)
    elif coord.name == 'icrs':
        icrs = coord
    elif coord.name == 'tete':
        icrs = _tete_to_icrs(coord)
    elif coord.name == 'hadec':
        icrs = _hadec_to_icrs(coord)
    else:
        print('ERROR Unable to handle frame')
        return None
    return icrs


def to_hadec(coord, obstime=None, earth_location=None):
    if hasattr(coord, 'alt'):
        hadec = _altaz_to_hadec(coord)
    elif coord.name == 'icrs':
        hadec = _icrs_to_hadec(coord, obstime=obstime, earth_location=earth_location)
    elif coord.name == 'tete':
        hadec = _tete_to_hadec(coord)
    elif coord.name == 'hadec':
        hadec = coord
    else:
        print('ERROR Unknown Coordinate')
        return None
    return hadec


def to_tete(coord, obstime=None, earth_location=None, overwrite_time=False):
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
        tete = _icrs_to_tete(coord, obstime=obstime, earth_location=earth_location)
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


def to_steps(coord, sync_info=None, obstime=None, earth_location=None,
             model_transform=False, ha_steps_per_degree=None, dec_steps_per_degree=None):
    """
    Takes a HaDec,TETE,IRCS,AltAz, or dict(steps) coordinate and converts to to steps.
    :param coord: RADec, AltAz, dict {'ha': int, 'dec': int}
    :param sync_info: If none uses runtime sync_info
    :param obstime: If None uses now
    :param earth_location: If none uses runtime
    :param model_transform: If true will send through pointing model if applicable.
    :param ha_steps_per_degree: If none uses settings
    :param dec_steps_per_degree: If None uses settings
    :return: dict {'ha': int, 'dec': int}
    """
    if type(coord) is dict and 'ha' in coord:  # Already ha dec steps
        return coord
    if coord.name == 'tete':
        coord = to_tete(coord, obstime=obstime, overwrite_time=True)
    hadec = to_hadec(coord, earth_location=earth_location, obstime=obstime)
    ret = _hadec_to_steps(hadec, sync_info=sync_info, ha_steps_per_degree=ha_steps_per_degree,
                          dec_steps_per_degree=dec_steps_per_degree, model_transform=model_transform)
    return ret


def steps_to_coord(steps, frame='icrs', sync_info=None, obstime=None, inverse_model=False, earth_location=None,
                   ha_steps_per_degree=None, dec_steps_per_degree=None):
    """
    Steps to hour angle dec.
    :param steps: keys ha, and dec
    :rtype steps: dict
    :param frame: One of, 'icrs', 'altaz', 'hadec', default 'icrs'
    :param sync_info: defaults to runtime_settings['sync_info']
    :param obstime: time of observation default now
    :param inverse_model: Should go through inverse model doing conversion
    :param earth_location: location of observation, defaults settings
    :param ha_steps_per_degree: defaults to settings
    :param dec_steps_per_degree: defaults to settings
    :return: astropy.coordinates.SkyCoord in frame as specified.
    """
    if not sync_info:
        sync_info = settings.runtime_settings['sync_info']
    if not ha_steps_per_degree:
        ha_steps_per_degree = settings.settings['ra_ticks_per_degree']
    if not dec_steps_per_degree:
        dec_steps_per_degree = settings.settings['dec_ticks_per_degree']
    d_ha = (steps['ha'] - sync_info['steps']['ha']) / ha_steps_per_degree
    d_dec = (steps['dec'] - sync_info['steps']['dec']) / dec_steps_per_degree

    # print({'d_ha': d_ha, 'steps_ha': steps['ha'], 'sync_ha': sync_info['steps']['ha'], 'ha_spd': ha_steps_per_degree, 'ha_sync_coord': sync_info['coord'].ra.deg})

    # print({'d_dec': d_dec, 'steps_dec': steps['dec'], 'sync_dec': sync_info['steps']['dec'], 'dec_spd': dec_steps_per_degree, 'dec_sync_coord': sync_info['coord'].dec.deg})

    ha_deg = _clean_deg(sync_info['coord'].ha.deg + d_ha)
    # print({'frame': frame, 'ha_deg': ha_deg})
    dec_deg, pole_count = _clean_deg(sync_info['coord'].dec.deg + d_dec, True)
    # print({'frame': frame, 'dec_deg': dec_deg})
    if pole_count % 2 > 0:
        ha_deg = _clean_deg(ha_deg + 180.0)
    # print({'frame': frame, 'dec_deg': dec_deg})

    frame_args = get_frame_init_args('hadec', earth_location=earth_location, obstime=obstime)
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
    :Example:
        >>> import skyconv
        >>> skyconv._clean_deg(91.0, True)
        (89.0, 1)
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
    :Example:
        >>> import skyconv
        >>> from astropy.coordinates import EarthLocation
        >>> import astropy.units as u
        >>> from astropy.units import si as usi
        >>> earth_location = EarthLocation(lat=38.9369*u.deg, lon= -95.242*u.deg, height=266.0*u.m)
        >>> skyconv._earth_location_to_pressure(earth_location).to_value(usi.Pa)
        98170.13549856932
    """
    if earth_location is None:
        earth_location = settings.runtime_settings['earth_location']
    height = earth_location.height.to_value(u.m)
    # https://www.engineeringtoolbox.com/air-altitude-pressure-d_462.html
    return 101325.0 * ((1.0 - 2.2557e-5 * height) ** 5.25588) * usi.Pa
