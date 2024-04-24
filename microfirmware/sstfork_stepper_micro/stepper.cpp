#include "stepper.h"
#include <digitalWriteFast.h>

static int timerCounter = 0;
static const int MICROSTEPS_IN_SINGLESTEP = 32;
static const float CURRENT_TO_RMS = 0.7071;  // 1/sqrt(2) see page 74 of datasheet
// GLOBALSCALER/256  *  (CS + 1)/32  *  V_FS/R_SENSE  *  1/sqrt(2)

template<typename T> int sgn(T val) {
  return (T(0) < val) - (val < T(0));
}

Stepper::Stepper(const int _dir_pin, const int _step_pin, const int _cs_pin,
                 uint8_t enc_chan, uint16_t enc_apin, uint16_t enc_bpin) {
  dir_pin = _dir_pin;
  step_pin = _step_pin;
  if (enc_apin != enc_bpin) {
    enc = new QuadEncoder(enc_chan, enc_apin, enc_bpin);
    enc->setInitConfig();
    enc->init();
  }
  pinModeFast(dir_pin, OUTPUT);
  pinModeFast(step_pin, OUTPUT);
  driver = new TMC5160Stepper(_cs_pin);
  driver->begin();
  driver->intpol(true);
  driver->en_pwm_mode(false);
  driver->pwm_autograd(true);
  driver->pwm_autoscale(true);
  driver->en_pwm_mode(true);
  this->setCurrents();
  if (timerCounter == 0) {
    stepTimer = new TeensyTimerTool::PeriodicTimer(TeensyTimerTool::GPT1);
  } else if (timerCounter == 1) {
    stepTimer = new TeensyTimerTool::PeriodicTimer(TeensyTimerTool::GPT2);
  } else {
    stepTimer = new TeensyTimerTool::PeriodicTimer();
  }
  setStepDirection(false);
  this->step();
  delay(50);
  this->step();
  delay(50);
  setStepDirection(true);
  this->step();
  delay(50);
  this->step();
  delay(50);
  stepTimer->begin([this] {
    this->step();
  }, 200ms, false);
  timerCounter++;
}

void Stepper::setSpeed(float speed) {
  sp_speed = speed;
}

float Stepper::getSpeed() {
  return v0;
}

long Stepper::getPosition() {
  long ret;
  cli();
  ret = x0;
  sei();
  return ret;
}

void Stepper::getEncoder(stepper_encoder_t& encodervalues) {
  cli();
  encodervalues.value = last_encoder;
  encodervalues.steps_in_pulse = steps_in_pulse;
  encodervalues.prev_steps_in_pulse = steps_in_pulse;
  sei();
}

void Stepper::setInvertedStepping(bool inverted) {
  inv_direction = inverted;
  setStepDirection(mode_forward);
}

bool Stepper::getInvertedStepping() {
  return inv_direction;
}

void Stepper::setSingleStepThreshold(long steps_per_sec) {
  micro_threshold_v = steps_per_sec;
}

long Stepper::getSingleStepThreshold() {
  return micro_threshold_v;
}

void Stepper::enableEncoder(bool enabled) {
  enc_enabled = true;
}

bool Stepper::encoderEnabled() {
  return enc_enabled;
}

void Stepper::setRealSpeed(float speed) {
  if (fabs(speed) < 0.05) {
    stepTimer->stop();
    stepper_stopped = true;
    v0 = 0;
    return;
  }
  float sp;
  // Only bother changing frequency if speed different is more than 1 step per
  // 1000 seconds.
  if (fabs(v0 - speed) > 0.001) {
    if (fabs(speed) > micro_threshold_v) {
      setStepResolution(true);
      sp = 500000000 / (speed * MICROSTEPS_IN_SINGLESTEP);  // us
    } else {
      setStepResolution(false);
      sp = 500000000 / speed;  // us
    }
    // Must be 0.5 * desired period because square wave on and off.
    stepTimer->setPeriod(sp);
    v0 = speed;
  }
  if (stepper_stopped) {
    stepper_stopped = false;
    stepTimer->start();
  }
  setCurrents();
}

void Stepper::setStepDirection(bool forward) {
  cli();
  if (forward) {
    if (!inv_direction) {
      digitalWriteFast(dir_pin, HIGH);
    } else {
      digitalWriteFast(dir_pin, LOW);
    }
    mode_forward = true;
  } else {
    if (!inv_direction) {
      digitalWriteFast(dir_pin, LOW);
    } else {
      digitalWriteFast(dir_pin, HIGH);
    }
    mode_forward = true;
  }
  sei();
}

void Stepper::setStepResolution(bool _single_step) {
  if (_single_step && !single_step) {
    single_step = true;
    cli();
    // Single step on TB67S249FTG_DRIVER
    driver->microsteps(0);
    // At full step every step is 16 microsteps
    stepResolution = MICROSTEPS_IN_SINGLESTEP;
    sei();
  } else if (!_single_step && single_step) {
    single_step = false;
    cli();
    driver->microsteps(MICROSTEPS_IN_SINGLESTEP);
    // Every micro step is 1 microsteps
    stepResolution = 1;
    sei();
  }
}

void Stepper::step() {
  bool on = !digitalReadFast(step_pin);
  digitalWriteFast(step_pin, on);
  if (on) {
    if (mode_forward) {
      x0 += stepResolution;
    } else {
      x0 -= stepResolution;
    }
  }
  if (enc_enabled) {
    long encV = enc->read();
    if (encV != last_encoder) {
      prev_steps_in_pulse = steps_in_pulse;
      steps_in_pulse = 0;
      last_encoder = encV;
    } else {
      if (on) {
        if (mode_forward) {
          steps_in_pulse += stepResolution;
        } else {
          steps_in_pulse -= stepResolution;
        }
      }
    }
  }
}

void Stepper::setMaxAccel(float _accell_tpss) {
  accell_tpss = _accell_tpss;
}

float Stepper::getMaxAccel() {
  return accell_tpss;
}

void Stepper::setMaxSpeed(float _max_tps) {
  max_v0 = _max_tps;
}

float Stepper::getMaxSpeed() {
  return max_v0;
}

bool Stepper::enabled() {
  return stepper_enabled;
}

void Stepper::enable(bool _enable) {
  stepper_enabled = _enable;
}

void Stepper::setGuideRate(long _guideRate) {
  guide_rate = _guideRate;
}

long Stepper::getGuideRate() {
  return guide_rate;
}

void Stepper::guide(int direction) {
  guiding = direction;
}

void Stepper::disableGuiding(bool disable) {
  guiding_enabled = !disable;
}

bool Stepper::guidingDisabled() {
  return !guiding_enabled;
}

void Stepper::setRunCurrent(float _run_current) {
  run_current = _run_current;
  setCurrents();
}

void Stepper::setMedCurrent(float _med_current) {
  med_current = _med_current;
  setCurrents();
}

void Stepper::setMedCurrentThreshold(float _med_current_threshold) {
  med_current_threshold = _med_current_threshold;
  setCurrents();
}

void Stepper::setHoldCurrent(float _hold_current) {
  hold_current = _hold_current;
  setCurrents();
}

float Stepper::getRunCurrent() {
  return run_current;
}

float Stepper::getMedCurrent() {
  return med_current;
}

float Stepper::getMedCurrentThreshold() {
  return med_current_threshold;
}

float Stepper::getHoldCurrent() {
  return hold_current;
}

void Stepper::setCurrents() {
  if (current_real != run_current && fabs(v0) >= med_current_threshold) {
    current_real = run_current;
    cli();
    driver->rms_current(current_real * CURRENT_TO_RMS, hold_current / current_real);
    sei();
  } else if (current_real != med_current && fabs(v0) < med_current_threshold) {
    current_real = med_current;
    cli();
    driver->rms_current(current_real * CURRENT_TO_RMS, hold_current / current_real);
    sei();
  }
}

void Stepper::update() {
  float new_speed;
  long t = timer / 1000000.0;
  float sp = sp_speed;
  //  long should_position;
  //  long delta_x;
  //  cli();
  //  delta_x = x0;
  //  sei();
  //  motion_func(accell, v0, delta_x, t, sp_speed, should_position, new_speed);
  if (guiding_enabled && guiding != 0) {
    sp += guiding * guide_rate;
  }
  calcNewV(accell_tpss, v0, t, sp, new_speed);
  if (!stepper_enabled) {
    setRealSpeed(0);
  } else {
    if (fabs(new_speed) > max_v0) {
      setRealSpeed(copysignf(new_speed, max_v0));
    } else {
      setRealSpeed(new_speed);
    }
  }
  timer = 0;
}

void Stepper::calcNewV(float a, float v_0, double t, float speed_wanted,
                       float& new_speed) {
  double t_v_max, dt_v_max;
  float v;
  if (speed_wanted < v_0) {
    a = -a;
  }
  t_v_max = (speed_wanted - v_0) / a;
  dt_v_max = t - t_v_max;

  if (dt_v_max > 0) {
    v = speed_wanted;
  } else {
    v = a * t + v_0;
  }
  new_speed = v;
}

// void Stepper::motion_func(float a, float v_0, long x_0, double t, float
// speed_wanted, long &position, float& speed) {
//   double t_v_max, dt_v_max;
//   float v;
//   long p;
//   if (speed_wanted < v_0) {
//     a = -a;
//   }
//   t_v_max = (speed_wanted - v_0) / a;
//   dt_v_max = t - t_v_max;
//
//   if (dt_v_max > 0) {
//     p = (long)(0.5 * (double)a * t_v_max * t_v_max) + (long)((double)v_0 *
//     t_v_max) + x_0; p += (double)speed_wanted * dt_v_max; v = speed_wanted;
//   } else {
//     v = a * t + v_0;
//     p = (long)(0.5 * (double)a * t * t) + (long)((double)v_0 * t) + x_0;
//   }
//   position = p;
//   speed = v;
// }
