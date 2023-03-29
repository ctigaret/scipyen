# -*- coding: utf-8 -*-
"""Processing of electrophysiology signal data.
"""
#### BEGIN core python modules
import sys, traceback, inspect, numbers, typing, datetime
import warnings
import os, pickle
import collections
import itertools
import math
from copy import deepcopy
#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import pandas as pd
import quantities as pq

import matplotlib as mpl
import matplotlib.pyplot as plt

import scipy
from scipy import optimize, cluster

# NOTE: 2019-05-02 22:38:20 
# progress display in QtConsole seems broken - that is because QtConsole is NOT
# a terminal like your usual shell console
# try:
#     # NOTE: progressbar does not work on QtConsole
#     #from progressbar import ProgressBar, Percentage, Bar, ETA
#     
#     # and neither does this as it should !
#     from pyprog import ProgressBar
#     
#     
# except Exception as e:
#     ProgressBar = None

# NOTE: 2019-07-29 13:09:02 do I really need these 2 lines?
from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty

import neo

#### END 3rd party modules

#### BEGIN pict.core modules
import core.workspacefunctions as wf
import core.signalprocessing as sigp
import core.curvefitting as crvf
import core.models as models
import core.datatypes as dt
import plots.plots as plots
import core.datasignal as datasignal

from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
from core import quantities as scq
from core.quantities import units_convertible
import core.neoutils as neoutils
#import core.triggerprotocols
from core.triggerevent import (TriggerEvent, TriggerEventType)
from core.triggerprotocols import (TriggerProtocol, auto_define_trigger_events, auto_detect_trigger_protocols)
#import imaging.scandata
from imaging.scandata import ScanData

from core.prog import safeWrapper
#from core.patchneo import *

#### END pict.core modules

#### BEGIN pict.gui modules
import gui.signalviewer as sv
from gui.signalviewer import SignalCursor as SignalCursor
import gui.pictgui as pgui

#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

#### BEGIN pict.ephys modules
import ephys.ephys as ephys
#### END pict.ephys modules


@safeWrapper
def segment_Rs_Rin(segment: neo.Segment, Im: typing.Union[str, int], Vm: typing.Union[str, int, pq.Quantity, float], regions: typing.Optional[typing.Union[neo.Epoch, typing.Tuple[SignalCursor, SignalCursor, SignalCursor]]] = None, channel: typing.Optional[int] = None):
    """Calculates the series (Rs) and input (Rin) resistances in voltage-clamp.
    
    Parameters:
    ----------
    segment: neo.Segment:
    
        A recorded "sweep" containing at least one analog signal containing 
        recorded membrane current (`Im`) with membrane capacitive currents used
        for the measurement of the series and input resistances (Rs and Rin).
        
        Ideally the segment would also contain a signal containing the command
        voltage (`Vm`) for the rectangular membrane voltage waveform used to 
        generate the capacitive membrane currents recorded in `Im`.
        
    Im: int, str.
    
        When an int, this is the index of the Im signal in the 
        segment.analogsignals list.
        
        When a str, this is the name of the Im signal, which should be present
        in the segment.analogsignals list.
        
    Vm: int, str, scalar python Quantity or scalar float.
    
        When int or str: the index or name of the signal containing the command
        voltage for the Vm rectangular waveform. The signal is expected to exist
        in the segment's analogsignals list.
        
        When a scalar, it is the signed magnitude of the step membrane voltage 
        change, with units of membrane voltage (assumed to be mV)
        
    regions: neo.Epoch, tuple of three signal cursors, or None (default).
    
        Indicates which regions of the Im signal (and possibly, of the Vm
        signal) are used to calculate Rs and Rin.
        
        When a neo.Epoch: this is expected to contain three intervals
        (i.e., len(epoch) == 3 is True), with the following labels (NOTE, these
        are CASE-SENSITIVE):

             "baseline", "Rs" and "Rin".
        
        These intervals define a baseline region, a region containing the peak 
        of the outward capacitance transient curent, and a region in the
        steady-state current during the step membrane voltage change.
        
        When a tuple, it expected to have three elements, each a vertical 
        SignalCursor with names (IDs) respectively, "baseline", "Rs" and "Rin"
        (also case-sensitive).
        
        When None (default), the segment is expected to contain an epoch named
        "Rm" (for membrane resistance) with the intervals as described above.
        
        ATTENTION: The order of the epoch intervals or cursors is irrelevant: 
        the interval or cursor for the baseline, Rs and Rin are selected 
        according to their labels or cursor ID.
        
    channel: int or None (default)
    
        For multi-channel signals, the index of the signal's channel. When None
        (default) the values returned will be arrays with size equal to the 
        number of channels in the signals.
        
        WARNING: Both Im and Vm signals should have the same number of channels
        (i.e., have identical array shapes)
        
    
    """
    
    if not isinstance(segment, neo.Segment):
        raise TypeError("Expecting a neo.Segment, for 'segment'; got %s instead" % type(segment).__name__)
    
    #  determine the signals interval boundaries for baseline, Rs, and Rin
    rm_epoch = None
    
    baseline_interval = None
    irs_interval = None
    irin_interval = None
    
    if regions is None:
        if len(segment.epochs) == 0:
            raise TypeError("When no region has been specified, the segment must contain epochs")
        
        rm_epochs = [e for e in segment.epochs if e.name == "Rm"]
        
        if len(rm_epochs) == 0:
            raise TypeError("No appropriate Rm epoch found in segment")
        
        rm_epoch = rm_epochs[0]
        
    elif isinstance(regions, neo.Epoch):
        rm_epoch = regions
        
    elif isinstance(regions, (tuple, list)) and len(regions) == 3:
        if all([isinstance(r, SignalCursor) and (r.cursorType is SignalCursorTypes.vertical or r.cursorType is SignalCursorTypes.crosshair) for r in regions]):
            cIDs = [c.ID for c in regions]
            
            if any([n not in cIDs for n in ["baseline", "Rs", "Rin"]]):
                raise ValueError("Inappropriate cursor IDs")
            
            base_ndx = regions[cIDs.index("baseline")]
            irs_ndx = regions[cIDs.index("Rs")]
            irin_ndx = regions[cIDs.index("Rin")]
            
            baseline_interval = [(regions[base_ndx].x - regions[base_ndx].xwindow/2) * pq.s, 
                                 (regions[base_ndx].x + regions[base_ndx].xwindow/2) * pq.s]
        
            irs_interval = [(regions[irs_ndx].x - regions[irs_ndx].xwindow/2) * pq.s, 
                            (regions[irs_ndx].x + regions[irs_ndx].xwindow/2) * pq.s]
        
            irin_interval = [(regions[irin_ndx].x - regions[irin_ndx].xwindow/2) * pq.s, 
                             (regions[irin_ndx].x + regions[irin_ndx].xwindow/2) * pq.s]
            
        else:
            raise TypeError("'regions' tuple must contain vertical SignalCursors")
        
    else:
        raise TypeError("Inappropriate type for 'regions' parameter: %s" % type(region).__name__)
    
    if isinstance(rm_epoch, neo.Epoch):
        if len(rm_epoch) != 3:
            raise TypeError("Rm epoch must have three intervals; got %s instead" % len(rm_epoch))
        
        region_labels = list(rm_epoch.labels)
        
        if len(region_labels) == 0 or not all([s in region_labels for s in ["baseline", "Rs", "Rin"]]):
            raise ValueError(f"Cannot use epoch {rm_epoch.name} with inappropriate interval labels {region_labels}")
        
        base_ndx = region_labels.index("baseline")
        irs_ndx = region_labels.index("Rs")
        irin_ndx = region_labels.index("Rin")
        
        baseline_interval = [rm_epoch.times[base_ndx],
                             rm_epoch.times[base_ndx] + rm_epoch.durations[base_ndx]]
        
        irs_interval = [rm_epoch.times[irs_ndx],
                        rm_epoch.times[irs_ndx] + rm_epoch.durations[irs_ndx]]
        
        irin_interval = [rm_epoch.times[irin_ndx],
                         rm_epoch.times[irin_ndx] + rm_epoch.durations[irin_ndx]]
        
    if any([i is None for i in [baseline_interval, irs_interval, irin_interval]]):
        raise RuntimeError("Cannot determine signal interval boundaries")
        
    if isinstance(Im, str):
        Im = neoutils.get_index_of_named_signal(segment, Im)
        
    elif not isinstance(Im, int):
        raise TypeError("Im expected to be a str or int; got %s instead" % type(Im).__name__)
    
    Im_signal = segment.analogsignals[Im]
    
    if isinstance(Vm, pq.Quantity):
        if not units_convertible(Vm, pq.V):
            raise TypeError("Wrong units for Vm quantity: %s" % Vm.units)
        
        if Vm.size != 1:
            raise TypeError("Vm must be a scalar")
        
        vstep = Vm
        
        if vstep.ndim == 0:
            vstep = vstep.flatten()
    
    elif isinstance(Vm, float):
        vstep = (Vm * pq.mV).flatten()
        
    else:
        # get the vm signal and measure vstep based on the specified regions:
        # use Irin region and Ibase region to determine the amplitude of vstep.
        if isinstance(Vm, str):
            Vm = neoutils.get_index_of_named_signal(segment, Vm)
        
        elif not isinstance(Vm, int):
            raise TypeError("Vm expected to be a str or int; got %s instead" % type(Vm).__name__)
        
        Vm_signal = segment.analogsignals[Vm]
        
        vrin = Vm_signal.time_slice(irin_interval[0], irin_interval[1]).mean(axis=0)
        vbase= Vm_signal.time_slice(baseline_interval[0], baseline_interval[1]).mean(axis=0)
        
        vstep = vrin - vbase
                
        if isinstance(channel, int):
            vstep = vstep[channel].flatten()
            
    Ibase = Im_signal.time_slice(baseline_interval[0], baseline_interval[1]).mean(axis=0)
    
    # Irs = Im_signal.time_slice(irs_interval[0], irs_interval[1]).mean(axis=0)
    Irs = Im_signal.time_slice(irs_interval[0], irs_interval[1]).max(axis=0)
    
    Irin = Im_signal.time_slice(irin_interval[0], irin_interval[1]).mean(axis=0)
    
    if isinstance(channel, int):
        Ibase = Ibase[channel].flatten()
        Irs = Irs[channel].flatten()
        Irin = Irin[channel].flatten()
        
    Rin = vstep / (Irin - Ibase)
    
    Rs = vstep / (Irs - Ibase)
    
    return (np.array([Rs, Rin]) * Rin.units).rescale(pq.MOhm)

@safeWrapper
def block_Rs_Rin(data:typing.Union[neo.Block,typing.Sequence[neo.Segment]], Im:typing.Union[str, int], Vm:typing.Union[str, int, pq.Quantity, float], regions:typing.Optional[typing.Union[neo.Epoch, typing.Tuple[SignalCursor, SignalCursor, SignalCursor]]] = None, channel: typing.Optional[int] = None, name:typing.Optional[str] = None):
    """Calls segment_Rs_Rin for all segments in data.
    
    Parameters:
    ===========
    data: neo.Block or a sequence (tuple, list) of neo.Segments
    
    Im, Vm, regions, channel - same as for segment_Rs_Rin()
    
    name: str or None (default) - the name prefix of the resulting signals (see
        below)
    
        When None or an empty str, the name will be the name of the block else
        the string "data".
    
    ATTENTION: See the requirement for `regions` in the help for segment_Rs_Rin.
    
    When `regions` is None (the default) each segment in the data is expected to 
    contain an Epoch named "Rm" with three intervals labelled "baseline", "Rs",
    and "Rin". Since each segment MAY have a different start time, the Epochs 
    should be distinct in each segment.
    
    Returns:
    ========
    
    Two neo.IrregularlySampledSignal objects with the time-course of the series
    resistance (Rs) and input resistance (Rin)
    
    """
    if isinstance(data, neo.Block):
        segments = data.segments
        
    elif isinstance(data, (tuple, list) and all(isinstance(d, neo.Segment) for d in data)):
        segments = data
    else:
        raise TypeError(f"Expecting a neo.Block, or a sequence of neo.Segments; got {type(data).__name__} instead")
    
    trsrin = [(s.t_start, segment_Rs_Rin(s, Im=Im, Vm=Vm, regions=regions, channel=channel)) for s in segments]
    
    times, rsrin = zip(*trsrin) # split into a times and a RsRin tuple
    
    t_vec = np.array(times) * times[0].units
    rarray = np.concatenate(rsrin, axis=1) * rsrin[0].units
    
    if not isinstance(name, str) or len(name.strip())==0:
        name = data.name if isinstance(data, neo.Block) and len(data.name.strip()) else "data"
        
    Rs  = neo.IrregularlySampledSignal(times=t_vec, signal = rarray[0,:], units = rarray.units, time_units = t_vec.units, name=f"{name}_Rs")
    Rin = neo.IrregularlySampledSignal(times=t_vec, signal = rarray[1,:], units = rarray.units, time_units = t_vec.units, name=f"{name}_Rin")
    
    return Rs, Rin
    
@safeWrapper
def cursors_Rs_Rin(signal: typing.Union[neo.AnalogSignal, DataSignal], baseline: typing.Union[SignalCursor, tuple], rs: typing.Union[SignalCursor, tuple], rin: typing.Union[SignalCursor, tuple], vstep: typing.Union[float, pq.Quantity], channel: typing.Optional[int] = None):
    """Calculates series and input resistance from voltage-clamp recording.
    
    Applies to voltage-clamp recordings (membrane current signal)
    
    Parameters:
    ----------
    
    signal: neo.AnalogSignal or DataSignal = the recorded membrane current
    
    baseline: signalviewer.SignalCursor of type "vertical", or tuple (t, w), 
        representing a notional vertical signal cursors with window "w" 
        centered at "t". "t" and "w" must be floats or python Quantity objects 
        with the same units as the signal's domain.
        
        Defines the baseline region of the signal, against which Rs and Rin will
        be calculated. The baseline value is calculated as the average of the 
        signal samples across the cursor's window.
        
        
    rs, rin: signalviewer.SignalCursor of type "vertical" or tuple (see the 
        "baseline" parameter, above).
        Set the signal region where Rs and Rin, respectively, will be calculated.
        
    vstep: float or python Quantity: the size of the membrane depolarization 
        step.
        
        When a Quantity it must be in units convertible to mV.
        
    channel: int or None (default)
    
        For multi-channel signals, the index of the signal's channel. When None
        (default) the values returned will be arrays with size equal to the 
        number of channels in the signals.
        
    Returns:
    -------
    
    (Rs, Rin): tuple of python Quantity objects in vstep.units / signal.units
    
    """
    if isinstance(vstep, float):
        vstep *= pq.mV
        
    elif isinstance(vstep, pq.Quantity):
        if not units_convertible(vstep, pq.mV):
            raise TypeError("Wrong units for vstep quantity (%s)" % vstep.units)
        
    else:
        raise TypeError("vstep expected to be a float or a python Quantity; got %s instead" % type(vstep).__name__)
    
    Ibase   = ephys.cursor_average(signal, baseline, channel=channel)
    IRs     = ephys.cursor_max(signal, rs, channel=channel)
    IRin    = ephys.cursor_average(signal, rin, channel=channel)
    
    Rs  = vstep / (IRs  - Ibase)
    Rin = vstep / (IRin - Ibase)
    
    return np.array([Rs, Rin]) * Rin.units

@safeWrapper
def epoch_Rs_Rin(signal: typing.Union[neo.AnalogSignal, DataSignal], epoch: typing.Union[neo.Epoch, tuple], vstep: typing.Union[float, pq.Quantity], channel: typing.Optional[int] = None):
    """Calculates series and input resistance based on epochs.
    
    The baseline, Rs and Rin are calculated across the time intervals defined in
    the Epoch, which is expected to contain three intervals each with its own
    time and duration (see neo.Epoch for details about Epoch objects)
    
    Parameters:
    -----------
    signal: neo.AnalogSignal or DataSignal
    
    epoch: neo.Epoch with three time intervals with the following roles:
        1) baseline → the baseline current BEFORE the depolarizing test voltage
    
        2) Rs       → contains the peak of the first capacitive transient 
                        (at start of depolarizing test)
    
        3) Rin      → contains a region of the steady-state current during the 
                        depolarizing text voltage, AND just before the repolarizing
                        capacitive transient
    
    vstep: scalar float or Quantity in mV, the size (amplitude) of the depolarizing
            test voltage
    
    channel: int or None (default). When given, it is the index of the signal
        channel (for multi-channel signals).
    
        NOTE: AnalogSignal objects typically have just ONE channel (i.e., they 
                are numpy array-like with shape (n,1) where n is the number of 
                samples). Therefore, passing the default value for `channel`
                (None) will result in just two scalars (Rs and Rin).
    
                If the signal has more than one channel, then passing the default
                `channel` will result in two arrays (Rs and Rin) with as many
                elements as channels.
    
    """
    if not isinstance(signal, (neo.AnalogSignal, DataSignal)):
        raise TypeError("signal expected to be a neo.AnalogSignal or DataSignal; got %s instead" % type(signal).__name__)
    
    if not isinstance(epoch, neo.Epoch):
        raise TypeError("epoch expected to be a neo.Epoch; got %s instead" % type(epoch).__name__)
    
    if len(epoch) != 3:
        raise TypeError("epoch must have three intervals; got %d instead" % len(epoch))
    
    if isinstance(vstep, float):
        vstep *= pq.mV
        
    Ibase = signal.time_slice(epoch[0].times, epoch[0].times + epoch[0].durations).mean(axis=0)
    IRs   = signal.time_slice(epoch[1].times, epoch[1].times + epoch[1].durations).max(axis=0)
    IRin  = signal.time_slice(epoch[2].times, epoch[2].times + epoch[2].durations).mean(axis=0)
    
    Rs  = vstep / (IRs  - Ibase)
    Rin = vstep / (IRin - Ibase)
    
    if channel is not None:
        Rs = Rs[channel].flatten()
        Rin = Rin[channel].flatten()
    
    return np.array([Rs, Rin]) * Rin.units
    

@safeWrapper
def v_Nernst(x_out, x_in, z, temp):
    """Calculates Nernst potential for an ionic species X.
    
    Calculates Nernst potential for an ionic species X, given its concentrations
    x_out and x_in (in M / L), valence, and temperature (in degress centigrade).
    """
    from scipy import constants
    
    T = constants.convert_temperature(temp, "Celsius", "Kelvin")
    F = constants.physical_constants["Faraday constant"][0]
    
    return constants.R * T * np.log(x_out/x_in) / (z * F)
    

def __wave_interp_root_near_val__(w, value):
    """Factored-out code in the for loop under NOTE:2017-09-04 22:09:38
    """
    # 1) get the waveform region where waveform >= value
    index_ge_value = w >= value
    
    # 2) find the boundaries of this region
    # NOTE: cannot use boolean indexing on AnalogSignal objects, but we can
    # on their magnitude!
    index_ge_diff = np.ediff1d(np.asfarray(index_ge_value), to_begin = 0)
    
    # if waveform >= value in more than one region this will have as many
    # indices as there are regions
    # might be empty if waveform is riding on a decreasing baseline
    ge_starts = np.where(index_ge_diff == 1)[0]  
    
    # ditto; 
    # might be empty if the waveform is riding on a rising baseline
    ge_stops = np.where(index_ge_diff   == -1)[0]
    
    if len(ge_starts) == 0:
        return np.nan, np.nan, np.nan, np.nan # nothing was found; nan is more meaningful
        #return None, None, None, None # nothing was found
    
    # the earliest positive crossing in index_ge_diff is the first sample 
    # index with sample >= value
    # on a "conforming" AP waveform this is on the rising phase
    first_ge_index = int(ge_starts[0])
    
    if len(ge_stops) == 0: # rising baseline !
        samples_ge_value = w.magnitude[index_ge_value]
        
    else:
        # the earliest negative crossing in index_ge_diff is one-past the
        # last sample index in the first region with samples >= value
        # index 
        
        last_ge_index = int(ge_stops[0]) 
        
        # we need to keep those samples >= value only for the FIRST occurence
        # of segments that satisfy this condition
        index_ge_value_corrected = np.full_like(index_ge_value, False)
        
        index_ge_value_corrected[ge_starts[0]:ge_stops[0]] = True
        
        index_ge_value = index_ge_value_corrected
        
    samples_ge_value = w.magnitude[index_ge_value]
    
    times_ge_value = w.times[index_ge_value.flatten()]
    
    # NOTE: 2019-04-29 12:16:34
    # 2) now do a linear interpolation between this sample (see NOTE: 2019-04-29 12:15:23)
    # and the previous one -- unles the first waveform sample is already >= value
    # in which case interpolate between first & second samples with all the risk
    # this entails, see NOTE: 2019-04-29 12:20:48
    
    rise_y1 = samples_ge_value[0]   # first sample value in the region >= value
    rise_x1 = times_ge_value[0]     # time point of the above
    
    rise_x1_index = w.time_index(rise_x1)
    
    rise_x1 = rise_x1.magnitude
    
    if rise_x1_index > 0:
        rise_y0 = w.magnitude[rise_x1_index - 1]
        rise_x0 = w.times.magnitude[rise_x1_index - 1]
        
    else:
        # NOTE: 2019-04-29 12:20:48
        # this shouldn't happen, but it might for crazy recordings
        # so we just do this to avoid raising exceptions, but the calculated
        # values are almost certainly garbage
        rise_y0 = w.magnitude[0]
        rise_x0 = w.times.magnitude[0]
        
        rise_y1 = w.magnitude[1]
        rise_x0 = w.times.magnitude[1]
        
    rise_slope = (rise_y1 - rise_y0) / (rise_x1 - rise_x0)
    
    time_at_value_rise = (value.magnitude - rise_y0) / rise_slope + rise_x0
    
    if len(ge_stops):
        decay_y0 = samples_ge_value[-1] # last sample value in the region >= value
        decay_x0 = times_ge_value[-1]   # the time point of the above
        
        decay_x0_index = w.time_index(decay_x0)
        
        decay_x0 = decay_x0.magnitude
        
        if decay_x0_index < len(w)-1:
            decay_y1 = w.magnitude[decay_x0_index + 1]
            decay_x1 = w.times.magnitude[decay_x0_index + 1]
        
        else: # this shouldn't happen, but it might for crazy recordings
            # so we just do this to avoid raiing exceptions, but the calculated
            # values are garbage
            decay_y0 = w.magnitude[-2]
            decay_x0 = w.times.magnitude[-2]
            decay_y1 = w.magnitude[-1]
            decay_x1 = w.times.magnitude[-1]
            
        decay_slope = (decay_y1 - decay_y0) / (decay_x1 - decay_x0)
        
        time_at_value_decay = (value.magnitude - decay_y0) / decay_slope + decay_x0
        
    else:
        decay_slope = np.nan
        time_at_value_decay = np.nan
        
    # NOTE: 2019-04-29 12:21:37
    # an alternative way is to do a PCHIP interpolation but this would require
    # a pre-determined end time point; it the latter is too large (i.e. too 
    # late in the waveform) the result is unstable; on the other hand, PCHIP
    # inteprolation on two adjacent samples is just overkill.
    
    return time_at_value_rise, time_at_value_decay, rise_slope, decay_slope

    
def fit_Frank_Fuortes(lat, I, fitrheo=False, xstart = 0, xend = 0.1, npts = 100):
    """Fits the Frank & Fuortes 1956 model through stimulus vs latency curve.
    
    Used for the determination of rheobase from series of depolarising current
    injections of increasing magnitude.
    
    See rheobase_latency for details.
    
    Parameters:
    -----------
    
    lat = data vector (1D numpy array) with latencies
    I   = data vector (1D numpy array) with injected current, each corresponding
            to its latency in the lat vector
    
    Keyword parameters:
    -------------------
    fitrheo: bool; default is False
        When False, membrane time constant tau is determined by fitting the data 
            with the models.Frank_Fuortes() equation
            
        When True, both rheobase current Irheo and the membrane time constant tau
            are determined by fitting the data with the models.Frank_Fuortes2() equation.
    
    xstart: float scalar or None
        Start of the the time domain of the fitted function, in s
        
        Default is 0
        
    xend: float scalar or None
        End value for the time domain of the fitted function, in s
        
        Default is 0.1
        
    npts: int, default is 100
        Number of points in the fitted function
    
    Returns:
    =======
    Irh  = apparent rheobase
    fit_tau = membrane time constans (fitted)
    fit_rheobase = fitted rheobase
    popt = fitted parameters for the Frank & Fuortes equation
    rsq  = coefficient of determination of the fit
    sst  = total sum of squares
    sse  = sum of square residuals
    pcov = covariance matrix in the fitted parameters
    perr = standard deviations for the fitted parameter values
    ii   = the actual dependent variable see NOTE (1)
    xx   = time domain of the fitted function
    yy   = the dependent variable of the fitted function
    
    NOTE (1):
        The original equation (1) is used for the determination of the 
        membrane time-constant from strength-latency relationship.
        
        Irh/I = 1 - exp(-t/tau)                                         (1)
        
            where Irh (rheobase curent) is measured experimentally as the 
            smallest I value where AP are fired.
            
        In practice, the following equation is used:
        
        Irh/I = 1 - exp(-(t-t0)/tau)                                    (2)
            
            where t0 is a small "delay" i.e., the smallest latency used in the 
            experiment.
            
            This helps the fit as latency approaches 0.
            
        By re-arranging equation (1), one can also use Irh as a free parameter
        (hence one can also get a fitted value for Irh):
        
        1/I = (1-exp(-t/tau)) / Irh                                     (3)
        
        When "fitrheo" is False, the function uses equation (2) and the fitted
        dependent variable is yy = I/Irh. 
            
            The fitted curve that is plotted is 
        
            I/Irh = f(latency)
        
        When "fitrheo" is True, the function uses equation (3) and the fitted
        dependent variable is 1/I. 
            For convenience, the function returns yy = I so that it can be
            directly plotted:
        
            I = 1/f(latency)
        
    """
    lat_ok = np.where(np.isfinite(lat))[0]
    
    delay = np.nanmin(lat)
    
    #print("delay", delay)
    
    # experimentally - determined rheobase current: the value of I where
    # at least one AP was detected (first "latency")
    # this assumes that latences are given in increasing order of the injected
    # current, which may NOT be the case!
    
    # first work on valid data i.e. those currents where latencies are numbers,
    # not nans
    # 
    ii = I[lat_ok]
    ltcy = lat[lat_ok]
    
    if len(ii) == 0:
        return
    
    # make sure injected currents are in ascnding order
    i_sort = np.argsort(ii) # get an indexing vector for sorting
    
    ii = ii[i_sort].flatten() # sorted currents
    
    ltcy = ltcy[i_sort].flatten() # latencies sorted by currents in ascending order

    #print("fit_Frank_Fuortes ii", ii)
    
    #Irh = I[lat_ok[0]]
    Irh = ii[0] # experimental rheobase current: the smallest injected current with
                # a finite latency

    decay = 0.1 # blue-sky initial guess
    
    if xstart is not None and xend is not None and npts is not None:
        xx = np.linspace(xstart, xend, npts)
    
    else:
        xx = None
    
    yy = None
    
    if fitrheo:
        ii = 1/ii
        i_ret = 1/I
        #ii = 1/I
        
        popt, pcov = optimize.curve_fit(models.Frank_Fuortes2,
                                        ltcy, 
                                        ii,
                                        [Irh, decay, delay])
        
        #popt, pcov = optimize.curve_fit(models.Frank_Fuortes2,
                                        #lat[lat_ok], 
                                        #ii[lat_ok],
                                        #[Irh, decay, delay])
        
        yfit = models.Frank_Fuortes2(ltcy, *popt)
        #yfit = models.Frank_Fuortes2(lat[lat_ok], *popt)
        #yfit = _Frank_Fuortes2(lat[lat_ok], *popt)
        
        
        if xx is not None:
            yy = 1 / models.Frank_Fuortes2(xx, *popt)
            #yy = 1 / _Frank_Fuortes2(xx, *popt)
        
        fit_rheobase = popt[0]
        
        fit_tau = popt[1]
        #print("fit_tau model 2", fit_tau)
        
    else:
        ii = Irh/ii
        i_ret = Irh/I
        #ii = Irh/I
        
        popt, pcov = optimize.curve_fit(models.Frank_Fuortes,
                                        ltcy,
                                        ii,
                                        [decay, delay])
        
        #popt, pcov = optimize.curve_fit(models.Frank_Fuortes,
                                        #lat[lat_ok],
                                        #ii[lat_ok],
                                        #[decay, delay])
        
        yfit = models.Frank_Fuortes(lat[lat_ok], *popt)
        #yfit = _Frank_Fuortes(lat[lat_ok], *popt)
    
        if xx is not None:
            yy = 1 / models.Frank_Fuortes(xx, *popt)
            #yy = 1 / _Frank_Fuortes(xx, *popt)
        
        fit_tau = popt[0]
        #print("fit_tau model 1", fit_tau)
        
        fit_rheobase = Irh
    
    sst = np.sum((ii - ii.mean()) ** 2.)# total sum of squares
    #sst = np.sum((ii[lat_ok] - ii[lat_ok].mean()) ** 2.)# total sum of squares

    sse = np.sum((yfit - ii) ** 2.) # sum of squared residuals
    #sse = np.sum((yfit - ii[lat_ok]) ** 2.) # sum of squared residuals

    rsq = 1 - sse/sst # coeff of determination

    perr = np.sqrt(np.diag(pcov))
    
    return Irh, fit_tau, fit_rheobase, popt, rsq, sst, sse, pcov, perr, i_ret, xx, yy

   
def rheobase_latency(*args, **kwargs):
    """ Frank & Fuortes (1956) Strength-latency analysis.
    
        Calculates rheobase and membrane time constant by fitting on
        1st AP latency vs injected current data.
        
        Always works on the first detected AP in the train!

        References:
        
        Frank & Fuortes (1956) Stimulation of spinal motoneurones with 
        intracellular electrodes. J.Physiol. 134, 451-470
        
        Spencer & Kandel (1961) Electrophysiology of hippocampal neurons:
        III. Firing level and time constant. J. Neurophysiol. 24(3), 260-271
    
    Parameters:
    -----------
    
    args: comma-separated sequence of python dictionaries as returned by 
        analyse_AP_step_injection_series() function, each containing the 
        following mandatory items:
        
        "Injected_current" : a list with the values of injected current
        
        "First_AP_latency" : a list with the latencies to the first AP
        
    Var-positional parameters:
    -------------------------
    plot: boolean, default False:
        When True, plots the fitted curve
        
    minsteps: int (default3) minimum number or current injection steps to use
        
    The following are passed directly to fit_Frank_Fuortes() function:
    
    fitrheo: boolean optional (default False); if True, the rheobase current is
        also fitted (see NOTE (1))
        
    xstart, xend: float or Quantity scalars corresponding to the start and end 
            of the time domain for the fitted I/Irheo  = f(latency) curve 
            (units are the latency time units)
            
            When float numbers, they are interpreted to be in s
            
            optional; defaults are 0. and 0.1
            
    npts: integer scalar: number of points in the generated fitted curve
            optional, default is 100
            
    
    when either xstart, xend or npoints are None or [], no fitted curve will be generated
    
    otherwise, the fitted curve and the original data will be plotted
    
    Returns:
    =======
    
    A dictionary with the following fields:
    
        Irh : experimentally determined rheobase current
        
        tau : fitted membrane time constant
        
        fit: a dictionary with the following fields:
        
            Irh: fitted rheobase current if fitrheo is True, or the same value 
                as Irheo, otherwise
                
            parameters : an iterable (list) with the fitted parameters as follows:
            
                if fitrheo is True:
                    [fitted_rheobase_current, membrane_time_constant, fitted_delay]
                    
                else:
                
                    [membrane_time_constant, fitted_delay], 
                    
                where "fitted_delay" is the latency asymptote ( ~ 0)
            
            rsq : coefficient of determination of the fit
            
            sse : sum of squared errors
            
            perr: a list with as many elements as popt, containing the 
                    standard deviations in the fitted parameter values
        
            x,
            
            y
                the fitted curve in the interval 0 .. 0.1 s at 50 points
                (see NOTE (2))
        
    NOTE (1):
        The original equation (1) is used for the determination of the 
        membrane time-constant from strength-latency relationship.
        
        Irh/I = 1 - exp(-t/tau)                                         (1)
        
            where Irh (rheobase curent) is measured experimentally as the 
            smallest I value where AP are fired.
            
        In practice, the following equation is used:
        
        Irh/I = 1 - exp(-(t-t0)/tau)                                    (2)
            
            where t0 is a small "delay" i.e., the smallest latency used in the 
            experiment.
            
            This helps the fit as latency approaches 0.
            
        By re-arranging equation (1), one can also use Irh as a free parameter
        (hence one can also get a fitted value for Irh):
        
        1/I = (1-exp(-t/tau)) / Irh                                     (3)
        
        When "fitrheo" is False, the function uses equation (2) and the
        dependent variable in the fit is Irh/I. 
            
            The fitted curve that is plotted is Irh/I vs latency
        
        When "fitrheo" is True, the function uses equation (3) and the
        dependent variable in the fit is 1/I. 
            For convenience, the function returns its inverse (I) so that it can 
            be directly plotted:
        
            I = 1/f(latency)
        
    """
    if len(args) == 0:
        raise RuntimeError("Expecting some data")
    
    if not all([isinstance(a, dict) and "Injected_current" in a.keys() and "First_AP_latency" in a.keys() for a in args]):
        raise TypeError("All arguments must be dictionaries containing the following fields: 'Injected_current' and 'First_AP_latency'")
    
    #plot = kwargs.pop("plot", False)
    
    minsteps = kwargs.pop("minsteps", 3)
    
    if not isinstance(minsteps, int):
        raise TypeError("minsteps expected to be an int; got %s instead" % type(minsteps).__name__)

    if minsteps < 1:
        raise ValueError("minsteps must be > 0; got %s instead" % minsteps)
    
    fitrheo = kwargs.get("fitrheo", False)
    
    if len(args) > 1:
        n_steps = min([len(d["Injected_current"]) for d in args])
        
        if n_steps < minsteps:
            warnings.warn("A minimum of %d are required for rheobase - latency analysis; currently there are only %d steps as minimum" % (minsteps, n_steps))
            return None
            
        Iinj = np.concatenate([d["Injected_current"].magnitude[:n_steps] for d in args], axis=1) * args[0]["Injected_current"].units
        
        latencies = np.concatenate([d["First_AP_latency"].magnitude[:n_steps] for d in args], axis=1) * args[0]["First_AP_latency"].units
    
        Iinj_mean = Iinj.mean(axis=1)
        
        latencies_mean = np.nanmean(latencies, axis=1)
        
    else:
        Iinj_mean = args[0]["Injected_current"].flatten()
        latencies_mean = args[0]["First_AP_latency"].flatten()
        
        n_steps = len(args[0]["Injected_current"])
        
        if n_steps < minsteps:
            warnings.warn("A minimum of three steps are required for rheobase - latency analysis; currently there are only %d minimum steps" % n_steps)
            return None
        
    xstart = kwargs.get("xstart", 0)
    
    if isinstance(xstart, pq.Quantity):
        if not units_convertible(xstart, latencies_mean.units):
            raise TypeError("'xstart' expected to have %s units; instead it has %s" % (latencies_mean.units, xstart.units))
        
        if xstart.units != pq.s:
            xstart = xstart.rescale(pq.s)
            
    elif isinstance(xstart, numbers.Real):
        xstart *= pq.s
        
    elif xstart is not None:
        raise TypeError("'xstart' expected to be a float scalar, a Quantity, or None; got %s instead" % type(xstart).__name__)
    
    xend = kwargs.get("xend", 0)
    
    if isinstance(xend, pq.Quantity):
        if not units_convertible(xstart, latencies_mean.units):
            raise TypeError("'xend' expected to have %s units; instead it has %s" % (latencies_mean.units, xend.units))
        
        if xend.units != pq.s:
            xend = xend.rescale(pq.s)
            
    elif isinstance(xend, numbers.Real):
        xend *= pq.s
        
    elif xend is not None:
        raise TypeError("'xend' expected to be a float scalar, a Quantity, or None; got %s instead" % type(xend).__name__)
    
    kwargs["xstart"] = xstart.magnitude
    kwargs["xend"] = xend.magnitude
    
    irheo, fit_tau, fit_rheobase, popt, rsq, sst, sse, pcov, perr, ii, xx, yy = \
        fit_Frank_Fuortes(latencies_mean.magnitude, Iinj_mean.magnitude, **kwargs)
    
    if xx is not None and yy is not None:
        if latencies_mean.units != pq.s:
            # xx is in seconds
            time_scale = float((1*pq.s).rescale(latencies_mean.units).magnitude)
            xx *= time_scale
            
    ret = collections.OrderedDict()
    
    ret["Name"] = "rheobase_latency_analysis"
    
    ret["I"]   = IrregularlySampledDataSignal(signal = Iinj_mean,
                                                 domain = [k for k in range(len(args[0]["Injected_current"]))],
                                                 units = Iinj_mean.units,
                                                 domain_units = pq.dimensionless)
    
    ret["Latency"] = IrregularlySampledDataSignal(signal = latencies_mean,
                                                     domain = [k for k in range(len(args[0]["Injected_current"]))],
                                                     units = latencies_mean.units,
                                                     domain_units = pq.dimensionless)

    #ret["I"]   = neo.IrregularlySampledSignal(signal = Iinj_mean,
                                              #times = args[0]["Injected_current"].times,
                                              #units = Iinj_mean.units,
                                              #time_units = args[0]["Injected_current"].times.units)
    
    #ret["Latency"] = neo.IrregularlySampledSignal(signal = latencies_mean,
                                                  #times = args[0]["Injected_current"].times,
                                                  #units = latencies_mean.units,
                                                  #time_units = args[0]["Injected_current"].times.units)

    ret["Irh"] = np.array([irheo]) * Iinj_mean.units
    ret["tau"] = np.array([fit_tau]) * pq.s
    
    ret["fit"] = collections.OrderedDict()
    
    ret["fit"]["Irh"] = np.array([fit_rheobase]) * Iinj_mean.units
    ret["fit"]["parameters"] = popt
    ret["fit"]["R2"] = rsq
    ret["fit"]["sse"] = sse
    ret["fit"]["perr"] = perr
    ret["fit"]["x"] = xx
    ret["fit"]["y"] = yy
    ret["fitrheo"] = fitrheo
    
    return ret

def extract_Vm_Im(data, VmSignal="Vm_prim_1", ImSignal="Im_sec_1", t0=None, t1=None):
    """Convenient function to extract Vm and Im signals as a block.
    
    Extract Vm and Im signals from a neo.Block containing current injection
    step experiments (current clamp) recorded in Clampex.
    
    The signals are returned as a block where each Segment contains only the 
    Vm and Im analog signals.
    
    WARNING: Do NOT use for recordings that do not contain a useful injected 
    current signal - either because it was not recorded or because the telegraph
    and/or scaling information was messed up during the recording!.
    In such cases, use neoutils.getABFProtocolEpochs to manually extract the 
    parameters of the current injection steps i.e. Iinj_0, delta_I, Istart and 
    Istop and pass those to analyse_AP_step_injection_series()
    
    Parameters:
    ------------
    
    data: neo.Block, sequence of neo.Segment or a neo.Segment
    
    Named parameters:
    -----------------
    
    VmSignal: integer index, or str (signal name) of the Vm analog signal
        Default is "Vm_prim_1"
        
    ImSignal: integer index, or str (signal name) of the Im analog signal.
        Default is "Im_sec_1"
        
    t0: None (default) or:
        * a float scalar (time, assumed to be given in seconds)
        * a Quantity scalar (time units)
        * a numpy array with one or two elements (start and possibly stop time, 
                                                  assumed to be given in seconds)
                                                  
        * a Quantity array (time units) with two elements
        * a neo.Epoch
        * a sequence of two float scalars or Quantity with time units
        
    t1: None (default) or
        * a float scalar (time, assumed to be given in seconds)
        * a Quantity (time units)
        
        Must be specified with t0 is a float or Quantity
        
    NOTE: t0 (possibly together with t1) specify the start and stop times for an
            optional time interval or "time slice" of the signals in data, 
            in case that only a time "slice" of the signals is to be extracted
    
        t1 MUST be specified when t0 contains a single time point (float scalar, 
            or Quantity scalar)
            
        By default, the full extent (length) of the signals is extracted.
        
    NOTE: when a time slice is specified, the start and stop times must be relative
        to the start time of the signals
        
    """
    from core import utilities
    
    t_start = None
    t_stop  = None
    
    if isinstance(t0, numbers.Real):
        t_start = t0 * pq.s
        
    elif isinstance(t0, neo.Epoch):
        t_start = t0.times[0]
        t_stop = t_start = t0.durations[0]
        
    elif isinstance(t0, pq.Quantity):
        if not units_convertible(t0, pq.s):
            raise TypeError("'t0' expected to have time units; got %s instead" % t0.units)
        
        if t0.size == 1:
            t_start = t0
            
        elif t0_size == 2:
            t_start = t0[0]
            t_stop  = t0[1]
            
        else:
            raise ValueError("'t0' expected to have one or two elements; got %d instead" % t0.size)
        
    elif isinstance(t0, np.ndarray):
        if t0.size == 1:
            t_start = t0*pq.s
            
        elif t0.size == 2:
            t_start = t0[0]*pq.s
            t_stop = t0[1]*pq.s
            
        else:
            raise ValueError("'t0' expected to have one or two elements; got %d instead" % t0.size)
        
    else:
        raise TypeError("'t0' has unexpected type: %s" % type(t0).__name__)
    
    if t_stop is None:
        if t1 is None:
            raise TypeError("'t1' must be specified")
        
        elif isinstance(t1, numbers.Real):
            t_stop = t1*pq.s
            
        elif isinstance(t1, pq.Quantity):
            if not units_convertible(t1, pq.s):
                raise TypeError("'t1' expected to have time units; got %s instead" % t1.units)
            
            if t1.size !=1:
                raise ValueError("'t1' expected to be a scalar Quantity")
            
            t_stop = t1
        
        else:
            raise TypeError("'t1' has unexpected type: %s" % type(t1).__name__)
        
        
    if not isinstance(VmSignal, (int, str)):
        raise TypeError("'VmSignal' expected to be an int or str; got %s instead" % type(VmSignal).__name__)
    
    if not isinstance(ImSignal, (int, str)):
        raise TypeError("'ImSignal' expected to be an int or str; got %s instead" % type(ImSignal).__name__)
    

    data = neoutils.set_relative_time_start(data)
    
    if t_start is not None and t_stop is not None:
        data = neoutils.get_time_slice(data, t0=t_start, t1=t_stop)
        
    if isinstance(data, neo.Block):
        segments = data.segments
        
    elif isinstance(data, (tuple, list)) and all([isinstance(x, neo.Segment) for x in data]):
        segments = data
        
    elif isinstance(data, neo.Segment):
        segments = [data]
        
    else:
        raise TypeError("'data' expected to be a neo.Block, neo.Segment, or a sequence of neo.Segment; got %s instead" % type(data).__name__)
    
    if isinstance(VmSignal, str):
        vmsignalindex = utilities.unique(neoutils.get_index_of_named_signal(data, VmSignal))[0]
        
    elif isinstance(VmSignal, int):
        vmsignalindex = VmSignal
        
    else:
        raise TypeError("'VmSignal' expected to be a str or an int; got %s instead" % type(VmSignal).__name__)
    
    if isinstance(ImSignal, str):
        imsignalindex = utilities.unique(neoutils.get_index_of_named_signal(data, ImSignal))[0]
        
    elif isinstance(ImSignal, int):
        imsignalindex = ImSignal
        
    else:
        raise TypeError("'ImSignal' expected to be a str or an int; got %s instead" % type(ImSignal).__name__)
    
    for segment in segments:
        signals = [segment.analogsignals[k] for k in (vmsignalindex, imsignalindex)]
        segment.analogsignals[:] = signals
        segment.epochs.clear()
        segment.events.clear()
        segment.spiketrains.clear()
        
    return data
    

def passive_Iclamp(vm, im=None, ssEpoch=None, baseEpoch=None, steadyStateDuration = 0.05 * pq.s, box_size = 0, Iinj=None):
    """
    Square pulse current injection in I-clamp experiments.
    
    vm: analogsignal with Vm in I-clamp
    im: analogsignal with Im command (injected current) - mandatory unless 
            Iinj is given
    
    baseEpoch: neo.Epoch, or sequence of t_start, t_stop time points
                baseline before current injection (optional, default is None) 
                needed when im is None
                
                when a sequence of time points, these may be python quantities in
                units compatible with vm.times.units
                
    ssEpoch:    steady state Vm epoch (optional, default is None)
                ends when current injection ends
                needed when im is None
                
    injEpoch:   
    
    steadyStateDuration: scalar or python quantity
                use to calculate the interval for Vm average on baseline and
                during trhe steady-state hyperpolarization
                default is 0.05 * pq.s
    
    box_size: int scalar (default 0) size of the boxcar window for filtering 
    
    Iinj : None or python Quantity: the amount of injected current; needed only
        when im is None
    
    """
    
    from scipy.signal import boxcar, convolve
    
    
    if isinstance(baseEpoch, (tuple, list)):
        if all([isinstance(v, numbers.Real) for v in baseEpoch]):
            t_start = baseEpoch[0]
            duration = t_stop - t_start
            baseEpoch = neo.Epoch(times = t_start * vm.times.units,
                                  durations = duration * vm.times.units)
            
        elif all([(isinstance(v, pq.Quantity) and units_convertible(v, vm.times)) for v in baseEpoch]):
            times = baseEpoch[0]
            durations = baseEpoch[1]-baseEpoch[0]
            baseEpoch = neo.Epoch(times=times, durations=durations)
            
        else:
            raise TypeError("incompatible base epoch specification: %s", baseEpoch)

    
    if isinstance(ssEpoch, (tuple, list)):
        if all([isinstance(v, numbers.Real) for v in ssEpoch]):
            t_start = ssEpoch[0]
            duration = t_stop - t_start
            ssEpoch = neo.Epoch(times = t_start * vm.times.units,
                                  durations = duration * vm.times.units)
            
        elif all([(isinstance(v, pq.Quantity) and units_convertible(v, vm.times)) for v in ssEpoch]):
            times = ssEpoch[0]
            durations = ssEpoch[1]-ssEpoch[0]
            ssEpoch = neo.Epoch(times=times, durations=durations)
            
        else:
            raise TypeError("incompatible base epoch specification: %s", ssEpoch)

        
    if box_size > 0 :
        window = boxcar(box_size)/box_size
        v_flt = convolve(np.squeeze(vm), window, mode="same", method = "fft")
        v_flt = neo.AnalogSignal(v_flt[:,np.newaxis], units = vm.units, t_start = vm.t_start, sampling_rate = 1/vm.sampling_period)
    else:
        v_flt = vm
        
    # 1) get transition times from injected current
    
    if isinstance(im, neo.AnalogSignal):
        # NOTE: 2017-08-30 21:53:33
        # there are only two states
        #
        # the code below this generates two states:
        #
        # state 0 = the lower-valued  centroid = "low" state
        # state 1 = the higher-valued centroid = "high" state
        #
        # for a NEGATIVE waveform (i.e., HYPERPOLARIZING current injection):
        #
        #   the high state is the baseline state (therefore expected to be found at
        #   the beginning and and at the end of the waveform)
        #
        #   the low state is the actual injection pulse
        #
        # for a POSITIVE waveform (i.e. upward deflection, for DEPOLARIZING current 
        # injection) things are reverse:
        #
        #   the low state is the baseline and the end of waveform
        #
        #   the high state is the actual pulse
        #
        centroids, cnt, edg, rng = sigp.state_levels(im, levels = 0.5)
        centroids = np.array(centroids).T[:,np.newaxis]
        
        #[low, high]
        
        #centroids, dist = cluster.vq.kmeans(im, 2)
        
        label, dst = cluster.vq.vq(im, centroids)
        
        #centroids, label = cluster.vq.kmeans2(im, 2) 
        
        #print("centroids ", centroids)
        
        # two states:
        
        edlabel = np.ediff1d(label, to_begin=0)
        
        down = im.times[np.where(edlabel == -1)]
        
        up  = im.times[np.where(edlabel == 1)]

        #print("down ", down)
        #print("up ", up)
        
        # upward deflection is earlier than downward deflection 
        # for a depolarizing current pulse
        if down > up:
            raise RuntimeError("For passive membrane properties, a hyperpolarizing current injection is expected")
        
        if baseEpoch is None:
            baseT1 = np.min([down, up]) * pq.s # because down and up are quantities and this strips their units away!
            baseT0 = baseT1 - steadyStateDuration
            
        else:
            baseT0 = baseEpoch.times
            baseT1 = baseT0 + baseEpoch.durations
            
        if ssEpoch is None:
            ssT1 = np.max([down, up]) * pq.s # because down and up are quantities and this strips their units away!
            ssT0 = ssT1 - steadyStateDuration
        else:
            ssT0 = ssEpoch.times
            ssT1 = ssT0 + ssEpoch.durations
        # the amount of injected Im
        Iinj = np.diff(centroids.ravel()) * im.units

    else:
        if not isinstance(baseEpoch, neo.Epoch):
            raise ValueError("base epoch must be specified")
        
        if not isinstance(ssEpoch, neo.Epoch):
            raise ValueError("steady-state epoch (ssEpoch) must be specified")
            
        if Iinj is None:
            raise ValueError("Iinj must be specified")
        
        elif isinstance(Iinj, numbers.Real):
            Iinj = Iinj * pq.pA
            
        elif isinstance(Iinj, pq.Quantity):
            if not units_convertible(Iinj, pq.pA):
                raise TypeError("Iinj is invalid: %s" % Iinj)
            
        else:
            raise TypeError("incompatible Iinj specified: %s" % Iinj)
        
        baseT0 = baseEpoch.times
        baseT1 = baseT0 + baseEpoch.durations
        
        ssT0 = ssEpoch.times
        ssT1 = ssT0 + ssEpoch.durations
            
        
    vmin = vm.min()
    
    "baseline Vm"
    vbase = v_flt.time_slice(baseT0, baseT1).mean()
    
    "steady-state hyperpolarization"
    vss = v_flt.time_slice(ssT0, ssT1).mean()
    
    
    # sag & rebound peak values (on filtered data => ~ average of box_size samples)
    vsag            = v_flt[box_size+1:-(box_size+1),:].min() # avoid filter artifacts at ends
    vrebound        = v_flt[box_size+1:-(box_size+1),:].max()
    
    #time of sag minimum
    sagMinTime      = (v_flt.argmin() + 1) * vm.sampling_period
    reboundMaxTime  = (v_flt.argmax() - 1) * vm.sampling_period
    
    #print("sag trough: ", vsag, " found at ", sagMinTime)

    vsagrise        = v_flt.time_slice(baseT1, sagMinTime)
    
    vsagmin = vsagrise.min()
    vsagmax = vsagrise.max()
    
    #print("vsagmin ", vsagmin)
    #print("vsagmax ", vsagmax)
    
    #print(vsagmin == vsag)
    
    vsagrange = vsagmin - vsagmax
    
    #print(vsagrange)
    
    # NOTE: if we use state_levels, below, we actually get a better fit & sag separation
    
    #vsag10 = vsagmax + 0.1  * vsagrange
    #vsag90 = vsagmax + 0.98  * vsagrange
    vsag10 = vsagmax
    vsag90 = vsagmin
    
    #print("vsag10 ", vsag10)
    #print("vsag90 ", vsag90)
    
    
    #### highest 10% of vsag rise
    #### vsagrise is negative, therefore "first" 10% are actually the last 10% values
    #vsag10 = sigp.state_levels(vsagrise, levels=0.9)[1]

    #### vice-versa for the 90%
    #vsag90 = sigp.state_levels(vsagrise, levels=0.1)[1]

    vsag10_90_index = (np.squeeze(vsagrise) <= vsag10) & (np.squeeze(vsagrise) >= vsag90)
    

    t_index = vsagrise.times[vsag10_90_index]
    vsag10_90 = vsagrise.time_slice(t_index[0],t_index[-1])
    
    offset = float(vsag10_90[0])
    
    scale  = float(vsag10_90[-1]) - offset
    
    delay  = float(vsag10_90.times[0])
    
    decay = 0.1
    
    params = [offset, scale, delay, decay]
    
        
    #popt, pcov = optimize.curve_fit(models.generic_exp_decay, vsagrise.times, np.squeeze(vsagrise), [offset, scale, delay, decay])
    popt, pcov = optimize.curve_fit(models.generic_exp_decay, vsag10_90.times, np.squeeze(vsag10_90), params)

    #print("params ", params)
    #print("popt ", popt)

    tau_m = popt[3]
    
    xx = np.linspace(float(vsag10_90.t_start), float(ssT0), (float(ssT0)-float(vsag10_90.t_start))/vm.sampling_period)
    #xx = np.linspace(float(vsag10_90.times[0]), float(vsag10_90.times[-1]), vm.shape[0])
    
    yy = models.generic_exp_decay(xx, *popt)
    
    vsag10_90_extended_fit = neo.AnalogSignal(yy[:, np.newaxis], 
                                     units = pq.mV, \
                                     t_start = vsag10_90.t_start, \
                                     sampling_rate = 1/vm.sampling_period)
    
    #print("fit time: ", vsag10_90_extended_fit.t_start, vsag10_90_extended_fit.t_stop)
    
    t0 = vsag10_90_extended_fit.t_stop - 0.05*pq.s
    t1 = vsag10_90_extended_fit.t_stop
    
    #print("t0 ", t0, "t1 ", t1)
    
    
    vinf = vsag10_90_extended_fit.time_slice(t0, t1).mean() # "tail" of vfit (at "infinity")
    
    vfit = dict()
    vfit["parameters"] = popt
    vfit["fitcurve"] = vsag10_90_extended_fit
    vfit["fitted_segment"] = vsag10_90
    vfit["Vextrapolated"] = vinf
    
    Rin = np.abs((vss - vbase) / Iinj).rescale(pq.ohm)
    Rss = np.abs((vinf - vbase) / Iinj).rescale(pq.ohm)
    
    time_constant = popt[-1] * pq.s
    
    
    return vbase, vss, vsag, vrebound, Rin, Rss, time_constant, vfit, v_flt


def PassiveMembranePropertiesAnalysis(block:neo.Block, Vm_index:(int,str) = "Vm_prim_1", Im_index:(int,str) = "Im_sec_1", box_size:int = 63, name:(str, type(None)) = None,plot:bool = True,**kwargs):
    """User-friendly wrap around the passive_Iclamp function.
    
    Arguments:
    =========
    block: neo.Block; expected to contain a songle Segment with the Vm and an Im 
        analog signals recorded for passive membrane properties experiments 
        (hyperpolarizing current injections in current-clamp).
        
    Vm_index = index or str with the Vm signal name (optinal, default is "Vm_prim_1")
    
    Im_index = index, or str with the name of the Im signal (optional, 
        default is Im_sec_1)
        
    box_size = scalar, integer, optinal (default 63) - size of a boxcar filter
        used for detecting state transitions in the Im waveform pulse
        
    name = str or None (optional, default is None)
    
    plot = boolean, optional, default True ; when True, a plot of the Vm 
    waveform and its fit are generated
    
    **kwargs -- passed directly on to passive_Iclamp
    
    Returns:
    ========
    
    A dictionary with the following keys:
    
    "Vbaseline"
    "Vsteadystate"
    "Vsag"        
    "Vrebound"    
    "Rinput"      
    "Rinsag"      
    "MembraneTau" 
    "VmFit"       
    "Name"        
    
    """
    if not isinstance(block, neo.Block):
        raise TypeError("Expected a neo.Block as first argument; got %s instead" % type(block).__name__)
    
    prefix = "Passive_Membrane_Analysis"
    
    if name is None:
        cframe = inspect.getouterframes(inspect.currentframe())[1][0]
        try:
            for (k,v) in cframe.f_globals.items():
                if isinstance(v, neo.Block) and v == block:
                    name = k
        finally:
            del(cframe)
        
    if block.name is not None:
        name += " block_%s" % block.name
    
    if Im_index is None:
        Im  = None
        
    else:
        if isinstance(Im_index, str):
            try:
                Im_index = neoutils.get_index_of_named_signal(block.segments[0], Im_index)
            except Exception as e:
                raise RuntimeError("%s signal not found" % Im_index)
            
        Im      = block.segments[0].analogsignals[Im_index]
        
        
    if isinstance(Vm_index, str):
        try:
            Vm_index = neoutils.get_index_of_named_signal(block.segments[0], Vm_index)
        except Exception as e:
            raise RuntimeError("%s signal not found" % Vm_index)
        
    
    Vm      = block.segments[0].analogsignals[Vm_index]

    [vbase, vss, vsag, vreb, rin, rss, mtc, vfit, _] = passive_Iclamp(Vm, Im, 
                                                                      box_size=box_size,
                                                                      **kwargs)
    
    if plot:
        plt.clf()
        plt.plot(Vm.times, Vm.magnitude, label="Vm", color="k")
        plt.plot(vfit["fitted_segment"].times, vfit["fitted_segment"], color="r", label="Fitted segment")
        plt.plot(vfit["fitcurve"].times, vfit["fitcurve"], color="blue", label="Fit")
        plt.xlabel("Time (%s)" % Vm.times.units.dimensionality.string)
        plt.ylabel("%s (%s)" % (Vm.name, Vm.units.dimensionality.string))
        plt.title(name)
        plt.legend()
        

    ret = dict()
    ret["Im"] = Im
    ret["Vm"] = Vm
    ret["Vbaseline"]    = vbase
    ret["Vsteadystate"] = vss
    ret["Vsag"]         = vsag
    ret["Vrebound"]     = vreb
    ret["Rinput"]       = rin
    ret["Rinsag"]       = rss
    ret["MembraneTau"]  = mtc
    ret["VmFit"]        = vfit
    ret["Name"]         = "%s %s" % (prefix, name)
    
    return ret

def ap_waveform_roots(w, value, interpolate=False):
    """ Times where value occurs on the rising and decaying phases of the waveform w
    
    Parameters:
    -----------
    
    w: neo.AnalogSignal
        Contains an AP waveform (possibly with some preceding and succeding 
        "baseline")
        
    value: scalar Quantity with same units as w
        The reference value for which the time occurrence in the rise and decay 
        phases of the waveform are sought.
    
    Returns:
    --------
    
    rise_x: the time where a sample nearest to value occurs in the rising phase
    rise_y: the actual value of the sample at that time
    rise_cslope: chord slope of rising phase around value
        calculated only when interpolate is True; otherwise is set to np.nan
    
    decay_x: the time where a sample nearest to value occurs on the decaying phase
    decay_y: the actual sample value at that time
    decay_cslope: chord slope of decaying phase around value
        calculated only when interpolate is True; otherwise is sety to np.nan
    
    Any of the returned value may be np.nan if calculations fail.
    
    NOTE: All returned values are floating point scalars
    
    """
    rise_x          = np.nan
    rise_y          = np.nan
    rise_cslope     = np.nan # chord slope of rising phase around value

    decay_x         = np.nan
    decay_y         = np.nan
    decay_cslope    = np.nan # chord slope of decay phase around value

    #print("ap_waveform_roots value", value)
    
    # "ge" stands for >= i.e. "greater than or equal"
    
    flags_ge_value = w >= value
    
    if not np.any(flags_ge_value):
        # no sample is >= value
        # bail out gracefully
        warnings.warn("ap_waveform_roots: no part of the signal is >= %s" % value, RuntimeWarning)
        
        return rise_x, rise_y, rise_cslope, decay_x, decay_y, decay_cslope
    
    flags_ge_value_diff = np.ediff1d(np.asfarray(flags_ge_value), to_begin=0)
    
    #print("flags_ge_value_diff", flags_ge_value_diff)
    
    # NOTE: deal with the rising phase
    # 
    
    # first positive crossing in flags_ge_value_diff is the index of the first
    # sample >= value, in the first region of waveform >= value
    
    # for "conformant" APs appropriately cropped (i.e. no bumps before
    # the AP itself) this falls on the rising phase
    ge_value_starts = np.where(flags_ge_value_diff == 1)[0]
    
    #print("ge_value_starts", ge_value_starts)
    
    if len(ge_value_starts) == 0:
        # bail out gracefully
        warnings.warn("ap_waveform_roots: cannot find where signla becomes >= %s" % value, RuntimeWarning)
        return rise_x, rise_y, rise_cslope, decay_x, decay_y, decay_cslope
        
    
    first_index_ge_value = int(ge_value_starts[0])
    
    # not sure we really need this
    first_sample_ge_value = float(w[first_index_ge_value])
    time_of_first_sample_ge_value = float(w.times[first_index_ge_value])
    
    if interpolate:
        if first_index_ge_value == 0:
            x0 = time_of_first_sample_ge_value
            y0 = first_sample_ge_value
            
            x1 = float(w.times[first_index_ge_value + 1])
            y1 = float(w[first_index_ge_value + 1])
    
        
        else: #get chord slope AROUND this point
            x0 = float(w.times[first_index_ge_value - 1])
            y0 = float(w[first_index_ge_value - 1])
        
            x1 = float(w.times[first_index_ge_value + 1])
            y1 = float(w[first_index_ge_value + 1])
            
            
        rise_cslope = (y1-y0) / (x1-x0) # chord slope at or around this point
            
        rise_x = (float(value) - y0) / rise_cslope + x0
        rise_y = first_sample_ge_value # value of "central" sample 
        
    else:
        rise_y = first_sample_ge_value
        rise_x = time_of_first_sample_ge_value
    
    
    # NOTE: deal with the decay phase - difficult if AP is on a rising baseline
    
    # for conformant AP waveforms this will never be empty, although it might
    # flag later regions that bump above the value
    # 
    ge_value_ends = np.where(flags_ge_value_diff == -1)[0]
    
    # ge_value_ends is empty when either w is an incomplete AP waveform 
    # (e.g. with truncated decay) or it rides on a rising baseline;
    
    # the latter can usually happen when value is the onset Vm and the AP is 
    # riding on a rising baseline (such that the onset Vm is only crossed once)
    
    # in these situations we bail out
    
    if len(ge_value_ends):
        # OK, there are regions of the AP waveform below this value
        # take index of the first sample past the last >= value in the 1st region
        # for conformant APs this falls on the decay phase
        end_index_ge_value = int(ge_value_ends[0])
        
        end_sample_ge_value = float(w[end_index_ge_value])
        time_of_end_sample_ge_value = float(w.times[end_index_ge_value])
        
        if interpolate:
            if end_index_ge_value == len(w)-1:
                x0 = float(w.times[end_index_ge_value-1])
                y0 = float(w[end_index_ge_value-1])
                
                x1 = time_of_end_sample_ge_value
                y1 = end_sample_ge_value
                
            else:
                x0 = float(w.times[end_index_ge_value-1])
                y0 = float(w[end_index_ge_value-1])
                
                x1 = float(w.times[end_index_ge_value+1])
                y1 = float(w[end_index_ge_value+1])
                
            decay_cslope = (y1-y0) / (x1-x0)
            
            if decay_cslope > 0:
                warnings.warn("positive slope on the decay phase", RuntimeWarning)
                
            decay_x = (float(value) - y0) / decay_cslope + x0
            decay_y = end_sample_ge_value# value of "central" sample 
            
        else:
            decay_y = end_sample_ge_value
            decay_x = time_of_end_sample_ge_value
            
    return float(rise_x), float(rise_y), float(rise_cslope), float(decay_x), float(decay_y), float(decay_cslope)

def analyse_AP_pulse_trains(data, segment_index=None, signal_index=0,triggers=None, tail=None,thr=20, atol=1e-8, smooth_window = 5,resample_with_period = 1e-5, t0=None, t1=None, dataname=None, cell="NA", genotype="NA", source="NA", sex="NA",age=np.nan, record=None, protocol_name=None,ref_vm = None, ref_vm_relative_onset=False,output_prefix=None):
    """Batch analysis for pulse-triggered APs in current-clamp.
    
    Loops through neo.Segments in data, calling analyse_AP_pulse_train for each
    segment. Suitable for use with ScanData objects (see below).
    
    Positional parameters:
    ======================
    data: neo.Block or datatypes.ScanData
        When a neo.Block, the function loops through the neo.Segment objects in 
            data.segments and calls analyse_AP_pulse_train() on each segment found
            
        When a datatypes.ScanData, the function does the same on the data.electrophysiology
        attribute (which is a neo.Block, see datatypes.ScanData)
    
    Named parameters:
    =================
    segment_index: one of int, tuple, list, range, slice, or None
    
        The function works on the subset of segments specified by 'segment_index'.
        
        When None, "triggers" must be provided as datatype.TriggerProtocol 
            (the function raises TypeError otherwise) 
            
    output_prefix: str or None (default)
        When a non-empty str, the function assigns the return variables (see below)
            directly in the calling namespace, with names prefixed by output_prefix
            (and returns None)
            
        Otherwise, the function returns as described in Returns section.
            
            
        
    NOTE: the remaining named parameters are passed directly to analyse_AP_pulse_train()
    
    triggers: 
    
    Returns:
    =======
    
    report: Pandas DataFrame; the concatenated reports of the analysed segments
            in data.
            
            NOTE: all identifiers (cell, source, genotype, etc) are categorical
            typpes (to be used as "factors" in further statistical analysis)
    
    aggregated_report: Pandas DataFrame; Aggregated data after grouping by AP index
                (AP index taken as factor factor) (*)
    
    grouped_report: Pandas DataFrame; results grouped by AP index (*)
    
    segments_ap_results
    segments_ap_waves, 
    segments_ap_dvdt, 
    segments_ap_d2vdt2
    
    
    (*) NOTE: these are meaningful when all analysed segments have the same number
    of APs
    
    """
    
    from CaTanalysis import group
    
    if isinstance(data, ScanData):
        dataname = data.name
        cell = data.cell
        genotype = data.genotype
        source = data.sourceID
        age = data.age
        sex = data.sex if hasattr(data, "sex") else getattr(data, "gender", "NA")
        data = data.electrophysiology
        
    if not isinstance(segment_index, (int, tuple, list, range, slice, type(None))):
        raise TypeError("segment_index has incompatible type: %s" % type(segment_index).__name__)
    
    if isinstance(segment_index, int):
        segment_index = [segment_index]
        
    elif isinstance(segment_index, (tuple, list)):
        if not all([isinstance(v, int) for v in segment_index]):
            raise TypeError("When a sequence, segment_index must contain ints")
        
    elif segment_index is None:
        if isinstance(triggers, TriggerProtocol):
            segment_index = triggers.segmentIndices()
            protocol_name = triggers.name
            
        elif triggers is None:
            raise TypeError("either a segment index should be specified, or triggers must be a TriggerProtocol")
    
    if isinstance(data, neo.Block):
        if isinstance(segment_index, (tuple, list, range)):
            if any([i<0 or i >= len(data.segments) for i in segment_index]):
                raise ValueError("segment_index %s contains invalid entries" % segment_index)
            
            segments = [data.segments[k] for k in segment_index]
            
        elif isinstance(segment_index, slice):
            if any([i<0 or i >= len(data.segments) for i in (segment_index.start, segment_index.stop)]):
                raise ValueError("segment_index %s is invalid" % segment_index)
            
            segments = data.segments[segment_index]
            
        else:
            segments = data.segments
        
    elif isinstance(data, (tuple, list, range)):
        if all([isinstance(d, neo.Segment) for d in data]):
            if isinstance(segment_index, (tuple, list)):
                if any([i<0 or i >= len(data.segments) for i in segment_index]):
                    raise ValueError("segment_index %s contains invalid entries" % segment_index)
                
                segments = [data[k] for k in segment_index]
            
            elif isinstance(segment_index, slice):
                if any([i<0 or i >= len(data.segments) for i in (segment_index.start, segment_index.stop)]):
                    raise ValueError("segment_index %s is invalid" % segment_index)
                
                segments = data[segment_index]
                
            else: # segment_index is a slice
                segments = data
                
            
        else:
            raise TypeError("when a sequence, data must contain only neo.Segment objects")
        
    else:
        raise TypeError("data expected to be a neo.Block or a sequence of neo.Segments; got %s instead" % type(data).__name__)
    
    segments_ap_results = list()
    segments_ap_reports = list()
    segments_ap_waves = list()
    segments_ap_dvdt = list()
    segments_ap_d2vdt2 = list()
    
    for k, segment in enumerate(segments):
        if record is None:
            if isinstance(segment.name, str) and len(segment.name.strip()):
                recname = segment.name
                
            else:
                recname = "segment_%d" % k
                
        else:
            recname=record
            
        ap_result, ap_report, ap_waves, ap_dvdt, ap_d2vdt2 = analyse_AP_pulse_train(segment, signal_index=signal_index,
                                                            triggers = triggers, tail=tail,
                                                            thr=thr, atol=atol, 
                                                            smooth_window=smooth_window,
                                                            resample_with_period=resample_with_period,
                                                            t0=t0,t1=t1, 
                                                            cell=cell, genotype=genotype, 
                                                            source=source, sex=sex,
                                                            age=age, dataname=dataname, 
                                                            record=recname, 
                                                            protocol_name=protocol_name,
                                                            ref_vm = ref_vm,
                                                            ref_vm_relative_onset = ref_vm_relative_onset)
        
        segments_ap_results.append(ap_result)
        segments_ap_reports.append(ap_report)
        segments_ap_waves.append(ap_waves)
        segments_ap_dvdt.append(ap_dvdt)
        segments_ap_d2vdt2.append(ap_d2vdt2)
        
    if len(segments_ap_reports):
        report = pd.concat(segments_ap_reports, ignore_index=True, sort=False)
        
        if report.Record.dtype.name != "category":
            report.Record = report.Record.astype("category")
            
        grouping = "AP"
        
        parameters = ['amplitude', 'onset', 'half_max', 'half_max_duration', 'quarter_max', 'quarter_max_duration', 'vm_0_duration', 'max_dv_dt']
        
        if all([v in report.columns for v in ("ref_vm", "ref_vm_duration")]):
            parameters += ["ref_vm", "ref_vm_duration"]
        
        grouped_report, group_by, pars = group(report, parameters=tuple(parameters), grouping=grouping)
        
        grouped_report = grouped_report.assign(Cell = [cell] * len(grouped_report),
                                                     AP = grouped_report.index)
        
        grouped_report.Cell = grouped_report.Cell.astype("category")
        
        grouped_report = grouped_report.assign(Source = [source] * len(grouped_report),
                                                     AP = grouped_report.index)
        grouped_report.Source = grouped_report.Source.astype("category")
        
        
        grouped_report = grouped_report.assign(Genotype = [genotype] * len(grouped_report),
                                                     AP = grouped_report.index)
        grouped_report.Genotype = grouped_report.Genotype.astype("category")
        
        grouped_report = grouped_report.assign(Sex = [sex] * len(grouped_report),
                                                     AP = grouped_report.index)
        grouped_report.Sex = grouped_report.Sex.astype("category")
        
        sdict = dict()
        
        for p in pars:
            sdict[p] = group_by[p].agg(np.nanmean)
            
        aggregated_report = pd.DataFrame(sdict)
        
        aggregated_report = aggregated_report.assign(Cell = [cell] * len(aggregated_report),
                                                     AP = aggregated_report.index)
        
        aggregated_report.Cell = aggregated_report.Cell.astype("category")
        
        aggregated_report = aggregated_report.assign(Source = [source] * len(aggregated_report),
                                                     AP = aggregated_report.index)
        aggregated_report.Source = aggregated_report.Source.astype("category")
        
        
        aggregated_report = aggregated_report.assign(Genotype = [genotype] * len(aggregated_report),
                                                     AP = aggregated_report.index)
        aggregated_report.Genotype = aggregated_report.Genotype.astype("category")
        
        aggregated_report = aggregated_report.assign(Sex = [sex] * len(aggregated_report),
                                                     AP = aggregated_report.index)
        aggregated_report.Sex = aggregated_report.Sex.astype("category")
        
        
        
        
    else:
        report = pd.DataFrame()
        grouped_report=None
        aggregated_report = None
        
    if isinstance(output_prefix, str) and len(output_prefix.strip()):
        wf.assignin(report, "%s_report" % output_prefix, )
        wf.assignin(aggregated_report, "%s_aggregated_report" % output_prefix)
        wf.assignin(grouped_report, "%s_grouped_report" % output_prefix)
        wf.assignin(segments_ap_results, "%s_ap_results" % output_prefix)
        wf.assignin(segments_ap_waves, "%s_ap_waves" % output_prefix)
        wf.assignin(segments_ap_dvdt, "%s_ap_dvdt" % output_prefix )
        wf.assignin(segments_ap_d2vdt2, "%s_ap_d2vdt2" % output_prefix )
        
        
    else:
        return report, aggregated_report, grouped_report, segments_ap_results, segments_ap_waves, segments_ap_dvdt, segments_ap_d2vdt2
        
def analyse_AP_pulse_train(segment, signal_index=0, triggers=None,tail=None, thr=20, atol=1e-8, smooth_window = 5,resample_with_period = 1e-5, t0=None, t1=None, record=None, dataname=None,cell="NA", genotype="NA", source="NA", sex="NA",age=np.nan, protocol_name="NA", ref_vm = None, ref_vm_relative_onset=False):
    
    """
    Analyses AP waveforms triggered by a train of current injection pulses.
    
    The function operates on a neo.Segment containing a Vm signal specified by
    signal_index, by calling analyse_AP_pulse_signal() on that signal
    
    Positional parameters:
    =====================
    
    segment: neo.Segment; its 'analogsignals' attribute is a list of 
                neo.AnalogSignal objects expected to contain the actual Vm 
                signal with the AP waveforms 
        
    Named parameters:
    =================
    signal_index: int scalar (default 0) = index of the Vm signal in 
                    segment.analogsignals, or
                    
                  str = name of Vm signal contained in segment.analogsignals
                  
    triggers: None (default), or
    
              TriggerEvent where 'times' attribute indicate the time
              of current pulses (in the time domain of Vm), or
              
              TriggerProtocol containing postsynaptic trigger events
              (see TriggerProtocol and TriggerEvent for details)
                the times of the current injection pulses for eliciting APs are
                taken as sthe postsynaptic trigger times
                
              neo.IrregularlySampledSignal or datatypes.IrregularlySampledDataSignal
                the times of the current injection pulses are taken as the 
                'times' attribute
                
                (useful when the times are determined by some other algorithm
                that returns them 'packed' as an irregularly sampled signal)
                
              Python Quantity array (this is just an array of time 'stamps')
                with units convertible to Vm time domain's units
                
              numpy array of float scalars with the time 'stamps' 
               (ideally a vector, otherwise it will be flattened)
               
              sequence (tuple, list) of time 'stamps' (packed as a non-nested 
               list); the element of the sequence can be fooat scalars or Python
               Quantity objects with units of time (convertible to Vm time 
               domain's units)
               
            NOTE: When None, the time 'stamps' for the current injection pulses
            will be retrieved from the trigger events contained in the segment's
            'events' attribute. 
            
            Raises ValueError if segment.events is empty or contains no 
            TriggerEvent objects.
              
              
              
    
    NOTE: the following names parameters are passed directly to 
            analyse_AP_pulse_signal()
            (execute analyse_AP_pulse_signal? for details)
    
    tail, thr, atol, smooth_window, resample_with_period, t0, t1,
    
    record, dataname, cell, genotype, source, sex, age,
    
    protocol_name, ref_vm
    
    Returns:
    =======
    
    """
    
    if isinstance(segment, (tuple, list)) and all([isinstance(s, neo.AnalogSignal) for s in segment]):
        signals = segment
        
    elif isinstance(segment, neo.Segment):
        signals = segment.analogsignals
        
    else:
        raise TypeError("'segment' expected to be a neo.Segment or a sequence of analogsignals; got %s inistead" % type(segment).__name__)
    
    if isinstance(signal_index, str):
        if len(signal_index.strip()) == 0:
            raise ValueError("signal_index is an empty string!")
        
        signal_index = neoutils.get_index_of_named_signal(segment, signal_index, silent=True)
        
        if isinstance(signal_index, (tuple, list)):
            if len(signal_index) and isinstance(signal_index[0], int):
                signal_index = signal_index[0]
            else:
                raise ValueError("signal %s not found" % signal_index)
            
        elif not isinstance(signal_index, int):
            raise ValueError("signal %s not found" % signal_index)
        
    if isinstance(signal_index, int):
        signal = signals[signal_index]
        
    else:
        raise TypeError("signal_index expected to be an int, or a str; got %s instead" % type(signal_index).__name__)
    
    if triggers is None:
        if isinstance(segment, neo.Segment):
        # try to identify AP trigger events crudely from the event name
        # this assumes some naming convention so it is likely to fail
            trigger_events = [e for e in segment.events if isinstance(e, TriggerEvent) and\
                                                        any([s in e.name.lower() for s in ("ap", "action", "postsyn")])]

            if len(trigger_events) == 0:
                raise ValueError("segment does not contain trigger events and no trigger have been specified")
            
            else:
                times = trigger_events[0].times
                
        else:
            raise TypeError("'triggers' is None, segment must be a neo.Segment")
        
    elif isinstance(triggers, TriggerEvent):
        # user passed a TriggerEvent; we assume the user knows what they're
        # doing so we're using the time stamps of these events
        times = triggers.times
        
    elif isinstance(triggers, TriggerProtocol) and isinstance(triggers.postsynaptic, TriggerEvent):
        times = triggers.postsynaptic.times
        
    elif isinstance(triggers, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal)):
        times = triggers.times
        
        if not units_convertible(times, signal.times.units):
            raise TypeError("triggers domain units (%s) are incompatible with this data" % triggers.times.dimensionality)
        
        elif times.units != signal.times.units:
            times = times.rescale(signal.times.units)
        
    elif isinstance(triggers, pq.Quantity):
        if units_convertible(triggers, signal.times):
            times = triggers
            
            if triggers.units != signal.times.units:
                times = times.rescale(signal.times.units)
                
        else:
            raise TypeError("triggers units (%s) are incompatible with the data" % triggers.dimensionality)
            
    elif isinstance(triggers, np.ndarray):
        times = triggers * signal.times.units
    
    elif isinstance(triggers, (tuple, list)):
        if all([isinstance(v, numbers.Real) for v in triggers]):
            times = np.array(triggers) * signal.times.units
            
        elif all([isinstance(v, pq.Quantity) and units_convertible(v, signal.times.units) for v in triggers]):
            times = triggers
            
        else:
            raise TypeError("%s cannot be used as trigger protocol" % triggers)
        
    else:
        raise TypeError("%s cannot be used as trigger protocol" % triggers)
    
    if isinstance(record, str) and len(record.strip()):
        recordname = record
        
    elif isinstance(segment.name, str) and len(segment.name.strip()):
        recordname = segment.name
        
    elif isinstance(signal.name, str) and len(signal.name.strip()):
        recordname = signal.name
        
    elif (protocol_name == "NA" or protocol_name is None) and \
        (isinstance(triggers, (TriggerProtocol, TriggerEvent)) and isinstance(triggers.name, str) and len(triggers.name.strip())):
        recordname.append(triggers.name)
        
    else:
        recordname = "NA"
        
    ap_result, ap_report, ap_waves, ap_dvdt, ap_d2vdt2 = analyse_AP_pulse_signal(signal, times, tail=tail,
                                                   thr=thr, atol=atol,
                                                   smooth_window=smooth_window,
                                                   resample_with_period=resample_with_period,
                                                   t0=t0, t1=t1, record=recordname, 
                                                   cell=cell, genotype=genotype, 
                                                   source=source, sex=sex,
                                                   age=age, dataname=dataname, protocol_name=protocol_name,
                                                   ref_vm = ref_vm,
                                                   ref_vm_relative_onset = ref_vm_relative_onset)
    
    #print(ap_report.Record)
    
    return ap_result, ap_report, ap_waves, ap_dvdt, ap_d2vdt2
    

def analyse_AP_pulse_signal(signal, times,  tail=None, thr=20, atol=1e-8, smooth_window = 5,resample_with_period = 1e-5, t0=None, t1=None, record=None, cell="NA", genotype="NA", source="NA", sex="NA",age=np.nan, dataname=None, protocol_name="NA", ref_vm = None, ref_vm_relative_onset=False):
    """Waveform analysis for action potentials elicited individually by brief 
    pulses of current injection.
    
    Potisional parameters:
    =====================
    
    signal: neo.AnalogSignal with the Vm signal
    
    times: Python Quantity array with the times of the trigger pulses 
            (with time units)

    Named parameters:
    ================
    tail: Python Quantity; the time interval that follows the waveform, 
            or None (default)
    
    thr: float scalar, detection threshold (default: 20)
    
    atol: float scalar, abs tolerance (default: 1e-8)
    
    smooth_window:  integer scalar for boxcar smoothing (default: 5)
    
    resample_with_period: float scalar or None; when not None, signal will be 
            resampled to achieve the specified new samplig period
            
    t0, t1: Python Quantities or None; when not None, they specify the time
        interval within 'signal', where APs have occurred (to avoid procesing
        very long signals when APs only occur within a defined and small interval)
        
    record: str, unique identifier for this signal (e.g. segment number or 
            segment name in a neo.Block or "NA" when not available) 
            or None (default).
            When None, will be set to "NA"
            
            
    cell: str, unique identifier for the recorded cell, or "NA" (default) when 
        not available
    
    genotype: str, e.g.: "wt", "het", "hom" or any other meaningful identifier
            or "NA" (default) when not available

    source: str, unique identifier of the recording source (e.g. animal ID, 
        culture ID, etc.); default is "NA"
        
    sex: str, the genetic sex or sex or "NA" (default) when not available
    
    age: scalar float, default is np.nan
    
    dataname: str or None (default); unique identifier of the electrophysiology 
        data (e.g. name of file on disk) that provided the Vm signal; when None,
        it will be set to "NA"
        
    protocol_name: str (default: "NA"); name of the stimulation or triggers 
        protocol (if any)
        
    ref_vm: scalar float with the Vm value where AP duration should be determined
        (in addition to the duration at half-max and at 0 mV); default is None.
        
        NOTE: this can be a value RELATIVE to the onset Vm 
        (see 'ref_vm_relative_onset', below).
        
    ref_vm_relative_onset: boolean (default False):
        When True, this indicates that ref_vm value is RELATIVE to the onset Vm.
        
        e.g., if ref_vm is given as -15, the actual Vm for the measurements
        described above (see 'ref_vm') will be calculated at V onset - 15 mV !
        
        When False (default), indicated that ref_vm is an absolute Vm value; e.g.,
        if ref_vm is -15, then the measurements described above (see 'ref_vm')
        will be done for THIS Vm value
        
        
    Returns:
    ========
    ap_results: list with results from the analysis of the AP waveforms;
                each element is a datatypes.DataBag with calculated parameters 
                for each AP waveform (as returned by analyse_AP_waveform())
    
    report: Python Pandas DataFrame or None if no APs are present 
                (i.e. when ap_results is an empty list)
                
                The ap_results list, packed in a R data.frame-like object.
                
    ap_waves, ap_dvdt, ap_d2vdt2: lists of neo.AnalogSignal objects.
    
                These are the waveforms, respectively, of the AP, 1st and 2nd 
                derivative of the AP with respect to time.
    
    """
    from scipy.signal import boxcar
    
    if not isinstance(signal, neo.AnalogSignal):
        raise TypeError("'signal' expected to be a neo.AnalogSignal; got %s instead" % type(signal).__name__)
        
    if resample_with_period is not None:
        signal = sigp.resample_pchip(signal, resample_with_period)
            
    if isinstance(t0, numbers.Real):
        t0 *= signal.times.units
        
    elif isinstance(t0, pq.Quantity):
        if not units_convertible(t0, signal.times.units):
            raise TypeError("t0 expected to be a float or quantity scalar with %s units" % signal.time.dimensionality)
        
        elif t0.units != signal.times.units:
            t0 = t0.rescale(signal.times.units)
            
    elif t0 is not None:
        raise TypeError("t0 has unexpected type %s" % type(t0).__name__)
    
    if isinstance(t1, numbers.Real):
        t1 *= signal.times.units
        
    elif isinstance(t1, pq.Quantity):
        if not units_convertible(t1, signal.times.units):
            raise TypeError("t1 expected to be a float or quantity scalar with %s units" % signal.time.dimensionality)
        
        elif t1.units != signal.times.units:
            t1 = t1.rescale(signal.times.units)
    elif t1 is not None:
        raise TypeError("t1 has unexpected type %s" % type(t0).__name__)
    
    if t0 is not None:
        if t1 is None:
            t1 = signal.t_stop
            
    if t1 is not None:
        if t0 is None:
            t0 = signal.t_start
            
    if t0 is not None and t1 is not None:
        signal = signal.time_slice(t0, t1)
            
    dsdt = sigp.ediff1d(signal).rescale(pq.V/pq.s)
    
    if isinstance(thr, numbers.Real):
        thr *= pq.V/pq.s
        
    elif isinstance(thr, pq.Quantity):
        if not units_convertible(thr, dsdt.units):
            raise TypeError("'thr' expected to have %s units; got %s instead" % (dsdt.units.dimensionality, thr.units.dimensionality))
        
        thr = thr.rescale(pq.V/pq.s)

    if smooth_window is not None:
        dsdt = sigp.convolve(dsdt, boxcar(smooth_window)/smooth_window)
        
    d2sdt2 = sigp.ediff1d(dsdt).rescale(dsdt.units/dsdt.times.units)
    
    if smooth_window is not None:
        d2sdt2 = sigp.convolve(d2sdt2, boxcar(smooth_window)/smooth_window)
    
    ap_waves = extract_pulse_triggered_APs(signal, times, tail=tail)
    ap_dvdt = extract_pulse_triggered_APs(dsdt, times, tail=tail)
    ap_d2vdt2 = extract_pulse_triggered_APs(d2sdt2, times, tail=tail)
        
    ap_results = [analyse_AP_waveform(w, thr, dvdt=dw, d2vdt2=d2w, ref_vm = ref_vm, ref_vm_relative_onset = ref_vm_relative_onset) for w, dw, d2w in zip(ap_waves, ap_dvdt, ap_d2vdt2)]
    
    if dataname is None:
        dataname="NA"
        
    if record is None:
        record = "NA"
    
    if len(ap_results):
        index = np.arange(len(ap_results))
        
        fields = [key for key in ap_results[0].keys() if isinstance(ap_results[0][key], np.ndarray) and len(ap_results[0][key]) == 1]
        
        res_dict = collections.OrderedDict()
        
        res_dict["Data"] = pd.Series([dataname] * len(ap_results), name="Data").astype("category")
        
        res_dict["Source"] = pd.Series([source] * len(ap_results), name="Source").astype("category")
        
        res_dict["Cell"] = pd.Series([cell] * len(ap_results), name="Cell").astype("category")
        
        res_dict["Genotype"] = pd.Series([genotype] * len(ap_results), name="Genotype").astype("category")
        
        res_dict["Sex"] = pd.Series([sex] * len(ap_results), name="Sex").astype("category")
        
        res_dict["Age"] = pd.Series([age] * len(ap_results), name="Age")
        
        res_dict["Record"] = pd.Series([record] * len(ap_results), name="Record").astype("category")
        
        res_dict["Protocol"] = pd.Series([protocol_name] * len(ap_results), name="Protocol").astype("category")
        
        res_dict["AP"] = pd.Series(["AP_%d" % k for k in range(len(ap_results))], name="AP").astype("category")
        
        for field in fields:
            value = np.array([r[field] for r in ap_results if isinstance(r[field], np.ndarray) and len(r[field]) == 1]).flatten() * ap_results[0][field].units
            series = pd.Series(data = value, index=index, name=field, copy=True)
            res_dict[field] = series
            
        report = pd.DataFrame(res_dict, index=index)
        
        #params.Record = pd.Categorical(params.Record.astype("category"))
        
    else:
        report = None
    
    return ap_results, report, ap_waves, ap_dvdt, ap_d2vdt2

def get_AP_analysis_parameter(data:typing.Union[dict, tuple, list], parameter=str, min_APs:typing.Optional[int] = None):
    """
    Get AP parameter from an AP analysis data for each depolarising step.
    
    Returns:
    a list of parameter values
    """

    if isinstance(data, dict): 
        if all(v in data.keys() for v in ["Depolarising_steps", "Injected_current"]):
            steps = data["Depolarising_steps"]
        else:
            raise ValueError("Data does not seem to be an AP analysis result")

    elif isinstance(data, (tuple, list)):
        if all(["AP_analysis"] in d.keys() and isinstance(d["AP_analysis"], dict) for d in data):
            steps = data
        else:
            raise ValueError("Data does not seem to be an AP analysis result")
            
    else:
        raise TypeError("Expecting a dict, tuple, or list containing results for each depolarizing step; got %s instead" % type(data).__name__)
    
    if any([parameter not in step["AP_analysis"].keys() for step in steps]):
        raise ValueError("parameter %s not found in all injection step analyses" % parameter)
    
    if isinstance(min_APs, int) and min_APs < 0:
        raise ValueError("minAPs must be > 0")
    
    else:
        min_APs = None
    
    max_parameter_array_len = 0
    
    ret = list()
    
    parameter_units = None
    
    for ks, step in enumerate(steps):
        if isinstance(min_APs, int):
            if min_APs > 1:
                if len(step["AP_analysis"]["AP_train"] < min_APs):
                    continue
            
        parameter_data = step["AP_analysis"][parameter] # NOTE: if a quantity, this should have the same units throughout!!!
        
        if parameter_data is None:
            continue
        
        elif isinstance(parameter_data, np.ndarray):
            if parameter_units is None or parameter_units == pq.dimensionless:
                if isinstance(parameter_data, (neo.basesignal.BaseSignal, pq.Quantity)):
                    parameter_units = parameter_data.units
                else:
                    parameter_units = pq.dimensionless
                
            if isinstance(parameter_data, neo.basesignal.BaseSignal):
                parameter_value = parameter_data.as_array()
                
            else:
                parameter_value = np.atleast_1d(parameter_data.magnitude) # enforce it being sizeable to enable len(...)
                
        elif isinstance(parameter_data, numbers.Number):
            parameter_value = np.atleast_1d(np.array([parameter_data]))
            parameter_units = pq.dimensionless
            
        else:
            parameter_value = parameter_data
            parameter_units = pq.dimensionless
            
        if parameter_units is None:
            parameter_units = pq.dimensionless
            
        
        ret.append(parameter_value)
        
    return list(map(lambda x: x * parameter_units, ret))


def extract_AP_waveforms(sig, iinj, times, before = None, after = None, use_min_isi=False):
    """Extracts the AP waveforms from a Vm signal.
    
    Parameters:
    ===========
    
    sig: neo.AnalogSignal with one channel
    
    iinj: neo.AnalogSignal with the actual current injection step 
                (without any tail that might have been added to sig)
            or a tuple (t_start, t_stop) in pq.s: the start/stop times of the 
            injection step
    
    times: 
        numpy or Quantity array in units compatible with the time units of sig
            
            * when a vector (ndim <= 2 with a single column) specifying waveform START times
            
            * when an array with ndim ==2 and two columns specifying waveform START and STOP times, respectively
            
            * a neo.Epoch: 
                its times attribute specifies waveform START times
                its durations attribute specifies waveform DURATIONS
                
            * a spike train: its times attribute specifies waveform START times
            
            
        
    before: None (default), or time value(s) to add BEFORE the waveform START times 
            specified as:
                a float scalar: 
        
                a Quantity with compatible time units
                
                a 1D numpy or Quantity array (either ndim == 1 OR ndim == 2 and shape[1] == 1)
                    size must equal the number of waveform START times in "times"
                    
    after: None (default), or as "before", but specifies the time interval to add to 
            "times" in case "times" only specifies the waveform START times
            
            Required when "times" specifies only waveform START times and use_min_isi is False (see below)
            
            NOTE: when not None and "times" also specifies waveform STOP or DURATIONS,
            the values in "after" will be added to the STOP/DURATION values effectively
            resulting in longer waveforms
            
    use_min_isi: boolean, default False
            When True, use the shortest time interval between the START of consecutive
                waveforms as duration for the waveforms. 
                NOTE: this will override any waveform stops specified in 'times'
                
            Used instead of specifying 'after', only when 'times' has more than one waveform START time
    """
    
    if not isinstance(sig, neo.AnalogSignal):
        raise TypeError("Expecting an analog signal, got %s instead" % type(sig).__name__)
    
    if isinstance(times, neo.SpikeTrain):
        times = times.times
        
    if isinstance(times, np.ndarray):
        if len(times) == 0:
            raise ValueError("'times' must contain at least one time point")
        
        if not isinstance(times, pq.Quantity):
            times = times * sig.time.units
            
        else:
            if not units_convertible(times, sig.times):
                raise TypeError("times units (%s) are incompatible with this signal (%s)" % (times.units.dimensionality, sig.times.units.dimensionality))
            
            times = times.rescale(sig.times.units)
                
        if times.ndim == 1 or (times.ndim == 2 and times.shape[1] == 1):
                
            starts = times.flatten()
                
            stops = None
                    
        else:
            starts = times[:,0].flatten()
            stops  = times[:,1].flatten()
            
    elif isinstance(times, neo.Epoch):
        starts = times.times.rescale(sig.times.units).flatten()
        stops = starts + times.durations.rescale(sig.times.units).flatten()
        
    else:
        raise TypeError("times expected to be a Quantity array, numpy array, neo.SpikeTrain or neo.Epoch; got %s instead" % type(times).__name__)
    
    if starts is None or len(starts) == 0:
        return [], None, None, None
    
    intervals = np.ediff1d(starts)
    
    if use_min_isi:
        if len(intervals):
            after = intervals.min()
            
        else:
            if isinstance(iinj, (tuple, list)):
                after = iinj[1] - starts[0]
            else:
                after = iinj.t_stop - starts[0]
            #raise ValueError("Cannot calculate minimum ISI for a single waveform")
        
    if after is None:
        if stops is None:
            raise TypeError("When times is a vector, after must be specified, or set 'use_min_isi' to True")
    
    if isinstance(after, numbers.Real):
        after = after * sig.times.units

        if stops is None or use_min_isi:
            stops = starts + after
            
        else:
            stops = stops + after
            
    elif isinstance(after, np.ndarray):
        after = after.flatten()
        
        if len(after) > 1 and after.shape != times.shape:
            raise ValueError("when a vector, 'after' must have the same length as times")
        
        if isinstance(after, pq.Quantity):
            if not units_convertible(after, sig.times.units):
                raise TypeError("units of after are incompatible with signal's times units")
            
        else:
            after = after * sig.times.units
        
        if stops is None or use_min_isi:
            stops = starts + after
            
        else:
            stops = stops + after
        
    else:
        raise TypeError("'after' has unexpected type: %s" % type(after).__name__)

    if before is not None:
        if isinstance(before, numbers.Real):
            before = before + sig.times.units
            
            delay_0 = starts[0] - sig.t_start
            
            if before > delay_0:
                before = delay_0
            
        elif isinstance(before, np.ndarray):
            before = before.flatten()
            
            if len(before) > 1 and len(before) != len(starts):
                raise ValueError("'before' had incompatible size" )
            
            if isinstance(before, pq.Quantity):
                if not units_convertible(before, sig.times.units):
                    raise TypeError("'before' has incompatible units")
                
                before = before.rescale(sig.times.units)
                
            else:
                before = before * sig.times.units
                
            delay_0 = starts[0] - sig.t_start
            
            if before[0] > delay_0:
                before[0] = delay_0
                
        else:
            raise TypeError("'before' has unexpected type %s" % type(before).__name__)
        
        starts = starts - before
        
        intervals = np.ediff1d(starts) # this will have changed if 'before' is a vector with different values
        
    if starts[0] < sig.t_start:
        starts[0] = sig.t_start
        
    if stops[-1] >= sig.t_stop:
        stops[-1] = sig.t_stop
        
    waves = [sig.time_slice(t0, t1) for (t0, t1) in zip(starts, stops)]

    return waves, intervals, starts, stops
    
    
def extract_pulse_triggered_APs(sig, times, tail = None):
    """
    Extracts AP waveforms from a Vm signal.
    
    The AP are supposed to be triggered by brief pulses of
    current injection at predefined times (hence no AP waveform
    detection is performed).
    
    Positional parameters:
    =====================
    
    sig: neo.AnalogSignal with Vm data
    
    times: Quantity array in units compatible with the time units of sig
    
    WARNING: no checks are performed on whether there actually is 
    an AP waveform at the specified time points
    
    Named parameters:
    =================
    tail: float scalar or quantity: duration of window to be added
        to the end of the last waveform, or None (default)
        
        
        When None, times must be an array with at least two time points
        and "tail" will be taken as the interval between the last two
        time points in the times array.
        
    Returns:
    ========
    
    waves: list of waveform signals (time slices of the analog signal sig)
    
    """
    
    if not isinstance(sig, neo.AnalogSignal):
        raise TypeError("Expecting an analog signal, got %s instead" % type(sig).__name__)
    
    if isinstance(times, np.ndarray):
        if len(times) == 0:
            raise ValueError("times must contain at least one time point")

        if not isinstance(times, pq.Quantity):
            times = times.flatten() * sig.times.units
                
        else:
            if not units_convertible(times, sig.times):
                raise TypeError("times units (%s) are incompatible with this signal (%s)" % (times.units.dimensionality, sig.times.units.dimensionality))
            
            times = times.rescale(sig.times.units)
        
    else:
        raise TypeError("times expected to be a Quantity or numpy array; got %s instead" % type(times).__name__)
        
    if tail is None:
        if len(times) == 1:
            raise TypeError("when times has only one time point, 'tail' must be specified")
        
        tail = np.ediff1d(times)[-1] # ediff1d returns a quantity here
        
    else:
        if isinstance(tail, numbers.Real):
            tail  *= sig.times.units
            
        elif isinstance(tail, np.ndarray):
            if len(tail) != 1:
                raise TypeError("'tail' expected to be a scalar; got %s instead" % tail)
            
            if not isinstance(tail, pq.Quantity):
                tail *= sig.times.units
                
            else:
                if not units_convertible(tail, sig.time.units):
                    raise TypeError("'tail' units (%s) are incompatible with signal's times: %s" % (tail.units.dimensionality, sig.times.units.dimensionality) )
                
                tail = tail.rescale(sig.times.units)
        
    
    waves = [sig.time_slice(start, start+tail) for start in times]
    
    return waves

def detect_AP_rises(s, dsdt, d2sdt2, dsdt_thr, minisi, vm_thr=0, rtol = 1e-5, atol = 1e-8, return_all=False):
    # NOTE: 2019-11-29 16:49:14
    # use a Vm threshold to discard "aberrant" events
    
    # NOTE: 2019-04-25 09:22:13
    # boolean array; True where dV/dt >= thr and rising (its 2nd derivative) is > 0
    #
    # NOTE: 2019-04-19 12:44:41
    # simply finding dV/dt >= threshold may detect a "fake" AP at the 
    # beginning of the Vm rising phase (when the depolarizing current injection
    # starts) if the Vm raises very quickly but remains subthreshold (no real AP 
    # firing occurs)
    #
    # TODO: possible workarounds 
    # 1) use a higher threshold but then this may misplace the true "start" of "real" APs
    # 
    # 2) consider two thresholds: one for time stamp detection, the other for the actual Vm
    # to be higher than a "ground truth" threshold (~ -60 mV) -- cumbersome
    #
    # 3) template matching (correlation) with a template AP waveform (synthetic or otherwise)
    #   -- needs constructing a templkate waveform selected by user.
    #
    # 4) give a minimum value of AP ISI or duration of the putative AP waveform
    
    # NOTE: 2019-04-23 13:37:48
    # using workaround (4) from above
    
    # NOTE: 2019-04-26 13:41:45 FIXME
    # the algorithm fails when the 1st order derivative is NOT monotonically
    # increasing over the fast rising phase;
    # in this case there are large variations in the 1st order derivative
    # leading to double-peaks in the 2nd order derivative
    #
    # e.g. when there is a "kink" between the "IS" spike and the "SD" spike
    # --  see Bruce Bean 2007 review
    #
    # NOTE: 2017-09-04 22:27:48 CAUTION
    # this algorithm may also detect "aborted" APs that fall on the repolarizing 
    # phase when Im injection has stopped
    #
    
    # ### BEGIN NOTE: 2019-04-25 09:22:13 DEPRECATED by NOTE: 2019-11-29 16:40:34
    # select start of the fast (initial) rising phase
    # we're LIKELY to have found a fast rising phase when the Vm satisfies:
    # 
    # a) dVm/dt >= threshold
    #
    # b) d2Vm/dt2 > 0 (dVm/dt is MONOTONICALLY INCREASING)
    #
    # select start of the fast (initial) rising phase
    # we're LIKELY to have found a fast rising phase when the Vm satisfies:
    # 
    # a) dVm/dt >= threshold
    #
    # b) d2Vm/dt2 > 0 (dVm/dt is MONOTONICALLY INCREASING)
    #
    #fast_rise_starts = (dsdt.magnitude >= dsdt_thr) & (d2sdt2.magnitude > (0 + atol))
    #fast_rise_start_flags = np.ediff1d(np.asfarray(fast_rise_starts), to_begin = 0) == 1 
    
    #fast_rise_start_times = s.times[fast_rise_start_flags]
    
    ##print("detect_AP_rises, len(fast_rise_start_times)", len(fast_rise_start_times))
    
    #if len(fast_rise_start_times) == 0: # nothing detected
        #return None, None, None
    
    #t0 = fast_rise_start_times[0]
    
    ## NOTE: with large injected currents the rise of Vm may be detected as an AP
    ## however, unlike the 1st deirvative of an AP, the dv/dt of this rising Vm
    ## curve does NOT cross zero (become negative) until the next detected rise
    #t1 = fast_rise_start_times[1] if len(fast_rise_start_times) > 1 else s.t_stop
    
    #if np.all(dsdt.time_slice(t0, t1).magnitude > 0):
        ## reject t0 as it is likely to come from a rising Vm without AP
        
        #if len(fast_rise_start_times) == 1: # nothing detected
            #return None, None, None
        
        #fast_rise_start_times = fast_rise_start_times[1:]
        
    
    ## NOTE: 2019-04-29 08:40:55
    ## The problem with the above is that AP waveforms with "hunched" rising phase
    ## (with a strong kink between the IS and SD spike) will be detected as two
    ## consecutive rising phases because their rising phase is NOT monotonic.
    ##
    ## We therefore have to eliminate the start times that are closer to the 
    ## previous one by less that minisi.
    ## 
    ## NOTE: 2019-04-29 09:16:45
    ## We cannot simply use ediff1d, because after we found a "bad" start, the
    ## time point following it must be judged by its delay with respect to
    ## the last "good" starts one instead of the current one (which is what ediff1d does). 
    ## Instead, we use the loop below.
    
    #fast_rise_start_times_corrected = list()
    
    ## this means we always return at least ONE fast rise time !
    #fast_rise_start_times_corrected.append(fast_rise_start_times[0])
    
    #for k, t in enumerate(fast_rise_start_times[1:]):
        #if t-t0 >= minisi:
            #fast_rise_start_times_corrected.append(t)
            #t0 = t

    ## CAUTION: this replaces the initial fast_rise_start_times
    #fast_rise_start_times = np.array(fast_rise_start_times_corrected) * s.times.units
            
    # ### END 
    
    #print(f"detect_AP_rises: vm_thr = {vm_thr}")
    
    # ### BEGIN NOTE: 2019-11-29 16:40:34 New algorithm
    # slightly modified detection algorithm:
    # 1) get the logical index where dv/dt >= threshold -- as in NOTE: 2019-04-25 09:22:13
    # but do not use any condition d2v/dt2 as it is too wobbly
    fast_rise_starts = (dsdt.magnitude[:,] >= dsdt_thr)
    # 2) as in NOTE: 2019-04-25 09:22:13 get the loical flags for the starts of
    # the regions of dv/dt >= threshold
    fast_rise_start_flags = np.ediff1d(np.asfarray(fast_rise_starts), to_begin = 0) == 1 
    
    # 3) generate enhanced times array, containing putative start times and 
    # including the signal's t_stop; np.append dumps the units but the quantity
    # __array_finalize__ will append its own (dimensionless); hence we correct
    # this by multiplying the result with the signal's times units
    fast_rise_start_times = np.append(s.times[fast_rise_start_flags], s.t_stop) * s.times.units
    
    # 4)  now use the start times pairwise to slice the original Vm signal;
    # we retain thse start times which begin a segment of the signal that overshoots
    # the vm threshold (vm_thr, which is 0 by default)
    accept_flags = [False] * len(fast_rise_start_times)
    accept_flags[:-1] = [s.time_slice(t, fast_rise_start_times[k+1]).max().magnitude > vm_thr for k, t in enumerate(fast_rise_start_times[:-1])]

    # the following _DROPS_ signal.t_stop at the end of the array
    fast_rise_start_times = fast_rise_start_times[accept_flags] 
    
    # this shuould also preclude the use of a minisi condition
    # ### END NOTE: 2019-11-29 16:40:34 New algorithm
    
    # NOTE: 2019-04-29 09:52:03
    # to find out when the fast rising phase of the waveform ends we get the time
    # of the next local maximum in the dsdt waveform slice following each fast 
    # rise start time;
    fast_rise_stop_times    = np.full_like(fast_rise_start_times, np.nan)
    
    # NOTE: 2019-04-29 11:13:46
    # also get the peak times by finding argmax on the AP waveform itself
    # an alternative way is to find where the dvdt waveform crosses zero
    # while d2vdt2 waveform is negative, but these conditions are likely to be
    # to met simultaneously met at several time points along the waveforms meaning
    # we'll have to pick the only first of such occurrence, which involves more CPU work
    peak_times              = np.full_like(fast_rise_start_times, np.nan)
    
    #print("detect_AP_rises signal t_start=%s, t_stop=%s" % (s.t_start, s.t_stop))
    #print("detect_AP_rises dsdt t_start=%s, t_stop=%s" % (dsdt.t_start, dsdt.t_stop))
    
    for k, t in enumerate(fast_rise_start_times):
        #print("detect_AP_rises k: %s,  t=%s" % (k,t))
        if t < s.t_start:
            # this won't ever happen would it?
            t = s.t_start
        
        if k < len(fast_rise_start_times)-1:
            t1 = fast_rise_start_times[k+1]
            
        else: # avoid going past the end in fast_rise_start_times
            t1 = s.t_stop
            
        wave = s.time_slice(t, t1)
        dwave = dsdt.time_slice(t, t1)
        
        ndx = dwave.argmax()
        fast_rise_stop_times[k] = dwave.times[ndx]
        
        peak_ndx = wave.argmax()
            
        peak_times[k] = s.times[peak_ndx]
        
    return fast_rise_start_times, fast_rise_stop_times, peak_times#, waves, dwaves
        

def extract_AP_train(vm:neo.AnalogSignal,im:typing.Union[neo.AnalogSignal, tuple],tail:pq.Quantity=0.5*pq.s,method:str="state_levels",box_size:numbers.Number=0, adcres:numbers.Number=15,adcrange:numbers.Number=10,adcscale:numbers.Number=1e3,resample_with_period:(pq.Quantity, type(None)) = None,resample_with_rate:(pq.Quantity, type(None)) = None,Itimes_relative:bool = True,Itimes_samples:bool=False):
    """
    Extract the time slice of the VM corresponding to a current injection step.
    
    If a signal containing a rectangular current injection waveform is given, it
    will also extract the corresponding time slice.
    
    Parameters:
    -----------
    
    vm: neo.AnalogSignal; the recorded membrane voltage
    
    im: neo.AnalogSignal (with current injection rectangular waveform) or
        a tuple of three python Quantity objects as follows: 
            current injection amplitude (pA), t_start (pq.s) and t_stop (pq.s)
            
        where t_start and t_stop are the onset and the end of the current 
        injection waveform.
            
        If 'im' is an AnalogSignal then t_start and t_stop will be determined
        form the waveform, assuming it is a rectangular wave.
        
    tail: non-negative scalar Quantity (units: "s"); default is 0.5 s
        duration to be added to t_stop (see above) before slicing the signals
        
    resample_with_period: None (default), scalar float or python Quantity
        When not None, the Vm signal will be resampled before processing.
        
        When a Quantity, it must be in units convertible (scalable) to the 
        signal's sampling period units.
        
        Resampling occurs on the region corresponding to the current injection, 
        prior to AP waveform detection.
        
        NOTE 1: Upsampling might be useful (see Naundorf et al, 2006) but slows
        the code. To upsample the Vm signal, pass here a value smaller than
        the sampling period of the Vm signal.
        
    resample_with_rate: None (default), scalar float or python Quantity.
        When not None, the Vm signal will be resampled before processing.
        
        When Quantity, it must be in units convertible (scalable) to the signal's
        sampling rate units.
        
        Resampling occurs on the region corresponding to the depolarizing current
        injection, before performing detection of AP waveforms.
        
        See NOTE 1 above.
        
    box_size: int >= 0; default is 0.
    
        size of the boxcar (scipy.signal.boxcar) used for filtering the Im signal
        containing the current injection rectangular waveform, before detecting 
        the waveform boundaries (t_start & t_stop)
        
        default is 0 (no boxcar filtering)
        
    method: str, one of "state_levels" (default) or "kmeans"
        Detection method for the two "states" ("ON" and "OFF") in the rectangular
        current injection.
        
        See also the functions:
        signalprocessing.parse_step_waveform_signal
    
    adcres, adcrange, adcscale: float scalars
        See also the functions:
        signalprocessing.parse_step_waveform_signal and signalprocessing.state_levels.
    
        Used only when method is "state_levels"
        
    Itimes_relative:bool, default is True; 
        When True and im is a triplet, then im[1] and im[2] are the times of 
        current injection start/stop relative to Vm signal start.
        
    Itimes_samples:bool, default is False.
        When True, and im is a triplet, then im[1] and im[2] are the current
        injection start/stop in number of samples; this implies they ALWAYS 
        resolve to times relative to the Vm signal start.
        
    """
    # parse resample_... parameters
    if not all([v is None for v in (resample_with_period, resample_with_rate)]):
        if isinstance(resample_with_period, float):
            resample_with_period *= vm.sampling_period.units
            
        elif isinstance(resample_with_period, pq.Quantity):
            if resample_with_period.size > 1:
                raise TypeError("new sampling period must be a scalar Quantity; got %s instead" % resample_with_period)
            
            if units_convertible(resample_with_period, vm.sampling_period):
                if resample_with_period.units != vm.sampling_period.units:
                    resample_with_period.rescale(vm.sampling_period.units)
                    
            else:
                raise TypeError("new sampling period has incompatible units (%s); expecting (%s)" % (resample_with_period.units, vm.sampling_period.units))
            
        elif resample_with_period is not None:
            raise TypeError("new sampling period expected to be a scalar float, Quantity, or None; got %s instead" % type(resample_with_period).__name__)
        
        if isinstance(resample_with_rate, float):
            resample_with_rate *= vm.sampling_rate.units
            
        elif isinstance(resample_with_rate, pq.Quantity):
            if resample_with_rate.size > 1:
                raise TypeError("new sampling rate must be a scalar Quantity; got %s instead" % resample_with_rate)
        
            if units_convertible(resample_with_rate, vm.sampling_rate):
                if resample_with_rate.units != vm.sampling_rate.units:
                    resample_with_rate.rescale(vm.sampling_rate.units)
                    
            else:
                raise TypeError("new sampling rate has incompatible units (%s); expecting (%s)" % (resample_with_rate.units, vm.sampling_rate.units))
            
        elif resample_with_rate is not None:
            raise TypeError("new sampling rate expected to be a scalar float, Quantity, or None; got %s instead" % type(resample_with_rate).__name__)
        
        if resample_with_rate is not None and resample_with_period is None:
            resample_with_period = neoutils.sampling_rate_or_period(resample_with_rate, resample_with_period)
            
        elif resample_with_rate is not None and resample_with_period is not None:
            if not neoutils.sampling_rate_or_period(resample_with_rate, resample_with_period):
                raise ValueError("resample_with_rate (%s) and resample_with_period (%s) are incompatible" % (resample_with_rate, resample_with_period))
    

    if isinstance(im, neo.AnalogSignal):
        try:
            # down, up, inj, centroids, label
            # down = time point of the up-down transition
            # up   = time point of the down-up transition
            # inj  = injected current (difference between centroids )
            # label = int array "mask" with 0 for down and 1 for up; same shape as im
            d, u, inj, c, l = sigp.parse_step_waveform_signal(im,
                                                                method=method,
                                                                box_size=box_size, 
                                                                adcres=adcres,
                                                                adcrange=adcrange,
                                                                adcscale=adcscale)
            
            
            if d.ndim > 0:
                d = d[0]
            if u.ndim > 0:
                u = u[0]
                
            start, stop = (min(d,u), max(d,u))
            
            if d < u:
                inj *= -1.0
            
            vstep = vm.time_slice(start, stop + tail)
            istep = im.time_slice(start, stop + tail)
            
            # print(f"extract_AP_train: start = {start}, stop = {stop}")
                
            Ihold = istep.mean()
            
        except:
            print("Cannot parse current injection signal; use manually entered Ihold, start and stop times instead\n\n\n")
            raise
            
    else:
        Ihold = im[0]
        inj = Ihold
            
        if Itimes_samples:
            istart = int(im[1]) * vm.sampling_period
            istop = int(im[2]) * vm.sampling_period
            
            istart, istop = (istart, istop) if istart <= istop else (istop, istart)
            
            istart = istart.rescale(pq.s) + vm.t_start
            istop = istop.rescale(pq.s) + vm.t_start
            
        elif Itimes_relative:
            if isinstance(im[1], (int, float)):
                istart = im[1] * pq.s
                
            elif isinstance(im[1], pq.Quantity):
                if im[1].size > 1:
                    raise TypeError(f"Expecting a scalar quantity in im[1]; got {im[1].size} instead")
                
                if units_convertible(im[1], pq.s):
                    istart = im[1].rescale(pq.s)
                else:
                    raise TypeError(f"Expecting a time quantity in im[1]; got {im[1]} instead")
                
            else:
                raise TypeError(f"Expecting an int, float or Quantity with time units in im[1]; got {type(im[1]).__name__} instead")

            if isinstance(im[2], (int, float)):
                istop = im[2] * pq.s
                
            elif isinstance(im[2], pq.Quantity):
                if im[2].size > 1:
                    raise TypeError(f"Expecting a scalar quantity in im[2]; got {im[2].size} instead")
                
                if units_convertible(im[2], pq.s):
                    istop = im[2].rescale(pq.s)
                else:
                    raise TypeError(f"Expecting a time quantity in im[2]; got {im[2]} instead")
                
            else:
                raise TypeError(f"Expecting an int, float or Quantity with time units in im[2]; got {type(im[2]).__name__} instead")

            istart, istop = (istart, istop) if istart <= istop else (istop, istart)

            istart = im[1] + vm.t_start
            istop = im[2] + vm.t_start
            
        vstep = vm.time_slice(istart, istop + tail)
        istep = [istart, istop]
    
    # resample the Vm signal (the sliced one)
    if resample_with_period is not None:
        if resample_with_period > vstep.sampling_period:
            warnings.warn("A sampling period larger than the signal's sampling period (%s) was requested (%s); the signal will be DOWNSAMPLED" % (vstep.sampling_period, resample_with_period), RuntimeWarning)

        vstep = sigp.resample_pchip(vstep, resample_with_period)
        
        if vstep.size == 0:
            raise RuntimeError("Check resampling; new period requested was %s and the resampled signal has vanished" % resample_with_period)
        
    return vstep, Ihold, inj, istep

def detect_AP_waveform_times(sig, thr=10, smooth_window=5, min_ap_isi= 6e-3*pq.s, min_fast_rise_duration=None, rtol=1e-5, atol = 1e-8, vm_thr=0):
    """Detects AP waveform time starts in an AP train elicited by step depolarizing current injection.
    
    Detection is done primarily via thresholding on the 1st derivative of the Vm signal
    
    Parameters:
    ===========
    sig: neo.AnalogSignal with the Vm data
    thr: scalar, detection threshold on the dV/dt
    smooth_window: scalar int, the size of boxcar smoothig window (default is 5)
    """
    
    from scipy.signal import boxcar
    
    if not isinstance(sig, neo.AnalogSignal):
        raise TypeError("Expecting a neo.AnalogSignal; got %s instead" % type(sig).__name__)
    
    if sig.ndim > 2 or (sig.ndim == 2 and sig.shape[1] > 1):
        raise TypeError("Signal must be a vector")
    
    if smooth_window > 0:
        w = boxcar(int(smooth_window))/int(smooth_window)
        
    else:
        w = None
    
    if min_fast_rise_duration is None:
        min_fast_rise_duration = (10**(np.floor(np.log10(sig.sampling_period.rescale(pq.s).magnitude)) + 1)) * pq.s
        
    elif isinstance(min_fast_rise_duration, numbers.Real):
        min_fast_rise_duration *= pq.s
    
    elif isinstance(min_fast_rise_duration, pq.Quantity):
        if not units_convertible(min_fast_rise_duration, sig.times):
            raise TypeError("units of 'min_fast_rise_duration' (%s) are not compatible with those of the signal's time domain (%s)" % (min_fast_rise_duration.units, sig.times.units))
        
        if min_fast_rise_duration.units != sig.times.units:
            min_fast_rise_duration.rescale(sig.times.units)
    
    else:
        raise TypeError("'min_fast_rise_duration' expected to be a scalar, a Quantity, or None; got %s instead" % type(min_fast_rise_duration).__name__)
    
    #### BEGIN Detect APs by thresholding on the 1st derivative of the Vm signal
    #
    # NOTE: 2019-04-25 09:23:59 FYI:
    # dVm/dt    = 1st derivative of the Vm wrt time
    # d2Vm/dt2  = 2nd derivative of the Vm wrt time

    # NOTE: 2019-04-25 09:15:03
    # 1st derivative of the Vm signal
    
    # NOTE: 2019-11-19 17:07:34
    # need to do this in order to scale signal derivatives correctly
    vmsig = neo.AnalogSignal(sig.rescale(pq.V).magnitude, sampling_period = sig.sampling_period.rescale(pq.s),
                             units = pq.V, t_start = sig.t_start, time_units = pq.s, name=sig.name)
    vmsig.annotate(**sig.annotations)
    
    dv_dt = sigp.ediff1d(vmsig).rescale(pq.V/pq.s)  # 1st derivative of the Vm signal
    
    if w is not None:
        dv_dt_smooth = sigp.convolve(dv_dt, w)        # and its smoothed version
        dv_dt_smooth.name = "%s_1st_derivative" % sig.name
        
    else:
        dv_dt_smooth = dv_dt
    
    # NOTE 2019-04-25 09:15:41
    # 2nd derivative tells whether the 1st derivative is monotonically
    # increasing or decreasing (i.e. if Vm rate of change is increasing or decreasing)
    # we differentiate the smoothed 1st derivative !
    
    dvmsig = neo.AnalogSignal(dv_dt_smooth.rescale(pq.V/pq.s).magnitude,
                              t_start = dv_dt_smooth.t_start,
                              sampling_period = dv_dt_smooth.sampling_period,
                              units = pq.V/pq.s, time_units = pq.s, 
                              name = dv_dt_smooth.name)
    
    dvmsig.annotate(**dv_dt_smooth.annotations)
    
    d2v_dt2 = sigp.ediff1d(dvmsig).rescale(pq.V/(pq.s**2)) # 2nd derivative of the Vm signal
    
    if w is not None:
        d2v_dt2_smooth = sigp.convolve(d2v_dt2, w)                   # and its smoothed version 
        d2v_dt2_smooth.name = "%s_2nd_derivative" % sig.name
        
    else:
        d2v_dt2_smooth = d2v_dt2
        
    ap_rises = detect_AP_rises(sig,
                                dv_dt_smooth,
                                d2v_dt2_smooth,
                                thr, min_ap_isi,
                                atol=atol,
                                vm_thr=vm_thr)
    
    ap_fast_rise_start_times, ap_fast_rise_stop_times, ap_peak_times = ap_rises
    
    if ap_fast_rise_start_times is None:
        ap_fast_rise_durations = None
        
    else:
        ap_fast_rise_durations = ap_fast_rise_stop_times - ap_fast_rise_start_times
        
        # kick out "fake" APs: AP_index is an integer array (with sample indices)
        # into the above times and durations arrays
        AP_index = np.where(ap_fast_rise_durations >= min_fast_rise_duration)[0]
        
        if len(AP_index):
            ap_fast_rise_start_times  = ap_fast_rise_start_times[AP_index]
            ap_fast_rise_stop_times   = ap_fast_rise_stop_times[AP_index]
            ap_fast_rise_durations    = ap_fast_rise_durations[AP_index]
            ap_peak_times             = ap_peak_times[AP_index]
            
        
        else:
            ap_fast_rise_start_times = ap_fast_rise_stop_times = ap_fast_rise_durations = ap_peak_times = None
        
            
    #
    #### END
    
    return ap_fast_rise_start_times, ap_fast_rise_stop_times, ap_fast_rise_durations, ap_peak_times, dv_dt, d2v_dt2
    
    
def detect_AP_waveforms_in_train(sig, iinj, thr = 10, before = 0.001, after = None, min_fast_rise_duration = None, min_ap_isi = 6e-3*pq.s, rtol = 1e-5, atol = 1e-8, use_min_detected_isi=True,smooth_window = 5,interpolate_roots = False,decay_intercept_approx = "linear",decay_ref = "hm",get_duration_at_Vm=None,return_all = False, vm_thr=0, **kwargs):
    """Detects action potentials in a Vm signal.
    For use with experiments using "steps" of depolarizing current injections.
    
    Parameters:
    ----------
    
    sig :       neo.AnalogSignal with Vm data (the "Vm signal"): 
                units must be in V or mV
                
    iinj:       neo.AnalogSignal with the actual current injection step 
                (without any tail that might have been added to sig)
    
    thr :       scalar;
                the rate of Vm rise threshold for AP detection (in V/s)
                (optional, default is 10)
    
    before :    scalar, or Quantity;
    
                The number of ms to include in the AP waveform BEFORE its threshold)
                (optional, default = 0.001 s)
                
                When a Quantity, it is expected to have units of "s"
                
    after :     scalar, Quantity or None (default);
    
                The number of ms to include in the AP waveform AFTER its threshold)
                (optional, default = None)
                
                When a Quantity, it is expected to have units of "s".
                
                When None (the default) the Vm slice encompassing the actual AP
                waveform is taken up to the onset of the next AP, or to the end
                of the depolarizing current injection step.
                
                NOTE 1: This is useful to capture AHPs that follow the actual 
                    AP waveform.
        
                NOTE 2: to generate waveforms of the AP only, set 
                    "before" and "after" to zero.
                
    min_fast_rise_duration : None (default), scalar or Quantity;
    
                The minimum duration of the initial (fast) segment of the rising 
                phase of a putative AP waveform.
            
                This is used to identify "fake" APs: regions of the Vm trace where 
                the 1st derivative is above the rise threshold ("thr" above) but
                the Vm values are still below AP threshold. "Fake" APs may be 
                detected when the Vm rises very fast at the beginning of 
                the current injection step (yet the Vm is still sub-threshold).
                
                When None, this parameter will be set to the next higher power of
                10 above the sampling period of the signal.
    
                When a Quantity, it is expected to have units convertible to the 
                Vm signal's time units.
                
    min_ap_isi : None, scalar or Quantity;
    
                Default is 6e-3 * pq.s
    
                Minimum interval between two consecutive AP fast rising times 
                ("kinks"). Used to discriminate against suprious fast rising time
                points that occur DURING the rising phase of AP waveforms.
                
                This can happen when the AP waveforms has prominent IS and the SD 
                "spikes", 
                
                see Bean, B. P. (2007) The action potential in mammalian central neurons.
                Nat.Rev.Neurosci (8), 451-465

    rtol, atol: float scalars;
                the relative and absolute tolerance, respectively, used in value 
                comparisons (see numpy.isclose())
                
                defaults are:
                rtol: 1e-5
                atol: 1e-8
                
    use_min_detected_isi: boolean, default True
    
        Used when "after" is None.
    
        When True, individual AP waveforms cropped from the Vm signal "sig" will
            have the duration equal to the minimum detected inter-AP interval.
        
        When False, the durations of the AP waveforms will be taken to the onset
            of the next AP waveform, or the end of the Vm signal
            
    smooth_window: int >= 0; default is 5
        The length (in samples) of a smoothing window (boxcar) used for the 
        signal's derivatives.
        
        The length of the window will be adjusted if the signal is upsampled.
        
    interpolate_roots: boolean, default False
        When true, use linear inerpolation to find the time coordinates of the
        AP waveform rise and decay phases crossing over the onset, half-maximum
        and 0 mV. 
        
        When False, uss the time coordinate of the first & last sample >= Vm value
        (onset, half-max, or 0 mV) respectively, on the rise and decay phases of
        the AP waveform.
        
        see ap_waveform_roots()
        
    decay_intercept_approx: str, one of "linear" (default) or "levels"
        Used when the end of the decay phase cannot be estimated from the onset
        Vm.
        
        The end of the decay is considerd to be the time point when the decaying
        Vm crosses over (i.e. goes below) the onset value of the action potential.
        
        Whe the AP waveform is riing on a rising baseline, this time point cannot
        be determined.
        
        Instead, it is estimated as specified by "decay_intercept_approx" parameter:
        
        When decay_intercept_approx is "linear", the function uses linear extrapolation
        from a (higher than Vm onset) value specified by decay_ref (see below)
        to the onset value.
        
        When decay_intercept_approx is "levels", the function estimates a "pseudo-baseline"
        as the lowest of two state levels determined from the AP waveform histogram.
        
        The pseudo-baseline is then used to estimate the time intercept on the decay
        phase.
        
    decay_ref: str, one of "hm" or "zero", or floating point scalar
        Which Vm value should be used to approximate the end of the decay phase
        when using the "linear" approximation method (see above)
        
    get_duration_at_Vm: None or scalar:
        When a scalar, the function reports the AP waveform durations at the specified
        Vm value, IN ADDITION TO the duration at 0 mV and half-max (which may vary
        across cells!)
            
    return_all: boolean, default False -- for debugging purposes only
    
        When True, the function will also return a dictionary with various
        internal variables used or calculated during the AP waveform detection.
    
    t_start, t_stop: start, stop time of the spiketrain - relevant when detection
        takes place on a slice of the original signal; these values should reflect 
        the entire extend of the original signal
        
        Optional; default values are taken from `sig`.
        
    Returns:
    --------
    
    ap_train, ap_waveform_signals
    
    The returned values, explained:
    -------------------------------
    
    ap_train : neo.SpikeTrain.
        The "times" attribute contains the time values of the AP thresholds
        (starts of the rising phase).
        
        The "waveforms" attribute contains the AP waveforms as a 2D numpy array
            (without time domain information, and shorter waveforms tail-padded
            with np.nan to the length of the longest waveform)
            
            These AP waveforms as neo.AnalogSignals are also returned separately
            as a list of AnalogSignals (not padded)
            
        The "annotations" attribute contains the following set of pre-defined keys:
        
        "AP_peak_values"
        "AP_peak_amplitudes"
        "AP_onset_Vm"
        "AP_durations_V_onset"
        "AP_half_max"
        "AP_durations_V_half_max"
        "AP_quart_max"
        "AP_durations_V_quart_max"
        "AP_third_max"
        "AP_durations_V_third_max"
        "AP_durations_V_0"
        "AP_ref_Vm"
        "AP_durations_at_Ref_Vm"
        "AP_Maximum_dV_dt"
        "AP_waveform_times"
        "AP_dV_dt_waveforms"
        "AP_d2V_dt2_waveforms"
    
        AP_peak_values: neo.IrregularlySampledSignal
            Contains the Vm values at each peak of the APs in the Vm signal
            The times of the AP peak in the Vm signal are in its "times"
            attribute. 
            
        AP_peak_amplitudes: neo.IrregularlySampledSignal
            Contains the amplitudes of each AP waveform, at the times of the 
            AP peaks.
            
        AP_onset_Vm: neo.IrregularlySampledSignal 
            Contains the Vm values at the onset of each AP in the Vm signal.
            The times of the AP onsets in the Vm signal are in the "times" 
            attribute of the signal. 
            
            The first value in this signal is the membrane AP threshold
            (value of Vm where the first AP was fired)
            
        AP_ref_Vm: the value of the reference Vm to calculate AP width at,
            or None if not specified
            
        AP_*_max: neo.IrregularlySampledSignal
            The values of the AP at half-max, 1/4 of maximum and 
            1/3 of maximum, from the onset value
            
        AP_durations_*: neo.IrregularlySampledSignal
            Contains the AP durations at the specified Vm values (0 mV, onset,
            half-max, etc...)
        
        AP_Maximum_dV_dt: new.IrregularlySampledSignal
            Contains the maximum slope of each AP waveform. The "times" attribute
            if the AP onset times.
            
        AP_waveform_times: Quantity array (in signal's time units)
            Contains the time domain for the ap_train's "waveforms" attribute
            (see blow). Useful for plotting.
            
        AP_dV_dt_waveforms: sequence of the fist order derivative of the AP 
            waveforms as analog signals.
            
            WARNING: these do not have identical time domains (although they do
                have the same sampling rate), and may have different lengths
            
        AP_d2V_dt2_waveforms: sequence of the second order derivative of the AP 
            waveforms as analog signals
            
            WARNING: these do not have identical time domains (although they do
                have the same sampling rate), and may have different lengths
        
        When no APs were found, the "times" and "waveforms" attributes are empty
        and "annotations" keys are mapped to None except for AP_ref_Vm, if given.
        
    ap_waveform_signals is a sequence (list) of neo.AnalogSignals, 
        each containing the AP waveform and any subsequent AHP (see NOTE 1);
        
        These do not have identical time domains (although they do have
        the same sampling rate, they will have different t_start and t_stop values).
        Depending on the value of the 'use_min_detected_isi' parmeter, they
        may also have different durations.
        
            
    References:
    -----------
    
    Naundorf et al (2006). Unique features of action potential initiation in 
        cortical neurons. Nature 440, 1060–1063.
    
    Brown & Randall (2009) Activity-dependent depression of the spike
        after-depolarization generates long-lasting intrinsic plasticity 
        in hippocampal CA3 pyramidal neurons. J Physiol 587(6) 1265-1281
        
    """
    import scipy.interpolate
    from scipy.interpolate import PchipInterpolator as pchip
    from scipy.signal import boxcar, convolve
    
    #### BEGIN parse parameters
    # make sure before & after are quantities with compatible time units
    
    if isinstance(before, numbers.Real):
        before *= pq.s
        
    elif isinstance(before, pq.Quantity):
            raise TypeError("units of 'before' (%s) are not compatible with those of the signal's time domain (%s)" % (before.units, sig.time.units))

    else:
        raise TypeError("'before' expected to be a scalar or a Quantity; got %s instead" % type(before).__name__)
        
    if isinstance(after, numbers.Real):
        after *= pq.s
        
    elif isinstance(after, pq.Quantity):
        if not units_convertible(after, sig.times):
            raise TypeError("units of 'after' (%s) are not compatible with those of the signal's time domain (%s)" % (after.units, sig.times.units))
        
    elif after is not None:
        raise TypeError("'after' expected to be a scalar, a Quantity, or None; got %s instead" % type(after).__name__)
        
    if not isinstance(sig, neo.AnalogSignal):
        raise TypeError("Expecting a neo.AnalogSignal; got %s instead" % type(sig).__name__)
    
    if sig.ndim > 2 or (sig.ndim == 2 and sig.shape[1] > 1):
        raise TypeError("Signal must be a vector")
    
    if min_fast_rise_duration is None:
        min_fast_rise_duration = (10**(np.floor(np.log10(sig.sampling_period.rescale(pq.s).magnitude)) + 1)) * pq.s
        
    elif isinstance(min_fast_rise_duration, numbers.Real):
        min_fast_rise_duration *= pq.s
    
    elif isinstance(min_fast_rise_duration, pq.Quantity):
        if not units_convertible(min_fast_rise_duration, sig.times):
            raise TypeError("units of 'min_fast_rise_duration' (%s) are not compatible with those of the signal's time domain (%s)" % (min_fast_rise_duration.units, sig.times.units))
        
        if min_fast_rise_duration.units != sig.times.units:
            min_fast_rise_duration.rescale(sig.times.units)
    
    else:
        raise TypeError("'min_fast_rise_duration' expected to be a scalar, a Quantity, or None; got %s instead" % type(min_fast_rise_duration).__name__)
    
    if min_ap_isi is None:
        min_ap_isi = 0 * pq.s
        
    elif isinstance(min_ap_isi, numbers.Real):
        min_ap_isi *= pq.s
        
    elif isinstance(min_ap_isi, pq.Quantity):
        if not units_convertible(min_ap_isi, sig.times):
            raise TypeError("units of 'min_ap_isi' (%s) are not compatible with those of the signal's time domain (%s)" % (min_ap_isi.units, sig.times.units))
    
        if min_ap_isi.units != sig.times.units:
            min_ap_isi.rescale(sig.times.units)
    
    else:
        raise TypeError("'min_ap_isi' expected to be a scalar, a Quantity, or None; got %s instead" % type(min_ap_isi).__name__)
    
    if isinstance(decay_intercept_approx, str):
        if decay_intercept_approx.strip().lower() not in ("linear", "levels"):
            raise ValueError("'decay_intercept_approx' expected to be one of 'linear', 'levels'; got %s instead" % decay_intercept_approx)

    else:
        raise TypeError("'decay_intercept_approx' expected to be a str; got %s instead" % type(decay_intercept_approx).__name__)
    
    if isinstance(decay_ref, str):
        if decay_ref.strip().lower() not in ("hm", "qm", "zero"):
            raise ValueError("When a str, 'decay_ref' must be one of 'hm', 'qm', or 'zero'; got %s instead" % decay_ref)
        
    elif isinstance(decay_ref, numbers.Real):
        decay_ref *= sig.units
        
    elif isinstance(decay_ref, pq.Quantity):
        if not units_convertible(decay_ref, sig):
            raise TypeError("'decay_ref' units (%s) are incompatible with the signal's units (%s)" % (decay_ref.units, sig.units))
        
        if decay_ref.units != sig.units:
            decay_ref.rescale(sig.units)
            
    else:
        raise TypeError("'decay_ref' has inappropriate type: %s" % type(decay_ref.__name__))
    
    if isinstance(get_duration_at_Vm, numbers.Real):
        reference_Vm = get_duration_at_Vm * sig.units
        
    elif isinstance(get_duration_at_Vm, pq.Quantity):
        if not units_convertible(get_duration_at_Vm, sig.units):
            raise TypeError("get_duration_at_Vm expected to have %s units; got %s instead" % (sig.units.dimensionality, get_duration_at_Vm.units.dimensionality))
        
        if get_duration_at_Vm.units != sig.units:
            reference_Vm = get_duration_at_Vm.rescale(sig.units)
            
        else:
            reference_Vm = get_duration_at_Vm
            
    elif get_duration_at_Vm is None:
        reference_Vm = None
        
    else:
        raise TypeError("get_duration_at_Vm expected to be a scalar real, Quantity or None; got %s instead" % type(get_duration_at_Vm).__name__)
    
    t_start = kwargs.pop("t_start", sig.t_start)
    t_stop = kwargs.pop("t_stop", sig.t_stop)
    
    # print(f"detect_AP_waveforms_in_train kwargs t_start {t_start} t_stop {t_stop}")
    # ### END parse parameters
    
    #### BEGIN Detect APs by thresholding on the 1st derivative of the Vm signal
    #
    
    #print(f"detect_AP_waveforms_in_train: vm_thr = {vm_thr}")
    ap_waveform_times = detect_AP_waveform_times(sig, thr=thr, 
                                                 smooth_window=smooth_window,
                                                 min_ap_isi=min_ap_isi,
                                                 min_fast_rise_duration=min_fast_rise_duration,
                                                 rtol=rtol, atol=atol,
                                                 vm_thr=vm_thr)

    ap_fast_rise_start_times, ap_fast_rise_stop_times, ap_fast_rise_durations, ap_peak_times, dv_dt, d2v_dt2 = ap_waveform_times
    
    # ### END detect APs by thresholding
    
    train_annotations = dict()
    train_annotations["AP_peak_values"]          = None
    train_annotations["AP_peak_amplitudes"]      = None
    train_annotations["AP_onset_Vm"]             = None
    train_annotations["AP_durations_V_onset"]    = None
    train_annotations["AP_half_max"]             = None
    train_annotations["AP_durations_V_half_max"] = None
    train_annotations["AP_quart_max"]            = None
    train_annotations["AP_durations_V_quart_max"]= None
    train_annotations["AP_third_max"]            = None
    train_annotations["AP_durations_V_third_max"]= None
    train_annotations["AP_durations_V_0"]        = None
    train_annotations["AP_ref_Vm"]               = reference_Vm
    train_annotations["AP_durations_at_Ref_Vm"]  = None
    train_annotations["AP_Maximum_dV_dt"]        = None
    train_annotations["AP_waveform_times"]       = None
    train_annotations["AP_dV_dt_waveforms"]      = None
    train_annotations["AP_d2V_dt2_waveforms"]    = None
    
    # print(f"detect_AP_waveforms_in_train t_start {t_start} t_stop {t_stop}")
    ap_train = neo.SpikeTrain([], t_start=t_start, t_stop = t_stop, units = pq.s)
    
    if ap_fast_rise_start_times is None:
        ap_train.annotations.update(train_annotations)
        return ap_train, []
    
    # indexing vector for the AP starts in the actual Vm trace
    sig_AP_start_index = [sig.time_index(t) for t in ap_fast_rise_start_times]
    
    #### BEGIN Collect AP values
    # See nested BEGIN - END comments for what are these
    
    ap_Vm_onset_values  = None
    ap_Vm_peak_values   = None
    ap_Vm_hmax_values   = None # half-max values
    ap_Vm_qmax_values   = None # quarter-max values (1/4 from threshold)
    ap_Vm_tmax_values   = None # third-max values (1/3 from threshold
    ap_amplitudes       = None
    ap_waveform_signals = None
    
    # ###   BEGIN Collect Vm values at AP onset
    # NOTE: 2019-04-24 14:04:04
    # this signal contains the Vm values at the times of AP onset (as determined
    # at NOTE: 2019-04-25 09:22:13)
    # the actual membrane AP threshold is the first sample in this signal
    #
    # NOTE: 2019-04-25 10:56:45
    # stores Vm values at AP onset times (times of start of the fast rising phase)
    #
    ap_Vm_onset_values = neo.IrregularlySampledSignal(ap_fast_rise_start_times,
                                                      sig.magnitude[sig_AP_start_index],
                                                      units = sig.units, 
                                                      time_units=ap_fast_rise_start_times.units, 
                                                      name="%s_AP_onset_Vm" % sig.name, 
                                                      description = "AP onset Vm for %s signal; dV/dt detection threshold: %g" % (sig.name, thr * pq.V/pq.s))
    
    # ###   END Collect Vm values at AP onset
    
    # ### BEGIN Collect the AP waveforms
    #
    ap_waves = extract_AP_waveforms(sig, iinj, ap_fast_rise_start_times, before=before, after=after, use_min_isi=use_min_detected_isi)
    
    ## ap_waveform_signals is a list of neo.AnalogSignals!
    ap_waveform_signals, inter_AP_intervals, wave_starts, wave_stops = ap_waves
    
    #
    # ### END Collect the AP waveforms
    
    # ### BEGIN Collect AP peak values
    #
    # NOTE: 2019-04-24 14:04:18
    # time points of the AP peaks: the times of the max values in each AP waveform
    #
    #    Each AP waveform is a time slice of the original Vm signal, therefore
    #    the index of the AP waveform argmax() is also the index of the 
    #    peak time in the original signal -- Neat !!!
    #
    # NOTE: 2019-04-24 14:05:15
    # in theory ap_peak_times should be close (if not identical) to
    # ap_rise_stops, but see NOTE: 2019-04-29 11:13:46 for why we don't use that
    #

    # NBOTE: 2019-05-03 13:32:22
    # get the values at the peaks
    ap_peak_values = np.array([w.max() for w in ap_waveform_signals]) * sig.units # must do this because we c'truct a new numpy array!
    
    # NOTE: 2019-04-25 10:58:41
    # store peak values at peak times in an IrregularlySampledSignal
    ap_Vm_peak_values = neo.IrregularlySampledSignal(ap_peak_times, 
                                                     ap_peak_values,
                                                     units = sig.units,
                                                     time_units = sig.times.units,
                                                     name = "%s_AP_peak_values" % (sig.name))
    #
    # ### END Collect AP peak values
    
    # ### BEGIN Collect AP amplitude values
    #
    # we define AP amplitude as the magnitude of the Vm excursion from the 
    # onset value to the peak
    
    # NOTE: 2019-04-23 23:22:09
    # we use the magnitudes instead of the signal themselves because, by design,
    # their time stamps do not coincide (see NOTE: 2019-04-25 10:56:45 and
    # NOTE: 2019-04-25 10:58:41)
    #
    ap_amplitude_values = ap_Vm_peak_values.magnitude - ap_Vm_onset_values.magnitude
    
    # NOTE: 2019-04-25 10:59:17
    # store AP amplitudes at peak times in an IrregularlySampledSignal
    ap_amplitudes = neo.IrregularlySampledSignal(ap_peak_times, 
                                                 ap_amplitude_values,
                                                 units = sig.units,
                                                 time_units = sig.times.units,
                                                 name = "%s_AP_amplitudes" % (sig.name))
    #
    # ### END Collect AP amplitude values
    
    # ### BEGIN Calculate AP durations at various levels
    # 
    # NOTE: 2019-04-30 11:12:42
    # the onset Vm is a sample value (the value of the sample at sig_AP_start_index)
    #   the time of its occurrence on the rising phase is at sig_AP_start_index
    #   the time of its occurrence on the decay phase needs to be determined
    #       by interpolation; however, if the baseline is sliding up, this will
    #       be tricky
    #
    # the half-maximum Vm is calculated, hence the times of its occurrence in 
    #   both rising and decay phases need to be calculated by interpolation
    #
    # The same stands for the 0 Vm (this being a sampled signal, no sample might
    # actually have the value 0 in the data)
    #
    # NOTE: 2019-04-29 15:08:34
    # calcuate the half-maximum value of the Vm = onset + half of amplitude
    # CAUTION: Vm beign a sampled signal, none of its samples may have this
    # CALCULATED value
    #
    #half_max = ap_Vm_onset_values.magnitude + ap_amplitudes.magnitude / 2. # NOT a quantity
    #half_max = ap_amplitudes.magnitude / 2. # NOT a quantity
    half_max = ap_amplitudes / 2. # Quantity array
    
    third_max = ap_amplitudes / 3. # Quantity array
    
    quarter_max = ap_amplitudes / 4.# Quantity array
    
    # NOTE: 2019-04-30 11:08:28
    # Vm values at half max are calculated; to get their time points we need to
    # interpolate on the waveform -- see NOTE: 2019-04-29 15:08:34
    #vm_at_half_max = ap_Vm_onset_values + half_max 
    # need to use their magnitudes because times do not match!
    vm_at_half_max = (ap_Vm_onset_values.magnitude + half_max.magnitude) * sig.units 
    vm_at_quart_max = (ap_Vm_onset_values.magnitude + quarter_max.magnitude) * sig.units 
    vm_at_third_max = (ap_Vm_onset_values.magnitude + third_max.magnitude) * sig.units
    
    # NOTE:2017-09-04 22:09:38
    # we need the time values where the Vm is around half-max on the rising phase
    # and the decaying phase
    #
    # NOTE: 2019-04-25 11:04:35
    # We lookup for Vm samples >= vm_at_half_max value to help us locate the 
    # half-max time points, to help us with interpolation
    #
    # WARNING this MAY slow things down a bit
    times_of_half_max_on_rise = list() # roots of interpolation on rise phases
    times_of_half_max_on_decay = list() # roots of interpolation on decay phases
    
    times_of_quart_max_on_rise = list() # roots of interpolation on rise phases
    times_of_quart_max_on_decay = list() # roots of interpolation on decay phases
    
    times_of_third_max_on_rise = list() # roots of interpolation on rise phases
    times_of_third_max_on_decay = list() # roots of interpolation on decay phases
    
    # ditto for Vm == 0 mV
    times_of_0_vm_on_rise = list()
    times_of_0_vm_on_decay = list()
    
    # ditto for Vm = Vm at onset ("the instantaneous AP threshold")
    times_of_onset_vm_on_rise = list()
    times_of_onset_vm_on_decay = list()
    
    times_of_refVm_on_rise = list()
    times_of_refVm_on_decay = list()
    
    for k, w in enumerate(ap_waveform_signals):
        #print("detect_AP_waveforms_in_train: waveform %d" % k)
        try:
            # NOTE: 2019-04-25 13:48:45
            # and same for Vm == Vm at onset ("instantaneous AP threshold")
            #print("find AP >= onset Vm %s" % ap_Vm_onset_values[k])
            ap_roots_onset =  ap_waveform_roots(w, ap_Vm_onset_values[k])
            rise_onset_Vm_x, rise_onset_Vm_y, rise_onset_slope, decay_onset_Vm_x, decay_onset_Vm_y, decay_onset_slope = ap_roots_onset

            #print("find AP >= Vm half max %s" % vm_at_half_max[k])
            ap_roots_half_max = ap_waveform_roots(w, vm_at_half_max[k])
            hm_rise_x, hm_rise_y, hm_rise_slope, hm_decay_x, hm_decay_y, hm_decay_slope = ap_roots_half_max
            
            # for 1/4 of maximum
            ap_roots_quart_max = ap_waveform_roots(w, vm_at_quart_max[k])
            qm_rise_x, qm_rise_y, qm_rise_slope, qm_decay_x, qm_decay_y, qm_decay_slope = ap_roots_quart_max
            
            ap_roots_third_max = ap_waveform_roots(w, vm_at_third_max[k])
            tm_rise_x, tm_rise_y, tm_rise_slope, tm_decay_x, tm_decay_y, tm_decay_slope = ap_roots_third_max
            
            #print("find AP >= 0 Vm")
            # NOTE: 2019-04-25 13:48:32
            # do the same for Vm = 0 mV
            #rise_0mV_x, decay_0mV_x, rise_0mV_slope, decay_0mV_slope = __wave_interp_root_near_val__(w, 0 * w.units)
            if ap_Vm_onset_values[k] < 0 * w.units:
                rise_0mV_x, rise_0mV_y, rise_0mV_slope, decay_0mV_x, decay_0mV_y, decay_0mV_slope = ap_waveform_roots(w, 0 * w.units)
                
            else:
                rise_0mV_x, rise_0mV_y, rise_0mV_slope, decay_0mV_x, decay_0mV_y, decay_0mV_slope = ap_waveform_roots(w, ap_Vm_onset_values[k])
                
            
            #print("decay_onset_Vm_x", decay_onset_Vm_x)

            if decay_onset_Vm_x is np.nan:
                # waveform is likely on a rising baseline
                # there are two alternative workarounds:
                # (a) extrapolate a straight line from the point on half-max and 
                #   find its intercept with the Vm onset value
                if decay_intercept_approx.strip().lower() == "linear":
                    #print("decay_ref", decay_ref)
                    if isinstance(decay_ref, str):
                        if decay_ref == "hm":
                            #print("hm_decay_slope", hm_decay_slope)
                            decay_onset_Vm_x = (ap_Vm_onset_values.magnitude[k] - vm_at_half_max.magnitude[k]) / hm_decay_slope + hm_decay_x
                            
                        elif decay_ref == "qm":
                            decay_onset_Vm_x = (ap_Vm_onset_values.magnitude[k] - vm_at_quart_max.magnitude[k]) / qm_decay_slope + qm_decay_x
                            
                        else:
                            decay_onset_Vm_x = (ap_Vm_onset_values.magnitude[k] - 0) / decay_0mV_slope + decay_0mV_x
                            
                    else:
                        decay_onset_Vm_x = (ap_Vm_onset_values.magnitude[k] - decay_ref.magnitude) / decay_0mV_slope + decay_0mV_x
                        
                # (b) determine a "pseudo-baseline" and use that as the onset Vm on the 
                # decay side
                else:
                    [lo, hi], _,_,_ = sigp.state_levels(w)
                    _,_,_,decay_onset_Vm_x,decay_onset_Vm_y,decay_onset_slope = ap_waveform_roots(w, lo)
                
                #print("estimated decay_onset_Vm_x", decay_onset_Vm_x)
                
            if isinstance(reference_Vm, pq.Quantity):
                if reference_Vm >= ap_Vm_onset_values[k]:
                    rise_refVm_x, rise_refVm_y, rise_refVm_slope, decay_refVm_x, decay_refVm_y, decay_refVm_slope = ap_waveform_roots(w, reference_Vm)
                    
                    times_of_refVm_on_rise.append(rise_refVm_x)
                    times_of_refVm_on_decay.append(decay_refVm_x)
                    
                else:
                    warnings.warn("cannot measure duration of waveform %d at Vm %s < onset Vm (%s)" % (k, reference_Vm, ap_Vm_onset_values[k]))
                    times_of_refVm_on_rise.append(np.nan)
                    times_of_refVm_on_decay.append(np.nan)
                    
            times_of_half_max_on_rise.append(hm_rise_x) 
            times_of_half_max_on_decay.append(hm_decay_x)

            times_of_quart_max_on_rise.append(qm_rise_x) 
            times_of_quart_max_on_decay.append(qm_decay_x)
    
            times_of_third_max_on_rise.append(tm_rise_x)
            times_of_third_max_on_decay.append(tm_decay_x)
    
            times_of_0_vm_on_rise.append(rise_0mV_x)
            times_of_0_vm_on_decay.append(decay_0mV_x)
            
            times_of_onset_vm_on_rise.append(rise_onset_Vm_x)
            #times_of_onset_vm_on_decay.append(decay_onset_Vm_x)
            
            if isinstance(decay_onset_Vm_x, (tuple, list, np.ndarray)):
                times_of_onset_vm_on_decay.append(decay_onset_Vm_x[0])
            else:
                times_of_onset_vm_on_decay.append(decay_onset_Vm_x)
            
        except Exception as e:
            print("in waveform %d:" % k)
            traceback.print_exc()
            raise e
    
    time_array_half_max_rise = np.array(times_of_half_max_on_rise).flatten() * sig.times.units
    time_array_half_max_decay  = np.array(times_of_half_max_on_decay).flatten() * sig.times.units
    
    time_array_quart_max_rise = np.array(times_of_quart_max_on_rise).flatten() * sig.times.units
    time_array_quart_max_decay  = np.array(times_of_quart_max_on_decay).flatten() * sig.times.units
    
    time_array_third_max_rise = np.array(times_of_third_max_on_rise).flatten() * sig.times.units
    time_array_third_max_decay  = np.array(times_of_third_max_on_decay).flatten() * sig.times.units
    
    time_array_0mV_rise = np.array(times_of_0_vm_on_rise).flatten() * sig.times.units
    time_array_0mV_decay = np.array(times_of_0_vm_on_decay).flatten() * sig.times.units
    
    time_array_onset_Vm_rise = np.array(times_of_onset_vm_on_rise).flatten() * sig.times.units
    #print("times_of_onset_vm_on_decay", times_of_onset_vm_on_decay)
    time_array_onset_Vm_decay = np.array(times_of_onset_vm_on_decay).flatten() * sig.times.units
    
    ap_Vm_hmax_values = neo.IrregularlySampledSignal(time_array_half_max_rise,
                                                     vm_at_half_max,
                                                     time_units = sig.times.units,
                                                     name = "%s_AP_half_max_amplitude" % sig.name,
                                                     description = "AP half-max amplitude for %s signal" % sig.name)
    
    ap_durations_hm = time_array_half_max_decay - time_array_half_max_rise
    
    ap_durations_Vhalf_max = neo.IrregularlySampledSignal(time_array_half_max_rise,
                                                          ap_durations_hm,
                                                          time_units = sig.times.units,
                                                          name = "%s_AP_durations_at_half_max" % sig.name,
                                                          description = "AP durations at half-maximum for %s" % sig.name)
    
    ap_Vm_qmax_values = neo.IrregularlySampledSignal(time_array_quart_max_rise,
                                                     vm_at_quart_max,
                                                     time_units = sig.times.units,
                                                     name = "%s_AP_quart_max_amplitude" % sig.name,
                                                     description = "AP quarter-max amplitude for %s signal" % sig.name)
    
    ap_durations_qm = time_array_quart_max_decay - time_array_quart_max_rise
    
    ap_durations_Vquart_max = neo.IrregularlySampledSignal(time_array_quart_max_rise,
                                                          ap_durations_qm,
                                                          time_units = sig.times.units,
                                                          name = "%s_AP_durations_at_quart_max" % sig.name,
                                                          description = "AP durations at quarter-maximum for %s" % sig.name)
    
    ap_Vm_tmax_values = neo.IrregularlySampledSignal(time_array_third_max_rise,
                                                     vm_at_third_max,
                                                     time_units = sig.times.units,
                                                     name="%s_AP_third_max_amplitude" % sig.name,
                                                          description = "AP third-max amplitude for %s" % sig.name)
    
    ap_durations_tm = time_array_third_max_decay - time_array_third_max_rise
    ap_durations_Vthird_max = neo.IrregularlySampledSignal(time_array_third_max_rise,
                                                          ap_durations_tm,
                                                          time_units = sig.times.units,
                                                          name = "%s_AP_durations_at_third_max" % sig.name,
                                                          description = "AP durations at third-maximum for %s" % sig.name)

    
    ap_durations_0 = time_array_0mV_decay - time_array_0mV_rise
    
    ap_durations_V0 = neo.IrregularlySampledSignal(time_array_0mV_rise, 
                                                   ap_durations_0, 
                                                   time_units = sig.times.units,
                                                   name = "%s_AP_durations_at_0_mV" % sig.name,
                                                   description = "AP durations at 0 mV for %s" % sig.name)
    
    ap_durations_onset_Vm = time_array_onset_Vm_decay - time_array_onset_Vm_rise
    
    #assert(np.all(np.isclose(time_array_onset_Vm_rise.magnitude, ap_fast_rise_start_times.magnitude)))
    
    ap_durations_Vonset = neo.IrregularlySampledSignal(time_array_onset_Vm_rise,
                                                       ap_durations_onset_Vm,
                                                       time_units = sig.times.units,
                                                       name = "%s_AP_durations_at_onset" % sig.name,
                                                       description = "AP durations at onset Vm for %s" % sig.name)
    
    if len(times_of_refVm_on_rise)> 0 and len(times_of_refVm_on_rise) == len(times_of_refVm_on_decay):
        time_array_refVm_rise = np.array(times_of_refVm_on_rise).flatten() * sig.times.units
        time_array_refVm_decay = np.array(times_of_refVm_on_decay).flatten() * sig.times.units
        
        ap_durations_refVm = time_array_refVm_decay - time_array_refVm_rise
        
        ap_durations_Vref = neo.IrregularlySampledSignal(time_array_refVm_rise,
                                                         ap_durations_refVm,
                                                         time_units = sig.times.units,
                                                         name = "%s_AP_durations_at_Reference_Vm" % sig.name,
                                                         description = "AP durations at %s Vm for %s" % (reference_Vm, sig.name))
        
    else:
        ap_durations_Vref = None
        
    # ### END Calculate AP durations at half-max, 0 mV, and onset Vm
    
    # ### BEGIN Collect dV/dt waveforms for each AP, also get maximum value of dV/dt for the waveform. 
    # using the unsmoothed derivative!
    # NOTE: 2017-09-04 21:09:43
    # CAUTION when "after" is None and "use_min_detected_isi" is False, these waveforms
    # will have different durations!
    ap_dvdt_waveform_signals = [dv_dt.time_slice(w.t_start, w.t_stop) for w in ap_waveform_signals]
    
    maxDvDt_index = [w.argmax() for w in ap_dvdt_waveform_signals]
    
    maxDvDt = np.array([w[k] for (w, k) in zip(ap_dvdt_waveform_signals, maxDvDt_index)]) * dv_dt.units
    
    maxDvDt_times = np.array([w.times[k] for (w, k) in zip(ap_dvdt_waveform_signals, maxDvDt_index)]) * dv_dt.times.units
    
    ap_max_dvdt = neo.IrregularlySampledSignal(maxDvDt_times,
                                               maxDvDt,
                                               units = dv_dt.units,
                                               time_units = sig.times.units,
                                               name = "%s_Max_AP_dV/dt" % sig.name,
                                               description = "Maximum AP rate of change for %s" % sig.name)
    
    # ### END Collect dV/dt for each AP, get maximum value of dV/dt for the waveform.
    
    # NOTE: 2019-04-24 15:19:22
    # ### BEGIN store the second derivative wave forms (also unsmoothed)
    # same algorithm and CAUTION as per NOTE: 2017-09-04 21:09:43
    ap_d2vdt2_waveform_signals = [d2v_dt2.time_slice(w.t_start, w.t_stop) for w in ap_waveform_signals]
    
    #
    # END store the second derivative wave forms
    
    # NOTE: 2019-04-25 10:31:00
    # The way neo.SpikeTrain has been designed, I understand, requires that
    # the waveforms is an array where the first axis is along the index of the spike
    # 
    if len(ap_waveform_signals) > 1:
        # NOTE: 2019-05-03 13:32:58
        # CAUTION see NOTE: 2017-09-04 21:09:43
        # when using the actual inter-AP interval to extract the AP waveforms,
        # these will have different lengths, so we will need to pad them at the
        # end with np.nan
        if all([w.size == ap_waveform_signals[0].size for w in ap_waveform_signals]):
            waveform_length = len(ap_waveform_signals[0])
            
            maxWaveformLength = waveform_length
            
            ap_waveforms = np.concatenate([w.magnitude.T for w in ap_waveform_signals], axis=0)
            #ap_waveforms = np.concatenate([w.magnitude for w in ap_waveform_signals], axis=1)
            ap_wave_times = np.linspace(0, ap_waveform_signals[0].duration.magnitude, num=len(ap_waveform_signals[0])) * sig.times.units
            
        else: # trouble!
            maxWaveformLength = np.max([len(w) for w in ap_waveform_signals])

            #ap_waveforms = np.full([maxWaveformLength, len(ap_waveform_signals)], np.nan)
            ap_waveforms = np.full([len(ap_waveform_signals), maxWaveformLength], np.nan)
            
            for k, w in enumerate(ap_waveform_signals):
                ap_waveforms[k, 0:w.size] = w.magnitude[:,0].copy()
                
            ap_wave_times = np.linspace(0, maxWaveformLength * sig.sampling_period.magnitude, num = maxWaveformLength) * sig.times.units
            
    else:
        ap_waveforms = ap_waveform_signals[0].magnitude.T
        ap_wave_times = np.linspace(0, ap_waveform_signals[0].duration.magnitude, num=len(ap_waveform_signals[0])) * sig.times.units
        maxWaveformLength = np.nan

    # spike train where eack "spike" is the beginning of the waveform 
    # "CONTAINING" a single AP
    #
    # NOTE: CAUTION: these times MAY be the beginning of the AP waveform 
    # itself if the "before" argument is set to 0; else, they PRECEDE the
    # the beginning of the actual AP waveform by an interval equal to 
    # before (in s)
    #
    if len(ap_fast_rise_start_times):
        ap_train = neo.SpikeTrain(ap_fast_rise_start_times,
                                t_start = t_start,
                                t_stop = t_stop,
                                left_sweep = ap_fast_rise_start_times - sig.t_start,
                                sampling_rate = sig.sampling_rate,
                                name="%s_AP_train" % (sig.name),
                                description = "AP train for %s signal; dV/dt detection threshold: %g" % (sig.name, thr * pq.V/pq.s))
    
        ap_train.waveforms = ap_waveforms
    
        train_annotations["AP_peak_values"]          = ap_Vm_peak_values
        train_annotations["AP_peak_amplitudes"]      = ap_amplitudes
        train_annotations["AP_onset_Vm"]             = ap_Vm_onset_values # Vm value at ap_fast_rise_start_times
        train_annotations["AP_durations_V_onset"]    = ap_durations_Vonset
        train_annotations["AP_half_max"]             = ap_Vm_hmax_values
        train_annotations["AP_durations_V_half_max"] = ap_durations_Vhalf_max
        train_annotations["AP_quart_max"]            = ap_Vm_qmax_values
        train_annotations["AP_durations_V_quart_max"]= ap_durations_Vquart_max
        train_annotations["AP_third_max"]            = ap_Vm_tmax_values
        train_annotations["AP_durations_V_third_max"]= ap_durations_Vthird_max
        train_annotations["AP_durations_V_0"]        = ap_durations_V0
        train_annotations["AP_ref_Vm"]               = reference_Vm
        train_annotations["AP_durations_at_Ref_Vm"]  = ap_durations_Vref
        train_annotations["AP_Maximum_dV_dt"]        = ap_max_dvdt
        train_annotations["AP_waveform_times"]       = ap_wave_times
        train_annotations["AP_dV_dt_waveforms"]      = ap_dvdt_waveform_signals
        train_annotations["AP_d2V_dt2_waveforms"]    = ap_d2vdt2_waveform_signals
    
    ap_train.annotations.update(train_annotations)
    
    # print(f"detect_AP_waveforms_in_train ap_train t_start {ap_train.t_start} t_stop {ap_train.t_stop}")
    
    return ap_train, ap_waveform_signals
        
def ap_duration_at_Vm(ap, value, **kwargs): #decay_ref, decay_intercept_approx="linear", interpolate=False):
    """Returns the duration of the AP waveform at given Vm value
    
    Parameters:
    -----------
    
    ap: neo AnalogSignal
    
        The AP waveform
        
    value: float or quantity scalar
    
        value of the AP waveform where its duration is required
        
    Var-keyword parameters:
    ----------------------
    decay_intercept_approx: str: one of "linear" or "levels"
    
    decay_ref: scalar float or Quantity
        used when the waveform decay phase does not reach the specified value
        AND decay_intercept_approx is "linear"
        
    interpolate: boolean, default is True
        When True (default) the function uses linear interpolation to determine t
        he waveform intercept with the specified Vm value
        
        When False, the function returns coordinates of the sample points of the 
        waveform region >= value, that are nearest to the intercept with value.
        
    Returns:
    -------
    ret: databag
    
    """
    
    interpolate = kwargs.pop("interpolate", True)
    
    decay_intercept_approx = kwargs.pop("decay_intercept_approx", "levels")
    
    decay_ref = kwargs.pop("decay_ref", None)
    
    if decay_intercept_approx == "linear":
        if isinstance(decay_ref, numbers.Real):
            decay_ref *= ap.units
            
        elif isinstance(decay_ref, pq.Quantity):
            if not units_convertible(decay_ref, ap.units):
                raise TypeError("decay_ref has incompatible units (%s)" % decay_ref.units.dimensionality)
            
            if decay_ref.units != ap.units:
                decay_ref = decay_ref.rescale(ap.units)
                
        else:
            raise TypeError("When decay_intercept_approx is 'linear' then 'decay_ref' if expected to be a scalar or a Quantity")
        
    if isinstance(ap, neo.AnalogSignal):
        if isinstance(value, numbers.Real):
            value *= ap.units
            
        elif isinstance(value, pq.Quantity):
            if not units_convertible(value, ap.units):
                raise TypeError("value units (%s) not convertible to signal's units (%s)" % (value.units.dimensionality, ap.units.dimensionality))
            
            value = value.rescale(ap.units)
            
    else:
        raise TypeError("ap must be an AnalogSignal; got %s instead" % type(ap).__name__)
            
            
    rise_time, rise_value, rise_slope, decay_time, decay_value, decay_slope = ap_waveform_roots(ap, value, interpolate=interpolate)
    
    if decay_time is np.nan:
        if decay_intercept_approx.strip().lower() == "linear":
            ref_rise_time, ref_rise_value, ref_rise_slope, ref_decay_time, ref_decay_value, ref_decay_slope = ap_waveform_roots(ap, decay_ref, interpolate=interpolate)
            
            decay_time = (value - ref_decay_value)/ref_decay_slope + ref_decay_time
            
        else:
            [lo, hi], _, _, _ = sigp.state_levels(ap)
            _,_,_, decay_time, decay_value, decay_slope = ap_waveform_roots(ap, lo, interpolate=interpolate)
            
    ret = dt.DataBag()
    
    ret.duration = decay_time - rise_time
    ret.value_rise = rise_value
    ret.time_rise = rise_time
    ret.value_decay = decay_value
    ret.time_decay = decay_time
    ret.value = value
    
    return ret

def ap_phase_plot_data(vm, dvdt=None, smooth_window=None):
    """Creates a DataSignal for a phase plot.
    """
    from scipy.signal import boxcar
    
    if not isinstance(vm, neo.AnalogSignal):
        raise TypeError("Expecting a neo.AnalogSignal object; got %s instead" % (type(vm).__name__))
    
    if not units_convertible(vm.units, pq.V):
        warnings.warn("'vm' this does not seem to contain a Vm signal")
    
    if vm.ndim > 2 or (vm.ndim == 2 and vm.shape[1] > 1):
        raise ValueError("Cannot operate on signal with %d dimensions " % (vm.ndim))
    
    if isinstance(smooth_window, int) and smooth_window > 0:
        h = boxcar(smooth_window)/smooth_window
        
    else:
        h = None
        
    if dvdt is None:
        dvdt = sigp.ediff1d(vm).rescale(pq.V/pq.s)
        
        if h is not None:
            dvdt = sigp.convolve(dvdt, h)
            
    ret = IrregularlySampledDataSignal(vm.magnitude * vm.units, 
                                          dvdt.magnitude * dvdt.units, 
                                          name="dV/dt",
                                          description="Phase plot data of %s" % vm.name)
    
    ret.domain_name = "Vm"
    
    
    return ret


def analyse_AP_waveform(vm, dvdt=None, d2vdt2=None, ref_vm = None, ref_vm_relative_onset=False, atol=1e-8, smooth_window = None,detect_times=True, dvdt_thr=10):
    """ AP waveform analysis for APs triggered by individual current pulses.
    
    WARNING: only to be used on isolated AP waveforms, obtained by calling
    extract_pulse_triggered_APs()
                
    Returns:
    ----------
    ap_amplitude,
    ap_onset_vm, 
    ap_onset_time, 
    ap_half_max,
    ap_half_max_time,
    ap_peak_vm, 
    ap_peak_time, 
    ap_fast_rise_end, 
    ap_fast_rise_end_time
    phase_plot
    dvdt
    d2vdt2
    """
    from scipy.signal import boxcar

    if not isinstance(vm, neo.AnalogSignal):
        raise TypeError("Expecting a neo.AnalogSignal object; got %s instead" % (type(vm).__name__))
    
    if not units_convertible(vm.units, pq.V):
        warnings.warn("this does not seem to be a Vm signal")
    
    if vm.ndim > 2 or (vm.ndim == 2 and vm.shape[1] > 1):
        raise ValueError("Cannot operate on signal with %d dimensions " % (vm.ndim))
    
    if isinstance(smooth_window, int) and smooth_window > 0:
        h = boxcar(smooth_window)/smooth_window
        
    else:
        h = None
        
    if dvdt is None:
        dvdt = sigp.ediff1d(vm).rescale(pq.V/pq.s)
        
        if h is not None:
            dvdt = sigp.convolve(dvdt, h)
            
    if isinstance(dvdt_thr, numbers.Real):
        dvdt_thr *= dvdt.units
        
    elif isinstance(dvdt_thr, pq.Quantity):
        if not units_convertible(dvdt_thr, dvdt.units):
            raise TypeError("'dvdt_thr' expected to have %s units; got %s instead" % (dvdt.units.dimensionality, dvdt_thr.units.dimensionality))
        
        dvdt_thr = dvdt_thr.rescale(dvdt.units)

    if d2vdt2 is None:
        d2vdt2 = sigp.ediff1d(dvdt).rescale(pq.V/(pq.s**2))
        
        if h is not None:
            d2vdt2 = sigp.convolve(d2vdt2, h)
    
    dvdt_ge_thr = dvdt >= dvdt_thr
    
    dvdt_ge_thr_start_flags = np.ediff1d(np.asfarray(dvdt_ge_thr), to_begin=0) == 1
    
    dvdt_ge_thr_stop_flags = np.ediff1d(np.asfarray(dvdt_ge_thr), to_begin=0) == -1
    
    fast_rise_start_times = vm.times[dvdt_ge_thr_start_flags]
    
    ####
    
    ap_onset_time = np.array([fast_rise_start_times[0]]).flatten() * vm.times.units
    
    ap_onset_vm = vm[vm.time_index(ap_onset_time)].flatten()
    
    ap_peak_vm = np.array([vm.max()]).flatten() * vm.units
    
    ap_peak_time = np.array([vm.times[vm.argmax()]]).flatten() * vm.times.units
    
    ap_amplitude = ap_peak_vm - ap_onset_vm
    
    ap_half_max = ap_onset_vm + (ap_amplitude/2)
    
    ap_quarter_max = ap_onset_vm + (ap_amplitude/4)
    
    half_max_duration_result = ap_duration_at_Vm(vm, ap_half_max)
    
    quarter_max_duration_result = ap_duration_at_Vm(vm, ap_quarter_max)
    
    vm_0_duration_result = ap_duration_at_Vm(vm, 0)
    
    onset_duration_result = ap_duration_at_Vm(vm, ap_onset_vm)
    
    fast_rise_stop_index = dvdt.argmax()
    
    ap_fast_rise_end = vm[fast_rise_stop_index].flatten()
    
    ap_fast_rise_end_time = np.array([vm.times[fast_rise_stop_index]]).flatten() * vm.times.units
    
    result = dt.DataBag()
    
    result.amplitude = ap_amplitude
    result.onset = ap_onset_vm
    result.onset_time = ap_onset_time
    result.is_sd = ap_fast_rise_end
    result.is_sd_time = ap_fast_rise_end_time
    result.peak = ap_peak_vm
    result.peak_time = ap_peak_time
    
    result.vm_0_duration = (np.array([vm_0_duration_result.duration]).flatten() * vm.times.units).rescale(pq.ms)
    result.vm_0_rise_value = np.array([vm_0_duration_result.value_rise]).flatten() * vm.units
    result.vm_0_rise_time = np.array([vm_0_duration_result.time_rise]).flatten() * vm.times.units
    result.vm_0_decay_value = np.array([vm_0_duration_result.value_decay]).flatten() * vm.units
    result.vm_0_decay_time = np.array([vm_0_duration_result.time_decay]).flatten() * vm.times.units

    result.half_max = ap_half_max
    
    result.half_max_duration = (np.array([half_max_duration_result.duration]).flatten() * vm.times.units).rescale(pq.ms)
    result.half_max_rise_value = np.array([half_max_duration_result.value_rise]).flatten() * vm.units
    result.half_max_rise_time = np.array([half_max_duration_result.time_rise]).flatten() * vm.times.units
    result.half_max_decay_value = np.array([half_max_duration_result.value_decay]).flatten() * vm.units
    result.half_max_decay_time = np.array([half_max_duration_result.time_decay]).flatten() * vm.times.units
    
    result.quarter_max = ap_quarter_max
    
    result.quarter_max_duration = (np.array([quarter_max_duration_result.duration]).flatten() * vm.times.units).rescale(pq.ms)
    result.quarter_max_rise_value = np.array([quarter_max_duration_result.value_rise]).flatten() * vm.units
    result.quarter_max_rise_time = np.array([quarter_max_duration_result.time_rise]).flatten() * vm.times.units
    result.quarter_max_decay_value = np.array([quarter_max_duration_result.value_decay]).flatten() * vm.units
    result.quarter_max_decay_time = np.array([quarter_max_duration_result.time_decay]).flatten() * vm.times.units
    
    result.max_dv_dt = np.array([dvdt.max()]).flatten() * dvdt.units
    
    
    #print("analyse_AP_waveform: ref_vm", ref_vm)
    
    if ref_vm is not None:
        if isinstance(ref_vm, numbers.Real):
            ref_vm *= vm.units
            
        elif isinstance(ref_vm, pq.Quantity):
            if not units_convertible(ref_vm, vm.units):
                raise TypeError("ref_vm has wrong units: %s" % ref_vm.units.dimensionality)
            
            #print("analyse_AP_waveform vm.units", vm.units)
            #print("analyse_AP_waveform ref_vm.units", ref_vm.units)
            
            if ref_vm.units != vm.units:
                #print("rescaling ref_vm")
                ref_vm = ref_vm.rescale(vm.units)
                
        else:
            raise TypeError("ref_vm must be a float, Quantity, or None; got %s instead" % type(ref_vm).__name__)
        
        if ref_vm_relative_onset:
            ref_vm = result.onset[0] + ref_vm
            # NOTE: 2019-06-23 22:40:47
            # don't do ref_vm += result.onset[0], as it seems to multiply the values !!!
            # bug in quantities?
            
            #print("analyse_AP_waveform: onset", result.onset)
            #print("analyse_AP_waveform: (relative) ref_vm", ref_vm)
        
        ref_vm_duration_result = ap_duration_at_Vm(vm, ref_vm)
        
        result.ref_vm = np.array([ref_vm]).flatten() * vm.units
        result.ref_vm_duration = (np.array([ref_vm_duration_result.duration]).flatten() * vm.times.units).rescale(pq.ms)
        result.ref_vm_rise_value = np.array([ref_vm_duration_result.value_rise]).flatten() * vm.units
        result.ref_vm_rise_time = np.array([ref_vm_duration_result.time_rise]).flatten() * vm.times.units
        result.ref_vm_decay_value = np.array([ref_vm_duration_result.value_decay]).flatten() * vm.units
        result.ref_vm_decay_time = np.array([ref_vm_duration_result.time_decay]).flatten() * vm.times.units
        
    else:
        result.ref_vm = None
        result.ref_vm_duration = None
        result.ref_vm_rise_value = None
        result.ref_vm_rise_time = None
        result.ref_vm_decay_value = None
        result.ref_vm_decay_time = None
        
    
    result.vm = vm
    result.dvdt = dvdt
    result.d2vdt2 = d2vdt2
    result.phase_plot = ap_phase_plot_data(vm, dvdt)
    
    return result
    
def collect_Iclamp_steps(block, VmSignal = "Vm_prim_1", ImSignal = "Im_sec_1", head = 0.05 * pq.s, tail = 0.05 * pq.s, name=None, segments=None):
    """Generates an segment from step current step injections in I-clamp experiments.
    Useful or stack-plotting.
    
    Arguments:
    ==========
    
    bloc : a neo.Block where each segment contains at least one VM an one Im analog signals
    
    VmSignal: integral index or name of the Vm analog signal
    
    ImSignal: integral index or name of the Im analog signal
    
    head, tail: scalar python time quantities indicating, respectively, the 
        signal intervals before and after the actual step current injection that
        should be included in the plot.
    
    segments: index into the segments taken into account (optional,  default is 
        None, meaning that ALL segments ate takein into account)
        can be:
            integral scalar : 0 <= segments <= len(block.segments)
            
            tuple or list of scalars as above (pick selected segments)
            
            range or slice, both valid given the number of segments in the block
    
    NOTE: The following assumptions are made:
    
    1) all segments have signals with the same name and stored in the same order
       in their "analogsignals" filed. This condition is satisfied when all segments 
       have been acquired within the same experiment run.
        
    2) all analog signals have been acquired with the same samping rate
    
    3) all analog signals have the same duration
    
    4) all analog signals have a singe channel; this condition is usually 
        satisfied when data was acquired with Clampex or Signal5
        
    """
    if not isinstance(block, neo.Block):
        raise TypeError("A neo.Block object was expected; got %s instead" % type(block).__name__)
    
    if len(block.segments) == 0:
        raise ValueError("There are no segments in the block")
    
    if isinstance(VmSignal, str):
        VmSignal = neoutils.get_index_of_named_signal(block.segments[0], VmSignal)
        
    if isinstance(ImSignal, str):
        ImSignal = neoutils.get_index_of_named_signal(block.segments[0], ImSignal)
        
        
    #times = None
    
    if isinstance(head, numbers.Number):
        head *= pq.s
        
    elif isinstance(head, pq.Quantity) and head.units.dimensionality != pq.s.units.dimensionality:
        head = head.magnitude * pq.s
    
    if isinstance(tail, numbers.Number):
        tail *= pq.s
    
    elif isinstance(tail, pq.Quantity) and tail.units.dimensionality != pq.s.units.dimensionality:
        tail = tail.magnitude * pq.s
        
    if name is None:
        cframe = inspect.getouterframes(inspect.currentframe())[1][0]
        try:
            for (k,v) in cframe.f_globals.items():
                if not type(v).__name__ in ("module","type", "function", "builtin_function_or_method"):
                    if v is block and not k.startswith("_"):
                        name = k
        finally:
            del(cframe)
            
    if segments is None:
        sgm = block.segments
        
    elif isinstance(segments, (tuple, list, np.ndarray)):
        if all([isinstance(s, number.Integral) and s >= 0 and s < len(block.segments) for s in segments]):
            sgm = [block.segments[k] for k in segments]
        else:
            raise ValueError("Invalid segment index: expected either None, " + \
                            "an integer, a sequence of integers, a range or a slice, " + \
                            "all in the interval [0:%d)." % len(block.segments))
        
    elif isinstance(segments, numbers.Integral) and segments >= 0 and segments < len(block.segments):
        sgm = [block.segments[segments]]
        
    elif isinstance(segments, range) and segments.start >= 0 and segments.stop <= len(block.segments):
        sgm = [block.segments[k] for k in segments]
        
    elif isinstance(segments, slice) and segments.start >= 0 and segments.stop <= len(block.segments):
        sgm = block.segments[segments]
        
    else:
        raise TypeError("Invalid segment index: expected either None, " + \
                        "an integer, a sequence of integers, a range or a slice, " + \
                        "all in the interval [0:%d)." % len(block.segments))
    
    
    #if isinstance(ImSignal, tuple):
        #if len(ImSignal) != len(sgm):
            #raise ValueError(f"When a tuple, ImSignal must contain {len(sgm)} segments for this data")
    
    i_steps = list()
    v_steps = list()
    
    
        
    for k, segment in enumerate(sgm):
        im = segment.analogsignals[ImSignal]
        vm = segment.analogsignals[VmSignal]
        if isinstance(im, neo.AnalogSignal):
            d,u,_,_,_ = sigp.parse_step_waveform_signal(im)
            
            start_stop = list((d,u))

            start_stop.sort()
            
        else:
            start_stop = im[1:]
            
        start_stop[0] -= head
        start_stop[1] += tail
        
        if start_stop[0] < im.t_start: # FIXME if this happens then we're in trouble
            start_stop[0] = im.t_start
            
        if start_stop[1] > im.t_stop: # FIXME if this happens then we're in trouble
            start_stop[1] = im.t_stop
            
        vstep = vm.time_slice(start_stop[0], start_stop[1]).copy() # so that block stays unchanged
        v_steps.append(vstep.magnitude)
        
        istep = im.time_slice(start_stop[0], start_stop[1]).copy() # avoid references
        i_steps.append(istep.magnitude)
            
        
        # reset the time domain, but use the same units else this breaks the AnalogSignal API
        #istep.t_start = 0 * istep.times.units
        #vstep.t_start = 0 * vstep.times.units
        
        
    i_steps_signal = neo.AnalogSignal(np.concatenate(i_steps, axis=1), \
                                    units = block.segments[0].analogsignals[ImSignal].units, \
                                    t_start = 0 * block.segments[0].analogsignals[ImSignal].times.units, \
                                    sampling_rate = block.segments[0].analogsignals[ImSignal].sampling_rate, \
                                    name = block.segments[0].analogsignals[ImSignal].name, \
                                    description = "Step current injection")
    
    v_steps_signal = neo.AnalogSignal(np.concatenate(v_steps, axis=1), \
                                    units = block.segments[0].analogsignals[VmSignal].units, \
                                    t_start = 0 * block.segments[0].analogsignals[VmSignal].times.units, \
                                    sampling_rate = block.segments[0].analogsignals[VmSignal].sampling_rate, \
                                    name = block.segments[0].analogsignals[VmSignal].name, \
                                    description = "Membrane voltage dring step current injection")
        
    ret = neo.Segment(name = name, description = "Overlaid step current injection sweeps for %s" % name)
    
    ret.analogsignals.append(v_steps_signal)
    ret.analogsignals.append(i_steps_signal)
    
    return ret



def analyse_AP_step_injection_series(data, **kwargs):
    """ Action potential (AP) detection and analysis in I-clamp experiment.
    
    Detects and analyses action potentials (AP) fired during depolarizing current
    injections in current clamp.
    
    The record may contain several sweeps where the current injection amplitude
    is varied progressively (typically incremented by the same amount from an 
    inital value).
    
    The current injection occurs during a defined time interval starting at the  
    same time relative to the beginning of the sweep, and of identical duration
    all sweeps.
    
    In each sweep, action potentials are detected in the signal containing the 
    recorded membrane voltage, during the time interval (or time slice) 
    corresponding to the current injection.
    
    The current injection waveform can be recoded alongside the membrane voltage.
    
    When available, the current injection signal must be present in all sweeps
    and is used to determine the amplitude, onset and duration of the current 
    injection "step".
    
    Alternatively, the current injection amplitude(s) and time interval must be
    specified using the following parameters:
    
    * for current injection amplitude:
        'Iinj_0' and 'delta_I' (initial amplitude and increment from one sweep 
            to the next)
            
        or:
        
        'Iinj': a sequence of current injection amplitudes - the length of the 
        sequemce must equal the number of sweeps (i.e. neo.Segment objects) in
        the data.
        
    * for current injection time interval:
        Istart, Istop (int for samples, or python Quantity in time units)
        
        NOTE 1: it is assumed that current injection starts at the same time
        relative to the beginning of the sweep, in all sweeps.
        
        NOTE 2: when all sweeps start at the same time, Istart and Istop may be
        specified in absolute time values (and pass Itimes_relative = False)
    
    Parameters:
    ----------
    data : neo.Block, list of neo.Segment, or a neo.Segment.
        Contains the recording from one run of a series of depolarizing current 
            injections steps (one rectangular current injection pulse - or step
            followed by return to initial condition).
            
        NOTE 3: one neo.Segment corresponds to one "sweep" in the experiment.
            
        When data is a neo.Block or a list of neo.Segment objects, with each 
        segment containing one epoch of depolarizing current injection.
        
        When data is a single neo.Segment, this contains data from a single step 
        current injection with the same meaning as above.
        
        The signal data is stored in the segments' 'analogsignals' attribute, 
        containing the recorded membrane voltage signal and, optionally, the
        signal with the recorded current injection waveform.
        
        When data has several segments and the signals are specified using 
        integer indices, the membrane voltage and the optional current injection
        signals MUST have the same index in the 'analogsignals' attribute of the
        segments.
        
        
    Var-keyword parameters (kwargs):
    --------------------------------
    VmSignal: int or str; index or name of the Vm analog signal
        integer index, or name (string) of the Vm analog signal
        NOTE: the index is the signal's index in the segments' 'analogsignals'
        attribute (a list of AnalogSignal objects)
        
    ImSignal: int or str; index or name of the Im analog signal; optional, 
        default is None
        NOTE: the index has the same meaning as above.
        
    Iinj_0: python quantity (pA), float scalar, or None: amplitude of the first 
        current injection in the series; optional default is None.
    
        NOTE: When None, the value of the first will be determined from the Im 
        signal of the segment
    
    delta_I: python quantity (pA), float scalar, or None; current injection 
        increment. ΔI
        When None (defaut) the value will be determined from the Im signal
        
    Istart, Istop: time quantities for current step injection, or None
        When given, all segments in the block must start at the same time
    
    Itimes_relative:bool, default is True; 
        When True, then Istart and Istop are considered RELATIVE to the sweep's 
        t0, in every sweep (this is the default, because usually Istart and Istop
        are given in the protocol configuration, where the times are always 
        relative to the start of the sweep).
        
        When False and Istart and Istop are specified then all sweeps must start
        at the same time t0.
        
    Itimes_samples: bool, default is False; when True, this flag indicates that
        Istart and Istop (when given) are numbers of samples (form the start of
        the sweep).
        
    Iinj: None (default), or sequence of current injection values. When not None,
        this must contain as many elements as injection steps, and these must be
        python quantities in units compatible with pA
        
    rheo: boolean, default True
    
        When True, the function attempts to calculate the rheobase & membrane
        time constant using rheobase_latency() function.
        
        This assumes that data is a neo.Block or a sequence of neo.Segment
        containing records of different current injection step amplitudes
        (one segment for each value of depolarizing current intensity).
        
        This parameter is ignored when data has lees than minsteps segments
        
    minsteps: int (default is 3)
        minimum number of curent injection steps where APs were triggered, for
        performing rheobase-latency analysis
        
    thr : float or python Quantity
        value of the dV/dt (in V/s) above which the waveform belongs to an AP.
        optional; default is 20 V/s
    
    plot_rheo: boolean, default is True 
        (plots the fitted curve) -- useful when a block or a list of segments is
        analyzed 
        
    Var-keyword parameters passed on to analyse_AP_step_injection_sweep():
    ----------------------------------------------------------------
    tail: scalar Quantity (units: "s"); default is 0 s
        duration of the analyzed Vm trace after current injection has ceased
    
    
    resample_with_period: None (default), scalar float or Quantity
        When not None, the Vm signal will be resampled before processing.
        
        When Quantity, it must be in units convertible (scalable) to the signal's
        sampling period units.
        
        Resampling occurs on the region corresponding to the depolarizing current
        injection, before detection of AP waveforms.
        
        Upsampling might be useful (see Naundorf et al, 2006) but slows down
        the execution. To upsample the Vm signal, pass here a value smaller than
        the sampling period of the Vm signal.
        
    resample_with_rate: None (default), scalar float or Quantity
        When not None, the Vm signal will be resampled before processing.
        
        When Quantity, it must be in units convertible (scalable) to the signal's
        sampling rate units.
        
        Resampling occurs on the region corresponding to the depolarizing current
        injection, before performing detection of AP waveforms.
        
        Upsampling might be useful (see Naundorf et al, 2006) but slows down
        the execution. To upsample the Vm signal, pass here a value larger than 
        the sampling period of the Vm signal.
        
    box_size: int >= 0; default is 0.
    
        size of the boxcar (scipy.signal.boxcar) used for filtering the Im signal
        (containing the step current injection) before detecting the step 
        boundaries (start & stop)
        
        default is 0 (no boxcar filtering)
        
    method: str, one of "state_levels" (default) or "kmeans": method for detection
        "up" vs "down" states of the step current injection waveform
    
    adcres, adcrange, adcscale: float scalars, see signalprocessing.state_levels()
        called from signalprocessing.parse_step_waveform_signal() 
        
        Used only when method is "state_levels"
        
    thr: floating point scalar: the minimum value of dV/dt of the Vm waveform to
        be considered an action potential (default is 10) -- parameter is passed to detect_AP_waveforms_in_train()
        
    before, after: floating point scalars, or Python Quantity objects in time 
        units convertible to the time units used by VmSignal.
        interval of the VmSignal data, respectively, before and after the actual
        AP in the returned AP waveforms -- parameters are passed to detect_AP_waveforms_in_train()
        
        defaults are:
        before: 1e-3
        after: None
        
    min_fast_rise_duration : None, scalar or Quantity (units "s");
    
        The minimum duration of the initial (fast) segment of the rising 
        phase of a putative AP waveform.
        
        When None, is will be set to the next higher power of 10 above the sampling period
        of the signal.
    
    min_ap_isi : None, scalar or Quantity;
    
                Minimum interval between two consecutive AP fast rising times 
                ("kinks"). Used to discriminate against suprious fast rising time
                points that occur DURING the rising phase of AP waveforms.
                
                This can happen when the AP waveforms has prominent IS and the SD 
                "spikes", 
                
                see Bean, B. P. (2007) The action potential in mammalian central neurons.
                Nat.Rev.Neurosci (8), 451-465

    rtol, atol: float scalars;
        the relative and absolute tolerance, respectively, used in value 
        comparisons (see numpy.isclose())
        
        defaults are:
        rtol: 1e-5
        atol: 1e-8
                
    use_min_detected_isi: boolean, default True
    
        When True, individual AP waveforms cropped from the Vm signal "sig" will
            have the duration equal to the minimum detected inter-AP interval.
        
        When False, the durations of the AP waveforms will be taken to the onset
            of the next AP waveform, or the end of the Vm signal
            
    smooth_window: int >= 0; default is 5
        The length (in samples) of a smoothing window (boxcar) used for the 
        signal's derivatives.
        
        The length of the window will be adjusted if the signal is upsampled.
        
    interpolate_roots: boolean, default False
        When true, use linear inerpolation to find the time coordinates of the
        AP waveform rise and decay phases crossing over the onset, half-maximum
        and 0 mV. 
        
        When False, use the time coordinate of the first & last sample >= Vm value
        (onset, half-max, or 0 mV) respectively, on the rise and decay phases of
        the AP waveform.
        
        see ap_waveform_roots()
        
    decay_intercept_approx: str, one of "linear" (default) or "levels"
        Used when the end of the decay phase cannot be estimated from the onset
        Vm.
        
        The end of the decay is considerd to be the time point when the decaying
        Vm crosses over (i.e. goes below) the onset value of the action potential.
        
        Whe the AP waveform is riing on a rising baseline, this time point cannot
        be determined.
        
        Instead, it is estimated as specified by "decay_intercept_approx" parameter:
        
        When decay_intercept_approx is "linear", the function uses linear extrapolation
        from a (higher than Vm onset) value specified by decay_ref (see below)
        to the onset value.
        
        When decay_intercept_approx is "levels", the function estimates a "pseudo-baseline"
        as the lowest of two state levels determined from the AP waveform histogram.
        
        The pseudo-baseline is then used to estimate the time intercept on the decay
        phase.
        
    decay_ref: str, one of "hm" or "zero", or floating point scalar
        Which Vm value should be used to approximate the end of the decay phase
        when using the "linear" approximation method (see above)
        
    get_duration_at_Vm: also get AP waveform duration at specified Vm,
        (in addition to Vhal-max and V0)
            default: -15 mV
            
    vm_thr: scalar, optional (default is 0) - discard Vm events that do not cross
        this value, see detect_AP_rises
        
        This parameter prevents the fast passive rising phase of the Vm at the
        start of current injection from being flagged as an AP (and similarly, 
        for other fast-rising events)
        

    NOTE: See analyse_AP_step_injection_sweep() documentation for details
    
    Var-keyword parameters related to the experiment "metadata"
    -----------------------------------------------------------
    cell: str (default, "NA")
        Cell ID
        NOTE: Case-sensitive
        
    source: str (default, "NA")
        Source ID (e.g. animal)
        NOTE: Case-sensitive
        
    genotype: str (default "NA")
        genotype (e.g., WT, HET, HOM or any other appropriate string)
        NOTE: Case-sensitive
        
    sex: str (default "M")
        sex: either "F" or "M"
        NOTE: Case-insensitive
        
    treatment: str (default "veh") ATTENTION: case-sensitive!
        
    age: python Quantity (one of days, months, years), "NA" or None 
        Default is None; either None or "NA" result in the string "NA" for age
        
    post_natal: bool (default True)
    
    name: str
        name of the results (string), or None; 
        optional; default is None
        
    
    Returns (see also 'Side effects', below):
    -----------------------------------------
    ret: ordered dict with the following key/value pairs:
    
        "Name": str or None; 
            the name parameter
            
        "Segment_k" where k is a running counter (int): a dictionary with the
            following key/value pairs:
            
            "Name": the name of the kth segment
            
            "AP_analysis": the result returned by calling analyse_AP_step_injection_sweep on
                the kth segment
            
            "Vm_signal": the region of the Vm signal in the kth segment, that 
                has been analyzed (possibly, upsampled); this corresponds to the
                current injection step or longer as specified by the "tail" 
                parameter to the analyse_AP_step_injection_sweep function, so it is usually only
                a time slice of the original Vm signal.
        
        ret["Injected_current"] : neo.IrregularlySampledSignal
            The intensity of the injected current step, one per segment.
                                            
        ret["Reference_AP_threshold"] : neo.IrregularlySampledSignal
            values of Vm at AP threshold, one per segment.
            
        ret["Reference_AP_latency"] : neo.IrregularlySampledSignal
            the latency of the first AP detected (time from start of step 
            current injection), one per segment.
            
        ret["Mean_AP_Frequency"] : neo.IrregularlySampledSignal
            mean AP frequency (ie. number of APs / duration of the current injection
            step, expressed in Hz), one for each segment,
            
        ret["Inter_AP_intervals"] : list of arrays with inter-AP intervals
            (one array per segment) or None for segments without APs
        
        ret["AP_peak_values"] : list of arrays with AP_peak_values
            (one for each segment, or None for segments without APs)
            
        ret["AP_peak_amplitudes"] : list of arrays with AP amplitudes
            (one for each segment or None for segments without APs)
        
        ret["AP_durations_at_half-max"] : list of arrays with AP width at 1/2 max
            (one for eaxch segment or None for segments without APs)
            
        ret["AP_durations_V_0"] : list of arrays with AP width at Vm = 0
            (one for each segment, or None for segments without APs)
            
        ret["AP_durations_V_onset"] : list of arrays with AP width at 
            Vm = threshold potential (one for each segment or None for segments
            without APs)
            
        ret["AP_maximum_dV_dt"] : list of arrays with the maximum dV/dt per AP
            (one for each segment, or None for segments without APs)
    
        NOTE: the lengths of the arrays returned as list elements equals the 
            number of APs detected in the corresponding segment; if no APs are
            detected, None is inserted instead of an empty array.
        
    Side effects
    ------------
        The detected APs are embedded as SpikeTrain objects in the segments
        where they have been detected.
        
    """
    if not isinstance(data, (neo.Block, neo.Segment)):
        raise TypeError("A neo.Block or neo.Segment object was expected; got %s instead" % type(data).__name__)
    
    if isinstance(data, neo.Block):
        if len(data.segments) == 0:
            raise ValueError("There are no segments in the block")
        
        else:
            segments = data.segments
            
    else:
        segments = [data]
    
    cellid = kwargs.pop("cell", "NA")
    sourceid = kwargs.pop("source", "NA")
    genotype = kwargs.pop("genotype", "NA")
    sex = kwargs.pop("sex", "M")
    age = kwargs.pop("age", "NA")
    
    if isinstance(age, pq.Quantity):
        if not any([age.dimensionality == ref.dimensionality for ref in [pq.day, pq.month, pq.year] ]):
            raise TypeError("age expected to be a python Quanity in day, month or year, or None; got %s instead" % age)
        
    elif age is None:
        age = "NA"
        
    treatment = kwargs.pop("treatment", "veh")
    
    post_natal = kwargs.pop("post_natal", True)
    
    if sex.lower() not in ("m", "f", "na"):
        raise ValueError("Allowed values for sex are 'm' or 'f'; got %s instead" % sex)
    
    plot_rheo = kwargs.pop("plot_rheo", False)
    
    thr = kwargs.pop("thr", 10)
    
    VmSignal = kwargs.pop("VmSignal", "Vm_prim_1")
    ImSignal = kwargs.pop("ImSignal", None)
    
    rheo = kwargs.pop("rheo", True)
    
    minsteps = kwargs.pop("minsteps", 3)
    
    if not isinstance(minsteps, int):
        raise TypeError("minsteps expected to be an int; got %s instead" % type(minsteps).__name__)

    if minsteps < 1:
        raise ValueError("minsteps must be > 0: got %s instead" % minsteps)
    
    rheoargs = dict()
    
    rheoargs["fitrheo"] = kwargs.pop("fitrheo", False)
    
    rheoargs["xstart"] = kwargs.pop("xstart", 0)
    
    rheoargs["xend"] = kwargs.pop("xend", 0.1)
    
    rheoargs["npts"] = kwargs.pop("npts", 100)
    
    rheoargs["minsteps"] = minsteps
    
    prefix = "AP_Train_Analysis"
    
    name = kwargs.pop("name", None)
    
    if name is None or (isinstance(name, str) and len(name.strip()) == 0):
        if isinstance(data, (neo.Block, neo.Segment)):
            if isinstance(data.name, str) and len(data.name.strip()):
                name = data.name
                
        if name is None:
            cframe = inspect.getouterframes(inspect.currentframe())[1][0]
            
            try:
                for (k,v) in cframe.f_globals.items():
                    if isinstance(v, (neo.Block, neo.Segment)) and v == data:
                        name = k
            finally:
                del(cframe)
        
    #kwargs["ImSignal"] = ImSignal # use this for each segmentm, below!
    kwargs["thr"] = thr
    
    Iinj_0 = kwargs.pop("Iinj_0", None)
    delta_I = kwargs.pop("delta_I", None)
    
    Iinj = kwargs.pop("Iinj", None)
    
    Istart = kwargs.pop("Istart", None)
    Istop = kwargs.pop("Istop", None)
    Itimes_samples = kwargs.pop("Itimes_samples", False)
    Itimes_relative = kwargs.pop("Itimes_relative", True)
    
    if isinstance(Iinj_0, (float, int)):
        Iinj_0 = Iinj_0 * pq.pA
        
    elif isinstance(Iinj_0, pq.Quantity):
        if Iinj_0.size != 1:
            raise TypeError("Iinj_0 must be a scalar quantity")
        
        if units_convertible(Iinj_0, pq.pA):
            Iinj_0 = Iinj_0.rescale(pq.pA)
            
        else:
            raise TypeError("Iinj_0 must be in current units; got %s instead" % Iinj_0.dimensionality)
        
    elif Iinj_0 is not None:
        raise TypeError("Iinj_0 must be scalar float or quantity, or None; got %s instead" % type(Iinj_0).__name__)
    
    #kwargs["Iinj_0"] = Iinj_0
    
    if isinstance(delta_I, (float, int)):
        delta_I = delta_I * pq.pA
        
    elif isinstance(delta_I, pq.Quantity):
        if delta_I.size != 1:
            raise TypeError("delta_I must be a scalar quantity")
        
        if units_convertible(delta_I, pq.pA):
            delta_I = delta_I.rescale(pq.pA)
            
        else:
            raise TypeError("delta_I must be in current units; got %s instead" % delta_I.dimensionality)
        
    elif delta_I is not None:
        raise TypeError("Iinj_0 must be scalar float or quantity, or None; got %s instead" % type(delta_I).__name__)
    
    
    #NOTE: set up the of current injection amplitudes
    # this is based on either:
    #   Iinj_0 and delta_I if given, or Iinj itself, or
    # will be detected from ImSignal if given
    #
    # to be supplied together with Istart, Istop
    # for use when current injection params would fail
    
    if ImSignal is None:
        # needs Iinj, or  (Iinj_0, delta_I)
        if Iinj is None:
            # needs Iinj_0 and delta_I
            if all([v is not None for v in (Iinj_0, delta_I)]):
                i_max = Iinj_0 + delta_I * (len(segments)-1)
                
                Iinj = np.linspace(Iinj_0, i_max, num=len(segments))
                
                if not isinstance(Iinj, pq.Quantity):
                    Iinj *= pq.pA
                    
            else:
                raise ValueError("I need Iinj_0 and delta_I")
    
        elif isinstance(Iinj, (tuple, list)):
            if len(Iinj) != len(segments):
                raise ValueError("Size mismatch between Iinj sequence (%d) and segments sequence (%d)" % (len(Iinj), len(segments)))
            
            if all([isinstance(v, float) for v in Iinj]):
                Iinj = np.array(Iinj) * pq.pA
                
            elif all([isinstance(v, pq.Quantity) and units_convertible(v, pq.pA) for v in Iinj]):
                Iinj = np.array([v.rescale(pq.pA).magnitude for v in Iinj]) * pq.pA
                
            else:
                raise TypeError("Unexpected type for Iinj: %s" % type(Iinj).__name__)
            
        elif isinstance(Iinj, pq.Quantity):
            if Iinj.size != len(segments):
                raise ValueError("Size mismatch between Iinj (%d) and segments sequence (%d)" % (Iinj.size, len(segments)))
            
            if Iinj.ndim > 1:
                if Iinj.shape[1] > 1:
                    raise TypeError("Iinj array must be a vector")
                
                Iinj = Iinj.flatten()
                
        else:
            raise TypeError("Unexpected type for Iinj: %s" % type(Iinj).__name__)
        
        # also needs Istart, Istop, Itimes_relative, Itimes_samples
        if all([v is None for v in (Istart, Istop)]):
            raise ValueError("I need Istart and Istop")
        
    elif not isinstance(ImSignal, (int, str)):
        raise TypeError("I need either ImSignal, or (Istart, Istop, Itimes_samples and Itimes_relative)")
        
            
    ret = collections.OrderedDict()
    
    ret["Data"] = name
    ret["Cell"] = cellid
    ret["Source"] = sourceid
    ret["Age"] = age
    ret["Post-natal"] = post_natal
    ret["Genotype"] = genotype
    ret["Sex"] = sex
    ret["Treatment"] = treatment
    ret["Depolarising_steps"] = list()
    
    kwargs["VmSignal"] = VmSignal
    
    try:
        for k, segment in enumerate(segments):
            #print("segment %d" %k)
            if isinstance(Iinj, pq.Quantity):
                im = (Iinj[k], Istart, Istop)
            else:
                im = ImSignal
                
            step_result, vstep = analyse_AP_step_injection_sweep(segment, ImSignal = im, 
                                                           Itimes_relative = Itimes_relative,
                                                           Itimes_samples = Itimes_samples,
                                                           **kwargs)
            
            if Iinj is not None:
                # override the value measured from the Im signal
                step_result["Injected_current"] = Iinj[k]
                
            segment_result = collections.OrderedDict()
            segment_result["Index"] = k
            segment_result["Name"] = segment.name
            segment_result["AP_analysis"] = step_result
            segment_result["Vm_signal"] = vstep
            
            
            ret["Depolarising_steps"].append(segment_result)
        
    
        seg_times = [s.analogsignals[0].t_start for s in segments]
        
        seg_index = [k for k in range(len(segments))]
        
        t_units = segments[0].analogsignals[0].times.units
        
        if Iinj is None:
            # use the measured value
            _inj = [seg_res["AP_analysis"]["Injected_current"] for seg_res in ret["Depolarising_steps"]]
            Iinj = np.array(_inj) * _inj[0].units
            
        i_units = Iinj[0].units
        
        ret["Name"] = "%s_%s" % (prefix, name)
        
        #print(ret["Name"], len(segments), "segments")
        
        # these are the collated data relevant for rheobase_latency
        ret["Injected_current"]     = IrregularlySampledDataSignal(domain = seg_index,
                                                                   signal = Iinj,
                                                                   units = i_units,
                                                                   dtype = np.dtype("float64"),
                                                                   domain_units = pq.dimensionless,
                                                                   name="Injected current")
        
        ret["Injected_current"].domain_name = "Current injection step index"
        
        if delta_I is not None:
            ret["Delta_I_step"] = delta_I
            
        else: # autodetected delta_I
            # use the measured Iinj values
            if len(segments) > 1:
                ret["Delta_I_step"]         = int(np.ediff1d(ret["Injected_current"].magnitude).mean()) * i_units 
                
            else:
                ret["Delta_I_step"]         = 0 * i_units 
                
                
        apThr = list()
        apLatency = list()
        
        for seg_res in ret["Depolarising_steps"]:
            if isinstance(seg_res["AP_analysis"]["AP_train"], neo.SpikeTrain) and len(seg_res["AP_analysis"]["AP_train"]):
                val = seg_res["AP_analysis"]["AP_train"].annotations["AP_onset_Vm"]
                if val is None:
                    apThr.append(np.nan)
                else:
                    apThr.append(float(val[0]))
                    
                apLatency.append(seg_res["AP_analysis"]["AP_train"][0] - seg_res["AP_analysis"]["AP_train"].t_start)
                
            else:
                apThr.append(np.nan)
                apLatency.append(np.nan * vstep.times.units)
                
        apThr = (np.array(apThr))[:,np.newaxis] * vstep.units
        
        #apThr = [seg_res["AP_analysis"]["AP_train"].annotations["AP_onset_Vm"][0] for seg_res in ret["Depolarising_steps"]]
        
        #apLatency = [seg_res["AP_analysis"]["AP_train"][0] - seg_res["AP_analysis"]["AP_train"][0].t_start for seg_res in ret["Depolarising_steps"]]
        
        apFrequency = [seg_res["AP_analysis"]["Mean_AP_Frequency"] for seg_res in ret["Depolarising_steps"]]
        
        #f_units = apFrequency[0].units
        
        nAPs = [seg_res["AP_analysis"]["Number_of_APs"] for seg_res in ret["Depolarising_steps"]]
        
        # print(f"Iinj = {Iinj}")
        # print(f"apThr = {apThr}")
        ret["First_AP_threshold"]   = IrregularlySampledDataSignal(domain = Iinj,
                                                                   signal = apThr,
                                                                   units = vstep.units,
                                                                   dtype = np.dtype("float64"),
                                                                   domain_units = i_units,
                                                                   name="First AP Onset")
        
        ret["First_AP_latency"]     = IrregularlySampledDataSignal(domain = Iinj,
                                                                   signal = apLatency,
                                                                   units = vstep.times.units, 
                                                                   dtype = np.dtype("float64"),
                                                                   domain_units = i_units,
                                                                   name = "First AP latency")
        
        ret["Mean_AP_Frequency"]    = IrregularlySampledDataSignal(domain = Iinj,
                                                                   signal = apFrequency,
                                                                   units = apFrequency[0].units, 
                                                                   dtype = np.dtype("float64"),
                                                                   domain_units = i_units,
                                                                   name="Mean AP Frequency")
        
        ret["Number_of_APs"]        = IrregularlySampledDataSignal(domain = Iinj,
                                                                   signal = nAPs, 
                                                                   units = pq.dimensionless,
                                                                   dtype = np.dtype("float64"),
                                                                   domain_units = i_units,
                                                                   name="AP count")
        
        # augument result with rheobase-latency analysis
        ret["rheobase_analysis"] = None
        
        #print("latency", ret["First_AP_latency"])
        #print("iinj", ret["Injected_current"])

        if not test_for_rheobase_latency(ret, minsteps):
            if rheo:
                print("%s: Rheobase-latency analysis requires a minimum of %d suprathreshold injection steps" % (ret["Name"], minsteps))
                
        elif rheo and len(ret["First_AP_latency"]) > 0 and len(ret["First_AP_latency"]) == len(ret["Injected_current"]) and \
            not np.all(np.isnan(ret["First_AP_latency"])):
            # further consistency checks
            ret["rheobase_analysis"] = rheobase_latency(ret, **rheoargs)
            
            if plot_rheo and ret["rheobase_analysis"] is not None:
                plot_rheobase_latency(ret["rheobase_analysis"])
            
        return ret
    
    except Exception as e:
        print("In %s:" % name)
        traceback.print_exc()
        
    
def plot_rheobase_latency(data, xstart=None, xend=None):
    #import models
    
    if not isinstance(data, dict):
        raise TypeError("Expecting a dict; got %s instead" % type(data).__name__)
    
    if "Summary" in data and isinstance(data["Summary"], dict):
        if "fit" in data["Summary"] and isinstance(data["Summary"]["fit"], dict):
            data = data["Summary"]
            
        else:
            raise ValueError("data does not seem to contain a rheobase-latency fit")
        
    elif "rheobase_analysis" in data and isinstance(data["rheobase_analysis"], dict):
        if "fit" in data["rheobase_analysis"] and isinstance(data["rheobase_analysis"]["fit"], dict):
            data = data["rheobase_analysis"]
            
        else:
            raise ValueError("data does not seem to contain a rheobase-latency fit")
        
    elif all([v in data for v in ("I", "Latency", "Irh")]):
        if "fit" not in data or not isinstance(data["fit"], dict):
            raise ValueError("data does not seem to contain a rheobase-latency fit")
            
        
    else:
        raise ValueError("data does not seem to contain a rheobase-latency fit")
    
    #print("xstart", xstart, "xend", xend)
        
    try:
        x = data["Latency"].magnitude
        y = data["I"].magnitude
        
        if all([x is None for x in (xstart, xend)]):
            x1 = data["fit"]["x"]
            y1 = data["fit"]["y"]
            
        else:
            if xstart is None:
                xstart = 0
                
            if xend is None:
                xend = np.nanmax(x)
                
            #print("xstart", xstart, "xend", xend)
            
            popt = data["fit"]["parameters"]
            
            x1 = np.linspace(xstart, xend, 100)
            
            if data["fitrheo"]:
                y1 = 1/models.Frank_Fuortes2(x1, *popt)
                
            else:
                y1 = 1/models.Frank_Fuortes(x1, *popt)
        
        plt.clf()
        
        if not data["fitrheo"]:
            # y is fit of I/Irh
            Irh = data["fit"]["Irh"].magnitude
            plt.plot(x, y/Irh, "o", label="Strength vs Latency")
            plt.plot(x1,y1, label="Fitted Strength vs Latency")
            plt.ylabel(r"$\mathrm{\mathsf{I}} \/ / \/\mathrm{\mathsf{I_{rheo}}}$")
            
        else:
            # y is fit of I
            plt.plot(x, y, "o", label="Current vs Latency")
            plt.plot(x1,y1, label = "Fitted Current vs Latency")
            plt.ylabel(r"$\mathrm{\mathsf{I}\ (%s)}$" % data["I"].units.dimensionality) 
            
        plt.xlabel("Latency (%s)" % data["Latency"].units.dimensionality)
        
        plt.legend()
            
    except Exception as e:
        raise ValueError("data does not seem to contain a rheobase-latency fit")
        
def test_for_rheobase_latency(data, minsteps=3):
    """Tests if data can be used for rheobase-latency analysis.
    
    The following conditions are tested:
    
    a) the data must be a dictionary as output from analyse_AP_step_injection_series, and
        containing the following keys:
        
        "Injected_current"
        "First_AP_latency"
        "Depolarising_steps"
        "Delta_I_step"
        
        With the exception of Delta_I_step, all other keys must map to iterables 
        containing the same number of elements.
        
        In particular, 
            "Injected_current" and "First_AP_latency" are 
                neo.IrregularlySampledSignal objects
        
            "Depolarising_steps" is a list of dictionaries as output by a call
                to analyse_AP_step_injection_sweep().
        
    b) The number of "Depolarising_steps" with at least one AP detected >= minsteps
        
    
    Parameters:
    ----------
    data: dict
        result from analyse_AP_step_injection_series (a "block result")
        
    minsteps: int (default is 3)
        minimum number of curent injection steps where APs were triggered, for
        performing rheobase-latency analysis
        
    """
    ok = False
    
    try:
        ok = len([s for s in data["Depolarising_steps"] if (s["AP_analysis"]["Number_of_APs"] > 0 and s["AP_analysis"]["AP_train"] is not None) ] ) >= minsteps
        
    except:
        return False
    
    return ok

def report_AP_analysis(data, name=None):
    """Reports data from analyse_AP_step_series_replicate in pandas format.
    
    Parameters:
    ----------
    
    data: a dict returned by analyse_AP_step_series_replicate()
    
    name: str or None
    
    Returns:
    -------
    
    summary: pandas DataFrame
    
        Contains values (scalars) for rheobase current, membrane time constant, 
            test current value and its multiple of rheobase, and mean AP frequency
            
    params: pandas DataFrame, or None 
        
        This is None if no action potentials were detected in analysis (this may 
        happen when the analysis was not applied to a current injection step 
        experiment).
    
        Contains values averaged over the series in the run (see NOTE), for the
        following AP parameters at the test current:
            
        frequency: the instantaneous AP frequency.
            
        amplitude: the AP amplitude values.
        
        peak: the AP peak values.
        
        onset: the AP onset values.
        
        max_dvdt: the values of the maximum dV/dt
        
        duration_half_max: the durations at half-max.
        
        duration_0_mV: the durations at 0 mV for the action potentials
        
    waveforms: list, or None
    
        This is None if no action potentials were detected in analysis (this may 
        happen when the analysis was not applied to a current injection step 
        experiment).
        
        Contains the AP waveforms for the AP train at test current injection
        (these are averages of the first minimum number of APs fired at test
        current injection in each series, see NOTE below)
        
        
    NOTE: The averages are taken over the minimum number of APs fired at test 
        current injection in each series in the run (there may be a different 
        number of APs fired at test current in each series)
        
    """
    if not isinstance(data, dict):
        raise TypeError("Expecting a dict; got %s instead" % type(data).__name__)
    
    report_dict = collections.OrderedDict()
    
    report_dict["Name"] = ""
    
    ap_ampli_series = None
    ap_peak_series = None
    ap_onset_series = None
    ap_durations_hm_series = None
    ap_durations_0mV_series = None
    ap_durations_refVm_series = None
    ap_max_dvdt_series = None
    ap_inst_freq_series = None
    
    summary = None
    
    params = None
    
    waveforms = None
    
    if isinstance(name, str) and len(name.strip()):
        report_dict["Name"] = name
        
    if all([v in data for v in ("Block_Results", "Summary")]):
        # a result from analyse_AP_step_series_replicate
        if "Summary" in data and isinstance(data["Summary"], dict):
            data = data["Summary"]
            
        else:
            print("data does not seem to be an AP analysis summary")
            return summary, params, waveforms
        
    elif all([v in data for v in ("Depolarising_steps", "rheobase_analysis")]):
        data = data["rheobase_analysis"]
    
    else:
        if not all(v in data for v in ["Irh", "tau"]):
            print("data does not seem to be an AP analysis summary")
            return summary, params, waveforms
        
    report_dict["Irh"] = data["Irh"]
    report_dict["tau (s)"] = data["tau"]
    test_current_dict = data.get("Test_Current", None)

    if isinstance(test_current_dict, dict) and len(test_current_dict):
        report_dict["test current x rheobase"] = test_current_dict["Rheobase_factor"]
        
        val = test_current_dict["Value"]
        
        #print("test_current_value", val)
        
        report_dict["test current value (%s)" % val.units.dimensionality] = val
        
        report_dict["minimum APs at test current"] =test_current_dict["Minimum_number_of_APs"]
        
        val = test_current_dict["Mean_AP_Frequency"]
        report_dict["test current AP frequency (%s)" % val.units.dimensionality] = val
        
        vm_units = test_current_dict["Action_potentials"][0]["Mean_AP_Amplitude"].units
        time_units = test_current_dict["Action_potentials"][0]["Mean_AP_duration_at_half_max"].units
        dvdt_units = test_current_dict["Action_potentials"][0]["Mean_AP_Max_dV_dt"].units
        freq_units = test_current_dict["Mean_AP_Frequency"].units
        
        ap_amplitudes = np.array([d["Mean_AP_Amplitude"] for d in test_current_dict["Action_potentials"]]) * vm_units
        ap_peaks = np.array([d["Mean_AP_Peak"] for d in test_current_dict["Action_potentials"]]) * vm_units
        ap_onsets = np.array([d["Mean_AP_Onset"] for d in test_current_dict["Action_potentials"]]) * vm_units
        
        ap_d_hm = (np.array([d["Mean_AP_duration_at_half_max"] for d in test_current_dict["Action_potentials"]]) * time_units).rescale(pq.ms)
        ap_d_0mV = (np.array([d["Mean_AP_duration_at_0_Vm"] for d in test_current_dict["Action_potentials"]]) * time_units).rescale(pq.ms)
        ap_d_refmV = (np.array([d["Mean_AP_duration_at_ref_Vm"] for d in test_current_dict["Action_potentials"]]) * time_units).rescale(pq.ms)
        
        ap_ref_Vm = test_current_dict["Action_potentials"][0]["Mean_AP_ref_Vm"]
        
        ap_max_dvdt = np.array([d["Mean_AP_Max_dV_dt"] for d in test_current_dict["Action_potentials"]]) * dvdt_units
        
        inst_freq = test_current_dict.get("AP_Instantaneous_frequency", [])[:len(test_current_dict["Action_potentials"])]

        ap_ampli_series = pd.Series(data = ap_amplitudes, name = "%s (%s)" % ("AP amplitude", ap_amplitudes.dimensionality))
        
        ap_peak_series = pd.Series(data = ap_peaks, name = "%s (%s)" % ("AP peak value", ap_peaks.dimensionality))
        
        ap_onset_series = pd.Series(data = ap_onsets, name = "%s (%s)" % ("AP onset value", vm_units.dimensionality))
        
        ap_max_dvdt_series = pd.Series(data = ap_max_dvdt, name = "%s (%s)" % ("Maximum dV/dt", ap_max_dvdt.dimensionality))

        ap_durations_hm_series = pd.Series(data = ap_d_hm, name = "%s (%s)" % ("AP duration at half-max", ap_d_hm.dimensionality))

        ap_durations_0mV_series = pd.Series(data = ap_d_0mV, name = "%s (%s)" % ("AP duration at 0 mV", ap_d_0mV.dimensionality))
        
        ap_durations_refVm_series =pd.Series(data = ap_d_refmV, name="AP duration at %g mV, %s" % (ap_ref_Vm, ap_d_refmV.dimensionality))

        ap_inst_freq_series = pd.Series(data = inst_freq.flatten(), name = "%s (%s)" % ("Instantaneous frequency", inst_freq.dimensionality))
        
        waveforms = [d["Average_waveform_signal"] for d in test_current_dict["Action_potentials"]]
        
    summary = pd.DataFrame(report_dict)
    
    params_d = dict()
    
    data_series = [s for s in (ap_ampli_series, ap_peak_series, ap_onset_series, ap_max_dvdt_series, ap_durations_hm_series, ap_durations_0mV_series, ap_durations_refVm_series, ap_inst_freq_series) if s is not None]
    
    if len(data_series):
        for s in data_series:
            params_d[s.name] = s
    
    if len(params_d):
        params = pd.DataFrame(data=params_d)
        
    else:
        params = None
    
    return summary, params, waveforms

def analyse_AP_step_injection_sweep(segment, VmSignal:typing.Union[int, str] = "Vm_prim_1", ImSignal:typing.Union[int, str, tuple] = "Im_sec_1", Itimes_relative:bool = True,Itimes_samples:bool = False,**kwargs):
    """AP Train analysis in a sweep (segment) of I-clamp experiments
    
    Positional parameters:
    ---------------------
    
    segment: a neo.Segment with at least two analog signals (see below)
    
    Named parameters:
    ----------------
    
    VmSignal: int, str.
        Indicates the analog signal containing the Vm response.
        
        When an int, this is the scalar index of the signal, in 'segment'
        
        When a str, this is the name of the Vm signal
        
        Default is "Vm_prim_1"
        
     ImSignal: int, str, tuple
        Indicates the current injection parameters.
        
        When an int, this is the scalar index, in 'segment', of the analog signal
        containing the current injeciton step.
        
        When a str, this is the name of the current injection signal.
        
        When a tuple, it MUST contain three elements (Inj, Istart, Istop), where:
        
            Iinj: scalar quantity (in pA): the magnitude of the current injection
                step
                
            Istart: scalar (int, float, or quantity in s): the start of the 
                injection step
                
            Istop: scalar (int, float, or quantity in s): the stop of the 
                injection step
                
            NOTE that Istart and Istop can also be given as numbers of samples.
            In this case, Itimes_samples must be set to True (see below).
        
        Default is "Im_sec_1".
        
    Itimes_relative:bool, default is True.
        When ImSignal is a tuple, ImSignal[1] and ImSignal[2] are current 
        injjection start and stp times, relative to the VmSignal start time.
        
    Itimes_samples:bool, default is False
        Set to True when the current injection start and stop times in the 
        'ImSignal' tuple are given as samples (BEFORE any resampling, see below).
        
        When True, this implies the resolved times are relative to VmSingal
        start time.
    
    Var-keyword parameters (kwargs):
    --------------------------------
    
    NOTE: passed to extract_AP_train:

    tail: scalar Quantity (units: "s"); default is 0 s
        duration of trailing Vm signal after current injection has ceased
    
    resample_with_period: None (default), scalar float or Quantity
        When not None, the Vm signal will be resampled before processing.
        
        When Quantity, it must be in units convertible (scalable) to the signal's
        sampling period units.
        
        Resampling occurs on the region corresponding to the depolarizing current
        injection, before detection of AP waveforms.
        
        Upsampling might be useful (see Naundorf et al, 2006) but slows down
        the execution. To upsample the Vm signal, pass here a value smaller than
        the sampling period of the Vm signal.
        
    resample_with_rate: None (default), scalar float or Quantity
        When not None, the Vm signal will be resampled before processing.
        
        When Quantity, it must be in units convertible (scalable) to the signal's
        sampling rate units.
        
        Resampling occurs on the region corresponding to the depolarizing current
        injection, before performing detection of AP waveforms.
        
        Upsampling might be useful (see Naundorf et al, 2006) but slows down
        the execution. To upsample the Vm signal, pass here a value larger than 
        the sampling period of the Vm signal.
        
    box_size: int >= 0; default is 0.
    
        size of the boxcar (scipy.signal.boxcar) used for filtering the Im signal
        (containing the step current injection) before detecting the step 
        boundaries (start & stop)
        
        default is 0 (no boxcar filtering)
        
    method: str, one of "state_levels" (default) or "kmeans"
    
    adcres, adcrange, adcscale: float scalars, see signalprocessing.state_levels()
        called from signalprocessing.parse_step_waveform_signal() 
        
        Used only when method is "state_levels"
        
    NOTE: The following are passed directly to detect_AP_waveforms_in_train():
    
    smooth_window: int >= 0; default is 5
        The length (in samples) of a smoothing window (boxcar) used for the 
        signal's derivatives.
        
        The length of the window will be adjusted if the signal is upsampled.
        
    thr: floating point scalar: the minimum value of dV/dt of the Vm waveform to
        be considered an action potential (default is 10) -- parameter is passed to detect_AP_waveforms_in_train()
        
    before, after: floating point scalars, or Python Quantity objects in time 
        units convertible to the time units used by VmSignal.
        interval of the VmSignal data, respectively, before and after the actual
        AP in the returned AP waveforms -- parameters are passed to detect_AP_waveforms_in_train()
        
        defaults are:
        before: 1e-3
        after: None
        
    min_fast_rise_duration : None, scalar or Quantity (units "s");
    
        The minimum duration of the initial (fast) segment of the rising 
        phase of a putative AP waveform.
        
        When None, is will be set to the next higher power of 10 above the sampling period
        of the signal.
    
    min_ap_isi : None, scalar or Quantity;
    
                Minimum interval between two consecutive AP fast rising times 
                ("kinks"). Used to discriminate against suprious fast rising time
                points that occur DURING the rising phase of AP waveforms.
                
                This can happen when the AP waveforms has prominent IS and the SD 
                "spikes", 
                
                see Bean, B. P. (2007) The action potential in mammalian central neurons.
                Nat.Rev.Neurosci (8), 451-465

    rtol, atol: float scalars;
        the relative and absolute tolerance, respectively, used in value 
        comparisons (see numpy.isclose())
        
        defaults are:
        rtol: 1e-5
        atol: 1e-8
                
    use_min_detected_isi: boolean, default True
    
        When True, individual AP waveforms cropped from the Vm signal "sig" will
            have the duration equal to the minimum detected inter-AP interval.
        
        When False, the durations of the AP waveforms will be taken to the onset
            of the next AP waveform, or the end of the Vm signal
            
    interpolate_roots: boolean, default False
        When true, use linear inerpolation to find the time coordinates of the
        AP waveform rise and decay phases crossing over the onset, half-maximum
        and 0 mV. 
        
        When False, uss the time coordinate of the first & last sample >= Vm value
        (onset, half-max, or 0 mV) respectively, on the rise and decay phases of
        the AP waveform.
        
        see ap_waveform_roots()
        
    decay_intercept_approx: str, one of "linear" (default) or "levels"
        Used when the end of the decay phase cannot be estimated from the onset
        Vm.
        
        The end of the decay is considerd to be the time point when the decaying
        Vm crosses over (i.e. goes below) the onset value of the action potential.
        
        Whe the AP waveform is riing on a rising baseline, this time point cannot
        be determined.
        
        Instead, it is estimated as specified by "decay_intercept_approx" parameter:
        
        When decay_intercept_approx is "linear", the function uses linear extrapolation
        from a (higher than Vm onset) value specified by decay_ref (see below)
        to the onset value.
        
        When decay_intercept_approx is "levels", the function estimates a "pseudo-baseline"
        as the lowest of two state levels determined from the AP waveform histogram.
        
        The pseudo-baseline is then used to estimate the time intercept on the decay
        phase.
        
    decay_ref: str, one of "hm" or "zero", or floating point scalar
        Which Vm value should be used to approximate the end of the decay phase
        when using the "linear" approximation method (see above)
        
    Passed to detect_AP_rises
    -------------------------
    vm_thr: scalar: putative events (APs) that do not cross this threshold will be 
                discarded (optional, default is 0)
                
                This parameter prevents flagging the passive rising phase of the Vm
                at the start of the current injection as being an AP.
            
                It will also result in no AP waveforms being detected in poor 
                recordings (e.g., where the APs do not seem to cross the 0 mV 
                likely due to bad & leaky current clamp).
                
    
    rtol, atol, return_all → see detect_AP_rises
            
    
        
    Returns:
    -------
    result : ordered dict; 
        key names should be self-explanatory
        
        contains the result of the AP train analysis, including the AP train
        itself, and AP waveforms and derivatves (1st and 2nd order) as 
        neo.AnalogSignals -- see detect_AP_waveforms_in_train()
    
    vstep : neo.AnalogSignal; 
        contains the time slice of the Vm signal, encompassing  the AP train
    
    References:
    -----------
    
    Naundorf et al (2006). Unique features of action potential initiation in 
        cortical neurons. Nature 440, 1060–1063.
    
    """
    tail                    = kwargs.pop("tail", 0*pq.s)
    resample_with_period    = kwargs.pop("resample_with_period", None)
    resample_with_rate      = kwargs.pop("resample_with_rate", None)
    method                  = kwargs.pop("method", "state_levels")
    box_size                = kwargs.pop("box_size", 0)
    adcres                  = kwargs.pop("adcres", 15)
    adcrange                = kwargs.pop("adcrange", 10)
    adcscale                = kwargs.pop("adcscale", 1e3) # (mV -> V)
    smooth_window           = kwargs.pop("smooth_window", 5)
    
    kwargs.pop("return_all", None) # remove the debugging parameter
    
    # NOTE: 2019-05-03 13:08:48
    # removed: result not has individual AP analysis for all detected APs
    # 
    
    if isinstance(VmSignal, str):
        VmSignal = neoutils.get_index_of_named_signal(segment, VmSignal)
    
    vm = segment.analogsignals[VmSignal].copy()
        
    if isinstance(ImSignal, str):
        im = segment.analogsignals[neoutils.get_index_of_named_signal(segment, ImSignal)].copy()
        
    elif isinstance(ImSignal, int):
        im = segment.analogsignals[ImSignal].copy()
        
    elif isinstance(ImSignal, tuple) and len(ImSignal) == 3: # (Iinj, Istart, Istop)
        im = ImSignal
        
    else:
        raise TypeError(f"ImSignal expected a str (signal name) int signal index) or a triplet (amplitude, start & stop times); got {ImSignal} instad")
                
    
    vstep, Ihold, Iinj, istep = extract_AP_train(vm,im,
                                    tail=tail,
                                    method=method,
                                    box_size=box_size, 
                                    adcres=adcres,
                                    adcrange=adcrange,
                                    adcscale=adcscale,
                                    resample_with_period=resample_with_period,
                                    resample_with_rate=resample_with_rate,
                                    Itimes_relative = Itimes_relative,
                                    Itimes_samples = Itimes_samples)
    
    
    # print(f"analyse_AP_step_injection_sweep: istep = {istep}")
    
    # adjust the smooth window for the new sampling_period
    if smooth_window > 0:
        upsampling = (vm.sampling_period.rescale(pq.s) / vstep.sampling_period.rescale(pq.s)).magnitude.flatten()[0]
        
        smooth_window = int(smooth_window * upsampling)
        
        if smooth_window % 2 == 0:
            smooth_window += 1
            
        kwargs["smooth_window"] = smooth_window
            
        
    #Ihold = im.time_slice(d, im.t_stop).mean()
    
    # NOTE: 2019-04-29 13:32:46
    # upsample the Vm signal if required
    
    # returns the array of time "stamps" (neo.SpikeTrain) and a list of AP
    # waveforms (neo.AnalogSignal objects)
    
    # NOTE: 2019-08-16 13:30:43
    # ap_train is always a SpikeTrain, even if empty
    kwargs["t_start"] = vm.t_start
    kwargs["t_stop"] = vm.t_stop
    # print(f"analyse_AP_step_injection_sweep kwargs t_start {kwargs['t_start']}, t_stop {kwargs['t_stop']}")
    ap_train, ap_waveform_signals = detect_AP_waveforms_in_train(vstep, istep, **kwargs)
    # print(f"analyse_AP_step_injection_sweep ap_train t_start = {ap_train.t_start}, t_stop = {ap_train.t_stop}")
    
    result = collections.OrderedDict() #dict()
    
    #if isinstance(ap_train, neo.SpikeTrain) and len(ap_train):
    if len(segment.spiketrains) > 0: 
        # check to see if there already is a spike train of APs; don't just append
        ndx = list(filter(lambda x: is_AP_spiketrain(x[1]), ((k,s) for k,s in enumerate(segment.spiketrains))))
        
        if len(ndx):
            segment = neoutils.remove_spiketrain(segment, ndx)
                   
        # for k, st in enumerate(segment.spiketrains):
        #     if is_AP_spiketrain(st):
        #         #segment.spiketrains[k] = ap_train
        #         # NOTE: in neo >= 0.10.0 segment.spiketrains is a neo.SpikeTrainList
        #         list(segment.spiketrains)[k] = ap_train
                
    else:
        segment.spiketrains.append(ap_train)
        
    result["Injected_current"] = Iinj
    result["Ihold"] = Ihold
    result["AP_train"] = ap_train
    
    for key, value in ap_train.annotations.items():
        result[key] = value
    
    # NOTE: mean AP frequency:
    if len(ap_train) > 1:
        # Mean AP freq = number of APs / full duration of the AP train;
        # full AP train duration (NOT the duration of the depolarized Vm region)
        # is the time difference between the end of the last AP and start of the
        # first AP;
        # time of the end of last AP is time of start of last AP + last AP duration at Vonset
        
        #print("analyse_AP_step_injection_sweep for Iinj %g: ap_train[-1]: %g, AP_durations_V_onset[-1]: %g, ap_train[0]: %g" % (Iinj, ap_train[-1], ap_train.annotations["AP_durations_V_onset"][-1], ap_train[0]))
        mean_ap_freq  = ( len(ap_train) / ( ap_train[-1] - ap_train[0] ) ).rescale(pq.Hz)
        # why do I sometimes get np.nan here ?
        # because you need to also provide a tail in case the last AP is right on the end of the Vm signal!
        ap_intvl = np.diff(ap_train.magnitude, axis=0) * vm.times.units
        
    elif len(ap_train) == 1: # just 1 AP:
        # here, there is NO AP train (just one AP) so we're forced to use the
        # full duration of the depolarized Vm trace
        mean_ap_freq = (1. / vstep.duration).rescale(pq.Hz)
        ap_intvl = np.array([np.nan]) * vm.times.units
        
    else:
        mean_ap_freq = 0. * pq.Hz
        ap_intvl = np.array([np.nan]) * vm.times.units
        
    #print("mean_ap_freq", mean_ap_freq)
        
    result["Inter_AP_intervals"] = ap_intvl
    
    result["Mean_AP_Frequency"]  = mean_ap_freq
    
    result["Number_of_APs"] = len(ap_train)
    
    result["Waveform_signals"] = ap_waveform_signals
    
    return result, vstep

def extract_AHPs(*data_blocks, step_index, Vm_index, Iinj_index, name_prefix):
    """Extracts AHPs from averaged trials at a given Iinj.
    
    *data_blocks = trial blocks (can have more that one segment)
    
    Keyword arguments (defaults are None and will raise Error)
    
    step_index: int >= 0; index of the segment for the given Iinj
    Vm_index: int >= 0; index of the recorded Vm analogsignal
    Iinj_index: int >= 0; index of the injected current command signal (for event/epoch detection)
    name_prefix: str = name prefix of returned variables
    
    Returns the tuple (AHP, averaged_block, params), where
    
    AHP: neo.AnalogSignal with the AHP waveform
    
    averaged_block: neo.Block with one segment, containing the average of the Vm signal and Iinj command signal
    
    params: a dict with the following keys:
        name: a str = the name prefix
        Base: a Quantity: the value of Vm baseline
        Ion, Ioff: Quantities = : times of start and stop, respectively of the current injection command
        Iinj: Quantity = the actual value of injected current calculated from the command signal
    
    """
    averaged_block = neoutils.average_blocks(*data_blocks, step_index = step_index, signal_index = [Vm_index, Iinj_index], name=name_prefix)
    
    neoutils.set_relative_time_start(averaged_block)
    
    auto_define_trigger_events(averaged_block, Iinj_index, "user", use_lo_hi = True, label = "Ion", append=False)
    auto_define_trigger_events(averaged_block, Iinj_index, "user", use_lo_hi = False, label = "Ioff", append=True)
    
    Ion = averaged_block.segments[0].events[0].times
    
    Ioff = averaged_block.segments[0].events[1].times
    
    Base = np.mean(averaged_block.segments[0].analogsignals[Vm_index].time_slice(0*pq.s, 0.05*pq.s))
    
    Iinj = np.mean(averaged_block.segments[0].analogsignals[Iinj_index].time_slice(Ion + 0.005*pq.s, Ioff)) - \
           np.mean(averaged_block.segments[0].analogsignals[Iinj_index].time_slice(0*pq.s, Ion))
    
    
    AHP = (averaged_block.segments[0].analogsignals[Vm_index] - Base).time_slice(Ioff, averaged_block.segments[0].analogsignals[Vm_index].t_stop)
    
    AHP.name = "%s_AHP" % name_prefix
    neoutils.set_relative_time_start(AHP)

    params = dict()
    params["name"] = name_prefix
    params["Base"] = Base
    params["Ion"]  = Ion
    params["Ioff"] = Ioff
    params["Iinj"] = Iinj
    
    return (AHP, averaged_block, params)
    
def auto_extract_AHPs(Iinj, Vm_index, Iinj_index, name_prefix, *data_blocks):
    """Extract an averaged AHP from data_blocks given Iinj value
    """
    segments = list() # place selected segments here
    
    Base = list()
    
    k = 0
    
    Ion = list()
    
    Ioff = list()
    
    for b in data_blocks:
        bb = deepcopy(b)
        
        neoutils.set_relative_time_start(bb)
        
        auto_define_trigger_events(bb, Iinj_index, "user", use_lo_hi = True, label="Ion", append=False)
        auto_define_trigger_events(bb, Iinj_index, "user", use_lo_hi = False, label = "Ioff", append=True)
        
        Ion.append(bb.segments[0].events[0].times)
        
        Ioff.append(bb.segments[0].events[1].times)
        
        inj = list()
        
        
        for s in bb.segments:
            inj.append(np.mean(s.analogsignals[Iinj_index].time_slice(Ion[k] + 0.05*pq.s, Ioff[k])) - \
                       np.mean(s.analogsignals[Iinj_index].time_slice(0*pq.s, Ion[k])))
            
        if all([i < Iinj for i in inj]):
            raise ValueError("%s not found" % Iinj)
        
        if all([i > Iinj for i in inj]):
            raise ValueError("%s not found" % Iinj)
        
        seg_index = np.where(inj >= Iinj)[0][0]
        
        Base.append(np.mean(bb.segments[seg_index].analogsignals[Vm_index].time_slice(0*pq.s, Ion[k])))
        
        bb.segments[seg_index].analogsignals[Vm_index] -= Base[k]
        
        segments.append(bb.segments[seg_index])
        
        k += 1
        
    ret = neo.Block()
    
    ret.segments[:] = neoutils.average_segments(*segments, signal_index = [Vm_index, Iinj_index],
                                                name = name_prefix)
    
    AHP = ret.segments[0].analogsignals[Vm_index].time_slice(Ioff[-1], ret.segments[0].analogsignals[Vm_index].t_stop)
    
    AHP.name = "%s_AHP_%d_%s" % (name_prefix, Iinj.magnitude, Iinj.units.dimensionality)
    
    neoutils.set_relative_time_start(AHP)

    params = dict()
    params["name"] = name_prefix
    params["Base"] = Base
    params["Ion"]  = Ion
    params["Ioff"] = Ioff
    params["Iinj"] = Iinj
    
    return AHP, ret, params

        
def measure_AHP(signal):
    """Returns the peak and its integral (Simpson)
    Signal = neo.AnalogSignal with t_start at 0 s and units of mV with one data channel
    Typically this is an AHP waveform already extracted using other functions in this module.
    
    """
    from scipy import integrate
    
    if signal.shape[1]> 1:
        raise ValueError("Signal must be a vector")
    
    if signal.t_start != 0*pq.s:
        signal.t_start = 0*pq.s
    
    # find V minimum
    vMin = np.min(signal)
    
    vMin_ndx = np.where(signal.magnitude == vMin.magnitude)[0][0]
    
    vMin_time = signal.times[vMin_ndx]
    
    # find where Vm == 0
    
    #v_positive_ndx = np.where(signal.time_slice(0*pq.s, vMin_time).magnitude >= 0)[0][-1]

    #v_zero_time = signal.times[v_plus]
    
    dx = signal.sampling_period.magnitude
    
    ahp_integral = integrate.simps(signal.time_slice(vMin_time, signal.t_stop), dx = dx, axis = 0)
    
    return vMin, ahp_integral


def is_AP_spiketrain(x):
    ret = isinstance(x, neo.SpikeTrain)
    
    if ret:
        ret &= (isinstance(x.name, str) and x.name.endswith("AP_train")) or (all([k.startswith("AP_") for k in x.annotations]))
    
    return ret

def PSCwaveform(model_parameters, units=pq.pA, t_start=0*pq.s, duration=0.02*pq.s, sampling_rate=1e4*pq.Hz):
    """Helper function to generate a synthetic post-synaptic current waveform.

    The waveform realizes the Clements & Bekkers 1997 model as a neo.AnalogSignal.
    
    The model has a fast mono-exponential rise and a somewhat slower mono-exponential
    decay ("Alpha-function") that mimics a post-synaptic current (e.g. a miniature
    or spontaneous E/I PSC, henceforth dubbed a "mini-PSC")
    
    Parameters:
    ===========
    model_parameters: a sequence of floating point numbers with the parameters
        for the Clements & Bekkers 97 mEPSC model (see core.models.Clements_Bekkers_97(...))
    
    Named parameters:
    =================
    units: a quantities.UnitQuantity, or quantities.Quantity; default is quantities.pA
    
    t_start, duration: scalar quantities, typically in quantities.s (for 
        AnalogSignals) although one can imagine a similar waveform in other 
        domains (e.g., space) hence usable with DataSignal objects as well.
    
        Defaults are 0*pq.s and 0.05*pq.s (50 ms) for t_start and duration, respectively.
    
    NOTE: make sure both t_start and duration have the same (or-interconvertible)
    units
    
    
    sampling_rate: scalar quantity in units reciprocal of duration.units; for
        example, in the case where domain.units == quantities.s this is expected
        to be in quantities.Hz
    
        Default is 1e4 Hz.
    
    Returns:
    ========
    
    A neo.AnalogSignal containing the synthetic waveform of a "mini-PSC".
    
    """
    
    from core import models, quantities # not to be confused with pq!!!
    
    x = np.linspace(t_start, t_start + duration, num=int(sampling_rate * duration))
    
    if all(isinstance(p, pq.Quantity) for p in model_parameters):
        model_parameters = tuple(float(p.magnitude) for p in model_parameters)
    
    y = models.Clements_Bekkers_97(x.magnitude, model_parameters)
    
    dstring = f"Clements_Bekkers_97 α={model_parameters[0]}, β={model_parameters[1]}, x₀={model_parameters[2]}, τ₁={model_parameters[3]}, τ₂={model_parameters[4]}"
    
    if quantities.check_time_units(x):
        klass = neo.AnalogSignal
    else:
        klass = DataSignal
        
    ret = klass(y, units = units, t_start=t_start, 
                            sampling_rate=sampling_rate,
                            name="Clements & Bekkers '97 model",
                            description=dstring)
    
    ret.annotations["parameters"] = model_parameters
    ret.array_annotations["channel_name"] = ["CB97"]
    ret.array_annotations["channel_ids"] = ["0"]
    
    
    return ret

def detect_Events_CBsliding(x:typing.Union[neo.AnalogSignal, DataSignal], waveform:typing.Union[neo.AnalogSignal, DataSignal], threshold:float=4., channels:typing.Optional[typing.Union[int, typing.Sequence[int]]]=None, outputDetection:bool=False, raw_signal=None):
    """Detect miniature or spontaneous PSCs with optimally scaled template.
    Implements the "sliding template" algorithm in Clements & Bekkers 1997, Biophys.J.
    
    Parameters:
    ==========
    
    x: neo.AnalogSignal or DataSignal containing the recorded membrane current
        that will be scanned for mEPSCs. Typically this is single-channel, 
        meaning it is a 2D array with a singleton 2nd axis (e.g., x.shape = (n,1)
        where `n` is the number of samples in `x`)
    
        NOTE: 2022-12-12 08:56:23 as of now, more than one channel is supported
    
    waveform: neo.AnalogSignal or 1D numpy array (vector, i.e., 
        waveform.shape = (m,) where `m` is the number of samples in `waveform`).
    
        Contains a model mEPSC (ie. a "synthetic" waveform) or a "template" 
        mEPSC waveform extracted from a signal.
    
        ATTENTION: Make sure this model waveform has the SAME SAMPLING RATE as 
        the signal!!!
    
        ALTERNATIVELY, the waveform can be specified by a sequence of six scalars, 
        where the first five are the Clements & Bekkers 1997 model parameters:
        α, β, x₀, τ₁ and τ₂ (see models.Clements_Bekkers_97 for details)
        and the 6ᵗʰ element is the duration of the model waveform (which will
        be generated ad-hoc); this last element is assumed to be in the units of
        the domain of x.
    
        By default, waveform is (0., -1., 0.01, 0.001, 0.01, 0.05) which means,
        for a membrane current signal `x` in pA:
    
        α  =  0.0 pA (ie. no offset)
        β  = -1.0 (i.e. downward deflection)
        x₀ =  0.01 (i.e. 10 ms from the start of the waveform)
        τ₁ =  0.001 (i.e., rising time constant of 1 ms)
        τ₂ =  0.01  (i.e., decay time constant of 10 ms)
        
        and 50 ms duration of the model waveform
    
        NOTE: When specified in this way the waveform will be generated ad-hoc
        using the sampling rate of the signal `x`.
    
        For example, if creating the waveform as a plain numpy array:
        
        t_start     = 0     # [s]
        duration    = 0.2   # [s]
        sr          = 1e4   # [Hz]
        
        t = np.linspace(0, duration, num = sr * duration)
        model = models.Clements_Bekkers_97(x, parameters)
        
        As a convenience, you can use PSCwaveform(...) function in this module to
        generate a synthetic  waveform as a neo.AnalogSignal.
        
    threshold: float; optional, default None.
        This value is the threshold for the detection criterion used in the 
        Clements & Bekkers 1997 Biophys J paper
    
        When threshold is None, the threshold of detection is the calculated 
        root-mean-square of the detection criterion signal output by the sliding
        template detection method.
    
        This parameter is only used when useCBsliding is True.
        
    outputDetection:bool, default is False
        When True, the function also returns the detection criterion (here, as 
        defined in Clements & Bekkers 1997 paper)
    
    raw_signal: analog signal with the same shape and domain as the signal where
        the detection took place, default is None
        When given, the waveforms will be extracted from THIS signal using the 
        time stamps in the spike train.
        This is useful when detection was performed on a pre-processed (e.g., 
        smoothed) signal but the "raw" waveforms are required.
    
        
    Returns:
    ========
    a neo SpikeTrainList with SpikeTrain objects containing time stamps of the 
    detected mPSCs, peak times, and associated waveforms
    
    ATTENTION: When detection has failed, returns None
    
    """
    if not isinstance(x, (neo.AnalogSignal, DataSignal)):
        raise TypeError(f"Expecting a neo.AnalogSignal or DataSignal; got a {type(x).__name__} instead")

    if isinstance(waveform, (np.ndarray,neo.core.basesignal.BaseSignal)):
        if not dt.is_vector(waveform):
            raise TypeError("waveform expected to be a vector")
    
    elif isinstance(waveform, (tuple, list)):
        if len(waveform) == 6:
            waveduration = waveform[5] * x.times.units
            
            waveform = PSCwaveform(waveform[0:-1], units = x.units,
                                     t_start = 0*x.times.units,
                                     duration = waveduration,
                                     sampling_rate = x.sampling_rate)
            
    else:
        raise ValueError("Incorrect waveform specification")
    
    if isinstance(waveform, neo.core.basesignal.BaseSignal):
        mini_duration = waveform.duration
    else:
        # NOTE: 2022-10-25 18:16:26
        # make sure the waveform, if a plain numpy array, has the same
        # "sampling rate" as the signal
        mini_duration = len(waveform) / x.sampling_rate
    
    if sigp.is_positive_waveform(waveform):
        peakfunc = np.argmax
    else:
        peakfunc = np.argmin
        
    h = waveform.magnitude[:,0]
    
    N = h.shape[0]
    
    M = x.shape[0]
    
    sum_h = np.sum(h)           # Σ TEMPLATE
    sum_h_N = sum_h/N
    sum_h2 = sum_h*sum_h        # Σ TEMPLATE * Σ TEMPLATE = (Σ TEMPLATE)²
    sum_h2_N = sum_h2/N         # (Σ TEMPLATE)² / N
    
    h_dot = np.dot(h, h)        # Σ TEMPLATE²
    
    beta_denom = h_dot - sum_h2_N #  Σ TEMPLATE² - Σ TEMPLATE * Σ TEMPLATE/N
    
    data_cache = (N, M, sum_h, sum_h_N, sum_h2, sum_h2_N, h_dot, beta_denom)
    
    thetas = [slide_detect(x.magnitude[:,k], h, data_cache=data_cache) for k in range(x.shape[1])]
    
    ch_id = x.array_annotations.get("channel_ids", [0])[0]
    ch_name = x.array_annotations.get("channel_names", [""])[0]
    
    ret = list()
    theta_sigs = list()
    
    for kt,t in enumerate(thetas):
        θ = type(x)(t.θ, units = pq.dimensionless, t_start = x.t_start, 
                    sampling_rate = x.sampling_rate,
                    name = f"{x.name}_θ",
                    description="Sliding template detection criterion")
        θ.array_annotate(channel_names=[f"{ch_name}_θ"])
        θ.array_annotate(channel_ids=[ch_id])
        theta_sigs.append(θ)
        
        if isinstance(raw_signal, type(x)) and raw_signal.shape == x.shape and \
            raw_signal.sampling_rate == x.sampling_rate and raw_signal.times.units == x.times.units and \
                raw_signal.t_start == x.t_start and raw_signal.units == x.units:
            ret_ = extract_event_waveforms(raw_signal[:,kt], mini_duration, t.θ, threshold, peakfunc)
        else:
            ret_ = extract_event_waveforms(x[:,kt], mini_duration, t.θ, threshold, peakfunc)
        
        
        # ret_ = extract_event_waveforms(x[:,kt], mini_duration, t.θ, threshold, peakfunc)
        
        if isinstance(ret_, neo.SpikeTrain):
            ret_.annotate(waveform = waveform, θ = θ, channel_id = x.array_annotations.get("channel_ids", [0])[0])
            # NOTE: 2022-12-12 15:34:06
            # this is wrong: for spike trains, array annotations seem to need as many
            # elements as there are time stamps !
            # ret_.array_annotate(channel_names = [θ.array_annotations.get("channel_names", [""])[0]])
            # ret_.array_annotate(channel_id = [θ.array_annotations.get("channel_ids", [0])[0]])
            ret_.segment = x.segment
            
            ret.append(ret_)
            
    if len(ret):
        result = neo.core.spiketrainlist.SpikeTrainList(items = ret, segment=x.segment)
        for st in result:
            st.segment = x.segment
            
        if outputDetection:
            return result, theta_sigs
        else:
            return result
    else:
        if outputDetection:
            return None, theta_sigs
        else:
            return
    
def calculate_template_scale_offset(x, h):
    if any(v.ndim != 1 for v in (x,h)):
        raise TypeError("Expecting two 1D vectors")
    
    if x.shape[0] != h.shape[0]:
        raise ValueError("Both vectors must have the same length")
    
    N = h.shape[0]
    
    sum_h = np.sum(h)           # Σ TEMPLATE
    sum_h_N = sum_h/N
    sum_h2 = sum_h*sum_h        # Σ TEMPLATE * Σ TEMPLATE = (Σ TEMPLATE)²
    sum_h2_N = sum_h2/N         # (Σ TEMPLATE)² / N
    
    h_dot = np.dot(h, h)        # Σ TEMPLATE²
    
    beta_denom = h_dot - sum_h2_N #  Σ TEMPLATE² - Σ TEMPLATE * Σ TEMPLATE/N
    
    sum_y = np.sum(x) # Σ data
    sum_y_N = sum_y / N
    y_dot = np.dot(x,x)       # Σ(data²)
    
    hy_dot = np.dot(h, x)   # Σ(TEMPLATE * DATA)
    
    β  = (hy_dot - sum_h * sum_y_N) / beta_denom
    
    α = sum_y_N - β*sum_h_N
    
    h_ = h*β + α
    y_h = x - h_ # the error
    ε = np.dot(y_h, y_h) # explicit
    
    σ = np.sqrt(ε/(N-1))
    θ = β/σ
    
    # print(f" sum_h = {sum_h}")
    # print(f" sum_h_N = {sum_h_N}")
    # print(f" sum_y = {sum_y}")
    # print(f" sum_y_N = {sum_y_N}")
    # print(f" h_dot = {h_dot}")
    # print(f" y_dot = {y_dot}")
    # print(f" hy_dot = {hy_dot}")
    # print(f" sum_h * sum_y_N = {sum_h * sum_y_N }")
    # print(f" β_denom = {beta_denom}")
    # print(f" α = {α}")
    # print(f" β = {β}")
    # print(f" ε = {ε}")
    # print(f" σ = {σ}")
    # print(f" θ = {θ}")
    
    return  h_

def test_sliding(x, y, h, viewer, step_size=100):
    N = h.shape[0]
    M = y.shape[0]
    
    test_y = np.full((M,), fill_value = np.nan)
    test_h = np.full((M,), fill_value = np.nan)
    test_scaled_h = np.full((M,), fill_value = np.nan)
    
    test_sig = np.concatenate([y[:,np.newaxis],
                               test_y[:,np.newaxis],
                               test_h[:,np.newaxis], 
                               test_scaled_h[:,np.newaxis]],
                              axis=1)
    
    for k in range(0, M-N, 100):
        # print(f"k = {k}")
        y_ = y[k:(N+k)]
        scaled_h = calculate_template_scale_offset(y_, h)
        if k > 0:
            test_sig[:,1] = np.nan
            test_sig[:,2] = np.nan
            test_sig[:,3] = np.nan
            
        test_sig[k:(N+k), 1] = y_[:]
        test_sig[k:(N+k), 2] = h[:]
        test_sig[k:(N+k), 3] = scaled_h[:]
        # t_sig = np.concatenate([x_[:,np.newaxis], h[:,np.newaxis], scaled_h[:,np.newaxis]], axis=1)
        viewer.plot(x, test_sig)
        a = input("Press Enter to continue, any key followed by Enter to stop: ")
        if len(a):
            break
    
def slide_detect(x:np.ndarray, h:np.ndarray, padding:bool=True, data_cache = None, **kwargs):
    """
    WARNING: Expects plain numpy arrays, NOT quantity arrays!
    x: signal
    h: template
    padding: True/False
    data_cache: None, or 8-tuple with N, M, sum_h, sum_h_N, sum_h2, sum_h2_N, h_dot, beta_denom
    """
    if any(v.ndim > 1 for v in (x,h)):
        raise TypeError("Expecting two 1D signals")
    
    units = kwargs.pop("units", None)
    t_start = kwargs.pop("t_start", None)
    
    if isinstance(data_cache, tuple) and len(data_cache) == 8:
        N, M, sum_h, sum_h_N, sum_h2, sum_h2_N, h_dot, beta_denom = data_cache
    else:
        N = h.shape[0]
        M = x.shape[0]
        sum_h = np.sum(h)           # Σ TEMPLATE
        sum_h_N = sum_h/N
        sum_h2 = sum_h*sum_h        # Σ TEMPLATE * Σ TEMPLATE = (Σ TEMPLATE)²
        sum_h2_N = sum_h2/N         # (Σ TEMPLATE)² / N
        
        h_dot = np.dot(h, h)        # Σ TEMPLATE²
        
        beta_denom = h_dot - sum_h2_N #  Σ TEMPLATE² - Σ TEMPLATE * Σ TEMPLATE/N
    
    if padding:
        # pad xx with a vector of size h, by duplicating last size(h) elements
        pad = x[M-N:]
        
        time_range = range(M)
        
        xx = np.concatenate([x, pad], axis=0)
        
        α  = np.full_like(x, fill_value = np.nan) # offset
        β  = np.full_like(x, fill_value = np.nan) # scale
        ε  = np.full_like(x, fill_value = np.nan) # sse
    else:
        xx = x
        time_range = range(M-N)
        α  = np.full((M-N, ), fill_value = np.nan) # offset
        β  = np.full((M-N,), fill_value = np.nan) # scale
        ε  = np.full((M-N,), fill_value = np.nan) # sse
        
        
    
    for k in time_range:
        y = xx[k:k+N]
        sum_y = np.sum(y) # Σ data
        sum_y_N = sum_y / N
        y_dot = np.dot(y, y)       # Σ(data²)
        
        # l = k + N - 1
        # if l >= M:
        #     l = M-1
#         if k > 1:
#             sum_y = sum_y + y[-1] - xx[k-1]       # Σ DATA
#             sum_y_N = sum_y / N
#             
#             y_dot = y_dot + y[-1]**2 - xx[k-1]**2 # Σ DATA²
            
            # sum_y = sum_y + xx[l] - xx[k-1]       # Σ DATA
            # y_dot = y_dot + xx[l]**2 - xx[k-1]**2 # Σ DATA²
            
            
        hy_dot = np.dot(h, y)   # Σ(TEMPLATE * DATA)
        
        # SCALE = [Σ(TEMPLATE * DATA) - Σ TEMPLATE * Σ DATA /N] / (Σ TEMPLATE² - Σ TEMPLATE * Σ TEMPLATE / N)
        
        β[k]  = (hy_dot - sum_h * sum_y_N) / beta_denom
        
        # α[k] = (sum_y - β[k]*sum_h)/N
        α[k] = sum_y_N - β[k]*sum_h_N
        
        
        # Calculate the SSE
        # the scaled (fitted) template:
        h_ = h*β[k] + α[k]
        y_h = y - h_ # the error
        ε[k] = np.dot(y_h, y_h) # explicit
        
        # ε[k] = y_dot + β[k]*β[k] * h_dot + N*α[k]*α[k] - 2 * (β[k]*hy_dot + α[k]*sum_y - α[k]*β[k]*sum_h)
        # ε[k] = y_dot + β[k]**2 * h_dot + N*α[k]**2 - 2 * (β[k]*hy_dot + α[k]*sum_y - α[k]*β[k]*sum_h)
        
        # the standard error
        # σ[k] = np.sqrt(ε[k]/(N-1))
        
        # the detection criterion: scale / standard error
        # θ[k] = β[k] / σ[k]
        
    σ = np.sqrt(ε/(N-1))
    θ = β/σ
    
    Result = collections.namedtuple("Result", ["θ", "α", "β", "ε", "σ"])
    ret = Result(θ , α, β, ε, σ)
    # Result = collections.namedtuple("Result", ["θ", "α", "β", "ε", "σ", "xx", "x"])
    # ret = Result(θ , α, β, ε, σ, xx, x)
    
    return ret
        
    # return θ , α, β, ε, σ, xx
    
def extract_event_waveforms(x:typing.Union[neo.AnalogSignal, DataSignal], duration, θ, threshold, peakfunc):
    """
    Extracts detected mPSC waveforms.
    
    Waveforms are detected by comparing the θ signal (containing a detection
    signal) to the scalar `threshold`, to determine the start & end time stamps
    of each waveform in the parent signal `x`.
    
    The start time stamps are stored in a SpikeTrain, and the peak time
    stamps are embedded as a quantity array in the SpikeTrain's annotations. The
    waveforms are also embedded in the spike train's `waveforms` attribute, and 
    also returned as a collection of analog signals 
    
    Parameters:
    ==========-
    x: single-channel signal
    duration: duration of the mPSC template 
    θ: single-channel signal with detection criterion (can be cross-correlation
        of the result of sliding deteciton algorithm)
    threshold: scalar detection threshold; samples in the θ that are >= threshold 
        are considered to correspond to samples in the detected mPSCs
    peakfunc: function to extract the sample index of the extremum in the 
        mPSC waveform (i.e., either argmax, for upward event waveform, or argmin
        for downward event waveform)
    
    Returns:
    ========
    A spike train, a sequence of neo signals with fitted copies of the waveforms
    and a sequence of neo signals containing aligned copies of the waveforms.
    
    CAUTION: 2022-12-18 23:11:33
    This extracts single-channel waveforms, which will carry the array annotations
    of the single-channel signal where the waveforms have been sliced from. 
    
    The waveforms are then concatenated into a 3D array stored as the `waveforms`
    attribute of the resulting spike train, losing their array annotations.
    
    When these waveforms are individually fitted, they will be converted again
    to individual analog signals waveforms which will be passed to the fitting
    function. As a result, they will gain a second channel 
    (channel 0 ↦ recorded waveform; channel 1 ↦ fitted waveform).

    There is no point using array annotations with the individual waveforms for 
    the following reasons:
    1. the waveform analgsignals will lose their metainformation (array annotations
    AND annotations) when embedded in the spike train
    2. after fitting, the original array annotations of the waveform signals (if
    present) will be incompatible with the shape of the new signals (which will
    contain both the original data and the fit curve, as explained above)
    
    Here, the array_annotations of the SINGLE-CHANNEL waveforms are merged as 
    array annotations in the spike train (where the keys are mapped to an 
    array of scalars with as many elements as spikes). These
    spike train array annotations are then used to carry the relevant metadata
    per spike, further into the analysis function(s).
    
    """
    if not isinstance(x, (neo.AnalogSignal, DataSignal)):
        raise TypeError(f"Expecting a neo.AnalogSignal or DataSignal; got {type(x).__name__} instead")
    if x.shape[1] > 1:
        raise TypeError(f"Expecting a vector; instead, the signal has {x.shape[1]} channels")
    flags =  θ >= threshold
    flag_bounds = np.ediff1d(flags.astype(np.dtype(float)))
    peak_begins = np.where(flag_bounds > 0)[0] # sample indices
    peak_ends   = np.where(flag_bounds < 0)[0] # sample indices
    
    # print(len(peak_begins), len(peak_ends))
    
    if len(peak_begins) == 0 or len(peak_ends) == 0:
        return # nothing detected ?!?
    
    if len(peak_begins) > len(peak_ends):
        if peak_begins[-1] > peak_ends[-1]:
            peak_begins = peak_begins[0:-1]
        elif peak_begins[-1] < peak_ends[-1]:
            peak_begins = peak_begins[1:]
            
    elif len(peak_begins) < len(peak_ends):
        if peak_begins[0] > peak_ends[0]:
            peak_ends = peak_ends[1:]
            
        elif peak_begins[-1] > peak_ends[-1]:
            peak_ends = peak_ends[0:-1]
            
    # print(f"peak begin, end: {[v for v in zip(peak_begins, peak_ends)]}")
        
    θmaxima = [np.argmax(θ[v[0]:v[1]]) + v[0] for v in zip(peak_begins, peak_ends) if len(θ[v[0]:v[1]]) > 0]
    
    # print(f"θmaxima {θmaxima}")
    mini_starts = x.times[θmaxima]
    
    mini_ends = mini_starts + duration
    
    # remove past-the-end intervals
    intervals = [(t0,t1) for (t0,t1) in zip(mini_starts, mini_ends) if t1 < x.t_stop]
    
    # generate new starts after removal of past-the-end
    starts = np.array([interval[0] for interval in intervals])
    # ends = starts + duration
    
    # for ke, me in enumerate(mini_ends):
    #     if me > x.t_stop:
    #         me = x.t_stop
    # print(mini_starts)

    minis = [x.time_slice(*interval) for interval in intervals]
    # minis = [x.time_slice(t0,t1) if t1 < x.t_stop else x.time_slice(t0,x.t_stop) for (t0, t1) in zip(mini_starts, mini_ends)]
    # minis = [x.time_slice(t0,t1) for (t0, t1) in zip(mini_starts, mini_ends) if t1 < x.t_stop ]
    if len(minis) == 0:
        return
    
    mini_peaks = np.array([w.times[peakfunc(w[:,0])] for w in minis])*x.times.units

    chname = x.array_annotations.get("channel_names", [""])[0]

    if len(chname.strip())==0:
        chname = "mPSC"
    chname +="_"
        
    for km, m in enumerate(minis):
        m.annotations["Accept"] = np.array([True])
        m.name = f"{chname}{km}"
        m.array_annotate(**x.array_annotations)
    
    # NOTE: 2022-12-17 22:08:57 array_annotating a SpikeTrain:
    # Normally, neo.DataObject take array annotations with as many elements per
    # key as the sie on the last axis (highest dimension).
    # For AnalogSignal and such, this is also the number of channels (2nd dimension
    # of the underlying data array, where one channel is a column vector).
    #
    # Therefore, the API dealing with array_annotations checks for the annotation
    # length against the size of the DataObject's data array on its last axis
    # (i.e., shape[-1]).
    #
    # However, for a SpikeTrain, things are different: the "data" array in a 
    # SpikeTrain is, BY DEFINITION, a 1D array (with shape (N,)). This means 
    # that for a SpikeTrain array.shape[-1] is the same as array.shape[0] !!!
    # If this is what the neo authors have intended (this is not explicit in 
    # the documentation) then the justification seems to be that the array
    # annotations of a SpikeTrain are intended to provide data related to
    # each individual spike in the SpikeTrain. This is perfectly justifiable
    # given that the spike waveform data is only stored as a plain numpy array, 
    # and not as a signal, in the SpikeTrain (so that any of the array annotations
    # associated with the original signal from where the spikes were taken are 
    # lost). 
    # This is unlike the array annotations for, say, an AnalogSignal, where they 
    # provide information related to each individual channel, and NOT to individual
    # data points (the latter being practically penalizing in terms of resources
    # and not very useful anyway).
    ret = neo.SpikeTrain(starts, t_start = x.t_start, units = x.times.units,
                         t_stop = x.times[-1], sampling_rate = x.sampling_rate,
                         name="mPSCs")
    
    # NOTE: 2022-12-17 22:22:41 
    # Although it would have been easier (and perhaps faster) to call directly
    # np.concatenate on the wave's magnitude, as in the next line,
    # mPSCtrain_waves = np.concatenate([w.magnitude[:,:,np.newaxis] for w in minis], axis=2)
    # we would be losing the array annotations (see NOTE: 2022-12-17 22:08:57);
    # therefore it would be better to merge signals one by one.
    #
    # However, this aproach has two shortcomings:
    # 1) in order to merge them, minis must have the same t_start (which, of
    # of course, they have not). We could set their time starts to 0, being
    # mindful that the TRUE start time is stored in the SpikeTrain, and their
    # peak time has already been collected above
    #
    # 2) The merged signal would efectively be a 2D array, whereas the 
    # the waveforms of the SpikeTrain need to be a 3D array. Taking the magnitude 
    # of the merged minis and adding add a new axis would NOT solve this because
    # the new axis would be a singleton (i.e., all minis in the merged object
    # would be treated as channels of a same signal, and NOT as separate waveform
    # signals).
    #
    # Therefore the best approach is to np.concatenate as above, but to also
    # merge their array annotations separately
    #
    mPSCtrain_waves = np.concatenate([w.magnitude[:,:,np.newaxis] for w in minis], axis=2)
    minis_arr_ann = minis[0].array_annotations
    for mw in minis[1:]:
        minis_arr_ann = neoutils.merge_array_annotations(minis_arr_ann, mw.array_annotations)
    ret.waveforms = mPSCtrain_waves.T
    # print(f"membrane.extract_event_waveforms: waves shape {mPSCtrain_waves.shape}, waveforms shape {ret.waveforms.shape}")
    ret.segment = x.segment
    
    # print(f"extract_event_waveforms x.name {x.name}")
    ret.annotate(
                 peak_time = mini_peaks, 
                 wave_name = [w.name for w in minis],
                 event_fit = [w.annotations.get("event_fit", None) for w in minis],
                 Accept = np.concatenate([w.annotations["Accept"] for w in minis]),
                 source="Event_detection",
                 signal_units = x.units, 
                 signal_origin = x.name,
                 datetime=datetime.datetime.now(),
                 Aligned = False,
                 )
    
    ret.array_annotate(**minis_arr_ann)
    ret.array_annotate(peak_time = mini_peaks)
    ret.array_annotate(wave_name = [w.name for w in minis])
    ret.array_annotate(accept = ret.annotations["Accept"])
    # ret.array_annotate(accept = np.concatenate([w.annotations["Accept"] for w in minis]))
    
    return ret

def detect_Events(x:typing.Union[neo.AnalogSignal, DataSignal], waveform:typing.Union[np.ndarray, tuple, list]=(0., -1., 0.01, 0.001, 0.01, 0.02), useCBsliding:bool=False, threshold:typing.Optional[float]=None, outputDetection:bool=False, raw_signal=None):
    """Detect spontaneous events in a signal.

    Uses cross-correlation with a waveform, or the sliding detection algorithm
    by Clements & Bekkers, 1997, (Biophys J.).
    
    Parameters:
    ==========
    
    x: neo.AnalogSignal containing the recorded membrane current that 
        will be scanned for events. Typically this is single-channel, meaning it
        is a 2D array with a singleton 2nd axis (e.g., x.shape = (n,1) where `n`
        is the number of samples in `x`)
    
    waveform: neo.AnalogSignal or 1D numpy array (vector, i.e., 
        waveform.shape = (m,) where `m` is the number of samples in `waveform`).
    
        Contains an event model (ie. a "synthetic" waveform) or a "template" 
        waveform extracted from a signal.
    
        ATTENTION: Make sure this model waveform has the SAME SAMPLING RATE as 
        the signal!!!
    
        ALTERNATIVELY, the waveform can be specified by a sequence of six scalars, 
        where the first five are the Clements & Bekkers 1997 model parameters:
        α, β, x₀, τ₁ and τ₂ (see models.Clements_Bekkers_97 for details)
        and the 6ᵗʰ element is the duration of the model waveform (which will
        be generated ad-hoc); this last element is assumed to be in the units of
        the domain of x.
    
        By default, waveform is (0., -1., 0.01, 0.001, 0.01, 0.05) which means,
        for a membrane current signal `x` in pA:
    
        α  =  0.0 pA (ie. no offset)
        β  = -1.0 (i.e. downward deflection)
        x₀ =  0.01 (i.e. 10 ms from the start of the waveform)
        τ₁ =  0.001 (i.e., rising time constant of 1 ms)
        τ₂ =  0.01  (i.e., decay time constant of 10 ms)
        
        and 50 ms duration of the model waveform
    
        NOTE: When specified in this way the waveform will be generated ad-hoc
        using the sampling rate of the signal `x`.
    
        For example, if creating the waveform as a plain numpy array:
        
        t_start     = 0     # [s]
        duration    = 0.2   # [s]
        sr          = 1e4   # [Hz]
        
        t = np.linspace(0, duration, num = sr * duration)
        model = models.Clements_Bekkers_97(x, parameters)
        
        As a convenience, you can use PSCwaveform(...) function in this module 
        to generate a synthetic  waveform as a neo.AnalogSignal.
        
    useCBsliding:bool, default is False
        When True (the default), uses the Clements & Bekkers optimally scaled 
        template sliding detection, with the waveform as a template.
    
        When False, uses cross-correlation between the signal and the waveform 
    
    threshold: float; optional, default None.
        This value is the threshold for the detection criterion used in the 
        Clements & Bekkers 1997 Biophys J paper
    
        When threshold is None, the threshold of detection is the calculated 
        root-mean-square of the detection criterion signal output by the sliding
        template detection method.
    
        This parameter is only used when useCBsliding is True.
    
    outputDetection:bool, default is False
        When True, the function also returns the detection criterion (here, the 
        cross-correlation signal)
    
    raw_signal: analog signal with the same shape and domain as the signal where
        the detection took place, default is None
        When given, the waveforms will be extracted from THIS signal using the 
        time stamps in the spike train.
        This is useful when detection was performed on a pre-processed (e.g., 
        smoothed) signal but the "raw" waveforms are required.
    
    Returns:
    ========
    A dict with keys:
    "mini_starts": a quantity array with the start times of the detected waveforms
    
    "mini_peaks": a quantity array with the times of the "mini's" peak (or trough)
    
    "minis": a list of AnalogSignal objects with the detected "mini" waveforms.
    
    "waveform": the actual waveform used as model or "template". 
    
        This is either:
    
        • the realization of the synthetic mPSC (when the `waveform` parameter 
            is the sequence of model parameters)
    
        • the `waveform` parameters itself, when it is a template (synthetic or
            otherwise)
        
    ATTENTION: When detection has failed, returns None
    
    """
    # print(f"membrane.detect_Events: waveform is a {type(waveform).__name__}")
    if not isinstance(x, (neo.AnalogSignal, DataSignal)):
        raise TypeError(f"Expecting a neo.AnalogSignal or DataSignal; got a {type(x).__name__} instead")

    if isinstance(waveform, (np.ndarray,neo.core.basesignal.BaseSignal)):
        if not dt.is_vector(waveform):
            raise TypeError("waveform expected to be a vector")
    
    elif isinstance(waveform, (tuple, list)):
        if len(waveform) == 6:
            waveduration = waveform[5] * x.times.units
            
            waveform = PSCwaveform(waveform[0:-1], units = x.units,
                                     t_start = 0*x.times.units,
                                     duration = waveduration,
                                     sampling_rate = x.sampling_rate)
            
    else:
        raise ValueError("Incorrect waveform specification")
    
    if isinstance(waveform, neo.core.basesignal.BaseSignal):
        mini_duration = waveform.duration
    else:
        # NOTE: 2022-10-25 18:16:26
        # you need to make sure the waveform (if a plain numpy array) has the
        # same "sampling rate" as the signal
        mini_duration = len(waveform) / x.sampling_rate
    
    if sigp.is_positive_waveform(waveform):
        peakfunc = np.argmax
    else:
        peakfunc = np.argmin
        
    if useCBsliding:
        return detect_Events_CBsliding(x, waveform, threshold, outputDetection=outputDetection, raw_signal=raw_signal)
            
    else:
        # 1) normalize the model waveform - only for the cross-correlation method
        # if not useCBsliding:
        mdl = sigp.normalise_waveform(waveform)
        
        mdl = np.atleast_2d(waveform)
        
        if mdl.shape[1] > 1:
            mdl = mdl.T
            
        N = mdl.shape[0]
        M = x.shape[0]

        # a list of cross-correrlation signals, one per signal channel (i.e. each
        # data on 2nd axis)
        xc = [scipy.signal.correlate(x[:,k], mdl, mode="valid") for k in range(x.shape[1])]
        
        ret = list()
        
        # waves = list()
        
        # for each cross-correlation:
        # • detrend it
        # • scale it to 10/max so that thresholding is done in this range (0..10)
        #   ∘ detrended & unscaled is stored in annotations as θ
        #   ∘ detrended & scaled is stored in annotations as θ_norm
        # • thresholding is always performed on θ_norm
        thetas = list()
        
        for k, c in enumerate(xc):
            dxc = scipy.signal.detrend(c, type="constant",axis=0)
            if threshold is None:
                thr = sigp.rms(dxc) * 10 / dxc.max()
            else:
                thr = threshold
            
            dxc_n = np.copy(dxc) # because next is mod-ing in place
            dxc_n = sigp.scale_waveform(dxc_n, 10, np.max(dxc[~np.isnan(dxc)]))

            θ = type(x)(dxc, units = pq.dimensionless, t_start = x.t_start,
                        sampling_rate = x.sampling_rate,
                        name = f"{x.name}_θ",
                        description = "Template cross-correlation")
            
            θ_norm = type(x)(dxc_n, units = pq.dimensionless, t_start = x.t_start,
                        sampling_rate = x.sampling_rate,
                        name = f"{x.name}_θ_norm",
                        description = "Template cross-correlation (normalized)")
            
            thetas.append(θ_norm)
            
            if isinstance(raw_signal, type(x)) and raw_signal.shape == x.shape and \
                raw_signal.sampling_rate == x.sampling_rate and raw_signal.times.units == x.times.units and \
                    raw_signal.t_start == x.t_start and raw_signal.units == x.units:
                ret_ = extract_event_waveforms(raw_signal[:,k], mini_duration, dxc_n, thr, peakfunc)
            else:
                ret_ = extract_event_waveforms(x[:,k], mini_duration, dxc_n, thr, peakfunc)
            
            if isinstance(ret_, neo.SpikeTrain):
                ret_.annotate(waveform = waveform, θ = θ, θ_norm=θ_norm,
                              channel_id = x.array_annotations.get("channel_ids", [0])[0])
                ret_.segment = x.segment
                ret.append(ret_)
                # waves.append(waves_)
                
        if len(ret) == 0:
            if outputDetection:
                return None, thetas
            else:
                return
        
        result = neo.core.spiketrainlist.SpikeTrainList(items = ret, segment=x.segment)
        for st in result:
            st.segment = x.segment
        
        if outputDetection:
            return result, thetas
        else:
            return result

def batch_EventDetection(x:typing.Union[neo.Block, neo.Segment, typing.Sequence[neo.Segment]], waveform:typing.Union[np.ndarray, tuple, list]=(0., -1., 0.01, 0.001, 0.01, 0.02), Im:typing.Union[int, str] = "IN0", epoch=None, clear_spiketrains:bool=True, fit_waves:bool=False):
    """Batch event detection - e.g., mini EPSC, IPSC, etc.
    
    Detects and analyses events (e.g. mini ePSCs) in a neo.Block, neo.Segment, or a sequence of 
    neo.Segment objects.
    
    Calls detect_Events for each segment in `x`, and generates a spiketrain with
    the the stamps of the detected mPSCs. The spiketrain's annotation contain 
    the mandatory key "source" mapped to the string "Event_detection", in order
    to identify this spike train among other (possible) spike trains held in the
    segment.
    
    NOTE: a neo.Block already contains a collection of segments, see 
    neo API reference:
    https://neo.readthedocs.io/en/stable/api_reference.html
    
    The segments (sweeps) are expected to contain a signal with the 
    recorded membrane current for mini EPSCs.
    
    The signal is identified by the "Im" parameter to this function (see below).
    
    Furthermore, each segment MUST have an epoch, named "mEPSC", which sets the
    region in the signal, where minis are going to be detected and analysed.
    
    Segmenst without such an epoch will be skipped.
    
    The results are returned as a list of pairs (SpikeTrain, list of AnalogSignal)
    with one pair per segment in the Block.
    
    In each pair, the SpikeTrain contains the time stamps of the detected minis,
    and the list of AnalogSignal object contains the detected mEPSC waveforms.
    
    Individual rejection of mEPSC rejection must be done manually for now.
    
    Parameters:
    ==========
    x: neo.Block or a sequence (tuple, list) of neo.Segments, where each segment
        contains:

        • a neo.AnalogSignal identified by the `Im` parameter below, which 
        represents the recorded membrane current with putative miniature or 
        spontaneous post-synaptic currents (mEPSCs or mIPSCs) 
    
        • a neo.Epoch with the name specified in the `epoch_name` parameter
    
    waveform: numpy array (1D), or a sequence of six float scalars
        
        • when a numpy array, this is a "template" waveform: usually, a synthetic
            mPSC generated by the `models.Clements_Bekkers_97` function, or a
            'real-life' mPSC waveform (usually averaged from several records, for
            a better signal/noise ratio). You probably want to use the former, 
            created with some default parameters.
    
        • when a sequence of floats, it contains the five parameters for the
            Clements & Bekkers 1997 waveform model, AND the duration of the
            synthetic waveform whcih will be generated ad hoc (see also the 
            `detect_Events` function in this module).
    
    Im: str or int. The identifier of the membrane current signal contained in
        the segments of `x`.
    
        When a str, its Im is the name of the signal (e.g., "IN0", "Im_prim_0", 
        etc., as set in the configuration of the acquisition software and/or 
        protocol).
    
        When an int, Im is the index of the signal in the segment's `analogsignals`
        attribute.
    
        ATTENTION: 
        • when Im is a str, the signal where mPSC detection is performed
        can be at any index in the segment's analogsignals collection (a very
        unusual situation), but MUST be present in ALL segments of `x`.
    
        • when Im is an int, it must be a valid index for the segment's
        analogsignals collection.
    
    epoch:str, int, sequence of str or int, or None; default is None
        Optional specification of an epoch (or epochs) where mPSC detection will
        occur.
    
        NOTE: This will retrict mPSC detection to a selected region (or regions)
        of the signal without interference from other tests (e.g. seal test, etc)
        
        • when a str, this is the name of the epoch where mPSC detection will be 
        performed.
    
        • when an int, this is the index of the epoch, in the segment's epochs
    
        • when a sequence of str or int: the names, or indices, of the epochs for
        mPSC detection
    
        NOTE: if the speification points to a non-existent epoch, this will be 
        ignored and no detection will take place
    
        • when None (the default), the detection will be performed on the ENTIRE
        signal (almost surely not what you want in most cases)
    
    clear_spiketrains:bool, optional, default is True
        When True, all SpikeTrain objects in the segments of `x` are removed.
        Typically, this is to allow a "clean" rerun of the mPSC detection. 

        As  explained below (see "Side effects") the time stamps of any detected
        mPSCs in each segment are stored in a SpikeTrain embedded in the segment,
        in `x`.
    
        The `clear_spiketrains = True` flag allows re-running the detection 
        without accumulating SpikeTrain from previous runs.
    
    fit_waves:bool, optional, default is False
        When True, the Clements & Bekkers 1997 model will be fitted to the 
        each of the detected mPSC waveforms, using the waveform's parameters as
        initial values for the model. 
        
        CAUTION: Fitting each mPSC waveform will significantly increase the
        execution time of this function.
    
    Returns:
    =======
    A tuple with :
        • A list where each element is a list of detected mPSC waveforms (as 
            AnalogSignals) or None, for each segment in `x`. 
            If `fit_wave` is True, then each mPSC waveform will have an additional
            channel containing the fitted curve, and the fit result will be
            embedded in its annotations.
    
        • The template waveform as an AnalogSignal
    
    Side effects:
    =============
    The time stamps for the detected mPSCs (i.e., the times of the mPSC waveforms
    starts) are embedded as a SpikeTrain in the segments where mPSC detection was
    successful.
    
    The waveforms of the detected mPSCs are attached to the embedded SpikeTrain 
    object.
    
    
    """
    raise NotImplementedError("Must adapt to new data layout")
    
    if clear_spiketrains:
        neoutils.clear_spiketrains(x)
    
    result = list()
    
    if isinstance(x, neo.Block):
        segments = x.segments
        data_name = x.name
        
    elif isinstance(x, neo.Segment):
        segments = [x]
        data_name = x.name
        
    elif isinstance(x, (tuple, list)) and all(isinstance(s, neo.Segment) for s in x):
        segments = x
        data_name = "Segments"
        
    else:
        raise TypeError(f"Expecting a neo.Block, a neo.Segment, or a sequence of neo.Segments; got {type(x).__name__} instead")
    
    if len(segments) == 0:
        warnings.warn("No data to analyse")
        return None, None
    
    for k, s in enumerate(segments):
        dstring = f"mEPSC detected in {data_name} segment {s.name}"
        
        try:
            if isinstance(Im, str):
                im = s.analogsignals[neoutils.get_index_of_named_signal(s, Im)].copy()
                
            elif isinstance(Im, int):
                im = s.analogsignals[Im].copy()
                
            else:
                result.append(None)
                continue
            
        except:
            warnings.warn(f"No membrane current signal with index or name {Im} is found in segment {k}")
            result.append(None)
            continue
        
        # print(s.epochs)
        start_times = list()
        peak_times  = list()
        mini_waves  = list()
        
        # NOTE: 2022-10-26 23:35:36
        # We use the same template across all segments; to avoid repeated function
        # calls, we cache the template waveform here, once it has been generated
        # as needed
        template = None 
        
        if epoch is None:
            if template is None:
                detection = detect_Events(im, waveform)
            else:
                detection = detect_Events(im, template)
            
            if detection is None:
                result.append(None)
                continue
            
            start_times = detection["mini_starts"]
            peak_times  = detection["mini_peaks"]
            mini_waves  = detection["minis"]
            
            if template is None:
                template = detection["waveform"]
                
        else:
            if len(s.epochs) == 0:
                warnings.warn(f"The {k}-th segment of {data_name} Block has no epochs!")
                result.append(None)
                continue
            
            if isinstance(epoch, str):
                mPSCdetectepochs = [e for e in s.epochs if e.name == epoch]
                if len(mPSCdetectepochs) == 0:
                    warnings.warn(f"The {k}-th segment of {data_name} Block does not have epoch(s) named {epoch}")
                    result.append(None)
                    continue
                
            elif isinstance(epoch, int):
                if epoch in range(-1*len(s.epochs), len(s.epochs)):
                    mPSCdetectepochs = [s.epochs[epoch]]
                    
                else:
                    warnings.warn(f"Epoch index {epoch} is not valid for the {k}-th segment of {data_name} Block with {len(s.epochs)} epochs")
                    result.append(None)
                    continue
                
            elif isinstance(epoch, (tuple, list)) and all(isinstance(e, (str, int)) for e in epoch):
                mPSCdetectepochs = list()
                
                for e in epoch:
                    if isinstance(e, str):
                        me_ = [e_ for e_ in s.epochs if e_.name == e]
                        if len(me_) == 0:
                            warnings.warn(f"The {k}-th segment of {data_name} Block has no epoch named {e}")
                        mPSCdetectepochs.extend(me_)
                        
                    elif isinstance(e, int):
                        if e in range(-1*len(s.epochs), len(s.epochs)):
                            mPSCdetectepochs.append(s.epochs[e])
                        else:
                            warnings.warn(f"Epoch index {e} is not valid for the {k}-th segment of {data_name} Block with {len(s.epochs)} epochs")
                            
            
            if len(mPSCdetectepochs) == 0:
                warnings.warn(f"No epochs with specified name or index wwere found in the {k}-th segment of {data_name} Block")
                result.append(None)
                continue
            
            # mPSCdetectepochs = mPSCdetectepochs[0]
            mini_waves = list()
            mini_starts = list()
            mini_peaks = list()
            
            
            for detect_epoch in mPSCdetectepochs:
                sig = im.time_slice(detect_epoch.times[0], detect_epoch.times[0] + detect_epoch.durations[0])
                if template is None:
                    detection = detect_Events(sig, waveform) # only generate template ONCE
                else:
                    detection = detect_Events(sig, template) 
                    # starts, peaks, epoch_minis, template = detect_Events(sig, template) 
                if detection is None:
                    continue
                
                template = detection["waveform"]
                
                mini_waves.extend(detection["minis"])
                mini_starts.append(detection["mini_starts"])
                mini_peaks.append(detection["mini_peaks"])
                
            if len(mini_starts) and len(mini_peaks):
                start_times = np.hstack(mini_starts) * mini_starts[0].units
                peak_times = np.hstack(mini_peaks) * mini_peaks[0].units
            
        if len(start_times) > 0:
            if isinstance(template, neo.core.basesignal.BaseSignal) and len(template.description.strip()):
                dstring += f" using {template.description}"
                
            train = neo.SpikeTrain(start_times, t_stop = im.t_stop, units = im.times.units,
                                    t_start = im.t_start, sampling_rate = im.sampling_rate,
                                    name = f"{data_name}_{s.name}_PSCs", description=dstring)
            
            # # waves = np.concatenate([w.magnitude[:,:,np.newaxis] for w in mini_waves], axis=2)
            # train.waveforms = waves
            train.annotations["peak_time"] = peak_times
            train.annotations["source"] = "Event_detection"
            
            if isinstance(template, neo.core.basesignal.BaseSignal):
                train.annotations["PSC_parameters"] = template.annotations["parameters"]
            # elif isinstance(waveform, neo.core.basesignal.BaseSignal):
            #     train.annotations["mPSC_parameters"] = waveform.annotations["parameters"]
            # elif isinstance(waveform, (tuple, list)) and len(waveform)==6:
            #     train.annotations["mPSC_parameters"] = waveform[:-1]
                # CAUTION here 2022-10-26 23:09:15 possible BUG
                
            # NOTE: 2022-10-27 23:14:18
            # fit mPSC waves if asked
            if fit_waves:
                for k,w in enumerate(mini_waves):
                    fw = fit_Event(w, template.annotations["parameters"])
                    
                    mini_waves[k] = fw
                
            # this below is (time, channel, spike)
            train_waves = np.concatenate([w.magnitude[:,:,np.newaxis] for w in mini_waves], axis=2)
            
            # a SpikeTrain expects (spike, channel, time) hence train_waves.T
            train.waveforms = train_waves.T 
            
            s.spiketrains.append(train)
            
            result.append(mini_waves)
        else:
            result.append(None)
        
    return result, template
        
    
def fit_Event(x, params, lo:typing.Optional[typing.Sequence]=None, up:typing.Optional[typing.Sequence]=None):
    """Convenience wrapper to curvefitting.fit_Event_model with suitable lower & upper bounds
    
    Modifies signal `x` in-place.
    
    Parameters:
    ===========
    x: neo.AnalogSignal or DataSignal) with an event such as a mmini ePSC   
        (i.e. fragment of a signal)
    
    params: sequence of float scalars; these are the initial parameter values for
            the Clements & Bekkers '97 model:
            
            α, β, x₀, τ₁ and τ₂, where:
    
            α  = offset (usually, 0.) in signal units, usually [pA];
        
            β  = scale (-1. for downward waveform; 1. for upward waveform);
                 dimensionless
        
            x₀ = delay ("onset") [ms];
        
            τ₁, τ₂ = the "rise" and "decay" time constants, respectively, in [ms]
    
        ATTENTION: Alternatively, the `params` may be an analog signal (a "template")
            In this case, the `lo` and `up` parameters (see below) are ignored,
            and only a R² value will be calculated between the experimental data
            and the template.
    
    lo, up: None, or a sequence of floats of the same length as params, with the
            the lower and upper bounds, respectively, for the model parameters.
    
            When None they will assume the following default values:
    
            • for downward waveform (params[1] < 0):
                        α,         β,        x₀,     τ₁        τ₂:
                lo  = ( 0.,       -np.inf,   0.,     1.0e-4,   1.0e-4)
                hi  = ( np.inf,    0.,       np.inf, 0.01,     0.01)
    
            • for upward waveform (params[1] >=0 ):
                        α,         β,        x₀,     τ₁        τ₂:
                lo  = ( 0.,        0,        0.,     1.0e-4,   1.0e-4)
                hi  = ( np.inf,    np.inf,   np.inf, 0.01,     0.01)
    
    WARNING: the structure of the params lo and up sequences is NOT checked.  
        If you feed garbage the function will either throw an exception, or will
        fail to give you what you want.
    
    Returns:
    =======
    An analog signal (neo.AnalogSignal) with two channels:
    • the experimental data (the original waveform to which the fitting was performed)
    • the fitted curve (optional; this IS NOT present when `params` is a template)
    
    Its `annotations` attribute (a dict) contains the following mapping:
    • "event_fit" → the fit result, an OrderedDict with the results of the 
        fitting function, in this case: curvefitting.fit_Event_model, mapping:
        ∘ "Fit"             → the result of scipy.optimize.least_squares
        ∘ "Coefficients"    → the fitted parameters
        ∘ "Rsq"             → The R² value of the fit (a.k.a goodness of fit)
        ∘ "template"        → True when `params` is a template; False, otherwise
    
        NOTE: When `params` is a template waveform, only the "Rsq" mapping is present
    
    • "amplitude" → the amplitude of the original data (waveform)
    • "fit_amplitude" → the amplitude of the fitted curve (typically, smaller 
                    than the amplitude of the experimental waveform data, due to
                    the noise in the latter)
    
    """
    
    if not isinstance(x, (neo.AnalogSignal, DataSignal)):
        raise TypeError(f"Data in 'x' expected to be a neo.AnalogSignal or DataSignal; got {type(x).__name__} instead")
    
    
    # NOTE: 2022-10-27 22:44:40
    # For fitting, waveform domain must start at 0, therefore we shift is needed,
    # but cache the original t_start to restore afterwards
    t_start = x.t_start
    if x.t_start.magnitude != 0:
        x_ = neoutils.set_relative_time_start(x)
    else:
        x_ = x
    
    l, c, e, _ = sigp.state_levels(x_[:,0], axis=0)
    
    if isinstance(params, neo.AnalogSignal): # template waveform given
        if params.t_start.magnitude != 0:
            params = neoutils.set_relative_time_start(params)
            
        Rsq = crvf.fit_Event_wave(x_, params)
        x.annotations["event_fit"] = {"Rsq": Rsq, "template": True, "amplitude":sigp.waveform_amplitude(params)}
        x.annotations["amplitude"] = sigp.waveform_amplitude(x)
        
    else:
    
        # NOTE: 2022-10-27 22:53:50
        # FYI these are:
        # α, β, x₀, τ₁ and τ₂
        # same structure for lower & upper bounds (respectively, lo & up)
        params = list(params)
        params[0] = l[1] # adapt the offset to the DC components in the waveform
        
        if lo is None:
            if params[1] < 0:   # downward mPSC
                lo = (0., -np.inf, 0., 1e-4, 1e-4)
            else:               # upward mPSC
                lo = (0., 0, 0., 1e-4, 1e-4)
                
        if up is None:
            if params[1] < 0:   # downward mPSC
                up = (np.inf, 0., np.inf, 0.01, 0.01) # fix upper bounds for the time constants to 0.1.
            else:
                up = (np.inf, np.inf, np.inf, 0.01, 0.01) # fix upper bounds for the time constants to 0.1.
                
        
        # NOTE: 2022-10-27 22:45:23
        # Normally, the waveform has just one channel: the mPSC "cropped" out from 
        # the signal it was detected in
        #
        # However, if the waveform was fitted before, the fitted curve is in the 2nd
        # channel. To avoid appending further curves upon re-fitting, we use the 1st
        # channel as data to fit, and overwrite the 2nd channel with the fitted curve
        # if a 2nd channel exists, else we just append the newly fit curve as 2nd 
        # channel
        
        xx = x_[:,0] # this always works even if there is only one channel, 
                    # and returns an AnalogSignal
                    
        fitresult = crvf.fit_Event_model(xx, params, bounds = [lo, up])
        
        fitted_x = type(x)(fitresult[0], units = x.units, t_start = x.t_start, sampling_rate = x.sampling_rate, name="EventModelFit")
        fitted_x.segment = x.segment
        
        if x.shape[1] > 1:
            x[:,1] = fitted_x # modifies x in-place
        else:
            for annkey in x.array_annotations:
                if annkey == "channel_names":
                    fitted_x.array_annotations[annkey] = [f"{annkey[0]}_fit"]
                elif annkey == "channel_ids":
                    fitted_x.array_annotations[annkey] = x.array_annotations[annkey][0] + "_fit"
                else:
                    fitted_x.array_annotations[annkey] = x.array_annotations[annkey]
                    
            name = f"{x.name}_{fitted_x.name}"
            x = x.merge(fitted_x) # returns a new x
            x.name = name
        
        # NOTE: 2022-10-27 22:44:50
        # Restore the domain start of the waveform (see NOTE: 2022-10-27 22:44:40)
        x.t_start = t_start
        x.annotate(event_fit = fitresult[1],
                   amplitude = sigp.waveform_amplitude(x[:,0]))
        
        x.annotations["event_fit"]["template"] = False
        x.annotations["event_fit"]["amplitude"] = sigp.waveform_amplitude(x[:,1])
        
    
    return x

def prep_for_nsfa(data):
    """Helper for the nsfa function
    Prepares an average event waveform and the variance of fluctuations.
    Parameters:
    ==========
    data: A collection (i.e., tuple, list) of 1D analog signals (either as special
            neo-style signal objects: neo.AnalogSignal, DataSignal) or as numpy 
            arrays, or a 2D numpy array with one signal per column.
    
        When a collection of signals, all elements must have the same Python type
        (i.e. mixing of neo.AnalogSignal and DataSignal is NOT allowed).
    
        Furthermore, the shapes and domains of the signals must be identical.
    
        These signals should contain events (i.e., synaptic events) aligned on
        their rising phase (i.e. on the point of the fastest rise) or or their 
        onset.
    
    Returns:
    =======
    A tuple (mean_data, flucts_var, scaled_means, flucts) were:
        • `mean_data` (1D numpy array) is the averaged event waveform
    
        • `flucts_var` (1D numpy array) is the variance of differences between 
            each signal in `data` and its corresponding peak-scaled mean
    
        • `scaled_means` (2D numpy array) contains the peak-scaled average
            waveforms for each signal in `data`, as column vectors
    
        • `flucts` (2D numpy array) contains the difference between each signal
            in `data` and its corresponding peak-scaled average waveforms in 
            `scaled_means`, as column vectors
    """
    if isinstance(data, np.ndarray):
        if data.ndim == 2:
            if data.shape[1] <= 1:
                raise ValueError(f"data must contain at least two signals; got {data.shape[1]} instead")
            
        else:
            raise ValueError(f"data array must have two dimensions")
            
    elif isinstance(data, (tuple, list)):
        if len(data) <= 1:
            raise ValueError(f"data must contain at least two signals; got {len(data)} instead")
        
        if not all(isinstance(v, (neo.AnalogSignal, DataSignal, np.ndarray)) for v in data):
            raise TypeError(f"The collection must contain only analog signal objects")
        
        types = set(type(v) for v in data)
        if len(types) > 1:
            raise TypeError(f"All signals in a collection must have the same type")
        
        if not all(v.shape == data[0].shape for v in data):
            raise ValueError(f"All signals must have the same shape")
        
        if all(isinstance(v, neo.core.baseneo.BaseNeo) for v in data):
            if not all(np.all(data[0].times == v.times) for v in data):
                raise ValueError(f"All signals must have the same domain")
            
            data = np.concatenate([v.magnitude for v in data], axis=1)
            
        else:
            if not all(dt.is_vector(v) for v in data):
                raise ValueError(f"All elements in the data collection must be vectors")
            data = np.concatenate(data, axis=1)
            
    else:
        raise TypeError(f"Expecting a 2D array with column-wise signals or a collection (tuple, list) of neo signals or numpy vectors")
            
    
    mean_data = np.nanmean(data, axis=1)
    
    scale_res = [crvf.scale_fit_wave(data[:,k], mean_data) for k in range(data.shape[1])]
    scaled_means = np.concatenate([mean_data[:,np.newaxis] * float(s.x[0]) for s in scale_res], axis=1)
    flucts = np.concatenate([(data[:,k]-scaled_means[:,k])[:, np.newaxis] for k in range(data.shape[1])], axis=1)
    # print(f"{len(fluct_waves)} fluct_waves")
    # all_fluct = np.concatenate(fluct_waves, axis=1)
    flucts_var = np.var(flucts, axis=1)
    
    return mean_data, flucts_var, scaled_means, flucts
    
    
# def nsfa(data, /, start:int=0, stop:typing.Optional[int]=None, i=0, N=1, b=0, **kwargs):
def nsfa(xdata:np.ndarray, ydata:np.ndarray, /, i=0, N=1, b=0, **kwargs):
    """Non-stationary fluctuation analysis.
    
    The function estimates the number of channels and their unitary currents 
    likely to have contributed to the events. When Vm and Erev are given (see 
    below) the function also outputs the calculate unitary slope conductance.
    
    Uses the average event waveform and the variance (at each data point) of the 
    differences between each event and its peak-scaled waveform. These can be 
    generated from a collection of events or a 2D numpy array using the function
    prep_for_nsfa() defined in this module.
    
    Typically, nsfa is run on a subset of the waveform data, correspnding to the
    decay phase of the events. This can be achieved by passing a subarray of the 
    xdata and ydata.
    
    
    
    For details, theoretical background and implementations see:
    Robinson H.P.C., Sahara Y., Kawai N. (1991) Biophys. J., 59:295-304
    Traynelis, S.F., Silver, R. A., Cull-Candy S.G. (1993) Neuron, 11:279-289
    Benke, T.A., et al, (1998) Nature 393:793-797
    Benke T.A., et al, (2001) J. Physiol. 537.2:407-420 
    
    Parameters:
    ===========
    xdata: The averaged event waveform 
    ydata: The variance of event fluctuations (differences between the average
            event waveform and the peak-scaled average waveform)
    
        NOTE: xdata and ydata should be generated with prep_for_nsfa() function 
        in this module
    
    i, N, b: numeric scalars, the initial value of the parameters for nsfa fit
            (unitary current, number of channels, background variance)
    
    Var-keyword parameters (**kwargs):
    ==================================
    Vm: float scalar, the membrane voltage (in mV) where the events were measured;
        optional, default is None.
    
        When given, the unitary conductance will be calculated as:
    
            γ = i/(Vm-Erev)         if Erev is also given
    
        or 
    
            γ = i/Vm                otherwise (assuming Erev == 0)
    
    Erev: float scalar, the reversal potential (in mV); optional default is None.
        
        When given, and Vm is also given, it is used to calculate the unitary 
        channel conductance using the estimated unitary current (see above)
    
    The following are passed directly to curvefitting.fit_nsfa (and onwards to the 
    scipy.optimise.least_squares() function, see the Scipy manual).
    
    The ones you are most likely to want to change are:
    
    • bounds: a tuple (lo, up) of scalars or vectors each with three elements
    
    Returns:
    =======
    A tuple with fitted curve and a collections.OrderedDict.
    
    The fitted curve is a realization of the parabola describing the variance
    of the current as function of the mean current, generated using the fitted 
    parameters values (see below).
    
    The OrderedDict contains the following key ↦ value mapping:
    • Fit ↦ the result of nonlinear least squares fit of the parabolic function
    
        y = x * i - x²/N + b
    
        Where 
        ∘ y = fitted variance of signal deviations from peak-scaled sample average
        ∘ x = sample average
        ∘ i = unitary (single-channel) current
        ∘ N = number of channels
        ∘ b = background variance
    
    • Coefficients ↦ a list of the fitted parameter values i, N and b, in THIS 
        order
    
    • Rsq ↦ a scalar, the R² correlation coefficient between `ydata` and the
        fitted curve, given `xdata`.
    
    • UnitaryCurrent ↦ a scalar python Quantity (units: pA)
    
    • UnitaryConductance ↦ a scalar python Quantity (units: pS) if Vm was given, or None, otherwise
    
    • N ↦ an int, the estimated number of receptors (channels)
    
    NOTE: `x` and `i` represent membrane current in pA
    
    If the holding membrane voltage (Vₘ) is known one can calculate the unitary
    conductance γ of the channels using the estimated unitary current as:
    
        γ = i/(Vₘ-Eᵣₑᵥ)
    
    where Eᵣₑᵥ is the reversal potential.
    
    Using the Python quantities package allows a quick calculation of γ in pS:
    
    import quantities as pq
    
    Vₘ = -70 * pq.mV
    
    γ = (i * pq.pA/Vₘ).rescale(pq.pS)
        
    """
    
    Vm = kwargs.pop("Vm", None)
    
    Erev = kwargs.pop("Erev", None)
    
    
    kwargs["x"] = xdata
    
    
    nsfa_fit = crvf.fit_nsfa(ydata, [i, N, b], **kwargs)
    
    i, N, b = nsfa_fit[1]["Coefficients"]
    
    i *= pq.pA
    
    b *= pq.pA**2
    
    N = math.ceil(N)
    
    # print(f"Vm = {Vm}")
    
    if isinstance(Vm, numbers.Number):
        Vm *= pq.mV
        
    elif isinstance(Vm, pq.Quantity):
        uname = scq.name_from_unit(Vm)
        if uname != "Potential":
            raise TypeError("Vm expected to be a Potential; got {uname} instead")
        Vm  = Vm.rescale(pq.mV)
        
    elif Vm is not None:
        raise TypeError(f"Vm expected to be a scalar float or quantity")
    
    if isinstance(Erev, numbers.Number):
        Erev *= pq.mV
        
    elif isinstance(Erev, pq.Quantity):
        uname = scq.name_from_unit(Erev)
        if uname != "Potential":
            raise TypeError("Erev expected to be a Potential; got {uname} instead")
        Erev  = Erev.rescale(pq.mV)
        
    elif Erev is not None:
        raise TypeError(f"Erev expected to be a scalar float or quantity")
    
    else:
        Erev = 0*pq.mV # assume 0 reversal potential
    
    if Vm is not None:
        gamma = (i/(Vm-Erev)).rescale(pq.pS)
        
    else:
        gamma = np.nan*pq.pS
        
    nsfa_fit[1]["UnitaryCurrent"] = i
    nsfa_fit[1]["UnitaryConductance"] = gamma
    nsfa_fit[1]["N"] = N
    nsfa_fit[1]["b"] = b
    
    
    return nsfa_fit


def get_nsfa_var(x, params):
    """
    Calculate nsfa variance from membrane currents in `x` using nsfa parabola.
    
    Useful to plot a fitted nsfa curve (current variance function of current
    value. 
    
    e.g.
    
    x = np.linspace(-20, 0, 100)
    
    i = -2
    N = 11
    b =  6
    
    y = get_nsfa_var(x, [i, N, b])
    
    plt.plot(x,y)
    
    Assuming `res` is a nsfa fit result returned by the nsfa() function:
    
    y1 = get_nsfa_var(x, res[1]["Coefficients"])
    
    assert np.all(y1==y) # → True
    
    Parameters:
    ==========
    x: 1D numpy array with membrane currents
    params: array-like with three elements (i, N, b) - see documentation for 
            the nsfa function in this module
    """
    
    from core import models
    
    return models.nsfa(x, params)

    
    
    
    
    
    
    
