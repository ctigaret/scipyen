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
from ephys.ephys_pathways import (SynapticPathway, SynapticPathwayList, RecordingSource, RecordingSourceList)


#### END pict.core modules

class BlockCompliance(dict):
    r"""Custom dictionary with bool keys ↦ list of neo.Block instances.
    It follows that it can contain at most two entries, False and True, each
    mapped to a possibly empty sequence of neo.Block objects.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if len(self):
            assert all(isinstance(k, bool) for k in self), "All keys must be booleans"
            assert all(isinstance(v, typing.Sequence) for v in self.values()), "All values must be sequences"
            non_empty = [v for v in self.values() if len(v)]
            assert all(all(isinstance(b, neo.Block) for b in v) for v in non_empty), "All non-empty values must contain neo.Block objects"

    def __contains__(self, key: bool) -> bool:
        if not isinstance(key, bool):
            raise TypeError(f"Invalid key type ({type(key).__name__}) when a bool was expected")

        return key in self.keys()

    def __getitem__(self, key: bool) -> list:
        if not isinstance(key, bool):
            raise TypeError(f"Invalid key type ({type(key).__name__}) when a bool was expected")

        if key in self:
            return super().__getitem__(key)

        return []

    def __setitem__(self, key: bool, value: list[neo.Block]):
        if not isinstance(key, bool):
            raise TypeError(f"Invalid key type ({type(key).__name__}) when a bool was expected")

        if not isinstance(value, list):
            raise TypeError(f"Invalid value type ({type(value).__name__}) when a list was expected")

        if len(value) and not all(isinstance(v, neo.Block) for v in value):
            raise TypeError("Invalid value element types; expecting a list of neo.Block objects")

        super().__setitem__(key, value)

    def addCompliant(self, value: neo.Block | list[neo.Block]):
        data = self[True]

        if isinstance(value, neo.Block):
            data.append(value)
            self[True] = data

        elif isinstance(value, list) and len(value):
            if not all(isinstance(v, neo.Block) for v in value):
                raise TypeError("Invalid value element types; expecting a list of neo.Block objects")
            data.extend(value)
            self[True] = data

        else:
            raise TypeError(f"Expecting a neo.Block or a list of neo.Block objects; instead, got {type(value).__name__}")

    def addNonCompliant(self, value: neo.Block | list[neo.Block]):
        data = self[False]

        if isinstance(value, neo.Block):
            data.append(value)
            self[False] = data

        elif isinstance(value, list) and len(value):
            if not all(isinstance(v, neo.Block) for v in value):
                raise TypeError("Invalid value element types; expecting a list of neo.Block objects")
            data.extend(value)
            self[False] = data

    @property
    def compliant(self) -> list:
        return self[True]

    @compliant.setter
    def compliant(self, value: neo.Block | list[neo.Block]):
        if isinstance(value, neo.Block):
            value = [neo.Block]

        if (not isinstance(value, list)
            or (len(value) and not all(isinstance(v, neo.Block) for v in value))):
            raise TypeError(f"Invalid value type ({type(value).__name__}) when a neo.Block or a list of neo.Block objects was expected")

        self[True] = value


    @property
    def nonCompliant(self) -> list:
        return self[False]

    @nonCompliant.setter
    def nonCompliant(self, value: neo.Block | list[neo.Block]):
        if isinstance(value, neo.Block):
            value = [neo.Block]

        if (not isinstance(value, list)
            or (len(value) and not all(isinstance(v, neo.Block) for v in value))):
            raise TypeError(f"Invalid value type ({type(value).__name__}) when a neo.Block or a list of neo.Block objects was expected")

        self[False] = value

class ComplianceNode(Node):
    def __init__(self, data: BlockCompliance, /,
                 identifier: str | None = None,
                 ):
        assert isinstance(data, BlockCompliance), "A ComplianceNode can only store a BlockCompliance object"

        super().__init__(tag="protocolCompliance", data=data)
        self._dataId_ = id(data)

    @property
    def tag(self) -> str:
        # makes tag property read-only
        return super().tag

    # @property
    # def data(self) -> BlockCompliance:
    #     return super(Node, self).data
    #
    # @data.setter
    # def data(self, value: BlockCompliance):
    #     if not isinstance(value, BlockCompliance):
    #         raise TypeError(f"Expecting a BlockCompliance object; instead, got {type(value).__name__}")
    #     super().data=value

class ProtocolNode(Node):
    def __init__(self, data: ElectrophysiologyProtocol, /,
                 tag: str | None = None, identifier: str | None = None,
                 ):
        assert isinstance(data, ElectrophysiologyProtocol), "A ProtocolNode can only store an ElectrophysiologyProtocol object"

        super().__init__(tag,identifier,data=data)
        self._dataId_ = id(data)

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

class PathwayTrials:
    valueChanged: typing.ClassVar[psygnal.Signal] = psygnal.Signal(typing.Self)
    pathwayChanged: typing.ClassVar[psygnal.Signal] = psygnal.Signal(SynapticPathway)

    @classmethod
    def fromRecordingSource(cls, source: RecordingSource):
        return cls({pathway: neo.Block(name=pathway.name) for pathway in source.pathways})

    def __init__(self, *args, **kwargs):
        self._tree_: Tree = Tree()
        self._root_: Node = Node(tag="root", identifier="root")
        self._tree_.add_node(self._root_)

        if len(kwargs):
            if len(args):
                raise ValueError("Expecting either a variadic argument sequence of a varkeyword mapping, NOT both")

            args = tuple(kwargs.items())
            kwargs = {}

        elif len(args):
            if len(kwargs):
                raise ValueError("Expecting either a variadic argument sequence of a varkeyword mapping, NOT both")

            if len(args) == 1 and isinstance(args[0], dict):
                args = tuple(args[0].items())

        else:
            return

        assert all(isinstance(a, tuple) and len(a) == 2 and isinstance(a[0], SynapticPathway) and isinstance(a[1], neo.Block) for a in args), "Variadic arguments must be passed as pairs of SynapticPathway ↦ neo.Block"
        for arg in args:
            pathNode = PathwayNode(arg[0], tag=arg[0].name)
            blockNode = NeoBlockNode(arg[1], tag=arg[1].name)
            self._tree_.add_node(pathNode, parent=self._root_)
            self._tree_.add_node(blockNode, parent=pathNode)

    def __len__(self):
        return len(self._tree_.children(self._root_.identifier))

    def __contains__(self, obj: SynapticPathway | str) -> bool:
        if len(self) == 0:
            return False

        if isinstance(obj, SynapticPathway):
            return any(node.data == obj or (hasattr(node, "_dataId_") and node._dataId_ == id(obj)) for node in self._tree_.all_nodes_itr())

        elif isinstance(obj, str):
            isPathWithName = lambda x: isinstance(x, SynapticPathway) and x.name==obj
            return any(isPathWithName(node.data) for node in self._tree_.all_nodes_itr())

        return False

    def __getitem__(self, key: SynapticPathway | str) -> neo.Block:
        if key not in self:
            raise KeyError(f"Key {key} not found")

        try:
            if isinstance(key, SynapticPathway):
                pathNode = next(iter(self._tree_.filter_nodes(lambda n: n.data == key or (hasattr(n, "_dataId_") and n._dataId_ == id(key)))))

            elif isinstance(key, str):
                isPathWithName = lambda x: isinstance(x, SynapticPathway) and x.name==key
                pathNode = next(iter(self._tree_.filter_nodes(lambda n: isPathWithName(n.data))))

        except: # noqa: E722
            traceback.print_exc()
            raise KeyError(f"Key {key} not found")

        blockNode = self._tree_.get_node(next(iter(pathNode.successors(self._tree_.identifier))))

        if blockNode :
            return blockNode.data

        else:
            raise KeyError(f"Invalid key {key}")

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
        return (k.data for k in self._tree_.filter_nodes(lambda n: isinstance(n.data, SynapticPathway)))

    def keys(self):
        yield from (k.data for k in self._tree_.filter_nodes(lambda n: isinstance(n.data, SynapticPathway)))

    def values(self):
        yield from (self[k.data] for k in iter(self._tree_.filter_nodes(lambda n: isinstance(n.data, SynapticPathway))))
        # yield from map(lambda k: self[k.data], iter(self._tree_.filter_nodes(lambda n: isinstance(n.data, SynapticPathway))))

    def items(self):
        yield from ((k.data, self[k.data]) for k in iter(self._tree_.filter_nodes(lambda n: isinstance(n.data, SynapticPathway))))
        # yield from map(lambda k: (k.data, self[k.data]), iter(self._tree_.filter_nodes(lambda n: isinstance(n.data, SynapticPathway))))

    def clear(self):
        nodes = tuple(self._tree_.filter_nodes(lambda n: self._tree_.depth(n) == 1))
        for node in nodes:
            self._tree_.remove_node(node.identifier)

    # def __hash__(self):
    #     return hash(tuple(self.keys()), tuple(self.values()))

    @property
    def pathways(self):
        yield from self

    @property
    def pathwayNames(self):
        yield from (p.name for p in self)

    def getPathway(self, name: str) -> SynapticPathway:
        if name not in self:
            raise KeyError(f"Pathway named {name} not found")
        isPathWithName = lambda x: isinstance(x, SynapticPathway) and x.name==key
        pathNode = next(iter(self._tree_.filter_nodes(lambda n: isPathWithName(n.data))))
        if pathNode:
            return pathNode.data

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

class ProtocolTrials:
    r"""Mapping of ElectrophysiologyProtocol to collection of trials (neo.Block objects).

    Maps a key: ElectrophysiologyProtocol instance ↦ value: dict with bool keys,
        where:
        True ↦ list of compliant trials (i.e. trials that were recorded with the
        protocol specified in the `key`, AND contain the same number of segments as the
        number of sweeps configured in the protocol)

        False ↦ list of non-compliant trials (trials wthat were also recorded
        with the protocol specified in the key, but have less segments that the
        number of sweeos in the protocol) — this can happen when the recording
        was interrupted for some reason, resulting in fewer sweeps being saved on disk.

    NOTE: Although an ElectrophysiologyProtocol is degined to be hashable, membership
    test in collections is more complicated than simply checking each of its members
    for equality. Notably, changes in the amplifier gain during a recording WILL
    appear as if the protocol changed (even though it is only the scaling of the
    physical dimensions that has changed). A workaround is to use the
    utilities.approximatelyEqual(…) function, which tests for numerical "closeness"
    and interconvertibility of physical dimensionality (i.e., units).

    This approach is implemented by this class and its companion, `ephys_protocol.ProtocolList`.
    My recomendation is to avoid collecting protocols in stock Python lists or dicts,
    and use this class (together with `ProtocolList`) instead.

    """
    valueChanged: typing.ClassVar[psygnal.Signal] = psygnal.Signal(BlockCompliance)
    protocolChanged: typing.ClassVar[psygnal.Signal] = psygnal.Signal(ElectrophysiologyProtocol)

    def __init__(self, *args, **kwargs):
        self._tree_: Tree = Tree()
        self._root_: Node = Node(tag="root", identifier="root")
        self._tree_.add_node(self._root_)

        if len(kwargs):
            if len(args):
                raise ValueError("Expecting either a variadic argument sequence of a varkeyword mapping, NOT both")

            args = tuple(kwargs.items())
            kwargs = {}

        elif len(args):
            if len(kwargs):
                raise ValueError("Expecting either a variadic argument sequence of a varkeyword mapping, NOT both")

            if len(args) == 1 and isinstance(args[0], dict):
                args = tuple(args[0].items())

        else:
            return

        assert all(isinstance(a, tuple) and len(a) == 2 and isinstance(a[0], ElectrophysiologyProtocol) and isinstance(a[1], BlockCompliance) for a in args), "Variadic arguments must be passed as tuples of ElectrophysiologyProtocol, BlockCompliance"
        for arg in args:
            protocolNode = ProtocolNode(arg[0], tag=arg[0].name)
            complianceNode = ComplianceNode(arg[1])
            self._tree_.add_node(protocolNode, parent=self._root_)
            self._tree_.add_node(complianceNode, parent=protocolNode)


    def __len__(self):
        return len(self._tree_.children(self._root_.identifier))

    def __contains__(self, obj: ElectrophysiologyProtocol | str) -> bool:
        if len(self) == 0:
            return False

        if isinstance(obj, ElectrophysiologyProtocol):
            return any(node.data == obj or (hasattr(node, "_dataId_") and node._dataId_ == id(obj)) for node in self._tree_.all_nodes_itr())

        elif isinstance(obj, str):
            isProtocolWithName = lambda x: isinstance(x, ElectrophysiologyProtocol) and x.name==obj
            return any(isProtocolWithName(node.data) for node in self._tree_.all_nodes_itr())

        return False

    def __getitem__(self, key: ElectrophysiologyProtocol | str) -> BlockCompliance:
        if key not in self:
            raise KeyError(f"Key {key} not found")

        try:
            if isinstance(key, ElectrophysiologyProtocol):
                protocolNode = next(iter(self._tree_.filter_nodes(lambda n: n.data == key or (hasattr(n, "_dataId_") and n._dataId_ == id(key)))))

            elif isinstance(key, str):
                isProtocolWithName = lambda x: isinstance(x, ElectrophysiologyProtocol) and x.name==key
                protocolNode = next(iter(self._tree_.filter_nodes(lambda n: isProtocolWithName(n.data))))

        except: # noqa: E722
            traceback.print_exc()
            raise KeyError(f"Key {key} not found")

        complianceNode = self._tree_.get_node(next(iter(protocolNode.successors(self._tree_.identifier))))

        if complianceNode :
            return complianceNode.data

        else:
            raise KeyError(f"Invalid {key} not found")

    def __setitem__(self, key: ElectrophysiologyProtocol, value: BlockCompliance):
        if not isinstance(key, ElectrophysiologyProtocol):
            raise TypeError(f"Invalid key type {type(key).__name__} when a ElectrophysiologyProtocol was expected")

        if not isinstance(value, BlockCompliance):
            raise TypeError(f"Invalid value type {type(value).__name__} when a BlockCompliance was expected")

        if key in self:
            complianceNode = self[key]
            complianceNode.data = value
            # complianceNode.tag = value.name

        else:
            protocolNode = ProtocolNode(key, tag=key.name)
            complianceNode = ComplianceNode(value)
            self._tree_.add_node(protocolNode, parent=self._root_)
            self._tree_.add_node(complianceNode, parent=protocolNode)

    def __delitem__(self, key: ElectrophysiologyProtocol):
        if key not in self:
            raise KeyError(f"Invalid key {key}")
        protocolNode = next(iter(self._tree_.filter_nodes(lambda n: n.data == key or (hasattr(n, "_dataId_") and n._dataId_ == id(key)))))
        self._tree_.remove_node(protocolNode.identifier)

    def __iter__(self):
        return (k.data for k in self._tree_.filter_nodes(lambda n: isinstance(n.data, ElectrophysiologyProtocol)))

    def keys(self):
        yield from (k.data for k in self._tree_.filter_nodes(lambda n: isinstance(n.data, ElectrophysiologyProtocol)))

    def values(self):
        yield from (self[k.data] for k in iter(self._tree_.filter_nodes(lambda n: isinstance(n.data, ElectrophysiologyProtocol))))

    def items(self):
        yield from ((k.data, self[k.data]) for k in iter(self._tree_.filter_nodes(lambda n: isinstance(n.data, ElectrophysiologyProtocol))))

    def clear(self):
        nodes = tuple(self._tree_.filter_nodes(lambda n: self._tree_.depth(n) == 1))
        for node in nodes:
            self._tree_.remove_node(node.identifier)

    # def __hash__(self):
    #     return hash(tuple(self.keys()), tuple(self.values()))

    @property
    def protocols(self):
        yield from self

    @property
    def protocolNames(self):
        yield from (p.name for p in self)

    @property
    def notComplied(self) -> list:
        r"""List of protocols without any compliant trial"""
        return [k for k in self if len(self[k].data[True]) == 0]

    @property
    def complied(self) -> list:
        r"""List of protocols with compliant trials"""
        return [k for k in self if len(self[k].data[True])]

    def getProtocol(self, name: str) -> ElectrophysiologyProtocol:
        if name not in self:
            raise KeyError(f"Protocol named {name} not found")
        isProtocolWithName = lambda x: isinstance(x, SynapticPathway) and x.name==key
        protocolNode = next(iter(self._tree_.filter_nodes(lambda n: isProtocolWithName(n.data))))
        if protocolNode:
            return protocolNode.data

    def addCompliant(self, key: ElectrophysiologyProtocol | str, value: neo.Block | list[neo.Block]):
        protocol = self.getProtocol(key) if isinstance(key, str) else key
        if protocol not in self:
            self[protocol] = BlockCompliance()
        self[protocol].addCompliant(value)

    def addNonCompliant(self, key: ElectrophysiologyProtocol | str, value: neo.Block | list[neo.Block]):
        protocol = self.getProtocol(key) if isinstance(key, str) else key
        if protocol not in self:
            self[protocol] = BlockCompliance()
        self[protocol].addNonCompliant(value)

    def getCompliant(self, key: ElectrophysiologyProtocol | str) -> list:
        r"""Retrieves list of blocks that comply with the specified protocol
    """
        protocol = self.getProtocol(key) if isinstance(key, str) else key
        if key not in self:
            raise ValueError("Specified protocol key not found")
        return self[protocol].compliant

    def getNonCompliant(self, key: ElectrophysiologyProtocol | str) -> list:
        r"""Retrieves list of blocks that do NOT comply with the specified protocol
    """
        protocol = self.getProtocolKey(key) if isinstance(key, str) else key
        if key not in self:
            raise ValueError("Specified protocol key not found")
        return self[protocol].nonCompliant

    def setCompliant(self, key: ElectrophysiologyProtocol | str, value: neo.Block | typing.List[neo.Block]):
        protocol = self.getProtocolKey(key) if isinstance(key, str) else key
        if protocol not in self:
            self[protocol] = BlockCompliance()
        self[protocol].compliant = value

    def setNonCompliant(self, key: ElectrophysiologyProtocol | str, value: neo.Block | typing.List[neo.Block]):
        protocol = self.getProtocolKey(key) if isinstance(key, str) else key
        if protocol not in self:
            self[protocol] = BlockCompliance()
        self[protocol].nonCompliant = value

    def add(self, key: ElectrophysiologyProtocol | str, value: neo.Block | typing.List[neo.Block], complies:bool):
        if complies:
            self.addCompliant(key, value)
        else:
            self.addNonCompliant(key, value)

    def set(self, key: ElectrophysiologyProtocol | str, value: neo.Block | typing.List[neo.Block], complies:bool):
        if complies:
            self.setCompliant(key, value)
        else:
            self.setNonCompliant(key, value)

    def discardNonCompliantTrials(self) -> typing.Self:
        r"""Returns an instance of ProtocolTrials containing only protocols with compliant trials"""
        if len(self) == 0:
            return typing.Self()

        return self.__class__({p: BlockCompliance({True: b[True]}) for p, b in self.items() if len(b[True])})

    def show(self, *args, **kwargs):
        self._tree_.show(*args, **kwargs)


# @timefunc
def groupTrialsByProtocol(*trials) -> ProtocolTrials:
    result = ProtocolTrials()
    if len(trials) == 1:
        if (
            isinstance(trials[0], typing.Sequence)
            and len(trials[0])>0
            and all(isinstance(t, neo.Block) for t in trials[0])
            ):
            trials = trials[0]

        elif not isinstance(trials[0], neo.Block):
            raise TypeError("Expecting a neo.Block object or a homogeneous sequence of neo.Block objects")


    elif len(trials) == 0:
        return result

    elif len(trials) > 1:
        if not all(isinstance(t, neo.Block) for t in trials):
            raise TypeError("Expecting a neo.Block object or a homogeneous sequence of neo.Block objects")

    else:
        raise TypeError("Expecting a neo.Block object or a homogeneous sequence of neo.Block objects")


    for trial in trials:
        protocol = ephys.getProtocol(trial)
        complies = len(trial.segments) == protocol.nSweeps
        # print(f"{protocol.name} found: {protocol in result}")
        result.add(protocol, trial, complies)

    return result

