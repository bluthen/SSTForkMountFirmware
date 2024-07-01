import React from "react";
import state from './State';
import {observer} from "mobx-react"
import TextField from '@mui/material/TextField';
import Grid from '@mui/material/Grid';
import InputAdornment from '@mui/material/InputAdornment';
import InputLabel from '@mui/material/InputLabel';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';
import Button from '@mui/material/Button';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import APIHelp from './util/APIHelp';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';


import {v4 as uuidv4} from 'uuid';
import {action as mobxaction} from "mobx";

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

    @mobxaction
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

    handleClearPointsClicked() {
        APIHelp.clearSyncPoints();
    }

    @mobxaction
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

    @mobxaction
    handleModelChange(e) {
        state.slewlimit.model = modelMap[~~(e.target.value)];
    }

    @mobxaction
    handleSlewBelowHorizonChange(e) {
        state.slewlimit.enabled = e.currentTarget.checked;
    }

    @mobxaction
    handleModelRemember(e) {
        state.slewlimit.model_remember = e.currentTarget.checked;
    }

    @mobxaction
    handleModelPointsChange(e) {
        state.slewlimit.model_points = parseInt(e.currentTarget.value, 10);
    }

    @mobxaction
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
        APIHelp.setPointingModel(state.slewlimit.model, state.slewlimit.model_points, state.slewlimit.model_remember).then(() => {
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
            <Grid item xs={12}><h2>Pointing Model</h2></Grid>
            <Grid item xs={6}>
                <InputLabel htmlFor={this.uuid + "model-select"}>Pointing Model</InputLabel>
                <Select id={this.uuid + "model_select"} value={modelMap.indexOf(state.slewlimit.model)}
                        onChange={this.handleModelChange} name="model">
                    <MenuItem value="0">Single</MenuItem>
                    <MenuItem value="1">Buie</MenuItem>
                    <MenuItem value="2">Affine</MenuItem>
                </Select>
            </Grid>
            { (state.slewlimit.model === 'buie' || state.slewlimit.model === 'affine_all') ? <>
            <Grid item xs={6}>
                <InputLabel htmlFor={this.uuid + "model-points"}>Model Points</InputLabel>
                <TextField label={'Number of model points'} id={this.uuid + 'model-points'} value={state.slewlimit.model_points}
                           type="number" inputProps={{min: 3, max: 9999}}
                onChange={this.handleModelPointsChange}/>
            </Grid>
            <Grid item xs={12}>
                <FormControlLabel
                    control={
                        <Checkbox
                            color="primary"
                            onChange={this.handleModelRemember}
                            checked={state.slewlimit.model_remember}
                        />
                    }
                    label="Remember model"/>
            </Grid>
            </> : <Grid item xs={6}/>}
            <Grid item xs={12}>
                <Button color="primary" variant="contained" onClick={this.handleClearPointsClicked}>Clear Pointing Model</Button>
            </Grid>
            <Grid item xs={12} style={{textAlign: "center"}}>
                <Button color="primary" variant="contained" onClick={this.handleSaveClicked}>Save</Button>
            </Grid>
        </Grid>
    }
}

export default SlewLimitsSettings;