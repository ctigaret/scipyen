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
# from systems.devices.deviceinterface import (_DeviceInterface_, DeviceInterface, DeviceInterfaceType, Device, DevicePredicate)
from systems.devices.deviceinterface import (_DeviceInterface_, DeviceInterface)

class _StorageDrive_(_DeviceInterface_):
    def __init__(self):
        super().__init__()
        
class _StorageDriveMultiMeta_(type(DeviceInterface), MultipleMeta): 
    """Enables constructor overloading"""
    pass
    
class StorageDrive(DeviceInterface, metaclass = _StorageDriveMultiMeta_):
    Bus = TypeEnum("Bus", ["Ide", "Usb", "Ieee1394", "Scsi", "Sata", "Platform"])
    
    DriveType = TypeEnum("DriveType", ["HardDisk", "CdromDrive", "Floppy", "Tape", 
                                    "CompactFlash", "MemoryStick", "SmartMedia", "SdMmc", "Xd"])
    def __init__(self, backendObject:QtCore.QObject):
        super().__init__(_StorageDrive_(), backendObject)
        self._bus_:self.Bus = self.Bus.Ide
        self._setupDefaults_()
        
    def __init__(self, dd:_StorageDrive_, backendObject:QtCore.QObject):
        # initializes super()._d_ i.e. DeviceInterface._d_, which is a _DeviceInterface_
        super().__init__(dd, backendObject) 
        self._bus_:self.Bus = self.Bus.Platform
        self._setupDefaults_()
        
    def _setupDefaults_(self):
        self._driveType_:self.DriveType = self.DriveType.HardDisk
        self._removable_:bool = False
        self._hotpluggable_:bool = False
        self._inUse_:bool = False
        self._size_:int = 0
        self._timeDetected_:QtCore.QDateTime = QtCore.QDateTime()
        self._timeMediaDetected_:QtCore.QDateTime = QtCore.QDateTime()
        
        
    def bus(self) -> Bus:
        # from systems.devices.interfaces.device import StorageDrive as IfaceStorageDrive
        
        # NOTE: 2025-02-11 22:30:02
        # while still using PyQt5 could try and use sip.cast
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        # print(f"{self.__class__.__name__} o is a {type(o).__name__}")
        if isinstance(o, self.IfaceStorageDrive):
            self.self._bus_ = o.bus() # Method parameter of return_SOLID_CALL macro
        else:
            self._bus_ = self.Bus.Platform
            
        return self._bus_ # Default parameter of return_SOLID_CALL macro
        
    @staticmethod
    def deviceInterfaceType() -> DeviceInterface.Type:
        return DeviceInterface.Type.StorageDrive
    
    def driveType(self) -> DriveType:
        from systems.devices.interfaces.storagedrive import StorageDrive as IfaceStorageDrive
        # from systems.devices.interfaces.device import StorageDrive as IfaceStorageDrive
        # NOTE: 2025-02-11 23:09:16
        # see NOTE: 2025-02-11 22:30:02
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        # print(f"{self.__class__.__name__} o is a {type(o).__name__}")
        if isinstance(o, IfaceStorageDrive):
            self._driveType_ = o.driveType()
        else:
            self._driveType_ = self.DriveType.HardDisk  # Default parameter of return_SOLID_CALL macro
            
        return self._driveType_
    
    def isRemovable(self) -> bool:
        from systems.devices.interfaces.storagedrive import StorageDrive as IfaceStorageDrive
        # NOTE: 2025-02-11 23:09:16
        # see NOTE: 2025-02-11 22:30:02
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        self._removable_ = o.isRemovable() if isinstance(o, IfaceStorageDrive) else False
        return self._removable_
        
        # if isinstance(o, IfaceStorageDrive):
        #     self._removable_ = o.isRemovable()
        # else:
        #     self._removable_ = False
            
        
    def isHotPluggable(self) -> str:
        from systems.devices.interfaces.storagedrive import StorageDrive as IfaceStorageDrive
        # NOTE: 2025-02-11 23:09:16
        # see NOTE: 2025-02-11 22:30:02
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        self._hotpluggable_ = o.isHotPluggable() if isinstance(o, IfaceStorageDrive) else False
        return self._hotpluggable_
#         if isinstance(o, IfaceStorageDrive):
#             self._hotpluggable_ = o.isHotPluggable()
#         else:
#             self._hotpluggable_ = False
#             
#         return self._hotpluggable_
        
    def size(self) -> int:
        from systems.devices.interfaces.storagedrive import StorageDrive as IfaceStorageDrive
        # NOTE: 2025-02-11 23:09:16
        # see NOTE: 2025-02-11 22:30:02
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        self._size_ = o.size() if isinstance(o, IfaceStorageDrive) else 0
        return self._size_
            
#         if isinstance(o, IfaceStorageDrive):
#             self._size_ = o.size()
#         else:
#             self._size_ = 0
#         
#         return self._size_
    
    def isInUse(self) -> bool: # TODO
        from systems.devices.device import Device
        from systems.devices.interfaces.storagedrive import StorageDrive as IfaceStorageDrive
        from systems.devices.predicate import Predicate
        p = Predicate(DeviceInterface.Type.StorageAccess)
        iface = self._d_.backendObject() # remember: a devices.interfaces.DeviceInterface
        if iface is not None:
            return Device(iface.encryptedContainerUdi())
        else:
            return Device()
    
