# -*- coding: utf-8 -*-
"""
The workspace model - also used by the internal shell, to which ii provides the
event handlers pre_execute() and post_execute().

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

import traceback, typing, inspect, os
from copy import deepcopy
import json

#from jupyter_core.paths import jupyter_runtime_dir

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot

import matplotlib as mpl
mpl.use("Qt5Agg")
import matplotlib.pyplot as plt
import matplotlib.mlab as mlb

import numpy as np
import seaborn as sb

from core.prog import safeWrapper
from core.utilities import (summarize_object_properties,
                            standard_obj_summary_headers,
                            safe_identity_test,
                            )

from core.traitcontainers import DataBag, generic_change_handler

from .guiutils import (get_text_width, get_elided_text)

class WorkspaceModel(QtGui.QStandardItemModel):
    '''
    The data model for the workspace variable that are displayed in the QTableView 
    inside pict main window.
    
    Also implements:
    * IPython event handlers for the internal console (pre_execute and post_execute)
    * handlers for variable change in the Scipyen workspace by code oustide of
      the internal console's event loop
    
    This may be used by code external to ScipyenWindow (e.g. CaTanalysis etc)
    
    '''
    modelContentsChanged = pyqtSignal(name = "modelContentsChanged")
    
    def __init__(self, shell, user_ns_hidden=dict(), parent=None,
                 mpl_figure_close_callback=None,
                 mpl_figure_click_callback=None,
                 mpl_figure_enter_callback=None):
        super(WorkspaceModel, self).__init__(parent)
        
        self.shell = shell # reference to IPython InteractiveShell of the internal console
        
        self.cached_vars = dict()
        self.modified_vars = dict()
        self.new_vars = dict()
        self.deleted_vars = dict()
        self.user_ns_hidden = dict(user_ns_hidden)
        
        self.observed_vars = DataBag(allow_none = True, mutable_types=True)
        self.observed_vars.verbose = True
        self.observed_vars.observe(self.var_observer)
        
        # NOTE: 2021-07-28 09:58:38
        # currentItem/Name are set by selecting/activating an item in workspace view
        self.currentItem = None
        # NOTE: 2017-09-22 21:33:47
        # cache for the current var name to allow renaming workspace variables
        # this should be updated whenever the variable name is selected/activated in the model table view
        self.currentItemName = "" # name of currently selected variable
        # NOTE: 2021-06-12 12:11:25
        # cache symbol when the data it is bound to has changed; needed e.g. 
        # for updateRowForVariable
        # CAUTION this is volatile, DO NOT USE it to retrieve current var name
        # e.g., for the purpose of renaming
        self.originalVarName = "" # varname cache for individual row changes
        self.setColumnCount(len(standard_obj_summary_headers))
        self.setHorizontalHeaderLabels(standard_obj_summary_headers) # defined in core.utilities
        
        # NOTE: 2021-01-28 17:47:36
        # management of workspaces in external kernels
        # details in self.update_foreign_namespace docstring
        self._foreign_workspace_count_ = -1
        # TODO/FIXME 2020-07-31 00:07:29
        # low priority: choose pallette in a clever way to take into account the
        # currently used GUI palette - VERY low priority!
        #self.foreign_kernel_palette = list(sb.color_palette("pastel", 1))
        
        self.foreign_namespaces = DataBag(allow_none=True, mutable_types=True)
        # FIXME: 2021-08-19 21:45:17
        #self.foreign_namespaces.observe(self._foreign_namespaces_count_changed_, names="length")
        
        self.mpl_figure_close_callback = mpl_figure_close_callback
        self.mpl_figure_click_callback = mpl_figure_click_callback
        self.mpl_figure_enter_callback = mpl_figure_enter_callback
            
    def _foreign_namespaces_count_changed_(self, change):
        # FIXME / TODO 2020-07-30 23:49:13
        # this assumes the GUI has the default (light coloured) palette e.g. Breeze
        # or such like. What if the system uses a dark-ish palette?
        # This approach is WRONG, but fixing it has low priority.
        #self.foreign_kernel_palette = list(sb.color_palette("pastel", change["new"]))
        #print("workspaceModel: foreign namespaces = %s, (old: %s, new: %s)" % (len(self.foreign_namespaces), change["old"], change["new"]))
        pass
    
    def __reset_variable_dictionaries__(self):
        self.cached_vars = dict([item for item in self.shell.user_ns.items() if item[0] not in self.user_ns_hidden and not item[0].startswith("_")])
        self.modified_vars.clear()
        self.new_vars.clear()
        self.deleted_vars.clear()
        self.observed_vars.clear()
        
    def remove_foreign_namespace(self, wspace:dict):
        #print("workspaceModel to remove %s" % wspace)
        self.clear_foreign_namespace_display(wspace, remove=True)
        
    def _load_session_cache_(self, connfilename:str):
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
    
    def _merge_session_cache_(self, connfilename:str, symbols:set):
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
        
        saved_current, saved_initial = self._load_session_cache_(connfilename)
        
        if saved_initial is not None and saved_current is not None:
            retained_initial = symbols & saved_initial
            
            #print("retained_initial", retained_initial)
            
            retained_current = symbols & saved_current
            
            #print("retained_current", retained_current)
                
            added_symbols = symbols - (retained_initial | retained_current)
            
            #print("added_symbols", added_symbols)
            
            current = retained_current | added_symbols
            
            initial = symbols - current
        
        else:
            current = set()
            initial = symbols
        
        return current, initial
            
    def _save_session_cache_(self, connfilename:str, nsname:str):
        mainWindow = self.shell.user_ns.get("mainWindow", None)
        if mainWindow:
            sessions_filename = os.path.join(os.path.dirname(mainWindow.scipyenSettings.user_config_path()),
                                             "cached_sessions.json")
            
            session_dict = {"current":list(self.foreign_namespaces[nsname]["current"]),
                            "initial":list(self.foreign_namespaces[nsname]["initial"]),
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
            
            stale_connections = [cfile for cfile in saved_sessions if not os.path.isfile(cfile)]
            
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
            
    def clear_foreign_namespace_display(self, workspace:typing.Union[dict, str], remove:bool=False):
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
        
        #print("clear_foreign_namespace_display nsname", nsname, "connection_file", connfilename)
                
        if nsname in self.foreign_namespaces:
            # NOTE: 2021-01-28 17:45:54
            # check if workspace nsname belongs to a remote kernel - see docstring to
            # self.update_foreign_namespace for details
        
            if remove: 
                # kernel is managed externally ==> store the "current" symbols
                # in cache
                # FIXME: this won't work because by this time the connection
                # dict from external console window connections has been removed
                #connfilename = externalConsole.window.get_connection_filename_for_workspace(natural_nsname)
                # NOTE: 2021-01-29 10:08:16 RESOLVED: we are sending the
                # connection dict instead of just the workspace name
                #print("connfilename", connfilename)
                if connfilename and os.path.isfile(connfilename) and not is_local:
                    self._save_session_cache_(connfilename, nsname)

                self.foreign_namespaces.pop(nsname)
                
            else:
                self.foreign_namespaces[nsname]["current"].clear()
            
            # OK. Now, update the workspace table
            kernel_items_rows = self.rowIndexForItemsWithProps(Workspace=nsname)
            
            #print("kernel_items_rows for %s" % nsname,kernel_items_rows)
            if isinstance(kernel_items_rows, int):
                if kernel_items_rows >= 0:
                    #print("item", self.item(kernel_items_rows,0).text())
                    self.removeRow(kernel_items_rows)
                
            else:
                # must get the row for one item at a time, because the item's row
                # will have changed after the removal of previous rows
                itemnames = [self.item(r,0).text() for r in kernel_items_rows]
                for name in itemnames:
                    r = self.rowIndexForItemsWithProps(Name=name, Workspace=nsname)
                    try:
                        self.removeRow(r)
                    except:
                        pass
                    
    def update_foreign_namespace(self, ns_name:str, cfile:str, val:typing.Any):
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
        "current" symbols when the namspace is first encountered, with the risk 
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
        #print("WorkspaceModel.update_foreign_namespace ns_name = ",ns_name, " val =", val)
        #print("WorkspaceModel.update_foreign_namespace ns_name %s" % ns_name)
        initial = set()
        current = set()
        
        if isinstance(val, dict):
            initial = val.get("user_ns", set())
            
        elif isinstance(val, (list, set, tuple)):
            initial = set([k for k in val])
            
        else:
            raise TypeError("val expected to be a dict or a list; got %s instead" % type(val).__name__)
                            
        #print("WorkspaceModel.update_foreign_namespace symbols", initial)
        
        #saved_sessions = dict()
        #saved_current = set()
        #saved_initial = set()
        
        #if len(initial):
        #print("\t%s in foreign_namespaces" % ns_name, ns_name in self.foreign_namespaces)
        if ns_name not in self.foreign_namespaces:
            # NOTE:2021-01-28 21:58:59
            # check to see if there is a snapshot of a currently live kernel
            # to retrieve live symbols from there
            if os.path.isfile(cfile): # make sure connection is alive
                externalConsole = self.shell.user_ns.get("external_console", None)
                if externalConsole:
                    cdict = externalConsole.window.connections.get(cfile, None)
                    if isinstance(cdict, dict) and "master" in cdict and cdict["master"] is None:
                        #print("found remote connection for %s" % cfile)
                        current, initial = self._merge_session_cache_(cfile, initial)
                    
            # special treatment for objects loaded from NEURON at kernel 
            # initialization time (see extipyutils_client 
            # nrn_ipython_initialization_cmd and the 
            # core.neuron_python.nrn_ipython module)
            
            neuron_symbols = initial & {"h", "ms", "mV"} # may have already been in saved current
            
            current = current | neuron_symbols # set operations ensure unique elements
            
            
            #for v in ("h", "ms", "mV",):
                #if v in initial:
                    #current.add(v)
                    #initial.remove(v)
                    
            # The distinction between initial and current boils down to symbols
            # visible in the workspace table and for which properties are queried
            # (i.e., those in the "current" set) versus the symbols NOT visible
            # in the workspace table and therefore skipped from property query 
            # (thus keeping the whole excercise of updating the workspace table 
            # less demanding)
            
            # will trigger _foreign_namespaces_count_changed_ which at the 
            # moment, does nothing
            self.foreign_namespaces[ns_name] = {"current": current,
                                                "initial": initial,
                                                }
            
        else:    
            #print("\tupdate_foreign_namespace: foreign namespaces:", self.foreign_namespaces)
            #print("\tself.foreign_namespaces[ns_name]['current']", self.foreign_namespaces[ns_name]["current"])
            
            removed_symbols = self.foreign_namespaces[ns_name]["current"] - initial
            #print("\tremoved_symbols", removed_symbols)
            for vname in removed_symbols:
                self.removeRowForVariable(vname, ns = ns_name)
                #self.removeRowForVariable(vname, ns = ns_name.replace("_", " "))
            
            added_symbols = initial - self.foreign_namespaces[ns_name]["current"]
            
            self.foreign_namespaces[ns_name]["current"] -= removed_symbols
            
            self.foreign_namespaces[ns_name]["current"] |= added_symbols
            
            self.foreign_namespaces[ns_name]["current"] -= self.foreign_namespaces[ns_name]["initial"]
            
                
    def clear(self):
        self.cached_vars.clear()
        self.modified_vars.clear()
        self.new_vars.clear()
        self.deleted_vars.clear()
        self.user_ns_hidden.clear()
        self.observed_vars.clear()
        
    def is_user_var(self, name, val):
        """Checks binding of symbol (name) to a hidden variable.
        """
        # see NOTE 2020-11-29 16:29:01
        if name in self.user_ns_hidden:
            return val is not self.user_ns_hidden[name]
        
        return True
    
    def var_observer(self, change):
        #print(f"WorkspaceModel.var_observer: change {change}")
        name = change.name
        displayed_vars_types = self.getDisplayedVariableNamesAndTypes()
        
        if name in self.shell.user_ns:
            if name not in displayed_vars_types:
                self.addRowForVariable(name, self.shell.user_ns[name])
            else:
                self.updateRowForVariable(name, self.shell.user_ns[name])
                
            self.modelContentsChanged.emit()
        
    def pre_execute(self):
        """Updates observed_vars DataBag
        """
        # ensure we observe only "user" variables in user_ns (i.e. excluding the "hidden"
        # ones like the ones used by ipython internally)
        self.cached_vars = dict([item for item in self.shell.user_ns.items() if not item[0].startswith("_") and self.is_user_var(item[0], item[1])])
        

        # need to withhold notifications here
        with self.observed_vars.hold_trait_notifications():
            self.observed_vars.clear()
            
            self.observed_vars.update(self.cached_vars)
        
    def post_execute(self):
        """Updates workspace model AFTER kernel execution.
        Also takes into account matplotlib figures that have been created by
        plt commands at the console
        """
        # NOTE: 2022-03-15 22:05:21
        # check if there is a mpl Figure created in the console (but NOT bound to
        # a user-available identifier)
        
        fig = self.shell.user_ns.get("_", None)
        
        if isinstance(fig, mpl.figure.Figure):
            figures = [v for v in self.cached_vars.values() if isinstance(v, mpl.figure.Figure)]
            if fig not in figures:
                num = fig.number
                assert num in plt.get_fignums()
                self.shell.user_ns[f"Figure{num}"] = fig
                self.observed_vars[f"Figure{num}"] = fig
                if self.mpl_figure_close_callback:
                    fig.canvas.mpl_connect("close_event", self.mpl_figure_close_callback)
                    
                if self.mpl_figure_click_callback:
                    fig.canvas.mpl_connect("button_press", self.mpl_figure_click_callback)
                    
                if self.mpl_figure_enter_callback:
                    fig.canvas.mpl_connect("figure_enter_event", self.mpl_figure_enter_callback)

        # just update the model directly
        self.update()
        
    def _gen_item_for_object_(self, propdict:dict, 
                            editable:typing.Optional[bool] = False, 
                            elidetip:typing.Optional[bool] = False,
                            background:typing.Optional[QtGui.QBrush]=None, 
                            foreground:typing.Optional[QtGui.QBrush]=None) -> QtGui.QStandardItem:
        item = QtGui.QStandardItem(propdict["display"])
        
        ttip = propdict["tooltip"]
        # NOTE: 2021-07-19 11:06:48
        # optionally use elided text for long tooltips
        if elidetip:
            components = ttip.split("\n")
            wspace_name = components[-1]
            w = get_text_width(wspace_name) * 2
            ttip = "\n".join([get_elided_text(s, w) for s in components[:-1]] + [wspace_name])
            
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
    def generateRowContents(self, dataname:str, data:object, namespace:str="Internal") -> typing.List[QtGui.QStandardItem]:
        #print("generateRowContents", dataname, data, namespace)
        obj_props = summarize_object_properties(dataname, data, namespace=namespace)
        #print("generateRowContents obj_props", obj_props)
        return self.genRowFromPropDict(obj_props)
    
    def genRowFromPropDict(self, obj_props:dict,
                                      background:typing.Optional[QtGui.QBrush]=None,
                                      foreground:typing.Optional[QtGui.QBrush]=None) -> typing.List[QtGui.QStandardItem]:
        """Returns a row of QStandardItems
        """
        return [self._gen_item_for_object_(obj_props[key], 
                editable = (key == "Name"), 
                elidetip = (key == "Name"),
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
        if regVarNames is None:
            regVarNames = self.getDisplayedVariableNames()
            
        ndx = None
        
        if len(regVarNames) == 0:
            return ndx
        
        if varname in regVarNames:
            ndx = regVarNames.index(varname)
            
        return ndx

    def getCurrentVarName(self):
        """DEPRECATED
        """
        warnings.warn("Deprecated", DeprecationWarning)
        
        varname = self.currentItemName
        
        if varname is None or (isinstance(varname, str) and len(varname.strip()) == 0):
            if self.parent():
                if hasattr(self.parent(),"workspaceView"):
                    wv = self.parent().workspaceView
                    indexList = wv.selectedIndexes()
                    if len(indexList) == 0:
                        return
                    
                    varname = wv.item(indexList[0].row(),0).text()
                    
                if varname is None or isinstance(varname, str) and len(varname.strip()) == 0:
                    return
                
                if varname not in self.shell.user_ns.keys():
                    return
                
                self.currentItemName = varname
            
        return varname
            
    def updateRowForVariable(self, dataname, data, ns=None):
        # CAUTION This is only for internal workspace, but 
        # TODO 2020-07-30 22:18:35 merge & factor code for both internal and foreign
        # kernels (make use of the ns parameter)
        #
        if ns is None:
            ns = "Internal"
            
        elif isinstance(ns, str):
            if len(ns.strip()) == 0:
                ns = "Internal"
                
        else:
            ns = "Internal"
            
        #print("updateRowForVariable", dataname, data, ns)
        
        row = self.rowIndexForItemsWithProps(Workspace=ns)
        
        #print("updateRowForVariable, row:", row)
        
        items = self.findItems(dataname)

        #print("updateRowForVariable, items", items)
        
        if len(items) > 0:
            row = self.indexFromItem(items[0]).row() # same as below
            #print("updateRowForVariable, row:", row)
            #row = items[0].index().row()
            v_row = self.generateRowContents(dataname, data) # generate model view row contents for existing item
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
        #print("updateRow originalRow as str", self.getRowContents(rowindex, asStrings=True))
        if originalRow is not None:
            #for col in range(self.columnCount()):
            for col in range(1, self.columnCount()):
                # NOTE: 2021-07-28 10:42:17
                # ATTENTION this emits itemChange signal thereby will trigger
                # code for displayed name change
                self.setItem(rowindex, col, newrowdata[col])

    def removeRowForVariable(self, dataname, ns=None):
        if isinstance(ns, str):
            if len(ns.strip()) == 0:
                ns = "Internal"
                
        else:
            ns = "Internal"
            
        row = self.rowIndexForItemsWithProps(Name=dataname, Workspace=ns)
        
        #print("WorkspaceModel.removeRowForVariable data: %s ns: %s row: %s" % (dataname, ns, row))
        if row == -1:
            return
        
        
        if isinstance(row, list):
            for r in row:
                self.removeRow(r)
                
        else:
            self.removeRow(row)
        
    @pyqtSlot()
    def slot_updateTable(self):
        #print("slot_updateTable")
        self.update()
            
    def addRowForVariable(self, dataname, data):
        """CAUTION Only use for data in the internal workspace, not in remote ones.
        """
        #print("addRowForVariable: ", dataname, data)
        v_row = self.generateRowContents(dataname, data) # generate model view row contents
        self.appendRow(v_row) # append the row to the model
        
    def clearTable(self):
        self.removeRows(0,self.rowCount())
        
    def update(self):
        """Updates workspace model.
        Must be called by code that adds/remove/modifies/renames variables 
        in the Scipyen's namespace in order to update the workspace viewer.
        
        Code executed in the main Scipyen's console does not (and SHOULD NOT)
        call this function, as the model is updated automatically by 
        self.observed_vars (via pre_execute and post_execute).
        """
        
        #print(f"WorkspaceModel.update observed_vars: {list(self.observed_vars.keys())}")
        del_vars = [name for name in self.observed_vars.keys() if name not in self.shell.user_ns.keys()]

        self.observed_vars.remove_members(*del_vars)
        
        current_vars = dict([item for item in self.shell.user_ns.items() if not item[0].startswith("_") and self.is_user_var(item[0], item[1])])
        
        self.observed_vars.update(current_vars)
        
        #print(f"WorkspaceModel.update del_vars = {del_vars}")
        
        obsolete_displayed_vars = [n for n in self.getDisplayedVariableNames() if n not in self.shell.user_ns.keys()] # in the internal ws
        
        names_to_remove = set(del_vars) | set(obsolete_displayed_vars)
        
        for name in names_to_remove:
            self.removeRowForVariable(name)

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
        #bg_cols = sb.color_palette("pastel", self._foreign_workspace_count_)
        
        #self._foreign_workspace_count_ += 1
        for varname, props in prop_dicts.items():
            ns_key = props["Workspace"]["display"]
            #ns_key = ns.replace(" ", "_")
            
            vname = varname.replace("properties_of_","")
            
            namespaces = sorted([k for k in self.foreign_namespaces.keys()])
            
            if ns_key not in namespaces:
                continue # FIXME 2020-07-30 22:42:16 should NEVER happen 
            
            ns_index = namespaces.index(ns_key)
            
            items_row_ndx = self.rowIndexForNamedItemsWithProps(vname, Workspace=ns_key)
            
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
                        if r  == -1:
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
        #from core.utilities import standard_obj_summary_headers
        
        if len(kwargs) == 0:
            return range(self.rowCount())

        else:
            if self.rowCount() == 0:
                return -1
            
            allrows = np.arange(self.rowCount())
            allndx = np.array([True] * self.rowCount())
            
            for key, value in kwargs.items():
                key_column = standard_obj_summary_headers.index(key.replace("_", " "))
                
                items_by_key = self.findItems(value, column=key_column)
                
                rows_by_key = [i.index().row() for i in items_by_key]
                
                key_ndx = np.array([allrows[k] in rows_by_key for k in range(len(allrows))])
                
                allndx = allndx & key_ndx
                
            ret = [int(v) for v in allrows[allndx]]
            #print("rowIndexForItemsWithProps ret", ret)
            #ret = list(allrows[allndx])
            
            if len(ret) == 1:
                return ret[0]
            
            elif len(ret) == 0:
                return -1
            
            else:
                return ret
            
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
        #from core.utilities import standard_obj_summary_headers
        name_column = standard_obj_summary_headers.index("Name")
        
        kwargs.pop("Name", None) # make sure we don't index by name twice
        
        allrows = np.arange(self.rowCount())
        allndx = np.array([True] * self.rowCount())
        
        items_by_name = self.findItems(name, column=name_column)
        rows_by_name = [i.index().row() for i in items_by_name] # empty if items is empty
        
        
        if len(kwargs) == 0: # find by name
            if len(items_by_name) > 1:
                return rows_by_name
            
            elif len(items_by_name) == 1:
                return rows_by_name[0]
            
            else: # not found
                return -1
        
        else:
            if len(rows_by_name):
                name_ndx = np.array([allrows[k] in rows_by_name for k in range(len(allrows))])
                
                allndx = allndx & name_ndx
                
                for key, value in kwargs.items():
                    key_column = standard_obj_summary_headers.index(key.replace("_", " "))
                    
                    items_by_key = self.findItems(value, column=key_column)
                    rows_by_key = [i.index().row() for i in items_by_key]
                    
                    key_ndx = np.array([allrows[k] in rows_by_key for k in range(len(allrows))])
                    
                    allndx = allndx & key_ndx
                    
                ret = [int(v) for v in allrows[allndx]]
                #ret = list(allrows[allndx])
                
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
        
        ret = dict([(self.item(row,0).text(), self.item(row,typecol).text()) for row in range(self.rowCount()) if self.item(row,wscol) is not None and self.item(row,wscol).text() == ws])
        
        return ret
            
    def getDisplayedVariableTypes(self, asStrings=True, ws = "Internal"):
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
        
        ret = [self.item(row, typecol).text() if asStrings else self.item(row, typecol) for row in range(self.rowCount()) if self.item(row, wscol).text() == ws]
        
        return ret
                
    def getDisplayedVariableNames(self, asStrings=True, ws="Internal"):
        '''Returns names of variables in the internal workspace, registered with the model.

        Parameter: asStrings (boolean, optional, default True) variable names 
                    are returned as (a Python list of) strings, otherwise 
                    they are returned as Python list of QStandardItems
        '''
        wscol = standard_obj_summary_headers.index("Workspace")
        ret = [self.item(row).text() if asStrings else self.item(row) for row in range(self.rowCount()) if self.item(row, wscol).text() == ws]
        
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
    

