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

NOTINTROSPECTABLE = PODS + (types.ModuleType, pkgutil.ModuleInfo,)


class ObjectParser(QtCore.QThread):
    sig_result = Signal(dict, dict, name="sig_result")
    def __init__(self, parent, obj, **kwargs):
        QtCore.QThread.__init__(self, parent)
        self._showPrivate_: bool = kwargs.pop("showPrivate", False)
        self._object_ = obj
        self._mutex_ = QtCore.QMutex()
        self._condition_ = QtCore.QWaitCondition()
        self._objectPath_ = []
        self._choices_ = {}
        # self._pData_ = {}
        # self._objDict_ = {}

    def run(self):
        try:
            self.setTerminationEnabled(True)
            locker = QtCore.QMutexLocker(self._mutex_)
            while not self.isInterruptionRequested():
                self._condition_.wait(self._mutex_)
            if self.isInterruptionRequested():
                return
            locker.unlock()
            self.setTerminationEnabled(False)
            pData, objDict = self._parseObject_(obj, self._showPrivate_, {})
            self.sig_result.emit(pData, objDict)

        except:  # noqa:
            traceback.print_exc()

    def _check_obj_choices_(self, choices: dict| None = None) -> dict:
        if (
            not isinstance(choices, dict)
            or (
                len(choices)> 0
                and not all(isinstance(v, objType) for v in choices.values())
                )
            ):
            choices = {}

        return choices


    @singledispatchmethod
    def _parseObject_(self: typing.Self, obj: object,
                      includePrivateMembers: bool = False,
                      choices: dict | None = None
                   ) -> tuple:
        r"""
        Returns:
        ========
        a tuple: (``parsedData``, ``infoDict``), where:

            ``parsedData`` if either ``obj`` itself, or a ``dict`` representation of it

            ``infoDict`` is the mapping:

            "indirect" ↦ bool
                When ``False``, ``self._privateData_`` attribute is ``obj`` itself, and
                ``obj`` is represented by a single row (the *object row*). The
                *object row* ia a child of the parent tree item, which is either the
                *invisibile root item* of the model or a row / branch representation of
                the container of ``obj``.

                When ``True`` this flag indicates that ``parsedData`` is in fact a
                ``dict`` representation of the object's structure. Members of ``obj``
                are to be represented as tree sub-branches (*member rows*) children of
                the *object row*. When ``includePrivateMembers`` is ``False`` (the default),
                private members of ``obj`` are excluded from this representation. All
                *member rows* follow a possible *data row* (see below).

            "objDataAsChild" ↦ bool
                When ``True``, the contents of ``obj`` should be displayed in a widget
                on its own, in the first row (*data row*) child (branch) of the *object row*.
                If, in addition, ``obj`` is represented indirectly by a ``dict``
                (``parsedData``, see above), all *member rows* **must** follow the
                *data row*.

            "objInfo" ↦ str
                When ``obj`` is a scalar number or singleton array, this is a string
                representaion of ``obj`` *value* and can be made editable, unless the
                model is configured to introspect all members of ``obj``.

                When ``obj`` is representable as a ``dict`` (see above) **or** the model
                is set up to introspect members of ``obj`` regardless of its type, then
                **objInfo** contains abrief description of ``obj`` (one line).

            "objType" ↦ str
                The type name of ``obj``.

            "objTip" ↦ str
                Contents of the UI tooltip to be shown when the *object row* is hovered.

            "memberAccess" ↦ typing.Tuple[str]

            "choices" ↦ dict, mapping name ↦ value - used in enums and enum-like objects
                where a combo box is appropriate for choosing a value from a predefined
                set; for all other object types, this will be empty.

            "readOnly" ↦ flag indicating if the represented object can be edited
                in the datatreeview. Some object types are immutable by design
                (e.g., bytes, bytearray, tuple, frozenset) and therefore their
                contents cannot be edited.



            "isLeaf" ↦ flag to determine if the object represented in the item in
                column 0 is a "leaf", or has children



        """
        # TODO 2026-03-28 16:32:58
        # configuration file to determine if instances of some user-defined types
        # are also editable or not -> use it to deterine the readOnly flag, above
        indirect: bool = False
        tip: str = type(obj).__name__
        objDataAsChild: bool = False
        objType = type(obj)
        objId = id(obj)

        choices = self._check_obj_choices_(choices)

        readOnly = False
        readOnlyChildren = False

        if isDataclass(obj):
            pData, fullCount, nChildren = self._generate_dict_(obj, includePrivateMembers)
            indirect = True
            if includePrivateMembers:
                readOnlyChildren = True

            info = f"{nChildren} {strutils.pluralize('member', nChildren)} (of {fullCount})"
            tip = f"{type(obj).__name__} (dataclass)"
            objDataAsChild = False
            memberAccess = (".",)
            accessType = "attribute"
            readOnly = False

        elif (
            HAVE_METAARRAY
            and hasattr(obj, "implements")
            and obj.implements("MetaArray")
            ):
            pData, fullCount, nChildren = self._generate_dict_(obj, includePrivateMembers)
            indirect = True
            objDataAsChild = False
            info = ""
            memberAccess = ("[", "]")
            accessType = "index"
            # nChildren = len(pData)

        elif HAS_MESHIO and isinstance(obj, meshio.Mesh):
            pData = obj
            indirect=False,
            s = " × ".join(list(map(lambda x: f"{x}", obj.points.shape))) # noqa
            info = f"{obj.points.size} points ({s})"
            tip = type(obj).__name__
            objDataAsChild = False
            memberAccess = ()
            accessType = None
            readOnly = True
            readOnlyChildren = True
            nChildren = 0

        elif self._introspect_ and self.introspectable(obj):
            # print(f"{self.__class__.__name__}._parseObject_({type(obj)}) introspectable")
            pData, fullCount, nChildren = self._generate_dict_(obj, includePrivateMembers)
            indirect = True
            objDataAsChild = False

            info = f"{nChildren} {strutils.pluralize('member', nChildren)} (of {fullCount})"
            memberAccess = (".", )
            accessType = "attribute"
            readOnly = True
            readOnlyChildren = True

        elif isinstance(obj, ephys_protocol.ElectrophysiologyProtocol):
            pData = obj
            indirect = False
            info = f"{obj.name}"
            tip = f"{obj.name}"
            objDataAsChild = False
            memberAccess = ()
            accessType = None
            nChildren = 0

        else:
            pData = obj
            indirect = False
            info = f"{obj}"
            tip = f"{obj}"
            objDataAsChild = False
            memberAccess = ()
            accessType = None
            nChildren = 0

        return pData, {
            "indirect": indirect,
            "nChildren": nChildren,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "memberAccess": memberAccess,
            "accessType": accessType,
            "objTip": tip,
            "objType": objType,
            "choices": choices,
            "readOnly": readOnly,
            "readOnlyChildren": readOnlyChildren,
            "objId": objId
            }

    @_parseObject_.register(type(None))
    @_parseObject_.register(type(MISSING))
    @_parseObject_.register(type(pd.NA))
    def __parseObject__(self: typing.Self, obj: typing.Union[type(None),        # noqa: UP007
                                                             type(MISSING),
                                                             type(pd.NA)],
                        _:bool = False, choices: dict | None = None, ) -> tuple:
        objType = type(obj)
        objId = id(obj)
        pData = obj
        indirect = False
        info = f"{obj}"
        tip = f"{obj}"
        objDataAsChild = False
        memberAccess = ()
        accessType = None
        choices = self._check_obj_choices_(choices)

        # TODO/FIXME: 2026-03-28 16:57:15
        # mechanism to see if a new object of another type is acceptable here, in which case call a UI c'tor'
        readOnly = True
        readOnlyChildren = True

        return pData, {
            "indirect": indirect,
            "nChildren": 0,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "memberAccess": memberAccess,
            "accessType": accessType,
            "objTip": tip,
            "objType": objType,
            "choices": choices,
            "readOnly": readOnly,
            "readOnlyChildren": readOnlyChildren,
            "objId": objId
            }

    @_parseObject_.register(datetime.datetime)
    @_parseObject_.register(datetime.date)
    @_parseObject_.register(datetime.time)
    @_parseObject_.register(datetime.timedelta)
    @_parseObject_.register(datetime.timezone)
    def __parseObject__(self: typing.Self, obj: typing.Union[datetime.datetime,   # noqa: F811,UP007
                                               datetime.date,
                                               datetime.time,
                                               datetime.timedelta,
                                               datetime.timezone],
          __:bool = False, _: dict | None = None, ) -> tuple:

        objType = type(obj)
        objId = id(obj)
        pData = obj
        info = f"{obj}"
        tip = f"{obj}"
        objDataAsChild = False
        memberAccess = ()
        accessType = None
        readOnly = False

        return pData, {
            "indirect": False,
            "nChildren": 0,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "memberAccess": memberAccess,
            "accessType": accessType,
            "objTip": tip,
            "objType": objType,
            "choices": {},
            "readOnly": readOnly,
            "objId": objId
            }

    @_parseObject_.register(types.FunctionType)
    @_parseObject_.register(types.BuiltinFunctionType)
    @_parseObject_.register(types.MethodType)
    @_parseObject_.register(types.BuiltinMethodType)
    def __parseObject__(self: typing.Self, obj: typing.Union[types.FunctionType,  # noqa: F811,UP007
                                               types.BuiltinFunctionType,
                                               types.MethodType,
                                               types.BuiltinMethodType],
                        _:bool = False, choices: dict | None = None) -> tuple:
        # print(f"{self.__class__.__name__}._parseObject_(obj: {type(obj)})")
        objType = type(obj)
        objId = id(obj)
        choices = self._check_obj_choices_(choices)

        tip = f"{obj}"
        word = "Function" if isinstance(obj, (types.FunctionType, types.BuiltinFunctionType)) else "Method"

        try:
            # NOTE: 2026-05-01 09:24:50
            # because signature of builtin functions e.g. on PyQt side) cannot be inspected
            signature = f"{inspect.signature(obj)}"

        except: # noqa
            signature = ""
        info = f"{word} {obj.__qualname__}{signature} from module {obj.__module__}"

        return obj, {
            "indirect": False,
            "nChildren": 0,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (),
            "accessType": None,
            "choices": choices,
            "readOnly": False, # TODO/FIXME
            "objId": objId
            }

    @_parseObject_.register(type)
    @_parseObject_.register(enum.EnumType)
    @_parseObject_.register(enum.Enum)
    @_parseObject_.register(enum.IntEnum)
    @_parseObject_.register(enum.Flag)
    @_parseObject_.register(TypeEnum)
    def __parseObject__(self: typing.Self, obj: typing.Union[type, enum.EnumType, # noqa: F811,UP007
                                                             enum.Enum,
                                                             enum.Flag,
                                                             TypeEnum],
          includePrivateMembers: bool = False, choices: dict | None = None) -> tuple:
        readOnly = True
        readOnlyChildren = True
        objType = type(obj)
        objId = id(obj)
        info = obj
        tip = str(obj)
        choices = self._check_obj_choices_(choices)
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
                # readOnly = True

        return obj, {
            "indirect": False,
            "nChildren": 0,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": memberAccess,
            "accessType": accessType,
            "choices": choices,
            "readOnly": readOnly,
            "readOnlyChildren": readOnlyChildren,
            "objId": objId
            }

    @_parseObject_.register(pkgutil.ModuleInfo)
    def __parseObject__(self: typing.Self, obj: pkgutil.ModuleInfo,   # noqa: F811
                        includePrivateMembers: bool = False,
                        choices: dict | None = None, ) -> tuple:
        objType = type(obj)
        tip = f"{objType}.__name__"
        objId = id(obj)
        choices = self._check_obj_choices_(choices)

        pData = {f: getattr(obj, f, None) for f in obj._fields} # dict(map(lambda f: (f, getattr(obj, f, None)), obj._fields))
        info = f"{len(pData)} fields"

        return obj, {
            "indirect": True,
            "nChildren": 0,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".",),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": True,
            "readOnlyChildren": True,
            "objId": objId
            }

    @_parseObject_.register(bgbridge.Structure)
    def __parseObject__(self: typing.Self, obj: bgbridge.Structure,   # noqa: F811
                        includePrivateMembers: bool = False,
                        choices: dict | None = None, ) -> tuple:
        objType = type(obj)
        objId = id(obj)
        choices = self._check_obj_choices_(choices)

        ndx = [
            i[1]
            for i in sorted(
                (str(k[0]), k[1])
                for k in zip(obj.keys(), range(len(obj)))
            )
        ]

        items = [i for i in obj.items()]
        pData = dict([items[k] for k in ndx])
        indirect = True
        info = f"{type(obj).__name__} ID: {obj['id']}, {obj['name']} ({obj['acronym']})"
        if not includePrivateMembers:
            pData = self._exclude_private_members_(pData)

        tip = type(obj).__name__

        return pData, {
            "indirect": indirect,
            "nChildren": len(pData),
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": ("[", "]"),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": True,
            "readOnlyChildren": True,
            "objId": objId
            }

    @_parseObject_.register(taxonbridge.Taxon)
    def __parseObject__(self: typing.Self, obj: taxonbridge.Taxon, # noqa: F811
                        includePrivateMembers: bool = False,
                        choices: dict | None = None ) -> tuple:
        objType = type(obj)
        objId = id(obj)
        choices = self._check_obj_choices_(choices)

        pData = obj.__dict__
        indirect = True
        info = f"{obj}"

        if not includePrivateMembers:
            pData = self._exclude_private_members_(pData)

        pData["common_name"] = obj.common_name
        pData["rank"] = obj.rank
        pData["scientific_name"] = obj.scientific_name
        pData["url"] = obj.url
        pData["wikidata_id"] = obj.wikidata_id
        pData["wikidata_url"] = obj.wikidata_url

        tip = type(obj).__name__
        return pData, {
            "indirect": indirect,
            "nChildren": len(pData),
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".",),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": True,
            "readOnlyChildren": True,
            "objId": objId
            }

    @_parseObject_.register(dict)
    @_parseObject_.register(types.MappingProxyType)
    @_parseObject_.register(UserDict)
    @_parseObject_.register(OrderedDict)
    def __parseObject__(self: typing.Self, obj: typing.Union[dict,              # noqa: F811,UP007
                                                types.MappingProxyType,
                                                UserDict,
                                                OrderedDict],
                        includePrivateMembers: bool = False,
                        choices: dict | None = None, ) -> tuple:
        # CAUTION: 2026-02-13 21:54:18
        # this might be the private data, NOT the original model data!

        # print(f"{self.__class__.__name__}._parseObject_({type(obj)})")

        objId = id(obj)

        if obj is self._privateData_:
            objType = type(self._modelData_)

        else:
            objType = type(obj)

        choices = self._check_obj_choices_(choices)

        # NOTE: 2021-07-20 09:52:34
        # dict objects with mixed key types cannot be sorted
        # therefore we resort to an indexing vector
        ndx = [
            i[1]
            for i in sorted(
                (str(k[0]), k[1])
                for k in zip(obj.keys(), range(len(obj)))
            )
        ]

        if isinstance(obj, UserDict):
            # print(f"{self.__class__.__name__}._parseObject_({type(obj)})")
            pData = obj
            indirect = False

        else:
            items = [i for i in obj.items()]
            pData = dict([items[k] for k in ndx])
            indirect = False

        nChildren = len(pData) # CAUTION: this might include private members !!!
        info = f"{len(obj)} key / value {strutils.pluralize('pair', nChildren)}"
        tip = type(obj).__name__

        return pData, {
            "indirect": indirect,
            "nChildren": nChildren,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip":tip,
            "memberAccess": ("[", "]"),
            "accessType": "key",
            "choices": choices,
            "readOnly": True,
            "readOnlyChildren": False,
            "objId": objId
            }

    @_parseObject_.register(list)
    @_parseObject_.register(tuple)
    @_parseObject_.register(deque)
    @_parseObject_.register(NeoObjectList)
    @_parseObject_.register(set)
    @_parseObject_.register(frozenset)
    @_parseObject_.register(os.stat_result)
    def __parseObject__(self: typing.Self, obj: typing.Union[list, tuple, deque,  # noqa: UP007,F811
                                                            set,
                                                            NeoObjectList,
                                                            frozenset,
                                                            os.stat_result],
                        includePrivateMembers: bool = False,
                        choices: dict | None = None, ) -> tuple:
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

        tip = objType.__name__
        readOnly = True
        readOnlyChildren = False

        if isinstance(obj, (tuple, frozenset)) or self.readOnly:
            readOnly = True
            readOnlyChildren = True

        if is_namedtuple(obj):
            pData = obj._asDict() if hasattr(obj, "_asDict") else obj._asdict()
            tip += "(namedtuple)"
            memberAccess = (".",)
            accessType = "attribute"
            readOnlyChildren = True

        elif isinstance(obj, os.stat_result):
            pData = dict(filter(lambda t: any(t[0].startswith(s) for s in ("n_", "st_")), inspect.getmembers(obj)))
            tip += "(stat result)"
            memberAccess = (".",)
            accessType = "attribute"
            readOnlyChildren = True

        else:
            pData = dict(enumerate(obj))
            memberAccess = ("[","]")
            accessType = "index"
            # readOnlyChildren = True

        if not includePrivateMembers:
            pData = self._exclude_private_members_(pData)

        n = len(pData)

        info = f"{n} {strutils.pluralize('element', n)}"

        return pData, {
            "indirect": True,
            "nChildren": n,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": memberAccess,
            "accessType": accessType,
            "choices": choices,
            "readOnly": readOnly,
            "readOnlyChildren": readOnlyChildren,
            "objId": objId
            }

    @_parseObject_.register(str)
    @_parseObject_.register(bytes)
    @_parseObject_.register(bytearray)
    def __parseObject__(self: typing.Self, obj: typing.Union[str, bytes, bytearray],   # noqa: UP007,F811
                        _: bool = True, choices: dict | None = None, ) -> tuple:
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

        readOnly = self.readOnly
        readOnlyChildren = self.readOnly
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

            if isinstance(obj, (bytes, bytearray)) or self.readOnly:
                readOnly = True
                readOnlyChildren = True

        return  obj, {
            "indirect": False,
            "nChildren": 0,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (),
            "accessType": None,
            "choices": choices,
            "readOnly": readOnly,
            "readOnlyChildren": readOnlyChildren,
            "objId": objId
            }

    @_parseObject_.register(pathlib.Path)
    def __parseObject__(self: typing.Self, obj: pathlib.Path, _: bool = True,   # noqa: F811
                        choices: dict | None = None) -> tuple:
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

        # info = f"{obj}"
        info = obj.as_posix()
        tip = objType.__name__
        pData = obj
        # indirect = True
        indirect = False
        return  pData, {
            "indirect": indirect,
            "nChildren": 0,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (),
            "accessType": None,
            "choices": choices,
            "readOnly": self.readOnly,
            "objId": objId
            }

    @_parseObject_.register(bool)
    @_parseObject_.register(int)
    @_parseObject_.register(float)
    @_parseObject_.register(complex)
    @_parseObject_.register(fractions.Fraction)
    @_parseObject_.register(decimal.Decimal)
    @_parseObject_.register(numbers.Number)
    @_parseObject_.register(np.integer)
    @_parseObject_.register(np.floating)
    @_parseObject_.register(np.complexfloating)
    def __parseObject__(self: typing.Self, obj: typing.Union[bool, int, float, complex,   # noqa: UP007,F811,PYI041
                                               fractions.Fraction,
                                               decimal.Decimal,
                                               numbers.Number,
                                               np.integer, np.floating,
                                               np.complexfloating],
                         _: bool=True, choices: dict | None = None,) -> tuple:
        objId = id(obj)
        objType = type(obj)

        # objInfo = obj

        if (
            not isinstance(choices, dict)
            and len(choices)> 0
            and not all(isinstance(v, objType) for v in choices.values())
            ):
            choices = {}

        tip = objType.__name__
        return obj, {
            "indirect": False,
            "nChildren": 0,
            "objDataAsChild": False,
            "objInfo": obj,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (),
            "accessType": None,
            "choices": choices,
            "readOnly": self.readOnly,
            "objId": objId
            }

    @_parseObject_.register(types.SimpleNamespace)
    def __parseObject__(self: typing.Self, obj: types.SimpleNamespace, # noqa: F811
                includePrivateMembers: bool = False,
                choices: dict | None = None) -> tuple:
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

        pData = obj.__dict__
        if not includePrivateMembers:
            pData = self._exclude_private_members_(pData)

        n = len(pData)
        info = f"{n} {strutils.pluralize('member', n)}"
        tip = type(obj).__name__
        return pData, {
            "indirect": True,
            "nChildren": n,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": True,
            "readOnlyChildren": False,
            "objId": objId
            }

    @_parseObject_.register(types.ModuleType)
    def __parseObject__(self: typing.Self, obj: types.ModuleType, # noqa: F811
          includePrivateMembers: bool = False,
          choices: dict | None = None) -> tuple:
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

        tip = type(obj).__name__

        if hasattr(obj, "__name__"):
            mname = f" {obj.__name__}"
        else:
            mname = ""

        if hasattr(obj, "__file__"):
            mfile = " from file " + obj.__file__
        else:
            mfile = ""

        mname = getattr(obj, "__name__", None)
        info = f"Module{mname}{mfile}"

        pData = obj.__dict__

        if not includePrivateMembers:
            pData = self._exclude_private_members_(pData)

        return pData, {
            "indirect": True,
            "nChildren": len(pData),
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": True,
            "readOnlyChildren": True,
            "objId": objId
            }

    @_parseObject_.register(vigra.filters.Kernel1D)
    @_parseObject_.register(vigra.filters.Kernel2D)
    def __parseObject__(self: typing.Self, obj: vigra.filters.Kernel1D | vigra.filters.Kernel2D,  # noqa: F811
                        _: bool = True, choices: dict | None = None) -> tuple:
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
        choices = self._check_obj_choices_(choices)

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

        return obj, {
            "indirect": False,
            "nChildren": 0,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": memberAccess,
            "accessType": accessType,
            "choices": {},
            # "choices": choices,
            "readOnly": True, # pending a new widget for this
            "objId": objId
            }

    @_parseObject_.register(pd.DataFrame)
    @_parseObject_.register(pd.Series)
    @_parseObject_.register(pd.Index)
    def __parseObject__(self: typing.Self, obj: typing.Union[pd.DataFrame,      # noqa: F811,UP007
                                                             pd.Series,
                                                             pd.Index],
                        _: bool = True, choices: dict | None = None) -> tuple:
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

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

        return obj, {
            "indirect": False,
            "nChildren": 0,
            "objDataAsChild": True,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": memberAccess,
            "accessType": None,
            "choices": choices,
            "readOnly": True,
            "objId": objId
            }


    @_parseObject_.register(Interval)
    def __parseObject__(self: typing.Self, obj: Interval, _: bool = True,   # noqa: F811
                        choices: dict | None = None) -> tuple:
        pData = {
                    "t0": obj.t0,
                    "t1": obj.t1,
                    "durations": obj.durations,
                    "extent": obj.extent,
                    "labels": obj.labels,
                    "annotations": obj.annotations,
                    "description": obj.description,
                }
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

        tip = type(obj).__name__
        n = len(obj)
        desc = strutils.pluralize('subinterval', n)
        info = f"Interval '{obj.name}' with {len(obj)} {desc}"

        return pData, {
            "indirect": True,
            "nChildren": len(pData),
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": self.readOnly,
            "readOnlyChildren": self.readOnly,
            "objId": objId
            }

    @_parseObject_.register(neo.Epoch)
    @_parseObject_.register(DataZone)
    def __parseObject__(self: typing.Self, obj: neo.Epoch | DataZone,           # noqa: F811
                        _: bool = True, choices: dict | None = None,) -> tuple:
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

        pData = {
                    "times": obj.times,
                    "durations": obj.durations,
                    "labels": obj.labels,
                    "annotations": obj.annotations,
                    "description": obj.description,
                }

        tip = type(obj).__name__
        n = obj.size
        klass = "Zone" if isinstance(obj, DataZone) else "Epoch"
        desc = strutils.pluralize('subinterval', n)
        info = f"{klass} '{obj.name}' with {n} {desc}"

        return pData, {
            "indirect": True,
            "nChildren": len(pData),
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": False,
            "objId": objId
            }

    @_parseObject_.register(neo.Event)
    @_parseObject_.register(DataMark)
    @_parseObject_.register(TriggerEvent)
    def __parseObject__(self: typing.Self, obj: neo.Event | DataMark | TriggerEvent, # noqa: F811
                        _: bool = True, choices: dict | None = None) -> tuple:
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

        pData = {"times": obj.times, "labels": obj.labels}

        if isinstance(obj, (DataMark, TriggerEvent)):
            pData.update({"type": obj.type, "relative": obj.relative})

        pData.update({"annotations": obj.annotations, "description": obj.description})

        tip = type(obj).__name__

        klass = "TriggerEvent" if isinstance(obj, TriggerEvent) else "Mark" if isinstance(obj, DataMark) else tip

        n = obj.size
        desc = strutils.pluralize('subinterval', n)
        info = f"{klass} '{obj.name}' with {n} {desc}"

        return pData, {
            "indirect": True,
            "nChildren": len(pData),
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": False,
            "objId": objId
            }

    @_parseObject_.register(pq.Quantity)
    def __parseObject__(self: typing.Self, obj: pq.Quantity, _: bool=True, # noqa: F811
                        choices: dict | None = None) -> tuple:
        # print(f"{self.__class__.__name__}._parseObject_({type(obj).__name__})")
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

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

        objDict = {
            "indirect": False,
            "nChildren": 0,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": readOnly,
            "objId": objId
            }

        # print(f"\t-> {objDict}")

        return obj, objDict

    @_parseObject_.register(vigra.VigraArray)
    def __parseObject__(self: typing.Self, obj: vigra.VigraArray,               # noqa: F811
                        _: bool = True, choices: dict | None = None) -> tuple:
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

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

        pData = dict(enumerate(obj.axistags))

        tip = type(obj).__name__

        return pData, {
            "indirect": True,
            "nChildren": len(pData),
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": True,
            "objId": objId
            }


    @_parseObject_.register(np.ndarray)
    def __parseObject__(self: typing.Self, obj: np.ndarray, _: bool = True,   # noqa: F811
                        choices: dict | None = None) -> tuple:
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

        return obj, {
            "indirect": False,
            "nChildren": 0,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (),
            "accessType": None,
            "choices": {},
            "readOnly": True,
            "objId": objId
            }

    @_parseObject_.register(vigra.AxisInfo)
    def __parseObject__(self: typing.Self, obj: vigra.AxisInfo,                 # noqa: F811
                        _: bool = False, choices: dict | None = None) -> tuple:
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

        info = f"{type(obj).__name__} ({getNameForAxisType(obj.typeFlags)}) key {obj.key}"
        tip = type(obj).__name__
        pData = {"resolution": obj.resolution, "description": obj.description,
                 "typeFlags": obj.typeFlags}

        return pData, {
            "indirect": True,
            "nChildren": len(pData),
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": False,
            "objId": objId
            }

    @_parseObject_.register(vigra.AxisType)
    def __parseObject__(self: typing.Self, obj: vigra.AxisType,                 # noqa: F811
                        _: bool = False, __: dict | None = None) -> tuple:
        # NOTE: 2026-02-08 22:54:09 TODO
        # Don't really want to edit this via GUI, so no member access for now
        objId = id(obj)
        objType = type(obj)
        tip = type(obj).__name__
        info = f"{tip}: {getNameForAxisType(obj)} ({getValueForAxisType(obj)})"

        return obj, {
            "indirect": False,
            "nChildren":0,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (),
            "accessType": None,
            "choices":  {vigra.AxisType.names},
            "readOnly": False,
            "objId": objId
            }

    @_parseObject_.register(AxesCalibration)
    def __parseObject__(self: typing.Self, obj: AxesCalibration, _:bool=True,  # noqa: F811
          choices: dict | None = None) -> tuple:
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

        pData = dict(enumerate(obj.calibrations))
        n = len(pData)
        info = f"{n} {strutils.pluralize('calibration', n)}"
        tip = type(obj).__name__

        return pData, {
            "indirect": True,
            "nChildren": n,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": self.readOnly,
            "readOnlyChildren": self.readOnly,
            "objId": objId
            }

    @_parseObject_.register(AxisCalibrationData)
    def __parseObject__(self: typing.Self, obj: AxisCalibrationData, _: bool = False,   # noqa: F811
          choices: dict | None = None) -> tuple:
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

        tip = type(obj).__name__
        indirect = True
        objDataAsChild = False
        datafields = dataclasses.fields(obj)
        fieldnames = [f.name for f in datafields]
        # pData = {c: getattr(obj, c) for c in fieldnames if c != "channel"} # dict(map(lambda c: (c, getattr(obj, c)), filter(lambda f: f != "channel", fieldnames)))
        n = len(pData)
        if not obj.isChannels:
            pData = {c: getattr(obj, c) for c in fieldnames if c != "channel"} # dict(map(lambda c: (c, getattr(obj, c)), filter(lambda f: f != "channel", fieldnames)))
            # pData = dict(map(lambda c: (c, getattr(obj, c)), filter(lambda f: f != "channel", fieldnames)))
            info = f"Axis calibration for axis {obj.index} (type {obj.type}; key {obj.key}); size {obj.size}"
        else:
            pData = {c: getattr(obj, c) for c in fieldnames} # dict(map(lambda c: (c, getattr(obj, c)), fieldnames))
            c = len(obj.channels)
            info = f"Channel axis calibration with {c} {strutils.pluralize('channel', c)}"

        return pData, {
            "indirect": indirect,
            "nChildren": n,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": False,
            "readOnly": True,
            "readOnlyChildren": self.readOnly,
            "objId": objId
            }

    @_parseObject_.register(ChannelCalibrationData)
    def __parseObject__(self: typing.Self, obj: ChannelCalibrationData, _: bool = False,   # noqa: F811
                        choices: dict | None = None) -> tuple:
        objId =  id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

        tip = f"{type(obj).__name__}"
        datafields = dataclasses.fields(obj)
        fieldnames = [f.name for f in datafields] # list(map(lambda f: f.name, datafields))
        pData = {c: getattr(obj, c) for c in fieldnames} # dict(map(lambda c: (c, getattr(obj, c)), fieldnames))

        return pData, {
            "indirect": True,
            "nChildren": len(pData),
            "objDataAsChild": False,
            "objInfo": obj.description,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": True,
            "readOnlyChildren": self.readOnly,
            "objId": objId
            }

    @_parseObject_.register(PVObject)
    def __parseObject__(self: typing.Self, obj: PVObject, _: bool = False, # noqa: F811
                        choices: dict | None = None) -> tuple:
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

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

        pData = obj.as_dict()

        return pData, {
            "indirect": True,
            "nChildren": len(pData),
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objtip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": False,
            "objId": objId
            }

    @_parseObject_.register(scipy.optimize.Bounds)
    def __parseObject__(self: typing.Self, obj: scipy.optimize.Bounds, _:bool = True, # noqa: F811
                        choices: dict | None = None) -> tuple:
        objId = id(obj)
        objType = type(obj)
        choices = self._check_obj_choices_(choices)

        tip = type(obj).__name__
        pData = {
                    "lb": obj.lb,
                    "ub": obj.ub,
                    "keep_feasible": obj.keep_feasible,
                }
        info = ""
        return pData, {
            "indirect": True,
            "nChildren": len(pData),
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip ,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": False,
            "objId": objId
            }

    def _generate_dict_(self, obj, includePrivateMembers=False) -> dict:
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

        elif self._introspect_ and self.introspectable(obj) :
            # self._introspect_ set by self.showIntrospection
            pData = datatypes.inspect_members(obj, self._predicate_)
            # indirect = True
            # if not includePrivateMembers:
            #     pData = self._exclude_private_members_(pData)
            #
            # if not self._showMethods_:
            #     pData = self._exclude_methods_and_functions_(pData)


        else:
            raise NotImplementedError(f"{type(obj).__name__} are not supported")

        fullCount = len(pData)

        if not includePrivateMembers:
            pData = self._exclude_private_members_(pData)

        if not self._showMethods_:
            pData = self._exclude_methods_and_functions_(pData)

        if self._showValueAttributesOnly_:
            pData = self._exclude_type_attributes_(pData)

        finalCount = len(pData)

        return pData, fullCount, finalCount
