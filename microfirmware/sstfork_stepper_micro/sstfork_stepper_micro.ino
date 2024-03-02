#define THROW_ERROR_IF_NOT_FAST
#include <Wire.h>
#include <digitalWriteFast.h>
#include <inttypes.h>
#include <stdint.h>

#include "command.h"
#include "forkmount.h"
#include "stepper.h"

const char *sstversion = "v1.1.0";
Stepper *raStepper = NULL;
Stepper *decStepper = NULL;


static const int RA_ENC_A_PIN = 5;
static const int RA_ENC_B_PIN = 3;
static const int DEC_ENC_A_PIN = 2;
static const int DEC_ENC_B_PIN = 4;

static const int RA_STEPPER_DIR_PIN = 10;
static const int RA_STEPPER_STEP_PIN = 9;
static const int RA_STEPPER_MS1 = 6;
static const int RA_STEPPER_MS2 = 7;
static const int RA_STEPPER_MS3 = 8;

static const int DEC_STEPPER_DIR_PIN = 22;
static const int DEC_STEPPER_STEP_PIN = 21;
static const int DEC_STEPPER_MS1 = 20;
static const int DEC_STEPPER_MS2 = 19;
static const int DEC_STEPPER_MS3 = 18;

const static int AUTOGUIDE_DEC_NEGY_PIN = 15;
const static int AUTOGUIDE_DEC_POSY_PIN = 14;
const static int AUTOGUIDE_RA_NEGX_PIN = 11;
const static int AUTOGUIDE_RA_POSX_PIN = 12;

bool sst_debug = false;

void autoguide_init() {
  pinModeFast(AUTOGUIDE_DEC_NEGY_PIN, INPUT);
  digitalWriteFast(AUTOGUIDE_DEC_NEGY_PIN, HIGH);
  pinModeFast(AUTOGUIDE_DEC_POSY_PIN, INPUT);
  digitalWriteFast(AUTOGUIDE_DEC_POSY_PIN, HIGH);
  pinModeFast(AUTOGUIDE_RA_NEGX_PIN, INPUT);
  digitalWriteFast(AUTOGUIDE_RA_NEGX_PIN, HIGH);
  pinModeFast(AUTOGUIDE_RA_POSX_PIN, INPUT);
  digitalWriteFast(AUTOGUIDE_RA_POSX_PIN, HIGH);
}

void configVarsInit() {
  // Some dumb initial values
  raStepper->setMaxSpeed(12000);
  raStepper->setGuideRate(20);
  decStepper->setMaxSpeed(12000);
  decStepper->setGuideRate(6);
  raStepper->setMaxAccel(10000);
  decStepper->setMaxAccel(10000);
  raStepper->disableGuiding(false);
  decStepper->disableGuiding(false);
  raStepper->setInvertedStepping(false);
  decStepper->setInvertedStepping(false);
  raStepper->enable(true);
  decStepper->enable(true);
}

/**
 * When first powered up. sets up serial, sstvars, stepper, console, resets
 * tracker.
 */
void setup() {
  Serial.begin(115200);

  configVarsInit();
  raStepper = new Stepper(RA_STEPPER_DIR_PIN, RA_STEPPER_STEP_PIN,
                          RA_STEPPER_MS1, RA_STEPPER_MS2, RA_STEPPER_MS3, 1,
                          RA_ENC_A_PIN, RA_ENC_B_PIN);
  decStepper = new Stepper(DEC_STEPPER_DIR_PIN, DEC_STEPPER_STEP_PIN,
                           DEC_STEPPER_MS1, DEC_STEPPER_MS2, DEC_STEPPER_MS3, 2,
                           DEC_ENC_A_PIN, DEC_ENC_B_PIN);
  raStepper->setSpeed(0.0);
  decStepper->setSpeed(0.0);
  autoguide_init();
  command_init();
  Serial.print(F("StarSync Tracker Fork Mount "));
  Serial.println(sstversion);
}

uint8_t status = 0;
uint8_t debounce_status = 255;
uint8_t prev_status = 255;
uint8_t rate_state = 0;

const uint8_t AG_POSY_MASK = 0;
const uint8_t AG_NEGY_MASK = 1;
const uint8_t AG_NEGX_MASK = 2;
const uint8_t AG_POSX_MASK = 3;

unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50;

void autoguide_read() {
  status = digitalRead(AUTOGUIDE_DEC_POSY_PIN) << AG_POSY_MASK;
  status |= digitalRead(AUTOGUIDE_DEC_NEGY_PIN) << AG_NEGY_MASK;
  status |= digitalRead(AUTOGUIDE_RA_NEGX_PIN) << AG_NEGX_MASK;
  status |= digitalRead(AUTOGUIDE_RA_POSX_PIN) << AG_POSX_MASK;
}

void autoguide_run() {
  if (raStepper->guidingDisabled() && decStepper->guidingDisabled()) {
    return;
  }

  autoguide_read();
  // If change
  if (status != debounce_status) {
    debounce_status = status;
    lastDebounceTime = millis();
  }

  if (status != prev_status && (millis() - lastDebounceTime) > debounceDelay) {
    if (sst_debug) {
      Serial.print("status != prev_status and debounced: ");
      Serial.println(status);
    }

    // Low means pressed except for rate switch

    prev_status = status;

    // If no directions are pressed we are just tracking
    if ((status & 0x0F) == 0x0F) {
      raStepper->guide(0);
      decStepper->guide(0);
      if (sst_debug) {
        Serial.print("no buttons: ");
      }
    } else {
      if (!(status & (1 << AG_POSY_MASK))) {
        decStepper->guide(1);
        if (sst_debug) {
          Serial.print("DEC up ");
        }
      } else if (!(status & (1 << AG_NEGY_MASK))) {
        decStepper->guide(-1);
        if (sst_debug) {
          Serial.print("DEC down ");
        }
      } else {
        decStepper->guide(0);
      }

      if (!(status & (1 << AG_POSX_MASK))) {
        raStepper->guide(1);
        if (sst_debug) {
          Serial.print("RA Right ");
        }

      } else if (!(status & (1 << AG_NEGX_MASK))) {
        raStepper->guide(-1);
        if (sst_debug) {
          Serial.print("RA Left");
        }
      } else {
        raStepper->guide(0);
      }
    }
  }
}

/**
 * Program loop.
 */
void loop() {
  // Serial.println("Loop");
  autoguide_run();
  command_read_serial();
  raStepper->update();
  decStepper->update();
}
