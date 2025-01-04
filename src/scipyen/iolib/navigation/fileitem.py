# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing, pathliob, urllib
from enum import Enum, IntEnum
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class Unknown(IntEnum):
    Unknown = -1
    
class FileTimes(IntEnum):
    ModificationTime = 0
    AccessTime = 1
    CreationTime = 2
    # ChangeTime = 3
    
class MimeTypeDetermination(IntEnum):
    NormalMimeTypeDetermination = 0
    SkipMimeTypeFromContent = 1

class FileItem():
    # NOTE: 2025-01-04 12:47:20
    # should use a pathlib.Path as backend
    # NOTE: 2025-01-04 15:07:39
    # doesn't use Qt Signals/Slots so no need to inherit from QObject
    # By keeping it in the Python world I guess also removes the need to inherit 
    # from QSharedData (KFIleItemPrivate)
    def __init__(self, parent=None):
        # ### BEGIN KFIleItemPrivate
        # ### END KFIleItemPrivate
        self._url_:QtCore.QUrl = QtCore.QUrl()
        self._user_:str = str()
        self._group_:str = str()
        self._isLink_:bool = False
        self._isDir_:bool = False
        self._isFile_:bool = False
        self._isReadable_:bool = False
        self._isWritable_:bool = False
        self._isHidden_:bool = False
        self._isSlow_:bool = False
        self._isDesktopFile_:bool = False
        self._linkDest_:str = str()
        self._targetUrl_:QtCore.QUrl = QtCore.QUrl()
        self._localPath_:str = str()
        self._isLocalFile_:bool = False
        self._text_:str = str()
        self._name_:str = str()
        self._mimetype_:str = str()
        self._determineMimeType_:QtCore.QMimeType = QtCore.QMimeType()
        self._currentMimeType_:QtCore.QMimeType = QtCore.QMimeType()
        self._isFinalIconKnown_:bool = False
        self._isMimeTypeKnown_:bool = False
        self._mimeComment_:str = str()
        self._iconName_:str = str()
        self._overlays_:list[str] = list()
        self._comment_:str = str()
        self._statusBarInfo_:str = str()
        self._isRegularFile_:bool = False

    @property
    def url(self) -> QtCore.QUrl:
        return self._url_
    
    @url.setter
    def url(self, val:QtCore.QUrl):
        self._url_ = val

    @property
    def user(self) -> str:
        return self._user_
    
    @user.setter
    def user(self, val:str):
        self._user_ = val
        
    @property
    def group(self) -> str:
        return self._group_
    
    @group.setter
    def group(self, val:str):
        self._group_ = val
        
    @property
    def isLink(self) -> bool:
        return self._isLink_
    
    @isLink.setter
    def isLink(self, val:bool):
        self._isLink_ = val == True
        
    @property
    def isDir(self)->bool:
        return self._isDir_
    
    @isDir.setter
    def isDir(self, val:bool):
        self._isDir_ = val == True
        
    @property
    def isFile(self)->bool:
        return self._isFile_
    
    @isFile.setter
    def isFile(self, val:bool):
        self._isFile_ = val == True
        
    @property
    def isReadable(self)->bool:
        return self._isReadable_
    
    @isReadable.setter
    def isReadable(self, val:bool):
        self._isReadable_ = val == True
        
    @property
    def isWritable(self)->bool:
        return self._isWritable_
    
    @isWritable.setter
    def isWritable(self, val:bool):
        self._isWritable_ = val == True
        
    @property
    def isHidden(self) -> bool:
        return self._isHidden_
    
    @isHidden.setter
    def isHidden(self, val:bool):
        self._isHidden_ = val == True
        
    @property
    def isSlow(self)->bool:
        return self._isSlow_
    
    @isSlow.setter
    def isSlow(self, val:bool):
        self._isSlow_ = val == True
        
    @property
    def isDesktopFile(self)->bool:
        return self._isDesktopFile_
    
    @isDesktopFile.setter
    def isDesktopFile(self, val:bool):
        self._isDesktopFile_ = val == True
        
    @property
    def linkDest(self)->str:
        return self._linkDest_
    
    @linkDest.setter
    def linkDest(self, val:str):
        self._linkDest_ = val
        
    @property
    def targetUrl(self)->QtCore.QUrl:
        return self._targetUrl_
    
    @targetUrl.setter
    def targetUrl(self, val:QtCore.QUrl):
        self._targetUrl_ = val

    @property
    def localPath(self)->str:
        return self._localPath_
    
    @localPath.setter
    def localPath(self, val:str):
        self._localPath_ = val
        
    @property
    def isLocalFile(self)->bool:
        return self._isLocalFile_
    
    @isLocalFile.setter
    def isLocalFile(self, val:bool):
        self._isLocalFile_ = val == True
        
    @property
    def text(self)->str:
        ret8urn self._text_
        
    @test.setter
    def text(self, val:str):
        self._text_ = val
        
    @property
    def name(self)->str:
        return self._name_
    
    @name.setter
    def name(self, val:str):
        self._name_ = val
        
    @property
    def mimetype(self)->str:
        return self._mimetype_
    
    @mimetype.setter
    def mimetype(self, val:str):
        self._mimetype_ = val
        
    @property
    def determineMimeType(self)->QtCore.QMimeType:
        return self._determineMimeType_
    
    @determineMimeType.setter
    def determineMimeType(self, val:QtCore.QMimeType):
        self._determineMimeType_ = val
        
    @property
    def currentMimeType(self)->QtCore.QMimeType:
        return self._currentMimeType_
    
    @currentMimeType.setter
    def currentMimeType(self, val:QtCore.QMimeType):
        self._currentMimeType_ = val
        
    @property
    def isFinalIconKnown(self)->bool:
        return self._isFinalIconKnown_
    
    @isFinalIconKnown.setter
    def isFinalIconKnown(self, val:bool):
        self._isFinalIconKnown_ = val == True
        
    @property
    def isMimeTypeKnown(self)->bool:
        return self._isMimeTypeKnown_
    
    @isMimeTypeKnown.setter
    def isMimeTypeKnown(self, val:bool):
        self._isMimeTypeKnown_ = val == True
        
    @property
    def mimeComment(self)->str:
        return self._mimeComment_
    
    @mimeComment.setter
    def mimeComment(self, val:str):
        self._mimeComment_ = val
    
    @property
    def iconName(self)->str:
        return self._iconName_
    
    @iconName.setter
    def iconName(self, val:str):
        self._iconName_ = val
        
    @property
    def overlays(self)->list[str]:
        return self._overlays_
    
    @overlays.setter
    def overlays(self, val:list[str]):
        self._overlays_ = val
        
    @property
    def comment(self)->str:
        return self._comment_
    
    @comment.setter
    def comment(self, val:str):
        self._comment_ = val
        
    @property
    def statusBarInfo(self)->str:
        return self._statusBarInfo_
    
    @statusBarInfo.setter
    def statusBarInfo(self, val:str):
        self._statusBarInfo_ = val
        
    @property
    def isRegularFile(self)->bool:
        return self._isRegularFile_
    
    @isRegularFile.setter
    def isRegularFile(self, val:bool):
        self._isRegularFile_ = val == True
