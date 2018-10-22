/* global $ */

import Formating from './Formating'

import template from './templates/SettingsMenuNetwork.html'

window.Formating = Formating;

const wifiClientConnect = function (ssid, mac, open, known, password) {
    return new Promise((resolve, reject) => {
        const data = {ssid: ssid, mac: mac, psk: password, open: open, known: known};
        $.ajax({
            url: '/wifi_connect',
            method: 'POST',
            data: data,
            success: () => {
                resolve();
            },
            error: (jq) => {
                reject(new Error(jq.responseText));
            }
        });
    });
};

const saveClicked = function () {
    const data = {
        ssid: $('#networkSettingsWifiAPSSID', this._selfDiv).removeClass('is-invalid').val().trim(),
        wpa2key: $('#networkSettingsWifiAPKey', this._selfDiv).removeClass('is-invalid').val(),
        channel: parseInt($('#networkSettingsWifiAPChannel', this._selfDiv).removeClass('is-invalid').val(), 10)
    };
    let valid = true;
    if (data.wpa2key.length === 0) {
        data.wpa2key = null;
    }
    if (data.ssid.length > 31) {
        $('#networkSettingsWifiAPSSID', this._selfDiv).addClass('is-invalid').next().text('Must be less than 31 characters');
        valid = false;
    }
    if (data.wpa2key && data.wpa2key.length !== 0 && (data.wpa2key.length < 8 || data.wpa2key.length > 63)) {
        $('#networkSettingsWifiAPKey', this._selfDiv).addClass('is-invalid').next().text('Length must be 0 or between 8-63');
        valid = false;
    }
    if (data.channel <= 0 || data.channel >= 11) {
        $('#networkSettingsWifiAPChannel', this._selfDiv).addClass('is-invalid').next().text('Channel should be between 1 & 11');
        valid = false;
    }
    if (!valid) {
        return;
    }
    const button = $('#networkSettingsWifiAPSave', this._selfDiv);
    const unspin = Formating.makeSpinner(button);
    $.ajax({
        url: '/settings_network_wifi',
        method: 'PUT',
        data: data,
        success: (d) => {
            unspin();
            $('span', $('#networkSettingsWifiAPSave', this._selfDiv).parent()).text('Saved').show().fadeOut(1000);
        },
        error: (jq) => {
            unspin();
            $('#errorInfoModalTitle').text('Error');
            $('#errorInfoModalBody').text(jq.responseText);
            $('#errorInfoModal').modal();
        }
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
    const button = $('#networkSettingsEthernetSave', this._selfDiv);
    const $ip = $('#networkSettingsEthernetStaticIP', this._selfDiv).removeClass('is-invalid');
    const $netmask = $('#networkSettingsEthernetStaticNetmask', this._selfDiv).removeClass('is-invalid');
    const dhcp_server = $('#networkSettingsEthernetDHCPServerEnabled', this._selfDiv).is(':checked');
    const ip = $ip.val();
    const netmask = $netmask.val();
    let valid = true;
    if (!validIP(ip, false)) {
        $ip.addClass('is-invalid').next().text('Invalid IP address');
        valid = false;
    }
    if (!validIP(netmask, false)) {
        $ip.addClass('is-invalid').next().text('Invalid netmask');
        valid = false;
    }
    if (!valid) {
        return;
    }
    const data = {ip: ip, netmask: netmask, dhcp_server: dhcp_server};
    //TODO: Dialog about how maybe after network change can't access anymore?
    const unspin = Formating.makeSpinner(button);
    $.ajax({
        url: '/settings_network_ethernet',
        method: 'PUT',
        data: data,
        success: (d) => {
            unspin();
            $('span', $('#networkSettingsEthernetSave', this._selfDiv).parent()).text('Saved').show().fadeOut(1000);
        },
        error: function (jq) {
            unspin();
            $('#errorInfoModalTitle').text('Error');
            $('#errorInfoModalBody').text(jq.responseText);
            $('#errorInfoModal').modal();
        }
    });
}


class SettingsMenuNetwork {
    constructor(parentDiv) {
        this._knownWifi = [];
        this._selfDiv = $(template);
        parentDiv.append(this._selfDiv);

        $('#networkSettingsWifiClientRescan', this._selfDiv).click(() => {
            this.wifiClientScan();
        });
        $('#networkSettingsWifiAPSave', this._selfDiv).click(saveClicked.bind(this));
        $('#networkSettingsEthernetSave', this._selfDiv).click(saveEthernetClicked.bind(this));
        $('#networkSettingsWifiAPChannel', this._selfDiv).inputSpinner();
    }

    show() {
        this.update(() => {
            this._selfDiv.data('bs.modal', null).modal({backdrop: true, keyboard: true});
            //Update wifi client list.
            this.updateKnownWifi().finally(() => {
                this.wifiClientScan();
            });
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
        const makeConnectClick = (ssid, mac, open, known, tr) => {
            return () => {
                const unspin = Formating.makeSpinner($('button', tr));
                const password = $('input', tr).val();
                wifiClientConnect.apply(this, [ssid, mac, open, known, password]).finally(() => {
                    unspin();
                    this.show();
                });
            }
        };
        $.ajax({
            url: '/wifi_scan',
            dataType: 'json',
            success: (data) => {
                const list = $('#networkSettingsWifiClientList tbody', this._selfDiv).empty();
                const connectButton = '<button type="button" class="btn btn-success"><i class="fas fa-globe" title="set"></i>Connect</button>';
                const passwordInput = '<br/><input class="wifisecurity" type="text">';
                for (let i = 0; i < data.aps.length; i++) {
                    const ap = data.aps[i];
                    const known = _.find(this._knownWifi, function (o) {
                        return o.bssid === ap.mac && o.ssid === ap.ssid;
                    });
                    const open = ap.flags.toLowerCase().indexOf('psk') === -1;
                    let connect_td = connectButton;
                    let security_td = ap.flags + (!known && !open ? passwordInput : '');
                    if (ap.ssid === data.connected.ssid && ap.mac === data.connected.mac) {
                        connect_td = 'Connected';
                        security_td = ap.flags;
                    }
                    console.log(ap.ssid);
                    const tr = $('<tr>' +
                        '<th scope="row">' + Formating.escapeHTML(ap.ssid, 20) + '<br/>' + ap.mac + '</th>' +
                        '<td>' + ap.signal + '</td>' +
                        '<td>' + security_td + '</td>' +
                        '<td>' + connect_td + '</td>'
                    );
                    list.append(tr);
                    $('button', tr).on('click', makeConnectClick(ap.ssid, ap.mac, open, known, tr));
                }
                $('#networkSettingsWifiClientListSpinner', this._selfDiv).hide();
                $('#networkSettingsWifiClientList', this._selfDiv).show();
            }
        });
    }

    updateKnownWifi() {
        const makeClick = (ssid, bssid, button) => {
            return () => {
                const unspin = Formating.makeSpinner(button);
                this.wifiForget(ssid, bssid).finally(() => {
                    unspin();
                    this.show();
                });
            }
        };
        return new Promise((resolve, reject) => {
            $.ajax({
                url: '/wifi_known',
                method: 'GET',
                success: (d) => {
                    this._knownWifi = d;
                    const list = $('#networkSettingsClientKnownList', this._selfDiv).empty();
                    const forgetButton = '<button type="button" class="btn btn-danger"></i>Forget</button>';

                    for (let i = 0; i < d.length; i++) {
                        const ap = d[i];
                        const tr = $('<tr>' +
                            '<th scope="row">' + Formating.escapeHTML(ap.ssid, 20) + '<br/>' + ap.bssid + '</th>' +
                            '<td>' + forgetButton + '</td>'
                        );
                        const button = $('button', tr);
                        button.on('click', makeClick(ap.ssid, ap.bssid, button));
                        list.append(tr);
                    }
                    resolve(d);
                },
                error: (jq, textStatus, errorThrown) => {
                    reject(new Error(jq.responseText));
                }
            });
        });
    }

    wifiForget(ssid, mac) {
        //TODO: Put up spinner
        return new Promise((resolve, reject) => {
            $.ajax({
                url: '/wifi_connect',
                method: 'DELETE',
                data: {ssid: ssid, mac: mac},
                success: () => {
                    resolve();
                },
                error: (jq) => {
                    $('#errorInfoModalTitle').text('Error');
                    $('#errorInfoModalBody').text(jq.responseText);
                    $('#errorInfoModal').modal();
                    reject();
                }
            });
        });

    }

}

export default SettingsMenuNetwork;