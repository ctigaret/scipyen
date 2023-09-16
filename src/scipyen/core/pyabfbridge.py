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
    
    this is effectivelyan alias to abf._dacSection.fDACHoldingLevel
    
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
use the epiochs defined on DAC Channel #1. When this option is switched off, and 
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
    in the protocol
    
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
import typing, struct, inspect, itertools, functools
from functools import singledispatch, partial
import numpy as np
import pandas as pd
import quantities as pq
import neo
import pyabf

from core import quantities as scq
from core import datatypes, strutils
from iolib import pictio as pio

from pyabf.abf1.headerV1 import HeaderV1
from pyabf.abf2.headerV2 import HeaderV2
from pyabf.abf2.section import Section
from pyabf.abfReader import AbfReader
from pyabf.stimulus import (findStimulusWaveformFile, 
                            stimulusWaveformFromFile)

# useful alias:
ABF = pyabf.ABF

# This is 8 for DigiData 1550 series, and 4 for DigiData 1440 series
DIGITAL_OUTPUT_COUNT = pyabf.waveform._DIGITAL_OUTPUT_COUNT # 8

class ABFAcquisitionMode(datatypes.TypeEnum):
    """Corresponds to nOperationMode in ABF and annotations"""
    variable_length_event = 1
    fixed_length_event = 2
    gap_free = 3
    high_speed_oscilloscope = 4 # Not supported by neo, but supported by pyabfbridge!
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
    """Encapsulates an ABF Epoch.
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
        
    @property
    def epochLetter(self):
        return epochLetter(self.epochNumber)
    
    @property
    def epochNumber(self) -> int:
        return self._epochNumber_
    
    @epochNumber.setter
    def epochNumber(self, val:int):
        self._epochNumber_ = val
        
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
        
    def nSamples(self, x, sampling_rate:pq.Quantity):
        assert isinstance(sampling_rate, pq.Quantity) and scq.check_time_units(1./sampling_rate), f"sampling rate {sampling_rate} is not a frequency quantity"
        return x.rescale(pq.s) * sampling_rate
    
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
        
    @property
    def useAlternateDigitalPattern(self) -> bool:
        return self._useAltPattern_
    
    @useAlternateDigitalPattern.setter
    def useAlternateDigitalPattern(self, val:bool):
        self._useAltPattern_ = val == True
        
    @property
    def hasAlternateDigitalOutputState(self) -> bool:
        return self._altDIGOutState_
    
    @hasAlternateDigitalOutputState.setter
    def hasAlternateDigitalOutputState(self, val:bool):
        self._altDIGOutState_ = val == True
        
    @property
    def digitalPattern(self) -> tuple:
        """Read-only"""
        return self.alternateDigitalPattern if (self.hasAlternateDigitalOutputState and self.useAlternateDigitalPattern) else self.mainDigitalPattern
        
        
        
class ABFEpochTable:
    """Encapsulates and ABF Epoch Table
    Similar to pyabf.waveform.EpochTable but uses Quantities in the relevant places
    and generates command waveforms and digital patterns when required.
    Also takes into account digital train pulses ("starred" patterns).
    """
    def __init__(self, obj:typing.Union[pyabf.ABF, neo.Block], 
                 dacChannel:int,
                 sweep:typing.Optional[int] = None):
        if isinstance(obj, pyabf.ABF):
            abfVer = obj.abfVersion["major"]
            if abfVer == 1:
                if dacChannel > 1:
                    dacChannel = 0
                self.nInterEpisodeLevel = bool(obj._headerV1.nInterEpisodeLevel[dacChannel])
                self.dacChannel = dacChannel
                
            elif abfVer == 2:
                if dacChannel not in obj._dacSection.nDACNum:
                    raise ValueError(f"Invalid DAC channel index {dacChannel}")
                
                self.dacChannel = dacChannel
                
                dacName = obj.dacNames[dacChannel] if dacChannel in obj.dacNames else ""
                dacUnits = obj.dacUnits[dacChannel] if dacChannel in obj.dacUnits else "mV"
                self.DACName = dacName 
                self.DACUnits = scq.unit_quantity_from_name_or_symbol(dacUnits)
                self.nDataPointsPerSweep = obj.sweepPointCount
                self.nDigitalOutputs = obj._dacSection._entryCount
                self.samplingRate = float(obj.dataRate) * pq.Hz
                self.DACHoldingLevel = float(obj._dacSection.fDACHoldingLevel[dacChannel]) * self.DACUnits
                self.nInterEpisodeLevel = bool(obj._dacSection.nInterEpisodeLevel[dacChannel])
            else:
                raise NotImplementedError(f"ABF version {abfVer} is not supported")
            
        elif isinstance(obj, neo.Block):
            assert sourcedFromABF(obj), "Object does not appear to be sourced from an ABF file"
            if dacChannel not in (c["nDACNum"] for c in obj.annotations["listDACInfo"]):
                raise ValueError(f"Invalid DAC channel index {dacChannel}")
            self.dacChannel = dacChannel
            self.DACName = obj.annotations["listDACInfo"][dacChannel]["DACChNames"].decode()
            self.DACUnits = scq.unit_quantity_from_name_or_symbol(obj.annotations["listDACInfo"][dacChannel]["DACChUnits"].decode())

            nSweeps = obj.annotations["protocol"]["lEpisodesPerRun"]
            nADCChannels = obj.annotations["sections"]["ADCSection"]["llNumEntries"]
            nTotalDataPoints = obj.annotations["sections"]["DataSection"]["llNumEntries"]
            self.nDataPointsPerSweep = int(nTotalDataPoints/nSweeps/nADCChannels)
            
            self.nDigitalOutputs = obj.annotations["sections"]["DACSection"]["llNumEntries"]
            self.samplingRate = float(obj.annotations["sampling_rate"]) * pq.Hz
            self.DACHoldingLevel = float(obj.annotations["listDACInfo"][dacChannel]["fDACHoldingLevel"]) * self.DACUnits
            self.nInterEpisodeLevel = bool(obj.annotations["listDACInfo"][dacChannel]["nInterEpisodeLevel"])
        else:
            raise TypeError(f"Expecting an ABF or a neo.Block sourced from an ABF file; instead, got {type(obj).__name__}")
    
        if np.abs(self.DACHoldingLevel).magnitude > 1e6:
            self.DACHoldingLevel = np.nan * self.DACUnits
            
        elif np.abs(self.DACHoldingLevel).magnitude > 0 and np.abs(self.DACHoldingLevel).magnitude < 1e-6:
            self.DACHoldingLevel = 0.0 * self.DACUnits
            
        self._epochs_ = list()
        
        self._init_epochs_(obj)
        
    def _init_epochs_(self, obj):
        if isinstance(obj, pyabf.ABF):
            self._init_epochs_abf_(obj)
            
        else:
            # assert self.dacChannel in obj.annotations["dictEpochInfoPerDAC"], f"DAC channel {self.dacChannel} is not used"
            
            # epochNums = list(obj.annotations["dictEpochInfoPerDAC"][self.dacChannel].keys())
            digPatterns = getDIGPatterns(obj)
            if self.dacChannel in obj.annotations["dictEpochInfoPerDAC"]:
                dacEpochDict = obj.annotations["dictEpochInfoPerDAC"][self.dacChannel]
                epochs = list()
                for epochNum, epochDict in dacEpochDict.items():
                    epoch = ABFEpoch()
                    epoch.epochNumber = epochNum
                    epoch.epochType = epochDict["nEpochType"]
                    epoch.firstLevel = epochDict["fEpochInitLevel"] * self.DACUnits
                    epoch.deltaLevel = epochDict["fEpochLevelInc"] * self.DACUnits
                    epoch.firstDuration = (epochDict["lEpochInitDuration"] / self.samplingRate).rescale(pq.ms)
                    epoch.deltaDuration = (epochDict["lEpochDurationInc"] / self.samplingRate).rescale(pq.ms)
                    epoch.pulsePeriod = (epochDict["lEpochPulsePeriod"] / self.samplingRate).rescale(pq.ms)
                    epoch.pulseWidth = (epochDict["lEpochPulseWidth"] / self.samplingRate).rescale(pq.ms)
                    epoch.hasAlternateDigitalOutputState = bool(obj.annotations["protocol"]["nAlternateDigitalOutputState"])
                    
                    if self.dacChannel == obj.annotations["protocol"]["nActiveDACChannel"] or epoch.hasAlternateDigitalOutputState:
                        epoch.mainDigitalPattern = digPatterns[epoch.epochNumber]["main"]
                        epoch.alternateDigitalPattern = digPatterns[epoch.epochNumber]["alternate"]
                        if obj.annotations["listDACInfo"][self.dacChannel]["nWaveformEnable"] == 1:
                            epoch.useAlternateDigitalPattern = False
                        else:
                            epoch.useAlternateDigitalPattern = True
                
                    epochs.append(epoch)
                
                self._epochs_ = epochs
            
    def _init_epochs_abf_(self, obj):
        # NOTE: no digital patterns in ABFv1 ?
        abfVer = obj.abfVersion["major"]
        epochs = list()
        
        if abfVer == 1:
            assert len(obj._headerV1.nEpochType) == 20, f"Expecting 20 memory slots for epoch info; instead got {len(obj._headerV1.nEpochType)}"
            
            for i in range(20):
                epoch = ABFEpoch()
                epoch.epochNumber = i % 10 # first -> 0-9: channel 0; last 0-9 -> channel 1
                epoch.epochType = obj._headerV1.nEpochType[i]
                epoch.firstLevel = obj._headerV1.fEpochInitLevel[i] * self.DACUnits
                epoch.deltaLevel = obj._headerV1.fEpochLevelInc[i] * self.DACUnits
                epoch.firstDuration = (obj._headerV1.lEpochInitDuration[i] / self.samplingRate).rescale(pq.ms)
                epoch.deltaDuration = (abf._headerV1.lEpochDurationInc[i] / self.samplingRate).rescale(pq.ms)
                epoch.pulsePeriod = 0 * pq.ms # not supported in ABF1
                epoch.pulseWidth = 0 * pq.ms # not supported in ABF1
                epochs.append(epoch)
                
            if self.dacChannel == 0:
                self._epochs_ = epochs[0:10]
                
            elif self.dacChannel == 1:
                self._epochs_ = epochs[10:20]
            else:
                warnings.debug("ABF1 does not support stimulus waveforms >2 DACs")
                self._epochs_.clear()
                
        elif abfVer == 2:
            digPatterns = getDIGPatterns(obj)
            
            # the epoch table is stored in _epochPerDacSection
            for i, epochDacNum in enumerate(obj._epochPerDacSection.nDACNum):
                # FIXME: 2023-09-14 22:49:09
                # for alternate DIG outputs you need TWO DACs even if only one
                # DAC channel is used!
                # RESOLVED?: you DO NOT need this info here
                if epochDacNum != self.dacChannel:
                    continue

                epoch = ABFEpoch()
                epoch.epochNumber = obj._epochPerDacSection.nEpochNum[i]
                epoch.epochType = obj._epochPerDacSection.nEpochType[i]
                epoch.firstLevel = obj._epochPerDacSection.fEpochInitLevel[i] * self.DACUnits
                epoch.deltaLevel = obj._epochPerDacSection.fEpochLevelInc[i] * self.DACUnits
                epoch.firstDuration = (obj._epochPerDacSection.lEpochInitDuration[i] / self.samplingRate).rescale(pq.ms)
                epoch.deltaDuration = (obj._epochPerDacSection.lEpochDurationInc[i] / self.samplingRate).rescale(pq.ms)
                epoch.pulsePeriod = (obj._epochPerDacSection.lEpochPulsePeriod[i] / self.samplingRate).rescale(pq.ms)
                epoch.pulseWidth = (obj._epochPerDacSection.lEpochPulseWidth[i] / self.samplingRate).rescale(pq.ms)
                epoch.hasAlternateDigitalOutputState = bool(obj._protocolSection.nAlternateDigitalOutputState)

                if epochDacNum == obj._protocolSection.nActiveDACChannel or epoch.hasAlternateDigitalOutputState:
                    epoch.mainDigitalPattern = digPatterns[epoch.epochNumber]["main"]
                    epoch.alternateDigitalPattern = digPatterns[epoch.epochNumber]["alternate"]
                    if obj._dacSection.nWaveformEnable[self.dacChannel] == 1:
                        epoch.useAlternateDigitalPattern = False
                    else:
                        epoch.useAlternateDigitalPattern = True
                    
                epochs.append(epoch)
                
            self._epochs_ = epochs

        else:
            raise NotImplementedError(f"ABf version {abfVer} is not supported")
            
    @property
    def returnToHold(self) -> bool:
        """When True, the command waveform returns to self.DACHoldingLevel after the last defined epoch"""
        return self.nInterEpisodeLevel
    
    @property
    def epochs(self) -> list:
        return self._epochs_

    @property
    def text(self):
        """
        Given a list of epochs, return a text string formatted to look like the
        epoch table displayed as plain text in pCLAMP and ClampFit.
        """

        # create a copy of the epochs list we can modify
        epochList = self.epochs

        # remove empty epochs
        epochList = [x for x in epochList if x.firstDuration > 0*pq.ms]

        # prepare lists to hold values for each epoch
        epochCount = len(epochList)
        epochLetters = [''] * epochCount
        epochTypes = [''] * epochCount
        epochLevels = [''] * epochCount
        epochLevelsDelta = [''] * epochCount
        durations = [''] * epochCount
        durationsDelta = [''] * epochCount
        # durationsMs = [''] * epochCount
        # durationsDeltaMs = [''] * epochCount
        digitalPatternLs = [''] * epochCount
        digitalPatternHs = [''] * epochCount
        trainPeriods = [''] * epochCount
        pulseWidths = [''] * epochCount

        # populate values for each epoch
        pointsPerMsec = self.samplingRate*1000
        for i, epoch in enumerate(epochList):
            assert isinstance(epoch, ABFEpoch)
            if epoch.typeName in (ABFEpochType.Unknown, ABFEpochType.Off):
                continue
            epochLetters[i] = epoch.epochLetter
            epochTypes[i] = epoch.typeName
            epochLevels[i] = f"{epoch.firstLevel}"
            epochLevelsDelta[i] = f"{epoch.deltaLevel}"
            durations[i] = f"{epoch.firstDuration} ({epoch.nSamples(epoch.firstDuration, self.samplingRate)} samples)"
            durationsDelta[i] = f"{epoch.deltaDuration} ({epoch.nSamples(epoch.deltaDuration, self.samplingRate)} samples)"
            digitalPatternLs[i] = "".join(map(str, epoch.digitalPattern[0]))
            digitalPatternHs[i] = "".join(map(str, epoch.digitalPattern[1]))
            trainPeriods[i] = f"{epoch.pulsePeriod} ({epoch.nSamples(epoch.pulsePeriod, self.samplingRate)} samples)"
            pulseWidths[i] = f"{epoch.pulseWidth} ({epoch.nSamples(epoch.pulseWidth, self.samplingRate)} samples)"

        # convert list of epoch values to a formatted string
        padLabel = 25
        pad = 10
        txt = ""
        txt += "EPOCH".rjust(padLabel)
        txt += " ".join([x.rjust(pad) for x in epochLetters])+"\n"
        txt += "Type".rjust(padLabel)
        txt += " ".join([x.rjust(pad) for x in epochTypes])+"\n"
        txt += "First Level ".rjust(padLabel)
        txt += " ".join([x.rjust(pad) for x in epochLevels])+"\n"
        txt += "Delta Level ".rjust(padLabel)
        txt += " ".join([x.rjust(pad) for x in epochLevelsDelta])+"\n"
        txt += "First Duration ".rjust(padLabel)
        txt += " ".join([x.rjust(pad) for x in durations])+"\n"
        txt += "Delta Duration ".rjust(padLabel)
        txt += " ".join([x.rjust(pad) for x in durationsDelta])+"\n"
        txt += "Digital Pattern #3-0 ".rjust(padLabel)
        txt += " ".join([x.rjust(pad) for x in digitalPatternLs])+"\n"
        txt += "Digital Pattern #7-4 ".rjust(padLabel)
        txt += " ".join([x.rjust(pad) for x in digitalPatternHs])+"\n"
        txt += "Train Period ".rjust(padLabel)
        txt += " ".join([x.rjust(pad) for x in trainPeriods])+"\n"
        txt += "Pulse Width ".rjust(padLabel)
        txt += " ".join([x.rjust(pad) for x in pulseWidths])+"\n"
        return txt.strip('\n')
    
    @property
    def dataFrame(self):
        # if len(self.epochs) == 0:
        #     return
        
        rowIndex = ["Type", "First Level", "Delta Level",
                    "First duration", "Delta Duration",
                    "Digital Pattern #3-0", "Digital Pattern #7-4", 
                    "Train Period", "Train Rate", "Pulse Width"]
        
        epochData = dict()
        
        for i, epoch in enumerate(self.epochs):
            epValues = [epoch.typeName, epoch.firstLevel, epoch.deltaLevel,
                        epoch.firstDuration, epoch.deltaDuration,
                        "".join(map(str, epoch.digitalPattern[0])), 
                        "".join(map(str, epoch.digitalPattern[1])),
                        epoch.pulsePeriod, epoch.pulseFrequency,
                        epoch.pulseWidth]
            
            epochData[epoch.epochLetter] = epValues
            
        return pd.DataFrame(epochData, index = rowIndex)
    
    def getEpoch(self, e:typing.Union[str, int]):
        if isinstance(e, str):
            e = epochNumberFromLetter(e)
            
        if e < 0 or e >= len(self.epochs):
            return
        
        return self.epochs[e]
    
    @property
    def holdingTime(self) -> pq.Quantity:
        samplingPeriod = (1/self.samplingRate).rescale(pq.s)
        return int(self.nDataPointsPerSweep/64) * samplingPeriod
    
    def stimulusWaveform(self, sweep:int=0) -> neo.AnalogSignal: 
        waveform = neo.AnalogSignal(np.full((self.nDataPointsPerSweep, 1), 0.),
                                    units = self.DACUnits, t_start = 0*pq.s,
                                    sampling_rate = self.samplingRate,
                                    name = self.DACName)
        # if len(self.epochs) == 0:
        #     return waveform
        
        t0 = t1 = self.holdingTime.rescale(pq.s)
        
        for epoch in self.epochs:
            actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
            actualLevel = epoch.firstLevel + sweep * epoch.deltaLevel

            t1 = t0 + actualDuration
            
            # TODO 2023-09-17 00:06:08
            # other epoch types as well
            
            # TODO: 2023-09-17 00:19:50
            # take account of alternate waveforms -> FIXME define relevant attribute in __init__ !!!
            if epoch.epochType == ABFEpochType.Step:
                tt = np.array([t0,t1])*pq.s
                ndx = waveform.time_index(tt)
                waveform[ndx[0]:ndx[1]+1,0] = actualLevel
                
            t0 = t1
            
                
        return waveform
    
    def digitalWaveform(self) -> neo.AnalogSignal:
        # TODO: 2023-09-17 00:20:07
        pass
        
        
        
        
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
        # NOTE: when not overwritten, sweepC delegates to stimulus.stimulusWaveform
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
    
    
        
    
    
        
