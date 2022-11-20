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
import sys, typing, dataclasses
from warnings import warn, warn_explicit
from collections import deque
import numpy as np
import quantities as pq
import pandas as pd

from traitlets.utils.bunch import Bunch
from traitlets.utils.descriptions import describe, class_of, add_article, repr_type

from traitlets.traitlets import (TraitError, TraitType, Instance, Container, 
                                 Undefined, Unicode, is_trait)

from .traitcontainers import DataBag
#from .traitutils import (enhanced_traitlet_set, standard_traitlet_set)

from .utilities import gethash

# NOTE: DataBagTrait <- Instance <- ClassBasedTraitType <- TraitType <- BaseDescriptor

class _NotifierDeque_(deque):
    # TODO: 2022-01-29 23:42:54
    # wrap and extend relevant deque methods to call obj._notify_trait
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._obj_ = None
        self._trait_name_ = None
        
    def init_instance(self, obj:typing.Optional[object]=None, trait_name:typing.Optional[str]=None):
        self._obj_ = obj
        self._trait_name_ = trait_name
        
    def append(self, x):
        if self._obj_ and self._trait_name_ and hasattr(self._obj_, "_notify_trait"):
            old_value = deque([v for v in self]) # make a NEW deque, don't just reference it'
                                                 # because this may be expensive we only do this
                                                 # when self is part of a traitlets.TraitType class
            super().append(x)
            new_value = deque(self)
            self._obj_._notify_trait(self._trait_name_, old_value, new_value)
            
        else:
            super().append(x)
            
        
    def appendleft(self, x):
        if self._obj_ and self._trait_name_ and hasattr(self._obj_, "_notify_trait"):
            old_value = deque([v for v in self]) # make a NEW deque, don't just reference it'
                                                 # because this may be expensive we only do this
                                                 # when self is part of a traitlets.TraitType class
            super().appendleft(x)
            new_value = deque(self)
            self._obj_._notify_trait(self._trait_name_, old_value, new_value)
            
        else:
            super().appendleft(x)
            
        
    def clear(self):
        if self._obj_ and self._trait_name_ and hasattr(self._obj_, "_notify_trait"):
            old_value = deque([v for v in self]) # make a NEW deque, don't just reference it'
                                                 # because this may be expensive we only do this
                                                 # when self is part of a traitlets.TraitType class
            super().clear()
            new_value = deque(self)
            self._obj_._notify_trait(self._trait_name_, old_value, new_value)
            
        else:
            super().clear()
            
    def extend(self, x):
        if self._obj_ and self._trait_name_ and hasattr(self._obj_, "_notify_trait"):
            old_value = deque([v for v in self]) # make a NEW deque, don't just reference it'
                                                 # because this may be expensive we only do this
                                                 # when self is part of a traitlets.TraitType class
            super().extend(x)
            new_value = deque(self)
            self._obj_._notify_trait(self._trait_name_, old_value, new_value)
            
        else:
            super().extend(x)
            
    def extendleft(self, x):
        if self._obj_ and self._trait_name_ and hasattr(self._obj_, "_notify_trait"):
            old_value = deque([v for v in self]) # make a NEW deque, don't just reference it'
                                                 # because this may be expensive we only do this
                                                 # when self is part of a traitlets.TraitType class
            super().extendleft(x)
            new_value = deque(self)
            self._obj_._notify_trait(self._trait_name_, old_value, new_value)
            
        else:
            super().extendleft(x)
            
    def insert(self, i, x):
        if self._obj_ and self._trait_name_ and hasattr(self._obj_, "_notify_trait"):
            old_value = deque([v for v in self]) # make a NEW deque, don't just reference it'
                                                 # because this may be expensive we only do this
                                                 # when self is part of a traitlets.TraitType class
            super().insert(i,x)
            new_value = deque(self)
            self._obj_._notify_trait(self._trait_name_, old_value, new_value)
            
        else:
            super().insert(i,x)
            
    def pop(self):
        if self._obj_ and self._trait_name_ and hasattr(self._obj_, "_notify_trait"):
            old_value = deque([v for v in self]) # make a NEW deque, don't just reference it'
                                                 # because this may be expensive we only do this
                                                 # when self is part of a traitlets.TraitType class
            val = super().pop()
            new_value = deque(self)
            self._obj_._notify_trait(self._trait_name_, old_value, new_value)
            return val
            
        else:
            return super().pop()
            
    def reverse(self):
        if self._obj_ and self._trait_name_ and hasattr(self._obj_, "_notify_trait"):
            old_value = deque([v for v in self]) # make a NEW deque, don't just reference it'
                                                 # because this may be expensive we only do this
                                                 # when self is part of a traitlets.TraitType class
            super().reverse()
            new_value = deque(self)
            self._obj_._notify_trait(self._trait_name_, old_value, new_value)
            
        else:
            super().reverse()
        
    def rotate(self, n=1):
        if self._obj_ and self._trait_name_ and hasattr(self._obj_, "_notify_trait"):
            old_value = deque([v for v in self]) # make a NEW deque, don't just reference it'
                                                 # because this may be expensive we only do this
                                                 # when self is part of a traitlets.TraitType class
            super().rotate(n)
            new_value = deque(self)
            self._obj_._notify_trait(self._trait_name_, old_value, new_value)
            
        else:
            super().rotate(n)
            
class QuantityTrait(Instance):
    info_text = "Trait for python quantities"
    default_value = pq.Quantity([]) # array([], dtype=float64) * dimensionless
    klass = pq.Quantity
    _cast_types = (np.ndarray, )
    _valid_defaults = (pq.Quantity,)
    
    def __init__(self, value_trait=None,
                 default_value = Undefined,
                 minlen = 0,
                 maxlen = sys.maxsize,
                 **kwargs):
        self._minlen = minlen
        self._maxlen = maxlen
        # self.hashed = 0
    
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
        
    def length_error(self, obj, value):
        e = "The '%s' trait of %s instance must be of length %i <= L <= %i, but a value of %s was specified." \
            % (self.name, class_of(obj), self._minlen, self._maxlen, value)
        raise TraitError(e)

    def validate_elements(self, obj, value):
        length = len(value)
        if length < self._minlen or length > self._maxlen:
            self.length_error(obj, value)

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
        
        try:
            old_value = obj._trait_values[self.name]
        except KeyError:
            silent=False    # this will be the first time the observed sees us
                            # therefore forcibly notify it
            old_value = self.default_value
            
        obj._trait_values[self.name] = new_value
        
        try:
            # new_hash = gethash(new_value)
            old_units = getattr(old_value, "units", pq.dimensionless)
            new_units = getattr(new_value, "units", pq.dimensionless)
            old_magnitude = getattr(old_value, "magnitude", np.nan)
            new_magnitude = getattr(new_value, "magnitude", np.nan)
            
            if silent:
                # so far silent is True when the observed knows about us
                # check it we changed and notify
                # silent = (new_hash == self.hashed)
                silent = new_value == old_value
            
            # if not silent:
            #     self.hashed = new_hash
                
        except:
            traceback.print_exc()
            silent = False
            
        #print(f"silent {silent}")
                
        if silent is not True:
            obj._notify_trait(self.name, old_value, new_value)
        
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
    
  
class DataBagTrait(Instance):
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
        
        
        obj._trait_values[self.name] = new_value
        
        try:
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
            obj._notify_trait(self.name, old_value, new_value)

class DequeTrait(Instance):
    klass = _NotifierDeque_
    #klass = deque
    _cast_types = (list, tuple)
    _valid_defaults = (deque, list, tuple, set, frozenset)
    
    def __init__(self, value_trait=None,
                 default_value=Undefined,
                 minlen=0,
                 maxlen=sys.maxsize,
                 **kwargs):
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
            
        elif trait is not None:
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
        
        try:
            old_value = obj._trait_values[self.name]
            
        except KeyError:
            silent=False    # this will be the first time the observed sees us
                            # therefore forcibly notify it
            old_value = self.default_value
            
        obj._trait_values[self.name] = new_value
        
        try:
            new_hash = gethash(new_value)
            if silent:
                # so far silent is True when the observed knows about us
                # check it we changed and notify
                silent = (new_hash == self.hashed)
            
            if not silent:
                self.hashed = new_hash
                
        except:
            traceback.print_exc()
            silent = False
            
        #print(f"silent {silent}")
                
        if silent is not True:
            obj._notify_trait(self.name, old_value, new_value)
        
        
