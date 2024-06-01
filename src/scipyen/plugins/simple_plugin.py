import os
from qtpy import QtWidgets
from gui.workspacegui import GuiMessages
from gui.textviewer import TextViewer
from core.prog import printStyled
from iolib.pictio import loadTextFile

__module_path__ = os.path.abspath(os.path.dirname(__file__))

__text_file__ = os.path.join(__module_path__, "simple_plugin_text")

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
           "• a module-level variable `__scipyen_plugin__` (with any value) ",
           "• a module-level function `init_scipyen_plugin`",
           "",
           "A plugin module can be imported directly at runtime via `import` statements in Scipyen's console.",
           "",
           "If the plugin defines an `init_scipyen_plugin` function, Scipyen will use it to generate a menu/submenu(s)/menu item hierarchy in the menu bar of Scipyen's main window. This function must return a mapping str ↦ function, where:",
           "• keys are strings with a menu path (left → right entries separated by '|' character) in the menu bar:"
           "",
           "• values are functions defined in the plugin module and are called when the last item in the hierarchy above has been triggered by user interaction.",
           "",
           "In this example plugin, the init_scipyen_plugin function returns the following dictionary:",
           "'Help|About Plugins|Simple Plugin Examples|Hello World': my_plugin_function,",
           "'Help|About Plugins|Simple Plugin Examples|Hello World (GUI)': helloWorld",
           "'Help|About Plugins|Simple Plugin Examples|Hello World (System console)': output_to_system_console, ",
           "",
           "A plugin module can be placed anywhere in Scipyen's code tree. However, when running a 'frozen' Scipyen application (i.e., bundles with PyInstaller), user-defined plugins must be stored outside Scipyen's tree, in a directory of your choice. ",
           f"By default, this directory is {mainWindow._default_scipyen_user_plugins_dir} but it can be configured from Scipyen main window `Settings` menu. Currently, the user plugins directory is {mainWindow.userPluginsDirectory}",
           "",
           "Information about the currently loaded plugin modules is available through the following attributes, properties, or methods of Scipyen's Main Window (`mainWindow` variable in console):",
           "plugins, pluginModules, pluginNames, UIPlugins, UIPluginMenus, UIPluginNames, getMenusForUIPlugin",
           "",
           "Bugs: ",
           "Isolated menu items - which should be placed on their own in the menu bar - are not visible",
           "As a workaround, please avoid single-item menu paths in the dict returned by `init_scipyen_plugin` function",
           "Many more to be discovered..."
           ]
    
    info = loadTextFile(__text_file__)
        
    
    tv = TextViewer(info, parent = mainWindow, 
                    doc_title="About Scipyen plugin modules",
                    win_title="",
                    wrap=QtWidgets.QTextEdit.WidgetWidth)
    # tv = TextViewer("\n".join(txt), parent = mainWindow, 
    #                 doc_title="About Scipyen plugin modules",
    #                 win_title="",
    #                 wrap=QtWidgets.QTextEdit.WidgetWidth)
    
    tv.show()
    
    # GuiMessages.informationMessage_static(mainWindow, 
    #                                       title = "Simple Plugin Example", 
    #                                       text = "\n".join(txt))
    
def init_scipyen_plugin():
    return {
            "Help|About Plugins|Simple Plugin Examples|Hello World (GUI)": helloWorld,
            "Help|About Plugins|Simple Plugin Examples|Hello World":my_plugin_function,
            "Help|About Plugins|Simple Plugin Examples|Hello World (System console)": output_to_system_console
            }
    # return {"Hello_World_(System_console)": output_to_system_console}
