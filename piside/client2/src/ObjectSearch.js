import React from "react";
import Typography from '@material-ui/core/Typography';
import TextField from '@material-ui/core/TextField';
import Grid from '@material-ui/core/Grid';
import CoordDisplayToggle from './CoordDisplayToggle';
import Table from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableHead from '@material-ui/core/TableHead';
import TableRow from '@material-ui/core/TableRow';


class ObjectSearch extends React.Component {
    rowClicked(event) {

    }

    render() {
        return <Typography component="div">
                    <TextField fullWidth placeholder="Search (Example Andromeda Galaxy or M 31)"/>
            <Table>
                <TableHead>
                    <TableRow>
                        <TableCell>Object Name</TableCell>
                        <TableCell><CoordDisplayToggle/></TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    <TableRow hover onClick={this.rowClicked}>
                        <TableCell>Andromedia</TableCell>
                        <TableCell>04h42m22s/+41&deg;15'08"</TableCell>
                    </TableRow>
                </TableBody>
            </Table>
        </Typography>;
    }
}

export default ObjectSearch;