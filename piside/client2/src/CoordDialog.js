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
    get RADecStr() {
        if (state.goto.coorddialog.radeg !== null && state.goto.coorddialog.decdeg !== null) {
            return Formatting.degRA2Str(state.goto.coorddialog.radeg) + '/' + Formatting.degDEC2Str(state.goto.coorddialog.decdeg)
        } else {
            return <LinearProgress/>;
        }
    }

    @computed
    get altAzStr() {
        if (state.goto.coorddialog.altdeg !== null && state.goto.coorddialog.azdeg !== null) {
            return Formatting.degDEC2Str(state.goto.coorddialog.altdeg) + '/' + Formatting.degDEC2Str(state.goto.coorddialog.azdeg);
        } else {
            return <LinearProgress/>
        }
    }

    handleSlewClick() {
        if (state.goto.coordinates.type === 'radec') {
            APIHelp.slewTo({ra: state.goto.coorddialog.radeg, dec: state.goto.coorddialog.decdeg});
        } else {
            APIHelp.slewTo({alt: state.goto.coorddialog.altdeg, az: state.goto.coorddialog.azdeg});
        }
        this.handleClose();
    }

    handleSyncClick() {
        if (state.goto.coordinates.type === 'radec') {
            APIHelp.sync({ra: state.goto.coorddialog.radeg, dec: state.goto.coorddialog.decdeg});
        } else {
            APIHelp.sync({alt: state.goto.coorddialog.altdeg, az: state.goto.coorddialog.azdeg});
        }
        this.handleClose();
    }

    render() {
        console.log('render');
        return <Dialog open maxwidth="xs" onClose={this.handleClose}>
            <DialogTitle>Object Title</DialogTitle>
            <DialogContent>
                <Grid container>
                    <Grid item xs={6}>
                        <h3>RA/DEC</h3>
                        {this.RADecStr}
                    </Grid>
                    <Grid item xs={6}>
                        <h3>Alt/Az</h3>
                        {this.altAzStr}
                    </Grid>
                    <Grid item xs={12}>
                        <AltChart width={500} height={200} ra={state.goto.coorddialog.radeg}
                                  dec={state.goto.coorddialog.decdeg} alt={state.goto.coorddialog.altdeg}
                                  az={state.goto.coorddialog.azdeg}/>
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