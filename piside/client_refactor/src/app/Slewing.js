/* global $ */

import SlewingObjectSearch from './SlewingObjectSearch'
import SlewingManual from './SlewingManual'
import Formating from './Formating'


import template from './templates/Slewing.html'

class Slewing {
    constructor(App, parentDiv) {
        this._selfDiv = $(template);
        parentDiv.append(this._selfDiv);
        this.slewingObjectSearch = new SlewingObjectSearch(this, this._selfDiv);
        this.slewingManual = new SlewingManual(this, this._selfDiv);

        App.socket.on('status', function (msg) {
            const slewmodal = $('#slewModal');
            if (!msg.slewing && slewmodal.hasClass('show')) {
                slewmodal.modal('hide');
            }
        });

        $('#slewModalCancel').click(function () {
            $.ajax({
                url: '/slewto',
                method: 'DELETE',
                success: function (d) {
                    $('#slewModal').modal('hide');
                },
                error: function (jq, errorstatus, errortxt) {
                    console.error(errorstatus, errortxt, jq.responseText);
                    $('#errorInfoModalTitle').text('Error');
                    $('#errorInfoModalBody').text(jq.responseText);
                    $('#errorInfoModal').modal();
                }
            })
        });

    }
    clearsync () {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: '/sync',
                method: 'DELETE',
                success: function (d) {
                    $('#errorInfoModalTitle').text('Info');
                    $('#errorInfoModalBody').html('Sync Points Cleared');
                    $('#errorInfoModal').modal();
                    resolve();
                },
                error: function (jq, errorstatus, errortxt) {
                    console.error(errortxt);
                    $('#errorInfoModalTitle').text('Error');
                    $('#errorInfoModalBody').text(jq.responseText);
                    $('#errorInfoModal').modal();
                    reject(new Error(errortxt));
                }
            });
        });

    }
    sync (ra, dec) {
        $.ajax({
            url: '/sync',
            method: 'PUT',
            dataType: 'json',
            data: {ra: ra, dec: dec},
            success: function (d) {
                console.log('synced');
                let info = '';
                if (d.hasOwnProperty('text')) {
                    info = d.text;
                }
                $('#errorInfoModalTitle').text('Info');
                $('#errorInfoModalBody').html('The mount is now synced.<br>' + info);
                $('#errorInfoModal').modal();
            },
            error: function (jq, errorstatus, errortxt) {
                console.error(errortxt);
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    }
    slewto (ra, dec) {
        $('#slewModalStatus').show();
        $('#slewModalStepsStatus').hide();
        $('#slewModalAltAzStatus').hide();
        $.ajax({
            url: '/slewto',
            method: 'PUT',
            data: {ra: ra, dec: dec},
            success: function (d) {
                const radecstr = Formating.ra((24.0 / 360) * ra) + '/' + Formating.dec(dec);
                $('#slewModalTarget').html(radecstr);
                //TODO: Dialog to abort?
                $('#slewModal').data('bs.modal', null).modal({backdrop: 'static', keyboard: false});
            },
            error: function (jq, errorstatus, errortxt) {
                console.error(errortxt);
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    }
    syncaltaz(alt, az) {
        //TODO: Combine with sync
        $.ajax({
            url: '/sync',
            method: 'PUT',
            data: {alt: alt, az: az},
            success: function (d) {
                console.log('synced');
                let info = '';
                if (d.hasOwnProperty('text')) {
                    info = d.text;
                }
                $('#errorInfoModalTitle').text('Info');
                $('#errorInfoModalBody').html('The mount is now synced.<br>' + info);
                $('#errorInfoModal').modal();
            },
            error: function (jq, errorstatus, errortxt) {
                console.error(errortxt);
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    }
    slewtoaltaz(alt, az) {
        //TODO: Combine with slewto
        $('#slewModalStatus').hide();
        $('#slewModalStepsStatus').hide();
        $('#slewModalAltAzStatus').show();
        $.ajax({
            url: '/slewto',
            method: 'PUT',
            data: {alt: alt, az: az},
            success: function (d) {
                const altAzStr = Formating.dec(alt) + '/' + Formating.dec(az);
                $('#slewModalTarget').html(altAzStr);
                //TODO: Dialog to abort?
                $('#slewModal').data('bs.modal', null).modal({backdrop: 'static', keyboard: false});
            },
            error: function (jq, errorstatus, errortxt) {
                console.error(errortxt);
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    }
    slewtosteps(ra, dec) {
        $('#slewModalStepsStatus').show();
        $('#slewModalStatus').hide();
        $('#slewModalAltAzStatus').hide();
        $.ajax({
            url: '/slewto',
            method: 'PUT',
            data: {ra_steps: ra, dec_steps: dec},
            success: function (d) {
                const radecstr = ra + '/' + dec;
                $('#slewModalTarget').html(radecstr);
                //TODO: Dialog to abort?
                $('#slewModal').data('bs.modal', null).modal({backdrop: 'static', keyboard: false});
            },
            error: function (jq, errorstatus, errortxt) {
                console.error(errortxt);
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });
    }
}

export default Slewing;