#!/usr/bin/env python
"""
authors: apullin

Contents of this file are copyright Andrew Pullin, 2013

"""
from lib import command
import time,sys,os
import serial
import numpy as np

# Path to imageproc-settings repo must be added
sys.path.append(os.path.dirname("../../imageproc-settings/"))
sys.path.append(os.path.dirname("../imageproc-settings/"))  
import shared_multi as shared

from velociroach import *


###### Operation Flags ####
RESET_R1     = True  
SAVE_DATA_R1 = False
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
    
    motorgains = [1500,0,0,0,0, 1500,0,0,0,0]
    #motorgains = [0,0,0,0,0, 0,0,0,0,0]
    R1.setMotorGains(motorgains)
    
    # example , 0.1s lead in + 2s run + 0.1s lead out
    EXPERIMENT_RUN_TIME_MS     = 3000 #ms
    EXPERIMENT_LEADIN_TIME_MS  = 100  #ms
    EXPERIMENT_LEADOUT_TIME_MS = 100  #ms
    
    # Some preparation is needed to cleanly save telemetry data
    for r in shared.ROBOTS:
        if r.SAVE_DATA:
            #This needs to be done to prepare the .telemetryData variables in each robot object
            r.setupTelemetryDataTime(EXPERIMENT_LEADIN_TIME_MS + EXPERIMENT_RUN_TIME_MS + EXPERIMENT_LEADOUT_TIME_MS)
            r.eraseFlashMem()
    
    
    PHASE_ZERO = 0
    PHASE_180 = 1.0
    freqL = 25
    freqR = 25
    #amp = 2000
    #R1.setAMSvibe(channel=1, frequency=freqL, amplitude = 5000, offset = 0, phase = PHASE_ZERO)
    #R1.setAMSvibe(channel=2, frequency=freqR, amplitude = 5000, offset = 0, phase = PHASE_ZERO)
    
    
    
    # Sleep for a lead-in time before any motion commands
    time.sleep(EXPERIMENT_LEADIN_TIME_MS / 1000.0)
    
    DEADTIME = 6.0
    
    freqs = [10, 15, 20, 25, 30, 35]
    nrep = 5;
    
    flist = np.array([[i]*nrep for i in freqs]).flatten().tolist()
    
    nruns = len(flist)
    est_time = nruns * (EXPERIMENT_LEADIN_TIME_MS + EXPERIMENT_LEADOUT_TIME_MS + EXPERIMENT_RUN_TIME_MS)/1000.0 + (nruns-1)*DEADTIME
    print
    
    print "Total estimated time:", est_time,"seconds,",nruns,"trials."
    
    print "\n  ***************************\n  *******    READY    *******\n  Press ENTER to start run ...\n  ***************************"
    raw_input("")
    
    for f in flist:
        freqL = f
        freqR = f
        #amp = 2000
        R1.setAMSvibe(channel=1, frequency=freqL, amplitude = 5000, offset = 0, phase = PHASE_ZERO)
        R1.setAMSvibe(channel=2, frequency=freqR, amplitude = 5000, offset = 0, phase = PHASE_ZERO)
        
        # Sleep for a lead-in time before any motion commands
        time.sleep(EXPERIMENT_LEADIN_TIME_MS / 1000.0)
        R1.startTimedRun( EXPERIMENT_RUN_TIME_MS ) #Faked for now, since pullin doesn't have a working VR+AMS to test with
        time.sleep(EXPERIMENT_RUN_TIME_MS / 1000.0)  #argument to time.sleep is in SECONDS
        
        #dead time between runs
        time.sleep(DEADTIME)

    # Initiate telemetry recording; the robot will begin recording immediately when cmd is received.
    for r in shared.ROBOTS:
        if r.SAVE_DATA:
            r.startTelemetrySave()
    
    time.sleep(EXPERIMENT_LEADOUT_TIME_MS / 1000.0) 
    
    for r in shared.ROBOTS:
        if r.SAVE_DATA:
            raw_input("Press Enter to start telemetry read-back ...")
            r.downloadTelemetry()
    
    if EXIT_WAIT:  #Pause for a Ctrl + C , if desired
        while True:
            time.sleep(0.1)

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
