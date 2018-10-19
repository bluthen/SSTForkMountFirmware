const color = "#FF0000";
const RADIUS = 7;

class Point {
    constructor(parent) {
        const self = this;
        this._parent = parent;
        const _floatingText = new createjs.Text('Alt,Az', '15px Arial', color);
        _floatingText.textBaseline = 'bottom';
        _floatingText.textAlign = 'left';
        const point = new createjs.Shape(new createjs.Graphics().beginFill(color).drawCircle(0, 0, RADIUS));
        point.scale = 1.0;
        point.cursor = 'pointer';
        // in this case that means it executes in the scope of the button.
        point.on("mousedown", function (evt) {
            this.parent.addChild(this);
            this.offset = {x: this.x - evt.stageX, y: this.y - evt.stageY};
        });

        // the pressmove event is dispatched when the mouse moves after a mousedown on the target until the mouse is released.
        point.on("pressmove", function (evt) {
            let newx = evt.stageX + this.offset.x;
            let newy = evt.stageY + this.offset.y;
            // indicate that the stage should be updated on the next tick:
            const p = self._parent._inverseConvertPoint(newx, newy);
            if (p.alt < 0) {
                p.alt = 0.0;
                console.log(p.alt, p.az);
                const p2 = self._parent._convertPoint(p.alt, p.az);
                newx = p2.x;
                newy = p2.y;
            }
            _floatingText.text = p.alt.toFixed(1) + ',' + p.az.toFixed(1);
            _floatingText.x = this.x + 2 * RADIUS;
            _floatingText.y = this.y - 2 * RADIUS;
            this.parent.addChild(_floatingText);
            this.x = newx;
            this.y = newy;
            this.point.alt = p.alt;
            this.point.az = p.az;
            self._parent.update = true;
        });

        point.on("rollover", function (evt) {
            this.scale = 1.3;
            self._parent.update = true;
        });
        point.on("rollout", function (evt) {
            this.scale = 1.0;
            self._parent.update = true;
            self._parent._parent.trigger('pointsChanged');
            this.parent.removeChild(_floatingText);
        });

        return point;
    }
}

export default Point;