#ifndef __FORKMOUNT_H
#define __FORKMOUNT_H

#include <stdint.h>

extern volatile float configvars_ra_max_tps;
extern volatile float configvars_ra_guide_rate;
extern volatile float configvars_dec_max_tps;
extern volatile float configvars_dec_guide_rate;
extern volatile float configvars_ra_accel_tpss;
extern volatile float configvars_dec_accel_tpss;
extern volatile boolean configvars_debug_enabled;
extern volatile boolean configvars_autoguide_enabled;
extern volatile int configvars_ra_direction;
extern volatile int configvars_dec_direction;
extern volatile int configvars_dec_disable;
extern volatile int configvars_ra_disable;

extern const char* fork_firmware_version;



#endif
