/*globals $ */
import SettingsMenu from './SettingsMenu'

const initStep2 = function() {
    this.settingsMenu = new SettingsMenu(this, $('.App'));

    const isMobile = function () {
        if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
            return true;
        }
        return false;
    };

    $('input').focus(function () {
        if (isMobile()) {
            $('nav#status_footer').hide();
        }
    }).blur(function () {
        if (isMobile()) {
            $('nav#status_footer').show();
        }
    });
};

const App = {
    init: function() {
        delete this.init;
        (initStep2.bind(this))();
    }
};

$(document).ready(function () {
    App.init();
});

export default App;
