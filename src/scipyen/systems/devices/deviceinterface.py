# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Work in progress, DO NOT USE
"""
import sys, os, typing, pathlib, functools, itertools, traceback
from copy import (copy, deepcopy)
from urllib.parse import urlparse, urlsplit
from collections import deque
from abc import abstractmethod
from enum import Enum, IntEnum
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path
from core.datatypes import TypeEnum
from core.multimeta import MultipleMeta

class _Device_:pass
class Device: pass

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
    class Type(TypeEnum):
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

    def __init__(self, dd:_DeviceInterface_, 
                 backendObject:QtCore.QObject,
                 parent:typing.Optional[QtCore.QObject]=None):
        super().__init__(parent=parent)
        self._d_:_DeviceInterface_ = dd
        if isinstance(self._d_, _DeviceInterface_) and isinstance(backendObject, QtCore.QObject):
            self._d_.setBackendObject(backendObject)
        
    def __del__(self):
        if isinstance(self._d_, _DeviceInterface_) and isinstance(backendObject, QtCore.QObject):
            self._d_.backendObject().deleteLater()
        self._d_ = None
        
    @staticmethod
    def deviceInterfaceype() -> Type:
        return Type.Unknown
        
    def isValid(self) -> bool:
        if isinstance(self._d_, _DeviceInterface_) and isinstance(backendObject, QtCore.QObject):
            return self._d_.backendObject() is not None
        else:
            return False
    
    @staticmethod
    def typeToString(type:Type) -> str:
        return type.name
        
    @staticmethod
    def stringToType(type:str) -> Type:
    # def stringToType(self, type:str) -> DeviceInterfaceType:
        return Type.namevalue(type)
    
    @staticmethod
    def typeDescription(type:Type):
    # def typeDescription(self, type:DeviceInterfaceType):
        match (type):
            case Type.Unknown:
                return "Unknown"
            case Type.GenericInterface:
                return "Generic Interface"
                # return tr("Generic Interface", "Generic Interface device type");
            case Type.Processor:
                return "Processor"
                # return tr("Processor", "Processor device type");
            case Type.Block:
                return "Block Device"
                # return tr("Block", "Block device type");
            case Type.StorageAccess:
                return "Storage Access Device"
                # return tr("Storage Access", "Storage Access device type");
            case Type.StorageDrive:
                return "Storage Drive"
                # return tr("Storage Drive", "Storage Drive device type");
            case Type.OpticalDrive:
                return "Optical Drive"
                # return tr("Optical Drive", "Optical Drive device type");
            case Type.StorageVolume:
                return "Storage Volume"
                # return tr("Storage Volume", "Storage Volume device type");
            case Type.OpticalDisc:
                return "Optical Disc"
                # return tr("Optical Disc", "Optical Disc device type");
            case Type.Camera:
                return "Camera"
                # return tr("Camera", "Camera device type");
            case Type.PortableMediaPlayer:
                return "Portable Media Player"
                # return tr("Portable Media Player", "Portable Media Player device type");
            case Type.Battery:
                return "Battery"
                # return tr("Battery", "Battery device type");
            case Type.NetworkShare:
                return "Network Share"
                # return tr("Network Share", "Network Share device type");
            case Type.Last:
                return str()
                # return QString();
                
            case _:
                return str()
            
        return str()
        # return QString();
        

from systems.devices.device import (_Device_, Device)
