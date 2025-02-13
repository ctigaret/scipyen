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

class DeviceNotifier: pass # NOTE 2025-02-10 21:21:44 discard once finalised
class _DeviceManager_: pass
class _DeviceInterface_: pass
class DeviceInterface: pass
class _Device_: pass
class Device: pass
class DevicePredicate: pass

class ParsingData:
    def __init__(self):
        self.result:typing.Optional[DevicePredicate] = None
        self.bfr:typing.Optional[QtCore.QByteArray] = None
        
IFaceDevice = typing.TypeVar("IFaceDevice")
IFaceDeviceManager = typing.TypeVar("IFaceDeviceManager")
    
class _ManagerBase_:
    # from systems.devices.interfaces.device import Device as IFaceDevice
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
    
global globalDeviceStorage
globalDeviceStorage = DeviceManagerStorage()
        
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
    def instance(cls) -> typing.Self: # NOTE: Singleton design pattern
        # return globalDeviceStorage.notifier()
        if not hasattr(cls, "__instance__") or not isinstance(cls.__instance__, cls):
            cls.__instance__ = globalDeviceStorage.notifier()
            if cls.__instance__ is None:
                inst = cls(*args, **kwargs)
                for subclass in cls._walk_mro():
                    subclass.__instance__ = inst
                    
        return cls.__instance__
        # if hasattr(cls, "__instance__") and isinstance(cls.__instance__, cls):
        #     return cls.__instance__
        # else:
        #     raise RuntimeError(f"Incompatible sibling of '{cls.__name__}' is already instantiated as singleton: {type(cls.__instance__).__name__}")

    # @classmethod
    # def instance(cls:typing.Self, *args, **kwargs) -> typing.Self: # NOTE: Singleton design pattern
    #     if cls.__instance__ is None:
    #         inst = cls(*args, **kwargs)
    #         for subclass in cls._walk_mro():
    #             subclass.__instance__ = inst
    #     if hasattr(cls, "__instance__") and isinstance(cls.__instance__, cls):
    #         return cls.__instance__
    #     else:
    #         raise RuntimeError(f"Incompatible sibling of '{cls.__name__}' is already instantiated as singleton: {type(cls.__instance__).__name__}")
    # 

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
    
# class _Device_:pass # CAUTION - remove if importing, below

class _DeviceInterface_:
    # from systems.devices.device import (_Device_, Device)
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
    def deviceInterfaceype() -> DeviceInterfaceType:
        return DeviceInterfaceType.Unknown
        
    def isValid(self) -> bool:
        if isinstance(self._d_, _DeviceInterface_) and isinstance(backendObject, QtCore.QObject):
            return self._d_.backendObject() is not None
        else:
            return False
    
    @staticmethod
    def typeToString(type:DeviceInterfaceType) -> str:
        return type.name
        
    @staticmethod
    def stringToType(type:str) -> DeviceInterfaceType:
    # def stringToType(self, type:str) -> DeviceInterfaceType:
        return DeviceInterfaceType.namevalue(type)
    
    @staticmethod
    def typeDescription(type:DeviceInterfaceType):
    # def typeDescription(self, type:DeviceInterfaceType):
        match (type):
            case DeviceInterfaceType.DeviceInterfaceType.Unknown:
                return "Unknown"
            case DeviceInterfaceType.DeviceInterfaceType.GenericInterface:
                return "Generic Interface"
                # return tr("Generic Interface", "Generic Interface device type");
            case DeviceInterfaceType.Processor:
                return "Processor"
                # return tr("Processor", "Processor device type");
            case DeviceInterfaceType.Block:
                return "Block Device"
                # return tr("Block", "Block device type");
            case DeviceInterfaceType.StorageAccess:
                return "Storage Access Device"
                # return tr("Storage Access", "Storage Access device type");
            case DeviceInterfaceType.StorageDrive:
                return "Storage Drive"
                # return tr("Storage Drive", "Storage Drive device type");
            case DeviceInterfaceType.OpticalDrive:
                return "Optical Drive"
                # return tr("Optical Drive", "Optical Drive device type");
            case DeviceInterfaceType.StorageVolume:
                return "Storage Volume"
                # return tr("Storage Volume", "Storage Volume device type");
            case DeviceInterfaceType.OpticalDisc:
                return "Optical Disc"
                # return tr("Optical Disc", "Optical Disc device type");
            case DeviceInterfaceType.Camera:
                return "Camera"
                # return tr("Camera", "Camera device type");
            case DeviceInterfaceType.PortableMediaPlayer:
                return "Portable Media Player"
                # return tr("Portable Media Player", "Portable Media Player device type");
            case DeviceInterfaceType.Battery:
                return "Battery"
                # return tr("Battery", "Battery device type");
            case DeviceInterfaceType.NetworkShare:
                return "Network Share"
                # return tr("Network Share", "Network Share device type");
            case DeviceInterfaceType.Last:
                return str()
                # return QString();
                
            case _:
                return str()
            
        return str()
        # return QString();
        


class _Device_(QtCore.QObject):
    # from systems.devices.interfaces.device import Device as IFaceDevice
    # from systems.devices.deviceinterface import (DeviceInterfaceType, DeviceInterface)
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
    # from systems.devices.devicemanager import (DeviceManagerStorage, DeviceManager)
    # from systems.devices.deviceinterface import (DeviceInterface, DeviceInterfaceType)
    DevIface = typing.TypeVar("DevIFace", bound="DeviceInterface")


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
    def listFromType(cls, devtype:DeviceInterfaceType, parentUdi:str) -> list[typing.Self]:
        pass

    @classmethod
    def listFromQuery(cls, predicate:typing.Union[str, DevicePredicate], parentUdi:str) -> list[typing.Self]:
        # TODO: 2025-02-11 12:49:24 DevicePredicate
        if not isinstance(predicate, DevicePredicate):
            if isinstance(predicate, str):
                predicate = DevicePredicate.fromString(predicate)
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
    
    def isDeviceInterface(self, type:DeviceInterfaceType) -> bool:
        pass
    
    def asDeviceInterface(self, type:DeviceInterfaceType) -> DeviceInterface:
        pass
    
    # def as(self, type:DeviceInterfaceType) -> DevIface:
    #     return self.asDeviceInterface(type)
    
    # def is(self, type:DeviceInterfaceType) -> bool:
    #     returnn self.isDeviceInterface(type)

# class _DevicePredicateMultiMeta_(type(DeviceInterface), MultipleMeta): 
#     """Enables constructor overloading"""
#     pass

class DevicePredicate(metaclass = MultipleMeta):
    ComparisonOperator = TypeEnum("ComparisonOperator", ["Equals", "Mask"])
    Type = TypeEnum("Type", ["PropertyCheck", "Conjunction", "Disjunction", "InterfaceCheck"])
    
    class Private:
        def __init__(self):
            self._isValid_:bool = False
            self._type_:DevicePredicate.Type = DevicePredicate.Type.PropertyCheck
            self._compOperator_:DevicePredicate.ComparisonOperator = DevicePredicate.ComparisonOperator.Equals
            self._operand1_:typing.Optional[self.__class__] = None
            self._operand1_:typing.Optional[self.__class__] = None
            self._ifaceType_:DeviceInterfaceType = DeviceInterfaceType.Unknown
            self._property_:str = str()
            # self._value_:object = None
            self._value_:QtCore.QVariant = QtCore.QVariant()
    
    def __init__(self):
        self._d_ = self.Private()
        
    def __init__(self, other:DevicePredicate):
        self._d_ = other._d_
        
    def __init__(self, ifaceType:DeviceInterfaceType, prop:str, value:QtCore.QVariant, compOperator: ComparisonOperator = ComparisonOperator.Equals):
        self._d_ = self.Private()
        self._d_._isValid_ = True
        self._d_._ifaceType_ = ifaceType
        self._d_._property_ = prop
        self._d_._value_ = value
        self._d_._type_ = self.Type.PropertyCheck
        self._d_._compOperator_ = compOperator
        
    def __init__(self, ifaceName:str, prop:str, value:QtCore.QVariant, compOperator: ComparisonOperator = ComparisonOperator.Equals):
        self._d_ = self.Private()
        ifaceType = DeviceInterfaceType.stringToType(ifaceName) 
        if ifaceType != -1:
            self._d_._isValid_ = True
            self._d_._ifaceType_ = ifaceType
            self._d_._property_ = prop
            self._d_._value_ = value
            self._d_._type_ = self.Type.PropertyCheck
            self._d_._compOperator_ = compOperator
            
    def __init__(self, ifaceType:DeviceInterfaceType):
        self._d_ = self.Private()
        self._d_._isValid_ = True
        self._d_._type_ = self.Type.InterfaceCheck
        self._d_._ifaceType_ = ifaceType
        
    def __init__(self, ifaceName:str):
        self._d_ = self.Private()
        ifaceType = DeviceInterfaceType.stringToType(ifaceName)
        if ifaceType != -1:
            self._d_._isValid_ = True
            self._d_._type_ = self.Type.InterfaceCheck
            self._d_._ifaceType_ = ifaceType
            
    def __del__(self):
        if hasattr(self, "_d_") and self._d_._type_ != self.Type.PropertyCheck and self._d_._type_ != self.Type.InterfaceCheck:
            self._d_._operand1_ = None
            self._d_._operand2_ = None
            
        self._d_ = None
        
    def __and__(self, other:typing.Self):
        """ operator&"""
        result = self.__class__()
        result._d_._isValid_ = True
        result._d_._type_ = self.Type.Conjunction
        
        # CAUTION 2025-02-12 22:20:58
        result._d_._operand1_ = self
        result._d_._operand2_ = other
        
        return result
    
    def __iand__(self, other:typing.Self):
        """ operator&="""
        self = self & other
        return self
    
    def __or__(self, other:typing.Self):
        """ operator| """
        result = self.__class__()
        result._d_._isValid_ = True
        result._d_._type_ = self.Type.Disjunction
        
        # CAUTION 2025-02-12 22:20:58
        result._d_._operand1_ = self
        result._d_._operand2_ = other
        
        return result
    
    def __ior__(self, other:typing.Self):
        """ operator|= """
        self = self | other
        return self
        
    def copy(self) -> typing.Self: 
        # ? use as assignment operator (operator= in C++)
        self._d_._isValid_ = other._d_._isValid_
        self._d_._type_ = other._d._type_
        
        if self._d_._type_ != self.Type.PropertyCheck and self._d_._type_ != self.Type.InterfaceCheck:
            self._d_._operand1_ = other._d_._operand1_
            self._d_._operand2_ = other._d_._operand2_
        else:
            self._d_._ifaceType_ = other._d_._ifaceType_
            self._d_._property_ = other._d_._property_
            self._d_._value_ = other._d_._value_
            self._d_._compOperator_ = other._d_._compOperator_
            
        return self
    
    def isValid(self) -> bool:
        return self._d_._isValid_
    
    def matches(self, device:Device) -> bool:
        if not self._d_._isValid_:
            return False
        
        match (self._d_._type_):
            case self.Type.Disjunction:
                return self._d_._operand1_.matches(device) or self._d_._operand2_.matches(device)
            case self.Type.Conjunction:
                return self._d_._operand1_.matches(device) and self._d_._operand2_.matches(device)
            case self.Type.PropertyCheck:
                iface = device.asDeviceInterface(self._d_._ifaceType_)
                if iface is not None:
                    index = iface.metaObject().indexOfProperty(self._d_._property_)
                    if index  == -1:
                        return False # ?!?
                    metaProp = iface.metaObject().property(index)
                    value = metaProp.read(iface) if metaProp.isReadable() else QVariant()
                    expected = self._d_._value_
                    if metaProp.isEnumType() and expected.userType() == QtCore.QMetaType.QString:
                        metaEnum = metaProp.enumerator()
                        value = metaEnum.keysToValue(self._d_._value_.value())
                        if value >= 0:
                            expected = QtCore.QVariant(value)
                        else:
                            expected = QtCore.QVariant()
                            
                    elif metaProp.isEnumType() and expected.userType() == QtCore.QMetaType.Int:
                        expectedValue = expected.value()
                        expected = QtCore.QVariant(expectedValue)
                
                    if self._d_._compOperator_ == self.ComparisonOperator.Mask:
                        v_ok = False
                        try:
                            v = int(value.value())
                            v_ok = True
                        except:
                            v_ok = False
                            
                        e_ok = False
                        try:
                            e = int(excepted.value())
                            e_ok = True
                        except:
                            e_ok = False
                        
                        return e_ok and v_ok and (v & e) # ?!?
                    
                    if value == expected:
                        return True
                    
                    if isinstance(value.value(), (typing.Set, typing.Sequence)):
                        for element in value.value():
                            if element == expected:
                                return True
                # break
            
            case self.Type.InterfaceCheck:
                return device.isDeviceInterface(self._d_._ifaceType_)
            case _:
                return False
            
        return False
            
    def usedTypes(self) -> set[DeviceInterfaceType]:
        res = set()
        if self._d_._isValid_:
            match (self._d_._type_):
                case self.Type.Disjunction:
                    pass
                case self.Type.Conjunction:
                    res |= self._d_._operand1_.usedTypes()
                    res |= self._d_._operand2_.usedTypes()
                    # break
                case self.Type.PropertyCheck:
                    pass
                case self.Type.InterfaceCheck:
                    res.add(self._d_._ifaceType_)
                    # break
                case _:
                    pass
                
        return res
                    
    def toString(self) -> str:
        if not self._d_._isValid_:
            return "False"
        
        if self._d_._type_ not in (self.Type.PropertyCheck, self.Type.InterfaceCheck):
            op = "OR" if self._d_._type_ == self.Type.Disjunction else "AND"
            return f"[{self._d_._operand1_.toString()} {op} {self._d_._operand2_.toString()}]"
        
        else:
            ifaceName = DeviceInterface.typeToString(self._d_._ifaceType_)
            if len(ifaceName) == 0:
                ifaceName = "Unknown"
                
            if self._d_._type_ == self.Type.InterfaceCheck:
                return f"IS {ifaceName}"
            
            v = self._d_._value_.value()
            
            ret = str()
            
            if isinstance(v, (tuple, list, deque)) and all(isinstance(v_, str) for v_ in v):
                if len(v) == 0:
                    ret = "{}"
                else:
                    ret = "{" + ', '.join(v) + "}"
                    
            elif isinstance(v, bool):
                ret = "True" if v else "False"
                
            elif isinstance(v, int):
                ret = f"{v}"
                
            else:
                ret = f"{v}"
                
            str_operator = "==" if self._d_._compOperator_ == self.ComparisonOperator.Equals else " &"
            
            return f"{ifaceName}.{self._d_._property_} {str_operator} {ret}"
                
#         Q_GLOBAL_STATIC(QThreadStorage<Solid::PredicateParse::ParsingData *>, s_parsingData)
# 
#         Solid::Predicate Solid::Predicate::fromString(const QString &predicate)
#         {
#             Solid::PredicateParse::ParsingData *data = new Solid::PredicateParse::ParsingData();
#             // above, data is a ParsingData with two fields:
#             // bfr - a QByteArray
#             // result - a Predicate object
#             s_parsingData->setLocalData(data);   // set this up as a QThreadStorage
#             data->buffer = predicate.toLatin1(); // predicate is a str; set it to ParsingData
#                                                 // data's buffer'
#             PredicateParse_mainParse(data->buffer.constData()); // bison parse the ParsingData's buffer
#                                                                 // my guess here is that PredicateParse_mainParse
#                                                                 // assigns a new Predicate to data's result
#             Predicate result; // set up a new Predicate
#             if (data->result) { // ParsingData has a result (a Predicate), then:
#                 result = Predicate(*data->result); // assign this to the Predicate object to return
#                 delete data->result;               // and delete ParsingData's result
#             }
#             s_parsingData->setLocalData(nullptr);  // release parginb data from the QThreadStorage
#             return result;
#         } 
#             
    @classmethod
    def fromString(cls, predicate:str) -> DevicePredicate:
        # NOTE: 2025-02-13 15:55:55 TODO
        data = ParsingData()
        data.bfr = QtCore.QByteArray(predicate.encode())
        result = cls()
        if isinstance(data.result, cls):
            pass
    
    def type(self) -> Type:
        return self._d_._type_
    
    def interfaceType(self) -> DeviceInterfaceType:
        return self._d_._ifaceType_
    
    def propertyName(self) -> str:
        return self._d_._property_
    
    def matchingValue(self) -> QtCore.QVariant:
        return self._d_._value_
    
    def comparisonOperator(self) -> ComparisonOperator:
        return self._d_._compOperator_
    
    def firstOperand(self) -> typing.Self:
        return self._d_._operand1_ if isinstance(self._d_._operand1_, self.__class__) else self.__class__()
    
    def secondOperand(self) -> typing.Self:
        return self._d_._operand2_ if isinstance(self._d_._operand2_, self.__class__) else self.__class__()


from systems.devices.interfaces.device import Device as IFaceDevice
from systems.devices.interfaces.device import DeviceManager as IFaceDeviceManager
