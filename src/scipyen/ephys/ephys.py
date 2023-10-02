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
import os, sys
import collections
import traceback
import datetime
import numbers
import inspect
import itertools
import functools
from functools import singledispatch
import warnings
import typing, types
from enum import Enum, IntEnum
from dataclasses import (dataclass, MISSING)
#### END core python modules

#### BEGIN 3rd party modules
# try:
#     import mypy
# except:
#     print("Please install mypy first")
#     raise
import numpy as np
import quantities as pq
import neo
# import pyabf
import matplotlib as mpl
# import pyqtgraph as pg
from gui.pyqtgraph_patch import pyqtgraph as pg
from PyQt5 import (QtGui, QtCore, QtWidgets)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, )
#### END 3rd party modules

#### BEGIN pict.core modules
from core.prog import (safeWrapper, with_doc, get_func_param_types)
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
from core.datazone import (DataZone, Interval)
from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType, )
from core.triggerprotocols import TriggerProtocol

from core import datatypes
from core.datatypes import (TypeEnum, check_type)
from core import workspacefunctions
from core import signalprocessing as sigp
from core import utilities
from core import neoutils
from core import pyabfbridge as pab
from core.utilities import normalized_index
from core.neoutils import get_index_of_named_signal
from core import quantities as scq
from core.quantities import (units_convertible, check_time_units, 
                             check_electrical_current_units, 
                             check_electrical_potential_units)

from gui.cursors import (SignalCursor, SignalCursorTypes)

#from .patchneo import neo


#### END pict.core modules


if __debug__:
    global __debug_count__

    __debug_count__ = 0
    
LOCATOR_TYPES = (SignalCursor, neo.Epoch, DataZone, Interval, type(MISSING))

LocatorTypeVar = typing.TypeVar('LocatorTypeVar', *LOCATOR_TYPES)

LOCATOR_SEQUENCE = typing.Sequence[LocatorTypeVar]

REGULAR_SIGNAL_TYPES = (neo.AnalogSignal, DataSignal)
IRREGULAR_SIGNAL_TYPES = (neo.IrregularlySampledSignal, IrregularlySampledDataSignal)

ABF = pab.ABF # useful alias

class LocationMeasure(collections.namedtuple("LocationMeasure", ("func", "locations", "name"))):
    """Lightweight functor to calculate a signal measure at a location.

A location is an object with one of the following types ('locator' types):
• SignalCursor
• neo.Epoch
• DataZone
• Interval

or a sequence (tuple, list) of SignalCursor, neo.Epoch, DataZone or Interval

Examples:
---------
from ephys import (LocationMeasure, cursor_average, interval_average,
                    cursors_difference, intervals_difference)

from datazone import Interval

from neoutils import get_epoch_interval

We assume a neo.AnalogSignal object is bound to the symbol 'signal' in the 
workspace, and that 'signal' is a voltage-clamp record of the membrane current
containing, say, and evoked excitatory synaptic current (EPSC).

1) Calculate the average of signal samples at a vertical cursor, which marks
the signal region corresponding to the cursor's xwindow extended symmetrically
around the cursor's x coordinate. The cursors is bound to a symbol 'cursor' in
the workspace.

c_measure = LocationMeasure(cursor_average, cursor, "c_measure")

a = c_measure(signal) → a quantity array

2) Same as (1) but using datazone.Interval objects; we assume there is a 
neo.Epoch bound to the symbol 'epoch' in the workspace.

To demonstrate, the following two lines generate two intervals based on an 
epoch interval labeled "EPSC0Base"; one Interval encapsulates a start time and a
duration; the other encapsulates a start and a stop time (see datazone.Interval)

intvl = get_epoch_interval(epoch, "EPSC0Base", duration=True)
intvl2 = get_epoch_interval(epoch, "EPSC0Base")

i_measure_1 = LocationMeasure(interval_average, intvl, "i_measure_1")

i_measure_2 = LocationMeasure(interval_average, intvl, "i_measure_2")

b = i_measure_1(signal)

c = i_measure_2(signal)

assert np.all(a == b) # see example (1) regarding 'a'
assert np.all(a == c)

3) Obtain a measure at a pair of locations of the same type.

We want to calculate the amplitude of an EPSC elicited as a difference between 
averages of the membrane current signal around the "peak" (or nadir) of the EPSC
and a baseline BEFORE the stimulus that elicited the EPSC.

For this example we assume that there are two intervals inside 'epoch' that
correspond to baseline and EPSC peak regions of the signal, labeled "EPSC0Base"
"EPSC0Peak".

From this epoch we generate two Interval objects (one each, for baseline and 
peak; note how we access the corresponding epoch intervals by using their labels):

# 'intervals' will be a list of Interval objects
intervals = [get_epoch_interval(epoch, i, duration=True) for i in ("EPSC0Base",
"EPSC0Peak")]

We also assume that there are two vertical cursors available (c0, c1), 
indicating the baseline and the peak regions of the signal.

We calculate this measure using the intervals (note we construct the LocationMeasure
and we call it with the signal in a one-line code):

a = LocalMeasure(intervals_difference, intervals, "i_diff") (signal)

For demonstration, we do the same using the cursors:

b = LocationMeasure(cursors_difference, [c0,c1], "c_diff")(signal)

assert np.all(a == b)

4) To calculate the same measure at the same location in several signals, 
you can call the LocationMeasure on each signal.

Say you want to calculate the input resistance during a voltage-clamp recording,
based on a recorded membrane current (the 'signal') and a recorded analog command 
signal (here, the command voltage, i.e. 'command').

For this purpose, the command signal contains a boxcar waveform (a hyperpolarizing
or depolarizing change in the membrane potential) - the "membrane test". 

If no whole-cell compensation is applied, then the membrane current recorded 
during the membrane test undergoes a rapid transient change (the "capacitive 
transient") before it settles to a new steady-state value, different from the 
baseline before the membrane test).

We calculate Rin by applying Ohm's law:

V = I×R ⇒ R = V / I

In this case:
V = the amplitude of the boxcar; 
I = the difference between the membrane current during the steady-state and that
during the baseline before the membrane test boxcar.

Therefore we need two LocationMeasure objects.

If we were to use two appropriately-placed cursors as locators:

baseline = LocationMeasure(cursor_average, baseline_cursor, "baseline")

steady_state = LocationMeasure(cursor_average, steady_state_cursor, "steady_state")

# next line calculates the average baseline membrane current before the membrane test boxcar
i0 = baseline(signal) 
# next line calculates the average baseline potential before the membrane test boxcar
v0 = baseine(command) # return

# similarly, for the steady-state membrane current and potential
i1 = steady_state(signal)
v1 = steady_state(command)

finally we calculate Rin as (v1 - v0) / (i1 - i0)

Note that in both cases we used cursor_average as the function passed to the 
LocationMeasure functor. Since we are taking a difference between the averages
of signals at two locations, we can be more direct and use just one 
LocationMeasure object (see example (3) above):

delta = LocationMeasure(cursors_difference, (baseline_cursor, steady_state_cursor), "delta")

dI = delta(signal)
dV = delta(command)

Rin = dV/dI # ⇒ this will generate a Quantity in command.units / signal.units
            # e.g. pq.mV / pq/pA
            # Most likely we want the resistance in MOhm (pq.MOhm), therefore
            # we must rescale it, so the last call should be:

Rin = (dV/dI).rescale(pq.MOhm)

Finally, a few reminders:

• Signals are 2D Quantity arrays (with the data represented as column vectors) 
and MAY have more than one trace (a.k.a "signal channel", not to be confused 
with a "recording channel"). A trace, therefore is a column in the signal array.

• Functions that calculate a measure at a single location return a Quantity
array. 
    ∘ For signals with just one trace, the result has only one element, so 
    in cases where just a scalar Quantity is needed, this value can be accessed 
    by indexing, e.g.:

        result[0], or more directly np.squeeze(result)

    ∘ For signals with more than one trace, the result is a subdimensional (1D)
    Quantity array, with one value per trace. Since the traces are indexed along
    the second axis (axis 1) of the original signal, one may want to restrict the
    calculations to the desired trace only, by passing the "channel" keyword to
    the call by the functor.

    • For situations where a numpy array is constructed from a list comprehension
    (such as is the case for cursors_difference, intervals_difference) the final
    result will gain a second axis (hence it will be 2D), even though it only 
    contains one value.

    I all these situation it is recommended to drop the singleton axes. 

So, we can finish the last example:

Rin = np.squeeze((dV/dI).rescale(pq.MOhm))  # ⇒ e.g. array(90.1997, dtype=float32) * Mohm

This is a SCALAR Quantity (even though it is described as an array, but note the
absence of square brackets in its string representation).

Indeed:

assert (Rin.ndim == 0) # ⇒ is True
    
"""
    __slots__ = ()
    
    def __call__(self, *args, **kwargs):
        # *args is a signal or sequence of signals
        
        if isinstance(self.locations, (list, tuple)) and not isinstance(self.locations, Interval):
            args = args + tuple(self.locations)
            
        else:
            args = args + (self.locations,)
            
        return self.func(*args, **kwargs)
  
class ClampMode(TypeEnum):
    NoClamp=1           # i.e., voltage follower (I=0) e.g., ElectrodeMode.Field,
                        # but OK with other ElectrodeMode
    VoltageClamp=2      # |these two should be
    CurrentClamp=4      # |     self-explanatory
    
    
class ElectrodeMode(TypeEnum):
    Field=1             # typically, associated with ClampMode.NoClamp; other ClampModes don't make sense
    WholeCellPatch=2    # can associate any ClampMode
    ExcisedPatch=4      # can associate any ClampMode although ClampMode.VoltageClamp makes more sense
    Sharp=8             # can associate any ClampMode although ClampMode.CurrentClamp makes more sense
    Tetrode=16          # these are really for 
    LinearArray=32      # local field potentials etc
    MultiElectrodeArray=64 # MEAs on a culture/slice?
   
class DataListener(QtCore.QObject):
    """
    Dynamically constructs and augments neo.Block data as
    axon files are created in the current working directory
    """
    def __init__(self, scipyenWindow, data:typing.Optional[neo.Block]=None):
        super().__init__(parent=scipyenWindow)
        self.scipyenWindow=scipyenWindow
        self.currentDir = os.getcwd()

    def start(self):
        self.scipyenWindow.enableDirectoryWatch(True)

    def stop(self):
        self.scipyenWindow.enableDirectoryWatch(False)


    @pyqtSlot(object)
    def slot_filesRemoved(self, removedItems):
        print(f"{self.__class__.__name__}.slot_filesRemoved {removedItems}")

    @pyqtSlot(object)
    def slot_filesChanged(self, changedItems):
        print(f"{self.__class__.__name__}.slot_filesChanged {changedItems}")

    @pyqtSlot(object)
    def slot_filesNew(self, newItems):
        print(f"{self.__class__.__name__}.slot_filesNew {newItems}")

def detectClampMode(signal:typing.Union[neo.AnalogSignal, DataSignal], 
                    command:typing.Union[neo.AnalogSignal, DataSignal, pq.Quantity]) -> ClampMode:
    """Infers the clamping mode from the units of signal and command"""
    vc_mode = scq.check_electrical_current_units(signal) and scq.check_electrical_potential_units(command)
    ic_mode = scq.check_electrical_potential_units(signal) and scq.check_electrical_current_units(command)
    
            
    clampMode = ClampMode.VoltageClamp if vc_mode else ClampMode.CurrentClamp if ic_mode else ClampMode.NoClamp

    return clampMode

def checkClampMode(clampMode:ClampMode, signal:typing.Union[neo.AnalogSignal, DataSignal],
                   command:typing.Union[neo.AnalogSignal, DataSignal, pq.Quantity, numbers.Number]) -> tuple:
    """Verifies that the clamping mode in clampMode is applicable to the signal & command.
Returns the signal and the command, possibly with units modified as expected for the specified clamping mode"""
    if clampMode == ClampMode.VoltageClamp:
        if not scq.check_electrical_current_units(signal):
            warnings.warn(f"'signal' has wrong units ({signal.units}) for VoltageClamp mode.\nThe signal will be FORCED to correct units ({pq.pA}). If this is NOT what you want then STOP NOW")
            klass = type(signal)
            signal = klass(signal.magnitude, units = pq.pA, 
                                         t_start = signal.t_start, sampling_rate = signal.sampling_rate,
                                         name=signal.name)
            
        if isinstance(command, pq.Quantity):# scalar Quantity, or Quantity array (including signal)
            if not scq.check_electrical_potential_units(command):
                if isinstance(command, (neo.AnalogSignal, DataSignal)):
                    warnings.warn(f"'command' has wrong units ({command.units}) for VoltageClamp mode.\nThe command signal will be FORCED to correct units ({pq.mV}). If this is NOT what you want then STOP NOW")
                    klass = type(command)
                    command = klass(command.magnitude, units = pq.mV, 
                                                t_start = command.t_start, sampling_rate = command.sampling_rate,
                                                name=command.name)
                    
                else:
                    warnings.warn(f"'command' has wrong units ({command.units}) for VoltageClamp mode.\nThe command will be FORCED to correct units ({pq.mV}). If this is NOT what you want then STOP NOW")
                    command = command.magnitude * pq.mV
                
        else: # command is a number
            command = command * pq.mV
        
    else: # current clamp mode
        if not scq.check_electrical_potential_units(signal):
            warnings.warn(f"'signal' has wrong units ({signal.units}) for CurrentClamp mode.\nThe signal will be FORCED to correct units ({pq.mV}). If this is NOT what you want then STOP NOW")
            klass = type(signal)
            signal = klass(signal.magnitude, units = pq.mV, 
                                         t_start = signal.t_start, sampling_rate = signal.sampling_rate,
                                         name=signal.name)
            
        if isinstance(command, pq.Quantity):
            if not scq.check_electrical_current_units(command):
                if isinstance(command, (neo.AnalogSignal, DataSignal)):
                    warnings.warn(f"'command' has wrong units ({command.units}) for CurrentClamp mode.\nThe command signal will be FORCED to correct units ({pq.pA}). If this is NOT what you want then STOP NOW")
                    klass = type(command)
                    command = klass(command.magnitude, units = pq.pA, 
                                                t_start = command.t_start, sampling_rate = command.sampling_rate,
                                                name=command.name)
                    
                else:
                    warnings.warn(f"'command' has wrong units ({command.units}) for VoltageClamp mode.\nThe command will be FORCED to correct units ({pq.pA}). If this is NOT what you want then STOP NOW")
                    command = command.magnitude * pq.pA
                    
        else: # command is a number
            command  = command * pq.pA
                
    return signal, command

def detectMembraneTest(command:typing.Union[neo.AnalogSignal, DataSignal], 
                       **kwargs) -> tuple:
    """Detects or checks the timing and amplitude of the command signal for a membrane test (boxcar).
Returns a tuple (start, stop, test_amplitude)"""
    up_first = kwargs.pop("up_first", True)
    boxduration = kwargs.pop("boxduration", None) # tuple min , max
    
    if isinstance(boxduration, (tuple, list)) and len(boxduration) == 2: # lower & upper boxcar widths
        if not all(isinstance(v, pq.Quantity) and v.size == 1 for v in boxduration):
            raise TypeError("'boxduration' must contain scalar Quantities")
        
    elif boxduration is not None:
        raise TypeError(f"'boxduration' expected to be a 2-tuple or None; got {type(boxduration).__name__} instead")
    
    u, d, test_amplitude, levels, labels, upward = sigp.detect_boxcar(command, up_first=up_first,
                                                                        **kwargs)
    
    if u.size != d.size:
        raise RuntimeError(f"The 'command' signal should have the same number of state transitions in both directions; currently, there are {d.size} down and {u.size} up transitions")
    
    if isinstance(upward, (tuple, list)) and not all(upward[0] == v for v in upward):
        raise RuntimeError("All boxcars must be in the same direction")
    
    if any(v.size > 1 for v in (d,u)): # more than one boxcar detected
        if boxduration is None:
            raise RuntimeError("More than one transition between levels has been detected and no constraints on boxcar width were specified ('boxduration')")
        
        else:
            if u.size == d.size and all(v == upward[0] for v in upward):
                if up_first:
                    widths = d-u if upward[0] else u-d
                else:
                    widths = u-d if upward[0] else d-u
                    
                ndx = np.where((widths >= boxduration[0]) & (widths <= boxduration[1]))[0]
                
                if ndx.size != 1:
                    raise RuntimeError(f"{ndx.size} boxcars have been detected with width between {boxduration[0]} and {boxduration[1]} when one was expected")
                
                ndx = ndx[0]
                # TODO: 2023-07-18 00:09:39
                # now, select down & up according to up_first and upward[0]
                    
    if d.ndim > 0:
        d = d[0]
        
    if u.ndim > 0:
        u = u[0]
        
    start, stop = (min(d,u), max(d,u))
    
    return start, stop, test_amplitude 
        

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
def epoch_reduce(func:types.FunctionType, 
                 signal: typing.Union[neo.AnalogSignal, DataSignal], 
                 epoch: typing.Union[neo.Epoch, tuple], 
                 intervals: typing.Optional[typing.Union[int, str]] = None,
                 channel: typing.Optional[int] = None) -> typing.Union[pq.Quantity, typing.Sequence[pq.Quantity]]:
    """
    Applies a reducing function to a signal, within the epoch's intervals.
    
    Parameters:
    ----------
    signal: neo.AnalogSignal, DataSignal

    epoch: neo.Epoch, DataZone

    intervals: int or str, a sequence of int or str; optional, default is None.

        This parameters is used when the Epoch or DataZone contains more than 
        one interval, to indicate on which epoch or zone interval(s) 'func' will
        be applied to the signal.

        See neoutils.get_epoch_interval(…) for details about how the epoch 
        intervals are selected.

        In addition, when the 'intervals' parameter is dataclasses.MISSING, then
        'func' is applied to a new signal generated by concatenating the slices 
        of the original signal, taken for all intervals in the epoch or zone.

        Finally, when index is None, 'func' is applied individually to the signal
        signal slices taken from all the intervals of the epoch or zone,
        returning an list of quantities (i.e. slices are NOT concatenated).

    channel: int or None (default)
        For multi-channel signal, specified which channel is used:
        0 <= channel < signal.shape[1]

    Returns:
    -------
    A python quantity, or a list of python quantities.

    For multi-channel signals the quantities are subdimensional arrays, unless a
    channel index is specified using the 'channel' parameter.

    When there is more than one interval specified, the function returns a list
    of quantities as above. This can be converted to a quantity array by passing
    it to np.array(…) constructor, but REMEMBER to re-apply the units!

    """
    
    if isinstance(epoch, (neo.Epoch, DataZone)):
        if len(epoch) == 0:
            return np.nan*signal.units
                
        if len(epoch) > 1:
            if intervals is None or isinstance(intervals, type(MISSING)):
                if isinstance(intervals, type(MISSING)):
                    intervals = [neoutils.get_epoch_interval(epoch, i) for i in range(len(epoch))]
                    # get all signal slices
                    slice_times = [(i[0][0] if i[0].ndim > 0 else i[0], i[1][0] if i[1].ndim > 0 else i[1]) for i in intervals]
                    slices = [signal.time_slice(*t) for t in slice_times]
                    #  and concatenate to new signal - use our (more convenient?)
                    # signal concatenation function
                    new_sig = neoutils.concatenate_signals(slices, axis=0)
                    
                    ret = fun(new_sig, axis=0)
                    
                    if isinstance(chanel, int):
                        return ret[channel].flatten()
                    
                    return ret

            elif isinstance(intervals, (int, str, np.str_, bytes)):
                intervals = [neoutils.get_epoch_interval(epoch, interval)]
                
            elif isinstance(intervals, (tuple, list))  and all(isinstance(i, (int, str, np.str_, bytes)) for i in intervals):
                intervals = [neoutils.get_epoch_interval(epoch, i) for i in intervals]
                
            else:
                raise TypeError(f"Unexpected index type")
            
        else:
            intervals = [(epoch.times[0], epoch.times[0] + epoch.durations[0])]
        
    else:
        raise TypeError(f"epoch expected to be a tuple (t0, duration) or a neo.Epoch; got {epoch} instead")
    
    ret = [interval_reduce(func, signal, interval, channel=channel) for interval in intervals]
    
    if len(ret)== 1:
        ret = ret[0]
        return ret
    
    return ret
    
def interval_reduce(func:typing.Callable,
                    signal: typing.Union[neo.AnalogSignal, DataSignal],
                    interval:typing.Union[Interval, typing.Sequence[typing.Union[numbers.Number, pq.Quantity]]],
                    channel:typing.Optional[int] = None,
                    duration:bool=False) -> pq.Quantity:
    """As cursor_reduce, but using an interval instead.
    
    The semantics of the interval is set by the 'duration' keyword parameters:
        • True ⇒ the interval tuple contains (start, duration, …)
        • False (default) ⇒ the interval tuple contains (start, stop, …)
    
    
    For more than one interval, use this function in a comprehension expression,
    such as:
    
    [interval_reduce(func, signal, interval, …) for interval in intervals]
    
    where '…' stands for the keyword parameters of this function.
    
    NOTE: In this context, an interval must not be confused with the arithmetic 
    concept of interval (see PyInterval, https://pyinterval.readthedocs.io/en/latest/)
    
    Positional parameters:
    ----------------------
    func: callable that takes a numpy array as parameters and returns a scalar 
        (eg np.mean, np.nanmean, etc)
    
    signal: signal-like object
    
    interval: a sequence (tuple, list) with at least two elements, and where the 
        first two values are both either numeric scalars or scalar quantities 
        (mixing two types is not allowed).
    
        These values specify the boundaries of the signal domain, as a closed
        interval.
    
        The first value indicates the start of the interval; the second value
        indicates the stop of the interval, or its duration, depending on the 
        value of the 'duration' keyword parameter (see below).
    
        When applied to a signal, the values of the interval, when given as 
        quantities, must have the same units as the signal's domain (e.g., 
        time units for neo.AnalogSignal).
    
        In either case, the values must resolve to an interval of size >= 0.
    
    Keyword (named) parameters:
    ---------------------------

    channel: optional, default is None.
        This is used with multi-channel signals (i.e. signals having more than 
        one trace) and selects the trace (channel) to which 'func' is applied.
    
        NOTE: Signal objects (neo.AnalogSignal, DataSignal) are essentially 2D
        numpy arrays with the data organized in COLUMNS.
    
        In this context, a 'channel' is one column of the signal array, hence it
        is indexed on the second axis (axis 1) of the array.
    
        When specified, 'channel' must be a single int value and normal python
        indexing rules apply (i.e. negative values are reverse indices).
    
        Therefore, 'channel' must be in range(-signal.shape[1], signal.shape[1])
    
    duration: optional default is False; a flag that indicates the semantic of 
        the second value in the interval:
    
        When False, the second value is a 'stop' time stamp.
    
        When True, the second value is a duration, meaning that the top time must
        be calculated as the sum of the first and second values of the interval
        
    
    Returns:
    --------
    
    A python Quantity. For multi-channel signals, this is a subdimensional array
    (with signal.ndim - 1 dimensions) unless a single channel has been specified
    with the 'channel' keyword parameter.
    
    When the interval size is 0, the function simply returns the signal value(s)
    interpolated at the domain value at the start of the interval (see 
    neo.AnalogSignal.time_index(…) for detals)
    
"""
    if not isinstance(func, types.FunctionType):
        raise TypeError(f"Expecting a function as first argument; got {type(func).__name__} instead")
    
    
    t0, t1 = interval[0:2]
    x0, x1 = t0, t1
    # NOTE: Must convert to scalars, i.e., unsized arrays
    if t0.ndim > 0:
        x0 = t0[0]
        
    if t1.ndim > 0:
        x1 = t1[0]
    
    if not isinstance(t0, pq.Quantity):
        x0 = t0 * signal.times.units
    
    if not isinstance(t1, pq.Quantity):
        x1 = t1 * signal.times.units
        
    if isinstance(interval, Interval):
        duration = interval.extent
        
    if duration:
        # t1 += t0 # BUG: 2023-06-18 14:18:16 → modified Interval in-place !!!
        x1 = t0 + t1
        
    # print(f"interval_reduce: interval = {interval} ⇒ t0 = {t0}, t1 = {t1}")
        
    if x0 == x1:
        ret = signal[signal.time_index(x0),:]
        
    elif x0 > x1:
        raise ValueError(f"The interval cannot have negative size")
    else:
        # print(f"t0 = {t0}, t1 = {t1}")
        ret = func(signal.time_slice(x0,x1), axis=0)
        
    if isinstance(channel, int):
        return ret[channel].flatten()
    
    return ret

def interval_average(signal, interval, channel=None, duration=False):
    return interval_reduce(np.mean, signal, interval, channel=channel, duration=duration)

def interval_max(signal, interval, channel=None, duration=False):
    return interval_reduce(np.max, signal, interval, channel=channel, duration=duration)
    
def interval_min(signal, interval, channel=None, duration=False):
    return interval_reduce(np.min, signal, interval, channel=channel, duration=duration)
    
def interval_argmax(signal, interval, channel=None, duration=False):
    return interval_reduce(np.argmax, signal, interval, channel=channel, duration=duration)
    
def interval_argmin(signal, interval, channel=None, duration=False):
    return interval_reduce(np.argmin, signal, interval, channel=channel, duration=duration)
    
def interval_maxmin(signal, interval, channel=None, duration=False):
    return interval_reduce(sigp.maxmin, signal, interval, channel=channel, duration=duration)
    
def interval_minmax(signal, interval, channel=None, duration=False):
    return interval_reduce(sigp.minmax, signal, interval, channel=channel, duration=duration)
    
def interval_argmaxmin(signal, interval, channel=None, duration=False):
    return interval_reduce(sigp.argmaxmin, signal, interval, channel=channel, duration=duration)
    
def interval_argminmax(signal, interval, channel=None, duration=False):
    return interval_reduce(sigp.argminmax, signal, interval, channel=channel, duration=duration)
    
def interval_slice(signal, interval, duration=False):
    t0, t1 = interval[0:2]
    if not isinstance(t0, pq.Quantity):
        t0 *= signal.times.units
    
    if not isinstance(t1, pq.Quantity):
        t1 *= signal.times.units
        
    if duration:
        t1 += t0
    
    if t1 == t0:
        return signal[signal.time_index(t0),:]
    
    return signal.time_slice(t0, t1)

def interval_mid_point(interval:tuple, duration:bool=False):
    """Calculated the mid-point of a interval tuple
"""
    i0, i1 = interval[0:2]
    
    return i0 + i1/2 if duration else i0 + (i1-i0)/2
    
        
def interval_chord_slope(signal, interval, channel = None, duration = False):
    t0, t1 = interval[0:2]
    if not isinstance(t0, pq.Quantity):
        t0 *= signal.times.units
    
    if not isinstance(t1, pq.Quantity):
        t1 *= signal.times.units
        
    if duration:
        t1 += t0
        
    if t1 == t0:
        raise ValueError(f"Cannot calculate slope for a 0-length array between t0 = {t0} and t1 = {t1}")
    
    v0, v1 = list(map(lambda x: neoutils.get_sample_at_domain_value(signal, x), (t0, t1)))
    
    ret = ((v1-v0) / (t1-t0)).simplified
    
    if isinstance(channel, int):
        return ret[channel]
    
    return ret

def interval_index(signal, interval:tuple, duration:bool=False):
    """Index of signal sample at the interval midpoint"""
    x = interval_mid_point(interval, duration=duration)
    
    if not isinstance(x, pq.Quantity):
        x *= signal.times.units
        
    elif x.units != signal.times.units:
        if not units_convertible(x, signal.times):
            raise TypeError(f"Interval units {x.units} are incompatible with the signal domain {signal.times.units}")
        
        x.rescale(signal.times.units)
        
    return signal.time_index(x)
    

def intervals_difference(signal: typing.Union[neo.AnalogSignal, DataSignal], 
                         interval0, interval1, 
                         func: typing.Optional[typing.Union[typing.Callable, types.FunctionType]] = None,
                         channel: typing.Optional[int]=None, 
                         duration:bool = False,
                         subfun: typing.Optional[typing.Union[typing.Callable, types.FunctionType]] = None):
    """Similar to cursors_difference(…).
    See cursors_difference(…) for details.
"""
    if func is None:
        func = interval_average
        functor=False
        
    elif isinstance(func, (typing.Callable, types.FunctionType)):
        # NOTE: 2023-06-16 11:26:59
        # to keep this simple I nonly check for the first & second parameters of func
        #
        # func is a functor if 1st parameter is a function
        #
        # a regularly sampled signal types is expected for the second parameter
        #   in a functor, or the first parameter, otherwise
        #
        # could also check for cursors and channnel, but it would complicate things
        #
        # therefore if subsequent parameters are of wrong type we will face 
        # exeptions raised by the call of func
        
        # NOTE: 2023-06-16 11:52:55 TODO factor out
        # currently this branch is the same code as in cursors_difference
        params = get_func_param_types(func)
        
        if len(params) == 0:
            raise TypeError("'func' must be a function with annotated signature")
        
        plist = [(p, t) for p,t in params.items()]
        
        # check against the first parameter
        
        # NOTE: 2023-06-16 11:31:03 
        # if first param is a function then func is a functor
        # the only cursor functor currently def'ed in this module is 'cursor_reduce''
        functor = "function" in plist[0][1] 
        
        sigparndx = 1 if functor else 0 # signal param is second for functors, first otherwise
        
        cursorparndx = 2 if functor else 1 # cursor param is 3rd for functors, 2nd otherwise
        
        sigpartype = plist[sigparndx][1]

        if isinstance(sigpartype, (tuple, list)):
            if any(t not in (neo.AnalogSignal, DataSignal) for t in sigpartype):
                raise TypeError(f"'func' expected to get a signal type {(neo.AnalogSignal, DataSignal)} at parameter {sigparndx}")
            
        elif isinstance(sigpartype, type):
            if sigpartype not in (neo.AnalogSignal, DataSignal):
                raise TypeError(f"'func' expected to get a signal type {(neo.AnalogSignal, DataSignal)} at parameter {sigparndx}")
            
    else:
        raise TypeError(f"'func' must be a callable; got {type(func).__name__} instead")

    if functor:
        if not isinstance(subfun, (typing.Callable, types.FunctionType)):
            raise TypeError(f"When 'func' is a functor, 'subfun' must be a callable or function; got {type(subfun).__name__} instead" )
        
        y0 = func(subfun, signal, interval0, channel=channel)
        y1 = func(subfun, signal, interval1, channel=channel)
    else:
        y0 = func(signal, interval0, channel=channel)
        y1 = func(signal, interval1, channel=channel)
    
    # y0, y1 = [interval_average(signal, i, channel=channel, duration=duration) for i in (interval0, interval1)]
    
    return y1 - y0

def intervals_distance(signal, interval0, interval1, duration=False):
    i0, i1 = [interval_index(signal, i, duration) for i in (interval0, interval1)]
    return i1 - i0
    
    
def intervals_chord_slope(signal, interval0, interval1, 
                          channel:typing.Optional[int] = None,
                          duration:bool=False):
    """Signal chord slope between two intervals.
        Similar to cursors_chord_slope but uses interval tuples
"""
    t0, t1 = [interval_mid_point(i, duration=duration) for i in (interval0, interval1)]
    
    y0, y1 = [interval_average(signal, i, channel=channel, duration = duration) for i in (interval0, interval1)]
    
    ret = ((y1-y0) / (t1-t0)).simplified
    
    if isinstance(channel, int):
        return ret[channel]
    
    return ret
    
def event_amplitude_at_intervals(signal:typing.Union[neo.AnalogSignal, DataSignal],
                                 intervals:tuple, 
                                 func:typing.Optional[typing.Callable]=None,
                                 channel:typing.Optional[int]=None, 
                                 duration:bool=False):
    """Similar to event_amplitude_at_cursors but using intervals.

    NOTE: when passed, 'func' must have the signature:
    
        f(signal, interval, channel:int, duration:bool)

    See also interval_reduce(…)
"""
    
    if len(intervals) % 2 > 0:
        raise ValueError(f"Expecting an even number of cursors; instead, got {len(intervals)}")
    
    base_intervals = [intervals[k] for k in range(0, len(intervals), 2)]
    peak_intervals = [intervals[k] for k in range(1, len(intervals), 2)]

    if func is None:
        return list(intervals_difference(signal, base_interval, peak_interval, channel=channel, duration=duration) for (base_interval, peak_interval) in zip(base_intervals, peak_intervals))
    elif isinstance(func, typing.Callable):
        # return peak - base
        return list(map(lambda x: func(signal, x[1], channel, duration=duration) - func(signal, x[0], channel, duration=duration), zip(base_intervals, peak_intervals)))
    else:
        raise TypeError(f"'func' must be a callable")
    

def cursor_slice(signal: typing.Union[neo.AnalogSignal, DataSignal],
                  cursor: typing.Union[SignalCursor, tuple]) -> typing.Union[neo.AnalogSignal, DataSignal]:
    """Returns a slice of the signal corresponding to a cursor's xwindow"""
    
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
                  channel: typing.Optional[int] = None) -> pq.Quantity:
    """Calculates reduced signal values (e.g. min, max, median etc) across a cursor's window.
    
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

        NOTE: 
        1) The core.signalprocessing module is already imported in a 
                Scipyen session under the `sigp` alias.

        2) These functions may take an optional 'axis' parameter; here, this
        parameter is ALWAYS 0 (i.e. we use the 'domain' axis of the signals).

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
def cursor_max(signal: typing.Union[neo.AnalogSignal, DataSignal], 
               cursor: typing.Union[SignalCursor, tuple], 
               channel: typing.Optional[int] = None) -> typing.Union[float, pq.Quantity]:
    """The maximum value of the signal across the cursor's window.
    Calls cursor_reduce with np.max as `func` parameter.
    """
    return cursor_reduce(np.max, signal, cursor, channel)

@safeWrapper
def cursor_min(signal: typing.Union[neo.AnalogSignal, DataSignal], 
               cursor: typing.Union[SignalCursor, tuple], 
               channel: typing.Optional[int] = None) -> typing.Union[float, pq.Quantity]:
    """The maximum value of the signal across the cursor's window.
    Calls cursor_reduce with np.min as `func` parameter.
    """
    return cursor_reduce(np.min, signal, cursor, channel)


@safeWrapper
def cursor_argmax(signal: typing.Union[neo.AnalogSignal, DataSignal], 
                  cursor: typing.Union[SignalCursor, tuple], 
                  channel: typing.Optional[int] = None):
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
def cursor_index(signal:typing.Union[neo.AnalogSignal, DataSignal], 
                 cursor: typing.Union[float, SignalCursor, pq.Quantity, tuple]):
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
def cursors_difference(signal: typing.Union[neo.AnalogSignal, DataSignal], 
                       cursor0: typing.Union[SignalCursor, tuple], 
                       cursor1: typing.Union[SignalCursor, tuple], 
                       func: typing.Optional[typing.Union[typing.Callable, types.FunctionType]] = None,
                       channel: typing.Optional[int] = None,
                       subfun: typing.Optional[typing.Union[typing.Callable, types.FunctionType]] = None) -> pq.Quantity:
    """Calculates the signal amplitude between two notional vertical cursors.
    
    amplitude = y1 - y0
    
    where y0, y1 are the average signal values across the windows of cursor0 and
    cursor1
    
    Parameters:
    -----------
    signal:neo.AnalogSignal, datatypes.DataSignal
    
    cursor0, cursor1: (x, window) tuples representing, respectively, the 
        cursor's x coordinate (time) and window (horizontal extent).
    
    func: a callable applied to the signal at both cursors. Optional, the default
        is cursor_average(…)
    
        The signature is:
    
        f(func, signal, cursor, …) → scalar i.e. a functor
        OR
        f(signal, cursor, …) → scalar i.e. a regular function
    
        The first category is cursor_reduce(…), defined in this module.
    
        The second category is any of the other cursor_*(…) functions defined in
        this module.
    
        WARNING: Custom functions can be also applied, but their signatures
        MUST BE annotated and conform to the signatures of the functions
        mentioned above.
    
        NOTE: It does not make sense to calculate the difference between measures
        determined with DIFFERENT functions.
        
    channel: optional default is None; specifies the channel index (i.e. the 
        the index of the signal along the 2nd axis). 
        When None, the function returns a subdiensional array if the signal is 
        a multi-channel signal (i.e. has more than one trace)
    
    subfun: types.FunctionType. 
        A function which takes a numpy array and returns a value(*).
    
        Used when 'func' itself is a functor (i.e. takes a function as parameter) 
        and represents the function passed to the call of 'func'.
            
        Such functions include those in the numpy package `np.min`, `np.max`,
        `np.mean`, `np.median`, `np.std`, `np.var`, (and their 'nan' versions),
        and functions defined in Scipyen's core.signalprocessing module (e.g.,
        `sem`, `nansem`, `nansize`, `data_range`, `is_positive_waveform`, 
        `waveform_amplitude`, `minmax`, etc.)

        NOTE: 
        1) The core.signalprocessing module is already imported in a 
                Scipyen session under the `sigp` alias.

        2) These functions may take an optional 'axis' parameter; here, this
        parameter is ALWAYS 0 (i.e. we use the 'domain' axis of the signals).

        (*) This value can be a scalar, or a tuple of scalars (e.g. sigp.maxmin)
    
        NOTE: Alternatively, one can wrap a functor in a functools.partial by
        fixing its function parameter to the 'subfunction', and pass this
        partial as 'func' parameter here.
            
    Returns:
    -------
    
    Python Quantity array with signal's units and shape (signal.shape[1], ) or
    (1, ) when channel is specified.
        
    """
    from gui.cursors import SignalCursor as SignalCursor
    
    if func is None:
        func = cursor_average
        functor=False
        
    elif isinstance(func, (typing.Callable, types.FunctionType)):
        # NOTE: 2023-06-16 11:26:59
        # to keep this simple I nonly check for the first & second parameters of func
        #
        # func is a functor if 1st parameter is a function
        #
        # a regularly sampled signal types is expected for the second parameter
        #   in a functor, or the first parameter, otherwise
        #
        # could also check for cursors and channnel, but it would complicate things
        #
        # therefore if subsequent parameters are of wrong type we will face 
        # exeptions raised by the call of func
        
        params = get_func_param_types(func)
        
        if len(params) == 0:
            raise TypeError("'func' must be a function with annotated signature")
        
        plist = [(p, (t, k)) for p, (t, k) in params.items()]
        
        # check against the first parameter
        
        # NOTE: 2023-06-16 11:31:03 
        # if first param is a function then func is a functor
        # the only cursor functor currently def'ed in this module is 'cursor_reduce''
        functor = "function" in plist[0][1] 
        
        sigparndx = 1 if functor else 0 # signal param is second for functors, first otherwise
        
        cursorparndx = 2 if functor else 1 # cursor param is 3rd for functors, 2nd otherwise
        
        sigpartype = plist[sigparndx][1]

        if isinstance(sigpartype, (tuple, list)):
            if any(t not in (neo.AnalogSignal, DataSignal) for t in sigpartype):
                raise TypeError(f"'func' expected to get a signal type {(neo.AnalogSignal, DataSignal)} at parameter {sigparndx}")
            
        elif isinstance(sigpartype, type):
            if sigpartype not in (neo.AnalogSignal, DataSignal):
                raise TypeError(f"'func' expected to get a signal type {(neo.AnalogSignal, DataSignal)} at parameter {sigparndx}")
            
    else:
        raise TypeError(f"'func' must be a callable; got {type(func).__name__} instead")

    # NOTE: 2023-06-18 18:08:24
    # below, we use numpy diff, but this will return a 2D array
    # this is DELIBERATE and is left up to the caller to decide that to do
    # (e.g. call np.squeeze() on the result, if that is suitable)
    if functor:
        if not isinstance(subfun, (typing.Callable, types.FunctionType)):
            raise TypeError(f"When 'func' is a functor, 'subfun' must be a callable or function; got {type(subfun).__name__} instead" )
        
        data = np.array([func(subfun, signal, c, channel=channel) for c in (cursor0, cursor1)]) * signal.units
        
        # y0 = func(subfun, signal, cursor0, channel=channel)
        # y1 = func(subfun, signal, cursor1, channel=channel)
    else:
        data = np.array([func(signal, c, channel=channel) for c in (cursor0, cursor1)]) * signal.units
        # y0 = func(signal, cursor0, channel=channel)
        # y1 = func(signal, cursor1, channel=channel)
    
    return np.diff(data, axis=0)
    # return np.ediff1d(data)
    # return y1-y0

@safeWrapper
def cursors_distance(signal: typing.Union[neo.AnalogSignal, DataSignal], 
                     cursor0: typing.Union[SignalCursor, tuple], 
                     cursor1: typing.Union[SignalCursor, tuple], 
                     channel: typing.Optional[int] = None):
    """Distance between two cursors, in signal samples.
    
    NOTE: The distance between two cursors in the signal domain is simply the
            difference between the cursors' x coordinates!.
    
    """
    ret = [cursor_index(signal, c) for c in (cursor0, cursor1)]
    
    return abs(ret[1]-ret[0])

@safeWrapper
def chord_slope(signal: typing.Union[neo.AnalogSignal, DataSignal], 
                t0: typing.Union[float, pq.Quantity], 
                t1: typing.Union[float, pq.Quantity], 
                w0: typing.Optional[typing.Union[float, pq.Quantity]] = 0.001*pq.s, 
                w1: typing.Optional[typing.Union[float, pq.Quantity]] = None, 
                channel: typing.Optional[int] = None):
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
    
    w0:  a scalar float or python Quantity = a window around the time points, 
        across which the mean signal value is calculated (useful for noisy 
        signals).
        
        Default is 0.001 * pq.s (i.e. 1 ms)
        
    w1: like w (optional default is None). When present, the windows w0 and w1
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
    intersection of the signal with two vertical cursors (or with the vertical
    lines of two crosshair cursors).
    
    The signal value at each cursor is taken as the average of signal samples
    across the cursor's horizontal window if the window it not zero, or the 
    sample values at the cursor's coordinate.
    
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
    
    return (y1-y0)/(t1-t0).simlified

def cursor_chord_slope(signal:typing.Union[neo.AnalogSignal, DataSignal], 
                       cursor:SignalCursor, 
                       channel:typing.Optional[int]=None):
    t0 = (cursor.x - cursor.xwindow/2) * signal.times.units
    t1 = (cursor.x + cursor.xwindow/2) * signal.times.units
    
    if t1 == t0:
        raise ValueError(f"Cursor xwindow is 0")
    
    v0, v1 = list(map(lambda x: neoutils.get_sample_at_domain_value(signal, x), (t0, t1)))
    
    ret = ((v1-v0) / (t1-t0)).simplified
    
    if isinstance(channel, int):
        return ret[channel]
    
    return ret
    
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
        
    elif isinstance(intervals, (tuple, list)) and all(isinstance(i, (int, str, np.str_, bytes)) for i in intervals):
        t0t1 = [neoutils.get_epoch_interval(epoch, i, duration=False) for i in intervals] 
        ret = [signal.time_slice(t0, t1).mean(axis=0) for (t0,t1) in t0t1]
       
    else:
        return np.nan * signal.units
        
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
    # TODO/FIXME see if pyabf can be used (via pyabfbridge)
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
            return  datatypes.DataSignal(y, origin=origin, **signalkwargs)
            
        else:
            return neo.AnalogSignal(y, **signalkwargs)
    
    return x, y
    
def event_amplitude_at_cursors(signal:typing.Union[neo.AnalogSignal, DataSignal], 
                               cursors:typing.Union[typing.Sequence[tuple], typing.Sequence[SignalCursor]],
                               func:typing.Optional[typing.Callable] = None,
                               channel:typing.Optional[int] = None) -> list:
    """
    Measures the amplitude of events(s) using "cursors".
    Use this for evoked events e.g. EPSC or IPSC
    
    Parameters:
    ----------
    
    signal: a signal object where the event amplitude is measured
    
    func: one (default) or callable with the signature 

        f(signal, cursor, channel) -> scalar (numeric or python Quantity)
    
        the function to be applied to each cursor  See, e.g., cursors_measure(…)
    
        When None, the function calls cursors_difference(…) on pairs of cursors
        taken every two cursors (see below)
    
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
    
    base_cursors = [cursors[k] for k in range(0, len(cursors), 2)]
    peak_cursors = [cursors[k] for k in range(1, len(cursors), 2)]

    if func is None:
        return list(cursors_difference(signal, base_cursor, peak_cursor, channel=channel) for (base_cursor, peak_cursor) in zip(base_cursors, peak_cursors))
    elif isinstance(func, typing.Callable):
        # return peak - base
        return list(map(lambda x: func(signal, x[1], channel) - func(signal, x[0], channel), zip(base_cursors, peak_cursors)))
    else:
        raise TypeError(f"'func' must be a callable")
    
def cursors_measure(func: typing.Callable,
                    signal:typing.Union[neo.AnalogSignal, DataSignal],
                    cursors: typing.Union[typing.Sequence[tuple], typing.Sequence[SignalCursor]],
                    channel: typing.Optional[int]=None) -> list:
    """Calculates a signal measure from signal data at cursors locations.
    
    Parameters:
    ----------
    func: a callable with signature f(signal, cursor, channel) -> scalar or array with signal.ndim-1 dimensions
    
    signal: neo.AnalogSignal or DataSignal
    
    cursors: sequence of SignalCursor (vertical or crosshair) or tuples of 
        parameters for notional vertical or crosshair cursors.
    
    channel: int (optional, default is None): index of the signal channel
        (i.e., along the signal's second axis)
    
"""
    return list(map(lambda x: func(signal, x, channel), cursors))

# NOTE: 2023-06-14 14:38:31
# migrating to single dispatch paradigm (dispatches on the locator type, which
# can be a cursor, an epoch, or an interval)
@singledispatch
def reduce(locator, func:typing.Callable, 
           signal:typing.Union[neo.AnalogSignal, DataSignal],
           channel:typing.Optional[int]=True, 
           duration:bool=False,
           loatorIndex:typing.Optional[int] = None):
    """Single-dispatch version of *_reduce functions in this module.

WARNING: this currently is just a springboard for the *_reduce functions already
defined in the module and delegates to them.

In the future, these functions will be replaced entirely by this function.
"""
    raise NotImplementedError(f"Function does not support {type(locator).__name__} locators")

@reduce.register(SignalCursor)
def _(locator, func, signal, channel:int=None, 
      duration:bool=False, locatorIndex:int=None):
    return cursor_reduce(func, signal, locator, channel=channel)

@reduce.register(tuple)
def _(locator, func, signal, channel:int=None,
      duration=False, locatorIndex:int=None):
    return interval_reduce(func, signal, locator,channel=channel, duration=duration)

@reduce.register(neo.Epoch)
@reduce.register(DataZone)
def _(locator, func, signal, channel=None,
      duration=False, locatorIndex:int=None):
    return epoch_reduce(func, signal, locator, 
                        index=locatorIndex, channel=channel)

def signal_measures_in_segment(s: neo.Segment, 
                            signal: typing.Union[int, str],
                            command_signal: typing.Optional[typing.Union[int, str]] = None,
                            trigger_signal: typing.Optional[typing.Union[int, str]] = None,
                            locations: typing.Optional[typing.Union[neo.Epoch, SignalCursor, Interval, 
                                                                    typing.Sequence[SignalCursor],
                                                                    typing.Sequence[Interval]]]=None,
                            membraneTest: typing.Optional[typing.Union[float, pq.Quantity, neo.Epoch, typing.Sequence[typing.Sequence[numbers.Number]], typing.Sequence[str], typing.Sequence[typing.Sequence[pq.Quantity]], typing.Sequence[SignalCursor]]]=None,
                            stim: typing.Optional[TriggerEvent]=None,
                            isi:typing.Union[float, pq.Quantity, None]=None) -> tuple:
    """
    TODO: 
    Calculates several signal measures on a signal contained in a neo.Segment.
    
    Use location functors (SignalMeasureAtLocation and SignalMeasureAtMultipleLocations)
    
    You need:
    
    1) THE signal to measure - I am inclined to use its units as an indication of whether
    the recording has been done in voltage clamp (⇒ signal has units of electrical
    current) of current clamp / field recording (⇒ signal has units of electrical
    potential).
    
    2) The command signal - optional. When present, this should help determine
        command waveforms as follows:
        • for voltage-clamp recordings, the boxcar voltage waveform for membrane
            test
        • for current-clamp recordings (patch or sharp electrode): 
            ∘ the boxcar current waveform for membrane test
            ∘ any further boxcar current waveforms for postsynaptic action potentials
        (if any were used)
    
        NOTE: This is NOT needed for field recordings.
    
        When absent, and the recordings are done in voltage- or current clamp, then
    the membrane test VALUES should be passed as a python Quantity in units of 
    electrical potential (indicates Volatge-clamp) or units of current (indicating
    current clamp).
    
        If no membrane test is passed then we shall refrain from any computations
    in this respect.
    
    
    Ultimately, this is up to the acquisition device to advertise this in the signal's
    meta-data, but sometimes things can go wrong on that side as well.
    
    So it's good to add parameters to specify the recording mode as well.
    
    3) A triggers signal - analogsignal that embeds the digital outputs (usually
recorded by feeding the digial output back into an auxiliary analog input port 
on the acquisition device)
    
    This again is optional, and can be replaced by a parameter specifying the 
    triggers (e.g a TriggerProtocol).
    
    This can be useful in order to:
    • place cursors automatically (subject to some location constraints) BEFORE
    any recording has been made
    • when needed, calculate the inter-stimulus interval (e.g.when investigating
    pre-synaptic release via paired-pulse stimulations)
    • determine the latency of synaptic responses i.e. the time delay between the
    trigger onset and the onset of the synaptic event
    
    4) a set of signal measures at locations along the signal
    
    This is the most tricky one: I need an abstract representation of that.
    
    ephys.SignalMeasureAtLocation and ephys.SignalMeasureAtMultipleLocations go
    some way toward this goal, but they require prior knowledge of the locations
    
    This can be OK in principle, when the locations are pre-determined by, say,
    a trigger protocol or a generic boxcar protocol; however, this may not always
    be the case, especially when performing post-hoc (i.e. off-line) analysis
    where the locations are typically set upmanually by the user (via SignalCursors
    and Epochs).
    
    So maybe the way to go is to use LocationMeasure and subclasses.
    
    
    
    
    
    
    """
    membrane_test_intervals = [b"Rbase", b"Rs", b"Rin"]
    mandatory_intervals = [b"EPSC0Base", b"EPSC0Peak"]
    optional_intervals = [b"EPSC1Base", b"EPSC1Peak"]
    
    if locations is None:
        if len(s.epochs) == 0:
            raise ValueError("Segment has no epochs, and no locations have been passed to this call.")
        
        # NOTE 2023-06-16 09:47:53
        # allow more flexibility in epoch naming e.g. LTP_epoch, etc - acceptable
        # epoch names are the ones beginning with "ltp" (case-insensitive)
        ltp_epochs = [e for e in s.epochs if (isinstance(e.name, str) and e.name.strip().lower() == "ltp" or e.name.strip().lower().startswith("ltp"))]
        
        if len(ltp_epochs) == 0:
            raise ValueError("Segment seems to have no LTP epoch defined, and no external epoch has been defined either")
        
        elif len(ltp_epochs) > 1:
            warnings.warn("There seem to be more than one LTP epoch defined in the segment; only the FIRST one will be used")
        
        if ltp_epochs.labels.size == 0 or ltp_epochs.labels.size != ltp_epochs.size:
            raise ValueError("Mismatch between epoch size and number of labels in the ltp epoch")
        
        if ltp_epoch.size in (2,4): # def'ed only for event amplitudes (v clamp, )
            pass
        
        locations = ltp_epochs[0]
        
    # NOTE: 2023-06-12 17:47:19
    # Allow for Rm epoch to by specified independently or not at all.
    # This means that the length of the LTP epoch can be 2, 4 (no Rm intervals), 5, or 7 (with rm intervals)
    # (rm intervals are always three: Rbase, Rs and Rin)
    
    if epoch.labels.size == 0 or epoch.labels.size != epoch.size:
        raise ValueError("Mismatch between epoch size and number of labels in the epoch")
    
    calculate_RsRin = True
    returnIdc = True
        
    if epoch.size in (2,4):
        # likely no Rm intervals ⇒
        # check that rm_epoch has been specified
        if rm_epoch is None:
            # no rm_epoch given ⇒ check if there is an rm epoch in the segment
            rm_epochs = [e for e in epochs if (e.size == 3 or (isinstance(e.name, str) and e.name.strip().lower() == "rm")) and all(neoutils.epoch_has_interval(l) for l in membrane_test_intervals)]
            
            if len(rm_epochs) == 0:
                calculate_RsRin = False
                
            else:
                if len(rm_epochs) > 1:
                    warnings.warn(f"{len(rm_epochs)} membrane test epochs were found; only the first one will be used ")

                rm_epoch = rm_epochs[0] # get the first one, discard the rest
                
        elif isinstance(rm_epoch, (tuple, list)) and len(rm_epoch) == 3 and all(isinstance(i, SignalCursor) for i in rm_epoch):
            calculate_RsRin = True
            returnIdc = True
            
        elif isinstance(rm_epoch, neo.Epoch): # pass trhu to delegated function; will raise if wrong
            calculate_RsRin = True
            returnIdc = True
            
        else:
            warnings.warn(f"'rm_epoch' cannot be used to calculate Rs and Rin")
            calculate_RsRin = False
            returnIdc = False
            
        # now check that the 2 or 4 intervals are the right ones
        
        if epoch.size == 2: 
            if not all(neoutils.epoch_has_interval(epoch, l) for l in mandatory_intervals):
                raise ValueError(f"The epoch is missing the intervals {mandatory_intervals}")
            
        elif epoch.size == 4:
            intvl = mandatory_intervals + optional_intervals
            if not all(neoutils.epoch_has_interval(epoch, l) for l in intvl):
                raise ValueError(f"The epoch is missing the intervals {intvl}")
            
    elif epoch.size in (5, 7): # this should include the Rm intervals - if not just skip the RsRin calculations
        if epoch.size == 5:
            intvl = mandatory_intervals
        else:
            intvl = optional_intervals
            
        if not all(neoutils.epoch_has_interval(epoch, l) for l in intvl):
            raise ValueError(f"The epoch is missing the intervals {intvl}")
        
        if not all(neoutils.epoch_has_interval(epoch, l) for l in membrane_test_intervals):
            calculate_RsRin = False
            returnIdc = False
            
        else:
            rm_epoch = epoch # we can use this to calculate RsRin as well (just using the Rm intervals in it)
            calculate_RsRin = True
            returnIdc = True
                
        
    # if epoch.size != 5 and epoch.size != 7:
    else:
        raise ValueError("The LTP epoch (either supplied or embedded in the segment) has incorrect length; expected to contain 2, 4, 5 or 7 intervals")
    
    
    membrane_test_intervals_ndx = [__interval_index__(epoch.labels, l) for l in membrane_test_intervals]
    mandatory_intervals_ndx = [__interval_index__(epoch.labels, l) for l in mandatory_intervals]
    optional_intervals_ndx = [__interval_index__(epoch.labels, l) for l in optional_intervals]
    
    # Now, check Im and Vm
    
    
    if calculate_RsRin:
        if isinstance(rm_epoch, neo.Epoch):
            rm_result = membrane.epoch_Rs_Rin()
        # Rs, Rin, Idc = 
    
    # [Rbase, Rs, Rin]
    t_test = [(epoch.times[k], epoch.times[k] + epoch.durations[k]) for k in membrane_test_intervals_ndx]
    
    
    # [EPSC0Base, EPSC0Peak]
    t = [(epoch.times[k], epoch.times[k] + epoch.durations[k]) for k in mandatory_intervals_ndx]
    
    Idc    = np.mean(s.analogsignals[signal].time_slice(t_test[0][0], t_test[0][1]))
    
    Irs    = np.max(s.analogsignals[signal].time_slice(t[1][0], t[1][1])) 
    
    Irin   = np.mean(s.analogsignals[signal].time_slice(t[2][0], t[2][1]))
    
    if command_signal is None:
        if isinstance(testVm, numbers.Number):
            testVm = testVm * pq.mV
            
        elif isinstance(testVm, pq.Quantity):
            if not units_convertible(testVm, pq.V):
                raise TypeError("When a quantity, testVm must have voltage units; got %s instead" % testVm.dimensionality)
            
            if testVm.size != 1:
                raise ValueError("testVm must be a scalar; got %s instead" % testVm)
            
        else:
            raise TypeError("When command_signal is None, testVm is expected to be specified as a scalar float or Python Quantity, ; got %s instead" % type(testVm).__name__)

    else:
        # NOTE: 2020-09-30 09:56:30
        # Vin - Vbase is the test pulse amplitude
        
        vm_signal = s.analogsignals[command_signal]
        
        if not units_convertible(vm_signal, pq.V):
            warnings.warn(f"The Vm signal has wrong units ({vm_signal.units}); expecting electrical potential units")
            warnings.warn(f"The Vm signal will be FORCED to correct units ({pq.mV}). If this is NOT what you want then STOP NOW")
            klass = type(vm_signal)
            vm_signal = klass(vm_signal.magnitude, units = pq.mV, 
                                         t_start = vm_signal.t_start, sampling_rate = vm_signal.sampling_rate,
                                         name=vm_signal.name)
        
        # vm_signal = s.analogsignals[command_signal].time_slice(t[0][0], t[0][1])
        # vm_signal = vm_signal.time_slice(t[0][0], t[0][1])
        
        Vbase = np.mean(vm_signal.time_slice(t[0][0], t[0][1])) # where Idc is measured
        # Vbase = np.mean(s.analogsignals[command_signal].time_slice(t[0][0], t[0][1])) # where Idc is measured
        #print("Vbase", Vbase)

        Vss   = np.mean(vm_signal.time_slice(t[2][0], t[2][1])) # where Rin is calculated
        # Vss   = np.mean(s.analogsignals[command_signal].time_slice(t[2][0], t[2][1])) # where Rin is calculated
        #print("Vss", Vss)
        
        testVm  = Vss - Vbase

    #print("testVm", testVm)
    
    Rs     = (testVm / (Irs - Idc)).rescale(pq.Mohm)
    Rin    = (testVm / (Irin - Idc)).rescale(pq.Mohm)
        
    #print("dIRs", (Irs-Idc), "dIRin", (Irin-Idc), "Rs", Rs, "Rin", Rin)
        
    Iepsc0base = np.mean(s.analogsignals[signal].time_slice(t[3][0], t[3][1])) 
    
    Iepsc0peak = np.mean(s.analogsignals[signal].time_slice(t[4][0], t[4][1])) 

    EPSC0 = Iepsc0peak - Iepsc0base
    
    if len(epoch) == 7 and len(optional_intervals_ndx) == 2:
        
        # [EPSC1Base, EPSC1Peak]
        t = [(epoch.times[k], epoch.times[k] + epoch.durations[k]) for k in optional_intervals_ndx]
        
        Iepsc1base = np.mean(s.analogsignals[signal].time_slice(t[0][0], t[0][1])) 
        
        Iepsc1peak = np.mean(s.analogsignals[signal].time_slice(t[1][0], t[1][1])) 
        
        #Iepsc1base = np.mean(s.analogsignals[signal].time_slice(t0[5], t1[5])) 
        
        #Iepsc1peak = np.mean(s.analogsignals[signal].time_slice(t0[6], t1[6])) 
        
        EPSC1 = Iepsc1peak - Iepsc1base
        PPR = (EPSC1 / EPSC0).magnitude.flatten()[0] # because it's dimensionless
        
    else:
        EPSC1 = np.nan * pq.mV
        PPR = np.nan
            
    ISI = np.nan * s.analogsignals[signal].times.units
    
    event = None
    
    if isinstance(isi, float):
        warnings.warn("Inter-stimulus interval explicitly given: %s" % isi)
        ISI = isi * s.analogsignals[signal].times.units
        
    elif isinstance(isi, pq.Quantity):
        if isi.size != 1:
            raise ValueError("ISI given explicitly must be a scalar; got %s instead" % isi)
            
        if not units_convertible(isi, s.analogsignals[signal].times):
            raise ValueError("ISI given explicitly has units %s which are incompatible with the time axis" % isi.units)
            
        warnings.warn("Inter-stimulus interval is explicitly given: %s" % isi)
        
        ISI = isi
        
    else:
        if isinstance(stim, TriggerEvent): # check for presyn stim event param
            if stim.event_type != TriggerEventType.presynaptic:
                raise TypeError("'stim' expected to be a presynaptic TriggerEvent; got %s instead" % stim.event_type.name)
            
            if stim.size < 1 or stim.size > 2:
                raise ValueError("'stim' expected to contain one or two triggers; got %s instead" % stim.size)
            
            event = stim
            
        elif len(s.events): # check for presyn stim event embedded in segment
            ltp_events = [e for e in s.events if (isinstance(e, TriggerEvent) and e.event_type == TriggerEventType.presynaptic and isinstance(e.name, str) and e.name.strip().lower() == "ltp")]
            
            if len(ltp_events):
                if len(ltp_events)>1:
                    warnings.warn("More than one LTP event array was found; taking the first and discarding the rest")
                    
                event = ltp_events[0]
                    
                
        if event is None: # none of the above => try to determine from trigger signal if given
            if isinstance(trigger_signal, (str)):
                trigger_signal = ephys.get_index_of_named_signal(s, trigger_signal)
                
            elif isinstance(trigger_signal, int):
                if trigger_signal < 0 or trigger_signal > len(s.analogsignals):
                    raise ValueError("invalid index for trigger signal; expected  0 <= index < %s; got %d instead" % (len(s.analogsignals), trigger_signal))
                
                event = tp.detect_trigger_events(s.analogsignals[trigger_signal], "presynaptic", name="LTP")
                
            elif not isinstance(trigger_signal, (int, type(None))):
                raise TypeError("trigger_signal expected to be a str, int or None; got %s instead" % type(trigger_signal).__name__)

            
        if isinstance(event, TriggerEvent) and event.size == 2:
            ISI = np.diff(event.times)[0]

    return (Idc, Rs, Rin, EPSC0, EPSC1, PPR, ISI)

def infer_clamp_mode(signal:typing.Union[neo.AnalogSignal, DataSignal], 
                     command:typing.Optional[typing.Union[neo.AnalogSignal, DataSignal]]) -> typing.Optional[ClampMode]:
    """
    Infers a clamp mode from the units embedded in the signals.
    
When 'command' is None, returns NoClamp, as this might be a recording of 
current or potential without any clamping (the latter case is more usual, e.g. 
the voltage follower, or the "I=0" mode in some amplifiers)
    
When 'command' is available, returns a ClampMode according to this table:
    
Signal units                    Command units                   ClampMode
----------------------------------------------------------------------------
electrical current (e.g. pA)    electrical potential (e.g. mV)  VoltageClamp
electrical potential (e.g. mV)  electrical current (e.g. pA)    CurrentClamp

In any other case (e.g. both signal and command have either current or potential
units) returns NoClamp, with a warning.

A command signal can be provided in one of the following ways:

∘ Recording of the secondary amplifier output. When available, and 
appropriately selected in the amplifier software/hardware, this signal
is - under usual circumstances - an APPROXIMATION of the actual 
command signal. NOTE: These are NOT identical! The secondary amplifier
output is a signal recorded through the microelectrode, and NOT a "clean"
command signal.

    Example for voltage-clamp mode with Multiclamp 700B:

    ⋆ The "Primary Output" and the "Secondary Output" are selectable in 
        MultiClamp commander software

    ⋆ The Primary output should be set to "Membrane current" (scaled by
        the gain)

    ⋆ The Secondary output should be set to "Membrane Potential".
        This is the membrane potential measured at the tip of the 
        microelectrode.

        Remember that in reality, the preamplifier (headstage) only
        measures potential, never a current.

        In voltage-clamp, the amplifier measures the membrane potential
        and injects a current with amplitude and polarity as needed to
        correct any deviations of the membrane potential from a desired
        value (the "clamp"). Traditionally, this requires two electrodes:
        one for potential measurement, and the other for current injection.

        In these amplifiers, both processes take place with a single
        electrode: the potential measurement and the current injection
        are performed via the same electrode alternatively - 
        interleaved - with a high repetition rate (μs period). This allows
        the amplifier to run a fast feedback loop to adjust the amount 
        of injected current needed to "clamp" the membrane potential.

        As the membrane potential deviates from the desired value, 
        a current (positive or negative) is injected in order to 
        compensate this change.

        Therefore, in voltage clamp, the primary output is actually the 
        current injected to "clamp" the voltage, whereas the secondary
        output (as set up above) is the actual membrane potential
        measured by the pipette.

        In other words, the command signal in voltage clamp merely alters
        the current injection so that the measured membrane potential
        follows the desired change described by the "command" waveform. 

        In these circumstances the secondary output (measured membrane
        potential) can be used as an approximation of the voltage 
        "command".

    In current clamp the same process applies, except for the need of a 
    feedback loop: the amplifier injects a predetermined current through
    the microelectrode, alternatively with measuring the membrane potential.
    Since the membrane potential is not being "clamped", no feedback loop
    is required.

    The Primary output is, now, the recorded membrane potential, whereas
    the Secondary output, when set to show membrane current, reflects
    the "real" command signal: the time-varying current injected through 
    the microelectrode.  

∘ A virtual command signal is generated post-hoc based on the protocol data. 
    This data may be present in the record file stored by the digitizer 
    software or in the protocol file

∘ A virtual command signal is generated manually by the user, based on 
    protocol information.
            
        

"""
    recordsCurrent = False
    recordsPotential = False
    commandIsCurrent = False
    commandIsPotential = False
    
    if isinstance(signal, (neo.AnalogSignal, DataSignal)):
        recordsCurrent = check_electrical_current_units(signal)
        recordsPotential = check_electrical_potential_units(signal)
        
    else:
        raise TypeError(f"'signal' expected a neo.AnalogSignal or DataSignal; instead, got {type(signal).__name__}")
    
    if not any(recordsCurrent, recordsPotential):
        raise ValueError(f"'signal' had incompatible units {signal.units}")
        
    if isinstance(command, (neo.AnalogSignal, DataSignal)):
        commandIsCurrent = check_electrical_current_units(command)
        commandIsPotential = check_electrical_potential_units(command)
        
        if not any(commandIsCurrent, commandIsPotential):
            raise ValueError(f"'command' has incompatible units {command.units}")
        
    elif command is None:
        return ClampMode.NoClamp
    else:
        raise TypeError(f"'comand' expected to be a neo.analogsignal, DataSignal or None; instead, got {type(command).__name__}")
    
    if commandIsPotential and recordsCurrent:
        return ClampMode.VoltageClamp
    
    if commandIsCurrent and recordsPotential:
        return ClampMode.CurrentClamp
    
    warnings.warn(f"Cannot infer clamp mode when recorded signal has {signal.units} units and the command signal has {command.units} units")
    
    return ClampMode.NoClamp
    
# should also pass an abf object; 
# find out adc names and units ⇒ recorded signal
# then for the DAC: dacNames, dacUnits ⇒ "command signal"
    
