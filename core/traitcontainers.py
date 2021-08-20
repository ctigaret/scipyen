# -*- coding: utf-8 -*-
"""
Traitlets-aware containers
An attempt to supplement traitlets package with container traits that can trigger
notifications if their contents change.

2020-09-05 14:20:18 Implemented so far: 

DataBag = behaves like a dictionary where its keys are also
accessed using attribute syntax.

"""
import traceback
from inspect import getcallargs, isfunction, ismethod
from functools import partial
#from traitlets import (HasTraits, TraitType, Eventhandler, Int, Bool, All, 
                       #is_trait, observe,TraitError,)
from traitlets.utils.bunch import Bunch

from .traitutils import (dynamic_trait, trait_from_type, transform_link, is_trait, 
                        HasTraits, TraitType, TraitsObserver, ContainerTraitsObserver,
                        EventHandler,Int, Bool, All, is_trait, observe)

from .prog import safeWrapper
from .strutils import str2symbol

class DataBagTraitsObserver(HasTraits):
    #hidden_traits = ("baglength", "mutable_types", "use_casting", "allow_none",)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def remove_traits(self, **traits):
        current_traits = self.traits()
        keep_traits  = dict([(k, current_traits[k]) for k in current_traits if k not in traits])
        #trait_values = dict([(k, self._trait_values[k]) for k in current_traits if k not in traits])
        
        #self.__class__ = type(self.__class__.__name__,
                              #(HasTraits, ), 
                              #{"changed":self.changed, "remove_traits":self.remove_traits, "_trait_values": trait_values})
        
        self._trait_values.clear()
        
        self.__class__ = type(self.__class__.__name__,
                              (HasTraits, ), 
                              {"changed":self.changed, "remove_traits":self.remove_traits})
        
        self.add_traits(**keep_traits)
        
    def __setstate__(self, state):
        #print("DataBagTraitsObserver.__setstate__: self.__dict__ before setting", self.__dict__)
        #print("DataBagTraitsObserver.__setstate__: I am a ", type(self))
        #print("DataBagTraitsObserver.__setstate__: and I have _trait_notifiers ", hasattr(self, "_trait_notifiers"))
        
        # ATTENTION: 2020-10-30 14:27:36
        # the following completely messes up DataBagTraitsObserver when unpickled
        #self.__dict__ = state.copy()
        
        # ATTENTION: 2020-10-30 14:27:58
        # therefore we UPDATE values in self._trait_values, rather than self__dict__
        
        #print("DataBagTraitsObserver.__setstate__: self.__dict__ after setting", self.__dict__)

        # event handlers are reassigned to self
        cls = self.__class__
        #print("DataBagTraitsObserver.__setstate__: cls", cls)
        for key in dir(cls):
            # Some descriptors raise AttributeError like zope.interface's
            # __provides__ attributes even though they exist.  This causes
            # AttributeErrors even though they are listed in dir(cls).
            #print("DataBagTraitsObserver.__setstate__: key", key)
            try:
                value = getattr(cls, key)
            except AttributeError:
                pass
            else:
                if isinstance(value, EventHandler):
                    #print("DataBagTraitsObserver.__setstate__ value is a ", type(value))
                    value.instance_init(self)

    def __getstate__(self):
        return super().__getstate__()
    
    @observe(All)
    def changed(self, change):
        """for illustration purposes
        WARNING the corresponding ObserveHandler will be removed upon calling
        self.unobserve() or self.unobserve_all()
        """
        ## NOTE: 2020-07-05 18:01:01 that's what you can to with these
        #print("self.changed: change['type']:\n",change["type"], "\n")
        #print("self.changed: change['owner']:\n",change["owner"], "\n")
        #print("self.changed: change['name']:\n",change["name"], "\n")
        #print("self.changed: change['old']:\n",change["old"], "\n")
        #print("self.changed: change['new']:\n",change["new"], "\n")
        return

class DataBag(Bunch):
    """Dictionary with semantics for direct attribute reference and attribute change observer.
    NOTE 2020-07-04 17:48:10
    The implementation is based on traitlets.utils.bunch.Bunch
    ("Yet another implementation of bunch - attribute-access of items on a dict"
    Copyright (c) IPython Development Team.)
    
    New public methods:
    
    sortedkeys()
    sortedvalues()
    sorteditems()
    copy()
    
    Overridden public methods:
    clear() => removes the traits
    update() => updates with new traits
    
    Public methods inherited from dict (indirectly, via Bunch):
    
    keys()
    values()
    items()
    __str__()
    __len__()

    TODO upgrade to defaultdict!
    
    TODO 2020-07-04 23:44:59
    customize observer handlers
    customize link & directional link
    deep copy
    
    """
    # Acquire HasTraits functionality through composition:
    
    # FIXME 2020-07-04 22:50:47
    # when mutable_types is True, TraitType._cast_types kicks in
    # preventing a real trait type change - this may be desirable but should be
    # controlled/configurable
    
    # NOTE 2020-09-05 12:31:25
    # item ACCESS accepts subscript syntax: obj['key']
    # and attribute syntax: obj.key
    # 
    # both access the same entity:
    # 
    #   obj['key'] == obj.key is True
    #
    # item ASSIGNMENT accepts subscript syntax: obj['key'] = value
    # and attribute syntax: obj.key = value
    #
    # both assign to the same entity.
    #
    # the entities are stored as traits inside DataBagTraitsObserver
    # so DataBag API queries/assigns values from/to the traits stored in
    # DataBagTraitsObserver.
    #
    # ATTENTION Whe assigning a new value to an existing trait:
    #
    # By default(*) the type of the new value is expected to be the same as the 
    # type of the trait. For example:
    # 
    #   d = DataBag()
    #   d.x = 1 (an int) - this creates an Int trait type 
    #
    #   d
    #   {'x': 1}
    #
    #   d.x = 1. (a float) ==> TypeError !
    #
    # However, this behaviour can be circumvented (with CAUTION) in two ways:
    #
    # a) casting the type of the new value to the expected type (i.e that of 
    # the trait)
    #
    #   d.use_casting = True
    #   d.x = 1. (a float) ==> OK, but:
    #   
    #   d
    #   {'x': 1} (an int, because the new value 1.0 was cast to an int (which was expected)
    #
    #   WARNING This will fail if the new value cannot be cast to the expected type
    #   d.x = "z" ==> ValueError
    #
    # b) mutating the trait type to accommodate the type of the new value 
    #   WARNING This involves replacing the old trait with a new one, but more
    #   importantly, it may break code that uses the DataBag's attributes expecting
    #   data of a specific type
    #
    #   d.use_casting = False (to avoid casting)
    #   d.mutable_types = True
    
            
    hidden_traits = ("length", "use_mutable", "use_casting", "allow_none")
    
    @staticmethod
    def _make_hidden(**kwargs):
        ret = Bunch([(name, kwargs.pop(name, False)) for name in DataBag.hidden_traits])
        ret.length = 0
        ret.allow_none = True
        ret.use_mutable = True
        return ret
    
    def __init__(self, *args, **kwargs):
        """Constructor for a DataBag.
        
        *args    : a DataBag, or None;
            When a DataBag (or a type that inherits it) this behaves like a 
            copy constructor.
            
            Otherwise it is ignored.
            
        **kwargs : key, value pairs to go into the data bag, and the following
                    options:
        
        use_casting: bool, default is False
            When True, the value set to an EXISTING attribute is cast to the type
            of that attribute, if possible. For example one can assign a float 
            value to an int attribute by automatically casting the float to an int
            (or vice-versa). 
            
            The casting is done through a "copy constructor" mechanism:
            
            e.g. trait expects an int, and the supplied value is a float => the 
            trait will get int(value).
            
        mutable_types: bool, default is False
            When True, allows a new value type to be assigned to an EXISTING
            attribute.
            
        allow_none: bool, default False
            When True, a trait value can be None
            
        handler: a function or method accepting a dict (or Bunch) with the 
            following keys: 'owner', 'type', 'name', 'old', 'new'
            
            Optional, default is None
            
            When given, all the key/value pairs in the DataBag will be observed
            for change (whenever possible)
            
        ATTENTION   mutable_types and use_casting cannot be simultaneously True,
                    but can be simultaneously False.
        
        When both mutable_types and use_casting are given True values, then 
        use_casting takes precedence over mutable_types.
            
        """
        self.__hidden__ = DataBag._make_hidden(**kwargs)
        
        dd = dict(*args, **kwargs)
        
        for name in self.__hidden__.keys():
            dd.pop(name, None)
        
        if self.use_casting:
            self.use_mutable = False
                
        elif self.use_mutable:
            self.use_casting = False
            
        self.__observer__ = DataBagTraitsObserver(**dd)
        
        super().__init__(*args, **kwargs)
        
        if self in dd.keys():
            raise ValueError("One cannot set onself as a trait key!")
        
        
        #trdict = dict(map(lambda x: (x, trait_from_type(dd[x], allow_none=self.__hidden__.allow_none)), dd.keys()))
        
        dtrait = partial(dynamic_trait, allow_none=self.__hidden__.allow_none) 
        
        trdict = dict(map(lambda x: (x[0], dtrait(x[1]) if x[1] is not self else dtrait(x[1].as_dict())), dd.items()))
        
        self.__hidden__.length = len(trdict)
        
        #trdict.update({"baglength": trait_from_type(length),
                        #"mutable_types": trait_from_type(use_mutable==True),
                        #"use_casting": trait_from_type(do_type_cast==True),
                        #"allow_none": trait_from_type(allow_none==True)})
                        
        self.__observer__.add_traits(**trdict)
        
    def __setitem__(self, key, val):
        """Implements indexed (subscript) assignment: self[key] = val
        """
        #if key in ("baglength", "length", "len"):
            #return # read-only but fail gracefully
            #raise KeyError("Key %s is read-only" % key)
        
            
        # NOTE 2020-07-04 17:32:16 :
        # Unlike an ordinary dict which accepts all sorts of hashable objects as
        # keys, emulating attribute access goes against this philosophy.
        #
        # For example, the statement:
        #
        #       d[23] = "a string"
        #
        #
        # assigns the value "a string" to the int key 23 which is hashable, 
        # inside the dict 'd' (even though it's a weird thing to do).
        #
        # However, this paradigm does not translate to that of object attribute 
        # assignment, where attributes are "stored" by a name/identifier
        # (strings containing valid pythonic identifiers).
        #
        # The expected attribute access statement corresponding to the assignment
        # statement shown above would be:
        #
        #       d.23 = "a string"
        #
        # which is syntactically invalid in Python (see "6.3.1 Attribute references" 
        # in The Python Launguage Reference).
        #
        # Therefore, attribute access emulation comes with the price that the key
        # in the key/value pair passed to __setattr__ must be a str, and that str
        # must be a valid Python identifier.
        #
        # NOTE 2020-09-05 12:47:37 One may be tempted to convert the non-string
        # key to its string representation - but that would open a can of worms:
        # the string representation of non numeric types and custom objects is
        # too complex for this purpose.
        
        if not isinstance(key, str):
            raise TypeError("Expecting a string key; got %s instead" % type(key).__name__)
        
        try:
            obs = object.__getattribute__(self, "__observer__") # bypass usual API
            
        except:
            # unpickling doesn't find an observer yet ('cause it is an instance 
            # var but is not pickled in the usual way; restoring it creates 
            # problems therefore we re-create it here)
            obs = DataBagTraitsObserver()
            object.__setattr__(self, "__observer__", obs)

        try:
            hid = object.__getattribute__(self, "__hidden__")
        except:
            hid = DataBag._make_hidden()
            object.__setattr__(self, "__hidden__", hid)
            
        if key in hid:
            hid[key]=val
            
            if key == "use_casting" and hid["use_casting"]:
                hid["use_mutable"] = False
                
            if key == "use_mutable" and hid["use_mutable"]:
                hid["use_casting"] = False

            return
        
        if obs.has_trait(key): # assign value to an existing trait
            # NOTE 2020-09-05 12:52:39 Below, one could use getattr(obs, key)
            # to achieve the same thing as object.__getattribute__(obs, key)
            try:
                old_value = object.__getattribute__(obs, key)
                target_type = type(old_value)
                
                if type(val) != target_type:
                    if hid["use_casting"]:
                        new_val = target_type(val) # this may fail !
                        object.__setattr__(obs, key, new_val)
                        
                    elif hid["use_mutable"]:
                        self.__coerce_trait__(obs, key, val)
                        
                    else:
                        # allow_none takes effect in the call below
                        object.__setattr__(obs, key, val) # may raise TraitError
                        
                else:
                    object.__setattr__(obs, key, val)

                super().__setitem__(key, val)
                        
            except:
                traceback.print_exc()
                
        else:
            # add a new trait
            if val is self:
                val = self.as_dict()
                #raise ValueError("One cannot add a trait to oneself!")
            
            if key not in ("__observer__", "__hidden__") and key not in self.__hidden__.keys():
                trdict = {key: dynamic_trait(val, allow_none = self.allow_none, content_traits=True)}
                #trdict = {key:trait_from_type(val, allow_none = self.allow_none, content_traits=True)}
                obs.add_traits(**trdict)
                object.__setattr__(obs, key, val)
                object.__getattribute__(self, "__hidden__").length = len(trdict)
                
            super().__setitem__(key, val)
            
    def __len__(self):
        obs = object.__getattribute__(self, "__observer__") # bypass self.__getitem__()
        ret = len(obs.traits())
        object.__getattribute__(self, "__hidden__")["length"] = ret
        return ret

    def __str__(self):
        obs = object.__getattribute__(self, "__observer__")
        d = dict((key, getattr(obs, key)) for key in obs.traits())
        return d.__str__()
    
    def __repr__(self):
        obs = object.__getattribute__(self, "__observer__")
        d = dict((key, getattr(obs, key)) for key in obs.traits())
        return d.__repr__()
    
    def __getitem__(self, key):
        """Implements bag[key] (subscript access, or "bracket syntax"")
        """
        obs = object.__getattribute__(self, "__observer__")
        return getattr(obs, key)
    
    def __getattr__(self, key):
        """Implements bag.key (attribute access, or "dot syntax")
        """
        try:
            obs = object.__getattribute__(self, "__observer__")
            
            if obs.has_trait(key):
                val = getattr(obs, key)
                
            else:
                val = self.__getitem__(key) # this exposes access to observer's methods
                
            if isinstance(val, TraitType):
                return val.get(obs)
            
            else:
                return val
            
        except:
            raise #KeyError("%s" % key)
        
    def __hash__(self):
        return sum((hash(v) for v in self.items()))
        
    def __delitem__(self, key):
        """Implements del a[key] where a is a DataBag and key is a str
        """
        try:
            obs = object.__getattribute__(self, "__observer__")
            super().__delitem__(key)
            #obs.length = self.__len__()
            
            #if obs.has_trait(key):
            if key in obs.traits():
                out_traits = {key: obs.traits()[key]}
                obs.remove_traits(**out_traits)
                #obs._trait_values.pop(key, None) # taken care of by obs.remove_traits
                
            object.__getattribute__(self, "__hidden__")["length"] = len(obs.traits())
            
        except:
            raise #KeyError("%s" % key)
        
    def __contains__(self, key):
        """Implements membership test ("in" keyword)
        """
        try:
            obs = object.__getattribute__(self, "__observer__")
            return obs.has_trait(key)
        except:
            raise
            
        
    def __getstate__(self):
        """Returns the DataBagTraitsObserver of this object, wrapped in a dict
        """
        obs = object.__getattribute__(self, "__observer__")
        state = obs.__getstate__()
        d = {"__observer__": state}
        return d
    
    def __setstate__(self, state):
        """Restores the state dictionary
        state: dict
        """
        if "__observer__" in state:
            observer_state = state["__observer__"]
            
        else:
            observer_state = state
            
        if not hasattr(self, "__observer__"):
            # old DataBag versions pickled w/o __observer__
            object.__setattr__(self, "__observer__", DataBagTraitsObserver())
            
        obs = object.__getattribute__(self, "__observer__")
            
        if state is not None:
            obs.__setstate__(observer_state)
    
    def __coerce_trait__(self, obs, key, val):
        old_trait = obs.traits()[key]
        old_type = type(object.__getattribute__(obs, key))
        
        new_trait = trait_from_type(val, allow_none = self.allow_none)
        new_type = type(val)
        
        obs.remove_traits(**{key:old_trait})
        
        obs.add_traits(**{key:new_trait})
        
        object.__setattr__(obs, key, val)
        
        # NOTE 2020-07-05 16:17:27
        # signal the change of trait type
        obs._notify_trait(key, old_type, new_type)
        
    @property
    def observer(self):
        """The HasTraits observer. Read-only
        """
        return self.__observer__
    
    def as_dict(self):
        """Dictionary view
        """
        return self._trait_values
        #return dict((k,v) for k,v in self.items())
        
    def remove_members(self, *keys):
        try:
            obs = object.__getattribute__(self, "__observer__")
            
            current_traits = dict(obs.traits())
            
            current_traits_keys = current_traits.keys()
            
            traits = dict([(key, current_traits[key]) for key in keys if key in current_traits_keys])
            
            obs.remove_traits(**traits)
            
            object.__getattribute__(self, "__hidden__")["length"] = len(obs.traits())
        
        except:
            traceback.print_exc()
            raise
        
    def clear(self):
        try:
            super().clear()
            
            obs = object.__getattribute__(self, "__observer__")
            traits = dict(obs.traits())
            obs.remove_traits(**traits)
            #obs._trait_values.clear() # taken care of by obs.remove_traits
            object.__getattribute__(self, "__hidden__")["length"] = len(obs.traits())
            
        except:
            traceback.print_exc()
            raise
        
    def pop(self, key, *args):
        """Implements a.pop(key, default).
        'a' is a DataBag, 'key' is a str and 'default' is the default value if 
        'key' not in 'a'.
        """
        try:
            ret = self.__getitem__(key)
            self.__delitem__(key) # also updates __hidden__.length
            return ret
        except:
            if len(args) == 0:
                raise
            else:
                return args[0]
        
    @property
    def mutable_types(self):
        return self.__hidden__.use_mutable
    
    @mutable_types.setter
    def mutable_types(self, val:bool):
        if not isinstance(val, bool):
            raise TypeError("Expecting a bool; got %s instead" % type(val).__name__)
        
        self.__hidden__.use_mutable = val
        
        if val:
            self.__hidden__.use_casting = False
        
    @property
    def use_mutable(self):
        return self.__hidden__.use_mutable
    
    @mutable_types.setter
    def use_mutable(self, val:bool):
        if not isinstance(val, bool):
            raise TypeError("Expecting a bool; got %s instead" % type(val).__name__)
        
        self.__hidden__.use_mutable = val
        
        if val:
            self.__hidden__.use_casting = False
        
    @property
    def use_casting(self):
        return self.__hidden__.use_casting
    
    @use_casting.setter
    def use_casting(self, val:bool):
        if not isinstance(val, bool):
            raise TypeError("Expecting a bool; got %s instead" % type(val).__name__)
        
        self.__hidden__.use_casting = val
        
        if val == True:
            self.__hidden__.use_mutable = False
        
    @property
    def allow_none(self):
        return self.__hidden__.allow_none
        
    @allow_none.setter
    def allow_none(self, val):
        if not isinstance(val, bool):
            raise TypeError("Expecting a bool; got %s instead" % type(val).__name__)
        
        self.__hidden__.allow_none = val
        
    def keys(self):
        """Generates a keys 'view'
        """
        obs = object.__getattribute__(self, "__observer__")
        # TODO find a way to return this as a dict_view (mapping proxy)
        # it should be OK for now
        yield from (k for k in obs._trait_values)
    
    def values(self):
        """Generates a values 'view'
        """
        obs = object.__getattribute__(self, "__observer__")
        yield from (obs._trait_values[k] for k in self.keys())
    
    def items(self):
        """Generates an items 'view'
        """
        obs = object.__getattribute__(self, "__observer__")
        yield from ((k, obs._trait_values[k]) for k in self.keys())
        
    @property
    def notifiers(self):
        return self.__observer__._trait_notifiers
    
    def sortedkeys(self):
        """Returns a sorted list of member names
        """
        return sorted([key for key in self.keys()])

    def sortedvalues(self, byname=True):
        """Returns a sorted list of member values.
        
        if byname, the values will be sorted by member names
        
        """
        if byname:
            mmb = self.sortedkeys()
            return [self[m] for m in mmb]
        
        else:
            return sorted([v for v in self.values()])
    
    def sorteditems(self, byname=True):
        if byname:
            return sorted([i for i in self.items()], key=lambda t: t[0])
        else:
            return sorted([i for i in self.items()], key=lambda t: t[1])
        
    def copy(self):
        """Creates a deep copy of this DataBag object.
        
        In: bag1=databag.DataBag({"a":1, "b":2})                                                             

        In: bag1                                                                                             
        Out: {'a': 1, 'b': 2}

        In: bag1_copy = bag1.copy()

        In: bag1_copy                                                                                        
        Out: {'a': 1, 'b': 2}

        In: bag1_copy.a=10                                                                                   

        In: bag1_copy                                                                                        
        Out: {'a': 10, 'b': 2}

        In: bag1                                                                                             
        Out: {'a': 1, 'b': 2}

        In : assert(bag1.a != bag1_copy.a)
        
        NOTE: Does NOT copy the external observer handles (i.e., those set up
        with self.observe(...))
        
        """
        dd = dict(self.items())
        
        # NOTE: 2020-11-02 16:16:28
        # need self.__class__ here for subclasses that call this function
        return self.__class__(dd, 
                       mutable_types = self.mutable_types, 
                       use_casting=self.use_casting,
                       allow_none=self.allow_none)
            
    def update(self, other):
        """Updates this DataBag with key/value pairs from 'other'.
        
        'other' is a subclass of dict.
        
        """
        # leaves self.mutable_types and self.use_casting unchanged
        # the behaviour depends on whether self accepts mutating or casting type
        # traits
        
        if isinstance(other, dict):  # this includes DataBag!
            for key, value in other.items():
                self[key] = value
                
    def observe(self, handler, names=All, type="change"):
        self.__observer__.observe(handler, names=names, type=type)
        
    def unobserve(self, handler, names=All, type="change"):
        self.__observer__.unobserve(handler, names=names, type=type)
        
    def link(self, name, other, other_name):
        """Links trait named 'name' to the trait 'other_name' in 'other'.
        
        The link is bi-directional:  changes of 'self.name' (trait 'name' in this
        object) result in changes to 'other.other_name' (traut 'other_name' in
        'other' object) and vice-versa.
        
        Changes are direct: the value of a designated trait in one obejct is 
            assigned to the designated trait in the other object, and vice-versa.
            
        NOTE:
        To create a bi-directional link which also transforms the value of the 
        trait, create two directional links, e.g.:
        
        link_to("x", other, "xx", transform = func)
        
        and 
        
        link_from("x", other, "xx", transform = inverse_func)
        
        Where 'func' if a transformation function x -> xx and 
        'inverse_func' is the inverse of 'func' performing the inverse
        transformation xx -> x
        
        Parameters:
        ----------
        name: str -  name of the trait of this object
        
        other: DataBag object or a HasTraits object - the object with which the 
            trait 'name' in this DataBag is to be kept in sync,
            
        other_name: str - name of the trait in the  'other' which is to be kept
            in sync with trait 'name' of this DataBag
            
        
        Returns:
        --------
        a traitlets.link object - useful to 'break' the link at a later time, by
            calling its unlink() method.
        
        """
        if isinstance(other, DataBag):
            return link((self.__observer__, name), (other.__observer__, other_name))
            
        elif isinstance(other, HasTraits):
            return link((self.__observer__, name), (other, other_name))
            
        else:
            raise TypeError("'other' expected to be a DataBag or HasTraits; got %s instead" % type(other).__name__)
        
        
    def link_to(self, name, target, target_name, transform=None):
        """Links trait named 'name' to the trait 'target_name' in 'target'.
        
        The link is uni-directional, from this object's trait to the target's 
        trait only.
        
        Changes in 'self.name' (trait 'name' in this DataBag) will update 
        target.target_name ('target_name' trait in 'target'), but changes in 
        target.target_name will not update 'self.name'.
        
        Changes in target.target_name will not update self.name
        
        Parameters:
        ----------
        name: str -  name of the trait of this object
        
        target: DataBag object or a HasTraits object - the object with which the 
            trait 'name' in this DataBag is to be kept in sync
            
        target_name: str - name of the trait in the 'target', which is to be kept
            in sync with trait 'name' of this DataBag
            
        
        Returns:
        --------
        a traitlets.directional_link object - useful to 'break' the link at a 
            later time, by calling its unlink() method.
        
        """
        if isinstance(target, DataBag):
            return directional_link((self.__observer__, name), (target.__observer__, target_name), transform=transform)
            
        elif isinstance(target, HasTraits):
            return directional_link((self.__observer__, name), (target, target_name), transform=transform)
            
        else:
            raise TypeError("'target' expected to be a DataBag or HasTraits; got %s instead" % type(target).__name__)
        
    def link_from(self, name, source, source_name, transform=None):
        """Links trait named 'name' to the trait 'source_name' in 'source'.
        
        The link is uni-directional, from the source's trait to this object's
        trait only.
        
        Changes in 'source.source_name' (trait 'source_name' in source object)
        will update 'self.name' (trait 'name' in this object), but changes in
        'self.name' will not update 'source.source_name'
        
        Changes in self.name will not update source.source_name
        
        Parameters:
        ----------
        name: str -  name of the trait of this object
        
        other: DataBag object or a HasTraits object - the object with which the 
            trait 'name' in this DataBag is to be kept in sync
            
        other_name: str - name of the trait in the  'other' which is to be kept
            in sync with trait 'name' of this DataBag
            
        
        Returns:
        --------
        a traitlets.directional_link object - useful to 'break' the link at a 
            later time, by calling its unlink() method.
        
        """
        if isinstance(source, DataBag):
            return directional_link((source.__observer__, source_name), (self.__observer__, name), transform=transform)
            
        elif isinstance(source, HasTraits):
            return directional_link((source.__observer__, source_name), (self.__observer__, name), transform=transform)
            
        else:
            raise TypeError("'source' expected to be a DataBag or HasTraits; got %s instead" % type(source).__name__)
        
def generic_change_handler(c):
    print("type:",  c.type)
    print("owner:", c.owner)
    print("name:",  c.name)
    print("old:",   c.old)
    print("new:",   c.new)
