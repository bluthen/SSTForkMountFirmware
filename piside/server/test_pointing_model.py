import unittest
import pointing_model
from astropy.coordinates import SkyCoord
import numpy
import sys


def assert_almost_equal_list(self, one, two, places=6, msg=None, delta=None):
    assert len(one) == len(two)
    for i in range(len(one)):
        self.assertAlmostEqual(one[i], two[i], places=places, msg=msg, delta=delta)


class TestHelperMethods(unittest.TestCase):
    def test_get_projection_coords(self):
        sp = [{'t': {'x': 4.3, 'y': 1.2}}, {'t': {'x': 4.3, 'y': 1.2}}, {'t': {'x': 4.5, 'y': 1.3}}]
        result = pointing_model.get_projection_coords([1, 2], sp, 't')
        self.assertEqual(result, [[4.3, 1.2], [4.5, 1.3]])

    def test_alt_az_projection(self):
        a = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
        xy = pointing_model.alt_az_projection(a)
        self.assertEqual(xy, {'x': 0.8888888888888888, 'y': 0.0})
        a = SkyCoord(alt=[10, 60, 20], az=[90, 95, 100], unit='deg', frame='altaz')
        xy = pointing_model.alt_az_projection(a)
        assert_almost_equal_list(self, xy['x'].tolist(), [0.88888889, 0.3320649, 0.76596159], places=7)
        assert_almost_equal_list(self, xy['y'].tolist(), [0., -0.02905191, -0.13505969], places=7)

    def test_inverse_altaz_projection(self):
        xy = {'x': 0.8888888888888888, 'y': 0.0}
        b = pointing_model.inverse_altaz_projection(xy)
        self.assertEqual((b.alt.deg, b.az.deg), (10.000000000000004, 90.0))
        xy = {'x': numpy.array([0.88888889, 0.3320649, 0.76596159]), 'y': numpy.array([0., -0.02905191, -0.13505969])}
        b = pointing_model.inverse_altaz_projection(xy)
        assert_almost_equal_list(self, b.alt.deg.tolist(), [9.9999999, 59.99999998, 19.99999968])
        assert_almost_equal_list(self, b.az.deg.tolist(), [90., 94.99999926, 99.99999967])

    def test_tr_point_in_triangle(self):
        import pointing_model
        t1 = pointing_model.tr_point_in_triangle([95., 50.], [90., 10.], [95., 60.0], [100, 20.0])
        t2 = pointing_model.tr_point_in_triangle([90., 50.], [90., 10.], [95., 60.0], [100, 20.0])
        t3 = pointing_model.tr_point_in_triangle([90., 30.], [45., 20.], [135., 20.0], [175, 80.0])
        self.assertEqual((t1, t2, t3), (True, False, True))


class TestPointingModelBuie(unittest.TestCase):
    def setUp(self):
        self.pm = pointing_model.PointingModelBuie()

    def test_unity(self):
        sync_point = SkyCoord(dec=10, ra=90, unit='deg', frame='icrs')
        stepper_point = SkyCoord(dec=10, ra=90, unit='deg', frame='icrs')
        self.pm.add_point(sync_point, stepper_point)
        sync_point = SkyCoord(dec=60, ra=95, unit='deg', frame='icrs')
        stepper_point = SkyCoord(dec=60, ra=95, unit='deg', frame='icrs')
        self.pm.add_point(sync_point, stepper_point)
        sync_point = SkyCoord(dec=20, ra=100, unit='deg', frame='icrs')
        stepper_point = SkyCoord(dec=20, ra=100, unit='deg', frame='icrs')
        self.pm.add_point(sync_point, stepper_point)
        point = SkyCoord(dec=50, ra=95, unit='deg', frame='icrs')
        tpt = self.pm.transform_point(point)
        self.assertEqual((tpt.ra.deg, tpt.dec.deg), (95.0, 50.0))
        tpt = self.pm.inverse_transform_point(tpt)
        self.assertEqual((tpt.ra.deg, tpt.dec.deg), (95.0, 50.0))

    def test_two_point_unity(self):
        sync_point = SkyCoord(dec=10, ra=90, unit='deg', frame='icrs')
        stepper_point = SkyCoord(dec=10, ra=90, unit='deg', frame='icrs')
        self.pm.add_point(sync_point, stepper_point)
        sync_point = SkyCoord(dec=60, ra=95, unit='deg', frame='icrs')
        stepper_point = SkyCoord(dec=60, ra=95, unit='deg', frame='icrs')
        self.pm.add_point(sync_point, stepper_point)
        point = SkyCoord(dec=50, ra=95, unit='deg', frame='icrs')
        tpt = self.pm.transform_point(point)
        self.assertEqual((tpt.ra.deg, tpt.dec.deg), (95.0, 50.0))
        tpt = self.pm.inverse_transform_point(tpt)
        self.assertEqual((tpt.ra.deg, tpt.dec.deg), (95.0, 50.0))

    def test_twop_stretch(self):
        sync_point = SkyCoord(dec=10, ra=90, unit='deg', frame='icrs')
        stepper_point = SkyCoord(dec=10, ra=90, unit='deg', frame='icrs')
        self.pm.add_point(sync_point, stepper_point)
        sync_point = SkyCoord(dec=60, ra=95, unit='deg', frame='icrs')
        stepper_point = SkyCoord(dec=10 + (60 - 10) * 1.02, ra=90 + (95 - 90) * 1.02, unit='deg', frame='icrs')
        self.pm.add_point(sync_point, stepper_point)
        sync_point = SkyCoord(dec=20, ra=100, unit='deg', frame='icrs')
        stepper_point = SkyCoord(dec=10 + (20 - 10) * 1.02, ra=90 + (100 - 90) * 1.02, unit='deg', frame='icrs')
        self.pm.add_point(sync_point, stepper_point)
        point = SkyCoord(dec=50, ra=95, unit='deg', frame='icrs')
        tpt = self.pm.transform_point(point)
        # TODO: Really expect 95.1 and 50.8, is this close enough?
        assert_almost_equal_list(self, (tpt.ra.deg, tpt.dec.deg), (95.1016616, 50.7997827))
        tpt = self.pm.inverse_transform_point(tpt)
        # TODO: Really expect 95.0 and 50.0, is this close enough
        assert_almost_equal_list(self, (tpt.ra.deg, tpt.dec.deg), (94.9999727, 50.000011))

    def test_one_degree(self):
        sync_point = SkyCoord(dec=10, ra=90, unit='deg', frame='icrs')
        stepper_point = SkyCoord(dec=10, ra=90, unit='deg', frame='icrs')
        self.pm.add_point(sync_point, stepper_point)
        sync_point = SkyCoord(dec=60, ra=95, unit='deg', frame='icrs')
        sp = pointing_model.test_hadec_transform(10.0, 90.0, 60., 95.0, 1.)
        stepper_point = SkyCoord(dec=sp['dec'], ra=sp['ha'], unit='deg', frame='icrs')
        self.pm.add_point(sync_point, stepper_point)
        sync_point = SkyCoord(dec=20, ra=100, unit='deg', frame='icrs')
        sp = pointing_model.test_hadec_transform(10.0, 90.0, 20., 100.0, 1.0)
        stepper_point = SkyCoord(dec=sp['dec'], ra=sp['ha'], unit='deg', frame='icrs')
        self.pm.add_point(sync_point, stepper_point)
        point = SkyCoord(dec=50, ra=95, unit='deg', frame='icrs')
        tpt = self.pm.transform_point(point)
        self.assertEqual((tpt.ra.deg, tpt.dec.deg), (95.42570155323564, 49.90590943208097))
        tpt = self.pm.inverse_transform_point(tpt)
        self.assertEqual((tpt.ra.deg, tpt.dec.deg), (94.99998504751636, 49.9999766439837))

    def test_single(self):
        point1 = SkyCoord(dec=10, ra=90, unit='deg', frame='icrs')
        point2 = SkyCoord(dec=60, ra=95, unit='deg', frame='icrs')
        point3 = SkyCoord(dec=21.212, ra=13.123, unit='deg', frame='icrs')
        point4 = SkyCoord(dec=-75.232, ra=272.23, unit='deg', frame='icrs')
        for pt_add in [point1, point2, point3, point4]:
            self.pm.clear()
            self.pm.add_point(pt_add, pt_add)
            for pt in [point1, point2, point3, point4]:
                tpt = self.pm.transform_point(pt)
                self.assertEqual((tpt.ra.deg, tpt.dec.deg), (pt.ra.deg, pt.dec.deg))

    def test_clear(self):
        self.test_twop_stretch()
        self.pm.clear()
        self.test_one_degree()


class PointingModelAffine(unittest.TestCase):
    def setUp(self):
        self.pm = pointing_model.PointingModelAffine()

    def test_unity(self):
        sync_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
        stepper_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
        self.pm.add_point(sync_point, stepper_point)
        sync_point = SkyCoord(alt=60, az=95, unit='deg', frame='altaz')
        stepper_point = SkyCoord(alt=60, az=95, unit='deg', frame='altaz')
        self.pm.add_point(sync_point, stepper_point)
        sync_point = SkyCoord(alt=20, az=100, unit='deg', frame='altaz')
        stepper_point = SkyCoord(alt=20, az=100, unit='deg', frame='altaz')
        self.pm.add_point(sync_point, stepper_point)
        point = SkyCoord(alt=50, az=95, unit='deg', frame='altaz')
        tpt = self.pm.transform_point(point)
        self.assertEqual((tpt.alt.deg, tpt.az.deg), (50.0, 95.0))
        tpt = self.pm.inverse_transform_point(tpt)
        self.assertEqual((tpt.alt.deg, tpt.az.deg), (50.0, 95.0))

    def test_two_point_unit(self):
        sync_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
        stepper_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
        self.pm.add_point(sync_point, stepper_point)
        sync_point = SkyCoord(alt=60, az=95, unit='deg', frame='altaz')
        stepper_point = SkyCoord(alt=60, az=95, unit='deg', frame='altaz')
        self.pm.add_point(sync_point, stepper_point)
        point = SkyCoord(alt=50, az=95, unit='deg', frame='altaz')
        tpt = self.pm.transform_point(point)
        self.assertEqual((tpt.alt.deg, tpt.az.deg), (50.0, 95.0))
        tpt = self.pm.inverse_transform_point(tpt)
        self.assertEqual((tpt.alt.deg, tpt.az.deg), (50.0, 95.0))

    def test_twop_stretch(self):
        sync_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
        stepper_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
        self.pm.add_point(sync_point, stepper_point)
        sync_point = SkyCoord(alt=60, az=95, unit='deg', frame='altaz')
        stepper_point = SkyCoord(alt=10 + (60 - 10) * 1.02, az=90 + (95 - 90) * 1.02, unit='deg', frame='altaz')
        self.pm.add_point(sync_point, stepper_point)
        sync_point = SkyCoord(alt=20, az=100, unit='deg', frame='altaz')
        stepper_point = SkyCoord(alt=10 + (20 - 10) * 1.02, az=90 + (100 - 90) * 1.02, unit='deg', frame='altaz')
        self.pm.add_point(sync_point, stepper_point)
        point = SkyCoord(alt=50, az=95, unit='deg', frame='altaz')
        tpt = self.pm.transform_point(point)
        self.assertEqual((tpt.alt.deg, tpt.az.deg), (50.80120905913654, 95.09687722671514))
        tpt = self.pm.inverse_transform_point(tpt)
        self.assertEqual((tpt.alt.deg, tpt.az.deg), (49.999999999999986, 94.99999999999999))

    def test_one_degree(self):
        sync_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
        stepper_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
        self.pm.add_point(sync_point, stepper_point)
        sync_point = SkyCoord(alt=60, az=95, unit='deg', frame='altaz')
        sp = pointing_model.test_altaz_transform(10.0, 90.0, 60., 95.0, 1.)
        stepper_point = SkyCoord(alt=sp['alt'], az=sp['az'], unit='deg', frame='altaz')
        self.pm.add_point(sync_point, stepper_point)
        sync_point = SkyCoord(alt=20, az=100, unit='deg', frame='altaz')
        sp = pointing_model.test_altaz_transform(10.0, 90.0, 20., 100.0, 1.0)
        stepper_point = SkyCoord(alt=sp['alt'], az=sp['az'], unit='deg', frame='altaz')
        self.pm.add_point(sync_point, stepper_point)
        point = SkyCoord(alt=50, az=95, unit='deg', frame='altaz')
        tpt = self.pm.transform_point(point)
        self.assertEqual((tpt.alt.deg, tpt.az.deg), (50.08108010292904, 94.4534133318961))
        tpt = self.pm.inverse_transform_point(tpt)
        self.assertEqual((tpt.alt.deg, tpt.az.deg), (49.99999999999997, 94.99999999999999))

    def test_clear(self):
        self.test_twop_stretch()
        self.pm.clear()
        self.test_one_degree()


if __name__ == '__main__':
    unittest.main()
