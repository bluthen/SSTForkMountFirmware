import React from "react";
import {observer} from "mobx-react"
import state from './State';
import Grid from '@material-ui/core/Grid';
import Button from '@material-ui/core/Button';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Checkbox from '@material-ui/core/Checkbox';
import uuidv4 from 'uuid/v4';
import APIHelp from './util/APIHelp';
import TToggle from './TToggle';
import EncoderGraph from './EncoderGraph';


@observer
class MiscellaneousSettings extends React.Component {
    constructor(props) {
        super(props);
        this.uuid = uuidv4();
        this.firmwareRef = React.createRef();
        this.handleFirmwareUpdate = this.handleFirmwareUpdate.bind(this);
        this.plotEncoderLogs = this.plotEncoderLogs.bind(this);
        this.state = {encoderData: null};
    }

    componentDidMount() {
        APIHelp.fetchSettings();
    }

    handleParkClicked() {
        APIHelp.setParkPosition();
    }

    handleFirmwareUpdate(e) {
        const file = this.firmwareRef.current.files[0];
        APIHelp.uploadFirmware(file);
    }

    onTrackingChange(e, tracking) {
        APIHelp.toggleTracking(tracking).then(() => {
            return APIHelp.statusUpdate();
        });
    }

    encoderLoggingChanged(e) {
        const enabled = e.target.checked;
        state.misc.encoder_logging = enabled;
        // Tell server to start logging.
        APIHelp.toggleLog('encoder', enabled);
    }

    calibrationLoggingChanged(e) {
        const enabled = e.target.checked;
        state.misc.calibration_logging = enabled;
        // Tell server to start logging.
        APIHelp.toggleLog('calibration', enabled);
    }

    clearEncoderClicked() {
        APIHelp.clearLog('encoder');
    }

    plotEncoderLogs(e) {
        this.setState({encoderData: "fetching"});
        APIHelp.getLogData('encoder').then((data) => {
            this.setState({encoderData: data});
        });
    }

    render() {
        return <Grid container spacing={3}>
            <Grid item xs={12}/>
            <Grid item xs={4}/>
            <Grid item xs={4}>
                <TToggle onLabel="Tracking" offLabel="Not Tracking" checked={state.status.tracking}
                         onChange={this.onTrackingChange}/>
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
                <Button color="secondary" variant="contained" onClick={this.handleFirmwareUpdate}>Upload</Button>
            </Grid>
            <Grid item xs={12} style={{textAlign: "center", padding: '3ex'}}>
                <h3>Calibration Tools</h3>
                <FormControlLabel
                    control={
                        <Checkbox
                            value="toggle"
                            color="primary"
                            checked={state.misc.calibration_logging}
                            onChange={this.calibrationLoggingChanged}
                        />
                    }
                    label="Enable Calibration Table"/>
            </Grid>
            <Grid item xs={12} style={{textAlign: "center", padding: '3ex'}}>
                <h3>Encoder Debugging</h3>
            </Grid>
            <Grid item xs={4}>
                <FormControlLabel
                    control={
                        <Checkbox
                            value="toggle"
                            color="primary"
                            checked={state.misc.encoder_logging}
                            onChange={this.encoderLoggingChanged}
                        />
                    }
                    label="Enable encoder Logging"/>
            </Grid>
            <Grid item xs={4}>
                <Button color="primary" variant="contained" onClick={this.clearEncoderClicked}>Clear encoder logs</Button>
            </Grid>
            <Grid item xs={4}>
                <Button color="primary" variant="contained" onClick={this.plotEncoderLogs}>Plot encoder logs</Button>
            </Grid>
            <Grid item xs={12}>
                <EncoderGraph height={500} width={"100%"} data={this.state.encoderData}/>
            </Grid>
        </Grid>;
    }
}

export default MiscellaneousSettings;
