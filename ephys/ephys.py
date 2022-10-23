# -*- coding: utf-8 -*-
""" Functionality for electrophysiology data.

NOTATIONS USED BELOW:

"cursor": signalviewer.SignalCursor object

"cursor time point", "cursor time coordinate", "cursor domain coordinate": 
the value of a cursor's 'x' attribute (floating point scalar). This is the 
undimensioned value of the signal's domain at the cursor position.

The module provides a set of utility functions to operate primarily on objects
in NeuralEnsemble's neo package (http://neuralensemble.org/), 
documented here: https://neo.readthedocs.io/en/stable/

Some of these function also apply to datatypes.DataSignal in Scipyen package.

NOTE 2020-10-07 09:42:28
# Code split and redistributed across ephys.ephys, core.neoutils and core.triggerprotocols

The following functions are specific to this module:

I. Cursor- and epoch-based functions
===================================================

These functions measure a signal parameter on closed intervals that are defined
using, respectively, signalviewer.SignalCursor objects or a neo.Epoch.

The type of SignalCursor objects must be:

SignalCursor.SignalCursorTypes.vertical, 
or 
SignalCursor.SignalCursorTypes.horizontal.

The difference between cursor- and epoch-based functions consist in the way the 
functions calculate the signal values at the interval boundaries, and in the
number of intervals that a single function can process.

1 Cursor-based functions: named with the prefix "cursor_" or "cursors_".

The function uses the 'x' and 'xwindow' attributes of a vertical or crosshar 
SignalCursor. These are floating point scalars and are converted internally to
python Quantity scalars with the units of the signal domain.

'x' is the horizontal coordinate of the cursor.
'xwindow' is a duration of a horizontal window (or interval) centered on 'x'

1.a "cursor_*" functions use a single cursor:
    * the signal interval is defined by the cursor's horizontal window 
        (the 'xwindow' attribute).
     
    * the signal values at the interval boundaries, if used, are the actual 
        signal sample values at the interval's boundary time points 
        (the interval is closed, i.e. it contains its boundaries)
        
    List of functions based on a single cursor:
    
    cursor_value: the signal sample value at the time point of the cursor 
        (i.e., at the cursor's 'x' attribute) regardless of the size of the
        cursor's 'xwindow'
        
    cursor_min, cursor_max: returns the signal minimum (maximum) across the 
                cursor's horizontal window (or cursor_value if xwindow is zero)
                
    cursor_maxmin: return a tuple of signal max and min in the cursor's window
    
    cursor_average: average of signal samples across the cursor's window.
        NOTE: When cursor's xwindow is zero, this calls cursor_value()
    
    cursor_argmin, cursor_argmax: the index of the signal minimum (maximum) 
                in the cursor window
        
    cursor_argmaxmin: tuple of indices for signal max and min in the cursor's 
            window
            
    
    If the cursor's horizontal window is zero, the above functions return
    the signal sample value at the cursor's coordinate or index 0
    
    
1.b "cursors_*" functions use two cursors to define a signal interval:
    * the signal interval is bounded by the cursor's 'x' coordinates, and is
        closed (i.e. the boundaries are part of the interval):
        
        left boundary: left_cursor.x
        
        right_boundary: right_cursor.x
        
    * the signal values at the interval boundaries, if used, are the averages
        of signal samples across the cursor's horizontal window, if not zero, at
        the respective boundary.
        
        
    List of functions based on two cursors:
    
    cursors_difference: the signed difference between the signal values at two cursors.
        NOTE: for each cursor, the signal value "at the cursor" is determined by 
        calling cursor_average(). This means that, if the cursor's xwindow is 
        zero, the value "at cursor" is the actual sample value at the cursor's
        time coordinate.
        
    cursors_chord_slope
    
All cursor-based functions return a python Quantity array of shape(m,1) with
    m = number of channels.
        
2. Epoch-based functions: named with the prefix "epoch_".

These functions use a single neo.Epoch object to define signal intervals. 

An interval is described by time and duration, contained in the 'times' and 
'durations' attributes of the neo.Epoch object. Since both these attributes
are numeric arrays with the same length, it follows that a neo.Epoch can define 
more than one interval. All intervals are considered closed (i.e. they contain
their boundaries).

    For interval 'k' where 0 <= k < len(epoch) the boundaries are:
        left boundary: times[k]
        right boundary: times[k] + durations[k]
        
The 'times' and 'durations' are python Quantities in time units ("s" by default)
as are the units of the signal domain.

Signal values at the interval boundaries, if used, are the sample values at the
the boundary time points (unlike "cursors_*" functions).

The "epoch_*" functions return a python Quantity array with the shape (m,n) with

    m = number of intervals in the epoch
    n = number of channels in the signal
    
List of neo.Epoch-based functions:
    epoch_average
    

As a rule of thumb:

* when several scalar measures, each derived from a signal interval, are needed,
use neo.Epoch to define the signal intervals where the measures are calculated.

* when a single measure derived from two signal locations is needed, use 
signalviewer.SignalCursors to define the locations.

II. Statistics
===========================================
aggregate_signals: calculates several statistical moments across several
                    single-channel signals with identical shapes; each moment 
                    is returned as a
                    new signal with the same shape as the arguments, contained 
                    in a dictionary
    
average_blocks

average_blocks_by_segments

average_segments

average_segments_in_block

average_signals

III. Electrophysiology signal processing
========================================
batch_normalise_signals
batch_remove_offset
convolve
correlate
diff
ediff1d
forward_difference
gradient
peak_normalise_signal
remove_signal_offset
parse_step_waveform_signal
resample_pchip
resample_poly
root_mean_square
sampling_rate_or_period
signal_to_noise

IV. Synthesis of artificial signals and waveforms
=================================================
generate_ripple_trace
generate_spike_trace
waveform_signal

V. I/O-related
=================
parse_acquisition_metadata

"""
#### BEGIN core python modules
import traceback
import datetime
import collections
import numbers
import inspect
import itertools
import functools
import warnings
import typing, types
from enum import Enum, IntEnum
#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import quantities as pq
import neo
import matplotlib as mpl
import pyqtgraph as pg
#### END 3rd party modules

#### BEGIN pict.core modules
from core.prog import safeWrapper
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
from core.datazone import DataZone
from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType, )
from core.triggerprotocols import TriggerProtocol

from core import datatypes as dt
from core import workspacefunctions
from core import signalprocessing as sigp
from core import utilities
from core import neoutils
from core.utilities import normalized_index
from core.neoutils import get_index_of_named_signal
from core.quantities import (units_convertible, check_time_units)


#from .patchneo import neo


#### END pict.core modules

class SignalCursor:
    # dummy
    pass

if __debug__:
    global __debug_count__

    __debug_count__ = 0
    
def isiFrequency(data:typing.Union[typing.Sequence, collections.abc.Iterable], start:int = 0, span:int=1, isISI:bool=False):
    """Calculates the reciprocal of an inter-event interval.
    
    This can be the time interval between any two events with indices "start" &
    "start" + "span".
    
    Parameters:
    ==========
    data: sequence of time stamps OR time intervals (python Quantity values with time units)
        The interpretation is dictated by the 'isISI' parameter described below
        
    start: int, the index of the first time stamp to take into consideration
        optional, default is 0 (i.e. the first time stamps in the 'data' parameter)
    
    span: int, the number of inter-event intervals (or "span");
        optional, default is 1 i.e., one interval
          
    isISI:bool, flag to interpret the data as a sequence of time stamps (when False)
        or time intervals (when True).
        
        Optional, default is False (i.e. data is taken as a sequence of time stamps)
        
    Returns:
    ========
    The frequency (reciprocal of the interval's duration) as a scalar Quantity 
    in pq.Hz.
    
    If the data is empty or contains only one element, returns 0 Hz
    
    Example:
    ===========
    # Given a neo.SpikeTrain 'AP_train':
    
    In: AP_train.times
    
    Out: array([20.0971, 20.1261, 20.1582, ..., 20.2213, 20.261 , 20.3052]) * s
    
    # Find out the instantaneous frequency as the reciprocal of the interval 
    # between the first and the third action potential:
    
    In: isiFrequency(AP_train.times, 0, 2)
    Out: array(16.3441) * Hz
    
    # Suppose the time inter-AP intervals are collected as follows:
    
    In: Inter_AP_intervals = np.diff(AP_train.times)
    
    In: Inter_AP_intervals
    Out: array([0.029 , 0.0322, 0.0327, 0.0304, 0.0396, 0.0442]) * s
    
    # To calculate the instantaneous frequency for the first two intervals:
    
    In: isifrequency(Inter_AP_intervals, 0, 2, True) # NOTE the third parameter
    Out: array(16.3441) * Hz
    
    """
    if len(data) <= 1:
        return 0*pq.Hz
    
    if start < 0:
        raise ValueError(f"'start' must be >= 0; got {start} instead")
    
    if start >= len(data):
        raise ValueError(f"'start' must be < {len(data)}; got {start} instead")
    
    if span < 1:
        raise ValueError(f"'span' expected to be at least 1; got {span} instead")
    
    if start + span >= len(data):
        raise ValueError(f"'span' cannot be larger than {len(data)-start}; got {span} instead")
    
    if isISI:
        return (1/np.sum(data[start:(start+span)])).rescale(pq.Hz)
    
    else:
        stamps = data[start:(start+span+1)]
        return (1/(stamps[-1]-stamps[start])).rescale(pq.Hz)
    

def correlate(in1, in2, **kwargs):
    """Calls scipy.signal.correlate(in1, in2, **kwargs).
    
    Correlation mode is by default set to "same", but can be overridden.
    
    Parameters
    
    ----------
    
    in1 : neo.AnalogSignal, neo.IrregularlySampledSignal, datatypes.DataSignal, or np.ndarray.
    
        Must be a 1D signal i.e. with shape (N,) or (N,1) where N is the number 
        of samples in "in1"
    
        The signal for which the correlation with "in2" is to be calculated. 
        
        Typically this is the longer of the signals to correlate.
        
    in2 : neo.AnalogSignal, neo.IrregularlySampledSignal, datatypes.DataSignal, or np.ndarray
    
        Must be a 1D signal, i.e. with shape (M,) or (M,1) where M is the number 
        of samples in "in2"
        
        The signal that "in1" is correlated with (typically, shorter than "in1")
        
    Var-keyword parameters
    
    -----------------------
    
    method : str {"auto", "direct", "fft"}, optional; default is "auto"
        Passed to scipy.signal.correlate
        
    name : str
        The name attribute of the result
        
    units : None or a Python Quantity or UnitQuantity. Default is None.
    
        These is mandatory when "a" is a numpy array
    
        The units of the returned signal; when None, the units of the returned 
        signal are pq.dimensionless (where "pq" is an alias for Python quantities
        module)
    
    Returns
    
    -------
    
    ret : object of the same type as "in1"
        Contains the result of correlating "in1" with "in2".
        
        When "in1" is a neo.AnalogSignal, neo.IrregularlySampledSignal, or datatypes.DataSignal,
        ret will have "times" attribute copied from "in1" and with "units" attribute
        set to dimensionless, unless specified explicitly by "units" var-keyword parameter.
        
        
    NOTE
    
    ----
    
    The function correlates the magnitudes of the signals and does not take into
    account their units, or their definition domains (i.e. "times" attribute).
    
    See also:
    --------
    scipy.signal.correlate
    
    """
    
    from scipy.signal import correlate
    
    from . import datatypes as dt
    
    name = kwargs.pop("name", "")
    
    units = kwargs.pop("units", pq.dimensionless)
    
    mode = kwargs.pop("mode", "same") # let mdoe be "same" by default but allow it to be overridden
    
    if in1.ndim > 1 and in1.shape[1] > 1:
        raise TypeError("in1 expected to be a 1D signal")
    
    if in2.ndim > 1 and in2.shape[1] > 1:
        raise TypeError("in2 expected to be a 1D signal")
    
    if isinstance(in1, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal)):
        in1_ = in1.magnitude.flatten()
        
    else:
        in1_ = in1.flatten()

    if isinstance(in2, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal)):
        in2_ = in2.magnitude.flatten()
        
    else:
        in2_ = in2.flatten()
        
    in2_ = np.flipud(in2_)
        
    corr = correlate(in1_, in2_, mode=mode, **kwargs)
    
    if isinstance(in1, (neo.AnalogSignal, DataSignal)):
        ret = neo.AnalogSignal(corr, t_start = in1.t_start,
                                units = units, 
                                sampling_period = in1.sampling_period,
                                name = name)
    
        if isinstance(in2, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal)):
            ret.description = "Correlation of %s with %s" % (in1.name, in2.name)
            
        else:
            ret.description = "Correlation of %s with an array" % in1.name
            
        return ret
    
    elif isinstance(in1, neo.IrregularlySampledSignal):
        ret = neo.IrregularlySampledSignal(corr, 
                                            units=units,
                                            times = in1.times,
                                            name = name)
    
        if isinstance(in2, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal)):
            ret.description = "Correlation of %s with %s" % (in1.name, in2.name)
            
        else:
            ret.description = "Correlation of %s with an array" % in1.name
            
        return ret

    else:
        return corr
    
@safeWrapper
def cursors2epoch(*args, **kwargs):
    """Constructs a neo.Epoch from a sequence of SignalCursor objects.
    
    Each cursor contributes an interval in the Epoch, corresponding to the 
    cursor's horizontal (x) window. In other words, the interval's (start) time
    equals the cursor's x coordinate - ½ cursor's x window, and the duration of
    the interval equals the cursor's x window.
    
    NOTE: For DataSignals, the result is a DataZone.
    
    SignalCursor objects are defined in the signalviewer module; this function
    expects vertical and crosshair cursors (i.e., with cursorType one of
    SignalCursor.SignalCursorTypes.vertical, 
    SignalCursor.SignalCursorTypes.horizontal). 
    
    SignalCursors can also be represented by tuples of cursor  "parameters" 
    (see below), although tuples and cursor objects cannot be mixed.
    
    Variadic parameters:
    --------------------
    *args: comma-separated list of EITHER:
    
        • SignalCursor objects - all of either 'vertical' or 'crosshair' type.
        
        • SignalCursor tuples (2, 3 or 5 elements) of cursor parameters:
        
            ∘ 2-tuples are interpreted as (time, window) pairs of coordinates
                for a notional vertical cursor
            
            ∘ 3-tuples are interpreted as (time, window, label) triplets of 
                parameters for a notional vertical cursor
            
            ∘ 5-tuples are interpreted as (x, xwindow, y, ywindow, label) tuples
                 of parameters for a notional crosshair cursor; only the x, 
                xwindow and label elements are used.
            
        NOTE: the following are NOT allowed:
            □ Mixing SignalCursor objects with parameter tuples.
            □ Mixing parameter 2- 3- or 5-tuples is NOT allowed.
        
    Var-keyword parameters:
    ----------------------
    
    units: python Quantity or None (default)
        When not specified (i.e. units = None) the function assumes units of
        quantities.s and will return a neo.Epoch object(*). 

        When the specified units are NOT temporal, the result is a DataZone(*).
    
        (*) assuming `intervals` is False
        
    name: str, default is "Epoch" or "Zone" (depending on `units`).
         When `intervals` is True, this parameter is not used (see below).
    
    sort: bool, default is True
        When True, the cursors, or their specifications, in *args are sorted by 
        their x coordinate.
        
    intervals: bool, default is False.
    
        When True, the function returns triplets of (start, stop, label) quantities.
        
        Otherwise returns a neo.Epoch if `units` is quantities.s, or DataZone.
        
        
    Returns:
    -------
    
    When intervals is False (default), returns a neo.Epoch (or DataZone) with 
        intervals generated from the cursors' x coordinates and horizontal 
        windows (`xwindow` properties):
        
            times = cursor.x - cursor.xwindow/2
            durations = cursor.xwindow
            
            By design, the epoch's units are time units (pq.s by default)
            
    When intervals is True, returns a list of triplets:
            (start, stop, label)
            
            If units are provided, start and stop are python Quantity scalars,
            otherwise they are floating point scalars.
    
    ATTENTION: The numeric parameters are treated as cursor parameters; do NOT
    calculate new time 'start' from these values! This function takes care of 
    that!!!
            
    Examples:
    ========
    
    Given "cursors" a list of vertical SignalCursors, and "params" the 
    corresponding list of cursor parameters:
    
    >>> params = [c.parameters for c in cursors]
    
    >>> params
        [(0.20573370205046024, 0.001, 'v2'),
         (0.1773754848365214,  0.001, 'v1'),
         (0.16775228528220001, 0.001, 'v0')]
         
    The following examples are valid call syntax:

    >>> epoch = cursors2epoch(cursors)
    >>> epoch1 = cursors2epoch(*cursors)
    >>> epoch2 = ephys.cursors2epoch(params)
    >>> epoch3 = ephys.cursors2epoch(*params)
    
    >>> epoch == epoch1
    array([ True,  True,  True])

    >>> epoch == epoch2
    array([ True,  True,  True])
    
    >>> epoch2 == epoch3
    array([ True,  True,  True])
    
    >>> epoch4 = ephys.cursors2epoch(*params, units=pq.um)
    >>> epoch4 == epoch3
    array([False, False, False]) #  because units are different
    
    >>> interval = cursors2epoch(cursors, intervals=True)
    >>> interval1 = cursors2epoch(*cursors, intervals=True)
    
    >>> interval == interval1
    True
    
    >>> interval2 = ephys.cursors2epoch(params, intervals=True)
    >>> interval3 = ephys.cursors2epoch(*params, intervals=True)
    
    >>> interval2 == interval3
    True
    
    >> interval == interval2
    True
    """
    from gui.signalviewer import SignalCursor as SignalCursor

    intervals = kwargs.get("intervals", False)
    
    units = kwargs.get("units", pq.s)
    
    if not isinstance(units, pq.UnitQuantity):
        units = units.units
        
    elif not isinstance(units, pq.Quantity) or units.size > 1:
        raise TypeError("Units expected to be a python Quantity; got %s instead" % type(units).__name__)
        
    name = kwargs.get("name", "Epoch")
    
    if not isinstance(name, str):
        raise TypeError("name expected to be a string")
    
    if len(name.strip())==0:
        raise ValueError("name must not be empty")
    
    sort = kwargs.get("sort", True)
    
    if not isinstance(sort, bool):
        raise TypeError("sort must be a boolean")
    
    def __parse_cursors_tuples__(*values):
        # check for dimensionality consistency
        #print(type(values))
        #print(len(values))
        if len(values) == 1:#  allow for a sequence to be given as first argument
            values = values[0]
            
        #print("given values", values)
        values_ = list(values)
        
        for k,c in enumerate(values_):
            if all([isinstance(v, pq.Quantity) for v in c[0:2]]):
                if c[0].units != c[1].units:
                    if not units_convertible(c[0], c[1]):
                        raise TypeError("Quantities must have compatible dimensionalities")
                    
                values = values_ # convert back
                
            elif all([isinstance(v, numbers.Number) for v in c[0:2]]):
                if units is not None:
                    c_ = [v*units for v in c[0:2]]
                    
                    if len(c) > 2:
                        c_ += list(c[2:])
                        
                    values_[k] = tuple(c_)
                    
                values = tuple(values_)
        
        #print("values:", values)
        
        if intervals:
            return [(v[0]-v[1]/2., v[0]+v[1]/2., "%d"%k) if len(v) == 2 else (v[0]-v[1]/2., v[0]+v[1]/2., v[2]) if len(v) == 3 else (v[0]-v[1]/2., v[0]+v[1]/2., v[4]) for k,v in enumerate(values)]
            
        else:
            return [(v[0]-v[1]/2., v[1],         "%d"%k) if len(v) == 2 else (v[0]-v[1]/2., v[1],         v[2]) if len(v) == 3 else (v[0]-v[1]/2., v[1],         v[4]) for k,v in enumerate(values)]
        
    if len(args) == 0:
        raise ValueError("Expecting at least one argument")
    
    if len(args) == 1:
        if isinstance(args[0], (tuple, list)):
            if all ([isinstance(c, SignalCursor) for c in args[0]]):
                if all([c.cursorTypeName in ("vertical", "crosshair")  for c in args[0]]):
                    t_d_i = __parse_cursors_tuples__(*[c.parameters for c in args[0]])                    
                else:
                    raise TypeError("Expecting only vertical or crosshair cursors")
                
            elif all([isinstance(c, (tuple, list)) for c in args[0]]):
                if all([len(c) in (2,3,5) for c in args[0]]):
                    t_d_i = __parse_cursors_tuples__(args[0])
                    
                else:
                    raise TypeError("All cursor parameter tuples must have two or three elements")
                         
        elif isinstance(args[0], SignalCursor):
            if args[0].cursorType is SignalCursor.SignalCursorTypes.horizontal:
                raise TypeError("Expecting a vertical or crosshair cursor")
            
            t_d_i = __parse_cursors_tuples__([args[0].parameters])
            
        elif len(args[0] == 3):
            t_d_i = __parse_cursors_tuples__([args[0]])
            
        else:
            raise TypeError("Unexpected argument type %s" % type(args[0]).__name__)
        
    else:
        if all([isinstance(c, SignalCursor) for c in args]):
            if all ([c.cursorTypeName in ("vertical", "crosshair") for c in args]):
                t_d_i = __parse_cursors_tuples__([c.parameters for c in args])
                
            else:
                raise TypeError("Expecting only vertical or crosshair cursors")
            
        elif all([isinstance(c, (tuple, list)) and len(c) in (2,3,5) for c in args]):
            t_d_i = __parse_cursors_tuples__(args)
            
        else:
            raise TypeError("Unexpected argument types")
        
    if sort:
        t_d_i = sorted(t_d_i, key=lambda x: x[0])

    if intervals:
        return t_d_i
    
    else:
        # transpose t_d_i and unpack:
        # print("cursors2epoch", t_d_i)
        t, d, i = [v for v in zip(*t_d_i)]
        
        if isinstance(t[0], pq.Quantity):
            units = t[0].units
            
        if not check_time_units(units):
            return DataZone(times=t, durations=d, labels=i, units=units, name=name)
        
        return neo.Epoch(times=t, durations=d, labels=i, units=units, name=name)
    
def cursors2intervals(*args, **kwargs):
    """Calls cursors2epochs with intervals set to True
    
    Additional var-keyword parameters:
    --------------------------------
    unwrap: bool default True
        When False, calling the function with a single cursor (or cursor parameter
            tuple) will return a single interval tuple (t0, t1, label) wrapped in
            a list.
            
        When True, the function returns the single interval tuple directly
    """
    kwargs.pop("intervals", True) # avoid double parameter specification
    
    unwrap = kwargs.pop("unwrap", True)
    
    ret = cursors2epoch(*args, **kwargs, intervals=True)
    
    if unwrap and len(ret) == 1:
        return ret[0]
    
    

@safeWrapper
def signal2epoch(sig, name=None, labels=None):
    """Constructs a neo.Epochs from the times and durations in a neo.IrregularlySampledSignal
    
    Parameters:
    ----------
    
    sig: neo.IrregularlySampledSignal where the signal's units are time units
        (typically, this signal contains an array of durations, and its elements
        will be used to supply the durations values for the Epoch)
        
    name: str or None (default)
        The name of the Epoch
        
    labels: numpy array with dtype "S" (str), a str, or None (default)
        Array with labels for each interval in the epoch.
        
        When an array it must have the same length as sig.
    
    """
    from . import datatypes as dt
    
    if not isinstance(sig, neo.IrregularlySampledSignal):
        raise TypeError("Expecting a neo.IrregularlySampledSignal; got %s instead" % type(sig).__name__)
    
    if not units_convertible(sig.units, sig.times.units):
        raise TypeError("Signal was expected to have time units; it has %s instead" % sig.units)
    
    if isinstance(labels, str) and len(labels.strip()):
        labels = np.array([label] * sig.times.size)
        
    elif isinstance(labels, np.ndarray):
        if not dt.is_string(labels):
            raise TypeError("'labels' array has wrong dtype: %s" % labels.dtype)
        
        if labels.shape != sig.times.shape:
            raise TypeError("'labels' array has wrong shape (%s); shloud have %s" % (labels.shape, sig.times.shape))
        
    elif labels is not None:
        raise TypeError("'labels' expected to be a str, numpy array of string dtype, or None; got %s instead" % type(labels).__name__)
    
    if not isinstance(name, (str, type(None))):
        raise TypeError("'name' expected to be None or a string; got %s instead" % type(name).__name__)
    
    if isinstance(name, str) and len(name) == 0:
        name = sig.name # this may be None

    ret = neo.Epoch(times = sig.times,
                    durations = sig.magnitude * sig.units,
                    name = name,
                    labels = labels)
    
    return ret

@safeWrapper
def epoch_reduce(func:types.FunctionType, signal: typing.Union[neo.AnalogSignal, DataSignal], epoch: typing.Union[neo.Epoch, tuple], channel: typing.Optional[int] = None):
    """
    The maximum value of a signal across an Epoch or a (t0, duration) interval.
    
    CAUTION: For an epoch with more than one interval, this returns the maximum
    signal value across ALL the intervals in the Epoch.
    
    If this is not what you want, then call this function passing the desired
    interval coordinates (t0, duration) of the Epoch.
    
    Example:
    epoch_max(signal, (epoch.times[0], epoch.durations[0]))
    
    Parameters:
    ----------
    signal: neo.AnalogSignal, DataSignal
    epoch: tuple (t0, duration) or neo.Epoch
    channel: int or None (default)
        For multi-channel signal, specified which channel is used:
        0 <= channel < signal.shape[1]
    
    """
    
    if isinstance(epoch, tuple) and len(epoch) == 2:
        t0, duration = epoch
        if not isinstance(t0, pq.Quantity):
            t0 *= signal.times.units
            
        else:
            if not units_convertible(t0, signal.times.units):
                raise ValueError(f"epoch start units ({t0.units}) are incompatible with the signal's domain ({signal.times.units})")
            
        if not isinstance(duration, pq.Quantity):
            duration *= signal.times.units
        else:
            if not units_convertible(duration, signal.times.units):
                raise ValueError(f"epoch duration units ({duration.units}) are incompatible with the signal's domain ({signal.times.units})")

    elif isinstance(epoch, neo.Epoch):
        t0 = epochs.times.min()
        duration = np.sum(epoch.durations)
        
    else:
        raise TypeError(f"epoch expected to be a tuple (t0, duration) or a neo.Epoch; got {epoch} instead")
    
    t1 = t0 + duration
    
    if t0 == t1:
        ret = signal[signal.time_index(t0),:]
        
    else:
        ret = signal.time_slice(t0,t1).max(axis=0).flatten()
    
    if isinstance(channel, int):
        return ret[channel].flatten()
    
    return ret

def cursor_reduce(func:types.FunctionType, signal: typing.Union[neo.AnalogSignal, DataSignal], cursor: typing.Union[SignalCursor, tuple], channel: typing.Optional[int] = None):
    """Reduced signal value (e.g. min, max, median etc) across a cursor's window.
    
    The reduced signal value is the value calculated by the `func` parameter
    from a signal region defined by the cursor.
    
    If the window is 0, the function returns the signal value at the cursor's 
    position in the signal domain.
    
    Parameters:
    ----------
    func:   types.FunctionType. A function which takes a numpy array and returns 
            a value(*).
            Such functions include those in the numpy package `np.min`, `np.max`,
            `np.mean`, `np.median`, `np.std`, `np.var`, (and their 'nan' versions),
            and functions defined in Scipyen's core.signalprocessing module (e.g.,
            `sem`, `nansem`, `nansize`, `data_range`, `is_positive_waveform`, 
            `waveform_amplitude`, `minmax`, etc.)
    
            NOTE: The core.signalprocessing module is already imported in a 
                    Scipyen session under the `sigp` alias.
    
            (*) This value can be a scalar, or a tuple of scalars (e.g. sigp.maxmin)
            
    signal: neo.AnalogSignal, DataSignal
    
    cursor: tuple (x, window) or SignalCursor of type vertical or crosshair
    
    channel: int or None (default)
        For multi-channel signal, specified which channel is used:
        0 <= channel < signal.shape[1]
    
    Returns:
    --------
    Python Quantity array of shape (signal.shape[1], ) with the reduced value
    calculated from the signal region in the interval defined by the cursor's 
    window, or the signal's sample value at the cursor's x coordinate if cursor 
    window is zero.
    
    NOTE: To get the signal extremes (and their sample indices) between two 
    cursors, just call max(), min(), argmax() argmin() on a signal time slice 
    obtained using the two cursor's x values.
    """
    from gui.signalviewer import SignalCursor as SignalCursor
    
    if not isinstance(func, types.FunctionType):
        raise TypeError(f"Expecting a function as first argument; got {type(func).__name__} instead")
    
    if isinstance(cursor, SignalCursor):
        t0 = (cursor.x - cursor.xwindow/2) * signal.times.units
        t1 = (cursor.x + cursor.xwindow/2) * signal.times.units
        
    elif isinstance(cursor, tuple) and len(cursor) == 2:
        t0, t1 = cursor
        
        if not isinstance(t0, pq.Quantity):
            t0 *= signal.times.units
            
        else:
            if not units_convertible(t0, signal.times.units):
                raise ValueError(f"t0 units ({t0.units}) are not compatible with the signal's time units {signal.times.units}")
    
        if not isinstance(t1, pq.Quantity):
            t1 *= signal.times.units
    
        else:
            if not units_convertible(t1, signal.times.units):
                raise ValueError(f"t1 units ({t1.units}) are not compatible with the signal's time units {signal.times.units}")
        
    else:
        raise TypeError(f"Incorrrect cursors specification; expecting a SignalCursor or a 2-tuple of scalars; got {cursors} instead")
    
    if t0 == t1:
        ret = signal[signal.time_index(t0),:]
        
    else:
        # ret = signal.time_slice(t0,t1).max(axis=0).flatten()
        ret = func(signal.time_slice(t0,t1), axis=0).flatten()
    
    if isinstance(channel, int):
        return ret[channel].flatten()
    
    return ret

@safeWrapper
def cursor_max(signal: typing.Union[neo.AnalogSignal, DataSignal], cursor: typing.Union[SignalCursor, tuple], channel: typing.Optional[int] = None):
    """The maximum value of the signal across the cursor's window.
    Calls cursor_reduce with np.max as `func` parameter.
    """
    return cursor_reduce(np.max, signal, cursor, channel)

@safeWrapper
def cursor_min(signal: typing.Union[neo.AnalogSignal, DataSignal], cursor: typing.Union[SignalCursor, tuple], channel: typing.Optional[int] = None):
    """The maximum value of the signal across the cursor's window.
    Calls cursor_reduce with np.min as `func` parameter.
    """
    return cursor_reduce(np.min, signal, cursor, channel)


@safeWrapper
def cursor_argmax(signal: typing.Union[neo.AnalogSignal, DataSignal], cursor: typing.Union[SignalCursor, tuple], channel: typing.Optional[int] = None):
    """The index of maximum value of the signal across the cursor's window.

    Parameters:
    ----------
    signal: neo.AnalogSignal, DataSignal
    cursor: tuple (x, window) or SignalCursor of type vertical or crosshair
    channel: int or None (default)
        For multi-channel signal, specified which channel is used:
        0 <= channel < signal.shape[1]
    
    Returns:
    --------
    Array with the index of the signal maximum, relative to the start of the 
    interval, with shape (signal.shape[1], ).
    
    When cursor's xwindow is zero, returns an array of shape (1,) containing 
    the sample index of the cursor's x coordinate relative to the beginning of
    the signal.
    """
    
    return cursor_reduce(np.argmax, signal, cursor, channel)
    
@safeWrapper
def cursor_argmin(signal: typing.Union[neo.AnalogSignal, DataSignal], cursor: typing.Union[tuple, SignalCursor], channel: typing.Optional[int] = None):
    """The index of minimum value of the signal across the cursor's window.

    Parameters:
    ----------
    signal: neo.AnalogSignal, DataSignal
    cursor: tuple (x, window) or SignalCursor of type vertical or crosshair
    channel: int or None (default)
        For multi-channel signal, specified which channel is used:
        0 <= channel < signal.shape[1]
    
    Returns:
    --------
    Array with the index of the signal minimum, relative to the start of the 
    interval, with shape (signal.shape[1], ).
    
    When cursor's xwindow is zero, returns an array of shape (1,) containing 
    the sample index of the cursor's x coordinate relative to the beginning of
    the signal.
    """
    
    return cursor_reduce(np.argmin, signal, cursor, channel)

@safeWrapper
def cursor_maxmin(signal: typing.Union[neo.AnalogSignal, DataSignal], cursor: typing.Union[tuple, SignalCursor], channel: typing.Optional[int] = None):
    """The maximum and minimum value of the signal across the cursor's window.

    Parameters:
    ----------
    signal: neo.AnalogSignal, DataSignal
    cursor: tuple (x, window) or SignalCursor of type vertical or crosshair
    channel: int or None (default)
        For multi-channel signal, specified which channel is used:
        0 <= channel < signal.shape[1]
    
    Returns:
    --------
    Tuple of two Python Quantity arrays each of shape (signal.shape[1], )
    respectively, with the signal maximum and minimum (respectively) in the 
    interval defined by the cursor's window.
    
    If cursor window is zero, returns a tuple with the signal's sample values 
    at the cursor's x coordinate (same value is replicated, so that the return
    object is still a two-element tuple).
    
    """
    
    return cursor_reduce(sigp.maxmin, signal, cursor, channel)

@safeWrapper
def cursor_minmax(signal, cursor, channel):
    return cursor_reduce(sigp.minmax, signal, cursor, channel)

@safeWrapper
def cursor_argmaxmin(signal: typing.Union[neo.AnalogSignal, DataSignal], cursor: typing.Union[tuple, SignalCursor], channel: typing.Optional[int] = None):
    """The indices of signal maximum and minimum across the cursor's window.
    """
    return cursor_reduce(sigp.argmaxmin, signal, cursor, channel)

@safeWrapper
def cursor_argminmax(signal, cursor, channel):
    return cursor_reduce(sigp.argminmax, signal, cursor, channel)

@safeWrapper
def cursor_average(signal: typing.Union[neo.AnalogSignal, DataSignal], cursor: typing.Union[tuple, SignalCursor], channel: typing.Optional[int]=None):
    """Average of signal samples across the window of a vertical cursor.
    Calls cursor_reduce with np.mean as `func` parameter
    
    Parameters:
    -----------
    
    signal: neo.AnalogSignal or datatypes.DataSignal
    
    cursor: tuple, or signalviewer.SignalCursor (vertical).
        When a tuple (t,w), it represents a notional vertical cursor with window
        "w" centered at time "t". "t" and "w" must be floats or python 
        Quantity objects with the same units as the signal's domain.
        
    channel: int or None (default). For multi-channel signals, it specifies the 
        signal channel to get the average value from.
        
        When channel is None, the function returns a python Quantity array
        (one value for each channel).
        
        When channel is an int, the function returns the average at the specifed
        channel (if it is valid)
        
    Returns:
    -------
    A python Quantity with the same units as the signal.
    
    """
    return cursor_reduce(np.mean, signal, cursor, channel)

cursor_mean = cursor_average

@safeWrapper
def cursor_value(signal:typing.Union[neo.AnalogSignal, DataSignal], cursor: typing.Union[float, SignalCursor, pq.Quantity, tuple], channel: typing.Optional[int] = None):
    """Value of signal at the vertical cursor's time coordinate.
    
    Signal sample values are NOT averaged across the cursor's window.
    
    Parameters:
    -----------
    signal: neo.AnalogSignal or datatypes.DataSignal
    
    cursor: float, python Quantity or vertical SignalCursor
    
            When float, it must be a valid value in the signal's domain 
                (signal domain ubnits are assumed)
                
            When a Quantity, its units must be convertible to the units of the
                signal's domain.
                
            When a SignalCursor, it must be a vertical or crosshair cursor.
            
    channel: int or None (default). Specifies which signal channel is the value
        retrieved from.
        
            When None (default), the function returns all channel values at 
                cursor. Otherwise, returns the value in the specified channel
                (channel must be a valid index >= 0 and < number of channels)
                
    Returns:
    --------
    
    python Quantity array with signal's, and shape (signal.shape[1], ) or (1,)
    when channel is specified.
    
    """
    from gui.signalviewer import SignalCursor as SignalCursor
    
    data_index = cursor_index(signal, cursor)
    
    ret = signal[data_index,:]
    
    if channel is None:
        return ret
    
    return ret[channel].flatten() # so that it can be indexed

@safeWrapper
def cursor_index(signal:typing.Union[neo.AnalogSignal, DataSignal], cursor: typing.Union[float, SignalCursor, pq.Quantity, tuple]):
    """Index of signal sample at the vertical cursor's time coordinate.
    
    Parameters:
    -----------
    signal: neo.AnalogSignal or datatypes.DataSignal
    
    cursor: float, python Quantity, vertical SignalCursor or cursor parameters
            tuple
    
            When float, it must be a valid value in the signal's domain 
                (signal domain ubnits are assumed)
                
            When a Quantity, its units must be convertible to the units of the
                signal's domain.
                
            When a SignalCursor, it must be a vertical or crosshair cursor.
            
                
    Returns:
    --------
    An int: index of the sample
    
    """
    from gui.signalviewer import SignalCursor as SignalCursor

    # NOTE: specifying a channel doesn't make sense here because all
    # channels in the signal sharethe domain and have the same number of
    # samples
    if isinstance(cursor, float):
        t = cursor * signal.time.units
        
    elif isinstance(cursor, SignalCursor):
        if cursor.cursorType not in (SignalCursor.SignalCursorTypes.vertical, SignalCursor.SignalCursorTypes.crosshair):
            raise TypeError("Expecting a vertical or crosshair cursor; got %s instead" % cursor.cursorType)
        
        t = cursor.x * signal.times.units
        
    elif isinstance(cursor, pq.Quantity):
        if not units_convertible(cursor, signal.times.units):
            raise TypeError("Expecting %s for cursor units; got %s instead" % (signal.times.units, cursor.units))
        
        t = cursor
        
    elif isinstance(cursor, (tuple, list)) and len(cursor) in (2,3) and all([isinstance(c, (numbers.Number, pq.Quantity)) for v in cursor[0:2] ]):
        # cursor parameter sequence
        t = cursor[0]
        
        if isinstance(t, numbers.Number):
            t *= signal.times.units
            
        else:
            if t.units != signal.times.units:
                if not units_convertible(t, signal.times):
                    raise TypeError("Incompatible units for cursor time")
            
            t = t.rescale(signal.times.units)
        
    else:
        raise TypeError("Cursor expected to be a float, python Quantity or SignalCursor; got %s instead" % type(cursor).__name__)
    
    data_index = signal.time_index(t)
    
    return data_index

@safeWrapper
def cursors_measure(func, data, *cursors, segment_index: int = None, analog: typing.Optional[typing.Union[int, str]] = None, irregular: typing.Optional[typing.Union[int, str]] = None, **kwargs):
    """
    data: a neo.AnalogSignal or datatypes.DataSignal
    """
    from gui.signalviewer import SignalCursor as SignalCursor

    
    def __signal_measure__(f, x, *cursors, **kwargs):
        return f(x, *cursors, **kwargs)
    
    def __parse_signal_index__(x, ndx, stype):
        if isinstance(ndx, int):
            if ndx < 0 or ndx >= len(x):
                raise ValueError("Invalid signal index %d for %d signals" % (ndx, len(x)))
            
            return ndx
        
        elif isinstance(ndx, str):
            ndx = get_index_of_named_signal(x, ndx, stype=stype)
            
        else:
            raise TypeError("invalid indexing type")
            
    
    if not isinstance(func, types.FunctionType):
        raise TypeError("first parameter expected to be a function; got %s instead")
    
    if isinstance(data, (neo.AnalogSignal, DataSignal)):
        return __signal_measure__(func, data, *cursors, **kwargs)
    
    elif isinstance(data, neo.Segment):
        if analog is not None:
            analog = __parse_signal_index__(data, analog, stype=neo.AnalogSignal)
            return __signal_measure__(func, data.analogsignals[analog], *cursors, **kwargs)
            
        elif irregular is not None:
            irregular = __parse_signal_index__(data, irregular, stype=neo.IrregularlySampledDataSignal)
            return __signal_measure__(func, data.irregularlysampledsignals[irregular], *cursors, **kwargs)
        
        else:
            raise TypeError("Analog signal index must be specified")
        
    elif isinstance(data, neo.Block):
        # iterate through segments
        pass
    
    elif isinstance(data, (tuple, list)):
        if all([isinstance(s, (neo.AnalogSignal, DataSignal)) for s in data]):
            # treat as a segment's signal collection
            pass
        
        elif all([isinstance(d, neo.Segment) for d in data]):
            # iterate through segments as for block
            pass
            
        
    return func(data, *cursors, **kwargs)

    
@safeWrapper
def cursors_difference(signal: typing.Union[neo.AnalogSignal, DataSignal], cursor0: typing.Union[SignalCursor, tuple], cursor1: typing.Union[SignalCursor, tuple], channel: typing.Optional[int] = None):
    """Calculates the signal amplitude between two notional vertical cursors.
    
    amplitude = y1 - y0
    
    where y0, y1 are the average signal values across the windows of cursor0 and
    cursor1
    
    Parameters:
    -----------
    signal:neo.AnalogSignal, datatypes.DataSignal
    
    cursor0, cursor1: (x, window) tuples representing, respectively, the 
        cursor's x coordinate (time) and window (horizontal extent).
        
    Returns:
    -------
    
    Python Quantity array with signal's units and shape (signal.shape[1], ) or
    (1, ) when channel is specified.
        
    """
    from gui.signalviewer import SignalCursor as SignalCursor

    y0 = cursor_average(signal, cursor0, channel=channel)
    y1 = cursor_average(signal, cursor1, channel=channel)
    
    return y1-y0

@safeWrapper
def cursors_distance(signal: typing.Union[neo.AnalogSignal, DataSignal], cursor0: typing.Union[SignalCursor, tuple], cursor1: typing.Union[SignalCursor, tuple], channel: typing.Optional[int] = None):
    """Distance between two cursors, in signal samples.
    
    NOTE: The distance between two cursors in the signal domain is simply the
            difference between the cursors' x coordinates!.
    
    """
    ret = [cursor_index(signal, c) for c in (cursor0, cursor1)]
    
    return abs(ret[1]-ret[0])

@safeWrapper
def chord_slope(signal: typing.Union[neo.AnalogSignal, DataSignal], t0: typing.Union[float, pq.Quantity], t1: typing.Union[float, pq.Quantity], w0: typing.Optional[typing.Union[float, pq.Quantity]]=0.001*pq.s, w1: typing.Optional[typing.Union[float, pq.Quantity]] = None, channel: typing.Optional[int] = None):
    """Calculates the chord slope of a signal between two time points t0 and t1.
    
                    slope = (y1 - y0) / (t1 - t0)
    
    The signal values (y0, y1) at time points (t0, t1) are taken as the average 
    of the sample values in a window (w) around t0 and t1:
    
    y0 = signal.time_slice(t0-w0/2, t0+w0/2).mean(axis=0)
    y1 = signal.time_slice(t1-w1/2, t1+w1/2).mean(axis=0)
    
    Parameters:
    ==========
    signal: neo.AnalogSignal, DataSignal
    
    t0: scalar float or python Quantity =  the limits of the interval where
            the chord slope is calculated, including the half-windows before t0
            and after t1;
            
            Their units must be convertible to the signal's time units
    
    w:  a scalar float or python Quantity = a window around the time points, 
        across which the mean signal value is calculated (useful for noisy 
        signals).
        
        Default is 0.001 * pq.s (i.e. 1 ms)
        
    w1: like w (optional default is None). When present, the windows w and w1
    are used respectively, with the time points t0 and t1.
        
    channel: int or None (default). For multi-channel signals, it specifies the 
        signal channel to get the average value from.
        
        When channel is None, the function returns a python Quantity array
        (one value for each channel).
        
        When channel is an int, the function returns the average at the specifed
        channel (if it is valid)
        
    Returns:
    ========
    
    A python quantity array with as many values as there are column vectors
    (channels) in the signal. The units are derived from the signal units and 
    signal's time units.
    
    """
    if isinstance(t0, numbers.Real):
        t0 *= signal.times.units
        
    if isinstance(t1, numbers.Real):
        t1 *= signal.times.units
        
    if isinstance(w, numbers.Real):
        w0 *= signal.times.units
        
    if isinstance(w1, numbers.Real):
        w1 *= signal.times.units
        
    y0 = signal.time_slice(t0-w0/2, t0+w0/2).mean(axis=0)
    
    if w1 is not None:
        y1 = signal.time_slice(t1-w1/2, t1+w1/2).mean(axis=0)
        
    else:
        y1 = signal.time_slice(t1-w0/2, t1+w0/2).mean(axis=0)
        
    #print(y0, y1, t0, t1)
    
    ret = (y1-y0) / (t1-t0)
    
    if channel is None:
        return ret
    
    else:
        return ret[channel].flatten() # so that it can accept array indexing
    
#@safeWrapper
#"def" epoch_chord_slope(signal,
                      #epoch: neo.Epoch,
                      #channel: typing.Optional[int] = None) -> pq.Quantity:
    #pass
    
@safeWrapper
def cursors_chord_slope(signal: typing.Union[neo.AnalogSignal, DataSignal], cursor0: typing.Union[SignalCursor, tuple], cursor1: typing.Union[SignalCursor, tuple], channel: typing.Optional[int] = None):
    """Signal chord slope between two vertical cursors.
    
    The function calculates the slope of a straight line connecting the 
    intersection of the signal with two vertical cursors (of with the vertical
    lines os two crosshair cursors).
    
    The signal value at each cursor is taken as the average of signal samples
    across the cursor's horizontal window if non-zero, or the sample values at 
    the cursor's coordinate.
    
    Parameters:
    ----------
    signal
    
    cursor0, cursor1: tuple (x, window) representing, respectively, the cursor's
        x coordinate (time) and (horizontal) window, or a
        gui.signalviewer.SignalCursor of type "vertical"
    
    """
    from gui.signalviewer import SignalCursor as SignalCursor

    t0 = cursor0[0] if isinstance(cursor0, tuple) else cursor0.x
    
    y0 = cursor_average(signal, cursor0, channel=channel)
    
    if isinstance(t0, float):
        t0 *= signal.times.units
        
    t1 = cursor1[0] if isinstance(cursor1, tuple) else cursor1.x

    if isinstance(t1, float):
        t1 *= signal.times.units
        
    y1 = cursor_average(signal, cursor1, channel=channel)
    
    return (y1-y0)/(t1-t0)
    
@safeWrapper
def epoch2cursors(epoch: neo.Epoch, axis: typing.Optional[typing.Union[pg.PlotItem, pg.GraphicsScene]] = None, **kwargs):
    """Creates vertical signal cursors from a neo.Epoch.
    
    Parameters:
    ----------
    epoch: neo.Epoch
    
    axis: (optional) pyqtgraph.PlotItem, pyqtgraph.GraphicsScene, or None.
    
        Default is None, in which case the function returns cursor parameters.
    
        When not None, the function populates 'axis' with a sequence of 
        vertical SignalCursor objects and returns their references in a list.
        
    Var-keyword parameters:
    ----------------------
    keep_units: bool, optional default is False
        When True, the numeric cursor parameters are python Quantities with the
        units borrowed from 'epoch'
        
    Other keyword parameters are passed to the cursor constructors:
    parent, follower, xBounds, yBounds, pen, linkedPen, hoverPen
    
    See the documentation of signalviewer.SignalCursor.__init__ for details.
    
    Returns:
    --------
    When axis is None, returns a list of tuples of vertical cursor parameters
        (time, window, labels) where:
        
        time = epoch.times + epoch.durations/2.
        window = epoch.durations
        labels = epoch.labels -- the labels of the epoch's intervals
        
    When axis is a pyqtgraph.PlotItem or a pyqtgraph.GraphicsScene, the function
    adds vertical SignalCursors to the axis and returns a list with references
    to them.
    
    Side effects:
    -------------
    When axis is not None, the cursors are added to the PlotItem or GraphicsScene
    specified by the 'axis' parameter.
    """
    from gui.signalviewer import SignalCursor as SignalCursor

    keep_units = kwargs.pop("keep_units", False)
    if not isinstance(keep_units, bool):
        keep_units = False
        
    if keep_units:
        ret = [(t + d/2., d, l) for (t, d, l) in zip(epoch.times, epoch.durations, epoch.labels)]
        
    else:
        ret = [(t + d/2., d, l) for (t, d, l) in zip(epoch.times.magnitude, epoch.durations.magnitude, epoch.labels)]
    
    if isinstance(axis, (pg.PlotItem, pg.GraphicsScene)):
        # NOTE: 2020-03-10 18:23:03
        # cursor constructor accepts python Quantity objects for its numeric
        # parameters x, y, xwindow, ywindow, xBounds and yBounds
        cursors = [SignalCursor(axis, x=t, xwindow=d,
                                cursor_type=SignalCursor.SignalCursorTypes.vertical,
                                cursorID=l) for (t,d,l) in ret]
        return cursors
    
    return ret

@safeWrapper
def epoch2intervals(epoch: neo.Epoch, keep_units:bool = False):
    """Generates a sequence of intervals as triplets (t_start, t_stop, label).
    
    Each interval coresponds to the epoch's interval.
    
    Parameters:
    ----------
    epoch: neo.Epoch
    
    keep_units: bool (default False)
        When True, the t_start and t_stop in each interval are scalar python 
        Quantity objects (units borrowed from the epoch)
    
    """
    if keep_units:
        return [(t, t+d, l) for (t,d,l) in zip(epoch.times, epoch.durations, epoch.labels)]
        
    else:
        return [(t, t+d, l) for (t,d,l) in zip(epoch.times.magnitude, epoch.durations.magnitude, epoch.labels)]
    
@safeWrapper
def intervals2epoch(*args, **kwargs):
    """Construct a neo.Epoch from a sequence of interval tuples or triplets.
    
    Variadic parameters:
    --------------------
    tuples (t0,t1) or triplets (t0,t1,label), or a sequence of tuples or triplets
    each specifying an interval
    
    """
    units = kwargs.pop("units", pq.s)
    if not isinstance(units, pq.Quantity) or units.size > 1:
        raise TypeError("units expected to be a scalar python Quantity")

    name = kwargs.pop("name", "Epoch")
    if not isinstance(name, str):
        raise TypeError("name expected to be a string")
    
    if len(name.strip())==0:
        raise ValueError("name must not be empty")
    
    sort = kwargs.pop("sort", True)
    if not isinstance(sort, bool):
        raise TypeError("sort must be a boolean")
    
    def __generate_epoch_interval__(value):
        if not isinstance(value, (tuple, list)) or len(value) not in (2,3):
            raise TypeError("expecting a tuple of 2 or 3 elements")
        
        if len(value) == 3:
            if not isinstance(value[2], str) or len(value[2].strip()) == 0:
                raise ValueError("expecting a non-empty string as thirs element in the tuple")
            
            l = value[2]
                
        else:
            l = None
            
        u = units # by default if boundaries are scalars
        
        if not all([isinstance(v, (pq.Quantity, numbers.Number)) for v in value[0:2]]):
            raise TypeError("interval boundaries must be scalar numbers or quantities")
        
        if all([isinstance(v, pq.Quantity) for v in value[0:2]]):
            if any([v.size != 1 for v in value[0:2]]):
                raise TypeError("interval boundaries must be scalar quantities")
            
            u = value[0].units #store the units
            
            if value[0].units != value[1].units:
                if not units_convertible(value[0], value[1]):
                    raise TypeError("interval boundaries must have compatible units")
                
                else:
                    value = [float(value[0]), float(value[1].rescale(value[0].units))]
                    
            else:
                value = [float(v) for v in value[0:2]]
            
        t, d = (value[0], value[1] - value[0])
        
        if d < 0:
            raise ValueError("interval cannot have negative duration")

        return (t, d, u) if l is None else (t, d, u, l)
     
    tdl = None
    
    if len(args) == 1:
        if isinstance(args[0], (tuple, list)):
            if len(args[0]) in (2,3): # a sequence with one tuple of 2-3 elements
                if all([isinstance(v, (numbers.Number, pq.Quantity)) for v in args[0][0:2]]):
                    # this can be an interval tuple
                    tdl = [__generate_epoch_interval__(args[0])]
                    
                elif all([isinstance(v, (tuple, list)) and len(v) in (2,3) and all([isinstance(_x, (numbers.Number, pq.Quantity)) for _x in v[0:2]]) for v in args[0]]):
                    # or a sequence of tuples -- feed this into __generate_epoch_interval__
                    # and hope for the best
                    if sort:
                        tdl = [__generate_epoch_interval__(v) for v in sorted(args[0], key=lambda x: x[0])]
                        
                    else:
                        tdl = [__generate_epoch_interval__(v) for v in args[0]]
                    
                else:
                    raise TypeError("incorrect syntax")
                
            else:
                if all([isinstance(v, (tuple, list)) and len(v) in (2,3) and all([isinstance(_x, (numbers.Number, pq.Quantity)) for _x in v[0:2]]) for v in args[0]]):
                    if sort:
                        tdl = [__generate_epoch_interval__(v) for v in sorted(args[0], key=lambda x: x[0])]
                    else:
                        tdl = [__generate_epoch_interval__(v) for v in args[0]]

        else:
            raise TypeError("expecting a sequence of tuples, or a 2- or 3- tuple")
        
    else:
        # sequence of 2- or 3- tuples
        if all([isinstance(v, (tuple, list)) and len(v) in (2,3) and all([isinstance(_x, (numbers.Number, pq.Quantity)) for _x in v[0:2]]) for v in args]):
            if sort:
                tdl = [__generate_epoch_interval__(v) for v in sorted(args, key=lambda x: x[0])]
                
            else:
                tdl = [__generate_epoch_interval__(v) for v in args]
        
        else:
            raise TypeError("expecting 2- or 3- tuples")
        
    if tdl is not None:
        # all numeric elements in tdl are python quantities
        if all([len(v) == 4 for v in tdl]):
            times, durations, units, labels = [x_ for x_ in zip(*tdl)]
            ret = neo.Epoch(times = times, durations = durations, units = units[0], labels=labels)
        else:
            times, durations, units = [x_ for x_ in zip(*tdl)]
            ret = neo.Epoch(times = times, durations = durations, units=units[0])
                
        return ret

@safeWrapper
def intervals2cursors(*args, **kwargs):
    """Construct a neo.Epoch from a sequence of interval tuples or triplets.
    
    Variadic parameters:
    --------------------
    triplets (t0,t1,label), or a sequence of tuples or triplets
    each specifying an interval
    
    """
    from gui.signalviewer import SignalCursor as SignalCursor

    axis = kwargs.pop("axis", None)
    if not isinstance(axis, (int, pg.PlotItem, type(None))):
        raise TypeError("axis expected to be an int, a PlotItem or None; got %s instead" % type(axis).__name__)

    sort = kwargs.pop("sort", True)
    
    if not isinstance(sort, bool):
        raise TypeError("sort must be a boolean")
    
    def __generate_cursor_params__(value):
        # start, stop, label
        if not isinstance(value, (tuple, list)) or len(value) != 3:
            raise TypeError("expecting a tuple of 3 elements")
        
        if not isinstance(value[2], str) or len(value[2].strip()) == 0:
            raise ValueError("expecting a non-empty string as thirs element in the tuple")
        
        l = value[2]
        
        if not all([isinstance(v, (pq.Quantity, numbers.Number)) for v in value[0:2]]):
            raise TypeError("interval boundaries must be scalar numbers or quantities")
        
        if all([isinstance(v, pq.Quantity) for v in value[0:2]]):
            if any([v.size != 1 for v in value[0:2]]):
                raise TypeError("interval boundaries must be scalar quantities")
            
            if value[0].units != value[1].units:
                if not units_convertible(value[0], value[1]):
                    raise TypeError("interval boundaries must have compatible units")
                
                else:
                    value = [float(value[0]), float(value[1].rescale(value[0].units)), value[2]]
                    
            else:
                value = [float(v) for v in value[0:2]] + [value[2]]
            
        x, xwindow = (value[0], value[1]-value[0])
        
        if xwindow < 0:
            raise ValueError("interval cannot have negative duration")
        
        x += xwindow/2. 
        
        return (x, xwindow, l)
     
    xwl = None
    
    if len(args) == 1:
        if isinstance(args[0], (tuple, list)):
            if len(args[0]) in (2,3): # a sequence with one tuple of 2-3 elements
                if all([isinstance(v, (numbers.Number, pq.Quantity)) for v in args[0][0:2]]):
                    # this can be an interval tuple
                    xwl = [__generate_cursor_params__(args[0])]
                    
                elif all([isinstance(v, (tuple, list)) and len(v) in (2,3) and all([isinstance(_x, (numbers.Number, pq.Quantity)) for _x in v[0:2]]) for v in args[0]]):
                    # or a sequence of tuples -- feed this into __generate_cursor_params__
                    # and hope for the best
                    if sort:
                        xwl = [__generate_cursor_params__(v) for v in sorted(args[0], key=lambda x: x[0])]
                    
                    else:
                        xwl = [__generate_cursor_params__(v) for v in args[0]]
                    
                else:
                    raise TypeError("incorrect syntax")
                
            else:
                if all([isinstance(v, (tuple, list)) and len(v) in (2,3) and all([isinstance(_x, (numbers.Number, pq.Quantity)) for _x in v[0:2]]) for v in args[0]]):
                    if sort:
                        xwl = [__generate_cursor_params__(v) for v in sorted(args[0], key=lambda x: x[0])]

        else:
            raise TypeError("expecting a sequence of tuples, or a 2- or 3- tuple")
        
    else:
        # sequence of 2- or 3- tuples
        if all([isinstance(v, (tuple, list)) and len(v) in (2,3) and all([isinstance(_x, (numbers.Number, pq.Quantity)) for _x in v[0:2]]) for v in args]):
            if sort:
                xwl = [__generate_cursor_params__(v) for v in sorted(args, key=lambda x: x[0])]
            
            else:
                xwl = [__generate_cursor_params__(v) for v in args]
        
        else:
            raise TypeError("expecting 2- or 3- tuples")
        
    if xwl is not None:
        if axis is not None:
            cursors = [SignalCursor(axis, x=p[0], xwindow=p[1], cursorID=p[2], 
                                    cursor_type=SignalCursor.SignalCursorTypes.vertical) for p in xwl]
                
            return cursors
        
        return xwl

@safeWrapper
def epoch_average(signal: typing.Union[neo.AnalogSignal, DataSignal], epoch: neo.Epoch, channel: typing.Optional[int] = None):
    """Signal average across an epoch's intervals.
    
    Parameters:
    -----------
    signal: neo.AnalogSignal or datatypes.DataSignal
    
    epoch: neo.Epoch
    
    channel: int or None (default)
    
    Returns:
    --------
    
    A list of python Quantity objects with as many elements as there
    are times,durations pairs in the epoch.
    
    For multi-channel signals, the Quantity are arrays of size that equals the
    number of channels.
    
    """
    
    t0 = epoch.times
    t1 = epoch.times + epoch.durations
    
    ret = [signal.time_slice(t0_, t1_).mean(axis=0) for (t0_, t1_) in zip(t0,t1)]
    
    if isinstance(channel, int):
        ret = [r[channel].flatten() for r in ret]
        
    return ret

@safeWrapper
def plot_signal_vs_signal(x: typing.Union[neo.AnalogSignal, neo.Segment, neo.Block], *args, **kwargs):
    from plots import plots
    
    if isinstance(x, neo.Block):
        segment = kwargs.pop("segment", 0)
        
        return plot_signal_vs_signal(x.segments[segment], **kwargs)
        
    elif isinstance(x, neo.Segment):
        sig0 = kwargs.pop("sig0", 0)
        sig1 = kwargs.pop("sig1", 1)
        
        if isinstance(sig0, str):
            sig0 = get_index_of_named_signal(x, sig0, stype=neo.AnalogSignal)
            
        if isinstance(sig1, str):
            sig1 = get_index_of_named_signal(x, sig1, stype=neo.AnalogSignal)
        
        return plot_signal_vs_signal(x.analogsignals[sig0], x.analogsignals[sig1], **kwargs)
        
    elif isinstance(x, neo.AnalogSignal):
        return plots.plotZeroCrossedAxes(x,args[0], **kwargs)


@safeWrapper
def plot_spike_waveforms(x: neo.SpikeTrain, figure: typing.Union[mpl.figure.Figure, type(None)] = None, new: bool = True, legend: bool = False):
    import matplotlib.pyplot as plt
    
    if not isinstance(x, neo.SpikeTrain):
        raise TypeError("Expected a neo.SpikeTrain object; got %s instead" % (type(x).__name__))

    if (x.waveforms is None) or (not x.waveforms.size):
        return
    
    if figure is None:
        figure = plt.gcf()
        
    elif type(figure).__name__ == "Figure":
        plt.figure(figure.number)
        
    else:
        raise TypeError("'figure' argument must be None or a matplotlib figure; got %s instead" % type(figure).__name__)
    
    if new:
        plt.clf()
        
    lines = plt.plot(np.squeeze(x.waveforms.T))
    
    if legend:
        for k,l in enumerate(lines):
            l.set_label("spike %d" % (k))
            
        plt.legend()
        
        figure.canvas.draw_idle()
    
    return lines
    
@safeWrapper
def resample_poly(sig, new_rate, p=1000, window=("kaiser", 5.0)):
    """Resamples signal using a polyphase filtering.
    
    Resampling uses polyphase filtering (scipy.signal.resample_poly) along the
    0th axis.
    
    Parameters:
    ===========
    
    sig: neo.AnalogSignal or datatypes.DataSignal
    
    new_rate: either a float scalar, or a Python Quantity 
            When a Python Quantity, it must have the same units as signal's 
            sampling RATE units.
            
            Alternatively, if it has the same units as the signal's sampling 
            PERIOD, its inverse will be taken as the new sampling RATE.
             
            NOTE: It must be strictly positive i.e. new_rate > 0
             
            When new_rate == sig.sampling_rate, the function returns a copy of sig.
             
            Otherwise, the function returns a copy of sig where all columns are resampled via
            scipy.signal.resample_poly
    
    p: int
        factor of precision (default 1000): power of 10 used to calculate up/down sampling:
        up = new_rate * p / signal_sampling_rate
        down = p
        
    window: string, tuple, or array_like, optional
        Desired window to use to design the low-pass filter, or the FIR filter 
        coefficients to employ. see scipy.signal.resample_poly() for details
    
    """
    from scipy.signal import resample_poly as resample
    
    using_rate=True
    
    if not isinstance(sig, neo.AnalogSignal):
        raise TypeError("First parameter expected to be a neo.AnalogSignal; got %s instead" % type(sig).__name__)
    
    if isinstance(new_rate, numbers.Real):
        new_rate = new_rate * sig.sampling_rate.units
        
    elif isinstance(new_rate, pq.Quantity):
        if new_rate.size > 1:
            raise TypeError("Expecting new_rate a scalar quantity; got a shaped array %d" % new_res)
        
        if new_rate.units != sig.sampling_rate.units:
            if new_rate.units == sig.sampling_period.units:
                using_rate = False
                
            else:
                raise TypeError("Second parameter should have the same units as signal's sampling rate (%s); it has %s instead" % (sig.sampling_rate.units, new_rate.units))
                
    
    if new_rate <= 0:
        raise ValueError("New sampling rate (%s) must be strictly positive !" % new_rate)
    
    p = int(p)
    
    if using_rate:
        if new_rate == sig.sampling_rate:
            return sig.copy()
        
        up = int(new_rate / sig.sampling_rate * p)
        
    else:
        if new_rate == sig.sampling_period:
            return sig.copy()
            
        up = int(sig.sampling_period / new_rate * p)
    
    if using_rate:
        ret = neo.AnalogSignal(resample(sig, up, p, window=window), 
                               units = sig.units, 
                               t_start = sig.t_start,
                               sampling_rate = new_rate)
        
    else:
        ret = neo.AnalogSignal(resample(sig, up, p, window=window), 
                               t_start = sig.t_start,
                               units = sig.units, 
                               sampling_period = new_rate) 
        
    ret.name = sig.name
    ret.description = "%s resampled %f fold on axis 0" % (sig.name, up)
    ret.annotations = sig.annotations.copy()
    
    return ret

@safeWrapper
def average_blocks(*args, **kwargs):
    """Generates a block containing a list of averaged AnalogSignal data from the *args.
    
    Parameters:
    -----------
    
    args: a comma-separated list of neo.Block objects
    
    kwargs: keyword/value pairs:
    
        count               how many analogsignals into one average
        
        every               how many segments to skip between averages
        
        segment             index of segments taken into average
        
        analog              index of signal into each of the segments to be used;
                            can also be a signal name
        
        name                see neo.Block docstring
        
        annotation          see neo.Block docstring
        
        rec_datetime        see neo.Block docstring
        
        file_origin         see neo.Block docstring
        
        file_datetime       see neo.Block docstring
        
    
    Returns:
    --------
    
    A new Block containing AnalogSignal data that are averages of the AnalogSignal 
    object in the *args across the segments, taken n segments at a time, every m segments.
    
    Depending on the values of 'n' and 'm', the result may contain several segments,
    each containing AnalogSignals averaged from the data.
    
    NOTE:
    
    By contrast to average_blocks_by_segments, this function can result in the 
    average of ALL segments in a block (or sequence of blocks) in  particular
    when "count" and "every" are not set (see below).
    
    The function only takes AnalogSignal data, and discards IrregularlySampledSignal
    SpikeTrain, Event and Epoch data that may be present in the blocks specified
    by *args.
    
    This is because, by definition, only AnalogSignal data may be enforced to be 
    shape-compatible for averaging, and this is what usually one is after, when 
    averaging multiple electrophysiology record sweeps acquired with the same
    protocol (sampling, duration, etc).
    
    For this reason only analog_index can be specified, to select from the
    analogsignals list in the segments.
    
    Examples of usage:
    ------------------
    
    >>> blocklist = getvars(sel=neo.Block, sort=True, by_name=False, sortkey="rec_datetime")
    >>> # or:
    >>> blocklist = getvars(locals(), sel="[\W]*common_data_name*", sort=True, by_name=True)
    >>> # then:
    >>> ret = average_blocks(blocklist, segment_index=k, count=n, every=m)
    
    ret is a neo.Block with segments where each segment contains the average signals from kth segment
    for groups of "n" blocks taken every "m" from the list of blocks given as starred argument(s) 

    """
    def __applyRecDateTime(sgm, blk):
        if sgm.rec_datetime is None:
            sgm.rec_datetime = blk.rec_datetime
            
        return sgm
        
    def __get_blocks_by_name__(*arg):
        ws = workspacefunctions.user_workspace() 
        
        if not all([isinstance(a, str) for a in arg]):
            raise TypeError("Expecting strings only")
        
        if len(arg) == 1:
            ret_ = workspacefunctions.getvars(arg[0], glob=True, var_type=neo.Block,
                                                ws=ws)
            
        elif len(arg) > 1:
            ret_ = workspacefunctions.getvars(*arg, glob=True, var_type=neo.Block,
                                                ws=ws)
        else:
            raise ValueError("Expecting at least one string")
        
        return ret_
            
        
    if len(args) == 0:
        return None
    
    blocks=list()
    
    if len(args) == 1:
        if isinstance(args[0], str): # glob for variable names
            blocks = __get_blocks_by_name__(args[0])
                #cframe = inspect.getouterframes(inspect.currentframe())[1][0]
                #blocks = workspacefunctions.getvars(args[0], glob=True,
                                                        #ws=cframe, as_dict=False,
                                                        #sort=False)
                
        elif isinstance(args[0], (tuple, list)):
            if all([isinstance(a, neo.Block) for a in args[0]]): # list of blocks
                blocks = args[0] # unpack the tuple
                
            elif all([isinstance(a, str) for a in args[0]]): # list of names
                blocks = __get_blocks_by_name__(*args[0])
                
            else:
                raise ValueError("Invalid argument %s" % args[0])
                
            
    else:
        if all([isinstance(a, neo.Block) for a in args]):
            blocks = args
            
        elif all([isinstance(a, str) for a in args]):
            blocks = __get_blocks_by_name__(*args)
            
        else:
            raise ValueError("Invalid argument %s" % args)
            
    if len(blocks)==0:
        return
            
    block_names = [b.name for b in blocks]
            
        
    #print(args)
    #try:
        #cframe = inspect.getouterframes(inspect.currentframe())[1][0]
        #bname = ""
        #for b in args:
            #if b.name is None or len(b.name) == 0:
                #if b.file_origin is None or len(b.file_origin) == 0:
                    #for (k,v) in cframe.f_globals.items():
                        #if isinstance(v, neo.Block) and v == b:
                            #bname = k
                #else:
                    #bname = b.file_origin
            #else:
                #bname = b.name
                
            #block_names.append(bname)
                    
        
    #finally:
        #del(cframe)
        
    
    n = None
    m = None
    segment_index = None
    analog_index = None
    
# we do something like this:
    #BaseDataPath0MinuteAverage = neo.Block()
    #BaseDataPath0MinuteAverage.segments = ephys.average_segments(BaseDataPath0.segments, n=6, every=6)
    #sgw.plot(BaseDataPath0MinuteAverage, signals=["Im_prim_1", "Vm_sec_1"])

    
    ret = neo.core.block.Block()
    
    if len(kwargs) > 0 :
        for key in kwargs.keys():
            if key not in ["count", "every", "name", "segment", 
                           "analog", "annotation", "rec_datetime", 
                           "file_origin", "file_datetime"]:
                raise RuntimeError("Unexpected named parameter %s" % key)
            
        if "count" in kwargs.keys():
            n = kwargs["count"]
            
        if "every" in kwargs.keys():
            m = kwargs["every"]
            
        if "name" in kwargs.keys():
            ret.name = kwargs["name"]
            
        if "segment" in kwargs.keys():
            segment_index = kwargs["segment"]
            
        if "analog" in kwargs.keys():
            analog_index = kwargs["analog"]
            
        if "annotation" in kwargs.keys():
            ret.annotation = kwargs["annotation"]

        if "rec_datetime" in kwargs.keys():
            ret.rec_datetime = kwargs["datetime"]
            
        if "file_origin" in kwargs.keys():
            ret.file_origin = kwargs["file_origin"]
            
        if "file_datetime" in kwargs.keys():
            ret.file_datetime = kwargs["file_datetime"]
            
    if segment_index is None:
        segments = [[__applyRecDateTime(sgm, b) for sgm in b.segments] for b in blocks]
        segment_str = "all"
        
    elif isinstance(segment_index, int):
        segments = [__applyRecDateTime(b.segments[segment_index], b) for b in blocks if segment_index < len(b.segments)]
        segment_str = str(segment_index)
        
    else:
        raise TypeError("Unexpected segment index type (%s) -- expected an int" % segment_index)
    
    #print(len(segments))
    
    if analog_index is not None:
        signal_str = str(analog_index)
    else:
        signal_str = "all"
        
    block_names= list()
    
    #print(args)
    
    ret.segments = average_segments(segments, count=n, every=m, analog_index=analog_index)
    
    ret.annotations["Averaged"] = dict()
    ret.annotations["Averaged"]["Count"] = n
    ret.annotations["Averaged"]["Every"] = m
    ret.annotations["Averaged"]["Origin"] = dict()
    ret.annotations["Averaged"]["Origin"]["Blocks"]   = "; ".join(block_names)
    ret.annotations["Averaged"]["Origin"]["Segments"] = segment_str
    ret.annotations["Averaged"]["Origin"]["Signals"]  = signal_str
    
    return ret

@safeWrapper
def average_blocks_by_segments(*args, **kwargs):
    """Generates a neo.Block whose segments contains averages of the corresponding
    signals in the corresponding segments across a sequence of blocks.
    
    All blocks in the sequence must contain the same number of segments.
    
    By contrast to average_blocks, the result will contain the same number of 
    segments as each block in *args, and each segment will contain an average
    of the corresponding analogsignals from the segment at the corresponding index 
    across all blocks.
    
    
    Arguments:
    =========
    
    args: a sequence of comma-separated list of neo.Blocks
    
    **kwargs:
    ========
    analog: which signal into each of the segments to consider
                  can also be a signal name; optional default is None 
                  (thus taking all signals)
                  
    name: str or None (optional default is None)
                  
    NOTE: the signals will keep their individuality in the averaged segment
    
    NOTE: do not use for I-clamp experiments where the amount of injected current
    is different in each segment!!!
    
    
    """
    if len(args) == 0:
        return None
    
    if len(args) == 1:
        args = args[0] # unpack the tuple
    
    analog_index = None
    
    name = None
    
    if len(kwargs) > 0:
        if "analog_index" in kwargs.keys():
            analog_index = kwargs["analog"]
            
        if "name" in kwargs.keys():
            name = kwargs["name"]
            
            
    # first check all blocks in the list have the same number of segments
    
    nSegs = [len(block.segments) for block in args]
    
    if min(nSegs) != max(nSegs):
        raise ValueError("The blocks must contain equal number of segments")
    
    nSegs = nSegs[0]
    
    # the check all segments have the same number of signals
    #nSigs = [[len(segment.analogsignals) for segment in block.segments] for block in args]
    
    ret = neo.Block()
    
    for k in range(nSegs):
        nSigs = [len(block.segments[k].analogsignals) for block in args]
        if min(nSigs) != max(nSigs):
            raise ValueError("Corresponding segments must have the same number of signals")
        
        segment = average_segments([block.segments[k] for block in args], analog_index = analog_index)
        ret.segments.append(segment[0])
    
    ret.name="Segment by segment average %s" % name
    
    return ret

@safeWrapper
def remove_signal_offset(sig):
    if not isinstance(sig, neo.AnalogSignal):
        raise TypeError("Expecting an AnalogSignal; got %s instead" % type(sig).__name__)
    
    return sig - sig.min()

@safeWrapper
def batch_normalise_signals(*arg):
    ret = list()
    for sig in arg:
        ret.append(peak_normalise_signal(sig))
        
    return ret

@safeWrapper
def batch_remove_offset(*arg):
    ret = list()
    for sig in arg:
        ret.append(remove_signal_offset(sig))

    return ret
    
@safeWrapper
def peak_normalise_signal(sig, minVal=None, maxVal=None):
    """Returns a peak-normalized copy of the I(V) curve
    
    Positional parameters:
    ----------------------
    
    sig = AnalogSignal with Im data (typically, a time slice corresponding to the
            Vm ramp)
            
    minVal, maxVal = the min and max values to normalize against;
    
    Returns:
    -------
    
    AnalogSignal normalized according to:
    
            ret = (sig - minVal) / (maxVal - minVal)
    
    """
    
    #return neo.AnalogSignal((sig - minVal)/(maxVal - minVal), \
                            #units = pq.dimensionless, \
                            #sampling_rate = sig.sampling_rate, \
                            #t_start = sig.t_start)
                        
    if any([v is None for v in (minVal, maxVal)]):
        if isinstance(sig, neo.AnalogSignal):
            maxVal = sig.max()
            minVal = sig.min()
            
        else:
            raise TypeError("When signal is not an analog signal both minVal and maxVal must be specified")

    return (sig - minVal)/(maxVal - minVal)

@safeWrapper
def average_segments_in_block(data, **kwargs):
    """Returns a new neo.Block containing one segment which is the average of 
    the segments in the block.
    
    Parameters:
    ==========
    "data" a neo.Block.
        
    Var-keyword parameters:
    ======================
    "segment_index" = integer, sequence of integers, range or slice that chooses
            which segment(s) are taken into the average
            
            optional: by default, all segments will be included in the average
        
        e.g. from a block with 5 segments, one may choose to calculate the
        average between segments 1, 3 and 5: segment_index = [1,3,5]
        
    "analog_index" = integer or string, or sequence of integers or strings
        that indicate which channels need to be included in the averaged
        segment. This argument is pased directly to ephys.average_segments
        function.
        
        NOTE: All segments in "Data" must contain the same number of channels,
        and these channels must have the same names.
        
    
    
    This will average individual signals in all the segments in data.
    The time base will be that of the first segment in data.
    
    
    Arguments:
    =========
    
    To operate on a list of segments, use "ephys.average_blocks" function.
    
    Keyword Arguments **kwargs: key/value pairs:
    ================================================
            
    Returns:
    =======
    
    A neo.Block with one segment which represents the average of the segments in
    "data" (either all segments, or of those selected by "segment_index").
    
    The new (average) segment contains averages of all signals, or of the signals
    selected by "analog_index".
    
    TODO: include other signal types contained in Segment
    """

    if not isinstance(data, neo.Block):
        raise TypeError("Data must be a neo.Block instance; got %s instead" % (type(data).__name__))
    
            
    segment_index = None
    analog_index = None
    
    if len(kwargs) > 0:
        for key in kwargs.keys():
            if key not in ["segment_index", "analog_index", 
                           "annotation", "rec_datetime", 
                           "file_origin", "file_datetime"]:
                raise RuntimeError("Unexpected named parameter %s" % key)
            
        if "segment_index" in kwargs.keys():
            segment_index = kwargs["segment_index"]
            
        if "analog_index" in kwargs.keys():
            analog_index = kwargs["analog_index"]
            
    
    if segment_index is not None:
        if isinstance(segment_index, (tuple, list)) and all(isinstance(k, numbers.Integral) and k >=0 and k <len(data.segments) for k in segment_index):
            sgm = [data.segments[k] for k in segment_index]
            
        elif isinstance(segment_index, (slice, numbers.Integral)):
            sgm = data.segments[segment_index]
            
        elif isinstance(segment_index, range):
            sgm = [data.segments[k] for k in segment_index]
            
        else:
            raise ValueError("Invalid segment index; got: %s" % (str(segment_index)))
        
    else:
        sgm = data.segments

    ret = neo.Block()
    ret.segments = average_segments(sgm, analog_index = analog_index)
    
    ret.annotations = data.annotations
    ret.file_origin = data.file_origin
    ret.rec_datetime = data.rec_datetime
    
    if data.name is None or (isinstance(data.name, str) and len(data.name) == 0):
        #data_name = kwargs["data"]
        if data.file_origin is not None and isinstance(data.file_origin, str) and len(data.file_origin) > 0:
            data_name = data.file_origin
            
        else:
            # find the variable name of data in the caller stack frame
            cframe = inspect.getouterframes(inspect.currentframe())[1][0]
            try:
                for (k,v) in cframe.f_globals.items():
                    if isinstance(v, neo.Block) and v == data:
                        data_name = k
            finally:
                del(cframe)
                data_name = "Block"
            
    else:
        data_name = data.name
        
    ret.name = "Average of %s" % (data_name)
        
    if segment_index is None:
        ret.annotations["averaged_segments"] = "all segments"
    else:
        ret.annotations["averaged_segments"] = segment_index
        
    if analog_index is None:
        ret.annotations["averaged_signals"] = "all signals"
    else:
        ret.annotations["averaged_signals"] = analog_index
        
    return ret
        
@safeWrapper
def average_segments(*args, **kwargs):
    """Returns a list of Segment objects containing averages of the signals from
    each segment in args.
    
    Called e.g. by average_segments_in_block
    
    args    comma-separated list of neo.Segment objects, or a sequence (list, tuple) of segments
    kwargs  keyword/value pairs
        count
        every
        analog_index
        
    
    """
    from core import datatypes as dt
    
    def __resample_add__(signal, new_signal):
        if new_signal.sampling_rate != signal.sampling_rate:
            ss = resample_poly(new_signal, signal.sampling_rate)
            
        else:
            ss = new_signal
            
        # neo.AnalogSignal and DataSignal always have ndim == 2
        
        if ss.shape != signal.shape:
            ss_ = neo.AnalogSignal(np.full_like(signal, np.nan),
                                                units = signal.units,
                                                t_start = signal.t_start,
                                                sampling_rate = signal.sampling_rate,
                                                name = ss.name,
                                                **signal.annotations)
            
            src_slicing = [slice(k) for k in ss.shape]
            
            dest_slicing = [slice(k) for k in ss_.shape]
            
            if ss.shape[0] < ss_.shape[0]:
                dest_slicing[0] = src_slicing[0]
                
            else:
                src_slicing[0]  = dest_slicing[0]
                
            if ss.shape[1] < ss_.shape[1]:
                dest_slicing[1] = src_slicing[1]
                
            else:
                src_slicing[1] = dest_slicing[1]
                
            ss_[tuple(dest_slicing)] = ss[tuple(src_slicing)]
            
            ss = ss_
                
        return ss
    
    #print(args)
    
    if len(args) == 0:
        return
    
    if len(args) == 1:
        args = args[0]
    
    if all([isinstance(s, (tuple, list)) for s in args]):
        slist = list()
        
        for it in args:
            for s in it:
                slist.append(s)
                
        args = slist
        
    if not all([isinstance(a, neo.Segment) for a in args]):
        raise TypeError("This function only works with neo.Segment objects")
        
    n = None
    m = None
    analog_index = None
    
    
    if len(kwargs) > 0:
        if "count" in kwargs.keys():
            n = kwargs["count"]
            
        if "every" in kwargs.keys():
            m = kwargs["every"]
            
        if "analog_index" in kwargs.keys():
            analog_index = kwargs["analog_index"]
            
    if n is None:
        n = len(args)
        m = None
        
    if m is None:
        ranges_avg = [range(0, len(args))] # take the average of the whole segments list
        
    else:
        ranges_avg = [range(k, k + n) for k in range(0,len(args),m)] # this will result in as many segments in the data block
        
        
    #print("ranges_avg ", ranges_avg)
    
    if ranges_avg[-1].stop > len(args):
        ranges_avg[-1] = range(ranges_avg[-1].start, len(args))
        
    #print("ranges_avg ", ranges_avg)
    
    ret_seg = list() #  a LIST of segments, each containing averaged analogsignals!
    
    if analog_index is None: #we want an average across the Block list for all signals in the segments
        if not all([len(arg.analogsignals) == len(args[0].analogsignals) for arg in args[1:]]):
            raise ValueError("All segments must have the same number of analogsignals")
        
        for range_avg in ranges_avg:
            #print("range_avg: ", range_avg.start, range_avg.stop)
            #continue
        
            seg = neo.core.segment.Segment()
            
            for k in range_avg:
                if k == range_avg.start:
                    if args[k].rec_datetime is not None:
                        seg.rec_datetime = args[k].rec_datetime

                    for sig in args[k].analogsignals:
                        seg.analogsignals.append(sig.copy())

                elif k < len(args):
                    for (l,s) in enumerate(args[k].analogsignals):
                        seg.analogsignals[l] += __resample_add__(seg.analogsignals[l], s)

            for sig in seg.analogsignals:
                sig /= len(range_avg)

            ret_seg.append(seg)
            
    elif isinstance(analog_index, str): # only one signal indexed by name
        for range_avg in ranges_avg:
            seg = neo.core.segment.Segment()
            for k in range_avg:
                if k == range_avg.start:
                    if args[k].rec_datetime is not None:
                        seg.rec_datetime = args[k].rec_datetime
                        
                    seg.analogsignals.append(args[k].analogsignals[get_index_of_named_signal(args[k], analog_index)].copy())
                    
                else:
                    s = args[k].analogsignals[get_index_of_named_signal(args[k], analog_index)].copy()

                    seg.analogsignals[0] += __resample_add__(seg.analogsignals[0], s)
                    
            seg.analogsignals[0] /= len(range_avg) # there is only ONE signal in this segment!
            
            ret_seg.append(seg)
            
    elif isinstance(analog_index, int):
        #print("analog_index ", analog_index)
        for range_avg in ranges_avg:
            seg = neo.core.segment.Segment()
            for k in range_avg:
                if args[k].rec_datetime is not None:
                    seg.rec_datetime = args[k].rec_datetime
                    
                if k == range_avg.start:
                    seg.analogsignals.append(args[k].analogsignals[analog_index].copy())
                    
                else:
                    s = args[k].analogsignals[analog_index].copy()
                    
                    seg.analogsignals[0] += __resample_add__(seg.analogsignals[0], s)
                    
            seg.analogsignals[0] /= len(range_avg)# there is only ONE signal in this segment!
            
            ret_seg.append(seg)
            
    elif isinstance(analog_index, (list, tuple)):
        for range_avg in ranges_avg:
            seg = neo.core.segment.Segment()
            for k in range_avg:
                if k == range_avg.start:
                    if args[k].rec_datetime is not None:
                        seg.rec_datetime = args[k].rec_datetime

                    for sigNdx in analog_index:
                        if isinstance(sigNdx, str):
                            sigNdx = get_index_of_named_signal(args[k], sigNdx)
                            
                        seg.analogsignals.append(args[k].analogsignals[sigNdx].copy()) # will raise an error if sigNdx is of unexpected type
                        
                else:
                    for ds in range(len(analog_index)):
                        sigNdx = analog_index[ds]
                        
                        if isinstance(sigNdx, str):
                            sigNdx = get_index_of_named_signal(args[k], sigNdx)
                            
                        s = args[k].analogsignals[sigNdx].copy()
                        
                        seg.analogsignals[ds] += __resample_add__(seg.analogsignals[ds], s)
                        
            for sig in seg.analogsignals:
                sig /= len(range_avg)
            
            ret_seg.append(seg)
            
    else:
        raise TypeError("Unexpected type for signal index")
    
    return ret_seg
    
@safeWrapper
def average_signals(*args, fun=np.mean):
    """ Returns an AnalogSignal containing the element-by-element average of several neo.AnalogSignals.
    All signals must be single-channel and have compatible shapes and sampling rates.
    """
    
    if len(args) == 0:
        return
    
    if len(args) == 1 and isinstance(args[0], (list, tuple)) and all([isinstance(a, neo.core.analogsignal.AnalogSignal) for a in args[0]]):
        args = args[0]

    #ret = args[0].copy() # it will inherit t_start, t_stop, name, annotations, sampling_rate
    
    if any([s.shape != args[0].shape for s in args]):
        raise ValueError("Signals must have identical shape")
    
    if any([s.shape[1]>1 for s in args]):
        raise ValueError("Expecting single-channel signals only")
    
    ret_signal = fun(np.concatenate(args, axis=1), axis=1)
    
    return ret_signal
    #if all([sig.shape == args[0].shape for sig in args[1:]]):
        #ret_signal = fun(np.concatenate(args, axis=1), axis=1)
        #return ret_signal
        
        ##for sig in args[1:]:
            ##ret += sig
            
        ##ret /= len(args)
        
    #else:
        #raise ValueError("Cannot average AnalogSignal objects of different shapes")
        
    
    return ret

@safeWrapper
def aggregate_signals(*args, name_prefix:str, collectSD:bool=True, collectSEM:bool=True):
    """Returns signal mean, SD, SEM, and number of signals in args.
    All signals must be single-channel.
    
    Keyword parameters:
    
    name_prefix : a str; must be specified (default is None)
    
    Returns a dict
    
    """
    from . import datatypes as dt
    
    if len(args) == 0:
        return
    
    if len(args) == 1 and isinstance(args[0], (list, tuple)) and all([isinstance(a, (neo.AnalogSignal, Datasignal)) for a in args[0]]):
        args = args[0]

    if any([s.shape != args[0].shape for s in args]):
        raise ValueError("Signals must have identical shape")
    
    if any([s.shape[1] > 1 for s in args]):
        raise ValueError("Expecting single-channel signals only")
    
    count = len(args)
    
    allsigs = np.concatenate(args, axis=1)
    
    ret_mean = np.mean(allsigs, axis=1).magnitude
    
    ret_SD = np.std(allsigs, axis = 1, ddof=1).magnitude
    
    ret_SEM = ret_SD/(np.sqrt(count-1))
    
    if collectSD:
        ret_mean_SD = np.concatenate((ret_mean[:,np.newaxis], 
                                      (ret_mean-ret_SD)[:,np.newaxis], 
                                      (ret_mean + ret_SD)[:,np.newaxis]),
                                     axis=1)
        suffix = "mean_SD"
        
        ret_mean_SD = neo.AnalogSignal(ret_mean_SD, units = args[0].units,
                                       sampling_period = args[0].sampling_period,
                                       name = "%s_%s" % (name_prefix, suffix))
        
    else:
        ret_mean_SD = None
        
    if collectSEM:
        ret_mean_SEM = np.concatenate((ret_mean[:,np.newaxis], 
                                       (ret_mean - ret_SEM)[:,np.newaxis],
                                       (ret_mean + ret_SEM)[:,np.newaxis]), 
                                     axis=1)
        
        suffix = "mean_SEM"
        
        ret_mean_SEM = neo.AnalogSignal(ret_mean_SEM, units = args[0].units,
                                        sampling_period = args[0].sampling_period,
                                        name = "%s_%s" % (name_prefix, suffix))
    
    else:
        ret_mean_SEM = None
    
    suffix = "mean"
        
    ret_mean = neo.AnalogSignal(ret_mean, units = args[0].units, 
                                sampling_period = args[0].sampling_period, 
                                name = "%s_%s" % (name_prefix, suffix))
    
        
    ret_SD = neo.AnalogSignal(ret_SD, units = args[0].units,
                              sampling_period = args[0].sampling_period,
                              name = "%s_SD" % name_prefix)
    
    ret_SEM = neo.AnalogSignal(ret_SEM, units = args[0].units,
                              sampling_period = args[0].sampling_period,
                              name = "%s_SEM" % name_prefix)
    
    
    ret = dict()
    
    ret["mean"] = ret_mean
    ret["sd"] = ret_SD
    ret["SEM"] = ret_SEM
    ret["mean-SEM"] = None
    ret["mean-SD"] = None
    ret["name"] = name_prefix
    ret["count"] = count
    
    if ret_mean_SEM is not None:
        ret["mean-SEM"] = ret_mean_SEM
        
    if ret_mean_SD is not None:
        ret["mean-SD"]  = ret_mean_SD

    return ret
    
    
    
@safeWrapper
def convolve(sig, w, **kwargs):
    """1D convolution of neo.AnalogSignal sig with kernel "w".
    
    Parameters:
    -----------
    
    sig : neo.AnalogSignal; if it has multiple channels, the convolution is
        applied for each channel
        
    w : 1D array-like
    
    Var-keyword parameters are passed on to the scipy.signal.convolve function,
    except for the "mode" which is always set to "same"
    """
    
    from scipy.signal import convolve
    
    name = kwargs.pop("name", "")
    
    units = kwargs.pop("units", pq.dimensionless)
    
    kwargs["mode"] = "same" # force "same" mode for convolution
    
    if sig.shape[1] == 1:
        ret = neo.AnalogSignal(convolve(sig.magnitude.flatten(), w, **kwargs),\
                            units = sig.units, \
                            t_start = sig.t_start, \
                            sampling_period = sig.sampling_period,\
                            name = "%s convolved" % sig.name)
        
    else:
        csig = [convolve(sig[:,k].magnitude.flatten(), w, **kwargs)[:,np.newaxis] for k in range(sig.shape[1])]
        
        ret = neo.AnalogSignal(np.concatenate(csig, axis=1),
                               units = sig.units,
                               t_start = sig.t_start,
                               sampling_period = sig.sampling_period,
                               name = "%s convolved" % sig.name)
        
    ret.annotations.update(sig.annotations)
    
    return ret


@safeWrapper
def parse_step_waveform_signal(sig, method="state_levels", **kwargs):
    """Parse a step waveform -- containing two states ("high" and "low").
    
    Typical example is a depolarizing curent injection step (or rectangular pulse)
    
    Parameters:
    ----------
    sig = neo.AnalogSignal with one channel (i.e. sig.shape[1]==1)
    
    Named parameters:
    -----------------
    box_size = length of smoothing boxcar window (default, 0)
    
    method: str, one of "state_levels" (default) or "kmeans"
    
    The following are used only when methos is "state_levels" and are passed 
    directly to signalprocessing.state_levels():
    
    adcres,
    adcrange,
    adcscale
    
    Returns:
    
    down: quantity array of high to low transitions times (in units of signal.times)
    up:  the same, for low to high transition times (in units of signal.times)
    inj: scalar quantity: the amplitude of the transition (in units of the signal)
    centroids: numpy array with shape (2,1): the centroid values i.e., the mean values
        of the two state levels
        
        
    """
    from scipy import cluster
    from scipy.signal import boxcar
    
    if not isinstance(sig, neo.AnalogSignal):
        raise TypeError("Expecting an analogsignal; got %s instead" % type(sig).__name__)
    
    if sig.ndim == 2 and sig.shape[1] > 1:
        raise ValueError("Expecting a signal with one channel, instead got %d" % sig.shape[1])
    
    box_size = kwargs.pop("box_size", 0)
    
    if box_size > 0:
        window = boxcar(box_size)/box_size
        sig_flt = convolve(sig, window)
        #sig_flt = convolve(np.squeeze(sig), window, mode="same")
        #sig_flt = neo.AnalogSignal(sig_flt[:,np.newaxis], units = sig.units, t_start = sig.t_start, sampling_rate = 1/sig.sampling_period)
    else:
        sig_flt = sig
        
    # 1) get transition times from injected current
    # use filtered signal, if available
    
    if method == "state_levels":
        levels = kwargs.pop("levels", 0.5)
        adcres = kwargs.pop("adcres", 15)
        adcrange = kwargs.pop("adcrange", 10)
        adcscale = kwargs.pop("adcrange", 1e3)
    
        centroids = sigp.state_levels(sig_flt.magnitude, levels = levels, 
                                    adcres = adcres, 
                                    adcrange = adcrange, 
                                    adcscale = adcscale)
        
        #centroids = sigp.state_levels(sig_flt.magnitude, levels = 0.5, 
                                    #adcres = adcres, 
                                    #adcrange = adcrange, 
                                    #adcscale = adcscale)
        
        
        centroids = np.array(centroids).T[:,np.newaxis]
        
    else:
        centroids, distortion = cluster.vq.kmeans(sig_flt, 2)
        centroids = np.sort(centroids, axis=0)
    
    #print(centroids)
    
    if len(centroids) == 0:
        return None, None, None, None, None
    
    label, dst = cluster.vq.vq(sig, centroids) # use un-filtered signal here
    edlabel = np.ediff1d(label, to_begin=0)
    
    down = sig.times[np.where(edlabel == -1)]
    
    up  = sig.times[np.where(edlabel == 1)]

    # NOTE: 2017-08-31 23:04:26 FYI: depolarizing = down > up 
    # in current-clamp, a depolarizing current injection is an outward current 
    # which therefore goes up BEFORE it goes back down, hence down is later than
    # up 
    
    # the step amplitude
    #amplitude = np.diff(centroids.ravel()) * sig.units
    amplitude = np.diff(centroids.flatten()) * sig.units
    
    return down, up, amplitude, centroids, label

@safeWrapper
def resample_pchip(sig, new_sampling_period, old_sampling_period = 1):
    """Resample a signal using a piecewise cubic Hermite interpolating polynomial.
    
    Resampling is calculated using scipy.interpolate.PchipInterpolator, along the
    0th axis.
    
    Parameters:
    -----------
    
    sig: numpy ndarray, python Quantity array or numpy array subclass which has 
        the attribute "sampling_period"
    
    new_sampling_period: float scalar
        The desired sampling period after resampling
        
    old_sampling_period: float scalar or None (default)
        Must be specified when sig is a generic numpy ndarray or Quantity array.
        
    Returns:
    --------
    
    ret: same type as sig
        A version of the signal resampled along 0th axis:
        
        * upsampled if new_sampling_period < old_sampling_period
        
        * downsampled if new_sampling_period > old_sampling_period
        
    When new_sampling_period == old_sampling_period, returns a reference to the
        signal (no resampling is performed and no data is copied).
        
        CAUTION: In this case the result is a REFERENCE to the signal, and 
                 therefore, any methods that modify the result in place will 
                 also modify the original signal!
    
    """
    # for upsampling this will introduce np.nan at the end
    # we replace these values wihtt he last signal sample value
    from scipy.interpolate import PchipInterpolator as pchip
    
    from . import datatypes as dt
    
    if isinstance(sig, (neo.AnalogSignal, DataSignal)):
        if isinstance(new_sampling_period, pq.Quantity):
            if not units_convertible(new_sampling_period, sig.sampling_period):
                raise TypeError("new sampling period units (%s) are incompatible with those of the signal's sampling period (%s)" % (new_sampling_period.units, sig.sampling_period.units))
            
            new_sampling_period.rescale(sig.sampling_period.units)
            
        else:
            new_sampling_period *= sig.sampling_period.units
    
        if sig.sampling_period > new_sampling_period:
            scale = sig.sampling_period / new_sampling_period
            new_axis_len = int(np.floor(len(sig) * scale))
            descr = "Upsampled"
            
        elif sig.sampling_period < new_sampling_period:
            scale = new_sampling_period / sig.sampling_period
            new_axis_len = int(np.floor(len(sig) // scale))
            descr = "Downsampled"
            
        else: # no resampling required; return reference to signal
            return sig
        
        new_times, new_step = np.linspace(sig.t_start.magnitude, sig.t_stop.magnitude, 
                                          num=new_axis_len, retstep=True, endpoint=False)
        
        #print("ephys.resample_pchip new_step", new_step, "new_sampling_period", new_sampling_period)
        
        assert(np.isclose(new_step, float(new_sampling_period.magnitude)))
        
        interpolator = pchip(sig.times.magnitude.flatten(), sig.magnitude.flatten(), 
                             axis=0, extrapolate=False)
        
        new_sig = interpolator(new_times)
        
        new_sig[np.isnan(new_sig)] = sig[-1,...]
        
        ret = sig.__class__(new_sig, units=sig.units,
                            t_start = new_times[0]*sig.times.units,
                            sampling_period=new_sampling_period,
                            name = sig.name,
                            description="%s %s %d-fold" % (sig.name, descr, scale))
        
        ret.annotations.update(sig.annotations)
    
        return ret
    
    else:
        if old_sampling_period is None:
            raise ValueError("When signal is a generic array the old sampling period must be specified")
        
        if isinstance(old_sampling_period, pq.Quantity):
            old_sampling_period = old_sampling_period.magnitude
            
        if isinstance(new_sampling_period, pq.Quantity):
            new_sampling_period = new_sampling_period.magnitude
            
        if old_sampling_period > new_sampling_period:
            scale = int(old_sampling_period / new_sampling_period)
            new_axis_len = sig.shape[0] * scale
            
        elif old_sampling_period < new_sampling_period:
            scale = int(new_sampling_period / old_sampling_period)
            new_axis_len = sig.shape[0] // scale
            
        else: # no resampling required; return reference to signal
            return sig
        
        t_start = 0
        
        t_stop = sig.shape[0] * old_sampling_period
        
        new_times, new_step = np.linspace(sig.t_start.magnitude, sig.t_stop.magnitude, 
                                          num=new_axis_len, retstep=True, endpoint=False)
        
        assert(np.isclose(new_step,float(new_sampling_period.magnitude)))
        
        interpolator = pchip(sig.times.magnitude.flatten(), sig.magnitude.flatten(), 
                             axis=0, extrapolate=False)
        
        ret = interpolator(new_times)
        
        ret[np.isnan(ret)] = sig[-1, ...]
        
        return ret

@safeWrapper
def diff(sig, n=1, axis=-1, prepend=False, append=True):
    """Calculates the n-th discrete difference along the given axis.
    
    Calls numpy.diff() under the hood.
    
    Parameters:
    ----------
    sig: numpy.array or subclass
        NOTE: singleton dimensions will be squeezed out
    
    Named parameters:
    -----------------
    These are passed directly to numpy.diff(). 
    The numpy.diff() documentation is replicated below highlighting any differences.
    
    n: int, optional
        The number of times values are differenced. 
        If zero the input is returned as is.
        
        Default is 1 (one)
    
    prepend, append: None or array-like, or bool
        Values to prepend/append to sig along the axis PRIOR to performing the 
        difference!
        
        NOTE:   When booleans, a value of True means that prepend or append will
        take, respectively, the first or last signal values along difference axis.
        
                A value of False is equivalent to None.
                
        NOTE:   "prepend" has default False; "append" has default True
        
    
    """
    if not isinstance(axis, int):
        raise TypeError("Axis expected to be an int; got %s instead" % type(axis).__name__)
    
    # first, squeeze out the signal's sigleton dimensions
    sig_data = np.array(sig).squeeze() # also copies the data; also we can use plain arrays
    #sig_data = sig.magnitude.squeeze() # also copies the data
    
    if isinstance(append, bool):
        if append:
            append_ndx = [slice(k) for k in sig_data.shape]
            append_ndx[axis] = -1
            
            append_shape = [slice(k) for k in sig_data.shape]
            append_shape[axis] = np.newaxis
            
            append = sig_data[tuple(append_ndx)][tuple(append_shape)]
            
        else:
            append = None
            
    if isinstance(prepend, bool):
        if prepend:
            prepend_ndx = [slice(k) for k in sig_data.shape]
            prepend_ndx[axis] = 0
            
            prepend_shape = [slice(k) for k in sig_data.shape]
            prepend_shape[axis] = np.newaxis
            
            prepend = sig_data[tuple(prepend_ndx)][tuple(prepend_shape)]
            
        else:
            prepend = None
            
    diffsig = np.diff(sig_data, n = n, axis = axis, prepend=prepend, append=append)
    
    ret = neo.AnalogSignal(diffsig, 
                           units = sig.units/(sig.times.units ** n),
                           t_start = 0 * sig.times.units,
                           sampling_rate = sig.sampling_rate,
                           name = sig.name,
                           description = "%dth order difference of %s" % (n, sig.name))
    
    ret.annotations.update(sig.annotations)
    
    return ret

@safeWrapper
def gradient(sig:[neo.AnalogSignal, DataSignal, np.ndarray], n:int=1, axis:int=0):
    """ First order gradient through central differences.
    
    Parameters:
    ----------
    
    sig: numpy.array or subclass
        The signal; can have at most 2 dimensions.
        When sig.shape[1] > 1, the gradient is calculated across the specified axis
    
    n: int; default is 1 (one)
        The spacing of the gradient (see numpy.gradient() for details)
    
    axis: int; default is 0 (zero)
        The axis along which the gradient is calculated;
        Can be -1 (all axes), 0, or 1.
        
        TODO/FIXME 2019-04-27 10:07:26: 
        At this time the function only supports axis = 0
        
    Returns:
    -------
    
    ret: neo.AnalogSignal or DataSignal, according to the type of "sig".
    
    
    """
    diffsig = np.array(sig) # for a neo.AnalogSignal this also copies the signal's magnitude
    
    if diffsig.ndim == 2:
        for k in range(diffsig.shape[1]):
            diffsig[:,k] = np.gradient(diffsig[:,k], n, axis=0)
            
        diffsig /= (n * sig.sampling_period.magnitude)
            
    elif diffsig.ndim == 1:
        diffsig = np.gradient(diffsig, n, axis=0)
        diffsig /= (n * sig.sampling_period.magnitude)
            
    else:
        raise TypeError("'sig' has too many dimensions (%d); expecting 1 or 2" % diffsig.ndim)
        
    if isinstance(sig, DataSignal):
        ret = DataSignal(diffsig, 
                            units = sig.units / sig.times.units, 
                            t_start = sig.t_start, 
                            sampling_period = sig.sampling_period, 
                            name = sig.name,
                            description = "Gradient of %s over %d samples along axis %d" % (sig.name, n, axis))
 
    else:
        ret = neo.AnalogSignal(diffsig, 
                            units = sig.units / sig.times.units, 
                            t_start = sig.t_start, 
                            sampling_period = sig.sampling_period, 
                            name = sig.name,
                            description = "Gradient of %s over %d samples along axis %d" % (sig.name, n, axis))
 
    ret.annotations.update(sig.annotations)
    
    return ret
    
@safeWrapper
def ediff1d(sig:[neo.AnalogSignal, DataSignal, np.ndarray], to_end:numbers.Number=0, to_begin:[numbers.Number, type(None)]=None):
    """Differentiates each channel of an analogsignal with respect to its time basis.
    
    Parameters:
    -----------
    
    sig: neo.AnalogSignal, numpy.array, or Quantity array
    
    
    Named parameters (see numpy.ediff1d):
    -------------------------------------
    Passed directly to numpy.ediff1d:
    
    to_end: scalar float, or 0 (default) NOTE: for numpy.ediff1d, the default is None
    
    to_begin: scalar float, or None (default)
    
    Returns:
    --------
    DataSignal or neo.AnalogSignal, according to the type of "sig"
    
    """
    
    diffsig = np.array(sig) # for a neo.AnalogSignal this also copies the signal's magnitude
    
    if diffsig.ndim == 2:
        for k in range(diffsig.shape[1]):
            diffsig[:,k] = np.ediff1d(diffsig[:,k], to_end=to_end, to_begin=to_begin)# to_end = to_end, to_begin=to_begin)
            
    elif diffsig.ndim == 1:
        diffsig = np.ediff1d(diffsig, to_end=to_end, to_begin=to_begin)
            
    else:
        raise TypeError("'sig' has too many dimensions (%d); expecting 1 or 2" % diffsig.ndim)
        
    diffsig /= sig.sampling_period.magnitude
    
    if isinstance(sig, DataSignal):
        ret = DataSignal(diffsig, units = sig.units / sig.times.units, 
                            t_start = sig.t_start, 
                            sampling_period = sig.sampling_period, 
                            name = sig.name,
                            description = "First order forward difference of %s" % sig.name)
    
        
    else:
        ret = neo.AnalogSignal(diffsig, units = sig.units / sig.times.units, 
                            t_start = sig.t_start, 
                            sampling_period = sig.sampling_period, 
                            name = sig.name,
                            description = "First order forward difference of %s" % sig.name)
    
    ret.annotations.update(sig.annotations)
    
    return ret

@safeWrapper
def forward_difference(sig:[neo.AnalogSignal, DataSignal, np.ndarray], n:int=1, to_end:numbers.Number=0, to_begin:[numbers.Number, type(None)]=None):
    """Calculates the forward difference along the time axis.
    
    Parameters:
    -----------
    
    sig: neo.AnalogSignal, numpy.array, or Quantity array
    
    
    Named parameters (see numpy.ediff1d):
    -------------------------------------
    
    n: int;
        number of samples in the difference.
        
        Must satisfy 0 <= n < len(sig) -2
        
        When n=0 the function returns a reference to the signal.
        
        When n=1 (the default), the function calls np.ediff1d() on the signal's 
            magnitude and the result is divided by signals sampling period
        
        When n > 1 the function calculates the forward difference 
            
            (sig[n:] - sig[:-n]) / (n * sampling_rate)
            
        Values of n > 2 not really meaningful.
            
    to_end: scalar float, or 0 (default) NOTE: for numpy.ediff1d, the default is None
    
    to_begin: scalar float, or None (default)
    
    Returns:
    --------
    DataSignal or neo.AnalogSignal, according to the type of "sig"
    
    """
    
    def __n_diff__(ary, n, to_b, to_e):
        dsig = ary[n:] - ary[:-n]
        
        shp = [s for s in ary.shape]
        
        if to_end is not None:
            if to_begin is None:
                shp[0] = n
                dsig = np.append(dsig, np.full(tuple(shp), to_e), axis=0)
                
            else:
                to_start = n//2
                to_stop = n - to_start
                
                shp[0] = to_start
                dsig = np.insert(dsig, np.full(tuple(shp), to_b), axis=0)
                
                shp[0] = to_stop
                dsig = np.append(dsig, np.full(tuple(shp), to_e), axis=0)
                
        else:
            if to_end is None:
                shp[0] = n
                dsig = np.insert(dsig, np.full(tuple(shp), to_b), axis=0)
                
            else:
                to_start = n//2
                to_stop = n - to_start
                
                shp[0] = to_start
                dsig = np.insert(dsig, np.full(tuple(shp), to_b), axis=0)
                
                shp[0] = to_stop
                dsig = np.append(dsig, np.full(tuple(shp), to_e), axis=0)
                
        return dsig
        
    
    if not isinstance(n, int):
        raise TypeError("'n' expected to be an int; got %s instead" % type(n).__name__)
    
    if n < 0: 
        raise ValueError("'n' must be >= 0; got %d instead" % n)
    
    diffsig = np.array(sig) # for a neo.AnalogSignal this also copies the signal's magnitude
    
    if diffsig.ndim == 2:
        if n >= diffsig.shape[0]:
            raise ValueError("'n' is too large (%d); should be n < %d" % (n, diffsig.shape[0]))
        
        if n == 0:
            return sig
        
        elif n == 1:
            for k in range(diffsig.shape[1]):
                diffsig[:,k] = np.ediff1d(diffsig[:,k], to_end=to_end, to_begin=to_begin)# to_end = to_end, to_begin=to_begin)
                
            diffsig /= sig.sampling_period.magnitude
            
        else:
            for k in range(diffsig.shape[1]):
                diffsig[:,k] = __n_diff__(diffsig[:,k], n=n, to_e=to_end, to_b=to_begin)# to_end = to_end, to_begin=to_begin)
            
            diffsig /= (n * sig.sampling_period.magnitude)
            
    elif diffsig.ndim == 1:
        if n >= len(diffsig):
            raise ValueError("'n' is too large (%d); should be < %d" % (n, len(diffsig)))
        
        if n == 0:
            return sig
        
        elif n == 1:
            diffsig = __n_diff__(diffsig, n=n, to_e = to_end, to_b = to_begin)
            #diffsig = np.ediff1d(diffsig, to_end=to_end, to_begin=to_begin)
            diffsig /= sig.sampling_period.magnitude
            
        else:
                    
            diffsig /= (n * sig.sampling_period.magnitude)
            
    else:
        raise TypeError("'sig' has too many dimensions (%d); expecting 1 or 2" % diffsig.ndim)
        
        
    if isinstance(sig, DataSignal):
        ret = DataSignal(diffsig, units = sig.units / sig.times.units, 
                            t_start = sig.t_start, 
                            sampling_period = sig.sampling_period, 
                            name = "%s_diff(1)" % sig.name,
                            description = "Forward difference (%dth order) of %s" % (n, sig.name))
 
    else:
        ret = neo.AnalogSignal(diffsig, units = sig.units / sig.times.units, 
                            t_start = sig.t_start, 
                            sampling_period = sig.sampling_period, 
                            name = "%s_diff(1)" % sig.name,
                            description = "Forward difference (%dth order) of %s" % (n, sig.name))
 
    ret.annotations.update(sig.annotations)
    
    return ret

def root_mean_square(x, axis = None):
    """ Computes the RMS of a signal.
    
    Positional parameters
    =====================
    x = neo.AnalogSignal, neo.IrregularlySampledSignal, or datatypes.DataSignal
    
    Named parameters
    ================
    
    axis: None (defult), or a scalar int, or a sequence of int: index of the axis,
            in the interval [0, x.ndim), or None (default)
            
            When a sequence of int, the RMS will be calculated across all the
            specified axes
    
        When None (default) the RMS is calculated for the flattened signal array.
        
        This argument is passed on to numpy.mean
        
    Returns: a scalar float
    RMS = sqrt(mean(x^2))
    
    """
    from . import datatypes as dt
    
    if not isinstance(x, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal)):
        raise TypeError("Expecting a neo.AnalogSignal, neo.IrregularlySampledSignal, or a datatypes.DataSignal; got %s instead" % type(x).__name__)
    
    if not isinstance(axis, (int, tuple, list, type(None))):
        raise TypeError("axis expected to be an int or None; got %s instead" % type(axis).__name__)
    
    if isinstance(axis, (tuple, list)):
        if not all([isinstance(a, int) for a in axis]):
            raise TypeError("Axis nindices must all be integers")
        
        if any([a < 0 or a > x.ndim for a in axis]):
            raise ValueError("Axis indices must be inthe interval [0, %d)" % x.ndim)
    
    if isinstance(axis, int):
        if axis < 0 or axis >= x.ndim:
            raise ValueError("Invalid axis index; expecting value between 0 and %d ; got %d instead" % (x.ndim, axis))
        
    return np.sqrt(np.mean(np.abs(x), axis=axis))
    
def signal_to_noise(x, axis=None, ddof=None, db=True):
    """Calculates SNR for the given signal.
    
    Positional parameters:
    =====================
    x = neo.AnalogSignal, neo.IrregularlySampledSignal, or datatypes.DataSignal
    
    Named parameters
    ================
    
    axis: None (defult), or a scalar int, or a sequence of int: index of the axis,
            in the interval [0, x.ndim), or None (default)
            
            When a sequence of int, the RMS will be calculated across all the
            specified axes
    
        When None (default) the RMS is calculated for the flattened signal array.
        
        This argument is passed on to numpy.mean and numpy.std
        
    ddof: None (default) or a scalar int: delta degrees of freedom
    
        When None, it sill be calculated from the size of x along the specified axes
        
        ddof is passed onto numpy.std (see numpy.std for details)
        
    db: boolean, default is True
        When True, the result is expressed in decibel (10*log10(...))
        
    """
    from . import datatypes as dt

    if not isinstance(x, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal)):
        raise TypeError("Expecting a neo.AnalogSignal, neo.IrregularlySampledSignal, or a datatypes.DataSignal; got %s instead" % type(x).__name__)
    
    if not isinstance(axis, (int, tuple, list, type(None))):
        raise TypeError("axis expected to be an int or None; got %s instead" % type(axis).__name__)
    
    if isinstance(axis, (tuple, list)):
        if not all([isinstance(a, int) for a in axis]):
            raise TypeError("Axis nindices must all be integers")
        
        if any([a < 0 or a > x.ndim for a in axis]):
            raise ValueError("Axis indices must be inthe interval [0, %d)" % x.ndim)
    
    if isinstance(axis, int):
        if axis < 0 or axis >= x.ndim:
            raise ValueError("Invalid axis index; expecting value between 0 and %d ; got %d instead" % (x.ndim, axis))
        
    if not isinstance(ddof, (int, type(None))):
        raise TypeError("ddof expected to be an int or None; got %sinstead" % ype(ddof).__name__)
    
    if ddof is None:
        if axis is None:
            ddof = 1
            
        elif isinstance(axis, int):
            ddof = 1
            
        else:
            ddof = len(axis)
            
    else:
        if ddof < 0:
            raise ValueError("ddof must be >= 0; got %s instead" % ddof)
        
        
    rms = root_mean_square(x, axis=axis)
    
    std = np.std(x, axis=axis, ddof=ddof)
    
    ret = rms/std
    
    if db:
        return np.log10(ret.magnitude.flatten()) * 20 
    
    return ret
    
def generate_text_stimulus_file(spike_times, start, duration, sampling_frequency, spike_duration, spike_value, filename, atol=1e-12, rtol=1e-12, skipInvalidTimes=True, maxSweepDuration=None):
    
    spike_trace = generate_spike_trace(spike_times, start, duration, sampling_frequency, 
                         spike_duration, spike_value, asNeoSignal=False)
    
    np.savetxt(filename, spike_trace)
    
def generate_ripple_trace(ripple_times, start, duration, sampling_frequency, spike_duration=0.001, spike_value=5000, spike_count=5, spike_isi=0.01, filename=None, atol=1e-12, rtol=1e-12, skipInvalidTimes=True):
    """Similar as generate_spike_trace and generate_text_stimulus_file combined.
    
    However, ripple times are the t_start values for ripple events. In turn,
    a ripple event if generated as a short burst of spikes containing 
    spike_count spikes, with spike_isi interval, spike_duration and spike_value.
    
    Positional parameters:
    =====================
    ripple_times: np.array (column vector) of ripple event timings (dimensionless,
                            but values are expected to time in s)
                            
    start: sweep start (dimensonless scalar representing the sweep start time in s)
    
    duration: sweep duration (dimensionless scalar, representing the duration of the sweep in s)
    
    sampling_frequency: dimensionless scalar representing the sampling frequency of the sweep in Hz
    
    Named parameters:
    =================
    spike_duration: float scalar: duration of ONE spike in the ripple-generating burst
        default: 0.001 s
        
    spike_value: float scalar (mV) default 5000
    
    spike_count: int scalar: number of spikes in a ripple event, default 5
    
    spike_isi: float scalar: the inter-spike interval in a ripple event
                (default if 0.01 s)
        
    filename = None (default) or a str (name of file where the trace will be written as ASCII)
    
    atol, rtol, skipInvalidTimes: see generate_spike_trace
    
    """
    
    def __inner_generate_ripples__(t_array, sp_times, t0, t_duration, s_freq, skip_invalid, atol_, rtol_):
        
        #print(sp_times)
        #print("t_duration", t_duration)
        
        ripple_trace = np.full_like(t_array, 0.0)
        
        order = int(np.log10(s_freq))
        
        pwr = eval("1e%d" % order)
        
        for k, ripple_time in enumerate(list(sp_times)):
            # generate spike train for one ripple
            #print("k, ripple_time", k, ripple_time)
            if skip_invalid:
                if ripple_time < start or ripple_time > (t0+t_duration):
                    continue
                
            clipped = int(ripple_time * pwr)/pwr
            
            ndx = np.where(np.isclose(t_array, clipped, atol=atol, rtol=rtol))[0]
            
            #print("ndx", ndx)
            
            if ndx.size == 1:
                for k_spike in range(spike_count):
                    
                    stride = int(spike_isi * s_freq) * k_spike
                        
                    spike_index = int(ndx + stride)
                    
                    ripple_trace[spike_index] = spike_value 
            
                    for k in range(int(spike_duration * s_freq)):
                        index = int(spike_index + k)
                        if index < ripple_trace.size:
                            ripple_trace[index] = spike_value
                        
                        
            elif ndx.size == 0:
                raise RuntimeError("spike time %g not found in the times array given start: %g, duration: %g, sampling frequency: %g and tolerances (atol: %g, rtol: %g). \nConsider increasing the tolerances or changing start and /or duration." \
                    % (spike_time, t0, t_duration, s_freq, atol_, rtol_))
            
            else:
                raise RuntimeError("ambiguous spike time found for %g, given start: %g, duration: %g, sampling frequency: %g and tolerances (atol: %g, rtol: %g). \nConsider decreasing the tolerances" \
                    % (spike_time, t0, t_duration, s_freq, atol_, rtol_))
            
        return ripple_trace
            
        
    
    if np.any(np.isnan(ripple_times)):
        raise ValueError("ripple times array cannot contain NaN values")
    
    if duration < np.max(ripple_times):
        warnings.warn("Duration (%s) is less than the maximum spike times (%s)" \
            % (float(duration), float(np.max(ripple_times))), RuntimeWarning)
        
    if start > np.min(ripple_times):
        warnings.warn("Start time (%s) is greater than the minimum spike time (%s)" \
            % (start, float(np.min(ripple_times))), RuntimeWarning)
        
    if spike_isi * sampling_frequency <= 1:
        raise ValueError("Either sampling frequency %g is too small or spike isi %g is too large")
    
    times_array = np.arange(start, start+duration, step=1/sampling_frequency)
    
    print("Generating trace ...")

       
    try:
        ret = __inner_generate_ripples__(times_array, ripple_times, 
                                        start, duration, 
                                        sampling_frequency,
                                        skipInvalidTimes, atol, rtol)
        
        if isinstance(filename, str):
            np.savetxt(filename, ret)
        
    except Exception as e:
        traceback.print_exc()
        return
        
    print("\n ... done")
    
    return ret
    
            
@safeWrapper
def generate_spike_trace(spike_times, start, duration, sampling_frequency, spike_duration=0.001, spike_value=5000, atol=1e-12, rtol=1e-12, skipInvalidTimes=True, maxSweepDuration=None, asNeoSignal=True, time_units = pq.s, spike_units=pq.mV, name="Spike trace", description="Synthetic spike trace", **annotations):
    """
    Converts a spike times array file to an AnalogSignal.
    
    A spike times array is a 1D array (column vector) that contains time "stamps"
    (in s)
    
    This kind of data can be loaded from a spike file (ASCII file) that lists the
    values in a single column (which in turn can be created in a spreadsheet program).
    
    To loadsuch a file use np.loadtxt(filename).
    
    Positional parameters:
    =====================
    spike_times: 1D array (float values) of spike times (in s) -- column vector
    start: scalar float = value of start time (in s);
    duration: scalar float = duration of the trace (in s);
    sampling_frequency: scalar float (in Hz)
    
    Named parameters:
    =================
    spike_duration: scalar float (in s), default is 0.001
    spike_value: scalar, default is 5000 (mV)

    atol, rtol: scalar floats: absolute  and relative tolerance, respectively, 
        for locating spike times in a linear time array (default for both: 1e-12)
        
        See np.isclose() for details
        
    skipInvalidTimes: bool (default True)
    
        If True, then invalid times (that fall outside the half-open interval 
        [start..start+duration) ) are skipped.
        
        When False, the function raises an error whenever an invalid time is found
        (see above).
        
    maxSweepDuration: scalar float (in s) or None (default is None)
        if given as a scalar float and the duration exceeds the sweep length
        then a list of analogsignals (one per sweep) will be produced having 
        a duration specified here
        
        
    asNeoSignal: bool (default, False) 
        When False, (the default) the function returns the spike trace as a 1D array
        (column vector).
        
        When True, the function returns the spike trace as a neo.AnalogSignal 
        object, in combination with the next named parameters
        
    NOTE: the following parameters are passed to the neo.AnalogSignal constructor
    and are used only when asNeoSignal is True:
        
    time_units: python Quantity (time, default is pq.s)
    
    spike_units: python Quantity (default is pq.mV)
    
    name: None, or str (default is "Spike trace")
    
    description: None or str (default is "Synthetic spike trace")
    
    Var-keyword parameters:
    ======================
    **annotations -- passed directly to the neo.AnalogSignal constructor
        
    """
    
    def __inner_trace_generate__(t_array, sp_times, t0, t_duration, s_freq, skip_invalid, atol_, rtol_):
        
        spike_trace = np.full_like(t_array, 0.0)
        
        order = int(np.log10(s_freq))
        
        pwr = eval("1e%d" % order)
        
        # take a slow for loop version otherwise we'd run out of memory pretty quickly
        # if we were to use numpy broadcasting here
        for k, spike_time in enumerate(sp_times):
            if skip_invalid:
                if spike_time < start or spike_time > (t0 + t_duration):
                    continue
                
            clipped = int(spike_time * pwr) / pwr
            
            ndx = np.where(np.isclose(t_array, clipped, atol=atol_, rtol=rtol_))[0]
            
            if ndx.size == 1:
                spike_trace[int(ndx)] = spike_value # this is just ONE sample
                
                # but the "spike" is a pulse waveform, so go ahead and generate the
                # rest of the waveform, too (for the spike_duration)
                for k in range(int(spike_duration * s_freq)):
                    index = int(ndx) + k
                    if index < spike_trace.size:
                        spike_trace[index] = spike_value
        
            elif ndx.size == 0:
                raise RuntimeError("spike time %g not found in the times array given start: %g, duration: %g, sampling frequency: %g and tolerances (atol: %g, rtol: %g). \nConsider increasing the tolerances or changing start and /or duration." \
                    % (spike_time, t0, t_duration, s_freq, atol_, rtol_))
            
            else:
                raise RuntimeError("ambiguous spike time found for %g, given start: %g, duration: %g, sampling frequency: %g and tolerances (atol: %g, rtol: %g). \nConsider decreasing the tolerances" \
                    % (spike_time, t0, t_duration, s_freq, atol_, rtol_))
            
        return spike_trace
    
    
    #resolution = 1/sampling_frequency
    
    #atol = 1e-12
    
    #rtol = 1e-12
    
    if np.any(np.isnan(spike_times)):
        raise ValueError("spike times array cannot contain NaN values")
    
    if duration < np.max(spike_times):
        warnings.warn("Duration (%s) is less than the maximum spike times (%s)" \
            % (float(duration), float(np.max(spike_times))), RuntimeWarning)
        
    if start > np.min(spike_times):
        warnings.warn("Start time (%s) is greater than the minimum spike time (%s)" \
            % (start, float(np.min(spike_times))), RuntimeWarning)
    
    times_array = np.arange(start, start+duration, step=1/sampling_frequency)
    
    if maxSweepDuration is not None:
        nSweeps = duration//maxSweepDuration
        if duration % maxSweepDuration > 0:
            nSweeps += 1
            
    else:
        nSweeps = 1
    
    result = list()
    
    if nSweeps > 1:
        print("Generating %d traces ..." % nSweeps)

        for k in range(nSweeps):
            start_time = float(k * maxSweepDuration)
            stop_time = float((k+1) * maxSweepDuration)
            
            times_sub_array = times_array[(times_array >= start_time) & (times_array < stop_time)]
            spike_sub_array = spike_times[(spike_times >= start_time) & (spike_times < stop_time)]
            
            try:
                ret = __inner_trace_generate__(times_sub_array, spike_sub_array, 
                                               start_time, maxSweepDuration, 
                                               sampling_frequency,
                                               skipInvalidTimes, atol, rtol)
                
                if asNeoSignal:
                    result.append(neo.AnalogSignal(ret, units=spike_units, 
                                                   t_start = start * time_units,
                                                   sampling_rate=sampling_frequency*pq.Hz,
                                                   name="%s_%d" % (name, k), 
                                                   description=description,
                                                   **annotations))
                    
                else:
                    result.append(ret)
                
            except Exception as e:
                traceback.print_exc()
                print( "In sub  array %d k")
                return
        
        
    
    else:
        print("Generating trace ...")
        
        try:
            ret = __inner_trace_generate__(times_array, spike_times, 
                                            start, duration, 
                                            sampling_frequency,
                                            skipInvalidTimes, atol, rtol)
            
            #print(ret.size)
            
            if asNeoSignal:
                result.append(neo.AnalogSignal(ret, units=spike_units, 
                                                t_start = start * time_units,
                                                sampling_rate=sampling_frequency*pq.Hz,
                                                name=name, 
                                                description=description,
                                                **annotations))
                
            else:
                result.append(ret)
            
        except Exception as e:
            traceback.print_exc()
            return
        
    print("\n ... done")
    
    if len(result) == 1:
        return result[0]
    
    else:
        return result

def sampling_rate_or_period(rate, period):
    """
    Get sampling rate period, or period from rate, or checks that they are
    the inverse of each other.
    
    Parameters:
    ----------
    rate, period: None or Quantity. They cannot both be None.
    
    Returns:
    -------
    
    rate as 1/period when rate is None
    
    period as 1/rate when period is None
    
    a bool when both rate and period are supplied (simply verifies they are the inverse of each other)
    
    see also neo.core.analogsignal._get_sampling_rate
    """
    if period is None:
        if rate is None:
            raise TypeError("Expecting either rate or period, at least")
        
        period = 1.0 /rate
        
        return period
        
    elif rate is None:
        if period is None:
            raise TypeError("Expecting either rate or period, at least")
            
        rate = 1.0 / period
        
        return rate
        
    else:
        return np.isclose(period, 1.0 / rate)
    
    if not hasattr(rate, "units"):
        raise TypeError("Sampling rate or period must have units")
    
    return rate

def segment_start(data:neo.Segment):
    """Returns the minimum of t_start for all signals and spiketrains in a segment.
    
    Avoids any events and epochs that fall outside the signals' time domain.
    
    NOTE: The segment's analogsignals and irregularlysampledsignals collections
    must be homogeneous (i.e., they MUST NOT contain mixtures of AnalogSignal 
    and DataSignal, or IrregularlySampledSignal and IrregularlySampledDataSignal)
    
    """
    
    return min([s.t_start for s in data.analogsignals] + 
               [s.t_start for s in data.spiketrains] +
               [min(s.times) for s in data.irregularlysampledsignals])
        

def set_relative_time_start(data, t = 0 * pq.s):
    """
    TODO: propagate to other members of a segment as well 
    (IrregularlySampledSignal, epochs, spike trains, etc)
    """
    from neo.core.spiketrainlist import SpikeTrainList
    if isinstance(data, neo.Block):
        for segment in data.segments:
            for isig in segment.irregularlysampledsignals:
                isig.times = isig.times-segment.analogsignals[0].t_start + t
                
            for signal in segment.analogsignals:
                signal.t_start = t
                
            try:
                new_epochs = list()
                
                for epoch in segment.epochs:
                    if epoch.times.size > 0:
                        new_times = epoch.times - epoch.times[0] + t
                        
                    else:
                        new_times = epoch.times
                        
                    new_epoch = neo.Epoch(new_times,
                                          durations = epoch.durations,
                                          labels = epoch.labels,
                                          units = epoch.units,
                                          name=epoch.name)
                    
                    new_epoch.annotations.update(epoch.annotations)
                    
                    new_epochs.append(new_epoch)
                    
                segment.epochs[:] = new_epochs
                    
                new_trains = list()
                
                for spiketrain in segment.spiketrains:
                    if spiketrain.times.size > 0:
                        new_times = spiketrain.times - spiketrain.times[0] + t
                        
                    else:
                        new_times = spiketrain.times
                        
                    new_spiketrain = neo.SpikeTrain(new_times, 
                                                    t_start = spiketrain.t_start - spiketrain.times[0] + t,
                                                    t_stop = spiketrain.t_stop - spiketrain.times[0] + t,
                                                    units = spiketrain.units,
                                                    waveforms = spiketrain.waveforms,
                                                    sampling_rate = spiketrain.sampling_rate,
                                                    name=spiketrain.name,
                                                    description=spiketrain.description)
                    
                    new_spiketrain.annotations.update(spiketrain.annotations)
                        
                    new_trains.append(spiketrain)
                        
                segment.spiketrains = SpikeTrainList(items=new_trains)
                    
                new_events = list()
                
                for event in segment.events:
                    new_times = event.times - event.times[0] + t if event.times.size > 0 else event.times
                    
                    if isinstance(event, TriggerEvent):
                        new_event = TriggerEvent(times = new_times,
                                                    labels = event.labels,
                                                    units = event.units,
                                                    name = event.name,
                                                    description = event.description,
                                                    event_type = event.event_type)
                    else:
                        new_event = neo.Event(times = new_times,
                                              labels = event.labels,
                                              units = event.units,
                                              name=event.name,
                                              description=event.description)
                        
                        new_event.annotations.update(event.annotations)
                        
                    new_events.append(new_event)

                segment.events[:] = new_events
            
            except Exception as e:
                traceback.print_exc()
                
    elif isinstance(data, (tuple, list)):
        if all([isinstance(x, neo.Segment) for x in data]):
            for s in data:
                for isig in s.irregularlysampledsignals:
                    isig.times = isig.times-segment.analogsignals[0].t_start + t
                    
                for signal in s.analogsignals:
                    signal.t_start = t
                    
                for epoch in s.epochs:
                    epoch.times = epoch.times - epoch.times[0] + t
                    
                for strain in s.spiketrains:
                    strain.times = strain.times - strain.times[0] + t
                    
                for event in s.events:
                    event.times = event.times - event.times[0] + t
                
        elif all([isinstance(x, (neo.AnalogSignal, DataSignal)) for x in data]):
            for s in data:
                s.t_start = t
                
        elif all([isinstance(x, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal))]):
            for s in data:
                s.times = s.times - s.times[0] + t
                
        elif all([isinstance(x, (neo.SpikeTrain, neo.Event, neo.Epoch))]):
            for s in data:
                s.times = s.times - s.times[0] + t
                    
                
    elif isinstance(data, neo.Segment):
        for isig in data.irregularlysampledsignals:
            isig.times = isig.times-data.analogsignals[0].t_start + t
            
        for signal in data.analogsignals:
            signal.t_start = t
            
        for epoch in data.epochs:
            epoch.times = epoch.times - epoch.times[0] + t
            
        for strain in data.spiketrains:
            strain.times = strain.times - strain.times[0] + t
            
        for event in data.events:
            event.times = event.times - event.times[0] + t
                
    elif isinstance(data, (neo.AnalogSignal, DataSignal)):
        data.t_start = t
        
    elif isinstance(data, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal)):
        data.times = data.times - data.times[0] + t
        
    elif isinstance(data, (neo.SpikeTrain, neo.Event, neo.Epoch)):
        data.times = data.times = data.times[0] + t
        
    else:
        raise TypeError("Expecting a neo.Block, neo.Segment, neo.AnalogSignal or datatypes.DataSignal; got %s instead" % type(data).__name__)
        
        
    return data

class ElectrophysiologyDataParser(object):
    """Encapsulate acquisition parameters and protocols for electrophysiology data
    
    Intended to provide a common denominator for data acquired with various 
        electrophysiology software vendors. 
        
    WARNING API under development (i.e. unstable)
    """
    def __init__(self):
        # possible values for self._data_source_:
        # "Axon", "CEDSignal", "CEDSpike", "Ephus", "NA", "unknown"
        # default: "unknown"
        self._data_source_ = "unknown"  
        self._acquisition_protocol_ = dict()
        self._acquisition_protocol_["trigger_protocol"] = TriggerProtocol()
        self._averaged_runs_ = False
        self._alternative_DAC_command_output_ = False
        self._alternative_digital_outputs_ = False
    
    def parse_data(self, data:neo.Block, metadata:dict=None):
        if hasattr(data, "annotations"):
            self._data_source_ = data.annotations.get("software", "unknown")
            if self._data_source_ == "Axon":
                self._parse_axon_data_(data, metadata)
                
            else:
                # TODO 2020-02-20 11:32:16
                # parse CEDSignal, CEDSpike, EPhus, unknown
                pass
            
    def _parse_axon_data_(self, data:neo.Block, metadata:dict=None):
        data_protocol = data.annotations.get("protocol", None)
        
        self._averaged_runs_ = data_protocol.get("lRunsPerTrial",1) > 1
        self._n_sweeps_ = data_protocol.get("lEpisodesPerRun",1)
        self._alternative_digital_outputs_ = data_protocol.get("nAlternativeDigitalOutputState", 0) == 1
        self._alternative_DAC_command_output_ = data_protocol.get("nAlternativeDACOutputState", 0) == 1
        
        
@safeWrapper
def parse_acquisition_metadata(data:neo.Block, configuration:[type(None), dict] = None):
    """Parses metadata from electrophysiology acquisition data.
    
    Tries to bring acquisition parameters and protocols from different
    software vendors under a common structure.
    
    NOTE: 2020-02-18 13:53:56
        Currently supports only data loaded from axon binary files (*.abf) 
    TODO: 2020-02-18 13:54:00 Support for:
    * axon text files (*.atf)
    * axon protocol files (*.pro)
    * CED Signal files (CFS)
    * CED Spike2 files (SON) -- see neo.io
    
    
    Parameters:
    ----------
    
    data: neo.Block loaded from an electrophysiology acquisition software
    
    configuration: dict or None (default): additional configuration data loaded
        from a configuration file alongside with the data acquisition file 
        
    
    
    Returns:
    --------
    A dictionary with fields detailing, to the extent possible, acquisition 
    protocols and parameters. 
    """
    
    if not isinstance(data, neo.Block):
        raise TypeError("Expecting a neo.Block; got %s instead" % type(data).__name__)
    
    if "software" in data.annotations:
        pass


def waveform_signal(extent, sampling_frequency, model_function, *args, **kwargs):
    """Generates a signal containing a synthetic waveform, as a column vector.
    
    Parameters:
    ===========
    extent              : float scalar, interpreted as having dimensionality of t or samples
                        the extent of the entire signal that contains the synthetic waveform
                        
                        This is either the duration (for time-varying signals) or
                        otherwise the extent of the natural domain of the signal
                        that the synthetic waveform is part of.
                        
                        NOTE: This is NOT the duration (or extent, otherwise) of the waveform
                        itself. The waveform is part of the signal
                        
    sampling_frequency  : float scalar, interpreted as having dimensionality of 1/t or 1/samples; must be > 0
                        sampling frequency of the signal containing the synthetic waveform
                        
    model_function      : one of the model functions in the models module or a wrapper of it
                        such that it has the following signature:
                        
                        y = func(x, parameters, **kwargs)
                        
                        where:
                            y is a numpy array (one column vector)
                            x is a numpy array (one column vector) with the definition domain of y
                            parameters: a sequence of funciton parameters
                            
                        The (possibly wrapped) model function generates a realization of
                        
                        y = f(x|parameters)
    
    Variadic parameters and keyword parameters:
    ===========================================
    *args,              : additional parameters to the model_function (the first 
                        parameter, "x" will be generated internally; see the 
                        documentation of the particular model_function for details) 
    
    **kwargs            : keyword parameters for the model function and those for
                        the constructor of neo.AnalogSignal or datatypes.DataSignal, 
                        used when asSignal is True (see below, for details)
                        
    Keyword parameters of special interest:
    
        asSignal        : boolean default False; when True, returns a neo.AnalogSignal
                        of datatypes.DataSignal according to the keyword parameter
                        "domain_units" (see below).
                        When False, returns a np.array (column vector).
                        
        domain_units    : Python UnitQuantity or Quantity; default is s.
                        When different from pq.s and asSignal is True, then the
                        function returns a datatypes.DataSignal; othwerise the 
                        function returns a neo.AnalogSignal unless asSignal is False
                        in which case it returns a numpy array
                        
        endpoint        : boolean, default True: whether to include the stop in the generated
                        function domain (a linear space, see numpy.linspace for detail)
                        
                        
    Returns:
    ========
    When asSignal is False (default):
    
        returns the tuple (x, y) containing two numpy arrays (each a column vector) 
            representing, respectively, the waveform (y) and its definition domain (x)
    
        ATTENTION NOTE the ORDER in the tuple: x, y
    
    When asSignal is True:
        
        when "domain_units" is present in kwargs and is NOT a time unit:
            returns a datatypes.DataSignal
                
        otherwise:
            returns a neo.AnalogSignal (domain units are s by default)
   
    """
    # TODO: contemplate using scipy.signal to generate AnalogSignal with waveforms
    
    import inspect
    
    if any([v <= 0 for v in (extent, sampling_frequency)]):
        raise ValueError("Both extent and sampling_frequency must be strictly positive")
        
    nSamples = int(extent * sampling_frequency)
    
    analogsignal_param_names_list = ("units", "dtype", "copy", "t_start", "sampling_rate", "sampling_period", "name", "file_origin", "description")
    
    datasignal_param_names_list = ("units", "dtype", "copy", "origin", "sampling_rate", "sampling_period", "name", "file_origin", "description")
    
    model_function_keyword_list = list()
    
    signal_keyword_params = dict()
    
    model_function_keyword_params = dict()
    
    annotation_keyword_params = dict()
    
    # NOTE: 2018-09-13 10:18:44
    # when asSignal is True:
    # if domain_units are specified and NOT time units, then return DataSignal
    # otherwise return AnalogSignal
    domain_units = kwargs.pop("domain_units", None)
    
    asSignal = kwargs.pop("asSignal", False)
    
    endpoint = kwargs.pop("endpoint", True)
    
    if domain_units is not None:
        if not isinstance(domain_units, (pq.UnitQuantity, pq.Quantity)):
            raise TypeError("When specified, domain_units must be a Python UnitQuantity or Quantity object; got %s instead" % type(domain_units).__name__)
        
        
        if check_time_units(domain_units):
            returnDataSignal = False
            
        else:
            returnDataSignal = True
    
    else:
        returnDataSignal = False
        
    if type(model_function).__name__ != "function":
        raise TypeError("model_function expected to be a function; got %s instead" % type(model_function).__name__)
    
    model_function_signature = inspect.signature(model_function)
    
    for param in model_function_signature.parameters.values():
        if param.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.VAR_KEYWORD) \
            and param.default is not param.empty:
                model_function_keyword_list.append(param.name) 
            
    
    for (key, value) in kwargs.items():
        if key in analogsignal_param_names_list:
            signal_keyword_params[key] = value
            
        elif key in datasignal_param_names_list:
            signal_keyword_params[key] = value
            
        elif key in model_function_keyword_list:
            model_function_keyword_params[key] = value
            
        else:
            annotation_keyword_params[key] = value
    
    
    #print("*args", args)
    x = np.linspace(0, extent, nSamples, endpoint=endpoint) # don't include endpoint
    
    
    y = model_function(x, *args, **model_function_keyword_params)
    
    if asSignal:
        signalkwargs = dict()
        signalkwargs.update(signal_keyword_params)
        signalkwargs.update(annotation_keyword_params)

        if returnDataSignal:
            origin = 0*domain_units
            return dt.DataSignal(y, origin=origin, **signalkwargs)
            
        else:
            return neo.AnalogSignal(y, **signalkwargs)
    
    return x, y
    
