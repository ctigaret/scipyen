# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Work in progress, DO NOT USE
"""
import sys, os, typing, pathlib, functools, itertools, traceback
from copy import (copy, deepcopy)
from urllib.parse import urlparse, urlsplit
from collections import deque
from abc import abstractmethod
from enum import Enum, IntEnum
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path
from core.datatypes import TypeEnum
from core.multimeta import MultipleMeta

class DeviceNotifier(QtCore.QObject):
    # singleton design pattern
    __instance__:typing.Optional[typing.Self] = None
    deviceAdded = Signal(str, name="deviceAdded") # parameters is an udi
    deviceRemoved = Signal(str, name="deviceRemoved") # parameters is an udi
    
    def __new__(cls:typing.Self, *args, **kwargs) -> typing.Self:
        if not hasattr(cls, "__instance__") or not isinstance(cls.__instance__, cls):
            cls.__instance__ = super(DeviceNotifier, cls).__new__(cls, *args, **kwargs)
            
        return cls.__instance__
    
    def __init__(self, parent:typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self.__instance__ = self
    
    @classmethod
    def _walk_mro(cls) -> typing.Generator[typing.Self, None, None]: # NOTE: Singleton design pattern
        for subclass in cls.mro():
            if (
                issubclass(cls, subclass)
                and issubclass(subclass, typing.Self)
                and subclass != typing.Self
            ):
                yield subclass
                
    @classmethod
    def initialized(cls:typing.Self) -> bool: # NOTE: Singleton design pattern
        return hasattr(cls, "__instance__" and isinstance(cls.__instance__, cls))
    
    @classmethod
    def instance(cls) -> typing.Self: # NOTE: Singleton design pattern
        # return globalDeviceStorage.notifier()
        if not hasattr(cls, "__instance__") or not isinstance(cls.__instance__, cls):
            cls.__instance__ = globalDeviceStorage.notifier()
            if cls.__instance__ is None:
                inst = cls(*args, **kwargs)
                for subclass in cls._walk_mro():
                    subclass.__instance__ = inst
                    
        return cls.__instance__
        # if hasattr(cls, "__instance__") and isinstance(cls.__instance__, cls):
        #     return cls.__instance__
        # else:
        #     raise RuntimeError(f"Incompatible sibling of '{cls.__name__}' is already instantiated as singleton: {type(cls.__instance__).__name__}")

    # @classmethod
    # def instance(cls:typing.Self, *args, **kwargs) -> typing.Self: # NOTE: Singleton design pattern
    #     if cls.__instance__ is None:
    #         inst = cls(*args, **kwargs)
    #         for subclass in cls._walk_mro():
    #             subclass.__instance__ = inst
    #     if hasattr(cls, "__instance__") and isinstance(cls.__instance__, cls):
    #         return cls.__instance__
    #     else:
    #         raise RuntimeError(f"Incompatible sibling of '{cls.__name__}' is already instantiated as singleton: {type(cls.__instance__).__name__}")
    # 
