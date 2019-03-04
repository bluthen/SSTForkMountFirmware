/* global $ */
import template from './templates/SettingsMenuPointModel.html';
import PointModelGraph from './pointModel/PointModelGraph';


class SettingsMenuPointModel {
    constructor(slewing, parentDiv) {
        this._selfDiv = $(template);
        parentDiv.append(this._selfDiv);

        $('#pointModelClearSync', this._selfDiv).on('click', () => {
            slewing.clearsync().then(()=>{ this._update(); });
        });
        $('#pointModelSave', this._selfDiv).on('click', () => {
            $.ajax({
                url: '/sync',
                method: 'POST',
                data: {'model': $('#pointModelSelect', this._selfDiv).val()},
                success: () => {
                    $('#errorInfoModalTitle').text('Info');
                    $('#errorInfoModalBody').html('Point Model Changed');
                    $('#errorInfoModal').modal();
                    this._update();
                },
                error: function (jq, errorstatus, errortxt) {
                    console.error('Invalid Latitude entered.');
                    $('#errorInfoModalTitle').text('Error');
                    $('#errorInfoModalBody').text(jq.responseText);
                    $('#errorInfoModal').modal();
                    return;
                }
            });
        });

        $('#settings-atmospheric-refraction-enabled, #settings-atmospheric-refraction-disabled', this._selfDiv).change(() => {
            if($('#settings-atmospheric-refraction-enabled', this._selfDiv).is(':checked')) {
                $.ajax({
                    url: '/settings',
                    method: 'PUT',
                    data: {'settings': JSON.stringify({atmos_refract: true})}
                });
            } else {
                $.ajax({
                    url: '/settings',
                    method: 'PUT',
                    data: {'settings': JSON.stringify({atmos_refract: false})}
                });
            }
        });

        this._graph = new PointModelGraph($('#pointModelCanvas', this._selfDiv)[0])
        this._update();
    }

    _update() {
        $.ajax({
            url: '/settings',
            dataType: 'json',
            success: (data) => {
                $('option[value="' + data.pointing_model + '"]', this._selfDiv).prop('selected', true);
            }
        });
        $.ajax({
            url: '/sync',
            method: 'GET',
            dataType: 'json',
            success: (data) => {
                this._graph.points = data;
            }
        });
        // TODO: Plot current position as a point
        // TODO: High current points being used in model
    }

    show() {
        this._update();
        this._selfDiv.show();
    }

    hide() {
        this._selfDiv.hide();
    }
}

export default SettingsMenuPointModel;