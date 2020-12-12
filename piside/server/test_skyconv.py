import unittest
from astropy.coordinates import EarthLocation, ICRS, AltAz, TETE
from skyconv_hadec import HADec
import astropy.units as u
from astropy.units import si as usi
from astropy.time import Time as AstroTime
import pendulum
import skyconv
import settings

el = EarthLocation(lat=38.9369 * u.deg, lon=-95.242 * u.deg, height=266.0 * u.m)
iso_timestr = "2019-07-18T05:35:23.053Z"  # 12:35am CDT
obstime = AstroTime(pendulum.parse(iso_timestr))

SR_RA = 284.1777484480906


class TestSkyConv(unittest.TestCase):
    def setUp(self):
        settings.runtime_settings['earth_location'] = el

    def test_get_sidereal_time(self):
        self.assertAlmostEqual(skyconv.get_sidereal_time(obstime=obstime).deg, SR_RA, places=5)

    def test_icrs_to_hadec(self):
        coord = ICRS(ra=283 * u.deg, dec=50.0 * u.deg)
        hadec, atm = skyconv._icrs_to_hadec(coord, obstime=obstime)
        self.assertAlmostEqual(hadec.ra.deg, skyconv._clean_deg(SR_RA - coord.ra.deg))
        self.assertAlmostEqual(hadec.dec.deg, coord.dec.deg)

    def test_altaz_to_hadec(self):
        coord = AltAz(alt=90 * u.deg, az=0 * u.deg, obstime=t)
        hadec = skyconv._altaz_to_hadec(coord)
        self.assertEqual(hadec.ha.deg, 0.)
        self.assertEqual(hadec.dec.deg, el.lat.deg)

    def test_get_frame_init_args(self):
        pass

    def test_hadec_to_icrs(self):
        icrs = ICRS(ra=223 * u.deg, dec=50.0 * u.deg)
        hadec = skyconv._icrs_to_hadec(icrs, obstime=obstime)
        result = skyconv._hadec_to_icrs(hadec)
        self.assertAlmostEqual(icrs.ra.deg, result.ra.deg)
        self.assertAlmostEqual(icrs.dec.deg, result.dec.deg)

    def test_hadec_to_altaz(self):
        pass

    def test_ha_delta_deg(self):
        self.assertEqual(skyconv._ha_delta_deg(359.0, 370.0), 11.0)
        self.assertEqual(skyconv._ha_delta_deg(359.0, -5.0), -4.0)
        self.assertEqual(skyconv._ha_delta_deg(90.0, 92.0), 2.0)
        self.assertEqual(skyconv._ha_delta_deg(-20.0, -5.0), 15.0)

    def test_hadec_to_steps(self):
        pass

    def test_altaz_threshold_fix_pressure(self):
        pass

    def test_altaz_to_icrs(self):
        t = AstroTime('2018-12-26T22:55:32.281', format='isot', scale='utc')
        skyconv.get_frame_init_args('altaz', obstime=t)
        b = AltAz(alt=80*u.deg, az=90*u.deg, **frame_args)
        icrs, atm = skyconv._altaz_to_icrs(b)
        self.assertAlmostEqual(icrs.ra.deg, 356.5643249365523)
        self.assertAlmostEqual(icrs.dec.deg, 38.12981040209684)
        self.assertEqual(atm, True)

    def test_icrs_to_altaz(self):
        t = AstroTime('2018-12-26T22:55:32.281', format='isot', scale='utc')
        icrs = ICRS(ra=30*u.deg, dec=45*u.deg, frame='icrs')
        altaz, atm = skyconv._icrs_to_altaz(icrs, obstime=t)
        self.assertAlmostEqual(altaz.alt.deg, 55.558034184006516)
        self.assertAlmostEqual(altaz.az.deg, 64.41850865846912)
        self.assertEqual(atm, True)


    def test_tete_to_hadec(self):
        pass

    def test_icrs_to_tete(self):
        pass

    def test_tete_to_icrs(self):
        pass

    def test_hadec_to_tete(self):
        pass

    def test_tete_to_altaz(self):
        pass

    def test_altaz_to_tete(self):
        pass

    def tesT_to_steps(self):
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
