import React from "react";
import state from './State';
import {observer} from "mobx-react"
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogContentText from '@material-ui/core/DialogContentText';
import DialogTitle from '@material-ui/core/DialogTitle';
import InputLabel from '@material-ui/core/InputLabel';
import Button from '@material-ui/core/Button';
import Grid from '@material-ui/core/Grid';
import AltChart from './AltChart';
import APIHelp from './util/APIHelp';

@observer
class ObjectDialog extends React.Component {
    constructor(props) {
        super(props);
        this.handleSlewClick = this.handleSlewClick.bind(this);
        this.handleSyncClick = this.handleSyncClick.bind(this);
    }

    handleClose() {
        state.goto.objectdialog.shown = false;
    }

    handleSlewClick() {
        APIHelp.slewTo({ra: state.goto.objectdialog.radeg, dec: state.goto.objectdialog.decdeg});
        this.handleClose();
    }

    handleSyncClick() {
        APIHelp.sync({ra: state.goto.objectdialog.radeg, dec: state.goto.objectdialog.decdeg});
        this.handleClose();
    }

    render() {
        return <Dialog open maxwidth="xs" onClose={this.handleClose}>
            <DialogTitle>Object Title</DialogTitle>
            <DialogContent>
                <Grid container>
                    <Grid item xs={6}>
                        <h3>RA/DEC</h3>
                        {state.goto.objectdialog.ra}/{state.goto.objectdialog.dec}
                    </Grid>
                    <Grid item xs={6}>
                        <h3>Alt/Az</h3>
                        {state.goto.objectdialog.alt}/{state.goto.objectdialog.az}
                    </Grid>
                    <Grid item xs={6}>
                        <h3>Magnitude</h3>
                        {state.goto.objectdialog.mag}
                    </Grid>
                    <Grid item xs={6}>
                        <h3>Size</h3>
                        {state.goto.objectdialog.size}
                    </Grid>
                    <Grid item xs={12} textalign="center">
                        <AltChart width={500} height={200} ra={state.goto.objectdialog.radeg}
                                  dec={state.goto.objectdialog.decdeg} alt={null} az={null}/>
                    </Grid>
                </Grid>
            </DialogContent>
            <DialogActions>
                <Button color="primary" onClick={this.handleClose}>Cancel</Button>
                <Button color="primary" onClick={this.handleSyncClick}>Sync</Button>
                <Button color="primary" onClick={this.handleSlewClick}>Slew</Button>
            </DialogActions>
        </Dialog>;
    }
}

export default ObjectDialog;