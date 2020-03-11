import React, {forwardRef} from "react";
import Grid from '@material-ui/core/Grid';
import APIHelp from './util/APIHelp';
import uuidv4 from 'uuid/v4';
import TextField from '@material-ui/core/TextField';
import InputAdornment from '@material-ui/core/InputAdornment';
import state from './State';
import Button from '@material-ui/core/Button';
import {observer} from "mobx-react";
import {observe} from 'mobx';
import Formating from './util/Formatting';
import TableContainer from '@material-ui/core/TableContainer';
import Table from '@material-ui/core/Table';
import TableHead from '@material-ui/core/TableHead';
import TableBody from '@material-ui/core/TableBody';
import TableRow from '@material-ui/core/TableRow';
import TableCell from '@material-ui/core/TableCell';
import Paper from '@material-ui/core/Paper';
import Checkbox from '@material-ui/core/Checkbox';



const component_map = {
    correction_factor: {display: 'Correction Factor', type: 'number', min: 0, endAdornment: '%'},
    ra_ticks_per_degree: {display: 'RA Stepper Scale', type: 'number', min: 0, endAdornment: 'Step/°'},
    ra_encoder_pulse_per_degree: {
        display: 'RA Encoder Scale',
        type: 'number',
        endAdornment: 'pulse/°'
    },
    dec_ticks_per_degree: {display: 'DEC Stepper Scale', type: 'number', min: 0, endAdornment: 'Step/°'},
    dec_encoder_pulse_per_degree: {
        display: 'DEC Encoder Scale',
        type: 'number',
        endAdornment: 'pulse/°'
    }
};

function updateValues() {
    // newRate = origRate/(percentError + 1);
    state.calibrationTable.ra_ticks_per_degree = state.advancedSettings.ra_ticks_per_degree /
        (state.calibrationTable.correction_factor / 100.0 * state.calibrationTable.mean_percent_ra / 100.0 + 1.0);
    state.calibrationTable.dec_ticks_per_degree = state.advancedSettings.dec_ticks_per_degree /
        (state.calibrationTable.correction_factor / 100.0 * state.calibrationTable.mean_percent_dec / 100.0 + 1.0);

    state.calibrationTable.ra_encoder_pulse_per_degree = state.advancedSettings.ra_encoder_pulse_per_degree /
        (state.calibrationTable.correction_factor / 100.0 * state.calibrationTable.mean_percent_ra / 100.0 + 1.0);
    state.calibrationTable.dec_encoder_pulse_per_degree = state.advancedSettings.dec_encoder_pulse_per_degree /
        (state.calibrationTable.correction_factor / 100.0 * state.calibrationTable.mean_percent_dec / 100.0 + 1.0);
}

function updateTableData() {
    const newData = [];
    state.calibrationLogs.forEach((r) => {
        const wantedMoveRA = Formating.deltaDegRA(r.slewfrom.ra, r.slewto.ra);
        const wantedMoveDec = Formating.deltaDegDec(r.slewto.dec, r.slewfrom.dec);
        const actualMoveRA = Formating.deltaDegRA(r.slewfrom.ra, r.sync.ra);
        const actualMoveDec = Formating.deltaDegDec(r.sync.dec, r.slewfrom.dec);
        const errorRA = actualMoveRA - wantedMoveRA;
        const errorDec = actualMoveDec - wantedMoveDec;
        let percentErrorRA = 0;
        if (wantedMoveRA !== 0) {
            percentErrorRA = errorRA / wantedMoveRA;
        }
        let percentErrorDec = 0;
        if (wantedMoveDec !== 0) {
            percentErrorDec = errorDec / wantedMoveDec;
        }

        newData.push({
            slewfrom: Formating.degRA2Str(r.slewfrom.ra) + ' / ' + Formating.degDEC2Str(r.slewfrom.dec),
            slewto: Formating.degRA2Str(r.slewto.ra) + ' / ' + Formating.degDEC2Str(r.slewto.dec),
            sync: Formating.degRA2Str(r.sync.ra) + ' / ' + Formating.degDEC2Str(r.sync.dec),
            errorRA: Formating.deg2arcseconds(errorRA),
            errorDec: Formating.deg2arcseconds(errorDec),
            percentErrorRA: percentErrorRA * 100.0,
            percentErrorDec: percentErrorDec * 100.0
        });
        // Correction would be:
        // newRate = origRate/(percentError + 1);
    });
    state.calibrationTable.table_data.replace(newData);
}

observe(state.calibrationTable, 'correction_factor', updateValues);
observe(state.calibrationTable, 'mean_percent_ra', updateValues);
observe(state.calibrationTable, 'mean_percent_dec', updateValues);


function makeOnChange(key, setting_map) {
    return (e) => {
        if (setting_map.type === 'number') {
            const v = e.currentTarget.value;
            if ((v !== '' && v !== '-' && v !== '-.') || (settings_map.hasOwnProperty('min') && settings_map.min >= 0)) {
                state.calibrationTable[key] = parseFloat(v);
            } else {
                state.calibrationTable[key] = v;
            }
        } else if (setting_map.type === 'boolean') {
            let v = e.target.checked;
            if (setting_map.map) {
                v = setting_map.map[v];
            }
            state.calibrationTable[key] = v;
        }
    }
}

function updateStats() {
    let selectedLength = state.calibrationTable.table_select.length;
    if (state.calibrationTable.select_all) {
        selectedLength = state.calibrationTable.table_data.length;
    }

    let pRA = 0, pDec = 0;
    if(state.calibrationTable.select_all) {
        for (let i = 0; i < selectedLength; i++) {
            const row = state.calibrationTable.table_data[i];
            pRA += row.percentErrorRA;
            pDec += row.percentErrorDec;
        }
    } else {
        for (let i = 0; i < selectedLength; i++) {
            const idx = state.calibrationTable.table_select[i];
            const row = state.calibrationTable.table_data[idx];
            pRA += row.percentErrorRA;
            pDec += row.percentErrorDec;
        }
    }
    if (selectedLength === 0) {
        state.calibrationTable.mean_percent_ra = 0;
        state.calibrationTable.mean_percent_dec = 0;
    } else {
        state.calibrationTable.mean_percent_ra = pRA / selectedLength;
        state.calibrationTable.mean_percent_dec = pDec / selectedLength;
    }
}

@observer
class CalibrationTable extends React.Component {
    constructor(props) {
        super(props);
        this.logInterval = null;
        this.uuid = uuidv4();
        this.tableRef = React.createRef();
        this.clDispose = null;
        this.handleTableSelectionChange = this.handleTableSelectionChange.bind(this);
    }

    refreshTable() {
        updateTableData();
        if (this.tableRef) {
            this.tableRef.current && this.tableRef.current.onQueryChange();
        }
    }

    componentDidMount() {
        this.clDispose = observe(state, 'calibrationLogs', () => {
            this.refreshTable();
        });
        APIHelp.fetchSettings();
        if (this.logInterval) {
            clearInterval(this.logInterval);
        }
        APIHelp.getLogData('calibration').then(() => {
            // Starts with no selection
            state.calibrationTable.table_select.replace([]);
            updateStats();
            updateValues();
        });
        this.logInterval = setInterval(() => {
            APIHelp.getLogData('calibration');
            updateTableData();
        }, 1500);
    }

    componentWillUnmount() {
        clearInterval(this.logInterval);
        this.logInterval = null;
        this.clDispose();
    }

    handleSave() {
        const resp = {};
        if (state.advancedSettings.ra_use_encoder) {
            resp.ra_encoder_pulse_per_degree = state.calibrationTable.ra_encoder_pulse_per_degree;
        } else {
            resp.ra_ticks_per_degree = state.calibrationTable.ra_ticks_per_degree;
        }
        if (state.advancedSettings.dec_use_encoder) {
            resp.dec_encoder_pulse_per_degree = state.calibrationTable.dec_encoder_pulse_per_degree;
        } else {
            resp.dec_ticks_per_degree = state.calibrationTable.dec_ticks_per_degree;
        }
        APIHelp.saveSettings(resp);
    }

    handleClear() {
        APIHelp.clearLog('calibration').then(()=> {
            APIHelp.getLogData('calibration').then(() => {
                state.calibrationTable.table_select.replace([]);
                updateTableData();
                updateStats();
            });
        });
    }

    handleTableSelectionChange(event) {
        if (state.calibrationTable.select_all) {
            state.calibrationTable.select_all = false;
            state.calibrationTable.table_select.replace(Array.from(Array(state.calibrationTable.table_data.length).keys()));
        }
        const checked = event.target.checked;
        const idx = parseInt(event.target.value, 10);
        if (!state.calibrationTable.table_select.includes(idx) && checked) {
            state.calibrationTable.table_select.push(idx);
        } else {
            state.calibrationTable.table_select.remove(idx);
        }
        updateStats();
    }

    handleSelectAll(event) {
        state.calibrationTable.table_select.replace([]);
        state.calibrationTable.select_all = event.target.checked;
        updateStats();
    }

    render() {
        let settingsAdjust = [];

        for (let key in component_map) {
            if (key === 'ra_ticks_per_degree' && state.advancedSettings.ra_use_encoder) {
                continue;
            }
            if (key === 'dec_ticks_per_degree' && state.advancedSettings.dec_use_encoder) {
                continue;
            }
            if (key === 'ra_encoder_pulse_per_degree' && !state.advancedSettings.ra_use_encoder) {
                continue;
            }
            if (key === 'dec_encoder_pulse_per_degree' && !state.advancedSettings.dec_use_encoder) {
                continue;
            }

            settingsAdjust.push(<Grid item key={key + this.uuid} xs={4}>
                <TextField value={state.calibrationTable[key]}
                           label={component_map[key].display}
                           key={key}
                           type={component_map[key].type}
                           inputProps={{
                               min: component_map[key].min,
                               max: component_map[key].max,
                               step: component_map[key].step
                           }} InputProps={{
                    endAdornment: <InputAdornment style={{whiteSpace: 'nowrap'}}
                                                  position="end">{component_map[key].endAdornment}</InputAdornment>
                }} onChange={makeOnChange(key, component_map[key])}/>
            </Grid>);
        }

        const tableRows = [];

        for (let i = 0; i < state.calibrationTable.table_data.length; i++) {
            const row1 = state.calibrationTable.table_data[i];
            tableRows.push(<TableRow key={"row" + i}>
                <TableCell>
                    <Checkbox checked={state.calibrationTable.select_all ? true : state.calibrationTable.table_select.includes(i)}
                              onChange={this.handleTableSelectionChange} value={i}/>
                </TableCell>
                <TableCell>{row1.slewfrom}</TableCell>
                <TableCell>{row1.slewto}</TableCell>
                <TableCell>{row1.sync}</TableCell>
                <TableCell>{row1.errorRA.toFixed(0)}</TableCell>
                <TableCell>{row1.errorDec.toFixed(0)}</TableCell>
                <TableCell>{row1.percentErrorRA.toFixed(2)}</TableCell>
                <TableCell>{row1.percentErrorDec.toFixed(2)}</TableCell>
            </TableRow>);
        }


        return (
            <Grid container spacing={2} justify="center" alignContent="center" alignItems="center">
                <Grid item xs={12}>
                    <h2>Calibration Info</h2>
                    <TableContainer component={Paper}>
                        <Table aria-label="calibration table">
                            <TableHead>
                                <TableRow>
                                    <TableCell>
                                        <Checkbox checked={state.calibrationTable.select_all} onChange={this.handleSelectAll}/>
                                    </TableCell>
                                    <TableCell>SlewFrom</TableCell>
                                    <TableCell>SlewTo</TableCell>
                                    <TableCell>Sync</TableCell>
                                    <TableCell>Error RA(")</TableCell>
                                    <TableCell>Error Dec(")</TableCell>
                                    <TableCell>Error RA(%)</TableCell>
                                    <TableCell>Error Dec(%)</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {tableRows}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Grid>
                <Grid item xs={12} style={{textAlign: "right"}}>
                    <Button color="primary" variant="contained" onClick={this.handleClear}>Clear Calibration Data</Button>
                </Grid>

                <Grid item xs={12}>
                    Rows selected are used to calculate the values below.
                </Grid>
                <Grid item xs={6}>
                    Mean Error RA (%): {state.calibrationTable.mean_percent_ra}
                </Grid>
                <Grid item xs={6}>
                    Mean Error Dec (%): {state.calibrationTable.mean_percent_dec}
                </Grid>
                {settingsAdjust}
                <Grid item xs={12} style={{textAlign: "center"}}>
                    <Button color="primary" variant="contained" onClick={this.handleSave}>Save</Button>
                </Grid>
            </Grid>
        )
    }
}

export default CalibrationTable;