# -*- coding: utf-8 -*-
# $Id: locationmeasure $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
    # SPDX-License-Identifier: GPL-3.0-or-later
    # SPDX-License-Identifier: LGPL-2.1-or-later

r"""
    Deferred function calls for signal measures
"""
# import sys
import os
# import io
import collections
import traceback
# import datetime
# import numbers
# import inspect
# import itertools
import operator
import re
import functools
from functools import (partial, singledispatch, singledispatchmethod) # noqa
# import warnings
import typing
import types
# import difflib
# import re as _re
# from enum import Enum, IntEnum
# from abc import ABC
import dataclasses
from dataclasses import dataclass
import numpy as np
import quantities as pq
import neo
# import h5py
# import pandas as pd

from copy import deepcopy

from core.datasignal import DataSignal
from core.datazone import (DataZone, Interval)
from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType, )
from core.triggerprotocols import TriggerProtocol

from core.prog import (scipywarn, print_styled)
# from core.prog import (safewrapper, scipywarn, print_styled)

from core import neoutils
from core.utilities import eq

# import core.pyabfbridge as pab

from gui.cursors import (DataCursor, SignalCursor)# , SignalCursorTypes)

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class DeferredSignalMeasure: pass # forward declaration
class DeferredComputation: pass # forward declaration

@dataclass
class DeferredOperation:
    r""""""
    op: typing.Callable
    args: tuple = dataclasses.field(default_factory = tuple)
    kwargs: dict = dataclasses.field(default_factory = dict)


    def __post_init__(self) -> None:
        self.placeholder = re.compile(r'<[0-9]*?>')
        self.debug: bool = False

    def resolve(self, objs) -> typing.Self:
        # print(f"\n{self.__class__.__name__}.resolve:\n")
        if isinstance(self.args, str):
            phMatch = self.placeholder.match(self.args)
            if phMatch:
                argMatch = phMatch.string.strip("<").strip(">")
                try:
                    argNdx = int(argMatch)
                except:
                    scipywarn(f"Cannot convert {argMatch} to an int")
                    traceback.print_exc()
                    argNdx = 0

                if isinstance(objs, tuple):
                    if argNdx >=-len(objs) and argNdx < len(objs):
                        arg = objs[argNdx]

                    else:
                        arg = objs
                    new_args = (arg, )
                else:
                    new_args = (self.args, )
            else:
                new_args = (self.args, )

        elif isinstance(self.args, self.__class__):
            new_args = (self.args.resolve(objs), ) # this already creates a copy!

            # print(f"\n\t\t => resolved to {new_args}\n\t{type(new_args)}")

        elif isinstance(self.args, DeferredSignalMeasure):
            resolved = deepcopy(self.args)
            for k, preproc in enumerate(resolved.preprocess):
                resolved.preprocess[k] = preproc.resolve(objs)

            for k, postproc in enumerate(resolved.postprocess):
                resolved.postprocess[k] = postproc.resolve(objs)

            new_args = (resolved, )

        elif isinstance(self.args, typing.Sequence) and len(self.args):
            new_args = list()
            for ka, arg in enumerate(self.args):
                # print(f"{self.__class__.__name__} to resolve arg {arg}\n\t({type(arg)})")
                resolved = arg

                if isinstance(arg, str):
                    phMatch = self.placeholder.match(arg)
                    if phMatch:
                        argMatch = phMatch.string.strip("<").strip(">")
                        try:
                            argNdx = int(argMatch)
                        except:
                            scipywarn(f"Cannot convert {argMatch} to an int")
                            traceback.print_exc()
                            argNdx = 0

                        if isinstance(objs, tuple):
                            if argNdx >=-len(objs) and argNdx < len(objs):
                                resolved = objs[argNdx]

                            else:
                                resolved = objs

                    # print(f"\n\t\t => resolved to {resolved}\n\t{type(resolved)}")

                elif isinstance(arg, self.__class__):
                    resolved = arg.resolve(objs) # this already creates a copy!

                    # print(f"\n\t\t => resolved to {resolved}\n\t{type(resolved)}")

                elif isinstance(arg, DeferredSignalMeasure):
                    # print(f"{self.__class__.__name__} to resolve arg:\n\t{arg}\n\t({type(arg)})")
                    resolved = deepcopy(arg)
                    for k, preproc in enumerate(resolved.preprocess):
                        resolved.preprocess[k] = preproc.resolve(objs)

                    for k, postproc in enumerate(resolved.postprocess):
                        resolved.postprocess[k] = postproc.resolve(objs)

                    # print(f"\n\t\t => resolved to {resolved}\n\t{type(resolved)}")

                elif isinstance(arg, tuple):
                    resolved = list()
                    # print(f"{self.__class__.__name__} to resolve recursively:")

                    for a_ in arg:
                        # print(f"{self.__class__.__name__} to resolve a_:\n\t{a_}\n\t({type(a_)})")
                        res_a = a_
                        if isinstance(a_, str):
                            phMatch = self.placeholder.match(a_)
                            if phMatch:
                                argMatch = phMatch.string.strip("<").strip(">")
                                try:
                                    argNdx = int(argMatch)
                                except:
                                    scipywarn(f"Cannot convert {argMatch} to an int")
                                    # traceback.print_exc()
                                    argNdx = 0

                                if isinstance(objs, tuple):
                                    if argNdx >=-len(objs) and argNdx < len(objs):
                                        res_a = objs[argNdx]

                                else:
                                    res_a = objs

                        elif isinstance(a_, self.__class__):
                            res_a = a_.resolve(objs) # this already crceates a copy !

                        elif isinstance(a_, DeferredSignalMeasure):
                            res_a = deepcopy(a_)
                            for k, preproc in enumerate(res_a.preprocess):
                                res_a.preprocess[k] = preproc.resolve(objs)

                            for k, postproc in enumerate(res_a.postprocess):
                                res_a.postprocess[k] = postproc.resolve(objs)

                        # print(f"\n\t\t => resolved to:\n\t{res_a}\n\t({type(res_a)})")
                        resolved.append(res_a)

                    if len(resolved) == 1:
                        resolved = resolved[0]
                    else:
                        resolved = tuple(resolved)

                new_args.append(resolved)

            new_args = tuple(new_args)

        else:
            new_args = (self.args, )


        ret = self.__class__(self.op, new_args, self.kwargs)
        ret.debug = self.debug
        # print(f"\n\t => return {ret}")
        return ret

    def __call__(self, obj) -> object:
        if self.debug:
            print(f"\n{self.__class__.__name__}__call__(obj={obj}, {self.args}, {self.kwargs})\n\t<with {len(self.args)} var-positional arguments and {len(self.kwargs)} keyword parameters>")
        if self.op in (operator.attrgetter, operator.itemgetter, operator.methodcaller):
            return self.op(*self.args, **self.kwargs)(obj)

        elif isinstance(self.op, np.ufunc):
            return self.op(obj)

        else:
            res_args = list()
            for arg in self.args:
                if isinstance(arg, tuple):
                    if len(arg) == 0:
                        continue

                    elif len(arg) in (2,3) and isinstance(arg[0], DeferredSignalMeasure):
                        if self.debug:
                            print(f"\n\n[{arg[0].name}] arg[0], {type(arg[0])}: {arg[0]}\n\n\t arg[1], {type(arg[1])}: {arg[1]}, {type(arg[1])}")
                        if len(arg) == 2:
                            if isinstance(arg[1], np.ndarray):
                                arg = arg[0](arg[1])
                            else:
                                arg = arg[0](*arg[1])
                        else:
                            if self.debug:
                                print(f"\n\n[{arg[0].name}] arg[2] {arg[2]}, {type(arg[2])}")
                            # NOTE: 2026-05-12 23:09:06 possible BUG will creep out -> to investigate!
                            if isinstance(arg[1], np.ndarray):
                                arg = arg[0](arg[1], **arg[2])
                            else:
                                arg = arg[0](*arg[1], **arg[2])

                        if self.debug:
                            print(f"\n\t[{arg[0].name}] =>=> {arg}\n")

                res_args.append(arg)

            if self.debug:
                print(f"\n=>res_args = {res_args}")

            return self.op(obj, *res_args, **self.kwargs)


@dataclass
class DeferredSignalMeasure:
    r"""Defers calculating a signal measure at a given location.

Aliased to ``DSM`` in this module.

.. |nbsp| unicode:: 0xA0
   :trim:

Applies a suitable function or functor on analog signal-like objects at a given "location" in the signal.

The ``DeferredSignalMeasure`` object is callable, taking as first argument a signal-like |nbsp|
    object, which will be passed at the *functor* or *function* encapsulated by |nbsp|
    its `func` field, together with the locators specified in the constructor. |nbsp|
    The call also accepts additional parameters to the `func`.

Attributes:
-----------

:func:
    Function with specific signature requirements, used to calculate the signal measure.

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

* a function (Callable) object which operates on ``signal`` **at** the given location ``loc`` **or between** locations ``loc0`` and ``loc1``.

A ``lambda`` function can also be provided here.

Any *<optional positional parameters>* intervening **between** the location arguments |nbsp|
and the ``signal`` argument are specified in the DeferredSignalMeasure's ``posargs`` attribute, |nbsp|
**in the order and with types expected by ``func``**

The ``ephys`` module provides several such functors and functions, all named |nbsp|
as 'signal_*'

See ephys.signal_* family of functions for example of suitable functions.

:locations:
    A location object or a sequence of location objects. These will be the first
    positional parmeters passed to ``func`` when this DeferredSignalMeasure is called
    as a function.

    A *location* is an object with one of the following types ('locator' types):

    * ``SignalCursor``

    * ``DataCursor`` This is an abstraction of a vertical or horizontal SignalCursor, which stores only the cursor's coordinates, NOT its type. |nbsp|
        Useful when no SignalViewer axes are available.

    * ``DataZone``

    * ``Interval``

    * ``neo.Epoch``

    * A ``collections.abc.Sequence[typing.Union[SignalCursor, DataCursor, neo.Epoch, DataZone, Interval]]`` |nbsp|
    e.g., a ``tuple`` or ``list`` of any of the above, and *homogeneous* in the type of its elements.

    * A functor generating a *locator* object as above; this includes DeferredSignalMeasure objects or
        sequence of DeferredSignalMeasure objects, with the precondition that each
        of them returns a value in the signal's domain (hence can be used as *locator*
        objects), or a signal (possibly, a region of it).

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

:posargs: a tuple of additional positional arguments, to be passed to ``func``

:kwargs:
    Named and keyword parameters passed to func *after* location and signal parameters

:preprocess: a list of chained operations to be applied to the parameters
    passed to callinf this DeferredSignalMeasure object as a function. Same structure
    as ``postprocess`` (see next).

:postprocess: a list of chained operations to be applied to the
    *result* of the deferred computations performed by ``func`` while calling
    this DeferredSignalMeasure object as a function.

    The operations are "chained" in the sense that the first operation in the
    chain works on the result of ``func``'s execution, and each of the
    subsequent operations is applied to the result of the previous operation.

    Therefore, the *order*  and the *contents* of the operation definitions
    are important.

    An operation is defined by a 3-tuple of the form:

            (operator, parameter_list, keyword_value_dict)

    * ``operator`` is a callable to which the result of the previous computations
        will be passed as first parameter

        Typical operators are the functions defined in the standard Pytyhon module
        ``operator`` (some of whom correspond to algebraic operators of addition,
        multiplication, collection indexing, method calling, etc), the ``getattr``
        builtin function, and some ``numpy`` array functions.

        Lambda functions can also be used here, although **I recommend against it**
        because they cannot be serialized (i.e. pickled), meaning that DeferredSignalMeasure
        objects containing lambda functions cannot be saved to disk for later use!

    * ``parameter_list`` is a list of *aditional* arguments to be passed to ``operator``.

        A special case is when the parameters to the operator also needs to be
        generated dynamically from one of the call arguments
        This list may contain strings of the form "<>" or "<X>" where X is an integer >= 0.

        These strings are placeholders intended to pass to the operator any of
        the signals given to the DeferredSignalMeasure when called as a function.

        The special placeholder "<>" always refers to the first parameter passed to
        the DeferredSignalMeasure() call, and is equivalent to "<0>".

        If there are more parameters passed to the call they can be referred with
        "<1>", "<2>", etc. Any integer X larger than the number of parameters will
        trigger an Exception.


    * ``keyword_value_dict`` is a dict of *additional* named parameter - value pairs
        that will be passed to ``operator``

    Both ``parameter_list`` and ``keyword_value_dict`` may be empty.

    By default ``postprocess`` is an empty list.

    Deferred operations can be added by calling ``self.defer(…)`` or its *alias*
    ``self.do(…)`` (for "Deferred Operation").

    All defined deferred operations can be removed at any time by calling either
    ``self.reset_deferred_postprocess()`` or ``self.postprocess.clear()``.

    **If you know what you are doing**, individual deferred operations can be inserted
    or removed *manually* from the self.postprocess field using
    standard Python ``list`` API.

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
    func: typing.Union[typing.Callable,
                       types.FunctionType,
                       functools.partial,
                       np.ufunc]

    locations: typing.Optional[
                                typing.Union[
                                                typing.Sequence,
                                                DataCursor,
                                                Interval,
                                                SignalCursor,
                                                DataZone,
                                                neo.Epoch,
                                                typing.Self
                                            ]
        ] = dataclasses.field(default = None)
    name: str = dataclasses.field(default = "measure")
    signalNameOrIndex: typing.Optional[int|str] = dataclasses.field(default = None)
    channel:typing.Optional[int]  = dataclasses.field(default = None)
    relative:bool = True

    posargs: tuple = dataclasses.field(default_factory = tuple)
    kwargs: dict = dataclasses.field(default_factory=dict)

    preprocess: list[tuple[typing.Callable, tuple, dict]] = dataclasses.field(default_factory=list)

    postprocess: list[tuple[typing.Callable, tuple, dict]] = dataclasses.field(default_factory=list)

    use_cache: bool = False # needs more work!


    def __post_init__(self) -> None:
        self.placeholder = re.compile(r'<[0-9]*?>')
        # self.cached_result = dataclasses.MISSING
        self.cached_result = dict()
        self.debug: bool = False

    def defer(self, op: typing.Callable, *args, **kwargs) -> typing.Self:
        r"""Appends a deferred process to self.postprocess"""
        # print(f"{self.__class__.__name__}.defer({op}, {args}, {kwargs})")
        return self._add_deferred_process_(op, True, *args, **kwargs)

    def use(self, op: typing.Callable, *args, **kwargs) -> typing.Self:
        r"""Appends a deferred process to self.preprocess"""
        return self._add_deferred_process_(op, False, *args, **kwargs)

    def _add_deferred_process_(self, op: typing.Callable, post:bool = True,
                               *args, **kwargs) -> typing.Self:
        """Appends a deferred operation to the future result of a call to self(…).

Parameters:
-----------
:op: a Callable, a **"deferred operation definition"** tuple (see below), or
    a sequence of **deferred operation definitions**.

    When ``op`` is a single **deferred operation definition** tuple, i.e. no
    further positional parameters are passed, its contents will be appended to
    the ``postprocess`` field and ``**kwargs`` are ignored.

    If, in addition, **all** subsequent positional parameters are also
    **deferred operation definition** tuples, they will also be appended to the
    ``postprocess`` field.

    Examples:

::

    # appends a SINGLE deferred operation calling op(<result>, *opargs, **opkwargs)
    self.defer(op, *opargs, **opkwargs)

    # In the next call:
    # if no opargs are passed:
    #   appends a SINGLE deferred operation calling op1(<result>, *op1args, **op1kwargs)
    #
    # else, if all opargs contain deferred operation tuples, appends op1(<result>, *op1args, **op1kwargs)
    #   AND each of the subsequent definitions in opargs.
    #

    self.defer((op1, op1args, op1kwargs) , *opargs, **opkwargs)

    # NOTE: in both cases, keyword/value parameters are ignored


This is useful for setting up a long chain of deferred operations:

::

    # defines 𝒏 deferred operations (from 1 to 𝒏):

    self.defer(op1, *op1args, **opkwargs).defer(op2, *op2args, **op2kwargs). … .defer(op𝒏, *op𝒏args, **op𝒏kwargs)

    # is the same as:

    self.defer((op1, *op1args, **opkwargs),
               (op2, *op2args, **op2kwargs),
                ⋮,
                (op𝒏, *op𝒏args, **op𝒏kwargs)
              )

Var-positional parameters
-------------------------
:args: comma-separated parameters to be passed to the ``op``, when ``op`` is a Callable.

    These *may* also be:

    * special placeholder strings of the form "<𝒌>", where "𝒌" is an integer;
        during the execution of self.__call__(…) these will be *replaced* with
        the 𝒌ᵗʰ var-positional parameter passed to self.__call__(…)

    * a **deferred operation definition**, which is a tuple

        (sub_op:Callable, args: tuple, kwargs:dict)

        This definition will be *evaluated* during the execution of self.__call__(…).

        **NOTE** that the args in this definition can also contain placeholder strings
        or deferred operation definition tuples, and so on, but apply **CAUTION**
        to deep nesting these because the resulting deep recursions will be harder to debug!

    WARNING: This syntax variant is currently buggy, as it does not play well when
placeholder strings are included in the "opargs"

    I suggest using the less convenient way of chaining calls to self.defer when
uain placeholder strings.

Var-keyword parameters:
-----------------------
:kwargs: <name>=<value> pairs, passed to the ``op``, when ``op`` is a Callable.


Returns:
--------
    The instance of this object, with updated 'postprocess' field,
    allowing chained called such as (but see alternative syntax examples above):

::

    lm.defer(item1, True).defer(item2, False)

.. note::
    1. To **reset** the deferred access chain, call self.reset_deferred_postprocess()
    2. This method is *aliased* to ``self.do``

"""
        target = self.postprocess if post else self.preprocess

        if isinstance(op, typing.Callable):
            dop = DeferredOperation(op, args, kwargs)
            dop.debug = self.debug
            target.append(dop)
            return self

        elif isinstance(op, DeferredOperation):
            op.debug = self.debug
            target.append(op)
            return self

        elif isinstance(op, (tuple, list, collections.deque)):
            # print(f"\nop is {op}")
            if len(op) in (2,3) and isinstance(op[0], typing.Callable):
                dop = DeferredOperation(*op)
                dop.debug = self.debug
                target.append(dop)
                if len(args):
                    for arg in args:
                        if isinstance(arg, tuple) and len(arg) in (2,3) and isinstance(arg[0], typing.Callable):
                            d_ = DeferredOperation(*arg)
                            target.append(d_)
            else:
                for op_ in op:
                    # print(f"\t\t to add {op_}")
                    if isinstance(op_, tuple) and len(op_) in (2,3) and isinstance(op_[0], typing.Callable):
                        d_ = DeferredOperation(*op_)
                        d_.debug = self.debug
                        target.append(d_)

                    elif isinstance(op_, DeferredOperation):
                        op_.debug = self.debug
                        target.append(op_)

                    else:
                        raise TypeError(f"Invalid operator definitions {op_}")

            return self

        else:
            raise TypeError(f"Invalid operator definition {op} {args} {kwargs}")

    # NOTE: 2026-05-10 01:13:35 provide a shortcut alias
    do = defer

    def reset_deferred_preprocess(self) -> None:
        self.preprocess.clear()

    def reset_deferred_postprocess(self) -> None:
        self.postprocess.clear()

    def _exec_deferred_process_(self, obj: object, defop: DeferredOperation) -> object:
        if self.debug:
            print(f"\n{self.__class__.__name__}[{self.name}] DEFERRED PROCESSING:")
            print(f"\n\t[{self.name}]_exec_deferred_process_(obj: {obj} ({type(obj)}), defop: {defop})")

        return defop(obj)


    def __call__(self, *args, **kwargs) -> object:
        r"""Executes the location measure object.

.. |nbsp| unicode:: 0xA0
   :trim:

Var-positional parameters (*args):
----------------------------------
Passed to encapsulated function (`func` field); MUST contain a signal a |nbsp|
sequence of signals, or several comma-separated signal objects, followed by |nbsp|
any additional positional parameters **EXCEPT** locators.

When ``args`` contains more than one signal object, the ``func`` will perform
the same computations on each of them.

Var-keyword parameters (**kwargs):
---------------------------------

The special keyword: "withLocation" = obj, allows overruling ``self.locations``
    **only** for this particular call, as follows:

    * When obj is a *locator* object, it is used directly *in lieu* of ``self.locations``

    * When obj is a function:

        * it should expect a *single* parameter,

        * it should return a *locator* object (neo.Epoch, DataZone,
Interval, DataCursor, SignalCursor) os sequence of *locator* objects,
based on its parameter

        * the *actual* parameter passed to it the current positional parameter (𝒙)
passed in ``args`` that will also be passed to the call to ``self.func``, such that
``self.func`` will be executed with the new location generated by ``obj(𝒙)``

.. note::

    When passed as a function this allows dynamically generating a new location
for ``self.func`` based on the parameters passed to this method. The instance of
DeferredSignalMeasure is NOT modified.

    This is **different** from calling ``self.withLocation``, which generates
a new instance of this object, with a new location.

Any aditional named or keyword parameters to be passed to `func`.

.. note::
     This **may override** the named/keyword parameters already included in the |nbsp|
     ``kwargs`` field passed at the constructor.

    Typical examples are ``channel`` and ``relative``.

"""
        if self.debug:
            print(f"\n*****\n{self.__class__.__name__}[{self.name}].__call__:\n")
            print(f"\n*****\n{self.__class__.__name__}[{self.name}].__call__: -> args = \n\t{args}\n\t({type(args)})\n\t({len(args)} args)")

            print(f"{self.__class__.__name__}[{self.name}].__call__: -> {len(args)} args = ")
            for ka, ia in enumerate(args):
                print(f"\n\targ {ka}: {type(ia)} =\n\t\t{ia}\n")

        if len(args) == 0:
            raise ValueError(f"In {self.__class__.__name__}[{self.name}].__call__: At least one signal, a iterable of signals, or a neo.Segment must be specified")

        if self.use_cache:
            cached_args = self.cached_result.get("args", tuple())
            cached_kwargs = self.cached_result.get("kwargs", dict())

            cached_OK = len(cached_args) == len(args)

            if cached_OK:
                cached_OK &= all(eq(a[0], a[1]) for a in zip(cached_args, args))

            if cached_OK:
                cached_OK = len(cached_kwargs) == len(kwargs)

            if cached_OK:
                cached_OK &= all(eq(k[0], k[1]) for k in zip(cached_kwargs.keys(), kwargs.keys()))

            if cached_OK:
                cached_OK &= all(eq(v[0], v[1]) for v in zip(cached_kwargs.values(), kwargs.values()))

            if cached_OK:
                cached_OK &= self.cached_result.get("result", dataclasses.MISSING) is not dataclasses.MISSING

            if cached_OK:
                if self.debug:
                    print(f"{self.__class__.__name__}[{self.name}] returning cached result")

                return self.cached_result["result"]

        # NOTE: 2026-05-10 01:14:51
        # prepare the signals; if args contain collections of signals then use
        # self.signalNameOrIndex to select the signal from these.
        if len(args) == 1:
            if isinstance(args[0], (neo.AnalogSignal, DataSignal)):
                callargs = (args[0], )

            elif isinstance(args[0], (typing.Sequence, typing.Iterable)):
                if len(args[0]) == 0:
                    raise ValueError(f"In {self.__class__.__name__}[{self.name}].__call__: 'args' is empty !")

                if not all(
                            isinstance(s,
                                       (
                                           neo.AnalogSignal, DataSignal,
                                        )
                                       ) for s in args[0]
                        ):
                    raise TypeError(f"In {self.__class__.__name__}[{self.name}].__call__: All elements in {type(args[0])} must be analog signal-like")

                if isinstance(self.signalNameOrIndex, int):
                    callargs = (args[0][self.signalNameOrIndex], )

                elif isinstance(self.signalNameOrIndex, str):
                    ndx = neoutils.normalized_index(args[0], self.signalNameOrIndex, silent=True)
                    if isinstance(ndx, int):
                        callargs = (args[0][ndx], )
                    else:
                        raise ValueError(f"In {self.__class__.__name__}[{self.name}].__call__: No signal with name or index {self.signalNameOrIndex} was found in the argument")

                else:
                    callargs = (args[0], )

            elif isinstance(args[0], neo.Segment):
                if isinstance(self.signalNameOrIndex, int):
                    callargs = (args[0].analogsignals[self.signalNameOrIndex], )

                elif isinstance(self.signalNameOrIndex, str):
                    ndx = neoutils.normalized_index(args[0].analogsignals, self.signalNameOrIndex, silent=True)
                    if isinstance(ndx, int):
                        callargs = (args[0].analogsignals[ndx], )
                    else:
                        raise ValueError(f"In {self.__class__.__name__}[{self.name}].__call__: No signal with name or index {self.signalNameOrIndex} was found in the argument")
                else:
                    callargs = tuple(args[0].analogsignals)

            elif isinstance(args[0], typing.Callable):
                callargs = (args[0](), )

            elif not isinstance(args[0], (neo.AnalogSignal, DataSignal)):
                raise TypeError(f"In {self.__class__.__name__}[{self.name}].__call__: Unexpected type of the first argument: {type(args[0]).__name__}")

            else:
                callargs = args

        else:
            if self.debug:
                print(f"\n####\n\targs = {args}\n###\n")

            if not all(isinstance(a, (neo.AnalogSignal, DataSignal)) for a in args):
                raise TypeError(f"In {self.__class__.__name__}[{self.name}].__call__: Expecting all arguments to be analog signal-like objects")

            callargs = args


        # NOTE: 2026-05-04 10:42:29
        # apply the measure to each signal, collect results in a list;
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

        withLocation = kwargs.pop("withLocation", None)


        for key in self.kwargs:
            if key in kwargs:
                kw[key] = kwargs[key]

        # now, add in the parameters stored at construction
        kwargs.update(self.kwargs)

        # finally, restore the cached values, possibly overriding those set at
        # construction
        kwargs.update(kw)

        for karg, arg in enumerate(callargs):
            if self.debug:
                print(f"\n\t[{self.name}] processing argument {karg} of type {type(arg)}:\n{arg}")

            # NOTE: 2026-05-04 10:41:03
            # augment and rearrange arguments to fit the signature of ``func`` i.e.
            # location(s) THEN signal(s)
            #
            # NOTE: 62026-05-04 22:31:56 DO NOT UNPACK self.locations;
            # some funcs (might) expect a sequence of locs
            #


            for kpre, preop in enumerate(self.preprocess):
                if self.debug:
                    print(f"\n\t[{self.name}] for argument {karg}, resolving preprocess {kpre}: {preop}\n")
                pre = preop.resolve(args)
                if self.debug:
                    print(f"\n\t[{self.name}] => preprocess {kpre} resolved to:\n{pre}\n")
                arg = self._exec_deferred_process_(arg, pre)

            if withLocation:
                if isinstance(withLocation, typing.Callable):
                    locations = withLocation(arg)

                else:
                    locations = withLocation

            else:
                locations = self.locations

            # REMEMBER:
            # func takes: location, posargs,  args
            # posargs come first so that we can insert a functool.partial before
            # passing the arg; the result of that functool then becomes the first
            # arg after the location, pased to func
            fargs = (locations,) + self.posargs + (arg,)

            ret = self.func(*fargs, **kwargs)

            #  NOTE: analogsignals are not hashable
            # ret = __dsm_call__(self.func, *fargs, **kwargs)

            for kpost, postop in enumerate(self.postprocess):
                if self.debug:
                    print(f"\n\t[{self.name}] for argument {karg}, resolving postrocess {kpost}:\n{postop}\n")
                post = postop.resolve(*args)
                if self.debug:
                    print(f"\n\t[{self.name}] => postprocess {kpost} resolved to:\n{post}\n")
                ret = self._exec_deferred_process_(ret, post)

            # print(f"\n\t[{self.name}] argument {karg} processed => {type(ret)}:\n{ret}\n\n")
            result.append(ret)

        if len(result) == 1:
            result = result[0]

        if self.use_cache:
            self.cached_result = {"args": args,
                                "kwargs": kwargs,
                                "result": result}
        else:
            if len(self.cached_result):
                self.cached_result.clear()

        return result

    def withLocation(self, loc) -> typing.Self:
        ret = deepcopy(self)
        ret.locations = loc
        return ret


@dataclass
class DeferredComputation:
    r"""Deferred computations with values using suitable function or functor.

Aliased to ``DComp`` in this module.

The computations are deferred until concrete data is passed as parameters to calling
this object as a function.

"""
    func: typing.Callable
    name: str = dataclasses.field(default = "measure")

    posargs: tuple = dataclasses.field(default_factory = tuple)
    kwargs: dict = dataclasses.field(default_factory=dict)
    preprocess: list[tuple[typing.Callable, tuple, dict]] = dataclasses.field(default_factory=list)
    postprocess: list[tuple[typing.Callable, tuple, dict]] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        self.debug: bool = False

    def _add_deferred_process_(self, op: typing.Callable, post:bool = True,
                               *args, **kwargs) -> typing.Self:
        """Appends a deferred operation to the future result of a call to self(…).

Parameters:
-----------
:op: a Callable, a **"deferred operation definition"** tuple (see below), or
    a sequence of **deferred operation definitions**.

    When ``op`` is a single **deferred operation definition** tuple, i.e. no
    further positional parameters are passed, its contents will be appended to
    the ``postprocess`` field and ``**kwargs`` are ignored.

    If, in addition, **all** subsequent positional parameters are also
    **deferred operation definition** tuples, they will also be appended to the
    ``postprocess`` field.

    Examples:

::

    # appends a SINGLE deferred operation calling op(<result>, *opargs, **opkwargs)
    self.defer(op, *opargs, **opkwargs)

    # In the next call:
    # if no opargs are passed:
    #   appends a SINGLE deferred operation calling op1(<result>, *op1args, **op1kwargs)
    #
    # else, if all opargs contain deferred operation tuples, appends op1(<result>, *op1args, **op1kwargs)
    #   AND each of the subsequent definitions in opargs.
    #

    self.defer((op1, op1args, op1kwargs) , *opargs, **opkwargs)

    # NOTE: in both cases, keyword/value parameters are ignored


This is useful for setting up a long chain of deferred operations:

::

    # defines 𝒏 deferred operations (from 1 to 𝒏):

    self.defer(op1, *op1args, **opkwargs).defer(op2, *op2args, **op2kwargs). … .defer(op𝒏, *op𝒏args, **op𝒏kwargs)

    # is the same as:

    self.defer((op1, *op1args, **opkwargs),
               (op2, *op2args, **op2kwargs),
                ⋮,
                (op𝒏, *op𝒏args, **op𝒏kwargs)
              )

Var-positional parameters
-------------------------
:args: comma-separated parameters to be passed to the ``op``, when ``op`` is a Callable.

    These *may* also be:

    * special placeholder strings of the form "<𝒌>", where "𝒌" is an integer;
        during the execution of self.__call__(…) these will be *replaced* with
        the 𝒌ᵗʰ var-positional parameter passed to self.__call__(…)

    * a **deferred operation definition**, which is a tuple

        (sub_op:Callable, args: tuple, kwargs:dict)

        This definition will be *evaluated* during the execution of self.__call__(…).

        **NOTE** that the args in this definition can also contain placeholder strings
        or deferred operation definition tuples, and so on, but apply **CAUTION**
        to deep nesting these because the resulting deep recursions will be harder to debug!

    WARNING: This syntax variant is currently buggy, as it does not play well when
placeholder strings are included in the "opargs"

    I suggest using the less convenient way of chaining calls to self.defer when
uain placeholder strings.

Var-keyword parameters:
-----------------------
:kwargs: <name>=<value> pairs, passed to the ``op``, when ``op`` is a Callable.


Returns:
--------
    The instance of this object, with updated 'postprocess' field,
    allowing chained called such as (but see alternative syntax examples above):

::

    lm.defer(item1, True).defer(item2, False)

.. note::
    1. To **reset** the deferred access chain, call self.reset_deferred_postprocess()
    2. This method is *aliased* to ``self.do``

"""
        target = self.postprocess if post else self.preprocess

        if isinstance(op, typing.Callable):
            dop = DeferredOperation(op, args, kwargs)
            dop.debug = self.debug
            target.append(dop)
            return self

        elif isinstance(op, DeferredOperation):
            op.debug = self.debug
            target.append(op)
            return self

        elif isinstance(op, (tuple, list, collections.deque)):
            # print(f"\nop is {op}")
            if len(op) in (2,3) and isinstance(op[0], typing.Callable):
                dop = DeferredOperation(*op)
                dop.debug = self.debug
                target.append(dop)
                if len(args):
                    for arg in args:
                        if isinstance(arg, tuple) and len(arg) in (2,3) and isinstance(arg[0], typing.Callable):
                            d_ = DeferredOperation(*arg)
                            target.append(d_)
            else:
                for op_ in op:
                    # print(f"\t\t to add {op_}")
                    if isinstance(op_, tuple) and len(op_) in (2,3) and isinstance(op_[0], typing.Callable):
                        d_ = DeferredOperation(*op_)
                        d_.debug = self.debug
                        target.append(d_)

                    elif isinstance(op_, DeferredOperation):
                        op_.debug = self.debug
                        target.append(op_)

                    else:
                        raise TypeError(f"Invalid operator definitions {op_}")

            return self

        else:
            raise TypeError(f"Invalid operator definition {op} {args} {kwargs}")

    def defer(self, op: typing.Callable, *args, **kwargs) -> typing.Self:
        r"""Appends a deferred process to self.postprocess"""
        return self._add_deferred_process_(op, True, *args, **kwargs)

    def use(self, op: typing.Callable, *args, **kwargs) -> typing.Self:
        r"""Appends a deferred process to self.preprocess"""
        return self._add_deferred_process_(op, False, *args, **kwargs)

    def reset_deferred_preprocess(self) -> None:
        self.preprocess.clear()

    def reset_deferred_postprocess(self) -> None:
        self.postprocess.clear()

    # def _exec_deferred_process_(self, obj, op, opargs, opkwargs):
    #     return op(obj, *opargs, **opkwargs)

    # NOTE: 2026-05-10 01:13:35 provide a shortcut alias
    do = defer

    def _exec_deferred_process_(self, obj: object, defop: DeferredOperation) -> None:
        if self.debug:
            print(f"\n{self.__class__.__name__}[{self.name}] DEFERRED PROCESSING:")
            print(f"\n\t[{self.name}]_exec_deferred_process_(obj: {obj} ({type(obj)}), defop: {defop})")

        return defop(obj)

    def __call__(self, *args, **kwargs) -> object:
        if len(args) == 0:
            raise ValueError("At least one operand must be specified")

        kw = dict()
        for key in self.kwargs:
            if key in kwargs:
                kw[key] = kwargs[key]
        kwargs.update(self.kwargs)
        kwargs.update(kw)


        for kpre, preop in enumerate(self.preprocess):
            if self.debug:
                print(f"\n\t[{self.name}] for argument {karg}, resolving preprocess {kpre}: {preop}\n")
            pre = preop.resolve(args)
            if self.debug:
                print(f"\n\t[{self.name}] => preprocess {kpre} resolved to:\n{pre}\n")
            arg = self._exec_deferred_process_(arg, pre)

        fargs = args + self.posargs

        result = self.func(*fargs, **kwargs)

        for kpost, postop in enumerate(self.postprocess):
            if self.debug:
                print(f"\n\t[{self.name}] for argument {karg}, resolving postrocess {kpost}:\n{postop}\n")
            post = postop.resolve(*args)
            if self.debug:
                print(f"\n\t[{self.name}] => postprocess {kpost} resolved to:\n{post}\n")
            result = self._exec_deferred_process_(result, post)

        return result


@dataclass
class DeferredCallChain:
    r"""Deferred call chain funcs[𝒌](funcs[𝒌-1](...(funcs[0](arg)))).




All functions (Callables) in funcs must accept a single parameter,
which is the result of calling the preceding function, or, in the
case of the first func in the chain, the unique parameter passed on
to self.__call__.

This can be implemented by passing combinations of functools.partial objects
and functions in the standard Python module ``operator``, thereby 'reducing'
calls that expect more than one parameter to a call expecting a single one.

"""
    funcs: typing.Sequence[
            typing.Union[
                typing.Callable,
                types.FunctionType,
                functools.partial,
                np.ufunc
            ]
        ]

    def __call__(self, obj: object): #*args, **kwargs):
        r"""
``obj`` is passed to the  *first* function in ``funcs``, the result of which is
    passed to the *second* function in ``funcs``, and so on.

When no funcs are defined, returns obj
"""
        result = obj
        for func in self.funcs:
            result = func(result)

        return result




@functools.cache
def __dsm_call__(func, *args, **kwargs):
    r"""Defined here, but won't work with numpy arrays, as they are not hashable.

Python Quantity and signal-like object types ALL derive from numpy arrays!

Therefore don't bother using this for anything other than Python POD types.
"""
    return func(*args, **kwargs)

def itemGetter(name: str = "ItemGetter"):
    return DeferredComputation(operator.itemgetter, name=name)


def itself(x, *args, **kwargs):
    r"""A noop to return the argument passed onto it.

Useful for adding deferred ops to a DeferredSignalMeasure"""
    return x


DSM     = DeferredSignalMeasure
DComp   = DeferredComputation
DOp     = DeferredOperation

__all__ = ("DeferredSignalMeasure", "DSM", "DeferredOperation", "DOp", "DeferredComputation", "DComp", "itself")
