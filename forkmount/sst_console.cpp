#include <avr/pgmspace.h>
#include "SerialCommand.h"
#include "sst_console.h"
#include "stepper_drivers.h"
#include "forkmount.h"

static SerialCommand sSSTCmd;

void sst_console_stop() {
  //TODO: Set it to stop
  keep_running = false;
  Serial.println(F("Tracking stopped"));
  if(sst_debug) {
    Serial.println(sstvars.dir*Astepper1.currentPosition());
    Serial.println(((float)(millis() - time_solar_start_ms))/1000.0);
    Serial.println(steps_to_time_solar(sstvars.dir*Astepper1.currentPosition()));
  }
  Serial.print(F("$ "));
}

void sst_console_continue() {
  Serial.println(F("Tracking continuing"));
  keep_running = true;
  time_adjust_s = steps_to_time_solar(sstvars.dir*Astepper1.currentPosition()) - ((float)(millis() - time_solar_start_ms))/1000.0;
  time_solar_last_s = -9999;
  if (sst_debug) {
    Serial.println(time_adjust_s);
  }
  Serial.print(F("$ "));
}

void sst_console_mv() {
  char* argL;
  double l;
  double cl;
  char* argUnit;
  char* argRate;
  argL = sSSTCmd.next();
  argUnit = sSSTCmd.next();

  if(!keep_running) {
    Serial.println(F("ERROR: Can't move if not running. Do 'continue' first."));
    return;
  }

  if (argL == NULL) {
    Serial.println(F("ERROR: Missing length to move."));
    return;
  }
  //TODO: See what max and min are.
  l = atof(argL);
  if (argUnit != NULL && strcmp(argUnit, "arcseconds") != 0) {
    Serial.println(F("ERROR: Invalid move unit"));
  } else {
    argUnit = "arcseconds";
  }

  Serial.print(F("Moving "));
  Serial.print(l);
  Serial.print(" ");
  Serial.println(argUnit);

  time_adjust_s = delta_asec_to_solar(cl) - ((float)(millis() - time_solar_start_ms))/1000.0;
  time_solar_last_s = -9999;
  
  Serial.print("$ ");
}

void sst_console_set_rate() {
  char* arg;
  double rate;
  arg = sSSTCmd.next();
  if (arg == NULL) {
    Serial.println(F("ERROR: Invalid argument given to 'set_rate'"));
  } else {
    rate = atof(arg);
    sst_rate = rate;
    time_adjust_s = steps_to_time_solar(sstvars.dir*Astepper1.currentPosition()) - ((float)(millis() - time_solar_start_ms))/1000.0;
    time_solar_last_s = -9999;
    if(sst_debug) {
      Serial.println(time_adjust_s);
    }

    Serial.print(F("Rate set to "));
    Serial.println(rate); 
  }  
  Serial.print(F("$ "));
}

void sst_console_set_debug() {
  char* arg;
  int iarg;
  
  arg = sSSTCmd.next();
  if (arg != NULL) {
    iarg = atoi(arg);
    if (iarg == 1) {
      sst_debug = true;
      Serial.println(F("Debug ENABLED"));
    } else {
      sst_debug = false;
      Serial.println(F("Debug DISABLED"));
    }
  } else {
    Serial.println(F("ERROR: Missing 0 or 1 argument."));
  }
  Serial.print(F("$ "));
}

void sst_console_set_var() {
  char* argVarName;
  char* argValue;
  double value;
  uint8_t ivalue;
  bool updated;

  argVarName = sSSTCmd.next();
  if (argVarName == NULL) {
    Serial.println(F("ERROR: Missing [variable_name] argument."));
    return;
  }
  argValue = sSSTCmd.next();
  if (argValue == NULL){
    Serial.println(F("ERROR: Missing [value] argument."));
    return;    
  }
  //TODO: Convert argValue based on argVarName? or always double atof?
  value = atof(argValue);
  ivalue = atoi(argValue);

  updated = true;
  if(strcmp_P(argVarName, PSTR("stepsPerRotation")) == 0) {
    sstvars.stepsPerRotation = value;
  } else if(strcmp_P(argVarName, PSTR("recalcIntervalS")) == 0) {
    sstvars.recalcIntervalS = value;
  } else if(strcmp_P(argVarName, PSTR("dir")) == 0) {
    sstvars.dir = value;
  } else {
    updated = false;
    Serial.print("ERROR: Invalid variable name '");
    Serial.print(argVarName);
    Serial.println("'");
  }
  
  if (updated) {
    sst_save_sstvars();
    Serial.println("Saved value to EEPROM, It's recommended to do a 'reset'");
  }
  
  Serial.print("$ ");

}

void sst_console_status() {
  float theta, t;
  float l;

  Serial.println();
  Serial.println(F("EEPROM Values:"));
  Serial.print(F(" stepsPerRotation="));
  Serial.println(sstvars.stepsPerRotation);
  Serial.print(F(" recalcIntervalS="));
  Serial.println(sstvars.recalcIntervalS);
  Serial.print(F(" dir="));
  Serial.println(sstvars.dir);
  Serial.println(F("Runtime Status:"));
  if (sst_debug) {
    Serial.println(F(" Debug: Enabled"));
  } else {
    Serial.println(F(" Debug: Disabled"));    
  }
  Serial.print(F(" Version: "));
  Serial.println(sstversion);
  Serial.print(F(" Rate: "));
  Serial.println(sst_rate);
  Serial.print(F(" Steps: "));
  Serial.println(sstvars.dir*Astepper1.currentPosition());
  Serial.print(F(" Time: "));
  t= (float)(millis() - time_solar_start_ms)/1000.0 + time_adjust_s;
  Serial.print(t);
  Serial.print(" RT: ");
  Serial.println(millis()/1000.0);
  Serial.print(F(" Speed: "));
  Serial.println(Astepper1.speed());
  
  Serial.print(F("$ "));
}

void sst_console_help(const char* cmd) {
  Serial.println(F("SST Commands:"));
  Serial.println(F(" stop                             Stop tracking."));
  Serial.println(F(" continue                         Continue tracking if stopped."));
  Serial.println(F(" mv [length] arcseconds           Move to [length] in arcseconds from current position"));
  Serial.println(F(" set_rate [rate]                  Set tracking rate to [rate]."));
  Serial.println(F(" set_debug 0|1                    0 debug output disable, 1 debug output enabled."));
  Serial.println(F(" set_var [variable_name] [value]  Sets eeprom calibration variable."));
  Serial.println(F(" status                           Shows tracker status and eeprom variable values."));
  Serial.println("");
  Serial.print(F("$ "));
}

void sst_console_init() {
  sSSTCmd.addCommand("stop", sst_console_stop);
  sSSTCmd.addCommand("continue", sst_console_continue);
  sSSTCmd.addCommand("mv", sst_console_mv);
  sSSTCmd.addCommand("set_rate", sst_console_set_rate);
  sSSTCmd.addCommand("set_debug", sst_console_set_debug);
  sSSTCmd.addCommand("set_var", sst_console_set_var);
  sSSTCmd.addCommand("status", sst_console_status);
  sSSTCmd.setDefaultHandler(sst_console_help); // Help   
  Serial.print(F("$ "));
}

void sst_console_read_serial() {
  sSSTCmd.readSerial();
}

