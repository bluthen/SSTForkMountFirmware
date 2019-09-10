import state from '../State';
import {observe} from "mobx";
import _ from 'lodash';
import Formatting from './Formatting';


function getStatus() {
    return fetch('/api/status').then((response) => {
        if (response.ok) {
            return response.json();
        }
        throw new Error('Status response not okay.', response.status)
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
    return fetch('/api/search_object?search=' + encodeURIComponent(t)).then((response) => {
        state.goto.object_search.searching = false;
        if (response.ok) {
            if (sc !== searchCounter) {
                return;
            }
            response.json().then((d) => {
                state.goto.object_search.results.replace(d.planets.concat(d.dso).concat(d.stars));
            });
        } else {
            console.error('/api/search_object failed.', response.status);
        }
    }, (e) => {
        state.goto.object_search.searching = false;
        state.goto.object_search.results = [];
        console.error(e);
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
    return fetch('/api/search_location?search=' + encodeURIComponent(t)).then((response) => {
        state.location.city_searching = false;
        if (response.ok) {
            if (sc !== searchCounter) {
                return;
            }
            response.json().then((d) => {
                state.location.city_search_results.replace(d);
            });
        } else {
            console.error('/api/search_location failed.', response.status);
        }
    }, (e) => {
        state.location.city_searching = false;
        state.location.city_search_results = [];
        console.error(e);
        throw e;
    });
}, 500);

let statusUpdateIntervalStarted = false;
const STATUS_DELAY = 1000;

const dirMap = {north: 'up', south: 'down', east: 'right', west: 'left'};
const manualIntervals = {};
const oppositeMap = {'left': 'right', 'right': 'left', 'up': 'down', 'down': 'up'};


function sendManualRequest(speed, direction) {
    fetch('/api/manual_control', {
        method: 'post',
        body: JSON.stringify({speed: speed, direction: direction}),
        headers: {
            'Content-Type': 'application/json'
        }
    })
}


function manualActive(speed, direction) {
    //If we are already going opposite direction then ignore.
    if (manualIntervals.hasOwnProperty(oppositeMap[direction])) {
        return;
    }
    console.log('Pressing: ' + direction);
    if (manualIntervals.hasOwnProperty(direction)) {
        clearTimeout(manualIntervals[direction]);
    }
    manualIntervals[direction] = setInterval(() => {
        sendManualRequest(speed, direction)
    }, 100);
    sendManualRequest(speed, direction)
}


function manualInactive(direction) {
    if (manualIntervals.hasOwnProperty(direction)) {
        clearInterval(manualIntervals[direction]);
        delete manualIntervals[direction];
    }
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
    }
    if ((res.ra !== null && res.dec !== null && res.alt === null && res.az === null) || (res.alt !== null && res.az !== null && res.ra === null && res.dec === null)) {
        fetch('/api/convert_coord', {
            method: 'post',
            body: JSON.stringify(res),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then((response) => {
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
            state.fatal_error = 'Failed to update status, maybe network issue.';
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
        }).then((response) => {
            if (response.ok) {
                return response.json().then((v) => {
                    const ret = [];
                    for (let i = 0; i < v.length; i++) {
                        const v2 = v[i];
                        const d = Formatting.dateHourMinuteStr(timesD[i]);
                        ret.push({time: d, alt: v2});
                    }
                    return ret;
                });
            } else {
                return new Error('Failed to get altitude data: ' + response.status);
            }
        })

    },

    cancelSlew() {
        return fetch('/api/slewto', {
            method: 'delete'
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
        }).then((response) => {
            if (!response.ok) {
                return response.text().then((t) => {
                    return new Error(t);
                })
            }
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
        }).then((response) => {
            if (!response.ok) {
                return response.text().then((t) => {
                    return new Error(t);
                })
            } else {
                return response.json();
            }
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
        }).then((response) => {
            if (!response.ok) {
                return response.text().then((t) => {
                    return new Error(t);
                })
            }
        });
    },
    fetchSettings() {
        state.advancedSettings.fetching = true;
        return fetch('/api/settings').then((response) => {
            if (response.ok) {
                return response.json().then((d) => {
                    state.location_presets.replace(d.location_presets);
                    state.location_set = d.location;
                    for (const key of Object.keys(d)) {
                        if (typeof d[key] === 'object') {
                            for (const key2 of Object.keys(d[key])) {
                                if (state.advancedSettings.hasOwnProperty(key2)) {
                                    state.advancedSettings[key] = d[key][key2];
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
            }
        });
    },
    saveSettings(settings) {
        return fetch('/api/settings', {
            method: 'put',
            body: JSON.stringify(coord),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then((response) => {
           if(response.ok) {
           }
        });
    },
    setParkPosition() {
        return fetch('/api/set_park_position', {
            method: 'put'
        }).then((response) => {
            if(response.ok) {
            }
        });
    },
    uploadFirmware(file) {
        const formData = new FormData();
        formData.append('file', file);
        return fetch('/api/firmware_update', {
            method: 'post',
            body: formData
        }).then((response) => {
            if (response.ok) {
                setTimeout(function() {
                    location.reload(true);
                }, 50000)
            }
        })
    },
    toggleTracking(track) {
        const formData = new FormData();
        let url = '/api/start_tracking';
        if(!track) {
            url = '/api/stop_tracking'
        }
        return fetch(url, {
            method: 'put'
        }).then((response)=> {
            if(response.ok) {
                // Just to beat the next status update
                if(track) {
                    state.status.tracking = true;
                } else {
                    state.status.tracking = false;
                }
            }
        })
    },
    addLocationPreset(name, lat, long, elevation) {
        return fetch('/api/location_preset', {
            method: 'post',
            body: JSON.stringify({name: name, lat: lat, long: long, elevation: elevation}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then((response) => {
            if(response.ok) {
                return response.text;
            }
        });
    },
    delLocationPreset(index) {
        return fetch('/api/location_preset', {
            method: 'delete',
            body: JSON.stringify({index: index}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then((response) => {
            if(response.ok) {
                return response.text;
            }
        });
    },
    setLocation(name, lat, long, elevation) {
        return fetch('/api/set_location', {
            method: 'put',
            body: JSON.stringify({name: name, lat: lat, long: long, elevation: elevation}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then((response) => {
            if(response.ok) {
                return response.text;
            }
        });
    },
    setTime() {
        return fetch('/api/set_time', {
            method: 'put',
            body: JSON.stringify({time: new Date().toISOString()}),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then((response) => {
            if(response.ok) {
                return response.text;
            }
        });

    }

};

export default APIHelp;