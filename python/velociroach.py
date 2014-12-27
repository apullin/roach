import glob,time,sys,datetime
from lib import command
from callbackFunc import xbee_received
import serial
import shared                       #this is now only COMPORT settings and baudrate settings
from struct import pack,unpack
from math import floor
import numpy as np

# TODO: check with firmware if this value is actually correct
PHASE_180_DEG = 0x8000

class GaitConfig:
    motorgains = None
    duration = None
    rightFreq = None
    leftFreq = None
    phase = None
    repeat = None
    deltasLeft = None
    deltasRight = None
    
    def __init__(self, motorgains = None, duration = None, rightFreq = None, leftFreq = None, phase = None, repeat = None):
        if motorgains == None:
            self.motorgains = [0,0,0,0,0 , 0,0,0,0,0]
        else:
            self.motorgains = motorgains
        
        self.duration = duration
        self.rightFreq = rightFreq
        self.leftFreq = leftFreq
        self.phase = phase
        self.repeat = repeat
         
        
class Velociroach:
    motor_gains_set = False
    robot_queried = False
    flash_erased = False
    
    currentGait = GaitConfig()

    dataFileName = ''
    telemtryData = [ [] ]
    numSamples = 0
    telemSampleFreq = 1000
    VERBOSE = True
    telemFormatString = '%d' # single type forces all data to be saved in this type
    SAVE_DATA = False
    RESET = False

    def __init__(self, address, xbee):
            self.DEST_ADDR = address
            self.DEST_ADDR_int = unpack('>h',self.DEST_ADDR)[0] #address as integer
            
            if xbee == None:
                raise Exception("Robot must be declared with xbee in argument")
            
            if not xbee.ser.isOpen():
                raise Exception("Xbee connection is not open!")
        
            #Store xbee object for use for sending            
            self.xbee = xbee
            #Add robot to list of robots in BaseStation object
            self.xbee.associateRobot(self)
            #TODO: Cyclic dependency? self.xbee -> xbee, xbee->ROBOT[i]->self ?
            
            print "Robot with DEST_ADDR = 0x%04X " % self.DEST_ADDR_int

    def clAnnounce(self):
        print "DST: 0x%02X | " % self.DEST_ADDR_int,
    
    #Now done via a call to BaseStation sendTX function
    #def tx(self, status, type, data):
    #    payload = chr(status) + chr(type) + ''.join(data)
    #    self.xbee.tx(dest_addr = self.DEST_ADDR, data = payload)
        
    def reset(self):
        self.clAnnounce()
        print "Resetting robot..."
        self.xbee.sendTX( 0, command.SOFTWARE_RESET, pack('h',1))
        
    def sendEcho(self, msg):
        self.xbee.sendTX( 0, command.ECHO, msg)
        
    def query(self, retries = 8):
        self.robot_queried = False
        tries = 1
        while not(self.robot_queried) and (tries <= retries):
            self.clAnnounce()
            print "Querying robot , ",tries,"/",retries
            self.xbee.sendTX( 0,  command.WHO_AM_I, "Robot Echo") #sent text is unimportant
            tries = tries + 1
            time.sleep(0.1)   
    
    #TODO: getting flash erase to work is critical to function testing (pullin)    
    #existing VR firmware does not send a packet when the erase is done, so this will hang and retry.
    def eraseFlashMem(self, timeout = 8):
        eraseStartTime = time.time()
        self.xbee.sendTX( 0, command.ERASE_SECTORS, pack('L',self.numSamples))
        self.clAnnounce()
        print "Started flash erase ..."
        while not (self.flash_erased):
            #sys.stdout.write('.')
            time.sleep(0.25)
            if (time.time() - eraseStartTime) > timeout:
                print"Flash erase timeout, retrying;"
                self.xbee.sendTX( 0, command.ERASE_SECTORS, pack('L',self.numSamples))
                eraseStartTime = time.time()    
        
    def setPhase(self, phase):
        self.clAnnounce()
        print "Setting phase to 0x%04X " % phase
        self.xbee.sendTX( 0, command.SET_PHASE, pack('l', phase))
        time.sleep(0.05)        
    
    def startTimedRun(self, duration):
        self.clAnnounce()
        print "Starting timed run of",duration," ms"
        self.xbee.sendTX( 0, command.START_TIMED_RUN, pack('h', duration))
        time.sleep(0.05)
        
    def findFileName(self):   
        # Construct filename
        path     = 'Data/'
        name     = 'trial'
        datetime = time.localtime()
        dt_str   = time.strftime('%Y.%m.%d_%H.%M.%S', datetime)
        root     = path + dt_str + '_' + name
        self.dataFileName = root + '_imudata.txt'
        #self.clAnnounce()
        #print "Data file:  ", shared.dataFileName
        
    def setVelProfile(self, gaitConfig):
        self.clAnnounce()
        print "Setting stride velocity profile to: "
        
        periodLeft = 1000.0 / gaitConfig.leftFreq
        periodRight = 1000.0 / gaitConfig.rightFreq
        
        deltaConv = 0x4000 # TODO: this needs to be clarified (ronf, dhaldane, pullin)
        
        lastLeftDelta = 1-sum(gaitConfig.deltasLeft) #TODO: change this to explicit entry, with a normalization here
        lastRightDelta = 1-sum(gaitConfig.deltasRight)
        
        temp = [int(periodLeft), int(gaitConfig.deltasLeft[0]*deltaConv), int(gaitConfig.deltasLeft[1]*deltaConv),
                int(gaitConfig.deltasLeft[2]*deltaConv), int(lastLeftDelta*deltaConv) , 0, \
                int(periodRight), int(gaitConfig.deltasRight[0]*deltaConv), int(gaitConfig.deltasRight[1]*deltaConv),
                int(gaitConfig.deltasRight[2]*deltaConv), int(lastRightDelta*deltaConv), 0]
        
        self.clAnnounce()
        print "     ",temp
        
        self.xbee.sendTX( 0, command.SET_VEL_PROFILE, pack('12h', *temp))
        time.sleep(0.1)
    
    #TODO: This may be a vestigial function. Check versus firmware.
    def setMotorMode(self, mode):
        self.clAnnounce()
        print "Setting motor mode to", mode
        self.xbee.sendTX( 0, command.SET_MOTOR_MODE, pack('h',mode))
        time.sleep(0.1)
            
    def setZeroMotorPosition(self):
        self.clAnnounce()
        print "Zeroing motor position"
        self.xbee.sendTX( 0, command.ZERO_POS, "Zero motor")
    
    ######TODO : sort out this function and flashReadback below
    def downloadTelemetry(self, timeout = 5, retry = True):
        #suppress callback output messages for the duration of download
        self.VERBOSE = False
        self.clAnnounce()
        print "Started telemetry download"
        self.xbee.sendTX( 0, command.FLASH_READBACK, pack('=L',self.numSamples))
                
        dlStart = time.time()
        shared.last_packet_time = dlStart
        #bytesIn = 0
        while self.telemtryData.count([]) > 0:
            time.sleep(0.04)
            dlProgress(self.numSamples - self.telemtryData.count([]) , self.numSamples)
            if (time.time() - shared.last_packet_time) > timeout:
                print ""
                #Terminal message about missed packets
                self.clAnnounce()
                print "Readback timeout exceeded"
                print "Missed", self.telemtryData.count([]), "packets."
                #print "Didn't get packets:"
                #for index,item in enumerate(self.telemtryData):
                #    if item == []:
                #        print "#",index+1,
                print "" 
                break
                # Retry telem download            
                if retry == True:
                    raw_input("Press Enter to restart telemetry readback ...")
                    self.telemtryData = [ [] ] * self.numSamples
                    self.clAnnounce()
                    print "Started telemetry download"
                    dlStart = time.time()
                    shared.last_packet_time = dlStart
                    self.xbee.sendTX( 0, command.FLASH_READBACK, pack('=L',self.numSamples))
                else: #retry == false
                    print "Not trying telemetry download."          

        dlEnd = time.time()
        dlTime = dlEnd - dlStart
        #Final update to download progress bar to make it show 100%
        dlProgress(self.numSamples-self.telemtryData.count([]) , self.numSamples)
        #totBytes = 52*self.numSamples
        totBytes = 52*(self.numSamples - self.telemtryData.count([]))
        datarate = totBytes / dlTime / 1000.0
        print '\n'
        #self.clAnnounce()
        #print "Got ",self.numSamples,"samples in ",dlTime,"seconds"
        self.clAnnounce()
        print "DL rate: {0:.2f} KB/s".format(datarate)
        
        #enable callback output messages
        self.VERBOSE = True

        print ""
        self.saveTelemetryData()
        #Done with flash download and save

    def saveTelemetryData(self):
        self.findFileName()
        self.writeFileHeader()
        fileout = open(self.dataFileName, 'a')
        sanitized = [item for item in self.telemtryData if item]
        np.savetxt(fileout , np.array(sanitized), self.telemFormatString, delimiter = ',')
        #np.savetxt(fileout , np.array(self.telemtryData), self.telemFormatString, delimiter = ',')
        fileout.close()
        self.clAnnounce()
        print "Telemetry data saved to", self.dataFileName
        
    def writeFileHeader(self):
        fileout = open(self.dataFileName,'w')
        #write out parameters in format which can be imported to Excel
        today = time.localtime()
        date = str(today.tm_year)+'/'+str(today.tm_mon)+'/'+str(today.tm_mday)+'  '
        date = date + str(today.tm_hour) +':' + str(today.tm_min)+':'+str(today.tm_sec)
        fileout.write('%  Data file recorded ' + date + '\n')

        fileout.write('%  Stride Frequency         = ' +repr( [ self.currentGait.leftFreq, self.currentGait.leftFreq]) + '\n')
        fileout.write('%  Lead In /Lead Out        = ' + '\n')
        fileout.write('%  Deltas (Fractional)      = ' + repr(self.currentGait.deltasLeft) + ',' + repr(self.currentGait.deltasRight) + '\n')
        fileout.write('%  Phase                    = ' + repr(self.currentGait.phase) + '\n')
            
        fileout.write('%  Experiment.py \n')
        fileout.write('%  Motor Gains    = ' + repr(self.currentGait.motorgains) + '\n')
        fileout.write('% Columns: \n')
        # order for wiring on RF Turner
        fileout.write('% time | Right Leg Pos | Left Leg Pos | Commanded Right Leg Pos | Commanded Left Leg Pos | DCR | DCL | GyroX | GryoY | GryoZ | AX | AY | AZ | RBEMF | LBEMF | VBatt\n')
        fileout.close()

    def setupTelemetryDataTime(self, runtime):
        ''' This is NOT current for Velociroach! '''
        #TODO : update for Velociroach
        
        # Take the longer number, between numSamples and runTime
        nrun = int(self.telemSampleFreq * runtime / 1000.0)
        self.numSamples = nrun
        
        #allocate an array to write the downloaded telemetry data into
        self.telemtryData = [ [] ] * self.numSamples
        self.clAnnounce()
        print "Telemetry samples to save: ",self.numSamples
        
    def setupTelemetryDataNum(self, numSamples):
        ''' This is NOT current for Velociroach! '''
        #TODO : update for Velociroach
     
        self.numSamples = numSamples
        
        #allocate an array to write the downloaded telemetry data into
        self.telemtryData = [ [] ] * self.numSamples
        self.clAnnounce()
        print "Telemetry samples to save: ",self.numSamples
    
    def startTelemetrySave(self):
        self.clAnnounce()
        print "Started telemetry save of", self.numSamples," samples."
        self.xbee.sendTX(0, command.START_TELEMETRY, pack('L',self.numSamples))

    def setMotorGains(self, gains, retries = 8):
        tries = 1
        self.motorGains = gains
        while not(self.motor_gains_set) and (tries <= retries):
            self.clAnnounce()
            print "Setting motor gains...   ",tries,"/8"
            self.xbee.sendTX( 0, command.SET_PID_GAINS, pack('10h',*gains))
            tries = tries + 1
            time.sleep(0.3)
            
    def setGait(self, gaitConfig):
        self.currentGait = gaitConfig
        
        self.clAnnounce()
        print " --- Setting complete gait config --- "
        self.setPhase(gaitConfig.phase)
        self.setMotorGains(gaitConfig.motorgains)
        self.setVelProfile(gaitConfig) #whole object is passed in, due to several references
        self.setZeroMotorPosition()
        
        self.clAnnounce()
        print " ------------------------------------ "
        
    
    ############ Interal Radio Callback ############
    def callbackHandler(self, packet):
        #Here, packet addressing is already checked by the raio

        #Dictionary of packet formats, for unpack()
        #TODO: this should be moved to lib.command
        pktFormat = { \
            command.TX_DUTY_CYCLE:          'l3f', \
            command.GET_IMU_DATA:           'l6h', \
            command.TX_SAVED_STATE_DATA:    'l3f', \
            command.SET_THRUST_OPEN_LOOP:   '', \
            command.PID_START_MOTORS:       '', \
            command.SET_PID_GAINS:          '10h', \
            command.GET_PID_TELEMETRY:      '', \
            command.GET_AMS_POS:            '=2l', \
            command.GET_IMU_LOOP_ZGYRO:     '='+2*'Lhhh', \
            command.SET_MOVE_QUEUE:         '', \
            command.SET_STEERING_GAINS:     '6h', \
            command.SOFTWARE_RESET:         '', \
            command.ERASE_SECTORS:          'L', \
            command.FLASH_READBACK:         '=LL' +'4l'+'11h', \
            command.SLEEP:                  'b', \
            command.ECHO:                   'c' ,\
            command.SET_VEL_PROFILE:        '8h' ,\
            command.WHO_AM_I:               '', \
            }
        #TODO: command.FLASH_READBACK needs automatic correspondence with self.telemFormatString   

        rf_data = packet.get('rf_data')
        #rssi = ord(packet.get('rssi'))
        (src_addr, ) = unpack('>H', packet.get('source_addr'))
        #id = packet.get('id')
        #options = ord(packet.get('options'))
        
        #Only print pertinent SRC lines
        #This also allows us to turn off messages on the fly, for telem download
        if r.VERBOSE:
            print "SRC: 0x%04X | " % src_addr,
       
        status = ord(rf_data[0])
        type = ord(rf_data[1])
        data = rf_data[2:]
          
        #Record the time the packet is received, so command timeouts
        # can be done
        shared.last_packet_time = time.time()
        
        try:
            pattern = pktFormat[type]
        except KeyError:
            print "Got bad packet type: ",type
            return
        
        #TODO: change command handlers to a dictionary; xbee lib does this, use as example?
        try:
            # ECHO
            if type == command.ECHO:
                print "echo: status = ",status," type=",type," data = ",data
                
            # SET_PID_GAINS
            elif type == command.SET_PID_GAINS:
                gains = unpack(pattern, data)
                print "Set motor gains to ", gains
                self.motor_gains_set = True
            
            # FLASH_READBACK
            elif type == command.FLASH_READBACK:
                datum = unpack(pattern, data)
                datum = list(datum)
                telem_index = datum.pop(0) #pop removes the index number from data array
                #print "Special Telemetry Data Packet #",telem_index
                #print datum
                if (datum[0] != -1) and (telem_index) >= 0:
                    if telem_index <= self.numSamples:
                        self.telemtryData[telem_index] = datum
                    else:
                        print "Got out of range telem_index =",telem_index
            
            # ERASE_SECTORS
            elif type == command.ERASE_SECTORS:
                datum = unpack(pattern, data)
                print "Erased flash for", datum[0], " samples."
                if datum[0] != 0:
                    self.flash_erased = datum[0] 
                
            # SLEEP     # removed due to non-maintenance; could be updated.
            #elif type == command.SLEEP:
            #    datum = unpack(pattern, data)
            #    print "Sleep reply: ",datum[0]
            #    if datum[0] == 0:
            #        self.awake = True;
            
            # ZERO_POS
            elif type == command.ZERO_POS:
                print 'Hall zeros established; Previous motor positions:',
                motor = unpack(pattern,data)
                print motor
                
            # SET_VEL_PROFILE
            elif (type == command.SET_VEL_PROFILE):
                print "Set Velocity Profile readback:"
                temp = unpack(pattern, data)
                print temp
                
            # WHO_AM_I
            elif (type == command.WHO_AM_I):
                print "query : ",data
                sel.frobot_queried = True

            # GET_AMS_POS
            elif (type == command.GET_AMS_POS):
                datum = unpack(pattern, data)
                #This command sends back a useless parameter, we need not display it
                #print "Motor positions: { %d , %d }" % (datum[0], datum[1])

                      
        except Exception as args:
            print "\nGeneral exception from callbackfunc:",args
            print "\n    ******    TRACEBACK    ******    "
            traceback.print_exc()
            print "    *****************************    \n"
            print "Attempting to exit cleanly..."
            shared.xb.halt()
            shared.ser.close()
            sys.exit()

    ################################################
        
########## Helper functions #################
#TODO: find a home for these? Possibly in BaseStation class (pullin, abuchan)
  
def verifyAllMotorGainsSet(xb):
    #Verify all robots have motor gains set
    for r in xb.ROBOTS:
        if not(r.motor_gains_set):
            print "CRITICAL : Could not SET MOTOR GAINS on robot 0x%02X" % r.DEST_ADDR_int
            xb.close()
            
def verifyAllTailGainsSet(xb):
    #Verify all robots have motor gains set
    for r in xb.ROBOTS:
        if not(r.tail_gains_set):
            print "CRITICAL : Could not SET TAIL GAINS on robot 0x%02X" % r.DEST_ADDR_int
            xb.close()
            
def verifyAllQueried(xb):            
    for r in xb.ROBOTS:
        if not(r.robot_queried):
            print "CRITICAL : Could not query robot 0x%02X" % r.DEST_ADDR_int
            xb.close()

#TODO: Replace with tqdm library, since it gives a time estimate.
def dlProgress(current, total):
    percent = int(100.0*current/total)
    dashes = int(floor(percent/100.0 * 45))
    stars = 45 - dashes - 1
    barstring = '|' + '-'*dashes + '>' + '*'*stars + '|'
    #sys.stdout.write("\r" + "Downloading ...%d%%   " % percent)
    sys.stdout.write("\r" + str(current).rjust(5) +"/"+ str(total).ljust(5) + "   ")
    sys.stdout.write(barstring)
    sys.stdout.flush()