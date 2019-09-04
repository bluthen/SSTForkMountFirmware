import React from "react";
import state from './State';
import {observer} from "mobx-react"
import Typography from '@material-ui/core/Typography';
import TextField from '@material-ui/core/TextField';
import Grid from '@material-ui/core/Grid';
import CoordDisplayToggle from './CoordDisplayToggle';
import InputAdornment from '@material-ui/core/InputAdornment';
import Button from '@material-ui/core/Button';
import RootRef from '@material-ui/core/RootRef';

@observer
class CoordinatesInput extends React.Component {
    constructor(props) {
        super(props);
        this.one = React.createRef();
        this.two = React.createRef();
        this.three = React.createRef();
        this.four = React.createRef();
        this.five = React.createRef();
        this.six = React.createRef();
        this.buttonRef = React.createRef();
    }

    onCoordChange(e, coord, sub) {
        let v = parseInt(e.currentTarget.value);
        if (isNaN(v)) {
            v = null;
        }
        state.goto.coordinates[coord][sub.key] = v;
        if (v * 10 > sub.max || v * 10 < sub.min) {
            sub.nextRef.current.focus();
        }
        if (v > sub.max || v < sub.min) {
            state.goto.coordinates[coord + '_error'][sub.key] = 'invalid value';
        }
        console.log(sub, v);
    }

    onSubFocus(e, ref) {
        console.log('subfocus', ref);
        ref.current.select();
    }

    handleClick(e) {
        let coords, subkeys;
        if (this.props.coordinateType === 'radec') {
            coords= ['ra', 'dec'];
            subkeys = ['h', 'm', 's'];
        }
        let validCoords = true;
        coords.forEach((coord)=> {
           subkeys.forEach((key)=> {
                if(state.goto.coordinates[coord][key] === null || state.goto.coordinates[coord+'_error'][key]) {
                    validCoords = false;
                }
            });
        });
        if(validCoords) {
            this.props.onClick(e);
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
            }} type="number" inputProps={{min: subs[0].min, max: subs[0].max, step: 1}} InputProps={{
                endAdornment: <InputAdornment position="end">{subs[0].adornment}</InputAdornment>,
            }} inputRef={subs[0].ref} onFocus={(e) => {
                this.onSubFocus(e, subs[0].ref)
            }}/>
        </Grid>
        <Grid item xs={2}>
            <TextField value={v2 === null ? '' : v2} error={!!v2_error} label={v2_error} onChange={(e) => {
                this.onCoordChange(e, coord, subs[1]);
            }} type="number" inputProps={{min: subs[0].min, max: subs[1].max, step: 1}} InputProps={{
                endAdornment: <InputAdornment position="end">{subs[1].adornment}</InputAdornment>,
            }} inputRef={subs[1].ref} onFocus={(e) => {
                this.onSubFocus(e, subs[1].ref)
            }}/>
        </Grid>
        <Grid item xs={2}>
            <TextField value={v3 === null ? '' : v3} error={!!v3_error} label={v3_error} onChange={(e) => {
                this.onCoordChange(e, coord, subs[2]);
            }} type="number" inputProps={{min: subs[2].min, max: subs[2].max, step: 1}} InputProps={{
                endAdornment: <InputAdornment position="end">{subs[2].adornment}</InputAdornment>,
            }} inputRef={subs[2].ref} onFocus={(e) => {
                this.onSubFocus(e, subs[2].ref)
            }}/>
        </Grid>
        </>;
    }

    render() {
        let field1, field2;
        if (this.props.coordinateType === 'radec') {
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


        return <Typography component="div">
            <Grid container spacing={2} justify="center" alignContent="center" alignItems="center">
                <Grid item xs={4}/>
                <Grid item xs={4}>
                    <CoordDisplayToggle checked={this.props.coordinateType === 'altaz'}
                                        onChange={this.props.onTypeChange}/>
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
                    <Button variant="contained" color="primary" buttonRef={this.buttonRef} onClick={this.handleClick}>Slew/Sync</Button>
                </Grid>
            </Grid>
        </Typography>
    }
}

export default CoordinatesInput;