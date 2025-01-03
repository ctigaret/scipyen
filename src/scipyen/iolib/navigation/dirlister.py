# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing, pathlib, warnings, traceback
from enum import Enum, IntEnum
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class OpenUrlFlag(IntEnum):
    NoFlags = 0x0
    Keep = 0x1,
    Reload = 0x2
    
    
class DirItem(): 
    # TODO 2025-01-03 23:10:51 
    # Use pathlib.Path instead !?
    def __init__(self, url:QtCore.QUrl, canonicalPath:str):
        self.url:QtCore.QUrl = url
        self._canonicalPath:str = canonicalPath
        self.autoUpdates:int = 0
        self.complete:bool = False
        self.watchedWhileInCache:bool = False

class CoreDirListerCache(QtCore.QObject):
    def __init__(self):
        super().__init__()
        
    


class CoreDirLister(QtCore.QObject):
    OpenUrlFlags = OpenUrlFlag
    def __init__(self, parent:typing.Optional[QtCore.QObject]=None):
        super().__init__(parent=parent)
        # ### BEGIN KFilePlacesModelPrivate c'tor
        
        # ### END KFilePlacesModelPrivate c'tor
        
