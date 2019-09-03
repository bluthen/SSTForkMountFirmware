import React from "react";
import state from './State';
import {observer} from "mobx-react"
import PositionInfo from "./PositionInfo";
import Radio from '@material-ui/core/Radio';
import RadioGroup from '@material-ui/core/RadioGroup';
import FormHelperText from '@material-ui/core/FormHelperText';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import FormControl from '@material-ui/core/FormControl';
import FormLabel from '@material-ui/core/FormLabel';
import Grid from '@material-ui/core/Grid';
import ObjectSearch from './ObjectSearch';
import CoordinatesInput from './CoordinatesInput';
import CircularProgress from '@material-ui/core/CircularProgress';


@observer
class ManualPage extends React.Component {

    gotoOptionChange(event, value) {
        state.goto.option = value;
    }

    typeChanged(event, checked) {
        if (checked) {
            state.goto.coordinates.type = 'altaz';
        } else {
            state.goto.coordinates.type = 'radec';
        }
    }

    render() {
        let option;

        if (state.goto.option === 'object_search') {
            option = <ObjectSearch/>;
        } else {
            option = <CoordinatesInput coordinateType={state.goto.coordinates.type} onTypeChange={this.typeChanged}/>;
        }

        return <React.Fragment>
            <PositionInfo/>
            <RadioGroup aria-label="goto option" name="goto_option" onChange={this.gotoOptionChange}>
                <Grid container>
                    <Grid item xs={2}/>
                    <Grid item xs={4}>
                        <FormControlLabel value="object_search" control={<Radio checked={state.goto.option === 'object_search'}/>} label="Object Search"/>
                    </Grid>
                    <Grid item xs={4}>
                        <FormControlLabel value="coordinates" control={<Radio checked={state.goto.option === 'coordinates'}/>} label="Coordinates"/>
                    </Grid>
                    <Grid item xs={2}/>
                </Grid>
            </RadioGroup>
            {option}
        </React.Fragment>
    }

}

export default ManualPage;