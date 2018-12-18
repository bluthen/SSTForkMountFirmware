/*global $ */
import SettingsMenuControls from './SettingsMenuControls.js'
import SettingsMenuGeneral from './SettingsMenuGeneral.js'
import SettingsMenuLocation from './SettingsMenuLocation.js'
import SettingsMenuNetwork from './SettingsMenuNetwork.js'
import SettingsMenuPolarAlignAssist from './SettingsMenuPolarAlignAssist';
import SettingsMenuHorizonLimit from './SettingsMenuHorizonLimit';

import template from './templates/SettingsMenu.html'

class SettingsMenu {
    constructor(App, parentDiv, startingSettings, directionsControls) {
        const _selfDiv = $(template);
        parentDiv.prepend(_selfDiv);
        const menuHeader = $('h2', _selfDiv);
        const settingsMenuDiv = $('<div></div>');
        parentDiv.append(settingsMenuDiv);

        this.settingsMenuControls = new SettingsMenuControls(App, settingsMenuDiv);
        this.settingsMenuControls.show();
        this.settingsMenuGeneral = new SettingsMenuGeneral(App, settingsMenuDiv);
        this.settingsMenuLocation = new SettingsMenuLocation(settingsMenuDiv, startingSettings);
        this.settingsMenuNetwork = new SettingsMenuNetwork(settingsMenuDiv);
        this.settingsMenuHorizonLimit = new SettingsMenuHorizonLimit(App, settingsMenuDiv);
        this.settingsMenuPolarAlignAssist = new SettingsMenuPolarAlignAssist(App, settingsMenuDiv, directionsControls);

        const hideAll = () => {
            $('#settings_menu_content li', _selfDiv).removeClass('active');
            this.settingsMenuControls.hide();
            this.settingsMenuGeneral.hide();
            this.settingsMenuLocation.hide();
            this.settingsMenuNetwork.hide();
            this.settingsMenuHorizonLimit.hide();
            this.settingsMenuPolarAlignAssist.hide();
        };

        // Controls
        $('#settings_menu_controls', _selfDiv).click(() => {
            hideAll();
            $('#settings_menu_controls', _selfDiv).parent().addClass('active');
            $('#settings_menu_content', _selfDiv).collapse('hide');
            menuHeader.text('Controls');
            this.settingsMenuControls.show();
        });

        // Settings menu
        $('#settings_menu_general', _selfDiv).click(() => {
            hideAll();
            $('#settings_menu_general', _selfDiv).parent().addClass('active');
            $('#settings_menu_content', _selfDiv).collapse('hide');
            menuHeader.text('General Settings');
            this.settingsMenuGeneral.show();
        });

        $('#settings_menu_location', _selfDiv).click(() => {
            hideAll();
            $('#settings_menu_location', _selfDiv).parent().addClass('active');
            $('#settings_menu_content', _selfDiv).collapse('hide');
            menuHeader.text('Location Settings');
            this.settingsMenuLocation.show();
        });

        $('#settings_menu_network', _selfDiv).click(() => {
            hideAll();
            $('#settings_menu_network', _selfDiv).parent().addClass('active');
            $('#settings_menu_content', _selfDiv).collapse('hide');
            menuHeader.text('Network Settings');
            this.settingsMenuNetwork.show();
        });

        $('#settings_menu_horizon', _selfDiv).click(() => {
            hideAll();
            $('#settings_menu_horizon', _selfDiv).parent().addClass('active');
            $('#settings_menu_content', _selfDiv).collapse('hide');
            menuHeader.text('Horizon Settings');
           this.settingsMenuHorizonLimit.show();
        });

        $('#settings_menu_polaralignassist', _selfDiv).click(() => {
            hideAll();
            $('#settings_menu_polaralignassist', _selfDiv).parent().addClass('active');
            $('#settings_menu_content', _selfDiv).collapse('hide');
            menuHeader.text('Polar Alignment Assist');
            this.settingsMenuPolarAlignAssist.show();
        });

    }
}

export default SettingsMenu;
