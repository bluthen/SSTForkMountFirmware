import React from "react";
import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import LinearProgress from '@mui/material/LinearProgress';
import Grid from '@mui/material/Grid';


class SyncingDialog extends React.Component {
    render() {
        return <Dialog open maxwidth="xs">
            <DialogTitle>Syncing</DialogTitle>
            <DialogContent>
                <Grid container>
                    <Grid item xs={12}>
                        <LinearProgress/>
                    </Grid>
                </Grid>
            </DialogContent>
        </Dialog>
    }
}

export default SyncingDialog;