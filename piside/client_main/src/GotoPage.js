import React from "react";
import state from './State';
import {observer} from "mobx-react"
import PositionInfo from "./PositionInfo";
import Radio from '@material-ui/core/Radio';
import RadioGroup from '@material-ui/core/RadioGroup';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Grid from '@material-ui/core/Grid';
import ObjectSearch from './ObjectSearch';
import CoordinatesInput from './CoordinatesInput';
import DebugStepsInput from './DebugStepsInput';


@observer
class ManualPage extends React.Component {

    gotoOptionChange(event, value) {
        state.goto.option = value;
    }

    handleTypeChange(e) {
        state.goto.coordinates.frame = e.target.value;
    }

    render() {
        let option;

        if (state.goto.option === 'object_search') {
            option = <ObjectSearch/>;
        } else if (state.goto.option === 'coordinates') {
            option =
                <CoordinatesInput coordinateType={state.goto.coordinates.frame} onTypeChange={this.handleTypeChange}/>;
        } else {
            option = <DebugStepsInput/>
        }
        let radioSize = 4;
        let stepsGotoRadio = null;
        if (state.misc.debug_options) {
            stepsGotoRadio = <Grid item xs={radioSize}>
                <FormControlLabel value="steps" control={<Radio checked={state.goto.option === 'steps'}/>}
                                  label="Steps"/>
            </Grid>;
        }


        return <React.Fragment>
            <PositionInfo/>
            <RadioGroup aria-label="goto option" name="goto_option" onChange={this.gotoOptionChange}>
                <Grid container>
                    {!state.misc.debug_options ? <Grid item xs={2}/> : null}
                    <Grid item xs={radioSize}>
                        <FormControlLabel value="object_search"
                                          control={<Radio checked={state.goto.option === 'object_search'}/>}
                                          label="Object Search"/>
                    </Grid>
                    <Grid item xs={radioSize}>
                        <FormControlLabel value="coordinates"
                                          control={<Radio checked={state.goto.option === 'coordinates'}/>}
                                          label="Coordinates"/>
                    </Grid>
                    {stepsGotoRadio}
                    {!state.misc.debug_options ? <Grid item xs={2}/> : null}
                </Grid>
            </RadioGroup>
            {option}
        </React.Fragment>
    }

}

export default ManualPage;