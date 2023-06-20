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


"""
import typing
import numpy as np
import pandas as pd
import quantities as pq
import neo

from core import quantities as scq
from iolib.pictio import getABF

try:
    import pyabf
    hasPyABF = True
except:
    hasPyABF = False

# import pyabf

def getABFProtocolEpochs(obj, sweep:int):
    if not hasPyABF:
        warning.warn("getABF requires pyabf package")
        return
    
    abf = getABF(obj)
    
    if abf:
        return getABFEpochsTable(abf, as_dataFrame=True)
    
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
            
        
        
            
            
        
        
