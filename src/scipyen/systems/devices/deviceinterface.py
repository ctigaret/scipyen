# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Work in progress, DO NOT USE
"""
import sys, os, typing, pathlib, functools, itertools, traceback
from urllib.parse import urlparse, urlsplit
from collections import namedtuple
from abc import ABCMeta, abstractmethod
from enum import Enum, IntEnum
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path
from core.datatypes import TypeEnum

class DeviceInterfaceType(TypeEnum):
    """"""
    # NOTE: 2025-01-03 14:09:24 
    # Solid DeviceInterface::Type
    Unknown = 0,
    GenericInterface = 1,
    Processor = 2,
    Block = 3,
    StorageAccess = 4,
    StorageDrive = 5,
    OpticalDrive = 6,
    StorageVolume = 7,
    OpticalDisc = 8,
    Camera = 9,
    PortableMediaPlayer = 10,
    Battery = 12,
    NetworkShare = 14,
    Last = 0xffff,
    
class _Device_:pass # CAUTION - remove if importing, below

class _DeviceInterface_:
    def __init__(self):
        super().__init__()
        self._devicePrivate_:typing.Optional[_Device_] = None
        self._backend_:typing.Optional[QtCore.QObject] = None
        
    def backendObject(self) -> QtCore.QObject:
        return self._backend_ # in Solid this is equiv to a python weakref?
    
    def setBackendObject(self, o:QtCore.QObject):
        self._backend_ = o
    
    def devicePrivate(self) -> _Device_:
        return self._devicePrivate_
    
    def setDevicePrivate(self, dev:_Device_):
        self._devicePrivate_ = dev

class DeviceInterface(QtCore.QObject):
    
    def __init__(self, dd:_DeviceInterface_, backendObject:QtCore.QObject,
                 parent:typing.Optional[QtCore.QObject]=None):
        super().__init__(parent=parent)
        self._d_ = dd
        self._d_.setBackendObject(backendObject)
        
    def __del__(self):
        self._d_.backendObject().deleteLater()
        self._d_ = None
        
    def isValid(self) -> bool:
        return self._d_.backendObject() is not None
    
    def typeToString(self, type:DeviceInterfaceType) -> str:
        return type.name()
        
    def stringToType(self, type:str) -> DeviceInterfaceType:
        return DeviceInterfaceType.
