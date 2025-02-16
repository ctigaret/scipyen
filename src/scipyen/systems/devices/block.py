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

class _Block_(_DeviceInterface_):
    def __init__(self):
        super().__init__()
        
    
class Block(DeviceInterface):
    def __init__(self, backendObject:QtCore.QObject):
        super().__init__(_Block_(), backendObject)
        self._major_:int = 0
        self._minor_:int =0
        self._device_:str = str()
        
    @staticmethod
    def deviceInterfaceType(self) -> DeviceInterface.Type:
        return DeviceInterface.Type.Block
    
    def deviceMajor(self) -> int:
        from systems.devices.interfaces.block import Block as IfaceBlock
        o = self._d_.backendObject()
        self._major_ = o.deviceMajor() if isinstance(o, IfaceBlock) else 0
        return self._major_
    
    def deviceMinor(self) -> int:
        from systems.devices.interfaces.block import Block as IfaceBlock
        o = self._d_.backendObject()
        self._minor_ = o.deviceMinor() if isinstance(o, IfaceBlock) else 0
        return self._minor_
    
    def device(self) -> str:
        from systems.devices.interfaces.block import Block as IfaceBlock
        o = self._d_.backendObject()
        self._device_ = o.device() if isinstance(o, IfaceBlock) else str()
        return self._device_
    
        
        
