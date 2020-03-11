import {observable, toJS} from "mobx";
import uuidv4 from 'uuid/v4';


const state = observable({
    client_id: uuidv4(),
    page: 'manual',
    topTabs: 'manual',
    coordDisplay: 'radec',
    fatal_error: null,
    manual: {
        speed: 'fastest',
        directions: {north: false, south: false, east: false, west: false}
    },
    misc: {
        encoder_logging: false,
        calibration_logging: false
    },
    status: {
        alert: null,
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
        slewing: false,
        slewingtype: 'radec',
        syncing: false,
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
            radeg: null,
            decdeg: null,
            altdeg: null,
            azdeg: null
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
        },
        slewingdialog: {
            target: {
                ra: null,
                dec: null,
                alt: null,
                az: null
            },
            start: {
                ra: null,
                dec: null,
                alt: null,
                az: null
            }
        }
    },
    advancedSettings: {
        fetching: false,
        ra_track_rate: 0,
        ra_ticks_per_degree: 0,
        dec_ticks_per_degree: 0,
        use_encoders: false,
        limit_encoder_step_fillin: false,
        ra_encoder_pulse_per_degree: 0,
        dec_encoder_pulse_per_degree: 0,
        ra_direction: 1,
        dec_direction: 1,
        ra_disable: 0,
        dec_disable: 0,
        ra_use_encoder: 0,
        dec_use_encoder: 0,
        ra_guide_rate: 0,
        dec_accel_tpss: 0,
        ra_accel_tpss: 0,
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
    calibrationLogs: [],
    calibrationTable: {
        correction_factor: 70,
        ra_ticks_per_degree: 0,
        dec_ticks_per_degree: 0,
        ra_encoder_pulse_per_degree: 0,
        dec_encoder_pulse_per_degree: 0,
        mean_percent_ra: 0,
        mean_percent_dec: 0,
        table_data: [],
        table_select: [],
        select_all: false
    },
    location_presets: [],
    location_set: {name: 'Unknown', lat: 0, long: 0, elevation: 0},
    location: {
        new_step: null,
        option: 'city_search',
        city_search: '',
        city_search_results: [],
        city_searching: false,
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
        enabled: true,
        greater_than: -90.0,
        greater_than_error: null,
        less_than: 90.0,
        less_than_error: null,
        model: null
    },
    network: {
        ssid: null,
        wpa2key: null,
        channel: 1,
        wifi_scan: {aps: [], connected: {mac: null, ssid: null}},
        wifi_known: [],
        password_dialog: {
            shown: false,
            ssid: null,
            mac: null,
            password: null,
            password_error: null
        }
    },
    encoderGraph: {
        left: ['step_ra', 'enc_ra', 'step_dec', 'enc_dec'],
        hide: [],
        right: ['ra_over_raenc', 'dec_over_decenc']
    },
    snack_bar: null,
    snack_bar_error: false
});


window.debugState = state;
window.debugStateJS = function () {
    return toJS(state);
};

export default state;