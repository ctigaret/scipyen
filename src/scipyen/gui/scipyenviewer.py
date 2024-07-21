# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


"""Superclass for Scipyen viewer windows
"""
import typing, warnings, inspect, sys, platform, os
from dataclasses import MISSING
from abc import (ABC, ABCMeta, abstractmethod,)
from traitlets import Bunch
#from abc import (abstractmethod,)

from qtpy import (QtCore, QtWidgets, QtGui)

has_qdbus = False
try:
    from qtpy import QtDBus
    has_qdbus = True
except:
    has_qdbus = False
    
from qtpy.QtCore import (Signal, Slot, Property,)
# from qtpy.QtCore import (Signal, Slot, QEnum, Property,)
# from PyQt5 import (QtCore, QtWidgets, QtGui, QtDBus)
# from PyQt5.QtCore import (Signal, Slot, QEnum, Q_FLAGS, Property,)

from core.utilities import safeWrapper
# from core import workspacefunctions as wfunc
# from .workspacegui import (WorkspaceGuiMixin, _X11WMBridge_, 
#                            saveWindowSettings, loadWindowSettings)
from .workspacegui import (WorkspaceGuiMixin, saveWindowSettings, loadWindowSettings)
from gui.widgets.spinboxslider import SpinBoxSlider
from gui.workspacemodel import WorkspaceModel
from core import sysutils
from iolib import pictio as pio
from pandas import NA


class ScipyenViewer(QtWidgets.QMainWindow, WorkspaceGuiMixin):
    """Base type for all Scipyen viewers.
    
    Includes common functionality for all viewer classes defined in Scypien.
    
    Inherits from WorkspaceGuiMixin which provides accesss to the Scipyen's 
    workspace and, indirectly, to the management of Qt and non-Qt settings 
    (through inheritance from ScipyenConfigurable)
    
    Derived classes:
    -----------------
    DataViewer, MatrixViewer, ScipyenFrameViewer, TableEditor, TextViewer, XMLViewer
    
    Developer information:
    -----------------------
    As a minimum, subclasses of ScipyenViewer must:
    
    1) define a :class: attribute named "viewer_for_types", set to a tuple or
        list of python data types supported by the viewer.

        Viewers also support sequences of data (list, tuple); the objects in the 
        sequence must be of one of the types specified here.

        This attribute is mostly for the benefit of Scipyen's mechanism of 
        choosing an appropriate viewer for an object in the workspace, but it 
        can be used by the viewer itself to determine what to do with the "data"
        passed to its constructor.
        
    
    2) define a :class: attribute called "view_action_name" set to a str that 
        gives the name for the menu item invoked to display a variable using this
        viewer. Scipyen will use this attribute to generate a menu item in the
        Workspace context menu. 
        
        NOTE: The Workspace context is invoked by single click of the right mouse
        button on a selected variable name in Scipyen "User variables" tab.
    
    2) implement the following abstract methods:
    
    _set_data_(data:object) -- sets up the actual display of data by the viewer's
        widgets (this may involve populating a custom data model specific
        to the viewer type and/or set).
        
        NOTE: ScipyenViewer holds a reference to the displayed data in the 
        attribute "_data_", but this mechanism can be superceded in the derived
        type.
    
    _configureUI_() -- configures specific GUI widgets and menus
        
         ATTENTION: If the viewer inherits Qt widgets and actions defined in a
        QtDesigner *.ui file (loaded with uic.loadUiType()) then this function
        must call self.setupUi() very early.
    
    If there are viewer type-specific settigns that need to be made persistent
    across sessions then the following abstract mthods also need to be implemented:
    
        saveViewerSettings() -- saves viewer class-specific settings
    
        loadViewerSettings() -- loads viewer class-specific settings
        
    The other methods may be reimplemented in the derived classes.
    
    The python data types that the viewer subclass is specialized for, are
    specified in the class attribute "viewer_for_types". This attribute is a 
    tuple or list of python types. 
    
    The same data type may be handled by more than one type of viewers, but one
    of these is the "preferred" one.
    
    When several viewer types can handle the same data type Scipyen assigns 
    priorities based on the order in which the data types are contained in the 
    "viewer_for_types" attribute.
    
    The viewer type where the data type occurs at index 0 in the viewer_for_types
    (i.e. is the first element) is the viewer with the highest priority, and so 
    on.
    
    Viewer types where a data type has the same index in their "viewer_for_types"
    attribute are prioritized in increasing alphabetical order of the viewer types.
    
    For example, a (2D) numpy.ndarray may be displayed in MatrixViewer, as well 
    as in TableEditor. 
    
    If numpy.ndarray if the first element in TableEditor.viewer_for_types
    but has a higher index in MatrixViewer.viewer_for_types then Scipyen will 
    "prefer" the TableEditor to display the array when the user double clicks the
    left mouse buttom on the array name in the "User variables" tab.
    
    If, however, numpy.ndarray occurs at the same index in the "viewer_for_types"
    attribute of both MatrixViewer and TableEditor, then Scipyen will use
    MatrixViewer.
    
    The other available viewer types can be invoked by menu items generated by
    Scipyen automatically according to the contents of the "viewer_for_types"
    attribute of the viewer classes; the names of these menu items are set by
    the value of the "view_action_name" attribute.
    
    DataViewer has a special place. It has been designed to display tree-like
    data structures (e.g. dict and derived types) but can also display any python 
    object that has a "__dict__" attribute. Therefore, the dict and derived types
    shuld be the first elements in DataViewer.viewer_for_types. In this way, other 
    data types for which there exists a specialized viewer will be displayed, 
    by default, in that specialized viewer, instead of DataViewer.
    """
    sig_activated           = Signal(int, name="sig_activated")
    sig_closeMe             = Signal()
    
    # tuple of 2-tuples (python type, priority)
    # if you don;t want this to be registered as a viewer, then make this attribute empty
    viewer_for_types = {object:0}
    view_action_name = None
    
    def __init__(self, data: object = None, parent: (QtWidgets.QMainWindow, type(None)) = None, 
                 ID:(int, type(None)) = None, win_title: (str, type(None)) = None, 
                 doc_title: (str, type(None)) = None, 
                 deleteOnClose:bool=False, **kwargs):
        """Constructor.
        
        Sets up attributes common to all Scipyen's viewers.
        
        Parameters:
        ----------
        
        data: object or None (default) - the data displayed in the viewer
        
        parent: QMainWindow or None (default) - the parent window 
        
            When parent is scipyen's MainWindow (type name ScipyenWindow) then 
            this also gets assigned to the '_scipyenWindow_' attribute, which:
            
            * gives access to the user (shell) workspace
            
            * indicates that this QMainWindow instance is a direct "client" of 
            scipyen app
            
            When a QMainWindow that is NOT scipyen's main window, this indicates
            it being a client of that window (typically, a scipyen sub-app, e.g.
            LSCaT)

        win_title: str or None (default). The display name of the viewer, to be 
            used as part of the window title according to the pattern
            "document - window". 
            
            When None (default), the display name of the viewer will be set to
            the class name of the viewer and the window ID as a suffix.
            
        doc_title: str or None (default). The display name of the data, to be 
            used as part of the window title according to the pattern
            "document - window". 
            
            When None (the default) the window title will contain only the
            viewer name suffixed with the window ID.
    
        deleteOnClose: When True, informs the parent that the this instance of
            viewer should be removed (deleted) from the window management
            attributes of the owner. 
            Default is False.
    
            NOTE: In this context, "deleting" just removes the symbol bound to 
            the python object (viewer instance). The object may still lurk
            around in memory until the garbage collector wipes it out.
        
        *args, **kwargs: variadic argument and keywords specific to the constructor of the
            derived subclass.
        """
        # print(f"ScipyenViewer<{self.__class__.__name__}>.__init__ data: {type(data).__name__}")
        # print(f"ScipyenViewer<{self.__class__.__name__}>.__init__")
        if sys.platform == "win32" or os.name == "nt" or platform.uname().system == "Windows":
            parent = None
            
        # NOTE: 2024-04-17 11:53:29
        # fixes viewer window stacking when running on Plasma 6 Wayland 
        # session
        # >>> NOTE <<< you still get the "qt.qpa.wayland: Wayland does not support QWindow::requestActivate()"
        # warnings at the system console, though ⌢
        elif sys.platform == "linux" and os.getenv("XDG_SESSION_TYPE").lower() == "wayland":
            parent = None
            
        super().__init__(parent)
        WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, on=False)
        self._docTitle_ = doc_title
        self._winTitle_ = win_title # force auto-set in update_title()
        # self._winTitle_ = None # force auto-set in update_title()
        self._custom_viewer_name_ = None
        
        # NOTE: 2023-01-22 11:14:42
        # A free-format state - stores volatile variables (that depend on the
        # specifics of the data shown in the viewer)
        # It is up to the subclass to manage its contents.
        self._state_ = Bunch() # TODO - not used yet!!!

        self._linkedViewers_ = list()
        
        self._data_ = None # holds a reference to data!
        
        # NOTE: 2023-01-08 00:54:17
        # nothing to do with WA_DeleteOnClose; this flags whether the main window
        # should remove the symbol bound to this instance from the user workspace,
        # once the window was closed
        self._delete_on_close_ = deleteOnClose 
        
        # NOTE: 2023-01-07 23:52:06
        # dirty hack to restore global menu after the window is closed (but not
        # deleted)
        # 
        # The problem:
        # When run in a KDE environment with global appmenu service running, the 
        # menu bar of any ScipyenViewer window is shown in the global menu (top of
        # Desktop) upon its first initialization.
        #
        # If the window is then closed (but neither its Qt/C++ side is deleted, 
        # nor its Python/sip wrapper binding - i.e., the symbol to which this 
        # sip wrapper is bound remains in scope) the window's menu is taken out 
        # from the global appmenu(*) - as expected, I guess.
        #
        # The actual problem is that when the window is shown again (e.g. by 
        # calling any of the show(), setVisible(),  raise_(), activateWindow()
        # methods) its menubar is not shown again in the global menu
        # 
        # *) or the "system-wide menu bar"
        
        self._global_menu_service_ = None
        
        # if not QtWidgets.qApp.testAttribute(QtCore.Qt.AA_DontUseNativeMenuBar):
        if not QtWidgets.QApplication.instance().testAttribute(QtCore.Qt.AA_DontUseNativeMenuBar):
            # if "startplasma" in sysutils.get_desktop() or "KDE" in sysutils.get_desktop("desktop"):
            if sysutils.is_kde_x11() and has_qdbus:
                appMenuServiceNames = list(name for name in QtDBus.QDBusConnection.sessionBus().interface().registeredServiceNames().value() if "AppMenu" in name)
                
                if len(appMenuServiceNames):
                    self._global_menu_service_ = appMenuServiceNames[0]
        
        # NOTE: 2019-11-09 09:30:38
        # _data_var_name_ is either None, or the symbol bound to the data in user's namespace
        # 
        # Used only when data has been loaded via a QAction (i.e. menu item) or
        # following a button click and is the symbol to which the displayed data 
        # is bound, in the workspace.
        # 
        # When given (and indeed bound to the displayed data) this can be used 
        # to refresh the data after it was modified
        # 
        # TODO: 2022-11-05 12:02:52 
        # implement a traitlets/observable mechanism for this purpose
        self._data_var_name_ = None

        if isinstance(ID, int):
            self._ID_ = ID
            
        else:
            self._ID_  = int(self.winId()) # this is the wm ID of the window
            
        # NOTE: 2021-09-16 12:26:09
        # This SHOULD be implemented in the derived class
        self._configureUI_()
        self._menu_bar_ = self.menuBar()
        self.windowHandle().visibilityChanged.connect(self._slot_visibility_changed)
        
        self.loadSettings() # inherited from ScipyenConfigurable (via WorkspaceGuiMixin)
            
        
        # NOTE: 2021-08-17 12:59:02
        # setData ALMOST SURELY needs the ui elements to be initialized - hence 
        # it is called here, AFTER self._configureUI_()
        if data is not None:
            # NOTE: 2022-01-17 12:39:49 this will call _set_data_
            # subclasses can override this by implementing their own setData()
            # see e.g., SignalViewer
            self.setData(data = data, doc_title = doc_title)
            
        else:
            self.update_title(win_title = win_title, doc_title = doc_title)
            
        # NOTE: 2023-01-08 21:21:20
        # int(winId()) is the same for QMainWindow, QWindow, AND
        # the WM_ID reported by wmctrl 
        self._wm_id_ = int(self.winId())
        
        self._app_menu_ = self.getAppMenu()
        
    #def mousePressEvent(self, evt):
        #if sys.platform == "win32":
            #self.activateWindow()
        #super().mousePressEvent(evt)

    def requestActivate(self):
        """workaround wayland"""
        if os.getenv("XDG_SESSION_TYPE").lower() == "wayland":
            return
        super().requestActivate()
        

    def activateWindow(self):
        if sys.platform== "win32":
            self.windowHandle().raise_()
        else:
            if os.getenv("XDG_SESSION_TYPE").lower() == "wayland":
                return
            super().activateWindow()
        
    def getAppMenu(self):
        if self._global_menu_service_ == "com.canonical.AppMenu.Registrar":
            service_name = self._global_menu_service_
            service_path = "/com/canonical/AppMenu/Registrar"
            interface = "com.canonical.AppMenu.Registrar"
            dbusinterface = QtDBus.QDBusInterface(service_name, service_path,
                                                  interface)
            dbusinterface.setTimeout(100)
            
            # v = QtCore.QVariant(self._wm_id_)
            v = QtCore.QVariant(int(self.winId()))
            
            if v.convert(QtCore.QVariant.UInt): # NOTE: 2023-01-08 23:10:14 MUST convert to UInt
                # NOTE: 2023-01-08 22:58:38
                # When all OK, result should be a list with:
                # • str: address of the connection on DBus (e.g.: ':1.383')
                # • str: The path to the object which implements the com.canonical.dbusmenu interface.
                #           (e.g., /MenuBar/4') as a str (NOT QDBusObjectPath!) 
                #
                #       If you use QDBusViewer, the address points to /MenuBar/x 
                #       where x is an int >= 1, and it has the following interfaces:
                #       ∘ com.canonical.dbusmenu (AHA!)
                #       ∘ the next three are generic and present on all objects on DBus
                #           ▷ org.freedesktop.DBus.Properties
                #           ▷ org.freedesktop.DBus.Introspectable
                #           ▷ org.freedesktop.DBus.Peer
                #
                result = dbusinterface.call("GetMenuForWindow", v).arguments()
            
                if len(result) == 1: # oops!
                    # warnings.warn(result[0])
                    return
            
                    # address, objpath = result
            
                return result
            
    def update_title(self, doc_title: typing.Optional[str] = None, 
                     win_title: typing.Optional[str] = None, 
                     enforce: bool = False):
        """Sets up the window title according to the pattern document - viewer.
        
        Parameters:
        -----------
        doc_title: str or None (default): display name of the data.
            When not None or non-empty, will replace the current display name
            of the data. Otherwise, the display name of the data is left unchanged
            (even if it is None or an empty string).
            
            When None, it will remove the data display name from the window title.
        
        win_title: str or None (default): display name of the viewer.
            When not None, or non-empty, will replace the current display name
            of the viewer, depending on the "enforce" parameter.
        
        enforce: bool (default: False) Used when win_title is None or an empty 
            string.
        
            When True, the display name of the viewer will be set to the canonical 
            name, even if the displayed viewer name had been previouly set to
            something else.
            
            When False (the default) the display name of the viewer will not be
            changed from its previous value (unless it is None, or an empty string)
            
        NOTE: a str is considered "empty" when it has a zero length after
        stripping all its leading and trailing whitespace.
            
        Developer information:
        ----------------------
            The canonical name is the viewer's class name suffixed with the 
            viewer's ID, or the name (symbol) that is bound to the viewer 
            variable in the user's namespace.
            
            str objects with zero length after stripping leading and trailing
            whitespace are treated as is they were None.
        
        """
        # print(f"{self.__class__.__name__} update_title win_title {win_title}")
        if isinstance(doc_title, str) and len(doc_title.strip()):
            self._docTitle_ = doc_title
            
        if isinstance(win_title, str) and len(win_title.strip()):
            # user-imposed viewer title
            self._winTitle_ = win_title
            self._custom_viewer_name_ = win_title
            
        if not isinstance(self._winTitle_, str):
            self._winTitle_ = self.__class__.__name__
            
        elif len(self._winTitle_.strip()) == 0:
            self._winTitle_ = self.scipyenWindow.applicationName
            
        if isinstance(self._docTitle_, str) and len(self._docTitle_.strip()):
            self.setWindowTitle("%s - %s" % (self._docTitle_, self._winTitle_))
            
        else:
            self.setWindowTitle(self._winTitle_)
            
    @abstractmethod
    def setDataDisplayEnabled(self, value):
        """Enable/disable the central data display widget.
        Abstract method; it must be implemented in subclasses, which have full
        control if and how a central data display widget is implemented.
        """
        w = getattr(self, "viewerWidget", None)
        if w:
            w.setEnabled(value is True)
            w.setVisible(value is True)
            
    @abstractmethod
    def _configureUI_(self):
        """Custom GUI initialization.
        Abstract method, it must be implemented in the derived :class:.
        
        Required when specifc GUI elements are introduced to the viewer's
        instance.
        
        CAUTION: The function needs to call self.setupUi() early, if the viewer
        inherits from a QtDesigner :class: generated from an  *ui file and loaded
        by loadUiType().
        """
        pass
    
    def view(self, data: (object, type(None)), doc_title: (str, type(None)) = None, *args, **kwargs):
        """Set the data to be displayed by this viewer.
        NOTE: Should be reimplemented in the derived :class:.
        In the derived class, the function binds the data to the actual data
        model used by the concrete viewer :class:.
        In addition, the implementation may choose to set the doc title and other
        properties of the viewer based on the data passed to this function.
        """
        self.setData(data, doc_title=doc_title, *args, **kwargs)
        
    def _check_supports_parameter_type_(self, value):
        def __check_val_type_is_supported__(val):
            mro = inspect.getmro(type(value))
            # types = list(v[0] for v in self.viewer_for_types)
            types = list(self.viewer_for_types)
            
            return any(t in types for t in mro)
            
            # return isinstance(value, tuple(self.viewer_for_types.keys())) or any([t in type(value).mro() for t in tuple(self.viewer_for_types.keys())])
            
        if isinstance(value, (tuple, list)):
            return all(__check_val_type_is_supported__(v) for v in value)
        else:
            return __check_val_type_is_supported__(value)
        
    def setData(self, *args, **kwargs):
        """Generic function to set the data to be displayed by this viewer.
        
        Checks that data is one of the supported types, or inherits from one of
        the supported types.
        
        Sets up the window title based on doc_title.
        
        May/should be reimplemented in the derived viewer type.
        
        Parameters:
        ----------
        data: a python object; its type depends of the types supported by
            the drived viewer class
            
        doc_title: str = data name to be shown as part of the window title
        
        Variadic named parameters (kwargs):
        ----------------------------------
        get_focus: bool Optional default False; 
            When True, the window will be given focus.
            When False (the default) an already visible viewer window is kept as
            is (e.g. behind other windows) - useful when the windowing system of 
            the operating system does not implement a focus stealing mechanism.
            
            Subclasses can enforce their own behaviour by reimplementing this
            method.
            
        
        uiParamsPrompt:bool, default False;l when True, a dialog asking for 
            further parameters is shown (if the viewer supports it)
        """
        
        # NOTE: 2020-09-25 10:35:34
        # 
        # This function does the following:
        #
        # 1. delegates to _set_data_(...) -- which does nothing here and SHOULD
        #   be reimplemented (see below).
        #
        # 2. sets up the window title
        #
        # 3. makes the window visible and optionally brings it into focus
        #
        # For a consistent behaviour, subclasses MUST define _set_data_() in order 
        # to set up their own instance variables and data model according to 
        # their deisgned functionality.
        #
        # Subclasses may also reimplement this method if necessary, but then
        # call super().setData(...) from within their own setData()
        #
        
        uiParamsPrompt = kwargs.pop("uiParamsPrompt", False)
        
        if uiParamsPrompt:
            # TODO 2023-01-18 08:48:13
            pass
            # print(f"{self.__class__.__name__}.setData uiParamsPrompt")
            
        if len(args):
            if "DataViewer" not in self.__class__.__name__:
                if len(self.viewer_for_types) and not any([self._check_supports_parameter_type_(a) for a in args]):
                    raise TypeError("Expecting one of the supported types: %s" % " ".join([s.__name__ for s in self.viewer_for_types]))
            
        get_focus = kwargs.get("get_focus", False)
        
        doc_title = kwargs.get("doc_title", None)
        
        # NOTE: 2020-09-25 10:28:59 make sure that the derived type handles
        # doc_title appropriately - see e.g. SignalViewer
        if isinstance(doc_title, str) and len(doc_title.strip()):
            self._docTitle_ = doc_title 
            
        else:
            self._docTitle_ = None
        
        self.update_title(doc_title = doc_title, win_title=self._winTitle_)
        
        # print(f"ScipyenViewer<{self.__class__.__name__}>.setData")
        
        self._set_data_(*args, **kwargs)
        
        #print(f"In ScipyenViewer<{self.__class__.__name__}>.setData(): is visible: {self.isVisible()}")
        
        if not self.isVisible():
            self.setVisible(True)
        
        if get_focus:
            self.activateWindow()
            
            #self.show()
        
    @abstractmethod
    def _set_data_(self, data: object, *args, **kwargs):
        """Must implement in the subclass
        """
        pass
    
    @property
    def ID(self):
        """An unique ID for this viewer.
        Do NOT confuse with the following available "id"s:
        • python's id (objetc identofier, typically the memory address in CPython)
        • self.winId() which is a sip voidptr to the QMainWindow
        • the pointer to the window manager window handler (e.g., a QWindow)
        """
        return self._ID_
    
    @ID.setter
    def ID(self, val: int):
        """Sets the window ID.
        
        If the viewer does not have a custom display name this will also update
        the window title.
        
        Parameters:
        -----------
        val: int
        """
        self._ID_ = val
        
        if self._custom_viewer_name_ is None or (isinstance(self._custom_viewer_name_, str) and len(self._custom_viewer_name_.strip()) == 0):
            self.update_title()
            
    @property
    def winTitle(self):
        """The prefix of the window title.
        
        This is the initial string in the window title, used in common regardless
        of the document's own name (typically, this is the name of the viewer's 
        type).
        
        This property also has a setter.
        """
        return self._winTitle_
    
    @winTitle.setter
    def winTitle(self, value: (str, type(None)) = None):
        """Sets up a custom display name for the viewer.
        
        Calls self.update_title()
        
        Parameters:
        ----------
        value: str or None (default). When None, the display name of the viewer
            will revert to the canonical name (see update_title()).
        """
        if not isinstance(value, (str, type(None))):
            raise TypeError("Expecting a str, or None; got %s instead" % type(value.__name__))
        
        self.update_title(win_title = value, enforce=True)
        
            
    @property
    def docTitle(self):
        """The document-specific part of the window title (display name of data).
        
        This is typically, but not necessarily, the variable name of the data 
        displayed in the viewer i.e., the symbolic name that the data is bound
        to, in Scipyen's workspace (user's namespace).
        
        This property also has a setter.
        """
        return self._docTitle_
    
    @docTitle.setter
    def docTitle(self, value: (str, type(None)) = None):
        """Sets the display name of the data.
        
        This is the "document" part of the pattern "document - window" used in the window title.
        
        Parameters:
        ----------
        value: str or None (default)
        
            When None or an empty str, the data display name will be removed from
            the window title.
            
            Calls self.update_title()
        """
        if not isinstance(value, (str, type(None))):
            raise TypeError("Expecting a str, or None; got %s instead" % type(value.__name__))
        
        self.update_title(doc_title=value)
        
    def resetTitle(self):
        """Resets the window title.
        
        Removes the data display name from the window title and reverts the 
        viewer display name to its canonical value.
        
        Calls self.update_title()
        """
        
        self.update_title(doc_title = None, win_title = None, enforce = True)
        
    def closeEvent(self, evt:QtCore.QEvent):
        """All viewers in Scipyen should behave consistently.
        However, this may by reimplemented in derived classes.
        """
        # print(f"ScipyenViewer<{self.__class__.__name__}>.closeEvent {self.winTitle}: isTopLevel {self.isTopLevel}")
        
        self.saveSettings()
        # NOTE: 2021-07-08 12:07:35
        # also de-register the viewer with Scipyen's main window, if this viewer
        # is NOT a client (child) of another Scipyen app (e.g. LSCaTWindow)
        
        if self.isTopLevel:
            if self._delete_on_close_ or self.appWindow.autoRemoveViewers:
                if any([v is self for v in self.appWindow.workspace.values()]):
                    self.appWindow.deRegisterWindow(self) # this will also save settings and close the viewer window
                    self.appWindow.removeFromWorkspace(self, by_name=False)
                    
        if self.close():
            # NOTE: 2023-01-08 23:42:22
            # It is graceful to unregister with the global menu via DBus, 
            # if/when it does exist
            self._deregister_menuBar_()
            self.sig_closeMe.emit()
            evt.accept()
        
    def event(self, evt:QtCore.QEvent):
        """Generic event handler
        NOTE: This can be reimplemented in the derived :class:
        """
        evt.accept()
            
        if evt.type() in (QtCore.QEvent.FocusIn, QtCore.QEvent.WindowActivate):
            self.sig_activated.emit(self.ID)
            return True

        return super().event(evt)
    
    @Slot(QtGui.QWindow.Visibility)
    def _slot_visibility_changed(self, val):
        if hasattr(self, "_wm_id_") and self._wm_id_ != int(self.winId()):
            if self._global_menu_service_ == "com.canonical.AppMenu.Registrar":
                self._restore_menuBar_()
                
    def _deregister_menuBar_(self):
        if self._app_menu_ is not None and self._global_menu_service_ == "com.canonical.AppMenu.Registrar":
            service_name = self._global_menu_service_
            service_path = "/com/canonical/AppMenu/Registrar"
            interface = "com.canonical.AppMenu.Registrar"
            dbusinterface = QtDBus.QDBusInterface(service_name, service_path,
                                                interface)
            dbusinterface.setTimeout(100)
            
            old_v = QtCore.QVariant(self._wm_id_)
            
            if old_v.convert(QtCore.QVariant.UInt):
                reply = dbusinterface.call("UnregisterWindow", old_v)
                
    def _restore_menuBar_(self):
        """Hack to restore the window's menubar in the desktop's global menu.
        
        Only necessary when running Scipyen in a windowing system / desktop
        environment that provides such service, such as GNOME AND KDE on UN*X.
        
        """
        currentAppMenu = self.getAppMenu()
        
        if self._app_menu_ is None:
            # nothing to restore
            return
        
        if currentAppMenu is None:
            if self._global_menu_service_ == "com.canonical.AppMenu.Registrar":
                service_name = self._global_menu_service_
                service_path = "/com/canonical/AppMenu/Registrar"
                interface = "com.canonical.AppMenu.Registrar"
                dbusinterface = QtDBus.QDBusInterface(service_name, service_path,
                                                    interface)
                dbusinterface.setTimeout(100)
                
                old_v = QtCore.QVariant(self._wm_id_)
                new_v = QtCore.QVariant(int(self.winId()))
                
                if old_v.convert(QtCore.QVariant.UInt) and new_v.convert(QtCore.QVariant.UInt):
                    # deregister old WM window ID, then register the new one
                    # to the same DBus object path (i.e. dbusmenu instance)
                    dereg_reply = dbusinterface.call("UnregisterWindow", old_v)
                    newreg_reply = dbusinterface.call("RegisterWindow", new_v, QtDBus.QDBusObjectPath(self._app_menu_[1]))
    
    @Slot()
    @safeWrapper
    def slot_refreshDataDisplay(self):
        """Triggeres a refresh of the displayed information.
        Typical usage is to connect it to a signal emitted after data has been
        modified, and implies two things:
        
        1. appWindow is a reference to Scipyen MainWindow instance
        2. the data displayed in the viewer is defined in Scipyen's workspace
           (a.k.a. the user's workspace)
           
        e.g.:
        
        from core.workspacefunctions import getvarsbytype
        
        if isinstance(self._data_var_name_, str):
            data_vars = getvarsbytype(self.viewer_for_types, ws = self._scipyenWindow_.workspace)
            
            if len(data_vars) == 0:
                return
            
            if self._data_var_name_ not in data_vars.keys():
                return
            
            data = data_vars[self._data_var_name_]
            
            self.setData(data)
        
        NOTE: Must be implemented in the derived subclass.
        """
        pass
            
class ScipyenFrameViewer(ScipyenViewer):
    """Base type for Scipyen viewers that handle data "frames".
    
    This should be inherited by viewers for data that is organized, or can be 
    sliced, in "frames","sweeps" or "segments", and display one frame (sweep or 
    segment) at a time.
    
    ScipyenFrameViewer inherits from ScipyenViewer and supplements it with code
    (attributes and abstract methods) for managing data frames.
    
    The abstract methods defined in ScipyenViewer must still be implemented in
    the derived types
    
    ScipyenFrameViewer also defines the Qt signal frameChanged, which should be
    emitted by the implementation of currentFrame setter method.
    
    Examples:
    
    Use ImageViewer to display a 2D array view (slice) of a 3D array (e.g., vigra.VigraArray);
        the slice view is taken the array axis designated as "frame axis".
    
    Use SignalViewer to display:
        one neo.Segment out of a sequence of neo.Segments, possibly contained in a neo.Block
        
        one neo.BaseSignal (or its derivative) out of a stand-alone collection of signals
        
        one 1D array view (slice) of a 2D array (e.g. numpy ndarray or vigra.VigraArray)
        
    ATTENTION: Synchronizing frame navigation across instances of ScipyenFrameViewer.
    
    1) Subclasses of ScipyenFrameViewer should have at least one of the following
    attributes (references to QWidgets) for frame nagivation:
    • '_frames_slider_' → QSlider
    • '_frames_spinner_' → QSpinBox
    • '_frames_spinBoxSlider_' → SpinBoxSlider
    
    In the implementation of _configureUI_() these widgets should then be 
    aliased to self._frames_slider_, self._frames_spinner_, self._frames_spinBoxSlider_,
    to  allow for synchronization of frame navigation, e.g.:
    
        self._frames_slider_ = self.myQSliderQWidget
    
    2) To enable or disable synchronized frame navigation, use linkToViewers() or
    unlinkViewer() / unlinkFromViewers(), respectively.
    
    Synchronized viewers display the data frame with the same index (provided
    that the frame index is valid for their individually displayed data). 
        
    Navigating across frames in one viewer is propagated to all viewers that
    are synchronized with it.
    
    Derived classes:
    ----------------
    In Scipyen code tree:
        ImageViewer, SignalViewer

    In scipyen_plugins (outside main Scipyehn code tree):
        LSCaTWindow, EventAnalysis, LTPAnalysis, APTrains.
        (NOTE: Some of these still need to be finalised/written)

    ATTENTION: When deriving a viewer window type from ScipyenFrameViewer:

    • in the __init__ method of the derived type call `super().__init__(...)` in  
        order to create an instance of the superclass ScipyenFrameViewer.
        
        The superclass __init__ method calls two methods which have to be 
        implemented specifically in the derived viewer class:
        
        ∘ `self._configureUI_` 

        ∘ `self._set_data_`
        
        The call order is as follows (↓ indicates temporal succession,
        → indicates function call):
        
        self.__int__() → super().__init__() → self._configureUI_()
                                ↓
                         super().__init__() → self.loadSettings()
                                ↓
                         super().__init__() → self.setData → self._set_data_()
        
        The above call sequence mandates that instance variables of the derived
        class be assigned default values BEFORE calling super().__init__()

    • define (implement) `self._set_data_()` method:
        This is called by self.setData (defined in ScipoyenViewer superclass) 
        and will parse the data to be displayed in order to set up properties 
        of the various GUI widgets in the derived class.
        
        If specific customizations are rewuired by the derived viewer you may
        call super().__init__() with `data` parameter set to None, then call 
        `self._set_data_` manually in the subclass __init__, passing custom 
        parameters to it. This ensures self._set_data_ is called AFTER the call
        to self._configureUI_
        
        NOTE: `self._set_data_` can be called either directly or indirectly by 
        calling `self.setData` method inherited all the way from ScipyenViewer.
        
        The self._set_data_ method MUST:
        ∘ assign the "data" object to self._data_ property (inherited all the
            way from ScipyenViewer)
        
        ∘ assign values to the following instance attributes inherited from 
            ScipyenFrameViewer:
            □ self._data_var_name_
            □ self._data_frames_
            □ self._frameIndex_
            □ self._number_of_frames_
        
        ∘ assign values to instance attributes of the derived class, containing
            properties of GUI widgets of the derived class.
        
        ∘ set the properties of the GUI widgets according to the instance 
            attributes listed above
        
    • implement widgets for frame navigation; you need:
        
        ∘ EITHER one QSpinBox instance named '_frames_spinner_' AND 
                 one QSlider  instance named '_frames_slider_'
        
        ∘ OR an instance of a SpinBoxSlider, named '_frames_spinBoxSlider_'
        
        These names are expected to be there among the instance attributes of 
        the class derived from ScipyenFrameViewer.
        
    • If the derived class managed several instances of ScipyenFrameViewer (e.g.
        several image and/or signal viewer instances that display one 'frame' at a
        time from the same number of 'frames') then, in __init__ make sure you
        call self.linkToViewers(...)

    • define (implement) `self._configureUI_()`, but do NOT call it directly:
        ∘ this method is called by the ScipyenFrameViewer __init__ (see above).

        ∘ the method instantiates the GUI widgets and connects their signals to 
            appropriate slots (Qt framework)
        
            WARNING: Make sure these slots are defined (implemented) in the 
                derived class, unless they are already inherited (and NOT defined
                as abstract methods) from the ScipyenFrameViewer or ScipyenViewer
                superclasses.

        ∘ ATTENTION: in classes that use UI forms generated with Qt 5 Designer, 
            this method MUST call `self.setupUi(self)` first thing, in order to
            instantiate all the widgets declared in the UI form.
        
        ∘ CAUTION: the widgets properties may require certain class or instance
            attributes having default values  - make sure these conditions are 
            met.
        

    """
    
    # signal emitted when the viewer displays a data frame; value:int = the
    # index of the frame in the data
    frameChanged            = Signal(int, name="frameChanged")
    
    def __init__(self, data: typing.Optional[object] = None, 
                 parent: typing.Optional[QtWidgets.QMainWindow] = None, 
                 ID: typing.Optional[int] = None, 
                 win_title: typing.Optional[str] = None, 
                 doc_title: typing.Optional[str] = None, 
                 frameIndex: typing.Optional[typing.Union[int, tuple, list, range, slice]] = None, 
                 currentFrame: typing.Optional[int] = None, 
                 missingFrameValue:typing.Optional[object]=None, *args, **kwargs):
        """Constructor for ScipyenFrameViewer.
        
        Parameters:
        -----------
        data: object or None (default) - the data displayed in the viewer
        
        parent: QMainWindow or None (default) - the parent window 

        pWin: QMainWindow, or None (default) - the instance of the Scipyen main
            window.
            When pWin is the Scipyen's main window, the viewer will have access to
            the user's workspace and will manage the viewer settings as part of
            the Scipyen's global Scipyen Qt configuration (i.e. save/load using
            the Scipyen configuration file).
            
            When pWin is any other QMainWindow, the viewer settings will be
            managed by pWin, if it has the capabilities to do so.
            
        win_title: str or None (default). The display name of the viewer, to be 
            used as part of the window title according to the pattern
            "document - window". 
            When None (default), the display name of the viewer will be set to
            the class name of the viewer and the window ID as a suffix.
            
        doc_title: str or None (default). The display name of the data, to be 
            used as part of the window title according to the pattern
            "document - window". 
            
            When None (the default) the window title will contain only the
            viewer name suffixed with the window ID.
            
        frameIndex: int or None (default). The index of the data frameIndex to be displayed.
        
        currentFrame: int or None (default). The index of the currentFrame.
        
        missingFrameValue: any object or None;
            When not None, this is the value that, when passed to the setter of
            the currentFrame property will disable the current display, to 
            visually indicate a missing data frame
        
        *args, **kwargs: variadic argument and keywords specific to the constructor of the
            derived subclass.
        """
        
        #print(f"ScipyenFrameViewer<{self.__class__.__name__}>.__init__ data: {type(data).__name__}")
 
        self._current_frame_index_      = 0 
        
        # These two should hold a reference to the actual QSlider and QSpinBox
        # defined in the subclass, or in *.ui file used by the subclass
        self._frames_spinner_           = None
        self._frames_slider_            = None
        
        # NOTE: 2022-11-05 13:10:22
        # Migrate to using gui.widgets.SliderSpinBox
        self._frames_spinBoxSlider_     = None
        
        self._missing_frame_value_ = missingFrameValue or NA
        
        # NOTE: 2022-01-17 13:02:27
        # the attributes below (and their properties with unmangled names)
        # MUST have their final values assigned by setData(...)
        self._data_frames_              = 0
        self._number_of_frames_         = 1 # determined from the data
        self._frameIndex_               = range(self._number_of_frames_)
        
        # NOTE: 2022-01-16 13:09:44
        # This also calls self._configureUI_() and self.setData(...)
        super().__init__(data=data, parent=parent, ID=ID,
                         win_title=win_title, doc_title=doc_title,
                         *args, **kwargs)
        
        
    @abstractmethod
    def displayFrame(self, *args, **kwargs):
        """Display the data frame with _current_frame_index_.
        Must be implemented in the derived class.
        The implementation may rely on an internal "curent_frame":int, or
        expect the index of the frame to be passed as function parameter.
        """
        pass
    
    @property
    def nDataFrames(self):
        """The number of "frames" (segments, sweeps) in which data is organized.
        This may be larger than nFrames which is the number of frames the viewer
        can actually display - e.g. see LSCaT.
        
        See also: self.nFrames property.
        """
        return self._data_frames_
    
    @property
    def nFrames(self):
        """The number of data "frames" this viewer knows of; read-only.
        
        A "frame" is either a 2D slice through a nD array (e.g. a 2D slice of a 
        VigraArray), a neo.Segment (which corresponds to an electrophysiology
        "sweep") or a data element in a sequence-like collection (e.g. a 1D 
        array or a neo BaseSignal in a list or tuple) considered as a unit of
        visualization.
        
        The displayed frames may be a subset of the frames that the data is 
        logically organized in, consisting of the frames selected for viewing.
        
        See also: self.nDataFrames property.
        
        Generally, self.nFrames = self.nDataFrames.
        
        When self.nFrames < self.nDataFrames this signifies that only a subset 
        of the frames available in the data are to be shown.
        
        Conversely, self.nFrames > self.nDataFrames happens when multi-channel 
        signals are plotted in SignalViewer with one channel per frame - hence, 
        there are several frames displayed one at a time, even if data is l
        ogically organized in just one frame.
        
        The distinction between self.nFrames and self.nDataFrames is useful for
        multi-index displays (see CaTAnslysis.LSCaTWindow)
        """
        return self._number_of_frames_
    
    @property
    def frameIndex(self):
        """Indices of frames.
        By default, this is range(self.nFrames). In turn, by default:
        self.nFrames == self.nDataFrames.
        
        However, assigning a sequence of int (tuple, list, range) here or in the 
        initializer effectively limits the display to a subset of the available 
        data frames (and thus self.nFrames becomes less than self.nDataFrames)
        
        """
        return self._frameIndex_
    
    @frameIndex.setter
    def frameIndex(self, value:typing.Optional[typing.Union[tuple, list, range]]=None):
        if value is None:
            self._frameIndex_ = range(self.nFrames)
            return 
        
        elif isinstance(value, (tuple, list)):
            if not all(isinstance(v, int) for v in value):
                raise TypeError("'frameIndex' can only accept a sequence of int")
            
            if len(range(self.nDataFrames)) and not all(v in range(self.nDataFrames) for v in value):
                raise ValueError(f"'frameIndex' cannot contain values outside {range(self.nDataFrames)}")
            
            if len(set(value)) != len(value):
                raise ValueError("'frameIndex' does not accept duplicate values")
            
        #elif isinstance(value, range):
            #if len(value) > self.nDataFrames:
                #raise ValueError(f"'frameIndex {value} goes beyound the total number of data frames {self.nDataFrames}")
            
        elif not isinstance(value, range):
            raise TypeError(f"New frameIndex must be a range, or sequence (tuple, list) of int with unique values in {range(self.nDataFrames)}; got {type(value).__name__} instead")
        #else:
            #raise TypeError(f"New frameIndex must be a range, or sequence (tuple, list) of int with unique values in {range(self.nDataFrames)}; got {type(value).__name__} instead")
        self._frameIndex_ = value
        
    @property
    def currentFrame(self):
        """The index of the current data "frame".
        Actually, the index into the current data frame index.
        
        For example, when only a subset of data frames are selected for display, 
        say, frames 1, 5, 7 out of a total of 10 frames, then nFrames = 3
        and currentFrame takes values in the half-open interval [0,3).
        
        Abstract method: it must be implemented in the derived class.
        This property also has a setter (also an abstract method that must be
        implemented in the derived class).
        """
        return self._current_frame_index_
    
    @currentFrame.setter
    def currentFrame(self, value:int):
        """Sets value of the current frame (to be displayed).
        
        The function actually sets the index into the current frame index; when
        the viewer displays only a subset of the available data frames, 
        currentFrame is an index into THAT subset, and not an index into all of
        the data frames.
        
        Should NOT emit frameChanged signal (exceptions are allowed with CAUTION).
        
        Developer information:
        ---------------------
        Deliberately NOT an abstract method therefore it does not need to be 
        implemented in subclasses.
        
        However derived subclasses may reimplement this function for more
        specific functionality (and call super().currentFrame setter)
        """
        # print(f"{self.__class__.__name__}.currentFrame.setter({value}) ")
        if not isinstance(value, int) or value >= self._number_of_frames_ or value < 0:
            return
        
        self._current_frame_index_ = value
        
        # widgets which we want to prevent from emitting signals, temporarily
        # signals from widgets in this list will be blocked for the lifetime of
        # this list (i.e. until and just before the function returns)
        blocked_signal_emitters = list()
        
        if isinstance(self._frames_slider_, QtWidgets.QSlider):
            blocked_signal_emitters.append(self._frames_slider_)
            
        if isinstance(self._frames_spinner_, QtWidgets.QSpinBox):
            blocked_signal_emitters.append(self._frames_spinner_)
            
        if isinstance(getattr(self, "_frames_spinBoxSlider_", None), SpinBoxSlider):
            blocked_signal_emitters.append(self._frames_spinBoxSlider_)
            
        if len(blocked_signal_emitters):
            signalBlockers = [QtCore.QSignalBlocker(w) for w in blocked_signal_emitters]
            
            if isinstance(self._frames_slider_, QtWidgets.QSlider):
                self._frames_slider_.setValue(value)
                
            if isinstance(self._frames_spinner_, QtWidgets.QSpinBox):
                self._frames_spinner_.setValue(value)
                
            if isinstance(getattr(self, "_frames_spinBoxSlider_", None), SpinBoxSlider):
                self._frames_spinBoxSlider_.setValue(value)
                
        self.displayFrame()
            
    @property
    def linkedViewers(self):
        """A list with linked viewers.
        All viewers must be ScipyenFrameViewer objects, and the "link" refers to
        the synchronization of frame navigation across several viewers.
        
        Data in each viewer should be structured with the same number of frames.
        
        """
        return self._linkedViewers_
    
    @property
    def framesSpinBoxSlider(self):
        return self._frames_spinBoxSlider_
    
    @property
    def framesSlider(self):
        """Read-only access to the frames QSlider.
        
        This is either None, or the actual QSlider used by the derived class
        for frame navigation (if defined). 
        """
        return self._frames_slider_
    
    @property
    def framesSpinner(self):
        """Read-only access to the frames QSpinBox.
        """
        return self._frames_spinner_
    
    @safeWrapper
    def linkToViewers(self, *viewers, broadcast: bool = True):
        """Synchronizes frame navigation with the specified viewer(s).
        
        CAUTION: Assumes each viewer in viewers manages data with the same 
        number of data frames.
        
        Named parameters:
        ----------------
        broadcast: bool (default True). If True, also synchronizes frame
            navigation among the additional viewers directly.
        
        Var-positional parameters:
        -------------------------
        viewers: Instances of ScipyenFrameViewer
        
        """
        # print(len(viewers))
        if len(viewers) == 0:
            return
        
        for viewer in viewers:
            if isinstance(viewer, ScipyenFrameViewer):
                self._linkedViewers_.append(viewer)
                
                if self not in viewer.linkedViewers:
                    viewer.linkedViewers.append(self)
                    
            if broadcast:
                for v in viewers:
                    if v is not viewer and viewer not in v.linkedViewers: # avoid synchronizing to itself
                        v.linkedViewers.append(viewer)
    
    @safeWrapper
    def unlinkViewer(self, other):
        """Removes the bidirectional link with the other viewer.
        """
        if isinstance(other, ScipyenFrameViewer) and other in self._linkedViewers_:
            if self in other.linkedViewers:
                other.linkedViewers.remove(self)
                
            if other in self._linkedViewers_:
                self._linkedViewers_.remove(other)
            
    @safeWrapper
    def unlinkFromViewers(self, *others):
        """Removes frame navigation synchronization with other viewers.
        
        Var-positional parmeters:
        =========================
        "others" : sequence of viewers that support multiple data frames
            and are present in self.linkedViewers property.
            and have a slot named "slot_setFrameNumber", i.e. SignalViewer and 
            ImageViewer.
            
        When "others" is empty, removes synchronization with all viewers in
        self.linkedViewers.
            
        
        Any navigation links between the others are left intact. This asymmetry 
        with linkToViewers() is deliberate.
        """
        
        if len(others):
            for viewer in others:
                if isinstance(viewer, ScipyenFrameViewer) and viewer in self._linkedViewers_:
                    self.unlinkViewer(others)
            
        else: # break all currently defined "links"
            for viewer in self._linkedViewers_:
                if self in viewer.linkedViewers:
                    viewer.unlinkViewer(self)
                    
            self._linkedViewers_.clear()
        
    @Slot(int)
    @safeWrapper
    def slot_setFrameNumber(self, value:typing.Union[int, type(MISSING), type(NA), type(None), float]):
        """Drives frame navigation from the GUI.
        
        The valueChanged signal of the widget used to select the index of the 
        displayed data frame should be connected to this slot in _configureUI_()
        
        NOTE: Subclasses can reimplement this function.
        """
        # print(f"ScipyenFrameViewer<{self.__class__.__name__}> slot_setFrameNumber {value}")
        
        if isinstance(value, int):
            if value not in range(self._number_of_frames_):
            #if value >= self._number_of_frames_ or value < 0:
            #if value not in self.frameIndex:
                return
            
            self.currentFrame = value
            
            self.frameChanged.emit(value)
            
            # NOTE: 2022-11-05 15:07:13
            # the linkedViewers mechanism is still useful even though it is 
            # bypassed in LSCaTWindow (where there is a need to deal with special
            # indexing in ScanData, see ScanData.framesMap)
            for viewer in self.linkedViewers:
                viewer.currentFrame = value
            
        
