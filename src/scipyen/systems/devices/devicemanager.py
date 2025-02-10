# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Work in progress, DO NOT USE
"""
# NOTE: 2025-02-10 17:38:45 solid/devices/frontend/devicemanager 

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

class _Device_: pass
class Device: pass

class _DeviceManager_(DeviceNotifier, _ManagerBase_):
    from systems.devices.device import _Device_, Device
    def __init__(self):
        super(_ManagerBase_, self).__init__()
        super(DeviceNotifier, self).__init__()
        self._nullDevice_ = _Device_("")
        # NOTE: 2025-02-09 22:51:23
        # should I use weakref as _devicesMap_ values, here ?!?
        self._devicesMap_ = dict() # str ↦ _Device_
        self._reverseMap_ = dict() # QObject ↦ str
            
        self.loadBackends()
        backends = self.managerBackends() # _ManagerBase_
        for backend in backends:
            backend.deviceAdded.connect(self._k_deviceAdded)
            backend.deviceRemoved.connect(self._k_deviceRemoved)
            # pass # TODO
        
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
        pass
    
    @Slot(str)
    def _k_deviceRemoved(self, udi:str):
        pass
    
    @Slot(QtCore.QObject)
    def _k_destroyed(self, o:QtCore.QObject):
        pass
    
    def createBackendObject(self, udi:str) -> Device:
        pass

class DeviceManagerStorage:
    def __init__(self):
        self._storage_ = None
        
    def managerBackends(self) -> list():
        pass
    
    def notifier(self) -> DeviceNotifier:
        pass
    
    def ensureManagerCreated(self):
        pass
    
    
class DeviceManager(QtCore.QObject):
    # abstract base class
    deviceAdded = Signal(str, name="deviceAdded") # parameter is the udi
    deviceRemoved = Signal(str, name="deviceRemoved") # parameter is the udi
    
    def __init__(self, parent:typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        
    @abstractmethod
    def udiPrefix() -> str:
        pass
    
    @abstractmethod
    def supportedInterfaces(sel) -> set:
        pass
    
    @abstractmethod
    def allDevices(self) -> list[str]:
        return list()
    
    @abstractmethod
    def devicesFromQuery(self, parentUdi:str, ):
        pass
        

        
