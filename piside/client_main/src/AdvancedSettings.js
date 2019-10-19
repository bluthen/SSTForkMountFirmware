import React from "react";
import {observer} from "mobx-react"
import state from './State';
import TextField from '@material-ui/core/TextField';
import Grid from '@material-ui/core/Grid';
import InputAdornment from '@material-ui/core/InputAdornment';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Checkbox from '@material-ui/core/Checkbox';
import Button from '@material-ui/core/Button';
import CircularProgress from '@material-ui/core/CircularProgress';
import uuidv4 from 'uuid/v4';
import APIHelp from './util/APIHelp';


const settings_map = {
    ra_ticks_per_degree: {display: 'RA Stepper Scale', type: 'number', min: 0, endAdornment: 'Step/°'},
    dec_ticks_per_degree: {display: 'DEC Stepper Scale', type: 'number', min: 0, endAdornment: 'Step/°'},
    ra_track_rate: {display: 'RA Stepper Tracking', type: 'number', min: 0, endAdornment: 'Step/s'},
    ra_guide_rate: {display: 'RA Stepper Guide', type: 'number', min: 0, endAdornment: 'Step/s', jsonLevel: 'micro'},
    dec_guide_rate: {display: 'DEC Stepper Guide', type: 'number', min: 0, endAdornment: 'Step/s', jsonLevel: 'micro'},

    ra_accel_tpss: {
        display: 'RA Max Acceleration',
        type: 'number',
        min: 0,
        endAdornment: 'Step/s^2',
        jsonLevel: 'micro'
    },
    dec_accel_tpss: {
        display: 'DEC Max Acceleration',
        type: 'number',
        min: 0,
        endAdornment: 'Step/s^2',
        jsonLevel: 'micro'
    },


    ra_slew_fastest: {display: 'RA Max Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    ra_slew_faster: {display: 'RA Fast Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    ra_slew_medium: {display: 'RA Medium Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    ra_slew_slower: {display: 'RA Slow Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    ra_slew_slowest: {display: 'RA Slowest', type: 'number', min: 0, endAdornment: 'Step/s'},

    dec_slew_fastest: {display: 'DEC Max Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    dec_slew_faster: {display: 'DEC Fast Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    dec_slew_medium: {display: 'DEC Medium Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    dec_slew_slower: {display: 'DEC Slow Slew', type: 'number', min: 0, endAdornment: 'Step/s'},
    dec_slew_slowest: {display: 'DEC Slowest Slew', type: 'number', min: 0, endAdornment: 'Step/s'},

    ra_direction: {display: 'RA Reverse', type: 'boolean', map: {false: 1, true: -1}, jsonLevel: 'micro'},
    dec_direction: {display: 'DEC Reverse', type: 'boolean', map: {false: 1, true: -1}, jsonLevel: 'micro'},


    use_encoders: {display: 'Use Encoders', type: 'boolean'},
    limit_encoder_step_fillin: {display: 'Limit Encoder Step Fill-in', type: 'boolean'},

    ra_encoder_pulse_per_degree: {
        display: 'RA Encoder Scale',
        type: 'number',
        endAdornment: 'pulse/°'
    },
    dec_encoder_pulse_per_degree: {
        display: 'DEC Encoder Scale',
        type: 'number',
        endAdornment: 'pulse/°'
    }
};

function makeOnChange(key, setting_map) {
    return (e) => {
        if (setting_map.type === 'number') {
            const v = e.currentTarget.value;
            if ((v !== '-' && v !== '-.') || (settings_map.hasOwnProperty('min') && settings_map.min >= 0)) {
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
