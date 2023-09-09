"""Module to access ABF meta-information.

This modules provides functionality to access "metadata" (e.g. command waveforms, 
protocol details) associated with electrophysiology data recorded using Axon 
hardware and software (pClamp suite/Clampex).

Scipyen uses the neo package (https://neo.readthedocs.io/en/stable/) to read
signal data from electrophysiology recordings from Axon ABF files and represent 
it in a coherent system of hierarchical containers, where the electrophysiological
data is contained in a neo.Block (see Table 1)

However, the PyABF (https://swharden.com/pyabf/) package offers complementary
functionality for a more convenient access to the information in the ABF file
about the experimental protocol (as defined in Clampex) and hardware
configuration (ABF "meta-information"). 

The functions defined in this module use the pyabf package to access the ABF
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
    
    this is effectivelyan alias to abf._dacSection.fDACHoldinglevel
    
    len(abf.holdingCommand) = abf._dacSection._entryCount = len(annotations["listDACInfo"])
    
    abf.holdingCommand[κ] = annotations["listDACInfo"][κ]["fDACHoldinglevel"]
    

2. Information about the DAC channels
=====================================
abf._dacSection

• nDACNum: list of DAC output channels by number: (0-3 for Digitdata 1440 series,
    0-7 for Digidata 1550 series, see also NOTE: 2023-09-03 22:26:46)
    length is 4 (DigiData 1440) or 8 (DigiData 1550) - the number of output DACs
    available (either used or not)
    
        = annotations["sections"]["DACSection"]["llNumEntries"]
        = len(annotations["listDACInfo"])
        
    nDACNum[κ] = annotations["listDACInfo"][κ]["nDACNum"]
    
• fDACHoldinglevel: list of holding levels, one per DAC channel

    fDACHoldinglevel[κ] = annotations["listDACInfo"][κ]["fDACHoldinglevel"]
    
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



3. Digital outputs (and patterns)
==================================
    
3.1. ALL DAC channels are available in the protocol editor, but 
only ONE DAC channel can associate a digital output at any time.

However, turning on "Alternate digital outputs" allows one to set digital output
patterns on up to TWO DACs (which will be used on alternative Sweeps in the Run).

3.2. Digital output specification follows a relatively simple pattern in 
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

4. Protocol Epochs
===================
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


4.1 Epoch section:
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

WARNING: Eppoch attribute names are case sensitive, so make sure you type 
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

# NOTE: for digital pattern things are a bit more complicated; see getDIGPatterns(…)

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
from core import datatypes
from iolib import pictio as pio

from pyabf.abf1.headerV1 import HeaderV1
from pyabf.abf2.headerV2 import HeaderV2
from pyabf.abf2.section import Section
from pyabf.abfReader import AbfReader
from pyabf.stimulus import (findStimulusWaveformFile, 
                            stimulusWaveformFromFile)

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
    
    # def epochTypeStr(self):
    #     if self.epochType == 0:
    #         return "Off"
    #     elif self.epochType == 1:
    #         return "Step"
    #     elif self.epochType == 2:
    #         return "Ramp"
    #     elif self.epochType == 3:
    #         return "Pulse"
    #     elif self.epochType == 4:
    #         return "Tri"
    #     elif self.epochType == 5:
    #         return "Cos"
    #     elif self.epochType == 7:
    #         return "BiPhsc"
    #     else:
    #         return "Unknown"

class ABFEpoch:
    def __init__(self):
        self.epochNumber = -1
        self.epochType = ABFEpochType.Unknown
        self.level = -1
        self.levelDelta = -1
        self.duration = -1
        self.durationDelta = -1
        self.digitalPattern = None
        self.pulsePeriod = -1
        self.pulseWidth = -1
        self.dacNum = -1

# useful alias:
ABF = pyabf.ABF

def epochLetter(epochNumber:int):
    # from pyabf.waveform.Epoch
    if epochNumber < 0:
        return "?"
    letter = ""
    while epochNumber >= 0:
        letter += chr(epochNumber % 26 + 65)
        epochNumber -= 26
        
    return letter

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
    """Return a specified ABF section as a dict.
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
def getDIGPatterns(o, reverse_banks:bool=False, wrap:bool=False, pack_str:bool=False) -> dict:
    raise NotImplementedError(f"This function does not support objects of {type(o).__name__} type")

@getDIGPatterns.register(neo.Block)
def _(obj:neo.Block, reverse_banks:bool=False, wrap:bool=False, pack_str:bool=False) -> dict:
    
    # check of this neo.Block was read from an ABF file
    sourcedFromABF(obj)
    
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
        d = getSynchBitList(epoch_info["nDigitalValue"])
        s = getSynchBitList(epoch_info["nDigitalTrainValue"])
        da = getAlternateBitList(epoch_info["nAlternateDigitalValue"])
        sa = getAlternateBitList(epoch_info["nAlternateDigitalTrainValue"])
        
        digitalPattern = list()
        
        for k in banks: 
            pattern = list()
            for i in range(len(d[k])):
                val = 1 if d[k][i] and not s[k][i] else '*' if s[k][i] and not d[k][i] else 0
                pattern.append(val)
                
            if wrap:
                digitalPattern.extend(pattern)
                if pack_str:
                    digitalPattern = "".join(map(str, digitalPattern))
            else:
                digitalPattern.append("".join(map(str, pattern)) if pack_str else pattern)
                    
        alternateDigitalPattern = list()
        # for k in range(2):
        for k in banks:
            pattern = list()
            for i in range(len(da[k])):
                val = 1 if da[k][i] and not sa[k][i] else '*' if sa[k][i] and not da[k][i] else 0
                pattern.append(val)
                
            if wrap:
                alternateDigitalPattern.extend(pattern)
                if pack_str:
                    alternateDigitalPattern = "".join(map(str, alternateDigitalPattern))
            else:
                alternateDigitalPattern.append("".join(map(str, pattern)) if pack_str else pattern)
        
        epochsDigitalPattern[epochNumber] = {"pattern": digitalPattern, "alternate": alternateDigitalPattern}
                
    return epochsDigitalPattern #, epochNumbers, epochDigital, epochDigitalStarred, epochDigitalAlt, epochDigitalStarredAlt

@getDIGPatterns.register(pyabf.ABF)
def _(abf:pyabf.ABF, reverse_banks:bool=False, wrap:bool=False, pack_str:bool=False) -> dict:
    """Creates a representation of the digital pattern associated with a DAC channel.

    Requires access to the original ABF file, because we are using our own
    algorithm to decode digital output trains.

    Returns a mapping (dict) with 

    Key                     ↦   Value:
    =======================================
    int (Epoch number)      ↦   mapping (dict) str ↦ list

    The nested dict maps:
    str ("pattern" or "alternate") ↦ list of int (0 or 1) or the character '*'
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
        epochDigitalAlt = [None] * nEpochs
        epochDigitalStarredAlt = [None] * nEpochs
        
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
            # epochNumbers[i] = epochNumber
            # epochDigital[i] = epochDig
            # epochDigitalStarred[i] = epochDigS
            # epochDigitalAlt[i] = epochDig_alt
            # epochDigitalStarredAlt[i] = epochDigS_alt
            
            epochDict = dict()
            
            # each of these is a list of two lists (DIG bank 3-0 and DIG bank 7-4)
            d = getSynchBitList(epochDig)           # steps
            s = getSynchBitList(epochDigS)          # pulses (starred)
            da = getAlternateBitList(epochDig_alt)  # alternative steps
            sa = getAlternateBitList(epochDigS_alt) # alternative pulses
            
            # print(f"epochDig = {epochDig} ⇒ {d}")
            # print(f"epochDigS = {epochDigS} ⇒ {s}")
            # print(f"epochDig_alt = {epochDig_alt} ⇒ {da}")
            # print(f"epochDigS_alt = {epochDigS_alt} ⇒ {sa}")
            
            # digitalPattern = [0] * abf._protocolSection.nDigitizerSynchDigitalOuts
            
            digitalPattern = list()
            
            # for k in range(2): # two banks
            for k in banks: 
                pattern = list()
                for i in range(len(d[k])):
                    val = 1 if d[k][i] and not s[k][i] else '*' if s[k][i] and not d[k][i] else 0
                    pattern.append(val)
                    
                if wrap:
                    digitalPattern.extend(pattern)
                    if pack_str:
                        digitalPattern = "".join(map(str, digitalPattern))
                else:
                    digitalPattern.append("".join(map(str, pattern)) if pack_str else pattern)
                    
            alternateDigitalPattern = list()
            # for k in range(2):
            for k in banks:
                pattern = list()
                for i in range(len(da[k])):
                    val = 1 if da[k][i] and not sa[k][i] else '*' if sa[k][i] and not da[k][i] else 0
                    pattern.append(val)
                    
                if wrap:
                    alternateDigitalPattern.extend(pattern)
                    if pack_str:
                        alternateDigitalPattern = "".join(map(str, alternateDigitalPattern))
                else:
                    alternateDigitalPattern.append("".join(map(str, pattern)) if pack_str else pattern)
                
            epochsDigitalPattern[epochNumber] = {"pattern": digitalPattern, "alternate": alternateDigitalPattern}
                    
        return epochsDigitalPattern #, epochNumbers, epochDigital, epochDigitalStarred, epochDigitalAlt, epochDigitalStarredAlt
        
def getABFEpochsTable(x:pyabf.ABF, sweep:typing.Optional[int]=None,
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
                    # etables = list(pyabf.waveform.EpochTable(x, c) for c in x.channelList)
                else:
                    etables = list(filter(lambda e: len(e.epochs) > 0, (pyabf.waveform.EpochTable(x, c) for c in x.channelList)))
                
            if as_dataFrame:
                etables = [epochTable2DF(e, x) for e in etables]
                
            sweepTables.append(etables)
            
    return sweepTables
    
#     if as_dataFrame:
#         return list(epochTable2DF(e, x) for e in etables)
#     
#     return etables
    # return [e for e in etables if len(e.epochs)]

def epochTable2DF(x:pyabf.waveform.EpochTable, abf:typing.Optional[pyabf.ABF] = None):
    """Returns a pandas.DataFrame with the data from the epoch table 'x'
    """
    if not isinstance(x, pyabf.waveform.EpochTable):
        raise TypeError(f"Expecting an EpochTable; got {type(x).__name__} instead")

    # NOTE: 2022-03-04 15:38:31
    # code below adapted from pyabf.waveform.EpochTable.text
    #
    
    rowIndex = ["Type", "First Level", "Delta Level", "First Duration (points)", "Delta Duration (points)",
                "First duration (ms)", "Delta Duration (ms)",
                "Digital Pattern #3-0", "Digital Pattern #7-4", "Train Period (points)", "Pulse Width (points)",
                "Train Period (ms)", "Pulse Width (ms)"]
    
    # prepare lists to hold values for each epoch
    
    # NOTE: 2022-03-04 16:05:20 
    # skip "Off" epochs
    epochs = [e for e in x.epochs if e.epochTypeStr != "Off"]
    
    if len(epochs):
        epochCount = len(epochs)
        epochLetters = [''] * epochCount
        
        epochData = dict()
        
        for i, epoch in enumerate(epochs):
            assert isinstance(epoch, pyabf.waveform.Epoch)
            
            if isinstance(abf, pyabf.ABF):
                adcName, adcUnits = abf._getAdcNameAndUnits(x.channel)
                dacName, dacUnits = abf._getDacNameAndUnits(x.channel)
                
            else:
                adcName = adcUnits = dacName = dacUnits = None
                
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
        # sweepCount        → ["lActualEpisodes"]
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
    
    assert abf_version == fileSigVersion, "Mismatch between reported ABF versions; check obejct's annotattions properties"
    
    fFileVersionNumber = obj.annotations.get("fFileVersionNumber", None)
    
    assert isinstance(fFileVersionNumber, float), "Object does not seem to be created from an ABF file"
    
    fileVersionMajor = int(fFileVersionNumber)
    
    assert abf_version == fileVersionMajor, "Mismatch between reported ABF versions; check obejct's annotattions properties"
    
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
    
    
        
    
    
        
