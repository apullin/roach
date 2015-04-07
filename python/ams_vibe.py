#!/usr/bin/env python
"""
authors: apullin

Contents of this file are copyright Andrew Pullin, 2013

"""
from lib import command
import time,sys,os
import serial

# Path to imageproc-settings repo must be added
sys.path.append(os.path.dirname("../../imageproc-settings/"))
sys.path.append(os.path.dirname("../imageproc-settings/"))  
import shared_multi as shared

from velociroach import *


###### Operation Flags ####
RESET_R1     = True  
SAVE_DATA_R1 = True  # CURRENTLY BROKEN HERE
EXIT_WAIT    = False

def main():    
    xb = setupSerial(shared.BS_COMPORT, shared.BS_BAUDRATE)
    
    R1 = Velociroach('\x20\x52', xb)
    R1.RESET = RESET_R1
    R1.SAVE_DATA = SAVE_DATA_R1
    
    shared.ROBOTS = [R1] #This is neccesary so callbackfunc can reference robots
    shared.xb = xb           #This is neccesary so callbackfunc can halt before exit

    if R1.RESET:
        R1.reset()
        time.sleep(0.35)
    
    # Query
    R1.query( retries = 8 )
    
    #Verify all robots can be queried
    verifyAllQueried()  #exits on failure

    EXPERIMENT_RUN_TIME_MS     = 2000  #ms
    EXPERIMENT_LEADIN_TIME_MS  = 0  #ms
    EXPERIMENT_LEADOUT_TIME_MS = 0  #ms
    
    if R1.SAVE_DATA:
        R1.setupTelemetryDataTime(EXPERIMENT_LEADIN_TIME_MS + EXPERIMENT_RUN_TIME_MS + EXPERIMENT_LEADOUT_TIME_MS)
    
    raw_input("Press enter to start vibe...")
    
    if R1.SAVE_DATA:
        R1.startTelemetrySave()
        
    print "len R1.telemetryData=",R1.numSamples
    print "len(R1.telemetryData)=",len(R1.telemetryData)
    
    time.sleep(EXPERIMENT_LEADIN_TIME_MS/1000.0) #leadin
    
    ZERO_PHASE = 0
    freqL = 10
    freqR = 20
    amp = 2000
    R1.setAMSvibe(1, freqL, amp, offset = 0, phase = ZERO_PHASE)
    R1.setAMSvibe(2, freqR, amp, offset = 500, phase = ZERO_PHASE)
    time.sleep( R1.runtime/1000.0 )
    R1.setAMSvibe(1, freqL, 0, phase = ZERO_PHASE)
    R1.setAMSvibe(2, freqR, 0, phase = ZERO_PHASE)
    
    time.sleep(EXPERIMENT_LEADOUT_TIME_MS/1000.0) #leadout
    
    for r in shared.ROBOTS:
        if r.SAVE_DATA:
            raw_input("Press Enter to start telemetry read-back ...")
            r.downloadTelemetry()

    if EXIT_WAIT:  #Pause for a Ctrl + Cif specified
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break

    print "Done"
	
	
#Provide a try-except over the whole main function
# for clean exit. The Xbee module should have better
# provisions for handling a clean exit, but it doesn't.
#TODO: provide a more informative exit here; stack trace, exception type, etc
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print "\nRecieved Ctrl+C, exiting."
    except Exception as args:
        print "\nGeneral exception from main:\n",args,'\n'
        print "\n    ******    TRACEBACK    ******    "
        traceback.print_exc()
        print "    *****************************    \n"
        print "Attempting to exit cleanly..."
    finally:
        xb_safe_exit(shared.xb)
