# -*- coding: utf-8 -*-
# $Id: inputspec.# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
import typing, collections, dataclasses, os, sys, types
import numpy as np
import pandas as pd
import quantities as pq
from tribool import Tribool
from core import scipyen_quantities as scq
from core import prog
from core import datatypes

class InputSpec():
    r"""Encapsulates arguments to interact.getInput(...)
    """
    __slots__ = ("_default", "_mytype", "_value", "_choices")

    def __init__(self, mytype=type(dataclasses.MISSING),
                 default = dataclasses.MISSING,
                 value = dataclasses.MISSING,
                 allowed_values : typing.Optional[
                                typing.Union[typing.Set, typing.Sequence]
                                ] = None):
        r"""Constructor for _InputSpec.

    Parameters:
    ==========

    :mytype:    optional; type of input argument, or set ot type objects, or MISSING (default)

            When MISSING, it will be inferred from the ``default`` parameter, below, or from the ``value`` parameter (see below)

    :default:   optional; default value of the input argument

    :value:     optional; current value (may be different from the default)

    :allowed_values:   optional; indicates the set of values that the argument can take;

                it can be:

                • a dict, EnumType, or set

                • a range object

                • a pair of numbers (min, max)



    """

        self._mytype, self._default, self._value = self.parse_args(mytype, default, value)
        # self._name = name
        self._choices   = allowed_values

    def parse_args(self, x, d = dataclasses.MISSING, v = dataclasses.MISSING):
        r"""
    """
        # NOTE: 2026-04-05 16:57:40 TODO
        # map typing.Any to object
        if isinstance(x, dataclasses.Field):
            # extracts expected type and default value from the field's attributes;
            #
            # ignores d, as a dataclasses.Field provides their own default value
            # mytype = prog.unwind_type(x.type)
            mytype = prog.unravel_types(x.type) # NOTE: 2026-04-16 22:08:06 this is a TypeSpec
            # print(f"\n***\nInputSpec.parse_args(x field) -> mytype = {mytype}")

            # NOTE: 2026-04-05 16:53:34
            # dataclass field definition syntax precludes both default and
            # default_factory to be MISSING (would raise SyntaxError if that was
            # the case)
            if x.default_factory is dataclasses.MISSING:
                default = x.default
            else:
                default = x.default_factory()

            def_type = prog.unravel_types(default)
            if def_type not in mytype.object_types:
                mytype.add(def_type)

            # # possibly a noop -- when field annotation results in a field
            # # "type" attribute of 'typing.Optional', the NoneType is already
            # # present in the mytype set
            # mytype.add(type(default))

            typing_types = tuple(filter(lambda t: isinstance(t, prog.TYPING_TYPES), mytype))

            regtypes = tuple(filter(lambda t: not isinstance(t, prog.TYPING_TYPES), mytype))

            for t in typing_types:
                mytype |= prog.unwind_type(t)

            if len(mytype) == 1:
                mytype = tuple(mytype)[0]

            elif len(mytype) > 1:
                mytype = tuple(mytype)

            else:
                mytype = type(default)


            # if v is not dataclasses.MISSING:
            #     # if not isinstance(v, mytype):
            #     if not datatypes.check_type(v, mytype)[0]:
            #         raise TypeError(f"An {mytype} object was expected for 'value'; got {type(v).__name__} instead")

        elif isinstance(x, (typing._Final, type)):
            # a default is not needed, but can be used if unwind_type fails
            mytype = prog.unwind_type(x)
            if len(mytype) == 0:
                if d is dataclasses.MISSING:
                    # get it from default's type; allow None as valid default value
                    mytype = {type(d)}

                elif v is not dataclasses.MISSING:
                        # get it from the value type; allow None as valid default value
                        mytype = {type(v)}
                else:
                    mytype = {object}

            else:
                mytype = tuple(mtype)

            default = d

            # if v is not dataclasses.MISSING:
            #     # if not isinstance(v, mytype):
            #     if not datatypes.check_type(v, mytype)[0]:
            #         raise TypeError(f"An {mytype} object was expected for 'value'; got {type(v).__name__} instead")

        elif x in (type(dataclasses.MISSING), dataclasses.MISSING, None, type(None), typing.Any):
            # needs the supplied default in 'd'; failing that, assume any object type
            if d is not dataclasses.MISSING:
                mytype = type(d)
            elif v is not dataclasses.MISSING:
                mytype = type(v)
            else:
                mytype = object

            default = d

            # if v is not dataclasses.MISSING:
            #     # if not isinstance(v, mytype):
            #     if not datatypes.check_type(v, mytype)[0]:
            #         raise TypeError(f"An {mytype} object was expected for 'value'; got {type(v).__name__} instead")

        else:
            # ignores d
            default = mytype
            mytype = type(default)

        if v is not dataclasses.MISSING:
            # if not isinstance(v, mytype):
            if not datatypes.check_type(v, mytype)[0]:
                raise TypeError(f"An {mytype} object was expected for 'value'; got {type(v).__name__} instead")

        # if isinstance(mytype, set) and len(mytype) == 1:
        #     mytype = tuple(mytype)[0]

        return mytype, default, v

    @property
    def type(self):
        return self._mytype

    @property
    def default(self):
        return self._default

    @property
    def value(self):
        return self._value

    @property
    def allowed_values(self):
        return self._choices

    def __repr__(self) -> str:
        df = self.default
        if isinstance(self.default, str):
            df = f"'{self.default}'"
        else:
            df = f"{self.default}"

        result = f"{self.__class__.__name__} for types: {self.type}, with value {self.value} (default: {df})"

        if isinstance(self.allowed_values, (typing.Set, typing.Sequence)) and len(self.allowed_values):
            result = result[:-1] + f"; allowed values: {self.allowed_values})"

        return result

