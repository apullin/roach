#!/usr/bin/env python
"""
authors: apullin

This script will run a VelociRoACH roach in open-loop (PWM) mode, based off a joystick input.

"""
from lib import command
import time,sys,os,traceback
import serial
import shared_multi as shared
import pygame

from velociroach import *

####### Wait at exit? #######
EXIT_WAIT   = False

MAXTHROT = 2000

BUTTON_Y = 3
BUTTON_B = 1
BUTTON_L1 = 6
BUTTON_R1 = 8
BUTTON_X = 2
BUTTON_A = 0

def main():
    global MAXTHROT    
    xb = setupSerial(shared.BS_COMPORT, shared.BS_BAUDRATE)
    
    R1 = Velociroach('\x20\x52', xb)
    R1.SAVE_DATA = False
                            
    #R1.RESET = False       #current roach code does not support software reset
    
    shared.ROBOTS.append(R1) #This is necessary so callbackfunc can reference robots
    shared.xb = xb           #This is necessary so callbackfunc can halt before exit

    # Send robot a WHO_AM_I command, verify communications
    for r in shared.ROBOTS:
        r.query(retries = 3)
    
    #Verify all robots can be queried
    #verifyAllQueried()  # exits on failure
    
    # Motor gains format:
    #  [ Kp , Ki , Kd , Kaw , Kff     ,  Kp , Ki , Kd , Kaw , Kff ]
    #    ----------LEFT----------        ---------_RIGHT----------
    motorgains = [1800,0,100,0,0, 1800,0,100,0,0]
    #motorgains = [0,0,0,0,0 , 0,0,0,0,0]
    
    j = setupJoystick()
    
    lastthrot = [0, 0]
    
    tinc = 25;
    olVibeFreq = 20;
    vinc = 2.5;
    LAST_BUTTON_R1 = 0;

    while True:

        value = []
        pygame.event.pump()
        
        #max throttle increase/decrease buttons
        if j.get_button(BUTTON_L1) == 1 and MAXTHROT > 0:
                MAXTHROT = MAXTHROT - 100
        elif j.get_button(BUTTON_R1) ==1 and MAXTHROT < 4000:
                MAXTHROT = MAXTHROT + 100
        
        left_throt = -j.get_axis(2)
        right_throt = -j.get_axis(1)
        #right_throt = -j.get_axis(0)
        if abs(left_throt) < 0.05:
            left_throt = 0
        if abs(right_throt) < 0.05:
            right_throt = 0
        left_throt = int(MAXTHROT * left_throt)
        right_throt = int(MAXTHROT * right_throt)
        
        sys.stdout.write(" "*60 + "\r")
        sys.stdout.flush()
        outstring = "L: {0:3d}  |   R: {1:3d}   MAX:{2:3d}\r".format(left_throt,right_throt,MAXTHROT)
        sys.stdout.write(outstring)
        sys.stdout.flush()
        
        R1.setThrustPWMOpenLoop([left_throt,right_throt])
        

        time.sleep(0.1)
    
    
    if EXIT_WAIT:  #Pause for a Ctrl + C , if desired
        while True:
            try:
                time.sleep(0.1)
            except KeyboardInterrupt:
                break

    print "Done"
    xb_safe_exit(xb)

    
def setupJoystick():
    try:
        pygame.init()
        j = pygame.joystick.Joystick(0)
        j.init()
        print j.get_name()
    except Exception as args:
        print 'No joystick'
        print 'Exception: ', args
        xb_safe_exit()
        
    return j

    
#Provide a try-except over the whole main function
# for clean exit. The Xbee module should have better
# provisions for handling a clean exit, but it doesn't.
#TODO: provide a more informative exit here; stack trace, exception type, etc
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print "\nRecieved Ctrl+C, exiting."
        shared.xb.halt()
        shared.ser.close()
    except Exception as args:
        print "\nGeneral exception:",args
        print "\n    ******    TRACEBACK    ******    "
        traceback.print_exc()
        print "    *****************************    \n"
        print "Attempting to exit cleanly..."
        shared.xb.halt()
        shared.ser.close()
        sys.exit()
    except serial.serialutil.SerialException:
        shared.xb.halt()
        shared.ser.close()
