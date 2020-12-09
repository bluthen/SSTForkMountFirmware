import React from "react";
import CircularProgress from '@material-ui/core/CircularProgress';
import APIHelp from './util/APIHelp';
import {Line, LineChart, XAxis, YAxis,} from 'recharts';


class AltChart extends React.Component {
    constructor(props) {
        super(props);
        this.state = {data: null};
    }

    componentDidMount() {
        APIHelp.getAltitudeData(this.props.wanted).then((data) => {
            this.setState({data: data});
        })
    }

    render() {
        let ret;
        if (!this.state.data) {
            ret = <CircularProgress/>
        } else {
            ret = <LineChart width={this.props.width} height={this.props.height} data={this.state.data}>
                <XAxis dataKey="time"/>
                <YAxis label={{value: "Altitude", angle: -90, position: 'insideLeft'}} unit="°"/>
                <Line dot={false} type="monotone" dataKey="alt"/>
            </LineChart>;
        }
        return ret;
    }
}

export default AltChart;