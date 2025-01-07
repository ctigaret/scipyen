# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import sys, os, typing, pathlib
from enum import Enum, IntEnum
from qtpy import QtCore
from qtpy.QtCore import Signal, Slot, Property

# from core.datatypes import TypeEnum

class NetworkMountOption(IntEnum):pass
NetworkMountOption = IntEnum("NetworkMountOption",
                             ["LowSideEffectsOptimizations",
                              "MediumSideEffectsOptimizations",
                              "StrongSideEffectsOptimizations",
                              "DirWatchDontAddWatches",
                              "SymlinkPathsUseCache"])
                             
class NetworkMountsType(IntEnum):pass
NetworkMountsType = IntEnum("NetworkMountsType",
                            ["NfsPaths",
                             "SmbPaths",
                             "SymlinkDirectory",
                             "SymlinkToNetworkMount",
                             "Any"])

NM = typing.TypeVar("NM", bound="NetworkMounts")

class NetworkMounts (QtCore.QObject):
    _instance = None
    
    def __new__(cls:type[NM], *args, **kwargs) -> NM:
        if not hasattr(cls, "_instance") or not isinstance(cls._instance, cls):
            cls._instance = super(NetworkMounts, cls).__new__(cls, *args, **kwargs)
            
        return cls._instance
    
    def __init__(self, parent:typing.Optional[QtCore.QObject] = None):
        super().__init__(self, parent=parent)
        
        self._settings:typing.Optional[QtCore.QSettings] = None
        
    
    @classmethod
    def _walk_mro(cls) -> typing.Generator[type[NM], None, None]:
        """Walk the cls.mro() for parent classes that are also singletons

        For use in instance()
        """
        # NOTE: 2025-01-07 12:42:39
        # see traitlets.config.SingletonConfigurable
        for subclass in cls.mro():
            if (
                issubclass(cls, subclass)
                and issubclass(subclass, NM)
                and subclass != NM
            ):
                yield subclass

    @classmethod
    def initialized(cls:type[NM]) -> bool:
        return hasattr(cls, "_instance" and isinstance(cls._instance, cls))

    @classmethod
    def instance(cls:type[NM]) -> NM:
        if cls._instance is None:
            inst = cls(*args, **kwargs)
            for subclass in cls._walk_mro():
                subclass._instance = inst
        if hasattr(cls, "_instance") and isinstance(cls._instance, cls):
            return cls._instance
        else:
            raise RuntimeError(f"Incompatible sibling of '{cls.__name__}' is already instantiated as singleton: {type(cls._instance).__name__}")

    @staticmethod
    def self() -> NM:
        return NM._instance
    
    @staticmethod
    def ensureTrailingSlash(path:str) -> bool:
        changed = False
        if len(path) and not path.endswith(os.sep):
            path += os.sep
            changed = True
            
        return changed
    
    @staticmethod
    def ensureTrailingSlashes(paths:list[str]) -> bool:
        changed = False
        for path in paths:
            if NetworkMounts.ensureTrailingSlash(path):
                changed = True
                
        return changed
    
    @staticmethod
    def getMatchingPath(path:str, slowPaths:list[str]) -> str:
        if len(slowPaths) == 0:
            return str()
        _path = path
        if not _path.endswith(os.sep):
            _path += os.sep
            
        for slp in slowPaths:
            if _path.startswith(slp):
                return slp
            
        return str()
    
    @staticmethod
    def enumToString(etype:IntEnum) -> str:
        from core.datatypes import enum2str
        return enum2str(etype)
    
    def isSlowPath(self, path:str, type = NetworkMountsType.Any) -> bool:
        pass

    def isOptionEnabledForPath(self, path:str, option:NetworkMountOption) -> bool:
        pass
    
    def isEnabled(self) -> bool:
        pass
    
    def setEnabled(self, val:bool):
        pass
    
    def isOptionEnabled(option:NetworkMountOption, defaultValue:bool=False) -> bool:
        pass
    
    def setOption(self, option:NetworkMountOption, value:bool):
        pass
    
    def paths(self, type:NetworkMountsType = NetworkMountsType.Any) -> list[str]:
        pass
    
    def addPath(self, patr:str, type:NetworkMountsType):
        pass
    
    def canonicalSymlinkPath(self, patr:str) -> str:
        pass
    
    def clearCache(self):
        pass
    
    def sync(self):
        pass
    
    
    
    


    
