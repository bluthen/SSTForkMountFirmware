import unittest

import motion


class TestMotion(unittest.TestCase):
    def test_t_x_vmax(self):
        t_maxv, x_maxv = motion.t_x_vmax(3.0, 3.0, 20)
        self.assertAlmostEqual(x_maxv, 65.17, places=2)
        self.assertAlmostEqual(t_maxv, 5.67, places=2)
        t_maxv, x_maxv = motion.t_x_vmax(-3.0, 3.0, -20)
        self.assertAlmostEqual(x_maxv, -65.17, places=2)
        self.assertAlmostEqual(t_maxv, 7.67, places=2)

    def test_t_at_x(self):
        t = motion.t_at_x(3, 5, 20)
        self.assertAlmostEqual(t, 2.35, places=2)
        t = motion.t_at_x(-3, 5, -20)
        self.assertAlmostEqual(t, 5.68, places=2)

    def test_v_at_t(self):
        v = motion.v_at_t(3, 4, 20, 3.5)
        self.assertAlmostEqual(v, 14.5, places=2)
        v = motion.v_at_t(-3, 4, -20, 3.5)
        self.assertAlmostEqual(v, -6.5, places=2)
        v = motion.v_at_t(3, 4, 20, 20)
        self.assertAlmostEqual(v, 20, places=2)
        v = motion.v_at_t(-3, 4, -20, 20)
        self.assertAlmostEqual(v, -20, places=2)


if __name__ == '__main__':
    unittest.main()
