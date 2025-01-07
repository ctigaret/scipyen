# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import sys, os, typing, pathlib
from enum import Enum, IntEnum
from qtpy import QtCore
from qtpy.QtCore import Signal, Slot, Property

# from core.datatypes import TypeEnum

s_canonicalLinkSpacePaths = dict() # str ↦ str

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
    
    def __init__(self):
        super().__init__(self)
        
        configLocation = pathlib.Path(QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.ConfigLocation))
        
        configFileName = (configLocation / "network_mounts").as_posix()
        
        self._settings_:QtCore.QSettings = QtCore.QSettings(configFileName,
                                                           QtCore.QSettings.Format.IniFormat, self)
        
        for nmType in (NetworkMountsType.NfsPaths, NetworkMountsType.SmbPaths,
                       NetworkMountsType.SymlinkDirectory,
                       NetworkMountsType.SymlinkToNetworkMount):
            typeStr = self.enumToString(nmType)
            slowPaths = self._settings_.value(typeStr, list()).value()
            _slowPaths = self.ensureTrailingSlashes(slowPaths)
            self._settings_.setValue(typeStr, _slowPaths)
    
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

    # @staticmethod
    # def self() -> NM:
    #     return NM._instance
    
    @staticmethod
    def ensureTrailingSlash(path:str) -> str:
        if len(path) and not path.endswith(os.sep):
            path += os.sep
        return path
    
    @staticmethod
    def ensureTrailingSlashes(paths:list[str]) -> list:
        return list(map(lambda x: NetworkMounts.ensureTrailingSlash(x), paths))

    @staticmethod
    def getMatchingPath(path:str, slowPaths:list[str]) -> str:
        if len(slowPaths) == 0:
            return str()
        
        _path = str(path)
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
    
    def isSlowPath(self, path:str, type:NetworkMountsType = NetworkMountsType.Any) -> bool:
        return len(self.getMatchingPath(path, self.paths(type))) > 0

    def isOptionEnabledForPath(self, path:str, option:NetworkMountOption) -> bool:
        if not self.isEnabled():
            return False
        
        if not self.isSlowPath(path):
            return False
        
        return self.isOptionEnabled(option, True)
    
    def isEnabled(self) -> bool:
        return self._settings_.value("EnableOptimizations", False).value()
    
    def setEnabled(self, val:bool):
        self._settings_.setValue("EnableOptimizations", val)
    
    def isOptionEnabled(option:NetworkMountOption, defaultValue:bool=False) -> bool:
        return self._settings_.value(self.enumToString(option), defaultValue).value()
    
    def setOption(self, option:NetworkMountOption, value:bool):
        self._settings_.setValue(self.enumToString(option), value)
    
    def paths(self, type:NetworkMountsType = NetworkMountsType.Any) -> list[str]:
        if type == NetworkMountsType.Any:
            paths = list()
            for nmType in (NetworkMountsType.NfsPaths, NetworkMountsType.SmbPaths,
                       NetworkMountsType.SymlinkDirectory,
                       NetworkMountsType.SymlinkToNetworkMount):
                paths.extend(self._settings_.value(self.enumToString(nmType), list()).value())
            return paths
        else:
            return self._settings_.value(self.enumToString(type, list())).value()
        
    def setPaths(self, paths:list[str], type:NetworkMountsType):
        _paths = self.ensureTrailingSlashes(list(paths))
        self._settings_.setValue(self.enumToString(type), _paths)
    
    def addPath(self, patr:str, type:NetworkMountsType):
        _path = self.ensureTrailingSlash(str(_path))
        newPaths = self.paths(type)
        newPaths.append(_path)
    
    def canonicalSymlinkPath(self, path:str) -> str:
        useCache = self.isOptionEnabled(NetworkMountOption.SymlinkPathsUseCache, True)
        
        if useCache:
            if path in s_canonicalLinkSpacePaths:
                return s_canonicalLinkSpacePaths[path]
        
        symlinkPath = self.getMatchingPath(path, self.paths(NetworkMountsType.SymlinkToNetworkMount))
        
        if len(symlinkPath):
            if symlinkPath.endswith(os.sep):
                symlinkPath = symlinkPath[:-1]
                
            pInfo = QtCore.QFileInfo(symlinkPath)
            linkPath = str(path)
            target = pInfo.symLinkTarget()
            
            if len(target) == 0: # not a symlink
                if useCache:
                    s_canonicalLinkSpacePaths[path] = path
                return path
            
            else: # symlink
                linkPath = linkPath.replace(symlinkPath, target)
                if useCache:
                    s_canonicalLinkSpacePaths[path] = linkPath
                    
                return linkPath
            
        linkSpacePath = self.getMatchingPath(path, self.paths(NetworkMountsType.SymlinkDirectory))
        
        if len(linkSpacePath):
            _path = str(path)
            if not _path.endswith(os.sep):
                _path += os.sep
                
            if _path == linkSpacePath:
                if useCache:
                    s_canonicalLinkSpacePaths[path] = path
                    
                return path
            
            try:
                linkIndex = path.index(os.sep, len(linkSpacePath))
            except ValueError:
                linkIndex = -1
                
            symlink = path[0:linkIndex] if linkIndex in range(len(path)) else path
            
            if useCache and symlink in s_canonicalLinkSpacePaths:
                linkPath = str(path)
                linkPath = linkPath.replace(symlink, s_canonicalLinkSpacePaths[symlink])
                s_canonicalLinkSpacePaths[path] = linkPath
                return linkPath
            else:
                link = QtCore.QFileInfo(symlink)
                
                if link.isSymLink():
                    linkPath = str(path)
                    linkPath = linkPath.replace(symlink, link.symLinkTarget())
                    if useCache:
                        s_canonicalLinkSpacePaths[path] = linkPath
                    return linkPath
                else:
                    if useCache:
                        s_canonicalLinkSpacePaths[path] = path
    
        return path
    
    def clearCache(self):
        if len(s_canonicalLinkSpacePaths):
            s_canonicalLinkSpacePaths.clear()
    
    def sync(self):
        self._settings_.sync()
    
    
    
    


    
