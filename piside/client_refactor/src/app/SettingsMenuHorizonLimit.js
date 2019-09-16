/*global $ */
import HorizonGraph from './horizonLimit/HorizonGraph';
import template from './templates/SettingsMenuHorizonLimit.html';


function handleFetchError(response) {
    if (!response.ok) {
        console.error(response.statusText);
        throw Error(response.statusText);
    }
    return response;
}


const savePoints = _.throttle(function (points) {
    return fetch('/api/settings_horizon_limit', {
        method: 'put',
        body: JSON.stringify({points: points}),
        headers: {
            'Content-Type': 'application/json'
        }
    }).then(handleFetchError);
}, 500);


class SettingsMenuHorizonLimit {
    constructor(App, parentDiv) {
        this._selfDiv = $(template);
        this._lastAltAz = {alt: 0, az: 0};
        parentDiv.append(this._selfDiv);

        this._graph = new HorizonGraph($('#horizonLimitgraphCanvas', this._selfDiv)[0]);

        const addPointButton = $('#horizonLimitaddButton', this._selfDiv);
        addPointButton.click(() => {
            const alt = parseFloat(document.getElementById('horizonLimitaddalt').value);
            const az = parseFloat(document.getElementById('horizonLimitaddaz').value);
            const p = {alt: alt, az: az};
            const pcopy = this._graph.points;
            pcopy.push(p);
            this._graph.points = pcopy;
        });

        const doStatus = () => {
            $.ajax({
                url: '/api/status',
                method: 'GET',
                success: (status) => {
                    if (status.hasOwnProperty('alt') && status.alt) {
                        this._lastAltAz = {alt: status.alt, az: status.az};
                    }
                },
                error: (jq, errorstatus, errortxt) => {
                    console.error(errorstatus, errortxt, jq.responseText);
                },
                complete: () => {
                    setTimeout(() => {
                        doStatus();
                    }, 1000);
                }
            });
        };

        setTimeout(() => {
            doStatus();
        }, 0);

        const addCurrentPositionPointButton = $('#horizonLimitaddCurrentPositionButton', this._selfDiv);
        addCurrentPositionPointButton.click(() => {
            const p = _.clone(this._lastAltAz);
            const pcopy = this._graph.points;
            pcopy.push(p);
            this._graph.points = pcopy;
        });

        const select = $('#horizonLimitexistingPoints', this._selfDiv);
        this._graph.on('pointsChanged', () => {
            console.log('in pointsChanged event on index');
            select.empty();
            const points = this._graph.points;
            for (let i = 0; i < points.length; i++) {
                const point = points[i];
                select.append('<option value="' + i + '">' + 'Alt:' + point.alt.toFixed(1) + ', Az:' + point.az.toFixed(1) + '</option>')
            }
            // Save points
            savePoints(points);
            select.change();
        });
        const modAlt = $('#horizonLimitmodAlt', this._selfDiv);
        const modAz = $('#horizonLimitmodAz', this._selfDiv);
        select.change(() => {
            const index = parseFloat(select.val());
            const points = this._graph.points;
            const point = this._graph.points[index];
            modAlt.val(point.alt.toFixed(1));
            modAz.val(point.az.toFixed(1));
        });
        $('#horizonLimitmoveButton', this._selfDiv).click(() => {
            const alt = parseFloat(modAlt.val());
            const az = parseFloat(modAz.val());
            const index = parseFloat(select.val());
            const points = this._graph.points;
            points[index].alt = alt;
            points[index].az = az;
            this._graph.points = points;
        });
        $('#horizonLimitdeleteButton', this._selfDiv).click(() => {
            const index = parseFloat(select.val());
            const points = this._graph.points;
            if (points.length === 1) {
                points[0].alt = 0;
                points[0].az = 0;
            } else {
                points.splice(index, 1);
            }
            this._graph.points = points;
        });

        $.ajax({
            url: '/api/settings',
            method: 'GET',
            success: (data) => {
                if (data.hasOwnProperty('horizon_limit_points')) {
                    this._graph.points = data.horizon_limit_points;
                }
            }
        })
    }

    show() {
        this._selfDiv.show();
    }

    hide() {
        this._selfDiv.hide();
    }
}

export default SettingsMenuHorizonLimit;
