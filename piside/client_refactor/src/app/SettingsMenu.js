/*global $ */
import SettingsMenuGeneral from './SettingsMenuGeneral.js'
import SettingsMenuLocation from './SettingsMenuLocation.js'
import SettingsMenuNetwork from './SettingsMenuNetwork.js'
import SettingsMenuPolarAlignAssist from './SettingsMenuPolarAlignAssist';
import SettingsMenuHorizonLimit from './SettingsMenuHorizonLimit';

import template from './templates/SettingsMenu.html'

class SettingsMenu {
    constructor(App, parentDiv, startingSettings, directionsControls) {
        const _selfDiv = $(template);
        parentDiv.append(_selfDiv);
        const settingsMenuDiv = $('<div></div>');
        parentDiv.append(settingsMenuDiv);

        this.settingsMenuGeneral = new SettingsMenuGeneral(App, settingsMenuDiv);
        this.settingsMenuLocation = new SettingsMenuLocation(settingsMenuDiv, startingSettings);
        this.settingsMenuNetwork = new SettingsMenuNetwork(settingsMenuDiv);
        this.settingsMenuHorizonLimit = new SettingsMenuHorizonLimit(App, settingsMenuDiv);
        this.settingsMenuPolarAlignAssist = new SettingsMenuPolarAlignAssist(App, settingsMenuDiv, directionsControls);

        // Settings menu
        $('#settings_menu_general', _selfDiv).click(() => {
            this.settingsMenuGeneral.show();
        });

        $('#settings_menu_location', _selfDiv).click(() => {
            this.settingsMenuLocation.show();
        });

        $('#settings_menu_network', _selfDiv).click(() => {
            this.settingsMenuNetwork.show();
        });

        $('#settings_menu_horizon', _selfDiv).click(() => {
           this.settingsMenuHorizonLimit.show();
        });

        $('#settings_menu_polaralignassist', _selfDiv).click(() => {
            this.settingsMenuPolarAlignAssist.show();
        });


    }
}

export default SettingsMenu;