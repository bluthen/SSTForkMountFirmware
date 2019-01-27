import numpy
import math
import affine_fit

from astropy.coordinates import SkyCoord


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


def find_triangle(coord, sync_points, triangles):
    """
    Find a set of sync points that make up a triangle in which the coord is inside the triangle.
    :param coord: The coordinate you want to find a triangle that it is in.
    :type coord: astropy.coordinates.SkyCoord or xy project coordinates
    :param sync_points: A list of dicts of (from_point, real_projection, ...)
    :type sync_points: list[dict['from_point': astropy.coordinates.SkyCoord, 'from_projection': dict[x, y]]
    :param triangles: A list of sets of indexes of sync_points that make minimal triangles.
    :return: Tuple of 3 sync_point indexes representing the triangle.
    :rtype: tuple
    """
    if not hasattr(coord, 'alt') and (not isinstance(coord, dict) or ('x' not in coord and 'y' not in coord)):
        raise AssertionError('coord should be an alt-az coordinate or xy projection coordinate')
    if len(triangles) == 0:
        return None
    if hasattr(coord, 'alt'):
        pt = alt_az_projection(coord)
    else:
        pt = coord
    pt = [pt['x'], pt['y']]
    for triangle in triangles:
        tri = []
        for idx in triangle:
            tri.append([sync_points[idx]['from_projection']['x'], sync_points[idx]['from_projection']['y']])
        if tr_point_in_triangle(pt, tri[0], tri[1], tri[2]):
            return triangle
    # Outside any triangle sync.
    return None


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


def test_transform(oalt, oaz, alt, az, deg):
    theta = deg * math.pi / 180.0
    return {'alt': oalt + (alt - oalt) * math.cos(theta) + (az - oaz) * math.sin(theta),
            'az': oaz + (az - oaz) * math.cos(theta) - (alt - oalt) * math.sin(theta)}


class PointingModel:
    def __init__(self):
        """
        :Example:
            >>> import pointing_model
            >>> from astropy.coordinates import SkyCoord
            >>> pm = pointing_model.PointingModel()
            >>> # Unity test
            >>> sync_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
            >>> stepper_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
            >>> triangle = pm.add_point(sync_point, stepper_point)
            >>> sync_point = SkyCoord(alt=60, az=95, unit='deg', frame='altaz')
            >>> stepper_point = SkyCoord(alt=60, az=95, unit='deg', frame='altaz')
            >>> triangle = pm.add_point(sync_point, stepper_point)
            >>> sync_point = SkyCoord(alt=20, az=100, unit='deg', frame='altaz')
            >>> stepper_point = SkyCoord(alt=20, az=100, unit='deg', frame='altaz')
            >>> triangle = pm.add_point(sync_point, stepper_point)
            >>> point = SkyCoord(alt=50, az=95, unit='deg', frame='altaz')
            >>> tpt = pm.transform_point(point)
            >>> tpt.alt.deg, tpt.az.deg
            (50.0, 95.0)
            >>> # Unit two point
            >>> pm.clear()
            >>> sync_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
            >>> stepper_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
            >>> triangle = pm.add_point(sync_point, stepper_point)
            >>> sync_point = SkyCoord(alt=60, az=95, unit='deg', frame='altaz')
            >>> stepper_point = SkyCoord(alt=60, az=95, unit='deg', frame='altaz')
            >>> triangle = pm.add_point(sync_point, stepper_point)
            >>> point = SkyCoord(alt=50, az=95, unit='deg', frame='altaz')
            >>> tpt = pm.transform_point(point)
            >>> tpt.alt.deg, tpt.az.deg
            (50.0, 95.0)
            >>> # 2% Stretched
            >>> pm.clear()
            >>> sync_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
            >>> stepper_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
            >>> triangle = pm.add_point(sync_point, stepper_point)
            >>> sync_point = SkyCoord(alt=60, az=95, unit='deg', frame='altaz')
            >>> stepper_point = SkyCoord(alt=10+(60-10)*1.02, az=90+(95-90)*1.02, unit='deg', frame='altaz')
            >>> triangle = pm.add_point(sync_point, stepper_point)
            >>> sync_point = SkyCoord(alt=20, az=100, unit='deg', frame='altaz')
            >>> stepper_point = SkyCoord(alt=10+(20-10)*1.02, az=90+(100-90)*1.02, unit='deg', frame='altaz')
            >>> triangle = pm.add_point(sync_point, stepper_point)
            >>> point = SkyCoord(alt=50, az=95, unit='deg', frame='altaz')
            >>> tpt = pm.transform_point(point)
            >>> tpt.alt.deg, tpt.az.deg
            (50.80120905913654, 95.09687722671514)

            >>> # 1 degree
            >>> pm.clear()
            >>> sync_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
            >>> stepper_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
            >>> triangle = pm.add_point(sync_point, stepper_point)
            >>> sync_point = SkyCoord(alt=60, az=95, unit='deg', frame='altaz')
            >>> sp = pointing_model.test_transform(10.0, 90.0, 60., 95.0, 1.)
            >>> stepper_point = SkyCoord(alt=sp['alt'], az=sp['az'], unit='deg', frame='altaz')
            >>> triangle = pm.add_point(sync_point, stepper_point)
            >>> sync_point = SkyCoord(alt=20, az=100, unit='deg', frame='altaz')
            >>> sp = pointing_model.test_transform(10.0, 90.0, 20., 100.0, 1.0)
            >>> stepper_point = SkyCoord(alt=sp['alt'], az=sp['az'], unit='deg', frame='altaz')
            >>> triangle = pm.add_point(sync_point, stepper_point)
            >>> point = SkyCoord(alt=50, az=95, unit='deg', frame='altaz')
            >>> tpt = pm.transform_point(point)
            >>> tpt.alt.deg, tpt.az.deg
            (50.08108010292904, 94.4534133318961)
        """
        self.__sync_points = []
        # Distance matrix for sync_points
        # https://en.wikipedia.org/wiki/Distance_matrix
        #: distance matrix created with sync_points
        self.__distance_matrix = []
        self.__triangles = []
        self.debug = False

    def add_point(self, from_point, to_point):
        """
        Updates parameters so it will use point for transforming future points.
        :param from_point: AltAz from point.
        :type from_point: astropy.coordinates.SkyCoord in AltAz frame
        :param to_point: AltAz to point
        :type to_point: astropy.coordinates.SkyCoord in AltAz frame
        :return: triangle mainly used for debugging.
        :Example:
            >>> import pointing_model
            >>> from astropy.coordinates import SkyCoord
            >>> pm = pointing_model.PointingModel()
            >>> pm.debug = True
            >>> sync_point = SkyCoord(alt=10, az=90, unit='deg', frame='altaz')
            >>> stepper_point = SkyCoord(alt=10.1, az=90.1, unit='deg', frame='altaz')
            >>> triangle = pm.add_point(sync_point, stepper_point)
            >>> sync_point = SkyCoord(alt=60, az=95, unit='deg', frame='altaz')
            >>> stepper_point = SkyCoord(alt=60.1, az=95.1, unit='deg', frame='altaz')
            >>> triangles = pm.add_point(sync_point, stepper_point)
            >>> sync_point = SkyCoord(alt=20, az=100, unit='deg', frame='altaz')
            >>> stepper_point = SkyCoord(alt=20.1, az=100.1, unit='deg', frame='altaz')
            >>> triangles = pm.add_point(sync_point, stepper_point)
            >>> triangles
            [{0, 1, 2}]
            >>> sync_point = SkyCoord(alt=12, az=80, unit='deg', frame='altaz')
            >>> stepper_point = SkyCoord(alt=12.1, az=80.1, unit='deg', frame='altaz')
            >>> triangles = pm.add_point(sync_point, stepper_point)
            >>> triangles
            [{0, 2, 3}, {0, 1, 2}]
        """
        if not hasattr(from_point, 'alt'):
            raise ValueError('coord should be an alt-az coordinate')
        # TODO: Check if coord already in sync_points first and don't add if so.

        # Add on to distance matrix
        row = []
        for i in range(len(self.__sync_points)):
            sep = from_point.separation(self.__sync_points[i]['from_point']).deg
            self.__distance_matrix[i].append(sep)
            row.append(sep)
        if 0.0 in row:
            raise ValueError('coord already in sync_points')
        row.append(0.0)
        self.__sync_points.append(
            {'from_point': from_point, 'from_projection': alt_az_projection(from_point), 'to_point': to_point,
             'to_projection': alt_az_projection(to_point)})
        self.__distance_matrix.append(row)

        # Create traingles again
        # For each point find two other points that are near by.
        if len(self.__sync_points) > 2:
            new_triangles = []
            for i in range(len(self.__sync_points)):
                min_v1 = 999999999.0
                min_idx1 = -1
                min_idx2 = -1
                for j in range(len(self.__sync_points)):
                    if i == j:
                        continue
                    if self.__distance_matrix[i][j] < min_v1:
                        min_idx2 = min_idx1
                        min_v1 = self.__distance_matrix[i][j]
                        min_idx1 = j
                # check if triangle is already in there or not.
                triangle = {i, min_idx1, min_idx2}
                if triangle not in new_triangles and -1 not in triangle:
                    new_triangles.append(triangle)
            self.__triangles = new_triangles
        else:
            self.__triangles = []
        return self.__triangles

    def __get_two_closest_sync_points_idx(self, coord):
        one = None
        two = None
        for i in range(len(self.__sync_points)):
            sep = coord.separation(self.__sync_points[i]['from_point']).deg
            if one is None:
                one = [i, sep]
            elif one[1] > sep:
                two = one
                one = [i, sep]
            elif two is None:
                two = [i, sep]
        return [one[0], two[0]]

    def transform_point(self, point):
        """
        Transform point using the model created by adding points.
        :param point: AltAz point to transform.
        :return:
        """
        proj_coord = alt_az_projection(point)
        triangle = None
        if len(self.__sync_points) >= 3:
            triangle = find_triangle(proj_coord, self.__sync_points, self.__triangles)
        # Find trangle it is in
        if triangle:
            # TODO: Or should affine be done in sync?
            # Calculate affine function from triangle
            # TODO: Can this fail?
            from_npa = get_projection_coords(triangle, self.__sync_points, 'from_projection')
            to_npa = get_projection_coords(triangle, self.__sync_points, 'to_projection')
            transform = affine_fit.affine_fit(from_npa, to_npa)
            transformed_projection = transform.Transform([proj_coord['x'], proj_coord['y']])
            to_point = inverse_altaz_projection({'x': transformed_projection[0], 'y': transformed_projection[1]})
            return to_point
        else:
            if len(self.__sync_points) >= 2:
                # Get nearest two_points
                near_two = self.__get_two_closest_sync_points_idx(point)
                # Just use scale and offset.
                from_npa = numpy.array(get_projection_coords(near_two, self.__sync_points, 'from_projection'))
                to_npa = numpy.array(get_projection_coords(near_two, self.__sync_points, 'to_projection'))

                A = numpy.array([[from_npa[0][0], 0, 1.0, 0],
                                 [from_npa[1][0], 0, 1, 0],
                                 [0, from_npa[0][1], 0, 1],
                                 [0, from_npa[1][1], 0, 1.0]])
                b = numpy.array([[to_npa[0][0]],
                                 [to_npa[1][0]],
                                 [to_npa[0][1]],
                                 [to_npa[1][1]]])
                x = numpy.linalg.solve(A, b)
                # print(proj_coord, x)
                transformed_projection = [proj_coord['x']*x[0][0]+x[2][0], proj_coord['y']*x[1][0]+x[3][0]]
                to_point = inverse_altaz_projection({'x': transformed_projection[0], 'y': transformed_projection[1]})
                return to_point
            elif len(self.__sync_points) == 1:
                # TODO: Or two point failed get nearest point
                # Just normal stepper slew using point as sync_point
                return point
            else:
                raise ValueError('No sync points.')

    def clear(self):
        """
        Reset all points in pointing model.
        """
        self.__init__()

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
