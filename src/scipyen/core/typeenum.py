# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
import typing, types
from enum  import (Enum, IntEnum)

TE = typing.TypeVar("TE", bound="TypeEnum")

class TypeEnum(IntEnum):
    r"""Common ancestor for enum types used in Scipyen
    """

    @classmethod
    def default(cls) -> type[TE]:
        r"""Aways returns the first member of the enum class
        """
        names = list(cls.names())
        return cls[names[0]]

    @classmethod
    def names(cls) -> typing.Generator[str, None, None]:
        r"""Iterate through the names in TypeEnum enumeration.
        """
        if hasattr(cls, "__members__") and isinstance(cls.__members__, types.MappingProxyType):
            yield from cls.__members__.keys()
        else:
            for t in cls:
                yield t.name

    @classmethod
    def values(cls) -> typing.Generator[int, None, None]:
        r"""Iterate through the int values of TypeEnum enumeration.
        """
        if hasattr(cls, "__members__") and isinstance(cls.__members__, types.MappingProxyType):
            yield from cls.__members__.values()
        else:
            for t in cls:
                yield t.value

    @classmethod
    def types(cls) -> typing.Generator[type[TE], None, None]:
        r"""Iterate through the elements of TypeEnum enumeration.
        Useful to quickly remember what the members of this enum are (with their
        names and values).

        A TypeEnum enum member is by definition a member
        of TypeEnum enum and an instance of TypeEnum.

        """
        for t in cls:
            yield t

    @classmethod
    def namevalue(cls, name:str) -> int:
        r"""Return the value (int) corresponding to a given name;
        WARNING If name is not a valid TypeEnum name returns -1
        """
        if name in cls.names():
            return getattr(cls, name).value

        return -1

    @classmethod
    def stringToType(cls, name:str) -> int:
        r"""Return the value (int) corresponding to a given name;
        WARNING If name is not a valid TypeEnum name returns -1
        """
        return cls.namevalue(name)

    @classmethod
    def __contains__(cls, value) -> bool:
        if isinstance(value, cls):
            return value in cls.types()

        elif isinstance(value, int):
            return value in cls.values()

        elif isinstance(value, str):
            return value in cls.names()

        else:
            return False

    @classmethod
    def type(cls, t:typing.Union[str, int]) -> type[TE]:
        r"""Returns the enum type corresponding to `t`, where
        `t` can be:
        • str: the name / symbol associated with the type in the enum
        • int: the value associated with the type in the enum


        """
        if isinstance(t, str):
            if t in cls.names():
                return [_t for _t in cls if _t.name == t][0]
            else:
                # check for user-defined composite type - break it down to a list
                # of existing types, if possible
                if "|" in t:
                    t_hat = [cls.type(_t.strip()) for _t in t.split("|")]
                    if len(t_hat):
                        return t_hat
                    else:
                        raise ValueError("Unknown %s type name %s" % (cls.__name__, t))
                else:
                    raise ValueError("Unknown %s type name %s" % (cls.__name__, t))

        elif isinstance(t, int):
            if t in cls.values():
                return [_t for _t in cls if _t.value == t][0]
            else:
                # check for implicit composite type (i.e. NOT listed in the definition)
                ret = [_t for _t in cls if _t.value & t]
                if len(ret):
                    return ret
                else:
                    raise ValueError("Unknown %s type value %d" % (cls.__name__, t))

        elif isinstance(t, cls):
            return t

        else:
            raise TypeError("Expecting a %s, int or str; got %s instead" % (cls.__name__, type(t).__name__))

    @classmethod
    def strand(cls, name1:str, name2:str) -> int:
        r""" Emulates '&' operator for type names 'name1' and 'name2'.
        If neither arguments are valid names returns 0
        """
        if any([n not in cls.names() for n in [name1, name2]]):
            return 0

        val1 = cls.namevalue(name1)
        val2 = cls.namevalue(name2)

        return val1 & val2

    @classmethod
    def is_primitive_type(cls, t) -> bool:
        r"""Checks if 't' is a primitive type in this types enumeration.

        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)

            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)

        """
        return len(cls.primitive_component_types(t)) == 0

    @classmethod
    def is_derived_type(cls, t) -> bool:
        r"""Checks if 't' is a compound type (i.e. derived from other type enums)

        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)

            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)

        """
        return len(cls.component_types(t)) > 0
        #return len(cls.primitive_component_types(t)) > 0

    @classmethod
    def is_composite_type(cls, t) -> bool:
        r"""Alias of TypeEnum.is_derived_type()

        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)

            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)

        """
        return cls.is_derived_type(t)

    @classmethod
    def primitive_component_types(cls, t) -> typing.List[TE]:
        r""" Returns a list of primitive TypeEnum objects that compose 't'.
        If 't' is already a primitive type, returns an empty list.

        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)

            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)

        """
        from .utilities import unique
        if isinstance(t, (int, str)):
            t_hat = cls.type(t)
            if isinstance(t_hat, list):
                return unique([__t for __t in chain.from_iterable([[_t for _t in cls if _t.is_primitive() and _t.value <= t_.value] for t_ in t_hat])])
            else:
                t = t_hat

        elif not isinstance(t, cls):
            raise TypeError("Expecting a TypeEnum, int or str; got %s instead" % type(t).__name__)

        return [_t for _t in filter(lambda x: x & t, cls) if _t.value < t.value and _t.is_primitive()]

    @classmethod
    def component_types(cls, t) -> typing.List[TE]:
        r""" Returns a list of TypeEnum objects that compose 't'.
        If 't' is already a primitive type, returns an empty list.

        The TypeEnum objects can also be composite types.

        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)

            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)

        """
        from .utilities import unique
        if isinstance(t, (int, str)):
            t_hat = cls.type(t)
            if isinstance(t_hat, list):
                # NOTE: 2021-04-14 23:33:22
                # by definition this only occurs with a composite type
                return unique([__t for __t in chain.from_iterable([[_t for _t in cls if _t.value <= t_.value] for t_ in t_hat])])
            else:
                t = t_hat

        elif not isinstance(t, cls):
            raise TypeError("Expecting a %s, int or str; got %s instead" % (cls.__name__, type(t).__name__))

        return [_t for _t in filter(lambda x: x & t, cls) if _t.value < t.value]

    @classmethod
    def derived_types(cls, t) -> typing.List[TE]:
        r""" Returns the composite TypeEnum objects where 't' participates.
        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)

            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)

        """
        if isinstance(t, (int, str)):
            t_hat = cls.type(t)
            if isinstance(t_hat, list):
                return unique([__t for __t in chain.from_iterable([[_t for _t in cls if _t is not t_ and _t.value > t_.value] for t_ in t_hat])])
            else:
                t = t_hat

        elif not isinstance(t, cls):
            raise TypeError("Expecting a %s, int or str; got %s instead" % (cls.__name__, type(t).__name__))

        return [_t for _t in filter(lambda x: x & t, cls) if not _t.is_primitive() and _t is not t and _t.value > t.value]# _t.value > t.value]

    def is_derived(self):
        r"""Return True if this TypeEnum object is a composite (i.e., derived) type.
        """
        return self.is_derived_type(self)

    def is_composite(self) -> bool:
        r"""Return True if this TypeEnum object is a composite (i.e., derived) type.
        """
        return self.is_derived()

    def is_primitive(self) -> bool:
        return self.is_primitive_type(self)

    def primitives(self) -> typing.List[TE]:
        r"""Returns a list of primitive types used to generate this type.

        Compound types are generated from primitive types through the logical
        OR operator (bitwise OR).

        Returns an empty list of this is a primitive type.
        """
        return self.primitive_component_types(self)

    def components(self) -> typing.List[TE]:
        r"""Returns a list of components for this TypeEnum object.

        Compound types are generated from primitive types through the logical
        OR operator (bitwise OR).

        If this TypeEnum object is a primitive returns an empty list
        """
        return self.component_types(self)

    def includes(self, t) -> bool:
        r"""Returns True if 't' is a component of this TypeEnum object.

        't' may be a primitive or a composite type.

        Always returns False when this is a primitive.
        """
        t = self.type(t)

        return t in self.components()

    def is_primitive_of(self, t) -> bool:
        r"""Returns True if this TypeEnum object is a primitive of 't'.

        Always returns False when this TypeEnum object is a composite (i.e.,
        even if it is a component of 't').
        """
        t = self.type(t)

        return self in t.primitives()

    def is_component_of(self, t) -> bool:
        r"""Returns True if this TypeEnum object is a component of 't'.
        """
        t = self.type(t)

        return self in t.components()

    def nameand(self, name:str) -> TE:
        r""" Applies strand() to the name of this object and the argument.
        """
        return self.strand(self.name, name)

