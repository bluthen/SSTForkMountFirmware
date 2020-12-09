import React from "react";
import state from './State';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '@material-ui/core/DialogTitle';
import Button from '@material-ui/core/Button';
import Grid from '@material-ui/core/Grid';
import AltChart from './AltChart';
import LinearProgress from '@material-ui/core/LinearProgress';
import Formatting from './util/Formatting';
import {observer} from "mobx-react"
import {computed} from 'mobx';
import APIHelp from './util/APIHelp';

//TODO: Make more generic and merge with ObjectDialog?

@observer
class CoordDialog extends React.Component {
    constructor(props) {
        super(props);
        this.handleSlewClick = this.handleSlewClick.bind(this);
        this.handleSyncClick = this.handleSyncClick.bind(this);
    }

    handleClose() {
        state.goto.coorddialog.shown = false;
    }

    @computed
    get ICRSStr() {
        if (state.goto.coorddialog.all_frames !== null) {
            return Formatting.degRA2Str(state.goto.coorddialog.all_frames.icrs.ra) + '/' + Formatting.degDEC2Str(state.goto.coorddialog.all_frames.icrs.dec)
        } else {
            return <LinearProgress/>;
        }
    }

    @computed
    get TETEStr() {
        if (state.goto.coorddialog.all_frames !== null) {
            return Formatting.degRA2Str(state.goto.coorddialog.all_frames.tete.ra) + '/' + Formatting.degDEC2Str(state.goto.coorddialog.all_frames.tete.dec)
        } else {
            return <LinearProgress/>;
        }
    }

    @computed
    get HADecStr() {
        if (state.goto.coorddialog.all_frames !== null) {
            return Formatting.degRA2Str(state.goto.coorddialog.all_frames.hadec.ha) + '/' + Formatting.degDEC2Str(state.goto.coorddialog.all_frames.hadec.dec)
        } else {
            return <LinearProgress/>;
        }
    }

    @computed
    get altAzStr() {
        if (state.goto.coorddialog.all_frames !== null) {
            return Formatting.degDEC2Str(state.goto.coorddialog.all_frames.altaz.alt) + '/' + Formatting.degDEC2Str(state.goto.coorddialog.all_frames.altaz.az);
        } else {
            return <LinearProgress/>
        }
    }

    handleSlewClick() {
        APIHelp.slewTo(state.goto.coorddialog.wanted_coord);
        this.handleClose();
    }

    handleSyncClick() {
        APIHelp.sync(state.goto.coorddialog.wanted_coord);
        this.handleClose();
    }

    render() {
        return <Dialog open maxwidth="xs" onClose={this.handleClose}>
            <DialogTitle>Object Title</DialogTitle>
            <DialogContent>
                <Grid container>
                    <Grid item xs={6}>
                        <b>RA/Dec (JNow):</b>
                    </Grid>
                    <Grid item xs={6}>
                        {this.TETEStr}
                    </Grid>
                    <Grid item xs={6}>
                        <b>RA/Dec (J2000):</b>
                    </Grid>
                    <Grid item xs={6}>
                        {this.ICRSStr}
                    </Grid>
                    <Grid item xs={6}>
                        <b>Alt/Az:</b>
                    </Grid>
                    <Grid item xs={6}>
                        {this.altAzStr}
                    </Grid>
                    <Grid item xs={6}>
                        <b>HA/Dec:</b>
                    </Grid>
                    <Grid item xs={6}>
                        {this.HADecStr}
                    </Grid>
                    <Grid item xs={12}>
                        <AltChart width={500} height={200} wanted={state.goto.coorddialog.wanted_coord}/>
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

export default CoordDialog;