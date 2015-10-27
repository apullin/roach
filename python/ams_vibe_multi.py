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
    
    motorgains = [2000,0,0,0,0, 2000,0,0,0,0]
    #motorgains = [0,0,0,0,0, 0,0,0,0,0]
    R1.setMotorGains(motorgains)
    
    # example , 0.1s lead in + 2s run + 0.1s lead out
    #EXPERIMENT_RUN_TIME_MS     = 6000 #ms
    EXPERIMENT_LEADIN_TIME_MS  = 250  #ms
    EXPERIMENT_LEADOUT_TIME_MS = 250  #ms
    DEADTIME = 3000
    
    PHASE_ZERO = 0
    PHASE_90 = 0.5
    PHASE_180 = 1.0
    
    #freqs = [10, 13, 16, 19, 22, 25, 28, 31]
    #freqs = [1,1.5,2,2.5]
    freqs = [0.5,1,1.5,2,3,4,5,6,7,8,9,10,12,14,16,18,20,25]
    times = [15000]*4 + [10000]*10 + [8000]*4
    #freqs = [5,6,7]
    #times = [5000]*3
    nrep = 1
    
    
    flist = np.array([[i]*nrep for i in freqs]).flatten().tolist()
    pairs = zip(flist, times)
    
    nruns = len(flist)
    
    est_time = (sum(times) + EXPERIMENT_LEADIN_TIME_MS + EXPERIMENT_LEADOUT_TIME_MS + nruns*DEADTIME)/1000.0
    
    print "Total estimated time:", est_time,"seconds,",nruns,"trials."
    
    # Some preparation is needed to cleanly save telemetry data
    for r in shared.ROBOTS:
        if r.SAVE_DATA:
            #This needs to be done to prepare the .telemetryData variables in each robot object
            r.setupTelemetryDataTime(est_time*1000, samp_freq = 500.0)
            r.eraseFlashMem(timeout = 100)
    
    
    print "!!!!!!!  SYSTEM INIT: ROBOT WILL MOVE BRIEFLY  !!!!!!!"
    raw_input("")
    R1.setAMSvibe(channel=1, frequency=1, amplitude = 0, offset = 0, phase = PHASE_ZERO)
    R1.setAMSvibe(channel=2, frequency=1, amplitude = 0, offset = 0, phase = PHASE_ZERO)
    R1.startTimedRun( 2000 )
    time.sleep(2.5)
    
    print ""
    print "****************************"
    print "*******    READY    ********"
    print "Press ENTER to start run ..."
    print "****************************\n"
    raw_input("")
    
    print "Dead time to start force sensor acq ..."
    time.sleep(5.0)
    
    # Initiate telemetry recording; the robot will begin recording immediately when cmd is received.
    for r in shared.ROBOTS:
        if r.SAVE_DATA:
            r.startTelemetrySave()
    
    time.sleep(EXPERIMENT_LEADIN_TIME_MS / 1000.0)
    
    for f,t in pairs:        
        EXPERIMENT_RUN_TIME_MS = t
        freqL = f
        freqR = f
        #amp = 2000
        print "Running @ freq = {",freqL,",",freqR,"} for t=",EXPERIMENT_RUN_TIME_MS," ms"
        R1.setAMSvibe(channel=1, frequency=freqL, amplitude = 3000, offset = 3000, phase = PHASE_ZERO)
        R1.setAMSvibe(channel=2, frequency=freqR, amplitude = 3000, offset = 3000, phase = PHASE_ZERO)
        
        # Sleep for a lead-in time before any motion commands
        R1.startTimedRun( EXPERIMENT_RUN_TIME_MS ) #Faked for now, since pullin doesn't have a working VR+AMS to test with
        time.sleep(EXPERIMENT_RUN_TIME_MS / 1000.0)  #argument to time.sleep is in SECONDS
        
        #dead time between runs
        time.sleep(DEADTIME/1000.0)
        
    
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
