
import template from './templates/SettingsMenuPolarAlignAssist.html'


class SettingsMenuPolarAlignAssist {
    constructor(App, parentDiv, directionControls) {
        this._selfDiv = $(template);
        parentDiv.append(this._selfDiv);
        //TODO: Get rotation coordinates from config
        $.ajax({
            url: '/settings',
            dataType: 'json',
            success: (data) => {
                this._cameraRotationXY = [data.polar_align_camera_rotation_x, data.polar_align_camera_rotation_y];
                $('#settings_polar_align_assist_config_rotation_x').val(this._cameraRotationXY[0]);
                $('#settings_polar_align_assist_config_rotation_y').val(this._cameraRotationXY[1]);
            },
            error: function (jq, errorstatus, errortxt) {
                $('#errorInfoModalTitle').text('Error');
                $('#errorInfoModalBody').text(jq.responseText);
                $('#errorInfoModal').modal();
            }
        });

        this._cameraRotationXY = [906, 728];
        this._$canvas = $('canvas', this._selfDiv);
        $('input[type="number"]', this._selfDiv).inputSpinner();
        this._capture = false;
        this._continuous = false;
        this._rotate = false;
        this._cameraImage = new createjs.Bitmap("1533416531.jpg");
        this._overlayImage = new createjs.Bitmap("1533416531_work.png");
        this._overlayImageReg = [906, 728];
        this._stage = new createjs.Stage(this._$canvas[0]);
        this._stage.update();
        $('#settings_polar_align_assist_exposure_time', this._selfDiv).change(_.debounce(()=>{
            const exposure = parseInt(1000000*parseFloat($('#settings_polar_align_assist_exposure_time', this._selfDiv).val()));
            const iso = parseInt($('#settings_polar_align_assist_iso', this._selfDiv).val());
            if(this._continuous && this._capture) {
                this._PAACapture(exposure, iso, !this._continuous);
            }
        }, 500));
        $('#settings_polar_align_assist_iso', this._selfDiv).change(_.debounce(()=>{
            const exposure = parseInt(1000000*parseFloat($('#settings_polar_align_assist_exposure_time', this._selfDiv).val()));
            const iso = parseInt($('#settings_polar_align_assist_iso', this._selfDiv).val());
            if(this._continuous && this._capture) {
                this._PAACapture(exposure, iso, !this._continuous);
            }
        }, 500));
        $('#settings_polar_align_assist_capture', this._selfDiv).click(()=> {
            if(this._capture) {
                this._capture = false;
                $.ajax({
                    url: '/paa_capture',
                    method: 'DELETE'
                });
                $('#settings_polar_align_assist_capture', this._selfDiv).text(' Capture');
            } else {
                this._capture = true;
                const exposure = parseInt(1000000*parseFloat($('#settings_polar_align_assist_exposure_time', this._selfDiv).val()));
                const iso = parseInt($('#settings_polar_align_assist_iso', this._selfDiv).val());
                this._continuous = $('#settings-polar-align-assist-continuous', this._selfDiv).is(':checked');
                if(this._continuous) {
                    $('#settings_polar_align_assist_capture', this._selfDiv).text(' Stop Capturing');
                } else {
                    $('#settings_polar_align_assist_capture', this._selfDiv).text(' Capturing...');
                }
                this._PAACapture(exposure, iso, !this._continuous);
            }
        });
        $('#settings_polar_align_assist_zoom, #settings_polar_align_assist_rotation, #settings_polar_align_assist_overlay_opacity', this._selfDiv).change(() => {
            this._update();
        });
        $('#settings_polar_align_assist_save', this._selfDiv).click(() => {
            const x = parseInt($('#settings_polar_align_assist_config_rotation_x').val(), 10);
            const y = parseInt($('#settings_polar_align_assist_config_rotation_y').val(), 10);
            this._cameraRotationXY=[x, y];
            const settings = {polar_align_camera_rotation_x: this._cameraRotationXY[0], polar_align_camera_rotation_y: this._cameraRotationXY[1]};
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
        $('#settings_polar_align_assist_expose_and_rotate', this._selfDiv).click(() => {
            //Start rotation
            directionControls.pressed('right', 'fastest');
            //Capture single.
            const exposure = parseInt(1000000*parseFloat($('#settings_polar_align_assist_exposure_time', this._selfDiv).val()));
            const iso = parseInt($('#settings_polar_align_assist_iso', this._selfDiv).val());
            this._continuous = false;
            this._capture = true;
            this._rotate = true;
            this._PAACapture(exposure, iso, true);
        });
        window._testStage = this._stage;
        this._selfDiv.on('shown.bs.modal', () => {
            this._$canvas[0].width = this._$canvas.parent().width();
            this._$canvas[0].height = this._$canvas.parent().width();
        });
        this._selfDiv.on('hidden.bs.modal', () => {
            this._capture = false;
            $.ajax({
                url: '/paa_capture',
                method: 'DELETE'
            });
            $('#settings_polar_align_assist_capture', this._selfDiv).text(' Capture');
        });
        console.log(App);
        App.socket.on('paa_capture_response', _.throttle((msg) => {
            console.log('got socket paa_capture_response', msg);
            if(this._rotate) {
                this._rotate = false;
                //Stop rotation
                directionControls.unpressed('right');
            }
            const image = new Image();
            image.onload = () => {
                console.log('image.onload');
                this._cameraImage = new createjs.Bitmap(image);
                this._update();
                //Capture again if continuous
                if(this._capture && !this._continuous) {
                    this._capture = false;
                }
                if(this._capture && this._continuous) {
                    //this._PAACapture();
                } else {
                    $('#settings_polar_align_assist_capture', this._selfDiv).text(' Capture');
                }
            };
            image.src = '/paa_image?ts='+new Date().getTime();
        }, 250));
    }

    _PAACapture(exposure, iso, single) {
        $.ajax({
            url: '/paa_capture',
            method: 'POST',
            data: {exposure: exposure, single: single, iso: iso}
        });
    }

    _update() {
        this._stage.removeAllChildren();
        this._stage.clear();
        this._canvasSize = [this._$canvas.width(), this._$canvas.height()];
        const transform = {
            scale: parseFloat($('#settings_polar_align_assist_zoom', this._selfDiv).val())/100.0,
            rotation: parseFloat($('#settings_polar_align_assist_rotation', this._selfDiv).val())
        };
        this._cameraImage.setTransform(0, 0, transform.scale, transform.scale, 0, 0, 0, this._cameraRotationXY[0], this._cameraRotationXY[1]);
        this._cameraImage.x = this._canvasSize[0]/2;
        this._cameraImage.y = this._canvasSize[1]/2;
        this._overlayImage.setTransform(0, 0, transform.scale, transform.scale, transform.rotation, 0, 0, this._overlayImageReg[0], this._overlayImageReg[1]);
        this._overlayImage.x = this._canvasSize[0]/2.0;
        this._overlayImage.y = this._canvasSize[1]/2.0;
        this._overlayImage.alpha = parseFloat($('#settings_polar_align_assist_overlay_opacity').val())/100.0;
        this._stage.addChild(this._cameraImage);
        this._stage.addChild(this._overlayImage);
        this._stage.update();
    }

    show() {
        this._selfDiv.data('bs.modal', null).modal({backdrop: true, keyboard: true});
    }
}

export default SettingsMenuPolarAlignAssist;
