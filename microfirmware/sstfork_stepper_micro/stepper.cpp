#include "stepper.h"
#include <digitalWriteFast.h>


static int timerCounter = 0;
static const int MICROSTEPS_IN_SINGLESTEP = 16;


template<typename T> int sgn(T val) {
  return (T(0) < val) - (val < T(0));
}


Stepper::Stepper(const int _dir_pin, const int _step_pin, const int _ms1_pin,
                 const int _ms2_pin, const int _ms3_pin, uint8_t enc_chan,
                 uint16_t enc_apin, uint16_t enc_bpin) {
  dir_pin = _dir_pin;
  step_pin = _step_pin;
  ms1_pin = _ms1_pin;
  ms2_pin = _ms2_pin;
  ms3_pin = _ms3_pin;
  if (enc_apin != enc_bpin) {
    enc = new QuadEncoder(enc_chan, enc_apin, enc_bpin);
    enc->setInitConfig();
    enc->init();
  }
  pinModeFast(dir_pin, OUTPUT);
  pinModeFast(step_pin, OUTPUT);
  pinModeFast(ms1_pin, OUTPUT);
  pinModeFast(ms2_pin, OUTPUT);
  pinModeFast(ms3_pin, OUTPUT);
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
  },
                   200ms, false);
  timerCounter++;
}

void Stepper::setSpeed(float speed) {
  sp_speed = speed;
}

float Stepper::getSpeed() {
  float ret;
  cli();
  ret = v0;
  sei();
  return ret;
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
    if (speed > micro_threshold_v) {
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
    digitalWriteFast(ms1_pin, LOW);
    digitalWriteFast(ms2_pin, LOW);
    digitalWriteFast(ms3_pin, HIGH);
    // At full step every step is 16 microsteps
    stepResolution = MICROSTEPS_IN_SINGLESTEP;
    sei();
  } else if (!_single_step && single_step) {
    single_step = false;
    cli();
    digitalWriteFast(ms1_pin, HIGH);
    digitalWriteFast(ms2_pin, HIGH);
    digitalWriteFast(ms3_pin, LOW);
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
