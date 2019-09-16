import React from 'react';
import state from './State';
import Snackbar from '@material-ui/core/Snackbar';
import IconButton from '@material-ui/core/IconButton';
import CloseIcon from '@material-ui/icons/Close';
import {observer} from "mobx-react"

@observer
class InfoSnackbar extends React.Component{

    handleClose(event, reason) {
        if (reason === 'clickaway') {
            return;
        }
        state.snack_bar = null;
        state.snack_bar_error = false;
    }

    render() {
        let style = null;
        if (state.snack_bar_error) {
            style = {color: 'red'};
        }

        return <Snackbar
            anchorOrigin={{
                vertical: 'bottom',
                horizontal: 'left',
            }}
            open={!!state.snack_bar}
            autoHideDuration={4000}
            onClose={this.handleClose}
            ContentProps={{
                'aria-describedby': 'infosnackbar-id',
            }}
            message={<span id="infosnackbar-id" style={style}>{state.snack_bar}</span>}
            action={[
                <IconButton
                    key="close"
                    aria-label="close"
                    color="inherit"
                    onClick={this.handleClose}
                >
                    <CloseIcon/>
                </IconButton>,
            ]}
        />
    }
}

export default InfoSnackbar;