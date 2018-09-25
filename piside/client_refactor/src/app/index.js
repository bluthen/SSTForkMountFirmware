/*globals $ */
import Formating from './Formating'
import DirectionControls from './DirectionControls'
import SettingsMenu from './SettingsMenu'
import Slewing from './Slewing'
import Footer from './Footer'

const initStep2 = function(startingSettings) {
    this.footer = new Footer(this, $('body'), startingSettings);
    this.directionControls = new DirectionControls(this, $('.App'));
    this.slewing = new Slewing(this, $('.App'));
    this.settingsMenu = new SettingsMenu(this, $('.App'), startingSettings, this.directionControls);

    this.socket.on('controls_response', function (msg) {
        console.log(msg);
    });

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
        console.log(Formating.absoluteURL('/'));
        this.socket = io(Formating.absoluteURL('/'));
        this.socket.on('connect', function (msg) {
            console.log('socket io connect.');
        });

        $.ajax({
            url: '/settings',
            dataType: 'json',
            success: initStep2.bind(this)
        });
    }
};

$(document).ready(function () {
    App.init();
});

export default App;
