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

SignalCursorTypes.vertical, 
or 
SignalCursorTypes.horizontal.

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

II. Synthesis of artificial signals and waveforms
=================================================
generate_ripple_trace
generate_spike_trace
waveform_signal

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
import pyabf
import matplotlib as mpl
# import pyqtgraph as pg
from gui.pyqtgraph_patch import pyqtgraph as pg
from PyQt5 import QtGui, QtCore
#### END 3rd party modules

#### BEGIN pict.core modules
from core.prog import safeWrapper
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
from core.datazone import DataZone
from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType, )
from core.triggerprotocols import TriggerProtocol

from core import datatypes as dt
from core.datatypes import TypeEnum
from core import workspacefunctions
from core import signalprocessing as sigp
from core import utilities
from core import neoutils
from core import quantities as spq
from core import pyabfbridge
from core.utilities import normalized_index
from core.neoutils import get_index_of_named_signal
from core.quantities import (units_convertible, check_time_units)

from gui.cursors import (SignalCursor, SignalCursorTypes)

#from .patchneo import neo


#### END pict.core modules


if __debug__:
    global __debug_count__

    __debug_count__ = 0
    
class ClampMode(TypeEnum):
    NoClamp=1           # i.e., voltage follower (I=0) e.g., ElectrodeMode.Field,
                        # but OK with other ElectrodeMode
    VoltageClamp=2      # these two should be
    CurrentClamp=4      # self-explanatory
    
    
class ElectrodeMode(TypeEnum):
    Field=1             # typically, associated with ClampMode.NoClamp; other ClampModes don't make sense
    WholeCellPatch=2    # can associate any ClampMode
    ExcisedPatch=4      # can associate any ClampMode although ClampMode.VoltageClamp makes more sense
    Sharp=8             # can associate any ClampMode although ClampMode.CurrentClamp makes more sense
    Tetrode=16          # these are really for 
    LinearArray=32      # local field potentials etc
    MultiElectrodeArray=64 # MEAs on a culture/slice?
    
    
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
    SignalCursorTypes.vertical, 
    SignalCursorTypes.horizontal). 
    
    SignalCursors can also be represented by tuples of cursor  "parameters" 
    (see below), although tuples and cursor objects cannot be mixed.
    
    Variadic parameters:
    --------------------
    *args: comma-separated list of EITHER:
    
        • SignalCursor objects - all of either 'vertical' or 'crosshair' type.
        
        • SignalCursor parameter tuples (2, 3 or 5 elements):
        
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
        
    zone: bool, default is False; only used when intervals is False
            When True, returns a DataZone; else returns a neo.Epoch
    
        
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
    # from gui.signalviewer import SignalCursor as SignalCursor

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
    
    zone = kwargsp.pop("zone", False)
    if not isinstance(zone, bool):
        raise TypeError("zone must be a boolean")
    
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
            if args[0].cursorType is SignalCursorTypes.horizontal:
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
            
        if zone or not check_time_units(units):
            klass = DataZone
        else:
            klass = neo.Epoch
        
        return klass(times=t, durations=d, labels=i, units=units, name=name)
    
def cursors2intervals(*args, **kwargs):
    """Calls cursors2epoch with intervals set to True
    
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
def epoch_reduce(func:types.FunctionType, 
                 signal: typing.Union[neo.AnalogSignal, DataSignal], 
                 epoch: typing.Union[neo.Epoch, tuple], 
                 channel: typing.Optional[int] = None):
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

def cursor_slice(signal: typing.Union[neo.AnalogSignal, DataSignal],
                  cursor: typing.Union[SignalCursor, tuple]) -> typing.Union[neo.AnalogSignal, DataSignal]:
    """Returns a slice of the signal corresponding to a cursor's window"""
    
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
        ret = signal.time_slice(t0,t1)
    
    return ret

def cursor_reduce(func:types.FunctionType, 
                  signal: typing.Union[neo.AnalogSignal, DataSignal], 
                  cursor: typing.Union[SignalCursor, tuple], 
                  channel: typing.Optional[int] = None):
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
    # from gui.signalviewer import SignalCursor as SignalCursor
    
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
        # ret = func(signal.time_slice(t0,t1), axis=0).flatten()
        ret = func(signal.time_slice(t0,t1), axis=0)
    
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
def cursor_argmin(signal: typing.Union[neo.AnalogSignal, DataSignal], 
                  cursor: typing.Union[tuple, SignalCursor], 
                  channel: typing.Optional[int] = None):
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
def cursor_maxmin(signal: typing.Union[neo.AnalogSignal, DataSignal], 
                  cursor: typing.Union[tuple, SignalCursor], 
                  channel: typing.Optional[int] = None):
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
def cursor_minmax(signal: typing.Union[neo.AnalogSignal, DataSignal], 
                  cursor: typing.Union[tuple, SignalCursor], 
                  channel: typing.Optional[int]=None):
    return cursor_reduce(sigp.minmax, signal, cursor, channel)

@safeWrapper
def cursor_argmaxmin(signal: typing.Union[neo.AnalogSignal, DataSignal], 
                     cursor: typing.Union[tuple, SignalCursor], 
                     channel: typing.Optional[int] = None):
    """The indices of signal maximum and minimum across the cursor's window.
    """
    return cursor_reduce(sigp.argmaxmin, signal, cursor, channel)

@safeWrapper
def cursor_argminmax(signal: typing.Union[neo.AnalogSignal, DataSignal],
                     cursor: typing.Union[tuple, SignalCursor], 
                     channel: typing.Optional[int]=None):
    return cursor_reduce(sigp.argminmax, signal, cursor, channel)

@safeWrapper
def cursor_average(signal: typing.Union[neo.AnalogSignal, DataSignal], 
                   cursor: typing.Union[tuple, SignalCursor], 
                   channel: typing.Optional[int]=None):
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
def cursor_value(signal:typing.Union[neo.AnalogSignal, DataSignal], 
                 cursor: typing.Union[float, SignalCursor, pq.Quantity, tuple], 
                 channel: typing.Optional[int] = None):
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
    # from gui.signalviewer import SignalCursor as SignalCursor
    
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
    # from gui.signalviewer import SignalCursor as SignalCursor

    # NOTE: specifying a channel doesn't make sense here because all
    # channels in the signal sharethe domain and have the same number of
    # samples
    if isinstance(cursor, float):
        t = cursor * signal.time.units
        
    elif isinstance(cursor, SignalCursor):
        if cursor.cursorType not in (SignalCursorTypes.vertical, SignalCursorTypes.crosshair):
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
def cursors_measure_in_segment(func, data, *cursors, 
                    segment_index: int = None, 
                    analog: typing.Optional[typing.Union[int, str]] = None, 
                    irregular: typing.Optional[typing.Union[int, str]] = None, 
                    **kwargs):
    """
    TODO/FIXME
    data: a neo.AnalogSignal or DataSignal
    """
    # from gui.signalviewer import SignalCursor as SignalCursor

    
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
        # iterate through segments # TODO 2023-06-12 23:17:33
        pass
    
    elif isinstance(data, (tuple, list)):
        if all([isinstance(s, (neo.AnalogSignal, DataSignal)) for s in data]):
            # treat as a segment's signal collection # TODO 2023-06-12 23:17:33
            pass
        
        elif all([isinstance(d, neo.Segment) for d in data]):
            # iterate through segments as for block # TODO 2023-06-12 23:17:33
            pass
            
        
    return func(data, *cursors, **kwargs)

    
@safeWrapper
def cursors_difference(signal: typing.Union[neo.AnalogSignal, DataSignal], 
                       cursor0: typing.Union[SignalCursor, tuple], 
                       cursor1: typing.Union[SignalCursor, tuple], 
                       channel: typing.Optional[int] = None) -> pq.Quantity:
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
    from gui.cursors import SignalCursor as SignalCursor

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
    
@safeWrapper
def cursors_chord_slope(signal: typing.Union[neo.AnalogSignal, DataSignal], 
                        cursor0: typing.Union[SignalCursor, tuple], 
                        cursor1: typing.Union[SignalCursor, tuple], 
                        channel: typing.Optional[int] = None):
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

def cursor_chord_slope(signal, cursor, channel=None):
    t0 = (cursor.x - cursor.xwindow/2) * signal.times.units
    t1 = (cursor.x + cursor.xwindow/2) * signal.times.units
    
    if t1 == t0:
        raise ValueError(f"Cursor xwindow is 0")
    
    v0, v1 = list(map(lambda x: neoutils.get_sample_at_domain_value(signal, x), (t0, t1)))
    
    return ((v1-v0) / (t1-t0)).simplified
    
    
    
    
@safeWrapper
def epoch2cursors(epoch: neo.Epoch, 
                  axis: typing.Optional[typing.Union[pg.PlotItem, pg.GraphicsScene]] = None, 
                  **kwargs):
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
    
    See the documentation of gui.cursors.SignalCursor.__init__ for details.
    
    signal_viewer:SignalViewer instance, or None (the default)
        When given, the cursors will also be registered with the signal viewer
        instance that owns the axis.
    
        Prerequisite: the axis must be owned by the signal viewer instance.
    
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
    from gui.cursors import SignalCursor as SignalCursor
    from gui.signalviewer import SignalViewer

    keep_units = kwargs.pop("keep_units", False)
    if not isinstance(keep_units, bool):
        keep_units = False
        
    if keep_units:
        ret = [(t + d/2., d, l) for (t, d, l) in zip(epoch.times, epoch.durations, epoch.labels)]
        
    else:
        ret = [(t + d/2., d, l) for (t, d, l) in zip(epoch.times.magnitude, epoch.durations.magnitude, epoch.labels)]
        
    signal_viewer = kwargs.pop("signal_viewer", None)
    
    if isinstance(axis, (pg.PlotItem, pg.GraphicsScene)):
        # NOTE: 2020-03-10 18:23:03
        # cursor constructor accepts python Quantity objects for its numeric
        # parameters x, y, xwindow, ywindow, xBounds and yBounds
        # NOTE: below, parent MUST be set to axis, else there will be duplicate
        # cursor lines when registering with signal viewer instance
        cursors = [SignalCursor(axis, x=t, xwindow=d,
                                cursor_type=SignalCursorTypes.vertical,
                                cursorID=l, parent=axis) for (t,d,l) in ret]
        
        if isinstance(signal_viewer, SignalViewer):
            if isinstance(axis, pg.PlotItem):
                if axis not in signal_viewer.axes:
                    return cursors
                
            elif isinstance(axis, pg.GraphicsScene):
                if axis is not signal_viewer.signalsLayout.scene():
                    return cursors
                
            cursorDict = signal_viewer.getDataCursors(SignalCursorTypes.vertical)
            cursorPen = QtGui.QPen(QtGui.QColor(signal_viewer.cursorColors["vertical"]), 1, QtCore.Qt.SolidLine)
            cursorPen.setCosmetic(True)
            hoverPen = QtGui.QPen(QtGui.QColor(signal_viewer.cursorHoverColor), 1, QtCore.Qt.SolidLine)
            hoverPen.setCosmetic(True)
            linkedPen = QtGui.QPen(QtGui.QColor(signal_viewer.linkedCursorColors["vertical"]), 1, QtCore.Qt.SolidLine)
            linkedPen.setCosmetic(True)
            if isinstance(axis, pg.PlotItem):
                cursorPrecision = signal_viewer.getAxis_xDataPrecision(axis)
            elif isinstance(axis, pg.GraphicsScene):
                pi_precisions = [signal_viewer.getAxis_xDataPrecision(ax) for ax in signal_viewer.plotItems]
                cursorPrecision = min(pi_precisions)
                
            else: 
                cursorPrecision = None
               
            for c in cursors:
                signal_viewer.registerCursor(c, pen=cursorPen, hoverPen=hoverPen,
                                             linkedPen=linkedPen,
                                             precision=cursorPrecision,
                                             showValue = signal_viewer.cursorsShowValue)
        
        return cursors
    
    return ret

@safeWrapper
def intervals2cursors(*args, **kwargs):
    """Construct a neo.Epoch from a sequence of interval tuples or triplets.
    
    Variadic parameters:
    --------------------
    triplets (t0,t1,label), or a sequence of tuples or triplets
    each specifying an interval
    
    """
    from gui.cursors import SignalCursor
    signal_viewer = kwargs.pop("signal_viewer", None)

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
                                    cursor_type=SignalCursorTypes.vertical) for p in xwl]
                
        if isinstance(signal_viewer, SignalViewer):
            if isinstance(axis, pg.PlotItem):
                if axis not in signal_viewer.axes:
                    return cursors
                
            elif isinstance(axis, pg.GraphicsScene):
                if axis is not signal_viewer.signalsLayout.scene():
                    return cursors
                
            cursorDict = signal_viewer.getDataCursors(SignalCursorTypes.vertical)
            cursorPen = QtGui.QPen(QtGui.QColor(signal_viewer.cursorColors["vertical"]), 1, QtCore.Qt.SolidLine)
            cursorPen.setCosmetic(True)
            hoverPen = QtGui.QPen(QtGui.QColor(signal_viewer.cursorHoverColor), 1, QtCore.Qt.SolidLine)
            hoverPen.setCosmetic(True)
            linkedPen = QtGui.QPen(QtGui.QColor(signal_viewer.linkedCursorColors["vertical"]), 1, QtCore.Qt.SolidLine)
            linkedPen.setCosmetic(True)
            if isinstance(axis, pg.PlotItem):
                cursorPrecision = signal_viewer.getAxis_xDataPrecision(axis)
            elif isinstance(axis, pg.GraphicsScene):
                pi_precisions = [signal_viewer.getAxis_xDataPrecision(ax) for ax in signal_viewer.plotItems]
                cursorPrecision = min(pi_precisions)
                
            else: 
                cursorPrecision = None
               
            for c in cursors:
                signal_viewer.registerCursor(c, pen=cursorPen, hoverPen=hoverPen,
                                             linkedPen=linkedPen,
                                             precision=cursorPrecision,
                                             showValue = signal_viewer.cursorsShowValue)
        
            return cursors
        
        return xwl

@safeWrapper
def epoch_average(signal: typing.Union[neo.AnalogSignal, DataSignal],
                  epoch: neo.Epoch, 
                  intervals: typing.Optional[typing.Union[int, str, typing.Sequence[int], typing.Sequence[str], range, slice]] = None,
                  channel: typing.Optional[int] = None):
    """Signal average across an epoch's intervals.
    
    Parameters:
    -----------
    signal: neo.AnalogSignal or datatypes.DataSignal
    
    epoch: neo.Epoch
    
    intervals: optional - when present, specified which epoch intervals to use
        This can be:
        • int (interval index)
        • str (interval name)
        • sequence of int (interval indices)
        • sequence of str (interval names)
        • a range
        • a slice
    
    channel: int or None (default)
    
    Returns:
    --------
    
    A list of python Quantity objects with as many elements as there
    are times, durations pairs (i.e., intervals) in the epoch.
    
    For multi-channel signals, the Quantity are arrays of size that equals the
    number of channels.
    
    """
    if intervals is None:
        t0 = epoch.times
        t1 = epoch.times + epoch.durations
        ret = [signal.time_slice(t0_, t1_).mean(axis=0) for (t0_, t1_) in zip(t0,t1)]
        
    elif isinstance(intervals, (int, str)):
        t0, t1 = neoutils.get_epoch_interval(epoch, intervals, duration=False)
        ret = [signal.time_slice(t0, t1).mean(axis=0)]
        
    elif isinstance(intervals, (tuple, list)) and all(isinstance(i, (int, str)) for i in intervals):
       t0t1 = [neoutils.get_epoch_interval(epoch, i, duration=False) for i in intervals] 
       ret = [signal.time_slice(t0, t1).mean(axis=0) for (t0,t1) in t0t1]
        
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
    
def generate_text_stimulus_file(spike_times, start, duration, sampling_frequency, spike_duration, spike_value, filename, atol=1e-12, rtol=1e-12, skipInvalidTimes=True, maxSweepDuration=None):
    """Generates an axon text file ("*.atf") for use as external waveform.
    
    The result is useful for Clampex protocols in sweep mode, using external 
    waveforms.
    
    """
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


class ElectrophysiologyProtocol(object):
    """Electrophysiology data acquisition protocols
    
    Intended to provide a common denominator for data acquired with various 
        electrophysiology software vendors. 
        
    WARNING DO NOT USE YET - API under development (i.e. unstable) TODO
    """
    # TODO/FIXME see if pyabf can be used
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
        
    def _parse_ced_data_(self, data:object):
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
    
def event_amplitude_at_cursors(signal:typing.Union[neo.AnalogSignal, DataSignal], 
                               func:typing.Callable,
                               cursors:typing.Union[typing.Sequence[tuple], typing.Sequence[SignalCursor]],
                               channel:typing.Optional[int] = None, 
                               ):
    """
    Measures the amplitude of events(s) using "cursors".
    Use this for evoked events e.g. EPSC or IPSC
    
    Parameters:
    ----------
    
    signal: a signal object where the event amplitude is measured
    
    func: callable with the signature 

        f(signal, cursor, channel) -> scalar (numeric or python Quantity)
    
        the function to be applied to each cursor  See, e.g., cursors_measure(…)
    
    cursors: a sequence of SignalCursor objects (cursorType vertical) or notional 
        cursors: tuples of (t, w) with the time coordinate and x window size.
    
        The sequence must contain an EVEN number of "cursors" (2 × the number of
        events in the signal) such that the signal measure determined at each
        cursor with EVEN index in the sequence (i.e. cursors 0, 2, etc) will be 
        subtracted from the signal measure determined at the following cursor
        (with ODD index in the sequence).
    
        E.g. for two E/IPSC events one would require four cursors:
        base_0, peak_0, base_1, peak_1 placed, respectively, on the signal baseline
        (just before the event - the "base" cursors) and on the event's "peak" 
        (for upward events) or "nadir" (or "trough", for inward events).

        The amplitude of the two events will be calculated as the difference 
        between the signal measures¹ at peak_0, base_0 and peak_1, base_1, i.e.:
    
        peak_0 - base_0 
        peak_1 - base_1
        
        ¹In this context, a signal measure is a scalar calculated from the signal
        data faling inside the cursor's x window, using the callable in 'func''
    
    channel: int: index of the signal channel (i.e., index along axis 1 of the 
        signal data array) or None
    
    
    WARNING: The parameters aren't checked for type and consistency
    """
    if len(cursors) % 2 > 0:
        raise ValueError(f"Expecting an even number of cursors; instead, got {len(cursors)}")
    
    if not isinstance(func, typing.Callable):
        raise TypeError(f"'func' must be a callable")
    
    base_cursors = [cursors[k] for k in range(0, len(cursors), 2)]
    peak_cursors = [cursors[k] for k in range(1, len(cursors), 2)]

    # return peak - base
    
    return list(map(lambda x: func(signal, x[1], channel) - func(signal, x[0], channel), zip(base_cursors, peak_cursors)))


    
def cursors_measure(signal, func, cursors, channel=None):
    return list(map(lambda x: func(signal, x, channel), cursors))


    
