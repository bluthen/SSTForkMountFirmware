import copy

import numpy
import math
import affine_fit
import settings
import json
import sys
import scipy
import scipy.optimize

from astropy.coordinates import AltAz, SkyCoord
from skyconv_hadec import HADec
import astropy.units as u

pointing_logger = settings.get_logger('pointing')

SEPERATION_THRESHOLD = 0.5


def inverse_altaz_projection(xy_coord):
    """
    Convert x-y azimuthal project coord back to AltAz
    :param xy_coord: projected x, y values to go back to altaz coordinates.
    :type xy_coord: Dict[str, float]
    :return: Coordinates projected back to altaz frame.
    :rtype: SkyCoord
    """
    x = numpy.array(xy_coord['x'])
    y = numpy.array(xy_coord['y'])
    caz = numpy.arctan2(y, x) * 180.0 / math.pi
    az = 90 - caz
    r = x / numpy.cos(caz * math.pi / 180.0)
    # TODO: When r is < 0, is this the right move.
    if r.size > 1:
        r[r < 0] = 0
    elif r < 0.0:
        r = 0.0
    alt = 90.0 * (1.0 - r)
    return SkyCoord(AltAz(alt=alt*u.deg, az=az*u.deg))


def alt_az_projection(altaz_coord):
    """
    Convert AltAz coordinate to x, y coordinates through azimuthal projection
    :param altaz_coord: A SkyCoord in AltAz frame with a array of coords inside or just one.
    :type altaz_coord: SkyCoord
    :return: projected x, y coordinates, array if given array, otherwise single values.
    :rtype: Union[Dict[str, float], Dict[str, List[float]]]
    """
    alt = numpy.array(altaz_coord.alt.deg)
    az = numpy.array(altaz_coord.az.deg)
    caz = -az + 90.0
    r = 1.0 - alt / 90.0
    x = r * numpy.cos(caz * math.pi / 180.0)
    y = r * numpy.sin(caz * math.pi / 180.0)
    return {'x': x, 'y': y}


def get_projection_coords(indexes, sync_points, sync_point_key):
    """

    :param indexes:
    :type indexes: List[int]
    :param sync_points:
    :type sync_points: Dict[str, Dict[str, float]]
    :param sync_point_key:
    :type sync_point_key: str
    :return:
    :rtype: List[List[float]]
    """
    ret = []
    for idx in indexes:
        ret.append([sync_points[idx][sync_point_key]['x'], sync_points[idx][sync_point_key]['y']])
    return ret


def test_altaz_transform(oalt, oaz, alt, az, deg):
    """
    Calculates alt az values with offset and rotation
    :param oalt: Alt offset
    :param oaz: Az offset
    :param alt: Given Alt
    :param az: Given Az
    :param deg: Rotation value
    :return: Dictionary with alt and az as keys for new offset rotated coordinate
    :rtype: Dict[str, float]
    """
    theta = deg * math.pi / 180.0
    return {'alt': oalt + (alt - oalt) * math.cos(theta) + (az - oaz) * math.sin(theta),
            'az': oaz + (az - oaz) * math.cos(theta) - (alt - oalt) * math.sin(theta)}


def test_hadec_transform(offset_dec, offset_ha, dec, ha, deg):
    """
    Calculate ha dec values with a offset and rotation.
    :param offset_dec: Dec Offset
    :type offset_dec: float
    :param offset_ha: HA offset
    :type offset_ha: float
    :param dec: given dec
    :type dec: float
    :param ha: given HA
    :type ha: float
    :param deg: rotation value
    :type deg: float
    :return: dictionary with 'ha', 'dec' as keys for new offseted rotated coordinate
    :rtype: Dict[str, float]
    """
    theta = deg * math.pi / 180.0
    return {'ha': offset_ha + (ha - offset_ha) * math.cos(theta) + (dec - offset_dec) * math.sin(theta),
            'dec': offset_dec + (dec - offset_dec) * math.cos(theta) - (ha - offset_ha) * math.sin(theta)}


def log_p2dict(point):
    """
    Takes degrees out of coordinate and makes a dictionary for easier logging.
    :param point: An AltAz or Dec Coordinate
    :type point: Union[SkyCoord, HADec]
    :return: dictionary with key values being coordinate axis
    :rtype: Dict[str, float]
    """
    if hasattr(point, 'alt'):
        return {'alt': point.alt.deg, 'az': point.az.deg}
    elif hasattr(point, 'dec'):
        return {'ra': point.ra.deg, 'dec': point.dec.deg}
    else:
        return {}


def buie_model(xdata, r, dr, dd, dt, i, c, gamma, nu, e, phi):
    """
    Tried to apply Buie model. From the paper "General Anlytical Telescope Point Model" By Marc W. Buie Feb. 16, 2003
    https://sites.astro.caltech.edu/~srk/TP/Literature/Lowell.pdf
    :param xdata: [ra_array, dec_array]
    :param r: RA - scale error
    :param dr: Dec - scale error
    :param dd: Dec - zeropoint offset
    :param dt: RA - zeropoint offset
    :param i: Dec - polar axis non-orthogonality value
    :param c: RA - mis-alignment of optical and mechanical axes
    :param gamma: Dec - angular separation of true and instrument pole
    :param nu: Dec - angle between true meridian and line of true and instrumental poles
    :param e: RA/Dec - tube flexure
    :param phi: latitude
    :return:
    """
    xdata_t = xdata.T
    tau = xdata_t[0] * math.pi / 180.0
    delta = xdata_t[1] * math.pi / 180.0

    a1 = gamma * numpy.cos(nu)
    a2 = gamma * numpy.sin(nu)
    x = numpy.cos(tau)
    y = numpy.sin(tau)
    x_hat = numpy.cos(delta)
    delta_tan = numpy.tan(delta)
    s = 1 / x_hat
    z = numpy.sin(phi) * x_hat - numpy.cos(phi) * numpy.sin(delta) * x

    # Paper notes:
    # Equation d = delta - (a0 - a1*x - a2*y - a3*z)   with:
    # a0 = dd
    # a3 = e
    # We added dec scale error: dr*delta
    d = delta - (dd - a1 * x - a2 * y - e * z + dr * delta)

    # Paper notes:
    # Equation t = tau - (b0 + b1*S - b2*T + H + b3*q + b4*tau)
    # b0 = dt
    # delta_tan = tan(delta)
    # b1 = c
    # b2 = i
    # b3 = l # Not used, so we set to 0 and remove
    # b4 = r
    # S = sec(delta)
    # H = (-a1*y+a2*x)*T+a3*cos(phi)*S*y = (-a1*sin(tau)+a2*cos(tau))*tan(delta)+a3*cos(phi)*sec(delta)*sin(tau)
    #   =
    # t = tau - (dt + c*sec(delta) - c * tan(delta) + (-a1*y+a2*x)*tan(delta)+a3*cos(phi)*sec(delta)*sin(tau) )
    # We add ra scale error: r*tau
    t = tau - (dt + delta_tan * (a2 * x - a1 * y - i) + s * (c + e * y * numpy.cos(phi)) + r * tau)

    return numpy.array([(180.0 / math.pi) * t, (180.0 / math.pi) * d]).T


def buie_model_error(p0, x, y):
    p0a = numpy.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    p0a = numpy.concatenate([p0, p0a[len(p0):]])
    ny = buie_model(x, *p0a)
    err = numpy.power(ny.T[0] - y.T[0], 2) + numpy.power(ny.T[1] - y.T[1], 2)
    return err


# scipy.curve_fit(buie_model, x_data, y_data, p0=[altitude, 1, 1, 1, 1, 1, 1, 1, 1, 1])
"""
import pointing_model
import numpy
import scipy
import scipy.optimize
xdata = numpy.array([
[30, 21],
[50, 41],
[44, 51],
[33, 61],
[130, 71],
[150, 81],
[92, 11],
[66, 14],
[98.2, 15],
[21, -50],
[89, -22],
[190, 44],
[200, -70],
[21, 1],
[44, 5],
])
ydata = numpy.array([xdata.T[0]*1.02, xdata.T[1]*0.98]).T
p0=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
scipy.optimize.leastsq(pointing_model.buie_model_error, p0[:], args=(xdata, xdata))
"""


# scipy.optimize.curve_fit(pointing_model.buie_model ,
# numpy.array([[30.0, 40.0, 24, 26, 70, 82, 32, 44, 65, 70, 12, 170], [45.0, 50.0, -32, -50, 32, 33, 66, 89, 11, 23, 66, -12]]) , numpy.array([[30.0, 40.0, 24, 26, 70, 82, 32, 44, 65, 70, 12, 170], [45.0, 50.0, -32, -50, 32, 33, 66, 89, 11, 23, 66, -12]]) , p0=[39.9, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])


class PointingModelBuie:
    def __init__(self, log=False, name='', max_points=-1):
        """
        :param log:
        :param name:
        """
        self.__from_points = None
        self.__to_points = []
        self.__buie_vals = None
        self.__max_points = max_points

    def add_point(self, from_point, to_point):
        """
        Add a point to the model.
        :param from_point: What mount thinks it is at
        :type from_point: HADec
        :param to_point: What mount is actually at.
        :type to_point: HADec
        :return: None
        :rtype: None
        """
        if self.__max_points != -1 and len(self.__to_points) >= self.__max_points:
            self.__to_points = self.__to_points[1:]
            self.__from_points = self.__from_points[1:]

        from_point = HADec(ha=from_point.ha, dec=from_point.dec)
        to_point = HADec(ha=to_point.ha, dec=to_point.dec)
        replace_idx = None
        if self.__from_points is not None:
            replace_idxex = numpy.where(self.__from_points.separation(from_point).deg < SEPERATION_THRESHOLD)[0]
            if len(replace_idxex) > 0:
                replace_idx = replace_idxex[0]
        if replace_idx is not None:
            fra = self.__from_points.ha.deg
            fdec = self.__from_points.dec.deg
            fra[replace_idx] = from_point.ha.deg
            fdec[replace_idx] = from_point.dec.deg
            self.__to_points[replace_idx] = [to_point.ha.deg, to_point.dec.deg]
        else:
            self.__to_points.append([to_point.ha.deg, to_point.dec.deg])
            if self.__from_points is not None:
                fra = numpy.append(self.__from_points.ha.deg, from_point.ha.deg)
                fdec = numpy.append(self.__from_points.dec.deg, from_point.dec.deg)
            else:
                fra = [from_point.ha.deg]
                fdec = [from_point.dec.deg]
        self.__from_points = HADec(ha=fra * u.deg, dec=fdec * u.deg)

        # Act just like single if number of points is only 1
        if len(self.__from_points) > 1:
            p0 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            if len(self.__to_points) < len(p0):
                p0 = p0[0:len(self.__to_points)]
            xdata = numpy.array([self.__from_points.ha.deg, self.__from_points.dec.deg]).T
            ydata = numpy.array(self.__to_points)
            # Default maxfev=800 fails in some unit tests
            result = scipy.optimize.leastsq(buie_model_error, numpy.array(p0), args=(xdata, ydata), full_output=True,
                                            maxfev=1600)
            result_ier = result[4]
            result_msg = result[3]
            # print(result[2]['fvec'], len(self.__from_points))
            if result_ier in [1, 2, 3, 4]:
                self.__buie_vals = result[0]
            else:
                print('WARNING: model failed, using single point model until successful. ' +
                      'scipy.optimize.leastsq: ier={result_ier:d}, mesg={result_msg:s}'.format(result_ier=result_ier,
                                                                                               result_msg=result_msg),
                      file=sys.stderr)
                # Had problem with least squares, use single point model until successful
                self.__buie_vals = None

    def transform_point(self, point):
        """
        Given desired point give us what we to tell the mount to go to.
        :param point: Desired Point
        :type point: HADec
        :return: Point the mount should go to.
        :rtype: HADec
        """
        if self.__buie_vals is not None:
            # print('buie_vals', self.__buie_vals)
            p0 = numpy.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
            p0 = numpy.concatenate([self.__buie_vals, p0[len(self.__buie_vals):]])
            new_point = buie_model(numpy.array([[point.ha.deg, point.dec.deg]]), *p0)
            return HADec(ha=new_point[0][0] * u.deg, dec=new_point[0][1] * u.deg)
        else:
            return point

    def inverse_transform_point(self, point):
        """
        Given what the mount is pointed give us what it should actually be at.
        :param point: Mount point
        :type point: HADec
        :return: What model thinks it is actually pointed at.
        :rtype: HADec
        """
        if self.__buie_vals is not None:
            def our_func(coord):
                new_point = self.transform_point(HADec(ha=coord[0] * u.deg, dec=coord[1] * u.deg))
                return (new_point.ha.deg - point.ha.deg) ** 2.0 + (new_point.dec.deg - point.dec.deg) ** 2.0

            results = scipy.optimize.fmin(our_func, [point.ha.deg, point.dec.deg], disp=False, full_output=True,
                                          maxfun=1600)
            inv_point = results[0]
            warnflag = results[4]
            if warnflag in [1, 2]:
                # TODO: Not sure if this will change until model has change, maybe can set/check model update flag
                print('WARNING: model failed, using single point model until successful. ', file=sys.stderr)
                return point
            else:
                return HADec(ha=inv_point[0] * u.deg, dec=inv_point[1] * u.deg)
        else:
            return point

    def frame(self):
        """
        Gives string of frame this model deals with.
        :return: 'hadec'
        :rtype: str
        """
        return 'hadec'

    def clear(self):
        """
        Resets the model removing all points and model values.
        :return: None
        :rtype: None
        """
        self.__from_points = None
        self.__to_points = []
        self.__buie_vals = None

    def get_from_points(self):
        """
        Gives you the from points in the model.
        :return:
        """
        return numpy.array(self.__from_points)

    def size(self):
        """
        Gives how many points are in the model
        :return: points in model
        :rtype: int
        """
        return len(self.__to_points)

    def __str__(self):
        if self.__buie_vals is None:
            return 'PointingModelBuie: no points'
        return f""""PointingModelBuie:
r={self.__buie_vals[0]:.2f} -- RA - scale error 
dr={self.__buie_vals[1]:.2f} -- Dec - scale error
dd={self.__buie_vals[2]:.2f} -- Dec - zero point offset
dt={self.__buie_vals[3]:.2f} -- RA - zero point offset
i={self.__buie_vals[4]:.2f} -- Dec - polar axis non-orthogonality value
c={self.__buie_vals[5]:.2f} -- RA - misalignment of mechanical axes
gamma={self.__buie_vals[6]:.2f} -- Dec - angular separation of true and instrument pole
nu={self.__buie_vals[7]:.2f} -- Dec - angle between true meridian line and true instrument pole
e={self.__buie_vals[8]:.2f} -- RA/Dec - tube flexure
phi={self.__buie_vals[9]:.2f} -- Latitude"""


class PointingModelAffine:
    def __init__(self, log=False, name='', isinverse=False, max_points=-1):
        """
        :Example:
        """
        self.__log = log
        self.__name = name

        self.__sync_points = []
        self.__from_points = None
        self.__max_points = max_points
        # Distance matrix for sync_points
        # https://en.wikipedia.org/wiki/Distance_matrix
        #: distance matrix created with sync_points
        self.__distance_matrix = []
        self.__affineAll = None
        self.__inverseModel = None
        if not isinverse:
            self.__inverseModel = PointingModelAffine(isinverse=True)
        self.debug = False

    def get_from_points(self):
        """
        Get model from points
        :return:
        """
        ret = []
        for point in self.__sync_points:
            ret.append(point['from_point'])
        return ret

    def add_point(self, from_point, to_point):
        """
        Updates parameters so it will use point for transforming future points.
        :param from_point: AltAz from point.
        :type from_point: Union[AltAz, SkyCoord]
        :param to_point: AltAz to point
        :type to_point: Union[AltAz, SkyCoord]
        """
        if from_point.name != 'altaz' or to_point.name != 'altaz':
            raise ValueError('coords should be an alt-az coordinate')

        if self.__max_points != -1 and len(self.__from_points) >= self.__max_points:
            self.__from_points = self.__max_points[1:]
            self.__sync_points = self.__sync_points[1:]


        from_point = SkyCoord(AltAz(alt=from_point.alt, az=from_point.az))
        to_point = SkyCoord(AltAz(alt=to_point.alt, az=to_point.az))

        # If it is close enough to a point already there, we will replace it.

        replace_idx = None
        if self.__from_points is not None:
            replace_idxex = numpy.where(self.__from_points.separation(from_point).deg < SEPERATION_THRESHOLD)[0]
            if len(replace_idxex) > 0:
                replace_idx = replace_idxex[0]
        if replace_idx is not None:
            self.__sync_points[replace_idx] = {'from_point': from_point,
                                               'from_projection': alt_az_projection(from_point), 'to_point': to_point,
                                               'to_projection': alt_az_projection(to_point)}
            alt = self.__from_points.alt.deg
            az = self.__from_points.az.deg
            alt[replace_idx] = from_point.alt.deg
            az[replace_idx] = from_point.az.deg
        else:
            self.__sync_points.append(
                {'from_point': from_point, 'from_projection': alt_az_projection(from_point), 'to_point': to_point,
                 'to_projection': alt_az_projection(to_point)})
            if self.__from_points is not None:
                alt = numpy.append(self.__from_points.alt.deg, from_point.alt.deg)
                az = numpy.append(self.__from_points.az.deg, from_point.az.deg)
            else:
                alt = [from_point.alt.deg]
                az = [from_point.az.deg]
        self.__from_points = SkyCoord(AltAz(alt=numpy.array(alt) * u.deg, az=numpy.array(az) * u.deg))

        if len(self.__sync_points) >= 3:
            if self.__log:
                pointing_logger.debug(json.dumps({'func': 'add_point', 'model': 'affine_all'}))
            from_npa = get_projection_coords(list(range(len(self.__sync_points))), self.__sync_points,
                                             'from_projection')
            to_npa = get_projection_coords(list(range(len(self.__sync_points))), self.__sync_points,
                                           'to_projection')
            self.__affineAll = affine_fit.affine_fit(from_npa, to_npa)
        if self.__inverseModel:
            self.__inverseModel.add_point(to_point, from_point)

    def __get_closest_sync_point_idx(self, coord):
        return self.__from_points.separation(coord).argmin()

    def __two_point(self, point, fp, tp):
        dalt = tp.alt.deg - fp.alt.deg
        daz = tp.az.deg - fp.az.deg
        new_alt = point.alt.deg + dalt
        if new_alt > 90.0:
            new_alt = 180.0 - new_alt
        elif new_alt < -90.0:
            new_alt = -180.0 - new_alt
        new_az = point.az.deg + daz
        if new_az > 360.0:
            new_az = new_az - 360.0
        elif new_az < 0:
            new_az = 360 + new_az
        to_point = SkyCoord(AltAz(alt=new_alt*u.deg, az=new_az*u.deg))
        if self.__log:
            pointing_logger.debug(json.dumps(
                {'func': 'transform_point', 'model': '1point', 'from_point': log_p2dict(point),
                 'to_point': log_p2dict(to_point)}))
        return to_point

    def transform_point(self, point):
        """
        Transform point using the model.
        :param point: AltAz desired point
        :type point: Union[AltAz, SkyCoord]
        :return: What the mount should goto to get to desired point, SkyCorod in altaz frame.
        :rtype: SkyCoord
        """
        point = SkyCoord(AltAz(alt=point.alt, az=point.az))
        proj_coord = alt_az_projection(point)
        if self.__affineAll:
            transformed_projection = self.__affineAll.Transform([proj_coord['x'], proj_coord['y']])
            to_point = inverse_altaz_projection(
                {'x': transformed_projection[0], 'y': transformed_projection[1]})
            if self.__log:
                pointing_logger.debug(json.dumps(
                    {'func': 'transform_point', 'model': 'affine_all', 'from_point': log_p2dict(point),
                     'to_point': log_p2dict(to_point)}))
            return to_point
        elif len(self.__sync_points) >= 2:
            # Get nearest two_points
            nearest_point = self.__get_closest_sync_point_idx(point)

            # for 1 point use simple offsets
            fp = self.__sync_points[nearest_point]['from_point']
            tp = self.__sync_points[nearest_point]['to_point']
            return self.__two_point(point, fp, tp)

        elif len(self.__sync_points) == 1:
            # Just normal stepper slew using point as sync_point
            if self.__log:
                pointing_logger.debug(json.dumps(
                    {'func': 'transform_point', 'model': 'nomodel', 'from_point': log_p2dict(point)}))
            return point
        else:
            raise ValueError('No sync points.')

    def inverse_transform_point(self, point):
        """
        Given what point mount is pointed to what is the model say real AltAz is.
        :param point: The mount point.
        :type point: Union[AltAz, SkyCoord]
        :return: The point the model thinks mount is pointed at. SkyCoord in AltAz frame.
        :rtype: SkyCoord
        """
        # A possible other alternative is to use fmin with transform_point
        point = SkyCoord(AltAz(alt=point.alt, az=point.az))
        return self.__inverseModel.transform_point(point)

    def frame(self):
        """
        Gives you string of the frame the model deals in.
        :return: 'altaz'
        :rtype: str
        """
        return 'altaz'

    def clear(self):
        """
        Reset all points in pointing model.
        """
        self.__sync_points = []
        self.__from_points = None
        self.__distance_matrix = []
        self.__affineAll = None
        if self.__inverseModel:
            self.__inverseModel.clear()

    def size(self):
        """
        :return: The number of point that make up the model.
        :rtype: int
        """
        return len(self.__sync_points)

    def __str__(self):
        return "Affine Model"


# Finding point in triangle
# xaedes answer
# https://stackoverflow.com/questions/2049582/how-to-determine-if-a-point-is-in-a-2d-triangle
# https://www.gamedev.net/forums/topic/295943-is-this-a-better-point-in-triangle-test-2d/
def tr_sign(p1, p2, p3):
    return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])


# Finding point in triangle
# xaedes answer
# https://stackoverflow.com/questions/2049582/how-to-determine-if-a-point-is-in-a-2d-triangle
# https://www.gamedev.net/forums/topic/295943-is-this-a-better-point-in-triangle-test-2d/
def tr_point_in_triangle(pt, t1, t2, t3):
    """
    Tests if point is in a triangle that is defined by three points.
    :param pt: Point checking
    :type pt: List[float, float]
    :param t1: first point of triangle
    :type t1: List[float, float]
    :param t2: second point of triangle
    :type t2: List[float, float]
    :param t3: third point of triangle
    :type t3: List[float, float]
    :return: true if point in triangle
    :rtype: bool
    """
    d1 = tr_sign(pt, t1, t2)
    d2 = tr_sign(pt, t2, t3)
    d3 = tr_sign(pt, t3, t1)

    h_neg = d1 < 0 or d2 < 0 or d3 < 0
    h_pos = d1 > 0 or d2 > 0 or d3 > 0

    return not (h_neg and h_pos)
