# -*- coding: utf-8 -*-
"""traitlets-aware containers
"""
import traceback
from inspect import getcallargs
from traitlets import (HasTraits, TraitType, Int, Bool, All, is_trait, observe,TraitError)
from traitlets.utils.bunch import Bunch

from .traitutils import (gen_trait_from_type, transform_link, 
                        TraitsObserver, ContainerTraitsObserver,
                        HasTraits, TraitType, Int, Bool, All, is_trait, observe)

from .prog import safeWrapper
from .strutils import string_to_valid_identifier

class DataBagTraitsObserver(HasTraits):
    __length__ = Int(default_value=0)
    __mutable_trait_types__ = Bool(default=False) # WARNING experimental
    __cast_trait_types__ = Bool(default=False)
    
    def add_traits(self, **traits):
        # NOTE 2020-07-04 22:43:58
        # the super's add_traits blows away non-trait attributes
        # because existing traits are reverted to the default value
        length = object.__getattribute__(self, "__length__")
        mutable = object.__getattribute__(self,"__mutable_trait_types__")
        do_type_casting = object.__getattribute__(self, "__cast_trait_types__")
        
        # NOTE 2020-07-04 22:42:42
        # __length__ and __mutable_trait_types__ need to be reset to their
        # current values (see NOTE 2020-07-04 22:43:58)
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
    
    Originally defined in Scipyen.core.datatypes using self.__dict__ = self paradigm

    """
    # Acquire HasTraits functionality through composition:
    
    # FIXME 2020-07-04 22:50:47
    # when __mutable_trait_types__ is True, TraitType._cast_types kicks in
    # preventing a real trait type change - this may be desirable but should be
    # controlled/configurable
    
            
    __observer__ = DataBagTraitsObserver()
    
    def __init__(self, *args, **kwargs):
        """Constructor for a DataBag.
        
        *args    : not used
        **kwargs : attributes to go into the data bag, and the 
                    following options:
        
        mutable_types: bool, default is False
            When True, an attribute can be of any type that is
            in the type hierarchy of the current attribute
            
        do_type_cast: bool default False
            When True, and mutable_types is also True,
            setting an attribute casts its value to
            the initial type (which is ... ?)
            
        """
        use_mutable = kwargs.pop("mutable_types", False)
        do_type_cast = kwargs.pop("use_casting", False)
        
        super().__init__(*args, **kwargs)
        
        try:
            
            dd = dict(*args, **kwargs)
            trdict = dict(map(lambda x: (x, gen_trait_from_type(dd[x])), dd.keys()))
            
            trdict.update({"__length__": gen_trait_from_type(self.__len__()),
                           "__mutable_trait_types__": gen_trait_from_type(use_mutable==True),
                           "__cast_trait_types__": gen_trait_from_type(do_type_cast==True)})
            
            # NOTE 2020-07-05 11:54:44
            # this is so that each DataBag instance carries its own instance of
            # DataBagTraitsObserver
            #
            # Because of this, self.copy() creates a new object (i.e. does not
            # have shallow copy semantics anymore)
            obs = DataBagTraitsObserver()
            
            object.__setattr__(self, "__observer__", obs)
            
            super(DataBagTraitsObserver, obs).add_traits(**trdict)
            
            obs.__setattr__("parent", self)
            
        except:
            raise
        
    def __setitem__(self, key, val):
        if key == "__length__":
            raise KeyError("Key '__length__' is read-only")
        
        if key =="__mutable_trait_types__":
            raise KeyError("Key '__mutable_trait_types__' is read-only")
            
        if key == "__cast_trait_types__":
            raise KeyError("Key '__cast_trait_types__' is read-only")
            
        if key == "mutable_types" and isinstance(val, bool):
            self.__observer__.__mutable_trait_types__ = val
            return
        
        if key == "use_casting" and isinstance(val, bool):
            self.__observer__.__cast_trait_types__ = val
            
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
        # reference, where attributes are "stored" by their name (strings containing
        # valid pythonic identifiers).
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
        
        if not isinstance(key, str):
            raise TypeError("Expecting a string key; got %s instead" % type(key).__name__)
        
        obs = object.__getattribute__(self, "__observer__")
        
        #if isinstance(obs, HasTraits):
        if obs.has_trait(key):
            # assigns value to an existing trait
            # NOTE 2020-07-04 21:47:57
            # Emulate a "dict" behaviour, where one can assign to a pre-exising
            # key an object of a different type than the object previously assigned
            # to that key.
            #
            # I agree this is pretty unorthodox and kind of defeats the purpose
            # of having observable traits in the first place, but I could imagine 
            # cases where this may be desirable.
            #
            #object.__setattr__(obs, key, val)
            
            try:
                if type(object.__getattribute__(obs, key)) != type(val):
                    print("type mismatch: expecting %s, got %s instead" % (type(object.__getattribute__(obs, key)).__name__, type(val).__name__))
                    #print("check if accept casting values")
                    if object.__getattribute__(obs, "__cast_trait_types__"):
                        print("casting traits OK")
                        target_type = type(object.__getattribute__(obs, key))
                        
                        new_val = target_type(val) # this may fail
                        object.__setattr__(obs, key, new_val)
                        
                        
                    elif object.__getattribute__(obs, "__mutable_trait_types__"):
                        print("not accepting casting, but can mutate")
                        self.__coerce_trait__(obs, key, val)
                        
                    else:
                        print("force through")
                        #super().__setitem__(key, val) # when all fails don't get here
                        object.__setattr__(obs, "__length__", self.__len__())
                        
                else:
                    #print("all OK")
                    object.__setattr__(obs, "__length__", self.__len__())
                    #super().__setitem__(key, val) # when all fails don't get here
                    
                        
            except:
                print("assignment of attribute failed")
                traceback.print_exc()
                super().__setitem__(key, val) # when all fails don't get here
                object.__setattr__(obs, "__length__", self.__len__())
                
                        
                
        else:
            # adds a new trait
            trdict = {key:gen_trait_from_type(val)}
            obs.add_traits(**trdict)
            super().__setitem__(key, val) # when all fails we don't get here
            obs.__length__ = self.__len__()
            
    def __getitem__(self, key):
        try:
            obs = object.__getattribute__(self, "__observer__")
            if obs.has_trait(key):
                val = getattr(obs, key)
            else:
                val = super().__getitem__(key)
                
            if isinstance(val, TraitType):
                return val.get(obs)
            
            else:
                return val
            
        except:
            raise KeyError("%s" % key)
    
    def __getattr__(self, key):
        try:
            obs = object.__getattribute__(self, "__observer__")
            
            if obs.has_trait(key):
                val = getattr(obs, key)
                
            else:
                val = self.__getitem__(key)
                
            if isinstance(val, TraitType):
                return val.get(obs)
            
            else:
                return val
            
        except:
            raise #KeyError("%s" % key)
        
    def __getattribute__(self, key):
        try:
            val = object.__getattribute__(self,key)
            
            if is_trait(val):
                obs = object.__getattribute__(self, "__observer__")
                
                if obs.has_trait(key):
                    getattr(obs, key)
                    
            return val
        
        except:
            raise #KeyError("%s" % key)
    
    def __delitem__(self, key):
        try:
            obs = object.__getattribute__(self, "__observer__")
            super().__delitem__(key)
            obs.__length__ = self.__len__()
            if obs.has_trait(key):
                out_traits = {key: obs.traits()[key]}
                obs.remove_traits(**out_traits)
            
            
        except:
            raise #KeyError("%s" % key)
        
    def __getstate__(self):
        return self.__observer__.__getstate__()
    
    def __setstate__(self, state):
        self.__observer__.__setstate__(state)
        
    def __coerce_trait__(self, obs, key, val):
        old_trait = obs.traits()[key]
        old_type = type(object.__getattribute__(obs, key))
        
        new_trait = gen_trait_from_type(val)
        new_type = type(val)
        
        obs.remove_traits(**{key:old_trait})
        
        obs.add_traits(**{key:new_trait})
        
        object.__setattr__(obs, key, val)
        
        # NOTE 2020-07-05 16:17:27
        # signal the change of trait type
        obs._notify_trait(key, old_type, new_type)
        
        
    def clear(self):
        try:
            # simply inheriting from Bunch just won't do: we also need to get rid
            # of the traits (except for the maintenance ones)
            super().clear()
            
            obs = object.__getattribute__(self, "__observer__")
            traits = dict([(k, obs.traits()[k]) for k in obs.traits() if k not in ("__length__", "__mutable_trait_types__")])
            obs.remove_traits(**traits)
            obs.__length__ = self.__len__()
            
        except:
            raise
        
    def pop(self, key, default=None):
        try:
            ret = self.__getitem__(key)
            self.__delitem__(key)
            return ret
        except:
            return default
        
    @property
    def mutable_types(self):
        obs = object.__getattribute__(self, "__observer__")
        return getattr(obs, "__mutable_trait_types__")
    
    @mutable_types.setter
    def mutable_types(self, value):
        setattr(self.__observer__, "__mutable_trait_types__", value==True)
        #self.__observer__.__mutable_trait_types__ = value
        
    @property
    def use_casting(self):
        obs = object.__getattribute__(self, "__observer__")
        return getattr(obs, "__cast_trait_types__")
    
    @use_casting.setter
    def use_casting(self, value):
        setattr(self.__observer__, "__cast_trait_types__", value==True)
        #self.__observer__.__cast_trait_types__ = value
        
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
        """Deep copy.
        
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
        dd = dict(self)
        return DataBag(dd, mutable_types = self.mutable_types, use_casting=self.use_casting)
            
        #result.mutable_types = self.mutable_types
        #result.use_casting = self.use_casting
            
        #return result
    
    def update(self, other):
        # leaves self.mutable_types and self.use_casting unchanged
        # the behaviour depends on whether self accepts mutating or casting type
        # traits
        
        if isinstance(other, dict):  # this includes DataBag!
            for key, value in other.items():
                self[key] = value
                
    def observe(self, handler, names=All, type="change"):
        if names == "length":
            names = "__length__"
        self.__observer__.observe(handler, names=names, type=type)
        
    def unobserve(self, handler, names=All, type="change"):
        if names == "length":
            names = "__length__"
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
        
    
def generic_change_handler(chg):
    print("change_handler chg['owner']:\n",chg["owner"], "\n")
    print("change_handler chg['name']:\n",chg["name"], "\n")
    print("change_handler chg['old']:\n",chg["old"], "\n")
    print("change_handler chg['new']:\n",chg["new"], "\n")
