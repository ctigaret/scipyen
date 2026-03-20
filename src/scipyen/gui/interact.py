# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""A collection of functions to prompt user input using GUI
"""
import typing, collections, dataclasses, os
import numpy as np
from tribool import Tribool
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True


from . import quickdialog as qd
from .itemslistdialog import ItemsListDialog


class _InputSpec():
    r"""Encapsulates arguments to interact.getInput(...)
    """
    __slots__ = ("_default", "_mytype")

    def __init__(self, mytype=type(dataclasses.MISSING), default = dataclasses.MISSING):
        if isinstance(mytype, type):
            if mytype in (type(dataclasses.MISSING), type(None)): # type not specified
                if default not in (dataclasses.MISSING, None): # get it from default's type
                    mytype = type(default)

            if default in (dataclasses.MISSING, None) and mytype not in (type(dataclasses.MISSING), type(None)):
                # mytype specified, but no default given -> instantiate it from mytype
                default = mytype()

            elif not isinstance(default, mytype): # consistency/sanity check
                raise TypeError(f"default expected to be a {type.__name__}; got {type(default).__name__} instead")

        self._default=default
        self._mytype=mytype

    @property
    def type(self):
        return self._mytype

    @property
    def default(self):
        return self._default


def selectWSData(*args, title="", single=True, asDict=False, **kwargs):
    r"""Selection of workspace variables from a list
    """
    from core.workspacefunctions import (lsvars, getvarsbytype, user_workspace)

    glob = kwargs.pop("glob", True)

    ws = kwargs.pop("ws", user_workspace())

    user_ns_visible = dict([(k,v) for k,v in ws.items() if not k.startswith("_") and k not in ws["mainWindow"].workspaceModel.user_ns_hidden])

    name_vars = lsvars(*args, glob=True, ws=user_ns_visible, **kwargs)

    if len(name_vars) == 0:
        return list()

    name_list = sorted([name for name in name_vars])

    selectionMode = QtWidgets.QAbstractItemView.SingleSelection if single else QtWidgets.QAbstractItemView.ExtendedSelection

    if len(title.strip()):
        dtitle = f"Select {title}"
    else:
        dtitle = "Select variable in workspace"

    dialog = ItemsListDialog(title=dtitle, itemsList = name_list,
                            selectmode = selectionMode)

    ans = dialog.exec()

    if ans == QtWidgets.QDialog.Accepted:
        if asDict:
            return dict((i, ws[i]) for i in dialog.selectedItemsText)

        return tuple(ws[i] for i in dialog.selectedItemsText)

    return dict() if asDict else list()


def getInputs(**kwargs):
    r"""Calls 'getInput' with a prompt mapping created from key/value pairs
Returns a list.

Typical use:
::
    a, b, c = getInputs(a=1, b=2, c=3)

"""

    return getInput(kwargs, mapping=False)

def packInputs(**kwargs):
    r"""Version of getInputs that returns a dict

Typical use:
::
    result = packInputs(a=1, b=2, c=3)

    result

    {'a': 1, 'b': 2, 'c': 3}

"""

    return getInput(kwargs, mapping=True)

def getInput(prompts:dict, mapping:bool=False):
    r"""Opens a quick dialog to prompt user input for values.

.. |nbsp| unicode:: 0xA0
   :trim:

Parameters:
-----------
:prompts: a dict with str keys (the name of the prompted variable) mapped to |nbsp|
either: |nbsp|

    * an _InputSpec that enapsulates the default prompt value and type of |nbsp|
    the value; the latter is used to determine what kind of GUI input |nbsp|
    field will be used in the dialog as a prompt for the variable.

    * any object: the object value is the default, and the object type |nbsp|
    determines what kind of gui input field should be used

:mapping: bool, optional default is False; when True, parameter names are mapped |nbsp|
to their new values (see below)

Returns:
--------

A tuple (when 'mapping' is False) else a dict.

Returns None if the dialog was cancelled.

The tuple contains object values in the same order as the keys in 'prompts'.

The dict maps the keys in 'prompts' to the object values.

In either case, the object values are those set in by interaction with the
dialog.

"""
    from gui.widgets.tableeditorwidget import TableEditorWidget
    from core import datatypes as dt
    from core import strutils as strutils
    dlg = qd.QuickDialog(title="Input values")
    if not isinstance(prompts, dict):
        raise TypeError(f"'prompts' expected to be a dict; got {type(prompts).__name__} instead")

    prompt_widgets = dict()
    labels = dict()

    nVars = len(prompts)

    print(nVars)

    if nVars == 0:
        return

    if nVars > 1:
        group = qd.VDialogGroup(dlg)
        widget_parent = group
    else:
        group = None
        widget_parent = dlg

    for k,v in prompts.items():
        # label = None

        if isinstance(v, _InputSpec):
            def_val  = v.default
            v_type = v.type

        elif isinstance(v, type):
            v_type = type
            def_val = _InputSpec(v).default

        else:
            def_val = v
            v_type = type(v)

        if isinstance(v, Tribool):
            def_text = str(def_val)
        else:
            def_text = str(def_val) if (not isinstance(def_val, np.ndarray) and def_val not in (dataclasses.MISSING, None)) else ""

        if v_type == Tribool:
            w = qd.CheckBox(widget_parent, f"{k}", tristate = True)
            w.setValue(def_val)
            # w.setCheckState(QtCore.Qt.Checked if def_val is True else QtCore.Qt.Unchecked)

        elif v_type == bool:
            w = qd.CheckBox(widget_parent, f"{k}")
            w.setCheckState(QtCore.Qt.Checked if def_val is True else QtCore.Qt.Unchecked)
            # labels[k] = None

        elif issubclass(v_type, (int, np.integer)):
            w = qd.HSpinBox(widget_parent,f"{k}:", widget_type = "i")
            w.setValue(def_val)
            # w = qd.IntegerInput(widget_parent,f"{k}:")
            # w.setValue(def_text)
            # labels[k] = None

        elif issubclass(v_type, (float, np.floating)):
            w = qd.HSpinBox(widget_parent,f"{k}:", widget_type = "f")
            w.setValue(def_val)
            # w = qd.FloatInput(widget_parent, f"{k}:")
            # w.setValue(def_text)
            # labels[k] = None

        elif issubclass(v_type, complex):
            w = qd.HSpinBox(widget_parent,f"{k}:", widget_type = "c")
            w.setValue(def_val)

        elif issubclass(v_type, pq.Quantity) and def_val.size <= 1:
            w = qd.HSpinBox(widget_parent,f"{k}:", widget_type = "q")
            w.setValue(def_val)

        elif issubclass(v_type, str):
            w = qd.StringInput(widget_parent, f"{k}:")
            w.setText(def_val)
            # labels[k] = None


        elif v_type == np.ndarray:
            if dt.is_vector(def_val) and def_val.size <= 5:
                w = qd.StringInput(widget_parent, f"{k}:")
                # labels[k] = None
                if def_val.dtype.type is np.str_:
                    w.setText(", ".join(list(def_val)))
                elif issubclass(def_val.dtype.type, np.number):
                    w.setText(strutils.numbers2str(def_val))
                else:
                    raise TypeError(f"Unsupported array dtype {def_val.dtype} ({def_val.dtype.type})")
            else:
                w = TableEditorWidget(widget_parent)
                w.setValue(def_val)
                label = QtWidgets.QLabel(f"{k}:", widget_parent)
                labels[k] = label

        else:
            raise TypeError(f"{v_type.__name__} types are not yet supported")

        if hasattr(w, "variable"):
            w.variable.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        else:
            w.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)

        prompt_widgets[k] = w

        # label = QtWidgets.QLabel(f"{k}:", widget_parent)
        # labels[k] = label


        if isinstance(group, qd.VDialogGroup):
            group.addWidget(w, stretch=1)
            if k in labels:
                group.addWidget(label)
            group.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)

        else:
            if k in labels:
                dlg.addWidget(label)

    if isinstance(group, qd.VDialogGroup):
        dlg.addWidget(group, stretch=1)
    else:
        dlg.addWidget(w, stretch=1)

    # dlg.resize(-1, -1)
    dlg.adjustSize()

    dlgret = dlg.exec()

    if dlgret:
        ret = tuple(w.text() if isinstance(w, qd.StringInput) else w.selection() if isinstance(w, qd.CheckBox) else w.value() for w in prompt_widgets.values())
        if mapping:
            return dict(zip(prompts.keys(), ret))
        return ret

def newObject(t: type):
    # PODS:
    if t is bool:
        pass



