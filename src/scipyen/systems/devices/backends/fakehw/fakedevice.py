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

from systems.devices.interfaces.device import Device as IfaceDevice

class FakeDevice(IfaceDevice, metaclass = MultipleMeta):
    class _Private_: pass # TODO

    def __init__(self, udi:str, propertyMap:dict): # TODO
        """
        propertyMap: str ↦ QVariant
        """
        pass 
    
    def __init__(self, device:object): # TODO
        """ Copy c'tor?
        device: FakeDevice
        """
        pass
    
    @Slot()
    def udi(self) -> str: # TODO
        pass
    
    @Slot()
    def parentUdi(self) -> str: # TODO
        pass
    
    @Slot()
    def vendor(self) -> str: # TODO
        pass
    
    @Slot()
    def product(self) -> str: # TODO
        pass
    
    @Slot()
    def icon(self) -> str: # TODO
        pass
    
    @Slot()
    def emblems(self) -> list[str]: # TODO
        pass
    
    @Slot()
    def description(self) -> str: # TODO
        pass
    
    @Slot()
    def getProperty(self, key:str) -> QtCore.QVariant: # TODO
        pass
    
    @Slot()
    def allProperties(self) -> dict: # TODO
        pass
    
    @Slot()
    def propertyExists(self, key:str) -> bool: # TODO
        # NOTE: 2025-02-21 09:49:11 TODO:
        # consider 'hasProperty' - there is an overap woth python object attribute
        # API here, but I might just keep it as in the Qt counterpart
        pass
    
    
# public Q_SLOTS:
#     QString udi() const override;
#     QString parentUdi() const override;
#     QString vendor() const override;
#     QString product() const override;
#     QString icon() const override;
#     QStringList emblems() const override;
#     QString description() const override;
# 
#     virtual QVariant property(const QString &key) const;
#     virtual QMap<QString, QVariant> allProperties() const;
#     virtual bool propertyExists(const QString &key) const;
#     virtual bool setProperty(const QString &key, const QVariant &value);
#     virtual bool removeProperty(const QString &key);
# 
#     virtual bool lock(const QString &reason);
#     virtual bool unlock();
#     virtual bool isLocked() const;
#     virtual QString lockReason() const;
# 
#     void setBroken(bool broken);
#     bool isBroken();
#     void raiseCondition(const QString &condition, const QString &reason);
# 
# public:
#     bool queryDeviceInterface(const Solid::DeviceInterface::Type &type) const override;
#     QObject *createDeviceInterface(const Solid::DeviceInterface::Type &type) override;
# 
# Q_SIGNALS:
#     void propertyChanged(const QMap<QString, int> &changes);
#     void conditionRaised(const QString &condition, const QString &reason);
# 
# private:
#     class Private;
#     QSharedPointer<Private> d;
    
