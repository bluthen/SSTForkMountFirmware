/*global $ */
import SettingsMenuGeneral from './SettingsMenuGeneral.js'
import SettingsMenuLocation from './SettingsMenuLocation.js'
import SettingsMenuNetwork from './SettingsMenuNetwork.js'

import template from './templates/SettingsMenu.html'

class SettingsMenu {
    constructor(App, parentDiv, startingSettings) {
        const _selfDiv = $(template);
        parentDiv.append(_selfDiv);
        const settingsMenuDiv = $('<div></div>');
        parentDiv.append(settingsMenuDiv);

        this.settingsMenuGeneral = new SettingsMenuGeneral(App, settingsMenuDiv);
        this.settingsMenuLocation = new SettingsMenuLocation(settingsMenuDiv, startingSettings);
        this.settingsMenuNetwork = new SettingsMenuNetwork(settingsMenuDiv);

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



    }
}

export default SettingsMenu;