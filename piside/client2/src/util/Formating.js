const DEG_SYM = '°';

const Formating = {
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
            h = '0'+h
        }
        if (m < 10) {
            m = '0'+m
        }
        return h+':'+m;
    }

};

export default Formating;