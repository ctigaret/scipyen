# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Utilities for programming with traitlets.
NOTE: 2022-01-29 13:32:21
There are issues when trying to implement traitlets for collection's CONTENTS,
see docstring in scipyen_traitlets module (FIXME/TODO 2022-01-29 13:29:19)
# NOTE: 2022-11-03 14:36:21
I'm sure there are lots of BUG(s) and/or redundant code - definitely needs
cleaning up...
"""

import enum, os
from enum import (EnumMeta, Enum, IntEnum, )
import contextlib, traceback, dataclasses

from inspect import (getmro, isclass, isfunction, signature,)
import quantities as pq
import numpy as np
from types import new_class
import typing
from collections import deque
from functools import (partial, partialmethod)

import qtpy
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
    # from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip
    # from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

import traitlets

from traitlets.utils.bunch import Bunch as Bunch
from traitlets import (TraitType, HasTraits, Bool, All, observe)
from traitlets import (HasTraits, MetaHasTraits, TraitType, All, Any, Bool, CBool, Bytes, CBytes,
    Dict, Enum, Set, Int, CInt, Long, CLong, Integer, Float, CFloat,
    Complex, CComplex, Unicode, CUnicode, CRegExp, TraitError, Union, Undefined,
    Type, This, Instance, TCPAddress, List, Tuple, UseEnum, ObjectName,
    DottedObjectName, CRegExp, ForwardDeclaredType, ForwardDeclaredInstance,
    link, directional_link, validate, observe, default,
    observe_compat, BaseDescriptor, HasDescriptors, Container,
    )
#, EventHandler,
    #)

import numpy as np
from core.vigra_patches import vigra
import pandas as pd
import neo
import quantities as pq
from core import datasignal
from core.scipyen_quantities import unitsConvertible
from core.utilities import gethash, safe_identity_test
from .prog import (timefunc, processtimefunc, brief_repr, print_styled)

# NOTE: ObjectList in recent neo versions: SpikeTrainList, Block.segments
if neo.__version__ >= '0.13.0':
    from neo.core.objectlist import ObjectList as NeoObjectList

else:
    NeoObjectList = list # alias for backward compatibility :(


# NOTE :2021-08-20 09:50:52
# to figure out traitlets classes use the following idioms:
#
#    for klass in vars(traitlets).values():
#        if inspect.isclass(klass) and issubclass(klass, traitlets.TraitType):
#            print(klass)
#
#    for klass in vars(traitlets).values():
#        if inspect.isclass(klass) and issubclass(traitlets.Instance):
#            print(klass)

from core.prog import safewrapper
#from core.traitcontainers import DataBag # doesn't work because of recursion

# NOTE: 2021-08-20 15:29:02
# below, type is a placeholder for types NOT defined in this module
# e.g. not imported
# in particular this is the case for traitcontainer.DataBag, TriggerEvent, etc

def traitlet_delete(self_instance, owner_instance):
    r"""Wraps descriptor __delete__
    Fails silently when owner is of wrong type
    """
    if hasattr(owner_instance, "remove_trait") and hasattr(owner_instance, "_trait_values") and hasattr(owner_instance, "traits"):
        if self_instance.name in owner_instance.traits():
            trait_to_remove = owner_instance.traits()[self_instance.name]
            owner_instance.remove_trait(self_instance.name, trait_to_remove)
            old_value = owner_instance._trait_values.pop(self_instance.name, None)
            owner_instance._notify_trait(self_instance.name, old_value, Undefined,
                                         change_type="removed")

def traitlet_set_scipyen_object_lists(instance, obj, value):
    from core import datatypes # noqa
    new_value = instance._validate(obj, value)
    # print(f"\n\n***\ntraitlet_set_scipyen_object_lists: -> validated value = {value} => new_value = {new_value}")
    new_hash = gethash(new_value)
    silent = True
    change_type = "modified"

    if instance.name and instance.name in obj._trait_values and instance.name in obj.traits():
        old_value = obj._trait_values[instance.name]
        # print(f"\n\told_value = {old_value}")
        if not instance.hashed:
            instance.hashed = gethash(old_value)
        silent = False
    else:
        change_type="new"
        old_value = instance.default_value
        if not instance.hashed:
            instance.hashed = new_hash
        silent=False

    try:
        klass = getattr(instance, "klass", None)
        # print(f"{print_styled(f'{instance.__class__.__name__}.set: klass = {klass};\n\told_value: {old_value}\n\tnew_value: {new_value}', color='yellow')}")
        check_klass = lambda v: (  # noqa
            isinstance(v, klass) if (
                isinstance(klass, type) or (isinstance(klass, tuple) and all(isinstance(k, type) for k in klass))
                ) else False
            )
        check_Qt_object = lambda v: (isinstance(v, QtCore.QObject) # noqa
                                    or (__has_PySide6__ and isinstance(v, type) and
                                        (hasattr(v, "setupUi") or
                                        issubclass(v, Shiboken.Object)
                                        )
                                        )
                                    ) # noqa

        if any(not check_klass(v) for v in (new_value, old_value)):
            # print(f"\n\nclass change")
            if not instance.name or instance.name not in obj._trait_values or instance.name not in obj.traits():
                change_type = "new"

                if check_Qt_object(new_value):
                    obj._trait_values[instance.name] = new_value
                    obj._notify_trait(instance.name, old_value, new_value,
                                    change_type = change_type)
                    return

            else:
                change_type = "modified"

            instance.hashed = new_hash
            obj._trait_values[instance.name] = new_value
            obj._notify_trait(instance.name, old_value, new_value,
                            change_type = change_type)
            return

        # NOTE: 2021-08-19 16:17:23
        # check for change in contents
        if silent:
            silent = bool(old_value == new_value)

    except:
        traceback.print_exc()
        silent = False

    if not silent:
        instance.hashed = new_hash
        obj._trait_values[instance.name] = new_value
        obj._notify_trait(instance.name, old_value, new_value,
                            change_type=change_type)

#@timefunc
def traitlet_set(instance, obj, value):
    r"""Overrides traitlets.TraitType.set to check for special hash.
    This is supposed to also detect changes in the order of elements in sequences.
    WARNING: Slows down execution
    """
    # NOTE: 2025-06-14 13:39:57 in PySide6 I need to deal with
    # Shiboken.ObjectType and with Ui_* types created by loadUiType
    # also, QObject instances should be left alone

    from core import datatypes
    klass = getattr(instance, "klass", None)
    # check_klass = lambda v: isinstance(v, klass) if (isinstance(klass, type) or (isinstance(klass, tuple) and all(isinstance(k, type) for k in klass))) else False # noqa
    check_Qt_object = lambda v: (isinstance(v, QtCore.QObject) # noqa
                                 or (__has_PySide6__ and isinstance(v, type) and
                                     (hasattr(v, "setupUi") or
                                      issubclass(v, Shiboken.Object)
                                      )
                                     )
                                 ) # noqa

    new_value = value # skip validation
    if hasattr(instance, "default_value"):
        old_value = instance.default_value

    silent = True

    change_type="modified"
    # if any(not check_klass(v) for v in (new_value, old_value)):
    #     if not instance.name or instance.name not in obj._trait_values or instance.name not in obj.traits():
    #         change_type = "new"
    #         old_value = instance.default_value
    #         if check_Qt_object(new_value):
    #             obj._trait_values[instance.name] = new_value
    #             obj._notify_trait(instance.name, old_value, new_value,
    #                             change_type = change_type)
    #             return
    #
    #     else:
    #         change_type = "modified"

    if instance.name and instance.name in obj._trait_values and instance.name in obj.traits():
        old_value = obj._trait_values[instance.name]
    else:
        change_type = "new"
        old_value = instance.default_value
        if check_Qt_object(new_value):
            obj._trait_values[instance.name] = new_value
            obj._notify_trait(instance.name, old_value, new_value,
                            change_type = change_type)
            return

        if not(check_Qt_object(old_value)) or not instance.hashed:
            instance.hashed = gethash(old_value)

        silent = False

    klass = getattr(instance, "klass", None)

    # check_klass = lambda v: isinstance(v, klass) if (isinstance(klass, type) or (isinstance(klass, tuple) and all(isinstance(k, type) for k in klass))) else False

    if klass is not type(None) and (new_value is None and old_value is None):
        return

    if check_Qt_object(new_value):
        return

    # new_hash = gethash(new_value)

    # NOTE: 2023-06-14 08:49:55
    # always notify here - this is relevant, because:
    # a) notifies when an existing trait is set to None
    # b) notifies when a new trait with underlying value of None is set
    # therefore this will enable e.g., showing up symbols bound to None, in
    # any monitored mappings (such as the workspace)

    # if (klass is not type(None) and (new_value is None or old_value is None)) or any(not check_klass(v) for v in (new_value, old_value)):
    #     if not instance.name or instance.name not in obj._trait_values or instance.name not in obj.traits():
    #         change_type = "new"
    #         instance.hashed = gethash(new_value)
    #         obj._trait_values[instance.name] = new_value
    #         obj._notify_trait(instance.name, old_value, new_value,
    #                         change_type = change_type)
    #         return
    #     else:
    #
    #         change_type = "modified"

    try:
        # print(f"{instance.__class__.__name__} set: -> old_value = {old_value}, new_value = {new_value}")
        if datatypes.is_iterable(new_value):
            if datatypes.is_iterable(old_value):
                try:
                    dLengths = len(old_value) != len(new_value)
                except: # noqa
                    dLengths = True

                if dLengths:
                    silent = False
                    change_type = "modified"

        if silent:
            new_hash = gethash(new_value)
            # old_hash = gethash(old_value)
            silent = bool(new_hash == instance.hashed)

    except:
        traceback.print_exc()
        # if there is an error in comparing, default to not notify
        silent = True


    if not silent:
        instance.hashed = gethash(new_value)
        obj._trait_values[instance.name] = new_value
        obj._notify_trait(instance.name, old_value, new_value,
                          change_type = change_type)

def _dynatrtyp_exec_body_(ns, klass,
                          setfn = traitlet_set,
                          delfn = traitlet_delete,
                          **kwargs):
    # NOTE: 2026-06-12 16:02:56
    # ns is supplied by types.new_class() function!!!!
    # and must be the ONLY parameter to exec_body in new_class
    # therefore this function must ALWAYS be used as a partial
    ns["info_text"]="Trait that is sensitive to changes in data contents"
    ns["klass"] = klass
    ns["hashed"] = None
    ns["set"] = setfn
    ns["__delete__"] = delfn
    for key, val in kwargs.items():
        ns[key] = val

#@safewrapper
def adapt_args_kw(x, args, kw, allow_none): # where is this used ?!?
    # NOTE: 2020-09-05 14:23:43 some classes need special treatment for
    # their default constructors (ie when *args and **kw are empty)
    # so far we plan to implement this for the following:
    # vigra.VigraArray, vigra.AxisInfo, vigra.AxisTags,
    # neo.ChannelIndex, neo.AnalogSignal, neo.IrregularlySampledSignal,
    # neo.ImageSequence, neo.SpikeTrain
    # datasignal.DataSignal, datasignal.IrregularlySampledDataSignal,
    # pandas.Series, pandas.DataFrame
    # TODO 2021-08-20 14:37:44
    # include vigra Kernel1D/2D, Chunked_Array_Base
    if isinstance(x, vigra.AxisInfo):
        if "key" not in kw:
            kw["key"] = x.key

        if "typeFlags" not in kw:
            kw["typeflags"] = x.typeFlags


        if "resolution" not in kw:
            kw["resolution"] = x.resolution

        if "description" not in kw:
            kw["description"] = x.description

    elif isinstance(x, vigra.AxisTags):
        if len(args) == 0:
            args = (x, ) # copy c'tor

    elif isinstance(x, vigra.VigraArray):
        if len(args) == 0:
            args = (x, ) # can be a copy constructor

        if "dtype" not in kw:
            kw["dtype"] = x.dtype

        if "order" not in kw:
            kw["order"] = x.order

        if "axistags" not in kw:
            kw["axistags"] = None # calls VigraArray.defaultAxistags or uses x.axistags if they exist

    elif isinstance(x, (neo.AnalogSignal, datasignal.DataSignal)):
        if len(args) == 0:
            args = (x,) # takes units & time units from x

        for attr in x._necessary_attrs:
            if attr[0] != "signal":
                if attr[0] not in kw:
                    kw[attr[0]] = getattr(x, attr[0])

    elif isinstance(x, (neo.IrregularlySampledSignal, datasignal.IrregularlySampledDataSignal)):
        if len(args) < 2:
            args = (x.times, x,)

        for attr in x.__class__._necessary_attrs:
            if attr[0] not in ("times", "signal"):
                if attr[0] not in kw:
                    kw[attr[0]] = getattr(x, attr[0], None)

    elif isinstance(x, neo.SpikeTrain):
        if len(args)  == 0:
            args = (x.times, x.t_stop,)

        for attr in x._necessary_attrs:
            if attr[0] not in ("times", "t_stop"):
                if attr[0] not in kw:
                    kw[attr[0]] = getattr(x, attr[0], None)

    elif isinstance(x, neo.ImageSequence):
        if len(args) == 0:
            args = (x, )

        for attr in x._necessary_attrs:
            if attr[0] != "image_data":
                if attr[0] not in kw:
                    kw[attr[0]] = getattr(x, attr[0], None)

    elif isinstance(x, (neo.Segment, neo.Block)):
        if len(args) == 0:
            args = (x, )

    elif isinstance(x, (neo.Epoch, neo.Event)):
        for attr in x._necessary_attrs:
            if attr[0] not in kw:
                kw[attr[0]] = getattr(x, attr[0], None)

    elif isinstance(x, pq.Quantity):
        if "units" not in kw:
            kw["units"] = x.units

        if "dtype" not in kw:
            kw["dtype"] = x.dtype

        if "buffer" not in kw:
            kw["buffer"] = x.data

        kw["default_value"] = x

        kw["allow_none"] = allow_none

        #return QuantityTrait(x, **kw)

    elif isinstance(x, np.ndarray):
        if "dtype" not in kw:
            kw["dtype"] = x.dtype

        if "buffer" not in kw:
            try:
                # NOTE: 2021-12-14 10:50:35
                # issues with this when 'x' is a struct array
                # generated by h5io.pandas2Structarray
                kw["buffer"] = x.data
            except:
                traceback.print_exc()

        kw["default_value"] = x
        kw["allow_none"] = allow_none


    elif isinstance(x, (pd.DataFrame, pd.Series, pd.Index)):
        if len(args) == 0:
            args = (x, )

    elif isinstance(x, (int, float, complex, str)):
        args = (x, )
        kw["default_value"] = x

        kw["allow_none"] = allow_none

        # print(f"adapt_args_kw args = {args}, kw = {kw}")

    return args, kw

def dynamic_trait(x, *args, **kwargs):
    r"""Generates a trait type for object x.

    Parameters:
    ===========

    x = an object;

    The trait type is derived from a traitlets.TraitType subclass according to
    type(x) after lookup in the TRAITSMAP dict in this module.

    The derived trait type overrides the default set() method for a customized
    notification mechanism.


    Prerequisites: Except for enum types (enum.Enum and enumIntEnum)
    x.__class__ should define a "copy constructor", e.g.:

    x = SomeClass()

    y = SomeClass(x)    # copy constructor semantics when x and y are of the same type
                        # x may be a subclass/superclass of y, or another type

    For types derived from builtin types, this is taken care of by the python
    library. Anything else needs a bit of work.

    Options:
    --------
    allow_none: bool default is False

    content_traits:bool, default is False

    content_allow_none:bool, default is the value of allow_none

    force_trait: a subclass of traitlets.TraitType, or None.

        Optional, default is None.

        When given, the trait type lookup is bypassed and the trait
        type specified by force_trait is used as the base Trait type instead.

    set_function: a function of the signature f(instance, obj, value)
        Optional, default is None

        When None, the generated trait type uses the function standard_traitlet_set
        defined in this module.

        For details see traitlets.TraitType.set()

    """
    from .traitcontainers import DataBag
    import core.scipyen_traitlets as sct
    from .scipyen_traitlets import (DataBagTrait, DequeTrait, QuantityTrait,
                                    NeoBlockTrait)#, MetaNotifier)
    allow_none = kwargs.pop("allow_none", False)
    force_trait = kwargs.pop("force_trait", None)
    set_function = kwargs.pop("set_function", None)
    content_traits = kwargs.pop("content_traits", True) # used in the recursive dynamic_trait call
    # FIXME: 2021-10-10 16:43:29
    # the following are never used !!!
    content_allow_none = kwargs.pop("content_allow_none", allow_none) # noqa
    use_mutable = kwargs.pop("use_mutable", False)
    #klass = kwargs.pop("klass", None)

    # NOTE: 2021-08-20 11:44:00 A reminder:
    # isinstance(x, sometype) returns True when sometype is in type(x).__mro__
    # this means a that EITHER 'x' is of type 'sometype' OR 'x' is derived from
    # 'sometype', possibly with more than one inheritance level
    #
    # getmro returns a tuple of classes starting from x.__class__ and backwards
    # up the inheritance chain: superclasses = getmro(type(x))
    #
    # therefore superclasses[0] == type(x) is ALWAYS True
    #
    # if 'x' is of a type found in traitsmap keys then OK, else we fallback to
    # Instance

    arg = [x] + [a for a in args]

    args = tuple(arg)

    kw = kwargs

    myclass = x.__class__

    if dataclasses.is_dataclass(x):
        return sct.DataclassTrait(allow_none=allow_none)

    if issubclass(myclass, DataBag):
        traits = dict((k, dynamic_trait(v, allow_none = allow_none, content_traits=False if v is x else True)) for k,v in x.items())
        return sct.DataBagTrait(default_value=x,
                            per_key_traits = traits,
                            allow_none = allow_none,
                            mutable_key_value_traits = use_mutable)

    traitlet_class = None

    # NOTE: 2025-07-06 10:34:23 -
    #
    # 1. Search for a custom traitlet class in scipyen_traitlets
    #
    # 2. I a custom traitlet class was found, then use it; else, construct a
    # dynamic traitlet class
    #
    traitlet_class_name = myclass.__name__

    if traitlet_class_name[0].islower():
        traitlet_class_name = traitlet_class_name.capitalize()

    # NOTE: 2025-11-25 20:11:27
    # avoid confusion of NeoObjectList with List, for older neo versions 😦
    if myclass == NeoObjectList:
        if issubclass(myclass, list):
            traitlet_class_name = "ListTrait" # give the pssibility to co-inherit from list, also
        else:
            traitlet_class_name = "NeoObjectListTrait"

    elif issubclass(myclass, NeoObjectList): # BUG 2026-06-12 16:44:38 FIXME
        # covers the recenty added ephys.*List types and triggerprotocols
        traitlet_class_name = myclass.__name__ + "Trait"
        base_classes = (sct.NeoObjectListTrait, )
        # base_classes = (sct.ListTrait, )
        exec_body_fn = partial(_dynatrtyp_exec_body_, klass=myclass,
                               setfn=traitlet_set_scipyen_object_lists,
                               allowed_contents = myclass.allowed_contents)

        traitlet_class = new_class(traitlet_class_name,
                                       bases = base_classes,
                                       exec_body = exec_body_fn)
        # traitlet_class.default_value = Undefined
        traitlet_class.default_value = myclass()

        return traitlet_class(allow_none = allow_none)

    else:
        traitlet_class_name = f"{traitlet_class_name}Trait"
        traitlet_class = sct.__dict__.get(traitlet_class_name, None)

    if traitlet_class is None:
        if any("neo" in c.__module__ for c in getmro(myclass)):
            traitlet_class_name = f"Neo{myclass.__name__}Trait"
            traitlet_class = sct.__dict__.get(traitlet_class_name, None)

    if (
        traitlet_class is not None and
        (
            not isinstance(traitlet_class, type)
            and TraitType not in getmro(traitlet_class)
         )
        ):
        traitlet_class = None


    if traitlet_class is None:
        traitlet_classes = [None]

        if isclass(force_trait) and issubclass(force_trait, traitlets.TraitType):
            traitlet_classes = sct.TRAITSMAP.get(myclass, (force_trait, ))

        else:
            # NOTE: 2021-08-20 12:22:12 For a finer granularity
            # we get a stock tratilet class from TRAITSMAP
            traitlet_classes = sct.TRAITSMAP.get(myclass, (Any, ))

        if traitlet_classes[0] is None:
            # NOTE: 2021-10-10 17:10:02
            # when 'x' is a DataBag, the line below always returns 'dict'
            highest_below_object = [s for s in reversed(getmro(myclass))][1] # all Python types inherit from object
            traitlet_classes = sct.TRAITSMAP.get(highest_below_object, (Any,))

        if not isfunction(set_function) or len(signature(set_function).parameters) != 3:
            set_function = traitlet_set
            #set_function = standard_traitlet_set

        traitlet_class = traitlet_classes[0]
        klass = getattr(traitlet_class, "klass", myclass)
        exec_body_fn = partial(_dynatrtyp_exec_body_, klass=klass, setfn=set_function)

        if traitlet_class.__name__ == "Any":
            new_traitlet_class_pfx = f"{myclass.__name__.capitalize()}_Any_Dyn"
        else:
            new_traitlet_class_pfx = f"{traitlet_class.__name__}_Dyn"

        new_traitlet_class = new_class(new_traitlet_class_pfx,
                                       bases = traitlet_classes,
                                       exec_body = exec_body_fn)

        new_args, new_kw = adapt_args_kw(x, args, kw, allow_none)

        if traitlet_classes[0] is Instance:
            return new_traitlet_class(klass = myclass, args = args, kw = kw, allow_none = allow_none)

        if issubclass(new_traitlet_class, Dict) and content_traits:
            traits = dict((k, dynamic_trait(v, allow_none = allow_none, content_traits=False if v is x else True)) for k,v in x.items())
            # NOTE: New API for traitlets >= 5.0: 'traits' is deprecated in favour of 'per_key_traits'
            return new_traitlet_class(default_value = x, per_key_traits = traits, allow_none = allow_none)

        return new_traitlet_class(default_value = x, allow_none = allow_none)

    else:
        return traitlet_class(default_value = x, allow_none = allow_none)

class transform_link(traitlets.link):
    r"""Bi-directional link traits from different objects via optional transforms.

    Parameters
    ----------
    source : (object / attribute name) pair
    target : (object / attribute name) pair
    forward: callable (optional) Data transformation FROM source TO target.
    reverse: callable (optional) Data transformation FROM target TO source.

    NOTE: Modified from traitlets.traitlets.link

    """
    updating = False

    def __init__(self, source, target, forward=None, reverse=None):
        self._forward = forward if forward else lambda x: x
        self._reverse = reverse if reverse else lambda x: x

        traitlets._validate_link(source, target)

        self.source, self.target = source, target

        try:
            setattr(target[0], target[1],
                    self._forward(getattr(source[0], source[1])))
        finally:
            source[0].observe(self._update_target, names=source[1])
            target[0].observe(self._update_source, names=target[1])

    @contextlib.contextmanager
    def _busy_updating(self):
        self.updating = True
        try:
            yield
        finally:
            self.updating = False

    def _update_target(self, change):
        if self.updating:
            return
        with self._busy_updating():
            setattr(self.target[0], self.target[1],
                    self._forward(change.new))

    def _update_source(self, change):
        if self.updating:
            return
        with self._busy_updating():
            setattr(self.source[0], self.source[1],
                    self._reverse(change.new))

    def unlink(self):
        self.source[0].unobserve(self._update_target, names=self.source[1])
        self.target[0].unobserve(self._update_source, names=self.target[1])
        self.source, self.target = None, None

