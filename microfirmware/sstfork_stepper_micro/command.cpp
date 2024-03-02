#include <pgmspace.h>

#include "SerialCommand.h"
#include "command.h"
#include "forkmount.h"
#include "stepper.h"

static SerialCommand cmd;

void print_prompt() { WSERIAL.print("$ "); }

void command_set_var() {
  char *argName;
  char *argVal;
  float value;

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
    if((int)value) {
      raStepper->enable(false);
    } else {
      raStepper->enable(true);
    }
  } else if (strcmp(argName, "ra_accel_tpss") == 0) {
    raStepper->setMaxAccel(value);
  } else if (strcmp(argName, "dec_accel_tpss") == 0) {
    decStepper->setMaxAccel(value);
  } else {
    WSERIAL.print("ERROR: Invalid variable name '");
    WSERIAL.print(argName);
    WSERIAL.println("'");
  }
  print_prompt();
}

void command_qs() {
  long raPos, decPos;
  stepper_encoder_t raEnc, decEnc;
  // TODO: Maybe make binary status so we don't get close to tracking tick
  // interval?
  WSERIAL.print("rs:");
  WSERIAL.println(raStepper->getSpeed());
  WSERIAL.print("ds:");
  WSERIAL.println(decStepper->getSpeed());
  raPos = raStepper->getPosition();
  decPos = decStepper->getPosition();
  raStepper->getEncoder(raEnc);
  decStepper->getEncoder(decEnc);
  WSERIAL.print("rp:");
  WSERIAL.println(raPos);
  WSERIAL.print("dp:");
  WSERIAL.println(decPos);
  WSERIAL.print("re:");
  WSERIAL.println(raEnc.value);
  WSERIAL.print("de:");
  WSERIAL.println(decEnc.value);
  WSERIAL.print("ri:");
  WSERIAL.println(raEnc.steps_in_pulse);
  WSERIAL.print("di:");
  WSERIAL.println(decEnc.steps_in_pulse);
  WSERIAL.print("rl:");
  WSERIAL.println(raEnc.prev_steps_in_pulse);
  WSERIAL.print("dl:");
  WSERIAL.println(decEnc.prev_steps_in_pulse);
  print_prompt();
}

void command_status() {
  long raPos, decPos;
  stepper_encoder_t raEnc, decEnc;
  WSERIAL.print("ra_max_tps=");
  WSERIAL.println(raStepper->getMaxSpeed());
  WSERIAL.print("ra_guide_rate=");
  WSERIAL.println(raStepper->getGuideRate());
  WSERIAL.print("ra_direction=");
  WSERIAL.println(raStepper->getInvertedStepping() ? -1 : 1);
  WSERIAL.print("ra_disable=");
  WSERIAL.println(raStepper->enabled() ? 0 : 1);
  WSERIAL.print("ra_accel_tpss=");
  WSERIAL.println(raStepper->getMaxAccel());
  WSERIAL.print("dec_max_tps=");
  WSERIAL.println(decStepper->getMaxSpeed());
  WSERIAL.print("dec_guide_rate=");
  WSERIAL.println(decStepper->getGuideRate());
  WSERIAL.print("dec_direction=");
  WSERIAL.println(decStepper->getInvertedStepping() ? -1 : 1);
  WSERIAL.print("dec_disable=");
  WSERIAL.println(decStepper->enabled() ? 0 : 1);
  WSERIAL.print("dec_accel_tpss=");
  WSERIAL.println(decStepper->getMaxAccel());
  WSERIAL.print("debug:");
  WSERIAL.println(sst_debug);
  WSERIAL.print("autoguide:");
  WSERIAL.println(!raStepper->guidingDisabled());
  WSERIAL.print("ra_speed:");
  WSERIAL.println(raStepper->getSpeed());
  WSERIAL.print("dec_speed:");
  WSERIAL.println(decStepper->getSpeed());

  raPos = raStepper->getPosition();
  decPos = decStepper->getPosition();
  raStepper->getEncoder(raEnc);
  decStepper->getEncoder(decEnc);
  WSERIAL.print("ra_tpe:");
  WSERIAL.println(raEnc.prev_steps_in_pulse);
  WSERIAL.print("dec_tpe:");
  WSERIAL.println(decEnc.prev_steps_in_pulse);
  WSERIAL.print("ra_pos:");
  WSERIAL.println(raPos);
  WSERIAL.print("dec_pos:");
  WSERIAL.println(decPos);
  WSERIAL.print("ra_enc:");
  WSERIAL.println(raEnc.value);
  WSERIAL.print("dec_enc:");
  WSERIAL.println(decEnc.value);
  WSERIAL.print("ra_tip:");
  WSERIAL.println(raEnc.steps_in_pulse);
  WSERIAL.print("dec_tip:");
  WSERIAL.println(decEnc.steps_in_pulse);
  print_prompt();
}

void command_ra_set_speed() {
  char *argVal;
  float value;

  argVal = cmd.next();

  if (argVal == NULL) {
    WSERIAL.println("ERROR: Missing [value] argument.");
    print_prompt();
    return;
  }
  value = atof(argVal);
  raStepper->setSpeed(value);
  WSERIAL.print("ra_speed:");
  WSERIAL.println(raStepper->getSpeed());
  print_prompt();
}

void command_dec_set_speed() {
  char *argVal;
  float value;

  argVal = cmd.next();

  if (argVal == NULL) {
    WSERIAL.println("ERROR: Missing [value] argument.");
    print_prompt();
    return;
  }
  value = atof(argVal);
  decStepper->setSpeed(value);
  WSERIAL.print("dec_speed:");
  WSERIAL.println(decStepper->getSpeed());
  print_prompt();
}

void command_help(const char *cmd) {
  WSERIAL.println("Commands:");
  WSERIAL.println("  set_var [variable_name] [value] Sets variable");
  WSERIAL.println("  ra_set_speed [tps]           Moves RA to tick position");
  WSERIAL.println("  dec_set_speed [tps]          Moves DEC to tick position");
  WSERIAL.println(
      "  autoguide_disable            Disables Autoguiding port input");
  WSERIAL.println(
      "  autoguide_enable             Enables Autoguiding prot input");
  WSERIAL.println("  status                       Shows status/variable info");
  WSERIAL.println("  qs                           Shows speed/position info");
  WSERIAL.println("  help                         This help info");
  print_prompt();
}

void command_autoguide_disable() {
  raStepper->disableGuiding(true);
  decStepper->disableGuiding(true);
  print_prompt();
}

void command_autoguide_enable() {
  raStepper->disableGuiding(false);
  decStepper->disableGuiding(false);
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

void command_read_serial() { cmd.readSerial(); }
