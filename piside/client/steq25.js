/*globals $ */
$(document).ready(function() {
    'use strict';

    var absoluteURL = function(relativeURL) {
        return new URL(relativeURL, window.location.href).href;
    };

    const socket = io(absoluteURL('/'));

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
    //init();
    bind_direction_controls();
    navigator.geolocation.getCurrentPosition(function(position) {
        var txt = 'Lat:' +position.coords.latitude+', Long:'+ position.coords.latitude+', Alt: '+position.coords.altitude;
        $('#location').text(txt);
    }, function(err) {
        $('#location').text(''+err.message+','+err.code);

    }, {enableHighAccuracy: true, timeout: 5000000})
});