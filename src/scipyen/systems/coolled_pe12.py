import io
from dataclasses import (dataclass, KW_ONLY, MISSING, field)
import serial
import serial.tools.list_ports as port_list

TriggerLabels = ["Off","RisingEdges","FallingEdges","BothEdges","FollowPulse"]
TriggerCmd = ['Z', '+', '-', '*', 'X'] # char


@dataclass
class CoolLEDpE12():
    port:str = "COM3"
    baudrate:int = 9600
    xonxoff: int = 0
    parity:str = serial.PARITY_NONE
    stopbits:int = 1
    verbose:int = 1
    timeout:float = 0.5
    inter_byte_timeput: float = 0.0

    def readChannels(self):
        with serial.Serial(self.port, self.timeout=1) as port:
            port.baudrate = self.baudrate
            port.xonxoff = self.xonxoff
            port.parity = self.parity
            port.stopbits = self.stopbits
            port.verbose = self.verbose
            port.timeoutk = self.timeout
            port.inter_byte_timeout = self.inter_byte_timeout

            if not port.is_open:
                port.open()





def readChannels()
