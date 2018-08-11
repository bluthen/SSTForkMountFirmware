/* global $ */

import Formating from './Formating';

import template from './templates/SlewingObjectSearch.html'

let search_object_counter = 0;
const searchObject = _.debounce(function () {
    const search = $('#search_txt', this._selfDiv).val();
    if (search.trim() === '') {
        return;
    }
    search_object_counter++;
    let sc = search_object_counter;
    $('#search_info', this._selfDiv).empty();
    // TODO: Goto Action should only be there if we've synced once.
    const sync_action = '<button type="button" class="sync btn btn-warning"><i class="fas fa-sync" title="sync"></i>Sync</button>';
    const slew_action = '<button type="button" class="slewto btn btn-success"><i class="far fa-play-circle" title="slew"></i>Slew</button>';
    $('#search_spinner', this._selfDiv).show();
    $('#search_results', this._selfDiv).hide();
    $.ajax({
        url: '/search_object',
        method: 'GET',
        data: {'search': search},
        success: (d) => {
            if (sc !== search_object_counter) {
                return;
            }
            const tbody = $('#search_results tbody', this._selfDiv);
            const syncclick = (ra, dec) => {
                return (e) => {
                    this._slewing.sync(ra, dec);
                    e.preventDefault();
                };
            };

            const slewtoclick = (ra, dec) => {
                return (e) => {
                    this._slewing.slewto(ra, dec);
                    e.preventDefault();
                };
            };
            tbody.empty();
            for (let i = 0; i < d.planets.length; i++) {
                const tr = $('<tr>' +
                    '<th scope="row">' + d.planets[i][0] + '</th>' +
                    '<td>' + slew_action + '</td>' +
                    '<td>' + sync_action + '</td>' +
                    '<td>' + Formating.ra(d.planets[i][1]) + '/ ' + Formating.dec(d.planets[i][2]) + '</td>' +
                    '<td>' + Formating.dec(d.planets[i][3]) + '/ ' + Formating.dec(d.planets[i][4]) + '</td>' +
                    '<td></td>' +
                    '<td></td>' +
                    '</tr>');
                tbody.append(tr);
                $('button.sync', tr).on('click', syncclick((360.0 / 24.0) * parseFloat(d.planets[i][1]), parseFloat(d.planets[i][2])));
                $('button.slewto', tr).on('click',
                    slewtoclick((360.0 / 24.0) * parseFloat(d.planets[i][1]), parseFloat(d.planets[i][2])));
            }
            for (let i = 0; i < d.dso.length; i++) {
                const tr = $('<tr>' +
                    '<th scope="row">' + d.dso[i][20] + '</th>' +
                    '<td>' + slew_action + '</td>' +
                    '<td>' + sync_action + '</td>' +
                    '<td>' + Formating.ra(d.dso[i][0]) + '/ ' + Formating.dec(d.dso[i][1]) + '</td>' +
                    '<td>' + Formating.dec(d.dso[i][21]) + '/ ' + Formating.dec(d.dso[i][22]) + '</td>' +
                    '<td>' + d.dso[i][4] + '</td>' +
                    '<td>' + d.dso[i][9] + '"x' + d.dso[i][10] + '"</td>' +
                    '</tr>');
                tbody.append(tr);
                $('button.sync', tr).on('click', syncclick((360.0 / 24.0) * parseFloat(d.dso[i][0]), parseFloat(d.dso[i][1])));
                $('button.slewto', tr).on('click',
                    slewtoclick((360.0 / 24.0) * parseFloat(d.dso[i][0]), parseFloat(d.dso[i][1])));
            }
            for (let i = 0; i < d.stars.length; i++) {
                const tr = $('<tr>' +
                    '<th scope="row">' + d.stars[i][6] + ', ' + d.stars[i][5] + '</th>' +
                    '<td>' + slew_action + '</td>' +
                    '<td>' + sync_action + '</td>' +
                    '<td>' + Formating.ra(d.stars[i][7]) + '/ ' + Formating.dec(d.stars[i][8]) + '</td>' +
                    '<td>' + Formating.dec(d.stars[i][37]) + '/ ' + Formating.dec(d.stars[i][38]) + '</td>' +
                    '<td>' + d.stars[i][13] + '</td>' +
                    '<td></td>' +
                    '</tr>');
                tbody.append(tr);
                $('button.sync', tr).on('click', syncclick((360.0 / 24.0) * parseFloat(d.stars[i][7]), parseFloat(d.stars[i][8])));
                $('button.slewto', tr).on('click', slewtoclick((360.0 / 24.0) * parseFloat(d.stars[i][7]), parseFloat(d.stars[i][8])));
            }

            console.log(d);

            if (d.dso.length >= 10 || d.stars.length >= 10) {
                $('#search_info', this._selfDiv).text('Too many results. Results were cut.')
            }
            $('#search_spinner', this._selfDiv).hide();
            $('#search_results', this._selfDiv).show();
        }
    })
}, 500);



class SlewingObjectSearch {
    constructor(slewing, parentDiv) {
        this._slewing = slewing;
        this._selfDiv = $(template);
        parentDiv.append(this._selfDiv);
        $('#search_txt').on('input', searchObject.bind(this));
    }
}

export default SlewingObjectSearch;