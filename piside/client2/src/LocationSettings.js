import React from "react";
import state from './State';
import TextField from '@material-ui/core/TextField';
import Typography from '@material-ui/core/Typography';
import Select from '@material-ui/core/Select';
import Button from '@material-ui/core/Button';
import MenuItem from '@material-ui/core/MenuItem';
import Radio from '@material-ui/core/Radio';
import RadioGroup from '@material-ui/core/RadioGroup';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Grid from '@material-ui/core/Grid';
import Table from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableHead from '@material-ui/core/TableHead';
import TableRow from '@material-ui/core/TableRow';
import InputAdornment from '@material-ui/core/InputAdornment';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemIcon from '@material-ui/core/ListItemIcon';
import ListItemText from '@material-ui/core/ListItemText';
import IconButton from '@material-ui/core/IconButton';
import ListItemSecondaryAction from '@material-ui/core/ListItemSecondaryAction';
import DeleteIcon from '@material-ui/icons/Delete';

const indent = {
    paddingLeft: "4ex"
};

const bold = {
    paddingTop: "3x",
    fontWeight: "bold"
};

class LocationSettings extends React.Component {
    render() {
        return <Typography component="div">
            <Typography component="h4" style={bold}>
                Preset Locations
            </Typography>
            <Grid container spacing={2}>
                <Grid item xs={12}>
                    <List component="nav">
                        <ListItem button><ListItemText primary="Home"/>
                            <ListItemSecondaryAction>
                                <IconButton edge="end" aria-label="delete">
                                    <DeleteIcon/>
                                </IconButton>
                            </ListItemSecondaryAction>
                        </ListItem>
                        <ListItem button><ListItemText primary="Farpoint"/>
                            <ListItemSecondaryAction>
                                <IconButton edge="end" aria-label="delete">
                                    <DeleteIcon/>
                                </IconButton>
                            </ListItemSecondaryAction>
                        </ListItem>
                    </List>
                </Grid>
                <Grid xs={12} style={{textAlign: "right"}}>
                    <Grid container spacing={2} justify="center" alignItems="center">
                        <Grid item>
                            <Button color="secondary" variant="contained">New Location</Button>
                        </Grid>
                    </Grid>
                </Grid>
            </Grid>
            <RadioGroup aria-label="location option" name="location_option">
                <Grid container>
                    <Grid item xs={2}/>
                    <Grid item xs={4}>
                        <FormControlLabel value="object_search"
                                          control={<Radio checked={state.goto.option === 'object_search'}/>}
                                          label="Object Search"/>
                    </Grid>
                    <Grid item xs={4}>
                        <FormControlLabel value="coordinates"
                                          control={<Radio checked={state.goto.option === 'coordinates'}/>}
                                          label="Coordinates"/>
                    </Grid>
                    <Grid item xs={2}/>
                </Grid>
            </RadioGroup>
            <TextField fullWidth placeholder="City Name or Zipcode"/>

            <Table>
                <TableHead>
                    <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell>Coords</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    <TableRow hover>
                        <TableCell>Lawrence, KS</TableCell>
                        <TableCell>38&deg;58'18"N 95&deg;14'7"W 264m</TableCell>
                    </TableRow>
                </TableBody>
            </Table>

            <Grid container spacing={2}>
                <Grid item xs={3}/>
                <Grid item xs={2}>
                    Lat
                </Grid>
                <Grid item xs={7}>
                    <TextField type="number" inputProps={{min: -90, max: 90}} InputProps={{
                        endAdornment: <InputAdornment position="end">&deg;</InputAdornment>,
                    }}/>
                </Grid>
                <Grid item xs={3}/>
                <Grid item xs={2}>
                    Long
                </Grid>
                <Grid item xs={7}>
                    <TextField type="number" inputProps={{min: -90, max: 90}} InputProps={{
                        endAdornment: <InputAdornment position="end">&deg;</InputAdornment>,
                    }}/>
                </Grid>

                <Grid item xs={3}/>
                <Grid item xs={2}>
                    Elevation
                </Grid>
                <Grid item xs={7}>
                    <TextField type="number" inputProps={{min: -1360, max: 8850}} InputProps={{
                        endAdornment: <InputAdornment position="end">m</InputAdornment>,
                    }}/>
                </Grid>
                <Grid item xs={12} style={{textAlign: "center"}}>
                    <Button variant="contained" color="primary">Save</Button>
                </Grid>
            </Grid>

        </Typography>;
    }
}

export default LocationSettings;