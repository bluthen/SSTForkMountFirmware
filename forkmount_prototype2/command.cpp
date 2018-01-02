#include <pgmspace.h>

#include "SerialCommand.h"
#include "forkmount.h"
#include "command.h"
#include "stepper_drivers.h"


static SerialCommand cmd;

void print_prompt() {
  WSERIAL.print("$ ");
}

void command_set_var() {
  char* argName;
  char* argVal;
  float value;

  argName = cmd.next();
  argVal = cmd.next();

  if (argName == NULL) {
    WSERIAL.println("ERROR: Missing [variable_name] argument.");
    return;
  }

  if (argVal == NULL) {
    WSERIAL.println("ERROR: Missing [value] argument.");
    return;
  }
  value = atof(argVal);

  if(strcmp(argName, "ra_max_tps") == 0) {
    configvars.ra_max_tps = value;
  } else if(strcmp(argName, "ra_guide_rate") == 0) {
    configvars.ra_guide_rate = value;
  } else if(strcmp(argName, "ra_direction") == 0) {
    configvars.ra_direction = (int)value;
  } else if(strcmp(argName, "dec_max_tps") == 0) {
    configvars.dec_max_tps = value;
  } else if(strcmp(argName, "dec_guide_rate") == 0) {
    configvars.dec_guide_rate = value;
  } else if(strcmp(argName, "dec_direction") == 0) {
    configvars.dec_direction = (int)value;
  } else {
    WSERIAL.print("ERROR: Invalid variable name '");
    WSERIAL.print(argName);
    WSERIAL.println("'");
  }
  print_prompt();
}


void command_qs() {
  //TODO: Maybe make binary status so we don't get close to tracking tick interval?
  WSERIAL.print("rs:");
  WSERIAL.println(getRASpeed());
  WSERIAL.print("ds:");
  WSERIAL.println(getDECSpeed());
  WSERIAL.print("rp:");
  WSERIAL.println(getRAPosition());
  WSERIAL.print("dp:");
  WSERIAL.println(getDECPosition());
  print_prompt();  
}

void command_status() {
  WSERIAL.print("ra_max_tps=");
  WSERIAL.println(configvars.ra_max_tps);
  WSERIAL.print("ra_guide_rate=");
  WSERIAL.println(configvars.ra_guide_rate);
  WSERIAL.print("ra_direction=");
  WSERIAL.println(configvars.ra_direction);
  WSERIAL.print("dec_max_tps=");
  WSERIAL.println(configvars.dec_max_tps);
  WSERIAL.print("dec_guide_rate=");
  WSERIAL.println(configvars.dec_guide_rate);
  WSERIAL.print("dec_direction=");
  WSERIAL.println(configvars.dec_direction);
  WSERIAL.print("debug:");
  WSERIAL.println(configvars.debug_enabled);
  WSERIAL.print("autoguide:");
  WSERIAL.println(configvars.autoguide_enabled);
  WSERIAL.print("ra_speed:");
  WSERIAL.println(getRASpeed());
  WSERIAL.print("dec_speed:");
  WSERIAL.println(getDECSpeed());
  WSERIAL.print("ra_pos:");
  WSERIAL.println(getRAPosition());
  WSERIAL.print("dec_pos:");
  WSERIAL.println(getDECPosition());
  print_prompt();
}

void command_ra_set_speed() {
  char* argVal;
  float value;

  argVal = cmd.next();

  if (argVal == NULL) {
    WSERIAL.println("ERROR: Missing [value] argument.");
    return;
  }
  value = atof(argVal);
  setRASpeed(value);
  WSERIAL.print("ra_speed:");
  WSERIAL.println(getRASpeed());  
  print_prompt();
}

void command_dec_set_speed() {
  char* argVal;
  float value;

  argVal = cmd.next();

  if (argVal == NULL) {
    WSERIAL.println("ERROR: Missing [value] argument.");
    return;
  }
  value = atof(argVal);
  setDECSpeed(value);
  WSERIAL.print("dec_speed:");
  WSERIAL.println(getDECSpeed());
  print_prompt();
}


void command_help(const char* cmd) {
  WSERIAL.println("Commands:");
  WSERIAL.println("  set_var [variable_name] [value] Sets variable");
  WSERIAL.println("  ra_set_speed [tps]           Moves RA to tick position");
  WSERIAL.println("  dec_set_speed [tps]          Moves DEC to tick position");
  WSERIAL.println("  autoguide_disable            Disables Autoguiding port input");
  WSERIAL.println("  autoguide_enable             Enables Autoguiding prot input");
  WSERIAL.println("  status                       Shows status/variable info");
  WSERIAL.println("  qs                           Shows speed/position info");
  WSERIAL.println("  help                         This help info");
  print_prompt();
}

void command_autoguide_disable() {
  configvars.autoguide_enabled = false;
}

void command_autoguide_enable() {
  configvars.autoguide_enabled = true;  
}


void command_init(void) {
  WSERIAL.begin(115200);
  cmd.addCommand("set_var", command_set_var);
  cmd.addCommand("ra_set_speed", command_ra_set_speed);
  cmd.addCommand("dec_set_speed", command_dec_set_speed);
  cmd.addCommand("autoguide_disable", command_autoguide_disable);
  cmd.addCommand("autoguide_disable", command_autoguide_enable);
  cmd.addCommand("status", command_status);
  cmd.addCommand("qs", command_qs);
  cmd.setDefaultHandler(command_help);
  print_prompt();
}

void command_read_serial() {
  cmd.readSerial();
}

