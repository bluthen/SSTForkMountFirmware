/* global $ */
import template from './templates/DirectionControls.html'

const sendPressed = function (direction, speed) {
    console.log('sendPressed: ' + direction + ', ' + speed);
    this._app.socket.emit('manual_control', {direction: direction, speed: speed})
};

const sendUnpressed = function (direction) {
    console.log('sendUnpressed: ' + direction);
    this._app.socket.emit('manual_control', {direction: direction, speed: null})
};


class DirectionControls {
    constructor(App, parentDiv) {
        parentDiv.append($(template));
        this._app = App;
        this._parentDiv = parentDiv;
        const up = $('.direction-controls-up', parentDiv);
        const upleft = $('.direction-controls-up-left', parentDiv);
        const upright = $('.direction-controls-up-right', parentDiv);
        const down = $('.direction-controls-down', parentDiv);
        const downleft = $('.direction-controls-down-left', parentDiv);
        const downright = $('.direction-controls-down-right', parentDiv);
        const left = $('.direction-controls-left', parentDiv);
        const right = $('.direction-controls-right', parentDiv);

        const all = up.add(upleft).add(upright).add(down).add(downleft).add(downright).add(left).add(right);

        this._intervals = {};

        all.click(function (e) {
            e.preventDefault();
            return false;
        });

        all.on('mousedown touchstart', (e) => {
            const id = $(e.currentTarget).attr('class');
            console.log('mousedown', id);
            $(e.currentTarget).addClass('pressed');
            const directions = id.split('direction-controls-')[1].split('-');
            const speed = this.getSelectedSpeed();
            for (let i = 0; i < directions.length; i++) {
                const direction = directions[i];
                this.pressed(direction, speed);
            }
            e.preventDefault();
        });
        all.on('mouseleave mouseup touchend touchcancel', (e) => {
            $(e.currentTarget).removeClass('pressed');
            const id = $(e.currentTarget).attr('class');
            const directions = id.split('direction-controls-')[1].split('-');
            for (let i = 0; i < directions.length; i++) {
                const direction = directions[i];
                this.unpressed(direction);
            }
            e.preventDefault();
        });
    }

    pressed(direction, speed) {
        const oppositeMap = {'left': 'right', 'right': 'left', 'up': 'down', 'down': 'up'};
        //If we are already going opposite direction then ignore.
        if (this._intervals.hasOwnProperty(oppositeMap[direction])) {
            return;
        }
        console.log('Pressing: ' + direction);
        if (this._intervals.hasOwnProperty(direction)) {
            clearTimeout(this._intervals[direction]);
        }
        this._intervals[direction] = setInterval(() => {
            sendPressed.apply(this, [direction, speed]);
        }, 100);
        sendPressed.apply(this, [direction, speed]);
    }

    unpressed(direction) {
        console.log('let go: ' + direction);
        if (this._intervals.hasOwnProperty(direction)) {
            clearInterval(this._intervals[direction]);
            delete this._intervals[direction];
        }
        sendUnpressed.apply(this, [direction]);
    }

    getSelectedSpeed() {
        let speed;
        if ($('.direction-controls-speed-fastest', this._parentDiv).is(':checked')) {
            speed = 'fastest';
        }
        if ($('.direction-controls-speed-faster', this._parentDiv).is(':checked')) {
            speed = 'faster';
        }
        if ($('.direction-controls-speed-medium', this._parentDiv).is(':checked')) {
            speed = 'medium';
        }
        if ($('.direction-controls-speed-slower', this._parentDiv).is(':checked')) {
            speed = 'slower';
        }
        if ($('.direction-controls-speed-slowest', this._parentDiv).is(':checked')) {
            speed = 'slowest';
        }
        return speed;
    }

}

export default DirectionControls;