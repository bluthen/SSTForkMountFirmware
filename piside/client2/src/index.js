import 'typeface-roboto';
import React from "react";
import {render} from "react-dom";
import CssBaseline from '@material-ui/core/CssBaseline';
import Container from '@material-ui/core/Container';
import state from './State';
import {observer} from "mobx-react"
import Paper from '@material-ui/core/Paper';
import Tabs from '@material-ui/core/Tabs';
import Tab from '@material-ui/core/Tab';
import ManualPage from './ManualPage';
import GotoPage from './GotoPage';
import SetupPage from './SetupPage';
import AdvancedSettings from './AdvancedSettings';
import LocationSettings from './LocationSettings';
import NetworkSettings from './NetworkSettings';
import SlewLimitsSettings from './SlewLimitsSettings';
import MiscellaneousSettings from './MiscellaneousSettings';
import APIHelp from './util/APIHelp';
import SlewingDialog from './SlewingDialog';
import SyncingDialog from './SyncingDialog';
import InfoSnackbar from './InfoSnackbar';

const tabMap = ['manual', 'goto', 'setup'];

@observer
class App extends React.Component {
    tabChange(event, newValue) {
        state.page = tabMap[newValue];
        state.topTabs = tabMap[newValue];
    }

    render() {
        const tabIndex = tabMap.indexOf(state.topTabs);
        let content = null;
        let tabs = <Container>
            <Tabs value={tabIndex} onChange={this.tabChange} aria-label="setup goto manual"
                  indicatorColor="primary" textColor="primary" centered>
                <Tab label="Manual"/>
                <Tab label="Goto"/>
                <Tab label="Setup"/>
            </Tabs>
        </Container>;

        if (state.page === 'manual') {
            content = <ManualPage/>;
        } else if (state.page === 'goto') {
            content = <GotoPage/>;
        } else if (state.page === 'advancedSettings') {
            console.log('advsetting')
            content = <AdvancedSettings/>;
        } else if(state.page === 'setup') { // Setup
            content = <SetupPage/>
        } else if(state.page === 'locationSettings') {
            content = <LocationSettings/>;
        } else if(state.page === 'networkSettings') {
            content = <NetworkSettings/>;
        } else if(state.page === 'slewLimitsSettings') {
            content = <SlewLimitsSettings/>;
        } else if(state.page === 'miscellaneousSettings') {
            content = <MiscellaneousSettings/>;
        } else {
            alert(state.page);
        }

        let dialog = null;
        if(state.goto.slewing || state.status.slewing) {
            dialog = <SlewingDialog/>;
        } else if(state.goto.syncing) {
            dialog = <SyncingDialog/>;
        }

        return <React.Fragment>
            <CssBaseline/>
            <Container>
                <Paper square style={{paddingLeft: '3ex', paddingRight: '3ex', height: '100%'}}>
                    {tabs}
                    {content}
                    {dialog}
                </Paper>
                <InfoSnackbar/>
            </Container>
        </React.Fragment>;
    }
}

render(
    <App/>,
    document.getElementById("root")
);
APIHelp.setTime();
APIHelp.startStatusUpdateInterval();
APIHelp.startNetworkStateListeners();
APIHelp.fetchSettings();