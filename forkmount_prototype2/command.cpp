#include "SerialCommand.h"
#include "forkmount.h"
#include "command.h"


static SerialCommand cmd;

void print_prompt() {
  WSERIAL.print(F("$ "));
}

void command_set_var() {
  char* argName;
  char* argVal;
  float value;

  argName = cmd.next();
  argVal = cmd.next();

  if (argName == NULL) {
    WSERIAL.println(F("ERROR: Missing [variable_name] argument."));
    return;
  }

  if (argVal == NULL) {
    WSERIAL.println(F("ERROR: Missing [value] argument."));
    return;
  }
  value = atof(argVal);

  if(strcmp_P(argName, F("ra_max_tps")) == 0) {
    configvars.ra_max_tps = value;
  } else if(strcmp_P(argName, F("ra_track_rate")) == 0) {
    configvars.ra_track_rate = value;
  } else if(strcmp_P(argName, F("ra_guide_rate")) == 0) {
    configvars.ra_guide_rate = value;
  } else if(strcmp_P(argName, F("ra_slew_rate")) == 0) {
    configvars.ra_slew_rate = value;
  } else if(strcmp_P(argName, F("dec_max_tps")) == 0) {
    configvars.dec_max_tps = value;
  } else if(strcmp_P(argName, F("dec_guide_rate")) == 0) {
    configvars.dec_guide_rate = value;
  } else if(strcmp_P(argName, F("dec_slew_rate")) == 0) {
    configvars.dec_slew_rate = value;
  } else {
    WSERIAL.print(F("ERROR: Invalid variable name '");
    WSERIAL.print(argName);
    WSERIAL.println("'");
  }
  print_prompt();
}

void command_status() {
  WSERIAL.print(F("ra_max_tps="));
  WSERIAL.println(configvars.ra_max_tps);
  WSERIAL.print(F("ra_track_rate="));
  WSERIAL.println(configvars.ra_track_rate);
  WSERIAL.print(F("ra_guide_rate="));
  WSERIAL.println(configvars.ra_guide_rate);
  WSERIAL.print(F("ra_slew_rate="));
  WSERIAL.println(configvars.ra_slew_rate);
  WSERIAL.print(F("dec_max_tps="));
  WSERIAL.println(configvars.dec_max_tps);
  WSERIAL.print(F("dec_guide_rate="));
  WSERIAL.println(configvars.dec_guide_rate);
  WSERIAL.print(F("dec_slew_rate="));
  WSERIAL.println(configvars.dec_slew_tps);
  WSERIAL.print(F("debug:"));
  WSERIAL.println(configvars.debug_enabled);
  WSERIAL.print(F("autoguide:"));
  WSERIAL.println(configvars.autoguide_enabled);
  WSERIAL.print(F("tracking:"));
  WSERIAL.println(configvars.tracking_enabled);
  WSERIAL.print(F("ra_speed:"));
  WSERIAL.println(getRASpeed());
  WSERIAL.print(F("dec_speed:"));
  WSERIAL.println(getDECSpeed());
  WSERIAL.print(F("ra_pos:"));
  WSERIAL.println(getRAPosition());
  WSERIAL.print(F("dec_pos:"));
  WSERIAL.println(getDECPosition());
  print_prompt();
}

void command_mv_ra() {
  
}

void command_mv_dec() {
  
}

void command_stop_tracking() {
  //What if tracking is currently happening?
  configvars.tracking_enabled = false;  
  print_prompt();
}

void command_start_tracking() {
  configvars.tracking_enabled = true;
  print_prompt();
}

void command_help() {
  WSERIAL.println(F("Commands:"));
  WSERIAL.println(F("  set_var [variable_name] [value] Sets variable");
  WSERIAL.println(F("  mv_ra [tick_position]           Moves RA to tick position"));
  WSERIAL.println(F("  mv_dec [tick_position]          Moves DEC to tick position"));
  WSERIAL.println(F("  stop_tracking                   Stops RA motor from tracking"));
  WSERIAL.println(F("  start_tracking                  Starts RA motor tracking"));
  WSERIAL.println(F("  disable_autoguide               Disables Autoguiding port input"));
  WSERIAL.println(F("  enable_autoguide                Enables Autoguiding prot input"));
  WSERIAL.println(F("  status                          Shows status/variable info"));
  WSERIAL.println(F("  help                            This help info"));
  print_prompt();
}

void command_disable_autoguide() {
  configvars.autoguide_enabled = false;
}

void command_enable_autoguide() {
  configvars.autoguide_enabled = true;  
}


void command_init(void) {
  cmd.addCommand("set_var", command_set_var);
  cmd.addCommand("mv_ra", command_mv_ra);
  cmd.addCommand("mv_dec", command_mv_dec);
  cmd.addCommand("stop_tracking", command_stop_tracking);
  cmd.addCommand("start_tracking", command_start_tracking);
  cmd.addCommand("disable_autoguide", command_disable_autoguide);
  cmd.addCommand("enable_autoguide", command_enable_autoguide);
  cmd.addCommand("status", command_status);
  cmd.addCommand("help", command_help);
  cmd.setDefaultHandler(command_help);
  print_prompt();
}

void command_read_serial() {
  cmd.readSerial();
}

