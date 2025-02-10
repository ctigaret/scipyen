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
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

class Device(QtCore.QObject):
    from systems.devices.device import DeviceInterfaceType
    
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
    def product(self) 0> str:
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
    def queryDeviceInterface(self, devtype:DeviceInterfaceType) -> bool:
        pass
    
    @abstractmethod
    def createDeviceInterface(self, devtype:DeviceInterfaceType) -> QtCore.QObject:
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
    
