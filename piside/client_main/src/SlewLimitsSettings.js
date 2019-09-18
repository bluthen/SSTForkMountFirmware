import React from "react";
import state from './State';
import {observer} from "mobx-react"
import TextField from '@material-ui/core/TextField';
import Grid from '@material-ui/core/Grid';
import InputAdornment from '@material-ui/core/InputAdornment';
import InputLabel from '@material-ui/core/InputLabel';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Checkbox from '@material-ui/core/Checkbox';
import Button from '@material-ui/core/Button';
import OpenInNewIcon from '@material-ui/icons/OpenInNew';
import APIHelp from './util/APIHelp';
import Select from '@material-ui/core/Select';
import MenuItem from '@material-ui/core/MenuItem';


import uuidv4 from 'uuid/v4';

const modelMap = ['single', 'buie', 'affine_all'];

@observer
class SlewLimitsSettings extends React.Component {
    constructor(props) {
        super(props);
        this.uuid = uuidv4()
    }

    componentDidMount() {
        APIHelp.fetchSettings();
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

    handleLessThanChange(e) {
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

    handleModelChange(e) {
        state.slewlimit.model = modelMap[parseInt(e.target.value)];
    }

    handleSlewBelowHorizonChange(e) {
        state.slewlimit.enabled = e.currentTarget.checked;
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
        if (state.slewlimit.less_than_error || state.slewlimit.greater_than_error) {
            return;
        }
        APIHelp.setPointingModel(state.slewlimit.model).then(() => {
            APIHelp.setSlewSettings(state.slewlimit.enabled, gt, lt);
        });
    }

    handleAdvancedClicked() {
        window.open('/advanced_slew_limits/index.html', '_blank')
    }

    render() {
        return <Grid container spacing={2}>
            <Grid item xs={12}><h2>Slew Limits</h2></Grid>
            <Grid item xs={4}>
                <FormControlLabel
                    control={
                        <Checkbox
                            color="primary"
                            onChange={this.handleSlewBelowHorizonChange}
                            checked={state.slewlimit.enabled}
                        />
                    }
                    label="Enable Slew Limits"/>
            </Grid>
            <Grid item xs={8}>
                <Button color="secondary" variant="contained" onClick={this.handleAdvancedClicked}>Advanced Limits
                    Editor&nbsp;&nbsp;<OpenInNewIcon/></Button>
            </Grid>
            <Grid item xs={12}>
                <InputLabel htmlFor={this.uuid + "model-select"}>Pointing Model</InputLabel>
                <Select id={this.uuid + "model_select"} value={modelMap.indexOf(state.slewlimit.model)}
                        onChange={this.handleModelChange} name="model">
                    <MenuItem value="0">Single</MenuItem>
                    <MenuItem value="1">Buie</MenuItem>
                    <MenuItem value="2">Affine</MenuItem>
                </Select>
            </Grid>
            <Grid item xs={12}>
                <h3>Allowed Declination</h3>
            </Grid>
            <Grid item xs={3}>
                <InputLabel htmlFor={this.uuid + '_greaterthan'}>Greater than</InputLabel></Grid>
            <Grid item xs={3}>
                <TextField label={state.slewlimit.greater_than_error} error={!!state.slewlimit.greater_than_error}
                           value={state.slewlimit.greater_than} id={this.uuid + '_greaterthan'}
                           onChange={this.onGreaterThanChange}
                           type="number" inputProps={{min: -90, max: 90}}
                           InputProps={{
                               endAdornment: <InputAdornment position="end">&deg;</InputAdornment>,
                           }}/></Grid>
            <Grid item xs={3}>
                <InputLabel>Less than</InputLabel>
            </Grid>
            <Grid item xs={3}>
                <TextField id={this.uuid + '_lessthan'} label={state.slewlimit.less_than_error}
                           error={!!state.slewlimit.less_than_error} value={state.slewlimit.less_than}
                           onChange={this.handleLessThanChange}
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