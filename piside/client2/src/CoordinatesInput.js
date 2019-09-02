import React from "react";
import state from './State';
import {observer} from "mobx-react"
import Typography from '@material-ui/core/Typography';
import TextField from '@material-ui/core/TextField';
import Grid from '@material-ui/core/Grid';
import CoordDisplayToggle from './CoordDisplayToggle';
import InputAdornment from '@material-ui/core/InputAdornment';
import Button from '@material-ui/core/Button';

@observer
class CoordinatesInput extends React.Component {

    onCoordChange(e, coord, sub) {
        let v = parseInt(e.currentTarget.value);
        if (isNaN(v)) {
            v = null;
        }
        state.goto.coordinates[coord][sub] = v;
    }

    fieldGen(coord, subs) {
        const v1 = state.goto.coordinates[coord][subs[0].key];
        const v2 = state.goto.coordinates[coord][subs[1].key];
        const v3 = state.goto.coordinates[coord][subs[2].key];

        return <>
        <Grid item xs={1}>
            {coord.toUpperCase()}
        </Grid>
        <Grid item xs={2}>
            <TextField value={v1 === null ? '' : v1} onChange={(e) => {
                this.onCoordChange(e, coord, subs[0].key);
            }} type="number" inputProps={{min: subs[0].min, max: subs[0].max, step: 1}} InputProps={{
                endAdornment: <InputAdornment position="end">{subs[0].adornment}</InputAdornment>,
            }}/>
        </Grid>
        <Grid item xs={2}>
            <TextField value={v2 === null ? '' : v2} onChange={(e) => {
                this.onCoordChange(e, coord, subs[1].key);
            }} type="number" inputProps={{min: subs[0].min, max: subs[1].max, step: 1}} InputProps={{
                endAdornment: <InputAdornment position="end">{subs[1].adornment}</InputAdornment>,
            }}/>
        </Grid>
        <Grid item xs={2}>
            <TextField value={v3 === null ? '' : v3} onChange={(e) => {
                this.onCoordChange(e, coord, subs[2].key);
            }} type="number" inputProps={{min: subs[2].min, max: subs[2].max, step: 1}} InputProps={{
                endAdornment: <InputAdornment position="end">{subs[2].adornment}</InputAdornment>,
            }}/>
        </Grid>
        </>;
    }

    render() {
        let field1, field2;
        if (this.props.coordinateType === 'radec') {
            field1 = this.fieldGen('ra', [{key: 'h', min: 0, max: 23, adornment: 'h'},
                {key: 'm', min: 0, max: 59, adornment: 'm'},
                {key: 's', min: 0, max: 59, adornment: 's'}]);
            field2 = this.fieldGen('dec', [{key: 'd', min: -90, max: 90, adornment: <>&deg;</>},
                {key: 'm', min: 0, max: 59, adornment: '\''},
                {key: 's', min: 0, max: 59, adornment: '"'}]);
        } else {
            field1 = this.fieldGen('alt', [{key: 'd', min: 0, max: 90, adornment: <>&deg;</>},
                {key: 'm', min: 0, max: 59, adornment: '\''},
                {key: 's', min: 0, max: 59, adornment: '"'}]);
            field2 = this.fieldGen('az', [{key: 'd', min: 0, max: 359, adornment: <>&deg;</>},
                {key: 'm', min: 0, max: 59, adornment: '\''},
                {key: 's', min: 0, max: 59, adornment: '"'}]);
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
                    <Button variant="contained" color="primary">Slew/Sync</Button>
                </Grid>
            </Grid>
        </Typography>
    }
}

export default CoordinatesInput;