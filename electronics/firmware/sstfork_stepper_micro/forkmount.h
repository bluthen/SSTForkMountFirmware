#ifndef __FORKMOUNT_H
#define __FORKMOUNT_H

#include <stdint.h>
#include "stepper.h"
#define DEBUG_SERIAL if(sst_debug && Serial)Serial


extern bool sst_debug;

extern const char *fork_firmware_version;
extern Stepper *raStepper;
extern Stepper *decStepper;
extern bool ra_autoguiding;
extern bool dec_autoguiding;

extern float prevRASpeed;
extern float prevDECSpeed;



#endif
