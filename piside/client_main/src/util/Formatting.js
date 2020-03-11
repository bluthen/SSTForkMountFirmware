const DEG_SYM = '°';

const Formatting = {
    absoluteURL: function (relativeURL) {
        return new URL(relativeURL, window.location.href).href;
    },
    degLat2Str(lat) {
        lat = parseFloat(lat);
        let latstr = "";
        if (lat < 0) {
            latstr += 'S';
        } else {
            latstr += 'N';
        }
        lat = Math.abs(lat);
        latstr += parseInt(lat, 10) + DEG_SYM;
        const remain = lat - parseInt(lat);
        const min = parseInt(remain * 60);
        const sec = (remain - (min / 60.0)) * 60 * 60;
        return latstr + min + '\'' + sec.toFixed(1) + '"';
    },
    degLong2Str(long) {
        long = parseFloat(long);
        let longstr = "";
        if (long < 0) {
            longstr += 'W';
        } else {
            longstr += 'E';
        }
        long = Math.abs(long);
        longstr += parseInt(long, 10) + DEG_SYM;
        const remain = long - parseInt(long);
        const min = parseInt(remain * 60);
        const sec = (remain - (min / 60.0)) * 60 * 60;
        return longstr + min + '\'' + sec.toFixed(1) + '"';
    },
    degRA2Str(ra) {
        if (ra !== null) {
            ra = parseFloat(ra);
            ra = ra * (24.0 / 360.0);
            const remain = ra - parseInt(ra, 10);
            const min = parseInt(remain * 60);
            const sec = (remain - (min / 60.0)) * 60 * 60;
            return parseInt(ra, 10) + 'h' + min + 'm' + sec.toFixed(1) + 's'
        } else {
            return '';
        }
    },
    hmsRA2deg(h, m, s) {
        return (360.0 / 24) *
            (parseFloat(h) +
            parseFloat(m) / 60.0 +
            parseFloat(s) / (60.0 * 60.0));
    },
    dmsDEC2deg(d, m, s) {
        const sign = Math.sign(d);
        return parseFloat(d) +
            sign * parseFloat(m) / 60.0 +
            sign * parseFloat(s) / (60.0 * 60.0);
    },
    degDEC2Str(dec) {
        if (dec !== null) {
            dec = parseFloat(dec);
            const remain = Math.abs(dec - parseInt(dec, 10));
            const arcmin = parseInt(remain * 60);
            const arcsec = (remain - (arcmin / 60.0)) * 60 * 60;
            return parseInt(dec, 10) + DEG_SYM + arcmin + '\'' + arcsec.toFixed(1) + '"'
        } else {
            return '';
        }
    },
    dateHourMinuteStr(date) {
        let h = date.getHours();
        let m = date.getMinutes();
        if (h < 10) {
            h = '0' + h;
        }
        if (m < 10) {
            m = '0' + m;
        }
        return h + ':' + m;
    },

    dateHourMinuteSecondStr(date) {
        const ret = Formatting.dateHourMinuteStr(date);
        let s = date.getSeconds();
        if (s < 10) {
            s = '0' + s;
        }
        return ret + ':' + s;
    },

    dateHourMinuteSecondMSStr(date) {
        const ret = Formatting.dateHourMinuteSecondStr(date);
        let s = parseInt(date.getMilliseconds() / 10, 10);
        if (s < 10) {
            s = '0' + s;
        }
        return ret + '.' + s;
    },
    deltaDegRA: function(frompt, topt) {
        const d_1 = topt - frompt;
        const d_2 = 360.0 + d_1;
        const d_3 = d_1 - 360;
        const ar = [d_1, d_2, d_3];
        const absar = [Math.abs(d_1), Math.abs(d_2), Math.abs(d_3)];
        const idx = absar.indexOf(Math.min.apply(Math, absar));
        return ar[idx];
    },
    deltaDegDec: function(frompt, topt) {
        return topt-frompt;
    },
    deg2arcseconds: function(pt) {
        return pt*60.*60.;
    }
};

export default Formatting;