# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Work in progress, DO NOT USE
"""
# TODO 2025-02-06 11:42:09 Devices access in Scipyen
# Consider:
# • Linux: pyserial, pyusb, pyudev
# • Windows: pyserial, pyusb, pywin32, msdevices (https://github.com/Donny-GUI/msdevices), pyusb
# • MacOS: pyserial, pyusb, import glob; glob.glob('/dev/tty.*')
#
# • All platforms: PyQt5.QtCore.QStorageInfo

#
# For storage devices ONLY see also:
# • https://stackoverflow.com/questions/12672981/python-os-independent-list-of-available-storage-devices
# • dbus.SystemBus() NOT on MAcOS
#


# NOTE: 2025-02-06 11:49:13 as of this date & time:
# pyserial - for USB/RS-232C "dongles" - I use this for coolLED, see coolled_pe12.py
# pyusb - not used yet; might need to add user to the 'plugdev' group
# pywin32 - installed specifically when Scipyen installation scripts are run in Windows 
#           use by Scipyen when run in Windows
# pyudev -  not used
# msdevices - git repo, NOT on pypi;
#           maybe to install specifically when Scipyen installation scripts are run in Windows 
#           not used yet
#

# --------------
# NOTE: 2025-02-06 13:29:13 proposals for this module (using PyQt5)
# 
# Solid::DeviceManager ↦ pyudev.Context
# Solid::Device ↦ pyudev.Device
#
# monitor adding/removing mountable filesystems (i.e. hotpluggable):
# • Synchronously:
#   use pyudev.Monitor with an event filter e.g. monitor.filter_by("block")
#
# • Asynchronously (preferred):
#   use pyudev.MonitorObserver
#
# • Asynchronously in the GUI event loop (required, here):
#   use pyudev.pyqt5 (don't know yet if this would also work in PySide6):
#   WARNING: to avoid clashes import as alias:
#       from pyudev import pyqt5 as udevqt5
#       (or something like that)
#   then use, e.g.:
# from pyudev.pyside import MonitorObserver
# monitor = pyudev.Monitor.from_netlink(context)
# observer = MonitorObserver(monitor)
# observer.deviceEvent.connect(log_event)
# monitor.start()
# --------------

# --------------
# is using PySide6, consider:
# • PySide6.QtSensors
# • PySide6.QtSerialBus & PySide6.QtSerialPort
# • PySide6.QtDbus for IPC
# • QIODevice and QStorageInfo in PySide6.QtCore
# --------------

# --------------
# OK, now I need to understand what does Solid provide to the KIO
# --------------

import sys, os, typing, pathlib, functools, itertools
from urllib.parse import urlparse, urlsplit
from collections import namedtuple
from enum import Enum, IntEnum
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

__HAS_PYUDEV__ = False

try:
    import pyudev
    __HAS_PYUDEV__ = True
except:
    __HAS_PYUDEV__ = False

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class DeviceType(IntEnum):
    """"""
    # NOTE: 2025-01-03 14:09:24 
    # Solid DeviceInterface::Type
    Unknown = 0,
    GenericInterface = 1,
    Processor = 2,
    Block = 3,
    StorageAccess = 4,
    StorageDrive = 5,
    OpticalDrive = 6,
    StorageVolume = 7,
    OpticalDisc = 8,
    Camera = 9,
    PortableMediaPlayer = 10,
    Battery = 12,
    NetworkShare = 14,
    Last = 0xffff,
    
class Device(QtCore.QObject):
    def __init__(self, parent:typing.Optional[QtCore.QObject]=None):
        super().__init__(parent=parent)

class DeviceInterface(QtCore.QObject):
    def __init__(self, parent:typing.Optional[QtCore.QObject]=None):
        super().__init__(parent=parent)
        
        # ### BEGIN DeviceInterfacePrivate
        self.backendObject:QtCore.QObject = QtCore.QObject()
        self.devicePrivate:Device = Device() # DevicePrivate
        self._backendObject:typing.Optional[QtCore.QObject] = None
        self._devicePrivate:typing.Optional[Device] = None
        # ### END DeviceInterfacePrivate
