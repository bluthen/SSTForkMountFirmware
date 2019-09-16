/*global $ */
import SettingsMenuHorizonLimit from './SettingsMenuHorizonLimit';

import template from './templates/SettingsMenu.html'

class SettingsMenu {
    constructor(App, parentDiv) {
        const _selfDiv = $(template);
        parentDiv.prepend(_selfDiv);
        const menuHeader = $('h2', _selfDiv);
        const settingsMenuDiv = $('<div></div>');
        parentDiv.append(settingsMenuDiv);

        this.settingsMenuHorizonLimit = new SettingsMenuHorizonLimit(App, settingsMenuDiv);

        const horizon = () => {
            menuHeader.text('Horizon Settings');
            this.settingsMenuHorizonLimit.show();
        };

        horizon();
    }
}

export default SettingsMenu;
