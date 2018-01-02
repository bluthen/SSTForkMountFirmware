#ifndef __FORKMOUNT_H
#define __FORKMOUNT_H

#include <stdint.h>

struct CONFIGVARS {
  float ra_max_tps;
  float ra_guide_rate;
  float dec_max_tps;
  float dec_guide_rate;
  boolean debug_enabled;
  boolean autoguide_enabled;
  int ra_direction;
  int dec_direction;
};

extern boolean ra_autoguiding;
extern boolean dec_autoguiding;

extern const char* fork_firmware_version;

extern CONFIGVARS configvars;


#endif
