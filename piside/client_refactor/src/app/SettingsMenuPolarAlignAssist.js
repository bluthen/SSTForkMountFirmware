
import template from './templates/SettingsMenuPolarAlignAssist.html'


class SettingsMenuPolarAlignAssist {
    constructor(parentDiv) {
        this._selfDiv = $(template);
        parentDiv.append(this._selfDiv);
        this._canvas = $('canvas', this._selfDiv);
        $('input[type="number"]', this._selfDiv).inputSpinner();
    }

    show() {
        this._selfDiv.data('bs.modal', null).modal({backdrop: true, keyboard: true});
    }
}

export default SettingsMenuPolarAlignAssist;
