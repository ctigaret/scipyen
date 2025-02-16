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

class _Processor_(_DeviceInterface_):
    def __init__(self):
        super().__init__()
        
class Processor(DeviceInterface):
    class InstructionSet(TypeEnum):
        NoExtensions = 0x0
        IntelMmx = 0x1
        IntelSse = 0x2
        IntelSse2 = 0x4
        IntelSse3 = 0x8
        IntelSsse3 = 0x80
        IntelSse4 = 0x10
        IntelSse41 = 0x10
        IntelSse42 = 0x100
        Amd3DNow = 0x20
        AltiVec = 0x40
        
    InstructionSets = InstructionSet
    
    def __init__(self, backendObject:QtCore.QObject):
        super().__init__(_Processor_(), backendObject)
        self._number_:int = 0
        self._maxSpeed_:int = 0
        self._canChangeFrequency_:bool = False
        self._instructionSets_:InstructionSets = InstructionSets()
        
    @staticmethod
    def deviceInterfaceType(self) -> DeviceInterface.Type:
        return DeviceInterface.Type.Processor
    
    def number(self) -> int:
        from systems.devices.interfaces.processor import Processor as IfaceProcessor
        o = self._d_.backendObject()
        self._number_ = o.number() if isinstance(o, IfaceProcessor) else 0
        return self._number_
    
    def maxSpeed(self) -> int:
        from systems.devices.interfaces.processor import Processor as IfaceProcessor
        o = self._d_.backendObject()
        self._maxSpeed_ = o.maxSpeed() if isinstance(o, IfaceProcessor) else 0
        return self._maxSpeed_

    def canChangeFrequency(self) -> bool:
        from systems.devices.interfaces.processor import Processor as IfaceProcessor
        o = self._d_.backendObject()
        self._canChangeFrequency_ = o.canChangeFrequency() if isinstance(o, IfaceProcessor) else False
        return self._canChangeFrequency_
    
    def instructionSets(self) -> InstructionSets:
        from systems.devices.interfaces.processor import Processor as IfaceProcessor
        o = self._d_.backendObject()
        self._instructionSets_ = o.instructionSets() if isinstance(o, IfaceProcessor) else InstructionSets()
        return self._instructionSets_
    
    
        
    
    
        
