from warnings import warn, warn_explicit

from traitlets.utils.bunch import Bunch
from traitlets.utils.descriptions import describe, class_of, add_article, repr_type

from traitlets.traitlets import (TraitError, TraitType, Instance, Undefined, Unicode, is_trait)

from .traitcontainers import DataBag
from .traitutils import enhanced_traitlet_set

from .utilities import (gethash, safe_identity_test)

# NOTE: DataBagTrait <- Instance <- ClassBasedTraitType <- TraitType <- BaseDescriptor

class DataBagTrait(Instance):
    """Avoid slicing the DataBag type to dict.
    
    When a DataBag is contained in another DataBag, its corresponding trait type
    should be DataBagTrait, such that the trait value type (DataBag) will be
    preserved instead of being cast to a dict (as it would happen if the trait 
    type was traitlets.Dict or a dynamically generated trait type 'Dict_Dyn).
    
    """
    _value_trait = None
    _key_trait = None   # not sure I really need this one
    klass=DataBag
    
    def __init__(self, value_trait=None, per_key_traits=None, default_value=Undefined,
                 **kwargs):
    #def __init__(self, value_trait=None, per_key_traits=None, key_trait=None, default_value=Undefined,
                 #**kwargs):
        """Avoid casting DataBag to dict
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
            self.hashed = gethash(default_value.as_dict)

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

        super(DataBagTrait, self).__init__(klass=self.klass, args=args, **kwargs)

    def element_error(self, obj, element, validator, side='Values'):
        e = side + " of the '%s' trait of %s instance must be %s, but a value of %s was specified." \
            % (self.name, class_of(obj), validator.info(), repr_type(element))
        raise TraitError(e)

    def validate(self, obj, value):
        value = super(DataBagTrait, self).validate(obj, value) # this should always return a DataBag
        if isinstance(value, DataBag) and len(value):
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
            if key_trait:
                try:
                    key = key_trait._validate(obj, key)
                except TraitError as error:
                    self.element_error(obj, key, key_trait, 'Keys')
            active_value_trait = per_key_override.get(key, value_trait)
            if active_value_trait:
                try:
                    v = active_value_trait._validate(obj, v)
                except TraitError:
                    self.element_error(obj, v, active_value_trait, 'Values')
            validated[key] = v

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
        new_value = self._validate(obj, value)
        
        try:
            old_value = obj._trait_values[self.name]
            
        except KeyError:
            #print(f"{instance.name} not found")
            old_value = self.default_value
            

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