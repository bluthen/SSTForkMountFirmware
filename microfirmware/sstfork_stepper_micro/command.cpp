#include <pgmspace.h>

#include "SerialCommand.h"
#include "command.h"
#include "forkmount.h"
#include "stepper.h"

Command::Command(Stream* _port) {
  port = _port;
  cmd = new SerialCommand(port);
  cmd->addCommand("set_var", [this] () -> void { this->command_set_var();});
  cmd->addCommand("ra_set_speed", [this] () { this->command_ra_set_speed(); } );
  cmd->addCommand("dec_set_speed", [this] () { this->command_dec_set_speed(); } );
  cmd->addCommand("autoguide_disable", [this] () { this->command_autoguide_disable(); });
  cmd->addCommand("autoguide_enable", [this] () { this->command_autoguide_enable(); });
  cmd->addCommand("status", [this] () { this->command_status(); });
  cmd->addCommand("qs", [this] () { this->command_qs(); });
  cmd->setDefaultHandler([this] (const char *cmd) -> void { this->command_help(cmd); });
  print_prompt();
}


void Command::print_prompt() {
  port->print("$ ");
}

void Command::command_set_var() {
  char *argName;
  char *argVal;
  float value;

  argName = cmd->next();
  argVal = cmd->next();

  if (argName == NULL) {
    port->println("ERROR: Missing [variable_name] argument.");
    print_prompt();
    return;
  }

  if (argVal == NULL) {
    port->println("ERROR: Missing [value] argument.");
    print_prompt();
    return;
  }
  value = atof(argVal);
  DEBUG_SERIAL.print(argName);
  DEBUG_SERIAL.print(": ");
  DEBUG_SERIAL.println(value);

  if (strcmp(argName, "ra_max_tps") == 0) {
    raStepper->setMaxSpeed(value);
  } else if (strcmp(argName, "ra_guide_rate") == 0) {
    raStepper->setGuideRate(value);
  } else if (strcmp(argName, "ra_direction") == 0) {
    raStepper->setInvertedStepping(((int)value) == -1);
  } else if (strcmp(argName, "dec_max_tps") == 0) {
    decStepper->setMaxSpeed(value);
  } else if (strcmp(argName, "dec_guide_rate") == 0) {
    decStepper->setGuideRate(value);
  } else if (strcmp(argName, "dec_direction") == 0) {
    decStepper->setInvertedStepping(((int)value) == -1);
  } else if (strcmp(argName, "dec_disable") == 0) {
    if ((int)value) {
      decStepper->enable(false);
    } else {
      decStepper->enable(true);
    }
  } else if (strcmp(argName, "ra_disable") == 0) {
    if ((int)value) {
      raStepper->enable(false);
    } else {
      raStepper->enable(true);
    }
  } else if (strcmp(argName, "ra_accel_tpss") == 0) {
    raStepper->setMaxAccel(value);
  } else if (strcmp(argName, "dec_accel_tpss") == 0) {
    decStepper->setMaxAccel(value);
  } else if (strcmp(argName, "ra_run_current") == 0) {
    raStepper->setRunCurrent(value);
  } else if (strcmp(argName, "ra_med_current") == 0) {
    raStepper->setMedCurrent(value);
  } else if (strcmp(argName, "ra_med_current_threshold") == 0) {
    DEBUG_SERIAL.print("ra_med_current_threshold");
    DEBUG_SERIAL.println(value);
    raStepper->setMedCurrentThreshold(value);
  } else if (strcmp(argName, "ra_hold_current") == 0) {
    raStepper->setHoldCurrent(value);
  } else if (strcmp(argName, "dec_run_current") == 0) {
    decStepper->setRunCurrent(value);
  } else if (strcmp(argName, "dec_med_current") == 0) {
    decStepper->setMedCurrent(value);
  } else if (strcmp(argName, "dec_med_current_threshold") == 0) {
    decStepper->setMedCurrentThreshold(value);
  } else if (strcmp(argName, "dec_hold_current") == 0) {
    decStepper->setHoldCurrent(value);
  } else if (strcmp(argName, "ra_backlash") == 0) {
    raStepper->setBacklash((int)value);
  } else if (strcmp(argName, "ra_backlash_speed") == 0) {
    raStepper->setBacklashSpeed(value);
  } else if (strcmp(argName, "dec_backlash") == 0) {
    decStepper->setBacklash((int)value);
  } else if (strcmp(argName, "dec_backlash_speed") == 0) {
    decStepper->setBacklashSpeed(value);
  } else {
    port->print("ERROR: Invalid variable name '");
    port->print(argName);
    port->println("'");
  }
  print_prompt();
}

void Command::command_qs() {
  long raPos, decPos;
  stepper_encoder_t raEnc, decEnc;
  // TODO: Maybe make binary status so we don't get close to tracking tick
  // interval?
  port->print("rs:");
  port->println(raStepper->getSpeed());
  port->print("ds:");
  port->println(decStepper->getSpeed());
  raPos = raStepper->getPosition();
  decPos = decStepper->getPosition();
  raStepper->getEncoder(raEnc);
  decStepper->getEncoder(decEnc);
  port->print("rp:");
  port->println(raPos);
  port->print("dp:");
  port->println(decPos);
  port->print("re:");
  port->println(raEnc.value);
  port->print("de:");
  port->println(decEnc.value);
  port->print("ri:");
  port->println(raEnc.steps_in_pulse);
  port->print("di:");
  port->println(decEnc.steps_in_pulse);
  port->print("rl:");
  port->println(raEnc.prev_steps_in_pulse);
  port->print("dl:");
  port->println(decEnc.prev_steps_in_pulse);
  print_prompt();
}

void Command::command_status() {
  long raPos, decPos;
  stepper_encoder_t raEnc, decEnc;
  port->print("ra_max_tps=");
  port->println(raStepper->getMaxSpeed());
  port->print("ra_guide_rate=");
  port->println(raStepper->getGuideRate());
  port->print("ra_direction=");
  port->println(raStepper->getInvertedStepping() ? -1 : 1);
  port->print("ra_disable=");
  port->println(raStepper->enabled() ? 0 : 1);
  port->print("ra_accel_tpss=");
  port->println(raStepper->getMaxAccel());
  port->print("dec_max_tps=");
  port->println(decStepper->getMaxSpeed());
  port->print("dec_guide_rate=");
  port->println(decStepper->getGuideRate());
  port->print("dec_direction=");
  port->println(decStepper->getInvertedStepping() ? -1 : 1);
  port->print("dec_disable=");
  port->println(decStepper->enabled() ? 0 : 1);
  port->print("dec_accel_tpss=");
  port->println(decStepper->getMaxAccel());

  port->print("ra_run_current=");
  port->println(raStepper->getRunCurrent());
  port->print("ra_med_current=");
  port->println(raStepper->getMedCurrent());
  port->print("ra_med_current_threshold=");
  port->println(raStepper->getMedCurrentThreshold());
  port->print("ra_hold_current=");
  port->println(raStepper->getHoldCurrent());

  port->print("dec_run_current=");
  port->println(decStepper->getRunCurrent());
  port->print("dec_med_current=");
  port->println(decStepper->getMedCurrent());
  port->print("dec_med_current_threshold=");
  port->println(decStepper->getMedCurrentThreshold());
  port->print("dec_hold_current=");
  port->println(decStepper->getHoldCurrent());

  port->print("ra_backlash=");
  port->println(raStepper->getBacklash());
  port->print("ra_backlash_speed=");
  port->println(raStepper->getBacklashSpeed());
  port->print("dec_backlash=");
  port->println(decStepper->getBacklash());
  port->print("dec_backlash_speed=");
  port->println(decStepper->getBacklashSpeed());


  port->print("ra_current_real=");
  port->println(raStepper->getCurrentReal());
  port->print("dec_current_real=");
  port->println(decStepper->getCurrentReal());


  port->print("debug:");
  port->println(sst_debug);
  port->print("autoguide:");
  port->println(raStepper->guidingEnabled());
  port->print("ra_speed:");
  port->println(raStepper->getSpeed());
  port->print("dec_speed:");
  port->println(decStepper->getSpeed());

  raPos = raStepper->getPosition();
  decPos = decStepper->getPosition();
  raStepper->getEncoder(raEnc);
  decStepper->getEncoder(decEnc);
  port->print("ra_tpe:");
  port->println(raEnc.prev_steps_in_pulse);
  port->print("dec_tpe:");
  port->println(decEnc.prev_steps_in_pulse);
  port->print("ra_pos:");
  port->println(raPos);
  port->print("dec_pos:");
  port->println(decPos);
  port->print("ra_enc:");
  port->println(raEnc.value);
  port->print("dec_enc:");
  port->println(decEnc.value);
  port->print("ra_tip:");
  port->println(raEnc.steps_in_pulse);
  port->print("dec_tip:");
  port->println(decEnc.steps_in_pulse);
  print_prompt();
}

void Command::command_ra_set_speed() {
  char *argVal;
  float value;

  argVal = cmd->next();

  if (argVal == NULL) {
    port->println("ERROR: Missing [value] argument.");
    print_prompt();
    return;
  }
  value = atof(argVal);
  raStepper->setSpeed(value);
  port->print("ra_speed:");
  port->println(raStepper->getSpeed());
  print_prompt();
}

void Command::command_dec_set_speed() {
  char *argVal;
  float value;

  argVal = cmd->next();

  if (argVal == NULL) {
    port->println("ERROR: Missing [value] argument.");
    print_prompt();
    return;
  }
  value = atof(argVal);
  decStepper->setSpeed(value);
  port->print("dec_speed:");
  port->println(decStepper->getSpeed());
  print_prompt();
}

void Command::command_help(const char *cmd) {
  port->println("Commands:");
  port->println("  set_var [variable_name] [value] Sets variable");
  port->println("  ra_set_speed [tps]           Moves RA to tick position");
  port->println("  dec_set_speed [tps]          Moves DEC to tick position");
  port->println(
    "  autoguide_disable            Disables Autoguiding port input");
  port->println(
    "  autoguide_enable             Enables Autoguiding prot input");
  port->println("  status                       Shows status/variable info");
  port->println("  qs                           Shows speed/position info");
  port->println("  help                         This help info");
  print_prompt();
}

void Command::command_autoguide_disable() {
  raStepper->guidingEnable(false);
  decStepper->guidingEnable(false);
  print_prompt();
}

void Command::command_autoguide_enable() {
  raStepper->guidingEnable(true);
  decStepper->guidingEnable(true);
  print_prompt();
}

void Command::read() {
  cmd->readSerial();
}
