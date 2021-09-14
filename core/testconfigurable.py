import inspect, typing
from traitlets import Bunch
from core.traitcontainers import DataBag
from core import scipyen_config

print("ATTENTION Remove before merging with master")

def markConfigurable(confname:str, conftype:str="", 
                     setter:bool=True, 
                     default:typing.Optional[typing.Any]=None,
                     trait_notifier:typing.Optional[DataBag] = None):
    """Decorator for instance methods & properties.
    
    Properties and methods decorates with this will be collected by the ::class::
    decorator makeConfigurable to enable saving/loading used settings for that 
    ::class::
    
    See documentation of makeConfigurable for details.
    
    Parameters:
    ===========
    
    confname: str: the name of the settings parameter (arbitrary but indicative 
        of what it represents)
        
        If this is an empty string, the decorator does nothing.
    
    conftype: str, optional, default is '' (the empty str)
        When 'conftype' is 'Qt' (case-insensitive) the decorated method or
        property will be used as getter/setter in the QSettings framework.
        
        Otherwise, the decorated methods or property will be used as getter/setter
        in the confuse framework.
        
    setter: bool, default is True - required for methods only, where it indicates
        whether the decorated method is a setter (when True) or a getter (when 
        False)
        
        NOTE: for properties, this is determined by the decorated property's
        'fget' and 'fset' attributes.
        
        For a read-only property, 'fset' is None.
        
        For a read-write property, both 'fget' and 'fset' are functions.
        
    default: any type (optional, default is None)
        When present it is used to supply a 'factory' default value to the setter,
        in case the configuration file doesn't have one.
        
        
    Returns:
    =======
    f: the decorated method or property object, augmented as described below.
        
    What it does:
    ============
    
    1) When f is a property:
    
    * if f.fget is a function, adds to it a 'configurable_getter' attribute:
            
    f.fget.configurable_getter = {'type': conftype, 'name': confname, 'getter':f.fget.__name__}
            
    * if f.fset is a function, adds to it a 'configurable_setter' attribute:
        
    f.fset.configurable_setter = {'type':conftype, 'name': confname, 'setter': f.fset.__name__, 'default':None}
    
    2) When f is a method function:
    
    * if setter is False, adds to it a 'configurable_getter' attribute:
        
    f.configurable_getter = {'type': conftype, 'name': confname, 'getter':f.__name__}
    
    * if setter is True, adds to it a 'configurable_setter' attribute:
    
    f.configurable_setter = {'type': conftype, 'name': confname, 'setter':f.__name__, 'default'None}
    
    In the above the 'default' field is mapped to the value of the 'default'
    parameter of this decorator function.
    
    CAUTION: the 'default' values are references to python objects; make sure
    they still exist; it is better to leave this parameter to its default (None)
    
    
    These attributes will be parsed by the ::class:: decorator makeConfigurable
    to construct the ::class:: attributes '_qtcfg' and '_cfg' according to the
    value of 'conftype'
    
    """
    if not isinstance(confname, str) or len(confname.strip()) == 0:
        return f # fail silently
    
    if not isinstance(conftype, str):
        return f # fail silently
    
    conftype = conftype.lower()
    
    def wrapper(f):
        # NOTE 2021-09-06 10:42:49
        # applies only to read-write properties
        # hence only decorate xxx.setter if defined
        if isinstance(f, property):
            if all((inspect.isfunction(func) for func in (f.fget, f.fset))):
                setattr(f.fget, "configurable_getter", Bunch({"type": conftype, "name": confname, "getter":f.fget.__name__, "default": default}))
                setattr(f.fset, "configurable_setter", Bunch({"type": conftype, "name": confname, "setter":f.fset.__name__, "default": default}))
                
                if conftype != "qt" and isinstance(trait_notifier, (bool, DataBag)):
                    def newfset(instance, *args, **kwargs):
                        f.fset.__call__(instance, *args, **kwargs)
                        if isinstance(trait_notifier, DataBag):
                            trait_notifier[confname] = args[0]
                        elif trait_notifier is True and isinstance(getattr(instance, "configurable_traits", None), DataBag):
                            instance.configurable_traits[confname] = args[0]
                        #print("update trait")
                    setattr(newfset, "configurable_setter", f.fset.configurable_setter)
                    
                    return property(fget = f.fget, fset = newfset, doc = f.__doc__)
                    
        elif inspect.isfunction(f):
            if setter is True:
                setattr(f, "configurable_setter", Bunch({"type": conftype, "name": confname, "setter":f.__name__, "default": default}))

                if conftype != "qt" and isinstance(trait_notifier, (bool, DataBag)):
                    def newf(instance, *args, **kwargs):
                        f(instance, *args, **kwargs)
                        if isinstance(trait_notifier, DataBag):
                            trait_notifier[confname] = args[0]
                        elif trait_notifier is True and isinstance(getattr(instance, "configurable_traits", None), DataBag):
                            instance.configurable_traits[confname] = args[0]
                        
                    setattr(newf, "configurable_setter", f.configurable_setter)
                        
                    return newf
                    
            else:
                setattr(f, "configurable_getter", Bunch({"type": conftype, "name": confname, "getter":f.__name__, "default": default}))
                
        return f
    
    return wrapper

def obs(change):
    print(change)

test_notifier = DataBag()
test_notifier.observe(obs)

#class TestConfigurable(object):
class TestConfigurable(scipyen_config.ScipyenConfigurable):
    def __init__(self):
        scipyen_config.ScipyenConfigurable.__init__(self)
        self._test_attribute_ = "something"
        
        self._another_thing_ = 0
    
    @property
    def test(self):
        return self._test_attribute_
    
    @markConfigurable("Test", default = "smth", trait_notifier=True)
    @test.setter
    def test(self, val):
        self._test_attribute_ = val
        
    def getAnotherThing(self):
        return self._another_thing_
    
    @markConfigurable("Another", trait_notifier = True)
    def yetAnotherThing(self, val):
        self._another_thing_ = val
        
        
#def saveWindowSettings(qsettings:QtCore.QSettings, 
                       #win:typing.Union[QtWidgets.QMainWindow, mpl.figure.Figure], 
                       #group_name:typing.Optional[str]=None,
                       #prefix:typing.Optional[str]=None) -> typing.Tuple[str, str]:
    #"""Saves window settings to the Scipyen's Qt configuration file.
    
    #On recent Linux distributions this is $HOME/.config/Scipyen/Scipyen.conf 
    
    #The following mandatory settings will be saved:
    
    #* For all QWidget-derived objects:
        #* WindowSize
        #* WindowPosition
        #* WindowGeometry
        
    #* Only for QMainWindow-derived objects, or objects that have a 'saveState()'
        #method returning a QByteArray:
        #* WindowState 
        
    #Additional (custom) entries and values can be saved when passed as a mapping.
    
    #Settings are always saved in groups inside the Scipyen.conf file. The group's
    #name is determined automatically, or it can be specified.
    
    #Because the conf file only supports one level of group nesting (i.e. no 
    #"sub-groups") an extra-nesting level is emulated by prepending a custom
    #prefix to the setting's name.
    
    #Parameters:
    #==========
    
    #qsettings: QtCore.QSettings. Typically, Scipyen's global QSettings.
    
    #win: QMainWindow or matplotlib Figure. The window for which the settings are
        #saved.
    
    #group_name:str, optional, default is None. The qsettings group name under 
        #which the settings will be saved.
        
        #When specified, this will override the automatically determined group 
        #name (see below).
    
        #When group_name is None, the group name is determined from win's type 
        #as follows:
        
        #* When win is a matplotlib Figure instance, group name is set to the 
            #class name of the Figure's canvas 
            
        #* When win is an instance of a QMainWindow (this includes Scipyen's main
            #window, all Scipyen viewer windows, and ExternalConsoleWindow):
            
            #* for instances of WorkspaceGuiMixin:
                #* if win is top level, or win.parent() is None:
                    #group name is the name of the win's class
                    
                #* otherwise:
                    #group name is set to the class name of win.parent(); 
                    #prefix is set to the win's class class name in order to
                    #specify the settings entries
            
            #* otherwise, the win is considered top level and the group name is
            #set to the win's class name
            
        #For any other window types, the group name is set to the window's class 
        #name (for now, this is only the case for ScipyenConsole which inherits 
        #from QWidget, and not from QMainWindow).
        
    #prefix: str (optional, default is None)
        #When given, it will be prepended to the settings entry name. This is 
        #useful to distinguish between several windows of the same type which are
        #children of the same parent, yet need distinct settings.
        
    #**kwargs: A mapping of key(str) : value(typing.Any) for additional entries
        #beyond the mandatory ones.
    
    #Returns:
    #========
    
    #A tuple: (group_name, prefix) 
        #group_name is the qsettings group name under which the win's settings 
            #were saved
            
        #prefix is th prefix prepended to each setting name
        
        #These are useful to append settings later
        
        
    #NOTE: Delegates to core.scipyen_config.syncQtSettings
    
    #"""
    ##print("saveWindowSettings %s" % win.__class__.__name__)
    #return syncQtSettings(qsettings, win, group_name, prefix, True)
    
#def loadWindowSettings(qsettings:QtCore.QSettings, 
                       #win:typing.Union[QtWidgets.QMainWindow, mpl.figure.Figure], 
                       #group_name:typing.Optional[str]=None,
                       #prefix:typing.Optional[str]=None) -> typing.Tuple[str, str]:
    #"""Loads window settings from the Scipyen's Qt configuration file.
    
    #On recent Linux distributions this is $HOME/.config/Scipyen/Scipyen.conf 
    
    #The following mandatory settings will be loaded:
    
    #* For all QWidget-derived objects:
        #* WindowSize
        #* WindowPosition
        #* WindowGeometry
        
    #* Only for QMainWindow-derived objects, or objects that have a 'saveState()'
        #method returning a QByteArray:
        #* WindowState 
        
    #Additional (custom) entries and values can be loaded when passed as a mapping.
    
    #Settings are always saved in groups inside the Scipyen.conf file. The group's
    #name is determined automatically, or it can be specified.
    
    #Because the conf file only supports one level of group nesting (i.e. no 
    #"sub-groups") an extra-nesting level, when needed, is emulated by prepending
    #a custom prefix to the setting's name.
    
    #Parameters:
    #==========
    
    #qsettings: QtCore.QSettings. Typically, Scipyen's global QSettings.
    
    #win: QMainWindow or matplotlib Figure. The window for which the settings are
        #loaded.
    
    #group_name:str, optional, default is None. The qsettings group name under 
        #which the settings will be saved.
        
        #When specified, this will override the automatically determined group 
        #name (see below).
    
        #When group_name is None, the group name is determined from win's type 
        #as follows:
        
        #* When win is a matplotlib Figure instance, group name is set to the 
            #class name of the Figure's canvas 
            
        #* When win is an instance of a QMainWindow (this includes Scipyen's main
            #window, all Scipyen viewer windows, and ExternalConsoleWindow):
            
            #* for instances of WorkspaceGuiMixin:
                #* if win is top level, or win.parent() is None:
                    #group name is the name of the win's class
                    
                #* otherwise:
                    #group name is set to the class name of win.parent(); 
                    #prefix is set to the win's class class name in order to
                    #specify the settings entries
            
            #* otherwise, the win is considered top level and the group name is
            #set to the win's class name
            
        #For any other window types, the group name is set to the window's class 
        #name (for now, this is only the case for ScipyenConsole which inherits 
        #from QWidget, and not from QMainWindow).
        
    #prefix: str (optional, default is None)
        #When given, it will be prepended to the settings entry name. This is 
        #useful to distinguish between several windows of the same type which are
        #children of the same parent, yet need distinct settings.
        
    #custom: A key(str) : value(typing.Any) mapping for additional entries.
    
        #The values in the mapping are default values used when their keys are 
        #not found in qsettings.
        
        #If found, their values will be mapped to the corresponding key in 'custom'
        
        #Since 'custom' is passed by reference, the new settings values can be 
        #accessed directly from there, in the caller namespace.
        
    #Returns:
    #========
    
    #A tuple: (group_name, prefix) 
        #group_name is the qsettings group name under which the win's settings 
            #were saved
            
        #prefix is th prefix prepended to each setting name
        
        #These are useful to append settings later
    
    #NOTE: Delegates to core.scipyen_config.syncQtSettings
    
    #"""
    #return syncQtSettings(qsettings, win, group_name, prefix, False)


#class TestGuiWindow(QtWidgets.QMainWindow, ScipyenConfigurable2, ):
    #def __init__(self, parent=None, *args, **kwargs):
        ##super().__init__(parent=parent)
        ##super(ScipyenConfigurable2, self).__init__()
        #super(QtWidgets.QMainWindow,self).__init__(parent=parent)
        
        #self.setVisible(True)
        
    #def closeEvent(self, evt):
        #print("%s.closeEvent" % self.__class__.__name__)
        #super(QtWidgets.QMainWindow, self).closeEvent(evt)
        #saveWindowSettings(self.qsettings, self)
        #evt.accept()

#@makeConfigurable(configurables = Bunch({"WindowSize": Bunch({"type":"qt","getter":"size", "setter":"resize"}),
                                         #"WindowPosition": Bunch({"type":"qt", "getter":"pos","setter":"move"}),
                                         #"WindowGeometry": Bunch({"type":"qt", "getter":"geometry", "setter":"setGeometry"}),
                                         #"WindowState": Bunch({"type":"qt","getter":"saveState", "setter":"restoreState"}),
                                         #}))
#class TestGuiWindow2(QtWidgets.QMainWindow):
    #def __init__(self, parent=None, *args, **kwargs):
        #super(QtWidgets.QMainWindow,self).__init__(parent=parent)
        ##super(ScipyenConfigurable2, self).__init__()
        
        #self.setVisible(True)
        
    #def closeEvent(self, evt):
        #print("%s.closeEvent" % self.__class__.__name__)
        #super(QtWidgets.QMainWindow, self).closeEvent(evt)
        #saveWindowSettings(self.qsettings, self)
        #evt.accept()
        
        
#def _test_load_settings_(instance): # for illustration purposes
    #print("_test_load_settings_: instance %s <%s>" % (instance, instance.__class__))
    #pprint(instance.qtconfigurables)
    #loadWindowSettings(instance.qsettings, instance)
    
#def _test_save_settings_(instance):
    #print("_test_save_settings_: instance %s <%s>" % (instance, instance.__class__))
    #pprint(instance.qtconfigurables)
    #saveWindowSettings(instance.qsettings, instance)
        
#def _test_new_init_(instance, *args, **kwargs):
    #print("_test_new_init_: instance %s <%s>" % (instance, instance.__class__))
    #instance.__class__.__init__(instance, *args, **kwargs)
    #bases = instance.__class__.__bases__
    #instance._load_settings_()
    #instance.__class__.setVisible(instance,True) # this is for illustration purposes as the source :class: is QMainWindow
    #instance.__class__.show(instance) # this is for illustration purposes as the source :class: is QMainWindow
    
#def _test_new_close_event_(instance, evt):
    #instance._save_settings_()
    #bases = instance.__class__.__bases__
    #for cls in bases:
        #if hasattr(cls, "closeEvent"):
            #try:
                #cls.closeEvent(instance,evt)
                #evt.accept()
            #except:
                #traceback.print_exc()
            #break
    
#config_extras = Bunch({"_load_settings_": _test_load_settings_,
                       #"_save_settings_": _test_save_settings_,
                       #"_init__": _test_new_init_,
                       #"closeEvent": _test_new_close_event_})

#TestGuiWindow3 = makeConfigurable(configurables = Bunch({"WindowSize": Bunch({"type":"qt","getter":"size", "setter":"resize"}),
                                         #"WindowPosition": Bunch({"type":"qt", "getter":"pos","setter":"move"}),
                                         #"WindowGeometry": Bunch({"type":"qt", "getter":"geometry", "setter":"setGeometry"}),
                                         #"WindowState": Bunch({"type":"qt","getter":"saveState", "setter":"restoreState"}),
                                         #}),
                                  #extras = config_extras)(QtWidgets.QMainWindow)
