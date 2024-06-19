import React from "react";
import state from './State';
import {observer} from "mobx-react";
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Grid from '@mui/material/Grid';
import TToggle from './TToggle';
import InputAdornment from '@mui/material/InputAdornment';
import Button from '@mui/material/Button';
import Formatting from './util/Formatting';
import CoordDialog from './CoordDialog';
import CalibrationTable from './CalibrationTable';
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import {action as mobxaction} from 'mobx';
import PropTypes from "prop-types";

@observer
class CoordinatesInput extends React.Component {
    constructor(props) {
        super(props);
        this.handleClick = this.handleClick.bind(this);
        this.one = React.createRef();
        this.two = React.createRef();
        this.three = React.createRef();
        this.four = React.createRef();
        this.five = React.createRef();
        this.six = React.createRef();
        this.buttonRef = React.createRef();
    }

    @mobxaction
    onCoordChange(e, coord, sub) {
        let v = e.currentTarget.value;
        //console.log('======='+v);
        //console.log(e);
        const l = v.length;
        let first = '';
        const negativeAllowed = sub.min < 0;
        let maxDigits = ~~(Math.log10(sub.max)) + 1;
        if (l > 0) {
            first = v[0];
            if (first === '-' && negativeAllowed) {
                maxDigits += 1;
            }
        }
        v = ~~v;
        if (isNaN(v)) {
            v = null;
        }
        //console.log(v, l, maxDigits, first, negativeAllowed);
        state.goto.coordinates[coord][sub.key] = v;
        if (v * 10 > sub.max || v * 10 < sub.min || l === maxDigits) {
            sub.nextRef.current.focus();
        }
        if (v === 0 && negativeAllowed && first === '-') {
            state.goto.coordinates[coord][sub.key] = '-';
            state.goto.coordinates[coord + '_error'][sub.key] = 'invalid value';
        } else if (v > sub.max || v < sub.min) {
            state.goto.coordinates[coord + '_error'][sub.key] = 'invalid value';
        } else {
            state.goto.coordinates[coord + '_error'][sub.key] = null;
        }
    }

    onSubFocus(e, ref) {
        ref.current.select();
    }

    @mobxaction
    goodClick() {
        let ra = null, dec = null, alt = null, az = null, ha = null;
        const frame = state.goto.coordinates.frame;
        if (frame === 'icrs' || frame === 'tete') {
            ra = Formatting.hmsRA2deg(state.goto.coordinates.ra.h, state.goto.coordinates.ra.m, state.goto.coordinates.ra.s);
            dec = Formatting.dmsDEC2deg(state.goto.coordinates.dec.d, state.goto.coordinates.dec.m, state.goto.coordinates.dec.s);
            state.goto.coorddialog.wanted_coord = {frame: frame, ra: ra, dec: dec};
        } else if (frame === 'hadec') {
            ha = Formatting.hmsRA2deg(state.goto.coordinates.ha.h, state.goto.coordinates.ha.m, state.goto.coordinates.ha.s);
            dec = Formatting.dmsDEC2deg(state.goto.coordinates.dec.d, state.goto.coordinates.dec.m, state.goto.coordinates.dec.s);
            state.goto.coorddialog.wanted_coord = {frame: frame, ha: ha, dec: dec};
        } else {
            alt = Formatting.dmsDEC2deg(state.goto.coordinates.alt.d, state.goto.coordinates.alt.m, state.goto.coordinates.alt.s);
            az = Formatting.dmsDEC2deg(state.goto.coordinates.az.d, state.goto.coordinates.az.m, state.goto.coordinates.az.s);
            state.goto.coorddialog.wanted_coord = {frame: frame, alt: alt, az: az};
        }
        state.goto.coorddialog.all_frames = null;
        state.goto.coorddialog.shown = true;
    }

    handleClick(e) {
        let coords;
        const frame = state.goto.coordinates.frame;
        if (frame === 'icrs' || frame === 'tete') {
            coords = {'ra': ['h', 'm', 's'], 'dec': ['d', 'm', 's']};
        } else if (frame === 'hadec') {
            coords = {'ha': ['h', 'm', 's'], 'dec': ['d', 'm', 's']};
        } else {
            coords = {'alt': ['d', 'm', 's'], 'az': ['d', 'm', 's']};
        }
        let validCoords = true;
        for (let coord in coords) {
            coords[coord].forEach((key) => {
                if (state.goto.coordinates[coord][key] === null || state.goto.coordinates[coord + '_error'][key]) {
                    validCoords = false;
                }
            });
        }
        if (validCoords) {
            this.goodClick();
        }
    }

    fieldGen(coord, subs) {
        const v1 = state.goto.coordinates[coord][subs[0].key];
        const v1_error = state.goto.coordinates[coord + '_error'][subs[0].key];
        const v2 = state.goto.coordinates[coord][subs[1].key];
        const v2_error = state.goto.coordinates[coord + '_error'][subs[1].key];
        const v3 = state.goto.coordinates[coord][subs[2].key];
        const v3_error = state.goto.coordinates[coord + '_error'][subs[2].key];

        return <>
            <Grid item xs={1}>
                {coord.toUpperCase()}
            </Grid>
            <Grid item xs={2}>
                <TextField value={v1 === null ? '' : v1} error={!!v1_error} label={v1_error} onChange={(e) => {
                    this.onCoordChange(e, coord, subs[0]);
                }} type="text" inputProps={{min: subs[0].min, max: subs[0].max, step: 1}} InputProps={{
                    endAdornment: <InputAdornment position="end">{subs[0].adornment}</InputAdornment>,
                }} inputRef={subs[0].ref} onFocus={(e) => {
                    this.onSubFocus(e, subs[0].ref)
                }}/>
            </Grid>
            <Grid item xs={2}>
                <TextField value={v2 === null ? '' : v2} error={!!v2_error} label={v2_error} onChange={(e) => {
                    this.onCoordChange(e, coord, subs[1]);
                }} type="text" inputProps={{min: subs[0].min, max: subs[1].max, step: 1}} InputProps={{
                    endAdornment: <InputAdornment position="end">{subs[1].adornment}</InputAdornment>,
                }} inputRef={subs[1].ref} onFocus={(e) => {
                    this.onSubFocus(e, subs[1].ref)
                }}/>
            </Grid>
            <Grid item xs={2}>
                <TextField value={v3 === null ? '' : v3} error={!!v3_error} label={v3_error} onChange={(e) => {
                    this.onCoordChange(e, coord, subs[2]);
                }} type="text" inputProps={{min: subs[2].min, max: subs[2].max, step: 1}} InputProps={{
                    endAdornment: <InputAdornment position="end">{subs[2].adornment}</InputAdornment>,
                }} inputRef={subs[2].ref} onFocus={(e) => {
                    this.onSubFocus(e, subs[2].ref)
                }}/>
            </Grid>
        </>;
    }

    render() {
        let field1, field2, dialog = null, calibration_table = null;
        if (this.props.coordinateType === 'icrs' || this.props.coordinateType === 'tete') {
            field1 = this.fieldGen('ra', [{key: 'h', min: 0, max: 23, adornment: 'h', ref: this.one, nextRef: this.two},
                {key: 'm', min: 0, max: 59, adornment: 'm', ref: this.two, nextRef: this.three},
                {key: 's', min: 0, max: 59, adornment: 's', ref: this.three, nextRef: this.four}]);
            field2 = this.fieldGen('dec',
                [
                    {key: 'd', min: -90, max: 90, adornment: <>&deg;</>, ref: this.four, nextRef: this.five},
                    {key: 'm', min: 0, max: 59, adornment: '\'', ref: this.five, nextRef: this.six},
                    {key: 's', min: 0, max: 59, adornment: '"', ref: this.six, nextRef: this.buttonRef}
                ]
            );
        } else if (this.props.coordinateType === 'hadec') {
            field1 = this.fieldGen('ha', [{key: 'h', min: 0, max: 23, adornment: 'h', ref: this.one, nextRef: this.two},
                {key: 'm', min: 0, max: 59, adornment: 'm', ref: this.two, nextRef: this.three},
                {key: 's', min: 0, max: 59, adornment: 's', ref: this.three, nextRef: this.four}]);
            field2 = this.fieldGen('dec',
                [
                    {key: 'd', min: -90, max: 90, adornment: <>&deg;</>, ref: this.four, nextRef: this.five},
                    {key: 'm', min: 0, max: 59, adornment: '\'', ref: this.five, nextRef: this.six},
                    {key: 's', min: 0, max: 59, adornment: '"', ref: this.six, nextRef: this.buttonRef}
                ]
            );
        } else {
            field1 = this.fieldGen('alt', [
                {key: 'd', min: 0, max: 90, adornment: <>&deg;</>, ref: this.one, nextRef: this.two},
                {key: 'm', min: 0, max: 59, adornment: '\'', ref: this.two, nextRef: this.three},
                {key: 's', min: 0, max: 59, adornment: '"', ref: this.three, nextRef: this.four}]);
            field2 = this.fieldGen('az', [
                {key: 'd', min: 0, max: 359, adornment: <>&deg;</>, ref: this.four, nextRef: this.five},
                {key: 'm', min: 0, max: 59, adornment: '\'', ref: this.five, nextRef: this.six},
                {key: 's', min: 0, max: 59, adornment: '"', ref: this.six, nextRef: this.buttonRef}]);
        }

        if (state.goto.coorddialog.shown) {
            dialog = <CoordDialog/>;
        }

        if (state.misc.calibration_logging) {
            calibration_table = <Grid item xs={12}><CalibrationTable/></Grid>
        }

        return (
            <Typography component="div">
                <Grid container spacing={2} justifyContent="center" alignContent="center" alignItems="center">
                    <Grid item xs={4}/>
                    <Grid item xs={4}>
                        <Select value={this.props.coordinateType} onChange={this.props.onTypeChange}>
                            <MenuItem value="tete">RA/Dec JNow</MenuItem>
                            <MenuItem value="icrs">RA/Dec J2000</MenuItem>
                            <MenuItem value="altaz">Alt/Az</MenuItem>
                            <MenuItem value="hadec">HA/Dec</MenuItem>
                        </Select>
                    </Grid>
                    <Grid item xs={4}/>
                    <Grid item xs={2}>
                    </Grid>
                    {field1}
                    <Grid item xs={3}>
                    </Grid>
                    <Grid item xs={2}>
                    </Grid>
                    {field2}
                    <Grid item xs={3}>
                    </Grid>
                    <Grid item xs={12} style={{textAlign: "center"}}>
                        <Button variant="contained" color="primary" buttonRef={this.buttonRef}
                                onClick={this.handleClick}>Slew/Sync</Button>
                    </Grid>
                </Grid>
                {calibration_table}
                {dialog}
            </Typography>
        );
    }
}

CoordinatesInput.propTypes = {
    coordinateType: PropTypes.string,
    onTypeChange: PropTypes.func
};

export default CoordinatesInput;