import state from '../State';
import {observe} from "mobx";
import _ from 'lodash';
import Formatting from './Formatting';
import Papa from 'papaparse';
import {action as mobxaction, runInAction} from 'mobx';


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
    return fetch('/api/status?client_id=' + state.client_id).then(handleFetchError).then((response) => {
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
    runInAction(()=> {
        state.goto.object_search.searching = true;
    });
    return fetch('/api/search_object?search=' + encodeURIComponent(t)).then(handleFetchError).then((response) => {
        runInAction(()=>{
            state.goto.object_search.searching = false;
        });
        if (sc !== searchCounter) {
            return;
        }
        return response.json().then(mobxaction((d) => {
            state.goto.object_search.results.replace(d.planets.concat(d.dso).concat(d.stars));
        }));
    }).catch(mobxaction((e) => {
        state.goto.object_search.searching = false;
        state.goto.object_search.results.replace([]);
        state.snack_bar_error = true;
        state.snack_bar = 'Error: Failed to get search results';
        throw e;
    }));
}, 500);

const doLocationSearch = _.debounce(function () {
    const t = state.location.city_search;
    if (t === null || !t.trim()) {
        return;
    }
    searchCounter++;
    let sc = searchCounter;
    runInAction(()=> {
        state.location.city_searching = true;
    });
    return fetch('/api/search_location?search=' + encodeURIComponent(t)).then(handleFetchError).then((response) => {
        state.location.city_searching = false;
        if (sc !== searchCounter) {
            return;
        }
        return response.json().then(mobxaction((d) => {
            state.location.city_search_results.replace(d);
        }));
    }).catch(mobxaction((e) => {
        state.location.city_searching = false;
        state.location.city_search_results.replace([]);
        state.snack_bar_error = true;
        state.snack_bar = 'Error: Failed to get search results';
        throw e;
    }));
}, 500);

let statusUpdateIntervalStarted = false;
let settingsUpdateIntervalStarted = false;
const STATUS_DELAY = 1000;
const SETTINGS_UPDATE_DELAY = 15000;

const dirMap = {north: 'up', south: 'down', east: 'right', west: 'left'};
// const oppositeMap = {'left': 'right', 'right': 'left', 'up': 'down', 'down': 'up'};


function sendManualRequest(speed, direction) {
    return fetch('/api/manual_control', {
        method: 'post',
        body: JSON.stringify({speed: speed, direction: direction, client_id: state.client_id}),
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

function getCordConversions(wanted_coord) {
    if (wanted_coord) {
        return fetch('/api/convert_coord', {
            method: 'post',
            body: JSON.stringify(wanted_coord),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.json();
        });
    } else {
        return Promise.resolve(null);
    }
}


const APIHelp = {
    statusUpdate: function () {
        return getStatus().then(mobxaction((s) => {
            Object.keys(s).forEach((key) => {
                if (state.status[key] !== s[key]) {
                    state.status[key] = s[key];
                }
            });
        })).catch(mobxaction((e) => {
            console.error('Failed to get status.', e);
            state.snack_bar = 'Error: Failed to get status, check network';
            state.snack_bar_error = true;
        }));
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

    startSettingsUpdateInterval: function () {
        if (!settingsUpdateIntervalStarted) {
            settingsUpdateIntervalStarted = true;
            const f = () => {
                if (state.page !== 'advancedSettings') {
                    this.fetchSettings().finally(() => {
                        setTimeout(() => {
                            f();
                        }, SETTINGS_UPDATE_DELAY)
                    });
                } else {
                    setTimeout(() => {
                        f();
                    }, SETTINGS_UPDATE_DELAY)
                }
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
        observe(state.goto.coorddialog, 'wanted_coord', mobxaction(async () => {
            state.goto.coorddialog.all_frames = await getCordConversions(state.goto.coorddialog.wanted_coord);
        }));
        observe(state.goto.objectdialog, 'wanted_coord', mobxaction(async () => {
            state.goto.objectdialog.all_frames = await getCordConversions(state.goto.objectdialog.wanted_coord);
        }));

        observe(state.status, 'slewing', mobxaction(() => {
            if (state.status.slewing) {
                state.goto.slewing = false;
            }
        }));
        observe(state.status, 'alert', mobxaction(() => {
            if (state.status.alert) {
                console.error('Alert Error: ', state.status.alert);
                state.snack_bar = 'Error: ' + state.status.alert;
                state.snack_bar_error = true;
            }
        }));
        observe(state.status, 'last_target', mobxaction(() => {
            if (state.status.slewing) {
                state.goto.slewingdialog.frame = state.status.last_target.frame;
                state.goto.slewingdialog.target = state.status.last_target;
            }
        }));
    },

    getAltitudeData: function (wanted_coord) {
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
            body: JSON.stringify({times: times, ...wanted_coord}),
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
        }).catch(mobxaction((e) => {
            state.snack_bar = 'Error: Failed to get altitude data';
            state.snack_bar_error = true;
            throw e;
        }));

    },

    cancelSlew() {
        return fetch('/api/slewto', {
            method: 'delete'
        }).then(handleFetchError).catch(mobxaction((e) => {
            state.snack_bar = 'Error: Failed to cancel slew';
            state.snack_bar_error = true;
            return e;
        }));
    },

    slewTo: mobxaction((coord) => {
        state.goto.slewing = true;
        state.goto.slewingdialog.frame = coord.frame;
        state.goto.slewingdialog.target = coord;
        setTimeout(mobxaction(() => {
            // If super fast slew maybe didn't catch it toggling.
            state.goto.slewing = false;
        }), 3000);
        //TODO: Steps
        return fetch('/api/slewto', {
            method: 'put',
            body: JSON.stringify(coord),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).catch(mobxaction((e) => {
            state.goto.slewing = false;
            state.snack_bar = 'Error: ' + e.message;
            state.snack_bar_error = true;
            throw e;
        }));
    }),

    sync: mobxaction((coord) => {
        state.goto.syncing = true;
        return fetch('/api/sync', {
            method: 'put',
            body: JSON.stringify(coord),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then(mobxaction((response) => {
            state.snack_bar = 'Synced';
            state.snack_bar_error = false;
            return response.json();
        })).catch(mobxaction((e) => {
            state.snack_bar = 'Error: Failed to sync.';
            state.snack_bar_error = true;
            throw e;
        })).finally(mobxaction(() => {
            state.goto.syncing = false;
        }));
    }),

    clearSyncPoints(index) {
        return fetch('/api/sync', {
            method: 'delete'
        }).then(handleFetchError).then((response) => {
            return response.text().then(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
        });
    },


    park: mobxaction(() => {
        state.goto.slewing = true;
        state.goto.slewingdialog.frame = 'park';
        setTimeout(mobxaction(() => {
            state.goto.slewing = false;
        }), 3000);
        return fetch('/api/park', {
            method: 'put'
        }).then(handleFetchError).catch(mobxaction((e) => {
            state.snack_bar = 'Error: failed to park';
            state.snack_bar_error = true;
            return e;
        }));
    }),
    fetchVersion() {
        return fetch('/api/version').then(handleFetchError).then((response) => {
            return response.json().then(mobxaction((d) => {
                state.version.version = d.version;
                state.version.version_date = d.version_date;
            }));
        }).catch(mobxaction((e) => {
            state.snack_bar = 'Error: Failed to get version';
            state.snack_bar_error = true;
            throw e;
        }));
    },
    fetchSettings: mobxaction(() => {
        state.advancedSettings.fetching = true;
        return fetch('/api/settings').then(handleFetchError).then((response) => {
            return response.json().then(mobxaction((d) => {
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
                state.misc.calibration_logging = d.calibration_logging;
                state.color_scheme = d.color_scheme;
                for (const key of Object.keys(d)) {
                    if (typeof d[key] === 'object') {
                        console.log('=== micro object' + key);
                        for (const key2 of Object.keys(d[key])) {
                            if (_.has(state.advancedSettings, key2)) {
                                // console.log('==== ' + key2, d[key][key2]);
                                state.advancedSettings[key2] = d[key][key2];
                            }
                        }
                    } else {
                        if (_.has(state.advancedSettings, key)) {
                            state.advancedSettings[key] = d[key];
                        }
                    }
                }
                state.advancedSettings.fetching = false;
                return d;
            }));
        }).catch(mobxaction((e) => {
            state.snack_bar = 'Error: Failed to get settings';
            state.snack_bar_error = true;
            throw e;
        }));
    }),
    saveSettings(settings) {
        return fetch('/api/settings', {
            method: 'put',
            body: JSON.stringify(settings),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
        }).catch(mobxaction((e) => {
            state.snack_bar = 'Error: failed to save settings';
            state.snack_bar_error = true;
            return e;
        }));
    },
    setParkPosition() {
        return fetch('/api/set_park_position', {
            method: 'put'
        }).then(handleFetchError).then((response) => {
            return response.text().then(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
        }).catch(mobxaction((e) => {
            state.snack_bar = 'Error: Failed setting park position';
            state.snack_bar_error = true;
            return e;
        }));
    },
    uploadFirmware(file) {
        const formData = new FormData();
        formData.append('file', file);
        return fetch('/api/firmware_update', {
            method: 'post',
            body: formData
        }).then(handleFetchError).then(mobxaction(() => {
            state.updateDialog.timer = 50;
            const to = function () {
                setTimeout( mobxaction(() => {
                    state.updateDialog.timer = state.updateDialog.timer - 1;
                    if (state.updateDialog.timer <= 0) {
                        location.reload(true);
                    } else {
                        to();
                    }
                }), 1000);
            };
            to();
        })).catch(mobxaction((e) => {
            state.snack_bar = 'Error: Failed to upload firmware';
            state.snack_bar_error = true;
            return e;
        }));
    },
    uploadSettings(file) {
        const formData = new FormData();
        formData.append('file', file);
        return fetch('/api/settings_dl', {
            method: 'post',
            body: formData
        }).then(handleFetchError).then(mobxaction(() => {
            state.updateDialog.timer = 50;
            const to = function () {
                setTimeout(mobxaction(() => {
                    state.updateDialog.timer = state.updateDialog.timer - 1;
                    if (state.updateDialog.timer <= 0) {
                        location.reload(true);
                    } else {
                        to();
                    }
                }), 1000);
            };
            to();
        })).catch(mobxaction((e) => {
            state.snack_bar = 'Error: Failed to import settings';
            state.snack_bar_error = true;
            return e;
        }));
    },
    toggleTracking(track) {
        let url = '/api/start_tracking';
        if (!track) {
            url = '/api/stop_tracking'
        }
        return fetch(url, {
            method: 'put'
        }).then(handleFetchError).then(mobxaction(() => {
            // Just to beat the next status update
            state.status.tracking = track;
        }));
    },
    addLocationPreset(name, lat, long, elevation) {
        return fetch('/api/location_preset', {
            method: 'post',
            body: JSON.stringify({name: name, lat: lat, long: long, elevation: elevation}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
        });
    },
    useGPSLocation() {
        return fetch('/api/location_gps', {
            method: 'post'
        }).then(handleFetchError).then((response) => {
            return response.text().then(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
        }).catch(mobxaction((e) => {
            state.snack_bar = e.message;
            state.snack_bar_error = true;
            throw e;
        }));
    },
    delLocationPreset(index) {
        return fetch('/api/location_preset', {
            method: 'delete',
            body: JSON.stringify({index: index}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
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
            return response.text(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
        }).catch(mobxaction((e) => {
            state.snack_bar = 'Error: Failed to set location';
            state.snack_bar_error = true;
            throw e;
        }));
    },
    setTime() {
        return fetch('/api/set_time', {
            method: 'put',
            body: JSON.stringify({time: new Date().toISOString()}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
        }).catch(mobxaction((e) => {
            state.snack_bar = 'Error: Failed to set time';
            state.snack_bar_error = true;
            throw e;
        }));
    },
    fetchWifiScan() {
        return fetch('/api/wifi_scan').then(handleFetchError).then((response) => {
            return response.json().then(mobxaction((d) => {
                state.network.wifi_scan.aps.replace(d.aps);
                state.network.wifi_scan.connected.ssid = d.connected.ssid;
                state.network.wifi_scan.connected.mac = d.connected.mac;
                return d;
            }));
        });
    },
    fetchKnownWifi() {
        return fetch('/api/wifi_known').then(handleFetchError).then((response) => {
            return response.json().then(mobxaction((d) => {
                state.network.wifi_known.replace(d);
                return d;
            }));
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
            return response.text().then(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
        }).catch(mobxaction((e) => {
            state.snack_bar = 'Error: Failed to save';
            state.snack_bar_error = true;
            throw e;
        }));
    },
    deleteKnown(ssid, mac) {
        return fetch('/api/wifi_connect', {
            method: 'delete',
            body: JSON.stringify({ssid: ssid, mac: mac}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
        }).catch(mobxaction((e) => {
            state.snack_bar = 'Error: Failed to delete';
            state.snack_bar_error = true;
            throw e;
        }));
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
            return response.text().then(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
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
            return response.text().then(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
        }).catch(mobxaction((e) => {
            state.snack_bar = 'Error: Failed to save slew settings';
            state.snack_bar_error = true;
            throw e;
        }));
    },
    setPointingModel(model) {
        return fetch('/api/sync', {
            method: 'post',
            body: JSON.stringify({model: model}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
        }).catch(mobxaction((e) => {
            state.snack_bar = 'Error: Failed to save slew settings';
            state.snack_bar_error = true;
            throw e;
        }));
    },
    clearLog(name) {
        return fetch('/api/logger', {
            method: 'delete',
            body: JSON.stringify({name: name}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(handleFetchError).then((response) => {
            return response.text().then(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
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
            return response.text().then(mobxaction((t) => {
                state.snack_bar = t;
                state.snack_bar_error = false;
            }));
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
        } else if (name === 'calibration') {
            return fetch('/api/logger?name=calibration&ts=' + (new Date().getTime()), {}).then(handleFetchError).then((response) => {
                return response.json().then(mobxaction((t) => {
                    state.calibrationLogs.replace(t);
                }));
            });
        }
    },
    exportSettings() {
        location.href = '/api/settings_dl';
    }

};

export default APIHelp;
