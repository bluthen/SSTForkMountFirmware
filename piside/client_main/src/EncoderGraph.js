import React from "react";
import {observer} from "mobx-react"
import CircularProgress from '@material-ui/core/CircularProgress';
import {Line, LineChart, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer} from 'recharts';
import Formating from './util/Formatting';
import Grid from '@material-ui/core/Grid';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Checkbox from '@material-ui/core/Checkbox';
import TriTransferList from './TriTransferList';
import state from './State';
import _ from 'lodash';

const sides = {'left': ['step_ra', 'enc_ra', 'step_dec', 'enc_dec'], 'right': ['ra_over_raenc', 'dec_over_decenc']};


const lineStrokes = {
    step_ra: "#ff0000",
    enc_ra: "#ff7c7c",
    step_dec: "#0000ff",
    enc_dec: "#4079ff",
    ra_over_raenc: "#ffab4a",
    dec_over_decenc: "#7aff3d"
};

@observer
class EncoderGraph extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            step_ra: true,
            enc_ra: false,
            step_dec: false,
            enc_dec: false,
            ra_over_raenc: true,
            dec_over_decenc: false
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

    findMin(side) {
        return () => {
            const keys = state.encoderGraph[side];
            if (keys.length === 0) {
                return 0;
            }
            let a = _.minBy(this.props.data, (o) => {
                return _.min(_.map(_.values(_.pick(o, keys)), x => parseFloat(x)));
            });
            a = _.min(_.map(_.values(_.pick(a, keys)), x => parseFloat(x)));
            return a;
        }
    }

    findMax(side) {
        return () => {
            const keys = state.encoderGraph[side];
            if (keys.length === 0) {
                return 0;
            }
            const a = _.maxBy(this.props.data, (o) => {
                return _.max(_.map(_.values(_.pick(o, keys)), x => parseFloat(x)));
            });
            return _.max(_.map(_.values(_.pick(a, keys)), x => parseFloat(x)));
        }
    }

    getTicks(side) {
        const amin = this.findMin(side)();
        const amax = this.findMax(side)();
        let range = (amax - amin);
        let step = range / 4.0;
        if (step > 10) {
            step = ~~(step + 0.5);
        }
        const ret = [amin, amin + step, amin + 2 * step, amin + 3 * step, amin + 4 * step];
        return ret;
    }

    handleLeftListChanged(items) {
        console.log('leftlistchanged', items);
        state.encoderGraph.left.replace(items)
    }

    handleRightListChanged(items) {
        state.encoderGraph.right.replace(items)
    }

    handleCenterListChanged(items) {
        state.encoderGraph.hide.replace(items)
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

            const leftLines = [], rightLines = [];
            state.encoderGraph.left.forEach((key) => {
                leftLines.push(<Line key={'key_' + key} yAxisId="left" dot={false} type="monotone" dataKey={key}
                                     stroke={lineStrokes[key]}/>);
            });

            state.encoderGraph.right.forEach((key) => {
                leftLines.push(<Line key={'key_' + key} yAxisId="right" dot={false} type="monotone" dataKey={key}
                                     stroke={lineStrokes[key]}/>);
            });


            ret = <>
            <ResponsiveContainer height={this.props.height} width={this.props.width}>
                <LineChart data={this.props.data}>
                    <XAxis dataKey="Time" tickFormatter={this.xTickFormatter}/>
                    <YAxis yAxisId="left" label={{value: "Steppers", angle: -90, position: 'insideLeft'}}
                           domain={[this.findMin('left'), this.findMax('left')]}/>
                    <YAxis yAxisId="right" orientation="right"
                           label={{value: "Encoders", angle: -90, position: 'insideLeft'}}
                           domain={[this.findMin('right'), this.findMax('right')]}/>
                    <Tooltip labelFormatter={this.labelFormatter}/>
                    <Legend/>
                    {leftLines}
                    {rightLines}
                </LineChart>
            </ResponsiveContainer>
            <TriTransferList leftLabel='Left Y-Axis' leftList={state.encoderGraph.left} centerLabel='Not Shown'
                             centerList={state.encoderGraph.hide} rightLabel='Right Y-Axis'
                             rightList={state.encoderGraph.right} onLeftListChanged={this.handleLeftListChanged}
                             onRightListChanged={this.handleRightListChanged}
                             onCenterListChanged={this.handleCenterListChanged}/>
            </>;
        }
        return ret;
    }
}

export default EncoderGraph;