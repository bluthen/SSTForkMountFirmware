"use strict";
import Point from './Point';

const largeRadius = 260;
const color = "#FF0000";
const LINE_STEP = 1;

class CircleGraph {
    constructor(parent, circleGraphContainer) {
        this._points = [];
        this._parent=parent;
        this._plotArea = _makeBackground.apply(this, [circleGraphContainer]);
    }
    set points(value) {
        setPoints(this, value);
    }
    set update(value) {
        redraw(this);
        this._parent.update = value;
    }
    _inverseConvertPoint(x,y) {
        const nx= x - largeRadius;
        const ny = -1*(y-largeRadius);
        const caz = Math.atan2(ny, nx) * 180.0/Math.PI;

        const r = (x - largeRadius)/Math.cos(caz * Math.PI/180);
        const alt = ((r/largeRadius)-1)*(-90.0);
        let az = -1 * (caz - 90.0);
        if(az < 0) {
            az = 360+az;
        }

        return {alt: alt, az: az};
    }

    _convertPoint(alt, az) {
        const r = (1 - alt / 90.0) * largeRadius;
        const caz = -az + 90.0;
        //console.log(caz);
        const x = r * Math.cos(caz * Math.PI / 180) + largeRadius;
        const y = largeRadius - r * Math.sin(caz * Math.PI / 180);
        return {x: x, y: y};
    }

}


function _sortPoints(self) {
    self._points = self._points.sort(function(a, b) {
        return a.az - b.az;
    });
}



function _makeBackground(circleGraphContainer) {
    //Outline horizon circle chart
    const circleGraph = new createjs.Shape();
    circleGraph.graphics.beginStroke(color).setStrokeStyle(2)
        .moveTo(300 - largeRadius - 5, 300).lineTo(300 + largeRadius + 5, 300)
        .moveTo(300, 300 - largeRadius - 5).lineTo(300, 300 + largeRadius + 5)
        .moveTo(300, 300);
    for (let i = 0; i < 7; i++) {
        circleGraph.graphics
            .drawCircle(300, 300, i * (largeRadius / 6));
        const pt = this._convertPoint(90 - i * 15, 315);
        const label = new createjs.Text('' + 90 - i * 15, '15px Arial', color);
        label.x = pt.x + 300 - largeRadius;
        label.y = pt.y + 300 - largeRadius;
        label.textAlign = 'right';
        label.textBaseline = 'bottom';
        circleGraphContainer.addChild(label);
    }
    circleGraph.graphics.endStroke();
    circleGraphContainer.addChild(circleGraph);
    const cgLabel0 = new createjs.Text('0', '20px Arial', color);
    const cgLabel90 = new createjs.Text('90', '20px Arial', color);
    const cgLabel180 = new createjs.Text('180', '20px Arial', color);
    const cgLabel270 = new createjs.Text('270', '20px Arial', color);
    cgLabel0.x = 300;
    cgLabel0.y = 0;
    cgLabel0.textAlign = "center";
    cgLabel90.x = 600;
    cgLabel90.y = 300;
    cgLabel90.textAlign = "right";
    cgLabel90.textBaseline = 'middle';
    cgLabel180.x = 300;
    cgLabel180.y = 600;
    cgLabel180.textAlign = "center";
    cgLabel180.textBaseline = 'bottom';
    cgLabel270.x = 0;
    cgLabel270.y = 300;
    cgLabel270.textAlign = "left";
    cgLabel270.textBaseline = 'middle';
    circleGraphContainer.addChild(cgLabel0);
    circleGraphContainer.addChild(cgLabel90);
    circleGraphContainer.addChild(cgLabel180);
    circleGraphContainer.addChild(cgLabel270);

    const circleGraphPlotAreaContainer = new createjs.Container();
    circleGraphPlotAreaContainer.x = 300 - largeRadius;
    circleGraphPlotAreaContainer.y = 300 - largeRadius;
    circleGraphContainer.addChild(circleGraphPlotAreaContainer);
    return circleGraphPlotAreaContainer;
}




//window.cptest = _convertPoint;
//window.icptest = _inverseConvertPoint;

function setPoints(self, points) {
    for(let i = 0; i < self._points.length; i++) {
        self._plotArea.removeChild(self._points[i].drawPoint);
    }
    self._points = points;
    for(let i = 0; i < points.length; i++) {
        const point = points[i];
        const drawPoint = new Point(self);
        point.drawPoint = drawPoint;
        drawPoint.point = point;
        console.log(point);
        const p = self._convertPoint(point.alt, point.az);
        drawPoint.x = p.x;
        drawPoint.y = p.y;
        self._plotArea.addChild(drawPoint);
    }
    _sortPoints(self);
    self._parent.trigger('pointsChanged');
    self.update = true;
}

function redraw(self) {
    let container;
    _sortPoints(self);
    if(!self._plotFillContainer) {
        container = new createjs.Container();
        container.x = self._plotArea.x;
        container.y = self._plotArea.y;
        self._parent._stage.addChildAt(container, 0);
        self._plotFillContainer = container;
    } else {
        container = self._plotFillContainer;
    }


    const newPlot = new createjs.Shape();
    newPlot.graphics.beginFill('#FF7F7F').setStrokeStyle(1);

    newPlot.graphics.drawCircle(largeRadius, largeRadius, largeRadius).endFill();
    newPlot.graphics.beginFill('#FFFFFF');


    for (let i = 0; i < self._points.length; i++) {
        let point2, p2;
        const point1 = self._points[i];
        let paz = point1.az;
        if (i+1 < self._points.length) {
            point2 = self._points[i+1];
        } else {
            point2 = self._points[0];
        }
        if (point2.az < paz || self._points.length === 1) {
            paz -= 360;
        }
        const p = self._convertPoint(point1.alt, point1.az);
        if (i === 0) {
            newPlot.graphics.moveTo(p.x, p.y);
        }
        //console.log(point1, point2);
        const m = (point2.alt - point1.alt)/(point2.az - paz);
        for(let az = paz; az < point2.az; az += LINE_STEP) {
            const alt = m*(az-paz) + point1.alt;
            p2 = self._convertPoint(alt, az);
            //console.log(m, alt, az);
            newPlot.graphics.lineTo(p2.x, p2.y)
        }
        p2 = self._convertPoint(point2.alt, point2.az);
        //newPlot.graphics.moveTo(p.x, p.y);
        newPlot.graphics.lineTo(p2.x, p2.y);
    }
    newPlot.graphics.endStroke();
    //newPlot.alpha=0.5;
    if(self._plotFill) {
        container.removeChild(self._plotFill);
    }
    self._plotFill = newPlot;
    container.addChild(self._plotFill);
}

export default CircleGraph;