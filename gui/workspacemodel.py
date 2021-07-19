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

from core.traitcontainers import DataBag

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
    windowVariableDeleted = pyqtSignal(int, name="windowVariableDeleted")
    
    def __init__(self, shell, user_ns_hidden=dict(), parent=None):
        #from core.utilities import standard_obj_summary_headers
        super(WorkspaceModel, self).__init__(parent)
        #self.abbrevs = {'IPython.core.macro.Macro' : 'Macro'}
        #self.seq_types = ['list', 'tuple', "deque"]
        #self.set_types = ["set", "frozenset"]
        #self.dict_types = ["dict"]
        #self.ndarray_type = np.ndarray.__name__
        self.currentVarItem = None
        
        self.shell = shell # reference to IPython InteractiveShell of the internal console
        
        #print("mainWindow" in self.shell.user_ns)
        
        self.cached_vars = dict()
        self.modified_vars = dict()
        self.new_vars = dict()
        self.deleted_vars = dict()
        self.user_ns_hidden = dict(user_ns_hidden)
    
        
        # NOTE: 2017-09-22 21:33:47
        # cache for the current var name to allow renaming workspace variables
        # this should be updated whenever the variable name is selected/activated in the model table view
        self.currentVarName = "" # name of currently selected variable
        # NOTE: 2021-06-12 12:11:25
        # cache symbol when the data it is bound to has changed
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
        self.foreign_namespaces.observe(self._foreign_namespaces_count_changed_, names="length")
            
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
        
    def is_user_var(self, name, val):
        """Checks binding of symbol (name) to a hidden variable.
        """
        # see NOTE 2020-11-29 16:29:01
        if name in self.user_ns_hidden:
            return val is not self.user_ns_hidden[name]
        
        return True
            
    def pre_execute(self):
        """Callback from the jupyter interpreter/kernel before executing code
        """
        # see NOTE 2020-11-29 16:29:01 and NOTE: 2020-11-29 16:05:14
        # checks if a new variable reassigns the binding to an already existing 
        # symbol (previously bound to a hidden variable) - so that it can be 
        # restored when user "deletes" it from the workspace
        self.cached_vars = dict([item for item in self.shell.user_ns.items() if not item[0].startswith("_") and self.is_user_var(item[0], item[1])])
        
        #print("pre_execute cached vars", self.cached_vars)
        
        self.modified_vars.clear()
        self.new_vars.clear()
        self.deleted_vars.clear()
        
    @safeWrapper
    def post_execute(self):
        """Callback for the internal inprocess ipython kernel
        """
        # NOTE: 2018-10-07 09:00:53
        # find out what happened to the variables and populate the corresponding
        # dictionaries
        try:
            # FIXME: 2019-09-11 21:46:30
            # when you call del(figure) in the console (Figure being a matplotlib Figure instance)
            # is unbinds the name "figure" in the shell (user) workspace from the Figure instance
            # however pyplot STILL holds a live reference to it (which is only removed
            # after calling plt.close(figure))
            # so just by simply comparing the figure numbers plt knows about, to those
            # of any figures left in the user namespace will flag those figures as newly created
            
            # NOTE 2019-09-11 22:01:42
            # a new figure (created via pyplot, or "plt" interface) will be present in BOTH 
            # user namespace and Gcf.figs (placed there by the plt intereface)
            # but absent from cached_vars
            #
            # conversely, a figure removed from user namespace via del statement
            # will be present in cached_vars AND ALSO in Gcf.figs, if created via
            # plt interface
            
            mpl_figs_in_pyplot = [plt.figure(i) for i in plt.get_fignums()] # a list of figure objects!!!

            mpl_figs_in_ns = [item[1] for item in self.shell.user_ns.items() if isinstance(item[1], mpl.figure.Figure)]
            
            #print("post_execute cached vars", self.cached_vars)
            
            # 1) deleted variables -- present in cached vars but not in the user namespace anymore
            self.deleted_vars.update([item for item in self.cached_vars.items() if item[0] not in self.shell.user_ns])
            
            #print("post_execute deleted vars", self.deleted_vars)
            
            # NOTE: 2020-11-29 16:05:14 check if any of the deleted symbols need 
            # to be rebound to their original variables in self.user_ns_hidden
            # (see NOTE 2020-11-29 16:29:01 below)
            # this also means we can NEVER remove these symbols from the user
            # workspace (which may not be a bad idea, after all)
            vars_to_restore = [k for k in self.deleted_vars.keys() if k in self.user_ns_hidden.keys()]
            #print("post_execute vars_to_restore",vars_to_restore)
            # restore the links between the deleted symbol and the original reference
            for v in vars_to_restore:
                self.shell.user_ns[v] = self.user_ns_hidden[v]
            
            deleted_mpl_figs = [item for item in mpl_figs_in_ns if item not in mpl_figs_in_pyplot]
            
            for item in deleted_mpl_figs:
                self.cached_vars.pop(item, None)
            
            #self.deleted_vars.update(dict_of_mpl_figs_deleted_in_ns)
            #self.deleted_vars.update(deleted_mpl_figs)
            
            #new_mpl_figs = [fig for fig in mpl_figs_in_pyplot if fig not in dict_of_mpl_figs_in_ns.values()]
            new_mpl_figs = [fig for fig in mpl_figs_in_pyplot if fig not in mpl_figs_in_ns]
            
            #print("\npost_execute: new figs",new_mpl_figs)
            
            # NOTE 2020-11-29 16:29:01: 
            # some variables may bear the same name as a loaded module;
            # this is an easy mistake to make, e.g. by loading electrophysiology
            # data and assigning it to a variable named "ephys" - a symbol which
            # is already bound to the module ephys.ephys; the module is still 
            # loaded in sys.module, and has a reference there, but it just becomes
            # unaccessible to the user
            #
            # this happens at interpreter (kernel) level, which cannot prevent it
            # from happening
            #
            # because the original symbol-object binding is contained in
            # self.user_ns_hidden (even if hidden from user's view) we can restore
            # it whem the new symbol-object binding has been removed by the user 
            # (i.e., when user has called "del").
            #
            # NOTE: 2020-11-29 16:35:21:
            # so here we show these new variables bound to an already existing
            # symbol to faciliate user interaction, but thenn we restore them
            # once the user has "deleted" the new binding (NOTE: 2020-11-29 16:05:14)
            new_vars = dict([(i,v) for i, v in self.shell.user_ns.items() if i not in self.cached_vars.keys() and not i.startswith("_") and self.is_user_var(i,v)])
            #new_vars = dict([(i,v) for i, v in self.shell.user_ns.items() if i not in self.cached_vars.keys() and i not in self.user_ns_hidden and not i.startswith("_")])
            
            self.new_vars.update(new_vars)
            
            #print("post_execute new_vars", self.new_vars)
            
            existing_vars = [item for item in self.shell.user_ns.items() if item[0] in self.cached_vars.keys()]
            
            for fig in new_mpl_figs:
                self.new_vars["Figure%d" % fig.number] = fig
                self.shell.user_ns["Figure%d" % fig.number] = fig
                fig.canvas.mpl_connect("close_event", self.shell.user_ns["mainWindow"]._handle_matplotlib_figure_close)
                fig.canvas.mpl_connect("button_press_event", self.shell.user_ns["mainWindow"].handle_mpl_figure_click)
                fig.canvas.mpl_connect("figure_enter_event", self.shell.user_ns["mainWindow"].handle_mpl_figure_enter)
            
            self.modified_vars.update([item for item in existing_vars if not safe_identity_test(item[1], self.cached_vars[item[0]])])
            
            self.cached_vars.update(self.new_vars)
            
            self.cached_vars.update(self.modified_vars) # not really necessary? (vars are stored by ref)
            
            cached_mpl_figs = [item[1] for item in self.cached_vars.items() if isinstance(item[1], mpl.figure.Figure)]
            
            for item in cached_mpl_figs:
                if item not in mpl_figs_in_pyplot:
                    self.cached_vars.pop(item, None)
            
            
            for item in self.deleted_vars.items():
                self.cached_vars.pop(item[0], None)
                if isinstance(item[1], QtWidgets.QWidget) and hasattr(item[1], "winId"):
                    item[1].close()
                    self.windowVariableDeleted.emit(int(item[1].winId()))
            
            self.cached_vars.clear()
            
        except Exception as e:
            traceback.print_exc()
            
        self.updateTable(from_console=True)
        
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
        obj_props = summarize_object_properties(dataname, data, namespace=namespace)
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

        #ret = []
        #for col in range(self.columnCount()):
            #ret.append(self.item(row, col).text() if asStrings else self.item(row, col))
                
        #return ret

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
        if self.currentVarItem is None:
            return None
        
        else:
            try:
                self.currentVarName = self.currentVarItem.text()
                return str(self.currentVarName)
            
            except Exception as e:
                traceback.print_exc()

    def __update_variable_row__(self, dataname, data):
        # FIXME/TODO 2019-08-04 23:55:04
        # make this faster
        
        row = self.indexFromItem(items[0]).row()
        
        originalRow = self.getRowContents(row, asStrings=False)
        
        v_row = self.generateRowContents(dataname, data) # generate model view row contents for existing item
        #v_row = self.generateRowContents(dataname, data) # generate model view row contents for existing item
        
        for col in range(1, self.columnCount()):
            if originalRow is not None and col < len(originalRow) and originalRow[col] != v_row[col]:
                self.setItem(row, col, v_row[col])
        
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
            
        row = self.rowIndexForItemsWithProps(Workspace=ns)
        
        items = self.findItems(dataname)

        if len(items) > 0:
            row = self.indexFromItem(items[0]).row() # same as below
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
            for col in range(self.columnCount()):
                #if col == 0:
                    #self.originalVarName = newrowdata[col].text()
                self.setItem(rowindex, col, newrowdata[col])
                #if originalRow is not None and col < len(originalRow):# and originalRow[col] != newrowdata[col]:
                    
        #for col in range(1, self.columnCount()):
            #if originalRow is not None and col < len(originalRow):# and originalRow[col] != newrowdata[col]:
                #self.setItem(rowindex, col, newrowdata[col])
                

    def removeRowForVariable(self, dataname, ns=None):
        #wscol = standard_obj_summary_headers.index("Workspace")
        
        if isinstance(ns, str):
            if len(ns.strip()) == 0:
                ns = "Internal"
                
        else:
            ns = "Internal"
            
        row = self.rowIndexForItemsWithProps(Name=dataname, Workspace=ns)
        
        if row == -1:
            return
        
        #print("removeRowForVariable data: %s ns: %s row: %s" % (dataname, ns, row))
        
        if isinstance(row, list):
            for r in row:
                self.removeRow(r)
                
        else:
            self.removeRow(row)
        
        #items = self.findItems(dataname)
        
        #if len(items) > 0:
            #row = self.indexFromItem(items[0]).row()
            
            #self.removeRow(row)
            
    @pyqtSlot()
    def slot_updateTable(self):
        self.updateTable(from_console=False)
            
    def addRowForVariable(self, dataname, data):
        """CAUTION Only use for data in the internal workspace, not in remote ones.
        """
        #print("addRowForVariable: ", dataname, data)
        v_row = self.generateRowContents(dataname, data) # generate model view row contents
        #v_row = self.generateRowContents(dataname, data) # generate model view row contents
        self.appendRow(v_row) # append the row to the model
        
    def clearTable(self):
        self.removeRows(0,self.rowCount())
        
    def updateTable(self, from_console:bool = False):
        """CAUTION Updates model table only for vars in internal workspace.
        For data in external kernels (i.e., in the external console) use 
        updateFromExternal
        
        TODO/FIXME 2020-07-30 21:51:49 factor these two under a common logic
        """

        try:
            displayed_vars_types = self.getDisplayedVariableNamesAndTypes()

            if from_console:
                #print("WT update from console")
                # NOTE: 2018-10-07 21:46:03
                # added/removed/modified variables as a result of code executed
                # in the console; 
                #
                # pre_execute and post_execute IPython events
                # are handled as follows:
                #
                # pre_execute always creates a snapshot of the shell.user_ns, in
                # cached_vars; hence, cached_vars represent the most recent state
                # of the user_ns (and hence of the mainWindow.workspace)
                #
                # post_execute checks shell.user_ns against cached_vars and determines:
                #
                # 1) if variables have been deleted from user_ns (but still present
                #       in cached_vars) => deleted_vars
                #
                # 2) if variables present in user_ns have been modified (these have
                #       the same KEYs in cached_vars, but the cached_vars maps these KEYs 
                #       to different objects than the ones they are mapped to in user_ns
                #   => modified_vars
                #
                # 3) if variables have been created in (added to) user_ns (but
                #       missing from cached_vars) => new_vars
                #
                
                # variables deleted via a call to "del()" in the console
                for varname in self.deleted_vars.keys(): # this is populated by post_execute()
                    self.removeRowForVariable(varname)
                    
                #print("modified variables:", self.modified_vars)
                
                # variables modified via code executed in the console
                for item in self.modified_vars.items(): # populated by post_execute
                    self.originalVarName = item[0] # make sure we cache this here
                    self.updateRowForVariable(item[0], item[1])
                self.originalVarName = ""
                
                #print("added variables:", self.new_vars)
                
                # variables created by code executed in the console
                for item in self.new_vars.items(): # populated by post_execute
                    # NOTE: 2020-11-29 16:39:18:
                    # see NOTE 2020-11-29 16:29:01 and NOTE: 2020-11-29 16:35:21
                    if self.is_user_var(item[0], item[1]) and not item[0].startswith("_"):
                        if item[0] not in displayed_vars_types:
                            self.addRowForVariable(item[0], item[1])
                        
                        else:
                            if item[0] in self.cached_vars and not safe_identity_test(item[1], self.cached_vars[item[0]]):
                                self.updateRowForVariable(item[0], item[1])
                                
                self.cached_vars = dict([item for item in self.shell.user_ns.items() if item[0] not in self.user_ns_hidden and not item[0].startswith("_")])
                self.deleted_vars.clear()
                self.new_vars.clear()
                
            else:
                # NOTE 2018-10-07 21:54:45
                # for variables added/modified/deleted from code executed outside
                # the console, unfortunately we cannot easily rely on the event handlers
                # pre_execute and post_execute;
                # therefore the cached_vars does not offer us much help here
                # we rely directly on shell.user_ns instead
                
                # NOTE: 2020-03-06 11:02:01
                # 1. updates self.cached_vars
                # 2. clears self.new_vars 
                # 3. clears self.deleted_vars
                self.pre_execute()
                
                # variables DELETED from workspace or MODIFIED by code executed 
                # outside the console
                for varname in displayed_vars_types:
                    if varname not in self.shell.user_ns: # deleted by GUI
                        self.removeRowForVariable(varname)
                        
                    elif varname in self.cached_vars: # should also be in user_ns
                        if type(self.cached_vars[varname]).__name__ != displayed_vars_types[varname]:
                            self.originalVarName = varname # see NOTE: 2021-06-12 12:11:25
                            self.updateRowForVariable(varname, self.shell.user_ns[varname])
                            
                        elif not safe_identity_test(self.shell.user_ns[varname], self.cached_vars[varname]):
                            self.originalVarName = varname # see NOTE: 2021-06-12 12:11:25
                            self.updateRowForVariable(varname, self.shell.user_ns[varname])
                
                # NOTE: 2021-06-12 12:12:50
                # clear symbol cache, see NOTE: 2021-06-12 12:11:25
                self.originalVarName=""            
                # variables CREATED by code executed outside the console
                for item in self.cached_vars.items():
                    if item[0] not in displayed_vars_types:
                        self.addRowForVariable(item[0], item[1])
                        
                # is this still needed !?!
                self.cached_vars = dict([item for item in self.shell.user_ns.items() if item[0] not in self.user_ns_hidden and not item[0].startswith("_")])

        except Exception as e:
            print("\n\n***Exception in updateTable: ***\n")
            traceback.print_exc()

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
        
            Key is one of 
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

        Parameter: strings (boolean, optional, default True) variable names are 
                            returned as (a Python list of) strings, otherwise 
                            they are returned as Python list of QStandardItems
        '''
        #from core.utilities import standard_obj_summary_headers
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
    

