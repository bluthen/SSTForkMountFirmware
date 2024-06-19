import React from "react";
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import IconButton from '@mui/material/IconButton';
import PropTypes from "prop-types";


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
    constructor(props) {
        super(props);
        this.cbHandleMouseUp = this.cbHandleMouseUp.bind(this);
        this.cbHandleMouseDown = this.cbHandleMouseDown.bind(this);
        this.state = {north: false, south: false, east: false, west: false};
    }

    handleMouseDown(direction) {
        const r = {};
        r[direction] = true;
        this.setState(r);
        const dirs = {
            north: this.state.north,
            south: this.state.south,
            east: this.state.east,
            west: this.state.west
        };
        dirs[direction] = true;
        this.props.onDirectionChange(dirs);
        console.log('down', direction)
    }

    handleMouseUp(direction) {
        const r = {};
        const wasDown = this.state[direction];
        r[direction] = false;
        this.setState(r);
        if (wasDown) {
            const dirs = {
                north: this.state.north,
                south: this.state.south,
                east: this.state.east,
                west: this.state.west
            };
            dirs[direction] = false;
            this.props.onDirectionChange(dirs);
        }
    }

    cbHandleMouseDown(direction) {
        return () => {
            this.handleMouseDown(direction);
        }
    }

    cbHandleMouseUp(direction) {
        return () => {
            this.handleMouseUp(direction);
        }
    }

    render() {
        return (
            <table style={circle}>
                <tbody>
                <tr>
                    <td/>
                    <td>
                        <IconButton
                            style={button}
                            onMouseDown={this.cbHandleMouseDown('north')}
                            onTouchStart={this.cbHandleMouseDown('north')}
                            onMouseLeave={this.cbHandleMouseUp('north')}
                            onMouseUp={this.cbHandleMouseUp('north')}
                            onTouchEnd={this.cbHandleMouseUp('north')}
                            onTouchCancel={this.cbHandleMouseUp('north')}
                            size="large">
                            <PlayArrowIcon color="primary" style={north}/>
                        </IconButton></td>
                    <td/>
                </tr>
                <tr>
                    <td>
                        <IconButton
                            style={button}
                            onMouseDown={this.cbHandleMouseDown('west')}
                            onTouchStart={this.cbHandleMouseDown('west')}
                            onMouseLeave={this.cbHandleMouseUp('west')}
                            onMouseUp={this.cbHandleMouseUp('west')}
                            onTouchEnd={this.cbHandleMouseUp('west')}
                            onTouchCancel={this.cbHandleMouseUp('west')}
                            size="large">
                            <PlayArrowIcon color="primary" style={west}/>
                        </IconButton></td>
                    <td/>
                    <td>

                        <IconButton
                            style={button}
                            onMouseDown={this.cbHandleMouseDown('east')}
                            onTouchStart={this.cbHandleMouseDown('east')}
                            onMouseLeave={this.cbHandleMouseUp('east')}
                            onMouseUp={this.cbHandleMouseUp('east')}
                            onTouchEnd={this.cbHandleMouseUp('east')}
                            onTouchCancel={this.cbHandleMouseUp('east')}
                            size="large">
                            <PlayArrowIcon color="primary" style={east}/>
                        </IconButton>

                    </td>
                </tr>
                <tr>
                    <td/>
                    <td>
                        <IconButton
                            style={button}
                            onMouseDown={this.cbHandleMouseDown('south')}
                            onTouchStart={this.cbHandleMouseDown('south')}
                            onMouseLeave={this.cbHandleMouseUp('south')}
                            onMouseUp={this.cbHandleMouseUp('south')}
                            onTouchEnd={this.cbHandleMouseUp('south')}
                            onTouchCancel={this.cbHandleMouseUp('south')}
                            size="large">
                            <PlayArrowIcon color="primary" style={south}/>
                        </IconButton></td>
                    <td/>
                </tr>
                </tbody>
            </table>
        );
    }
}

DirectionControls.propTypes = {
  onDirectionChange: PropTypes.func
};

export default DirectionControls;