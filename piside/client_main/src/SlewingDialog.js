import {computed} from 'mobx';
import {observer} from "mobx-react"
import React from "react";
import state from './State';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Button from '@mui/material/Button';
import Formatting from './util/Formatting';
import LinearProgress from '@mui/material/LinearProgress';
import Grid from '@mui/material/Grid';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import APIHelp from './util/APIHelp';
import {action as mobxaction} from "mobx";

@observer
class SlewingDialog extends React.Component {

    handleCancelSlew() {
        APIHelp.cancelSlew();
    }

    @computed
    get slewProgress() {
        //TODO: This needs to be better about loops, maybe can get distance from server?
        // then it can be determinate.
        return null;
    }

    @mobxaction
    @computed
    get target() {
        console.error(state.goto.slewingdialog.target);
        if (!state.goto.slewingdialog.target) {
            return '';
        }
        if (state.goto.slewingdialog.frame === 'steps') {
            return state.goto.slewingdialog.target.ra_steps + '/' + state.goto.slewingdialog.target.dec_steps;
        }
        const ra = state.goto.slewingdialog.target.ra || state.goto.slewingdialog.target.ha;
        const dec = state.goto.slewingdialog.target.dec;
        const alt = state.goto.slewingdialog.target.alt;
        const az = state.goto.slewingdialog.target.az;

        if (ra) {
            return Formatting.degRA2Str(ra) + '/' +
                Formatting.degDEC2Str(dec)
        } else if (alt) {
            return Formatting.degDEC2Str(alt) + '/' +
                Formatting.degDEC2Str(az)
        }

        return '';
    }

    @computed
    get current() {
        if (state.goto.slewingdialog.frame === 'steps') {
            return state.status.rp + '/' + state.status.dp;
        }
        let ra, dec;
        if (state.goto.slewingdialog.frame === 'altaz' || state.goto.slewingdialog.frame === 'park') {
            const alt = state.status.alt;
            const az = state.status.az;
            return Formatting.degDEC2Str(alt) + '/' + Formatting.degDEC2Str(az);
        } else if (state.goto.slewingdialog.frame === 'icrs') {
            ra = state.status.icrs_ra;
            dec = state.status.icrs_dec;
        } else if (state.goto.slewingdialog.frame === 'tete') {
            ra = state.status.tete_ra;
            dec = state.status.tete_dec;
        } else {
            ra = state.status.hadec_ha;
            dec = state.status.hadec_dec;
        }
        return Formatting.degRA2Str(ra) + '/' + Formatting.degDEC2Str(dec);
    }

    render() {
        let variant = 'determinate';
        if (this.slewProgress === null) {
            variant = 'indeterminate';
        }
        const target = this.target;
        let arrow = null;
        if (target) {
            arrow = <ArrowForwardIcon/>
        }

        let title = 'Slewing';
        if (state.goto.slewingdialog.frame === 'park') {
            title = 'Parking';
        }

        let frameLabel = 'J2000'
        if (state.goto.slewingdialog.frame === 'tete') {
            frameLabel = 'JNow'
        } else if (state.goto.slewingdialog.frame === 'hadec') {
            frameLabel = 'HA/Dec'
        } else if (state.goto.slewingdialog.frame === 'altaz' || state.goto.slewingdialog.frame === 'parking') {
            frameLabel = 'Alt/Az'
        }

        return <Dialog open={true} maxwidth="xs">
            <DialogTitle>{title}</DialogTitle>
            <DialogContent>
                <Grid container>
                    <Grid item xs={12}>
                        Frame: {frameLabel}
                    </Grid>
                    <Grid item xs={12}>
                        {this.current} {arrow} {this.target}
                    </Grid>
                    <Grid item xs={12}>
                        <LinearProgress variant={variant} value={this.slewProgress}/>
                    </Grid>
                </Grid>
            </DialogContent>
            <DialogActions>
                <Button color="primary" onClick={this.handleCancelSlew}>Cancel Slew</Button>
            </DialogActions>
        </Dialog>
    }
}

export default SlewingDialog;