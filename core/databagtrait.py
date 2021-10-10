from traitlets.utils.bunch import Bunch

from .traitutils import (traitlets, dynamic_trait, transform_link,
                         HasTraits, TraitType, TraitsObserver, 
                         ContainerTraitsObserver, Int, Bool, All, Dict, observe)

from .traitcontainers import DataBag

class DataBagTrait(Dict):
    """Avoid slicing the DataBag type into the basic dict type.
    """
    def __init__(self, value_trait=None, per_key_traits=None, key_trait=None, devault_value=Undefined,
                 **kwargs):
        """Avoid casting DataBag to dict, as traitlets.Dict does
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

        # Handling positional arguments
        if default_value is Undefined and value_trait is not None:
            if not is_trait(value_trait):
                default_value = value_trait
                value_trait = None

        if key_trait is None and per_key_traits is not None:
            if is_trait(per_key_traits):
                key_trait = per_key_traits
                per_key_traits = None

        # Handling default value
        if default_value is Undefined:
            default_value = {}
        if default_value is None:
            args = None
        elif isinstance(default_value, dict):
            args = (default_value,)
        elif isinstance(default_value, SequenceTypes):
            args = (default_value,)
        else:
            raise TypeError('default value of Dict was %s' % default_value)

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

        if is_trait(key_trait):
            if isinstance(key_trait, type):
                warn("Traits should be given as instances, not types (for example, `Int()`, not `Int`)"
                     " Passing types is deprecated in traitlets 4.1.",
                     DeprecationWarning, stacklevel=2)
                key_trait = key_trait()
            self._key_trait = key_trait
        elif key_trait is not None:
            raise TypeError("`key_trait` must be a Trait or None, got %s" % repr_type(key_trait))

        self._per_key_traits = per_key_traits

        super(Dict, self).__init__(klass=DataBag, args=args, **kwargs)

