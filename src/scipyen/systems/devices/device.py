# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Work in progress, DO NOT USE
"""
# NOTE: 2025-02-10 17:40:56 solid/devices/frontend/...

# TODO 2025-02-06 11:42:09 Devices access in Scipyen
# Consider:
# • Linux: pyserial, pyusb, pyudev
# • Windows: pyserial, pyusb, pywin32, msdevices (https://github.com/Donny-GUI/msdevices), pyusb
# • MacOS: pyserial, pyusb, import glob; glob.glob('/dev/tty.*')
#
# • All platforms: PyQt5.QtCore.QStorageInfo

#
# For storage devices ONLY see also:
# • https://stackoverflow.com/questions/12672981/python-os-independent-list-of-available-storage-devices
# • dbus.SystemBus() NOT on MAcOS
#


# NOTE: 2025-02-06 11:49:13 as of this date & time:
# pyserial - for USB/RS-232C "dongles" - I use this for coolLED, see coolled_pe12.py
# pyusb - not used yet; might need to add user to the 'plugdev' group
# pywin32 - installed specifically when Scipyen installation scripts are run in Windows 
#           use by Scipyen when run in Windows
# pyudev -  not used
# msdevices - git repo, NOT on pypi;
#           maybe to install specifically when Scipyen installation scripts are run in Windows 
#           not used yet
#

# --------------
# NOTE: 2025-02-06 13:29:13 proposals for this module (using PyQt5)
# 
# Solid::DeviceManager ↦ pyudev.Context
# Solid::Device ↦ pyudev.Device
#
# monitor adding/removing mountable filesystems (i.e. hotpluggable):
# • Synchronously:
#   use pyudev.Monitor with an event filter e.g. monitor.filter_by("block")
#
# • Asynchronously (preferred):
#   use pyudev.MonitorObserver
#
# • Asynchronously in the GUI event loop (required, here):
#   use pyudev.pyqt5 (don't know yet if this would also work in PySide6):
#   WARNING: to avoid clashes import as alias:
#       from pyudev import pyqt5 as udevqt5
#       (or something like that)
#   then use, e.g.:
# from pyudev.pyside import MonitorObserver
# monitor = pyudev.Monitor.from_netlink(context)
# observer = MonitorObserver(monitor)
# observer.deviceEvent.connect(log_event)
# monitor.start()
# --------------

# --------------
# is using PySide6, consider:
# • PySide6.QtSensors
# • PySide6.QtSerialBus & PySide6.QtSerialPort
# • PySide6.QtDbus for IPC
# • QIODevice and QStorageInfo in PySide6.QtCore
# --------------

# --------------
# OK, now I need to understand what does Solid provide to the KIO
# --------------

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


__HAS_PYUDEV__ = False

try:
    import pyudev
    __HAS_PYUDEV__ = True
except:
    __HAS_PYUDEV__ = False

__module_path__ = os.path.abspath(os.path.dirname(__file__))

# class DeviceNotifier: pass # NOTE 2025-02-10 21:21:44 discard once finalised
# class _DeviceManager_: pass
# class _DeviceInterface_: pass
# class DeviceInterface: pass
# class _Device_: pass

from systems.devices.deviceinterface import (_DeviceInterface_, DeviceInterface)

class Predicate: pass
class DeviceManagerStorage: pass

IfaceDevice = typing.TypeVar("IfaceDevice")
IfaceDevIface = typing.TypeVar("IfaceDevIface")
IfaceDeviceManager = typing.TypeVar("IfaceDeviceManager")
DevIFaceType = typing.TypeVar("DevIFaceType")

    
global globalDeviceStorage
globalDeviceStorage = DeviceManagerStorage()
        
class _Device_(QtCore.QObject):
    # from systems.devices.interfaces.device import Device as IfaceDevice
    def __init__(self, udi:str):
        super().__init__()
        self._udi_:str = udi
        self._backendObject_:typing.Optional[QtCore.QObject] = None # interfaces.device.Device
        self._ifaces_:dict = dict() # DeviceInterface.Type ↦ IfaceDevIface
        
    def __del__(self):
        self.setBackendObject(None)
        
    def udi(self) -> str:
        return self._udi_
        
    @Slot(QtCore.QObject)
    def _k_destroyed(self, o:QtCore.QObject):
        self.setBackendObject(None)
        
    def backendObject(self) -> IfaceDevice | None:
        return self._backendObject_
    
    def setBackendObject(self, o:typing.Optional[QtCore.QObject]=None):
        if self._backendObject_ is not None:
            self._backendObject_.disconnect(self)
        self._backendObject_ = o
        
        if o is not None:
            o.destroyed.connect(self._k_destroyed)
            
        if len(self._ifaces_) > 0: # why this ?!?
            self._ifaces_.clear()
            self.deleteLater()
            
    def interface(self, devtype:DeviceInterface.Type) -> DeviceInterface | None:
        return self._ifaces_.get(devtype, None)
    
    def setInterface(self, devtype:DeviceInterface.Type, interface:DeviceInterface):
        self._ifaces_[devtype] = interface
            
class Device():
    def __init__(self, device_or_udi:typing.Union[typing.Self, str]=""):
        self._d_:typing.optional[_Device_] = None
        if isinstance(device_or_udi, str):
            manager = _DeviceManager_.instance()
            self._d_ = manager.findRegisteredDevice(device_or_udi)
             
        elif isinstance(device_or_udi, self.__class__):
             self._d_ = device_or_udi._d_ # I think this is what's intended
             
    
    def __eq__(self, other:typing.Self):
        pass
    
    @classmethod
    def allDevices(cls) -> list[typing.Self]:
        devList = list()
        backends = globalDeviceStorage.managerBackends()
        for backend in backends:
            udis = backend.allDevices()
            for udi in udis:
                devList.append(cls(udi))
        
        return devList
    
    @classmethod
    def listFromType(cls, devtype:DevIFaceType, parentUdi:str) -> list[typing.Self]:
        pass

    @classmethod
    def listFromQuery(cls, predicate:typing.Union[str, Predicate], parentUdi:str) -> list[typing.Self]:
        # TODO: 2025-02-11 12:49:24 Predicate
        if not isinstance(predicate, Predicate):
            if isinstance(predicate, str):
                predicate = Predicate.fromString(predicate)
        pass
    
    @classmethod
    def storageAccessFromPath(cls, path:str) -> typing.Self:
        pass
    
    def isValid(self) -> bool:
        pass
    
    def udi(self) -> str:
        pass
    
    def parentUdi(self) -> str:
        pass
    
    def parent(self) -> typing.Self:
        pass
    
    def vendor(self) -> str:
        pass
    
    def product(self) -> str:
        pass
    
    def icon(self) -> str:
        pass
    
    def emblems(self) -> list[str]:
        pass
    
    def displayName(self) -> str:
        pass
    
    def description(self) -> str:
        pass
    
    def isDeviceInterface(self, type:DevIFaceType) -> bool:
        pass
    
    def asDeviceInterface(self, type:DevIFaceType) -> DeviceInterface:
        pass
    
    # def as(self, type:DeviceInterfaceType) -> DevIface:
    #     return self.asDeviceInterface(type)
    
    # def is(self, type:DeviceInterfaceType) -> bool:
    #     returnn self.isDeviceInterface(type)

# class _DevicePredicateMultiMeta_(type(DeviceInterface), MultipleMeta): 
#     """Enables constructor overloading"""
#     pass


from systems.devices.devicemanager import DeviceManagerStorage
globalDeviceStorage = DeviceManagerStorage()
from systems.devices.deviceinterface import DeviceInterface
DevIFaceType = DeviceInterface.Type
from systems.devices.predicate import Predicate
from systems.devices.interfaces.device import Device as IfaceDevice
from systems.devices.interfaces.devicemanager import DeviceManager as IfaceDeviceManager
