/*
 * File:   ams-vibe.c
 * Author: pullin
 *
 * Created on April 6, 2015
 */

#include <xc.h>
//Library includes
#include "timer.h"
#include "libq.h"
#include <stdint.h>
//#include "math.h"  //for abs
//Module includes
#include "ams-vibe.h"
#include "tih.h"
#include "telem.h"      //Cross-module dependence
#include "mpu6000.h"    //Cross-module dependence
#include "ams-enc.h"    //Cross-module dependence


//static int chan1amp, chan2amp;
//static int chan1off, chan2off;
//static int chan1dc, chan2dc;
//static _Q15 chan1_tb, chan2_tb;
//static _Q15 chan1arg, chan2arg;
//static _Q15 chan1_delta, chan2_delta;

static unsigned char running = 0;


typedef struct{
    unsigned char channel;
    int amp, offset, phase;
    int out;
    _Q15 timebase;
    _Q15 delta;
    _Q15 arg;
} amsVibeCtrl_t;

amsVibeCtrl_t vibe1, vibe2;

//Private functions
static void update_vibe_synth();
//static void SetupTimer1();

void amsVibeSetup() {
    //Default to 50hz @ 0% drive
    //TODO: Verify this for new ams-vibe mode, probably wrong due to new update rate!, pullin 4/6/2015
    //amsVibeSetAmplitude(1, 0);
    //amsVibeSetAmplitude(2, 0);
    //amsVibeSetFrequency(1,2621); //50 hz
    //amsVibeSetFrequency(2,2621); //50 hz

    vibe1.arg = 0;
    vibe1.amp = 0;
    vibe1.channel = 1;
    vibe1.delta = 2621;
    vibe1.offset = 0;
    vibe1.phase = 0;
    vibe1.timebase = 0;

    vibe2.arg = 0;
    vibe2.amp = 0;
    vibe2.channel = 1;
    vibe2.delta = 2621;
    vibe2.offset = 0;
    vibe2.phase = 0;
    vibe2.timebase = 0;

    //Set up timer
    //SetupTimer1();
    //T1CONbits.TON = 1;
    //_T1IE = 1;
}

//TODO: rewrite
void amsVibeStart(void) {
    //_OC1IE = 1;
    //TMR3 = 0; //reset timer counter, so sin arg starts at 0
    //T3CONbits.TON = 1;
    //_T3IE = 1;
}

//TODO: rewrite
void amsVibeStop(void) {
    //_OC1IE = 0;
    //T3CONbits.TON = 0;
}

void amsVibeSetFrequency(unsigned int channel, unsigned int incr) {

     if (channel == 1) {
        //chan1_delta = incr;
        vibe1.delta = incr;
    } else if (channel == 2) {
        //chan2_delta = incr;
        vibe2.delta = incr;
    }

}

void amsVibeSetAmplitude(unsigned int channel, unsigned int amp) {
    if (channel == 1) {
        //chan1amp = amp;
        vibe1.amp = amp;
    } else if (channel == 2) {
        //chan2amp = amp;
        vibe2.amp = amp;
    }

    if((vibe1.amp != 0) || (vibe2.amp != 0)){
        running = 1;
    }
    else{
        running = 0;
        vibe1.timebase = 0;
        vibe2.timebase = 0;
    }

}

void amsVibeSetOffset(unsigned int channel, int off) {
    if (channel == 1) {
        //chan1off = off;
        vibe1.offset = off;
    } else if (channel == 2) {
        //chan2off = off;
        vibe2.offset = off;
    }
    
}

//void amsVibeSetAmplitudeFloat(unsigned int channel, float famp) {
    //unimplemented
//}

void amsVibeSetPhase(unsigned int channel, _Q15 phase) {
    //phase should be a _Q15, correpsonding to [-pi, pi]

    if (channel == 1) {
        //chan1arg += phase;
        vibe1.phase = phase;
    } else if (channel == 2) {
        //chan2arg += phase;
        vibe2.phase = phase;
    }

}


int amsVibeGetOutput(unsigned int channel){
    if (channel == 1) {
        return vibe1.out;
    }
    if (channel == 2) {
        return vibe2.out;
    }

    return 0;
}

//Private funcitons

//This could be called from an external task, scheduler, etc.
//Currently just called below in T1 interrupt.
void amsVibeUpdate() {

    if (running) {
        update_vibe_synth();
        //BYPASS FOR TESTING
        //tiHSetDC(vibe1.channel, vibe1.dc);
        //tiHSetDC(vibe2.channel, vibe2.dc);
        //tiHSetDC(1, chan1dc);
        //tiHSetDC(2, chan2dc);
    } else {
        vibe1.out = 0;
        vibe2.out = 0;
        //tiHSetDC(vibe1.channel, 0);
        //tiHSetDC(vibe2.channel, 0);
        //tiHSetDC(1, 0);
        //tiHSetDC(2, 0);
    }
}


static void update_vibe_synth() {
    vibe1.timebase += vibe1.delta;
    vibe1.arg = vibe1.timebase + vibe1.phase;

    vibe2.timebase += vibe2.delta;
    vibe2.arg = vibe2.timebase + vibe2.phase;
    //chan1arg += chan1_delta;
    //chan2arg += chan2_delta;

    long temp;

    temp = _Q15sinPI(vibe1.arg);
    temp *= (long) vibe1.amp;
    temp = (int) (temp >> 15); //shift back to Q15 format
    vibe1.out = _Q15add((_Q15)temp, (_Q15)vibe1.offset); // Add offset with saturation

    temp = _Q15sinPI(vibe2.arg);
    temp *= (long) vibe2.amp;
    temp = (int) (temp >> 15); //shift back to Q15 format
    vibe2.out = _Q15add((_Q15)temp, (_Q15)vibe2.offset); // Add offset with saturation

    //chan1dc = _Q15sinPI(chan1arg);
    //long temp = (long)(chan1dc) * (long)chan1amp;
    //chan1dc = (int)(temp >> 15);

    //chan2dc = _Q15sinPI(chan2arg);
    //temp = (long)(chan2dc) * (long)chan2amp;
    //chan2dc = (int)(temp >> 15);
}


//This is largely copied from pid-ip2.5
static volatile unsigned char interrupt_count = 0;
static volatile unsigned long t1_ticks;
#define T1_MAX 0xffffff  // max before rollover of 1 ms counter

/*
void __attribute__((interrupt, no_auto_psv)) _T1Interrupt(void) {
    interrupt_count++;

    //interrupt_count == 1 , do nothing
    //interrupt_count == 2 , do nothing

    //Telemetry save, at 1Khz
    //TODO: Break coupling between PID module and telemetry triggering
    if (interrupt_count == 3) {
        telemSaveNow();
    }
    //Update IMU , AMS encoders
    //TODO: Break coupling between PID module and IMU update
    if (interrupt_count == 4) {
        mpuBeginUpdate();
        amsEncoderStartAsyncRead();
    } //PID controller update
    if (interrupt_count == 5) {
        interrupt_count = 0;

        if (t1_ticks == T1_MAX) t1_ticks = 0;
        t1_ticks++;

        amsVibeUpdate();
    }

    _T1IF = 0;
}
*/

/*
static void SetupTimer1(void)
{
    unsigned int T1CON1value, T1PERvalue;
    T1CON1value = T1_ON & T1_SOURCE_INT & T1_PS_1_8 & T1_GATE_OFF &
                  T1_SYNC_EXT_OFF & T1_INT_PRIOR_2;
    T1PERvalue = 0x03E8; //clock period = 0.0002s = ((T1PERvalue * prescaler)/FCY) (5000Hz)
  	t1_ticks = 0;
    OpenTimer1(T1CON1value, T1PERvalue);
}
 */