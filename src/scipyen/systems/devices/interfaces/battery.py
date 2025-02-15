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

class Battery(DeviceInterface):
    presentStateChanged = Signal(bool, str, name="presentStateChanged", arguments = ["newState", "udi"])
    chargePercentChanged = Signal(int, str, name="chargePercentChanged", arguments = ["value", "udi"])
    capacityChanged = Signal(int, str, name="capacityChanged", arguments = ["value", "udi"])
    cycleCountChanged = Signal(int, str, name="cycleCountChanged", arguments = ["value", "udi"])
    powerSupplyStateChanged = Signal(bool, str, name="powerSupplyStateChanged", arguments = ["newState", "udi"])
    chargeStateChanged = Signal(int, str, name="chargeStateChanged", arguments = ["newState", "udi"])
    timeToEmptyChanged = Signal(int, str, name="timeToEmptyChanged", arguments = ["time", "udi"])
    timeToFullChanged = Signal(int, str, name="timeToFullChanged", arguments = ["time", "udi"])
    energyChanged = Signal(float, str, name="energyChanged", arguments = ["energy", "udi"])
    energyFullChanged = Signal(float, str, name="energyFullChanged", arguments = ["energy", "udi"])
    energyFullDesignChanged = Signal(float, str, name="energyFullDesignChanged", arguments = ["energy", "udi"])
    energyRateChanged = Signal(float, str, name="energyRateChanged", arguments = ["energyRate", "udi"])
    voltageChanged = Signal(float, str, name="voltageChanged", arguments = ["voltage", "udi"])
    temperatureChanged = Signal(float, str, name="temperatureChanged", arguments = ["temperature", "udi"])
    remainingTimeChanged = Signal(int, str, name="remainingTimeChanged", arguments = ["time", "udi"])
    
    def __init__(self):
        super().__init__()
        
    @abstractmethod
    def isPresent(self) -> bool:
        pass
    
    @abstractmethod
    def type(): # TODO: devices/battery (for BatteryType)
        pass
        
    @abstractmethod
    def chargePercent(self) ->int:
        pass
    
    @abstractmethod
    def capacity(self) -> int:
        pass
    
    @abstractmethod
    def cycleCount(self) -> int:
        pass
    
    @abstractmethod
    def isRechargeable(self) -> bool:
        pass
        
    @abstractmethod
    def isPowerSupply(self) -> bool:
        pass
    
    @abstractmethod
    def chargeState(self): # TODO: devices/battery (for ChargeState)
        pass
    
    @abstractmethod
    def timeToEmpty(self) -> int:
        # time in s until empty
        pass
    
    @abstractmethod
    def timeToFull(self) -> int:
        pass
    
    @abstractmethod
    def technology(self): # TODO: devices/battery (for Technology)
        pass 
    
    @abstractmethod
    def energy(self) -> float:
        pass
    
    @abstractmethod
    def energyFull(self) -> float:
        pass
    
    @abstractmethod
    def energyFullDesign(self) -> float:
        pass
    
    @abstractmethod
    def energyRate(self) -> float:
        pass
    
    @abstractmethod
    def voltage(self) -> float:
        pass
    
    @abstractmethod
    def temperature(self) -> float:
        pass
    
    @abstractmethod
    def serial(self) -> str:
        pass
    
    @abstractmethod
    def remainingTime(self) -> int:
        pass
    
