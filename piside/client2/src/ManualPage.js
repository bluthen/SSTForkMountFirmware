import React from "react";
import PositionInfo from "./PositionInfo";
import Slider from '@material-ui/core/Slider';
import Grid from '@material-ui/core/Grid';
import DirectionControls from './DirectionControls';
import Typography from '@material-ui/core/Typography';


const marks = [
    {value: 3, label: 'Fastest'},
    {value: 2, label: ''},
    {value: 1, label: ''},
    {value: 0, label: 'Slowest'}

];


class ManualPage extends React.Component {
    constructor(props) {
        super(props);
        //this.classes = useStyles();
    }

    render() {
        return <React.Fragment>
            <PositionInfo/>
            <Typography component="div" style={{paddingBottom: "4ex"}}>
            <Grid container style={{height: "500px"}} justify="center" alignItems="center">
                <Grid item style={{height: "100%", paddingRight: "15%"}} xs={3}>
                    <Slider defaultValue={3} orientation="vertical" min={0} max={3} step={1} marks={marks}/>
                </Grid>
                <Grid item style={{height: "100%"}} xs={9}>
                    <DirectionControls/>
                </Grid>
            </Grid>
            </Typography>
        </React.Fragment>;
    }

}

export default ManualPage;