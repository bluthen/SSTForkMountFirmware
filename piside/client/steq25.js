/*globals $ */
$(document).ready(function () {
    'use strict';

    var absoluteURL = function (relativeURL) {
        return new URL(relativeURL, window.location.href).href;
    };

    console.log(absoluteURL('/'));
    window.socket = io(absoluteURL('/'));
    socket.on('connect', function (msg) {
        console.log('socket io connect.');
    });
    socket.on('status', function (msg) {
        console.log(msg);
        $('#ra_stat').text('' + msg.rs + '/' + msg.rp);
        $('#dec_stat').text('' + msg.ds + '/' + msg.dp);
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

        var unpressed = function (direction, speed) {
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
                var direction = directions[i];
                pressed(direction, speed);
            }
            e.preventDefault();
        });
        all.on('mouseup touchstop', function (e) {
            var direction, i;
            var id = $(e.currentTarget).attr('id');
            var directions = id.split('direction-controls-')[1].split('-');
            for (i = 0; i < directions.length; i++) {
                var direction = directions[i];
                unpressed(direction);
            }
            e.preventDefault();
        })

    };

    function update_settings() {
        $.ajax({
            url: '/settings', dataType: 'json', success: function (data) {
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
            }
        });
    }

    update_settings();
    //init();
    bind_direction_controls();

    var ra_format = function(ra) {
        ra = parseFloat(ra);
        var remain = ra - parseInt(ra);
        var min = parseInt(remain*60);
        var sec = (remain - (min/60.0))*60*60;
        return parseInt(ra, 10)+'h'+min+'m'+sec.toFixed(1)+'s'
    };

    var dec_format = function(dec) {
        dec = parseFloat(dec);
        var remain = dec - parseInt(dec);
        var arcmin = parseInt(remain*60);
        var arcsec = (remain - (arcmin/60.0))*60*60;
        return parseInt(dec, 10)+'&deg;'+arcmin+'\''+arcsec.toFixed(1)+'"'
    };

    var search_object = _.throttle(function() {
        var search = $('#search_txt').val();
        $('#search_info').empty();
        var action='<a href="#">Sync</a>&nbsp; &nbsp;<a href="#">Goto</a>'
        $.ajax({
            url: '/search_object',
            method: 'GET',
            data: {'search': search},
            success: function(d) {
                var i = 0;
                var tbody = $('#search_results tbody');
                tbody.empty();
                for(i = 0; i < d.dso.length; i++) {
                    tbody.append('<tr><td>'+d.dso[i][20]+'</td><td>'+ra_format(d.dso[i][0])+'/'+dec_format(d.dso[i][1])+'</td><td></td></td><td>'+action+'</td>')
                }
                for(i = 0; i < d.stars.length; i++) {
                    tbody.append('<tr><td>'+d.stars[i][6]+', '+d.stars[i][5]+'</td><td>'+ra_format(d.stars[i][7])+'/'+dec_format(d.stars[i][8])+'</td><td></td></td><td>'+action+'</td>')
                }

                console.log(d);

                if(d.dso.length >= 10 || d.stars.length >= 10) {
                    $('#search_info').text('Too many results. Results were cut.')
                }
            }
        })
    }, 500);

    $('#search_txt').on('input', search_object);

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
            error: function (jqXHR, textStatus, errorThrown) {
                $('#settings_save_status').text(textStatus).show().fadeOut(1000);
            }
        });
    });
});