# -*- coding: utf-8 -*-
# $Id: locationmeasure $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
    # SPDX-License-Identifier: GPL-3.0-or-later
    # SPDX-License-Identifier: LGPL-2.1-or-later

r"""
    Deferred function calls for signal measures
"""
import sys
import os
import collections
import traceback
import datetime
import numbers
import inspect
import itertools
# import functools
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
import numpy as np
import quantities as pq
import neo
# import h5py
import pandas as pd

from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
from core.datazone import (DataZone, Interval)
from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType, )
from core.triggerprotocols import TriggerProtocol

# from core.prog import (safewrapper, scipywarn, print_styled)

from core import neoutils

# import core.pyabfbridge as pab

from gui.cursors import (DataCursor, SignalCursor)# , SignalCursorTypes)

__module_path__ = os.path.abspath(os.path.dirname(__file__))

@dataclass
class DeferredSignalMeasure:
    r"""Defer calculating a signal measure at a location using a suitable function or functor.

.. |nbsp| unicode:: 0xA0
   :trim:

The ``DeferredSignalMeasure`` object is callable, taking as first argument a signal-like |nbsp|
    object, which will be passed at the *functor* or *function* encapsulated by |nbsp|
    its `func` field, together with the locators specified in the constructor. |nbsp|
    The call also accepts additional parameters to the `func`.

Attributes:
-----------

:func:
    The function or functor with specific signature requirements, used to calculate the signal measure.

    The signature requirements are:

::

    func(loc, fn: typing.Callable,
         signal: typing.Union[neo.AnalogSignal, DataSignal], /,
         channel: int = None, relative: bool)


    func(loc0, loc1, fn: typing.Callable,
         signal: typing.Union[neo.AnalogSignal, DataSignal], /,
         channel: int = None, relative: bool)


    func(loc, fn: typing.Callable, <optional positional parameters> ,
         signal: typing.Union[neo.AnalogSignal, DataSignal], /,
         channel: int = None, relative: bool)


    func(loc0, loc1, fn: typing.Callable, <optional positional parameters> ,
         signal: typing.Union[neo.AnalogSignal, DataSignal], /,
         channel: int = None, relative: bool)




A "suitable" *function* (``func`` in the examples above) takes a primitive numeric |nbsp|
function as argument and uses it to calculate a measure in a ``neo`` signal-like object, |nbsp|
using ALL the supplied |nbsp| locators.

The arguments of ``func`` are:

* one or two location objects,

* a function (Callable) object which operates on ``signal`` **at** the given location ``loc`` or between locations ``loc0`` and ``loc1`` akes the location object and a signal object.

A ``lambda`` function can also be provided here.

Any *<optional positional parameters>* intervening **between** the location arguments |nbsp|
and the ``signal`` argument are specified in the DeferredSignalMeasure's ``posargs`` attribute, |nbsp|
**in the order and with types expected by ``func``**

The ``ephys`` module provides several such functors and functions, all named |nbsp|
as 'signal_*'

See ephys.signal_* family of functions for example of suitable functions

:locations:
    A location object or a sequence of location objects.

    A *location* is an object with one of the following types ('locator' types):

    * ``SignalCursor``

    * ``DataCursor`` This is an abstraction of a SignalCursor, which stores only the cursor's coordinates, NOT its type. |nbsp|
        It *may* represent a vertical or horizontal signal cursor; useful when no SignalViewer axes are available.

    * ``DataZone``

    * ``Interval``

    * ``neo.Epoch``

    * A ``typing.Sequence[typing.Union[SignalCursor, DataCursor, neo.Epoch, DataZone, Interval]]`` |nbsp|
    e.g., a ``tuple`` or ``list`` of any of the above, and homogeneous in the type of its elements.

:name:
    Name of this DeferredSignalMeasure object

:signalNameOrIndex:
    Name or index of signal in a list-like collection such as a neo.Segment's ``analogsignals`` attribute.
    Optional, default is None.

    Determines what to do in the case when an *iterable* of signal objects is passed |nbsp|
    as the first argument when calling DeferredSignalMeasure as a function:

    * When None, the measurement will be performed on *all* signals in the iterable.

    * When not None, the measurement will be performed onthe signal with the specified index or name from the iterable, if found.

    This attribute is ignored when several signal objects are passed as a sequence or arguments |nbsp|
    when calling DeferredSignalMeasure as a function.


:kwargs:
    Named and keyword parameters passed to func *after* location and signal parameters

:deferred_access_chain: a list of tuples that defers access to the elements or members of
    the result value returned from calling this DeferredSignalMeasure instance as a function.

    Each tuple contains an accessor object and a flag indicating if the accessor
is an attribute or an index.

    When an attribute, the accessor MUST be a string, referring to the symbol of
the attribuet *expected* to exist in the result.

    When an index (2nd element if False) the accessor can by *any* hashable object
that the expected result *can use* as index (i.e., an ``int`` for sequences, or
any hashable object — ``str``, ``int``, etc) when result is an instance of a mapping
types such as ``dict``.

    Say you create a DeferredSignalMeasure to get a slice of the signal, but you're only
interested in the first sample of the result to be used in computations performed by
othee DeferredSignalMeasure. Simply calling the DeferredSignalMeasure object as a function
gives you a concrete result which you will then have to index *later* on.

You can "incorporate" this indexing into the DeferredSignalMeasure so that it will be
executed when the DeferredSignalMeasure obect is called


.. note::
    ¹ A signal `channel` is a numeric data vector, not to be confused with |nbsp|
    the `input` or `output` hardware channel that carries the signal in your |nbsp|
    experimental setup. All signals in Scipyen are represented as `neo` |nbsp|
    objects (essentially, 'enhanced' numpy arrays), that store data in |nbsp|
    memory as columns of a matrix: each column (a 1D array, or 'vector') is |nbsp|
    a signal `channel`.

    Normally, all neo signal-like objects have just one such channel (thus |nbsp|
    having shape (M,1) where M is the number of samples in the |nbsp|
    signal, same as the number of rows in the data matrix).

    However, there is no restriction to the number of channels a signal can |nbsp|
    have, and Scipyen frequently uses this feature to store additional data |nbsp|
    (e.g., a "filtered" signal alongside the "raw", unfiltered version of the |nbsp|
    signal as it was recorded). It follows that ALL the channels of a signal |nbsp|
    share the signal's domain (usually, time).

    Due to this layout, the axes of a signal have a very specific meaning:

    axis 0: the domain axis (the signal's **domain** e.g., time).
            All channels in a signal are aligned to this axis, hence an index `𝑚` along this |nbsp|
            axis points to the 𝑚ᵗʰ "row" of data spanning ALL channels. For a signal `sig`, |nbsp|
            this is sig[𝑚,:]. In signal object types supplied by thre ``neo`` package, |nbsp|
            axis 0 is *always* time.

    axis 1: the channel axis.
            An index `𝑛` along this axis points to the |nbsp|
            𝑛ᵗʰ "column" of data (i.e., channel `𝑛`) spanning the entire domain |nbsp|
            of the signal. For a signal `sig`, this is sig[:,𝑛].

    Given a signal `sig`, the sample at sig[𝑚,𝑛] is the unique data sample |nbsp|
        at domain index `𝑚` in channel `𝑛`.


Examples
--------
CAUTION - This section needs to be re-written

::

    from ephys import (DeferredSignalMeasure, signal_average, interval_average,
                        cursors_difference, intervals_difference)

    from datazone import Interval, epoch2intervals



We assume a neo.AnalogSignal object is bound to the symbol 'signal' in the |nbsp|
workspace, and that 'signal' is a voltage-clamp record of the membrane current |nbsp|
containing, say, and evoked excitatory synaptic current (EPSC).

Example 1:
==========

Calculate the average of signal samples at a vertical cursor, which marks |nbsp|
the signal region corresponding to the cursor's x window extended symmetrically |nbsp|
around the cursor's x coordinate. The cursors is bound to a symbol 'cursor' in |nbsp|
the workspace.

::

    c_measure = DeferredSignalMeasure(cursor_average, cursor, "c_measure")

    a = c_measure(signal) # → a quantity array with as many elements as channels in the signal


Example 2:
==========

Same as **Example 1** but using datazone.Interval objects; we assume there is a |nbsp|
neo.Epoch bound to the symbol 'epoch' in the workspace.

To demonstrate, the following two lines generate two intervals based on an |nbsp|
epoch interval labeled "EPSC0Base"; one Interval (`intvl`) encapsulates a start time and a |nbsp|
duration; the other (`intvl2`) encapsulates a start and a stop time (see ``datazone.Interval``)

::

    intvl = epoch2intervals(epoch, "EPSC0Base", duration=True)[0]
    intvl2 = epoch2intervals(epoch, "EPSC0Base")[0]

    i_measure_1 = DeferredSignalMeasure(interval_average, intvl, "i_measure_1")

    i_measure_2 = DeferredSignalMeasure(interval_average, intvl2, "i_measure_2")

    b = i_measure_1(signal)

    c = i_measure_2(signal)

    assert np.all(a == b) # see example (1) regarding 'a'
    assert np.all(a == c)


Example 3:
==========
Obtain a measure at a pair of locations of the same type.

We want to calculate the amplitude of an elicited EPSC, as the difference between |nbsp|
the average membrane current around the "peak" (or nadir) of the EPSC |nbsp|
and the average membrane current BEFORE the stimulus that elicited the EPSC |nbsp|
(i.e., the local baseline).

For this example we assume that 'epoch' contains two intervals, labeled |nbsp|
"EPSC0Base" and "EPSC0Peak", corresponding to the "baseline" and the "peak" regions |nbsp|
as explained. Obviously, the "baseline" occurs BEFORE the "peak".

From this epoch we generate two Interval objects (one each, for "baseline" and |nbsp|
"peak"; note how we access the corresponding epoch intervals by using their labels):

::

    # 'intervals' will be a list of Interval objects
    intervals = [get_epoch_interval(epoch, i, duration=True) for i in ("EPSC0Base", "EPSC0Peak")]

    # For comparison, we also consider two available vertical cursors ("c0", "c1"),
    # indicating the "baseline" and the "peak" regions of the signal.

    # We calculate this measure using the intervals (note we construct the
    # DeferredSignalMeasure and we call it with the signal in a one-line code):

    a = LocalMeasure(intervals_difference, intervals, "i_diff") (signal)

    # For demonstration, we do the same using the cursors:

    b = DeferredSignalMeasure(cursors_difference, [c0, c1], "c_diff")(signal)

    assert np.all(a == b)


Example 4:
==========
To calculate the same measure at the same location in several signals, |nbsp|
you can call the DeferredSignalMeasure on each signal.

Say you want to calculate the input resistance during a *voltage-clamp* recording, |nbsp|
based on a recorded membrane current (the 'signal') and a recorded proxy of the analog command |nbsp|
signal which triggered a boxcar-like change in the membrane potential (the |nbsp|
command voltage, i.e. 'command'). This boxcar waveform (a hyperpolarizing |nbsp|
or depolarizing change in the membrane potential) is the "membrane test".

If no whole-cell compensation is applied, then the membrane current recorded |nbsp|
during the membrane test undergoes a rapid transient change (the "capacitive |nbsp|
transient") before it settles to a new steady-state value, different from the |nbsp|
baseline before the membrane test).

We calculate `Rin` by applying Ohm's law:

V = I×R

⇒ R = V / I

In this case:
V = the amplitude of the boxcar;
I = the *difference* between the membrane current during the steady-state and that |nbsp|
during the baseline before the membrane test boxcar.

We need two DeferredSignalMeasure objects, and two appropriately-placed cursors as locators:

::

    baseline = DeferredSignalMeasure(cursor_average, baseline_cursor, "baseline")

    steady_state = DeferredSignalMeasure(cursor_average, steady_state_cursor, "steady_state")

    # next line calculates the average baseline membrane current before the membrane test boxcar
    i0 = baseline(signal)

    # next line calculates the average baseline potential before the membrane test boxcar
    v0 = baseline(command) # return

    # similarly, for the steady-state membrane current and potential
    i1 = steady_state(signal)
    v1 = steady_state(command)

    # finally, we calculate Rin as (v1 - v0) / (i1 - i0)

Note that in both cases we used cursor_average as the function passed to the |nbsp|
DeferredSignalMeasure functor. Since we are taking a difference between the averages |nbsp|
of signals at two locations, we can be more direct and use just one |nbsp|
DeferredSignalMeasure object (see example (3) above):

::

    delta = DeferredSignalMeasure(cursors_difference, (baseline_cursor, steady_state_cursor), "delta")

    I = delta(signal)
    V = delta(command)

    Rin = V/I # ⇒ this will generate a Quantity in command.units / signal.units
                # e.g. pq.mV / pq/pA
                # Most likely we want the resistance in MOhm (pq.MOhm), therefore
                # we must rescale it, so the last call should be:

    Rin = (V/I).rescale(pq.MOhm)


Finally, a few reminders:
=========================
* Signals are 2D Quantity arrays (with the data represented as column vectors). They MAY have more than one trace (a.k.a "signal channel", not to be confused with a "recording channel"). A trace, therefore is a column in the signal array.

* Functions that calculate a measure at a single location return a Quantity array.

* For signals with just one trace (or `channel`), the result has only one element.

``result[0]`` or, more directly, ``np.squeeze(result)``

* For signals with more than one trace, the result is a subdimensional (1D) Quantity array.

* For situations where a numpy array is constructed from a list comprehension (such as is the case for cursors_difference, intervals_difference) the final result will gain a second axis (hence it will be 2D), even though it only contains one value. In such situation it is recommended to drop the singleton axes.

We can now finish the last example:

::

    Rin = np.squeeze((V/I).rescale(pq.MOhm))  # ⇒ e.g. array(90.1997, dtype=float32) * Mohm

    # This is a SCALAR Quantity (even though it is described as an array, but note the
    # absence of square brackets in its string representation).
    #
    # Indeed:

    assert (Rin.ndim == 0) # ⇒ is True

Changelog:
----------
2024-02-09 09:41:11 made this a DataClass to enable mutations |nbsp|
    WARNING: In order to be fully mutable when locations are specified as |nbsp|
    sequences of scalars, the sequences must also be mutable

"""
    # NOTE: 2024-02-29 22:37:54
    # mandatory signature for func:
    #
    # func(*args, **kwargs) where:
    # *args: signal or signals, and any other positional parameters NOT locators
    # **kwargs: named parameters for func; these MAY be 'relative' and 'channel'
    #   although these two will by supplied in self.__call__ if not present in kwargs
    #
    func: typing.Callable
    locations: typing.Union[typing.Sequence, DataCursor, Interval, SignalCursor, DataZone, neo.Epoch, typing.Self]
    name: str = dataclasses.field(default = "measure")
    signalNameOrIndex: typing.Optional[int|str] = dataclasses.field(default = None)
    channel:typing.Optional[int]  = dataclasses.field(default = None)
    relative:bool = True
    posargs: tuple = dataclasses.field(default_factory = tuple)
    kwargs: dict = dataclasses.field(default_factory=dict)
    deferred_access_chain: list = dataclasses.field(default_factory=list)

    # def __post_init__(self):
    #     # self.deferred_result = MISSING
    #     self.deferred_access_chain = list()

    def defer_access(self, item: object, isattribute: bool = True) -> typing.Self:
        r"""Adds deferred access to future results of a call to self(…).

Returns:
--------
    The instance of this object, with updated 'deferred_access_chain' field.

    Although this *may* seem unnecessary, it allows chaining these calls, e.g.:

::

    lm.defer_access(item1, True).defer_access(item2, False)

.. note::
    To **reset** the deferred access chain, call self.reset_access_chain()

"""
        self.deferred_access_chain.append((item, isattribute))

        return self

    def reset_access_chain(self):
        self.deferred_access_chain.clear()

    def _apply_deferred_access_(self, obj, item, isattribute):
        if isattribute:
            return getattr(obj, item)

        else:
            return obj.__getitem__(item)


    def __call__(self, *args, **kwargs) -> object:
        r"""Executes the location measure object.

.. |nbsp| unicode:: 0xA0
   :trim:

Var-positional parameters (*args):
----------------------------------
Passed to encapsulated function (`func` field); MUST contain a signal or |nbsp|
signals and any additional positional parameters **EXCEPT** locators

Var-keyword parameters (**kwargs):
---------------------------------
Any aditional named or keyword parameters to be passed to `func`.

.. note::
     This **may override** the named/keyword parameters already included in the |nbsp|
     ``kwargs`` field passed at the constructor.

    Typical examples are ``channel`` and ``relative``.

"""
        # print(f"{self.__class__.__name__}<{self.name}>.__call__({args})\n\n\n")
        if len(args) == 0:
            raise ValueError("At least one signal, a iterable of signals, or a neo.Segment must be specified")

        if len(args) == 1:
            if (isinstance(args[0], (typing.Sequence, typing.Iterable))
                and len(args[0]) > 0
                and all(isinstance(s, (neo.AnalogSignal, DataSignal)) for s in args[0])
                ):

                # print(f"{self.__class__.__name__}<{self.name}>.__call__ {type(args[0])}, {self.signalNameOrIndex} =>")
                if isinstance(self.signalNameOrIndex, int):
                    args = (args[0][self.signalNameOrIndex], )
                    # print(f"\n\targs[0] = {args[0]}")

                elif isinstance(self.signalNameOrIndex, str):
                    ndx = neoutils.normalized_index(args[0], self.signalNameOrIndex, silent=True)
                    # print(f"\n\tndx = {ndx}")
                    if isinstance(ndx, int):
                        args = (args[0][ndx], )
                    else:
                        raise ValueError(f"No signal with name or index {self.signalNameOrIndex} was found in the argument")

                else:
                    # print(f"\n\targs[0] = {args[0]}")
                    args = (args[0], )

            elif isinstance(args[0], neo.Segment):
                if isinstance(self.signalNameOrIndex, int):
                    args = (args[0].analogsignals[self.signalNameOrIndex], )

                elif isinstance(self.signalNameOrIndex, str):
                    # print(f"{self.__class__.__name__}<{self.name}>.__call__ {type(args[0])}, {self.signalNameOrIndex} =>")
                    ndx = neoutils.normalized_index(args[0].analogsignals, self.signalNameOrIndex, silent=True)
                    # print(f"\n\tndx = {ndx}")
                    if isinstance(ndx, int):
                        args = (args[0].analogsignals[ndx], )
                    else:
                        raise ValueError(f"No signal with name or index {self.signalNameOrIndex} was found in the argument")
                else:
                    args = tuple(args[0].analogsignals)

            elif not isinstance(args[0], (neo.AnalogSignal, DataSignal)):
                raise TypeError(f"Unexpected type of the first argument: {type(args[0]).__name__}")

        else:
            if not all(isinstance(a, (neo.AnalogSignal, DataSignal)) for a in args):
                raise TypeError("Expecting all arguments to be signal-like objects")


        # NOTE: 2026-05-04 10:42:29
        # apply the measure to each signal, collect in a list;
        # when just one signal is measured, return the first result
        result = list()

        # NOTE: 2026-05-04 21:57:25
        # make sure there are no duplicate named/keyword parameters, but
        # allow overriding those in self.kwargs

        # ATTENTION: 2026-05-04 22:05:38
        # kwargs are COMMON to all calls on each element of args

        # NOTE: 2026-05-04 22:00:49
        # cache the kwargs parameters that would override those in self.kwargs
        kw = dict()

        for key in self.kwargs:
            if key in kwargs:
                kw[key] = kwargs[key]

        # now, add in the parameters stored at construction
        kwargs.update(self.kwargs)

        # finally, restore the cached values, possibly overriding those set at
        # construction
        kwargs.update(kw)

        for arg in args:
            # NOTE: 2026-05-04 10:41:03
            # augment and rearrange arguments to fit the signature of ``func`` i.e.
            # location(s) THEN signal(s)
            fargs = (self.locations,) + self.posargs + (arg,) # NOTE: 62026-05-04 22:31:56 DO NOT UNPACK self.locations; some funcs expect seq of locs
            # if isinstance(self.locations, (list, tuple, collections.deque)):
            #     fargs = tuple(self.locations) + (arg,)
            #
            # else:
            #     fargs = (self.locations,) + (arg,)


            # print(f"{self.__class__.__name__}.call: relative = {self.relative}")
            # print(f"{self.__class__.__name__}.call: func = {self.func}")
            # print(f"{self.__class__.__name__}.__call__ fargs =\n\t{fargs}\n\n\n")
            # print(f"{self.__class__.__name__}.__call__ kwargs = {kwargs}")
            result.append(self.func(*fargs, **kwargs))

        if len(result) == 1:
            result = result[0]

        if len(self.deferred_access_chain):
            for k, daccess in enumerate(self.deferred_access_chain):
                result = self._apply_deferred_access_(result, *daccess)

        return result

