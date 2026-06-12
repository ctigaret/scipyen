# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later


r"""
The workspace model - also used by the internal shell, to which it provides the
event handlers preExecute() and post_execute().

"""
# NOTE 2020-10-19 14:53:39
# TODO factorize and bring here the code for handling the variables according to
# their types when selected & right-clicked or double-clicked in the workspace viewer
#
# TODO related to the above, also include a way to call (execute) functions in
# the workspace by double-clicking; use a GUI prompt for parameters when needed
#
# TODO bring here the code for finding variables by name, link to the variable name
# filter/finder in workspace viewer
#
import gc
import contextlib
import itertools
import seaborn as sb
import numpy as np
import matplotlib as mpl
import matplotlib.mlab as mlb
import matplotlib.pyplot as plt
from matplotlib._pylab_helpers import Gcf as Gcf
import traceback
import typing
import inspect
import os
import asyncio
import warnings
from copy import deepcopy
from functools import partial
from collections import deque
import json

from traitlets import Bunch

from gui.guiutils import (get_text_width, get_elided_text)
from gui import pictgui as pgui
from core.traitcontainers import DataBag
from core.utilities import (summarize_object_properties,
                            standard_obj_summary_headers,
                            safe_identity_test,
                            reverse_mapping_lookup,
                            )
from core.strutils import (is_cached_output_varname, is_cached_input_varname)

from core.prog import (safewrapper, timefunc, processtimefunc, timeblock, print_styled)
from core.typeenum import TypeEnum
# from jupyter_core.paths import jupyter_runtime_dir

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


class WorkspaceVarChange(TypeEnum):
    New = 1
    Modified = 2
    Removed = 4


class WorkspaceModel(QtGui.QStandardItemModel):
    '''
    The data model for the workspace variable that are displayed in the QTableView
    inside pict main window.

    Also implements:
    * IPython event handlers for the internal console (preExecute and post_execute)
    * handlers for variable change in the Scipyen workspace by code oustide of
      the internal console's event loop

    This may be used by code external to ScipyenWindow (e.g. CaTanalysis etc)

    '''
    # NOTE: 2025-09-30 22:22:50
    # Although it inherits from QStandardItemModel, little of that APi is used
    # here — this is heavily customized, perhaps too much
    # TODO 2025-09-30 22:24:00 simplify/streamline and see what can be used from QStandardItemModel
    #
    modelContentsChanged = Signal(name="modelContentsChanged")
    workingDir = Signal(str, name="workingDir")
    internalVariableChanged = Signal(dict, name="internalVariableChanged")
    varModified = Signal(object, name="varModified")
    sig_startAsyncUpdate = Signal(dict, name="sig_startAsyncUpdate")

    #                         ns    dataname ns_name
    # sig_varAdded = Signal(dict, str,     str,     name="sig_varAdded")
    # sig_varRemoved = Signal(dict, str,     str,     name="sig_varRemoved")
    # sig_varModified = Signal(dict, str,     str,     name="sig_varModified")

    def __init__(self, shell, user_ns_hidden=dict(),
                 parent=None,
                 mpl_figure_close_callback=None,
                 mpl_figure_click_callback=None,
                 mpl_figure_enter_callback=None):
        # make sure parent is passed from ScipyenWindow as an instance of ScipyenWindow
        super(WorkspaceModel, self).__init__(parent)
        # self._first_run_ = True

        self.threadpool = QtCore.QThreadPool()

        # self.Gcf = Gcf

        # self.loop = asyncio.get_event_loop()
        # NOTE: 2023-05-27 21:58:23
        # reference to IPython InteractiveShell of the internal console;
        # WARNING: this is also a reference to the "workspace" attribute of the
        # ScipyenWindow instance
        self.shell = shell
        self.currentDir = os.getcwd()

        self.cached_vars = dict()
        self.modified_vars = dict()
        self.new_vars = dict()
        self.deleted_vars = dict()
        self.user_ns_hidden = dict(user_ns_hidden)
        # self.cached_mpl_figs_in_internal = set()
        self.gcf_figs = set()
        # self.deleted_gcf_figs = set()
        # cache of the 'result' field in an ExecutionResult
        # used by postRunCell + _updateModel_
        self.lastExecutionResult = None

        # NOTE: 2023-05-23 16:58:37
        # temporary cache of notified observer changes
        self.__changes__:typing.Dict[str, WorkspaceVarChange] = dict()

        # NOTE: 2023-01-27 08:57:52 about _pylab_helpers.Gcf:
        # the `figs` attribute if an OrderedDict with:
        # int (the figure number) ↦ manager (instance of FigureManager concrete subclass, backend-dependent)
        #
        # the matplotlib figure itself is stored (by reference) as the `figure`
        # attribute of the manager's `canvas` attribute, which is a reference to
        # the figure's canvas

        self.internalVariablesMonitor = DataBag(allow_none=True, mutable_types=True,
                                                __parent__ = self)
        self.internalVariablesMonitor.verbose = True

        # NOTE: 2021-01-28 17:47:36 TODO to complete observables here
        # management of workspaces in external kernels
        # details in self.updateForeignNamespace docstring
        self._foreign_workspace_count_ = -1

        # self.foreign_namespaces = DataBag(self, allow_none=True, mutable_types=True)
        self.foreign_namespaces = dict()
        # BUG: 2021-08-19 21:45:17 FIXME
        # self.foreign_namespaces.observe(self._foreignNamespacesCountChanged_, names="length")

        # NOTE: 2021-07-28 09:58:38
        # currentItem/Name are set by selecting/activating an item in workspace view
        # self.currentItem = None
        # NOTE: 2017-09-22 21:33:47
        # cache for the current var name to allow renaming workspace variables
        # this should be updated whenever the variable name is selected/activated in the model table view
        # self.currentItemName = "" # name of currently selected variable
        # NOTE: 2021-06-12 12:11:25
        # cache symbol when the data it is bound to has changed; needed e.g.
        # for updateRowForVariable
        # CAUTION this is volatile, DO NOT USE it to retrieve current var name
        # e.g., for the purpose of renaming
        # self.originalVarName = "" # varname cache for individual row changes

        self._wspace_headers_ = [k for k in standard_obj_summary_headers if k != "Icon"]
        self.setColumnCount(len(self._wspace_headers_))
        self.setHorizontalHeaderLabels(self._wspace_headers_)  # defined in core.utilities

        self.mpl_figure_close_callback = mpl_figure_close_callback
        self.mpl_figure_click_callback = mpl_figure_click_callback
        self.mpl_figure_enter_callback = mpl_figure_enter_callback

        # NOTE: 2025-09-28 20:40:09
        # callbacks executed when a specific change (New, Modified, Removed) is
        # notified by the traits notifier
        self._varChanges_callbacks_ = {WorkspaceVarChange.New:      partial(self.__class__.addRowForVariable2, self, self.shell.user_ns),
                                       # WorkspaceVarChange.Modified: partial(self.__class__.updateRowForVariable2, self, self.shell.user_ns),
                                       WorkspaceVarChange.Modified: partial(self.__class__.variableModified, self, self.shell.user_ns),
                                       WorkspaceVarChange.Removed:  partial(self.__class__.removeRowForVariable2, self, self.shell.user_ns)}

        self.internalVariableChanged.connect(self._slot_cacheInternalVariableChange_)
        self.sig_startAsyncUpdate.connect(self._slot_updateModelAsync_)

        self._displayFont = QtWidgets.QApplication.font()

#     def _foreignNamespacesCountChanged_(self, change):
#         # FIXME / TODO 2020-07-30 23:49:13
#         # this assumes the GUI has the default (light coloured) palette e.g. Breeze
#         # or such like. What if the system uses a dark-ish palette?
#         # This approach is WRONG, but fixing it has low priority.
#         # self.foreign_kernel_palette = list(sb.color_palette("pastel", change["new"]))
#
#         print(f"{self.__class__.__name__}._foreignNamespacesCountChanged_ foreign namespaces = {len(self.foreign_namespaces)} (old: {change['old']}, new: {change['new']})")
#         pass

    @property
    def font(self) -> QtGui.QFont:
        return self._displayFont

    @font.setter
    def font(self, val:QtGui.QFont):
        self._displayFont = val
        self._updateItemsFont()

    def __reset_variable_dictionaries__(self):
        self.cached_vars = dict([item for item in self.shell.user_ns.items(
        ) if item[0] not in self.user_ns_hidden and not item[0].startswith("_")])
        self.modified_vars.clear()
        self.new_vars.clear()
        self.deleted_vars.clear()
        self.internalVariablesMonitor.clear()

    def removeForeignNamespace(self, session: dict):
        # print("workspaceModel to remove %s" % wspace)
        self.clearForeignNamespaceDisplay(session, remove=True)

    def _loadSessionCache_(self, connfilename: str):
        saved_sessions = dict()
        saved_current = set()
        saved_initial = set()

        mainWindow = self.shell.user_ns.get("mainWindow", None)

        if mainWindow:
            sessions_filename = os.path.join(os.path.dirname(mainWindow.scipyenSettings.user_config_path()),
                                             "cached_sessions.json")

            if os.path.isfile(sessions_filename):
                try:
                    with open(sessions_filename, mode="rt") as file_in:
                        saved_sessions = json.load(file_in)

                except:
                    pass

            if connfilename in saved_sessions:
                saved_current = set(saved_sessions[connfilename]["current_symbols"])
                saved_initial = set(saved_sessions[connfilename]["initial_symbols"])
                saved_hidden  = set(saved_sessions[connfilename]["hidden_symbols"])

            else:
                saved_current = None
                saved_initial = None
                saved_hidden = None

        return saved_current, saved_initial, saved_hidden

    def _mergeSessionCache_(self, connfilename: str, symbols: set):
        # NOTE: 2021-01-28 22:15:24:
        # Now, of course, with the remote kernel still alive across
        # Scipyen/ExternalIPython sessions, its namespace contents may have
        # been changed by the 3rd party process (e.g. jupyter notebook)
        #
        # Upon re-establishing the connection to the remote kernel,
        # the previously current and initial symbols are now retrieved
        # in the initial
        #
        # If no change has occurred, initial should be the union of the
        # saved initial and saved current symbol sets.

        # We are only interested in the saved current symbol sets to
        # be 'migrated' to the actual current set

        # Symbols that were previously included in "old" initial symbols
        # (saved_initial) are kept inside the new "initial" set:
        #   v in initial AND v in saved_initial
        #
        # Symbols that were previously in the "old" current symbols are
        # moved from the "initial" set to the new "current" set:
        #   v in initial AND v in saved_current
        #
        # Symbols added in the meanwhile are moved to the new "current"
        # set
        #   v in initial AND v not in saved_initial
        #
        # Symbols removed in the meanwhile are discarded:
        #   v in saved_initial OR v in saved_current AND
        #       v not in intial_symbols

        saved_current, saved_initial, saved_hidden = self._loadSessionCache_(connfilename)

        if saved_initial is not None and saved_current is not None:
            retained_initial = symbols & saved_initial

            # print("retained_initial", retained_initial)

            retained_current = symbols & saved_current

            # print("retained_current", retained_current)

            added_symbols = symbols - (retained_initial | retained_current)

            # print("added_symbols", added_symbols)

            current_symbols = retained_current | added_symbols

            initial_symbols= symbols - current_symbols

        else:
            current_symbols = set()
            initial_symbols = symbols

        hidden_symbols = saved_hidden

        return current_symbols, initial_symbols, hidden_symbols

    def _saveSessionCache_(self, connfilename: str, nsname: str):
        mainWindow = self.shell.user_ns.get("mainWindow", None)
        if mainWindow:
            sessions_filename = os.path.join(os.path.dirname(mainWindow.scipyenSettings.user_config_path()),
                                             "cached_sessions.json")

            session_dict = {"current_symbols": list(self.foreign_namespaces[nsname]["current_symbols"]),
                            "initial_symbols": list(self.foreign_namespaces[nsname]["initial_symbols"]),
                            "hidden_symbols": list(self.foreign_namespaces[nsname]["hidden_symbols"]),
                            "name": nsname,
                            }

            saved_sessions = dict()

            if os.path.isfile(sessions_filename):
                try:
                    with open(sessions_filename, mode="rt") as file_in:
                        saved_sessions = json.load(file_in)

                except:
                    pass

            # NOTE: 2021-01-30 13:48:40
            # remove stale sessions (where connection files don't exist anymore)

            stale_connections = [
                cfile for cfile in saved_sessions if not os.path.isfile(cfile)]

            for cfile in stale_connections:
                saved_sessions.pop(cfile, None)

            # NOTE: check if kernel is still alive here, or at least its connection
            # file still exists

            if os.path.isfile(connfilename):
                if connfilename in saved_sessions:
                    saved_sessions[connfilename].update(session_dict)

                else:
                    saved_sessions[connfilename] = session_dict

            if len(saved_sessions):
                with open(sessions_filename, mode="wt") as file_out:
                    json.dump(saved_sessions, file_out, indent=4)

    def clearForeignNamespaceDisplay(self, workspace: typing.Union[dict, str],
                                     remove: bool = False):
        r"""De-registers a foreign workspace dictionary.

        Parameters:
        ==========

        workspace: dict or str

            When a dict it represents a session and must contain the following
                key ↦ value mapping:

                "connection_file": str = name of the connection file

                "master": None, or a dict with the following key/value pairs:
                    "client_session_ID": str,
                    "manager_session_ID": str,
                    "tab_name": str

                "name": str = registered natural workspace name (i.e allowing
                                spaces)

                For a non-local session/connection, "master" is mapped to None.

            When a str, it is the workspace name _AS_REGISTERED_ with the workspace
            model.

        remove: bool, optional (default is False)
            When True, the workspace name will also be de-registered.

            If workspace is a session dict (see above) it will be used to determine
            whether the workspace belongs to a remote kernel (which is NOT managed
            by Scipyen's external ipython); in this case, and a snapshot of the
            symbols in the kernel's namespace will be saved to the "cached_sessions.json" file
            (typically located in ~/.config/Scipyen)

            WARNING: This has not been throughly tested and may not work with
            non-serializable objects, such as many of the Qt classes.

        """
        # check that we received a sessions dictionary and that this was generated
        # from a remotely-managed kernel

        if isinstance(workspace, str):
            nsname = workspace
            connfilename = None

            is_master = None

        elif isinstance(workspace, dict) and \
                all([s in workspace.keys() for s in ("connection_file", "master", "name")]):
            is_master = isinstance(workspace["master"], dict)
            nsname = workspace["name"]
            connfilename = workspace.get("connection_file")

        else:
            return

        # print("clearForeignNamespaceDisplay nsname", nsname, "connection_file", connfilename)
        internal_nsname = nsname.replace(" ", "_")
        # if nsname in self.foreign_namespaces:
        if internal_nsname in self.foreign_namespaces:
            # NOTE: 2021-01-28 17:45:54
            # check if workspace nsname belongs to a remote kernel - see docstring to
            # self.updateForeignNamespace for details

            if remove:
                # kernel is managed externally ==> store the "current" symbols
                # in cache
                # FIXME: this won't work because by this time the connection
                # dict from external console window connections has been removed
                # connfilename = externalConsole.window.get_connection_filename_for_workspace(natural_nsname)
                # NOTE: 2021-01-29 10:08:16 RESOLVED: we are sending the
                # connection dict instead of just the workspace name
                # print("connfilename", connfilename)
                if connfilename and os.path.isfile(connfilename) and not is_master:
                    self._saveSessionCache_(connfilename, nsname)

                self.foreign_namespaces.pop(internal_nsname)

            else:
                self.foreign_namespaces[internal_nsname]["current_symbols"].clear()

            # OK. Now, update the workspace table
            kernel_items_rows = self.rowIndexForItemsWithProps(Workspace=nsname)

            # print("kernel_items_rows for %s" % nsname,kernel_items_rows)
            if isinstance(kernel_items_rows, int):
                if kernel_items_rows >= 0:
                    # print("item", self.item(kernel_items_rows,0).text())
                    self.removeRow(kernel_items_rows)

            else:
                # must get the row for one item at a time, because the item's row
                # will have changed after the removal of previous rows
                itemnames = [self.item(r, 0).text() for r in kernel_items_rows]
                for name in itemnames:
                    r = self.rowIndexForItemsWithProps(
                        Name=name, Workspace=nsname)
                    try:
                        self.removeRow(r)
                    except:
                        pass

    def updateForeignNamespace(self, ns_name:str, cfile:str, val:typing.Union[dict, list],
                               hidden:bool = False):
        r"""Symbols in external kernels' namepaces are stored here
        Parameters:
        ==========
        ns_name:str Name of the external kernel workspace (this kernel may be managed
            by the External Console, or by some independent process such as a
            running jupyter notebook; in ths latter case this is considered a
            'remote' kernel even if it is running on the local machine)

        cfile:str Fully qualified name of the connection file

        val: dict, list, set, tuple
            When a dict, it is expected to contain one key ("user_ns") that is
                mapped to a list, set, or tuple of strings which are the symbols
                or identifiers of the variables in the external kernel workspace.

            Otherwise, it is expected to contain symbols (identifiers) as above

        self.foreign_namespaces is a DataBag where:
            key = name of foreign namespace
            value = dict with two key/set mappings:
                "initial": the set of symbols present in the said namespace when
                    it first encountered
                "current": the set of symbols present at the time this method is
                    invoked

        The intention is that the initial (pre-loaded) symbols in the namespace
        are made invisible to the user in the workspace table - the user can always
        inspect the full contents of the namespace by calling dir() in the cliennt
        console frontend.

        The distinction is necessary for the workspace model to workout which symbols
        have been added and which have been removed from the external namespace
        between subsequenct invocations of this method. Without this distinction
        the whole mechanism would query the properties for ALL variables in the
        externa namespace creating unnecessary data trafic.

        HOWEVER: Symbols added to the namespace during a session won't be seen
        in subsequent sessions, when the remote kernel survives (and is reused)
        from one session to another.

        This typically happens with external kernels started e.g., by jupyter
        notebook and such: closing the External Console leaves these kernels running
        (my design, because these kernels are supposed to be managed by an
        independent process); then, re-starting the External Console (either in
        the same Scipyen session of in a subsequent one) will "see" these existing
        symbols as part of the "initial" set and hence they won't be listed in
        the workspace table - these variables will in effect be "masked".

        This "masking" can become a problem when repeatedly restarting Scipyen
        (or even just the External Console)  but the remote kernel is kept alive
         - case in poiint being a running jupyter notebook.

        The immediate workaround is to drop the distinction between "initial" and
        "current" symbols when the namespace is first encountered, with the risk
        of populating the workspace table with symbols added to the namespace
        immediately after the connection to the kernel was initialized (and
        including anysymbols created by the code executed at initialization of
        the console). Not all these may be relevant to the user.

        Alternatively, a tally of the "current" set of symbols when the connection
        to the remote kernel is stopped could be saved (as a snapshot) - but only
        for truly remote kernels (i.e. NOT started by the external ipython console).

        This snapshot would then be added to the "current" set in a subsequent session
        IF the connection is made to a running remote kernel which has been used before.

        To implement this latter solution we need:
            a) to know that the named workspace (ns_name) belongs to a 'remote'
                kernel; this can be determined by checking the
                ExternalIPython.window._connections_ dictionary like in this
                pseudocode:

                Let cfile be the filename of a connection file, and connections
                the ExternalIPython.window._connections_ dictionary

                Find connections[cfile] where
                    connections[cfile]['name'] == ns_name

                If found, check that connections[cfile]['master'] is None
                    If None then the kernel is managed by a 3rd party process.

                => remember the connection file name: if this file exists during
                a future Scipyen session (or ExternalIPython session) and is
                opened, then, provided that remote kernel is still running,
                its variables created in the previous Scipyen or ExternalIPython
                session are still present, unless modified by another independent
                client.

            b) to store the "current" set of variables at the end of the session

                Probably the best is to use a dict with
                    key = connection file name
                    value = set of "current" variables.

                then save it at the end of Scipyen session as a *.json file
                inside Scipyen config directory.

            c) when starting a remote kernel session in ExternalIPython, check
                if the chosen connection file name exists in the dictionary
                 stored as described in (b)

                If the chosen connection file name does exist, then check
                the stored "current" dict against the symbols in the remote
                kernel workspace and popu;ate the workspace model accordingly.

            d) the remote workspaces dictionary should probably NOT be loaded
            via the confuse configuration mechanism: depending on how frequent
            new remote kernels are used, this file may grow substantially

            e) set an age limit for the contents of the dictionary, and also
            give the possibility to clear it at any time (thus re-used kernels
            will be interpreted as new and symbols persisting across sessions
            will be masked as it happens now).

        """
        # print(f"{self.__class__.__name__}.updateForeignNamespace ns_name = {ns_name}, cfile = {cfile}")

        internal_ns_name = ns_name.replace(" ", "_")

        if isinstance(val, dict):
            symbols = val.get('user_ns', set())

        elif isinstance(val, (list, set, tuple, deque)):
            symbols = set([k for k in val])

        else:
            raise TypeError(
                "val expected to be a dict or a list; got %s instead" % type(val).__name__)

        if internal_ns_name not in self.foreign_namespaces:
            # print(f"{self.__class__.__name__}.updateForeignNamespace new namespace: {ns_name} ({internal_ns_name})")
            if hidden:
                hidden_symbols = symbols.copy()
                initial_symbols = set()
                current_symbols = set()
            else:
                hidden_symbols = set()
                initial_symbols = symbols.copy()
                current_symbols = symbols.copy()
            # first time ns_name is dealt with
            # NOTE:2021-01-28 21:58:59
            # check to see if there is a snapshot of a currently live kernel
            # to retrieve live symbols from there (session 'cache')
            if os.path.isfile(cfile):  # make sure connection is alive
                externalConsole = self.shell.user_ns.get("external_console", None)
                if externalConsole:
                    cdict = externalConsole.window.connections.get(cfile, None)
                    if isinstance(cdict, dict) and "master" in cdict and cdict["master"] is None:
                        # print("found remote connection for %s" % cfile)
                        current_symbols, initial_symbols, hidden_symbols = self._mergeSessionCache_(cfile, initial_symbols)

            # special treatment for objects loaded from NEURON at kernel
            # initialization time (see extipyutils_client
            # nrn_ipython_initialization_cmd and the
            # core.neuron_python.nrn_ipython module)

            # may have already been in saved current
            neuron_symbols = initial_symbols & {"h", "ms", "mV"}

            current_symbols = current_symbols | neuron_symbols  # set operations ensure unique elements

            # will trigger _foreignNamespacesCountChanged_ which at the
            # moment, does nothing
            self.foreign_namespaces[internal_ns_name] = {"current_symbols": current_symbols,
                                                "initial_symbols": initial_symbols,
                                                "hidden_symbols": hidden_symbols
                                                }

        else:
            # print("\tupdateForeignNamespace: foreign namespaces:", self.foreign_namespaces)
            # print("\tself.foreign_namespaces[ns_name]['current']", self.foreign_namespaces[ns_name]["current"])
            ns = self.foreign_namespaces.get(internal_ns_name, None)
            if ns is None:
                scipywarn(f"{self.__class__.__name__}.updateForeignNamespace expecting namespace: {ns_name} ({internal_ns_name}) but not found")
                return
            # print(f"{self.__class__.__name__}.updateForeignNamespace found namespace: {ns_name} ({internal_ns_name})")

            if hidden:
                hidden_symbols = symbols.copy()
                initial_symbols = ns["initial_symbols"].copy()
                current_symbols = ns["current_symbols"].copy()
            else:
                hidden_symbols = ns["hidden_symbols"].copy()
                initial_symbols = ns["initial_symbols"].copy()
                current_symbols = symbols.copy()

            added_symbols = current_symbols - initial_symbols # newly added symbols
            removed_symbols = initial_symbols - current_symbols # symbols removed

            for vname in removed_symbols:
                # self.removeRowForVariable2(ns, vname, internal_ns_name)
                self.removeRowForVariable2(ns, vname, ns_name)

            # cache for next round of listings
            ns["initial_symbols"] = current_symbols
            ns["current_symbols"] = current_symbols

    def hasForeignNamespace(ns_name:str) -> bool:
        r"""Check the presence of a foreign name space"""

        internal_ns_name = ns_name.replace(" ", "_")
        return internal_ns_name in self.foreign_namespaces.keys()

    def getForeignNamespaceSymbols(self, ns_name:str, what:str = "current"):
        r"""Returns a set of symbol names in the foreign name space `ns_name`

        If the foreign name space `ns_name` does not exist, or is not registered,
        returns an empty set.

        Representation of foreign name spaces contain three sets of symbols
        that indicate how are they to be displayed in the workspace view:
        'hidden' -> never displayed
        'current' -> always displayed
        'initial' -> used to determine additions and removals of symbols
            in the foreign name space

        Parameters:
        ==========
        ns_name: name of the foreign name space (e.g., 'kernel 0')
        what: one of 'current', 'initial', 'hidden'
        """

        internal_ns_name = ns_name.replace(" ", "_")

        if internal_ns_name not in self.foreign_namespaces.keys():
            return set()

        target = f"{what}_symbols" if what in ("current", "initial", "hidden") else "current_symbols"

        return self.foreign_namespaces[internal_ns_name].get(target, set())


    def clear(self):
        self.cached_vars.clear()
        self.modified_vars.clear()
        self.new_vars.clear()
        self.deleted_vars.clear()
        # self.user_ns_hidden.clear()
        self.internalVariablesMonitor.clear()

    def isDisplayable(self, ns, name, val):
        r"""Check if the name ↦ value binding is in the ns and should be shown in the viewer.

        A visible symbol ↦ value should be visible to the user IF name is a
        symbol in the Scipyen Console namespace, AND
        • is not one of the IPython symbols for cached input variables
        • is not one of the IPython symbols for cached output variables
        • is not among the symbols for the "hidden" objects.

            The 'hidden' variables are set up at Scipyen's initialization
            and include loaded modules and variables set up BEFORE the
            Scipyen Console is alive. These are available to the user at the
            Scipyen Console, but not shown inside the workspace viewer, in
            order to avoid clutter.

        All of the above can, of course, be listed with the 'dir' command.

        WARNING: A variable returned by code execution (but NOT bound to a symbol
        through an assignment statement in the code) is automatically bound by
        IPython to the symbol '_' which is reserved for the most recent output.

        """
        if name not in ns:
            return False

        # rule out IPython cached inputs
        if is_cached_input_varname(name):
            return False

        # rule out IPython cached outputs
        if is_cached_output_varname(name):
            return False

        if name in self.user_ns_hidden.keys():
            return False

        return True

    def bindObjectInNamespace(self, varname:str,
                              data:typing.Any, hidden:bool=False,
                              namespace:typing.Optional[dict] = None):
        r"""Binds an object to a symbol, in the specified namespace.
        Unless the symbol is flagged as 'hidden', the object will be summarized
        in the workspace viewer, and changes to its contents may be automatically
        shown in the viewer.

        Parameters:
        ===========
        varname:str
            The symbol to be created in the namespace; if the symbol already
            exists (and bound to something else) it will be rebound to the new
            object. WARNING: The 'old' object will still exist in memory, and will
            be garbage collected when all references to it are removed.

            For details about these concepts, please see the documentation for
            'object.__del__' in section '3. Data model' of the pfficial Python
            documentation.

        data: Any
            The object to be bound to the symbol specified by 'varname' inside
            the namespace (see below)

        hidden: bool Optional, default is False.
            When True, the new binding of 'data' to 'varname' will be hidden from
            the workspace viewer, and the 'data' object will NOT be monitored by
            this worksapce model instance.

        namespace:dict Optional, default is None.
            The namespace where the 'data' object will be bound to 'varname'.
            This binding is essentially a key ↦ value mapping.

            When None, the function will create the binding in the user namespace
            (i.e. the namespace that is accessible to the user in Scipyen's console).

        """
        if namespace is None:
            namespace = self.shell.user_ns

        if namespace != self.shell.user_ns:
            scipywarn("Currently, only the internal workspace is supported")
            return

        # print(f"\n{self.__class__.__name__}.bindObjectInNamespace(varname={varname}, hidden={hidden})")

        # NOTE: 2023-05-27 22:24:04
        # If needed, store a reference in self.user_ns_hidden, so that it won't
        # be picked up by self.internalVariablesMonitor observer
        if hidden:
            self.user_ns_hidden[varname] = data

        # NOTE: 2023-06-07 08:34:57
        # emulates a console execution
        self.preExecute()
        namespace[varname] = data
        self.postRunCell(Bunch(success=True))

    def unbindFromNamespace(self, varname:typing.Union[str, typing.Sequence[str]],
                                  namespace:typing.Optional[dict] = None) -> typing.Any:
        r"""Unbinds an object from its symbol is a specified namespace.
        WARNING: The object may be still alive, but unaccessible in the namespace
        via its symbol given by varname, until it will be garbage-collected.
        """
        if namespace is None:
            namespace = self.shell.user_ns

        if namespace != self.shell.user_ns:
            warnings.warn("Currently, only the internal workspace is supported")
            return
        # print(f"{self.__class__.__name__}.unbindFromNamespace(varname = {varname})")
        # print(f"{varname} is observed: {varname in self.internalVariablesMonitor.keys()}")
        if isinstance(varname, str):
            if varname in namespace:
                if varname not in self.user_ns_hidden:
                    # NOTE: 2023-06-07 08:34:57
                    # emulates a console execution
                    self.preExecute()
                    obj = namespace.pop(varname)
                    # self.__changes__[varname]=WorkspaceVarChange.Removed
                    self.postRunCell(Bunch(success=True))
                    return obj

        elif isinstance(varname, typing.Sequence):
            existing = list(filter(lambda v: isinstance(v, str) and len(v.strip()) and v in namespace, varname))
            if len(existing):
                ret = list()
                self.preExecute()
                for v in existing:
                    ret.append(namespace.pop(v))
                self.postRunCell(Bunch(success=True))
                return ret

        # print(f"{self.__class__.__name__}.unbindFromNamespace(varname = {varname}) not found")

    def rebindObjectInNamespace(self, old_name:str, new_name:str,
                                namespace:typing.Optional[dict] = None):

        if namespace is None:
            namespace = self.shell.user_ns

        if namespace != self.shell.user_ns:
            warnings.warn("Currently, only the internal workspace is supported")
            return

        if old_name in namespace:
            if old_name not in self.user_ns_hidden:
                self.preExecute()
                obj = namespace.pop(old_name)
                self.postRunCell(Bunch(success=True))
                self.preExecute()
                namespace[new_name] = obj
                self.postRunCell(Bunch(success=True))

    def enableInternalVariableObserver(self, enable:bool = True):
        if enable:
            self.internalVariablesMonitor.unobserve(self.noopCB)
            self.internalVariablesMonitor.observe(self.internalVariablesListenerCB)
        else:
            self.internalVariablesMonitor.unobserve(self.internalVariablesListenerCB)
            self.internalVariablesMonitor.observe(self.noopCB)

    def noopCB(self, change:dict):
        r"""No-op callback"""
        return

    def internalVariablesListenerCB(self, change:dict):
        r"""Callback for notifications from the workspace monitor (a trait notifier).
        Emits self.internalVariableChanged signal
        """
        if change.type not in ("remove", "removed"):
            if change.name not in self.shell.user_ns:
                change.type = "remove"
        self.internalVariableChanged.emit(change)

    @Slot(str, str)
    def _slot_dataModifiedInViewer(self, varName:str, ns_name:str="internal"):
        from gui.scipyenviewer import ScipyenViewer
         # FIXME: 2025-09-28 21:12:26 allow the use of foreign namespaces too TODO
        ns = self.shell.user_ns
        viewer = self.sender()
        # print(f"{self.__class__.__name__}._slot_dataModifiedInViewer(varNaame={varName}, ns_name={ns_name}) -> sender: {type(viewer).__name__}")
        exclude = [viewer] if isinstance(viewer, ScipyenViewer) else list()
        self.refreshDataViewers(ns, varName, ns_name, exclude=exclude)

    @Slot(dict)
    def _slot_cacheInternalVariableChange_(self, change):
        if isinstance(change, Bunch):
            name = change.name
            change_type = getattr(change, "change_type", change.type)
        else:
            name = change["name"]
            change_type = change["change_type"]

        # print(f"\n{self.__class__.__name__}._slot_cacheInternalVariableChange_: for variable {name}: change_type = {change_type}")

        if change_type == "new":
            self.__changes__[name] = WorkspaceVarChange.New

        elif change_type in ("remove", "removed"):
            self.__changes__[name] = WorkspaceVarChange.Removed

        elif change_type == "modified":
            self.__changes__[name] = WorkspaceVarChange.Modified

        else:
            # for legacy (traitlets.TraitType-style) notifications
            # that lack 'change_type' attribute
            if name not in self.shell.user_ns:
                self.__changes__[name] = WorkspaceVarChange.New
            else:
                self.__changes__[name] = WorkspaceVarChange.Modified

    @Slot(tuple)
    def _slot_updateModelFromMonitor_(self, value):
        name, alteration = value
        if isinstance(alteration, WorkspaceVarChange):
            # calls a callback to affect the model ⇒ the viewer UI
            self._varChanges_callbacks_[alteration](name)
            # ⇒ in MainWindow this will trigger cosmetic update of the viewer
            self.modelContentsChanged.emit()

    def preExecute(self):
        r"""Updates internalVariablesMonitor DataBag.

    Used as a callback (hence, called) by IPython after entering a python
    command at the Scipyen console, but BEFORE executing the code contained
    in the command.

    In order for the workspace viewer to be updated dyamically, this method
    should also be called when code outside the Scipyen console adds, removes
    or modifies workspace variables, followed by calling postRunCell.

    For GUI components, the best way to deal with this is via calling
    'bindObjectInNamespace' and 'unbindFromNamespace' methods of the
    WorkspaceModel instance.
        """
        # ensure we observe only "user" variables in user_ns (i.e. excluding the "hidden"
        # ones like the ones used by ipython internally)
        # NOTE: 2023-01-28 13:27:40
        # we take a snapshot of the current user_ns HERE:
        # self.cached_vars = dict([item for item in self.shell.user_ns.items(
        # ) if not item[0].startswith("_") and self.isDisplayable(item[0], item[1])])

        self.cached_vars = dict([item for item in self.shell.user_ns.items() if self.isDisplayable(self.shell.user_ns, *item)])
#
        # print(f"{print_styled(f'\nIn {self.__class__.__name__}.preExecute:', color='magenta')}")
        # print(f"{print_styled(f'\t{len(self.cached_vars)} cached_vars', color='magenta')}")

        # NOTE: 2023-06-07 08:39:15
        # at this stage there may be variables not cached but still monitored
        # we need to remove then from the monitor, but withhold notifications
        with self.internalVariablesMonitor.observer.hold_trait_notifications():
            observed_set = set(self.internalVariablesMonitor.keys())
            cached_set = set(self.cached_vars)

            observed_not_cached = observed_set - cached_set
            # print(f"{print_styled('\t{len(observed_not_cached)} observed_not_cached', color='magenta')}")
            for var in observed_not_cached:
                self.internalVariablesMonitor.pop(var, None)

    # @timefunc
    # def post_execute(self):
    #     r"""Updates workspace model AFTER kernel execution.
    #     Also takes into account:
    #     1) matplotlib figures that have been created by plt commands at the console
    #     """
    #     # NOTE: 2022-03-15 22:05:21
    #     # check if there is a mpl Figure created in the console (but NOT bound to
    #     # a user-available identifier)
    #
    #     # mpl_figs_nums_in_ns = [(f.number, f) for f in self.shell.user_ns.values() if isinstance(f, mpl.figure.Figure)]
    #
    #     # NOTE: 2023-01-28 22:36:33
    #     # • a figure was created using pyplot:
    #     #   ∘ by calling plt.figure() ⇒ the new Figure instance will be present
    #     #       in user_ns AND will be referenced in Gcf.figs;
    #     #       the default identifier in the IPython shell's user_ns is '_'
    #     #       (underscore) UNLESS the user binds the return from plt.figure()
    #     #       to a specified identifier e..g figX = plt.figure()
    #     #   ∘ by calling a plotting function in plt, e.g. plt.plot(x,y) ⇒ a new
    #     #       Figure instance will be referenced in Gcf.figs, BUT NOT in user_ns
    #     #       (the plt plotting functions return artist(s), but not the figure
    #     #       object that renders the artist(s) on screen)
    #     #
    #     # • a figure was created directly via its c'tor ⇒ the new figure object
    #     #   will be resent in user_ns, bound to the default symbol ('_') or to
    #     #   a user-specified symbol; in either case,
    #     #   the new figure instance will NOT be referenced in Gcf.figs
    #
    #     # Also, NOTE that figures created via their c'tor do not usually have a
    #     # figure manager (i.e. the fig.canvas.manager attribute is None) hence
    #     # they also do NOT have a number (in the pyplot sense)
    #     #
    #     # Hence we need to operate independently of whether there is a number
    #     # associated with the figure, or not.
    #
    #     from core.workspacefunctions import validate_varname
    #
    #     # print(f"\npost_execute cached figs {self.cached_mpl_figs_in_internal}")
    #
    #     # print(f"\npost_execute Gcf figs {Gcf.figs}")
    #
    #     # NOTE: 2023-01-29 23:32:44
    #     # capture the figures referenced in Gcf
    #     # these should be ALL mpl figures Scipyen knows about, see NOTE: 2023-01-29 23:30:32
    #     #
    #     current_gcf_figs = set(
    #         fig_manager.canvas.figure for fig_manager in Gcf.figs.values())
    #
    #     # print(f"\npost_execute current figs {current_gcf_figs}")
    #
    #     deleted_mpl_figs = self.cached_mpl_figs_in_internal - current_gcf_figs
    #
    #     # print(f"\npost_execute deleted_mpl_figs = {deleted_mpl_figs}")
    #
    #     for f in deleted_mpl_figs:
    #         f_names = list(k for k, v in self.shell.user_ns.items() if isinstance(
    #             v, mpl.figure.Figure) and v == f and not k.startswith("_"))
    #         if len(f_names):
    #             for n in f_names:
    #                 self.shell.user_ns.pop(n, None)
    #                 if n in self.internalVariablesMonitor.keys():
    #                     self.internalVariablesMonitor.pop(n, None)
    #
    #     new_mpl_figs_from_gcf = current_gcf_figs - self.cached_mpl_figs_in_internal
    #
    #     for k, v in self.shell.user_ns.items():
    #         if isinstance(v, mpl.figure.Figure):
    #             if v not in self.cached_mpl_figs_in_internal:
    #                 new_mpl_figs_from_gcf.add(v)
    #
    #     # print(f"\npost_execute new_mpl_figs_from_gcf = {new_mpl_figs_from_gcf}")
    #
    #     for fig in new_mpl_figs_from_gcf:
    #         fig_var_name = "Figure"
    #         # NOTE: 2023-01-29 23:34:00
    #         # make sure all new figures are managed by pyplot (see NOTE: 2023-01-29 23:30:32)
    #         # We need to call this early because we need a fig.number to avoid
    #         # complicatons in fig variable name management!
    #         if getattr(fig.canvas, "manager", None) is None:
    #             fig = self.parent()._adopt_mpl_figure(fig)  # , integrate_in_pyplot=False)
    #
    #         if fig.canvas.manager is not None and getattr(fig.canvas.manager, "num", None) is not None:
    #             fig_var_name = f"Figure{fig.canvas.manager.num}"
    #
    #         elif getattr(fig, "number", None) is not None:
    #             fig_var_name = f"Figure{fig.number}"
    #
    #         if fig_var_name in self.shell.user_ns:
    #             fig_var_name = validate_varname(
    #                 fig_var_name, ws=self.shell.user_ns)
    #
    #         # cached_figs = [v for v in self.cached_vars.values() if isinstance(v, mpl.figure.Figure)]
    #         cached_figs = [v for v in self.shell.user_ns.values(
    #         ) if isinstance(v, mpl.figure.Figure)]
    #         if fig not in cached_figs:
    #             # print(f"\n adding fig_var_name {fig_var_name}")
    #             self.shell.user_ns[fig_var_name] = fig
    #             self.internalVariablesMonitor[fig_var_name] = fig
    #
    #     if isinstance(self.parent(), QtWidgets.QMainWindow) and type(self.parent()).__name__ == "ScipyenWindow":
    #         cached_viewers = [(wname, win) for (wname, win) in self.cached_vars.items() if isinstance(
    #             win, QtWidgets.QMainWindow) and self.parent()._isScipyenViewerClass_(type(win))]
    #         user_ns_viewers = [v for v in self.shell.user_ns.values() if isinstance(
    #             v, QtWidgets.QMainWindow) and self.parent()._isScipyenViewerClass_(type(v))]
    #         for w_name_obj in cached_viewers:
    #             if w_name_obj[1] not in user_ns_viewers:
    #                 self.cached_vars.pop(w_name_obj[0], None)
    #
    #             else:
    #                 # print(f"win: {w_name_obj[1]}")
    #                 self.parent().registerWindow(w_name_obj[1])
    #                 # if type(w_name_obj[1]) in self.parent().viewers.keys():
    #                 #     if w_name_obj[1] not in self.parent().viewers[type(w_name_obj[1])]:
    #                 #         self.parent().registerWindow(w_name_obj[1])
    #
    #     # with timeblock("post_execute workspace update"):
    #     #     # current_user_varnames = set(self.shell.user_ns.keys())
    #     #     # observed_varnames = set(self.internalVariablesMonitor.keys())
    #     #     # del_vars = observed_varnames - current_user_varnames
    #     #     # self.internalVariablesMonitor.remove_members(*list(del_vars))
    #     #     # current_vars = dict([item for item in self.shell.user_ns.items() if not item[0].startswith("_") and self.isDisplayable(item[0], item[1])])
    #     #     # self.internalVariablesMonitor.update(current_vars)
    #     #     # just update the model directly
    #     #     # QtCore.QTimer.singleShot(0, self.update)
    #     #     # FIXME: 2023-05-23 17:57:21
    #     #     # Although this speeds up execution, the workspace viewer does NOT get
    #     #     # updated
    #     #     #
    #     #     # timer = QtCore.QTimer()
    #     #     # timer.timeout.connect(self.update)
    #     #     # timer.start(0)
    #     #
    #     #     # NOTE: 2023-05-23 17:58:06 FIXME:
    #     #     # slow when too many variables, but surely works!
    #     #     self.update()
    #
    #     # NOTE: 2023-05-23 17:58:06 FIXME:
    #     # UI-blocking and, when too many variables, very slow, but surely works!
    #     self.update()
    #
    #     current_dir = os.getcwd()
    #
    #     self.workingDir.emit(current_dir)

    def preRunCell(self, info):
        r"""Use this function EXCLUSIVELY for debugging"""
        pass

    def postRunCell(self, result: Bunch):
        if hasattr(result, "result"):
            # NOTE: 2023-06-06 12:56:44
            # this is bound to the symbol "_" in the internal namespace, by IPython
            self.lastExecutionResult = result.result

        else:
            self.lastExecutionResult = None

        if hasattr(result, "success") and result.success:
            self._updateModel_(self.shell.user_ns)

    def _updateModel_(self, ns: dict):
        r"""Determines what workspace variables have been removed/added/modified.

        This change may be a consequence of:
        • code run at Scipyen's console
        • code run outside of console, but which adds/removes/modifies objects in
            the workspace

        The changes will then be propagated to the internalVariablesMonitor
        which will notify the observer self.internalVariablesListenerCB for it,
        in turn, to trigger the UI update.

        Parameters:
        ===========
        ns: a mapping key:str ↦ value:Any
            This is typically the shell user_ns, which in theory, is either the
            workspace (or namespace) of the current session, or that of an external
            (i.e. foreign) running kernel.

            In practice, this is used in relation to the session's namespace
            visible in Scioyen's console.

        ATTENTION - It is assumed that all changes in the workspace took place
        already.

        The only exception to this assumption is the case of matplotlib figures
        where the workspace may still hold references to matplotlib figures which
        were disposed of by the matplotlib figure manager (in the land of
        matplotlib pyplot).

        Conversely, there may be matplotlib figures created by code NOT via
        pyplot API. For these, I take the approach to registere them with pyplot
        in order to be able to manage them more consistently.

        """
        # from core.workspacefunctions import validate_varname

        # NOTE: 2023-06-14 08:37:57
        # whenever  None is bound to a signal thus must always be shown

        # ATTENTION 2023-05-24 17:04:36
        #
        # I assume all changes to the workspace have already taken place.
        #
        # The notifications from the variable observer DataBag are used to trigger
        # GUI updates, they do NOT alter the contents of the 'ns' workspace !!!
        #
        #
        # print(f"{self.__class__.__name__}._updateModel_")

        # ###
        # 1. deal with matplotlib figures
        #
        # Figures can be:
        #
        # a) "New": created as a result of code executed in console - that is, AFTER
        #   preExecute, and EITHER
        #   a.1) directly bound to a user-defined symbol in ns (when code is an assignment)
        #   a.2) assigned to a cached input variable by IPython (when code does not end in ';')
        #   a.3) unbound, when generating code is NOT an assignment and DOES end with ';',
        #       or otherwise calls a figure-generating code indirectly (i.e., deeper
        #       in the call stack) yet somewhat manages to "inject" it into the ns
        #       (not sure if such a thing is at all possible)
        #
        #       ⇒ without binding, there is no way to handle this ⇒ memory leak
        #        unless is grarbage-collected at some point
        #
        #
        #   a.a) The figure-generating code is part of pyplot API ⇒ the new figure
        #       is added to the Gcf figures AFTER preExecute - hence is absent
        #       from Gcf at preExecute, but present NOW)
        #
        #       a.a.1) ⇒ directly bound to a user-defined symbol in ns (assignment)
        #       a.a.2) ⇒ figure is self.lastExecutionResult (i.e. bound to '_' in ns)
        #       a.a.3) ⇒ figure is in Gcf but not found in ns
        #
        #   a.b) The figure-generating code is outside the pyplot API (e.g. calls
        #       mpl.figure.Figure(...) c'tor directly) ⇒ the new figure is NEVER
        #       in Gcf ⇒ getattr(fig, "number", None) is None ALWAYS
        #
        #       a.b.1) ⇒ as a.a.1 but w/o "number" attribute  ⇒ should "adopt" or otherwise treat as Scipyen viewers
        #       a.b.2) ⇒ as a.a.2 but w/o "number" attribute  ⇒ should "adopt" or otherwise treat as Scipyen viewers
        #       a.b.3) ⇒ this is where a memory leak might be possible, unless the
        #               garbage collector plugs the hole (since there is no reference to
        #               the object)
        #
        #       NOTE: Assigning variables to the ns from deeper code is possible
        #       via workspacefunctions.assignin() function, but this will ALWAYS
        #       bind the object to a symbol in the ns
        #
        # b) "New", created BEFORE preExecute (i.e., NOT by code called at the console
        #   but nevertheless run sometimes before) - because this MAY involve
        #   pyplot API (hence present in the Gcf) yet we do NOT want any such
        #   figures internal to the code to be unnecesssrily displayed, we must
        #   skip them, here. Hence, we only check for new figs from gcf, whe it
        #   comes to their addition


        # ###
        # 2. deal with Scipyen viewer windows - NOTE: 2023-06-07 09:10:08
        # dealt with from main window (Scipyen's main window) (see 'registerWindow'
        # and 'deRegisterWindow' methods, there)
        #
        # Here, any QMainWindow-based viewer, other than matplotlib Figure, that
        # created by commands at the console using its default constructor will
        # have some limited functionality (especially, no parent() widget) and will
        # not interact with Scipyen's main window and workspace unless the main
        # window is specified at the constructor.
        #
        # Best is to handle these viewers via the gui (for now)
        #
        # if isinstance(self.parent(), QtWidgets.QMainWindow) and type(self.parent()).__name__ == "ScipyenWindow":
        #     # cached_viewers = [(wname, win) for (wname, win) in self.shell.user_ns.items() if isinstance(
        #     #     win, QtWidgets.QMainWindow) and self.parent()._isScipyenViewerClass_(type(win))]
        #     cached_viewers = [(wname, win) for (wname, win) in self.cached_vars.items() if isinstance(
        #         win, QtWidgets.QMainWindow) and self.parent()._isScipyenViewerClass_(type(win))]
        #     user_ns_viewers = [v for v in ns.values() if isinstance(
        #         v, QtWidgets.QMainWindow) and self.parent()._isScipyenViewerClass_(type(v))]
        #     for w_name_obj in cached_viewers:
        #         if w_name_obj[1] not in user_ns_viewers:
        #             self.cached_vars.pop(w_name_obj[0], None)
        #
        #         else:
        #             self.parent().registerWindow(w_name_obj[1])

        # ###
        # 3. now, deal with everything else
        #
        # if self.lastExecutionResult:
        #     print(f"{print_styled(f'\n{self.__class__.__name__}._updateModel_ last execution result: {self.lastExecutionResult}', 'magenta')}")
        # ### BEGIN 2023-05-23 22:39:22 do not delete
        #
        # 3.1. establish which variables have been removed ⇒ del_vars
        #
        # symbols present in the namespace
        current_user_varnames = set(ns.keys())
        # varnames that are currently monitored
        observed_varnames = set(self.internalVariablesMonitor.keys())
        # varnames that have been removed
        del_vars = observed_varnames - current_user_varnames

        # print(f"{print_styled(f'\n{self.__class__.__name__}._updateModel_ del_vars = {del_vars}', 'magenta')}")

        # 3.2. now, remove these from the DataBag of observed variables (self.internalVariablesMonitor)
        #
        # NOTE: 2023-05-24 16:18:58
        # The DataBag will NOW notify any observers upon the removal of these variables
        # Works OK
        self.internalVariablesMonitor.delete(*list(del_vars))

        #
        # 3.3. now, figure out whether there are NEW variables added to the workspace
        # Their names are present in the workspace, but ABSENT in the DataBag of
        # observed variables.
        #

        # current_vars = dict([item for item in self.shell.user_ns.items() if not item[0].startswith("_") and self.isDisplayable(item[0], item[1])])
        current_vars = dict([item for item in ns.items() if not item[0].startswith(
            "_") and self.isDisplayable(ns, *item)])

        # print(f"{self.__class__.__name__}._updateModel_ current_vars = {current_vars}")

        # NOTE: 2023-05-24 16:22:58
        # this SHOULD also notify the observers - Works OK when adding new symbols
        # does not work when an object bound to an existing symbol has been modified
        # (i.e., either the symbols is bound to a different object reference, or
        # the contents of the object - e.g. a container - have changed)
        #
        # see NOTE: 2025-06-28 23:17:33 in core.scipyen_traitlets
        #
        self.internalVariablesMonitor.update(current_vars)

        # NOTE 2023-05-25 18:13:46
        # Changes of object attributes or data the object are NOT detected by this approach
        # (see TODO/FIXME 2023-05-25 18:12:56 in core/scipyen_traitlets.py)
        # ### END 2023-05-23 22:39:22 do not delete

        # NOTE: 2023-06-01 08:16:13
        # see NOTE: 2023-06-01 08:14:33
        # try:
        #     self.internalVariableChanged.disconnect(self._slot_cacheInternalVariableChange_)
        # except:
        #     traceback.print_exc()
        # self.internalVariableChanged.connect(self._slot_internalVariableChanged_)

        # NOTE: 2023-06-05 20:59:00
        # connected to self._slot_updateModelAsync_
        self.sig_startAsyncUpdate.emit(self.shell.user_ns)

        self.lastExecutionResult = None

        # NOTE: 2023-05-28 01:31:53
        # the next two signal a change directory command issued at the console
        current_dir = os.getcwd()
        if current_dir != self.currentDir:
            self.currentDir = current_dir
            self.workingDir.emit(current_dir)

        # NOTE: 2023-11-04 17:53:24
        # update internal caches
        # self.cached_vars = dict([item for item in self.shell.user_ns.items(
        # ) if self.isDisplayable(self.shell.user_ns, *item)])
        # self.gcf_figs.clear()
        # self.gcf_figs.update(
        #     fig_manager.canvas.figure for fig_manager in Gcf.figs.values())

    @Slot(str)
    def _slot_itemGuiObjectTitleChanged(self, val:str):
        r"""For dynamic update of 1st line of tooltip of items representing a QWidget"""
        obj = self.sender()
        if __has_PySide6__:
            if not isinstance(obj, (QtWidgets.QWidget,Shiboken.Object)):
                return
        else:
            if not isinstance(obj, QtWidgets.QWidget):
                return

        # print(f"{self.__class__.__name__}._slot_itemGuiObjectTitleChanged obj: {obj}, str: {val}")

        item = self.getItemForObject(obj)

        if not isinstance(item, QtGui.QStandardItem):
            return


        ttip = item.toolTip()

        wtitle = f"Window: {obj.windowTitle()}"

        # print(f"{self.__class__.__name__}._slot_itemGuiObjectTitleChanged item ttip: {ttip}, wtitle: {wtitle}")

        components = ttip.split("\n")
        if components[0].startswith("Window:"):
            components[0] = wtitle
        else:
            components.insert(0, wtitle)
        wspace_name = components[-1]
        w = max(get_text_width(wtitle) * 2, get_text_width(wspace_name) * 2)
        # w = get_text_width(wspace_name) * 2
        tooltip = "\n".join(components)
        ttip = "\n".join([get_elided_text(s, w)
                            for s in components[:-1]] + [wspace_name])

        # print(f"{self.__class__.__name__}._slot_itemGuiObjectTitleChanged item toolTip: {tooltip}, ttip: {ttip}")
        # return

        # NOTE: 2023-09-16 18:31:13
        # block self from emitting itemChanged (triggered whenever some item has
        # changed), to prevent symbol mangling in the workspace
        signalBlocker = QtCore.QSignalBlocker(self)

        item.setToolTip(ttip)
        item.setStatusTip(tooltip)
        item.setWhatsThis(tooltip)

    def _generateModelItemForObject_(self, propdict: dict,
                                     icon: typing.Optional[QtGui.QIcon] = None,
                                     editable: typing.Optional[bool] = False,
                                     elidetip: typing.Optional[bool] = False,
                                     background: typing.Optional[QtGui.QBrush] = None,
                                     foreground: typing.Optional[QtGui.QBrush] = None) -> QtGui.QStandardItem:
        # print(f"_generateModelItemForObject_ propdict = {propdict}")
        item = QtGui.QStandardItem(propdict["display"])

        ttip = propdict["tooltip"]
        # NOTE: 2021-07-19 11:06:48
        # optionally use elided text for long tooltips
        if elidetip:
            components = ttip.split("\n")
            wspace_name = components[-1]
            w = get_text_width(wspace_name) * 2
            ttip = "\n".join([get_elided_text(s, w)
                             for s in components[:-1]] + [wspace_name])

        item.setToolTip(ttip)
        item.setStatusTip(propdict["tooltip"])
        item.setWhatsThis(propdict["tooltip"])
        item.setEditable(editable)

        if isinstance(background, QtGui.QBrush):
            item.setBackground(background)

        if isinstance(foreground, QtGui.QBrush):
            item.setForeground(foreground)

        item.setData(self._displayFont, QtCore.Qt.FontRole)

        return item

    def _updateItemsFont(self):
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                self.item(row, col).setData(self._displayFont, QtCore.Qt.FontRole)

    @safewrapper
    def generateRowContents(self, dataname: str,
                            data: object,
                            namespace: str = "Internal"):
        # print(f"{self.__class__.__name__}.generateRowContents(dataname={dataname})")
        obj_props = summarize_object_properties(dataname, data, namespace=namespace)
        return self.genRowFromPropDict(obj_props)

    def genRowFromPropDict(self, obj_props: dict,
                           background: typing.Optional[QtGui.QBrush] = None,
                           foreground: typing.Optional[QtGui.QBrush] = None) -> typing.List[QtGui.QStandardItem]:
        r"""Returns a row of QStandardItems
        """
        # print(f"genRowFromPropDict obj_props = {obj_props}")
        # print(f"{self.__class__.__name__}.genRowFromPropDict:\n-> Object Type: {obj_props['Object Type']['display']}")
        # headers = [k for k in standard_obj_summary_headers if k != "Icon"]
        ret = [self._generateModelItemForObject_(obj_props[key],
                                                  editable=(key == "Name"),
                                                  elidetip=(key == "Name"),
                                                  background=background,
                                                  foreground=foreground) for key in self._wspace_headers_]
        icon = obj_props.get("Icon", None)
        if isinstance(icon, QtGui.QIcon):
            # print(f"{self.__class__.__name__}.genRowFromPropDict icon = {icon.name()}")
            ret[0].setData(icon, QtCore.Qt.DecorationRole)

        return ret

    def getRowContents(self, row, asStrings=True):
        '''
        Returns a list of QStandardItem (or their display text, if strings is True)
        for the given row.
        If row index is not valid, returns the empty string (if strings is True)
        or None
        '''

        if row is None or row >= self.rowCount() or row < 0:
            return "" if asStrings else None

        return [self.item(row, col).text() if asStrings else self.item(row, col) for col in range(self.columnCount())]

    def getItemForObject(self, obj):
        r"""Returns a model item for the object.
        If the object is not currrently in the workspace will return None.
        Only works for displayed (and displayable) variables.
        """
        # FIXME: 2025-09-28 20:48:49 TODO - do this for external (foreign) namespaces also
        names_objs = list((n,o) for n,o in self.shell.user_ns.items() if o is obj)

        if len(names_objs) == 0:
            return

        name, o = names_objs[0]

        ndx = self.getRowIndexForVarname(name)

        if isinstance(ndx, int):
            return self.item(ndx, 0)

    def getRowIndexForVarname(self, varname, regVarNames=None):
        r"""Returns the row index for the variable symbol 'varname'

        Parameters:
        ==========

        varname: str; a symbol in the user namespace (get_ipython().user_ns)

        regVarNames: list of str or None (default); a list of symbols;

            When None, (default ) then 'varname' is looked up in the list of
            the symbol currently shown in the "User Variables" tab of the
            Scipyen's main window.

            In this case, this function simply returns the row index in the
            workspace model


        """
        if regVarNames is None:
            regVarNames = self.getDisplayedVariableNames()

        ndx = None

        if len(regVarNames) == 0:
            return ndx

        if varname in regVarNames:
            ndx = regVarNames.index(varname)

        return ndx

    def getVarName(self, index: QtCore.QModelIndex):
        r"""Returns the symbol of a variable in this model, for a given model index.

        Returns none it if the symbol does not exist in the user workspace
        """
        v = self.item(index.row(), 0).text()

        return v if v in self.shell.user_ns else None  # <- FIXME: 2025-09-28 20:47:43 this is the internal workspace; TODO fix this for external namespaces also

    @Slot(dict, str, str)
    def variableModified(self, ns:dict, dataname:str, ns_name:str="Internal"):
        # print(f"{self.__class__.__name__}.variableModified(dataname={dataname}, ns_name={ns_name})")
        self.updateRowForVariable2(ns, dataname, ns_name)
        self.refreshDataViewers(ns, dataname, ns_name)


    def refreshDataViewers(self, ns:dict, dataname:str, ns_name:str = "Internal", exclude:typing.Optional[typing.Sequence[QtWidgets.QWidget]] = None):
        from gui.scipyenviewer import ScipyenViewer
        if dataname in ns:
            data = ns[dataname]
            showsData = lambda x: id(data) in [id(v) for v in x.data] if isinstance(x.data,typing.Sequence) else id(data) == id(x.data)
            viewers = list(filter(showsData, filter(lambda x: isinstance(x, ScipyenViewer), ns.values())))
            if isinstance(exclude, typing.Sequence) and all(isinstance(e, ScipyenViewer) for e in exclude):
                viewers = list(filter(lambda x: x not in exclude, viewers))
            for viewer in viewers:
                viewer.slot_refreshDataDisplay()

    @Slot(dict, str, str)
    def updateRowForVariable2(self, ns: dict, dataname: str, ns_name:str = "Internal"):
        # CAUTION This is only for internal workspace, but
        # TODO 2020-07-30 22:18:35 merge & factor code for both internal and foreign
        # kernels (make use of the ns parameter)
        #
        # print(f"{print_styled(f'{self.__class__.__name__}.updateRowForVariable2 dataname = {dataname}, ns_name={ns_name}, sender: {self.sender()}', color='green')}")
        if dataname not in ns:
            return

        if dataname not in self.getDisplayedVariableNames(asStrings=True, ws=ns_name):
            self.addRowForVariable2(ns, dataname, ns_name)
            return

        data = ns[dataname]

        # NOTE: 2025-07-06 14:05:36
        # row indices for items in the given workspace - Do NOT DELETE - useful later when implementing this for foreign namespaces
        internalWSRows = self.rowIndexForItemsWithProps(Workspace=ns_name)
        if isinstance(internalWSRows, int):
            internalWSRows = [internalWSRows]

        # print(f"{print_styled(f'\trow = {internalWSRows}', color='green')}")
        # print("updateRowForVariable2, internalWSRows:", internalWSRows)

        items = self.findItems(dataname)

        if len(items) > 0:
            item_row = self.indexFromItem(items[0]).row()  # same as below

            # NOTE: 2025-07-06 14:10:10
            ## for now, restrict to internal workspace
            if item_row not in internalWSRows:
                return
            # print(f"{print_styled(f'\titem_row = {item_row}', color='green')}")
            # generate new contents for model view row for the existing item
            row_contents = self.generateRowContents(dataname, data)

            # NOTE: 2025-07-06 15:00:17
            # workaround to avoid triggering mainWindow.slot_variableItemNameChanged
            # due to model's itemChange signal, when the only  changes are at most
            # in the contents of the variable bound to dataname, and not to dataname itself

            self.itemChanged.disconnect(self.parent().slot_variableItemNameChanged)
            self.updateRow(item_row, row_contents)

            # BUG: 2023-09-16 09:55:11
            # this causes a rename to the variables, which shouldn't happen; the
            # BUG is subtle and related to how the variables are assigned to symbols
            # in the workspace - clearly a flaw in how I designed all of this...
            if isinstance(data, QtWidgets.QWidget):
                data.windowTitleChanged.connect(self._slot_itemGuiObjectTitleChanged)

            self.itemChanged.connect(self.parent().slot_variableItemNameChanged)

    def updateRowFromProps(self, row, obj_props, background=None):
        r"""
        Parameters:
        row = int
        obj_props: dict, see generateRowContents
        """
        if background is None:
            v_row = self.genRowFromPropDict(obj_props)

        else:
            v_row = self.genRowFromPropDict(obj_props, background=background)

        self.updateRow(row, v_row)

    def updateRow(self, rowindex, newrowdata):
        # print(f"{self.__class__.__name__}.updateRow(rowindex = {rowindex}, newrowdata = {newrowdata})")
        originalRow = self.getRowContents(rowindex, asStrings=False)
        # print("updateRow originalRow as str", self.getRowContents(rowindex, asStrings=True))
        if originalRow is not None:
            # NOTE: 2024-01-26 10:04:48 update decoration data (icon)
            original_item0_icon = self.item(rowindex, 0).data(QtCore.Qt.DecorationRole)
            new_item0_icon = newrowdata[0].data(QtCore.Qt.DecorationRole)

            if isinstance(original_item0_icon, QtGui.QIcon):
                if isinstance(new_item0_icon, QtGui.QIcon):
                    if new_item0_icon != original_item0_icon:
                        self.item(rowindex, 0).setData(new_item0_icon, QtCore.Qt.DecorationRole)
                else:
                    self.item(rowindex, 0).setData(None, QtCore.Qt.DecorationRole)

            else:
                if isinstance(new_item0_icon, QtGui.QIcon):
                    self.item(rowindex, 0).setData(new_item0_icon, QtCore.Qt.DecorationRole)


            for col in range(1, self.columnCount()):
                # NOTE: 2021-07-28 10:42:17
                # ATTENTION this emits itemChanged signal thereby will trigger
                # code for displayed name change
                self.setItem(rowindex, col, newrowdata[col])

    @Slot(dict, str, str)
    def removeRowForVariable2(self, ns: dict, dataname: str, ns_name: str = "Internal"):

        # print(f"{self.__class__.__name__}.removeRowForVariable2 dataname = {dataname}, ns_name={ns_name}")
        row = self.rowIndexForItemsWithProps(Name=dataname, Workspace=ns_name)

        # data = self.shell.user_ns.get(dataname, None)
        data = ns.get(dataname, None)

        if isinstance(data, QtWidgets.QWidget):
            data.windowTitleChanged.disconnect()

        if row == -1:
            return

        if isinstance(row, list):
            for r in row:
                self.removeRow(r)

        else:
            self.removeRow(row)

    # def addRowForVariable(self, dataname, data):
    #     r"""CAUTION Only use for data in the internal workspace, not in remote ones.
    #     """
    #     # print("addRowForVariable: ", dataname, data)
    #     # generate model view row contents
    #     v_row = self.generateRowContents(dataname, data)
    #     self.appendRow(v_row)  # append the row to the model

    @Slot(dict, str, str)
    def addRowForVariable2(self, ns: dict, dataname: str, ns_name: str = "Internal"):
        r"""CAUTION Only use for data in the internal workspace, not in remote ones.
        """
        # print(f"{print_styled(f'\n{self.__class__.__name__}.addRowForVariable2 for {dataname}', color='green')}")
        # if isinstance(ns_name, str):
        #     if len(ns_name.strip()) == 0:
        #         ns_name = "Internal"
        #
        # else:
        #     ns_name = "Internal"

        if dataname not in ns:
            return


        data = ns[dataname]
        # print(f"{self.__class__.__name__}.addRowForVariable2 dataname = {dataname}, ns_name={ns_name}")

        # generate model view row contents
        v_row = self.generateRowContents(dataname, data)
        # BUG: 2023-09-16 09:55:11
        # this causes a rename to the variables, which shouldn't happen; the
        # BUG is subtle and related to how the variables are assigned to symbols
        # in the workspace - clearly a flaw in how I designed all of this...
        if isinstance(data, QtWidgets.QWidget):
            data.windowTitleChanged.connect(self._slot_itemGuiObjectTitleChanged)
        self.appendRow(v_row)  # append the row to the model

    def mimeData(self, indexes: typing.Sequence[QtCore.QModelIndex]) -> QtCore.QMimeData:
        import pickle
        from iolib import jsonio
        from core import strutils
        mData = super().mimeData(indexes)

        if len(indexes):
            wscol = list(map(lambda c: self.headerData(c, QtCore.Qt.Horizontal),
                               range(self.columnCount()))).index("Workspace")

            items = list(map(lambda i: self.item(i.row(), 0), indexes))

            varnames = list(filter(lambda t: t in self.shell.user_ns,
                                    map(lambda i: i.data(QtCore.Qt.DisplayRole),
                                        filter(lambda i: self.item(i.row(), wscol).text() == "Internal",
                                                items)
                                        )
                                    )
                            )

            if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
                varnames = list(map(lambda s: f'"{s}"', varnames))

            if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier):
                data = ",\n".join(varnames)
            else:
                data = ", ".join(varnames)

            mData.setText(data)

            # ### BEGIN 2026-04-24 22:23:57 DO NOT DELETE
            # objects = list(map(lambda v: (v, self.shell.user_ns[v]), varnames))
            #
            # objs = dict(zip(varnames, objects))
            #
            # # objs = dict(map(lambda v: (v, self.shell.user_ns[v]),
            # #                 list(filter(lambda t: t in self.shell.user_ns,
            # #                             map(lambda i: i.text(),
            # #                                 filter(lambda i: self.workspaceModel.item(i.row(), wscol).text() == "Internal",
            # #                                         items))))
            # #                 )
            # #             )
            #
            # if len(varnames) == 1:
            #     obj = objs[varnames[0]]
            #
            #     if isinstance(obj, (QtWidgets.QWidget, mpl.figure.Figure)):
            #         return mData
            #
            #     elif isinstance(obj, QtGui.QPixmap):
            #         data = obj.toImage()
            #         mData = QtCore.QMimeData()
            #         mData.setImageData(data)
            #
            #     elif isinstance(obj, QtGui.QImage):
            #         data = objs[varnames[0]]
            #         mData = QtCore.QMimeData()
            #         mData.setImageData(data)
            #
            #     elif isinstance(obj, str):
            #         mData = QtCore.QMimeData()
            #         if strutils.is_html(obj):
            #             mData.setHtml(data)
            #
            #         elif strutils.is_latex(obj):
            #             data = strutils.render_latex(obj, out="bytes")
            #             mData.setImageData(data)
            #
            #         else:
            #             mData.setText(obj)
            #
            #     else:
            #         mData = QtCore.QMimeData()
            #         data = pickle.dumps(obj)
            #         mData.setData("application/octet-stream", data)
            #         # try:
            #         #     data = jsonio.dumps(obj)
            #         #     mData.setData("application/json", data)
            #         # except:
            #         #     data = pickle.dumps(obj)
            #         #     mData.setData("application/octet-stream", data)
            #
            # elif len(varnames) > 1:
            #     oo = dict(map(filter(lambda i: not isinstance(i[1], (QtWidgets.QWidget, mpl.figure.Figure)),
            #                          objs.items()
            #                          )
            #                   )
            #               )
            #
            #     if len(oo):
            #         mData = QtCore.QMimeData()
            #         try:
            #             data = jsonio.dumps(oo)
            #             mData.setData("application/json", data)
            #         except:
            #             data = pickle.dumps(oo)
            #             mData.setData("application/octet-stream", data)
            # ### END   2026-04-24 22:23:57 DO NOT DELETE



        return mData


    def clearTable(self):
        self.removeRows(0, self.rowCount())

#     def update_old(self):
#         r"""Updates workspace model.
#         To be called by code that adds/remove/modifies/renames variables
#         in the Scipyen's namespace in order to update the workspace viewer.
#
#         WARNING: This function should NOT be used for normal operation: changes
#         in the workspace contents are monitored by the internal variable monitor
#         which triggers Ui updates already.
#
#         """
#
#         # currently displayed variables in the viewer widget
#         displayed_var_names = set(self.getDisplayedVariableNames())
#
#         # current variable names in the namespace, which should be available to
#         # the user - this ain't faster
#         current_vars = dict(filter(lambda x: not x[0].startswith("_") and self.isDisplayable(*x), self.shell.user_ns.items()))
#
#         # names of variables in user namespace
#         current_user_varnames = set(current_vars.keys())
#         # current_user_varnames = set(self.shell.user_ns.keys())
#
#         # names of variables present in the internalVariablesMonitor DataBag
#         observed_varnames = set(self.internalVariablesMonitor.keys())
#
#         # names still in internalVariablesMonitor but not in user namespace anymore
#         del_vars = observed_varnames - current_user_varnames
#
#         # current variable names in the namespace, which should be available to
#         # the user - CAUTION this scales with 𝒪(n) !
#         # current_vars = dict([item for item in self.shell.user_ns.items(
#         # ) if not item[0].startswith("_") and self.isDisplayable(item[0], item[1])])
#
#         self.internalVariablesMonitor.delete(*list(del_vars))
#
#         self.internalVariablesMonitor.update(current_vars)

    def update(self):
        r"""Updates workspace model - batch version.
        Used when the namespace contents are modified by code run OUTSIDE the
        console (hence, independently of the console's kernel events)

        WARNING: This function is for batch operations and should NOT be used for
        normal operation: changes in the workspace contents are monitored by the
        internal variable monitor which triggers Ui updates already.

        """
#         print(f"{self.__class__.__name__}.update: _first_run_: {self._first_run_}")
#         if self._first_run_:
#             self._first_run_ = False
#             return
#
        # currently displayed variables in the viewer widget
        displayed_var_names = set(self.getDisplayedVariableNames())

        # current variable names in the namespace, which should be available to
        # the user - is this faster?
        current_vars = dict(filter(lambda x: not x[0].startswith("_") and self.isDisplayable(self.shell.user_ns, *x), self.shell.user_ns.items()))

        # names of variables in user namespace
        current_user_varnames = set(current_vars.keys())
        # current_user_varnames = set(self.shell.user_ns.keys())

        # names of variables present in the internalVariablesMonitor DataBag
        observed_varnames = set(self.internalVariablesMonitor.keys())

        # names still in internalVariablesMonitor but not in user namespace anymore
        del_vars = observed_varnames - current_user_varnames
        # print(f"{self.__class__.__name__}.updateModel del_vars = {del_vars}")

        # current variable names in the namespace, which should be available to
        # the user - CAUTION this scales with 𝒪(n) !
        # current_vars = dict([item for item in self.shell.user_ns.items(
        # ) if not item[0].startswith("_") and self.isDisplayable(item[0], item[1])])

        new_vars = dict(filter(lambda x: not x[0] in displayed_var_names, current_vars.items()))

        mod_vars = dict(filter(lambda x: x[0] in displayed_var_names, current_vars.items()))

        self.internalVariablesMonitor.delete(*list(del_vars)) # -> WorkspaceVarChange.Removed
        self.internalVariablesMonitor.update(current_vars) # -> WorkspaceVarChange.New or WorkspaceVarChange.Modified

        # try:
        #     self.internalVariableChanged.disconnect(self._slot_cacheInternalVariableChange_)
        # except:
        #     traceback.print_exc()
        # self.internalVariableChanged.connect(self._slot_internalVariableChanged_)

        self.sig_startAsyncUpdate.emit(self.shell.user_ns)

        # ATTENTION: 2023-05-28 22:42:12
        # When unobserve/observe will access methods of self from another thread
        # they will cause a segfault - Do NOT use this.
        # self.internalVariablesMonitor.unobserve(self.internalVariablesListenerCB)
        # self.internalVariablesMonitor.remove_members(*list(del_vars))
        # self.internalVariablesMonitor.update(current_vars)
        # self.internalVariablesMonitor.observe(self.internalVariablesListenerCB)

        # NOTE: 2023-05-28 22:26:43
        # this holds notification until AFTER ALL traits have been set
        # (which happens upon call to self.internalVariablesMonitor.update)
        # but it will still BLOCK the UI!
        # Furthermore, I think self.internalVariablesMonitor.remove_members still
        # # notifies?
        # with self.internalVariablesMonitor.observer.hold_trait_notifications():
        #     self.internalVariablesMonitor.remove_members(*list(del_vars))
        #     self.internalVariablesMonitor.update(current_vars)


    @Slot(dict)
    def _slot_updateModelAsync_(self, namespace:dict):
        r"""Triggered by self.sig_startAsyncUpdate signal.
        The signal 'self.sig_startAsyncUpdate' is emitted by self.update() and self._updateModel_()
        """
        # print(f"{print_styled(f'\n{self.__class__.__name__}._slot_updateModelAsync_ -> self.__changes__ = {self.__changes__}', color='green')}")
        if len(self.__changes__) == 0:
            return

        removals = list(filter(lambda x: x[1] == WorkspaceVarChange.Removed, self.__changes__.items()))
        additions = list(filter(lambda x: x[1] == WorkspaceVarChange.New, self.__changes__.items()))
        modifications = list(filter(lambda x: x[1] == WorkspaceVarChange.Modified, self.__changes__.items()))

        # print(f"\n{self.__class__.__name__}._slot_updateModelAsync_: {len(modifications)} modifications")
        # if len(modifications):
        #     for modification in modifications:
        #         print(f"{modification}")

        # NOTE: 2025-07-06 10:54:42
        # invoke the callbacks in THIS order
        for item in removals:
            self._varChanges_callbacks_[item[1]](item[0])

        for item in additions:
            self._varChanges_callbacks_[item[1]](item[0])

        for item in modifications:
            self._varChanges_callbacks_[item[1]](item[0])

        self.__changes__.clear()
        self.modelContentsChanged.emit()

    def updateFromExternal(self, prop_dicts):
        r"""prop_dicts: {name: nested properties dict}
            nested properties dict: {property: {"display": str, "tooltip":str}}
                property: one of
                    ['Name', 'Type', 'Data_Type', 'Minimum', 'Maximum', 'Size',
                    'Dimensions','Shape', 'Axes', 'Array_Order', 'Memory_Size',
                    'Workspace']

                display: the displayed text
                tooltip: tooltip text
        """
        for varname, props in prop_dicts.items():
            ns_key = props["Workspace"]["display"]
            internal_ns_key = ns_key.replace(" " , "_")

            vname = varname.replace("properties_of_", "")

            namespaces = sorted([k for k in self.foreign_namespaces.keys()])

            if internal_ns_key not in namespaces:
                continue  # FIXME 2020-07-30 22:42:16 should NEVER happen

            items_row_ndx = self.rowIndexForNamedItemsWithProps(
                vname, Workspace=ns_key)

            if items_row_ndx is None:
                row = self.genRowFromPropDict(props)
                self.appendRow(row)

            elif isinstance(items_row_ndx, int):
                if items_row_ndx == -1:
                    row = self.genRowFromPropDict(props)
                    self.appendRow(row)

                else:
                    self.updateRowFromProps(items_row_ndx, props)

            elif isinstance(items_row_ndx, (tuple, list)):
                if len(items_row_ndx) == 0:
                    row = self.genRowFromPropDict(props)
                    self.appendRow(row)

                else:
                    for r in items_row_ndx:
                        if r == -1:
                            row = self.genRowFromPropDict()
                            self.appendRow(row)

                        else:
                            self.updateRowFromProps(r, props)

    @safewrapper
    def rowIndexForItemsWithProps(self, **kwargs):
        r"""Returns row indices for all items that satisfy specified properties.

        Parameters:
        ----------
        **kwargs: key/value mapping, where:

            Key is one of (case-sensitive)
                ['Name', 'Type', 'Data_Type', 'Minimum', 'Maximum', 'Size',
                'Dimensions','Shape', 'Axes', 'Array_Order', 'Memory_Size',
                'Workspace']

            Value is the text displayed in the workspace table in the column with
            the header given by the "key"

            NOTE: Spaces in column header texts should be replaced by underscores
            in the key (to conform with Python identifier syntax); the function
            perform the inverse substitution (form underscored to space character).

        Returns:
        --------
        a list of row indices (0-based) or one integer >=0 if only one
        item was found , or -1 if no item was found (Qt way)

        If kwargs are not specified, then returns range(self.rowCount())

        """
        # from core.utilities import standard_obj_summary_headers

        if len(kwargs) == 0:
            # return all row indices here
            # if used from a deleting function, this should result in the removal
            # of all items in the model
            return range(self.rowCount())

        else:
            if self.rowCount() == 0:
                return -1

            # auxiliary vector for setting up logical indexing, see for loop below
            allrows = np.arange(self.rowCount())

            # set up logical indexing vector
            allndx = np.array([True] * self.rowCount())

            # NOTE: 2022-10-28 13:41:36
            # kwargs keys are column names in the workspace viewer (but with " "
            #   replaced by "_")
            # so, below, for each of the column names GIVEN in kwargs:
            for key, value in kwargs.items():
                # find the column's index  - this is the index of the column name
                # in the summary header
                key_column = standard_obj_summary_headers.index(key.replace("_", " "))
                # now, find the viewer item based on the value mapped to the kwarg
                # key, given the index of the key column; the value must be a str
                # NOTE: findItems is a method of QAbstractItemModel
                items_by_key = self.findItems(value, column=key_column)

                # once items are found, we get their row indices
                rows_by_key = [i.index().row() for i in items_by_key]

                # key_ndx is an intermediate logical vector flagging True wherever
                # a row index from the current model contents is in rows_by_key
                key_ndx = np.array(
                    [allrows[k] in rows_by_key for k in range(len(allrows))])

                # update the logical vector
                allndx = allndx & key_ndx

            # use the logial indexing to create a list of row indices
            ret = [int(v) for v in allrows[allndx]]
            # print("rowIndexForItemsWithProps ret", ret)
            # ret = list(allrows[allndx])

            if len(ret) == 1:
                return ret[0]

            elif len(ret) == 0:
                return -1

            else:
                return ret

    @safewrapper
    def rowIndexForItemInWorkspace(self, name, Workspace="internal"):
        r"""Variant of rowIndexForItemsWithProps selecting row indices for variables
            in the internal workspace

        Accepts a list of names !

        TODO!
        """

        pass

    @safewrapper
    def rowIndexForNamedItemsWithProps(self, name, **kwargs):
        r"""Find the item named with "name" and optional property values

        Parameters:
        -----------
        name: displayed name in column 0

        **kwargs: mapping of key/value pairs, optional (default empty) for
                filtering the results

            each key is a property name, one of

            ['Type', 'Data_Type', 'Minimum', 'Maximum', 'Size', 'Dimensions',
             'Shape', 'Axes', 'Array_Order', 'Memory_Size', 'Workspace']

            and the value is as displayed in their corresponding columns

            NOTE: Spaces in column header texts should be replaced by underscores
            in the key (to conform with Python identifier syntax); the function
            perform the inverse substitution (form underscored to space character).

        Return the row index of the item, if found, or -1 if not found (Qt way).

        When several items are found, returns a list with their row indices.

        Technically, several items with the same name can exist in the table
        ONLY if their "Workspace" property is different.

        No two variables in the same workspace can be bound to the same identifier
        hence all "Name" items for the data in a given workspace should be unique.

        """
        # from core.utilities import standard_obj_summary_headers
        name_column = standard_obj_summary_headers.index("Name")

        kwargs.pop("Name", None)  # make sure we don't index by name twice

        allrows = np.arange(self.rowCount())
        allndx = np.array([True] * self.rowCount())

        items_by_name = self.findItems(name, column=name_column)
        rows_by_name = [i.index().row()
                        for i in items_by_name]  # empty if items is empty

        if len(kwargs) == 0:  # find by name
            if len(items_by_name) > 1:
                return rows_by_name

            elif len(items_by_name) == 1:
                return rows_by_name[0]

            else:  # not found
                return -1

        else:
            if len(rows_by_name):
                name_ndx = np.array(
                    [allrows[k] in rows_by_name for k in range(len(allrows))])

                allndx = allndx & name_ndx

                for key, value in kwargs.items():
                    key_column = standard_obj_summary_headers.index(
                        key.replace("_", " "))

                    items_by_key = self.findItems(value, column=key_column)
                    rows_by_key = [i.index().row() for i in items_by_key]

                    key_ndx = np.array(
                        [allrows[k] in rows_by_key for k in range(len(allrows))])

                    allndx = allndx & key_ndx

                ret = [int(v) for v in allrows[allndx]]
                # ret = list(allrows[allndx])

                if len(ret) == 1:
                    return ret[0]

                elif len(ret) == 0:
                    return -1

                else:
                    return ret

            else:
                return -1

    def getDisplayedVariableNamesAndTypes(self, ws="Internal"):
        r"""Returns a mapping of displayed variable names to their type names (as string).

        Parameters:
        -----------
        ws: str (optional, default is "Internal")

        """
        if not isinstance(ws, str):
            ws = "Internal"

        wscol = standard_obj_summary_headers.index("Workspace")
        typecol = standard_obj_summary_headers.index("Object Type")

        ret = dict([(self.item(row, 0).text(), self.item(row, typecol).text()) for row in range(
            self.rowCount()) if self.item(row, wscol) is not None and self.item(row, wscol).text() == ws])

        return ret

    def getDisplayedVariableTypes(self, asStrings=True, ws="Internal"):
        r"""Returns the DISPLAYED type of the variables.

        CAUTION: These may be different from the name of the actual type of
        the variable, in the user_ns.

        Parameters:
        -----------
        asStrings: bool (optional, default True)
            When True variable names are returned as (a Python list of) strings,
            otherwise they are returned as Python list of QStandardItems

        ws: str (optional, default is "Internal")

        """
        if not isinstance(ws, str):
            ws = "Internal"

        wscol = standard_obj_summary_headers.index("Workspace")
        typecol = standard_obj_summary_headers.index("Object Type")

        ret = [self.item(row, typecol).text() if asStrings else self.item(
            row, typecol) for row in range(self.rowCount()) if self.item(row, wscol).text() == ws]

        return ret

    def getDisplayableVarnamesForVar(self, ns:dict, value:typing.Any) -> list:
        varnames = reverse_mapping_lookup(ns, value)

        if isinstance(varnames, (tuple, list)) and all(isinstance(v, str) for v in varnames):
            return list(filter(lambda x: self.isDisplayable(ns, x, value), varnames))

        if isinstance(varnames, str) and self.isDisplayable(ns, varnames, value):
            return [varnames]

        return []


    def getDisplayedVariableNames(self, asStrings=True, ws="Internal") -> typing.List[str|QtGui.QStandardItem]:
        '''Returns names of variables in the specified workspace, registered with the model.

        Parameter: asStrings (boolean, optional, default True) variable names
                    are returned as (a Python list of) strings.
                    When False, returned a Python list of QStandardItems
        '''
        wscol = standard_obj_summary_headers.index("Workspace")
        ret = [self.item(row,0).text() if asStrings else self.item(row,0) for row in range(
            self.rowCount()) if self.item(row, wscol).text().lower() == ws.lower()]

        return ret

    def getNumberOfDisplayedForeignKernels(self):
        return len(self.getDisplayedWorkspaces(foreign_only=True))

    def getDisplayedWorkspaces(self, foreign_only=False):
        r"""Returns a set with the names of the workspaces shown.
        """
        wcsol = standard_obj_summary_headers.index("Workspace")
        workspaces = set()
        for row in range(self.rowCount()):
            wsname = self.item(row, wscol).text()
            if foreign_only and wsname == "Internal":
                continue

            workspaces.add(wsname)

        return workspaces

    def getBinding(self, obj:typing.Any, ns_name="internal") -> str|None:
        r"""Retrieve the symbol that an object is bound to, in the specified namespace.
        Returns None is the object is not found in the namespace
    """
        if ns_name.lower() == "internal":
            items = list(filter(lambda x: id(obj) == id(x[1]), self.shell.user_ns.items()))
            # print(f"{self.__class__.__name__}.getBinding -> {len(items)} items")
            if len(items):
                varNames = self.getDisplayedVariableNames(asStrings=True, ws = ns_name)
                # print(f"\tvarNames -> {varNames}")
                items = list(filter(lambda x: x[0] in varNames, items)) # only select those objects that are listed (displayed) in the model
                # print(f"among varNames -> {len(items)} items")
                if len(items) > 1:
                    scipywarn("More than one symbols appear to be bound to the object; will return the first one")
                return items[0][0] if len(items) else None
        else:
            scipywarn("This method only supports the internal namespace, for now...")

