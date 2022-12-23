''' Mon Apr 04 2016 23:41:53 GMT+0100 (BST)

    Searches for python module source files declared as plugins and loads them. 
    
    The search is executed inside scipyen's directory.
    
    Scipyen plugins provide code (module-level functions) to be called from the 
    Scipyen main window menu bar. While the plugin module may define an arbitrary 
    number of functions, a subset of these would be useful as "callbacks", to be 
    called interactively from menu items in the main pict GUI window.
    
    For the purpose of flexibility, there are no restriction on the syntax of the 
    plugin functions designated for use as "callbacks".
    
    A Scipyen plugin is defined as a python module containing the attribute 
    __scipyen_plugin__ and/or the function init_scipyen_plugin().
    
    When a plugin module defines the function init_scipyen_plugin() this function
    is expected to return:
    
    • a mapping (dict-like) of menu path string (key) ↦ module-level function or
        sequence of module-level functions (all defined in the plugin module)
        
        Menu paths are given as stirngs of the form:
        
        "Top menu|submenu|sub-submenu|item_or_submenu"
        See ScipyenWindow.installPluginMenu() docstring for details.
        
    • a module-level function or a sequence of module-level functions, all 
        defined in the plugin module.
        
    
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

    This approach allows the dynamic generation of GUI dialogs prompting for 
    argument values and for the names of the return variables that will be 
    created in the pict workspace.
    
    -------------------------------------------------------------------------
        
    A plugin module can also be imported directly in other modules. However this
    will NOT result is the plugin installing GUI menu items in Scipyen's main 
    window.
    
    Furthermore, a plugin module can import any other Scipyen modules PROVIDED
    that the import statements are given in absolute import mode (i.e., no
    relative import statements are supported).
    
    -------------------------------------------------------------------------
        
'''
# TODO, FIXME:
# 
#     Make it easy to introspect the plugin function code so that the number of 
#     return variables, and possibly, the argument types for positional parameters
#     could be deduced directly from the function object.
# 
#     This would simplify init_scipyen_plugin() function -- no need for nested 
#     dictionary but just a simple dictionary mapping a menu path to a function 
#     object.
# 
#     Porting to Python 3 should make it easier to introspect the function code
#     these things easier as there is already a ystem in place for function 
#     annotations and inspection of return variables in the function signature.
# 
# NOTE: 2016-04-17 16:53:00
# 
#     Implemented by using function annotations.
#     
#     See PEP 3107 -- Function Annotations and http://python-future.org/func_annotations.html
#     
#     for details.
#         
#     Although function annotations are optional in python they are useful for 
#     porting code later to Python 3.
#     
#     In python 2.7 use the funcsigs module (https://pypi.python.org/pypi/funcsigs).
#         
# 
#     Here are a few examples, see also example_plugin.py in this directory.
#     
#     Example 1. function signature with 0 arguments and no return (i.e. returns
#     None)
#     
#     def f1():
#         ... some code ...
#         
#     The mapping for f1 should be {f1:(None, None)}  or  {f1:(0, None)}
#     
#     Example 2. function takes 0 arguments and returns one variable
# 
#     def f2():
#         a = ... some computation ...
#         return a
#         
#     The mapping describing f2 signature should be {f2:[1, None]}
# 
# 
#     Example 3. function takes 0 arguments and returns 2 variables -- note 
#         that the return variables are packd as a tuple in python.
#     
#     def f3():
#         a = ... some computation ...
#         b = ... some more computation ..
#         return a,b 
#         
#     The mapping should be {f3:(2, None)}
# 
#     Example 4. function takes 1 string argument and returns 2 variables.
#     
#     def f4(arg):
#         file = open(arg)
#         data = ... read some data from the file name given in arg ...
#         metadata = ... do something with data or some more / different data from the file ...
#         file.close()
#         return data, metadata
#         
#     The mapping should be {f3:(2, str)}
# 
#     Example 5. function takes 2 positional arguments, one with a default value,
#     and returns 3 variables.
#     
#     def f5(arg0, arg1 = 1.0):
#         file = open(arg)
#         data = ... read some data from the file name given in arg ...
#         file.close()
#         
#         a = data * arg1
#         b = ... perform some computation ...
#         c = ... perform some more computation ...
#         return data, metadata
#         
#     The mapping should be {f5:(3, (str, float))}
#     
#     def f7(arg1, arg2='default value for arg2', arg3=44, *args, **kwargs):
#         return arg1, arg2
# 
#     # set function attributes here, as a dict:
#     # NOTE: this is vulnerable to injecting bad values there, but appripriate exceptions
#     # will be raise by the plugin loading code in pict
#     
#     f7.__setattr__('__annotations__',{'return':'a+b', 'arg1':int, 'arg2':str, 'arg3':int})
#     
#     The mapping returned by init_scipyen_plugin() should be:
#     
#     'Example Plugin|Plugin|Annotated function', f7
#     
#     Caveats: 
#     1) the plugin info should be resolved in unique menu paths but this is 
#     not enforced (it is up to the plugin installer code to deal with name clashes)
#     
# 

from __future__ import print_function

# FIXME 2016-04-03 00:35:17
# if the plugin advertises itself on an already used menu item and with a similar callback function
# the previosuly loaded plugin will be overwritten !!!

import os, inspect, importlib, sys, collections, traceback, types
from pprint import pprint
# import os, inspect, imp, sys, collections

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

# NOTE: 2016-04-15 12:06:04
# not needed anymore, just access the loaded_plugins dict from the caller of 
# plugin_loader (here, ScipyenWindow)
#plugin_info=collections.OrderedDict()

loaded_plugins = collections.OrderedDict()

# __avoid_modules__ = ("scipyen_start", "scipyen_plugin_loader")

def find_plugins(path):
    dw = os.walk(path)
    # module_dict = dict()
    for entry in dw:
        # print(f"find_plugins({path}) entry: {entry}")
        for file_name in (os.path.join(entry[0], i) for i in entry[2]):
            root, ext = os.path.splitext(file_name)
            # NOTE: 2022-12-22 22:43:14
            # stick with source code files only
            if ext in importlib.machinery.SOURCE_SUFFIXES:
                module_name = inspect.getmodulename(file_name)
                if module_name is not None:
                    # print(f"find_plugins({path}) filename: {file_name}, module_name: {module_name}")
                    module_spec = importlib.util.spec_from_file_location(module_name, file_name)
                    # print(f"module spec: {module_spec}")
                    with open(file_name, "rt") as module_file:
                        for line in module_file:
                            if line.startswith('__scipyen_plugin__') or line.startswith("def init_scipyen_plugin"):
                                check_load_module(module_spec)
                                # module_dict[module_name] = module_spec
                                break
                        
            else:
                continue
            
    # print(f"modules to load: {[module_dict.keys()]}")
    # pprint(module_dict)
    
    # for name, spec in module_dict.items():
    #     # print(f"module {name} in sys.modules: {name in sys.modules}")
    #     if name in sys.modules:
    #         # NOTE: 2022-12-23 10:50:11
    #         # we might still want to add this module to the loaded_plugins
    #         # as we want to run its init_scipyen_plugin() function
    #         # loaded_plugins[name] = module
    #         continue
    #     try:
    #         module = importlib.util.module_from_spec(spec)
    #         sys.modules[name] = module
    #         spec.loader.exec_module(module)
    #         loaded_plugins[name] = module
    #     except:
    #         traceback.print_exc()
    #         continue

def check_load_module(spec):
    module = sys.modules.get(spec.name, None)
    if isinstance(module, types.ModuleType): 
        # module found, no beef here
        loaded_plugins[module.__name__] = module
    
    # NOTE: it may be that the module name is not the same (e.g. if it was 
    # imported with absolute import statements)
    
    # retrieve loaded modules with same origin:
    modules = [m_ for m_ in sys.modules.values() if isinstance(m_, types.ModuleType) and isinstance(m_.__spec__, importlib.machinery.ModuleSpec) and m_.__spec__.origin == spec.origin]
    
    if len(modules): # module found, no beef here
        module = modules[0]
        loaded_plugins[module.__name__] = module
    
    # module not found ⇒ create and load module
    try:
        module = importlib.util.moduel_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        loaded_plugins[spec.name] = module
    except:
        traceback.print_exc
    
    
    
    
    
