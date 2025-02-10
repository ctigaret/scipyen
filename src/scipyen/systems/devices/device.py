# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Work in progress, DO NOT USE
"""
# NOTE: 2025-02-10 17:40:56 solid/devices/frontend/device

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
from urllib.parse import urlparse, urlsplit
from collections import namedtuple
from abc import ABCMeta, abstractmethod
from enum import Enum, IntEnum
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

__HAS_PYUDEV__ = False

try:
    import pyudev
    __HAS_PYUDEV__ = True
except:
    __HAS_PYUDEV__ = False

__module_path__ = os.path.abspath(os.path.dirname(__file__))

# class DeviceInterfaceType(IntEnum):
#     """"""
#     # NOTE: 2025-01-03 14:09:24 
#     # Solid DeviceInterface::Type
#     Unknown = 0,
#     GenericInterface = 1,
#     Processor = 2,
#     Block = 3,
#     StorageAccess = 4,
#     StorageDrive = 5,
#     OpticalDrive = 6,
#     StorageVolume = 7,
#     OpticalDisc = 8,
#     Camera = 9,
#     PortableMediaPlayer = 10,
#     Battery = 12,
#     NetworkShare = 14,
#     Last = 0xffff,
    
class _ManagerBase_:
    def __init__(self):
        self._backends_:list = list()
        
    def __del__(self):
        self._backends_.clear()
        
    def managerBackends(self)->list:
        return self._backends_
        
    def loadBackends(self):
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
        
        
class DeviceNotifier(QtCore.QObject):
    # singleton design pattern
    __instance__:typing.Optional[typing.Self] = None
    deviceAdded = Signal(str, name="deviceAdded") # parameters is an udi
    deviceRemoved = Signal(str, name="deviceRemoved") # parameters is an udi
    
    def __new__(cls:typing.Self, *args, **kwargs) -> typing.Self:
        if not hasattr(cls, "__instance__") or not isinstance(cls.__instance__, cls):
            cls.__instance__ = super(DeviceNotifier, cls).__new__(cls, *args, **kwargs)
            
        return cls.__instance__
    
    def __init__(self, parent:typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self.__instance__ = self
    
    @classmethod
    def _walk_mro(cls) -> typing.Generator[typing.Self, None, None]: # NOTE: Singleton design pattern
        for subclass in cls.mro():
            if (
                issubclass(cls, subclass)
                and issubclass(subclass, typing.Self)
                and subclass != typing.Self
            ):
                yield subclass
                
    @classmethod
    def initialized(cls:typing.Self) -> bool: # NOTE: Singleton design pattern
        return hasattr(cls, "__instance__" and isinstance(cls.__instance__, cls))
    
    @classmethod
    def instance(cls:typing.Self, *args, **kwargs) -> typing.Self: # NOTE: Singleton design pattern
        if cls.__instance__ is None:
            inst = cls(*args, **kwargs)
            for subclass in cls._walk_mro():
                subclass.__instance__ = inst
        if hasattr(cls, "__instance__") and isinstance(cls.__instance__, cls):
            return cls.__instance__
        else:
            raise RuntimeError(f"Incompatible sibling of '{cls.__name__}' is already instantiated as singleton: {type(cls.__instance__).__name__}")

class _DeviceManager_: pass
class DeviceInterface: pass
class Device: pass

class _Device_(QtCore.QObject):
    from systems.devices.interface.device import Device as IFaceDevice
    from systems.devices.deviceinterface import (DeviceInterfaceType, DeviceInterface)
    def __init__(self, udi:str):
        super().__init__()
        self._udi_:str = udi
        self._backendObject_:typing.Optional[IFaceDevice] = None # interfaces.device.Device
        self._ifaces_:dict = dict() # DeviceInterfaceType ↦ DeviceInterface
        
    def __del__(self):
        self.setBackendObject(None)
        
    def udi(self) -> str:
        return self._udi_
        
    @Slot(QtCore.QObject)
    def slot_k_destroyed(self, o:QtCore.QObject):
        self.setBackendObject(None)
        
    def backendObject(self) -> IFaceDevice | None:
        return self._backendObject_
    
    def setBackendObject(self, o:typing.Optional[IFaceDevice]=None):
        if self._backendObject_ is not None:
            self._backendObject_.disconnect(self)
        self._backendObject_ = o
        
        if o is not None:
            o.destroyed.connect(self.slot_k_destroyed)
            
        if len(self._ifaces_) > 0: # why this ?!?
            self._ifaces_.clear()
            self.deleteLater()
            
    def interface(self, devtype:DeviceInterfaceType) -> DeviceInterface | None:
        return self._ifaces_.get(devtype, None)
    
    def setInterface(self, devtype:DeviceInterfaceType, interface:DeviceInterface):
        self._ifaces_[devtype] = interface
            
    
class Device():
    from systems.devices.devicemanager import (DeviceManagerStorage, DeviceManager)
    from systems.devices.predicate import Predicate # TODO: 2025-02-10 18:30:03 needs done
    def __init__(self, device:typing.Optional[typing.Self]=None):
        pass
    
    @classmethod
    def allDevices(cls) -> list[typing.Self]:
        # NOTE: 2025-02-10 18:04:38 TODO 
        # needs DeviceManager and DeviceManagerStorage
        pass
    
    @classmethod
    def listFromQuery(cls, predicate:typing.Union[str, Predicate], parentUdi:str) -> list[typing.Self]:
        pass
    
    @classmethod
    def listFromType(cls, devtype:DeviceInterfaceType, parentUdi:str) -> list[typing.Self]:
        pass
        
