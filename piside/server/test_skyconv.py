import unittest
from astropy.coordinates import EarthLocation, SkyCoord
import astropy.units as u
from astropy.units import si as usi
from astropy.time import Time as AstroTime
import pendulum
import skyconv

el = EarthLocation(lat=38.9369 * u.deg, lon=-95.242 * u.deg, height=266.0 * u.m)
iso_timestr = "2019-07-18T05:35:23.053Z"  # 12:35am CDT
obstime = AstroTime(pendulum.parse(iso_timestr))

SR_RA = 284.1777484480906


class TestSkyConv(unittest.TestCase):
    def setUp(self):
        pass

    def test_get_sidereal_time(self):
        self.assertAlmostEqual(skyconv.get_sidereal_time(obstime=obstime, earth_location=el).deg, SR_RA, places=5)

    def test_clean_deg(self):
        r = skyconv.clean_deg(91.0, True)
        self.assertEqual(r, (89.0, 1))

        r = skyconv.clean_deg(-91.0, True)
        self.assertEqual(r, (-89.0, 1))

        r = skyconv.clean_deg(-190.0, True)
        self.assertEqual(r, (10.0, 1))

        r = skyconv.clean_deg(190.0, True)
        self.assertEqual(r, (-10.0, 1))

        r = skyconv.clean_deg(390.0, True)
        self.assertEqual(r, (30.0, 2))

        r = skyconv.clean_deg(390.0, False)
        self.assertEqual(r, 30.0)

        r = skyconv.clean_deg(-390.0, False)
        self.assertEqual(r, 330.0)

        r = skyconv.clean_deg(20.0, False)
        self.assertEqual(r, 20.0)

    def test_clean_altaz(self):
        coord = SkyCoord(alt=60 * u.deg, az=20 * u.deg, frame='altaz', location=el, obstime=obstime)
        clean_coord = skyconv.clean_altaz(coord)
        self.assertIsNone(clean_coord.location)

    def test_clean_icrs(self):
        coord = SkyCoord(ra=20 * u.deg, dec=40 * u.deg, frame='icrs', location=el)
        clean_coord = skyconv.clean_icrs(coord)
        self.assertIsNone(clean_coord.location)

    def test_ha_delta_deg(self):
        self.assertEqual(skyconv.ha_delta_deg(359.0, 370.0), 11.0)
        self.assertEqual(skyconv.ha_delta_deg(359.0, -5.0), -4.0)
        self.assertEqual(skyconv.ha_delta_deg(90.0, 92.0), 2.0)
        self.assertEqual(skyconv.ha_delta_deg(-20.0, -5.0), 15.0)

    def test_icrs_to_hadec(self):
        coord = SkyCoord(ra=283 * u.deg, dec=50.0 * u.deg, frame='icrs')
        hadec = skyconv.icrs_to_hadec(coord, obstime=obstime, earth_location=el)
        self.assertAlmostEqual(hadec.ra.deg, skyconv.clean_deg(SR_RA - coord.ra.deg))
        self.assertAlmostEqual(hadec.dec.deg, coord.dec.deg)

    def test_altaz_to_hadec(self):
        coord = SkyCoord(alt=90*u.deg, az=0*u.deg, frame='altaz')
        hadec = skyconv.altaz_to_hadec(coord, obstime=obstime, earth_location=el)
        self.assertEqual(hadec.ra.deg, 0.)
        self.assertEqual(hadec.dec.deg, el.lat.deg)

    def test_hadec_to_icrs(self):
        icrs = SkyCoord(ra=283 * u.deg, dec=50.0 * u.deg, frame='icrs')
        hadec = skyconv.icrs_to_hadec(icrs, obstime=obstime, earth_location=el)
        result = skyconv.hadec_to_icrs(hadec, obstime=obstime, earth_location=el)
        self.assertAlmostEqual(icrs.ra.deg, result.ra.deg)
        self.assertAlmostEqual(icrs.dec.deg, result.dec.deg)

    def test_earth_location_to_pressure(self):
        p = skyconv.earth_location_to_pressure(el).to_value(usi.Pa)
        self.assertAlmostEqual(p, 98170.13549856932)


if __name__ == '__main__':
    unittest.main()
