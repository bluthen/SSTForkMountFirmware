/*globals $ */
$(document).ready(function() {
    'use strict';

    var absoluteURL = function(relativeURL) {
        return new URL(relativeURL, window.location.href).href;
    };

    console.log(absoluteURL('/'));
    window.socket = io(absoluteURL('/'));
    socket.on('connect', function(msg) {
        console.log('socket io connect.');
    });
    socket.on('status', function(msg) {
        console.log(msg);
        $('#ra_stat').text(''+msg.rs+'/'+msg.rp);
        $('#dec_stat').text(''+msg.ds+'/'+msg.dp);
    });
    socket.on('controls_response', function(msg) {
        console.log(msg);
    });


    var bind_direction_controls = function() {
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
        var sendPressed = function(direction, speed) {
            console.log('sendPressed: '+direction+', '+speed);
            socket.emit('manual_control', {direction: direction, speed: speed})
        };
        var sendUnpressed = function(direction) {
            console.log('sendUnpressed: '+direction);
            socket.emit('manual_control', {direction: direction, speed: null})
        };
        var pressed = function(direction, speed) {
            //If we are already going opposite direction then ignore.
            if(intervals.hasOwnProperty(oppositeMap[direction])) {
                return;
            }
            console.log('Pressing: '+direction);
            if(intervals.hasOwnProperty(direction)) {
                clearTimeout(intervals[direction]);
            }
            intervals[direction] = setInterval(function() {
                sendPressed(direction, speed);
            }, 250);
            sendPressed(direction, speed);
        };

        var unpressed = function(direction, speed) {
            console.log('let go: ' + direction);
            if (intervals.hasOwnProperty(direction)) {
                clearInterval(intervals[direction]);
                delete intervals[direction];
            }
            sendUnpressed(direction);
        };


        all.on('mousedown touchstart', function(e) {
            var direction, i;
            var id = $(e.currentTarget).attr('id');
            var directions = id.split('direction-controls-')[1].split('-');
            var speed = $('#direction-controls-speed-fast').is(':checked');
            if (speed) {
                speed = 'fast';
            } else {
                speed = 'slow';
            }
            for(i = 0; i < directions.length; i++) {
                var direction = directions[i];
                pressed(direction, speed);
            }
            e.preventDefault();
        });
        all.on('mouseup touchstop', function(e) {
            var direction, i;
            var id = $(e.currentTarget).attr('id');
            var directions = id.split('direction-controls-')[1].split('-');
            for(i = 0; i < directions.length; i++) {
                var direction = directions[i];
                unpressed(direction);
            }
            e.preventDefault();
        })

    };

    function update_settings() {
        $.ajax({url:'/settings', dataType: 'json', success: function(data) {
            $('#settings_ra_track_rate').val(data.ra_track_rate);
            $('#settings_ra_direction').val(data.micro.ra_direction);
            $('#settings_dec_direction').val(data.micro.dec_direction);
            $('#settings_ra_guide_rate').val(data.micro.ra_guide_rate);
            $('#settings_ra_slew_fast').val(data.ra_slew_fast);
            $('#settings_ra_slew_slow').val(data.ra_slew_slow);
            $('#settings_dec_guide_rate').val(data.micro.dec_guide_rate);
            $('#settings_dec_slew_fast').val(data.dec_slew_fast);
            $('#settings_dec_slew_slow').val(data.dec_slew_slow);
        }});
    }

    update_settings();
    //init();
    bind_direction_controls();
});