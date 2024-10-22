# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

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

epoch.type = annotations["dictEpochInfoPerDAC"][0][0]["nEpochType"]

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
    

NOTE:

Typical mapping of outputs & inputs in pClamp (NOTE: these must be configured in
the "LabBench" in the Clampex software)

Amplifier 

Inputs (ADC)                                    | Outputs (DAC)         
-------------------------------------------------------------------------------------------
# |    Name (aliases)   | Amplifier output      | # |   Name (aliases)  | Amplifier input
-------------------------------------------------------------------------------------------
0 | Im_prim_0 Vm_prim_0 | Channel 0 primary     | 0 | V/I_Clamp_0       | Channel 0 command
1 | Vm_sec_0  Im_sec_0  | Channel 0 secondary   | 0 |                   | Channel 0 command
                          (if available)
-------------------------------------------------------------------------------------------
These are available only for dual-channel amplifiers (e.g. MultiClamp)
2 |                     | Channel 1 primary     | 1 | V/I_Clamp_1       | Channel 1 command
3 |                     | Channel 1 secondary   | 1 |                   | Channel 1 command
-------------------------------------------------------------------------------------------
From here onwards, any signal source can be input into the ADCs below; for example,
one may feed a branch of a digital output (from either the DAQ board or some other 
device such as an image acquisition workstation - e.g. linescan TTLs or frame TTLs)
 - or an analog signal (e.g. from a temperature sensor, etc) into one of these.
4 |                                             
5 |                                                 
6 |
7 |

"""
import typing, struct, inspect, itertools, functools, warnings, pathlib
from functools import singledispatch, partial
import numpy as np
import pandas as pd
import quantities as pq
import neo
from dataclasses import MISSING

from core import quantities as scq
from core import datatypes, strutils, utilities
from core.triggerevent import (TriggerEvent, TriggerEventType)
from core.triggerprotocols import TriggerProtocol
from core.prog import scipywarn
from ephys.ephys_protocol import ElectrophysiologyProtocol
from core.neoutils import getAcquisitionInfo
import pyabf
from pyabf.abf1.headerV1 import HeaderV1
from pyabf.abf2.headerV2 import HeaderV2
from pyabf.abf2.section import Section
from pyabf.abfReader import AbfReader
from pyabf.stimulus import (findStimulusWaveformFile, 
                            stimulusWaveformFromFile)

from iolib import h5io
import h5py

# useful alias:
ABF = pyabf.ABF

# This is 8 for DigiData 1550 series, and 4 for DigiData 1440 series
DIGITAL_OUTPUT_COUNT = pyabf.waveform._DIGITAL_OUTPUT_COUNT # 8

# These two will be (properly) redefined further below
class ABFOutputConfiguration:   # placeholder to allow the definition of ABFProtocol, below
    pass
class ABFInputConfiguration:   # placeholder to allow the definition of ABFProtocol, below
    pass                         # will be (properly) redefined further below

class ABFAcquisitionMode(datatypes.TypeEnum):
    """Corresponds to nOperationMode in ABF._protocolSection and annotations"""
    variable_length_event = 1
    fixed_length_event = 2
    gap_free = 3
    high_speed_oscilloscope = 4 # Not supported by neo, but supported by pyabf!
    episodic_stimulation = 5
    
class ABFAveragingMode(datatypes.TypeEnum):
    """Corresponds to nAverageAlgorithm in ABF._protocolSection"""
    cumulative = 0
    most_recent = 1
    
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
    def __init__(self, epochNumber:int = -1, epochType: ABFEpochType = ABFEpochType.Unknown,
                 level: typing.Optional[pq.Quantity]=None,
                 levelDelta: typing.Optional[pq.Quantity] = None,
                 duration: pq.Quantity = 0 * pq.ms,
                 durationDelta: pq.Quantity = 0* pq.ms,
                 mainDigitalPattern: typing.Sequence = (tuple(), tuple()),
                 alternateDigitalPattern: typing.Sequence = (tuple(), tuple()),
                 useAltPattern: bool=False,
                 altDIGOutState: bool = False,
                 pulsePeriod: pq.Quantity = np.nan * pq.ms,
                 pulseWidth: pq.Quantity = np.nan * pq.ms,
                 dacNum: int = -1):
        self._epochNumber_ = epochNumber
        self._epochType_ = epochType
        self._level_ = level # -1 * pq.dimensionless
        self._levelDelta_ = levelDelta # -1 * pq.dimensionless
        self._duration_ = duration
        self._durationDelta_ = durationDelta
        self._mainDigitalPattern_ = mainDigitalPattern
        self._alternateDigitalPattern_ = alternateDigitalPattern
        self._useAltPattern_ = useAltPattern
        self._altDIGOutState_ = altDIGOutState
        self._pulsePeriod_ = pulsePeriod
        self._pulseWidth_ = pulseWidth
        self._dacNum_ = dacNum
        
    @classmethod
    def _check_dig_pattern_args_(cls, val):
        if isinstance(val, str):
            # eval it then keep fingers crossed
            try:
                val = eval(val)
            except:
                traceback.print_exc()
                return (tuple(), tuple())
                
        if isinstance(val, (tuple, list)) and all(isinstance(x, (tuple, list)) and all(isinstance(v, (int, str)) for v in x) for x in val):
            return tuple(tuple(x) for x in val)

        return (tuple(), tuple())
        
    def toHDF5(self, group, name, oname, compression, chunks, track_order,
                       entity_cache) -> h5py.Dataset:
        # print(f"{self.__class__.__name__}.toHDF5: group = {group}, name = {name}, oname = {oname}")
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity
        
        # TODO: 2024-07-17 15:49:20
        # parse relevant ABFEpoch attributes into obj_attrs
        # make sure you take h5io.fromHDF5 into account
        #
        attrs = list(filter(lambda x: not x[0].startswith("_") and x[1].fset, 
                            inspect.getmembers_static(self, inspect.isdatadescriptor)))
        
        objattrs = h5io.makeAttrDict(**dict(map(lambda x: (x[0], getattr(self, x[0])), attrs)))
        obj_attrs.update(objattrs)
        # if isinstance(name, str) and len(name.strip()):
        #     target_name = name
            
        entity = group.create_dataset(name, data = h5py.Empty("f"), 
                                      track_order = track_order)
        entity.attrs.update(obj_attrs)
        h5io.storeEntityInCache(entity_cache, self, entity)
        
        return entity
    
    @classmethod
    def fromHDF5(cls, entity:h5py.Dataset, 
                             attrs:typing.Optional[dict]=None, cache:dict = {}):
        # print(f"{cls.__name__}.fromHDF5 entity: {type(entity).__name__}")
        if entity in cache:
            return cache[entity]
        
        # if attrs is None:
        attrs = h5io.attrs2dict(entity.attrs)
        # print(f"\tattrs = {attrs}")
        
        epochNumber = attrs.get("epochNumber", None)
        epochType = attrs.get("type", ABFEpochType.Unknown)
        if isinstance(epochType, np.int64):
            epochType = int(epochType)
            
        if isinstance(epochType, int):
            if epochType not in (ABFEpochType.values()):
                epochType = ABFEpochType.Unknown
            else:
                epochType = ABFEpochType(epochType)
                
        firstLevel = attrs.get("firstLevel",None)
        deltaLevel = attrs.get("deltaLevel", None)
        firstDuration = attrs.get("firstDuration", None)
        if firstDuration is None:
            firstDuration = 0*pq.ms
        deltaDuration = attrs.get("deltaDuration", None)
        if deltaDuration is None:
            deltaDuration = 0*pq.ms
            
        # BUG 2024-07-19 23:25:20 
        # reconstitution of the digital patterns from json doesn't work well
        # they're stored as strings so we need to eval them
        #
        # NOTE: 2024-07-19 23:35:19 fixed in class method _check_dig_pattern_args_(…)
        
        mainDigitalPattern = cls._check_dig_pattern_args_(attrs["mainDigitalPattern"])
        # print(f"\tmainDigitalPattern = {mainDigitalPattern} ({type(mainDigitalPattern).__name__})")
        
        alternateDigitalPattern = cls._check_dig_pattern_args_(attrs["alternateDigitalPattern"])
        # print(f"\talternateDigitalPattern = {alternateDigitalPattern} ({type(alternateDigitalPattern).__name__})")
        useAltPattern = attrs.get("useAltPattern", None)
        altDIGOutState = attrs.get("altDIGOutState", None)
        pulsePeriod = attrs.get("pulsePeriod", None)
        pulseWidth = attrs.get("pulseWidth", None)
        dacNum = attrs.get("dacNum", None)
        
        return cls(epochNumber, epochType, firstLevel, deltaLevel, 
                   firstDuration, deltaDuration, 
                   mainDigitalPattern, alternateDigitalPattern, useAltPattern, altDIGOutState,
                   pulsePeriod, pulseWidth, dacNum)
        
    def __repr__(self) -> str:
        return f"{self.__class__.__name__} ({super().__repr__()}) Epoch {self.epochNumber} (\'{self.letter}\'), type: {self.epochType.name}"
        
        
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        
        properties = inspect.getmembers_static(self, lambda x: isinstance(x, property))
        return all(getattr(self, p[0])==getattr(other, p[0]) for p in properties)
        
        # return all(np.all( utilities.safe_identity_test(getattr(self, p[0]), getattr(other, p[0])) ) for p in properties)
        
    def is_identical_except_digital(self, other):
        if not isinstance(other, self.__class__):
            return False
        
        properties = inspect.getmembers_static(self, lambda x: isinstance(x, property))
        
        return all(np.all(utilities.safe_identity_test(getattr(self, p[0]), getattr(other, p[0]), idcheck=False)) for p in properties if p[0] not in ("mainDigitalPattern", "alternateDigitalPattern"))
        # return all(np.all(getattr(self, p[0]) == getattr(other, p[0])) for p in properties if p[0] not in ("mainDigitalPattern", "alternateDigitalPattern"))
        
    @property
    def letter(self) -> str:
        """Epoch's letter in the epochs index.
        E.g., 'A', 'B', etc"""
        return getEpochLetter(self.number)
    
    @property
    def number(self) -> int:
        """Alias to self.index"""
        return self._epochNumber_
    
    @property
    def index(self) -> int:
        """Index of thsi epochs in the Epochs table"""
        return self._epochNumber_
    
    @number.setter
    def number(self, val:int):
        self._epochNumber_ = val
        
    @property
    def epochNumber(self) -> int:
        """Alias to self.number for backward compatibility"""
        return self.number
    
    @epochNumber.setter
    def epochNumber(self, val):
        self.number = val
        
    @property
    def epochType(self) -> ABFEpochType:
        """Alias to self.type"""
        return self._epochType_
    
    @property
    def emulatesTTL(self) -> bool:
        """True when epoch type is ABFEpochType.Pulse and meets the conditions below:
        • First level       != 0
        • Delta level       == 0
        • Delta duration    == 0
        • all digital outputs are zero
        First duration, train rate and pulse duration are all > 0 (enforced by Clampex)
        """
        
        return self.epochType == ABFEpochType.Pulse and self.firstLevel != 0 and \
            self.deltaLevel == 0 and self.deltaDuration == 0 and not self.hasDigitalOutput("any", "alt")
    
    @property
    def type(self) -> ABFEpochType:
        return self._epochType_
    
    @type.setter
    def type(self, val:typing.Union[ABFEpochType, str, int]):
        
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
        return self.type.name
    
    @property
    def firstLevel(self) -> pq.Quantity:
        return self._level_
    
    @firstLevel.setter
    def firstLevel(self, val:typing.Optional[pq.Quantity] = None):
        if isinstance(val, pq.Quantity):
            assert (scq.checkElectricalCurrentUnits(val) or scq.checkElectricalPotentialUnits(val)), f"Expecting a quantity in A or V; instead, got {val}"
            
        else:
            self._levelDelta_ = None
            
        self._level_ = val
        
    @property
    def deltaLevel(self) -> pq.Quantity:
        return self._levelDelta_
    
    @deltaLevel.setter
    def deltaLevel(self, val:typing.Optional[pq.Quantity]= None):
        if isinstance(val, pq.Quantity):
            assert (scq.checkElectricalCurrentUnits(val) or scq.checkElectricalPotentialUnits(val)), f"Expecting a quantity in A or V; instead, got {val}"
            if self.firstLevel is None:
                raise RuntimeError("'firstLevel' property must be set before 'deltaLevel'")
            else:
                assert scq.unitsConvertible(self._level_, val), f"Value units ({val.units}) are incompaibl with firstLevel units ({self._level_.units})"
        
        self._levelDelta_ = val
        
    @property
    def firstDuration(self):
        return self._duration_
    
    @firstDuration.setter
    def firstDuration(self, val:pq.Quantity):
        assert isinstance(val, pq.Quantity) and scq.checkTimeUnits(val), f"{val} is not a time quantity"
        self._duration_ = val
        
    @property
    def deltaDuration(self):
        return self._durationDelta_
    
    @deltaDuration.setter
    def deltaDuration(self, val):
        assert isinstance(val, pq.Quantity) and scq.checkTimeUnits(val), f"{val} is not a time quantity"
        self._durationDelta_ = val
    
    @property
    def pulsePeriod(self):
        return self._pulsePeriod_
    
    @pulsePeriod.setter
    def pulsePeriod(self, val):
        assert isinstance(val, pq.Quantity) and scq.checkTimeUnits(val), f"{val} is not a time quantity"
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
        assert isinstance(val, pq.Quantity) and scq.checkTimeUnits(val), f"{val} is not a time quantity"
        self._pulseWidth_ = val
        
    @property
    def mainDigitalPattern(self) -> tuple:
        return self._mainDigitalPattern_
    
    @mainDigitalPattern.setter
    def mainDigitalPattern(self, val:tuple):
        # TODO: 2023-09-14 15:55:11
        # check the argument
        self._mainDigitalPattern_ = self._check_dig_pattern_args_(val)
        
    @property
    def useAltPattern(self) -> bool:
        return self._useAltPattern_
    
    @useAltPattern.setter
    def useAltPattern(self, val:bool):
        self._useAltPattern_ = vall==True
        
    @property
    def altDIGOutState(self) -> bool:
        return self._altDIGOutState_
    
    @altDIGOutState.setter
    def altDIGOutState(selv, val:bool):
        self._altDIGOutState_ = val == True
        
    @property
    def alternateDigitalPattern(self) -> tuple:
        return self._alternateDigitalPattern_
    
    @alternateDigitalPattern.setter
    def alternateDigitalPattern(self, val:tuple):
        # TODO: 2023-09-14 15:55:58
        # check the argument
        self._alternateDigitalPattern_ = self._check_dig_pattern_args_(val)
        
    def getDigitalPattern(self, alternate:bool=False) -> tuple:
        return self.alternateDigitalPattern if alternate else self.mainDigitalPattern
    
    def getUsedDigitalOutputChannels(self, alternate:typing.Optional[bool]=None,
                                  trains:typing.Optional[bool] = None) -> list:
        """Indices of DIG channels that emit TTL trains OR TTL pulses
        
        For a more specific query (i.e. pulse v train output) see
        getPulseDigitalOutputChannels and getTrainDigitalOutputChannels.
        
        Parameters:
        ===========
        alternate: default is None: 
        
            When None, returns a list of all digital output indices
            used in this epoch.
        
            When False, returns the indices of the digital output channels
            used for the main pattern.
    
            When True, returns the indices of the digital output channels
            used for the alternate pattern.
        
            When None, the only accepted value is "all". In this case, the function
            return a list of digital channel indices used in both main and alternate patterns
            (WARNING: these are not necessarily unique)
        
            This is useful to test if there is the epochs associates any digital
            output at all.
            
            Another possible test, specific for a digial channel is the
            'hasDigital...' family of methods.
    
        
        """
        if isinstance(alternate, bool):
            p = self.getDigitalPattern(alternate)
            
            # if isinstance(trains, str) and trains.lower() == "all":
            if trains is None:
                return list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(p[k]), 
                                                                    filter(lambda i: i[1] != 0, 
                                                                        enumerate(reversed(p[k]))))) for k in range(len(p))]))
            elif isinstance(trains, bool):
                val = "*" if trains else 1
                return list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(p[k]), 
                                                                    filter(lambda i: i[1] == val, 
                                                                        enumerate(reversed(p[k]))))) for k in range(len(p))]))
            else:
                raise ValueError(f"'trains' expected to be a bool or None; instead, got {trains}")
            
        # elif isinstance(alternate, str) and alternate.lower() == "all":
        elif alternate is None or (isinstance(alternate, str) and alternate.lower() == "all"):
            p = self.getDigitalPattern(False)
            pa = self.getDigitalPattern(True)
            
            # if isinstance(trains, str) and trains.lower() == "all":
            if trains is None:
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
                raise ValueError(f"'trains' expected to be a bool or None; instead, got {trains}")
            
        else:
            raise ValueError(f"Invalid 'alternate' specification {alternate}; expecting a bool or None")
            
        
    def getPulseDigitalOutputChannels(self, alternate:typing.Union[bool, str]=False) -> list:
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
            p = self.getDigitalPattern(alternate)
            return list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(p[k]), 
                                                                filter(lambda i: i[1] == 1, 
                                                                       enumerate(reversed(p[k]))))) for k in range(len(p))]))
        
        elif isinstance(alternate, str) and alternate.lower() == "all":
            p = self.getDigitalPattern(False)
            pa = self.getDigitalPattern(True)
            return list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(p[k]), 
                                                                filter(lambda i: i[1] == 1, 
                                                                       enumerate(reversed(p[k]))))) for k in range(len(p))])) \
                   + list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(pa[k]), 
                                                                 filter(lambda i: i[1] == 1, 
                                                                        enumerate(reversed(pa[k]))))) for k in range(len(pa))]))
        else:
            raise ValueError(f"Invalid 'alternate' specification {alternate}")
            
    def getTrainDigitalOutputChannels(self, alternate:typing.Union[bool, str]=False) -> list:
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
            p = self.getDigitalPattern(alternate)
            return list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(p[k]), filter(lambda i: i[1] == '*', enumerate(reversed(p[k]))))) for k in range(len(p))]))

        elif isinstance(alternate, str) and alternate.lower() == "all":
            p = self.getDigitalPattern(False)
            pa = self.getDigitalPattern(True)
            return list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(p[k]), 
                                                                filter(lambda i: i[1] == '*', 
                                                                       enumerate(reversed(p[k]))))) for k in range(len(p))])) \
                   + list(itertools.chain.from_iterable([list(map(lambda v: v[0] + k * len(pa[k]), 
                                                                 filter(lambda i: i[1] == '*', 
                                                                        enumerate(reversed(pa[k]))))) for k in range(len(pa))]))

        else:
            raise ValueError(f"Invalid 'alternate' specification {alternate}")
        
    
    def hasDigitalOutput(self, digChannel: typing.Union[int, str] = 0, 
                         alternate:typing.Union[bool, str]=False) -> bool:
        """
        Checks the epochs defines an output on the specified digital channel.
        
        For a more atomic test, see self.hasDigitalPulse and self.hasDigitalTrain.
        
        This is useful to determine if the Pulse... properties of the epoch are
        related to any digital pattern defined in the epoch, or just to the 
        associated DAC waveform.
        
        Parameters:
        ===========
        digChannel: int in the range(8) (maximum number of digital channels)
                    or the string "any" -> returns True if ANY of the digital
                    channels is emitting a train or a pulse
        
        alternate: bool, default False; when True, the function will test the 
                    alternate digital pattern
        
                    str ("all") the function will test if the epochs emits a
                    digital pattern at all
                
        
        
        """
        if isinstance(alternate, bool):
            p = self.getDigitalPattern(alternate)
            
            if isinstance(digChannel, int):
                if digChannel in range(len(p[0])):
                    return p[0][-digChannel-1] != 0
                
                elif len(p) == 2 and digChannel in range(len(p[0]), len(p[1])):
                    return p[1][-len(p[0])+digChannel-1] != 0
                
                else:
                    return False
                
            elif isinstance(digChannel, str) and digChannel.lower() == "any":
                return any(v != 0 for v in itertools.chain.from_iterable(p))
            
        elif isinstance(alternate, str):
            if alternate.lower() == "all":
                p = self.getDigitalPattern(False)
                pa = self.getDigitalPattern(True)
                
                if isinstance(digChannel, int):
                    if digChannel in range(len(p[0])):
                        return p[0][-digChannel-1] != 0 or pa[0][-digChannel-1] != 0
                    
                    elif len(p) == 2 and digChannel in range(len(p[0]), len(p[1])):
                        return p[1][-digChannel-1] != 0 or pa[1][-digChannel-1] != 0
                    
                    else:
                        return False
                        
                elif isinstance(digChannel, str) and digChannel.lower() == "any":
                    return any(v != 0 for v in itertools.chain.from_iterable(p+pa))
                
            elif alternate.lower() in ("main", "alt"):
                alt = alternate.lower() == "alt"
                p = self.getDigitalPattern(alternate)
                if isinstance(digChannel, int):
                    if digChannel in range(len(p[0])):
                        return p[0][-digChannel-1] != 0
                    
                    elif len(p) == 2 and digChannel in range(len(p[0]), len(p[1])):
                        return p[1][-digChannel-1] != 0
                    
                    else:
                        return False
                        
                elif isinstance(digChannel, str) and digChannel.lower() == "any":
                    return any(v != 0 for v in itertools.chain.from_iterable(p))
                
    def hasDigitalPulse(self, digChannel:int = 0, alternate:bool=False) -> bool:
        """
        Checks if there is a pulse output (1) on the specified digital channel
        
        Parameters:
        ===========
        digChannel: int in the range(8) (maximum number of digital channels)
        alternate: when True, the function will test the alternate digital pattern
        
        """
        p = tuple(itertools.chain.from_iterable(map(lambda x: reversed(x), self.getDigitalPattern(alternate))))

        if digChannel in range(len(p)):
            return p[digChannel] == 1
        
        return False
        
    def hasDigitalTrain(self, digChannel:int = 0, alternate:bool=False) -> bool:
        """
        Returns if there is a train output ('*') on the specified digital channel
        
        Parameters:
        ===========
        digChannel: int in the range(8) (maximum number of digital channels)
        alternate: when True, the function will test the alternate digital pattern
        
        """
        p = tuple(itertools.chain.from_iterable(map(lambda x: reversed(x), self.getDigitalPattern(alternate))))
        
        if digChannel in range(len(p)):
            return p[digChannel] == '*'
        
        return False
        
    @property
    def digitalOutputChannels(self):
        """Returns a dictionary mapping key:int ↦ nested dict, where
            key = index of digital channel used (0-7)
            nested dict: a mapping of key:str ↦ 2-tuple[bool] as follows
            "pulse" ↦ pulse emission in (main, alternate) pattern
            "train" ↦ train emission in (main, alternate) pattern
        
        This mapping is empty if the epoch does not emit any digital signal.
        
        See also:
        self.hasDigitalPulse
        self.hasDigitalTrain
        self.hasDigitalOutput
        self.getPulseDigitalOutputChannels
        self.getTrainDigitalOutputChannels
        selg.getDigitalPattern
        
        """
        return dict((channel, {"pulse": (self.hasDigitalPulse(channel, False), self.hasDigitalPulse(channel, True)),
                               "train": (self.hasDigitalTrain(channel, False), self.hasDigitalTrain(channel, True))}) for channel in self.getUsedDigitalOutputChannels())
        

class ABFProtocol(ElectrophysiologyProtocol):
    """Instance of an ABF protocol (for Clampex v ≥ 10).
    Particularities:
        • When "Alternative Waveforms" is enabled, only TWO DACs will emit analog
        waveforms, on alternative sweeps ()
    """
    # TODO 2024-07-19 13:19:40 FIXME URGENTLY
    # implement code related to pyabf stimulusFilefolder & stimulusWaveformFromFile
    # 
    from ephys.ephys import SynapticPathway
    from ephys.ephys import ClampMode
    
    def __init__(self, obj:typing.Optional[typing.Union[pyabf.ABF,neo.Block]]=None,
                 **kwargs):
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
            
            # NOTE: 2024-03-08 22:32:29
            # this below returns a tuple - not what we want
            # self._acquisitionMode_ = ABFAcquisitionMode.namevalue(obj.nOperationMode)
            self._acquisitionMode_ = ABFAcquisitionMode(obj.nOperationMode)
            self._nSweeps_ = obj._protocolSection.lEpisodesPerRun
            self._nRuns_   = obj._protocolSection.lRunsPerTrial
            self._nTrials_ = obj._protocolSection.lNumberOfTrials
            self._nTotalDataPoints_ = obj._dataSection._entryCount
            self._nDataPointsPerSweep_ = obj.sweepPointCount
            self._samplingRate_ = float(obj.dataRate) * pq.Hz
            self._sweepInterval_ = obj._protocolSection.fEpisodeStartToStart * pq.s
            self._averaging_ = ABFAveragingMode(obj._protocolSection.nAverageAlgorithm) # 0 = Cumulative; 1 = Most recent
            self._averageWeighting_ =  obj._protocolSection.fAverageWeighting
            
            self._protocolFile_ = obj.protocolPath # store this for future reference
            
            self._sourceHash_ = hash(obj)
            self._sourceId_ = id(obj)
            self._fileOrigin_ = obj.abfFilePath
            
            self._inputs_ = [ABFInputConfiguration(obj, self, k) for k in range(self._nADCChannels_)]
            self._outputs_ = [ABFOutputConfiguration(obj, self, k) for k in range(self._nDACChannels_)]
                
        elif isinstance(obj, neo.Block):
            assert sourcedFromABF(obj), "Object does not appear to be sourced from an ABF file"
            info_dict = getAcquisitionInfo(obj)
                
            if info_dict["lActualEpisodes"] != info_dict["protocol"]["lEpisodesPerRun"]:
                scipywarn(f"In {obj.name}: Mismatch between lActualEpisodes ({info_dict['lActualEpisodes']}) and lEpisodesPerRun ({info_dict['protocol']['lEpisodesPerRun']})")
            
            # ### BEGIN ADC inputs information
            # NOTE: further info in self._inputs_
            self._nADCChannels_ = info_dict["sections"]["ADCSection"]["llNumEntries"]
            # ### END   ADC inputs information
            
            # ### BEGIN DAC outputs information
            # NOTE: further info in self._outputs_
            self._nDACChannels_ = info_dict["sections"]["DACSection"]["llNumEntries"]
            self._activeDACChannel_ = info_dict["protocol"]["nActiveDACChannel"]
            self._hasAltDacOutState_ = bool(info_dict["protocol"]["nAlternateDACOutputState"])
            # ### END   DAC outputs information
            
            # ### BEGIN digital outputs information
            # NOTE: further info indirectly via self._outputs_
            self._nDigitalOutputs_ = info_dict["sections"]["DACSection"]["llNumEntries"]
            self._nTotalDigitalOutputs_ = info_dict["protocol"]["nDigitizerTotalDigitalOuts"]
            self._nSynchronizedDigitalOutputs_ = info_dict["protocol"]["nDigitizerSynchDigitalOuts"]
            self._hasAltDigOutState_ = bool(info_dict["protocol"]["nAlternateDigitalOutputState"])
            self._digTrainActiveHi_ = bool(info_dict["protocol"]["nDigitalTrainActiveLogic"])
            self._digHolding_ = info_dict["protocol"]["nDigitalHolding"]
    
            # allow the use of blocks read from ABF before 2023-09-20 23:26:08
            digHolds = info_dict["sections"]["EpochSection"].get("nEpochDigitalOutput", None) # 3,2,1,0,7,6,5,4
    
            if isinstance(digHolds, list) and len(digHolds) == self._nDigitalOutputs_:
                digHolds = list(map(bool, digHolds))
                if self._nDigitalOutputs_ == 8:
                    digHolds = list(reversed(digHolds[:4])) + list(reversed(digHolds[4:]))
                    
                else:
                    digHolds = list(reversed(digHolds))
                    
                self._digHoldingValue_ = digHolds
                
            else:
                self._digHoldingValue_ = [False] * self._nDigitalOutputs_
                
            self._digUseLastEpochHolding_ = bool(info_dict["protocol"]["nDigitalInterEpisode"])
            # ### END   digital outputs information
            
            # NOTE: 2024-03-08 22:33:34 see NOTE: 2024-03-08 22:32:29
            # self._acquisitionMode_ = ABFAcquisitionMode.type(info_dict["protocol"]["nOperationMode"])
            self._acquisitionMode_ = ABFAcquisitionMode(info_dict["protocol"]["nOperationMode"])
            self._nSweeps_ = info_dict["protocol"]["lEpisodesPerRun"]
            self._nRuns_   = info_dict["protocol"]["lRunsPerTrial"]
            self._nTrials_ = info_dict["protocol"]["lNumberOfTrials"]
            self._nTotalDataPoints_ = info_dict["sections"]["DataSection"]["llNumEntries"]
            self._nDataPointsPerSweep_ = int(self._nTotalDataPoints_/self._nSweeps_/self._nADCChannels_)
            self._samplingRate_ = float(info_dict["sampling_rate"]) * pq.Hz
            self._sweepInterval_ = info_dict["protocol"]["fEpisodeStartToStart"] * pq.s
            self._averaging_ = ABFAveragingMode(info_dict["protocol"]["nAverageAlgorithm"]) # 0 = Cumulative; 1 = Most recent
            self._averageWeighting_ =  info_dict["protocol"]["fAverageWeighting"] 
            
            self._protocolFile_ = info_dict["sProtocolPath"].decode()

            self._sourceHash_ = hash(obj)
            self._sourceId_ = id(obj)
            self._fileOrigin_ = obj.file_origin
        
            self._inputs_ = [ABFInputConfiguration(obj, self, k) for k in range(self._nADCChannels_)]
            self._outputs_ = [ABFOutputConfiguration(obj, self, k) for k in range(self._nDACChannels_)]
                
        else:
            if len(kwargs) == 0:
                raise TypeError(f"A source pyabf.ABF or neo.Block object was not specified; instead, got {type(obj).__name__}; in addition, no other parameters were given, therefore cannot initialize a {self.__class__.__name__} object")
            
            adcChannels = kwargs.get("inputs", list())
            dacChannels = kwargs.get("outputs", list())
            self._nADCChannels_ = len(adcChannels)
            self._nDACChannels_ = len(dacChannels)
            self._activeDACChannel_ = kwargs.get("activeDACChannel", 0)
            self._hasAltDacOutState_ = kwargs.get("hasAltDacOutState", False)
            
            self._nDigitalOutputs_ = kwargs.get("nDigitalOutputs", 0)
            self._nTotalDigitalOutputs_ = kwargs.get("nTotalDigitalOutputs", 0)
            self._nSynchronizedDigitalOutputs_ = kwargs.get("nSynchronizedDigitalOutputs", 0)
            self._hasAltDigOutState_ = kwargs.get("hasAltDigOutState", False)
            self._digTrainActiveHi_ = kwargs.get("digTrainActiveHi", True)
            self._digHolding_ = kwargs.get("digHolding", 0)
            self._digHoldingValue_ = kwargs.get("digHoldingValue", list())
            self._digUseLastEpochHolding_ = kwargs.get("digUseLastEpochHolding", False)
            acqMode = kwargs.get("acquisitionMode", ABFAcquisitionMode.episodic_stimulation)
            if isinstance(acqMode, int) and acqMode in ABFAcquisitionMode.values():
                self._acquisitionMode_ = ABFAcquisitionMode(acqMode)
            elif isinstance(acqMode, ABFAcquisitionMode):
                self._acquisitionMode_ = acqMode
            else:
                self._acquisitionMode_ = ABFAcquisitionMode.episodic_stimulation
                
            self._nSweeps_ = kwargs.get("nSweeps", 0)
            self._nRuns_ = kwargs.get("nRuns", 0)
            self._nTrials_ = kwargs.get("nTrials", 0)
            self._nTotalDataPoints_ = kwargs.get("nTotalDataPoints", 0)
            self._nDataPointsPerSweep_ = kwargs.get("nDataPointsPerSweep", 0)
            self._samplingRate_ = kwargs.get("samplingRate", 0* pq.Hz)
            self._sweepInterval_ = kwargs.get("sweepInterval", 0*pq.s)
            averaging = kwargs.get("averaging", ABFAveragingMode.cumulative)
            if isinstance(averaging, int) and averaging in ABFAveragingMode.values():
                self._averaging_ = ABFAveragingMode(averaging)
            elif isinstance(averaging, ABFAveragingMode):
                self._averaging_ = averaging
            else:
                self._averaging_ = ABFAveragingMode.cumulative
            self._averageWeighting_ = kwargs.get("averageWeighting", 1.0)
            self._protocolFile_ = kwargs.get("protocolFile", MISSING)
            self._sourceHash_ = kwargs.get("sourceHash", MISSING)
            self._sourceId_ = kwargs.get("sourceID", MISSING)
            self._fileOrigin_ = kwargs.get("fileOrigin", MISSING)
            
            self._inputs_ = [i for i in kwargs.get("inputs", list()) if isinstance(i, ABFInputConfiguration)]
            self._outputs_ = [i for i in kwargs.get("outputs", list()) if isinstance(i, ABFOutputConfiguration)]
        
        # NOTE: 2024-07-19 13:43:00
        # All attributes below are calculated from what h been set up so far
        #
        
        # since Clampex only runs on Windows, we simply split the string up:
        if isinstance(self._protocolFile_, str) and len(self._protocolFile_.strip()):
            self._name_ = pathlib.Path(self._protocolFile_.split("\\")[-1]).stem  # strip off the extension
        self._sweepDuration_ = (self._nDataPointsPerSweep_ / self._samplingRate_).rescale(pq.s)
        self._totalDuration_ = self._nSweeps_ * (self._sweepDuration_ if self._sweepInterval_ == 0*pq.s else self._sweepInterval_)
        if self._nSweeps_ > 1:
            self._totalDuration_ += self._sweepDuration_
            
        self._nAlternateDigitalOutputs = self._nTotalDigitalOutputs_ - self._nSynchronizedDigitalOutputs_
        self._nDataPointsHolding_ = int(self._nDataPointsPerSweep_/64)
        
    def __repr__(self):
        ret = [f"{self.__class__.__name__} ({super().__repr__()}) with:"]
        ret.append(f"{self.nADCChannels} ADCs:")
        ret += [f"  {o.physicalIndex}: {o.__repr__()}" for o in self.ADCs]
        ret.append(f"{self.nDACChannels} DACs:")
        for o in self.DACs:
            nEpochs = len(o.epochs)
            ret.append(f"  {o.physicalIndex}: {o.__repr__()} with {nEpochs} epochs{' ' if nEpochs ==0 else ':'}")
            for e in o.epochs:
                ret.append(f"    {e.__repr__()}")
            
        # ret += [o.__repr__() for o in self.DACs]
        ret.append(f"• {self.nDigitalOutputs} Digital outputs ")
        # ret.append(f" ∘ {self.nSychronizedDigitalOutChannels} synchronized digital channels")
        # ret.append(f" ∘ {self.nAlternateDigitalOutChannels} alternate digital channels ")
        ret.append(f" ∘ Digital train active logic High: {self.digitalTrainActiveLogic}")
        ret.append(f" ∘ Digital holding {self.digitalHolding}, ; using last epoch holding: {self.digitalUseLastEpochHolding} ")
        ret.append(f"• Acquisition mode: {self.acquisitionMode.name}")
        ret.append(f"• Trials: {self.nTrials}")
        ret.append(f"• Runs/trial: {self.nRuns}")
        ret.append(f"• Sweeps/run: {self.nSweeps}")
        ret.append(f"• Sampling rate: {self.samplingRate}")
        ret.append(f"• Averaging: {self.averaging.name}")
        ret.append(f"• Name: {self.name}")
        ret.append(f"• File: {self.protocolFile}")
        return "\n".join(ret)
    
    def __eq__(self, other):
        """Tests for equality of scalar properties and epochs tables.
        Epochs tables are checked for equality sweep by sweep, in all channels.
        
        WARNING: This includes any digital output patterns definded.
        
        If this is not intended, then use self.is_identical_except_digital(other).
        
        ATTENTION: For comparison and inclusion test purposes, this function 
        deliberately does not compare object id values (i.e. their memory 
        addresses). Instead, it compares the value of the relevant object 
        attributes (numbers and strings). Two protocol objects can have identical 
        parameter values, and yet be digitally distinct (i.e., stored at different
        memory locations).
        """
        if not isinstance(other, self.__class__):
            return False
        
        properties = inspect.getmembers_static(self, lambda x: isinstance(x, property))
        
        # selfProp = getattr(self, p[0])
        # otherProp = getattr(other, p[0])
        
        #  NOTE: 2024-10-01 19:17:40
        # ths below suffers from the fact that the == operator checks the IDs
        # I guess e need to override that in the appropriate classes
        # check equality of properties (descriptors); this includes nSweeps and nADCChannels
        ret = all(np.all(getattr(self, p[0]) == getattr(other, p[0])) for p in properties)

        # if checked out then verify all epochs Tables are sweep by sweep 
        # identical in all DAC channels, including digital output patterns!
        if ret:
            for k in range(self.nDACChannels):
                # NOTE: 2023-11-05 21:06:10
                # Return after first iteration showing distinct DACs
                # this should speed up comparison for many DACs (but scales up
                # with the index of the distinct DAC)
                if self.getDAC(k) != other.getDAC(k): 
                    return False
            # ret = all(self.getDAC(d) == other.getDAC(d) for d in range(self.nDACChannels))
            # ret = all(all(np.all(self.getDAC(d).getEpochsTable(s) == other.getDAC(d).getEpochsTable(s)) for s in range(self.nSweeps)) for d in range(self.nDACChannels))
                    
        if ret:
            for k in range(self.nADCChannels):
                # NOTE: Return after first iteration showing distinct ADCs
                if self.getADC(k) != other.getADC(k):
                    return False
            # ret = all(self.getADC(c) == other.getADC(c) for c in range(self.nADCChannels))
            
        return ret
    
    def diff(self, other) -> dict:
        if not isinstance(other, self.__class__):
            return {"Type":(self.__class__, other.__class__)}
        
        properties = inspect.getmembers_static(self, lambda x: isinstance(x, property))
        
        prop_diffs = list(filter(lambda x: np.any(x[2] != x[4]), ((p, "self:", getattr(self, p[0]), "other:", getattr(other, p[0])) for p in properties)))
        
        if len(prop_diffs):
            return {"Properties": prop_diffs}
        
        dac_diffs = list(filter(lambda x: x[1] != x[2], ((f"DAC {k}", self.getDAC(k), other.getDAC(k)) for k in range(self.nDACChannels))))
        
        if len(dac_diffs):
            return {"DACs":dac_diffs}
        
        adc_diffs = list(filter(lambda x: x[1] != x[2], ((f"ADC {k}", self.getADC(k), other.getADC(k)) for k in range(self.nADCChannels))))
        
        if len(adc_diffs):
            return {"ADCs": adc_diffs}
    
    def toHDF5(self, group:h5py.Group, name:str, oname:str, compression, chunks, track_order,
                       entity_cache) -> h5py.Group:
        """Encodes this ABFProtocol as a HDF5 Group"""
        
        # print(f"{self.__class__.__name__}.toHDF5: group = {group}, name = {name}, oname = {oname}")
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        # print(f"\ttarget_name = {target_name}")
        # print(f"\tobj_attrs {obj_attrs}")
        
        
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity
        
        
        attrs = dict()
        for n in ("_nADCChannels_", "_nDACChannels_", "_activeDACChannel_",
                  "_hasAltDacOutState_", "_hasAltDigOutState_",
                  "_nDigitalOutputs_", "_nTotalDigitalOutputs_",
                  "_nSynchronizedDigitalOutputs_", "_digTrainActiveHi_",
                  "_digHolding_", "_digHoldingValue_","_digUseLastEpochHolding_",
                  "_acquisitionMode_", "_nSweeps_", "_nRuns_", "_nTrials_",
                  "_nTotalDataPoints_", "_nDataPointsPerSweep_",
                  "_samplingRate_", "_sweepInterval_", 
                  "_averaging_", "_averageWeighting_", 
                  "_protocolFile_","_sourceHash_", "_sourceId_", 
                  "_fileOrigin_",
                  ):
            
            arg = n.strip("_")
            attrs[arg] = getattr(self, n)
            
        objattrs = h5io.makeAttrDict(**attrs)

        obj_attrs.update(objattrs)
        # objattrs = h5io.makeAttrDict(**obj_attrs)
        
        # print(f"{self.__class__.__name__}.toHDF5:")
        # print(f"\tobj_attrs: {obj_attrs}")
        # print(f"\tobjattrs: {objattrs}")
        
        inputs = self._inputs_
        outputs = self._outputs_
        
        # entity_name = name if (isinstance(name, str) and len(name.strip())) else oname if (isinstance(oname, str) and len(oname.strip())) else strutils.str2symbol(self.name)
        
        if isinstance(name, str) and len(name.strip()):
            target_name = name
        
        entity = group.create_group(target_name, track_order = track_order)
        entity.attrs.update(obj_attrs)
        
        inputs_group = h5io.toHDF5(inputs, entity, name="inputs",
                                           oname="ADCs", 
                                           compression=compression,
                                           chunks=chunks, 
                                           track_order=track_order,
                                           entity_cache=entity_cache,
                                           )
        
        outputs_group = h5io.toHDF5(outputs, entity, name="outputs",
                                            oname="DACs", 
                                           compression=compression,
                                           chunks=chunks, 
                                           track_order=track_order,
                                           entity_cache=entity_cache,
                                           )
        
        h5io.storeEntityInCache(entity_cache, self, entity)
        
        return entity
    
    @classmethod
    def fromHDF5(cls, entity:h5py.Group, 
                             attrs:typing.Optional[dict]=None, cache:dict = {}):
        
        if entity in cache:
            return cache[entity]
        
        if attrs is None:
            attrs = h5io.attrs2dict(entity.attrs)
            
        # print(f"{cls.__name__}.fromHDF5:")
        # print(f"\tattrs: {attrs}")
            
        kargs = dict()
            
        for n in ("_nADCChannels_", "_nDACChannels_", "_activeDACChannel_",
                  "_hasAltDacOutState_", "_hasAltDigOutState_",
                  "_nDigitalOutputs_", "_nTotalDigitalOutputs_",
                  "_nSynchronizedDigitalOutputs_", "_digTrainActiveHi_",
                  "_digHolding_", "_digHoldingValue_","_digUseLastEpochHolding_",
                  "_acquisitionMode_", "_nSweeps_", "_nRuns_", "_nTrials_",
                  "_nTotalDataPoints_", "_nDataPointsPerSweep_",
                  "_samplingRate_", "_sweepInterval_", 
                  "_averaging_", "_averageWeighting_", 
                  "_protocolFile_","_sourceHash_", "_sourceId_", "_fileOrigin_",
                  ):
            arg = n.strip("_")
            kargs[arg] = attrs[arg]
            
        # print(f"\tentity/inputs = {entity['inputs']}")
        # print(f"\tentity/outputs = {entity['outputs']}")
            
        kargs["inputs"] = h5io.fromHDF5(entity["inputs"], cache)
        kargs["outputs"] = h5io.fromHDF5(entity["outputs"], cache)
        
        # print(f"inputs: {kargs['inputs']}")
        # print(f"outputs: {kargs['outputs']}")
        
        # print(f"kargs: {kargs}")
        
        ret = cls(obj = None, **kargs)
        
        for i in ret.inputs:
            i.protocol = ret
            
        for o in ret.outputs:
            o.protocol = ret
            
        return ret
            
    
    def is_identical_except_digital(self, other):
        if not isinstance(other, self.__class__):
            return False
        
        properties = inspect.getmembers_static(self, lambda x: isinstance(x, property))
        
        ret = True
        for p in properties:
            # NOTE: see NOTE: 2023-11-05 21:05:46 and NOTE: 2023-11-05 21:06:10
            myattr = getattr(self, p[0])
            otherattr = getattr(other, p[0])
            if isinstance(myattr, np.ndarray) or isinstance(otherattr, np.ndarray):
                if not np.all(myattr == otherattr):
                    return False
            else:
                if myattr != otherattr:
                    return False
        
        if ret:
            for k in range(self.nDACChannels):
                if not self.getDAC(k).is_identical_except_digital(other.getDAC(k)):
                    return False
                    
        if ret:
            for k in range(self.nADCChannels):
                if self.getADC(k) != other.getADC(k):
                    return False
                    
            # ret = all(self.getADC(c) == other.getADC(c) for c in range(self.nADCChannels))
        # if ret:
        #     ret = all(all(np.all(self.getDAC(d).getEpochsTable(s, includeDigitalPattern=False) == other.getDAC(d).getEpochsTable(s, includeDigitalPattern=False)) for s in range(self.nSweeps)) for d in range(self.nDACChannels))
                    
        return ret
    
    def logicalADCIndex(self, index:int) -> int:
        """Returns the logical index of the ADC with specified physical index.
    
        See also self.physicalADCIndex
        """
        if not isinstance(index, int):
            raise TypeError(f"Expecting an int; instead, got {type(index).__name__}")
        indexingMap = self.adcPhysical2LogicalIndexMap 
        if index in indexingMap:
            return indexingMap[index]
        
        raise ValueError(f"Invalid physical ADC index: {index}")
    
    def physicalADCIndex(self, index:int) -> int:
        """Returns the physical index of the ADC with specified logical index.
        
        See also self.logicalADCIndex."""
        if not isinstance(index, int):
            raise TypeError(f"Expecting an int; instead, got {type(index).__name__}")
    
        indexingMap = self.adcLogical2PhysicalIndexMap 
        if index in indexingMap:
            return indexingMap[index]
        
        raise ValueError(f"Invalid logical ADC index: {index}")
    
    @property
    def adcNames(self):
        return tuple(i.name for i in self.inputs)
    
    @property
    def adcUnits(self):
        return tuple(i.units for i in self.inputs)
    
    @property
    def adcLogical2PhysicalIndexMap(self):
        return dict((i.logicalIndex, i.physicalIndex) for i in self.inputs)
            
    @property
    def adcPhysical2LogicalIndexMap(self):
        return dict((i.physicalIndex, i.logicalIndex) for i in self.inputs)
    
    @property
    def dacNames(self):
        return tuple(o.name for o in self.outputs)
            
    @property
    def dacUnits(self):
        return tuple(o.units for o in self.outputs)
    
    @property
    def physicalDACIndexes(self):
        return tuple(o.physicalIndex for o in self.outputs)
            
    @property
    def logicalDACIndexes(self):
        return tuple(o.logicalIndex for o in self.outputs)
            
    @property
    def physicalADCIndexes(self):
        return tuple(i.physicalIndex for i in self.inputs)
            
    @property
    def logicalADCIndexes(self):
        return tuple(i.logicalIndex for i in self.inputs)
            
    @property
    def dacLogical2PhysicalIndexMap(self):
        return dict((i.logicalIndex, i.physicalIndex) for i in self.outputs)
            
    @property
    def dacPhysical2LogicalIndexMap(self):
        return dict((i.physicalIndex, i.logicalIndex) for i in self.outputs)
    
    @property
    def acquisitionMode(self) -> ABFAcquisitionMode:
        """Alias to operationMode"""
        return self._acquisitionMode_
    
    @property
    def digitalOutputDACs(self) -> tuple:
        """DAC channels where digital output is configured"""
        return tuple(filter(lambda x: x.digitalOutputEnabled, self.DACs))
    
    @property
    def operationMode(self) -> ABFAcquisitionMode:
        """    
        variable_length_event = 1
        fixed_length_event = 2
        gap_free = 3
        high_speed_oscilloscope = 4 # Not supported by neo, but supported by pyabf!
        episodic_stimulation = 5
        """
        return self._acquisitionMode_
    
    @property
    def activeDACOutput(self) -> ABFOutputConfiguration:
        return self.outputs[self.activeDACChannelIndex]
    
    @property
    def activeDACChannelIndex(self) -> int:
        """Alias to self.activeDACChannel, for backward compatibility"""
        return self.activeDACChannel
    
    @property
    def activeDACChannel(self) -> int:
        """Index of the "active" DAC channel as reported in the ABF file protocol.
        
        This can be somewhat confusing — a DAC channel is `active` in a given 
        protocol if:
        
        • it has "Digital Outputs" enabled in the corresponding 'Channel #' 
            sub-tab of the "Waveform" tab in Clampex protocol editor; 
        
        OR:
        • when no DAC is sending digital output, it is the channel with the 
            highest index that sends out analog waveforms
        
        NOTE 1:
        ∘ when "Alternate Digital Outputs" is DISABLED in the "Waveform" tab:
            ⋆ the "active" DAC is the only DAC that associates digital output in
                the protocol
    
            ⋆ the digital pattern defined in an epoch under this DAC's "Channel #"
            sub-tab will be sent out with every sweep;
    
            ⋆ the pattern will be emitted on the digital channel index
            corresponding to the actual index of the bit (highest on the left)
            in the DIG channels bank; e.g., for the top bank (3-0):
    
            0001 → emits a TTL PULSE on DIG0 
            000* → emits a TTL TRAIN on DIG0
            0010 → emits a TTL PULSE on DIG1
            00*0 → emits a TTL TRAIN on DIG1
    
        ∘ when "Alternate Digital Outputs" is ENABLED in the "Waveform" tab:
            ⋆ this DAC will send the pattern defined under this DAC's
                "Channel #" sub-tab, ONLY during even-numbered sweeps 
                (0, 2, 4, ...); this is the MAIN digital pattern
    
            ⋆ the "alternative" pattern needs to be defined in ANOTHER DAC
                sub-tab and will be emitted during odd-numbered sweeps
                (1, 3, 5, ...); this is the ALTERNATIVE digital pattern
    
            ⋆ there can be only one alternate DIG pattern defined in any 
                other DAC;     
        
        ∘ when two DACs are used to configure alternate digital patterns (see above)
            the "active" DAC is the one where "Analog waveform" is enabled in the
            corresponding "Channel #" sub-tab.
        
            CAUTION: This means that one can record using DAC0, yet the actual
            "active" DAC may be DAC1. This is important when constructing a
            RecordingSource (see ephys module) — one needs to specify the actual 
            DAC used for recording (DAC0 in this example) instead of the "active"
            DAC (DAC1 in this example).
            
        WARNING: In a two-pathways experiment, the MAIN and ALTERNATE patterns
        should use bits corresponding to distinct DIG channels.
        
        NOTE: The association between the alternate DIG pattern and a particular DAC
        is only for GUI purposes - it does NOT engage the "other" DAC in any way
        (the "other" DAC may still be used for other purposes e.g. sending out
        analog DAC command waveforms during its epochs)
        
        Works for most cases where a single DAC (0 or 1) is used , but currently
        meaningless when no analog or digital commands are sent at all or with
        atypical connections and DAC configurations (see comments in the code)
        
        
        When DIG channels are off in all DACs, this method return 0.
        
        NOTE: DAC channels have identical physical and logical indices. WARNING:
        This is in contrast to the ADC channels, where the ADCs logical indices 
        may differ from the physical ones (depending on which ADCs are actually 
        used, in the protocol, to record the data).
        
        
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
#         digSendingDacs = list(c for c in range(self.nDACChannels) if self.getDAC(c).digitalOutputEnabled)
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
        """Number of sweeps per run or per trial average"""
        return self._nSweeps_
    
    @property
    def nRuns(self) -> int:
        """Number of runs per trial.
        All runs have the same number of sweeps (self.nSweeps)
        A trial with more than one run will save sweep-by-sweep average in the ABF
        file. This average is equivalent of a single run with self.nSweeps sweeps.
        """
        return self._nRuns_
    
    @property
    def nTrials(self) -> int:
        """This is always 1?"""
        return self._nTrials_
    
    @property
    def averaging(self) -> ABFAveragingMode:
        """Averaging mode - irrelevant when self.nRuns == 1"""
        return self._averaging_
    
    @property
    def averageWeighting(self) -> float:
        """Sweep eighting when averaging - irrelevant when self.nRuns == 1"""
        return self._averageWeighting_
    
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
    def file(self):
        return self._protocolFile_
    
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
        return np.array(list(map(self.getSweepTime, range(self.nSweeps)))) * pq.s
    
    def digitalOutputs(self, alternate:typing.Optional[bool] = None, 
                       trains:typing.Optional[bool] = None) -> set:
        """Indices of the digital output channels used in this protocol.
    
        By default, returns all DIG channels used in both main and alternate 
        patterns, for TTL pulses and TTL trains.
        
        This behaviour can be refined with the two parameters:
        
        • alternate (False|True|None) - default is None — whether to report only
            DIG channels used in the main (False) or alternate (TRUE) pattern
        
        • trains (False|True|None) - default is None — whether to report only
            DIG channels used to generate single pulses (False) or trains (True).
        
        """
        
        return set(itertools.chain.from_iterable([list(itertools.chain.from_iterable([e.getUsedDigitalOutputChannels(alternate, trains) for e in o.epochs])) for o in self.outputs]))

    def getClampMode(self, 
                     adc:typing.Union[int, str, ABFInputConfiguration] = 0,
                     dac:typing.Optional[typing.Union[int, str, ABFOutputConfiguration]] = None,
                     physicalADC:bool=True,
                     physicalDAC:bool=True) -> object:
        """Infers the clamping mode used in the experiment run with this protocol.
        
        The inferrence is based on the physical units of the input - output signal
        pair, as follows:
        
        Input units             Output units:           Clamping mode:
        -----------------------------------------------------------
        electrical current      electrical potential    voltage clamp
        electrical potential    electrical current      current clamp
        
        In any other combination: no clamping. NOTE that this is not necessarily
        encountered in practice. Rather, one can have membrane voltage recorded
        in the input, with current units for any signal sent on the output as 
        "command voltage", but with the amplifier set to voltage follower mode 
        (e.g. 'I=0' setting in some amplifiers). Technically, this is a NoClamp
        case, although the DAQ device may not be able to detect this.
        
        Parameters:
        -----------
        adcIndex: int or str, default is 0
            Index (logical or physical) or name of the ADC channel involved in 
            the experiment
        
        dacIndex: int or str, or None; default is None
            Index (logical or physical) or name of the DAC channel involved in 
            the experiment.
            When None (the default) the method used the active DAC channel as 
            defined in the protocol.
        
        physicalADC, physicalDAC: bool (default is True for both) indicate if 
            the adcIndex, respectively dacIndex are physical or logical indexes.
            Ignored when those indexes are given as strings (channel names).
        
        Returns:
        
        an ephys.ephys.ClampMode
        
        """
        # from ephys.ephys import ClampMode
        if not isinstance(adc, ABFInputConfiguration):
            adc = self.getADC(adc, physical=physicalADC) # get first (primary) input by default

        if adc is None:
            raise ValueError(f"{'Physical' if physicalADC else 'Logical'} ADC index {adcIndex} is invalid for this protocol")

        recordsCurrent = scq.checkElectricalCurrentUnits(adc.units)
        recordsPotential = scq.checkElectricalPotentialUnits(adc.units)

        if not isinstance(dac, ABFOutputConfiguration):
            dac = self.getDAC(dac, physicalDAC) # get active DAC by default

        commandIsCurrent = scq.checkElectricalCurrentUnits(dac.units)

        commandIsPotential = scq.checkElectricalPotentialUnits(dac.units)

        if recordsPotential and commandIsCurrent:
            return self.ClampMode.CurrentClamp
        elif recordsCurrent and commandIsPotential:
            return self.ClampMode.VoltageClamp
        else:
            return self.ClampMode.NoClamp

    def getSweepTime(self, sweep:int = 0) -> pq.Quantity:
        if self.sweepInterval == 0*pq.s:
            return sweep * self.sweepDuration
        return sweep * self.sweepInterval
    
    def getSweepwiseDigitalActivationForPathways(self, pathways:typing.Sequence[SynapticPathway],
                                        dac:typing.Optional[typing.Union[ABFOutputConfiguration, int, str]]=None,
                                        byFirstStimulus:bool=True,
                                        indices:bool=True):
        """Returns sweep-specific digital stimulation of pathways.
        
        Often, a protocol is used to digitally stimulate more than one synaptic
        pathway (typically, to test cross-talk, or overlap, between two synaptic
        pathways based on short-term plasticity phenomena such as paired-pulse
        facilitation).
        
        This function helps identifying such cases, including the order in which 
        the pathways are stimulated, in each sweep.
        
        For each sweep in the protocol, returns a tuple with the indices of the 
        pathways that have been stimulated (in the `pathways` sequence), ordered
        by the temporal order of the stimulation in each sweep.
        
        This works on ABFEpoch epochs, defined in the specified DAC, that emit 
        digital signals to stimulate the pathways.
        
        Parameters:
        ----------
        pathways: sequence of SynapticPathway objects
            Not all pathways in the sequence might be stimulated by the protocol 
            in every sweep.
        
        dac: a DAC channel configuration of this protocol, an int (physical index)
            or str (name of the DAC channel), or None (default)
        
            When None, `dac` is the active DAC channel of the protocol.
        
            WARNING: When a protocol uses alternative digital outputs, this DAC 
            should be the "active" DAC of the protocol; for generality, we allow
            specifying other DAC here in case the protocol configured digital
            output a DAC other than the one used for command waveforms.
        
        byFirstStimulus: bool, default is True — controls how the order of pathway
            stimulation is returned, in particular when the pathways are 
            stimulated in several interleaved epochs in a given sweep.
        
            When True, the order of the pathways inside the stimulation sequence
            is given by the first occurence of a stimulus in the pathway(s) (i.e.,
            according to the timing of the first ABFEpoch that stimulates the 
            pathway, regardless of any subsequent epochs that stimulate the 
            same pathway later in the sweep).
        
            NOTE: This is useful to simply determine the sweep-specific order in
                which parthways are stimulated, regardless of the stimulation pattern.
        
            When False, the output reflects sequence of pathways in all ABF Epochs
            that emit stimulus signals. See examples below
        
        indices: bool, default is True.
            When True, the returned tuple will contain the indexes of the pathways 
                in the sequence supplied in the 'pathways' parameter (see above)
            When False, the return tuple will contin a reference to the pathway 
                itself
            
        
        Returns:
        -------
        A tuple of 2-tuples, eacb containing:
            sweep index, tuple of indexes in the `pathways` sequence (when the 
                'indices' parameter is True), or tuple of pathways (when 'indices'
                is False) that have been stimulated in that sweep.
        
        NOTE: Depending on the value of the `byFirstStimulus` parameter (see above)
            the tuple of pathway indexes contains:
        
            • `byFirstStimulus` True: the stimulated pathway indexes in the order
                of the occurrence of their FIRST stimulation in the given sweep
                — this is the default;
        
            • `byFirstStimulus` False: the indexes of the stimulated pathways in 
                the order they occur accross all epochs that trigger their stimulation,
                in the given sweep.
        
        Examples:
        ---------
        
        Example 1: given a source declaring two pathways stimulated, respectively, 
            via digital channels DIG 0 and DIG 1, and a protocol that stimulates 
            these pathways alternatively according to the schematic below 
            (NOTE: protocol has alternateDigitalOutputStateEnabled True),
        
            sweep 0 (even sweeps):
        
                path 0 (DIG 0)  ______|_|_________
                path 1 (DIG 1)  __________________
            
            sweep 1 (odd sweeps):
            
                path 0 (DIG 0)  __________________
                path 1 (DIG 1)  ______|_|_________
        
            `byFirstStimulus`:          the function returns:
        -------------------------------------------------------------------
            True                        ((0, (0,)), (1, (1,)))
            False                       ((0, (0,)), (1, (1,)))
        
            NOTE: In this example there is one epoch triggering a pathway in 
                all sweeps, but the epochs uses a TTL train instead of a pulse;
                the value of `byFirstStimulus` is irrelevant;
                each epoch appear to be triggered once, but in reality it is 
                stimulated twice per epoch (via a TTL train)
        
            ATTENTION: this example reflects the fact that the number of times
                a pathway index appears in the tuple does NOT necessarily indicate
                how many times that pathway was actually stimulated — the
                latter depends on whether the epoch emits a TTL pulse or a TTL
                train, and, in the case of TTL trains, on the pulse period in the 
                train, and duration of the epoch.
        
        Example 2: the same source as in Example 1, but the protocol stimulates
            the pathways according to the following scheme:
        
            sweep 0 (even sweeps):
        
                path 0 (DIG 0)  ______|___________
                path 1 (DIG 1)  ________|_________
            
            sweep 1 (odd sweeps):
            
                path 0 (DIG 0)  ________|_________
                path 1 (DIG 1)  ______|___________
        
            `byFirstStimulus`:          the function returns:
        -------------------------------------------------------------------
            True                        ((0, (0, 1)), (1, (1, 0)))
            False                       ((0, (0, 1)), (1, (1, 0)))
        
            NOTE: In this example there is one epoch triggering each pathway in 
                all sweeps, therefore the value of `byFirstStimulus` is irrelevant.
        
        Example 3 (contrived): the same source as in Example 1, but the protocol 
            stimulates the pathways according to the following scheme:
        
            sweep 0 (even sweeps):
        
                path 0 (DIG 0)  ______|_____|_____
                path 1 (DIG 1)  ________|_|_______
            
            sweep 1 (odd sweeps):
            
                path 0 (DIG 0)  ________|_|_______
                path 1 (DIG 1)  ______|___________
        
            `byFirstStimulus`:          the function returns:
        -------------------------------------------------------------------
            True                        ((0, (0, 1)), (1, (1, 0)))
            False                       ((0, (0, 1, 1, 0)), (1, (1, 0, 0)))

            I.e., when `byFirstStimulus` is True the pathway stimulations are
            returned in the order of their first stimulation (in sweep 0,
            pathway 0 is the first pathway that is being stimulated, whereas in 
            sweep 1 it is the second pathway — pathway 1 — that is stimulated,
            even if both pathways are also stimulated several times later).
        
            When `byFirstStimulus` is False, the function returns the full 
            stimulation sequence of the pathways in the sweep.
        
        Example 4: Same recording source as above, but the protocol defines a single
            sweep for the stimulation of a single pathway
            TODO! docstring for this example
        
        """
        # from ephys.ephys import SynapticPathway
        
        if dac is None:
            dac = self.getDAC()
            
        elif isinstance(dac, (int, str)):
            dac = self.getDAC(dac)
            
        elif isinstance(dac, ABFOutputConfiguration):
            assert dac.protocol == self, "The specified DAC channel configuration does not belong to this protocol"
            
        else:
            raise TypeError(f"`dac` expected an ABFOutputConfiguration, and int, or a string (name); instad, ot {type(dac).__name__} ")
            
        if len(pathways) == 0:
            raise ValueError("`pathways` is an empty sequence")
        
        if not all(isinstance(v, self.SynapticPathway) for v in pathways):
            raise TypeError("`pathways` expected to be a sequence of ephys.SynapticPathway objects")
        
        pathways = utilities.unique(pathways, idcheck=False)
        # pathways = utilities.unique([p for p in pathways if p.stimulus.dig])
        # digStimPathways = [p for p in pathways if p.stimulus.dig]
        # dacStimPathways = [p for p in pathways if p.stimulus.dig]
        
        ret = tuple()
        
        if len(pathways):
            if byFirstStimulus:
                # NOTE: 2024-03-10 20:11:22
                # description of the algorithm in the one-line nested comprehension
                # below:
                # 1. for each sweep:
                #   1.1. for each pathway:
                #       1.1.1. get the epochs with digital stimulus ON for the pathway's 
                #       digital stimulus channel, in the current sweep →
                #           → as tuples of pathway index, epochs sequence
                #           (NOTE: the epochs sequence there may have more than 
                #           one epoch, or NO epoch if there is no stimulation on 
                #           that DIG channel, in current sweep)
                #       1.1.2. take out (filter) the entries with no epochs
                #       1.1.3. sort entries by the start time of the first epoch in 
                #           the entry (does nothing if no entry left after the filter 
                #           in step 1.1.2.)
                # 2. collect a tuple of tuples: (sweep index, tuple of pathway indices 
                #   ordered by the time of their first epoch, sorted as in step 1.1.3. above)
                if indices:
                    # this one returns pathway INDEXES, NOT pathway objects
                    ret = tuple((s, tuple( x[0] for x in tuple(sorted(tuple(filter(lambda j: len(j[1]), tuple([(k, dac.getEpochsForDigitalChannel(pathways[k].stimulus.channel, s)) for k in range(len(pathways))]))), key = lambda x: dac.getEpochStartTime(x[1][0]))))) for s in range(self.nSweeps))
                else:
                    # this one returns pathway OBJECTS, NOT THEIR INDEXES
                    ret = tuple((s, tuple( x[0] for x in tuple(sorted(tuple(filter(lambda j: len(j[1]), tuple([(p, dac.getEpochsForDigitalChannel(p.stimulus.channel, s)) for p in pathways]))), key = lambda x: dac.getEpochStartTime(x[1][0]))))) for s in range(self.nSweeps))
                
            else:
                # NOTE: 2024-03-10 20:14:34
                # description of the algorithm (one-liner nested comprehensions)
                # 2. for each sweep:
                #   2.1. get epochs with digital output
                #   2.2. collect only those that use the stimulus digital channel 
                #       declared in the pathway specifications
                # collect a tuple of tuples: (sweep index, tuple of pathway indices stimulated in all epochs in the sweep)
                if indices:
                    ret = tuple([(s, tuple(itertools.chain.from_iterable([list(itertools.chain.from_iterable([list(filter(lambda k: pathways[k].stimulus.channel == c, range(len(pathways)))) for c in e.getUsedDigitalOutputChannels(s%2 > 0)])) for e in dac.getEpochsWithDigitalOutput()]))) for s in range(self.nSweeps)])
                else:
                    ret = tuple([(s, tuple(itertools.chain.from_iterable([list(itertools.chain.from_iterable([list(filter(lambda p: p.stimulus.channel == c, pathways) for c in e.getUsedDigitalOutputChannels(s%2 > 0))])) for e in dac.getEpochsWithDigitalOutput()]))) for s in range(self.nSweeps)])
                
        return ret
    
    @property
    def inputs(self):
        """List of input configurations (ADC channels); alias to self.ADCs"""
        return self.ADCs
    
    @property
    def ADCs(self):
        """List of input configurations (ADC channels)"""
        return self._inputs_
    
    def getADC(self, adcChannel:typing.Union[int, str] = 0, 
               physical:bool=True) -> ABFInputConfiguration:
        """Access the input configuration of an ADC channel with a given index or name.
        
        Parameters:
        -----------
        adcChannel: int or str, or None. Optional, default is None
            When an int, it represents the index (physical or logical) of the ADC.
            When a str, it represents the name of the ADC.
        
        physical: bool; flag to indicate if `adcChannel`, when an int, represents
            the physical channel index.
            
            Default is True.
        
        Returns:
        --------
        An ABFInputConfiguration
        
        """
        if isinstance(adcChannel, str):
            if adcChannel not in self.adcNames:
                raise ValueError(f"Invalid ADC channel name {adcChannel}")
            
            adcChannel = self.adcNames.index(adcChannel)
            
            # if physical:
            #     adcChannel = self.adcLogical2PhysicalIndexMap[adcChannel]

        inputconfs = list(filter(lambda x: x.getChannelIndex(physical) == adcChannel, self._inputs_))
        
        if len(inputconfs):
            return inputconfs[0]
        else:
            ndx = adcChannel if physical else self.adcLogical2PhysicalIndexMap[adcChannel]
            if ndx in range(self.nADCChannels):
                return self.inputs[ndx]
            chtype = "physical" if physical else "logical"
            raise ValueError(f"Invalid {chtype} ADC channel specified {adcChannel}")

    def getInput(self, adcChannel:int = 0, physical:bool=True) -> ABFInputConfiguration:
        """Calls self.getADC(…)"""
        return self.getADC(adcChannel, physical=physical)
    
    def inputConfiguration(self, adcChannel:typing.Union[int, str] = 0, 
                           physical:bool=True) -> ABFInputConfiguration:
        """Calls self.getADC(…)"""
        return self.getADC(adcChannel, physical=physical)
        
    @property
    def DACs(self):
        """List of output configurations (DAC channels)"""
        return self._outputs_
    
    @property
    def outputs(self):
        """List of output configurations (DAC channels); alias to self.DACs"""
        return self.DACs
    
    def getDAC(self, dacChannel:typing.Optional[typing.Union[int, str]] = None, 
                            physical:bool=True) -> ABFOutputConfiguration:
        """Access the output configuration of a DAC channel with a given index or name.
        
        Parameters:
        -----------
        dacChannel: int or str, or None. Optional, default is None
            When an int, it represents the index (physical or logical) of the DAC.
            When a str, it represents the name of the DAC.
        
        physical: bool; flag to indicate if `dacChannel`, when an int, represents
            the physical channel index.
            
            Default is True.
        
        Returns:
        --------
        An ABFOutputConfiguration
        
        """
        # if not isinstance(index, int):
        if dacChannel is None:
            dacChannel = self.activeDACChannelIndex
            
        elif isinstance(dacChannel, str):
            if dacChannel not in self.dacNames:
                raise ValueError(f"Invalid DAC channel name {dacChannel}")
            
            dacChannel = self.dacNames.index(dacChannel)
            
        # outputConfs = list(filter(lambda x: x.logicalIndex == index if physical else x.physicalIndex == index, self._outputs_))
        outputConfs = list(filter(lambda x: x.getChannelIndex(physical) == dacChannel, self._outputs_))

        if len(outputConfs):
            return outputConfs[0]
        else:
            chtype = "physical" if physical else "logical"
            raise ValueError(f"Invalid {chtype} DAC channel specified {dacChannel}")
        
    def getEpochDigitalPattern(self, dac:typing.Union[int, str], 
                               epoch:typing.Union[int, str], sweep:int = 0) -> tuple:
        """
        Returns the digital pattern that WOULD be output by a dac during a specific epoch.
        
        This depends, simultaneously, on the following conditions:
        
        1) the DAC channel has digital outputs enabled
        
        2) If alternative digital outputs are enabled in the protocol, this DAC
            emits DIG outputs on the specified sweep.
            
        3) the DAC channel takes part in alternate digital outputs or not (this
            depends on the channel index, with DAC 0 and 1 being the only ones
            used for alternate digital output during even- and odd-numbered sweeps)
        
        Returns:
        --------
        A 2-tuple[4-tuple[int]] corresponding to the two DIG output banks in the
        order 3⋯0, 7⋯4
        
        dac: physical DAC channel index, or DAC name
        epoch: ABFEpoch number or letter
        sweep: int, default is 0
        """
        dac = self.getDAC(dac)
        
        isAlternateDigital = self.alternateDigitalOutputStateEnabled and sweep % 2 > 0
        
        epoch = dac.getEpoch(epoch)
        if epoch is None:
            raise ValueError(f"Invalid epoch index or name {epoch} for {len(dac.epochs)} epochs defined for this DAC ({dac.physicalIndex}, {dac.name})")
        
        if self.alternateDigitalOutputStateEnabled:#  and dac.logicalIndex < 2: # dac emits the main pattern
            if dac.digitalOutputEnabled:
                if dac.physicalIndex == self.activeDACChannel:
                    if isAlternateDigital:
                        # this DAC has dig output enabled, hence during
                        # an experiment it will output NOTHING if either 
                        # alternateDigitalPattern is disabled OR sweep number 
                        # is even
                        #
                        
                        # NOTE: 2024-10-20 10:42:42
                        # retrieve the alternate digital pattern defined in
                        # epoch, then:
                        dig_3_0 = epoch.getDigitalPattern(True)[0] # select first bank
                        dig_7_4 = epoch.getDigitalPattern(True)[1] # select second bank
                    else:
                        # this DAC has dig output enabled, hence during
                        # an experiment it will output the main digital pattern
                        # if either alternateDigitalPattern is disabled, OR
                        # sweep number is even
                        #
                        
                        # NOTE: 2024-10-20 10:43:38
                        # retrieve the main digital pattern defined in epoch,
                        # then:
                        dig_3_0 = epoch.getDigitalPattern(False)[0] # select first bank
                        dig_7_4 = epoch.getDigitalPattern(False)[1] # select second bank
                        
                else:
                        dig_3_0 = dig_7_4 = [0,0,0,0] # if not active DAC, return zeros
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
                
                dig_3_0 = dig_7_4 = [0,0,0,0]
                
        else:
            if dac.digitalOutputEnabled:
                # if alternateDigitalPattern is not enabled, or the DAC channel
                # is one of the channels NOT involved in alternate output
                # (2, …) the channel will always output the main digital 
                # pattern here
                dig_3_0 = epoch.getDigitalPattern()[0]
                dig_7_4 = epoch.getDigitalPattern()[1]
            else:
                dig_3_0 = dig_7_4 = [0,0,0,0]
                
        return dig_3_0, dig_7_4
    
    def getEpochDigitalWaveform(self, dac:typing.Union[int,str], 
                                epoch:typing.Union[int,str],
                                digChannel:typing.Optional[typing.Union[int, typing.Sequence[int]]] = None, 
                                sweep:int,
                                lastLevelOnly:bool = False,
                                seprateWaves:bool=True,
                                digOFF:typing.Optional[pq.Quantity] = None,
                                digON:typing.Optional[pq.Quantity] = None,
                                trainOFF:typing.Optional[pq.Quantity] = None,
                                trainON:typong.Optional[pq.Quantity] = None,
                                returnLevels:bool=False) -> typing.Union[pq.Quantity, typing.Sequence[pq.Quantity]]:
        """Waveform with the TTL signals emitted by the epoch.
        
        Mandatory positional parameters:
        --------------------------------
        
        epoch: the ABF epoch that is queried
        
        Named parameters:
        -----------------
        
        sweep: the index of the ABF sweep (digital outputs may be specific to the 
                sweep index, when alternate digital patterns are enabled in the 
                ABF protocol)
        
                Default is 0 (first sweep)
        
        digChannel:default is None, meaning that the function returns a waveform
            for each digital output channel that is active during this epoch
            (and during the specified sweep)
        
        lastLevelOnly: default is False; when True, just generate a constant wave
            with the value of the last digital logic level; that is, OFF for digital 
            pulse or train. NOTE that the actual value of this level is either 0 V 
            or 5 V, depending on the values of protocol.digitalHoldingValue(channel) 
            and protocol.digitalTrainActiveLogic.
        
            See self.getDigitalLogicLevels, self.getDigitalPulseLogicLevels,
            and self.getDigitalTrainLogicLevels
        
        separateWavePerChannel: default is False. 
            When False, and more than one digChannel is queried, the function 
            returns a Quantity array with one channel-specific waveform per
            column.
        
            When True, the function returns a list of vector waveforms (one per 
            channel)
        
        digOFF, digON, trainOFF, trainON: scalar Python Quantities representing
            the logic levels for digital pulses and trains, respectively; when 
            they are None (default) the function will query these values from the 
            ABF protocol that associates this DAC output.
        
        returnLevels: default False; When True, returns the waves and the digOFF, 
        digON, trainOFF and trainON logical levels
        
        Returns:
        --------
        waves, [digOFF, digON, trainOFF, trainON], where:
        
        waves: list of Python quantities (Quantity arrays) whith the digital waveforms
        for each specified DIG channel are returned.
        
            The list contains:
                • a single 1D Quantity array, when digChannel parameter is an int 
                    (but see below)
                • as many 1D Quantity arrays as DIG channel indexes specified in 
                    digChannel parameter, and separateWavePerChannel is True
                • a single 2D Quantity array with shape (N,M) where:
                    ∘ N is the number of samples recorded by the epoch
                    ∘ M is the number of DIG channels specified in digChannel
        
            The list is EMPTY when not all DIG channel indexes specified
                    in the digChannel parameter are used by the epoch.
        
        digOFF, digON, trainOFF, trainON - scalar Python Quantities with the values
            of the logical levels for digital pulse and digital train.
        
            NOTE:
            1. trainOFF and trainON are None when the epoch emits only digital pulses
            2. digOFF and digON are None when the epoch emits only digital pulse trains
            3. Within a given epoch, these levels are identical for all DIG channels.
        
        When not all DIG channel indexes are used by the epoch to emit digital signals
        the function returns None
    
        """
        pass
        
    
    def getDigitalWaveform(self, dac:typing.Union[int, str], sweep:int = 0):
        pass
            
            
    def outputConfiguration(self, index:typing.Optional[typing.Union[int, str]] = None, 
                            physical:bool=False) -> ABFOutputConfiguration:
        """Calls self.getDAC(…)
        """
        return self.getDAC(index, physical)
    
    def getOutput(self, index:typing.Optional[typing.Union[int, str]] = None, 
                            physical:bool=False) -> ABFOutputConfiguration:
        """Calls self.getDAC(…)"""
        return self.getDAC(index, physical)
    
    def getDigitalChannelUsage(self, digChannel:int, dac:typing.Union[ABFOutputConfiguration, str, int], 
                               epochIndexes:bool=False, train:typing.Optional[bool] = None,
                               physical:bool=True) -> tuple:
        """Looks up the sweeps and epochs where a digital channel emits a TTL pulse or train
        See ABFOutputConfiguration.getEpochsForDigitalChannel documentation for 
        details.
        
        Returns a tuple of (sweep index ↔ epochs list) pairs
        
        """
        if not isinstance(digChannel, int):
            raise TypeError(f"`digChannel` expected an int; instead got {type(digChannel).__name__} ")
        if digChannel < 0 or digChannel >= self.nDigitalChannels:
            raise ValueError(f"Invalid `digChannel` ({digChannel}); expecting a value in {range(self.nDigitalChannels)}")
        
        if isinstance(dac, (int, str)):
            dac = self.getDAC(dac, physical=physical)
        elif not isinstance(dac, ABFOutputConfiguration):
            raise TypeError(f"`dac` expected an ABFOutputConfiguration, a str (DAC name) or int (DAC index); instead, got {type(dac).__name__}")
        
        return tuple(filter(lambda x: len(x[1]), ((k, dac.getEpochsForDigitalChannel(digChannel, k, indexes = epochIndexes, train=train)) for k in range(self.nSweeps))))
        
    
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
    def __init__(self, obj: typing.Optional[typing.Union[pyabf.ABF, neo.Block]]=None,
                 protocol:typing.Optional[ABFProtocol] = None,
                 adcChannel:int = 0, physical:bool=False, physicalIndex:typing.Optional[int]=None,
                 name:str = None,
                 units:typing.Optional[typing.Union[pq.Quantity, str]] = None):
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
        if protocol is None and isinstance(obj, (pyabf.ABF, neo.Block)):
            protocol = ABFProtocol(obj)

        if not isinstance(protocol, ABFProtocol):
            protocol = None
        # if isinstance(protocol, ABFProtocol):
        #     assert self._protocol_._sourceHash_ == hash(obj) and self._protocol_._sourceId_ == id(obj), f"The source {type(obj).__name__} object does not appear linked to the supplied protocol"
        # else:
        #     protocol = None
            # raise TypeError(f"'protocol' expected to be an ABFProtocol object; instead, got {type(protocol).__name__}")

        self._protocol_ = protocol


        adcName = ""
        
        adcUnits = None
        self._adcChannel_ = None
        self._physicalChannelIndex_ = None
        
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

            self._adcName_ = adcName
            self._adcUnits_ = scq.unitQuantityFromNameOrSymbol(adcUnits)

        elif isinstance(obj, neo.Block):
            assert sourcedFromABF(obj), "Object does not appear to be sourced from an ABF file"
            info_dict = getAcquisitionInfo(obj)
                
            if physical:
                p = [v["nADCNum"] for v in info_dict["listADCInfo"]]
                if adcChannel not in p:
                    adcName = ""
                    adcUnits = ""
                else:
                    self._physicalChannelIndex_ = adcChannel
                    logical = p.index(adcChannel)
                    self._adcChannel_ = logical
                    adcName = info_dict["listADCInfo"][logical]["ADCChNames"].decode()
                    adcUnits = info_dict["listADCInfo"][logical]["ADCChUnits"].decode()
            else:
                if adcChannel not in range(len(info_dict["listADCInfo"])):
                    adcName = ""
                    adcUnits = ""
                else:
                    self._adcChannel_ = adcChannel
                    self._physicalChannelIndex_ = info_dict["listADCInfo"][adcChannel]["nADCNum"]
                    adcName = info_dict["listADCInfo"][adcChannel]["ADCChNames"].decode()
                    adcUnits = info_dict["listADCInfo"][adcChannel]["ADCChUnits"].decode()
                    
            self._adcName_ = adcName
            self._adcUnits_ = scq.unitQuantityFromNameOrSymbol(adcUnits)

        else:
            if isinstance(physicalIndex, int):
                self._physicalChannelIndex_ = physicalIndex
                
            else:
                raise TypeError(f"Expecting physicalIndex an int; instead, got {type(physicalIndex).__name__}")
            
            if isinstance(adcChannel, int):
                self._adcChannel_ = adcChannel
            else:
                raise TypeError((f"Expecting adcChannel an int; instead, got {type(adcChannel).__name__}"))
            # BUG: 2024-10-06 13:31:46 FIXME
            # this assigns logical & physical to be the same  --  wrong!
            # self._physicalChannelIndex_ = self._adcChannel_ = adcChannel
            if isinstance(name, str) and len(name.strip()):
                adcName = name
                
            else:
                adcName = f"ADC_{self._physicalChannelIndex_}"
                
            self._adcName_ = adcName
            
            if isinstance(units, str) and len(units.strip()):
                self._adcUnits_ = scq.unitQuantityFromNameOrSymbol(units)
                
            elif isinstance(units, pq.Quantity):
                self._adcUnits_ = units
            else:
                self._adcUnits_ = pq.dimensionless
                
    def toHDF5(self, group, name, oname, compression, chunks, track_order,
                       entity_cache) -> h5py.Group:
        """Encodes this ABFInputConfiguration as a HDF5 Group.
        """
        
        # print(f"{self.__class__.__name__}.toHDF5: group = {group}, name = {name}, oname = {oname}")
        # NOTE: 2024-07-18 15:10:22
        # I choose a Group here, and not a Dataset, so that we can store the 
        # parent protocol as a soft link.
        #
        # The other reason is to have some kind of similarity to / symmetry with
        # ABFOutputConfiguration which is also encoded as HDF5 Group (because of 
        # the Epochs list)
        #
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        # print(f"\ttarget_name = {target_name}")
        # print(f"\tobj_attrs {obj_attrs}")
        
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity
        
        
        attrs = list(filter(lambda x: not x[0].startswith("_") and x[1].fset, 
                            inspect.getmembers_static(self, inspect.isdatadescriptor)))
        
        prattr = list(filter(lambda x: x[0]=="protocol", attrs))
        
        protocol_attr = None
        if len(prattr):
            ndx = attrs.index(prattr[0])
            protocol_attr = attrs.pop(ndx)
            
        
        objattrs = h5io.makeAttrDict(**dict(map(lambda x: (x[0], getattr(self, x[0])), attrs)))
        obj_attrs.update(objattrs)
        # if isinstance(name, str) and len(name.strip()):
        #     target_name = name
            
        entity = group.create_group(target_name, track_order = track_order)
        entity.attrs.update(obj_attrs)
            
        if isinstance(protocol_attr, tuple) and protocol_attr[0] == "protocol":
            # NOTE: 2024-07-18 14:57:47 Steps:
            # 1) this DAC is in a member of the parent protocol DACs list;
            # 2) that list is encoded as a hdf5 Group, and this must be indicated as
            #   such, in the group's attributes;
            # 3) furthermore, the encoded list is a member of a hdf5 Group which
            #   encodes the ABFProtocol → an ABF protocol can only be encoded as
            #   a hdf5 Group, because the hdf5 Goup is the only hdf5 entity that
            #   may contain children entities,
            # 
            
            # NOTE: 2024-07-18 15:05:34 check steps (1 & 2) from NOTE: 2024-07-18 14:57:47
            #
            # group_attrs = h5io.attrs2dict(group.attrs)
            # group_obj_class = group_attrs.get("type_name", None)
            
            # Not sure the above can be done directly:
            # group_obj_class = group.attrs.get("type_name", None)
            # if group_obj_class == "list":
            group_obj_class = group.attrs.get("python.class", None)
            if group_obj_class == "builtins.list":
                # NOTE: 2024-07-18 15:05:53
                # check step (2) from NOTE: 2024-07-18 14:57:47
                parent = group.parent   # by definition in HDF5, this is also a Group
                                        # and its attributes must indicate it is an
                                        # ABFProtocol
                
                # NOTE: 2024-07-18 15:16:06
                # check step (3) from NOTE: 2024-07-18 14:57:47
                parent_obj_class = parent.attrs.get("type_name", None)
                if parent_obj_class == "ABFProtocol":
                    entity["protocol"] = parent # soft link here
                    
            else:
                # to avoid infinite recursion, we only save the protocol when this ADC
                # is saved as part of a protocol
                scipywarn(f"Saving as an independent object will break the relationship between this ADC and its parent protocol.")
                h5io.toHDF5(None, entity, name="protocol") 
                    
        h5io.storeEntityInCache(entity_cache, self, entity)
        
        return entity
    
    @classmethod
    def fromHDF5(cls, entity:h5py.Dataset, 
                             attrs:typing.Optional[dict]=None, cache:dict = {}):
        # print(f"{cls.__name__}.fromHDF5")
        if entity in cache:
            return cache[entity]
        
        if attrs is None:
            attrs = h5io.attrs2dict(entity.attrs)
        # print(f"attrs: {attrs}")
        
        adcChannel = attrs.get("physicalIndex", 0)
        name = attrs.get("name", f"ADC{adcChannel}")
        units = attrs.get("units", pq.dimensionless)
        logicalIndex = attrs.get("logicalIndex", 0)
        protocol = h5io.fromHDF5(entity["protocol"], cache)
        
        return cls(obj=None, protocol=protocol, adcChannel=logicalIndex,
                   physical=True, physicalIndex = adcChannel, name=name, units=units)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        
        props = inspect.getmembers_static(self, lambda x: isinstance(x, property))
        
        return np.all([getattr(self, p[0]) == getattr(other, p[0]) for p in props if p[0] != "protocol"])
        # return np.all([utilities.safe_identity_test(getattr(self, p[0]), getattr(other, p[0]), idcheck=False) for p in props if p[0] != "protocol"])
    
    def __repr__(self):
        # return f"{self.__class__.__name__} ({super().__repr__()}): \'{self.name}\' (\'{scq.shortSymbol(self.adcUnits.symbol)}\') at index {self.physicalIndex} ↔ {self.logicalIndex}) (physical ↔ logical)"
        return f"{self.__class__.__name__} ({super().__repr__()}): \'{self.name}\' (\'{scq.shortSymbol(self.adcUnits)}\') at index {self.physicalIndex} ↔ {self.logicalIndex}) (physical ↔ logical)"

    def getChannelIndex(self, physical:bool=False) -> int:
        return self.physicalIndex if physical else self.logicalIndex

    @property
    def logicalIndex(self) -> int:
        return self._adcChannel_
    
    @logicalIndex.setter
    def logicalIndex(self, val:int):
        self._adcChannel_ = val
    
    @property
    def number(self) -> int:
        """Alias to self.logicalIndex"""
        return self.logicalIndex

    @property
    def physicalIndex(self) -> int:
        return self._physicalChannelIndex_
    
    @physicalIndex.setter
    def physicalIndex(self, val:int):
        self._physicalChannelIndex_ = val
    
    @property
    def physical(self) -> int:
        """Alias to self.physicalIndex"""
        return self.physicalIndex
    
    @property
    def name(self) -> str:
        return self._adcName_
    
    @name.setter
    def name(self, val:str):
        self._adcName_ = val
    
    @property
    def adcName(self)->str:
        """Alias to self.name for backward compatibility"""
        return self.name
    
    @property
    def units(self) -> pq.Quantity:
        return self._adcUnits_
    
    @units.setter
    def units(self, val:pq.Quantity):
        self._adcUnits_ = val

    @property
    def adcUnits(self) -> pq.Quantity:
        return self._adcUnits_

    @property
    def protocol(self) -> ABFProtocol:
        return self._protocol_
    
    @protocol.setter
    def protocol(self, val: ABFProtocol):
        if isinstance(val, ABFProtocol):
            self._protocol_ = val
            

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
        
    An ABF DAC channel can be indentified by its numeric index (logical or physical)
    or by its name.
        • the physical index of a DAC channel is contained in the DAC section of
            the ABF protocol, under the 'nDACNum' attribute, which is a list; the
            whereas the logical index is in fact the index of the physical index 
            in that list.
        
        In general the ABF protocol seems to ascribe the same value to both the 
        logical and physical index of a DAC channel. This is unlike the ADC channels
        where the logical ADC index depends on how many ADC channel are selected
        in the "Inputs" tab of the Clampex protocol editor. In contrast, one cannot
        'select' individual DAC channels in the "Outputs" tab of the protocol
        editor.
        
        • the name of a DAC channel is stored in the strings section of the 
        protocol, in the '_indexedStrings' attribute. A DAC with a physical index 
        𝑖 located at the logical index 𝑗 in 'nDACNum' has its name located at
        index 𝑗 in '_indexedStrings'
        
    """
    # NOTE: 2024-02-08 21:40:30
    # it seems to me that in ABF files the DAC channels physical indexes are the 
    # same as the logical indeFxes i.e. they are ALWAYS present in the protocol.
    #
    # This is unlike the ADC channels, where the logical index depends on whether 
    # other input channels are also selected in the "Inputs" tab. In contrast,
    # one cannot "unselect" DACs in the "Outputs" tab — they always seem to be
    # present. Instead, their analog waveform can be turned ON/OFF thus controlling
    # whether individual DACs are used for sending analog sommand waveforms or not
    # 
    # Things are different for digital outputs — these are NOT normally sent out
    #   via DAC channels (unless one uses a DAC channel to emulate digital TTLs).
    #   Yet, they appear to be associated with a particular DAC by activating 
    #   the digital output feature in the configruation tab for that DAC output
    #   channel. This may give the false impression that a digital signal IS
    #   carried by / associated with an individual DAC. In reality, it is just 
    #   a (maybe not so) convenient way to configure digital outputs inside the 
    #   analog waveform epochs ascribed to a particular DAC.
    # 
    #
    # NOTE: 2023-09-17 23:41:15
    # index of the DAC where Digital output IS enabled is given by 
    #   annotations["protocol"]["nActiveDACChannel"]
    #       (counter-intuitive: expecting to see this from nDigitalDACChannel and nDigitalEnable
    #       but these seem to be 0 and 1 regardless of which DAC has waveform enabled and dig enabled)
    #
    #  I guess nDigitalEnable is rather to be used as a bool flag indicating
    # that the protocol enables digital signals to be sent to other devices.
    #
    # The index of the DAC where analog waveform is enabled is the κ index in 
    #   annotations["listDACInfo"] where:
    #       annotations["listDACInfo"][κ]["nWaveformEnable"] == 1
    # 
    # there are the following possibilities:
    # Alt waveform  | Alt Dig | DAC waveform enabled | DAC Digital output enabled
    #----------------------------------------------------------------------------
    def __init__(self, obj:typing.Optional[typing.Union[pyabf.ABF, neo.Block]]=None,
                 protocol:typing.Optional[ABFProtocol] = None,
                 dacChannel:int = 0, 
                 physical:bool=False, 
                 physicalIndex:typing.Optional[int]=None,
                 name: typing.Optional[str] = None,
                 units: typing.Optional[typing.Union[str, pq.Quantity]]=pq.dimensionless,
                 dacHoldingLevel:typing.Optional[typing.Union[float,pq.Quantity]] = None,
                 interEpisodeLevel:bool = True,
                 waveFormEnabled:bool=False,
                 waveFormSource:typing.Optional[typing.Union[ABFDACWaveformSource, int]] = None,
                 epochs:typing.Optional[typing.Sequence[ABFEpoch]] = None
                 ):
        
        if protocol is None and isinstance(obj, (pyabf.ABF, neo.Block)):
            protocol = ABFProtocol(obj)

        if not isinstance(protocol, ABFProtocol):
            protocol = None
        
        self._protocol_ = protocol
        
        self._epochs_ = list()
        
        if isinstance(obj, pyabf.ABF):
            abfVer = obj.abfVersion["major"]
            if abfVer == 1:
                raise NotImplementedError(f"ABF version {abfVer} is not supported")
                # TODO finalize this...
                
            elif abfVer == 2:
                if physical: # specify via its physical index
                    if dacChannel in obj._dacSection.nDACNum:
                        self._physicalChannelIndex_ = dacChannel
                        logical = obj._dacSection.nDACNum.index(dacChannel)
                        self._dacChannel_ = logical
                        
                        dacName = obj._stringsSection._indexedStrings[obj._dacSection.lDACChannelNameIndex[self._dacChannel_]]
                        dacUnits = obj._stringsSection._indexedStrings[obj._dacSection.lDACChannelUnitsIndex[self._dacChannel_]]
                        
                    else:
                        raise ValueError(f"Invalid physical DAC channel index specified ({dacChannel}) for physical DAC channels {obj._dacSection.nDACNum}")

                else: # specify via its logical index
                    if dacChannel in range(len(obj._dacSection.nDACNum)):
                        self._dacChannel_ = dacChannel
                        self._physicalChannelIndex_ = obj._dacSection.nDACNum[dacChannel]
                        dacName = obj._stringsSection._indexedStrings[obj._dacSection.lDACChannelNameIndex[self._dacChannel_]]
                        dacUnits = obj._stringsSection._indexedStrings[obj._dacSection.lDACChannelUnitsIndex[self._dacChannel_]]
                        
                    else:
                        raise ValueError(f"Invalid logical DAC channel index specified {dacChannel} for {len(obj._dacSection.nDACNum)} channels")
                        self._dacChannel_ = None
                        self._physicalChannelIndex_ = None
                        dacName =""
                        dacUnits = ""
                
                self._dacName_ = dacName 
                self._dacUnits_ = scq.unitQuantityFromNameOrSymbol(dacUnits)
                self._dacHoldingLevel_ = float(obj._dacSection.fDACHoldingLevel[self._dacChannel_]) * self._dacUnits_
                self._interEpisodeLevel_ = bool(obj._dacSection.nInterEpisodeLevel[self._dacChannel_])
                
                # command (analog) waveform flags:
                self._waveformEnabled_ = bool(obj._dacSection.nWaveformEnable[self._dacChannel_])
                
                wsrc = obj._dacSection.nWaveformSource[self._dacChannel_]
                
                if wsrc in ABFDACWaveformSource.values():
                    self._waveformSource_ = ABFDACWaveformSource.type(wsrc)
                else:
                    self._waveformSource_ = ABFDACWaveformSource.none
                
                # # digital (TTL) waveform flags & parameters:
                # NOTE 2023-10-17 17:31:40 FIXME
                # not sure this is the correct approach
                # self._digOutEnabled_ = self._dacChannel_ == self.protocol.activeDACChannelIndex
            else:
                raise NotImplementedError(f"ABF version {abfVer} is not supported")
            
            self._init_epochs_(obj)
            
        elif isinstance(obj, neo.Block):
            assert sourcedFromABF(obj), "Object does not appear to be sourced from an ABF file"
            info_dict = getAcquisitionInfo(obj)
            
            if physical: # specify via its physical index
                p = [v["nDACNum"] for v in info_dict["listDACInfo"]]
                if dacChannel in p:
                    self._physicalChannelIndex_ = dacChannel
                    logical = p.index(dacChannel)
                    self._dacChannel_ = logical
                    dacName = info_dict["listDACInfo"][logical]["DACChNames"].decode()
                    dacUnits = info_dict["listDACInfo"][logical]["DACChUnits"].decode()
                else:
                    self._physicalChannelIndex_ = None
                    self._dacChannel_ = None
                    dacName = ""
                    dacUnits = ""
                    
            else: # specify via its logical index
                if dacChannel in range(len(info_dict["listDACInfo"])):
                    self._dacChannel_ = dacChannel
                    self._physicalChannelIndex_ = info_dict["listDACInfo"][dacChannel]["nDACNum"]
                    dacName = info_dict["listDACInfo"][dacChannel]["DACChNames"].decode()
                    dacUnits = info_dict["listDACInfo"][dacChannel]["DACChUnits"].decode()
                else:
                    self._physicalChannelIndex_ = None
                    self._dacChannel_ = None
                    dacName = ""
                    dacUnits = ""
                    
            self._dacName_ = dacName
            self._dacUnits_ = scq.unitQuantityFromNameOrSymbol(dacUnits)

            self._dacHoldingLevel_ = float(info_dict["listDACInfo"][self._dacChannel_]["fDACHoldingLevel"]) * self._dacUnits_
            self._interEpisodeLevel_ = bool(info_dict["listDACInfo"][self._dacChannel_]["nInterEpisodeLevel"])
            
            if np.abs(self._dacHoldingLevel_).magnitude > 1e6:
                self._dacHoldingLevel_ = np.nan * self._dacUnits_
                
            elif np.abs(self._dacHoldingLevel_).magnitude > 0 and np.abs(self._dacHoldingLevel_).magnitude < 1e-6:
                self._dacHoldingLevel_ = 0.0 * self._dacUnits_
            
            # command (analog) waveform flags:
            self._waveformEnabled_ = bool(info_dict["listDACInfo"][self._dacChannel_]["nWaveformEnable"])
            
            wsrc = info_dict["listDACInfo"][self._dacChannel_]["nWaveformSource"]
            
            if wsrc in ABFDACWaveformSource.values():
                self._waveformSource_ = ABFDACWaveformSource.type(wsrc)
            else:
                self._waveformSource_ = ABFDACWaveformSource.none
                
            # digital (TTL) waveform flags & parameters:
            # NOTE: 2023-10-17 17:31:20 FIXME
            # not sure this is the correct approach
            # self._digOutEnabled_ = self._dacChannel_ == self.protocol.activeDACChannelIndex
            
            self._init_epochs_(obj)
            
        else:
            # print(f"{self.__class__.__name__}.__init__ from atoms")
            if isinstance(physicalIndex, int):
                self._physicalChannelIndex_ = physicalIndex
                
            else:
                raise TypeError(f"Expecting physicalIndex an int; instead, got {type(physicalIndex).__name__}")
            
            if isinstance(dacChannel, int):
                self._dacChannel_ = dacChannel
            else:
                raise TypeError((f"Expecting adcChannel an int; instead, got {type(adcChannel).__name__}"))
            
            # self._physicalChannelIndex_ = self._dacChannel_ = dacChannel
            if isinstance(name, str) and len(name.strip()):
                self._dacName_ = name
            else:
                self._dacName_ = f"DAC_{self._physicalChannelIndex_}"
                
            if isinstance(units, pq.Quantity):
                self._dacUnits_ = units
                
            elif isintance(units, str):
                self._dacUnits_ = scq.unitQuantityFromNameOrSymbol(units)
                
            else:
                self._dacUnits_ = pq.dimensionless

            if isinstance(dacHoldingLevel, pq.Quantity):
                if not scq.unitsConvertible(dacHoldingLevel, self._dacUnits_):
                    raise TypeError(f"'dacHoldingLevel' has wrong units ({dacHoldingLevel.units}) for a DAC output in {self._dacUnits_}")
                dacHoldingLevel = dacHoldingLevel.rescale(self._dacUnits_)
                
                if np.abs(dacHoldingLevel).magnitude > 1e6:
                    self._dacHoldingLevel_ = np.nan * self._dacUnits_
                elif np.abs(dacHoldingLevel).magnitude > 0 and np.abs(dacHoldingLevel).magnitude < 1e-6:
                    self._dacHoldingLevel_ = 0.0 * self._dacUnits_
                else:
                    self._dacHoldingLevel_ = dacHoldingLevel
                    
            elif isinstance(dacHoldingLevel, float):
                if np.abs(dacHoldingLevel) > 1e6:
                    self._dacHoldingLevel_ = np.nan * self._dacUnits_
                elif np.abs(dacHoldingLevel)> 0 and np.abs(dacHoldingLevel) < 1e-6:
                    self._dacHoldingLevel_ = 0.0 * self._dacUnits_
                else:
                    self._dacHoldingLevel_ = dacHoldingLevel
                    
            self._interEpisodeLevel_ = interEpisodeLevel == True
            
            self._waveformEnabled_ = waveFormEnabled == True
            
            if isinstance(waveFormSource, int) and waveFormSource in ABFDACWaveformSource.values():
                self._waveformSource_ = ABFDACWaveformSource(waveFormSource)
                
            elif isinstance(waveFormSource, ABFDACWaveformSource):
                self._waveformSource_ = waveFormSource
                
            else:
                self._waveformSource_ = ABFDACWaveformSource.none
                
            # print(f"\tepochs: {epochs}")
            if isinstance(epochs, (tuple, list)) and all(isinstance(e, ABFEpoch) for e in epochs):
                self._epochs_ = epochs
                
            
    def __repr__(self):
        # ret = f"{self.__class__.__name__} ({super().__repr__()}): \'{self.name}\' (\'{scq.shortSymbol(self.units.symbol)}\') at index {self.physicalIndex} ↔ {self.logicalIndex}  (physical ↔ logical)"
        # return ret
        return f"{self.__class__.__name__} ({super().__repr__()}): \'{self.name}\' (\'{scq.shortSymbol(self.units)}\') at index {self.physicalIndex} ↔ {self.logicalIndex}  (physical ↔ logical)"
        
    def _init_epochs_(self, obj):
        if isinstance(obj, pyabf.ABF):
            self._init_epochs_abf_(obj)
            
        elif isinstance(obj, neo.Block):
            assert sourcedFromABF(obj), "Object does not appear sourced from an ABF file"
            info_dict = getAcquisitionInfo(obj)
                
            digPatterns = getDIGPatterns(obj)
            if self.logicalIndex in info_dict["dictEpochInfoPerDAC"]:
                dacEpochDict = info_dict["dictEpochInfoPerDAC"][self.logicalIndex]
                epochs = list()
                for epochNum, epochDict in dacEpochDict.items():
                    epoch = ABFEpoch()
                    epoch.number = epochNum
                    epoch.type = epochDict["nEpochType"]
                    epoch.firstLevel = epochDict["fEpochInitLevel"] * self.units
                    epoch.deltaLevel = epochDict["fEpochLevelInc"] * self.units
                    epoch.firstDuration = (epochDict["lEpochInitDuration"] / self.samplingRate).rescale(pq.ms)
                    epoch.deltaDuration = (epochDict["lEpochDurationInc"] / self.samplingRate).rescale(pq.ms)
                    epoch.pulsePeriod = (epochDict["lEpochPulsePeriod"] / self.samplingRate).rescale(pq.ms)
                    epoch.pulseWidth = (epochDict["lEpochPulseWidth"] / self.samplingRate).rescale(pq.ms)
                    epoch.mainDigitalPattern = digPatterns[epoch.number]["main"]
                    epoch.alternateDigitalPattern = digPatterns[epoch.number]["alternate"]

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
#                 epoch.type = obj._headerV1.nEpochType[i]
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
                if epochDacNum != self.logicalIndex:
                    continue

                epoch = ABFEpoch()
                epoch.number = obj._epochPerDacSection.nEpochNum[i]
                epoch.type = obj._epochPerDacSection.nEpochType[i]
                epoch.firstLevel = obj._epochPerDacSection.fEpochInitLevel[i] * self.units
                epoch.deltaLevel = obj._epochPerDacSection.fEpochLevelInc[i] * self.units
                epoch.firstDuration = (obj._epochPerDacSection.lEpochInitDuration[i] / self.samplingRate).rescale(pq.ms)
                epoch.deltaDuration = (obj._epochPerDacSection.lEpochDurationInc[i] / self.samplingRate).rescale(pq.ms)
                epoch.pulsePeriod = (obj._epochPerDacSection.lEpochPulsePeriod[i] / self.samplingRate).rescale(pq.ms)
                epoch.pulseWidth = (obj._epochPerDacSection.lEpochPulseWidth[i] / self.samplingRate).rescale(pq.ms)
                epoch.mainDigitalPattern = digPatterns[epoch.number]["main"]
                epoch.alternateDigitalPattern = digPatterns[epoch.number]["alternate"]

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
        
        ret = True
        
        # NOTE: 2023-11-05 21:21:39
        # check equality of properties (descriptors); this includes nSweeps and nADCChannels
        # but EXCLUDE the protocol property because:
        # 1) we can have the same DAC output configuration shared among different
        #    protocols
        # 2) we want to avoid reentrant code when comparing the protocols of 
        #   self and other.
        #
        # Also, EXCLUDE epochs because we check them individualy
        #
        properties = list(filter(lambda x: x[0] not in ("protocol", "epochs"), inspect.getmembers_static(self, lambda x: isinstance(x, property))))
        
        ret &= all(getattr(self, p[0])==getattr(other, p[0]) for p in properties)

        epochs = self.epochs
        other_epochs = other.epochs
        
        if ret:
            if len(epochs) != len(other_epochs):
                return False
        
        if ret:
            ret &= all(self.epochs[k] == other.epochs[k] for k in range(len(self.epochs)))

        # if checked out then verify all epochs Tables are sweep by sweep 
        # identical in all DAC channels, including digital output patterns!
        # WARNING: this is quite time consuming
        # if ret:
        #     ret = all(np.all(self.getEpochsTable(s) == other.getEpochsTable(s)) for s in range(self.protocol.nSweeps))
                    
        return ret
    
    def toHDF5(self, group, name, oname, compression, chunks, track_order,
                       entity_cache) -> h5py.Group:
        """Encodes this ABFOutputConfiguration as a HDF5 Group"""
        
        # NOTE: 2024-07-18 16:01:14
        # I chose Group because we need to store a link to the parent protocol
        # and a Group encoding the list of ABFEpoch objects (the "epochs" attribute)
        
        # print(f"{self.__class__.__name__}.toHDF5: group = {group}, name = {name}, oname = {oname}")
        
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        # print(f"\ttarget_name = {target_name}")
        # print(f"\tobj_attrs {obj_attrs}")
        
        
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity
        
        attrs = list(filter(lambda x: x[0] not in ("protocol", "epochs"), inspect.getmembers_static(self, lambda x: isinstance(x, property))))
        
        objattrs = h5io.makeAttrDict(**dict(map(lambda x: (x[0], getattr(self, x[0])), attrs)))
        obj_attrs.update(objattrs)
            
        entity = group.create_group(target_name, track_order = track_order)
        entity.attrs.update(obj_attrs)
        
        group_obj_class = group.attrs.get("python.class", None)
        if group_obj_class == "builtins.list":
            parent = group.parent   # by definition in HDF5, this is also a Group
                                    # and its attributes must indicate it is an
                                    # ABFProtocol
            parent_obj_class = parent.attrs.get("type_name", None)
            if parent_obj_class == "ABFProtocol":
                entity["protocol"] = parent # soft link here
                
        else:
            # to avoid infinite recursion, we only save the protocol when this DAC
            # is saved as part of a protocol
            scipywarn(f"When saved as independent object, the parent protocol will NOT be saved,\nthus the relationship of this DAC channel with the parent protocol will be lost.")
            h5io.toHDF5(None, entity, name="protocol")
            
        epochs_group = h5io.toHDF5(self.epochs, entity, name="epochs",
                                            oname="epochs",
                                            compression=compression,
                                            chunks=chunks, 
                                            track_order=track_order,
                                            entity_cache=entity_cache,
                                            )
        # epochs = self.epochs
            
        # if isinstance(protocol_attr, tuple) and protocol_attr[0] == "protocol":
        #     # NOTE: 2024-07-18 16:03:58
        #     # see NOTE: 2024-07-18 14:57:47
        #     group_obj_class = group.attrs.get("python.class", None)
        #     if group_obj_class == "builtins.list":
        #         parent = group.parent   # by definition in HDF5, this is also a Group
        #                                 # and its attributes must indicate it is an
        #                                 # ABFProtocol
        #         parent_obj_class = parent.attrs.get("type_name", None)
        #         if parent_obj_class == "ABFProtocol":
        #             entity["protocol"] = parent # soft link here
                
        # if isinstance(epochs_attr, tuple) and epochs_attr[0] == "epochs":
        #     epochs = getattr(self, "epochs")
        #     # NOTE: 2024-07-19 11:02:03 ATTENTION
        #     # this below IS THE CORRECT WAY, as the h5io function will treat the
        #     # epochs list appropriately (including descending into it and encoding
        #     # its elements, recursively) to be compatible with full round Robin
        #     # read/write
        #     epochs_group = h5io.toHDF5(epochs, entity, name="epochs",
        #                                        oname="epochs",
        #                                        compression=compression,
        #                                        chunks=chunks, 
        #                                        track_order=track_order,
        #                                        entity_cache=entity_cache,
        #                                        )
        
        h5io.storeEntityInCache(entity_cache, self, entity)
        
        return entity
    
    @classmethod
    def fromHDF5(cls, entity:h5py.Group, 
                             attrs:typing.Optional[dict]=None, cache:dict = {}):
        # print(f"{cls.__name__}.fromHDF5")
        if entity in cache:
            return cache[entity]
        
        if attrs is None:
            attrs = h5io.attrs2dict(entity.attrs)
        
        dacChannel = attrs.get("physicalIndex", 0)
        logicalIndex = attrs.get("logicalIndex", 0)
        name = attrs.get("name", f"DAC{dacChannel}")
        units = attrs.get("units", pq.dimensionless)
        dacHoldingLevel = attrs.get("dacHoldingLevel", pq.dimensionless)
        interEpisodeLevel = attrs.get("returnToHold", True)
        waveFormEnabled = attrs.get("analogWaveformEnabled", False)
        waveFormSource = attrs.get("analogWaveformSource", 0)
        
        # print(f"waveFormSource = {waveFormSource}")
        
        # print(f"entity/epochs: {entity['epochs']}")
        
        protocol = h5io.fromHDF5(entity["protocol"], cache)
        epochs = h5io.fromHDF5(entity["epochs"], cache)
        
        return cls(obj=None, protocol=protocol, dacChannel=logicalIndex, 
                   physicalIndex = dacChannel, 
                   physical=True,
                   units=units,
                   dacHoldingLevel=dacHoldingLevel, 
                   interEpisodeLevel=interEpisodeLevel,
                   waveFormEnabled=waveFormEnabled, 
                   waveFormSource=waveFormSource,
                   epochs=epochs, name=name)
        
    def is_identical_except_digital(self, other):
        if not isinstance(other, self.__class__):
            return False
        
        properties = inspect.getmembers_static(self, lambda x: isinstance(x, property))
        
        ret = True
        # NOTE: see NOTE: 2023-11-05 21:21:39
        for p in properties:
            if p[0] not in ("protocol", "epochs"):
                # NOTE: 2023-11-05 21:05:46
                # no need to compare all; just compare until first distinct one
                if getattr(self, p[0]) != getattr(other, p[0]):
                    return False
        # check equality of properties (descriptors); this includes nSweeps and nADCChannels
        # ret = all(np.all(getattr(self, p[0]) == getattr(other, p[0])) for p in properties)
        
        epochs = self.epochs
        other_epochs = other.epochs
        if ret:
            if len(epochs) != len(other_epochs):
                return False
        
        if ret:
            for k in range(len(epochs)):
                if not epochs[k].is_identical_except_digital(other_epochs[k]):
                    return False
                    
        return ret
    
    def has_identical_epochs_table(self, other:ABFOutputConfiguration, 
                                   sweep:int = 0, includeDigitalPattern:bool=True):
        
        if not isinstance(other, ABFOutputConfiguration):
            return False
        
        return np.all(self.getEpochsTable(sweep, includeDigitalPattern = includeDigitalPattern) == 
                      other.getEpochsTable(sweep, includeDigitalPattern = includeDigitalPattern))
        
    @property
    def protocol(self) -> ABFProtocol:
        return self._protocol_
    
    @protocol.setter
    def protocol(self, val:ABFProtocol):
        self._protocol_ = val
        # if isinstance(val, ABFProtocol) and self in val.outputs:
        
    @property
    def returnToHold(self) -> bool: 
        """True if the command waveform return to last epoch's level.
        This is specific to the DAC output.
        """
        return self._interEpisodeLevel_
    
    @returnToHold.setter
    def returnToHold(self, val:bool):
        self._interEpisodeLevel_ = val == True
    
    @property
    def epochs(self) -> list:
        """List of ABFEpoch objects defined for this DAC channel"""
        return self._epochs_
    
    @epochs.setter
    def epochs(self, val:typing.Sequence[ABFEpoch]):
        if isinstance(val, (tuple, list)) and all(isinstance(v, ABFEpoch) for v in val):
            self._epochs_[:] = val[:]
    
    def getEpochsWithDigitalOutput(self) -> typing.List[ABFEpoch]:
        """List of ABF Epochs emitting digital signals (TTLs)"""
        return [e for e in self.epochs if len(e.getUsedDigitalOutputChannels())]
    
    def getEpochsWithTTLWaveforms(self, sweep:int = 0,
                                  indexes: bool=False,
                                  train: typing.Optional[bool] = None) -> typing.List[ABFEpoch]:
        """Returns the epochs (or their indices) where the DAC emits TTL-emulating wavforms.
        A an epoch with TTL-emulating waveform(s) has:
        • type ABFEpochType.Pulse
        • First level       != 0 (NOTE: this should be ± 5 V but this is not
                                    enforced here)
        • Delta level       == 0
        • Delta duration    == 0
        • all digital outputs are 0 (off)
        
        See also ABFEpoch.emulatesTTL()
        
        Furthermore, the DACs index must be > 2 (the first two DACs are ALWAYS 
        used for clamping waveforms, not for trigger emulation)
        
        """
        isAlternateWaveorm = self.alternateDACOutputStateEnabled and sweep % 2 > 0
        ret = list()
        
        return [e for e in self.epochs if e.emulatesTTL]
    
    def getDigitalTriggerEvent(self, sweep:int = 0, digChannel:typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
                         eventType:TriggerEventType = TriggerEventType.presynaptic,
                         label:typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
                         name:typing.Optional[str] = None,
                         enableEmptyEvent:bool=True) -> TriggerEvent|None:
        """Generates TriggerEvent objects from all epochs in the protocol.
        These may be empty if the protocol epochs do not define digital patterns.
        (NOTE: 'enableEmptyEvent' parameter is not yet used)
        
        See also: self.getEpochDigitalTriggerEvent
        """
        usedDigs = list(itertools.chain.from_iterable([epoch.getUsedDigitalOutputChannels() for epoch in self.epochs]))
        
        if isinstance(digChannel, int):
            if digChannel not in usedDigs:
                raise ValueError(f"Invalid DIG channel index {digChannel}")
            
            digChannel = (digChannel,)
            
        elif isinstance(digChannel, (list, tuple)) and all(isinstance(v, int) for v in digChannel):
            if all(v not in usedDigs for v in digChannel):
                raise ValueError(f"Invalid DIG channel indexes {digChannel}")
            
            digChannel = tuple(sorted(set(digChannel)))
            
        elif digChannel is None:
            digChannel = tuple(sorted(set(usedDigs)))
            
        else:
            raise TypeError(f"expecting digChannel an int or sequence of int; instead got {digChannel}")
            
        channel_times = [list()] * len(digChannel)
        
        # print(f"{self.__class__.__name__}.getDigitalTriggerEvent(sweep={sweep}) -> digChannel: {digChannel}")
        for epoch in self.epochs:
            if epoch.type not in (ABFEpochType.Step, ABFEpochType.Pulse):
                continue
            digPattern = tuple(itertools.chain.from_iterable(map(lambda x: reversed(x), self.getEpochDigitalPattern(epoch, sweep))))
            digChannelValue = tuple(digPattern[chnl] for chnl in digChannel)
            # print(f"{self.__class__.__name__}.getDigitalTriggerEvent(sweep={sweep}) -> epoch: {epoch.epochNumber}, digPattern: {digPattern}, digChannelValue: {digChannelValue}")
            
            # digChannelValue = [tuple(reversed(self.getEpochDigitalPattern(epoch, sweep)[chnl // 4]))[chnl] for chnl in digChannel]
            # print(f"digChannelValue = {digChannelValue}" )
            for k, chnl in enumerate(digChannel):
                # print(f"k: {k} -> chnl: {chnl}")
                # if chnl >= len(digChannelValue):
                #     continue
                # if digChannelValue[chnl] == "*":
                if digChannelValue[k] == "*":
                    channel_times[k].extend([x.rescale(pq.s) for x in self.getEpochActualPulseTimes(epoch, sweep)])
                    
                elif digChannelValue[k] == 1:
                    channel_times[k].extend([self.getEpochActualStartTime(epoch, sweep).rescale(pq.s)])
                    
        # print(f"{self.__class__.__name__}.getDigitalTriggerEvent(sweep={sweep}) -> channel_times: {channel_times}")
        trigs = [TriggerEvent(times=channel_times[k], units = pq.s, event_type = eventType, 
                            name=name, labels = label) for k in range(len(channel_times))]

        # NOTE: 2023-10-31 15:00:10
        # remove duplicates
        # CAUTION: TriggerEvent objects are not hashable hence cannot use 
        # set logic to achieve this
        uniqueTrigs = list()

        for k,t in enumerate(trigs):
            if k == 0:
                uniqueTrigs.append(t)
            else:
                if t not in uniqueTrigs:
                    uniqueTrigs.append(t)
                    
        if len(uniqueTrigs) == 1:
            return uniqueTrigs[0]
        
        else:
            return uniqueTrigs
        
#         # if isinstance(digChannel, int):
#         if len(digChannel) == 1:
#             times = list()
#             for epoch in self.epochs:
#                 if epoch.type not in (ABFEpochType.Step, ABFEpochType.Pulse):
#                     continue
#                 
#                 digPattern = tuple(itertools.chain.from_iterable(map(lambda x: reversed(x), self.getEpochDigitalPattern(epoch, sweep))))
#                 digChannelValue = digPattern[digChannel[0]]
#                 
#                 if digChannelValue == "*": # ⟹ pulse train
#                     times.extend([x.rescale(pq.s) for x in self.getEpochActualPulseTimes(epoch, sweep)])
#                 
#                 elif digChannelValue == 1: # ⟹ single TTL pulse ⇒ take the epoch's
#                     # onset time as a trigger event; in theory, a device may 
#                     # actually require a "ON" state during which it may perform
#                     # some ciclic function etc;
#                     # regardless, I think is OK to consider the onset time of
#                     # of the epoch as the time of "OFF"-"ON" transition, and
#                     # the time of the trigger.
#                     
#                     times.extend([self.getEpochActualStartTime(epoch, sweep).rescale(pq.s)])
#                     
#                 else:
#                     continue
#                 
#             # print(f"{self.__class__.__name__}.getDigitalTriggerEvent(sweep={sweep}) -> times: {times}")
#             
#             if len(times) == 0 and not enableEmptyEvent:
#                 return
#             
#             trig = TriggerEvent(times=times, units = pq.s, labels = label, name=name,
#                                 event_type = eventType)
#         
#             if isinstance(label, str) and len(label.strip()):
#                 trig.labels = [f"{label}{k}" for k in range(trig.times.size)]
# 
#             return trig
#         
#         # elif isinstance(digChannel, (list, tuple)) and all(isinstance(v, int) for v in digChannel):
#         else:
#             channel_times = [list()] * len(digChannel)
#             
#             # print(f"{self.__class__.__name__}.getDigitalTriggerEvent(sweep={sweep}) -> digChannel: {digChannel}")
#             for epoch in self.epochs:
#                 if epoch.type not in (ABFEpochType.Step, ABFEpochType.Pulse):
#                     continue
#                 digPattern = tuple(itertools.chain.from_iterable(map(lambda x: reversed(x), self.getEpochDigitalPattern(epoch, sweep))))
#                 digChannelValue = tuple(digPattern[chnl] for chnl in digChannel)
#                 # print(f"{self.__class__.__name__}.getDigitalTriggerEvent(sweep={sweep}) -> epoch: {epoch.epochNumber}, digPattern: {digPattern}, digChannelValue: {digChannelValue}")
#                 
#                 # digChannelValue = [tuple(reversed(self.getEpochDigitalPattern(epoch, sweep)[chnl // 4]))[chnl] for chnl in digChannel]
#                 # print(f"digChannelValue = {digChannelValue}" )
#                 for k, chnl in enumerate(digChannel):
#                     # print(f"k: {k} -> chnl: {chnl}")
#                     # if chnl >= len(digChannelValue):
#                     #     continue
#                     # if digChannelValue[chnl] == "*":
#                     if digChannelValue[k] == "*":
#                         channel_times[k].extend([x.rescale(pq.s) for x in self.getEpochActualPulseTimes(epoch, sweep)])
#                         
#                     elif digChannelValue[k] == 1:
#                         channel_times[k].extend([self.getEpochActualStartTime(epoch, sweep).rescale(pq.s)])
#                         
#             # print(f"{self.__class__.__name__}.getDigitalTriggerEvent(sweep={sweep}) -> channel_times: {channel_times}")
#             trigs = [TriggerEvent(times=channel_times[k], units = pq.s, event_type = eventType, 
#                                 name=name, labels = label) for k in range(len(channel_times))]
# 
#             # NOTE: 2023-10-31 15:00:10
#             # remove duplicates
#             # CAUTION: TriggerEvent objects are not hashable hence cannot use 
#             # set logic to achieve this
#             uniqueTrigs = list()
# 
#             for k,t in enumerate(trigs):
#                 if k == 0:
#                     uniqueTrigs.append(t)
#                 else:
#                     if t not in uniqueTrigs:
#                         uniqueTrigs.append(t)
#                         
#             if len(uniqueTrigs) == 1:
#                 return uniqueTrigs[0]
#             
#             else:
#                 return uniqueTrigs
            
    
    def getEpochDigitalTriggerEvent(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int = 0, 
                             digChannel:typing.Union[int, typing.Sequence[int]] = 0,
                             eventType:TriggerEventType = TriggerEventType.presynaptic,
                             label:typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
                             name:typing.Optional[str] = None,
                             enableEmptyEvent:bool=True) -> typing.Union[TriggerEvent, typing.List[TriggerEvent]]:
        """
        TODO: Move this code to ABFProtocol, thus breaking the need to store
        a reference to the protocol in this ABFOutputConfiguration instance.
        
        Trigger events from an individual Step or Pulse-type ABF Epoch.
        
        Parameters:
        ------------
        
        epoch: ABFEpoch, int index of ABFEpoch or letter of ABFEpoch
        
        sweep: index of sweep (0-based)
        
        digChannel: int or sequence of int; index or indices of digital output
            channels where a TTL output is expected.
        
            Specifying a tuple of int here (e.g., (0,1)) is convenient for the 
            situation where alternate digital outputs are used to generate the 
            same type of TriggerEvent (such as presynaptic). Such alternate 
            digital outputs will be emitted on distinct digital output channels, 
            even though they both represent the same type of event (in this case, 
            presynaptic pulses). This scenario can be used for Hebbian synaptic    
            plasticity experiments where synaptic responses are recorded 
            alternatively from two distinct presynaptic pathways converging on 
            the same cell.
        
        sweep: int, index of the sweep in the protocol. 
            Normally, an ABF Epoch (and any digital output patterns defined 
            within) is repeated in each sweep - hence the sweep index is 
            irrelevant. 
    
            When alternate digital outputs are enabled, the sweep index BECOMES
            RELEVANT, as the main digital pattern is emitted during sweeps with 
            even indices (0, 2, 4, …) whereas the alternate digital pattern is
            emitted during sweeps with odd indices (1, 3, 5, …).
        
            Such scenario is also likely to involve distinct digital output 
            channels in the main and the alternate digital patterns. In this 
            case it is recommended to specify BOTH digital output channels used
            in the protocol (see above).
        
        eventType: optional; default is TriggerEventType.presynaptic
            Necessary in building a TriggerProtocol for the experiment.
        
        label: The label(s) for each individual time stamp in the resulting
            TriggerEvent object
        
        name: The name of the resulting TriggerEvent object.
        
        enableEmptyEvent: when True (default) the function will return an empty
            TriggerEvent (i.e. without any time stamps) in any of the following
            cases:
        
            • the ABF Epoch is neither a Step or Pulse Type
        
            • Neither of the digital channels given in digChannel are active in
                the epoch during the specified sweep
            
        Returns:
        ========
        
        A TriggerEvent object. This may be empty, or None - see 'enableEmptyEvent'
        
        If the epoch has digital outputs, the time stamps for the trigger
        events will be set by the timings of the digital TTL signals during
        
        NOTE 1: Digital signals (triggers) are emitted during epochs defined on 
        the "active" DAC
        
        NOTE 2: An ABF Epoch supports sending digital signals simultaneously via 
        more than one digital output channel; however, Clampex does not support
        defining different timings for distinct digital output channels, EXCEPT
        for for the case where digital train and digital pulse are emitted by
        distinct channels.
        
        In such case, the digital train emitted on one channel is interpreted
        as a sequence of trigger events, whereas the digital pulse emitted on 
        a distinct digital channel can be intepreted here as a single trigger
        event, with the onset being equal to the timing of the first pulse in 
        the digital train (both being defined by the epoch's onset time in the 
        sweep0).
        
        Cases like this one are ambiguous and are best avoided, if possible.
        
        However, because distinct digital output channels can drive different
        devices, it is necessary to specify their "semantic" within the experiment
        (i.e. the trigger event type for a specific digital output channel).
        
        In synaptic plasticity experiments it is usual to use two digital output
        channels to send digital trains ALTERNATIVELY to two pathways. Since
        both outputs are effectively presynaptic stimuli, one can specify
        the output indices by passing a tuple of int to the digChannel parameter.
        
        """
        if isinstance(epoch, (str, int)):
            e = self.getEpoch(epoch)
            
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        if epoch.type not in (ABFEpochType.Step, ABFEpochType.Pulse):
            return TriggerEvent(event_type = eventType, name=name, labels = label) if enableEmptyEvent else None
        
        usedDigs = epoch.getUsedDigitalOutputChannels()
        
        if isinstance(digChannel, int) and digChannel not in usedDigs:
            return TriggerEvent(event_type = eventType, name=name, labels = label) if enableEmptyEvent else None
        
        elif isinstance(digChannel, (list, tuple)) and all(isinstance(v, int) for v in digChannel):
            if any(v not in usedDigs for v in digChannel):
                return TriggerEvent(event_type = eventType, name=name, labels = label) if enableEmptyEvent else None
            
        elif digChannel is None:
            digChannel = usedDigs
        
        if isinstance(digChannel, int):
            times = list()
            
            digPattern = self.getEpochDigitalPattern(epoch, sweep)[digChannel // 4]
            
            digChannelValue = tuple(reversed(digPattern))[digChannel]
            
            if digChannelValue == "*": # ⟹ pulse train
                times = [x.rescale(pq.s) for x in self.getEpochActualPulseTimes(epoch, sweep)]
            
            elif digChannelValue == 1: # ⟹ single TTL pulse ⇒ take the onset time as
                                    # a trigger event; in theory, a device may 
                                    # actually require a "ON" state during which 
                                    # it performs some ciclic function etc;
                                    # regardless of this we may conosider the onset
                                    # of the "ON" state as a trigger for such device
                times = [self.getEpochActualStartTime(epoch, sweep).rescale(pq.s)]
                
            trig = TriggerEvent(times=times, units = pq.s, event_type = eventType, 
                                name=name, labels = label) if enableEmptyEvent else None
            
            if isinstance(trig, TriggerEvent) and trig.size > 0:
                # see BUG: 2023-10-03 17:57:30 in triggerevent.TriggerEvent.__new__ 
                if isinstance(label, str) and len(label.strip()):
                    trig.labels = [f"{label}{k}" for k in range(trig.times.size)]
                
            return trig
        
        elif isinstance(digChannel, (list, tuple)) and all(isinstance(v, int) for v in digChannel):
            digChannelValue = [tuple(reversed(self.getEpochDigitalPattern(epoch, sweep)[chnl // 4]))[chnl] for chnl in digChannel]
            
            trigs = list()
            
            for k,chnl in enumerate(digChannel):
                times = list()
                
                if digChannelValue[k] == "*":
                    times = [x.rescale(pq.s) for x in self.getEpochActualPulseTimes(epoch, sweep)]
                    
                elif digChannelValue[k] == 1:
                    times = [self.getEpochActualStartTime(epoch, sweep).rescale(pq.s)]
                    
                trig = TriggerEvent(times=times, units = pq.s, event_type = eventType, 
                                    name=name, labels = label) if enableEmptyEvent else None
                
                if isinstance(trig, TriggerEvent) and trig.size > 0:
                    # see BUG: 2023-10-03 17:57:30 in triggerevent.TriggerEvent.__new__ 
                    if isinstance(label, str) and len(label.strip()):
                        trig.labels = [f"{label}{k}" for k in range(trig.times.size)]
                        
                    trigs.append(trig)
                    
            # NOTE: 2023-10-31 15:01:50 see NOTE: 2023-10-31 15:00:10
            uniqueTrigs = list()

            for k,t in enumerate(trigs):
                if k == 0:
                    uniqueTrigs.append(t)
                else:
                    if t not in uniqueTrigs:
                        uniqueTrigs.append(t)
                        
            if len(uniqueTrigs) == 1:
                return uniqueTrigs[0]
            
            else:
                return uniqueTrigs
            
        else:
            raise TypeError(f"digChannel expected an int or a sequence of int; instead, got {digChannel}")
    
    def getEpochsTable(self, sweep:int = 0, includeDigitalPattern:bool=True):
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
                epochDigPattern = self.getEpochDigitalPattern(epoch, sweep)
                epValues = [epoch.typeName, epoch.firstLevel, epoch.deltaLevel,
                            epoch.firstDuration, self.getEpochFirstDurationSamples(epoch),
                            epoch.deltaDuration, self.getEpochDeltaDurationSamples(epoch),
                            self.getEpochActualDuration(epoch, sweep),
                            self.getEpochActualDurationSamples(epoch, sweep),
                            "".join(map(str, epochDigPattern[0])), 
                            "".join(map(str, epochDigPattern[1])),
                            epoch.pulseFrequency,
                            epoch.pulsePeriod, self.getEpochPulsePeriodSamples(epoch),
                            epoch.pulseWidth, self.getEpochPulseWidthSamples(epoch),
                            self.getEpochPulseCount(epoch, sweep)]
            else:
                epValues = [epoch.typeName, epoch.firstLevel, epoch.deltaLevel,
                            epoch.firstDuration, self.getEpochFirstDurationSamples(epoch),
                            epoch.deltaDuration, self.getEpochDeltaDurationSamples(epoch),
                            self.getEpochActualDuration(epoch, sweep),
                            self.getEpochActualDurationSamples(epoch, sweep),
                            epoch.pulseFrequency,
                            epoch.pulsePeriod, self.getEpochPulsePeriodSamples(epoch),
                            epoch.pulseWidth, self.getEpochPulseWidthSamples(epoch),
                            self.getEpochPulseCount(epoch, sweep)]
                    
            
            epochData[epoch.letter] = epValues
            
        return pd.DataFrame(epochData, index = rowIndex)
        
    def getEpoch(self, e:typing.Union[str, int]):
        if isinstance(e, str):
            e = getEpochNumberFromLetter(e)
            
        if e < 0 or e >= len(self.epochs):
            return
        
        return self.epochs[e]
    
    def getEpochRelativeStartTime(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int = 0) -> pq.Quantity:
        """Starting time of the epoch, relative to sweep start.
        WARNING: Does NOT take into account the holding time (1/64 of sweep samples),
        therefore the response to the epoch's waveform, as recorded in the ADC
        signal, will appear delayed relative to the epoch's start by the holding time.
        
        Depending what you need, you may want to use self.getEpochActualRelativeStartTime
        
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
        return np.sum([self.getEpochActualDuration(e_, sweep).rescale(units) for e_ in self.epochs[:epoch.epochNumber]]) * units
    
    def getEpochActualRelativeStartTime(self, epoch:typing.Union[ABFEpoch, str, int], 
                                        sweep:int = 0) -> pq.Quantity:
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
        return np.sum([self.getEpochActualDuration(e_, sweep).rescale(units) for e_ in self.epochs[:epoch.epochNumber]]) * units + self.holdingTime
        
    def getEpochRelativeStartSamples(self, epoch:typing.Union[ABFEpoch, str, int], 
                                     sweep:int=0) -> int:
        """Number of samples from the start of the sweep to the start of epoch.
        WARNING: Like self.getEpochRelativeStartTime, does NOT take into account 
        the holding time; you may want to use self.epochActualRelativeStartsSamples
        
        
        """
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        return np.sum([self.getEpochActualDurationSamples(e_, sweep) for e_ in self.epochs[:epoch.epochNumber]])
    
    def getEpochActualRelativeStartSamples(self, epoch:typing.Union[ABFEpoch, str, int],
                                           sweep:int=0) -> int:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        return np.sum([self.getEpochActualDurationSamples(e_, sweep) for e_ in self.epochs[:epoch.epochNumber]]) + self.holdingSampleCount
        
    def getEpochStartTime(self, epoch:typing.Union[ABFEpoch, str, int], 
                          sweep:int = 0) -> pq.Quantity:
        """Starting time of the epoch, relative to the start of recording.
        WARNING: Does NOT take into account the holding time (1/64 of sweep samples),
        therefore the respoonse to the epoch's waveform, as recorded in the ADC 
        signal, will appear delayed relative to the epoch's start by the holding time.
        
        Depending what you need, you may want to use self.getEpochActualStartTime
        """
        # units = epoch.firstDuration.units
        return self.getEpochRelativeStartTime(epoch, sweep) + self.protocol.sweepInterval * sweep
    
    def getEpochActualStartTime(self, epoch:typing.Union[ABFEpoch, str, int], 
                                sweep:int = 0) -> pq.Quantity:
        """Starting time of the epoch, relative to the start of recording.
        Takes into account the sweep holding time.
        """
        return self.getEpochActualRelativeStartTime(epoch, sweep) + self.protocol.sweepInterval * sweep
        
    def getEpochStartSamples(self, epoch:typing.Union[ABFEpoch, str, int], 
                             sweep:int=0) -> int:
        """Number of samples from start fo recording to the epoch.
        WARNING: Like self.epochStartSamples, does NOT take into account 
        the holding time; you may want to use self.epochActualStartSamples.
        
        """
        return self.getEpochRelativeStartSamples(epoch, sweep) + self.protocol.sweepSampleCount * sweep
    
    def getEpochActualStartSamples(self, epoch:typing.Union[ABFEpoch, str, int], 
                                   sweep:int=0) -> int:
        """Number of samples from start fo recording to the epoch.
        Takes into account the sweep holding time.
        """
        return self.getEpochActualRelativeStartSamples(epoch, sweep) + self.protocol.sweepSampleCount * sweep
    
    def getEpochActualDuration(self, epoch:typing.Union[ABFEpoch, str, int], 
                               sweep:int=0) -> pq.Quantity:
        """Actual epoch duration (in ms) for the given sweep.
        Takes into account first duration and delta duration"""
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        return epoch.firstDuration + sweep * epoch.deltaDuration
        
    def getEpochActualDurationSamples(self, epoch:typing.Union[ABFEpoch, str, int], 
                                      sweep:int=0) -> int:
        """Actual epoch duration (in samples) for the given sweep.
        Takes into account first duration and delta duration"""
        return scq.nSamples(self.getEpochActualDuration(epoch, sweep), self.samplingRate)
    
    def getEpochFirstDurationSamples(self, epoch:typing.Union[ABFEpoch, str, int]) -> int:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        return scq.nSamples(epoch.firstDuration, self.samplingRate)
        
    def getEpochDeltaDurationSamples(self, epoch:typing.Union[ABFEpoch, str, int]) -> int:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        return scq.nSamples(epoch.deltaDuration, self.samplingRate)
    
    def getEpochPulseWidthSamples(self, epoch:typing.Union[ABFEpoch, str, int]) -> int:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        return scq.nSamples(epoch.pulseWidth, self.samplingRate)
    
    def getEpochPulsePeriodSamples(self, epoch:typing.Union[ABFEpoch, str, int]) -> int:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        return scq.nSamples(epoch.pulsePeriod, self.samplingRate)
    
    def getEpochPulseCount(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int = 0) -> int:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        if float(epoch.pulsePeriod) == 0.:
            return 0
        
        return int(self.getEpochActualDuration(epoch,sweep)/epoch.pulsePeriod)

    def getEpochActualPulseTimes(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int = 0) -> list:
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
        pc = self.getEpochPulseCount(epoch, sweep)
        
        if pc == 0:
            return list()

        t0 = self.getEpochActualStartTime(epoch, sweep)

        return [t0 + p * epoch.pulsePeriod for p in range(pc)]
    
    def getEpochRelativePulseTimes(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int = 0) -> list:
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        pc = self.getEpochPulseCount(epoch, sweep)
        if pc == 0:
            return list()
        
        # t0 = self.epochStartTime(epoch, sweep)
        t0 = self.getEpochRelativeStartTime(epoch, sweep)

        return [t0 + p * epoch.pulsePeriod for p in range(pc)]

    def getEpochAnalogWaveform(self, epoch:typing.Union[ABFEpoch, str, int], previousLevel:pq.Quantity, 
                      sweep:int = 0, lastLevelOnly:bool=False) -> pq.Quantity:
        """
        TODO: Move this code to ABFProtocol, thus breaking the need to store
        a reference to the protocol in this ABFOutputConfiguration instance.
        
    
        Realizes the analog waveform associated with a single epoch.
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
            
        if self.protocol:
            isAlternateWaveform = self.alternateDACOutputStateEnabled and sweep % 2 > 0
            
        actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
        epochSamplesCount = scq.nSamples(actualDuration, self.samplingRate)
        actualLevel = epoch.firstLevel + sweep * epoch.deltaLevel
        
        if epoch.type == ABFEpochType.Step:
            wave = actualLevel if lastLevelOnly else np.full([epochSamplesCount, 1], float(actualLevel)) * self.units
        
        elif epoch.type == ABFEpochType.Ramp:
            wave = actualLevel if lastLevelOnly else np.linspace(previousLevel, actualLevel, epochSamplesCount)[:,np.newaxis]
            
        elif epoch.type == ABFEpochType.Pulse:
            pulsePeriod = self.getEpochPulsePeriodSamples(epoch)
            pulseSamples = self.getEpochPulseWidthSamples(epoch)
            pulseCount = self.getEpochPulseCount(epoch)
            
            if lastLevelOnly:
                wave = actualLevel
            else:
                wave = np.full([epochSamplesCount, 1], float(previousLevel)) * self.units
                
                for pulse in range(pulseCount):
                    p1 = int(pulsePeriod * pulse)
                    p2 = int(p1 + pulseSamples)
                    wave[p1:p2] = actualLevel
                        
        elif epoch.type == ABFEpochType.Triangular:
            pulsePeriod = self.getEpochPulsePeriodSamples(epoch)
            pulseSamples = self.getEpochPulseWidthSamples(epoch)
            pulseCount = self.getEpochPulseCount(epoch)
            
            if lastLevelOnly:
                wave = actualLevel
            else:
                wave = np.full([epochSamplesCount, 1], float(previousLevel)) * self.units
                            
                for pulse in range(pulseCount):
                    p1 = int(pulsePeriod * pulse)
                    p2 = int(p1 + pulseSamples)
                    p3 = int(p1 + pulsePeriod)
                    
                    wave[p1:p2] = np.linspace(previousLevel, actualLevel, pulseSamples)[:,np.newaxis]
                    wave[p2:p3] = np.linspace(actualLevel, previousLevel, int(pulsePeriod - pulseSamples))[:,np.newaxis]
            
        elif epoch.type == ABFEpochType.Cosine:
            if lastLevelOnly:
                wave = actualLevel
            else:
                pulseCount = self.getEpochPulseCount(epoch)
                levelDelta = float(actualLevel) - float(previousLevel)
                values = np.linspace(0, 2*pulseCount*np.pi, epochSamplesCount) + np.pi
                cosines = (np.cos(values) * levelDelta / 2 + levelDelta/2 ) * self.units + previousLevel
                wave = cosines[:, np.newaxis]
            
        elif epoch.type == ABFEpochType.Biphasic:
            pulsePeriod = self.getEpochPulsePeriodSamples(epoch)
            pulseSamples = self.getEpochPulseWidthSamples(epoch)
            pulseCount = self.getEpochPulseCount(epoch)
            levelDelta = actualLevel - previousLevel
            
            if lastLevelOnly:
                wave = actualLevel
            else:
                wave = np.full([epochSamplesCount, 1], float(previousLevel)) * self.units
                
                for pulse in range(pulseCount):
                    p1 = int(pulsePeriod * pulse)
                    p3 = int(p1 + pulseSamples)
                    p2 = int((p1+p3)/2)
                    wave[p1:p2] = previousLevel + levelDelta
                    wave[p2:p3] = previousLevel - levelDelta
            
        else:
            wave = np.full([epochSamplesCount, 1], float(previousLevel)) * self.units
            
        return wave
    
    def getEpochDigitalWaveform(self, epoch:typing.Union[ABFEpoch, str, int], /, 
                                sweep:int = 0, 
                                digChannel: typing.Optional[typing.Union[int, typing.Sequence[int]]] = None, 
                                lastLevelOnly:bool=False,
                                separateWavePerChannel:bool=True,
                                digOFF:typing.Optional[pq.Quantity]=None,
                                digON:typing.Optional[pq.Quantity]=None,
                                trainOFF:typing.Optional[pq.Quantity]=None,
                                trainON:typing.Optional[pq.Quantity]=None,
                                returnLevels:bool=False) -> typing.Union[pq.Quantity, typing.Sequence[pq.Quantity]]:
        """Waveform with the TTL signals emitted by the epoch.
        
        Mandatory positional parameters:
        --------------------------------
        
        epoch: the ABF epoch that is queried
        
        Named parameters:
        -----------------
        
        sweep: the index of the ABF sweep (digital outputs may be specific to the 
                sweep index, when alternate digital patterns are enabled in the 
                ABF protocol)
        
                Default is 0 (first sweep)
        
        digChannel:default is None, meaning that the function returns a waveform
            for each digital output channel that is active during this epoch
            (and during the specified sweep)
        
        lastLevelOnly: default is False; when True, just generate a constant wave
            with the value of the last digital logic level; that is, OFF for digital 
            pulse or train. NOTE that the actual value of this level is either 0 V 
            or 5 V, depending on the values of protocol.digitalHoldingValue(channel) 
            and protocol.digitalTrainActiveLogic.
        
            See self.getDigitalLogicLevels, self.getDigitalPulseLogicLevels,
            and self.getDigitalTrainLogicLevels
        
        separateWavePerChannel: default is False. 
            When False, and more than one digChannel is queried, the function 
            returns a Quantity array with one channel-specific waveform per
            column.
        
            When True, the function returns a list of vector waveforms (one per 
            channel)
        
        digOFF, digON, trainOFF, trainON: scalar Python Quantities representing
            the logic levels for digital pulses and trains, respectively; when 
            they are None (default) the function will query these values from the 
            ABF protocol that associates this DAC output.
        
        returnLevels: default False; When True, returns the waves and the digOFF, 
        digON, trainOFF and trainON logical levels
        
        Returns:
        --------
        waves, [digOFF, digON, trainOFF, trainON], where:
        
        waves: list of Python quantities (Quantity arrays) whith the digital waveforms
        for each specified DIG channel are returned.
        
            The list contains:
                • a single 1D Quantity array, when digChannel parameter is an int 
                    (but see below)
                • as many 1D Quantity arrays as DIG channel indexes specified in 
                    digChannel parameter, and separateWavePerChannel is True
                • a single 2D Quantity array with shape (N,M) where:
                    ∘ N is the number of samples recorded by the epoch
                    ∘ M is the number of DIG channels specified in digChannel
        
            The list is EMPTY when not all DIG channel indexes specified
                    in the digChannel parameter are used by the epoch.
        
        digOFF, digON, trainOFF, trainON - scalar Python Quantities with the values
            of the logical levels for digital pulse and digital train.
        
            NOTE:
            1. trainOFF and trainON are None when the epoch emits only digital pulses
            2. digOFF and digON are None when the epoch emits only digital pulse trains
            3. Within a given epoch, these levels are identical for all DIG channels.
        
        When not all DIG channel indexes are used by the epoch to emit digital signals
        the function returns None
    
        """
        if isinstance(epoch, (int, str)):
            e = self.getEpoch(epoch)
            if e is None:
                raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
            
            epoch = e
            
        actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
        epochSamplesCount = scq.nSamples(actualDuration, self.samplingRate)
        pulsePeriod = self.getEpochPulsePeriodSamples(epoch)
        pulseSamples = self.getEpochPulseWidthSamples(epoch)
        pulseCount = self.getEpochPulseCount(epoch)

        usedDigs = epoch.digitalOutputChannels
        
        if len(usedDigs) == 0:
            scipywarn(f"The epoch {epoch.number} ({epoch.letter}) of DAC {self.physicalIndex} ({self.name}) does NOT emit digital outputs")
            return 
        
        if isinstance(digChannel, int):
            if digChannel not in usedDigs:
                scipywarn(f"The DIG channel {digChannel} is not used in the epoch {epoch.number} ({epoch.letter}) of DAC {self.physicalIndex} ({self.name}) ")
                return 
                # raise ValueError(f"Invalid DIG channel index {digChannel}")
            
            digChannel = (digChannel,)
        
        elif isinstance(digChannel, (list, tuple)) and all(isinstance(v, int) for v in digChannel):
            if any(v not in usedDigs for v in digChannel):
                scipywarn(f"Not all specified DIG channels {digChannel} are used by the epoch {epoch.number} ({epoch.letter}) of DAC {self.physicalIndex} ({self.name}) ")
                return 
            
                # raise ValueError(f"Invalid DIG channel index {digChannel}")
            
        elif digChannel is None:
            digChannel = tuple(usedDigs.keys())
            
        else:
            raise TypeError(f"Expecting digChannel an int or a sequence of int; instead got {digChannel}")

        digPattern = tuple(itertools.chain.from_iterable(map(lambda x: reversed(x), self.getEpochDigitalPattern(epoch, sweep))))
        digChannelValue = tuple(digPattern[chnl] for chnl in digChannel)
        
        epochDIGs = epoch.digitalOutputChannels # a dict

        waves = list()
        
        for k, chnl in enumerate(digChannel):
            wave = np.full([epochSamplesCount, 1], 0) * self.units
            
            if digChannelValue[k] == 1: # emits pulse
                if any(v is None for v in (digOFF, digON)):
                    digOFF, digON = self.getDigitalPulseLogicLevels(chnl)
                
                if lastLevelOnly:
                    wave[:] = digOFF
                else:
                    wave[:] = digON
                    
            elif digChannelValue[k] == "*": # emits train
                if any(v is None for v in (trainOFF, trainON)):
                    trainOFF, trainON = self.getDigitalTrainLogicLevels()

                wave[:] = trainOFF
                if not lastLevelOnly:
                    for pulse in range(pulseCount):
                        p1 = int(pulsePeriod * pulse)
                        p2 = int(p1 + pulseSamples)
                        wave[p1:p2] = trainON
                        
            waves.append(wave)
            
        if not separateWavePerChannel:
            waves = [np.hstack(waves) * self.units]
            
        if returnLevels:
            return waves, digOFF, digON, trainOFF, trainON
        
        return waves
            
                        
    def getPreviousSweepLastEpochLevel(self, sweep:int) -> pq.Quantity:
        """Final analog value in the previous epoch"""
        # FIXME: 2023-09-18 23:34:27
        # this can become very expensive for many sweeps!
        if len(self.epochs) == 0 or sweep == 0:
            return self.dacHoldingLevel
        
        if self.returnToHold:
            prevLevel = self.dacHoldingLevel
            for s in range(sweep):
                for e in self.epochs:
                    prevLevel = self.getEpochAnalogWaveform(e, prevLevel, s, True)
                    
            return prevLevel
        
        return self.dacHoldingLevel
    
    def getDigitalTrainLogicLevels(self) -> typing.Tuple[pq.Quantity]:
        """TTL levels for digital trains, V.
        HIGH level is 5 V, LOW level is 0 V.
        If protocol.digitalTrainActiveLogic is True then all digital pulses in 
        the train are steps from OFF = LOW to ON = HIGH then back to OFF = LOW;
        otherwise, the logic is inversed: each pulse is from OFF = HIGH to 
        ON = LOW, then back to OFF = HIGH
        
        Returns a tuple with OFF and ON values, in THIS order.
        """
        if self.protocol.digitalTrainActiveLogic:
            return (0 * pq.V, 5 * pq.V)
        else:
            return (5 * pq.V, 0 * pq.V)
        
    def getDigitalPulseLogicLevels(self, digChannel:int = 0) -> typing.Tuple[pq.Quantity]:
        """TTL levels for digital pulses.
        HIGH level is 5 V, LOW level is 0 V.
        
        If protocol.digitalHoldingValue(digChannel) is True, then a TTL pulse
        is a step from OFF = HIGH to ON = LOW; otherwise the logic is inversed.
        
        Returns a tuple (OFF, ON) values (in THIS order)
        
        See also self.getDigitalTrainLogicLevels
        
    
    """
        if self.protocol.digitalHoldingValue(digChannel):
            return (5 * pq.V, 0 * pq.V)
        else:
            return (0 * pq.V, 5 * pq.V)
            
    
    def getDigitalLogicLevels(self, digChannel:int = 0) -> typing.Tuple[pq.Quantity]:
        """Returns (digOFF, digON, trainOFF, trainON).
        See also:
        self.getDigitalPulseLogicLevels() and self.getDigitalTrainLogicLevels()
    """
        digOFF, digON = self.getDigitalPulseLogicLevels(digChannel)
        trainOFF, trainON = self.getDigitalTrainLogicLevels()
        
        return digOFF, digON, trainOFF, trainON
        
            
    def getPreviousSweepLastDigitalLevel(self, sweep:int, digChannel:int,
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
        
    def getEpochsForDigitalChannel(self, digChannel: int, sweep: int = 0, 
                                   indexes: bool=False, 
                                   train: typing.Optional[bool] = None) -> list:
        """Returns the index of the epoch where the digChannel is used (set to 1 or '*')
        Parameters:
        -----------
        digChannel: int in the semi-open interval [0 ⋯ 8)
        sweep: int — index of the sweep (necessary to determine in which digital 
            pattern — main or alternate — the digChannel is sought
        indexes:bool, default is False
            When True, the method returns a list of epoch indexes in this DAC epochs table
            When False (the default), return a list of epochs
        train:bool or None
            When a bool, restricts the look up to where digChannel emits a TTL train
            (True) or pulse (False).
    
            Default is None
    
        Returns:
        --------
        A list of epochs (or their indexes in the epochs table if `indexes` is True)
        where digChannel is set (i.e., non-zero).
    
        The list may be empty is none of the epochs define a digital pattern for 
        the given sweep.
    
        NOTE: In Clampex, the digital pattern defined in an epoch normally applies
        to ALL sweeps.
     
        The only exception are the protocols where alternate digital pattern
        is enabled. In such protocols, the active DAC channel is the one where
        the "main" digital pattern is defined in the protocol editor, and this
        "main" pattern is applied to the sweeps with even index (0, 2, 4, etc).
        The "alternative" digital pattern is defined in any other DAC in the protocol
        editor, and is applied to the sweeps with odd index (1, 3, 5, etc)
    
        NOTE: In reality, this apparent association between a digital pattern 
        and a DAC is not born out by the hardware; however, digital patterns can 
        only be configured inside an epoch for analog command waveform output
        defined for a particular DAC. This may give the false impression that
        a digital pattern is emitted through the DAC where such epochs were defined,
        in the protocol editor.
    
        Things get more complicated when distinct digital patterns need to be 
        emitted in consecutive sweeps. Currently, Clampex supports only the definition
        of only two digital patterns in the same protocol, as explained in the NOTE above.
    
        For more complex experimental configuration (e.g. using three distinct 
        digital patterns in consecutive sweeps) the only approach in Clampex 
        appears to be the use of distinct ABF protocols via  "Sequencing keys".
        These protocols would have to generate just one sweep per run, with the 
        disadvantage that recording averages would have to be done offline
        (or at least Outside Clampex).
        
    
        """
        isAlternateDigital = self.alternateDigitalOutputStateEnabled and sweep % 2 > 0
        
        ret = list()
        
        for k, epoch in enumerate(self.epochs):
            # see self.getEpochDigitalPattern for code logic
            digPattern = list()
            if self.alternateDigitalOutputStateEnabled and self.logicalIndex < 2:
                if self.digitalOutputEnabled:
                    if self.physicalIndex == self.protocol.activeDACChannel:
                        if digChannel in range(4):
                            digPattern = list(reversed(epoch.getDigitalPattern(isAlternateDigital)[0]))
                        elif digChannel in range(4,8):
                            digPattern = list(reversed(epoch.getDigitalPattern(isAlternateDigital)[1]))
                            digChannel -= 4
                        else:
                            raise ValueError(f"Expecting a digital channel index (`digChannel`) in the interval [0 ⋯ 8); instead, got {digChannel}")
            else:
                if self.digitalOutputEnabled:
                    if digChannel in range(4):
                        digPattern = list(reversed(epoch.getDigitalPattern()[0]))
                    elif digChannel in range(4,8):
                        digPattern = list(reversed(epoch.getDigitalPattern()[1]))
                        digChannel -= 4
                    else:
                        raise ValueError(f"Expecting a digital channel index (`digChannel`) in the interval [0 ⋯ 8); instead, got {digChannel}")
                    
            if digChannel < len(digPattern) and (digPattern[digChannel] != 0 if train is None else digPattern[digChannel] == '*' if train is True else digPattern[digChannel] == 1):
                if indexes:
                    ret.append(k)
                else:
                    ret.append(epoch)
                
        return ret
    
#     def getEpochDigitalPattern(self, epoch:typing.Union[ABFEpoch, str, int], 
#                                sweep:int=0) ->tuple:
#         """
#         TODO: Move this code to ABFProtocol, thus breaking the need to store
#         a reference to the protocol in this ABFOutputConfiguration instance.
#         
#         Returns the digital pattern that WOULD be output by the epoch.
#         
#         This depends, simultaneously, on the following conditions:
#         
#         1) the DAC channel has digital outputs enabled
#         
#         2) If alternative digital outputs are enabled in the protocol, this DAC
#             emits DIG outputs on the specified sweep.
#             
#         3) the DAC channel takes part in alternate digital outputs or not (this
#             depends on the channel index, with DAC 0 and 1 being the only ones
#             used for alternate digital output during even- and odd-numbered sweeps)
#         
#         Returns:
#         --------
#         A 2-tuple[4-tuple[int]] corresponding to the two DIG output banks in the
#         order 3⋯0, 7⋯4
#         
#         """
#         
#         isAlternateDigital = self.alternateDigitalOutputStateEnabled and sweep % 2 > 0
#         
#         if isinstance(epoch, (int, str)):
#             e = self.getEpoch(epoch)
#             if e is None:
#                 raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.physicalIndex}, {self.name})")
#             
#             epoch = e
#             
#         elif not isinstance(epoch, ABFEpoch):
#             raise TypeError(f"Expecting an ABFEpoch, an int or a str (epoch 'name' e.g. 'A', 'B' or 'AB', etc); instead got {type(epoch).__name__}")
#         
#         if self.alternateDigitalOutputStateEnabled and self.logicalIndex < 2:
#             # NOTE: 2023-09-18 13:22:56
#             # When alternative digital outputs are used in an experiment,
#             # ONLY the first two DACs (0 and 1) take part in the alternative
#             # arangement of digital outputs, as follows:
#             #
#             # • The DAC where digital outputs are enabled sends TTLs during
#             #   even-numbered sweeps (0,2,4,…),
#             #
#             # • The "other" DAC (where digital outputs are NOT enabled) sends 
#             #   TTLs during odd-numbered sweeps (1,3,5,…)
#             #
#             # The alternate pattern is DEFINED in the protocol editor 
#             # in the "other" DAC channel (DAC1 if digital output is enabled
#             # on DAC0, or DAC0 if digital output is enabled on DAC1); this 
#             # pattern is stored internally in the ABF file as the "alternate"
#             # digital pattern (at a different address)
#             #
#             # NOTE: neither physical DAC channel actually sends out any TTL signals
#             # The association of a digital pattern with the GUI for the configuration
#             # of a particular DAC channel seems an arbitrary decision in Clampex,
#             # likely justified by the fact that the digital output (TTL) is
#             # associated logically with the command waveform (if any) sent out 
#             # by a physical DAC channel during a particular epoch; another
#             # possible reason is to avoid the Clampex GUI becoming more complex...
#             # 
#             #
#             if self.digitalOutputEnabled:
#                 # for the DAC channel where digital output is enabled we write
#                 # ONLY the main digital pattern of the epoch, and ONLY if 
#                 # the sweep has an even number
#                 #
#                 # if self.logicalIndex == self.protocol.activeDACChannel:
#                 if self.physicalIndex == self.protocol.activeDACChannel:
#                     if isAlternateDigital:
#                         # this DAC has dig output enabled, hence during
#                         # an experiment it will output NOTHING if either 
#                         # alternateDigitalPattern is disabled OR sweep number 
#                         # is even
#                         #
#                         
#                         # NOTE: 2024-10-20 10:42:42
#                         # retrieve the alternate digital pattern defined in
#                         # epoch, then:
#                         dig_3_0 = epoch.getDigitalPattern(True)[0] # select first bank
#                         dig_7_4 = epoch.getDigitalPattern(True)[1] # select second bank
#                     else:
#                         # this DAC has dig output enabled, hence during
#                         # an experiment it will output the main digital pattern
#                         # if either alternateDigitalPattern is disabled, OR
#                         # sweep number is even
#                         #
#                         
#                         # NOTE: 2024-10-20 10:43:38
#                         # retrieve the main digital pattern defined in epoch,
#                         # then:
#                         dig_3_0 = epoch.getDigitalPattern(False)[0] # select first bank
#                         dig_7_4 = epoch.getDigitalPattern(False)[1] # select second bank
#                 else:
#                     dig_3_0 = dig_7_4 = [0,0,0,0] # if not active DAC, return zeros
#             else:
#                 # For a DAC where dig output is DISabled, the DAC is simply
#                 # a placeholder for the alternate digital output of the epoch, 
#                 # (and these TTLs will be sent out) ONLY if alternateDigitalPattern
#                 # is enabled AND sweep number is odd
#                 #
#                 # NOTE: 2023-10-04 09:07:42 - show what is actually sent out
#                 # i.e., if digital output is DISABLED then show zeroes even if
#                 # in the Clampex protocol editor we have a pattern entered here.
#                 #
#                 # This is because, when digital output is disabled for this DAC
#                 # AND alternative digital output is enabled in the protocol, the
#                 # digital pattern entered on this waveform tab in Clampex
#                 # protocol editor is used as the alternative digital output for
#                 # the DAC where digital output IS enabled.
#                 #
#                 # I guess this is was a GUI design decision taken the by Clampex
#                 # authors n order to avoid adding another field to the GUI form.
#                 #
#                 # NOTE: 2023-10-04 09:12:29
#                 # Also, the DAC where digital output patterns are enabled may NOT
#                 # be the same as the DAC one is recording from! 
#                 #
#                 # So if you're using, say DAC1, to send commands to your cell 
#                 # (where DAC1 should be paired with the ADCs coming from the second
#                 # amplifier channel, in a MultiClamp device) it is perfectly OK to
#                 # enable digital outputs in the DAC0 waveform tab: Clampex will
#                 # still issue TTLs during the sweep, even if DAC0 does not send 
#                 # any command waveforms.
#                 #
#                 #
#                 # On the other hand, if DAC0 has waveforms disabled (in this example,
#                 # DAC0 is NOT used in the experiment) AND alternate digital outputs
#                 # is disabled in the protocol, then NO digital outputs are "linked"
#                 # to this DAC0.
#                 #
#                 # That somewhat confuses things, because DIG channels and DAC
#                 # channels are physically independent! The only logical "link"
#                 # between them is the timings of the epochs.
#                 # 
#                 # Also, NOTE that in Clampex only one DAC can have digital outputs
#                 # enabled.
#                 #
#                 
#                 dig_3_0 = dig_7_4 = [0,0,0,0]
#                     
#         else:
#             if self.digitalOutputEnabled:
#                 # if alternateDigitalPattern is not enabled, or the DAC channel
#                 # is one of the channels NOT involved in alternate output
#                 # (2, …) the channel will always output the main digital 
#                 # pattern here
#                 dig_3_0 = epoch.getDigitalPattern()[0]
#                 dig_7_4 = epoch.getDigitalPattern()[1]
#             else:
#                 dig_3_0 = dig_7_4 = [0,0,0,0]
#                 
#         return dig_3_0, dig_7_4
    
    @property
    def emulatesTTL(self)->bool:
        """True when this ADC emulates TTLs for3rd party devices.
        This can happen when:
        • the DAC has analog waveform enabled
        • the DAC has epochs that emulate TTLs via analog waveforms (see ABFEpoch.emulatesTTL)
        """
        return self.analogWaveformEnabled and len(self.getEpochsWithTTLWaveforms())
    
                
    @property
    def analogWaveformEnabled(self) -> bool:
        return self._waveformEnabled_
    
    @analogWaveformEnabled.setter
    def analogWaveformEnabled(self, val:bool):
        self._waveformEnabled_ = val == True
    
    @property
    def analogWaveformSource(self) -> ABFDACWaveformSource:
        return self._waveformSource_
    
    @analogWaveformSource.setter
    def analogWaveformSource(self, val:typing.Union[int, ABFDACWaveformSource]):
        if isinstance(val) and val in ABFDACWaveformSource.values():
            self._waveformSource_ = ABFDACWaveformSource(val)
        elif isinstance(val, ABFDACWaveformSource):
            self._waveformSource_ = val
        else:
            self._waveformSource_ = ABFDACWaveformSource.none
    
    # @property
    # def isactiveDACChannel(self) -> bool:
    #     return self._isActiveDACChannel_
    
    @property
    def digitalOutputEnabled(self) -> bool:
        """True if any epoch defined in this DAC emits digital pulses or trains"""
        # NOTE: 2023-10-18 09:57:46
        # This is NOT an intrinsic variable in Clampex, but is used here to
        # help identify if this DAC associates the main digital output pattern
        
        # In Clampex, only one DAC can associate DIG out; however, when alternate
        # digital output is enabled in the protocol, the alternative dig out 
        # pattern can only be defined on another DAC's GUI in the Waveforms tab 
        # of the Clampex protocol editor.
        
        # I think this is unfortunate, as it may confuse one into thinkng that
        # this "other" DAC emits dig out on alternate sweeps, when in fact it 
        # doesn't
        # 
        return len(tuple(itertools.chain.from_iterable([e.getUsedDigitalOutputChannels(alternate=False) for e in self.epochs]))) > 0
        # pass
        # return self._digOutEnabled_
    
    def getChannelIndex(self, physical:bool=False):
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
    def physicalIndex(self) -> int:
        return self._physicalChannelIndex_
    
    @physicalIndex.setter
    def physicalIndex(self, val:int):
        self._physicalIndex_ = val
    
    @property
    def number(self) -> int:
        """Alias to self.logicalIndex"""
        return self.logicalIndex
    
    @property
    def physical(self):
        return self.physicalIndex

    @property
    def name(self) -> str:
        return self._dacName_
    
    @name.setter
    def name(self, val:str):
        if isinstance(val, str):
            self._dacName_ = val
    
    @property
    def dacName(self)->str:
        """Alias to self.name for backward compatibility"""
        return self.name
    
    @property
    def units(self) -> pq.Quantity:
        return self._dacUnits_
    
    @units.setter
    def units(self, val:pq.Quantity):
        self._dacUnits_ = val
    
    @property
    def dacUnits(self) -> pq.Quantity:
        return self.units
    
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
    
    def getDigitalOutputs(self, alternate:typing.Optional[bool]=None,
                       trains:typing.Optional[bool]=None) -> set:
        return set(itertools.chain.from_iterable([e.getUsedDigitalOutputChannels(alternate, trains) for e in self.epochs]))
        
        # return self._digitalOutputs_
    
    @property
    def samplingRate(self) -> pq.Quantity:
        return self.protocol.samplingRate
    
    @property
    def dacHoldingLevel(self) -> pq.Quantity:
        """DAC-specific"""
        return self._dacHoldingLevel_
    
    @dacHoldingLevel.setter
    def dacHoldingLevel(self, val: pq.Quantity):
        if not scq.unitsConvertible(self.units, val.units):
            raise TypeError(f"Argument units {val.units} are incompatible with this channel units ({self.units})")
        
        self._dacHoldingLevel_ = val.rescale(self.units)
    
    @property
    def alternateDigitalOutputStateEnabled(self) -> bool:
        if self.protocol:
            return self.protocol.alternateDigitalOutputStateEnabled
        return False
    
    @property
    def alternateDACOutputStateEnabled(self) -> bool:
        if self.protocol:
            return self.protocol.alternateDACOutputStateEnabled
        return False
        
    @property
    def holdingTime(self) -> pq.Quantity:
        """Read-only (determined by Clampex).
        This corresponds 1/64 samples of total samples in a sweep.
        This is protocol-specific.
    """
        if self.protocol:
            return self.protocol.holdingTime
    
    def getAnalogWaveform(self, sweep:int=0) -> neo.AnalogSignal:
        return self.getCommandWaveform(sweep)
    
    def getCommandWaveform(self, sweep:int=0) -> neo.AnalogSignal: 
        """Generates an AnalogSignal representation of the command waveform.
        
        CAUTION: The `sweep` parameter is only used to get the epoch parameter 
        values where these values vary from one sweep to another ("Delta level" 
        and "Delta duration"), and not to establish if the DAC would emit a 
        waveform for that particular sweep or not. 
    
        Whether a DAC emits an analog wavefomr on a particular sweep is determined
        entirely by the protocol. The DAC only does what its Epochs "tell" it to do.
        The protocol "tells" the DAC to emit a wavefomr or not, depending on the
        protocols' alternateDACOutputStateEnabled and on the sweep number!
    
        Therefore, the wavefomr returned here reflects sweep-specific state of 
        the epoch parametrs, and nothing else.
    
    
    
    
    The analog waveform returned here is the one generated by
        the Epchs in the DAC regardless 
     
        NOTE: DAC command waveforms and digital outputs are enabled only in 
        Episodic Stimulation type of experiments.
     
        """
        if self.analogWaveformSource == ABFDACWaveformSource.none or not self.analogWaveformEnabled:
            # return empty signal (containing np.nan)
            return neo.AnalogSignal(np.full((self.protocol.sweepSampleCount, 1), np.nan),
                                    units = self.units, t_start = 0*pq.s,
                                    sampling_rate = self.samplingRate,
                                    name = self.dacName)
        
        if self.analogWaveformSource == ABFDACWaveformSource.epochs:
            if len(self.epochs) == 0:
                return neo.AnalogSignal(np.full((self.protocol.sweepSampleCount, 1), float(holdingLevel)),
                                        units = self.units, t_start = 0*pq.s,
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
                                        units = self.units, t_start = 0*pq.s,
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
                
                wave = self.getEpochAnalogWaveform(epoch, previousLevel, sweep)
                
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
                                    units = self.units, t_start = 0*pq.s,
                                    sampling_rate = self.samplingRate,
                                    name = self.dacName)
        
            
                
        return waveform
    
    def getDigitalWaveform(self, sweep:int=0, 
                           digChannel:typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
                           separateWavePerChannel:bool=True) -> neo.AnalogSignal:
        """Realizes the digital output waveform (pulses, trains) emitted when
        this DAC channel is active.
        
        """
        # NOTE: 2023-09-20 22:22:41
        # the digital output is ALWAYS in V
        # "high logic" means 5V on a background of 0 V
        # "low logic" means 0V on a background of 5V
        
        usedDigs = list(itertools.chain.from_iterable([epoch.getUsedDigitalOutputChannels() for epoch in self.epochs]))
        
        if isinstance(digChannel, int):
            if digChannel not in usedDigs:
                raise ValueError(f"Invalid DIG channel index {digChannel}")
            
            digChannel = (digChannel,)
            
        elif isinstance(digChannel, (list, tuple)) and all(isinstance(v, int) for v in digChannel):
            if all(v not in usedDigs for v in digChannel):
                raise ValueError(f"Invalid DIG channel indexes {digChannel}")
            
            digChannel = tuple(sorted(set(digChannel)))
            
        elif digChannel is None:
            digChannel = tuple(sorted(set(usedDigs)))
            
        else:
            raise TypeError(f"expecting digChannel an int or sequence of int; instead got {digChannel}")
            
        if separateWavePerChannel:
            waveforms = [neo.AnalogSignal(np.full((self.sweepSampleCount, 1), 
                                                np.nan),
                                        units = pq.V, t_start = 0*pq.s,
                                        sampling_rate = self.samplingRate,
                                        name = f"DIG {chnl} DAC {self.physicalIndex} ({self.name})") for chnl in digChannel]
        else:
            waveforms = neo.AnalogSignal(np.full((self.sweepSampleCount, len(digChannel)), 
                                                np.nan),
                                        units = pq.V, t_start = 0*pq.s,
                                        sampling_rate = self.samplingRate,
                                        name = f"DIG Output DAC {self.physicalIndex} ({self.name})")
            
        t0 = t1 = self.holdingTime.rescale(pq.s)
        
        offLevel = None
        
        if separateWavePerChannel:
            lastEpochNdx = [0] * len(digChannel)
            lastLevel = [None] * len(digChannel)
        else:
            lastEpochNdx = 0
            lastLevel = None 
        
        for epoch in self.epochs:
            actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
            t1 = t0 + actualDuration
            tt = np.array([t0,t1])*pq.s
            
            eWaves = self.getEpochDigitalWaveform(epoch, sweep, digChannel,
                                             separateWavePerChannel=separateWavePerChannel,
                                             returnLevels=True)
            
            t0 = t1
            
            if eWaves is None:
                continue
            
            epochWaves, epoch_digOFF, epoch_digON, epoch_trainOFF, epoch_trainON = eWaves
            offLevel = epoch_digOFF if epoch_digOFF is not None else epoch_trainOFF
            
            if lastLevel is None:
                lastLevel = epoch_digOFF if epoch_digOFF is not None else epoch_trainOFF
                
            if separateWavePerChannel:
                for k in range(len(epochWaves)):
                    ndx = waveforms[k].time_index(tt)
                    lastEpochNdx[k] = ndx[1]
                    lastLevel[k] = epochWaves[k][-1]
                    waveforms[k][ndx[0]:ndx[1], :] = epochWaves[k]
                    
            else:
                ndx = waveforms.time_index(tt)
                lastEpochNdx = ndx[1]
                lastLevel = epochWaves[0][-1,:]
                waveforms[ndx[0]:ndx[1], :] = epochWaves[0]
                
        if self.protocol.digitalUseLastEpochHolding:
            if separateWavePerChannel:
                for k in range(len(waveforms)):
                    waveforms[k][lastEpochNdx[k]:, :] = lastLevel[k]
            else:
                 waveforms[lastEpochNdx:, :] = lastLevel
        else:
            if separateWavePerChannel:
                for k in range(len(waveforms)):
                    waveforms[k][lastEpochNdx[k]:, :] = offLevel
            else:
                waveforms[lastEpochNdx:, :] = offLevel
                
        if separateWavePerChannel:
            for k in range(len(waveforms)):
                waveforms[k][np.isnan(waveforms[k])] = offLevel
        else:
            waveforms[np.isnan(waveforms)] = offLevel
            
        return waveforms
        
        
def getEpochNumberFromLetter(x:str) -> int:
    """The inverse function of getEpochLetter()"""
    from core import strutils
    return strutils.lettersToOrdinal(x)


def getEpochLetter(epochNumber:int):
    from core import strutils
    return strutils.ordinalToLetters(epochNumber)

def __wrap_to_quantity__(x:typing.Union[list, tuple], convert:bool=True):
    return (x[0], unitStrAsQuantity(x[1])) if convert else x

def unitStrAsQuantity(x:str, convert:bool=True):
    return scq.unitQuantityFromNameOrSymbol(x) if convert else x

def sourcedFromABF(x:neo.Block) -> bool:
    return x.annotations.get("software", None) == "Axon"

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
    info_dict = getAcquisitionInfo(obj)
        
    epochsDigitalPattern = dict()
    
    # reverses the banks => 7-4 then 3-0
    banks = [1,0] if reverse_banks else [0,1]
    
    nSynchDIGBits = info_dict["protocol"]["nDigitizerSynchDigitalOuts"]
    nAlternateDIGBits = info_dict["protocol"]["nDigitizerTotalDigitalOuts"] - nSynchDIGBits

    getSynchBitList = partial(valToBitList, bitCount = nSynchDIGBits,
                                as_bool=True)
    
    getAlternateBitList = partial(valToBitList, bitCount = nAlternateDIGBits,
                                    as_bool = True)
    
    for epoch_info in info_dict["EpochInfo"]:
        epochNumber = epoch_info["nEpochNum"]
        if isinstance(epoch_num, int) and epoch_num != epochNumber:
            continue
        d  = getSynchBitList(epoch_info["nDigitalValue"])
        s  = getSynchBitList(epoch_info["nDigitalTrainValue"])
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
                
            dacLevel = epoch.level*scq.unitQuantityFromNameOrSymbol(dacUnits) if isinstance(dacUnits, str) and len(dacUnits.strip()) else epoch.level
            dacLevelDelta = epoch.levelDelta*scq.unitQuantityFromNameOrSymbol(dacUnits) if isinstance(dacUnits, str) and len(dacUnits.strip()) else epoch.levelDelta

            epValues = np.array([epoch.epochTypeStr,    # str description of epoch type (as per Clampex e.g Step, Pulse, etc)                            
                              dacLevel,                 # "first" DAC level -> quantity; CAUTION units depen on Clampex and whether its telegraphs were OK
                              dacLevelDelta,            # "delta" DAC level: level change with each sweep in the run; quantity, see above
                              epoch.duration,           # "first" duration (samples)
                              epoch.durationDelta,      # "delta" duration (samples)
                              epoch.duration/x.sampleRateHz * 1000 * pq.ms, # first duration (time units)
                              epoch.durationDelta/x.sampleRateHz * 1000 * pq.ms, # delta duration (time units)
                              epoch.getDigitalPattern()[:4], # first 4 digital channels
                              epoch.getDigitalPattern()[4:], # last 4 digital channels
                              epoch.pulsePeriod,        # train period (samples`)
                              epoch.pulseWidth,         # pulse width (samples)
                              epoch.pulsePeriod/x.sampleRateHz * 1000 * pq.ms, # train period (time units)
                              epoch.pulseWidth/x.sampleRateHz * 1000 * pq.ms], # pulse width (time units)
                              dtype=object)
            
            epochData[epoch.getEpochLetter] = epValues
            
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
        x_units = scq.unitQuantityFromNameOrSymbol(abf.sweepUnitsX)
        x = abf.sweepX
        y_name, y_units_str = abf._getDacNameAndUnits(dacIndex)
        y_units = scq.unitQuantityFromNameOrSymbol(y_units_str) if isinstance(y_units_str, str) else pq.dimensionless
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
        x_units = scq.unitQuantityFromNameOrSymbol(abf.sweepUnitsX)
        x = abf.sweepX
        y_name, y_units_str = abf._getDacNameAndUnits(dacIndex)
        y_units = scq.unitQuantityFromNameOrSymbol(y_units_str)
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
    info_dict = getAcquisitionInfo(obj)
    
    abf_version = info_dict.get("abf_version", None)
    assert isinstance(abf_version, float), "Object does not appear to be sourced from an ABF file"
    
    # NOTE: 2024-09-29 21:45:08
    # we need to compare the int part of abf_verison with fileVersionMajor below
    abf_version = int(abf_version)
    
    fFileSignature = info_dict.get("fFileSignature", None)
    
    assert isinstance(fFileSignature, bytes), "Object does not appear to be sourced from an ABF file"
    
    fileSig = fFileSignature.decode()
    fileSigVersion = int(fileSig[-1])
    
    assert abf_version == fileSigVersion, "Mismatch between reported ABF versions; check obejct's annotations properties"
    
    fFileVersionNumber = info_dict.get("fFileVersionNumber", None)
    
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
    info_dict = getAcquisitionInfo(obj)
    return dict(map(lambda x: (x, (info_dict["listADCInfo"][x]["ADCChNames"].decode(),
                                   unitStrAsQuantity(info_dict["listADCInfo"][x]["ADCChUnits"].decode(), useQuantities))),
                    range(info_dict["sections"]["ADCSection"]["llNumEntries"])))
    # return dict(map(lambda x: (x, (obj.annotations["listADCInfo"][x]["ADCChNames"].decode(),
    #                                unitStrAsQuantity(obj.annotations["listADCInfo"][x]["ADCChUnits"].decode(), useQuantities))),
    #                 range(obj.annotations["sections"]["ADCSection"]["llNumEntries"])))

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
    info_dict = getAcquisitionInfo(obj)
    return dict(map(lambda d: (d["nDACNum"], (d["DACChNames"].decode(), unitStrAsQuantity(d["DACChUnits"].decode(), useQuantities))),
                    filter(lambda x: x["nWaveformEnable"] > 0 and x["nWaveformSource"] > 0, info_dict["listDACInfo"])))
    # return dict(map(lambda d: (d["nDACNum"], (d["DACChNames"].decode(), unitStrAsQuantity(d["DACChUnits"].decode(), useQuantities))),
    #                 filter(lambda x: x["nWaveformEnable"] > 0 and x["nWaveformSource"] > 0, obj.annotations["listDACInfo"])))
    
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
    
    
        
    
    
        
