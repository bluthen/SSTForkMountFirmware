import React from "react";
import state from './State';
import TextField from '@material-ui/core/TextField';
import Grid from '@material-ui/core/Grid';
import InputAdornment from '@material-ui/core/InputAdornment';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Checkbox from '@material-ui/core/Checkbox';
import Button from '@material-ui/core/Button';


const settings_map = {
    ra_direction: {display: 'RA Reverse', type: 'boolean', value: false, map: {false: 1, true: -1}},
    dec_direction: {display: 'DEC Reverse', type: 'boolean', value: false, map: {false: 1, true: -1}},
    ra_track_rate: {display: 'Tracking', type: 'number', value: 0, min: 0, endAdornment: 'Steps/s'},
    ra_ticks_per_degree: {display: 'RA Scale', type: 'number', value: 0, min: 0, endAdornment: 'Steps/Degree'},
    dec_ticks_per_degree: {display: 'DEC', type: 'number', value: 0, min: 0, endAdornment: 'Steps/Degree'},

    use_encoders: {display: 'Use Encoders', type: 'boolean', value: false},
    limit_encoder_step_fillin: {display: 'Limit Encoder Step Fillin', type: 'boolean', value: false},
    ra_encoder_pulse_per_degree: {
        display: 'RA Encoder Scale',
        type: 'number',
        value: 0,
        min: 0,
        endAdornment: 'pulse/degree'
    },
    dec_encoder_pulse_per_degree: {
        display: 'DEC Encoder Scale',
        type: 'number',
        value: 0,
        min: 0,
        endAdornment: 'pulse/degree'
    },

    ra_guide_rate: {display: 'RA Guide', type: 'number', value: 0, min: 0, endAdornment: 'Steps/s'},
    ra_slew_fastest: {display: 'RA Max Slew', type: 'number', value: 0, min: 0, endAdornment: 'Steps/s'},
    ra_slew_faster: {display: 'RA Fast Slew', type: 'number', value: 0, min: 0, endAdornment: 'Steps/s'},
    ra_slew_medium: {display: 'RA Medium Slew', type: 'number', value: 0, min: 0, endAdornment: 'Steps/s'},
    ra_slew_slower: {display: 'RA Slow Slew', type: 'number', value: 0, min: 0, endAdornment: 'Steps/s'},
    ra_slew_slowest: {display: 'RA Slowest', type: 'number', value: 0, min: 0, endAdornment: 'Steps/s'},
    dec_guide_rate: {display: 'DEC Guide', type: 'number', value: 0, min: 0, endAdornment: 'Steps/s'},
    dec_slew_fastest: {display: 'DEC Max Slew', type: 'number', value: 0, min: 0, endAdornment: 'Steps/s'},
    dec_slew_faster: {display: 'DEC Fast Slew', type: 'number', value: 0, min: 0, endAdornment: 'Steps/s'},
    dec_slew_medium: {display: 'DEC Medium Slew', type: 'number', value: 0, min: 0, endAdornment: 'Steps/s'},
    dec_slew_slower: {display: 'DEC Slow Slew', type: 'number', value: 0, min: 0, endAdornment: 'Steps/s'},
    dec_slew_slowest: {display: 'DEC Slowest Slew', type: 'number', value: 0, min: 0, endAdornment: 'Steps/s'}
};


class AdvancedSettings extends React.Component {
    render() {
        console.log('whats the problem?');
        const settings = [];
        for (let key in settings_map) {
            console.log(key);
            if (settings_map[key].type === 'boolean') {
                settings.push(<Grid item xs={4}><FormControlLabel
                    control={
                        <Checkbox
                            value={key}
                            color="primary"
                        />
                    }
                    label={settings_map[key].display}
                /></Grid>);
            } else {
                settings.push(<Grid item xs={4}><TextField label={settings_map[key].display} key={key}
                                                           type={settings_map[key].type} inputProps={{
                    min: settings_map[key].min,
                    max: settings_map[key].max,
                    step: settings_map[key].step
                }} InputProps={{
                    endAdornment: <InputAdornment position="end">{settings_map[key].endAdornment}</InputAdornment>
                }}/></Grid>);
            }
        }
        return <Grid container spacing={3}>
            <Grid item xs={12} style={{textAlign: "center", paddingTop: '3ex'}}>
                <Button color="primary" variant="contained">Set Park Position</Button>
            </Grid>
            {settings}
            <Grid item xs={12} style={{textAlign: "center"}}>
                <Button color="primary" variant="contained">Save</Button>
            </Grid>
        </Grid>;
    }
}

export default AdvancedSettings;
