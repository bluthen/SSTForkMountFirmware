//
// Need AccelStepper fork with AFMotor support with library 
//   https://github.com/adafruit/AccelStepper

#include <AccelStepper.h>
#include <Wire.h>
#include <EEPROM.h>
#include <avr/pgmspace.h>
#include <stdint.h>

#include "forkmount.h"
#include "sst_console.h"
#include "stepper_drivers.h"

const char* sstversion = "v1.0.0";


// Default constant EEPROM values
static const uint16_t EEPROM_MAGIC = 0x0101;
static const float STEPS_PER_ROTATION = 200.0; // Steps per rotation, just steps not microsteps.
static const float GEAR_REDUCTION = 64.0;
static const float SIDEREAL_DAY_SECONDS = 0.99726958*86400;

static const float RECALC_INTERVAL_S = 15; // Time in seconds between recalculating
static const float DIRECTION = 1.0; // 1 forward is forward; -1 + is forward is backward

bool keep_running = true;
float sst_rate = 1.0;
int sst_reset_count = 0;
SSTVARS sstvars;
float time_diff_s = 0;
float time_adjust_s = 0;
float time_solar_last_s; //Last solar time we recalculated steps 

boolean sst_debug = false;

unsigned long time_solar_start_ms;  // Initial starting time.

static void sst_eeprom_init(void);
static float tracker_calc_steps(float time_solar_s);

/**
 * If the EEPROM has not be been initialized, it will init it. If it has been set it sets 
 * struct sstvars with the contents of the EEPROM.
 */
static void sst_eeprom_init() {
  //Since arduino doesn't load eeprom set with EEMEM, do our own init.
  uint16_t magic;
  EEPROM.get(0, magic);
  if (magic != EEPROM_MAGIC) {
    //Initial EEPROM
    EEPROM.put(0, EEPROM_MAGIC);
    sstvars.stepsPerRotation = STEPS_PER_ROTATION;
    sstvars.recalcIntervalS = RECALC_INTERVAL_S;
    sstvars.dir = DIRECTION;
    sst_save_sstvars();
  } else {
    //Read in from EEPROM
    EEPROM.get(sizeof(uint16_t), sstvars);
  }
}

// See starsynctrackers.h
void sst_save_sstvars() {
    EEPROM.put(sizeof(uint16_t), sstvars); 
}

/**
 * When first powered up. sets up serial, sstvars, stepper, console, resets tracker.
 */
void setup()
{  
  Serial.begin(115200);           // set up Serial library at 9600 bps
  Serial.print(F("StarSync Tracker "));
  Serial.println(sstversion);

  sst_eeprom_init();

  stepper_init();

  //while(true) {
  //  stepper_reset_lp();
  //}
  sst_console_init();

}


/**
 * Steps the tracker should be set to if ran for a time.
 * @param time_solar_s Time in seconds of run time.
 * @return Steps the tracker should be at, at time.
 */
static float tracker_calc_steps(float time_solar_s) {
  return (STEPS_PER_ROTATION*GEAR_REDUCTION*MICROSTEPS*time_solar_s/SIDEREAL_DAY_SECONDS);  
}

 // See forkmount.h
float steps_to_time_solar(float current_steps) {
  //Secant method
  //http://www.codewithc.com/c-program-for-secant-method/
  float a=millis()/1000.0;
  float b=0;
  float c= 0;
  float fa = 0;
  float fb = 0;
  do
  {
    fb = tracker_calc_steps(b) - current_steps;
    fa = tracker_calc_steps(a) - current_steps;
    c=(a*fb - b*fa)/(fb-fa);
    a = b;
    b = c;
  } while(fabs(tracker_calc_steps(c) - current_steps) > 1);
  if (sst_debug) {
    Serial.print("c =");
    Serial.println(c);
  }
  return c;
}

float delta_asec_to_solar(float asec) {
  return (360.0*60.0*60.0*asec)/SIDEREAL_DAY_SECONDS;
}


static int loop_count = 0;
/**
 * Program loop.
 */
void loop()
{
  float time_solar_s, spd, steps_wanted;
  loop_count++;

  if (time_solar_start_ms == 0) {
    time_solar_start_ms = millis();
  }
  time_solar_s = ((float)(millis() - time_solar_start_ms))/1000.0 + time_adjust_s;
  //if(loop_count > 10000) {
    //Serial.println(time_solar_s, 8);
   // loop_count = 0;
  //}
  time_diff_s = time_solar_s - time_solar_last_s;

  if (!keep_running) {
    delay(10);
  } else {  
    if (time_diff_s >= RECALC_INTERVAL_S) {
      time_solar_last_s = time_solar_s;
      if(sst_debug) {
        Serial.print(tracker_calc_steps(time_solar_s));
        Serial.print(",");
        Serial.println(sstvars.dir*Astepper1.currentPosition());
      }
      steps_wanted = tracker_calc_steps(time_solar_s + RECALC_INTERVAL_S);
      spd = (steps_wanted - sstvars.dir*Astepper1.currentPosition())/(RECALC_INTERVAL_S);
      if(spd > 500) {
        spd = 500;
      }
      Astepper1.setSpeed(sstvars.dir*spd);
      if(sst_debug) {
        Serial.println(spd);
      }
    }
    Astepper1.runSpeed();
  }
  sst_console_read_serial();
}

