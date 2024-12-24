#include "stepper.h"
#include "forkmount.h"

static const int MICROSTEPS_IN_SINGLESTEP = 32;
static const float CURRENT_TO_RMS = 0.7071;  // 1/sqrt(2) see page 74 of datasheet
// GLOBALSCALER/256  *  (CS + 1)/32  *  V_FS/R_SENSE  *  1/sqrt(2)
static const bool STEP_DEDGE = true; // Step on rising or falling edge

template<typename T> int sgn(T val) {
  return (T(0) < val) - (val < T(0));
}

Stepper::Stepper(const int _dir_pin, const int _step_pin, 
                 const int _cs_pin, const int _miso_pin, const int _mosi_pin, const int _sck_pin,
                 uint8_t enc_chan, uint16_t enc_apin, uint16_t enc_bpin, uint8_t timer) {
  id = timer;
  dir_pin = _dir_pin;
  step_pin = _step_pin;
  if (enc_apin != enc_bpin) {
    enc = new QuadEncoder(enc_chan, enc_apin, enc_bpin);
    enc->setInitConfig();
    enc->init();
  }
  pinMode(dir_pin, OUTPUT);
  pinMode(step_pin, OUTPUT);
  //driver = new TMC5160Stepper(_cs_pin);
  //driver = new TMC5160Stepper(_cs_pin, 0.075f);
  //driver = new TMC5160Stepper(_cs_pin);

  driver = new TMC5160Stepper(_cs_pin, R_SENSE, _mosi_pin, _miso_pin, _sck_pin);
  //driver = new TMC5160Stepper(_cs_pin, _mosi_pin, _miso_pin, _sck_pin);

  driver->setSPISpeed(1000);
  driver->begin();
  delay(100);
  this->test_connection();
  driver->toff(5);
  this->setCurrents(true);

  driver->en_pwm_mode(true);
  driver->pwm_autoscale(true);
  driver->intpol(true);
  
  DEBUG_SERIAL.print("vhighfs: "); DEBUG_SERIAL.println(driver->vhighfs());
  driver->microsteps(MICROSTEPS_IN_SINGLESTEP);
  driver->dedge(STEP_DEDGE);
  single_step = false;

  if (id == 0) {
    stepTimer = new TeensyTimerTool::PeriodicTimer(TeensyTimerTool::GPT1);
  } else if (id == 1) {
    stepTimer = new TeensyTimerTool::PeriodicTimer(TeensyTimerTool::GPT2);
  } else {
    stepTimer = new TeensyTimerTool::PeriodicTimer();
  }
  setStepDirection(false);
  for(int i = 0; i < 8; i++) {
    this->step(true);
    delay(50);
  }
  setStepDirection(true);
  for(int i = 0; i < 8; i++) {
    this->step(true);
    delay(50);
  }
  stepTimer->begin([this] {
    this->step(true);
  }, 200ms, false);

  while(driver->microsteps() != MICROSTEPS_IN_SINGLESTEP) {
    driver->microsteps(MICROSTEPS_IN_SINGLESTEP);
  }

}

uint8_t Stepper::test_connection() {
  uint8_t tcv = driver->test_connection();
  while(tcv != 0) {
    if (Serial) {
      DEBUG_SERIAL.print("WARN: Test connection failed ");
      DEBUG_SERIAL.print(id);
      DEBUG_SERIAL.print(", ");
      DEBUG_SERIAL.println(tcv);
    }
    delay(1000);
    tcv = driver->test_connection();
  } 
  if (Serial) {
    DEBUG_SERIAL.print("Test Connection Good ");
    DEBUG_SERIAL.println(id);
  }
  return tcv;
}

void Stepper::setSpeed(float speed) {
  DEBUG_SERIAL.println(driver->DRV_STATUS(), BIN);
  sp_speed = speed;
  timer = 0;
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
    setCurrents(false);
    return;
  }
  float sp, dv;
  if (speed > 0) {
    setStepDirection(true);
  } else {
    setStepDirection(false);
  }
  dv = fabs(v0-speed);
  // Only bother changing frequency if speed different is more than 1 step per
  // 1000 seconds.
  if (dv > 0.001) {
    if (micro_threshold_v > 0 && fabs(speed) > micro_threshold_v) {
      setStepResolution(true);
      sp = 1000000.0 / (fabs(speed)/MICROSTEPS_IN_SINGLESTEP);  // us
    } else {
      setStepResolution(false);
      sp = 1000000.0 / (fabs(speed));  // us
    }
    // If dedge is false, Must be 0.5 * desired period because square wave on and off. otherwise can be period
    stepTimer->setPeriod((STEP_DEDGE ? 1.0 : 0.5) * sp);
    v0 = speed;
    setCurrents(false);
  }
  if (stepper_stopped) {
    stepper_stopped = false;
    stepTimer->start();
  }
}

void Stepper::backlashSteps() {
  stepTimer->stop();
  setStepResolution(false);
  for(int i = 0; i < (STEP_DEDGE ? 1 : 2) * backlash; i++) {
    step(false);
    if (backlashSpeed > 100) {
      delayMicroseconds((STEP_DEDGE ? 1 : 0.5) * 1000000/backlashSpeed);
    } else {
      delay((STEP_DEDGE ? 1 : 0.5) * 1000/backlashSpeed);
    }
  }
  if (!stepper_stopped) {
    stepTimer->start();
  }
  DEBUG_SERIAL.print("D: Done Backlash: ");
  DEBUG_SERIAL.print(driver->GCONF());
  DEBUG_SERIAL.print(" ");
  DEBUG_SERIAL.print(driver->GSTAT());
  DEBUG_SERIAL.print(" ");
  DEBUG_SERIAL.println(driver->SW_MODE());
}

void Stepper::setStepDirection(bool forward) {
  if (forward) {
    if (!inv_direction) {
      digitalWrite(dir_pin, HIGH);
    } else {
      digitalWrite(dir_pin, LOW);
    }
    if(!mode_forward && backlash > 0 && backlashSpeed > 0) {
      backlashSteps();
    }
    mode_forward = true;
  } else {
    if (!inv_direction) {
      digitalWrite(dir_pin, LOW);
    } else {
      digitalWrite(dir_pin, HIGH);
    }
    if(mode_forward && backlash > 0 && backlashSpeed > 0) {
      backlashSteps();
    }
    mode_forward = false;
  }
}

void Stepper::setStepResolution(bool _single_step) {
  if (_single_step && !single_step) {
    single_step = true;
    while(driver->microsteps() != 0) {
      driver->microsteps(0);
    }

    // At full step every step is X microsteps
    stepResolution = MICROSTEPS_IN_SINGLESTEP;
  } else if (!_single_step && single_step) {
    single_step = false;
    while(driver->microsteps() != MICROSTEPS_IN_SINGLESTEP) {
      driver->microsteps(MICROSTEPS_IN_SINGLESTEP);
    }
    // Every micro step is 1 microsteps
    stepResolution = 1;
  }
}

void Stepper::step(bool counters) {
  bool on = !digitalRead(step_pin);
  digitalWrite(step_pin, on);
  if (counters && (STEP_DEDGE || on)) {
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
      if(counters) {
        last_encoder = encV;
      } else {
        enc->write(last_encoder);
      }
    } else {
      if (STEP_DEDGE || on) {
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
  run_current = _run_current > 1 ? _run_current : 1;
  setCurrents(true);
}

void Stepper::setMedCurrent(float _med_current) {
  med_current = _med_current > 1 ? _med_current : 1;
  setCurrents(true);
}

void Stepper::setMedCurrentThreshold(float _med_current_threshold) {
  med_current_threshold = _med_current_threshold;
  setCurrents(true);
}

void Stepper::setHoldCurrent(float _hold_current) {
  // Setting 0 current doesn't work (at least if not doing ihold)
  hold_current = _hold_current > 1 ? _hold_current : 100;
  // if(Serial) {
  //   DEBUG_SERIAL.print("Set hold current: ");
  //   DEBUG_SERIAL.println(hold_current);
  // }
  setCurrents(true);
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

void Stepper::setCurrents(bool force) {
  if ((force || current_real != run_current) && fabs(v0) >= med_current_threshold && fabs(v0) > 0.0f) {
    current_real = run_current;
    //driver->rms_current((uint16_t)(current_real), hold_current / current_real);
    driver->rms_current((uint16_t)(current_real));
    if (Serial) {
      DEBUG_SERIAL.print("C1: ");
      DEBUG_SERIAL.print(current_real);
      DEBUG_SERIAL.print(", ");
      DEBUG_SERIAL.println(driver->rms_current());
    }
  } else if ((force || current_real != med_current) && fabs(v0) < med_current_threshold && fabs(v0) > 0.0f) {
    current_real = med_current;
    //driver->rms_current((uint16_t)(current_real), hold_current / current_real);
    driver->rms_current((uint16_t)(current_real));
    if (Serial) {
      DEBUG_SERIAL.print("C2: ");
      DEBUG_SERIAL.print(current_real);
      DEBUG_SERIAL.print(", ");
      DEBUG_SERIAL.println(driver->rms_current());
    }
  } else if ((force || current_real != hold_current) && fabs(v0) == 0.0f) {
    current_real = hold_current;
    //driver->rms_current((uint16_t)(current_real), hold_current / current_real);
    driver->rms_current((uint16_t)(current_real));
    if (Serial) {
      DEBUG_SERIAL.print("C3: ");
      DEBUG_SERIAL.print(current_real);
      DEBUG_SERIAL.print(", ");
      DEBUG_SERIAL.println(driver->rms_current());
    }    
  }
}

void Stepper::update() {
  // 30000
  if (timer < 30000) {
    return;
  }
  float new_speed;
  float t = timer / 1000000.0;
  float sp = sp_speed;
  if (guiding_enabled && guiding != 0) {
    sp += guiding * guide_rate;
  }
  calcNewV(accell_tpss, v0, t, sp, new_speed);
  if (!stepper_enabled) {
    setRealSpeed(0);
  } else {
    if (fabs(new_speed) > max_v0) {
      setRealSpeed(copysignf(max_v0, new_speed));
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

void Stepper::setBacklash(int _backlash) {
  backlash = _backlash;
}

void Stepper::setBlacklashSpeed(float _backlashSpeed) {
  backlashSpeed = _backlashSpeed;
}

int Stepper::getBacklash() {
  return backlash;
}

float Stepper::getBacklashSpeed() {
  return backlashSpeed;
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
