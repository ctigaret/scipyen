# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r""" Classes and functions for electrophysiology data.

NOTATIONS USED BELOW:

"cursor": signalviewer.SignalCursor object

"cursor time point", "cursor time coordinate", "cursor domain coordinate":
the value of a cursor's 'x' attribute (floating point scalar). This is the
undimensioned value of the signal's domain at the cursor position.

The module provides a set of utility functions to operate primarily on objects
in NeuralEnsemble's neo package (http://neuralensemble.org/),
documented here: https://neo.readthedocs.io/en/stable/

Some of these function also apply to datasignal.DataSignal in Scipyen package.

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
import os
# import sys
import collections
import traceback
import datetime
import numbers
import inspect
import itertools
import functools
from functools import singledispatch
import warnings
import typing
import types
# import difflib
# import re as _re
# from enum import Enum, IntEnum
# from abc import ABC
import dataclasses
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
from neo.core.objectlist import ObjectList as NeoObjectList
import h5py
import pandas as pd
from tribool import Tribool
# import pyabf

from scipy import optimize

# import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip # noqa
    # from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True


import matplotlib as mpl
# from core.pyqtgraph_patch import pyqtgraph as pg
#### END 3rd party modules

#### BEGIN pict.core modules
from core.basescipyen import BaseScipyenData
# from core.traitcontainers import DataBag
from core.prog import (safewrapper, with_doc, get_func_param_types, scipywarn)
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
from core.datazone import (DataZone, Interval)
from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType, )
from core.triggerprotocols import TriggerProtocol, TriggerProtocolList
from core.typeenum import TypeEnum
from core.scipyendataclasses import (Episode, Schedule, ScipyenDataclass)
from core import datatypes
from core.datatypes import (check_type, type2str)
from core import workspacefunctions
from core import signalprocessing as sigp
from core import utilities
from core import neoutils
from core import strutils
from core import curvefitting as crvf
from core import models as models

from core.utilities import (reverse_mapping_lookup,
                            get_index_for_seq,
                            sp_set_loc,
                            normalized_index,
                            unique,
                            GeneralIndexType)

from core.neoutils import (get_index_of_named_signal, concatenate_blocks)
from core import scipyen_quantities as scq
from core.scipyen_quantities import (unitsConvertible, checkTimeUnits,
                             checkElectricalCurrentUnits,
                             checkElectricalPotentialUnits,
                             checkRescale)
import core.pyabfbridge as pab

from core.deferredmeasures import * # noqa

from gui.cursors import (DataCursor, SignalCursor, SignalCursorTypes)

from ephys.ephys_protocol import ElectrophysiologyProtocol

#from .patchneo import neo


#### END pict.core modules


if __debug__:
    global __debug_count__

    __debug_count__ = 0

LOCATOR_TYPES = (SignalCursor, DataCursor, neo.Epoch, DataZone, Interval, type(MISSING))

LocatorTypeVar = typing.TypeVar('LocatorTypeVar', *LOCATOR_TYPES)

LOCATOR_SEQUENCE = typing.Sequence[LocatorTypeVar]

REGULAR_SIGNAL_TYPES = (neo.AnalogSignal, DataSignal)
IRREGULAR_SIGNAL_TYPES = (neo.IrregularlySampledSignal, IrregularlySampledDataSignal)

class ClampMode(TypeEnum):
    NoClamp=1           # i.e., voltage follower (I=0) e.g., ElectrodeMode.Field,
                        # but OK with other ElectrodeMode
    VoltageClamp=2      # |these two should be
    CurrentClamp=4      # |     self-explanatory

NoClamp = ClampMode.NoClamp
VoltageClamp = ClampMode.VoltageClamp
CurrentClamp = ClampMode.CurrentClamp

class ElectrodeMode(TypeEnum):
    Null=0
    Field=1             # typically, associated with ClampMode.NoClamp; other ClampModes don't make sense
    WholeCellPatch=2    # can associate any ClampMode
    ExcisedPatch=4      # can associate any ClampMode although ClampMode.VoltageClamp makes more sense
    Sharp=8             # can associate any ClampMode although ClampMode.CurrentClamp makes more sense
    Tetrode=16          # 16-64 are for
    LinearArray=32      # local field potentials etc
    MultiElectrodeArray=64 # MEAs on a culture/slice?

NullElectrode = ElectrodeMode.Null
Field = ElectrodeMode.Field
WholeCellPatch = ElectrodeMode.WholeCellPatch
ExcisedPatch = ElectrodeMode.ExcisedPatch
Sharp = ElectrodeMode.Sharp
Tetrode = ElectrodeMode.Tetrode
LinearArray = ElectrodeMode.LinearArray
MultiElectrodeArray = ElectrodeMode.MultiElectrodeArray


class EphysDataListener(QtCore.QObject): # FIXME 2026-06-13 22:05:16 Not used ?!?
    r"""
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


    @Slot(object)
    def slot_filesRemoved(self, removedItems):
        print(f"{self.__class__.__name__}.slot_filesRemoved {removedItems}")
        pass

    @Slot(object)
    def slot_filesChanged(self, changedItems):
        print(f"{self.__class__.__name__}.slot_filesChanged {changedItems}")
        pass

    @Slot(object)
    def slot_filesNew(self, newItems):
        print(f"{self.__class__.__name__}.slot_filesNew {newItems}")
        pass

class Analysis(BaseScipyenData): # TODO 2026-05-31 21:15:19
    r"""TODO Finalize me !!!
    See deferredmeasures !
    """
    _data_attributes_ = (
        ("measurements", list, list()),     # list of time-varying measurements, by default is empty
                                            # e.g., EPSP amplitude(s), fEPSP slope(s), RS, Rin, DC
                                            # NOTE: even though some parameters such
                                            # as Rin, DC, etc are not pathway specific,
                                            # we store them here as
        )

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

def detectClampMode(signal:typing.Union[neo.AnalogSignal, DataSignal],
                    command:typing.Union[neo.AnalogSignal, DataSignal, pq.Quantity]) -> ClampMode:
    r"""Infers the clamping mode from the units of signal and command"""
    vc_mode = scq.checkElectricalCurrentUnits(signal) and scq.checkElectricalPotentialUnits(command)
    ic_mode = scq.checkElectricalPotentialUnits(signal) and scq.checkElectricalCurrentUnits(command)


    clampMode = ClampMode.VoltageClamp if vc_mode else ClampMode.CurrentClamp if ic_mode else ClampMode.NoClamp

    return clampMode

def checkCrossTalk(val:dict) -> bool:
    if len(val) == 0:
        return False

    if validatePAxS(val):
        return all(len(unique(v))==2 for v in val.values())

    else:
        return False

def validatePAxS(val:dict):
    if not isinstance(val, dict):
        return False

    if len(val) == 0:
        return True

    # if not all(isinstance(k, int) or (isinstance(k, tuple) and len(k)>0 and all(isinstance(k_, int) for k_ in k)) for k in val) or \
    #     not all(isinstance(v, tuple) and all(isinstance(x, SynapticPathway) for x in v) for v in val.values()):
    #     raise ValueError("Argument must map ints or tuples of int keys to tuples of SynapticPathway objects")

    keys = list(val.keys())

    int_keys = list(filter(lambda x: isinstance(x, int), keys))
    tuple_keys = list(filter(lambda x: isinstance(x, tuple) and len(x)==2 and all(isinstance (v, int) for v in x), keys))

    if len(int_keys + tuple_keys) != len(val):
        return False

    values = [val[k] for k in int_keys + tuple_keys]

    OK_vals = list(filter(lambda x: isinstance(x, tuple) and (all(isinstance(v, SynapticPathway) for v in x) if len(x) else True), values ))

    if len(OK_vals) != len(values):
        return False

    return True

def checkClampMode(clampMode:ClampMode, signal:typing.Union[neo.AnalogSignal, DataSignal],
                   command:typing.Union[neo.AnalogSignal, DataSignal, pq.Quantity, numbers.Number]) -> tuple:
    r"""Verifies that the clamping mode in clampMode is applicable to the signal & command.
    Returns the signal and the command, possibly with units modified as expected for the specified clamping mode"""
    if clampMode == ClampMode.VoltageClamp:
        if not scq.checkElectricalCurrentUnits(signal):
            warnings.warn(f"'signal' has wrong units ({signal.units}) for VoltageClamp mode.\nThe signal will be FORCED to correct units ({pq.pA}). If this is NOT what you want then STOP NOW")
            klass = type(signal)
            signal = klass(signal.magnitude, units = pq.pA,
                                         t_start = signal.t_start, sampling_rate = signal.sampling_rate,
                                         name=signal.name)

        if isinstance(command, pq.Quantity):# scalar Quantity, or Quantity array (including signal)
            if not scq.checkElectricalPotentialUnits(command):
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
        if not scq.checkElectricalPotentialUnits(signal):
            warnings.warn(f"'signal' has wrong units ({signal.units}) for CurrentClamp mode.\nThe signal will be FORCED to correct units ({pq.mV}). If this is NOT what you want then STOP NOW")
            klass = type(signal)
            signal = klass(signal.magnitude, units = pq.mV,
                                         t_start = signal.t_start, sampling_rate = signal.sampling_rate,
                                         name=signal.name)

        if isinstance(command, pq.Quantity):
            if not scq.checkElectricalCurrentUnits(command):
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
    r"""Detects or checks the timing and amplitude of a membrane test waveform (boxcar).
    The detection occurs in a command signal (a copy of the DAC command) where the boxcar is defined.
    Use this an alternative to parsing an ElectrophysiologyProtocol, in order to
    infer the parameters of a membrane test epoch.

    Prerequisite: the command signal must have been recorded in the data. This
    can be chieved by routing the DAC output directly into an ADC input in the
    DAQ device, or by recording an appropriate¹ "secondary" output signal from
    the amplifier (if available).

    Returns a tuple (start, stop, test_amplitude).


    NOTE:
    ¹ Some amplifiers provide a secondary output in addition to the main output
    signal carrying the recorded electrical signal. The secondary output signal
    may be selected to contain the pipette voltage (in voltage clamp) or
    pipette current (in current clamp) which can be used as a "proxy" for the
    command signal in these clamping modes.
"""
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


def isiFrequency(data:typing.Union[typing.Sequence, collections.abc.Iterable],
                 start:int = 0,
                 span:int=1,
                 isISI:bool=False,
                 useNan:bool=True):
    r"""Calculates the reciprocal of an inter-event interval.

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

    useNan:bool, flag to return NaN Hz when data contains at most one event.
            Optional, default is True; when False, returns 0 Hz for such condition.

    Returns:
    ========
    The frequency (reciprocal of the interval's duration) as a scalar Quantity
    in pq.Hz.

    If the data is empty returns nan Hz, or 0. Hz when `useNan` parameter is False.

    If the data contains only element:
        • if the element is a time stamp (`isISI` parameter is False), returns
        nan Hz, unless `useNan` parameter is False, in which case returns 0.

        • if the element if an interval (`isISI` parameter is Trtue), returns
        the reciprocal of that interval.

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

    CHANGELOG:
    2024-01-20 09:44:10
        • returns NaN Hz when data has at most one event; this behavour can be
            reverted to the previous one (i.e. return 0 Hz when there is at most
            one event) by passing `useNan` False
        • added the `useNan` flag to change what is returned when data has at
            most one event

    """
    if len(data) == 0:
        return np.nan * pq.Hz if useNan else 0*pq.Hz

    if len(data) == 1:
        if isISI: # just one inter-spike interval is given
            return 1/data[0]
        else: # data is just one time stamp - cannot calculate - return NaN or 0 depending on useNan
            return np.nan * pq.Hz if useNan else 0*pq.Hz

    if start < 0:
        raise ValueError(f"'start' must be >= 0; got {start} instead")

    if start >= len(data):
        raise ValueError(f"'start' must be < {len(data)}; got {start} instead")

    if span < 1:
        raise ValueError(f"'span' expected to be at least 1; got {span} instead")

    if start + span >= len(data):
        raise ValueError(f"'span' cannot be larger than {len(data)-start}; got {span} instead")

    if isISI: # data has inter-spike intervals
        return (1/np.sum(data[start:(start+span)])).rescale(pq.Hz)

    else: # data is time stamps
        stamps = data[start:(start+span+1)]
        return (1/(stamps[-1]-stamps[start])).rescale(pq.Hz)

@singledispatch
def mid_point(loc: object,
              outer: bool = True):
    r"""Mid point across a location object.

.. |nbsp| unicode:: 0xA0
   :trim:

Parameters:
-----------

:loc:
    A "location" object.

    This can be:
    * a pair of two coordinates on a signal domain,
    * a sequence of coordinate pairs
    * a neo.Epoch
    * a datazone.DataZone
    * a datazone.Interval
    * a cursors.DataCursor
    * a cursors.SignalCursor

    The mid-point of a DataCursor or SignalCursor is their coordinate!

:outer:
    When ``True`` (the default) and 'loc' has more than one *sub-interval* |nbsp|
    returns the mid-point across *all* sub-intervals. When ``False``, returns the |nbsp|
    mid-point for each *sub-interval*.

    When 'loc' is a DataCursor or a SignalCursor, this parameter is ignored as |nbsp|
these objects encapsulate a single interval.

.. attention::
    The *sub-intervals* in Interval, DataZone and neo.Epoch objects are not necessarily contiguous!
"""
    raise NotImplementedError(f"Locations of type {type(loc).__name__} are not supported")

@mid_point.register(tuple)
@mid_point.register(list)
@mid_point.register(collections.deque)
def _mid_point_(loc: typing.Union[typing.Sequence[numbers.Number],
                                      typing.Sequence[pq.Quantity],
                                      typing.Sequence[typing.Sequence[numbers.Number]],
                                      typing.Sequence[typing.Sequence[pq.Quantity]],
                                      ],
                outer: bool = True):
    if all(isinstance(l, (numbers.Number, pq.Quantity)) for l in loc): # noqa
        assert len(loc) == 2, f"Expecting a pair of scalars; got {len(loc)} elements instead."
        loc = (min(loc), max(loc))
        return loc[0] + (loc[1]-loc[0])/2

    elif all(isinstance(l, (tuple, list, collections.deque)) and all(isinstance(ll, (numbers.Number, pq.Quantity)) for ll in l) for l in loc): # noqa
        if outer:
            t0, t1 = min(loc[0][0], loc[-1][-1]), max(loc[0][0], loc[-1][-1])
            return t0 + (t1-t0)/2
        else:
            mp = lambda xx: xx[0] + (xx[1]-xx[0])/2 # noqa
            return list(map(lambda l: mp(sorted(l)), loc))

    else:
        raise ValueError("'loc' must be a sequence of two scalars or a sequence of scalar pairs")

@mid_point.register(neo.Epoch)
@mid_point.register(DataZone)
@mid_point.register(Interval)
def _mid_point_(loc: typing.Union[neo.Epoch, DataZone, Interval], # noqa
                outer: bool = True):

    if outer:
        t0 = loc.t0.flatten()[0] if isinstance(loc, Interval) else loc.times.flatten()[0]
        dt = loc.t1.flatten()[-1] - t0 if isinstance(loc, Interval) else np.sum(loc.durations.flatten())

        return t0 + dt/2

    else:
        intervals = list(map(lambda k: (
                                        loc[k] if isinstance(loc, Interval)
                                        else (loc[k].times, loc[k].times+loc[k].durations)
                                        ),
                             range(loc.size)
                            )
                        )

        return list(map(lambda i: mid_point(i, True), intervals))

@mid_point.register(DataCursor)
@mid_point.register(SignalCursor)
def _mid_point_(loc: typing.Union[DataCursor, SignalCursor], # noqa
                _: bool = True):
    ret = loc.x if isinstance(loc, SignalCursor) else loc.coord

    if isinstance(ret, pq.Quantity):
        return ret.copy()

    return ret

@mid_point.register(pq.Quantity)
def _mid_point_(loc: pq.Quantity, _:bool = True):
    if loc.size == 1:
        return loc

    return (loc[-1] - loc[0])/2


@singledispatch
def get_location_boundary(loc: object, start: bool,
                          outer: bool = True,
                          ) -> typing.Union[
                            numbers.Number, pq.Quantity,
                            typing.Sequence[numbers.Number],
                            typing.Sequence[pq.Quantity]
                            ]:
    r"""Returns the left or reight boundary of the location object.

.. |nbsp| unicode:: 0xA0
   :trim:

Parameters:
-----------

:loc:
    A "location" object.

    This can be:
    * a pair of two coordinates on a signal domain,
    * a sequence of coordinate pairs
    * a neo.Epoch
    * a datazone.DataZone
    * a datazone.Interval
    * a cursors.DataCursor
    * a cursors.SignalCursor

.. note::
    When 'loc' is a sequence of coordinate pairs, each pair is assumed to be sorted in ascending order. |nbsp|
In addition, if the coordinates are Quantity objects, they must all have the same units.

:start:
    When True, returns the left boundary; otherwise, returns the right boundary.

:outer:
    When ``True`` (the default) and 'loc' has more than one *sub-interval* |nbsp|
    returns the *outer* left or right boundary (depending on the 'start' parameter) |nbsp|
    i.e., the "left-most" or "right-most" boundary.

    When ``False``, returns the left or right boundary for each sub-interval.

.. note::
    The 'outer' parameter is ignored when 'loc' is a DataCursor or a SignalCursor |nbsp|
because these objects encapsulate only one sub-interval.


"""
    raise NotImplementedError(f"Locations of type {type(loc).__name__} are not supported")

@get_location_boundary.register(tuple)
@get_location_boundary.register(list)
@get_location_boundary.register(collections.deque)
def _get_location_boundary_(loc: typing.Union[typing.Sequence[numbers.Number],
                                      typing.Sequence[pq.Quantity],
                                      typing.Sequence[typing.Sequence[numbers.Number]],
                                      typing.Sequence[typing.Sequence[pq.Quantity]],
                                      ],
                       start: bool,
                       outer: bool = True
                   ) -> typing.Union[numbers.Number, pq.Quantity,
                                     typing.Sequence[numbers.Number],
                                     typing.Sequence[pq.Quantity]]:

    # print(f"get_location_boundary(loc = {loc})\n")
    if all(isinstance(l, (numbers.Number, pq.Quantity)) for l in loc): # noqa
        assert len(loc) == 2, f"Expecting a pair of scalars; got {len(loc)} elements instead."
        return loc[0] if start else loc[1]

    elif all(isinstance(l, (tuple, list, collections.deque)) and all(isinstance(ll, (numbers.Number, pq.Quantity)) for ll in l) for l in loc): # noqa
        if outer:
            return loc[0][0] if start else loc[-1][-1]
        else:
            return list(map(lambda l: l[0] if start else l[1], loc)) # noqa

    else:
        raise ValueError("'loc' must be a sequence of two scalars or a sequence of scalar pairs")

@get_location_boundary.register(neo.Epoch)
@get_location_boundary.register(DataZone)
@get_location_boundary.register(Interval)
def _get_location_boundary_(loc: typing.Union[neo.Epoch, DataZone, Interval],
                       start: bool,
                       outer: bool = True
                   ) -> typing.Union[numbers.Number, pq.Quantity,
                                     typing.Sequence[numbers.Number],
                                     typing.Sequence[pq.Quantity]]:
    get_boundary = lambda i: (
        (
            i.t0.copy().flatten()[0] if isinstance(i, Interval)
            else i.times.copy().flatten()[0]
        ) if start
        else (
                i.t1.copy().flatten()[-1] if isinstance(i, Interval)
                else i.times.copy().flatten()[-1] + i.durations.copy().flatten()[-1]
             )
        )

    if outer:
        return get_boundary(loc)
    else:
        intervals = list(sorted(list(map(lambda k: loc[k], range(loc.size))),
                                key = lambda i: i.times if isinstance(loc, (neo.Epoch, DataZone)) else i.t0))
        return list(map(get_boundary, intervals))

@get_location_boundary.register(DataCursor)
@get_location_boundary.register(SignalCursor)
def _get_location_boundary_(loc: typing.Union[DataCursor, SignalCursor], # noqa
                       start: bool,
                       _: bool = True
                   ) -> typing.Union[numbers.Number, pq.Quantity,
                                     typing.Sequence[numbers.Number],
                                     typing.Sequence[pq.Quantity]]:

    if isinstance(loc, SignalCursor):
        coord = float(loc.x)
        span = float(loc.xwindow)
        if isinstance(loc.xUnits, pq.Quantity):
            coord *= loc.xUnits
            span *= loc.xUnits

    elif isinstance(loc, DataCursor):
        # need copies here, because of possible readjustment
        coord = loc.coord.copy() if isinstance(loc.coord, np.ndarray) else float(loc.coord)
        span = loc.span.copy() if isinstance(loc.span, np.ndarray) else float(loc.span)

    else:
        raise TypeError(f"Incorrrect cursors specification; expecting a SignalCursor, DataCursor, or a 2-tuple of scalars; got {loc} instead")

    t0, t1 = (coord - span/2, coord + span/2)

    return t0 if start else t1

@singledispatch
def signal_fit(loc:object,
               model: typing.Callable,
               fitTable: pd.DataFrame,
               signal: typing.Union[neo.AnalogSignal, DataSignal],
               /,
               adjustFitTable: dict = dict(),
               channel: typing.Optional[int] = None,
               ) -> typing.Optional[
                   typing.Union[
                       tuple,
                       typing.Sequence[tuple]
                       ]
                   ]:
    r"""
Parameters:
-----------
:signal: The signal to be fitted

:model: a function decorated with the ``models.modelfunction`` decorator

:fitTable: a DataFrame with intial fit parameters.

    This is expected to have
    * rows: names of the ``model`` function, in the order expected by it.

    * columns: "Initial Value", "Lower Bound", "Upper Bound" and "Keep Feasible"

    WARNING: the fitTable is NOT checked for compliance to the model!

    See examples in core.models.

:adjustFitTable: mapping of coefficient name to a dict (A: B) where

    * the key (A) is the kind of coefficient value: str, one of 'Initial Value', 'Lower Bound', 'Upper Bound', 'Keep Feasible'

    * the value (B) is the value to be set for the specified kind:
        * when kind is one of 'Initial Value', 'Lower Bound', 'Upper Bound':

            * str: signal attribute that returns a scalar

            * a reducing function (e.g. np.max, etc) which takes a signal as the first argument

            * a scalar number or a scalar pq.Quantity

        * when kind is 'Keep Feasible' this is expected to be a bool

    Example:

::

    {"x0": [("Initial Value", "t_start"), ("Lower Bound", 0)]
     "λ0": [("Initial Value", lambda x: -100 if <...> else 100),
            ("Upper Bound", lambda x: 0.0 if <...> else np.inf),
            ],
    }


    This will allow readjusting the table of fit coefficients dynamically


:channel: for multi-channel signals only, the index of the channel with data to be fit.

    When None, the fitting will proceed through **all** channels

Returns
--------

* when fitting single-channel signals, or a single channel of a multi-channel signal,
    returns a tuple (fitted curve, fit result)

* when fitting all channels returns a list of tuples as above

.. note::
    The ``model`` and the ``fitTable`` are used for **all** curve fitting operations

(i.e., across **all** channels)

.. warning::
    The ``fitTable`` should match the parameters expected by ``model``. NO CHECKS are performed by this function.


Returns None in case of failure

"""
    # print(f"signal_fit({loc} : {type(loc)})")
    raise NotImplementedError(f"Locations of type {type(loc).__name__} are not supported")

@signal_fit.register(DeferredSignalMeasure)
@signal_fit.register(types.FunctionType)
@signal_fit.register(functools.partial)
@signal_fit.register(types.NoneType)
@signal_fit.register(tuple)
@signal_fit.register(list)
@signal_fit.register(collections.deque)
def _signal_fit_(loc: typing.Union[typing.Sequence[numbers.Number],
                                      typing.Sequence[pq.Quantity],
                                      DeferredSignalMeasure,
                                      typing.Sequence[typing.Sequence[numbers.Number]],
                                      typing.Sequence[typing.Sequence[pq.Quantity]],
                                      typing.Sequence[typing.Sequence[DeferredSignalMeasure]],
                                      typing.Sequence[typing.Sequence[types.FunctionType]],
                                      typing.Sequence[typing.Sequence[functools.partial]],
                                      typing.Sequence[
                                                        typing.Union[
                                                            numbers.Number,
                                                            pq.Quantity,
                                                            DeferredSignalMeasure,
                                                            types.FunctionType,
                                                            functools.partial,
                                                            ]
                                                     ],
                                      types.NoneType],
                 model: typing.Callable,
                 fitTable: pd.DataFrame,
                 signal: typing.Union[neo.AnalogSignal, DataSignal],
                 /,
                 adjustFitTable: dict = dict(),
                 channel: typing.Optional[int]=None,
                 ) -> typing.Optional[
                   typing.Union[
                       tuple,
                       typing.Sequence[tuple]
                       ]
                   ]:
    if not models.isModelFunction(model):
        raise ValueError(f"The supplied {model} function is NOT a model function")

    # if not isinstance(fitTable, pd.DataFrame):
    #     raise TypeError("'fitTable' must be a pandas DataFrame")

    if loc is None:
        return __do_fit__(signal, model, fitTable, adjustFitTable, channel)

    # elif isinstance(loc, DeferredSignalMeasure):
    elif isinstance(loc, typing.Callable):
        if isinstance(loc, DeferredSignalMeasure):
            sg = loc(signal)

        else:
            sg = loc()
        if not isinstance(sg, typing.Union[neo.AnalogSignal, DataSignal]):
            raise ValueError(f"The supplied location measure ({loc}) did not return a signal")

        return __do_fit__(sg, model, fitTable, adjustFitTable, channel)

    # elif all(isinstance(loc_, (numbers.Number, pq.Quantity, DeferredSignalMeasure)) for loc_ in loc):
    elif all(isinstance(loc_, (numbers.Number, pq.Quantity, typing.Callable)) for loc_ in loc):
        if len(loc) == 1:
            if isinstance(loc[0], DeferredSignalMeasure):
                sg = loc[0](signal)

            elif isinstance(loc[0], typing.Callable):
                sg = loc[0]()

            if not isinstance(sg, typing.Union[neo.AnalogSignal, DataSignal]):
                raise ValueError(f"The supplied location measure ({loc}) did not return a signal")

            return __do_fit__(sg, model, fitTable, adjustFitTable, channel)

        elif len(loc) == 2:
            t0, t1 = loc
            sg = __slice_signal__(t0,t1, signal, channel) #, relative)

            return __do_fit__(sg, model, fitTable, adjustFitTable, channel)

        else:
            raise ValueError(f"Expecting a pair of elements; got {len(loc)} elements instead.")

    elif all(isinstance(loc_, (tuple, list, collections.deque)) and all(isinstance(ll, (numbers.Number, pq.Quantity, DeferredSignalMeasure)) for ll in loc_) for loc_ in loc):
        result = list()
        for loc_ in loc:
            t0, t1 = loc_
            sg = __slice_signal__(t0, t1, signal, channel) # , relative)
            ret = __do_fit__(sg, model, fitTable, adjustFitTable, channel)

        return np.vstack(result)

    else:
        raise ValueError(f"'loc' must be a Location Measure, a pair of scalars or Location Measures, or a sequence of such pairs")

@signal_fit.register(neo.Epoch)
@signal_fit.register(DataZone)
@signal_fit.register(Interval)
def _signal_fit_(loc: typing.Union[neo.Epoch, DataZone, Interval],  # noqa
                 model: typing.Callable,
                 fitTable: pd.DataFrame,
                 signal: typing.Union[neo.AnalogSignal, DataSignal],
                 /,
                 adjustFitTable: dict = dict(),
                 channel: typing.Optional[int] = None,
                 ) -> typing.Optional[
                   typing.Union[
                       tuple,
                       typing.Sequence[tuple]
                       ]
                   ]:
    if loc.ndim > 0:
        intervals = list(sorted(list(map(lambda k: loc[k], range(loc.size))),
                                key = lambda i: i.times if isinstance(loc, (neo.Epoch, DataZone)) else i.t0))
    else:
        intervals = [loc]

    result = list()

    for i in intervals:
        if isinstance(i, Interval):
            t0, t1 = i.t0.copy(), i.t1.copy()
        else:
            t0, t1 = i.times.copy(), i.durations.copy()

        # x0, x1 = t0, t1
        # NOTE: Must convert to scalars, i.e., unsized arrays
        if t0.ndim > 0:
            t0 = t0[0]

        if t1.ndim > 0:
            t1 = t1[0]

        if not isinstance(i, Interval):
            t1 = t0 + t1

        ret = signal_fit([t0, t1], func, fitTable, signal, adjustFitTable, channel) #, relative)

        result.append(ret)

    if all(isinstance(ret, (neo.AnalogSignal, DataSignal)) for ret in result):
        return neoutils.concatenate_signals(result)

    return np.vstack(result)

@signal_fit.register(DataCursor)
@signal_fit.register(SignalCursor)
def _signal_fit_(loc: typing.Union[DataCursor, SignalCursor], # noqa
                 model: types.FunctionType,
                 fitTable: pd.DataFrame,
                 signal: typing.Union[neo.AnalogSignal, DataSignal],
                 /,
                 adjustFitTable: dict = dict(),
                 channel: typing.Optional[int] = None,
                 ) -> typing.Optional[
                   typing.Union[
                       tuple,
                       typing.Sequence[tuple]
                       ]
                   ]:
    if isinstance(loc, SignalCursor):
        coord = float(loc.x)
        span = float(loc.xwindow)
        if isinstance(loc.xUnits, pq.Quantity):
            coord *= loc.xUnits
            span *= loc.xUnits

    elif isinstance(loc, DataCursor):
        # need copies here, because of possible readjustment
        coord = loc.coord.copy() if isinstance(loc.coord, np.ndarray) else float(loc.coord)
        span = loc.span.copy() if isinstance(loc.span, np.ndarray) else float(loc.span)

    else:
        raise TypeError(f"Incorrrect cursors specification; expecting a SignalCursor, DataCursor, or a 2-tuple of scalars; got {cursor} instead")

    t0, t1 = (coord - span/2, coord + span/2)

    return signal_fit([t0,t1], model, fitTable, signal, adjustFitTable, channel) #, relative)

@singledispatch
def signal_reduce(loc: object, func: typing.Callable,
                  signal: typing.Union[neo.AnalogSignal, DataSignal], /,
                  channel: typing.Optional[int] = None,
                  ) -> typing.Union[pq.Quantity, typing.Sequence[pq.Quantity]]:
                  # relative: bool = True) -> typing.Union[pq.Quantity, typing.Sequence[pq.Quantity]]:
    r""" Applies a reducing function to a signal, within the location's intervals.

.. |nbsp| unicode:: 0xA0
   :trim:

Operates on a region (or slice) of the signal.

Positional parameters:
----------------------
:loc:
    The location where a measure is calculated.

    This can be a neo.Epoch, datazone.DataZone or datazone.Interval, a |nbsp|
SignalCursor or DataCursor, or a DeferredSignalMeasure.
    ``neo.Epoch``, ``datazone.DataZone`` or ``datazone.Interval`` objects can |nbsp|
define more than one sub-interval.

:func: the reducing function, taking a numpy array argument and returning a scalar (e.g., np.min, np.argmin , etc)

:signal: neo.AnalogSignal, DataSignal

Named parameters:
-----------------
:channel: optional, default is None.
    When specified, 'channel' must be a single int value and normal python |nbsp|
    indexing rules apply (i.e. negative values are reverse indices).

    This is used with multi-channel signals (i.e. signals having more than
    one trace) and selects the trace (channel) to which 'func' is applied. |nbsp|

    NOTE: Signal objects (neo.AnalogSignal, DataSignal) are essentially 2D |nbsp|
    numpy arrays with the data organized in COLUMNS.

    In this context, a 'channel' is one column of the signal array, hence it |nbsp|
    is indexed on the second axis (axis 1) of the array.

    Therefore, 'channel' must be in range(-signal.shape[1], signal.shape[1])


Returns:
--------
A python quantity, or numpy array.

* When 'loc' is a DataZone, Interval, or neo.Epoch:
    * with a single *sub-interval* (loc.size == 1):
        * For a single-channel signal, returns a scalar quantity
        * For a multi-channel signal returns a scalar quantity if 'channel' is specified, else a subdimensional array with (signal.ndim - 1) dimensions

    * with loc.size > 1 (i.e. has several *sub-intervals*), returns a 2D Quantity array where each *row* contains the result from a *sub-interval*, as above

    For multi-channel signals the returned value are subdimensional arrays, unless a channel index is specified using the 'channel' parameter.

When there is more than one interval specified, the function returns a list
of quantities as above. This can be converted to a quantity array by passing
it to np.array(…) constructor, but REMEMBER to re-apply the units!

.. attention::
    Indexing a neo.Epoch or datazone.DataZone does NOT return an epoch, but a |nbsp|
Quantity with attributes 'times' and 'durations'. This is likely a bug. |nbsp|
Therefore, to pass a single neo.Epoch *sub-interval* create a new neo.Epoch or DataZone object first.

Example:

::

    epoch = neo.Epoch(times=[0.25, 0.35], durations=[0.01, 0.01], units=pq.s, labels = ["epoch0", "epoch1"])

    # getting the first interval of ``epoch`` as a new neo.Epoch object:

    sub_epoch = neo.Epoch(epoch[0].times, epoch[0].durations, labels = [epoch.labels[0]])

    # then use the new ``sub_epoch`` object

"""
    print(f"signal_reduce: loc = {loc}")
    raise NotImplementedError(f"Locations of type {type(loc).__name__} are not supported")

@signal_reduce.register(tuple)
@signal_reduce.register(list)
@signal_reduce.register(collections.deque)
@signal_reduce.register(DeferredSignalMeasure) # noqa
@signal_reduce.register(DeferredComputation) # noqa
@signal_reduce.register(types.FunctionType)
@signal_reduce.register(functools.partial)
@signal_reduce.register(types.NoneType)
def _signal_reduce_(loc: typing.Union[typing.Sequence[numbers.Number],
                                      typing.Sequence[pq.Quantity],
                                      DeferredSignalMeasure, # noqa
                                      typing.Callable,
                                      types.FunctionType,
                                      functools.partial,
                                      typing.Sequence[typing.Sequence[numbers.Number]],
                                      typing.Sequence[typing.Sequence[pq.Quantity]],
                                      typing.Sequence[typing.Sequence[DeferredSignalMeasure]],
                                      typing.Sequence[typing.Sequence[types.FunctionType]],
                                      typing.Sequence[typing.Sequence[functools.partial]],
                                      typing.Sequence[
                                                        typing.Union[
                                                            numbers.Number,
                                                            pq.Quantity,
                                                            DeferredSignalMeasure,
                                                            types.FunctionType,
                                                            functools.partial,
                                                            ]
                                                     ],
                                      types.NoneType],
                    func: typing.Callable,
                    signal: typing.Union[neo.AnalogSignal, DataSignal], /,
                    channel: typing.Optional[int] = None,
                    ) -> typing.Union[pq.Quantity, typing.Sequence[pq.Quantity]]:
                    # relative: bool = True) -> typing.Union[pq.Quantity, typing.Sequence[pq.Quantity]]:

    if loc is None:
        return __do_reduce__(func, signal, channel)

    elif isinstance(loc, (DeferredSignalMeasure, DeferredComputation)): # noqa
        sg = loc(signal)
        if not isinstance(sg, typing.Union[neo.AnalogSignal, DataSignal]):
            raise ValueError(f"The supplied location measure ({loc}) did not return a signal")

        return __do_reduce__(func, sg, channel)

    elif isinstance(loc, typing.Sequence) and all(isinstance(loc_, (numbers.Number, pq.Quantity, typing.Callable)) for loc_ in loc):
        if len(loc) == 1:
            if isinstance(loc[0], (DeferredSignalMeasure, np.ufunc)): # noqa
                sg = loc[0](signal)

            elif isinstance(loc, (types.FunctionType, functools.partial, typing.Callable)):
                sg = loc[0]() # pass here a functools.partial!

            else:
                raise TypeError(f"When 'loc' is a sequence with one element, this element should be a Callable: function, partial, np.ufunc or DeferredMeasure; instead, got a {type(loc[0]).__name__}")

            if not isinstance(sg, typing.Union[neo.AnalogSignal, DataSignal]):
                raise ValueError(f"The supplied location measure ({loc}) did not return a signal")

            return __do_reduce__(func, sg, channel)

        elif len(loc) == 2:
            t0, t1 = loc
            # print(f"\n__signal_reduce__ t0 = {t0}, t1 = {t1}\n")
            sg = __slice_signal__(t0, t1, signal, channel) #, relative)

            return __do_reduce__(func, sg, channel)

        else:
            raise ValueError(f"Expecting a pair of elements; got {len(loc)} elements instead.")

    elif all(isinstance(loc_, (tuple, list, collections.deque)) and all(isinstance(ll, (numbers.Number, pq.Quantity, typing.Callable)) for ll in loc_) for loc_ in loc):
        result = list()
        for loc_ in loc:
            if isinstance(loc_, DeferredSignalMeasure):
                sg = loc_(signal)
            elif isinstance(loc_, typing.Callable):
                sg = loc_()
            else:
                t0, t1 = loc_
                # print(f"\n__signal_reduce__ t0 = {t0}, t1 = {t1}\n")
                sg = __slice_signal__(t0, t1, signal, channel) #, relative)

            ret = __do_reduce__(func, sg, channel)
            result.append(ret)

        # print(f"_signal_reduce_ loc = {loc} ->\n\t{result}")

        if len(result) == 1:
            result = result[0]
            if not isinstance(result, pq.Quantity):
                result *= signal.units
            return result

        else:
            if all(isinstance(ret, (neo.AnalogSignal, DataSignal)) for ret in result):
                return neoutils.concatenate_signals(result)

            return np.vstack(result) * signal.units

    else:
        raise ValueError("'loc' must be a Location Measure, a pair of scalars or Location Measures, or a sequence of such pairs")


@signal_reduce.register(neo.Epoch)
@signal_reduce.register(DataZone)
@signal_reduce.register(Interval)
def _signal_reduce_(loc: typing.Union[neo.Epoch, DataZone, Interval], # noqa
                    func: typing.Callable,
                    signal: typing.Union[neo.AnalogSignal, DataSignal], /,
                    channel: typing.Optional[int] = None,
                    ) -> typing.Union[pq.Quantity, typing.Sequence[pq.Quantity]]:
                    # relative: bool = True) -> typing.Union[pq.Quantity, typing.Sequence[pq.Quantity]]:

    if loc.ndim > 0:
        intervals = list(sorted(list(map(lambda k: loc[k], range(loc.size))),
                                key = lambda i: i.times if isinstance(loc, (neo.Epoch, DataZone)) else i.t0))
    else:
        intervals = [loc]

    # print(f"\n»»»\n_signal_reduce_[{type(loc)}]\n\tintervals = \n")

    result = list()

    for ki, i in enumerate(intervals):
        if isinstance(i, Interval):
            t0, t1 = i.t0.copy(), i.t1.copy()
        else:
            t0, t1 = i.times.copy(), i.durations.copy()
        # print(f"\n\tt0 = {t0}, t1 = {t1}\n")
        # NOTE: Must convert to scalars, i.e., unsized arrays
        if t0.ndim > 0:
            t0 = t0[0]

        if t1.ndim > 0:
            t1 = t1[0]

        if not isinstance(i, Interval):
            t1 = t0 + t1

        # print(f"\n\t»»» t0 = {t0}, t1 = {t1} «««\n")
        ret = signal_reduce([t0, t1], func, signal, channel) #, relative)
        # print(f"_signal_reduce_<{i}: {type(i)}> -> interval {ki}: t0 = {t0}, t1 = {t1} => {ret} ({type(ret)})")

        result.append(ret)

        # print(f"\n«««\n")

    return result

@signal_reduce.register(DataCursor)
@signal_reduce.register(SignalCursor)
def _signal_reduce_(loc: typing.Union[DataCursor, SignalCursor], # noqa
                    func: types.FunctionType,
                    signal: typing.Union[neo.AnalogSignal, DataSignal], /,
                    channel: typing.Optional[int] = None,
                    ) -> typing.Union[pq.Quantity, typing.Sequence[pq.Quantity]]:
                    # relative: bool = True) -> typing.Union[pq.Quantity, typing.Sequence[pq.Quantity]]:
    if isinstance(loc, SignalCursor):
        assert loc.cursorType != SignalCursorTypes.horizontal, "Only vertical and crossshair cursors are supported"
        δx = loc.x - loc.xBounds()[0]
        coord = float(signal.t_start) + float(δx)
        # coord = float(loc.x)

        span = float(loc.xwindow)

        if isinstance(loc.xUnits, pq.Quantity):
            coord *= loc.xUnits
            span *= loc.xUnits

    elif isinstance(loc, DataCursor):
        # need copies here, because of possible readjustment
        coord = loc.coord.copy() if isinstance(loc.coord, np.ndarray) else float(loc.coord)
        span = loc.span.copy() if isinstance(loc.span, np.ndarray) else float(loc.span)

    else:
        raise TypeError(f"Incorrrect cursors specification; expecting a SignalCursor, DataCursor, or a 2-tuple of scalars; got {loc} instead")

    t0, t1 = (coord - span/2, coord + span/2)

    return signal_reduce([t0,t1], func, signal, channel) #, relative)

def signal_max(loc, signal, /, channel = None): #, relative = True):
    return signal_reduce(loc, np.max, signal, channel) #, relative) # * signal.units

def signal_argmax(loc, signal, /, channel = None): #, relative = True):
    loc_bounds = get_location_boundary(loc, True, True)
    starts = signal.time_index(loc_bounds)
    ext = signal_reduce(loc, np.argmax, signal, channel) #, relative)
    return starts + ext

def signal_domain_max(loc, signal, /, channel = None): #, relative = True):
    # print(f"\n***\nsignal_domain_max: signal length: {signal.shape[0]}, t_start: {signal.t_start}, t_stop: {signal.t_stop}")
    ndx = signal_argmax(loc, signal, channel) #, relative)
    # print(f"\n\tsignal_domain_max -> ndx = {ndx}\n***\n")
    return signal.times[ndx]

def signal_min(loc, signal, /, channel = None): #, relative = True):
    return signal_reduce(loc, np.min, signal, channel)# , relative) # * signal.units
    # if not isinstance(ret, pq.Quantity):
    #     ret *= signal.units
    # return ret

def signal_argmin(loc, signal, /, channel = None): #, relative = True):
    loc_bounds = get_location_boundary(loc, True, True)
    starts = signal.time_index(loc_bounds)# - signal.time_index(signal.t_start)
    ext = signal_reduce(loc, np.argmin, signal, channel) #, relative)
    # print(f"\n\text -> {ext}") # this is the time index in the signal AFTER having been sliced by loc!
    return starts + ext

def signal_domain_min(loc, signal, /, channel = None): # , relative = True):
    # print(f"\nsignal_domain_min: signal length: {signal.shape[0]}, t_start: {signal.t_start}, t_stop: {signal.t_stop}")
    ndx = signal_argmin(loc, signal, channel)# , relative)
    # print(f"\n\tsignal_domain_min -> ndx = {ndx}")
    return signal.times[ndx]

def signal_maxmin(loc, signal, /, channel =  None):# , relative = True):
    return signal_reduce(loc, sigp.maxmin, signal, channel) * signal.units
    # return signal_reduce(loc, sigp.maxmin, signal, channel, relative) * signal.units
    # if not isinstance(ret, pq.Quantity): # BUG 2026-05-11 01:02:33 FIXME
    #     ret *= signal.units
    # return ret

def signal_argmaxmin(loc, signal, /, channel = None):# , relative = True):
    loc_bounds = get_location_boundary(loc, True, True)
    # if relative:
    #     loc_bounds += signal.t_start
    starts = signal.time_index(loc_bounds)
    return starts + signal_reduce(loc, sigp.maxmin, signal, channel)# , relative)

def signal_domain_maxmin(loc, signal, /, channel = None): #, relative = True):
    ndx = signal_argmaxmin(loc, signal, channel)# , relative)
    return signal.times[ndx]

def signal_minmax(loc, signal, /, channel = None): #, relative = True):
    return signal_reduce(loc, sigp.minmax, signal, channel) * signal.units
    # return signal_reduce(loc, sigp.minmax, signal, channel, relative) * signal.units
    # if not isinstance(ret, pq.Quantity):
    #     ret *= signal.units
    # return ret

def signal_argminmax(loc, signal, /, channel = None): #, relative = True):
    loc_bounds = get_location_boundary(loc, True, True)
    # if relative:
    #     loc_bounds += signal.t_start
    starts = signal.time_index(loc_bounds)
    return starts + signal_reduce(loc, sigp.maxmin, signal, channel) #, relative)

def signal_domain_minmax(loc, signal, /, channel = None): # , relative = True):
    ndx = signal_argminmax(loc, signal, channel) #, relative)
    return signal.times[ndx]

def signal_average(loc, signal, /, channel = None):# , relative = True):
    ret = signal_reduce(loc, np.nanmean, signal, channel)# , relative)
    if not isinstance(ret, pq.Quantity):
        ret *= signal.units
    return ret

    # return signal_reduce(loc, np.nanmean, signal, channel, relative) * signal.units

@singledispatch
def signal_slice(loc, signal, /, channel = None,
                 outer: bool = True) -> typing.Union[neo.AnalogSignal,
                                                        DataSignal]:
                 # relative: bool = True) -> typing.Union[neo.AnalogSignal,
                 #                                        DataSignal]:
    raise NotImplementedError(f"Locations of type {type(loc).__name__} are not supported")

@signal_slice.register(types.NoneType)
def _signal_slice_(loc: types.NoneType, signal, /, channel = None,
                 outer: bool = True) -> typing.Union[neo.AnalogSignal,
                                                        DataSignal]:
    return signal

@signal_slice.register(DeferredSignalMeasure) # noqa
@signal_slice.register(types.FunctionType)
@signal_slice.register(functools.partial)
def _signal_slice_(loc: typing.Union[DeferredSignalMeasure, # noqa
                                    typing.Callable,
                                    types.FunctionType,
                                    functools.partial,
                                   ],
                 signal, /,
                 channel = None,
                 outer: bool = True,
                 ) -> typing.Union[neo.AnalogSignal,
                                                        DataSignal]:
                 # relative: bool = True) -> typing.Union[neo.AnalogSignal,
                 #                                        DataSignal]:

    loc = loc(signal)
    return slice_signal(loc, signal)


@signal_slice.register(tuple)
@signal_slice.register(list)
@signal_slice.register(collections.deque)
# def _signal_slice_(loc: typing.Union[list, tuple, collections.deque], signal, /,
def _signal_slice_(loc: typing.Union[typing.Sequence[numbers.Number],
                                      typing.Sequence[pq.Quantity],
                                      DeferredSignalMeasure, # noqa
                                      typing.Callable,
                                      types.FunctionType,
                                      functools.partial,
                                      typing.Sequence[pq.Quantity],
                                      typing.Sequence[DeferredSignalMeasure],
                                      typing.Sequence[types.FunctionType],
                                      typing.Sequence[functools.partial],
                                      typing.Sequence[
                                                        typing.Union[
                                                            numbers.Number,
                                                            pq.Quantity,
                                                            DeferredSignalMeasure,
                                                            types.FunctionType,
                                                            functools.partial,
                                                            ]
                                                     ],
                                      types.NoneType],
                   signal, /,
                   channel = None,
                   outer: bool = True,
                   ) -> typing.Union[neo.AnalogSignal,
                                                        DataSignal]:
                   # relative: bool = True) -> typing.Union[neo.AnalogSignal,
                   #                                      DataSignal]:

    # if isinstance(loc, typing.Callable):
    #     loc = loc(signal)
    #     return slice_signal(loc, signal, channel, outer, relative)

    if len(loc) != 2:
        raise ValueError("Expecting a sequence of two elements")

    t0, t1 = loc

    # WARNING 2026-05-07 12:36:09
    # this will FAIL WHEN LocationMasure DOES NOT RETURN a domain scalar!
    if isinstance(t0, DeferredSignalMeasure):
        t0_ = t0(signal, channel=channel) #, relative=relative)
        if isinstance(t0_, pq.Quantity) and not scq.unitsConvertible(t0_, signal.times.units):
            raise ValueError(f"Location measure {t0} generated data with incompatible physical dimensionality {t0_} ")
        t0 = t0_

    if isinstance(t1, DeferredSignalMeasure):
        t1_ = t1(signal, channel=channel) #, relative=relative)
        if isinstance(t1_, pq.Quantity) and not scq.unitsConvertible(t1_, signal.times.units):
            raise ValueError(f"Location measure {t1} generated data with incompatible physical dimensionality {t1_} ")
        t1 = t1_

    if all(isinstance(x, numbers.Number) for x in (t0,t1)):
        t0,t1 = tuple(map(lambda x: x*signal.times.units), (t0,t1))

    elif not all(isinstance(x, pq.Quantity) and x.size==1 for x in (t0,t1)):
        raise ValueError("Expecting a pair of floats or scalar Quantity objects")

    # print(f"\n***\n_signal_slice_ t0 = {t0}, t1 = {t1}")

    # if relative:
    #     # t0, t1 = adjust_time_relative_to_signal(signal, t0, t1)
    #     t0 = adjust_time_relative_to_signal(signal, t0)
    #     t1 = adjust_time_relative_to_signal(signal, t1)

    # print(f"\n\t_signal_slice_ adjusted t0 = {t0}, t1 = {t1}\n***\n")

    # ensure all are scalars (i.e. arrays with ndim = 0) an sorted in ascending order
    t0, t1 = sorted(tuple(map(lambda x: x.flatten()[0], (t0, t1))))

    # print(f"t0 = {t0}, t1 = {t1}")

    ret = signal.time_slice(t0,t1)
    if isinstance(channel, int):
        ret = ret[:,channel]
    return ret

@signal_slice.register(neo.Epoch)
@signal_slice.register(DataZone)
@signal_slice.register(Interval)
@signal_slice.register(DataCursor)
@signal_slice.register(SignalCursor)
def _signal_slice_(loc: typing.Union[neo.Epoch, DataZone, Interval,
                                     DataCursor, SignalCursor], signal, /,
                   channel = None,
                   outer: bool = True,
                   ) -> typing.Union[neo.AnalogSignal,
                                                        DataSignal]:
                   # relative: bool = True) -> typing.Union[neo.AnalogSignal,
                   #                                      DataSignal]:
    t0 = get_location_boundary(loc, True, outer) #+ signal.t_start
    t1 = get_location_boundary(loc, False, outer)# + signal.t_start

    # print(f"_signal_slice_[{type(loc)}]: t0 = {t0}, t1 = {t1}")

    return signal_slice((t0, t1), signal, channel, outer) # , relative)

def signal_chord_slope(loc, signal, /, channel = None, outer: bool = True): #, relative = True):
    r"""Calculates the signal chord slope between two time points t0 and t1.

.. |nbsp| unicode:: 0xA0
   :trim:


                    slope = (y1 - y0) / (t1 - t0)

where t0, t1 are the boundaries of the location 'loc'.

When 'loc' defines several *sub-intervals* the value of 'outer' determines if |nbsp|
a single slope is calculated on the outer boundaries (when True) or a slope is |nbsp|
calculated for every sub-interval.

See signal_chord_slope2() for a verison taking two locations.

"""
    t0 = get_location_boundary(loc, True, outer)
    t1 = get_location_boundary(loc, False, outer)

    slope = lambda x0, x1, y0, y1: (y1-y0) / (t1-t0)

    if all(isinstance(t, pq.Quantity) for t in (t0,t1)):
        # if relative:
        #     # t0, t1 = adjust_time_relative_to_signal(signal, t0, t1)
        #     t0 = adjust_time_relative_to_signal(signal, t0)
        #     t1 = adjust_time_relative_to_signal(signal, t1)

        if t1 == t0:
            raise ValueError(f"The signal slice between t0 = {t0} and t1 = {t1} has zero length")

        v0, v1 = list(map(lambda x: neoutils.get_sample_at_domain_value(signal, x), (t0, t1)))

        # print(f"signal_chord_slope: t0 = {t0}, t1 = {t1}, v0 = {v0}, v1 = {v1}")

        ret = slope(t0, t1, v0, v1).simplified

        if isinstance(channel, int):
            ret = ret[channel]

        return ret

    elif all(isinstance(t, typing.Sequence) for t in (t0, t1)):
        if relative:
            t0, t1 = zip(*list(map(lambda xx: adjust_time_relative_to_signal(signal, *xx),
                                  zip(t0, t1))))

        eqtimes = list(filter(lambda x: x[1][0] == x[1][1],
                              enumerate(zip(t0, t1))
                              )
                      )

        if len(eqtimes):
            raise ValueError(f"The following coordinate pairs would result in zero-length arrays: {list(map(lambda x: x[1], eqtimes))}")

        v0, v1 = zip(
                        *list(
                                map(lambda xx: tuple(
                                                        map(
                                                                lambda x: neoutils.get_sample_at_domain_value(signal, x),
                                                                xx
                                                            )
                                                     ),
                                    zip(t0, t1))
                              )
                     )

        if isinstance(channel, int):
            return list(map(lambda x: slope(*x).simplified[:,channel], zip(t0, t1, v0, v1)))
        else:
            return list(map(lambda x: slope(*x).simplified, zip(t0, t1, v0, v1)))

def signal_chord_slope2(loc0, loc1, signal, /, channel = None): #, relative = True):
    r"""Calculates signal chord slope between the mid-points of two locations.

.. |nbsp| unicode:: 0xA0
   :trim:

To calculate the chord slope between the boundaries of a single location use the |nbsp|
signal_chord_slope() function.

.. attention::

    The location mid-points are calculated over the entire locations (thus, including all sub-intervals defined in the location).

    If this is not what is intended, then make sure each location defines a single sub-interval.

Best used with two DataCursor or two SignalCursor objects.

"""
    # print(f"signal_chord_slope2({loc0}, {loc1}, {signal})")

    if isinstance(loc0, typing.Callable):
        # print(f"\nsignal_chord_slope2: loc0 = {loc0}")
        loc0 = loc0(signal)
        # print(f"\n\t => loc0 = {loc0}")

    if isinstance(loc1, typing.Callable):
        # print(f"\nsignal_chord_slope2: loc1 = {loc1}")
        loc1 = loc1(signal)
        # print(f"\n\t => loc1 = {loc1}")

    # NOTE: 2026-05-19 10:05:48
    #
    # SignalCursor objects have x "boundaries" allowing us to adjust their x
    # coordinate according to the current signal domain boundaries, when the
    # cursors were defined on another signal domain boundaries (and thus would fall
    # outside the domain of the current signal);
    #
    # Thisk is helpful when signal cursors defined in a signal viewer showing
    # a segment in a block, are used to measure things in signals in another
    # segment (i.e., with t_start DISTINCT from the current signal.t_start)
    #
    # ATTENTION: there are two CAVEATS:
    #
    # 1. The signal where the cursors were defined and the current signal should
    # have domains of identical size
    #
    # 2. The SignalCursor x boundaries must be identical to the domain boundaries
    # of the signal where the cursor was defined
    #
    if isinstance(loc0, SignalCursor):
        δx = loc0.x - loc0.xBounds()[0]
        t0 = float(signal.t_start) + float(δx)

    else:
        t0 = mid_point(loc0, True)

    if isinstance(loc1, SignalCursor):
        δx = loc1.x - loc1.xBounds()[0]
        t1 = float(signal.t_start) + float(δx)

    else:
        t1 = mid_point(loc1, True)

    # t0, t1 = tuple(map(lambda loc: mid_point(loc, True), (loc0, loc1)))


    if isinstance(t0, float):
        t0 = t0 * signal.times.units

    if isinstance(t1, float):
        t1 = t1 * signal.times.units

    # if relative:
    #     t0, t1 = adjust_time_relative_to_signal(signal, t0, t1)

    # print(f"signal_chord_slope2: t0 = {t0}, t1 = {t1}")

    if isinstance(channel, int):
        y0, y1 = tuple(map(lambda x: signal[signal.time_index(x), channel], (t0, t1)))
        # y0, y1 = tuple(map(lambda x: neoutils.get_sample_at_domain_value(signal[:channel], x), (t0, t1)))
    else:
        y0, y1 = tuple(map(lambda x: signal[signal.time_index(x)], (t0, t1)))
        # y0, y1 = tuple(map(lambda x: neoutils.get_sample_at_domain_value(signal, x), (t0, t1)))

    # print(f"{signal_chord_slope2} -> y0 = {y0}, y1 = {y1}")

    return (y1-y0)/(t1-t0)
    # return ((y1-y0)/(t1-t0)).simplified

@safewrapper
def epoch_reduce(func:types.FunctionType,
                 signal: typing.Union[neo.AnalogSignal, DataSignal],
                 epoch: typing.Union[neo.Epoch, DataZone, Interval],
                 channel: typing.Optional[int] = None) -> typing.Union[pq.Quantity, typing.Sequence[pq.Quantity]]:
    r"""
    Applies a reducing function to a signal, within the epoch's intervals.

    Parameters:
    ----------
    signal: neo.AnalogSignal, DataSignal

    epoch: neo.Epoch, DataZone

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
    assert isinstance(epoch, (neo.Epoch, DataZone, Interval)), f"'epoch' expected to be a datazone.DataZone, datazone.Interval, or neo.Epoch; instead got a {type(epoch).__name__}"

    # make sure sub-intervals are monotonically increasing
    if isinstance(epoch, (neo.Epoch, DataZone)):
        intervals = list(sorted(list(map(lambda k: epoch[k], range(epoch.size))),
                                key = lambda i: i.times))
    else:
        intervals = list(sorted(list(map(lambda k: epoch[k], range(epoch.size))),
                                key = lambda i: i.t0))

    result = list()

    for i in intervals:
        if isinstance(i, Interval):
            t0, t1 = i.t0.copy(), i.t1.copy()
        else:
            t0, t1 = i.times.copy(), i.durations.copy()

        # x0, x1 = t0, t1
        # NOTE: Must convert to scalars, i.e., unsized arrays
        if t0.ndim > 0:
            t0 = t0[0]

        if t1.ndim > 0:
            t1 = t1[0]

        if not isinstance(i, Interval):
            t1 = t0 + t1

        if t0 == t1:
            ret = signal[signal.time_index(t0),:]

        elif t0 > t1:
            raise ValueError(f"The interval cannot have negative size")
        else:
            # print(f"t0 = {t0}, t1 = {t1}")
            ret = func(signal.time_slice(t0,t1), axis=0)

        if isinstance(channel, int):
            ret = ret[channel].flatten()

        result.append(ret)

    # if len(result) == 0:
    #     return result[0]

    return np.vstack(result)# * signal.units

def interval_reduce(func:typing.Callable,
                    signal: typing.Union[neo.AnalogSignal, DataSignal],
                    interval: typing.Union[neo.Epoch, DataZone, Interval],
                    channel:typing.Optional[int] = None,
                    ) -> pq.Quantity:
                    # duration:bool=False) -> pq.Quantity:
    r"""Alias to epoch_reduce

.. |nbsp| unicode:: 0xA0
   :trim:

.. note::
    In this context, an interval must not be confused with the arithmetic |nbsp|
concept of interval (see PyInterval, https://pyinterval.readthedocs.io/en/latest/)

Positional parameters:
----------------------
:func: callable that takes a numpy array as parameters and returns a scalar (eg np.mean, np.nanmean, etc)

:signal: signal-like object

:interval: see datazone.interval

Named parameters:
-----------------
:channel: optional, default is None.
    When specified, 'channel' must be a single int value and normal python |nbsp|
    indexing rules apply (i.e. negative values are reverse indices).

    This is used with multi-channel signals (i.e. signals having more than
    one trace) and selects the trace (channel) to which 'func' is applied. |nbsp|

    NOTE: Signal objects (neo.AnalogSignal, DataSignal) are essentially 2D |nbsp|
    numpy arrays with the data organized in COLUMNS.

    In this context, a 'channel' is one column of the signal array, hence it |nbsp|
    is indexed on the second axis (axis 1) of the array.

    Therefore, 'channel' must be in range(-signal.shape[1], signal.shape[1])

Returns:
--------

A python Quantity.

* When 'interval' has a single *sub-interval*:
    * For a single-channel signal, returns a scalar quantity
    * For a multi-channel signal returns a scalar quantity if 'channel' is specified, else a subdimensional array with (signal.ndim - 1) dimensions

* When interval.size > 1 (i.e. has several *sub-intervals*), returns a 2D Quantity array where each *row* contains the result from a *sub-interval*, as above

.. note::
    One can supply only a sub-interval to the 'interval' parameter, obtained through indexing.
"""
    assert isinstance(interval, (DataZone, Interval, neo.Epoch)), f"'interval' expected to be a datazone.Interval, datazone.DataZone or neo.Epoch; instead got a {type(interval).__name__}"

    return epoch_reduce(func, signal, interval, channel)

def interval_average(signal, interval, channel=None):
    return interval_reduce(np.mean, signal, interval, channel) * signal.units

def interval_max(signal, interval, channel=None):
    return interval_reduce(np.max, signal, interval, channel) * signal.units

def interval_min(signal, interval, channel=None):
    return interval_reduce(np.min, signal, interval, channel) * signal.units

def interval_argmax(signal, interval, channel=None):
    return interval_reduce(np.argmax, signal, interval, channel)

def interval_domain_max(signal, interval, channel=None):
    ndx = interval_argmax(signal, interval, channel)
    return signal.times[ndx]

def interval_argmin(signal, interval, channel=None,):
    return interval_reduce(np.argmin, signal, interval, channel)

def interval_domain_min(signal, interval, channel=None):
    ndx = interval_argmin(signal, interval, channel)
    return signal.times[ndx]

def interval_maxmin(signal, interval, channel=None):
    return interval_reduce(sigp.maxmin, signal, interval, channel) * signal.units

def interval_minmax(signal, interval, channel=None):
    return interval_reduce(sigp.minmax, signal, interval, channel) * signal.units

def interval_argmaxmin(signal, interval, channel=None):
    return interval_reduce(sigp.argmaxmin, signal, interval, channel)

def interval_domain_maxmin(signal, interval, channel=None):
    ndx = interval_argmaxmin(signal, interval, channel)
    return tuple(map(lambda x: signal.times[x], ndx))

def interval_argminmax(signal, interval, channel=None):
    return interval_reduce(sigp.argminmax, signal, interval, channel)

def interval_domain_minmax(signal, interval, channel=None):
    ndx = interval_argminmax(signal, interval, channel)
    return tuple(map(lambda x: signal.times[x], ndx))

def interval_slice(signal, interval):
    r"""Signal slice according to the first sub-interval in 'interval'"""
    t0, t1 = interval[0].t0, interval[0].t1

    if t1 == t0:
        return signal[signal.time_index(t0),:]

    return signal.time_slice(t0, t1)

def interval_mid_point(interval: Interval):
    r"""Calculates the mid-point of an interval.
Uses the first sub-interval of 'interval'
"""
    i0, i1 = interval[0].t0, interval[0].t1

    return i0 + (i1-i0)/2


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
    r"""Index of signal sample at the interval midpoint"""
    x = interval_mid_point(interval, duration=duration)

    if not isinstance(x, pq.Quantity):
        x *= signal.times.units

    else:
        x = checkRescale(x, signal.times.units)

    return signal.time_index(x)


def intervals_difference(signal: typing.Union[neo.AnalogSignal, DataSignal],
                         interval0, interval1,
                         func: typing.Optional[typing.Union[typing.Callable, types.FunctionType]] = None,
                         channel: typing.Optional[int]=None,
                         duration:bool = False,
                         subfun: typing.Optional[typing.Union[typing.Callable, types.FunctionType]] = None):
    r"""Similar to cursors_difference(…).
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
    r"""Signal chord slope between two intervals.
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
    r"""Similar to event_amplitude_at_cursors but using intervals.

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
                  cursor: typing.Union[SignalCursor, tuple, DataCursor]) -> typing.Union[neo.AnalogSignal, DataSignal]:
    r"""Returns a slice of the signal corresponding to a cursor's xwindow"""

    if isinstance(cursor, SignalCursor):
        t0 = (cursor.x - cursor.xwindow/2) * signal.times.units
        t1 = (cursor.x + cursor.xwindow/2) * signal.times.units

    elif isinstance(cursor, tuple) and len(cursor) == 2:
        t0, t1 = cursor

    elif isinstance(cursor, DataCursor):
        t0 = cursor.coord - cursor.span/2
        t1 = cursor.span + cursor.span/2

    else:
        raise TypeError(f"Incorrrect cursors specification; expecting a SignalCursor, DataCursor or a 2-tuple of scalars; got {cursors} instead")

    if not isinstance(t0, pq.Quantity):
        t0 *= signal.times.units

    else:
        if not unitsConvertible(t0, signal.times.units):
            raise ValueError(f"t0 units ({t0.units}) are not compatible with the signal's time units {signal.times.units}")

    if not isinstance(t1, pq.Quantity):
        t1 *= signal.times.units

    else:
        if not unitsConvertible(t1, signal.times.units):
            raise ValueError(f"t1 units ({t1.units}) are not compatible with the signal's time units {signal.times.units}")

    if t0 == t1:
        ret = signal[signal.time_index(t0),:]

    else:
        ret = signal.time_slice(t0,t1)

    return ret

# @singledispatch
# def signal_reduce(loc:)

def cursor_reduce(func:types.FunctionType,
                  signal: typing.Union[neo.AnalogSignal, DataSignal],
                  cursor: typing.Union[SignalCursor, tuple, DataCursor, Interval],
                  channel: typing.Optional[int] = None,
                  relative:bool = True) -> pq.Quantity:
    r"""Calculates reduced signal values (e.g. min, max, median etc) across a cursor's window.

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
        When a tuple, its elements (`x` and `window`) represent a notional
            vertical cursor at `x` coordinate, with a horizontal span given by
            `window` such that `x` is at the center of the span.

            Both elements are numeric scalars (that will assume the domain units
            of the signal where the notional cursor is applied), or python Quantities
            (their units are expected to be convertible to the units of the signal's
            domain, e.g. time units for neo.AnalogSignal, etc).

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
    # from copy import deepcopy
    if isinstance(cursor, tuple) and len(cursor) == 2:
        t0, t1 = cursor

    else:
        if isinstance(cursor, Interval):
            t0 = Interval.t0[0].copy()
            t1 = Interval.t1[0].copy()
        else:
            if isinstance(cursor, SignalCursor):
                coord = float(cursor.x)
                span = float(cursor.xwindow)
                if isinstance(cursor.xUnits, pq.Quantity):
                    coord *= cursor.xUnits
                    span *= cursor.xUnits

            elif isinstance(cursor, DataCursor):
                # need copies here, because of possible readjustment
                coord = cursor.coord.copy() if isinstance(cursor.coord, np.ndarray) else float(cursor.coord)
                span = cursor.span.copy() if isinstance(cursor.span, np.ndarray) else float(cursor.span)

            else:
                raise TypeError(f"Incorrrect cursors specification; expecting a SignalCursor, DataCursor, or a 2-tuple of scalars; got {cursor} instead")

            t0, t1 = (coord - span/2, coord + span/2)

    # print(f"cursor_reduce: t0 = {t0}, t1 = {t1}")

    if not isinstance(t0, pq.Quantity):
        t0 *= signal.times.units

    else:
        t0 = checkRescale(t0, signal.times.units)

    if not isinstance(t1, pq.Quantity):
        t1 *= signal.times.units

    else:
        t1 = checkRescale(t1, signal.times.units)

    t0, t1 = min(t0,t1), max(t0,t1)

    # print(f"cursor_reduce: t0 = {t0}, t1 = {t1}")

    if relative:
        t0, t1 = adjust_time_relative_to_signal(signal, t0, t1)

    else:
        if t0 < signal.t_start or t0 > signal.t_stop:
            scipywarn(f"t0 {t0} falls outside signal's domain with start {signal.t_start} and stop {signal.t_stop}")
            return np.nan

        if t1 < signal.t_start or t1 > signal.t_stop:
            scipywarn(f"t1 {t1} falls outside signal's domain with start {signal.t_start} and stop {signal.t_stop}")
            return np.nan

    # print(f"\n\t-> t0 = {t0}, t1 = {t1}")
    if t0 == t1:
        ret = signal[signal.time_index(t0),:]

    else:
        ret = func(signal.time_slice(t0,t1), axis=0)

    if isinstance(channel, int):
        return ret[channel].flatten()

    return ret

def adapt_coordinate_to_lower_boundary(val: typing.Union[numbers.Number, np.ndarray, pq.Quantity],
                        old: typing.Union[numbers.Number, np.ndarray, pq.Quantity],
                        new: typing.Union[numbers.Number, np.ndarray, pq.Quantity]):
    r"""

Parameters:
===========

:val:
    coordinate to be adapted

:old:
    old domain boundary, used at the time the original coordinate was created

:new:
    new domain boundary

Returns:
========

Coordinate adapted to the new domain boundary

"""
    # print(f"adapt_coordinate_to_lower_boundary(val = {val}, new = {new}, old = {old}")

    if new == old:
        ret = val

    # elif val < new:
    #     ret = val + new

    else:
        ret = val - old + new

    # if ret < new:
    #     ret += new
    # print(f"\n\t => ret = {ret}")

    return ret

@singledispatch
def adapt_location_to_lower_domain_bounds(obj, old: typing.Union[
                                        numbers.Number,
                                        np.ndarray,
                                        pq.Quantity
                                        ],
        new: typing.Union[numbers.Number,
                          np.ndarray,
                          pq.Quantity
                          ]
        ) -> object:
    # print(f"\nadapt_location_to_lower_domain_bounds[{type(obj).__name__}]: old = {old}, new = {new}\n")
    raise NotImplementedError(f"adapt_location_to_lower_domain_bounds does not support {type(obj).__name__} location type ")

@adapt_location_to_lower_domain_bounds.register(neo.Epoch)
@adapt_location_to_lower_domain_bounds.register(DataZone)
def _adapt_location_to_lower_domain_bounds_(obj: typing.Union[
                                                            neo.Epoch, DataZone
                                                            ],
                                            old, new):

    # print(f"\nadapt_location_to_lower_domain_bounds[{type(obj).__name__}]: old = {old}, new = {new}\n")

    new_times = list(
        map(
            lambda t: adapt_coordinate_to_lower_boundary(
                t, old.flatten()[0], new.flatten()[0]
                ),
            obj.times
            # list(obj.times)
            )
        )

    # why not this ?!?
    # ret = obj.duplicate_with_new_data()

    ret = type(obj)(times = new_times, durations = obj.durations,
                     units = obj.units, labels = obj.labels,
                     name = obj.name, description = obj.description,
                     array_annotations = obj.array_annotations)
    if isinstance(obj, DataZone):
        ret.relative = obj.relative

    ret.annotations.update(obj.annotations)

    if isinstance(obj, DataZone):
        ret.domain_name = obj.domain_name

    return ret

@adapt_location_to_lower_domain_bounds.register(neo.Event)
@adapt_location_to_lower_domain_bounds.register(DataMark)
@adapt_location_to_lower_domain_bounds.register(TriggerEvent)
def _adapt_location_to_lower_domain_bounds_(obj: typing.Union[neo.Event, # noqa
                                                              DataMark,
                                                              TriggerEvent],
                                            old, new):
    new_times = list(
        map(
            lambda t: adapt_coordinate_to_lower_boundary(
                t, old, new
                ),
            obj.times
            )
        )

    ret = type(obj)(times = new_times,
                    units = obj.units, labels = obj.labels,
                    name = obj.name, description = obj.description,
                    array_annotations = obj.array_annotations)

    ret.annotations.update(obj.annotations)

    if isinstance(obj, DataMark):
        ret.mark_type = obj.mark_type
        ret.domain_name = obj.domain_name

    elif isinstance(obj, TriggerEvent):
        ret.event_type = obj.event_type

    return ret

@adapt_location_to_lower_domain_bounds.register(DataCursor)
def _adapt_location_to_lower_domain_bounds_(obj: DataCursor, old, new): # noqa
    new_coord = adapt_coordinate_to_lower_boundary(obj.coord, old, new)

    return DataCursor(new_coord, span = obj.span, name = obj.name)

@adapt_location_to_lower_domain_bounds.register(SignalCursor)
def _adapt_location_to_lower_domain_bounds_(obj: SignalCursor, old, new, # noqa
                                            axis: int = None):

    if obj.cursorType == SignalCursorTypes.vertical:
        currentBounds = obj.xBounds()
        currentCoord = obj.x

    elif obj.cursorType == SignalCursorTypes.horizontal:
        currentBounds = obj.yBounds()
        currentCoord = obj.y

    else:
        if axis == 0:
            currentBounds = obj.xBounds()
            currentCoord = obj.x

        elif axis == 1:
            currentBounds = obj.yBounds()
            currentCoord = obj.y

        else:
            raise ValueError(f"For crosshair cursors an axis of 0 or 1 must be specified")

    new_coord = adapt_coordinate_to_lower_boundary(currentCoord, old, new)
    boundRange = currentBounds[1] - currentBounds[0]
    newBoundsLo = adapt_coordinate_to_lower_boundary(currentBounds[0])
    newBoundsForAxis = (newBoundsLo, newBoundsLo + boundRange)

    if obj.cursorType == SignalCursorTypes.vertical:
        obj.x = new_coord
        obj.setBounds(None, newBoundsForAxis, obj.yBounds())

        if (
            ((obj.x + obj.xwindow/2) >= newBoundsForAxis[-1])
            or ((obj.x - obj.xwindow/2) < newBoundsForAxis[0])
            ):
            new_xwindow = 0

            if isinstance(obj.xwindow, pq.Quantity):
                new_xwindow *= obj.xwindow.units

            obj.xwindow = new_xwindow

    elif obj.cursorType == SignalCursorTypes.horizontal:
        obj.y = new_coord
        obj.setBounds(None, obj.xBounds(), newBoundsForAxis)

        if (
            ((obj.y + obj.ywindow/2) >= newBoundsForAxis[-1])
            or ((obj.y - obj.ywindow/2) < newBoundsForAxis[0])
            ):
            new_ywindow = 0

            if isinstance(obj.ywindow, pq.Quantity):
                new_ywindow *= obj.ywindow.units

            obj.ywindow = new_ywindow

    else:
        if axis == 0:
            obj.x = new_coord
            obj.setBounds(None, newBoundsForAxis, obj.yBounds())

            if (
                ((obj.x + obj.xwindow/2) >= newBoundsForAxis[-1])
                or ((obj.x - obj.xwindow/2) < newBoundsForAxis[0])
                ):
                new_xwindow = 0

                if isinstance(obj.xwindow, pq.Quantity):
                    new_xwindow *= obj.xwindow.units

                obj.xwindow = new_xwindow

        elif axis == 1:
            obj.y = new_coord
            obj.setBounds(None, obj.xBounds(), newBoundsForAxis)

            if (
                ((obj.y + obj.ywindow/2) >= newBoundsForAxis[-1])
                or ((obj.y - obj.ywindow/2) < newBoundsForAxis[0])
                ):
                new_ywindow = 0

                if isinstance(obj.ywindow, pq.Quantity):
                    new_ywindow *= obj.ywindow.units

                obj.ywindow = new_ywindow

    return obj

@adapt_location_to_lower_domain_bounds.register(Interval)
def _adapt_location_to_lower_domain_bounds_(obj: Interval, old, new):  # noqa

    new_times = list(
        map(
            lambda t: adapt_coordinate_to_lower_boundary(
                t, old, new
                ),
            obj.times
            )
        )

    ret = Interval(times = new_times, units = obj.units, labels = obj.labels,
                    durations = obj.durations, extent = obj.extent,
                    name = obj.name, description = obj.description,
                    segment = obj.segment, array_annotations = obj.array_annotations
                    )

    ret.annotations.update(obj.annotations)

    ret.domain_name = obj.domain_name

    return ret

def adjust_time_relative_to_signal(signal:typing.Union[neo.AnalogSignal, DataSignal], *args) -> typing.Union[pq.Quantity, typing.List[pq.Quantity]]:
    r"""Adjust the domain values supplied in `args` relative to signal's domain limit.
    `args` must contain scalar Quantities with units equal (or convertible to) signal's domain units.

    The values WILL be sorted in increasing order!

    """
    if len(args) == 0:
        scipywarn("No domain values were supplied")
        return

    if not all(isinstance(v, pq.Quantity) and v.size == 1 and unitsConvertible(v, signal.times.units) for v in args):
        raise TypeError(f"Expecting scalar Quantities in {signal.times.units}")

    # if not (isinstance(t, pq.Quantity) and t.size == 1 and unitsConvertible(t, signal.times.units)):
    #     raise TypeError(f"'t' expected to be scalar Quantities in {signal.times.units}")

    args = sorted([checkRescale(t, signal.times.units) for t in args])

    # print(f"\n»»»\nadjust_time_relative_to_signal from {args}\n«««\n")

    ret = list()

    for t in args:
        # not working when t is in the future...
        if t < signal.t_start:
            t += signal.t_start

        elif t > signal.t_stop:
            while t > signal.t_stop:
                t -= signal.t_start

        ret.append(t)

    if len(ret) == 1:
        return ret[0]
    else:
        return ret

@safewrapper
def cursor_max(signal: typing.Union[neo.AnalogSignal, DataSignal],
               cursor: typing.Union[SignalCursor, tuple, DataCursor],
               channel: typing.Optional[int] = None,
               relative: bool=True) -> typing.Union[float, pq.Quantity]:
    r"""The maximum value of the signal across the cursor's window.
    Calls cursor_reduce with np.max as `func` parameter.
    """
    return cursor_reduce(np.max, signal, cursor, channel, relative)

@safewrapper
def cursor_min(signal: typing.Union[neo.AnalogSignal, DataSignal],
               cursor: typing.Union[SignalCursor, tuple, DataCursor],
               channel: typing.Optional[int] = None,
               relative: bool=True) -> typing.Union[float, pq.Quantity]:
    r"""The maximum value of the signal across the cursor's window.
    Calls cursor_reduce with np.min as `func` parameter.
    """
    return cursor_reduce(np.min, signal, cursor, channel, relaive)

@safewrapper
def cursor_argmax(signal: typing.Union[neo.AnalogSignal, DataSignal],
                  cursor: typing.Union[SignalCursor, tuple, DataCursor],
                  channel: typing.Optional[int] = None,
                  relative: bool=True) -> np.ndarray:
    r"""The index of maximum value of the signal across the cursor's window.

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

    return cursor_reduce(np.argmax, signal, cursor, channel, relative)

def cursor_domain_max(signal: typing.Union[neo.AnalogSignal, DataSignal],
                  cursor: typing.Union[SignalCursor, tuple, DataCursor],
                  channel: typing.Optional[int] = None,
                  relative: bool=True) -> pq.Quantity:
    r"""Returns the domain position for the maximum value of the signal"""
    ndx = cursor_argmax(signal, cursor, channel, relative)
    return signal.times[ndx]

@safewrapper
def cursor_argmin(signal: typing.Union[neo.AnalogSignal, DataSignal],
                  cursor: typing.Union[tuple, SignalCursor, DataCursor],
                  channel: typing.Optional[int] = None,
                  relative: bool=True) -> np.ndarray:
    r"""The index of minimum value of the signal across the cursor's window.

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

    return cursor_reduce(np.argmin, signal, cursor, channel, relative)

def cursor_domain_min(signal: typing.Union[neo.AnalogSignal, DataSignal],
                  cursor: typing.Union[tuple, SignalCursor, DataCursor],
                  channel: typing.Optional[int] = None,
                  relative: bool=True) -> pq.Quantity:
    ndx = cursor_argmin(signal, cursor, channel, relative)
    return signal.times[ndx]

@safewrapper
def cursor_maxmin(signal: typing.Union[neo.AnalogSignal, DataSignal],
                  cursor: typing.Union[tuple, SignalCursor, DataCursor],
                  channel: typing.Optional[int] = None,
                  relative: bool=True) -> tuple[np.ndarray]:
    r"""The maximum and minimum value of the signal across the cursor's window.

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

    return cursor_reduce(sigp.maxmin, signal, cursor, channel, relative)

@safewrapper
def cursor_minmax(signal: typing.Union[neo.AnalogSignal, DataSignal],
                  cursor: typing.Union[tuple, SignalCursor, DataCursor],
                  channel: typing.Optional[int]=None,
                  relative: bool=True) -> tuple[np.ndarray]:
    return cursor_reduce(sigp.minmax, signal, cursor, channel, relative)

@safewrapper
def cursor_argmaxmin(signal: typing.Union[neo.AnalogSignal, DataSignal],
                     cursor: typing.Union[tuple, SignalCursor, DataCursor],
                     channel: typing.Optional[int] = None,
                     relative: bool=True) -> tuple[np.ndarray]:
    r"""The indices of signal maximum and minimum across the cursor's window.
    """
    return cursor_reduce(sigp.argmaxmin, signal, cursor, channel, relative)

def cursor_domain_maxmin(signal: typing.Union[neo.AnalogSignal, DataSignal],
                     cursor: typing.Union[tuple, SignalCursor, DataCursor],
                     channel: typing.Optional[int] = None,
                     relative: bool=True) -> tuple[pq.Quantity]:

    ndx = cursor_argmaxmin(signal, cursor, channel, relative)
    return tuple(map(lambda x: signal.times[x], ndx))

@safewrapper
def cursor_argminmax(signal: typing.Union[neo.AnalogSignal, DataSignal],
                     cursor: typing.Union[tuple, SignalCursor, DataCursor],
                     channel: typing.Optional[int]=None,
                     relative:bool = True) -> tuple[np.ndarray]:
    return cursor_reduce(sigp.argminmax, signal, cursor, channel, relative)

def cursor_domain_minmax(signal: typing.Union[neo.AnalogSignal, DataSignal],
                     cursor: typing.Union[tuple, SignalCursor, DataCursor],
                     channel: typing.Optional[int]=None,
                     relative:bool = True) -> tuple[pq.Quantity]:
    ndx = cursor_argminmax(signal, cursor, channel, relative)
    return tuple(map(lambda x: signal.times[x], ndx))

@safewrapper
def cursor_average(signal: typing.Union[neo.AnalogSignal, DataSignal],
                   cursor: typing.Union[tuple, SignalCursor, DataCursor, Interval],
                   channel: typing.Optional[int]=None,
                   relative: bool = True,
                   usenan: bool = False):
    r"""Average of signal samples across the window of a vertical cursor.
    Calls cursor_reduce with np.mean as `func` parameter

    Parameters:
    -----------

    signal: neo.AnalogSignal or datasignal.DataSignal

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

    usenan:bool, default is False; when True, uses np.nanmean

    Returns:
    -------
    A python Quantity with the same units as the signal.

    """
    fcn = np.nanmean if usenan else np.mean
    return cursor_reduce(fcn, signal, cursor, channel, relative)

cursor_mean = cursor_average

@safewrapper
def cursor_value(signal:typing.Union[neo.AnalogSignal, DataSignal],
                 cursor: typing.Union[float, SignalCursor, DataCursor, pq.Quantity, tuple],
                 channel: typing.Optional[int] = None,
                 relative:bool = True):
    r"""Value of signal at the vertical cursor's time coordinate.

    Signal sample values are NOT averaged across the cursor's window.

    Parameters:
    -----------
    signal: neo.AnalogSignal or datasignal.DataSignal

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

    data_index = cursor_index(signal, cursor, relative)

    ret = signal[data_index,:]

    if channel is None:
        return ret

    return ret[channel].flatten() # so that it can be indexed

@safewrapper
def cursor_index(signal:typing.Union[neo.AnalogSignal, DataSignal],
                 cursor: typing.Union[float, SignalCursor, DataCursor, pq.Quantity, tuple],
                 relative: bool = True):
    r"""Index of signal sample at the vertical cursor's time coordinate.

    Parameters:
    -----------
    signal: neo.AnalogSignal or datasignal.DataSignal

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
        t = cursor * signal.times.units

    elif isinstance(cursor, SignalCursor):
        if cursor.cursorType not in (SignalCursorTypes.vertical, SignalCursorTypes.crosshair):
            raise TypeError("Expecting a vertical or crosshair cursor; got %s instead" % cursor.cursorType)

        t = cursor.x * signal.times.units

    elif isinstance(cursor, DataCursor):
        t = cursor.coord
        if isinstance(t, numbers.Number):
            t *= signal.times.units

        elif isinstance(t, pq.Quantity):
            if t.size != 1:
                raise ValueError(f"Expecting a scalar quantity instead, got {t}")

            t = checkRescale(t, signal.times.units)

        else:
            raise TypeError(f"Invalid domain coordinate {t}")

    elif isinstance(cursor, pq.Quantity):
        if cursor.size != 1:
            raise ValueError(f"Expecting a scalar quantity; instead, got {cursor}")

        t = checkRescale(cursor, signal.times.units)

    elif isinstance(cursor, (tuple, list)) and len(cursor) in (2,3) and all([isinstance(c, (numbers.Number, pq.Quantity)) for v in cursor[0:2] ]):
        # cursor parameter sequence
        t = cursor[0]

        if isinstance(t, numbers.Number):
            t *= signal.times.units

        elif isinstance(t, pq.Quantity):
            if t.size != 1:
                raise ValueError(f"Expecting a scalar quantity; instead got {t}")

            t = checkRescale(t, signal.times.units)

    else:
        raise TypeError("Cursor expected to be a float, python Quantity, DataCursor or SignalCursor; got %s instead" % type(cursor).__name__)

    if relative:
        t = adjust_time_relative_to_signal(signal, t)

    data_index = signal.time_index(t)

    return data_index

@safewrapper
def cursors_difference(signal: typing.Union[neo.AnalogSignal, DataSignal],
                       cursor0: typing.Union[SignalCursor, tuple, DataCursor],
                       cursor1: typing.Union[SignalCursor, tuple, DataCursor],
                       func: typing.Optional[typing.Union[typing.Callable, types.FunctionType]] = None,
                       channel: typing.Optional[int] = None,
                       subfun: typing.Optional[typing.Union[typing.Callable, types.FunctionType]] = None,
                       relative:bool = True) -> pq.Quantity:
    r"""Calculates the signal amplitude between two notional vertical cursors.

    amplitude = y1 - y0

    where y0, y1 are the AVERAGE signal values across the windows of cursor0 and
    cursor1

    Parameters:
    -----------
    signal:neo.AnalogSignal, datasignal.DataSignal

    cursor0, cursor1: SignalCursor of vertical type, or (x, window) tuples
        representing, respectively, the cursor's x coordinate (time) and window
        (horizontal extent). When tuples, the `x` and `window` must be numeric
        scalars (float) or scalar python Quantity objects. For details, see the
        documentation for cursor_reduce(…)

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
    # from gui.cursors import SignalCursor as SignalCursor

    if func is None:
        func = cursor_average
        functor = False

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

        # cursorparndx = 2 if functor else 1 # cursor param is 3rd for functors, 2nd otherwise

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
    # below, we use numpy diff, but this will return a 2D array;
    # this is DELIBERATE and is left up to the caller to decide that to do
    # (e.g. call np.squeeze() on the result, if that is suitable)

    kw = {"relative": relative}

    # print(f"In cursors_difference: func = {func}, functor = {functor}")

    if functor:
        if not isinstance(subfun, (typing.Callable, types.FunctionType)):
            raise TypeError(f"When 'func' is a functor, 'subfun' must be a callable or function; got {type(subfun).__name__} instead" )

        data = np.array([func(subfun, signal, c, channel=channel, **kw) for c in (cursor0, cursor1)]) * signal.units

    else:
        data = np.array([func(signal, c, channel=channel, **kw) for c in (cursor0, cursor1)]) * signal.units

    return np.diff(data, axis=0)

@safewrapper
def cursors_distance(signal: typing.Union[neo.AnalogSignal, DataSignal],
                     cursor0: typing.Union[SignalCursor, tuple, DataCursor],
                     cursor1: typing.Union[SignalCursor, tuple, DataCursor],
                     relative:bool = True,
                     samples:bool = True):
    r"""Distance between two cursors.

    NOTE: The distance between two cursors in the signal domain is simply the
            difference between the cursors' x coordinates.

    Parameters:
    -----------
    signal: regularly sampled signal

    cursor0, cursor1: vertical SignalCursor objects or DataCursor objects; these
        do not need to be sorted by their coordinate in the signal domain.

    relative: bool — flag specifying whether the time stamps of the cursors are
                    to be adjusted relative to the limits of the signal's domain;
                    default is True

    samples:bool — flag specifying whether the distance between cursors is to be
        reported in samples (True) or in signal domain units (False); default is
        True

    """
    ret = [cursor_index(signal, c, relative) for c in (cursor0, cursor1)]

    return abs(ret[1]-ret[0]) if samples else abs(signal.times[ret[1]] - signal.times[ret[0]])

@safewrapper
def chord_slope(signal: typing.Union[neo.AnalogSignal, DataSignal],
                t0: typing.Union[float, pq.Quantity],
                t1: typing.Union[float, pq.Quantity],
                w0: typing.Optional[typing.Union[float, pq.Quantity]] = 0.001*pq.s,
                w1: typing.Optional[typing.Union[float, pq.Quantity]] = None,
                channel: typing.Optional[int] = None):
    r"""Calculates the chord slope of a signal between two time points t0 and t1.

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

    if isinstance(w0, numbers.Real):
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

@safewrapper
def cursors_chord_slope(signal: typing.Union[neo.AnalogSignal, DataSignal],
                        cursor0: typing.Union[SignalCursor, tuple, DataCursor, Interval],
                        cursor1: typing.Union[SignalCursor, tuple, DataCursor, Interval],
                        channel: typing.Optional[int] = None,
                        relative:bool = True):
    r"""Signal chord slope between two vertical cursors.

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
        gui.signalviewer.SignalCursor of type "vertical", or a DataCursor

    """
    # from copy import deepcopy
    if not isinstance(cursor0, (SignalCursor, DataCursor, typing.Sequence)):
        raise TypeError(f"Invalid first cursor specified; expecting a SignalCursor or DataCursor; instead, got {type(cursor0).__name__}")

    if not isinstance(cursor1, (SignalCursor, DataCursor, typing.Sequence)):
        raise TypeError(f"Invalid first cursor specified; expecting a SignalCursor or DataCursor; instead, got {type(cursor1).__name__}")

    if isinstance(cursor0, tuple):
        t0 = float(cursor0[0])

    elif isinstance(cursor0, Interval):
        t0 = cursor0.t0[0].copy()

    else:
        if isinstance(cursor0, DataCursor):
            coord = cursor0.coord.copy() if isinstance(cursor0.coord, np.ndarray) else float(cursor0.coord)
            # span = cursor0.span.copy() if isinstance(cursor0.span, np.ndarray) else float(cursor0.span)

        elif isinstance(cursor0, SignalCursor):
            coord = float(cursor0.x)
            # span = float(cursor0.xwindow)
            if isinstance(cursor0.xUnits, pq.Quantity):
                coord *= cursor0.xUnits
                # span *= cursor0.xUnits

        t0 = coord

    if isinstance(t0, float):
        t0 = t0 * signal.times.units

    if isinstance(cursor1, tuple):
        t1 = float(cursor1[0])

    elif isinstance(cursor1, Interval):
        t1 = cursor1.t0[0].copy()

    else:
        if isinstance(cursor1, DataCursor):
            coord = cursor1.coord.copy() if isinstance(cursor1.coord, np.ndarray) else float(cursor1.coord)
            # span = cursor1.span.copy() if isinstance(cursor1.span, np.ndarray) else float(cursor1.span)

        elif isinstance(cursor1, SignalCursor):
            coord = float(cursor1.x)
            # span = float(cursor1.xwindow)
            if isinstance(cursor1.xUnits, pq.Quantity):
                coord *= cursor1.xUnits
                # span *= cursor1.xUnits

        t1 = coord

    if isinstance(t1, float):
        t1 = t1 * signal.times.units

    # y0 = cursor_average(signal, cursor0, channel=channel)
    # y1 = cursor_average(signal, cursor1, channel=channel)

    y0 = signal_average(cursor0, signal, channel=channel)
    y1 = signal_average(cursor1, signal, channel=channel)

    return (y1-y0)/(t1-t0) # ).simplified


def cursor_chord_slope(signal:typing.Union[neo.AnalogSignal, DataSignal],
                       cursor:typing.Union[SignalCursor, DataCursor],
                       channel:typing.Optional[int]=None,
                       relative:bool = True):
    if isinstance(cursor, SignalCursor):
        t0 = (cursor.x - cursor.xwindow/2) * signal.times.units
        t1 = (cursor.x + cursor.xwindow/2) * signal.times.units

    elif isinstance(cursor, DataCursor):
        t0 = cursor.coord - cursor.span/2
        t1 = cursor.coord + cursor.span/2

        if isinstance(t0, numbers.Number):
            t0 *= signal.times.units

        elif isinstance(t0, pq.Quantity):
            t0 = checkRescale(t0, signal.times.units)

        if isinstance(t1, numbers.Number):
            t1 *= signal.times.units

        elif isinstance(t1, pq.Quantity):
            t1 = checkRescale(t1, signal.times.units)

    else:
        raise TypeError(f"Invalid cursor specification: expecting a SignalCursor or a DataCursor instead got a {type(cursor).__name__}")

    if t1 == t0:
        raise ValueError("Cursor xwindow is 0")

    if relative:
        t0, t1 = adjust_time_relative_to_signal(signal, t0, t1)

    else:
        if t0 < signal.t_start or t0 > signal.t_stop:
            scipywarn(f"t0 {t0} fals outside signal's domain with start {signal.t_start} and stop {signal.t_stop}")
            return np.nan

        if t1 < signal.t_start or t1 > signal.t_stop:
            scipywarn(f"t1 {t1} fals outside signal's domain with start {signal.t_start} and stop {signal.t_stop}")
            return np.nan

    v0, v1 = list(map(lambda x: neoutils.get_sample_at_domain_value(signal, x), (t0, t1)))

    # print(f"cursor_chord_slope t0 = {t0}, t1 = {t1}, v0 = {v0}, v1 = {v1}")
    # print(f"t1-t0 = {t1-t0}, v1-v0 = {v1-v0}")

    ret = ((v1-v0) / (t1-t0)).simplified

    if isinstance(channel, int):
        return ret[channel]

    return ret

@safewrapper
def epoch_average(signal: typing.Union[neo.AnalogSignal, DataSignal],
                  epoch: neo.Epoch,
                  intervals: typing.Optional[typing.Union[int, str, typing.Sequence[int], typing.Sequence[str], range, slice]] = None,
                  channel: typing.Optional[int] = None):
    r"""Signal average across an epoch's intervals.

    Parameters:
    -----------
    signal: neo.AnalogSignal or datasignal.DataSignal

    epoch: neo.Epoch

    intervals: optional - when present, specifies which epoch intervals to use
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

@safewrapper
def plot_signal_vs_signal(x: typing.Union[neo.AnalogSignal, neo.Segment, neo.Block], *args, **kwargs):
    r"""Useful for phase plots"""
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


@safewrapper
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
    r"""Generates an axon text file ("*.atf") for use as external waveform.

    The result is useful for Clampex protocols in sweep mode, using external
    waveforms.

    """
    spike_trace = generate_spike_trace(spike_times, start, duration, sampling_frequency,
                         spike_duration, spike_value, asNeoSignal=False)

    np.savetxt(filename, spike_trace)

def generate_ripple_trace(ripple_times, start, duration, sampling_frequency, spike_duration=0.001, spike_value=5000, spike_count=5, spike_isi=0.01, filename=None, atol=1e-12, rtol=1e-12, skipInvalidTimes=True):
    r"""Similar as generate_spike_trace and generate_text_stimulus_file combined.

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


@safewrapper
def generate_spike_trace(spike_times, start, duration, sampling_frequency, spike_duration=0.001, spike_value=5000, atol=1e-12, rtol=1e-12, skipInvalidTimes=True, maxSweepDuration=None, asNeoSignal=True, time_units = pq.s, spike_units=pq.mV, name="Spike trace", description="Synthetic spike trace", **annotations):
    r"""
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


def waveform_signal(extent, sampling_frequency, model_function, *args, **kwargs):
    r"""Generates a signal containing a synthetic waveform, as a column vector.

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
                        the constructor of neo.AnalogSignal or datasignal.DataSignal,
                        used when asSignal is True (see below, for details)

    Keyword parameters of special interest:

        asSignal        : boolean default False; when True, returns a neo.AnalogSignal
                        of datasignal.DataSignal according to the keyword parameter
                        "domain_units" (see below).
                        When False, returns a np.array (column vector).

        domain_units    : Python UnitQuantity or Quantity; default is s.
                        When different from pq.s and asSignal is True, then the
                        function returns a datasignal.DataSignal; othwerise the
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
            returns a datasignal.DataSignal

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


        if checkTimeUnits(domain_units):
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
            return  DataSignal(y, origin=origin, **signalkwargs)

        else:
            return neo.AnalogSignal(y, **signalkwargs)

    return x, y

def event_amplitude_at_cursors(signal:typing.Union[neo.AnalogSignal, DataSignal],
                               cursors:typing.Union[typing.Sequence[tuple], typing.Sequence[SignalCursor]],
                               func:typing.Optional[typing.Callable] = None,
                               channel:typing.Optional[int] = None) -> list:
    r"""
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
        raise TypeError("'func' must be a callable")

def cursors_measure(func: typing.Callable,
                    signal:typing.Union[neo.AnalogSignal, DataSignal],
                    cursors: typing.Union[typing.Sequence[tuple], typing.Sequence[SignalCursor], typing.Sequence[DataCursor]],
                    channel: typing.Optional[int]=None) -> list:
    r"""Calculates a signal measure from signal data at cursors locations.

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

# # NOTE: 2023-06-14 14:38:31
# # migrating to single dispatch paradigm (dispatches on the locator type, which
# # can be a cursor, an epoch, an interval, or NOTE: 2024-02-09 08:50:35 a scalar
# # time quantity (TODO))
# @singledispatch
# def reduce(locator, func:typing.Callable,
#            signal:typing.Union[neo.AnalogSignal, DataSignal],
#            channel:typing.Optional[int]=True,
#            duration:bool=False,
#            loatorIndex:typing.Optional[int] = None):
#     r"""Single-dispatch version of *_reduce functions in this module.
#
# WARNING: this currently is just a springboard for the *_reduce functions already
# defined in the module and delegates to them.
#
# In the future, these functions might be replaced entirely by this function.
# """
#     raise NotImplementedError(f"Function does not support {type(locator).__name__} locators")
#
# @reduce.register(SignalCursor)
# def _(locator, func, signal, channel:int=None,
#       duration:bool=False, locatorIndex:int=None):
#     return cursor_reduce(func, signal, locator, channel=channel)
#
# @reduce.register(tuple)
# def _(locator, func, signal, channel:int=None,
#       duration=False, locatorIndex:int=None):
#     return interval_reduce(func, signal, locator,channel=channel, duration=duration)
#
# @reduce.register(neo.Epoch)
# @reduce.register(DataZone)
# def _(locator, func, signal, channel=None,
#       duration=False, locatorIndex:int=None):
#     return epoch_reduce(func, signal, locator,
#                         index=locatorIndex, channel=channel)
# @singledispatch
def amplitudeMeasure(*args, name:str = "amplitude",
                     channel:int = 0,
                     relative: bool = True) -> DeferredSignalMeasure:
    r"""DeferredSignalMeasure factory for an amplitude of a signal.

    The amplitude is measured as the difference between signal averages at a
    a location, and a baseline. Each of these two locations can be indicated as:
    • a coordinate and a span window centered on the coordinate
    • a DataCursor
    • a vertical SignalCursor

    Operates on a single channel of the signal (default is channel 0).

    Syntax:
    -------
    amplitudeMeasure(refX, refW, locX, locW, name, channel, relative)

    amplitudeMeasure(c0, c1, name, channel, relative)

    Parameters:
    ----------
    refX, refW: float — scalars with the X coordinate (e.g., time) and a span
        window centered on baseX, defining the "baseline" or "reference"

    locX, locW: float — as above, defining the location of the amplitude
        measurement relative to reference

    ref, loc: DataCursor, SignalCursor — cursors defining, respectively, the
        reference (baseline) and the measurement location; NOTE: when SignalCursor
        objects, they must be of vertical type

    name: str — name of this DeferredSignalMeasure; default is "amplitude"

    channel: int — index of the signal's channel where the measurement is performed;
        default is 0 (first channel)

    relative: bool  — flag specifying whether the time stamps of the cursors are
                    to be adjusted relative to the limits of the signal's domain;
                    default is True


    """
    if len(args) == 4:
        if all(isinstance(v, (float, pq.Quantity)) for v in args):
            refX, refW, locX, locW = args
            return DeferredSignalMeasure(cursors_difference,
                                   (DataCursor(refX, refW),
                                    DataCursor(locX, locW)),
                                   name, channel, relative)
        else:
            raise TypeError(f"Expecting four floats or pq.Quantity scalars")

    elif len(args) == 2:
        if all(isinstance(v, (DataCursor, SignalCursor)) for v in args):
            ref, loc = args
            return DeferredSignalMeasure(cursors_difference,
                                  (ref,loc),
                                  name, channel, relative)


def chordSlopeMeasure(*args, name:str="chord_slope", channel:int = 0, relative:bool=True) -> DeferredSignalMeasure:
    r"""DeferredSignalMeasure factory for the slope of a straight line (chord) between two points on the signal.
    The two points can be specified as:
    • two (vertical) SignalCursor or two DataCursor objects
    • a single (vertical) SignalCursor, or a DataCursor; in this case, the two
    points on the signal are the ends of the cursor's horizontal window.

    Operates on a single channel of the signal (default is channel 0).

    Syntax:
    -------
    chordSlopeMeasure(*args, name:str="chord_slope", channel:int = 0, relative:bool=True) -> DeferredSignalMeasure

    Var-positional parameters (*args):
    ----------------------------------
    One or two DataCursor or vertical SignalCursor objects

    Named parameters:
    -----------------
    name: str       — name of the DeferredSignalMeasure object; default is 'chord_slope'

    channel: int    — index of the signal channel; default is 0

    relative: bool  — flag specifying whether the time stamps of the cursors are
                    to be adjusted relative to the limits of the signal's domain;
                    default is True

    """
    raise NotImplementedError

    if all(isinstance(v, (DataCursor, SignalCursor)) for v in args):
        if len(args) == 1:
            return DeferredSignalMeasure(cursor_chord_slope, args[0], name, channel, relative)

        elif len(args) == 2:
            return DeferredSignalMeasure(cursors_chord_slope, args, name, channel, relative)

        else:
            raise SyntaxError(f"Expecting at most two cursors; got {len(args)} instead")
    else:
        raise TypeError(f"Expecting DataCursor or SignalCursor objects in args; instead, got {args}")

@singledispatch
def durationMeasure(c0:typing.Union[DataCursor, SignalCursor], c1: typing.Union[DataCursor, SignalCursor],
                    name: str = "duration", relative: bool = True) -> DeferredSignalMeasure:
    r"""DeferredSignalMeasure factory for the distance between two locations in the signal.
    The locations are specified as two (vertical) SignalCursor or two DataCursor
    objects. Bt default, the distance between them can be reported in signal domain
    units — e.g., time units — but it can be reported in samples.

    Syntax:
    -------
    durationMeasure(c0: typing.Union[DataCursor, SignalCursor], c1: typing.Union[DataCursor, SignalCursor],
                    name: str = "duration", relative: bool = True) -> DeferredSignalMeasure

    Parameters:
    ----------
    c0, c1: DataCursor or SignalCursor (vertical) objects

    name: str       — name of the DeferredSignalMeasure object; default is 'chord_slope'

    relative: bool  — flag specifying whether the time stamps of the cursors are
                    to be adjusted relative to the limits of the signal's domain;
                    default is True
"""
    return DeferredSignalMeasure(cursors_distance, (c0,c1), name, relative)

def membraneTestVClampMeasure(base: typing.Union[DataCursor, SignalCursor],
                              Rs: typing.Union[DataCursor, SignalCursor],
                              Rin: typing.Union[DataCursor, SignalCursor],
                              name:str = "DC Rs Rin",
                              channel: int = 0,
                              relative:bool=True) -> DeferredSignalMeasure:
    r"""DeferredSignalMeasure factory for membrane test in voltage-clamp.
    Calculates DC, Rs and Rin based on three cursors (baseline, Rs and Rin).

    Rs cursor is located on the extremum of the first current transient at the
    start of the membrane potential change during the test; this extremum can be
    a peak (for depolarizing Vm step) or a trough (hyperpolarizing Vm step)

    Returns a tuple (DC, Rs, Rin) where DC is the baseline current, Rs and Rin
    are, respectively, the series and input membrane resistance.
    """

    # NOTE: 2024-02-29 22:37:45 see NOTE: 2024-02-29 22:37:54 for mandatory signature
    def _func_(s, testVmDelta:pq.Quantity, c1, c2, c3, channel:int = 0, relative:bool = True):
        # print(f"_func_:\ns = {s}\nc1 = {c1}\nc2 = {c2}\nc3 = {c3}\ntestVmDelta = {testVmDelta}")
        _dc  = cursor_average(s, c1)
        _rin = (testVmDelta / (cursor_average(s, c3) - _dc)).rescale(pq.megaohm)
        _rs  = (testVmDelta / ((cursor_max(s, c2) if testVmDelta > 0 else cursor_min(s, c2)) - _dc)).rescale(pq.megaohm)

        return (_dc, _rs, _rin)

    # f = functools.partial(_func_, channel=channel, relative=relative)

    return DeferredSignalMeasure(_func_, (base, Rs, Rin), name, channel, relative)

def membraneTestVClampRs(base: typing.Union[DataCursor, SignalCursor],
                   Rs: typing.Union[DataCursor, SignalCursor],
                   name:str = "Rs",
                   channel: int = 0,
                   relative: bool = True) -> DeferredSignalMeasure:

    def _func_(s, c1, c2, testVmDelta:pq.Quantity, channel:int = 0, relative:bool = True):
        _dc  = cursor_average(s, c1)
        _rs  = (testVmDelta / ((cursor_max(s, c2) if testVmDelta > 0 else cursor_min(s, c2)) - _dc)).rescale(pq.megaohm)
        # _rin = (testVmDelta / (cursor_average(s, c3) - _dc)).rescale(pq.megaohm)

        return _rs

    return DeferredSignalMeasure(_func_, (base, Rs), name, channel, relative)


def membraneTestVClampRin(base: typing.Union[DataCursor, SignalCursor],
                   Rin: typing.Union[DataCursor, SignalCursor],
                   name:str = "Rs",
                   channel: int = 0,
                   relative: bool = True) -> DeferredSignalMeasure:

    def _func_(s, c1, c2, testVmDelta:pq.Quantity, channel:int = 0, relative:bool = True):
        _dc  = cursor_average(s, c1)
        # _rs  = (testVmDelta / ((cursor_max(s, c2) if testVmDelta > 0 else cursor_min(s, c2)) - _dc)).rescale(pq.megaohm)
        _rin = (testVmDelta / (cursor_average(s, c3) - _dc)).rescale(pq.megaohm)

        return _rin

    return DeferredSignalMeasure(_func_, (base, Rin), name, channel, relative)


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
    r"""
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

    So maybe the way to go is to use DeferredSignalMeasure and subclasses.






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
            if not unitsConvertible(testVm, pq.V):
                raise TypeError("When a quantity, testVm must have voltage units; got %s instead" % testVm.dimensionality)

            if testVm.size != 1:
                raise ValueError("testVm must be a scalar; got %s instead" % testVm)

        else:
            raise TypeError("When command_signal is None, testVm is expected to be specified as a scalar float or Python Quantity, ; got %s instead" % type(testVm).__name__)

    else:
        # NOTE: 2020-09-30 09:56:30
        # Vin - Vbase is the test pulse amplitude

        vm_signal = s.analogsignals[command_signal]

        if not unitsConvertible(vm_signal, pq.V):
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

        if not unitsConvertible(isi, s.analogsignals[signal].times):
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
    r"""
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
    # should also pass an abf object;
    # find out adc names and units ⇒ recorded signal
    # then for the DAC: dacNames, dacUnits ⇒ "command signal"

    recordsCurrent = False
    recordsPotential = False
    commandIsCurrent = False
    commandIsPotential = False

    if isinstance(signal, (neo.AnalogSignal, DataSignal)):
        recordsCurrent = checkElectricalCurrentUnits(signal)
        recordsPotential = checkElectricalPotentialUnits(signal)

    else:
        raise TypeError(f"'signal' expected a neo.AnalogSignal or DataSignal; instead, got {type(signal).__name__}")

    if not any(recordsCurrent, recordsPotential):
        raise ValueError(f"'signal' had incompatible units {signal.units}")

    if isinstance(command, (neo.AnalogSignal, DataSignal)):
        commandIsCurrent = checkElectricalCurrentUnits(command)
        commandIsPotential = checkElectricalPotentialUnits(command)

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


def trials_sequence_info(*args, return_sorted:bool=False):
    r"""Reveals the temporal order of trials represented by neo.Block objects.

    Returns:
    • DataFrame with the following columns:
        "name" - the Block `name` attribute
        "time" - the Block `rec_datetime` attribute
        "deltaMinutes" - the lapsed time, in minutes, from the start of the first Block
        in `args`

        This information is stored in ascending order of the `rec_datetime` values.

        Drug "incubation" periods may be inferred from the first difference of
        the "deltaMinutes" values.

    • (optionally, and when `return_sorted` is True) a sequence with the
        neo.Block objects ordered by `rec_datetime`


    """
    if len(args) == 0:
        return

    if isinstance(args, (tuple, list, collections.deque)) and len(args) == 1:
        args = args[0]

    if not all(isinstance(v, neo.Block) for v in args):
        raise TypeError("Expecting a sequence of neo.Block objects")

    sorted_blocks = sorted(args, key = lambda x: x.rec_datetime)

    trial_names_times = list(map(lambda x: (x.name, x.rec_datetime), sorted_blocks))

    deltaMinutes = list(map(lambda x: (x[1] - trial_names_times[0][1]).seconds/60, trial_names_times))

    ret = dict()
    ret["name"], ret["time"] = zip(*trial_names_times)
    ret["deltaMinutes"] = deltaMinutes

    if return_sorted:
        return pd.DataFrame(ret), sorted_blocks

    return pd.DataFrame(ret)


def getProtocol(x:typing.Union[neo.Block, pab.pyabf.ABF]) -> ElectrophysiologyProtocol | None:
    r"""Tries to retrieve the protocol used to record the data.
    The outcome depends on whether `x` is a `neo.Block` generated by reading
    a data file created by electrophysiology acquisition software.

    Currently, this function supports only data acquired with Clampex® (part of
    the pClamp® software from MolecularDevices™).

    Support for CED™ Signal® software is under development.

"""
    if not isinstance(x, (neo.Block, pab.pyabf.ABF)):
        raise TypeError(f"Expecting a neo.Block or a pyabf.ABF object; instead, got {type(x).__name__}")

    if isinstance(x, neo.Block) and not pab.sourcedFromABF(x):
        scipywarn("The neo.Block has not been generated directly from ABF data")
        return
        # raise NotImplementedError("The neo.Block has not been generated directly from ABF data")

    if isinstance(x, neo.Block) and getattr(x, "annotations", None) is None or getattr(x, "annotations", {}).get("abf_version", None) is None:
        scipywarn(f"{type(x).__name__} object does not appear to have been created from an ABF file; cannot parse a protocol")
        return
    return pab.ABFProtocol(x)

def __slice_signal__(t0, t1, sg, ch): #, rel):
    r"""Helper function for signal_fit & signal_reduce."""
    # print(f"\n***\n__slice_signal__({t0}, {t1}, rel = {rel})\n\tt_start: {sg.t_start}, t_stop: {sg.t_stop}")
    if isinstance(t0, DeferredSignalMeasure):
        t0_ = t0(sg, channel=ch, relative=rel)
        if isinstance(t0_, pq.Quantity) and not scq.unitsConvertible(t0_, signal.times.units):
            raise ValueError(f"Location measure {t0} generated data with incompatible physical dimensionality {t0_} ")
        t0 = t0_

    if isinstance(t1, DeferredSignalMeasure):
        t1 = t1(sg, channel=ch, relative=rel)
        if isinstance(t1_, pq.Quantity) and not scq.unitsConvertible(t1_, signal.times.units):
            raise ValueError(f"Location measure {t1} generated data with incompatible physical dimensionality {t1_} ")
        t1 = t1_

    if not isinstance(t0, pq.Quantity):
        t0 *= sg.times.units

    else:
        t0 = checkRescale(t0, sg.times.units)

    if not isinstance(t1, pq.Quantity):
        t1 *= sg.times.units

    else:
        t1 = checkRescale(t1, sg.times.units)

    t0, t1 = sorted((t0,t1))

    # print(f"\n\t__slice_signal__ t0 = {t0}, t1 = {t1}")

    # if rel:
    #     t0, t1 = adjust_time_relative_to_signal(sg, t0, t1)
        # t0, t1 = tuple(map(lambda t_: sg.t_start + t_, (t0, t1)))
        # t0, t1 = tuple(map(lambda t: adjust_time_relative_to_signal(sg, t),  (t0, t1)))

    # print(f"\n\t__slice_signal__ adjusted t0 = {t0}, t1 = {t1}\n***\n\n")

    if t0 < sg.t_start:
        scipywarn(f"__slice_signal__: t0 {t0} is earlier than signal's domain start {sg.t_start}",
                  with_traceback=True)
        return np.nan
    if t0 > sg.t_stop:
        scipywarn(f"__slice_signal__: t0 {t0} is later than signal's domain stop {sg.t_stop}",
                  with_traceback=True)
        return np.nan

    if t1 < sg.t_start:
        scipywarn(f"__slice_signal__: t1 {t1} is earlier than signal's domain start {sg.t_start}",
                  with_traceback=True)
        return np.nan

    if t1 > sg.t_stop:
        # scipywarn(f"__slice_signal__: t1 {t1} is later than signal's domain stop {sg.t_stop}",
        #           with_traceback=False)
        t1 = sg.t_stop

    # t0, t1 = sorted((t0,t1))

    # NOTE: 2026-05-04 22:12:55
    # make sure t0, t1 are "scalar-like" arrays
    t0, t1 = tuple(map(lambda x: x.flatten()[0], sorted((t0, t1))))

    # print(f"\n\t__slice_signal__ -> t0 = {t0}, t1 = {t1}:\n\tfor a signal with t_start = {sg.t_start}, t_stop = {sg.t_stop}\n***\n")

    if t0 == t1:
        return sg[sg.time_index(t0),:]

    else:
        return sg.time_slice(t0,t1)

def __do_reduce__(fn, sg, ch):
    kw = dict()

    if not inspect.isbuiltin(fn):
        signature = inspect.signature(fn)
        if "axis" in signature.parameters:
            kw["axis"] = 0

    ret = fn(sg, **kw)

    if isinstance(ch, int):
        ret = ret[ch].flatten()

    # else:
    #     if isinstance(ret, np.ndarray) and ret.size > 1:


    # print(f"__do_reduce__ {fn} will return {ret} ({type(ret)})")

    return ret

def __adjustFitTable__(sg, mdl, ft, ch, aft):
    for coefName, coefValues in aft.items():
        if coefName in ft.index:
            for key in ['Initial Value', 'Lower Bound', 'Upper Bound']:
                if key in coefValues:
                    actor = coefValues[key]

                    if isinstance(actor, str) and hasattr(sg, actor):
                        value = getattr(sg, actor).magnitude

                    elif isinstance(actor, typing.Callable):
                        value = actor(sg[:,ch])

                    elif (isinstance(actor, numbers.Number)
                        or (isinstance(actor, pq.Quantity
                                        and actor.size == 1)
                            )
                        ):
                        value = actor

                    else:
                        raise TypeError(f"Cannot set {key} for {coefName} to {actor}")

                    ft.loc[coefName, key] = value

            kf = coefValues.get("Keep Feasible", None)
            if isinstance(kf, bool):
                ft.loc[coefName, "Keep Feasible"] = kf

        else:
            raise ValueError(f"Invalid ft coefficient name: {coefName} for the {mdl.name} model")

    return ft

def __get_initial_and_bounds__(fT):
        initial = list(fT["Initial Value"])
        bounds = optimize.Bounds(lb=list(fT["Lower Bound"]),
                                    ub=list(fT["Upper Bound"]),
                                    keep_feasible=list(fT["Keep Feasible"])
                                    )

        return initial, bounds

def _construct_signal_from_fitted_curve_(fitCurve, fitResult, fitted_signal):
    if isinstance(fitted_signal, (neo.AnalogSignal, neo.IrregularlySampledSignal)):
        result = neo.AnalogSignal(fitCurve, units = fitted_signal.units,
                                  t_start = fitted_signal.t_start,
                                  sampling_rate = fitted_signal.sampling_rate,
                                  name = f"Fitted {fitted_signal.name}",
                                  )

    elif isinstance(fitted_signal, (DataSignal, IrregularlySampledDataSignal)):
        result = DataSignal(fitCurve, units = fitted_signal.units,
                            domain_units = fitted_signal.domain_units,
                            t_start = fitted_signal.t_start,
                            sampling_rate = fitted_signal.sampling_rate,
                            name = f"Fitted {fitted_signal.name}",
                            domain_name = fitted_signal.domain_name
                            )

    else:
        raise TypeError(f"'fitted_signal' ws expected to be a neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal, IrregularlySampledDataSignal; instead, got a {type(fitted_signal).__name__}")

    result.annotations["ModelFunction"] = fitResult.ModelFunction
    result.annotations["Fit"] = fitResult.Fit.__dict__
    result.annotations["Coefficients"] = dict(zip(fitResult.Coefficients.Names, fitResult.Coefficients.Fitted))
    result.annotations["Coefficients"]["GoF"] = fitResult.Coefficients.GoF.__dict__

    return result

def __do_fit__(sg, mdl, fT, fTadj, ch):
    result = list()
    if len(fTadj) == 0:
        # defer this to below if adjustments are to be made
        initial, bounds = __get_initial_and_bounds__(fT)

    if datatypes.is_vector(sg):
        if len(fTadj):
            fT = __adjustFitTable__(sg, mdl, fT, 0, fTadj)
            initial, bounds = __get_initial_and_bounds__(fT)

        # print(f"initial = {initial}\nbounds = {bounds}")
        fC, fR = crvf.fit_model(sg, mdl, initial, bounds=bounds)

        fCsig = _construct_signal_from_fitted_curve_(fC, fR, sg)

        result.append((fCsig, fR))

    else:
        if isinstance(ch, int):
            if ch < -sg.shape[1] or ch >= sg.shape[1]:
                raise ValueError(f"Invalid channel ({ch}) for a signal with {sg.shape[1]} channels")

            if len(fTadj):
                fT = __adjustFitTable__(sg, mdl, fT, ch, fTadj)
                initial, bounds = __get_initial_and_bounds__(fT)

            fC, fR = crvf.fit_model(sg[:,ch], mdl, initial,
                                    bounds=bounds)

            fCsig = _construct_signal_from_fitted_curve_(fC, fR, sg)

            result.append((fCsig, fR))

        elif ch is None:
            for ch in range(sg.shape[1]):
                if len(fTadj):
                    fT = __adjustFitTable__(sg, mdl, fT, ch, fTadj)
                    initial, bounds = __get_initial_and_bounds__(fT)

                fC, fR = crvf.fit_model(sg[:,ch], mdl, initial,
                                        bounds=bounds)
                fCsig = _construct_signal_from_fitted_curve_(fC, fR, sg[:,ch])
                result.append((fCsig, fR))

        else:
            raise TypeError(f"'channel' expected to be an int or None; instead, got {type(channel).__name__}")

    if len(result) == 1:
        return result[0]

    elif len(result) > 1:
        return result

