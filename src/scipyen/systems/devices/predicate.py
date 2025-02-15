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

class ParsingData:
    def __init__(self):
        self.result:typing.Optional[Predicate] = None
        self.bfr:typing.Optional[QtCore.QByteArray] = None
        
class Predicate(metaclass = MultipleMeta):
    from systems.devices.device import Device as FendDevice
    from systems.devices.device import DeviceInterface as FendDeviceIFace
    ComparisonOperator = TypeEnum("ComparisonOperator", ["Equals", "Mask"])
    Type = TypeEnum("Type", ["PropertyCheck", "Conjunction", "Disjunction", "InterfaceCheck"])
    
    class Private:
        def __init__(self):
            self._isValid_:bool = False
            self._type_:Predicate.Type = Predicate.Type.PropertyCheck
            self._compOperator_:Predicate.ComparisonOperator = Predicate.ComparisonOperator.Equals
            self._operand1_:typing.Optional[self.__class__] = None
            self._operand1_:typing.Optional[self.__class__] = None
            self._ifaceType_:DeviceInterfaceType = DeviceInterfaceType.Unknown
            self._property_:str = str()
            # self._value_:object = None
            self._value_:QtCore.QVariant = QtCore.QVariant()
    
    def __init__(self):
        self._d_ = self.Private()
        
    def __init__(self, other:object):
        assert isinstance(other, self.__class__)
        self._d_ = other._d_
        
    def __init__(self, ifaceType:FendDeviceIFace.Type, prop:str, value:QtCore.QVariant, compOperator: ComparisonOperator = ComparisonOperator.Equals):
        self._d_ = self.Private()
        self._d_._ifaceType_ = ifaceType
        self._d_._property_ = prop
        self._d_._type_ = self.Type.PropertyCheck
        self._d_._value_ = value
        self._d_._compOperator_ = compOperator
        
        self._d_._isValid_ = True
        
    def __init__(self, ifaceName:str, prop:str, value:QtCore.QVariant, compOperator: ComparisonOperator = ComparisonOperator.Equals):
        self._d_ = self.Private()
        ifaceType = FendDeviceIFace.Type.stringToType(ifaceName) 
        if ifaceType != -1:
            self._d_._ifaceType_ = ifaceType
            self._d_._property_ = prop
            self._d_._type_ = self.Type.PropertyCheck
            self._d_._value_ = value
            self._d_._compOperator_ = compOperator
        
            self._d_._isValid_ = True
            
    def __init__(self, ifaceType:FendDeviceIFace.Type):
        self._d_ = self.Private()
        self._d_._isValid_ = True
        self._d_._type_ = self.Type.InterfaceCheck
        self._d_._ifaceType_ = ifaceType
        
    def __init__(self, ifaceName:str):
        self._d_ = self.Private()
        ifaceType = FendDeviceIFace.Type.stringToType(ifaceName)
        if ifaceType != -1:
            self._d_._isValid_ = True
            self._d_._type_ = self.Type.InterfaceCheck
            self._d_._ifaceType_ = ifaceType
            
    def __del__(self):
        if hasattr(self, "_d_") and self._d_._type_ != self.Type.PropertyCheck and self._d_._type_ != self.Type.InterfaceCheck:
            self._d_._operand1_ = None
            self._d_._operand2_ = None
            
        self._d_ = None
        
    def __and__(self, other:typing.Self):
        """ operator&"""
        result = self.__class__()
        result._d_._isValid_ = True
        result._d_._type_ = self.Type.Conjunction
        
        # CAUTION 2025-02-12 22:20:58
        result._d_._operand1_ = self
        result._d_._operand2_ = other
        
        return result
    
    def __iand__(self, other:typing.Self):
        """ operator&="""
        self = self & other
        return self
    
    def __or__(self, other:typing.Self):
        """ operator| """
        result = self.__class__()
        result._d_._isValid_ = True
        result._d_._type_ = self.Type.Disjunction
        
        # CAUTION 2025-02-12 22:20:58
        result._d_._operand1_ = self
        result._d_._operand2_ = other
        
        return result
    
    def __ior__(self, other:typing.Self):
        """ operator|= """
        self = self | other
        return self
        
    def copy(self) -> typing.Self: 
        # ? use as assignment operator (operator= in C++)
        self._d_._isValid_ = other._d_._isValid_
        self._d_._type_ = other._d._type_
        
        if self._d_._type_ != self.Type.PropertyCheck and self._d_._type_ != self.Type.InterfaceCheck:
            self._d_._operand1_ = other._d_._operand1_
            self._d_._operand2_ = other._d_._operand2_
        else:
            self._d_._ifaceType_ = other._d_._ifaceType_
            self._d_._property_ = other._d_._property_
            self._d_._value_ = other._d_._value_
            self._d_._compOperator_ = other._d_._compOperator_
            
        return self
    
    def isValid(self) -> bool:
        return self._d_._isValid_
    
    def matches(self, device:FendDevice) -> bool:
        if not self._d_._isValid_:
            return False
        
        match (self._d_._type_):
            case self.Type.Disjunction:
                return self._d_._operand1_.matches(device) or self._d_._operand2_.matches(device)
            case self.Type.Conjunction:
                return self._d_._operand1_.matches(device) and self._d_._operand2_.matches(device)
            case self.Type.PropertyCheck:
                iface = device.asDeviceInterface(self._d_._ifaceType_)
                if iface is not None:
                    index = iface.metaObject().indexOfProperty(self._d_._property_)
                    if index  == -1:
                        return False # ?!?
                    metaProp = iface.metaObject().property(index)
                    value = metaProp.read(iface) if metaProp.isReadable() else QVariant()
                    expected = self._d_._value_
                    if metaProp.isEnumType() and expected.userType() == QtCore.QMetaType.QString:
                        metaEnum = metaProp.enumerator()
                        value = metaEnum.keysToValue(self._d_._value_.value())
                        if value >= 0:
                            expected = QtCore.QVariant(value)
                        else:
                            expected = QtCore.QVariant()
                            
                    elif metaProp.isEnumType() and expected.userType() == QtCore.QMetaType.Int:
                        expectedValue = expected.value()
                        expected = QtCore.QVariant(expectedValue)
                
                    if self._d_._compOperator_ == self.ComparisonOperator.Mask:
                        v_ok = False
                        try:
                            v = int(value.value())
                            v_ok = True
                        except:
                            v_ok = False
                            
                        e_ok = False
                        try:
                            e = int(excepted.value())
                            e_ok = True
                        except:
                            e_ok = False
                        
                        return e_ok and v_ok and (v & e) # ?!?
                    
                    if value == expected:
                        return True
                    
                    if isinstance(value.value(), (typing.Set, typing.Sequence)):
                        for element in value.value():
                            if element == expected:
                                return True
                # break
            
            case self.Type.InterfaceCheck:
                return device.isDeviceInterface(self._d_._ifaceType_)
            case _:
                return False
            
        return False
            
    def usedTypes(self) -> set[FendDeviceIFace.Type]:
        res = set()
        if self._d_._isValid_:
            match (self._d_._type_):
                case self.Type.Disjunction:
                    pass
                case self.Type.Conjunction:
                    res |= self._d_._operand1_.usedTypes()
                    res |= self._d_._operand2_.usedTypes()
                    # break
                case self.Type.PropertyCheck:
                    pass
                case self.Type.InterfaceCheck:
                    res.add(self._d_._ifaceType_)
                    # break
                case _:
                    pass
                
        return res
                    
    def toString(self) -> str:
        if not self._d_._isValid_:
            return "False"
        
        if self._d_._type_ not in (self.Type.PropertyCheck, self.Type.InterfaceCheck):
            op = "OR" if self._d_._type_ == self.Type.Disjunction else "AND"
            return f"[{self._d_._operand1_.toString()} {op} {self._d_._operand2_.toString()}]"
        
        else:
            ifaceName = FendDeviceIFace.typeToString(self._d_._ifaceType_)
            if len(ifaceName) == 0:
                ifaceName = "Unknown"
                
            if self._d_._type_ == self.Type.InterfaceCheck:
                return f"IS {ifaceName}"
            
            v = self._d_._value_.value()
            
            ret = str()
            
            if isinstance(v, (tuple, list, deque)) and all(isinstance(v_, str) for v_ in v):
                if len(v) == 0:
                    ret = "{}"
                else:
                    ret = "{" + ', '.join(v) + "}"
                    
            elif isinstance(v, bool):
                ret = "True" if v else "False"
                
            elif isinstance(v, int):
                ret = f"{v}"
                
            else:
                ret = f"{v}"
                
            str_operator = "==" if self._d_._compOperator_ == self.ComparisonOperator.Equals else " &"
            
            return f"{ifaceName}.{self._d_._property_} {str_operator} {ret}"
                
#         Q_GLOBAL_STATIC(QThreadStorage<Solid::PredicateParse::ParsingData *>, s_parsingData)
# 
#         Solid::Predicate Solid::Predicate::fromString(const QString &predicate)
#         {
#             Solid::PredicateParse::ParsingData *data = new Solid::PredicateParse::ParsingData();
#             // above, data is a ParsingData with two fields:
#             // bfr - a QByteArray
#             // result - a Predicate object
#             s_parsingData->setLocalData(data);   // set this up as a QThreadStorage
#             data->buffer = predicate.toLatin1(); // predicate is a str; set it to ParsingData
#                                                 // data's buffer'
#             PredicateParse_mainParse(data->buffer.constData()); // bison parse the ParsingData's buffer
#                                                                 // my guess here is that PredicateParse_mainParse
#                                                                 // assigns a new Predicate to data's result
#             Predicate result; // set up a new Predicate
#             if (data->result) { // ParsingData has a result (a Predicate), then:
#                 result = Predicate(*data->result); // assign this to the Predicate object to return
#                 delete data->result;               // and delete ParsingData's result
#             }
#             s_parsingData->setLocalData(nullptr);  // release parginb data from the QThreadStorage
#             return result;
#         } 
#             
    @classmethod
    def fromString(cls, predicate:str) -> typing.Self:
        # NOTE: 2025-02-13 15:55:55 TODO
        data = ParsingData()
        data.bfr = QtCore.QByteArray(predicate.encode())
        result = cls()
        if isinstance(data.result, cls):
            pass
    
    def type(self) -> Type:
        return self._d_._type_
    
    def interfaceType(self) -> FendDeviceIFace.Type:
        return self._d_._ifaceType_
    
    def propertyName(self) -> str:
        return self._d_._property_
    
    def matchingValue(self) -> QtCore.QVariant:
        return self._d_._value_
    
    def comparisonOperator(self) -> ComparisonOperator:
        return self._d_._compOperator_
    
    def firstOperand(self) -> typing.Self:
        return self._d_._operand1_ if isinstance(self._d_._operand1_, self.__class__) else self.__class__()
    
    def secondOperand(self) -> typing.Self:
        return self._d_._operand2_ if isinstance(self._d_._operand2_, self.__class__) else self.__class__()

