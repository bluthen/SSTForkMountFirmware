import '@fontsource/roboto';
import React from "react";
import {render} from "react-dom";
import { ThemeProvider, StyledEngineProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Container from '@mui/material/Container';
import state from './State';
import {observer} from "mobx-react"
import Paper from '@mui/material/Paper';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
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
import {defaultTheme, darkTheme, redTheme} from './Themes';

const tabMap = ['manual', 'goto', 'setup'];

@observer
class App extends React.Component {
    tabChange(event, newValue) {
        state.page = tabMap[newValue];
        state.topTabs = tabMap[newValue];
    }

    render() {
        const tabIndex = tabMap.indexOf(state.topTabs);
        let theme = defaultTheme;
        if (state.color_scheme === 'dark') {
            theme = darkTheme;
        } else if (state.color_scheme === 'red') {
            theme = redTheme;
        }
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

        location.hash = state.page;


        let dialog = null;
        if(state.goto.slewing || state.status.slewing) {
            dialog = <SlewingDialog/>;
        } else if(state.goto.syncing) {
            dialog = <SyncingDialog/>;
        }

        return (
            <React.Fragment>
                <StyledEngineProvider injectFirst>
                    <ThemeProvider theme={theme}>
                        <CssBaseline/>
                        <Container>
                            <Paper square style={{paddingLeft: '3ex', paddingRight: '3ex', height: '100%'}}>
                                {tabs}
                                {content}
                                {dialog}
                            </Paper>
                            <InfoSnackbar/>
                        </Container>
                    </ThemeProvider>
                </StyledEngineProvider>
            </React.Fragment>
        );
    }
}

function handleHashChange() {
    const hash = location.hash.substring(1);
    if (state.page !== hash) {
        state.page = hash;
        if(state.page === 'goto' || state.page === 'manual') {
            state.topTabs = state.page;
        } else {
            state.topTabs='setup';
        }
    }
}

window.onhashchange = handleHashChange;

render(
    <App/>,
    document.getElementById("root")
);
APIHelp.setTime();
APIHelp.startStatusUpdateInterval();
APIHelp.startSettingsUpdateInterval();
APIHelp.startNetworkStateListeners();
APIHelp.fetchSettings();

