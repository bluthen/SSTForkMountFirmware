#define ENCODER_OPTIMIZE_INTERRUPTS
#include <Encoder.h>
#include <Arduino.h>
#include <AccelStepper.h>
#include "stepper_drivers.h"
#include "forkmount.h"

static Encoder raEnc(9, 10);
static Encoder decEnc(11, 12);
static long ra_ticks_in_pulse = 0;
static long dec_ticks_in_pulse = 0;
static long ra_last_encoder = 0;
static long dec_last_encoder = 0;

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

AccelStepper raStepper(1, RA_STEPPER_STEP_PIN, RA_STEPPER_DIR_PIN);
AccelStepper decStepper(1, DEC_STEPPER_STEP_PIN, DEC_STEPPER_DIR_PIN);

/* local functions */

static int ra_mode_steps = 9999;
static int dec_mode_steps = 9999;

static void ra_set_step_resolution(boolean full);
static void dec_set_step_resolution(boolean full);

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

boolean ra_autoguiding = false;
boolean dec_autoguiding = false;
float prevRASpeed = 0.0;
float prevDECSpeed = 0.0;


void stepperInit() {
  pinMode(RA_STEPPER_DIR_PIN, OUTPUT);
  pinMode(RA_STEPPER_STEP_PIN, OUTPUT);
  pinMode(RA_STEPPER_MS1, OUTPUT);  
  pinMode(RA_STEPPER_MS2, OUTPUT);  
  pinMode(RA_STEPPER_MS3, OUTPUT);  
  ra_set_step_resolution(false);
  pinMode(DEC_STEPPER_DIR_PIN, OUTPUT);
  pinMode(DEC_STEPPER_STEP_PIN, OUTPUT);
  pinMode(DEC_STEPPER_MS1, OUTPUT);  
  pinMode(DEC_STEPPER_MS2, OUTPUT);  
  pinMode(DEC_STEPPER_MS3, OUTPUT);  
  dec_set_step_resolution(false);

  raStepper.setSpeed(0.0);
  decStepper.setSpeed(0.0);
}

void setRASpeed(float speed) {
  raStepper.setSpeed(speed);
}

void setRAMaxAccel(float accel) {
  raStepper.setAcceleration(accel);
}

void setRAMaxSpeed(float maxSpeed) {
  raStepper.setMaxSpeed(maxSpeed);
}

float getRASpeed() {
  return raStepper.speed();
}

long getRAPosition() {
  return raStepper.currentPosition();
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
  decStepper.setSpeed(speed);  
}

void setDECMaxAccel(float accel) {
  decStepper.setAcceleration(accel);
}

void setDECMaxSpeed(float maxSpeed) {
  decStepper.setMaxSpeed(maxSpeed);
}

float getDECSpeed() {
  return decStepper.speed();
}

long getDECPosition() {
  return decStepper.currentPosition();
}


void runSteppers() {
  raStepper.runSpeed();
  if (ra_last_encoder != raEnc.read()) {
    ra_last_encoder = raEnc.read();
    ra_ticks_in_pulse = raStepper.currentPosition();
  }
  decStepper.runSpeed();
  if (dec_last_encoder != decEnc.read()) {
    dec_last_encoder = decEnc.read();
    dec_ticks_in_pulse = decStepper.runSpeed();
  }
}

