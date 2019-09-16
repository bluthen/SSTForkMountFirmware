import {computed} from 'mobx';
import {observer} from "mobx-react"
import React from "react";
import state from './State';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogContentText from '@material-ui/core/DialogContentText';
import DialogTitle from '@material-ui/core/DialogTitle';
import InputLabel from '@material-ui/core/InputLabel';
import Button from '@material-ui/core/Button';
import Formatting from './util/Formatting';
import LinearProgress from '@material-ui/core/LinearProgress';
import Grid from '@material-ui/core/Grid';
import ArrowForwardIcon from '@material-ui/icons/ArrowForward';
import APIHelp from './util/APIHelp';

@observer
class SlewingDialog extends React.Component {

    handleCancelSlew() {
        APIHelp.cancelSlew();
    }

    @computed
    get slewProgress() {
        //TODO: This needs to be better about loops, maybe can get distance from server?
        return null;
        const tra = state.goto.slewingdialog.target.ra;
        const tdec = state.goto.slewingdialog.target.dec;
        const talt = state.goto.slewingdialog.target.alt;
        const taz = state.goto.slewingdialog.target.az;

        const sra = state.goto.slewingdialog.start.ra;
        const sdec = state.goto.slewingdialog.start.dec;
        const salt = state.goto.slewingdialog.start.alt;
        const saz = state.goto.slewingdialog.start.az;

        const ra = state.status.ra;
        const dec = state.status.dec;
        const alt = state.status.alt;
        const az = state.status.az;

        if (tra !== null && sra !== null) {
            const total = Math.abs(tra - sra) + Math.abs(tdec - sdec);
            const now = Math.abs(tra - ra) + Math.abs(tdec - dec);
            return 100 * (1-((total - now) / total));
        } else if (talt !== null && salt !== null) {
            const total = Math.abs(talt - salt) + Math.abs(taz - saz);
            const now = Math.abs(talt - alt) + Math.abs(taz - az);
            return 100 * (1-((total - now) / total));
        }
        return null;
    }

    @computed
    get target() {
        const ra = state.goto.slewingdialog.target.ra;
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
        const talt = state.goto.slewingdialog.target.alt;

        const ra = state.status.ra;
        const dec = state.status.dec;
        const alt = state.status.alt;
        const az = state.status.az;

        if (talt || state.goto.slewingtype === 'altaz' || state.goto.slewingtype === 'park') {
            return Formatting.degDEC2Str(alt) + '/' + Formatting.degDEC2Str(az);
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
        if(state.goto.slewingtype === 'park') {
            title='Parking';
        }

        return <Dialog open maxwidth="xs">
            <DialogTitle>{title}</DialogTitle>
            <DialogContent>
                <Grid container>
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