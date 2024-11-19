# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Wrapper around BrainGlobe API
"""
import collections, typing, dataclasses
from dataclasses import MISSING
import numpy as np
import pandas as pd

class BGStructure:
    """Shim class that will be overwritten below if brainglobe packages are installed"""
    def __new__(obj, *args, **kwargs):
        return NISSING
    def __init__(self, *args, **kwargs):
        pass
    
class BGAtlas:
    """Shim class that will be overwritten below if brainglobe_atlasapi package is installed"""
    def __init__(self, *args, **kwargs):
        pass
    
    @property
    def annotation(self) -> np.ndarray: return np.array([])

    @property
    def atlas_name(self) -> str: return ""
    
    def additional_references(self) -> collections.UserDict : return collections.UserDict()
    
    @property
    def lookup_df(self) -> pd.DataFrame: return pd.DataFrame(columns = ["acronym", "id", "name"])
    
    def local_full_name(self) -> str: return ""

    def __getattr__(self, name:str):
        scipywarn(f"The brainglobe_atlasapi package is not installed; {self.__class__.__name__} is just a placeholder")
        return
    
hasBrainGlobe=False
hasBrainGlobeAtlasAPI=False
try:
    import brainglobe_atlasapi
    from brainglobe_atlasapi import BrainGlobeAtlas as BGAtlas
    from brainglobe_atlasapi.list_atlases import (get_all_atlases_lastversions,
                                                  get_atlases_lastversions,
                                                  get_downloaded_atlases,
                                                  get_local_atlas_version,
                                                  show_atlases)
    from brainglobe_atlasapi.structure_class import Structure as BGStructure
    
    hasBrainGlobe=True
    hasBrainGlobeAtlasAPI=True
except:
    hasBrainGlobeAtlasAPI=False
    hasBrainGlobe=False
    get_all_atlases_lastversions = lambda : dict()
    get_atlases_lastversions = lambda : dict()
    get_downloaded_atlases = lambda : list()
    get_local_atlas_version = lambda x: str()
    def show_atlases(show_local_path:bool=False, table_width:int=88): None

class BGStructureDescriptor:
    """Generic, str-based brain structure descriptor.
    Currently, a shim, to evolve into a descriptor for instances of 
    brainglobe_atlasapi.structure_class.Structure once I've figured out a way to
    "normalize" the structure IDs for corresponding structures across various 
    atlases.
    
    For example, the structure with name "Hippocampal formation" has the acronym
    "HF" in Waxholm rat brain atlas, but to "HPF" in Allen adult brain atlas (and 
    (and the derived ones, like Princeton mouse atlas or Kim mouse atlas).
    
    
    There are also discrepancies in the "canonical" name of the structure, e.g.
    acronym "CA1" is mapped to "Cornu ammonis 1" in Waxholm, "Field CA1" in Allen
    and Princeton atlases, bu to "Field CA1 of the hippocampus" in Kim atlas.
    
        
    """
    def __init__(self, *, default:typing.Optional[typing.Union[BGStructure, str, type(pd.NA), type(MISSING)]] = None):
        if hasBrainGlobeAtlasAPI and isinstance(default, BGStructure):
            self._default = default
            
        elif isinstance(default, str) or default in (None, MISSING, pd.NA):
            self._default = default
            
        elif not isinstance(default, type(pd.NA)):
            raise TypeError(f"Expecting a BGSStructure, a non-empty str, pandas NA, None or MISSING; instead, got {type(default).__name__}")
        
    def __set_name__(self, obj:object, name:str):
        if len(name.strip()) == 0:
            raise ValueError("Cannot accept an empty name")
        self._name = "_"+name
    
    def __get__(self, obj:object, objtype:type) -> object:
        if obj is None:
            return self._default
        return getattr(obj, self._name, self._default)
    
    def __set__(self, obj:object, value:typing.Optional[typing.Union[BGStructure, str, type(pd.NA), type(MISSING)]] = None):
        if hasBrainGlobeAtlasAPI and isinstance(value, BGStructure):
            setattr(obj, self._name, value)
        elif isinstance(value, str) or value in (None, MISSING, pd.NA):
            setattr(obj, self._name, value)
        else:
            raise TypeError(f"Expecting a non-empty str, pandas NA, or None; instead, got {type(default).__name__}")
