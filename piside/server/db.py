import re
import sqlite3
import threading

import astropy.coordinates
import astropy.time
import astropy.units as u
from astropy.coordinates import solar_system_ephemeris, SkyCoord
from astropy.time import Time as AstroTime

import settings
import skyconv

db_lock = threading.RLock()
conn = sqlite3.connect('ssteq.sqlite', check_same_thread=False)


def to_list_of_lists(tuple_of_tuples):
    b = [list(x) for x in tuple_of_tuples]
    return b


def to_list_of_dicts(tuple_of_tuples, keys):
    b = []
    for r in tuple_of_tuples:
        d = {}
        for i in range(len(r)):
            d[keys[i]] = r[i]
        b.append(d)
    return b


def search_planets(search):
    do_altaz = True
    planet_search = search.lower()
    bodies = solar_system_ephemeris.bodies
    planets = []
    for body in bodies:
        if body.find('earth') != -1:
            continue
        if body.find(planet_search) != -1:
            location = None
            if settings.runtime_settings['earth_location_set']:
                location = settings.runtime_settings['earth_location']
            coord = astropy.coordinates.get_body(body, AstroTime.now(),
                                                 location=location)
            ra = coord.ra.deg
            dec = coord.dec.deg
            coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
            if do_altaz:
                altaz = skyconv.icrs_to_altaz(coord, atmo_refraction=True)
                altaz = {'alt': altaz.alt.deg, 'az': altaz.az.deg}
            else:
                altaz = {'alt': None, 'az': None}
            planets.append(
                {
                    'type': 'planet', 'name': body.title(), 'ra': coord.icrs.ra.deg, 'dec': coord.icrs.dec.deg,
                    'alt': altaz['alt'],
                    'az': altaz['az']
                }
            )
    return planets


def search_dso(search):
    do_altaz = True
    dso_search = search
    if re.match(r'.*\d+$', search):
        dso_search = '%' + dso_search + '|%'
    else:
        dso_search = '%' + dso_search + '%'
    # catalogs = {'IC': ['IC'], 'NGC': ['NGC'], 'M': ['M', 'Messier'], 'Pal': ['Pal'], 'C': ['C', 'Caldwell'],
    # 'ESO': ['ESO'], 'UGC': ['UGC'], 'PGC': ['PGC'], 'Cnc': ['Cnc'], 'Tr': ['Tr'], 'Col': ['Col'], 'Mel': ['Mel'],
    # 'Harvard': ['Harvard'], 'PK': ['PK']}
    dso_columns = ["ra", "dec", "type", "const", "mag", "name", "r1", "r2", "search"]
    with db_lock:
        cur = conn.cursor()
        cur.execute(('SELECT %s from dso where search like ? limit 10' % ','.join(dso_columns)), (dso_search,))
        dso = cur.fetchall()
    dso = to_list_of_dicts(dso, dso_columns)
    print(dso)
    for ob in dso:
        # print(ob['ra'], ob['dec'], ob['r1'], ob['r2'])
        ob['ra'] = float(ob['ra']) * (360. / 24.)
        ob['dec'] = float(ob['dec'])
        if not ob['mag']:
            ob['mag'] = None
        else:
            ob['mag'] = float(ob['mag'])
        if not ob['r1']:
            ob['r1'] = None
        else:
            ob['r1'] = float(ob['r1'])
        if not ob['r2']:
            ob['r2'] = None
        else:
            ob['r2'] = float(ob['r2'])
        if do_altaz:
            coord = SkyCoord(ra=ob['ra'] * u.deg, dec=ob['dec'] * u.deg, frame='icrs')
            altaz = skyconv.icrs_to_altaz(coord, atmo_refraction=True)
            ob['alt'] = altaz.alt.deg
            ob['az'] = altaz.az.deg
        else:
            ob['alt'] = None
            ob['az'] = None
    return dso


def search_stars(search):
    do_altaz = True
    star_search = search
    if re.match(r'.*\d+$', search):
        star_search = '%' + star_search
    else:
        star_search = '%' + star_search + '%'
    # catalogs = {'IC': ['IC'], 'NGC': ['NGC'], 'M': ['M', 'Messier'], 'Pal': ['Pal'], 'C': ['C', 'Caldwell'],
    # 'ESO': ['ESO'], 'UGC': ['UGC'], 'PGC': ['PGC'], 'Cnc': ['Cnc'], 'Tr': ['Tr'], 'Col': ['Col'], 'Mel': ['Mel'],
    # 'Harvard': ['Harvard'], 'PK': ['PK']}
    stars_columns = ["ra", "dec", "bf", "proper", "mag", "con"]
    with db_lock:
        cur = conn.cursor()
        cur.execute('SELECT \'star\',%s from stars where bf like ? or proper like ? limit 10' % ','.join(stars_columns),
                    (star_search, star_search))
        stars = cur.fetchall()
        cur.close()
    stars = to_list_of_dicts(stars, ['type'] + stars_columns)
    # Alt az
    for ob in stars:
        ob['ra'] = float(ob['ra']) * (360. / 24.)
        ob['dec'] = float(ob['dec'])
        if not ob['mag']:
            ob['mag'] = None
        else:
            ob['mag'] = float(ob['mag'])
        if do_altaz:
            coord = SkyCoord(ra=ob['ra'] * u.deg, dec=ob['dec'] * u.deg, frame='icrs')
            altaz = skyconv.icrs_to_altaz(coord, atmo_refraction=True)
            ob['alt'] = altaz.alt.deg
            ob['az'] = altaz.az.deg
        else:
            ob['alt'] = None
            ob['az'] = None
    return stars


def search_cities(search):
    columns = ["postalcode", "city", "state", "state_abbr", "latitude", "longitude", "elevation"]
    # If zipcode search
    if re.match(r'\d+$', search):
        search = search + '%'
        with db_lock:
            cur = conn.cursor()
            cur.execute(('SELECT %s from uscities where postalcode like ? limit 20' % ','.join(columns)), (search,))
            cities = cur.fetchall()
            cur.close()
    else:
        cstate = search.split(',')
        if len(cstate) == 1:
            # Just search city
            city = cstate[0]
            city = city.strip()
            search = city + '%'
            with db_lock:
                cur = conn.cursor()
                cur.execute(('SELECT %s from uscities where city like ? limit 20' % ','.join(columns)), (search,))
                cities = cur.fetchall()
                cur.close()
        else:
            city = cstate[0]
            state = cstate[1]

            city = city.strip()
            state = state.strip()
            # If using state abbreviation
            if len(state) == 2:
                abbr = state.upper()
                city = city + '%'
                with db_lock:
                    cur = conn.cursor()
                    cur.execute(
                        ('SELECT %s from uscities where city like ? and state_abbr = ? limit 20' % ','.join(columns)),
                        (city, abbr))
                    cities = cur.fetchall()
                    cur.close()
            else:
                # State must be full name
                city = city + '%'
                state = state + '%'
                with db_lock:
                    cur = conn.cursor()
                    cur.execute(
                        ('SELECT %s from uscities where city like ? and state like ? limit 20' % ','.join(columns)),
                        (city, state))
                    cities = cur.fetchall()
                    cur.close()
    cities = to_list_of_dicts(cities, columns)
    for city in cities:
        city['latitude'] = float(city['latitude'])
        city['longitude'] = float(city['longitude'])
        city['elevation'] = float(city['elevation'])
    return cities
