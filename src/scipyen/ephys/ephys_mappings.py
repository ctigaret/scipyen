# $Id: ephys_mappings.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

#### BEGIN core python modules
import os  # noqa: I001
# import sys
import collections
# import traceback
import dataclasses
from dataclasses import (dataclass, MISSING, KW_ONLY)  # noqa: F401
import datetime
# import numbers
import inspect
import itertools
import more_itertools
import typing
# from traitlets import Bunch, HasTraits
# from copy import deepcopy
# import difflib
# import re as _re
# from enum import Enum, IntEnum
# from abc import ABC
#### END core python modules

#### BEGIN 3rd party modules
# try:
#     import mypy
# except:
#     print("Please install mypy first")
#     raise
import numpy as np
import quantities as pq
import matplotlib as mpl
from matplotlib import pyplot as plt
import neo
from neo.core.objectlist import ObjectList as NeoObjectList
import h5py
import pandas as pd # noqa
from tribool import Tribool
# import pyabf
import psygnal
# from psygnal import evented

from scipy import optimize # noqa
from treelib import (Tree, Node)

# import qtpy
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


# import matplotlib as mpl
# from core.pyqtgraph_patch import pyqtgraph as pg
#### END 3rd party modules

#### BEGIN pict.core modules
from core.basescipyen import BaseScipyenData # noqa
# from core.traitcontainers import DataBag
from core.prog import (safewrapper, with_doc,# noqa
                       get_func_param_types, scipywarn, timefunc, timemethod,
                       DescriptorGenericValidator)
from core.datasignal import (DataSignal, IrregularlySampledDataSignal) # noqa
from core.datazone import (DataZone, Interval) # noqa
from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType, ) # noqa
from core.triggerprotocols import TriggerProtocol, TriggerProtocolList # noqa
from core.typeenum import TypeEnum
from core.scipyendataclasses import (Episode, Schedule, ScipyenDataclass,
                                     getField, getFieldOrProperty) # noqa
from core import datatypes # noqa
from core.datatypes import (check_type, type2str) # noqa
from core import workspacefunctions # noqa
from core import signalprocessing as sigp # noqa
from core import utilities # noqa
from core import neoutils
from core import strutils
from core import curvefitting as crvf # noqa
from core import models # noqa

from core.utilities import (reverse_mapping_lookup, # noqa
                            get_index_for_seq,
                            sp_set_loc,
                            normalized_index,
                            unique,
                            GeneralIndexType)
from core.strutils import counter_suffix
from core.neoutils import (get_index_of_named_signal, concatenate_blocks) # noqa
from core import scipyen_quantities as scq # noqa
from core.scipyen_quantities import (unitsConvertible, checkTimeUnits, # noqa
                             checkElectricalCurrentUnits,
                             checkElectricalPotentialUnits,
                             checkRescale)

import core.pyabfbridge as pab

from core.deferredmeasures import *

from gui.cursors import (DataCursor, SignalCursor, SignalCursorTypes) # noqa

from ephys import ephys

from ephys.ephys_protocol import ElectrophysiologyProtocol
from ephys import ephys_pathways
from ephys_pathways import (SynapticPathway, SynapticPathwayList)


#### END pict.core modules

class ProtocolNode(Node):

class NeoBlockNode(Node):
    def __init__(self, data: neo.Block, /,
                 tag: str | None = None, identifier: str | None = None,
                 ):
        assert isinstance(data, neo.Block), "A NeoBlockNode can only store a neo.Block object"

        super().__init__(tag,identifier,data=data)
        self._dataId_ = id(data)

class PathwayNode(Node):
    def __init__(self, data: SynapticPathway, /,
                 tag: str | None = None, identifier: str | None = None,
                 ):
        assert isinstance(data, SynapticPathway), "A PathwayNode can only store a SynapticPathway object"

        super().__init__(tag,identifier,data=data)
        self._dataId_ = id(data)

class PathwayTrialsTree:
    def __init__(self, *args, **kwargs):
        self._tree_: Tree = Tree()

        self._root_: Node = Node(tag="root", identifier="root")
        self._tree_.add_node(self._root_)

        if len(args):
            assert all(isinstance(a, tuple) and len(a) == 2 and isinstance(a[0], SynapticPathway) and isinstance(a[1], neo.Block) for a in args), "Variadic arguments must be passed as pairs of SynapticPathway ↦ neo.Block"
            for arg in args:
                pathNode = PathwayNode(arg[0], tag=arg[0].name)
                blockNode = NeoBlockNode(arg[1], tag=arg[1].name)
                self._tree_.add_node(pathNode, parent=self._root_)
                self._tree_.add_node(blockNode, parent=pathNode)

    def __len__(self):
        return len(self._tree_.children(self._tree_.root))

    def __contains__(self, obj: SynapticPathway | str) -> bool:
        if len(self) == 0:
            return False

        if isinstance(obj, SynapticPathway):
            return any(node.data == obj or (hasattr(node, "_dataId_") and node._dataId_ == id(obj)) for node in self._tree_.all_nodes_itr())

        elif isinstance(obj, str):
            isPathWithName = lambda x: isinstance(x, SynapticPathway) and x.name==obj
            return any(isPathWithName(node.data) or (hasattr(node, "_dataId_") and node._dataId_ == id(obj)) for node in self._tree_.all_nodes_itr())

        return False

    def __getitem__(self, key: SynapticPathway | str) -> neo.Block:
        if key not in self:
            raise KeyError(f"Key {key} not found")

        try:
            if isinstance(key, SynapticPathway):
                pathNode = next(iter(self._tree_.filter_nodes(lambda n: n.data == key or (hasattr(n, "_dataId_") and n._dataId_ == id(key)))))

            elif isinstance(key, str):
                isPathWithName = lambda x: isinstance(x, SynapticPathway) and x.name==key
                pathNode = next(iter(self._tree_.filter_nodes(lambda n: isPathWithName(n.data) or (hasattr(n, "_dataId_") and n._dataId_ == id(key)))))

        except:
            traceback.print_exc()
            raise KeyError(f"Key {key} not found")

        blockNode = self._tree_.get_node(next(iter(pathNode.successors(self._tree_.identifier))))

        if blockNode :
            return blockNode.data

        else:
            raise KeyError(f"Invalid {key} not found")

    def __setitem__(self, key: SynapticPathway, value: neo.Block):
        # print(f"{self.__class__.__name__}.__setitem__({key}, {value})")
        if not isinstance(key, SynapticPathway):
            raise TypeError(f"Invalid key type {type(key).__name__} when a SynapticPathway was expected")

        if not isinstance(value, neo.Block):
            raise TypeError(f"Invalid value type {type(value).__name__} when a neo.Block was expected")

        if key in self:
            # pathNode = next(iter(self._tree_.filter_nodes(lambda n: n.data == key or (hasattr(n, "_dataId_") and n._dataId_ == id(key)))))
            # blockNode = self._tree_.get_node(next(iter(pathNode.successors(self._tree_.identifier))))
            blockNode = self[key]
            blockNode.data = value
            blockNode.tag = value.name

        else:
            pathNode = PathwayNode(key, tag=key.name)
            blockNode = NeoBlockNode(value, tag=value.name)
            self._tree_.add_node(pathNode, parent=self._root_)
            self._tree_.add_node(blockNode, parent=pathNode)

    def __delitem__(self, key: SynapticPathway):
        if key not in self:
            raise KeyError(f"Invalid key {key}")
        pathNode = next(iter(self._tree_.filter_nodes(lambda n: n.data == key or (hasattr(n, "_dataId_") and n._dataId_ == id(key)))))
        self._tree_.remove_node(pathNode.identifier)

    def __iter__(self):
        return self._tree_.filter_nodes(lambda n: isinstance(n.data, SynapticPathway))

    def keys(self):
        yield from self._tree_.filter_nodes(lambda n: isinstance(n.data, SynapticPathway))

    def values(self):
        yield from map(lambda k: self[k.data], iter(self._tree_.filter_nodes(lambda n: isinstance(n.data, SynapticPathway))))

    def items(self):
        yield from map(lambda k: (k.data, self[k.data]), iter(self._tree_.filter_nodes(lambda n: isinstance(n.data, SynapticPathway))))

    # def __hash__(self):
    #     return hash(tuple(self.keys()), tuple(self.values()))

    @property
    def pathways(self):
        yield from self.keys()

    @property
    def pathwayNames(self):
        yield from map(lambda p: p.name, self.keys())

    def onPathwayScheduleEpisodeChange(self, pathway, schedule, episode,
                                       episodeAttr, newVal, oldVal):
        if pathway not in self:
            scipywarn(f"{pathway.name} does not exist in this {self.__class__.__name__} object")
            return

        if len(self[pathway].segments) == 0:
            scipywarn(f"No segments associated with {pathway.name}")
            return

        if episode.endFrame < len(self[pathway].segments) and episodeAttr == "name":
            for segment in self[pathway].segments[episode.beginFrame:episode.endFrame+1]:
                if oldVal in segment.name:
                    segment.name = segment.name.replace(oldVal, newVal)

            # self.valueChanged.emit(self)
            self.pathwayChanged.emit(pathway)

    def show(self, *args, **kwargs):
        self._tree_.show(*args, **kwargs)

