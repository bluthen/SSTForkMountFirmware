
import template from './templates/SettingsMenuPolarAlignAssist.html'


class SettingsMenuPolarAlignAssist {
    constructor(parentDiv) {
        this._selfDiv = $(template);
        parentDiv.append(this._selfDiv);
        //TODO: Get rotation coordinates from config
        $.ajax({
            url: '/settings',
            dataType: 'json',
            success: (data) => {
                this._cameraRotationXY = data.polar_align_camera_rotation;
                $('#settings_polar_align_assist_config_rotation_x').val(this._cameraRotationXY[0]);
                $('#settings_polar_align_assist_config_rotation_y').val(this._cameraRotationXY[1]);
            },
            error: function (jq, errorstatus, errortxt) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });

        this._cameraRotationXY = [1812, 1456];
        this._$canvas = $('canvas', this._selfDiv);
        $('input[type="number"]', this._selfDiv).inputSpinner();
        this._testCameraImage = new createjs.Bitmap("1533416531.jpg");
        this._overlayImage = new createjs.Bitmap("1533416531_work.png");
        this._overlayImageReg = [1812, 1456];
        this._stage = new createjs.Stage(this._$canvas[0]);
        this._stage.update();
        $('#settings_polar_align_assist_capture', this._selfDiv).click(()=> {
           this.capture();
        });
        $('#settings_polar_align_assist_zoom, #settings_polar_align_assist_rotation, #settings_polar_align_assist_overlay_opacity', this._selfDiv).change(() => {
            this._update();
        });
        $('#settings_polar_align_assist_save', this._selfDiv).click(() => {
            const x = parseInt($('#settings_polar_align_assist_config_rotation_x').val(), 10);
            const y = parseInt($('#settings_polar_align_assist_config_rotation_y').val(), 10);
            this._cameraRotationXY=[x, y];
            const settings = {polar_align_camera_rotation: this._cameraRotationXY};
            $.ajax({
                url: '/settings',
                method: 'PUT',
                data: {'settings': JSON.stringify(settings)},
                success: () => {
                    $('#settings_polar_align_assist_save_status', this._selfDiv).text('Saved').show().fadeOut(1000);
                },
                error: function (jq, errorstatus, errortxt) {
                    $('#errorInfoModalTitle').text('Error');
                    $('#errorInfoModalBody').text(jq.responseText);
                    $('#errorInfoModal').modal();
                    return;
                }
            });
            this._update();
        });
        window._testStage = this._stage;
        this._selfDiv.on('shown.bs.modal', () => {
            this._$canvas[0].width = this._$canvas.parent().width();
            this._$canvas[0].height = this._$canvas.parent().width();
        });
    }

    capture() {
        this._update();
    }

    _update() {
        this._stage.clear();
        this._canvasSize = [this._$canvas.width(), this._$canvas.height()];
        const transform = {
            scale: parseFloat($('#settings_polar_align_assist_zoom', this._selfDiv).val())/100.0,
            rotation: parseFloat($('#settings_polar_align_assist_rotation', this._selfDiv).val())
        };
        this._testCameraImage.setTransform(0, 0, transform.scale, transform.scale, 0, 0, 0, this._cameraRotationXY[0], this._cameraRotationXY[1]);
        this._testCameraImage.x = this._canvasSize[0]/2;
        this._testCameraImage.y = this._canvasSize[1]/2;
        this._overlayImage.setTransform(0, 0, transform.scale, transform.scale, transform.rotation, 0, 0, this._overlayImageReg[0], this._overlayImageReg[1]);
        this._overlayImage.x = this._canvasSize[0]/2.0;
        this._overlayImage.y = this._canvasSize[1]/2.0;
        this._overlayImage.alpha = parseFloat($('#settings_polar_align_assist_overlay_opacity').val())/100.0;
        this._stage.addChild(this._testCameraImage);
        this._stage.addChild(this._overlayImage);
        this._stage.update();
    }

    show() {
        this._selfDiv.data('bs.modal', null).modal({backdrop: true, keyboard: true});
    }
}

export default SettingsMenuPolarAlignAssist;
