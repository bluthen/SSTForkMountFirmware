import React from "react";
import state from './State';
import Button from '@mui/material/Button';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import APIHelp from './util/APIHelp';


const item={ textAlign: "center", padding: "2ex"};

const park={...item, paddingTop: "6ex"};

class ManualPage extends React.Component {
    advancedSettingsClicked() {
        state.page='advancedSettings';
    }

    locationSettingsClicked() {
        state.page='locationSettings';
    }

    networkSettingsClicked() {
        state.page='networkSettings';
    }

    slewLimitsSettingsClicked() {
        state.page='slewLimitsSettings';
    }

    slewMiscSettingsClicked() {
        state.page='miscellaneousSettings';
    }

    render() {
        return <Container>
            <Grid container>
                <Grid item xs={12} style={item}>
                    <Button variant="contained" color="primary" onClick={this.locationSettingsClicked}>Location</Button>
                </Grid>
                <Grid item xs={12} style={item}>
                    <Button variant="contained" color="primary" onClick={this.networkSettingsClicked}>Network Settings</Button>
                </Grid>
                <Grid item xs={12} style={item}>
                    <Button variant="contained" color="primary" onClick={this.slewLimitsSettingsClicked}>Slew Limits</Button>
                </Grid>
                <Grid item xs={12} style={item}>
                    <Button variant="contained" color="primary" onClick={this.slewMiscSettingsClicked}>Miscellaneous</Button>
                </Grid>
                <Grid item xs={12} style={item}>
                    <Button variant="contained" color="primary" onClick={this.advancedSettingsClicked}>Advanced Settings</Button>
                </Grid>
                <Grid item xs={12} style={item}>
                    <Button variant="contained">Help</Button>
                </Grid>
                <Grid item xs={12} style={item}>
                    <Button variant="contained">About</Button>
                </Grid>
                <Grid item xs={12} style={park}>
                    <Button variant="contained" color="secondary" onClick={APIHelp.park}>Park Scope</Button>
                </Grid>
            </Grid>
        </Container>
    }
}

export default ManualPage;