import React from "react";
import state from './State';
import {observer} from "mobx-react"
import TextField from '@material-ui/core/TextField';
import Typography from '@material-ui/core/Typography';
import Grid from '@material-ui/core/Grid';
import InputAdornment from '@material-ui/core/InputAdornment';
import InputLabel from '@material-ui/core/InputLabel';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Checkbox from '@material-ui/core/Checkbox';
import Button from '@material-ui/core/Button';



import uuidv4 from 'uuid/v4';

@observer
class SlewLimitsSettings extends React.Component {
    constructor(props) {
        super(props);
        this.uuid = uuidv4()
    }

    onGreaterThanChange(e) {
        let v = parseFloat(e.currentTarget.value);
        if (isNaN(v)) {
            v = '';
        }
        if (v > 90) {
            v = 90;
        }
        if (v < -90) {
            v = -90
        }
        state.slewlimit.greater_than = v;
    }

    onLessThanChange(e) {
        let v = parseFloat(e.currentTarget.value);
        if (isNaN(v)) {
            v = '';
        }
        if (v > 90) {
            v = 90;
        }
        if (v < -90) {
            v = -90
        }
        state.slewlimit.less_than = v;
    }

    onSlewBelowHorizonChange(e) {
        let v = e.currentTarget.checked;
        state.slewlimit.enabled = v;
    }

    handleSaveClicked() {
        let gt = parseFloat(state.slewlimit.greater_than);
        let lt = parseFloat(state.slewlimit.less_than);
        if (isNaN(gt)) {
            state.slewlimit.greater_than_error = 'Required';
        } else {
            state.slewlimit.greater_than_error = null;
        }
        if (isNaN(lt)) {
            state.slewlimit.less_than_error = 'Required';
        } else {
            state.slewlimit.less_than_error = null;
        }
        if (state.slewlimit.less_than_error ||  state.slewlimit.greater_than_error) {
            return;
        }

    }

    render() {
        return <Grid container spacing={2}>
            <Grid item xs={12}>
                <h2>Horizon</h2>
            </Grid>
            <Grid item xs={12}>
                <FormControlLabel
                    control={
                        <Checkbox
                            color="primary"
                            onChange={this.onSlewBelowHorizonChange}
                            checked={state.slewlimit.enabled}
                        />
                    }
                    label="Enable Slew Limits"/>
            </Grid>
            <Grid item xs={12}>
                <h2>Allowed Declination</h2>
            </Grid>
            <Grid item xs={3}>
                <InputLabel htmlFor={this.uuid + '_greaterthan'}>Greater than</InputLabel></Grid>
            <Grid item xs={3}>
                <TextField label={state.slewlimit.greater_than_error} error={!!state.slewlimit.greater_than_error} value={state.slewlimit.greater_than} id={this.uuid + '_greaterthan'}
                           onChange={this.onGreaterThanChange}
                           type="number" inputProps={{min: -90, max: 90}}
                           InputProps={{
                               endAdornment: <InputAdornment position="end">&deg;</InputAdornment>,
                           }}/></Grid>
            <Grid item xs={3}>
                <InputLabel>Less than</InputLabel>
            </Grid>
            <Grid item xs={3}>
                <TextField id={this.uuid + '_lessthan'} label={state.slewlimit.less_than_error} error={!!state.slewlimit.less_than_error} value={state.slewlimit.less_than}
                           onChange={this.onLessThanChange}
                           type="number" inputProps={{min: -90, max: 90}}
                           InputProps={{
                               endAdornment: <InputAdornment position="end">&deg;</InputAdornment>,
                           }}/>
            </Grid>
            <Grid item xs={12} style={{textAlign: "center"}}>
                <Button color="primary" variant="contained" onClick={this.handleSaveClicked}>Save</Button>
            </Grid>
        </Grid>
    }
}

export default SlewLimitsSettings;