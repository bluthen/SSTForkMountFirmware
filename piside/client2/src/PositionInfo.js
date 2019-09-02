import state from './State';
import {observer} from "mobx-react"
import React from "react";
import CoordDisplayToggle from './CoordDisplayToggle';
import Typography from '@material-ui/core/Typography';
import Grid from '@material-ui/core/Grid';
import Formating from './util/Formating';


const indent = {
    paddingLeft: "4ex"
};

const bold = {
    paddingTop: "3x",
    fontWeight: "bold"
};

@observer
class PositionInfo extends React.Component {
    coordChange(event, value) {
        if (value) {
            state.coordDisplay = 'altaz';
        } else {
            state.coordDisplay = 'radec';
        }
    }

    render() {
        const tableInfo = {coord1: 'RA', coord2: 'Dec', toggleChecked: false, coord1Value: 'CDV1', coord2Value: 'CDV2'};
        if (state.coordDisplay === 'radec') {
            tableInfo.coord1Value = Formating.degRA2Str(state.status.ra);
            tableInfo.coord2Value = Formating.degDEC2Str(state.status.dec);
        } else {
            tableInfo.coord1 = 'Alt';
            tableInfo.coord2 = 'Az';
            tableInfo.toggleChecked = true;
            tableInfo.coord1Value = Formating.degDEC2Str(state.status.alt);
            tableInfo.coord2Value = Formating.degDEC2Str(state.status.az);
        }
        return <Typography component="div" style={{paddingBottom: "4ex"}}>
            <Typography component="h4" style={bold}>
                Mount Location
            </Typography>
            <Typography component="div" style={indent}>LawrenceAA, KS</Typography>
            <Typography component="h4" style={bold}>
                Mount Time
            </Typography>
            <Typography component="div" style={indent}>{new Date(state.status.time).toLocaleString()}</Typography>
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
                            <CoordDisplayToggle checked={tableInfo.toggleChecked} onChange={this.coordChange}/>
                        </Grid>
                        <Grid item xs={4}>{tableInfo.coord1Value}</Grid>
                        <Grid item xs={4}>{tableInfo.coord2Value}</Grid>
                    </Grid>
                </Grid>
            </Grid>
        </Typography>;
    }
}


export default PositionInfo;