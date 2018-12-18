/* global $ */
import template from './templates/SettingsMenuGeneral.html'
import Formating from './Formating'


const saveSettingsClicked = function() {
    const settings = {
        ra_track_rate: $('#settings_ra_track_rate', this._selfDiv).val(),
        dec_ticks_per_degree: $('#settings_dec_ticks_per_degree', this._selfDiv).val(),
        ra_direction: $('#settings_ra_direction', this._selfDiv).val(),
        dec_direction: $('#settings_dec_direction', this._selfDiv).val(),
        ra_guide_rate: $('#settings_ra_guide_rate', this._selfDiv).val(),
        ra_slew_fastest: $('#settings_ra_slew_fastest', this._selfDiv).val(),
        ra_slew_faster: $('#settings_ra_slew_faster', this._selfDiv).val(),
        ra_slew_medium: $('#settings_ra_slew_medium', this._selfDiv).val(),
        ra_slew_slower: $('#settings_ra_slew_slower', this._selfDiv).val(),
        ra_slew_slowest: $('#settings_ra_slew_slowest', this._selfDiv).val(),
        dec_guide_rate: $('#settings_dec_guide_rate', this._selfDiv).val(),
        dec_slew_fastest: $('#settings_dec_slew_fastest', this._selfDiv).val(),
        dec_slew_faster: $('#settings_dec_slew_faster', this._selfDiv).val(),
        dec_slew_medium: $('#settings_dec_slew_medium', this._selfDiv).val(),
        dec_slew_slower: $('#settings_dec_slew_slower', this._selfDiv).val(),
        dec_slew_slowest: $('#settings_dec_slew_slowest', this._selfDiv).val()
    };
    $.ajax({
        url: '/settings',
        method: 'PUT',
        data: {'settings': JSON.stringify(settings)},
        success: () => {
            $('#settings_save_status', this._selfDiv).text('Saved').show().fadeOut(1000);
        },
        error: function (jq, errorstatus, errortxt) {
            console.error('Invalid Latitude entered.');
            $('#errorInfoModalTitle').text('Error');
            $('#errorInfoModalBody').text(jq.responseText);
            $('#errorInfoModal').modal();
            return;
        }
    });
};

class SettingsMenuGeneral {
    constructor(App, parentDiv) {
        this._selfDiv = $(template);
        this._selfDiv.hide();
        parentDiv.append(this._selfDiv);

        App.socket.on('status', (msg) => {
            if (msg.tracking) {
                $('#settings_stop_tracking', this._selfDiv).show();
                $('#settings_start_tracking', this._selfDiv).hide();
            } else {
                $('#settings_start_tracking', this._selfDiv).show();
                $('#settings_stop_tracking', this._selfDiv).hide();
            }
        });

        $.ajax({
            url: '/version',
            method: 'GET',
            success: function (d) {
                $('#firmware_version', this._selfDiv).html('Current&nbsp;Version:&nbsp;' + d.version);
            },
            error: function (jq, errorstatus, errortxt) {
                $('#firmware_version', this._selfDiv).html('Current&nbsp;Version:&nbsp;Unknown');
            }
        });

        $('#settings_save', this._selfDiv).click(saveSettingsClicked.bind(this));

        $('#settings_park', this._selfDiv).click(() => {
            $.ajax({
                url: '/park',
                method: 'PUT',
                success: () => {
                    $('#slewModalTarget').html('Parking...');
                    //TODO: Dialog to abort?
                    $('#slewModal').data('bs.modal', null).modal({backdrop: 'static', keyboard: false});
                },
                error: function (jq, errorstatus, errortxt) {
                    $('#errorInfoModalTitle').text('Error');
                    $('#errorInfoModalBody').text(jq.responseText);
                    $('#errorInfoModal').modal();
                }
            });
        });

        $('#settings_set_park_position', this._selfDiv).click(() => {
            console.log('Setting park position');
            $.ajax({
                url: '/set_park_position',
                method: 'PUT',
                success: () => {
                    this.updateSettings();
                },
                error: function (jq, errorstatus, errortxt) {
                    $('#errorInfoModalTitle').text('Error');
                    $('#errorInfoModalBody').text(jq.responseText);
                    $('#errorInfoModal').modal();
                }
            });
        });

        $('#settings_unset_park_position', this._selfDiv).click(() => {
            $.ajax({
                url: '/set_park_position',
                method: 'DELETE',
                success: () => {
                    this.updateSettings();
                },
                error: function (jq, errorstatus, errortxt) {
                    $('#errorInfoModalTitle').text('Error');
                    $('#errorInfoModalBody').text(jq.responseText);
                    $('#errorInfoModal').modal();
                }
            });

        });

        $('#settings_start_tracking', this._selfDiv).click(function () {
            $.ajax({
                url: '/start_tracking',
                method: 'PUT',
                success: function () {
                },
                error: function (jq, errorstatus, errortxt) {
                    $('#errorInfoModalTitle').text('Error');
                    $('#errorInfoModalBody').text(jq.responseText);
                    $('#errorInfoModal').modal();
                }
            });
        });

        $('#settings_stop_tracking', this._selfDiv).click(function () {
            $.ajax({
                url: '/stop_tracking',
                method: 'PUT',
                success: function () {
                },
                error: function (jq, errorstatus, errortxt) {
                    $('#errorInfoModalTitle').text('Error');
                    $('#errorInfoModalBody').text(jq.responseText);
                    $('#errorInfoModal').modal();
                }
            });
        });

        $('#settings-color-scheme-default, #settings-color-scheme-nightvision', this._selfDiv).change(() => {
            if ($('#settings-color-scheme-default', this._selfDiv).is(':checked')) {
                $('#bootstrapcss').attr('href', 'bootstrap/css/bootstrap.min.css');
                $('#maincss').attr('href', 'main.css');
            } else {
                $('#bootstrapcss').attr('href', 'bootstrap/css/bootstrap.min.redlights.css');
                $('#maincss').attr('href', 'main.redlights.css');
            }
        });

        $('#firmware_file_upload', this._selfDiv).click(() => {
            const formData = new FormData();
            const file = $('#firmware_file', this._selfDiv)[0].files[0];
            if (file) {
                formData.append('file', file);
                $.ajax({
                    url: '/firmware_update',
                    type: 'POST',
                    data: formData,
                    processData: false,
                    contentType: false,
                    success: (data) => {
                        $('#firmware_upload_div', this._selfDiv).html('Success. Rebooting, please wait 1min...');
                        setTimeout(function () {
                            location.reload(true);
                        }, 50000);
                    },
                    error: (jq) => {
                        $('#firmware_upload_div', this._selfDiv).html('Error:' + jq.responseText);
                    }
                });
            }
        });

    }

    show() {
        this.updateSettings(() => {
            this._selfDiv.show();
        });
    }

    hide() {
        this._selfDiv.hide();
    }

    updateSettings(successCB) {
        $.ajax({
            url: '/settings',
            dataType: 'json',
            success: (data) => {
                $('#settings_ra_track_rate', this._selfDiv).val(data.ra_track_rate);
                $('#settings_dec_ticks_per_degree', this._selfDiv).val(data.dec_ticks_per_degree);
                $('#settings_ra_direction', this._selfDiv).val(data.micro.ra_direction);
                $('#settings_dec_direction', this._selfDiv).val(data.micro.dec_direction);
                $('#settings_ra_guide_rate', this._selfDiv).val(data.micro.ra_guide_rate);
                $('#settings_ra_slew_fastest', this._selfDiv).val(data.ra_slew_fastest);
                $('#settings_ra_slew_faster', this._selfDiv).val(data.ra_slew_faster);
                $('#settings_ra_slew_medium', this._selfDiv).val(data.ra_slew_medium);
                $('#settings_ra_slew_slower', this._selfDiv).val(data.ra_slew_slower);
                $('#settings_ra_slew_slowest', this._selfDiv).val(data.ra_slew_slowest);
                $('#settings_dec_guide_rate', this._selfDiv).val(data.micro.dec_guide_rate);
                $('#settings_dec_slew_fastest', this._selfDiv).val(data.dec_slew_fastest);
                $('#settings_dec_slew_faster', this._selfDiv).val(data.dec_slew_faster);
                $('#settings_dec_slew_medium', this._selfDiv).val(data.dec_slew_medium);
                $('#settings_dec_slew_slower', this._selfDiv).val(data.dec_slew_slower);
                $('#settings_dec_slew_slowest', this._selfDiv).val(data.dec_slew_slowest);

                if (data.park_position) {
                    $('#settings_park_position', this._selfDiv).html(Formating.dec(data.park_position.alt) + '/' + Formating.dec(data.park_position.az));
                    $('#settings_unset_park_position', this._selfDiv).show();
                } else {
                    $('#settings_park_position', this._selfDiv).html('None Set');
                    $('#settings_unset_park_position', this._selfDiv).hide();
                }
                if (successCB) {
                    successCB();
                }
            },
            error: function (jq, errorstatus, errortxt) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    }
}

export default SettingsMenuGeneral;
