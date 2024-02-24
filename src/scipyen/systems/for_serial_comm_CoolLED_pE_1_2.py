"""
Requires PySerial installed in scipyenv

"""
import io
import serial
import serial.tools.list_ports as port_list

TriggerLabels = ["Off","RisingEdges","FallingEdges","BothEdges","FollowPulse"]
TriggerCmd = ['Z', '+', '-', '*', 'X'] # char
intensity  = 100

# this is the COM port mapped to the USB connection of CoolLED pE 1 & 2 on
# Bruker PC !!!
with serial.Serial("COM3", timeout=1) as com3:
    # A-HA! need to append \n to the messages in comio!
    try:
        comio = io.TextIOWrapper(io.BufferedRWPair(com3, com3))
        com3.baudrate = 9600
        com3.xonxoff = 0 # flow control handshaking Off
        com3.parity = 'N' # parity None (serial.PARITY_NONE)
        com3.stopbits = 1
        com3.verbose = 1
        com3.timeout = 0.5
        com3.inter_byte_timeout = 0.0 # DelayBetweenCharsMs ?
        if not com3.is_open:
            com3.open()

        msg = " "
        while len(msg):
            # msg = com3.readline()
            msg = comio.readline()
            # outputs:
            # CoolLED precisExcite
            #
            # Hello, pleased to meet you.
            print(msg)

        # com3.flush()

        #

        print("send 'LAMS'")
        # com3.write(b"LAMS")
        comio.write("LAMS\n")
        comio.flush()
        msg = comio.readlines()
        for s in msg:
            s = s.strip('\n')

        msg = '\n'.join(msg)
        print(f"LAMS are:\n{msg}")

        # switch illumination ON:


        # set itensity on channel A
        print(f"send 'CAI{intensity}'")
        comio.write(f"CAI{intensity}\n")
        comio.flush()
        msg = comio.readlines()
        for s in msg:
            s = s.strip('\n')

        msg = '\n'.join(msg)
        print(f"received:\n{msg}")

        # get intensity on channel A
        print("send 'CA?'")
        comio.write("CA?\n")
        comio.flush()
        msg = comio.readlines()
        for s in msg:
            s = s.strip('\n')

        msg = '\n'.join(msg)
        print(f"received:\n{msg}")
    except:
        raise

    # com3.close()
    # del com3
    # del comio


