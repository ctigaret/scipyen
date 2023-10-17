"""Module to access ABF meta-information.

This modules provides functionality to access "metadata" (e.g. command waveforms, 
protocol details) associated with electrophysiology data recorded using Axon 
hardware and software (pClamp suite/Clampex).

Scipyen uses primarily the neo package (https://neo.readthedocs.io/en/stable/) 
to read signal data from electrophysiology recordings from Axon ABF files and
represent it in a coherent system of hierarchical containers, where the 
electrophysiological data is contained in a neo.Block. In addition, associated 
"meta-information" (e.g. channels/hardware configuration, protocols) are stored 
by Scipyen in the 'annotations' attribute of the neo.Block generated after 
reading an ABF file.

The PyABF (https://swharden.com/pyabf/) package complements the functionality
for accesssing this "meta-information". 

This module defines functions uing the pyabf package to access the meta-information
information nuse the pyabf package to access the ABF
meta-information associated with a 

See also 
• https://swharden.com/pyabf/tutorial/ 
• https://swharden.com/pyabf/

NOTE: About ADCs and DACs
These are defined in the Lab bench, together with their telegraphing (if a 
telegraphed is configured). 

0. Useful pyabf functions to be used even without an ABF object:
================================================================
pyabf.names.getDigitizerName(int)

    the argument is abf._protocolSection.nDigitizerType which is the same as
    annotations["protocol"]["nDigitizerType"]
    
    supports values in range(8)
    
    in pyabf this function populates abf._protocolSection.sDigitizerName
    
pyabf.names.getTelegraphName(int)

    the argument is abf._adcSection.nTelegraphInstrument[ADC_index], the same as
    annotations["listADCInfo"][ADC_index]["nTelegraphInstrument"]
    
    supports values in range(27)
    
    in pyabf this function populates abf._adcSection.sTelegraphInstrument

1. ABF object attributes and their correspondence to the neo axon_info
========================================================================
ABF information is placed in the neo.Block 'annotations' attribute upon loading
in Scipyen.

abf.sweepCount == abf._headerV2.lActualEpisodes == abf._protocolSection.lEpisodesPerRun

    = annotations["lActualEpisodes"]
    = annotations["protocol"]["lEpisodesPerRun"]

abf.channelCount == abf._adcSection._entryCount → the number of ADC channels
    used (checked in the protocol editor's 'Inputs' tab) → the number of ABF 
    (input) channels
    
    = annotations["sections"]["ADCSection"]["llNumEntries"]
    = len(annotations["listADCInfo"])
    
abf.channelList == list(range(abf.channelcount)) list of channel indices
    
abf.stimulusFilefolder : str, the fully qualifies path to the folder where the 
    stimulus file may be (if used); by default this is the same folder as the
    one where the recorded data is stored
    
abf.holdingCommand: list with nDAC channel elements; holds the holding value in 
    each DAC (whether the DAC it is used or not)
    
    this is effectively an alias to abf._dacSection.fDACHoldingLevel
    
    len(abf.holdingCommand) = abf._dacSection._entryCount = len(annotations["listDACInfo"])
    
    abf.holdingCommand[κ] = annotations["listDACInfo"][κ]["fDACHoldingLevel"]
    

2. Information about the DAC channels
=====================================

The available DAC channels (whether selected for use or not) are shown in the
bottom tabs of the Protocol editor (Waveform tab) and are determined based on 
the digitizer type set up with the Configure > Digitizer menu item.

The names, aliases and scales of the DAC channels are configured using 
Configure > Lab Bench menu item and, optionally, the 
Configure > Telegraphed Instrument menu item.

abf._dacSection

• nDACNum: list of DAC output channels by number: (0-3 for Digitdata 1440 series,
    0-7 for Digidata 1550 series, see also NOTE: 2023-09-03 22:26:46)
    length is 4 (DigiData 1440) or 8 (DigiData 1550) - the number of output DACs
    available (either used or not)
    
        = annotations["sections"]["DACSection"]["llNumEntries"]
        = len(annotations["listDACInfo"])
        
    nDACNum[κ] = annotations["listDACInfo"][κ]["nDACNum"]
    
• fDACHoldingLevel: list of holding levels, one per DAC channel

    fDACHoldingLevel[κ] = annotations["listDACInfo"][κ]["fDACHoldingLevel"]
    
• nInterEpisodeLevel: list of interepisode levels for each DAC channel

    nInterEpisodeLevel[κ] = annotations["listDACInfo"][κ]["nInterEpisodeLevel"]
    
• nWaveformEnable → list of int flags indicating if the DAC is used to generate
    a command waveform (1) or not (0); same length as nDACNum
    
        a DAC is used if "Analog waveform" is checked in the Waveform tab of the
        protocol editor corresponding to the output channel corresponding to 
        the current channel tab in the bottom row, see NOTE: 2023-09-03 22:26:46
    
    nWaveformEnable[κ] = annotations["listDACInfo"][κ]["nWaveformEnable"]
    
• nWaveformSource → list of int flags indicating the source of the DAC command
    waveform; same length as nDACNum; values: 
    0 = no waveform defined (regardless of the vaue of nWaveformEnable)
    
    1 = waveform generated using the Waveform tab epochs specifiers
    
    2 = waveform generated using a source (ABF or ATF) file
    
    nWaveformSource[κ] = annotations["listDACInfo"][κ]["nWaveformSource"]
    
• lDACFilePathIndex  → list of int flags with the index into the strings section,
    for the name of a stimulus waveform file for the DAC with nWaveformSource == 2,
    see above
    
    set to 0 if no external waveform file is used
    
    WARNING: This is the path as defined in the protocol; pyabf will try to 
    locate it as if it was run on the same machine where the acquisition was 
    performed; failing that, will try to locate it in the folder given by the 
    pyabf.ABF constructor parameter "stimulusFilefolder"; failing that, it will
    try the folder of the recorded ABF file (usef to construct the pyabf.AB object)
    and finally, will issue a warning.
    
    lDACFilePathIndex[κ] = annotations["listDACInfo"][κ]["lDACFilePathIndex"]

3. Protocol Epochs
===================
By design, a DAC channel outputs a command waveform defined discretely using a
number of epochs.

For a given DAC channel, the number of epochs is the same in all sweeps in a run
and the parameters of the 𝒏ᵗʰ epoch are the same across all sweeps¹:

• type ('Off', 'Step', 'Ramp', 'Pulse', 'Triangular', 'Cosine', 'Biphasic')

• inter-sweep holding level

• initial command level ("First level") and increment ("Delta level")

    The actual command value (or level) is:
    "First level" + sweep counter × "Delta level"

• initial duration ("First duration") and duration increment ("Delta
duration")  

    The actual epoch duration in each sweep is:
    "First duration" + sweep counter × "Delta duration", with sweep counter 
    starting at 0
    
• digital pattern²

• high logic for digital outputs

¹The exception to this rule is when "Alternate Waveforms" is enabled, such that
even sweep numbers use the epochs defined in DAC Channel #0 and odd sweep numbers
use the epochs defined on DAC Channel #1. When this option is switched off, and 
both first two DAC channels (#0 and #1) are configured with a waveform, these 
waveforms are sent to the amplifier in every sweep, on their corresponding DAC
outputs!

²Unless "Alternate Digital Outputs" is enabled, in which case the digital output
for that epoch alternates between even and odd sweeps. The main digital pattern 
is set on DAC Channel #0, whereas the alternative pattern is set on Channel #1.

From a Scipyen programming point of view, the consequences are:
• if "Alternate Waveform" is OFF, the epoch table for a given DAC channel is THE
 SAME for all sweeps in a run.
• if "Alternate Waveform" is ON, the epoch table for a given DAC channel is the 
one defined on Channel #0 on even sweep numbers, and on Channel #1 for odd sweep
numbers



NOTE: 2023-09-06 23:19:29 About the Epochs table

The epoch table is dynamically created by pyabf when a pyabf.ABF object is 
initialized. PyABF represents an epoch table as a pyabf.waveform.EpochTable
object, for a specific DAC channel index. See getABFEpochsTable(…) in this module.

An EpochTable stores pyabf.waveform.Epoch objects (NOT neo.Epoch !!!) created
using the information in "epochs per dac" section.

In neo.Blocks read from ABF files using neo, the epoch table can be constructed 
from annotations dict (WARNING do NOT confuse this epoch table with neo.Epoch
objects!).

In particular, the dictEpochInfoPerDAC contains the Epoch information for each 
defined epochs:

abf._epochPerDacSection.nEpochType: int - see ABFEpochType enum type in this module


3.1 Epoch section:
==================
nEpochDigitalOutput: list with as many elements as the number of epochs defined
    in the protocol = set to 1 when holding is enabled on this Dig channel
    
TODO: consider writing our own DAQEpoch class containing a common protocol 
interface for ABF and CED Signal data -> to be specialzed (subclassed) into
ABFEpoch and CEDSignalEpoch

NOTE: About holding levels and times: (from Clampex help):

"...output is held at the holding level for two "holding" periods at the start 
and end of each sweep, each 1/64th of the total sweep duration."

NOTE: 2023-09-03 22:26:46 About the 'Waveform' tab in Clampex Protocol Editor
The tabs in the bottom row (Channel #0 → 7) corresponds each to one DAC output
channel (4 for digidata 1440 series, 8 for digidata 1550 series)

A pyabf.waveform.Epoch can be constructed using the information contained in 
the 'annotations' attribute of a neo.Block generated forman ABF file via the
neo.io.axonio/neo.io.axonrawio modules.

WARNING: Epoch attribute names are case sensitive, so make sure you type 
"epochType", not "epochtype". 

The annotations["dictEpochInfoPerDAC"] is the go-to place for most of the 
information you need. For digital patterns, the information is held in 
annotations["EpochInfo"].

Be aware that dictEpochInfoPerDAC is keyed on the int DAC number (or output 
channel index); the DAC index key is mapped to a nested dict keyed on the int
epoch number (corresponding to the epoch hnumber also mapped to the "nEpochNum"
key of this nested dict).

Therefore, to access the information for the 𝒏ᵗʰ epoch on the 𝒎ᵗᴴ DAC (output)
you select:

annotations["dictEpochInfoPerDAC"][𝒎][𝒏][<key:str>], see examples below:

epoch = pab.pyabf.waveform.Epoch()

epoch.epochNumber = annotations["dictEpochInfoPerDAC"][0][0]["nEpochNum"]
# NOTE: alternatively: epoch.epochNumber = annotations["EpochInfo"][0]["nEpochNum"]

epoch.epochType = annotations["dictEpochInfoPerDAC"][0][0]["nEpochType"]

epoch.level = annotations["dictEpochInfoPerDAC"][0][0]["fEpochInitLevel"]

epoch.levelDelta = annotations["dictEpochInfoPerDAC"][0][0]["fEpochLevelInc"]

epoch.duration = annotations["dictEpochInfoPerDAC"][0][0]["lEpochInitDuration"]

epoch.durationDelta = annotations["dictEpochInfoPerDAC"][0][0]["lEpochDurationInc"]

epoch.pulsePeriod = annotations["dictEpochInfoPerDAC"][0][0]["lEpochPulsePeriod"]

epoch.pulseWidth = annotations["dictEpochInfoPerDAC"][0][0]["lEpochPulseWidth"]

# NOTE: for digital patterns see below

4. Digital outputs (and patterns)
==================================
    
4.1. ALL DAC channels are available in the protocol editor, but 
only ONE DAC channel can associate a digital output at any time.

However, turning on "Alternate digital outputs" allows one to set digital output
patterns on up to TWO DACs (which will be used on alternative Sweeps in the Run).

4.2. Digital output specification follows a relatively simple pattern in 
Clampex:
    ∘ there are two banks of four bits (total of 8 bits) 3-0 and 7-4 (yes, in 
    reverse order, I guess this is "little endian")

    ∘ for each bank the user may enter a sequence of four digits (0 or 1) to 
    turn OFF or ON the output in the corresponding position of the digit, e.g.:
    
    0001 => digital output 0 is ON, outputs 3,2,1 are OFF
    
    When a digital output is ON, this generates a digital PULSE (TTL) with
    the duration specified in the corresponding epoch number in dictEpochInfoPerDAC
    
    ∘ WARNING: This is NOT correctly read in pyabf: at any position, the user CAN
    place an asterisk ('*') instead or 0 or 1, which signifies that digital output
    corresponding to the position of the asterisk is supposed to generate a PULSE
    TRAIN; see below for details.

BEGIN Excerpt from Clampex help:

Set the digital output bit patterns for individual epochs in each of these rows.  

The four character positions in each cell correspond to, from left to right,
Digital OUT channels 3, 2, 1, 0 (for Digital bit pattern #3-0) and Digital OUT 
channels 7, 6, 5, 4 (for Digital bit pattern #7-4).

    To set a channel HIGH, place a 1 in the appropriate position.
    To set a channel LOW, place a 0 in the appropriate position.
    To have a pulse train delivered on a channel, enter an asterisk, <Shift+8>, 
    in the appropriate channel.

When a train is selected you must enter train period and pulse width values in 
the cells below.  These values are shared with any analog trains in the epoch. 
Behavior of and terminology for digital trains is the same as for analog Pulse trains.

Digital trains are inverted by unchecking the Active HI logic for digital trains
check box, above the table.    

END Excerpt from Clampex help


The difference between a "regular" digital bit flag (e.g. 0010) and a 'starred'
one is that the 'regular' one generates a digital signal (TTL) lasting as 
long as the "First duration" parameter, whereas the "starred" one generates 
a TRAIN of TTLs given the specified train frequency AND impulse 
width, all taking place within the same First duration:

For example given a protocol with only one output channel (Channel #0) for 
DAC waveform:

Analog Output #0
Waveform:
EPOCH                    A      B      C      D      E      F      G      H      I      J
Type                     Train  Off    Off    Off    Off    Off    Off    Off    Off    Off
Sample rate              Fast   Fast   Fast   Fast   Fast   Fast   Fast   Fast   Fast   Fast
First level (mV)         0      0      0      0      0      0      0      0      0      0
Delta level (mV)         0      0      0      0      0      0      0      0      0      0
First duration (samples) 200    0      0      0      0      0      0      0      0      0
Delta duration (samples) 0      0      0      0      0      0      0      0      0      0
First duration (ms)      20.0   0.0    0.0    0.0    0.0    0.0    0.0    0.0    0.0    0.0
Delta duration (ms)      0.0    0.0    0.0    0.0    0.0    0.0    0.0    0.0    0.0    0.0
Digital pattern #3-0     000*   0000   0000   0000   0000   0000   0000   0000   0000   0000
Digital pattern #7-4     0000   0000   0000   0000   0000   0000   0000   0000   0000   0000
Train Period (samples)   100    0      0      0      0      0      0      0      0      0
Pulse Width (samples)    10     0      0      0      0      0      0      0      0      0
Train Rate (Hz)          100.00 0.00   0.00   0.00   0.00   0.00   0.00   0.00   0.00   0.00
Pulse Width (ms)         1.0    0.0    0.0    0.0    0.0    0.0    0.0    0.0    0.0    0.0
Intersweep holding: same as for signal Cmd 0.
Digital train active logic: 1.

will generate a train of 1 ms TTLs at 100 Hz covering 20 ms (hence 2 pulses, 10
ms interval) on D0.

on the other hand:

Digital pattern #3-0     0001   0000   0000   0000   0000   0000   0000   0000   0000   0000

will generate one TTL boxcar lasting 20 ms on D0
    
Moreover, both the 'regular' and the 'starred' digital outputs are subject to
"Alternate  digital outputs" flag in the Waveform tab of the protocol editor.

This means that digital bit patterns in Channel#0 and Channel#1 can be different 
(NOTE: this only applies to Channel #0 and #1; Channel #2 and higher will
take the same pattern as Channel#1)

This allows alternate (i.e. interleaved) application of distinct patterns of
TTL during a run, provided there are at least two sweeps:

DIG enabled on channel:

0 ⇒ DIG output is disabled on Channel #1 UNLESSS Alternate Digital Outputs is enabled;
this is the value of nAlternateDigitalOutputState in protocol section

(When this option if unchecked, the digital bit pattern for Channel#1 is disabled)



All these are stored in the ABF v2 file as follows:

(Dec offset: 4096)

bytes 0, 1 ⇒ Epoch num (read by pyabf)
bytes 2, 3 ⇒ 'regular' bit pattern (read by pyabf)
bytes 4, 5 ⇒ 'starred' bit pattern Channel#0 (NOT read by pyabf)
bytes 6, 7 ⇒ 'regular' bit pattern Channel#1 (alternate) (NOT read by pyabf)
bytes 8, 9 ⇒ 'starred' bit pattern Channel#1 (alternate) (NOT read by pyabf)


The original pyabf code only takes into account "regular" digital bit patterns
(i.e. 0 and 1) and overlooks the fact that Clampex allows one to specify a
train of digital outputs PER Epoch PER output channel (Channel#0, #1 etc)
also using a star ('*') notation, e.g.:

Digital out #3-0: 00*0 

etc...

In contrast, axonrawio is more accurate, as it stores the digital pattern as 
int values in EpochInfo dict::

nDigitalValue -> the steps logic for banks 7-4 and 3-0
nAlternateDigitalValue -> the alternative steps logic for banks 7-4 and 3-0
    
nDigitalTrainValue -> the trains logic for banks 7-4 and 3-0
nAlternateDigitalTrainValue -> the alternative trains logic for banks 7-4 and 3-0

Whether the alternate values are enabled or not is given by 
nAlternateDigitalOutputState = 0 or 1 in the protocol dict

Total number of DIG outs:

nDigitizerSynchDigitalOuts -> for step TTLs
ndigitizerTotalDigitalOuts -> for step + pulse train TTLs

5. Protocol section
===================
annotations["protocol"]["nActiveDACChannel"]
abf._protocolSection.nActiveDACChannel

    index of the DACchannel where "Digital outputs" is enabled in the Waveform
    tab of the protocol editor
    
abf._protocolSection attributes / annotations["protocol"] key:str ↦ value:Number pairs:

nAlternateDACOutputState        0, 1    ⇐ "Alternate Waveforms" unchecked, checked
(when 1 presumes both Channel #0 and Channel #1 are used/active)

nAlternateDigitalOutputState    0, 1    ⇐ "Alternate Digital Outputs" unckecked, checked

Analog Waveform checked on Channel #0, 
Digital Outputs chacked on Channel #0, with 
    Active high logic checked ⇒ nDigitalTrainActiveLogic = 1
    Intersweep bit pattern: Use Holding (Use holding / Use last epoch)
    Alternate Digital Outputs: checked ⇒ nAlternateDigitalOutputState = 1
    Alternate Waveforms ⇒ nAlternate

    nActiveDACChannel  = 0
    nDigitalDACChannel = 0
    nDigitalHolding    = 0 (Use holding)
    nDigitalInterEpisode = 0
    

    
    

"""
import typing, struct, inspect, itertools, functools, warnings, pathlib
from functools import singledispatch, partial
import numpy as np
import pandas as pd
import quantities as pq
import neo
import pyabf

from core import quantities as scq
from core import datatypes, strutils
from core.triggerevent import (TriggerEvent, TriggerEventType)
from core.triggerprotocols import TriggerProtocol
# from iolib import pictio as pio # NOTE: not here, so we can import this from
# pictiio (pio); instead we import pio where it is needed i.e. in getABF()

from pyabf.abf1.headerV1 import HeaderV1
from pyabf.abf2.headerV2 import HeaderV2
from pyabf.abf2.section import Section
from pyabf.abfReader import AbfReader
from pyabf.stimulus import (findStimulusWaveformFile, 
                            stimulusWaveformFromFile)

from ephys.ephys import ElectrophysiologyProtocol

# useful alias:
ABF = pyabf.ABF

# This is 8 for DigiData 1550 series, and 4 for DigiData 1440 series
DIGITAL_OUTPUT_COUNT = pyabf.waveform._DIGITAL_OUTPUT_COUNT # 8

class ABFAcquisitionMode(datatypes.TypeEnum):
    """Corresponds to nOperationMode in ABF._protocolSection and annotations"""
    variable_length_event = 1
    fixed_length_event = 2
    gap_free = 3
    high_speed_oscilloscope = 4 # Not supported by neo, but supported by pyabf!
    episodic_stimulation = 5
    
    
class ABFDACWaveformSource(datatypes.TypeEnum):
    none     = 0
    epochs   = 1
    wavefile = 2
    
class ABFEpochType(datatypes.TypeEnum):
    Unknown = -1
    Off = 0
    Step = 1
    Ramp = 2
    Pulse = 3
    Triangular = 4
    Cosine = 5
    Biphasic = 7
    
class ABFEpoch:
    """Encapsulates an ABF Epoch - a building part of the DAC (command) waveform.
    Similar to pyabf.waveform.Epoch.
    
    Takes into account digital train pulses.
    """
    def __init__(self):
        self._epochNumber_ = -1
        self._epochType_ = ABFEpochType.Unknown
        self._level_ = None # -1 * pq.dimensionless
        self._levelDelta_ = None # -1 * pq.dimensionless
        # self._duration_ = None # -1 * pq.dimensionless
        self._duration_ = 0 * pq.ms
        # self._duration_in_samples_ = 0
        self._durationDelta_ = 0 * pq.ms
        # self._durtationDelta_in_samples_ = 0
        self._mainDigitalPattern_ = (tuple(), tuple())
        self._alternateDigitalPattern_ = (tuple(), tuple())
        self._useAltPattern_ = False
        self._altDIGOutState_ = False
        self._pulsePeriod_ = np.nan * pq.ms
        # self._pulsePeriod_in_samples_ = 0
        self._pulseWidth_ = np.nan * pq.ms
        # self._pulseWidth_in_samples_ = 0
        self._dacNum_ = -1
        
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        
        properties = inspect.getmembers_static(self, lambda x: isinstance(x, property))
        
        return all(np.all(getattr(self, p[0]) == getattr(other, p[0])) for p in properties)
        
        
    @property
    def epochLetter(self) -> str:
        return epochLetter(self.epochNumber)
    
    @property
    def letter(self) -> str:
        return self.epochLetter
    
    @property
    def epochNumber(self) -> int:
        return self._epochNumber_
    
    @epochNumber.setter
    def epochNumber(self, val:int):
        self._epochNumber_ = val
        
    @property
    def number(self) -> int:
        return self.epochNumber
    
    @number.setter
    def number(self, val):
        self.epochNumber = val
    
    @property
    def epochType(self) -> ABFEpochType:
        return self._epochType_
    
    @epochType.setter
    def epochType(self, val:typing.Union[ABFEpochType, str, int]):
        
        if isinstance(val, ABFEpochType):
            self._epochType_ = val
            
        elif isinstance(val, (str, int)):
            if (isinstance(val, str) and val not in ABFEpochType.names()) or (isinstance(val, int) and val not in ABFEpochType.values()):
                raise ValueError(f"Unknown ABF Epoch type {val}'")
            
            self._epochType_ = ABFEpochType.type(val)
                
        else:
            raise TypeError(f"Expecting a str, int, or an ABFEpochType; instead, got{type(val).__name__}")
        
    @property
    def type(self) -> ABFEpochType:
        """Alias to self.epochType"""
        return self.epochType
    
    @type.setter
    def type(self, val:typing.Union[ABFEpochType, str, int]):
        self.epochType = val
            
    @property
    def typeName(self) -> str:
        return self.epochType.name
    
    @property
    def firstLevel(self) -> pq.Quantity:
        return self._level_
    
    @firstLevel.setter
    def firstLevel(self, val:typing.Optional[pq.Quantity] = None):
        if isinstance(val, pq.Quantity):
            assert (scq.check_electrical_current_units(val) or scq.check_electrical_potential_units(val)), f"Expecting a quantity in A or V; instead, got {val}"
            
        else:
            self._levelDelta_ = None
            
        self._level_ = val
        
    @property
    def deltaLevel(self) -> pq.Quantity:
        return self._levelDelta_
    
    @deltaLevel.setter
    def deltaLevel(self, val:typing.Optional[pq.Quantity]= None):
        if isinstance(val, pq.Quantity):
            assert (scq.check_electrical_current_units(val) or scq.check_electrical_potential_units(val)), f"Expecting a quantity in A or V; instead, got {val}"
            if self.firstLevel is None:
                raise RuntimeError("'firstLevel' property must be set before 'deltaLevel'")
            else:
                assert scq.units_convertible(self._level_, val), f"Value units ({val.units}) are incompaibl with firstLevel units ({self._level_.units})"
        
        self._levelDelta_ = val
        
    @property
    def firstDuration(self):
        return self._duration_
    
    @firstDuration.setter
    def firstDuration(self, val:pq.Quantity):
        assert isinstance(val, pq.Quantity) and scq.check_time_units(val), f"{val} is not a time quantity"
        self._duration_ = val
        
    @property
    def deltaDuration(self):
        return self._durationDelta_
    
    @deltaDuration.setter
    def deltaDuration(self, val):
        assert isinstance(val, pq.Quantity) and scq.check_time_units(val), f"{val} is not a time quantity"
        self._durationDelta_ = val
    
    @property
    def pulsePeriod(self):
        return self._pulsePeriod_
    
    @pulsePeriod.setter
    def pulsePeriod(self, val):
        assert isinstance(val, pq.Quantity) and scq.check_time_units(val), f"{val} is not a time quantity"
        self._pulsePeriod_ = val
        
    @property
    def pulseFrequency(self):
        if float(self.pulsePeriod) == 0.:
            return 0*pq.Hz
        return (1/self.pulsePeriod).rescale(pq.Hz)
        
    @property
    def pulseWidth(self):
        return self._pulseWidth_
    
    @pulseWidth.setter
    def pulseWidth(self, val):
        assert isinstance(val, pq.Quantity) and scq.check_time_units(val), f"{val} is not a time quantity"
        self._pulseWidth_ = val
        
    @property
    def mainDigitalPattern(self) -> tuple:
        return self._mainDigitalPattern_
    
    @mainDigitalPattern.setter
    def mainDigitalPattern(self, val:tuple):
        # TODO: 2023-09-14 15:55:11
        # check the argument
        self._mainDigitalPattern_ = val
        
    @property
    def alternateDigitalPattern(self) -> tuple:
        return self._alternateDigitalPattern_
    
    @alternateDigitalPattern.setter
    def alternateDigitalPattern(self, val:tuple):
        # TODO: 2023-09-14 15:55:58
        # check the argument
        self._alternateDigitalPattern_ = val
        
    def digitalPattern(self, alternate:bool=False) -> tuple:
        """Read-only"""
        return self.alternateDigitalPattern if alternate else self.mainDigitalPattern
    
    def usedDigitalOutputChannels(self, alternate:typing.Union[bool, str]=False,
                                  trains:typing.Union[bool, str] = "all") -> list:
        """Indices of DIG channels that emit TTL trains OR TTL pulses
        
        For a more specific query (i.e. pulse v train output) see
        pulseDigitalOutputChannels and trainDigitalOutputChannels.
        
        Parameters:
        ===========
        alternate: when True, the alternate digital pattern will be queried.
        
            When a str, the only accepted value is "all". In this case, the function
            return a list of digital channel indices used in both main and alternate patterns
            (WARNING: these are not necessarily unique)
            This is useful to test if there is a digital output at all associated with
            the epoch.
            
            Another possible test, specific for a digial channel is the
            'hasDigital...' family of methods.
    
        
        """
        if isinstance(alternate, bool):
            p = self.digitalPattern(alternate)
            
            if isinstance(trains, str) and trains.lower() == "all":
                return list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(p[k]), 
                                                                    filter(lambda i: i[1] != 0, 
                                                                        enumerate(reversed(p[k]))))) for k in range(len(p))]))
            elif isinstance(trains, bool):
                val = "*" if trains else 1
                return list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(p[k]), 
                                                                    filter(lambda i: i[1] == val, 
                                                                        enumerate(reversed(p[k]))))) for k in range(len(p))]))
            else:
                raise ValueError(f"'trains' expected to be the string 'all' or a bool; instead, got {trains}")
            
        elif isinstance(alternate, str) and alternate.lower() == "all":
            p = self.digitalPattern(False)
            pa = self.digitalPattern(True)
            
            if isinstance(trains, str) and trains.lower() == "all":
                return list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(p[k]), 
                                                                    filter(lambda i: i[1] != 0, 
                                                                        enumerate(reversed(p[k]))))) for k in range(len(p))])) \
                    + list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(pa[k]), 
                                                                    filter(lambda i: i[1] != 0, 
                                                                        enumerate(reversed(pa[k]))))) for k in range(len(pa))]))
            elif isinstance(trains, bool):
                val = "*" if trains else 1
                return list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(p[k]), 
                                                                    filter(lambda i: i[1] == val,
                                                                        enumerate(reversed(p[k]))))) for k in range(len(p))])) \
                    + list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(pa[k]), 
                                                                    filter(lambda i: i[1] == val, 
                                                                        enumerate(reversed(pa[k]))))) for k in range(len(pa))]))
            else:
                raise ValueError(f"'trains' expected to be the string 'all' or a bool; instead, got {trains}")
            
        else:
            raise ValueError(f"Invalid 'alternate' specification {alternate}")
            
        
    def pulseDigitalOutputChannels(self, alternate:typing.Union[bool, str]=False) -> list:
        """Indices of DIG channel that emit a digital pulse.
        Parameters:
        ===========
        alternate: when True, the alternate digital pattern will be queried.

            When a str, the only accepted value is "all". In this case, the function
            return a list of digital channel indices used in both main and alternate patterns
            (WARNING: these are not necessarily unique)
            This is useful to test if there is a digital output at all associated with
            the epoch.
            
            Another possible test, specific for a digial channel is the
            'hasDigital...' family of methods.
        
        """
        if isinstance(alternate, bool):
            p = self.digitalPattern(alternate)
            return list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(p[k]), 
                                                                filter(lambda i: i[1] == 1, 
                                                                       enumerate(reversed(p[k]))))) for k in range(len(p))]))
        
        elif isinstance(alternate, str) and alternate.lower() == "all":
            p = self.digitalPattern(False)
            pa = self.digitalPattern(True)
            return list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(p[k]), 
                                                                filter(lambda i: i[1] == 1, 
                                                                       enumerate(reversed(p[k]))))) for k in range(len(p))])) \
                   + list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(pa[k]), 
                                                                 filter(lambda i: i[1] == 1, 
                                                                        enumerate(reversed(pa[k]))))) for k in range(len(pa))]))
        else:
            raise ValueError(f"Invalid 'alternate' specification {alternate}")
            
    def trainDigitalOutputChannels(self, alternate:typing.Union[bool, str]=False) -> list:
        """Indices of DIG channels that emit trains of digital TTL pulses.
        Parameters:
        ===========
        alternate: when True, the alternate digital pattern will be queried.

            When a str, the only accepted value is "all". In this case, the function
            return a list of digital channel indices used in both main and alternate patterns
            (WARNING: these are not necessarily unique)
            This is useful to test if there is a digital output at all associated with
            the epoch.
            
            Another possible test, specific for a digial channel is the
            'hasDigital...' family of methods.
        
        """
        if isinstance(alternate, bool):
            p = self.digitalPattern(alternate)
            return list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(p[k]), filter(lambda i: i[1] == '*', enumerate(reversed(p[k]))))) for k in range(len(p))]))

        elif isinstance(alternate, str) and alternate.lower() == "all":
            p = self.digitalPattern(False)
            pa = self.digitalPattern(True)
            return list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(p[k]), 
                                                                filter(lambda i: i[1] == '*', 
                                                                       enumerate(reversed(p[k]))))) for k in range(len(p))])) \
                   + list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(pa[k]), 
                                                                 filter(lambda i: i[1] == '*', 
                                                                        enumerate(reversed(pa[k]))))) for k in range(len(pa))]))

        else:
            raise ValueError(f"Invalid 'alternate' specification {alternate}")
        
    
    def hasDigitalOutput(self, digChannel:int = 0, alternate:bool=False) -> bool:
        """
        Checks the epochs defines an output on the specified digital channel.
        
        For a more atomic test, see self.hasDigitalPulse and self.hasDigitalTrain.
        
        This is useful to determine if the Pulse... prioperties of the epoch are
        related to any digital pattern defined in the epoch, or just to the 
        associated DAC waveform.
        
        Parameters:
        ===========
        digChannel: int in the range(8) (maximum number of digital channels)
        alternate: when True, the function will test the alternate digital pattern
        
        """
        p = self.digitalPattern(alternate)
        
        if digChannel in range(len(p[0])):
            return p[0][-digChannel-1] != 0
        
        elif len(p) == 2 and digChannel in range(len(p[0]), len(p[1])):
            return p[1][-len(p[0])+digChannel-1] != 0
        
        else:
            return False
    
    def hasDigitalPulse(self, digChannel:int = 0, alternate:bool=False) -> bool:
        """
        Checks if there is a pulse output (1) on the specified digital channel
        
        Parameters:
        ===========
        digChannel: int in the range(8) (maximum number of digital channels)
        alternate: when True, the function will test the alternate digital pattern
        
        """
        p = self.digitalPattern(alternate)
        if digChannel in range(len(p[0])):
            return p[0][-digChannel-1] == 1
        
        elif len(p) == 2 and digChannel in range(len(p[0]), len(p[1])):
            return p[1][-len(p[0])+digChannel-1] == 1
        
        else:
            return False
        
    def hasDigitalTrain(self, digChannel:int = 0, alternate:bool=False) -> bool:
        """
        Returns if there is a train output ('*') on the specified digital channel
        
        Parameters:
        ===========
        digChannel: int in the range(8) (maximum number of digital channels)
        alternate: when True, the function will test the alternate digital pattern
        
        """
        p = self.digitalPattern(alternate)
        if digChannel in range(len(p[0])):
            return p[0][-digChannel-1] == '*'
        
        elif len(p) == 2 and digChannel in range(len(p[0]), len(p[1])):
            return p[1][-len(p[0])+digChannel-1] == '*'
        
        else:
            return False

class ABFOutputConfiguration:   # placeholder to allow the definition of ABFProtocol, below
    pass
# will be (properly) redefined further below
class ABFInputConfiguration:   # placeholder to allow the definition of ABFProtocol, below
    pass                         # will be (properly) redefined further below

class ABFProtocol(ElectrophysiologyProtocol):
    def __init__(self, obj:typing.Union[pyabf.ABF,neo.Block],
                 generateOutputConfigs:bool=True,
                 generateInputConfigs:bool=True):
        super().__init__()
        if isinstance(obj, pyabf.ABF):
            abfVer = obj.abfVersion["major"]
            if abfVer !=2:
                raise NotImplementedError(f"ABF version {abfVer} is not supported")
                
            assert obj._headerV2.lActualEpisodes == obj._protocolSection.lEpisodesPerRun, f"Mismatch between lActualEpisodes ({obj._headerV2.lActualEpisodes}) and lEpisodesPerRun ({obj._protocolSection.lEpisodesPerRun})"

            # ### BEGIN ADC inputs information
            # NOTE: further info in self._inputs_
            self._nADCChannels_ = obj._adcSection._entryCount
            # ### END   ADC inputs information
            
            # ### BEGIN DAC outputs information
            # NOTE: further info in self._outputs_
            self._nDACChannels_ = obj._dacSection._entryCount
            self._activeDACChannel_ = obj._protocolSection.nActiveDACChannel
            self._hasAltDacOutState_ = bool(obj._protocolSection.nAlternateDACOutputState)
            # ### END   DAC outputs information
            
            # ### BEGIN digital outputs information
            # NOTE: further info indirectly via self._outputs_
            self._nDigitalOutputs_ = obj._dacSection._entryCount
            self._nTotalDigitalOutputs_ = obj._protocolSection.nDigitizerTotalDigitalOuts
            self._nSynchronizedDigitalOutputs_ = obj._protocolSection.nDigitizerSynchDigitalOuts
            self._hasAltDigOutState_ = bool(obj._protocolSection.nAlternateDigitalOutputState)
            self._digTrainActiveHi_ = bool(obj._protocolSection.nDigitalTrainActiveLogic)
            self._digHolding_ = obj._protocolSection.nDigitalHolding
            digHolds = list(map(bool, obj._epochSection.nEpochDigitalOutput)) # 3,2,1,0,7,6,5,4
            self._digHoldingValue_ = list(reversed(digHolds[0:4])) + list(reversed(digHolds[4:]))
            self._digUseLastEpochHolding_ = bool(obj._protocolSection.nDigitalInterEpisode)
            # ### END   digital outputs information
            
            self._acquisitionMode_ = ABFAcquisitionMode.type(obj.nOperationMode)
            self._nSweeps_ = obj._protocolSection.lEpisodesPerRun
            self._nTotalDataPoints_ = obj._dataSection._entryCount
            self._nDataPointsPerSweep_ = obj.sweepPointCount
            self._samplingRate_ = float(obj.dataRate) * pq.Hz
            self._sweepInterval_ = obj._protocolSection.fEpisodeStartToStart * pq.s
            
            self._protocolFile_ = abf.protocolPath # store this for future reference
            
            
        elif isinstance(obj, neo.Block):
            assert sourcedFromABF(obj), "Object does not appear to be sourced from an ABF file"
            assert obj.annotations["lActualEpisodes"] == obj.annotations["protocol"]["lEpisodesPerRun"], f"In {obj.name}: Mismatch between lActualEpisodes ({obj.annotations['lActualEpisodes']}) and lEpisodesPerRun ({obj.annotations['protocol']['lEpisodesPerRun']})"
            
            # ### BEGIN ADC inputs information
            # NOTE: further info in self._inputs_
            self._nADCChannels_ = obj.annotations["sections"]["ADCSection"]["llNumEntries"]
            # ### END   ADC inputs information
            
            # ### BEGIN DAC outputs information
            # NOTE: further info in self._outputs_
            self._nDACChannels_ = obj.annotations["sections"]["DACSection"]["llNumEntries"]
            self._activeDACChannel_ = obj.annotations["protocol"]["nActiveDACChannel"]
            self._hasAltDacOutState_ = bool(obj.annotations["protocol"]["nAlternateDACOutputState"])
            # ### END   DAC outputs information
            
            # ### BEGIN digital outputs information
            # NOTE: further info indirectly via self._outputs_
            self._nDigitalOutputs_ = obj.annotations["sections"]["DACSection"]["llNumEntries"]
            self._nTotalDigitalOutputs_ = obj.annotations["protocol"]["nDigitizerTotalDigitalOuts"]
            self._nSynchronizedDigitalOutputs_ = obj.annotations["protocol"]["nDigitizerSynchDigitalOuts"]
            self._hasAltDigOutState_ = bool(obj.annotations["protocol"]["nAlternateDigitalOutputState"])
            self._digTrainActiveHi_ = bool(obj.annotations["protocol"]["nDigitalTrainActiveLogic"])
            self._digHolding_ = obj.annotations["protocol"]["nDigitalHolding"]
    
            # allow the use of blocks read from ABF before 2023-09-20 23:26:08
            digHolds = obj.annotations["sections"]["EpochSection"].get("nEpochDigitalOutput", None) # 3,2,1,0,7,6,5,4
    
            if isinstance(digHolds, list) and len(digHolds) == self._nDigitalOutputs_:
                digHolds = list(map(bool, digHolds))
                if self._nDigitalOutputs_ == 8:
                    digHolds = list(reversed(digHolds[:4])) + list(reversed(digHolds[4:]))
                    
                else:
                    digHolds = list(reversed(digHolds))
                    
                self._digHoldingValue_ = digHolds
                
            else:
                self._digHoldingValue_ = [False] * self._nDigitalOutputs_
                
            self._digUseLastEpochHolding_ = bool(obj.annotations["protocol"]["nDigitalInterEpisode"])
            # ### END   digital outputs information
            
            self._acquisitionMode_ = ABFAcquisitionMode.type(obj.annotations["protocol"]["nOperationMode"]), 
            self._nSweeps_ = obj.annotations["protocol"]["lEpisodesPerRun"]
            self._nTotalDataPoints_ = obj.annotations["sections"]["DataSection"]["llNumEntries"]
            self._nDataPointsPerSweep_ = int(self._nTotalDataPoints_/self._nSweeps_/self._nADCChannels_)
            self._samplingRate_ = float(obj.annotations["sampling_rate"]) * pq.Hz
            self._sweepInterval_ = obj.annotations["protocol"]["fEpisodeStartToStart"] * pq.s
            
            self._protocolFile_ = obj.annotations["sProtocolPath"].decode()

        else:
            raise TypeError(f"Expecting a pyabf.ABF or a neo.Block; instead, got {type(obj).__name__}")
        
        # since Clampex only runs on Windows, we simply split the string up:
        self._name_ = pathlib.Path(self._protocolFile_.split("\\")[-1]).stem  # strip off the extension
        
        self._sourceHash_ = hash(obj)
        self._sourceId_ = id(obj)
        
        self._sweepDuration_ = (self._nDataPointsPerSweep_ / self._samplingRate_).rescale(pq.s)
        self._totalDuration_ = self._nSweeps_ * (self._sweepDuration_ if self._sweepInterval_ == 0*pq.s else self._sweepInterval_)
        if self._nSweeps_ > 1:
            self._totalDuration_ += self._sweepDuration_
            
        self._nAlternateDigitalOutputs = self._nTotalDigitalOutputs_ - self._nSynchronizedDigitalOutputs_
        
        self._nDataPointsHolding_ = int(self._nDataPointsPerSweep_/64)
        
        self._inputs_ = [ABFInputConfiguration(obj, self, k) for k in range(self._nADCChannels_)]
        self._outputs_ = [ABFOutputConfiguration(obj, self, k) for k in range(self._nDACChannels_)]
            
    def __eq__(self, other):
        """Tests for equality of scalar properties and epochs tables.
        Epochs tables are checked for equality sweep by sweep, in all channels.
        
        WARNING: This includes any digital output patterns definded.
        
        If this is not intended, then use self.is_identical_except_digital(other)
        """
        if not isinstance(other, self.__class__):
            return False
        
        properties = inspect.getmembers_static(self, lambda x: isinstance(x, property))
        
        # check equality of properties (descriptors); this includes nSweeps and nADCChannels
        ret = all(np.all(getattr(self, p[0]) == getattr(other, p[0])) for p in properties)

        # if checked out then verify all epochs Tables are sweep by sweep 
        # identical in all DAC channels, including digital output patterns!
        if ret:
            ret = all(all(np.all(self.outputConfiguration(d).epochsTable(s) == other.outputConfiguration(d).epochsTable(s)) for s in range(self.nSweeps)) for d in range(self.nDACChannels))
                    
        return ret
    
    def is_identical_except_digital(self, other):
        if not isinstance(other, self.__class__):
            return False
        
        properties = inspect.getmembers_static(self, lambda x: isinstance(x, property))
        
        # check equality of properties (descriptors); this includes nSweeps and nADCChannels
        ret = all(np.all(getattr(self, p[0]) == getattr(other, p[0])) for p in properties)
        
        if ret:
            ret = all(all(np.all(self.outputConfiguration(d).epochsTable(s, includeDigitalPattern=False) == other.outputConfiguration(d).epochsTable(s, includeDigitalPattern=False)) for s in range(self.nSweeps)) for d in range(self.nDACChannels))
                    
        return ret
    
    @property
    def adcNames(self):
        return [i.name for i in self.inputs]
    
    @property
    def adcUnits(self):
        return [i.units for i in self.inputs]
    
    @property
    def adcLogical2PhysicalIndexMap(self):
        return dict((i.logicalIndex, i.physicalIndex) for i in self.inputs)
            
    @property
    def adcPhysical2LogicalIndexMap(self):
        return dict((i.physicalIndex, i.logicalIndex) for i in self.inputs)
    
    @property
    def dacNames(self):
        return [o.name for o in self.outputs]
            
    @property
    def dacUnits(self):
        return [o.units for o in self.outputs]
            
    @property
    def dacLogical2PhysicalIndexMap(self):
        return dict((i.logicalIndex, i.physicalIndex) for i in self.outputs)
            
    @property
    def dacPhysical2LogicalIndexMap(self):
        return dict((i.physicalIndex, i.logicalIndex) for i in self.outputs)
    
    @property
    def acquisitionMode(self) -> ABFAcquisitionMode:
        return self._acquisitionMode_
    
    @property
    def activeDACChannelIndex(self) -> int:
        """Index of the "active" DAC channel.
        
        The active DAC channel is the DAC channel that:
        
        • sends out the MAIN DIGITAL output - irrespective of whether it 
            also has analog waveform enabled or not.
        
        • when no DAC is sending digital output, it is the channel with the 
            highest index that sends out analog waveforms
            
        Works for most cases where a single DAC (0 or 1) is used , but currently
        meaningless when no analog or digital commands are sent at all or with
        atypical connections and DAC configurations (see comments in the code)
        
        
        Swithching DIG off in all DACs returns 0 here.
        
        
        Therefore, to find out which DAC is associated with stimuli in your experiment:
        
        TODO/FIXME 
        
        """
        # NOTE: 2023-10-09 13:31:58
        # Beyond DAC1, the active DAC index returns the highest DAC index in use.
        # HOWEVER, it appears that the highest value returned here is 3 (as if there 
        # were a maximum of 4 DACs - from 0 to 3 - this may be a limitation in my 
        # simulations)
        #
        # This is either not very useful or I fail to understand this:
        # 
        # Two identical protocols except for the DAC used report the same number:
        # protocol 1: alternateDigitalOutputStateEnabled True
        #             DAC0 analogWaveformEnabled True, digitalOutputEnabled True
        #             DAC1 analogWaveformEnabled False, digitalOutputEnabled False, but enabled on Channel #0
        #             
        # protocol 2: alternateDigitalOutputStateEnabled True
        #             DAC0 analogWaveformEnabled False, digitalOutputEnabled True
        #             DAC1 analogWaveformEnabled True, digitalOutputEnabled False, but enabled on Channel #0
        # 
        # both report self._activeDACChannel_ 0 (in pyabf this is regardless of sweep)
        
        # However: if alternateDigitalOutputStateEnabled is False AND 
        #     both analogWaveformEnabled and digitalOutputEnabled are enabled in 
        #     the same DAC then activeDACChannelIndex is the index of said DAC output.
        #
        #
        # NOTE: DIG OUT CAN ONLY BE ENABLED ON A SINGLE DAC!
        #
        # protocol with:
        #               DAC0:   DAC1:       Alt wave    Alt Dig     Returns:
        #   analog      1       1           0           1           0
        #   digital     1       0
        #
        #   analog      1       1           0           1           1
        #   digital     0       1
        #
        #   analog      0       1           0           1           1                              
        #   digital     0       1
        #
        #   analog      1       0           0           1           1                              
        #   digital     0       1
        #
        #   analog      0       1           0           1           0                           
        #   digital     1       0
        #
        #   analog      1       1           1           1           0         
        #   digital     1       0
        #
        #   analog      1       1           1           1           1
        #   digital     0       1
        #
        #   analog      0       1           1¹          1           1                           
        #   digital     0       1
        #
        #   analog      1       0           1¹          1           1                              
        #   digital     0       1
        #
        #   analog      0       1           1¹          1           0                           
        #   digital     1       0
        #
        #   analog      1       1           1           0           0         
        #   digital     1       0
        #
        #   analog      1       1           1           0           1
        #   digital     0       1
        #
        #   analog      0       1           1¹          0           1
        #   digital     0       1
        #
        #   analog      1       0           1¹          0           1                              
        #   digital     0       1
        #
        #   analog      0       1           1¹          0           0                           
        #   digital     1       0
        #
        #   analog      1       1           1           0           ?0         
        #   digital     1       0
        #
        #   analog      1       1           1           0           ?1
        #   digital     0       1
        #
        #   analog      0       1           1¹          0           ?1
        #   digital     0       1
        #
        #   analog      1       0           1¹          0           ?1                              
        #   digital     0       1
        #
        #   analog      0       1           1¹          0           0                           
        #   digital     1       0
        #
        #
        #   analog      1       1           0           0           0                           
        #   digital     0       0
        #
        #   analog      1       1           1           0           0
        #   digital     0       0
        #
        #   analog      1       0           0¹          0           0
        #   digital     0       0
        #
        #   analog      0       1           0¹          0           0! ???
        #   digital     0       0
        #
        #   analog      0       1           1¹          0           0!
        #   digital     0       0
        #
        #   analog      0       0           1¹          0           0!
        #   digital     0       0
        #
        #               DAC2    DAC3
        #   analog      1       0           1¹          1           2
        #   digital     1       0
        #
        #   analog      0       1           1¹          1           3
        #   digital     0       1
        #
        #   analog      0       1           1¹          1           3
        #   digital     0       0
        #
        #   analog      1       1           1           1           3!
        #   digital     0       0
        #
        #   analog      1       1           0           1           3!
        #   digital     0       0
        #
        #               DAC3    DAC4
        #   analog      1       1           0           1           3!
        #   digital     0       0
        #
        #   analog      0       1           0           1           3!
        #   digital     0       0
        #
        #                       DAC5
        #   analog      0       1           0           1           3!
        #   digital     0       0
        #
        #               DAC2    DAC>2
        #   analog      1       1           0           1           3!
        #   digital     0       0
        #
        #               DAC2    DAC5
        #   analog      1       1           0           1           2 AHA!
        #   digital     1       0
        #
        # ¹ irrelevant here
        #
        
        #   
        
        # BUG: 2023-10-15 23:38:59 code with circular dependency
        # # NOTE: 2023-10-15 21:56:55
        # # this can have AT MOST one element
#         digSendingDacs = list(c for c in range(self.nDACChannels) if self.outputConfiguration(c).digitalOutputEnabled)
#         
#         if len(digSendingDacs): 
#             return digSendingDacs[-1]
        
        return self._activeDACChannel_
    
    @property
    def nADCChannels(self) -> int:
        return self._nADCChannels_
    
    @property
    def nInputChannels(self) -> int:
        return self.nADCChannels
    
    @property
    def nDACChannels(self) -> int:
        return self._nDACChannels_
    
    @property
    def nOutputChannels(self) -> int:
        return self.nDACChannels
    
    @property
    def nDigitalOutputs(self)->int:
        return self._nDigitalOutputs_
    
    @property
    def nSychronizedDigitalOutChannels(self) -> int:
        return self._nSynchronizedDigitalOutputs_
    
    @property
    def nDigitalChannels(self) -> int:
        return self.nSychronizedDigitalOutChannels
    
    @property
    def nAlternateDigitalOutChannels(self) -> int:
        return self._nAlternateDigitalOutputs
    
    @property
    def nAlternateDigitalChannels(self) -> int:
        return self.nAlternateDigitalOutChannels
    
    @property
    def digitalTrainActiveLogic(self) -> bool:
        return self._digTrainActiveHi_
    
    @property
    def digitalHolding(self) -> int:
        return self._digHolding_
    
    def digitalHoldingValue(self, digChannel) -> bool:
        return self._digHoldingValue_[digChannel]
    
    @property
    def digitalUseLastEpochHolding(self) -> bool:
        return self._digUseLastEpochHolding_
            
    @property
    def nSweeps(self) -> int:
        return self._nSweeps_
    
    @property
    def nSamples(self) -> int:
        return self._nTotalDataPoints_
    
    @property
    def sweepSampleCount(self) -> int:
        return self._nDataPointsPerSweep_
    
    @property
    def samplingRate(self) -> pq.Quantity:
        return self._samplingRate_
    
    @property
    def holdingTime(self) -> pq.Quantity:
        """Read-only (determined by Clampex).
        This corresponds 1/64 samples of total samples in a sweep"""
        samplingPeriod = (1/self.samplingRate).rescale(pq.s)
        return self.holdingSampleCount * samplingPeriod
    
    @property
    def holdingSampleCount(self) -> int:
        return self._nDataPointsHolding_
    
    @property
    def protocolFile(self) -> str:
        if not hasattr(self, "_protocolFile_"):
            self._protocolFile_ = ""
        return self._protocolFile_
    
    @property
    def name(self)->str:
        if not hasattr(self, "_name_"):
            self._name_ = "protocol"
        return self._name_
    
    @property
    def duration(self) -> pq.Quantity:
        return self._totalDuration_
    
    @property
    def sweepDuration(self) -> pq.Quantity:
        return self._sweepDuration_
    
    @property
    def sweepInterval(self) -> pq.Quantity:
        """Time interval between the starts of successive sweeps"""
        return self._sweepInterval_
    
    @property
    def alternateDigitalOutputStateEnabled(self) -> bool:
        return self._hasAltDigOutState_
    
    @property
    def alternateDACOutputStateEnabled(self) -> bool:
        return self._hasAltDacOutState_
    
    @property
    def sweepTimes(self) -> pq.Quantity:
        return np.array(list(map(self.sweepTime, range(self.nSweeps)))) * pq.s
    
    def digitalOutputs(self, alternate:typing.Union[bool, str] = "all", trains:typing.Union[str, bool] = "all") -> set:
        """Returns the indices of digital output channels used in this protocol.
    
        By default, returns ALL channels used in both main and alternate patterns,
        for either TTL pulses OR TTL trains.
        
        This behaviour can be controlled with the two parameters:
        
        • alterante (False/True/"all") - default is "all"
        
        • trains (False/True/"all") - default is "all"
        
        """
        
        return set(itertools.chain.from_iterable([list(itertools.chain.from_iterable([e.usedDigitalOutputChannels(alternate, trains) for e in o.epochs])) for o in self.outputs]))

    def clampMode(self, adcIndex:int = 0,
                  dacIndex:typing.Optional[int] = None):
        from ephys.ephys import ClampMode
        adc = self.inputConfiguration(adcIndex) # get first (primary) input by default

        if adc is None:
            raise ValueError(f"ADC index {adcIndex} is invalid for this protocol")

        recordsCurrent = scq.check_electrical_current_units(adc.units)
        recordsPotential = scq.check_electrical_potential_units(adc.units)

        dac = self.outputConfiguration(dacIndex) # get active DAC by default

        commandIsCurrent = scq.check_electrical_current_units(dac.units)
        commandIsPotential = scq.check_electrical_potential_units(dac.units)


        if recordsPotential and commandIsCurrent:
            return ClampMode.CurrentClamp
        elif recordsCurrent and commandIsPotential:
            return ClampMode.VoltageClamp
        else:
            return ClampMode.NoClamp

    def sweepTime(self, sweep:int = 0) -> pq.Quantity:
        if self.sweepInterval == 0*pq.s:
            return sweep * self.sweepDuration
        return sweep * self.sweepInterval
    
    @property
    def inputs(self):
        return self._inputs_

    def inputConfiguration(self, adcChannel:typing.Union[int, str] = 0, physical:bool=False) -> ABFInputConfiguration:
        if isinstance(adcChannel, str):
            if adcChannel not in self.adcNames:
                raise ValueError(f"Invalid ADC channel name {adcChannel}")
            
            adcChannel = self.adcNames.index(adcChannel)
            
            if physical:
                adcChannel = self.adcLogical2PhysicalIndexMap[adcChannel]

        inputconfs = list(filter(lambda x: x.channelIndex(physical) == adcChannel, self._inputs_))
        
        if len(inputconfs):
            return inputconfs[0]
        else:
            chtype = "physical" if physical else "logical"
            raise ValueError(f"Invalid {chtype} ADC channel specified {adCChannel}")

    def input(self, adcChannel:int = 0, physical:bool=False) -> ABFInputConfiguration:
        """Shorthand to self.inputConfiguration"""
        return self.inputConfiguration(adcChannel, physical)
    
    @property
    def outputs(self):
        return self._outputs_
    
    def outputConfiguration(self, dacChannel:typing.Optional[typing.Union[int, str]] = None, physical:bool=False) -> ABFOutputConfiguration:
        # if not isinstance(dacChannel, int):
        if dacChannel is None:
            dacChannel = self.activeDACChannelIndex
            
        elif isinstance(dacChannel, str):
            if dacChannel not in self.dacNames:
                raise ValueError(f"invaid DAC channel name {dacChannel}")
            
            dacChannel = self.dacNames.index(dacChannel)
            
            if physical:
                dacChannel = self.dacLogical2PhysicalIndexMap[dacChannel]

        outputConfs = list(filter(lambda x: x.dacChannel == dacChannel, self._outputs_))

        if len(outputConfs):
            return outputConfs[0]
        else:
            chtype = "physical" if physical else "logical"
            raise ValueError(f"Invalid {chtype} DAC channel specified {dacChannel}")
            
            
    def output(self, dacChannel:typing.Optional[typing.Union[int, str]] = None, 
               physical:bool=False) -> ABFOutputConfiguration:
        """Shorthand to self.outputConfiguration"""
        return self.outputConfiguration(dacChannel, physical)
        
class ABFInputConfiguration:
    """Deliberately thin class with basic info about an ADC input in Clampex.
        More information may be added for convenience later; until then, just
        explore the neo.Block annotations (assuming the Block was created from an
        Axon ABF file) or the relevanmt sections in an ABF object created using
        pyabf.

        Also note that most relevant information is already parsed by the neo.io
        classes when the AnalogSignals are constructed using the input data in
        the ABF.

    """
    def __init__(self, obj:typing.Union[pyabf.ABF, neo.Block],
                 protocol:typing.Optional[ABFProtocol] = None,
                 adcChannel:int = 0, physical:bool=False):
        """
        obj: ABF object or neo.Block; both must be read from an ABF file
        adcChannel: logical or physical index of the channel sought (0 -> max ADC channels available)
        physical: default False, meaning that adcChannel is the logical number
            When True, then adcChannel is interpreted as the physical channel

            Explanation:

            The ABF protocol can be configured to record data from up to the
            maximum number of input channels available in the DAQ board.

            These inputs get a logical number (0 → number of USED ADC channels in
            the protocol). Furthermore, one has the option to select WHICH pysical
            channel is allocated to a particular logical input channel, depending
            which physical channels have been already matched to logical inputs,
            e.g.:

            Input 0 → IN0
            Input 1 → IN1
            Input 2 → IN3 !!!
            Input 3 → IN5 !!! (assuming there are 8 inputs in the hardware this
                               can take any channel from IN4 to IN7)
            ⋮
            etc

            Therefore, when we query for an ADC channel we need to distinguish
            between a query by logical or physical index. In the first case,
            passing adcChannel = 3 gets us the physical input channel IN5 matched
            to logical channel 3; in the latter case we get the physical input
            channel IN3 matched to logical channel 2!
        """
        if protocol is None:
            protocol =  ABFProtocol(obj)

        elif not isinstance(protocol, ABFProtocol):
            raise TypeError(f"'protocol' expected to be an ABFProtocol object; instead, got {type(protocol).__name__}")

        self._protocol_ = protocol

        assert self._protocol_._sourceHash_ == hash(obj) and self._protocol_._sourceId_ == id(obj), f"The source {type(obj).__name__} object does not appear linked to the supplied protocol"

        if isinstance(obj, pyabf.ABF):
            abfVer = obj.abfVersion["major"]
            if abfVer == 1:
                raise NotImplementedError(f"ABF version {abfVer} is not supported")
                # if dacChannel > 1:
                #     dacChannel = 0
                # self._interEpisodeLevel_ = bool(obj._headerV1.nInterEpisodeLevel[dacChannel])
                # self._dacChannel_ = dacChannel
                # TODO finalize this...

            elif abfVer == 2:
                if adcChannel not in obj._adcSection.nADCnum or adcChannel not in range(len(obj._adcSection.nADCNum)):
                    raise ValueError(f"Invalid DAC channel index {adcChannel}")

                self._adcChannel_ = adcChannel
                self._physicalChannelIndex_ = None

                if physical:
                    if adcChannel in obj._adcSection.nADCNum:
                        self._physicalChannelIndex_ = adcChannel
                        logical = obj._adcSection.nADCNum.index(adcChannel)
                        self._adcChannel_ = logical
                        adcName = obj.adcNames[logical]
                        adcUnits = obj.adcUnits[logical]
                    else:
                        adcName = ""
                        adcUnits = ""
                else:
                    if adcChannel not in range(len(obj.adcNames)):
                        adcName = ""
                        adcUnits = ""
                    else:
                        self._physicalChannelIndex_ = obj._adcSection.nADCNum[adcChannel]
                        adcName = obj.adcNames[adcChannel]# if adcChannel in obj.adcNames else
                        adcUnits = obj.adcUnits[adcChannel]

            else:
                raise NotImplementedError(f"ABF version {abfVer} is not supported")

        elif isinstance(obj, neo.Block):
            assert sourcedFromABF(obj), "Object does not appear to be sourced from an ABF file"

            if physical:
                p = [v["nADCNum"] for v in obj.annotations["listADCInfo"]]
                if adcChannel not in p:
                    adcName = ""
                    adcUnits = ""
                else:
                    self._physicalChannelIndex_ = adcChannel
                    logical = p.index(adcChannel)
                    self._adcChannel_ = logical
                    adcName = obj.annotations["listADCInfo"][logical]["ADCChNames"].decode()
                    adcUnits = obj.annotations["listADCInfo"][logical]["ADCChUnits"].decode()
            else:
                if adcChannel not in range(len(obj.annotations["listADCInfo"])):
                    adcName = ""
                    adcUnits = ""
                else:
                    self._adcChannel_ = adcChannel
                    self._physicalChannelIndex_ = obj.annotations["listADCInfo"][adcChannel]["nADCNum"]
                    adcName = obj.annotations["listADCInfo"][adcChannel]["ADCChNames"].decode()
                    adcUnits = obj.annotations["listADCInfo"][adcChannel]["ADCChUnits"].decode()

                    # raise ValueError(f"Invalid ADC channel index {adcChannel}")

        self._adcName_ = adcName
        self._adcUnits_ = scq.unit_quantity_from_name_or_symbol(adcUnits)

    def channelIndex(self, physical:bool=False) -> int:
        return self.physicalIndex if physical else self.logicalIndex

    @property
    def logicalIndex(self) -> int:
        return self._adcChannel_
    
    @property
    def number(self) -> int:
        """Alias to self.logicalIndex"""
        return self.logicalIndex

    @property
    def physicalIndex(self) -> int:
        return self._physicalChannelIndex_
    
    @property
    def physical(self) -> int:
        """Alias to self.physicalIndex"""
        return self.physicalIndex
    
    @property
    def adcName(self) -> str:
        return self._adcName_

    @property
    def name(self) -> str:
        return self._adcName_
    
    @property
    def adcUnits(self) -> pq.Quantity:
        return self._adcUnits_

    @property
    def units(self) -> pq.Quantity:
        return self._adcUnits_
    
    @property
    def protocol(self) -> ABFProtocol:
        return self._protocol_

class ABFOutputConfiguration:
    """Configuration of a DAC channel and digital outputs in pClamp/Clampex ABF files.
        
    An ABFOutputConfiguration contains the information related to the use of a 
    particular DAC channel (between 0 and the maximum number of DAC outputs of 
    your DAQ hardware - 1, e.g., for DigiData series 1550 there are 8 DAC channels,
    hence a DAC channel can be between 0 and 7).
    
    An ABFOutputConfiguration object encapsulates information accessed through
    the Waveform tab of the Clampex protocol editor, with a Channel tab selected
    for the specified DAC channel.
        
    This information includes Epoch waveforms AND digital output configuration
        (i.e, pulses or trains).
        
    The class only makes sense for episodic stimulation experiments in Clampex.
        
    """
    # NOTE: 2023-09-17 23:41:15
    # index of the DAC where Digital output IS enabled is given by 
    #   annotations["protocol"]["nActiveDACChannel"]
    #       (counter-intuitive: expecting to see this from nDigitalDACChannel and nDigitalEnable
    #       but these seem to be 0 and 1 regardless of which DAC has waveform enabled and dig enabled)
    #
    # index of the DAC where waveform is enabled is the κ index in annotations["listDACInfo"],
    # where 
    #   annotations["listDACInfo"][κ]["nWaveformEnable"] == 1
    # 
    # there are the following possibilities:
    # Alt waveform  | Alt Dig | DAC waveform enabled | DAC Digital output enabled
    #----------------------------------------------------------------------------
    def __init__(self, obj:typing.Union[pyabf.ABF, neo.Block],
                 protocol:typing.Optional[ABFProtocol] = None,
                 dacChannel:int = 0, physical:bool=False):
        
        if protocol is None:
            protocol = ABFProtocol(obj)

        elif not isinstance(protocol, ABFProtocol):
            raise TypeError(f"'protocol' expected to be an ABFProtocol object; instead, got {type(protocol).__name__}")
        
        self._protocol_ = protocol
        
        assert self._protocol_._sourceHash_ == hash(obj) and self._protocol_._sourceId_ == id(obj), f"The source {type(obj).__name__} object does not appear linked to the supplied protocol"
        
        if isinstance(obj, pyabf.ABF):
            abfVer = obj.abfVersion["major"]
            if abfVer == 1:
                raise NotImplementedError(f"ABF version {abfVer} is not supported")
                # if dacChannel > 1:
                #     dacChannel = 0
                # self._interEpisodeLevel_ = bool(obj._headerV1.nInterEpisodeLevel[dacChannel])
                # self._dacChannel_ = dacChannel
                # TODO finalize this...
                
            elif abfVer == 2:
                if dacChannel not in obj._dacSection.nDACNum or dacChannel not in range(len(obj._dacSection.nDACNum)):
                    raise ValueError(f"Invalid DAC channel index {dacChannel}")
                
                self._dacChannel_ = dacChannel
                self._physicalChannelIndex_ = None
                
                if physical:
                    if dacChannel in obj._dacSection.nDACNum:
                        self._physicalChannelIndex_ = dacChannel
                        logical = obj._dacSection.nDACNum[dacChannel]
                        self._dacChannel_ = logical
                        dacName = obj.dacNames[logical]
                        dacUnits = obj.dacUnits[logical]
                    else:
                        dacName = ""
                        dacUnits = ""
                        
                else:
                    if dacChannel not in range(len(obj.dacNames)):
                        dacName =""
                        dacUnits = ""
                        
                    else:
                        self._physicalChannelIndex_ = obj._dacSection.nDACNum[dacChannel]
                        dacName = obj.dacNames[dacChannel]
                        dacUnits = obj.dacUnits[dacChannel]
                        
                
                # dacName = obj.dacNames[dacChannel]# if dacChannel in obj.dacNames else ""
                # dacUnits = obj.dacUnits[dacChannel]# if dacChannel in obj.dacUnits else "mV"
                
                self._dacName_ = dacName 
                self._dacUnits_ = scq.unit_quantity_from_name_or_symbol(dacUnits)
                self._dacHoldingLevel_ = float(obj._dacSection.fDACHoldingLevel[self._dacChannel_]) * self._dacUnits_
                self._interEpisodeLevel_ = bool(obj._dacSection.nInterEpisodeLevel[self._dacChannel_])
                
                # command (analog) waveform flags:
                self._waveformEnabled_ = bool(obj._dacSection.nWaveformEnable[self._dacChannel_])
                
                wsrc = obj._dacSection.nWaveformSource[self._dacChannel_]
                
                if wsrc in range(3):
                    self._waveformSource_ = ABFDACWaveformSource.type(wsrc)
                else:
                    self._waveformSource_ = ABFDACWaveformSource.none
                
                # # digital (TTL) waveform flags & parameters:
                # NOTE 2023-10-17 17:31:40 FIXME
                # not sure this is the correct approach
                self._digOutEnabled_ = self._dacChannel_ == self.protocol.activeDACChannelIndex
            else:
                raise NotImplementedError(f"ABF version {abfVer} is not supported")
            
        elif isinstance(obj, neo.Block):
            assert sourcedFromABF(obj), "Object does not appear to be sourced from an ABF file"
            # if dacChannel not in (c["nDACNum"] for c in obj.annotations["listDACInfo"]):
            #     raise ValueError(f"Invalid DAC channel index {dacChannel}")
            
            if physical:
                p = [v["nDACNum"] for v in obj.annotations["listDACInfo"]]
                if dacChannel not in p:
                    dacName = ""
                    dacUnits = ""
                else:
                    self._physicalChannelIndex_ = dacChannel
                    logical = p.index(dacChannel)
                    self._dacChannel_ = logical
                    dacName = obj.annotations["listDACInfo"][logical]["DACChNames"].decode()
                    dacUnits = obj.annotations["listDACInfo"][logical]["DACChUnits"].decode()
            else:
                if dacChannel not in range(len(obj.annotations["listDACInfo"])):
                    dacName = ""
                    dacUnits = ""
                else:
                    self._dacChannel_ = dacChannel
                    self._physicalChannelIndex_ = obj.annotations["listDACInfo"][dacChannel]["nDACNum"]
                    dacName = obj.annotations["listDACInfo"][dacChannel]["DACChNames"].decode()
                    dacUnits = obj.annotations["listDACInfo"][dacChannel]["DACChUnits"].decode()
                    
            self._dacName_ = dacName
            self._dacUnits_ = scq.unit_quantity_from_name_or_symbol(dacUnits)

            self._dacHoldingLevel_ = float(obj.annotations["listDACInfo"][self._dacChannel_]["fDACHoldingLevel"]) * self._dacUnits_
            self._interEpisodeLevel_ = bool(obj.annotations["listDACInfo"][self._dacChannel_]["nInterEpisodeLevel"])
            
            # command (analog) waveform flags:
            self._waveformEnabled_ = bool(obj.annotations["listDACInfo"][self._dacChannel_]["nWaveformEnable"])
            
            wsrc = obj.annotations["listDACInfo"][self._dacChannel_]["nWaveformSource"]
            
            if wsrc in range(3):
                self._waveformSource_ = ABFDACWaveformSource.type(wsrc)
            else:
                self._waveformSource_ = ABFDACWaveformSource.none
                
            # digital (TTL) waveform flags & parameters:
            # NOTE: 2023-10-17 17:31:20 FIXME
            # not sure this is the correct approach
            self._digOutEnabled_ = self._dacChannel_ == self.protocol.activeDACChannelIndex
            
        else:
            raise TypeError(f"Expecting an ABF or a neo.Block sourced from an ABF file; instead, got {type(obj).__name__}")
    
        if np.abs(self._dacHoldingLevel_).magnitude > 1e6:
            self._dacHoldingLevel_ = np.nan * self.dacUnits
            
        elif np.abs(self._dacHoldingLevel_).magnitude > 0 and np.abs(self._dacHoldingLevel_).magnitude < 1e-6:
            self._dacHoldingLevel_ = 0.0 * self.dacUnits
            
        self._epochs_ = list()
        
        self._init_epochs_(obj)
        
    def _init_epochs_(self, obj):
        if isinstance(obj, pyabf.ABF):
            self._init_epochs_abf_(obj)
            
        else:
            digPatterns = getDIGPatterns(obj)
            if self._dacChannel_ in obj.annotations["dictEpochInfoPerDAC"]:
                dacEpochDict = obj.annotations["dictEpochInfoPerDAC"][self.logicalIndex]
                epochs = list()
                for epochNum, epochDict in dacEpochDict.items():
                    epoch = ABFEpoch()
                    epoch.epochNumber = epochNum
                    epoch.epochType = epochDict["nEpochType"]
                    epoch.firstLevel = epochDict["fEpochInitLevel"] * self.dacUnits
                    epoch.deltaLevel = epochDict["fEpochLevelInc"] * self.dacUnits
                    epoch.firstDuration = (epochDict["lEpochInitDuration"] / self.samplingRate).rescale(pq.ms)
                    epoch.deltaDuration = (epochDict["lEpochDurationInc"] / self.samplingRate).rescale(pq.ms)
                    epoch.pulsePeriod = (epochDict["lEpochPulsePeriod"] / self.samplingRate).rescale(pq.ms)
                    epoch.pulseWidth = (epochDict["lEpochPulseWidth"] / self.samplingRate).rescale(pq.ms)
                    epoch.mainDigitalPattern = digPatterns[epoch.epochNumber]["main"]
                    epoch.alternateDigitalPattern = digPatterns[epoch.epochNumber]["alternate"]

                    epochs.append(epoch)
                
                self._epochs_ = epochs
            
    def _init_epochs_abf_(self, obj):
        # NOTE: no digital patterns in ABFv1 ?
        abfVer = obj.abfVersion["major"]
        epochs = list()
        
        if abfVer == 1:
            raise NotImplementedError(f"ABf version {abfVer} is not supported")
#             assert len(obj._headerV1.nEpochType) == 20, f"Expecting 20 memory slots for epoch info; instead got {len(obj._headerV1.nEpochType)}"
#             
#             for i in range(20):
#                 epoch = ABFEpoch()
#                 epoch.epochNumber = i % 10 # first -> 0-9: channel 0; last 0-9 -> channel 1
#                 epoch.epochType = obj._headerV1.nEpochType[i]
#                 epoch.firstLevel = obj._headerV1.fEpochInitLevel[i] * self._dacUnits_
#                 epoch.deltaLevel = obj._headerV1.fEpochLevelInc[i] * self._dacUnits_
#                 epoch.firstDuration = (obj._headerV1.lEpochInitDuration[i] / self._samplingRate_).rescale(pq.ms)
#                 epoch.deltaDuration = (abf._headerV1.lEpochDurationInc[i] / self._samplingRate_).rescale(pq.ms)
#                 epoch.pulsePeriod = 0 * pq.ms # not supported in ABF1
#                 epoch.pulseWidth = 0 * pq.ms # not supported in ABF1
#                 epochs.append(epoch)
#                 
#             if self._dacChannel_ == 0:
#                 self._epochs_ = epochs[0:10]
#                 
#             elif self._dacChannel_ == 1:
#                 self._epochs_ = epochs[10:20]
#             else:
#                 warnings.debug("ABF1 does not support stimulus waveforms >2 DACs")
#                 self._epochs_.clear()
                
        elif abfVer == 2:
            digPatterns = getDIGPatterns(obj)
            
            # the epoch table is stored in _epochPerDacSection
            for i, epochDacNum in enumerate(obj._epochPerDacSection.nDACNum):
                # FIXME: 2023-09-14 22:49:09
                # for alternate DIG outputs you need TWO DACs even if only one
                # DAC channel is used!
                # RESOLVED?: you DO NOT need this info here
                
                # NOTE: 2023-09-18 14:46:37 skip epochs NOT defined for this DAC
                if epochDacNum != self.dacChannel:
                    continue

                epoch = ABFEpoch()
                epoch.epochNumber = obj._epochPerDacSection.nEpochNum[i]
                epoch.epochType = obj._epochPerDacSection.nEpochType[i]
                epoch.firstLevel = obj._epochPerDacSection.fEpochInitLevel[i] * self.dacUnits
                epoch.deltaLevel = obj._epochPerDacSection.fEpochLevelInc[i] * self.dacUnits
                epoch.firstDuration = (obj._epochPerDacSection.lEpochInitDuration[i] / self.samplingRate).rescale(pq.ms)
                epoch.deltaDuration = (obj._epochPerDacSection.lEpochDurationInc[i] / self.samplingRate).rescale(pq.ms)
                epoch.pulsePeriod = (obj._epochPerDacSection.lEpochPulsePeriod[i] / self.samplingRate).rescale(pq.ms)
                epoch.pulseWidth = (obj._epochPerDacSection.lEpochPulseWidth[i] / self.samplingRate).rescale(pq.ms)
                epoch.mainDigitalPattern = digPatterns[epoch.epochNumber]["main"]
                epoch.alternateDigitalPattern = digPatterns[epoch.epochNumber]["alternate"]

                epochs.append(epoch)
                
            self._epochs_ = epochs

        else:
            raise NotImplementedError(f"ABf version {abfVer} is not supported")
        
    def __eq__(self, other):
        """Tests for equality of scalar properties and epochs tables.
        Epochs tables are checked for equality sweep by sweep, in all channels.
        
        WARNING: This includes any digital output patterns definded.
        
        If this is not intended, then use self.is_identical_except_digital(other)
        """
        if not isinstance(other, self.__class__):
            return False
        
        properties = inspect.getmembers_static(self, lambda x: isinstance(x, property))
        
        # check equality of properties (descriptors); this includes nSweeps and nADCChannels
        ret = all(np.all(getattr(self, p[0]) == getattr(other, p[0])) for p in properties)

        # if checked out then verify all epochs Tables are sweep by sweep 
        # identical in all DAC channels, including digital output patterns!
        if ret:
            ret = all(np.all(self.epochsTable(s) == other.epochsTable(s)) for s in range(self.protocol.nSweeps))
                    
        return ret
        
    def is_identical_except_digital(self, other):
        if not isinstance(other, self.__class__):
            return False
        
        properties = inspect.getmembers_static(self, lambda x: isinstance(x, property))
        
        # check equality of properties (descriptors); this includes nSweeps and nADCChannels
        ret = all(np.all(getattr(self, p[0]) == getattr(other, p[0])) for p in properties)
        
        if ret:
            ret = all(np.all(self.epochsTable(s, includeDigitalPattern=False) == other.epochsTable(s, includeDigitalPattern=False)) for s in range(self.protocol.nSweeps))
                    
        return ret
    
    def has_identical_epochs_table(self, other:ABFOutputConfiguration, 
                                   sweep:int = 0, includeDigitalPattern:bool=True):
        
        if not isinstance(other, ABFOutputConfiguration):
            return False
        
        return np.all(self.epochsTable(sweep, includeDigitalPattern = includeDigitalPattern) == 
                      other.epochsTable(sweep, includeDigitalPattern = includeDigitalPattern))
        
    @property
    def protocol(self) -> ABFProtocol:
        return self._protocol_
        
#     @property
#     def digitalTrainActiveLogic(self) -> bool:
#         return self.protocol.digitalTrainActiveLogic
#     
#     @property
#     def digitalHolding(self) -> int:
#         return self.protocol.digitalHolding
#     
#     @property
#     def digitalUseLastEpochHolding(self) -> bool:
#         return self.protocol.digitalUseLastEpochHolding
            
    @property
    def returnToHold(self) -> bool: 
        """True if the command waveform return to last epoch's level.
        This is specific to the DAC output.
        """
        return self._interEpisodeLevel_
    
    @property
    def epochs(self) -> list:
        """List of ABFEpoch objects defined for this DAC channel"""
        return self._epochs_
    
    def triggerEvents(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int = 0, 
                      eventType:TriggerEventType = TriggerEventType.presynaptic,
                      label:typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
                      name:typing.Optional[str] = None) -> TriggerEvent:
        """Trigger events from Step and Pulse-type ABF Epochs.
        If the epoch has digital outputs, the time stamps for the trigger
        events will be set by the timings of the digital TTL signals during
        the epoch. Otherwise, the timings will be given by the epoch's
        command waveform timing (i.e. its start time)
        """
        if isinstance(epoch, (str, int)):
            epoch = self.getEpoch(epoch)
            
        if epoch.epochType not in (ABFEpochType.Step, ABFEpochType.Pulse):
            return list()
        
        times = [x.rescale(pq.s) for x in self.epochActualPulseTimes(epoch, sweep)]
        
        trig = TriggerEvent(times=times, units = pq.s, labels = label, name=name)
        
        # see BUG: 2023-10-03 17:57:30 in triggerevent.TriggerEvent.__new__ 
        if isinstance(label, str) and len(label.strip()):
            trig.labels = [f"{label}{k}" for k in range(trig.times.size)]
            
        return trig
    
    def epochsTable(self, sweep:int = 0, includeDigitalPattern:bool=True):
        """Generate a Pandas DataFrame with the epochs definition for this DAC channel.
        
        Regarding the command and digital outputs, this reflects the actual 
        DAC and DIG outputs for the specified sweep.
        
        The epoch table in Clmapex/Clampfit and pyabf are "generic" - one has to
        work out the actual outputs for a sweep by themselves. In contrast, the
        logic in this function should also supply the necessary data to
        reconstruct the DAC "command" ("analog") waveform and also the "digital"
        waveform more easily.
        
        """
        if includeDigitalPattern:
            rowIndex = ["Type", "First Level", "Delta Level",
                        "First Duration", "First Duration (Samples)",
                        "Delta Duration", "Delta Duration (Samples)",
                        "Actual Duration", "Actual Duration (Samples)",
                        "Digital Pattern #3-0", "Digital Pattern #7-4", 
                        "Train Rate", "Train Period", "Train Period (Samples)",
                        "Pulse Width", "Pulse Width (Samples)",
                        "Pulse Count"]
        else:
            rowIndex = ["Type", "First Level", "Delta Level",
                        "First Duration", "First Duration (Samples)",
                        "Delta Duration", "Delta Duration (Samples)",
                        "Actual Duration", "Actual Duration (Samples)",
                        "Train Rate", "Train Period", "Train Period (Samples)",
                        "Pulse Width", "Pulse Width (Samples)",
                        "Pulse Count"]
                
    
        epochData = dict()
        
        for i, epoch in enumerate(self.epochs):
            if includeDigitalPattern:
                epochDigPattern = self.epochDigitalPattern(epoch, sweep)
                epValues = [epoch.typeName, epoch.firstLevel, epoch.deltaLevel,
                            epoch.firstDuration, self.epochFirstDurationSamples(epoch),
                            epoch.deltaDuration, self.epochDeltaDurationSamples(epoch),
                            self.epochActualDuration(epoch, sweep),
                            self.epochActualDurationSamples(epoch, sweep),
                            "".join(map(str, epochDigPattern[0])), 
                            "".join(map(str, epochDigPattern[1])),
                            epoch.pulseFrequency,
                            epoch.pulsePeriod, self.epochPulsePeriodSamples(epoch),
                            epoch.pulseWidth, self.epochPulseWidthSamples(epoch),
                            self.epochPulseCount(epoch, sweep)]
            else:
                epValues = [epoch.typeName, epoch.firstLevel, epoch.deltaLevel,
                            epoch.firstDuration, self.epochFirstDurationSamples(epoch),
                            epoch.deltaDuration, self.epochDeltaDurationSamples(epoch),
                            self.epochActualDuration(epoch, sweep),
                            self.epochActualDurationSamples(epoch, sweep),
                            epoch.pulseFrequency,
                            epoch.pulsePeriod, self.epochPulsePeriodSamples(epoch),
                            epoch.pulseWidth, self.epochPulseWidthSamples(epoch),
                            self.epochPulseCount(epoch, sweep)]
                    
            
            epochData[epoch.epochLetter] = epValues
            
        return pd.DataFrame(epochData, index = rowIndex)
        
    def getEpoch(self, e:typing.Union[str, int]):
        if isinstance(e, str):
            e = epochNumberFromLetter(e)
            
        if e < 0 or e >= len(self.epochs):
            return
        
        return self.epochs[e]
    
    def epochRelativeStartTime(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int = 0) -> pq.Quantity:
        """Starting time of the epoch, relative to sweep start.
        WARNING: Does NOT take into account the holding time (1/64 of sweep samples),
        therefore the response to the epoch's waveform, as recorded in the ADC
        signal, will appear delayed relative to the epoch's start by the holding time.
        
        Depending what you need, you may want to use self.epochActualRelativeStartTime
        
        """
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        # NOTE: 2023-09-22 15:39:13
        # below, the sweep index is REQUIRED to calculate the actual epoch duration
        # 
        units = epoch.firstDuration.units
        return np.sum([self.epochActualDuration(e_, sweep).rescale(units) for e_ in self.epochs[:epoch.epochNumber]]) * units
    
    def epochActualRelativeStartTime(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int = 0) -> pq.Quantity:
        """Starting time of the epoch, relative to sweep start.
        Takes into account the holding time (1/64 sweep samples, in Clampex),
        resulting in timings that match the times in the recorded neo.AnalogSignals.
        
        Use this function to construct neo.Epoch or neo.Events!
        
        """
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        units = epoch.firstDuration.units
        return np.sum([self.epochActualDuration(e_, sweep).rescale(units) for e_ in self.epochs[:epoch.epochNumber]]) * units + self.holdingTime
        
    def epochRelativeStartSamples(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int=0) -> int:
        """Number of samples from the start of the sweep to the start of epoch.
        WARNING: Like self.epochRelativeStartTime, does NOT take into account 
        the holding time; you may want to use self.epochActualRelativeStartsSamples
        
        
        """
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        return np.sum([self.epochActualDurationSamples(e_, sweep) for e_ in self.epochs[:epoch.epochNumber]])
    
    def epochActualRelativeStartSamples(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int=0) -> int:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        return np.sum([self.epochActualDurationSamples(e_, sweep) for e_ in self.epochs[:epoch.epochNumber]]) + self.holdingSampleCount
        
    def epochStartTime(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int = 0) -> pq.Quantity:
        """Starting time of the epoch, relative to the start of recording.
        WARNING: Does NOT take into account the holding time (1/64 of sweep samples),
        therefore the respoonse to the epoch's waveform, as recorded in the ADC 
        signal, will appear delayed relative to the epoch's start by the holding time.
        
        Depending what you need, you may want to use self.epochActualStartTime
        """
        # units = epoch.firstDuration.units
        return self.epochRelativeStartTime(epoch, sweep) + self.protocol.sweepInterval * sweep
    
    def epochActualStartTime(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int = 0) -> pq.Quantity:
        """Starting time of the epoch, relative to the start of recording.
        Takes into account the sweep holding time.
        """
        return self.epochActualRelativeStartTime(epoch, sweep) + self.protocol.sweepInterval * sweep
        
    def epochStartSamples(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int=0) -> int:
        """Number of samples from start fo recording to the epoch.
        WARNING: Like self.epochStartSamples, does NOT take into account 
        the holding time; you may want to use self.epochActualStartSamples.
        
        """
        return self.epochRelativeStartSamples(epoch, sweep) + self.protocol.sweepSampleCount * sweep
    
    def epochActualStartSamples(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int=0) -> int:
        """Number of samples from start fo recording to the epoch.
        Takes into account the sweep holding time.
        """
        return self.epochActualRelativeStartSamples(epoch, sweep) + self.protocol.sweepSampleCount * sweep
    
    def epochActualDuration(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int=0) -> pq.Quantity:
        """Actual epoch duration (in ms) for the given sweep.
        Takes into account first duration and delta duration"""
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        return epoch.firstDuration + sweep * epoch.deltaDuration
        
    def epochActualDurationSamples(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int=0) -> int:
        """Actual epoch duration (in samples) for the given sweep.
        Takes into account first duration and delta duration"""
        return scq.nSamples(self.epochActualDuration(epoch, sweep), self.samplingRate)
    
    def epochFirstDurationSamples(self, epoch:typing.Union[ABFEpoch, str, int]) -> int:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        return scq.nSamples(epoch.firstDuration, self.samplingRate)
        
    def epochDeltaDurationSamples(self, epoch:typing.Union[ABFEpoch, str, int]) -> int:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        return scq.nSamples(epoch.deltaDuration, self.samplingRate)
    
    def epochPulseWidthSamples(self, epoch:typing.Union[ABFEpoch, str, int]) -> int:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        return scq.nSamples(epoch.pulseWidth, self.samplingRate)
    
    def epochPulsePeriodSamples(self, epoch:typing.Union[ABFEpoch, str, int]) -> int:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        return scq.nSamples(epoch.pulsePeriod, self.samplingRate)
    
    def epochPulseCount(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int = 0) -> int:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        if float(epoch.pulsePeriod) == 0.:
            return 0
        
        return int(self.epochActualDuration(epoch,sweep)/epoch.pulsePeriod)

    def epochActualPulseTimes(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int = 0) -> list:
        """Start times for the pulses defined in the epoch.
        An ABF epoch may define pulses regardless of whether it associates a
        digital output patter or not. 
    
        In the former case, the pulse timings refer to the TTL timings sent out 
        on the digital channel(s). If a digital channel has a pulse, then only
        the first timing should be used (as this is a TTL "step"); otherise,
        the timings should reflect the timings of the TTL pulses in the digital 
        train.
        
        In the latter case (i.e. no digital output associated) then, depending on
        the epoch type, there will be one pulse (step epoch), or several (pulse
        epoch).
        """
        pc = self.epochPulseCount(epoch, sweep)
        
        if pc == 0:
            return list()

        t0 = self.epochActualStartTime(epoch, sweep)

        return [t0 + p * epoch.pulsePeriod for p in range(pc)]
    
    def epochPulseTimes(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int = 0) -> list:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        pc = self.epochPulseCount(epoch, sweep)
        if pc == 0:
            return list()
        
        t0 = self.epochStartTime(epoch, sweep)

        return [t0 + p * epoch.pulsePeriod for p in range(pc)]

    def epochAnalogWaveform(self, epoch:typing.Union[ABFEpoch, str, int], previousLevel:pq.Quantity, 
                      sweep:int = 0, lastLevelOnly:bool=False) -> pq.Quantity:
        """Realizes the analog waveform associated with a single epoch.
        An 'epoch' is defined as a specific time interval in a sweep, during 
        which the DAC outputs a command signal waveform givemn the epoch's type
        (step, ramp, pulse, etc). This information is configured using the 
        Channel tab inside the Waveform tab of the Clampex Protocol Editor.
        Complex DAC output commands can be generated by defining and concatenating
        several epochs (subject to the constraints of the Clampex software version)
        """
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
        epochSamplesCount = scq.nSamples(actualDuration, self.samplingRate)
        actualLevel = epoch.firstLevel + sweep * epoch.deltaLevel
        
        # print(f"self.__class__.__name__}.epochAnalogWaveform epoch {epoch.epochNumber} ({epoch.epochLetter}) type {epoch.epochType} sample count {epochSamplesCount}")
        
        if epoch.epochType == ABFEpochType.Step:
            wave = actualLevel if lastLevelOnly else np.full([epochSamplesCount, 1], float(actualLevel)) * self.dacUnits
        
        elif epoch.epochType == ABFEpochType.Ramp:
            wave = actualLevel if lastLevelOnly else np.linspace(previousLevel, actualLevel, epochSamplesCount)[:,np.newaxis]
            
        elif epoch.epochType == ABFEpochType.Pulse:
            pulsePeriod = self.epochPulsePeriodSamples(epoch)
            pulseSamples = self.epochPulseWidthSamples(epoch)
            pulseCount = self.epochPulseCount(epoch)
            
            if lastLevelOnly:
                wave = actualLevel
            else:
                wave = np.full([epochSamplesCount, 1], float(previousLevel)) * self.dacUnits
                
                for pulse in range(pulseCount):
                    p1 = int(pulsePeriod * pulse)
                    p2 = int(p1 + pulseSamples)
                    wave[p1:p2] = actualLevel
                        
        elif epoch.epochType == ABFEpochType.Triangular:
            pulsePeriod = self.epochPulsePeriodSamples(epoch)
            pulseSamples = self.epochPulseWidthSamples(epoch)
            pulseCount = self.epochPulseCount(epoch)
            
            if lastLevelOnly:
                wave = actualLevel
            else:
                wave = np.full([epochSamplesCount, 1], float(previousLevel)) * self.dacUnits
                            
                for pulse in range(pulseCount):
                    p1 = int(pulsePeriod * pulse)
                    p2 = int(p1 + pulseSamples)
                    p3 = int(p1 + pulsePeriod)
                    
                    wave[p1:p2] = np.linspace(previousLevel, actualLevel, pulseSamples)[:,np.newaxis]
                    wave[p2:p3] = np.linspace(actualLevel, previousLevel, int(pulsePeriod - pulseSamples))[:,np.newaxis]
            
        elif epoch.epochType == ABFEpochType.Cosine:
            if lastLevelOnly:
                wave = actualLevel
            else:
                pulseCount = self.epochPulseCount(epoch)
                levelDelta = float(actualLevel) - float(previousLevel)
                values = np.linspace(0, 2*pulseCount*np.pi, epochSamplesCount) + np.pi
                cosines = (np.cos(values) * levelDelta / 2 + levelDelta/2 ) * self.dacUnits + previousLevel
                wave = cosines[:, np.newaxis]
            
        elif epoch.epochType == ABFEpochType.Biphasic:
            pulsePeriod = self.epochPulsePeriodSamples(epoch)
            pulseSamples = self.epochPulseWidthSamples(epoch)
            pulseCount = self.epochPulseCount(epoch)
            levelDelta = actualLevel - previousLevel
            
            if lastLevelOnly:
                wave = actualLevel
            else:
                wave = np.full([epochSamplesCount, 1], float(previousLevel)) * self.dacUnits
                # waveform[ndx[0]:ndx[1],0] = previousLevel
                
                for pulse in range(pulseCount):
                    p1 = int(pulsePeriod * pulse)
                    p3 = int(p1 + pulseSamples)
                    p2 = int((p1+p3)/2)
                    wave[p1:p2] = previousLevel + levelDelta
                    wave[p2:p3] = previousLevel - levelDelta
                    # waveform[p1:p2,0] = previousLevel + levelDelta
                    # waveform[p2:p3,0] = previousLevel - levelDelta
            
        else:
            wave = np.full([epochSamplesCount, 1], float(previousLevel)) * self.dacUnits
            
        return wave
    
    def epochDigitalWaveform(self, epoch:typing.Union[ABFEpoch, str, int], trainOFF, trainON, digOFF, digON,
                             sweep:int = 0, digChannel:int = 0, lastLevelOnly:bool=False) -> pq.Quantity:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
        epochSamplesCount = scq.nSamples(actualDuration, self.samplingRate)
        pulsePeriod = self.epochPulsePeriodSamples(epoch)
        pulseSamples = self.epochPulseWidthSamples(epoch)
        pulseCount = self.epochPulseCount(epoch)
        
        digPattern = self.epochDigitalPattern(epoch, sweep)
        # # either this:
        # digPattern = list(reversed(digPattern[1] + digPattern[0]))
        # digChannelValue = digPattern[digChannel]
        # # or this:
        digPattern = digPattern[1] + digPattern[0]
        digChannelValue = digPattern[-digChannel-1]
        
        wave = np.full([epochSamplesCount, 1], 0) * pq.V 

        if digChannelValue == 1: # single TTL pulse (step-like)
            if lastLevelOnly:
                wave = digON * V
            else:
                wave[:] = digON * pq.V
            
        elif digChannelValue == "*": # pulse train!
            if lastLevelOnly:
                wave = trainOFF * pq.V
            else:
                wave[:] = trainOFF * pq.V
                for pulse in range(pulseCount):
                    p1 = int(pulsePeriod * pulse)
                    p2 = int(p1 + pulseSamples)
                    wave[p1:p2] = trainON * pq.V
                    
        else:
            if lastLevelOnly:
                wave = digOFF * pq.V
                
        return wave
    
    def getPreviousSweepLastEpochLevel(self, sweep:int) -> pq.Quantity:
        # FIXME: 2023-09-18 23:34:27
        # this can become very expensive for many sweeps!
        if len(self.epochs) == 0 or sweep == 0:
            return self.dacHoldingLevel
        
        if self.returnToHold:
            prevLevel = self.dacHoldingLevel
            for s in range(sweep):
                for e in self.epochs:
                    prevLevel = self.epochAnalogWaveform(e, prevLevel, s, True)
                    
            return prevLevel
        
        return self.dacHoldingLevel
    
    def getDigitalLogicLevels(self, digChannel:int=0) -> tuple:
        if self.digitalTrainActiveLogic:
            trainOFF = 0
            trainON = 5
        else:
            trainOFF = 5
            trainON = 0
            
        if self.protocol.digitalHoldingValue(digChannel):
            digOFF = 5
            digON = 0
        else:
            digOFF = 0
            digON = 5
            
        return digOFF, digON, trainOFF, trainON
        
            
    def getPreviousSweelLastDigitalLevel(self, sweep:int, digChannel:int,
                                         trainOFF, trainON, digOFF, digON) -> pq.Quantity:
        if len(self.epochs) == 0 or sweep == 0:
            return digOFF * pq.V
        
        if self.digitalUseLastEpochHolding:
            prevLevel = digOFF * pq.V
            for s in range(sweep):
                for e in self.epochs:
                    prevLevel = self.epochDigitalWaveform(e, trainOFF, trainON, digOFF, digON, sweep, digChannel,
                                                          True)
                    
                return prevLevel
            
        return digOFF * pq.V
        
    
    def epochDigitalPattern(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int=0) ->tuple:
        """Returns the digital pattern that WOULD be output by the epoch.
        This depends, simultaneously, on the following conditions:
        1) the DAC channel has digital outputs enabled
        2) alternative digital outputs are enabled in the protocol
        3) the DAC channel takes part in alternate digital outputs or not (this
            depends on the channel index, with DAC 0 and 1 being the only ones
            used for alternate digital output during even- and odd-numbered sweeps)
        """
        isAltDig = self.alternateDigitalOutputStateEnabled and sweep % 2 > 0
        
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        elif not isinstance(epoch, ABFEpoch):
            raise TypeError(f"Expecting an ABFEpoch, an int or a str (epoch 'name' e.g. 'A', 'B' or 'AB', etc); instead got {type(epoch).__name__}")
        
        if self.alternateDigitalOutputStateEnabled and self.dacChannel < 2:
            # NOTE: 2023-09-18 13:22:56
            # When alternative digital outputs are used in an experiment,
            # ONLY the first two DACs (0 and 1) take part in the alternative
            # arangement of digital outputs, as follows:
            #
            # • The DAC where digital outputs are enabled sends TTLs during
            #   even-numbered sweeps (0,2,4,…),
            #
            # • The "other" DAC (where digital outputs are NOT enabled) sends 
            #   TTLs during odd-numbered sweeps (1,3,5,…)
            #
            # The alternate pattern is DEFINED in the protocol editor 
            # in the "other" DAC channel (DAC1 if digital output is enabled
            # on DAC0, or DAC0 if digital output is enabled on DAC1); this 
            # pattern is stored internally in the ABF file as the "alternate"
            # digital pattern (at a different address)
            #
            # NOTE: neither physical DAC channel actually sends out any TTL signals
            # The association of a digital pattern with the GUI for the configuration
            # of a particular DAC channel seems an arbitrary decision in Clampex,
            # likely justified by the fact that the digital output (TTL) is
            # associated logically with the command waveform (if any) sent out 
            # by a physical DAC channel during a particular epoch; another
            # possible reason is to avoid the Clampex GUI becoming more complex...
            # 
            #
            if self.digitalOutputEnabled:
                # for the DAC channel where digital output is enabled we write
                # ONLY the main digital pattern of the epoch, and ONLY if 
                # the sweep has an even number
                #
                if isAltDig:
                    # this DAC has dig output enabled, hence during
                    # an experiment it will output NOTHING if either 
                    # alternateDigitalPattern is disabled OR sweep number 
                    # is even
                    #
                    dig_3_0 = epoch.digitalPattern(True)[0]
                    dig_7_4 = epoch.digitalPattern(True)[1]
                    # dig_3_0 = dig_7_4 = [0,0,0,0]
                else:
                    # this DAC has dig output enabled, hence during
                    # an experiment it will output the main digital pattern
                    # if either alternateDigitalPattern is disabled, OR
                    # sweep number is even
                    #
                    dig_3_0 = epoch.digitalPattern()[0]
                    dig_7_4 = epoch.digitalPattern()[1]
            else:
                # For a DAC where dig output is DISabled, the DAC is simply
                # a placeholder for the alternate digital output of the epoch, 
                # (and these TTLs will be sent out) ONLY if alternateDigitalPattern
                # is enabled AND sweep number is odd
                #
                # NOTE: 2023-10-04 09:07:42 - show what is actually sent out
                # i.e., if digital output is DISABLED then show zeroes even if
                # in the Clampex protocol editor we have a pattern entered here.
                #
                # This is because, when digital output is disabled for this DAC
                # AND alternative digital output is enabled in the protocol, the
                # digital pattern entered on this waveform tab in Clampex
                # protocol editor is used as the alternative digital output for
                # the DAC where digital output IS enabled.
                #
                # I guess this is was a GUI design decision taken the by Clampex
                # authors n order to avoid adding another field to the GUI form.
                #
                # NOTE: 2023-10-04 09:12:29
                # Also, the DAC where digital output patterns are enabled may NOT
                # be the same as the DAC one is recording from! 
                #
                # So if you're using, say DAC1, to send commands to your cell 
                # (where DAC1 should be paired with the ADCs coming from the second
                # amplifier channel, in a MultiClamp device) it is perfectly OK to
                # enable digital outputs in the DAC0 waveform tab: Clampex will
                # still issue TTLs during the sweep, even if DAC0 does not send 
                # any command waveforms.
                #
                #
                # On the other hand, if DAC0 has waveforms disabled (in this example,
                # DAC0 is NOT used in the experiment) AND alternate digital outputs
                # is disabled in the protocol, then NO digital outputs are "linked"
                # to this DAC0.
                #
                # That somewhat confuses things, because DIG channels and DAC
                # channels are physically independent! The only logical "link"
                # between them is the timings of the epochs.
                # 
                # Also, NOTE that in Clampex only one DAC can have digital outputs
                # enabled.
                #
                
                # if self.analogWaveformEnabled
                dig_3_0 = dig_7_4 = [0,0,0,0]
                # if isAltDig:
                #     dig_3_0 = epoch.digitalPattern(True)[0]
                #     dig_7_4 = epoch.digitalPattern(True)[1]
                # else:
                #     dig_3_0 = dig_7_4 = [0,0,0,0]
                    
        else:
            if self.digitalOutputEnabled:
                # if alternateDigitalPattern is not enabled, or the DAC channel
                # is one of the channels NOT involved in alternate output
                # (2, …) the channel will always output the main digital 
                # pattern here
                dig_3_0 = epoch.digitalPattern()[0]
                dig_7_4 = epoch.digitalPattern()[1]
            else:
                dig_3_0 = dig_7_4 = [0,0,0,0]
                
        return dig_3_0, dig_7_4
                
    @property
    def analogWaveformEnabled(self) -> bool:
        return self._waveformEnabled_
    
    @property
    def analogWaveformSource(self) -> ABFDACWaveformSource:
        return self._waveformSource_
    
    # @property
    # def isactiveDACChannel(self) -> bool:
    #     return self._isActiveDACChannel_
    
    @property
    def digitalOutputEnabled(self) -> bool:
        return self._digOutEnabled_
    
    def channelIndex(self, physical:bool=False):
        return self.physicalIndex if physical else self.logicalIndex
    
    @property
    def logicalIndex(self) -> int:
        """The index of the DAC channel configured in this object.
        Read-only. 
        An instance of ABFOutputConfiguration is 'linked' to the same
        DAC channel throughtout its lifetime; therefore this property can only 
        be set at construction time.
        
        """
        return self._dacChannel_
    
    @property
    def physicalIndex(self):
        return self._physicalChannelIndex_
    
    @property
    def number(self) -> int:
        """Alias to self.logicalIndex"""
        return self.logicalIndex
    
    @property
    def physical(self):
        return self.physicalIndex

    @property
    def dacName(self) -> str:
        """Read-only; can only be set up at initialization (construction)
        and stays the same throughout the lifetime of the object"""
        return self._dacName_
    
    @property
    def name(self) -> str:
        """Alias to self.dacName"""
        return self.dacName
    
    @property
    def dacUnits(self) -> pq.Quantity:
        """Read-only; can only be set up at initialization (construction)
        and stays the same throughout the lifetime of the object"""
        return self._dacUnits_
    
    @property
    def units(self) -> pq.Quantity:
        """Alias to self.dacUnits"""
        return self.dacUnits
    
    @property
    def sweepSampleCount(self) -> int:
        """Read-only; can only be set up at initialization (construction)
        and stays the same throughout the lifetime of the object"""
        return self.protocol.sweepSampleCount
    
    @property
    def holdingSampleCount(self) -> int:
        return self.protocol.holdingSampleCount
    
    @property
    def digitalOutputsCount(self) -> int:
        """Read-only; can only be set up at initialization (construction)
        and stays the same throughout the lifetime of the object"""
        return self.protocol.nDigitalOutputs
    
    @property
    def samplingRate(self) -> pq.Quantity:
        return self.protocol.samplingRate
    
    @property
    def dacHoldingLevel(self) -> pq.Quantity:
        """DAC-specific"""
        return self._dacHoldingLevel_
    
    @property
    def alternateDigitalOutputStateEnabled(self) -> bool:
        return self.protocol.alternateDigitalOutputStateEnabled
    
    @property
    def alternateDACOutputStateEnabled(self) -> bool:
        return self.protocol.alternateDACOutputStateEnabled
        
    @property
    def holdingTime(self) -> pq.Quantity:
        """Read-only (determined by Clampex).
        This corresponds 1/64 samples of total samples in a sweep.
        This is protocol-specific.
    """
        return self.protocol.holdingTime
    
    def analogWaveform(self, sweep:int=0) -> neo.AnalogSignal:
        return self.dacCommandWaveform(sweep)
    
    def commandWaveform(self, sweep:int=0) -> neo.AnalogSignal:
        return self.dacCommandWaveform(sweep)
    
    def dacCommandWaveform(self, sweep:int=0) -> neo.AnalogSignal: 
        """Generates an AnalogSignal representation of the command waveform.
        
        When nAlternateDACOutputState is True, this waveform IS specific to the 
        sweep number.
     
        NOTE: DAC command waveforms and digital outputs are enabled only in 
        Episodic Stimulation type of experiments.
     
        """
        if self.analogWaveformSource == ABFDACWaveformSource.none or (not self.analogWaveformEnabled and not self.alternateDACOutputStateEnabled):
            # return empty signal (containing np.nan)
            return neo.AnalogSignal(np.full((self.protocol.sweepSampleCount, 1), np.nan),
                                    units = self.dacUnits, t_start = 0*pq.s,
                                    sampling_rate = self.samplingRate,
                                    name = self.dacName)
        
        # holdingLevel = float(self.dacHoldingLevel.magnitude)
        
        if self.analogWaveformSource == ABFDACWaveformSource.epochs:
            
            if len(self.epochs) == 0:
                return neo.AnalogSignal(np.full((self.protocol.sweepSampleCount, 1), float(holdingLevel)),
                                        units = self.dacUnits, t_start = 0*pq.s,
                                        sampling_rate = self.samplingRate,
                                        name = self.dacName)
            
            if sweep > 0 and self.returnToHold:
                # is the waveform of a subsequent sweep is sought, and returnToHold
                # is True, then we need the level of the last epoch in the "previous"
                # sweep
                # previousLevel = self.epochs[-1].firstLevel + self.epochs[-1].deltaLevel * (sweep-1)
                previousLevel = self.getPreviousSweepLastEpochLevel(sweep)
            else:
                previousLevel = self.dacHoldingLevel
            
            waveform = neo.AnalogSignal(np.full((self.protocol.sweepSampleCount, 1), float(previousLevel)),
                                        units = self.dacUnits, t_start = 0*pq.s,
                                        sampling_rate = self.samplingRate,
                                        name = self.dacName)
            
            t0 = t1 = self.holdingTime.rescale(pq.s)
            
            for epoch in self.epochs:
                actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
                epochSamplesCount = scq.nSamples(actualDuration, self.samplingRate)
                actualLevel = epoch.firstLevel + sweep * epoch.deltaLevel

                t1 = t0 + actualDuration
                tt = np.array([t0,t1])*pq.s
                ndx = waveform.time_index(tt)
                
                wave = self.epochAnalogWaveform(epoch, previousLevel, sweep)
                
                waveform[ndx[0]:ndx[1],0] = wave
                
                previousLevel = actualLevel
                t0 = t1
                
            if self.returnToHold:
                waveform[ndx[1]:, 0] = previousLevel
                
        
        else:
            # TODO: 2023-09-18 15:44:03
            # use waveform (stimulus) file
            # for that, I need to modify axonrawio (or provide alternative) so 
            # that the strings section is properly read and inserted into the 
            # metadata / resulting neo.Block's annotations.
            #
            # a possible solution is to read the ABF file post-hoc using pyabf
            # (called from a pictio function) and populate annotations there, 
            # thus avoiding changes to neo stock code
            #
            # NOTE: 2023-09-21 00:44:48
            # the above logic is now implemented in pictio
            # TODO: 2023-09-21 00:45:03
            # use that informaiton here (search under annotations["sections"]["StringsSection"]["IndexedStrings"])
            warnings.warning(f"Command waveforms from external stimulus files are not yet supported", RuntimeWarning)
            return neo.AnalogSignal(np.full((self.protocol.sweepSampleCount, 1), np.nan),
                                    units = self.dacUnits, t_start = 0*pq.s,
                                    sampling_rate = self.samplingRate,
                                    name = self.dacName)
        
            
                
        return waveform
    
    def digitalWaveform(self, sweep:int=0, digChannel:int = 0) -> neo.AnalogSignal:
        """Realizes the digital output waveform (pulses, trains) emitted when
        this DAC channel is active"""
        # NOTE: 2023-09-20 22:22:41
        # the digital output is ALWWAYS in V
        # "high logic" means 5V on a background of 0 V
        # "low logic" means 0V on a background of 5V
        assert digChannel in range(self.digitalOutputsCount), f"Invalid digital output channel {digChannel} for {self.digitalOutputsCount} channels "

        digOFF, digON, trainOFF, trainON = self.getDigitalLogicLevels(digChannel)
        
        waveform = neo.AnalogSignal(np.full((self.sweepSampleCount, 1), digOFF),
                                    units = pq.V, t_start = 0*pq.s,
                                    sampling_rate = self.samplingRate,
                                    name = f"DIG{digChannel}")

        t0 = t1 = self.holdingTime.rescale(pq.s)
        
        lastEpochNdx = 0
        
        lastlevel = digOFF * pq.V
        
        for epoch in self.epochs:
            # print(f"{self.__class__.__name__}.digitalWaveform sweep {sweep}, digChannel {digChannel} in epoch {epoch.epochLetter}: digChannelValue {digChannelValue}")
            actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
            t1 = t0 + actualDuration
            tt = np.array([t0,t1])*pq.s
            ndx = waveform.time_index(tt)
            
            wave = self.epochDigitalWaveform(epoch, trainOFF, trainON, digOFF, digON, 
                                             sweep, digChannel)
            
            waveform[ndx[0]:ndx[1], 0] = wave
            
            t0 = t1
            
            lastEpochNdx = ndx[1]
            lastLevel = wave[-1]
            
        if self.digitalUseLastEpochHolding:
            waveform[lastEpochNdx:, 0] = lastLevel
        else:
            waveform[lastEpochNdx:, 0] = digOFF * pq.V
            
        return waveform
        
        
        
def epochNumberFromLetter(x:str) -> int:
    """The inverse function of epochLetter()"""
    from core import strutils
    return strutils.lettersToOrdinal(x)

def epochLetter(epochNumber:int):
    from core import strutils
    return strutils.ordinalToLetters(epochNumber)
    # from pyabf.waveform.Epoch
#     if epochNumber < 0:
#         return "?"
#     letter = ""
#     while epochNumber >= 0:
#         letter += chr(epochNumber % 26 + 65)
#         epochNumber -= 26
#         
#     return letter

def __wrap_to_quantity__(x:typing.Union[list, tuple], convert:bool=True):
    return (x[0], unitStrAsQuantity(x[1])) if convert else x

def unitStrAsQuantity(x:str, convert:bool=True):
    return scq.unit_quantity_from_name_or_symbol(x) if convert else x

def sourcedFromABF(x:neo.Block) -> bool:
    ver = getABFversion(x) # raises AssertionError if x is not sourced from ABF
    return True

def getABF(obj:typing.Union[str, neo.Block]):
    """
    Returns a pyabf.ABF object from an ABF file.
    
    Parameters:
    ----------
    obj: str (ABF file name) or a neo.core.baseneo.BaseNeo object containing an
        attribute named "file_origin" pointing to an ABF file on disk where its
        data is stored (in Scipyen, the contents of ABF files are normally loaded
        as neo.Block objects).
    """
    import os
    from iolib import pictio as pio
    # if not hasPyABF:
    #     warning.warn("getABF requires pyabf package")
    #     return

    if isinstance(obj, str):
        filename = obj
    else:
        filename = getattr(obj, "file_origin", None)
        
    if not os.path.exists(filename):
        return
    
    loader = pio.getLoaderForFile(filename)
    
    if loader == pio.loadAxonFile:
        try:
            if filename.lower().endswith(".abf"):
                return pyabf.ABF(filename)
            elif filename.lower().endswith(".atf"):
                return pyabf.ATF(filename)
            else:
                raise RuntimeError("pyabf can only handle ABF and ATF files")
        except:
            pass
        
    else:
        warning.warn(f"{filename} is not an Axon file")
        
def getABFsection(abf:pyabf.ABF, sectionType:typing.Optional[str] = None) -> dict:
    """Return a specific section from a pyabf.ABF object, as a dict.
    The section's type is specified as a string (case-insensitive) which can be
    one of:
    'adc'
    'dac'
    'data'
    'epoch'
    'epochperdac'
    'header'
    'protocol'
    'strings'
    'syncharray'
    'tag'
    'userlist'
    
    When sectionType is None (default) the function returns a dict with the values
    of the abf object data members 
    
    
"""
    import io
    reject_funcs = (inspect.ismemberdescriptor,
                    inspect.ismethod,
                    inspect.ismethoddescriptor,
                    inspect.ismethodwrapper,
                    inspect.ismodule,
                    inspect.isfunction,
                    inspect.isasyncgen,
                    inspect.isabstract,
                    inspect.isasyncgenfunction,
                    inspect.isawaitable        ,  
                    inspect.isbuiltin           , 
                    inspect.isclass              ,
                    inspect.iscode               ,
                    inspect.iscoroutine          ,
                    inspect.iscoroutinefunction  ,
                    inspect.isdatadescriptor     ,
                    inspect.isframe              ,
                    inspect.isfunction           ,
                    inspect.isgenerator          ,
                    inspect.isgeneratorfunction  ,
                    inspect.isgetsetdescriptor   ,
                    inspect.ismemberdescriptor   ,
                    inspect.ismethod             ,
                    inspect.ismethoddescriptor   ,
                    inspect.ismethodwrapper      ,
                    inspect.ismodule             ,
                    inspect.isroutine            ,
                    inspect.istraceback          
                    )
    
    if not isinstance(sectionType, str):
        return datatypes.inspect_members(abf, lambda x: not any(f(x) for f in reject_funcs) and not isinstance(x, property) and not isinstance(x, io.BufferedReader))
        
    sType = sectionType.lower()
    if sType == "protocol":
        s = abf._protocolSection
    elif sType == "adc":
        s = abf._adcSection
    elif sType == "dac":
        s = abf._dacSection
    elif sType == "data":
        s = abf._dataSection
    elif sType == "epochperdac":
        s = abf._epochPerDacSection
    elif sType == "epoch":
        s = abf._epochSection
    elif sType == "header":
        s = abf._headerV2 if abf.abfVersion["major"] == 2 else abf._headerV1
    elif sType == "strings":
        s = abf._stringsSection
    elif sType == "syncharray":
        s = abf._synchArraySection
    elif sType == "tag":
        s = abf._tagSection
    elif sType == "userlist":
        s = abf._userListSection
    else:
        raise ValueError(f"Unknown section type {sectionType}")

    return datatypes.inspect_members(s, lambda x: not any(f(x) for f in reject_funcs) and not isinstance(x, property) and not isinstance(x, io.BufferedReader))
    
def readInt16(fb):
    bytes = fb.read(2)
    values = struct.unpack("h", bytes) # ⇐ this is a tuple! first element is what we need
    # print(f"abfReader.readInt16 bytes = {bytes}, values = {values}")
    return values[0]
    
def valToBitList(value:int, bitCount:int = DIGITAL_OUTPUT_COUNT, 
                 reverse:bool = False, breakout:bool = True, as_bool:bool=False):
    # NOTE: 2023-06-24 23:18:15
    # I think DIGITAL_OUTPUT_COUNT should be abf._protocolSection.nDigitizerSynchDigitalOuts 
    # but I'm not sure...
    value = int(value)
    binString = bin(value)[2:].zfill(bitCount) # first two chars are always '0b'
    bits = list(binString)
    if as_bool:
        bits = [True if int(x) == 1 else False for x in bits]
    else:
        bits = [int(x) for x in bits]
    if breakout:
        reverse = False
    if reverse:
        bits.reverse()
    if breakout:
        return bits[4:], bits [0:4] # bank 3-0, bank 7-4
    return bits

def bitListToString(bits:list, star:bool=False):
    ret = ''.join([str(x) for x in bits])
    if star:
        ret = ret.replace('1', '*')
    return ret
        
@singledispatch
def getDIGPatterns(o, reverse_banks:bool=False, wrap:bool=False, 
                   pack_str:bool=False, epoch_num:typing.Optional[int]=None) -> dict:
    """Access the digital patterns of bit flags associated with the Epochs.

    Returns a mapping epoch_number:int ↦ nested mapping of key:str ↦ pair of 4-tuples of int or '*' elements

    Key                     ↦   Value:
    =======================================
    int (Epoch number)      ↦   mapping (dict) str ↦ list

    The nested dict maps:
    str ("main" or "alternate") ↦ list of int (0 or 1) or the character '*'
                                in the bit order 0-7 (DigiData 1550 series) or
                                0-3 (DigiData 1440 series) 

    The inner mapping keys can be one of the following:
    'main'      ↦ the main pattern
    'alternate' ↦ the alternate pattern

    Each pattern is a 4-tuple (for ABF1) or a pair of 4-tuples (for ABF2), 
    where a 4-tuple represents the bit value (0 or 1, or '*' for pulse train) 
    for the corresponding DIG channel index

    NOTE: Below, the number of DIG channels (and banks) depends on the ditigizer:

    DigiData 1440 series: DIG channels (3, 2, 1, 0) i.e. one bank of 4 bits
    
    DigiData 1550 series: DIG channels ((3, 2, 1, 0) , (7, 6, 5, 4)) i.e. two 
                        banks of 4 bits

    Parameters:
    ===========
    o: pyabf.ABF object, or neo.Block
        NOTE when 'o' is an ABF object, the original ABF file needs to be 
        accessible as indicated by the 'abfFilePath' attribute of the ABF object

    reverse_banks: bool, optional (default is False)
        When True, the order of the banks will be reversed: 

        (7,6,5,4) followed by (3,2,1,0)

    wrap: bool, optional (default is False)
        By default, the function returns the bits flags as to separate banks:
        (3,2,1,0) and (7,6,5,4)

        When True, the bit flags will be wrapped in a single 8-tuple, as:

        (7,6,5,4,3,2,1,0) when reverse_banks is True

        (0,1,2,3,4,5,6,7) when reverse_banks is False (default)

    pack_str: bool, optional (default is False)
        When True, the tuples willl contain string representations, e.g.:

        (0,0,0,0) becomes '0000'

        (0,1,0,'*') becomes '010*'  

        etc.

    epoch_num: int; optional, default is None
        By default the function returns the digital bit patterns for all the epochs

        When specified, this parameter causes the function to return the digital
        bit pattern for the specified epoch number.

    """
    raise NotImplementedError(f"This function does not support objects of {type(o).__name__} type")

@getDIGPatterns.register(neo.Block)
def _(obj:neo.Block, reverse_banks:bool=False, wrap:bool=False, 
      pack_str:bool=False, epoch_num:typing.Optional[int]=None) -> dict:
    
    # check of this neo.Block was read from an ABF file
    assert sourcedFromABF(obj), "Object does not appear to have been sourced from an ABF file"
    
    epochsDigitalPattern = dict()
    
    # reverses the banks => 7-4 then 3-0
    banks = [1,0] if reverse_banks else [0,1]
    
    nSynchDIGBits = obj.annotations["protocol"]["nDigitizerSynchDigitalOuts"]
    nAlternateDIGBits = obj.annotations["protocol"]["nDigitizerTotalDigitalOuts"] - nSynchDIGBits

    getSynchBitList = partial(valToBitList, bitCount = nSynchDIGBits,
                                as_bool=True)
    
    getAlternateBitList = partial(valToBitList, bitCount = nAlternateDIGBits,
                                    as_bool = True)
    
    for epoch_info in obj.annotations["EpochInfo"]:
        epochNumber = epoch_info["nEpochNum"]
        if isinstance(epoch_num, int) and epoch_num != epochNumber:
            continue
        d = getSynchBitList(epoch_info["nDigitalValue"])
        s = getSynchBitList(epoch_info["nDigitalTrainValue"])
        da = getAlternateBitList(epoch_info["nAlternateDigitalValue"])
        sa = getAlternateBitList(epoch_info["nAlternateDigitalTrainValue"])
        
        digitalPattern = list()
        
        for k in banks: 
            pattern = tuple(1 if d[k][i] and not s[k][i] else '*' if s[k][i] and not d[k][i] else 0 for i in range(len(d[k])))
                
            if wrap:
                if not reverse_banks:
                    pattern = tuple(reversed(pattern))

                digitalPattern.extend(pattern)
                
                if pack_str:
                    digitalPattern = "".join(map(str, digitalPattern))
            else:
                digitalPattern.append("".join(map(str, pattern)) if pack_str else pattern)
                
        digitalPattern = tuple(digitalPattern)
                    
        alternateDigitalPattern = list()

        for k in banks:
            pattern = tuple(1 if da[k][i] and not sa[k][i] else '*' if sa[k][i] and not da[k][i] else 0 for i in range(len(da[k])))
            if wrap:
                if not reverse_banks:
                    pattern = tuple(reversed(pattern))
                alternateDigitalPattern.extend(pattern)
                if pack_str:
                    alternateDigitalPattern = "".join(map(str, alternateDigitalPattern))
            else:
                alternateDigitalPattern.append("".join(map(str, pattern)) if pack_str else pattern)
                
        alternateDigitalPattern = tuple(alternateDigitalPattern)
        
        epochsDigitalPattern[epochNumber] = {"main": digitalPattern, "alternate": alternateDigitalPattern}
                
    return epochsDigitalPattern #, epochNumbers, epochDigital, epochDigitalStarred, epochDigitalAlt, epochDigitalStarredAlt

@getDIGPatterns.register(pyabf.ABF)
def _(abf:pyabf.ABF, reverse_banks:bool=False, wrap:bool=False, 
      pack_str:bool=False, epoch_num:typing.Optional[int]=None) -> dict:
    """Creates a representation of the digital pattern associated with a DAC channel.

    Requires access to the original ABF file, because we are using our own
    algorithm to decode digital output trains.

    Returns a mapping (dict) with 

    Key                     ↦   Value:
    =======================================
    int (Epoch number)      ↦   mapping (dict) str ↦ list

    The nested dict maps:
    str ("main" or "alternate") ↦ list of int (0 or 1) or the character '*'
                                in the bit order 0-7 (DigiData 1550 series) or
                                0-3 (DigiData 1440 series) 

    """
    # NOTE: 2023-06-24 23:37:33
    # the _protocolSection has the following flags useful in this context:
    # nDigitalEnable: int (0 or 1) → whether D0-D8 are enabled
    # nAlternateDigitalOutputState: int (0 or 1) → whether the DAC channel 0
    #      and the others (see below) use an alternative DIG bit pattern
    # nDigitalDACChannel: int (0 ⋯ N) where N is _protocolSection.nDigitizerDACs - 1 
    #                   → on which DAC channel are the DIG outputs enabled
    #   This IS IMPORTANT because when the nAlternateDigitalOutputState is 1
    #   then the PRIMARY pattern applies to the actual DAC channel used for 
    #   digital output: when this is Channel 0 then the alternative pattern is 
    #   applied on the channels 1 and higher; when this is Channel 1 (or higher)
    #   then the alternative pattern is applied on Channel 0 !
    epochsDigitalPattern = dict()
    
    # reverses the banks => 7-4 then 3-0
    banks = [1,0] if reverse_banks else [0,1]
    
    with open(abf.abfFilePath, 'rb') as fb:
        epochSection = abf._epochSection
        nEpochs = epochSection._entryCount
        # epochNumbers = [None] * nEpochs
        # epochDigital = [None] * nEpochs
        # epochDigitalStarred = [None] * nEpochs
        
        # NOTE: When these are populated, then abf._protocolSection.nAlternateDigitalOutputState
        # SHOULD be 1 (but we don't check for this here)
        # epochDigitalAlt = [None] * nEpochs
        # epochDigitalStarredAlt = [None] * nEpochs
        
        nSynchDIGBits = abf._protocolSection.nDigitizerSynchDigitalOuts
        nAlternateDIGBits = abf._protocolSection.nDigitizerTotalDigitalOuts - nSynchDIGBits
        
        getSynchBitList = partial(valToBitList, bitCount = nSynchDIGBits,
                                  as_bool=True)
        
        getAlternateBitList = partial(valToBitList, bitCount = nAlternateDIGBits,
                                      as_bool = True)
        
        
        # TODO: 2023-09-07 10:18:14
        # use THIS in our own ABFEpoch class; might want to augment neo.io.rawio.axonrawio
        # OR write a new axon raw io class...
        for i in range(nEpochs):
            fb.seek(epochSection._byteStart + i * epochSection._entrySize)
            epochNumber = readInt16(fb)
            epochDig = readInt16(fb) # reads the step digital pattern (0s and 1s, for ditigal steps)
            epochDigS = readInt16(fb) # reads the starred digital pattern (for digital pulse trains)
            epochDig_alt = readInt16(fb) # reads the alternative step digital pattern
            epochDigS_alt = readInt16(fb) # reads the alternative digital pulse trains
            
            if isinstance(epoch_num, int) and epoch_num != epochNUumber:
                # skip if requesting for a specific epoch
                continue
            
            epochDict = dict()
            
            # each of these is a list of two lists (DIG bank 3-0 and DIG bank 7-4)
            d = getSynchBitList(epochDig)           # steps
            s = getSynchBitList(epochDigS)          # pulses (starred)
            da = getAlternateBitList(epochDig_alt)  # alternative steps
            sa = getAlternateBitList(epochDigS_alt) # alternative pulses
            
            
            digitalPattern = list()
            
            # for k in range(2): # two banks
            for k in banks: 
                pattern = tuple(1 if d[k][i] and not s[k][i] else '*' if s[k][i] and not d[k][i] else 0 for i in range(len(d[k])))
                    
                if wrap:
                    if not reverse_banks:
                        pattern = tuple(reversed(pattern))

                    digitalPattern.extend(pattern)

                    if pack_str:
                        digitalPattern = "".join(map(str, digitalPattern))
                else:
                    digitalPattern.append("".join(map(str, pattern)) if pack_str else pattern)
                    
            digitalPattern = tuple(digitalPattern)
                    
            alternateDigitalPattern = list()

            for k in banks:
                pattern = tuple(1 if da[k][i] and not sa[k][i] else '*' if sa[k][i] and not da[k][i] else 0 for i in range(len(da[k])))
                    
                if wrap:
                    if not reverse_banks:
                        pattern = tuple(reversed(pattern))

                    alternateDigitalPattern.extend(pattern)

                    if pack_str:
                        alternateDigitalPattern = "".join(map(str, alternateDigitalPattern))
                else:
                    alternateDigitalPattern.append("".join(map(str, pattern)) if pack_str else pattern)
                    
            alternateDigitalPattern = tuple(alternateDigitalPattern)
                
            epochsDigitalPattern[epochNumber] = {"main": digitalPattern, "alternate": alternateDigitalPattern}
                    
        return epochsDigitalPattern #, epochNumbers, epochDigital, epochDigitalStarred, epochDigitalAlt, epochDigitalStarredAlt
        
@singledispatch
def getABFEpochTable(o, sweep:typing.Optional[int]=None,
                      dacChannel:typing.Optional[int] = None,
                      as_dataFrame:bool=False, allTables:bool=False) -> list:
    raise NotImplementedError(f"This function does not support {type(o).__name__} objects")

@getABFEpochTable.register(pyabf.ABF)
def _(x:pyabf.ABF, sweep:typing.Optional[int]=None,
                      dacChannel:typing.Optional[int] = None,
                      as_dataFrame:bool=False, allTables:bool=False) -> list:
    if not isinstance(x, pyabf.ABF):
        raise TypeError(f"Expecting a pyabf.ABF object; got {type(x).__name__} instead")
    
    sweepTables = list()
    
    if isinstance(sweep, int):
        if sweep < 0 or sweep >= x.sweepCount:
            raise ValueError(f"Invalid sweep {sweep} for {x.sweepCount} sweeps")
        
        x.setSweep(sweep)
        # NOTE: 2022-03-04 15:30:22
        # only return the epoch tables that actually contain any non-OFF epochs (filtered here)
        if isinstance(dacChannel, int):
            if dacChannel not in x._dacSection.nDACNum:
                raise ValueError(f"Invalid DAC channel index (dacChannel) {dacChannel}; current DAC channel indices are {x._dacSection.nDACNum}")
            
            etables = [pyabf.waveform.EpochTable(x, dacChannel)] # WARNING: 2023-09-06 23:36:28 may be an empty EpochTable
        else:
            if allTables:
                etables = list(pyabf.waveform.EpochTable(x, c) for c in x._dacSection.nDACNum)
                # etables = list(pyabf.waveform.EpochTable(x, c) for c in x.channelList)
            else:
                etables = list(filter(lambda e: len(e.epochs) > 0, (pyabf.waveform.EpochTable(x, c) for c in x.channelList)))
            
        if as_dataFrame:
            etables = [epochTable2DF(e, x) for e in etables]
            
        sweepTables.append(etables)
    
    else:
        for sweep in range(x.sweepCount):
            x.setSweep(sweep)
            if isinstance(dacChannel, int):
                if dacChannel not in x._dacSection.nDACNum:
                    raise ValueError(f"Invalid DAC channel index (dacChannel) {dacChannel}; current DAC channel indices are {x._dacSection.nDACNum}")
                
                etables = [pyabf.waveform.EpochTable(x, dacChannel)] # WARNING: 2023-09-06 23:36:28 may be an empty EpochTable
            else:
                if allTables:
                    etables = list(pyabf.waveform.EpochTable(x, c) for c in x._dacSection.nDACNum)
                else:
                    etables = list(filter(lambda e: len(e.epochs) > 0, (pyabf.waveform.EpochTable(x, c) for c in x.channelList)))
                
            if as_dataFrame:
                etables = [epochTable2DF(e, x) for e in etables]
                
            sweepTables.append(etables)
            
    return sweepTables

@getABFEpochTable.register(neo.Block)
def _(x:neo.Block, sweep:typing.Optional[int]=None,
                      dacChannel:typing.Optional[int] = None,
                      as_dataFrame:bool=False, allTables:bool=False) -> list:
    pass
    
@singledispatch
def epochTable2DF(obj, src) -> pd.DataFrame:
    """Returns a pandas.DataFrame with the data from the epoch table 'x'
    """
    raise NotImplementedError(f"{type(obj).__name__} objects are not supported")

# def _(x:pyabf.waveform.EpochTable, abf:typing.Optional[pyabf.ABF] = None):
@epochTable2DF.register(pyabf.waveform.EpochTable)
def _(x:pyabf.waveform.EpochTable, abf:typing.Optional[pyabf.ABF] = None) -> pd.DataFrame:
    # if not isinstance(x, pyabf.waveform.EpochTable):
    #     raise TypeError(f"Expecting an EpochTable; got {type(x).__name__} instead")

    # NOTE: 2022-03-04 15:38:31
    # code below adapted from pyabf.waveform.EpochTable.text
    #
    
    rowIndex = ["Type", "First Level", "Delta Level", "First Duration (points)", "Delta Duration (points)",
                "First duration (ms)", "Delta Duration (ms)",
                "Digital Pattern #3-0", "Digital Pattern #7-4", 
                "Train Period (points)", "Pulse Width (points)",
                "Train Period (ms)", "Pulse Width (ms)"]
    
    # prepare lists to hold values for each epoch
    
    # NOTE: 2022-03-04 16:05:20 
    # skip "Off" epochs
    epochs = [e for e in x.epochs if e.typeName != "Off"]
    
    if len(epochs):
        epochCount = len(epochs)
        epochLetters = [''] * epochCount
        
        epochData = dict()
        
        for i, epoch in enumerate(epochs):
            assert isinstance(epoch, pyabf.waveform.Epoch)
            
            if isinstance(abf, pyabf.ABF):
                # adcName, adcUnits = abf._getAdcNameAndUnits(x.channel)
                dacName, dacUnits = abf._getDacNameAndUnits(x.channel)
                
            else:
                dacName = dacUnits = None
                
            dacLevel = epoch.level*scq.unit_quantity_from_name_or_symbol(dacUnits) if isinstance(dacUnits, str) and len(dacUnits.strip()) else epoch.level
            dacLevelDelta = epoch.levelDelta*scq.unit_quantity_from_name_or_symbol(dacUnits) if isinstance(dacUnits, str) and len(dacUnits.strip()) else epoch.levelDelta

            epValues = np.array([epoch.epochTypeStr,    # str description of epoch type (as per Clampex e.g Step, Pulse, etc)                            
                              dacLevel,                 # "first" DAC level -> quantity; CAUTION units depen on Clampex and whether its telegraphs were OK
                              dacLevelDelta,            # "delta" DAC level: level change with each sweep in the run; quantity, see above
                              epoch.duration,           # "first" duration (samples)
                              epoch.durationDelta,      # "delta" duration (samples)
                              epoch.duration/x.sampleRateHz * 1000 * pq.ms, # first duration (time units)
                              epoch.durationDelta/x.sampleRateHz * 1000 * pq.ms, # delta duration (time units)
                              epoch.digitalPattern[:4], # first 4 digital channels
                              epoch.digitalPattern[4:], # last 4 digital channels
                              epoch.pulsePeriod,        # train period (samples`)
                              epoch.pulseWidth,         # pulse width (samples)
                              epoch.pulsePeriod/x.sampleRateHz * 1000 * pq.ms, # train period (time units)
                              epoch.pulseWidth/x.sampleRateHz * 1000 * pq.ms], # pulse width (time units)
                              dtype=object)
            
            epochData[epoch.epochLetter] = epValues
            
        #colIndex = epochLetters
        
        return pd.DataFrame(epochData, index = rowIndex)
    
@epochTable2DF.register(ABFEpoch)
def _(x:ABFEpoch, _=None) -> pd.DataFrame:
    return x.toDataFrame()
    
@singledispatch
def getABFHoldDelay(obj):
    """Returns the duration of holding time before actual sweep start.

    WARNING: Only works with a neo.Block generated from an Axon ABF file.
    
    The function first tries to create a pyabf.ABF object using the Axon (ABF)
    file as indicated in the 'file_origin' attribute of 'data'. 

    When this fails, (usually because the original ABF file cannot be found) the 
    function will inspect the 'annotations' attribute of 'data' as a fallback.
    If the data was read from an ABF file using Scipyen's pictio module, then the
    'annotations' attribute should already contain the relevant information.
    
    """    
    raise NotImplementedError(f"not implemented for {type(obj).__name__} objects")

@getABFHoldDelay.register(pyabf.ABF)
def _(abf:pyabf.ABF):
    isABF2 = abf.abfVersion["major"] == 2
    protocol = getABFsection(abf,"protocol")
    samplingPeriod = (1/(abf.sampleRate*pq.Hz)).rescale(pq.s)
    return int(abf.sweepPointCount/64) * samplingPeriod

@getABFHoldDelay.register(neo.Block)
def _(data:neo.Block):
    try:
        isABF2 = data.annotations["fFileSignature"].decode() == "ABF2"
        if not isABF2:
            raise NotImplementedError("This function only supports ABF2 version")
        
        protocol = data.annotations["protocol"]
        
        # NOTE: 2023-08-28 09:35:22
        # this could be obtained from the analogsignals, but what if someone
        # corrupts the data by inserting an analog signal with a different 
        # sampling rate? It seems 'neo' does not have a way to prevent that.
        samplingPeriod = 1 * pq.s/data.annotations["sampling_rate"]
        
        # NOTE: 2023-08-28 09:40:18
        # the number of points per sweep is calculated as (see pyabf):
        # dataPointCount / sweepCount / channelCount , where all are properties
        # of the pyabf.ABF object;
        # in the annotations, these are stored as follows:
        # dataPointCount    → ["sections"]["DataSection"]["llNumEntries"]
        # sweepCount        → ["lActualEpisodes"] = ["protocol"]["lEpisodesPerRun"]
        # channelCount      → ["sections"]["ADCSection"]["llNumEntries"]
        sweepPointCount = data.annotations["sections"]["DataSection"]["llNumEntries"] / data.annotations["lActualEpisodes"] / data.annotations["sections"]["ADCSection"]["llNumEntries"]
        
        return int(sweepPointCount/64) * samplingPeriod

    except:
        traceback.print_exc()
        raise RuntimeError(f"The {type(data).__name__} data {data.name} does not seem to have been generated from readind an ABF file")

@singledispatch
def getActiveDACChannel(obj) -> int:
    """Returns the index of the active DAC channel.

    WARNING: Only works with a neo.Block generated from an Axon ABF file.
    
    The function first tries to create a pyabf.ABF object using the Axon (ABF)
    file as indicated in the 'file_origin' attribute of 'data'. 

    When this fails, (usually because the original ABF file cannot be found) the 
    function will inspect the 'annotations' attribute of 'data' as a fallback.
    If the data was read from an ABF file using Scipyen's pictio module, then the
    'annotations' attribute should already contain the relevant information.
    
    """
    raise NotImplementedError(f"Not implemented for {type(obj).__name__} objects")
            
@getActiveDACChannel.register(pyabf.ABF)
def _(abf:pyabf.ABF) -> int:
    return abf._protocolSection.nActiveDACChannel
    
@getActiveDACChannel.register(neo.Block)
def _(data:neo.Block) -> int:
    try:
        isAxon = data.annotations.get("software", None) == "Axon"
        if not isAxon:
            raise NotImplementedError("This function suypports only data recorded with Axon software")
        isABF2 = data.annotations["fFileSignature"].decode() == "ABF2"
        if not isABF2:
            raise NotImplementedError("This function only supports ABF2 version")
        
        return data.annotations["protocol"]["nActiveDACChannel"]
    except:
        traceback.print_exc()
        raise RuntimeError(f"The {type(data).__name__} data {data.name} does not seem to have been generated from readind an ABF file")
    
    
@singledispatch
def getDACCommandWaveforms(obj, 
                        sweep:typing.Optional[int] = None,
                        adcChannel:typing.Optional[typing.Union[int, str]] = None,
                        dacChannel:typing.Optional[typing.Union[int, str]]=None,
                        absoluteTime:bool=False) -> dict:
    """Retrieves the waveforms of the command (DAC) signal.
    
    Returns one waveform per sweep (i.e., per neo.Segment) unless segmentIndex
    if specified, and has a valid int value.

    WARNING: Only works with a neo.Block generated from an Axon ABF file.
    
    The function first tries to create a pyabf.ABF object using the Axon (ABF)
    file as indicated in the 'file_origin' attribute of 'data'. 

    When this fails (usually because the original ABF file cannot be found) the 
    function will fallback on using information contained in the 'annotations' 
    attribute and the properties on the analog signals contained in the data.
    
    This is OK ONLY if the data was obtained by reading the ABF file using
    neo.io module via Scipyen's pictio module functions.
    
    CAUTION: Using synthetic data (e.g. neo.Block created manually) or data
    augmented manually (such as by adding manually-created segments and/or signals)
    will most likely result in an Exception being raised.
    
    """
    raise NotImplementedError(f"Not implemented for {type(obj).__name__} objects")

@getDACCommandWaveforms.register(pyabf.ABF)
def _(abf: pyabf.ABF, 
      sweep:typing.Optional[int] = None,
      adcChannel:typing.Optional[typing.Union[int, str]] = None,
      dacChannel:typing.Optional[typing.Union[int, str]] = None,
      absoluteTime:bool=False) -> dict:
    """Retrieves the waveforms of the command (DAC) signal."""
    
    # NOTE: 2023-08-28 15:31:13
    # each ADC input channels in Clampex is associated with one DAC output
    # for the most complete configuration, IN0 and IN1 are typically associated with OUT0
    # IN2 and IN3 are associated with OUT1, etc; here, IN0 and IN2 are the 
    # primary input channels from the amplifierl; IN1 and IN3 are the secondary
    # inputs from the amplifier
    
    def __f__(a_:abf, dacIndex:int) -> neo.AnalogSignal:
        x_units = scq.unit_quantity_from_name_or_symbol(abf.sweepUnitsX)
        x = abf.sweepX
        y_name, y_units_str = abf._getDacNameAndUnits(dacIndex)
        y_units = scq.unit_quantity_from_name_or_symbol(y_units_str) if isinstance(y_units_str, str) else pq.dimensionless
        abfChannel = abf.sweepChannel # the current channel in the ABF, set when calling abf.setSweep(…)
        
        # NOTE: 2023-08-28 15:09:15
        # the command waveform for this sweep
        # WARNING: this can be manually overwritten; in this case, all bets are off
        #
        # NOTE: when not overwritten, sweepC delegates to stimulus.dacWaveform
        # in turn this checks if a waveform is enabled, or if the waveform is
        # defined in a file;
        #
        # the variables nWaveformEnable and nWaveformSource are defined in 
        #   header (for ABF1)
        #   dac section (for ABF2)
        #
        # nWaveformEnable →   0 (disabled); 
        #                     1 (enabled)
        #
        # nWaveformSource →   0 (no waveform); 
        #                     1 (defined in the epoch table)
        #                     2 (defined in a separate file)
        #
        # if neither, then this will return a synthetic array filled with the 
        # holding values - not sure we want this, because, in effect, THERE IS NO
        # command waveform on that channel... But this information is not available
        # until one calls sweepC for that channel - so there is no way of knowing this beforehand
        #
        # So, instead of calling accessing sweepC (however convenient this may be)
        # we may want to directly run the actual stimulus code instead
        # (or call sweepC but then check the 'text' property of the correspdonding
        # stimulus, which has been updated while calling sweepC) - IMO the design
        # of pyabf is not ideal...
            
        y = abf.sweepC 
        
        stimObj = abf.stimulusByChannel[abfChannel]
        
        if stimObj.text == "DAC waveform is not enabled":
            # NOTE: 2023-09-02 22:41:41
            # this happens when there is no Epoch defined in the Epoch Table
            # for the given ADC/DAC channels combination
            y_name += " (disabled)"
            
        elif stimObj.text == "DAC waveform is controlled by custom file":
            y_name += " from file" # TODO 2023-08-31 15:29:15 FIXME get the name of the stimulus file
        # y_label = abf.sweepLabelC
        sampling_rate = abf.sampleRate * pq.Hz
        
        return neo.AnalogSignal(y, units = y_units, 
                                t_start = x[0] * x_units,
                                sampling_rate = abf.sampleRate * pq.Hz,
                                name = y_name)
        
    if isinstance(sweep, int):
        if sweep not in range(abf.sweepCount):
            raise ValueError(f"Invalid sweep {sweep} for {abf.sweepCount} sweeps")
        
    elif sweep is not None:
        raise TypeError(f"Expecting sweep an int in range {abf.sweepCount} or None; instead, got {type(sweep).__name__}")
    
    ADCs = usedADCs(abf)
    ADCnames = tuple(x[0] for x in ADCs.values())
    DACs = usedDACs(abf)
    DACnames = tuple(x[0] for x in DACs.values())
    
    if isinstance(adcChannel, int):
        # if adcChannel not in range(len(abf.adcNames)) :
        if adcChannel not in ADCs.keys() :
            raise ValueError(f"Invalid ADC channel {adcChannel} for ADC channels {tuple(ADCs.keys())}")
        
    elif isinstance(adcChannel, str):
        if adcChannel not in ADCnames:
            raise ValueError(f"ADC channel {adcChannel} not found; current ADC channels are {ADCnames}")
        
        adcChannel = ADCs[ADCnames.index(adcChannel)]
        
    elif adcChannel is not None:
        raise TypeError(f"adcChannel expected to be an int in {tuple(ADCs.keys())}, a string in {ADCnames}, or None; instead, got {type(adcChannel).__name__}")
        
    if isinstance(dacChannel, int):
        if dacChannel not in tuple(DACs.keys()):
            raise ValueError(f"Invalid ADAC channel {dacChannel} for DAC channels {tuple(DACs.keys())}")
        
    elif isinstance(dacChannel, str):
        if dacChannel not in DACnames:
            raise ValueError(f"DAC channel {dacChannel} not found; current DAC channels are {DACnames}")
        
        dacChannel = DACs[DACnames.index(dacChannel)]
        
    elif dacChannel is not None:
        raise TypeError(f"dacChannel expected to be an int in {tuple(DACs.keys())},a string in {DACnames}, or None; instead, got {type(dacChannel).__name__}")
    
    # ret = list()
    ret = dict()
    
    if not isinstance(sweep, int):
        for s in range(abf.sweepCount):
            if not isinstance(adcChannel, int):
                adcChannelWaves = dict()
                # for chnl in range(len(abf.adcNames)):
                for chnl in ADCs:
                    abf.setSweep(s, chnl, absoluteTime)
                    if not isinstance(dacChannel, int):
                        dacChannelWaves = dict()
                        # for dacChnl in range(len(abf.dacNames)):
                        for dacChnl in DACs:
                            dacChannelWaves[f"DAC_{dacChnl}_{DACs[dacChnl][0]}"] = __f__(abf, dacChnl)
                                            
                    else:
                        dacChannelWaves = {f"DAC_{dacChannel}_{DACs[dacChannel][0]}": __f__(abf, dacChannel)}
                        
                    adcChannelWaves[f"ADC_{chnl}_{ADCs[chnl][0]}"] = dacChannelWaves
            else:
                abf.setSweep(s, adcChannel, absoluteTime)
                if not isinstance(dacChannel, int):
                    dacChannelWaves = dict()
                    for dacChnl in range(len(abf.dacNames)):
                        dacChannelWaves[f"DAC_{dacChnl}_{DACs[dacChnl][0]}"] = __f__(abf, dacChnl)
                                        
                else:
                    dacChannelWaves = {f"DAC_{dacChannel}_{DACs[dacChannel][0]}": __f__(abf, dacChannel)}
                    
                adcChannelWaves = {f"ADC_{adcChannel}_{ADCs[adcChannel][0]}": dacChannelWaves}
                    
            ret[f"sweep_{s}"] = adcChannelWaves
            
    else:
        if not isinstance(adcChannel, int):
            adcChannelWaves = dict()
            # for adcChnl in range(len(abf.adcNames)):
            for adcChnl in ADCs:
                abf.setSweep(sweep, adcChnl, absoluteTime)
                if not isinstance(dacChannel, int):
                    dacChannelWaves = dict()
                    for dacChnl in DACs:
                        dacChannelWaves[f"DAC_{dacChnl}_{DACs[dacChnl][0]}"] = __f__(abf, dacChnl)
                                        
                else:
                    dacChannelWaves = {f"DAC_{dacChannel}_{DACs[dacChannel][0]}": __f__(abf, dacChannel)}
                    
                adcChannelWaves[f"ADC_{chnl}_{ADCs[chnl][0]}"] = dacChannelWaves
                
        else:
            abf.setSweep(sweep, adcChannel, absoluteTime)
            if not isinstance(dacChannel, int):
                # for dacChnl in range(abf._dacSection._entryCount):
                dacChannelWaves = dict()
                # for dacChnl in range(len(abf.dacNames)):
                for dacChnl in DACs:
                    dacChannelWaves[f"DAC_{dacChnl}_{DACs[dacChnl][0]}"] = __f__(abf, dacChnl)
                                    
            else:
                dacChannelWaves = {f"DAC_{dacChannel}_{DACs[dacChannel][0]}": __f__(abf, dacChannel)}
                
            adcChannelWaves[f"ADC_{adcChannel}_{ADCs[adcChannel][0]}"] = dacChannelWaves
            
        ret[f"sweep_{sweep}"] = adcChannelWaves
        
    return ret
            
@getDACCommandWaveforms.register(neo.Block)
def _(data:neo.Block,
      sweep:typing.Optional[int] = None,
      adcChannel:typing.Optional[typing.Union[int, str]] = None,
      dacChannel:typing.Optional[typing.Union[int, str]]=None,
      absoluteTime:bool=False) -> dict:

    def __f__(a_:abf, dacIndex:int) -> neo.AnalogSignal:
        x_units = scq.unit_quantity_from_name_or_symbol(abf.sweepUnitsX)
        x = abf.sweepX
        y_name, y_units_str = abf._getDacNameAndUnits(dacIndex)
        y_units = scq.unit_quantity_from_name_or_symbol(y_units_str)
        y = abf.sweepC # the command waveform for this sweep
        # y_label = abf.sweepLabelC
        sampling_rate = abf.sampleRate * pq.Hz
        
        return neo.AnalogSignal(y, units = y_units, 
                                t_start = x[0] * x_units,
                                sampling_rate = abf.sampleRate * pq.Hz,
                                name = y_name)
        
    sweepCount = data.annotations["lActualEpisodes"]
    
    # NOTE: 2023-08-30 12:15:16
    # just make sure no segments have been added/removed to the block after it 
    # has been read from its original ABF file
    if sweepCount != len(data.segments):
        raise RuntimeError(f"The number of segments ({len(data.segments)}) in the 'data' {data.name} is different from what ABF header reports ({sweepCount})")
    
    if isinstance(sweep, int):
        if sweep not in range(sweepCount):
            raise ValueError(f"Invalid sweep {sweep} for {sweepCount} sweeps")
        
    elif sweep is not None:
        raise TypeError(f"Expecting sweep an int in range {sweepCount} or None; instead, got {type(sweep).__name__}")
    
    # NOTE: 2023-08-30 12:56:11
    # number of ADC channels in the file is found in ADCSection.llNumEntries
    # NOTE: these are the ADC channels USED in the file, NOT ADC channels
    # available on the DAQ device!!!
    #
    # names and units of the ADC channels are placed by AxonRawIO into listADCInfo
    # (which therefore has same length as the number of ADC channels used in the
    # ABF file)
    #
    # it is therefore easy to figure out names & units (+ scaling etc) ONLY for
    # those ADC channels that have been used to record data
    
    adcCount = data.annotations["sections"]["ADCSection"]["llNumEntries"]
    
    adcNames = [i["ADCChNames"].decode() for i in data.annotations["listADCInfo"]]
    
    if isinstance(adcChannel, int):
        if adcChannel not in range(adcCount):
            raise ValueError(f"Invalid ADC channel {adcChannel} for {adcCount} ADC channels")
    
    elif isinstance(adcChannel, str):
        if adcChannel not in adcNames:
            raise ValueError(f"ADC channel {adcChannel} not found; current ADC channels are {adcNames}")
        
        adcChannel = adcNames.index(adcChannel)
        
    elif adcChannel is not None:
        raise TypeError(f"adcChannel expected to be an int in range 0 ... {adcCount}, a string in {adcNames}, or None; instead, got {type(adcChannel).__name__}")

    # NOTE: 2023-08-30 12:56:26
    # For DAC channels the situation is different: we have to dig out which of these
    # are actually used in the file/experiment, using the epoch info.
    #
    # the actual DAC used in each protocol epoch is contained in the 'dictEpochInfoPerDAC'
    # of the annotations.
    #
    # Structure of the dictEpochInfoPerDAC:
    #
    # dictEpochInfoPerDAC maps int keys (DAC number) with a nested dict
    #   the nested dict maps  key (Epoch number) to a sub-nested dict of fields
    #
    # Only the used DACs are included in dictEpochInfoPerDAC.
    #
    # So, if the Outputs tab of the protocol editor uses DAC channels 0 and 1 (e.g. 
    # "Cmd 0" and "Cmd 1")then the dictEpochInfoPerDAC will contain only two
    # key → value pairs, with keys (int) 0 and 1, each mapped to a sub-nested dict
    # of epochs describing the parameters sent to the corresponding DAC (0 or 1)
    #
    # Now, whether each DAC is used to send a command waveform to the electrode
    # is configured separately, in the "Epochs" tab of the protocol editor; this 
    # information is given in the 'listDACInfo'
    #
    # listDACInfo is a list of dicts, expected to be ordered by the DAC output channel
    #
    # CAUTION: 2023-08-30 14:15:11
    # this is where pyabf bridge may be supplying redundant information
    #
    usedDacCount = len(data.annotations["dictEpochInfoPerDAC"])
    
    usedDACIndices = list(data.annotations["dictEpochInfoPerDAC"].keys())
    
    # if dacChannel
    
@singledispatch
def getABFversion(obj) -> int:
    raise NotImplementedError(f"Not implemented for {type(obj).__name__} objects")
        
@getABFversion.register(pyabf.ABF)
def _(obj:pyabf.ABF) -> int:
    return abf.abfVersion["major"]

@getABFversion.register(neo.Block)
def _(obj:neo.Block) -> int:
    abf_version = obj.annotations.get("abf_version", None)
    assert isinstance(abf_version, float), "Object does not seem to be created from an ABF file"
    
    abf_version = int(abf_version)
    
    fFileSignature = obj.annotations.get("fFileSignature", None)
    
    assert isinstance(fFileSignature, bytes), "Object does not seem to be created from an ABF file"
    
    fileSig = fFileSignature.decode()
    fileSigVersion = int(fileSig[-1])
    
    assert abf_version == fileSigVersion, "Mismatch between reported ABF versions; check obejct's annotations properties"
    
    fFileVersionNumber = obj.annotations.get("fFileVersionNumber", None)
    
    assert isinstance(fFileVersionNumber, float), "Object does not seem to be created from an ABF file"
    
    fileVersionMajor = int(fFileVersionNumber)
    
    assert abf_version == fileVersionMajor, "Mismatch between reported ABF versions; check obejct's annotations properties"
    
    return abf_version

@singledispatch
def usedADCs(obj, useQuantities:bool=True) -> dict:
    """Returns a mapping of used ADC channel index (int) to pair (name, units).

    Units are returned as a python Quantity if useQuantities is True, else as
    a string (units symbol)
"""
    raise NotImplementedError(f"Not implemented for {type(obj).__name__} objects")
    
@usedADCs.register(pyabf.ABF)
def _(obj:pyabf.ABF, useQuantities:bool=True) -> dict:
    return dict(map(lambda x: (x, __wrap_to_quantity__(obj._getAdcNameAndUnits(x), useQuantities)), 
                    obj._adcSection.nADCNum))

@usedADCs.register(neo.Block)
def _(obj:neo.Block, useQuantities:bool=True) -> dict:
    assert sourcedFromABF(obj), "Object does not appear to be sourced from ABF"
    return dict(map(lambda x: (x, (obj.annotations["listADCInfo"][x]["ADCChNames"].decode(),
                                   unitStrAsQuantity(obj.annotations["listADCInfo"][x]["ADCChUnits"].decode(), useQuantities))),
                    range(obj.annotations["sections"]["ADCSection"]["llNumEntries"])))

@singledispatch
def usedDACs(obj, useQuantities:bool=True) -> dict:
    """Returns a mapping of used DAC channel index (int) to pair (name, units)

    Units are returned as a python Quantity if useQuantities is True, else as
    a string (units symbol)
"""
    raise NotImplementedError(f"Not implemented for {type(obj).__name__} objects")

@usedDACs.register(pyabf.ABF)
def _(obj:pyabf.ABF, useQuantities:bool=True) -> dict:
    return dict(map(lambda d: (d, __wrap_to_quantity__(obj._getDacNameAndUnits(d), useQuantities)),
                    filter(lambda x: obj._dacSection.nWaveformEnable[x] and obj._dacSection.nWaveformSource[x] > 0, obj._dacSection.nDACNum)))
    
@usedDACs.register(neo.Block)
def _(obj:neo.Block, useQuantities:bool=True) -> dict:
    assert sourcedFromABF(obj), "Object does not appear to be sourced from ABF"
    
    return dict(map(lambda d: (d["nDACNum"], (d["DACChNames"].decode(), unitStrAsQuantity(d["DACChUnits"].decode(), useQuantities))),
                    filter(lambda x: x["nWaveformEnable"] > 0 and x["nWaveformSource"] > 0, obj.annotations["listDACInfo"])))
    
@singledispatch    
def isDACWaveformEnabled(obj, channel:int) -> bool:
    raise NotImplementedError(f"Not implemented for {type(obj).__name__} objects")
            
@isDACWaveformEnabled.register(pyabf.ABF)
def _(obj, dacChannel:int) -> bool:
    abf_version = getABFversion(obj)
    assert abf_version in (1,2), f"Unsupported ABF version {abf_version}"
    
    section = obj._headerV1 if abf_version == 1 else obj._dacSection
    
    return obj._dacSection.nWaveformEnable[dacChannel] == 1
    
@isDACWaveformEnabled.register(neo.Block)
def _(obj, channel:int) -> bool:
    assertFromABFmsg = "Object does not seem to be created from an ABF file"
    abf_version = getABFversion(obj)
    assert abf_version in (1,2), f"Unsupported ABF version {abf_version}"
    
    epochInfoPerDAC = data.annotations.get("dictEpochInfoPerDAC", None)
    
    assert isinstance(epochInfoPerDAC, dict) , assertFromABFmsg
    
    assert channel in epochInfoPerDAC.keys(), f"ADC channel {channel} if not used"
    
    channelEpochInfoPerDac = epochInfoPerDAC[channel]
    
    
        
    
    
        
