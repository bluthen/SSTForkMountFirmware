import React from "react";
import state from './State';
import {observer} from "mobx-react"

import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import TToggle from './TToggle';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import ObjectDialog from './ObjectDialog';
import CircularProgress from '@mui/material/CircularProgress';
import Formatting from './util/Formatting';
import {v4 as uuidv4} from 'uuid';
import {action as mobxaction} from 'mobx';


@observer
class ObjectSearch extends React.Component {
    constructor(props) {
        super(props);
        this.uuid = uuidv4();
    }

    @mobxaction
    rowClicked(event, index) {
        const result = state.goto.object_search.results[index];
        state.goto.objectdialog.all_frames = null;
        state.goto.objectdialog.wanted_coord = {frame: 'icrs', ra: result['ra'], dec: result['dec']}
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

    @mobxaction
    onSearchChanged(e) {
        state.goto.object_search.search_txt = e.currentTarget.value;
    }

    @mobxaction
    onCoordToggle(e, value) {
        if (value) {
            state.goto.object_search.coord_display = 'altaz';
        } else {
            state.goto.object_search.coord_display = 'radec';
        }
    }

    render() {
        let dialog = null, table;
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
                        <TableCell><TToggle offLabel="RA/Dec J2000" onLabel="Alt/Az"
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