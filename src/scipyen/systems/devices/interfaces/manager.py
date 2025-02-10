# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
    # SPDX-License-Identifier: GPL-3.0-or-later
    # SPDX-License-Identifier: LGPL-2.1-or-later
    
    """
"""
import sys, os, typing, traceback
from abc import ABCMeta, abstractmethod
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class DeviceManager(QtCore.QObject, ABCMeta):
    from systems.devices.device import DeviceInterfaceType
    # abstract base class
    deviceAdded = Signal(str, name="deviceAdded") # parameter is the udi
    deviceRemoved = Signal(str, name="deviceRemoved") # parameter is the udi
    
    def __init__(self, parent:typing.Optional[QCore.QObject] = None):
        super().__init__(parent=parent)
        
    @abstractmethod
    def udiPrefix() -> str:
        pass
    
    @abstractmethod
    def supportedInterfaces(sel) -> set[DeviceInterfaceType]:
        pass
    
    @abstractmethod
    def allDevices(self) -> list[str]:
        return list()
    
    @abstractmethod
    def devicesFromQuery(self, parentUdi:str, ) -> 
        
    
