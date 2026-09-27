# $Id: objectparser.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# from __future__ import print_function

import os # noqa
# import warnings
import types
import traceback
# import itertools
import inspect
import dataclasses
import numbers
import pathlib
import datetime
import fractions
import decimal
import pkgutil
import typing
import enum
# import functools
from functools import singledispatchmethod
from collections import deque, UserDict, OrderedDict
from dataclasses import MISSING
# import weakref
import math # noqa

import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
# __has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    # import PySide6
    # from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    # from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    # from qtpy import sip
    # from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    # __has_sip__ = True

try:
    from pyqtgraph.widgets.DataTreeWidget import HAVE_METAARRAY
except Exception: # noqa
    HAVE_METAARRAY = None

HAS_MESHIO = False
try:
    import meshio
    HAS_MESHIO = True
except: # noqa
    pass

# from pyqtgraph import (DataTreeWidget, TableWidget, )

import neo # noqa
if neo.__version__ >= '0.13.0':
    from neo.core.objectlist import ObjectList as NeoObjectList
import quantities as pq # noqa
import numpy as np
import scipy
import pandas as pd
import vigra
import meshio
# ### END 3rd party modules

# from core.qtutils import qVariant #, QVariantType #, qVariants, fromQVariant, isQObjectAlive)
import core.datatypes as datatypes # noqa
from core.datatypes import (is_namedtuple, TypeEnum)
from core.prog import (scipywarn, timefunc, processtimefunc)  # noqa
from core import taxonbridge
from core import bgbridge
from core.triggerprotocols import TriggerProtocol # noqa
from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType) # noqa
import core.datasignal as datasignal # noqa
from core.datasignal import (DataSignal, IrregularlySampledDataSignal) # noqa
import core.datazone as datazone # noqa
from core.datazone import (DataZone, Interval)
from core import xmlutils, strutils # noqa
from core import scipyen_quantities as scq
from core.utilities import unique
from core.prog import (safewrapper, safeguiwrapper, print_styled, # noqa
                       is_hashable)
from core.traitcontainers import (DataBag, DataBagTraitsObserver,) # noqa
from core.scipyendataclasses import (isDataclass, getField, getFieldOrProperty)
from core.datatypes import PODS

from ephys import ephys_protocol

# print(f"has brain globe: {bgbridge.hasBrainGlobe}")

# NOTE: 2026-02-07 09:14:19 FIXME/TODO
# to break cycling dependencies in systems.PrairieView, which needs this for the
# importer gui, MOVE the latter to a separate module
from systems.PrairieView import *

from imaging import vigrautils # noqa
import imaging.axiscalibration
from imaging.axiscalibration import (
    AxesCalibration,
    AxisCalibrationData,
    ChannelCalibrationData,
)
from imaging.axisutils import (axisTypeStrings, # noqa
                               getValueForAxisType,
                               getNameForAxisType)
import imaging.scandata # noqa
from imaging.scandata import (ScanData, AnalysisUnit) # noqa

from gui.itemmodels.roles import *

import gui.itemmodels.datatree.objectnode as onode
from gui.itemmodels.datatree.objectnode import ObjectInfo, ObjectNode

NOTINTROSPECTABLE = PODS + (types.ModuleType, pkgutil.ModuleInfo,)


class ObjectParser(QtCore.QThread):
    sig_result = Signal(dict, ObjectInfo, name="sig_result")
    def __init__(self, parent, **kwargs): #obj, objName: str, objectParentInfo: ObjectInfo | None = None,
        QtCore.QThread.__init__(self, parent)
        self._introspect_: bool = kwargs.pop("introspect", True)
        self._predicate_ = kwargs.pop("predicate", None)
        self._showPrivate_: bool = kwargs.pop("includePrivateMembers", False)
        self._showCallables_: bool = kwargs.pop("includeCallables", False)
        self._showTypeMembers_: bool = kwargs.pop("includeTypes", False)
        self._choices_: dict = kwargs.pop("choices", {})
        self._readOnly_: bool = kwargs.pop("readOnly", True)
        self._readOnlyChildren_: bool = kwargs.pop("readOnlyChildren", True)
        self._supportedDataTypes_ = kwargs.pop("supportedTypes", ())

        # NOTE: instantiate an empty object, because MISSING or None are valid
        # for my purposes here
        # HOWEVER WARNING: ALL python object types are a subclass of object
        # hence isinstance(…, object) will ALWAYS return True
        # therefore, this much be verified against the ACTUAL class of the data
        # i.e., test self._object_.__class__ == object
        self._object_: object = object() # python allows this
        self._objectName_: str | None = None
        self._objectParentInfo_ = None
        self._valueChoices_ = {}
        # if not isinstance(self._objectParentInfo_, ObjectInfo):
        #     self._objectParentInfo_ = ObjectInfo()

        # ----- Private API ----
        self._mutex_ = QtCore.QMutex()
        # ### BEGIN protected by mutex
        #
        self._condition_ = QtCore.QWaitCondition()
        self._path_ = deque()
        self._objects_ = deque()
        #
        # ### END   protected by mutex

        # self.start(QtCore.QThread.LowPriority)

    def __del__(self):
        self.requestAbort()
        self.wait()

    # def event(self, evt: QtCore.QEvent):
    #     if evt.type() == QtCore.QEvent.De

    def requestAbort(self):
        self.requestInterruption()
        locker = QtCore.QMutexLocker(self.mutex)
        self.condition.wakeAll()

    def setObject(self, obj, objName:str, /, valueChoices: dict | None = None, objParentInfo: ObjectInfo | None = None):
        self._object_ = obj
        self._objectName_ = objName
        self._objectParentInfo_ = objParentInfo
        if not isinstance(choices, dict):
            self._valueChoices_ = {}
        else:
            self._valueChoices_ = valueChoices

    def run(self):
        # NOTE: 2026-09-21 11:07:54
        # in the qfileinfogatherer this is run as an infinite loop
        # the ``forever`` statement (a macro)
        # but that is necessary to pick up changes in the underlying file system
        #
        # I don't need that, here;
        #
        # what I need is to ppiopulate an object node with child nodes in a
        # separate thread on its own


        try:
            self.setTerminationEnabled(True)
            locker = QtCore.QMutexLocker(self._mutex_)
            while not self.isInterruptionRequested():
                self._condition_.wait(self._mutex_)
            if self.isInterruptionRequested():
                return
            if self._object_.__class__ == object:
                return

            if not isinstance(self._objectName_, str):
                return

            if len(self._objectName_.strip()) == 0:
                objName = "/"
            else:
                objName = self._objectName_

            locker.unlock()
            self.setTerminationEnabled(False)
            objInfo = onode.parseObject(self._object_, objName,
                                        introspect=self._introspect_,
                                        predicate=self._predicate_,
                                        includePrivate=self._showPrivate_,
                                        includeCallables=self._showCallables_,
                                        includeTypeMembers=self._showTypeMembers_,
                                        choices=self._choices_,
                                        readOnly=self._readOnly_,
                                        readOnlyChildren=self._readOnlyChildren_)
            self.sig_result.emit(objInfo)

        except:    # noqa: E722
            traceback.print_exc()

