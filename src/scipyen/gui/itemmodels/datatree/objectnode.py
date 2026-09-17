# $Id: objectnode.py $
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
import functools
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


NOTMEMOIZED = (
    tuple,
    type(None),
    type(MISSING),
    type(pd.NA),
    type,
    np.ndarray,
    np.bool,
    np.complexfloating,
    np.floating,
    np.integer,
    np.ufunc,
    types.ModuleType,
    pkgutil.ModuleInfo,
    typing.Callable,
    types.FunctionType,
    functools.partial
)


FUNCTION_TYPES = (
    types.FunctionType,
    types.BuiltinFunctionType,
    types.MethodType,
    types.BuiltinMethodType
    )

NOTINTROSPECTABLE = (
                    PODS + NOTMEMOIZED +
                    (types.ModuleType, pkgutil.ModuleInfo) +
                    FUNCTION_TYPES
                    )

@dataclasses.dataclass
class ObjectInfo:
    indirect: bool = False
    nChildren: int = 0
    objDataAsChild: bool = dataclasses.field(default = False)
    objInfo: str = dataclasses.field(default_factory=str)
    memberAccess: tuple[str] = dataclasses.field(default_factory=tuple)
    accessType: str | None = None
    objTip: str = dataclasses.field(default_factory=str)
    objType: type | None = None
    choices: dict = dataclasses.field(default_factory = dict)
    readOnly: bool = True
    objId: int | None = None

    # NOTE: 2026-09-16 10:22:19 fileystem-like stuff:
    # a "directory" is an object that is EITHER a hierarchical structure by itself
    #   e.g. a dict or dict-like, OR CAN BE REPRESENTED by a dict
    #   e.g. a sequence, including namedtuple, dataclass, following introspection
    #
    # a "file" is an object that is represented by itself, i.e. NO descending into
    # its structure -- NOTINTROSPECTABLE objects -> indirect = True
    #
    # collapses QExtendedInformation and QFileInfo in one type, omits logic
    # related to "real" file systems

class ObjectNode:
    def __init__(self, objInfo: ObjectInfo, name:str, parent: typing.Self | None = None):
        self._objInfo_ = objInfo

        if not isinstance(name, str) or len(name.strip()) == 0:
            self._name_ = "/" # for the root node

        else:
            self._name_ = name

        self._parent_: typing.Self = parent

        self._reference_: typing.Self | None = None

        # mapping pathKey ↦ ObjectNode
        self._children_: dict[str, typing.Self] = {}

        self._visibleChildren_: list[str] = []

        self._objDict_: dict | None = None

        self._dirtyChildrenIndex_: int = -1

        self._populatedChildren_: bool = False

        self._isVisible_: bool = False

    @property
    def isReference(self) -> bool:
        r"""Is this a node for an object already references in the tree?"""
        return isinstance(self._reference_, self.__class__)

    @property
    def objectInfo(self) -> ObjectInfo:
        return self._objInfo_

    @objectInfo.setter
    def objectInfo(self, value: ObjectInfo):
        if not isinstance(value, ObjectInfo):
            self._objInfo_ = ObjectInfo()
        else:
            self._objInfo_ = value

    @property
    def hasInformation(self) -> bool:
        return (
                    isinstance(self.objectInfo.objId, int)
                    and isinstance(self.objectInfo.objType, type)
                )

    @property
    def isBranch(self) -> bool:
        if self.hasInformation:
            return not self.objectInfo.indirect

        return len(self._children_) > 0

    @property
    def isLeaf(self)-> bool:
        return not self.isBranch

    def visibleLocation(self, childName: str) -> int:
        if len(self._visibleChildren_) and childName in self._visibleChildren_:
            return self._visibleChildren_.index(childName)

        return -1
