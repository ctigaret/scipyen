# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Work in progress, DO NOT USE
"""
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

class DeviceInterfaceType(IntEnum):
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

    # @staticmethod
    # def instance():
    #     pass
    
class _DeviceManager_: pass

class _Device_(QtCore.QObject):
    def __init__(self, udi:str):
        super().__init__()
        self._udi_ = udi
        self._backendObject_ = None
        self._ifaces_ = dict()
        
    def __del__(self):
        self.setBackendObject(None)
        
    @Slot(QtCore.QObject)
    def slot_k_destroyed(self, o:QtCore.QObject):
        self.setBackendObject(None)
        
    def setBackendObject(self, o=None):
        if self._backendObject_ is not None:
            self._backendObject_.data.disconnect(self)
        self._backendObject_ = o
        
        if o is not None:
            o.destroyed.connect(self.slot_k_destroyed)
            
        if len(self._ifaces_) > 0:
            self._ifaces_.clear()
            self.deleteLater()
            
    def interface(self, devtype:DeviceInterfaceType) -> DeviceInterface | None:
        return self._ifaces_.get(devtype, None)
    
    def setInterface(self, devtype:DeviceInterfaceType, interface:DeviceInterface):
        self._ifaces_[devtype] = interface
            
class _DeviceManager_(DeviceNotifier, _ManagerBase_):
    def __init__(self):
        super(DeviceNotifier, self).__init__()
        self._nullDevice_ = _Device_("")
        self.loadBackends()
        backends = self.managerBackends()
        for backend in backends:
            pass # TODO
        
    @Slot(str)
    def _k_deviceAdded(self, udi:str):
        pass
    
    @Slot(str)
    def _k_deviceRemoved(self, udi:str):
        pass
    
    @Slot(QtCore.QObject)
    def _k_destroyed(self, o:QtCore.QObject):
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
        
class DeviceInterface(QtCore.QObject):
    def __init__(self, parent:typing.Optional[QtCore.QObject]=None):
        super().__init__(parent=parent)
        
        # ### BEGIN DeviceInterfacePrivate
        self.backendObject:QtCore.QObject = QtCore.QObject()
        self.devicePrivate:Device = Device() # DevicePrivate
        self._backendObject:typing.Optional[QtCore.QObject] = None
        self._devicePrivate:typing.Optional[Device] = None
        # ### END DeviceInterfacePrivate

        
    
class Device():
    def __init__(self, device :typing.Optional[typing.Self]=None):
        pass
        
