import {observable, toJS} from "mobx";


const state = observable({
    page: 'manual',
    topTabs: 'manual',
    coordDisplay: 'radec',
    fatal_error: null,
    status: {
        alt: null,
        az: null,
        de: null,
        dec: null,
        dep: null,
        di: null,
        dp: null,
        ds: null,
        hostname: null,
        ra: null,
        re: null,
        rep: null,
        ri: null,
        rp: null,
        rs: null,
        slewing: false,
        started_parked: false,
        synced: false,
        time: null,
        time_been_set: false,
        tracking: true
    },
    goto: {
        option: 'object_search',
        object_search: {
            coord_display: 'radec',
            searching: false,
            search_txt: null,
            results: []
        },
        objectdialog: {
            shown: false,
            name: 'Object Name',
            radeg: null,
            decdeg: null,
            graphdata: [],
            ra: null,
            dec: null,
            alt: null,
            az: null,
            size: null,
            mag: null
        },
        coorddialog: {
            shown: false,
            ra: '04h21m44s',
            dec: '34d12\'23"',
            alt: '45d32\'12"',
            az: '120d43\'22"',
        },
        coordinates: {
            type: 'radec',
            ra: {h: null, m: null, s: null},
            ra_error: {h: null, m: null, s: null},
            dec: {d: null, m: null, s: null},
            dec_error: {d: null, m: null, s: null},
            alt: {d: null, m: null, s: null},
            alt_error: {d: null, m: null, s: null},
            az: {d: null, m: null, s: null},
            az_error: {d: null, m: null, s: null}
        }
    },
    advancedSettings: {
        ra_track_rate: 0,
        ra_ticks_per_degree: 0,
        dec_ticks_per_degree: 0,
        use_encoders: false,
        limit_encoder_step_fillin: false,
        ra_encoder_pulse_per_degree: 0,
        dec_encoder_pulse_per_degree: 0,
        ra_direction: 1,
        dec_direction: 1,
        ra_guide_rate: 0,
        ra_slew_fastest: 0,
        ra_slew_faster: 0,
        ra_slew_medium: 0,
        ra_slew_slower: 0,
        ra_slew_slowest: 0,
        dec_guide_rate: 0,
        dec_slew_fastest: 0,
        dec_slew_faster: 0,
        dec_slew_medium: 0,
        dec_slew_slower: 0,
        dec_slew_slowest: 0
    },
    location: {
        new_step: null,
        option: 'city_search',
        city_search: '',
        coord_lat: null,
        coord_lat_error: null,
        coord_long: null,
        coord_long_error: null,
        coord_elevation: null,
        coord_elevation_error: null,
        name: null,
        name_error: null
    },
    slewlimit: {
        never_below_horizon: true,
        greater_than: -90.0,
        less_than: 90.0
    }
});


window.debugState = state;
window.debugStateJS = function () {
    return toJS(state);
};

export default state;