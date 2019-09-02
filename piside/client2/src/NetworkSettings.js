import React from "react";
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




class WifiClient extends React.Component {
    render() {
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
                <TableRow hover onClick={() => {
                    //Prompt for password if security
                }}>
                    <TableCell>London<br/>f8:f8:f8:f8:f8:f8</TableCell>
                    <TableCell>-34</TableCell>
                    <TableCell>PSK</TableCell>
                </TableRow>
            </TableBody>
        </Table>
        </>
    }
}

class KnownWifi extends React.Component {
    render() {
        return <>
        <Grid container spacing={2}>
            <Grid item xs={12}>
                <List component="nav">
                    <ListItem button><ListItemText primary="London" secondary="f8:f8:f8:f8:f8:f8"/>
                        <ListItemSecondaryAction>
                            <IconButton edge="end" aria-label="delete">
                                <DeleteIcon/>
                            </IconButton>
                        </ListItemSecondaryAction>
                    </ListItem>
                    <ListItem button><ListItemText primary="Farpoint Outside" secondary="aa:aa:aa:aa:aa:aa"/>
                        <ListItemSecondaryAction>
                            <IconButton edge="end" aria-label="delete">
                                <DeleteIcon/>
                            </IconButton>
                        </ListItemSecondaryAction>
                    </ListItem>
                </List>
            </Grid>
        </Grid>
        </>
    }
}


class NetworkSettings extends React.Component {

    render() {
        return <Typography component="div">
            <h2>Access Point Settings</h2>
            <Grid container spacing={2}>
                <Grid item xs={4}>
                    <TextField label="SSID"/>
                </Grid>
                <Grid item xs={4}>
                    <TextField label="WPA2 Key"/>
                </Grid>
                <Grid item xs={4}>
                    <TextField type="number" label="Channel"/>
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