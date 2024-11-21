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
    
# from core.ncbi_entrez import list_databases

hasTaxoniq = False
try:
    import taxoniq
    from taxoniq import Taxon
    hasTaxoniq = True
except:
    hasTaxoniq = False
    taxoniq = None

import collections, typing, dataclasses, traceback
from dataclasses import MISSING
import numpy as np
import pandas as pd

def get_common_name(t:Taxon):
    if hasTaxoniq and isinstance(t, taxoniq.Taxon):
        try:
            return t.common_name
        except:
            traceback.print_exc()
            return ""
    
    return ""

supported_species=["Homo", "Danio", "Caenorhabditis", "Rattus", "Mus", "Gallus"]
    

class TaxonDescriptor:
    def __init__(self, *, default:typing.Optional[typing.Union[Taxon, str, type(pd.NA), type(MISSING)]] = None):
        if hasTaxoniq and isinstance(default, taxoniq.Taxon):
            self._default = default
        elif isinstance(default, str) or default in (None, MISSING, pd.NA):
            if hasTaxoniq and isinstance(default, str) and default in supported_species:
                self._default = Taxon(scientific_name=default)
                # self._default = default
            self._default=default
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
            if hasTaxoniq and isinstance(value, str) and value in supported_species:
                value = Taxon(scientific_name=value)
            setattr(obj, self._name, value)
        else:
            raise TypeError(f"Expecting a str, a Taxon, None, or MISSING; instead, got {type(value).__name__}")
