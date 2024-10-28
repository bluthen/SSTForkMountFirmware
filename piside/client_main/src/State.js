import {observable, toJS} from "mobx";
import {v4 as uuidv4} from 'uuid';


const state = observable({
    client_id: uuidv4(),
    page: 'manual',
    topTabs: 'manual',
    coordDisplay: 'icrs',
    fatal_error: null,
    color_scheme: 'default',
    version: {version: "", version_date: ""},
    manual: {
        speed: 'fastest',
        directions: {north: false, south: false, east: false, west: false}
    },
    misc: {
        encoder_logging: false,
        calibration_logging: false,
        debug_options: false
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
        hadec_ha: null,
        hadec_dec: null,
        hostname: null,
        icrs_dec: null,
        icrs_ra: null,
        ra: null,
        re: null,
        rep: null,
        ri: null,
        rp: null,
        rs: null,
        slewing: false,
        started_parked: false,
        synced: false,
        sidereal_time: null,
        tete_dec: null,
        tete_ra: null,
        time: null,
        tracking: true,
        handpad: false,
        last_target: {ra: null, dec: null, ha: null, alt: null, az: null, frame: null, parking: false},
        cpustats: {tempc: null, tempf: null, load_percent: null, memory_percent_usage: null}
    },
    goto: {
        slewing: false,
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
            wanted_coord: null,
            all_frames: null,
            size: null,
            mag: null
        },
        coorddialog: {
            shown: false,
            wanted_coord: null,
            all_frames: null
        },
        coordinates: {
            frame: 'icrs',
            ha: {h: null, m: null, s: null},
            ha_error: {h: null, m: null, s: null},
            ra: {h: null, m: null, s: null},
            ra_error: {h: null, m: null, s: null},
            dec: {d: null, m: null, s: null},
            dec_error: {d: null, m: null, s: null},
            alt: {d: null, m: null, s: null},
            alt_error: {d: null, m: null, s: null},
            az: {d: null, m: null, s: null},
            az_error: {d: null, m: null, s: null}
        },
        steps: {
            ra: null,
            ra_error: null,
            dec: null,
            dec_error: null
        },
        slewingdialog: {
            frame: null,
            target: null
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
        dec_slew_slowest: 0,
        ra_run_current: 0,
        dec_run_current: 0,
        ra_med_current: 0,
        ra_med_current_threshold: 0,
        dec_med_current: 0,
        dec_med_current_threshold: 0,
        ra_hold_current: 0,
        dec_hold_current: 0,
        ra_backlash: 0,
        ra_backlash_speed: 0,
        dec_backlash: 0,
        dec_backlash_speed: 0
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
        model: null,
        model_points: 3,
        model_remember: false
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
    updateDialog: {timer: null, show: false},
    snack_bar: null,
    snack_bar_error: false
});


window.debugState = state;
window.debugStateJS = function () {
    return toJS(state);
};

export default state;
