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

class InputSpec():
    r"""Encapsulates arguments to interact.getInput(...)
    """
    __slots__ = ("_default", "_mytype", "_choices")

    def __init__(self, mytype=type(dataclasses.MISSING),
                 default = dataclasses.MISSING,
                 choices : typing.Optional[
                                typing.Union[typing.Set, typing.Sequence]
                                ] = None):
        r"""Constructor for _InputSpec.

    Parameters:
    ==========

    :mytype:    optional; type of input argument; when MISSING

    :default:   optional; default value of the input argument

    :choices:   optional; indicates the set of values that the argument can take;

                it can be:

                • a dict, EnumType, or set

                • a range object

                • a pair of numbers (min, max)



    """

        self._mytype, self._default = self.parse_args(mytype, default)
        # self._name = name
        self._choices   = choices

    @staticmethod
    def parse_args(x, d = None):
        r""""""
        # NOTE: 2026-04-05 16:57:40 TODO
        # map typing.Any to object
        if isinstance(x, dataclasses.Field):
            # ignores d, as a dataclasses.Field provides their own default value
            mytype = prog.unwind_type(x.type)
            # if isinstance(mytype, set) and type(None) in mytype:

            # NOTE: 2026-04-05 16:53:34
            # dataclass field definition syntax precludes both default and
            # default_factory to be MISSING (would raise SyntaxError if that was
            # the case)
            if x.default_factory is dataclasses.MISSING:
                default = x.default
            else:
                default = x.default_factory()

            # possibly a noop -- when field annotation results in a field
            # "type" attribute of 'typing.Optional', the NoneType is already
            # present in the mytype set
            mytype.add(type(default))

            if len(mytype) == 1:
                mytype = tuple(mytype)[0]

        elif isinstance(x, (typing._Final, type)):
            # a default is not needed, but can be used if unwind_type fails
            mytype = prog.unwind_type(x)
            if len(mytype) == 0:
                if d not in (dataclasses.MISSING, None): # get it from default's type
                    mytype = {type(d)}
                else:
                    mytype = {object}

            default = d

        elif x in (type(dataclasses.MISSING), dataclasses.MISSING, None, type(None), typing.Any):
            # needs the supplied default in 'd'; failing that, assume any object type
            if d not in (dataclasses.MISSING, None): # get it from default's type
                mytype = type(d)
            else:
                mytype = object

            default = d

        else:
            # ignores d
            default = mytype
            mytype = type(default)


        if isinstance(mytype, set) and len(mytype) == 1:
            mytype = tuple(mytype)[0]

        return mytype, default

    @property
    def type(self):
        return self._mytype

    @property
    def default(self):
        return self._default

    @property
    def choices(self):
        return self._choices

