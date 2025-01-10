# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: Python version: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-FileCopyrightText: Original KDE C++ KCompletion Framework authors https://invent.kde.org/frameworks/kcompletion
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing
from enum import IntEnum
from qtpy import QtCore, QtGui, QtWidgets, QtSvg, QtNetwork, sip
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

CompletionMode = IntEnum("CompletionMode",
                         ["CompletionNone", # 1
                          "CompletionAuto",
                          "CompletionMan",
                          "CompletionShell",
                          "CompletionPopup",
                          "CompletionPopupAuto"])
                         
CompOrder = IntEnum("CompOrder", ["Sorted", "Insertion", "Weighted"])

KeyBindingType = IntEnum("KeyBindingType",
                         ["TextCompletion",
                          "PrevCompletionMatch",
                          "NextCompletionMatch",
                          "SubstringCompletion"
                         ])

KeyBindingMap = dict[KeyBindingType, list[QtGui.QKeySequence]]

CB = typing.TypeVar("CB", bound="CompletionBase")
CompletionClass = typing.TypeVar("CompletionClass", bound="Completion")
# CompletionBaseClass = typing.TypeVar("CompletionBaseClass", bound="CompletionBase")

# class Completion:pass

class CompletionBase(QtCore.QObject):
    # ### BEGIN do not use
#     _instance = None
#     def __new__(cls:typing.Self, *args, **kwargs) -> typing.Self:
#         obj = super(CompletionBase, cls).__new__(cls, *args, **kwargs)
#         
#         if cls == type[CB] and not hasattr(cls, "_instance") or not isinstance(cls._instance, cls):
#             cls._instance = obj
#             
#         return obj
#     
#     @classmethod
#     def _walk_mro(cls) -> typing.Generator[typing.Self, None, None]:
#         """Walk the cls.mro() for parent classes that are also singletons
#     
#         For use in instance()
#         """
#         # NOTE: 2025-01-07 12:42:39
#         # see traitlets.config.SingletonConfigurable
#         for subclass in cls.mro():
#             if (
#                 issubclass(cls, subclass) and issubclass(subclass, typing.Self) and subclass != typing.Self
#             ):
#                 yield subclass
#     
#     @classmethod
#     def initialized(cls:typing.Self) -> bool:
#         if cls != CB:
#             return True
#         return hasattr(cls, "_instance" and isinstance(cls._instance, cls))
#     
#     @classmethod
#     def instance(cls:typing.Self, *args, **kwargs) -> typing.Self:
#         if cls._instance is None:
#             inst = cls(*args, **kwargs)
#             for subclass in cls._walk_mro():
#                 subclass._instance = inst
#         if hasattr(cls, "_instance") and isinstance(cls._instance, cls):
#             return cls._instance
#         else:
#             raise RuntimeError(f"Incompatible sibling of '{cls.__name__}' is already instantiated as singleton: {type(cls._instance).__name__}")
#             
    # ### END  do not use
    
    def __init__(self):
        super().__init__()
        self._completionObject_:typing.Optional[CompletionClass] = None
        self._keyBindingMap_:KeyBindingMap = dict()
        self._delegate_:typing.Optional[CompletionBase] = None
        self._handleSignals_:bool = False
        self._emitSignals_:bool = False
        
        self.init()
        

    def init(self):
        self.completionMode:CompletionMode
        self.useGlobalKeyBindings()
        # self.q.setAutoDeleteCompletionObject(False) # see NOTE: 2025-01-10 21:49:08
        self.setHandleSignals(True)
        self.setEmitSignals(False)
        
    def setDelegate(self, delegate:typing.Self):
        if isinstance(self._delegate_, CompletionBase):
            self._delegate_ = delegate
            self._delegate_.setHandleSignals(self._handleSignals_)
            self._delegate_.setEmitSignals(self._emitSignals_)
            self._delegate_.setCompletionMode(self._completionMode_)
            self._delegate_.setKeyBindingMap(self._keyBindingMap_)

    def delegate(self) -> typing.Self:
        return self._delegate_
    
    def setCompletionObject(self, completionObject:CompletionClass, handleSignals:bool):
        if isinstance(self._delegate_, CompletionBase):
            self._delegate_.setCompletionObject(completionObject, handleSignals)
        else:
            self._completionObject_ = completionObject
            self.setHandleSignals(handleSignals)
    
    def completionObject(self, handleSignals:bool) -> CompletionClass:
        if isinstance(self._delegate_, CompletionBase):
            return self._delegate_.completionObject(handleSignals)
        
        if not isinstance(self._completionObject_, CompletionClass):
            self.setCompletionObject(CompletionClass(), handleSignals)
            
        return self._completionObject_
        
    def setHandleSignals(self, handle:bool):
        if isinstance(self._delegate_, CompletionBase):
            self.delegate.setHandleSignals(handle)
        else:
            self._handleSignals_ = handle
            
    def useGlobalKeyBindings(self):
        if isinstance(self._delegate_, CompletionBase):
            self._delegate_.useGlobalKeyBindings()
            return
        
        self._keyBindingMap_.clear()
        self._keyBindingMap_["KeyBindingType.TextCompletion"] = list()
        self._keyBindingMap_["KeyBindingType.PrevCompletionMatch"] = list()
        self._keyBindingMap_["KeyBindingType.NextCompletionMatch"] = list()
        self._keyBindingMap_["KeyBindingType.SubstringCompletion"] = list()

    def setEmitSignals(self, emitRotationSignals:bool):
        if isinstance(self._delegate_, CompletionBase):
            self._delegate_.setEmitSignals(emitRotationSignals)
        else:
            self._emitSignals_ = emitRotationSignals
            
    def setEnableSignals(self, enable:bool):
        if isinstance(self._delegate_, CompletionBase):
            self._delegate_.setEnableSignals(enable)
        else:
            self._emitSignals_ = enable
            
    def handleSignals(self) -> bool:
        return self._delegate_.handleSignals() if isinstance(self._delegate_, CompletionBase) else self._handleSignals_
        
    def emitSignals(self) -> bool:
        return self._delegate_.emitSignals() if isinstance(self._delegate_, CompletionBase) else self._emitSignals_
    
    def setCompletionMode(self, mode:CompletionMode):
        if isinstance(self._delegate_, CompletionBase):
            self._delegate_.setCompletionMode(mode)
            return
        
        
        self._completionMode_ = mode
        if isinstance(self._completionObject_, CompletionClass) and self._completionMode_ != CompletionMode.CompletionNone:
            self._completionMode_.setCompletionMode(self._completionMode_)
            
    def completionMode(self) -> CompletionMode:
        return self._delegate_.completionMode() if isinstance(self._delegate_, CompletionBase) else self._completionMode_
            
    def setKeyBinding(self, item:KeyBindingType, cut:list[QtGui.QKeySequence]) -> bool:
        if isinstance(self._delegate_, CompletionBase):
            return self._delegate_.setKeyBinding(item, cut)
        
        if len(cut):
            if item in self._keyBindingMap_.values():
                return False
            
        self._keyBindingMap_[item] = cut
        return True
    
    def keyBinding(self, item:KeyBindingType) -> list:
        return self._delegate_.keyBinding(item) if isinstance(self._delegate_, CompletionBase) else self._keyBindingMap_.get(item, list())
    
    def compObj(self) -> CompletionClass:
        return self._delegate_.compObj() if isinstance(self._delegate_, CompletionBase) else self._completionObject_
    
    def keyBindingMap(self) -> KeyBindingMap:
        return self._delegate_.keyBindingMap() if isinstance(self._delegate_, CompletionBase) else self._keyBindingMap_
    
    def setKeyBindingMap(self, keyBindingMap:KeyBindingMap):
        if isinstance(self._delegate_, CompletionBase):
            self._delegate_.setKeyBindingMap(keyBindingMap)
            return
        
        self._keyBindingMap_ = keyBindingMap
        
    def virtual_hool(self):
        pass # ?!?
        
class Completion():pass # TODO 2025-01-10 23:57:57
