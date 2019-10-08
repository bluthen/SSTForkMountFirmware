import math


def t_x_vmax(a, v_0, v_max):
    t_maxv = (v_max - v_0) / a
    x_maxv = 0.5 * a * t_maxv * t_maxv + v_0 * t_maxv
    return t_maxv, x_maxv


def t_at_x(a, v_0, x):
    """
    Only works if x is before gets to v_max. x < x_maxv
    """
    s = 1.0
    if a < 0.0:
        s = -1.0
    return (-v_0 + s * math.sqrt(v_0 * v_0 + 2 * a * x))/a


def v_at_t(a, v_0, v_max, t):
    v = a * t + v_0
    if abs(v) > abs(v_max):
        v = v_max
    return v


def calc_speed_sleeps(delta, a, v_0, v_max, v_track, type):
    v_trackcopy = v_track
    if delta < 0:
        a = math.copysign(a, -1)
        v_max = math.copysign(v_max, -1)
        # v_track = 0
    ret = []
    t_maxv, x_maxv = t_x_vmax(a, v_0, v_max)
    if abs(2 * x_maxv) >= abs(delta):
        # print({'a': a, 'v_0': v_0, 'd2': delta/2.0})
        t_hdelta = t_at_x(a, v_0, delta / 2.0)
        v_hdelta = v_at_t(a, v_0, v_max, t_hdelta)
        t_total = 2 * t_hdelta / (1.0 - v_track / v_hdelta)
        t_track = t_total - 2 * t_hdelta
        if t_track < 0:
            # We need v_max to be slower
            return calc_speed_sleeps(delta, a, v_0, v_hdelta/2.0, v_track, type)
        # print({'t_maxv': t_maxv, 'x_maxv': x_maxv, 'delta': delta, 't_hdelta': t_hdelta, 't_track': t_track})
        ret.append({'type': type, 'speed': v_hdelta, 'sleep': t_hdelta + t_track})
        ret.append({'type': type, 'speed': v_trackcopy, 'sleep': t_hdelta})
    else:
        t_c = (delta - 2 * x_maxv) / v_max
        t_total = (2 * t_maxv + t_c) / (1 - v_track / v_max)
        t_track = t_total - (2.0 * t_maxv + t_c)
        if t_track > t_c:
            # We need v_max to be slower
            return calc_speed_sleeps(delta, a, v_0, v_max/2, v_track, type)
        # print(t_maxv, t_c, t_track)
        ret.append({'type': type, 'speed': v_max, 'sleep': t_maxv + t_c + t_track})
        ret.append({'type': type, 'speed': v_trackcopy, 'sleep': t_maxv})
    return ret


def combine_speed_sleeps(ra_times, dec_times):
    # First one from both are combined
    a = []
    a.extend(ra_times)
    a.extend(dec_times)
    a = sorted(a, key=lambda s: s['csleep'])
    t = 0
    ret = []
    ctime = 0
    for r in a:
        t = {'ra_speed': None, 'dec_speed': None, 'sleep': r['csleep'] - ctime}
        if r['type'] == 'ra':
            t['ra_speed'] = r['speed']
        else:
            t['dec_speed'] = r['speed']
        ctime += t['sleep']
        ret.append(t)
    return ret
