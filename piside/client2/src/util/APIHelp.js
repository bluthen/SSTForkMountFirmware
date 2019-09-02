import state from '../State';
import {observe} from "mobx";
import _ from 'lodash';
import Formating from './Formating';


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
                state.goto.object_search.results = d.planets.concat(d.dso).concat(d.stars);
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

let statusUpdateIntervalStarted = false;
const STATUS_DELAY = 2000;

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
    },

    getAltitudeData: function (ra, dec, alt, az) {
        const now = new Date();
        let times;
        const timesD = [];
        for (let h = 0; h < 8; h++) {
            for (let m = 0; m < 60; m += 10) {
                timesD.push(new Date(now.getTime() + 1000 * (h * 60 * 60 + 60*m)));
                times = timesD.map(x=>x.toISOString())
            }
        }
        return fetch('/api/altitude_data', {
            method: 'post',
            body: JSON.stringify({times: times, ra: ra, dec: dec, alt: alt, az: az}),
            headers:{
                'Content-Type': 'application/json'
            }
        }).then((response) => {
            if (response.ok) {
                return response.json().then((v)=>{
                    const ret = [];
                    for(let i = 0; i < v.length; i++) {
                        const v2 = v[i];
                        const d = Formating.dateHourMinuteStr(timesD[i]);
                        ret.push({time: d, alt: v2});
                    }
                    return ret;
                });
            } else {
                return new Error('Failed to get altitude data: '+response.status);
            }
        })

    }
};

export default APIHelp;