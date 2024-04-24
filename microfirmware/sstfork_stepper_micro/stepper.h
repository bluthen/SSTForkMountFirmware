#ifndef __STEPPER_H
#define __STEPPER_H


#include <QuadEncoder.h>
#include "TeensyTimerTool.h"
#include <TMCStepper.h>


struct stepper_encoder_t {
  long value;
  long steps_in_pulse;
  long prev_steps_in_pulse;
};

class Stepper {
public:
  Stepper(const int _dir_pin, const int _step_pin, const int _cs_pin,
                 uint8_t enc_chan, uint16_t enc_apin, uint16_t enc_bpin);
  /**
   * Set final desired speed after acceleration in steps per second.
   * @param speed - steps per second
   */
  void setSpeed(float speed);
  float getSpeed();
  long getPosition();
  void getEncoder(stepper_encoder_t &encodervalues);
  stepper_encoder_t getEncoder();
  void setInvertedStepping(bool inverted);
  bool getInvertedStepping();
  void setSingleStepThreshold(long steps_per_sec);
  long getSingleStepThreshold();
  void enableEncoder(bool enabled);
  bool encoderEnabled();

  void setMaxAccel(float _accell_tpss);
  float getMaxAccel();
  void setMaxSpeed(float _max_tps);
  float getMaxSpeed();

  void setGuideRate(long _guideRate);
  long getGuideRate();
  void guide(int direction);
  void disableGuiding(bool disable);
  bool guidingDisabled();

  void setRunCurrent(float _run_current);
  void setMedCurrent(float _med_current);
  void setMedCurrentThreshold(float _med_current_threshold);
  void setHoldCurrent(float _hold_current);

  float getRunCurrent();
  float getMedCurrent();
  float getMedCurrentThreshold();
  float getHoldCurrent();

  bool enabled();
  void enable(bool _enabled);
  void update();

private:
  // void motion_func(float a, float v_0, long x_0, double t, float
  // speed_wanted, long &position, float& speed);
  void calcNewV(float a, float v_0, double t, float speed_wanted,
                float &new_speed);
  void setStepResolution(bool _single_step);
  void setStepDirection(bool);
  void setRealSpeed(float speed);
  void setCurrents();
  void step();
  float v0 = 0;
  float max_v0 = 0;
  volatile long x0 = 0;
  volatile bool mode_forward = true;
  volatile long last_encoder = 0;
  volatile long prev_steps_in_pulse = 0;
  volatile long steps_in_pulse = 0;
  volatile long stepResolution = 1;
  volatile bool inv_direction = false;
  volatile bool enc_enabled = false;

  long guide_rate = 0;
  int guiding = 0;
  bool guiding_enabled = true;

  bool stepper_enabled = true;
  float accell_tpss;
  float current_real = -1;
  float run_current = 0.7;
  float med_current = 0.7;
  float med_current_threshold = 0;
  float hold_current = 0.7;
  int step_pin;
  int dir_pin;
  float sp_speed = 0;
  bool stepper_stopped = true;
  long micro_threshold_v = -1;
  bool single_step = false;
  QuadEncoder *enc = NULL;
  TeensyTimerTool::PeriodicTimer *stepTimer = NULL;
  elapsedMicros timer;
  TMC5160Stepper *driver = NULL;
};

#endif