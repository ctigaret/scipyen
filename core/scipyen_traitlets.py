"""Very much work in progress.
FIXME/TODO:2022-01-29 13:29:19
The issue with collection "traits", I think, is that changes to the contents of
the collection by using builtin API (e.g. list.append, deque.appendLeft) or 
directly changing the value of an element does NOT involve the traitlet's 'set'
method (traitlets are implemented using the descriptor protocol).

Hence the traitlet is oblivious to these changes and will not notify any 
observers that registered with it.


A workaround is to create an object of the appropriate type and assign it via 
the corresponding property setter (i.e. avoid modifying the collection instance
in place)

"""
import sys, typing, dataclasses, traceback
from warnings import warn, warn_explicit
from collections import deque
from collections.abc import MutableMapping
import enum
from enum import (EnumMeta, Enum, IntEnum, )
import numpy as np
import quantities as pq
import pandas as pd
import neo

import six

import traitlets

from traitlets import (HasTraits, MetaHasTraits, TraitType, All, Any, Bool, CBool, Bytes, CBytes, 
    Dict, Enum, Set, Int, CInt, Long, CLong, Integer, Float, CFloat, 
    Complex, CComplex, Unicode, CUnicode, CRegExp, TraitError, Union, Undefined, 
    Type, This, Instance, TCPAddress, List, Tuple, UseEnum, ObjectName, 
    DottedObjectName, CRegExp, ForwardDeclaredType, ForwardDeclaredInstance, 
    link, directional_link, validate, observe, default,
    observe_compat, BaseDescriptor, HasDescriptors, Container,
    )
from traitlets.utils.bunch import Bunch
from traitlets.utils.descriptions import (describe, class_of, add_article, repr_type)

from traitlets.traitlets import is_trait

from .traitcontainers import DataBag
from .datasignal import DataSignal, IrregularlySampledDataSignal
from .datazone import DataZone
from .triggerevent import DataMark, TriggerEvent

from .utilities import (gethash, safe_identity_test)

from .prog import timeblock

# NOTE: DataBagTrait <- Instance <- ClassBasedTraitType <- TraitType <- BaseDescriptor

# NOTE: neo and neo-like types that take 0-argument __init__ (a.k.a default c'tor):
# Block, Segment, Group, Epoch, Event, DataZone, DataMark, TriggerEvent
#
# neo and neo-lke objects that require positional arguments in the c'tor:
# AnalogSignal, IrregularlySampledSignal, DataSignal, IrregularlySampledDataSignal,
# ImageSequence, ChannelView, and pretty much everything else in the neo's core
# types hierarchy
#
# Other neo types outside neo's core types hierarchy:
# ArrayDict, SpikeTrainList, 
# RegionOfInterest, CircularRegionOfInterest, RectangularRegionOfInterest, PolygonRegionOfInterest

TRAITSMAP = {           # use casting versions
    None:       (Any,),
    type(None): (Any,),
    bool:       (CBool,),
    int:        (CInt,),
    float:      (CFloat,),
    complex:    (CComplex,),
    bytes:      (CBytes,),
    str:        (Unicode,),
    # str:        (CUnicode,),
    list:       (List,),
    #deque:      (List,),
    set:        (Set,),
    frozenset:  (Set,),
    tuple:      (Tuple,),
    dict:       (Dict,),
    EnumMeta:   (Any,),
    Enum:       (Any,), # IntEnum inherits from int and Enum
    #EnumMeta:   (UseEnum,),
    #Enum:       (UseEnum,), # IntEnum inherits from int and Enum
    type:       (Any,),    # e.g., type(type(None))
    #type:       (Instance,),    # e.g., type(type(None)) # Instance requires arguments to instantiate default value
    property:   (Any,),
    #property:   (DottedObjectName,),
    #type:       (Type,),    # e.g., type(type(None))
    #function:   (Any,)
    }

class ScipyenTraitTypeMixin:
    def __delete__(self, obj):
        """Fails silently when owner is of wrong type"""
        if hasattr(obj, "remove_trait") and hasattr(obj, "_trait_values") and hasattr(obj, "traits"):
            if self.name in obj.traits():
                trait_to_remove = obj.traits()[self.name]
                obj.remove_trait(self.name, trait_to_remove)
                old_value = obj._trait_values.pop(self.name, None)
                obj._notify_trait(self.name, old_value, Undefined,
                                  change_type="removed")
                
class DictTrait(Dict, ScipyenTraitTypeMixin):
    info_text = "Traitlet for mapping types (dict) that is sensitive to content changes"
    default_value = dict() # default value of the Trait instance
    klass = dict
    _value_trait = None # type of mapping values - could be None
    _key_trait = None # type of key values (typically a Hashable) - can be None in which case no validation happens
    _valid_defaults = (dict,)
     
    def __init__(self, value_trait=None, per_key_traits=None, key_trait=None,
                 default_value=Undefined, **kwargs):
        super(ScipyenTraitTypeMixin, self).__init__()
            
        # NOTE: traitlets.Undefined is an instance of traitlets.Sentinel
        self.hashed = 0
        if default_value is None and not kwargs.get("allow_none", False):
            default_value = Undefined
            
        # when value_trait is given, but no default_value was given
        if default_value is Undefined and value_trait is not None:
            if not is_trait(value_trait):
                default_value = value_trait
                value_trait = None
                
        if default_value is Undefined:
            default_value = self.klass()
            args = ()
            
        elif isinstance(default_value, self._valid_defaults):
            args = (default_value,)
            
        else:
            raise TypeError(f"default_value expected to be {None} or one of {self._valid_defaults}")
        
        if is_trait(value_trait):
            self._value_trait = value_trait() if isinstance(value_trait, type) else value_trait
            
        elif value_trait is not None:
            raise TypeError(f"Expecting 'value_trait to be a Trait or None; got {type(value_trait_.__name__)}")
        
        if is_trait(key_trait):
            if isinstance(key_trait, type):
                warn(
                    "Traits should be given as instances, not types (for example, `Int()`, not `Int`)"
                    " Passing types is deprecated in traitlets 4.1.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                key_trait = key_trait()
            self._key_trait = key_trait
            
        elif key_trait is not None:
            raise TypeError("`key_trait` must be a Trait or None, got %s" % repr_type(key_trait))

        self._per_key_traits = per_key_traits
        
        super().__init__(value_trait=value_trait, per_key_traits=per_key_traits,key_trait=key_trait,
                         default_value=default_value, **kwargs)
        
#     def validate(self, obj, value):
#         # return super().validate(obj, value)
#         value = super().validate(obj, value)
#         if value is None:
#             return value
#         value = self.validate_elements(obj, value)
#         return value
# 
# #         if isinstance(value, self.klass):
# #             return value
# #         
# #         elif isinstance(value, self._valid_defaults):
# #             return self.klass(value)
    
    def validate_elements(self, obj, value):
        value = super(DictTrait, self).validate_elements(obj, value)
        
        length = len(value)
        
        # if length < self._minlen or length > self._maxlen:
        #     self.length_error(obj, value)

        return super().validate_elements(obj, value)

    def set(self, obj, value):
        """
        Additional notifications:
        • change in dict length (i.e. number of keys)
        • change in key types
        • change in value types

        No notifications are issued for changes in the values, as the checks can
        be too expensive and/or prone to fail.
        
        """
        new_value = self._validate(obj, value)
        silent = True 
        change_type = "modified"
        
        if self.name and self.name in obj._trait_values and self.name in obj.traits():
            old_value = obj._trait_values[self.name]
        else:
            old_value = self.default_value
            silent=False
            change_type="new"
        
        try:
            if silent:
                silent = bool(old_value == new_value)
            
            # NOTE: 2021-08-19 16:17:23
            # check for change in contents
            if silent:
                new_hash = gethash(new_value)
                silent = (new_hash == self.hashed)
                if not silent:
                    self.hashed = new_hash
        except:
            # if there is an error in comparing, default to notify
            silent = False
            
        # print(f"{self.__class__.__name__}.set: silent {silent}, hashed {self.hashed}")
        obj._trait_values[self.name] = new_value
        
        # print(f"\n{self.__class__.__name__} object {self.name} .set({obj}, {value}) → old_value = {old_value}; new_value = {new_value}; notify_trait = {not silent}")

        if silent is not True:
            # print(f"{self.__class__.__name__}.set(...) will notify")
            # obj._notify_trait(self.name, old_value, new_value)
            obj._notify_trait(self.name, old_value, new_value, 
                              change_type=change_type)
  
            
class ListTrait(List, ScipyenTraitTypeMixin):
    """TraitType that ideally should notify:
    a) when a list contents has changed (i.e., gained/lost members)
    b) when an element in the list has changed (either a new value, or a new type)
    c) when the order of the elements has changed
    """
    info_text = "Traitlet for lists that is sensitive to content changes"
    default_value = []
    klass = list
    _trait = None
    _valid_defaults = (list,tuple)
    
    
    def __init__(self, trait=None, traits=None, default_value=Undefined, **kwargs):
        """
        trait: in the super() List traitype, `traits` restricts the type of elements
                in the container to that TraitType -- i.e. all must be of the same type
    
                this is OK for homogeneous sequences
    
        traits: when specified, is a sequence of TypeTrais, so that the instance 
                is valid when the list's elements are of these types - the intention
                is to accomodate heterogeneous sequences
    
            FIXME/TODO: there are two options:
                • we pass a list of traitlets with the same number of elements as the
                instance of ListTrait - meaning that it will be valid if 
                traitlet[k] validates the kth element in the ListTrait
                 - a bit of overkill: for large lists we effectively pass a second
                list as large as the list 
    
                • we pass a list of traitlets such that an element in the ListTrait
                is valid IF it can be validated by at least one of the traitlets
                in here - question is, how to do that?
                WARNING this may introduce a BUG by casting a value to another
                type, depending on thhe _cast_types of the particular trait used
                to validate
    
        default_value: list, tuple, set 
        """
        super(ScipyenTraitTypeMixin, self).__init__()
        self._traits = traits # a list of traits, one per element - corresponds to per_key_traits in Dict
        self._length = 0
        
        self.hashed = 0
        
        allow_none = kwargs.pop("allow_none", True) # make this True by default
        
        
        # initialize the List (<- Container <- Instance) NOW
        # NOTE: 2022-11-02 22:45:46
        # this will also set the super() defaults:
        # self._minlen = tratielts.Int(0), 
        # self._maxlen = traitlets.Int(sys.maxsize)
        super(ListTrait, self).__init__(trait=trait, default_value=default_value, **kwargs)
        
        # NOTE: for our purposes we don't really need the validation logic!
            
    def instance_init(self, obj=None):
        # print(f"ListTrait {self.__class__.__name__}")
        if obj is None:
            obj = self
        if isinstance(self._trait, TraitType):
            self._trait.instance_init(obj)
        super(Container, self).instance_init(obj)
        
    def validate_elements(self, obj, value):
        # NOTE: 2021-08-19 11:28:10 do the inherited validation first
        value = super(ListTrait, self).validate_elements(obj, value)
        # NOTE: 2021-08-19 11:18:25 then the customized one
        # imitates see traitlets.Dict.validate_elements
        use_list = bool(self._traits) # may be None
        default_to = (self._trait or Any())
        validated = []
        
#         if isinstance(value, self.klass):
#             self.length = len(value)
#         
        if not use_list and isinstance(default_to, Any):
            return value
        
        for k,v in enumerate(value):
            vv = list()
            for t in self._traits:
                # FIXME: 2022-11-02 23:18:08 potential BUG
                try:
                    v_ = self._traits[k]._validate(obj, v)
                    vv.append(v_)
                except TraitError:
                    pass
            if len(vv):
                validated.append(vv[0])
                    
        return self.klass(validated)

    def set(self, obj, value):
        """Overrides List.set to check for special hash.
        This is supposed to also detect changes in the order of elements.
        """
        new_value = self._validate(obj, value)
        silent = True
        change_type = "modified"
        
        # if self.name in obj._trait_values:
        if self.name and self.name in obj._trait_values and self.name in obj.traits():
            old_value = obj._trait_values[self.name]
        else:
            old_value = self.default_value
            silent=False
            change_type="new"

        try:
            # print(f"{self.__class__.__name__}.set: old_value = {old_value}, new_value = {new_value}")
            if silent:
                silent = bool(old_value == new_value)
                # print(f"{self.__class__.__name__}.set: old_value == new_value => silent {silent}")
            
            
            # NOTE: 2021-08-19 16:17:23
            # check for change in contents
            if silent:
                new_hash = gethash(new_value)
                silent = (new_hash == self.hashed)
                # print(f"{self.__class__.__name__}.set: new_hash == self.hashed => silent {silent}")
                
                if not silent:
                    self.hashed = new_hash
        except:
            traceback.print_exc()
            # if there is an error in comparing, default to notify
            silent = False
            
        # print(f"\n{self.__class__.__name__} object {self.name} .set({obj}, {value}) → old_value = {old_value}; new_value = {new_value}; notify_trait = {not silent}")
            
        obj._trait_values[self.name] = new_value
        
        # print(f"{self.__class__.__name__}.set: silent {silent}, hashed {self.hashed}")
        
        if not silent:
            # obj._notify_trait(self.name, old_value, new_value)
            obj._notify_trait(self.name, old_value, new_value,
                              change_type=change_type)
            
class NdarrayTrait(Instance, ScipyenTraitTypeMixin):
    info_text = "Trait for numpy arrays"
    default_value = np.array([])
    klass = np.ndarray
    
    def __init__(self, args=None, kw=None, **kwargs):
        # allow 1st argument to be the array instance
        super(ScipyenTraitTypeMixin, self).__init__()
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
 
class NeoBaseNeoTrait(Instance, ScipyenTraitTypeMixin):
    """Traitlet for BaseNeo objects
    """
    info_text = "Trais for neo.baseneo.BaseNeo"
    default_value = neo.baseneo.BaseNeo()
    klass = neo.baseneo.BaseNeo
    _cast_types = tuple()
    _valid_defaults = (neo.baseneo.BaseNeo,)
    _characteristic_attrs_ = tuple() # only needed for container-like objects to trap changs to inner containers
    
    def __init__(self, value_trait=None, default_value = Undefined, **kwargs):
        # print(f"{self.__class__.__name__}.__init__")
        super(ScipyenTraitTypeMixin, self).__init__()
        self.hashed = 0
        trait = kwargs.pop('trait', None)
        if trait is not None:
            if value_trait is not None:
                raise TypeError("Found a value for both `value_trait` and its deprecated alias `trait`.")
            value_trait = trait
            warn(
                "Keyword `trait` is deprecated in traitlets 5.0, use `value_trait` instead",
                DeprecationWarning,
                stacklevel=2,
            )
            
        if default_value is None and not kwargs.get("allow_none", False):
            default_value = Undefined
            
        if default_value is Undefined and value_trait is not None:
            if not is_trait(value_trait):
                default_value = value_trait
                value_trait = None
                
        if default_value is Undefined:
            default_value = pq.Quantity([])
            args = ()
            
        elif isinstance(default_value, self._valid_defaults):
            args = (default_value,)
            
        else:
            raise TypeError(f"default_value expected to be {None} or one of {self._valid_defaults}")
        
        if is_trait(value_trait):
            self._trait = value_trait() if isinstance(value_trait, type) else value_trait
            
        elif trait is not None:
            raise TypeError(f"Expecting 'value_trait to be a Trait or None; got {type(value_trait_.__name__)}")
        
        super().__init__(klass = self.klass, args=args, **kwargs) # init the Instance
    
    def info(self):
        if isinstance(self.klass, six.string_types):
            klass = self.klass
        else:
            klass = self.klass.__name__
            
        result = klass
        
        if self.allow_none:
            result += ' or None'

        return result
            
    def make_dynamic_default(self):
        return self.klass()
            
    def validate_elements(self, obj, value):
        return super().validate_elements(obj, value) # returns value if value is an instance of self.klass
    
    def compare_element(self, x,y):
        result = False
        if all(isinstance(v, np.ndarray) for v in (x,y)):
            result = x.shape == y.shape
            if result:
                result = x.dtype == y.dtype
                
                if result:
                    result = np.all(x == y)
                    
        elif not any(isinstance(v, np.ndarray) for v in (x,y)):
            result = x == y
            
        return result
    
    def compare_elements(self, old_value, new_value):
        """Returns True if old_value and new_value are identical.
        Identity can mean anything from them being the same class, or their
        children (up to a certain nesting level) are identical.
        
        This method does NOT serve as a validation mechanism for the trait purpose.
        Instead, it merely determines whether values passed to the trait's `set` 
        method is worthy of launching a change notification through the 
        `HasTraits` traits observing mechanism.
        
        This SHOULD be overloaded in subclasses...
    
        Furthermore,this method should be called from inside the `set` method
        of the traitlet
        """
        # NOTE: 2023-05-23 10:58:16
        # this is too expensive ⇒ simplify it !
        try:
            # check class
            result = type(new_value) == type(old_value) and isinstance(new_value, self.klass)
            
            if result and hasattr(self.klass, "_all_attrs"):
                # check attributes
                attrs = tuple((getattr(new_value, a[0], None), getattr(old_value, a[0], None)) for a in old_value._all_attrs)
                
                result = all(self.compare_element(c_new, c_old) for (c_new, c_old) in attrs)
                
            # NOTE: 2023-05-23 10:58:42
            # see NOTE: 2023-05-23 10:58:16
            # NOTE: 2023-05-23 22:24:41
            # can be very expensive
            if result:
                # check annotations
                result = new_value.annotations == old_value.annotations
                # result = safe_identity_test(new_value.annotations, old_value.annotations)
            
            
            # if result:
            #     # so far silent is True when the observed knows about us
            #     # check it we changed and notify
            #     new_hash = gethash(new_value)
            #     silent = (new_hash == self.hashed)
            #     # result = new_value == old_value
            #     # result = safe_identity_test(new_value, old_value)
        except:
            traceback.print_exc()
            result = False
            
        return result
            
    def error(self, obj, value):
        kind = type(value)
        if six.PY2 and kind is InstanceType:
            msg = 'class %s' % value.__class__.__name__
        else:
            msg = '%s (i.e. %s)' % ( str( kind )[1:-1], repr( value ) )

        if obj is not None and not isinstance(value, self.klass):
            e = f"The {self.name} trait of {class_of(obj)} instance must be {self.info()}, but a value of {msg} was specified."
        else:
            types = (self.klass, type(None)) if self.allow_none else (self.klass, )
            if not isinstance(value, types):
                e = f"The {self.name} trait must be {self.info()}, but a value of {msg} was specified."

        raise TraitError(e)
    
    def set(self, obj, value):
        """See traitlets.traitlets.TraitType.set for details
        """
        # with timeblock(f"{type(value).__name__}"):
        # this one simply checks if value is the appropriate class, or None (if allow_none is True)
        new_value = self._validate(obj, value) 
        new_hash = gethash(new_value)
            
        # NOTE: 82021-10-20 09:13:51
        # to also flag addition of this trait:
        # when DataBag is empty, its hashed value will be 0 thus not different 
        # from the default; therefore when an old_value of this trait does not
        # exist we should be notifying the observer
        silent = True 
        
        change_type = "modified"
        
        if self.name and self.name in obj._trait_values and self.name in obj.traits():
            old_value = obj._trait_values[self.name]
        else:
            old_value = self.default_value
            self.hashed = gethash(old_value)
            silent=False
            change_type="new"
        
        # print(f"\n{self.__class__.__name__} <for object {self.name}>.set(...) → first test silent = {silent}")
        
        try:
            # FIXME/TODO: 2023-05-25 22:37:35
            # there should be a better way than this;
            # othwerise, this keeps notifying a change when it shouldn't, and 
            # this can cause bottleneck downstream (e.g. in workspace model a 
            # Modifed change triggers updating the row - which scales poorly with 
            # the number of variables in the workspace)
            if silent:
                silent = self.compare_elements(old_value, new_value)
                
            # print(f"\n{self.__class__.__name__}<NeoBaseNeoTrait>[{self.name}] after compare_elements → silent = {silent}")
            if silent:
                silent = bool(id(old_value) == id(new_value))
                
            if silent:
                silent = bool(old_value == new_value) # this must be overwritten for signal traits !
                
            if silent:
                silent = (new_hash == self.hashed)
                # print(f"{self.__class__.__name__}.set: new_hash == self.hashed => silent {silent}")
                
#                 if not silent:
#                     self.hashed = new_hash
#             
        except:
            traceback.print_exc()
            silent = False
            
        # print(f"\n{self.__class__.__name__} <for object {self.name}>.set({value}) → notify_trait = {not silent}")
                
        obj._trait_values[self.name] = new_value
        
        if not silent:
            self.hashed = new_hash
    
        # print(f"\n{self.__class__.__name__} object {self.name} .set({obj}, {value}) → old_value = {old_value}; new_value = {new_value}; notify_trait = {not silent}")
        if silent is not True:
            # print(f"\n{self.__class__.__name__}<NeoBaseNeoTrait>[{self.name}] to notify {change_type}")
            # obj._notify_trait(self.name, old_value, new_value)
            obj._notify_trait(self.name, old_value, new_value,
                              change_type=change_type)
        
class NeoContainerTrait(NeoBaseNeoTrait):
    klass = neo.container.Container
    info_text = f"Traitlet for {klass}"
    default_value = klass()
    _cast_types = tuple()
    _valid_defaults = (klass,)
    _characteristic_attrs_ = ("_container_child_containers", "_data_child_containers")
    
    
    def __init__(self, value_trait=None, default_value = Undefined, **kwargs):
        # print(f"{self.__class__.__name__}<NeoContainerTrait>.__init__")
        super().__init__(value_trait=value_trait, default_value=default_value, **kwargs)

        # NOTE: 2023-06-01 09:39:20
        # try this
        obj = self.default()
        self.characterisics = self.get_characteristics(obj)
        # self.container_child_containers_lenghts, self.data_child_containers_lenghts = self.get_container_lengths(obj)
        
    def get_characteristics(self, obj):
        characteristics = {}
        
        for c in self._characteristic_attrs_:
            if hasattr(obj, c):
                ccc = dict(map(lambda x: (x, getattr(obj, x, None)), getattr(obj, c) ))
                characteristics[c] = dict((c, len(v) if hasattr(v, "__iter__") else -1) for c,v in ccc.items())
                
        return characteristics
                
            
#     def get_container_lengths(self, obj):
#         if hasattr(obj, "_container_child_containers"):
#             ccc = dict(map(lambda c: (c, getattr(obj, c, None)), obj._container_child_containers))
#             container_child_containers_lenghts = dict((c, len(v) if hasattr(v, "__iter__") else -1) for c,v in ccc.items())
#         else:
#             container_child_containers_lenghts = {}
#             
#         if hasattr(obj, "_data_child_containers"):
#             ccc = dict(map(lambda c: (c, getattr(obj, c, None)), obj._data_child_containers))
#             data_child_containers_lenghts = dict((c, len(v) if hasattr(v, "__iter__") else -1) for c,v in ccc.items())
#         else:
#             data_child_containers_lenghts = {}
#             
#         return container_child_containers_lenghts, data_child_containers_lenghts
    
    def compare_elements(self, old_value, new_value):
        try:
            result = super().compare_elements(old_value, new_value)
            
            if result:
                # check container children count
                result = len(new_value.container_children_recur) == len(old_value.container_children_recur)
                
                if result:
                    # check data children count
                    result = len(new_value.data_children_recur) == len(old_value.data_children_recur)
                    
                    # NOTE: 2023-05-23 15:24:45
                    # potential bottleneck
                    # if result:
                    #     # check data children
                    #     result = all(np.all(c_new == c_old) for (c_new, c_old) in zip(new_value.data_children_recur, old_value.data_children_recur))
        except:
            traceback.print_exc()
            result = False
            
        
        return result
    
    def set(self, obj, value):
        new_value = self._validate(obj,value)
        new_characteristics = self.get_characteristics(new_value)
        # new_container_child_container_lengths, new_data_child_container_lengths = self.get_container_lengths(new_value)
        silent = True
        change_type = "modified"
        
        if self.name and self.name in obj._trait_values and self.name in obj.traits():
            old_value = obj._trait_values[self.name]
        else:
            # print(f"\n{self.__class__.__name__}<NeoContainerTrait>[{self.name}].set() for the first time")
            old_value = self.default_value
            # self.hashed = gethash(old_value)
            self.characteristics = self.get_characteristics(obj)
            # print(f"\n\told characteristics:\n\t{self.characteristics}")
                
            silent=False
            change_type="new"
            
        try:
            if silent:
                silent = self.compare_elements(old_value, new_value)
                # print(f"\n{self.__class__.__name__}<NeoContainerTrait>[{self.name}].set(): compare_elements → {silent}")
                
            if silent:
#                 print(f"\n{self.__class__.__name__}<NeoContainerTrait>[{self.name}]:")
#                 print(f"\n\tcontainer children container lengths new:\n\t{new_container_child_container_lengths}")
#                 print(f"\n\tcontainer children container lengths old:\n\t{self.container_child_containers_lenghts}")
#         
#                 print(f"\n\tdata children container lengths new:\n\t{new_data_child_container_lengths}")
#                 print(f"\n\tdata children container lengths old:\n\t{self.data_child_containers_lenghts}")
        
                
                silent = new_characteristics == self.characteristics
                # print(f"\n{self.__class__.__name__}<NeoContainerTrait>[{self.name}].set(): compare characteristics → {silent}")
                # silent = new_container_child_container_lengths == self.container_child_containers_lenghts and new_data_child_container_lengths == self.data_child_containers_lenghts
                # print(f"\n{self.__class__.__name__}<NeoContainerTrait>[{self.name}].set(): compare container lengths → {silent}")
                
                # if not silent:
                #     self.container_child_containers_lenghts = new_container_child_container_lengths
                #     self.data_child_containers_lenghts = new_data_child_container_lengths
                
        except:
            traceback.print_exc()
            silent = False
                
        obj._trait_values[self.name] = new_value
        
        if not silent:
            self.characteristics = new_characteristics
            # self.container_child_containers_lenghts = new_container_child_container_lengths
            # self.data_child_containers_lenghts = new_data_child_container_lengths
        
        if silent is not True:
            # print(f"\n{self.__class__.__name__}<NeoContainerTrait>[{self.name}].set(): to notify {change_type}")
            # obj._notify_trait(self.name, old_value, new_value)
            obj._notify_trait(self.name, old_value, new_value,
                              change_type=change_type)
        
        
    
class NeoBlockTrait(NeoContainerTrait):
    klass = neo.Block
    info_text = f"Traitlet for {klass}"
    default_value = klass()
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
class NeoGroupTrait(NeoContainerTrait):
    klass = neo.Group
    info_text = f"Traitlet for {klass}"
    default_value = klass()
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
class NeoSegmentTrait(NeoContainerTrait):
    klass = neo.Segment
    info_text = f"Traitlet for {klass}"
    default_value = klass()
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
class NeoChannelViewTrait(NeoBaseNeoTrait):
    klass = neo.view.ChannelView
    info_text = f"Traitlet for {klass}"
    default_value = Undefined
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
class NeoDataObjectTrait(NeoBaseNeoTrait):
    klass = neo.dataobject.DataObject
    info_text = f"Traitlet for {klass}"
    default_value = Undefined
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
    def compare_elements(self, old_value, new_value):
        try:
            result = np.all(super().compare_elements(old_value, new_value))
            if result:
                result = old_value.array_annotations == new_value.array_annotations
                
        except:
            traceback.print_exc()
            result = False
            
        return result
    
    def set(self, obj, value):
        new_value = self._validate(obj, value) 
        silent = True
        change_type = "modified"
        
        if self.name and self.name in obj._trait_values and self.name in obj.traits():
            old_value = obj._trait_values[self.name]
        else:
            old_value = self.default_value
            # self.hashed = gethash(old_value)
            silent=False
            change_type="new"
            
        try:
            if silent:
                silent = self.compare_elements(old_value, new_value)
                
            # print(f"\n{self.__class__.__name__}<NeoDataObjectTrait>[{self.name}] compare_elements → {silent}")
                
            # if silent:
        except:
            traceback.print_exc()
            silent = False
            
        obj._trait_values[self.name] = new_value
        
        if not silent:
            # print(f"\n{self.__class__.__name__}<NeoDataObjectTrait>[{self.name}] to notify {change_type}")
            obj._notify_trait(self.name, old_value, new_value,
                              change_type=change_type)
            
                
class NeoAnalogSignalTrait(NeoDataObjectTrait):
    klass = neo.AnalogSignal
    info_text = f"Traitlet for {klass}"
    default_value = Undefined
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
    def make_dynamic_default(self):
        return self.klass([0.], units=pq.s, sampling_rate=1*pq.Hz)
            
class NeoIrregularlySampledSignalTrait(NeoDataObjectTrait):
    klass = neo.IrregularlySampledSignal
    info_text = f"Traitlet for {klass}"
    default_value = Undefined
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
    def make_dynamic_default(self):
        return self.klass([0.]*pq.s, [0], units = pq.dimensionless)
            
class NeoEpochTrait(NeoDataObjectTrait):
    klass = neo.Epoch
    info_text = f"Traitlet for {klass}"
    default_value = klass()
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
class NeoEventTrait(NeoDataObjectTrait):
    klass = neo.Event
    info_text = f"Traitlet for {klass}"
    default_value = klass()
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
class DataMarkTrait(NeoDataObjectTrait):
    klass = DataMark
    info_text = f"Traitlet for {klass}"
    default_value = klass()
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
    def compare_elements(self, old_value, new_value):
        try:
            result = super().compare_elements(old_value, new_value)
            if result:
                result = old_value.mark_type == new_value.mark_type
                
        except:
            traceback.print_exc()
            result = False
            
        return result
    
class TrigggerEventTrait(NeoDataObjectTrait):
    klass = TriggerEvent
    info_text = f"Traitlet for {klass}"
    default_value = klass()
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
    def compare_elements(self, old_value, new_value):
        try:
            result = super().compare_elements(old_value, new_value)
            if result:
                result = old_value.event_type == new_value.event_type
                
        except:
            traceback.print_exc()
            result = False
            
        return result
    
class DataZoneTrait(NeoDataObjectTrait):
    klass = DataZone
    info_text = f"Traitlet for {klass}"
    default_value = klass()
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
class NeoSpikeTrainTrait(NeoDataObjectTrait):
    klass = neo.SpikeTrain
    info_text = f"Traitlet for {klass}"
    default_value = Undefined
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
    def make_dynamic_default(self):
        return self.klass([0.]*pq.s, 0.)
            
class NeoSpikeTrainListTrait(NeoBaseNeoTrait):
    klass = neo.spiketrainlist.SpikeTrainList
    info_text = f"Traitlet for {klass}"
    default_value = Undefined
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
    def compare_elements(self, old_value, new_value):
        try:
            result = type(old_value) == type(new_value)
            
            if result and isinstance(old_value, self.klass):
                result = len(old_value) == len(new_value)
                
            if result:
                result = np.all(old_value == new_value)
                
            if result:
                result = len(old_value.all_channel_ids) == len(new_value.all_channel_ids)
                    
            if result:
                result = old_value.all_channel_ids == new_value.all_channel_ids and old_value.t_start == new_value.t_start and old_value.t_stop == new_value.t_stop
                    
        except:
            traceback.print_exc()
            result = False
            
        return result
    
class NeoImageSequenceTrait(NeoDataObjectTrait):
    klass = neo.ImageSequence
    info_text = f"Traitlet for {klass}"
    default_value = Undefined
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
    # def compare_elements(self, old_value, new_value):
    #     try:
    #         result = super().compare_elements(old_value, new_value)
    #         if result:
    #             result = old_value.frame_duration == new_value.frame_duration
    
class NeoCircularRegionOfInterestTrait(NeoBaseNeoTrait):
    klass = neo.regionofinterest.CircularRegionOfInterest
    info_text = f"Traitlet for {klass}"
    default_value = Undefined
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
    def compare_elements(self, old_value, new_value):
        try:
            result = super().compare_element(old_value, new_value)
            
            if result:
                result = all(getattr(old_value, a) == getattr(new_value, a) for a in ("x", "y", "radius"))
                
        except:
            traceback.print_exc()
            result = False
            
        return result
    
class NeoRectangularRegionOfInterestTrait(NeoBaseNeoTrait):
    klass = neo.regionofinterest.RectangularRegionOfInterest
    info_text = f"Traitlet for {klass}"
    default_value = Undefined
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
    def compare_elements(self, old_value, new_value):
        try:
            result = super().compare_element(old_value, new_value)
            
            if result:
                result = all(getattr(old_value, a) == getattr(new_value, a) for a in ("x", "y", "height", "width"))
                
        except:
            traceback.print_exc()
            result = False
            
        return result
    
class NeoPolygonRegionOfInterestTrait(NeoBaseNeoTrait):
    klass = neo.regionofinterest.PolygonRegionOfInterest
    info_text = f"Traitlet for {klass}"
    default_value = Undefined
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
    def compare_elements(self, old_value, new_value):
        try:
            result = super().compare_element(old_value, new_value)
            
            if result:
                result = old_value.vertices == new_value.vertices
                
        except:
            traceback.print_exc()
            result = False
            
        return result
    
class NeoArrayDictTrait(NeoBaseNeoTrait):
    klass = neo.dataobject.ArrayDict
    def compare_elements(self, old_value, new_value):
        try:
            result = super().compare_element(old_value, new_value)
            
            if result:
                result = old_value.vertices == new_value.vertices
                
        except:
            traceback.print_exc()
            result = False
            
        return result
    
    info_text = f"Traitlet for {klass}"
    default_value = Undefined
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
    
class QuantityTrait(Instance, ScipyenTraitTypeMixin):
    info_text = "Traitlet for python quantities"
    default_value = pq.Quantity([]) # array([], dtype=float64) * dimensionless
    klass = pq.Quantity
    _cast_types = (np.ndarray, )
    _valid_defaults = (pq.Quantity,)
    
    def __init__(self, value_trait=None, default_value = Undefined, minlen = 0, maxlen = sys.maxsize, **kwargs):
        super(ScipyenTraitTypeMixin, self).__init__()
        self._minlen = minlen
        self._maxlen = maxlen
        self.hashed = 0
    
        trait = kwargs.pop('trait', None)
        if trait is not None:
            if value_trait is not None:
                raise TypeError("Found a value for both `value_trait` and its deprecated alias `trait`.")
            value_trait = trait
            warn(
                "Keyword `trait` is deprecated in traitlets 5.0, use `value_trait` instead",
                DeprecationWarning,
                stacklevel=2,
            )
            
        if default_value is None and not kwargs.get("allow_none", False):
            default_value = Undefined
            
        if default_value is Undefined and value_trait is not None:
            if not is_trait(value_trait):
                default_value = value_trait
                value_trait = None
                
        if default_value is Undefined:
            default_value = pq.Quantity([])
            args = ()
            
        elif isinstance(default_value, self._valid_defaults):
            args = (default_value,)
            
        else:
            raise TypeError(f"default_value expected to be {None} or one of {self._valid_defaults}")
        
        if is_trait(value_trait):
            self._trait = value_trait() if isinstance(value_trait, type) else value_trait
            
        elif trait is not None:
            raise TypeError(f"Expecting 'value_trait to be a Trait or None; got {type(value_trait_.__name__)}")
        
        super().__init__(klass = self.klass, args=args, **kwargs)
        
    # def length_error(self, obj, value):
    #     e = "The '%s' trait of %s instance must be of length %i <= L <= %i, but a value of %s was specified." \
    #         % (self.name, class_of(obj), self._minlen, self._maxlen, value)
    #     raise TraitError(e)

    def validate_elements(self, obj, value):
        # TODO/FIXME 2023-06-01 11:46:27
        # what's this for ?!? get rid of length malarkey
        
        # length = len(value)
        # if length < self._minlen or length > self._maxlen:
        #     self.length_error(obj, value)

        return super().validate_elements(obj, value)

        
    def make_dynamic_default(self):
        return pq.Quantity(self.default_value)
    
    def set(self, obj, value):
        if isinstance(value, str):
            new_value = self._validate(obj, [value])
        else:
            new_value = self._validate(obj, value)
            
        # NOTE: 82021-10-20 09:13:51
        # to also flag addition of this trait:
        # when DataBag is empty, its hashed value will be 0 thus not different 
        # from the default; therefore when and old_value of this trait does not
        # exist we should be notifying the observer
        silent = True 
        
        change_type="modified"

        if self.name and self.name in obj._trait_values and self.name in obj.traits():
            old_value = obj._trait_values[self.name]
        else:
            old_value = self.default_value
            silent=False
            change_type="new"
        
        try:
            if silent:
                # so far silent is True when the observed knows about us
                # check it we changed and notify
                # silent = (new_hash == self.hashed)
                silent = new_value == old_value
            
        except:
            traceback.print_exc()
            silent = False
            
        #print(f"silent {silent}")
                
        obj._trait_values[self.name] = new_value
        
        if silent is not True:
            # obj._notify_trait(self.name, old_value, new_value)
            obj._notify_trait(self.name, old_value, new_value,
                              change_type=change_type)
        
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
    
class DataSignalTrait(NeoDataObjectTrait):
    klass = DataSignal
    info_text = f"Traitlet for {klass}"
    default_value = Undefined
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
    def make_dynamic_default(self):
        return self.klass([0.], units=pq.dimensionless, sampling_rate=1*pq.dimensionless)
        
class IrregularlySampledDataSignalTrait(NeoDataObjectTrait):
    klass = IrregularlySampledDataSignal
    info_text = f"Traitlet for {klass}"
    default_value = Undefined
    _cast_types = tuple()
    _valid_defaults = (klass,)
    
    def make_dynamic_default(self):
        return self.klass([0.]*pq.dimensionless, [0], units=pq.dimensionless)
        
    
    
class DataBagTrait(Instance, ScipyenTraitTypeMixin):
    """Avoid slicing the DataBag type to dict.
    
    When a DataBag is contained in another DataBag, its corresponding trait type
    should be DataBagTrait, such that the trait value type (DataBag) will be
    preserved instead of being cast to a dict (as it would happen if the trait 
    type was traitlets.Dict or a dynamically generated trait type 'Dict_Dyn).
    
    """
    _value_trait = None
    # FIXME 2021-10-11 23:14:13
    # there's something wrong going on here: 
    # the line below at some point calls traitlets.TraitType._validate(self, obj, value)
    # which then raises AttributeError: 'str' object has no attribute '_cross_validation_lock'
    # on line 613, once it goes past value=self.validate(obj, value) on line 612
    # not sure why obj in that context resolves to a str - it is a gremlin somewhere?
    #
    #_key_trait = Unicode   
    
    # NOTE: 2021-10-11 23:16:31
    # for now, disable the key_trait
    _key_trait = None
    klass=DataBag
    
    def __init__(self, value_trait=None, per_key_traits=None, default_value=Undefined,
                 mutable_key_value_traits=True, **kwargs):
        """Avoid back-casting DataBag to dict
        """
        super(ScipyenTraitTypeMixin, self).__init__()
        
        # handle deprecated keywords
        trait = kwargs.pop('trait', None)
        if trait is not None:
            if value_trait is not None:
                raise TypeError("Found a value for both `value_trait` and its deprecated alias `trait`.")
            value_trait = trait
            warn(
                "Keyword `trait` is deprecated in traitlets 5.0, use `value_trait` instead",
                DeprecationWarning,
                stacklevel=2,
            )
        traits = kwargs.pop("traits", None)
        if traits is not None:
            if per_key_traits is not None:
                raise TypeError("Found a value for both `per_key_traits` and its deprecated alias `traits`.")
            per_key_traits = traits
            warn(
                "Keyword `traits` is deprecated in traitlets 5.0, use `per_key_traits` instead",
                DeprecationWarning,
                stacklevel=2,
            )

        self.hashed = 0

        # Handling positional arguments
        if default_value is Undefined and value_trait is not None:
            if not is_trait(value_trait):
                default_value = value_trait
                value_trait = None
                
        elif isinstance(default_value, DataBag):
            self.hashed = gethash(default_value.as_dict) # FIXME/TODO this slows down; must find a way to speed up - give up on gethash?

        if per_key_traits is not None:
            if is_trait(per_key_traits):
                warn(
                    "per_key_traits expected to be a dict, not a TraitType; got %s instead" % type(per_key_traits),
                    SyntaxWarning,
                    stacklevel=2,
                    )
                per_key_traits = None

        # Handling default value
        if default_value is Undefined:
            default_value = DataBag()
        if default_value is None:
            args = None
        elif isinstance(default_value, DataBag):
            args = (default_value,)
        else:
            raise TypeError('default value of DataBagTrait was %s' % default_value)

        # Case where a type of TraitType is provided rather than an instance
        if is_trait(value_trait):
            if isinstance(value_trait, type):
                warn("Traits should be given as instances, not types (for example, `Int()`, not `Int`)"
                     " Passing types is deprecated in traitlets 4.1.",
                     DeprecationWarning, stacklevel=2)
                value_trait = value_trait()
            self._value_trait = value_trait
        elif value_trait is not None:
            raise TypeError("`value_trait` must be a Trait or None, got %s" % repr_type(value_trait))

        #if is_trait(key_trait):
            #if isinstance(key_trait, type):
                #warn("Traits should be given as instances, not types (for example, `Int()`, not `Int`)"
                     #" Passing types is deprecated in traitlets 4.1.",
                     #DeprecationWarning, stacklevel=2)
                #key_trait = key_trait()
            #self._key_trait = key_trait
        #elif key_trait is not None:
            #raise TypeError("`key_trait` must be a Trait or None, got %s" % repr_type(key_trait))

        self._per_key_traits = per_key_traits
        
        self.mutable_key_value_traits = mutable_key_value_traits

        super(DataBagTrait, self).__init__(klass=self.klass, args=args, **kwargs)

    def element_error(self, obj, element, validator, side='Values'):
        e = side + " of the '%s' trait of %s instance must be %s, but a value of %s was specified." \
            % (self.name, class_of(obj), validator.info(), repr_type(element))
        raise TraitError(e)

    def validate(self, obj, value):
        # NOTE: called by TraitType :superclass: _validate() method.
        value = super(DataBagTrait, self).validate(obj, value) # this should always return a DataBag
        
        if isinstance(value, DataBag) and len(value):
            # now, go ahead and validate its contents (or "elements")
            value = self.validate_elements(obj, value)
            #return value
        return value

    def validate_elements(self, obj, value):
        #print("DataBagTrait.validate_elements: obj", obj, "value", value)
        per_key_override = self._per_key_traits or {}
        key_trait = self._key_trait
        value_trait = self._value_trait
        if not (key_trait or value_trait or per_key_override):
            return value

        validated = {}
        for key in value:
            v = value[key]
            #print(f"DataBag.validate_elements, obj: {obj}, value: {value}, key {key}:, v: {v}")
            if key_trait:
                try:
                    key = key_trait._validate(obj, key, v)
                except TraitError as error:
                    self.element_error(obj, key, key_trait, 'Keys')
                    
            if not self.mutable_key_value_traits:
                active_value_trait = per_key_override.get(key, value_trait)
                #print("active_value_trait", active_value_trait)
                if active_value_trait:
                    try:
                        v = active_value_trait._validate(obj, v)
                    except TraitError:
                        self.element_error(obj, v, active_value_trait, 'Values')
                        
            validated[key] = v
        
        # NOTE: 2021-10-21 21:56:00 
        # next line effectively creates a new instance of self containing the
        # validated values - is this why the update of a databag member of a 
        # :class: (A) from another :class: B(A) derived from (A) is broken?
        return self.klass(validated) 
    
    def class_init(self, cls, name):
        if isinstance(self._value_trait, TraitType):
            self._value_trait.class_init(cls, None)
        if isinstance(self._key_trait, TraitType):
            self._key_trait.class_init(cls, None)
        if self._per_key_traits is not None:
            for trait in self._per_key_traits.values():
                trait.class_init(cls, None)
        super(DataBagTrait, self).class_init(cls, name)

    def instance_init(self, obj):
        if isinstance(self._value_trait, TraitType):
            self._value_trait.instance_init(obj)
        if isinstance(self._key_trait, TraitType):
            self._key_trait.instance_init(obj)
        if self._per_key_traits is not None:
            for trait in self._per_key_traits.values():
                trait.instance_init(obj)
        super(DataBagTrait, self).instance_init(obj)

    def from_string(self, s):
        """Load value from a single string"""
        if not isinstance(s, str):
            raise TypeError(f"from_string expects a string, got {repr(s)} of type {type(s)}")
        try:
            return self.from_string_list([s])
        except Exception:
            test = _safe_literal_eval(s)
            if isinstance(test, dict):
                return test
            raise

    def from_string_list(self, s_list):
        """Return a dict from a list of config strings.

        This is where we parse CLI configuration.

        Each item should have the form ``"key=value"``.

        item parsing is done in :meth:`.item_from_string`.
        """
        if len(s_list) == 1 and s_list[0] == "None" and self.allow_none:
            return None
        if (
            len(s_list) == 1
            and s_list[0].startswith("{")
            and s_list[0].endswith("}")
        ):
            warn(
                "--{0}={1} for dict-traits is deprecated in traitlets 5.0. "
                "You can pass --{0} <key=value> ... multiple times to add items to a dict.".format(
                    self.name,
                    s_list[0],
                ),
                FutureWarning,
            )

            return literal_eval(s_list[0])

        combined = {}
        for d in [self.item_from_string(s) for s in s_list]:
            combined.update(d)
        return combined

    def item_from_string(self, s):
        """Cast a single-key dict from a string.

        Evaluated when parsing CLI configuration from a string.

        Dicts expect strings of the form key=value.

        Returns a one-key dictionary,
        which will be merged in :meth:`.from_string_list`.
        """

        if '=' not in s:
            raise TraitError(
                "'%s' options must have the form 'key=value', got %s"
                % (self.__class__.__name__, repr(s),)
            )
        key, value = s.split("=", 1)

        # cast key with key trait, if defined
        if self._key_trait:
            key = self._key_trait.from_string(key)

        # cast value with value trait, if defined (per-key or global)
        value_trait = (self._per_key_traits or {}).get(key, self._value_trait)
        if value_trait:
            value = value_trait.from_string(value)
        return {key: value}
    
    def set(self, obj, value):
        try:
            old_value = obj._trait_values[self.name]
            
        except KeyError:
            #print(f"{instance.name} not found")
            old_value = self.default_value
            
        # NOTE: 2021-10-21 22:02:40# self._validate is inherited from 
        # traitlets.TraitType.
        #
        # This returns value if value is None and allow_none is True;
        #
        # If the TraitYpe subtype has a "validate" attribute (a method) then 
        # calls it, with the expectation it will return the value if validation
        # was successful
        #
        # When mutable_key_value_traits is False, next line will throw exception if
        # new value is a different trait from old_value
        new_value = self._validate(obj, value) 
        silent=True
        
        change_type = "modified"
        
        if self.name and self.name in obj._trait_values and self.name in obj.traits():
            old_value = obj._trait_values[self.name]
        else:
            old_value = self.default_value
            silent=False
            change_type="new"
            
        obj._trait_values[self.name] = new_value
        
        try:
            if silent:
                new_hash = gethash(new_value.as_dict())
                #print("\told %s (hash %s)\n\tnew %s (hash %s)" % (old_value, instance.hashed, new_value, new_hash))
                #print(instance.name, "old hashed", instance.hashed, "new_hash", new_hash)
                silent = (new_hash == self.hashed)
            
                if not silent:
                    self.hashed = new_hash
                
        except:
            traceback.print_exc()
            # if there is an error in comparing, default to notify
            silent = False
            
        if silent is not True:
            # we explicitly compare silent to True just in case the equality
            # comparison above returns something other than True/False
            # obj._notify_trait(self.name, old_value, new_value)
            obj._notify_trait(self.name, old_value, new_value,
                              change_type=change_type)

class DequeTrait(Instance, ScipyenTraitTypeMixin):
    info_text = "Traitlet for deque"
    # klass = _NotifierDeque_
    klass = deque
    _cast_types = (list, tuple)
    _valid_defaults = (deque, list, tuple, set, frozenset) # -- why ?!?
    
    def __init__(self, value_trait=None, default_value=Undefined, 
                 minlen=0, maxlen=sys.maxsize, **kwargs):
        super(ScipyenTraitTypeMixin, self).__init__()
        self._minlen = minlen
        self._maxlen = maxlen
        self.hashed = 0
        
        trait = kwargs.pop('trait', None)
        if trait is not None:
            if value_trait is not None:
                raise TypeError("Found a value for both `value_trait` and its deprecated alias `trait`.")
            value_trait = trait
            warn(
                "Keyword `trait` is deprecated in traitlets 5.0, use `value_trait` instead",
                DeprecationWarning,
                stacklevel=2,
            )
            
        if default_value is None and not kwargs.get("allow_none", False):
            default_value = Undefined
            
        if default_value is Undefined and value_trait is not None:
            if not is_trait(value_trait):
                default_value = value_trait
                value_trait = None
                
        if default_value is Undefined:
            default_value = self.klass()
            #default_value = deque()
            args = ()
            
        elif isinstance(default_value, self._valid_defaults):
            args = (default_value,)
            
        else:
            raise TypeError(f"default_value expected to be {None} or one of {self._valid_defaults}")
        
        if is_trait(value_trait):
            self._trait = value_trait() if isinstance(value_trait, type) else value_trait
            
        elif value_trait is not None:
            raise TypeError(f"Expecting 'value_trait to be a Trait or None; got {type(value_trait_.__name__)}")
        
        super().__init__(klass = self.klass, args=args, **kwargs)
        
    def length_error(self, obj, value):
        e = "The '%s' trait of %s instance must be of length %i <= L <= %i, but a value of %s was specified." \
            % (self.name, class_of(obj), self._minlen, self._maxlen, value)
        raise TraitError(e)

    def validate_elements(self, obj, value):
        length = len(value)
        if length < self._minlen or length > self._maxlen:
            self.length_error(obj, value)

        return super().validate_elements(obj, value)

    def set(self, obj, value):
        # if isinstance(value, str):
        #     new_value = self._validate(obj, [value])
        # else:
        #     new_value = self._validate(obj, value)
        
        new_value = self._validate(obj, value)
            
        # NOTE: 82021-10-20 09:13:51
        # to also flag addition of this trait:
        # when DataBag is empty, its hashed value will be 0 thus not different 
        # from the default; therefore when and old_value of this trait does not
        # exist we should be notifying the observer
        silent = True 
        
        change_type="modified"
        
        if self.name and self.name in obj._trait_values and self.name in obj.traits():
            old_value = obj._trait_values[self.name]
        else:
            old_value = self.default_value
            silent=False
            change_type="new"
        
        obj._trait_values[self.name] = new_value
        
        try:
            if silent:
                silent = bool(old_value == new_value)

            if silent:
                # so far silent is True when the observed knows about us
                # check it we changed and notify
                new_hash = gethash(new_value)
                silent = (new_hash == self.hashed)
            
                if not silent:
                    self.hashed = new_hash
                
        except:
            traceback.print_exc()
            silent = False
            
        #print(f"silent {silent}")
                
        if silent is not True:
            # obj._notify_trait(self.name, old_value, new_value)
            obj._notify_trait(self.name, old_value, new_value,
                              change_type=change_type)
        
