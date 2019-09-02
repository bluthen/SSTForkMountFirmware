import React from "react";
import state from './State';
import {observer} from "mobx-react"
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

import Fab from '@material-ui/core/Fab';
import AddIcon from '@material-ui/icons/Add';

import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogContentText from '@material-ui/core/DialogContentText';
import DialogTitle from '@material-ui/core/DialogTitle';
import InputLabel from '@material-ui/core/InputLabel';

import uuidv4 from 'uuid/v4';

const indent = {
    paddingLeft: "4ex"
};

const bold = {
    paddingTop: "3x",
    fontWeight: "bold"
};

class CitySearch extends React.Component {
    render() {
        return <><TextField fullWidth autoFocus={this.props.autoFocus} placeholder="City Name or Zipcode"/>
        <Table>
            <TableHead>
                <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Coords</TableCell>
                </TableRow>
            </TableHead>
            <TableBody>
                <TableRow hover onClick={() => {
                    this.props.onCityClick('Lawrence, KS', 38.23, -95.232, 264)
                }} style={{cursor: "pointer"}}>
                    <TableCell>Lawrence, KS</TableCell>
                    <TableCell>38&deg;58'18"N 95&deg;14'7"W 264m</TableCell>
                </TableRow>
            </TableBody>
        </Table>
        </>;
    }
}

function numE(v) {
    if (v === null || isNaN(v)) {
        return '';
    }
    return v;
}

class GeoCoordinateInput extends React.Component {
    constructor(props) {
        super(props);
        this.uuid = uuidv4();
        this.state = {
            latitude: numE(props.latitude),
            longitude: numE(props.longitude),
            elevation: numE(props.elevation)
        };
        this.onLatitudeChange = this.onLatitudeChange.bind(this);
        this.onLongitudeChange = this.onLongitudeChange.bind(this);
        this.onElevationChange = this.onElevationChange.bind(this);
    }

    onLatitudeChange(e) {
        let v = parseFloat(e.currentTarget.value);
        if (isNaN(v)) {
            v = null;
        }
        this.setState({latitude: numE(v)});
        this.props.onChange(v, this.state.longitude, this.state.elevation);
    }

    onLongitudeChange(e) {
        let v = parseFloat(e.currentTarget.value);
        if (isNaN(v)) {
            v = null;
        }
        this.setState({longitude: numE(v)});
        this.props.onChange(this.state.latitude, this.state.longitude, v);
    }

    onElevationChange(e) {
        let v = parseFloat(e.currentTarget.value);
        if (isNaN(v)) {
            v = null;
        }
        this.setState({elevation: numE(v)});
        this.props.onChange(this.state.latitude, this.state.longitude, v);
    }

    render() {
        return <Grid container spacing={2}>
            <Grid item xs={3}/>
            <Grid item xs={2}>
                <InputLabel htmlFor={this.uuid + '_latitude'}>Latitude</InputLabel>
            </Grid>
            <Grid item xs={7}>
                <TextField id={this.uuid + '_latitude'} onChange={this.onLatitudeChange} value={this.state.latitude}
                           autoFocus={this.props.autoFocus}
                           error={!!this.props.latitude_error} label={this.props.latitude_error} type="number"
                           inputProps={{min: -90, max: 90}} InputProps={{
                    endAdornment: <InputAdornment position="end">&deg;</InputAdornment>,
                }}/>
            </Grid>
            <Grid item xs={3}/>
            <Grid item xs={2}>
                <InputLabel htmlFor={this.uuid + '_longitude'}>Longitude</InputLabel>
            </Grid>
            <Grid item xs={7}>
                <TextField id={this.uuid + '_longitude'} onChange={this.onLongitudeChange} value={this.state.longitude}
                           error={!!this.props.longitude_error}
                           label={this.props.longitude_error} type="number" inputProps={{min: -180, max: 180}}
                           InputProps={{
                               endAdornment: <InputAdornment position="end">&deg;</InputAdornment>,
                           }}/>
            </Grid>

            <Grid item xs={3}/>
            <Grid item xs={2}>
                <InputLabel htmlFor={this.uuid + '_elevation'}>Elevation</InputLabel>
            </Grid>
            <Grid item xs={7}>
                <TextField id={this.uuid + '_elevation'} onChange={this.onElevationChange} value={this.state.elevation}
                           error={!!this.props.elevation_error}
                           label={this.props.elevation_error} type="number" inputProps={{min: -1360, max: 8850}}
                           InputProps={{
                               endAdornment: <InputAdornment position="end">m</InputAdornment>,
                           }}/>
            </Grid>
        </Grid>
    }
}


@observer
class LocationSettings extends React.Component {
    constructor(props) {
        super(props);
        this.citySearchClicked = this.citySearchClicked.bind(this);
    }

    addClicked() {
        state.location.new_step = 1;
    }

    newLocationOptionChanged(event) {
        state.location.option = event.currentTarget.value;
    }

    cancelClicked() {
        state.location.new_step = null;
    }

    citySearchClicked(name, lat, lon, elevation) {
        state.location.name = name;
        this.onCoordinateChange(lat, lon, elevation);
        this.step1NextClicked(null, true);
    }

    onCoordinateChange(lat, lon, elevation) {
        state.location.coord_lat = lat;
        state.location.coord_long = lon;
        state.location.coord_elevation = elevation;
    }

    step2LocationNameChanged(e) {
        state.location.name = e.currentTarget.value;
    }

    step1NextClicked(e, dont_empty_name) {
        const lat = state.location.coord_lat;
        const long = state.location.coord_long;
        const elevation = state.location.coord_elevation;

        console.log('bob', state.location.coord_long);
        if (lat === null || isNaN(lat)) {
            state.location.coord_lat_error = 'required';
        } else if (lat < -90 || lat > 90) {
            state.location.coord_lat_error = 'Invalid Latitude';
        } else {
            state.location.coord_lat_error = null;
        }
        if (long === null || isNaN(long)) {
            state.location.coord_long_error = 'required';
        } else if (long < -180 || long > 180) {
            state.location.coord_long_error = 'Invalid Longituderequired';
        } else {
            state.location.coord_long_error = null;
        }
        if (elevation === null || isNaN(elevation)) {
            state.location.coord_elevation_error = 'required';
        } else if (elevation < -1360 || elevation > 8850) {
            state.location.coord_elevation_error = 'Invalid Elevation';
        } else {
            state.location.coord_elevation_error = null;
        }
        if (!state.location.coord_lat_error && !state.location.coord_long_error &&
            !state.location.coord_elevation_error) {
            if (!dont_empty_name) {
                state.location.name = null;
            }
            state.location.new_step = 2;
        }
    }

    saveClicked(e) {
        if (!state.location.name) {
            state.location.name_error = "Location Name required"
        } else {
            //TODO: Actually save new location
            state.location.new_step = null;
        }
    }

    handleDialogClose() {
        state.location.new_step = 0;
    }

    render() {
        let location_option = null;
        if (state.location.option === 'city_search') {
            location_option = <CitySearch autoFocus={true} onCityClick={this.citySearchClicked}/>;
        } else {
            location_option = <GeoCoordinateInput latitude={state.location.coord_lat}
                                                  longitude={state.location.coord_long}
                                                  elevation={state.location.coord_elevation}
                                                  latitude_error={state.location.coord_lat_error}
                                                  longitude_error={state.location.coord_long_error}
                                                  elevation_error={state.location.coord_elevation_error}
                                                  onChange={this.onCoordinateChange}/>;
        }
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
                <Grid item xs={12} style={{textAlign: "right"}}>
                    <Fab color="primary" aria-label="add" onClick={this.addClicked}>
                        <AddIcon/>
                    </Fab>
                </Grid>
            </Grid>

            <Dialog open={state.location.new_step === 1} maxWidth="xs" onClose={this.handleDialogClose}>
                <DialogTitle>New Location</DialogTitle>
                <DialogContent>
                    <RadioGroup aria-label="location option" name="location_option">
                        <Grid container>
                            <Grid item xs={2}/>
                            <Grid item xs={4}>
                                <FormControlLabel value="city_search"
                                                  control={<Radio
                                                      checked={state.location.option === 'city_search'}
                                                      onChange={this.newLocationOptionChanged}/>}
                                                  label="City Search"/>
                            </Grid>
                            <Grid item xs={4}>
                                <FormControlLabel value="coordinates"
                                                  control={<Radio
                                                      checked={state.location.option === 'coordinates'}
                                                      onChange={this.newLocationOptionChanged}/>}
                                                  label="Coordinates"/>
                            </Grid>
                            <Grid item xs={2}/>
                        </Grid>
                    </RadioGroup>
                    {location_option}
                </DialogContent>
                <DialogActions>
                    <Button color="primary" onClick={this.cancelClicked}>Cancel</Button>
                    {state.location.option !== 'city_search' &&
                    <Button color="primary" onClick={this.step1NextClicked}>Next</Button>}
                </DialogActions>
            </Dialog>

            <Dialog open={state.location.new_step === 2} maxWidth="xs" onClose={this.handleDialogClose}>
                <div style={{padding: "2ex"}}>
                    <DialogTitle>New Location Name</DialogTitle>
                    <DialogContent>Please enter a name for this new location.</DialogContent>
                    <TextField autoFocus margin="dense" error={!!state.location.name_error}
                               label={state.location.name_error} type="text" fullWidth
                               value={state.location.name || ''} placeholder="Your Location Name"
                               onChange={this.step2LocationNameChanged}/>
                    <DialogActions>
                        <Button color="primary" onClick={this.cancelClicked}>Cancel</Button>
                        <Button color="primary" onClick={this.saveClicked}>Save</Button>
                    </DialogActions>
                </div>
            </Dialog>
        </Typography>;
    }
}

export default LocationSettings;