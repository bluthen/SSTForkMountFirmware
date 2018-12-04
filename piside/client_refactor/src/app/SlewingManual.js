/* global $ */

import template from './templates/SlewingManual.html'

const convert_manual_coordinates_radec = function () {
    const ras = [
        $('#goto_manual_ra_hh', this._selfDiv).val().trim(),
        $('#goto_manual_ra_mm', this._selfDiv).val().trim(),
        $('#goto_manual_ra_ss', this._selfDiv).val().trim()
    ];
    const decs = [
        $('#goto_manual_dec_dd', this._selfDiv).val().trim(),
        $('#goto_manual_dec_mm', this._selfDiv).val().trim(),
        $('#goto_manual_dec_ss', this._selfDiv).val().trim()
    ];

    for (let i = 0; i < ras.length; i++) {
        ras[i] = parseInt(ras[i], 10);
        if (isNaN(ras[i])) {
            $('#errorInfoModalTitle').text('Error');
            $('#errorInfoModalBody').text("Invalid RA Coordinates Entered.");
            $('#errorInfoModal').modal();
            return null;
        }
    }
    for (let i = 0; i < decs.length; i++) {
        decs[i] = parseInt(decs[i], 10);
        if (isNaN(decs[i])) {
            $('#errorInfoModalTitle').text('Error');
            $('#errorInfoModalBody').text("Invalid DEC Coordinates Entered.");
            $('#errorInfoModal').modal();
            return null;
        }
    }

    const ra = (360.0 / 24.0) * (ras[0] + (ras[1] / 60.0) + (ras[2] / (60 * 60)));
    let decsign;
    if (decs[0] === 0) {
        decsign = 1;
    } else {
        decsign = decs[0] / Math.abs(decs[0]);
    }
    const dec = decs[0] + decsign * (decs[1] / 60.0) + decsign * (decs[2] / (60 * 60));
    return {ra: ra, dec: dec};
};

const convert_manual_coordinates_altaz = function () {
    const alts = [
        $('#goto_manual_alt_dd', this._selfDiv).val().trim(),
        $('#goto_manual_alt_mm', this._selfDiv).val().trim(),
        $('#goto_manual_alt_ss', this._selfDiv).val().trim()
    ];
    const azs = [
        $('#goto_manual_az_ddd', this._selfDiv).val().trim(),
        $('#goto_manual_az_mm', this._selfDiv).val().trim(),
        $('#goto_manual_az_ss', this._selfDiv).val().trim()
    ];

    for (let i = 0; i < alts.length; i++) {
        alts[i] = parseInt(alts[i], 10);
        if (isNaN(alts[i])) {
            $('#errorInfoModalTitle').text('Error');
            $('#errorInfoModalBody').text("Invalid Alt Coordinates Entered.");
            $('#errorInfoModal').modal();
            return null;
        }
    }
    for (let i = 0; i < azs.length; i++) {
        azs[i] = parseInt(azs[i], 10);
        if (isNaN(azs[i])) {
            $('#errorInfoModalTitle').text('Error');
            $('#errorInfoModalBody').text("Invalid Az Coordinates Entered.");
            $('#errorInfoModal').modal();
            return null;
        }
    }
    let altsign;
    if (alts[0] === 0) {
        altsign = 1;
    } else {
        altsign = alts[0] / Math.abs(alts[0]);
    }
    const alt = alts[0] + altsign * (alts[1] / 60.0) + altsign * (alts[2] / (60 * 60));
    const az = azs[0] + (azs[1] / 60.0) + (azs[2] / (60 * 60));
    return {alt: alt, az: az};
};

const convert_manual_coordinates_steps = function () {
    const ra = parseInt($('#goto_manual_steps_ra', this._selfDiv).val().trim(), 10);
    const dec = parseInt($('#goto_manual_steps_dec', this._selfDiv).val().trim(), 10);
    if (isNaN(ra) || isNaN(dec)) {
        $('#errorInfoModalTitle').text('Error');
        $('#errorInfoModalBody').text("Invalid Step values Entered.");
        $('#errorInfoModal').modal();
        return null;
    }
    return {ra: ra, dec: dec};
};

const numbericIntOnly = function (plusminus) {
    return function (e) {
        // https://weblog.west-wind.com/posts/2011/Apr/22/Restricting-Input-in-HTML-Textboxes-to-Numeric-Values
        const key = e.which || e.keyCode;
        const keyStr = e.key;
        //console.log(key);
        //console.log(e);

        if (!e.shiftKey && !e.altKey && !e.ctrlKey &&
            // numbers
            key >= 48 && key <= 57 ||
            // Numeric keypad
            key >= 96 && key <= 105 ||
            // comma, period and minus on keypad
            (plusminus && (key === 173 || key === 187 || key === 189 || key === 109 || key === 107) || (keyStr && keyStr === '-')) ||
            // Backspace and Tab and Enter
            key === 8 || key === 9 || key === 13 ||
            // Home and End
            key === 35 || key === 36 ||
            // left and right arrows
            key === 37 || key === 39 ||
            // Del and Ins
            key === 46 || key === 45)
            return true;

        return false;
    }
};


class SlewingManual {
    constructor(slewing, parentDiv) {
        let self = this;
        this._selfDiv = $(template);
        parentDiv.append(this._selfDiv);

        $('#manual_sync', this._selfDiv).on('click', () => {
            let coords;
            if ($('#goto_manual_coord_select-radec', this._selfDiv).is(':checked')) {
                coords = convert_manual_coordinates_radec.apply(this);
                if (coords) {
                    slewing.sync(coords.ra, coords.dec);
                }
            } else if ($('#goto_manual_coord_select-altaz', this._selfDiv).is(':checked')) {
                coords = convert_manual_coordinates_altaz.apply(this);
                slewing.syncaltaz(coords.alt, coords.az);
            } else {
            }
        });
        $('#manual_slewto', this._selfDiv).on('click', () => {
            let coords;
            if ($('#goto_manual_coord_select-radec', this._selfDiv).is(':checked')) {
                coords = convert_manual_coordinates_radec.apply(this);
                slewing.slewto(coords.ra, coords.dec);
            } else if ($('#goto_manual_coord_select-altaz', this._selfDiv).is(':checked')) {
                coords = convert_manual_coordinates_altaz.apply(this);
                slewing.slewtoaltaz(coords.alt, coords.az);
            } else {
                coords = convert_manual_coordinates_steps.apply(this);
                if (coords !== null) {
                    slewing.slewtosteps(coords.ra, coords.dec);
                }
            }
        });


        $('#goto_manual_coord_select-radec, #goto_manual_coord_select-altaz, #goto_manual_coord_select-steps', this._selfDiv).change(() => {
            if ($('#goto_manual_coord_select-radec', this._selfDiv).is(':checked')) {
                $('#goto_manual_coord_altaz', this._selfDiv).hide();
                $('#goto_manual_coord_steps', this._selfDiv).hide();
                $('#goto_manual_coord_radec', this._selfDiv).show();
                $('#manual_sync', this._selfDiv).show();
            } else if ($('#goto_manual_coord_select-altaz', this._selfDiv).is(':checked')) {
                $('#goto_manual_coord_radec', this._selfDiv).hide();
                $('#goto_manual_coord_steps', this._selfDiv).hide();
                $('#goto_manual_coord_altaz', this._selfDiv).show();
                $('#manual_sync', this._selfDiv).show();
            } else {
                $('#goto_manual_coord_radec', this._selfDiv).hide();
                $('#goto_manual_coord_altaz', this._selfDiv).hide();
                $('#goto_manual_coord_steps', this._selfDiv).show();
                $('#manual_sync', this._selfDiv).hide();
            }
        });

        $('#goto_manual_ra_hh, #goto_manual_ra_mm, #goto_manual_ra_ss, #goto_manual_dec_dd, #goto_manual_dec_mm, #goto_manual_dec_ss, #goto_manual_alt_dd, #goto_manual_alt_mm, #goto_manual_alt_ss, #goto_manual_az_ddd, #goto_manual_az_mm, #goto_manual_az_ss', this._selfDiv).focus(function () {
            $(this).select();
        });

        $('#goto_manual_ra_hh, #goto_manual_ra_mm, #goto_manual_ra_ss, #goto_manual_dec_mm, #goto_manual_dec_ss, #goto_manual_alt_mm, #goto_manual_alt_ss, #goto_manual_az_ddd, #goto_manual_az_mm, #goto_manual_az_ss', this._selfDiv).keydown(numbericIntOnly(false));
        $('#goto_manual_dec_dd, #goto_manual_alt_dd, #goto_manual_steps_ra, #goto_manual_steps_ra', this._selfDiv).keydown(numbericIntOnly(true));

        $('#goto_manual_ra_hh', this._selfDiv).keyup(function (e) {
            console.log(this);
            if (this.selectionStart === this.selectionEnd && this.value.length === 2) {
                $('#goto_manual_ra_mm', self._selfDiv).focus();
            }
        });

        $('#goto_manual_ra_mm', this._selfDiv).keyup(function (e) {
            console.log(this);
            if (this.selectionStart === this.selectionEnd && this.value.length === 2) {
                $('#goto_manual_ra_ss', self._selfDiv).focus();
            }
        });

        $('#goto_manual_ra_ss', this._selfDiv).keyup(function (e) {
            console.log(this);
            if (this.selectionStart === this.selectionEnd && this.value.length === 2) {
                $('#goto_manual_dec_dd', self._selfDiv).focus();
            }
        });

        $('#goto_manual_dec_dd', this._selfDiv).keyup(function (e) {
            console.log(this);
            if (this.selectionStart === this.selectionEnd && ((this.value[0] !== '-' && this.value[0] !== '+' && this.value.length === 2) || this.value.length === 3)) {
                $('#goto_manual_dec_mm', self._selfDiv).focus();
            }
        });

        $('#goto_manual_dec_mm', this._selfDiv).keyup(function (e) {
            console.log(this);
            if (this.selectionStart === this.selectionEnd && this.value.length === 2) {
                $('#goto_manual_dec_ss', self._selfDiv).focus();
            }
        });

        $('#goto_manual_alt_dd', this._selfDiv).keyup(function (e) {
            if (this.selectionStart === this.selectionEnd && ((this.value[0] !== '-' && this.value[0] !== '+' && this.value.length === 2) || this.value.length === 3)) {
                $('#goto_manual_alt_mm', self._selfDiv).focus();
            }
        });

        $('#goto_manual_alt_mm', this._selfDiv).keyup(function (e) {
            if (this.selectionStart === this.selectionEnd && this.value.length === 2) {
                $('#goto_manual_alt_ss', self._selfDiv).focus();
            }
        });

        $('#goto_manual_alt_ss', this._selfDiv).keyup(function (e) {
            if (this.selectionStart === this.selectionEnd && this.value.length === 2) {
                $('#goto_manual_az_ddd', self._selfDiv).focus();
            }
        });

        $('#goto_manual_az_ddd', this._selfDiv).keyup(function (e) {
            if (this.selectionStart === this.selectionEnd && this.value.length === 3) {
                $('#goto_manual_az_mm', self._selfDiv).focus();
            }
        });

        $('#goto_manual_az_mm', this._selfDiv).keyup(function (e) {
            if (this.selectionStart === this.selectionEnd && this.value.length === 2) {
                $('#goto_manual_az_ss', self._selfDiv).focus();
            }
        });
    }
}

export default SlewingManual;