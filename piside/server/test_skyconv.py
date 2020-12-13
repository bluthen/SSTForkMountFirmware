import unittest
from astropy.coordinates import EarthLocation, ICRS, AltAz, TETE
from skyconv_hadec import HADec
import astropy.units as u
from astropy.units import si as usi
from astropy.time import Time as AstroTime
import pendulum
import skyconv
import settings

# 38d23m48.8s  95d14m31.2s
el = EarthLocation(lat=38.9369 * u.deg, lon=-95.242 * u.deg, height=266.0 * u.m)
settings.runtime_settings['earth_location'] = el
iso_timestr = "2019-07-18T05:35:23.053Z"  # 12:35am CDT
obstime = AstroTime(pendulum.parse(iso_timestr))

SR_RA = 284.3476512387979  # 18:57:23.4
# KStars 18:57:24
# SR_RA = 284.3520833333333 # stellariums

# m75 = SkyCoord.from_name('m75')
m75_icrs = ICRS(ra=301.52017083 * u.deg, dec=-21.92226111 * u.deg)
# These are from previous ircs->coord calculations, that seems close to KStars
m75_tete = TETE(ra=301.8090381273364 * u.deg, dec=-21.864148464527666 * u.deg,
                **(skyconv.get_frame_init_args('tete', obstime=obstime)))
m75_altaz = AltAz(alt=27.067210767906897 * u.deg, az=161.7810984394531 * u.deg,
                  **(skyconv.get_frame_init_args('altaz', obstime=obstime)))
m75_hadec = HADec(ha=342.54699618235094 * u.deg, dec=-21.835812539832737 * u.deg,
                  **(skyconv.get_frame_init_args('hadec', obstime=obstime)))

ALMOST_PLACES = 4 # Half arc-second


# KSTARS
# J2000 301.52000000000004, -21.922222222222224
# JNow  301.8088333333333, -21.86411388888889
# HADec 342.5416666666667, -21.86411388888889
# Altaz: 27.55138888888889, 161.69611111111112


class TestSkyConv(unittest.TestCase):

    def test_get_sidereal_time(self):
        self.assertAlmostEqual(skyconv.get_sidereal_time(obstime=obstime).deg, SR_RA, places=ALMOST_PLACES)

    def test_icrs_to_hadec(self):
        hadec, atm = skyconv._icrs_to_hadec(m75_icrs, obstime=obstime)
        self.assertAlmostEqual(hadec.ha.deg, m75_hadec.ha.deg, places=ALMOST_PLACES)  # 22h50m:9.28s
        self.assertAlmostEqual(hadec.dec.deg, m75_hadec.dec.deg, places=ALMOST_PLACES)  # -21d51m51.36s
        self.assertEqual(atm, True)

    def test_icrs_to_altaz(self):
        altaz, atm = skyconv._icrs_to_altaz(m75_icrs, obstime=obstime)
        self.assertAlmostEqual(altaz.alt.deg, m75_altaz.alt.deg, places=ALMOST_PLACES)
        self.assertAlmostEqual(altaz.az.deg, m75_altaz.az.deg, places=ALMOST_PLACES)
        self.assertEqual(atm, True)

    def test_icrs_to_tete(self):
        tete = skyconv._icrs_to_tete(m75_icrs, obstime=obstime)
        self.assertAlmostEqual(tete.ra.deg, m75_tete.ra.deg, places=ALMOST_PLACES)
        self.assertAlmostEqual(tete.dec.deg, m75_tete.dec.deg, places=ALMOST_PLACES)

    def test_tete_to_hadec(self):
        hadec, atm = skyconv._tete_to_hadec(m75_tete)
        self.assertAlmostEqual(hadec.ha.deg, m75_hadec.ha.deg, places=ALMOST_PLACES)
        self.assertAlmostEqual(hadec.dec.deg, m75_hadec.dec.deg, places=ALMOST_PLACES)
        self.assertEqual(atm, True)

    def test_tete_to_icrs(self):
        icrs = skyconv._tete_to_icrs(m75_tete)
        self.assertAlmostEqual(icrs.ra.deg, m75_icrs.ra.deg, places=ALMOST_PLACES)
        self.assertAlmostEqual(icrs.dec.deg, m75_icrs.dec.deg, places=ALMOST_PLACES)

    def test_tete_to_altaz(self):
        altaz, atm = skyconv._tete_to_altaz(m75_tete)
        self.assertAlmostEqual(altaz.alt.deg, m75_altaz.alt.deg, places=ALMOST_PLACES)
        self.assertAlmostEqual(altaz.az.deg, m75_altaz.az.deg, places=ALMOST_PLACES)
        self.assertEqual(atm, True)

    def test_altaz_to_hadec(self):
        hadec, atm = skyconv._altaz_to_hadec(m75_altaz)
        self.assertAlmostEqual(hadec.ha.deg, m75_hadec.ha.deg, places=ALMOST_PLACES)
        self.assertAlmostEqual(hadec.dec.deg, m75_hadec.dec.deg, places=ALMOST_PLACES)
        self.assertEqual(atm, True)

    def test_altaz_to_icrs(self):
        icrs, atm = skyconv._altaz_to_icrs(m75_altaz)
        self.assertAlmostEqual(icrs.ra.deg, m75_icrs.ra.deg, places=ALMOST_PLACES)
        self.assertAlmostEqual(icrs.dec.deg, m75_icrs.dec.deg, places=ALMOST_PLACES)
        self.assertEqual(atm, True)

    def test_altaz_to_tete(self):
        tete, atm = skyconv._altaz_to_tete(m75_altaz)
        self.assertAlmostEqual(tete.ra.deg, m75_tete.ra.deg, places=ALMOST_PLACES)
        self.assertAlmostEqual(tete.dec.deg, m75_tete.dec.deg, places=ALMOST_PLACES)
        self.assertEqual(atm, True)

    def test_hadec_to_tete(self):
        tete, atm = skyconv._hadec_to_tete(m75_hadec)
        self.assertAlmostEqual(tete.ra.deg, m75_tete.ra.deg, places=ALMOST_PLACES)
        self.assertAlmostEqual(tete.dec.deg, m75_tete.dec.deg, places=ALMOST_PLACES)
        self.assertEqual(atm, True)

    def test_hadec_to_icrs(self):
        icrs, atm = skyconv._hadec_to_icrs(m75_hadec)
        self.assertAlmostEqual(icrs.ra.deg, m75_icrs.ra.deg, places=ALMOST_PLACES)
        self.assertAlmostEqual(icrs.dec.deg, m75_icrs.dec.deg, places=ALMOST_PLACES)
        self.assertEqual(atm, True)

    def test_hadec_to_altaz(self):
        altaz, atm = skyconv._hadec_to_altaz(m75_hadec)
        self.assertAlmostEqual(altaz.alt.deg, m75_altaz.alt.deg, places=ALMOST_PLACES)
        self.assertAlmostEqual(altaz.az.deg, m75_altaz.az.deg, places=ALMOST_PLACES)
        self.assertEqual(atm, True)

    def test_get_frame_init_args(self):
        pass

    def test_ha_delta_deg(self):
        self.assertEqual(skyconv._ha_delta_deg(359.0, 370.0), 11.0)
        self.assertEqual(skyconv._ha_delta_deg(359.0, -5.0), -4.0)
        self.assertEqual(skyconv._ha_delta_deg(90.0, 92.0), 2.0)
        self.assertEqual(skyconv._ha_delta_deg(-20.0, -5.0), 15.0)

    def test_hadec_to_steps(self):
        pass

    def test_altaz_threshold_fix_pressure(self):
        frame_args = skyconv.get_frame_init_args('altaz', obstime=obstime)
        altaz = AltAz(alt=4 * u.deg, az=180 * u.deg, **frame_args)
        altaz = skyconv._altaz_threshold_fix_pressure(altaz)
        self.assertAlmostEqual(altaz.pressure.value, 0.)

    def test_to_altaz(self):
        for coord in [m75_altaz, m75_hadec, m75_icrs, m75_tete]:
            self.assertEqual(skyconv.to_altaz(coord).name, 'altaz')

    def test_to_icrs(self):
        for coord in [m75_altaz, m75_hadec, m75_icrs, m75_tete]:
            self.assertEqual(skyconv.to_icrs(coord).name, 'icrs')

    def test_to_hadec(self):
        for coord in [m75_altaz, m75_hadec, m75_icrs, m75_tete]:
            self.assertEqual(skyconv.to_hadec(coord).name, 'hadec')

    def test_to_tete(self):
        for coord in [m75_altaz, m75_hadec, m75_icrs, m75_tete]:
            self.assertEqual(skyconv.to_tete(coord).name, 'tete')

    def test_to_steps(self):
        pass

    def test_steps_to_coord(self):
        pass

    def test_clean_deg(self):
        r = skyconv._clean_deg(91.0, True)
        self.assertEqual(r, (89.0, 1))

        r = skyconv._clean_deg(-91.0, True)
        self.assertEqual(r, (-89.0, 1))

        r = skyconv._clean_deg(-190.0, True)
        self.assertEqual(r, (10.0, 1))

        r = skyconv._clean_deg(190.0, True)
        self.assertEqual(r, (-10.0, 1))

        r = skyconv._clean_deg(390.0, True)
        self.assertEqual(r, (30.0, 2))

        r = skyconv._clean_deg(390.0, False)
        self.assertEqual(r, 30.0)

        r = skyconv._clean_deg(-390.0, False)
        self.assertEqual(r, 330.0)

        r = skyconv._clean_deg(20.0, False)
        self.assertEqual(r, 20.0)

    def test_earth_location_to_pressure(self):
        p = skyconv._earth_location_to_pressure(el).to_value(usi.Pa)
        self.assertAlmostEqual(p, 98170.13549856932)


if __name__ == '__main__':
    unittest.main()
