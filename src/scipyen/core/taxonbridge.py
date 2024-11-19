# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Wrapper around BrainGlobe API, with shims
"""
class Taxon:
    """Shim class that will be overwritten below if taxoniq package is installed"""
    def __new__(obj, *args, **kwargs):
        return MISSING
    def __init__(self, *args, **kwargs):
        pass
    
hasTaxoniq = False
try:
    import taxoniq
    from taxoniq import Taxon
    hasTaxoniq = True
except:
    hasTaxoniq = False
    taxoniq = None

import collections, typing, dataclasses
from dataclasses import MISSING
import numpy as np
import pandas as pd


class TaxonDescriptor:
    def __init__(self, *, default:typing.Optional[typing.Union[Taxon, str, type(pd.NA), type(MISSING)]] = None):
        if hasTaxoniq and isinstance(default, taxoniq.Taxon):
            self._default = default
        elif isinstance(default, str) or default in (None, MISSING, pd.NA):
            if hasTaxoniq:
                self._default = default
        else:
            raise TypeError(f"Expecting a str, a Taxon, None, or MISSING; instead, got {type(value).__name__}")
            
    def __set_name__(self, obj:object, name:str):
        if len(name.strip()) == 0:
            raise ValueError("Cannot accept an empty name")
        self._name = "_"+name
        
    def __get__(self, obj:object, objtype:type) -> object:
        if obj is None:
            return self._default
        return getattr(obj, self._name, self._default)
    
    def __set__(self, obj:object, value:typing.Optional[typing.Union[str, Taxon, type(MISSING)]] = None):
        if isinstance(value, Taxon):
            setattr(obj, self._name, value)
        elif isinstance(value, str) or value in (None, MISSING, pd.NA):
            setattr(obj, self._name, value)
        else:
            raise TypeError(f"Expecting a str, a Taxon, None, or MISSING; instead, got {type(value).__name__}")
