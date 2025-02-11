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

has_qtdbus = False
try:
    from qtpy import QtDBus
    has_qtdbus = True
except:
    pass

from core.datatypes import TypeEnum
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

# class DeviceInterfaceType: pass
DevIType = typing.TypeVar("DevIType")
DevITypeUnknown = typing.TypeVar("DevITypeUnknown")
StoVolUseType = typing.TypeVar("StoVolUseType")

class DeviceInterface(QtCore.QObject):
    def __init__(self):
        super().__init__()

class DeviceManager(QtCore.QObject):
    # from systems.devices.device import DeviceInterfaceType
    # abstract base class
    deviceAdded = Signal(str, name="deviceAdded") # parameter is the udi
    deviceRemoved = Signal(str, name="deviceRemoved") # parameter is the udi
    
    def __init__(self, parent:typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        
    @abstractmethod
    def udiPrefix() -> str:
        pass
    
    @abstractmethod
    def supportedInterfaces(sel) -> set[DevIType]:
        pass
    
    @abstractmethod
    def allDevices(self) -> list[str]:
        pass
    
    @abstractmethod
    def devicesFromQuery(self, parentUdi:str, 
                         type:DevIType = DevITypeUnknown) -> list[str]:
        pass
    
    @abstractmethod
    def createDevice(self, udi:str) -> QtCore.QObject:
        pass
    
class GenericInterface(QtCore.QObject):
    propertyChanged = Signal(dict, name="propertyChanged") # emits dict[str, int]
    conditionRaised = Signal(str, str, name="conditionRaised") # emits condition, reason
    
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def property(self, key:str) -> object:
        pass
    
    @abstractmethod
    def allProperties(self) -> dict:
        pass
    
    @abstractmethod
    def propertyExists(self, key:str) -> bool:
        pass
    
class Device(QtCore.QObject):
    # from systems.devices.device import DeviceInterfaceType
    
    def __init__(self, parent:typing.Optional[QtCore.QObject]=None):
        super().__init__(parent=parent)
    
    @abstractmethod
    def udi(self) -> str:
        pass
    
    @abstractmethod
    def parentUdi(self) -> str:
        return str()
    
    @abstractmethod
    def vendor(self) -> str:
        pass
    
    @abstractmethod
    def product(self) -> str:
        pass
    
    @abstractmethod
    def icon(self) -> str:
        pass
    
    @abstractmethod
    def emblems(self) -> list[str]:
        pass
    
    @abstractmethod
    def displayName(self) -> str:
        return self.description()
    
    @abstractmethod
    def description(self) -> str:
        pass
    
    @abstractmethod
    def queryDeviceInterface(self, devtype:DevIType) -> bool:
        pass
    
    @abstractmethod
    def createDeviceInterface(self, devtype:DevIType) -> QtCore.QObject:
        pass
    
    def registerAction(self, actionName:str, requestSlot:Slot, doneSlot:Slot):
        if has_qtdbus:
            # NOTE: 2025-02-09 23:33:01
            # QDBusConnection.connect(service:str, path:str, interface:str,
            #                           name:str, slot:Slot)
            service = str()
            path = self.deviceDBusPath()
            interface = "org.Scipyen.Device"
            requestedName = f"{actionName}Requested"
            doneName = f"{actionName}Done"
            QtDBus.QDBusConnection.sessionBus().connect(service, path, interface,
                                                        requestedName, requestSlot)
            QtDBus.QDBusConnection.sessionBus().connect(service, path, interface,
                                                        doneName, doneSlot)
    
    def broadcastActionRequested(self, actionName:str):
        if has_qtdbus:
            path = self.deviceDBusPath()
            interface = "org.Scipyen.Device"
            name = f"{actionName}Requested"
            signal = QtDBus.QDBusMessage.createSignal(path, interface, name)
            QtDBus.QDBusConnection.sessionBus().send(signal)
            
    def broadCastActionDone(self, actionName:str, error:int, errorString:str = ""):
        if has_qtdbus:
            path = self.deviceDBusPath()
            interface = "org.Scipyen.Device"
            name = f"{actionName}Done"
            signal = QtDBus.QDBusMessage.createSignal(path, interface, name) << errorString
            QtDBus.QDBusConnection.sessionBus().send(signal)
            
    def deviceDBusPath(self) -> str:
        encodedUdi = QtCore.QByteArray(self.udi().encode()).toPercentEncoding(QtCore.QByteArray(), b".~-", "_")
        return f"/org/Scipyen/Device_{bytearray(encodedUdi).decode()}"
    
class StorageAccess(DeviceInterface):
    from systems.devices.errors import ErrorType
    repairRequested = Signal(str, name="repairRequested", arguments=["udi"]) # emits an udi:str
    repairDone = Signal(ErrorType, object, str, name = "repairDone", arguments=["error", "resultData", "udi"])
    teardownRequested = Signal(str, name="teardownRequested", arguments=["udi"])
    setupRequested = Signal(str, name="setupRequested", arguments = ["udi"])
    teardownDone = Signal(ErrorType, object, str, name="teardownDone", arguments=["error", "resultData", "udi"])
    setupDone = Signal(ErrorType, object, str, name="setupDone", arguments=["error", "resultData", "udi"])
    accessibilityChanged = Signal(bool, str, name="accessibilityChanged", arguments=["accessible", "udi"])
    
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def isAccessible(self) -> bool:
        pass
    
    @abstractmethod
    def filePath(self) -> str:
        pass
    
    @abstractmethod
    def isIgnored(self) -> bool:
        pass
    
    @abstractmethod
    def isEncrypted(self) -> bool:
        pass
    
    @abstractmethod
    def setup(self) -> bool:
        pass
    
    @abstractmethod
    def teardown(self) -> bool:
        pass
    
    @abstractmethod
    def canCheck(self) -> bool:
        return False
    
    @abstractmethod
    def check(self) -> bool:
        return False
    
    @abstractmethod
    def canRepair(self) -> bool:
        return False
    
    @abstractmethod
    def repair(self) -> bool:
        return False
    
class Block(DeviceInterface):
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def deviceMajor(self) -> int:
        pass
    
    @abstractmethod
    def deviceMinor(self) -> int:
        pass
    
    @abstractmethod
    def device(self) -> str:
        pass
    
class StorageVolume(Block):
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def isIgnored(self) -> bool:
        pass
    
    @abstractmethod
    def usage(self) -> TypeEnum: #StoVolUseType:
        pass
    
    @abstractmethod
    def fsType(self) -> str:
        pass
    
    @abstractmethod
    def label(self) -> str:
        pass
    
    @abstractmethod
    def size(self) -> int:
        pass
    
    @abstractmethod
    def encryptedContainerUdi() -> str:
        pass
    
# from systems.devices.storagevolume import UsageType as StoVolUseType
from systems.devices.device import DeviceInterfaceType as DevIType
DevITypeUnknown = DevIType.Unknown
