
// If using Adafruit v2 Motorshield requires the Adafruit_Motorshield v2 library 
//   https://github.com/adafruit/Adafruit_Motor_Shield_V2_Library

#include <Wire.h>
#include <EEPROM.h>
#include <stdint.h>
#include <inttypes.h>


#include "forkmount.h"
#include "stepper_drivers.h"

const char* sstversion = "v1.0.0";
const static float DIRECTION = -1.0;
const static float RA_HANDPAD_DIRECTION = 1.0; //To invert the RA handpad set to -1
const static float DEC_HANDPAD_DIRECTION = 1.0; //To invert the DEC handpad set to -1
const float trackingRate = DIRECTION*3.60;
const float decGuideRate = DIRECTION*0.22;

const float rateRA[] = {trackingRate, 4.0*trackingRate, 10.0*trackingRate, 100.0*trackingRate, 200.0*trackingRate};
const float rateDEC[] = {0, 4.0*decGuideRate, 10.0*decGuideRate, 100.0*decGuideRate, 200.0*decGuideRate};


//Using AVR PORT and PIN for speed
const static int PIN_BUTTON_UP = 7;
const static int PIN_BUTTON_DOWN = 6;
const static int PIN_BUTTON_LEFT = 5;
const static int PIN_BUTTON_RIGHT = 4;
const static int PIN_BUTTON_RATE = 3;

const static int PIN_LED_RATE = 2;
const static int PIN_LED_RATE2 = 8;

boolean sst_debug = false;

void handpad_init()
{
  
  pinMode(PIN_BUTTON_UP, INPUT);
  digitalWrite(PIN_BUTTON_UP, HIGH);
  pinMode(PIN_BUTTON_DOWN, INPUT);
  digitalWrite(PIN_BUTTON_DOWN, HIGH);
  pinMode(PIN_BUTTON_LEFT, INPUT);
  digitalWrite(PIN_BUTTON_LEFT, HIGH);
  pinMode(PIN_BUTTON_RIGHT, INPUT);
  digitalWrite(PIN_BUTTON_RIGHT, HIGH);
  pinMode(PIN_BUTTON_RATE, INPUT);
  digitalWrite(PIN_BUTTON_RATE, HIGH);

  //LEDs
  pinMode(PIN_LED_RATE, OUTPUT);
  digitalWrite(PIN_LED_RATE, LOW);
  pinMode(PIN_LED_RATE2, OUTPUT);
  digitalWrite(PIN_LED_RATE2, LOW);
}

/**
 * When first powered up. sets up serial, sstvars, stepper, console, resets tracker.
 */
void setup()
{  
  Serial.begin(115200);
  Serial.print(F("StarSync Tracker Fork Mount"));
  Serial.println(sstversion);

  stepper_init();

  handpad_init();
  setRASpeed(rateRA[0]);
  setDECSpeed(rateDEC[0]);

  if(sst_debug) {
    Serial.print("Speed: tracking - ");
    Serial.println(trackingRate);
  }
}


uint8_t status = 0;
uint8_t debounce_status = 255;
uint8_t prev_status = 255;
uint8_t rate_state=0;

const uint8_t MUP = 0;
const uint8_t MDOWN = 1;
const uint8_t MLEFT = 2;
const uint8_t MRIGHT = 3;
const uint8_t MRATE = 4;

unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50;

void set_leds(uint8_t rate_state) {
  digitalWrite(PIN_LED_RATE, rate_state & 1);
  digitalWrite(PIN_LED_RATE2, rate_state & 2);
}

void handpad_read_slow()
{
  status = digitalRead(PIN_BUTTON_UP) << MUP;
  status |= digitalRead(PIN_BUTTON_DOWN) << MDOWN;
  status |= digitalRead(PIN_BUTTON_LEFT) << MLEFT;
  status |= digitalRead(PIN_BUTTON_RIGHT) << MRIGHT;
  status |= digitalRead(PIN_BUTTON_RATE) << MRATE;  
}

void handpad_run()
{
  
  //handpad_read_fast();  
  handpad_read_slow();
  //If change
  if(status != debounce_status) { //TODO: Add debounce
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
    //First see if we need to adjust the rate
    if(status & (1<<MRATE)) {
      if(sst_debug) {
        Serial.println("rate adjust ");
      }
      rate_state = (rate_state+1) % 4;
      set_leds(rate_state);
    }

    // If no directions are pressed we are just tracking
    if ((status & 0x0F) == 0x0F) {
      setRASpeed(rateRA[0]);
      setDECSpeed(rateDEC[0]);
      if(sst_debug) {
        Serial.print("no buttons: ");
      }

    } else {
      if(!(status & (1 << MUP))) {
        setDECSpeed(DEC_HANDPAD_DIRECTION*rateDEC[rate_state+1]);
        if(sst_debug) {
          Serial.print("DEC up ");
        }
      } else if(!(status & (1 << MDOWN))) {
        setDECSpeed(-1.0*DEC_HANDPAD_DIRECTION*rateDEC[rate_state+1]);        
        if(sst_debug) {
          Serial.print("DEC down ");
        }
      } else {
        setDECSpeed(rateDEC[0]);      
      }
  
      if(!(status & (1 << MRIGHT))) {
        setRASpeed(RA_HANDPAD_DIRECTION*rateRA[rate_state+1]);        
        if(sst_debug) {
          Serial.print("RA Right ");
        }

      } else if(!(status & (1 << MLEFT))) {
        setRASpeed(-1.0*RA_HANDPAD_DIRECTION*rateRA[rate_state+1]);
        if(sst_debug) {
          Serial.print("RA Left");
        }
      } else {
        setRASpeed(rateRA[0]);      
      }
    }
  }
}


/**
 * Program loop.
 */
void loop()
{

  handpad_run();
  runSteppers();
}

