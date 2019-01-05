/* global $ */
import template from './templates/SettingsMenuPolarAlignAssist.html'


// thatOneGuy's answer at https://stackoverflow.com/questions/32861804/how-to-calculate-the-centre-point-of-a-circle-given-three-points
function calculateCircle(A,B,C)
{
    const yDelta_a = B.y - A.y;
    const xDelta_a = B.x - A.x;
    const yDelta_b = C.y - B.y;
    const xDelta_b = C.x - B.x;

    const center = {};

    const aSlope = yDelta_a / xDelta_a;
    const bSlope = yDelta_b / xDelta_b;

    center.x = (aSlope*bSlope*(A.y - C.y) + bSlope*(A.x + B.x) - aSlope*(B.x+C.x) )/(2* (bSlope-aSlope) );
    center.y = -1*(center.x - (A.x+B.x)/2)/aSlope +  (A.y+B.y)/2;

    const radius = Math.pow(Math.pow((A.x - center.x), 2.0) + Math.pow((A.y - center.y), 2.0), 0.5);

    return {center: center, radius: radius};
}


class SettingsMenuPolarAlignAssist {
    constructor(App, parentDiv, directionControls) {
        this._selfDiv = $(template);
        this._directionControls = directionControls;
        parentDiv.append(this._selfDiv);
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
        this._calibrate = false;
        this._cameraImage = null;
        this._circles = [];
        this._dataCanvas = document.createElement('canvas');
        this._dataCanvasContext = this._dataCanvas.getContext('2d');
        this._overlayImage = new createjs.Bitmap("1533416531_work.png");
        this._overlayImageReg = [906, 728];
        this._stage = new createjs.Stage(this._$canvas[0]);
        this._stage.update();
        $('#settings_polar_align_assist_exposure_time', this._selfDiv).change(_.debounce(this._exposureTimeChange_event.bind(this), 500));
        $('#settings_polar_align_assist_iso', this._selfDiv).change(_.debounce(this._isoChange_event.bind(this), 500));
        $('#settings_polar_align_assist_capture', this._selfDiv).click(this._captureClick_event.bind(this));
        $('#settings_polar_align_assist_zoom, #settings_polar_align_assist_rotation, #settings_polar_align_assist_overlay_opacity', this._selfDiv).change(this._update.bind(this));
        $('#settings_polar_align_assist_save', this._selfDiv).click(this._saveClick_event.bind(this));
        $('#settings_polar_align_assist_find_rotation_axis', this._selfDiv).click(() => {
           const coords = JSON.parse($('#settings_polar_align_assist_dev_coords', this._selfDiv).val());
           const A = {x: coords[0][0], y:coords[0][1]};
           const B = {x: coords[1][0], y:coords[1][1]};
           const C = {x: coords[2][0], y:coords[2][1]};
           const cir = calculateCircle(A, B, C);
           // console.log('circle', cir);
           this._circles = [[cir.center.x, cir.center.y, 2], [cir.center.x, cir.center.y, cir.radius]];
           $('#settings_polar_align_assist_config_rotation_x', this._selfDiv).val(cir.center.x);
            $('#settings_polar_align_assist_config_rotation_y', this._selfDiv).val(cir.center.y);
           this._update();
        });
        $(window).on('resize', () => {
            if (this._selfDiv.is(':visible')) {
                this.show();
            }
        });
        App.socket.on('paa_capture_response', this._socketCaptureResponse_event.bind(this));
    }

    _exposureTimeChange_event() {
        const exposure = parseInt(1000000*parseFloat($('#settings_polar_align_assist_exposure_time', this._selfDiv).val()));
        const iso = parseInt($('#settings_polar_align_assist_iso', this._selfDiv).val());
        if(this._continuous && this._capture) {
            this._PAACapture(exposure, iso, -1, 0.25, false);
        }
    }

    _isoChange_event() {
        const exposure = parseInt(1000000*parseFloat($('#settings_polar_align_assist_exposure_time', this._selfDiv).val()));
        const iso = parseInt($('#settings_polar_align_assist_iso', this._selfDiv).val());
        if(this._continuous && this._capture) {
            this._PAACapture(exposure, iso, -1, 0.25, false);
        }
    }

    _captureClick_event() {
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
            const count = this._continuous ? -1 : 1;
            if(this._continuous) {
                $('#settings_polar_align_assist_capture', this._selfDiv).text(' Stop Capturing');
            } else {
                $('#settings_polar_align_assist_capture', this._selfDiv).text(' Capturing...');
            }
            this._PAACapture(exposure, iso, count, 0.25, false);
        }
    }

    _saveClick_event() {
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
            }
        });
        this._update();
    }

    _centroid(xc, yc, data, radius=15, rcount=0) {
        window.data = data;
        // console.log(data);
        const background = 0.0;
        //y = 0.2126*r + 0.7152*g + 0.0722*b
        const nx = this._dataCanvas.width;
        const ny = this._dataCanvas.height;

        const xci=Math.round(xc-radius);
        const xcf=Math.round(xc+radius);
        const yci=Math.round(yc-radius);
        const ycf=Math.round(yc+radius);
        let centerx=0.0;
        let centery=0.0;
        let t = 0.0;
        for(let x=xci; x<=xcf; x++){
            for(let y=yci; y<=ycf; y++){
                if(x >= 0 && x < nx && y >=0 && y < ny){
                    t+=data[y*nx*4+x*4]-background;
                    centerx+=x*(data[y*nx*4+x*4]-background);
                    centery+=y*(data[y*nx*4+x*4]-background);
                }
            }
        }
        centerx=centerx/t;
        centery=centery/t;
        if ((Math.abs(centerx - xc) > 0.01 || Math.abs(centery - yc) > 0.01) && rcount < 20) {
            return this._centroid(centerx, centery, data, radius, rcount + 1);
        } else {
            return [centerx, centery];
        }
    }

    _socketCaptureResponse_event(msg) {
        // console.log('got socket paa_capture_response', msg);
        if (msg.hasOwnProperty('status')) {
            $('[name="paa_status"]', this._selfDiv).text('Last Status: '+msg.status);
        } else {
            if(this._calibrate && msg.done) {
                this._calibrate = false;
                this._continuous = false;
                //Stop rotation
                this._directionControls.unpressed('right');
                this._directionControls.unpressed('left');
            }
            const image = new Image();
            image.onload = () => {
                // console.log('image.onload');
                this._cameraImage = new createjs.Bitmap(image);
                this._dataCanvas.width = image.width;
                this._dataCanvas.height = image.height;
                this._dataCanvasContext.drawImage(image, 0, 0);
                this._cameraImage.addEventListener('click', (e) => {
                    // console.log(e.localX, e.localY);
                    const data = this._dataCanvasContext.getImageData(0, 0, this._dataCanvas.width, this._dataCanvas.height).data;
                    const c = this._centroid(e.localX, e.localY, data);
                    $('div[name="paa_select"]', this._selfDiv).text('Select: '+c[0]+', '+c[1]);
                    // console.log(e.localX, e.localY, c);
                    let v=$('#settings_polar_align_assist_dev_coords', this._selfDiv).val().trim();
                    if (v) {
                        v = JSON.parse(v);
                        v.push([c[0],c[1]]);
                    } else {
                        v = [[c[0], c[1]]]
                    }
                    $('#settings_polar_align_assist_dev_coords', this._selfDiv).val(JSON.stringify(v));
                    c.push(10);
                    this._circles = [c];
                    this._update();
                    //const data = this._dataCanvasContext.getImageData(e.localX, e.localY, 1, 1).data;
                    //console.log(data);
                });
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
        }
    }

    _PAACapture(exposure, iso, count, delaySeconds, calibration) {
        $.ajax({
            url: '/paa_capture',
            method: 'POST',
            data: {exposure: exposure, iso: iso, count: count, delay: delaySeconds, calibration: calibration}
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
        const markers = [];
        if(this._cameraImage) {
            for(let i = 0; i < this._circles.length; i++) {
                const circle = new createjs.Shape();
                const g = circle.graphics;
                g.beginStroke('#FF0000');
                g.drawCircle(this._circles[i][0], this._circles[i][1], this._circles[i][2]);
                g.endStroke();
                circle.setTransform(0, 0, transform.scale, transform.scale, 0, 0, 0, this._cameraRotationXY[0], this._cameraRotationXY[1]);
                circle.x = this._canvasSize[0]/2;
                circle.y = this._canvasSize[1]/2;
                markers.push(circle);
            }
            this._cameraImage.setTransform(0, 0, transform.scale, transform.scale, 0, 0, 0, this._cameraRotationXY[0], this._cameraRotationXY[1]);
            this._cameraImage.x = this._canvasSize[0]/2;
            this._cameraImage.y = this._canvasSize[1]/2;
        }
        this._overlayImage.setTransform(0, 0, transform.scale, transform.scale, transform.rotation, 0, 0, this._overlayImageReg[0], this._overlayImageReg[1]);
        this._overlayImage.x = this._canvasSize[0]/2.0;
        this._overlayImage.y = this._canvasSize[1]/2.0;
        this._overlayImage.alpha = parseFloat($('#settings_polar_align_assist_overlay_opacity', this._selfDiv).val())/100.0;
        this._stage.addChild(this._cameraImage);
        for(let i = 0; i < markers.length; i++) {
            this._stage.addChild(markers[i]);
        }
        this._stage.addChild(this._overlayImage);
        this._stage.update();
    }

    show() {
        this._selfDiv.show();
        this._$canvas[0].width = this._$canvas.parent().width();
        this._$canvas[0].height = window.innerHeight*0.75;
        this._update();

    }

    hide() {
        this._selfDiv.hide();
        this._capture = false;
        $.ajax({
            url: '/paa_capture',
            method: 'DELETE'
        });
        $('#settings_polar_align_assist_capture', this._selfDiv).text(' Capture');
    }
}

export default SettingsMenuPolarAlignAssist;
