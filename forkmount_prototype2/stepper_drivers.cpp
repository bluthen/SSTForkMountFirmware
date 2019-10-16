#define ENCODER_OPTIMIZE_INTERRUPTS
#include <Encoder.h>
#include <Arduino.h>
#include "stepper_drivers.h"
#include "forkmount.h"

static Encoder raEnc(9, 10);
static Encoder decEnc(11, 12);
static long last_ra_ticks_in_pulse = 0;
static long last_dec_ticks_in_pulse = 0;
static long ra_ticks_in_pulse = 0;
static long dec_ticks_in_pulse = 0;
static long ra_last_encoder = 0;
static long dec_last_encoder = 0;

static float ra_v0 = 0, dec_v0 = 0;
static long ra_x0 = 0, dec_x0 = 0;
elapsedMicros ourTimer = 0;

static const int MODE_FULL = 1;
static const int MODE_SIXTEEN = 16;
static const int MODE_FORWARD = 1;
static const int MODE_BACKWARD = -1;

static const int RA_STEPPER_DIR_PIN = 2;
static const int RA_STEPPER_STEP_PIN = 3;
static const int RA_STEPPER_MS1 = 6;
static const int RA_STEPPER_MS2 = 5;
static const int RA_STEPPER_MS3 = 4;

static const int DEC_STEPPER_DIR_PIN = 22;
static const int DEC_STEPPER_STEP_PIN = 21;
static const int DEC_STEPPER_MS1 = 20;
static const int DEC_STEPPER_MS2 = 19;
static const int DEC_STEPPER_MS3 = 18;

/* local functions */

static int ra_mode_direction = 9999;
static int ra_mode_steps = 9999;
static long ra_total_steps = 0;

static int dec_mode_direction = 9999;
static int dec_mode_steps = 9999;
static long dec_total_steps = 0;

static void ra_set_step_direction(boolean forward);
static void ra_set_step_resolution(boolean full);
static void ra_step(void);
static void ra_stepper_forwardstep(void);
static void ra_stepper_backwardstep(void);
static void ra_stepper_forwardstep_fast(void);
static void ra_stepper_backwardstep_fast(void);

static void dec_set_step_direction(boolean forward);
static void dec_set_step_resolution(boolean full);
static void dec_step(void);
static void dec_stepper_forwardstep(void);
static void dec_stepper_backwardstep(void);
static void dec_stepper_forwardstep_fast(void);
static void dec_stepper_backwardstep_fast(void);
static void motion_func(float a, float v_0, long x_0, double t, float speed_wanted, long &position, float& speed);


static void ra_set_step_direction(boolean forward) {
  if(forward) {
    if(configvars_ra_direction > 0) {
      digitalWrite(RA_STEPPER_DIR_PIN, HIGH);      
    } else {
      digitalWrite(RA_STEPPER_DIR_PIN, LOW);
    }
    ra_mode_direction = MODE_FORWARD;
  } else {
    if(configvars_ra_direction > 0) {
      digitalWrite(RA_STEPPER_DIR_PIN, LOW);      
    } else {
      digitalWrite(RA_STEPPER_DIR_PIN, HIGH);      
    }
    ra_mode_direction = MODE_BACKWARD;
  }
}

void ra_set_step_resolution(boolean full) {
  if(full) {
    digitalWrite(RA_STEPPER_MS1, LOW);
    digitalWrite(RA_STEPPER_MS2, LOW);
    digitalWrite(RA_STEPPER_MS3, LOW);
    ra_mode_steps = MODE_FULL;
  } else {
    digitalWrite(RA_STEPPER_MS1, HIGH);
    digitalWrite(RA_STEPPER_MS2, HIGH);
    digitalWrite(RA_STEPPER_MS3, HIGH);
    ra_mode_steps = MODE_SIXTEEN;
  }  
}

void ra_step() {
    digitalWrite(RA_STEPPER_STEP_PIN, HIGH);
    delayMicroseconds(1);
    digitalWrite(RA_STEPPER_STEP_PIN, LOW);    
}

void ra_stepper_forwardstep() {
  if(ra_mode_steps != MODE_SIXTEEN) {
    ra_set_step_resolution(false);
  }
  if(ra_mode_direction != MODE_FORWARD) {
    ra_set_step_direction(true);
  }
  ra_step();
  ra_total_steps++;  
}

void ra_stepper_backwardstep() {
  if(ra_mode_steps != MODE_SIXTEEN) {
    ra_set_step_resolution(false);
  }
  if(ra_mode_direction != MODE_BACKWARD) {
    ra_set_step_direction(false);
  }
  ra_step();
  ra_total_steps--;
}

void ra_stepper_forwardstep_fast() {
  if(ra_mode_steps != MODE_FULL) {
    ra_set_step_resolution(true);
  }
  if(ra_mode_direction != MODE_FORWARD) {
    ra_set_step_direction(true);
  }
  ra_step();
  ra_total_steps += MICROSTEPS;
}

void ra_stepper_backwardstep_fast() {
  if(ra_mode_steps != MODE_FULL) {
    ra_set_step_resolution(true);
  }
  if(ra_mode_direction != MODE_BACKWARD) {
    ra_set_step_direction(false);
  }
  ra_step();
  ra_total_steps -= MICROSTEPS;  
}

void dec_set_step_direction(boolean forward) {
  if(forward) {
    if(configvars_dec_direction > 0) {
      digitalWrite(DEC_STEPPER_DIR_PIN, HIGH);    
    } else {
      digitalWrite(DEC_STEPPER_DIR_PIN, LOW);
    }
    dec_mode_direction = MODE_FORWARD;
  } else {
    if(configvars_dec_direction > 0) {
      digitalWrite(DEC_STEPPER_DIR_PIN, LOW);      
    } else {
      digitalWrite(DEC_STEPPER_DIR_PIN, HIGH);
    }
    dec_mode_direction = MODE_BACKWARD;
  }  
}

void dec_set_step_resolution(boolean full) {
  if(full) {
    digitalWrite(DEC_STEPPER_MS1, LOW);
    digitalWrite(DEC_STEPPER_MS2, LOW);
    digitalWrite(DEC_STEPPER_MS3, LOW);
    dec_mode_steps = MODE_FULL;
  } else {
    digitalWrite(DEC_STEPPER_MS1, HIGH);
    digitalWrite(DEC_STEPPER_MS2, HIGH);
    digitalWrite(DEC_STEPPER_MS3, HIGH);
    dec_mode_steps = MODE_SIXTEEN;
  }    
}

void dec_step() {
    digitalWrite(DEC_STEPPER_STEP_PIN, HIGH);
    delayMicroseconds(1);
    digitalWrite(DEC_STEPPER_STEP_PIN, LOW);    
}

void dec_stepper_forwardstep() {
  if(dec_mode_steps != MODE_SIXTEEN) {
    dec_set_step_resolution(false);
  }
  if(dec_mode_direction != MODE_FORWARD) {
    dec_set_step_direction(true);
  }
  dec_step();
  dec_total_steps++;  
}

void dec_stepper_backwardstep() {
  if(dec_mode_steps != MODE_SIXTEEN) {
    dec_set_step_resolution(false);
  }
  if(dec_mode_direction != MODE_BACKWARD) {
    dec_set_step_direction(false);
  }
  dec_step();
  dec_total_steps--;
}

void dec_stepper_forwardstep_fast() {
  if(dec_mode_steps != MODE_FULL) {
    dec_set_step_resolution(true);
  }
  if(dec_mode_direction != MODE_FORWARD) {
    dec_set_step_direction(true);
  }
  dec_step();
  dec_total_steps += MICROSTEPS;
}

void dec_stepper_backwardstep_fast() {
  if(dec_mode_steps != MODE_FULL) {
    dec_set_step_resolution(true);
  }
  if(dec_mode_direction != MODE_BACKWARD) {
    dec_set_step_direction(false);
  }
  dec_step();
  dec_total_steps -= MICROSTEPS;  
}

/* non-local  functions */

static volatile float RASpeed = 0.0;
static volatile float RARealSpeed = 0.0;
static volatile long RACounts = 0;
static volatile long RAPosition = 0;

static volatile float DECSpeed = 0.0;
static volatile float DECRealSpeed = 0.0;
static volatile long DECCounts = 0;
static volatile long DECPosition = 0;

volatile boolean ra_autoguiding = false;
volatile boolean dec_autoguiding = false;
volatile float prevRASpeed = 0.0;
volatile float prevDECSpeed = 0.0;


void stepperInit() {
  pinMode(RA_STEPPER_DIR_PIN, OUTPUT);
  pinMode(RA_STEPPER_STEP_PIN, OUTPUT);
  pinMode(RA_STEPPER_MS1, OUTPUT);  
  pinMode(RA_STEPPER_MS2, OUTPUT);  
  pinMode(RA_STEPPER_MS3, OUTPUT);  
  ra_set_step_resolution(false);
  ra_set_step_direction(true);
  pinMode(DEC_STEPPER_DIR_PIN, OUTPUT);
  pinMode(DEC_STEPPER_STEP_PIN, OUTPUT);
  pinMode(DEC_STEPPER_MS1, OUTPUT);  
  pinMode(DEC_STEPPER_MS2, OUTPUT);  
  pinMode(DEC_STEPPER_MS3, OUTPUT);  
  dec_set_step_resolution(false);
  dec_set_step_direction(true);
  
  ra_stepper_backwardstep();
  delay(100);
  dec_stepper_backwardstep();
  delay(100);
  ra_stepper_forwardstep();
  delay(100);
  dec_stepper_forwardstep();
  delay(100);
}


void directionUpdated() {
  // Fixes possible direction error.
  // TODO: Should we stop moving?
  ra_mode_direction = 9999;
  dec_mode_direction = 9999;
}


void setRASpeed(float speed) {
  if(fabs(speed) > configvars_ra_max_tps) {
    RASpeed = (fabs(speed)/speed) * configvars_ra_max_tps;
  } else {
    RASpeed = speed;
  }
  stepperSnapshot();
}

void stepperSnapshot() {
  ra_x0 = RAPosition;
  ra_v0 = RARealSpeed;
  
  dec_x0 = DECPosition;  
  dec_v0 = DECRealSpeed;
  ourTimer = 0;
}

float getRASpeed() {
  return RARealSpeed;
}

long getRAPosition() {
  return RAPosition;
}

long getRAEncoder() {
  return raEnc.read();
}

long getLastRAEncoder() {
  return ra_last_encoder;
}

long getRATicksInPulse() {
  return ra_ticks_in_pulse;
}

long getDECEncoder() {
  return decEnc.read();
}

long getDECTicksInPulse() {
  return dec_ticks_in_pulse;
}

long getLastDECEncoder() {
  return dec_last_encoder;
}

void setDECSpeed(float speed) {
  if(fabs(speed) > configvars_dec_max_tps) {
    DECSpeed = (fabs(speed)/speed) * configvars_dec_max_tps;
  } else {
    DECSpeed = speed;
  }
  stepperSnapshot();  
}

float getDECSpeed() {
  return DECRealSpeed;
}

long getDECPosition() {
  return DECPosition;
}

long getRALastTicksPerEncoder() {
  return last_ra_ticks_in_pulse;
}

long getDECLastTicksPerEncoder() {
  return last_dec_ticks_in_pulse;
}



elapsedMillis debugTimer = 0;
void motion_func(float a, float v_0, long x_0, double t, float speed_wanted, long &position, float& speed) {
  double t_v_max, dt_v_max;
  float v;
  long p;
  if (speed_wanted < v_0) {
    a = -a;
  }
  t_v_max = (speed_wanted - v_0) / a;
  dt_v_max = t - t_v_max;

  if (dt_v_max > 0) {
    p = (long)(0.5 * (double)a * t_v_max * t_v_max) + (long)((double)v_0 * t_v_max) + x_0;
    p += (double)speed_wanted * dt_v_max;
    v = speed_wanted;
  } else {
    v = a * t + v_0;
    p = (long)(0.5 * (double)a * t * t) + (long)((double)v_0 * t) + x_0;
  }
  position = p;
  speed = v;  
}



void runSteppers() {
  double t = ourTimer/1000000.0;
  long should_position;
  long increment = 1;
  float real_speed;
  motion_func(configvars_ra_accel_tpss, ra_v0, ra_x0, t, RASpeed, should_position, real_speed);
  RARealSpeed = real_speed;
  should_position = should_position - RAPosition;

  if (abs(real_speed) > MICROSTEP_TO_FULL_THRES) {
    increment = MICROSTEPS;
  }
  
  if (ra_last_encoder != raEnc.read()) {
    ra_last_encoder = raEnc.read();
    last_ra_ticks_in_pulse = ra_ticks_in_pulse;
    ra_ticks_in_pulse = 0;
  }
  if (should_position <= -1*increment) {
    if (increment == MICROSTEPS) {
      ra_stepper_backwardstep_fast();
    } else {
      ra_stepper_backwardstep();
    }
    RAPosition -= increment;
    ra_ticks_in_pulse -= increment;
  } else if (should_position >= increment) {
    if (increment == MICROSTEPS) {
      ra_stepper_forwardstep_fast();          
    } else {
      ra_stepper_forwardstep();    
    }
    RAPosition += increment;
    ra_ticks_in_pulse += increment;
  }

  motion_func(configvars_dec_accel_tpss, dec_v0, dec_x0, t, DECSpeed, should_position, real_speed);
  DECRealSpeed = real_speed;
  should_position = should_position - DECPosition;

  if (dec_last_encoder != decEnc.read()) {
    dec_last_encoder = decEnc.read();
    last_dec_ticks_in_pulse = dec_ticks_in_pulse;
    dec_ticks_in_pulse = 0;
  }
  if (should_position <= -1*increment) {
    if (increment == MICROSTEPS) {
      dec_stepper_backwardstep_fast();      
    } else {
      dec_stepper_backwardstep();
    }
    DECPosition -= increment;
    dec_ticks_in_pulse -= increment;
  } else if (should_position >= increment) {
    if (increment == MICROSTEPS) {
      dec_stepper_forwardstep_fast();
    } else {
      dec_stepper_forwardstep();          
    }
    DECPosition += increment;
    dec_ticks_in_pulse += increment;
  }

  // Before it has a chance to rollback lets take a snapshot.
  if (ourTimer > 3600000000) {
    stepperSnapshot();
  }
}

