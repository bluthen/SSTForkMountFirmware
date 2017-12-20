
#include <Wire.h>
#include <EEPROM.h>
#include <stdint.h>
#include <inttypes.h>


#include "forkmount.h"
#include "stepper_drivers.h"
#include "command.h"

const char* sstversion = "v1.0.0";
const static float DIRECTION = 1.0;
const float raTrackingRate = DIRECTION * 5.20;
//const float raTrackingRate = 12000; //@12V 2:09 
const float raGuideRate = 4 * raTrackingRate;
const float decGuideRate = DIRECTION * 0.22;

const static int AUTOGUIDE_DEC_NEGY_PIN = 17;
const static int AUTOGUIDE_DEC_POSY_PIN = 16;
const static int AUTOGUIDE_RA_NEGX_PIN = 7;
const static int AUTOGUIDE_RA_POSX_PIN = 8;

boolean sst_debug = false;
boolean autoguide_enabled = true;

void autoguide_init()
{
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
 * When first powered up. sets up serial, sstvars, stepper, console, resets tracker.
 */
void setup()
{  
  Serial.begin(115200);
  Serial.print(F("StarSync Tracker Fork Mount"));
  Serial.println(sstversion);

  stepperInit();

  autoguide_init();
  setRASpeed(raTrackingRate);
  setDECSpeed(0.0);


  if(sst_debug) {
    Serial.print("Speed: tracking - ");
    Serial.println(raTrackingRate);
  }
}


uint8_t status = 0;
uint8_t debounce_status = 255;
uint8_t prev_status = 255;
uint8_t rate_state=0;

const uint8_t AG_POSY_MASK = 0;
const uint8_t AG_NEGY_MASK = 1;
const uint8_t AG_NEGX_MASK = 2;
const uint8_t AG_POSX_MASK = 3;

unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50;

void autoguide_read()
{
  status = digitalRead(AUTOGUIDE_DEC_POSY_PIN) << AG_POSY_MASK;
  status |= digitalRead(AUTOGUIDE_DEC_NEGY_PIN) << AG_NEGY_MASK;
  status |= digitalRead(AUTOGUIDE_RA_NEGX_PIN) << AG_NEGX_MASK;
  status |= digitalRead(AUTOGUIDE_RA_POSX_PIN) << AG_POSX_MASK;
}

void autoguide_run()
{
  if(!configvars.autoguide_enabled) {
    return;
  }
  
  autoguide_read();
  //If change
  if(status != debounce_status) {
    debounce_status = status;
    lastDebounceTime = millis();
  }
  
  if (status != prev_status && (millis() - lastDebounceTime) > debounceDelay) {
    if(sst_debug) {
      Serial.print("status != prev_status and debounced: ");
      Serial.println(status);
    }

    // Low means pressed except for rate switch
    
    prev_status = status;

    // If no directions are pressed we are just tracking
    if ((status & 0x0F) == 0x0F) {
      setRASpeed(raTrackingRate);
      setDECSpeed(0.0);
      if(sst_debug) {
        Serial.print("no buttons: ");
      }

    } else {
      if(!(status & (1 << AG_POSY_MASK))) {
        setDECSpeed(decGuideRate);
        if(sst_debug) {
          Serial.print("DEC up ");
        }
      } else if(!(status & (1 << AG_NEGY_MASK))) {
        setDECSpeed(-1.0 * decGuideRate);        
        if(sst_debug) {
          Serial.print("DEC down ");
        }
      } else {
        setDECSpeed(0.0);      
      }
  
      if(!(status & (1 << AG_POSX_MASK))) {
        setRASpeed(raGuideRate);        
        if(sst_debug) {
          Serial.print("RA Right ");
        }

      } else if(!(status & (1 << AG_NEGX_MASK))) {
        setRASpeed(-1.0*raGuideRate);
        if(sst_debug) {
          Serial.print("RA Left");
        }
      } else {
        setRASpeed(raTrackingRate);      
      }
    }
  }
}


/**
 * Program loop.
 */
void loop()
{
  //Serial.println("Loop");
  autoguide_run();
  command_read_serial();
  runSteppers();
}

