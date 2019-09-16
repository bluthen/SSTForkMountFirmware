import React from "react";
import state from './State';
import Typography from '@material-ui/core/Typography';
import TextField from '@material-ui/core/TextField';
import Grid from '@material-ui/core/Grid';
import Table from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableHead from '@material-ui/core/TableHead';
import TableRow from '@material-ui/core/TableRow';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemText from '@material-ui/core/ListItemText';
import IconButton from '@material-ui/core/IconButton';
import ListItemSecondaryAction from '@material-ui/core/ListItemSecondaryAction';
import DeleteIcon from '@material-ui/icons/Delete';
import {observer} from "mobx-react"
import APIHelp from './util/APIHelp';
import Button from '@material-ui/core/Button';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '@material-ui/core/DialogTitle';
import DialogContentText from '@material-ui/core/DialogContentText';
import CheckCircle from '@material-ui/icons/CheckCircle';


@observer
class WifiClient extends React.Component {
    constructor(props) {
        super(props);
        this.wifiScanInterval = null;
        this.handleConnectClick = this.handleConnectClick.bind(this);
    }

    componentDidMount() {
        APIHelp.fetchWifiScan();
        this.wifiScanInterval = setInterval(() => {
            APIHelp.fetchWifiScan();
        }, 20000);
    }

    componentWillUnmount() {
        clearInterval(this.wifiScanInterval);
        this.wifiScanInterval = null;
    }

    genHandleConnectClicked(ssid, mac, flags, password) {
        //Is this known
        return () => {
            let known = false;
            for (let i = 0; i < state.network.wifi_known.length; i++) {
                const ap = state.network.wifi_known[i];
                if (ap.mac === mac && ap.ssid === ssid) {
                    known = true;
                    break;
                }
            }
            //Is it need password?
            const open = flags.toLowerCase().indexOf('psk') === -1;
            if (!known && !open && !password) {
                // Password dialog
                state.network.password_dialog.ssid = ssid;
                state.network.password_dialog.mac = mac;
                state.network.password_dialog.password = '';
                state.network.password_dialog.password_error = null;
                state.network.password_dialog.shown = true;
            } else {
                if (open) {
                    password = null;
                }
                APIHelp.setWifiConnect(ssid, mac, known, open, password).then(() => {
                    APIHelp.fetchWifiScan();
                    APIHelp.fetchKnownWifi();
                    this.handleDialogClose();
                });
            }
        }

    }

    handleDialogClose() {
        state.network.password_dialog.shown = false;
    }

    handleConnectClick() {
        if (!state.network.password_dialog.password) {
            state.network.password_dialog.password_error = 'Password required';
            return;
        } else {
            state.network.password_dialog.password_error = null;
        }

        this.genHandleConnectClicked(state.network.password_dialog.ssid, state.network.password_dialog.mac, 'psk', state.network.password_dialog.password)();
    }

    handleDialogPasswordChange(e) {
        state.network.password_dialog.password = e.currentTarget.value;
    }

    render() {
        const rows = [];
        let foundConnected = false;
        const connectedInfo = {flags: '', signal: ''};
        for (let i = 0; i < state.network.wifi_scan.aps.length; i++) {
            const ap = state.network.wifi_scan.aps[i];
            if (!(ap.ssid === state.network.wifi_scan.connected.ssid && ap.mac === state.network.wifi_scan.connected.mac)) {

                rows.push(<TableRow key={'wifi_scan_' + i} hover
                                    onClick={this.genHandleConnectClicked(ap.ssid, ap.mac, ap.flags)}
                                    style={{cursor: "pointer"}}>
                    <TableCell>{ap.ssid}<br/>{ap.mac}</TableCell>
                    <TableCell>{ap.signal}</TableCell>
                    <TableCell>{ap.flags}</TableCell>
                </TableRow>);
            } else {
                connectedInfo.flags = ap.flags;
                connectedInfo.signal = ap.signal;
            }
        }
        if (!foundConnected && state.network.wifi_scan.connected.ssid) {
            const ap = state.network.wifi_scan.connected;
            rows.unshift(<TableRow key={'wifi_scan_connected'} hover>
                <TableCell>{ap.ssid}<CheckCircle style={{color: "green"}}/><br/>{ap.mac}</TableCell>
                <TableCell>{connectedInfo.signal}</TableCell>
                <TableCell>CONNECTED</TableCell>
            </TableRow>)
        }

        return <>
        <Table>
            <TableHead>
                <TableRow>
                    <TableCell>SSID</TableCell>
                    <TableCell>Signal</TableCell>
                    <TableCell>Security</TableCell>
                </TableRow>
            </TableHead>
            <TableBody>
                {rows}
            </TableBody>
        </Table>
        <Dialog open={state.network.password_dialog.shown} maxWidth="xs" onClose={this.handleDialogClose}>
            <DialogTitle>{state.network.password_dialog.ssid} Wifi Password</DialogTitle>
            <DialogContent>
                <DialogContentText>Please enter password to connect to access point
                    "{state.network.password_dialog.ssid}".</DialogContentText>
                <TextField autoFocus type="text" fullWidth value={state.network.password_dialog.password}
                           placeholder="Password" onChange={this.handleDialogPasswordChange}
                           error={!!state.network.password_dialog.password_error}
                           label={state.network.password_dialog.password_error}/>
            </DialogContent>
            <DialogActions>
                <Button color="primary" onClick={this.handleDialogClose}>Cancel</Button>
                <Button color="primary" onClick={this.handleConnectClick}>Connect</Button>
            </DialogActions>
        </Dialog>
        </>
    }
}

@observer
class KnownWifi extends React.Component {
    constructor(props) {
        super(props);
    }

    componentDidMount() {
        APIHelp.fetchKnownWifi();
    }

    componentWillUnmount() {

    }

    genHandleDeleteKnown(ssid, mac) {
        return () => {
            APIHelp.deleteKnown(ssid, mac).then(() => {
                APIHelp.fetchKnownWifi();
            });
        }

    }

    render() {
        const list = [];
        for (let i = 0; i < state.network.wifi_known.length; i++) {
            const known = state.network.wifi_known[i];
            list.push(
                <ListItem button key={'known_wifi_' + i}><ListItemText primary={known.ssid} secondary={known.bssid}/>
                    <ListItemSecondaryAction>
                        <IconButton edge="end" aria-label="delete"
                                    onClick={this.genHandleDeleteKnown(known.ssid, known.bssid)}>
                            <DeleteIcon/>
                        </IconButton>
                    </ListItemSecondaryAction>
                </ListItem>
            )
        }

        return <>
        <Grid container spacing={2}>
            <Grid item xs={12}>
                <List component="nav">
                    {list}
                </List>
            </Grid>
        </Grid>
        </>
    }
}

@observer
class NetworkSettings extends React.Component {

    componentDidMount() {
        APIHelp.fetchSettings();
    }

    handleSave() {
        APIHelp.setWAP(state.network.ssid, state.network.wpa2key, state.network.channel).then(() => {
            return APIHelp.fetchSettings();
        });
    }

    handleSSIDChange(e) {
        let ssid = e.currentTarget.value;
        if (ssid.length <= 31) {
            state.network.ssid = ssid;
        }
    }

    handleWPA2KeyChange(e) {
        let wpa2key = e.currentTarget.value;
        if (wpa2key.length <= 63) {
            state.network.wpa2key = wpa2key;
        }
    }

    handleChannelChange(e) {
        let channel = parseInt(e.currentTarget.value);
        if (channel >= 1 && channel <= 12) {
            state.network.channel = channel;
        }
    }

    render() {
        return <Typography component="div">
            <h2>Access Point Settings</h2>
            <Grid container spacing={2}>
                <Grid item xs={4}>
                    <TextField label="SSID" value={state.network.ssid} inputProps={{maxLength: 31}}
                               onChange={this.handleSSIDChange}/>
                </Grid>
                <Grid item xs={4}>
                    <TextField label="WPA2 Key" value={state.network.wpa2key} inputProps={{maxLength: 63}}
                               onChange={this.handleWPA2KeyChange}/>
                </Grid>
                <Grid item xs={4}>
                    <TextField type="number" label="Channel" value={state.network.channel}
                               inputProps={{min: 1, max: 11, steps: 1}} onChange={this.handleChannelChange}/>
                </Grid>
                <Grid item key={'save' + this.uuid} xs={12} style={{textAlign: "center"}}>
                    <Button color="primary" variant="contained" onClick={this.handleSave}>Save</Button>
                </Grid>
            </Grid>
            <h2>Wifi Client</h2>
            <WifiClient/>
            <h3>Known Wifi Connections</h3>
            <KnownWifi/>
        </Typography>;
    }

}

export default NetworkSettings;