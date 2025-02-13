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
from abc import abstractmethod
from enum import Enum, IntEnum
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
# ATTENTION: 2025-02-11 22:13:57 
# see NOTE: 2025-02-11 22:28:54 and NOTE: 2025-02-11 22:46:31
# in core/multimeta.py
# for workaround the metaclass conflict for subclasses of QObject and multimeta.MultipleMeta
from core.multimeta import MultipleMeta
from core.sysutils import adapt_ui_path
from core.datatypes import TypeEnum

from systems.devices import device
from systems.devices.device import (_DeviceInterface_, DeviceInterface, DeviceInterfaceType, Device)

class UsageType(TypeEnum):
    Other = 0
    Unused = 1
    FileSystem = 1
    PartitionTable = 3
    Raid = 4
    encrypted = 5
    
class _StorageVolume_(_DeviceInterface_):
    def __init__(self):
        super().__init__()
        
class _StorageVolumeMultiMeta_(type(DeviceInterface), MultipleMeta): 
    """Enables constructor overloading"""
    pass
    
class StorageVolume(DeviceInterface, metaclass = _StorageVolumeMultiMeta_):
    from systems.devices.interfaces.device import DeviceInterface as IfaceDevIFace
    def __init__(self, backendObject:QtCore.QObject):
        super().__init__(_StorageVolume_(), backendObject)
        self._ignored_:bool = True
        self._usage_:UsageType = UsageType.Unused
        self._fsType_:str = str()
        self._label_:str = str()
        self._uuid_:str = str()
        self._size_:int = 0
        
    def __init__(self, dd:_StorageVolume_, backendObject:QtCore.QObject):
        # initializes super()._d_ i.e. DeviceInterface._d_, which is a _DeviceInterface_
        super().__init__(dd, backendObject) 
        self._ignored_:bool = True
        self._usage_:UsageType = UsageType.Unused
        self._fsType_:str = str()
        self._label_:str = str()
        self._uuid_:str = str()
        self._size_:int = 0

    def isIgnored(self) -> bool:
        # from systems.devices.interfaces.device import DeviceInterface as IfaceDevIFace
        # Q_D(const StorageVolume);
        #                   Type,                   Object,             Default, Method        
        # return_SOLID_CALL(Ifaces::StorageVolume *, d->backendObject(), true, isIgnored());
        # Here, Solid casts d->backendObject() to a 
        # Ifaces::StorageVolume <- Ifaces::Block <- Ifaces::DeviceInterface
        # then calls its isIgnored() and returns the result
        # if casting fails, returns True (i.e., is ignored)
        #
        # Now, self inherits from systems.devices.device.DeviceInterface ⟹
        # self._d_ is a devices.device._DeviceInterface_; its backend object 
        # (QObject); Solid, casts this backend object, here, to a 
        # devices.interfaces.DeviceInterface aliases here to IfaceDevIFace
        
        # NOTE: 2025-02-11 22:30:02
        # while still using PyQt5 could try and use sip.cast
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        # print(f"{self.__class__.__name__} o is a {type(o).__name__}")
        if isinstance(o, self.IfaceDevIFace):
            self._ignored_ = o.isIgnored() # Method parameter of return_SOLID_CALL macro
        else:
            self._ignored_ = True
            
        return self._ignored_ # Default parameter of return_SOLID_CALL macro
        
    @staticmethod
    def deviceInterfaceType() -> DeviceInterfaceType:
        return DeviceInterfaceType.StorageVolume
    
    def usage(self) -> UsageType:
        # NOTE: 2025-02-11 23:09:16
        # see NOTE: 2025-02-11 22:30:02
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        # print(f"{self.__class__.__name__} o is a {type(o).__name__}")
        if isinstance(o, self.IfaceDevIFace):
            self._usage_ = o.usage()
        else:
            self._usage_ = UsageType.Unused # Default parameter of return_SOLID_CALL macro
            
        return self._usage_
    
    def fsType(self) -> str:
        # NOTE: 2025-02-11 23:09:16
        # see NOTE: 2025-02-11 22:30:02
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        # print(f"{self.__class__.__name__} o is a {type(o).__name__}")
        if isinstance(o, self.IfaceDevIFace):
            self._fsType_ = o.fsType()
        else:
            self._fsType_ = str()
            
        return self._fsType_
        
    def label(self) -> str:
        # NOTE: 2025-02-11 23:09:16
        # see NOTE: 2025-02-11 22:30:02
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        # print(f"{self.__class__.__name__} o is a {type(o).__name__}")
        if isinstance(o, self.IfaceDevIFace):
            self._label_ = o.label()
        else:
            self._label_ = str()
            
        return self._label_
        
    def uuid(self) -> str:
        # NOTE: 2025-02-11 23:09:16
        # see NOTE: 2025-02-11 22:30:02
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        # print(f"{self.__class__.__name__} o is a {type(o).__name__}")
        if isinstance(o, self.IfaceDevIFace):
            self._uuid_ = o.uuid().lower()
        else:
            self._uuid_ = str()
            
        return self._uuid_
        
    def size(self) -> int:
        # NOTE: 2025-02-11 23:09:16
        # see NOTE: 2025-02-11 22:30:02
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        # print(f"{self.__class__.__name__} o is a {type(o).__name__}")
        if isinstance(o, self.IfaceDevIFace):
            self._size_ = o.size()
        else:
            self._size_ = 0
        
        return self._size_
    
    def encryptedContainer(self) -> Device:
        iface = self._d_.backendObject() # remember: a devices.interfaces.DeviceInterface
        if iface is not None:
            return Device(iface.encryptedContainerUdi())
        else:
            return Device()
    
