
#include "stepper_drivers.h"

static void stepper_forwardstep1(void);
static void stepper_forwardstep2(void);
static void stepper_backwardstep1(void);
static void stepper_backwardstep2(void);


static const uint16_t stepsPerRotation = 200;

Adafruit_MotorShield AFMS;
Adafruit_StepperMotor* myStepper1;
Adafruit_StepperMotor* myStepper2;

void stepper_init() {
  // Create the motor shield object with the default I2C address
  AFMS = Adafruit_MotorShield();
  // Or, create it with a different I2C address (say for stacking)
  // Adafruit_MotorShield AFMS = Adafruit_MotorShield(0x61); 

  // create with the default frequency 1.6KHz
  AFMS.begin(); 
  
  // motor port #1 M1 and M2
  myStepper1 = AFMS.getStepper(stepsPerRotation, 1);
  // motor port #2 (M3 and M4)
  myStepper2 = AFMS.getStepper(stepsPerRotation, 2);
  stepper_forwardstep1();
  stepper_forwardstep2();
  
}


// you can change these to DOUBLE or INTERLEAVE or MICROSTEP!
void stepper_forwardstep1() {
  myStepper1->onestep(FORWARD, MICROSTEP);
}
void stepper_backwardstep1() {  
  myStepper1->onestep(BACKWARD, MICROSTEP);
}

void stepper_forwardstep1_fast() {
  myStepper1->onestep(FORWARD, SINGLE);
}
void stepper_backwardstep1_fast() {  
  myStepper1->onestep(BACKWARD, SINGLE);
}



// you can change these to DOUBLE or INTERLEAVE or MICROSTEP!
void stepper_forwardstep2() {
  myStepper2->onestep(FORWARD, MICROSTEP);
}
void stepper_backwardstep2() {  
  myStepper2->onestep(BACKWARD, MICROSTEP);
}

// you can change these to DOUBLE or INTERLEAVE or MICROSTEP!
void stepper_forwardstep2_fast() {
  myStepper2->onestep(FORWARD, SINGLE);
}
void stepper_backwardstep2_fast() {  
  myStepper2->onestep(BACKWARD, SINGLE);
}




static float RASpeed = 0.0;
static float DECSpeed = 0.0;

static long RACounts = 0;
static long DECCounts = 0;

static unsigned long RAClock = 0;
static unsigned long DECClock = 0;



void setRASpeed(float speed) {
  RASpeed = speed;
  RACounts = 0;
  RAClock = millis();  
}

void setDECSpeed(float speed) {
  DECSpeed = speed;
  DECCounts = 0;
  DECClock = millis();
  
}

static float count;

void runSteppers() {
  count = RACounts - (RASpeed*((float)(millis() - RAClock))/1000.0);
  //Serial.println(RASpeed);
  //Serial.println(RAClock);
  //Serial.println(RACounts);
  //Serial.println(count);
  if(abs(RASpeed) > 150.0) {
    if (count < -MICROSTEP) {
        stepper_backwardstep1_fast();
        RACounts += MICROSTEP;
    } else if (count > MICROSTEP) {
        stepper_forwardstep1_fast();    
        RACounts -= MICROSTEP;
    }    
  } else {
    if (count < -1.0) {
        stepper_backwardstep1();
        RACounts++;
    } else if (count > 1.0) {
        stepper_forwardstep1();    
        RACounts--;
    }
  }

  count = DECCounts - (DECSpeed*((float)(millis() - DECClock))/1000.0);

  if(abs(DECSpeed) > 150.0) {
    if (count < -MICROSTEP) {
      stepper_backwardstep2_fast();
      DECCounts+=MICROSTEP;
    } else if (count > MICROSTEP) {
      stepper_forwardstep2_fast();    
      DECCounts-=MICROSTEP;
    }    
  } else {
    if (count < -1.0) {
      stepper_backwardstep2();
      DECCounts++;
    } else if (count > 1.0) {
      stepper_forwardstep2();    
      DECCounts--;
    }
  }

}


//AccelStepper RAStepper1(stepper_forwardstep1, stepper_backwardstep1); // use functions to step
//AccelStepper DECStepper2(stepper_forwardstep2, stepper_backwardstep2); // use functions to step

