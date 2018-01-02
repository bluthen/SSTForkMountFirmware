#ifndef __FORKMOUNT_H
#define __FORKMOUNT_H

#include <stdint.h>

struct CONFIGVARS {
  float ra_max_tps;
  float ra_track_rate;
  float ra_guide_rate;
  float ra_slew_rate;
  float dec_max_tps;
  float dec_guide_rate;
  float dec_slew_rate;
  boolean debug_enabled;
  boolean autoguide_enabled;
  boolean tracking_enabled;
};

extern const char* fork_firmware_version;

extern CONFIGVARS configvars;


#endif