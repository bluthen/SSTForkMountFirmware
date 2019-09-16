import CircleGraph from './CircleGraph';
//import HorizontalGraph from './horizonLimit/CircleGraph';

/** TODO: Events
 * pointsChanged
 */
class HorizonGraph {
    constructor(canvas) {
        this._eventHolder = {};
        this._points = [];
        const self = this;
        // check to see if we are running in a browser with touch support
        self._stage = new createjs.Stage(canvas);

        // enable touch interactions if supported on the current device:
        createjs.Touch.enable(self._stage);

        // enabled mouse over / out events
        self._stage.enableMouseOver(10);
        // keep tracking the mouse even when it leaves the canvas
        self._stage.mouseMoveOutside = true;

        const circleGraphContainer = new createjs.Container();
        self._stage.addChild(circleGraphContainer);

        // var horizontalGraphContainer = new createjs.Container();
        // horizontalGraphContainer.x = 0;
        // horizontalGraphContainer.y = 600;
        // self._stage.addChild(horizontalGraphContainer);

        self._circleGraph = new CircleGraph(this, circleGraphContainer, true, true);
        self._circleGraph.points = [{alt: 0, az: 0}];
        // self._horizontalGraph = new HorizontalGraph(this, horizontalGraphContainer);

        createjs.Ticker.addEventListener("tick", function (event) {
            _tick(self, event);
        });
    }

    on(eventName, callback) {
        if (!callback) {
            return;
        }
        if (!this._eventHolder.hasOwnProperty(eventName)) {
            this._eventHolder[eventName] = [];
        }
        this._eventHolder[eventName].push(callback)
    }

    off(eventName, callback) {
        if (!this._eventHolder.hasOwnProperty(eventName)) {
            return;
        }
        if(!callback) {
            this._eventHolder[eventName] = [];
            return;
        }
        for (let i = 0; i < this._eventHolder[eventName]; i++) {
            if(this._eventHolder[eventName][i] === callback) {
                this._eventHolder[eventName].splice(i, 1);
                break;
            }
        }
    }

    trigger(eventName, eventObj) {
        if (!this._eventHolder.hasOwnProperty(eventName)) {
            return;
        }
        for (let i = 0; i < this._eventHolder[eventName].length; i++) {
            this._eventHolder[eventName][i](eventObj);
        }
    }

    get points() {
        const points = [];
        const pts = this._circleGraph._points;
        for(let i = 0; i < pts.length; i++) {
            points.push({alt: pts[i].alt, az: pts[i].az});
        }
        return points;
    }

    set points(value) {
        setPoints(this, value);
    }
}

function setPoints(self, points) {
    console.log('HorizonGraph.setPoints');
    if (points.length === 0) {
    //    throw new Error('No points in array.')
    }
    for(let i = 0; i < points.length; i++) {
        const point = points[i];
        if (point.alt > 90.0 || point.alt < 0 ||point.az >= 360.0 || point.az < 0) {
            throw new Error('Invalid points:', point);
        }
    }
    points = points.sort(function(a, b) {
        return a.az - b.az;
    });
    self._points = points;
    self._circleGraph.points = points;
    // self._horizontalGraph.points = points;
}

function _tick(self, event) {
    // this set makes it so the stage only re-renders when an event handler indicates a change has happened.
    if (self.update) {
        self.update = false; // only update once
        self._stage.update(event);
    }
}

window.HorizonGraph = HorizonGraph;
export default HorizonGraph;