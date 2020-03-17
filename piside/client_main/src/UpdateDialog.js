import {observer} from "mobx-react"
import React from "react";
import state from './State';
import Dialog from '@material-ui/core/Dialog';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '@material-ui/core/DialogTitle';
import Grid from '@material-ui/core/Grid';
import CircularProgress from '@material-ui/core/CircularProgress';


@observer
class InfoDialog extends React.Component {

    render() {
        return <Dialog open maxwidth="xs">
            <DialogTitle>Updating</DialogTitle>
            <DialogContent>
                <Grid container>
                    <Grid item xs={12} style={{textAlign: "center"}}>
                        <CircularProgress/><br/>
                        {state.updateDialog.timer}
                    </Grid>
                </Grid>
            </DialogContent>
        </Dialog>
    }
}

export default InfoDialog;