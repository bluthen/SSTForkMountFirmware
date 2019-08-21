import {observable, toJS} from "mobx";


const state = observable({
    page: 'manual',
    topTabs: 'manual',
    coordDisplay: 'radec',
    goto: {
        option: 'object_search',
        object_search: {},
        coordinates: {type: 'radec'}
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
    }
});


window.debugState = state;
window.debugStateJS = function() {
  return toJS(state);
};

export default state;