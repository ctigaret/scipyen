# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Wrapper around BrainGlobe API, with shims
"""
# TODO: 2024-11-25 16:51:43 FIXME
# brainglobe_atlasapi is using requests package for downloading;
# unfortunately, this API is BLOCKING, thus making the UI unresponsive
# and download operation uninterruptible
# TODO: try QNetwork API see what flexibility there is
#
# some preparations:
# 1) figure out where brainglobe downoloads stuff (no need to our own custom locations,
# we're OK with their defaults):
#
# 1.1) get the brainglobe configuration (a configparser ⌣ ) 
# bgconf = bgbridge.brainglobe_atlasapi.config.read_config()
# 1.2) get the directory where atlases are saved
# bgconf["default_dirs"]["brainglobe_dir"] -> by default: $HOME/.brainglobe
# 1.3) get the directory where atlas tarballs are downloaded
# bgconf["default_dirs"]["interm_download_dir"] -> by deault, same as above: $HOME/.brainglobe
# 
# 2) prepare some ingredients
# 2.1) get the remote url for an atlas - given atlas_name:str
# 2.1.1) get the remote version - requires being online
# bgbridge.brainglobe_atlasapi.descriptors.remote_url_base
#   -> 'https://gin.g-node.org/brainglobe/atlases/raw/master/{}'
#
# therefore:
# remote_url = remote_url_base.format("last_versions.conf") ← to be requested
# now read the remote conf (configparser) using QNetwork API
#
# to be continued... 2024-11-25 17:09:34


import collections, typing, dataclasses, traceback, os, sys, pathlib
import functools
from dataclasses import MISSING
import numpy as np
import pandas as pd
from qtpy import (QtCore, QtWidgets, QtGui)
from qtpy.QtCore import (Signal, Slot, Property)

import configparser # from standard library; Scipyen uses confuse from  pypi
                    # so don't "confuse" them(!)

# import qasync
# from qasync import asyncSlot

from core.prog import scipywarn
from core import taxonbridge
from core import workspacefunctions as wf
import gui.pictgui as pgui
from iolib import network

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

    def __set__(self, obj:object, value:typing.Optional[typing.Union[BGStructure, str, type(pd.NA), type(MISSING)]] = None):
        if hasBrainGlobeAtlasAPI and isinstance(value, brainglobe_atlasapi.structure_class.Structure):
            setattr(obj, self._name, value)
            
        elif isinstance(value, str) or value in (None, MISSING, pd.NA):
            setattr(obj, self._name, value)

        else:
            raise TypeError(f"Expecting a non-empty str, pandas NA, or None; instead, got {type(value).__name__}")

class BrainAtlasManager(QtCore.QObject):
    # _instance = None
    # def __new__(cls, parent=None):
    #     if cls._instance is None:
    #         cls._instance = super().__new__(cls)
    # 
    #     return cls._instance
    
    # default_config_file = brainglobe_atlasapi.config.get_brainglobe_dir() / "last_versions.conf" if hasBrainGlobeAtlasAPI else None
    default_config_file = brainglobe_atlasapi.config.CONFIG_PATH if hasBrainGlobeAtlasAPI else None
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._atlas = None
        self._atlas_name_ = None
        self._atlas_in_progress_ = None
        self.downloadThread = None
        self.progressDlg = None
        self.scipyenWindow = None
        self.loopControl = {"break":False}
        self.netMan = network.ScipyenNetworkManager(verbose=False)
        self._tempFile_ = None
        self._waitCondition_ = QtCore.QWaitCondition()
        self._mutex_ = QtCore.QMutex()
        self._locker_ = QtCore.QMutexLocker(self._mutex_)
        

        ws = wf.user_workspace()
        if ws is not None:
            self.scipyenWindow = ws["mainWindow"]
        else:
            frame_records = inspect.getouterframes(inspect.currentframe())
            for (n,f) in enumerate(frame_records):
                if "ScipyenWindow" in f[0].f_globals:
                    self.scipyenWindow = f[0].f_globals["ScipyenWindow"].instance()
                    break
        
#     def refresh(self):
#         if hasBrainGlobeAtlasAPI:
#             self._local_atlases_ = get_atlases_lastversions()
#             self._local_atlas_names_ = list(self._local_atlases_.keys())
#             if len(self._local_atlas_names_) == 0:
#                 scipywarn("No mouse or rat brain atlases are downloaded locally; a suitable atlas will be downloaded shortly, but make sure you have a good internet conection")
#                 
#             self._all_atlases_ = get_all_atlases_lastversions() # mapping atlas name ↦ version
#             if len(self._all_atlases_) == 0:
#                 scipywarn("Cannot query the atlases database - check your internet connection")
#             
#             all_atlas_names = list(self._all_atlases_.keys())
#             if len(all_atlas_names + self._local_atlas_names_) == 0:
#                 scipywarn("No local atlases and no reliable internet connection - bailing out...")
#                 return
#                 
#             self._all_available_atlas_names_ = sorted(list(set(all_atlas_names) | set(self._local_atlas_names_)))
#             
#         else:
#             scipywarn("Please install the REQUIRED package brainglobe (or at least brainglobe_atlasapi)")
#             self._all_atlases_ = dict()
#             self._all_available_atlas_names_ = list()
#             self._local_atlases_ = dict()
#             self._local_atlas_names_ = list()
            
    def initAtlasForSpecies(self, taxon:typing.Union[str, taxonbridge.Taxon], atlas_name:typing.Optional[str]=None):
        if not hasBrainGlobeAtlasAPI:
            scipywarn("Please install REQUIRED package: brainglobe (or at least brainglobe_atlasapi)")
            return
        
        if len(self._all_available_atlas_names_) == 0:
            scipywarn("No atlases are available. Make sure the REQUIRED package brainglobe (or at least brainglobe_atlasapi) is installed.")
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
            
        atlas_names_for_species = [a for a in self._all_available_atlas_names_ if species in a]
        
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
        
        self.initAtlas(ret)
        
    def initAtlas(self, name:typing.Optional[str]=None):
        if name is None or (isinstance(name, str) and (len(name.strip()) == 0 or name not in self.availableAtlasNames)):
            name = self._selectAtlas()
            if name is None:
                return
                    
        if name not in self._local_atlas_names_:
            self._downloadAtlas(name)
        else:
            # TODO 2024-11-24 21:23:14
            # make 'check_latest' below a Scipyen configurable variable
            # (not Qt configurable)
            self._atlas = BGAtlas(name, check_latest=False) 
                
    def showAtlases(self, show_local_path:bool=False, toConsole:bool=True, 
                    table_width:int=80) -> typing.Optional[pd.DataFrame]:
        if toConsole:
            show_atlases(show_local_path, table_width)
        else:
            isLocal = lambda x: x in self.localAtlasNames
            isUpdated = lambda x: self.localAtlases[x]["updated"] if isLocal(x) else False
            localVersion = lambda x: self.localAtlases[x]["version"] if isLocal(x) else ""
            localPath = lambda x: self.localAtlases[x]["local"] if isLocal(x) else ""
            
            ll = sorted(sorted(list((k, isLocal(k), isUpdated(k), localVersion(k), v, localPath(k)) for k,v in self._all_atlases_.items()), key=lambda x: x[0]), key=lambda x: x[1], reverse=True)
            names, downloaded, updated, local_version, latest_version, path = zip(*ll)
            
            if show_local_path:
                return pd.DataFrame({"Names": names, "Downloaded": downloaded, "Updated": updated, "Local version": local_version, "Latest version": latest_version, "Local path": path},
                                   columns = ["Names", "Downloaded", "Updated", "Local version", "Latest version", "Local path"])
            else:
                return pd.DataFrame({"Names": names, "Downloaded": downloaded, "Updated": updated, "Local version": local_version, "Latest version": latest_version},
                                   columns = ["Names", "Downloaded", "Updated", "Local version", "Latest version"])
                
    def _downloadAtlas(self, name:str, setOwn:bool=True):
        # scipywarn(f"Will try and download {name}")
        self.progressDlg = QtWidgets.QProgressDialog(f"Downloading {name}", "", 0, 0, self.scipyenWindow)
        self.progressDlg.setMinimumDuration(1000)
        self.progressDlg.setCancelButton(None)
        self.downloadThread = AtlasDownloadThread(self, name)
        self.downloadThread.signals.signal_setMaximum[int].connect(self.progressDlg.setMaximum)
        self.downloadThread.signals.signal_Progress[int].connect(self.progressDlg.setValue)
        if setOwn:
            self.downloadThread.signals.signal_Result[object].connect(self._slot_setAtlas)
        self.downloadThread.signals.signal_Finished.connect(self.finished)
        # print(f"Start downloading atlas {name}.")
        if setOwn:
            self._atlas_in_progress_ = name
        self.downloadThread.start()
        
    def _updateAtlas(self, atlas_name:str, inBatch:bool=False):
        from brainglobe_atlasapi.utils import (
            _rich_atlas_metadata,
            check_gin_status,
            check_internet_connection,
        )
        import shutil
        if atlas_name not in self.localAtlasNames:
            return
        
        atlas = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(atlas_name, check_latest=False)
        
        folder = atlas.brainglobe_dir / atlas.local_full_name
        
        shutil.rmtree(folder)
        
        if folder.exists():
            raise RuntimeError(f"Cannot delete the old version.")
        
        if inBatch:
            # force download
            atlas.download_extract_file()
            # atlas = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(atlas_name)
        else:
            self._downloadAtlas(name, setOwn=False)
            
    def installAtlas(self, name:typing.Optional[str] = None):
        from gui.itemslistdialog import ItemsListDialog
        if name is None or (isinstance(name, str) and (len(name.strip()) == 0 or name not in self.availableAtlasNames)):
            name = self._selectAtlas()
            if name is None:
                return
                    
        self._downloadAtlas(name, setOwn=False)
        
    def _selectAtlas(self) -> str:
        from gui.itemslistdialog import ItemsListDialog
        dlg = ItemsListDialog(parent = self.scipyenWindow, itemsList = self.availableAtlasNames,
                                title = f"Choose atlas:")
        a = dlg.exec_()
        
        if a == QtWidgets.QDialog.Accepted:
            names = dlg.selectedItemsText
            if len(names):
                return names[0]
        
    def uninstallAtlas(self, name:str):
        from gui.itemslistdialog import ItemsListDialog
        
        if len(self.localAtlasNames) == 0:
            print("No atlas is installed locally")
            return
        
        if name not in self.localAtlasNames:
            dlg = ItemsListDialog(parent = self.scipyenWindow, itemsList = self.localAtlasNames,
                                  title = f"Choose atlas:")
            a = dlg.exec_()
            
            if a == QtWidgets.QDialog.Accepted:
                names = dlg.selectedItemsText
                if len(names):
                    name = names[0]
        
        self._downloadAtlas(name, setOwn=False)
        
    @property
    def atlas(self):
        if isinstance(self.downloadThread, QtCore.QThread) and self.downloadThread.isRunning() and isinstance(self._atlas_in_progress_, str):
            print(f"Atlas {self._atlas_in_progress_} is still downloading; please wait")
            return
        
        if self._atlas is None:
            scipywarn("No atlas has been initialized yet; please call one of:\n self.initAtlas(…)\n self.initAtlasForSpecies(…)\n self.installAtlas(…)\n")
            
        return self._atlas
    
    @property
    def localAtlasNames(self) -> list[str]:
        return self._local_atlas_names_
    
    @property
    def availableAtlasNames(self) -> list[str]:
        return self._all_available_atlas_names_
    
    @property
    def atlases(self) -> dict:
        return self._all_atlases_
    
    @property
    def localAtlases(self) -> dict:
        return self._local_atlases_
        # return dict((k,v) for k,v in self.atlases.items() if k in self.localAtlasNames)
    
    @Slot(object)
    def _slot_setAtlas(self, o:object):
        self._atlas = o
        self._atlas_in_progress_ = None
        
    @Slot()
    def finished(self):
        # print(f"Atlas {self._atlas_name_} has been downloaded.")
        if isinstance(self.downloadThread, QtCore.QThread) and self.downloadThread.isRunning():
            self.downloadThread.requestInterruption()
        # for signal in self.downloadThread.signals.signals:
        #     signal.disconnect()
        self.downloadThread.quit()
        self.downloadThread.wait()
        self.progressDlg.cancel()
        self.progressDlg.reset()
        self.progressDlg.close()
        self.progressDlg = None
        self.downloadThread = None
        self._atlas_in_progress_ = None
        # self._instance = None
        
    def updateLocalAtlases(self, force:bool=False):
        # from brainglobe_atlasapi.update_atlases import update_atlas
        progressDlg = QtWidgets.QProgressDialog("Updating local atlases...", "Abort",
                                                0, len(self.localAtlasNames), 
                                                self.scipyenWindow)
        
        progressDlg.setMinimumDuration(1000)
        progressDlg.canceled.connect(self._slot_breakLoop)
        
        workerThread = pgui.LoopWorkerThread(self, self.batchUpdate)
        workerThread.signals.signal_Progress[int].connect(progressDlg.setValue)
        workerThread.signals.signal_Result[object].connect(self.batchUpdateReady)
        workerThread.signals.signal_Finished.connect(progressDlg.reset)
        workerThread.start()
        
        
    def batchUpdate(self, **kwargs):
        canceled = False
        progressSignal = kwargs.pop("progressSignal", None)        
        for k, name in enumerate(self.localAtlasNames):
            try:
                self._updateAtlas(name, inBatch=True)
                
            except:
                traceback.print_exc()
                continue
            
            progressSignal.emit(k)
        
    @Slot(object)
    def batchUpdateReady(self, _):
        self.loopControl["break"] = False
        # try:
        #     ok = bool(obj) == True
        # except:
        #     ok = False
            
    @Slot()
    def _slot_breakLoop(self):
        self.loopControl["break"] = True
        
    def updateLocalAtlas(self, name:str, force:bool=False):
        # from brainglobe_atlasapi.update_atlases import update_atlas
        if name not in self.localAtlasNames:
            self._downloadAtlas(name, False)
        else:
            self._updateAtlas(name)
            
#     def _retrieveRemoteAtlasesList(self):
#         """Does what brainglobe_atlasapi.utils.conf_from_url(…) does.
#         Uses Qt Network framework.
#         """
#         if not hasBrainGlobeAtlasAPI:
#             return
#         
#         url = BGAtlas._remote_url_base.format("last_versions.conf")
#         self.netMan.sig_textFromUrl[object].connect(self._slot_remoteConfigReceived)
#         self.netMan.getTextFromUrl(url)
            
#     @Slot(object)
#     def _slot_remoteConfigReceived(self, txt:object):
#         if hasBrainGlobeAtlasAPI:
#             if isinstance(txt, str):
#                 conf_object = configparser.ConfigParser()
#                 conf_object.read_string(txt)
#                 if not self.default_config_file.parent.exists():
#                     self.default_config_file.parent.mkdir(parents=True, exist_ok=True)
#                     
#                 with open(self.default_config_file, "w") as f_out:
#                     conf_object.write(f_out)
         
    def getBrainGlobeConfiguration(self, file_path:typing.Optional[pathlib.Path]=None,
                                   asDict:bool = False) -> configparser.ConfigParser:
        """Reads the brainglobe configuration from a local file.
        
        WARNING: This is NOT the atlas configuration (last_versions.conf) !!!
        
        On UN*X platforms, by default, this is file is '~/.config/brainglobe/bg_config.conf'
        
        """
        if not hasBrainGlobeAtlasAPI:
            return
        
        if file_path is None:
            file_path = self.default_config_file
            
        if not isinstance(file_path, pathlib.Path) or not file_path.exists():
            return
            
        conf_object = configparser.ConfigParser()
        with open(file_path) as file_object:
            conf_object.read_file(file_object)
            
        if not conf_object.has_section("default_dirs"):
            raise RuntimeError(f"The {file_path} is an invalid brainglobe configuration file; please provide a valid file or reinstall brainglobe package")
            
        if asDict:
            return dict((s, dict(conf_object[s])) for s in conf_object.sections())
            
        return conf_object

    def getAtlasVersions(self, file_path:typing.Optional[pathlib.Path]=None) -> dict | None:
        if not hasBrainGlobeAtlasAPI:
            return
        
        conf = self.getBrainGlobeConfiguration(file_path)
        atlases_conf_path = pathlib.Path(os.path.join(conf["default_dirs"]["brainglobe_dir"], "last_versions.conf"))
        
        if atlases_conf_path.exists():
            atlases_conf = configparser.ConfigParser()
            with open(atlases_conf_path) as conf_file:
                atlases_conf.read_file(conf_file)
            if atlases_conf.has_section("atlases"):
                return dict(atlases_conf["atlases"])
            else:
                raise RuntimeError(f"Invalid atlases configuration file {atlases_conf_path}")
            
        else:
            scipywarn(f"File {atlases_conf_path} does not exist; will retrieve a copy from the remote GIN site, then call this method again")
            self.getRemoteAtlasVersions()
            
    def getRemoteAtlasVersions(self, file_path:typing.Optional[pathlib.Path]=None):
        if not hasBrainGlobeAtlasAPI:
            return
        
        if file_path is None:
            conf = self.getBrainGlobeConfiguration()
            file_path = os.path.join(conf["default_dirs"]["brainglobe_dir"], "last_versions.conf")
            
        self._tempFile_ = file_path
        url = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas._remote_url_base.format("last_versions.conf")
        self.netMan.sig_finished.connect(self._slot_last_versions_conf_downloaded)
        self.netMan.getUrl(url, destination=file_path)
        
    def compareAtlasVersions(self):
        # TODO: 2024-11-29 13:48:08
        # write code to retrieve versions from locally downloaded atlases
        # the retrieve the remote last_versions.conf to compare versions
        # advertise atlas: name current and remote version and whether it needs
        # to be updated
        pass
        
        
    @Slot()
    def _slot_last_versions_conf_downloaded(self):
        print(printStyled(f"Latest atlas versions information was downloaded to {self._tempFile_}; you can call getAtlasVersions('{self._tempFile_}') method again", "green", True))
        self._tempFile_ = None
        self.netMan.sig_finished.disconnect()
    
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
            self.signals.signal_Finished.emit()
            
        finally:
            self.signals.signal_Finished.emit()
            
    
# ### BEGIN ---- module-level functions
        
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
    
# ### END ---- module-level functions
    
