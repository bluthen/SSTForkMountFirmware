from astropy.coordinates import AltAz, SkyCoord, ICRS
from astropy.time import Time as AstroTime

import astropy.units as u
import astropy.units.si as usi

import settings

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
    return altaz_to_icrs(AltAz(alt=90.0 * u.deg, az=0 * u.deg), earth_location=earth_location, obstime=obstime,
                         atmo_refraction=False).ra
    # if not location:
    #    location = settings.runtime_settings['earth_location']
    # t = AstroTime(obstime, location=location)
    # return t.sidereal_time('mean')


def icrs_to_hadec(coord, obstime=None, earth_location=None, atmo_refraction=False):
    """
    Transforms icrs coordinate to hadec.
    :param coord: The RADEC ICRS coordinate
    :param obstime: Observations time to get hadec
    :param earth_location: Location of observation
    :param atmo_refraction: If should correct for atmosphereic refraction
    :return: new hadec coordinate
    """
    if atmo_refraction:
        altaz = icrs_to_altaz(coord, earth_location=earth_location, obstime=obstime, atmo_refraction=True)
        coord = altaz_to_icrs(altaz, obstime=obstime, earth_location=earth_location, atmo_refraction=False)
    sr_time = get_sidereal_time(obstime=obstime, earth_location=earth_location)
    coord = SkyCoord(ra=sr_time - coord.ra, dec=coord.dec, frame='icrs')
    return coord


def altaz_to_hadec(coord, obstime=None, earth_location=None):
    """
    Convert altaz coordinate to hadec.
    :param coord: altaz SkyCoord
    :param obstime: Time of observation
    :param earth_location: Locatin of observation
    :return: hadec SkyCoord
    """
    coord = altaz_to_icrs(coord, earth_location=earth_location, obstime=obstime, atmo_refraction=False)
    return icrs_to_hadec(coord, obstime=obstime, earth_location=earth_location, atmo_refraction=False)


def hadec_to_icrs(coord, obstime=None, earth_location=None, atmo_refraction=False):
    """
    HADec SkyCoord to ICRS RADec SkyCoord
    :param coord:  The HADec SkyCoord
    :param obstime: Time of observation
    :param earth_location: location of observation
    :param atmo_refraction: If should take into account atmospheric refraction while converting to ICRS RADec SkyCoord.
    :return: SkyCoord in ICRS Frame as RADec
    """
    sr_time = get_sidereal_time(obstime, earth_location=earth_location)
    coord = SkyCoord(ra=(sr_time.deg - coord.ra.deg) * u.deg, dec=coord.dec.deg * u.deg, frame='icrs')
    if atmo_refraction:
        coord = icrs_to_altaz(coord, earth_location=earth_location, atmo_refraction=False)
        coord = altaz_to_icrs(coord, earth_location=earth_location, obstime=obstime, atmo_refraction=True)
    return coord


def hadec_to_altaz(coord, obstime=None, earth_location=None):
    """
    HADec SkyCoord to AltAz SkyCoord.
    :param coord: HADec ICRS SkyCoord.
    :param obstime: Time of observation, default now
    :param earth_location: location of observation, default settings
    :return:
    """
    coord = hadec_to_icrs(coord, obstime=obstime, earth_location=None, atmo_refraction=False)
    coord = icrs_to_altaz(coord, earth_location=earth_location, obstime=obstime, atmo_refraction=False)
    return coord


def ha_delta_deg(started_angle, end_angle):
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
        >>> skyconv.ha_delta_deg(359.0, 370.0)
        11.0
    """
    end_angle = clean_deg(end_angle)
    started_angle = clean_deg(started_angle)

    d_1 = end_angle - started_angle
    d_2 = 360.0 + d_1
    d_3 = d_1 - 360

    return min([d_1, d_2, d_3], key=abs)


def hadec_to_steps(ha_dec_coord, sync_info=None, ha_steps_per_degree=None, dec_steps_per_degree=None,
                   model_transform=False):
    """
    Takes HaDec SkyCoord and converts it to steps.
    :param ha_dec_coord:
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
        ha_dec_coord = model_real_stepper.transform_point(ha_dec_coord)
    # TODO: Do we neeed something like ra_deg_d? Or stop it from twisting even with tracking?
    #  How does this affect the model?
    # d_ha = ha_dec_coord.ra.deg - sync_info['coord'].ra.deg
    d_ha = ha_delta_deg(sync_info['coord'].ra.deg, ha_dec_coord.ra.deg)
    d_dec = ha_dec_coord.dec.deg - sync_info['coord'].dec.deg

    steps_ha = sync_info['steps']['ha'] + (d_ha * ha_steps_per_degree)
    steps_dec = sync_info['steps']['dec'] + (d_dec * dec_steps_per_degree)
    return {'ha': steps_ha, 'dec': steps_dec}


def altaz_to_icrs(altaz_coord, earth_location=None, obstime=None, atmo_refraction=False):
    """
    Converts an alt-az coordinate to ICRS ra-dec coordinate.
    :param altaz_coord: coordinate to convert
    :param earth_location: earth location to use, if none, uses runtime earth_location
    :param obstime: UTC time to use to do coordinate conversions, defaults to now.
    :param atmo_refraction: If should take into account atmosphereic refration while doing conversion.
    :return: astropy.coordinate.SkyCoord in ICRS frame.
    :Example:
        >>> import skyconv
        >>> from astropy.coordinates import EarthLocation, AltAz
        >>> from astropy.time import Time as AstroTime
        >>> import astropy.units as u
        >>> el = EarthLocation(lat=38.9369*u.deg, lon=-95.242*u.deg, height=266.0*u.m)
        >>> t = AstroTime('2018-12-26T22:55:32.281', format='isot', scale='utc')
        >>> b = AltAz(alt=80*u.deg, az=90*u.deg)
        >>> c = skyconv.altaz_to_icrs(b, earth_location=el, obstime=t, atmo_refraction=False)
        >>> c.ra.deg, c.dec.deg
        (356.5643249365523, 38.12981040209684)
    """
    if obstime is None:
        obstime = AstroTime.now()
    if earth_location is None:
        earth_location = settings.runtime_settings['earth_location']
    if earth_location is not None:
        pressure = None
        if atmo_refraction and settings.runtime_settings['earth_location_set']:
            pressure = earth_location_to_pressure(earth_location)
        coord = AltAz(alt=altaz_coord.alt.deg * u.deg, az=altaz_coord.az.deg * u.deg,
                      obstime=obstime, location=earth_location, pressure=pressure).transform_to(ICRS)
        return clean_icrs(coord)
    return None


def icrs_to_altaz(coord, earth_location=None, obstime=None, atmo_refraction=False):
    """
    Convert a skycoordinate to altaz frame.
    :param coord: The coordinates you would want to covert to altaz, probably icrs frame.
    :type coord: astropy.coordinates.SkyCoord
    :param earth_location: Location to base altaz on, defaults runtime_settings['earth_location']
    :type earth_location: astropy.coordinates.EarthLocation
    :param obstime: The observation time to get altaz coordinates, defaults to astropy.time.Time.now()
    :type obstime: astropy.time.Time
    :param atmo_refraction: if should adjust for atmospheric refraction
    :type atmo_refraction: bool
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
        >>> altaz = skyconv.icrs_to_altaz(radec, earth_location, t)
        >>> altaz.alt.deg, altaz.az.deg
        (55.558034184006516, 64.41850865846912)
    """
    if obstime is None:
        obstime = AstroTime.now()
    if earth_location is None:
        earth_location = settings.runtime_settings['earth_location']
    if earth_location is not None:
        pressure = None
        if atmo_refraction and settings.runtime_settings['earth_location_set']:
            pressure = earth_location_to_pressure(earth_location)
        altaz = coord.transform_to(AltAz(obstime=obstime, location=earth_location, pressure=pressure))
        return clean_altaz(altaz)
    else:
        return None


def coord_to_steps(coord, sync_info=None, obstime=None, earth_location=None, atmo_refraction=False,
                   model_transform=False, ha_steps_per_degree=None, dec_steps_per_degree=None):
    """
    Takes a RADec,AltAz, or dict(steps) coordinate and converts to to steps.
    :param coord: RADec, AltAz, dict {'ha': int, 'dec': int}
    :param sync_info: If none uses runtime sync_info
    :param obstime: If None uses now
    :param earth_location: If none uses runtime
    :param atmo_refraction: if shoudld take atmospheric refraction into account, default false
    :param model_transform: If true will send through pointing model if applicable.
    :param ha_steps_per_degree: If none uses settings
    :param dec_steps_per_degree: If None uses settings
    :return: dict {'ha': int, 'dec': int}
    """
    if type(coord) is dict and 'ha' in coord:  # Already ha dec steps
        return coord
    if hasattr(coord, 'alt'):
        coord = altaz_to_icrs(coord, earth_location=earth_location, obstime=obstime, atmo_refraction=False)
        coord = icrs_to_hadec(coord, obstime=obstime, earth_location=earth_location, atmo_refraction=False)
    else:
        coord = icrs_to_hadec(coord, obstime=obstime, earth_location=earth_location, atmo_refraction=atmo_refraction)
    coord = hadec_to_steps(coord, sync_info=sync_info, ha_steps_per_degree=ha_steps_per_degree,
                           dec_steps_per_degree=dec_steps_per_degree, model_transform=model_transform)
    return coord


def steps_to_coord(steps, frame='icrs', sync_info=None, obstime=None, inverse_model=False, earth_location=None,
                   atmo_refraction=False, ha_steps_per_degree=None, dec_steps_per_degree=None):
    """
    Steps to hour angle dec.
    :param steps: keys ha, and dec
    :rtype steps: dict
    :param frame: One of, 'icrs', 'altaz', 'hadec', default 'icrs'
    :param sync_info: defaults to runtime_settings['sync_info']
    :param obstime: time of observation default now
    :param inverse_model: Should go through inverse model doing conversion
    :param earth_location: location of observation, defaults settings
    :param atmo_refraction: If to take atmo refraction into consideration, default false.
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

    ha_deg = clean_deg(sync_info['coord'].ra.deg + d_ha)
    dec_deg, pole_count = clean_deg(sync_info['coord'].dec.deg + d_dec, True)
    if pole_count % 2 > 0:
        ha_deg = clean_deg(ha_deg + 180.0)

    hadec_coord = SkyCoord(ra=ha_deg * u.deg, dec=dec_deg * u.deg, frame='icrs')
    if inverse_model:
        hadec_coord = model_real_stepper.inverse_transform_point(hadec_coord)
    if frame == 'hadec':
        return hadec_coord
    elif frame == 'altaz':
        return hadec_to_altaz(hadec_coord, obstime=obstime, earth_location=earth_location)
    else:  # ICRS
        return hadec_to_icrs(hadec_coord, obstime=obstime, earth_location=earth_location,
                             atmo_refraction=atmo_refraction)


def clean_deg(deg, dec=False):
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
        >>> skyconv.clean_deg(91.0, True)
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


def clean_altaz(altaz):
    """
    Cleans up altaz coordinate without any location info.
    :param altaz:
    :return:
    """
    return SkyCoord(alt=altaz.alt.deg * u.deg, az=altaz.az.deg * u.deg, frame='altaz')


def clean_icrs(icrs):
    """
    Clean ICRS SkyCoord
    :param icrs:
    :return:
    """
    return SkyCoord(ra=icrs.ra.deg * u.deg, dec=icrs.dec.deg * u.deg, frame='icrs')


def earth_location_to_pressure(earth_location=None):
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
        >>> skyconv.earth_location_to_pressure(earth_location).to_value(usi.Pa)
        98170.13549856932
    """
    if earth_location is None:
        earth_location = settings.runtime_settings['earth_location']
    height = earth_location.height.to_value(u.m)
    # https://www.engineeringtoolbox.com/air-altitude-pressure-d_462.html
    return 101325.0 * ((1.0 - 2.2557e-5 * height) ** 5.25588) * usi.Pa
