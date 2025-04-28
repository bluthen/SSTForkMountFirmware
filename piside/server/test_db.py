import unittest
import db

import astropy.units as u
import pendulum
from astropy.time import Time as AstroTime
from astropy.coordinates import EarthLocation
import settings

el = EarthLocation(lat=38.9369 * u.deg, lon=-95.242 * u.deg, height=266.0 * u.m)
settings.runtime_settings['earth_location'] = el
iso_timestr = "2019-07-18T05:35:23.053Z"  # 12:35am CDT
obstime = AstroTime(pendulum.parse(iso_timestr))
ALMOST_PLACES = 4  # Half arc-second


class TestDB(unittest.TestCase):
    def test_search_planets_moon(self):
        result = db.search_planets('moon', obstime, el)[0]
        self.assertAlmostEqual(result['ra'], 313.3399, places=ALMOST_PLACES)
        self.assertAlmostEqual(result['dec'], -20.4567, places=ALMOST_PLACES)
        self.assertAlmostEqual(result['alt'], 24.6883, places=ALMOST_PLACES)
        self.assertAlmostEqual(result['az'], 149.71244, places=ALMOST_PLACES)


if __name__ == '__main__':
    unittest.main()
