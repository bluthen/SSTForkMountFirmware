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
void setRAMaxAccel(float accel);
void setRAMaxSpeed(float maxSpeed);
float getRASpeed(void);
long getRAPosition(void);

void setDECSpeed(float speed);
void setDECMaxAccel(float accel);
void setDECMaxSpeed(float maxSpeed);
float getDECSpeed(void);
long getDECPosition(void);

long getRAEncoder(void);
long getDECEncoder(void);
long getRATicksInPulse(void);
long getDECTicksInPulse(void);
long getLastRAEncoder(void);
long getLastDECEncoder(void);

void runSteppers(void);

#endif
