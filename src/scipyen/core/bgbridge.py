# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
Wrapper around BrainGlobe API, with shims
"""
# TODO: 2024-11-25 16:51:43 FIXME
# brainglobe_atlasapi is using requests package for downloading;
# unfortunately, this API is BLOCKING, thus making the UI unresponsive
# and download operation uninterruptible
# TODO: try QNetwork API see what flexibility there is
#
# some preparations:
# 1) figure out where brainglobe downloads stuff (no need to use our own custom locations,
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
# import json
import re
from dataclasses import MISSING
import numpy as np
import pandas as pd
import quantities as pq

import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    # from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip
    # from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

if os.environ["QT_API"] == "pyside6":
    import PySide6
    import qtpy
    qtpy.API = os.environ["QT_API"]
    from PySide6 import (QtCore, QtWidgets, QtGui)
    from PySide6.QtCore import (Signal, Slot, Property)

else:
    import qtpy
    qtpy.API = os.environ["QT_API"]
    from qtpy import (QtCore, QtWidgets, QtGui)
    from qtpy.QtCore import (Signal, Slot, Property)


import configparser # from standard library; Scipyen uses confuse from  pypi
                    # so don't "confuse" them(!)

# import qasync
# from qasync import asyncSlot

from core.prog import scipywarn, print_styled, safewrapper
from core import taxonbridge, utilities
from core import workspacefunctions as wf
from core import scipyen_quantities as scq
# import gui.pictgui as pgui # avoid circular import
from gui.widgets.cancellableqprogressbar import CancellableQProgressBar
from iolib import network
from iolib import pictio as pio

DEFAULT_RAT_BRAIN_ATLAS = "whs_sd_rat_39um"
DEFAULT_MOUSE_BRAIN_ATLAS = "allen_mouse_50um"
DEFAULT_SPECIES = "Rattus norvegicus"

class Structure(collections.UserDict):
    r"""Shim class that will be overwritten below if brainglobe packages are installed"""
    def __getitem__(self, name:str):
        scipywarn(f"The current {self.__class__.__name__} is a shim. You need to install the brainglobe_atlasapi package for full functionality")
        return self.data.get(name, None)

class StructuresDict(collections.UserDict):
    r"""Shim class that will be overwritten below if brainglobe packages are installed"""
    def __init__(self, data:list):
        super().__init__()
        self.acronym_to_id_map = dict()
        self.tree = None
        for k,i in enumerate(data):
            if isinstance(i, Structure):
                sid = i.get("id", k)
                acro = i.get("name", f"Structure Shim {k}")
                self.data[sid] = i
                self.acronym_to_id_map[acro] = sid

    def __getitem__(self, name:str):
        scipywarn(f"The current {self.__class__.__name__} is a shim. You need to install the brainglobe_atlasapi package for full functionality")
        return self.data.get(name, None)

class BrainGlobeAtlas:
    r"""Shim class that will be overwritten below if brainglobe_atlasapi package is installed"""
    def __init__(self, **kwargs):
        self.atlas_name = kwargs.pop("atlas_name", None)

hasBrainGlobe=False
hasBrainGlobeAtlasAPI=False
try:
    import brainglobe_atlasapi
    from brainglobe_atlasapi import BrainGlobeAtlas
    from brainglobe_atlasapi.list_atlases import (get_all_atlases_lastversions,
                                                  get_atlases_lastversions,
                                                  get_downloaded_atlases,
                                                  get_local_atlas_version,
                                                  show_atlases)
    from brainglobe_atlasapi.structure_class import Structure, StructuresDict
    # BGStructure = Structure

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
    r"""Generic, string-based brain structure descriptor.
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
    def __init__(self, *, default:typing.Optional[typing.Union[Structure, str, type(pd.NA), type(MISSING)]] = None):
        # if hasBrainGlobeAtlasAPI and isinstance(default, Structure):
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

    # This one below: instance of                       owner class
    #                 owner class
    #                  ↓                                ↓
    def __get__(self, obj:typing.Optional[object]=None, objtype:typing.Optional[type]=None) -> object:
        if obj is None:
            if isinstance(objtype, type):
                return getattr(objtype, self._name, self._default)

            return self._default

        return getattr(obj, self._name, self._default)

    def __set__(self, obj:object, value:typing.Optional[typing.Union[Structure, str, type(pd.NA), type(MISSING)]] = None):
        if hasBrainGlobeAtlasAPI and isinstance(value, brainglobe_atlasapi.structure_class.Structure):
            setattr(obj, self._name, value)

        elif isinstance(value, str) or value in (None, MISSING, pd.NA):
            setattr(obj, self._name, value)

        else:
            raise TypeError(f"Expecting a non-empty str, pandas NA, or None; instead, got {type(value).__name__}")

class BrainAtlasManager(QtCore.QObject):
    r"""Access for brainglobe atlasapi, with non UI blocking network operations.
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

    default_atlas_name =  'whs_sd_rat_39um'
    default_species = "Rattus norvegicus"

    def __init__(self, parent=None):
        r"""Parameters:
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
        # self._atlas_ = None
        self._current_atlas_ = None
        self._atlas_name_to_initialize_ = None
        self._atlas_in_progress_ = None
        self.downloadThread = None
        self.progressDlg = None
        # self.scipyenWindow = None
        self.loopControl = {"break":False}
        self._netMan_ = None
        self._current_atlases_versions_ = None # cache this
        self._current_atlases_versions_updated_ = True
        self._maxFreeSpaceFraction_ = self.default_free_space_fraction_allowed

        # NOTE: singleton design pattern
        # see traitlets.config.SingletonConfigurable
        # self.__class__._instance = self

    @classmethod
    def _walk_mro(cls) -> typing.Generator[typing.Self, None, None]:
        r"""Walk the cls.mro() for parent classes that are also singletons

        For use in instance()
        """
        # NOTE: Singleton design pattern
        # NOTE: 2025-01-07 12:42:39
        # see traitlets.config.SingletonConfigurable
        for subclass in cls.mro():
            if (
                issubclass(cls, subclass)
                and issubclass(subclass, typing.Self)
                # and issubclass(subclass, SMW)
                # and subclass != SMW
                and subclass != typing.Self
            ):
                yield subclass

    # @classmethod
    # def initialized(cls:typing.Self) -> bool:
    #     # NOTE: Singleton design pattern
    #     return hasattr(cls, "_instance" and isinstance(cls._instance, cls))
    #
    # @classmethod
    # def instance(cls: typing.Self, *args, **kwargs) -> typing.Self:
    #     if cls._instance is None:
    #         inst = cls(*args, **kwargs)
    #         for subclass in cls._walk_mro():
    #             subclass._instance = inst
    #     if hasattr(cls, "_instance") and isinstance(cls._instance, cls):
    #         return cls._instance
    #     else:
    #         raise RuntimeError(f"Incompatible sibling of '{cls.__name__}' is already instantiated as singleton: {type(cls._instance).__name__}")

    @classmethod
    def hasBrainGlobeAtlasAPI(self)->bool:
        from gui.workspacegui import GuiMessages
        if not hasBrainGlobeAtlasAPI:
            # scipyenWindow = wf.getMainScipyenWindow()
            scipywarn("The 'brainglobe_atlasapi' package is not installed")
            GuiMessages.informationMessage_static(title = f"{self.__class__.__name__}",
                                                  text = f"Please install brainglobe_atlasapi package.")
            return False

        return True

    def getAtlasNamesForSpecies(self: typing.Self,
                            taxon:typing.Union[str, taxonbridge.Taxon],
                            localAtlasesOnly: bool = True,
                            ) -> typing.Sequence[str]:

        if not self.hasBrainGlobeAtlasAPI():
            scipywarn("brainglobe is not installed")
            return list()

        atlasNames = self.localAtlasNames if localAtlasesOnly else self.atlasNames

        if len(atlasNames) == 0:
            scipywarn("No atlases are available. Make sure the REQUIRED package brainglobe (or at least brainglobe_atlasapi) is installed.")
            return list()

        if taxonbridge.hasTaxoniq and isinstance(taxon, taxonbridge.Taxon):
            species = taxonbridge.get_nearest_parent_common_name(taxon)

        elif isinstance(taxon, str):
            if len(taxon.strip()) == 0:
                raise ValueError("taxon is an empty string!")

            ret = list(
                map(
                    lambda a: a.atlas_name,
                    filter(
                        lambda a: (isinstance(a, BrainGlobeAtlas)
                                and taxon in a.metadata["species"]),
                            map(
                                lambda s: BrainGlobeAtlas(s, check_latest=False),
                                atlasNames
                                )
                        )
                    )
                )

            if len(ret):
                return ret

            if taxon in [s.lower() for s in taxonbridge.supported_species] + ["mouse", "mice", "rat", "rats"]:
                if taxonbridge.hasTaxoniq:
                    taxonObj = taxonbridge.get_taxon(taxon)

                    if isinstance(taxonObj, taxonbridge.Taxon):
                        species = taxonbridge.get_nearest_parent_common_name(taxonObj)

                    else:
                        species = taxon

                else:
                    # could not retrieve a Taxon object => use taxon parameter as species
                    # and continue with that
                    species = taxon

            else:
                raise ValueError(f"taxon {taxon} is not supported")

        else:
            raise TypeError(f"'taxon' expected to be Taxon or a str; instead got a {type(taxon).__name__}")

        if any(species.lower().startswith(a) or species.lower().endswith(a) for a in ("rat", "rats")):
            species = "rat"

        elif any(species.lower().startswith(a) or species.lower().endswith(a) for a in ("mus", "mouse", "mice")):
            species = "mouse"

        ret = list(
            map(
                lambda a: a.atlas_name,
                filter(
                    lambda x: (
                        isinstance(x, BrainGlobeAtlas)
                        and (
                            species in x.metadata["species"]
                            or species in x.atlas_name
                            )
                        ),
                    map(
                        lambda s: BrainGlobeAtlas(s, check_latest=False),
                        atlasNames
                        )
                    )
                )
            )

        return ret

    def initAtlasForSpecies(self: typing.Self,
                            taxon:typing.Union[str, taxonbridge.Taxon],
                            atlasName:typing.Optional[str]=None,
                            interactive: bool = True,
                            localAtlasesOnly: bool = True) -> typing.Optional[
                                typing.Union[
                                    BrainGlobeAtlas,
                                    typing.Sequence[BrainGlobeAtlas]
                                    ]
                                ]:
        # print(f"{self.__class__.__name__}.initAtlasForSpecies({taxon})")
        if not self.hasBrainGlobeAtlasAPI():
            scipywarn("brainglobe is not installed")
            return

        atlasNames = self.localAtlasNames if localAtlasesOnly else self.atlasNames

        if len(atlasNames) == 0:
            scipywarn("No atlases are available. Make sure the REQUIRED package brainglobe (or at least brainglobe_atlasapi) is installed.")
            return

        if taxonbridge.hasTaxoniq and isinstance(taxon, taxonbridge.Taxon):
            species = taxonbridge.get_nearest_parent_common_name(taxon)

        elif isinstance(taxon, str):
            if len(taxon.strip()) == 0:
                raise ValueError("taxon is an empty string!")

            atlases = list(
                filter(
                    lambda a: (
                        isinstance(a, BrainGlobeAtlas)
                        and (
                            taxon in a.metadata["species"]
                            or taxon in a.atlas_name
                            )
                        ),
                        map(
                            lambda s: BrainGlobeAtlas(s, check_latest=False),
                            atlasNames
                            )
                    )
                )

            if len(atlases):
                names = list(map(lambda a: a.atlas_name, atlases))
                if atlasName in names:
                    return atlases[names.index(atlasName)]
                else:
                    if len(atlases) == 1:
                        return atlases[0]
                    else:
                        if interactive:
                            chosen_atlas_name = self.selectAtlasName(
                                list(
                                    map(
                                        lambda a: a.atlas_name,
                                        atlases
                                        )
                                    ),
                                localAtlasesOnly = localAtlasesOnly,
                                )
                        else:
                            atlas_names_for_species = list(
                                    map(
                                        lambda a: a.atlas_name,
                                        atlases
                                        )
                                    )
                            if self.default_atlas_name in atlas_names_for_species:
                                chosen_atlas_name = self.default_atlas_name

                        if chosen_atlas_name:
                            return BrainGlobeAtlas(chosen_atlas_name,
                                                   check_latest = False)

            if taxon in [
                s.lower() for s in taxonbridge.supported_species
                ] + ["mouse", "mice", "rat", "rats"]:
                if taxonbridge.hasTaxoniq:
                    taxonObj = taxonbridge.get_taxon(taxon)

                    if isinstance(taxonObj, taxonbridge.Taxon):
                        species = taxonbridge.get_nearest_parent_common_name(taxonObj)

                    else:
                        species = taxon

                else:
                    # could not retrieve a Taxon object => use taxon parameter as species
                    # and continue with that
                    species = taxon

            else:
                raise ValueError(f"taxon {taxon} is not supported")

        else:
            raise TypeError(f"'taxon' expected to be Taxon or a str; instead got a {type(taxon).__name__}")

        if (
            any(
                species.lower().startswith(a)
                or species.lower().endswith(a) for a in ("rat", "rats")
                )
            ):
            species = "rat"

        elif any(species.lower().startswith(a) or species.lower().endswith(a) for a in ("mus", "mouse", "mice")):
            species = "mouse"

        atlas_names_for_species = list(
            filter(
                lambda x: (
                    isinstance(x, BrainGlobeAtlas)
                    and (
                        species in x.metadata["species"]
                        or species in x.atlas_name
                        )
                    ),
                map(
                    lambda s: BrainGlobeAtlas(s, check_latest=False),
                    atlasNames
                    )
                )
            )

        # atlas_names_for_species = list(filter(lambda x: species in x, self.atlasNames))

        chosen_atlas = None

        if isinstance(atlasName, str) and len(atlasName.strip()):
            if atlasName not in atlas_names_for_species:
                scipwarn(f"The supplied atlas name {atlasName} is not valid for species {species}")

            else:
                chosen_atlas = atlasName

        else:
            if len(atlas_names_for_species) > 1:
                if interactive:
                    chosen_atlas = self.selectAtlasName(atlas_names_for_species,
                                                        localAtlasesOnly=localAtlasesOnly,
                                                        retNone=True)
                else:
                    if self.default_atlas_name in atlas_names_for_species:
                        chosen_atlas = self.default_atlas_name
                    else:
                        chosen_atlas = atlas_names_for_species[0]

            elif len(atlas_names_for_species) == 1:
                chosen_atlas = atlas_names_for_species[0]

            else:
                if interactive:
                    chosen_atlas = self.selectAtlasName(species,
                                                        localAtlasesOnly=localAtlasesOnly,
                                                        retNone=True)

        ret = ""

        if chosen_atlas is None:
            if species == "mouse":
                default_atlas = DEFAULT_MOUSE_BRAIN_ATLAS

            elif species == "rat":
                default_atlas = DEFAULT_RAT_BRAIN_ATLAS

            else:
                return

            if len(atlas_names_for_species) == 0:
                scipywarn(f"No brain atlas for species {species} is found")
                return

            elif len(atlas_names_for_species) > 1:
                if default_atlas in atlas_names_for_species:
                    scipywarn(f"There is more than one brain atlas available. The default one ({default_atlas}) will be used")
                    ret = default_atlas
                else:
                    scipywarn(f"There is more than one brain atlas available, but the default one ({default_atlas}) is not among them. The first available one ({atlas_names_for_species[0]}) will be used")
                    ret = atlas_names_for_species[0]

        else:
            ret = chosen_atlas

        self._current_atlas_ = BrainGlobeAtlas(ret, check_latest=False)

        return self._current_atlas_

    def _parse_size(self, s:str) -> int:
        r"""Parses the archive size from the HTML file for a given atlas archive.
        Code taken from brainglobe_atlasapi
        """
        import re
        search_result = re.search(r"([0-9]+\.[0-9] [MGK]B)|([0-9]+ [MGK]B)", s)
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
        r"""Tests downloading and extracting an atlas archive.
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
        if not self._netMan_:
            self._netMan_ = network.ScipyenNetworkManager(progressUIFactory = CancellableQProgressBar)
        self._netMan_.sig_networkError[object].connect(self._slot_networkError)
        self._netMan_.sig_resultReady[object].connect(self._slot_extractAtlasArchive)
        self._netMan_.sig_finished.connect(self.slot_networkOperationFinished)

        handle = functools.partial(self._getArchiveSizeAndDownload,
                                   targetDir = self.localDownloadDirectory,
                                   url = url)

        self._netMan_.getUrl(url1, destination=None, replyHandler=handle)

    @Slot(object)
    def _slot_networkError(self, url_msg:tuple[str]):
        from gui.workspacegui import GuiMessages
        scipyenWindow = wf.getMainScipyenWindow()
        print(f"{self.__class__.__name__}._slot_networkError: url_msg = {url_msg}")
        GuiMessages.criticalMessage_static(scipyenWindow,
                                           f"{self.__class__.__name__}",
                                           f"Error from {url_msg[0]}:\n{url_msg[1]}")

    def _extractAtlasArchive(self, target:typing.Union[str, pathlib.Path]) -> bool:
        import tarfile
        print(f"{self.__class__.__name__}._extractAtlasArchive: target = {target}")
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
                raise RuntimeError(f"In {self.__class__.__name__}._extractAtlasArchive: File object {path} does not exist!")

            tar = tarfile.open(path)
            try:
                tar.extractall(path = targetDir)
                tar.close()
                target.unlink()
                return True
            except:
                traceback.print_exc()
                return False

        return False

    @Slot(object)
    def _slot_extractAtlasArchive(self, target:typing.Union[str, pathlib.Path]) -> None:
        ret = self._extractAtlasArchive(target)

    @Slot(object)
    def _slot_extractAtlasArchiveAndInit(self, target:typing.Union[str, pathlib.Path]) -> None:
        # print(f"{self.__class__.__name__}._slot_extractAtlasArchiveAndInit: target = {target}")
        ret = self._extractAtlasArchive(target)
        if ret and self._atlas_name_to_initialize_ is not None:
            # self._atlas_ = BrainGlobeAtlas(self._atlas_name_to_initialize_, check_latest=False)
            self._current_atlas_ = BrainGlobeAtlas(self._atlas_name_to_initialize_, check_latest=False)
            print(f"{print_styled(f'{self._atlas_name_to_initialize_}', 'green')} was initialized")
            self._atlas_name_to_initialize_ = None

    def initAtlas(self, nameOrSpecies: typing.Optional[typing.Union[str, taxonbridge.Taxon]] = None,
                  localAtlasesOnly: bool = True,
                  interactive: bool = True
                  # download: bool = False,
                  ) -> BrainGlobeAtlas | None:
        from gui.workspacegui import GuiMessages
        # print(f"{self.__class__.__name__}.initAtlas({name})")
        if not self.hasBrainGlobeAtlasAPI():
            scipywarn("BraingGlobe is not installed; brain atlases are not available")
            return

        if localAtlasesOnly:
            atlasNames = self.localAtlasNames
        else:
            atlasNames = self.atlasNames

        species = None

        if isinstance(nameOrSpecies, taxonbridge.Taxon):
            species = nameOrSpecies

        elif isinstance(nameOrSpecies, str):
            availableSpecies = self.getAvailableSpecies()
            if (
                nameOrSpecies in availableSpecies
                or any(nameOrSpecies.lower() in s.lower() for s in availableSpecies)
                or nameOrSpecies in ("rat", "rats", "mouse", "mice")
                ):
                species = nameOrSpecies

        if species:
            try:
                return self.initAtlasForSpecies(
                    species,
                    interactive=interactive,
                    localAtlasesOnly=localAtlasesOnly
                    )
            except:
                traceback.print_exc()

        else:
            name = nameOrSpecies

            if (
                name is None
                or (
                    isinstance(name, str) and (
                        len(name.strip()) == 0
                        or name not in atlasNames
                        )
                    )
                ):

                name = self.selectAtlasName(localAtlasesOnly = localAtlasesOnly)

                if name is None:
                    return
                    # name = self.default_atlas_name

            if name not in self.localAtlasNames:
                if interactive:
                    GuiMessages.informationMessage_static(
                        title = f"Atlas {name}:",
                        text  = "\n".join(
                                [
                                    f"Atlas {name} must be installed manually.",
                                    "Open a terminal, run 'scipyact' to activate Scipyen's environment,"
                                    f"then run 'brainglobe install -a {name}' to install the atlas"
                                ]
                            )
                        )
                return
                # if download:
                #     scipywarn(f"The atlas {name} will be available as the 'atlas' attribute once donwloaded and initialized")
                #     self.downloadAtlas(name, True)
                # else:
                #     scipywarn(f"The atlas {name} must be downloaded manually")
                #     return
            else:
                # TODO 2024-11-24 21:23:14
                # make 'check_latest' below a Scipyen configurable variable
                # (not Qt configurable)
                self._current_atlas_ = BrainGlobeAtlas(name, check_latest=False)
                # self._atlas_ = BrainGlobeAtlas(name, check_latest=download)
                self._atlas_name_to_initialize_ = None

                return self._current_atlas_

    def showAtlases(self, show_local_path:bool=False, toConsole:bool=True,
                    table_width:int=80) -> typing.Optional[pd.DataFrame]:
        r"""Shows atlases using brainglobe_atlasapi.
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
        if not self._netMan_:
            self._netMan_ = network.ScipyenNetworkManager(progressUIFactory = CancellableQProgressBar)
        self._netMan_.sig_resultReady[object].connect(self._slot_checkGINReady)
        self._netMan_.sig_finished.connect(self.slot_networkOperationFinished)
        self._netMan_.checkUrl(url)

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
        errorMsg = self._netMan_.networkErorName
        scipywarn(f"Got {errorMsg} from {result[1]}" )
        if self._netMan_.receivers(self._netMan_.sig_resultReady) > 0:
            self._netMan_.sig_resultReady.disconnect()

    @Slot()
    def cancelDownload(self):
        try:
            self._netMan_.networkReply.abort()
            self._netMan_.networkReply.close()
        except:
            traceback.print_exc()

    def downloadAtlas(self, name:typing.Optional[str], initAtlas:bool=False) -> None:
        r"""Downloads an atlas data from the BrainGlobe GIN repository

        https://gin.g-node.org/brainglobe/atlases/raw/master/

        If the atlas data already exists locally, it will be overwritten.

        By default, atlas data is stored in the $HOME/.brainglobe directory
        (on UNIX operating systems).

        """
        frame_records = inspect.getouterframes(inspect.currentframe())

        if "console" in frame_records[1].frame.f_globals:
            dlgParent = frame_records[1].frame.f_globals["console"]
        else:
            scipyenWindow = wf.getMainScipyenWindow()
            dlgParent = scipyenWindow

        if not self.hasBrainGlobeAtlasAPI():
            return

        slot = self._slot_extractAtlasArchiveAndInit if initAtlas else self._slot_extractAtlasArchive

        self._atlas_name_to_initialize_ = name if initAtlas else None

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

        if not self._netMan_:
            self._netMan_ = network.ScipyenNetworkManager(progressUIFactory = CancellableQProgressBar)
        self._netMan_.sig_resultReady[object].connect(self._slot_extractAtlasArchive)

        handle = functools.partial(self._getArchiveSizeAndDownload,
                                   targetDir = self.localDownloadDirectory,
                                   url = url)

        self._netMan_.getUrl(url1, destination=None, replyHandler=handle)


    @Slot()
    def slot_networkOperationFinished(self):
        if isinstance(self._netMan_, network.ScipyenNetworkManager):
            color = "yellow" if self._netMan_.networkError else "green"
            print(print_styled(f"{self.__class__.__name__} network operation finished with {self._netMan_.networkErrorName}", color, True))

    def selectAtlasName(
        self: typing.Self,
        choices: typing.Optional[
            typing.Union[
                typing.Sequence[str],
                str
                ]
            ] = None,
        localAtlasesOnly: bool = True,
        retNone: bool = False,
        dlgTitle: typing.Optional[str] = None,
        dlgParent: typing.Optional[QtWidgets.QWidget] = None
        ) -> str | None:
        from gui.itemslistdialog import ItemsListDialog

        if not self.hasBrainGlobeAtlasAPI():
            return

        atlasNames = self.localAtlasNames if localAtlasesOnly else self.atlasNames

        if isinstance(choices, (tuple, list)):
            if all(isinstance(v, str) for v in choices):
                names = list(
                    itertools.chain.from_iterable(
                        map(
                            lambda c: filter(
                                lambda x: c in x,
                                atlasNames
                                ),
                            choices
                            )
                        )
                    )

                if len(names) == 0:
                    scipywarn("No valid atlas names were supplied")
                    names = atlasNames

        elif isinstance(choices, str) and len(choices.strip()):
            names = list(
                        filter(
                            lambda x: choices in x,
                            atlasNames
                            )
                        )

            if len(names) == 0:
                scipywarn("No valid atlas names were supplied")
                names = atlasNames

        else:
            names = atlasNames

        if len(names) == 0:
            if retNone:
                return
            else:
                return str()

        if not isinstance(dlgTitle, str) or len(dlgTitle.strip()) == 0:
            where = f" local " if localAtlasesOnly else " "
            dlgTitle = f"Choose from available{where}atlas names:"

        preSelected = (
        self.default_atlas_name if self.default_atlas_name in names else None
        )

        scipyenWindow = wf.getMainScipyenWindow()
        if dlgParent is None:
            dlgParent = scipyenWindow

        dlg = ItemsListDialog(parent = dlgParent, itemsList = names,
                                title = dlgTitle, preSelected = preSelected)
        dlg.adjustSize()
        a = dlg.exec_()

        if a == QtWidgets.QDialog.Accepted:
            names = dlg.selectedItemsText
            if len(names):
                return names[0]

#     def uninstallAtlas(self, name:str):
#         """
#         TODO - Do NOT use yet!
#         """
#         from gui.itemslistdialog import ItemsListDialog
#
#         if len(self.localAtlasNames) == 0:
#             print("No atlas is installed locally")
#             return
#
#         if name not in self.localAtlasNames:
#             dlg = ItemsListDialog(parent = self.scipyenWindow, itemsList = self.localAtlasNames,
#                                   title = f"Choose atlas:")
#             a = dlg.exec_()
#
#             if a == QtWidgets.QDialog.Accepted:
#                 names = dlg.selectedItemsText
#                 if len(names):
#                     name = names[0]
#
#         # self._downloadAtlas(name, setOwn=False)

    def getAtlasStructure(self, name:str,
                        acro:bool=False,
                        cutoff = 0.5,
                        maxfound = 10,
                        ):
        r"""See get_atlas_structure(…) module-level function"""
        if self._current_atlas_ is None:
            raise RuntimeError("no atlas has been initialized yet")

        return get_atlas_structure(name, self._current_atlas_)

    @property
    def atlas(self):
        r"""Last initialized atlas
        """
        if self._current_atlas_ is None:
            if self._atlas_name_to_initialize_ is None:
                self._current_atlas_ = self.initAtlas()
                # scipywarn("No atlas has been initialized yet; please call one of:\n self.initAtlas(…)\n self.initAtlasForSpecies(…)\n self.installAtlas(…)\n")
            else:
                self._current_atlas_ = BrainGlobeAtlas(self._atlas_name_to_initialize_, check_latest=False)

        return self._current_atlas_

    @property
    def localAtlases(self) -> dict:
        if not self.hasBrainGlobeAtlasAPI():
            return dict()

        return self.getAtlasesConfiguration(localAtlasesOnly = True)

        # p = self.localAtlasRepository
        # p_glob = p.glob("*")
        #
        # atlasesConfig = self.getAtlasesConfiguration()
        # if len(atlasesConfig) == 0:
        #     scipywarn("No local atlases configuration was found. Please use brainglobe executable to setup the local repository")
        #     return dict()
        #
        # atlasDirsVers = sorted(
        #     filter(
        #         lambda x: x[0] in atlasesConfig,
        #         map(
        #             lambda x: x if len(x)==2 else [x[0], ""],
        #             map(
        #                 lambda x: x.name.split("_v"),
        #                 filter(
        #                     lambda x: x.is_dir(), p_glob
        #                     )
        #                 )
        #             )
        #         )
        #     )
        #
        # atlasNames, atlasVers = zip(*atlasDirsVers)
        #
        # uniqueAtlasNames = utilities.unique(atlasNames)
        #
        # if len(uniqueAtlasNames) < len(atlasNames):
        #     # there are atlases with several versions stored locally
        #
        #     check_singleton = lambda x: x[0] if len(x) == 1 else tuple(x)
        #
        #     return dict(
        #             (
        #                 u,
        #                 check_singleton(
        #                     list(
        #                         map(lambda x: x[1],
        #                             filter(
        #                                 lambda x: x[0] == u,
        #                                 atlasDirsVers
        #                                 )
        #                             )
        #                         )
        #                     )
        #             ) for u in uniqueAtlasNames
        #         )
        #
        # return dict(atlasDirsVers)
        # return dict(sorted(map(lambda x: x.name.split("_v"), filter(lambda x: x.is_dir(), p.glob("*")))))

    @property
    def localAtlasNames(self) -> list[str]:
        return list(self.localAtlases.keys())

    @property
    def localAtlasVersions(self) -> list:
        return list(self.localAtlases.values())

    @property
    def maxFileSystemFraction(self: typing.Self) -> float:
        return self._maxFreeSpaceFraction_

    @maxFileSystemFraction.setter
    def maxFileSystemFraction(self: typing.Self, val: float):
        if isinstance(val, float) and maxFileSystemFraction >= 0.1 and val <= 0.9:
            self._maxFreeSpaceFraction_ = val
        else:
            self._maxFreeSpaceFraction_ = self.default_free_space_fraction_allowed



    @property
    def atlases(self) -> dict:
        r"""A mapping with all available atlases, of the form name ↦ version"""
        if not self.hasBrainGlobeAtlasAPI():
            return dict()

        return self.getAtlasesConfiguration()

    @property
    def atlasNames(self) -> list[str]:
        r"""List of available atlas names.
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

        if atlasConf:
            return list(atlasConf.keys())
        else:
            return list()

    def getAvailableSpecies(self: typing.Self, localAtlasesOnly: bool = True) -> tuple:
        conf = self.getBrainGlobeConfiguration()
        if not conf:
            scipywarn("No brainglobe configuration file was found; is brainglobe installed?")
            return

        if localAtlasesOnly:
            atlases_dir = conf["default_dirs"]["brainglobe_dir"]

            _get_species = lambda i: get_species_for_local_atlas(
                pathlib.Path(atlases_dir) / f"{i[0]}_v{i[1]}" / "metadata.json"
                )

            return set(
                        map(
                            lambda s: s[0],
                            filter(
                                # lambda s: isinstance(s, str) and len(s)>0,
                                lambda s: len(s)>0,
                                map(
                                    lambda i: _get_species(i),
                                    self.localAtlases.items()
                                    )
                                )
                            )
                        )

        else:
            # CAUTION: 2026-02-17 21:27:45
            # slow, because it constructs a BrainGlobeAtlas for each atlas, and
            # this MAY involve downloading a large file !
            atlasNames = self.atlasNames

            atlases = list(
                filter(
                    lambda a: isinstance(a, BrainGlobeAtlas),
                        map(
                            lambda s: BrainGlobeAtlas(s, check_latest = False),
                            # lambda s: self.initAtlas(s, localAtlasesOnly,
                            #                         interactive = False),
                            atlasNames
                            )
                    )
                )

            species = set(
                map(
                    lambda a: a.metadata["species"],
                    list(
                        filter(
                            lambda a: isinstance(a, BrainGlobeAtlas),
                                map(
                                    lambda s: BrainGlobeAtlas(s, check_latest = False),
                                    atlasNames
                                    )
                            )
                        )
                    )
                )

            return species

    # @Slot(object)
    # def _slot_setAtlas(self, o:object):
    #     self._atlas_ = o
    #     self._atlas_in_progress_ = None

    # @Slot()
    # def finished(self):
    #     # print(f"Atlas {self._atlas_name_to_initialize_} has been downloaded.")
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

    @Slot()
    def _slot_breakLoop(self):
        self.loopControl["break"] = True

    @classmethod
    def getBrainGlobeConfiguration(cls, file_path:typing.Optional[pathlib.Path]=None,
                                   asDict:bool = False) -> configparser.ConfigParser | None:
        r"""Reads the brainglobe configuration from a local file.

        WARNING: This is NOT the atlas configuration file (last_versions.conf) !!!

        On UN*X platforms, by default, this is file is '~/.config/brainglobe/bg_config.conf'

        """
        if not cls.hasBrainGlobeAtlasAPI():
            return

        if file_path is None:
            file_path = cls.default_config_file

        if not isinstance(file_path, pathlib.Path) or not file_path.exists():
            brainglobe_atlasapi.config.write_default_config()

            # return

        conf_object = configparser.ConfigParser()
        with open(file_path) as file_object:
            conf_object.read_file(file_object)

        if not conf_object.has_section("default_dirs"):
            raise RuntimeError(f"The {file_path} is an invalid brainglobe configuration file; please provide a valid file or reinstall brainglobe package")

        if asDict:
            return dict((s, dict(conf_object[s])) for s in conf_object.sections())

        return conf_object

    def getAtlasesConfiguration(self: typing.Self,
                atlases_conf_file: typing.Optional[pathlib.Path]=None,
                conf_path: typing.Optional[pathlib.Path] = None,
                localAtlasesOnly: bool = False,
                ) -> dict:
        r"""Returns atlas names and versions as a dictionary.

        This information is taken from the local atlas configuration file
        $HOME/.brainglobe/last_versions.conf if it exists, and assumed to be up
        to date.

        A diferent local configuration file can be specified using 'atlases_conf_path'
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
        # FIXME: 2026-02-13 13:00:38
        # there are issues with downloading atlases programmatically,
        # probably on the remote site.
        # Until I figure out what the problem is, just return an empty dict()
        # Failing that, an atlas configuration file is downloaded from the BrainGlobe
        # GIN repository https://gin.g-node.org/brainglobe/atlases/raw/master/last_versions.conf
        # and saved as the local configuration file specified above.
        # atlases_conf_file = None
        if not self.hasBrainGlobeAtlasAPI():
            return dict()

        if not isinstance(atlases_conf_file, pathlib.Path) or not atlases_conf_file.exists():
            conf = self.getBrainGlobeConfiguration(conf_path)
            if conf:
                atlases_dir = conf["default_dirs"]["brainglobe_dir"]
                atlases_conf_file = pathlib.Path(os.path.join(conf["default_dirs"]["brainglobe_dir"], "last_versions.conf"))
            else:
                scipywarn("No brainglobe configuration file was found; is brainglobe installed?")
                return dict()

        if not isinstance(self._current_atlases_versions_, dict) or len(self._current_atlases_versions_) == 0:
            self._current_atlases_versions_ = self._parseLocalAtlasesConf(atlases_conf_file)

        if localAtlasesOnly:
            return dict(filter(lambda i: (pathlib.Path(atlases_dir) / f"{i[0]}_v{i[1]}").is_dir(), self._current_atlases_versions_.items()))

        return self._current_atlases_versions_

    def _parseLocalAtlasesConf(self, atlases_conf_file) -> dict:
        atlases_conf = configparser.ConfigParser()
        with open(atlases_conf_file) as conf_file:
            atlases_conf.read_file(conf_file)

        if atlases_conf.has_section("atlases"):
            # self._current_atlases_versions_ = dict(sorted(((k,v) for k,v in atlases_conf["atlases"].items()), key=lambda x: x[0]))
            return dict(sorted(((k,v) for k,v in atlases_conf["atlases"].items()), key=lambda x: x[0]))
            # return True
        else:
            scipywarn(f"Invalid atlases configuration file {atlases_conf_file}")
            return dict()
            # return False

    def getRemoteAtlasesConfiguration(self, file_path:typing.Optional[pathlib.Path]=None):
        r"""Updates the atlas configuration file containing atlas names and versions.

        This information is downloaded from the BrainGlobe GIN repository

        https://gin.g-node.org/brainglobe/atlases/raw/master/last_versions.conf

        and saved to the local "conf" file (by default this is $HOME/.brainglobe/last_versions.conf)

        Optionally, a different destination can be specified using the 'file_path'
        parameter, but the manager will use the default one (specified above)
        for all other operations.

        CAUTION: this relies on a good connection to the remote gin node.

        """
        if not self.hasBrainGlobeAtlasAPI():
            return

        if file_path is None:
            conf = self.getBrainGlobeConfiguration()
            if conf:
                file_path = os.path.join(conf["default_dirs"]["brainglobe_dir"], "last_versions.conf")

        url = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas._remote_url_base.format("last_versions.conf")
        if not self._netMan_:
            self._netMan_ = network.ScipyenNetworkManager(progressUIFactory = CancellableQProgressBar, timeout_ms=120000)
        self._netMan_.sig_resultReady[object].connect(self._slot_lastVersionsConfDownloaded)
        self._netMan_.getUrl(url, destination=file_path, replyHandler = None)

    def checkAtlasesConfiguration(self):
        r"""Compares the local atlas configuration file to the remote one.
        The local configuration file is $HOME/.brainglobe/last_versions.conf and
        the remote one is downloaded from the BrainGlobe GIN repository
        https://gin.g-node.org/brainglobe/atlases/raw/master/last_versions.conf
        saved to a temporary file, for comparing.

        The temporary file is removed after the comparison.

        CAUTION: this relies on a good connection to the remote gin node.

        """
        if not self.hasBrainGlobeAtlasAPI():
            return
        url = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas._remote_url_base.format("last_versions.conf")
        if not self._netMan_:
            self._netMan_ = network.ScipyenNetworkManager(progressUIFactory = CancellableQProgressBar)
        self._netMan_.sig_resultReady[object].connect(self._slot_lastVersionsConfTempDownloaded)
        self._netMan_.getUrl(url, destination="temp", replyHandler = None)

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
        scipyenWindow = wf.getMainScipyenWindow()
        if not self._current_atlases_versions_updated_:
            scipywarn("Atlas versions database needs updating. To update, call 'getRemoteAtlasesConfiguration()'")
            ret = GuiMessages.questionMessage_static(scipyenWindow,
                                                  f"{self.__class__.__name__}",
                                                  f"Local database needs updating.\nDo you wish to download it?")

            if ret == QtWidgets.QMessageBox.Yes:
                self.getRemoteAtlasesConfiguration()
        else:
            GuiMessages.informationMessage_static(scipyenWindow,
                                                  f"{self.__class__.__name__}",
                                                  "Local atlases database is up to date")

    @Slot(object)
    def _slot_lastVersionsConfDownloaded(self, o:typing.Union[str, pathlib.Path]):
        from gui.workspacegui import GuiMessages
        scipyenWindow = wf.getMainScipyenWindow()
        if isinstance(o, str):
            target = pathlib.Path(o)

        elif isinstance(o, pathlib.Path):
            target = o
        else:
            raise TypeError(f"In {self.__class__.__name__}._slot_lastVersionsConfDownloaded: expecting a str or a pathlib.Path; indteag, got {type(o).__name__}")

        print(print_styled(f"Latest atlas versions information was downloaded to {target.as_posix()}.", "green", True))
        GuiMessages.informationMessage_static(scipyenWindow,
                                                f"{self.__class__.__name__}",
                                                f"Latest atlas versions information was downloaded to {target.as_posix()}.")

        self._current_atlases_versions_updated_ = True

    def getArchiveNameForAtlas(self, entryName:typing.Optional[str]=None) -> str | None:
        atlasPath = self.atlasDir(entryName)
        if isinstance(atlasPath, pathlib.Path):
            return atlasPath.name + ".tar.gz"

    @property
    def localAtlasRepository(self) -> pathlib.Path:
        r"""The local directory where atlases are stored.
        WARNING: The path may not exist in your file system!
        """
        return pathlib.Path(self.getBrainGlobeConfiguration()["default_dirs"]["brainglobe_dir"])

    @property
    def localDownloadDirectory(self) -> pathlib.Path:
        r"""The local directory where temporary atlas archives are downloaded.
        WARNING: The path may not exist in your file system!
        """
        return self.getBrainGlobeConfiguration()["default_dirs"]["interm_download_dir"]

    def atlasDir(self, entryName:typing.Optional[str]=None) -> pathlib.Path | None:
        r"""Get the local atlas directory for a given atlas name.
        WARNING: The returned pathlib Path may NOT exist; this needs to be
        verified by the caller of this method!
        """
        # from gui.itemslistdialog import ItemsListDialog
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
        r"""
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
        r"""Returs the versions of the locally installed atlas data.
        This information is derived from the directory name(s) for the
        downloaded atlas data, in the local atlas repository.

        ATTENTION: This version, derived as above, may be different from the version
        advertised in the local atlases configuration file (assuming it is uptodate),
        indicating that an update of atlas data may be necessary.

        The local atlas repository is located in $HOME/.brainglobe.

        """
        from gui.workspacegui import GuiMessages
        scipyenWindow = wf.getMainScipyenWindow()
        if not self.hasBrainGlobeAtlasAPI():
            return

        p = self.localAtlasRepository

        if not isinstance(n, str) or len(n.strip()) == 0:
            n = self.selectAtlasName(localAtlasesOnly=True)

        elif n not in self.atlasNames:
            n = self.selectAtlasName(n, localAtlasesOnly=True)

        dirs = sorted(p.glob(f"*{n}*"))

        if len(dirs) > 0:
            vStrings = list(map(lambda x: x.name[len(n):].strip("_v"), dirs))
            if len(vStrings) == 1:
                return vStrings[0] if asString else atlas_version_str2tuple(vString[0])
            return vStrings if asString else list(map(atlas_version_str2tuple, vStrings))

        else:
            scipywarn(f"No local atlas named, or with name containing '{n}' was found")
            GuiMessages.informationMessage_static(scipyenWindow,
                                                  f"{self.__class__.__name__}",
                                                  f"No local atlas named, or with name containing '{n}' was found")

    def getRemoteAtlasVersion(self, n:typing.Optional[str]=None,
                              asString:bool=True) -> str |None:
        r"""Returns the version of the atlas data using the atlases configuration file.

        Uses the local atlases configuration file, assumed to to be uptodate.

        """
        if not self.hasBrainGlobeAtlasAPI():
            return

        if not isinstance(n, str) or len(n.strip()) == 0:
            n = self.selectAtlasName()

        elif n not in self.atlasNames:
            n = self.selectAtlasName(n)

        return self.atlases[n] if asString else atlas_version_str2tuple(self.atlases[n])

# ### BEGIN ---- module-level functions

def get_atlas_structure(name:str, atlas:BrainGlobeAtlas,
                        acro:bool=False,
                        cutoff = 0.5,
                        maxfound = 10,
                        ) -> dict | None:
    r"""Best-guess for an atlas structure corresponding to a named brain region.

    The function tries to match the brain region name given in 'name' parameter
    to the 'name' or 'acronym' attribute of the structures in the atlas — depending
    in the value of the 'acro' parameters.

    Matching is performed by difflib.get_close_matches. When matches are found,
    the "best" matching structure is returned.


    Parameters:
    ===========

    :name:   common name of the brain region. Case sensitive (sometimes)¹

    :atlas:  a brainglobe_atlasapi.BrainGlobeAtlas instance

    :acro:   flag indicating is the search for matches will take place primarily
            on structure acronyms (``True``) or names (``False``)
            Default is ``False``, meaning that the function will first try to
            match 'name' against the structure names, then (and only if no
            matches are found) against the structure acronyms in the atlas.

    :cutoff: the 'cutoff' parameter for the 'difflib.get_close_matches'
            function; default (here) is 0.5

    :maxfound: the maximum number of matches to be returned (passed directly to
            difflib.get_close_matches function). Default is 10

    Returns:
    ========

    A dict or ``None``

    See also: difflib.get_close_matches in Python standard library

    WARNING: This may yield surprising results, so it is best avoid ambiguities
        in the 'name' parameter.

    ¹Case sensitivity does not always work as you may think, see examples below.

    Some examples using the Waxholm Space Atlas of the Sprague Dawley Rat Brain
        ('whs-sd-atlas')
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

    if not isinstance(name, str) or len(name.strip()) == 0:
        raise TypeError(f"Expecting a non-empty string; got {name} instead")

    # if len(name.strip()) == 0:
    #     raise ValueError("Expecting a non-empty string")

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
        ret["atlasName"] = atlas.atlas_name
        return ret

def atlas_vercomp(x:str, y:typing.Union[str, typing.Tuple[str]]) -> bool:
    r"""Compares remote atlas versions tring (x) to local atlas version (str, or tuple[str]).
    NOTE: Unlike the equivalent code in brainglobe_atlasapi, this allows to existence,
    locally, of more than one version of the atlas...
    """
    return atlas_version_str2tuple(x) == atlas_version_str2tuple(y) if isinstance(y, str) else atlas_version_str2tuple(x) in tuple(map(lambda v: atlas_version_str2tuple(v), y)) if isinstance(y, tuple) else False

def atlas_dirname2name_version(n:str) -> tuple:
    r"""Breaks up atlas directory name into atlas name and version.

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
    r"""Code from brainglobe_atlasapi.bg_atlas._version_tuple_from_str.
    Used here for convenience in case brainglobe_atlasapi is not available.
    """
    return tuple(map(lambda x: int(x), v.split(".")))

def atlas_version_tuple2str(t:tuple[int])-> str | None:
    r"""Code from brainglobe_atlasapi.bg_atlas._version_str_from_tuple.
    Used here for convenience in case brainglobe_atlasapi is not available.
    """
    try:
        return f"{t[0]}.{t[1]}"
    except:
        traceback.print_exc()
        return

def atlas_name2components(n:str) -> str | tuple:
    r"""Breaks up an atlas name (`n`) into its identifier and resolution.

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

def get_species_for_local_atlas(atlas_metadata_json_file_name) -> str | None:
    r"""Retrieve the species from an atlas metadata.json file.

Bypassess the construction of an atlas object.

Returns:
========
    A list containing the species name of the corresponding atlas.

.. attention::

    Fails (returns and empty list) if the named file does not exist, or is not
a valid atlas ``metadata.json`` file.

.. warning::

    Does not verify is the file conforms to the atlas metadata.json structure.

    *I.e.*, the funcion may be "fooled" by passing a text file containing a
    'bogus' species definition.


"""
    pattern = r'"species":\s*"(.*?)"'
    with open(atlas_metadata_json_file_name, "rt", encoding="utf-8") as json_file:
        return re.findall(pattern, json_file.read())



def get_hash(s: typing.Union[Structure, StructuresDict]) -> int:
    items = tuple(map(lambda i: (i[0], tuple(i[1]) if isinstance(i[1], list) else get_hash(i[1]) if isinstance(i[1], Structure) else i[1])))
    return hash(items)

# ### END ---- module-level functions

# manager = BrainAtlasManager()
#
# available_species = manager.getAvailableSpecies()



