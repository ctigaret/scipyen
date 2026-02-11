# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
Wrapper around BrainGlobe API, with shims
"""
class Taxon:
    r"""Shim class that will be overwritten below if taxoniq package is installed.
    For HDF5 storage, all we need is a scientific_name
    """
    def __init__(self, **kwargs):
        self.tax_id = None
        self.scientific_name = kwargs.pop("scientific_name", None)
        
    def __getattr__(self, name:str):
        scipywarn(f"The current {self.__class__.__name__} is a shim. You need to install the taxoniq package for full functionality")
        return
        
    
# from ncbi.ncbi_entrez import list_databases

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

from core.prog import (scipywarn, safewrapper)

@safewrapper
def get_nearest_parent_common_name(t:Taxon):
    r"""Returns the common name of the taxon.
    If the taxon does not have a common name, then returns the common name of
    its nearest parent.
    """
    if hasTaxoniq and isinstance(t, taxoniq.Taxon):
        try:
            return t.common_name
        except:
            ret = get_nearest_parent_common_name(t.parent)
            return ret
    
    return ""

# supported_species=["Homo", "Danio", "Caenorhabditis", "Rattus", "Mus", "Gallus"]
supported_species=["Rattus", "Mus"]
    
def get_taxon(s:str) -> Taxon | str:
    if hasTaxoniq:
        try:
            if s.lower() in ["mouse", "mice"]:
                s = "Mus"
                
            elif s.lower() in ["rat", "rats"] or s.lower().startswith("rat"):
                s = "Rattus"
                
            taxon = taxoniq.Taxon(scientific_name=s)
            return taxon
        except:
            errorstr = traceback.format_exc()
            scipywarn(f"Cannot obtain a Taxon for {s}:\n{errorstr}")
            return s
    else:
        scipywarn(f"taxoniq package is not installed")
        return s
    
class TaxonDescriptor:
    r"""Python descriptors for taxoniq.Taxon or a placeholder if taxoniq is not available
    default can be a string (scientific name of the species, e.g. Rattus, Mus, Homo, Dabio, Gallus)
    """
    def __set_name__(self, obj:object, name:str):
        if len(name.strip()) == 0:
            raise ValueError("Cannot accept an empty name")
        self._name = "_"+name
        
    def __get__(self, obj:object, objtype:type) -> object:
        if obj is None:
            return
        return getattr(obj, self._name, None)
    
    def __set__(self, obj:object, value:typing.Optional[typing.Union[str, Taxon, type(MISSING)]] = None):
        if isinstance(value, Taxon):
            setattr(obj, self._name, value)
        elif isinstance(value, str) or value in (None, MISSING, pd.NA):
            if hasTaxoniq and isinstance(value, str):
                if value in supported_species:
                    value = Taxon(scientific_name=value)
                else:
                    value = get_taxon(value)
                    
            setattr(obj, self._name, value)
        else:
            raise TypeError(f"Expecting a str, a Taxon, None, or MISSING; instead, got {type(value).__name__}")
