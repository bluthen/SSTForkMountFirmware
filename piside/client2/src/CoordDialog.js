import React from "react";
import state from './State';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogContentText from '@material-ui/core/DialogContentText';
import DialogTitle from '@material-ui/core/DialogTitle';
import InputLabel from '@material-ui/core/InputLabel';
import Button from '@material-ui/core/Button';
import Grid from '@material-ui/core/Grid';



class CoordDialog extends React.Component {
    handleClose() {
        state.goto.coorddialog.shown = false;
    }

    render() {
        return <Dialog open maxwidth="xs" onClose={this.handleClose}>
            <DialogTitle>Object Title</DialogTitle>
            <DialogContent>
            <Grid container >
                <Grid item xs={6}>
                    <h3>RA/DEC</h3>
                    dddhmm'ss"/dd&deg;mm'ss"

                </Grid>
                <Grid item xs={6}>
                    <h3>Alt/Az</h3>
                    dd&deg;mmmsss/ddd&deg;mm'ss"
                </Grid>
                <Grid item xs={12}>
                    Altitude vs Hour graph
                </Grid>
            </Grid>
            </DialogContent>
                <DialogActions>
                    <Button color="primary" onClick={this.handleClose}>Cancel</Button>
                    <Button color="primary">Sync</Button>
                    <Button color="primary">Slew</Button>
                </DialogActions>
        </Dialog>;
    }
}

export default CoordDialog;