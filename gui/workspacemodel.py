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

import traceback, typing

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
    
    def __init__(self, shell, hidden_vars=dict(), parent=None):
        #from core.utilities import standard_obj_summary_headers
        super(WorkspaceModel, self).__init__(parent)
        #self.abbrevs = {'IPython.core.macro.Macro' : 'Macro'}
        #self.seq_types = ['list', 'tuple', "deque"]
        #self.set_types = ["set", "frozenset"]
        #self.dict_types = ["dict"]
        #self.ndarray_type = np.ndarray.__name__
        self.currentVarItem = None
        
        self.shell = shell # reference to IPython InteractiveShell os the internal console
        
        self.cached_vars = dict()
        self.modified_vars = dict()
        self.new_vars = dict()
        self.deleted_vars = dict()
        self.hidden_vars = dict(hidden_vars)
    
        
        # NOTE: 2017-09-22 21:33:47
        # cache for the current var name to allow renaming workspace variables
        # this should be updated whenever the variable name is selected/activated in the model table view
        self.currentVarName = "" 
        self.setColumnCount(len(standard_obj_summary_headers))
        self.setHorizontalHeaderLabels(standard_obj_summary_headers) # defined in core.utilities
        
        self._foreign_workspace_count_ = -1
        # TODO/FIXME 2020-07-31 00:07:29
        # low priority: choose pallette in a clever way to take into account the
        # currently used GUI palette - VERY low priority!
        #self.foreign_kernel_palette = list(sb.color_palette("pastel", 1))
        
        self.foreign_namespaces = DataBag()
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
        self.cached_vars = dict([item for item in self.shell.user_ns.items() if item[0] not in self.hidden_vars and not item[0].startswith("_")])
        self.modified_vars.clear()
        self.new_vars.clear()
        self.deleted_vars.clear()
        
    def remove_foreign_namespace(self, txt):
        #print("workspaceModel to remove %s namespace" % txt)
        #if txt in self.foreign_namespaces:
        self.clear_foreign_namespace_display(txt, remove=True)
        #self.foreign_namespaces.pop(txt, None)
            
    def clear_foreign_namespace_display(self, txt, remove=False):
        #print("workspaceModel to clear %s namespace" % txt)
        if txt in self.foreign_namespaces:
            self.foreign_namespaces[txt]["current"].clear()
            ns = txt.replace("_", " ")
            kernel_items_rows = self.rowIndexForItemsWithProps(Workspace=ns)
            
            #print("kernel_items_rows",kernel_items_rows)
            if isinstance(kernel_items_rows, int):
                if kernel_items_rows >= 0:
                    #print("item", self.item(kernel_items_rows,0).text())
                    self.removeRow(kernel_items_rows)
                
            else:
                # must get the row for one item at a time, because the item's row
                # will have changed after the removal of previous rows
                itemnames = [self.item(r,0).text() for r in kernel_items_rows]
                for name in itemnames:
                    r = self.rowIndexForItemsWithProps(Name=name, Workspace=ns)
                    try:
                        self.removeRow(r)
                    except:
                        pass
                    
        if remove:
            self.foreign_namespaces.pop(txt, None)
                    
    def update_foreign_namespace(self, name, val):
        #print("WorkspaceModel.update_foreign_namespace name %s" % name)
        #print("name", name)
        user_ns_shown = set()
        
        if isinstance(val, dict):
            user_ns_shown = val.get("user_ns", set())
            
        elif isinstance(val, (list, set, tuple)):
            user_ns_shown = set([k for k in val])
            
        else:
            raise TypeError("val expected to be a dict or a list; got %s instead" % type(val).__name__)
                            
        first_run = name not in self.foreign_namespaces
        
        if len(user_ns_shown):
            if first_run:
                # special treatment for objects loaded from NEURON at kernel 
                # initialization time (see extipyutils_client 
                # nrn_ipython_initialization_cmd and the 
                # core.neuro_python.nrn_ipython module)
                
                current = set()
                
                for v in ("h", "ms", "mV",):
                    if v in user_ns_shown:
                        current.add(v)
                        user_ns_shown.remove(v)
                
                # will trigger _foreign_namespaces_count_changed_ which at the 
                # moment, does nothing
                self.foreign_namespaces[name] = {"initial": user_ns_shown,
                                                 "current": current}
                
            else:    
                removed_items = self.foreign_namespaces[name]["current"] - user_ns_shown
                for vname in removed_items:
                    self.removeRowForVariable(vname, ns = name.replace("_", " "))
                
                added_items = user_ns_shown - self.foreign_namespaces[name]["current"]
                
                self.foreign_namespaces[name]["current"] -= removed_items
                
                self.foreign_namespaces[name]["current"] |= added_items
                
                self.foreign_namespaces[name]["current"] -= self.foreign_namespaces[name]["initial"]
                
                
    def clear(self):
        self.cached_vars.clear()
        self.modified_vars.clear()
        self.new_vars.clear()
        self.deleted_vars.clear()
        self.hidden_vars.clear()
        
    def pre_execute(self):
        self.cached_vars = dict([item for item in self.shell.user_ns.items() if item[0] not in self.hidden_vars and not item[0].startswith("_")])
        
        self.modified_vars.clear()
        self.new_vars.clear()
        self.deleted_vars.clear()
        
    @safeWrapper
    def post_execute(self):
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
            #mpl_figs_in_pyplot = plt._pylab_helpers.Gcf.figs # this maps int values to figure managers, not figure instances !!!

            # TODO do not delete
            #mpl_figs_in_user_ns = [item for item in self.user_ns.items() if isinstance(item[1], mpl.figure.Figure)]
            ## NOTE that user_ns and cached vars may be different in post_execute
            #mpl_figs_cached = [item for item in self.cached_vars.items() if isinstance(item[1], mpl.figure.Figure)]
            
            ## new figures created via pyplot interface - they're in pyplot Gcf, but not in cached, nor in user ns
            #new_mpl_figs_via_plt = dict(map(lambda x: (x.number, x), [ x for x in mpl_figs_in_pyplot if item not in mpl_figs_cached.values() and item not in mpl_figs_in_user_ns.values()]))
            
            ## new figures created directly via matplotlib API (but still at the console)
            ## they are present in user_ns (put there by your code), but not in cached vars, 
            ## and not (yet) in Gcf; also it doesn't automatically  get a number (this seems
            ## to be managed only via the pyplot interface)
            #new_mpl_figs = [item for item in mpl_figs_in_user_ns if item[1] not in mpl_figs_cached.values() and item[1] not in mpl_figs_in_pyplot.values()]
            
            #if len(mpl_figs_in_pyplot):
                #next_fig_num = max(plt.get_fignums()) + 1
                
            #else:
                #next_fig_num = 1
                
            ## add these to Gcf
            ##  note that figures created directly with mpl API don;t have a canvas yet (Backend)
            #for fig in new_mpl_figs.values():
                #fig.number = next_fig_num
                #next_fig_num += 1
                
                
            
            #print("\npost_execute: figs in pyplot", mpl_figs_in_pyplot)
            
            mpl_figs_in_ns = [item[1] for item in self.shell.user_ns.items() if isinstance(item[1], mpl.figure.Figure)]
            
            # 1) deleted variables -- present in cached vars but not in the user namespace anymore
            self.deleted_vars.update([item for item in self.cached_vars.items() if item[0] not in self.shell.user_ns])
            
            deleted_mpl_figs = [item for item in mpl_figs_in_ns if item not in mpl_figs_in_pyplot]
            
            for item in deleted_mpl_figs:
                self.cached_vars.pop(item, None)
            
            #self.deleted_vars.update(dict_of_mpl_figs_deleted_in_ns)
            #self.deleted_vars.update(deleted_mpl_figs)
            
            #new_mpl_figs = [fig for fig in mpl_figs_in_pyplot if fig not in dict_of_mpl_figs_in_ns.values()]
            new_mpl_figs = [fig for fig in mpl_figs_in_pyplot if fig not in mpl_figs_in_ns]
            
            #print("\npost_execute: new figs",new_mpl_figs)
            
            new_vars = dict([(i,v) for i, v in self.shell.user_ns.items() if i not in self.cached_vars.keys() and i not in self.hidden_vars and not i.startswith("_")])
            
            self.new_vars.update(new_vars)
            
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
        
    def _generate_standard_item_for_object_(self, propdict:dict, editable:typing.Optional[bool] = False, background:typing.Optional[QtGui.QBrush]=None, foreground:typing.Optional[QtGui.QBrush]=None):
        item = QtGui.QStandardItem(propdict["display"])
        item.setToolTip(propdict["tooltip"])
        item.setStatusTip(propdict["tooltip"])
        item.setWhatsThis(propdict["tooltip"])
        item.setEditable(editable)
        
        if isinstance(background, QtGui.QBrush):
            item.setBackground(background)
            
        if isinstance(foreground, QtGui.QBrush):
            item.setForeground(foreground)
        
        return item
    
    @safeWrapper
    def generateRowContents2(self, dataname, data, namespace="Internal"):
        obj_props = summarize_object_properties(dataname, data, namespace=namespace)
        
        return self.generateRowFromPropertiesDict(obj_props)
    
    def generateRowFromPropertiesDict(self, obj_props:dict, background:typing.Optional[QtGui.QBrush]=None, foreground:typing.Optional[QtGui.QBrush]=None):
        """Returns a row of QStandardItems
        """
        return [self._generate_standard_item_for_object_(obj_props[key], editable = (key=="Name"), background=background, foreground=foreground) for key in standard_obj_summary_headers]
        
        
    def getRowContents(self, row, asStrings=True):
        '''
        Returns a list of QStandardItem (or their display text, if strings is True)
        for the given row.
        If row index is not valid, returns the empty string (if strings is True)
        or None
        '''
        
        if row is None or row >= self.rowCount() or row < 0:
            return "" if asStrings else None

        ret = []
        for col in range(self.columnCount()):
            ret.append(self.item(row, col).text() if asStrings else self.item(row, col))
                
        return ret

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
        
        v_row = self.generateRowContents2(dataname, data) # generate model view row contents for existing item
        #v_row = self.generateRowContents(dataname, data) # generate model view row contents for existing item
        
        for col in range(1, self.columnCount()):
            if originalRow is not None and col < len(originalRow) and originalRow[col] != v_row[col]:
                self.setItem(row, col, v_row[col])
        
    def updateRowForVariable(self, dataname, data, ns=None):
        # CAUTION This is only for internal workspace, but 
        # TODO 2020-07-30 22:18:35 merge & factor code for both interna and foreign
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
            v_row = self.generateRowContents2(dataname, data) # generate model view row contents for existing item
            self.updateRow(row, v_row)
            
    def updateRowFromProps(self, row, obj_props, background=None):
        """
        Parameters:
        row = int
        obj_props: dict, see generateRowContents2
        """
        if background is None:
            v_row = self.generateRowFromPropertiesDict(obj_props)
            
        else:
            v_row = self.generateRowFromPropertiesDict(obj_props, background=background)
            
        self.updateRow(row, v_row)
                
    def updateRow(self, rowindex, newrowdata):
        originalRow = self.getRowContents(rowindex, asStrings=False)
        for col in range(1, self.columnCount()):
            if originalRow is not None and col < len(originalRow) and originalRow[col] != newrowdata[col]:
                self.setItem(rowindex, col, newrowdata[col])
                

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
            
    def addRowForVariable(self, dataname, data):
        """CAUTION Only use for data in the internal workspace, not in remote ones.
        """
        #print("addRowForVariable: ", dataname, data)
        v_row = self.generateRowContents2(dataname, data) # generate model view row contents
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
                    self.updateRowForVariable(item[0], item[1])
                
                #print("added variables:", self.new_vars)
                
                # variables created by code executed in the console
                for item in self.new_vars.items(): # populated by post_execute
                    if item[0] not in self.hidden_vars and not item[0].startswith("_"):
                        if item[0] not in displayed_vars_types:
                            self.addRowForVariable(item[0], item[1])
                        
                        else:
                            if item[0] in self.cached_vars and not safe_identity_test(item[1], self.cached_vars[item[0]]):
                                self.updateRowForVariable(item[0], item[1])
                                
                self.cached_vars = dict([item for item in self.shell.user_ns.items() if item[0] not in self.hidden_vars and not item[0].startswith("_")])
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
                            self.updateRowForVariable(varname, self.shell.user_ns[varname])
                            
                        elif not safe_identity_test(self.shell.user_ns[varname], self.cached_vars[varname]):
                            self.updateRowForVariable(varname, self.shell.user_ns[varname])
                            
                # variables CREATED by code executed outside the console
                for item in self.cached_vars.items():
                    if item[0] not in displayed_vars_types:
                        self.addRowForVariable(item[0], item[1])
                        
                    #else: # NOTE: 2020-09-24 11:02:39 this is now redundant
                        #if not safe_identity_test(item[1], self.cached_vars[item[0]]):
                            ## NOTE: This will always fail to detect when a symbol
                            ## that exists in user_ns has been reassigned to a variable
                            ## of a different TYPE. This happens because cached_vars
                            ## contains a snapshot of the user_ns, created AFTER
                            ## the new variable/object has been bound to the same
                            ## symbol.
                            ##
                            ## Hpwever it should work OK when the TYPE is the same
                            ## but its contents have been changed
                            
                            #print("update row for variable", item[0])
                            #self.updateRowForVariable(item[0], item[1])
                            
                        #else:
                            #print("what to do with", item[0])
                       
                # is this still needed !?!
                self.cached_vars = dict([item for item in self.shell.user_ns.items() if item[0] not in self.hidden_vars and not item[0].startswith("_")])

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
            ns = props["Workspace"]["display"]
            ns_key = ns.replace(" ", "_")
            
            vname = varname.replace("properties_of_","")
            
            namespaces = sorted([k for k in self.foreign_namespaces.keys()])
            
            if ns_key not in namespaces:
                continue # FIXME 2020-07-30 22:42:16 should NEVER happen 
            
            ns_index = namespaces.index(ns_key)
            
            items_row_ndx = self.rowIndexForNamedItemsWithProps(vname, Workspace=ns)
            
            if items_row_ndx is None:
                row = self.generateRowFromPropertiesDict(props)
                self.appendRow(row)
                
            elif isinstance(items_row_ndx, int):
                if items_row_ndx == -1:
                    row = self.generateRowFromPropertiesDict(props)
                    self.appendRow(row)
                
                else:
                    self.updateRowFromProps(items_row_ndx, props)
                    
            elif isinstance(items_row_ndx, (tuple, list)):
                if len(items_row_ndx) == 0:
                    row = self.generateRowFromPropertiesDict(props)
                    self.appendRow(row)
                    
                else:
                    for r in items_row_ndx:
                        if r  == -1:
                            row = self.generateRowFromPropertiesDict()
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
        
        ret = dict([(self.item(row,0).text(), self.item(row,typecol).text()) for row in range(self.rowCount()) if self.item(row,wscol).text() == ws])
        
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
    

