import React from "react";
import state from './State';
import {observer} from "mobx-react"
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import Grid from '@mui/material/Grid';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import InputAdornment from '@mui/material/InputAdornment';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import ListItemSecondaryAction from '@mui/material/ListItemSecondaryAction';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircle from '@mui/icons-material/CheckCircle';

import Fab from '@mui/material/Fab';
import AddIcon from '@mui/icons-material/Add';

import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import InputLabel from '@mui/material/InputLabel';
import CircularProgress from '@mui/material/CircularProgress';
import Formatting from './util/Formatting';
import APIHelp from './util/APIHelp';


import {v4 as uuidv4} from 'uuid';

const bold = {
    paddingTop: "3x",
    fontWeight: "bold"
};

@observer
class CitySearch extends React.Component {
    constructor(props) {
        super(props);
        this.uuid = uuidv4();
    }

    handleSearchChange(e) {
        state.location.city_search = e.currentTarget.value;
    }

    makeHandleCityClick(name, latitude, longitude, elevation) {
        return () => {
            this.props.onCityClick(name, latitude, longitude, elevation);
        }
    }

    render() {
        let table = null;
        if (state.location.city_searching) {
            table = <CircularProgress/>
        } else if (state.location.city_search_results.length === 0) {
            table = <Typography component="div">No results</Typography>;
        } else {
            let tableRows = [];
            for (let i = 0; i < state.location.city_search_results.length; i++) {
                const result = state.location.city_search_results[i];
                const coord = Formatting.degLat2Str(result.latitude) + '/' + Formatting.degLong2Str(result.longitude) + ' ' + result.elevation + 'm';
                tableRows.push(<TableRow key={this.uuid + '_' + i} hover style={{cursor: "pointer"}}
                                         onClick={this.makeHandleCityClick(result.city + ', ' + result.state_abbr, result.latitude, result.longitude, result.elevation)}>
                    <TableCell>{result.city}, {result.state_abbr} {result.postalcode}</TableCell>
                    <TableCell>{coord}</TableCell>
                </TableRow>);
            }
            table = <Table>
                <TableHead>
                    <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell>Coords</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {tableRows}
                </TableBody>
            </Table>;
        }

        return <><TextField fullWidth autoFocus={this.props.autoFocus} placeholder="City Name or Zipcode"
                            onChange={this.handleSearchChange} value={state.location.city_search}/>
        {table}
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

    saveClicked() {
        if (!state.location.name) {
            state.location.name_error = "Location Name required"
        } else {
            APIHelp.addLocationPreset(state.location.name, state.location.coord_lat, state.location.coord_long, state.location.coord_elevation).then(() => {
                return APIHelp.fetchSettings();
            });
            state.location.new_step = null;
        }
    }

    useGPSClicked() {
        APIHelp.useGPSLocation().then(() => {
           return APIHelp.fetchSettings();
        });
    }

    handleDialogClose() {
        state.location.new_step = 0;
    }

    componentDidMount() {
        APIHelp.fetchSettings();
    }

    genHandleDeletePreset(index) {
        return () => {
            APIHelp.delLocationPreset(index).then(() => {
                return APIHelp.fetchSettings();
            })
        }
    }

    genHandleSetLocation(name, lat, long, elevation) {
        return () => {
            APIHelp.setLocation(name, lat, long, elevation).then(() => {
                return APIHelp.fetchSettings();
            })
        }
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
        const presets = [];
        for (let i = 0; i < state.location_presets.length; i++) {
            const preset = state.location_presets[i];
            let icon = null;
            if (state.location_set.name === preset.name && state.location_set.lat === preset.lat && state.location_set.long === preset.long && state.location_set.elevation === preset.elevation) {
                icon = <ListItemIcon><CheckCircle/></ListItemIcon>;
            }
            presets.push(
                <ListItem key={'location_list' + i} button
                          onClick={this.genHandleSetLocation(preset.name, preset.lat, preset.long, preset.elevation)}>
                    {icon}
                    <ListItemText primary={preset.name} secondary={
                        Formatting.degLat2Str(preset.lat) + '/' + Formatting.degLong2Str(preset.long) + ' ' + preset.elevation + 'm'
                    }/>
                    <ListItemSecondaryAction>
                        <IconButton
                            edge="end"
                            aria-label="delete"
                            onClick={this.genHandleDeletePreset(i)}
                            size="large">
                            <DeleteIcon/>
                        </IconButton>
                    </ListItemSecondaryAction>
                </ListItem>
            )
        }
        return <Typography component="div">
            <Typography component="h4" style={bold}>
                Preset Locations
            </Typography>
            <Grid container spacing={2}>
                <Grid item xs={12}>
                    <List component="nav">
                        {presets}
                    </List>
                </Grid>
                <Grid item xs={12} style={{textAlign: "right"}}>
                    <Fab color="primary" aria-label="add" onClick={this.addClicked}>
                        <AddIcon/>
                    </Fab>
                </Grid>
                <Grid item xs={12}>
                    {state.status.handpad &&
                    <Button color="primary" variant="contained" aria-label="Use GPS" onClick={this.useGPSClicked}>Use GPS</Button>
                    }
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