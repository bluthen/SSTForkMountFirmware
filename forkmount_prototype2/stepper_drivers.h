#ifndef __STEPPER_DRIVERS_H
#define __STEPPER_DRIVERS_H

#define MICROSTEPS 16
#define MICROSTEP_TO_FULL_THRES 800
void stepperInit(void);

void setRASpeed(float speed);
float getRASpeed(void);
long getRAPosition(void);

void setDECSpeed(float speed);
float getDECSpeed(void);
long getDECPosition(void);

void runSteppers(void);


#endif
