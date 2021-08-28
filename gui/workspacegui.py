# -*- coding: utf-8 -*-
import typing, warnings, os, inspect, sys
from pprint import pprint
from functools import singledispatch, update_wrapper, wraps
#### BEGIN Configurable objects with traitlets.config
from traitlets import (config, Bunch)
#### END Configurable objects with traitlets.config
import matplotlib as mpl
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
#from traitlets.config import SingletonConfigurable
from core.utilities import safeWrapper
from core.workspacefunctions import user_workspace
from core.scipyen_config import (ScipyenConfigurable, syncQSettings)
from gui.pictgui import ItemsListDialog


#class makeConfigurable(object):
    #"""Decorator to set up a type's property as a configurable.
    
        #A configurable is an attribute that can be saved as a persistent setting
        #of an object, to be restored in a later Scipyen session.
        
        #This is achieved by adding a type attribute that maps the setting name
        #(which can be arbitrary) to a tuple containing the names of the getter 
        #and setter methods defined in the object's type.
        
        #Depending on the third argument of the initializer, the new attribute is
        #called '_qtcfg', or '_cfg' and takes the form:
        
        #{
            #SettingName1: (getter_method1_name, setter_method1_name),
            #SettingName2: (getter_method2_name, setter_method2_name),
            #... etc...
        #}
        
        #When the tuple contains only one str, this is assumed to be the name of
        #a read/write property. CAUTION: this may raise AttributeError when the
        #property is read-only and a attempt is made to set it to a value loaded
        #from the config file.
        
        #WARNING This behaviour may change in the future, enforcing the read/write
        #property to be represented by a tuple of (getter, setter) names even when 
        #they are the same.
        
        #Of course, the '_qtcfg' and '_cfg' type attributes can be also set 
        #manually (i.e. 'hardcoded') in any user-defined type. This is useful 
        #when the user-defined type is derived (inherits) from a type defined in 
        #a thid party library (and thus cannot be modified), provided that:
        
        #1) the designer of the new type already KNOWS what are the getter/setter
        #methods for a settings 
        
        #2) the setter accepts the same data type as returned by the getter
        
        #For example, see WorkspaceGuiMixin._qtcfg which uses 
        #PyQt5.QWidgets.QMainWindow method names for window size, position, etc)
        
        #Usage scenarios:
        
        #1) As a decorator for data descriptors in user-defined classes - this is 
        #a shorthand for manually defining '_qtcfg' and/or '_cfg' as above.
        
        #Let 'SomeType' a user-defined type, where the designer has defined a
        #read-write property called 'someprop':
        
        ## this defines the property 'someprop' of 'SomeType' as read-only
        ## because this is the first thing that the Python compiler sees when reading
        ## the source code, and therefore 'someprop' will only have its 'fget'
        ## defined as a function.
        #@property           
        #def someprop(self):
            #return ...
            
        ## this adds write capability to the 'someprop' property of 'SomeType'
        ## now, the compiler rightly set the property's 'fset' attribute to a 
        ## function
        #@someprop.setter    
        #def someprop(self, val):
            #...
            
        #To covert 'someprop' into a Qt setting, decorate _AT_LEAST_ the setter
        #so that the property can be used in both ways (read/write)
        
        ## this will make it a read-only settings: it can be saved to, or loaded
        ## from the config file, but if 'SomeType' does not also define a setter,
        ## attempts to set a value loaded from the config file will raise
        ## AttributeError
        ## NOTE that this happens because when the 'someprop' property is first
        ## defined, it is by default read-only (i.e., its 'fset' method is an
        ## empty wrapper)
        #@makeConfigurable(SomeType, 'SomeProp') # 'Qt' is the default
        #@property
        #def someprop(self):
            #...
            
        ## this will overwrite mechanism the effect of the above by explicitly
        ## mapping the settings name 'SomeProp' to ('someprop' , 'someprop')
        ## in SomeType._qtcfg attribute
        ##
        ## Hence, as 'SomeType' is defining a setter for 'someprop', the 
        ## decorator needs only to be used here.
        ##
        #@makeConfigurable(SomeType, 'SomeProp') # 'Qt' is the default
        #@someprop.setter
        #def someprop(self):
            #...
            
        
        
        
    #"""
    #def __init__(self, klass:type, confname:str, type:str="Qt"):
        #"""Arguments to the decorator:
        #klass: type = the where the property needs to be flagged as configurable
        
        #confname: str = the name of the configuration 'key'
        
        #type:str = 'Qt', 'default', or anything else (optional, default is 'Qt')
        
            #When 'type' is the 'Qt', (the default) then this is a setting to be 
            #saved in / loaded from the Scipyen's QSettings conf file 
            #(typically, $HOME/.config/Scipyen/Scipyen.conf).
            
            #When 'type' is 'default', then this is a setting to be saved in, or
            #loaded from, the config_default.yaml file
            #(typically, in the root directory of where Scipyen is installed, 
            #assuming it has read/write access to the user)
            
            #Otherwise, it will be considerd to be a setting to be saved in the 
            #user's config.yaml fileLoaders
            #(typically, in $HOME/.config/Scipyen/config.yaml)
            
        #"""
        #self._klass_ = klass
        #self._confname_ = confname
        #self._conftype_ = type
        
    #def __call__(self, f):
        ##print("in makeConfigurable.__call__")
        ## NOTE: 2021-08-28 10:43:26
        ## make sure 'f' is a property that has getter and setter
        ## we don't use the actual f.getter and f.setter here because they're
        ## builtin_function_or_method and their __qualname__ is decoupled from
        ## the owner klass;
        ##locals = sys._getframe(1).f_locals
        ##print("locals", locals)
        ##globals = sys._getframe(1).f_globals
        ##print("globals", globals)
        
        #if isinstance(f, property):
            ##print("property", f) 
            #gs = []
            ## NOTE: 2021-08-28 13:43:00
            ## when f.fset is not a function, f is a read-only property
            ## ATTENTION for backward compatibility this is NOT picked up in 
            ## syncQSettings(). I.e., when confname is mapped to a 1-tuple in 
            ## klass._qtcfg this is _ASSUMED_ to be a read-write property
            ##
            #if inspect.isfunction(f.fget):
                #propname = f.fget.__qualname__.split(".")[-1]
                #gs.append(propname)
                
            #if inspect.isfunction(f.fset):
                #propname = f.fset.__qualname__.split(".")[-1]
                #gs.append(propname)
                
            #if self._conftype_ is 'Qt':
                ## NOTE: 2021-08-28 13:58:20
                ## klass._qtcfg is handled in syncQSettings()
                #if hasattr(self._klass_, "_qtcfg") and isinstance(self._klass_._qtcfg, dict):
                    #self._klass_._qtcfg.update({self._confname_: tuple(gs)})
                    
                #else:
                    #self._klass_._qtcfg = Bunch({self._confname_ : tuple(gs)})
                    
            #elif self._conftype_ is 'default':
                ## TODO 2021-08-28 13:58:00
                ## implement handling of default non-Qt settings
                #pass
            #else:
                #if hasattr(self._klass_, "_cfg") and isinstance(self._klass_._cfg, dict):
                    #self._klass_._cfg.update({self._confname_: tuple(gs)})
                    
                #else:
                    #self._klass_._cfg = Bunch({self._confname_ : tuple(gs)})
                    
                
        ##else:
            ##print(f, "is not a property")
                    
        #return f
    
class GuiMessages(object):
    @safeWrapper
    def errorMessage(self, title, text):
        errMsgDlg = QtWidgets.QErrorMessage(self)
        errMsgDlg.setWindowTitle(title)
        errMsgDlg.showMessage(text)
        
    @safeWrapper
    def criticalMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        QtWidgets.QMessageBox.critical(self, title, text)
        
    @safeWrapper
    def informationMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        QtWidgets.QMessageBox.information(self, title, text)
        
    @safeWrapper
    def questionMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        QtWidgets.QMessageBox.question(self, title, text)
        
    @safeWrapper
    def warningMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        QtWidgets.QMessageBox.warning(self, title, text)
        
    @safeWrapper
    def detailedMessage(self, title, text, detail="", msgType="Critical"):
        if not hasattr(QtWidgets.QMessageBox.Icon, msgType):
            raise ValueError("Invalid msgType %s. Expecting one of %s" % (msgType, ("NoIcon", "Question", "Information", "Warning", "Critical")))
        
        msgbox = QtWidgets.QMessageBox()
        msgbox.setSizeGripEnabled(True)
        msgbox.setIcon(getattr(QtWidgets.QMessageBox.Icon, msgType))
        msgbox.setWindowTitle(title)
        msgbox.setText(text)
        if isinstance(detail, str) and len(detail):
            msgbox.setDetailedText(detail)
            
        msgbox.exec()
        
class FileIOGui(object):
    @safeWrapper
    def chooseFile(self, caption:typing.Optional[str]=None, fileFilter:typing.Optional[str]=None, 
                   single:typing.Optional[bool]=True,
                   targetDir:typing.Optional[str]=None) -> typing.Tuple[typing.Union[str, typing.List[str]], str]:
        """Launcher of file open dialog
        
        Parameters:
        ----------
        caption: str, optional default is None - The caption of the file chooser dialog
        fileFilter: str, optional, default is None - The file filter for choosing
            from a specific subset of tile types. When present, it must have a 
            specific format, e.g. "Pickle Files (*.pkl);;Text Files (*.txt)"
            
        single:bool, optional (default: True)
           When False, the file chooser dialog will allow opening several files
           
        targetDir:str, optional (default is None) Target directory from where 
            files are chosen.
            
            When None, an empty string or a string that does NOT resolve to a
            directory, target 
            
        Returns:
        -------
        fn: str or list of str The selected file name (or file names, if "single"
            is False)
            
        fl: str The string containing the selected file filter (defaults to
            "All files (*.*)")
        
        """
        from functools import partial
        
        if targetDir is None:
            targetDir = os.getcwd()
            
        if isinstance(targetDir, str):
            if len(targetDir.strip()) == 0 or not os.path.isdir(targetDir):
                targetDir = os.getcwd()
                
        opener = QtWidgets.QFileDialog.getOpenFileName if single else QtWidgets.QFileDialog.getOpenFileNames
        
        if isinstance(caption, str) and len(caption.strip()):
            opener = partial(opener, caption=caption)
            
        if isinstance(fileFilter, str) and len(fileFilter.strip()):
            opener = partial(opener, filter=fileFilter)
        
        fn, fl = opener(parent=self, directory=targetDir)
        
        return fn, fl
    
    @safeWrapper
    def chooseDirectory(self, caption:typing.Optional[str]=None,
                        targetDir:typing.Optional[str]=None) -> str:
        
        if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
            dirName = str(QtWidgets.QFileDialog.getExistingDirectory(self, caption=caption, directory=targetDir))
        else:
            dirName = str(QtWidgets.QFileDialog.getExistingDirectory(self, caption=caption))
            
        return dirName

class WorkspaceGuiMixin(GuiMessages, FileIOGui, ScipyenConfigurable):
    """Mixin type for windows that need to be aware of Scipyen's main workspace.
    
    Also provides:
    1) common functionality needed in Scipyen's windows, including QSettings
        maganement
    2) a custom ID useful when the window is a child of a Scipyen "app" (e.g.,
     LSCaT) instead of beign top level
     
    To save a standardized set of window-specifc settings to the QSettings .conf
    file, in the derived type, override the instance methos closeEvent() to 
    call 'saveWindowSettings()' defined in this module.
    
    To load a standardized set of window-specific settings from the QSettings
    .conf file call 'loadWindowSettings()' defined in this module.
    
    The standardized window-specific settings are window size, position, geometry
    and (whenever possible ) state.
    
    In addition, further settings can be defined by either
    
    1) populating the '_qtcfg' attribute of the derived window type with new
    entries (see self.qtconfigurables for details),  - this will be updated with
    WorkspaceGuiMixin._qtcfg contents upon initialization of the derived type,
    
    or
    
    2) creating in the derievd type an attribute named '_ownqtcfg' - a mapping 
    of a similar structure to '_qtcfg'.
    
    NOTE: this only needs to be done in the most derived type in a long
    inheritance chain. This is done. e.g. in SignalViewer where the inheritance 
    chains is:
    
    SignalViewer <- ScipyenFrameViewer <- ScipyenViewer <- WorkspaceGuiMixin
    
    or
    
    3) by decorating the desired property in the derived type with the 
    @makeConfigurable  decorator (defined in this module)
    
    """
    # NOTE: 2021-08-26 11:32:25
    # key:str = QSettings key
    # value: 
    #   EITHER: tuple (str, str) = getter method name, setter method name
    #           where:
    #               getter method name: name of instance or :class: method that
    #                                   returns a Python object (CAUTION: when
    #                                   the method returns SEVERAL obejcts they
    #                                   will be captured in a tuple!)
    #               setter method name: name of the instance or :class: method that
    #                                   accepts ONE Python object as parameter
    #                                   which corresponds to the return value of
    #                                   the getter method
    #
    #   OR:     tuple (str, ) = property
    #           where: property is the name of a descriptor with read-write access
    #
    #
    #
    _qtcfg = Bunch({"WindowSize":       ("size",        "resize"),
                    "WindowPosition":   ("pos",         "move"),
                    "WindowGeometry":   ("geometry",    "setGeometry"),
                    "WindowState":      ("saveState",   "restoreState")})
    
    _ownqtcfg = Bunch()
    
    _cfg = Bunch()
    
    _owncfg = Bunch()
    
    def __init__(self, parent: (QtWidgets.QMainWindow, type(None)) = None,
                 title="", **kwargs):
        if self.__class__ is not WorkspaceGuiMixin:
            if hasattr(self.__class__, "_qtcfg"):
                subclassqtcfg = getattr(self.__class__, "_qtcfg")
                subclassqtcfg.update(WorkspaceGuiMixin._qtcfg)
                setattr(self.__class__, "_qtcfg", subclassqtcfg)
                
        self._scipyenWindow_ = None
        
        if isinstance(parent, QtWidgets.QMainWindow) and type(parent).__name__ == "ScipyenWindow":
            self._scipyenWindow_   = parent
            
        else:
            # NOTE: 2020-12-05 21:24:45
            # this successfully returns the user workspace ONLY when the 
            # constructor is invoked (directly or indirectly) from within
            # the console; otherwise, it is None
            ws = user_workspace()
            
            if ws is not None:
                self._scipyenWindow_ = ws["mainWindow"]
                
            else:
                frame_records = inspect.getouterframes(inspect.currentframe())
                for (n,f) in enumerate(frame_records):
                    if "ScipyenWindow" in f[0].f_globals:
                        self._scipyenWindow_ = f[0].f_globals["ScipyenWindow"].instance()
                        break
                
        if isinstance(title, str) and len(title.strip()):
            self.setWindowTitle(title)
            
    #@property
    #def qtconfigurables(self):
        #"""A str -> type mapping of configurable properties for QSettings.
        
        #The keys of the mapping (str) are attributes or descriptors with read &
        #write access, defined in the viewer class, as follows. 
        
        #key:str = QSettings key
        
        #value: 
        #EITHER: tuple (str, str) = (getter method name, setter method name)
                #where:
                    #getter method name: name of instance or :class: method that
                                        #returns a Python object (CAUTION: when
                                        #the method returns SEVERAL obejcts they
                                        #will be captured in a tuple!)
                                        
                    #setter method name: name of the instance or :class: method that
                                        #accepts ONE Python object as parameter
                                        #of the same type as the return value of
                                        #the getter method
        
        #OR:     tuple (str, ) = property
                #where: property is the name of a descriptor with read-write access
                #CAUTION: If the propert is read-only, trying to set values
                #loaded from configuration file will raise AttributeError
                
                #WARNING: this behaviour is on its way out, and two method names
                #will be required for read-write settings (even if they refer to
                #the same method).
        
        #The values are returned by the getter method is expected to be built-in 
        #Python types that can be easily converted to a QVariant, EXCLUDING:
        #- context managers
        #- modules
        #- classes
        #- functions and methods
        #- code objects
        #- type objects
        #- Ellipsis
        #- NotImplemented
        #- stack frame objects
        #- traceback objects
        
        #NOTE: No type checking is performed.
        
        #"""
        ## TODO 2021-08-25 16:47:16
        ## if using traitlets.config framework then make functions to write atomic
        ## qsettings keyts to the conf file, as the configurble is changed
        #return self._qtcfg
    
    #@property
    #def configurables(self):
        #return self._cfg

    @property
    def isTopLevel(self):
        """Returns True when this window is a top level window in Scipyen.
        In Scipyen, a window is "top level" when its instance is not a member of
        a Scipyen "application" (e.g. LSCaT).
        
        For example, any viewer created upon double-clicking on a variable in
        the workspace viewer ("User Variables") is a top-level window.
        
        In contrast, viewers created from within a Scipyen "application" are
        members of the application and thus are not "top level".
        
        A Scipyen "application" is any facility that runs its own GUI inside
        Scipyen (e.g., LSCaT) - this is NOT a stand-alone PyQt5 application with
        which Scipyen communicates.
        
        """
        return self.appWindow is self.parent()
                
    @property
    def appWindow(self):
        """The application main window.
        This is a reference to the  Scipyen main window, unless explicitly given
        as something else at the viewer's initiation.
        
        appWindow gives access to Scipyen main window API (e.g. the workspace).
        """
        return self._scipyenWindow_
    
    @safeWrapper
    def importWorkspaceData(self, dataTypes:typing.Union[typing.Type[typing.Any], typing.Sequence[typing.Type[typing.Any]]],
                            title:str="Import from workspace",
                            single:bool=True) -> list:
        """Launches ItemsListDialog to import on or several workspace variables.
        
        Parameters:
        -----------
        dataTypes: type, or sequence of types
        """
        from core.workspacefunctions import getvarsbytype
        #print("dataTypes", dataTypes)
        
        user_ns_visible = dict([(k,v) for k,v in self._scipyenWindow_.workspace.items() if k not in self._scipyenWindow_.workspaceModel.user_ns_hidden])
        
        name_vars = getvarsbytype(dataTypes, ws = user_ns_visible)
        
        if len(name_vars) == 0:
            return list()
        
        name_list = sorted([name for name in name_vars])
        
        #selectionMode = QtWidgets.QAbstractItemView.SingleSelection if single else QtWidgets.QAbstractItemView.MultiSelection
        selectionMode = QtWidgets.QAbstractItemView.SingleSelection if single else QtWidgets.QAbstractItemView.ExtendedSelection
        
        dialog = ItemsListDialog(parent=self, title=title, itemsList = name_list,
                                 selectmode = selectionMode)
        
        ans = dialog.exec()
        
        if ans == QtWidgets.QDialog.Accepted:
            return [self._scipyenWindow_.workspace[i] for i in dialog.selectedItemsText]
            
        return list()
            
        
def saveWindowSettings(qsettings:QtCore.QSettings, 
                       win:typing.Union[QtWidgets.QMainWindow, mpl.figure.Figure], 
                       group_name:typing.Optional[str]=None,
                       prefix:typing.Optional[str]=None) -> typing.Tuple[str, str]:
    """Saves window settings to the Scipyen's Qt configuration file.
    
    On recent Linux distributions this is $HOME/.config/Scipyen/Scipyen.conf 
    
    The following mandatory settings will be saved:
    
    * For all QWidget-derived objects:
        * WindowSize
        * WindowPosition
        * WindowGeometry
        
    * Only for QMainWindow-derived objects, or objects that have a 'saveState()'
        method returning a QByteArray:
        * WindowState 
        
    Additional (custom) entries and values can be saved when passed as a mapping.
    
    Settings are always saved in groups inside the Scipyen.conf file. The group's
    name is determined automatically, or it can be specified.
    
    Because the conf file only supports one level of group nesting (i.e. no 
    "sub-groups") an extra-nesting level is emulated by prepending a custom
    prefix to the setting's name.
    
    Parameters:
    ==========
    
    qsettings: QtCore.QSettings. Typically, Scipyen's global QSettings.
    
    win: QMainWindow or matplotlib Figure. The window for which the settings are
        saved.
    
    group_name:str, optional, default is None. The qsettings group name under 
        which the settings will be saved.
        
        When specified, this will override the automatically determined group 
        name (see below).
    
        When group_name is None, the group name is determined from win's type 
        as follows:
        
        * When win is a matplotlib Figure instance, group name is set to the 
            class name of the Figure's canvas 
            
        * When win is an instance of a QMainWindow (this includes Scipyen's main
            window, all Scipyen viewer windows, and ExternalConsoleWindow):
            
            * for instances of WorkspaceGuiMixin:
                * if win is top level, or win.parent() is None:
                    group name is the name of the win's class
                    
                * otherwise:
                    group name is set to the class name of win.parent(); 
                    prefix is set to the win's class class name in order to
                    specify the settings entries
            
            * otherwise, the win is considered top level and the group name is
            set to the win's class name
            
        For any other window types, the group name is set to the window's class 
        name (for now, this is only the case for ScipyenConsole which inherits 
        from QWidget, and not from QMainWindow).
        
    prefix: str (optional, default is None)
        When given, it will be prepended to the settings entry name. This is 
        useful to distinguish between several windows of the same type which are
        children of the same parent, yet need distinct settings.
        
    **kwargs: A mapping of key(str) : value(typing.Any) for additional entries
        beyond the mandatory ones.
    
    Returns:
    ========
    
    A tuple: (group_name, prefix) 
        group_name is the qsettings group name under which the win's settings 
            were saved
            
        prefix is th prefix prepended to each setting name
        
        These are useful to append settings later
        
        
    NOTE: Delegates to core.scipyen_config.syncQSettings
    
    """
    return syncQSettings(qsettings, win, group_name, prefix, True)
    
def loadWindowSettings(qsettings:QtCore.QSettings, 
                       win:typing.Union[QtWidgets.QMainWindow, mpl.figure.Figure], 
                       group_name:typing.Optional[str]=None,
                       prefix:typing.Optional[str]=None) -> typing.Tuple[str, str]:
    """Loads window settings from the Scipyen's Qt configuration file.
    
    On recent Linux distributions this is $HOME/.config/Scipyen/Scipyen.conf 
    
    The following mandatory settings will be loaded:
    
    * For all QWidget-derived objects:
        * WindowSize
        * WindowPosition
        * WindowGeometry
        
    * Only for QMainWindow-derived objects, or objects that have a 'saveState()'
        method returning a QByteArray:
        * WindowState 
        
    Additional (custom) entries and values can be loaded when passed as a mapping.
    
    Settings are always saved in groups inside the Scipyen.conf file. The group's
    name is determined automatically, or it can be specified.
    
    Because the conf file only supports one level of group nesting (i.e. no 
    "sub-groups") an extra-nesting level, when needed, is emulated by prepending
    a custom prefix to the setting's name.
    
    Parameters:
    ==========
    
    qsettings: QtCore.QSettings. Typically, Scipyen's global QSettings.
    
    win: QMainWindow or matplotlib Figure. The window for which the settings are
        loaded.
    
    group_name:str, optional, default is None. The qsettings group name under 
        which the settings will be saved.
        
        When specified, this will override the automatically determined group 
        name (see below).
    
        When group_name is None, the group name is determined from win's type 
        as follows:
        
        * When win is a matplotlib Figure instance, group name is set to the 
            class name of the Figure's canvas 
            
        * When win is an instance of a QMainWindow (this includes Scipyen's main
            window, all Scipyen viewer windows, and ExternalConsoleWindow):
            
            * for instances of WorkspaceGuiMixin:
                * if win is top level, or win.parent() is None:
                    group name is the name of the win's class
                    
                * otherwise:
                    group name is set to the class name of win.parent(); 
                    prefix is set to the win's class class name in order to
                    specify the settings entries
            
            * otherwise, the win is considered top level and the group name is
            set to the win's class name
            
        For any other window types, the group name is set to the window's class 
        name (for now, this is only the case for ScipyenConsole which inherits 
        from QWidget, and not from QMainWindow).
        
    prefix: str (optional, default is None)
        When given, it will be prepended to the settings entry name. This is 
        useful to distinguish between several windows of the same type which are
        children of the same parent, yet need distinct settings.
        
    custom: A key(str) : value(typing.Any) mapping for additional entries.
    
        The values in the mapping are default values used when their keys are 
        not found in qsettings.
        
        If found, their values will be mapped to the corresponding key in 'custom'
        
        Since 'custom' is passed by reference, the new settings values can be 
        accessed directly from there, in the caller namespace.
        
    Returns:
    ========
    
    A tuple: (group_name, prefix) 
        group_name is the qsettings group name under which the win's settings 
            were saved
            
        prefix is th prefix prepended to each setting name
        
        These are useful to append settings later
    
    NOTE: Delegates to core.scipyen_config.syncQSettings
    
    """
    return syncQSettings(qsettings, win, group_name, prefix, False)

#class TestWSGui(QtWidgets.QMainWindow, WorkspaceGuiMixin):
    #_qtcfg = {"Something": ("something",)} # Something MAY BE read-only !
    ##_qtcfg = {"Something": ("something","something")} # Something is read-write
    #def __init__(self, parent=None):
        #super().__init__(parent=parent)
        #WorkspaceGuiMixin.__init__(self, parent=parent, title="Test WorkspaceGuiMixin")
        #self._something = "test window"
        #self._another = "funny prop"
        
    #@property
    #def something(self):
        #return self._something
    
    #@something.setter
    #def something(self, val):
        #self._something = val
        
    ##@makeConfigurable(self.__class__, "Another") # 'self' is not defined here!
    #@property
    #def another(self):
        #return self._another
    
    ##@makeConfigurable("Another")
    #@WorkspaceGuiMixin.makeConfigurable("Another") # 'TestWSGui' is not defined yet!
    #@another.setter
    #def another(self, val):
        #self._another = val
        
        
class TestGuiCfg(QtWidgets.QMainWindow, ScipyenConfigurable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._something = "test window"
        self._another = "funny prop"
        
    @property
    def something(self):
        return self._something
    
    @ScipyenConfigurable.makeConfigurable("Something")
    @something.setter
    def something(self, val):
        self._something = val
        
    @property
    def another(self):
        return self._another
    
    @ScipyenConfigurable.makeConfigurable("Another", "")
    @another.setter
    def another(self, val):
        self._another = val
        
        
        
