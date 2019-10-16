#ifndef __STEPPER_DRIVERS_H
#define __STEPPER_DRIVERS_H

#define MICROSTEPS 16
#define MICROSTEP_TO_FULL_THRES 4000

extern volatile boolean ra_autoguiding;
extern volatile boolean dec_autoguiding;
extern volatile float prevRASpeed;
extern volatile float prevDECSpeed;

void stepperInit(void);
void directionUpdated(void);

void setRASpeed(float speed);
float getRASpeed(void);
long getRAPosition(void);

void setDECSpeed(float speed);
float getDECSpeed(void);
long getDECPosition(void);

void stepperSnapshot(void);

long getRAEncoder(void);
long getDECEncoder(void);
long getRATicksInPulse(void);
long getDECTicksInPulse(void);
long getLastRAEncoder(void);
long getLastDECEncoder(void);

long getRALastTicksPerEncoder(void);
long getDECLastTicksPerEncoder(void);


void runSteppers(void);

#endif
