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
import treelib
from treelib import Tree, Node
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
    name: str = "/"
    r"""Symbol to which this object is bount (either in its parent, or in some namespace)"""

    indirect: bool = False
    r"""True if the object isinternally represented by a hierarchical structures such as a dict.
    This happens for obejcts that are themselves a 'flavor' of dict, a sequence (tuple, list, deque)
    a dataclass, and for introspectable objects.

    For these, the internal (indirect) representation is a mapping as follows:

    dict & related          => key¹ ↦ value

    sequences:
        tuple, list, deque  => index² ↦ value
        namedtuple          => field_name³ ↦ value

    dataclasses             => field_name³ ↦ value

    introspectable          => attribute_name³ ↦ value

.. note::

    ¹ by definition these are hashable objects; mot commonly, they are str or int
    but the language allows other types as well e.g. tuple, or any object type that
    can generate a unique hash value.

    ² sequences indexes are always int so they can be used as keys for the intermal
    representation, but CAUTION: the language allows user-defined types where an index
    might be anything that the usee deems useful (in theory; cannot think of an exmaple now)

    ³ by definition these are symbols, hence strings (str)

"""

    objDataAsChild: bool = dataclasses.field(default = False)
    r"""Used for arrays, to indicate they are to be shown in a table widget and not introspected
"""

    children: tuple = dataclasses.field(default_factory = tuple)
    r"""Symbols or indexes of the 'children' of the object.
A child is an attribute, a key/value pair (for mappings) or an element (for sequences)
This is always 0 for PODs, not introspectables and for objects where
objectDataAsChild is True.
"""
    containerChild: str = dataclasses.field(default_factory=str)
    r"""Name of container attribute (if any) where children are inspected.
For the special case of objects where only a child container is introspected
"""

    objInfo: str = dataclasses.field(default_factory=str)
    r"""A very short description string. Goes into the 3rd column"""

    memberAccess: tuple[str] = dataclasses.field(default_factory=tuple)
    r"""Describes the syntax for acccessing this object's members.
This is either:

* empty for objects with no access to their members,
* the tuple ('[',']') for item access in mappings or 1D indexing in sequences, e.g. ``A[x]``
* the tuple ('.',) for attribute access i.e., ``A.x``
"""

    accessType: str | None = None
    r"""Type of access:

* None for object that forbid access to their contents
* "attribute" for attribute style access (see above)
* "index" for item or index style access

This field is redundant, therefore flagged for culling.

"""
    # accessPath: tuple = dataclasses.field(default_factory = tuple)
    # r"""tuple of member access from the root of the hierarchy through the parentsm down to this object"""

    objTip: str = dataclasses.field(default_factory = str)
    objType: type | None = None
    # objKey: str = dataclasses.field(default_factory = str)
    objKeyType: type | None = None # hashable (str, int, ...) or weakref.ReferenceType - type of THIS object's key in parent'
    choices: dict = dataclasses.field(default_factory = dict)
    readOnly: bool = True
    readOnlyChildren: bool = True
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

    # NOTE: 2026-09-18 13:20:00
    # about access :
    # this is supposed to support item and attribute access, e.g.:
    #
    # X.Y[Z].U[T].V.W.[Q][R][S]
    #
    # with Y, U, V, W: str, and
    # T, Q, R, S: hashables (including str, int)
    #
    # i.e., no ellipses, range, slice objects or numpy-style indexing
    #
    # Breaking the above example down:
    #
    # -> getattr(X, Y).getitem(Z) ->
    #   -> getitem(..., )
    #
    # this may be contrived, wheres the current logic in datatreemodel
    # meesa more straightforward

    def isValid(self) -> bool:
        return isinstance(objId, int)

    def __hash__(self) -> int:
        field_values = tuple(getattr(self, f.name) for f in dataclasses.fields(self))
        return hash(field_values)

class ObjectNode:
    def __init__(self, obj, objInfo: ObjectInfo | None = None, parent: typing.Self | None = None):
        self._obj_ = obj

        self._objInfo_ = objInfo

        self._parentNode_: typing.Self = parent

        self._reference_: typing.Self | None = None

        # mapping pathKey ↦ ObjectNode
        self._children_: dict[str, typing.Self] = {}

        self._visibleChildren_: list[str] = []

        # self._objDict_: dict | None = None

        self._dirtyChildrenIndex_: int = -1

        self._populatedChildren_: bool = False

        self._isVisible_: bool = False

        self._path_ = self.getAccessPathFromParent()

    @property
    def children(self) -> dict:
        return self._children_

    @property
    def visibleChildren(self) -> list:
        return self._visibleChildren_

    @property
    def isReference(self) -> bool:
        r"""Is this a node for an object already references in the tree?"""
        return isinstance(self._reference_, self.__class__)

    @property
    def objectInfo(self) -> ObjectInfo:
        return self._objInfo_

    @objectInfo.setter
    def objectInfo(self, value: ObjectInfo | None):
        if not isinstance(value, ObjectInfo):
            self._objInfo_ = None
        else:
            self._objInfo_ = value

    @property
    def hasInformation(self) -> bool:
        return isinstance(self.objectInfo, ObjectInfo)

    @property
    def isBranch(self) -> bool:
        if self.hasInformation:
            return not self.objectInfo.indirect
        return False

        # return len(self._children_) > 0

    @property
    def isLeaf(self)-> bool:
        return not self.isBranch

    def visibleLocation(self, childName: str) -> int:
        if len(self._visibleChildren_) and childName in self._visibleChildren_:
            return self._visibleChildren_.index(childName)

        return -1

    def getAccessPathFromParent(self, pathOnly: bool = False) -> str:
        path = []
        if self.objectInfo is None:
            return path
        objectBinding = self.objectInfo.name            # the "key" for this object in parent -> str (always)
        bindingType = self.objectInfo.objKeyTypeRole    # objDict["accessType"] -> a type or None
        parentInfo = self._parentNode_.objectInfo

        if isinstance(parentInfo, ObjectInfo) and parentInfo.isValid():
            parentAccess = parentInfo.memberAccess      # parent's objDict["memberAccess"] -> tuple (always)
            parentAccessType = parentInfo.accessType    # parent's objDict["accessType"] -> str or None
            parentName = parentInfo.name

            if pathOnly:
                path.append(parentName)
            else:
                path.append(self._parentNode_.getAccessPathFromParent(pathOnly))

            if objectBinding:
                if len(parentAccess) == 1: # (".", )
                    # `attribute` access (`x.y`)
                    path.append(f"{parentAccess[0]}{objectBinding}")

                elif len(parentAccess) == 2:
                    # `item` or `index` access (`x[y]`)
                    if bindingType is weakref.ReferenceType:
                        path.append(f"{parentAccess[0]}{objectBinding}{parentAccess[1]}")
                    else:
                        if bindingType is str:
                            iB = f"{objectBinding}"
                        else:
                            try:
                                # expect trouble
                                iB = bindingType(objectBinding) # casting back to the hashable
                            except:
                                iB = objectBinding

                        path.append(f"{parentAccess[0]}{iB}{parentaccess[1]}")

        return "".join(path)


