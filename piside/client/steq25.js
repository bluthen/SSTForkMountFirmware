/*globals $ */
$(document).ready(function () {
    'use strict';

    var absoluteURL = function (relativeURL) {
        return new URL(relativeURL, window.location.href).href;
    };
    var status = null;

    console.log(absoluteURL('/'));
    window.socket = io(absoluteURL('/'));
    socket.on('connect', function (msg) {
        console.log('socket io connect.');
    });
    socket.on('status', function (msg) {
        //console.log(msg);
        status = msg;
        var status_radec = $('#status_radec');
        var status_altaz = $('#status_altaz');
        status_radec.empty();
        status_altaz.empty();
        if(status.ra) {
            status_radec.html(formating.ra((24.0/360)*status.ra)+'/'+formating.dec(status.dec));
        }
        if (status.alt) {
            status_altaz.html(formating.dec(status.alt)+'/'+formating.dec(status.az));
        }
        $('#status_ra_ticks').text('' + msg.rs + '/' + msg.rp);
        $('#status_dec_ticks').text('' + msg.ds + '/' + msg.dp);
    });
    socket.on('controls_response', function (msg) {
        console.log(msg);
    });


    var bind_direction_controls = function () {
        var up = $('#direction-controls-up');
        var upleft = $('#direction-controls-up-left');
        var upright = $('#direction-controls-up-right');
        var down = $('#direction-controls-down');
        var downleft = $('#direction-controls-down-left');
        var downright = $('#direction-controls-down-right');
        var left = $('#direction-controls-left');
        var right = $('#direction-controls-right');

        var all = up.add(upleft).add(upright).add(down).add(downleft).add(downright).add(left).add(right);

        var intervals = {};
        var oppositeMap = {'left': 'right', 'right': 'left', 'up': 'down', 'down': 'up'};
        var sendPressed = function (direction, speed) {
            console.log('sendPressed: ' + direction + ', ' + speed);
            socket.emit('manual_control', {direction: direction, speed: speed})
        };
        var sendUnpressed = function (direction) {
            console.log('sendUnpressed: ' + direction);
            socket.emit('manual_control', {direction: direction, speed: null})
        };
        var pressed = function (direction, speed) {
            //If we are already going opposite direction then ignore.
            if (intervals.hasOwnProperty(oppositeMap[direction])) {
                return;
            }
            console.log('Pressing: ' + direction);
            if (intervals.hasOwnProperty(direction)) {
                clearTimeout(intervals[direction]);
            }
            intervals[direction] = setInterval(function () {
                sendPressed(direction, speed);
            }, 250);
            sendPressed(direction, speed);
        };

        var unpressed = function (direction) {
            console.log('let go: ' + direction);
            if (intervals.hasOwnProperty(direction)) {
                clearInterval(intervals[direction]);
                delete intervals[direction];
            }
            sendUnpressed(direction);
        };


        all.on('mousedown touchstart', function (e) {
            var direction, i;
            var id = $(e.currentTarget).attr('id');
            var directions = id.split('direction-controls-')[1].split('-');
            var speed = $('#direction-controls-speed-fast').is(':checked');
            if (speed) {
                speed = 'fast';
            } else {
                speed = 'slow';
            }
            for (i = 0; i < directions.length; i++) {
                direction = directions[i];
                pressed(direction, speed);
            }
            e.preventDefault();
        });
        all.on('mouseup touchstop', function (e) {
            var direction, i;
            var id = $(e.currentTarget).attr('id');
            var directions = id.split('direction-controls-')[1].split('-');
            for (i = 0; i < directions.length; i++) {
                direction = directions[i];
                unpressed(direction);
            }
            e.preventDefault();
        });
    };

    function update_settings() {
        $.ajax({
            url: '/settings', dataType: 'json', success: function (data) {
                var location;
                $('#settings_ra_track_rate').val(data.ra_track_rate);
                $('#settings_dec_ticks_per_degree').val(data.dec_ticks_per_degree);
                $('#settings_ra_max_accel_tpss').val(data.ra_max_accel_tpss);
                $('#settings_dec_max_accel_tpss').val(data.ra_max_accel_tpss);
                $('#settings_ra_direction').val(data.micro.ra_direction);
                $('#settings_dec_direction').val(data.micro.dec_direction);
                $('#settings_ra_guide_rate').val(data.micro.ra_guide_rate);
                $('#settings_ra_slew_fast').val(data.ra_slew_fast);
                $('#settings_ra_slew_slow').val(data.ra_slew_slow);
                $('#settings_dec_guide_rate').val(data.micro.dec_guide_rate);
                $('#settings_dec_slew_fast').val(data.dec_slew_fast);
                $('#settings_dec_slew_slow').val(data.dec_slew_slow);
                location = $('#location');
                location.empty();
                if (data.location.name) {
                    location.text(data.location.name);
                }
            }
        });
    }

    update_settings();
    //init();
    bind_direction_controls();

    var formating = {
        lat: function (lat) {
            lat = parseFloat(lat);
            var latstr = "";
            if (lat < 0) {
                latstr += 'S';
            } else {
                latstr += 'N';
            }
            lat = Math.abs(lat);
            latstr += parseInt(lat, 10) + '&deg;';
            var remain = lat - parseInt(lat);
            var min = parseInt(remain * 60);
            var sec = (remain - (min / 60.0)) * 60 * 60;
            return latstr + min + '\'' + sec.toFixed(1) + '"'
        },
        long: function (long) {
            long = parseFloat(long);
            var longstr = "";
            if (long < 0) {
                longstr += 'W';
            } else {
                longstr += 'E';
            }
            long = Math.abs(long);
            longstr += parseInt(long, 10) + '&deg;';
            var remain = long - parseInt(long);
            var min = parseInt(remain * 60);
            var sec = (remain - (min / 60.0)) * 60 * 60;
            return longstr + min + '\'' + sec.toFixed(1) + '"'
        },
        ra: function (ra) {
            ra = parseFloat(ra);
            var remain = ra - parseInt(ra, 10);
            var min = parseInt(remain * 60);
            var sec = (remain - (min / 60.0)) * 60 * 60;
            return parseInt(ra, 10) + 'h' + min + 'm' + sec.toFixed(1) + 's'
        },
        dec: function (dec) {
            if (dec !== null) {
                dec = parseFloat(dec);
                var remain = Math.abs(dec - parseInt(dec, 10));
                var arcmin = parseInt(remain * 60);
                var arcsec = (remain - (arcmin / 60.0)) * 60 * 60;
                return parseInt(dec, 10) + '&deg;' + arcmin + '\'' + arcsec.toFixed(1) + '"'
            } else {
                return '';
            }
        }
    };

    var search_object = _.debounce(function () {
        var search = $('#search_txt').val();
        $('#search_info').empty();
        // TODO: Goto Action should only be there if we've synced once.
        var action = '<a href="#" class="sync"><i class="fas fa-sync" title="sync"></i></a>&nbsp; &nbsp;<a href="#" class="slewto"><i class="far fa-play-circle" title="slew"></i></a>'
        $.ajax({
            url: '/search_object',
            method: 'GET',
            data: {'search': search},
            success: function (d) {
                var i = 0, tr;
                var tbody = $('#search_results tbody');
                var syncclick = function (ra, dec) {
                    return function (e) {
                        sync(ra, dec);
                        e.preventDefault();
                    };
                };

                var slewtoclick = function (ra, dec) {
                    return function (e) {
                        slewto(ra, dec);
                        e.preventDefault();
                    };
                };
                tbody.empty();
                for (i = 0; i < d.planets.length; i++) {
                    tr = $('<tr><td>' + d.planets[i][0] + '</td><td>' + formating.ra(d.planets[i][1]) + '/' + formating.dec(d.planets[i][2]) + '</td><td>'+formating.dec(d.planets[i][3])+'/'+formating.dec(d.planets[i][4])+'</td><td></td><td></td><td>' + action + '</td>');
                    tbody.append(tr);
                    $('a.sync', tr).on('click', syncclick((360.0 / 24.0) * parseFloat(d.planets[i][1]), parseFloat(d.planets[i][2])));
                    $('a.slewto', tr).on('click',
                        slewtoclick((360.0 / 24.0) * parseFloat(d.planets[i][1]), parseFloat(d.planets[i][2])));
                }
                for (i = 0; i < d.dso.length; i++) {
                    tr = $('<tr><td>' + d.dso[i][20] + '</td><td>' + formating.ra(d.dso[i][0]) + '/' + formating.dec(d.dso[i][1]) + '</td><td>'+formating.dec(d.dso[i][21])+'/'+formating.dec(d.dso[i][22])+'</td><td>'+d.dso[i][4]+'</td><td>'+d.dso[i][9]+'"x'+d.dso[i][10]+'"</td></td><td>' + action + '</td>');
                    tbody.append(tr);
                    $('a.sync', tr).on('click', syncclick((360.0 / 24.0) * parseFloat(d.dso[i][0]), parseFloat(d.dso[i][1])));
                    $('a.slewto', tr).on('click',
                        slewtoclick((360.0 / 24.0) * parseFloat(d.dso[i][0]), parseFloat(d.dso[i][1])));
                }
                for (i = 0; i < d.stars.length; i++) {
                    tr = $('<tr><td>' + d.stars[i][6] + ', ' + d.stars[i][5] + '</td><td>' + formating.ra(d.stars[i][7]) + '/' + formating.dec(d.stars[i][8]) + '</td><td>'+formating.dec(d.stars[i][37])+'/'+formating.dec(d.stars[i][38])+'</td><td>'+d.stars[i][13]+'</td><td></td><td>' + action + '</td>');
                    tbody.append(tr);
                    $('a.sync', tr).on('click', syncclick((360.0 / 24.0) * parseFloat(d.stars[i][7]), parseFloat(d.stars[i][8])));
                    $('a.slewto', tr).on('click', slewtoclick((360.0 / 24.0) * parseFloat(d.stars[i][7]), parseFloat(d.stars[i][8])));
                }

                console.log(d);

                if (d.dso.length >= 10 || d.stars.length >= 10) {
                    $('#search_info').text('Too many results. Results were cut.')
                }
            }
        })
    }, 500);

    var set_location = function (lat, long, name) {
        $.ajax({
            url: '/set_location',
            method: 'PUT',
            data: {location: JSON.stringify({lat: lat, long: long, name: name})},
            success: function (d) {
                update_settings();
                //TODO: Confirm Dialog?
            },
            error: function (jqxhq, errortxt) {
                console.error(errortxt);
            }
        });
    };

    var search_location = _.throttle(function () {
        var search = $('#location_search_txt').val();
        $('#location_search_info').empty();
        var action = '<a href="#"><i class="fas fa-globe" title="set"></i>Set</a>';
        $.ajax({
            url: '/search_location',
            method: 'GET',
            data: {'search': search},
            success: function (d) {
                var i;
                var setclicked = function(lat, lon, name) {
                    return function(e) {
                        set_location(lat, lon, name);
                        e.preventDefault();
                    }
                };
                var tbody = $('#location_search_results tbody');
                tbody.empty();
                for (i = 0; i < d.cities.length; i++) {
                    var tr = $('<tr><td>' + d.cities[i][2] + ', ' + d.cities[i][4] + ' ' + d.cities[i][1] + '</td><td>' + formating.lat(d.cities[i][9]) + ' ' + formating.long(d.cities[i][10]) + '</td><td>' + action + '</td>');
                    tbody.append(tr);
                    $('a', tr).on('click', setclicked(parseFloat(d.cities[i][9]), parseFloat(d.cities[i][10]), d.cities[i][2] + ', ' + d.cities[i][4]));
                }

                console.log(d);
                if (d.cities.length >= 20) {
                    $('#location_search_info').text('Too many results. Results were cut.');
                }
            }
        })
    }, 500, {leading: false, trailing: true});

    var convert_manual_coordinates = function () {
        var ra = $('#goto_manual_ra').val();
        var dec = $('#goto_manual_dec').val();

        var ras = ra.split(' ');
        if (ras.length !== 3) {
            //TODO: Error
        }
        ra = (360.0 / 24.0) * parseInt(ras[0], 10) + parseInt(ras[1], 10) / 60.0 + parseFloat(ras[2]) / (60 * 60);

        var decs = dec.split(' ');
        dec = parseInt(decs[0], 10) + parseInt(decs[1], 10) / 60.0 + parseFloat(decs[2]) / (60 * 60);
        return {ra: ra, dec: dec};
    };

    var sync = function (ra, dec) {
        $.ajax({
            url: '/sync',
            method: 'PUT',
            data: {ra: ra, dec: dec},
            success: function (d) {
                console.log('synced')
            },
            error: function (jq, errortxt) {
                console.error(errortxt);
            }
        });
    };

    var slewto = function (ra, dec) {
        $.ajax({
            url: '/slewto',
            method: 'PUT',
            data: {ra: ra, dec: dec},
            success: function (d) {
                //TODO: Dialog to abort?
            },
            error: function (jq, errortxt) {
                console.error(errortxt);
            }
        });
    };

    $('#location_manual_set').click(function () {
        var match, lat_deg, long_deg;
        var lat = $('#manual_lat').val();
        var long = $('#manual_long').val();
        var name = $('#manual_name').val().trim();

        if (!name) {
            //TODO: Show missing name
        }

        // lat has two formats
        lat = lat.toUpperCase();
        if (lat.match(/^-?\d*(\.\d+)?$/)) {
            //Degree mode
            lat_deg = parseFloat(lat)
        } else {
            match = lat.match(/^([NS])(\d+)[° ](\d+)' ?(\d*.?\d+)?/);
            if (match) {
                lat_deg = parseInt(match[2], 10);
                if (match[1] === 'S') {
                    lat_deg = -lat_deg;
                }
                lat_deg += parseFloat(match[3]) / 60.0;
                lat_deg += parseFloat(match[4]) / (60.0 * 60.0);
            } else {
                //Invalid
                //TODO: Error message
            }
        }

        long = long.toUpperCase();
        if (long.match(/^-?\d*(\.\d+)?$/)) {
            //Degree mode
            long_deg = parseFloat(long)
        } else {
            match = long.match(/^([WE])(\d+)[° ](\d+)' ?(\d*.?\d+)?/);
            if (match) {
                long_deg = parseInt(match[2], 10);
                if (match[1] === 'W') {
                    long_deg = -long_deg;
                }
                long_deg += parseFloat(match[3]) / 60.0;
                long_deg += parseFloat(match[4]) / (60.0 * 60.0);
            } else {
                //Invalid
                //TODO: Error message
            }
        }
        console.log(lat_deg, long_deg);

        //convert coordinates
        //Check lat long and name are okay
        set_location(lat_deg, long_deg, name);
    });

    $('#location_search_txt').on('input', search_location);
    $('#search_txt').on('input', search_object);
    $('#manual_sync').on('click', function () {
        var coords = convert_manual_coordinates();
        sync(coords.ra, coords.dec);
    });
    $('#manual_slewto').on('click', function () {
        var coords = convert_manual_coordinates();
        slewto(coords.ra, coords.dec);
    });

    $('#settings_save').click(function () {
        var settings = {
            ra_track_rate: $('#settings_ra_track_rate').val(),
            dec_ticks_per_degree: $('#settings_dec_ticks_per_degree').val(),
            ra_direction: $('#settings_ra_direction').val(),
            dec_direction: $('#settings_dec_direction').val(),
            ra_max_accel_tpss: $('#settings_ra_max_accel_tpss').val(),
            dec_max_accel_tpss: $('#settings_dec_max_accel_tpss').val(),
            ra_guide_rate: $('#settings_ra_guide_rate').val(),
            ra_slew_fast: $('#settings_ra_slew_fast').val(),
            ra_slew_slow: $('#settings_ra_slew_slow').val(),
            dec_guide_rate: $('#settings_dec_guide_rate').val(),
            dec_slew_fast: $('#settings_dec_slew_fast').val(),
            dec_slew_slow: $('#settings_dec_slew_slow').val()
        };
        $.ajax({
            url: '/settings',
            method: 'PUT',
            data: {'settings': JSON.stringify(settings)},
            success: function () {
                $('#settings_save_status').text('Saved').show().fadeOut(1000);
            },
            error: function (jqXHR, textStatus) {
                $('#settings_save_status').text(textStatus).show().fadeOut(1000);
            }
        });
    });

    $.ajax({
        url: '/set_time',
        method: 'PUT',
        data: {time: (new Date()).toISOString()},
        success: function (d) {
            console.log('Time synced:' + d);
        },
        error: function (jqXHR, text) {
            console.error(text);

        }
    });
});