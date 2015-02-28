/* 
 * File:   bclock.h
 * Author: pullin
 *
 * Created on February 23, 2015, 12:53 PM
 */

#ifndef BCLOCK_H
#define	BCLOCK_H

// Phase defs
#define PHASE_0_DEG   0x0000;
#define PHASE_180_DEG 0x7FFF;

// Frequency defs
#define BCLOCK_INCR_1HZ      52;
#define BCLOCK_INCR_2HZ     104;
#define BCLOCK_INCR_3HZ     157;
#define BCLOCK_INCR_4HZ     210;
#define BCLOCK_INCR_5HZ     262;
#define BCLOCK_INCR_6HZ     315;
#define BCLOCK_INCR_7HZ     367;
#define BCLOCK_INCR_8HZ     419;
#define BCLOCK_INCR_9HZ     472;
#define BCLOCK_INCR_10HZ    524;
#define BCLOCK_INCR_11HZ    577;
#define BCLOCK_INCR_12HZ    629;
#define BCLOCK_INCR_13HZ    682;
#define BCLOCK_INCR_14HZ    734;
#define BCLOCK_INCR_15HZ    786;

typedef struct{
    unsigned int speed_td;
    unsigned int phase;
    unsigned int incr;
    unsigned int period;
    unsigned int arg;
    unsigned int sp;
} bclock_t;

void blockSetup();

void bclockSetParams(bclock_t* params);
void bclockGetParams(bclock_t* buf);

void bclockUpdate(unsigned int time);
void bclockGetSetpoint(int* sp1, int* sp2);

#endif	/* BCLOCK_H */
