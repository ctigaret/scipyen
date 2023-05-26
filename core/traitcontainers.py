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
import typing
import contextlib
from inspect import getcallargs, isfunction, ismethod
from functools import partial
from pprint import pformat
# from traitlets import (HasTraits, TraitType, Eventhandler, Int, Bool, All,
# is_trait, observe,TraitError,)
from traitlets.utils.bunch import Bunch
import traitlets
from traitlets import (HasTraits, TraitType, Int, Bool, All, observe)

from .traitutils import (dynamic_trait, transform_link)
# from .traitutils import (traitlets, dynamic_trait, transform_link,
#                          HasTraits, TraitType, TraitsObserver,
#                          ContainerTraitsObserver, Int, Bool, All, observe)

from .prog import safeWrapper, timefunc, processtimefunc, timeblock
from .strutils import str2symbol


class DataBagTraitsObserver(HasTraits):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._verbose_ = False

    @property
    def verbose(self):
        return self._verbose_

    @verbose.setter
    def verbose(self, val):
        self._verbose_ = (val == True)
        
    def add_trait(self, traitname:str, traitobject:TraitType) -> None:
        """Binds a TraitType instance to a new attribute of self.
        This must be followed by a call to setattr in the caller.
        """
        # print(f"\n{self.__class__.__name__}.add_trait({traitname}, {traitobject})")
        cls = self.__class__
        traits_dict = self._traits.copy()
        traits_dict[traitname] = traitobject
        
        attrs = {"__module__":cls.__module__}
        
        if hasattr(cls, "__qualname__"):
            attrs["__qualname__"] = cls.__qualname__
            
        # NOTE: 2023-05-26 12:19:51 NOTE 2023-05-26 12:00:34
        attrs["add_trait"] = self.add_trait
        attrs["remove_traits"] = self.remove_traits
        attrs["remove_trait"] = self.remove_trait
        attrs["set_trait_coercive"] = self.set_trait_coercive
        
        attrs.update(traits_dict)
        
        # NOTE: 2023-05-26 12:18:16 see NOTE: 2023-05-26 11:59:19
        self.__class__ = type(cls.__name__, (HasTraits, ), attrs)
        for trait in traits_dict.values():
            trait.instance_init(self)
        
    def set_trait_coercive(self, name:str, traitobj:TraitType, val:typing.Any) -> None:
        """Forcibly sets trait attribute, bypassing validation.
        """
        # copied from tratilets' HasTraits
        # print(f"\n{self.__class__.__name__}.set_trait({name}, {type(value).__name__})")
        cls = self.__class__
        if not self.has_trait(name):
            raise TraitError(f"Class {cls.__name__} does not have a trait named {name}")
        else:
            self.remove_trait(name, self.traits()[name])
            self._trait_values.pop(name, None)
            self.add_trait(name, traitobj)
            object.__setattr__(self, name, val)
            # getattr(cls, name).set(self, value)

    def remove_trait(self, traitname:str, traitobject:TraitType):
        """Unbinds a TraitType instance from an attribute of self.
        """
        # print(f"{self.__class__.__name__}.remove_trait({traitname}, {traitobject})")
        cls = self.__class__
        traits_dict = dict((k,v) for k, v in self._traits.items() if k != traitname)
        # trait_values = dict((k,v) for k,v in self._trait_values.items() if k != traitname)
        trait_values = self._trait_values.copy()
        
        trait_values.pop(traitname, None)
        
        attrs = {"__module__": cls.__module__}
        if hasattr(cls, "__qualname__"):
            attrs["__qualname__"] = cls.__qualname__
            
        # NOTE 2023-05-26 12:00:34
        # these MUST be included, because the new class below inherits straight
        # from HasTraits
        attrs["add_trait"] = self.add_trait
        attrs["remove_traits"] = self.remove_traits
        attrs["remove_trait"] = self.remove_trait
        attrs["set_trait_coercive"] = self.set_trait_coercive
        attrs["_trait_values"] = trait_values
        attrs.update(traits_dict)
        
        # print(f"\tin remove_trait, for new class: traits_dict = {traits_dict}; trait_values = {trait_values}")
        
        # NOTE: 2023-05-26 11:59:19
        # below, DO NOT include cls in the bases tuple or else it will inherit
        # attributes from the very class we want to modify
        # WARNING This also means we need to reinject the new methods, 
        # see NOTE 2023-05-26 12:00:34
        self.__class__ = type(cls.__name__, (HasTraits,), attrs)
        # self.__class__.setup_class(attrs)
        
        for trait in traits_dict.values():
            trait.instance_init(self)
            
        # print(f"hasattr {traitname}: {hasattr(self, traitname)}")
        # print(f"{traitname} lurking in observer: {traitname in dir(self)}")
        # print(f"self._trait_values = {self._trait_values}")
        
    def remove_traits(self, **traits):
        trait_names_objs = list(traits.items())
        
        for traitname, traitobject in trait_names_objs:
            self.remove_trait(traitname, traitobject)
            
            
        # current_traits = self.traits()
        # 
        # valid_traits_to_remove = dict([(k, current_traits[k])
        #                                for k in traits if k in current_traits])
        # 
        # keep_traits = dict([(k, current_traits[k])
        #                    for k in current_traits if k not in valid_traits_to_remove])
        # 
        # values_to_remove = dict([(k, current_traits[k])
        #                          for k in valid_traits_to_remove])

#         keep_traits = dict([(k, current_traits[k])
#                            for k in current_traits if k not in traits])
#
#         values_to_remove = dict([(k, self._trait_values[k])
#                                  for k in valid_traits_to_remove])

        # self._trait_values.clear()
        # 
        # self.__class__ = type(self.__class__.__name__,
        #                       (self.__class__, ),
        #                       {"remove_traits": self.remove_traits})
        # 
        # self.add_traits(**keep_traits)

        # for traitname, traitvalue in values_to_remove.items():
        #     change = Bunch(owner=self, name=traitname,
        #                    old=traitvalue, new=None, type="change")
        #     self.notify_change(change)

    def notify_change(self, change):
        """Notify observers of a change event"""
        if self._verbose_:
            print(f"notify_change: event = {event}")

        return self._notify_observers(change)


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

    NOTE: 2021-10-10 17:00:26
    Acquired traitlets.HasTraits functionality through composition, via the
    'observer' property which inherits from traitlets.HasTraits.

    The following DataBag instance methods are exposed from traitlets.HasTraits:

    traits()

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

    hidden_traits = ("length", "use_mutable",
                     "use_casting", "allow_none", "verbose")

    # @staticmethod
    @classmethod
    def _make_hidden(cls, **kwargs):
        """ Returns a Bunch where each key in kwargs is mapped to a bool.
        The mapping flags whether a key in kwargs is to be considered "hidden attribute".

        Contrary to this label, a "hidden attribute" is one that it is NOT a
        trait, yet it is still "visible" to the usual access API. Rather, they
        are "hidden" to the instance of HasTraits which implements the traitlets
        parts in DataBag (i.e., the DataBagTraitsObserver).

        Instead, a "hidden attribute" can be queried and assigned to (in order 
        to change the behaviour of the  DataBag object) yet it is not considered
        a trait type (hence changing it does not trigger a notification).

        The "hidden attributes" are:
        "length", "use_mutable", "use_casting", "allow_none","verbose"

        and are augmented here with "mutable_types" because this was added to
        the API design later, and I want to be able to unpickle old data...
        """
        if not issubclass(cls, DataBag):
            raise TypeError(
                f"Expecting a DataBag or a type derived from DataBag; got {cls.__name__} instead")

        ret = Bunch([(name, kwargs.pop(name, False))
                    for name in list(cls.hidden_traits) + ["mutable_types"]])
        # ret = Bunch([(name, kwargs.pop(name, False)) for name in list(DataBag.hidden_traits) + ["mutable_types"]])
        ret.length = 0
        ret.allow_none = True
        ret.use_mutable = True
        ret.verbose = False
        return ret

    # hold_trait_notifications = self._observer__.hold_trait_notifications
    # @contextlib.contextmanager
    # def hold_trait_notifications(self):
    #     """Context manager to hold trait change notifications in self.__observer__
    #     """
    #     with self.__observer__.hold_trait_notifications() as holder:
    #         yield holder
    #     # return self.__observer__.hold_trait_notifications
    #     # if self.__observer__._cross_validation_lock:
    #     #     yield
    #     #     return
    #     # else:
    #     #     return self.__observer__.hold_trait_notifications

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

        use_mutable: bool, default is False
            When True, allows a new value type to be assigned to an EXISTING
            attribute.

        mutable_types: alias for use_mutable (for backward compatibility)

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
        obs = DataBagTraitsObserver()
        hid = self.__class__._make_hidden(**kwargs)
        object.__setattr__(self, "__observer__", obs)
        object.__setattr__(self, "__hidden__", hid)
        # self.__observer__ = DataBagTraitsObserver()
        # NOTE: so that derived types can use their OWN hidden_traits
        # self.__hidden__ = self.__class__._make_hidden(**kwargs)
        self.__observer__.verbose = self.__hidden__.verbose

        for name in self.__hidden__.keys():
            kwargs.pop(name, None)

        if self.use_casting:
            self.use_mutable = False

        elif self.use_mutable:
            self.use_casting = False

        if len(args) == 1 and isinstance(args[0], dict):
            dd = args[0]
        else:
            dd = kwargs

        traits = dict(
            map(lambda x: (x[0], self._make_trait_(x[1])), dd.items()))

        self.__hidden__.length = len(traits)

        self.__observer__.add_traits(**traits)

        # FIXME: 2021-10-10 15:59:37
        # Why is this needed: because otherwise DataBag shows no contents
        for k, v in dd.items():
            object.__setattr__(self.__observer__, k, v)

        super().__init__(**dd)

    def _make_trait_(self, obj):
        # NOTE: 2022-01-29 19:29:56 dynamic_trait is from traitutils
        # print(f"{self.__class__.__name__}._make_trait_ for {type(obj).__name__}")
        if obj is self:
            dtrait = partial(dynamic_trait,
                             allow_none=self.__hidden__.allow_none,
                             content_traits=False)  # ,
            # force_trait=traitlets.Any) # 2022-11-26 23:06:46 we use DataBagTrait

        else:
            dtrait = partial(dynamic_trait,
                             allow_none=self.__hidden__.allow_none,
                             content_traits=True,
                             use_mutable=self.__hidden__.use_mutable,
                             force_trait=traitlets.Any)
            
        trait_obj = dtrait(obj)
        
        # print(f"\n{self.__class__.__name__}._make_trait_ for {type(obj).__name__} ⇒ {type(trait_obj).__name__}")

        return dtrait(obj)  # , force_trait=traitlets.Any)

    def __setitem__(self, key, val):
        """Implements indexed (subscript) assignment: obj[key] = val
        """
        # from .scipyen_traitlets import MetaNotifier
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
        # in The Python Language Reference).
        #
        #

        if not isinstance(key, str):
            raise TypeError("Expecting a str key; got %s instead" %
                            type(key).__name__)

        try:
            # NOTE: 2022-11-03 09:43:10
            # this `try` block is for when traits (key values in __observer__) are
            # being set upon unpickling - the observer may not be alive yet
            #
            # FIXME 2022-11-03 09:44:18
            # I am doubtful whether a DataBag is worth serializing - for data to
            # be serialized/pickled, a Bunch might be a better way...
            #
            # NOTE: 2022-11-03 09:41:36
            # __observer__ is hidden from dir() but can be accesses manually at
            # console, e.g. <some DataBag instance>.__observer__
            obs = object.__getattribute__(self, "__observer__")  

            # print(f"\n{self.__class__.__name__} in __setitem__:  has __observer__")
        except:
            # unpickling doesn't find an observer yet ('cause it is an instance
            # var but is not pickled in the usual way; restoring it creates
            # problems therefore we re-create it here)
            # traceback.print_exc()
            # print(f"\n{self.__class__.__name__} in __setitem__: has no __observer__")
            obs = DataBagTraitsObserver()
            object.__setattr__(self, "__observer__", obs)

        # NOTE: 2022-11-03 09:50:59
        # BEGIN Deal with the situation where a "hidden attribute" is being set
        # i.e. when __setitem__ is invoked for assigning to a "hidden attribute"
        # we look it up then return
        # see self._make_hidden for details
        try:
            hid = object.__getattribute__(self, "__hidden__")

        except:
            hid = DataBag._make_hidden()
            object.__setattr__(self, "__hidden__", hid)

        if key in hid:
            hid[key] = val

            if key == "use_casting" and hid["use_casting"]:
                hid["use_mutable"] = False

            if key == "use_mutable" and hid["use_mutable"]:
                hid["use_casting"] = False

            return
        # END Deal with the situation where a "hidden attribute" is being set

        # BEGIN Deal with the actual traitlet - assign to an existing one or add a new one
        if obs.has_trait(key): # tis just checks if key is in obj._traits
            # print(f"\n{self.__class__.__name__}.__setitem__ to modify trait {key}")
            
            # NOTE: 2022-11-03 12:02:45 assign new value to existing
            # NOTE 2020-09-05 12:52:39
            # Below, one should use getattr(obs, key) instead of 
            #   object.__getattribute__(obs, key), because:
            #
            # • calling object.__getattribute__(...) returns the trait type that
            #   wraps the object, and NOT the object itself ! (in HasTraits, the 
            #   TraitType instances are also stored as class attributes, because
            #   the HasTraits API operates on the class -- see HasTraits.add_traits()
            #   for details)
            #
            # • if the observer has a trait, then getattr will also return its 
            #   value; this can be:
            #   ∘ the object wrapped by the TypeTrait trait, or
            #   ∘ a dynamically generates object according to the specific 
            #       TypeTrait subclass
            #
            # Reason for NOT accessing _trait_values directly (as in NOT calling
            #   obs._trait_values[key] ):
            #
            # • the _trait_values is populated typically after calling the Trait
            #   class' set method (descriptor method); hence _trait_values[key]
            #   may not exist !!!
            #
            # • therefore, calling here object.__setattr_ on the obs is ESSENTIAL
            #   in order to trigger this mechanism
            #
            try:
                old_value = getattr(obs,key, None) # -> YES
                
                # WARNING: 2023-05-25 11:37:41
                # this may be a notifier wrapper type (e.g. _NotifierDeque_, _NotifierDict_)
                target_type = type(old_value)

                if type(val) != target_type:
                    if hid["use_casting"]:
                        new_val = target_type(val)  # this may fail !
                        obs.set_trait(key, new_val)
                        # object.__setattr__(obs, key, new_val)

                    elif hid["use_mutable"]:
                        self.__coerce_trait__(obs, key, val)

                    else:
                        # allow_none takes effect in the call below
                        # may raise TraitError
                        # trait = self._make_trait_(val)
                        # obs.add_trait(key, trait)
                        obs.set_trait(key, new_val)
                        # object.__setattr__(obs, key, val)

                else:
                    obs.set_trait(key, val)
                    # trait = self._make_trait_(val)
                    # obs.add_trait(key, trait)
                    # object.__setattr__(obs, key, val)

                # print(f"\tcall super().__setitem__")
                super().__setitem__(key, val)  # do I need this ?!?

            except:
                traceback.print_exc()

        else:
            # NOTE: 2022-11-03 12:02:34
            # add a new trait
            # print(f"{self.__class__.__name__}.__setitem__ trait {key} not found")
            if key not in ("__observer__", "__hidden__") and key not in self.__hidden__.keys():
                
                # print(f"\n{self.__class__.__name__}.__setitem__ to add trait {key}")
                traitobject = self._make_trait_(val)
                trdict = {key: traitobject}
                obs.add_trait(key, traitobject)
                object.__setattr__(obs, key, val)
                
                # NOTE: 2023-05-25 11:01:41
                # this kind of works, and it is the HasTraits way 
                # but does not update the _trait_values -- why?
                # answer: because _trait_values is updated by the traitlet's set method
                # (a descriptor method)
                # trdict = {key: self._make_trait_(val)}
                # obs.add_traits(**trdict)
                # setattr(obs, key, val)
                
                # object.__setattr__(obs, key, val)
                object.__getattribute__(self, "__hidden__").length = len(trdict)

            super().__setitem__(key, val)

    def __len__(self):
        # bypass self.__getitem__()
        obs = object.__getattribute__(self, "__observer__")
        ret = len(obs.traits())
        object.__getattribute__(self, "__hidden__")["length"] = ret
        return ret

    def __str__(self):
        # return pformat(self)
        obs = object.__getattribute__(self, "__observer__")
        d = dict(map(lambda x: (x[0], x[1] if x[1] is not self else "<Reference to %s object with id=%d>" % (
            self.__class__.__name__, id(self))), obs._trait_values.items()))
        return pformat(d)

    def __repr__(self):
        # return "%s:\n%s" % (self.__class__, pformat(self))
        obs = object.__getattribute__(self, "__observer__")
        d = dict(map(lambda x: (x[0], x[1] if x[1] is not self else "<Reference to %s object with id=%d>" % (
            self.__class__.__name__, id(self))), obs._trait_values.items()))
        return pformat(d)

    def __getitem__(self, key):
        """Implements obj[key] (subscript access, or "bracket syntax"")
        """
        try:
            obs = object.__getattribute__(self, "__observer__")
        except:
            obs = DataBagTraitsObserver()
            object.__setattr__(self, "__observer__", obs)
            
        try:
            # obs = object.__getattribute__(self, "__observer__")
            return getattr(obs, key)
        except AttributeError:
            return object.__getattribute__(self, key)
        except:
            raise
        
    def __setattr__(self, key, value):
        hidden = self.__class__.hidden_traits
        if key == "__observer__" and isinstance(value, DataBagTraitsObserver):
            object.__setattr__(self, key, value)
            return
        
        if key == "__hidden__" and isinstance(value, dict):
            h_keys = list(self.__class__.hidden_traits) + ["mutable_types"]
            
            if all(k in h_keys for k in value.keys()):
                object.__setattr__(self, key, value)
                return
        
        try:
            obs = object.__getattribute__(self, "__observer__")
        except:
            obs = DataBagTraitsObserver()
            object.__setattr__(self, "__observer__", obs)
            
        try:
            hid = object.__getattribute__(self, "__hidden__")
        except:
            hid = DataBag._make_hidden()
            object.__setattr__(self, "__hidden__", hid)
            
        if key in hidden:
            object.__setattr__(self, key, value)
        else:
            if obs.has_trait(key):
                if hid["use_casting"]:
                    trait = self._make_trait_(value)
                    obs.set_trait_coercive(key, trait, value) # ATTENTION pass a TraitType, not the value!
                else:
                    obs.set_trait(key, value) # calls TraitType superclass method
            else:
                trait = self._make_trait_(value)
                obs.add_trait(key, trait) # ATTENTION pass a TraitType, not the value!
                setattr(obs, key, value)
            

    def __getattr__(self, key):
        """Implements obj.key (attribute access, or "dot syntax")
        """
        try:
            obs = object.__getattribute__(self, "__observer__")

            if obs.has_trait(key):
                val = getattr(obs, key)

            else:
                # this exposes access to observer's methods when key is "__observer__"
                val = self.__getitem__(key)

            if isinstance(val, TraitType):
                return val.get(obs)

            else:
                return val

        except:
            raise  # KeyError("%s" % key)

    def __iter__(self):
        """Restricted membership test ('in' keyword).
        Overloads super().__iter__(self) to restrict membership test for trait
        values.
        """
        try:
            obs = object.__getattribute__(self, "__observer__")
        except:
            traceback.print_exc()
            return
        
        return (k for k in obs._trait_values.keys())

    def __iter_full__(self):
        return super().__iter__(self)

    def __hash__(self):
        return sum((hash(v) for v in self.items()))

    def __delitem__(self, key):
        """Implements del obj[key] where a is a DataBag and key is a str
        """
        try:
            obs = object.__getattribute__(self, "__observer__")
            # super().__delitem__(key)
            # obs.length = self.__len__()

            # if obs.has_trait(key):
            if key in obs.traits():
                # print(f"{self.__class__.__name__}.__delitem__ to remove trait {key}")
                trait_to_remove = obs.traits()[key]
                
                obs.remove_trait(key, trait_to_remove)
                # NOTE: 2023-05-26 23:24:48
                # fore whatever reason, THIS BELOW MUST BE CALLED !!!
                obs._trait_values.pop(key, None)

            object.__getattribute__(self, "__hidden__")[
                "length"] = len(obs.traits())

            # print(f"{key} lurking in self: {key in dir(self)}")
            
        except:
            raise  # KeyError("%s" % key)
        
    def __getstate__(self):
        """Returns the state of this object's observer wrapped in a dict
        """
        # NOTE: Python 3.9 way
        if hasattr(self, "__observer__"):
            obs = object.__getattribute__(self, "__observer__")
            state = obs.__getstate__()
            d = {"__observer__": state}

        else:
            d = {"__observer__": {"_trait_notifiers": {}, "_trait_validators": {}}}

        return d

    def __setstate__(self, state: dict):
        """Restores the state dictionary
        state: dict
        """

        # print("DataBag.__setstate__", [k for k in state])
        if "__observer__" in state:
            observer_state = state["__observer__"]

        else:
            observer_state = state

        if not hasattr(self, "__observer__"):
            # old DataBag versions pickled w/o __observer__
            object.__setattr__(self, "__observer__", DataBagTraitsObserver())

        obs = object.__getattribute__(self, "__observer__")

        obs.__setstate__(observer_state)

    def __coerce_trait__(self, obs, key, val):
        """Removes old trait, replaces with new trait"""
        # print(f"{self.__class__.__name__}.__coerce_trait__ obs = {obs}, key = {key}, val = {val} (type = {type(val).__name__})")
        old_trait = obs.traits().get(key, None)
        old_value = getattr(obs, key, None)
        to_notify = False
        if any is None in (old_trait, old_value):
            to_notify = True
            # obs.add_trait(key, trait)
        else:
            old_type = type(old_value)
            new_type = type(val)
            to_notify = new_type != old_type
        # old_trait = obs.traits()[key]
        # old_type = type(object.__getattribute__(obs, key))

        new_trait = self._make_trait_(val)
        
        obs.set_trait_coercive(key, new_trait, val)
        # setattr(obj, key, val)  # MUST be called
        # object.__setattr__(obs, key, val)
        # new_type = type(val)
        # 
        # # NOTE 2020-07-05 16:17:27
        # # signal the change of trait type
        # if new_type != old_type:
        #     obs._notify_trait(key, old_type, new_type)
        # 
        # obs.remove_traits(**{key: old_trait})
        # 
        # obs.add_traits(**{key: new_trait})

        # object.__setattr__(obs, key, val)

    @property
    def observer(self):
        """The HasTraits observer. Read-only
        """
        return self.__observer__

    def as_dict(self):
        """Dictionary of trait values
        """
        try:
            obs = object.__getattribute__(self, "__observer__")
        except:
            return dict()
        
        return obs._trait_values

    def remove_members(self, *keys):
        # print(f"DataBag.remove_members {keys}")
        try:
            obs = object.__getattribute__(self, "__observer__")

            current_traits = dict(obs.traits())

            valid_traits_to_remove = dict([(k, current_traits[k])
                                        for k in keys if k in current_traits])
            
            current_traits_keys = valid_traits_to_remove.keys()

            # traits = dict([(key, valid_traits_to_remove[key])
            #               for key in keys if key in current_traits_keys])
            
            values_to_remove = dict([(k, obs._trait_values[k])
                                    for k in valid_traits_to_remove.keys() if k in obs._trait_values])

            obs.remove_traits(**valid_traits_to_remove)
            
            for tn, tv in values_to_remove.items():
                change = Bunch(owner=self, name=tn,
                            old=tv, new=None, type="change")
                obs.notify_change(change)
                

            object.__getattribute__(self, "__hidden__")[
                "length"] = len(obs.traits())

        except:
            traceback.print_exc()
            raise

    def clear(self):
        try:
            super().clear()

            obs = object.__getattribute__(self, "__observer__")
            
            traitkeys = [k for k in obs.traits()]
            
            self.remove_members(*traitkeys)
            # traits = dict(obs.traits())
            # obs.remove_traits(**traits)
            
            # obs._trait_values.clear() # taken care of by obs.remove_traits
            object.__getattribute__(self, "__hidden__")[
                "length"] = len(obs.traits())

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
            # also calls remove_trait on the observed, and updates __hidden__.length
            self.__delitem__(key)
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
    def mutable_types(self, val: bool):
        if not isinstance(val, bool):
            raise TypeError("Expecting a bool; got %s instead" %
                            type(val).__name__)

        self.__hidden__.use_mutable = val

        if val:
            self.__hidden__.use_casting = False

    @property
    def use_mutable(self):
        return self.__hidden__.use_mutable

    @mutable_types.setter
    def use_mutable(self, val: bool):
        if not isinstance(val, bool):
            raise TypeError("Expecting a bool; got %s instead" %
                            type(val).__name__)

        self.__hidden__.use_mutable = val

        if val:
            self.__hidden__.use_casting = False

    @property
    def use_casting(self):
        return self.__hidden__.use_casting

    @use_casting.setter
    def use_casting(self, val: bool):
        if not isinstance(val, bool):
            raise TypeError("Expecting a bool; got %s instead" %
                            type(val).__name__)

        self.__hidden__.use_casting = val

        if val == True:
            self.__hidden__.use_mutable = False

    @property
    def verbose(self):
        return self.__hidden__.verbose

    @verbose.setter
    def verbose(self, val):
        self.__hidden__.verbose = (val == True)
        self.__observer__.verbose = (val == True)

    @property
    def allow_none(self):
        return self.__hidden__.allow_none

    @allow_none.setter
    def allow_none(self, val):
        if not isinstance(val, bool):
            raise TypeError("Expecting a bool; got %s instead" %
                            type(val).__name__)

        self.__hidden__.allow_none = val

    def keys(self):
        """Generates a keys 'view'
        """
        obs = object.__getattribute__(self, "__observer__")
        return obs._trait_values.keys()
        # return obs._traits.keys()

    def values(self):
        """Generates a values 'view'
        """
        obs = object.__getattribute__(self, "__observer__")
        return obs._trait_values.values()

    def items(self):
        """Generates an items 'view'
        """
        obs = object.__getattribute__(self, "__observer__")
        return obs._trait_values.items()

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
                              mutable_types=self.mutable_types,
                              use_casting=self.use_casting,
                              allow_none=self.allow_none)

    # @timefunc
    def update(self, other):
        """Updates this DataBag with key/value pairs from 'other'.

        'other' is a subclass of dict.

        """
        # leaves self.mutable_types and self.use_casting unchanged
        # the behaviour depends on whether self accepts mutating or casting type
        # traits
        # print(f"\n{self.__class__.__name__}.update")
        if isinstance(other, dict):  # this includes DataBag!
            for key, value in other.items():
                self[key] = value # calls __setitem__
                
            # with timeblock("DataBag.update"):
            #     for key, value in other.items():
            #         self[key] = value

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
            raise TypeError(
                "'other' expected to be a DataBag or HasTraits; got %s instead" % type(other).__name__)

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
            raise TypeError(
                "'target' expected to be a DataBag or HasTraits; got %s instead" % type(target).__name__)

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
            raise TypeError(
                "'source' expected to be a DataBag or HasTraits; got %s instead" % type(source).__name__)


# def generic_change_handler(c, show: typing.Optional[str] = "all"):
#     if isinstance(show, str):
#         if len(show.strip()) == 0:
#             show = "all"
# 
#         elif show not in c:
#             show = "all"
# 
#     else:
#         show = "all"
# 
#     herald = "#debug generic_change_handler"
# 
#     if show == "all":
#         print(f"{herald} type:",  c.type)
#         print(f"{herald} owner:", c.owner)
#         print(f"{herald} name:",  c.name)
#         print(f"{herald} old:",   c.old)
#         print(f"{herald} new:",   c.new)
# 
#     else:
#         print(f"{herald} {show}", c[show])
        
        
    
