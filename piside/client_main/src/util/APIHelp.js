/* global fetch */
import state from '../State';
import {observe} from "mobx";
import _ from 'lodash';
import Formatting from './Formatting';
import Papa from 'papaparse';


function handleFetchError(response) {
    if (!response.ok) {
        console.error(response.statusText);
        const t = response.statusText;
        return response.text().then((t2) => {
            if (!t2) {
                throw Error(t);
            } else {
                throw Error(t2);
            }
        });
    }
    return response;
}


function getStatus() {
    return fetch('/api/status').then(handleFetchError).then((response) => {
        return response.json();
    });
}

let searchCounter = 0;

const doObjectSearch = _.debounce(function () {
    const t = state.goto.object_search.search_txt;
    if (t === null || !t.trim()) {
        return;
    }
    searchCounter++;
    let sc = searchCounter;
    state.goto.object_search.searching = true;
    return fetch('/api/search_object?search=' + encodeURIComponent(t)).then(handleFetchError).then((response) => {
        state.goto.object_search.searching = false;
        if (sc !== searchCounter) {
            return;
        }
        response.json().then((d) => {
            state.goto.object_search.results.replace(d.planets.concat(d.dso).concat(d.stars));
        });
    }).catch((e) => {
        state.goto.object_search.searching = false;
        state.goto.object_search.results.replace([]);
        state.snack_bar_error = true;
        state.snack_bar = 'Error: Failed to get search results';
        throw e;
    });
}, 500);

let locationSearchCounter = 0;
const doLocationSearch = _.debounce(function () {
    const t = state.location.city_search;
    if (t === null || !t.trim()) {
        return;
    }
    searchCounter++;
    let sc = searchCounter;
    state.location.city_searching = true;
    return fetch('/api/search_location?search=' + encodeURIComponent(t)).then(handleFetchError).then((response) => {
        state.location.city_searching = false;
        if (sc !== searchCounter) {
            return;
        }
        response.json().then((d) => {
            state.location.city_search_results.replace(d);
        });
    }).catch((e) => {
        state.location.city_searching = false;
        state.location.city_search_results.replace([]);
        state.snack_bar_error = true;
        state.snack_bar = 'Error: Failed to get search results';
        throw e;
    });
}, 500);

let statusUpdateIntervalStarted = false;
const STATUS_DELAY = 1000;

const dirMap = {north: 'up', south: 'down', east: 'right', west: 'left'};
const oppositeMap = {'left': 'right', 'right': 'left', 'up': 'down', 'down': 'up'};


function sendManualRequest(speed, direction) {
    return fetch('/api/manual_control', {
        method: 'post',
        body: JSON.stringify({speed: speed, direction: direction}),
        headers: {
            'Content-Type': 'application/json'
        }
    }).then(handleFetchError);
}


function manualActive(speed, direction) {
    sendManualRequest(speed, direction);
}


function manualInactive(direction) {
    sendManualRequest(null, direction);
}

function observeManualDirection(cardinalDir) {
    observe(state.manual.directions, cardinalDir, () => {
        if (state.manual.directions[cardinalDir]) {
            manualActive(state.manual.speed, dirMap[cardinalDir]);
        } else {
            manualInactive(dirMap[cardinalDir]);
        }
    });
}

function updateCoordDialogMissing() {
    const res = {
        alt: state.goto.coorddialog.altdeg,
        az: state.goto.coorddialog.azdeg,
        ra: state.goto.coorddialog.radeg,
        dec: state.goto.coorddialog.decdeg
    };
    if ((res.ra !== null && res.dec !== null && res.alt === null && res.az === null) || (res.alt !== null && res.az !== null && res.ra === null && res.dec === null)) {
        fetch('/api/convert_coord', {
            method: 'post',
            body: JSON.stringify(res),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.json()
        }).then((d) => {
            if (d.hasOwnProperty('ra')) {
                state.goto.coorddialog.radeg = d.ra;
                state.goto.coorddialog.decdeg = d.dec;
            } else {
                state.goto.coorddialog.altdeg = d.alt;
                state.goto.coorddialog.azdeg = d.az;
            }
        });
    }
}


const APIHelp = {
    statusUpdate: function () {
        return getStatus().then((s) => {
            Object.keys(s).forEach((key) => {
                if (state.status[key] !== s[key]) {
                    state.status[key] = s[key];
                }
            });
        }).catch((e) => {
            console.error('Failed to get status.', e);
            state.snack_bar = 'Error: Failed to get status, check network';
            state.snack_bar_error = true;
        });
    },

    startStatusUpdateInterval: function () {
        console.log('this', this);
        if (!statusUpdateIntervalStarted) {
            statusUpdateIntervalStarted = true;
            const f = () => {
                this.statusUpdate().finally(() => {
                    setTimeout(() => {
                        f();
                    }, STATUS_DELAY)
                })
            };
            f();
        }
    },

    startNetworkStateListeners: function () {
        const doObjectSearchDebounced = _.debounce(doObjectSearch, 500);
        observe(state.goto.object_search, 'search_txt', () => {
            doObjectSearchDebounced();
        });
        const doLocationSearchDebounced = _.debounce(doLocationSearch, 500);
        observe(state.location, 'city_search', () => {
            doLocationSearchDebounced();
        });

        ['north', 'south', 'east', 'west'].forEach(observeManualDirection);
        observe(state.goto.coorddialog, 'radeg', () => {
            updateCoordDialogMissing();
        });
        observe(state.goto.coorddialog, 'decdeg', () => {
            updateCoordDialogMissing();
        });
        observe(state.goto.coorddialog, 'altdeg', () => {
            updateCoordDialogMissing();
        });
        observe(state.goto.coorddialog, 'azdeg', () => {
            updateCoordDialogMissing();
        });

        observe(state.status, 'slewing', () => {
            if (state.status.slewing) {
                state.goto.slewing = false;
            }
        });
        observe(state.status, 'alert', () => {
            if (state.status.alert) {
                console.error('Alert Errot: ', state.status.alert);
                state.snack_bar = 'Error: ' + state.status.alert;
                state.snack_bar_error = true;
            }
        });

    },

    getAltitudeData: function (ra, dec, alt, az) {
        const now = new Date();
        let times;
        const timesD = [];
        for (let h = 0; h < 8; h++) {
            for (let m = 0; m < 60; m += 10) {
                timesD.push(new Date(now.getTime() + 1000 * (h * 60 * 60 + 60 * m)));
                times = timesD.map(x => x.toISOString())
            }
        }
        return fetch('/api/altitude_data', {
            method: 'post',
            body: JSON.stringify({times: times, ra: ra, dec: dec, alt: alt, az: az}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.json().then((v) => {
                const ret = [];
                for (let i = 0; i < v.length; i++) {
                    const v2 = v[i];
                    const d = Formatting.dateHourMinuteStr(timesD[i]);
                    ret.push({time: d, alt: v2});
                }
                return ret;
            });
        }).catch((e) => {
            state.snack_bar = 'Error: Failed to get altitude data';
            state.snack_bar_error = true;
            throw e;
        });

    },

    cancelSlew() {
        return fetch('/api/slewto', {
            method: 'delete'
        }).then(handleFetchError).catch((e) => {
            state.snack_bar = 'Error: Failed to cancel slew';
            state.snack_bar_error = true;
            return e;
        });
    },

    slewTo(coord) {
        state.goto.slewing = true;
        if (coord.ra) {
            state.goto.slewingtype = 'radec';
        } else {
            state.goto.slewingtype = 'altaz';
        }
        setTimeout(() => {
            state.goto.slewing = false;
        }, 3000);
        //TODO: Steps
        if (coord.ra) {
            state.goto.slewingdialog.target.ra = coord.ra;
            state.goto.slewingdialog.target.dec = coord.dec;
            state.goto.slewingdialog.target.alt = null;
            state.goto.slewingdialog.target.az = null;
        } else if (coord.alt) {
            state.goto.slewingdialog.target.ra = null;
            state.goto.slewingdialog.target.dec = null;
            state.goto.slewingdialog.target.alt = coord.alt;
            state.goto.slewingdialog.target.az = coord.az;
        }
        return fetch('/api/slewto', {
            method: 'put',
            body: JSON.stringify(coord),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).catch((e) => {
            state.goto.slewing = false;
            state.snack_bar = 'Error: ' + e.message;
            state.snack_bar_error = true;
            throw e;
        });
    },

    sync(coord) {
        state.goto.syncing = true;
        return fetch('/api/sync', {
            method: 'put',
            body: JSON.stringify(coord),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            state.snack_bar = 'Synced';
            state.snack_bar_error = false;
            return response.json();
        }).catch((e) => {
            state.snack_bar = 'Error: Failed to sync.';
            state.snack_bar_error = true;
            throw e;
        }).finally(() => {
            state.goto.syncing = false;
        });
    },
    park() {
        state.goto.slewing = true;
        state.goto.slewingtype = 'park';
        setTimeout(() => {
            state.goto.slewing = false;
        }, 3000);
        return fetch('/api/park', {
            method: 'put'
        }).then(handleFetchError).catch((e) => {
            state.snack_bar = 'Error: failed to park';
            state.snack_bar_error = true;
            return e;
        });
    },
    fetchSettings() {
        state.advancedSettings.fetching = true;
        return fetch('/api/settings').then(handleFetchError).then((response) => {
            return response.json().then((d) => {
                state.location_presets.replace(d.location_presets);
                state.location_set = d.location;
                state.network.ssid = d.network.ssid;
                state.network.wpa2key = d.network.wpa2key;
                state.network.channel = d.network.channel;
                state.slewlimit.enabled = d.horizon_limit_enabled;
                state.slewlimit.greater_than = d.horizon_limit_dec.greater_than;
                state.slewlimit.less_than = d.horizon_limit_dec.less_than;
                state.slewlimit.model = d.pointing_model;
                state.misc.encoder_logging = d.encoder_logging;
                for (const key of Object.keys(d)) {
                    if (typeof d[key] === 'object') {
                        console.log('=== micro object' + key);
                        for (const key2 of Object.keys(d[key])) {
                            if (state.advancedSettings.hasOwnProperty(key2)) {
                                console.log('==== ' + key2, d[key][key2]);
                                state.advancedSettings[key2] = d[key][key2];
                            }
                        }
                    } else {
                        if (state.advancedSettings.hasOwnProperty(key)) {
                            state.advancedSettings[key] = d[key];
                        }
                    }
                }
                state.advancedSettings.fetching = false;
                return d;
            });
        }).catch((e) => {
            state.snack_bar = 'Error: Failed to get settings';
            state.snack_bar_error = true;
            throw e;
        });
    },
    saveSettings(settings) {
        return fetch('/api/settings', {
            method: 'put',
            body: JSON.stringify(settings),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            });
        }).catch((e) => {
            state.snack_bar = 'Error: failed to save settings';
            state.snack_bar_error = true;
            return e;
        });
    },
    setParkPosition() {
        return fetch('/api/set_park_position', {
            method: 'put'
        }).then(handleFetchError).then((response) => {
            return response.text().then((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            });
        }).catch((e) => {
            state.snack_bar = 'Error: Failed setting park position';
            state.snack_bar_error = true;
            return e;
        });
    },
    uploadFirmware(file) {
        const formData = new FormData();
        formData.append('file', file);
        return fetch('/api/firmware_update', {
            method: 'post',
            body: formData
        }).then(handleFetchError).then(() => {
            setTimeout(function () {
                location.reload(true);
            }, 50000)
        }).catch((e) => {
            state.snack_bar = 'Error: Failed to upload firmware';
            state.snack_bar_error = true;
            return e;
        });
    },
    toggleTracking(track) {
        let url = '/api/start_tracking';
        if (!track) {
            url = '/api/stop_tracking'
        }
        return fetch(url, {
            method: 'put'
        }).then(handleFetchError).then(() => {
            // Just to beat the next status update
            state.status.tracking = track;
        });
    },
    addLocationPreset(name, lat, long, elevation) {
        return fetch('/api/location_preset', {
            method: 'post',
            body: JSON.stringify({name: name, lat: lat, long: long, elevation: elevation}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            });
        });
    },
    delLocationPreset(index) {
        return fetch('/api/location_preset', {
            method: 'delete',
            body: JSON.stringify({index: index}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            });
        });
    },
    setLocation(name, lat, long, elevation) {
        return fetch('/api/set_location', {
            method: 'put',
            body: JSON.stringify({name: name, lat: lat, long: long, elevation: elevation}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            });
        }).catch((e) => {
            state.snack_bar = 'Error: Failed to set location';
            state.snack_bar_error = true;
            throw e;
        });
    },
    setTime() {
        return fetch('/api/set_time', {
            method: 'put',
            body: JSON.stringify({time: new Date().toISOString()}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            });
        }).catch((e) => {
            state.snack_bar = 'Error: Failed to set time';
            state.snack_bar_error = true;
            throw e;
        });
    },
    fetchWifiScan() {
        return fetch('/api/wifi_scan').then(handleFetchError).then((response) => {
            return response.json().then((d) => {
                state.network.wifi_scan.aps.replace(d.aps);
                state.network.wifi_scan.connected.ssid = d.connected.ssid;
                state.network.wifi_scan.connected.mac = d.connected.mac;
                return d;
            })
        });
    },
    fetchKnownWifi() {
        return fetch('/api/wifi_known').then(handleFetchError).then((response) => {
            return response.json().then((d) => {
                state.network.wifi_known.replace(d);
                return d;
            })
        });
    },
    setWAP(ssid, wpa2key, channel) {
        return fetch('/api/settings_network_wifi', {
            method: 'put',
            body: JSON.stringify({ssid: ssid, wpa2key: wpa2key, channel: channel}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            });
        }).catch((e) => {
            state.snack_bar = 'Error: Failed to save';
            state.snack_bar_error = true;
            throw e;
        });
    },
    deleteKnown(ssid, mac) {
        return fetch('/api/wifi_connect', {
            method: 'delete',
            body: JSON.stringify({ssid: ssid, mac: mac}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            });
        }).catch((e) => {
            state.snack_bar = 'Error: Failed to delete';
            state.snack_bar_error = true;
            throw e;
        });
    },
    setWifiConnect(ssid, mac, known, open, password) {
        const req = {ssid: ssid, mac: mac, known: known, open: open, psk: password};
        return fetch('/api/wifi_connect', {
            method: 'post',
            body: JSON.stringify(req),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            });
        });
    },
    setSlewSettings(slewLimitEnabled, dec_greater_than, dec_less_than) {
        const req = {
            horizon_limit_enabled: slewLimitEnabled,
            dec_greater_than: dec_greater_than,
            dec_less_than: dec_less_than
        };
        return fetch('/api/settings_horizon_limit', {
            method: 'put',
            body: JSON.stringify(req),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            });
        }).catch((e) => {
            state.snack_bar = 'Error: Failed to save slew settings';
            state.snack_bar_error = true;
            throw e;
        });
    },
    setPointingModel(model) {
        return fetch('/api/sync', {
            method: 'post',
            body: JSON.stringify({model: model}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            });
        }).catch((e) => {
            state.snack_bar = 'Error: Failed to save slew settings';
            state.snack_bar_error = true;
            throw e;
        });
    },
    clearLog(name) {
        return fetch('/api/logger', {
            method: 'delete',
            body: JSON.stringify({name: name}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            });
        });
    },
    toggleLog(name, enabled) {
        return fetch('/api/logger', {
            method: 'put',
            body: JSON.stringify({name: name, enabled: enabled}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            });
        });
    },
    getLogData(name) {
        if (name === 'encoder') {
            return fetch('/api/logger?name=encoder&ts=' + (new Date().getTime()), {}).then(handleFetchError).then((response) => {
                return response.text().then((t) => {
                    //console.log(t)
                    return new Promise((resolve, reject) => {
                        Papa.parse(t, {
                            header: true,
                            fastMode: true,
                            worker: true,
                            skipEmptyLines: true,
                            complete: (results, file) => {
                                resolve(results.data);
                                console.log('test ', results, file);
                            }
                        });
                    });
                });
            });
        }
    }

};

export default APIHelp;
