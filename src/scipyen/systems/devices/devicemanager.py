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

from systems.devices.devicenotifier import DeviceNotifier
class IFaceDeviceManager:pass
class IFaceDevice:pass
class _Device_:pass

class _ManagerBase_:
    def __init__(self):
        self._backends_:list[IFaceDeviceManager] = list()
        
    def __del__(self):
        self._backends_.clear()
        
    def managerBackends(self)->list[IFaceDeviceManager]:
        return self._backends_
        
    def loadBackends(self):
        # NOTE: 2025-02-10 22:45:55
        # a backend is a interfaces object!
        solidFakeXml = os.environ.get("SOLID_FAKEHW")
        if isinstance(solidFakeXml, str) and len(solidFakeXml) > 0:
            pass # TODO backends/FakeManager
        else:
            pass # TODO backends/FstabManager
        
        # TODO: backends/IMobileManager
        # TODO: backends/IOKitManager
        # TODO: backends/UDevManager
        
        solidDisableUdisks2 = os.environ.get("SOLID_DISABLE_UDISKS2")
        if not isinstance(solidDisableUdisks2, str) or len(solidDisableUdisks2) == 0:
            pass # TODO backends/Udisks2Manager
        
        # solidDisableUpower # skip this
        
        if sys.platform == "win32":
            pass # TODO backends/WinDeviceManager
        
class DeviceManagerStorage:
    def __init__(self):
        self._storage_:typing.Optional[_DeviceManager_] = None
        
    def managerBackends(self) -> list():
        self.ensureManagerCreated()
        return self._storage_.managerBackends()
    
    def notifier(self) -> DeviceNotifier:
        # returns a _DeviceManager_, which is a DeviceNotifier
        self.ensureManagerCreated()
        return self._storage_
    
    def ensureManagerCreated(self):
        if not isinstance(self._storage_, _DeviceManager_):
            self._storage_ = _DeviceManager_() # hmmm...
    
class _DeviceManager_(DeviceNotifier, _ManagerBase_):
    def __init__(self):
        super(_ManagerBase_, self).__init__()
        super(DeviceNotifier, self).__init__()
        self._nullDevice_ = _Device_("")
        # NOTE: 2025-02-09 22:51:23
        # should I use weakref as _devicesMap_ values, here ?!?
        self._devicesMap_ = dict() # udi:str ↦ _Device_
        self._reverseMap_ = dict() # QObject ↦ udi:str
            
        self.loadBackends() # def in _ManagerBase_
        
        backends = self.managerBackends() # list[_ManagerBase_.IFaceDevice] WARNING
        
        for backend in backends:
            backend.deviceAdded.connect(self._k_deviceAdded)
            backend.deviceRemoved.connect(self._k_deviceRemoved)
        
    def __del__(self):
        backends = self.managerBackends()
        for backend in backends:
            backend.deviceAdded.disconnect(self._k_deviceAdded)
            backend.deviceRemoved.disconnect(self._k_deviceRemoved)
            
        # NOTE: 2025-02-09 22:51:23
        # should I use weakref as _devicesMap_ values, here ?!?
        self._devicesMap_.clear()
        
    @Slot(str)
    def _k_deviceAdded(self, udi:str):
        if udi in self._devicesMap_:
            dev = self._devicesMap_[udi]
            if dev and dev.backendObject() is None:
                dev.setBackendObject(self.createBackendObject(udi))
                assert dev.backendObject() is not None
                
        self.deviceAdded.emit(udi)
    
    @Slot(str)
    def _k_deviceRemoved(self, udi:str):
        if udi in self._devicesMap_:
            dev = self._devicesMap_[udi]
            
            if dev:
                dev.setBackendObject(None)
                
        self.deviceRemoved.emit(udi)
    
    @Slot(QtCore.QObject)
    def _k_destroyed(self, o:QtCore.QObject):
        udi = self._reverseMap_.pop(o, None)
        if isinstance(udi, str) and len(udi):
            self._devicesMap_.pop(udi)
    
    def createBackendObject(self, udi:str) -> IFaceDevice | None:
        backends = globalDeviceStorage.managerBackends()
        for backend in backends:
            # backend is a devices.interfaces.device.DeviceManager
            if not udi.startsWith(backend.udiPrefix()):
                continue
            
            iface = backend.createDevice(udi) # a devices.interfaces.device.DeviceInterface (QObject)
            
            return iface
    
    def findRegisteredDevice(self, udi:str) -> _Device_:
        if len(udi) == 0:
            return self._nullDevice_
        
        elif udi in self._devicesMap_:
            return self._devicesMap_[udi]
        
        else:
            iface = self.createBackendObject(udi) # and IFaceDevice
            devData = _Device_(udi)
            devData.setBackendObject(iface)
            self._devicesMap_[udi] = devData
            self._reverseMap_[deviceData] = udi
            devData.destroyed.connect(self._k_destroyed)
            return devData

class DeviceManager(QtCore.QObject):
    # abstract base class
    deviceAdded = Signal(str, name="deviceAdded") # parameter is the udi
    deviceRemoved = Signal(str, name="deviceRemoved") # parameter is the udi
    
    def __init__(self, parent:typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        
    @abstractmethod
    def udiPrefix() -> str: pass
    
    @abstractmethod
    def supportedInterfaces(sel) -> set: pass
    
    @abstractmethod
    def allDevices(self) -> list[str]: 
        return list()
    
    @abstractmethod
    def devicesFromQuery(self, parentUdi:str, ): pass
    
from systems.devices.interfaces.device import Device as IFaceDevice
from systems.devices.device import _Device_
from systems.devices.interfaces.devicemanager import DeviceManager as IFaceDeviceManager
