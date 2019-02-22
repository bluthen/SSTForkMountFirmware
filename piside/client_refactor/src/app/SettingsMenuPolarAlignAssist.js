/* global $ */
import template from './templates/SettingsMenuPolarAlignAssist.html'


// thatOneGuy's answer at https://stackoverflow.com/questions/32861804/how-to-calculate-the-centre-point-of-a-circle-given-three-points
function calculateCircle(A, B, C) {
    const yDelta_a = B.y - A.y;
    const xDelta_a = B.x - A.x;
    const yDelta_b = C.y - B.y;
    const xDelta_b = C.x - B.x;

    const center = {};

    const aSlope = yDelta_a / xDelta_a;
    const bSlope = yDelta_b / xDelta_b;

    center.x = (aSlope * bSlope * (A.y - C.y) + bSlope * (A.x + B.x) - aSlope * (B.x + C.x) ) / (2 * (bSlope - aSlope) );
    center.y = -1 * (center.x - (A.x + B.x) / 2) / aSlope + (A.y + B.y) / 2;

    const radius = Math.pow(Math.pow((A.x - center.x), 2.0) + Math.pow((A.y - center.y), 2.0), 0.5);

    return {center: center, radius: radius};
}

function forwardEvents(from, to) {
    from.addEventListener('mousedown', function (e) {
        const new_e = new e.constructor(e.type, e);
        to.dispatchEvent(new_e);
    });
    from.addEventListener('mouseup', function (e) {
        const new_e = new e.constructor(e.type, e);
        to.dispatchEvent(new_e);
    });
    from.addEventListener('touchstart', function (e) {
        const new_e = new e.constructor(e.type, e);
        to.dispatchEvent(new_e);
    });
    from.addEventListener('touchend', function (e) {
        const new_e = new e.constructor(e.type, e);
        to.dispatchEvent(new_e);
    });
    from.addEventListener('keyup', function (e) {
        const new_e = new e.constructor(e.type, e);
        to.dispatchEvent(new_e);
    });
    from.addEventListener('keydown', function (e) {
        const new_e = new e.constructor(e.type, e);
        to.dispatchEvent(new_e);
    });
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

        this._throttled = false;
        this._cameraRotationXY = [906, 728];
        this._$canvas = $('canvas', this._selfDiv);
        $('input[type="number"]', this._selfDiv).inputSpinner();
        this._cameraImage = null;
        this._circles = [];
        this._dataCanvas = document.createElement('canvas');
        this._dataCanvasContext = this._dataCanvas.getContext('2d');
        this._overlayImage = new createjs.Bitmap("paa_overlay.png");
        this._overlayImageReg = [906, 728];
        this._overlayImagePolarisTheta = null;
        fetch('paa_overlay.json').then((response) => {
            return response.json();
        }).then((j) => {
            this._overlayImageReg = j.ncp_xy;
            this._overlayImagePolarisTheta = j.polaris_theta;
        }, (err) => {
            console.error(err);
        });
        this._solveImage = null;
        this._solveImageCount = 0;
        this._solveImageInfo = null;
        this._lastSolveImageCount = 0;
        this._stage = new createjs.Stage(this._$canvas[0]);
        this._stage.update();
        $('#settings_polar_align_assist_exposure_time', this._selfDiv).change(_.debounce(this._exposureTimeChange_event.bind(this), 500));
        $('#settings_polar_align_assist_iso', this._selfDiv).change(_.debounce(this._isoChange_event.bind(this), 500));
        $('#settings_polar_align_assist_zoom, #settings_polar_align_assist_rotation, #settings_polar_align_assist_overlay_opacity, #settings_polar_align_assist_solve_opacity', this._selfDiv).change(this._update.bind(this));
        $('#settings_polar_align_assist_save', this._selfDiv).click(this._saveClick_event.bind(this));
        $('#settings_polar_align_assist_find_rotation_axis', this._selfDiv).click(() => {
            const coords = JSON.parse($('#settings_polar_align_assist_dev_coords', this._selfDiv).val());
            const A = {x: coords[0][0], y: coords[0][1]};
            const B = {x: coords[1][0], y: coords[1][1]};
            const C = {x: coords[2][0], y: coords[2][1]};
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

        //Canvas side buttons
        forwardEvents($('#polar_align_canvas_zoom_plus', this._selfDiv)[0], $('.btn-increment', $('#settings_polar_align_assist_zoom', this._selfDiv).parent())[0]);
        forwardEvents($('#polar_align_canvas_zoom_minus', this._selfDiv)[0], $('.btn-decrement', $('#settings_polar_align_assist_zoom', this._selfDiv).parent())[0]);
        forwardEvents($('#polar_align_canvas_rotation_plus', this._selfDiv)[0], $('.btn-increment', $('#settings_polar_align_assist_rotation', this._selfDiv).parent())[0]);
        forwardEvents($('#polar_align_canvas_rotation_minus', this._selfDiv)[0], $('.btn-decrement', $('#settings_polar_align_assist_rotation', this._selfDiv).parent())[0]);

        setInterval(() => {
            if (this._selfDiv.is(':visible')) {
                this._solve();
            }
        }, 25000);
        App.socket.on('paa_capture_response', this._socketCaptureResponse_event.bind(this));
        App.socket.on('paa_solve_done', this._solveDone.bind(this));

    }

    _solve() {
        $.ajax({
            url: '/paa_solve',
            method: 'POST',
            data: {
                low: $('#settings_polar_align_assist_solve_width_low', this._selfDiv).val(),
                high: $('#settings_polar_align_assist_solve_width_high', this._selfDiv).val(),
                pixel_error: $('#settings_polar_align_assist_solve_pixel_error', this._selfDiv).val(),
                code_tolerance: $('#settings_polar_align_assist_solve_code_tolerance', this._selfDiv).val()
            }
        });
    }

    _solveDone() {
        $.ajax({
            url: '/paa_solve_info', dataType: 'json', method: 'GET', success: (d) => {
                const image = new Image();
                const sic = this._solveImageCount;
                image.onload = () => {
                    if (sic === this._solveImageCount) {
                        this._solveImageCount++;
                        this._solveImageInfo = d;
                        if ($('#settings_polar_align_assist_solve_auto_rotate', this._selfDiv).is(':checked') && this._overlayImagePolarisTheta && d.polaris_theta) {
                            let rdegrees = 180.0 / Math.PI * (d.polaris_theta - this._overlayImagePolarisTheta);
                            if (rdegrees < 0) {
                                rdegrees += 360.0;
                            }
                            //TODO: Set rotation input to rdegrees if option is checked to do that.
                            $('#settings_polar_align_assist_rotation', this._selfDiv).val(rdegrees);
                        }
                        this._solveImage = new createjs.Bitmap(image);
                        $('div[name="paa_solve"]', this._selfDiv).text('Last Solve: ' + parseFloat(d.solve_time).toFixed(1) + 's, ' + d.last_solve)
                        this._update();
                    }
                };
                image.src = "/paa_solve_image?ts=" + new Date().getTime();
            }
        });
    }

    _exposureTimeChange_event() {
        const exposure = parseInt(1000000 * parseFloat($('#settings_polar_align_assist_exposure_time', this._selfDiv).val()));
        const iso = parseInt($('#settings_polar_align_assist_iso', this._selfDiv).val());
        this._PAACapture(exposure, iso);
    }

    _isoChange_event() {
        const exposure = parseInt(1000000 * parseFloat($('#settings_polar_align_assist_exposure_time', this._selfDiv).val()));
        const iso = parseInt($('#settings_polar_align_assist_iso', this._selfDiv).val());
        this._PAACapture(exposure, iso);
    }

    _saveClick_event() {
        const x = parseInt($('#settings_polar_align_assist_config_rotation_x').val(), 10);
        const y = parseInt($('#settings_polar_align_assist_config_rotation_y').val(), 10);
        this._cameraRotationXY = [x, y];
        const settings = {
            polar_align_camera_rotation_x: this._cameraRotationXY[0],
            polar_align_camera_rotation_y: this._cameraRotationXY[1]
        };
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

    _centroid(xc, yc, data, radius = 15, rcount = 0) {
        window.data = data;
        // console.log(data);
        const background = 0.0;
        //y = 0.2126*r + 0.7152*g + 0.0722*b
        const nx = this._dataCanvas.width;
        const ny = this._dataCanvas.height;

        const xci = Math.round(xc - radius);
        const xcf = Math.round(xc + radius);
        const yci = Math.round(yc - radius);
        const ycf = Math.round(yc + radius);
        let centerx = 0.0;
        let centery = 0.0;
        let t = 0.0;
        for (let x = xci; x <= xcf; x++) {
            for (let y = yci; y <= ycf; y++) {
                if (x >= 0 && x < nx && y >= 0 && y < ny) {
                    t += data[y * nx * 4 + x * 4] - background;
                    centerx += x * (data[y * nx * 4 + x * 4] - background);
                    centery += y * (data[y * nx * 4 + x * 4] - background);
                }
            }
        }
        centerx = centerx / t;
        centery = centery / t;
        if ((Math.abs(centerx - xc) > 0.01 || Math.abs(centery - yc) > 0.01) && rcount < 20) {
            return this._centroid(centerx, centery, data, radius, rcount + 1);
        } else {
            return [centerx, centery];
        }
    }

    _socketCaptureResponse_event(msg) {
        if (this._throttled || !this._selfDiv.is(':visible')) {
            // If phone/tablet too slow and exposure fast, or not visible.
            console.log('throttled or hidden');
            return;
        }
        console.log(msg);
        clearTimeout(this._throttledTO);
        this._throttled = true;
        this._throttledTO = setTimeout(() => {
            this._throttled = false;
        }, 2000);
        // console.log('got socket paa_capture_response', msg);
        if (msg.hasOwnProperty('status')) {
            $('[name="paa_status"]', this._selfDiv).text('Last Status: ' + msg.status + ', ' + new Date());
        } else {
            $('[name="paa_status"]', this._selfDiv).text('Last Status: Exposure ' + msg.paa_count + ', ' + new Date());
            const image = new Image();
            image.onload = () => {
                this._throttled = false;
                // console.log('image.onload');
                this._cameraImage = new createjs.Bitmap(image);
                this._dataCanvas.width = image.width;
                this._dataCanvas.height = image.height;
                this._dataCanvasContext.drawImage(image, 0, 0);
                this._cameraImage.addEventListener('click', (e) => {
                    // console.log(e.localX, e.localY);
                    const data = this._dataCanvasContext.getImageData(0, 0, this._dataCanvas.width, this._dataCanvas.height).data;
                    const c = this._centroid(e.localX, e.localY, data);
                    $('div[name="paa_select"]', this._selfDiv).text('Select: ' + c[0] + ', ' + c[1]);
                    // console.log(e.localX, e.localY, c);
                    let v = $('#settings_polar_align_assist_dev_coords', this._selfDiv).val().trim();
                    if (v) {
                        v = JSON.parse(v);
                        v.push([c[0], c[1]]);
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
            };
            image.src = '/paa_image?ts=' + new Date().getTime();
        }
    }

    _PAACapture(exposure, iso) {
        $.ajax({
            url: '/paa_capture',
            method: 'POST',
            data: {exposure: exposure, iso: iso}
        });
    }

    _update() {
        $('#polar_align_canvas_rotation_label', this._selfDiv).text(parseFloat($('#settings_polar_align_assist_rotation', this._selfDiv).val()).toFixed(1) + '%');
        $('#polar_align_canvas_zoom_label', this._selfDiv).html($('#settings_polar_align_assist_zoom', this._selfDiv).val() + '&deg;');

        this._stage.removeAllChildren();
        this._stage.clear();
        this._canvasSize = [this._$canvas.width(), this._$canvas.height()];
        const transform = {
            scale: parseFloat($('#settings_polar_align_assist_zoom', this._selfDiv).val()) / 100.0,
            rotation: parseFloat($('#settings_polar_align_assist_rotation', this._selfDiv).val())
        };
        const markers = [];
        if (this._cameraImage) {
            for (let i = 0; i < this._circles.length; i++) {
                const circle = new createjs.Shape();
                const g = circle.graphics;
                g.beginStroke('#FF0000');
                g.drawCircle(this._circles[i][0], this._circles[i][1], this._circles[i][2]);
                g.endStroke();
                circle.setTransform(0, 0, transform.scale, transform.scale, 0, 0, 0, this._cameraRotationXY[0], this._cameraRotationXY[1]);
                circle.x = this._canvasSize[0] / 2;
                circle.y = this._canvasSize[1] / 2;
                markers.push(circle);
            }
            this._cameraImage.setTransform(0, 0, transform.scale, transform.scale, 0, 0, 0, this._cameraRotationXY[0], this._cameraRotationXY[1]);
            this._cameraImage.x = this._canvasSize[0] / 2;
            this._cameraImage.y = this._canvasSize[1] / 2;
        }
        if (this._solveImage) {
            this._solveImage.setTransform(0, 0, transform.scale, transform.scale, 0, 0, 0, this._cameraRotationXY[0], this._cameraRotationXY[1]);
            this._solveImage.x = this._canvasSize[0] / 2;
            this._solveImage.y = this._canvasSize[1] / 2;
            this._solveImage.alpha = parseFloat($('#settings_polar_align_assist_solve_opacity', this._selfDiv).val()) / 100.0;
        }
        this._overlayImage.setTransform(0, 0, transform.scale, transform.scale, transform.rotation, 0, 0, this._overlayImageReg[0], this._overlayImageReg[1]);
        this._overlayImage.x = this._canvasSize[0] / 2.0;
        this._overlayImage.y = this._canvasSize[1] / 2.0;
        this._overlayImage.alpha = parseFloat($('#settings_polar_align_assist_overlay_opacity', this._selfDiv).val()) / 100.0;
        this._stage.addChild(this._cameraImage);
        this._stage.addChild(this._solveImage);
        for (let i = 0; i < markers.length; i++) {
            this._stage.addChild(markers[i]);
        }
        this._stage.addChild(this._overlayImage);
        this._stage.update();
    }

    show() {
        this._selfDiv.show();
        this._$canvas[0].width = this._$canvas.parent().width();
        this._$canvas[0].height = window.innerHeight * 0.75;
        this._update();

    }

    hide() {
        this._selfDiv.hide();
    }
}

export default SettingsMenuPolarAlignAssist;
