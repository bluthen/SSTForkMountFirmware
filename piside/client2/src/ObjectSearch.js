import React from "react";
import state from './State';
import {observer} from "mobx-react"

import Typography from '@material-ui/core/Typography';
import TextField from '@material-ui/core/TextField';
import Grid from '@material-ui/core/Grid';
import TToggle from './TToggle';
import Table from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableHead from '@material-ui/core/TableHead';
import TableRow from '@material-ui/core/TableRow';
import ObjectDialog from './ObjectDialog';
import CircularProgress from '@material-ui/core/CircularProgress';
import Formatting from './util/Formatting';
import uuidv4 from 'uuid/v4';


@observer
class ObjectSearch extends React.Component {
    constructor(props) {
        super(props);
        this.uuid = uuidv4();
    }

    rowClicked(event, index) {
        const result = state.goto.object_search.results[index];
        state.goto.objectdialog.radeg = result['ra'];
        state.goto.objectdialog.decdeg = result['dec'];
        state.goto.objectdialog.graphdata = [];
        state.goto.objectdialog.ra = Formatting.degRA2Str(result['ra']);
        state.goto.objectdialog.dec = Formatting.degDEC2Str(result['dec']);
        state.goto.objectdialog.alt = Formatting.degDEC2Str(result['alt']);
        state.goto.objectdialog.az = Formatting.degDEC2Str(result['az']);
        if (result.type !== 'planet') {
            state.goto.objectdialog.mag = result['mag'];
        } else {
            state.goto.objectdialog.mag = '';
        }

        if (result.type !== 'planet' && result.type !== 'star') {
            let size = '' + result.r1;
            if (result.r2) {
                size += 'x' + result.r2;
            }
            state.goto.objectdialog.size = size;
        } else {
            state.goto.objectdialog.size = '';
        }

        state.goto.objectdialog.shown = true;
    }

    onSearchChanged(e) {
        const v = e.currentTarget.value;
        state.goto.object_search.search_txt = v;
    }

    onCoordToggle(e, value) {
        if (value) {
            state.goto.object_search.coord_display = 'altaz';
        } else {
            state.goto.object_search.coord_display = 'radec';
        }
    }

    render() {
        let dialog = null, table = null;
        if (state.goto.objectdialog.shown) {
            dialog = <ObjectDialog/>;
        }
        if (state.goto.object_search.searching) {
            table = <CircularProgress/>;
        } else if (state.goto.object_search.results.length > 0) {
            let tableRows = [];
            for (let i = 0; i < state.goto.object_search.results.length; i++) {
                const result = state.goto.object_search.results[i];
                let coord = '';
                if (state.goto.object_search.coord_display === 'radec') {
                    coord = Formatting.degRA2Str(result.ra) + '/' + Formatting.degDEC2Str(result.dec);
                } else {
                    coord = Formatting.degDEC2Str(result.alt) + '/' + Formatting.degDEC2Str(result.az);
                }
                let name;
                if (result.type === 'planet') {
                    name = result.name;
                } else if (result.type === 'star') {
                    name = result.bf + ',' + result.proper;
                } else {
                    name = result.search;
                    name = name.replace(/^\|/, '');
                    name = name.replace(/[| ]*$/, '');
                    name = name.replace(/\|/g, ',');
                }
                const click = ((index) => {
                    return (e) => {
                        this.rowClicked(e, index);
                    }
                })(i);


                tableRows.push(<TableRow key={this.uuid + '_' + i} hover onClick={click}
                                         style={{cursor: "pointer"}}>
                        <TableCell>{name}</TableCell>
                        <TableCell>{coord}</TableCell>
                    </TableRow>
                )
            }
            table = <Table>
                <TableHead>
                    <TableRow>
                        <TableCell>Object Name</TableCell>
                        <TableCell><TToggle offLabel="RA/Dec" onLabel="Alt/Az"
                                            checked={state.goto.object_search.coord_display === 'altaz'}
                                            onChange={this.onCoordToggle}/></TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {tableRows}
                </TableBody>
            </Table>

        } else {
            table = <Typography component="div">No results</Typography>;
        }
        return <Typography component="div">
            <TextField value={state.goto.object_search.search_txt || ''} fullWidth
                       placeholder="Search (Example Andromeda Galaxy or M 31)" onChange={this.onSearchChanged}/>
            {table}
            {dialog}
        </Typography>;
    }
}

export default ObjectSearch;