import os
from gui.workspacegui import GuiMessages
from core.prog import printStyled

__module_path__ = os.path.abspath(os.path.dirname(__file__))

__scipyen_plugin__ = None

def my_plugin_function():
    print(f"{printStyled('Hello world', 'green', True)}", file = mainWindow.console.stdout)

def output_to_system_console():
    print(f"{printStyled('Hello world', 'cyan', True)}")

def helloWorld():
    """
    The following attributes are "injected" in this module
    namespace:
    
    manWindow → Scipyen's main window': the user's name space is available as `mainWindow.workspace` attribute
    """
    txt = ["A Scipyen plugin is a regular Python module with at least one of the two members below:",
           "• a module-level variable `__scipyen_plugin__` (with any value) AND/OR ",
           "",
           "• a module-level function `init_scipyen_plugin`",
           "",
           "A plugin module will available for importing directly at runtime, using an `import` statement in Scipyen's console",
           "",
           "If the plugin defines the `init_scipyen_plugin` function, then Scipyen",
           "will generate a menu/submenu(s)/menu item hierarchy in the menu bar of ",
           "Scipyen's main window, based on the return value of this function.",
           "",
           "The `init_scipyen_plugin` function must return a dict mapping key:str ↦ value:function, where:",
           "",
           "• keys are strings with a menu path rooted at the menu bar of Scipyen",
           "containing optional submenus, separated by the '|' character:",
           "",
           "∘ the top (leftmost) item in this hierarchy will be added",
           "to Scipyen's Menu bar AFTER the last menu item defined in Scipyen's gui/mainwindow.ui file;",
           " (If this item already exists as a menu in the menu bar, the new menu path will be created",
           "  inside, as a submenu)",
           "",
           "∘ intermediate items, if any, describe the submenus ('branch') leading to the leaf item",
           "",
           "∘ the last item (rightmost) in this hierarchy if the 'leaf' item which, when",
           "triggered, will call the module function mapped to the key",
           "",
           "• values are functions defined in the plugin module and are called when the",
           "last menu item in the hierarchy above has been triggered by user interaction.",
           "",
           "In this example, the init_scipyen_plugin function returns the following dictionary:",
           "'Help|About Plugins|Simple Plugin Examples|Hello World (GUI)': helloWorld",
           "'Help|About Plugins|Simple Plugin Examples|Hello World': my_plugin_function,",
           "'Help|About Plugins|Simple Plugin Examples|Hello World (System console)': output_to_system_console, ",
           "",
           "A plugin module can be placed anywhere in Scipyen's code tree. However,",
           "this tree is inaccessible when running a 'frozen' Scipyen application.",
           "",
           "Therefore, user-defined plugins are to be stored outside Scipyen's tree, in a directory of your choice. ",
           f"By default, this directory is {mainWindow._default_scipyen_user_plugins_dir}",
           "but it can be configured from Scipyen main window `Settings` menu.",
           "",
           f"Currently, the user plugins directory is {mainWindow.userPluginsDirectory}",
           "",
           "The currently loaded plugin module names are available via mainWindow.plugins property (a tuple)",
           "Bugs: Isolated menu items - whih should be placed on their own in the menu bar - are not visible",
           "As a workaround, please avoid single-item menu paths in the dict returned by `init_scipyen_plugin` function"
           ]
    
    GuiMessages.informationMessage_static(mainWindow, 
                                          title = "Simple Plugin Example", 
                                          text = "\n".join(txt))
    
def init_scipyen_plugin():
    return {
            "Help|About Plugins|Simple Plugin Examples|Hello World (GUI)": helloWorld,
            "Help|About Plugins|Simple Plugin Examples|Hello World":my_plugin_function,
            "Help|About Plugins|Simple Plugin Examples|Hello World (System console)": output_to_system_console
            }
    # return {"Hello_World_(System_console)": output_to_system_console}
