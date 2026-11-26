# $Id: treedict.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import os, traceback
from treelib import (Tree, Node)

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

class _TreeDictObjectNode_(Node):
    def __init__(self, data, /, tag: str | None = None, identifier: str | None = None):
        super().__init__(tag,identifier,data=data)
        self._dataId_ = id(data)

class TreeDict:
    r"""A mapping lass backed bhy a treelib.tree"""
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

        assert(all(isinstance(a, tuple) and len(a) ==2)), "Variadic arguments MUST be 2-tuples"

        for arg in args:
            keyTag = getattr(arg[0], "name", type(arg[0]).__name__)
            if not isinstance(keyTag, str) or len(keyTag.strip()) == 0:
                keyTag = type(arg[0]).__name__

            keyNode = _TreeDictObjectNode_(arg[0], tag=keyTag)

            if isinstance(arg[1], QtCore.QObject):
                valueTag = arg[1].objectName()

            else:
                valueTag = getattr(arg[1], "name", type(arg[1]).__name__)

            if not isinstance(valueTag, str) or len(valueTag.strip()) == 0:
                valueTag = type(arg[1]).__name__

            valueNode = _TreeDictObjectNode_(arg[1], tag=valueTag)

            self._tree_.add_node(keyNode, parent=self._root_)
            self._tree_.add_node(valueNode, parent=keyNode)

    def __len__(self):
        return len(self._tree_.children(self._root_.identifier))

    def __contains__(self, obj) -> bool:
        if len(self) == 0:
            return False

        return any(node.data == obj or (hasattr(node, "_dataId_") and node._dataId_ == id(obj)) for node in self._tree_.all_nodes_itr())

        return False

    def __getitem__(self, key):
        if key not in self:
            raise KeyError(f"Key {key} not found")

        try:
            keyNode = next(iter(self._tree_.filter_nodes(lambda n: n.data == key or (hasattr(n, "_dataId_") and n._dataId_ == id(key)))))
        except: # noqa: E722
            traceback.print_exc()
            raise KeyError(f"Key {key} not found")

        valueNode = self._tree_.get_node(next(iter(keyNode.successors(self._tree_.identifier))))

        if valueNode :
            return valueNode.data

        else:
            raise KeyError(f"Invalid key {key}")

    def __setitem__(self, key, value):
        # print(f"{self.__class__.__name__}.__setitem__({key}, {value})")
        keyTag = getattr(key, "name", type(key).__name__)
        if not isinstance(keyTag, str) or len(keyTag.strip()) == 0:
            keyTag = type(key).__name__
        if isinstance(value, QtCore.QObject):
            valueTag = value.objectName()

        else:
            valueTag = getattr(value, "name", type(value).__name__)

        if not isinstance(valueTag, str) or len(valueTag.strip()) == 0:
            valueTag = type(value).__name__

        if key in self:
            # keyNode = next(iter(self._tree_.filter_nodes(lambda n: n.data == key or (hasattr(n, "_dataId_") and n._dataId_ == id(key)))))
            # blockNode = self._tree_.get_node(next(iter(keyNode.successors(self._tree_.identifier))))
            keyNode = self[key]
            keyNode.data = value
            keyNode.tag = keyTag

        else:
            keyNode = _TreeDictObjectNode_(key, tag=keyTag)
            valueNode = _TreeDictObjectNode_(value, tag=valueTag)
            self._tree_.add_node(keyNode, parent=self._root_)
            self._tree_.add_node(valueNode, parent=keyNode)

    def __delitem__(self, key):
        if key not in self:
            raise KeyError(f"Invalid key {key}")
        keyNode = next(iter(self._tree_.filter_nodes(lambda n: self._tree_.depth(n) == 1)))
        self._tree_.remove_node(keyNode.identifier)

    def __iter__(self):
        return (k.data for k in self._tree_.filter_nodes(lambda n: self._tree_.depth(n) == 1))

    def keys(self):
        yield from (k.data for k in self._tree_.filter_nodes(lambda n: self._tree_.depth(n) == 1))

    def values(self):
        yield from (self[k.data] for k in iter(self._tree_.filter_nodes(lambda n: self._tree_.depth(n) == 1)))
        # yield from map(lambda k: self[k.data], iter(self._tree_.filter_nodes(lambda n: isinstance(n.data, SynapticPathway))))

    def items(self):
        yield from ((k.data, self[k.data]) for k in iter(self._tree_.filter_nodes(lambda n: self._tree_.depth(n) == 1)))

    def clear(self):
        nodes = tuple(self._tree_.filter_nodes(lambda n: self._tree_.depth(n) == 1))
        for node in nodes:
            self._tree_.remove_node(node.identifier)
