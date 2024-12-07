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
# 2.1) get the remote url for an atlas - given atlasName:str
# 2.1.1) get the remote version - requires being online
# bgbridge.brainglobe_atlasapi.descriptors.remote_url_base
#   -> 'https://gin.g-node.org/brainglobe/atlases/raw/master/{}'
#
# therefore:
# remote_url = remote_url_base.format("last_versions.conf") ← to be requested
# now read the remote conf (configparser) using QNetwork API
#
# to be continued... 2024-11-25 17:09:34


import traceback, os, sys, pathlib, shutil, inspect
import collections, typing, dataclasses, functools, itertools
from dataclasses import MISSING
import numpy as np
import pandas as pd
import quantities as pq
from qtpy import (QtCore, QtWidgets, QtGui)
from qtpy.QtCore import (Signal, Slot, Property)

import configparser # from standard library; Scipyen uses confuse from  pypi
                    # so don't "confuse" them(!)

# import qasync
# from qasync import asyncSlot

from core.prog import scipywarn, printStyled, safeWrapper
from core import taxonbridge, utilities
from core import workspacefunctions as wf
from core import quantities as scq
# import gui.pictgui as pgui # avoid circular import
from gui.widgets.cancellableqprogressbar import CancellableQProgressBar
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
    """Access for brainglobe atlasapi, with non UI blocking network operations.
    """
    # _instance = None
    # def __new__(cls, parent=None):
    #     if cls._instance is None:
    #         cls._instance = super().__new__(cls)
    # 
    #     return cls._instance
    
    default_config_file = brainglobe_atlasapi.config.CONFIG_PATH if hasBrainGlobeAtlasAPI else None
    
    remoteUrlBase = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas._remote_url_base if hasBrainGlobeAtlasAPI else None
    
    default_free_space_fraction_allowed = 0.01
    
    assumed_compression_ratio = 2.
    
    def __init__(self, maxFileSystemFraction:typing.Optional[float] = None,
                 parent=None):
        """Parameters:
        maxFileSystemFraction: float in the interval [0.1 ⋯ 0.9]
            The maximum file system size available for downloading an extracting
            an atlas data. This will take into account the temporary file space
            occupied by the archive. 
    
            As the final size of the extracted data is not known a priori, this 
            class will assume a conservative compression ratio of 2/1.
    
            Thus, for an archive of 1 GiB, the resulting data after extraction
            would occupy 2 GiB. 
    
            This means that a safe installation of atlas data would require
            3 × archive size:
    
                the archive size for the download + twice the archive size for
                extracted data, even if the archive will be deleted after the
                extraction.
    
    
    
            By default this is set to 0.1
    
    
        """
        super().__init__(parent=parent)
        self._atlas = None
        self._atlas_name_ = None
        self._atlas_in_progress_ = None
        self.downloadThread = None
        self.progressDlg = None
        # self.scipyenWindow = None
        self.loopControl = {"break":False}
        self.netMan = network.ScipyenNetworkManager(progressUIFactory = CancellableQProgressBar)
        self._current_atlases_versions_ = None # cache this
        self._current_atlases_versions_updated_ = True
        if isinstance(maxFileSystemFraction, float) and maxFileSystemFraction >= 0.1 and maxFileSystemFraction <= 0.9:
            self._maxFreeSpaceFraction_ = maxFileSystemFraction
        else:
            self._maxFreeSpaceFraction_ = self.default_free_space_fraction_allowed
            
        self.scipyenWindow = wf.getMainScipyenWindow()
        
        # ws = wf.user_workspace()
        # # self._user_ns_ = ws
        # if ws is not None:
        #     self.scipyenWindow = ws["mainWindow"]
        # else:
        #     # self._user_ns_ = dict()
        #     frame_records = inspect.getouterframes(inspect.currentframe())
        #     for (n,f) in enumerate(frame_records):
        #         if "ScipyenWindow" in f[0].f_globals:
        #             self.scipyenWindow = f[0].f_globals["ScipyenWindow"].instance()
        #             break
        
    @classmethod
    def hasBrainGlobeAtlasAPI(self)->bool:
        from gui.workspacegui import GuiMessages
        if not hasBrainGlobeAtlasAPI:
            scipywarn("The 'brainglobe_atlasapi' package is not installed")
            GuiMessages.informationMessage_static(self.scipyenWindow, 
                                                  f"{self.__class__.__name__}",
                                                  f"Please install brainglobe_atlasapi package.")
            return False
        
        return True
        
    def initAtlasForSpecies(self, taxon:typing.Union[str, taxonbridge.Taxon], atlasName:typing.Optional[str]=None):
        if not self.hasBrainGlobeAtlasAPI():
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
        
        if isinstance(atlasName, str) and len(atlasName.strip()):
            if atlasName not in atlas_names_for_species:
                scipwarn(f"The supplied atlas name {atlasName} is not valid for species {species}")
                
            else:
                default_atlas = atlasName
                
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
        
    def _parse_size(self, s:str) -> int:
        """Parses the archive size from the HTML file for a given atlas archive.
        Code taken from brainglobe_atlasapi
        """
        import re
        search_result = re.search("([0-9]+\.[0-9] [MGK]B)|([0-9]+ [MGK]B)", s)
        assert search_result is not None
        sz_str = search_result.group()
        assert sz_str is not None
        sz = float(sz_str[:-3])
        pfx = sz_str[-2]
        if pfx == "G":
            sz *= 1e9
        elif pfx == "M":
            sz *= 1e6
        elif pfx == "K":
            sz *= 1e3
        return int(sz)    
    
    def _getArchiveSizeAndDownload(self,info:QtCore.QByteArray,
                                   manager:network.ScipyenNetworkManager,
                                   targetDir:str,
                                   url:typing.Union[str, QtCore.QUrl],
                                   ) -> None:
        from gui.workspacegui import GuiMessages
        
        if not isinstance(info, QtCore.QByteArray):
            raise TypeError(f"In BrainAtlasManager._getArchiveSizeAndDownload: Expecting a QByteArray; instead, got {type(info).__name__}")
        
        info = bytes(info).decode()
        
        if not isinstance(info, str) or len(info.strip()) == 0:
            scipywarn("BrainAtlasManager._getArchiveSizeAndDownload received invalid data")
            return 
        
        sz = self._parse_size(info)
        
        if isinstance(sz, int):
            t,u,f = shutil.disk_usage(targetDir)
            
            freeSpace = scq.getInformationQuantity(f)
            archiveSize = scq.getInformationQuantity(sz)
            neededSpace = archiveSize * (self.assumed_compression_ratio + 1)
            
            if float(neededSpace/freeSpace) >= self.default_free_space_fraction_allowed:
                txt = [f"You are about to download a file with size of {scq.quantity2str(archiveSize,precision=1)}",
                       f"requiring {scq.quantity2str(neededSpace, precision=1)} for a 'safe' installation!",
                       f"This will occupy over {self.default_free_space_fraction_allowed} of the currently available file system space ({scq.quantity2str(freeSpace, precision=1)}).",
                       "Do you want to continue?"]
                ret = GuiMessages.questionMessage_static(None,
                                                   title="Large File Download!",
                                                   text="\n".join(txt))
                if ret != QtWidgets.QMessageBox.Yes:
                    self.cancelDownload()
                    # manager.slot_abortReply()
                    return
                
            
            manager.setNextDownloadSize(sz)
        else:
            scipywarn("In BrainAtlasManager._getArchiveSizeAndDownload: Could not get the size of the next download")
        
        # targetDir = self.getBrainGlobeConfiguration()["default_dirs"]["brainglobe_dir"]   
        destination = os.path.join(targetDir, "archive.tar.gz")
        manager.getUrl(url, destination=destination, replyHandler = None) 
        
    def testAtlasDownload(self):
        """Tests downloading and extracting an atlas archive.
        See iolib.network.example_sequential_download_handler for explanations
        TODO - refactor this into self.downloadAtlas/self._updateAtlas
        """
        if not self.hasBrainGlobeAtlasAPI():
            return
        
        archiveName = "example_mouse_100um_v1.2.tar.gz"
        versions = self.getAtlasesConfiguration()
        
        resolution = list((k,v) for k, v in versions.items() if archiveName.startswith(k))
        
        if len(resolution):
            atlasName, atlasVersion = resolution[0]
            
        localAtlasDir = self.localAtlasRepository / f"{atlasName}_v{atlasVersion}"
        
        if localAtlasDir.exists():
            shutil.rmtree(localAtlasDir)

        url = self.remoteUrlBase.format(archiveName)
        
        url1 = url.replace("raw", "src")
        
        self.netMan = network.ScipyenNetworkManager(progressUIFactory = CancellableQProgressBar)
        self.netMan.sig_networkError[object].connect(self._slot_networkError)
        self.netMan.sig_resultReady[object].connect(self._slot_extractArchive)
        self.netMan.sig_finished.connect(self.slot_networkOperationFinished)
        
        handle = functools.partial(self._getArchiveSizeAndDownload, 
                                   targetDir = self.localDownloadDirectory,
                                   url = url)
        
        self.netMan.getUrl(url1, destination=None, replyHandler=handle)
        
    @Slot(object)
    def _slot_networkError(self, url_msg:tuple[str]):
        from gui.workspacegui import GuiMessages
        print(f"{self.__class__.__name__}._slot_networkError: url_msg = {url_msg}")
        GuiMessages.criticalMessage_static(self.scipyenWindow, 
                                           f"{self.__class__.__name__}",
                                           f"Error from {url_msg[0]}:\n{url_msg[1]}")
        
    @Slot(object)
    def _slot_extractArchive(self, target:typing.Union[str, pathlib.Path]) -> None:
        import tarfile
        print(f"{self.__class__.__name__}._slot_extractArchive: target = {target}")
        targetDir = self.getBrainGlobeConfiguration()["default_dirs"]["brainglobe_dir"]
        if isinstance(target, str):
            target = pathlib.Path(target)
            
        elif not isinstance(target, pathlib.Path):
            raise TypeError(f"'target' expected a str or a pathlib.Path; instead, got {type(target).__name__}")
            
        if not isinstance(targetDir, str) or not os.path.isdir(targetDir):
            raise ValueError(f"'targetDir ('{targetDir}') is not a directory")
        
        if isinstance(target, pathlib.Path):
            path = target.as_posix()
            if not target.exists():
                raise RuntimeError(f"In {__name__}.extract_archive: File object {path} does not exist!")
            
            # print(f"In {self.__class__.__name__}._slot_extractArchive: path = {path}")
            tar = tarfile.open(path)
            try:
                tar.extractall(path = targetDir)
                tar.close()
                target.unlink()
            except:
                traceback.print_exc()
        
        # if self.netMan.receivers(self.netMan.sig_finished) > 0:
        #     self.netMan.sig_finished.disconnect()
        # if self.netMan.receivers(self.netMan.sig_replyFromUrl) > 0:
        #     self.netMan.sig_replyFromUrl.disconnect()
        # if self.netMan.receivers(self.netMan.sig_resultReady) > 0:
        #     self.netMan.sig_resultReady.disconnect()
        
    def initAtlas(self, name:typing.Optional[str]=None):
        if name is None or (isinstance(name, str) and (len(name.strip()) == 0 or name not in self.availableAtlasNames)):
            name = self.selectAtlasName()
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
        """Shows atlases using brainglobe_atlasapi.
        WARNING: May be blocking the GUI
        """
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
                
    def checkAtlasGINStatus(self):
        url = QtCore.QUrl("https://gin.g-node.org/")
        self.netMan.sig_resultReady[object].connect(self._slot_checkGINReady)
        self.netMan.sig_finished.connect(self.slot_networkOperationFinished)
        self.netMan.checkUrl(url)
        
    def getRemoteAtlasArchiveFileSizes(self): # TODO
        atlasesConf = self.getAtlasesConfiguration()
        names, versions = zip(*list(atlasesConf.items()))
        archiveNames = list(map(lambda x: f"{x[0]}_v{x[1]}.tar.gz", zip(names, versions)))
        # archiveNames = list(map(lambda x: f"{x[0]}_v{x[1]}.tar.gz", zip(*list(atlasesConf.items()))))
        
        urls = list(map(lambda x: self.remoteUrlBase.format(x).replace("raw", "src"), archiveNames))
        
    def _reportRemoteArchiveSizes(self):
        pass
        
    @Slot(object)
    def _slot_checkGINReady(self, result):
        errorMsg = self.netMan.networkErorName
        scipywarn(f"Got {errorMsg} from {result[1]}" )
        if self.netMan.receivers(self.netMan.sig_resultReady) > 0:
            self.netMan.sig_resultReady.disconnect()
            
    @Slot()
    def cancelDownload(self):
        try:
            self.netMan.networkReply.abort()
            self.netMan.networkReply.close()
        except:
            traceback.print_exc()
            
    def downloadAtlas(self, name:typing.Optional[str]) -> None:
        """Downloads an atlas data from the BrainGlobe GIN repository
        
        https://gin.g-node.org/brainglobe/atlases/raw/master/
        
        If the atlas data already exists locally, it will be overwritten.
        
        By default, atlas data is stored in the $HOME/.brainglobe directory
        (on UNIX operating systems).
        
        """
        frame_records = inspect.getouterframes(inspect.currentframe())
        
        if "console" in frame_records[1].frame.f_globals:
            dlgParent = frame_records[1].frame.f_globals["console"]
        else:
            dlgParent = self.scipyenWindow
        
        if not self.hasBrainGlobeAtlasAPI():
            return
        
        versions = self.getAtlasesConfiguration()
        if not isinstance(name, str) or len(name.strip()) == 0 or name not in self.atlases:
            name = self.selectAtlasName(name, dlgParent = dlgParent)
            
        if name is None:
            return
        
        version = versions[name]
            
        archiveName = f"{name}_v{version}.tar.gz"
        
        localAtlasDir = self.localAtlasRepository / f"{name}_v{version}"
        if localAtlasDir.exists():
            shutil.rmtree(localAtlasDir)
        
        url = self.remoteUrlBase.format(archiveName)
        
        url1 = url.replace("raw", "src")
        
        self.netMan = network.ScipyenNetworkManager(progressUIFactory = CancellableQProgressBar)
        self.netMan.sig_resultReady[object].connect(self._slot_extractArchive)
        
        handle = functools.partial(self._getArchiveSizeAndDownload, 
                                   targetDir = self.localDownloadDirectory,
                                   url = url)
        
        self.netMan.getUrl(url1, destination=None, replyHandler=handle)
        
        
    @Slot()
    def slot_networkOperationFinished(self):
        if isinstance(self.netMan, network.ScipyenNetworkManager):
            color = "yellow" if self.netMan.networkError else "green"
            print(printStyled(f"{self.__class__.__name__} network operation finished with {self.netMan.networkErrorName}", color, True))
            
#     def _updateAtlas(self, atlasName:str, inBatch:bool=False):
#         """
#         TODO - Do NOT use yet! - see testAtlasDownload()
#         """
#         from brainglobe_atlasapi.utils import (
#             _rich_atlas_metadata,
#             check_gin_status,
#             check_internet_connection,
#         )
#         if atlasName not in self.localAtlasNames:
#             return
#         
#         atlas = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(atlasName, check_latest=False)
#         
#         folder = atlas.brainglobe_dir / atlas.local_full_name
#         
#         shutil.rmtree(folder)
#         
#         if folder.exists():
#             raise RuntimeError(f"Cannot delete the old version.")
#         
#         if inBatch:
#             # force download
#             atlas.download_extract_file()
#             # atlas = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(atlasName)
#         else:
#             self._downloadAtlas(name, setOwn=False)
            
    def installAtlas(self, name:typing.Optional[str] = None):
        # TODO 2024-12-03 14:06:33 finalize me!
        from gui.itemslistdialog import ItemsListDialog
        if name is None or (isinstance(name, str) and (len(name.strip()) == 0 or name not in self.availableAtlasNames)):
            name = self.selectAtlasName()
            if name is None:
                return
            
        pass

    def selectAtlasName(self, choices:typing.Optional[typing.Sequence[str]]=None,
                        dlgTitle:typing.Optional[str]=None,
                        dlgParent:typing.Optional[QtWidgets.QWidget] = None) -> str:
        from gui.itemslistdialog import ItemsListDialog

        if not self.hasBrainGlobeAtlasAPI():
            return
        
        atlasNames = self.atlasNames
        
        if isinstance(choices, (tuple, list)) and all(isinstance(v, str) for v in choices):
            names = list(itertools.chain.from_iterable(map(lambda c: filter(lambda x: c in x, atlasNames), choices)))
            if len(names) == 0:
                scipywarn("No valid atlas names were supplied")
                names = atlasNames
            
        elif isinstance(choices, str) and len(choices.strip()):
            names = list(filter(lambda x: choices in x, atlasNames))
            if len(names) == 0:
                scipywarn("No valid atlas names were supplied")
                names = atlasNames
            
        else:
            names = atlasNames
            
        if len(names) == 0:
            scipywarn
            
        if not isinstance(dlgTitle, str) or len(dlgTitle.strip()) == 0:
            dlgTitle = "Choose from available atlas names:"
            
        if dlgParent is None:
            dlgParent = self.scipyenWindow
        
        dlg = ItemsListDialog(parent = dlgParent, itemsList = names,
                                title = dlgTitle)
        
        a = dlg.exec_()
        
        if a == QtWidgets.QDialog.Accepted:
            names = dlg.selectedItemsText
            if len(names):
                return names[0]
        
    def uninstallAtlas(self, name:str):
        """
        TODO - Do NOT use yet!
        """
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
        
        # self._downloadAtlas(name, setOwn=False)
        
    @property
    def atlas(self):
        """
        TODO  - do NOT use yet!
        """
        pass
#         if isinstance(self.downloadThread, QtCore.QThread) and self.downloadThread.isRunning() and isinstance(self._atlas_in_progress_, str):
#             print(f"Atlas {self._atlas_in_progress_} is still downloading; please wait")
#             return
#         
#         if self._atlas is None:
#             scipywarn("No atlas has been initialized yet; please call one of:\n self.initAtlas(…)\n self.initAtlasForSpecies(…)\n self.installAtlas(…)\n")
#             
#         return self._atlas
    
    @property
    def localAtlases(self) -> dict:
        if not self.hasBrainGlobeAtlasAPI():
            return dict()
        
        p = self.localAtlasRepository
        
        atlasDirsVers = sorted(map(lambda x: x.name.split("_v"), filter(lambda x: x.is_dir(), p.glob("*"))))
        
        atlasNames, atlasVers = zip(*atlasDirsVers)
        
        uniqueAtlasNames = utilities.unique(atlasNames)
        
        if len(uniqueAtlasNames) < len(atlasNames):
            # there are atlases with several versions stored locally
            
            check_singleton = lambda x: x[0] if len(x) == 1 else tuple(x)
            
            return dict((u, check_singleton(list(map(lambda x: x[1], filter(lambda x: x[0] == u, atlasDirsVers))))) for u in uniqueAtlasNames)
                    
        return dict(atlasDirsVers)
        # return dict(sorted(map(lambda x: x.name.split("_v"), filter(lambda x: x.is_dir(), p.glob("*")))))
    
    @property
    def localAtlasNames(self) -> list[str]:
        return list(self.localAtlases.keys())
    
    @property
    def localAtlasVersions(self) -> list:
        return list(self.localAtlases.values())
    
    @property
    def atlases(self) -> dict:
        """A mapping with all available atlases, of the form name ↦ version"""
        if not self.hasBrainGlobeAtlasAPI():
            return dict()
        
        return self.getAtlasesConfiguration()
    
    @property
    def atlasNames(self) -> list[str]:
        """List of available atlas names.
        Assumes that the local atlas configuration file $HOME/.brainglobe.last_versions.conf
        is up to date
    
        A 'canonical' atlas name is of the form:
        
        name = <identifier>_{<identifier>_}*<resolution>um
        
        identifier = [a-zA-Z0-9]
        
        """
        if not hasBrainGlobeAtlasAPI:
            scipywarn("The 'brainglobe_atlasapi' package is not installed")
            return list()

        atlasConf = self.getAtlasesConfiguration()
        
        return list(atlasConf.keys())
    
    # @Slot(object)
    # def _slot_setAtlas(self, o:object):
    #     self._atlas = o
    #     self._atlas_in_progress_ = None
        
    # @Slot()
    # def finished(self):
    #     # print(f"Atlas {self._atlas_name_} has been downloaded.")
    #     if isinstance(self.downloadThread, QtCore.QThread) and self.downloadThread.isRunning():
    #         self.downloadThread.requestInterruption()
    #     # for signal in self.downloadThread.signals.signals:
    #     #     signal.disconnect()
    #     self.downloadThread.quit()
    #     self.downloadThread.wait()
    #     self.progressDlg.cancel()
    #     self.progressDlg.reset()
    #     self.progressDlg.close()
    #     self.progressDlg = None
    #     self.downloadThread = None
    #     self._atlas_in_progress_ = None
    #     # self._instance = None
        
    def displayAtlases(self, asDict:bool=False, showNeedsUpdate:bool=True,
                       pretty:bool=True, prettier:bool=False) -> pd.DataFrame | dict:
        if not self.hasBrainGlobeAtlasAPI():
            if asDict:
                return dict()
            else:
                return pd.DataFrame()
            
        all_atlases = self.getAtlasesConfiguration()
        local_atlases = self.localAtlases
        
        # vercomp = lambda x,y: atlas_version_str2tuple(x) == atlas_version_str2tuple(y) if isinstance(y, str) else atlas_version_str2tuple(x) in tuple(map(lambda v: atlas_version_str2tuple(v), y)) if isinstance(y, tuple) else False
        
        if prettier: 
            pretty = True
        
        if pretty:
            if showNeedsUpdate:
                names, remote_vers, is_local, local_vers, uptodate = zip(*sorted(sorted(map(lambda k: (k, all_atlases[k], "✓" if k in local_atlases else "", local_atlases.get(k, ""), "✓" if atlas_vercomp(all_atlases[k], local_atlases.get(k, None)) else ""), all_atlases.keys()), key=lambda x: x[0]), key=lambda x: x[2], reverse=True))
            else:
                names, remote_vers, is_local, local_vers = zip(*sorted(sorted(map(lambda k: (k, all_atlases[k], "✓" if k in local_atlases else "", local_atlases.get(k, "")), all_atlases.keys()), key=lambda x: x[0]), key=lambda x: x[2], reverse=True))
        else:
            if showNeedsUpdate:
                names, remote_vers, is_local, local_vers, uptodate = zip(*sorted(sorted(map(lambda k: (k, all_atlases[k], k in local_atlases, local_atlases.get(k, pd.NA)), all_atlases.keys(), atlas_vercomp(all_atlases[k], local_atlases.get(k, None))), key=lambda x: x[0]), key=lambda x: x[2], reverse=True))
            else:
                names, remote_vers, is_local, local_vers = zip(*sorted(sorted(map(lambda k: (k, all_atlases[k], k in local_atlases, local_atlases.get(k, pd.NA)), all_atlases.keys()), key=lambda x: x[0]), key=lambda x: x[2], reverse=True))
            
        if showNeedsUpdate:
            ret = {"Atlas":names,
                "Remote version":remote_vers,
                "Local":is_local,
                "Local version":local_vers,
                "Up to date": uptodate}
        else:
            ret = {"Atlas":names,
                "Remote version":remote_vers,
                "Local":is_local,
                "Local version":local_vers}
        
        if asDict:
            return ret
        
        if prettier:
            r1 = ret.copy()
            r1.pop("Atlas")
            return pd.DataFrame(r1, columns=r1.keys(), index = ret["Atlas"])
        
        return pd.DataFrame(ret, columns=ret.keys())
        
    def updateLocalAtlases(self, force:bool=False):
        """
        TODO - Do NOt use yet!
        """
        pass
#         # from brainglobe_atlasapi.update_atlases import update_atlas
#         progressDlg = QtWidgets.QProgressDialog("Updating local atlases...", "Abort",
#                                                 0, len(self.localAtlasNames), 
#                                                 self.scipyenWindow)
#         
#         progressDlg.setMinimumDuration(1000)
#         progressDlg.canceled.connect(self._slot_breakLoop)
#         
#         workerThread = pgui.LoopWorkerThread(self, self.batchUpdate)
#         workerThread.signals.signal_Progress[int].connect(progressDlg.setValue)
#         workerThread.signals.signal_Result[object].connect(self.batchUpdateReady)
#         workerThread.signals.signal_Finished.connect(progressDlg.reset)
#         workerThread.start()
        
        
    def batchUpdate(self, **kwargs):
        """
        TODO - Do NOt use yet!
        """
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
        """
        TODO - Do NOt use yet!
        """
        self.loopControl["break"] = False
        # try:
        #     ok = bool(obj) == True
        # except:
        #     ok = False
            
    @Slot()
    def _slot_breakLoop(self):
        self.loopControl["break"] = True
        
    def updateLocalAtlas(self, name:str, force:bool=False):
        """
        TODO - Do NOt use yet!
        """
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
         
    @classmethod
    def getBrainGlobeConfiguration(cls, file_path:typing.Optional[pathlib.Path]=None,
                                   asDict:bool = False) -> configparser.ConfigParser | None:
        """Reads the brainglobe configuration from a local file.
        
        WARNING: This is NOT the atlas configuration file (last_versions.conf) !!!
        
        On UN*X platforms, by default, this is file is '~/.config/brainglobe/bg_config.conf'
        
        """
        if not cls.hasBrainGlobeAtlasAPI():
            return
        
        if file_path is None:
            file_path = cls.default_config_file
            
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

    def getAtlasesConfiguration(self, atlases_conf_path:typing.Optional[pathlib.Path]=None,
                         conf_path:typing.Optional[pathlib.Path] = None) -> dict | None:
        """Returns atlas names and versions as a dictionary.
        
        This information is taken from the local atlas configuration file
        $HOME/.brainglobe/last_versions.conf if it exists, and assumed to be up 
        to date.
        
        Failing that, an atlas configuration file is downloaded from the BrainGlobe
        GIN repository https://gin.g-node.org/brainglobe/atlases/raw/master/last_versions.conf
        and saved as the local configuration file specified above.
        
        A diferent local configuraiton file can be specified using 'atlases_conf_path'
        parameter, but the default one (see above) will be used in all other operations 
        by the manager.
        
        By default the method uses the default local BrainGlobe configuration file¹
        ($HOME/.config/brainglobe/bg_config.conf), but an alternative configuration
        file can be specified using the 'conf_path' parameter. WARNING: nevertheless,
        the manager will use the default BrainGlobe configuration file for all other
        operations.
        
        NOTE:
        ¹ do NOT confuse with the atlas configuration file
        
        """
        if not self.hasBrainGlobeAtlasAPI():
            return dict()
        
        if not isinstance(atlases_conf_path, pathlib.Path) or not atlases_conf_path.exists():
            conf = self.getBrainGlobeConfiguration(conf_path)
            atlases_conf_path = pathlib.Path(os.path.join(conf["default_dirs"]["brainglobe_dir"], "last_versions.conf"))
        
        if not atlases_conf_path.exists():
            scipywarn(f"File {atlases_conf_path} does not exist; a copy from the remote GIN site will be downloaded. You will need to call getAtlasesConfiguration method again")
            self.getRemoteAtlasesConfiguration()
        else:
            self._current_atlases_versions_ = self._parseLocalAtlasesConf(atlases_conf_path)
            return self._current_atlases_versions_
        
    def _parseLocalAtlasesConf(self, atlases_conf_path) -> dict:
        atlases_conf = configparser.ConfigParser()
        with open(atlases_conf_path) as atlases_conf_file:
            atlases_conf.read_file(atlases_conf_file)
            
        if atlases_conf.has_section("atlases"):
            # self._current_atlases_versions_ = dict(sorted(((k,v) for k,v in atlases_conf["atlases"].items()), key=lambda x: x[0]))
            return dict(sorted(((k,v) for k,v in atlases_conf["atlases"].items()), key=lambda x: x[0]))
            # return True
        else:
            scipywarn(f"Invalid atlases configuration file {atlases_conf_path}")
            return dict()
            # return False
            
    def getRemoteAtlasesConfiguration(self, file_path:typing.Optional[pathlib.Path]=None):
        """Updates the atlas configuration file containing atlas names and versions.
        
        This information is downloaded from the BrainGlobe GIN repository
        
        https://gin.g-node.org/brainglobe/atlases/raw/master/last_versions.conf
        
        and saved to the local "conf" file (by default this is $HOME/.brainglobe/last_versions.conf)
        
        Optionally, a different destination can be specified using the 'file_path'
        parameter, but the manager will use the default one (specified above)
        for all other operations.
        
        """
        if not self.hasBrainGlobeAtlasAPI():
            return
        
        if file_path is None:
            conf = self.getBrainGlobeConfiguration()
            file_path = os.path.join(conf["default_dirs"]["brainglobe_dir"], "last_versions.conf")
            
        url = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas._remote_url_base.format("last_versions.conf")
        self.netMan = network.ScipyenNetworkManager(progressUIFactory = CancellableQProgressBar)
        self.netMan.sig_resultReady[object].connect(self._slot_lastVersionsConfDownloaded)
        self.netMan.getUrl(url, destination=file_path, replyHandler = None)
        
    def checkAtlasesConfiguration(self):
        """Compares the local atlas configuration file to the remote one.
        The local configuration file is $HOME/.brainglobe/last_versions.conf and
        the remote one is downloaded from the BrainGlobe GIN repository
        https://gin.g-node.org/brainglobe/atlases/raw/master/last_versions.conf
        saved to a temporary file, for comparing. 
        
        The temporary file is removed after the comparison.
        
        """
        if not self.hasBrainGlobeAtlasAPI():
            return
        url = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas._remote_url_base.format("last_versions.conf")
        self.netMan = network.ScipyenNetworkManager(progressUIFactory = CancellableQProgressBar)
        self.netMan.sig_resultReady[object].connect(self._slot_lastVersionsConfTempDownloaded)
        self.netMan.getUrl(url, destination="temp", replyHandler = None)
    
    @Slot(object)
    def _slot_lastVersionsConfTempDownloaded(self, o:typing.Union[str, pathlib.Path, QtCore.QFile]):
        if isinstance(o, str):
            target = pathlib.Path(o)
            
        elif isinstance(o, pathlib.Path):
            target = o
            
        elif isinstance(o, QtCore.QFile):
            target = pathlib.Path(o.fileName())
            
        else:
            raise TypeError(f"In {self.__class__.__name__}._slot_lastVersionsConfDownloaded: expecting a str, a pathlib.Path, or a QtCore.QFile; instead, got {type(o).__name__}")

        atlasConf = self.getAtlasesConfiguration()
        # print(f"atlasConf = {atlasConf}")
        
        tempRemoteConf = self._parseLocalAtlasesConf(target)
        # print(f"tempRemoteConf = {tempRemoteConf}")
        
        self._current_atlases_versions_updated_ = atlasConf == tempRemoteConf
        
        if isinstance(o, QtCore.QFile):
            o.remove()
        
        self._slot_reportLocalDBUpdated()
            
    @Slot()
    def _slot_reportLocalDBUpdated(self):
        from gui.workspacegui import GuiMessages
        if not self._current_atlases_versions_updated_:
            scipywarn("Atlas versions database needs updating. To update, call 'getRemoteAtlasesConfiguration()'")
            ret = GuiMessages.questionMessage_static(self.scipyenWindow,
                                                  f"{self.__class__.__name__}", 
                                                  f"Local database needs updating.\nDo you wish to download it?")
            
            if ret == QtWidgets.QMessageBox.Yes:
                self.getRemoteAtlasesConfiguration()
        else:
            GuiMessages.informationMessage_static(self.scipyenWindow, 
                                                  f"{self.__class__.__name__}", 
                                                  "Local atlases database is up to date")
            
    @Slot(object)
    def _slot_lastVersionsConfDownloaded(self, o:typing.Union[str, pathlib.Path]):
        from gui.workspacegui import GuiMessages
        if isinstance(o, str):
            target = pathlib.Path(o)
            
        elif isinstance(o, pathlib.Path):
            target = o
        else:
            raise TypeError(f"In {self.__class__.__name__}._slot_lastVersionsConfDownloaded: expecting a str or a pathlib.Path; indteag, got {type(o).__name__}")
    
        print(printStyled(f"Latest atlas versions information was downloaded to {target.as_posix()}.", "green", True))
        GuiMessages.informationMessage_static(self.scipyenWindow, 
                                                f"{self.__class__.__name__}", 
                                                f"Latest atlas versions information was downloaded to {target.as_posix()}.")
        
        self._current_atlases_versions_updated_ = True
        
    def getArchiveNameForAtlas(self, entryName:typing.Optional[str]=None) -> str | None:
        atlasPath = self.atlasDir(entryName)
        if isinstance(atlasPath, pathlib.Path):
            return atlasPath.name + ".tar.gz"
        
    @property
    def localAtlasRepository(self) -> pathlib.Path:
        """The local directory where atlases are stored.
        WARNING: The path may not exist in your file system!
        """
        return pathlib.Path(self.getBrainGlobeConfiguration()["default_dirs"]["brainglobe_dir"])
    
    @property
    def localDownloadDirectory(self) -> pathlib.Path:
        """The local directory where temporary atlas archives are downloaded.
        WARNING: The path may not exist in your file system!
        """
        return self.getBrainGlobeConfiguration()["default_dirs"]["interm_download_dir"]
        
    def atlasDir(self, entryName:typing.Optional[str]=None) -> pathlib.Path | None:
        """Get the local atlas directory for a given atlas name.
        WARNING: The returned pathlib Path may NOT exist; this needs to be 
        verified by the caller of this method!
        """
        from gui.itemslistdialog import ItemsListDialog
        if not self.hasBrainGlobeAtlasAPI():
            return

        atlasConf = self.getAtlasesConfiguration()
        
        if entryName not in atlasConf:
            if isinstance(entryName, str):
                keys = list(map(lambda x: entryName in x, atlasConf.keys()))
                if len(keys) == 0:
                    entryName = self.selectAtlasName()
                elif len(keys) > 1:
                    entryName = self.selectAtlasName(keys)
                else:
                    entryName = keys[0]
                    
            if entryName is None:
                entryName = self.selectAtlasName()
                if entryName is None:
                    return
        
        name = f"{entryName}_v{atlasConf[entryName]}"

        return self.localAtlasRepository / name
        
    
    def atlasIsUpdated(self, atlasName:typing.Optional[str] = None) -> bool:
        """
        Returns False if:
        • a local copy of the named atlas does NOT have the latest version available.
        • there is no local copy of the named atlas
        
        Raised an error if there is no atlas with that name available anywhere
        
        NOTE: The latest version available is the one cached in the local brainglobe
        database. You may want to update it first, by calling getRemoteAtlasesConfiguration().
        
        """
        if not self.hasBrainGlobeAtlasAPI():
            return False
        
        a = atlasName if isinstance(atlasName, str) else None
        
        allAtlases = self.getAtlasesConfiguration()
        localAtlases = self.localAtlases
        if atlasName not in self.atlasNames:
            atlasName = self.selectAtlasName(list(allAtlases.keys()))
            
        if atlasName is None:
            if isinstance(a, str):
                raise ValueError(f"No atlas named '{a}' was found")
            else:
                raise ValueError(f"No atlas is available")
        
        if atlasName not in localAtlases:
            return False
            
        remoteVersion = atlas_version_str2tuple(allAtlases[localName])
        localVersion = localAtlases[atlasName]
        
        return atlas_vercomp(remoteVersion, localVersion)
        
    def getLocalAtlasVersion(self, n:typing.Optional[str]=None, 
                              asString:bool=True) -> str | list | None:
        """Returs the versions of the locally installed atlas data.
        This information is derived from the directory name(s) for the
        downloaded atlas data, in the local atlas repository.
        
        ATTENTION: This version, derived as above, may be different from the version
        advertised in the local atlases configuration file (assuming it is uptodate),
        indicating that an update of atlas data may be necessary.
    
        The local atlas repository is located in $HOME/.brainglobe.
    
        """
        from gui.workspacegui import GuiMessages
        if not self.hasBrainGlobeAtlasAPI():
            return
        
        p = self.localAtlasRepository
        
        if not isinstance(n, str) or len(n.strip()) == 0:
            n = self.selectAtlasName()
            
        elif n not in self.atlasNames:
            n = self.selectAtlasName(n)

        dirs = sorted(p.glob(f"*{n}*"))
        
        if len(dirs) > 0:
            vStrings = list(map(lambda x: x.name[len(n):].strip("_v"), dirs))
            if len(vStrings) == 1:
                return vStrings[0] if asString else atlas_version_str2tuple(vString[0])
            return vStrings if asString else list(map(atlas_version_str2tuple, vStrings))
        
        else:
            scipywarn(f"No local atlas named, or with name containing '{n}' was found")
            GuiMessages.informationMessage_static(self.scipyenWindow, 
                                                  f"{self.__class__.__name__}",
                                                  f"No local atlas named, or with name containing '{n}' was found")
            
    def getRemoteAtlasVersion(self, n:typing.Optional[str]=None, 
                              asString:bool=True) -> str |None:
        """Returns the version of the atlas data using the atlases configuration file.
        
        Uses the local atlases configuration file, assumed to to be uptodate.
        
        """
        if not self.hasBrainGlobeAtlasAPI():
            return
            
        if not isinstance(n, str) or len(n.strip()) == 0:
            n = self.selectAtlasName()
            
        elif n not in self.atlasNames:
            n = self.selectAtlasName(n)
            
        return self.atlases[n] if asString else atlas_version_str2tuple(self.atlases[n])
        
# class AtlasDownloadThread(QtCore.QThread):
#     def __init__(self, parent, atlasName:str):
#         """
#         """
#         QtCore.QThread.__init__(self, parent)
#         self.atlasName = atlasName
#         self.signals = pgui.ProgressWorkerSignals()
#         self.result=None
#         
#     def progressUpdater(self, current:int, total:int):
#         self.signals.signal_setMaximum.emit(total)
#         self.signals.signal_Progress.emit(current)
#         
#     def run(self):
#         try:
#             print(f"Downloading {self.atlasName}")
#             self.result = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(self.atlasName, fn_update=self.progressUpdater)
#             self.signals.signal_Result.emit(self.result)
#         except:
#             traceback.print_exc()
#             exctype, value = sys.exc_info()[:2]
#             self.signals.sig_error.emit((exctype, value, traceback.format_exc()))
#             
#         else:
#             self.signals.signal_Finished.emit()
#             
#         finally:
#             self.signals.signal_Finished.emit()
            
    
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
        scipywarn("The 'brainglobe_atlasapi' package is not installed")
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
        ret["atlasName"] = atlas.atlasName
        return ret
    
def atlas_vercomp(x:str, y:typing.Union[str, typing.Tuple[str]]) -> bool:
    """Compares remote atlas versions tring (x) to local atlas version (str, or tuple[str]).
    NOTE: Unlike the equivalent code in brainglobe_atlasapi, this allows to existence,
    locally, of more than one version of the atlas...
    """
    return atlas_version_str2tuple(x) == atlas_version_str2tuple(y) if isinstance(y, str) else atlas_version_str2tuple(x) in tuple(map(lambda v: atlas_version_str2tuple(v), y)) if isinstance(y, tuple) else False
    
def atlas_dirname2name_version(n:str) -> tuple:
    """Breaks up atlas directory name into atlas name and version.
    
       A 'canonical' atlas name is of the form:
        
        name = <identifier>_{<identifier>_}*<resolution>um
        
        identifier = [a-zA-Z0-9]
        
        In addition, an atlas directory name has the version apended:
    
        dirname = <name>_v<maj.min>
        maj = [0-9]+
        min = [0-9]+
    
    Returns:
    --------
    A tuple[str]: (name, version)
    
    """
    return n.split("_v")

def atlas_version_str2tuple(v:str)->tuple | None:
    """Code from brainglobe_atlasapi.bg_atlas._version_tuple_from_str.
    Used here for convenience in case brainglobe_atlasapi is not available.
    """
    return tuple(map(lambda x: int(x), v.split(".")))

def atlas_version_tuple2str(t:tuple[int])-> str | None:
    """Code from brainglobe_atlasapi.bg_atlas._version_str_from_tuple.
    Used here for convenience in case brainglobe_atlasapi is not available.
    """
    try:
        return f"{t[0]}.{t[1]}"
    except:
        traceback.print_exc()
        return

def atlas_name2components(n:str) -> str | tuple:
    """Breaks up an atlas name (`n`) into its identifier and resolution.
    
       A 'canonical' atlas name is of the form:
        
        name = <identifier>_{<identifier>_}*<resolution>um
        
        identifier = [a-zA-Z0-9]
        
    NOTE: atlas version is NOT contained in the atlas name
    """
    # 1. break apart
    parts = n.split("_")
    if len(parts) == 1:
        parts = n.split(" ")
        
        if len(parts) == 1:
            return parts[0]
        
    # 2. locate the resolution
    resolution = list(filter(lambda x: x[1].endswith("um"), enumerate(parts)))
    if len(resolution) == 0:
        return n # no resolution found, return the full name
    
    ndx = resolution[0][0]
    parts.pop(ndx)
    resolutionString = resolution[0][1]
    resolution = float(resolutionString.strip("um"))
    
    # version = list(filter(lambda x: x[1].startswith("v"), enumerate(parts)))
    # if len
    
    return "_".join(parts), resolutionString, resolution
        
# ### END ---- module-level functions

    
