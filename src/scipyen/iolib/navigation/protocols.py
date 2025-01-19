# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import typing, pathlib, functools, os, itertools, sys
import datetime
import json
from functools import (singledispatch, singledispatchmethod)
from urllib.parse import urlparse, urlsplit
from collections import namedtuple
from enum import Enum, IntEnum
try:
    from qtpy import sip as sip # for sip.cast
    has_sip = True
except:
    has_sip = False
# import sip # for sip.isdeleted() - not used yet, but beware
from traitlets.utils.bunch import Bunch
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg)
from qtpy.QtCore import (Signal, Slot, Property,)
# from qtpy.uic import loadUiType
from core import desktoputils as dutils
from core import qtutils
from core.prog import (scipywarn, safeWrapper)

class ProtocolType(IntEnum):pass
ProtocolType = IntEnum("ProtocolType", ["T_STREAM", "T_FILESYSTEM"
                                        "T_NONE", "T_ERROR"])

class FileNameUsedForCopying(IntEnum):pass
FileNameUsedForCopying = IntEnum("FileNameUsedForCopying", ["Name", "FromUrl", "DisplayName"])

class ExtraFieldType(IntEnum):
    String = QtCore.QMetaType.QString # 10
    DateTime = QtCore.QMetaType.QDateTime # 16
    Invalid = QtCore.QMetaType.UnknownType # 0
    
class ExtraField:
    def __init__(self, name:typing.Optional[str]=None, type:typing.Optional[ExtraFieldType]=ExtraFieldType.Invalid):
        self.name:str = name
        self.type:ExtraFieldType = type
    

class _ProtocolInfo_:
    def __init__(self, name:str, exec:str, jsonobj:dict): # CAUTION dict in place of QJsonObject (not available in PyQt5)
        # ### BEGIN KProtocolInfoPrivate API
        self._name = name
        self._exec = exec
        
        self._isSourceProtocol:bool     = jsonobj.get("source", True)
        self._supportsPermissions:bool  = jsonobj.get("permissions", True)
        self._isHelperProtocol:bool     = jsonobj.get("helper", False)
        self._supportsreading:bool      = jsonobj.get("reading", True)
        self._supportsWriting:bool      = jsonobj.get("writing", True)
        self._supportsMakeDir:bool      = jsonobj.get("makedir", True)
        self._supportsDeleting:bool     = jsonobj.get("deleting", True)
        self._supportsLinking:bool      = jsonobj.get("linking", True)
        self._supportsMoving:bool       = jsonobj.get("moving", True)
        self._supportsOpening:bool      = jsonobj.get("opening", True)
        self._supportsTruncating:bool   = jsonobj.get("truncating", True)
        self._canCopyFromFile:bool      = jsonobj.get("copyFromFile", True)
        self._canCopyToFile:bool        = jsonobj.get("copyToFile", True)
        self._canRenameFromFile:bool    = jsonobj.get("renameFromFile", True)
        self._canRenameToFile:bool      = jsonobj.get("renameToFile", True)
        self._canDeleteRecursive:bool   = jsonobj.get("deleteRecursive", True)

        self._fileNameUsedForCopying:FileNameUsedForCopying = FileNameUsedForCopying.FromUrl
        
        fnu = jsonobj.get("fileNameUsedForCopying", "Name")
        if fnu == "Name":
            self._fileNameUsedForCopying = FileNameUsedForCopying.Name
        elif fnu = "DisplayName":
            self._fileNameUsedForCopying = FileNameUsedForCopying.DisplayName
            
        self._listing:list = list()
        tmp = jsonobj.get("listing", "[]")
        if all(isinstance(v, str) for v in tmp) and all(c in tmp for c in ("[", "]")) and tmp.startswith("[") and tmp.endswith("]"):
            self._listing = json.loads(tmp)
            
        if len(self._listing) == 1 and self._listing[0].lower() == "false":
            self._listing.clear()
            
        self._supportsListing:bool = len(self._listing) > 0
        self._defaultMimeType:str = jsonobj.get("defaultMimeType", str())
        self._determineMimetypeFromExtension:bool = jsonobj.get("determineMimetypeFromExtension", True)
        
        self._archiveMimeTypes:list = list()
        tmp = jsonobj.get("archiveMimetype", "[]")
        if all(isinstance(v, str) for v in tmp) all(c in tmp for c in ("[", "]")) and tmp.startswith("[") and tmp.endswith("]"):
            self._archiveMimeTypes = json.loads(tmp)
            
        self._icon:str = jsonobj.get("icon", "")
        
        self._config:str = jsonobj.get("config", self._name)
        
        self._maxWorkers:int = jsonobj.get("maxInstances", 1)
        
        self._maxWorkersPerHost:int = jsonobj.get("maxInstancesPerHost", 1)
        
        self._inputType:ProtocolType = ProtocolType."T_FILESYSTEM"
        
        tmp = jsonobj.get("input", "")
        
        if tmp  == "filesystem":
            self._inputType = ProtocolType.T_FILESYSTEM
        elif tmp == "stream":
            self._inputType = ProtocolType.T_STREAM
        else:
            self._inputType = ProtocolType.T_NONE
            
        self._outputType:ProtocolType = ProtocolType.T_FILESYSTEM
        
        tmp = jsonobj.get("output", "")
        if tmp  == "filesystem":
            self._outputType = ProtocolType.T_FILESYSTEM
        elif tmp == "stream":
            self._outputType = ProtocolType.T_STREAM
        else:
            self._outputType = ProtocolType.T_NONE
        
        self._docPath:str = jsonobj.get("X-DocPath", "")
        
        if len(self._docPath) == 0:
            self._docPath = jsonobj.get("DocPath", "")
            
        self._protClass:str = jsonobj.get("Class", "").lower()
        if not self._protClass.startswith(":"):
            self._protClass = ":" + self._protClass
            
        tmp = jsonobj.get("ExtraNames", "[]")
        if all(isinstance(v, str) for v in tmp) all(c in tmp for c in ("[", "]")) and tmp.startswith("[") and tmp.endswith("]"):
            extraNames = json.loads(tmp)
        else:
            extraNames = list()
            
        tmp = jsonobj.get("ExtraTypes", "[]")
        if all(isinstance(v, str) for v in tmp) all(c in tmp for c in ("[", "]")) and tmp.startswith("[") and tmp.endswith("]"):
            extraTypes = json.loads(tmp)
        else:
            extraTypes = list()
        
        toMetaType = lambda x: QtCore.QMetaType(QtCore.QMetaType.type(x)).id()
        
        if len(extraNames) > 0:
            if len(extraNames) == len(extraTypes):
                self._extraFields = list(map(lambda x: ExtraField(x[0], toMetaType(x[1])), zip(extraNames, extraTypes)))
            else:
                scipywarn(f"Malformed JSON protocol file for protocol {self._name}; number of ExtraNames fields should match the number of ExtraTypes fields")
        
        self._showPreviews:bool = jsonobj.get("ShowPreviews", self._protClass == ":local")
        
        self._capabilities:list = list()
        tmp = jsonobj.get("Capabilities", "[]")
        if all(isinstance(v, str) for v in tmp) all(c in tmp for c in ("[", "]")) and tmp.startswith("[") and tmp.endswith("]"):
            self._capabilities = json.loads(tmp)
            
            self._proxyProtocol = jsonobj.get("ProxiedBy", "")
            
        # ### END   KProtocolInfoPrivate API

class ProtocolInfoFactory: # pass # TODO 2025-01-18 12:18:35 write me - singleton class!
    _instance = None # NOTE: Singleton design pattern
    
    def __new__(cls:typing.Self, app: QtWidgets.QApplication, 
                 parent: typing.Optional[QtWidgets.QWidget] = None, *args, **kwargs) -> typing.Self:
        # NOTE: Singleton design pattern
        if not hasattr(cls, "_instance") or not isinstance(cls._instance, cls):
            cls._instance = super(ProtocolInfoFactory, cls).__new__(cls, app, parent, *args, **kwargs)
            
        return cls._instance
    
    def __init__(self):
        self._cacheDirty:bool = True
        self._mutex:QtCore.QMutex = QtCore.QMutex()
        self._cache:dict = dict() # mapping str ↦ _ProtocolInfo_
        
    def __del__(self):
        locker = QtCore.QMutexLocker(self._mutex)
        self._cache.clear()
        
    @classmethod
    def _walk_mro(cls) -> typing.Generator[typing.Self, None, None]: # NOTE: Singleton design pattern
        for subclass in cls.mro():
            if (
                issubclass(cls, subclass)
                and issubclass(subclass, typing.Self)
                and subclass != typing.Self
            ):
                yield subclass
                
    @classmethod
    def initialized(cls:typing.Self) -> bool: # NOTE: Singleton design pattern
        return hasattr(cls, "_instance" and isinstance(cls._instance, cls))
    
    @classmethod
    def instance(cls:typing.Self, *args, **kwargs) -> typing.Self: # NOTE: Singleton design pattern
        if cls._instance is None:
            inst = cls(*args, **kwargs)
            for subclass in cls._walk_mro():
                subclass._instance = inst
        if hasattr(cls, "_instance") and isinstance(cls._instance, cls):
            return cls._instance
        else:
            raise RuntimeError(f"Incompatible sibling of '{cls.__name__}' is already instantiated as singleton: {type(cls._instance).__name__}")

    @staticmethod
    def instance() -> typing.Self: # originally self()...
        return _instance
    
    def protocols(self) -> list:
        """Returns a list of names of cached protocols"""
        locker = QtCore.QMutexLocker(self._mutex)
        self.fillCache()
        return list(self._cache.keys())
    
    def allProtocols(self) -> list:
        """Returns a list of cached protocols"""
        locker = QtCore.QMutexLocker(self._mutex)
        self.fillCache()
        return list(self._cache.values())
    
    def findProtocol(self, protocol:str, updateCacheIfNotFound:bool) -> _ProtocolInfo_:
        if len(protocol) == 0 or not protocol.startswith(":"):
            return
        
        locker = QtCore.QMutexLocker(self._mutex)
        filled = self.fillCache()
        
        info = self._cache.get(protocol, None)
        
        if info is None and not filled and updateCacheIfNotFound:
            scipywarn(f"Refilling ProtocolInfoFactory cache in the hope to find {protocol}")
            self._cacheDirty = True
            self.fillCache()
            info = self._cache.get(protocol, None)
            
        return info
        
    def fillCache(self) -> bool: 
        # TODO 2025-01-18 22:42:33 FIXME
        # - requires a stand-in for KPluginMetaData
        assert not self._mutex.tryLock()
        if not self._cacheDirty:
            return False
        
        self._cache.clear()
        if sys.platform.startswith("win32"):
            worker = "cmd /c start '' "
        elif sys.platform.startswith("darwin"):
            worker = "open -n"
        else:
            worker = "xdg-open"
            
        self._cache[":local"] = _ProtocolInfo_(":local", worker, dict())
        
        self._cacheDirty =  False
        return True
        
class ProtocolInfo:
    @staticmethod
    def protocols() -> list:
        return ProtocolInfoFactory.instance().protocols()
        
    
    @singledispatchmethod
    @staticmethod
    def isKnownProtocol(url:typing.Any, _:bool=True) -> bool:
        pass
    
    @isKnownProtocol.register(QtCore.QUrl)
    def _(url:QtCore.QUrl, _:bool=True) -> bool:
        pass

    @isKnownProtocol.register(str)
    def _(protocol:str, updateCacheIfNotFound:bool=True) -> bool:
        pass
    
    @staticmethod
    def exec(protocol:str) -> str:
        pass
    
    @staticmethod
    def extraFields(url:QtCore.QUrl) -> list:
        pass
    
    @singledispatchmethod
    @staticmethod
    def isHelperProtocol(o:typing.Any) -> bool:
        pass
    
    @isHelperProtocol.register(QtCore.QUrl)
    def _(url:QtCore.QUrl) -> bool:
        pass
    
    @isHelperProtocol.register(str)
    def _(url:str) -> bool:
        pass
    
    @singledispatchmethod
    @staticmethod
    def isFilterProtocol(o:typing.Any) -> bool:
        pass
    
    @isFilterProtocol.register(QtCore.QUrl)
    def _(url:QtCore.QUrl) -> bool:
        return self.isFilterProtocol(url.scheme())
    
    @isFilterProtocol.register(str)
    def _(protocol:str) -> bool:
        prot = ProtocolInfoFactory.instance().findProtocol(protocol)
        if not isinstance(prot, _ProtocolInfo_):
            return False
        
        return not prot._isSourceProtocol
    
    @staticmethod
    def icon(protocol:str) -> str:
        # TODO 2025-01-18 23:45:06
        # see how I can bypass all this and use desktoputils
        prot = ProtocolInfoFactory.instance().findProtocol(protocol)
        pass
    
    @staticmethod
    def config(protocol:str) -> str:
        pass

    @staticmethod
    def maxWorkers(protocol:str) -> int:
        pass
    
    @staticmethod
    def maxWorkersPerHost(protocol:str) -> int:
        pass
    
    @staticmethod
    def determineMimetypeFromExtension(protocol:str) -> bool:
        pass
    
    @staticmethod
    def defaultMimetype(protocol:str) -> str:
        pass
    
    @staticmethod
    def docPath(protocol:str) -> str:
        pass
    
    @staticmethod
    def protocolClass(protocol:str) -> str:
        prot = ProtocolInfoFactory.instance().findProtocol(protocol) # TODO
        if prot it None:
            return ""
        return ":local" # NOTE: 2025-01-18 23:44:33 for now
        return prot._protClass
    
    @staticmethod
    def showFilePreview(protocol:str) -> bool:
        pass
    
    @staticmethod
    def capabilities(protocol:str) -> list:
        pass
    
    @staticmethod
    def archiveMimetypes(protocol:str) -> list:
        pass
    
    @staticmethod
    def proxiedBy(protocol:str) -> str:
        pass
    
