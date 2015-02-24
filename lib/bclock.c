// Andrew Pullin, 2/23/15
// Simple 3-segment beuhler clock for roach running

#include <xc.h>

#include "bclock.h"
#include "stdint.h"
#include "timer.h"

bclock_t currentClock;
char running = 0;

//Private function prototypes
static void SetupTimer3(void);
static void bclockSynth(void);

//Private funcitons
void SetupTimer3() {
    unsigned int T3CON1value, T3PERvalue;
    T3CON1value = T3_ON & T3_SOURCE_INT & T3_PS_1_8 & T3_GATE_OFF &
            T1_SYNC_EXT_OFF & T3_INT_PRIOR_6;
    T3PERvalue = 4000; //1250 Hz for 1:8 divider
    OpenTimer3(T3CON1value, T3PERvalue);
    _T3IE = 0;
}

static void bclockSynth(void){
    //Synth math goes here!
}


// Interrupt definition
void __attribute__((interrupt, no_auto_psv)) _T3Interrupt(void) {

    if(running){
        currentClock.arg1 += currentClock.incr1;
        currentClock.arg2 += currentClock.incr2;

        bclockSynth();
    }
    else{
        tiHSetDC(1, 0);
        tiHSetDC(2, 0);
    }
    _T3IF = 0;
}


//Public functions

void blockSetup(){
    //Default setup
    currentClock.phase1 = 0;
    currentClock.phase2 = PHASE_180_DEG;
    currentClock.incr1 = BCLOCK_INCR_3HZ;
    currentClock.incr2 = BCLOCK_INCR_3HZ;
    currentClock.period1 = 3*65535;
    currentClock.period2 = 3*65535;
    currentClock.t1 = (int)(0.2222*65535);
    currentClock.t2 = (int)(0.7777*65535);
    currentClock.theta1 = (int)(0.4*65535);
    currentClock.theta2 = (int)(0.7*65535);

    //Set up timer
    SetupTimer3();

}

void bclockStart(void) {
    //_OC1IE = 1;
    running = 1;
    TMR3 = 0; //reset timer counter, so sin arg starts at 0
    T3CONbits.TON = 1;
    _T3IE = 1;
}

void bclockStop(void) {
    //_OC1IE = 0;
    running = 0;
    T3CONbits.TON = 0;
}


void bclockSetParams(bclock_t* params);
void bclockGetParams(bclock_t* buf);

void bclockUpdate(unsigned int time);
void bclockGetSetpoint(int* sp1, int* sp2);