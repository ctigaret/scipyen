"""Bridge to pyabf package

Requires pyabf.

NOTE: PyABF (https://swharden.com/pyabf/) is not currently used to load 
Axon ABF files - Scipyen uses neo package instead (https://neo.readthedocs.io/en/stable/)

This is because all electorprhyiology signals are represented in Scipyen as
objects of types defined in the neo framework. 

However, pyABF does offer functionality that neo lacks, in particular, for the
inspection of acquisition protocol data embedded in an axon file.

Such functionality comes in handy when one needs to inspect the acquisition
protocol post hoc.

To use the functions in this module you need to load the ABF file as a pyabf.ABF
object (see https://swharden.com/pyabf/tutorial/ and https://swharden.com/pyabf/)


"""
import typing
import numpy as np
import pandas as pd
import quantities as pq

from core import quantities as spq

try:
    import pyabf
    hasPyABF=True
except:
    hasPyABF = False
    
def getEpochTables(x:object, as_dataFrame:bool=False):
    if not hasPyABF:
        return

    if not isinstance(x, pyabf.ABF):
        raise TypeError(f"Expecting a pyabf.ABF object; got {type(x).__name__} instead")
    
    etable = [pyabf.waveform.EpochTable(x, c) for c in x.channelList]
    
    # NOTE: 2022-03-04 15:30:22
    # only return the epoch tables that actually contain any non-OFF epochs
    
    if as_dataFrame:
        return [epochTable2DF(e) for e in etable if len(e.epochs)]
    
    return [e for e in etable if len(e.epochs)]

def epochTable2DF(x:object, abf:typing.optional[pyabf.ABF] = None):
    """Returns a pandas.DataFrame with the data from the epoch table 'x'
    """
    if not hasPyABF:
        return
    
    if not isinstance(x, pyabf.waveform.EpochTable):
        raise TypeError(f"Expecting an EpochTable; got {type(x).__name__} instead")

    # NOTE: 2022-03-04 15:38:31
    # code below taken & adapted from pyabf.waveform.EpochTable.text
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
        #epochTypes = [''] * epochCount
        #epochLevels = [''] * epochCount
        #epochLevelsDelta = [''] * epochCount
        #durations = [''] * epochCount
        #durationsDelta = [''] * epochCount
        #durationsMs = [''] * epochCount
        #durationsDeltaMs = [''] * epochCount
        #digitalPatternLs = [''] * epochCount
        #digitalPatternHs = [''] * epochCount
        #trainPeriods = [''] * epochCount
        #pulseWidths = [''] * epochCount
        #pointsPerMsec = x.sampleRateHz*1000 # WRONG!
        
        epochData = dict()
        
        for i, epoch in enumerate(epochs):
            assert isinstance(epoch, pyabf.waveform.Epoch)
            #epochLetters[i] = epoch.epochLetter
            #epochTypes[i] = epoch.epochTypeStr
            #epochLevels[i] = "%.02f" % epoch.level
            #epochLevelsDelta[i] = "%.02f" % epoch.levelDelta
            #durations[i] = "%d" % epoch.duration
            #durationsDelta[i] = "%d" % epoch.durationDelta
            #durationsMs[i] = "%.02f" % (epoch.duration/pointsPerMsec)
            #durationsDeltaMs[i] = "%.02f" % (epoch.durationDelta/pointsPerMsec)
            #digStr = "".join(str(int(x)) for x in epoch.digitalPattern)
            #digitalPatternLs[i] = digStr[:4]
            #digitalPatternHs[i] = digStr[4:]
            #trainPeriods[i] = "%d" % epoch.pulsePeriod
            #pulseWidths[i] = "%d" % epoch.pulseWidth
            
            if isinstance(abf, pyabf.ABF):
                adcName, adcUnits = self._getAdcNameAndUnits(epoch.channel)
                dacName, dacUnits = self._getDacNameAndUnits(epoch.channel)
                
            else:
                adcName = adcUnits = dacName = dacUnits = None
                
            #level = epoch.level*

            epValues = np.array([epoch.epochTypeStr,                              
                              epoch.level, epoch.levelDelta,
                              epoch.duration, epoch.durationDelta,
                              epoch.duration/x.sampleRateHz * 1000 * pq.ms, 
                              epoch.durationDelta/x.sampleRateHz * 1000 * pq.ms,
                              epoch.digitalPattern[:4], epoch.digitalPattern[4:],
                              epoch.pulsePeriod, epoch.pulseWidth,
                              epoch.pulsePeriod/x.sampleRateHz * 1000 * pq.ms,
                              epoch.pulseWidth/x.sampleRateHz * 1000 * pq.ms], dtype=object)
            
            epochData[epoch.epochLetter] = epValues
            
        #colIndex = epochLetters
        
        return pd.DataFrame(epochData, index = rowIndex)
    
    
    
    

