import time,sys

try:
    while True:
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print "Got interrupt!"
    sys.exit()