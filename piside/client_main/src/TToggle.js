import Typography from '@mui/material/Typography';
import React from "react";
import Switch from '@mui/material/Switch';
import Stack from '@mui/material/Stack';
import {styled} from '@mui/material/styles';

// const AntSwitch = withStyles(theme => ({
//         root: {
//                 width: 28,
//                 height: 16,
//                 padding: 0,
//                 display: 'flex',
//             },
//         switchBase: {
//             padding: 2,
//                 color: theme.palette.secondary.main,
//                 '&$checked': {
//                     color: theme.palette.common.white,
//                         '& + $track': {
//                             opacity: 1,
//                                 backgroundColor: theme.palette.primary.main,
//                                 borderColor: theme.palette.primary.main,
//                             },
//                 },
//         },
//     thumb: {
//             width: 12,
//                 height: 12,
//                 boxShadow: 'none',
//             },
//     track: {
//             border: `1px solid ${theme.palette.secondary.main}`,
//                 borderRadius: 16 / 2,
//                 opacity: 1,
//                 backgroundColor: theme.palette.common.white,
//             },
//     checked: {},
// }))(Switch);


const AntSwitch = styled(Switch)(({theme}) => ({
    width: 28,
    height: 16,
    padding: 0,
    display: 'flex',
    '&:active': {
        '& .MuiSwitch-thumb': {
            width: 15,
        },
        '& .MuiSwitch-switchBase.Mui-checked': {
            transform: 'translateX(9px)',
        },
    },
    '& .MuiSwitch-switchBase': {
        padding: 2,
        '&.Mui-checked': {
            transform: 'translateX(12px)',
            color: '#fff',
            '& + .MuiSwitch-track': {
                opacity: 1,
                backgroundColor: theme.palette.mode === 'dark' ? '#177ddc' : '#1890ff',
            },
        },
    },
    '& .MuiSwitch-thumb': {
        boxShadow: '0 2px 4px 0 rgb(0 35 11 / 20%)',
        width: 12,
        height: 12,
        borderRadius: 6,
        transition: theme.transitions.create(['width'], {
            duration: 200,
        }),
    },
    '& .MuiSwitch-track': {
        borderRadius: 16 / 2,
        opacity: 1,
        backgroundColor:
            theme.palette.mode === 'dark' ? 'rgba(255,255,255,.35)' : 'rgba(0,0,0,.25)',
        boxSizing: 'border-box',
    },
}));


class TToggle extends React.Component {
    render() {
        // return <Typography component="div"><Grid component="label" container alignItems="center" spacing={1}>
        //     <Grid item>{this.props.offLabel}</Grid>
        //     <Grid item>
        //         <AntSwitch
        //             checked={this.props.checked}
        //             onChange={this.props.onChange}
        //             value="CoordV"
        //         />
        //     </Grid>
        //     <Grid item>{this.props.onLabel}</Grid>
        // </Grid></Typography>
        return <Stack direction="row" spacing={1} alignItems="center">
            <Typography>{this.props.offLabel}</Typography>
            <AntSwitch
                checked={this.props.checked}
                onChange={this.props.onChange}
                value="CoordV"
            />
            <Typography>{this.props.onLabel}</Typography>
        </Stack>;
    }
}


export default TToggle;