import numpy
import math
import affine_fit
import settings
import json
import scipy
import scipy.optimize

from astropy.coordinates import SkyCoord
import astropy.units as u

pointing_logger = settings.get_logger('pointing')

SEPERATION_THRESHOLD = 0.5


def inverse_altaz_projection(xy_coord):
    """
    Convert x-y azimuthal project coord back to altaz SkyCoord
    :param xy_coord: projected x, y values to go back to altaz coordinates.
    :type xy_coord: dict with keys x, y
    :return: Coordinates projected back to altaz frame.
    :rtype: astropy.coordinates.SkyCoord
    :Example:
        >>> import pointing_model
        >>> import numpy
        >>> xy = {'x': 0.8888888888888888, 'y': 0.0}
        >>> b = pointing_model.inverse_altaz_projection(xy)
        >>> b.alt.deg, b.az.deg
        (10.000000000000004, 90.0)
        >>> xy = {'x': numpy.array([0.88888889, 0.3320649 , 0.76596159]), 'y': numpy.array([0., -0.02905191, -0.13505969])}
        >>> b = pointing_model.inverse_altaz_projection(xy)
        >>> b.alt.deg, b.az.deg
        (array([ 9.9999999 , 59.99999998, 19.99999968]), array([90.        , 94.99999926, 99.99999967]))
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
    return SkyCoord(alt=alt, az=az, unit='deg', frame='altaz')


def alt_az_projection(altaz_coord):
    """
    Convert alt-az coordinate to x, y coordinates through azimuthal projection
    :param altaz_coord: A skyCoord with a arrow of coords inside or just one in altaz frame.
    :type altaz_coord: astropy.coordiantes.SkyCord
    :return: projected x, y coordinates, array if given array, otherwise single values.
    :rtype: dict with keys x, y
    :Example:
        >>> import pointing_model
        >>> from astropy.coordinates import SkyCoord
        >>> a=SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
        >>> xy = pointing_model.alt_az_projection(a)
        >>> xy
        {'x': 0.8888888888888888, 'y': 0.0}
        >>> a=SkyCoord(alt=[10, 60, 20], az=[90, 95, 100], unit='deg', frame='altaz')
        >>> xy = pointing_model.alt_az_projection(a)
        >>> xy
        {'x': array([0.88888889, 0.3320649 , 0.76596159]), 'y': array([ 0.        , -0.02905191, -0.13505969])}
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
    :param sync_points:
    :param sync_point_key:
    :return:
    :Example:
        >>> import pointing_model
        >>> sp = [{'t': {'x': 4.3, 'y': 1.2}}, {'t': {'x': 4.3, 'y': 1.2}}, {'t': {'x': 4.5, 'y': 1.3}}]
        >>> pointing_model.get_projection_coords([1, 2], sp, 't')
        [[4.3, 1.2], [4.5, 1.3]]
    """
    ret = []
    for idx in indexes:
        ret.append([sync_points[idx][sync_point_key]['x'], sync_points[idx][sync_point_key]['y']])
    return ret


def test_altaz_transform(oalt, oaz, alt, az, deg):
    theta = deg * math.pi / 180.0
    return {'alt': oalt + (alt - oalt) * math.cos(theta) + (az - oaz) * math.sin(theta),
            'az': oaz + (az - oaz) * math.cos(theta) - (alt - oalt) * math.sin(theta)}


def test_hadec_transform(offset_dec, offset_ha, dec, ha, deg):
    theta = deg * math.pi / 180.0
    return {'ha': offset_ha + (ha - offset_ha) * math.cos(theta) + (dec - offset_dec) * math.sin(theta),
            'dec': offset_dec + (dec - offset_dec) * math.cos(theta) - (ha - offset_ha) * math.sin(theta)}


def log_p2dict(point):
    if hasattr(point, 'alt'):
        return {'alt': point.alt.deg, 'az': point.az.deg}
    elif hasattr(point, 'dec'):
        return {'ra': point.ra.deg, 'dec': point.dec.deg}
    else:
        return {}


def buie_model(xdata, r, dr, dd, dt, i, c, gamma, nu, e, phi):
    """

    :param xdata: [ra_array, dec_array]
    :param r: ra scale error
    :param dr: dec scale error
    :param dd: zeropoint offset dec
    :param dt: zeropoint offset ra
    :param i: polar axis non-orthogonality value
    :param c: mis-alignment of optical and mechanical axes
    :param gamma: angular separation of true and instrument pole
    :param nu: angle between true meridian and line of true and instrumental poles
    :param e: tube flexure
    :param phi: latitude
    :return:
    """
    xdataT = xdata.T
    tau = xdataT[0] * math.pi / 180.0
    delta = xdataT[1] * math.pi / 180.0

    a1 = gamma * numpy.cos(nu)
    a2 = gamma * numpy.sin(nu)
    x = numpy.cos(tau)
    y = numpy.sin(tau)
    x_hat = numpy.cos(delta)
    T = numpy.tan(delta)
    S = 1 / x_hat
    z = numpy.sin(phi) * x_hat - numpy.cos(phi) * numpy.sin(delta) * x

    d = delta - (dd - a1 * x - a2 * y - e * z + dr * delta)
    t = tau - (dt + T * (a2 * x - a1 * y - i) + S * (c + e * y * numpy.cos(phi)) + r * tau)

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
    def __init__(self, log=False, name=''):
        """
        :param log:
        :param name:
        """
        self.__from_points = None
        self.__to_points = []
        self.__model = 'buie'
        self.__buie_vals = None

    def set_model(self, model):
        pass

    def add_point(self, from_point, to_point):
        replace_idx = None
        if self.__from_points is not None:
            replace_idxex = numpy.where(self.__from_points.separation(from_point).deg < SEPERATION_THRESHOLD)[0]
            if len(replace_idxex) > 0:
                replace_idx = replace_idxex[0]
        if replace_idx is not None:
            fra = self.__from_points.ra.deg
            fdec = self.__from_points.dec.deg
            fra[replace_idx] = from_point.ra.deg
            fdec[replace_idx] = from_point.dec.deg
            self.__to_points[replace_idx] = [to_point.ra.deg, to_point.dec.deg]
        else:
            self.__to_points.append([to_point.ra.deg, to_point.dec.deg])
            if self.__from_points is not None:
                fra = numpy.append(self.__from_points.ra.deg, from_point.ra.deg)
                fdec = numpy.append(self.__from_points.dec.deg, from_point.dec.deg)
            else:
                fra = [from_point.ra.deg]
                fdec = [from_point.dec.deg]
        self.__from_points = SkyCoord(ra=fra * u.deg, dec=fdec * u.deg, frame='icrs')

        if self.__model == 'buie':
            p0 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            if len(self.__to_points) < len(p0):
                p0 = p0[0:len(self.__to_points)]
            xdata = numpy.array([self.__from_points.ra.deg, self.__from_points.dec.deg]).T
            ydata = numpy.array(self.__to_points)
            self.__buie_vals = scipy.optimize.leastsq(buie_model_error, p0, args=(xdata, ydata))[0]

    def transform_point(self, point):
        if self.__model == 'buie' and self.__buie_vals is not None:
            p0 = numpy.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
            p0 = numpy.concatenate([self.__buie_vals, p0[len(self.__buie_vals):]])
            new_point = buie_model(numpy.array([[point.ra.deg, point.dec.deg]]), *p0)
            return SkyCoord(ra=new_point[0][0] * u.deg, dec=new_point[0][1] * u.deg, frame='icrs')
        else:
            return point

    def inverse_transform_point(self, point):
        if self.__model == 'buie' and self.__buie_vals is not None:
            def our_func(coord):
                new_point = self.transform_point(SkyCoord(ra=coord[0] * u.deg, dec=coord[1] * u.deg, frame='icrs'))
                return (new_point.ra.deg-point.ra.deg)**2.0+(new_point.dec.deg-point.dec.deg)**2.0
            inv_point = scipy.optimize.fmin(our_func, [point.ra.deg, point.dec.deg])
            return SkyCoord(ra=inv_point[0]*u.deg, dec=inv_point[1]*u.deg, frame='icrs')
        else:
            return point

    def frame(self):
        return 'hadec'

    def clear(self):
        self.__from_points = None
        self.__to_points = []
        self.__buie_vals = None

    def get_from_points(self):
        return numpy.array(self.__from_points)

    def size(self):
        return len(self.__to_points)


class PointingModelAffine:
    def __init__(self, log=False, name='', isinverse=False):
        """
        :Example:
        """
        self.__log = log
        self.__name = name

        self.__sync_points = []
        self.__from_points = None
        self.__model = 'affine_all'
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
        ret = []
        for point in self.__sync_points:
            ret.append(point['from_point'])
        return ret

    def set_model(self, model):
        if model in ['single', '1point', 'affine_all']:
            if self.__log:
                pointing_logger.debug(json.dumps({'func': 'set_model', 'model': model}))
            self.__model = model

    def add_point(self, from_point, to_point):
        """
        Updates parameters so it will use point for transforming future points.
        :param from_point: AltAz from point.
        :type from_point: astropy.coordinates.SkyCoord in AltAz frame
        :param to_point: AltAz to point
        :type to_point: astropy.coordinates.SkyCoord in AltAz frame
        :return: triangle mainly used for debugging.
        """
        if not hasattr(from_point, 'alt'):
            raise ValueError('coord should be an alt-az coordinate')

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
        self.__from_points = SkyCoord(alt=numpy.array(alt) * u.deg, az=numpy.array(az) * u.deg, frame='altaz')

        if self.__model == 'affine_all':
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
        to_point = SkyCoord(alt=new_alt, az=new_az, unit='deg', frame='altaz')
        if self.__log:
            pointing_logger.debug(json.dumps(
                {'func': 'transform_point', 'model': '1point', 'from_point': log_p2dict(point),
                 'to_point': log_p2dict(to_point)}))
        return to_point

    def transform_point(self, point):
        """
        Transform point using the model created by adding points.
        :param point: AltAz point to transform.
        :return:
        """
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
        # A possible other alternative is to use fmin with transform_point
        return self.__inverseModel.transform_point(point)

    def frame(self):
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
        return len(self.__sync_points)


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
    :type pt: array [float, float]
    :param t1: first point of triangle
    :type t1: array [float, float]
    :param t2: second point of triangle
    :type t2: array [float, float]
    :param t3: third point of triangle
    :type t3: array [float, float]
    :return: true if point in triangle
    :rtype: bool
    :Example:
        >>> import pointing_model
        >>> t1=pointing_model.tr_point_in_triangle([95., 50.], [90., 10.], [95., 60.0], [100, 20.0])
        >>> t2=pointing_model.tr_point_in_triangle([90., 50.], [90., 10.], [95., 60.0], [100, 20.0])
        >>> t3=pointing_model.tr_point_in_triangle([90., 30.], [45., 20.], [135., 20.0], [175, 80.0])
        >>> t1, t2, t3
        (True, False, True)
    """
    d1 = tr_sign(pt, t1, t2)
    d2 = tr_sign(pt, t2, t3)
    d3 = tr_sign(pt, t3, t1)

    h_neg = d1 < 0 or d2 < 0 or d3 < 0
    h_pos = d1 > 0 or d2 > 0 or d3 > 0

    return not (h_neg and h_pos)
