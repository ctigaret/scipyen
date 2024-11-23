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
from core import taxonbridge

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
                        atlas = get_atlas_for_species(obj.organism.taxon)
                        structure = get_atlas_structure(value, atlas)
                
            setattr(obj, self._name, value)
        else:
            raise TypeError(f"Expecting a non-empty str, pandas NA, or None; instead, got {type(default).__name__}")

def get_atlas_for_species(taxon:typing.Union[str, taxonbridge.Taxon]) -> BGAtlas | None:
    # from core import taxonbridge
    if hasBrainGlobeAtlasAPI:
        atlas_names = get_downloaded_atlases()
        if len(atlas_names) == 0:
            scipywarn("No mouse or rat brain atlases are donwloaded locally; make sure you have a good internet conection")
            atlases = get_all_atlases_lastversions()
            if len(atlases) == 0:
                scipywarn("Cannot query the atlases database - check your internet connection")
                return
            atlas_names = list(atlases.keys())
                
        if taxonbridge.hasTaxoniq and isinstance(taxon, taxonbridge.Taxon):
            species = taxonbridge.get_nearest_parent_common_name(taxon)
                
        elif isinstance(taxon, str):
            if len(taxon.strip()) == 0:
                raise ValueError("taxon is an empty string!")
            
            if taxon not in [s.lower() for s in taxonbridge.supported_species] + ["mouse", "mice", "rat"]:
                raise ValueError(f"taxon {taxon} is not supported")
            
            # NOTE: 2024-11-23 14:40:50
            # try and get a Taxon object using this species string, then get the 
            # actual species from thisTaxon object
            taxonObj = taxonbridge.get_taxon(taxon)
            
            if isnstance(taxonObj, taxonbridge.Taxon):
                species = taxonbridge.get_nearest_parent_common_name(taxonObj)
            else:
                # could not retrieve a Taxon object => use taxon parameter as species
                # and continue with that
                species = taxon
            
            if species.lower().startswith("rat") or species.lower().endswith("rat"):
                species = "rat"
            elif any(species.lower().startswith(a) or species.lower().endswith(a) for a in ("mus", "mouse", "mice")):
                species = "mouse"
            
        else:
            raise TypeError(f"'taxon' expected to be Taxon or a str; instad got a {type(taxon).__name__}")
        
        if "mice" in species.lower():
            species = "mouse"
            
        atlas_names = [a for a in atlas_names if species in a]
        
        if species == "mouse":
            default_atlas = DEFAULT_MOUSE_BRAIN_ATLAS
        elif species == "rat":
            default_atlas = DEFAULT_RAT_BRAIN_ATLAS
        else:
            raise ValueError(f"Species {species} is not yet supported ")
        
        ret = ""
        
        if len(atlas_names) == 0:
            scipywarn(f"No brain atlas for species {species} is installed locally; please use brainglobe_atlasapi to download")
            return
        
        elif len(atlas_names) > 1:
            if default_atlas in atlas_names:
                scipywarn(f"There is more than one brain atlas available. The default one ({default_atlas}) will be used")
                ret = default_atlas
            else:
                scipywarn(f"There is more than one brain atlas available, but the default one ({default_atlas}) is not among them. The first available one ({atlas_names[0]}) will be used")
                ret = atlas_names[0]
            
        else:
            ret = atlas_names[0]
                
        if len(ret.strip()):
            return BGAtlas(ret)
                            
def get_atlas_structure(name:str, atlas:typing.Optional[BGAtlas]=None, 
                        acro:bool=False,
                        ) -> dict | None:
    import editdistance
    if not hasBrainGlobeAtlasAPI:
        scipywarn("BrainGlobe Atlas API is not installed")
        return
    
    if not isinstance(name, str):
        raise TypeError(f"Expecting a str; got {type(name).__name__} instead")
    
    if len(name.strip()) == 0:
        raise ValueError("Expecting a non-empty string")
    
    # structures, snames, sacronyms, sids = zip(*[(s, s["name"], s["acronym"], s["id"]) for s in atlas.structures_list])
    structures, snames, sacronyms = zip(*[(s, s["name"], s["acronym"]) for s in atlas.structures_list])
    
    sss = sacronyms if acro else snames
    ll = list(map(lambda x: editdistance.eval(name, x), sss))
    
#     la = list(map(lambda x: editdistance.eval(name, x), sacronyms))
#     ln = list(map(lambda x: editdistance.eval(name, x), snames))
#     
#     ll = list(map(lambda x: min(x), zip(ln,la)))
    
    
    closestNdx = ll.index(min(ll))
    
    if closestNdx == 0:
        return
    
    ret = structures[closestNdx]
    ret["atlas_name"] = atlas.atlas_name
    
    return ret
    
#     words = name.split()
#     
#     a = set([(x, sacronyms[k], sids[k]) for k,x in enumerate(snames) if name.lower() in x.lower() or all(w.lower() in x.lower() for w in words)])
# 
#     b = set([(snames[k], x, sids[k]) for k, x in enumerate(sacronyms) if name.lower() in x.lower() or all(w.lower() in x.lower() for w in words)])
#     
#     return a | b
    
