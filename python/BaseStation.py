#!/usr/bin/env python
"""
authors: Kevin Peterson, Stan Baek, Andrew Pullin
Modification on 2011-10-4:

This file creates a class BaseStation that can be used to send commands 
to the custom basestation or an XBee module

Wrapper functions are provided for this class, see:
base_functions and robot_functions

Modification on 2013-1-30: (apullin)
Brining in functions from base_functions to create a unified Basestation class.

"""


import time, os, sys, traceback
from lib import command
import serial
from scan import *
from xbee import XBee
from struct import unpack

class BaseStation(object):

    api_frame = 'A'
    pendingAT = False
    
    robots = []

    def __init__(self, port, baudrate, channel = None, PANid = None, base_addr = None, verbose = False):
        
        self.verbose = verbose
        
        try:
            self.ser = serial.Serial(port, baudrate, timeout = 1)
        except serial.SerialException:
            print
            print "Could not open serial port:",port
            print
            print "Scanning for available COM ports:"
            print "------------------------------------"
            self.scanSerialPorts()
            print "------------------------------------"
            print "Check your BaseStation declaration --OR--"
            print " you may need to change the port in shared.py"
            sys.exit() #force exit
        
        if verbose:
            print "serial open"
            
        self.ser.writeTimeout = 5

        #Set up callback
        self.xb = XBee(self.ser, callback = self.xbee_received)

    def close(self):
        try:
            self.xb.halt()
            self.ser.close()
            print "BaseStation halted and close."
        except SerialException:
            print "SerialException on Basestation close() attempt."
            
    def sendTX(self, status, type, data ):
        pld = chr(status) + chr(type)  + ''.join(data)
        self.xb.tx(dest_addr = self.dest_addr, data = pld)
        
    def sendAT(self, command, parameter = None, frame_id = None):
    #TODO: This logic may not be correct. Need to sort out condition where frame id and parameters are used
        if frame_id is None:
            #Send with no wait
            if parameter is not None:
                self.xb.at(command = command, parameter = parameter)
            else:
                self.xb.at(command = command)
        else: #use frame_id
            #send with wait
            if parameter is not None:
                self.xb.at(frame_id = frame_id, command = command, parameter = parameter)
            else:
                self.xb.at(frame_id = frame_id, command = command)
            
            self.ATwait()
            
        #if parameter is not None:
        #    if frame_id is not None:
        #        self.xb.at(frame_id = frame_id, command = command, parameter = parameter)
        #    else:
        #        self.xb.at(command = command, parameter = parameter)
        #elif frame_id is not None: # expects an AT response
        #    self.xb.at(frame_id = frame_id, command = command)
            #Since an AT response is expected, this function will busy wait here for the AT response
        #    self.ATwait()
        #else:
        #    self.xb.at(command = command)

    def read(self):
        packet = self.xb.wait_read_frame()
        return packet

    def getChannel(self):
        self.incremetAPIFrame()
        self.sendAT(command='CH', frame_id = self.api_frame)
        return self.atResponseParam

    def setChannel(self, param):
        self.incremetAPIFrame()
        self.sendAT(command='CH', parameter=param, frame_id = self.api_frame)

    def getPanID(self):
        self.incremetAPIFrame()
        self.sendAT(command='ID', frame_id = self.api_frame)
        return self.atResponseParam
        
    def setPanID(self, param):
        self.incremetAPIFrame()
        self.sendAT(command='ID', parameter=param, frame_id = self.api_frame)
        
    def getSrcAddr(self):
        self.incremetAPIFrame()
        self.sendAT(command='MY', frame_id = self.api_frame)
        return self.atResponseParam
        
    def setSrcAddr(self, param):
        self.incremetAPIFrame()
        self.sendAT(command='MY',parameter=param, frame_id = self.api_frame)

    def getLastAckd(self):
        self.incremetAPIFrame()
        self.sendAT(command='EA', frame_id = self.api_frame)
        return self.atResponseParam
        
    def writeParams(self):
        self.incremetAPIFrame()
        self.sendAT(command='WR', frame_id = self.api_frame)
        
    def incremetAPIFrame(self):
        api_frame = chr( ord(self.api_frame) + 1 )  #increment API frame
        
    def ATwait(self):
        self.pendingAT = True
        self.atResponseParam = None
        while self.pendingAT:
            pass
    
    def associateRobot(self, robot):
        if robot.callbackHandler: #Do no associate if robot has no callback handler
            #TODO: We could check channel/PAN here, and raise error 
            self.robots.append(robot)
        else:
            raise Error("Robot must have callbackHandler function defined.")
    
    def scanSerialPorts(self):
        """scan for available ports. return a list of tuples (num, name)"""
        available = []
        for i in range(256):
            try:
                s = serial.Serial(i)
                available.append( (i, s.portstr))
                s.close()   # explicit close 'cause of delayed GC in java
            except serial.SerialException:
                pass
        for n,s in available:
            print "%s" % s
        
    #XBee library callback function
    #This will be set up as the RX callback, to be called every time a packet is received
    def xbee_received(self, packet):
        try:
            #Check type of packet:
            name = packet.get('id')
            #The packet is a response to an AT command
            if name == 'at_response':
                frame_id = packet.get('frame_id')
                command = packet.get('command')
                status = packet.get('status')
                parameter = packet.get('parameter')
                if parameter is not None: #responses can have no parameter
                    if len(parameter)  == 1:
                        param_num = unpack('>B',parameter)[0]
                    else:
                        param_num = unpack('>H',parameter)[0]
                    self.atResponseParam = param_num
                else:
                    self.atResponseParam = None
                
                
                #Handle packet in whatever way is appropriate
                if self.verbose:
                    print "Got AT response"
                    print "command = ",command
                    if parameter is not None:
                        print "length = ",len(parameter)
                        print "param = 0x%X" % param_num
                    else:
                        print "length = 0 (no parameter)"
                        print "param = None"
                    print "status = ",ord(status)
                    

                #Once all processing done, clear pendingAT flag
                self.pendingAT = False
                
            #The packet is data received from the radio
            elif name == 'rx':
                print "Got RX"
                src_addr = packet.get('source_addr')
                rssi = packet.get('rssi')
                options = packet.get('options')
                data = packet.get('rf_data')
                #if self.verbose:
                #    print "RSSI:",rssi,"options:",options,"data:",data
                #print "RSSI:",-ord(rssi),"dBm","options:",options,"data:",data
                
                #extract source addr
                #send packet to any robots matching addr (handle bcast)
                for r in self.robots:
                    if r.DEST_ADDR_int == src_addr:
                        r.callbackHandler(packet)
        
        except Exception as args:
            print "\nGeneral exception from callbackfunc:",args
            print "\n    ******    TRACEBACK    ******    "
            traceback.print_exc()
            print "    *****************************    \n"
            print "Attempting to exit cleanly..."
            self.close()