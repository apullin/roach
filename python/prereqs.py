from setuptools.command import easy_install

libs = ["xbee","pyserial","chan"]

for lib in libs:
    print
    print " #######  Installing",lib,"library... "
    easy_install.main( [lib] )
