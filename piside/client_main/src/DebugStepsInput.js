import React from "react";
import state from './State';
import {observer} from "mobx-react";
import Typography from '@material-ui/core/Typography';
import TextField from '@material-ui/core/TextField';
import Grid from '@material-ui/core/Grid';
import InputAdornment from '@material-ui/core/InputAdornment';
import Button from '@material-ui/core/Button';
import APIHelp from './util/APIHelp';

@observer
class DebugStepsInput extends React.Component {
    constructor(props) {
        super(props);
        this.handleClick = this.handleClick.bind(this);
        this.one = React.createRef();
        this.two = React.createRef();
        this.buttonRef = React.createRef();
    }

    onCoordChange(e, coord, sub) {
        let v = e.currentTarget.value;
        v = parseInt(v);
        if (isNaN(v)) {
            v = null;
        }
        state.goto.steps[coord] = v;
        if (v) {
            state.goto.steps[coord + '_error'] = null;
        } else {
            state.goto.steps[coord + '_error'] = 'invalid value';
        }
    }

    onSubFocus(e, ref) {
        ref.current.select();
    }


    goodClick() {
        APIHelp.slewToSteps({ra_steps: state.goto.steps.ra, dec_steps: state.goto.steps.dec});
    }

    handleClick(e) {
        let coords = ['ra', 'dec'];
        for (let coord in coords) {
            if (state.goto.steps[coord] !== null && !state.goto.steps[coord + '_error']) {
                this.goodClick();
            }
        }
    }

    fieldGen(coord, subs) {
        const v1 = state.goto.steps[coord];
        const v1_error = state.goto.steps[coord + '_error'];

        return <>
        <Grid item xs={2}/>
        <Grid item xs={2}>
            {coord.toUpperCase()}
        </Grid>
        <Grid item xs={6}>
            <TextField value={v1 === null ? '' : v1} error={!!v1_error} label={v1_error} onChange={(e) => {
                this.onCoordChange(e, coord, subs[0]);
            }} type="number" inputProps={{step: 1}} InputProps={{
                endAdornment: <InputAdornment position="end">steps</InputAdornment>,
            }} inputRef={subs[0].ref} onFocus={(e) => {
                this.onSubFocus(e, subs[0].ref)
            }}/>
        </Grid>
        <Grid item xs={2}/>
        </>;
    }

    render() {
        let field1, field2, dialog = null;
        field1 = this.fieldGen('ra', [{ref: this.one}]);
        field2 = this.fieldGen('dec', [{ref: this.two}]);

        return <Typography component="div">
            <Grid container spacing={2} justify="center" alignContent="center" alignItems="center">
                <Grid item xs={2}/>
                <Grid item xs={4}>
                    RA Steps: {state.status.rep}
                </Grid>
                <Grid item xs={4}>
                    DEC Steps: {state.status.dep}
                </Grid>
                <Grid item xs={2}/>
                {field1}
                {field2}
                <Grid item xs={12} style={{textAlign: "center"}}>
                    <Button variant="contained" color="primary" buttonRef={this.buttonRef} onClick={this.handleClick}>Slew</Button>
                </Grid>
            </Grid>
            {dialog}
        </Typography>
    }
}

export default DebugStepsInput;