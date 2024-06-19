import {observer} from "mobx-react"
import React from "react";
import state from './State';
import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Grid from '@mui/material/Grid';
import CircularProgress from '@mui/material/CircularProgress';


@observer
class InfoDialog extends React.Component {

    render() {
        return <Dialog open={true} maxwidth="xs">
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