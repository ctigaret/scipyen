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
# ATTENTION: 2025-02-11 22:13:57 
# see NOTE: 2025-02-11 22:28:54 and NOTE: 2025-02-11 22:46:31
# in core/multimeta.py
# for workaround the metaclass conflict for subclasses of QObject and multimeta.MultipleMeta
from core.multimeta import MultipleMeta
from core.sysutils import adapt_ui_path
from core.datatypes import TypeEnum

from systems.devices.deviceinterface import (_DeviceInterface_, DeviceInterface)

class _StorageAccess_(_DeviceInterface_):
    def __init__(self):
        super().__init__()
        
class _StorageAccessMultiMeta_(type(DeviceInterface), MultipleMeta): 
    """Enables constructor overloading"""
    pass
    
class StorageAccess(DeviceInterface, metaclass = _StorageAccessMultiMeta_):
    from systems.devices.errors import ErrorType
    from systems.devices.interfaces.deviceinterface import DeviceInterface as IfaceDeviceInterface
    
    accessibilityChanged = Signal(bool, str, name="accessibilityChanged", arguments=["accessible", "udi"])
    setupDone = Signal(ErrorType, object, str, name="setupDone", arguments=["error", "errorData", "udi"])
    teardownDone = Signal(ErrorType, object, str, name="teardownDone", arguments=["error", "errorData", "udi"])
    setupRequested = Signal(str, name="setupRequested", arguments = ["udi"])
    teardownRequested = Signal(str, name="teardownRequested", arguments = ["udi"])
    repairRequested = Signal(str, name="repairRequested", arguments=["udi"])
    repairDone = Signal(ErrorType, object, str, name="repairDone", arguments=["error", "errorData", "udi"])
    
    def __init__(self, backendObject:QtCore.QObject):
        super().__init__(_StorageAccess_(), backendObject)
        self._finalizeInit_()
        
    def __init__(self, dd:_StorageAccess_, backendObject:QtCore.QObject):
        # initializes super()._d_ i.e. DeviceInterface._d_, which is a _DeviceInterface_
        super().__init__(dd, backendObject) 
        self._finalizeInit_()
        

    def _finalizeInit_(self):
        self._accessible_:bool = False
        self._filePath_:str = str()
        self._ignored_:bool = True
        self._encrypted_:bool = False
        
        backendObject.setupDone[ErrorType, object, str].connect(self.setupDone)
        backendObject.teardownDone[ErrorType, object, str].connect(self.teardownDone)
        backendObject.setupRequested[str].connect(self.setupRequested)
        backendObject.teardownRequested[str].connect(self.teardownRequested)
        backendObject.accessibilityChanged[bool, str].connect(self.accessibilityChanged)
        
        backendObject.repairRequested[str].connect(self.repairRequested)
        backendObject.repairDone[ErrorType, object, str].connect(self.repairDone)

    def isIgnored(self) -> bool:
        # from systems.devices.interfaces.device import DeviceInterface as IfaceDeviceInterface
        # Q_D(const StorageAccess);
        #                   Type,                   Object,             Default, Method        
        # return_SOLID_CALL(Ifaces::StorageAccess *, d->backendObject(), true, isIgnored());
        # Here, Solid casts d->backendObject() to a 
        # Ifaces::StorageAccess <- Ifaces::Block <- Ifaces::DeviceInterface
        # then calls its isIgnored() and returns the result
        # if casting fails, returns True (i.e., is ignored)
        #
        # Now, self inherits from systems.devices.device.DeviceInterface ⟹
        # self._d_ is a devices.device._DeviceInterface_; its backend object 
        # (QObject); Solid, casts this backend object, here, to a 
        # devices.interfaces.DeviceInterface aliases here to IfaceDeviceInterface
        
        # NOTE: 2025-02-11 22:30:02
        # while still using PyQt5 could try and use sip.cast
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        self._ignored_ = o.isIgnored() if isinstance(o, self.IfaceDeviceInterface) else True
        return self._ignored_
        
    def isEncrypted(self) -> bool:
        # from systems.devices.interfaces.device import DeviceInterface as IfaceDeviceInterface
        # Q_D(const StorageAccess);
        #                   Type,                   Object,             Default, Method        
        # return_SOLID_CALL(Ifaces::StorageAccess *, d->backendObject(), true, isIgnored());
        # Here, Solid casts d->backendObject() to a 
        # Ifaces::StorageAccess <- Ifaces::Block <- Ifaces::DeviceInterface
        # then calls its isIgnored() and returns the result
        # if casting fails, returns True (i.e., is ignored)
        #
        # Now, self inherits from systems.devices.device.DeviceInterface ⟹
        # self._d_ is a devices.device._DeviceInterface_; its backend object 
        # (QObject); Solid, casts this backend object, here, to a 
        # devices.interfaces.DeviceInterface aliases here to IfaceDeviceInterface
        
        # NOTE: 2025-02-11 22:30:02
        # while still using PyQt5 could try and use sip.cast
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        self._encrypted_ = o.isIgnored() if isinstance(o, self.IfaceDeviceInterface) else False
        return self._encrypted_
        
    @staticmethod
    def deviceInterfaceType() -> DeviceInterface.Type:
        return DeviceInterface.Type.StorageAccess
    
    def isAccessible(self) -> bool:
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        self._accessible_ = o.isAccessible() if isinstance(o, self.IfaceDeviceInterface) else False
        return self._accessible_ # Default parameter of return_SOLID_CALL macro
    
    def filePath(self) -> str:
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        self._filePath_ = o.filePath() if isinstance(o, self.IfaceDeviceInterface) else str()
        return self._filePath_ # Default parameter of return_SOLID_CALL macro
    
    def setup(self) -> bool:
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        return o.setup() if isinstance(o, self.IfaceDeviceInterface) else False # Method parameter of return_SOLID_CALL macro
    
    def teardown(self) -> bool:
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        return o.teardown() if isinstance(o, self.IfaceDeviceInterface) else False
        
    def canCheck(self) -> bool:
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        return o.canCheck() if isinstance(o, self.IfaceDeviceInterface) else False
    
    def check(self) -> bool:
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        return o.check() if isinstance(o, self.IfaceDeviceInterface) else False
        
    def canRepair(self) -> bool:
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        return o.canRepair() if isinstance(o, self.IfaceDeviceInterface) else False
        
    def repair(self) -> bool:
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        return o.repair() if isinstance(o, self.IfaceDeviceInterface) else False
        
