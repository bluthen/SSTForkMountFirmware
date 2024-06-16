import React from 'react';
import Grid from '@mui/material/Grid';
import List from '@mui/material/List';
import Card from '@mui/material/Card';
import CardHeader from '@mui/material/CardHeader';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import ListItemIcon from '@mui/material/ListItemIcon';
import Checkbox from '@mui/material/Checkbox';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';

function not(a, b) {
    return a.filter(value => b.indexOf(value) === -1);
}

function intersection(a, b) {
    return a.filter(value => b.indexOf(value) !== -1);
}

function union(a, b) {
    return [...a, ...not(b, a)];
}

export default function TriTransferList(props) {
    const [checked, setChecked] = React.useState([]);
    let left = props.leftList;
    let right = props.rightList;
    let center = props.centerList;

    let leftChecked = intersection(checked, left);
    let centerChecked = intersection(checked, center);
    let rightChecked = intersection(checked, right);

    const handleToggle = value => () => {
        const currentIndex = checked.indexOf(value);
        const newChecked = [...checked];

        if (currentIndex === -1) {
            newChecked.push(value);
        } else {
            newChecked.splice(currentIndex, 1);
        }

        setChecked(newChecked);
    };

    const numberOfChecked = items => intersection(checked, items).length;

    const handleToggleAll = items => () => {
        if (numberOfChecked(items) === items.length) {
            setChecked(not(checked, items));
        } else {
            setChecked(union(checked, items));
        }
    };

    const handleACheckedRight = () => {
        console.log('aright');
        center = center.concat(leftChecked);
        left = not(left, leftChecked);
        setChecked(not(checked, leftChecked));
        props.onLeftListChanged(left);
        props.onCenterListChanged(center);
    };

    const handleACheckedLeft = () => {
        left = left.concat(centerChecked);
        center = not(center, centerChecked);
        setChecked(not(checked, centerChecked));
        props.onLeftListChanged(left);
        props.onCenterListChanged(center);
    };

    const handleBCheckedRight = () => {
        right = right.concat(centerChecked);
        center = not(center, centerChecked);
        setChecked(not(checked, centerChecked));
        props.onRightListChanged(right);
        props.onCenterListChanged(center);
    };

    const handleBCheckedLeft = () => {
        center = center.concat(rightChecked);
        right = not(right, rightChecked);
        setChecked(not(checked, rightChecked));
        props.onRightListChanged(right);
        props.onCenterListChanged(center);
    };

    const customList = (title, items) => (
        <Card>
            <CardHeader
                sx={{px: 1, py: 2}}
                avatar={
                    <Checkbox
                        onClick={handleToggleAll(items)}
                        checked={numberOfChecked(items) === items.length && items.length !== 0}
                        indeterminate={numberOfChecked(items) !== items.length && numberOfChecked(items) !== 0}
                        disabled={items.length === 0}
                        inputProps={{'aria-label': 'all items selected'}}
                    />
                }
                title={title}
                subheader={`${numberOfChecked(items)}/${items.length} selected`}
            />
            <Divider/>
            <List sx={{
                width: 200,
                height: 230,
                overflow: 'auto',
                backgroundColor: 'background.paper'
            }} dense component="div" role="list">
                {items.map(value => {
                    const labelId = `transfer-list-all-item-${value}-label`;

                    return (
                        <ListItem key={value} role="listitem" button onClick={handleToggle(value)}>
                            <ListItemIcon>
                                <Checkbox
                                    checked={checked.indexOf(value) !== -1}
                                    tabIndex={-1}
                                    disableRipple
                                    inputProps={{'aria-labelledby': labelId}}
                                />
                            </ListItemIcon>
                            <ListItemText id={labelId} primary={`${value}`}/>
                        </ListItem>
                    );
                })}
                <ListItem/>
            </List>
        </Card>
    );

    return (
        <Grid container spacing={2} justifyContent="center" alignItems="center">
            <Grid item>{customList(props.leftLabel, left)}</Grid>
            <Grid item>
                <Grid container direction="column" alignItems="center">
                    <Button
                        sx={{mx: 0.5, my: 0}}
                        variant="outlined"
                        size="small"
                        onClick={handleACheckedRight}
                        disabled={leftChecked.length === 0}
                        aria-label="move selected right"
                    >
                        &gt;
                    </Button>
                    <Button
                        sx={{mx: 0.5, my: 0}}
                        variant="outlined"
                        size="small"
                        onClick={handleACheckedLeft}
                        disabled={centerChecked.length === 0}
                        aria-label="move selected left"
                    >
                        &lt;
                    </Button>
                </Grid>
            </Grid>
            <Grid item>{customList(props.centerLabel, center)}</Grid>
            <Grid item>
                <Grid container direction="column" alignItems="center">
                    <Button
                        sx={{mx: 0.5, my: 0}}
                        variant="outlined"
                        size="small"
                        onClick={handleBCheckedRight}
                        disabled={centerChecked.length === 0}
                        aria-label="move selected right"
                    >
                        &gt;
                    </Button>
                    <Button
                        sx={{mx: 0.5, my: 0}}
                        variant="outlined"
                        size="small"
                        onClick={handleBCheckedLeft}
                        disabled={rightChecked.length === 0}
                        aria-label="move selected left"
                    >
                        &lt;
                    </Button>
                </Grid>
            </Grid>
            <Grid item>{customList(props.rightLabel, right)}</Grid>
        </Grid>
    );
}