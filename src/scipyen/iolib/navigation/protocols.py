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
ProtocolType = IntEnum("ProtocolType", ["T_STREAM", "T_FILESYSTEM",
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
    def __init__(self, name:str, exec_str:str, jsonobj:dict): # CAUTION dict in place of QJsonObject (not available in PyQt5)
        self._name_ = name
        self._exec_ = exec_str
        self._isSourceProtocol_:bool     = jsonobj.get("source", True)
        self._supportsPermissions_:bool  = jsonobj.get("permissions", True)
        self._isHelperProtocol_:bool     = jsonobj.get("helper", False)
        self._supportsReading_:bool      = jsonobj.get("reading", True)
        self._supportsWriting_:bool      = jsonobj.get("writing", True)
        self._supportsMakeDir_:bool      = jsonobj.get("makedir", True)
        self._supportsDeleting_:bool     = jsonobj.get("deleting", True)
        self._supportsLinking_:bool      = jsonobj.get("linking", True)
        self._supportsMoving_:bool       = jsonobj.get("moving", True)
        self._supportsOpening_:bool      = jsonobj.get("opening", True)
        self._supportsTruncating_:bool   = jsonobj.get("truncating", True)
        self._canCopyFromFile_:bool      = jsonobj.get("copyFromFile", True)
        self._canCopyToFile_:bool        = jsonobj.get("copyToFile", True)
        self._canRenameFromFile_:bool    = jsonobj.get("renameFromFile", True)
        self._canRenameToFile_:bool      = jsonobj.get("renameToFile", True)
        self._canDeleteRecursive_:bool   = jsonobj.get("deleteRecursive", True)
        
        self._inputType_:ProtocolType = ProtocolType.T_FILESYSTEM
        self._outputType_:ProtocolType = ProtocolType.T_FILESYSTEM
        
        # ATTENTION: jsonobj here is, in fact, a dict
        # default is FileNameUsedForCopying.FromUrl
        fnu = jsonobj.get("fileNameUsedForCopying", "Name")
        self._fileNameUsedForCopying_:FileNameUsedForCopying = FileNameUsedForCopying.FromUrl
        if fnu == "Name":
            self._fileNameUsedForCopying_ = FileNameUsedForCopying.Name
        elif fnu == "DisplayName":
            self._fileNameUsedForCopying_ = FileNameUsedForCopying.DisplayName
            
        self._listing_:list = list()
        tmp = jsonobj.get("listing", "[]")
        if all(isinstance(v, str) for v in tmp) and all(c in tmp for c in ("[", "]")) and tmp.startswith("[") and tmp.endswith("]"):
            self._listing_ = json.loads(tmp)
            
        if len(self._listing_) == 1 and self._listing_[0].lower() == "false":
            self._listing_.clear()
            
        self._supportsListing_:bool = len(self._listing_) > 0
        
        self._defaultMimeType_:str = jsonobj.get("defaultMimeType", str())
        
        self._determineMimetypeFromExtension_:bool = jsonobj.get("determineMimetypeFromExtension", True)
        
        self._archiveMimeTypes_:list = list()
        tmp = jsonobj.get("archiveMimetype", "[]")
        if all(isinstance(v, str) for v in tmp) and all(c in tmp for c in ("[", "]")) and tmp.startswith("[") and tmp.endswith("]"):
            self._archiveMimeTypes_ = json.loads(tmp)
            
        self._icon_:str = jsonobj.get("icon", "")
        
        self._config_:str = jsonobj.get("config", self._name_)
        
        self._maxWorkers_:int = jsonobj.get("maxInstances", 1)
        
        self._maxWorkersPerHost_:int = jsonobj.get("maxInstancesPerHost", 1)
        
        
        tmp = jsonobj.get("input", "")
        if tmp  == "filesystem":
            self._inputType_ = ProtocolType.T_FILESYSTEM
        elif tmp == "stream":
            self._inputType_ = ProtocolType.T_STREAM
        else:
            self._inputType_ = ProtocolType.T_NONE
            
        self._outputType_:ProtocolType = ProtocolType.T_FILESYSTEM
        tmp = jsonobj.get("output", "")
        if tmp  == "filesystem":
            self._outputType_ = ProtocolType.T_FILESYSTEM
        elif tmp == "stream":
            self._outputType_ = ProtocolType.T_STREAM
        else:
            self._outputType_ = ProtocolType.T_NONE
        
        self._docPath_:str = jsonobj.get("X-DocPath", "")
        
        if len(self._docPath_) == 0:
            self._docPath_ = jsonobj.get("DocPath", "")
            
        self._protClass_:str = jsonobj.get("Class", "").lower()
        if not self._protClass_.startswith(":"):
            self._protClass_ = ":" + self._protClass_
            
        tmp = jsonobj.get("ExtraNames", "[]")
        if all(isinstance(v, str) for v in tmp) and all(c in tmp for c in ("[", "]")) and tmp.startswith("[") and tmp.endswith("]"):
            extraNames = json.loads(tmp)
        else:
            extraNames = list()
            
        tmp = jsonobj.get("ExtraTypes", "[]")
        if all(isinstance(v, str) for v in tmp) and all(c in tmp for c in ("[", "]")) and tmp.startswith("[") and tmp.endswith("]"):
            extraTypes = json.loads(tmp)
        else:
            extraTypes = list()
        
        toMetaType = lambda x: QtCore.QMetaType(QtCore.QMetaType.type(x)).id()
        
        if len(extraNames) > 0:
            if len(extraNames) == len(extraTypes):
                self._extraFields_ = list(map(lambda x: ExtraField(x[0], toMetaType(x[1])), zip(extraNames, extraTypes)))
            else:
                scipywarn(f"Malformed JSON protocol file for protocol {self._name_}; number of ExtraNames fields should match the number of ExtraTypes fields")
        
        self._showPreviews_:bool = jsonobj.get("ShowPreviews", self._protClass_ == ":local")
        
        self._capabilities_:list = list()
        tmp = jsonobj.get("Capabilities", "[]")
        if all(isinstance(v, str) for v in tmp) and all(c in tmp for c in ("[", "]")) and tmp.startswith("[") and tmp.endswith("]"):
            self._capabilities_ = json.loads(tmp)
            
        self._proxyProtocol_ = jsonobj.get("ProxiedBy", "")
            
class ProtocolInfoFactory: # pass # TODO 2025-01-18 12:18:35 write me - singleton class!
    __instance__ = None # NOTE: Singleton design pattern
    
    def __new__(cls:typing.Self, *args, **kwargs) -> typing.Self:
        # NOTE: Singleton design pattern
        if not hasattr(cls, "__instance__") or not isinstance(cls.__instance__, cls):
            cls.__instance__ = super(ProtocolInfoFactory, cls).__new__(cls, *args, **kwargs)
            
        return cls.__instance__
    
    def __init__(self):
        self._cacheDirty_:bool = True
        self._mutex_:QtCore.QMutex = QtCore.QMutex()
        self._cache_:dict = dict() # mapping str ↦ _ProtocolInfo_
        self.__instance__ = self # NOTE: Singleton design pattern
        
    def __del__(self):
        locker = QtCore.QMutexLocker(self._mutex_)
        self._cache_.clear()
        
    # ### BEGIN NOTE: 2025-02-07 14:30:06 Singleton design pattern
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
        return hasattr(cls, "__instance__" and isinstance(cls.__instance__, cls))
    
    @classmethod
    def instance(cls:typing.Self, *args, **kwargs) -> typing.Self: # NOTE: Singleton design pattern
        if cls.__instance__ is None:
            inst = cls(*args, **kwargs)
            for subclass in cls._walk_mro():
                subclass.__instance__ = inst
        if hasattr(cls, "__instance__") and isinstance(cls.__instance__, cls):
            return cls.__instance__
        else:
            raise RuntimeError(f"Incompatible sibling of '{cls.__name__}' is already instantiated as singleton: {type(cls.__instance__).__name__}")

    @staticmethod
    def instance() -> typing.Self: # originally self()... in kprotocolinfofactory.cpp
        return ProtocolInfoFactory.__instance__
    
    # ### END   NOTE: 2025-02-07 14:30:06 Singleton design pattern
    
    def protocols(self) -> list:
        """Returns a list of names of cached protocols"""
        locker = QtCore.QMutexLocker(self._mutex_)
        self.fillCache()
        return list(self._cache_.keys())
    
    def allProtocols(self) -> list:
        """Returns a list of cached protocols"""
        locker = QtCore.QMutexLocker(self._mutex_)
        self.fillCache()
        return list(self._cache_.values())
    
    def findProtocol(self, protocol:str, updateCacheIfNotFound:bool) -> _ProtocolInfo_:
        if len(protocol) == 0 or not protocol.startswith(":"):
            return
        
        locker = QtCore.QMutexLocker(self._mutex_)
        filled = self.fillCache()
        
        info = self._cache_.get(protocol, None)
        
        if info is None and not filled and updateCacheIfNotFound:
            scipywarn(f"Refilling ProtocolInfoFactory cache in the hope to find {protocol}")
            self._cacheDirty_ = True
            self.fillCache()
            info = self._cache_.get(protocol, None)
            
        return info
        
    def fillCache(self) -> bool: 
        # TODO 2025-01-18 22:42:33 FIXME
        # - requires a stand-in for KPluginMetaData
        assert not self._mutex_.tryLock()
        if not self._cacheDirty_:
            return False
        
        self._cache_.clear()
        if sys.platform.startswith("win32"):
            worker = "cmd /c start '' "
        elif sys.platform.startswith("darwin"):
            worker = "open -n"
        else:
            worker = "xdg-open"
            
        # c'tor for+ProtocolInfo_: name:str, exec_str:str, jsonobj:dict'
        self._cache_[":local"] = _ProtocolInfo_(":local", worker, dict())
        
        self._cacheDirty_ =  False
        return True
        
class ProtocolInfo:
    @staticmethod
    def protocols() -> list:
        pfact = ProtocolInfoFactory()
        return pfact.instance().protocols()
    
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
        pinfo = ProtocolInfoFactory.instance().findProtocol(protocol)
        if not isinstance(pinfo, _ProtocolInfo_):
            return False
        
        return not pinfo._isSourceProtocol_
    
    @staticmethod
    def icon(protocol:str) -> str:
        # TODO 2025-01-18 23:45:06
        # relies on KService framework, specifically on KApplicationTrader
        # that identifies a "service" used for that application
        # see how I can bypass all this and use desktoputils -> go back and
        # check ProtocolInfoFactory.fillCache
        
        # what KF6 does:
        # 1) use ProtocolInfoFactory to get a _ProtocolInfo_ object (pinfo) from 
        #     its cache, using the protocol mentioned in 'protocol'
        # 2) if no _ProtocolInfo_ is found (pinfo is None): 
        #   figure out a service for the specified protocol:
        #       use KService KApplicationTrader to query the preferredService for the
        #       f"x-scheme-handler/{protocol}" string
        #
        # 3) once a valid protocol info is found, just get its icon name
        pinfo = ProtocolInfoFactory.instance().findProtocol(protocol)
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
        if prot is None:
            return ""
        return ":local" # NOTE: 2025-01-18 23:44:33 for now
        return prot._protClass_
    
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
    
