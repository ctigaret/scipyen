import os
from gui.workspacegui import GuiMessages
from core.prog import printStyled

__module_path__ = os.path.abspath(os.path.dirname(__file__))

def my_plugin_function():
    print(f"{printStyled('Hello world', 'green', True)}", file = mainWindow.console.stdout)

def output_to_system_console():
    print("Hello world")

def helloWorld():
    """
    The following attributes are "injected" in this module
    namespace:
    
    manWindow → Scipyen's main window': the user's name space is available as `mainWindow.workspace` attribute
    """
    txt = ["A Scipyen plugin is a regular Python module that defines the function `init_scipyen_plugin`",
           "returning a dict mapping key:str ↦ value:function, where:",
           "",
           "• keys are strings with a menu path rooted at the menu bar of Scipyen",
           "containing optional submenus, e.g. 'Plugins|Simple Plugin Examples|Hello World'",
           "∘ the top item in this hierarchy ('Plugins' in this example) will be added",
           "AFTER the last menu item defined in Scipyen's gui/mainwindow.ui file;",
           "∘ the last item in this hierarchy ('Hellow World' in this example)",
           "is the actual menu item that will trigger an action calling the module",
           "function mapped to this key"
           ""
           "• values are functions defined in the plugin module and are called when the",
           "last menu item in the hierarchy above has been triggered by user interaction.",
           "",
           "In this particular example there will be three new menu items installed:",
           "• Plugins / Simple Plugin Examples / Hello World (system console) →",
           "will output a short message to the system's console ",
           "• Plugins / Simple Plugin Examples / Hello World →",
           "will output a short message to the Scipyen console ",
           "• Hello World →",
           "will show this Information dialog. ",
           "",
           "NOTE:",
           "A plugin module can be placed anywhere in Scipyen's code tree. However,",
           "this tree is inaccessible when running a 'frozen' Scipyen application.",
           "",
           "Therefore, user-defined plugins can be stored outside Scipyen's tree, in ",
           f"a directory of your choice. By default, this directory is {mainWindow._default_scipyen_user_plugins_dir}",
           "and can be configured from Scipyen main window `Settings` menu.",
           "",
           f"Currently, the user plugins directory is {mainWindow.userPluginsDirectory}"
           ]
    
    GuiMessages.informationMessage_static(mainWindow, 
                                          title = "Simple Plugin Example", 
                                          text = "\n".join(txt))
    
def init_scipyen_plugin():
    return {"Plugins|Simple Plugin Examples|Hello World":my_plugin_function,
            "Hello World (System console)": output_to_system_console,
            "Plugins|Simple Plugin Examples|Hello World (GUI)": helloWorld}
