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

from systems.devices import device
from systems.devices.device import (_DeviceInterface_, DeviceInterface, DeviceInterfaceType, Device, DevicePredicate)

class _Battery_(_DeviceInterface_):
    def __init__(self):
        super().__init__()


class Battery(DeviceInterface):
    from systems.devices.interfaces.device import DeviceInterface as IfaceDevIFace
    from systems.devices.interfaces.device import Battery as IfaceBattery
    BatteryType = TypeEnum("BatteryType", ["UnknownBattery",
        "PdaBattery",
        "UpsBattery",
        "PrimaryBattery",
        "MouseBattery",
        "KeyboardBattery",
        "KeyboardMouseBattery",
        "CameraBattery",
        "PhoneBattery",
        "MonitorBattery",
        "GamingInputBattery",
        "BluetoothBattery",
        "TabletBattery",
        "HeadphoneBattery",
        "HeadsetBattery",
        "TouchpadBattery"])
    
    ChargeState = TypeEnum("ChargeState", ["NoCharge", "Charging", "Discharging", "FullyCharged"])
    
    Technology = TypeEnum("Technology", ["UnknownTechnology",
        "LithiumIon",
        "LithiumPolymer",
        "LithiumIronPhosphate",
        "LeadAcid",
        "NickelCadmium",
        "NickelMetalHydride"], start=0)

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
    
    
    def __init__(self, backendObject:QtCore.QObject):
        super().__init__(_Battery_(), backendObject)
        self._isPresent_: bool = False
        self._type_ = self.BatteryType.UnknownBattery
        self._chargePercent_:int = 0
        self._capacity_:int = 100
        
        backendObject.presentStateChanged(int, str).connect(self.presentStateChanged)
        backendObject.chargePercentChanged(int, str).connect.(self.chargePercentChanged)
        backendObject.capacityChanged(int, str).connect.(self.capacityChanged)
        backendObject.cycleCountChanged(int, str).connect.(self.cycleCountChanged)
        backendObject.powerSupplyStateChanged(bool, str).connect.(self.powerSupplyStateChanged)
        backendObject.chargeStateChanged(int, str).connect.(self.chargeStateChanged)
        backendObject.timeToEmptyChanged(int, str).connect.(self.timeToEmptyChanged)
        backendObject.timeToFullChanged(int, str).connect.(self.timeToFullChanged)
        backendObject.energyChanged(float, str).connect.(self.energyChanged)
        backendObject.energyFullChanged(float, str).connect.(self.energyFullChanged)
        backendObject.energyFullDesignChanged(float, str).connect.(self.energyFullDesignChanged)
        backendObject.energyRateChanged(float, str).connect.(self.energyRateChanged)
        backendObject.voltageChanged(float, str).connect.(self.voltageChanged)
        backendObject.temperatureChanged(float, str).connect.(self.temperatureChanged)
        backendObject.remainingTimeChanged(int, str).connect.(self.remainingTimeChanged)
        
    @staticmethod
    def deviceInterfaceType() -> DeviceInterfaceType:
        return DeviceInterfaceType.Battery
    
    def isPresent(self) -> bool: 
        o = self._d_.backendObject()
        # if isinstance(o, self.IfaceDevIFace):
        if isinstance(o, IfaceBattery):
            self._isPresent_ = o.isPresent()
        else:
            self._isPresent_ = False
            
        return self._isPresent_

    def type(self) -> BatteryType: 
        o = self._d_.backendObject()
        # if isinstance(o, self.IfaceDevIFace):
        if isinstance(o, self.IfaceBattery):
            self._type_ = o.type()
        else:
            self._type_ = self.BatteryType.UnknownBattery
            
        return self._type_

    def chargePercent(self) -> int:
        o = self._d_.backendObject()
        if isinstance(o, self.IfaceBattery):
            self._chargePercent_ = o.chargePercent()
        else:
            self._chargePercent_ = 0
            
        return self._chargePercent_

    def capacity(self) -> int:
        o = self._d_.backendObject()
        if isinstance(o, self.IfaceBattery):
            self._capacity_ = o.capacity()
        else:
            self._capacity_ = 100
        

    def cycleCount(self) -> int: pass # TODO

    def isRechargeable(self) -> bool: pass # TODO
    
    def isPowerSupply(self) -> bool: pass # TODO
    
    def chargeState(self) -> ChargeState: pass  # TODO

    def timeToEmpty(self) -> int: pass # TODO

    def timeToFull(self) -> int: pass # TODO

    def technology(self) -> Technology: pass # TODO

    def energy(self) -> float: pass # TODO

    def energyFull(self) -> float: pass # TODO

    def energyFullDesign(self) -> float: pass # TODO

    def energyRate(self) -> float: pass # TODO

    def voltage(self) -> float: pass # TODO

    def serial(self) -> str: pass  # TODO

    def remainingTime(self) -> str: pass # TODO


    
        
