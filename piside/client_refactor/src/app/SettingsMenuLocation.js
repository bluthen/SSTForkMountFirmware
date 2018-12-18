/*global $, _ */

import Formating from './Formating'

import template from './templates/SettingsMenuLocation.html'

let searchLocationCounter = 0;

const DEFAULT_ELEVATION = 405;

const searchLocation = _.throttle(function () {
    const search = $('#location_search_txt', this._selfDiv).val();
    if (!search.trim()) {
        return;
    }
    searchLocationCounter++;
    let sc = searchLocationCounter;
    $('#location_search_info', this._selfDiv).empty();
    const action = '<button type="button" class="btn btn-success"><i class="fas fa-globe" title="set"></i>Set</button>';
    $('#location_search_spinner', this._selfDiv).show();
    $('#location_search_results', this._selfDiv).hide();
    $.ajax({
        url: '/search_location',
        method: 'GET',
        data: {'search': search},
        success: (d) => {

            if (sc !== searchLocationCounter) {
                return;
            }
            const setclicked = (lat, lon, elevation, name) => {
                return (e) => {
                    this.setLocation(lat, lon, elevation, name);
                    e.preventDefault();
                }
            };
            const tbody = $('#location_search_results tbody', this._selfDiv);
            tbody.empty();
            for (let i = 0; i < d.cities.length; i++) {
                const tr = $('<tr><td>' + d.cities[i][2] + ', ' + d.cities[i][4] + ' ' + d.cities[i][1] + '</td><td>' + Formating.lat(d.cities[i][9]) + ' ' + Formating.long(d.cities[i][10]) + '</td><td>'+d.cities[i][12]+'m</td><td>' + action + '</td>');
                tbody.append(tr);
                $('button', tr).on('click', setclicked(parseFloat(d.cities[i][9]), parseFloat(d.cities[i][10]), parseFloat(d.cities[i][12]), d.cities[i][2] + ', ' + d.cities[i][4]));
            }

            console.log(d);
            if (d.cities.length >= 20) {
                $('#location_search_info', this._selfDiv).text('Too many results. Results were cut.');
            }
            $('#location_search_spinner', this._selfDiv).hide();
            $('#location_search_results', this._selfDiv).show();
        }
    })
}, 500, {leading: false, trailing: true});

const setLocationManualClicked = function () {
    let lat_deg, long_deg;
    let lat = $('#manual_lat', this._selfDiv).val();
    let long = $('#manual_long', this._selfDiv).val();
    const elevation = parseFloat($('#manual_elevation', this._selfDiv).val().trim());

    const name = $('#manual_name', this._selfDiv).val().trim();

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
        const match = lat.match(/^([NS])(\d+)[° ](\d+)' ?(\d*.?\d+)?/);
        if (match) {
            lat_deg = parseInt(match[2], 10);
            lat_deg += parseFloat(match[3]) / 60.0;
            lat_deg += parseFloat(match[4]) / (60.0 * 60.0);
            if (match[1] === 'S') {
                lat_deg = -lat_deg;
            }
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
        const match = long.match(/^([WE])(\d+)[° ](\d+)' ?(\d*.?\d+)?/);
        if (match) {
            long_deg = parseInt(match[2], 10);
            long_deg += parseFloat(match[3]) / 60.0;
            long_deg += parseFloat(match[4]) / (60.0 * 60.0);
            if (match[1] === 'W') {
                long_deg = -long_deg;
            }
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
    this.setLocation(lat_deg, long_deg, elevation, name);
};


class SettingsMenuLocation {
    constructor(parentDiv, startingSettings) {
        this._selfDiv = $(template);
        parentDiv.append(this._selfDiv);

        if(startingSettings.time_autosync !== false) {
            this.syncTimeWithDevice(new Date().toISOString());
        }

        $('#location_manual_unset', this._selfDiv).click(() => {
            this.unsetLocation();
        });
        $('#location_manual_set', this._selfDiv).click(setLocationManualClicked.bind(this));
        $('#location_search_txt', this._selfDiv).on('input', searchLocation.bind(this));

        $('#time_datetimepicker1', this._selfDiv).datetimepicker({
            icons:
                {
                    time: 'far fa-clock',
                    date: 'far fa-calendar',
                    up: 'fas fa-arrow-up',
                    down: 'fas fa-arrow-down',
                    previous: 'fas fa-chevron-left',
                    next: 'fas fa-chevron-right',
                    today: 'far fa-calendar-check',
                    clear: 'fas fa-trash',
                    close: 'fas fa-times'
                }
        });


        $('#time_sync', this._selfDiv).click(() => {
            this.syncTimeWithDevice((new Date()).toISOString());
        });

        $('#time_sync_manual', this._selfDiv).click(() => {
            const time = $('#time_datetimepicker1').datetimepicker('date').toISOString();
            if (time) {
                this.syncTimeWithDevice(time);
            }
        });

        $('#time_autosync', this._selfDiv).change(function () {
            $.ajax({
                url: '/settings',
                method: 'PUT',
                data: {settings: JSON.stringify({'time_autosync': $('#time_autosync').is(':checked')})}
            })
        });
    }

    syncTimeWithDevice(isotimestr) {
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
    }

    unsetLocation() {
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
    }

    setLocation(lat, long, elevation, name) {
        if (isNaN(elevation)) {
            elevation = DEFAULT_ELEVATION;
        }
        //TODO: Confirm Dialog?
        $.ajax({
            url: '/set_location',
            method: 'PUT',
            data: {location: JSON.stringify({lat: lat, long: long, elevation: elevation, name: name})},
            success: function (d) {
                // Footer
                const location = $('#location');
                location.empty();
                if (name) {
                    location.text(name);
                }
            },
            error: function (jq, errorstatus, errortxt) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    }

    show() {
        this._selfDiv.show();
    }

    hide() {
        this._selfDiv.hide();
    }

}

export default SettingsMenuLocation;
