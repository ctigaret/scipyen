"""Bridge to pyabf package

Requires pyabf.

NOTE: PyABF (https://swharden.com/pyabf/) is not currently used to load 
Axon ABF files - Scipyen uses neo package instead (https://neo.readthedocs.io/en/stable/)

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

from core import quantities as spq
from iolib.pictio import getABF

try:
    import pyabf
    hasPyABF = True
except:
    hasPyABF = False

# import pyabf

def getABFProtocolEpochs(obj):
    if not hasPyABF:
        warning.warn("getABF requires pyabf package")
        return
    
    abf = getABF(obj)
    
    if abf:
        return getABFEpochsTable(abf, as_dataFrame=True)
    
def getABFEpochsTable(x:object, as_dataFrame:bool=False, allTables:bool=False):
    if not isinstance(x, pyabf.ABF):
        raise TypeError(f"Expecting a pyabf.ABF object; got {type(x).__name__} instead")
    
    # NOTE: 2022-03-04 15:30:22
    # only return the epoch tables that actually contain any non-OFF epochs (filtered here)
    if allTables:
        etables = list(pyabf.waveform.EpochTable(x, c) for c in x.channelList)
    else:
        etables = list(filter(lambda e: len(e.epochs) > 0, (pyabf.waveform.EpochTable(x, c) for c in x.channelList)))
    
    
    if as_dataFrame:
        return list(epochTable2DF(e, x) for e in etables)
    
    return etables
    # return [e for e in etables if len(e.epochs)]

def epochTable2DF(x:object, abf:typing.Optional[pyabf.ABF] = None):
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
                
            dacLevel = epoch.level*spq.unit_quantity_from_name_or_symbol(dacUnits) if isinstance(dacUnits, str) and len(dacUnits.strip()) else epoch.level
            dacLevelDelta = epoch.levelDelta*spq.unit_quantity_from_name_or_symbol(dacUnits) if isinstance(dacUnits, str) and len(dacUnits.strip()) else epoch.levelDelta

            epValues = np.array([epoch.epochTypeStr,                              
                              dacLevel, dacLevelDelta,
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
    
    
    
    

