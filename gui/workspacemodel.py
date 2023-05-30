# -*- coding: utf-8 -*-
"""
The workspace model - also used by the internal shell, to which ii provides the
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
import contextlib
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
import json

from traitlets import Bunch

from .guiutils import (get_text_width, get_elided_text)
from gui import pictgui as pgui
from core.traitcontainers import DataBag
from core.utilities import (summarize_object_properties,
                            standard_obj_summary_headers,
                            safe_identity_test,
                            )
from core.prog import (safeWrapper, timefunc, processtimefunc, timeblock)
from core.datatypes import TypeEnum
# from jupyter_core.paths import jupyter_runtime_dir

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot

mpl.use("Qt5Agg")


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
    modelContentsChanged = pyqtSignal(name="modelContentsChanged")
    workingDir = pyqtSignal(str, name="workingDir")
    internalVariableChanged = pyqtSignal(dict, name="internalVariableChanged")
    varModified = pyqtSignal(object, name="varModified")
    sig_startAsyncUpdate = pyqtSignal(dict, name="sig_startAsyncUpdate")

    def __init__(self, shell, user_ns_hidden=dict(),
                 parent=None,
                 mpl_figure_close_callback=None,
                 mpl_figure_click_callback=None,
                 mpl_figure_enter_callback=None):
        # make sure parent is passed from ScipyenWindow as an instance of ScipyenWindow
        super(WorkspaceModel, self).__init__(parent)

        self.threadpool = QtCore.QThreadPool()

        # self.loop = asyncio.get_event_loop()
        # NOTE: 2023-05-27 21:58:23
        # reference to IPython InteractiveShell of the internal console; 
        # WARNING: this is also a reference to the "workspace" attribute of the 
        # ScipyenWindow instance
        self.shell = shell  

        self.cached_vars = dict()
        self.modified_vars = dict()
        self.new_vars = dict()
        self.deleted_vars = dict()
        self.user_ns_hidden = dict(user_ns_hidden)
        self.mpl_figs = dict()

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

        self.internalVariablesMonitor = DataBag(allow_none=True, mutable_types=True)
        self.internalVariablesMonitor.verbose = True
        self.internalVariablesMonitor.observe(self.internalVariablesListenerCB)
        # self.internalVariablesMonitor.observe(self._slot_internalVariableChanged_)

        # NOTE: 2021-01-28 17:47:36 TODO to complete observables here
        # management of workspaces in external kernels
        # details in self.updateForeignNamespace docstring
        self._foreign_workspace_count_ = -1

        self.foreign_namespaces = DataBag(allow_none=True, mutable_types=True)
        # FIXME: 2021-08-19 21:45:17
        # self.foreign_namespaces.observe(self._foreignNamespacesCountChanged_, names="length")

        # TODO/FIXME 2020-07-31 00:07:29
        # low priority: choose pallette in a clever way to take into account the
        # currently used GUI palette - VERY low priority!
        # self.foreign_kernel_palette = list(sb.color_palette("pastel", 1))

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
        self.setColumnCount(len(standard_obj_summary_headers))
        self.setHorizontalHeaderLabels(
            standard_obj_summary_headers)  # defined in core.utilities

        self.mpl_figure_close_callback = mpl_figure_close_callback
        self.mpl_figure_click_callback = mpl_figure_click_callback
        self.mpl_figure_enter_callback = mpl_figure_enter_callback

        self._varChanges_callbacks_ = {WorkspaceVarChange.New:      partial(self.__class__.addRowForVariable2, self, self.shell.user_ns),
                                       WorkspaceVarChange.Modified: partial(self.__class__.updateRowForVariable2, self, self.shell.user_ns),
                                       WorkspaceVarChange.Removed:  partial(self.__class__.removeRowForVariable2, self, self.shell.user_ns)}

        # self.internalVariableChanged.connect(self._slot_internalVariableChanged_)
        self.internalVariableChanged.connect(self._slot_internalVariableChanged_)
        self.sig_startAsyncUpdate.connect(self._slot_updateModelAsync_, QtCore.Qt.QueuedConnection)

    def _foreignNamespacesCountChanged_(self, change):
        # FIXME / TODO 2020-07-30 23:49:13
        # this assumes the GUI has the default (light coloured) palette e.g. Breeze
        # or such like. What if the system uses a dark-ish palette?
        # This approach is WRONG, but fixing it has low priority.
        # self.foreign_kernel_palette = list(sb.color_palette("pastel", change["new"]))
        # print("workspaceModel: foreign namespaces = %s, (old: %s, new: %s)" % (len(self.foreign_namespaces), change["old"], change["new"]))
        pass

    def __reset_variable_dictionaries__(self):
        self.cached_vars = dict([item for item in self.shell.user_ns.items(
        ) if item[0] not in self.user_ns_hidden and not item[0].startswith("_")])
        self.modified_vars.clear()
        self.new_vars.clear()
        self.deleted_vars.clear()
        self.internalVariablesMonitor.clear()

    def removeForeignNamespace(self, wspace: dict):
        # print("workspaceModel to remove %s" % wspace)
        self.clearForeignNamespaceDisplay(wspace, remove=True)

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
                saved_current = set(saved_sessions[connfilename]["current"])
                saved_initial = set(saved_sessions[connfilename]["initial"])

            else:
                saved_current = None
                saved_initial = None

        return saved_current, saved_initial

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

        saved_current, saved_initial = self._loadSessionCache_(connfilename)

        if saved_initial is not None and saved_current is not None:
            retained_initial = symbols & saved_initial

            # print("retained_initial", retained_initial)

            retained_current = symbols & saved_current

            # print("retained_current", retained_current)

            added_symbols = symbols - (retained_initial | retained_current)

            # print("added_symbols", added_symbols)

            current = retained_current | added_symbols

            initial = symbols - current

        else:
            current = set()
            initial = symbols

        return current, initial

    def _saveSessionCache_(self, connfilename: str, nsname: str):
        mainWindow = self.shell.user_ns.get("mainWindow", None)
        if mainWindow:
            sessions_filename = os.path.join(os.path.dirname(mainWindow.scipyenSettings.user_config_path()),
                                             "cached_sessions.json")

            session_dict = {"current": list(self.foreign_namespaces[nsname]["current"]),
                            "initial": list(self.foreign_namespaces[nsname]["initial"]),
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

    def clearForeignNamespaceDisplay(self, workspace: typing.Union[dict, str], remove: bool = False):
        """De-registers a foreign workspace dictionary.

        Parameters:
        ==========

        workspace: dict or str

            When a dict it must have the following key/value pairs:

                "connection_file": str = name of the connection file

                "master": None, or a dict with the following key/value pairs:
                    "client_session_ID": str,
                    "manager_session_ID": str,
                    "tab_name": str

                "name": str = registered natural workspace name (i.e allowing
                                spaces)

                For a non-local session/connection, "master" is mapped to None.

            When a str, it is the workspace name _AS_REGISTERED_ with the workspace
            model (i.e. " " replaced with "_")

        remove: bool, optional (default is False)
            When True, the workspace name will also be de-registered.

            If workspace is a dict is till be used to determine whether the 
            workspace belongs to a remote kernel (which is NOT managed by Scipyen's
            external ipython) and a snapshot of the symbols in the kernel's 
            namespace will be saved to the "cached_sessions.json" file 
            (typically located in ~/.config/Scipyen)

        """
        # check that we received a sessions dictionary and that this was generated
        # from a remotely-managed kernel

        if isinstance(workspace, str):
            nsname = workspace
            connfilename = None

            is_local = None

        elif isinstance(workspace, dict) and \
                all([s in workspace.keys() for s in ("connection_file", "master", "name")]):
            is_local = isinstance(workspace["master"], dict)
            nsname = workspace["name"]
            connfilename = workspace.get("connection_file")

        else:
            return

        # print("clearForeignNamespaceDisplay nsname", nsname, "connection_file", connfilename)

        if nsname in self.foreign_namespaces:
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
                if connfilename and os.path.isfile(connfilename) and not is_local:
                    self._saveSessionCache_(connfilename, nsname)

                self.foreign_namespaces.pop(nsname)

            else:
                self.foreign_namespaces[nsname]["current"].clear()

            # OK. Now, update the workspace table
            kernel_items_rows = self.rowIndexForItemsWithProps(
                Workspace=nsname)

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

    def updateForeignNamespace(self, ns_name: str, cfile: str, val: typing.Any):
        """Symbols in external kernels' namepaces are stored here

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
        # print("WorkspaceModel.updateForeignNamespace ns_name = ",ns_name, " val =", val)
        # print("WorkspaceModel.updateForeignNamespace ns_name %s" % ns_name)
        initial = set()
        current = set()

        if isinstance(val, dict):
            initial = val.get("user_ns", set())

        elif isinstance(val, (list, set, tuple)):
            initial = set([k for k in val])

        else:
            raise TypeError(
                "val expected to be a dict or a list; got %s instead" % type(val).__name__)

        # print("WorkspaceModel.updateForeignNamespace symbols", initial)

        # saved_sessions = dict()
        # saved_current = set()
        # saved_initial = set()

        # if len(initial):
        # print("\t%s in foreign_namespaces" % ns_name, ns_name in self.foreign_namespaces)
        if ns_name not in self.foreign_namespaces:
            # NOTE:2021-01-28 21:58:59
            # check to see if there is a snapshot of a currently live kernel
            # to retrieve live symbols from there
            if os.path.isfile(cfile):  # make sure connection is alive
                externalConsole = self.shell.user_ns.get(
                    "external_console", None)
                if externalConsole:
                    cdict = externalConsole.window.connections.get(cfile, None)
                    if isinstance(cdict, dict) and "master" in cdict and cdict["master"] is None:
                        # print("found remote connection for %s" % cfile)
                        current, initial = self._mergeSessionCache_(
                            cfile, initial)

            # special treatment for objects loaded from NEURON at kernel
            # initialization time (see extipyutils_client
            # nrn_ipython_initialization_cmd and the
            # core.neuron_python.nrn_ipython module)

            # may have already been in saved current
            neuron_symbols = initial & {"h", "ms", "mV"}

            current = current | neuron_symbols  # set operations ensure unique elements

            # for v in ("h", "ms", "mV",):
            # if v in initial:
            # current.add(v)
            # initial.remove(v)

            # The distinction between initial and current boils down to symbols
            # visible in the workspace table and for which properties are queried
            # (i.e., those in the "current" set) versus the symbols NOT visible
            # in the workspace table and therefore skipped from property query
            # (thus keeping the whole excercise of updating the workspace table
            # less demanding)

            # will trigger _foreignNamespacesCountChanged_ which at the
            # moment, does nothing
            self.foreign_namespaces[ns_name] = {"current": current,
                                                "initial": initial,
                                                }

        else:
            # print("\tupdateForeignNamespace: foreign namespaces:", self.foreign_namespaces)
            # print("\tself.foreign_namespaces[ns_name]['current']", self.foreign_namespaces[ns_name]["current"])

            removed_symbols = self.foreign_namespaces[ns_name]["current"] - initial
            # print("\tremoved_symbols", removed_symbols)
            for vname in removed_symbols:
                self.removeRowForVariable(vname, ns=ns_name)
                # self.removeRowForVariable(vname, ns = ns_name.replace("_", " "))

            added_symbols = initial - \
                self.foreign_namespaces[ns_name]["current"]

            self.foreign_namespaces[ns_name]["current"] -= removed_symbols

            self.foreign_namespaces[ns_name]["current"] |= added_symbols

            self.foreign_namespaces[ns_name]["current"] -= self.foreign_namespaces[ns_name]["initial"]

    def clear(self):
        self.cached_vars.clear()
        self.modified_vars.clear()
        self.new_vars.clear()
        self.deleted_vars.clear()
        # self.user_ns_hidden.clear()
        self.internalVariablesMonitor.clear()

    def isUserVariable(self, name, val):
        """Check if symbol ↦ value binding is not hidden from the user.
        """
        # see NOTE 2020-11-29 16:29:01
        if name in self.user_ns_hidden:
            return val is not self.user_ns_hidden[name]
        else:
            return not name.startswith("_")

        return True
    
    def bindObjectInNamespace(self, varname:str, data:typing.Any, hidden:bool=False,
                namespace:typing.Optional[dict] = None):
        """Binds an object to a symbol, in the specified namespace.
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
            warnings.warn("Currently, only the internal workspace is supported")
            return
        
        # NOTE: 2023-05-27 22:24:04
        # If needed, store a reference in self.user_ns_hidden, so that it won't 
        # be picked up by self.internalVariablesMonitor observer
        if hidden: 
            self.user_ns_hidden[varname] = data
            
        self.preExecute()
        namespace[varname] = data
        self.postRunCell(Bunch(success=True))
        
    def unbindObjectInNamespace(self, varname:str, 
                                  namespace:typing.Optional[dict] = None) -> typing.Any:
        """Unbinds an object from its symbol is a specified namespace.
        WARNING: The object may be still alive, but unaccessible in the namespace
        via its symbol given by varname, until it will be garbage-collected.
        """
        if namespace is None:
            namespace = self.shell.user_ns
        
        if namespace != self.shell.user_ns:
            warnings.warn("Currently, only the internal workspace is supported")
            return
        
        if varname in namespace:
            if varname not in self.user_ns_hidden:
                self.preExecute()
                obj = namespace.pop(varname)
                self.postRunCell(Bunch(success=True))
                return obj
            
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
            
    def internalVariablesListenerCB(self, change):
        # self.__change_dict__ = change
        # QtCore.QTimer.singleShot(0, self._observe_wrapper_)
        # connected to self._slot_internalVariableChanged_, def'ed below
        # print(f"\n{self.__class__.__name__}.internalVariablesListenerCB({change})")
        self.internalVariableChanged.emit(change)
        
    @pyqtSlot(dict)
    def _slot_cacheInternalVariableChange_(self, change):
        name = change.name
        change_type = change.get("change_type", change.type)
        
        if change_type in ("remove", "removed"):
            self.__changes__[name] = WorkspaceVarChange.Removed
        elif change_type == "new":
            self.__changes__[name] = WorkspaceVarChange.New
        elif change_type == "modified":
            self.__changes__[name] = WorkspaceVarChange.Modified
        else:   # for legacy (traitlets.TraitType-style) notifications
                # that lack 'change_type' attribute
            self.__changes__[name] = WorkspaceVarChange.Modified

    @pyqtSlot(dict)
    def _slot_internalVariableChanged_(self, change):
        """Connected (and triggered by) self.internalVariableChanged Qt signal"""
        name = change.name
        # print(f"\n{self.__class__.__name__}._slot_internalVariableChanged_({change})")

        displayed_var_names = set(self.getDisplayedVariableNames())
        user_shell_var_names = set(self.shell.user_ns.keys())

        # NOTE: 2023-05-28 22:15:54
        # GuiWorker is a QRunnable
        # worker = pgui.GuiWorker(self._updateFromMonitor_, name, 
        #                         displayed_var_names, user_shell_var_names,
        #                         change.type)
        
        change_type = change.get("change_type", change.type)
        
        worker = pgui.GuiWorker(self._updateFromMonitor_, name, 
                                displayed_var_names, user_shell_var_names,
                                change_type)
        
        worker.signals.signal_Result.connect(self._slot_updateModelFromMonitor_)
        
        self.threadpool.start(worker)

    def _updateFromMonitor_(self, name: str, 
                            displayed_var_names: set, user_shell_var_names: set,
                            change_type:str):

        # print(f"\n{self.__class__.__name__}._updateFromMonitor_ {name}\n\tin shell: {name in self.shell.user_ns}\n\tdisplayed: {name in displayed_var_names}")
        if change_type in ("remove", "removed"):
            alteration = WorkspaceVarChange.Removed
        elif change_type == "new": # name in user_shell_var_names:
            alteration = WorkspaceVarChange.New
        elif change_type == "modified":
            alteration = WorkspaceVarChange.Modified
        else:   # for legacy (traitlets.TraitType-style) notifications
                # lacking a 'change_type' attribute
            if name in user_shell_var_names:
                if name not in displayed_var_names:
                    alteration = WorkspaceVarChange.New
                else:
                    alteration = WorkspaceVarChange.Modified
            else:
                if name in displayed_var_names:
                    alteration = WorkspaceVarChange.Removed
        
                else:
                    alteration = None
                
#             if change_type == "new": # name in user_shell_var_names:
#                 alteration = WorkspaceVarChange.New
#             elif change_type == "modified":
#                 alteration = WorkspaceVarChange.Modified
#             else: # for legacy (traitlets.TraitType-style) notifications
#                 if name in user_shell_var_names:
#                     if name not in displayed_var_names:
#                         alteration = WorkspaceVarChange.New
#                     else:
#                         alteration = WorkspaceVarChange.Modified
#                 else:
#                     if name in displayed_var_names:
#                         alteration = WorkspaceVarChange.Removed
#             
#                     else:
#                         alteration = None
#                     
        return (name, alteration)

    @pyqtSlot(tuple)
    def _slot_updateModelFromMonitor_(self, value):
        name, alteration = value
        # print(f"\n{self.__class__.__name__}._slot_updateModelFromMonitor_ {name} {alteration.name}")
        if isinstance(alteration, WorkspaceVarChange):
            # calls a callback to affect the model ⇒ the viewer UI
            self._varChanges_callbacks_[alteration](name)
            # ⇒ in MainWindow this will trigger cosmetic update of the viewer
            self.modelContentsChanged.emit()

    def preExecute(self):
        """Updates internalVariablesMonitor DataBag
        """
        # ensure we observe only "user" variables in user_ns (i.e. excluding the "hidden"
        # ones like the ones used by ipython internally)
        # NOTE: 2023-01-28 13:27:40
        # we take a snapshot of the current user_ns HERE:
        self.cached_vars = dict([item for item in self.shell.user_ns.items(
        ) if not item[0].startswith("_") and self.isUserVariable(item[0], item[1])])

        # NOTE: 2023-01-28 13:27:47
        # we also take a snapshot of the mpl figures
        # first, capture those registered in pyplot/pylab
        # REMEMBER Gcf holds references to instances of FigureManager concrete subclasses
        self.cached_mpl_figs = set(
            fig_manager.canvas.figure for fig_manager in Gcf.figs.values())

        # NOTE: 2023-01-29 23:30:32
        # all figures created outside pyplot are now adopted for management under
        # pyplot (see mainwindow.WindowManager._adopt_mpl_figure() method, called
        # by code inside post_execute, below)
        for v in self.cached_vars.values():
            if isinstance(v, mpl.figure.Figure):
                # self.cached_mpl_figs is a set so duplicates won't be added
                self.cached_mpl_figs.add(v)

        # print(f"\npreExecute cached figs {self.cached_mpl_figs}")

        # need to withhold notifications here
        with self.internalVariablesMonitor.observer.hold_trait_notifications():
            observed_set = set(self.internalVariablesMonitor.keys())
            cached_set = set(self.cached_vars)

            observed_not_cached = observed_set - cached_set
            for var in observed_not_cached:
                self.internalVariablesMonitor.pop(var, None)

    # @timefunc
    # def post_execute(self):
    #     """Updates workspace model AFTER kernel execution.
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
    #     # print(f"\npost_execute cached figs {self.cached_mpl_figs}")
    # 
    #     # print(f"\npost_execute Gcf figs {Gcf.figs}")
    # 
    #     # NOTE: 2023-01-29 23:32:44
    #     # capture the figures referenced in Gcf
    #     # these should be ALL mpl figures Scipyen knows about, see NOTE: 2023-01-29 23:30:32
    #     #
    #     current_mpl_figs = set(
    #         fig_manager.canvas.figure for fig_manager in Gcf.figs.values())
    # 
    #     # print(f"\npost_execute current figs {current_mpl_figs}")
    # 
    #     deleted_mpl_figs = self.cached_mpl_figs - current_mpl_figs
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
    #     new_mpl_figs = current_mpl_figs - self.cached_mpl_figs
    # 
    #     for k, v in self.shell.user_ns.items():
    #         if isinstance(v, mpl.figure.Figure):
    #             if v not in self.cached_mpl_figs:
    #                 new_mpl_figs.add(v)
    # 
    #     # print(f"\npost_execute new_mpl_figs = {new_mpl_figs}")
    # 
    #     for fig in new_mpl_figs:
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
    #             win, QtWidgets.QMainWindow) and self.parent()._is_scipyen_viewer_class_(type(win))]
    #         user_ns_viewers = [v for v in self.shell.user_ns.values() if isinstance(
    #             v, QtWidgets.QMainWindow) and self.parent()._is_scipyen_viewer_class_(type(v))]
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
    #     #     # current_vars = dict([item for item in self.shell.user_ns.items() if not item[0].startswith("_") and self.isUserVariable(item[0], item[1])])
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

    def postRunCell(self, result):
        # print(f"{self.__class__.__name__}.postRunCell result = {result}")
        if hasattr(result, "success") and result.success:
            self._updateModel_(self.shell.user_ns)

    def _updateModel_(self, ns: dict):
        """Determines what workspace variables have been removed/added/modified.
        
        This change may be a consequence of:
        • code run at Scipyen's console
        • code run outside of console, but which adds/removes/modifies objects in
            the workspace
        
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

        # NOTE: 2023-01-29 23:32:44
        #
        # 1.1 capture the figures referenced in Gcf
        #   these should be ALL mpl figures Scipyen knows about, see NOTE: 2023-01-29 23:30:32
        #
        current_mpl_figs = set(
            fig_manager.canvas.figure for fig_manager in Gcf.figs.values())

        #
        # 1.2 figure out which currently cached reference to matplotlib figures
        #   were actually removed from Gcf - if they still esixt in the workspace
        #   we need to remove them ⇒ deleted_mpl_figs
        #
        # NOTE: cached_mpl_figs is populated/updated at preExecute when code is
        #   called at the console; otherwise, it is the MainWindow's responsibility - TODO/FIXME
        #
        deleted_mpl_figs = self.cached_mpl_figs - current_mpl_figs

        #
        # 1.3 now, remove the figs in the deleted_mpl_figs
        #
        for f in deleted_mpl_figs:
            f_names = list(k for k, v in ns.items() if isinstance(
                v, mpl.figure.Figure) and v == f and not k.startswith("_"))
            if len(f_names):
                for n in f_names:
                    ns.pop(n, None)
                    # NOTE: 2023-05-24 16:33:14 - remove them from the DataBag of observed vars
                    #
                    if n in self.internalVariablesMonitor.keys():
                        # NOTE: the DataBag only deals with user_ns variables
                        self.internalVariablesMonitor.pop(n, None)

        #
        # 1.4 figure out if there are new matplpotlib figures around ⇒ collect in new_mpl_figs
        #   these are registered with Gcf, but not referenced in the workspace cached ones
        #
        new_mpl_figs = current_mpl_figs - self.cached_mpl_figs

        # NOTE: 2023-05-24 16:37:06
        # in addition, these may have been placed directly in the workspace upon
        # return by code called at the console - add these to new_mpl_figs as well
        # CAUTION: we may end up with duplicate references !
        #
        for k, v in ns.items():
            if isinstance(v, mpl.figure.Figure):
                if v not in self.cached_mpl_figs:
                    new_mpl_figs.add(v)

        #
        # 1.5 finally, add these new figures
        #   • make sure they are managed by pyplot
        #   • assign variable names avoiding clashes
        for fig in new_mpl_figs:
            # NOTE: 2023-01-29 23:34:00 • make sure they are managed by pyplot
            # (see NOTE: 2023-01-29 23:30:32)
            # We need to call this early because we need a fig.number to avoid
            # complicatons in fig variable name management!
            if getattr(fig.canvas, "manager", None) is None:
                fig = self.parent()._adopt_mpl_figure(fig)  # , integrate_in_pyplot=False)

            # NOTE: 2023-05-24 16:45:11 • assign variable names avoiding clashes
            # set up a reasonable variable name
            fig_var_name = "Figure"

            if fig.canvas.manager is not None and getattr(fig.canvas.manager, "num", None) is not None:
                fig_var_name = f"Figure{fig.canvas.manager.num}"

            elif getattr(fig, "number", None) is not None:
                fig_var_name = f"Figure{fig.number}"

            # see if there are any figs in the workspace
            # cached_figs = [v for v in self.cached_vars.values() if isinstance(v, mpl.figure.Figure)]
            cached_figs = [v for v in ns.values(
            ) if isinstance(v, mpl.figure.Figure)]

            # only add the figure if not already present
            if fig not in cached_figs:
                # adjust variable name to avoid clashes
                if fig_var_name in ns:
                    fig_var_name = validate_varname(fig_var_name, ws=ns)
                    
                # print(f"\n adding fig_var_name {fig_var_name}")
                ns[fig_var_name] = fig
                
                # this SHOULD notify hence populate the ns
                self.internalVariablesMonitor[fig_var_name] = fig
                # self.shell.user_ns[fig_var_name] = fig

        # ###
        # 2. deal with Scipyen viewer windows
        #
        if isinstance(self.parent(), QtWidgets.QMainWindow) and type(self.parent()).__name__ == "ScipyenWindow":
            cached_viewers = [(wname, win) for (wname, win) in self.cached_vars.items() if isinstance(
                win, QtWidgets.QMainWindow) and self.parent()._is_scipyen_viewer_class_(type(win))]
            user_ns_viewers = [v for v in ns.values() if isinstance(
                v, QtWidgets.QMainWindow) and self.parent()._is_scipyen_viewer_class_(type(v))]
            for w_name_obj in cached_viewers:
                if w_name_obj[1] not in user_ns_viewers:
                    self.cached_vars.pop(w_name_obj[0], None)

                else:
                    self.parent().registerWindow(w_name_obj[1])

        # ###
        # 3. now, deal with everything else
        #
        # ### BEGIN 2023-05-23 22:39:22 do not delete
        #
        # 3.1. establish which variables have been removed ⇒ del_vars
        #
        # current_user_varnames = set(self.shell.user_ns.keys())
        current_user_varnames = set(ns.keys())
        observed_varnames = set(self.internalVariablesMonitor.keys())
        del_vars = observed_varnames - current_user_varnames

        # if len(del_vars):
        # print(f"{self.__class__.__name__}._updateModel_ del_vars = {del_vars}")
        #
        # 3.2. now, remove these from the DataBag of observed variables (self.internalVariablesMonitor)
        #
        # NOTE: 2023-05-24 16:18:58
        # The DataBag will NOW notify any observers upon the removal of these variables
        # Works OK
        self.internalVariablesMonitor.delete(*list(del_vars))
        # self.internalVariablesMonitor.remove_members(*list(del_vars))

        #
        # 3.3. now, figure out whether there are NEW variables added to the workspace
        # Their names are present in the workspace, but ABSENT in the DataBag of 
        # observed variables.
        #

        # current_vars = dict([item for item in self.shell.user_ns.items() if not item[0].startswith("_") and self.isUserVariable(item[0], item[1])])
        current_vars = dict([item for item in ns.items() if not item[0].startswith(
            "_") and self.isUserVariable(item[0], item[1])])

        # NOTE: 2023-05-24 16:22:58
        # this SHOULD also notify the observers - Works OK when adding new symbols
        # does not work when an object bound to an existing symbol has been modified
        # (i.e., either the symbols is bound to a different object reference, or
        # the contents of the object have changed)
        self.internalVariablesMonitor.update(current_vars)
        
        # NOTE 2023-05-25 18:13:46
        # Changes of object attributes or data the object are NOT detected by this approach 
        # (see TODO/FIXME 2023-05-25 18:12:56 in core/scipyen_traitlets.py)
        # ### END 2023-05-23 22:39:22 do not delete

        # NOTE: 2023-05-28 01:31:53
        # the next two signal a change directory command issued at the console
        current_dir = os.getcwd()
        self.workingDir.emit(current_dir)

    def _generateModelItemForObject_(self, propdict: dict, editable: typing.Optional[bool] = False, elidetip: typing.Optional[bool] = False, background: typing.Optional[QtGui.QBrush] = None, foreground: typing.Optional[QtGui.QBrush] = None):
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

        return item

    @safeWrapper
    def generateRowContents(self, dataname: str, data: object, namespace: str = "Internal"):
        # print("generateRowContents", dataname, data, namespace)
        obj_props = summarize_object_properties(
            dataname, data, namespace=namespace)
        # print("generateRowContents obj_props", obj_props)
        return self.genRowFromPropDict(obj_props)

    def genRowFromPropDict(self, obj_props: dict, background: typing.Optional[QtGui.QBrush] = None, foreground: typing.Optional[QtGui.QBrush] = None):
        """Returns a row of QStandardItems
        """
        # print(f"genRowFromPropDict obj_props = {obj_props}")
        return [self._generateModelItemForObject_(obj_props[key],
                editable=(key == "Name"),
                elidetip=(key == "Name"),
                background=background,
                foreground=foreground) for key in standard_obj_summary_headers]

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

    def getRowIndexForVarname(self, varname, regVarNames=None):
        """Returns the row index for the variable symbol 'varname'

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
        """Returns the symbol of a variable in the model, for a given model index.

        Returns none it if the symbol does not exist in the user workspace
        """
        v = self.item(index.row(), 0).text()

        return v if v in self.shell.user_ns else None  # <- this is the workspace

    # @pyqtSlot()
    # def slot_updateTable(self):
    #     # print("slot_updateTable")
    #     # QtCore.QTimer.singleShot(0, self.update)
    #     timer = QtCore.QTimer()
    #     timer.timeout.connect(self.update)
    #     timer.start(0)
    #     # self.update()

    # def updateRowForVariable(self, dataname, data, ns=None):
    #     # CAUTION This is only for internal workspace, but
    #     # TODO 2020-07-30 22:18:35 merge & factor code for both internal and foreign
    #     # kernels (make use of the ns parameter)
    #     #
    #     if ns is None:
    #         ns = "Internal"
    # 
    #     elif isinstance(ns, str):
    #         if len(ns.strip()) == 0:
    #             ns = "Internal"
    # 
    #     else:
    #         ns = "Internal"
    # 
    #     # print("updateRowForVariable", dataname, data, ns)
    # 
    #     row = self.rowIndexForItemsWithProps(Workspace=ns)
    # 
    #     # print("updateRowForVariable, row:", row)
    # 
    #     items = self.findItems(dataname)
    # 
    #     # print("updateRowForVariable, items", items)
    # 
    #     if len(items) > 0:
    #         row = self.indexFromItem(items[0]).row()  # same as below
    #         # print("updateRowForVariable, row:", row)
    #         # row = items[0].index().row()
    #         # generate model view row contents for existing item
    #         v_row = self.generateRowContents(dataname, data)
    #         self.updateRow(row, v_row)

    def updateRowForVariable2(self, ns: dict, dataname: str, ns_name: typing.Optional[str] = None):
        # CAUTION This is only for internal workspace, but
        # TODO 2020-07-30 22:18:35 merge & factor code for both internal and foreign
        # kernels (make use of the ns parameter)
        #
        if dataname not in ns:
            return

        data = ns[dataname]

        if ns_name is None:
            ns_name = "Internal"

        elif isinstance(ns_name, str):
            if len(ns_name.strip()) == 0:
                ns_name = "Internal"

        else:
            ns_name = "Internal"

        # print(f"{self.__class__.__name__}.updateRowForVariable2 dataname = {dataname}, ns_name={ns_name}")

        row = self.rowIndexForItemsWithProps(Workspace=ns_name)

        # print("updateRowForVariable, row:", row)

        items = self.findItems(dataname)

        # print("updateRowForVariable, items", items)

        if len(items) > 0:
            row = self.indexFromItem(items[0]).row()  # same as below
            # print("updateRowForVariable, row:", row)
            # row = items[0].index().row()
            # generate model view row contents for existing item
            v_row = self.generateRowContents(dataname, data)
            self.updateRow(row, v_row)

    def updateRowFromProps(self, row, obj_props, background=None):
        """
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
        originalRow = self.getRowContents(rowindex, asStrings=False)
        # print("updateRow originalRow as str", self.getRowContents(rowindex, asStrings=True))
        if originalRow is not None:
            # for col in range(self.columnCount()):
            for col in range(1, self.columnCount()):
                # NOTE: 2021-07-28 10:42:17
                # ATTENTION this emits itemChange signal thereby will trigger
                # code for displayed name change
                self.setItem(rowindex, col, newrowdata[col])

    # def removeRowForVariable(self, dataname, ns=None):
    #     if isinstance(ns, str):
    #         if len(ns.strip()) == 0:
    #             ns = "Internal"
    # 
    #     else:
    #         ns = "Internal"
    # 
    #     row = self.rowIndexForItemsWithProps(Name=dataname, Workspace=ns)
    # 
    #     # print("WorkspaceModel.removeRowForVariable data: %s ns: %s row: %s" % (dataname, ns, row))
    #     if row == -1:
    #         return
    # 
    #     if isinstance(row, list):
    #         for r in row:
    #             self.removeRow(r)
    # 
    #     else:
    #         self.removeRow(row)

    def removeRowForVariable2(self, ns: dict, dataname: str, ns_name: typing.Optional[str] = None):
        if isinstance(ns_name, str):
            if len(ns_name.strip()) == 0:
                ns_name = "Internal"

        else:
            ns_name = "Internal"

        # print(f"{self.__class__.__name__}.removeRowForVariable2 dataname = {dataname}, ns_name={ns_name}")
        row = self.rowIndexForItemsWithProps(Name=dataname, Workspace=ns_name)

        if row == -1:
            return

        if isinstance(row, list):
            for r in row:
                self.removeRow(r)

        else:
            self.removeRow(row)

    # def addRowForVariable(self, dataname, data):
    #     """CAUTION Only use for data in the internal workspace, not in remote ones.
    #     """
    #     # print("addRowForVariable: ", dataname, data)
    #     # generate model view row contents
    #     v_row = self.generateRowContents(dataname, data)
    #     self.appendRow(v_row)  # append the row to the model

    def addRowForVariable2(self, ns: dict, dataname: str, ns_name: typing.Optional[str] = None):
        """CAUTION Only use for data in the internal workspace, not in remote ones.
        """
        if isinstance(ns_name, str):
            if len(ns_name.strip()) == 0:
                ns_name = "Internal"

        else:
            ns_name = "Internal"

        if dataname not in ns:
            return
        
        data = ns[dataname]
        # print(f"{self.__class__.__name__}.addRowForVariable2 dataname = {dataname}, ns_name={ns_name}")
        
        # generate model view row contents
        v_row = self.generateRowContents(dataname, data)
        self.appendRow(v_row)  # append the row to the model

    def clearTable(self):
        self.removeRows(0, self.rowCount())

    def update_old(self):
        """Updates workspace model.
        To be called by code that adds/remove/modifies/renames variables 
        in the Scipyen's namespace in order to update the workspace viewer.
        
        WARNING: This function should NOT be used for normal operation: changes
        in the workspace contents are monitored by the internal variable monitor
        which triggers Ui updates already.

        """

        # currently displayed variables in the viewer widget
        displayed_var_names = set(self.getDisplayedVariableNames())

        # current variable names in the namespace, which should be available to
        # the user - this ain't faster
        current_vars = dict(filter(lambda x: not x[0].startswith("_") and self.isUserVariable(*x), self.shell.user_ns.items()))
        
        # names of variables in user namespace
        current_user_varnames = set(current_vars.keys())
        # current_user_varnames = set(self.shell.user_ns.keys())

        # names of variables present in the internalVariablesMonitor DataBag
        observed_varnames = set(self.internalVariablesMonitor.keys())

        # names still in internalVariablesMonitor but not in user namespace anymore
        del_vars = observed_varnames - current_user_varnames

        # current variable names in the namespace, which should be available to
        # the user - CAUTION this scales with 𝒪(n) !
        # current_vars = dict([item for item in self.shell.user_ns.items(
        # ) if not item[0].startswith("_") and self.isUserVariable(item[0], item[1])])

        self.internalVariablesMonitor.delete(*list(del_vars))

        self.internalVariablesMonitor.update(current_vars)
        
    def update(self):
        """Updates workspace model - batch version.
        Used when the namespace contents are modified by code run OUTSIDE the 
        console (hence, independently of the console's kernel events)
        
        WARNING: This function is for batch operations and should NOT be used for
        normal operation: changes in the workspace contents are monitored by the
        internal variable monitor which triggers Ui updates already.

        """
        self.internalVariableChanged.disconnect(self._slot_internalVariableChanged_)
        self.internalVariableChanged.connect(self._slot_cacheInternalVariableChange_)
        
        # currently displayed variables in the viewer widget
        displayed_var_names = set(self.getDisplayedVariableNames())
        
        # current variable names in the namespace, which should be available to
        # the user - is this faster?
        current_vars = dict(filter(lambda x: not x[0].startswith("_") and self.isUserVariable(*x), self.shell.user_ns.items()))
        
        # names of variables in user namespace
        current_user_varnames = set(current_vars.keys())
        # current_user_varnames = set(self.shell.user_ns.keys())

        # names of variables present in the internalVariablesMonitor DataBag
        observed_varnames = set(self.internalVariablesMonitor.keys())

        # names still in internalVariablesMonitor but not in user namespace anymore
        del_vars = observed_varnames - current_user_varnames

        # current variable names in the namespace, which should be available to
        # the user - CAUTION this scales with 𝒪(n) !
        # current_vars = dict([item for item in self.shell.user_ns.items(
        # ) if not item[0].startswith("_") and self.isUserVariable(item[0], item[1])])
        
        new_vars = dict(filter(lambda x: not x[0] in displayed_var_names, current_vars.items()))
        
        mod_vars = dict(filter(lambda x: x[0] in displayed_var_names, current_vars.items()))
        
        self.internalVariablesMonitor.delete(*list(del_vars)) # -> WorkspaceVarChange.Removed
        self.internalVariablesMonitor.update(current_vars) # -> WorkspaceVarChange.New or WorkspaceVarChange.Modified
            
        self.internalVariableChanged.disconnect(self._slot_cacheInternalVariableChange_)
        self.internalVariableChanged.connect(self._slot_internalVariableChanged_)
        
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

#     @contextlib.contextmanager
#     def holdUIUpdate(self):
#         """Inspired from traitlets.HasTraits.hold_trait_notifications"""
#         # cache = typing.Dict[str, typing.Any] = {}
#         
#         # def compress(past_changes, change):
#         #     """Merges the provided change with the last if possible."""
#         #     if past_changes is None:
#         #         return [change]
#         #     else:
#         #         if past_changes[-1]["type"] == "change" and change.type == "change":
#         #             past_changes[-1]["new"] = change.new
#         #         elif past_changes[-1]["type"] == "remove" and change.type == "remove":
#         #             past_changes[-1]["new"] = Undefined
#         #         else:
#         #             # In case of changes other than 'change', append the notification.
#         #             past_changes.append(change)
#         #         return past_changes
# 
#         def hold(change):
#             pass
#             # name = change.name
#             # cache[name] = compress(cache.get(name), change)
#             
#         try:
#             self.internalVariablesListenerCB = hold
#             yield
#         except:
#             traceback.print_exc()
#         finally:
#             del self.internalVariablesListenerCB
                
            
    @pyqtSlot(dict)
    def _slot_updateModelAsync_(self, namespace:dict):
        """Triggered by self.sig_startAsyncUpdate emitted by self.update2()
        """
        if len(self.__changes__) == 0:
            return
        
        removals = filter(lambda x: x[1] == WorkspaceVarChange.Removed, self.__changes__.items())
        additions = filter(lambda x: x[1] == WorkspaceVarChange.New, self.__changes__.items())
        modifications = filter(lambda x: x[1] == WorkspaceVarChange.Modified, self.__changes__.items())
        
        
        for item in removals:
            self._varChanges_callbacks_[item[1]](item[0])
        
        for item in additions:
            self._varChanges_callbacks_[item[1]](item[0])
        
        for item in modifications:
            self._varChanges_callbacks_[item[1]](item[0])

        self.__changes__.clear()
        
        self.modelContentsChanged.emit()

    def updateFromExternal(self, prop_dicts):
        """prop_dicts: {name: nested properties dict}
            nested properties dict: {property: {"display": str, "tooltip":str}}
                property: one of
                    ['Name', 'Type', 'Data_Type', 'Minimum', 'Maximum', 'Size', 
                    'Dimensions','Shape', 'Axes', 'Array_Order', 'Memory_Size', 
                    'Workspace']

                display: the displayed text
                tooltip: tooltip text
        """
        # bg_cols = sb.color_palette("pastel", self._foreign_workspace_count_)

        # self._foreign_workspace_count_ += 1
        for varname, props in prop_dicts.items():
            ns_key = props["Workspace"]["display"]
            # ns_key = ns.replace(" ", "_")

            vname = varname.replace("properties_of_", "")

            namespaces = sorted([k for k in self.foreign_namespaces.keys()])

            if ns_key not in namespaces:
                continue  # FIXME 2020-07-30 22:42:16 should NEVER happen

            ns_index = namespaces.index(ns_key)

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

    @safeWrapper
    def rowIndexForItemsWithProps(self, **kwargs):
        """Returns row indices for all items that satisfy specified properties.

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
        a list of row indices (0-based) or one integer >=0 if ony one 
        item was found , or -1 if no item was found (Qt way)

        If kwargs are not specified, then returns range(self.rowCount())

        """
        # from core.utilities import standard_obj_summary_headers

        if len(kwargs) == 0:
            # return all row indices here
            # if used froma  deleting function, thso shoudl result in the removal
            # of all items in the model
            return range(self.rowCount())

        else:
            if self.rowCount() == 0:
                return -1

            # auxiliary vector for setting up logical indexin, see for loop below
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
                key_column = standard_obj_summary_headers.index(
                    key.replace("_", " "))
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

    @safeWrapper
    def rowIndexForItemInWorkspace(self, name, Workspace="internal"):
        """Variant of rowIndexForItemsWithProps selecting row indices for variables
            in the internal workspace

        Accepts a list of names !

        TODO!
        """

        pass

    @safeWrapper
    def rowIndexForNamedItemsWithProps(self, name, **kwargs):
        """Find the item named with "name" and optional property values

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
        """Returns a mapping of displayed variable names to their type names (as string).

        Parameters:
        -----------
        ws: str (optional, default is "Internal")

        """
        if not isinstance(ws, str):
            ws = "Internal"

        wscol = standard_obj_summary_headers.index("Workspace")
        typecol = standard_obj_summary_headers.index("Type")

        ret = dict([(self.item(row, 0).text(), self.item(row, typecol).text()) for row in range(
            self.rowCount()) if self.item(row, wscol) is not None and self.item(row, wscol).text() == ws])

        return ret

    def getDisplayedVariableTypes(self, asStrings=True, ws="Internal"):
        """Returns the DISPLAYED type of the variables.

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
        typecol = standard_obj_summary_headers.index("Type")

        ret = [self.item(row, typecol).text() if asStrings else self.item(
            row, typecol) for row in range(self.rowCount()) if self.item(row, wscol).text() == ws]

        return ret

    def getDisplayedVariableNames(self, asStrings=True, ws="Internal"):
        '''Returns names of variables in the internal workspace, registered with the model.

        Parameter: asStrings (boolean, optional, default True) variable names 
                    are returned as (a Python list of) strings, otherwise 
                    they are returned as Python list of QStandardItems
        '''
        wscol = standard_obj_summary_headers.index("Workspace")
        ret = [self.item(row).text() if asStrings else self.item(row) for row in range(
            self.rowCount()) if self.item(row, wscol).text() == ws]

        return ret

    def getNumberOfDisplayedForeignKernels(self):
        return len(self.getDisplayedWorkspaces(foreign_only=True))

    def getDisplayedWorkspaces(self, foreign_only=False):
        """Returns a set with the names of the workspaces shown.
        """
        wcsol = standard_obj_summary_headers.index("Workspace")
        workspaces = set()
        for row in range(self.rowCount()):
            wsname = self.item(row, wscol).text()
            if foreign_only and wsname == "Internal":
                continue

            workspaces.add(wsname)

        return workspaces
