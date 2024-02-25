"""CoolLED pE 1&2 device
Device connected to PC via USB ↦ port:
    On Windows PC ↦ COM3
        might need the CoolLED pE device?
    
    On Linux PC (laptop) ↦ /dev/serial/by-id/usb-CoolLED_precisExcite_1154-if00 → /dev/ttyACM0
        To use the device:
            the user needs to have read/write permissions to the device file
            (see below)
        for VirtualBox Windows client:
            • forward THE DEVICE ABOVE to COM3
            • launch the VirtulBox client machine (user needs read/write access 
                to the device file on the host machine, see below)
            
Upon trying to launch the virtual box Windows client you an error dialog a 
message as below:

**************************************************
Failed to start the virtual machine Windows10.

Cannot open host device '/dev/serial/by-id/usb-CoolLED_precisExcite_1154-if00' 
for read/write access. Check the permissions of that device ('/bin/ls -l 
/dev/serial/by-id/usb-CoolLED_precisExcite_1154-if00'): Most probably you need 
to be member of the device group. Make sure that you logout/login after changing 
the group settings of the current user (VERR_ACCESS_DENIED).

Result Code:NS_ERROR_FAILURE (0X80004005) Component:ConsoleWrap 
Interface:IConsole {6ac83d89-6ee7-4e33-8ae6-b257b2e81be8}
**************************************************

This is because, as a user in the host (Linux) world you do not have read/write
access to the serial device file, and you need a few more steps:
configure 
• find out who has read/write permissions on the serial device:
    ∘ find out the original device file, display permissions to that file:
    
user@Host:~> ls -l /dev/serial/by-id/usb-CoolLED_precisExcite_1154-if00 
lrwxrwxrwx 1 root root 13 Feb 24 15:51 /dev/serial/by-id/usb-CoolLED_precisExcite_1154-if00 -> ../../ttyACM0

    ∘ we see it is a symbolic link to the serial device file /dev/ttyACM0
        therefore, find permissions to that as well:

user@Host:~> ls -l /dev/ttyACM0 

crw-rw---- 1 root dialout 166, 0 Feb 24 15:51 /dev/ttyACM0

    ∘ in this example the user running Virtualbox needs to be a member of the 
        'dialout' group ⇒ ask the sysadmin to configure the user as a member of 
        that group; the user needs to log out and log in again
        
        WARNING: Some distribution might require a system reboot after this change

NOTE: Each Linux distribution may assign different group names (e.g. 'devices'
instead of 'dialout', etc). This being a serial device, the choice of 'dialout'
as a group may be justified as these devices usually are communication devices
(for example, modems).

        
"""

import io, sys, os, typing
from dataclasses import (dataclass, KW_ONLY, MISSING, field)
import serial
import serial.tools.list_ports as port_list

from core.prog import (scipywarn, printStyled)
from core.datatypes import TypeEnum

TriggerLabels = ["Off","RisingEdges","FallingEdges","BothEdges","FollowPulse"]
TriggerCmd = ['Z', '+', '-', '*', 'X'] # char

carriage_return = "\r"
line_feed = "\n"

class TriggerType(TypeEnum):
    Off = 0
    RisingEdges = 1
    FallingEdges = 2
    BothEdges = 3
    FollowPulse = 4
    
    @classmethod
    def getCommandString(cls, t):
        if isinstance(t, (str, int)):
            t = cls.type(t)
        elif t not in cls:
            raise TypeError(f"Expecting a {cls.__name__} object; instead, got a {type(t).__name__}")
        
        return TriggerCmd[t.value]
    
    @classmethod
    def fromCommandString(cls, s:str):
        if not isinstance(s, str) :
            raise TypeError(f"Expecting a string; instead, got a {type(s).__name__}")
        
        if len(s) != 1 or s.upper() not in TriggerCmd:
            raise ValueError(f"Expecting a str in {TriggerCmd} (case-insenstive); instead, got {s}")
        
        s = s.upper()
        
        if s in ("Z", "X"):
            return cls.Off if s == "Z" else cls.FollowPulse
        
        else:
            return cls.RisingEdges if s == "+" else cls.FallingEdges if s == "-" else cls.BothEdges
        
            
    @property
    def command(self):
        return TriggerCmd[self.value]

class CoolLEDpE12():
    def __init__(self, port:str = "COM3" if sys.platform == "win32" else "/dev/serial/by-id/usb-CoolLED_precisExcite_1154-if00", 
                 baudrate:int = 9600, parity:str = serial.PARITY_NONE, stopbits:int = 1, 
                 timeout:float = 0.5, xonxoff:int = 0, verbose:int = 1, 
                 inter_byte_timeout:float = 0.0):
        """
        Default parameter values are:

            port:str = "COM3" if sys.platform == "win32" else "/dev/serial/by-id/usb-CoolLED_precisExcite_1154-if00"
            baudrate:int = 9600
            xonxoff: int = 0
            parity:str = serial.PARITY_NONE
            stopbits:int = 1
            verbose:int = 1
            timeout:float = 0.5
            inter_byte_timeout: float = 0.0
        """
        
        if parity not in serial.PARITY_NAMES:
            raise ValueError(f"Invalid bit parity {parity}, expecting a str, one of {serial.PARITY_NAMES}")
        
        self._lam_labels_ = list() # of str
        self._xlam_labels_ = list() # of str
        self._greeting_msg_ = list()
        self._trigger_sequence_ = ""
        self._trigger_mode_ = TriggerType.Off
        self._current_channel_ = 0
        self._channel_states_ = dict()
        self._state_ = dict()
        
        try:
            self.__serial_port__ = serial.Serial(port, timeout = timeout)
            self.__serial_port__.baudrate = baudrate
            self.__serial_port__.xonxoff = xonxoff
            self.__serial_port__.parity = parity
            self.__serial_port__.stopbits = stopbits
            self.__serial_port__.verbose = verbose
            # self.__serial_port__.timeoutk = timeout
            self.__serial_port__.inter_byte_timeout = inter_byte_timeout
            
            self.__portio__ = io.TextIOWrapper(io.BufferedRWPair(self.__serial_port__, self.__serial_port__))
            
            if not self.__serial_port__.is_open:
                self.openPort()
                
            self._greeting_msg_ = self.readPort(collapse=False)
            self._initChannels_()
            # print(f"{self.__class__.__name__} greeting: {self._greeting_msg_}")
                
        except:
            print("Device could not be found; make sure it is turned on and plugged in an USB port")
            raise
        
    
    def __enter__(self):
        if not self.__serial_port__.is_open:
            self.__serial_port__.open()
        return self
    
    def __exit__(self, *args):
        if self.__serial_port__.is_open:
            self.__serial_port__.close()
            
    def readPort(self, collapse:bool = True) -> str | list:
        if not self.__serial_port__.is_open:
            return ""
        
        msg = self.__portio__.readlines()
        
        if collapse:
            for s in msg:
                s.strip("\n")
                
            if len(msg) == 1:
                msg = msg[0].strip("\n")
            else:
                msg = "\n".join(msg)
        
        return msg
    
    def sendCommand(self, cmd: str, verbose:bool=True, collapse:bool=True):
        if not self.__serial_port__.is_open:
            scipywarn("The underlying serial port is closed; call method openPort() then call this method again.")
            # printStyled("The underlying serial port is closed; call method openPort() then call this method again.", "red")
            return
        
        if not cmd.endswith("\n"):
            cmd += "\n"
            
        self.__portio__.write(cmd)
        self.__portio__.flush()
        
        if verbose:
            c_ = cmd.replace("\r", "↵")
            print(f"sending {c_}")
            
        msg = self.readPort(collapse=collapse)
        
        if verbose:
            print(f"received:\n{msg}")
            
        return msg
    
    def readChannels(self):
        msg = self.sendCommand("LAMS", verbose=False, collapse=False)
        print(msg)
        
    def _readLAMLabels_(self):
        msg = list(filter(lambda x: x not in self._greeting_msg_, self.sendCommand("LAMS", verbose=False, collapse=False)))
        
        self._lam_labels_ = sorted([s[4] for s in msg if len(s) >= 4 and s.startswith("LAM:")])
        self._trigger_sequence_ = "".join(self._lam_labels_) + "0" # for now !
        
    def _readXLAMLabels_(self):
        msg = list(filter(lambda x: x not in self._greeting_msg_, self.sendCommand("LAMS", verbose=False, collapse=False)))
        self._xlam_labels_ = sorted([s[5] for s in msg if len(s) >=6 and s.startswith("XLAM:")])
        
    def _initChannels_(self):
        """Reads the channel labels, sets up a default trigger sequence and initializes channel states"""
        msg = list(filter(lambda x: x not in self._greeting_msg_, self.sendCommand("LAMS", verbose=False, collapse=False)))
        self._lam_labels_ = sorted([s[4] for s in msg if len(s) >= 4 and s.startswith("LAM:")])
        self._xlam_labels_ = sorted([s[5] for s in msg if len(s) >=6 and s.startswith("XLAM:")])
        self._trigger_sequence_ = "".join(self._lam_labels_) + "0"# for now!
        self.readChannelStates()
        
    def openPort(self):
        if not self.__serial_port__.is_open:
            self.__serial_port__.open()
            
    def closePort(self):
        if hasattr(self, "__serial_port__") and self.__serial_port__.is_open:
            self.__portio__.flush()
            self.__serial_port__.close()

    def __del__(self):
        self.closePort()
        
    def _actionChannelLight_(self, channel:typing.Optional[typing.Union[int, str]] = None, 
                             on:bool=True, exclusive:bool=True):
        pfx = "SQX"
        action = "N" if on else "F"
        oppact = "F" if on else "N"
        print(f"{self.__class__.__name__}._actionChannelLight_: action = {action}, oppact = {oppact}")
        
        
        if isinstance(channel, int):
            if channel < 0 or channel > 3:
                raise ValueError(f"Invalid channel index {channel}; the device has only four (0 ⋯ 3) channels")
            channel = self._lam_labels_[channel]
            
        elif isinstance(channel, str):
            if channel not in self._lam_labels_:
                raise ValueError(f"Invalid channel {channel}; was expecting one of {self._lam_labels_}")
            
        elif channel is not None:
            raise TypeError(f"Invalid channel specification; expecting an int (0 ⋯ 3) a str, one of {self._lam_labels_}, or None; instead, got {type(channel).__name__}")
        
        if channel is not None:
            msg = f"{pfx}"
            for lam in self._lam_labels_:
                print(f"switching {lam} {'off' if action == 'F' else 'on'}")
                msg += f"C{lam}{action}\r"
                # action = "N" if channel == lam else "F"
            msg += "\r"
            
        else:
            if exclusive:
                msg = f"{pfx}"
                for lam in self._lam_labels_:
                    act = action if channel == lam else oppact
                    msg += f"C{lam}{act}\r"
                msg += "\r"
            else:
                msg = f"{pfx}C{channel}{action}\r"
        
        return self.sendCommand(msg, verbose=False, collapse=False)
        
        
    def channelON(self, channel:typing.Optional[typing.Union[int, str]] = None, 
                  exclusive:bool=True, intensity: int = 0):
        
        self.lights(channel, True)
        # self._actionChannelLight_(channel, on=True, exclusive=exclusive)
        
    def channelOFF(self, channel:typing.Optional[typing.Union[int,str]] = None,
                  exclusive:bool=True, intensity: int = 0):
                   
        self.lights(channel, False)
        
    def readChannelStates(self):
        self.__portio__.flush()
        self._channel_states_ = dict(sorted(list(map(lambda x: (x[1], {"on": x.strip("\n")[-1]=="N", "intensity":int(x[2:5])}), filter(lambda x: x.startswith("C"), self.sendCommand("C?", verbose=False, collapse=False)))), key = lambda x: x[0]))        
        
    @property
    def channelStates(self) -> dict:
        """Read-only property.
        A channel state can be changed only by commands to switch it ON/OFF or
        alter its intensity
        """
        self.readChannelStates()
        return self._channel_states_
    
    def getChannelState(self, channel:typing.Optional[typing.Union[int,str]] = None) -> dict:
        self.readChannelStates()
        if channel is None:
            return self._channel_states_
        
        if isinstance(channel, int):
            nchannels = len(self._lam_labels_)
            if channel not in range(nchannels):
                raise ValueError(f"Invalid channel index specified ({channel}); expecting an int the semi-open interval [0 ⋯ {nchannels})")

            channel = self._lam_labels_[channel]
        
        if isinstance(channel, str): 
            if channel not in self._lam_labels_ or channel not in self._channel_states_:
                raise ValueError(f"Invalid channel specified {channel}; expecting a string in {self._lam_labels_}")
            
            return self._channel_states_[channel]
        
        else:
            raise TypeError(f"Invalid LAM channel specification; expecting an int, a str or None; instead, got {type(channel).__name__}")
    
    @property
    def state(self) -> int:
        if self.triggerMode == TriggerType.Off:
            self.__portio__.flush()
            channelStates = sorted(list(filter(lambda x: x.startswith("C"), self.sendCommand("C?", verbose=False, collapse=False))))
            
            # state = any(c[5] == "N" for c in channelStates)
            self._state_ = any(c[5] == "N" for c in channelStates)
            
        # else:
        #     state = self._state_
        
        return self._state_
            
    @state.setter
    def state(self, val:bool):
        self._state_ = val == True
        
    def lights(self, channel:typing.Union[int,str], on:bool):
        # action = "N" if on else "F"
        # oppact = "F" if on else "N"
        # print(f"action: {action}, oppact: {oppact}")
        
        self.currentChannel = channel
        
        channelState = self.getChannelState()
        
        if on:
            trigCmd = "Z" if self.triggerMode in (TriggerType.Off, TriggerType.FollowPulse) else self.triggerMode.command
            
            msg = f"SQ{trigCmd}\r"
            
            if self.triggerMode == TriggerType.Off:
                for k, lam in enumerate(self._lam_labels_):
                    msg += f"C{lam}"
                    if k == self.currentChannel:
                        msg += "N"
                    else:
                        msg += "F"
                        
                    msg += "\r"
                    
            elif self.triggerMode == TriggerType.FollowPulse:
                msg += f"\rA{self.currentLAM}#"
                
            else:
                msg += f"{self.triggerMessage}SQ{self.triggerMode.command}"
                
        else:
            if self.triggerMode in (TriggerType.Off, TriggerType.FollowPulse):
                msg = f"SQX\rC{self.currentLAM}F\rAZ"
            else:
                msg = "SQXAZ"
            
        self.sendCommand(msg, verbose=True, collapse=False)
        self.readChannelStates()
                    
           
    @property
    def triggerMessage(self) -> str:
        return f"SQX\rSQ{self.triggerSequence}\r"
            
    @property
    def triggerSequence(self) -> str:
        return self._trigger_sequence_
    
    @triggerSequence.setter
    def triggerSequence(self, val:str):
        if not isinstance(val, str) or len(val.strip()) == 0:
            scipywarn(f"Invalid trigger sequence {val}")
            return
        
        self._trigger_sequence_ = val
        
        
            
    @property
    def portOpen(self) -> bool:
        return self.__serial_port__.is_open
    
    @property
    def timeout(self)-> int:
        return self.__serial_port__.timeout
    
    @timeout.setter
    def timeout(self, val:float):
        self.__serial_port__.timeout = val
        
    @property
    def baudrate(self)-> int:
        return self.__serial_port__.baudrate
    
    @baudrate.setter
    def baudrate(self, val:float):
        self.__serial_port__.baudrate = val
        
    @property
    def parity(self) -> int:
        return self.__serial_port__.parity
    
    @parity.setter
    def parity(self, val:str):
        if parity not in serial.PARITY_NAMES:
            raise ValueError(f"Invalid parity {val}; expecting a str, one of {serial.PARITY_NAMES}")
        
        self.__serial_port__.parity = val
        
    @property
    def lamLabels(self):
        return self._lam_labels_
    
    @property
    def triggerMode(self) -> TriggerType:
        """The trigger type.
        This property can be set using an int (0 ⋯ 4), a string in 
        ["Off","RisingEdges","FallingEdges","BothEdges","FollowPulse"] (case-sensitive)
        or a string in ['Z', '+', '-', '*', 'X'] (case-insensitive).
        
        The latter collection represents the command strings (in upper case) 
        sent to the device.
        """
        return self._trigger_mode_
    
    @triggerMode.setter
    def triggerMode(self, val:typing.Optional[typing.Union[TriggerType, int, str]] = None):
        if isinstance(val, (int, str)):
            if isinstance(val,str) and val.upper() in TriggerCmd:
                val = TriggerType.fromCommandString(val)
            else:
                val = TriggerType.type(val)
        elif not isinstance(val, TriggerType):
            raise TypeError(f"Expecting an int, str or TriggerType; instead, got {type(val).__name__}")
        
        self._trigger_mode_ = val
        
    @property
    def currentChannel(self)->int:
        """The index of the LAM where commands are currently sent.
        The setter accepts an int or a str.
        See also currentLAM.
        """
        return self._current_channel_
    
    @currentChannel.setter
    def currentChannel(self, val:typing.Union[int, str]):
        if isinstance(val, int):
            if val < 0 or val > 3:
                raise ValueError(f"Expecting an int in range 0 ⋯ 3 ; instead, got {val}")
            
            self._current_channel_ = val
            
        elif isinstance(val, str):
            if val not in self._lam_labels_:
                raise ValueError(f"Expecting a string in {self._lam_labels_}; nstead, got {val}")
            
            self._current_channel_ = self._lam_labels_.index(val)
        else:
            raise TypeError(f"Expecting an int; instead gotr a {type(val).__name__}")
        
    @property
    def currentLAM(self)-> str:
        """<Label of the current LAM channel.
        The setter accepts an int or a str.
        See also currentChannel.
        """
        return self._lam_labels_[self._current_channel_]
    
    @currentLAM.setter
    def currentLAM(self, val:typing.Union[int,str]):
        self.currentChannel = val
    
        
    
    

