#ifndef __STEPPER_DRIVERS_H
#define __STEPPER_DRIVERS_H

// If using Adafruit v2 Motorshield requires the Adafruit_Motorshield v2 library 
//   https://github.com/adafruit/Adafruit_Motor_Shield_V2_Library

#include <Adafruit_MotorShield.h>

void stepper_init(void);

void setRASpeed(float speed);

void setDECSpeed(float speed);

void runSteppers(void);


#endif
