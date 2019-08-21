import React from "react";
import Typography from '@material-ui/core/Typography';
import TextField from '@material-ui/core/TextField';
import Grid from '@material-ui/core/Grid';
import CoordDisplayToggle from './CoordDisplayToggle';
import InputAdornment from '@material-ui/core/InputAdornment';
import Button from '@material-ui/core/Button';


class CoordinatesInput extends React.Component {
    render() {
        let field1, field2;
        if (this.props.coordinateType === 'radec') {
            field1 = <React.Fragment>
                <Grid item xs={1}>
                    RA
                </Grid>
                <Grid item xs={2}>
                    <TextField type="number" inputProps={{min: 0, max: 24, step: 1}} InputProps={{
                        endAdornment: <InputAdornment position="end">h</InputAdornment>,
                    }}/>
                </Grid>
                <Grid item xs={2}>
                    <TextField type="number" inputProps={{min: 0, max: 59, step: 1}} InputProps={{
                        endAdornment: <InputAdornment position="end">m</InputAdornment>,
                    }}/>
                </Grid>
                <Grid item xs={2}>
                    <TextField type="number" inputProps={{min: 0, max: 59, step: 1}} InputProps={{
                        endAdornment: <InputAdornment position="end">s</InputAdornment>,
                    }}/>
                </Grid>
            </React.Fragment>;
            field2 = <React.Fragment>
                <Grid item xs={1}>
                    DEC
                </Grid>
                <Grid item xs={2}>
                    <TextField type="number" inputProps={{min: -90, max: 90, step: 1}} InputProps={{
                        endAdornment: <InputAdornment position="end">&deg;</InputAdornment>,
                    }}/>
                </Grid>
                <Grid item xs={2}>
                    <TextField type="number" inputProps={{min: 0, max: 59, step: 1}} InputProps={{
                        endAdornment: <InputAdornment position="end">'</InputAdornment>,
                    }}/>
                </Grid>
                <Grid item xs={2}>
                    <TextField type="number" inputProps={{min: 0, max: 59, step: 1}} InputProps={{
                        endAdornment: <InputAdornment position="end">"</InputAdornment>,
                    }}/>
                </Grid>
            </React.Fragment>;
        } else {
            field1 = <React.Fragment>
                <Grid item xs={1}>
                    Alt
                </Grid>
                <Grid item xs={2}>
                    <TextField type="number" inputProps={{min: 0, max: 90, step: 1}} InputProps={{
                        endAdornment: <InputAdornment position="end">&deg;</InputAdornment>,
                    }}/>
                </Grid>
                <Grid item xs={2}>
                    <TextField type="number" inputProps={{min: 0, max: 59, step: 1}} InputProps={{
                        endAdornment: <InputAdornment position="end">'</InputAdornment>,
                    }}/>
                </Grid>
                <Grid item xs={2}>
                    <TextField type="number" inputProps={{min: 0, max: 59, step: 1}} InputProps={{
                        endAdornment: <InputAdornment position="end">"</InputAdornment>,
                    }}/>
                </Grid>
            </React.Fragment>;
            field2 = <React.Fragment>
                <Grid item xs={1}>
                    Az
                </Grid>
                <Grid item xs={2}>
                    <TextField type="number" inputProps={{min: 0, max: 359, step: 1}} InputProps={{
                        endAdornment: <InputAdornment position="end">&deg;</InputAdornment>,
                    }}/>
                </Grid>
                <Grid item xs={2}>
                    <TextField type="number" inputProps={{min: 0, max: 59, step: 1}} InputProps={{
                        endAdornment: <InputAdornment position="end">'</InputAdornment>,
                    }}/>
                </Grid>
                <Grid item xs={2}>
                    <TextField type="number" inputProps={{min: 0, max: 59, step: 1}} InputProps={{
                        endAdornment: <InputAdornment position="end">"</InputAdornment>,
                    }}/>
                </Grid>
            </React.Fragment>;

        }


        return <Typography component="div">
            <Grid container spacing={2} justify="center" alignContent="center" alignItems="center">
                <Grid item xs={4}/>
                <Grid item xs={4}>
                    <CoordDisplayToggle checked={this.props.coordinateType === 'altaz'} onChange={this.props.onTypeChange}/>
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