#ifndef __COMMAND_H
#define __COMMAND_H

#include "SerialCommand.h"

class Command {
public:
  Command(Stream* _port);
  void read();

private:
  void command_set_var();
  void command_ra_set_speed();
  void command_dec_set_speed();
  void command_autoguide_disable();
  void command_autoguide_enable();
  void command_status();
  void command_qs();
  void command_help(const char *cmd);
  void print_prompt();
  Stream* port;
  SerialCommand* cmd;
};

#endif
