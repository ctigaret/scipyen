# $Id: objectnode.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# from __future__ import print_function

import os # noqa
# import warnings
import types
import traceback  # noqa: F401
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
from functools import singledispatch
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
from treelib import (Tree, Node)
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

# from gui.itemmodels.datatree.objectnode import ObjectInfo #, ObjectNode
# from gui.itemmodels.datatree.objectparser import ObjectParser


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

NOTINTROSPECTABLE = PODS + (types.ModuleType, pkgutil.ModuleInfo,) + FUNCTION_TYPES

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
    objKey: str = dataclasses.field(default_factory = str)
    objKeyType: type | None = None # hashable (str, int, ...) or weakref.ReferenceType - type of THIS object's key in parent'
    choices: dict = dataclasses.field(default_factory = dict)
    readOnly: bool = True
    readOnlyChildren: bool = True
    objId: int | None = None
    referenceInfo: typing.Self | None = None

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

class ObjectNode(Node):
    def __init__(self, tag: str | None = None, identifier: str | None = None,
                 data: typing.Any = dataclasses.MISSING,
                 objInfo: ObjectInfo | None = None,
                 ):
        # print(f"{self.__class__.__init__}(tag={tag}, identifier={identifier}, data={data}, objInfo={objInfo})")
        # super().__init__(tag, identifier)
        if data is not dataclasses.MISSING:
            super().__init__(tag, identifier, data=data)

        else:
            super().__init__(tag, identifier)

        self._objectInfo_ = objInfo

    @property
    def objectInfo(self) -> ObjectInfo:
        return self._objectInfo_

    @property
    def intialized(self) -> bool:
        return isinstance(self._objectInfo_, ObjectInfo)


# @timefunc
def findObjectNodes(tree: Tree, **kwargs):
    def _checkNodeInfoAttribute_(info, **kwargs):
        return all(getattr(info, item[0], None) == item[1] for item in kwargs.items())

    yield from tree.filter_nodes(lambda node: isinstance(node, ObjectNode) and _checkNodeInfoAttribute_(node, **kwargs))

# @timefunc
def nodesWithTag(tree: Tree, tag: str):
    yield from tree.filter_nodes(lambda node: node.tag == tag)

# @timefunc
def nodesWithPayload(tree: Tree, payload: typing.Any = None):
    yield from tree.filter_nodes(lambda node: node.data is payload)

@timefunc
def populateNode(tree: Tree, node: ObjectNode,
                introspect: bool = False,
                predicate = None,
                includePrivate: bool = False,
                includeCallables : bool = False,
                includeTypeMembers: bool = False,
                choices: dict | None = None,
                readOnly: bool = False,
                readOnlyChildren: bool = False):
    def getitem(obj, item, default=None):
        try:
            return obj.__getitem__(item)
        except:  # noqa: E722
            return default

    accessor = None

    assert isinstance(node, ObjectNode), f"Expecting an ObjectNode instance; instead got a {type(node).__name__}"

    if node.identifier not in tree:
        raise ValueError(f"The node {node.tag} with identifier {node.identifier} does not belong to the tree {tree.identifier}")

    if node.is_root(tree.identifier) and node.data is None:
        scipywarn(f"The root node ({node.tag} with identifier {node.identifier}) does not associate any data; please set data first")
        return

    # elif node.data is None:
    #     nodeAccessPath = []
    #     parentNode = node.predecessor(tree.identifier)
    #     assert isinstance(parentNode, ObjectNode), f"The node {node.tag} with identifier {node.identifier} has no predecessor, yet it not a root node"
    #     accessToThisNode = (parentNode.objectInfo.memberAccess, node.objectInfo.name)


    else:
        if (
            len(node.objectInfo.children) == 0
            # or not node.objectInfo.indirect
            or node.objectInfo.objDataAsChild
            or len(node.objectInfo.memberAccess) == 0
            or len(node.successors(tree.identifier)) > 0
            ):
            # TODO: 2026-09-21 14:16:58
            # check if ALL children in objectInfo hve a corresponding successor
            # node in this node; else, add missing nodes up to max number of children
            # we want to "populate"
            return

        if (
            node.objectInfo.memberAccess == (".", )
            and node.objectInfo.accessType == "attribute"
            ):
            accessor = getattr

        elif(
            node.objectInfo.memberAccess == ("[","]")
            and node.objectInfo.accessType == "index"
            ):
            accessor = getitem

        else:
            scipywarn(f"Unclear access method for children of data for node {node.tag} with {node.identifier}")
            return

        if accessor is None:
            return

        for child in node.objectInfo.children:
            # print(f"inspecting '{child}' of node '{node.tag}'")
            keyType = type(child)
            key = f"{child}"
            obj = accessor(node.data, child, None)
            # visited = list(tree.filter_nodes(lambda n: n.data is obj))
            oInfo = parseObject(obj, child, introspect=introspect,
                                predicate=predicate, includePrivate=includePrivate,
                                includeCallables=includeCallables,
                                includeTypeMembers=includeTypeMembers,
                                choices=choices,
                                readOnly=readOnly,
                                readOnlyChildren=readOnlyChildren,
                                objKey = key,
                                objKeyType = keyType,
                                )

            # oInfo.objKey = key
            # oInfo.objKeyType = keyType

            childNode = ObjectNode(tag=oInfo.name, data=obj, objInfo=oInfo)

            tree.add_node(childNode, parent=node)

def populateNode2(tree: Tree, node: ObjectNode,
                introspect: bool = False,
                predicate = None,
                includePrivate: bool = False,
                includeCallables : bool = False,
                includeTypeMembers: bool = False,
                choices: dict | None = None,
                readOnly: bool = False,
                readOnlyChildren: bool = False):
    def getitem(obj, item, default=None):
        try:
            return obj.__getitem__(item)
        except:  # noqa: E722
            return default

    accessor = None

    assert isinstance(node, ObjectNode), f"Expecting an ObjectNode instance; instead got a {type(node).__name__}"

    if node.identifier not in tree:
        raise ValueError(f"The node {node.tag} with identifier {node.identifier} does not belong to the tree {tree.identifier}")

    if node.is_root(tree.identifier) and node.data is None:
        scipywarn(f"The root node ({node.tag} with identifier {node.identifier}) does not associate any data; please set data first")
        return

    # elif node.data is None:
    #     nodeAccessPath = []
    #     parentNode = node.predecessor(tree.identifier)
    #     assert isinstance(parentNode, ObjectNode), f"The node {node.tag} with identifier {node.identifier} has no predecessor, yet it not a root node"
    #     accessToThisNode = (parentNode.objectInfo.memberAccess, node.objectInfo.name)


    else:
        if (
            len(node.objectInfo.children) == 0
            or not node.objectInfo.indirect
            or node.objectInfo.objDataAsChild
            or len(node.objectInfo.memberAccess) == 0
            or len(node.successors(tree.identifier)) > 0
            ):
            # TODO: 2026-09-21 14:16:58
            # check if ALL children in objectInfo hve a corresponding successor
            # node in this node; else, add missing nodes up to max number of children
            # we want to "populate"
            return

        if (
            node.objectInfo.memberAccess == (".", )
            and node.objectInfo.accessType == "attribute"
            ):
            accessor = getattr

        elif(
            node.objectInfo.memberAccess == ("[","]")
            and node.objectInfo.accessType == "index"
            ):
            accessor = getitem

        else:
            scipywarn(f"Unclear access method for children of data for node {node.tag} with {node.identifier}")
            return

        if accessor is None:
            return

        for child in node.objectInfo.children:
            print(f"inspecting '{child}' of node '{node.tag}'")
            keyType = type(child)
            key = f"{child}"
            obj = accessor(node.data, child, None)
            # visited = list(tree.filter_nodes(lambda n: n.data is obj))
            visited = list(nodesWithPayload(tree, obj))
            if len(visited):
                print([n.tag for n in visited])
                existingNode = visited[0]
                print(f"\t'{child}' shares data with existing node '{existingNode.tag}'")
                oInfo = ObjectInfo(name=child,
                                   children=(),
                                   objInfo = f"Reference to {existingNode.objectInfo.name}",
                                   memberAccess = (),
                                   objTip = existingNode.objectInfo.objTip,
                                   objType = existingNode.objectInfo.objType,
                                   objKey = key,
                                   objKeyType = keyType,
                                   objId = existingNode.objectInfo.objId)
                oInfo.referenceInfo = existingNode.objectInfo
                childNode = ObjectNode(tag=oInfo.name, objInfo=oInfo)

            else:
                oInfo = parseObject(obj, child, introspect=introspect,
                                    predicate=predicate, includePrivate=includePrivate,
                                    includeCallables=includeCallables,
                                    includeTypeMembers=includeTypeMembers,
                                    choices=choices,
                                    readOnly=readOnly,
                                    readOnlyChildren=readOnlyChildren,
                                    objKey = key,
                                    objKeyType = keyType,
                                   )

                # oInfo.objKey = key
                # oInfo.objKeyType = keyType

                childNode = ObjectNode(tag=oInfo.name, data=obj, objInfo=oInfo)

            tree.add_node(childNode, parent=node)

def createNode(obj, objName: str, /,
               storeData: bool = True,
               introspect: bool = False,
               predicate = None,
               includePrivate: bool = False,
               includeCallables : bool = False,
               includeTypeMembers: bool = False,
               choices: dict | None = None,
               readOnly: bool = False,
               readOnlyChildren: bool = False,
               objKey: str | None = None,
               objKeyType: type | None = None
               ) -> ObjectNode:


    objectInfo = parseObject(obj, objName,
                             introspect=introspect,
                             predicate=predicate,
                             includePrivate=includePrivate,
                             includeCallables=includeCallables,
                             includeTypeMembers=includeTypeMembers,
                             choices=choices,
                             readOnly=readOnly,
                             readOnlyChildren=readOnlyChildren,
                             objKey = objKey,
                             objKeyType = objKeyType)

    # identifier = f"{objectInfo.objId}"
    nodeName = objectInfo.name
    # NOTE: 2026-09-20 13:34:34
    # treelib.node.Node API:
    # Node(tag: str, identifier: str,
    #       expanded: bool,
    #       data: Any = None)
    #
    # with identifier being unique (in the Tree's context)

    if storeData:
        return ObjectNode(tag=nodeName, data = obj, objInfo = objectInfo)

    else:
        return ObjectNode(tag=objName, objInfo = objectInfo)


@singledispatch
def parseObject(obj: object,
                objName: str, /,
                introspect: bool = False,
                predicate = None,
                includePrivate: bool = False,
                includeCallables : bool = False,
                includeTypeMembers: bool = False,
                choices: dict | None = None,
                readOnly: bool = False,
                readOnlyChildren: bool = False,
                objKey: str | None = None,
                objKeyType: type | None = None
                ) -> ObjectInfo:
    r""" TODO Documentation
    """
    # TODO 2026-03-28 16:32:58
    # configuration file to determine if instances of some user-defined types
    # are also editable or not -> use it to determine the readOnly flag, above
    indirect: bool = False
    tip: str = type(obj).__name__
    objDataAsChild: bool = False
    objType = type(obj)
    objId = id(obj)
    readOnly = False
    readOnlyChildren = False
    children = ()

    choices = check_obj_choices(objType, choices)

    if isDataclass(obj):
        children = introspectObject(obj, predicate = predicate,
                  includePrivate = includePrivate,
                  includeCallables = includeCallables,
                  includeTypeMembers = includeTypeMembers)
        indirect = True

        if includePrivate:
            readOnlyChildren = True

        n = len(children)
        info = f"{n} {strutils.pluralize('member', n)}"
        tip = f"{type(obj).__name__} (dataclass)"
        objDataAsChild = False
        memberAccess = (".",) # access to obj members!
        accessType = "attribute"
        readOnly = False

    elif (
        HAVE_METAARRAY
        and hasattr(obj, "implements")
        and obj.implements("MetaArray")
        ):
        if introspect:
            children = introspectObject(obj, predicate = predicate,
                    includePrivate = includePrivate,
                    includeCallables = includeCallables,
                    includeTypeMembers = includeTypeMembers)

        indirect = True
        objDataAsChild = False
        info = ""
        memberAccess = ("[", "]")
        accessType = "index"

    elif HAS_MESHIO and isinstance(obj, meshio.Mesh):
        # pData = obj
        indirect=False,
        s = " × ".join(list(map(lambda x: f"{x}", obj.points.shape))) # noqa
        info = f"{obj.points.size} points ({s})"
        tip = type(obj).__name__
        objDataAsChild = False
        memberAccess = ()
        accessType = None
        readOnly = True
        readOnlyChildren = True
        children = ()

    elif introspect and introspectable(obj):
        # print(f"{self.__class__.__name__}.parseObject({type(obj)}) introspectable")
        children = introspectObject(obj, predicate = predicate,
                  includePrivate = includePrivate,
                  includeCallables = includeCallables,
                  includeTypeMembers = includeTypeMembers)
        # pData, fullCount, nChildren = self.generate_dict(obj, includePrivateMembers)
        indirect = True
        objDataAsChild = False

        n = len(children)

        info = f"{n} {strutils.pluralize('member', n)}"
        memberAccess = (".", )
        accessType = "attribute"
        readOnly = True
        readOnlyChildren = True

    else:
        # pData = obj
        indirect = False
        info = f"{obj}"
        tip = f"{obj}"
        objDataAsChild = False
        memberAccess = ()
        accessType = None
        # nChildren = 0
        # nVisibleChildren = 0

    # if len(objectParentInfo.objectAccessPath):
    #     if len(objectParentInfo)

    infoDict = {
        "name": objName,
        "indirect": indirect,
        "children": children,
        "objDataAsChild": objDataAsChild,
        "objInfo": info,
        "memberAccess": memberAccess,
        "accessType": accessType,
        # "objectAccessPath": objectAccessPath,
        "objTip": tip,
        "objType": objType,
        "choices": choices,
        "readOnly": readOnly,
        "readOnlyChildren": readOnlyChildren,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        # "containerChild": ""
        }

    return ObjectInfo(**infoDict)
    # return pData, objectInfo

@parseObject.register(types.NoneType)
@parseObject.register(type(MISSING))
@parseObject.register(type(pd.NA))
def _parseObject_(obj: types.NoneType | type(MISSING) | type(pd.NA),
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objType = type(obj)
    objId = id(obj)
    # pData = obj
    indirect = False
    info = f"{obj}"
    tip = f"{obj}"
    objDataAsChild = False
    memberAccess = ()
    accessType = None
    choices = check_obj_choices(objType, choices)

    # TODO/FIXME: 2026-03-28 16:57:15
    # mechanism to see if a new object of another type is acceptable here, in which case call a UI c'tor'
    readOnly = True
    readOnlyChildren = True

    infoDict = {
        "name": objName,
        "indirect": indirect,
        "objDataAsChild": objDataAsChild,
        "objInfo": info,
        "memberAccess": memberAccess,
        "accessType": accessType,
        "objTip": tip,
        "objType": objType,
        "choices": choices,
        "readOnly": readOnly,
        "readOnlyChildren": readOnlyChildren,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(datetime.datetime)
@parseObject.register(datetime.date)
@parseObject.register(datetime.time)
@parseObject.register(datetime.timedelta)
@parseObject.register(datetime.timezone)
def _parseObject_(obj: typing.Union[datetime.datetime,   # noqa: F811,UP007
                                    datetime.date,
                                    datetime.time,
                                    datetime.timedelta,
                                    datetime.timezone],
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    # NOTE: 2026-09-20 11:37:16
    # NEVER introspected

    objType = type(obj)
    objId = id(obj)
    info = f"{obj}"
    tip = f"{obj}"
    objDataAsChild = False
    memberAccess = ()
    accessType = None
    readOnly = False

    infoDict = {
        "name": objName,
        "indirect": False,
        "children": (),
        "objDataAsChild": objDataAsChild,
        "objInfo": info,
        "memberAccess": memberAccess,
        "accessType": accessType,
        "objTip": tip,
        "objType": objType,
        "choices": {},
        "readOnly": readOnly,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(types.FunctionType)
@parseObject.register(types.BuiltinFunctionType)
@parseObject.register(types.MethodType)
@parseObject.register(types.BuiltinMethodType)
def _parseObject_(obj: typing.Union[types.FunctionType,  # noqa: F811,UP007
                                    types.BuiltinFunctionType,
                                    types.MethodType,
                                    types.BuiltinMethodType],
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    # print(f"{self.__class__.__name__}.parseObject(obj: {type(obj)})")
    objType = type(obj)
    objId = id(obj)
    choices = check_obj_choices(objType, choices)

    tip = f"{obj}"
    word = "Function" if isinstance(obj, (types.FunctionType, types.BuiltinFunctionType)) else "Method"

    try:
        # NOTE: 2026-05-01 09:24:50
        # because signature of builtin functions e.g. on PyQt side) cannot be inspected
        signature = f"{inspect.signature(obj)}"

    except: # noqa
        signature = ""

    info = f"{word} {obj.__qualname__}{signature} from module {obj.__module__}"

    infoDict = {
        "name": objName,
        "indirect": False,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (),
        "accessType": None,
        "choices": choices,
        "readOnly": False, # TODO/FIXME
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(type)
@parseObject.register(enum.EnumType)
@parseObject.register(enum.Enum)
@parseObject.register(enum.IntEnum)
@parseObject.register(enum.Flag)
@parseObject.register(TypeEnum)
def _parseObject_(obj: typing.Union[type, enum.EnumType, # noqa: F811,UP007
                                    enum.Enum,
                                    enum.Flag,
                                    TypeEnum],
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    # NOTE: 2026-09-20 11:47:13
    # NEVER introspected
    readOnly = True
    readOnlyChildren = True
    objType = type(obj)
    objId = id(obj)
    info = obj
    tip = str(obj)
    choices = check_obj_choices(objType, choices)
    memberAccess = ()
    accessType = None

    if isinstance(obj, (
        enum.EnumType, TypeEnum, enum.Enum, enum.IntEnum, enum.Flag)):
        memberAccess = (".", )
        accessType = "attribute"
        readOnly = False
        readOnlyChildren = False

        if isinstance(obj, (enum.Enum, enum.IntEnum, TypeEnum, enum.Flag)):
            info = obj.name

        if hasattr(obj, "__members__"):
            choices = dict(obj.__members__)

        elif hasattr(type(obj), "__members__"):
            choices = dict(type(obj).__members__)

        else:
            try:
                # NOTE: 2026-02-13 17:45:45
                # this only works for TypeEnum
                #
                choices = dict(zip(obj.names(), obj.values()))

            except: # noqa
                scipywarn(f"Cannot access enumeration values for {type(obj).__name__}")
                choices = {}

    infoDict = {
        "name": objName,
        "indirect": False,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": memberAccess,
        "accessType": accessType,
        "choices": choices,
        "readOnly": readOnly,
        "readOnlyChildren": readOnlyChildren,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(pkgutil.ModuleInfo)
def _parseObject_(obj: pkgutil.ModuleInfo, # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objType = type(obj)
    tip = f"{objType}.__name__"
    objId = id(obj)
    choices = check_obj_choices(objType, choices)
    if introspect:
        children = tuple(obj._fields)
        info = f"{len(children)} fields"
        indirect = True
    else:
        children = ()
        info = ""
        indirect = False

    infoDict = {
        "name": objName,
        "indirect": indirect,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (".",),
        "accessType": "attribute",
        "choices": choices,
        "readOnly": True,
        "readOnlyChildren": True,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return objectInfo(**infoDict)

@parseObject.register(bgbridge.Structure)
def _parseObject_(obj: bgbridge.Structure,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objType = type(obj)
    objId = id(obj)
    choices = check_obj_choices(objType, choices)

    if introspect:
        children = introspectObject(
            obj,
            predicate = predicate,
            includePrivate = includePrivate,
            includeCallables = includeCallables,
            includeTypeMembers = includeTypeMembers
            )
        indirect = True

    else:
        children = ()
        indirect = False


    info = f"{type(obj).__name__} ID: {obj['id']}, {obj['name']} ({obj['acronym']})"

    tip = type(obj).__name__

    infoDict = {
        "name": objName,
        "indirect": indirect,
        "children": children,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": ("[", "]"),
        "accessType": "attribute",
        "choices": choices,
        "readOnly": True,
        "readOnlyChildren": True,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(ephys_protocol.ElectrophysiologyProtocol)
def _parseObject_(obj: ephys_protocol.ElectrophysiologyProtocol,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objType = type(obj)
    objId = id(obj)
    # choices = check_obj_choices(objType, choices)

    if introspect:
        children = introspectObject(obj,
                            includePrivate = includePrivate,
                            includeCallables = includeCallables,
                            includeTypeMembers = includeTypeMembers)
        indirect = True
    else:
        children = ()
        indirect = False

    info = obj.name
    tip = type(obj).__name__
    infoDict = {
        "name": objName,
        "indirect": indirect,
        "children": children,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (".",),
        "accessType": "attribute",
        "choices": choices,
        "readOnly": True,
        "readOnlyChildren": True,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(taxonbridge.Taxon)
def _parseObject_(obj: taxonbridge.Taxon,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objType = type(obj)
    objId = id(obj)
    choices = check_obj_choices(objType, choices)

    if introspect:
        children = introspectObject(obj,
                                includePrivate = includePrivate,
                                includeCallables = includeCallables,
                                includeTypeMembers = includeTypeMembers)
        indirect = True
    else:
        children = ()
        indirect = False

    info = f"{obj}"

    tip = type(obj).__name__

    infoDict = {
        "name": objName,
        "indirect": indirect,
        "children": children,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (".",),
        "accessType": "attribute",
        "choices": choices,
        "readOnly": True,
        "readOnlyChildren": True,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(dict)
@parseObject.register(types.MappingProxyType)
@parseObject.register(UserDict)
@parseObject.register(OrderedDict)
def _parseObject_(obj: typing.Union[dict,              # noqa: F811,UP007
                                    types.MappingProxyType,
                                    UserDict,
                                    OrderedDict],
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    # NOTE: 2021-07-20 09:52:34
    # cannot sort te keys in dict objects with mixed key types
    # therefore we resort to an indexing vector
    ndx = [
        i[1]
        for i in sorted(
                        (str(k[0]), k[1])
                        for k in zip(obj, range(len(obj)))
                        )
        ]

    keys = tuple(obj.keys())

    children = tuple(keys[k] for k in ndx) # the actual mapping keys sorted by their string representation

    info = f"{len(obj)} key / value {strutils.pluralize('pair', len(children))}"
    tip = type(obj).__name__

    infoDict = {
        "name": objName,
        "indirect": False,
        "children": children,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip":tip,
        "memberAccess": ("[", "]"),
        "accessType": "index",
        "choices": choices,
        "readOnly": True,
        "readOnlyChildren": False,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(list)
@parseObject.register(tuple)
@parseObject.register(deque)
@parseObject.register(NeoObjectList)
@parseObject.register(set)
@parseObject.register(frozenset)
@parseObject.register(os.stat_result)
def _parseObject_(obj: typing.Union[list, tuple, deque,  # noqa: UP007,F811
                                    set,
                                    NeoObjectList,
                                    frozenset,
                                    os.stat_result],
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    tip = objType.__name__
    readOnly = True
    readOnlyChildren = False

    if isinstance(obj, (tuple, frozenset)) or readOnly:
        readOnly = True
        readOnlyChildren = True

    if is_namedtuple(obj):
        if introspect:
            oDict = obj._asDict() if hasattr(obj, "_asDict") else obj._asdict()
            children = tuple(oDict)
            indirect = True
        else:
            children = ()
            indirect = False
        # pData = obj._asDict() if hasattr(obj, "_asDict") else obj._asdict()
        tip += "(namedtuple)"
        memberAccess = (".",)
        accessType = "attribute"
        readOnlyChildren = True

    elif isinstance(obj, os.stat_result):
        if introspect:
            children = introspectObject(obj, predicate=predicate,
                                        includePrivate=includePrivate,
                                        includeCallables=includeCallables,
                                        includeTypeMembers=includeTypeMembers)
            indirect = True
        else:
            children = ()
            indirect = False
        # pData = dict(filter(lambda t: any(t[0].startswith(s) for s in ("n_", "st_")), inspect.getmembers(obj)))
        tip += "(stat result)"
        memberAccess = (".",)
        accessType = "attribute"
        readOnlyChildren = True

    else:
        if introspect:
            children = tuple(range(len(obj)))
            indirect = True
        else:
            children = ()
            introspect = False

        memberAccess = ("[","]")
        accessType = "index"

    n = len(children)

    info = f"{n} {strutils.pluralize('element', n)}"

    infoDict = {
        "name": objName,
        "indirect": indirect,
        "children": children,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": memberAccess,
        "accessType": accessType,
        "choices": choices,
        "readOnly": readOnly,
        "readOnlyChildren": readOnlyChildren,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(str)
@parseObject.register(bytes)
@parseObject.register(bytearray)
def _parseObject_(obj: str | bytes | bytearray,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    # NOTE: 2026-09-20 11:37:16
    # NEVER introspected

    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    objDataAsChild = False
    tip = objType.__name__

    if isinstance(obj, str) and strutils.is_path(obj):
        objDataAsChild = False
        info = obj
        readOnly = True
        readOnlyChildren = True

    else:
        n = len(obj)
        if n > 100:
            info = (
                obj[:97] if isinstance(obj, str) else obj.decode()[:97]
            )
            info += "..."
            objDataAsChild = True

        else:
            info = obj if isinstance(obj, str) else obj.decode()

        if isinstance(obj, (bytes, bytearray)) or readOnly:
            readOnly = True
            readOnlyChildren = True

    infoDict =  {
        "name": objName,
        "indirect": False,
        "objDataAsChild": objDataAsChild,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (),
        "accessType": None,
        "choices": choices,
        "readOnly": readOnly,
        "readOnlyChildren": readOnlyChildren,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

    return  objectInfo

@parseObject.register(pathlib.Path)
def _parseObject_(obj: pathlib.Path,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    # NOTE: 2026-09-20 11:37:16
    # NEVER introspected
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    # info = f"{obj}"
    info = obj.as_posix()
    tip = objType.__name__
    indirect = False

    infoDict = {
        "name": objName,
        "indirect": indirect,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (),
        "accessType": None,
        "choices": choices,
        "readOnly": readOnly,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(*infoDict)

@parseObject.register(bool)
@parseObject.register(int)
@parseObject.register(float)
@parseObject.register(complex)
@parseObject.register(fractions.Fraction)
@parseObject.register(decimal.Decimal)
@parseObject.register(numbers.Number)
@parseObject.register(np.integer)
@parseObject.register(np.floating)
@parseObject.register(np.complexfloating)
def _parseObject_(obj: typing.Union[bool, int, float, complex,   # noqa: UP007,F811,PYI041
                                    fractions.Fraction,
                                    decimal.Decimal,
                                    numbers.Number,
                                    np.integer, np.floating,
                                    np.complexfloating],
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    # NOTE: 2026-09-20 11:37:16
    # NEVER introspected
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    tip = objType.__name__

    infoDict = {
        "name": objName,
        "indirect": False,
        "objDataAsChild": False,
        "objInfo": f"{obj}",
        "objType": objType,
        "objTip": tip,
        "memberAccess": (),
        "accessType": None,
        "choices": choices,
        "readOnly": readOnly,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(types.SimpleNamespace)
def _parseObject_(obj: types.SimpleNamespace, # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    if introspect:
        children = introspectObject(obj, predicate=predicate,
                                    includePrivate=includePrivate,
                                    includeCallables=includeCallables,
                                    includeTypeMembers=includeTypeMembers)
        n = len(children)
        info = f"{n} {strutils.pluralize('member', n)}"
    else:
        children = ()
        info = ""

    tip = type(obj).__name__

    infoDict =  {
        "name": objName,
        "indirect": True,
        "children": children,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (".", ),
        "accessType": "attribute",
        "choices": choices,
        "readOnly": True,
        "readOnlyChildren": False,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(types.ModuleType)
def _parseObject_(obj: types.ModuleType, # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    tip = type(obj).__name__

    mname = getattr(obj, "__name__", None)

    mfile = getattr(obj, "__file__", None)

    if isinstance(mname, str) and len(mname.strip()):
        if objName != mname:
            alias = f" (aliased as {objname})"
        else:
            alias = ""
    else:
        mname = ""
        alias = f" (aliased as {objName})"

    if isinstance(mfile, str) and len(mfile.strip()):
        mfile = " from file " + mfile
    else:
        mfile = ""

    info = f"Module{mname}{mfile}{alias}"

    if introspect:
        children = introspectObject(obj, predicate=predicate,
                                    includePrivate=includePrivate,
                                    includeCallables=includeCallables,
                                    includeTypeMembers=includeTypeMembers)
        indirect = True
    else:
        children = ()
        indirect = False

    infoDict = {
        "name": objName,
        "indirect": indirect,
        "children": children,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (".", ),
        "accessType": "attribute",
        "choices": choices,
        "readOnly": True,
        "readOnlyChildren": True,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(vigra.filters.Kernel1D)
@parseObject.register(vigra.filters.Kernel2D)
def _parseObject_(obj: vigra.filters.Kernel1D | vigra.filters.Kernel2D, # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    # ### BEGIN NOTE: 2026-02-08 21:20:00 TODO/FIXME
    #
    # enable representation of the kernel as: (think hard & choose one)
    #
    # for 1D kernels:
    # ===============
    #
    # REMEMBER: read-write access to the sample values for a 1D kernel is:
    # k1d[k] where k varies from [-s to s] where s is the kernel window,
    # e.g.
    #
    # .. ::
    #
    #   from matplotlib import pyplot as plt
    #
    #   g1d = vigra.filters.Kernel1D()
    #   g1d.initGaussian(1.0, 1.0, 2.0) # window = 2
    #   x,y = vigrautils.lernel2array(g1d)
    #   x
    #   array([-2, -1,  0,  1,  2])
    #   y
    #   array([0.0545, 0.2442, 0.4026, 0.2442, 0.0545])
    #
    #   g1d[-1] = 0.3
    #
    #   -> y = array([0.0545, 0.3, 0.4026, 0.2442, 0.0545])
    #
    #   plt.plot(x,y,'o')
    #
    #
    # (a) pd.Series -> TabeEditorWidget: probably the most intuitively
    #   accessible, but not straightforward as it involves an extra layer
    #  of bidirectional conversion
    #
    # (b) 2D np.ndarray, with sample indices in the 1st, *immutable* column,
    #   and sample values in the second -> TableEditorWidget
    #
    #   also requires bidirectional conversion, but the vigrautils can do the
    #   trick, and editing is done directly without need to convert indices.
    #
    # (c) as a dict mapping kernel_sample_index ↦ sample value
    #   {-2: 0.0545, -1: 0.2442, 0: 0.4026, 1: 0.2442, 2: 0.0545}
    #   -> delegate editor for each value
    #       this MAY seem straightforward, but unwieldy / cumbersome
    #       appearance for large kernels
    #
    #
    # for 2D kernels:
    # ===============
    #
    # Read-write access to the sample is of the form k2d[x,y]
    #
    # .. ::
    #
    #   from matplotlib import pyplot as plt
    #
    #   g2d = vigra.filters.Kernel2D()
    #   g2d.initDisk(1) # disk (averaging) kernel with radius 1
    #   x, y, z = vigrautils.kernel2array(g2d)
    #
    #   x
    #   -> array([[ 1,  0, -1],
    #             [ 1,  0, -1],
    #             [ 1,  0, -1]], shape=(3, 3)) # x coordinates of each column
    #
    #   y
    #   -> array([[ 1,  1,  1],
    #             [ 0,  0,  0],
    #             [-1, -1, -1]], shape=(3, 3)) # y coordinates of each row
    #
    #   z
    #   -> array([[0.1111, 0.1111, 0.1111],
    #             [0.1111, 0.1111, 0.1111],
    #             [0.1111, 0.1111, 0.1111]], shape=(3, 3)) # sample values
    #
    #   fig, ax = plt.subplots()
    #   ax.pcolormesh(x,y,z)
    #
    # I don't seem to have many options here: use ogrid option to get the
    #   x, y mesh coordinates and kernel sample values, then create a
    #   pd.DataFrame with column index the X array, roww index Y array
    #   and data, the sample values ... then use TableEditorWidget...
    #
    # TODO/FIXME: 2026-02-08 23:12:56
    # Better still, enable direct editing in
    # TableEditorWidget/TabularDataModel possibly via pd.DataFrame
    # FIXME/TODO
    #
    # ### END   NOTE: 2026-02-08 21:20:00 TODO/FIXME

    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    tip = type(obj).__name__

    if isinstance(obj, vigra.filters.Kernel1D):
        n = int(obj.size())
        info = f"with {n} {strutils.pluralize('sample', n)}"
        memberAccess = ("[","]")
        accessType = "index"

    else:
        h = int(obj.height())
        w = int(obj.width())
        info = f"with {h} × {w} {strutils.pluralize('sample', h*w)}"
        memberAccess = ("[", ",", "]")
        accessType = "indexes"

    infoDict = {
        "name": objName,
        "indirect": False,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": memberAccess,
        "accessType": accessType,
        "choices": {},
        "readOnly": True, # pending a new widget for this
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(pd.DataFrame)
@parseObject.register(pd.Series)
@parseObject.register(pd.Index)
def _parseObject_(obj: typing.Union[pd.DataFrame,      # noqa: F811,UP007
                                    pd.Series,
                                    pd.Index],
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    # NOTE: 2026-09-20 11:37:16
    # NEVER introspected
    # NOTE: 2026-09-20 11:40:40
    # ALWAYS as a child object (to be shown in its own table widget)
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    # NOTE: 2026-02-11 21:09:34
    # TableEditorWidget gives direct read-write access, so no direct access
    # required in this model
    memberAccess = ()

    # Don;t be fooled by the nomenclature; for a column index, this is the
    # number of columns
    nrows = len(obj)

    if isinstance(obj, pd.DataFrame):
        ncols = len(obj.columns)
        rows = strutils.pluralize('row', nrows)

        cols = strutils.pluralize('column', ncols)

        info = f"{nrows} {rows} × {ncols} {cols}"

    elif isinstance(obj, pd.Series):
        rows = strutils.pluralize('row', nrows)
        info = f"{nrows} {rows}, dtype = {obj.dtype}"

    else:
        rows = strutils.pluralize('element', nrows)

        info = f"{nrows} {rows}"

    tip = type(obj).__name__

    infoDict = {
        "name": objName,
        "indirect": False,
        "objDataAsChild": True,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": memberAccess,
        "accessType": None,
        "choices": choices,
        "readOnly": True,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)


@parseObject.register(Interval)
def _parseObject_(obj: Interval, # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    children = ("t0", "t1", "durations", "extent", "labels", "annotations", "description")
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    tip = type(obj).__name__
    n = len(obj)
    desc = strutils.pluralize('subinterval', n)
    info = f"Interval '{obj.name}' with {len(obj)} {desc}"
    infoDict = {
        "name": objName,
        "indirect": True,
        "children": children,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (".", ),
        "accessType": "attribute",
        "choices": choices,
        "readOnly": readOnly,
        "readOnlyChildren": readOnlyChildren,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }
    return ObjectInfo(**infoDict)

@parseObject.register(neo.Epoch)
@parseObject.register(DataZone)
def _parseObject_(obj: neo.Epoch | DataZone, # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)
    children = ("times", "durations", "labels", "annotations", "description")

    tip = type(obj).__name__
    n = obj.size
    klass = "Zone" if isinstance(obj, DataZone) else "Epoch"
    desc = strutils.pluralize('subinterval', n)
    info = f"{klass} '{obj.name}' with {n} {desc}"

    infoDict =  {
        "name": objName,
        "indirect": True,
        "children": children,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (".", ),
        "accessType": "attribute",
        "choices": choices,
        "readOnly": readOnly,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }
    return ObjectInfo(**infoDict)

@parseObject.register(neo.Event)
@parseObject.register(DataMark)
@parseObject.register(TriggerEvent)
def _parseObject_(obj: neo.Event | DataMark | TriggerEvent,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    children = ("times", "labels")

    if isinstance(obj, (DataMark, TriggerEvent)):
        children += ("type", "relative")

    children += ("annotations", "description")

    tip = type(obj).__name__

    klass = "TriggerEvent" if isinstance(obj, TriggerEvent) else "Mark" if isinstance(obj, DataMark) else tip

    n = obj.size
    desc = strutils.pluralize('subinterval', n)
    info = f"{klass} '{obj.name}' with {n} {desc}"
    infoDict = {
        "name": objName,
        "indirect": True,
        "children": children,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (".", ),
        "accessType": "attribute",
        "choices": choices,
        "readOnly": readOnly,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }
    return ObjectInfo(**infoDict)

@parseObject.register(pq.Quantity)
def _parseObject_(obj: pq.Quantity,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    # NOTE: 2026-09-20 11:49:26
    # NEVER introspected
    # NOTE: 2026-09-20 11:49:34
    # as a child object ONLY if an array,
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    readOnly = False
    tip = f"{scq.unitFamilyName(obj.units)} quantity"
    if isinstance(obj, pq.UnitQuantity):
        info = f"{obj} {scq.unitFamilyName(obj)}"
        objDataAsChild = False

    else:
        if obj.size <= 1:
            info = f"{obj}"
            objDataAsChild = False
        else:
            n = obj.size
            # s = " × ".join(list(map(lambda x: f"{x}", obj.shape))) if len(obj.shape) > 1 else f"{obj.shape}"
            info = f"Quantity array ({obj.units.dimensionality}) with {n} {strutils.pluralize('sample', n)}, shape: {obj.shape},  dtype {obj.dtype}."
            objDataAsChild = True
            readOnly = False

    infoDict = {
        "name": objName,
        "indirect": False,
        "objDataAsChild": objDataAsChild,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (".", ),
        "accessType": "attribute",
        "choices": choices,
        "readOnly": readOnly,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(vigra.VigraArray)
def _parseObject_(obj: vigra.VigraArray,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    # NOTE: 2026-09-20 11:51:46
    # array data as object child if array size > 1
    # axistags as subtree (if introspected)
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    # NOTE: 2026-02-11 21:11:11
    # member access relates to metadata attributes (i.e., axistags);
    # the array data has read-write access to the underlying array via the
    # TableEditorWidget in the child item
    samples = strutils.pluralize('samples', obj.size)
    s = f"{obj.shape}"
    c = obj.channels
    axtags = ", ".join([f"'{t.key}'" for t in obj.axistags])
    objDataAsChild = False

    if obj.size <= 1:
        info = obj
    else:
        objDataAsChild = True
        info = f"Vigra Array with {n} {samples}; shape {s}; axistags: {axtags}; {c} channels; dtype {obj.dtype}."

    if introspect:
        children = tuple(obj.axistags)
        indirect = True
    else:
        children = ()
        indirect = False

    tip = type(obj).__name__

    infoDict = {
        "name": objName,
        "indirect": indirect,
        "children": children,
        "objDataAsChild": objDataAsChild,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": ("[","]", ),
        "accessType": "index",
        "choices": choices,
        "readOnly": True,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType,
        "containerChild": "axistags"
        }
    return ObjectInfo(**infoDict)


@parseObject.register(np.ndarray)
def _parseObject_(obj: np.ndarray,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    # NOTE: 2026-09-20 11:37:16
    # NEVER introspected
    # NOTE: 2026-09-20 11:40:40
    # Large arrays shown as a child object (in its own table widget)
    objId = id(obj)
    objType = type(obj)

    # TableEditorWidget gives read-write access to array data
    tip = type(obj).__name__
    n = obj.size
    # shape = obj.shape
    s = f"{obj.shape}"
    samples = strutils.pluralize('sample', n)
    objDataAsChild = False

    if obj.size <= 1:
        info = obj
    else:
        objDataAsChild = True
        info = f"Array with {n} {samples}, shape {s}, dtype {obj.dtype}."

    infoDict =  {
        "name": objName,
        "indirect": False,
        "objDataAsChild": objDataAsChild,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (),
        "accessType": None,
        "choices": {},
        "readOnly": True,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }
    return ObjectInfo(**infoDict)

@parseObject.register(vigra.AxisInfo)
def _parseObject_(obj: vigra.AxisInfo,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    info = f"{type(obj).__name__} ({getNameForAxisType(obj.typeFlags)}) key {obj.key}"
    tip = type(obj).__name__

    if introspect:
        children = ("resolution", "description", "typeFlags")
        indirect = True
    else:
        children = ()
        indirect = False

    infoDict = {
        "name": objName,
        "indirect": indirect,
        "children": children,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (".", ),
        "accessType": "attribute",
        "choices": choices,
        "readOnly": False,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(vigra.AxisType)
def _parseObject_(obj: vigra.AxisType,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    # NOTE: 2026-02-08 22:54:09 TODO
    # Don't really want to edit this via GUI, so no member access for now
    # hence NEVER introspected
    objId = id(obj)
    objType = type(obj)
    tip = type(obj).__name__
    info = f"{tip}: {getNameForAxisType(obj)} ({getValueForAxisType(obj)})"

    infoDict = {
        "name": objName,
        "indirect": False,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (),
        "accessType": None,
        "choices":  {vigra.AxisType.names},
        "readOnly": False,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)


@parseObject.register(AxesCalibration)
def _parseObject_(obj: AxesCalibration,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    if introspect:
        children = tuple(obj.axiskeys())
        n = len(children)
        info = f"{n} {strutils.pluralize('calibration', n)}"
        indirect = True
    else:
        children = ()
        info = ""
        indirect = False

    tip = type(obj).__name__

    infoDict = {
        "name": objName,
        "indirect": indirect,
        "children": children,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": ("[","]", ),
        "accessType": "index", # calls __getitem__ for obtain an AxisCalibrationData
        "choices": choices,
        "readOnly": readOnly,
        "readOnlyChildren": readOnlyChildren,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(AxisCalibrationData)
def _parseObject_(obj: AxisCalibrationData,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> tuple:
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    tip = type(obj).__name__
    objDataAsChild = False

    if introspect:
        children = introspectObject(obj, predicate = predicate,
                    includePrivate = includePrivate,
                    includeCallables = includeCallables,
                    includeTypeMembers = includeTypeMembers)
        indirect = True
    else:
        children = ()
        indirect = False

    if not obj.isChannels:
        info = f"Axis calibration for axis {obj.index} (type {obj.type}; key {obj.key}); size {obj.size}"

    else:
        c = len(obj.channels)
        info = f"Channel axis calibration with {c} {strutils.pluralize('channel', c)}"

    infoDict = {
        "name": objName,
        "indirect": indirect,
        "children": children,
        "objDataAsChild": objDataAsChild,
        "objInfo": info,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (".", ),
        "accessType": "attribute",
        "choices": False,
        "readOnly": readOnly,
        "readOnlyChildren": readOnlyChildren,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return pData, ObjectInfo(**infoDict)

@parseObject.register(ChannelCalibrationData)
def _parseObject_(obj: ChannelCalibrationData,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objId =  id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    tip = f"{type(obj).__name__}"

    if introspect:
        children = introspectObject(obj, predicate = predicate,
                includePrivate = includePrivate,
                includeCallables = includeCallables,
                includeTypeMembers = includeTypeMembers
                )
        indirect = True
    else:
        children = ()
        indirect = False

    infoDict = {
        "name": objName,
        "indirect": indirect,
        "children": children,
        "objDataAsChild": False,
        "objInfo": obj.description,
        "objType": objType,
        "objTip": tip,
        "memberAccess": (".", ),
        "accessType": "attribute",
        "choices": choices,
        "readOnly": readOnly,
        "readOnlyChildren": readOnlyChildren,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(PVObject)
def _parseObject_(obj: PVObject,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    tip = type(obj).__name__
    info = tip
    if isinstance(obj, PVScan):
        info = f"{obj.attributes}"

    elif isinstance(obj, PVSequence):
        nframes = len(obj.frames)
        info = f"{obj.attributes['sequencetypename']} with {nframes} {strutils.pluralize('frame', nframes)}"

    elif isinstance(obj, PVFrame): # star imports from systems.PrairieView
        info = f"Channels: {obj.channels}"

    elif isinstance(obj, (PVSystemConfiguration, PVIndexedValue, PVSubIndexedValue)): # noqa # star imports from systems.PrairieView
        if (
            hasattr(obj, "description")
            and isinstance(obj.description, str)
            and len(obj.description.strip())
            ):
            info = obj.description

    if introspect:
        children = tuple(obj.as_dict())
        indirect = True
    else:
        children = ()
        indirect = False

    infoDict = {
        "name": objName,
        "indirect": indirect,
        "children": children,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objtip": tip,
        "memberAccess": (".", ),
        "accessType": "attribute",
        "choices": choices,
        "readOnly": False,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

@parseObject.register(scipy.optimize.Bounds)
def _parseObject_(obj: scipy.optimize.Bounds,  # noqa: F811
                  objName: str, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables : bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None,
                  readOnly: bool = False,
                  readOnlyChildren: bool = False,
                  objKey: str | None = None,
                  objKeyType: type | None = None
                ) -> ObjectInfo:
    objId = id(obj)
    objType = type(obj)
    choices = check_obj_choices(objType, choices)

    tip = type(obj).__name__
    if introspect:
        children = ("lb", "ub", "keep_feasible")
        indirect = True
    else:
        children = ()
        indirect = False
    info = ""
    infoDict = {
        "name": objName,
        "indirect": indirect,
        "children": children,
        "objDataAsChild": False,
        "objInfo": info,
        "objType": objType,
        "objTip": tip ,
        "memberAccess": (".", ),
        "accessType": "attribute",
        "choices": choices,
        "readOnly": False,
        "objId": objId,
        "objKey": objKey,
        "objKeyType": objKeyType
        }

    return ObjectInfo(**infoDict)

def introspectable(obj: object, supportedDataTypes: tuple = ()) -> bool:
    mro = inspect.getmro(type(obj))
    return (all(t not in supportedDataTypes for t in mro)
                        and not inspect.isroutine(obj)
                        and not isinstance(obj, NOTINTROSPECTABLE)
                        and obj is not None)

def exclude_private_members(pDict):
    return {i[0]:i[1] for i in pDict.items() if check_public_member(i)}

def exclude_methods_and_functions(pDict):
    return {i[0]:i[1] for i in pDict.items() if type(i[1]) not in FUNCTION_TYPES}

def exclude_type_attributes(pDict):
    return {i[0]:i[1] for i in pDict.items() if type not in inspect.getmro(type(i[1]))}

def generate_node(obj, objName, /,
                  introspect: bool = False,
                  predicate = None,
                  includePrivate: bool = False,
                  includeCallables: bool = False,
                  includeTypeMembers: bool = False,
                  choices: dict | None = None) -> Node:
    objId = id(obj)
    objInfo = parseObject(obj, objName, introspect = introspect,
                  predicate = predicate,
                  includePrivate = includePrivate,
                  includeCallables = includeCallables,
                  includeTypeMembers = includeTypeMembers,
                  choices = choices)

    node = ObjectNode(tag=objName, identifier = f"{objId}", objInfo = objInfo)

    return node

def filterAttribute(attrName, obj,
                    includePrivate = False,
                    includeCallables = False,
                    includeTypeMembers = False) -> bool:
    if not hasattr(obj, attrName):
        return False

    if not includePrivate and not check_public_attribute(attrName):
        return False

    value = getattr(obj, attrName)

    if not includeCallables and type(value) in FUNCTION_TYPES:
        return False

    return not (not includeTypeMembers and type in inspect.getmro(type(value)))

@singledispatch
def introspectObject(obj, /,
                     predicate = None,
                     includePrivate = False,
                     includeCallables = False,
                     includeTypeMembers = False) -> tuple:
    r"""Returns a tuple of symbols(str)
"""
    if isinstance(obj, dict):
        return tuple(obj.keys())

    fcn = functools.partial(filterAttribute,
                            obj = obj,
                            includePrivate = includePrivate,
                            includeCallables = includeCallables,
                            includeTypeMembers = includeTypeMembers)

    # NOTE: Keep iterables as iterables
    if isDataclass(obj):
        fieldnames = (f.name for f in dataclasses.fields(obj)) # keep this as a generator
        try:
            # in try block because there's no __dict__ in dataclasses with __slots__
            membernames = obj.__dict__.keys() # keep this as dict_keys

            # this is short-lived !!!
            fullmembers = itertools.chain(membernames, fieldnames)

            childnames = tuple(sorted(unique(fullmembers)))
            selected = tuple(filter(fcn, childnames))

        except: # noqa: E722
            childnames = tuple(fieldnames)
            selected = tuple(filter(fcn, childnames))

        return selected

    elif (
        HAVE_METAARRAY
        and hasattr(obj, "implements") and obj.implements("MetaArray")
        ):
        return ("data", "meta")

    elif introspectable(obj):
        fieldnames = tuple(datatypes.inspect_members(obj, predicate, symbols_only = True))
        return tuple(filter(fcn, fieldnames))

    else:
        raise NotImplementedError()

@introspectObject.register(AxisCalibrationData)
def _introspectObject_(obj: AxisCalibrationData, /,
                     predicate = None,
                     includePrivate = False,
                     includeCallables = False,
                     includeTypeMembers = False):
    if not obj.isChannels:
        fields = tuple(f.name for f in dataclasses.fields(obj) if f.name != "channels")
    else:
        fields = tuple(f.name for f in dataclasses.fields(obj))

    return fields

@introspectObject.register(bgbridge.Structure)
def _introspectObject_(obj: bgbridge.Structure, /, # noqa: F811
                     predicate = None,
                     includePrivate = False,
                     includeCallables = False,
                     includeTypeMembers = False) -> tuple:

    ndx = [
            i[1]
            for i in sorted(
                (str(k[0]), k[1])
                for k in zip(obj.keys(), range(len(obj)))
                )
        ]

    keys = tuple(obj.keys())
    return tuple(keys[k] for k in ndx)

@introspectObject.register(taxonbridge.Taxon)
def _introspectObject_(obj: taxonbridge.Taxon, /, # noqa: F811
                     predicate = None,
                     includePrivate = False,
                     includeCallables = False,
                     includeTypeMembers = False) -> tuple:
    fcn = functools.partial(filterAttribute,
                            obj = obj,
                            includePrivate = includePrivate,
                            includeCallables = includeCallables,
                            includeTypeMembers = includeTypeMembers)

    children = tuple(key for key in obj.__dict__ if fcn(getattr(obj, key)))

    children += ("common_name", "rank", "scientific_name", "url", "wikidata_id", "wikidata_url")

    return children

@introspectObject.register(os.stat_result)
def _introspectObject_(obj: os.stat_result, /, # noqa: F811
                     predicate = None,
                     includePrivate = False,
                     includeCallables = False,
                     includeTypeMembers = False) -> tuple:
    oDict = inspect.getmembers(obj)

    return tuple(t for t in oDict if any(t.startswith(s) for s in ("n_", "st_")))

@introspectObject.register(types.ModuleType)
@introspectObject.register(types.SimpleNamespace)
def _introspectObject_(obj: types.ModuleType | types.SimpleNamespace, /, # noqa: F811
                     predicate = None,
                     includePrivate = False,
                     includeCallables = False,
                     includeTypeMembers = False) -> tuple:

    fcn = functools.partial(filterAttribute,
                            obj = obj,
                            includePrivate = includePrivate,
                            includeCallables = includeCallables,
                            includeTypeMembers = includeTypeMembers)

    return tuple(key for key in obj.__dict__ if fcn(getattr(obj, key)))


def generate_dict(obj, /, predicate = None,
                    introspect = False,
                    showPrivate = False,
                    showCallables = False,
                    showTypeMembers = False) -> dict:
    if isinstance(obj, dict):
        return obj, len(obj, len(obj))

    if isDataclass(obj):
        datafields = dataclasses.fields(obj)
        try:
            fieldnames = [f.name for f in datafields] #list(map(lambda f: f.name, datafields))
            membernames = list(obj.__dict__.keys())
            childnames = sorted(unique(membernames + fieldnames))
            pData = {c: getFieldOrProperty(obj, c) for c in childnames}

        except: # noqa
            pData = {x.name: getField(obj,x) for x in datafields}

    elif (
        HAVE_METAARRAY
        and hasattr(obj, "implements")
        and obj.implements("MetaArray")
        ):
        pData = dict( # noqa
                [("data", obj.view(np.ndarray)), ("meta", obj.infoCopy())]
            )

    elif introspect and introspectable(obj) :
        pData = datatypes.inspect_members(obj, predicate)

    else:
        raise NotImplementedError(f"{type(obj).__name__} are not supported")

    fullCount = len(pData)

    if not showPrivate:
        pData = exclude_private_members(pData)

    if not showCallables:
        pData = exclude_methods_and_functions(pData)

    if not showTypeMembers:
        pData = exclude_type_attributes(pData)

    finalCount = len(pData)

    return pData, fullCount, finalCount

def check_public_attribute(x: str):
    return (isinstance(x, str) and not x.startswith("_"))

def check_public_member(x: tuple):
    # return not (isinstance(x[0], str) and not x[0].startswith("_"))
    return (not isinstance(x[0], str) or not x[0].startswith("_"))

def check_obj_choices(objType, choices: dict| None = None) -> dict:
    if (
        not isinstance(choices, dict)
        or (
            len(choices)> 0
            and not all(isinstance(v, objType) for v in choices.values())
            )
        ):
        choices = {}

    return choices

