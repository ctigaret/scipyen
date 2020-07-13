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
    # TODO 2020-07-12 11:23:47 
    # remove the dependency on shell; instead, supply a reference to it as a
    # parameters to the relevant methods
    #
    # alsothiyg thsi also supplied event handlers for the internal shell, so 
    # maybe I should keed this.
    
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
        self.setHorizontalHeaderLabels(standard_obj_summary_headers)
        
        self._foreign_workspace_count_ = -1
        self.foreign_kernel_palette = list(sb.color_palette("pastel", 1))
        
        self.foreign_namespaces = DataBag()
        self.foreign_namespaces.observe(self._foreign_namespaces_changed_, names="length")
            
    def _foreign_namespaces_changed_(self, change):
        print(change["new"])
        #pass
        
    def __reset_variable_dictionaries__(self):
        self.cached_vars = dict([item for item in self.shell.user_ns.items() if item[0] not in self.hidden_vars and not item[0].startswith("_")])
        self.modified_vars.clear()
        self.new_vars.clear()
        self.deleted_vars.clear()
        
    def clear(self):
        self.cached_vars.clear()
        self.modified_vars.clear()
        self.new_vars.clear()
        self.deleted_vars.clear()
        self.hidden_vars.clear()
        
    def pre_execute(self):
        self.cached_vars = dict([item for item in self.shell.user_ns.items() if item[0] not in self.hidden_vars and not item[0].startswith("_")])
        #self.cached_vars.update([item for item in self.shell.user_ns.items() if item[0] not in self.hidden_vars and not item[0].startswith("_")])
        
        self.modified_vars.clear()
        self.new_vars.clear()
        self.deleted_vars.clear()
        
        #cached_figs = [item[1] for item in self.cached_vars if isinstance(item[1], mpl.figure.Figure)]
        #print("\npre_execute: cached figs", cached_figs)
        
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
            
            #mpl_figs_in_ns = [item[1] for item in self.cached_vars.items() if isinstance(item[1], mpl.figure.Figure)]
            mpl_figs_in_ns = [item[1] for item in self.shell.user_ns.items() if isinstance(item[1], mpl.figure.Figure)]
            
            #dict_of_mpl_figs_in_ns = dict([item for item in self.cached_vars.items() if isinstance(item[1], mpl.figure.Figure)])
            #print("\npost_execute: figs in ns", mpl_figs_in_ns)
            
            # 1) deleted variables -- present in cached vars but not in the user namespace anymore
            self.deleted_vars.update([item for item in self.cached_vars.items() if item[0] not in self.shell.user_ns])
            
            #dict_of_mpl_figs_deleted_in_ns = [item for item in dict_of_mpl_figs_in_ns.items() if item[1] not in mpl_figs_in_pyplot]
            
            #deleted_mpl_figs = [item for item in mpl_figs_in_ns if item[1] not in mpl_figs_in_pyplot]
            deleted_mpl_figs = [item for item in mpl_figs_in_ns if item not in mpl_figs_in_pyplot]
            
            #print("\npost_execute: deleted figs", deleted_mpl_figs)
            
            for item in deleted_mpl_figs:
                self.cached_vars.pop(item, None)
            
            #self.deleted_vars.update(dict_of_mpl_figs_deleted_in_ns)
            #self.deleted_vars.update(deleted_mpl_figs)
            
            #new_mpl_figs = [fig for fig in mpl_figs_in_pyplot if fig not in dict_of_mpl_figs_in_ns.values()]
            new_mpl_figs = [fig for fig in mpl_figs_in_pyplot if fig not in mpl_figs_in_ns]
            
            #print("\npost_execute: new figs",new_mpl_figs)
            
            new_vars = [item for item in self.shell.user_ns.items() if item[0] not in self.cached_vars.keys() and item[0] not in self.hidden_vars and not item[0].startswith("_")]
            
            self.new_vars.update(new_vars)
            
            existing_vars = [item for item in self.shell.user_ns.items() if item[0] in self.cached_vars.keys()]
            
            for fig in new_mpl_figs:
                self.new_vars["Figure%d" % fig.number] = fig
                self.shell.user_ns["Figure%d" % fig.number] = fig
                fig.canvas.mpl_connect("close_event", self.shell.user_ns["mainWindow"]._handle_matplotlib_figure_close)
                fig.canvas.mpl_connect("button_press_event", self.shell.user_ns["mainWindow"].handle_mpl_figure_click)
                fig.canvas.mpl_connect("figure_enter_event", self.shell.user_ns["mainWindow"].handle_mpl_figure_enter)
            
            self.modified_vars.update([item for item in existing_vars if not safe_identity_test(item[1], self.cached_vars[item[0]])])
            
            #print("modified vars:", len(self.modified_vars))
            
            self.cached_vars.update(self.new_vars)
            
            self.cached_vars.update(self.modified_vars) # not really necessary? (vars are stored by ref)
            
            #print("\ndeleted_vars", self.deleted_vars)
            #print("\ncached_vars", self.cached_vars)
            cached_mpl_figs = [item[1] for item in self.cached_vars.items() if isinstance(item[1], mpl.figure.Figure)]
            
            #print("\npost_execute: cached figs", cached_mpl_figs)
            
            #print("\npost_execute: cached_vars", [k for k in self.cached_vars.keys()])
            
            for item in cached_mpl_figs:
                if item not in mpl_figs_in_pyplot:
                    self.cached_vars.pop(item, None)
            
            
            for item in self.deleted_vars.items():
                self.cached_vars.pop(item[0], None)
                #print(type(item[1]))
                if isinstance(item[1], QtWidgets.QWidget) and hasattr(item[1], "winId"):
                    item[1].close()
                    self.windowVariableDeleted.emit(int(item[1].winId()))
                    #print(item[0])
                    #wid = int(item[1].winId())
                    #print(wid)
                    #for mapping in self.windows.maps:
                        #mapping.pop(wid, None)
                        
                    #self.windows.pop(wid, None)
            
            self.cached_vars.clear()
            #self.deleted_vars.clear()
            
        except Exception as e:
            #pass
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
        #from core.utilities import (summarize_object_properties,
                                    #standard_obj_summary_headers,
                                    #)

        obj_props = summarize_object_properties(dataname, data, namespace=namespace)
        
        #row = [self._generate_standard_item_for_object_(obj_props[key], editable = (key=="Name")) for key in standard_obj_summary_headers]
        
        return self.generateRowFromPropertiesDict(obj_props)
    
    def generateRowFromPropertiesDict(self, obj_props:dict, background:typing.Optional[QtGui.QBrush]=None, foreground:typing.Optional[QtGui.QBrush]=None):
        """Returns a row of QStandardItems
        """
        return [self._generate_standard_item_for_object_(obj_props[key], editable = (key=="Name"), background=background, foreground=foreground) for key in standard_obj_summary_headers]
        
        
    #def generateRowContents(self, dataname, data):
        #'''   Generates a row in the workspace table view.
        
        #NOTE: memory size is reported as follows:
            #result of obj.nbytes, for object types derived from numpy ndarray
            #result of total_size(obj) for python containers
                #by default, and as currently implemented, this is limited 
                #to python container classes (tuple, list, deque, dict, set and frozenset)
                
            #result of sys.getsizeof(obj) for any other python object
            
            #TODO construct handlers for other object types as well including 
                #PyQt5 objects
                
        #Returns: a row of QStandardItem objects.
        #'''
        #from numbers import Number
        
        #self.currentVarName = dataname # cache this
        
        #row = []

        #dtypestr = ""
        #dtypetip = ""
        #datamin = ""
        #mintip = ""
        #datamax = ""
        #maxtip = ""
        #sz = ""
        #sizetip = ""
        #ndims = ""
        #dimtip = ""
        #shp = ""
        #shapetip = ""
        #axes = ""
        #axestip = ""
        #arrayorder = ""
        #ordertip= ""
        #memsz = ""
        #memsztip = ""
        
        #vname = QtGui.QStandardItem(dataname)
        #vname.setToolTip(dataname)
        #vname.setStatusTip(dataname)
        #vname.setWhatsThis(dataname)
        
        ## NOTE: 2016-03-26 23:18:00
        ## somehow enabling variable name editing from within the workspace view
        ## is NOT trivial, so we disable this for now
        #vname.setEditable(True)
        #row.append(vname) # so that we display at least the data name & type
        
        #tt = type(data).__name__
        #tt = self.abbrevs.get(tt,tt)
        
        #if tt=='instance':
            #tt = self.abbrevs.get(str(data.__class__),
                                  #str(data.__class__))
            
        #vtype = QtGui.QStandardItem(tt)
        #vtype.setToolTip("type: %s" % tt)
        #vtype.setStatusTip("type: %s" % tt)
        #vtype.setWhatsThis("type: %s" % tt)
        #vtype.setEditable(False)
        #row.append(vtype) # so that we display at least the data name & type
        
        #try:
            #if tt in self.seq_types:
                #if len(data) and all([isinstance(v, numbers.Number) for v in data]):
                    #datamin = str(min(data))
                    #mintip = "min: "
                    #datamax = str(max(data))
                    #maxtip = "max: "
                
                #sz = str(len(data))
                #sizetip = "length: "
                
                ##memsz    = str(total_size(data)) # too slow for large collections
                #memsz    = str(sys.getsizeof(data))
                #memsztip = "memory size: "
                
            #elif tt in self.set_types:
                #if len(data) and all([isinstance(v, numbers.Number) for v in data]):
                    #datamin = str(min([v for v in data]))
                    #mintip = "min: "
                    #datamax = str(max([v for v in data]))
                    #maxtip = "max: "
                
                #sz = str(len(data))
                #sizetip = "length: "
                
                #memsz    = str(sys.getsizeof(data))
                ##memsz    = str(total_size(data)) # too slow for large collections
                #memsztip = "memory size: "
                
            #elif tt in self.dict_types:
                #sz = str(len(data))
                #sizetip = "length: "
                
                ##memsz    = str(total_size(data)) # too slow for large collections
                #memsz    = str(sys.getsizeof(data))
                #memsztip = "memory size: "
                
            #elif tt in ('VigraArray', "PictArray"):
                #dtypestr = str(data.dtype)
                #dtypetip = "dtype: "
                
                #if data.size > 0:
                    #try:
                        #if np.all(np.isnan(data[:])):
                            #datamin = str(np.nan)
                            
                        #else:
                            #datamin = str(np.nanmin(data))
                            
                    #except:
                        #pass
                    
                    #mintip = "min: "
                    
                    #try:
                        #if np.all(np.isnan(data[:])):
                            #datamax = str(np.nan)
                        
                        #else:
                            #datamax  = str(np.nanmax(data))
                            
                    #except:
                        #pass
                    
                    #maxtip = "max: "
                    
                #sz    = str(data.size)
                #sizetip = "size: "
                
                #ndims   = str(data.ndim)
                #dimtip = "dimensions: "
                
                #shp = str(data.shape)
                #shapetip = "shape: "
                
                #axes    = repr(data.axistags)
                #axestip = "axes: "
                
                #arrayorder    = str(data.order)
                #ordertip = "array order: "
                
                #memsz    = str(data.nbytes)
                ##memsz    = "".join([str(sys.getsizeof(data)), str(data.nbytes), "bytes"])
                #memsztip = "memory size (array nbytes): "
                
            #elif tt in ('Quantity', 'AnalogSignal', 'IrregularlySampledSignal', 'SpikeTrain', "DataSignal", "IrregularlySampledDataSignal"):
                #dtypestr = str(data.dtype)
                #dtypetip = "dtype: "
                
                #if data.size > 0:
                    #try:
                        #if np.all(np.isnan(data[:])):
                            #datamin = str(np.nan)
                            
                        #else:
                            #datamin = str(np.nanmin(data))
                            
                    #except:
                        #pass
                        
                    #mintip = "min: "
                        
                    #try:
                        #if np.all(np.isnan(data[:])):
                            #datamax = str(np.nan)
                            
                        #else:
                            #datamax  = str(np.nanmax(data))
                            
                    #except:
                        #pass
                    
                    #maxtip = "max: "
                    
                #sz    = str(data.size)
                #sizetip = "size: "
                
                #ndims   = str(data.ndim)
                #dimtip = "dimensions: "
                
                #shp = str(data.shape)
                #shapetip = "shape: "
                
                #memsz    = str(data.nbytes)
                ##memsz    = "".join([str(sys.getsizeof(data)), str(data.nbytes), "bytes"])
                #memsztip = "memory size (array nbytes): "
                
            #elif tt in ('Block', 'Segment'):
                #sz = str(data.size)
                #sizetip = "size: "
                    
                #memsz = str(sys.getsizeof(data))
                #memsztip = "memory size: "
                
            #elif tt == 'str':
                #sz = str(len(data))
                #sizetip = "size: "
                
                #ndims = "1"
                #dimtip = "dimensions "
                
                #shp = '('+str(len(data))+',)'
                #shapetip = "shape: "

                #memsz = str(sys.getsizeof(data))
                #memsztip = "memory size: "
                
            #elif isinstance(data, Number):
                #dtypestr = tt
                #datamin = str(data)
                #mintip = "min: "
                #datamax = str(data)
                #maxtip = "max: "
                #sz = "1"
                #sizetip = "size: "
                
                #ndims = "1"
                #dimtip = "dimensions: "
                
                #shp = '(1,)'
                #shapetip = "shape: "

                #memsz = str(sys.getsizeof(data))
                #memsztip = "memory size: "
                
            ##elif isinstance(data, pd.Series):
            #elif  tt == "Series":
                #dtypestr = "%s" % data.dtype
                #dtypetip = "dtype: "

                #sz = "%s" % data.size
                #sizetip = "size: "

                #ndims = "%s" % data.ndim
                #dimtip = "dimensions: "
                
                #shp = str(data.shape)
                #shapetip = "shape: "

                #memsz = str(sys.getsizeof(data))
                #memsztip = "memory size: "
                
            ##elif isinstance(data, pd.DataFrame):
            #elif tt == "DataFrame":
                #sz = "%s" % data.size
                #sizetip = "size: "

                #ndims = "%s" % data.ndim
                #dimtip = "dimensions: "
                
                #shp = str(data.shape)
                #shapetip = "shape: "

                #memsz = str(sys.getsizeof(data))
                #memsztip = "memory size: "
                
            #elif tt == self.ndarray_type:
                #dtypestr = str(data.dtype)
                #dtypetip = "dtype: "
                
                #if data.size > 0:
                    #try:
                        #if np.all(np.isnan(data[:])):
                            #datamin = str(np.nan)
                            
                        #else:
                            #datamin = str(np.nanmin(data))
                    #except:
                        #pass
                        
                    #mintip = "min: "
                        
                    #try:
                        #if np.all(np.isnan(data[:])):
                            #datamax = str(np.nan)
                            
                        #else:
                            #datamax  = str(np.nanmax(data))
                            
                    #except:
                        #pass
                    
                    #maxtip = "max: "
                    
                #sz = str(data.size)
                #sizetip = "size: "
                
                #ndims = str(data.ndim)
                #dimtip = "dimensions: "

                #shp = str(data.shape)
                #shapetip = "shape: "
                
                #memsz    = str(data.nbytes)
                #memsztip = "memory size: "
                
            #else:
                #vmemsize = QtGui.QStandardItem(str(sys.getsizeof(data)))
                #memsz = str(sys.getsizeof(data))
                #memsztip = "memory size: "
                
            #vdtype   = QtGui.QStandardItem(dtypestr)
            #vdtype.setToolTip("%s%s" % (dtypetip, dtypestr))
            #vdtype.setStatusTip("%s%s" % (dtypetip, dtypestr))
            #vdtype.setWhatsThis("%s%s" % (dtypetip, dtypestr))
            #vdtype.setEditable(False)

            #vmin = QtGui.QStandardItem(datamin)
            #vmin.setToolTip("%s%s" % (mintip, datamin))
            #vmin.setStatusTip("%s%s" % (mintip, datamin))
            #vmin.setWhatsThis("%s%s" % (mintip, datamin))
            #vmin.setEditable(False)

            #vmax = QtGui.QStandardItem(datamax)
            #vmax.setToolTip("%s%s" % (maxtip, datamax))
            #vmax.setStatusTip("%s%s" % (maxtip, datamax))
            #vmax.setWhatsThis("%s%s" % (maxtip, datamax))
            #vmax.setEditable(False)

            #vsize    = QtGui.QStandardItem(sz)
            #vsize.setToolTip("%s%s" % (sizetip, sz))
            #vsize.setStatusTip("%s%s" % (sizetip, sz))
            #vsize.setWhatsThis("%s%s" % (sizetip, sz))
            #vsize.setEditable(False)
                
            #vndims   = QtGui.QStandardItem(ndims)
            #vndims.setToolTip("%s%s" % (dimtip, ndims))
            #vndims.setStatusTip("%s%s" % (dimtip, ndims))
            #vndims.setWhatsThis("%s%s" % (dimtip, ndims))
            #vndims.setEditable(False)

            #vshape   = QtGui.QStandardItem(shp)
            #vshape.setToolTip("%s%s" % (shapetip, shp))
            #vshape.setStatusTip("%s%s" % (shapetip, shp))
            #vshape.setWhatsThis("%s%s" % (shapetip, shp))
            #vshape.setEditable(False)

            #vaxes    = QtGui.QStandardItem(axes)
            #vaxes.setToolTip("%s%s" % (axestip, axes))
            #vaxes.setStatusTip("%s%s" % (axestip, axes))
            #vaxes.setWhatsThis("%s%s" % (axestip, axes))
            #vaxes.setEditable(False)
            
            #vorder   = QtGui.QStandardItem(arrayorder)
            #vorder.setToolTip("%s%s" % (ordertip, arrayorder))
            #vorder.setStatusTip("%s%s" % (ordertip, arrayorder))
            #vorder.setWhatsThis("%s%s" % (ordertip, arrayorder))
            #vorder.setEditable(False)
            
            #vmemsize = QtGui.QStandardItem(memsz)
            #vmemsize.setToolTip("%s%s" % (memsztip, memsz))
            #vmemsize.setStatusTip("%s%s" % (memsztip, memsz))
            #vmemsize.setWhatsThis("%s%s" % (memsztip, memsz))
            #vmemsize.setEditable(False)

            ## data name and type are always present
            #row += [vdtype, vmin, vmax, vsize, vndims, vshape, vaxes, vorder, vmemsize]
            
        #except Exception as e:
            #traceback.print_exc()
            ##print(str(e))

        #return row

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
        
    def updateRowForVariable(self, dataname, data):
        # FIXME/TODO 2019-08-04 23:55:04
        # make this faster
        items = self.findItems(dataname)

        if len(items) > 0:
            row = self.indexFromItem(items[0]).row() # same as below
            #row = items[0].index().row()
            v_row = self.generateRowContents2(dataname, data) # generate model view row contents for existing item
            self.updateRow(row, v_row)
            
            #originalRow = self.getRowContents(row, asStrings=False)
            
            ##v_row = self.generateRowContents(dataname, data) # generate model view row contents for existing item
            
            #for col in range(1, self.columnCount()):
                #if originalRow is not None and col < len(originalRow) and originalRow[col] != v_row[col]:
                    #self.setItem(row, col, v_row[col])
                    
    def updateRowFromProps(self, row, obj_props):
        #originalRow = self.getRowContents(row, asStrings=False)
        v_row = self.generateRowFromPropertiesDict(obj_props)
        self.updateRow(row, v_row)
        #for col in range(1, self.columnCount()):
            #if originalRow is not None and col < len(originalRow) and originalRow[col] != v_row[col]:
                #self.setItem(row, col, v_row[col])
                
    def updateRow(self, rowindex, newrowdata):
        originalRow = self.getRowContents(rowindex, asStrings=False)
        for col in range(1, self.columnCount()):
            if originalRow is not None and col < len(originalRow) and originalRow[col] != newrowdata[col]:
                self.setItem(rowindex, col, newrowdata[col])
                

    def removeRowForVariable(self, dataname):
        items = self.findItems(dataname)
        
        if len(items) > 0:
            row = self.indexFromItem(items[0]).row()
            self.removeRow(row)
            
    def addRowForVariable(self, dataname, data):
        v_row = self.generateRowContents2(dataname, data) # generate model view row contents
        #v_row = self.generateRowContents(dataname, data) # generate model view row contents
        self.appendRow(v_row) # append the row to the model
        
    def clearTable(self):
        self.removeRows(0,self.rowCount())
        
    def updateTable(self, from_console:bool = False):
        """Updates workspace model table
        """
        try:
            displayed_vars = self.getDisplayedVariableNames(asStrings=True)
            
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
                
                #print("deleted variables:", self.deleted_vars)
                
                # variables deleted via a call to "del()" in the console
                for varname in self.deleted_vars.keys():
                    self.removeRowForVariable(varname)
                    
                #print("modified variables:", self.modified_vars)
                
                # variables modified via code executed in the console
                for item in self.modified_vars.items():
                    self.updateRowForVariable(item[0], item[1])
                
                #print("added variables:", self.new_vars)
                
                # variables created by code executed in the console
                for item in self.new_vars.items():
                    if item[0] not in self.hidden_vars and not item[0].startswith("_"):
                        if item[0] not in displayed_vars:
                            self.addRowForVariable(item[0], item[1])
                        
                        else:
                            if item[0] in self.cached_vars and not safe_identity_test(item[1], self.cached_vars[item[0]]):
                                self.updateRowForVariable(item[0], item[1])
                                
                            else:
                                self.removeRowForVariable(item[0])
                        
                self.cached_vars = dict([item for item in self.shell.user_ns.items() if item[0] not in self.hidden_vars and not item[0].startswith("_")])
                self.deleted_vars.clear()
                
            else:
                # NOTE:; 2018-10-07 21:54:45
                # for variables added/modified/deleted from code executed outside
                # the console, unfortunately we cannot easily rely on the event handlers
                # pre_execute and post_execute;
                # therefore the cached_vars does not offer us much help here
                # we rely directly on shell.user_ns instead
                
                # NOTE: 2020-03-06 11:02:01
                # 1. updates self.cached_vars
                # 2. clears self.new_vars and self.deleted_vars
                self.pre_execute()
                
                displayed_vars = self.getDisplayedVariableNames(asStrings=True)
                
                # variables deleted from workspace or modified by code executed 
                # outside the console
                for varname in displayed_vars:
                    if varname not in self.shell.user_ns: # deleted by GUI
                        self.removeRowForVariable(varname)
                        
                    elif varname in self.cached_vars:
                        if not safe_identity_test(self.shell.user_ns[varname], self.cached_vars[varname]):
                            self.updateRowForVariable(varname, self.shell.user_ns[varname])
                            
                # variables created by code executed outside the console
                for item in self.shell.user_ns.items():
                    if item[0] not in self.hidden_vars and not item[0].startswith("_"):
                        if item[0] not in displayed_vars:
                            self.addRowForVariable(item[0], item[1])
                            
                        else:
                            if not safe_identity_test(item[1], self.cached_vars[item[0]]):
                                self.updateRowForVariable(item[0], item[1])
                        
                #print("displayed vars again:", self.getDisplayedVariableNames(asStrings=True))
                        
                self.cached_vars = dict([item for item in self.shell.user_ns.items() if item[0] not in self.hidden_vars and not item[0].startswith("_")])

        except Exception as e:
            traceback.print_exc()
            print("Exception in updateTable")

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
        
        for varname, props in prop_dicts.items():
            items_row_ndx = self.rowIndexForNamedItemsWithProps(varname, Workspace=props["Workspace"])
            
            if (isinstance(items_row_ndx, int) and items_row_ndx == -1) or \
                (isinstance(items_row_ndx, (tuple, list)) and len(items_row_ndx) == 0):
                self._foreign_workspace_count_ += 1
                background = QtGui.QBrush(QtGui.QColor(*[int(255*v) for v in self.foreign_kernel_palette[self._foreign_workspace_count_]]))
                row = self.generateRowFromPropertiesDict(props, background=background)
                self.appendRow(row)
                
            else:
                for row in items_row_ndx:
                    self.updateRowFromProps(row, obj_props)
            
            
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
        
        if len(kwargs == 0):
            return range(self.rowCount())

        else:
            allrows = np.arange(self.rowCount())
            allndx = np.array([True] * self.rowCount())
            for key, value in kwargs.items():
                key_column = standard_obj_summary_headers.index(key.replace("_", " "))
                
                items_by_key = self.findItems(value, column=key_column)
                rows_by_key = [i.index().row() for i in items_by_key]
                
                key_ndx = np.array([allrows[k] in rows_by_key for k in range(len(allrows))])
                
                allndx = allndx & key_ndx
                
            ret = list(allrows[allndx])
            
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
                    
                ret = list(allrows[allndx])
                
                if len(ret) == 1:
                    return ret[0]
                
                elif len(ret) == 0:
                    return -1
                
                else:
                    return ret
                
            else:
                return -1
                
    def getDisplayedVariableNames(self, asStrings=True):
        '''Returns names of variables in the internal workspace, registered with the model.
        Parameter: strings (boolean, optional, default True) variable names are 
                            returned as (a Python list of) strings, otherwise 
                            they are returned as Python list of QStandardItems
        '''
        #from core.utilities import standard_obj_summary_headers
        wscol = standard_obj_summary_headers.index("Workspace")
        ret = [self.item(row).text() if asStrings else self.item(row) for row in range(self.rowCount()) if self.item(row, wscol).text() == "Internal"]
        
        return ret
    

