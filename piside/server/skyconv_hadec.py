"""
A HA-DEC frame to work in astropy 4.2
"""
import astropy.units as u
import erfa
from astropy.coordinates import representation as r
from astropy.coordinates.attributes import (TimeAttribute,
                                            QuantityAttribute,
                                            EarthLocationAttribute)
from astropy.coordinates.baseframe import BaseCoordinateFrame, RepresentationMapping
from astropy.coordinates.builtin_frames.utils import atciqz, aticq
from astropy.coordinates.builtin_frames.utils import (
    get_jd12, get_cip, prepare_earth_position_vel, get_polar_motion
)
from astropy.coordinates.representation import (SphericalRepresentation,
                                                CartesianRepresentation,
                                                UnitSphericalRepresentation)


class HADec(BaseCoordinateFrame):
    frame_specific_representation_info = {
        r.SphericalRepresentation: [
            RepresentationMapping('lon', 'ha'),
            RepresentationMapping('lat', 'dec')
        ]
    }
    default_representation = r.SphericalRepresentation
    default_differential = r.SphericalCosLatDifferential

    obstime = TimeAttribute(default=None)
    location = EarthLocationAttribute(default=None)
    pressure = QuantityAttribute(default=0, unit=u.hPa)
    temperature = QuantityAttribute(default=0, unit=u.deg_C)
    relative_humidity = QuantityAttribute(default=0, unit=u.dimensionless_unscaled)
    obswl = QuantityAttribute(default=1 * u.micron, unit=u.micron)
    name = 'hadec'

def icrs_to_hadec(icrs_coo, hadec_frame):
    """
    Convert to hadec coordinates from ICRS and a AltAz frame.
    :param icrs_coo: Original IRCS coordinate.
    :param hadec_frame: HaDec frame with location, obstime, and any other info see AltAz documentation
    :return: HaDec
    :Example:
        >>> import skyconv_hadec
        >>> from astropy.coordinates import EarthLocation, TETE, ICRS, AltAz, SkyCoord
        >>> from astropy.time import Time as AstroTime
        >>> from astropy import units as u
        >>> t = AstroTime('2020-11-27 19:12:16.894431')
        >>> earth_location = EarthLocation(lat=38.9369 * u.deg, lon=-95.242 * u.deg, height=266.0 * u.m)
        >>> pressure = 98170.13549857 * u.Pa
        >>> # East horizon object
        >>> icrs = ICRS(ra=344.0516042 * u.deg, dec=3.9267833 * u.deg)  # ngc7422
        >>> hadec = skyconv_hadec.icrs_to_hadec(icrs, skyconv_hadec.HADec(obstime=t, location=earth_location, pressure=pressure, obswl=540 * u.nm, temperature=20 * u.deg_C, relative_humidity=0.35))
        >>> hadec.ha.deg, hadec.dec.deg
        (275.7578128072564, 4.108663110053187)
    """
    # https://github.com/astropy/astropy/blob/master/astropy/coordinates/builtin_frames/icrs_observed_transforms.py
    # last commit d2c37f3
    # if the data are UnitSphericalRepresentation, we can skip the distance calculations
    is_unitspherical = (isinstance(icrs_coo.data, UnitSphericalRepresentation) or
                        icrs_coo.cartesian.x.unit == u.one)
    # first set up the astrometry context for ICRS<->AltAz
    # astrom = erfa_astrom.get().apco(altaz_frame)
    astrom = apco(hadec_frame)

    # correct for parallax to find BCRS direction from observer (as in erfa.pmpx)
    if is_unitspherical:
        srepr = icrs_coo.spherical
    else:
        observer_icrs = CartesianRepresentation(astrom['eb'], unit=u.au, xyz_axis=-1, copy=False)
        srepr = (icrs_coo.cartesian - observer_icrs).represent_as(
            SphericalRepresentation)

    # convert to topocentric CIRS
    cirs_ra, cirs_dec = atciqz(srepr, astrom)

    # now perform AltAz conversion
    az, zen, ha, odec, ora = erfa.atioq(cirs_ra, cirs_dec, astrom)
    odec = odec << u.radian
    if is_unitspherical:
        aa_srepr = UnitSphericalRepresentation(ha << u.radian, odec << u.radian, copy=False)
    else:
        aa_srepr = SphericalRepresentation(ha << u.radian, odec << u.radian, srepr.distance, copy=False)
    # hadec_frame = HaDec(obstime=hadec_frame.obstime, location=hadec_frame.location, pressure=hadec_frame.pressure,
    #                    temperature=hadec_frame.temperature, relative_humidity=hadec_frame.relative_humidity,
    #                    obswl=hadec_frame.obswl)
    return hadec_frame.realize_frame(aa_srepr)


def hadec_to_icrs(hadec_coo, icrs_frame):
    """
    Convert to ICRS coordinates from HaDec coordinate.
    :param hadec_coo: Original HaDec coordinate.
    :param icrs_frame: IRCS frame
    :return: IRCS
    :Example:
        >>> import skyconv_hadec
        >>> from astropy.coordinates import EarthLocation, TETE, ICRS, AltAz, SkyCoord
        >>> from astropy.time import Time as AstroTime
        >>> from astropy import units as u
        >>> t = AstroTime('2020-11-27 19:12:16.894431')
        >>> earth_location = EarthLocation(lat=38.9369 * u.deg, lon=-95.242 * u.deg, height=266.0 * u.m)
        >>> pressure = 98170.13549857 * u.Pa
        >>> # East horizon object
        >>> icrs = ICRS(ra=344.0516042 * u.deg, dec=3.9267833 * u.deg)  # ngc7422
        >>> hadec = skyconv_hadec.icrs_to_hadec(icrs, skyconv_hadec.HADec(obstime=t, location=earth_location, pressure=pressure, obswl=540 * u.nm, temperature=20 * u.deg_C, relative_humidity=0.35))
        >>> hadec.ha.deg, hadec.dec.deg
        (275.7578128072564, 4.108663110053187)
        >>> icrs2 = skyconv_hadec.hadec_to_icrs(hadec, ICRS())
        >>> icrs2.ra.deg, icrs2.dec.deg
        (344.0516175128818, 3.9267726237749687)
    """
    # https://github.com/astropy/astropy/blob/master/astropy/coordinates/builtin_frames/icrs_observed_transforms.py
    # last commit d2c37f3
    # if the data are UnitSphericalRepresentation, we can skip the distance calculations
    is_unitspherical = (isinstance(hadec_coo.data, UnitSphericalRepresentation) or
                        hadec_coo.cartesian.x.unit == u.one)

    usrepr = hadec_coo.represent_as(UnitSphericalRepresentation)
    ha = usrepr.lon.to_value(u.radian)
    odec = usrepr.lat.to_value(u.radian)

    # first set up the astrometry context for ICRS<->CIRS at the altaz_coo time
    astrom = apco(hadec_coo)

    # Topocentric CIRS
    cirs_ra, cirs_dec = erfa.atoiq('H', ha, odec, astrom) << u.radian
    if is_unitspherical:
        srepr = SphericalRepresentation(cirs_ra, cirs_dec, 1, copy=False)
    else:
        srepr = SphericalRepresentation(lon=cirs_ra, lat=cirs_dec,
                                        distance=hadec_coo.distance, copy=False)

    # BCRS (Astrometric) direction to source
    bcrs_ra, bcrs_dec = aticq(srepr, astrom) << u.radian

    # Correct for parallax to get ICRS representation
    if is_unitspherical:
        icrs_srepr = UnitSphericalRepresentation(bcrs_ra, bcrs_dec, copy=False)
    else:
        icrs_srepr = SphericalRepresentation(lon=bcrs_ra, lat=bcrs_dec,
                                             distance=hadec_coo.distance, copy=False)
        observer_icrs = CartesianRepresentation(astrom['eb'], unit=u.au, xyz_axis=-1, copy=False)
        newrepr = icrs_srepr.to_cartesian() + observer_icrs
        icrs_srepr = newrepr.represent_as(SphericalRepresentation)

    return icrs_frame.realize_frame(icrs_srepr)


def apco(frame_or_coord):
    """
    Wrapper for ``erfa.apco``, used in conversions AltAz <-> ICRS and CIRS <-> ICRS

    Arguments
    ---------
    frame_or_coord: ``astropy.coordinates.BaseCoordinateFrame`` or ``astropy.coordinates.SkyCoord``
        Frame or coordinate instance in the corresponding frame
        for which to calculate the calculate the astrom values.
        For this function, an AltAz or CIRS frame is expected.
    """
    # Also from master https://github.com/astropy/astropy/blob/master/astropy/coordinates/erfa_astrom.py
    # 4.3dev last commit 82a3ef4
    lon, lat, height = frame_or_coord.location.to_geodetic('WGS84')
    obstime = frame_or_coord.obstime

    jd1_tt, jd2_tt = get_jd12(obstime, 'tt')
    xp, yp = get_polar_motion(obstime)
    sp = erfa.sp00(jd1_tt, jd2_tt)
    x, y, s = get_cip(jd1_tt, jd2_tt)
    era = erfa.era00(*get_jd12(obstime, 'ut1'))
    earth_pv, earth_heliocentric = prepare_earth_position_vel(obstime)

    # refraction constants
    if hasattr(frame_or_coord, 'pressure'):
        # this is an AltAz like frame. Calculate refraction
        refa, refb = erfa.refco(
            frame_or_coord.pressure.to_value(u.hPa),
            frame_or_coord.temperature.to_value(u.deg_C),
            frame_or_coord.relative_humidity.value,
            frame_or_coord.obswl.to_value(u.micron)
        )
    else:
        # This is not an AltAz frame, so don't bother computing refraction
        refa, refb = 0.0, 0.0

    return erfa.apco(
        jd1_tt, jd2_tt, earth_pv, earth_heliocentric, x, y, s, era,
        lon.to_value(u.radian),
        lat.to_value(u.radian),
        height.to_value(u.m),
        xp, yp, sp, refa, refb
    )
