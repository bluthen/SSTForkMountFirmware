import React from "react";
import CircularProgress from '@material-ui/core/CircularProgress';
import {Line, LineChart, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer} from 'recharts';
import Formating from './util/Formatting';
import Grid from '@material-ui/core/Grid';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Checkbox from '@material-ui/core/Checkbox';


class EncoderGraph extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            step_ra: true,
            enc_ra: true,
            step_dec: true,
            enc_dec: true,
            ra_over_raenc: true,
            dec_over_decenc: true
        };
    }

    xTickFormatter(x) {
        const d = new Date(x * 1000);
        return Formating.dateHourMinuteSecondStr(d);
    }

    labelFormatter(x) {
        const d = new Date(x * 1000);
        return Formating.dateHourMinuteSecondMSStr(d);
    }

    makeToggleCallback(key) {
        return (e) => {
            const enabled = e.target.checked;
            const s = {};
            s[key] = enabled;
            this.setState(s)
        }
    }

    render() {
        let ret;
        if (!this.props.data) {
            ret = <></>;
        } else if (this.props.data === "fetching") {
            ret = <CircularProgress/>
        } else {
            const toggles = [];
            ['step_ra', 'enc_ra', 'step_dec', 'enc_dec', 'ra_over_raenc', 'dec_over_decenc'].forEach((key, idx) => {
                toggles.push(<Grid item key={key} xs={3}>
                    <FormControlLabel
                        control={
                            <Checkbox
                                value="toggle"
                                color="primary"
                                checked={this.state[key]}
                                onChange={this.makeToggleCallback(key)}
                            />
                        }
                        label={key}/>
                </Grid>);
            });

            ret = <>
            <ResponsiveContainer height={this.props.height} width={this.props.width}><LineChart
                data={this.props.data}>
                <XAxis dataKey="Time" tickFormatter={this.xTickFormatter}/>
                <YAxis yAxisId="left" label={{value: "Steppers", angle: -90, position: 'insideLeft'}}/>
                <YAxis yAxisId="right" orientation="right"
                       label={{value: "Encoders", angle: -90, position: 'insideLeft'}}/>
                <Tooltip labelFormatter={this.labelFormatter}/>
                <Legend/>
                {this.state.step_ra &&
                <Line yAxisId="left" dot={false} type="monotone" dataKey="step_ra" stroke="#ff0000"/>}
                {this.state.enc_ra &&
                <Line yAxisId="left" dot={false} type="monotone" dataKey="enc_ra" stroke="#ff7c7c"/>}
                {this.state.step_dec &&
                <Line yAxisId="left" dot={false} type="monotone" dataKey="step_dec" stroke="#0000ff"/>}
                {this.state.enc_dec &&
                <Line yAxisId="left" dot={false} type="monotone" dataKey="enc_dec" stroke="#4079ff"/>}

                {this.state.ra_over_raenc &&
                <Line yAxisId="right" dot={false} type="monotone" dataKey="ra_over_raenc" stroke="#ffab4a"/>}
                {this.state.dec_over_decenc &&
                <Line yAxisId="right" dot={false} type="monotone" dataKey="dec_over_decenc" stroke="#7aff3d"/>}

            </LineChart></ResponsiveContainer>
            <Grid container>
                {toggles}
            </Grid>;
            </>;
        }
        return ret;
    }
}

export default EncoderGraph;