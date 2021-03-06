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
  int oldv;

  argName = cmd.next();
  argVal = cmd.next();

  if (argName == NULL) {
    WSERIAL.println("ERROR: Missing [variable_name] argument.");
    print_prompt();
    return;
  }

  if (argVal == NULL) {
    WSERIAL.println("ERROR: Missing [value] argument.");
    print_prompt();
    return;
  }
  value = atof(argVal);

  if(strcmp(argName, "ra_max_tps") == 0) {
    configvars_ra_max_tps = value;
  } else if(strcmp(argName, "ra_guide_rate") == 0) {
    configvars_ra_guide_rate = value;
  } else if(strcmp(argName, "ra_direction") == 0) {
    oldv = configvars_ra_direction;
    configvars_ra_direction = (int)value;
    if (oldv != configvars_ra_direction) {
      directionUpdated();
    }
  } else if(strcmp(argName, "dec_max_tps") == 0) {
    configvars_dec_max_tps = value;
  } else if(strcmp(argName, "dec_guide_rate") == 0) {
    configvars_dec_guide_rate = value;
  } else if(strcmp(argName, "dec_direction") == 0) {
    oldv = configvars_dec_direction;
    configvars_dec_direction = (int)value;
    if (oldv != configvars_dec_direction) {
      directionUpdated();
    }
  } else if(strcmp(argName, "dec_disable") == 0) {
    configvars_dec_disable = (int)value;
  } else if(strcmp(argName, "ra_disable") == 0) {
    configvars_ra_disable = (int)value;
  } else if(strcmp(argName, "ra_accel_tpss") == 0) {
    configvars_ra_accel_tpss = value;
    stepperSnapshot();
  } else if(strcmp(argName, "dec_accel_tpss") == 0) {
    configvars_dec_accel_tpss = value;
    stepperSnapshot();
  } else {
    WSERIAL.print("ERROR: Invalid variable name '");
    WSERIAL.print(argName);
    WSERIAL.println("'");
  }
  print_prompt();
}


void command_qs() {
  long raPos, decPos, raEnc, decEnc, raTip, decTip, raltpe, decltpe;
  //TODO: Maybe make binary status so we don't get close to tracking tick interval?
  WSERIAL.print("rs:");
  WSERIAL.println(getRASpeed());
  WSERIAL.print("ds:");
  WSERIAL.println(getDECSpeed());
  raPos = getRAPosition();
  decPos = getDECPosition();
  raEnc = getRAEncoder();
  decEnc = getDECEncoder();
  raltpe = getRALastTicksPerEncoder();
  decltpe = getDECLastTicksPerEncoder();
  if (getLastRAEncoder() != raEnc) {
    raTip = 0;
  } else {
    raTip = getRATicksInPulse();
  }
  if (getLastDECEncoder() != decEnc) {
    decTip = 0;
  } else {
    decTip = getDECTicksInPulse();
  }
  WSERIAL.print("rp:");
  WSERIAL.println(raPos);
  WSERIAL.print("dp:");
  WSERIAL.println(decPos);
  WSERIAL.print("re:");
  WSERIAL.println(raEnc);
  WSERIAL.print("de:");
  WSERIAL.println(decEnc);
  WSERIAL.print("ri:");
  WSERIAL.println(raTip);
  WSERIAL.print("di:");
  WSERIAL.println(decTip);
  WSERIAL.print("rl:");
  WSERIAL.println(raltpe);
  WSERIAL.print("dl:");
  WSERIAL.println(decltpe);
  print_prompt();  
}

void command_status() {
  long raPos, decPos, raEnc, decEnc, raTip, decTip;
  WSERIAL.print("ra_max_tps=");
  WSERIAL.println(configvars_ra_max_tps);
  WSERIAL.print("ra_guide_rate=");
  WSERIAL.println(configvars_ra_guide_rate);
  WSERIAL.print("ra_direction=");
  WSERIAL.println(configvars_ra_direction);
  WSERIAL.print("ra_disable=");
  WSERIAL.println(configvars_ra_disable);
  WSERIAL.print("ra_accel_tpss=");
  WSERIAL.println(configvars_ra_accel_tpss);
  WSERIAL.print("dec_max_tps=");
  WSERIAL.println(configvars_dec_max_tps);
  WSERIAL.print("dec_guide_rate=");
  WSERIAL.println(configvars_dec_guide_rate);
  WSERIAL.print("dec_direction=");
  WSERIAL.println(configvars_dec_direction);
  WSERIAL.print("dec_disable=");
  WSERIAL.println(configvars_dec_disable);
  WSERIAL.print("dec_accel_tpss=");
  WSERIAL.println(configvars_dec_accel_tpss);
  WSERIAL.print("debug:");
  WSERIAL.println(configvars_debug_enabled);
  WSERIAL.print("autoguide:");
  WSERIAL.println(configvars_autoguide_enabled);
  WSERIAL.print("ra_speed:");
  WSERIAL.println(getRASpeed());
  WSERIAL.print("dec_speed:");
  WSERIAL.println(getDECSpeed());
  WSERIAL.print("ra_tpe:");
  WSERIAL.println(getRALastTicksPerEncoder());
  WSERIAL.print("dec_tpe:");
  WSERIAL.println(getDECLastTicksPerEncoder());


  raPos = getRAPosition();
  decPos = getDECPosition();
  raEnc = getRAEncoder();
  decEnc = getDECEncoder();
  if (getLastRAEncoder() != raEnc) {
    raTip = 0;
  } else {
    raTip = getRATicksInPulse();
  }
  if (getLastDECEncoder() != decEnc) {
    decTip = 0;
  } else {
    decTip = getDECTicksInPulse();
  }
  
  WSERIAL.print("ra_pos:");
  WSERIAL.println(raPos);
  WSERIAL.print("dec_pos:");
  WSERIAL.println(decPos);
  WSERIAL.print("ra_enc:");
  WSERIAL.println(raEnc);
  WSERIAL.print("dec_enc:");
  WSERIAL.println(decEnc);
  WSERIAL.print("ra_tip:");
  WSERIAL.println(raTip);
  WSERIAL.print("dec_tip:");
  WSERIAL.println(decTip);  
  print_prompt();
}

void command_ra_set_speed() {
  char* argVal;
  float value;

  argVal = cmd.next();

  if (argVal == NULL) {
    WSERIAL.println("ERROR: Missing [value] argument.");
    print_prompt();
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
    print_prompt();
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
  configvars_autoguide_enabled = false;
  if (ra_autoguiding) {
    setRASpeed(prevRASpeed);
    ra_autoguiding = false;
    prevRASpeed = 0.0;
  }
  if (dec_autoguiding) {
    setDECSpeed(prevDECSpeed);
    dec_autoguiding = false;
    prevDECSpeed = 0.0;
  }
  print_prompt();
}

void command_autoguide_enable() {
  configvars_autoguide_enabled = true;
  print_prompt();
}


void command_init(void) {
  WSERIAL.begin(115200);
  cmd.addCommand("set_var", command_set_var);
  cmd.addCommand("ra_set_speed", command_ra_set_speed);
  cmd.addCommand("dec_set_speed", command_dec_set_speed);
  cmd.addCommand("autoguide_disable", command_autoguide_disable);
  cmd.addCommand("autoguide_enable", command_autoguide_enable);
  cmd.addCommand("status", command_status);
  cmd.addCommand("qs", command_qs);
  cmd.setDefaultHandler(command_help);
  print_prompt();
}

void command_read_serial() {
  cmd.readSerial();
}
