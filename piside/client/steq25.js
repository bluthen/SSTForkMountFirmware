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
        var radecstr;
        //console.log(msg);
        status = msg;
        var status_radec = $('#status_radec');
        var status_altaz = $('#status_altaz');
        var status_radec2 = $('#slewModalStatus');
        var status_altaz2 = $('#slewModalAltAzStatus');
        var status_steps2 = $('#slewModalStepsStatus');
        var slewmodal = $('#slewModal');
        status_radec.empty();
        status_altaz.empty();
        if (status.ra) {
            radecstr = formating.ra((24.0 / 360) * status.ra) + '/' + formating.dec(status.dec);
            status_radec.html(radecstr);
            status_radec2.html(radecstr);
        }
        if (status.alt) {
            status_altaz.html(formating.dec(status.alt) + '/' + formating.dec(status.az));
            status_altaz2.html(formating.dec(status.alt) + '/' + formating.dec(status.az));
        }
        $('#status_ra_ticks').text('' + msg.rs + '/' + msg.rp);
        $('#status_dec_ticks').text('' + msg.ds + '/' + msg.dp);
        status_steps2.text(msg.rp+'/'+msg.dp);
        $('#status_time').text(msg.time);
        if (!status.slewing && slewmodal.hasClass('show')) {
            slewmodal.modal('hide');
        }
        if (msg.tracking) {
            $('#settings_stop_tracking').show();
            $('#settings_start_tracking').hide();
        } else {
            $('#settings_start_tracking').show();
            $('#settings_stop_tracking').hide();
        }
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
            }, 100);
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

        all.click(function (e) {
            e.preventDefault();
            return false;
        });

        var get_manual_speed = function () {
            var speed;
            if ($('#direction-controls-speed-fastest').is(':checked')) {
                speed = 'fastest';
            }
            if ($('#direction-controls-speed-faster').is(':checked')) {
                speed = 'faster';
            }
            if ($('#direction-controls-speed-medium').is(':checked')) {
                speed = 'medium';
            }
            if ($('#direction-controls-speed-slower').is(':checked')) {
                speed = 'slower';
            }
            if ($('#direction-controls-speed-slowest').is(':checked')) {
                speed = 'slowest';
            }
            return speed;
        };


        all.on('mousedown touchstart', function (e) {
            var direction, i;
            var id = $(e.currentTarget).attr('id');
            console.log('mousedown', id);
            var directions = id.split('direction-controls-')[1].split('-');
            var speed = get_manual_speed();
            for (i = 0; i < directions.length; i++) {
                direction = directions[i];
                pressed(direction, speed);
            }
            e.preventDefault();
        });
        all.on('mouseleave mouseup touchend touchcancel', function (e) {
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
                $('#settings_ra_direction').val(data.micro.ra_direction);
                $('#settings_dec_direction').val(data.micro.dec_direction);
                $('#settings_ra_guide_rate').val(data.micro.ra_guide_rate);
                $('#settings_ra_slew_fastest').val(data.ra_slew_fastest);
                $('#settings_ra_slew_faster').val(data.ra_slew_faster);
                $('#settings_ra_slew_medium').val(data.ra_slew_medium);
                $('#settings_ra_slew_slower').val(data.ra_slew_slower);
                $('#settings_ra_slew_slowest').val(data.ra_slew_slowest);
                $('#settings_dec_guide_rate').val(data.micro.dec_guide_rate);
                $('#settings_dec_slew_fastest').val(data.dec_slew_fastest);
                $('#settings_dec_slew_faster').val(data.dec_slew_faster);
                $('#settings_dec_slew_medium').val(data.dec_slew_medium);
                $('#settings_dec_slew_slower').val(data.dec_slew_slower);
                $('#settings_dec_slew_slowest').val(data.dec_slew_slowest);
                location = $('#location');
                location.empty();
                if (data.location.name) {
                    location.text(data.location.name);
                }
                if (data.park_position) {
                    $('#settings_park_position').html(formating.dec(data.park_position.alt) + '/' + formating.dec(data.park_position.az));
                    $('#settings_unset_park_position').show();
                } else {
                    $('#settings_park_position').html('None Set');
                    $('#settings_unset_park_position').hide();
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

    var search_object_counter = 0;

    var search_object = _.debounce(function () {
        var sc;
        var search = $('#search_txt').val();
        if (search.trim() === '') {
            return;
        }
        search_object_counter++;
        sc = search_object_counter;
        $('#search_info').empty();
        // TODO: Goto Action should only be there if we've synced once.
        var sync_action = '<button type="button" class="sync btn btn-warning"><i class="fas fa-sync" title="sync"></i>Sync</button>';
        var slew_action = '<button type="button" class="slewto btn btn-success"><i class="far fa-play-circle" title="slew"></i>Slew</button>';
        $('#search_spinner').show();
        $('#search_results').hide();
        $.ajax({
            url: '/search_object',
            method: 'GET',
            data: {'search': search},
            success: function (d) {
                if (sc !== search_object_counter) {
                    return;
                }
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
                    tr = $('<tr>' +
                        '<th scope="row">' + d.planets[i][0] + '</th>' +
                        '<td>' + slew_action + '</td>' +
                        '<td>' + sync_action + '</td>' +
                        '<td>' + formating.ra(d.planets[i][1]) + '/ ' + formating.dec(d.planets[i][2]) + '</td>' +
                        '<td>' + formating.dec(d.planets[i][3]) + '/ ' + formating.dec(d.planets[i][4]) + '</td>' +
                        '<td></td>' +
                        '<td></td>' +
                        '</tr>');
                    tbody.append(tr);
                    $('button.sync', tr).on('click', syncclick((360.0 / 24.0) * parseFloat(d.planets[i][1]), parseFloat(d.planets[i][2])));
                    $('button.slewto', tr).on('click',
                        slewtoclick((360.0 / 24.0) * parseFloat(d.planets[i][1]), parseFloat(d.planets[i][2])));
                }
                for (i = 0; i < d.dso.length; i++) {
                    tr = $('<tr>' +
                        '<th scope="row">' + d.dso[i][20] + '</th>' +
                        '<td>' + slew_action + '</td>' +
                        '<td>' + sync_action + '</td>' +
                        '<td>' + formating.ra(d.dso[i][0]) + '/ ' + formating.dec(d.dso[i][1]) + '</td>' +
                        '<td>' + formating.dec(d.dso[i][21]) + '/ ' + formating.dec(d.dso[i][22]) + '</td>' +
                        '<td>' + d.dso[i][4] + '</td>' +
                        '<td>' + d.dso[i][9] + '"x' + d.dso[i][10] + '"</td>' +
                        '</tr>');
                    tbody.append(tr);
                    $('button.sync', tr).on('click', syncclick((360.0 / 24.0) * parseFloat(d.dso[i][0]), parseFloat(d.dso[i][1])));
                    $('button.slewto', tr).on('click',
                        slewtoclick((360.0 / 24.0) * parseFloat(d.dso[i][0]), parseFloat(d.dso[i][1])));
                }
                for (i = 0; i < d.stars.length; i++) {
                    tr = $('<tr>' +
                        '<th scope="row">' + d.stars[i][6] + ', ' + d.stars[i][5] + '</th>' +
                        '<td>' + slew_action + '</td>' +
                        '<td>' + sync_action + '</td>' +
                        '<td>' + formating.ra(d.stars[i][7]) + '/ ' + formating.dec(d.stars[i][8]) + '</td>' +
                        '<td>' + formating.dec(d.stars[i][37]) + '/ ' + formating.dec(d.stars[i][38]) + '</td>' +
                        '<td>' + d.stars[i][13] + '</td>' +
                        '<td></td>' +
                        '</tr>');
                    tbody.append(tr);
                    $('button.sync', tr).on('click', syncclick((360.0 / 24.0) * parseFloat(d.stars[i][7]), parseFloat(d.stars[i][8])));
                    $('button.slewto', tr).on('click', slewtoclick((360.0 / 24.0) * parseFloat(d.stars[i][7]), parseFloat(d.stars[i][8])));
                }

                console.log(d);

                if (d.dso.length >= 10 || d.stars.length >= 10) {
                    $('#search_info').text('Too many results. Results were cut.')
                }
                $('#search_spinner').hide();
                $('#search_results').show();
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
            error: function (jq, errorstatus, errortxt) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    };


    var search_location_counter = 0;
    var search_location = _.throttle(function () {
        var sc;
        var search = $('#location_search_txt').val();
        if (!search.trim()) {
            return;
        }
        search_location_counter++;
        sc = search_location_counter;
        $('#location_search_info').empty();
        var action = '<button type="button" class="btn btn-success"><i class="fas fa-globe" title="set"></i>Set</button>';
        $('#location_search_spinner').show();
        $('#location_search_results').hide();
        $.ajax({
            url: '/search_location',
            method: 'GET',
            data: {'search': search},
            success: function (d) {

                if (sc !== search_location_counter) {
                    return;
                }
                var i;
                var setclicked = function (lat, lon, name) {
                    return function (e) {
                        set_location(lat, lon, name);
                        e.preventDefault();
                    }
                };
                var tbody = $('#location_search_results tbody');
                tbody.empty();
                for (i = 0; i < d.cities.length; i++) {
                    var tr = $('<tr><td>' + d.cities[i][2] + ', ' + d.cities[i][4] + ' ' + d.cities[i][1] + '</td><td>' + formating.lat(d.cities[i][9]) + ' ' + formating.long(d.cities[i][10]) + '</td><td>' + action + '</td>');
                    tbody.append(tr);
                    $('button', tr).on('click', setclicked(parseFloat(d.cities[i][9]), parseFloat(d.cities[i][10]), d.cities[i][2] + ', ' + d.cities[i][4]));
                }

                console.log(d);
                if (d.cities.length >= 20) {
                    $('#location_search_info').text('Too many results. Results were cut.');
                }
                $('#location_search_spinner').hide();
                $('#location_search_results').show();
            }
        })
    }, 500, {leading: false, trailing: true});

    var convert_manual_coordinates_radec = function () {
        var i, ra, dec, decsign;
        var ras = [
            $('#goto_manual_ra_hh').val().trim(),
            $('#goto_manual_ra_mm').val().trim(),
            $('#goto_manual_ra_ss').val().trim()
        ];
        var decs = [
            $('#goto_manual_dec_dd').val().trim(),
            $('#goto_manual_dec_mm').val().trim(),
            $('#goto_manual_dec_ss').val().trim()
        ];

        for (i = 0; i < ras.length; i++) {
            ras[i] = parseInt(ras[i], 10);
            if (isNaN(ras[i])) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text("Invalid RA Coordinates Entered.");
                $('#errorInfoModal').modal();
                return null;
            }
        }
        for (i = 0; i < decs.length; i++) {
            decs[i] = parseInt(decs[i], 10);
            if (isNaN(decs[i])) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text("Invalid DEC Coordinates Entered.");
                $('#errorInfoModal').modal();
                return null;
            }
        }

        ra = (360.0 / 24.0) * (ras[0] + (ras[1] / 60.0) + (ras[2] / (60 * 60)));
        if (decs[0] === 0) {
            decsign = 1;
        } else {
            decsign = decs[0] / Math.abs(decs[0]);
        }
        dec = decs[0] + decsign * (decs[1] / 60.0) + decsign * (decs[2] / (60 * 60));
        return {ra: ra, dec: dec};
    };

    var convert_manual_coordinates_altaz = function () {
        var i, alts, azs, alt, az, altsign;
        alts = [
            $('#goto_manual_alt_dd').val().trim(),
            $('#goto_manual_alt_mm').val().trim(),
            $('#goto_manual_alt_ss').val().trim()
        ];
        azs = [
            $('#goto_manual_az_ddd').val().trim(),
            $('#goto_manual_az_mm').val().trim(),
            $('#goto_manual_az_ss').val().trim()
        ];

        for (i = 0; i < alts.length; i++) {
            alts[i] = parseInt(alts[i], 10);
            if (isNaN(alts[i])) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text("Invalid Alt Coordinates Entered.");
                $('#errorInfoModal').modal();
                return null;
            }
        }
        for (i = 0; i < azs.length; i++) {
            azs[i] = parseInt(azs[i], 10);
            if (isNaN(azs[i])) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text("Invalid Az Coordinates Entered.");
                $('#errorInfoModal').modal();
                return null;
            }
        }
        if (alts[0] === 0) {
            altsign = 1;
        } else {
            altsign = alts[0] / Math.abs(alts[0]);
        }
        alt = alts[0] + altsign * (alts[1] / 60.0) + altsign * (alts[2] / (60 * 60));
        az = azs[0] + (azs[1] / 60.0) + (azs[2] / (60 * 60));
        return {alt: alt, az: az};
    };

    var convert_manual_coordinates_steps = function() {
        var ra, dec;
        ra = parseInt($('#goto_manual_steps_ra').val().trim(), 10);
        dec = parseInt($('#goto_manual_steps_dec').val().trim(), 10);
        if (isNaN(ra) || isNaN(dec)) {
            $('#errorInfoModalTitle').text('Error');
            $('#errorInfoModalBody').text("Invalid Step values Entered.");
            $('#errorInfoModal').modal();
            return null;
        }
        return {ra: ra, dec: dec};
    };

    var sync = function (ra, dec) {
        $.ajax({
            url: '/sync',
            method: 'PUT',
            dataType: 'json',
            data: {ra: ra, dec: dec},
            success: function (d) {
                console.log('synced');
                var errstr = '';
                if (d.ra_error) {
                    errstr += 'RAErr: ' + (d.ra_error * 100.0).toFixed(2) + '%';
                }
                if (d.dec_error) {
                    errstr += ' DECErr: ' + (d.dec_error * 100.0).toFixed(2) + '%';
                }
                $('#errorInfoModalTitle').text('Info');
                $('#errorInfoModalBody').html('The mount is now synced.<br>' + errstr);
                $('#errorInfoModal').modal();
            },
            error: function (jq, errorstatus, errortxt) {
                console.error(errortxt);
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    };

    var syncaltaz = function (alt, az) {
        //TODO: Combine with sync
        $.ajax({
            url: '/sync',
            method: 'PUT',
            data: {alt: alt, az: az},
            success: function (d) {
                console.log('synced');
                $('#errorInfoModalTitle').text('Info');
                $('#errorInfoModalBody').text('The mount is now synced.');
                $('#errorInfoModal').modal();
            },
            error: function (jq, errorstatus, errortxt) {
                console.error(errortxt);
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    };


    var slewto = function (ra, dec) {
        $('#slewModalStatus').show();
        $('#slewModalStepsStatus').hide();
        $('#slewModalAltAzStatus').hide();
        $.ajax({
            url: '/slewto',
            method: 'PUT',
            data: {ra: ra, dec: dec},
            success: function (d) {
                var radecstr = formating.ra((24.0 / 360) * ra) + '/' + formating.dec(dec);
                $('#slewModalTarget').html(radecstr);
                //TODO: Dialog to abort?
                $('#slewModal').data('bs.modal', null).modal({backdrop: 'static', keyboard: false});
            },
            error: function (jq, errorstatus, errortxt) {
                console.error(errortxt);
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    };

    var slewtoaltaz = function (alt, az) {
        //TODO: Combine with slewto
        $('#slewModalStatus').hide();
        $('#slewModalStepsStatus').hide();
        $('#slewModalAltAzStatus').show();
        $.ajax({
            url: '/slewto',
            method: 'PUT',
            data: {alt: alt, az: az},
            success: function (d) {
                var altAzStr = formating.dec(alt) + '/' + formating.dec(az);
                $('#slewModalTarget').html(altAzStr);
                //TODO: Dialog to abort?
                $('#slewModal').data('bs.modal', null).modal({backdrop: 'static', keyboard: false});
            },
            error: function (jq, errorstatus, errortxt) {
                console.error(errortxt);
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    };


    var slewtosteps = function (ra, dec) {
        $('#slewModalStepsStatus').show();
        $('#slewModalStatus').hide();
        $('#slewModalAltAzStatus').hide();
        $.ajax({
            url: '/slewto',
            method: 'PUT',
            data: {ra_steps: ra, dec_steps: dec},
            success: function (d) {
                var radecstr = ra + '/' + dec;
                $('#slewModalTarget').html(radecstr);
                //TODO: Dialog to abort?
                $('#slewModal').data('bs.modal', null).modal({backdrop: 'static', keyboard: false});
            },
            error: function (jq, errorstatus, errortxt) {
                console.error(errortxt);
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    };


    $('#slewModalCancel').click(function () {
        $.ajax({
            url: '/slewto',
            method: 'DELETE',
            success: function (d) {
                $('#slewModal').modal('hide');
            },
            error: function (jq, errorstatus, errortxt) {
                console.error(errorstatus, errortxt, jq.responseText);
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        })
    });

    $('#location_manual_unset').click(function () {
        $.ajax({
            url: '/set_location',
            method: 'DELETE',
            success: function () {
            },
            error: function (jq, errorstatus, errortxt) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    });


    $('#location_manual_set').click(function () {
        var match, lat_deg, long_deg;
        var lat = $('#manual_lat').val();
        var long = $('#manual_long').val();
        var name = $('#manual_name').val().trim();

        if (!name || name.trim() === '') {
            console.error('Invalid name entered.');
            $('#errorInfoModalTitle').text('Error');
            $('#errorInfoModalBody').text('Invalid name for location entered.');
            $('#errorInfoModal').modal();
            return;
        }

        // lat has two formats
        lat = lat.toUpperCase();
        if (lat.match(/^[-+]?\d*(\.\d+)?$/)) {
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
                console.error('Invalid Latitude entered.');
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text('Invalid latitude format entered.');
                $('#errorInfoModal').modal();
                return;
            }
        }

        long = long.toUpperCase();
        if (long.match(/^[-+]?\d*(\.\d+)?$/)) {
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
                console.error('Invalid Longitude entered.');
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text('Invalid longitude format entered.');
                $('#errorInfoModal').modal();
                return;
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
        var coords;
        if ($('#goto_manual_coord_select-radec').is(':checked')) {
            coords = convert_manual_coordinates_radec();
            if (coords) {
                sync(coords.ra, coords.dec);
            }
        } else if($('#goto_manual_coord_select-altaz').is(':checked')) {
            coords = convert_manual_coordinates_altaz();
            syncaltaz(coords.alt, coords.az);
        } else {
        }
    });
    $('#manual_slewto').on('click', function () {
        var coords;
        if ($('#goto_manual_coord_select-radec').is(':checked')) {
            coords = convert_manual_coordinates_radec();
            slewto(coords.ra, coords.dec);
        } else if($('#goto_manual_coord_select-altaz').is(':checked')) {
            coords = convert_manual_coordinates_altaz();
            slewtoaltaz(coords.alt, coords.az);
        } else {
            coords = convert_manual_coordinates_steps();
            if (coords !== null) {
                slewtosteps(coords.ra, coords.dec);
            }
        }
    });

    $('#settings_save').click(function () {
        var settings = {
            ra_track_rate: $('#settings_ra_track_rate').val(),
            dec_ticks_per_degree: $('#settings_dec_ticks_per_degree').val(),
            ra_direction: $('#settings_ra_direction').val(),
            dec_direction: $('#settings_dec_direction').val(),
            ra_guide_rate: $('#settings_ra_guide_rate').val(),
            ra_slew_fastest: $('#settings_ra_slew_fastest').val(),
            ra_slew_faster: $('#settings_ra_slew_faster').val(),
            ra_slew_medium: $('#settings_ra_slew_medium').val(),
            ra_slew_slower: $('#settings_ra_slew_slower').val(),
            ra_slew_slowest: $('#settings_ra_slew_slowest').val(),
            dec_guide_rate: $('#settings_dec_guide_rate').val(),
            dec_slew_fastest: $('#settings_dec_slew_fastest').val(),
            dec_slew_faster: $('#settings_dec_slew_faster').val(),
            dec_slew_medium: $('#settings_dec_slew_medium').val(),
            dec_slew_slower: $('#settings_dec_slew_slower').val(),
            dec_slew_slowest: $('#settings_dec_slew_slowest').val()
        };
        $.ajax({
            url: '/settings',
            method: 'PUT',
            data: {'settings': JSON.stringify(settings)},
            success: function () {
                $('#settings_save_status').text('Saved').show().fadeOut(1000);
            },
            error: function (jq, errorstatus, errortxt) {
                console.error('Invalid Latitude entered.');
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
                return;
            }
        });
    });

    $('#settings_park').click(function () {
        $.ajax({
            url: '/park',
            method: 'PUT',
            success: function () {
                $('#slewModalTarget').html('Parking...');
                //TODO: Dialog to abort?
                $('#slewModal').data('bs.modal', null).modal({backdrop: 'static', keyboard: false});
            },
            error: function (jq, errorstatus, errortxt) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    });

    $('#settings_set_park_position').click(function () {
        console.log('Setting park position');
        $.ajax({
            url: '/set_park_position',
            method: 'PUT',
            success: function () {
                update_settings();
            },
            error: function (jq, errorstatus, errortxt) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    });

    $('#settings_unset_park_position').click(function () {
        $.ajax({
            url: '/set_park_position',
            method: 'DELETE',
            success: function () {
                update_settings();
            },
            error: function (jq, errorstatus, errortxt) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });

    });

    $('#settings_start_tracking').click(function () {
        $.ajax({
            url: '/start_tracking',
            method: 'PUT',
            success: function () {
            },
            error: function (jq, errorstatus, errortxt) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    });

    $('#settings_stop_tracking').click(function () {
        $.ajax({
            url: '/stop_tracking',
            method: 'PUT',
            success: function () {
            },
            error: function (jq, errorstatus, errortxt) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    });

    $('#settings-color-scheme-default, #settings-color-scheme-nightvision').change(function () {
        if ($('#settings-color-scheme-default').is(':checked')) {
            $('#bootstrapcss').attr('href', 'bootstrap/css/bootstrap.min.css');
            $('#maincss').attr('href', 'main.css');
        } else {
            $('#bootstrapcss').attr('href', 'bootstrap/css/bootstrap.min.redlights.css');
            $('#maincss').attr('href', 'main.redlights.css');
        }
    });

    $('#goto_manual_coord_select-radec, #goto_manual_coord_select-altaz, #goto_manual_coord_select-steps').change(function () {
        if ($('#goto_manual_coord_select-radec').is(':checked')) {
            $('#goto_manual_coord_altaz').hide();
            $('#goto_manual_coord_steps').hide();
            $('#goto_manual_coord_radec').show();
            $('#manual_sync').show();
        } else if ($('#goto_manual_coord_select-altaz').is(':checked')) {
            $('#goto_manual_coord_radec').hide();
            $('#goto_manual_coord_steps').hide();
            $('#goto_manual_coord_altaz').show();
            $('#manual_sync').show();
        } else {
            $('#goto_manual_coord_radec').hide();
            $('#goto_manual_coord_altaz').hide();
            $('#goto_manual_coord_steps').show();
            $('#manual_sync').hide();
        }
    });

    var numbericIntOnly = function (plusminus) {
        return function (e) {
            // https://weblog.west-wind.com/posts/2011/Apr/22/Restricting-Input-in-HTML-Textboxes-to-Numeric-Values
            var key = e.which || e.keyCode;
            console.log(key);

            if (!e.shiftKey && !e.altKey && !e.ctrlKey &&
                // numbers
                key >= 48 && key <= 57 ||
                // Numeric keypad
                key >= 96 && key <= 105 ||
                // comma, period and minus on keypad
                (plusminus && (key === 187 || key === 189 || key === 109 || key === 107)) ||
                // Backspace and Tab and Enter
                key === 8 || key === 9 || key === 13 ||
                // Home and End
                key === 35 || key === 36 ||
                // left and right arrows
                key === 37 || key === 39 ||
                // Del and Ins
                key === 46 || key === 45)
                return true;

            return false;
        }
    };

    $('#goto_manual_ra_hh, #goto_manual_ra_mm, #goto_manual_ra_ss, #goto_manual_dec_dd, #goto_manual_dec_mm, #goto_manual_dec_ss, #goto_manual_alt_dd, #goto_manual_alt_mm, #goto_manual_alt_ss, #goto_manual_az_ddd, #goto_manual_az_mm, #goto_manual_az_ss').focus(function () {
        $(this).select();
    });

    $('#goto_manual_ra_hh, #goto_manual_ra_mm, #goto_manual_ra_ss, #goto_manual_dec_mm, #goto_manual_dec_ss, #goto_manual_alt_mm, #goto_manual_alt_ss, #goto_manual_az_ddd, #goto_manual_az_mm, #goto_manual_az_ss').keydown(numbericIntOnly(false));
    $('#goto_manual_dec_dd, #goto_manual_alt_dd, #goto_manual_steps_ra, #goto_manual_steps_ra').keydown(numbericIntOnly(true));

    $('#goto_manual_ra_hh').keyup(function (e) {
        console.log(this);
        if (this.selectionStart === this.selectionEnd && this.value.length === 2) {
            $('#goto_manual_ra_mm').focus();
        }
    });

    $('#goto_manual_ra_mm').keyup(function (e) {
        console.log(this);
        if (this.selectionStart === this.selectionEnd && this.value.length === 2) {
            $('#goto_manual_ra_ss').focus();
        }
    });

    $('#goto_manual_ra_ss').keyup(function (e) {
        console.log(this);
        if (this.selectionStart === this.selectionEnd && this.value.length === 2) {
            $('#goto_manual_dec_dd').focus();
        }
    });

    $('#goto_manual_dec_dd').keyup(function (e) {
        console.log(this);
        if (this.selectionStart === this.selectionEnd && ((this.value[0] !== '-' && this.value[0] !== '+' && this.value.length === 2) || this.value.length === 3)) {
            $('#goto_manual_dec_mm').focus();
        }
    });

    $('#goto_manual_dec_mm').keyup(function (e) {
        console.log(this);
        if (this.selectionStart === this.selectionEnd && this.value.length === 2) {
            $('#goto_manual_dec_ss').focus();
        }
    });

    $('#goto_manual_alt_dd').keyup(function (e) {
        if (this.selectionStart === this.selectionEnd && ((this.value[0] !== '-' && this.value[0] !== '+' && this.value.length === 2) || this.value.length === 3)) {
            $('#goto_manual_alt_mm').focus();
        }
    });

    $('#goto_manual_alt_mm').keyup(function (e) {
        if (this.selectionStart === this.selectionEnd && this.value.length === 2) {
            $('#goto_manual_alt_ss').focus();
        }
    });

    $('#goto_manual_alt_ss').keyup(function (e) {
        if (this.selectionStart === this.selectionEnd && this.value.length === 2) {
            $('#goto_manual_az_ddd').focus();
        }
    });

    $('#goto_manual_az_ddd').keyup(function (e) {
        if (this.selectionStart === this.selectionEnd && this.value.length === 3) {
            $('#goto_manual_az_mm').focus();
        }
    });

    $('#goto_manual_az_mm').keyup(function (e) {
        if (this.selectionStart === this.selectionEnd && this.value.length === 2) {
            $('#goto_manual_az_ss').focus();
        }
    });

    $('#firmware_file_upload').click(function () {
        var formData = new FormData();
        var file = $('#firmware_file')[0].files[0];
        if (file) {
            formData.append('file', file);
            $.ajax({
                url: '/firmware_update',
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                success: function (data) {
                    $('#firmware_upload_div').html('Success. Rebooting, please wait 1min...');
                    setTimeout(function () {
                        location.reload(true);
                    }, 50000);
                },
                error: function (jq) {
                    $('#firmware_upload_div').html('Error:' + jq.responseText);
                }
            });
        }
    });

    var isMobile = function () {
        if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
            return true;
        }
        return false;
    };

    $('input').focus(function () {
        if (isMobile()) {
            $('#status_footer').hide();
        }
    }).blur(function () {
        if (isMobile()) {
            $('#status_footer').show();
        }
    });

    $.ajax({
        url: '/version',
        method: 'GET',
        success: function (d) {
            $('#firmware_version').html('Current&nbsp;Version:&nbsp;' + d.version);
        },
        error: function (jq, errorstatus, errortxt) {
            $('#firmware_version').html('Current&nbsp;Version:&nbsp;Unknown');
        }
    });

    $.ajax({
        url: '/set_time',
        method: 'PUT',
        data: {time: (new Date()).toISOString()},
        success: function (d) {
            console.log('Time synced:' + d);
        },
        error: function (jq, errorstatus, errortxt) {
            console.error(errorstatus, errortxt, jq.responseText);
        }
    });
});
