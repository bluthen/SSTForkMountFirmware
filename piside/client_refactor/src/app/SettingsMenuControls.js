import Slewing from './Slewing';
import DirectionControls from './DirectionControls';


class SettingsMenuControls {
    constructor(App, parentDiv) {
        this._selfDiv = $('<div></div>');
        this._selfDiv.hide();
        parentDiv.append(this._selfDiv);
        this.directionControls = new DirectionControls(App, this._selfDiv);
        this.slewing = new Slewing(App, this._selfDiv);
    }

    show() {
        this._selfDiv.show();
    }

    hide() {
        this._selfDiv.hide();
    }
}

export default SettingsMenuControls;
