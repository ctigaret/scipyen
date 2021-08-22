# -*- coding: utf-8 -*-
"""Utilities for programming with traitlets
"""

import enum
from enum import (EnumMeta, Enum, IntEnum, )
import contextlib

from inspect import (getmro, isclass, isfunction, signature,)
from types import new_class
from collections import deque
from functools import (partial, partialmethod)

import traitlets

from traitlets import (six,
    HasTraits, MetaHasTraits, TraitType, All, Any, Bool, CBool, Bytes, CBytes, 
    Dict, Enum, Set, Int, CInt, Long, CLong, Integer, Float, CFloat, 
    Complex, CComplex, Unicode, CUnicode, CRegExp, TraitError, Union, Undefined, 
    Type, This, Instance, TCPAddress, List, Tuple, UseEnum, ObjectName, 
    DottedObjectName, CRegExp, ForwardDeclaredType, ForwardDeclaredInstance, 
    link, directional_link, validate, observe, default,
    observe_compat, BaseDescriptor, HasDescriptors, is_trait, getmembers,
    class_of, repr_type, add_article, EventHandler,
)

from traitlets.utils.bunch import Bunch as Bunch

import numpy as np
import vigra
import pandas as pd
import neo
import quantities as pq
from core import datasignal
from core.datatypes import units_convertible
from core.utilities import gethash, safe_identity_test

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



#from prog import safeWrapper
#from core.traitcontainers import DataBag # doesn't work because of recursion

# NOTE: 2021-08-20 15:29:02
# below, type is a placeholder for types NOT defined in this module
# e.g. not imported
# in particular this is the case for traitcontainer.DataBag, TriggerEvent, etc

TRAITSMAP = {           # use casting versions
    None:       (Any,),
    type(None): (Any,),
    bool:       (CBool,),
    int:        (CInt,),
    float:      (CFloat,),
    complex:    (CComplex,),
    bytes:      (CBytes,),
    str:        (CUnicode,),
    list:       (List,),
    deque:      (List,),
    set:        (Set,),
    frozenset:  (Set,),
    tuple:      (Tuple,),
    dict:       (Dict,),
    EnumMeta:   (UseEnum,),
    Enum:       (UseEnum,), # IntEnum inherits from int and Enum
    type:       (Instance,),    # e.g., type(type(None))
    property:   (DottedObjectName,),
    #type:       (Type,),    # e.g., type(type(None))
    #function:   (Any,)
    }

def enhanced_set(instance, obj, value):
    """Overrides traitlets.TraitType.set to check for special hash.
    This is supposed to also detect changes in the order of elements in sequences.
    """
    #print("enhanced set for %s" % type(instance).__name__)
    
    new_value = instance._validate(obj, value)
    
    try:
        old_value = obj._trait_values[instance.name]
    except KeyError:
        old_value = instance.default_value

    obj._trait_values[instance.name] = new_value
    
    try:
        new_hash = gethash(new_value)
        #print(instance.name, "old hashed", instance.hashed, "new_hash", new_hash)
        silent = (new_hash == instance.hashed)
        
        if not silent:
            instance.hashed = new_hash
            
        
        ##silent = bool(old_value == new_value)
        
        #print("%s: silent before hash" % instance.name, silent)
        
        ## NOTE: 2021-08-19 16:17:23
        ## check for change in contents
        #if silent is not False:
            #new_hash = gethash(new_value)
            #silent = (new_hash == instance.hashed)
            #print("%s: silent after hash" % instance.name, silent)
            #if not silent:
                #instance.hashed = new_hash
    except:
        traceback.print_exc()
        # if there is an error in comparing, default to notify
        silent = False
        
    if silent is not True:
        # we explicitly compare silent to True just in case the equality
        # comparison above returns something other than True/False
        obj._notify_trait(instance.name, old_value, new_value)

def _dynatrtyp_exec_body_(ns, setfn = enhanced_set):
    #print("ns:", ns)
    ns["info_text"]="Trait that is sensitive to content change"
    ns["hashed"] = 0
    ns["set"] = setfn
    
def adapt_args_kw(x, args, kw, allow_none):
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
            
    elif isinstance(x, neo.ChannelIndex):
        if len(args) == 0:
            args = (x.index, )
            
        for attr in x._all_attrs:
            if attr[0] != "index":
                if attr[0] not in kw:
                    kw[attr[0]] = getattr(x, attr[0])
        
    elif isinstance(x, (neo.AnalogSignal, datasignal.DataSignal)):
        if len(args) == 0:
            args = (x,) # takes units & time units from x
            
        for attr in x._all_attrs:
            if attr[0] != "signal":
                if attr[0] not in kw:
                    kw[attr[0]] = getattr(x, attr[0])
        
    elif isinstance(x, (neo.IrregularlySampledSignal, datasignal.IrregularlySampledDataSignal)):
        if len(args) < 2:
            args = (x.times, x,)
            
        for attr in x._all_attrs:
            if attr[0] not in ("times", "signal"):
                if attr[0] not in kw:
                    kw[attr[0]] = getattr(x, attr[0])
                
    elif isinstance(x, neo.SpikeTrain):
        if len(args)  == 0:
            args = (x.times, x.t_stop,)
            
        for attr in x._all_attrs:
            if attr[0] not in ("times", "t_stop"):
                if attr[0] not in kw:
                    kw[attr[0]] = getattr(x, attr[0])
        
    elif isinstance(x, neo.ImageSequence):
        if len(args) == 0:
            args = (x, )
            
        for attr in x._all_attrs:
            if attr[0] != "image_data":
                if attr[0] not in kw:
                    kw[attr[0]] = getattr(x, attr[0])
        
    elif isinstance(x, (neo.Segment, neo.Block, neo.Unit)):
        if len(args) == 0:
            args = (x, )
        
    elif isinstance(x, (neo.Epoch, neo.Event)):
        for attr in x._all_attrs:
            if attr[0] not in kw:
                kw[attr[0]] = getattr(x, attr[0])
        
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
            kw["buffer"] = x.data
            
        kw["default_value"] = x
        kw["allow_none"] = allow_none
        
        #return ArrayTrait(x, **kw)
                    
    elif isinstance(x, (pd.DataFrame, pd.Series, pd.Index)):
        if len(args) == 0:
            args = (x, )

    return args, kw
    
def dynamic_trait(x, *args, **kwargs):
    """Generates a trait type for object x.
    
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
        
        When None, the generated trait type uses the function enhanced_set 
        defined in this module.
        
        For details see traitlets.TraitType.set()
    
    """
    allow_none = kwargs.pop("allow_none", False)
    content_traits = kwargs.pop("content_traits", True)
    content_allow_none = kwargs.pop("content_allow_none", allow_none)
    force_trait = kwargs.pop("force_trait", None)
    set_function = kwargs.pop("set_function", None)
    
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
    # so unlike in trait_from_type, here we don't need immediate_class anymore
    # if 'x' is of a type found in traitsmap keys then OK, else we fallback to
    # Instance
    
    myclass = x.__class__
    
    #print("myclass", myclass)
    
    arg = [x] + [a for a in args]
    
    args = tuple(arg)
    
    kw = kwargs
    
    #traitclass = TRAITSMAP.get(myclass, Instance)
    
    if isclass(force_trait) and issubclass(force_trait, traitlets.TraitType):
        traitclass = (force_trait, )
    else:
        # NOTE: 2021-08-20 12:22:12 For a finer granularity
        traitclass = TRAITSMAP.get(myclass, (None, ))
    
    #print("traitclass", traitclass)

    if traitclass[0] is None:
        highest_below_object = [s for s in reversed(getmro(type(x)))][1] # all Python types inherit from object
        traitclass = TRAITSMAP.get(highest_below_object, (Any,))
        #traitclass = TRAITSMAP.get(highest_below_object, (Instance,))
        
    #print("traitclass", traitclass)
    
    if not isfunction(set_function) or len(signature(set_function).parameters) != 3:
        set_function = enhanced_set

    exec_body_fn = partial(_dynatrtyp_exec_body_, setfn=set_function)
    
    new_klass = new_class("%s_Dyn" % traitclass[0].__name__, bases = traitclass, 
                          exec_body = exec_body_fn)
    
    new_args, new_kw = adapt_args_kw(x, args, kw, allow_none)
    
    #print("new_args", new_args)
    #print("new_kw", new_kw)
    
    if traitclass[0] is Instance:
        return new_klass(klass = myclass, args = args, kw = kw, allow_none = allow_none)
    
    if issubclass(new_klass, Dict):
        if content_traits:
            # NOTE: 2021-08-21 09:54:18 FIXME
            # ATTENTION Line below produces infinite recursion when the underlying dict
            # contains a reference to itself
            #traits = dict((k, dynamic_trait(v, allow_none = allow_none, content_traits=content_traits)) for k,v in x.items())
            # NOTE: 2021-08-21 09:54:46 FIXED
            # do NOT use content_traits for dict values when these are of dict type
            traits = dict((k, dynamic_trait(v, allow_none = allow_none, content_traits=False)) for k,v in x.items())
        else:
            traits = None
            
        return new_klass(default_value = x, traits=traits, allow_none = allow_none)
    
    else:
        return new_klass(default_value = x, allow_none = allow_none)
    
class TraitSetMixin(object):
    def __init__(self):
        super().__init__
            
    def set(self, obj, value):
        """Overrides List.set to check for special hash.
        This is supposed to also detect changes in the order of elements.
        """
        enhanced_set(self, obj, value)
        
class TraitsObserver(HasTraits):
    """ CAUTION do not use yet
    """
    mutable_types = Bool(default=False)
    use_casting = Bool(default=False)
    allow_none = Bool(default=False)
    hidden_traits = ("mutable_types", "use_casting", "allow_none",)
    
    def add_traits(self, **traits):
        # NOTE 2020-07-04 22:43:58
        # the super's add_traits blows away non-trait attributes
        # because existing traits are reverted to the default value
        mutable = object.__getattribute__(self,"mutable_types")
        use_casting = object.__getattribute__(self, "use_casting")
        allow_none = object.__getattribute__(self, "allow_none")
        
        # NOTE 2020-07-04 22:42:42
        # __length__ and mutable_types need to be reset to their
        # current values (see NOTE 2020-07-04 22:43:58)
        # we do this here in order to avoid triggering a change notification
        traits.update({"mutable_types":trait_from_type(mutable),
                       "use_casting": trait_from_type(use_casting),
                       "allow_none": trait_from_type(allow_none)})
        
        super().add_traits(**traits) # this DOES keep __length__ and mutable_types traits but reverts them to the defaults
        
        # this also works, but triggers a change notification, which we don't 
        # need right now
        #self.__length__ = length
        #self.mutable_types = mutable
        
    def remove_traits(self, **traits):
        current_traits = self.traits()
        keep_traits  = dict([(k, current_traits[k]) for k in current_traits if k not in traits])
        
        mutable = self.mutable_types
        use_casting = self.use_casting
        allow_none = self.allow_none
        
        
        # again, this resets the maintenance traits to their default values, 
        # so we need to restore them (see NOTE 2020-07-04 22:43:58 and 
        # NOTE 2020-07-04 22:42:42)
        keep_traits.update({"mutable_types":trait_from_type(mutable),
                            "use_casting": trait_from_type(use_casting),
                            "allow_none": trait_from_type(allow_none==True)})
        
        self.__class__ = type(self.__class__.__name__, (HasTraits, ), {"changed":self.changed, "remove_traits":self.remove_traits})
        
        self.add_traits(**keep_traits)
        
    @observe(All)
    def changed(self, change):
        return
        ## NOTE: 2020-07-05 18:01:01 that's what you can to with these
        #print("self.changed: change['owner']:\n",change["owner"], "\n")
        #print("self.changed: change['name']:\n",change["name"], "\n")
        #print("self.changed: change['old']:\n",change["old"], "\n")
        #print("self.changed: change['new']:\n",change["new"], "\n")


class ContainerTraitsObserver(HasTraits):
    """ CAUTION do not use yet
    """
    __length__ = Int(default_value=0)
    mutable_types = Bool(default=False)
    use_casting = Bool(default=False)
    
    def add_traits(self, **traits):
        # NOTE 2020-07-04 22:43:58
        # the super's add_traits blows away non-trait attributes
        # because existing traits are reverted to the default value
        length = object.__getattribute__(self, "__length__")
        mutable = object.__getattribute__(self,"mutable_types")
        use_casting = object.__getattribute__(self, "use_casting")
        
        # NOTE 2020-07-04 22:42:42
        # these "maintenance" traits need to be reset to their current values
        # (see NOTE 2020-07-04 22:43:58)
        # we do this here in order to avoid triggering a change notification
        traits.update({"__length__":trait_from_type(length), 
                       "mutable_types":trait_from_type(mutable),
                       "use_casting": trait_from_type(use_casting)})
        
        super().add_traits(**traits) # this DOES keep __length__ and mutable_types traits but reverts them to the defaults
        
        # this also works, but triggers a change notification, which we don't 
        # need right now
        #self.__length__ = length
        #self.mutable_types = mutable
        
    def remove_traits(self, **traits):
        current_traits = self.traits()
        keep_traits  = dict([(k, current_traits[k]) for k in current_traits if k not in traits])
        
        length = self.__length__
        mutable = self.mutable_types
        use_casting = self.use_casting
        
        
        # again, this resets the maintenance traits to their default values, 
        # so we need to restore them (see NOTE 2020-07-04 22:43:58 and 
        # NOTE 2020-07-04 22:42:42)
        keep_traits.update({"__length__":trait_from_type(length), 
                            "mutable_types":trait_from_type(mutable),
                            "use_casting": trait_from_type(use_casting)})
        
        self.__class__ = type(self.__class__.__name__, (HasTraits, ), {"changed":self.changed, "remove_traits":self.remove_traits})
        
        self.add_traits(**keep_traits)
        
    @observe(All)
    def changed(self, change):
        return
        ## NOTE: 2020-07-05 18:01:01 that's what you can to with these
        #print("self.changed: change['owner']:\n",change["owner"], "\n")
        #print("self.changed: change['name']:\n",change["name"], "\n")
        #print("self.changed: change['old']:\n",change["old"], "\n")
        #print("self.changed: change['new']:\n",change["new"], "\n")

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
        
class ListTrait(List): # inheritance chain: List <- Container <- Instance
    """TraitType that ideally should notify:
    a) when a list contents has changed (i.e., gained/lost members)
    b) when an element in the list has changed (either a new value, or a new type)
    c) when the order of the elements has changed
    """
    _trait = None
    
    info_text = "Trait for lists that is sensitive to changes in content"
    
    def __init__(self, trait=None, traits=None, default_value=None, **kwargs):
        
        self._traits = traits # a list of traits, one per element
        self._length = 0
        
        self.hashed = 0
        
        # initialize the List (<- Container <- Instance) NOW
        super(ListTrait, self).__init__(trait=trait, default_value=default_value, **kwargs)
        
        if default_value is not None or default_value is not Undefined:
            self._length = len(default_value)
            self.hashed = gethash(default_value)
            
    def validate_elements(self, obj, value):
        # NOTE: 2021-08-19 11:28:10 do the inherited validation first
        value = super(ListTrait, self).validate_elements(obj, value)
        # NOTE: 2021-08-19 11:18:25 then the customized one
        # imitates see traitlets.Dict.validate_elements
        use_list = bool(self._traits) # may be None
        default_to = (self._trait or Any())
        validated = []
        
        if not use_list and isinstance(default_to, Any):
            return value
        
        for k,v in enumerate(value):
            if k < len(self._traits):
                try:
                    v = self._traits[k]._validate(obj, v)
                except TraitError:
                    self.element_error(obj, v, self._traits[k])
                else:
                    validated.append(v)
                    
            else:
                validated.append(v)

        return self.klass(validated)

    def set(self, obj, value):
        """Overrides List.set to check for special hash.
        This is supposed to also detect changes in the order of elements.
        """
        new_value = self._validate(obj, value)
        try:
            old_value = obj._trait_values[self.name]
        except KeyError:
            old_value = self.default_value

        obj._trait_values[self.name] = new_value
        try:
            silent = bool(old_value == new_value)
            
            # NOTE: 2021-08-19 16:17:23
            # check for change in contents
            if silent is not False:
                new_hash = gethash(new_value)
                silent = (new_hash == self.hashed)
                if not silent:
                    self.hashed = new_hash
        except:
            # if there is an error in comparing, default to notify
            silent = False
        if silent is not True:
            # we explicitly compare silent to True just in case the equality
            # comparison above returns something other than True/False
            obj._notify_trait(self.name, old_value, new_value)
        
class ArrayTrait(Instance):
    info_text = "Trait for numpy arrays"
    default_value = np.array([])
    klass = np.ndarray
    
    def __init__(self, args=None, kw=None, **kwargs):
        # allow 1st argument to be the array instance
        default_value = kwargs.pop("default_value", None)
        self.allow_none = kwargs.pop("allow_none", False)
        
        if isinstance(args, np.ndarray):
            self.default_value = args
            
        elif isinstance(args, (tuple, list)):
            if len(args):
                if isinstance(args[0], np.ndarray):
                    self.default_value = args[0]
                    
                else:
                    self.default_value = np.array(*args, **kwargs)
                    
            else:
                self.default_value = np.array([])
                
        else:
            self.default_value = np.array([])
                
        args = None
        super().__init__(klass = self.klass, args=args, kw=kw, 
                         default_value=default_value, **kwargs)
        
    def validate(self, obj, value):
        if isinstance(value, np.ndarray):
            return value
        
        self.error(obj, value)
        
    def make_dynamic_default(self):
        return np.array(self.default_value)
    
class QuantityTrait(Instance):
    info_text = "Trait for python quantities"
    default_value = pq.Quantity([]) # array([], dtype=float64) * dimensionless
    klass = pq.Quantity
    
    def __init__(self, args=None, kw=None, **kwargs):
        # allow 1st argument to be the array instance
        default_value = kwargs.pop("default_value", None)
        self.allow_none = kwargs.pop("allow_none", False)
        if isinstance(kw, dict) and len(kw):
            units = kw.pop("units", pq.dimensionless)
            
        else:
            kw = dict()
            units = kwargs.pop("units", pq.dimensionless)
        
        if isinstance(args, np.ndarray):
            if isinstance(args, pq.Quantity):
                units = args.units
                
            self.default_value = pq.Quantity(args, units=units)
            
        elif isinstance(args, (tuple, list)):
            if len(args):
                if isinstance(args[0], np.ndarray):
                    if isinstance(args[0], pq.Quantity):
                        units = args[0].units
                        self.default_value = pq.Quantity(args[0], units=units)
                            
                    else:
                        self.default_value = pq.Quantity(args[0], units=units)
                        
                else:
                    self.default_value = pq.Quantity(*args, units=units **kwargs)
                    
            else:
                self.default_value = pq.Quantity([], units=units)
                            
        else:
            self.default_value = pq.Quantity([], units=units)
            
        args=None
                
        kw["units"] = units
        
        super().__init__(klass = self.klass, args=args, kw=kw, 
                         default_value=default_value, **kwargs)
        
    def validate(self, obj, value):
        if isinstance(value, pq.Quantity) and units_convertible(value, self.default_value):
            return value
        
        self.error(obj, value)
        
    def make_dynamic_default(self):
        return pq.Quantity(self.default_value)
    
    def info(self):
        if isinstance(self.klass, six.string_types):
            klass = self.klass
        else:
            klass = self.klass.__name__
            
        result = "%s with dimensionality (units) of %s " % (class_of(klass), self.default_value.dimensionality)
        
        if self.allow_none:
            result += ' or None'

        return result

    def error(self, obj, value):
        kind = type(value)
        if six.PY2 and kind is InstanceType:
            msg = 'class %s' % value.__class__.__name__
        else:
            msg = '%s (i.e. %s)' % ( str( kind )[1:-1], repr( value ) )

        if obj is not None:
            if isinstance(value, pq.Quantity):
                e = "The '%s' trait of %s instance must be %s, but a Quantity with dimensionality (units) of %s was specified." \
                    % (self.name, class_of(obj),
                    self.info(), value.dimensionality)
                
            else:
                e = "The '%s' trait of %s instance must be %s, but a value of %s was specified." \
                    % (self.name, class_of(obj),
                    self.info(), msg)
        else:
            if isinstance(value, pq.Quantity):
                e = "The '%s' trait must be %s, but a Quantity with dimensionality (units) of %s was specified." \
                    % (self.name, self.info(), value.dimensionality)
            else:
                e = "The '%s' trait must be %s, but a value of %r was specified." \
                    % (self.name, self.info(), msg)
            
        raise TraitError(e)
    
   
    
def trait_from_type(x, *args, **kwargs):
    """Generates a TraitType for object x.
    
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
    content_allow_none:bool, default is whatever allow_none is
    
    """
    allow_none = kwargs.pop("allow_none", False)
    content_traits = kwargs.pop("content_traits", True)
    content_allow_none = kwargs.pop("content_allow_none", allow_none)
    
    immediate_class = getmro(x.__class__)[0]
    # NOTE 2020-07-07 14:42:22
    # to prevent "slicing" of derived classes, 
    
    arg = [x] + [a for a in args]
    
    args = tuple(arg)
    
    kw = kwargs
    
    if x is None:
        return Any()
    
    elif isinstance(x, bool):
        if immediate_class != bool:
            # preserve its immediate :class:, otherwise this will slice subclasses
            return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
        
        return Bool(default_value=x, allow_none = allow_none)
    
    elif isinstance(x, int):
        if immediate_class != int:
            return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
        
        return Int(default_value=x, allow_none = allow_none)
    
    elif isinstance(x, float):
        if immediate_class != float:
            return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
        
        return Float(default_value=x, allow_none = allow_none)
    
    elif isinstance(x, complex):
        if immediate_class != complex:
            return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
        
        return Complex(default_value=x, allow_none = allow_none)
    
    elif isinstance(x, bytes):
        if immediate_class != bytes:
            return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
        
        return Bytes(default_value=x, allow_none = allow_none)
    
    elif isinstance(x, str):
        if immediate_class != str:
            return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
        
        return Unicode(default_value=x, allow_none = allow_none)
    
    elif isinstance(x, list):
        if content_traits:
            traits = [trait_from_type(v, allow_none=allow_none, content_traits=content_traits) for v in x]
        else:
            traits = None
            
        if immediate_class != list:
            return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
        
        traitklass = new_class("ListTrait1", bases = (List,), exec_body = new_trait_callback)
        return traitklass(default_value = x, allow_none = allow_none)
        #return TestTrait(default_value = x, traits = traits, allow_none = allow_none)
        #return ListTrait(default_value = x, traits = traits, allow_none = allow_none)
        #return List(default_value=x, allow_none = allow_none)
    
    elif isinstance(x, set):
        if immediate_class != set:
            return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
        
        return Set(default_value = x, allow_none = allow_none)
    
    elif isinstance(x, tuple):
        if immediate_class != tuple:
            return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
        
        return Tuple(default_value = x, allow_none = allow_none)
    
    #elif "DataBag" in type(x).__name__:
    #elif isinstance(x, DataBag):
        #return DataBagTrait(default_value=x, allow_none=allow_none)
    
    elif isinstance(x, dict):
        # NOTE 2021-08-19 11:33:03
        # for Dict, traits is a mapping of dict keys to their corresponding traits
        if content_traits:
            traits = dict((k, trait_from_type(v, allow_none = allow_none, content_traits=content_traits)) for k,v in x.items()) 
        else:
            traits = None
            
        if immediate_class != dict:
            # preserve its immediate :class:, otherwise this will slice subclasses
            return Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
        
        return Dict(default_value=x, traits=traits, allow_none = allow_none)
        #return Dict(default_value=x, allow_none = allow_none)
    
    elif isinstance(x, enum.EnumMeta):
        return UseEnum(x, allow_none = allow_none)
    
    else:
        #immediate_class = getmro(x.__class__)[0]
        if immediate_class.__name__ == "type": # trait encapsulates a type, not an instance
            return Type(klass=x, default_value = immediate_class, allow_none = allow_none)
        
        else: # trait encapsulates an instance
            # NOTE: 2020-09-05 14:23:43 some classes need special treatment for 
            # their default constructors (ie when *args and **kw are empty)
            # so far we plan to implement this for the following:
            # vigra.VigraArray, vigra.AxisInfo, vigra.AxisTags,
            # neo.ChannelIndex, neo.AnalogSignal, neo.IrregularlySampledSignal,
            # neo.ImageSequence, neo.SpikeTrain
            # datasignal.DataSignal, datasignal.IrregularlySampledDataSignal,
            # pandas.Series, pandas.DataFrame
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
                    
            elif isinstance(x, neo.ChannelIndex):
                if len(args) == 0:
                    args = (x.index, )
                    
                for attr in x._all_attrs:
                    if attr[0] != "index":
                        if attr[0] not in kw:
                            kw[attr[0]] = getattr(x, attr[0])
                        
            elif isinstance(x, (neo.AnalogSignal, datasignal.DataSignal)):
                if len(args) == 0:
                    args = (x,) # takes units & time units from x
                    
                for attr in x._all_attrs:
                    if attr[0] != "signal":
                        if attr[0] not in kw:
                            kw[attr[0]] = getattr(x, attr[0])
                        
            elif isinstance(x, (neo.IrregularlySampledSignal, datasignal.IrregularlySampledDataSignal)):
                if len(args) < 2:
                    args = (x.times, x,)
                    
                for attr in x._all_attrs:
                    if attr[0] not in ("times", "signal"):
                        if attr[0] not in kw:
                            kw[attr[0]] = getattr(x, attr[0])
                        
            elif isinstance(x, neo.SpikeTrain):
                if len(args)  == 0:
                    args = (x.times, x.t_stop,)
                    
                for attr in x._all_attrs:
                    if attr[0] not in ("times", "t_stop"):
                        if attr[0] not in kw:
                            kw[attr[0]] = getattr(x, attr[0])
                        
            elif isinstance(x, neo.ImageSequence):
                if len(args) == 0:
                    args = (x, )
                    
                for attr in x._all_attrs:
                    if attr[0] != "image_data":
                        if attr[0] not in kw:
                            kw[attr[0]] = getattr(x, attr[0])
                
            elif isinstance(x, (neo.Block, neo.Segment, neo.Unit)):
                if len(args) == 0:
                    args = (x, )
                    
            elif isinstance(x, (neo.Epoch, neo.Event)):
                for attr in x._all_attrs:
                    if attr[0] not in kw:
                        kw[attr[0]] = getattr(x, attr[0])
                        
            elif isinstance(x, pq.Quantity):
                if "units" not in kw:
                    kw["units"] = x.units
                
                if "dtype" not in kw:
                    kw["dtype"] = x.dtype
                    
                if "buffer" not in kw:
                    kw["buffer"] = x.data
                
                kw["default_value"] = x
                
                kw["allow_none"] = allow_none
                
                return QuantityTrait(x, **kw)
                
            elif isinstance(x, np.ndarray):
                #shp = tuple(list(x.shape))
                
                if "dtype" not in kw:
                    kw["dtype"] = x.dtype
                    
                if "buffer" not in kw:
                    kw["buffer"] = x.data
                    
                kw["default_value"] = x
                kw["allow_none"] = allow_none
                
                return ArrayTrait(x, **kw)
                    
            elif isinstance(x, pd.DataFrame):
                if len(args) == 0:
                    args = (x, )
                
            elif isinstance(x, pd.Series):
                if len(args) == 0:
                    args = (x, )
                    
                
            trait = Instance(klass = x.__class__, args=args, kw=kw, allow_none = allow_none)
            trait.default_value = x
            return trait
    
class TestTrait(TraitSetMixin, List):
    def __init__(self, *args, **kwargs):
        List.__init__(self, **kwargs)
        super().__init__()
        #TraitSetMixin.__init__(self)
        
