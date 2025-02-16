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

class _GenericInterface_(_DeviceInterface_):
    def __init__(self):
        super().__init__()
        
class GenericInterface(DeviceInterface):
    PropertyChange = TypeEnum("PropertyChange", ["PropertyModified", "PropertyAdded", "PropertyRemoved"])
    propertyChanged = Signal(dict, name="propertyChanged", arguments = ["changes"])
    conditionRaised = Signal(str, str, name="conditionRaised", aguments = ["condition", "reason"])
    
    
    def __init__(self, backendObject:QtCore.QObject):
        super().__init__(_GenericInterface_(), backendObject)
        
        if backendObject:
            backendObject.propertyChanged[dict].connect(self.propertyChanged)
            backendObject.conditionRaised[str, str].connect(self.conditionRaised)
            
    def getProperty(self, key:str) -> QtCore.QVariant:
        from systems.devices.interfaces.genericinterface import GenericInterface as IfaceGenericInterface
        o = self._d_.backendObject()
        return o.getProperty(key) if isinstance(o, IfaceGenericInterface) else QtCore.QVariant()
    
    def allProperties(self) -> dict: 
        from systems.devices.interfaces.genericinterface import GenericInterface as IfaceGenericInterface
        o = self._d_.backendObject()
        return o.allProperties() if isinstance(o, IfaceGenericInterface) else dict()
    
    def propertyExists(self, key:str) -> bool:
        from systems.devices.interfaces.genericinterface import GenericInterface as IfaceGenericInterface
        o = self._d_.backendObject()
        return o.propertyExists() if isinstance(o, IfaceGenericInterface) else False
