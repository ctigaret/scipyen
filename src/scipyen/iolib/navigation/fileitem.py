# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class FileItem(QtCore.QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._url_:QtCore.QUrl = None
        self._user_:str = ""
        self._group_:str = ""
        self._isLink_:bool = False
        self._isDir_:bool = False
        Q_PROPERTY(bool isDir READ isDir)
        Q_PROPERTY(bool isFile READ isFile)
        Q_PROPERTY(bool isReadable READ isReadable)
        Q_PROPERTY(bool isWritable READ isWritable)
        Q_PROPERTY(bool isHidden READ isHidden)
        Q_PROPERTY(bool isSlow READ isSlow)
        Q_PROPERTY(bool isDesktopFile READ isDesktopFile)
        Q_PROPERTY(QString linkDest READ linkDest)
        Q_PROPERTY(QUrl targetUrl READ targetUrl)
        Q_PROPERTY(QString localPath READ localPath WRITE setLocalPath)
        Q_PROPERTY(bool isLocalFile READ isLocalFile)
        Q_PROPERTY(QString text READ text)
        Q_PROPERTY(QString name READ name WRITE setName)
        Q_PROPERTY(QString mimetype READ mimetype)
        Q_PROPERTY(QMimeType determineMimeType READ determineMimeType)
        Q_PROPERTY(QMimeType currentMimeType READ currentMimeType)
        Q_PROPERTY(bool isFinalIconKnown READ isFinalIconKnown)
        Q_PROPERTY(bool isMimeTypeKnown READ isMimeTypeKnown)
        Q_PROPERTY(QString mimeComment READ mimeComment)
        Q_PROPERTY(QString iconName READ iconName)
        Q_PROPERTY(QStringList overlays READ overlays)
        Q_PROPERTY(QString comment READ comment)
        Q_PROPERTY(QString getStatusBarInfo READ getStatusBarInfo)
        Q_PROPERTY(bool isRegularFile READ isRegularFile)
        self._linkDest_:str = ""
        self._targetUrl_:QtCore.QUrl = None

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
        
