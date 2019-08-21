import React from "react";
import PlayArrowIcon from '@material-ui/icons/PlayArrow';
import IconButton from '@material-ui/core/IconButton';
import Grid from '@material-ui/core/Grid';


const circle = {
    position: "relative",
    backgroundColor: "#bddfff",
    border: "3px solid #333",
    height: "300px",
    width: "300px",
    borderRadius: "50%"
};

const north = {
    fontSize: "150px",
    transform: "rotate(-90deg)"
};

const south = {
    fontSize: "150px",
    transform: "rotate(90deg)"
};

const east = {
    fontSize: "150px",
};

const west = {
    fontSize: "150px",
    transform: "rotate(180deg)"
};

const button = {
    padding: 0
};

class DirectionControls extends React.Component {
    render() {
        return <table style={circle}><tbody>
            <tr><td></td><td>
                <IconButton style={button}>
                    <PlayArrowIcon color="primary" style={north}/>
                </IconButton></td><td></td></tr>
            <tr><td>
                <IconButton style={button}>
                    <PlayArrowIcon color="primary" style={west}/>
                </IconButton></td><td></td><td>

                <IconButton style={button}>
                    <PlayArrowIcon color="primary" style={east}/>
                </IconButton>

            </td></tr>
            <tr><td></td><td>
                <IconButton style={button}>
                    <PlayArrowIcon color="primary" style={south}/>
                </IconButton></td><td></td></tr>
        </tbody></table>
    }
}

export default DirectionControls;