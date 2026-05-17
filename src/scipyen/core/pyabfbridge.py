# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Module to access ABF meta-information.

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
from functools import singledispatch, singledispatchmethod, partial
import traceback
import numpy as np
import pandas as pd
import quantities as pq
import neo
from dataclasses import MISSING
from collections import namedtuple
from tribool import Tribool

from core import scipyen_quantities as scq
from core import datatypes, strutils, utilities
from core.typeenum import TypeEnum
from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType, MarkType)
from core.triggerprotocols import TriggerProtocol
from core.prog import scipywarn
from core.datazone import Interval
from ephys.ephys_protocol import ElectrophysiologyProtocol
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

# ABFDigitalPattern = namedtuple("ABFDigitalPattern", ["main", "alternate"], module=__name__)

class ABFDigitalPattern(typing.NamedTuple):
    r"""Digital pattern for the DIG channels in Clampex.

.. |nbsp| unicode:: 0xA0
   :trim:

For Digidata 1500 series (with eight digital outputs) the DIG channels are stored |nbsp|
as a pair of 4-tuple flags, one pair for each of the "main" and "alternate" digital |nbsp|
patterns, with 'x' below standing for any of the three possible values (0, 1, '*'):

::
    Channel index:  3,2,1,0    7,6,5,4
                  ((x,x,x,x), (x,x,x,x))

For Digidata 1400 series (with only four digital outputs) there is only one such |nbsp|
bank of four flags, for each of the "main" and "alternate" digital patterns:

::
    Channel index:  3,2,1,0
                  ((x,x,x,x), )


Members (attributes):
---------------------

:main: a pair of 4-channel banks with their value (0 = inactive, 1 = emitting a |nbsp|
        TTL pulse, or '*' = emitting a TTL train), by default, in DESCENDING order |nbsp|
        of their index (see above). For Digidata < 1500, the pair contains only one |nbsp|
        bank of four channels.

:alternate: as ``main``, but reflects the digital channel activity on alternate |nbsp|
    sweeps (and therefore ONLY used in a protocol where "alternateDigitalOutputsEnabled" |nbsp|
    is ``True``).

:reversed: flag indicating the index order in which channels are stored in each bank. |nbsp|
    By default, this is False.

    Since ABFDigitalPattern objects are NamedTuples, this value cannot be changed |nbsp|
    for a given instance (Python language feature). However, new instances can be |nbsp|
    created with ``reversed`` set to True, which is whate the method ``self.reverse()`` |nbsp|
    does.

    To avoid any confusion, one should NOT pass a value to this parameter when |nbsp|
    constructing a new ABFDigitalPattern, unless they have a very good reason to do so.


.. note::
    The default order of the channels is as depicted above. However, sometimes |nbsp|
    it is convenient to have the channels in ascending (natural) order.

    Therefore the new method self.reversed generates a new ABFDigitalPattern with
    the order reversed. To ensure which order is beng used in an ABFDigitalPattern
    instance, check the ``reversed`` attribute.!

    The default value of ``False`` indicates that channels are stored in descending |nbsp|
    order of their index (as used throughout the Clampex protocol).

"""
    main: tuple
    alternate: tuple
    reversed: bool = False

    def channelIsUsed(self, channel: int,
                        main: typing.Optional[
                            typing.Union[bool, Tribool]
                            ] = None,
                        train: typing.Optional[
                            typing.Union[bool, Tribool]
                            ] = None) -> bool | tuple[bool]:
        if main is None:
            main = Tribool()

        elif isinstance(main, bool):
            main = Tribool(main)

        elif not isinstance(main, Tribool):
            raise TypeError(f"'main' expected a bool, Tribool, or None; got {type(main).__name__} instead")

        if train is None:
            train = Tribool()

        elif isinstance(train, bool):
            train = Tribool(train)

        elif not isinstance(train, Tribool):
            raise TypeError(f"'train' expected a bool, Tribool, or None; got {type(train).__name__} instead")

        if main.value is None:
            if len(self.main) == 0 and len(self.alternate) == 0:
                return False

            return (self.channelIsUsed(channel, Tribool(True),   train),
                    self.channelIsUsed(channel, Tribool(False),  train))

        else:
            banks = self.main if main.value else self.alternate

            if channel >= 0:
                if channel < 4:
                    bank0  = tuple(reversed(banks[0])) if not self.reversed else banks[0]
                    if train.value is None:
                        return bank0[channel] != 0
                    elif train.value:
                        return bank0[channel] == "*"
                    else:
                        return bank0[channel] == 1

                elif channel < 8:
                    bank1 = tuple(reversed(banks[1])) if not self.reversed else banks[1]
                    if train.value is None:
                        return bank1[channel] != 0
                    elif train.value:
                        return bank1[channel] == "*"
                    else:
                        return bank1[channel] == 1

        return False

    def reverse(self) -> typing.Self:
        r"""Generate a version of this object with the order of the channels REVERSED in each bank"""
        main = tuple(map(lambda b: tuple(reversed(b)), self.main))
        alternate = tuple(map(lambda b: tuple(reversed(b)), self.alternate))
        return self.__class__(main, alternate, not self.reversed)

    def getActiveChannels(self,
                        main: typing.Optional[
                            typing.Union[bool, Tribool]
                            ] = None,
                        train: typing.Optional[
                            typing.Union[bool, Tribool]
                            ] = None) -> tuple:
        r"""Return a tuple of the indexes of the used digital channels.

.. |nbsp| unicode:: 0xA0
   :trim:

Parameters:
-----------
:main: bool, Tribool, or None (default). Flag specifying which bank of digital |nbsp|
    channels should be queried. When ``None``, the function queries both banks |nbsp|
    and returns a pair of tuples, respectively, for the *main* and the *alternate* |nbsp|
    digital channel banks.

:train: bool, Tribool, or None (default). Flag specifying which type of TTL |nbsp|
        signal is expected for the digital channels to emit for them to be considered |nbsp|
        "in use". When ``None``, then a



"""
        if isinstance(main, bool):
            main  = Tribool(main)

        elif main is None:
            main = Tribool()

        elif not isinstance(main, Tribool):
            raise TypeError(f"'main' expected a bool, Tribool, or None; instead, got a {type(main).__name__}")

        if isinstance(train, bool):
            train  = Tribool(train)

        elif train is None:
            train = Tribool()

        elif not isinstance(train, Tribool):
            raise TypeError(f"'train' expected a bool, Tribool, or None; instead, got a {type(train).__name__}")

        if main.value is None:
            return (self.getActiveChannels(Tribool(True), train),
                    self.getActiveChannels(Tribool(False), train))

        else:
            pattern = self if self.reversed else self.reverse()

            # print(f"{self.__class__.__name__}.getActiveChannels: pattern -> {pattern}")

            banks = pattern.main if main.value else pattern.alternate

            # full_banks = tuple(itertools.chain.from_iterable(banks))
            full_banks = itertools.chain.from_iterable(banks)

            testVal = lambda v: v != 0 if train.value is None else v == "*" if train.value else v == 1

            return tuple(map(lambda i: i[0], filter(lambda i: testVal(i[1]), enumerate(full_banks))))

# These two will be (properly) redefined further below
class ABFOutputConfiguration:   # placeholder to allow the definition of ABFProtocol, below
    pass
class ABFInputConfiguration:   # placeholder to allow the definition of ABFProtocol, below
    pass                         # will be (properly) redefined further below

class ABFAcquisitionMode(TypeEnum):
    r"""Corresponds to nOperationMode in ABF._protocolSection and annotations"""
    variable_length_event = 1
    fixed_length_event = 2
    gap_free = 3
    high_speed_oscilloscope = 4 # Not supported by neo, but supported by pyabf!
    episodic_stimulation = 5

class ABFAveragingMode(TypeEnum):
    r"""Corresponds to nAverageAlgorithm in ABF._protocolSection"""
    cumulative = 0
    most_recent = 1

class ABFDACWaveformSource(TypeEnum):
    none     = 0
    epochs   = 1
    wavefile = 2

class ABFEpochType(TypeEnum):
    Unknown = -1
    Off = 0
    Step = 1
    Ramp = 2
    Pulse = 3
    Triangular = 4
    Cosine = 5
    Biphasic = 7

class ABFEpoch:
    r"""Encapsulates an ABF Epoch - a building part of the DAC (command) waveform.
    Similar to pyabf.waveform.Epoch.

    Takes into account digital train pulses.
    """
    def __init__(self, epochNumber:int = -1, epochType: ABFEpochType = ABFEpochType.Unknown,
                 level: typing.Optional[pq.Quantity]=None,
                 levelDelta: typing.Optional[pq.Quantity] = None,
                 duration: pq.Quantity = 0 * pq.ms,
                 durationDelta: pq.Quantity = 0* pq.ms,
                 # mainDigitalPattern: typing.Sequence = (tuple(), tuple()),
                 # alternateDigitalPattern: typing.Sequence = (tuple(), tuple()),
                 # useAltPattern: bool=False,
                 # altDIGOutState: bool = False,
                 pulsePeriod: pq.Quantity = np.nan * pq.ms,
                 pulseWidth: pq.Quantity = np.nan * pq.ms,
                 dacNum: int = -1):
        self._epochNumber_ = epochNumber
        self._epochType_ = epochType
        self._level_ = level # -1 * pq.dimensionless
        self._levelDelta_ = levelDelta # -1 * pq.dimensionless
        self._duration_ = duration
        self._durationDelta_ = durationDelta
        # self._mainDigitalPattern_ = mainDigitalPattern
        # self._alternateDigitalPattern_ = alternateDigitalPattern
        # self._useAltPattern_ = useAltPattern
        # self._altDIGOutState_ = altDIGOutState
        self._pulsePeriod_ = pulsePeriod
        self._pulseWidth_ = pulseWidth
        self._dacNum_ = dacNum

#     @classmethod
#     def _check_dig_pattern_args_(cls, val):
#         if isinstance(val, str):
#             # eval it then keep fingers crossed
#             try:
#                 val = eval(val)
#             except:
#                 traceback.print_exc()
#                 return (tuple(), tuple())
#
#         if isinstance(val, (tuple, list)) and all(isinstance(x, (tuple, list)) and all(isinstance(v, (int, str)) for v in x) for x in val):
#             return tuple(tuple(x) for x in val)
#
#         return (tuple(), tuple())

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

        # mainDigitalPattern = cls._check_dig_pattern_args_(attrs["mainDigitalPattern"])
        # print(f"\tmainDigitalPattern = {mainDigitalPattern} ({type(mainDigitalPattern).__name__})")

        # alternateDigitalPattern = cls._check_dig_pattern_args_(attrs["alternateDigitalPattern"])
        # print(f"\talternateDigitalPattern = {alternateDigitalPattern} ({type(alternateDigitalPattern).__name__})")
        # useAltPattern = attrs.get("useAltPattern", None)
        # altDIGOutState = attrs.get("altDIGOutState", None)
        pulsePeriod = attrs.get("pulsePeriod", None)
        pulseWidth = attrs.get("pulseWidth", None)
        dacNum = attrs.get("dacNum", None)

        return cls(epochNumber, epochType, firstLevel, deltaLevel,
                   firstDuration, deltaDuration,
                   pulsePeriod, pulseWidth, dacNum)

#         return cls(epochNumber, epochType, firstLevel, deltaLevel,
#                    firstDuration, deltaDuration,
#                    mainDigitalPattern, alternateDigitalPattern, useAltPattern, altDIGOutState,
#                    pulsePeriod, pulseWidth, dacNum)
#
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
        r"""Epoch's letter in the epochs index; read-only.
        E.g., 'A', 'B', etc"""
        return getEpochLetter(self.number)

    @property
    def name(self) -> str:
        r"""Alias to self.letterm(for convenience); read-only"""
        return self.letter

    @property
    def number(self) -> int:
        r"""Alias to self.index"""
        return self._epochNumber_

    @property
    def index(self) -> int:
        r"""Index of thsi epochs in the Epochs table"""
        return self._epochNumber_

    @number.setter
    def number(self, val:int):
        self._epochNumber_ = val

    @property
    def epochNumber(self) -> int:
        r"""Alias to self.number for backward compatibility"""
        return self.number

    @epochNumber.setter
    def epochNumber(self, val):
        self.number = val

    @property
    def epochType(self) -> ABFEpochType:
        r"""Alias to self.type"""
        return self._epochType_

    @property
    def emulatesTTL(self) -> bool:
        r"""True when epoch type is ABFEpochType.Pulse and meets the conditions below:
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
    def trainPeriod(self):
        r"""Alias to pulsePeriod"""
        return self.pulsePeriod

    @trainPeriod.setter
    def trainPeriod(self, value):
        self.pulsePeriod = value

    @property
    def pulseFrequency(self) -> pq.Quantity:
        if float(self.pulsePeriod) == 0.:
            return 0*pq.Hz
        return (1/self.pulsePeriod).rescale(pq.Hz)

    @property
    def trainRate(self) -> pq.Quantity:
        r"""Alias to pulseFrequency"""
        return self.pulseFrequency

    @property
    def pulseWidth(self):
        return self._pulseWidth_

    @pulseWidth.setter
    def pulseWidth(self, val):
        assert isinstance(val, pq.Quantity) and scq.checkTimeUnits(val), f"{val} is not a time quantity"
        self._pulseWidth_ = val

    @property
    def dacIndex(self) -> int:
        r"""Physical index of the DAC where this epoch was defined"""
        return self._dacNum_

    @dacIndex.setter
    def dacIndex(self, val:int):
        self._dacNum_ = val

class ABFProtocol(ElectrophysiologyProtocol):
    r"""Instance of an ABF protocol (for Clampex v ≥ 10).
    Particularities:
        • When "Alternative Waveforms" is enabled, only TWO DACs (DAC 0 and DAC 1)
        will emit analog waveforms on alternative sweeps
    """
    # BUG: 2024-10-27 09:47:18 - probably related to Clampex 11.0, to check if it
    # still occurs in Clampex 11.4.3
    #
    # When Alternate Digital Outputs is enabled in the protocol, setting a digital
    # pattern in a second DAC channel with index > 2, and setting the Digital Outputs
    # flag ON on that DAC channel seems to mess up the allocation of the DIG bits
    # to a DIG channel: both the main and alternate digital patterns are emitted
    # by the same DIG channel, when they should be emitted on the DIG channel
    # indicated in the pattern.

    # WORKAROUND: when alternate digital outputs are needed, use only DAC Channels
    # 0 and 1 for recording and for setting up the alternative digital patterns.
    #
    # These two DACs should be used anyway, by default, in electrophysiology as they
    # are typically used to send out command signals to the cells via the amplifier
    # channels "1" and "2", respectively. This mst be reflected in the LabBench.

    # TODO 2024-07-19 13:19:40 FIXME URGENTLY
    # implement code related to pyabf stimulusFilefolder & stimulusWaveformFromFile
    #
    from ephys.ephys import SynapticPathway
    from ephys.ephys import ClampMode
    from core.neoutils import getAcquisitionInfo

    def __init__(self, obj:typing.Optional[typing.Union[pyabf.ABF,neo.Block]]=None,
                 **kwargs):
        from core.neoutils import getAcquisitionInfo
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

            # total number of physical DAC channels available with digital outputs
            # NOTE: 2024-10-24 22:40:56 FIXME redundant info:
            # _nDigitalOutputs_ is the same as nDACChannels: same source, same value
            # self._nDigitalOutputs_ = obj._dacSection._entryCount

            # total number of DIG "outputs" available; these would typically be
            # 2 * self._nDigitalOutputs_ because each of those can emit either:
            # • a single pulse ("step mode"), when its byte value resolves to '1',
            # or
            # • a train of pulses ("pulse mode"), when its byte value resolves to '*'
            self._nTotalDigitalOutputs_ = obj._protocolSection.nDigitizerTotalDigitalOuts

            self._nDigitalEnable_ = obj._protocolSection.nDigitalEnable

            # not sure what this is, my guess is that it represents how many of
            # the DIG channels can emit trains ?
            # from what I gathered so far:
            # _protocolSection.nDigitizerTotalDigitalOuts = _dacSection._entryCount + _protocolSection.nDigitizerSynchDigitalOuts
            #
            self._nSynchronizedDigitalOutputs_ = obj._protocolSection.nDigitizerSynchDigitalOuts
            self._hasAltDigOutState_ = bool(obj._protocolSection.nAlternateDigitalOutputState)
            self._digTrainActiveHi_ = bool(obj._protocolSection.nDigitalTrainActiveLogic)
            self._digHolding_ = obj._protocolSection.nDigitalHolding
            digHolds = list(map(bool, obj._epochSection.nEpochDigitalOutput)) # 3,2,1,0,7,6,5,4
            self._digHoldingValue_ = list(reversed(digHolds[0:4])) + list(reversed(digHolds[4:]))
            self._digUseLastEpochHolding_ = bool(obj._protocolSection.nDigitalInterEpisode)

            # NOTE: 2024-10-24 22:02:03 WARNING new API
            # digitalPattern stored at protocol level, by emitting epoch
            self._epochsDigitalPatterns_ = getDIGPatterns(obj)

            #
            # ### END   digital outputs information

            # NOTE: 2024-03-08 22:32:29
            # this below returns a tuple - not what we want
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
            #
            # NOTE: further info indirectly via self._outputs_

            # NOTE: 2024-10-24 22:40:56 FIXME redundant info:
            # _nDigitalOutputs_ is the same as nDACChannels: same source, same value
            # self._nDigitalOutputs_ = info_dict["sections"]["DACSection"]["llNumEntries"]
            self._nTotalDigitalOutputs_ = info_dict["protocol"]["nDigitizerTotalDigitalOuts"]
            self._nDigitalEnable_ = info_dict["protocol"]["nDigitalEnable"]
            self._nSynchronizedDigitalOutputs_ = info_dict["protocol"]["nDigitizerSynchDigitalOuts"]
            self._hasAltDigOutState_ = bool(info_dict["protocol"]["nAlternateDigitalOutputState"])
            self._digTrainActiveHi_ = bool(info_dict["protocol"]["nDigitalTrainActiveLogic"])
            self._digHolding_ = info_dict["protocol"]["nDigitalHolding"]

            # allow the use of blocks read from ABF before 2023-09-20 23:26:08
            digHolds = info_dict["sections"]["EpochSection"].get("nEpochDigitalOutput", None) # 3,2,1,0,7,6,5,4

            if isinstance(digHolds, list) and len(digHolds) == self._nDACChannels_:
                digHolds = list(map(bool, digHolds))
                if self._nDACChannels_ == 8:
                    digHolds = list(reversed(digHolds[:4])) + list(reversed(digHolds[4:]))

                else:
                    digHolds = list(reversed(digHolds))

                self._digHoldingValue_ = digHolds

            else:
                self._digHoldingValue_ = [False] * self._nDACChannels_

            self._digUseLastEpochHolding_ = bool(info_dict["protocol"]["nDigitalInterEpisode"])

            # NOTE: 2024-10-24 22:02:03 WARNING new API
            # digitalPattern stored at protocol level, by emitting epoch
            self._epochsDigitalPatterns_ = getDIGPatterns(obj)

            #
            # ### END   digital outputs information

            # NOTE: 2024-03-08 22:33:34 see NOTE: 2024-03-08 22:32:29
            self._acquisitionMode_ = ABFAcquisitionMode(info_dict["protocol"]["nOperationMode"])
            self._nSweeps_ = info_dict["protocol"]["lEpisodesPerRun"]
            self._nRuns_   = info_dict["protocol"]["lRunsPerTrial"]
            self._nTrials_ = info_dict["protocol"]["lNumberOfTrials"]
            self._nTotalDataPoints_ = info_dict["sections"]["DataSection"]["llNumEntries"]
            self._nDataPointsPerSweep_ = int(info_dict["protocol"]["lNumSamplesPerEpisode"]/self._nADCChannels_)
            # self._nDataPointsPerSweep_ = int(self._nTotalDataPoints_/self._nSweeps_/self._nADCChannels_)
            self._samplingRate_ = float(info_dict["sampling_rate"]) * pq.Hz
            self._sweepInterval_ = info_dict["protocol"]["fEpisodeStartToStart"] * pq.s
            self._averaging_ = ABFAveragingMode(info_dict["protocol"]["nAverageAlgorithm"]) # 0 = Cumulative; 1 = Most recent
            self._averageWeighting_ =  info_dict["protocol"]["fAverageWeighting"]

            self._protocolFile_ = info_dict["sProtocolPath"].decode()

            self._sourceHash_ = hash(obj)
            self._sourceId_ = id(obj)
            self._fileOrigin_ = obj.file_origin

            self._inputs_ = [ABFInputConfiguration(obj, k) for k in range(self._nADCChannels_)]
            self._outputs_ = [ABFOutputConfiguration(obj, k) for k in range(self._nDACChannels_)]

        else:
            if len(kwargs) == 0:
                raise TypeError(f"A source pyabf.ABF or neo.Block object was not specified; instead, got {type(obj).__name__}; in addition, no other parameters were given, therefore cannot initialize a {self.__class__.__name__} object")

            adcChannels = kwargs.get("inputs", list())
            dacChannels = kwargs.get("outputs", list())
            self._nADCChannels_ = len(adcChannels)
            self._nDACChannels_ = len(dacChannels)
            self._activeDACChannel_ = kwargs.get("activeDACChannel", 0)
            self._hasAltDacOutState_ = kwargs.get("hasAltDacOutState", False)

            self._nTotalDigitalOutputs_ = kwargs.get("nTotalDigitalOutputs", 0)
            self._nDigitalEnable_ = kwargs.get("nDigitalEnable", 0)
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
            self._epochsDigitalPatterns_ = kwargs.get("epochsDigitalPatterns", dict())
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

        self._nAlternateDigitalOutputs_ = self._nTotalDigitalOutputs_ - self._nSynchronizedDigitalOutputs_
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

        ret.append(f"• {self.nTotalDigitalOutputs} Logical digital outputs for {self.nDIGChannels} physical DIG channels")
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
        r"""Tests for equality of scalar properties and epochs tables.
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

        if ret:
            for k in range(self.nADCChannels):
                # NOTE: Return after first iteration showing distinct ADCs
                if self.getADC(k) != other.getADC(k):
                    return False

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
        r"""Encodes this ABFProtocol as a HDF5 Group"""
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)


        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity


        attrs = dict()
        for n in ("_nADCChannels_", "_nDACChannels_", "_activeDACChannel_",
                  "_hasAltDacOutState_", "_hasAltDigOutState_",
                  "_nTotalDigitalOutputs_", "_nSynchronizedDigitalOutputs_",
                  "_epochsDigitalPatterns_", "_digTrainActiveHi_",
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

        inputs = self._inputs_
        outputs = self._outputs_

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

        # for n in ("_nADCChannels_", "_nDACChannels_", "_activeDACChannel_",
        #           "_hasAltDacOutState_", "_hasAltDigOutState_",
        #           "_nDigitalOutputs_", "_nTotalDigitalOutputs_",
        #           "_nSynchronizedDigitalOutputs_", "_digTrainActiveHi_",
        #           "_digHolding_", "_digHoldingValue_","_digUseLastEpochHolding_",
        #           "_acquisitionMode_", "_nSweeps_", "_nRuns_", "_nTrials_",
        #           "_nTotalDataPoints_", "_nDataPointsPerSweep_",
        #           "_samplingRate_", "_sweepInterval_",
        #           "_averaging_", "_averageWeighting_",
        #           "_protocolFile_","_sourceHash_", "_sourceId_", "_fileOrigin_",
        #           ):
        for n in ("_nADCChannels_", "_nDACChannels_", "_activeDACChannel_",
                  "_hasAltDacOutState_", "_hasAltDigOutState_",
                  "_nTotalDigitalOutputs_", "_nSynchronizedDigitalOutputs_",
                  "_epochsDigitalPatterns_", "_digTrainActiveHi_",
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
        return ret

    def logicalADCIndex(self, index:int) -> int:
        r"""Returns the logical index of the ADC with specified physical index.

        See also self.physicalADCIndex
        """
        if not isinstance(index, int):
            raise TypeError(f"Expecting an int; instead, got {type(index).__name__}")
        indexingMap = self.adcPhysical2LogicalIndexMap
        if index in indexingMap:
            return indexingMap[index]

        raise ValueError(f"Invalid physical ADC index: {index}")

    def physicalADCIndex(self, index:int) -> int:
        r"""Returns the physical index of the ADC with specified logical index.

        See also self.logicalADCIndex.
    """
        if not isinstance(index, int):
            raise TypeError(f"Expecting an int; instead, got {type(index).__name__}")

        indexingMap = self.adcLogical2PhysicalIndexMap
        if index in indexingMap:
            return indexingMap[index]

        raise ValueError(f"Invalid logical ADC index: {index}")

    @property
    def adcNames(self):
        r"""Names assigned to the ADCs, in the lab bench.

        This is a read-only property.

    """
        return tuple(i.name for i in self.inputs)

    @property
    def adcUnits(self):
        r"""Physical units associated with the ADCs.

        This is a read-only property.
    """
        return tuple(i.units for i in self.inputs)

    @property
    def adcLogical2PhysicalIndexMap(self):
        return dict((i.logicalIndex, i.physicalIndex) for i in self.inputs)

    @property
    def adcPhysical2LogicalIndexMap(self):
        return dict((i.physicalIndex, i.logicalIndex) for i in self.inputs)

    @property
    def dacNames(self):
        r"""Names assigned to the DACs, in the lab bench.

        This is a read-only property.

    """
        return tuple(o.name for o in self.outputs)

    @property
    def dacUnits(self):
        r"""Physical units associated with the DACs.

        This is a read-only property.
    """
        return tuple(o.units for o in self.outputs)

    @property
    def digitalPatterns(self) -> dict:
        r"""Mapping of ABF Epochs number to ABFDigitalPattern object.
        This is empty for protocols where operation mode is not episodic_stimulation.

        This is a read-only property.
    """
        return self._epochsDigitalPatterns_

    # @digitalPatterns.setter
    # def digitalPatterns(self, val:dict):
    #     if isinstance(val, dict):
    #         if all(isinstance(key, int) and key >=0 and key < self.nDACChannels for key in val.keys()):
    #             self._epochsDigitalPatterns_ = val

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
        r"""Alias to operationMode"""
        return self._acquisitionMode_

    # NOTE: 2024-11-08 12:25:51
    # this property is removed, being made obsolete by self.getDACsWithDigitalOutput
#     @property
#     def digitalOutputDACs(self) -> tuple:
#         r"""DAC channels where digital output is configured"""
#         if not self.digitalOutputEnabled:
#             return tuple()
#
#         dp = self.digitalPatterns
#
#         if len(dp) == 0:
#             return tuple()
#
#         for sweep in range(self.nSweeps):
#
#
#         return tuple(filter(lambda x: x.digitalOutputEnabled, self.DACs))

    @property
    def digitalOutputEnabled(self) -> bool:
        return self._nDigitalEnable_ == 1

    @digitalOutputEnabled.setter
    def digitalOutputEnabled(self, val:bool):
        self._nDigitalEnable_ = 1 if val else 0

    @property
    def operationMode(self) -> ABFAcquisitionMode:
        r"""
        variable_length_event = 1
        fixed_length_event = 2
        gap_free = 3
        high_speed_oscilloscope = 4 # Not supported by neo, but supported by pyabf!
        episodic_stimulation = 5

        Read-only property.

        """
        return self._acquisitionMode_

    @property
    def activeDACOutput(self) -> ABFOutputConfiguration:
        return self.outputs[self.activeDACChannelIndex]

    @property
    def activeDAC(self) -> ABFOutputConfiguration:
        r"""Alias to self.activeDACOutput"""
        return self.outputs[self.activeDACChannelIndex]

    @property
    def activeDACChannelIndex(self) -> int:
        r"""Alias to self.activeDACChannel, for backward compatibility"""
        return self.activeDACChannel

    @property
    def activeDACChannel(self) -> int:
        r"""Logical (or physical?) index of the "active" DAC channel as reported in the ABF file protocol.
        """
        # NOTE: this below doesn't (always?) report things correctly
        #
        return self._activeDACChannel_

        # I think the heuristic should be as follows:
        #
        # if there is ONLY ONE DAC emitting analog waveforms, then THAT is the active channel
        # when only one DAC channel emits waveforms, then this is the active DAC channel.
        # FIXME 2025-10-19 21:17:45 TODO
#         waveformDACs = list(filter(lambda d: d.analogWaveformEnabled, self.DACs))
#         if len(waveformDACs) == 1:
#             # if alt waveforms is ON then this channel will emit ONLY on even sweeps
#             # (0,2,4,…)
#             # otherwise, it will emit on ALL sweeps
#             return waveformDACs[0].logicalIndex
#
#         elif len(waveformDACs) > 1:
#             if self.alternateWaveformsEnabled:
#

    def getActiveDACChannel(self, sweep:int = 0) -> int | list[int] | None:
        r"""Retrieves the logical index of the DAC channel that is active during a specific sweep.
        When alternateWaveformsEnabled is True, there may be no active DAC channel
        in the sweep
        See also activeDACChannel or activeDACChannelIndex
    """
        waveformDACs = list(filter(lambda d: d.analogWaveformEnabled, self.DACs))
        if len(waveformDACs) == 0:
            return  # no DAC emits waveforms - one needs to infer the command waveform from the analog inputs
                    # possibly problematic...

        if len(waveformDACs) == 1:
            if self.alternateWaveformsEnabled:
                if sweep % 2 == 0: # even sweep (0,2,4,…)
                    return waveformDACs[0].logicalIndex
                else:
                    return # does not emit on odd sweeps (1,3,5,…)
            else:
                return waveformDACs[0].logicalIndex # used in ALL sweeps

        else: #elif len(waveformDACs) >= 2:
            dacNdx = list(map(lambda d: d.logicalIndex, waveformDACs))
            if self.alternateWaveformsEnabled: # only the first two emit commands (whether it is 0 & 1 or 1 & 2, or 1 & 3, etc, according to Clampex 11.4.3)
                if sweep % 2 == 0: # even sweep (0,2,4,…)
                    return waveformDACs[0].logicalIndex
                else: # odd sweep (1,3,5…)
                    return waveformDACs[1].logicalIndex
            else:
                # both are active during ALL sweeps, so all bets are off - need to determine from corresponding analog inputs?
                return list(map(lambda d: d.logicalIndex, waveformDACs))

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
    def nDIGChannels(self)->int:
        r"""Total number of physical DIG channels available.

        In ABF v2, during an Epoch, each physical DIG out channel can output:
        • a single TTL "step-like", determined by the logical level set to the
            DIG out i.e, 0 (low) or 5V (high)
            ∘ depending on the "Intersweep bit pattern" in Clampex protocol editor
            dialog, this will generate a single TTL "pulse" or a TTL "step" during
            the sweep

            ∘ this is configured by a '1' in the bit pattern corresponding to
            the index of the DIG out, in the "Digital bit pattern" of the Epoch
            configuration.

        • a train of TTL pulses (can contain a single pulse)
            ∘ this is configured by a '*' in the Epoch's digital bit pattern
            ∘ depending on the "Intersweep bit pattern" the last pulse in this
            train may actually be a "step"

        """
        return self._nSynchronizedDigitalOutputs_

    @property
    def nTotalDigitalOutputs(self):
        r"""Total number of logical digital output channels.

        Describes the capability of sending alternate DIG outputs through the
        physical DIG channels.

        If "Alternate Digital Outputs" is enabled in Clampex, then each physical
        DIG output can emit distinct patterns on alternate sweeps — which here
        are named as "main" and "alternate" — thus the total number of distinct
        (logical) digital output channels is 2 × number of physical DIG channels.

        Therefore, a DAQ board with 8 physical DIG channels will have 16 logical
        DIG output channels.

        """
        return self._nTotalDigitalOutputs_

    @property
    def nAlternateDigitalOutputs(self) -> int:
        r"""Number of logical "alternate" digital outputs.
        This is typically identical to nDIGChannels, and half of nTotalDigitalOutputs
        """
        return self._nAlternateDigitalOutputs_

    @property
    def digitalTrainActiveLogic(self) -> bool:
        return self._digTrainActiveHi_

    @property
    def digitalHolding(self) -> int:
        return self._digHolding_

    def getDigitalHoldingValue(self, digChannel:int) -> bool:
        return self._digHoldingValue_[digChannel]

    @property
    def digitalUseLastEpochHolding(self) -> bool:
        r"""This is :
        • False, if the states of the DIG channels active during an ABFEpoch
            return to the holding value at the end of the ABFEpoch, or
        • True, f at the end of thre ABFEpoch the DIG channels retain their
            levels achieved during the ABFEpoch"""

        return self._digUseLastEpochHolding_

    @property
    def nSweeps(self) -> int:
        r"""Number of sweeps per run or per trial average"""
        return self._nSweeps_

    @property
    def nRuns(self) -> int:
        r"""Number of runs per trial.
        All runs have the same number of sweeps (self.nSweeps)
        A trial with more than one run will save sweep-by-sweep average in the ABF
        file. This average is equivalent of a single run with self.nSweeps sweeps.
        """
        return self._nRuns_

    @property
    def nTrials(self) -> int:
        r"""This is always 1?"""
        return self._nTrials_

    @property
    def averaging(self) -> ABFAveragingMode:
        r"""Averaging mode - irrelevant when self.nRuns == 1"""
        return self._averaging_

    @property
    def averageWeighting(self) -> float:
        r"""Sweep eighting when averaging - irrelevant when self.nRuns == 1"""
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
        r"""Read-only (determined by Clampex).
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
        r"""Time interval between the starts of successive sweeps"""
        return self._sweepInterval_

    @property
    def alternateDigitalOutputStateEnabled(self) -> bool:
        r"""True if the protocol emits alternative DIG output patterns on odd/even sweeps.
        NOTE: This option produces alternative digital patterns only when the
        epochs emitting TTLs on DIG channels are configured in relation with
        DAC 0 or DAC 1.
     """
        return self._hasAltDigOutState_

    @property
    def alternateDigitalOutputsEnabled(self) -> bool:
        r"""Alias to self.alternateDigitalOutputStateEnabled"""
        return self._hasAltDigOutState_

    @property
    def alternateDACOutputStateEnabled(self) -> bool:
        r"""True if the protocol emits alternate DAC waveforms on odd/even sweeps.

        The DAC waveforms are analog signals meant to be sent to the recorded
        source (cell, membrane patch) via the amplifier's output channel, therefore
        acting as 'command' waveforms (e.g. membrane seal test, voltage ramps, or
        current injections).

        Such command waveforms are "synthesized" by the acquisition software as
        digital signals which are then converted to analog signals by the digital
        acquisition (DAQ) device and sent to the recording amplifier via a
        "digital-to-analog converter" (DAC) channel (usually labeled "Analog
        Output Channel" on the DAQ device), connected to the amplifier's
        "Command input".

        It follows that a single DAC channel can send commands to only one
        amplifier command input.

        When the protocol is configured to emit alternate command waveforms,
        these waveforms are defined as being attached to distinct DAC output
        channels sent via the DAC where they are defined, on alternate
        sweeps: waveform from the active DAC is emitted during even-indexed sweeps
        (0,2,4,… ) whereas the waveform from the "alternative" DAC is emitted
        during odd-indexed sweeps( 1,3,5, …).

        NOTE: In Clampex only the first two DACs (DAC 0 and DAC 1) support alternate
        DAC waveforms. Waveforms configured in Epochs on higer order DAC (i.e.,
        DAC with index > 1) are emitted with every sweep.
        order DACs

        """
        return self._hasAltDacOutState_

    @property
    def alternateWaveformsEnabled(self) -> bool:
        r"""Alias to self.alternateDACOutputStateEnabled"""
        return self._hasAltDacOutState_

    @property
    def sweepTimes(self) -> pq.Quantity:
        return np.array(list(map(self.getSweepTime, range(self.nSweeps)))) * pq.s

    def check_DAC_Epoch(self,
                       dac:typing.Union[ABFOutputConfiguration, int, str],
                       epoch:typing.Optional[typing.Union[ABFEpoch, int, str]]=None) -> tuple:
        r"""
        Checks that:

        1. dac belongs to this protocol, when given as an ABFOutputConfiguration, or
            points to an existing DAC in this protocol, when given as a str (DAC name)
            or int (DAC physical index);

        2. epoch belong to the specified dac, when given as an ABFEpoch, or
            points to a valid epoch in the specified dac, when given as a str
            (ABFEpoch 'letter') or int (APBEpoch index)

        Returns:
        ========
        A tuple (dac:ABFOutputConfiguration, epoch:ABFEpoch) both validated with
        respect to their parent object.

    """
        if dac is None:
            dac = self.activeDACOutput
        else:
            if isinstance(dac, (int, str)):
                dac = self.getDAC(dac)
            if not isinstance(dac, ABFOutputConfiguration) or dac not in self._outputs_:
                raise TypeError(f"Invalid DAC {dac}")

        if epoch is not None:
            # print(f"{self.__class__.__name__}.check_DAC_Epoch: dac{dac}, epoch: {epoch}")
            if isinstance(epoch, (int,str)):
                epoch = dac.getEpoch(epoch)

            elif isinstance(epoch, ABFEpoch):
                if epoch not in dac.epochs:
                    raise ValueError(f"The specified epoch {epoch} does not belong to this dac ({dac.physicalIndex} ('{dac.name}'))")

            if not isinstance(epoch, ABFEpoch) or epoch.number not in tuple(e.number for e in dac.epochs):
                raise ValueError(f"Invalid epoch specified {epoch} for DAC ({dac.physicalIndex} ('{dac.name}')) with {len(dac.epochs)} epochs")

        return dac, epoch

    def digitalOutputs(self, main: typing.Optional[
                                                    typing.Union[bool, Tribool]
                                                  ] = None,
                       trains: typing.Optional[
                                                typing.Union[bool, Tribool]
                                              ] = None,
                       sweep: typing.Optional[
                                            typing.Union[int, tuple,
                                                         ABFDigitalPattern]
                                             ] = None) -> set:
        r"""Indices of the digital output channels used in this protocol.

        By default, returns all DIG channels used in both main and alternate
        patterns, for TTL pulses and TTL trains.

        This behaviour can be refined with the two parameters:

        • alternate (False|True|None) - default is None — whether to report only
            DIG channels used in the main (False) or alternate (TRUE) pattern

        • trains (False|True|None) - default is None — whether to report only
            DIG channels used to generate single pulses (False) or trains (True).

        """

        return set(
            itertools.chain.from_iterable(
                [list(
                    itertools.chain.from_iterable(
                        [self.getActiveDigitalChannels(sweep, epoch = e, main=main, trains=trains) for e in o.epochs]
                        )
                    ) for o in self.outputs]
                )
            )
        # return set(itertools.chain.from_iterable([list(itertools.chain.from_iterable([self.getUsedDigitalOutputChannels(alternate, trains) for e in o.epochs])) for o in self.outputs]))

    def getClampMode(self, adc: typing.Union[int, str, ABFInputConfiguration] = 0,
                     dac: typing.Optional[typing.Union[int, str, ABFOutputConfiguration]] = None,
                     physicalADC:bool=True,
                     physicalDAC:bool=True) -> TypeEnum:
        r"""Infers the clamping mode used in the experiment run with this protocol.

        The inferrence is based on the physical units of the input - output signal
        pair, as follows:

        Input (ADC) units       Output (DAC) units:     Clamping mode:
        -----------------------------------------------------------
        electrical current      electrical potential    voltage clamp
        electrical potential    electrical current      current clamp

        Any other combination maps to no clampingm but NOTE that this is not
        necessarily encountered in practice. An example is the case when the
        amplifier is set in voltage follower mode (e.g. 'I=0' setting in some
        amplifiers), one measures "voltage" (hence the input, or ADC, has voltage
        units, and the "output" has current units, although not sending any
        command waveform). Technically, this is a NoClamp case.

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
        adcIndex = adc
        if not isinstance(adc, ABFInputConfiguration):
            adc = self.getADC(adcIndex, physical=physicalADC) # get first (primary) input by default

        if adc is None:
            raise ValueError(f"Specified {'physical' if physicalADC else 'logical'} ADC index {adcIndex} is invalid for this protocol")

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


    @property
    def inputs(self):
        r"""List of input configurations (ADC channels); alias to self.ADCs"""
        return self.ADCs

    @property
    def ADCs(self):
        r"""List of input configurations (ADC channels)"""
        return self._inputs_

    def getADC(self, adcChannel:typing.Union[int, str] = 0,
               physical:bool=True) -> ABFInputConfiguration:
        r"""Access the input configuration of an ADC channel with a given index or name.

        Parameters:
        -----------
        adcChannel: int or str, or None. Optional, default is None
            When an int, it represents the index (physical or logical) of the ADC.
            When a str, it represents the name of the ADC.

        physical: bool; flag to indicate if 'adcChannel', when an int, represents
            the physical channel index.

            Default is True.

        Returns:
        --------
        An ABFInputConfiguration

        """
        if isinstance(adcChannel, str):
            if adcChannel not in self.adcNames:
                raise ValueError(f"Invalid ADC channel name '{adcChannel}'")

            adcChannel = self.adcNames.index(adcChannel)

            # if physical:
            #     adcChannel = self.adcLogical2PhysicalIndexMap[adcChannel]

        inputconfs = list(filter(lambda x: x.getChannelIndex(physical) == adcChannel, self._inputs_))

        if len(inputconfs):
            return inputconfs[0]

        else:
            chtype = "physical" if physical else "logical"
            ndx = adcChannel if physical else self.adcLogical2PhysicalIndexMap.get(adcChannel, None)
            if ndx is None:
                raise ValueError(f"Invalid {chtype} ADC channel index specified ({adcChannel})")

            if ndx in range(self.nADCChannels):
                return self.inputs[ndx]

            raise ValueError(f"Invalid {chtype} ADC channel index specified ({adcChannel})")

    def getInput(self, adcChannel:int = 0, physical:bool=True) -> ABFInputConfiguration:
        r"""Calls self.getADC(…)"""
        return self.getADC(adcChannel, physical=physical)

    def inputConfiguration(self, adcChannel:typing.Union[int, str] = 0,
                           physical:bool=True) -> ABFInputConfiguration:
        r"""Calls self.getADC(…)"""
        return self.getADC(adcChannel, physical=physical)

    @property
    def DACs(self):
        r"""List of output configurations (DAC channels)"""
        return self._outputs_

    @property
    def outputs(self):
        r"""List of output configurations (DAC channels); alias to self.DACs"""
        return self.DACs

    def getDAC(self, dacChannel:typing.Optional[typing.Union[int, str]] = None,
                            physical:bool=True) -> ABFOutputConfiguration:
        r"""Access the output configuration of a DAC channel with a given index or name.

        Parameters:
        -----------
        dacChannel: int or str, or None. Optional, default is None
            When an int, it represents the index (physical or logical) of the DAC.
            When a str, it represents the name of the DAC.

        physical: bool; flag to indicate if 'dacChannel', when an int, represents
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
                raise ValueError(f"Invalid DAC channel name '{dacChannel}'")

            dacChannel = self.dacNames.index(dacChannel)
            physical=True

        elif not isinstance(dacChannel, int):
            raise TypeError(f"dacChannel expected an int or str; instead, got {type(dacChannel).__name__}")

        outputConfs = list(filter(lambda x: x.getChannelIndex(physical) == dacChannel, self._outputs_))

        if len(outputConfs):
            return outputConfs[0]
        else:
            chtype = "physical" if physical else "logical"
            raise ValueError(f"Invalid {chtype} DAC channel index specified ({dacChannel})")

    def getDigitalTrainLogicLevels(self) -> typing.Tuple[pq.Quantity]:
        r"""TTL levels for digital trains, V.
        HIGH level is 5 V, LOW level is 0 V.
        If protocol.digitalTrainActiveLogic is True then all digital pulses in
        the train are steps from OFF = LOW to ON = HIGH then back to OFF = LOW;
        otherwise, the logic is inversed: each pulse is from OFF = HIGH to
        ON = LOW, then back to OFF = HIGH

        Returns a tuple with OFF and ON values, in THIS order.
        """
        if self.digitalTrainActiveLogic:
            return (0 * pq.V, 5 * pq.V)
        else:
            return (5 * pq.V, 0 * pq.V)

    def getDigitalPulseLogicLevels(self, digChannel:int = 0) -> typing.Tuple[pq.Quantity]:
        r"""TTL levels for digital pulses.
        HIGH level is 5 V, LOW level is 0 V.

        If protocol.getDigitalHoldingValue(digChannel) is True, then a TTL pulse
        is a step from OFF = HIGH to ON = LOW; otherwise the logic is inversed.

        Returns a tuple (OFF, ON) values (in THIS order)

        See also self.getDigitalTrainLogicLevels
        """
        if self.getDigitalHoldingValue(digChannel):
            return (5 * pq.V, 0 * pq.V)
        else:
            return (0 * pq.V, 5 * pq.V)

    @property
    def digitalLogicLevels(self) -> typing.Tuple[pq.Quantity]:
        r"""Returns:
        (OFF, ON) when 'trains' is False, or
        (trainOFF, trainON) when 'trains' is True, or
        (digOFF, digON, trainOFF, trainON) in any other case

        See also:
        self.getDigitalPulseLogicLevels() and self.getDigitalTrainLogicLevels()
        """
        if self.digitalTrainActiveLogic:
            return (0 * pq.V, 5 * pq.V)
        else:
            return (5 * pq.V, 0 * pq.V)

        if isinstance(trains, bool):
            return self.getDigitalTrainLogicLevels() if trains else self.getDigitalPulseLogicLevels(digChannel)

        digOFF, digON = self.getDigitalPulseLogicLevels(digChannel)
        trainOFF, trainON = self.getDigitalTrainLogicLevels()

        return digOFF, digON, trainOFF, trainON

    def getEpochDuration(self, epoch:typing.Union[ABFEpoch, int, str],
                               dac:typing.Union[ABFOutputConfiguration, int, str],
                               sweep:int=0,
                               samples:bool=False) -> typing.Union[pq.Quantity, int]:
        r"""Actual epoch duration (in time units or samples) for the given sweep.
        Takes into account first duration and delta duration, both defined in the
        protocol, for the given DAC.

        When delta duration != 0, the epoch's actual duration is the epoch's
        first duration + delta duration × sweep.

        To get the epoch's first duration just pass sweep = 0 to this method.

        (NOTE: sweep indexing starts at 0)

        """
        dac, epoch = self.check_DAC_Epoch(dac, epoch)

        ret = epoch.firstDuration + sweep * epoch.deltaDuration
        if samples:
            return scq.nSamples(ret, self.samplingRate)
        return ret

    def getEpochDeltaDuration(self, epoch:typing.Union[ABFEpoch, int, str],
                                    dac:typing.Union[ABFOutputConfiguration, int, str],
                                    samples:bool=False) -> typing.Union[pq.Quantity, int]:
        r"""Change in epoch duration (time units or samples) with each sweep"""
        dac, epoch = self.check_DAC_Epoch(dac, epoch)

        ret = epoch.deltaDuration
        if samples:
            return scq.nSamples(ret, self.samplingRate)
        return ret

    def getEpochLevel(self, epoch:typing.Union[ABFEpoch, str, int],
                            dac:typing.Union[ABFOutputConfiguration, int, str],
                            sweep:int = 0,
                            ):
        dac, epoch = self.check_DAC_Epoch(dac, epoch)
        return epoch.firstLevel + sweep * epoch.deltaLevel

    def neoEpochForDAC(self, dac:typing.Union[ABFOutputConfiguration, int, str],
                 sweep:int=0,
                 epoch:typing.Optional[typing.Union[ABFEpoch, int, str]] = None,
                 holding:bool=True,
                 fromRunStart:bool=False,
                 name:typing.Optional[str] = None,
                 description:typing.Optional[str] = None) -> neo.Epoch:
        """
    Creates a neo.Epoch based on *all* ABFEpoch(s) defined for a DAC at a specific sweep.
    DEPRECATED — use dacEpochsToNeoEpoch
    """
        if dac is None:
            dac = self.activeDAC
        elif isinstance(dac, (int, str)):
            dac = self.getDAC(dac)
        if not isinstance(dac, ABFOutputConfiguration) or dac not in self._outputs_:
            raise TypeError(f"Invalid DAC {dac}")

        if isinstance(epoch, (ABFEpoch, str, int)):
            if isinstance(epoch, (int,str)):
                epoch = dac.getEpoch(epoch)
            if not isinstance(epoch, ABFEpoch) or epoch.number not in tuple(e.number for e in dac.epochs):
                raise ValueError(f"Invalid epoch specified {epoch} for DAC ({dac.physicalIndex} ('{dac.name}')) with {len(dac.epochs)} epochs")
            units = epoch.firstDuration.units
            times = [self.getEpochStart(epoch, dac, sweep, holding, fromRunStart, samples=False)]
            durations = [epoch.firstDuration + sweep * epoch.deltaDuration]
            labels = [epoch.letter]

            if not isinstance(name, str) or len(name.strip()) == 0:
                name = epoch.letter

        else:
            epochs = dac.epochs
            units = epochs[0].firstDuration.units
            times, durations, labels = zip(*list(map(lambda e: (self.getEpochStart(e, dac, sweep, holding, fromRunStart, samples=False),
                                                                e.firstDuration + sweep * e.deltaDuration,
                                                                e.letter),
                                                     epochs)))
            if not isinstance(name, str) or len(name.strip()) == 0:
                name = f"Epochs for dac {dac.name} in protocol {self.name}"

        return neo.Epoch(times = times, durations = durations, units=units,
                         labels = labels, name=name, description=description,
                         axis = dac.name, sweep = sweep)

    def dacEpochsToInterval(self,
                            dac:typing.Union[ABFOutputConfiguration, int, str],
                            epochs:typing.Optional[typing.Union[typing.Sequence[typing.Union[ABFEpoch, int, str]], ABFEpoch, int, str]] = None,
                            sweep:int = 0,
                            holding:bool=True,
                            fromRunStart:bool=False,
                            name:typing.Optional[str] = None,
                            description:typing.Optional[str] = None,
                            extent:bool=False,
                            merge:bool=False) -> Interval:
        r"""
    Constructs a core.datazone.Interval object from the epochs of the given DAC.
    Parameters:
    ==========
    dac
    epochs
    holding
    fromRunStart
    name
    description
    extent (False); see Interval documentation
    merge (False); when True, the result holds one (t0, t1) interval.

    See also dacEpochsToNeoEpoch, getNeoEpoch, getEpochsTable with asNeoEpoch = True
    """
        if isinstance(dac, (int, str)):
            dac = self.getDAC(dac)

        elif isinstance(dac, ABFOutputConfiguration):
            if dac not in self.DACs:
                raise ValueError("The specified DAC is not configured in this protocol")

        else:
            raise TypeError(f"'dac' expected to be an ABFOutputConfiguration, int or str; got {type(dac).__name__} instead")

        if epochs is None:
            epochs = dac.epochs

        elif isinstance(epochs, typing.Sequence):
            epochs = list(map(lambda x: x if isinstance(x, ABFEpoch) else dac.getEpoch(x), epochs))

        elif isinstance(epochs, (int, str)):
            epochs = [dac.getEpoch(epochs)]

        elif isinstance(epochs, ABFEpoch):
            epochs = [epochs]

        else:
            raise TypeError(f"Invalid epochs specification: {epochs}")

        neoEpoch = self.dacEpochsToNeoEpoch(dac, epochs, sweep, holding = holding,
                                            fromRunStart = fromRunStart,
                                            name = name,
                                            description = description)

        return Interval.fromNeoEpoch(neoEpoch, index=None, extent = extent,
                                     merge = merge,
                                     name = name,
                                     description = description)


    def dacEpochsToNeoEpoch(self,
                            dac:typing.Union[ABFOutputConfiguration, int, str],
                            epochs:typing.Optional[typing.Union[typing.Sequence[typing.Union[ABFEpoch, int, str]], ABFEpoch, int, str]] = None,
                            sweep:int = 0,
                            holding:bool=True,
                            fromRunStart:bool=False,
                            skipInterSweepInterval:bool=False,
                            name:typing.Optional[str] = None,
                            description:typing.Optional[str] = None,
                            durations:bool=False) -> neo.Epoch:
        r"""Constructs a neo.Epoch object based on *all* ABFEpochs of a DAC for a particular sweep.

.. |nbsp| unicode:: 0xA0
   :trim:

The neo.Epoch object 'times' and 'durations' attributes are derived from the |nbsp|
ABF epochs' start times and actual durations, adjusted to reflect their actual values, |nbsp| .
given the DAC, sweep, and whether alternate command waveforms are enabled in the protocol.

Returns:
--------
    A neo.Epoch annotated with the name of the DAC where it is defined and the sweep index where the actual values were obtained.

See also getNeoEpoch and getEpochsTable with asNeoEpoch = True
"""
        if isinstance(dac, (int, str)):
            dac = self.getDAC(dac)

        elif isinstance(dac, ABFOutputConfiguration):
            if dac not in self.DACs:
                raise ValueError("The specified DAC is not configured in this protocol")

        else:
            raise TypeError(f"'dac' expected tp be an ABFOutputConfiguration, int or str; got {type(dac).__name__} instead")

        if epochs is None:
            epochs = dac.epochs

        elif isinstance(epochs, typing.Sequence):
            epochs = list(map(lambda x: x if isinstance(x, ABFEpoch) else dac.getEpoch(x), epochs))

        elif isinstance(epochs, (int, str)):
            epochs = [dac.getEpoch(epochs)]

        elif isinstance(epochs, ABFEpoch):
            epochs = [epochs]

        else:
            raise TypeError(f"Invalid epochs specification: {epochs}")

        if len(epochs) == 0:
            return

        times, durations, labels = zip(*list(map(
            lambda epoch: (
                            self.getEpochStart(epoch, dac, sweep,
                                               holding=holding,
                                               fromRunStart=fromRunStart,
                                               skipInterSweepInterval=skipInterSweepInterval).rescale(self.sweepDuration.units),
                            self.getEpochDuration(epoch, dac, sweep).rescale(self.sweepDuration.units),
                            epoch.letter
                            ),
            epochs)))

        if not isinstance(name, str) or len(name.strip()) == 0:
            name = f"{dac.name}_sweep_{sweep}_ABFEpochs"

        if not isinstance(description, str) or len(description.strip()) == 0:
            description = f"ABFEpochs for DAC {dac.name} in sweep {sweep}"

        ret = neo.Epoch(times = times, durations = durations, labels = labels,
                        units = times[0].units, name = name,
                        description = description,
                        axis = dac.name,
                        sweep = sweep)

        return ret

    def getEpochStart(self, epoch:typing.Union[ABFEpoch, str, int],
                            dac:typing.Union[ABFOutputConfiguration, int, str],
                            sweep:int = 0,
                            holding:bool=True,
                            fromRunStart:bool=False,
                            skipInterSweepInterval:bool=False,
                            samples:bool=False) -> pq.Quantity:
        r"""Starting time of the epoch (in time units or samples) relative to run or sweep.

.. |nbsp| unicode:: 0xA0
   :trim:

Parameters:
-----------
:epoch: ABFEpoch, str (epoch letter) or int (epoch index, 0-based)
:dac: ABFOutputConfiguration (i.e. a DAC output), str (DAC name), or
    int (DAC physical index)
:sweep: index of the sweep; must be in the half-open interval [0, nSweeps)
:holding: When True (default), timings include the sweep holding time,
    equivalent to the 1/64 × the number of samples in a sweep
:fromRunStart: When True, the ABFEpoch start time is calculated from the
    start of the run (thus taking into account the time elapsed during
    previous sweeps and including any inter-sweep interval)
    Default is False.
:skipInterSweepInterval: Used when fromRunStart is True. When True, the sweep start to sweep start interval will be skipped
:samples:bool When True, return the start of Epoch in samples, rather than
    time units.
    Default is False.
"""
        dac, epoch = self.check_DAC_Epoch(dac, epoch)
        units = epoch.firstDuration.units

        # summate duration of all previous epochs (this always comes in time units)
        ret = np.sum([self.getEpochDuration(e_, dac, sweep, samples).rescale(units) for e_ in dac.epochs[:epoch.number]]) * units

        if samples:
            ret = scq.nSamples(ret, self.samplingRate)
            if holding:
                ret += self.holdingSampleCount
        else:
            if holding:
                ret += self.holdingTime

        if fromRunStart:
            if samples:
                # only useful is representing data as a continuous signal !!!
                sweepInterval = self.sweepSampleCount
            else:
                if skipInterSweepInterval:
                    sweepInterval = self.sweepDuration
                else:
                    sweepInterval = self.sweepInterval

            ret += sweepInterval * sweep

        return ret

    def getEpochStartStop(self, epoch:typing.Union[ABFEpoch, str, int],
                            dac:typing.Union[ABFOutputConfiguration, int, str],
                            sweep:int = 0,
                            holding:bool=True,
                            fromRunStart:bool=False,
                            samples:bool=False) -> typing.Tuple[typing.Union[pq.Quantity, int]]:
        t0, t1 = (self.getEpochStart(epoch, dac, sweep, holding, fromRunStart, samples),
                  self.getEpochDuration(epoch, dac, sweep, samples))

        t1 += t0
        return (t0, t1)

    def getEpochPulseCount(self, epoch:typing.Union[ABFEpoch, int, str],
                                 dac:typing.Union[ABFOutputConfiguration, int, str],
                                 sweep:int=0):
        dac, epoch = self.check_DAC_Epoch(dac, epoch)
        if float(epoch.pulsePeriod) == 0.:
            return 0
        return int(np.ceil(self.getEpochDuration(epoch, dac, sweep)/epoch.pulsePeriod))

    def getEpochPulsePeriod(self, epoch:typing.Union[ABFEpoch, int, str],
                                  dac:typing.Union[ABFOutputConfiguration, int, str],
                                  samples:bool=False):
        dac, epoch = self.check_DAC_Epoch(dac, epoch)

        if samples:
            return scq.nSamples(epoch.pulsePeriod, self.samplingRate)

        return epoch.pulsePeriod

    def getEpochPulseTimes(self, epoch:typing.Union[ABFEpoch, int, str],
                                 dac:typing.Union[ABFOutputConfiguration, int, str],
                                 sweep:int = 0,
                                 holding:bool=True,
                                 fromRunStart:bool=False,
                                 samples:bool=False) -> tuple:
        dac, epoch = self.check_DAC_Epoch(dac, epoch)

        pc = self.getEpochPulseCount(epoch, dac, sweep)
        pp = self.getEpochPulsePeriod(epoch, dac, samples)

        if pc == 0:
            return tuple()

        t0 = self.getEpochStart(epoch, dac, sweep, holding, fromRunStart, samples)

        return tuple(t0 + pp * p for p in range(pc))

    def getEpochPulseWidth(self, epoch:typing.Union[ABFEpoch, int, str],
                                 dac:typing.Union[ABFOutputConfiguration, int, str],
                                 samples:bool=False) -> int:
        dac, epoch = self.check_DAC_Epoch(dac, epoch)
        if samples:
            return scq.nSamples(epoch.pulseWidth, self.samplingRate)
        return epoch.pulseWidth

    def getPreviousSweepLastEpochLevel(self, dac:typing.Union[ABFOutputConfiguration, int, str],
                                       sweep:int) -> pq.Quantity:
        r"""Final analog value in the previous epoch"""
        # FIXME: 2023-09-18 23:34:27
        # this can become very expensive for many sweeps!
        dac, _ = self.check_DAC_Epoch(dac, None)

        if len(dac.epochs) == 0 or sweep == 0:
            return dac.dacHoldingLevel

        if dac.returnToHold:
            prevLevel = dac.dacHoldingLevel
            for s in range(sweep):
                for e in dac.epochs:
                    prevLevel = self.getEpochAnalogWaveform(e, prevLevel, s,
                                                            dac, lastLevelOnly=True)

            return prevLevel

        return dac.dacHoldingLevel

    def getPreviousSweepLastDigitalLevel(self, dac:typing.Union[ABFOutputConfiguration, int, str],
                                         sweep:int, digChannel:int) -> pq.Quantity:
        dac, _ = self.check_DAC_Epoch(dac, None)
        # BUG: 2024-10-23 01:49:44 FIXME
        # what is the last epoch digital level ?!?
        if len(dac.epochs) == 0 or sweep == 0:
            return digOFF * pq.V

        if self.digitalUseLastEpochHolding:
            prevLevel = digOFF * pq.V
            for s in range(sweep):
                for e in dac.epochs:
                    prevLevel = self.getEpochDigitalWaveform(e, s, dac,
                                                             digChannel, lastLevelOnly=True)

                return prevLevel

        return digOFF * pq.V

    def getActiveDigitalChannels(self, sweep: typing.Optional[typing.Union[int, tuple]] = None,
                               epoch:typing.Optional[
                                                typing.Union[ABFEpoch, int, str]
                                                    ] = None,
                               letters: bool = False,
                               main: typing.Optional[
                                                    typing.Union[bool, Tribool]
                                                    ] = None,
                               trains:typing.Optional[
                                                    typing.Union[bool, Tribool]
                                                    ] = None,
                               ) -> list[dict]:
        r"""Queries the active DIG channels in a given sweep, or in all sweeps.

.. |nbsp| unicode:: 0xA0
   :trim:


By default this reports the DIG channels used for emitting a TTL "pulse"
(i.e. single pulse) or a "train", in the digital pattern that would be active
given the specified sweep.

This behaviour can be fine-tuned with the parameters below.

Parameters:
-----------
:sweep: int, in the semi-open interval [0, nSweeps); default is None (queries all |nbsp|
    sweeps).

:epoch: and ABFEpoch object, an int (epoch number) or a str (epoch "letter")

        Index of the ABFEpoch where the pattern is queried.

        Optional, default is None, in which case returns the digital |nbsp|
        patterns for all epochs, during the specified sweep.

:letters:, default is False. Used when 'epoch' parameter is None.

        When True, the epochs are reported by their letter; otherwise, |nbsp|
        they are reported by their number in the epochs table.

:main: Optional, default is None.

    When None, report digital channels used in either "main" or "alternate" |nbsp|
    pattern.

    When True, report only digital channels used in the "main" pattern. |nbsp|
    When False, report only digital channels used in the "alternate" pattern.

:trains: Optional, default is None.

    When None, reports the used digital channels regardless of them being |nbsp|
    configured to emit either a step (a.k.a single pulse) or a train (pulse train) |nbsp|

    When True, report only digital channels emitting a pulse train. |nbsp|
    When False, report only digital channels emitting a step (single pulse) |nbsp|


Returns:
--------

When 'epoch' is specified and not None return a tuple (posssibly empty) |nbsp|
with the indexes of the DIG channels emitting signals during the specified |nbsp|
sweep, in that epoch.

When 'epoch' is None, returns a mapping:

letters:            returned mapping:
------------------------------------------------------------------------
False               epoch_number ↦ a tuple as above
True                epoch_letter ↦ a tuple as above


"""


        if isinstance(main, bool):
            main = Tribool(main)
        elif main is None:
            main = Tribool()
        elif not isinstance(main, Tribool):
            raise TypeError(f"'main' expected a bool, Tribool, or None; instead got a {type(main).__name__}")

        if isinstance(trains, bool):
            trains = Tribool(trains)
        elif trains is None:
            trains = Tribool()
        elif not isinstance(trains, Tribool):
            raise TypeError(f"'trains' expected a bool, Tribool, or None; instead got a {type(trains).__name__}")

        comparator = lambda x: (x != 0 if trains.value is None else x == "*" if trains.value else x == 1)

        index = lambda p: tuple(map(lambda i: i[0], filter(lambda i: comparator(i[1]), enumerate(p))))

        # index = lambda p: tuple(sorted(map(lambda c: p.index(c), ("*", 1)))) if trains.value is None else lambda p: (p.index("*"), ) if trains.value else lambda p: set(p.index(1), )

        # print(f"{self.__class__.__name__}.getActiveDigitalChannels: sweep = {sweep}")

        if sweep is None:
            sweeps = range(self.nSweeps)

        elif isinstance(sweep, tuple):
            if not all(isinstance(s, int) and s in range(self.nSweeps) for s in sweep):
                raise ValueError(f"Invalid sweep indexes for {self.nSweeps} sweeps ")

            sweeps = sweep

        elif isinstance(sweep, int):
            if sweep not in range(self.nSweeps):
                raise ValueError(f"Invalid sweep index ({sweep}) for {self.nSweeps} sweeps ")

            sweeps = (sweep, )

        else:
            raise TypeError(f"'sweep' argument has invalid type {type(sweep).__name__}")


        ret = list()

        for sweep in sweeps:
            # sweep_result = dict()
            sweep_result = {"sweep": sweep, "epochs": dict()}
            if epoch is None:
                for e in self.digitalPatterns:
                    # pattern = self.digitalPatterns[e]
                    key = getEpochLetter(e) if letters else e
                    pattern = self.getEpochDigitalPattern(e, main=main, separateBanks=False) # uses natural=True and separateBanks = False
                    # print(f"{self.__class__.__name__}.getActiveDigitalChannels epoch {key} -> pattern = {pattern}")
                    if all(isinstance(p, tuple) for p in pattern):
                        # value = tuple(map(index, pattern))
                        ndx = tuple(filter(lambda t: len(t)>0, map(index, pattern)))
                        if any(len(x) for x in ndx):
                            val = dict(zip(("main", "alternate"), ndx))
                            sweep_result["epochs"][key] = val

                    else:
                        ndx = index(pattern)
                        if len(ndx):
                            which = "main" if main.value == True else "alternate"
                            sweep_result["epochs"][key] = {which: ndx}

                if len(sweep_result["epochs"]):
                    ret.append(sweep_result)

            else:
                if isinstance(epoch, int):
                    if epoch not in self.digitalPatterns:
                        raise ValueError(f"Invalid epoch index {epoch}")

                    key = getEpochLetter(epoch) if letters else epoch

                    pattern = self.getEpochDigitalPattern(epoch, main=main, separateBanks=False)

                elif isinstance(epoch, str):
                    e = getEpochNumberFromLetter(epoch)
                    if e not in self.digitalPatterns:
                        raise ValueError(f"Invalid epoch index {e}")

                    key = epoch if letters else e

                    pattern = self.getEpochDigitalPattern(e, main=main, separateBanks=False)

                elif isinstance(epoch, ABFEpoch):
                    e = epoch.number
                    if e not in self.digitalPatterns:
                        raise ValueError(f"Invalid epoch index {e}")
                    key = epoch.letter if letters else epoch.number

                    pattern = self.getEpochDigitalPattern(epoch, main=main, separateBanks=False)

                else:
                    raise TypeError(f"'epoch' has invalid type ({type(epoch).__name__})")

                # print(f"{self.__class__.__name__}.getActiveDigitalChannels epoch {key}-> pattern = {pattern}")

                if all(isinstance(p, tuple) for p in pattern):
                    ndx = tuple(filter(lambda t: len(t)>0, map(index, pattern)))
                    if any(len(x) for x in ndx):
                        sweep_result["epochs"][key] = dict(zip(("main", "alternate"), tuple(map(index, pattern))))

                else:
                    ndx = index(pattern)
                    if len(ndx):
                        which = "main" if main.value else "alternate"
                        sweep_result["epochs"][key] = {which: index(pattern)}

                if len(sweep_result["epochs"]) > 0:
                    ret.append(sweep_result)

        return ret

    @property
    def epochsWithDigitalOutput(self) -> tuple:
        r"""A tuple of all ABFEpoch numbers where a digital output is defined.

    Read-only.
    """
        return tuple(map(lambda x: x[0],
                         filter(lambda x: not all (x_ ==0 for x_ in x[1]),
                                map(lambda i: (i[0], tuple(itertools.chain.from_iterable(i[1].main + i[1].alternate))),
                                    self.digitalPatterns.items()))))

    def getDACsWithDigitalOutput(self) -> list:
        r"""List of DACs that emit digital outputs.

    Read-only.
    """
        digEpochs = self.epochsWithDigitalOutput
        ret = set() # DAC physical indexes
        for epoch in digEpochs:
            dacs = self.getDACsForEpoch(epoch) # DAC physical indexes
            for dac in dacs:
                ret.add(dac)
        return sorted(list(ret))

    @property
    def digitalOutputDACs(self) -> list:
        r"""Property version of self.getDACsWithDigitalOutput; read-only.
    """
        return self.getDACsWithDigitalOutput()


    def getDACsForEpoch(self, epoch:typing.Union[ABFEpoch, str, int]) -> tuple:
        r"""A tuple of DAC physical indexes where the epoch is defined.

        Parameters:
        -----------
        epoch: ABFEpoch, str (epoch letter(s)) or int (epoch number)

        CAUTION: is 'epoch' is an ABFEpoch, all of its parameters will be compared
        to those of the epochs in every DAC. This may not be always useful.

        If the intention is only to obtain the DAC indexes where an epoch with a
        given number or letter(s) is defined, then pass that number or letter(s)
        as 'epoch' parameter.

        """
        if isinstance(epoch, ABFEpoch):
            return tuple(dac.physicalIndex for dac in self.DACs if epoch in dac.epochs)

        elif isinstance(epoch, int):
            # No not check against len(dac.epochs), because this iss irrelevant
            return tuple(dac.physicalIndex for dac in self.DACs if epoch in (tuple(e.number for e in dac.epochs)))

        elif isinstance(epoch, str):
            return tuple(dac.physicalIndex for dac in self.DACs if epoch in (tuple(e.letter for e in dac.epochs)))

        else:
            raise TypeError(f"Expecting an ABFEpoch, int or str; instead, got a {type(epoch).__name__}")

    def getEpochDigitalPattern(self, epoch:typing.Union[ABFEpoch, int, str, typing.Sequence],
                          /,
                          main: typing.Optional[
                                            typing.Union[bool, Tribool]
                                            ] = None,
                          natural: bool = True,
                          separateBanks: bool = True,
                          letters: bool = False) -> tuple:
        r"""
        Queries the digital pattern defined in an ABFEpoch.

        A digital pattern is a sequence of 0, 1, or '*' where the position of
        each element corresponds to the index of a DIG output channel.

        The meaning of these values is given below:

        Element     Logical state of the                Effect:
        value:      DIG channel during the epoch:
        ------------------------------------------------------------------
        0   (int)   Low (OFF)                           No output
        1   (int)   High (ON)                           A "step" output¹
        '*' (str)   Mutiple OFF↔ON                      A "train" of pulses
                    transitions

        ¹ When an epoch emits a "step" on a DIG channel this can be seen as a
        single pulse if the getDigitalHoldingValue() returns True for that DIG
        channel.

        Digidata DAQ boards 1440 and 1550 series provide 8 digital output channels.

        In Clampex v 11.+ (possibly in Clampex 10, too) these digital output
        channels are accesses via two banks, corresponding to two digital bit
        patterns in each epoch inside the Waveform tabs:

        Digital bit pattern #3-0
        Digital bit pattern #7-4

        Buy default all entries are 0, but they can be set to 1 or '*' (see above)
        when the Epoch type is set anything other than "Off".

        The digital bit pattern corresponds to the way the DIG output are stored
        in the protocol, and can be relatively hard to work with, directly.

        When Alternate Digital Outputs is enabled in the protocol, one can configure
        two digital bit patterns for the same epoch. The "main" pattern is specified
        in the Waveform tab for the DAC channel where "Digital Outputs" is enabled,
        whereas the "alternate" pattern is specified in the Waveform tab for a
        distinct DAC channel. See self.getEpochstable(…) for details.

        By default, this method reports the digital bit pattern AS IT WOULD BE
        used during the specified sweep (i.e., when self.alternateDigitalOutputsEnabled
        is True, it returns the "main" or the "alternate" pattern, depending
        on the sweep). The returned digital bit pattern is reversed and unpacked,
        such that for any given epoch it will return a tuple of 8 values representing
        the DIG channel indexes in "natural" order, i.e., #0-7, as a single bank.

        This behaviour can be fine-tuned using the parameters below.

        Parameters:
        -----------
        :epoch: and ABFEpoch object, an int (epoch number) or a str (epoch "letter"),
                or a sequence of such.
                Index of the ABFEpoch where the pattern is queried.

        :main: bool or str. Optional, default is None.
            When True, report only the "alternate" pattern.
            When False, report only the "main" pattern.

            When None, report both the "main" or "alternate" pattern wrapped in
            an ABFDigitalPattern¹ object as follows:

        :natural: bool, whether to return the pattern in the "natural" (i.e.,
            increasing) order of the DIG channel indexes — i.e. 0 ⋯ 7
                default is True;

        :separateBanks: default is True
            True            ⇒ the "main" and "alternate" fields of the
                            ABFDigitalPattern are each a pair of 4-tuples

            False           ⇒ the "main" and "alternate" fields of the
                            ABFDigitalPattern are each a tuple of all digital
                            channels in the pattern (8, in Clampex 11.+)

        :separateBanks:bool, whether to return the pattern as two tuples, one for
                each bank of 4 DIG channels;
                default is False;

        :letters:bool, default is False. Used when 'epoch' parameter is None.
                When True, the epochs are reported by their letter; otherwise,
                they are reported by their number in the epochs table.

        NOTE: Passing:
        `natural=False, separateBanks=False, alternate = None`
        is the same as querying the mapping of the digital patterns directly:

        `self.digitalPatterns[epoch.number]`

        ¹ An ABFDigitalPattern object is a named tuple with two fields:
            "main" and "alternate", each being a tuple (bit pattern, or DIG index)

        Returns:
        --------

        When 'epoch' is specified and not None, returns a tuple with the digital
        but pattern as in the table below:

        separateBanks       natural         returns
        ------------------------------------------------------------------------
        True                False           A 2-tuple[4-tuple[int]] corresponding
                                            to the two DIG output banks in the
                                            order 3⋯0, 7⋯4.

        True                True            A 2-tuple[4-tuple[int]] corresponding
                                            to the two DIG output banks in the
                                            order 0⋯3, 4⋯7.

        False               False           An 8-tuple[int] corresponding to the
                                            DIG channels in the order 7 ⋯ 0

        True                True            An 8-tuple[int] corresponding to the
                                            DIG channels in the order 0 ⋯ 7

        When 'epoch' is None, returns a mapping:

        letters:            returned mapping:
        ------------------------------------------------------------------------
        False               epoch_number ↦ a tuple as in the table above
        True                epoch_letter ↦ a tuple as in the table above

        """
        if isinstance(epoch, typing.Sequence):
            ret = dict()
            for e in self.digitalPatterns:
                if isinstance(e, int):
                    key = getEpochLetter(e) if letters else e

                elif isinstance(e, str):
                    key = e if letters else getEpochNumberFromLetter(e)

                elif isinstance(e, ABFEpoch):
                    key = e.letter if letters else e.number

                else:
                    raise TypeError(f"Invalid epoch specification {e} in {epochs}")

                ret[key] = self.getEpochDigitalPattern(e, main = main,
                                                  natural = natural,
                                                separateBanks = separateBanks,
                                                )
            return ret

        elif isinstance(epoch, str):
            epochNum = getEpochNumberFromLetter(epoch)

        elif isinstance(epoch, int):
            epochNum = epoch

        elif isinstance(epoch, ABFEpoch):
            epochNum = epoch.number

        else:
            raise TypeError("Expecting an ABFEpoch, int or str; got ")

        if isinstance(main, bool):
            main = Tribool(main)
        elif main is None:
            main = Tribool()
        elif not isinstance(main, Tribool):
            raise TypeError(f"'main' expected a bool, Tribool, or None; instead, got a {type(main).__name__}")

        src = "all" if main.value is None else "main" if main.value else "alternate"

        if epochNum in self.digitalPatterns:
            pattern = self.digitalPatterns[epochNum]
            if natural:
                ret = pattern if pattern.reversed else pattern.reverse()
            else:
                ret = pattern

            if src != "all":
                ret = getattr(ret, src)
                if not separateBanks:
                    ret = tuple(itertools.chain.from_iterable(ret))
            else:
                if not separateBanks:
                    ret = tuple(map(lambda x: tuple(itertools.chain.from_iterable(x)), ret[:2]))
                else:
                    ret = ret[:2]

            return ret

        else:
            # construct an inactive pattern
            pattern = ((((0,) * (self.nDIGChannels//2), ) * 2, ) * 2)
            if separateBanks:
                if src == "all":
                    return ABFDigitalPattern(*pattern)[:,2]

                return (0,) * (self.nDIGChannels//2), (0,) * (self.nDIGChannels//2)

            return (0,) * self.nDIGChannels

    def getActiveDigitalChannelsInEpoch(self, epoch:typing.Union[
                                            ABFEpoch, int, str, typing.Sequence
                                            ],
                                        /,
                                        main: typing.Optional[
                                                    typing.Union[bool, Tribool]
                                                            ] = None
                                        ) -> tuple:
        r"""Obtain the indexes of active digital channels in an ABFEpoch.


.. |nbsp| unicode:: 0xA0
   :trim:

    Parameters:
    -----------

    :epoch: An ``ABFEpoch`` or the number or letter of the ABFEpoch to be queried.

    :main: Flag indicating whether rthe method queries the *main* (``True``), |nbsp|
        *alternate*, or *both* digital patterns in the epoch (if there are any)

    Returns:
    --------
        When ``main`` is ``None`` or a ``Tribool`` with value of ``None``, returns |nbsp|
        a pair of tuples (one each, for the *main* and the *alternate* digital |nbsp|
        pattern), containing the indexes of the DIG channel active in the Epoch, |nbsp|
        when either of these patterns would be enacted.

        Either of these tuples may be empty of not DIG channel is active in the |nbsp|
        corresponding digital pattern.

        When ``main`` a ``bool`` or a ``Tribool`` with value ``True`` or ``False``, |nbsp|
        returns a single tuple with the indexes of the DIG channels that are active when |nbsp|
        the *main* (``True``) or *alternate* (``False``) digital pattern is enacted.

        This tuple may be empty if no DIG channel is active in the selected digital |nbsp| pattern.


    .. note::

        The enacting of the *main* or *alternate* digital pattern during an |nbsp|
        ABFEpoch depends on whether the protocol has alternate digital outputs |nbsp|
        enabled, and on whether the sweep index is odd or even.

        While this method operates independently of these criteria, it allows |nbsp|
        for the queried digital pattern to be specified by prior decision based on |nbsp|
        these criteria.

    """

        if main is None:
            main = Tribool()

        elif isinstance(main, bool):
            main = Tribool(main)

        elif not isinstance(main, Tribool):
            raise TypeError(f"'main' expected a bool, Tribool, or None; instead, got a {type(main).__name__}")


        digPattern = self.getEpochDigitalPattern(epoch, main = main,
                                                 separateBanks=False) # either main or alternate, depending on the sweep
        if main.value is None:
            return tuple(
                            map(
                                lambda t: tuple(
                                                map(lambda x: x[0],
                                                    filter(
                                                            lambda x: x[1] !=0,
                                                            enumerate(t)
                                                           )
                                                    )
                                                ),
                                digPattern
                                )
                         )
        else:
            return tuple(map(lambda x: x[0], filter(lambda x: x[1] !=0, enumerate(digPattern))))



    def getEpochDigitalTriggers(self, epoch: typing.Union[ABFEpoch, str, int], /,
                             sweep:int = 0,
                             dac:typing.Optional[typing.Union[ABFOutputConfiguration, int, str]] = None,
                             digChannel:typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
                             eventType:typing.Optional[TriggerEventType] = TriggerEventType.presynaptic,
                             label:typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
                             name:typing.Optional[str] = None,
                             enableEmptyEvent:bool=True,
                             holding:bool=True,
                             fromRunStart:bool=False) -> typing.Optional[TriggerEvent | typing.Sequence[TriggerEvent]]:
        r""" TriggerEvent emitted by digital output channels (TTLs) during an ABF Epoch.

        For an Epoch of type Step or Pulse AND where digital output is enabled (i.e.
        the digital pattern is non-zero in any DIG output) the method will generate
        TriggerEvents (in the time domain) based on the specified digital channel(s)

        Otherwise, the method return None or an empty TriggerEvent (see
        'enableEmptyEvent' parameter, below).

        NOTE: A TriggerEvent object (see 'core.triggerevent' module) can contain
        more than one time stamp. Since an Epoch can, in principle, use more than
        one DIG channel to emit TTL signals, the method will return as many
        trigger events as DIG channels queried (these can be all DIG channels
        emitting TTLs if the 'digChannel' parameter is None).

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

            When None, the method will generate TriggerEvent instances using
            digital patterns from  ALL used digital channels (if any).

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

        eventType: optional; default is TriggerEventType.presynaptic for
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

        A TriggerEvent object, or a sequence of TriggerEvents, or None.

        NOTE 1: Digital signals (triggers) are emitted during epochs defined on
        the "active" DAC

        NOTE 2: An ABF Epoch supports sending digital signals simultaneously via
        more than one digital output channel; however, Clampex does not support
        defining different timings for distinct digital output channels, EXCEPT
        for the case where digital train and digital pulse are emitted by
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
        if sweep not in range(self.nSweeps):
            raise ValueError(f"Invalid sweep index {sweep} for {self.nSweeps} sweeps")

        actualOutput = dac is None

        dac, epoch = self.check_DAC_Epoch(dac, epoch)

        hoDACActive = self.activeDACChannel not in (0,1)

        isAlternateDigital = False

        if self.alternateDigitalOutputsEnabled:
            if actualOutput:
                if hoDACActive:
                    isAlternateDigital = True
                else:
                    isAlternateDigital =  sweep % 2 > 0
            else:
                isAlternateDigital = dac.physicalIndex != self.activeDACChannel

        if actualOutput:
            if self.alternateDigitalOutputsEnabled:
                digDACs = self.getDACsForEpoch(epoch.number)
                if len(digDACs) > 1:
                    assert dac.physicalIndex in digDACs, f"DAC {dac.physicalIndex} not in digital-emitting DACs"
                    # thisDacNdx = digDACs.index(dac.physicalIndex)
                    if self.activeDACChannel == 0:
                        myDac = self.getDAC(1 if isAlternateDigital else 0)
                    elif self.activeDACChannel == 1:
                        myDac = self.getDAC(0 if isAlternateDigital else 1)
                    else:
                        assert hoDACActive, f"Active DAC index expected to be > 1; got {self.activeDACChannel}"
                        # activeDAC is a HO DAC
                        if sweep % 2 == 0 and 0 in digDACs: # "even" sweeps => query DAC0
                            myDac = self.getDAC(0)
                        elif sweep % 2 > 0 and 1 in digDACs: # "odd" sweeps => query DAC1
                            myDac = self.getDAC(1)
                        else:
                            myDac = dac
                            # continue

                    # to report correct temporal params for epoch in DAC, given sweep index
                    myEpoch = myDac.getEpoch(epoch.number)

                else:
                    myDac = dac
                    myEpoch = epoch

            else:
                myDac = dac
                myEpoch = epoch
        else:
            # OK here: shows the Epoch table AS DEFINED in Clampex, regardless
            # of the sweep
            myDac = dac
            myEpoch = epoch

        # print(f"{self.__class__.__name__}.getEpochDigitalTriggers: myEpoch.type = {myEpoch.type.name}")

        if myEpoch.type not in (ABFEpochType.Step, ABFEpochType.Pulse):
            return TriggerEvent(event_type = eventType, name=name, labels = label) if enableEmptyEvent else None

        digPattern = self.getEpochDigitalPattern(myEpoch, main = not isAlternateDigital) # either main or alternate, depending on the sweep

        linearDigPattern = tuple(itertools.chain.from_iterable(digPattern))
        # usedDigs = tuple(map(lambda x: x[0], filter(lambda x: x[1] !=0, enumerate(itertools.chain.from_iterable(digPattern)))))

        if isinstance(digChannel, int):
            digChannel = (digChannel,)

        elif digChannel is None:
            # digChannel = tuple(map(lambda x: x[0], filter(lambda x: x[1] !=0, enumerate(itertools.chain.from_iterable(digPattern)))))
            digChannel = tuple(map(lambda x: x[0], filter(lambda x: x[1] !=0, enumerate(linearDigPattern))))

        elif isinstance(digChannel, (tuple, int)) and all(isinstance(v, int) for v in digChannel) :
            digChannel = tuple(sorted(set(digChannel)))

        else:
            raise TypeError(f"Unexpected digChannel specification {digChannel}")

        # print(f"{self.__class__.__name__}.getEpochTriggers: epoch = {myEpoch}, dac = {myDac}, sweep = {sweep}, pulseCount = {pulseCount}, digChannel = {digChannel}")

        if len(digChannel) == 0:
            return TriggerEvent(event_type = eventType, name=name, labels = label) if enableEmptyEvent else None

        else:
            trigs = list()
            digChannelValue = tuple(linearDigPattern[chnl] for chnl in digChannel)
            # print(f"{self.__class__.__name__}.getEpochTriggers: digChannelValue = {digChannelValue}")
            for k, chnl in enumerate(digChannel):
                times = list()
                if digChannelValue[k] == 1:
                    times = [self.getEpochStart(epoch, myDac, sweep, holding, fromRunStart).rescale(pq.s)]
                elif digChannelValue[k] == "*":
                    tt = self.getEpochPulseTimes(epoch, myDac, sweep, holding, fromRunStart)
                    if len(tt):
                        times = [x.rescale(pq.s) for x in tt]

                if len(times):
                    trig = TriggerEvent(times=times, units = pq.s, event_type = eventType,
                                    name=name, labels = label)
                else:
                    trig = TriggerEvent(event_type = eventType, name=name, labels = label) if enableEmptyEvent else None

                if isinstance(trig, TriggerEvent) and trig.size > 0:
                    # see BUG: 2023-10-03 17:57:30 in triggerevent.TriggerEvent.__new__
                    # if isinstance(label, str) and len(label.strip()):
                    #     trig.labels = [f"{label}{k}" for k in range(trig.times.size)]

                    if trig not in trigs:
                        trigs.append(trig)

            if len(trigs):
                return (trigs[0] if len(trigs) == 1 else trigs)

            else:
                return TriggerEvent(event_type = eventType, name=name, labels = label) if enableEmptyEvent else None

    def getEpochDACTriggers(self, epoch:typing.Union[ABFEpoch, str, int], /,
                            sweep:int=0,
                            dac:typing.Optional[typing.Union[ABFOutputConfiguration, int, str]] = None,
                            eventType:typing.Optional[TriggerEventType] = TriggerEventType.presynaptic,
                            label:typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
                            name:typing.Optional[str] = None,
                            maxPulseDuration:pq.Quantity = 1*pq.ms,
                            enableEmptyEvent:bool=True,
                            fromRunStart:bool=False,
                            holding:bool = True,
                            perEpoch:bool=False,
                            asNeoEvent:bool=False) -> dict:
        r"""Obtain TriggerEvent objects encoded as analog step or pulse waveforms.
        Returns a mapping dac name ↦ TriggerEvent or list of TriggerEvent objects

        Whe perEpoch is True, the mapping contains a list of TriggerEvent objects
        with one per DAC Epoch; whe False (the default) the ammping contains a
        TriggerEvent per DAC.

        DACs without TTL-emulating waveforms (± 5V pulse or step epochs, the latter
        with duration <= maxPulseDuration) are excluded.


        """
        if sweep not in range(self.nSweeps):
            raise ValueError(f"Invalid sweep index {sweep} for {self.nSweeps} sweeps")

        actualOutput = dac is None

        if asNeoEvent:
            cls = neo.Event
        else:
            cls = TriggerEvent

        dac, _ = self.check_DAC_Epoch(dac, None)

        digDACs = self.getDACsWithDigitalOutput()

        if len(digDACs) == 0 or dac.physicalIndex not in digDACs:
            return TriggerEvent(event_type = eventType, name=name, labels = label) if enableEmptyEvent else None

        # epochs with DAC-emulated triggers are of type step or pulse; for step epochs
        # the duration of the step must be <= maxPulseDuration; for both types,
        # the epoch level must be 5 V (TTL-like)
        ret = dict()
        for dac in digDACs:
            isTTLlike= lambda e: np.abs(e.firstLevel) == 5 * pq.mV and e.deltaLevel == 0 and e.firstDuration <= maxPulseDuration and e.deltaDuration == 0

            epochs = list(filter(lambda e: e.type in (ABFEpochType.Step, ABFEpochType.Pulse) and isTTLlike(e), dac.epochs))

            if len(epochs):
                dacEvents = list()
                # epochs = sorted(epochs, key = lambda e: self.getEpochStart(e, dac, sweep,
                #                                                            holding, fromRunStart, False))
                eventdata = list() # tuples of times labels for each epoch
                for e in epochs:
                    if e.type == ABFEpochType.Step:
                        t = [self.getEpochstart(e, dac, sweep, holding, fromRunStart, False).rescale(pq.s)]
                        l = [e.name]
                        n = e.name
                    elif e.type == ABFEpochType.Pulse:
                        t = list(map(lambda x: x.rescale(pq.s), self.getEpochPulseTimes(e, dac, sweep, holding, fromRunStart, False)))
                        l = list(map(lambda k: f"{e.name}_{k}", range(len(t))))
                        n = e.name
                    else:
                        continue

                    eventdata.append((t, l, n))

                if perEpoch:
                    if asNeoEvent:
                        events = list(map(lambda d: cls(times=d[0], labels=d[1], units = pq.s, name=f"TTL-like events in DAC {dac.name} epoch {d[2]}"),
                                         eventdata))
                    else:
                        events = list(map(lambda d: cls(times=d[0], labels=d[1], units = pq.s, name=f"TTL-like events in DAC {dac.name} epoch {d[2]}",
                                                        event_type = eventType),
                                        eventdata))
                    dacEvents = events

                else:
                    times, labels, _ = zip(*eventdata)
                    event_times = list(itertools.chain(times))
                    event_labels = list(itertools.chain(labels))
                    event_name = f"TTL-like events in DAC {dac.name}"

                    if asNeoEvent:
                        dacEvents = cls(times = event_times, labels = event_labels, units = pq.s, name = event_name)
                    else:
                        dacEvents = cls(times = event_times, labels = event_labels, units = pq.s, name = event_name,
                                        event_type = eventType)

                ret[dac.name] = dacEvents


        return ret

    def getTTLEmittingEpochsForDAC(self, dac: typing.Union[
                                                    ABFOutputConfiguration, int, str
                                                    ],
                                    digChannel: int, /,
                                    sweep: typing.Optional[int] = None) -> list[int]:
        if isinstance(dac, (int, str)):
            dac = self.getDAC(dac)

        digTriggerEpochs = list()
        wantsAltDIGOutput = sweep % 2 > 0

        protocolSEDs = list(filter(lambda s: s["sweep"] == sweep, self.getActiveDigitalChannels(sweep)))

        if len(protocolSEDs):
            sed = protocolSEDs[0]
            if self.alternateDigitalOutputsEnabled:
                # we want the pattern ACTUALLY being output, NOT the one defined in the DAC tab
                dp_variant = "alternate" if wantsAltDIGOutput else "main"
            else:
                dp_variant = "main"

            for epoch, dp in sed["epochs"].items():
                digDACs = self.getDACsForEpoch(epoch)
                if dac.physicalIndex in digDACs and digChannel in dp[dp_variant]:
                    digTriggerEpochs.append(epoch)

        return digTriggerEpochs # sequence of epoch numbers


    def getDigitalTriggers(self, sweep:int = 0,
                    dac: typing.Optional[typing.Union[ABFOutputConfiguration, int, str]]=None,
                    digChannel: typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
                    byDIGIndex:bool=False,
                    relativeToRunStart:typing.Optional[bool]=True,
                    useHoldingTime:bool=False,
                    # enableEmptyEvent:bool = False,
                    **kwargs
                    ) -> typing.Sequence[TriggerEvent] | TriggerEvent | None:
        r"""Trigger events emitted by the epochs in this DAC.
        The method considers that there is one TriggerEvent for each DIG
        channel, that emits a TTL while this DAC is "live"¹.

        By design, distinct DIG channels control distinct devices.

        Because each DIG channel normally controls exactly ONE device, and this
        device is the same in all epochs that emit TTL signals on this DIG channel,
        the time stamps of the TTLs sent via this DIG in all Epochs where this
        is enabled will be "merged" into the same trigger event.

        In short: one DIG channel => one TriggerEvent in the sweep(s) where it
        was configured to defined to send TTLs, in Clampex.

        NOTE: This implies the acquisition was made in "episodic mode"; in such
        case, a DIG channel that has a value of 1 or '*' in Clampex protocol
        editor (Waveforms tab) will ALWAYS emit the SAME trigger event in every
        sweep.

        In the case of alternative digital outputs, TWO distinct DIG channels
        will emit distinct trigger events on alternative sweeps¹; these events are
        CONCEPTUALLY distinct even if they have identical time stamps, etc (for
        example, they can be both presynaptic events, but ocurring on distinct
        synaptic pathways).

        ¹ Clampex uses this only for the first two DAC channels where DIG channels
        are activated.

        Parameters:
        -----------
        sweep: sweep index, in the half-open interval [0, nSweeps)

        dac: DAC channel, DAC physical index or DAC name; optional, default is
            None.

            Whe dac is None, the method returns the triggers ACTUALLY generated
            during the specified sweep.

            When DAC is specified, this method returns the trigger AS DEFINED
            in the Clampex waveform dialog's Channel tab corresponding to the
            specified DAC. NOTE that these may not be output during a given sweep
            (depending on the value of alternateDACOutputStateEnabled property and
            how the DIG channels are activated during that sweep)

            See also self.getDigitalWaveform and self.getCommandWaveform

        digChannel: index of the DIG channel to be inspected for trigger events,
            or None (default) in which case the method returns a TriggerEvent
            for each DIG channel used to send TTLs

        byDIGIndex: flag indicating whether the TriggerEvent objects should be
            packed in a mapping according to the index of the DIG channel that
            emits them. Default is False

        relativeToRunStart: ternary flag indicating how the time stamps in the
            TriggerEvent objects should be readjusted with respectu to the start
            of the Run:

            • True (the default) => the time stamps will be adjusted to include
            the inter-sweep interval.

            • False => the time stamps are adjusted to reflect the cummulative
            duration of the previous sweeps, excluding the inter-sweep interval.

            • None => then the time stamps are relative to the sweep start (i.e.
            no adjustment is made)

            This is useful for the analysis of repetitive peri-trigger features
            in a multi-sweep recording, where each sweep record starts at increasing
            times (including the inter-sweep interval).

        useHoldingTime: flag to indicate whether the TriggerEvent time stamps are
            to be corrected for the "idle" holding period at the sweep start²
            (hence they will appear delayed with respect to the Epochs' timings,
            but correctly synchronized with the recording events they triggered).

            Optional, default is True (i.e. shift the time stamps by the first
            holding period, in each sweep).

            WARNING: default is False for data recorded with Clampex v >= 11.1
            as the holding time is NOT output in the record (CAUTION: do check
            that the reported trigger times are aligned with the events of interest
            and pass either False or True, accordingly!)

        Var-keyword parameters:
        -----------------------
        triggerType: triggerevent.TriggerEventType, default is
            triggerevent.TriggerEventType.unspecified

        name: str, optional, default is None

        label_prefix: str, the prefix ued to label the time stamps in the
            TriggerEvent; optional, default is None

        NOTE:
        ¹ A DAC is "live" when its Epoch configurations are used to emit DIG or
            analog command waveforms. When Alternative Waveforms or Alternative
            Digital Outputs are enabled in the protocol, the physical index of
            the "live" DAC depends on which sweep index is queried.

            The word "live" is a misnomer, because the actual recording uses the
            same physical DAC in all sweeps; yet I use it to indicate the fact
            that in Clampex the actual waveform(s) emitted by the recording
            DAC on alternate sweeps can only be "configured" on distinct DAC
            indexes in the Clampex Protocol Editor GUI, resulting in sweep-specific
            command or digital waveforms...

        ² In episodic mode, Clampex uses two "idle" time periods of 1/64 of the
            total sweep samples, one at the start and one at end of each sweep.
            See Clampex manual for details.


        """
        if sweep not in range(self.nSweeps):
            raise ValueError(f"Invalid sweep index {sweep} for {self.nSweeps} sweeps")

        triggerType = kwargs.get("triggerType", TriggerEventType.unspecified)
        name = kwargs.get("name", None)
        label_prefix = kwargs.get("label_prefix", None)

        actualOutput = dac is None

        dac, _ = self.check_DAC_Epoch(dac, None)

        # set of DAC physical indexes for those DACs where DIG output is configured
        # but not necesarily enabled
        digDACs = self.getDACsWithDigitalOutput()

        if len(digDACs) == 0 or dac.physicalIndex not in digDACs:
            return list()

        hoDACActive = self.activeDACChannel not in (0,1) # high-order DAC active

        isAlternateDigital = False

        if self.alternateDigitalOutputsEnabled:
            if actualOutput:
                if hoDACActive:
                    isAlternateDigital = True
                else:
                    isAlternateDigital =  sweep % 2 > 0
            else:
                isAlternateDigital = dac.physicalIndex != self.activeDACChannel

        if actualOutput:
            if self.alternateDigitalOutputsEnabled:
                # digDACs = self.getDACsForEpoch(epoch.number)
                if len(digDACs) > 1:
                    # assert dac.physicalIndex in digDACs, f"DAC {dac.physicalIndex} not in digital-emitting DACs"
                    # thisDacNdx = digDACs.index(dac.physicalIndex)
                    if self.activeDACChannel == 0:
                        myDac = self.getDAC(1 if isAlternateDigital else 0)

                    elif self.activeDACChannel == 1:
                        myDac = self.getDAC(0 if isAlternateDigital else 1)

                    else:
                        assert hoDACActive, f"Active DAC index expected to be > 1; got {self.activeDACChannel}"

                        # activeDAC is a HO DAC
                        if sweep % 2 == 0 and 0 in digDACs: # "even" sweeps => query DAC0
                            myDac = self.getDAC(0)

                        elif sweep % 2 > 0 and 1 in digDACs: # "odd" sweeps => query DAC1
                            myDac = self.getDAC(1)

                        else:
                            myDac = dac
                else:
                    myDac = dac

            else:
                myDac = dac
        else:
            # OK here: shows the Epoch table AS DEFINED in Clampex, regardless
            # of the sweep
            myDac = dac

        # a tuple of ABFEpoch numbers where digital outputs are defined:
        digEpochs = self.epochsWithDigitalOutput

        activeDigChannels = (self.getActiveDigitalChannels(sweep, e)[0] for e in digEpochs)

        # usedDigs = tuple(itertools.chain.from_iterable(map(lambda x: tuple(itertools.chain.from_iterable(x)) if isinstance(x, ABFDigitalPattern) else x,
        #                                                    (self.getActiveDigitalChannels(sweep, e) for e in digEpochs))))
        usedDigs = tuple(itertools.chain.from_iterable(map(
                                                            lambda x: (tuple(itertools.chain.from_iterable(x)) if isinstance(x, ABFDigitalPattern)
                                                                       else tuple(
                                                                                    itertools.chain.from_iterable(map(
                                                                                                                        lambda e: e["main"] + e["alternate"],
                                                                                                                        x["epochs"].values()
                                                                                                                      )
                                                                                                                  )
                                                                                  )
                                                                        ),
                                                            activeDigChannels
                                                            )
                                                        )
                        )

        # print(f"{self.__class__.__name__}.getDigitalTriggers: usedDigs = {usedDigs}")

        if isinstance(digChannel, int):
            if digChannel not in usedDigs:
                # none of the specified digChannels is in use => return either an
                # empty trigger event or None
                # return TriggerEvent(event_type = triggerType, name=name, labels = label_prefix) if enableEmptyEvent else None
                return

            digChannel = (digChannel,)

        elif isinstance(digChannel, (list, tuple)) and all(isinstance(v, int) for v in digChannel):
            digChannel = tuple(sorted(set(digChannel)))

        elif digChannel is None:
            digChannel = tuple(sorted(set(usedDigs)))

        else:
            raise TypeError(f"Expecting digChannel an int or sequence of int; instead got {digChannel}")

        t0 = t1 = self.holdingTime.rescale(pq.s)
        shift = (0 if not isinstance(relativeToRunStart, bool)
                 else self.sweepInterval if relativeToRunStart
                 else self.sweepDuration)
        shift *= sweep
        if useHoldingTime:
            shift += self.holdingTime

        triggers = dict() # mapping DIG_index ↦ TriggerEvent

        for epoch in myDac.epochs:
            if epoch.type not in (ABFEpochType.Step, ABFEpochType.Pulse):
                continue
            # collect as mapping DIG index ↦ trigger event for all non-empty trigger events
            # in the epoch
            epoch_triggers = dict(filter(lambda x: len(x[1]), map(lambda x: (x, self.getEpochDigitalTriggers(epoch, sweep, myDac, digChannel=x, eventType = triggerType, name=name)), digChannel)))

            if isinstance(label_prefix, str) and len(label_prefix.strip()):
                for triggerEvent in epoch_triggers.values():
                    triggerEvent.setLabels(list(map(lambda k: f"{label_prefix}{k}", range(triggerEvent.size))))

            # if DIG index in triggers, then "concatenate"; else, just enter in triggers

            for digIndex, epoch_trigger in epoch_triggers.items():
                # adjust times for sweep start
                if isinstance(relativeToRunStart, bool):
                    epoch_trigger.relative=False
                    epoch_trigger.shift(shift)

                if digIndex not in triggers:
                    triggers[digIndex] = epoch_trigger
                else:
                    if triggers[digIndex].type != epoch_trigger.type:
                        scipywarn(f"In ABFEpoch {epoch.number} ('{epoch.letter}'), for DIG {digIndex}: concatenating TriggerEvents of distinct types: {triggers[digIndex].type} and {epoch_trigger.type}; new TriggerEvent will have {triggers[digIndex].type}")
                    time_units = triggers[digIndex].times.units
                    new_times  = np.hstack((triggers[digIndex].times, epoch_trigger.times)) * time_units
                    new_labels = np.hstack((triggers[digIndex].labels, epoch_trigger.labels))
                    triggers[digIndex] = TriggerEvent(new_times, units = time_units, labels=new_labels, name = triggers[digIndex].name)

        if byDIGIndex:
            return triggers
        else:
            triggers = tuple(triggers.values())
            return triggers[0] if len(triggers) == 1 else triggers if len(triggers) > 1 else None

    def getNeoEpoch(self, epoch:typing.Union[ABFEpoch, str, int],
                            dac:typing.Union[ABFOutputConfiguration, int, str],
                            sweep:int = 0,
                            holding:bool=True,
                            fromRunStart:bool=False,
                            name: typing.Optional[str] = None) -> neo.Epoch:
        r"""Construct a neo.Epoch object from a *single* ABFEpoch.

.. |nbsp| unicode:: 0xA0
   :trim:

The ``dac`` and ``sweep`` parameters are necessary to determine the correct |nbsp|
timings, within the trial, for the epoch taking into account preceding epochs, |nbsp|
the possibility that epochs may have changed duration (`deltaDuration`) and that |nbsp|
alternative command waveforms may have been enabled in the protocol.

Returns:
--------
A neo.Epoch object with a *single* sub-interval, and with:
    * the ``times`` attribute containing a single value (epochs *current* start time)
    * the ``durations`` attribute containing a single value (the epoch's *current* duration)
    * the ``labels`` attribute contains a single value (string) with the ABFEpoch's label.

In addition, the returned neo.Epoch object is annotated with the following data:

    :axis: name of the signal to which this epoch applies. Normally, a neo.Epoch
        is NOT associated with a particular signal (being a common feature of a |nbsp|
        neo.Segment, i.e. a sweep). However, this is a useful exception which enables |nbsp|
        the visualization of the corresponding ABFEpoch with the command waveform |nbsp|
        emitted by the DAC channel where the ABFEpoch was defined (see the |nbsp|
        ``self.waveformPreview`` method)

    :sweep: the sweep number where the *actual* epoch values are calculated.

    :epochType: type of the ABFEpoch

    :digital: the ABFDigitalPattern associated with the ABFEpoch

    :epochLetter: the letter of the ABFEpoch, in the epochs table

    :epochNumber: the number (index) of the ABFEoch in the epochs table

    :epochDACs: the index(es) of the DAC channel(s) where this ABFEpoch applies.
    :epochCurrentLevel: the current level of the command signal set in the ABFEpoch during this sweep
        (calculated based on the ABFEpoch's "firstLevel" and "deltaLevel" values)


and with the following ABFEpoch parameter values, except for its current duration:, which is |nbsp|
represented by the neo.Epoch ``duration`` attribute and is calculated according |nbsp|
the ABFEpoch's ``firstDuration``, ``deltaDuration``, and sweep number


    :epochFirstLevel:
    :epochDeltaLevel:
    :epochFirstDuration:
    :epochDeltaDuration:
    :epochPulseCount:
    :epochPulsePeriod:
    :epochPulseTimes:
    :epochPulseWidth:


.. note::
        These values depend on the position of the ABFEpoch in the epochs table, number of sweeps, and the duration of any preceding ABFEpoch in the sweep.

See also ``dacEpochsToNeoEpoch`` and ``getEpochsTable`` with ``asNeoEpoch = True``
"""
        dac, epoch = self.check_DAC_Epoch(dac, epoch)

        t0, t1 = (self.getEpochStart(epoch, dac, sweep, holding, fromRunStart, False),
                  self.getEpochDuration(epoch, dac, sweep, False))

        if not isinstance(name, str) or len(name.strip()) == 0:
            name = f"{dac.name}_epoch_{epoch.letter}"

        return neo.Epoch(times = [t0], durations = [t1],
                         labels = [epoch.letter], name = name,
                         axis = dac.name, sweep = sweep,
                         epochType = epoch.type, units = t0.units,
                         epochLetter = epoch.letter,
                         epochNumber = epoch.number,
                         epochDACs = self.getDACsForEpoch(epoch),
                         epochCurrentLevel = self.getEpochLevel(epoch, dac, sweep),
                         epochFirstLevel = epoch.firstLevel,
                         epochDeltaLevel = epoch.deltaLevel,
                         epochFirstDuration = epoch.firstDuration,
                         epochDeltaDuration = epoch.deltaDuration,
                         epochPulseCount = self.getEpochPulseCount(epoch, dac, sweep),
                         epochPulsePeriod = self.getEpochPulsePeriod(epoch, dac, samples=False),#, sweep),
                         epochPulseTimes = self.getEpochPulseTimes(epoch, dac, sweep),
                         epochPulseWidth = self.getEpochPulseWidth(epoch, dac, samples=False),#, sweep),
                         digital = self.getEpochDigitalPattern(epoch.epochNumber,
                                                               self.getIsAlternateDigital(sweep, dac)))

    def getIsAlternateDigital(self, sweep:int = 0, /,
                       dac:typing.Optional[typing.Union[ABFOutputConfiguration, int, str]]=None) -> bool:
        r"""Tests if the specified DAC is used for alternate DIG output on a given sweep"""
        actualOutput = dac is None
        dac, _= self.check_DAC_Epoch(dac, None)
        hoDACActive = self.activeDACChannel not in (0,1)
        isAlternateDigital = False
        if self.alternateDigitalOutputsEnabled:
            # NOTE: 2024-10-27 15:53:06
            # use the active DAC to get the epoch parameters for the main DIG
            # and the next DAC to get epoch params for the alt DIG

            # if dac.physicalIndex == self.activeDACChannel:
            if actualOutput:
                if hoDACActive:
                    # when active DAC is a HO DAC the "main" pattern (def'ed on
                    # the HO DAC) is ignored; instead, the "alt" pattern is used
                    # but with timings of DAC0 for even sweeps and those of DAC1
                    # on odd sweeps.
                    # If neither DAC0 nor DAC1 defines digital bit patterns, then
                    # no DIG pattern is emitted.
                    isAlternateDigital =  True # force the use of the "alt" pattern
                                               # sort out timings below
                else:
                    # odd sweep -> must query alternate DIG pattern, NOT for the
                    # active DAC, but for the DAC where the alternative pattern is
                    # defined; this is because that DAC might have defined different
                    # values for the relevant epoch parameters:
                    # first duration, delta duration, pulse width & frequency
                    #
                    # If the "active" DAC index is 0 then the "alternate" DAC
                    # index is that of the next higher index DAC where
                    # this epoch is defined, else, it is that of the higher
                    # previous DAC index where the epoch is defined.
                    #
                    # If there is no other DAC where this epoch is defined, this
                    # means there is no alternate DIG pattern emitted.
                    isAlternateDigital =  sweep % 2 > 0
            else:
                isAlternateDigital = dac.physicalIndex != self.activeDACChannel

        return isAlternateDigital

    def getEpochForDAC(self, epochIndex:typing.Union[str, int], /,
                       dac:typing.Optional[typing.Union[ABFOutputConfiguration, int, str]]=None,
                       sweep:int = 0,
                       holding:bool=True,
                       fromRunStart:bool=False,
                       asNeoEpoch:bool=False,
                       ) -> typing.Optional[ABFEpoch | neo.Epoch] :

        r"""Return an epoch specified by its *index* or *name*

    """

        dac = self.getDAC(dac)
        if isinstance(epochIndex, (str, int)):
            epoch = dac.getEpoch(epochIndex)

        if asNeoEpoch:
            return self.getNeoEpoch(epoch, dac, sweep, holding, fromRunStart)

    def getEpochsTable(self, sweep:int = 0, /,
                       dac:typing.Optional[typing.Union[ABFOutputConfiguration, int, str]]=None,
                       includeDigitalPattern:bool=True,
                       holding:bool=True,
                       fromRunStart:bool=False,
                       asNeoEpoch:bool=False,
                       ) -> typing.Optional[pd.DataFrame | neo.Epoch] :
        r"""Returns the Epochs Description table for a specific DAC.

.. |nbsp| unicode:: 0xA0
   :trim:

Parameters:
----------
:sweep: int, the 0-based index of the sweep. Optional, default is the |nbsp|
    active DAC output i.e., the ``activeDACChannel` attribute of the protocol. |nbsp|
    The *active* DAC is the DAC output channel used to send command signals  |nbsp|
    via the amplifier to the cell, during the trial. In experiments that do not |nbsp|
    send command signals (e.g. field potential recordings) the *active* DAC is |nbsp|
    the DAC associated with the ADC used for recording. This association is usually |nbsp|
    defined in Clampex's Telegraphed Instruments... dialog. If a telegraphed |nbsp|
    insstrument is not configured then the active DAC fallsback to DAC 0.

:dac: the DAC channel (or DAC channel name, or DAC channel physical index) |nbsp|
    for which the Epochs table is queried. Optional, default is None.

    When this is specified, the method returns the Epochs table AS DEFINED in |nbsp|
    the protocol editor dialog "Waveform" tab for the given DAC channel |nbsp|
    (thus, irrespective of the sweep index).

    When 'dac' is None, the method returns the Epochs table reflecting |nbsp|
    the epoch parameters that would be output during the specified sweep. In |nbsp|
    Clampex this is not necessarily the same as the one configured for the active |nbsp|
    DAC output.

    When alternative digital outputs are *disabled* in the protocol, passing
    ``dac = None`` will return the Epochs table confiured for the active DAC
    output (i.e. the one used to send comman waveforms to the cell).

:includeDigitalPattern:bool. Optional, default is True.|nbsp|
    When True, the Digital bit patterns for DIG channel banks 3-0 and 7-4 |nbsp|
    are output as in the Clampex's Waveform tab of the protocol editor. |nbsp|
    Otherwise, they are omitted.

:holding: add the holding time period to the epoch timings (default ``True``)

:fromRunStart: When ``True``, epoch timings are adjusted relative to the start |nbsp|
    of the trial. Default is ``False``.

:asNeoEpoch: When ``True``, generates a neo.Epoch object with "intervals" |nbsp|
    corresponding to the ABF Epochs; default is ``False``. **NOTE** If a digital |nbsp|
    output patter is defined in the protocol, this will **NOT** be included. |nbsp|
    To generate TriggerEvent objects, use the ``getDigitalTriggers`` method.

:actualOutput: When ``True``, the digital pattern, if shown, reflects the  |nbsp|
    *actual* digital output for the given sweep. The default (``False``) outputs |nbsp|
    the digital pattern *as defined* in the given DAC. **NOTE** This requires |nbsp|
    passing ``includeDigitalPattern = True`` .


Returns:
--------
A Pandas DataFrame or, a neo.Epoch object.

The DataFrame has a layout similar to the Clampex's Waveform tab, |nbsp|
augmented with the following rows:

First Duration (samples)¹
Delta Duration (samples)¹ ²
Train Period (samples)¹ ³
Pulse Width (samples)¹
Final Duration²
Final Duration (Samples)²
Pulse Count⁴
Final Pulse Count — same as Pulse Count if Delta Duration == 0, else |nbsp|
    this is the pulse count emitted during the last sweep that uses the |nbsp|
    pulse-emitting Epoch.

Currently not shown:
Sample rate (Fast vs Slow)

¹ In Clampex, these are shown as additional information below the Epochs table

² In Clampex, this is only shown when Delta Duration (ms) > 0, and there |nbsp|
    are more than one sweep using this Epoch

³ In Clampex, this is reported on the same line as Train rate, albeit |nbsp|
    inappropriately called "rate".

⁴ In Clampex, when the result of dividing the Epoch's duration by the |nbsp|
    train period is a rational, non-integer number, the pulse count reported |nbsp|
    in the Epochs table will be smaller than the number of pulses shown |nbsp|
    in the Waveform Preview. I suspect the reason behind this may be that, |nbsp|
    for waveform display, they could be using the ceiling of the result |nbsp|
    of this division, whereas in the Epochs table the result of the division |nbsp|
    might be simply casted to an int — bug or feature ?!?

    In this method I use the np.ceil(duration/train_period) cast to int, |nbsp|
    for consistency wiyth the waveform preview.

    CAUTION/TODO: 2024-11-10 10:14:34
    This needs to be confirmed with actual recordings of outputs when |nbsp|
    running a protocol that generates such conditions.

See also dacEpochsToNeoEpoch and getNeoEpoch

"""
        # NOTE: 2024-10-30 21:30:47
        # looks OK now
        #
        # NOTE: 2024-10-30 21:31:01 TODO:
        # 2) use same logic for generating epoch (and sweep) -specific digital
        # waveform (self.getEpochDigitalWaveform)
        #   in this respect, consider factoring the logic out to a common instance
        #   method

        actualOutput = dac is None
        dac, _= self.check_DAC_Epoch(dac, None) # when dac is None, dac is set to active DAC

        # a tuple of ABFEpoch numbers where digital outputs are defined:
        digEpochs = self.epochsWithDigitalOutput

        # HO DAC is a "high-order" DAC: a DAC with index > 1
        hoDACActive = self.activeDACChannel not in (0,1)

        # ### BEGIN set up row labels for output data frame
        if sweep not in range(self.nSweeps):
            raise ValueError(f"Invalid sweep index {sweep} for {self.nSweeps} sweeps")

        if actualOutput:
            outputNdx = f"(as output in sweep {sweep})"

        else:
            outputNdx = f"(as defined in DAC {dac.physicalIndex})"

        if asNeoEpoch:
            # convert *all* epochs to neo.Epoch
            labels = list(map(lambda e: e.name, dac.epochs))

            times, durations = zip(*list(map(lambda e: self.getEpochStartStop(e, dac, sweep, holding=holding,
                                                                              fromRunStart=fromRunStart),
                                             dac.epochs)))
            etypes = list(map(lambda e: e.type, dac.epochs))


            result = neo.Epoch(times=times, durations=durations, labels=labels,
                             name = f"{dac.name} Epochs in sweep {sweep}",
                             units = times[0].units,
                             epochTypes = etypes)#, digital = digPatterns)

        else:
            if includeDigitalPattern:
                rowIndex = ["Type", "First Level", "Delta Level",
                            "First Duration", "First Duration (Samples)",
                            "Delta Duration", "Delta Duration (Samples)",
                            "Actual Duration", "Actual Duration (Samples)",
                            "Final Duration", "Final Duration (Samples)",
                            "Digital Pattern (#3-0)", "Digital Pattern (#7-4)",
                            "Train Rate", "Train Period", "Train Period (Samples)",
                            "Pulse Width", "Pulse Width (Samples)",
                            "Pulse Count", "Final Pulse Count"]
            else:
                rowIndex = ["Type", "First Level", "Delta Level",
                            "First Duration", "First Duration (Samples)",
                            "Delta Duration", "Delta Duration (Samples)",
                            "Actual Duration", "Actual Duration (Samples)",
                            "Final Duration", "Final Duration (Samples)",
                            "Train Rate", "Train Period", "Train Period (Samples)",
                            "Pulse Width", "Pulse Width (Samples)",
                            "Pulse Count", "Final Pulse Count"]

            rowIndex.append(outputNdx)
            # ### END set up row labels for output data frame

            result = dict()

        for i, epoch in enumerate(dac.epochs):

            myDac = dac # allocate early — use the given dac

            # would an alt output be output for this sweep?
            # for how alt output is def'ed see comments in self.getIsAlternateDigital
            wantsAltOutput = sweep % 2 > 0

            if actualOutput:
                if self.alternateDigitalOutputsEnabled and epoch.number in digEpochs:
                    # get the dac where the alternative digital bit pattern was defined:
                    digDACs = self.getDACsForEpoch(epoch.number)

                    if len(digDACs) > 1 and dac.physicalIndex in digDACs:
                        if hoDACActive:
                            if 1 in digDACs and wantsAltOutput:
                                myDac = self.getDAC(1)
                            elif 0 in digDACs and not wantsAltOutput:
                                myDac = self.getDAC(0)

                        else:
                            if self.activeDACChannel in digDACs:
                                mainDacNdx = digDACs.index(self.activeDACChannel)
                                if mainDacNdx > 0:
                                    altDacNdx = mainDacNdx - 1
                                else:
                                    altDacNdx = mainDacNdx + 1

                                if altDacNdx < len(digDACs):
                                    altDac = self.getDAC(digDACs[altDacNdx])

                            myDac = altDac if wantsAltOutput else self.activeDAC

                        # to report correct temporal params for epoch in DAC, given sweep index
                        myEpoch = myDac.getEpoch(epoch.number)

                    else:
                        myDac = dac
                        myEpoch = epoch

                else:
                    myDac = dac
                    myEpoch = epoch
            else:
                # OK here: shows the Epoch table AS DEFINED in Clampex, regardless
                # of the sweep
                wantsAltOutput = self.getIsAlternateDigital(sweep, dac)
                myDac = dac
                myEpoch = epoch

            epochDigPattern = self.getEpochDigitalPattern(epoch.epochNumber,
                                                    main = not wantsAltOutput,
                                                    natural=False, separateBanks=True)

            duration = self.getEpochDuration(myEpoch, myDac, sweep, samples = False)
            durationSamples = scq.nSamples(duration, self.samplingRate)

            deltaDuration = self.getEpochDeltaDuration(myEpoch, myDac)
            deltaDurationSamples = scq.nSamples(deltaDuration, self.samplingRate)

            finalDuration = self.getEpochDuration(myEpoch, myDac, self.nSweeps-1, samples = False)
            finalDurationSamples = scq.nSamples(finalDuration, self.samplingRate)

            pulsePeriod = self.getEpochPulsePeriod(myEpoch, myDac)
            pulsePeriodSamples = scq.nSamples(pulsePeriod, self.samplingRate)

            pulseCount = 0 if pulsePeriod == 0. else int(np.ceil(duration/pulsePeriod))
            finalPulseCount = 0 if pulsePeriod == 0. else int(np.ceil(finalDuration/pulsePeriod))

            if includeDigitalPattern:
                if asNeoEpoch:
                    if "digital" not in result.annotations:
                        result.annotations["digital"] = list()

                    result.annotations["digital"].append({epoch.letter:
                                                              {"bank 0": epochDigPattern[0],
                                                               "bank 1": epochDigPattern[1]}
                                                         })
                else:
                    epValues = [myEpoch.typeName, myEpoch.firstLevel,
                                myEpoch.deltaLevel, myEpoch.firstDuration,
                                scq.nSamples(myEpoch.firstDuration, self.samplingRate),
                                deltaDuration, deltaDurationSamples,
                                duration, durationSamples,
                                finalDuration, finalDurationSamples,
                                "".join(map(str, epochDigPattern[0])),
                                "".join(map(str, epochDigPattern[1])),
                                myEpoch.pulseFrequency,
                                pulsePeriod, pulsePeriodSamples,
                                myEpoch.pulseWidth,
                                scq.nSamples(myEpoch.pulseWidth, self.samplingRate),
                                pulseCount,
                                finalPulseCount,
                                ""
                                ]

                    result[epoch.letter] = epValues
            else:
                epValues = [myEpoch.typeName, myEpoch.firstLevel,
                            myEpoch.deltaLevel, myEpoch.firstDuration,
                            scq.nSamples(myEpoch.firstDuration, self.samplingRate),
                            deltaDuration, deltaDurationSamples,
                            duration, durationSamples,
                            finalDuration, finalDurationSamples,
                            myEpoch.pulseFrequency,
                            pulsePeriod, pulsePeriodSamples,
                            myEpoch.pulseWidth,
                            scq.nSamples(myEpoch.pulseWidth, self.samplingRate),
                            pulseCount,
                            finalPulseCount,
                            ""
                            ]

                result[epoch.letter] = epValues

        if not asNeoEpoch:
            result = pd.DataFrame(result, index = np.array(rowIndex))

        return result

    def getDigitalWaveform(self, sweep: int = 0,
                           dac: typing.Optional[
                               typing.Union[ABFOutputConfiguration, int, str]
                               ] = None,
                           digChannel: typing.Optional[
                               typing.Union[int, typing.Sequence[int]]
                               ] = None,
                           separateWaves: bool = True,
                           normalized: bool = False,
                           asSignals: bool = True) -> typing.Optional[
                               typing.Union[
                                            typing.Sequence[
                                                np.ndarray | neo.AnalogSignal
                                                ],
                                            np.ndarray
                                            ]
                               ]:
        r"""TTL (digital) waveforms for the given sweep.

.. |nbsp| unicode:: 0xA0
   :trim:

Generates a waveform with the digital signals output during a given *sweep*.

Parameters:
-----------

:sweep: 0-based index of the trial sweep. Optional, default is 0 (1ˢᵗ sweep)

:dac:  the DAC channel (or DAC channel name, or DAC channel physical index) |nbsp|
    for which the digital output waveform table is requeste. Optional, default is ``None``.

    When 'dac' is ``None``, the method returns the waveform reflecting |nbsp|
    the digital outputs signal emitted during the specified sweep.

    In any other case, the method returns the digital outputs table AS DEFINED in |nbsp|
    the protocol editor dialog "Waveform" tab for the specified DAC channel |nbsp|
    (thus, irrespective of the sweep index).

:digChannel: index (``int``) or sequence of indexes (all ``int``) for the digital |nbsp|
    channel where the output is requested. When ``alternateDigitalOutputsEnabled`` |nbsp|
    is ``True``, this may be *different* on alternate sweeps.

    Optional; default is ``None``, in which case all digital channels emitting a |nbsp|
    TTL signal will contribute to the generated waveform.

    Moreover, when 'digChannel' is ``None`` *and* ``alternateDigitalOutputsEnabled`` |nbsp|
    is ``True``, the generated waveform will reflect the digital output what *would* |nbsp|
    emitted by the specified 'dac' during this particular sweep.

    If, in adition, 'dac' is also ``None``, then the generated waveform will reflect |nbsp|
    the TTL signals that *would* be emitted at all, during the sweep.

:separateWaves: When ``True`` and there is more than one digital channel emitting |nbsp|
    TTL signals, then a list of waveforms will be generated, one per digital channel. |nbsp|
    When ``False`` the a single waveform will be generated, incorporating all |nbsp|
    TTL signals emitted during the sweep.

    Optional; default is ``True``.

    When only *one* waveform would be generated for the specified sweep (see above) |nbsp|
    then the method returns a single AnalogSignal or numpy array *irrespective* of |nbsp|
    this parameter.

:normalized: When ``True`` the generated waveform is normalized to the "high" logic |nbsp|
    and will contains values of 0 and 1.

    Optional; default is ``False``

:asSignals: When ``True``, the generated waveforms are ``neo.AnalogSignal`` objects. |nbsp|
    When ``False``, the egenrated waveforms are numpy arrays.

    Optional; default is ``True``.

See documentation of self.getEpochsTable(…) for details regarding digital patterns |nbsp|
and alternative digital output.

"""
        if sweep not in range(self.nSweeps):
            raise ValueError(f"Invalid sweep index {sweep} for {self.nSweeps} sweeps")

        actualOutput = dac is None

        dac, _ = self.check_DAC_Epoch(dac, None)

        # set of DAC physical indexes for those DACs where DIG output is configured
        # but not necesarily enabled
        digDACs = self.getDACsWithDigitalOutput()

        waveUnits = pq.dimensionless if normalized else pq.V

        if len(digDACs) == 0 or dac.physicalIndex not in digDACs:
            wave = np.array(np.full((self.sweepSampleCount, 1), 0.)) * waveUnits
            if asSignals:
                return neo.AnalogSignal(wave, units = waveUnits, sampling_rate=self.samplingRate,
                                        name = f"Digital Waveform for DAC {dac.physicalIndex}")

            return wave

        hoDACActive = self.activeDACChannel not in (0,1)

        myDac = dac

        wantsAltDIGOutput = sweep % 2 > 0

        if actualOutput:
            if self.alternateDigitalOutputsEnabled:
                if hoDACActive:
                    if 1 in digDACs and wantsAltDIGOutput:
                        myDac = self.getDAC(1)
                    elif 0 in digDACs and not wantsAltDIGOutput:
                        myDac = self.getDAC(0)

                else:
                    if self.activeDACChannel in digDACs:
                        mainDacNdx = digDACs.index(self.activeDACChannel)
                        if mainDacNdx > 0:
                            altDacNdx = mainDacNdx - 1
                        else:
                            altDacNdx = mainDacNdx - 1

                        if altDacNdx < len(digDACs):
                            altDac = self.getDAC(digDACs[altDacNdx])

                    myDac = altDac if wantsAltDIGOutput else self.activeDAC


        # a tuple of ABFEpoch numbers where digital outputs are defined:
        digEpochs = self.epochsWithDigitalOutput

        if actualOutput and self.alternateDigitalOutputsEnabled:
            activeDigChannels = (self.getActiveDigitalChannels(sweep, e, main = not wantsAltDIGOutput)[0] for e in digEpochs)
            key = "alternate" if wantsAltDIGOutput else "main"
            usedDigs = tuple(
                            itertools.chain.from_iterable(
                                map(
                                    lambda x: (tuple(x.alternate) if isinstance(x, ABFDigitalPattern)
                                               else tuple(
                                                        itertools.chain.from_iterable(map(
                                                                                            lambda e: e[key],
                                                                                            x["epochs"].values()
                                                                                            )
                                                                                        )
                                                        )
                                                ),
                                    activeDigChannels
                                    )
                                )
                            )
        else:
            activeDigChannels = (self.getActiveDigitalChannels(sweep, e)[0] for e in digEpochs)
            usedDigs = tuple(
                            itertools.chain.from_iterable(
                                map(
                                    lambda x: (tuple(itertools.chain.from_iterable(x)) if isinstance(x, ABFDigitalPattern)
                                               else tuple(
                                                        itertools.chain.from_iterable(map(
                                                                                            lambda e: e["main"] + e["alternate"],
                                                                                            x["epochs"].values()
                                                                                            )
                                                                                        )
                                                        )
                                               ),
                                    activeDigChannels
                                    )
                                )
                            )

        # NOTE: 2023-09-20 22:22:41
        # the digital output is ALWAYS in V
        # "high logic" means 5V on a background of 0 V
        # "low logic" means 0V on a background of 5V

        if isinstance(digChannel, int):
            if digChannel not in usedDigs:
                digOFF, digON = self.getDigitalPulseLogicLevels(digChannel)
                wave = np.full((self.sweepSampleCount, 1), digOFF)
                if asSignals:
                    return neo.AnalogSignal(wave,
                                            units = pq.V, t_start = 0*pq.s,
                                            sampling_rate = self.samplingRate,
                                            name = f"DIG {digChannel}", DAC = {dac.name: dac.physicalIndex})
                return wave
                # raise ValueError(f"Invalid DIG channel index {digChannel}")

            digChannel = (digChannel,)

        elif isinstance(digChannel, (list, tuple)) and all(isinstance(v, int) for v in digChannel):
            digChannel = tuple(sorted(set(digChannel)))

        elif digChannel is None:
            digChannel = tuple(sorted(set(usedDigs)))

        else:
            raise TypeError(f"expecting digChannel an int or sequence of int; instead got {digChannel}")

        if separateWaves:
            waveforms = [neo.AnalogSignal(np.full((self.sweepSampleCount, 1),
                                                np.nan),
                                        units = pq.V, t_start = 0*pq.s,
                                        sampling_rate = self.samplingRate,
                                        name = f"DIG {chnl}", DAC = {dac.name: dac.physicalIndex}) for chnl in digChannel]
        else:
            chnlname = lambda x: x if len(x) > 1 else x[0]
            waveforms = neo.AnalogSignal(np.full((self.sweepSampleCount, len(digChannel)),
                                                np.nan),
                                        units = pq.V, t_start = 0*pq.s,
                                        sampling_rate = self.samplingRate,
                                        name = f"DIG {chnlname(digChannel)}", DAC = {dac.name: dac.physicalIndex})

        t0 = t1 = self.holdingTime.rescale(pq.s)

        offLevel = None

        if separateWaves:
            lastEpochNdx = [0] * len(digChannel)
            lastLevel = [None] * len(digChannel)
        else:
            lastEpochNdx = 0
            lastLevel = None

        for epoch in myDac.epochs:
            actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
            t1 = t0 + actualDuration
            tt = np.array([t0,t1])*pq.s

            eWaves = self.getEpochDigitalWaveform(epoch, sweep, dac=myDac,
                                                  digChannel=digChannel,
                                                  separateWaves=separateWaves,
                                                  returnLevels=True,
                                                  normalized=normalized,
                                                  asSignals=False)

            t0 = t1

            if eWaves is None:
                continue

            epochWaves, epoch_digOFF, epoch_digON, epoch_trainOFF, epoch_trainON = eWaves
            offLevel = epoch_digOFF if epoch_digOFF is not None else epoch_trainOFF

            if isinstance(epochWaves, np.ndarray):
                epochWaves = (epochWaves, )

            if lastLevel is None:
                lastLevel = epoch_digOFF if epoch_digOFF is not None else epoch_trainOFF

            if separateWaves:
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

        if self.digitalUseLastEpochHolding:
            if separateWaves:
                for k in range(len(waveforms)):
                    waveforms[k][lastEpochNdx[k]:, :] = lastLevel[k]
            else:
                 waveforms[lastEpochNdx:, :] = lastLevel
        else:
            if separateWaves:
                for k in range(len(waveforms)):
                    waveforms[k][lastEpochNdx[k]:, :] = offLevel #* waveforms[k].units
            else:
                waveforms[lastEpochNdx:, :] = offLevel #* waveforms.units

        if separateWaves:
            for k in range(len(waveforms)):
                waveforms[k][np.isnan(waveforms[k])] = offLevel

            if not asSignals:
                waveforms = list(map(lambda w: w.magnitude.flatten(), waveforms))

            if len(waveforms) == 0:
                return

            if len(waveforms) == 1:
                return waveforms[0]

            return waveforms

        else:
            waveforms[np.isnan(waveforms)] = offLevel
            if not asSignals:
                return waveforms.magnitude.flatten()

            return waveforms

    def getEpochDigitalWaveform(self, epoch:typing.Union[ABFEpoch, str, int], /,
                                sweep:int = 0,
                                dac:typing.Optional[typing.Union[ABFOutputConfiguration, int, str]] = None,
                                digChannel:typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
                                lastLevelOnly:bool = False,
                                separateWaves:bool = True,
                                normalized:bool=False,
                                asSignals:bool=False,
                                returnLevels:bool = False) -> tuple[pq.Quantity]:
        r"""Waveform with the TTL signals emitted by the epoch.

.. |nbsp| unicode:: 0xA0
   :trim:


Mandatory positional parameters:
--------------------------------

epoch: the ABF epoch that is queried

Named parameters:
-----------------

:sweep: the index of the ABF sweep (digital outputs may be specific to the |nbsp|
        sweep index, when alternate digital patterns are enabled in the |nbsp|
        ABF protocol).

        Default is 0 (first sweep)

:dac: index, name, or ABFOutputConfiguration: the DAC channel where the |nbsp|
    epoch is defined. Optional, default is None.

    When None, the method returns the digital waveform that would be |nbsp|
    output during the specified sweep. Depending on the use of alternate |nbsp|
    digital outputs and on the Epoch's delta duration parameter, the |nbsp|
    output for the specified sweep may be different from what is defined |nbsp|
    in the Clampex's Epochs table.

    When not None, the method returns the digital waveform reflecting |nbsp|
    what was defined in Clampex's Epochs table, irrespective of the |nbsp|
    sweep index.

:digChannel:int, Sequence[int] default is None.

    When None, the function returns a waveform for each digital output |nbsp|
    channel that is active during this epoch (and during the specified |nbsp|
    sweep). The waveforms may be returned as individual waveforms or as |nbsp|
    column vectors of a 2D Quantity array — see 'separateWaves' parameter, |nbsp|
    below.

:lastLevelOnly: default is False; when True, just generate a constant wave |nbsp|
    with the value of the last digital logic level; that is, OFF for digital |nbsp|
    pulse or train. NOTE that the actual value of this level is either 0 V |nbsp|
    or 5 V, depending on the values of protocol.digitalHoldingValue(channel) |nbsp|
    and protocol.digitalTrainActiveLogic.

    When 'normalized' is True (see below), the wave is dimensionless |nbsp|
    (i.e. without physical units).

    See self.getDigitalLogicLevels, self.getDigitalPulseLogicLevels, |nbsp|
    and self.getDigitalTrainLogicLevels

:separateWaves: default is False.

    When False, and more than one digChannel is queried, the function |nbsp|
    returns a Quantity array with one channel-specific waveform per |nbsp|
    column.

    When True, the function returns a list of vector waveforms (one per |nbsp|
    channel).

:normalized: Flag to normalize the resulted waveform. Default is False. |nbsp|
    When True, the waveform is normalized to the value of the "high" logic |nbsp|
    (therefore containing values of 0 and 1).

    When False (the default) the "high" logic is in mV (i.e. 5000 mV).

:asSignals: Flag to return the waveform as neo.AnalogSignal. Default is False. |nbsp|
    When True, the waveforms will be returned as analog signals; when |nbsp|
    'separateWaves' is False, they will be contained as "channels" in the |nbsp|
    returned AnalogSignal object.

    When 'normalized' is True, the waveform data will be dimensionless.

:returnLevels: default False; When True, returns the waves and the |nbsp|
    digOFF, digON, trainOFF and trainON logical levels

Returns:
--------
waves, [digOFF, digON, trainOFF, trainON], where:

'waves':
    When 'digChannel' parameter is an int, 'waves' is a Python Quantity |nbsp|
    array or a neo.AnalogSignal (depending on the value of 'asSignals' |nbsp|
    parameter).

    Otherwise, 'waves' is a tuple of Python Quantity arrays or AnalogSignal |nbsp|
    objects, each with the digital waveforms for each specified DIG channel, |nbsp|
    if 'separateWaves' is True, else, a Python Quantity array (or AnalogSignal |nbsp|
    object) where each DIG channel corresponds to a column vector.

    If there is only one DIG channel emitting signals in the epoch, then |nbsp|
    'waves' is a single Python Quantity array or AnalogSignal.

digOFF, digON, trainOFF, trainON - scalar Python Quantities with the values |nbsp|
    of the logical levels for digital pulse and digital train.

    These are returned only when 'returnLevels' parameter is True.

    .. note::

        1. trainOFF and trainON are None when the epoch emits only digital pulses

        2. digOFF and digON are None when the epoch emits only digital pulse trains

        3. Within a given epoch, these levels are identical for all DIG channels.

"""
        if sweep not in range(self.nSweeps):
            raise ValueError(f"Invalid sweep index {sweep} for {self.nSweeps} sweeps")

        actualOutput = dac is None

        dac, epoch = self.check_DAC_Epoch(dac, epoch)

        hoDACActive = self.activeDACChannel not in (0,1)

        isAlternateDigital = False

        if self.alternateDigitalOutputsEnabled:
            if actualOutput:
                if hoDACActive:
                    isAlternateDigital = True
                else:
                    isAlternateDigital =  sweep % 2 > 0
            else:
                isAlternateDigital = dac.physicalIndex != self.activeDACChannel

        digOFF = digON = trainOFF = trainON = None # to return None if needed
        trainOFF, trainON = self.getDigitalTrainLogicLevels()


        if actualOutput:
            if self.alternateDigitalOutputsEnabled:
                digDACs = self.getDACsForEpoch(epoch.number)
                if len(digDACs) > 1:
                    assert dac.physicalIndex in digDACs, f"DAC {dac.physicalIndex} not in digital-emitting DACs"
                    # thisDacNdx = digDACs.index(dac.physicalIndex)
                    if self.activeDACChannel == 0:
                        myDac = self.getDAC(1 if isAlternateDigital else 0)
                    elif self.activeDACChannel == 1:
                        myDac = self.getDAC(0 if isAlternateDigital else 1)
                    else:
                        assert hoDACActive, f"Active DAC index expected to be > 1; got {self.activeDACChannel}"
                        # activeDAC is a HO DAC
                        if sweep % 2 == 0 and 0 in digDACs: # "even" sweeps => query DAC0
                            myDac = self.getDAC(0)
                        elif sweep % 2 > 0 and 1 in digDACs: # "odd" sweeps => query DAC1
                            myDac = self.getDAC(1)
                        else:
                            myDac = dac
                            # continue

                    # to report correct temporal params for epoch in DAC, given sweep index
                    myEpoch = myDac.getEpoch(epoch.number)

                else:
                    myDac = dac
                    myEpoch = epoch

            else:
                myDac = dac
                myEpoch = epoch
        else:
            # OK here: shows the Epoch table AS DEFINED in Clampex, regardless
            # of the sweep
            myDac = dac
            myEpoch = epoch

        waveUnits = pq.dimensionless if normalized else pq.V

        durationSamples = self.getEpochDuration(myEpoch, myDac, sweep, samples = True)
        # deltaDurationSamples = self.getEpochDeltaDuration(myEpoch, myDac, samples=True)
        # finalDurationSamples = self.getEpochDuration(myEpoch, myDac, self.nSweeps-1, samples = True)
        pulsePeriodSamples = self.getEpochPulsePeriod(myEpoch, myDac, True)
        pulseWidthSamples = self.getEpochPulseWidth(myEpoch, myDac, True)

        pulseCount = 0 if pulsePeriodSamples == 0. else int(np.ceil(durationSamples/pulsePeriodSamples))
        # finalPulseCount = 0 if pulsePeriodSamples == 0. else int(np.ceil(finalDurationSamples/pulsePeriodSamples))


        # NOTE: 2024-10-28 17:28:04
        # trick to avoid calling getEpochDigitalPattern twice - see docstring for
        # self.getActiveDigitalChannels() - the trick is that getEpochDigitalPattern
        # now accepts a digital but pattern tuple (with some caveats!)
        # digPattern = self.getEpochDigitalPattern(sweep, myEpoch) # either main or alternate, depending on the sweep
        digPattern = self.getEpochDigitalPattern(myEpoch, not isAlternateDigital) # either main or alternate, depending on the sweep
        activeDigChannels = self.getActiveDigitalChannels(sweep, myEpoch, main = not isAlternateDigital)
        key = "alternate" if isAlternateDigital else "main"
        # usedDigs = self.getActiveDigitalChannels(sweep, myEpoch, main = not isAlternateDigital)# digPattern)
        usedDigs = tuple(
                        itertools.chain.from_iterable(
                            map(
                                lambda x: (tuple(itertools.chain.from_iterable(x)) if isinstance(x, ABFDigitalPattern)
                                            else tuple(
                                                    itertools.chain.from_iterable(map(
                                                                                        lambda e: e[key],
                                                                                        x["epochs"].values()
                                                                                        )
                                                                                    )
                                                    )
                                            ),
                                activeDigChannels
                                )
                            )
                        )

        # print(f"{self.__class__.__name__}.getEpochDigitalWaveform: epoch = {epoch}, myDac = {myDac}, sweep = {sweep}\n->\n\tdigPattern = {digPattern}\n\tactiveDigChannels = {activeDigChannels}\n\tusedDigs = {usedDigs}")

        if isinstance(digChannel, int):
            digChannel = (digChannel,)

        elif digChannel is None:
            digChannel = usedDigs

        elif isinstance(digChannel, (tuple, int)) and all(isinstance(v, int) for v in digChannel) :
            digChannel = tuple(sorted(set(digChannel)))

        else:
            raise TypeError(f"Expecting digChannel an int or a sequence of int; instead got {digChannel}")

        if len(digChannel) == 0:
            if lastLevelOnly:
                return tuple(map(lambda k, chnl: self.getDigitalLogicLevels(chnl, None)[0] , digChannel))

            waves = [np.full([durationSamples, 1], 0) * waveUnits for k in range(len(digChannel))]

        else:
            dp = tuple(itertools.chain.from_iterable(digPattern))
            digChannelValue = tuple(map(lambda c: dp[c], digChannel))
            # digChannelValue = tuple(digPattern[chnl] for chnl in digChannel)
            # print(f"digChannelValue = {digChannelValue}")
            if lastLevelOnly:
                return tuple(map(lambda k, chnl: self.getDigitalLogicLevels(chnl, lambda k: True if digChannelValue[k] == "*" else False if digChannelValue[k]==1 else None)[0] , digChannel))

            waves = list()

            for k, chnl in enumerate(digChannel):
                digOFF, digON = self.getDigitalPulseLogicLevels(chnl)

                wave = np.full([durationSamples, 1], digOFF) * pq.V

                if digChannelValue[k] == 1: # emits pulse (a.k.a step)
                    wave[:] = digON

                    if normalized:
                        wave = wave / digON # normalize to 0⋯1 => dimensionless

                elif digChannelValue[k] == "*": # emits train
                    wave[:] = trainOFF

                    for pulse in range(pulseCount):
                        p1 = int(pulsePeriodSamples * pulse)
                        p2 = int(p1 + pulseWidthSamples)
                        wave[p1:p2] = trainON

                    if normalized:
                        wave = wave/trainON # normalize to 0⋯1 => dimensionless

                waves.append(wave)

        if not separateWaves:
            waves = [np.hstack(waves) * waveUnits]

        if asSignals:
            waves = [neo.AnalogSignal(w, units = w.units, sampling_rate = self.samplingRate, name=f"Epoch {myEpoch.number} ('{myEpoch.letter}') for DAC {myDac.physicalIndex} ('{dac.name}')") for w in waves]
            if not separateWaves:
                for k,w in waves[0]:
                    w.array_annotate(DIG=[digChannel[k]])

            else:
                waves[0].array_annotate(DIG=[chnl for chnl in digChannel])

        if len(waves) == 1:
            waves = waves[0]
        else:
            waves = tuple(waves)

        if returnLevels:
            return waves, digOFF, digON, trainOFF, trainON

        return waves

    def waveformPreview(self, continuous: typing.Optional[
                                            typing.Union[bool, Tribool]
                                            ]=None) -> neo.Block:
        r"""Generates a neo.Blocm with the protocol's analog command waveforms and digital TTLs.

.. |nbsp| unicode:: 0xA0
   :trim:

Returns a neo.Block with output waveforms per sweep, for all DAC and DIG |nbsp|
channels in the protocol.

When alternative analog or digital outputs are enabled, takes into account |nbsp|
which waveform is generated in the displayed sweep.

When the optional 'continuous' parameter is set to a bool, the neo.Block |nbsp|
has only one segment with the per-sweep waveforms continuous.

By default, 'continuous' is None.

When 'continuous' is True: the corresponding waveforms across ALL sweeps |nbsp|
are concatenated, discarding the inter-sweep interval.

When 'continuous' is False, the inter-sweep interval is taken into account.

Therefore the waveform preview shows the actual time-course of the waveforms |nbsp|
during a trial.

NOTE: Multiple sweeps are displayed only when at least one of the following |nbsp|
conditions are met:
* either Alternate Waveforms or Alternate Digital Outputs are enabled
* there is at least one epoch with delta duration or delta level != 0

Furthermore, when either Alternate Waveforms or Alternate Digital Outputs |nbsp|
are enabled, only two sweep "prototypes" are shown, unless there is at |nbsp|
least one epoch with delta duration or delta level != 0.

"""
        from core import neoutils
        ret = neo.Block(name=f"{self.name} Waveforms")
        if self.alternateWaveformsEnabled or self.alternateDigitalOutputsEnabled:
            if self.nSweeps % 2 == 1:
                if any(any(e.deltaDuration > 0 or e.deltaLevel > 0 for e in d.epochs) for d in self.DACs):
                    maxSweeps = self.nSweeps
                else:
                    maxSweeps = 2
            else:
                maxSweeps = 2

        elif any(any(e.deltaDuration > 0 or e.deltaLevel > 0 for e in d.epochs) for d in self.DACs):
            maxSweeps = self.nSweeps
        else:
            maxSweeps = 1

        if maxSweeps == 1 or not isinstance(continuous, (bool, Tribool)):
            continuous=Tribool()

        elif isinstance(continuous, bool):
            continuous = Tribool(continuous)

        if isinstance(continuous.value, bool):
            # segment = neo.Segment(name=f"Sweeps {tuple(range(maxSweeps))} of {maxSweeps} sweeps")
            pfx = "Continuous" if continuous.value else "Concatenated"
            segment = neo.Segment(name=f"{pfx} sweeps")
            analogWaveforms = list()
            digitalWaveforms = list()
            neoEpochs = dict()
            for sweep in range(maxSweeps):
                sweepAnalogs = list(map(lambda dac: self.getCommandWaveform(sweep, dac), self.DACs))
                sweepDigital = list(map(lambda d: self.getDigitalWaveform(sweep,
                                                                          digChannel=d,
                                                                          asSignals=True,
                                                                          separateWaves=False),
                                        range(self.nDIGChannels)
                                        )
                                    )
                if sweep == 0:
                    analogWaveforms.extend(sweepAnalogs)
                    digitalWaveforms.extend(sweepDigital)


                else:
                    new_t_start = self.sweepInterval * sweep
                    for k,sig in enumerate(sweepAnalogs):
                        sig.t_start = new_t_start
                        analogWaveforms[k] = neoutils.concatenate_signals(analogWaveforms[k], sig, axis=0,
                                                                          name=analogWaveforms[k].name,
                                                                          force_contiguous=continuous.value)

                    for k, sig in enumerate(sweepDigital):
                        sig.t_start = new_t_start
                        digitalWaveforms[k] = neoutils.concatenate_signals(digitalWaveforms[k],
                                                                           sig,
                                                                           axis=0,
                                                                           name=digitalWaveforms[k].name,
                                                                           force_contiguous=continuous.value)
                fromRunStart, skipInterSweepInterval = (True, True) if continuous.value else (True, False)
                sweepNeoEpochs = dict(map(
                                            lambda d: (d.name, [
                                                self.dacEpochsToNeoEpoch(dac=d,
                                                                         sweep=sweep,
                                                                         fromRunStart=fromRunStart,
                                                                         skipInterSweepInterval=skipInterSweepInterval)
                                                ]),
                                            list(filter(lambda d: len(d.epochs),
                                                        self.DACs)
                                                )
                                          )
                                     )
                # if sweep > 0 and continuous.value:
                #     elapsedTime = self.sweepDuration * sweep
                # else:
                #     elapsedTime = 0 * self.sweepDuration.units

                for d, ee in sweepNeoEpochs.items():
                    # if elapsedTime > 0:
                    #     for e in ee:
                    #         e.times = e.times + elapsedTime

                    if d in neoEpochs:
                        neoEpochs[d].extend(ee)
                    else:
                        neoEpochs[d] = ee


            for d, ee in neoEpochs.items():
                if len(ee)>1:
                    eTimes = np.hstack(list(map(lambda e: e.times, ee))) * ee[0].units
                    eDurations = np.hstack(list(map(lambda e: e.durations, ee))) * ee[0].units
                    eLabels = np.hstack(list(map(lambda e: e.labels, ee)))
                    dacEpoch = neo.Epoch(eTimes, eDurations, eLabels, axis = ee[0].annotations.get("axis", d))

                elif len(ee) == 1:
                    dacEpoch = ee[0]

                segment.epochs.append(dacEpoch)

            segment.analogsignals += analogWaveforms + digitalWaveforms


            if self.holdingTime > 0:
                segment.events.append(neo.Event([self.holdingTime,
                                                self.sweepDuration - self.holdingTime],
                                                units = self.sweepDuration.units,
                                                labels = ["Wave start","Wave end"]))

            ret.segments.append(segment)

        else:
            for sweep in range(maxSweeps):
                segment = neo.Segment(name=f"Sweep {sweep} of {maxSweeps} sweeps")
                analogWaveforms = [self.getCommandWaveform(sweep, dac) for dac in self.DACs]
                digitalWaveforms = [self.getDigitalWaveform(sweep, digChannel=d,
                                                            asSignals=True, separateWaves=False) for d in range(self.nDIGChannels)]

                segment.analogsignals += analogWaveforms + digitalWaveforms

                if self.holdingTime > 0:
                    segment.events.append(neo.Event([self.holdingTime,
                                                    self.sweepDuration - self.holdingTime],
                                                    units = self.sweepDuration.units,
                                                    labels = ["Wave start","Wave end"]))

                dacEpochs = list(map(lambda d: self.dacEpochsToNeoEpoch(dac=d, sweep=sweep),
                                     list(filter(lambda d: len(d.epochs), self.DACs))))

                segment.epochs.extend(dacEpochs)

                ret.segments.append(segment)

        return ret

    def getCommandEvents(self, sweep:int = 0,
                         dac:typing.Optional[typing.Union[ABFOutputConfiguration, int, str]]=None,
                         ignoreIsWaveformEnabled:bool=False,
                         relativeToRunStart:typing.Optional[bool]=True,
                         useHoldingTime:bool=True):
        if sweep not in range(self.nSweeps):
            raise ValueError(f"Invalid sweep index {sweep} for {self.nSweeps} sweeps")

        actualOutput = dac is None

        dac, _ = self.check_DAC_Epoch(dac, None)

        analogDACs = tuple(d for d in self.DACs if d.analogWaveformEnabled)

        if len(analogDACs) == 0:
            return DataMark() # if enableEmptyEvent else None

        # NOTE: 2024-11-12 11:42:09
        # code below applies the logic in getCommandWaveform
        #
        if actualOutput:
            if self.alternateWaveformsEnabled:
                if sweep % 2 == 0:
                    return self.getDACAnalogEvents(analogDACs[0], sweep)
                else:
                    if len(analogDACs) > 1:
                        return self.getDACAnalogEvents(analogDACs[1], sweep)
                    else:
                        return DataMark()
            else:
                return tuple(self.getDACAnalogEvents(d, sweep), analogDACs)

        else:
            if self.alternateWaveformsEnabled:
                dNdx = tuple(d.physicalIndex for d in analogDACs)
                if dac.physicalIndex not in dNdx:
                    # dac not found in analog DACs
                    return DataMark()

                # Find out where if this dac's physical index is among analogDACs.
                dacNdx = dNdx.index(dac.physicalIndex)
                if dacNdx == 0:
                    # this DAC has the lowest physical index => emit waveform
                    # if sweep is even, else emit empty waveform
                    if sweep % 2 == 0:
                        return self.getDACAnalogEvents(dac, sweep)
                    else:
                        return DataMark()

                elif dacNdx == 1:
                    # this DAC is the next highest => emit waveform if the
                    # sweep is odd else emit empty waveform
                    if sweep % 2 == 1:
                        return self.getDACAnalogEvents(dac, sweep)
                    else:
                        return DataMark()

                else:
                    # in case there are multiple analog emitting DACs, and
                    # this DAC has a higher index than the first two =>
                    # return empty wave:
                    return neo.AnalogSignal(np.full((self.sweepSampleCount, 1), dac.dacHoldingLevel),
                                            units = dac.units, t_start = 0*pq.s,
                                            sampling_rate = self.samplingRate,
                                            name = dac.name)
            else:
                # return self.getDACCommandWaveform(dac, sweep)
                if ignoreIsWaveformEnabled:
                    return self.getDACAnalogEvents(dac, sweep)
                else:
                    if dac.analogWaveformEnabled:
                        return self.getDACAnalogEvents(dac, sweep)

                    return DataMark()

    def getDACAnalogEvents(self, dac, sweep):
        pass # FIXME/TODO 2026-03-31 09:12:45 ?!?
        dac, _ = self.check_DAC_Epoch(dac, None)

        t0 = t1 = self.holdingTime.rescale(pq.s)

        if dac.analogWaveformSource == ABFDACWaveformSource.epochs:
            for epoch in dac.epochs:
                actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
                # actualLevel = epoch.firstLevel + sweep * epoch.deltaLevel
                t1 = t0 + actualDuration
                tt = np.array([t0,t1])*pq.s
                ndx = waveform.time_index(tt)

                events = self.getEpochAnalogEvent(epoch, previousLevel, sweep,
                                                   dac, lastLevelOnly=False,
                                                   returnLevels=True)
                # TODO: 2024-11-12 13:02:16
                # now, "concatenate" the events
                t0=t1

        else:
            # TODO: 2024-11-12 13:03:03
            # just use the time stamps already present in the external stimulus
            # file
            scipywarn(f"Waveform source {myDac.analogWaveformSource} are not yet supported")


#         if dac.returnToHold:
#             waveform[ndx[1]:,0] = previousLevel
#
#         return waveform

        pass # FIXME/TODO 2026-03-31 09:12:45 ?!?

    def getEpochAnalogEvent(self, epoch:typing.Union[ABFEpoch, str, int],
                            sweep:int = 0,
                            dac:typing.Optional[typing.Union[ABFOutputConfiguration,str, int]] = None,
                            collapse:bool=False):
        if sweep not in range(self.nSweeps):
            raise ValueError(f"Invalid sweep index {sweep} for {self.nSweeps} sweeps")

        actualOutput = dac is None

        dac, epoch = self.check_DAC_Epoch(dac, epoch)

        actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
        epochSamplesCount = scq.nSamples(actualDuration, self.samplingRate)
        actualLevel = epoch.firstLevel + sweep * epoch.deltaLevel

        if epoch.type == ABFEpochType.Step:
            if collapse:
                markType = MarkType.ppulse if actualLevel > epoch.firstLevel else MarkType.npulse if actualLevel < epoch.firstLevel else MarkType.step # (undetermined)
            else:
                # report as TWO events ()
                markType0 = MarkType.pedge if actualLevel > epoch.firstLevel else MarkType.nedge if actualLevel < epoch.firstLevel else MarkType.edge # (undetermined)
                markType1 = MarkType.nedge if actualLevel > epoch.firstLevel else MarkType.pedge if actualLevel < epoch.firstLevel else MarkType.edge # (undetermined)


        pass


    def getAnalogWaveform(self, sweep: int = 0,
                          dac: typing.Optional[
                              typing.Union[ABFOutputConfiguration, int, str]
                              ] = None,
                          ignoreIsWaveformEnabled: bool = False,
                          asSignals: bool = True) -> neo.AnalogSignal:
        r"""Alias to self.getCommandWaveform"""
        return self.getCommandWaveform(sweep, dac,
                                       ignoreIsWaveformEnabled=ignoreIsWaveformEnabled,
                                       asSignals = asSignals)

    def getCommandWaveform(self, sweep: int = 0,
                           dac: typing.Optional[
                                    typing.Union[ABFOutputConfiguration, int, str]
                               ] = None,
                           ignoreIsWaveformEnabled: bool = False,
                           asSignals: bool = True,
                           ) -> neo.AnalogSignal:
        r"""Generates an AnalogSignal representation of a DAC command waveform.

.. |nbsp| unicode:: 0xA0
   :trim:

DAC command waveforms (and digital outputs) are enabled only in Episodic Stimulation nmode.

Parameters:
-----------
:sweep: Index of the sweep for which the command waveform is required. |nbsp|
    Must be in the semi-open interval [0, self.nSweeps).

:dac: Valid index (int) or name (str) of the DAC output (ABFOutputConfiguration) |nbsp|
    or a ABFOutputConfiguration valid for this protocol, or None (default)

    • When 'dac' is None, the method will determine which DAC is used to |nbsp|
    generate an analog command waveform, as follows:

        ∘ when no DACs have Analog Waveform enabled, the method returns |nbsp|
            an empty waveform — this is an AnalogSignal containing the |nbsp|
            holding level of this DAC, throughout;

        ∘ when there is a single DAC having Analog Waveform enabled, this |nbsp|
            DAC will be used to compute a command waveform, and:

            ▷ If Alternate Waveforms is enabled in the protocol, then the |nbsp|
                method will return this DAC's analog command waveform for |nbsp|
                even values of 'sweep' (0,2,4,…), and an empty waveform |nbsp|
                (see above) for odd values (1,3,5,…).

            ▷  Otherwise, the method will return this DAC's analog |nbsp|
                command waveform for any sweep index.

        ∘ when there are more than one DAC with Analog Waveform enabled: |nbsp|

            ▷ If Alternative Waveforms is enabled in the protocol, only |nbsp|
                the DACs with the two lowest physical indexes in the |nbsp|
                collection of DACs with Analog Waveform enabled will be |nbsp|
                used:
                → the DAC with the lowest physical index will be used |nbsp|
                    to generate the analog command waveform for sweeps with |nbsp|
                    even index.

                → the DAC with the next higher physical index will be used |nbsp|
                    to generate the analog command waveform for sweeps with |nbsp|
                    odd index.

            ▷ Otherwise, all DACs with Analog Waveform enabled will be |nbsp|
                used to generate a collection of AnalogSignal objects |nbsp|
                for any sweep index passed to the method.

:ignoreIsWaveformEnabled: default: False
    When True, and a DAC is specified, its command waveform will be |nbsp|
    generated even if it wouold not normally be output during an actual |nbsp|
    trial (useful to inspect what command waveform the epochs in the DAC |nbsp|
    are configured to generate IF Analog Waveform ws enabled on this DAC)

    NOTE: This parameter is only used when Alternate Waveforms is *DIS*abled!

    BUG: 2024-11-10 01:12:01 FIXME
    this messes up things!

:asSignals: When ``True`` all waveforms are returned as ``neo.AnalogSignal`` obejcts |nbsp|;
    otherwise, they wil be returned as numpy arrays.

    Optional; default is ``True``.

Returns:
--------

A neo.AnalogSignal, or a tuple of neo.AnalogSignal objects, depending on
the value of 'dac', and on whether Alternative Waveforms is enabled in
the protocol.

"""
        if sweep not in range(self.nSweeps):
            raise ValueError(f"Invalid sweep index {sweep} for {self.nSweeps} sweeps")

        # NOTE: 2024-11-08 16:48:00
        # logic to follow here
        #
        # 1) when no DAC is specified
        # 1.1) get the DACs where analog waveform is enabled, given the sweep
        # 1.1) if alternate waveform is enabled:
        # 1.1.1) if there is more than one DAC with analog waveform enabled:
        # 1.1.1.1) sweep with even index (0,2,4,…) => use the the DAC with the lowest index, that also emits analog waveform
        # 1.1.1.2) sweep in odd index (1,3,5,…) => use he DAC with the next index up, that also emits analog waveform
        # 1.1.2) else use the DAC waveform only on sweeps with even index
        # 1.2) else collect waveforms from all DACs that emit analog waveform,
        #       in each sweep
        #
        # In all cases, the sweep number will help determine actual epoch durations
        # & start times, taking into account the values of delta duration parameters.

        actualOutput = dac is None

        dac, _ = self.check_DAC_Epoch(dac, None)

        analogDACs = tuple(d for d in self.DACs if d.analogWaveformEnabled)

        if len(analogDACs) == 0:
            result = neo.AnalogSignal(np.full((self.sweepSampleCount, 1), dac.dacHoldingLevel),
                                    units = dac.units, t_start = 0*pq.s,
                                    sampling_rate = self.samplingRate,
                                    name = dac.name)

            return result if asSignals else result.magnitude * dac.units

        if actualOutput:
            # NOTE: 2024-11-08 15:04:54
            # if there is only one DAC emitting analog waveform, then use that
            # DAC's waveform on even sweeps (0,2,4,…) and nothing on odd sweeps
            # (1,3,5,…)
            # if there are two DACs emitting waveforms then use the first DAC
            # for even sweeps, and next DAC up in the odd sweeps
            if self.alternateWaveformsEnabled:
                if sweep % 2 == 0: # even-indexed sweep
                    return self.getDACCommandWaveform(analogDACs[0], sweep, asSignals)
                else: # odd-indexed sweeps
                    if len(analogDACs) > 1:
                        return self.getDACCommandWaveform(analogDACs[1], sweep, asSignals)
                    else:
                        result = neo.AnalogSignal(np.full((self.sweepSampleCount, 1), dac.dacHoldingLevel),
                                                units = dac.units, t_start = 0*pq.s,
                                                sampling_rate = self.samplingRate,
                                                name = dac.name)

                        return result if asSignals else result.magnitude * dac.units

            else:
                result = tuple(map(lambda x: self.getDACCommandWaveform(x, sweep, asSignals), analogDACs))
                if len(result) == 1:
                    result = result[0]

                return result

        else:
            # NOTE: 2024-11-09 13:28:41
            # A DAC is specified. However, if the protocol uses alternate
            # waveforms, then check to see if this DAC would emit on the specified
            # sweep.
            #
            # By definition, the DAC would emit on the even sweep indices if the
            # DAC is has the lowest physical index among the analogDACs
            #
            # Otherwise, if the DAC has the second highest
            # physical index then it would emit on odd sweeps.
            #

            if self.alternateWaveformsEnabled:
                dNdx = tuple(d.physicalIndex for d in analogDACs)
                if dac.physicalIndex not in dNdx:
                    # dac not found in analog DACs
                    result = neo.AnalogSignal(np.full((self.sweepSampleCount, 1), dac.dacHoldingLevel),
                                            units = dac.units, t_start = 0*pq.s,
                                            sampling_rate = self.samplingRate,
                                            name = dac.name)

                    return result if asSignals else result.magnitude * dac.units

                # Find out where if this dac's physical index is among analogDACs.
                dacNdx = dNdx.index(dac.physicalIndex)
                if dacNdx == 0:
                    # this DAC has the lowest physical index => emit waveform
                    # if sweep is even, else emit empty waveform
                    if sweep % 2 == 0:
                        return self.getDACCommandWaveform(dac, sweep, asSignals)
                    else:
                        # emit empty waveform
                        result = neo.AnalogSignal(np.full((self.sweepSampleCount, 1), dac.dacHoldingLevel),
                                                units = dac.units, t_start = 0*pq.s,
                                                sampling_rate = self.samplingRate,
                                                name = dac.name)
                        return result if asSignals else result.manitude * dac.units
                elif dacNdx == 1:
                    # this DAC is the next highest => emit waveform if the
                    # sweep is odd else emit empty waveform
                    if sweep % 2 == 1:
                        return self.getDACCommandWaveform(dac, sweep, asSignals)
                    else:
                        result = neo.AnalogSignal(np.full((self.sweepSampleCount, 1), dac.dacHoldingLevel),
                                                units = dac.units, t_start = 0*pq.s,
                                                sampling_rate = self.samplingRate,
                                                name = dac.name)
                        return result if asSignals else result.magnitude * dac.units

                else:
                    # in case there are multiple analog emitting DACs, and
                    # this DAC has a higher index than the first two =>
                    # return empty wave:
                    result = neo.AnalogSignal(np.full((self.sweepSampleCount, 1), dac.dacHoldingLevel),
                                            units = dac.units, t_start = 0*pq.s,
                                            sampling_rate = self.samplingRate,
                                            name = dac.name)
                    return result if asSignals else result.magnitude * dac.units
            else:
                if ignoreIsWaveformEnabled:
                    return self.getDACCommandWaveform(dac, sweep, asSignals)
                else:
                    if dac.analogWaveformEnabled:
                        return self.getDACCommandWaveform(dac, sweep, asSignals)

                    result = neo.AnalogSignal(np.full((self.sweepSampleCount, 1), dac.dacHoldingLevel),
                                            units = dac.units, t_start = 0*pq.s,
                                            sampling_rate = self.samplingRate,
                                            name = dac.name)
                    return result if asSignals else result.manitude * dac.units

    def getDACCommandWaveform(self, dac, sweep,
                              asSignals: bool = True):
        r"""Returns the analog waveform emitted by the specified DAC during a sweep.
        This returns the output as defined in the Epochs table, i.e., regardless
        of whether the DAC would output a waveform or not, given the specified
        sweep index.

        The sweep index parameter 'sweep' is necessary to calculate the actual
        durations and levels of the Epochs defined for the DAC.

        """

        # NOTE: 2026-04-18 16:23:14
        # treating as analosignals for convenience; returning their magnitude
        # if requested (i.e., asSignals is False)
        from iolib import pictio as pio

        dac, _ = self.check_DAC_Epoch(dac, None)
        if sweep > 0 and dac.returnToHold:
            previousLevel = self.getPreviousSweepLastEpochLevel(dac,sweep)
        else:
            previousLevel = dac.dacHoldingLevel

        waveform = neo.AnalogSignal(np.full((self.sweepSampleCount, 1), previousLevel),
                                    units = dac.units, t_start = 0*pq.s,
                                    sampling_rate=self.samplingRate,
                                    name=dac.name)

        t0 = t1 = self.holdingTime.rescale(pq.s)

        if dac.analogWaveformSource == ABFDACWaveformSource.epochs:
            for epoch in dac.epochs:
                actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
                # actualLevel = epoch.firstLevel + sweep * epoch.deltaLevel
                t1 = t0 + actualDuration
                tt = np.array([t0,t1])*pq.s
                ndx = waveform.time_index(tt)

                wave, actualLevel = self.getEpochAnalogWaveform(epoch, previousLevel, sweep,
                                                   dac, lastLevelOnly=False,
                                                   returnLevels=True)
                waveform[ndx[0]:ndx[1],0] = wave
                previousLevel = actualLevel
                t0=t1

        else:
            stimData = None
            if len(myDac.stimulusFile.strip()):
                try:
                    stimData = pio.loadFile(myDac.stimulusFile)

                except:
                    scipywarn(f"Simulus file DAC#{myDac.physicalIndex} ({myDac.name}) is not valid for {sys.platform} platform")
                    if askForStimFile:
                        # TODO: 2024-11-12 16:25:17 FIXME
                        # bring up file open dialog
                        pass

                    return waveform if asSignals else waveform.magnitude
            else:
                scipywarn(f"DAC#{myDac.physicalIndex} ({myDac.name}) is configured to use a waveform source {myDac.analogWaveformSource} but the stimulus file is not defined")

                return waveform if asSignals else waveform.magnitude

            if isinstance(stimData, neo.Block):
                # TODO: 2024-11-12 16:26:31
                # ask for sweep and signal indexes in the stimulus file
                #
                segNdx = 0
                sigNdx = 0
                if segNdx < len(stimData.segments):
                    seg = stimData.segments[segNdx]
                    if sigNdx < len(seg.analogsignals):
                        return seg.analogsignals[sigNdx] if asSignals else seg.analogsignals[sigNdx].magnitude
            return waveform

        if dac.returnToHold:
            waveform[ndx[1]:,0] = previousLevel

        if not asSignals:
            return waveform.magnitude

        return waveform


    def getEpochAnalogWaveform(self, epoch:typing.Union[ABFEpoch, str, int],
                               previousLevel: pq.Quantity, /,
                               sweep:int = 0,
                               dac:typing.Optional[typing.Union[ABFOutputConfiguration, int, str]] = None,
                               lastLevelOnly:bool=False,
                               returnLevels:bool=False) -> pq.Quantity:
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
        if sweep not in range(self.nSweeps):
            raise ValueError(f"Invalid sweep index {sweep} for {self.nSweeps} sweeps")

        actualOutput = dac is None

        dac, epoch = self.check_DAC_Epoch(dac, epoch)

        actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
        epochSamplesCount = scq.nSamples(actualDuration, self.samplingRate)
        actualLevel = epoch.firstLevel + sweep * epoch.deltaLevel

        if epoch.type == ABFEpochType.Step:
            wave = actualLevel if lastLevelOnly else np.full([epochSamplesCount, 1], float(actualLevel)) * dac.units

        elif epoch.type == ABFEpochType.Ramp:
            wave = actualLevel if lastLevelOnly else np.linspace(previousLevel, actualLevel, epochSamplesCount)[:,np.newaxis]

        elif epoch.type == ABFEpochType.Pulse:
            pulsePeriod = self.getEpochPulsePeriod(epoch, dac, samples=True)
            pulseSamples = self.getEpochPulseWidth(epoch, dac, samples=True)
            pulseCount = self.getEpochPulseCount(epoch, dac, sweep)

            if lastLevelOnly:
                wave = actualLevel
            else:
                wave = np.full([epochSamplesCount, 1], float(previousLevel)) * dac.units

                for pulse in range(pulseCount):
                    p1 = int(pulsePeriod * pulse)
                    p2 = int(p1 + pulseSamples)
                    wave[p1:p2] = actualLevel

        elif epoch.type == ABFEpochType.Triangular:
            pulsePeriod = self.getEpochPulsePeriod(epoch, dac, samples=True)
            pulseSamples = self.getEpochPulseWidth(epoch, dac, samples=True)
            pulseCount = self.getEpochPulseCount(epoch, dac, sweep)

            if lastLevelOnly:
                wave = actualLevel
            else:
                wave = np.full([epochSamplesCount, 1], float(previousLevel)) * dac.units

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
                pulseCount = self.getEpochPulseCount(epoch, dac, sweep)
                levelDelta = float(actualLevel) - float(previousLevel)
                values = np.linspace(0, 2*pulseCount*np.pi, epochSamplesCount) + np.pi
                cosines = (np.cos(values) * levelDelta / 2 + levelDelta/2 ) * dac.units + previousLevel
                wave = cosines[:, np.newaxis]

        elif epoch.type == ABFEpochType.Biphasic:
            pulsePeriod = self.getEpochPulsePeriod(epoch, dac, samples=True)
            pulseSamples = self.getEpochPulseWidthSamples(epoch, dac, samples=True)
            pulseCount = self.getEpochPulseCount(epoch, dac, sweep)
            levelDelta = actualLevel - previousLevel

            if lastLevelOnly:
                wave = actualLevel
            else:
                wave = np.full([epochSamplesCount, 1], float(previousLevel)) * dac.units

                for pulse in range(pulseCount):
                    p1 = int(pulsePeriod * pulse)
                    p3 = int(p1 + pulseSamples)
                    p2 = int((p1+p3)/2)
                    wave[p1:p2] = previousLevel + levelDelta
                    wave[p2:p3] = previousLevel - levelDelta

        else:
            wave = np.full([epochSamplesCount, 1], float(previousLevel)) * dac.units

        if returnLevels:
            return wave, actualLevel

        return wave

    def outputConfiguration(self, index:typing.Optional[typing.Union[int, str]] = None,
                            physical:bool=False) -> ABFOutputConfiguration:
        r"""Calls self.getDAC(…)
        """
        return self.getDAC(index, physical)

    def getOutput(self, index:typing.Optional[typing.Union[int, str]] = None,
                            physical:bool=False) -> ABFOutputConfiguration:
        r"""Calls self.getDAC(…)"""
        return self.getDAC(index, physical)


class ABFInputConfiguration:
    r"""Deliberately thin class with basic info about an ADC input in Clampex.
        More information may be added for convenience later; until then, just
        explore the neo.Block annotations (assuming the Block was created from an
        Axon ABF file) or the relevanmt sections in an ABF object created using
        pyabf.

        Also note that most relevant information is already parsed by the neo.io
        classes when the AnalogSignals are constructed using the input data in
        the ABF.

    r"""
    def __init__(self, obj: typing.Optional[typing.Union[pyabf.ABF, neo.Block]]=None,
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
        from core.neoutils import getAcquisitionInfo

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
        r"""Encodes this ABFInputConfiguration as a HDF5 Group.
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

#         prattr = list(filter(lambda x: x[0]=="protocol", attrs))
#
#         protocol_attr = None
#         if len(prattr):
#             ndx = attrs.index(prattr[0])
#             protocol_attr = attrs.pop(ndx)


        objattrs = h5io.makeAttrDict(**dict(map(lambda x: (x[0], getattr(self, x[0])), attrs)))
        obj_attrs.update(objattrs)
        # if isinstance(name, str) and len(name.strip()):
        #     target_name = name

        entity = group.create_group(target_name, track_order = track_order)
        entity.attrs.update(obj_attrs)

#         if isinstance(protocol_attr, tuple) and protocol_attr[0] == "protocol":
#             # NOTE: 2024-07-18 14:57:47 Steps:
#             # 1) this DAC is in a member of the parent protocol DACs list;
#             # 2) that list is encoded as a hdf5 Group, and this must be indicated as
#             #   such, in the group's attributes;
#             # 3) furthermore, the encoded list is a member of a hdf5 Group which
#             #   encodes the ABFProtocol → an ABF protocol can only be encoded as
#             #   a hdf5 Group, because the hdf5 Goup is the only hdf5 entity that
#             #   may contain children entities,
#             #
#
#             # NOTE: 2024-07-18 15:05:34 check steps (1 & 2) from NOTE: 2024-07-18 14:57:47
#             #
#             # group_attrs = h5io.attrs2dict(group.attrs)
#             # group_obj_class = group_attrs.get("type_name", None)
#
#             # Not sure the above can be done directly:
#             # group_obj_class = group.attrs.get("type_name", None)
#             # if group_obj_class == "list":
#             group_obj_class = group.attrs.get("python.class", None)
#             if group_obj_class == "builtins.list":
#                 # NOTE: 2024-07-18 15:05:53
#                 # check step (2) from NOTE: 2024-07-18 14:57:47
#                 parent = group.parent   # by definition in HDF5, this is also a Group
#                                         # and its attributes must indicate it is an
#                                         # ABFProtocol
#
#                 # NOTE: 2024-07-18 15:16:06
#                 # check step (3) from NOTE: 2024-07-18 14:57:47
#                 parent_obj_class = parent.attrs.get("type_name", None)
#                 if parent_obj_class == "ABFProtocol":
#                     entity["protocol"] = parent # soft link here
#
#             else:
#                 # to avoid infinite recursion, we only save the protocol when this ADC
#                 # is saved as part of a protocol
#                 scipywarn(f"Saving as an independent object will break the relationship between this ADC and its parent protocol.")
#                 h5io.toHDF5(None, entity, name="protocol")

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
        # protocol = h5io.fromHDF5(entity["protocol"], cache)

        return cls(obj=None, adcChannel=logicalIndex,
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
        r"""Alias to self.logicalIndex"""
        return self.logicalIndex

    @property
    def physicalIndex(self) -> int:
        return self._physicalChannelIndex_

    @physicalIndex.setter
    def physicalIndex(self, val:int):
        self._physicalChannelIndex_ = val

    @property
    def physical(self) -> int:
        r"""Alias to self.physicalIndex"""
        return self.physicalIndex

    @property
    def name(self) -> str:
        return self._adcName_

    @name.setter
    def name(self, val:str):
        self._adcName_ = val

    @property
    def adcName(self)->str:
        r"""Alias to self.name for backward compatibility"""
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

class ABFOutputConfiguration:
    r"""Configuration of a DAC channel and digital outputs in pClamp/Clampex ABF files.

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
                 dacChannel:int = 0,
                 physical:bool=False,
                 physicalIndex:typing.Optional[int]=None,
                 name: typing.Optional[str] = None,
                 units: typing.Optional[typing.Union[str, pq.Quantity]]=pq.dimensionless,
                 dacHoldingLevel:typing.Optional[typing.Union[float,pq.Quantity]] = None,
                 interEpisodeLevel:bool = True,
                 waveFormEnabled:bool=False,
                 waveFormSource:typing.Optional[typing.Union[ABFDACWaveformSource, int]] = None,
                 epochs:typing.Optional[typing.Sequence[ABFEpoch]] = None,
                 stimulusFile:typing.Optional[typing.Union[str, pathlib.Path]] = None
                 ):
        from core.neoutils import getAcquisitionInfo

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

                        dacName = obj._stringsSection._indexedStrings[obj._dacSection.lDACChannelNameIndex[self._physicalChannelIndex_]]
                        dacUnits = obj._stringsSection._indexedStrings[obj._dacSection.lDACChannelUnitsIndex[self._physicalChannelIndex_]]
                        dacStimFile = obj._stringsSection._indexedStrings[obj._dacSection.lDACFilePathIndex[self._physicalChannelIndex_]]
                        # dacName = obj._stringsSection._indexedStrings[obj._dacSection.lDACChannelNameIndex[self._dacChannel_]]
                        # dacUnits = obj._stringsSection._indexedStrings[obj._dacSection.lDACChannelUnitsIndex[self._dacChannel_]]
                        # dacStimFile = obj._stringsSection._indexedStrings[obj._dacSection.lDACFilePathIndex[self._dacChannel_]]

                    else:
                        raise ValueError(f"Invalid physical DAC channel index specified ({dacChannel}) for physical DAC channels {obj._dacSection.nDACNum}")

                else: # specify via its logical index
                    if dacChannel in range(len(obj._dacSection.nDACNum)):
                        self._dacChannel_ = dacChannel
                        self._physicalChannelIndex_ = obj._dacSection.nDACNum[dacChannel]
                        dacName = obj._stringsSection._indexedStrings[obj._dacSection.lDACChannelNameIndex[self._physicalChannelIndex_]]
                        dacUnits = obj._stringsSection._indexedStrings[obj._dacSection.lDACChannelUnitsIndex[self._physicalChannelIndex_]]
                        dacStimFile = obj._stringsSection._indexedStrings[obj._dacSection.lDACFilePathIndex[self._physicalChannelIndex_]]

                    else:
                        raise ValueError(f"Invalid logical DAC channel index specified {dacChannel} for {len(obj._dacSection.nDACNum)} channels")
                        self._dacChannel_ = None
                        self._physicalChannelIndex_ = None
                        dacName =""
                        dacUnits = ""
                        dacStimFile = ""

                self._dacName_ = dacName
                self._dacUnits_ = scq.unitQuantityFromNameOrSymbol(dacUnits)
                self._dacStimulusFile_ = dacStimFile
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
                    dacName = info_dict["listDACInfo"][self._physicalChannelIndex_]["DACChNames"].decode()
                    dacUnits = info_dict["listDACInfo"][self._physicalChannelIndex_]["DACChUnits"].decode()
                    dacStimFile = info_dict["sections"]["StringsSection"]["IndexedStrings"][info_dict["listDACInfo"][self._physicalChannelIndex_]["lDACFilePathIndex"]]
                    # dacName = info_dict["listDACInfo"][logical]["DACChNames"].decode()
                    # dacUnits = info_dict["listDACInfo"][logical]["DACChUnits"].decode()
                else:
                    self._physicalChannelIndex_ = None
                    self._dacChannel_ = None
                    dacName = ""
                    dacUnits = ""
                    dacStimFile = ""

            else: # specify via its logical index
                if dacChannel in range(len(info_dict["listDACInfo"])):
                    self._dacChannel_ = dacChannel
                    self._physicalChannelIndex_ = info_dict["listDACInfo"][dacChannel]["nDACNum"]
                    dacName = info_dict["listDACInfo"][dacChannel]["DACChNames"].decode()
                    dacUnits = info_dict["listDACInfo"][dacChannel]["DACChUnits"].decode()
                    dacStimFile = info_dict["sections"]["StringsSection"]["IndexedStrings"][info_dict["listDACInfo"][self._physicalChannelIndex_]["lDACFilePathIndex"]]
                else:
                    self._physicalChannelIndex_ = None
                    self._dacChannel_ = None
                    dacName = ""
                    dacUnits = ""
                    dacStimFile = ""

            self._dacName_ = dacName
            self._dacUnits_ = scq.unitQuantityFromNameOrSymbol(dacUnits)
            self._dacStimulusFile_ = dacStimFile

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

            if isinstance(stimulusFile, str):
                self._dacStimulusFile_ = stimulusFile

            # print(f"\tepochs: {epochs}")
            if isinstance(epochs, (tuple, list)) and all(isinstance(e, ABFEpoch) for e in epochs):
                self._epochs_ = epochs

    def __repr__(self):
        return f"{self.__class__.__name__} ({super().__repr__()}): \'{self.name}\' (\'{scq.shortSymbol(self.units)}\') at index {self.physicalIndex} ↔ {self.logicalIndex}  (physical ↔ logical)"

    @singledispatchmethod
    def _init_epochs_(self, *args):
        raise NotImplementedError(f"{type(args[0]).__name__} are not supported")

    @_init_epochs_.register(neo.Block)
    def _(self, obj:neo.Block):
        from core.neoutils import getAcquisitionInfo

        assert sourcedFromABF(obj), "Object does not appear sourced from an ABF file"
        info_dict = getAcquisitionInfo(obj)

        digPatterns = getDIGPatterns(obj)
        if self.physicalIndex in info_dict["dictEpochInfoPerDAC"]:
            dacEpochDict = info_dict["dictEpochInfoPerDAC"][self.physicalIndex]
            epochs = list()
            samplingRate = float(info_dict["sampling_rate"]) * pq.Hz
            for epochNum, epochDict in dacEpochDict.items():
                epoch = ABFEpoch()
                epoch.number = epochNum
                epoch.type = ABFEpochType(epochDict["nEpochType"])
                epoch.firstLevel = epochDict["fEpochInitLevel"] * self.units
                epoch.deltaLevel = epochDict["fEpochLevelInc"] * self.units
                epoch.firstDuration = (epochDict["lEpochInitDuration"] / samplingRate).rescale(pq.ms)
                epoch.deltaDuration = (epochDict["lEpochDurationInc"] / samplingRate).rescale(pq.ms)
                epoch.pulsePeriod = (epochDict["lEpochPulsePeriod"] / samplingRate).rescale(pq.ms)
                epoch.pulseWidth = (epochDict["lEpochPulseWidth"] / samplingRate).rescale(pq.ms)
                epoch.dacIndex = epochDict["nDACNum"]
                # epoch.mainDigitalPattern = digPatterns[epoch.number]["main"]
                # epoch.alternateDigitalPattern = digPatterns[epoch.number]["alternate"]
                epochs.append(epoch)

            self._epochs_ = epochs

    @_init_epochs_.register(pyabf.ABF)
    def _(self, obj:pyabf.ABF):
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
            # digPatterns = getDIGPatterns(obj)
            samplingRate = float(obj.dataRate) * pq.Hz
            # the epoch table is stored in _epochPerDacSection
            for i, epochDacNum in enumerate(obj._epochPerDacSection.nDACNum):
                # FIXME: 2023-09-14 22:49:09
                # for alternate DIG outputs you need TWO DACs even if only one
                # DAC channel is used!
                # RESOLVED?: you DO NOT need this info here

                # NOTE: 2023-09-18 14:46:37 skip epochs NOT defined for this DAC
                if epochDacNum != self.physicalIndex:
                    continue

                epoch = ABFEpoch()
                epoch.number = obj._epochPerDacSection.nEpochNum[i]
                epoch.type = ABFEpochType(obj._epochPerDacSection.nEpochType[i])
                epoch.firstLevel = obj._epochPerDacSection.fEpochInitLevel[i] * self.units
                epoch.deltaLevel = obj._epochPerDacSection.fEpochLevelInc[i] * self.units
                epoch.firstDuration = (obj._epochPerDacSection.lEpochInitDuration[i] / samplingRate).rescale(pq.ms)
                epoch.deltaDuration = (obj._epochPerDacSection.lEpochDurationInc[i] / samplingRate).rescale(pq.ms)
                epoch.pulsePeriod = (obj._epochPerDacSection.lEpochPulsePeriod[i] / samplingRate).rescale(pq.ms)
                epoch.pulseWidth = (obj._epochPerDacSection.lEpochPulseWidth[i] / samplingRate).rescale(pq.ms)
                epoch.dacIndex = epochDacNum
                # epoch.mainDigitalPattern = digPatterns[epoch.number]["main"]
                # epoch.alternateDigitalPattern = digPatterns[epoch.number]["alternate"]

                epochs.append(epoch)

            self._epochs_ = epochs

        else:
            raise NotImplementedError(f"ABf version {abfVer} is not supported")

    def __eq__(self, other):
        r"""Tests for equality of scalar properties and epochs tables.
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
        r"""Encodes this ABFOutputConfiguration as a HDF5 Group"""

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

        attrs = list(filter(lambda x: x[0] not in ("epochs", "emulatesTTL"), inspect.getmembers_static(self, lambda x: isinstance(x, property))))

        objattrs = h5io.makeAttrDict(**dict(map(lambda x: (x[0], getattr(self, x[0])), attrs)))
        obj_attrs.update(objattrs)

        entity = group.create_group(target_name, track_order = track_order)
        entity.attrs.update(obj_attrs)

        group_obj_class = group.attrs.get("python.class", None)

        epochs_group = h5io.toHDF5(self.epochs, entity, name="epochs",
                                            oname="epochs",
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

        epochs = h5io.fromHDF5(entity["epochs"], cache)

        return cls(obj=None, dacChannel=logicalIndex,
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
    def returnToHold(self) -> bool:
        r"""True if the command waveform return to last epoch's level.
        This is specific to the DAC output.
        """
        return self._interEpisodeLevel_

    @returnToHold.setter
    def returnToHold(self, val:bool):
        self._interEpisodeLevel_ = val == True

    @property
    def epochs(self) -> list:
        r"""List of ABFEpoch objects defined for this DAC channel"""
        return self._epochs_

    @epochs.setter
    def epochs(self, val:typing.Sequence[ABFEpoch]):
        if isinstance(val, (tuple, list)) and all(isinstance(v, ABFEpoch) for v in val):
            self._epochs_[:] = val[:]

    # def getEpochsWithDigitalOutput(self) -> typing.List[ABFEpoch]:
    #     r"""List of ABF Epochs emitting digital signals (TTLs)"""
    #     return [e for e in self.epochs if len(e.getUsedDigitalOutputChannels())]

    def getEpochsWithTTLWaveforms(self, sweep:int = 0,
                                  indexes: bool=False,
                                  train: typing.Optional[bool] = None) -> typing.List[ABFEpoch]: # FIXME 2026-04-17 21:59:44 TODO Finalize this
        r"""Returns the epochs (or their indices) where the DAC emits TTL-emulating waveforms.
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
        # isAlternateWaveform = self.protocol.alternateDACOutputStateEnabled and sweep % 2 > 0
        # ret = list()

        return [e for e in self.epochs if e.emulatesTTL]

#     def getDigitalTriggerEvent(self, sweep:int = 0, digChannel:typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
#                          eventType:TriggerEventType = TriggerEventType.presynaptic,
#                          label:typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
#                          name:typing.Optional[str] = None,
#                          enableEmptyEvent:bool=True) -> TriggerEvent|None:
#         r"""Generates TriggerEvent objects from all epochs in the protocol.
#         These may be empty if the protocol epochs do not define digital patterns.
#         (NOTE: 'enableEmptyEvent' parameter is not yet used)
#
#         See also: self.getEpochDigitalTriggerEvent
#         """
#         usedDigs = list(itertools.chain.from_iterable([epoch.getUsedDigitalOutputChannels() for epoch in self.epochs]))
#
#         if isinstance(digChannel, int):
#             if digChannel not in usedDigs:
#                 raise ValueError(f"Invalid DIG channel index {digChannel}")
#
#             digChannel = (digChannel,)
#
#         elif isinstance(digChannel, (list, tuple)) and all(isinstance(v, int) for v in digChannel):
#             if all(v not in usedDigs for v in digChannel):
#                 raise ValueError(f"Invalid DIG channel indexes {digChannel}")
#
#             digChannel = tuple(sorted(set(digChannel)))
#
#         elif digChannel is None:
#             digChannel = tuple(sorted(set(usedDigs)))
#
#         else:
#             raise TypeError(f"expecting digChannel an int or sequence of int; instead got {digChannel}")
#
#         channel_times = [list()] * len(digChannel)
#
#         # print(f"{self.__class__.__name__}.getDigitalTriggerEvent(sweep={sweep}) -> digChannel: {digChannel}")
#         for epoch in self.epochs:
#             if epoch.type not in (ABFEpochType.Step, ABFEpochType.Pulse):
#                 continue
#             digPattern = tuple(itertools.chain.from_iterable(map(lambda x: reversed(x), self.getEpochDigitalPattern(epoch, sweep))))
#             digChannelValue = tuple(digPattern[chnl] for chnl in digChannel)
#             # print(f"{self.__class__.__name__}.getDigitalTriggerEvent(sweep={sweep}) -> epoch: {epoch.epochNumber}, digPattern: {digPattern}, digChannelValue: {digChannelValue}")
#
#             # digChannelValue = [tuple(reversed(self.getEpochDigitalPattern(epoch, sweep)[chnl // 4]))[chnl] for chnl in digChannel]
#             # print(f"digChannelValue = {digChannelValue}" )
#             for k, chnl in enumerate(digChannel):
#                 # print(f"k: {k} -> chnl: {chnl}")
#                 # if chnl >= len(digChannelValue):
#                 #     continue
#                 # if digChannelValue[chnl] == "*":
#                 if digChannelValue[k] == "*":
#                     channel_times[k].extend([x.rescale(pq.s) for x in self.getEpochActualPulseTimes(epoch, sweep)])
#
#                 elif digChannelValue[k] == 1:
#                     channel_times[k].extend([self.getEpochRecordingStartTimeActual(epoch, sweep).rescale(pq.s)])
#
#         # print(f"{self.__class__.__name__}.getDigitalTriggerEvent(sweep={sweep}) -> channel_times: {channel_times}")
#         trigs = [TriggerEvent(times=channel_times[k], units = pq.s, event_type = eventType,
#                             name=name, labels = label) for k in range(len(channel_times))]
#
#         # NOTE: 2023-10-31 15:00:10
#         # remove duplicates
#         # CAUTION: TriggerEvent objects are not hashable hence cannot use
#         # set logic to achieve this
#         uniqueTrigs = list()
#
#         for k,t in enumerate(trigs):
#             if k == 0:
#                 uniqueTrigs.append(t)
#             else:
#                 if t not in uniqueTrigs:
#                     uniqueTrigs.append(t)
#
#         if len(uniqueTrigs) == 1:
#             return uniqueTrigs[0]
#
#         else:
#             return uniqueTrigs
#
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
#                     times.extend([self.getEpochRecordingStartTimeActual(epoch, sweep).rescale(pq.s)])
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
#                         channel_times[k].extend([self.getEpochRecordingStartTimeActual(epoch, sweep).rescale(pq.s)])
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


#     def getEpochDigitalTriggerEvent(self, epoch:typing.Union[ABFEpoch, str, int], sweep:int = 0,
#                              digChannel:typing.Union[int, typing.Sequence[int]] = 0,
#                              eventType:TriggerEventType = TriggerEventType.presynaptic,
#                              label:typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
#                              name:typing.Optional[str] = None,
#                              enableEmptyEvent:bool=True) -> typing.Union[TriggerEvent, typing.List[TriggerEvent]]:
#         r"""
#         TODO: Move this code to ABFProtocol, thus breaking the need to store
#         a reference to the protocol in this ABFOutputConfiguration instance.
#
#         Trigger events from an individual Step or Pulse-type ABF Epoch.
#
#         Parameters:
#         ------------
#
#         epoch: ABFEpoch, int index of ABFEpoch or letter of ABFEpoch
#
#         sweep: index of sweep (0-based)
#
#         digChannel: int or sequence of int; index or indices of digital output
#             channels where a TTL output is expected.
#
#             Specifying a tuple of int here (e.g., (0,1)) is convenient for the
#             situation where alternate digital outputs are used to generate the
#             same type of TriggerEvent (such as presynaptic). Such alternate
#             digital outputs will be emitted on distinct digital output channels,
#             even though they both represent the same type of event (in this case,
#             presynaptic pulses). This scenario can be used for Hebbian synaptic
#             plasticity experiments where synaptic responses are recorded
#             alternatively from two distinct presynaptic pathways converging on
#             the same cell.
#
#         sweep: int, index of the sweep in the protocol.
#             Normally, an ABF Epoch (and any digital output patterns defined
#             within) is repeated in each sweep - hence the sweep index is
#             irrelevant.
#
#             When alternate digital outputs are enabled, the sweep index BECOMES
#             RELEVANT, as the main digital pattern is emitted during sweeps with
#             even indices (0, 2, 4, …) whereas the alternate digital pattern is
#             emitted during sweeps with odd indices (1, 3, 5, …).
#
#             Such scenario is also likely to involve distinct digital output
#             channels in the main and the alternate digital patterns. In this
#             case it is recommended to specify BOTH digital output channels used
#             in the protocol (see above).
#
#         eventType: optional; default is TriggerEventType.presynaptic
#             Necessary in building a TriggerProtocol for the experiment.
#
#         label: The label(s) for each individual time stamp in the resulting
#             TriggerEvent object
#
#         name: The name of the resulting TriggerEvent object.
#
#         enableEmptyEvent: when True (default) the function will return an empty
#             TriggerEvent (i.e. without any time stamps) in any of the following
#             cases:
#
#             • the ABF Epoch is neither a Step or Pulse Type
#
#             • Neither of the digital channels given in digChannel are active in
#                 the epoch during the specified sweep
#
#         Returns:
#         ========
#
#         A TriggerEvent object. This may be empty, or None - see 'enableEmptyEvent'
#
#         If the epoch has digital outputs, the time stamps for the trigger
#         events will be set by the timings of the digital TTL signals during
#
#         NOTE 1: Digital signals (triggers) are emitted during epochs defined on
#         the "active" DAC
#
#         NOTE 2: An ABF Epoch supports sending digital signals simultaneously via
#         more than one digital output channel; however, Clampex does not support
#         defining different timings for distinct digital output channels, EXCEPT
#         for for the case where digital train and digital pulse are emitted by
#         distinct channels.
#
#         In such case, the digital train emitted on one channel is interpreted
#         as a sequence of trigger events, whereas the digital pulse emitted on
#         a distinct digital channel can be intepreted here as a single trigger
#         event, with the onset being equal to the timing of the first pulse in
#         the digital train (both being defined by the epoch's onset time in the
#         sweep0).
#
#         Cases like this one are ambiguous and are best avoided, if possible.
#
#         However, because distinct digital output channels can drive different
#         devices, it is necessary to specify their "semantic" within the experiment
#         (i.e. the trigger event type for a specific digital output channel).
#
#         In synaptic plasticity experiments it is usual to use two digital output
#         channels to send digital trains ALTERNATIVELY to two pathways. Since
#         both outputs are effectively presynaptic stimuli, one can specify
#         the output indices by passing a tuple of int to the digChannel parameter.
#
#         """
#         if isinstance(epoch, (str, int)):
#             e = self.getEpoch(epoch)
#
#             if e is None:
#                 raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
#
#             epoch = e
#
#         if epoch.type not in (ABFEpochType.Step, ABFEpochType.Pulse):
#             return TriggerEvent(event_type = eventType, name=name, labels = label) if enableEmptyEvent else None
#
#         usedDigs = epoch.getUsedDigitalOutputChannels()
#
#         if isinstance(digChannel, int) and digChannel not in usedDigs:
#             return TriggerEvent(event_type = eventType, name=name, labels = label) if enableEmptyEvent else None
#
#         elif isinstance(digChannel, (list, tuple)) and all(isinstance(v, int) for v in digChannel):
#             if any(v not in usedDigs for v in digChannel):
#                 return TriggerEvent(event_type = eventType, name=name, labels = label) if enableEmptyEvent else None
#
#         elif digChannel is None:
#             digChannel = usedDigs
#
#         if isinstance(digChannel, int):
#             times = list()
#
#             digPattern = self.getEpochDigitalPattern(epoch, sweep)[digChannel // 4]
#
#             digChannelValue = tuple(reversed(digPattern))[digChannel]
#
#             if digChannelValue == "*": # ⟹ pulse train
#                 times = [x.rescale(pq.s) for x in self.getEpochActualPulseTimes(epoch, sweep)]
#
#             elif digChannelValue == 1: # ⟹ single TTL pulse ⇒ take the onset time as
#                                     # a trigger event; in theory, a device may
#                                     # actually require a "ON" state during which
#                                     # it performs some ciclic function etc;
#                                     # regardless of this we may conosider the onset
#                                     # of the "ON" state as a trigger for such device
#                 times = [self.getEpochRecordingStartTimeActual(epoch, sweep).rescale(pq.s)]
#
#             trig = TriggerEvent(times=times, units = pq.s, event_type = eventType,
#                                 name=name, labels = label) if enableEmptyEvent else None
#
#             if isinstance(trig, TriggerEvent) and trig.size > 0:
#                 # see BUG: 2023-10-03 17:57:30 in triggerevent.TriggerEvent.__new__
#                 if isinstance(label, str) and len(label.strip()):
#                     trig.labels = [f"{label}{k}" for k in range(trig.times.size)]
#
#             return trig
#
#         elif isinstance(digChannel, (list, tuple)) and all(isinstance(v, int) for v in digChannel):
#             digChannelValue = [tuple(reversed(self.getEpochDigitalPattern(epoch, sweep)[chnl // 4]))[chnl] for chnl in digChannel]
#
#             trigs = list()
#
#             for k,chnl in enumerate(digChannel):
#                 times = list()
#
#                 if digChannelValue[k] == "*":
#                     times = [x.rescale(pq.s) for x in self.getEpochActualPulseTimes(epoch, sweep)]
#
#                 elif digChannelValue[k] == 1:
#                     times = [self.getEpochRecordingStartTimeActual(epoch, sweep).rescale(pq.s)]
#
#                 trig = TriggerEvent(times=times, units = pq.s, event_type = eventType,
#                                     name=name, labels = label) if enableEmptyEvent else None
#
#                 if isinstance(trig, TriggerEvent) and trig.size > 0:
#                     # see BUG: 2023-10-03 17:57:30 in triggerevent.TriggerEvent.__new__
#                     if isinstance(label, str) and len(label.strip()):
#                         trig.labels = [f"{label}{k}" for k in range(trig.times.size)]
#
#                     trigs.append(trig)
#
#             # NOTE: 2023-10-31 15:01:50 see NOTE: 2023-10-31 15:00:10
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
#
#         else:
#             raise TypeError(f"digChannel expected an int or a sequence of int; instead, got {digChannel}")

#     def getEpochsTable(self, sweep:int = 0, includeDigitalPattern:bool=True):
#         r"""Generate a Pandas DataFrame with the epochs definition for this DAC channel.
#
#         Regarding the command and digital outputs, this reflects the actual
#         DAC and DIG outputs for the specified sweep.
#
#         The epoch table in Clmapex/Clampfit and pyabf are "generic" - one has to
#         work out the actual outputs for a sweep by themselves. In contrast, the
#         logic in this function should also supply the necessary data to
#         reconstruct the DAC "command" ("analog") waveform and also the "digital"
#         waveform more easily.
#
#         """
#         if includeDigitalPattern:
#             rowIndex = ["Type", "First Level", "Delta Level",
#                         "First Duration", "First Duration (Samples)",
#                         "Delta Duration", "Delta Duration (Samples)",
#                         "Actual Duration", "Actual Duration (Samples)",
#                         "Digital Pattern #3-0", "Digital Pattern #7-4",
#                         "Train Rate", "Train Period", "Train Period (Samples)",
#                         "Pulse Width", "Pulse Width (Samples)",
#                         "Pulse Count"]
#         else:
#             rowIndex = ["Type", "First Level", "Delta Level",
#                         "First Duration", "First Duration (Samples)",
#                         "Delta Duration", "Delta Duration (Samples)",
#                         "Actual Duration", "Actual Duration (Samples)",
#                         "Train Rate", "Train Period", "Train Period (Samples)",
#                         "Pulse Width", "Pulse Width (Samples)",
#                         "Pulse Count"]
#
#
#         epochData = dict()
#
#         for i, epoch in enumerate(self.epochs):
#             if includeDigitalPattern:
#                 epochDigPattern = self.getEpochDigitalPattern(epoch, sweep)
#                 epValues = [epoch.typeName, epoch.firstLevel, epoch.deltaLevel,
#                             epoch.firstDuration, self.getEpochFirstDurationSamples(epoch),
#                             epoch.deltaDuration, self.getEpochDeltaDurationSamples(epoch),
#                             self.getEpochActualDuration(epoch, sweep),
#                             self.getEpochActualDurationSamples(epoch, sweep),
#                             "".join(map(str, epochDigPattern[0])),
#                             "".join(map(str, epochDigPattern[1])),
#                             epoch.pulseFrequency,
#                             epoch.pulsePeriod, self.getEpochPulsePeriodSamples(epoch),
#                             epoch.pulseWidth, self.getEpochPulseWidthSamples(epoch),
#                             self.getEpochPulseCount(epoch, sweep)]
#             else:
#                 epValues = [epoch.typeName, epoch.firstLevel, epoch.deltaLevel,
#                             epoch.firstDuration, self.getEpochFirstDurationSamples(epoch),
#                             epoch.deltaDuration, self.getEpochDeltaDurationSamples(epoch),
#                             self.getEpochActualDuration(epoch, sweep),
#                             self.getEpochActualDurationSamples(epoch, sweep),
#                             epoch.pulseFrequency,
#                             epoch.pulsePeriod, self.getEpochPulsePeriodSamples(epoch),
#                             epoch.pulseWidth, self.getEpochPulseWidthSamples(epoch),
#                             self.getEpochPulseCount(epoch, sweep)]
#
#
#             epochData[epoch.letter] = epValues
#
#         return pd.DataFrame(epochData, index = rowIndex)

    def getEpoch(self, e:typing.Union[str, int]):
        if isinstance(e, str):
            e = getEpochNumberFromLetter(e)

        if e < 0 or e >= len(self.epochs):
            return

        return self.epochs[e]

#     def getEpochAnalogWaveform(self, epoch:typing.Union[ABFEpoch, str, int], previousLevel:pq.Quantity,
#                       sweep:int = 0, lastLevelOnly:bool=False,
#                       returnLevels:bool=False) -> pq.Quantity:
#         r"""
#         TODO: Move this code to ABFProtocol, thus breaking the need to store
#         a reference to the protocol in this ABFOutputConfiguration instance.
#
#
#         Realizes the analog waveform associated with a single epoch.
#         An 'epoch' is defined as a specific time interval in a sweep, during
#         which the DAC outputs a command signal waveform givemn the epoch's type
#         (step, ramp, pulse, etc). This information is configured using the
#         Channel tab inside the Waveform tab of the Clampex Protocol Editor.
#         Complex DAC output commands can be generated by defining and concatenating
#         several epochs (subject to the constraints of the Clampex software version)
#         """
#         if isinstance(epoch, (int, str)):
#             e = self.getEpoch(epoch)
#             if e is None:
#                 raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
#
#             epoch = e
#
#         if self.protocol:
#             isAlternateWaveform = self.alternateDACOutputStateEnabled and sweep % 2 > 0
#
#         actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
#         epochSamplesCount = scq.nSamples(actualDuration, self.samplingRate)
#         actualLevel = epoch.firstLevel + sweep * epoch.deltaLevel
#
#         if epoch.type == ABFEpochType.Step:
#             wave = actualLevel if lastLevelOnly else np.full([epochSamplesCount, 1], float(actualLevel)) * self.units
#
#         elif epoch.type == ABFEpochType.Ramp:
#             wave = actualLevel if lastLevelOnly else np.linspace(previousLevel, actualLevel, epochSamplesCount)[:,np.newaxis]
#
#         elif epoch.type == ABFEpochType.Pulse:
#             pulsePeriod = self.getEpochPulsePeriodSamples(epoch)
#             pulseSamples = self.getEpochPulseWidthSamples(epoch)
#             pulseCount = self.getEpochPulseCount(epoch)
#
#             if lastLevelOnly:
#                 wave = actualLevel
#             else:
#                 wave = np.full([epochSamplesCount, 1], float(previousLevel)) * self.units
#
#                 for pulse in range(pulseCount):
#                     p1 = int(pulsePeriod * pulse)
#                     p2 = int(p1 + pulseSamples)
#                     wave[p1:p2] = actualLevel
#
#         elif epoch.type == ABFEpochType.Triangular:
#             pulsePeriod = self.getEpochPulsePeriodSamples(epoch)
#             pulseSamples = self.getEpochPulseWidthSamples(epoch)
#             pulseCount = self.getEpochPulseCount(epoch)
#
#             if lastLevelOnly:
#                 wave = actualLevel
#             else:
#                 wave = np.full([epochSamplesCount, 1], float(previousLevel)) * self.units
#
#                 for pulse in range(pulseCount):
#                     p1 = int(pulsePeriod * pulse)
#                     p2 = int(p1 + pulseSamples)
#                     p3 = int(p1 + pulsePeriod)
#
#                     wave[p1:p2] = np.linspace(previousLevel, actualLevel, pulseSamples)[:,np.newaxis]
#                     wave[p2:p3] = np.linspace(actualLevel, previousLevel, int(pulsePeriod - pulseSamples))[:,np.newaxis]
#
#         elif epoch.type == ABFEpochType.Cosine:
#             if lastLevelOnly:
#                 wave = actualLevel
#             else:
#                 pulseCount = self.getEpochPulseCount(epoch)
#                 levelDelta = float(actualLevel) - float(previousLevel)
#                 values = np.linspace(0, 2*pulseCount*np.pi, epochSamplesCount) + np.pi
#                 cosines = (np.cos(values) * levelDelta / 2 + levelDelta/2 ) * self.units + previousLevel
#                 wave = cosines[:, np.newaxis]
#
#         elif epoch.type == ABFEpochType.Biphasic:
#             pulsePeriod = self.getEpochPulsePeriodSamples(epoch)
#             pulseSamples = self.getEpochPulseWidthSamples(epoch)
#             pulseCount = self.getEpochPulseCount(epoch)
#             levelDelta = actualLevel - previousLevel
#
#             if lastLevelOnly:
#                 wave = actualLevel
#             else:
#                 wave = np.full([epochSamplesCount, 1], float(previousLevel)) * self.units
#
#                 for pulse in range(pulseCount):
#                     p1 = int(pulsePeriod * pulse)
#                     p3 = int(p1 + pulseSamples)
#                     p2 = int((p1+p3)/2)
#                     wave[p1:p2] = previousLevel + levelDelta
#                     wave[p2:p3] = previousLevel - levelDelta
#
#         else:
#             wave = np.full([epochSamplesCount, 1], float(previousLevel)) * self.units
#
#         if returnLevels:
#             return wave, actualLevel
#
#         return wave

#     def getEpochDigitalWaveform(self, epoch:typing.Union[ABFEpoch, str, int], /,
#                                 sweep:int = 0,
#                                 digChannel: typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
#                                 lastLevelOnly:bool=False,
#                                 separateWaves:bool=True,
#                                 digOFF:typing.Optional[pq.Quantity]=None,
#                                 digON:typing.Optional[pq.Quantity]=None,
#                                 trainOFF:typing.Optional[pq.Quantity]=None,
#                                 trainON:typing.Optional[pq.Quantity]=None,
#                                 returnLevels:bool=False) -> typing.Union[pq.Quantity, typing.Sequence[pq.Quantity]]:
#         r"""Waveform with the TTL signals emitted by the epoch.
#
#         Mandatory positional parameters:
#         --------------------------------
#
#         epoch: the ABF epoch that is queried
#
#         Named parameters:
#         -----------------
#
#         sweep: the index of the ABF sweep (digital outputs may be specific to the
#                 sweep index, when alternate digital patterns are enabled in the
#                 ABF protocol)
#
#                 Default is 0 (first sweep)
#
#         digChannel:default is None, meaning that the function returns a waveform
#             for each digital output channel that is active during this epoch
#             (and during the specified sweep)
#
#         lastLevelOnly: default is False; when True, just generate a constant wave
#             with the value of the last digital logic level; that is, OFF for digital
#             pulse or train. NOTE that the actual value of this level is either 0 V
#             or 5 V, depending on the values of protocol.digitalHoldingValue(channel)
#             and protocol.digitalTrainActiveLogic.
#
#             See self.getDigitalLogicLevels, self.getDigitalPulseLogicLevels,
#             and self.getDigitalTrainLogicLevels
#
#         separateWaves: default is False.
#             When False, and more than one digChannel is queried, the function
#             returns a Quantity array with one channel-specific waveform per
#             column.
#
#             When True, the function returns a list of vector waveforms (one per
#             channel)
#
#         digOFF, digON, trainOFF, trainON: scalar Python Quantities representing
#             the logic levels for digital pulses and trains, respectively; when
#             they are None (default) the function will query these values from the
#             ABF protocol that associates this DAC output.
#
#         returnLevels: default False; When True, returns the waves and the digOFF,
#         digON, trainOFF and trainON logical levels
#
#         Returns:
#         --------
#         waves, [digOFF, digON, trainOFF, trainON], where:
#
#         waves: list of Python quantities (Quantity arrays) whith the digital waveforms
#         for each specified DIG channel are returned.
#
#             The list contains:
#                 • a single 1D Quantity array, when digChannel parameter is an int
#                     (but see below)
#                 • as many 1D Quantity arrays as DIG channel indexes specified in
#                     digChannel parameter, and separateWaves is True
#                 • a single 2D Quantity array with shape (N,M) where:
#                     ∘ N is the number of samples recorded by the epoch
#                     ∘ M is the number of DIG channels specified in digChannel
#
#             The list is EMPTY when not all DIG channel indexes specified
#                     in the digChannel parameter are used by the epoch.
#
#         digOFF, digON, trainOFF, trainON - scalar Python Quantities with the values
#             of the logical levels for digital pulse and digital train.
#
#             NOTE:
#             1. trainOFF and trainON are None when the epoch emits only digital pulses
#             2. digOFF and digON are None when the epoch emits only digital pulse trains
#             3. Within a given epoch, these levels are identical for all DIG channels.
#
#         When not all DIG channel indexes are used by the epoch to emit digital signals
#         the function returns None
#
#         """
#         if isinstance(epoch, (int, str)):
#             e = self.getEpoch(epoch)
#             if e is None:
#                 raise ValueError(f"Invalid epoch index or name {epoch} for {len(self.epochs)} epochs defined for this DAC ({self.dacChannel})")
#
#             epoch = e
#
#         actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
#         epochSamplesCount = scq.nSamples(actualDuration, self.samplingRate)
#         pulsePeriod = self.getEpochPulsePeriodSamples(epoch)
#         pulseSamples = self.getEpochPulseWidthSamples(epoch)
#         pulseCount = self.getEpochPulseCount(epoch)
#
#         usedDigs = epoch.digitalOutputChannels
#
#         if len(usedDigs) == 0:
#             scipywarn(f"The epoch {epoch.number} ({epoch.letter}) of DAC {self.physicalIndex} ({self.name}) does NOT emit digital outputs")
#             return
#
#         if isinstance(digChannel, int):
#             if digChannel not in usedDigs:
#                 scipywarn(f"The DIG channel {digChannel} is not used in the epoch {epoch.number} ({epoch.letter}) of DAC {self.physicalIndex} ({self.name}) ")
#                 return
#                 # raise ValueError(f"Invalid DIG channel index {digChannel}")
#
#             digChannel = (digChannel,)
#
#         elif isinstance(digChannel, (list, tuple)) and all(isinstance(v, int) for v in digChannel):
#             if any(v not in usedDigs for v in digChannel):
#                 scipywarn(f"Not all specified DIG channels {digChannel} are used by the epoch {epoch.number} ({epoch.letter}) of DAC {self.physicalIndex} ({self.name}) ")
#                 return
#
#                 # raise ValueError(f"Invalid DIG channel index {digChannel}")
#
#         elif digChannel is None:
#             digChannel = tuple(usedDigs.keys())
#
#         else:
#             raise TypeError(f"Expecting digChannel an int or a sequence of int; instead got {digChannel}")
#
#         digPattern = tuple(itertools.chain.from_iterable(map(lambda x: reversed(x), self.getEpochDigitalPattern(epoch, sweep))))
#         digChannelValue = tuple(digPattern[chnl] for chnl in digChannel)
#
#         epochDIGs = epoch.digitalOutputChannels # a dict
#
#         waves = list()
#
#         for k, chnl in enumerate(digChannel):
#             wave = np.full([epochSamplesCount, 1], 0) * self.units
#
#             if digChannelValue[k] == 1: # emits pulse
#                 if any(v is None for v in (digOFF, digON)):
#                     digOFF, digON = self.getDigitalPulseLogicLevels(chnl)
#
#                 if lastLevelOnly:
#                     wave[:] = digOFF
#                 else:
#                     wave[:] = digON
#
#             elif digChannelValue[k] == "*": # emits train
#                 if any(v is None for v in (trainOFF, trainON)):
#                     trainOFF, trainON = self.getDigitalTrainLogicLevels()
#
#                 wave[:] = trainOFF
#                 if not lastLevelOnly:
#                     for pulse in range(pulseCount):
#                         p1 = int(pulsePeriod * pulse)
#                         p2 = int(p1 + pulseSamples)
#                         wave[p1:p2] = trainON
#
#             waves.append(wave)
#
#         if not separateWaves:
#             waves = [np.hstack(waves) * self.units]
#
#         if returnLevels:
#             return waves, digOFF, digON, trainOFF, trainON
#
#         return waves


#     def getPreviousSweepLastEpochLevel(self, sweep:int) -> pq.Quantity:
#         r"""Final analog value in the previous epoch"""
#         # FIXME: 2023-09-18 23:34:27
#         # this can become very expensive for many sweeps!
#         if len(self.epochs) == 0 or sweep == 0:
#             return self.dacHoldingLevel
#
#         if self.returnToHold:
#             prevLevel = self.dacHoldingLevel
#             for s in range(sweep):
#                 for e in self.epochs:
#                     prevLevel = self.getEpochAnalogWaveform(e, prevLevel, s, True)
#
#             return prevLevel
#
#         return self.dacHoldingLevel
#
#     def getPreviousSweepLastDigitalLevel(self, sweep:int, digChannel:int,
#                                          trainOFF, trainON, digOFF, digON) -> pq.Quantity:
#         if len(self.epochs) == 0 or sweep == 0:
#             return digOFF * pq.V
#
#         if self.digitalUseLastEpochHolding:
#             prevLevel = digOFF * pq.V
#             for s in range(sweep):
#                 for e in self.epochs:
#                     prevLevel = self.epochDigitalWaveform(e, trainOFF, trainON, digOFF, digON, sweep, digChannel,
#                                                           True)
#
#                 return prevLevel
#
#         return digOFF * pq.V

    # def getEpochsForDigitalChannel(self, digChannel: int, sweep: int = 0,
    #                                indexes: bool=False,
    #                                train: typing.Optional[bool] = None) -> list:
    #     r"""Returns the index of the epoch where the specified digChannel is used.
    #
    #
    #     Parameters:
    #     -----------
    #     digChannel: int in the semi-open interval [0 ⋯ 8)
    #     sweep: int — index of the sweep (necessary to determine in which digital
    #         pattern — main or alternate — the digChannel is sought
    #     indexes:bool, default is False
    #         When True, the method returns a list of epoch indexes in this DAC epochs table
    #         When False (the default), return a list of epochs
    #     train:bool or None
    #         When a bool, restricts the look up to where digChannel emits a TTL train
    #         (True) or pulse (False).
    #
    #         Default is None
    #
    #     Returns:
    #     --------
    #     A list of epochs (or their indexes in the epochs table if 'indexes' is True)
    #     where digChannel is set (i.e., non-zero).
    #
    #     The list may be empty is none of the epochs define a digital pattern for
    #     the given sweep.
    #
    #     NOTE: In Clampex, the digital pattern defined in an epoch normally applies
    #     to ALL sweeps.
    #
    #     The only exception are the protocols where alternate digital pattern
    #     is enabled. In such protocols, the active DAC channel is the one where
    #     the "main" digital pattern is defined in the protocol editor, and this
    #     "main" pattern is applied to the sweeps with even index (0, 2, 4, etc).
    #     The "alternative" digital pattern is defined in any other DAC in the protocol
    #     editor, and is applied to the sweeps with odd index (1, 3, 5, etc)
    #
    #     NOTE: In reality, this apparent association between a digital pattern
    #     and a DAC is not born out by the hardware; however, digital patterns can
    #     only be configured inside an epoch for analog command waveform output
    #     defined for a particular DAC. This may give the false impression that
    #     a digital pattern is emitted through the DAC where such epochs were defined,
    #     in the protocol editor.
    #
    #     Things get more complicated when distinct digital patterns need to be
    #     emitted in consecutive sweeps. Currently, Clampex supports only the definition
    #     of only two digital patterns in the same protocol, as explained in the NOTE above.
    #
    #     For more complex experimental configuration (e.g. using three distinct
    #     digital patterns in consecutive sweeps) the only approach in Clampex
    #     appears to be the use of distinct ABF protocols via  "Sequencing keys".
    #     These protocols would have to generate just one sweep per run, with the
    #     disadvantage that recording averages would have to be done offline
    #     (or at least Outside Clampex).
    #
    #
    #     """
    #     isAlternateDigital = self.alternateDigitalOutputStateEnabled and sweep % 2 > 0
    #
    #     ret = list()
    #
    #     for k, epoch in enumerate(self.epochs):
    #         # see self.getEpochDigitalPattern for code logic
    #         digPattern = list()
    #         if self.alternateDigitalOutputStateEnabled and self.logicalIndex < 2:
    #             if self.digitalOutputEnabled:
    #                 if self.physicalIndex == self.protocol.activeDACChannel:
    #                     if digChannel in range(4):
    #                         digPattern = list(reversed(epoch.getEpochDigitalPattern(isAlternateDigital)[0]))
    #                     elif digChannel in range(4,8):
    #                         digPattern = list(reversed(epoch.getEpochDigitalPattern(isAlternateDigital)[1]))
    #                         digChannel -= 4
    #                     else:
    #                         raise ValueError(f"Expecting a digital channel index ('digChannel') in the interval [0 ⋯ 8); instead, got {digChannel}")
    #         else:
    #             if self.digitalOutputEnabled:
    #                 if digChannel in range(4):
    #                     digPattern = list(reversed(epoch.getEpochDigitalPattern()[0]))
    #                 elif digChannel in range(4,8):
    #                     digPattern = list(reversed(epoch.getEpochDigitalPattern()[1]))
    #                     digChannel -= 4
    #                 else:
    #                     raise ValueError(f"Expecting a digital channel index ('digChannel') in the interval [0 ⋯ 8); instead, got {digChannel}")
    #
    #         if digChannel < len(digPattern) and (digPattern[digChannel] != 0 if train is None else digPattern[digChannel] == '*' if train is True else digPattern[digChannel] == 1):
    #             if indexes:
    #                 ret.append(k)
    #             else:
    #                 ret.append(epoch)
    #
    #     return ret

#     def getEpochDigitalPattern(self, epoch:typing.Union[ABFEpoch, str, int],
#                                sweep:int=0) ->tuple:
#         r"""
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
#                         dig_3_0 = epoch.getEpochDigitalPattern(True)[0] # select first bank
#                         dig_7_4 = epoch.getEpochDigitalPattern(True)[1] # select second bank
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
#                         dig_3_0 = epoch.getEpochDigitalPattern(False)[0] # select first bank
#                         dig_7_4 = epoch.getEpochDigitalPattern(False)[1] # select second bank
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
#                 dig_3_0 = epoch.getEpochDigitalPattern()[0]
#                 dig_7_4 = epoch.getEpochDigitalPattern()[1]
#             else:
#                 dig_3_0 = dig_7_4 = [0,0,0,0]
#
#         return dig_3_0, dig_7_4

    @property
    def emulatesTTL(self)->bool:
        r"""True when this ADC emulates TTLs for3rd party devices.
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

    @property
    def stimulusFile(self) -> str:
        return self._dacStimulusFile_

    @stimulusFile.setter
    def stimulusFile(self, val:str):
        self._dacStimulusFile_ = val

    # @property
    # def isactiveDACChannel(self) -> bool:
    #     return self._isActiveDACChannel_

#     @property
#     def digitalOutputsEnabled(self) -> bool:
#         r"""True if any epoch defined in this DAC emits digital pulses or trains"""
#         # NOTE: 2023-10-18 09:57:46
#         # This is NOT an intrinsic variable in Clampex, but is used here to
#         # help identify if this DAC associates the main digital output pattern
#
#         # In Clampex, only one DAC can associate DIG out; however, when alternate
#         # digital output is enabled in the protocol, the alternative dig out
#         # pattern can only be defined on another DAC's GUI in the Waveforms tab
#         # of the Clampex protocol editor.
#
#         # I think this is unfortunate, as it may confuse one into thinkng that
#         # this "other" DAC emits dig out on alternate sweeps, when in fact it
#         # doesn't
#         #
#         return len(tuple(itertools.chain.from_iterable([e.getUsedDigitalOutputChannels(alternate=False) for e in self.epochs]))) > 0
#         # pass
#         # return self._digOutEnabled_

    def getChannelIndex(self, physical:bool=False):
        return self.physicalIndex if physical else self.logicalIndex

    @property
    def logicalIndex(self) -> int:
        r"""The index of the DAC channel configured in this object.
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
        r"""Alias to self.logicalIndex"""
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
        r"""Alias to self.name for backward compatibility"""
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

    # @property
    # def sweepSampleCount(self) -> int:
    #     r"""Read-only; can only be set up at initialization (construction)
    #     and stays the same throughout the lifetime of the object"""
    #     return self.protocol.sweepSampleCount

    # @property
    # def digitalOutputsCount(self) -> int:
    #     r"""Read-only; can only be set up at initialization (construction)
    #     and stays the same throughout the lifetime of the object"""
    #     return self.protocol.nDigitalOutputs

    # def getDigitalOutputs(self, alternate:typing.Optional[bool]=None,
    #                    trains:typing.Optional[bool]=None) -> set:
    #     return set(itertools.chain.from_iterable([e.getUsedDigitalOutputChannels(alternate, trains) for e in self.epochs]))

        # return self._digitalOutputs_

    # @property
    # def samplingRate(self) -> pq.Quantity:
    #     return self.protocol.samplingRate

    @property
    def dacHoldingLevel(self) -> pq.Quantity:
        r"""DAC-specific"""
        return self._dacHoldingLevel_

    @dacHoldingLevel.setter
    def dacHoldingLevel(self, val: pq.Quantity):
        if not scq.unitsConvertible(self.units, val.units):
            raise TypeError(f"Argument units {val.units} are incompatible with this channel units ({self.units})")

        self._dacHoldingLevel_ = val.rescale(self.units)

#     @property
#     def alternateDigitalOutputStateEnabled(self) -> bool:
#         if self.protocol:
#             return self.protocol.alternateDigitalOutputStateEnabled
#         return False
#
#     @property
#     def alternateDACOutputStateEnabled(self) -> bool:
#         if self.protocol:
#             return self.protocol.alternateDACOutputStateEnabled
#         return False

#     def getAnalogWaveform(self, sweep:int=0) -> neo.AnalogSignal:
#         return self.getCommandWaveform(sweep)
#
#     def getCommandWaveform(self, sweep:int=0) -> neo.AnalogSignal:
#         r"""Generates an AnalogSignal representation of the command waveform.
#
#         CAUTION: The 'sweep' parameter is only used to get the epoch parameter
#         values where these values vary from one sweep to another ("Delta level"
#         and "Delta duration"), and not to establish if the DAC would emit a
#         waveform for that particular sweep or not.
#
#         Whether a DAC emits an analog wavefomr on a particular sweep is determined
#         entirely by the protocol. The DAC only does what its Epochs "tell" it to do.
#         The protocol "tells" the DAC to emit a wavefomr or not, depending on the
#         protocols' alternateDACOutputStateEnabled and on the sweep number!
#
#         Therefore, the wavefomr returned here reflects sweep-specific state of
#         the epoch parametrs, and nothing else.
#
#
#
#
#     The analog waveform returned here is the one generated by
#         the Epchs in the DAC regardless
#
#         NOTE: DAC command waveforms and digital outputs are enabled only in
#         Episodic Stimulation type of experiments.
#
#         """
#         if self.analogWaveformSource == ABFDACWaveformSource.none or not self.analogWaveformEnabled:
#             # return empty signal (containing np.nan)
#             return neo.AnalogSignal(np.full((self.protocol.sweepSampleCount, 1), np.nan),
#                                     units = self.units, t_start = 0*pq.s,
#                                     sampling_rate = self.samplingRate,
#                                     name = self.dacName)
#
#         if self.analogWaveformSource == ABFDACWaveformSource.epochs:
#             if len(self.epochs) == 0:
#                 return neo.AnalogSignal(np.full((self.protocol.sweepSampleCount, 1), float(holdingLevel)),
#                                         units = self.units, t_start = 0*pq.s,
#                                         sampling_rate = self.samplingRate,
#                                         name = self.dacName)
#
#             if sweep > 0 and self.returnToHold:
#                 # is the waveform of a subsequent sweep is sought, and returnToHold
#                 # is True, then we need the level of the last epoch in the "previous"
#                 # sweep
#                 # previousLevel = self.epochs[-1].firstLevel + self.epochs[-1].deltaLevel * (sweep-1)
#                 previousLevel = self.getPreviousSweepLastEpochLevel(sweep)
#             else:
#                 previousLevel = self.dacHoldingLevel
#
#             waveform = neo.AnalogSignal(np.full((self.protocol.sweepSampleCount, 1), float(previousLevel)),
#                                         units = self.units, t_start = 0*pq.s,
#                                         sampling_rate = self.samplingRate,
#                                         name = self.dacName)
#
#             t0 = t1 = self.holdingTime.rescale(pq.s)
#
#             for epoch in self.epochs:
#                 actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
#                 epochSamplesCount = scq.nSamples(actualDuration, self.samplingRate)
#                 actualLevel = epoch.firstLevel + sweep * epoch.deltaLevel
#
#                 t1 = t0 + actualDuration
#                 tt = np.array([t0,t1])*pq.s
#                 ndx = waveform.time_index(tt)
#
#                 wave = self.getEpochAnalogWaveform(epoch, previousLevel, sweep)
#
#                 waveform[ndx[0]:ndx[1],0] = wave
#
#                 previousLevel = actualLevel
#                 t0 = t1
#
#             if self.returnToHold:
#                 waveform[ndx[1]:, 0] = previousLevel
#
#
#         else:
#             # TODO: 2023-09-18 15:44:03
#             # use waveform (stimulus) file
#             # for that, I need to modify axonrawio (or provide alternative) so
#             # that the strings section is properly read and inserted into the
#             # metadata / resulting neo.Block's annotations.
#             #
#             # a possible solution is to read the ABF file post-hoc using pyabf
#             # (called from a pictio function) and populate annotations there,
#             # thus avoiding changes to neo stock code
#             #
#             # NOTE: 2023-09-21 00:44:48
#             # the above logic is now implemented in pictio
#             # TODO: 2023-09-21 00:45:03
#             # use that informaiton here (search under annotations["sections"]["StringsSection"]["IndexedStrings"])
#             warnings.warning(f"Command waveforms from external stimulus files are not yet supported", RuntimeWarning)
#             return neo.AnalogSignal(np.full((self.protocol.sweepSampleCount, 1), np.nan),
#                                     units = self.units, t_start = 0*pq.s,
#                                     sampling_rate = self.samplingRate,
#                                     name = self.dacName)
#
#
#
#         return waveform

#     def getDigitalWaveform(self, sweep:int=0,
#                            digChannel:typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
#                            separateWaves:bool=True) -> neo.AnalogSignal:
#         r"""Realizes the digital output waveform (pulses, trains) emitted when
#         this DAC channel is active.
#
#         """
#         # NOTE: 2023-09-20 22:22:41
#         # the digital output is ALWAYS in V
#         # "high logic" means 5V on a background of 0 V
#         # "low logic" means 0V on a background of 5V
#
#         usedDigs = list(itertools.chain.from_iterable([epoch.getUsedDigitalOutputChannels() for epoch in self.epochs]))
#
#         if isinstance(digChannel, int):
#             if digChannel not in usedDigs:
#                 raise ValueError(f"Invalid DIG channel index {digChannel}")
#
#             digChannel = (digChannel,)
#
#         elif isinstance(digChannel, (list, tuple)) and all(isinstance(v, int) for v in digChannel):
#             if all(v not in usedDigs for v in digChannel):
#                 raise ValueError(f"Invalid DIG channel indexes {digChannel}")
#
#             digChannel = tuple(sorted(set(digChannel)))
#
#         elif digChannel is None:
#             digChannel = tuple(sorted(set(usedDigs)))
#
#         else:
#             raise TypeError(f"expecting digChannel an int or sequence of int; instead got {digChannel}")
#
#         if separateWaves:
#             waveforms = [neo.AnalogSignal(np.full((self.sweepSampleCount, 1),
#                                                 np.nan),
#                                         units = pq.V, t_start = 0*pq.s,
#                                         sampling_rate = self.samplingRate,
#                                         name = f"DIG {chnl} DAC {self.physicalIndex} ({self.name})") for chnl in digChannel]
#         else:
#             waveforms = neo.AnalogSignal(np.full((self.sweepSampleCount, len(digChannel)),
#                                                 np.nan),
#                                         units = pq.V, t_start = 0*pq.s,
#                                         sampling_rate = self.samplingRate,
#                                         name = f"DIG Output DAC {self.physicalIndex} ({self.name})")
#
#         t0 = t1 = self.holdingTime.rescale(pq.s)
#
#         offLevel = None
#
#         if separateWaves:
#             lastEpochNdx = [0] * len(digChannel)
#             lastLevel = [None] * len(digChannel)
#         else:
#             lastEpochNdx = 0
#             lastLevel = None
#
#         for epoch in self.epochs:
#             actualDuration = epoch.firstDuration + sweep * epoch.deltaDuration
#             t1 = t0 + actualDuration
#             tt = np.array([t0,t1])*pq.s
#
#             eWaves = self.getEpochDigitalWaveform(epoch, sweep, digChannel,
#                                              separateWaves=separateWaves,
#                                              returnLevels=True)
#
#             t0 = t1
#
#             if eWaves is None:
#                 continue
#
#             epochWaves, epoch_digOFF, epoch_digON, epoch_trainOFF, epoch_trainON = eWaves
#             offLevel = epoch_digOFF if epoch_digOFF is not None else epoch_trainOFF
#
#             if lastLevel is None:
#                 lastLevel = epoch_digOFF if epoch_digOFF is not None else epoch_trainOFF
#
#             if separateWaves:
#                 for k in range(len(epochWaves)):
#                     ndx = waveforms[k].time_index(tt)
#                     lastEpochNdx[k] = ndx[1]
#                     lastLevel[k] = epochWaves[k][-1]
#                     waveforms[k][ndx[0]:ndx[1], :] = epochWaves[k]
#
#             else:
#                 ndx = waveforms.time_index(tt)
#                 lastEpochNdx = ndx[1]
#                 lastLevel = epochWaves[0][-1,:]
#                 waveforms[ndx[0]:ndx[1], :] = epochWaves[0]
#
#         if self.protocol.digitalUseLastEpochHolding:
#             if separateWaves:
#                 for k in range(len(waveforms)):
#                     waveforms[k][lastEpochNdx[k]:, :] = lastLevel[k]
#             else:
#                  waveforms[lastEpochNdx:, :] = lastLevel
#         else:
#             if separateWaves:
#                 for k in range(len(waveforms)):
#                     waveforms[k][lastEpochNdx[k]:, :] = offLevel
#             else:
#                 waveforms[lastEpochNdx:, :] = offLevel
#
#         if separateWaves:
#             for k in range(len(waveforms)):
#                 waveforms[k][np.isnan(waveforms[k])] = offLevel
#         else:
#             waveforms[np.isnan(waveforms)] = offLevel
#
#         return waveforms

    def getEpochEmulatesTTL(dac, epoch, /, sweep:int=0) -> bool:
        r"""True when epoch type is ABFEpochType.Pulse and meets the conditions below:
        • First level       != 0
        • Delta level       == 0
        • Delta duration    == 0
        • all digital outputs are zero
        First duration, train rate and pulse duration are all > 0 (enforced by Clampex)
        """

        dac, epoch = self.check_DAC_Epoch(dac, epoch)
        return epoch.epochType == ABFEpochType.Pulse and epoch.firstLevel != 0 and \
            epoch.deltaLevel == 0 and epoch.deltaDuration == 0 and len(self.getActiveDigitalChannels(sweep, epoch)) == 0

# ### BEGIN module-level functions

def getEpochNumberFromLetter(x:str) -> int:
    r"""The inverse function of getEpochLetter()"""
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

def getABF(obj:typing.Union[str, pathlib.Path, neo.Block]):
    r"""
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

    if isinstance(obj, neo.Block):
        filename = getattr(obj, "file_origin", None)

    elif isinstance(obj, (str, pathlib.Path)):
        filename = pathlib.Path(obj)

    else:
        raise TypeError(f"Expecting a neo.Block, or a file past (str or patlhib.Path); instead, got {type(obj).__name__}")
#         if isinstance(obj, pathlib.Path):
#         filename = obj.as_posix()
#         # filename = getattr(obj, "file_origin", None)
#
#     filename = pathlib.Path(filename)

    if not filename.is_file():
        return
    loader = pio.getLoaderForFile(filename)

    if loader == pio.loadAxonFile:
        try:
            # if filename.lower().endswith(".abf"):
            if filename.suffix.lower() == ".abf":
                return pyabf.ABF(filename.as_posix())
            # elif filename.lower().endswith(".atf"):
            elif filename.suffix.lower() == ".atf":
                return pyabf.ATF(filename.as_posix())
            else:
                raise RuntimeError("pyabf can only handle ABF and ATF files")
        except:
            pass

    else:
        warning.warn(f"{filename} is not an Axon file")

def getABFsection(abf:pyabf.ABF, sectionType:typing.Optional[str] = None) -> dict:
    r"""Return a specific section from a pyabf.ABF object, as a dict.
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
    r""""""
    # NOTE: 2024-10-24 15:40:12
    # this should be Little-endian as it is generated on a IBM PC
    bytes = fb.read(2)
    values = struct.unpack("h", bytes) # ⇐ this is a tuple! first element is what we need
    # print(f"abfReader.readInt16 bytes = {bytes}, values = {values}")
    return values[0]

def readStruct(fb, structFormat, seek=False, cleanStrings=True):
    # NOTE: 2024-10-24 15:55:01
    # original code by Scott Harden https://github.com/swharden/pyABF
    import struct
    if seek:
        fb.seek(seek)
    vSize = struct.calcsize(structFormat)
    bString = fb.read(vSize)
    values = struct.unpack(structFormat, bString)

    if cleanStrings:
        values = tuple(map(lambda x: x.decode("ascii", errors="ignore").strip if isinstance(x, bytes) else x, values))
        # for i in range(len(values)):
        #     if type(values[i]) == type(b''):
        #         values[i] = values[i].decode("ascii", errors='ignore').strip()

    if len(values) == 1:
        return values[0]
    return values

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
def getDIGPatterns(o:typing.Union[neo.Block, pyabf.ABF], reverse_banks:bool=False, wrap:bool=False,
                   pack_str:bool=False, epoch_num:typing.Optional[int]=None) -> dict:
    r"""Access the digital patterns of bit flags associated with the Epochs.

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
    for the corresponding DIG channel index.

    NOTE: Below, the number of DIG channels (and banks) depends on the ditigizer:

    DigiData 1440 series: DIG channels (3, 2, 1, 0) i.e. one bank of 4 bits

    DigiData 1550 series: DIG channels ((3, 2, 1, 0) , (7, 6, 5, 4)) i.e. two
                        banks of 4 bits

    NOTE: In the ABF file metadata thse bit patterns are stored as 8 bytes (one
    byte per DIG channnel) for the main, and 8 bytes for the alternate pattern

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
def _getDIGPatterns_(obj:neo.Block, reverse_banks:bool=False, wrap:bool=False,
      pack_str:bool=False, epoch_num:typing.Optional[int]=None) -> dict:
    from core.neoutils import getAcquisitionInfo

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
        dpm = getSynchBitList(epoch_info["nDigitalValue"])
        dtm = getSynchBitList(epoch_info["nDigitalTrainValue"])
        dpa = getAlternateBitList(epoch_info["nAlternateDigitalValue"])
        dta = getAlternateBitList(epoch_info["nAlternateDigitalTrainValue"])

        digitalPatternMain = list()
        digitalPatternAlternate = list()

        for k in banks:
            patternMain = tuple(1 if dpm[k][i] and not dtm[k][i] else '*' if dtm[k][i] and not dpm[k][i] else 0 for i in range(len(dpm[k])))
            patternAlt  = tuple(1 if dpa[k][i] and not dta[k][i] else '*' if dta[k][i] and not dpa[k][i] else 0 for i in range(len(dpa[k])))

            if wrap:
                if not reverse_banks:
                    patternMain = tuple(reversed(patternMain))
                    patternAlt = tuple(reversed(patternAlt))

                digitalPatternMain.extend(patternMain)
                digitalPatternAlternate.extend(pattern)

                if pack_str:
                    digitalPatternMain = "".join(map(str, digitalPatternMain))
                    digitalPatternAlternate = "".join(map(str, digitalPatternAlternate))
            else:
                digitalPatternMain.append("".join(map(str, patternMain)) if pack_str else patternMain)
                digitalPatternAlternate.append("".join(map(str, patternAlt)) if pack_str else patternAlt)

        digitalPatternMain = tuple(digitalPatternMain)
        digitalPatternAlternate = tuple(digitalPatternAlternate)

        # epochsDigitalPattern[epochNumber] = {"main": digitalPatternMain, "alternate": digitalPatternAlternate}
        epochsDigitalPattern[epochNumber] = ABFDigitalPattern(digitalPatternMain, digitalPatternAlternate)

    return epochsDigitalPattern #, epochNumbers, epochDigital, epochDigitalStarred, epochDigitalAlt, epochDigitalStarredAlt

@getDIGPatterns.register(pyabf.ABF)
def _getDIGPatterns_(abf:pyabf.ABF, reverse_banks:bool=False, wrap:bool=False,
      pack_str:bool=False, epoch_num:typing.Optional[int]=None) -> dict:
    r"""Creates a representation of the digital pattern associated with a DAC channel.

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
            # NOTE: 2024-10-23 17:34:09
            # these MUST be executed in the order BELOW:
            epochNumber = readInt16(fb)
            epochDigPM  = readInt16(fb) # reads the main "pulse" ("steps") digital pattern (0s and 1s, for ditigal steps)
            epochDigTM  = readInt16(fb) # reads the main "train" ("pulses", "starred") digital pattern (for digital pulse trains)
            epochDigPA  = readInt16(fb) # reads the alternative "pulse" digital pattern
            epochDigTA  = readInt16(fb) # reads the alternative "train" digital patter

            if isinstance(epoch_num, int) and epoch_num != epochNUumber:
                # skip if requesting for a specific epoch
                continue

            epochDict = dict()

            # each of these is a list of two lists (DIG bank 3-0 and DIG bank 7-4)
            dpm = getSynchBitList(epochDigPM)       # main steps
            dtm = getSynchBitList(epochDigTM)       # main train (starred)
            dpa = getAlternateBitList(epochDigPA)   # alternative steps
            dta = getAlternateBitList(epochDigTA)   # alternative train (starred)


            digitalPatternMain = list()
            digitalPatternAlternate = list()

            # for k in range(2): # two banks
            for k in banks:
                patternMain = tuple(1 if dpm[k][i] and not dtm[k][i] else '*' if dtm[k][i] and not dpm[k][i] else 0 for i in range(len(dpm[k])))
                patternAlt  = tuple(1 if dpa[k][i] and not dta[k][i] else '*' if dta[k][i] and not dpa[k][i] else 0 for i in range(len(dpa[k])))

                if wrap:
                    if not reverse_banks:
                        patternMain = tuple(reversed(patternMain))
                        patternAlt = tuple(reversed(patternAlt))

                    digitalPatternMain.extend(patternMain)
                    digitalPatternAlternate.extend(patternAlt)

                    if pack_str:
                        digitalPatternMain = "".join(map(str, digitalPatternMain))
                        digitalPatternAlternate = "".join(map(str, digitalPatternAlternate))
                else:
                    digitalPatternMain.append("".join(map(str, patternMain)) if pack_str else patternMain)
                    digitalPatternAlternate.append("".join(map(str, patternAlt)) if pack_str else patternAlt)

            digitalPatternMain = tuple(digitalPatternMain)
            digitalPatternAlternate = tuple(digitalPatternAlternate)

            # epochsDigitalPattern[epochNumber] = {"main": digitalPatternMain, "alternate": alternateDigitalPattern}
            epochsDigitalPattern[epochNumber] = ABFDigitalPattern(digitalPatternMain, digitalPatternAlternate)

        return epochsDigitalPattern #, epochNumbers, epochDigital, epochDigitalStarred, epochDigitalAlt, epochDigitalStarredAlt

# @singledispatch
# def getABFEpochTable(o, sweep:typing.Optional[int]=None,
#                       dacChannel:typing.Optional[int] = None,
#                       as_dataFrame:bool=False, allTables:bool=False) -> list:
#     raise NotImplementedError(f"This function does not support {type(o).__name__} objects")
#
# @getABFEpochTable.register(pyabf.ABF)
# def _(x:pyabf.ABF, sweep:typing.Optional[int]=None,
#                       dacChannel:typing.Optional[int] = None,
#                       as_dataFrame:bool=False, allTables:bool=False) -> list:
#     if not isinstance(x, pyabf.ABF):
#         raise TypeError(f"Expecting a pyabf.ABF object; got {type(x).__name__} instead")
#
#     sweepTables = list()
#
#     if isinstance(sweep, int):
#         if sweep < 0 or sweep >= x.sweepCount:
#             raise ValueError(f"Invalid sweep {sweep} for {x.sweepCount} sweeps")
#
#         x.setSweep(sweep)
#         # NOTE: 2022-03-04 15:30:22
#         # only return the epoch tables that actually contain any non-OFF epochs (filtered here)
#         if isinstance(dacChannel, int):
#             if dacChannel not in x._dacSection.nDACNum:
#                 raise ValueError(f"Invalid DAC channel index (dacChannel) {dacChannel}; current DAC channel indices are {x._dacSection.nDACNum}")
#
#             etables = [pyabf.waveform.EpochTable(x, dacChannel)] # WARNING: 2023-09-06 23:36:28 may be an empty EpochTable
#         else:
#             if allTables:
#                 etables = list(pyabf.waveform.EpochTable(x, c) for c in x._dacSection.nDACNum)
#                 # etables = list(pyabf.waveform.EpochTable(x, c) for c in x.channelList)
#             else:
#                 etables = list(filter(lambda e: len(e.epochs) > 0, (pyabf.waveform.EpochTable(x, c) for c in x.channelList)))
#
#         if as_dataFrame:
#             etables = [epochTable2DF(e, x) for e in etables]
#
#         sweepTables.append(etables)
#
#     else:
#         for sweep in range(x.sweepCount):
#             x.setSweep(sweep)
#             if isinstance(dacChannel, int):
#                 if dacChannel not in x._dacSection.nDACNum:
#                     raise ValueError(f"Invalid DAC channel index (dacChannel) {dacChannel}; current DAC channel indices are {x._dacSection.nDACNum}")
#
#                 etables = [pyabf.waveform.EpochTable(x, dacChannel)] # WARNING: 2023-09-06 23:36:28 may be an empty EpochTable
#             else:
#                 if allTables:
#                     etables = list(pyabf.waveform.EpochTable(x, c) for c in x._dacSection.nDACNum)
#                 else:
#                     etables = list(filter(lambda e: len(e.epochs) > 0, (pyabf.waveform.EpochTable(x, c) for c in x.channelList)))
#
#             if as_dataFrame:
#                 etables = [epochTable2DF(e, x) for e in etables]
#
#             sweepTables.append(etables)
#
#     return sweepTables
#
# @getABFEpochTable.register(neo.Block)
# def _(x:neo.Block, sweep:typing.Optional[int]=None,
#                       dacChannel:typing.Optional[int] = None,
#                       as_dataFrame:bool=False, allTables:bool=False) -> list:
#     pass

# @singledispatch
# def epochTable2DF(obj, src) -> pd.DataFrame:
#     r"""Returns a pandas.DataFrame with the data from the epoch table 'x'
#     """
#     raise NotImplementedError(f"{type(obj).__name__} objects are not supported")
#
# # def _(x:pyabf.waveform.EpochTable, abf:typing.Optional[pyabf.ABF] = None):
# @epochTable2DF.register(pyabf.waveform.EpochTable)
# def _(x:pyabf.waveform.EpochTable, abf:typing.Optional[pyabf.ABF] = None) -> pd.DataFrame:
#     # if not isinstance(x, pyabf.waveform.EpochTable):
#     #     raise TypeError(f"Expecting an EpochTable; got {type(x).__name__} instead")
#
#     # NOTE: 2022-03-04 15:38:31
#     # code below adapted from pyabf.waveform.EpochTable.text
#     #
#
#     rowIndex = ["Type", "First Level", "Delta Level", "First Duration (points)", "Delta Duration (points)",
#                 "First duration (ms)", "Delta Duration (ms)",
#                 "Digital Pattern #3-0", "Digital Pattern #7-4",
#                 "Train Period (points)", "Pulse Width (points)",
#                 "Train Period (ms)", "Pulse Width (ms)"]
#
#     # prepare lists to hold values for each epoch
#
#     # NOTE: 2022-03-04 16:05:20
#     # skip "Off" epochs
#     epochs = [e for e in x.epochs if e.typeName != "Off"]
#
#     if len(epochs):
#         epochCount = len(epochs)
#         epochLetters = [''] * epochCount
#
#         epochData = dict()
#
#         for i, epoch in enumerate(epochs):
#             assert isinstance(epoch, pyabf.waveform.Epoch)
#
#             if isinstance(abf, pyabf.ABF):
#                 # adcName, adcUnits = abf._getAdcNameAndUnits(x.channel)
#                 dacName, dacUnits = abf._getDacNameAndUnits(x.channel)
#
#             else:
#                 dacName = dacUnits = None
#
#             dacLevel = epoch.level*scq.unitQuantityFromNameOrSymbol(dacUnits) if isinstance(dacUnits, str) and len(dacUnits.strip()) else epoch.level
#             dacLevelDelta = epoch.levelDelta*scq.unitQuantityFromNameOrSymbol(dacUnits) if isinstance(dacUnits, str) and len(dacUnits.strip()) else epoch.levelDelta
#
#             epValues = np.array([epoch.epochTypeStr,    # str description of epoch type (as per Clampex e.g Step, Pulse, etc)
#                               dacLevel,                 # "first" DAC level -> quantity; CAUTION units depen on Clampex and whether its telegraphs were OK
#                               dacLevelDelta,            # "delta" DAC level: level change with each sweep in the run; quantity, see above
#                               epoch.duration,           # "first" duration (samples)
#                               epoch.durationDelta,      # "delta" duration (samples)
#                               epoch.duration/x.sampleRateHz * 1000 * pq.ms, # first duration (time units)
#                               epoch.durationDelta/x.sampleRateHz * 1000 * pq.ms, # delta duration (time units)
#                               epoch.getEpochDigitalPattern()[:4], # first 4 digital channels
#                               epoch.getEpochDigitalPattern()[4:], # last 4 digital channels
#                               epoch.pulsePeriod,        # train period (samples')
#                               epoch.pulseWidth,         # pulse width (samples)
#                               epoch.pulsePeriod/x.sampleRateHz * 1000 * pq.ms, # train period (time units)
#                               epoch.pulseWidth/x.sampleRateHz * 1000 * pq.ms], # pulse width (time units)
#                               dtype=object)
#
#             epochData[epoch.getEpochLetter] = epValues
#
#         #colIndex = epochLetters
#
#         return pd.DataFrame(epochData, index = rowIndex)
#
# @epochTable2DF.register(ABFEpoch)
# def _(x:ABFEpoch, _=None) -> pd.DataFrame:
#     return x.toDataFrame()

@singledispatch
def getABFHoldDelay(obj):
    r"""Returns the duration of holding time before actual sweep start.
    DEPRECATED: 2024-11-15 10:34:29 use protocol.holdingTime property, instead

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
def _getABFHoldDelay_(abf:pyabf.ABF):
    isABF2 = abf.abfVersion["major"] == 2
    protocol = getABFsection(abf,"protocol")
    samplingPeriod = (1/(abf.sampleRate*pq.Hz)).rescale(pq.s)
    return int(abf.sweepPointCount/64) * samplingPeriod

@getABFHoldDelay.register(neo.Block)
def _getABFHoldDelay_(data:neo.Block):
    try:
        isABF2 = data.annotations["generator"]["fFileSignature"].decode() == "ABF2"
        if not isABF2:
            raise NotImplementedError("This function only supports ABF2 version")

        protocol = data.annotations["generator"]["protocol"]

        # NOTE: 2023-08-28 09:35:22
        # this could be obtained from the analogsignals, but what if someone
        # corrupts the data by inserting an analog signal with a different
        # sampling rate? It seems 'neo' does not have a way to prevent that.
        samplingPeriod = 1 * pq.s/data.annotations["generator"]["sampling_rate"]

        # NOTE: 2023-08-28 09:40:18
        # the number of points per sweep is calculated as (see pyabf):
        # dataPointCount / sweepCount / channelCount , where all are properties
        # of the pyabf.ABF object;
        # in the annotations, these are stored as follows:
        # dataPointCount    → ["sections"]["DataSection"]["llNumEntries"]
        # sweepCount        → ["lActualEpisodes"] = ["protocol"]["lEpisodesPerRun"]
        # channelCount      → ["sections"]["ADCSection"]["llNumEntries"]
        sweepPointCount = data.annotations["generator"]["sections"]["DataSection"]["llNumEntries"] / data.annotations["generator"]["lActualEpisodes"] / data.annotations["generator"]["sections"]["ADCSection"]["llNumEntries"]

        return int(sweepPointCount/64) * samplingPeriod

    except:
        traceback.print_exc()
        raise RuntimeError(f"The {type(data).__name__} data {data.name} does not seem to have been generated from readind an ABF file")

# @singledispatch
# def getActiveDACChannel(obj) -> int:
#     r"""Returns the index of the active DAC channel.
#
#     WARNING: Only works with a neo.Block generated from an Axon ABF file.
#
#     The function first tries to create a pyabf.ABF object using the Axon (ABF)
#     file as indicated in the 'file_origin' attribute of 'data'.
#
#     When this fails, (usually because the original ABF file cannot be found) the
#     function will inspect the 'annotations' attribute of 'data' as a fallback.
#     If the data was read from an ABF file using Scipyen's pictio module, then the
#     'annotations' attribute should already contain the relevant information.
#
#     """
#     raise NotImplementedError(f"Not implemented for {type(obj).__name__} objects")

# @getActiveDACChannel.register(pyabf.ABF)
# def _(abf:pyabf.ABF) -> int:
#     return abf._protocolSection.nActiveDACChannel
#
# @getActiveDACChannel.register(neo.Block)
# def _(data:neo.Block) -> int:
#     try:
#         isAxon = data.annotations.get("software", None) == "Axon"
#         if not isAxon:
#             raise NotImplementedError("This function suypports only data recorded with Axon software")
#         isABF2 = data.annotations["fFileSignature"].decode() == "ABF2"
#         if not isABF2:
#             raise NotImplementedError("This function only supports ABF2 version")
#
#         return data.annotations["protocol"]["nActiveDACChannel"]
#     except:
#         traceback.print_exc()
#         raise RuntimeError(f"The {type(data).__name__} data {data.name} does not seem to have been generated from readind an ABF file")
#

# @singledispatch
# def getDACCommandWaveforms(obj,
#                         sweep:typing.Optional[int] = None,
#                         adcChannel:typing.Optional[typing.Union[int, str]] = None,
#                         dacChannel:typing.Optional[typing.Union[int, str]]=None,
#                         absoluteTime:bool=False) -> dict:
#     r"""Retrieves the waveforms of the command (DAC) signal.
#
#     Returns one waveform per sweep (i.e., per neo.Segment) unless segmentIndex
#     if specified, and has a valid int value.
#
#     WARNING: Only works with a neo.Block generated from an Axon ABF file.
#
#     The function first tries to create a pyabf.ABF object using the Axon (ABF)
#     file as indicated in the 'file_origin' attribute of 'data'.
#
#     When this fails (usually because the original ABF file cannot be found) the
#     function will fallback on using information contained in the 'annotations'
#     attribute and the properties on the analog signals contained in the data.
#
#     This is OK ONLY if the data was obtained by reading the ABF file using
#     neo.io module via Scipyen's pictio module functions.
#
#     CAUTION: Using synthetic data (e.g. neo.Block created manually) or data
#     augmented manually (such as by adding manually-created segments and/or signals)
#     will most likely result in an Exception being raised.
#
#     """
#     raise NotImplementedError(f"Not implemented for {type(obj).__name__} objects")
#
# @getDACCommandWaveforms.register(pyabf.ABF)
# def _(abf: pyabf.ABF,
#       sweep:typing.Optional[int] = None,
#       adcChannel:typing.Optional[typing.Union[int, str]] = None,
#       dacChannel:typing.Optional[typing.Union[int, str]] = None,
#       absoluteTime:bool=False) -> dict:
#     r"""Retrieves the waveforms of the command (DAC) signal."""
#
#     # NOTE: 2023-08-28 15:31:13
#     # each ADC input channels in Clampex is associated with one DAC output
#     # for the most complete configuration, IN0 and IN1 are typically associated with OUT0
#     # IN2 and IN3 are associated with OUT1, etc; here, IN0 and IN2 are the
#     # primary input channels from the amplifierl; IN1 and IN3 are the secondary
#     # inputs from the amplifier
#
#     def __f__(a_:abf, dacIndex:int) -> neo.AnalogSignal:
#         x_units = scq.unitQuantityFromNameOrSymbol(abf.sweepUnitsX)
#         x = abf.sweepX
#         y_name, y_units_str = abf._getDacNameAndUnits(dacIndex)
#         y_units = scq.unitQuantityFromNameOrSymbol(y_units_str) if isinstance(y_units_str, str) else pq.dimensionless
#         abfChannel = abf.sweepChannel # the current channel in the ABF, set when calling abf.setSweep(…)
#
#         # NOTE: 2023-08-28 15:09:15
#         # the command waveform for this sweep
#         # WARNING: this can be manually overwritten; in this case, all bets are off
#         #
#         # NOTE: when not overwritten, sweepC delegates to stimulus.dacWaveform
#         # in turn this checks if a waveform is enabled, or if the waveform is
#         # defined in a file;
#         #
#         # the variables nWaveformEnable and nWaveformSource are defined in
#         #   header (for ABF1)
#         #   dac section (for ABF2)
#         #
#         # nWaveformEnable →   0 (disabled);
#         #                     1 (enabled)
#         #
#         # nWaveformSource →   0 (no waveform);
#         #                     1 (defined in the epoch table)
#         #                     2 (defined in a separate file)
#         #
#         # if neither, then this will return a synthetic array filled with the
#         # holding values - not sure we want this, because, in effect, THERE IS NO
#         # command waveform on that channel... But this information is not available
#         # until one calls sweepC for that channel - so there is no way of knowing this beforehand
#         #
#         # So, instead of calling accessing sweepC (however convenient this may be)
#         # we may want to directly run the actual stimulus code instead
#         # (or call sweepC but then check the 'text' property of the correspdonding
#         # stimulus, which has been updated while calling sweepC) - IMO the design
#         # of pyabf is not ideal...
#
#         y = abf.sweepC
#
#         stimObj = abf.stimulusByChannel[abfChannel]
#
#         if stimObj.text == "DAC waveform is not enabled":
#             # NOTE: 2023-09-02 22:41:41
#             # this happens when there is no Epoch defined in the Epoch Table
#             # for the given ADC/DAC channels combination
#             y_name += " (disabled)"
#
#         elif stimObj.text == "DAC waveform is controlled by custom file":
#             y_name += " from file" # TODO 2023-08-31 15:29:15 FIXME get the name of the stimulus file
#         # y_label = abf.sweepLabelC
#         sampling_rate = abf.sampleRate * pq.Hz
#
#         return neo.AnalogSignal(y, units = y_units,
#                                 t_start = x[0] * x_units,
#                                 sampling_rate = abf.sampleRate * pq.Hz,
#                                 name = y_name)
#
#     if isinstance(sweep, int):
#         if sweep not in range(abf.sweepCount):
#             raise ValueError(f"Invalid sweep {sweep} for {abf.sweepCount} sweeps")
#
#     elif sweep is not None:
#         raise TypeError(f"Expecting sweep an int in range {abf.sweepCount} or None; instead, got {type(sweep).__name__}")
#
#     ADCs = usedADCs(abf)
#     ADCnames = tuple(x[0] for x in ADCs.values())
#     DACs = usedDACs(abf)
#     DACnames = tuple(x[0] for x in DACs.values())
#
#     if isinstance(adcChannel, int):
#         # if adcChannel not in range(len(abf.adcNames)) :
#         if adcChannel not in ADCs.keys() :
#             raise ValueError(f"Invalid ADC channel {adcChannel} for ADC channels {tuple(ADCs.keys())}")
#
#     elif isinstance(adcChannel, str):
#         if adcChannel not in ADCnames:
#             raise ValueError(f"ADC channel {adcChannel} not found; current ADC channels are {ADCnames}")
#
#         adcChannel = ADCs[ADCnames.index(adcChannel)]
#
#     elif adcChannel is not None:
#         raise TypeError(f"adcChannel expected to be an int in {tuple(ADCs.keys())}, a string in {ADCnames}, or None; instead, got {type(adcChannel).__name__}")
#
#     if isinstance(dacChannel, int):
#         if dacChannel not in tuple(DACs.keys()):
#             raise ValueError(f"Invalid ADAC channel {dacChannel} for DAC channels {tuple(DACs.keys())}")
#
#     elif isinstance(dacChannel, str):
#         if dacChannel not in DACnames:
#             raise ValueError(f"DAC channel {dacChannel} not found; current DAC channels are {DACnames}")
#
#         dacChannel = DACs[DACnames.index(dacChannel)]
#
#     elif dacChannel is not None:
#         raise TypeError(f"dacChannel expected to be an int in {tuple(DACs.keys())},a string in {DACnames}, or None; instead, got {type(dacChannel).__name__}")
#
#     # ret = list()
#     ret = dict()
#
#     if not isinstance(sweep, int):
#         for s in range(abf.sweepCount):
#             if not isinstance(adcChannel, int):
#                 adcChannelWaves = dict()
#                 # for chnl in range(len(abf.adcNames)):
#                 for chnl in ADCs:
#                     abf.setSweep(s, chnl, absoluteTime)
#                     if not isinstance(dacChannel, int):
#                         dacChannelWaves = dict()
#                         # for dacChnl in range(len(abf.dacNames)):
#                         for dacChnl in DACs:
#                             dacChannelWaves[f"DAC_{dacChnl}_{DACs[dacChnl][0]}"] = __f__(abf, dacChnl)
#
#                     else:
#                         dacChannelWaves = {f"DAC_{dacChannel}_{DACs[dacChannel][0]}": __f__(abf, dacChannel)}
#
#                     adcChannelWaves[f"ADC_{chnl}_{ADCs[chnl][0]}"] = dacChannelWaves
#             else:
#                 abf.setSweep(s, adcChannel, absoluteTime)
#                 if not isinstance(dacChannel, int):
#                     dacChannelWaves = dict()
#                     for dacChnl in range(len(abf.dacNames)):
#                         dacChannelWaves[f"DAC_{dacChnl}_{DACs[dacChnl][0]}"] = __f__(abf, dacChnl)
#
#                 else:
#                     dacChannelWaves = {f"DAC_{dacChannel}_{DACs[dacChannel][0]}": __f__(abf, dacChannel)}
#
#                 adcChannelWaves = {f"ADC_{adcChannel}_{ADCs[adcChannel][0]}": dacChannelWaves}
#
#             ret[f"sweep_{s}"] = adcChannelWaves
#
#     else:
#         if not isinstance(adcChannel, int):
#             adcChannelWaves = dict()
#             # for adcChnl in range(len(abf.adcNames)):
#             for adcChnl in ADCs:
#                 abf.setSweep(sweep, adcChnl, absoluteTime)
#                 if not isinstance(dacChannel, int):
#                     dacChannelWaves = dict()
#                     for dacChnl in DACs:
#                         dacChannelWaves[f"DAC_{dacChnl}_{DACs[dacChnl][0]}"] = __f__(abf, dacChnl)
#
#                 else:
#                     dacChannelWaves = {f"DAC_{dacChannel}_{DACs[dacChannel][0]}": __f__(abf, dacChannel)}
#
#                 adcChannelWaves[f"ADC_{chnl}_{ADCs[chnl][0]}"] = dacChannelWaves
#
#         else:
#             abf.setSweep(sweep, adcChannel, absoluteTime)
#             if not isinstance(dacChannel, int):
#                 # for dacChnl in range(abf._dacSection._entryCount):
#                 dacChannelWaves = dict()
#                 # for dacChnl in range(len(abf.dacNames)):
#                 for dacChnl in DACs:
#                     dacChannelWaves[f"DAC_{dacChnl}_{DACs[dacChnl][0]}"] = __f__(abf, dacChnl)
#
#             else:
#                 dacChannelWaves = {f"DAC_{dacChannel}_{DACs[dacChannel][0]}": __f__(abf, dacChannel)}
#
#             adcChannelWaves[f"ADC_{adcChannel}_{ADCs[adcChannel][0]}"] = dacChannelWaves
#
#         ret[f"sweep_{sweep}"] = adcChannelWaves
#
#     return ret
#
# @getDACCommandWaveforms.register(neo.Block)
# def _(data:neo.Block,
#       sweep:typing.Optional[int] = None,
#       adcChannel:typing.Optional[typing.Union[int, str]] = None,
#       dacChannel:typing.Optional[typing.Union[int, str]]=None,
#       absoluteTime:bool=False) -> dict:
#
#     def __f__(a_:abf, dacIndex:int) -> neo.AnalogSignal:
#         x_units = scq.unitQuantityFromNameOrSymbol(abf.sweepUnitsX)
#         x = abf.sweepX
#         y_name, y_units_str = abf._getDacNameAndUnits(dacIndex)
#         y_units = scq.unitQuantityFromNameOrSymbol(y_units_str)
#         y = abf.sweepC # the command waveform for this sweep
#         # y_label = abf.sweepLabelC
#         sampling_rate = abf.sampleRate * pq.Hz
#
#         return neo.AnalogSignal(y, units = y_units,
#                                 t_start = x[0] * x_units,
#                                 sampling_rate = abf.sampleRate * pq.Hz,
#                                 name = y_name)
#
#     sweepCount = data.annotations["lActualEpisodes"]
#
#     # NOTE: 2023-08-30 12:15:16
#     # just make sure no segments have been added/removed to the block after it
#     # has been read from its original ABF file
#     if sweepCount != len(data.segments):
#         raise RuntimeError(f"The number of segments ({len(data.segments)}) in the 'data' {data.name} is different from what ABF header reports ({sweepCount})")
#
#     if isinstance(sweep, int):
#         if sweep not in range(sweepCount):
#             raise ValueError(f"Invalid sweep {sweep} for {sweepCount} sweeps")
#
#     elif sweep is not None:
#         raise TypeError(f"Expecting sweep an int in range {sweepCount} or None; instead, got {type(sweep).__name__}")
#
#     # NOTE: 2023-08-30 12:56:11
#     # number of ADC channels in the file is found in ADCSection.llNumEntries
#     # NOTE: these are the ADC channels USED in the file, NOT ADC channels
#     # available on the DAQ device!!!
#     #
#     # names and units of the ADC channels are placed by AxonRawIO into listADCInfo
#     # (which therefore has same length as the number of ADC channels used in the
#     # ABF file)
#     #
#     # it is therefore easy to figure out names & units (+ scaling etc) ONLY for
#     # those ADC channels that have been used to record data
#
#     adcCount = data.annotations["sections"]["ADCSection"]["llNumEntries"]
#
#     adcNames = [i["ADCChNames"].decode() for i in data.annotations["listADCInfo"]]
#
#     if isinstance(adcChannel, int):
#         if adcChannel not in range(adcCount):
#             raise ValueError(f"Invalid ADC channel {adcChannel} for {adcCount} ADC channels")
#
#     elif isinstance(adcChannel, str):
#         if adcChannel not in adcNames:
#             raise ValueError(f"ADC channel {adcChannel} not found; current ADC channels are {adcNames}")
#
#         adcChannel = adcNames.index(adcChannel)
#
#     elif adcChannel is not None:
#         raise TypeError(f"adcChannel expected to be an int in range 0 ... {adcCount}, a string in {adcNames}, or None; instead, got {type(adcChannel).__name__}")
#
#     # NOTE: 2023-08-30 12:56:26
#     # For DAC channels the situation is different: we have to dig out which of these
#     # are actually used in the file/experiment, using the epoch info.
#     #
#     # the actual DAC used in each protocol epoch is contained in the 'dictEpochInfoPerDAC'
#     # of the annotations.
#     #
#     # Structure of the dictEpochInfoPerDAC:
#     #
#     # dictEpochInfoPerDAC maps int keys (DAC number) with a nested dict
#     #   the nested dict maps  key (Epoch number) to a sub-nested dict of fields
#     #
#     # Only the used DACs are included in dictEpochInfoPerDAC.
#     #
#     # So, if the Outputs tab of the protocol editor uses DAC channels 0 and 1 (e.g.
#     # "Cmd 0" and "Cmd 1")then the dictEpochInfoPerDAC will contain only two
#     # key → value pairs, with keys (int) 0 and 1, each mapped to a sub-nested dict
#     # of epochs describing the parameters sent to the corresponding DAC (0 or 1)
#     #
#     # Now, whether each DAC is used to send a command waveform to the electrode
#     # is configured separately, in the "Epochs" tab of the protocol editor; this
#     # information is given in the 'listDACInfo'
#     #
#     # listDACInfo is a list of dicts, expected to be ordered by the DAC output channel
#     #
#     # CAUTION: 2023-08-30 14:15:11
#     # this is where pyabf bridge may be supplying redundant information
#     #
#     usedDacCount = len(data.annotations["dictEpochInfoPerDAC"])
#
#     usedDACIndices = list(data.annotations["dictEpochInfoPerDAC"].keys())
#
#     # if dacChannel

@singledispatch
def getABFversion(obj) -> int:
    raise NotImplementedError(f"Not implemented for {type(obj).__name__} objects")

@getABFversion.register(pyabf.ABF)
def _getABFversion_(obj:pyabf.ABF) -> int:
    return abf.abfVersion["major"]

@getABFversion.register(neo.Block)
def _getABFversion_(obj:neo.Block) -> int:
    from core.neoutils import getAcquisitionInfo

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
    r"""Returns a mapping of used ADC channel index (int) to pair (name, units).

    Units are returned as a python Quantity if useQuantities is True, else as
    a string (units symbol)
"""
    raise NotImplementedError(f"Not implemented for {type(obj).__name__} objects")

@usedADCs.register(pyabf.ABF)
def _usedADCs_(obj:pyabf.ABF, useQuantities:bool=True) -> dict:
    return dict(map(lambda x: (x, __wrap_to_quantity__(obj._getAdcNameAndUnits(x), useQuantities)),
                    obj._adcSection.nADCNum))

@usedADCs.register(neo.Block)
def _usedADCs_(obj:neo.Block, useQuantities:bool=True) -> dict:
    from core.neoutils import getAcquisitionInfo

    assert sourcedFromABF(obj), "Object does not appear to be sourced from ABF"
    info_dict = getAcquisitionInfo(obj)
    return dict(map(lambda x: (x, (info_dict["listADCInfo"][x]["ADCChNames"].decode(),
                                   unitStrAsQuantity(info_dict["listADCInfo"][x]["ADCChUnits"].decode(), useQuantities))),
                    range(info_dict["sections"]["ADCSection"]["llNumEntries"])))

@singledispatch
def usedDACs(obj, useQuantities:bool=True) -> dict:
    r"""Returns a mapping of used DAC channel index (int) to pair (name, units)

    Units are returned as a python Quantity if useQuantities is True, else as
    a string (units symbol)
"""
    raise NotImplementedError(f"Not implemented for {type(obj).__name__} objects")

@usedDACs.register(pyabf.ABF)
def _usedDACs_(obj:pyabf.ABF, useQuantities:bool=True) -> dict:
    return dict(map(lambda d: (d, __wrap_to_quantity__(obj._getDacNameAndUnits(d), useQuantities)),
                    filter(lambda x: obj._dacSection.nWaveformEnable[x] and obj._dacSection.nWaveformSource[x] > 0, obj._dacSection.nDACNum)))

@usedDACs.register(neo.Block)
def _usedDACs_(obj:neo.Block, useQuantities:bool=True) -> dict:
    from core.neoutils import getAcquisitionInfo

    assert sourcedFromABF(obj), "Object does not appear to be sourced from ABF"
    info_dict = getAcquisitionInfo(obj)
    return dict(map(lambda d: (d["nDACNum"], (d["DACChNames"].decode(), unitStrAsQuantity(d["DACChUnits"].decode(), useQuantities))),
                    filter(lambda x: x["nWaveformEnable"] > 0 and x["nWaveformSource"] > 0, info_dict["listDACInfo"])))

@singledispatch
def isDACWaveformEnabled(obj, channel:int) -> bool:
    raise NotImplementedError(f"Not implemented for {type(obj).__name__} objects")

@isDACWaveformEnabled.register(pyabf.ABF)
def _isDACWaveformEnabled_(obj, dacChannel:int) -> bool:
    abf_version = getABFversion(obj)
    assert abf_version in (1,2), f"Unsupported ABF version {abf_version}"

    section = obj._headerV1 if abf_version == 1 else obj._dacSection

    return obj._dacSection.nWaveformEnable[dacChannel] == 1

@isDACWaveformEnabled.register(neo.Block)
def _isDACWaveformEnabled_(obj, channel:int) -> bool:
    assertFromABFmsg = "Object does not seem to be created from an ABF file"
    abf_version = getABFversion(obj)
    assert abf_version in (1,2), f"Unsupported ABF version {abf_version}"

    epochInfoPerDAC = data.annotations.get("dictEpochInfoPerDAC", None)

    assert isinstance(epochInfoPerDAC, dict) , assertFromABFmsg

    assert channel in epochInfoPerDAC.keys(), f"ADC channel {channel} if not used"

    channelEpochInfoPerDac = epochInfoPerDAC[channel]


def showEpochsTable(p: ABFProtocol):
    pass # TODO: 2026-03-31 08:55:59 use interact.packInputs(…)

# def isFlatEpoch(e:ABFEPoch) -> bool:
#     r"""Returns ``True`` if the epoch ``e`` does nothing.
#
# .. note::
#     A *flat* epoch if an epoch during which no command waveforms or digital TTLs
# are emitted for a specific DAC during a specific sweep
# """

# ### END module-level functions





