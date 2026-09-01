# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""A collection of functions to prompt user input using GUI
"""
import typing, collections, dataclasses, os, types # noqa
import numpy as np
import quantities as pq
from tribool import Tribool
import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
# __has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    # import PySide6 # noqa
    # from PySide6 import Shiboken # noqa
    # from PySide6.QtCore import (Signal, Slot, Property,)
    # from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    # from qtpy import sip
    # from qtpy.uic import loadUiType # noqa
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    # __has_sip__ = True

from core import prog # noqa
from core.prog import scipywarn
from core.inputspec import InputSpec
from . import quickdialog as qd
from .itemslistdialog import ItemsListDialog
from gui.widgets import small_widgets as smw # noqa


def selectWSData(*args, title="", single=True, asDict=False,
                 **kwargs) -> tuple | dict:
    r"""Selection of workspace variables from a list.

    Var-positional parameters:
    ==========================

    When given, it should be a string or sequence of strings with variable name
        patterns (regular expressions or "glob" expressions)

        For regular expressions see the standard Python library model 're'.

        A "glob" expressions is a string matching part of the name and containing
        one of the special characters '*' '+' as a place holder for:
            zero or more characters ('*') e.g., 'abc_*' will match variable
                names starting with 'abc_'

            one or more characters ('+') e.g., 'abc_+' will match variable names
                starting with 'abc_' and containing a SINGLE  extra character

    NOTE: These can be omitted, and a selection by name can be made in the dialog.

    Named (keyword) parameters:
    ===========================
    title: the title of the dialog; when missing, the dialog will have a suitable
        descriptive title

    single: bool flag indicating whether the selection is restricted to a single item
        (default, True) or not (False)

    asDict: bool flag; when True, variables are to be returned "packed"
        in a dict (mapping variable name as key ↦ variable). This is useful to
        also capture the symbols (i.e., names) the variables are bound to, in the
        workspace where they are being looked up.

        Default is False.

    Var-keyword parameters:
    =======================

    :glob: bool flag, which indicates how the var-positional parameters are to
        be used; default is True i.e., expecting the "glob" expressions

    :ws: a dictionary corresponding to the namespace where variables are to be
        looked up by name; defaults to the user's workspace (i.e. the workspace
        of the current Scipyen session)

    :retrieve_all: a bool flag indicating whether to show all available variables
        in the case none of the regular or glob expressions in ``*args`` found
        a match; default is False

    :preselected: name pre-selected variable (default is None)

    :parent: optional QtWidget object (default is None)

    Var-keyword parameters passed to code.workspacefunctions.lsvars(…) function
    ===========================================================================

    :var_type: type or sequence of type objects to further restrict the list of
        variables

    NOTE for other keyword parameters please see the documentation for lsvars(…)

    Returns:
    ========

    A (possibly empty) tuple containing the selected variables (when ``asDict``
    is False) or a dict.

    """
    from core.workspacefunctions import (lsvars, getvarsbytype, user_workspace)

    retrieve_all = kwargs.pop("retrieve_all", False)

    parent = kwargs.pop("parent", None)

    glob = kwargs.pop("glob", True)

    ws = kwargs.pop("ws", user_workspace())

    preselected = kwargs.pop("preselected", None)

    if "mainWindow" not in ws:
        scipywarn("In interact.selectWSData(): The supplied namespace is not the Scipyen's workspace")
        return

    user_ns_visible = dict([(k,v) for k,v in ws.items() if not k.startswith("_") and k not in ws["mainWindow"].workspaceModel.user_ns_hidden])

    name_vars = lsvars(*args, glob=glob, ws=user_ns_visible, **kwargs)

    if len(name_vars) == 0:
        if retrieve_all is True:
            name_vars = lsvars(glob=glob, ws = user_ns_visible, **kwargs)

    if len(name_vars) == 0:
        return tuple()

    name_list = sorted([name for name in name_vars])

    # print(f"interact.selectWSData: single -> {single}")

    selectionMode = (QtWidgets.QAbstractItemView.SingleSelection if single
                     else QtWidgets.QAbstractItemView.ExtendedSelection)

    if len(title.strip()):
        dtitle = f"{title}"
    else:
        dtitle = "Select Workspace Variable(s)"

    if isinstance(preselected, str) and len(preselected.strip()) and preselected in name_list:
        dialog = ItemsListDialog(parent=parent, title=dtitle,
                                 itemsList = name_list,
                                 selectmode = selectionMode,
                                 preSelected=preselected)
    else:
        dialog = ItemsListDialog(parent=parent, title=dtitle,
                                 itemsList = name_list,
                                 selectmode = selectionMode)

    ans = dialog.exec()

    if ans == QtWidgets.QDialog.Accepted:
        if asDict:
            return dict((i, ws[i]) for i in dialog.selectedItemsText) # noqa

        return tuple(ws[i] for i in dialog.selectedItemsText)

    return dict() if asDict else tuple() # noqa


def getInputs(**kwargs):
    r"""Calls 'getInput' with a prompt mapping created from key/value pairs
Returns a list.

Typical use:
::
    a, b, c = getInputs(a=1, b=2, c=3)

"""
    dlg_title = kwargs.pop("dlg_title", "Input Values")
    dlg_widget_orientation = kwargs.pop("dlg_widget_orientation", None)
    modal = kwargs.pop("modal", False)

    # NOTE: 2026-09-01 15:17:19
    # needed in order to pass prompt kwargs separately

    kw = {"dlg_title": dlg_title,
          "dlg_widget_orientation": dlg_widget_orientation,
          "modal": modal}

    return getInput(kwargs, mapping=False, **kw)

def packInputs(**kwargs):
    r"""Version of getInputs that returns a dict

Typical use:
::
    result = packInputs(a=1, b=2, c=3)

    result

    {'a': 1, 'b': 2, 'c': 3}

"""

    return getInput(kwargs, mapping=True)

def getInput(*prompts, mapping:bool=False, **kwargs):
    r"""Opens a quick dialog to prompt user input for values.

.. |nbsp| unicode:: 0xA0
   :trim:

Parameters:
-----------
:prompts: A ``dict`` with ``str`` keys (the name of the prompted variable) mapped to |nbsp|
either: |nbsp|

    * an ``InputSpec`` that enapsulates the default prompt value and type of |nbsp|
    the value; the latter is used to determine what kind of GUI input |nbsp|
    field will be used in the dialog as a prompt for the variable.

    * any object: the object value is the default, and the object type |nbsp|
    determines what kind of gui input field should be used

or a comma-separated list of _NamedInputSpec objects

:mapping: bool, optional default is False; when True, parameter names are mapped |nbsp|
to their new values (see below)

Kwargs:
=======
:dlg_title: ustom dialog title (default is "Input values")

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
    dlg_title = kwargs.pop("dlg_title", "Input Values")
    dlg_widget_orientation = kwargs.pop("dlg_widget_orientation", None)
    modal = kwargs.pop("modal", False)
    dlg = qd.QuickDialog(title=dlg_title)

    if isinstance(modal, bool):
        if modal is True:
            dlg.setWindowModality(QtCore.Qt.WindowModal)

        else:
            dlg.setWindowModality(QtCore.Qt.NonModal)

    elif isinstance(modal, QtCore.Qt.WindowModality):
        dlg.setWindowModality(modal)

    if len(prompts) == 0 or not isinstance(prompts[0], dict):
        raise TypeError(f"'prompts' expected to be contain dict; got {prompts} instead")

    prompts = prompts[0]

    prompt_widgets = dict()
    labels = dict()

    nVars = len(prompts)

    if nVars == 0:
        return

    if isinstance(dlg_widget_orientation, QtCore.Qt.Orientation):
        dlgGroupFactory = qd.VDialogGroup if dlg_widget_orientation == QtCore.Qt.Vertical else qd.HDialogGroup
    else:
        dlgGroupFactory = qd.VDialogGroup

    if nVars > 1:
        group = dlgGroupFactory(dlg)
        widget_parent = group
    else:
        group = None
        widget_parent = dlg

    for k,v in prompts.items():
        if isinstance(v, InputSpec):
            def_val  = v.default
            v_type = v.type

        elif isinstance(v, type):
            v_type = type
            def_val = InputSpec(v).default

        else:
            def_val = v
            v_type = type(v)

        if v_type is Tribool:
            w = qd.CheckBox(widget_parent, f"{k}", tristate = True)
            w.setValue(def_val)
            w.setToolTip("Tri-state checkbox: click to set the desired state: □ (False), ✓ (True) or ⋯ (Undetermined)")
            labels[k] = None

        elif issubclass(v_type, typing.Sequence):
            if not dt.is_homogeneous_sequence(def_val):
                raise TypeError("Only sequences homogeneous in their element types are supported")
            v_type = type(def_val)
            labels[k] = QtWidgets.QLabel(f"{k}")#, widget_parent)

        elif v_type is bool:
            w = qd.CheckBox(widget_parent, f"{k}")
            w.setCheckState(QtCore.Qt.Checked if def_val is True else QtCore.Qt.Unchecked)
            w.setToolTip("Click to set to □ (False) or ✓ (True)")
            labels[k] = None

        elif issubclass(v_type, (int, np.integer)):
            w = qd.HSpinBox(widget_parent,f"{k}:", widget_type = "i")
            w.setValue(def_val)
            w.setToolTip("Click to edit, scroll or use arrows to change the value")
            labels[k] = None

        elif issubclass(v_type, (float, np.floating)):
            w = qd.HSpinBox(widget_parent,f"{k}:", widget_type = "q")
            w.setToolTip("Click to edit, scroll or use arrows to change the value")
            w.setValue(def_val)
            labels[k] = None

        elif issubclass(v_type, complex):
            w = qd.HSpinBox(widget_parent,f"{k}:", widget_type = "c")
            w.setValue(def_val)
            w.setToolTip("Click to edit, scroll or use arrows to change the value")
            labels[k] = None

        elif issubclass(v_type, str):
            w = qd.StringInput(widget_parent, f"{k}:")
            w.setText(def_val)
            w.setToolTip("Click to edit text")
            labels[k] = None

        elif issubclass(v_type, np.ndarray):
            if dt.is_scalar(def_val):
                if def_val.dtype.type is np.str_:
                    w = qd.StringInput(widget_parent, f"{k}:")
                    # w.setText(", ".join(list(def_val)))
                    w.setText(str(def_val[0]))
                    w.setToolTip("Click to edit text")
                    labels[k] = None

                elif issubclass(def_val.dtype.type, np.number):
                    if issubclass(def_val.dtype.type, complex):
                        w = qd.HSpinBox(widget_parent, f"{k}:", "c")

                    else:
                        w = qd.HSpinBox(widget_parent, f"{k}:", "q")
                    labels[k] = None

                    w.setValue(def_val)
                    if isinstance(def_val, pq.Quantity):
                        w.setToolTip("Left click to edit, scroll or use arrows to change the value;\nRight click for more options")
                    else:
                        w.setToolTip("Click to edit, scroll or use arrows to change the value")

                else:
                    raise TypeError(f"Unsupported array dtype {def_val.dtype} ({def_val.dtype.type})")

            elif dt.is_vector(def_val):
                # NOTE: 2026-03-20 12:39:44
                # case of arrays with just one element treated above
                if def_val.size <= 5:
                    w = qd.StringInput(widget_parent, f"{k}:")
                    w.setToolTip("Click to edit text")
                    labels[k] = None

                    if def_val.dtype.type is np.str_:
                        w.setText(", ".join(list(def_val)))

                    elif issubclass(def_val.dtype.type, np.number):
                        w.setText(strutils.numbers2str(def_val))

                    else:
                        raise TypeError(f"Unsupported array dtype {def_val.dtype} ({def_val.dtype.type})")

            else:
                w = TableEditorWidget(widget_parent)
                w.setValue(def_val)
                w.setToolTip("Double click in cells to edit contents")
                labels[k] = QtWidgets.QLabel(f"{k}")#, widget_parent)

        else:
            raise TypeError(f"{v_type.__name__} types are not yet supported")

        if hasattr(w, "variable"):
            w.variable.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        else:
            w.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)

        prompt_widgets[k] = w

    for k in prompt_widgets:
        if isinstance(group, qd.DialogGroup):
            if isinstance(labels[k], QtWidgets.QWidget):
                group.addWidget(labels[k])
            group.addWidget(prompt_widgets[k], stretch=1)

        else:
            if isinstance(labels[k], QtWidgets.QWidget):
                dlg.addWidget(labels[k])
            dlg.addWidget(prompt_widgets[k])


    if isinstance(group, qd.DialogGroup):
        group.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        dlg.addWidget(group, stretch=1)

    dlg.adjustSize()

    dlgret = dlg.exec()

    if dlgret:
        ret = tuple(w.text() if isinstance(w, qd.StringInput) else w.selection() if isinstance(w, qd.CheckBox) else w.value() for w in prompt_widgets.values())
        if mapping:
            return dict(zip(prompts.keys(), ret))
        return ret

def newObject(t: type): # TODO 2026-06-21 23:28:27  finalize me
    # PODS:
    if t is bool:
        pass



