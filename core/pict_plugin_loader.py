''' Mon Apr 04 2016 23:41:53 GMT+0100 (BST)

    Finds then loads python modules declared as pict plugins. 
    
    Python module files (*.py or *.pyc) are searched recursively from the directory
    where pict module is located.
    
    Pict plugins mainly provide code (functions) to be called from the pict 
    GUI main menu. While the plugin module may define an arbitrary number of 
    functions, a subset of these would be useful as "callbacks", to be called 
    interactively from menu items in the main pict GUI window.
    
    For the purpoe of flexibility, there are no restriction on the syntax of the 
    plugin functions designated for use as "callbacks".
    
    A pict plugin is defined as a python module containing the attribute 
    __pict_plugin__ and the function init_pict_plugin().
    
    __pict_plugin__ can have any value -- in fact it can be None -- and plays 
    the role of a "tag", used by pict_plugin_loader to distinguish a pict
    module from regular python modules in the pict package.
    
    The init_pict_plugin() function returns information about how plugin functions 
    designated as callbacks should be handled by the pict application's GUI.
    
    This information is packed as a mapping: a dict or a collections.OrderedDict.
    
    The KEYS in this mapping are strings: either the empty string, or describing
        the "menu path" that would trigger the execution of the plugin functions 
        described in the VALUES of the mapping (see below). 
        
        When the KEY is an empty string, the plugin function(s) will be installed
        
        
        The following table illustrates this with some examples:
        
Key:                                Mapped to:          Result:
--------------------------------------------------------------------------------------------
"Menuitem"                          One function        A menu item that calls the plugin 
                                                        function will be created directly
                                                        in the Menu bar of the GUI.

                                    Several functions   "Menuitem" is a top-level menu with 
                                                        each function called by its own 
                                                        menu item named after it.

"Menu|Menuitem"                     One function        A menu item that calls the plugin 
                                                        function is created in a top-level 
                                                        menu.

                                    Several functions   "Menuitem" is a submenu of a top-level
                                                        "Menu" menu with each function
                                                        called by its own menu item named after
                                                        it.

"Menu|Submenu|Menuitem"             One function        A menu item that calls the plugin 
                                                        function is created in a submenu of 
                                                        a top-level menu.

                                    Several functions   "Menuitem" is a submenu of "Submenu"
                                                        and each function is called by its
                                                        own menu item named after it.

"Menu|Submenu|Subsubmenu|Menuitem"  One function        A menu item that calls the plugin 
                                                        function is created in a 2nd level
                                                        submenu.
                                                        
                                    Several functions   As in the previous example.

""                                  One function        A menu item named after the plugin
                                                        function placed in a submenu named
                                                        after the plugin module, inside 
                                                        a "Plugins" top-level menu.
                                    
                                    Several functions   A submenu named after the plugin module,
                                                        inside a "Plugins" top-level menu;
                                                        each function called by a menu item named
                                                        after it.
    
---------------------------------------------------------------------------------------------

        NOTE: The menu items can be nested at any depth level in the menu tree.
        In other words, there can be any number of Submenus defined in the menu 
        path string.

        -------------------------------------------------------------------------
        
    The VALUES are mappings (dict or collections.OrderedDict) that specify one 
        or more designated plugin functions, together with their call syntax,
        to be associated with the menu or menuitem defined in the KEYS. 
        
        Whenn there are more than one functions described here, they will be
        attached to menu items named after them, placed in a submenu named after 
        the last element in the menu path string (see the examples in the Table 
        above).
        
        Here, the "keys" of the mapping are plugin function objects, mapped to
        iterable ("values") -- tuple or list with two elements describing the 
        function signature:
        
        {func_object:(number_of_return_vars or None, type or type list or None)}
    
        1. The first element is either None, or an int >= 0 and specifies the 
            number of variables returned by the plugin function.
            
        2. The second element is either None, or a type object, or a tuple or 
            list of type objects, that specify the type of formal (positional) 
            parameters for the plugin function. 
            
        NOTE: When the plugin functions do neither expect parameters, nor return
        variables, the VALUE can be the fucntion object itself (or a list of 
        function objects).
        

    This approach allows the dynamic generation of GUI dialogs prompting for 
    argument values and for the names of the return variables that will be 
    created in the pict workspace.
    
TODO, FIXME:

    Make it easy to introspect the plugin function code so that the number of 
    return variables, and possibly, the argument types for positional parameters
    could be deduced directly from the function object.

    This would simplify init_pict_plugin() function -- no need for nested 
    dictionary but just a simple dictionary mapping a menu path to a function 
    object.

    Porting to Python 3 should make it easier to introspect the function code
    these things easier as there is already a ystem in place for function 
    annotations and inspection of return variables in the function signature.

NOTE: 2016-04-17 16:53:00

    Implemented by using function annotations.
    
    See PEP 3107 -- Function Annotations and http://python-future.org/func_annotations.html
    
    for details.
        
    Although function annotations are optional in python they are useful for 
    porting code later to Python 3.
    
    In python 2.7 use the funcsigs module (https://pypi.python.org/pypi/funcsigs).
        

    Here are a few examples, see also example_plugin.py in this directory.
    
    Example 1. function signature with 0 arguments and no return (i.e. returns
    None)
    
    def f1():
        ... some code ...
        
    The mapping for f1 should be {f1:(None, None)}  or  {f1:(0, None)}
    
    Example 2. function takes 0 arguments and returns one variable

    def f2():
        a = ... some computation ...
        return a
        
    The mapping describing f2 signature should be {f2:[1, None]}


    Example 3. function takes 0 arguments and returns 2 variables -- note 
        that the return variables are packd as a tuple in python.
    
    def f3():
        a = ... some computation ...
        b = ... some more computation ..
        return a,b 
        
    The mapping should be {f3:(2, None)}

    Example 4. function takes 1 string argument and returns 2 variables.
    
    def f4(arg):
        file = open(arg)
        data = ... read some data from the file name given in arg ...
        metadata = ... do something with data or some more / different data from the file ...
        file.close()
        return data, metadata
        
    The mapping should be {f3:(2, str)}

    Example 5. function takes 2 positional arguments, one with a default value,
    and returns 3 variables.
    
    def f5(arg0, arg1 = 1.0):
        file = open(arg)
        data = ... read some data from the file name given in arg ...
        file.close()
        
        a = data * arg1
        b = ... perform some computation ...
        c = ... perform some more computation ...
        return data, metadata
        
    The mapping should be {f5:(3, (str, float))}
    
    def f7(arg1, arg2='default value for arg2', arg3=44, *args, **kwargs):
        return arg1, arg2

    # set function attributes here, as a dict:
    # NOTE: this is vulnerable to injecting bad values there, but appripriate exceptions
    # will be raise by the plugin loading code in pict
    
    f7.__setattr__('__annotations__',{'return':'a+b', 'arg1':int, 'arg2':str, 'arg3':int})
    
    The mapping returned by init_pict_plugin() should be:
    
    'Example Plugin|Plugin|Annotated function', f7
    
    Caveats: 
    1) the plugin info should be resolved in unique menu paths but this is 
    not enforced (it is up to the plugin installer code to deal with name clashes)
    



'''



from __future__ import print_function
# TODO/FIXME -- imp is deprecated in Python 3 !!!

# FIXME 2016-04-02
# dict.view...() functions are removed from Python3 !!!
# FIXED 2016-04-02 23:59:45
# using items(), keys(), value() (in Python 3 these already return views)

# FIXME 2016-04-03 00:35:17
# if the plugin advertises itself on an already used menu item and with a similar callback function
# the previosuly loaded plugin will be overwritten !!!

import os, inspect, imp, sys, collections

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

# NOTE: 2016-04-15 12:06:04
# not needed anymore, just access the loaded_plugins dict from the caller of 
# plugin_loader (here, ScipyenWindow)
#plugin_info=collections.OrderedDict()

loaded_plugins = collections.OrderedDict()

__avoid_modules__ = ("scipyen_start", "pict_plugin_loader")

def load_plugin(mod_info):
    '''Imports the plugin module according to the information in mod_info tuple:
    
        mod_info[0] is a module information sequence as returned by inspect.getmoduleinfo
        
        In partcular:
        
        mod_info[0].name is the module name (when imported, this will be the __name__ 
            attribute of the module)
            
        mod_info[0].mode is the mode; relevant hare are:
            python source file (*.py)    -- mode is PY_SOURCE
            compiled python file (*.pyc) -- mode is PY_COMPILED
            
        mod_info[1] is the filename (fully qualified absolute pathname); when 
            imported, this will appear as __file__ attribute of the module
    '''
    module_file = open(mod_info[1], mod_info[0].mode)

    # NOTE: 2016-04-15 11:51:08
    # do not call init_pict_plugin here anymore, just import the modules, then
    # let the caller of the plugin_loader to deal with plugin initialization and
    # installation
    
    # NOTE: 2016-04-15 14:21:43
    # the loaded module is found in sys.modules that can be accessed via the 
    # PICT console !!!

    try:
        plugin_module = imp.load_module(mod_info[0].name, module_file, mod_info[1], (mod_info[0].suffix, mod_info[0].mode, mod_info[0].module_type))
        loaded_plugins.update({mod_info[0].name:plugin_module})
        module_file.close()
    finally:
        module_file.close()
    
    module_file.close()

def find_plugins(path):
    '''Searches for module files that advertise themselves as pict plugins, in 
    the directory tree rooted at path.
    '''
    dw = os.walk(path)
    
    plugin_files = collections.OrderedDict()
    
    plugin_sources = collections.OrderedDict()
    
    forceRecompile = True # TODO make it a configuration variable
    
    for entry in dw:
        for fn in (os.path.join(entry[0], i) for i in entry[2]):
            if '.py' in fn and ('~' not in fn and 'bak' not in fn and 'old' not in fn and 'sav' not in fn and 'asv' not in fn): # skip backup files
                module_info = inspect.getmoduleinfo(fn)
                if module_info is not None:
                    if module_info.name not in __avoid_modules__: # skip _THESE_ files
                        module_file = open(fn, module_info.mode)
                        try:
                            for line in module_file:
                                if '__pict_plugin__' in line:
                                    if module_info.module_type == imp.PY_COMPILED:
                                        plugin_files[module_info.name] = (module_info, fn)
                                    elif module_info.module_type == imp.PY_SOURCE:
                                        plugin_sources[module_info.name] = (module_info, fn)
                                    break
                        except:
                            module_file.close()
                        finally:
                            module_file.close()
                            
                        module_file.close()
        
    source_plugins = set(plugin_sources.keys())
    compiled_plugins = set(plugin_files.keys())
    
    source_and_compiled_plugins = source_plugins & compiled_plugins
    
    source_only_plugins   = source_plugins - compiled_plugins
    compiled_only_plugins = compiled_plugins - source_plugins
    
    # (1) load compiled_only_plugins
    if len(compiled_only_plugins) > 0:
        for plugin in compiled_only_plugins:
            load_plugin(plugin_files[plugin])
            
    # (2) load the rest of compiled_plugins (that also have source files), unless
    # forceRecompile is True, in which case load (and compile) _all_ source_plugins
    if len(source_and_compiled_plugins) > 0:
        for plugin in source_and_compiled_plugins:
            if forceRecompile:
                load_plugin(plugin_sources[plugin])
            else:
                load_plugin(plugin_files[plugin])
                
    # finally load source only plugins
    if len(source_only_plugins) > 0:
        for plugin in source_only_plugins:
            load_plugin(plugin_sources[plugin])
    
