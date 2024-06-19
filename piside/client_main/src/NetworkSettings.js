import React from "react";
import state from './State';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Grid from '@mui/material/Grid';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import ListItemSecondaryAction from '@mui/material/ListItemSecondaryAction';
import DeleteIcon from '@mui/icons-material/Delete';
import {observer} from "mobx-react"
import APIHelp from './util/APIHelp';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContentText from '@mui/material/DialogContentText';
import CheckCircle from '@mui/icons-material/CheckCircle';
import {action as mobxaction} from 'mobx';


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

    @mobxaction
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
                state.snack_bar = 'Connecting...';
                state.snack_bar_error = false;
                this.handleDialogClose();
                APIHelp.setWifiConnect(ssid, mac, known, open, password).then(() => {
                    APIHelp.fetchWifiScan();
                    APIHelp.fetchKnownWifi();
                });
            }
        }

    }

    @mobxaction
    handleDialogClose() {
        state.network.password_dialog.shown = false;
    }

    @mobxaction
    handleConnectClick() {
        if (!state.network.password_dialog.password) {
            state.network.password_dialog.password_error = 'Password required';
            return;
        } else {
            state.network.password_dialog.password_error = null;
        }

        this.genHandleConnectClicked(state.network.password_dialog.ssid, state.network.password_dialog.mac, 'psk', state.network.password_dialog.password)();
    }

    @mobxaction
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
                    &quot;{state.network.password_dialog.ssid}&quot;.</DialogContentText>
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

    @mobxaction
    genHandleDeleteKnown(ssid, mac) {
        return () => {
            state.snack_bar = 'Deleting...';
            state.snack_bar_error = false;
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
                        <IconButton
                            edge="end"
                            aria-label="delete"
                            onClick={this.genHandleDeleteKnown(known.ssid, known.bssid)}
                            size="large">
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
        let channel = ~~(e.currentTarget.value);
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