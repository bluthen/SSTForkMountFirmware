import React from "react";
import Typography from '@material-ui/core/Typography';
import TextField from '@material-ui/core/TextField';
import Grid from '@material-ui/core/Grid';

class NetworkSettings extends React.Component {

    render() {
        return <Typography component="div">
            <Grid container spacing={2}>
                <Grid item xs={12}>
                    AP Settings
                </Grid>
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
        </Typography>;
    }

}

export default NetworkSettings;