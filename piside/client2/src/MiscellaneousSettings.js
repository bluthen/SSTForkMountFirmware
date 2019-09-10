import React from "react";
import {observer} from "mobx-react"
import state from './State';
import TextField from '@material-ui/core/TextField';
import Grid from '@material-ui/core/Grid';
import InputAdornment from '@material-ui/core/InputAdornment';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Checkbox from '@material-ui/core/Checkbox';
import Button from '@material-ui/core/Button';
import CircularProgress from '@material-ui/core/CircularProgress';
import uuidv4 from 'uuid/v4';
import APIHelp from './util/APIHelp';
import TToggle from './TToggle';



@observer
class MiscellaneousSettings extends React.Component {
    constructor(props) {
        super(props);
        this.uuid = uuidv4();
        this.firmwareRef = React.createRef();
        this.handleFirmwareUpdate = this.handleFirmwareUpdate.bind(this);
    }

    handleParkClicked() {
        APIHelp.setParkPosition();
    }

    handleFirmwareUpdate(e) {
        const file = this.firmwareRef.current.files[0];
        APIHelp.uploadFirmware(file);
    }

    onTrackingChange(e, tracking) {
            APIHelp.toggleTracking(tracking);
    }

    render() {
        return <Grid container spacing={3}>
            <Grid item xs={12}/>
            <Grid item xs={4}/>
            <Grid item xs={4}>
                <TToggle onLabel="Tracking" offLabel="Not Tracking" checked={state.status.tracking} onChange={this.onTrackingChange}/>
            </Grid>
            <Grid item xs={4}/>
            <Grid item xs={12} style={{textAlign: "center", paddingTop: '3ex'}}>
                <Button color="primary" variant="contained" onClick={this.handleParkClicked}>Set Park Position</Button>
            </Grid>
            <Grid item xs={12} style={{textAlign: "center", padding: '3ex'}}>
                <h3>Update mount Firmware</h3>
                <Button color="primary"
                        variant="contained"
                        component="label"
                >
                    Select Firmware File
                    <input
                        type="file"
                        style={{display: "none"}}
                        accept="application/zip"
                        ref={this.firmwareRef}
                    />
                </Button>
                <Button color="secondary"  variant="contained" onClick={this.handleFirmwareUpdate}>Upload</Button>
            </Grid>
        </Grid>;
    }
}

export default MiscellaneousSettings;
