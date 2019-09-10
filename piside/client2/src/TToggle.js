import Typography from '@material-ui/core/Typography';
import Grid from '@material-ui/core/Grid';
import React from "react";
import Switch from '@material-ui/core/Switch';
import {withStyles} from '@material-ui/core/styles';


const AntSwitch = withStyles(theme => ({
    root: {
        width: 28,
        height: 16,
        padding: 0,
        display: 'flex',
    },
    switchBase: {
        padding: 2,
        color: theme.palette.secondary.main,
        '&$checked': {
            color: theme.palette.common.white,
            '& + $track': {
                opacity: 1,
                backgroundColor: theme.palette.primary.main,
                borderColor: theme.palette.primary.main,
            },
        },
    },
    thumb: {
        width: 12,
        height: 12,
        boxShadow: 'none',
    },
    track: {
        border: `1px solid ${theme.palette.secondary.main}`,
        borderRadius: 16 / 2,
        opacity: 1,
        backgroundColor: theme.palette.common.white,
    },
    checked: {},
}))(Switch);

class TToggle extends React.Component {
    render() {
        return <Typography component="div"><Grid component="label" container alignItems="center" spacing={1}>
            <Grid item>{this.props.offLabel}</Grid>
            <Grid item>
                <AntSwitch
                    checked={this.props.checked}
                    onChange={this.props.onChange}
                    value="CoordV"
                />
            </Grid>
            <Grid item>{this.props.onLabel}</Grid>
        </Grid></Typography>
    }
}


export default TToggle;