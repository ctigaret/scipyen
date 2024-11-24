# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Wrapper around BrainGlobe API, with shims
"""
import collections, typing, dataclasses, traceback
from dataclasses import MISSING
import numpy as np
import pandas as pd
from qtpy import (QtCore, QtWidgets, QtGui)
from qtpy.QtCore import (Signal, Slot, Property)

# import qasync
# from qasync import asyncSlot

from core.prog import scipywarn
from core import taxonbridge
from core import workspacefunctions as wf
import gui.pictgui as pgui

DEFAULT_RAT_BRAIN_ATLAS = "whs_sd_rat_39um" 
DEFAULT_MOUSE_BRAIN_ATLAS = "allen_mouse_50um"

class BGStructure:
    """Shim class that will be overwritten below if brainglobe packages are installed"""
    def __new__(obj, *args, **kwargs):
        return MISSING
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
        # if hasBrainGlobeAtlasAPI and isinstance(default, BGStructure):
        if hasBrainGlobeAtlasAPI and isinstance(default, brainglobe_atlasapi.structure_class.Structure):
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

#         if isinstance(ret, str):
#             if hasattr(obj, "organism") and hasattr(obj.organism, "taxon"):
#                 if isinstance(obj.organism.taxon, str):
#                     atlas = get_atlas_for_species(obj.organism.taxon)
#                     if isinstance(atlas, brainglobe_atlasapi.BrainGlobeAtlas):
#                         structure = get_atlas_structure(value, atlas)
#                         ret = structure
#                         setattr(obj, self._name, ret)
#                         
#         return ret
    
    
    def __set__(self, obj:object, value:typing.Optional[typing.Union[BGStructure, str, type(pd.NA), type(MISSING)]] = None):
        if hasBrainGlobeAtlasAPI and isinstance(value, brainglobe_atlasapi.structure_class.Structure):
            setattr(obj, self._name, value)
            
        elif isinstance(value, str) or value in (None, MISSING, pd.NA):
            # if isinstance(value, str):
            #     if hasattr(obj, "organism") and hasattr(obj.organism, "taxon"):
            #         if isinstance(obj.organism.taxon, str):
            #             atlas = get_atlas_for_species(obj.organism.taxon)
            #             structure = get_atlas_structure(value, atlas)
            #             setattr(obj, self._name, structure)
            #             return
                
            setattr(obj, self._name, value)
        else:
            raise TypeError(f"Expecting a non-empty str, pandas NA, or None; instead, got {type(value).__name__}")

class BrainAtlasResolver(QtCore.QObject):
    _instance = None
    def __new__(cls, parent=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._atlas = None
        self._atlas_name_ = None
        self.downloadThread = None
        self.progressDlg = None
        self.scipyenWindow = None
        ws = wf.user_workspace()
        if ws is not None:
            self.scipyenWindow = ws["mainWindow"]
        else:
            frame_records = inspect.getouterframes(inspect.currentframe())
            for (n,f) in enumerate(frame_records):
                if "ScipyenWindow" in f[0].f_globals:
                    self.scipyenWindow = f[0].f_globals["ScipyenWindow"].instance()
                    break
        
        if hasBrainGlobeAtlasAPI:
            self.local_atlas_names = get_downloaded_atlases()
            if len(self.local_atlas_names) == 0:
                scipywarn("No mouse or rat brain atlases are downloaded locally; a suitable atlas will be downloaded shortly, but make sure you have a good internet conection")
                
            self.all_atlases = get_all_atlases_lastversions() # mapping atlas name ↦ version
            if len(self.all_atlases) == 0:
                scipywarn("Cannot query the atlases database - check your internet connection")
            
            all_atlas_names = list(self.all_atlases.keys())
            if len(all_atlas_names + self.local_atlas_names) == 0:
                scipywarn("No local atlases and no reliable internet connection - bailing out...")
                return
                
            self.all_available_atlas_names = sorted(list(set(all_atlas_names) | set(self.local_atlas_names)))
            
        else:
            scipywarn(f"Please install brainglobe or at least brainglobe_atlasapi first")
            self.all_available_atlas_names = list()
            self.local_atlas_names = list()
            self.all_atlases = dict()
            
            
    def resolveAtlas(self, taxon:typing.Union[str, taxonbridge.Taxon], atlas_name:typing.Optional[str]=None):
        if len(self.all_available_atlas_names) == 0:
            scipywarn("No atlases are available")
            return
        
        if taxonbridge.hasTaxoniq and isinstance(taxon, taxonbridge.Taxon):
            species = taxonbridge.get_nearest_parent_common_name(taxon)
                
        elif isinstance(taxon, str):
            if len(taxon.strip()) == 0:
                raise ValueError("taxon is an empty string!")
            
            if taxon not in [s.lower() for s in taxonbridge.supported_species] + ["mouse", "mice", "rat", "rats"]:
                raise ValueError(f"taxon {taxon} is not supported")
            
            # NOTE: 2024-11-23 14:40:50
            # try and get a Taxon object using this species string, then get the 
            # actual species from thisTaxon object
            taxonObj = taxonbridge.get_taxon(taxon)
            
            if isinstance(taxonObj, taxonbridge.Taxon):
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
            
        atlas_names_for_species = [a for a in self.all_available_atlas_names if species in a]
        
        if isinstance(atlas_name, str) and len(atlas_name.strip()):
            if atlas_name not in atlas_names_for_species:
                scipwarn(f"The supplied atlas name {atlas_name} is not valid for species {species}")
                
            else:
                default_atlas = atlas_name
                
        else:
            if species == "mouse":
                default_atlas = DEFAULT_MOUSE_BRAIN_ATLAS
                
            elif species == "rat":
                default_atlas = DEFAULT_RAT_BRAIN_ATLAS
                
            else:
                raise ValueError(f"Species {species} is not yet supported ")
        
        ret = ""
        
        if len(atlas_names_for_species) == 0:
            scipywarn(f"No brain atlas for species {species} is found")
            return
        
        elif len(atlas_names_for_species) > 1:
            if default_atlas in atlas_names_for_species:
                scipywarn(f"There is more than one brain atlas available. The default one ({default_atlas}) will be used")
                ret = default_atlas
            else:
                scipywarn(f"There is more than one brain atlas available, but the default one ({default_atlas}) is not among them. The first available one ({atlas_names[0]}) will be used")
                ret = atlas_names_for_species[0]
            
        else:
            ret = atlas_names_for_species[0]
            
        self._atlas_name_ = ret
                
        if len(self._atlas_name_.strip()):
            if self._atlas_name_ not in self.local_atlas_names:
                self._resolveAtlasThreaded()
                # return dl.result # FIXME: 2024-11-24 22:28:01 WRONG
                    
            else:
                # TODO 2024-11-24 21:23:14
                # make 'check_latest' below a Scipyen configurable variable
                # (not Qt configurable)
                self._atlas = BGAtlas(self._atlas_name_, check_latest=False) 
                
    def _resolveAtlasThreaded(self): #, atlas_name:str):
        scipywarn(f"Will try and download {self._atlas_name_}")
        self.progressDlg = QtWidgets.QProgressDialog(f"Downloading {self._atlas_name_}", "", 0, 0, self.scipyenWindow)
        self.progressDlg.setMinimumDuration(1000)
        self.progreDlg.setCancelButton(None)
        self.downloadThread = AtlasDownloadThread(self, self._atlas_name_)
        self.downloadThread.signals.signal_setMaximum[int].connect(self.progressDlg.setMaximum)
        self.downloadThread.signals.signal_Progress[int].connect(self.progressDlg.setValue)
        self.downloadThread.signals.signal_Result[object].connect(self._slot_setAtlas)
        self.downloadThread.signals.signal_Finished.connect(self.finished)
        print(f"Start downloading atlas {self._atlas_name_}.")
        self.downloadThread.start()
        
    @property
    def atlas(self):
        if isinstance(self.downloadThread, QtCore.QThread) and self.downloadThread.isRunning():
            print(f"Atlas {self._atlas_name_} is still downloading; please wait")
            return
        return self._atlas
    
    @atlas.setter
    def atlas(self, o:object):
        self._atlas = o
        
    @Slot(object)
    def _slot_setAtlas(self, o:object):
        self.atlas = o
        
    @Slot()
    def finished(self):
        print(f"Atlas {self._atlas_name_} has been downloaded.")
        if isinstance(self.downloadThread, QtCore.QThread) and self.downloadThread.isRunning():
            self.downloadThread.requestInterruption()
        self.downloadThread.quit()
        self.downloadThread.wait()
        self.progressDlg.cancel()
        self.progressDlg.reset()
        self.progressDlg.close()
        self._instance = None
        
def get_atlas_structure(name:str, atlas:BGAtlas, 
                        acro:bool=False,
                        cutoff = 0.5,
                        maxfound = 10,
                        ) -> dict | None:
    """Best-guess for the atlas a structure corresponding to a named brain region.

    The function tries to match the brain region name given in 'name' parameter
    to the 'name' or 'acronym' attribute of the structures in the atlas — depending
    in the value of the 'acro' parameters. 

    Matching is performed by difflib.get_close_matches. When matches are found, 
    the "best" matching structure is returned.
    

    Parameters:
    ===========
    name:   common name of the brain region. Case sensitive (sometimes)¹ 
    
    atlas:  a brainglobe_atlasapi.BrainGlobeAtlas instance
    
    acro:   flag indicating is the search for matches will take place primarily
            on stucture acronyms (True) or names (False)
            Default: False, meaning that the function will first try to match
            'name' against the structure names, then (and only if no matches are
            found) against the structure acronyms in the atlas.
    
    cutoff: the 'cutoff' parameter for the 'difflib.get_close_matches' function.
            default (here) is 0.5
    
    maxfound:the maximum number of matches to be returned (passed directly to 
            difflib.get_close_matches function).
            Default is 10
    
    See also: difflib.get_close_matches in Python standard library
    
    WARNING: This may yield surprising results, so it is best avoid ambiguities 
        in the 'name' parameter. 
    
    ¹Case sensitivity does not always work as you may think, see examples below.

    Some examples using the Waxholm Space Atlas of the Sprague Dawley Rat Brain 
    (https://www.nitrc.org/projects/whs-sd-atlas):
    
    'name'                          best guess structure:
                                    name                        acronym
    --------------------------------------------------------------------
    hippocampus                     alveus of the hippocampus   alv
    Hippocampus                     Hippocampal region          HR
    Hippocamp                       Hippocampal region          HR
    hippocamp                       Hippocampal region          HR
    Hippocampal                     Hippocampal region          HR
    hippocampal                     Hippocampal region          HR
    CA1                             Cornu ammonis 1             CA1
    ca1                             anterior commissure, 
                                    anterior limb               aca     !
    accum                           Tectum                      Tc      !
    accumb                          Nucleus accumbens           NAc
    core                            cochlea                     Co      !
    accumbens core                  Nucleus accumbens, core     NAc-c
    accumbens, core                 Nucleus accumbens, core     NAc-c
    shell                           Lateral lemniscus           ll      !
    accumbens shell                 Nucleus accumbens, shell    NAc-sh
    accumbens, shell                Nucleus accumbens, shell    NAc-sh
    

    """
    # import editdistance
    import difflib
    if not hasBrainGlobeAtlasAPI:
        scipywarn("BrainGlobe Atlas API is not installed")
        return
    
    if not isinstance(name, str):
        raise TypeError(f"Expecting a str; got {type(name).__name__} instead")
    
    if len(name.strip()) == 0:
        raise ValueError("Expecting a non-empty string")
    
    # structures, snames, sacronyms, sids = zip(*[(s, s["name"], s["acronym"], s["id"]) for s in atlas.structures_list])
    structures, snames, sacronyms = zip(*[(s, s["name"], s["acronym"]) for s in atlas.structures_list])
    
    # first, check against the primary (the "primary" being sacronyms if acro,
    # else snames) 
    sss = sacronyms if acro else snames
    matches = list(map(lambda x: structures[x], map(lambda x: sss.index(x), difflib.get_close_matches(name, sss, 10, 0.5))))
    
    if len(matches) == 0:
        # nothing found => check against the secondary (the "secondary" being
        # the one left out above, i.e., snames if acro else sacronyms)
        sss = snames if acro else sacronyms
        matches = list(map(lambda x: structures[x], map(lambda x: sss.index(x), difflib.get_close_matches(name, sss, 10, 0.5))))
    
    # finally, get the best match (if any found) and augment with atlas name
    # return None when nothing was found
    if len(matches):
        ret = atlas.structures[matches[0]["id"]]
        ret["atlas_name"] = atlas.atlas_name
        return ret
    
class AtlasDownloadThread(QtCore.QThread):
    def __init__(self, parent, atlas_name:str):
        """
        """
        QtCore.QThread.__init__(self, parent)
        self.atlas_name = atlas_name
        self.signals = pgui.ProgressWorkerSignals()
        self.result=None
        
    def progressUpdater(self, current:int, total:int):
        self.signals.signal_setMaximum.emit(total)
        self.signals.signal_Progress.emit(current)
#         if current==0:
#             self.signals.signal_setMaximum.emit(total)
#             
#         else:
#             self.signals.signal_Progress.emit(current)
        
    def run(self):
        try:
            print(f"Downloading {self.atlas_name}")
            self.result = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(self.atlas_name, fn_update=self.progressUpdater)
            self.signals.signal_Result.emit(self.result)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.sig_error.emit((exctype, value, traceback.format_exc()))
            
        else:
            # self.signals.signal_Result.emit(result)
            self.signals.signal_Finished.emit()
        finally:
            # self.signals.signal_Result.emit(result)
            self.signals.signal_Finished.emit()
            
    
