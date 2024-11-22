# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Wrapper around BrainGlobe API, with shims
"""
import collections, typing, dataclasses
from dataclasses import MISSING
import numpy as np
import pandas as pd

from core.prog import scipywarn

DEFAULT_RAT_BRAIN_ATLAS = "whs_sd_rat_39um" 
DEFAULT_MOUSE_BRAIN_ATLAS = "allen_mouse_50um"

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
    and Princeton atlases, but to "Field CA1 of the hippocampus" in Kim atlas.
    
        
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
            if isinstance(value, str):
                if hasattr(obj, "organism") and hasattr(obj.organism, "taxon"):
                    if isinstance(obj.organism.taxon, str):
                        atlas = resolve_atlas(obj.organism.taxon)
                
            setattr(obj, self._name, value)
        else:
            raise TypeError(f"Expecting a non-empty str, pandas NA, or None; instead, got {type(default).__name__}")

def resolve_atlas(taxon:object):
    from core import taxonbridge
    if hasBrainGlobeAtlasAPI:
        if taxonbridge.hasTaxoniq:
            species = taxonbridge.get_common_name(taxon)
        elif isinstance(taxon, str) and taxon in taxonbridge.supported_species:
            local_atlas_names = get_downloaded_atlases()
            if len(local_atlas_names):
                if taxon.startswith("Rat"):
                    species = "rat"
                    rat_atlas_names = [a for a in local_atlas_names if "rat" in a]
                    if len(rat_atlas_names) == 0:
                        scipywarn("No rat brain atlas is installed locally; please use brainglobe_atlasapi to download")
                        return
                    
                    elif len(rat_atlas_names) > 1:
                        if DEFAULT_RAT_BRAIN_ATLAS in rat_atlas_names:
                            scipywarn(f"There is more than one rat brain atlas downloaded locally. The default one {DEFAULT_RAT_BRAIN_ATLAS} will be used")
                            return DEFAULT_RAT_BRAIN_ATLAS
                        else:
                            scipywarn(f"There is more than one rat brain atlas downloaded locally, but the default one {DEFAULT_RAT_BRAIN_ATLAS} is not among them. The first available one ({rat_atlas_names[0]}) will be used")
                            return rat_atlas_names[0]
                        
                    else:
                        return rat_atlas_names[0]
                            
                elif taxon.startswith("Mus"):
                    species = "mouse"
                else:
                    scipywarn("The only supported species are rat (Rattus) and mouse (Mus)")
                    return
                
                atlas_names = [a for a in local_atlas_names if species in a]
                if len(atlas_names) == 0:
                    scipywarn(f"No brain atlasfor species {species} is installed locally; please use brainglobe_atlasapi to download")
                    return
                
                elif len(atlas_names) > 1:
                    if DEFAULT_MOUSE_BRAIN_ATLAS in mouse_atlas_names:
                        scipywarn(f"There is more than one rat brain atlas downloaded locally. The default one {DEFAULT_MOUSE_BRAIN_ATLAS} will be used")
                        return DEFAULT_MOUSE_BRAIN_ATLAS
                    else:
                        scipywarn(f"There is more than one rat brain atlas downloaded locally, but the default one {DEFAULT_MOUSE_BRAIN_ATLAS} is not among them. The first available one ({mouse_atlas_names[0]}) will be used")
                        return mouse_atlas_names[0]
                    
                else:
                    return mouse_atlas_names[0]
                            
        
    
    
