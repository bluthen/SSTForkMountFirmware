import unittest
import pointing_model
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from skyconv_hadec import HADec
import astropy.units as u
import numpy
import settings

el = EarthLocation(lat=38.9369 * u.deg, lon=-95.242 * u.deg, height=266.0 * u.m)
settings.runtime_settings["earth_location"] = el

ASSERT_PLACES = 4


def assert_almost_equal_list(
    self, one, two, places=ASSERT_PLACES, msg=None, delta=None
):
    assert len(one) == len(two)
    for i in range(len(one)):
        self.assertAlmostEqual(one[i], two[i], places=places, msg=msg, delta=delta)


class TestHelperMethods(unittest.TestCase):
    def test_get_projection_coords(self):
        sp = [
            {"t": {"x": 4.3, "y": 1.2}},
            {"t": {"x": 4.3, "y": 1.2}},
            {"t": {"x": 4.5, "y": 1.3}},
        ]
        result = pointing_model.get_projection_coords([1, 2], sp, "t")
        self.assertEqual(result, [[4.3, 1.2], [4.5, 1.3]])

    def test_alt_az_projection(self):
        a = SkyCoord(AltAz(alt=10 * u.deg, az=90 * u.deg))
        xy = pointing_model.alt_az_projection(a)
        self.assertEqual(xy, {"x": 0.8888888888888888, "y": 0.0})
        a = SkyCoord(
            AltAz(
                alt=[10 * u.deg, 60 * u.deg, 20 * u.deg],
                az=[90 * u.deg, 95 * u.deg, 100 * u.deg],
            )
        )
        xy = pointing_model.alt_az_projection(a)
        assert_almost_equal_list(
            self, xy["x"].tolist(), [0.88888889, 0.3320649, 0.76596159]
        )
        assert_almost_equal_list(
            self, xy["y"].tolist(), [0.0, -0.02905191, -0.13505969]
        )

    def test_inverse_altaz_projection(self):
        xy = {"x": 0.8888888888888888, "y": 0.0}
        b = pointing_model.inverse_altaz_projection(xy)
        self.assertEqual((b.alt.deg, b.az.deg), (10.000000000000004, 90.0))
        xy = {
            "x": numpy.array([0.88888889, 0.3320649, 0.76596159]),
            "y": numpy.array([0.0, -0.02905191, -0.13505969]),
        }
        b = pointing_model.inverse_altaz_projection(xy)
        assert_almost_equal_list(
            self, b.alt.deg.tolist(), [9.9999999, 59.99999998, 19.99999968]
        )
        assert_almost_equal_list(
            self, b.az.deg.tolist(), [90.0, 94.99999926, 99.99999967]
        )

    def test_tr_point_in_triangle(self):
        import pointing_model

        t1 = pointing_model.tr_point_in_triangle(
            [95.0, 50.0], [90.0, 10.0], [95.0, 60.0], [100, 20.0]
        )
        t2 = pointing_model.tr_point_in_triangle(
            [90.0, 50.0], [90.0, 10.0], [95.0, 60.0], [100, 20.0]
        )
        t3 = pointing_model.tr_point_in_triangle(
            [90.0, 30.0], [45.0, 20.0], [135.0, 20.0], [175, 80.0]
        )
        self.assertEqual((t1, t2, t3), (True, False, True))


class TestPointingModelBuie(unittest.TestCase):
    def setUp(self):
        self.pm = pointing_model.PointingModelBuie()

    def test_unity(self):
        sync_point = HADec(dec=10 * u.deg, ha=90 * u.deg)
        stepper_point = HADec(dec=10 * u.deg, ha=90 * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        sync_point = HADec(dec=60 * u.deg, ha=95 * u.deg)
        stepper_point = HADec(dec=60 * u.deg, ha=95 * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        sync_point = HADec(dec=20 * u.deg, ha=100 * u.deg)
        stepper_point = HADec(dec=20 * u.deg, ha=100 * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        point = HADec(dec=50 * u.deg, ha=95 * u.deg)
        tpt = self.pm.transform_point(point)
        self.assertEqual((tpt.ha.deg, tpt.dec.deg), (95.0, 50.0))
        tpt = self.pm.inverse_transform_point(tpt)
        self.assertEqual((tpt.ha.deg, tpt.dec.deg), (95.0, 50.0))

    def test_two_point_unity(self):
        sync_point = HADec(dec=10 * u.deg, ha=90 * u.deg)
        stepper_point = HADec(dec=10 * u.deg, ha=90 * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        sync_point = HADec(dec=60 * u.deg, ha=95 * u.deg)
        stepper_point = HADec(dec=60 * u.deg, ha=95 * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        point = HADec(dec=50 * u.deg, ha=95 * u.deg)
        tpt = self.pm.transform_point(point)
        self.assertEqual((tpt.ha.deg, tpt.dec.deg), (95.0, 50.0))
        tpt = self.pm.inverse_transform_point(tpt)
        self.assertEqual((tpt.ha.deg, tpt.dec.deg), (95.0, 50.0))

    def test_twop_stretch(self):
        sync_point = HADec(dec=10 * u.deg, ha=90 * u.deg)
        stepper_point = HADec(dec=10 * u.deg, ha=90 * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        sync_point = HADec(dec=60 * u.deg, ha=95 * u.deg)
        stepper_point = HADec(
            dec=(10 + (60 - 10) * 1.02) * u.deg, ha=(90 + (95 - 90) * 1.02) * u.deg
        )
        self.pm.add_point(sync_point, stepper_point)
        sync_point = HADec(dec=20 * u.deg, ha=100 * u.deg)
        stepper_point = HADec(
            dec=(10 + (20 - 10) * 1.02) * u.deg, ha=(90 + (100 - 90) * 1.02) * u.deg
        )
        self.pm.add_point(sync_point, stepper_point)
        point = HADec(dec=50 * u.deg, ha=95 * u.deg)
        tpt = self.pm.transform_point(point)
        # TODO: Really expect 95.1 and 50.8, is this close enough?
        numpy.testing.assert_almost_equal((tpt.ha.deg, tpt.dec.deg), (95.1, 50.4), 4)
        tpt = self.pm.inverse_transform_point(tpt)
        # TODO: Really expect 95.0 and 50.0, is this close enough
        numpy.testing.assert_almost_equal(
            (tpt.ha.deg, tpt.dec.deg), (95.0000, 50.0000), 4
        )

    def test_one_degree(self):
        sync_point = HADec(dec=10 * u.deg, ha=90 * u.deg)
        stepper_point = HADec(dec=10 * u.deg, ha=90 * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        sync_point = HADec(dec=60 * u.deg, ha=95 * u.deg)
        sp = pointing_model.test_hadec_transform(10.0, 3.0, 60.0, 95.0, 1.0)
        stepper_point = HADec(dec=sp["dec"] * u.deg, ha=sp["ha"] * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        sync_point = HADec(dec=20 * u.deg, ha=100 * u.deg)
        sp = pointing_model.test_hadec_transform(10.0, 3.0, 20.0, 100.0, 1.0)
        stepper_point = HADec(dec=sp["dec"] * u.deg, ha=sp["ha"] * u.deg)
        self.pm.add_point(sync_point, stepper_point)

        sync_point = HADec(dec=-33 * u.deg, ha=40 * u.deg)
        sp = pointing_model.test_hadec_transform(10.0, 3.0, -33.0, 40.0, 1.0)
        stepper_point = HADec(dec=sp["dec"] * u.deg, ha=sp["ha"] * u.deg)
        self.pm.add_point(sync_point, stepper_point)

        sync_point = HADec(dec=-53 * u.deg, ha=4 * u.deg)
        sp = pointing_model.test_hadec_transform(10.0, 3.0, -53.0, 4.0, 1.0)
        stepper_point = HADec(dec=sp["dec"] * u.deg, ha=sp["ha"] * u.deg)
        self.pm.add_point(sync_point, stepper_point)

        sync_point = HADec(dec=-70 * u.deg, ha=60 * u.deg)
        sp = pointing_model.test_hadec_transform(10.0, 3.0, -70.0, 60.0, 1.0)
        stepper_point = HADec(dec=sp["dec"] * u.deg, ha=sp["ha"] * u.deg)
        self.pm.add_point(sync_point, stepper_point)

        point = HADec(dec=50 * u.deg, ha=95 * u.deg)
        tpt = self.pm.transform_point(point)
        numpy.testing.assert_almost_equal(
            (tpt.ha.deg, tpt.dec.deg), (95.57058308, 48.70252532), 4
        )
        tpt = self.pm.inverse_transform_point(tpt)
        numpy.testing.assert_almost_equal(
            (tpt.ha.deg, tpt.dec.deg), (94.99997885310887, 49.999988412567774), 4
        )

    def test_single(self):
        point1 = HADec(dec=10 * u.deg, ha=90 * u.deg)
        point2 = HADec(dec=60 * u.deg, ha=95 * u.deg)
        point3 = HADec(dec=21.212 * u.deg, ha=13.123 * u.deg)
        point4 = HADec(dec=-75.232 * u.deg, ha=272.23 * u.deg)
        for pt_add in [point1, point2, point3, point4]:
            self.pm.clear()
            self.pm.add_point(pt_add, pt_add)
            for pt in [point1, point2, point3, point4]:
                tpt = self.pm.transform_point(pt)
                self.assertEqual((tpt.ha.deg, tpt.dec.deg), (pt.ha.deg, pt.dec.deg))

    def test_clear(self):
        self.test_twop_stretch()
        self.pm.clear()
        self.test_one_degree()


class PointingModelAffine(unittest.TestCase):
    def setUp(self):
        self.pm = pointing_model.PointingModelAffine()

    def test_unity(self):
        sync_point = AltAz(alt=10 * u.deg, az=90 * u.deg)
        stepper_point = AltAz(alt=10 * u.deg, az=90 * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        sync_point = AltAz(alt=60 * u.deg, az=95 * u.deg)
        stepper_point = AltAz(alt=60 * u.deg, az=95 * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        sync_point = AltAz(alt=20 * u.deg, az=100 * u.deg)
        stepper_point = AltAz(alt=20 * u.deg, az=100 * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        point = AltAz(alt=50 * u.deg, az=95 * u.deg)
        tpt = self.pm.transform_point(point)
        self.assertEqual((tpt.alt.deg, tpt.az.deg), (50.0, 95.0))
        tpt = self.pm.inverse_transform_point(tpt)
        self.assertEqual((tpt.alt.deg, tpt.az.deg), (50.0, 95.0))

    def test_two_point_unit(self):
        sync_point = AltAz(alt=10 * u.deg, az=90 * u.deg)
        stepper_point = AltAz(alt=10 * u.deg, az=90 * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        sync_point = AltAz(alt=60 * u.deg, az=95 * u.deg)
        stepper_point = AltAz(alt=60 * u.deg, az=95 * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        point = AltAz(alt=50 * u.deg, az=95 * u.deg)
        tpt = self.pm.transform_point(point)
        self.assertEqual((tpt.alt.deg, tpt.az.deg), (50.0, 95.0))
        tpt = self.pm.inverse_transform_point(tpt)
        self.assertEqual((tpt.alt.deg, tpt.az.deg), (50.0, 95.0))

    def test_twop_stretch(self):
        sync_point = AltAz(alt=10 * u.deg, az=90 * u.deg)
        stepper_point = AltAz(alt=10 * u.deg, az=90 * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        sync_point = AltAz(alt=60 * u.deg, az=95 * u.deg)
        stepper_point = AltAz(
            alt=(10 + (60 - 10) * 1.02) * u.deg, az=(90 + (95 - 90) * 1.02) * u.deg
        )
        self.pm.add_point(sync_point, stepper_point)
        sync_point = AltAz(alt=20 * u.deg, az=100 * u.deg)
        stepper_point = AltAz(
            alt=(10 + (20 - 10) * 1.02) * u.deg, az=(90 + (100 - 90) * 1.02) * u.deg
        )
        self.pm.add_point(sync_point, stepper_point)
        point = AltAz(alt=50 * u.deg, az=95 * u.deg)
        tpt = self.pm.transform_point(point)
        self.assertEqual(
            (tpt.alt.deg, tpt.az.deg), (50.80120905913654, 95.09687722671514)
        )
        tpt = self.pm.inverse_transform_point(tpt)
        self.assertEqual(
            (tpt.alt.deg, tpt.az.deg), (49.999999999999986, 94.99999999999999)
        )

    def test_one_degree(self):
        sync_point = AltAz(alt=10 * u.deg, az=90 * u.deg)
        stepper_point = AltAz(alt=10 * u.deg, az=90 * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        sync_point = AltAz(alt=60 * u.deg, az=95 * u.deg)
        sp = pointing_model.test_altaz_transform(10.0, 90.0, 60.0, 95.0, 1.0)
        stepper_point = AltAz(alt=sp["alt"] * u.deg, az=sp["az"] * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        sync_point = AltAz(alt=20 * u.deg, az=100 * u.deg)
        sp = pointing_model.test_altaz_transform(10.0, 90.0, 20.0, 100.0, 1.0)
        stepper_point = AltAz(alt=sp["alt"] * u.deg, az=sp["az"] * u.deg)
        self.pm.add_point(sync_point, stepper_point)
        point = AltAz(alt=50 * u.deg, az=95 * u.deg)
        tpt = self.pm.transform_point(point)
        self.assertEqual(
            (tpt.alt.deg, tpt.az.deg), (50.08108010292904, 94.4534133318961)
        )
        tpt = self.pm.inverse_transform_point(tpt)
        self.assertEqual(
            (tpt.alt.deg, tpt.az.deg), (49.99999999999997, 94.99999999999999)
        )

    def test_clear(self):
        self.test_twop_stretch()
        self.pm.clear()
        self.test_one_degree()


if __name__ == "__main__":
    unittest.main()
