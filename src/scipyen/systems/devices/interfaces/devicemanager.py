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

IFaceDevice = typing.TypeVar("IFaceDevice")
IFaceDeviceManager = typing.TypeVar("IFaceDeviceManager")

class FendDeviceIFace:pass
FendDeviceIFaceType = typing.TypeVar("FendDeviceIFaceType")
FendDeviceIFaceTypeUnknown = 0

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
    def supportedInterfaces(sel) -> set[FendDeviceIFaceType]:
        pass
    
    @abstractmethod
    def allDevices(self) -> list[str]:
        pass
    
    @abstractmethod
    def devicesFromQuery(self, parentUdi:str, 
                         type:FendDeviceIFaceType = FendDeviceIFaceTypeUnknown) -> list[str]:
        pass
    
    @abstractmethod
    def createDevice(self, udi:str) -> QtCore.QObject:
        pass
    

from systems.devices.deviceinterface import DeviceInterface as FendDeviceIFace
FendDeviceIFaceType = FendDeviceIFace.Type
FendDeviceIFaceTypeUnknown = FendDeviceIFace.Type.Unknown
