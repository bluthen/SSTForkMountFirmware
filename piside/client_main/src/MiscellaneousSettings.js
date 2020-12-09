import React from "react";
import {observer} from "mobx-react"
import state from './State';
import Grid from '@material-ui/core/Grid';
import Button from '@material-ui/core/Button';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Checkbox from '@material-ui/core/Checkbox';
import InputLabel from '@material-ui/core/InputLabel';
import Select from '@material-ui/core/Select';
import MenuItem from '@material-ui/core/MenuItem';
import uuidv4 from 'uuid/v4';
import APIHelp from './util/APIHelp';
import TToggle from './TToggle';
import EncoderGraph from './EncoderGraph';
import UpdateDialog from './UpdateDialog';


@observer
class MiscellaneousSettings extends React.Component {
    constructor(props) {
        super(props);
        this.uuid = uuidv4();
        this.firmwareRef = React.createRef();
        this.settingsRef = React.createRef();
        this.handleFirmwareUpdate = this.handleFirmwareUpdate.bind(this);
        this.handleSettingImportClicked = this.handleSettingImportClicked.bind(this);
        this.plotEncoderLogs = this.plotEncoderLogs.bind(this);
        this.state = {encoderData: null};
    }

    componentDidMount() {
        APIHelp.fetchSettings();
        APIHelp.fetchVersion();
    }

    handleParkClicked() {
        APIHelp.setParkPosition();
    }

    handleFirmwareUpdate(e) {
        const file = this.firmwareRef.current.files[0];
        APIHelp.uploadFirmware(file);
        state.updateDialog.timer = null;
        state.updateDialog.show = true;
    }

    handleSettingImportClicked() {
        const file = this.settingsRef.current.files[0];
        APIHelp.uploadSettings(file);
        state.updateDialog.timer = null;
        state.updateDialog.show = true;
    }

    handlExportSettingsClicked() {
        APIHelp.exportSettings();
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

    debugOptionsChanged(e) {
        const enabled = e.target.checked;
        state.misc.debug_options = enabled;
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

    handleThemeChange(e) {
        state.color_scheme = e.target.value;
        APIHelp.saveSettings({'color_scheme': e.target.value});
    }

    render() {
        let dialog = null;
        if (state.updateDialog.show) {
            dialog = <UpdateDialog/>;
        }
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
            <Grid item xs={12} style={{textAlign: "center", paddingTop: '3ex'}}>
                <InputLabel htmlFor={this.uuid + "theme-select"}>Theme</InputLabel>
                <Select id={this.uuid + "theme-select"} value={state.color_scheme}
                        onChange={this.handleThemeChange} name="theme">
                    <MenuItem value="default">Default</MenuItem>
                    <MenuItem value="dark">Dark</MenuItem>
                </Select>
            </Grid>
            <Grid item xs={12} style={{textAlign: "center", padding: '3ex'}}>
                <h3>Update mount Firmware (Installed: {state.version.version}/{state.version.version_date})</h3>
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
                <h3>Import/Export Settings</h3>
                <Button color="primary"
                        variant="contained"
                        component="label"
                >
                    Select Settings File
                    <input
                        type="file"
                        style={{display: "none"}}
                        accept="application/json"
                        ref={this.settingsRef}
                    />
                </Button>
                <Button color="secondary" variant="contained" onClick={this.handleSettingImportClicked}>Import
                    Settings</Button>
                <br/><br/>
                <Button color="primary" variant="contained" onClick={this.handlExportSettingsClicked}>Export
                    Settings</Button>
            </Grid>
            <Grid item xs={3}/>
            <Grid item xs={6} style={{textAlign: "center", padding: '3ex'}}>
                <h3>CPU Stats</h3>
                Temperature: {~~(state.status.cpustats.tempc)}&deg;
                C({~~(state.status.cpustats.tempf)}&deg;F)<br/>
                CPU Load: {~~(state.status.cpustats.load_percent)}%<br/>
                Memory Use: {~~(state.status.cpustats.memory_percent_usage)}%
            </Grid>
            <Grid item xs={3}/>
            <Grid item xs={12} style={{textAlign: "center", padding: '3ex'}}>
                <h3>Calibration Tools and Debug Options</h3>
                <FormControlLabel
                    control={
                        <Checkbox
                            value="toggle"
                            color="primary"
                            checked={state.misc.calibration_logging}
                            onChange={this.calibrationLoggingChanged}
                        />
                    }
                    label="Enable Calibration Table"/><br/>
                <FormControlLabel
                    control={
                        <Checkbox
                            value="toggle"
                            color="primary"
                            checked={state.misc.debug_options}
                            onChange={this.debugOptionsChanged}
                        />
                    }
                    label="Enable Debug Options"/><br/>
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
                <Button color="primary" variant="contained" onClick={this.clearEncoderClicked}>Clear encoder
                    logs</Button>
            </Grid>
            <Grid item xs={4}>
                <Button color="primary" variant="contained" onClick={this.plotEncoderLogs}>Plot encoder logs</Button>
            </Grid>
            <Grid item xs={12}>
                <EncoderGraph height={500} width={"100%"} data={this.state.encoderData}/>
            </Grid>
            {dialog}
        </Grid>;
    }
}

export default MiscellaneousSettings;
