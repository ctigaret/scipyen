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
        
        
