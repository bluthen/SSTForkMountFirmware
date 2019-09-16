import React from "react";
import Dialog from '@material-ui/core/Dialog';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '@material-ui/core/DialogTitle';
import LinearProgress from '@material-ui/core/LinearProgress';
import Grid from '@material-ui/core/Grid';


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