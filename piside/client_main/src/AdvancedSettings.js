import React from "react";
import {observer} from "mobx-react"
import state from './State';
import TextField from '@mui/material/TextField';
import Grid from '@mui/material/Grid';
import InputAdornment from '@mui/material/InputAdornment';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import {v4 as uuidv4}  from 'uuid';
import APIHelp from './util/APIHelp';
import _ from 'lodash';


const settings_map = {
    ra_ticks_per_degree: {display: 'RA Stepper Scale', type: 'number', min: 0, endAdornment: 'Step/°'},
    dec_ticks_per_degree: {display: 'Dec Stepper Scale', type: 'number', min: 0, endAdornment: 'Step/°'},
    ra_track_rate: {display: 'RA Stepper Tracking', type: 'number', min: 0, endAdornment: 'Step/s'},
    ra_guide_rate: {display: 'RA Stepper Guide', type: 'number', min: 0, endAdornment: 'Step/s', jsonLevel: 'micro'},
    dec_guide_rate: {display: 'Dec Stepper Guide', type: 'number', min: 0, endAdornment: 'Step/s', jsonLevel: 'micro'},

    ra_accel_tpss: {
        display: 'RA Max Acceleration',
        type: 'number',
        min: 0,
        endAdornment: 'Step/s^2',
        jsonLevel: 'micro'
    },
    dec_accel_tpss: {
        display: 'Dec Max Acceleration',
        type: 'number',
        min: 0,
        endAdornment: 'Step/s^2',
        jsonLevel: 'micro'
    },

    ra_run_current: {
        display: 'RA Run Current',
        type: 'number',
        min: 0,
        endAdornment: 'mA',
        jsonLevel: 'micro'
    },
    dec_run_current: {
        display: 'Dec Run Current',
        type: 'number',
        min: 0,
        endAdornment: 'mA',
        jsonLevel: 'micro'
    },
    ra_med_current: {
        display: 'RA Medium Current',
        type: 'number',
        min: 0,
        endAdornment: 'mA',
        jsonLevel: 'micro'
    },
    ra_med_current_threshold: {
        display: 'RA Medium Threshold',
        type: 'number',
        min: 0,
        endAdornment: '<steps/s',
        jsonLevel: 'micro'
    },
    dec_med_current: {
        display: 'Dec Medium Current',
        type: 'number',
        min: 0,
        endAdornment: 'mA',
        jsonLevel: 'micro'
    },
    dec_med_current_threshold: {
        display: 'Dec Medium Threshold',
        type: 'number',
        min: 0,
        endAdornment: 'steps/s',
        jsonLevel: 'micro'
    },
    ra_hold_current: {
        display: 'RA Hold Current',
        type: 'number',
        min: 0,
        endAdornment: 'mA',
        jsonLevel: 'micro'
    },
    dec_hold_current: {
        display: 'Dec Hold Current',
        type: 'number',
        min: 0,
        endAdornment: 'mA',
        jsonLevel: 'micro'
    },

    ra_slew_fastest: {display: 'RA Max Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    ra_slew_faster: {display: 'RA Fast Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    ra_slew_medium: {display: 'RA Medium Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    ra_slew_slower: {display: 'RA Slow Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    ra_slew_slowest: {display: 'RA Slowest', type: 'number', min: 0, endAdornment: 'Step/s'},

    dec_slew_fastest: {display: 'Dec Max Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    dec_slew_faster: {display: 'Dec Fast Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    dec_slew_medium: {display: 'Dec Medium Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    dec_slew_slower: {display: 'Dec Slow Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    dec_slew_slowest: {display: 'Dec Slowest Slew', type: 'number', min: 0, endAdornment: 'Step/s'},

    ra_direction: {display: 'RA Reverse', type: 'boolean', map: {false: 1, true: -1}, jsonLevel: 'micro'},
    dec_direction: {display: 'Dec Reverse', type: 'boolean', map: {false: 1, true: -1}, jsonLevel: 'micro'},

    ra_disable: {display: 'RA Disable Motor', type: 'boolean', map: {false: 0, true: 1}, jsonLevel: 'micro'},
    dec_disable: {display: 'Dec Disable Motor', type: 'boolean', map: {false: 0, true: 1}, jsonLevel: 'micro'},

    ra_use_encoder: {display: 'Use Encoders w/RA', type: 'boolean'},
    dec_use_encoder: {display: 'Use Encoders w/Dec', type: 'boolean'},
    limit_encoder_step_fillin: {display: 'Limit Encoder Step Fill-in', type: 'boolean'},

    ra_encoder_pulse_per_degree: {
        display: 'RA Encoder Scale',
        type: 'number',
        endAdornment: 'pulse/°'
    },
    dec_encoder_pulse_per_degree: {
        display: 'Dec Encoder Scale',
        type: 'number',
        endAdornment: 'pulse/°'
    }
};

function makeOnChange(key, setting_map) {
    return (e) => {
        if (setting_map.type === 'number') {
            const v = e.currentTarget.value;
            if ((v !== '' && v !== '-' && v !== '-.') || (_.has(settings_map, 'min') && settings_map.min >= 0)) {
                state.advancedSettings[key] = parseFloat(v);
            } else {
                state.advancedSettings[key] = v;
            }
        } else if (setting_map.type === 'boolean') {
            let v = e.target.checked;
            if (setting_map.map) {
                v = setting_map.map[v];
            }
            state.advancedSettings[key] = v;
        }
    }
}

@observer
class AdvancedSettings extends React.Component {
    constructor(props) {
        super(props);
        this.uuid = uuidv4();
    }

    componentDidMount() {
        APIHelp.fetchSettings();
    }

    handleSave() {
        const resp = {};
        for (const key of Object.keys(settings_map)) {
            const jl = settings_map[key].jsonLevel;
            if (jl) {
                if (!resp[jl]) {
                    resp[jl] = {};
                }
                if (typeof state.advancedSettings[key] === 'string') {
                    resp[jl][key] = 0;
                } else {
                    resp[jl][key] = state.advancedSettings[key];
                }
            } else {
                if (typeof state.advancedSettings[key] === 'string') {
                    resp[key] = 0;
                } else {
                    resp[key] = state.advancedSettings[key];
                }
            }
        }
        APIHelp.saveSettings(resp);
    }

    render() {
        const settings = [];
        let spinner = null;
        if (state.advancedSettings.fetching) {
            spinner = <CircularProgress/>;
        } else {
            for (let key in settings_map) {
                if (settings_map[key].type === 'boolean') {
                    let checked;
                    if (settings_map[key].map) {
                        checked = settings_map[key].map[true] === state.advancedSettings[key];
                    } else {
                        checked = state.advancedSettings[key];
                    }
                    settings.push(<Grid item key={key + this.uuid} xs={4}><FormControlLabel
                        control={
                            <Checkbox
                                value={key}
                                color="primary"
                                checked={checked}
                                onChange={makeOnChange(key, settings_map[key])}
                            />
                        }
                        label={settings_map[key].display}
                    /></Grid>);
                } else {
                    settings.push(<Grid item key={key + this.uuid} xs={4}>
                        <TextField value={state.advancedSettings[key]}
                                   label={settings_map[key].display}
                                   key={key}
                                   type={settings_map[key].type}
                                   inputProps={{
                                       min: settings_map[key].min,
                                       max: settings_map[key].max,
                                       step: settings_map[key].step
                                   }} InputProps={{
                            endAdornment: <InputAdornment style={{whiteSpace: 'nowrap'}}
                                                          position="end">{settings_map[key].endAdornment}</InputAdornment>
                        }} onChange={makeOnChange(key, settings_map[key])}/>
                    </Grid>);
                }
            }
            settings.push(<Grid item key={'save' + this.uuid} xs={12} style={{textAlign: "center"}}>
                <Button color="primary" variant="contained" onClick={this.handleSave}>Save</Button>
            </Grid>);
        }
        return <Grid container spacing={3}>
            {settings}
            {spinner}
        </Grid>;
    }
}

export default AdvancedSettings;
