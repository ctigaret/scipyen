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
from core.datatypes import TypeEnum

from systems.devices.interfaces.deviceinterface import DeviceInterface

class Processor(DeviceInterface):
    def __init__(self):
        super().__init__()
        
    @abstractmethod
    def number(self) -> int: pass

    @abstractmethod
    def maxSpeed(self) -> int: pass

    @abstractmethod
    def canChangeFrequency(self) -> bool : pass

    @abstractmethod
    def instructionSets(self) -> TypeEnum : pass
