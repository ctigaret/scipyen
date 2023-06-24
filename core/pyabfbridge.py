"""Bridge to pyabf package

Requires pyabf.

PyABF (https://swharden.com/pyabf/) is not currently used to load Axon ABF files.
Scipyen uses the neo package (https://neo.readthedocs.io/en/stable/) to represent

This is because all electrophysiology signals are represented in Scipyen as
objects of the types defined in the neo framework. 

However, pyABF does offer complementary functionality to neo package, allowing
the inspection of acquisition protocol data embedded in an axon file.

See also 
• https://swharden.com/pyabf/tutorial/ 
• https://swharden.com/pyabf/


NOTE: About pyabf EpochSection
Cezar Tigaret <cezar.tigaret@gmail.com>

The original pyabf code onlt takes into account "regular" digital bit patterns
(i.e. 0 and 1) and overlooks the fact that Clampex allows one to specify a
train of digital outputs PER Epoch PER output channel (Channel#0, #1 etc)
also using a star ('*') notation, e.g.:

Digital out #3-0: 00*0 

etc...

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
TTL during a run, provided there are at least two sweeps.

(When this option if unchecked, the digital bit pattern for Channel#1 is disabled)

Also, NOTE that in reality the "principal" channel is the one where the "Digital
outputs" checkbox is checked

All these are stored in the ABF v2 file as follows:

(Dec offset: 4096)

bytes 0, 1 ⇒ Epoch num (read by pyabf)
bytes 2, 3 ⇒ 'regular' bit pattern (read by pyabf)
bytes 4, 5 ⇒ 'starred' bit pattern Channel#0 (NOT read by pyabf)
bytes 6, 7 ⇒ 'regular' bit pattern Channel#1 (alternate) (NOT read by pyabf)
bytes 8, 9 ⇒ 'starred' bit pattern Channel#1 (alternate) (NOT read by pyabf)

"""
import typing, struct
import numpy as np
import pandas as pd
import quantities as pq
import neo
import pyabf

from core import quantities as scq
from iolib import pictio as pio

from pyabf.abf1.headerV1 import HeaderV1
from pyabf.abf2.headerV2 import HeaderV2
from pyabf.abf2.section import Section
from pyabf.abfReader import AbfReader

DIGITAL_OUTPUT_COUNT = pyabf.waveform._DIGITAL_OUTPUT_COUNT # 8

def getABF(obj):
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
        
def readInt16(fb):
    bytes = fb.read(2)
    values = struct.unpack("h", bytes) # ⇐ this is a tuple! first element is what we need
    # print(f"abfReader.readInt16 bytes = {bytes}, values = {values}")
    return values[0]
    
def valToBitList(value, bitCount = DIGITAL_OUTPUT_COUNT, reverse = False):
    value = int(value)
    binString = bin(value)[2:].zfill(bitCount)
    bits = list(binString)
    bits = [int(x) for x in bits]
    if reverse:
        bits.reverse()
    return bits
        
def getDIGOutput(abf:pyabf.ABF):
    with open(abf.abfFilePath, 'rb') as fb:
        epochSection = abf._epochSection
        nEpochs = epochSection._entryCount
        epochNumbers = [None] * nEpochs
        epochDigital = [None] * nEpochs
        epochDigitalStarred = [None] * nEpochs
        epochDigitalAlt = [None] * nEpochs
        epochDigitalStarredAlt = [None] * nEpochs
        
        for i in range(nEpochs):
            fb.seek(epochSection._byteStart + i * epochSection._entrySize)
            epochNumbers[i] = readInt16(fb)
            epochDigital[i] = readInt16(fb)
            epochDigitalStarred[i] = readInt16(fb)
            epochDigitalAlt[i] = readInt16(fb)
            epochDigitalStarredAlt[i] = readInt16(fb)
            
        
        return epochNumbers, epochDigital, epochDigitalStarred, epochDigitalAlt, epochDigitalStarredAlt
        
    
    

def getABFEpochsTable(x:pyabf.ABF, sweep:typing.Optional[int]=None,
                      as_dataFrame:bool=False, allTables:bool=False):
    if not isinstance(x, pyabf.ABF):
        raise TypeError(f"Expecting a pyabf.ABF object; got {type(x).__name__} instead")
    
    
    sweepTables = list()
    if isinstance(sweep, int):
        if sweep < 0 or sweep >= x.sweepCount:
            raise ValueError(f"Invalid sweep {sweep} for {x.sweepCount} sweeps")
        
        x.setSweep(sweep)
        # NOTE: 2022-03-04 15:30:22
        # only return the epoch tables that actually contain any non-OFF epochs (filtered here)
        if allTables:
            etables = list(pyabf.waveform.EpochTable(x, c) for c in x.channelList)
        else:
            etables = list(filter(lambda e: len(e.epochs) > 0, (pyabf.waveform.EpochTable(x, c) for c in x.channelList)))
            
        if as_dataFrame:
            etables = [epochTable2DF(e, x) for e in etables]
            
        sweepTables.append(etables)
    
    else:
        for sweep in range(x.sweepCount):
            x.setSweep(sweep)
            if allTables:
                etables = list(pyabf.waveform.EpochTable(x, c) for c in x.channelList)
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
    
def getCommandWaveforms(abf: pyabf.ABF, 
                        sweep:typing.Optional[int] = None,
                        channel:typing.Optional[int] = None,
                        absoluteTime:bool=False) -> typing.List[typing.List[neo.AnalogSignal]]:
    
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
        
    if isinstance(sweep, int):
        if sweep < 0:
            raise ValueError("sweep must be >= 0")
        
        if sweep >= abf.sweepCount:
            raise ValueError(f"Invalid sweep {sweep} for {abf.sweepCount} sweeps")
        
    if isinstance(channel, int):
        if channel < 0 :
            raise ValueError("channel must be >= 0")
        
        if channel >= abf.channelCount:
            raise ValueError(f"Invalid channel {channel} for {abf.channelCount} channels")
    
    ret = []
    if not isinstance(sweep, int):
        for s in range(abf.sweepCount):
            sweepSignals = []
            if not isinstance(channel, int):
                for c in range(abf.channelCount):
                    abf.setSweep(s, c, absoluteTime)
                    sweepSignals.append(__f__(abf, c))
            else:
                    
                abf.setSweep(s, channel, absoluteTime)
                sweepSignals.append(__f__(abf, channel))
                
            ret.append(sweepSignals)
            
    else:
        sweepSignals = []
        if not isinstance(channel, int):
            for c in range(abf.channelCount):
                abf.setSweep(sweep, c, absoluteTime)
                sweepSignals.append(__f__(abf, c))
                
        else:
            abf.setSweep(sweep, channel, absoluteTime)
            sweepSignals.append(__f__(abf, channel))
            
        ret.append(sweepSignals)
        
    return ret
            
        
        
            
            
        
        
