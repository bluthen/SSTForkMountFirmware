#ifndef __STARSYNCTRACKERS_H
#define __STARSYNCTRACKERS_H

#include <stdint.h>


/** 
 * Structure that holds EEPROM values. The default values are in starsynctrackers.ino
 */
struct SSTVARS {
  float stepsPerRotation;
  float recalcIntervalS;
  float dir;
};

/**
 * Holds the firmware version.
 */
extern const char* sstversion;

/**
 * Holds values from EEPROM.
 */
extern SSTVARS sstvars;

extern boolean sst_debug;

extern float time_diff_s;
extern float sst_rate;
extern unsigned long time_solar_start_ms;
extern float time_adjust_s;
extern float time_solar_last_s; //Last solar time we recalculated steps 


/**
 * Runs when true.
 */
extern boolean keep_running;

/**
 * Inverse of tracker_calc_steps, gives you time given tracker steps.
 * @param current_steps The number of steps to use to calculate time.
 * @return time in seconds.
 */
float steps_to_time_solar(float current_steps);


/**
 * How many steps must be taken to move certain arcseconds.
 * @param asec the arcseconds to change
 * @return time in seconds
 */
float delta_asec_to_solar(float asec);


/**
 * Saves eeprom values with the contents of sstvars.
 */
void sst_save_sstvars(void);


#endif
