//vr_telem.c , VelociRoACH specific telemetry packet format

// XC compiler include
#include <xc.h>

// Project settings
#include "settings.h"

// imageproc-lib includes
#include "utils.h"
#include "vr_telem.h"
#include "mpu6000.h"
#include "adc_pid.h"
#include "tih.h"
#include "ams-enc.h"
#include "pid-ip2.5.h"


// TODO (apullin) : Remove externs by adding getters to other modules
//extern pidObj motor_pidObjs[NUM_MOTOR_PIDS];
//extern int bemf[NUM_MOTOR_PIDS];

//externs added back in for VR telem porting (pullin 10/9/14)
//extern int bemf[NUM_PIDS];
//extern pidPos pidObjs[NUM_PIDS];

//void vrTelemGetData(unsigned char* ptr) {
void vrTelemGetData(vrTelemStruct_t* ptr) {

    int gdata[3];   //gyrodata
    int xldata[3];  // accelerometer data
    /////// Get XL data
    mpuGetGyro(gdata);
    mpuGetXl(xldata);

    ptr->posL = pidGetPState(LEFT_LEGS_PID_NUM);
    ptr->posR = pidGetPState(RIGHT_LEGS_PID_NUM);
    ptr->composL = pidGetPInput(LEFT_LEGS_PID_NUM) + pidGetInterpolate(LEFT_LEGS_PID_NUM);
    ptr->composR = pidGetPInput(RIGHT_LEGS_PID_NUM) + pidGetInterpolate(RIGHT_LEGS_PID_NUM);
    ptr->dcL = pidGetOutput(LEFT_LEGS_PID_NUM); // left
    ptr->dcR = pidGetOutput(RIGHT_LEGS_PID_NUM); // right
    ptr->bemfL = pidGetBEMF(LEFT_LEGS_PID_NUM);
    ptr->bemfR = pidGetBEMF(RIGHT_LEGS_PID_NUM);

    ptr->gyroX = gdata[0];
    ptr->gyroY = gdata[1];
    ptr->gyroZ = gdata[2];
    ptr->accelX = xldata[0];
    ptr->accelY = xldata[1];
    ptr->accelZ = xldata[2];
    ptr->Vbatt = (int) adcGetVbatt();
}

//This may be unneccesary, since the telemtry type isn't totally anonymous

unsigned int vrTelemGetSize() {
    return sizeof (vrTelemStruct_t);
}