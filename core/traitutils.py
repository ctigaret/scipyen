# -*- coding: utf-8 -*-
"""Utilities for programming with traitlets
"""

import enum
import contextlib

from inspect import getmro

import traitlets

from traitlets import (
    HasTraits, MetaHasTraits, TraitType, Any, Bool, CBytes, Dict, Enum, Set,
    Int, CInt, Long, CLong, Integer, Float, CFloat, Complex, Bytes, Unicode,
    TraitError, Union, All, Undefined, Type, This, Instance, TCPAddress,
    List, Tuple, UseEnum, ObjectName, DottedObjectName, CRegExp, link, directional_link,
    ForwardDeclaredType, ForwardDeclaredInstance, validate, observe, default,
    observe_compat, BaseDescriptor, HasDescriptors, is_trait, getmembers,
)

from traitlets.utils.bunch import Bunch as Bunch

#from prog import safeWrapper

def gen_trait_from_type(x, *args, **kwargs):
    """Generates a TraitType for object x.
    
    Prerequisites: Except for enum types (enum.Enum and enumIntEnum)
    x.__class__ should define a "copy constructor", e.g.:
    
    x = SomeClass()
    
    y = SomeClass(x)
    
    For types derived from builtin types, this is taken care of by the python 
    library. Anything else needs 
    
    """
    immclass = getmro(x.__class__)[0]
    # NOTE 2020-07-07 14:42:22
    # to prevent "slicing" of derived classes, 
    
    arg = [x] + [a for a in args]
    
    args = tuple(arg)
    
    kw = kwargs
    
    if x is None:
        return Any()
    
    elif isinstance(x, bool):
        if immclass != bool:
            # preserve its immediate :class:, otherwise this will slice subclasses
            return Instance(klass = x.__class__, args=args, kw=kw)
        
        return Bool(default_value=x)
    
    elif isinstance(x, int):
        if immclass != int:
            return Instance(klass = x.__class__, args=args, kw=kw)
        
        return Int(default_value=x)
    
    elif isinstance(x, float):
        if immclass != float:
            return Instance(klass = x.__class__, args=args, kw=kw)
        
        return Float(default_value=x)
    
    elif isinstance(x, complex):
        if immclass != complex:
            return Instance(klass = x.__class__, args=args, kw=kw)
        
        return Complex(default_value=x)
    
    elif isinstance(x, bytes):
        if immclass != bytes:
            return Instance(klass = x.__class__, args=args, kw=kw)
        
        return Bytes(default_value=x)
    
    elif isinstance(x, str):
        if immclass != str:
            return Instance(klass = x.__class__, args=args, kw=kw)
        
        return Unicode(default_value=x)
    
    elif isinstance(x, list):
        if immclass != list:
            return Instance(klass = x.__class__, args=args, kw=kw)
        
        return List(default_value=x)
    
    elif isinstance(x, set):
        if immclass != set:
            return Instance(klass = x.__class__, args=args, kw=kw)
        
        return Set(default_value = x)
    
    elif isinstance(x, tuple):
        if immclass != tuple:
            return Instance(klass = x.__class__, args=args, kw=kw)
        
        return Tuple(default_value=x)
    
    elif isinstance(x, dict):
        if immclass != dict:
            # preserve its immediate :class:, otherwise this will slice subclasses
            return Instance(klass = x.__class__, args=args, kw=kw)
        
        return Dict(default_value=x)

    
    elif isinstance(x, enum.EnumMeta):
        return UseEnum(x)
    
    else:
        #immclass = getmro(x.__class__)[0]
        if immclass.__name__ == "type":
            return Type(klass=x, default_value = immclass)
        
        else:
            return Instance(klass = x.__class__, args=args, kw=kw)
    
            
class TraitsObserver(HasTraits):
    __mutable_trait_types__ = Bool(default=False)
    __cast_trait_types__ = Bool(default=False)
    
    def add_traits(self, **traits):
        # NOTE 2020-07-04 22:43:58
        # the super's add_traits blows away non-trait attributes
        # because existing traits are reverted to the default value
        mutable = object.__getattribute__(self,"__mutable_trait_types__")
        do_type_casting = object.__getattribute__(self, "__cast_trait_types__")
        
        # NOTE 2020-07-04 22:42:42
        # __length__ and __mutable_trait_types__ need to be reset to their
        # current values (see NOTE 2020-07-04 22:43:58)
        # we do this here in order to avoid triggering a change notification
        traits.update({"__mutable_trait_types__":gen_trait_from_type(mutable),
                       "__cast_trait_types__": gen_trait_from_type(do_type_casting)})
        
        super().add_traits(**traits) # this DOES keep __length__ and __mutable_trait_types__ traits but reverts them to the defaults
        
        # this also works, but triggers a change notification, which we don't 
        # need right now
        #self.__length__ = length
        #self.__mutable_trait_types__ = mutable
        
    def remove_traits(self, **traits):
        current_traits = self.traits()
        keep_traits  = dict([(k, current_traits[k]) for k in current_traits if k not in traits])
        
        mutable = self.__mutable_trait_types__
        do_type_casting = self.__cast_trait_types__
        
        
        # again, this resets the maintenance traits to their default values, 
        # so we need to restore them (see NOTE 2020-07-04 22:43:58 and 
        # NOTE 2020-07-04 22:42:42)
        keep_traits.update({"__mutable_trait_types__":gen_trait_from_type(mutable),
                            "__cast_trait_types__": gen_trait_from_type(do_type_casting)})
        
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
    __length__ = Int(default_value=0)
    __mutable_trait_types__ = Bool(default=False)
    __cast_trait_types__ = Bool(default=False)
    
    def add_traits(self, **traits):
        # NOTE 2020-07-04 22:43:58
        # the super's add_traits blows away non-trait attributes
        # because existing traits are reverted to the default value
        length = object.__getattribute__(self, "__length__")
        mutable = object.__getattribute__(self,"__mutable_trait_types__")
        do_type_casting = object.__getattribute__(self, "__cast_trait_types__")
        
        # NOTE 2020-07-04 22:42:42
        # these "maintenance" traits need to be reset to their current values
        # (see NOTE 2020-07-04 22:43:58)
        # we do this here in order to avoid triggering a change notification
        traits.update({"__length__":gen_trait_from_type(length), 
                       "__mutable_trait_types__":gen_trait_from_type(mutable),
                       "__cast_trait_types__": gen_trait_from_type(do_type_casting)})
        
        super().add_traits(**traits) # this DOES keep __length__ and __mutable_trait_types__ traits but reverts them to the defaults
        
        # this also works, but triggers a change notification, which we don't 
        # need right now
        #self.__length__ = length
        #self.__mutable_trait_types__ = mutable
        
    def remove_traits(self, **traits):
        current_traits = self.traits()
        keep_traits  = dict([(k, current_traits[k]) for k in current_traits if k not in traits])
        
        length = self.__length__
        mutable = self.__mutable_trait_types__
        do_type_casting = self.__cast_trait_types__
        
        
        # again, this resets the maintenance traits to their default values, 
        # so we need to restore them (see NOTE 2020-07-04 22:43:58 and 
        # NOTE 2020-07-04 22:42:42)
        keep_traits.update({"__length__":gen_trait_from_type(length), 
                            "__mutable_trait_types__":gen_trait_from_type(mutable),
                            "__cast_trait_types__": gen_trait_from_type(do_type_casting)})
        
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


    
