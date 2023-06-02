# -*- coding: utf-8 -*-
"""Utilities for programming with traitlets.
NOTE: 2022-01-29 13:32:21
There are issues when trying to implement traitlets for collection's CONTENTS,
see docstring in scipyen_traitlets module (FIXME/TODO 2022-01-29 13:29:19)
# NOTE: 2022-11-03 14:36:21
I'm sure there are lots of BUG(s) and/or redundant code - definitely needs
cleaning up...
"""

import enum
from enum import (EnumMeta, Enum, IntEnum, )
import contextlib, traceback

from inspect import (getmro, isclass, isfunction, signature,)
import quantities as pq
import numpy as np
from types import new_class
import typing
from collections import deque
from functools import (partial, partialmethod)

# import six
# 
# 
# 
# try:
#     from traitlets import (class_of, repr_type, add_article,)
# except:
#     from traitlets.utils.descriptions import (class_of, repr_type, add_article,)
    
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
import vigra
import pandas as pd
import neo
import quantities as pq
from core import datasignal
from core.quantities import units_convertible
from core.utilities import gethash, safe_identity_test
from .prog import (timefunc, processtimefunc)

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

from core.prog import safeWrapper
#from core.traitcontainers import DataBag # doesn't work because of recursion

# NOTE: 2021-08-20 15:29:02
# below, type is a placeholder for types NOT defined in this module
# e.g. not imported
# in particular this is the case for traitcontainer.DataBag, TriggerEvent, etc

def traitlet_delete(self_instance, owner_instance):
    """Wraps descriptor __delete__
    Fails silently when owner is of wrong type
    """
    if hasattr(owner_instance, "remove_trait") and hasattr(owner_instance, "_trait_values") and hasattr(owner_instance, "traits"):
        if self_instance.name in owner_instance.traits():
            trait_to_remove = owner_instance.traits()[self_instance.name]
            owner_instance.remove_trait(self_instance.name, trait_to_remove)
            old_value = owner_instance._trait_values.pop(self_instance.name, None)
            owner_instance._notify_trait(self_instance.name, old_value, Undefined,
                                         change_type="removed")
   

#@timefunc
def traitlet_set(instance, obj, value):
    """Overrides traitlets.TraitType.set to check for special hash.
    This is supposed to also detect changes in the order of elements in sequences.
    WARNING: Slows down execution
    """
    #new_value = instance._validate(obj, value)
    new_value = value # skip validation
    silent = True
    change_type="modified"
    
    if instance.name and instance.name in obj._trait_values and instance.name in obj.traits():
        old_value = obj._trait_values[instance.name]
    else:
        old_value = instance.default_value
        silent = False
        change_type = "new"
    
    if new_value is None and old_value is None:
        return
    
    try:
        #silent = new_value is old_value
        if silent:
            new_hash = gethash(new_value)
            #print("\told %s (hash %s)\n\tnew %s (hash %s)" % (old_value, instance.hashed, new_value, new_hash))
            #print(instance.name, "old hashed", instance.hashed, "new_hash", new_hash)
            silent = bool(new_hash == instance.hashed)
            
            if not silent:
                instance.hashed = new_hash
            
    except:
        traceback.print_exc()
        # if there is an error in comparing, default to notify
        silent = False
        
    obj._trait_values[instance.name] = new_value
    
    if silent is not True:
        # we explicitly compare silent to True just in case the equality
        # comparison above returns something other than True/False
        # obj._notify_trait(instance.name, old_value, new_value)
        obj._notify_trait(instance.name, old_value, new_value, 
                          change_type = change_type)

def _dynatrtyp_exec_body_(ns, setfn = traitlet_set, delfn=traitlet_delete):
    #print("ns:", ns)
    ns["info_text"]="Trait that is sensitive to content change"
    ns["hashed"] = 0
    # ns["hashed"] = -1
    ns["set"] = setfn
    ns["__delete__"] = delfn
    
#@safeWrapper
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
    """Generates a trait type for object x.
    
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
    content_allow_none = kwargs.pop("content_allow_none", allow_none)
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
    
    if issubclass(myclass, DataBag):
        traits = dict((k, dynamic_trait(v, allow_none = allow_none, content_traits=False if v is x else True)) for k,v in x.items())
        return sct.DataBagTrait(default_value=x, 
                            per_key_traits = traits, 
                            allow_none = allow_none, 
                            mutable_key_value_traits = use_mutable)
    
    traitlet_class = None
    
    traitlet_class_name = myclass.__name__
    
    if traitlet_class_name[0].islower():
        traitlet_class_name = traitlet_class_name.capitalize()
        # traitlet_class_name = traitlet_class_name[0].upper() + traitlet_class_name[1:]
        
    traitlet_class_name = f"{traitlet_class_name}Trait"
    
    traitlet_class = sct.__dict__.get(traitlet_class_name, None)
    
    if traitlet_class is None:
        if any("neo" in c.__module__ for c in getmro(myclass)):
            traitlet_class_name = f"Neo{myclass.__name__}Trait"
            traitlet_class = sct.__dict__.get(traitlet_class_name, None)
            
    if traitlet_class is not None and (not isinstance(traitlet_class, type) and TraitType not in getmro(traitlet_class)):
        traitlet_class = None
    
    # print(f"\n\tdynamic_trait {type(x).__name__} ⇒ traitlet_class = {traitlet_class.__class__.__name__}")
    
    # if myclass == dict:
    #     print(f"traitlet_class {traitlet_class}")
    
    # print(f"\n\tdynamic_trait {type(x).__name__} ⇒ traitlet_class = {traitlet_class.__class__.__name__}")
    
    if traitlet_class is None:
        traitlet_classes = [None]
        
        if issubclass(myclass, tuple):
            return Tuple(x)
        
        elif issubclass(myclass, dict):
            return Dict(x)
        
        if isclass(force_trait) and issubclass(force_trait, traitlets.TraitType):
            traitlet_classes = sct.TRAITSMAP.get(myclass, (force_trait, ))
            
        else:
            # NOTE: 2021-08-20 12:22:12 For a finer granularity
            traitlet_classes = sct.TRAITSMAP.get(myclass, (Any, ))

        if traitlet_classes[0] is None:
            # NOTE: 2021-10-10 17:10:02
            # when 'x' is a DataBag, the line below always returns 'dict'
            highest_below_object = [s for s in reversed(getmro(myclass))][1] # all Python types inherit from object
            traitlet_classes = sct.TRAITSMAP.get(highest_below_object, (Any,))
            
        if not isfunction(set_function) or len(signature(set_function).parameters) != 3:
            set_function = traitlet_set
            #set_function = standard_traitlet_set

        exec_body_fn = partial(_dynatrtyp_exec_body_, setfn=set_function)
        
        traitlet_class = traitlet_classes[0]
        
        new_klass = new_class("%s_Dyn" % traitlet_class.__name__, 
                            bases = traitlet_classes, 
                            exec_body = exec_body_fn)
        
        new_args, new_kw = adapt_args_kw(x, args, kw, allow_none)
        
        if traitlet_classes[0] is Instance:
            return new_klass(klass = myclass, args = args, kw = kw, allow_none = allow_none)
        
        if issubclass(new_klass, Dict) and content_traits:
            traits = dict((k, dynamic_trait(v, allow_none = allow_none, content_traits=False if v is x else True)) for k,v in x.items())
            # NOTE: New API for traitlets >= 5.0: 'traits' is deprecated in favour of 'per_key_traits'
            return new_klass(default_value = x, per_key_traits = traits, allow_none = allow_none)
        
        return new_klass(default_value = x, allow_none = allow_none)
    
    else:
        return traitlet_class(default_value = x, allow_none = allow_none)
    
class transform_link(traitlets.link):
    """Bi-directional link traits from different objects via optional transforms.
    
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
        
# def trait_from_type(x, *args, **kwargs):
#     """Generates a TraitType for object x.
#     
#     Prerequisites: Except for enum types (enum.Enum and enumIntEnum)
#     x.__class__ should define a "copy constructor", e.g.:
#     
#     x = SomeClass()
#     
#     y = SomeClass(x)    # copy constructor semantics when x and y are of the same type 
#                         # x may be a subclass/superclass of y, or another type
#     
#     For types derived from builtin types, this is taken care of by the python 
#     library. Anything else needs a bit of work.
#     
#     Options:
#     --------
#     
#     allow_none: bool default is False
#     content_traits:bool, default is False
#     content_allow_none:bool, default is whatever allow_none is
#     
#     """
#     allow_none = kwargs.pop("allow_none", False)
#     content_traits = kwargs.pop("content_traits", True)
#     content_allow_none = kwargs.pop("content_allow_none", allow_none)
#     
#     immediate_class = getmro(x.__class__)[0]
#     # NOTE 2020-07-07 14:42:22
#     # to prevent "slicing" of derived classes, 
#     
#     arg = [x] + [a for a in args]
#     
#     args = tuple(arg)
#     
#     kw = kwargs
#     
#     if x is None:
#         return Any()
#     
#     elif isinstance(x, bool):
#         if immediate_class != bool:
#             # preserve its immediate :class:, otherwise this will slice subclasses
#             return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
#         
#         return Bool(default_value=x, allow_none = allow_none)
#     
#     elif isinstance(x, int):
#         if immediate_class != int:
#             return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
#         
#         return Int(default_value=x, allow_none = allow_none)
#     
#     elif isinstance(x, float):
#         if immediate_class != float:
#             return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
#         
#         return Float(default_value=x, allow_none = allow_none)
#     
#     elif isinstance(x, complex):
#         if immediate_class != complex:
#             return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
#         
#         return Complex(default_value=x, allow_none = allow_none)
#     
#     elif isinstance(x, bytes):
#         if immediate_class != bytes:
#             return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
#         
#         return Bytes(default_value=x, allow_none = allow_none)
#     
#     elif isinstance(x, str):
#         if immediate_class != str:
#             return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
#         
#         return Unicode(default_value=x, allow_none = allow_none)
#     
#     elif isinstance(x, list):
#         if content_traits:
#             traits = [trait_from_type(v, allow_none=allow_none, content_traits=content_traits) for v in x]
#         else:
#             traits = None
#             
#         if immediate_class != list:
#             return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
#         
#         traitklass = new_class("ListTrait", bases = (List,), exec_body = new_trait_callback)
#         return traitklass(default_value = x, allow_none = allow_none)
#         #return TestTrait(default_value = x, traits = traits, allow_none = allow_none)
#         #return ListTrait(default_value = x, traits = traits, allow_none = allow_none)
#         #return List(default_value=x, allow_none = allow_none)
#     
#     elif isinstance(x, set):
#         if immediate_class != set:
#             return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
#         
#         return Set(default_value = x, allow_none = allow_none)
#     
#     elif isinstance(x, tuple):
#         if immediate_class != tuple:
#             return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
#         
#         return Tuple(default_value = x, allow_none = allow_none)
#     
#     elif isinstance(x, dict):
#         # NOTE 2021-08-19 11:33:03
#         # for Dict, traits is a mapping of dict keys to their corresponding traits
#         if content_traits:
#             traits = dict((k, trait_from_type(v, allow_none = allow_none, content_traits=content_traits)) for k,v in x.items()) 
#         else:
#             traits = None
#             
#         if immediate_class != dict:
#             # preserve its immediate :class:, otherwise this will slice subclasses
#             return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
#         
#         return Dict(default_value=x, traits=traits, allow_none = allow_none)
#         #return Dict(default_value=x, allow_none = allow_none)
#     
#     elif isinstance(x, enum.EnumMeta):
#         return UseEnum(x, allow_none = allow_none)
#     
#     else:
#         #immediate_class = getmro(x.__class__)[0]
#         if immediate_class.__name__ == "type": # trait encapsulates a type, not an instance
#             return Type(klass=x, default_value = immediate_class, allow_none = allow_none)
#         
#         else: # trait encapsulates an instance
#             # NOTE: 2020-09-05 14:23:43 some classes need special treatment for 
#             # their default constructors (ie when *args and **kw are empty)
#             # so far we plan to implement this for the following:
#             # vigra.VigraArray, vigra.AxisInfo, vigra.AxisTags,
#             # neo.ChannelIndex, neo.AnalogSignal, neo.IrregularlySampledSignal,
#             # neo.ImageSequence, neo.SpikeTrain
#             # datasignal.DataSignal, datasignal.IrregularlySampledDataSignal,
#             # pandas.Series, pandas.DataFrame
#             if isinstance(x, vigra.AxisInfo):
#                 if "key" not in kw:
#                     kw["key"] = x.key
#                     
#                 if "typeFlags" not in kw:
#                     kw["typeflags"] = x.typeFlags
#                     
#                     
#                 if "resolution" not in kw:
#                     kw["resolution"] = x.resolution
#                     
#                 if "description" not in kw:
#                     kw["description"] = x.description
#                     
#             elif isinstance(x, vigra.AxisTags):
#                 if len(args) == 0:
#                     args = (x, ) # copy c'tor
#                 
#             elif isinstance(x, vigra.VigraArray):
#                 if len(args) == 0:
#                     args = (x, ) # can be a copy constructor
#                     
#                 if "dtype" not in kw:
#                     kw["dtype"] = x.dtype
#                     
#                 if "order" not in kw:
#                     kw["order"] = x.order
#                     
#                 if "axistags" not in kw:
#                     kw["axistags"] = None # calls VigraArray.defaultAxistags or uses x.axistags if they exist
#                     
#             #elif isinstance(x, neo.ChannelIndex):
#                 #if len(args) == 0:
#                     #args = (x.index, )
#                     
#                 #for attr in x._all_attrs:
#                     #if attr[0] != "index":
#                         #if attr[0] not in kw:
#                             #kw[attr[0]] = getattr(x, attr[0])
#                         
#             elif isinstance(x, (neo.AnalogSignal, datasignal.DataSignal)):
#                 if len(args) == 0:
#                     args = (x,) # takes units & time units from x
#                     
#                 for attr in x._all_attrs:
#                     if attr[0] != "signal":
#                         if attr[0] not in kw:
#                             kw[attr[0]] = getattr(x, attr[0])
#                         
#             elif isinstance(x, (neo.IrregularlySampledSignal, datasignal.IrregularlySampledDataSignal)):
#                 if len(args) < 2:
#                     args = (x.times, x,)
#                     
#                 for attr in x._all_attrs:
#                     if attr[0] not in ("times", "signal"):
#                         if attr[0] not in kw:
#                             kw[attr[0]] = getattr(x, attr[0])
#                         
#             elif isinstance(x, neo.SpikeTrain):
#                 if len(args)  == 0:
#                     args = (x.times, x.t_stop,)
#                     
#                 for attr in x._all_attrs:
#                     if attr[0] not in ("times", "t_stop"):
#                         if attr[0] not in kw:
#                             kw[attr[0]] = getattr(x, attr[0])
#                         
#             elif isinstance(x, neo.ImageSequence):
#                 if len(args) == 0:
#                     args = (x, )
#                     
#                 for attr in x._all_attrs:
#                     if attr[0] != "image_data":
#                         if attr[0] not in kw:
#                             kw[attr[0]] = getattr(x, attr[0])
#                 
#             elif isinstance(x, (neo.Block, neo.Segment)):
#                 if len(args) == 0:
#                     args = (x, )
#                     
#             #elif isinstance(x, (neo.Block, neo.Segment, neo.Unit)):
#                 #if len(args) == 0:
#                     #args = (x, )
#                     
#             elif isinstance(x, (neo.Epoch, neo.Event)):
#                 for attr in x._all_attrs:
#                     if attr[0] not in kw:
#                         kw[attr[0]] = getattr(x, attr[0])
#                         
#             elif isinstance(x, pq.Quantity):
#                 if "units" not in kw:
#                     kw["units"] = x.units
#                 
#                 if "dtype" not in kw:
#                     kw["dtype"] = x.dtype
#                     
#                 if "buffer" not in kw:
#                     kw["buffer"] = x.data
#                 
#                 kw["default_value"] = x
#                 
#                 kw["allow_none"] = allow_none
#                 
#                 return QuantityTrait(x, **kw)
#                 
#             elif isinstance(x, np.ndarray):
#                 #shp = tuple(list(x.shape))
#                 
#                 if "dtype" not in kw:
#                     kw["dtype"] = x.dtype
#                     
#                 if "buffer" not in kw:
#                     kw["buffer"] = x.data
#                     
#                 kw["default_value"] = x
#                 kw["allow_none"] = allow_none
#                 
#                 return NdarrayTrait(x, **kw)
#                     
#             elif isinstance(x, pd.DataFrame):
#                 if len(args) == 0:
#                     args = (x, )
#                 
#             elif isinstance(x, pd.Series):
#                 if len(args) == 0:
#                     args = (x, )
#                     
#                 
#             trait = Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
#             trait.default_value = x
#             return trait
#     
