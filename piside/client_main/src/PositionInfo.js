import state from './State';
import {observer} from "mobx-react"
import React from "react";
import TToggle from './TToggle';
import Typography from '@material-ui/core/Typography';
import Grid from '@material-ui/core/Grid';
import Formatting from './util/Formatting';
import APIHelp from './util/APIHelp';
import MenuItem from '@material-ui/core/MenuItem';
import Select from '@material-ui/core/Select';


const indent = {
    paddingLeft: "4ex"
};

const bold = {
    paddingTop: "3x",
    fontWeight: "bold"
};

@observer
class PositionInfo extends React.Component {
    coordChange(e) {
        state.coordDisplay = e.target.value;
    }

    componentDidMount() {
        APIHelp.fetchSettings();
    }

    render() {
        let notTrackingWarning = null;
        const tableInfo = {coord1: 'RA', coord2: 'Dec', toggleChecked: false, coord1Value: 'CDV1', coord2Value: 'CDV2'};
        if (state.coordDisplay === 'icrs') {
            tableInfo.coord1Value = Formatting.degRA2Str(state.status.icrs_ra);
            tableInfo.coord2Value = Formatting.degDEC2Str(state.status.icrs_dec);
        } else if(state.coordDisplay === 'tete') {
            tableInfo.coord1Value = Formatting.degRA2Str(state.status.tete_ra);
            tableInfo.coord2Value = Formatting.degDEC2Str(state.status.tete_dec);
        } else if(state.coordDisplay === 'hadec') {
            tableInfo.coord1 = 'HA';
            tableInfo.coord2 = 'Dec';
            tableInfo.coord1Value = Formatting.degRA2Str(state.status.hadec_ha);
            tableInfo.coord2Value = Formatting.degDEC2Str(state.status.hadec_dec);
        } else if(state.coordDisplay === 'steps') {
            tableInfo.coord1 = 'Steps-HA';
            tableInfo.coord2 = 'Steps-Dec';
            tableInfo.coord1Value = state.status.rep;
            tableInfo.coord2Value = state.status.dep;

        } else {
            tableInfo.coord1 = 'Alt';
            tableInfo.coord2 = 'Az';
            tableInfo.toggleChecked = true;
            tableInfo.coord1Value = Formatting.degDEC2Str(state.status.alt);
            tableInfo.coord2Value = Formatting.degDEC2Str(state.status.az);
        }
        if(!state.status.tracking) {
            notTrackingWarning = <Grid item xs={12} style={{color: 'red'}}>Warning: not tracking</Grid>
        }

        return <Typography component="div" style={{paddingBottom: "4ex"}}>
            <Typography component="h4" style={bold}>
                Mount Location
            </Typography>
            <Typography component="div" style={indent}>{state.location_set.name}<br/><span style={{color: 'gray'}}>
                {Formatting.degLat2Str(state.location_set.lat)}/{Formatting.degLong2Str(state.location_set.long)} {state.location_set.elevation}m
            </span></Typography>
            <Typography component="h4" style={bold}>
                Mount Local Time [Sidereal Time JNow]
            </Typography>
            <Typography component="div" style={indent}>{new Date(state.status.time).toLocaleString()} [{state.status.sidereal_time}]</Typography>
            <Grid container>
                <Grid item xs={8}>
                    <Grid container>
                        <Grid item xs={4} style={bold}>
                            Position
                        </Grid>
                        <Grid item xs={4} style={bold}>
                            {tableInfo.coord1}
                        </Grid>
                        <Grid item xs={4} style={bold}>
                            {tableInfo.coord2}
                        </Grid>
                        <Grid item xs={4}>
                            <Select value={state.coordDisplay} onChange={this.coordChange}>
                                <MenuItem value="tete">RA/Dec JNow</MenuItem>
                                <MenuItem value="icrs">RA/Dec J2000</MenuItem>
                                <MenuItem value="altaz">Alt/Az</MenuItem>
                                <MenuItem value="hadec">HA/Dec</MenuItem>
                                <MenuItem value="steps">Steps</MenuItem>
                            </Select>
                        </Grid>
                        <Grid item xs={4}>{tableInfo.coord1Value}</Grid>
                        <Grid item xs={4}>{tableInfo.coord2Value}</Grid>
                    </Grid>
                </Grid>
                {notTrackingWarning}
            </Grid>
        </Typography>;
    }
}


export default PositionInfo;