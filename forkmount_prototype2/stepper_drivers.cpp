#include <Arduino.h>
#include "stepper_drivers.h"

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


static void ra_set_step_direction(boolean forward) {
  if(forward) {
    digitalWrite(RA_STEPPER_DIR_PIN, HIGH);
    ra_mode_direction = MODE_FORWARD;
  } else {
    digitalWrite(RA_STEPPER_DIR_PIN, LOW);
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
    digitalWrite(DEC_STEPPER_DIR_PIN, HIGH);
    dec_mode_direction = MODE_FORWARD;
  } else {
    digitalWrite(DEC_STEPPER_DIR_PIN, LOW);
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

static float RASpeed = 0.0;
static long RACounts = 0;
static unsigned long RAClock = 0;
static long RAPosition = 0;

static float DECSpeed = 0.0;
static long DECCounts = 0;
static unsigned long DECClock = 0;
static long DECPosition = 0;

static float count;

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
  ra_stepper_forwardstep();
  dec_stepper_forwardstep();
}

void setRASpeed(float speed) {
  RASpeed = speed;
  RACounts = 0;
  RAClock = millis();  
}

void getRASpeed() {
  return RASpeed;
}

long getRAPosition() {
  return RAPosition;
}

void setDECSpeed(float speed) {
  DECSpeed = speed;
  DECCounts = 0;
  DECClock = millis();
  
}

void getDECSpeed() {
  return DECSpeed();
}

long getDECPosition() {
  return DECPosition;
}

void runSteppers() {
  count = RACounts - (RASpeed*((float)(millis() - RAClock))/1000.0);
  //Serial.println(RASpeed);
  //Serial.println(RAClock);
  //Serial.println(RACounts);
  //Serial.println(count);
  if(abs(RASpeed) > 150.0) {
    if (count < -MICROSTEPS) {
        ra_stepper_backwardstep_fast();
        RACounts += MICROSTEPS;
        RAPosition += MICROSTEPS;
    } else if (count > MICROSTEPS) {
        ra_stepper_forwardstep_fast();    
        RACounts -= MICROSTEPS;
        RAPosition -= MICROSTEPS;
    }    
  } else {
    if (count < -1.0) {
        ra_stepper_backwardstep();
        RACounts++;
        RAPosition++;
    } else if (count > 1.0) {
        ra_stepper_forwardstep();    
        RACounts--;
        RAPosition--;
    }
  }

  count = DECCounts - (DECSpeed*((float)(millis() - DECClock))/1000.0);

  if(abs(DECSpeed) > 150.0) {
    if (count < -MICROSTEPS) {
      dec_stepper_backwardstep_fast();
      DECCounts+=MICROSTEPS;
      DECPosition+=MICROSTEPS;
    } else if (count > MICROSTEPS) {
      dec_stepper_forwardstep_fast();    
      DECCounts-=MICROSTEPS;
      DECPosition-=MICROSTEPS;
    }    
  } else {
    if (count < -1.0) {
      dec_stepper_backwardstep();
      DECCounts++;
      DECPosition++;
    } else if (count > 1.0) {
      dec_stepper_forwardstep();    
      DECCounts--;
      DECPosition--;
    }
  }
}
