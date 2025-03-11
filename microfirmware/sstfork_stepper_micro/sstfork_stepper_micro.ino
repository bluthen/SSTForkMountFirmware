#include <Wire.h>
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

static const int RA_DIR_PIN = 7;
static const int RA_STEP_PIN = 8;
static const int RA_CS_PIN = 10;
static const int RA_MISO_PIN = 16;
static const int RA_SCK_PIN = 18;
static const int RA_MOSI_PIN = 19;

static const int DEC_DIR_PIN = 14;
static const int DEC_STEP_PIN = 15;
static const int DEC_CS_PIN = 17;
static const int DEC_MISO_PIN = 16;
static const int DEC_SCK_PIN = 18;
static const int DEC_MOSI_PIN = 19;

static const int LED_PIN = 13;

const static int AUTOGUIDE_DEC_NEGY_PIN = 21;
const static int AUTOGUIDE_DEC_POSY_PIN = 22;
const static int AUTOGUIDE_RA_NEGX_PIN = 20;
const static int AUTOGUIDE_RA_POSX_PIN = 23;

bool sst_debug = false;

static Command* piCommand = NULL;
static Command* usbCommand = NULL;
IntervalTimer stepperTimer;

void autoguide_init() {
  pinMode(AUTOGUIDE_DEC_NEGY_PIN, INPUT);
  digitalWrite(AUTOGUIDE_DEC_NEGY_PIN, HIGH);
  pinMode(AUTOGUIDE_DEC_POSY_PIN, INPUT);
  digitalWrite(AUTOGUIDE_DEC_POSY_PIN, HIGH);
  pinMode(AUTOGUIDE_RA_NEGX_PIN, INPUT);
  digitalWrite(AUTOGUIDE_RA_NEGX_PIN, HIGH);
  pinMode(AUTOGUIDE_RA_POSX_PIN, INPUT);
  digitalWrite(AUTOGUIDE_RA_POSX_PIN, HIGH);
}

/**
 * When first powered up. sets up serial, sstvars, stepper, console, resets
 * tracker.
 */
void setup() {
  pinMode(DEC_CS_PIN, OUTPUT);
  digitalWrite(DEC_CS_PIN, HIGH);
  pinMode(RA_CS_PIN, OUTPUT);
  digitalWrite(RA_CS_PIN, HIGH);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);

  while (!Serial && millis() < 2000) {

  }
  digitalWrite(LED_PIN, LOW);
  if (Serial) {
    Serial.begin(115200);
    usbCommand = new Command(&Serial);
  }
  Serial1.begin(115200);
  piCommand = new Command(&Serial1);

  delay(1000);
  if (Serial) {
    DEBUG_SERIAL.println("Begin");
  }
  //SPI.begin();

  decStepper = new Stepper(DEC_DIR_PIN, DEC_STEP_PIN,
                           DEC_CS_PIN, DEC_MISO_PIN, DEC_MOSI_PIN, DEC_SCK_PIN, 
                           2, DEC_ENC_A_PIN, DEC_ENC_B_PIN, 1);
  raStepper = new Stepper(RA_DIR_PIN, RA_STEP_PIN,
                          RA_CS_PIN, RA_MISO_PIN, RA_MOSI_PIN, RA_SCK_PIN, 
                          1, RA_ENC_A_PIN, RA_ENC_B_PIN, 0);

  //raStepper->setSpeed(0.0);
  //decStepper->setSpeed(0.0);
  autoguide_init();
  stepperTimer.begin(update, 4);
  if (Serial && usbCommand != NULL) {
    Serial.print(F("StarSync Tracker Fork Mount "));
    Serial.println(sstversion);
    Serial.print("$ ");
  }
  Serial1.print(F("StarSync Tracker Fork Mount "));
  Serial1.println(sstversion);
  Serial1.print("$ ");
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

void update() {
  raStepper->update();
  decStepper->update();
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
      Serial1.print("status != prev_status and debounced: ");
      Serial1.println(status);
    }

    // Low means pressed except for rate switch

    prev_status = status;

    // If no directions are pressed we are just tracking
    if ((status & 0x0F) == 0x0F) {
      raStepper->guide(0);
      decStepper->guide(0);
      if (sst_debug) {
        Serial1.print("no buttons: ");
      }
    } else {
      if (!(status & (1 << AG_POSY_MASK))) {
        decStepper->guide(1);
        if (sst_debug) {
          Serial1.print("DEC up ");
        }
      } else if (!(status & (1 << AG_NEGY_MASK))) {
        decStepper->guide(-1);
        if (sst_debug) {
          Serial1.print("DEC down ");
        }
      } else {
        decStepper->guide(0);
      }

      if (!(status & (1 << AG_POSX_MASK))) {
        raStepper->guide(1);
        if (sst_debug) {
          Serial1.print("RA Right ");
        }

      } else if (!(status & (1 << AG_NEGX_MASK))) {
        raStepper->guide(-1);
        if (sst_debug) {
          Serial1.print("RA Left");
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
  piCommand->read();
  if (Serial) {
    if (usbCommand == NULL) {
      Serial.begin(115200);
      usbCommand = new Command(&Serial);
    }
    usbCommand->read();
  }
}
