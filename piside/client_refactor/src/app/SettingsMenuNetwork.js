/* global $ */

import Formating from './Formating'

import template from './templates/SettingsMenuNetwork.html'


const wifiClientConnect = function (ssid, mac) {
    return function () {
        //TODO: Put up spinner
        $.ajax({
            url: '/wifi_connect',
            method: ['POST'],
            data: {ssid: ssid, mac: mac},
            success: function () {
                //TODO: ok dialog saying connected.
                //TODO: Reload?
            }
        });
    }
};

const saveClicked = function () {
    const data = {
        mode: $('input[name="networkSettingsWifiAPMode"]:checked', this._selfDiv).val(),
        ssid: $('#networkSettingsWifiAPSSID', this._selfDiv).removeClass('is-invalid').val().trim(),
        wpa2key: $('#networkSettingsWifiAPKey', this._selfDiv).removeClass('is-invalid').val(),
        channel: parseInt($('#networkSettingsWifiAPChannel', this._selfDiv).removeClass('is-invalid').val(), 10)
    };
    let valid = true;
    if (data.wpa2key.length === 0) {
        data.wpa2key = null;
    }
    if (data.mode !== 'clientonly' && data.ssid.length > 31) {
        $('#networkSettingsWifiAPSSID', this._selfDiv).addClass('is-invalid').next().text('Must be less than 31 characters');
        valid = false;
    }
    if (data.wpa2key !== null && data.mode !== 'clientonly' && (data.wpa2key.length < 8 || data.wpa2key.length > 63)) {
        $('#networkSettingsWifiAPKey', this._selfDiv).addClass('is-invalid').next().text('Length must be 0 or between 8-63');
        valid = false;
    }
    if (data.mode !== 'clientonly' && (data.channel <= 0 || data.channel >= 11)) {
        $('#networkSettingsWifiAPChannel', this._selfDiv).addClass('is-invalid').next().text('Channel should be between 1 & 11');
        valid = false;
    }
    if (!valid) {
        return;
    }
    $.ajax({
        url: '/settings_network_wifi',
        method: 'PUT',
        data: data,
        success: function (d) {

        }//TODO: Error dialog, or message somewhere
    });
    //TODO: Dialog about how maybe after network change can't access anymore?
};

/**
 *
 * @param ipOrNetmask {string} IP like string to check.
 * @param netmask {boolean} If it is a netmask string instead of actual ip.
 * @returns {boolean} true if valid
 */
function validIP(ipOrNetmask, netmask) {
    const blocks = ipOrNetmask.split('.');
    if (blocks.length === 4) {
        for (let i = 0; i < blocks.length; i++) {
            const v = parseInt(blocks[i], 10);
            blocks[i] = v;
            if (isNaN(v)) {
                return false;
            }
            if (!netmask && i === 0 && (v < 1 || v > 255)) {
                return false;
            } else if (v < 0 || v > 255) {
                return false;
            }
        }
        if (!netmask && blocks[0] === 255 && blocks[1] === 255 && blocks[2] === 255 && blocks[3] === 255) {
            return false;
        }
        return true;
    } else {
        return false;
    }
}


function saveEthernetClicked() {
    const $ip = $('#networkSettingsEthernetStaticIP', this._selfDiv).removeClass('is-invalid');
    const $netmask = $('#networkSettingsEthernetStaticNetmask', this._selfDiv).removeClass('is-invalid');
    const dhcp_server = $('#networkSettingsEthernetDHCPServerEnabled', this._selfDiv).is(':checked');
    const ip = $ip.val();
    const netmask = $netmask.val();
    let valid = true;
    if(!validIP(ip, false)) {
        $ip.addClass('is-invalid').next().text('Invalid IP address');
        valid = false;
    }
    if(!validIP(netmask, false)) {
        $ip.addClass('is-invalid').next().text('Invalid netmask');
        valid = false;
    }
    if(!valid) {
        return;
    }
    const data = {ip: ip, netmask: netmask, dhcp_server: dhcp_server};
    //TODO: Dialog about how maybe after network change can't access anymore?
    $.ajax({
        url: '/settings_network_ethernet',
        method: 'PUT',
        data: data,
        success: (d) => {
            $('span', $('#networkSettingsEthernetSave', this._selfDiv).parent()).text('Saved').show().fadeOut(1000);
        },
        error: function() {
            $('#errorInfoModalTitle').text('Error');
            $('#errorInfoModalBody').text(jq.responseText);
            $('#errorInfoModal').modal();
        }
    });
}


class SettingsMenuNetwork {
    constructor(parentDiv) {
        this._selfDiv = $(template);
        parentDiv.append(this._selfDiv);

        $('#networkSettingsWifiClientRescan', this._selfDiv).click(() => {
            this.wifiClientScan();
        });
        $('#networkSettingsWifiAPSave', this._selfDiv).click(saveClicked.bind(this));
        $('#networkSettingsEthernetSave', this._selfDiv).click(saveEthernetClicked.bind(this))
    }

    show() {
        this.update(() => {
            this._selfDiv.data('bs.modal', null).modal({backdrop: true, keyboard: true});
            //Update wifi client list.
            this.wifiClientScan();
            this.updateKnownWifi();
        });
    }

    update(successCB) {
        $.ajax({
            url: '/settings',
            dataType: 'json',
            success: (data) => {

                // Network
                $('#networkSettingsWifiAPSSID', this._selfDiv).val(data.network.ssid);
                $('#networkSettingsWifiAPKey', this._selfDiv).val(data.network.wpa2key);
                $('#networkSettingsWifiAPChannel', this._selfDiv).val(data.network.channel);
                $('#networkSettingsEthernetStaticIP', this._selfDiv).val(data.network.ip);
                $('#networkSettingsEthernetStaticNetmask', this._selfDiv).val(data.network.netmask);
                if (data.network.mode === 'autoap') {
                    $('#networkSettingsWifiAPModeAutoAp', this._selfDiv).click();
                } else if (data.network.mode === 'always') {
                    $('#networkSettingsWifiAPModeAlways', this._selfDiv).click();
                } else if (data.network.mode === 'clientonly') {
                    $('#networkSettingsWifiAPModeClientOnly', this._selfDiv).click();
                }
                const enabledRadio = $('#networkSettingsEthernetDHCPServerEnabled', this._selfDiv);
                const disabledRadio = $('#networkSettingsEthernetDHCPServerDisabled', this._selfDiv);
                if (data.network.dhcp_server) {
                    disabledRadio.prop('checked', false);
                    enabledRadio.prop('checked', true);
                } else {
                    enabledRadio.prop('checked', false);
                    disabledRadio.prop('checked', true);
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

    wifiClientScan() {
        $('#networkSettingsWifiClientList', this._selfDiv).hide();
        $('#networkSettingsWifiClientListSpinner', this._selfDiv).show();
        $.ajax({
            url: '/wifi_scan',
            dataType: 'json',
            success: (data) => {
                const list = $('#networkSettingsWifiClientList tbody', this._selfDiv).empty();
                for (let i = 0; i < data.aps.length; i++) {
                    const ap = data.aps[i];
                    const connectButton = '<button type="button" class="btn btn-success"><i class="fas fa-globe" title="set"></i>Connect</button>';
                    let connect_td = connectButton;
                    if (ap.ssid === data.connected.ssid && ap.mac === data.connected.mac) {
                        connect_td = 'Connected';
                    }
                    const tr = $('<tr>' +
                        '<th scope="row">' + Formating.escapeHTML(ap.ssid, 20) + '<br/>' + ap.mac + '</th>' +
                        '<td>' + ap.signal + '</td>' +
                        '<td>' + ap.flags + '</td>' +
                        '<td>' + connect_td + '</td>'
                    );
                    $('button', tr).on('click', wifiClientConnect(ap.ssid, ap.mac));
                    list.append(tr);
                }
                $('#networkSettingsWifiClientListSpinner', this._selfDiv).hide();
                $('#networkSettingsWifiClientList', this._selfDiv).show();
            }
        });
    }

    updateKnownWifi() {
        $.ajax({
            url: '/wifi_known',
            method: 'GET',
            success: (d) => {
                const list = $('#networkSettingsClientKnownList', this._selfDiv).empty();
                const forgetButton = '<button type="button" class="btn btn-danger"></i>Forget</button>';

                for (let i = 0; i < d.length; i++) {
                    const ap = d[i];
                    const tr = $('<tr>' +
                        '<th scope="row">' + Formating.escapeHTML(ap.ssid, 20) + '<br/>' + ap.bssid + '</th>' +
                        '<td>' + forgetButton + '</td>'
                    );
                    $('button', tr).on('click', this.wifiForget(ap.ssid, ap.bssid));
                    list.append(tr);
                }
            }
        });
    }

    wifiForget(ssid, mac) {
        return () => {
            //TODO: Put up spinner
            $.ajax({
                url: '/wifi_connect',
                method: ['DELETE'],
                data: {ssid: ssid, mac: mac},
                success: () => {
                    //TODO: ok dialog saying connected.
                    //TODO: Reload?
                }
            });
        }
    }


}

export default SettingsMenuNetwork;