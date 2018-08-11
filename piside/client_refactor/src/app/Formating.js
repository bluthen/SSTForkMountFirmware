export default {
    lat: function (lat) {
        lat = parseFloat(lat);
        let latstr = "";
        if (lat < 0) {
            latstr += 'S';
        } else {
            latstr += 'N';
        }
        lat = Math.abs(lat);
        latstr += parseInt(lat, 10) + '&deg;';
        const remain = lat - parseInt(lat);
        const min = parseInt(remain * 60);
        const sec = (remain - (min / 60.0)) * 60 * 60;
        return latstr + min + '\'' + sec.toFixed(1) + '"'
    },
    long: function (long) {
        long = parseFloat(long);
        let longstr = "";
        if (long < 0) {
            longstr += 'W';
        } else {
            longstr += 'E';
        }
        long = Math.abs(long);
        longstr += parseInt(long, 10) + '&deg;';
        const remain = long - parseInt(long);
        const min = parseInt(remain * 60);
        const sec = (remain - (min / 60.0)) * 60 * 60;
        return longstr + min + '\'' + sec.toFixed(1) + '"'
    },
    ra: function (ra) {
        ra = parseFloat(ra);
        const remain = ra - parseInt(ra, 10);
        const min = parseInt(remain * 60);
        const sec = (remain - (min / 60.0)) * 60 * 60;
        return parseInt(ra, 10) + 'h' + min + 'm' + sec.toFixed(1) + 's'
    },
    dec: function (dec) {
        if (dec !== null) {
            dec = parseFloat(dec);
            const remain = Math.abs(dec - parseInt(dec, 10));
            const arcmin = parseInt(remain * 60);
            const arcsec = (remain - (arcmin / 60.0)) * 60 * 60;
            return parseInt(dec, 10) + '&deg;' + arcmin + '\'' + arcsec.toFixed(1) + '"'
        } else {
            return '';
        }
    },
    escapeHTML: function (text, limit) {
        return $('<div>').text(text.substring(0, limit)).html();
    },
    absoluteURL: function (relativeURL) {
        return new URL(relativeURL, window.location.href).href;
    }

}