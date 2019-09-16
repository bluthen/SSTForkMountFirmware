/*globals createjs*/
"use strict";
var color = "#FF0000";


//Horizontal Graph
var HorizontalGraph = Classy({
    initialize: initialize,
});

Object.defineProperty(HorizontalGraph.prototype, 'points', {
    set: function(value) {
        setPoints(this, value);
    }
});


function _convertPoint(alt, az) {
    var x = 550 * az / 360.0;
    var y = 350 - 350 * (alt / 90.0);
    return {x: x, y: y};
}

function _inverseConvertPoint(x, y) {
    var az = x * 360 / 550;
    var alt = ((y - 350) / (-350)) * 90.0;
    return {alt: alt, az: az};
}

function _makeBackground(horizontalGraphContainer) {
    var i;
    var label;
    var horizontalGraph = new createjs.Shape();

    horizontalGraph.graphics.beginStroke(color).setStrokeStyle(2)
        .moveTo(50, 0).lineTo(50, 400)
        .moveTo(0, 350).lineTo(600, 350).endStroke();
    // Ticks
    for (i = 1; i < 9; i++) {
        horizontalGraph.graphics.beginStroke(color).setStrokeStyle(2)
            .moveTo(50 + i * (550 / 8), 340).lineTo(50 + i * (550 / 8), 360).endStroke();
        horizontalGraph.graphics.beginStroke(color).setStrokeStyle(1)
            .moveTo(50 + i * (550 / 8), 350).lineTo(50 + i * (550 / 8), 0).endStroke();
        label = new createjs.Text('' + i * 45, '20px Arial', color);
        label.x = 50 + i * (550 / 8);
        label.y = 360;
        label.textAlign = 'center';
        horizontalGraphContainer.addChild(label);
    }
    for (i = 1; i < 7; i++) {
        horizontalGraph.graphics.beginStroke(color).setStrokeStyle(2)
            .moveTo(40, 350 - i * (350 / 6)).lineTo(60, 350 - i * (350 / 6)).endStroke();
        horizontalGraph.graphics.beginStroke(color).setStrokeStyle(1)
            .moveTo(50, 350 - i * (350 / 6)).lineTo(600, 350 - i * (350 / 6)).endStroke();
        label = new createjs.Text('' + i * 15, '20px Arial', color);
        label.x = 40;
        label.y = 350 - i * (350 / 6);
        label.textAlign = 'right';
        label.textBaseline = 'middle';
        horizontalGraphContainer.addChild(label);
    }
    horizontalGraphContainer.addChild(horizontalGraph);
    var altLabel = new createjs.Text('Alt', '20px Arial', color);
    var azLabel = new createjs.Text('Az', '20px Arial', color);
    altLabel.rotation = -90;
    altLabel.x = 0;
    altLabel.y = 175;
    horizontalGraphContainer.addChild(altLabel);
    azLabel.y = 400;
    azLabel.x = 300;
    azLabel.textAlign = 'center';
    azLabel.textBaseline = 'bottom';
    horizontalGraphContainer.addChild(azLabel);
    var horizontalGraphPlotAreaContainer = new createjs.Container();
    horizontalGraphPlotAreaContainer.x = 50;
    horizontalGraphPlotAreaContainer.y = 0;
    horizontalGraphContainer.addChild(horizontalGraphPlotAreaContainer);

    return horizontalGraphPlotAreaContainer;
}

function setPoints(self, points) {

}

function initialize(parent, horizontalGraphContainer) {
    var self = this;
    self._parent = parent;
    self._plotArea = _makeBackground(horizontalGraphContainer);

    //var htpoint = newPoint();
    //var pp = _horizontalGraphConvertPoint(60, 360);
    //htpoint.x=pp.x;
    //htpoint.y=pp.y;
    //horizontalGraphPlotAreaContainer.addChild(htpoint);
}


module.exports = HorizontalGraph;