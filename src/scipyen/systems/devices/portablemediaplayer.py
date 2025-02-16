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
from core.datatypes import TypeEnum

from systems.devices.deviceinterface import (_DeviceInterface_, DeviceInterface)

class _PortableMediaPlayer_(_DeviceInterface_):
    def __init__(self):
        super().__init__()
        
class PortableMediaPlayer(DeviceInterface):
    def __init__(self, backendObject:QtCore.QObject):
        super().__init__(_PortableMediaPlayer_(), backendObject)
        self._supportedProtocols_:list[str] = list()
        self._supportedDrivers_:list[str] = list()
        
    @staticmethod
    def deviceInterfaceType() -> DeviceInterface.Type:
        return DeviceInterface.Type.PortableMediaPlayer
    
    def supportedProtocols(self) -> list[str]:
        from systems.devices.interfaces.portablemediaplayer import PortableMediaPlayer as IfacePMP
        o = self._d_.backendObject()
        self._supportedProtocols_ = o.supportedProtocols() if isinstance(o, IfacePMP) else list()
        return self._supportedProtocols_
    
    def supportedDrivers(self, protocol:str = str()) -> list[str]:
        from systems.devices.interfaces.portablemediaplayer import PortableMediaPlayer as IfacePMP
        o = self._d_.backendObject()
        self._supportedDrivers_ = o.supportedDrivers() if isinstance(o, IfacePMP) else list()
        return self._supportedDrivers_
    
    def driverHandle(self, driver:str) -> QtCore.QVariant:
        from systems.devices.interfaces.portablemediaplayer import PortableMediaPlayer as IfacePMP
        o = self._d_.backendObject()
        return o.driverHandle(driver) if isinstance(o, IfacePMP) else QtCore.QVariant()
        
        

