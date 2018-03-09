#ifndef __STEPPER_DRIVERS_H
#define __STEPPER_DRIVERS_H

#define MICROSTEPS 16
#define MICROSTEP_TO_FULL_THRES 800

extern boolean ra_autoguiding;
extern boolean dec_autoguiding;
extern float prevRASpeed;
extern float prevDECSpeed;

void stepperInit(void);

void setRASpeed(float speed);
float getRASpeed(void);
long getRAPosition(void);

void setDECSpeed(float speed);
float getDECSpeed(void);
long getDECPosition(void);

void runSteppers(void);

#endif
