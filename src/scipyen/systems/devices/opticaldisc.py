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
# from core.sysutils import adapt_ui_path
from core.datatypes import TypeEnum

from systems.devices.storagevolume import (StorageVolume, _StorageVolume_)
from systems.devices.deviceinterface import (_DeviceInterface_, DeviceInterface)

# class IfaceOpticalDisc:pass

class _OpticalDisc_ (_StorageVolume_):
    def __init__(self):
        super().__init__()
        
class OpticalDisc(StorageVolume):
    class ContentType(TypeEnum):
        NoContent = 0x00,
        Audio = 0x01,
        Data = 0x02,
        VideoCd = 0x04,
        SuperVideoCd = 0x08,
        VideoDvd = 0x10,
        VideoBluRay = 0x20
        
    ContentTypes = ContentType
        
    DiscType = TypeEnum("DiscType", [
        "UnknownDiscType",
        "CdRom",
        "CdRecordable",
        "CdRewritable",
        "DvdRom",
        "DvdRam",
        "DvdRecordable",
        "DvdRewritable",
        "DvdPlusRecordable",
        "DvdPlusRewritable",
        "DvdPlusRecordableDuallayer",
        "DvdPlusRewritableDuallayer",
        "BluRayRom",
        "BluRayRecordable",
        "BluRayRewritable",
        "HdDvdRom",
        "HdDvdRecordable",
        "HdDvdRewritable",
        ], start=-1)
        
        
    def __init__(self, backendObject:QtCore.QObject):
        super().__init__(_OpticalDisc_(), backendObject)
        self._availableContent_:self.ContentTypes = self.ContentType.NoContent
        self._discType_:self.DiscType = self.DiscType.UnknownDiscType
        self._appendable_:bool = False
        self._blank_:bool  = False
        self._rewritable_:bool = False
        self._capacity_:int = 0
#         
    @staticmethod
    def deviceInterfaceType() -> DeviceInterface.Type:
        return DeviceInterface.Type.OpticalDisc
        
    def availableContent(self) -> ContentType:
        from systems.devices.interfaces.opticaldisc import OpticalDisc as IfaceOpticalDisc
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        self._availableContent_ = o.availableContent() if isinstance(o, IfaceOpticalDisc) else self.ContentType.NoContent
        return self._availableContent_
    
    def discType(self) -> DiscType:
        from systems.devices.interfaces.opticaldisc import OpticalDisc as IfaceOpticalDisc
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        self._discType_ = o.discType() if isinstance(o, IfaceOpticalDisc) else self.DiscType.UnknownDiscType
        return self._discType_
    
    def isAppendable(self) -> bool:
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        from systems.devices.interfaces.opticaldisc import OpticalDisc as IfaceOpticalDisc
        self._appendable_ = o.isAppendable() if isinstance(o, IfaceOpticalDisc) else False
        return self._appendable_
    
    def isBlank(self) -> bool:
        from systems.devices.interfaces.opticaldisc import OpticalDisc as IfaceOpticalDisc
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        self._blank_ = o.isBlank() if isinstance(o, IfaceOpticalDisc) else False
        return self._blank_
        
    def isRewritable(self) -> bool:
        from systems.devices.interfaces.opticaldisc import OpticalDisc as IfaceOpticalDisc
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        self._rewritable_ = o.isRewritable() if isinstance(o, IfaceOpticalDisc) else False
        return self._rewritable_
    
    def capacity(self) -> int:
        from systems.devices.interfaces.opticaldisc import OpticalDisc as IfaceOpticalDisc
        o = self._d_.backendObject() # expected a systems.devices.interfaces.DeviceInterface
        self._capacity_ = o.capacity() if isinstance(o, IfaceOpticalDisc) else 0
        return self._capacity_
        
        
    
        
    
        
    
