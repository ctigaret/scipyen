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
from systems.devices.deviceinterface import (_DeviceInterface_, DeviceInterface)

class _Battery_(_DeviceInterface_):
    def __init__(self):
        super().__init__()


class Battery(DeviceInterface):
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
        self._cycleCount_:int = -1
        self._isRechargeable_:bool = False
        self._isPowerSupply_:bool = True
        self._chargeState_:self.ChargeState = self.ChargeState.NoCharge
        self._timeToEmpty_:int = 0
        self._timeToFull_:int = 0
        self._technology_:self.Technology = self.Technology.UnknownTechnology
        self._energy_:float = 0.0
        self._energyFull_:float = 0.0
        self._energyFullDesign_:float = 0.0
        self._energyRate_:float = 0.0
        self._voltage_:float = 0.0
        self._temperature_:float = 0.0
        self._serial_:str = str()
        self._remainingTime_:int =-1
        
        backendObject.presentStateChanged(int, str).connect(self.presentStateChanged)
        backendObject.chargePercentChanged(int, str).connect(self.chargePercentChanged)
        backendObject.capacityChanged(int, str).connect(self.capacityChanged)
        backendObject.cycleCountChanged(int, str).connect(self.cycleCountChanged)
        backendObject.powerSupplyStateChanged(bool, str).connect(self.powerSupplyStateChanged)
        backendObject.chargeStateChanged(int, str).connect(self.chargeStateChanged)
        backendObject.timeToEmptyChanged(int, str).connect(self.timeToEmptyChanged)
        backendObject.timeToFullChanged(int, str).connect(self.timeToFullChanged)
        backendObject.energyChanged(float, str).connect(self.energyChanged)
        backendObject.energyFullChanged(float, str).connect(self.energyFullChanged)
        backendObject.energyFullDesignChanged(float, str).connect(self.energyFullDesignChanged)
        backendObject.energyRateChanged(float, str).connect(self.energyRateChanged)
        backendObject.voltageChanged(float, str).connect(self.voltageChanged)
        backendObject.temperatureChanged(float, str).connect(self.temperatureChanged)
        backendObject.remainingTimeChanged(int, str).connect(self.remainingTimeChanged)
        
    @staticmethod
    def deviceInterfaceType() -> DeviceInterface.Type:
        return DeviceInterface.Type.Battery
    
    def isPresent(self) -> bool: 
        from systems.devices.interfaces.device import Battery as IfaceBattery
        
        o = self._d_.backendObject()
        self._isPresent_ = o.isPresent() if isinstance(o, IfaceBattery) else False
        return self._isPresent_

    def type(self) -> BatteryType: 
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._type_ = o.type() if isinstance(o, IfaceBattery) else self.BatteryType.UnknownBattery
        return self._type_

    def chargePercent(self) -> int:
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._chargePercent_ = o.chargePercent() if isinstance(o, IfaceBattery) else 0
        return self._chargePercent_

    def capacity(self) -> int:
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._capacity_ = o.capacity() if isinstance(o, IfaceBattery) else 100
        return self._capacity_

    def cycleCount(self) -> int:
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._cycleCount_ = o.cycleCount() if isinstance(o, IfaceBattery) else -1
        return self._cycleCount_

    def isRechargeable(self) -> bool:
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._isRechargeable_ = o.isRechargeable() if isinstance(o, IfaceBattery) else False
        return self._isRechargeable_
    
    def isPowerSupply(self) -> bool: 
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._isPowerSupply_ = o.isPowerSupply() if isinstance(o, IfaceBattery) else True
        return self._isPowerSupply_
    
    def chargeState(self) -> ChargeState: 
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._chargeState_ = o.chargeState() if isinstance(o, IfaceBattery) else self.ChargeState.NoCharge
        return self._chargeState_
    
    def timeToEmpty(self) -> int:
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._timeToEmpty_ = o.timeToEmpty() if isinstance(o, IfaceBattery) else 0
        return self._timeToEmpty_

    def timeToFull(self) -> int: 
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._timeToFull_ = o.timeToFull() if isinstance(o, IfaceBattery) else 0
        return self._timeToFull_

    def technology(self) -> Technology:
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._technology_ = o.technology() if isinstance(o, IfaceBattery) else self.Technology.UnknownTechnology
        return self._technology_

    def energy(self) -> float:
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._energy_ = o.energy() if isinstance(o, IfaceBattery) else 0.0
        return self._energy_

    def energyFull(self) -> float:
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._energyFull_ = o.energyFull() if isinstance(o, IfaceBattery) else 0.0
        return self._energyFull_

    def energyFullDesign(self) -> float:
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._energyFullDesign_ = o.energyFullDesign() if isinstance(o, IfaceBattery) else 0.0
        return self._energyFullDesign_

    def energyRate(self) -> float:
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._energyRate_ = o.energyRate()if isinstance(o, IfaceBattery) else 0.0
        return self._energyRate_

    def voltage(self) -> float:
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._voltage_ = o.voltage() if isinstance(o, IfaceBattery) else 0.0
        return self._voltage_

    def serial(self) -> str:
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._serial_ = o.serial() if isinstance(o, IfaceBattery) else str()
        return self._serial_

    def remainingTime(self) -> str:
        from systems.devices.interfaces.device import Battery as IfaceBattery
        o = self._d_.backendObject()
        self._remainingTime_ = o.remainingTime() if isinstance(o, IfaceBattery) else -1
        return self._remainingTime_


    
        
