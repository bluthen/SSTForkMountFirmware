#include <LiquidCrystal.h>
#include <Bounce2.h>
#include <stdint.h>

static const uint16_t handpad_version = 2;
const static uint8_t lcd_rs = 3;
const static uint8_t lcd_en = 4;
const static uint8_t lcd_d7 = 7;
const static uint8_t lcd_d6 = 9;
const static uint8_t lcd_d5 = 12;
const static uint8_t lcd_d4 = 13;
const static uint8_t lcd_columns = 20;
const static uint8_t lcd_rows = 4;

const static uint8_t lcd_pwm = 11;
const static uint8_t button_pwm = 10;

static const uint16_t PWM_LEVELS_LCD[] = {5000, 12071, 65535};
static const uint16_t PWM_LEVELS_BUTTONS[] = {100, 300, 738};
static uint8_t brightness_pwm = 2; 

LiquidCrystal lcd (lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7);
Bounce up = Bounce();
Bounce esc = Bounce();
Bounce down = Bounce();
Bounce left = Bounce();
Bounce right = Bounce();
Bounce sel = Bounce();

static char buttons_released[7];
static char buttons_pressed[7];
uint8_t bs_idx = 0;
static const uint8_t MAX_BUTTON_SEQUENCE = 40;
static char button_sequence[MAX_BUTTON_SEQUENCE];

static char gps_rmc_buf[83];
static char gps_gga_buf[83];

static bool no_cmd_display = false;
static unsigned long no_cmd_timer = 0;
static unsigned long wake_timer = 0;
static char lcd_state[4][21];
static bool is_display_sleep = false;

static const uint8_t MAX_CMD_SIZE = 25;
static char cmd[MAX_CMD_SIZE];

static uint8_t BOUNCE_DELAY = 20;

void display_sleep() {
  analogWrite(lcd_pwm, PWM_LEVELS_LCD[brightness_pwm]);
  analogWrite(button_pwm, PWM_LEVELS_BUTTONS[brightness_pwm]);  
}


void display_awake() {
  analogWrite(lcd_pwm, PWM_LEVELS_LCD[brightness_pwm]);
  analogWrite(button_pwm, PWM_LEVELS_BUTTONS[brightness_pwm]);  
}


void clearSerial1Input() {
  while(Serial1.available() > 0) {
    Serial1.read();
  }
}


void get_gps_lines() {
  uint8_t len;
  unsigned long start = millis();
  clearSerial1Input();
  while(true && (millis() - start) < 2500) {
    len = Serial1.readBytesUntil('\n', gps_rmc_buf, 82);
    if(len > 6 && gps_rmc_buf[0] == '$' && gps_rmc_buf[1] == 'G' && gps_rmc_buf[2] == 'P' && 
       gps_rmc_buf[3] == 'R' && gps_rmc_buf[4] == 'M' && gps_rmc_buf[5] == 'C') {
      gps_rmc_buf[len] = 0;
     
      while(true && (millis() - start) < 2500) {
        len = Serial1.readBytesUntil('\n', gps_gga_buf, 82);
        if(len > 6 && gps_gga_buf[0] == '$' && gps_gga_buf[1] == 'G' && gps_gga_buf[2] == 'P' && 
           gps_gga_buf[3] == 'G' && gps_gga_buf[4] == 'G' && gps_gga_buf[5] == 'A') {
          gps_gga_buf[len] = 0;
          return;   
        }
      }
    }
  }
  strcpy(gps_rmc_buf, "ERROR");
  strcpy(gps_gga_buf, "ERROR");
}


uint8_t read_cmd() {
  unsigned long start = millis();
  int avail = 0;
  uint8_t pos = 0;
  bool found_at = false;
  char c = 0;
  while(millis() - start < 100 && pos < MAX_CMD_SIZE-1) {
    avail = Serial.available();
    if (avail > 0) {
       c = Serial.read();
       start = millis();
    }
    if(!found_at) {
      if (c == '@') {
        found_at = true;
      }
    }
    if(found_at) {
      cmd[pos] = c;
      pos++;
      if (c == '!') {
        cmd[pos] = 0;
        return pos;
      }
    }
  }
  cmd[0] = 0;
  return 0;
}


void print_lcd_state(uint8_t start_line, uint8_t end_line) {
  uint8_t i = 0;
  for(i = start_line; i < end_line + 1; i++) {
    lcd.setCursor(0, i);    
    lcd.print(lcd_state[i]);
  }
}


void button_sequence_updates(Bounce& b, char bc, uint8_t& br_idx, uint8_t& bp_idx) {
  if (b.fell()) {
    wake_timer = millis();
    if (is_display_sleep) {
      display_awake();
      is_display_sleep = false;
    } else {
      if (bs_idx < MAX_BUTTON_SEQUENCE -1) {
        button_sequence[bs_idx] = bc;
        bs_idx++;
        button_sequence[bs_idx] = 0;
      }
    }
  }
  if (b.read()) {
    buttons_released[br_idx] = bc;
    br_idx++;    
  } else {
    buttons_pressed[bp_idx] = bc;
    bp_idx++;
  }  
}



void setup()
{
  strcpy(lcd_state[0], "StarSync Trackers   ");
  strcpy(lcd_state[1], "Initializing...     ");
  strcpy(lcd_state[2], "                    ");
  strcpy(lcd_state[3], "                    ");

  lcd.begin(lcd_columns, lcd_rows);
  print_lcd_state(0, 3);
  analogWriteResolution(16);
  display_awake();
  
  up.attach(A4, INPUT_PULLUP);
  esc.attach(A3, INPUT_PULLUP);
  down.attach(A2, INPUT_PULLUP);
  left.attach(A5, INPUT_PULLUP);
  right.attach(A1, INPUT_PULLUP);
  sel.attach(2, INPUT_PULLUP);
  up.interval(BOUNCE_DELAY);
  esc.interval(BOUNCE_DELAY);
  down.interval(BOUNCE_DELAY);
  left.interval(BOUNCE_DELAY);
  right.interval(BOUNCE_DELAY);
  sel.interval(BOUNCE_DELAY);

  Serial1.begin(9600);
  Serial1.setTimeout(2500);
  no_cmd_timer = millis();
  wake_timer = millis();
  is_display_sleep = false;
  no_cmd_display = false;
  bs_idx = 0;
}


void loop()
{
  uint8_t len = 0;
  len = read_cmd();
  if (len >= 3) {
    no_cmd_timer = millis();
    if (no_cmd_display && cmd[0] == '@' && cmd[len-1] == '!') {
      no_cmd_display = false;
      print_lcd_state(0, 3);
    }
    if (cmd[0] == '@' && cmd[len-1] == '!') {
      if (cmd[1] == 'B') {
        Serial.print("@");
        Serial.print(button_sequence);
        Serial.print("!");
        button_sequence[0] = 0;
        bs_idx = 0;

      } else if (cmd[1] == 'J') {
        Serial.print("@");
        Serial.print(buttons_released);
        Serial.print("!");        
      } else if (cmd[1] == 'K') {
        Serial.print("@");
        Serial.print(buttons_pressed);
        Serial.print("!");                
      } else if (cmd[1] == 'D' && cmd[2] >= 48) {
        uint8_t line = cmd[2] - 48;
        if (line < 4) {
          memcpy(lcd_state[line], cmd+3, len-4);
          print_lcd_state(line, line);
          Serial.print("@K!");
        }
      } else if (len == 7 && cmd[1] == 'S' && cmd[2] == 'S' && cmd[3] == 'T' && cmd[4] == 'H' && cmd[5] == 'P') {
        Serial.print("@");
        Serial.print("SSTHP_");
        if (handpad_version < 100) {
          Serial.print("0");
        }
        if (handpad_version < 10) {
          Serial.print(0);
        }
        Serial.print(handpad_version);
        Serial.print("!");
      } else if (cmd[1] == 'R') {
        lcd.clear();
        Serial.print("@K!");
      } else if (cmd[1] == 'L') {
        uint8_t brightness = cmd[2] - 48;
        if (brightness < 3) {
          brightness_pwm = brightness;
          display_awake();
          Serial.print("@K!");        
        }
      } else if (cmd[1] == 'G' && cmd[2] == 'P' && cmd[3] == 'S') {
        get_gps_lines();
        Serial.print("@");
        Serial.print(gps_rmc_buf);
        Serial.print("\n");
        Serial.print(gps_gga_buf);
        Serial.print("!");
      }
    }
  }

  // Button states
  uint8_t br_idx = 0;
  uint8_t bp_idx = 0;

  button_sequence_updates(up, 'U', br_idx, bp_idx);
  button_sequence_updates(esc, 'E', br_idx, bp_idx);
  button_sequence_updates(down, 'D', br_idx, bp_idx);
  button_sequence_updates(left, 'L', br_idx, bp_idx);
  button_sequence_updates(right, 'R', br_idx, bp_idx);
  button_sequence_updates(sel, 'S', br_idx, bp_idx);
  
  buttons_released[br_idx] = 0;
  buttons_pressed[bp_idx] = 0;

  if (millis() - wake_timer > 120000 && !is_display_sleep) {
    display_sleep();
    is_display_sleep = true;  
  }

  if (!no_cmd_display && (millis() - no_cmd_timer) > 30000) {
    no_cmd_display = true;
    lcd.setCursor(0,0);
    lcd.print("Communication with  ");
    lcd.setCursor(0,1);
    lcd.print("mount lost.         ");
    lcd.setCursor(0,2);
    lcd.print("                    ");
    lcd.setCursor(0,3);
    lcd.print("                    ");
  }

  up.update();
  esc.update();
  down.update();
  left.update();
  right.update();
  sel.update();
}
