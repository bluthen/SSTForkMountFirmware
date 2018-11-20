/* global $ */

import Formating from './Formating'

import template from './templates/Footer.html'

class Footer {
    constructor(App, parentDiv, startingSettings) {
        this._selfDiv = $(template);
        parentDiv.append(this._selfDiv);

        const location = $('#location', this._selfDiv);
        location.empty();

        if (startingSettings.location.name) {
            location.text(startingSettings.location.name);
        }

        App.socket.on('status', (msg) => {
            //console.log(msg);
            const status = msg;
            if ('alert' in msg) {
                console.error('ALERT', msg.alert);
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(msg.alert);
                $('#errorInfoModal').modal();
            }
            const status_radec = $('#status_radec');
            const status_altaz = $('#status_altaz');
            const status_radec2 = $('#slewModalStatus');
            const status_altaz2 = $('#slewModalAltAzStatus');
            const status_steps2 = $('#slewModalStepsStatus');
            status_radec.empty();
            status_altaz.empty();
            if (status.ra) {
                const radecstr = Formating.ra((24.0 / 360) * status.ra) + '/' + Formating.dec(status.dec);
                status_radec.html(radecstr);
                status_radec2.html(radecstr);
            }
            if (status.alt) {
                status_altaz.html(Formating.dec(status.alt) + '/' + Formating.dec(status.az));
                status_altaz2.html(Formating.dec(status.alt) + '/' + Formating.dec(status.az));
            }
            $('#status_ra_ticks', this._selfDiv).text('' + msg.rs + '/' + msg.rp);
            $('#status_dec_ticks', this._selfDiv).text('' + msg.ds + '/' + msg.dp);
            status_steps2.text(msg.rp + '/' + msg.dp);
            $('#status_time', this._selfDiv).text(msg.time);
        });


    }
}

export default Footer;