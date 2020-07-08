import os
import signal
import sys
from warnings import warn

from PyQt5 import (QtCore, QtGui, QtWidgets, )
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, )

#### BEGIN ipython/jupyter modules
from traitlets.config.application import boolean_flag
from traitlets.config.application import catch_config_error
from traitlets import (
    Dict, Unicode, CBool, Any
)

from qtconsole import styles, __version__

#NOTE: 2017-03-21 01:09:05 inheritance chain ("<" means inherits from)
# RichJupyterWidget < RichIPythonWidget < JupyterWidget < FrontendWidget < (HistoryConsoleWidget, BaseFrontendMixin)
#in turn, FrontendWidget < ... < ConsoleWidget which implements underlying 
# Qt logic, including drag'n drop
from qtconsole.rich_jupyter_widget import RichJupyterWidget # DIFFERENT from that in qtconsoleapp module !!!
from qtconsole.jupyter_widget import JupyterWidget # for use in the External Console

from qtconsole.inprocess import QtInProcessKernelManager
from qtconsole.jupyter_widget import JupyterWidget
#from qtconsole.mainwindow import MainWindow as ConsoleMainWindow
from qtconsole.mainwindow import MainWindow, background
from qtconsole.client import QtKernelClient
from qtconsole.manager import QtKernelManager


#import jupyter_client


#from IPython.utils.ipstruct import Struct as IPStruct

#from IPython.core.history import HistoryAccessor

#from IPython.lib.deepreload import reload as dreload

from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic,
                                needs_local_scope)

from jupyter_core.application import JupyterApp, base_flags, base_aliases
from jupyter_client.consoleapp import (
        JupyterConsoleApp, app_aliases, app_flags,
    )


from jupyter_client.localinterfaces import is_local_ip

#from IPython.display import set_matplotlib_formats

#### END ipython/jupyter modules

#from core import prog
from core.prog import safeWrapper

flags = dict(base_flags)
qt_flags = {
    'plain' : ({'JupyterQtConsoleApp' : {'plain' : True}},
            "Disable rich text support."),
}
qt_flags.update(boolean_flag(
    'banner', 'JupyterQtConsoleApp.display_banner',
    "Display a banner upon starting the QtConsole.",
    "Don't display a banner upon starting the QtConsole."
))

# and app_flags from the Console Mixin
qt_flags.update(app_flags)
# add frontend flags to the full set
flags.update(qt_flags)

# start with copy of base jupyter aliases
aliases = dict(base_aliases)
qt_aliases = dict(
    style = 'JupyterWidget.syntax_style',
    stylesheet = 'JupyterQtConsoleApp.stylesheet',

    editor = 'JupyterWidget.editor',
    paging = 'ConsoleWidget.paging',
)
# and app_aliases from the Console Mixin
qt_aliases.update(app_aliases)
qt_aliases.update({'gui-completion':'ConsoleWidget.gui_completion'})
# add frontend aliases to the full set
aliases.update(qt_aliases)

# get flags&aliases into sets, and remove a couple that
# shouldn't be scrubbed from backend flags:
qt_aliases = set(qt_aliases.keys())
qt_flags = set(qt_flags.keys())

class ExternalConsoleWindow(MainWindow):
    def __init__(self, app,
                    confirm_exit=True,
                    new_frontend_factory=None, slave_frontend_factory=None,
                    connection_frontend_factory=None,
                ):
        super().__init__(app, confirm_exit = confirm_exit,
                         new_frontend_factory = new_frontend_factory,
                         slave_frontend_factory = slave_frontend_factory,
                         connection_frontend_factory=connection_frontend_factory)
        
        self.defaultFixedFont = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        self.settings = QtCore.QSettings()
        self._console_font_ = None
        self._load_settings_()
        
        
    def _load_settings_(self):
        # located in $HOME/.config/Scipyen/Scipyen.conf
        winSize = self.settings.value("ExternalConsole/Size", QtCore.QSize(600, 350))
        winPos = self.settings.value("ExternalConsole/Position", QtCore.QPoint(0,0))
        fontFamily = self.settings.value("ExternalConsole/FontFamily", self.defaultFixedFont.family())
        fontSize = int(self.settings.value("ExternalConsole/FontPointSize", self.defaultFixedFont.pointSize()))
        fontStyle = int(self.settings.value("ExternalConsole/FontStyle", self.defaultFixedFont.style()))
        fontWeight = int(self.settings.value("ExternalConsole/FontWeight", self.defaultFixedFont.weight()))
        
        self._console_font_ = QtGui.QFont(fontFamily, fontSize, fontWeight, italic = fontStyle > 0)
        
        #self.setFont(console_font)
        
        #self._set_font(console_font)
        
        #self.font = console_font

        self.move(winPos)
        self.resize(winSize)
        self.setAcceptDrops(True)
        
    @safeWrapper
    def _save_settings_(self):
        self.settings.setValue("ExternalConsole/Size", self.size())
        self.settings.setValue("ExternalConsole/Position", self.pos())
        if self.active_frontend:
            font = self.active_frontend.font
            self.settings.setValue("ExternalConsole/FontFamily", font.family())
            self.settings.setValue("ExternalConsole/FontPointSize", font.pointSize())
            self.settings.setValue("ExternalConsole/FontStyle", font.style())
            self.settings.setValue("ExternalConsole/FontWeight", font.weight())

    @safeWrapper
    def _save_tab_settings_(self, widget):
        font = widget.font
        self.settings.setValue("ExternalConsole/FontFamily", font.family())
        self.settings.setValue("ExternalConsole/FontPointSize", font.pointSize())
        self.settings.setValue("ExternalConsole/FontStyle", font.style())
        self.settings.setValue("ExternalConsole/FontWeight", font.weight())
        
        
    def add_tab_with_frontend(self,frontend,name=None):
        """ insert a tab with a given frontend in the tab bar, and give it a name

        """
        if not name:
            name = 'kernel %i' % self.next_kernel_id
        self.tab_widget.addTab(frontend,name)
        self.update_tab_bar_visibility()
        self.make_frontend_visible(frontend)
        frontend.font = self._console_font_
        frontend.exit_requested.connect(self.close_tab)

    def closeEvent(self, event):
        """ Forward the close event to every tabs contained by the windows
        """
        if self.tab_widget.count() == 0:
            # no tabs, just close
            self._save_settings_()
            event.accept()
            return
        
        # Do Not loop on the widget count as it change while closing
        title = self.window().windowTitle()
        cancel = QtWidgets.QMessageBox.Cancel
        okay = QtWidgets.QMessageBox.Ok
        accept_role = QtWidgets.QMessageBox.AcceptRole

        if self.confirm_exit:
            if self.tab_widget.count() > 1:
                msg = "Close all tabs, stop all kernels, and Quit?"
            else:
                msg = "Close console, stop kernel, and Quit?"
            info = "Kernels not started here (e.g. notebooks) will be left alone."
            closeall = QtWidgets.QPushButton("&Quit", self)
            closeall.setShortcut('Q')
            box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question,
                                    title, msg)
            box.setInformativeText(info)
            box.addButton(cancel)
            box.addButton(closeall, QtWidgets.QMessageBox.YesRole)
            box.setDefaultButton(closeall)
            box.setEscapeButton(cancel)
            pixmap = QtGui.QPixmap(self._app.icon.pixmap(QtCore.QSize(64,64)))
            box.setIconPixmap(pixmap)
            reply = box.exec_()
        else:
            reply = okay

        if reply == cancel:
            event.ignore()
            return
        
        if reply == okay or reply == accept_role:
            while self.tab_widget.count() >= 1:
                # prevent further confirmations:
                widget = self.active_frontend
                widget._confirm_exit = False
                if self.tab_widget.count() == 1:
                    self._save_tab_settings_()
                self.close_tab(widget)
            event.accept()
        
    def close_tab(self,current_tab):
        """ Called when you need to try to close a tab.

        It takes the number of the tab to be closed as argument, or a reference
        to the widget inside this tab
        """

        # let's be sure "tab" and "closing widget" are respectively the index
        # of the tab to close and a reference to the frontend to close
        if type(current_tab) is not int :
            current_tab = self.tab_widget.indexOf(current_tab)
        closing_widget=self.tab_widget.widget(current_tab)


        # when trying to be closed, widget might re-send a request to be
        # closed again, but will be deleted when event will be processed. So
        # need to check that widget still exists and skip if not. One example
        # of this is when 'exit' is sent in a slave tab. 'exit' will be
        # re-sent by this function on the master widget, which ask all slave
        # widgets to exit
        if closing_widget is None:
            return

        #get a list of all slave widgets on the same kernel.
        slave_tabs = self.find_slave_widgets(closing_widget)

        keepkernel = None #Use the prompt by default
        if hasattr(closing_widget,'_keep_kernel_on_exit'): #set by exit magic
            keepkernel = closing_widget._keep_kernel_on_exit
            # If signal sent by exit magic (_keep_kernel_on_exit, exist and not None)
            # we set local slave tabs._hidden to True to avoid prompting for kernel
            # restart when they get the signal. and then "forward" the 'exit'
            # to the main window
            if keepkernel is not None:
                for tab in slave_tabs:
                    tab._hidden = True
                if closing_widget in slave_tabs:
                    try :
                        self.find_master_tab(closing_widget).execute('exit')
                    except AttributeError:
                        self.log.info("Master already closed or not local, closing only current tab")
                        self.tab_widget.removeTab(current_tab)
                    self.update_tab_bar_visibility()
                    return

        kernel_client = closing_widget.kernel_client
        kernel_manager = closing_widget.kernel_manager

        if keepkernel is None and not closing_widget._confirm_exit:
            # don't prompt, just terminate the kernel if we own it
            # or leave it alone if we don't
            keepkernel = closing_widget._existing
        if keepkernel is None: #show prompt
            if kernel_client and kernel_client.channels_running:
                title = self.window().windowTitle()
                cancel = QtWidgets.QMessageBox.Cancel
                okay = QtWidgets.QMessageBox.Ok
                if closing_widget._may_close:
                    msg = "You are closing the tab : "+'"'+self.tab_widget.tabText(current_tab)+'"'
                    info = "Would you like to quit the Kernel and close all attached Consoles as well?"
                    justthis = QtWidgets.QPushButton("&No, just this Tab", self)
                    justthis.setShortcut('N')
                    closeall = QtWidgets.QPushButton("&Yes, close all", self)
                    closeall.setShortcut('Y')
                    # allow ctrl-d ctrl-d exit, like in terminal
                    closeall.setShortcut('Ctrl+D')
                    box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question,
                                            title, msg)
                    box.setInformativeText(info)
                    box.addButton(cancel)
                    box.addButton(justthis, QtWidgets.QMessageBox.NoRole)
                    box.addButton(closeall, QtWidgets.QMessageBox.YesRole)
                    box.setDefaultButton(closeall)
                    box.setEscapeButton(cancel)
                    pixmap = QtGui.QPixmap(self._app.icon.pixmap(QtCore.QSize(64,64)))
                    box.setIconPixmap(pixmap)
                    reply = box.exec_()
                    if reply == 1: # close All
                        for slave in slave_tabs:
                            background(slave.kernel_client.stop_channels)
                            self.tab_widget.removeTab(self.tab_widget.indexOf(slave))
                        kernel_manager.shutdown_kernel()
                        self.tab_widget.removeTab(current_tab)
                        background(kernel_client.stop_channels)
                    elif reply == 0: # close Console
                        if not closing_widget._existing:
                            # Have kernel: don't quit, just close the tab
                            closing_widget.execute("exit True")
                        self.tab_widget.removeTab(current_tab)
                        background(kernel_client.stop_channels)
                else:
                    reply = QtWidgets.QMessageBox.question(self, title,
                        "Are you sure you want to close this Console?"+
                        "\nThe Kernel and other Consoles will remain active.",
                        okay|cancel,
                        defaultButton=okay
                        )
                    if reply == okay:
                        self.tab_widget.removeTab(current_tab)
        elif keepkernel: #close console but leave kernel running (no prompt)
            self.tab_widget.removeTab(current_tab)
            background(kernel_client.stop_channels)
        else: #close console and kernel (no prompt)
            self.tab_widget.removeTab(current_tab)
            if kernel_client and kernel_client.channels_running:
                for slave in slave_tabs:
                    background(slave.kernel_client.stop_channels)
                    self.tab_widget.removeTab(self.tab_widget.indexOf(slave))
                if kernel_manager:
                    kernel_manager.shutdown_kernel()
                background(kernel_client.stop_channels)

        self.update_tab_bar_visibility()


class ExternalIPython(JupyterApp, JupyterConsoleApp):
    """Modifed version of qtconsole.qtconsoleapp.JupyterQtConsoleApp
    """
    #  NOTE 2020-07-08 08:23:39
    #
    # uses the exising app (Scipyen) so no more init_qt_app()
    #
    # there is one python app and one PyQt GUI app (in the original, started by
    # the qtconsole)
    #
    # in the original start mechanism is:
    # 
    # * call class method launch_instance - which calls (by MRO) Application.launch_instance()
    # (from traitlets.config.application) to launch a global instance
    #   in turn, Application.launch_instance creates an instance of the python app
    #   initializes (app.initialize()) and starts (app.start())
    #
    name = 'Scypien External IPython Console'
    version = __version__
    description = """
        The Jupyter QtConsole.

        This launches a Console-style application using Qt.  It is not a full
        console, in that launched terminal subprocesses will not be able to accept
        input.

    """
    classes = [JupyterWidget] + JupyterConsoleApp.classes
    flags = Dict(flags)
    aliases = Dict(aliases)
    frontend_flags = Any(qt_flags)
    frontend_aliases = Any(qt_aliases)
    kernel_client_class = QtKernelClient
    kernel_manager_class = QtKernelManager

    stylesheet = Unicode('', config=True,
        help="path to a custom CSS stylesheet")

    hide_menubar = CBool(False, config=True,
        help="Start the console window with the menu bar hidden.")

    maximize = CBool(False, config=True,
        help="Start the console window maximized.")

    plain = CBool(False, config=True,
        help="Use a plaintext widget instead of rich text (plain can't print/save).")

    display_banner = CBool(True, config=True,
        help="Whether to display a banner upon starting the QtConsole."
    )

    def _plain_changed(self, name, old, new):
        kind = 'plain' if new else 'rich'
        self.config.ConsoleWidget.kind = kind
        if new:
            self.widget_factory = JupyterWidget
        else:
            self.widget_factory = RichJupyterWidget

    # the factory for creating a widget
    widget_factory = Any(RichJupyterWidget)

    def parse_command_line(self, argv=None):
        super().parse_command_line(argv)
        self.build_kernel_argv(self.extra_args)


    def new_frontend_master(self):
        """ Create and return new frontend attached to new kernel, launched on localhost.
        """
        kernel_manager = self.kernel_manager_class(
                                connection_file=self._new_connection_file(),
                                parent=self,
                                autorestart=True,
        )
        # start the kernel
        kwargs = {}
        # FIXME: remove special treatment of IPython kernels
        if self.kernel_manager.ipykernel:
            kwargs['extra_arguments'] = self.kernel_argv
        kernel_manager.start_kernel(**kwargs)
        kernel_manager.client_factory = self.kernel_client_class
        kernel_client = kernel_manager.client()
        kernel_client.start_channels(shell=True, iopub=True)
        widget = self.widget_factory(config=self.config,
                                     local_kernel=True)
        self.init_colors(widget)
        widget.kernel_manager = kernel_manager
        widget.kernel_client = kernel_client
        widget._existing = False
        widget._may_close = True
        widget._confirm_exit = self.confirm_exit
        widget._display_banner = self.display_banner
        return widget

    def new_frontend_connection(self, connection_file):
        """Create and return a new frontend attached to an existing kernel.

        Parameters
        ----------
        connection_file : str
            The connection_file path this frontend is to connect to
        """
        kernel_client = self.kernel_client_class(
            connection_file=connection_file,
            config=self.config,
        )
        kernel_client.load_connection_file()
        kernel_client.start_channels()
        widget = self.widget_factory(config=self.config,
                                     local_kernel=False)
        self.init_colors(widget)
        widget._existing = True
        widget._may_close = False
        widget._confirm_exit = False
        widget._display_banner = self.display_banner
        widget.kernel_client = kernel_client
        widget.kernel_manager = None
        return widget

    def new_frontend_slave(self, current_widget):
        """Create and return a new frontend attached to an existing kernel.

        Parameters
        ----------
        current_widget : JupyterWidget
            The JupyterWidget whose kernel this frontend is to share
        """
        kernel_client = self.kernel_client_class(
                                connection_file=current_widget.kernel_client.connection_file,
                                config = self.config,
        )
        kernel_client.load_connection_file()
        kernel_client.start_channels()
        widget = self.widget_factory(config=self.config,
                                local_kernel=False)
        self.init_colors(widget)
        widget._existing = True
        widget._may_close = False
        widget._confirm_exit = False
        widget._display_banner = self.display_banner
        widget.kernel_client = kernel_client
        widget.kernel_manager = current_widget.kernel_manager
        return widget
    
    def init_qt_elements(self):
        # Create the widget.

        base_path = os.path.abspath(os.path.dirname(__file__))
        #icon_path = os.path.join(base_path, 'resources', 'icon', 'JupyterConsole.svg')
        icon_path = os.path.join(base_path, 'resources', 'images', 'ipython.svg')
        self.app.icon = QtGui.QIcon(icon_path)
        QtWidgets.QApplication.setWindowIcon(self.app.icon)

        ip = self.ip
        local_kernel = (not self.existing) or is_local_ip(ip)
        self.widget = self.widget_factory(config=self.config,
                                        local_kernel=local_kernel)
        self.init_colors(self.widget)
        self.widget._existing = self.existing
        self.widget._may_close = not self.existing
        self.widget._confirm_exit = self.confirm_exit
        self.widget._display_banner = self.display_banner

        self.widget.kernel_manager = self.kernel_manager
        self.widget.kernel_client = self.kernel_client
        
        self.window = ExternalConsoleWindow(self.app,
                                confirm_exit=self.confirm_exit,
                                new_frontend_factory=self.new_frontend_master,
                                slave_frontend_factory=self.new_frontend_slave,
                                connection_frontend_factory=self.new_frontend_connection,
                                )
        
        self.window.log = self.log
        self.window.add_tab_with_frontend(self.widget)
        self.window.init_menu_bar()

        # Ignore on OSX, where there is always a menu bar
        if sys.platform != 'darwin' and self.hide_menubar:
            self.window.menuBar().setVisible(False)

        self.window.setWindowTitle('External Scipyen Console')

    def init_colors(self, widget):
        """Configure the coloring of the widget"""
        # Note: This will be dramatically simplified when colors
        # are removed from the backend.

        # parse the colors arg down to current known labels
        cfg = self.config
        colors = cfg.ZMQInteractiveShell.colors if 'ZMQInteractiveShell.colors' in cfg else None
        style = cfg.JupyterWidget.syntax_style if 'JupyterWidget.syntax_style' in cfg else None
        sheet = cfg.JupyterWidget.style_sheet if 'JupyterWidget.style_sheet' in cfg else None

        # find the value for colors:
        if colors:
            colors=colors.lower()
            if colors in ('lightbg', 'light'):
                colors='lightbg'
            elif colors in ('dark', 'linux'):
                colors='linux'
            else:
                colors='nocolor'
        elif style:
            if style=='bw':
                colors='nocolor'
            elif styles.dark_style(style):
                colors='linux'
            else:
                colors='lightbg'
        else:
            colors=None

        # Configure the style
        if style:
            widget.style_sheet = styles.sheet_from_template(style, colors)
            widget.syntax_style = style
            widget._syntax_style_changed()
            widget._style_sheet_changed()
        elif colors:
            # use a default dark/light/bw style
            widget.set_default_style(colors=colors)

        if self.stylesheet:
            # we got an explicit stylesheet
            if os.path.isfile(self.stylesheet):
                with open(self.stylesheet) as f:
                    sheet = f.read()
            else:
                raise IOError("Stylesheet %r not found." % self.stylesheet)
        if sheet:
            widget.style_sheet = sheet
            widget._style_sheet_changed()


    def init_signal(self):
        """allow clean shutdown on sigint"""
        signal.signal(signal.SIGINT, lambda sig, frame: self.exit(-2))
        # need a timer, so that QApplication doesn't block until a real
        # Qt event fires (can require mouse movement)
        # timer trick from http://stackoverflow.com/q/4938723/938949
        timer = QtCore.QTimer()
         # Let the interpreter run each 200 ms:
        timer.timeout.connect(lambda: None)
        timer.start(200)
        # hold onto ref, so the timer doesn't get cleaned up
        self._sigint_timer = timer

    def _deprecate_config(self, cfg, old_name, new_name):
        """Warn about deprecated config."""
        if old_name in cfg:
            self.log.warning(
                "Use %s in config, not %s. Outdated config:\n    %s",
                new_name, old_name,
                '\n    '.join(
                    '{name}.{key} = {value!r}'.format(key=key, value=value,
                                                      name=old_name)
                    for key, value in self.config[old_name].items()
                )
            )
            cfg = cfg.copy()
            cfg[new_name].merge(cfg[old_name])
            return cfg

    def _init_asyncio_patch(self):
        """
        Same workaround fix as https://github.com/ipython/ipykernel/pull/456

        Set default asyncio policy to be compatible with tornado
        Tornado 6 (at least) is not compatible with the default
        asyncio implementation on Windows
        Pick the older SelectorEventLoopPolicy on Windows
        if the known-incompatible default policy is in use.
        do this as early as possible to make it a low priority and overrideable
        ref: https://github.com/tornadoweb/tornado/issues/2608
        FIXME: if/when tornado supports the defaults in asyncio,
               remove and bump tornado requirement for py38
        """
        if sys.platform.startswith("win") and sys.version_info >= (3, 8):
            import asyncio
            try:
                from asyncio import (
                    WindowsProactorEventLoopPolicy,
                    WindowsSelectorEventLoopPolicy,
                )
            except ImportError:
                pass
                # not affected
            else:
                if type(asyncio.get_event_loop_policy()) is WindowsProactorEventLoopPolicy:
                    # WindowsProactorEventLoopPolicy is not compatible with tornado 6
                    # fallback to the pre-3.8 default of Selector
                    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

    @catch_config_error
    def initialize(self, argv=None):
        self._init_asyncio_patch()
        
        # NOTE 2020-07-08 09:17:44
        # this is the GUI Pyqt app (providing a GUI event loop etc)
        #self.init_qt_app()
        self.app = QtWidgets.QApplication.instance()
        super().initialize(argv)
        if self._dispatching:
            return
        # handle deprecated renames
        for old_name, new_name in [
            ('IPythonQtConsoleApp', 'JupyterQtConsole'),
            ('IPythonWidget', 'JupyterWidget'),
            ('RichIPythonWidget', 'RichJupyterWidget'),
        ]:
            cfg = self._deprecate_config(self.config, old_name, new_name)
            if cfg:
                self.update_config(cfg)
        JupyterConsoleApp.initialize(self,argv)
        self.init_qt_elements()
        self.init_signal()

    def start(self):
        super().start()

        # draw the window
        if self.maximize:
            self.window.showMaximized()
        else:
            self.window.show()
        self.window.raise_()

        # Start the application main loop.
        #self.app.exec_() # already happening

    @classmethod
    def launch(cls, argv=None, **kwargs):
        # the launch_instance mechanism in jupyter and qtconsole does not return
        # an instance of this python "app"
        app = cls.instance(**kwargs)
        app.initialize(argv)
        app.start()
        
        return app

# NOTE: use Jupyter (IPython >= 4.x and qtconsole / qt5 by default)
class ScipyenConsole(RichJupyterWidget):
    """Console with in-process kernel manager for pythonic command interface.
    Uses an in-process kernel generated and managed by QtInProcessKernelManager.
    """
    historyItemsDropped = pyqtSignal()
    workspaceItemsDropped = pyqtSignal()
    #workspaceItemsDropped = pyqtSignal(bool)
    loadUrls = pyqtSignal(object, bool, QtCore.QPoint)
    pythonFileReceived = pyqtSignal(str, QtCore.QPoint)
    
    def __init__(self, mainWindow=None):
        ''' ScipyenConsole constructor
        
        Using Qt5 gui by default
        NOTE:
        Since August 2016 -- using Jupyter/IPython 4.x and qtconsole
        
        '''
        super(RichJupyterWidget, self).__init__()
        
        #if isinstance(mainWindow, (ScipyenWindow, type(None))):
        if type(mainWindow).__name__ ==  "ScipyenWindow":
            self.mainWindow = mainWindow
            
        else:
            self.mainWindow = None
        
        # NOTE 2020-07-07 12:32:40
        # ALWAYS uses the in-proces Qt kernel manager
        self.kernel_manager = QtInProcessKernelManager() # what if gui is NOT Qt?
            
        self.kernel_manager.start_kernel()
        self.ipkernel = self.kernel_manager.kernel
        
        ## NOTE: 2016-03-20 14:37:37
        ## this must be set BEFORE start_channels is called
        ##self.ipkernel.shell.banner2 = "\n".join(ScipyenConsole.banner)
        #self.ipkernel.shell.banner2 = u'\n*** NOTE: ***\n\nUser variables created here in console be visible in the User variables tab of the PICT main window.\n' +\
        #u'\n\nThe Pict main window GUI object is accessible from the console as `mainWindow` or `mainWindow` (an alias of mainWindow)' +\
        #u'\n\nExcept for user variables, if any of `mainWindow`, `mainWindow`, or loaded modules are deleted from the console workspace by calling del(...), they can be restored using the `Console/Restore Namespace` menu item.' +\
        #u'\n\nThe "Workspace" dock widget of the Pict main window shows variables shared between the console (the IPython kernel) and the Pict window.' +\
        #u'\n\nThe "matplotlib.pyplot" module is aliased as "plt". Use this prefix for pyplot functions (e.g., plt.plot(), plt.cla(), etc.)' +\
        #u'\n\nTo clear this window at any time type %clear at the prompt'+\
        #u'\n\nFor further details type console_info()'
        
        #self.kernel.shell.push(kwarg)
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        
        self.ipkernel.gui = "qt"
        # NOTE: 2019-08-07 16:34:58
        # enforce qt5 backend for matplotlib
        # see NOTE: 2019-08-07 16:34:23 
        self.ipkernel.shell.run_line_magic("matplotlib", "qt5")
        
        self.drop_cache=None
        
        self.defaultFixedFont = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        
        self.clear_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_X), self)
        
        self.clear_shortcut.activated.connect(self.slot_clearConsole)
        
        #self.settings = QtCore.QSettings("PICT", "PICT")
        self.settings = QtCore.QSettings()
        
        self._load_settings_()
        
    def closeEvent(self, evt):
        self._save_settings_()
        evt.accept()

    def _save_settings_(self):
        self.settings.setValue("Console/Size", self.size())
        self.settings.setValue("Console/Position", self.pos())
        self.settings.setValue("Console/FontFamily", self.font.family())
        self.settings.setValue("Console/FontPointSize", self.font.pointSize())
        self.settings.setValue("Console/FontStyle", self.font.style())
        self.settings.setValue("Console/FontWeight", self.font.weight())

    def _load_settings_(self):
        # located in $HOME/.config/Scipyen/Scipyen.conf
        winSize = self.settings.value("Console/Size", QtCore.QSize(600, 350))
        winPos = self.settings.value("Console/Position", QtCore.QPoint(0,0))
        fontFamily = self.settings.value("Console/FontFamily", self.defaultFixedFont.family())
        fontSize = int(self.settings.value("Console/FontPointSize", self.defaultFixedFont.pointSize()))
        fontStyle = int(self.settings.value("Console/FontStyle", self.defaultFixedFont.style()))
        fontWeight = int(self.settings.value("Console/FontWeight", self.defaultFixedFont.weight()))
        
        console_font = QtGui.QFont(fontFamily, fontSize, fontWeight, italic = fontStyle > 0)
        
        #self.setFont(console_font)
        
        #self._set_font(console_font)
        
        self.font = console_font

        self.move(winPos)
        self.resize(winSize)
        self.setAcceptDrops(True)
        
        
    def dragEnterEvent(self, evt):
        #if "text/plain" in evt.mimeData().formats():
            ##print("mime data text:\n", evt.mimeData().text())
            #text = evt.mimeData().text()
            #if len(text):
                #self.drop_cache = text
            #else:
                #self.drop_cache = evt.mimeData().data("text/plain").data().decode()

            #evt.acceptProposedAction();
            
        evt.acceptProposedAction();
        evt.accept()
        
    @safeWrapper
    def dropEvent(self, evt):
        from textwrap import dedent
        #print("ScipyenConsole.dropEvent: evt", evt)
        #data = evt.mimeData().data(evt.mimeData().formats()[0])
        src = evt.source()
        #print("ScipyenConsole.dropEvent: evt.source:", src)
        
        #print("ScipyenConsole.dropEvent: evt.mimeData()", evt.mimeData())
        
        #print("ScipyenConsole.dropEvent: evt.proposedAction()", evt.proposedAction())
        
        #print("ScipyenConsole.dropEvent: evt.mimeData().hasText()", evt.mimeData().hasText())
        #print(dir(evt.keyboardModifiers()))
        #print("ScipyenConsole.dropEvent: event source: %s" % src)
        
        #print("ScipyenConsole.dropEvent: \nevt mimeData %s" % evt.mimeData())
        #print("ScipyenConsole.dropEvent: \ndata: %s \nsrc: %s" % (text, src))
        
        # NOTE: 2019-08-10 00:23:42
        # for drop events issued by mainWindow's workspace viewer and command
        # history ignore the mimeData and simply paste the text via clipboard
        # (is there a way to bypass this? it work well as it is, but...)
        # we do this asynchronously, via Qt's signal/slot mechanism
        #NOTE: 2017-03-21 22:56:23 ScipyenWindow is signalled to copy the command:
        #
        # copy string(s) to the system's cliboard then paste them directly 
        # into the console
        # this works fine, with the added bonus that the drag/dropped commands 
        # are also available on the system clipboard to paste onto some text 
        # editor
        #if isinstance(self.mainWindow, ScipyenWindow):
        #if isinstance(self.mainWindow, ScipyenWindow) and src is self.mainWindow.workspaceView:
        if type(self.mainWindow).__name__ == "ScipyenWindow" and src is self.mainWindow.workspaceView:
            #print("ScipyenConsole.dropEvent mime data has text:",  evt.mimeData().hasText())
            #if evt.mimeData().hasText():
                #print(evt.mimeData().text())
            #print("ScipyenConsole.dropEvent mime data has urls:", evt.mimeData().hasUrls())
            #print("ScipyenConsole.dropEvent possible actions:", evt.possibleActions())
            #print("ScipyenConsole.dropEvent proposed action:", evt.proposedAction())
            #print("ScipyenConsole.dropEvent actual drop action:",  evt.dropAction())
            
            #print(evt.keyboardModifiers() & QtCore.Qt.ShiftModifier)
            
            #quoted = evt.keyboardModifiers() & QtCore.Qt.ShiftModifier
            
            #linesep = evt.keyboardModifiers() & QtCore.Qt.ControlModifier
            
            #self.mainWindow.slot_pasteWorkspaceSelection()
            # NOTE: 2019-08-10 00:29:04
            # do the above asynchronously
            #self.workspaceItemsDropped.emit(bool(quoted))
            self.workspaceItemsDropped.emit()
            
        #elif isinstance(self.mainWindow, ScipyenWindow) and src is self.mainWindow.historyTreeWidget:
        elif type(self.mainWindow).__name__ == "ScipyenWindow" and src is self.mainWindow.historyTreeWidget:
            #print(evt.mimeData().hasText())
            #print(evt.mimeData().hasUrls())
            #print(evt.possibleActions())
            #print(evt.proposedAction())
            #print(evt.dropAction())
            
            #self.mainWindow.slot_pasteHistorySelection()
            # NOTE: 2019-08-10 00:29:27
            # do the above asynchronously
            self.historyItemsDropped.emit()
            
        #elif isinstance(self.mainWindow, ScipyenWindow) and src is self.mainWindow.fileSystemTreeView:
        elif type(self.mainWindow).__name__ == "ScipyenWindow" and src is self.mainWindow.fileSystemTreeView:
            # NOTE: 2019-08-10 00:54:40
            # TODO: load data from disk
            pass
                
                
            #evt.accept()
                
        else:
            #NOTE: 2019-08-02 13:35:52
            # allow dropping text in the console 
            # useful for drag&drop python code directly from a python source file
            # opened in a text editor (that also supports drag&drop)
            # event source is from outside the Pict application (i.e. it is None)
            #print("ScipyenConsole.dropEvent: \nproposed action: %s" % evt.proposedAction())
            
            #print("ScipyenConsole.dropEvent source:",  src)
            #print("ScipyenConsole.dropEvent mime data has text:",  evt.mimeData().hasText())
            #print("ScipyenConsole.dropEvent mime data has urls:",  evt.mimeData().hasUrls())
            #print("ScipyenConsole.dropEvent possible actions:",  evt.possibleActions())
            #print("ScipyenConsole.dropEvent proposed action:",  evt.proposedAction())
            #print("ScipyenConsole.dropEvent actual drop action:",  evt.dropAction())
            
            if evt.mimeData().hasUrls():
                urls = evt.mimeData().urls()
                
                if len(urls) == 1 and (urls[0].isRelative() or urls[0].isLocalFile()) and os.path.isfile(urls[0].path()):
                    # check if this is a python source file
                    mimeType = QtCore.QMimeDatabase().mimeTypeForFile(QtCore.QFileInfo(urls[0].path()))
                    
                    if all([s in mimeType.name() for s in ("text", "python")]):
                        self.pythonFileReceived.emit(urls[0].path(), evt.pos())
                        return
                
                # NOTE: 2019-08-10 00:32:00
                # set mainWindow to load the URL asynchronously
                # this also allows us to decide if we should also cd to the
                # directory of the (local) URL, by pressing SHIFT while dropping
                self.loadUrls.emit(urls, evt.keyboardModifiers() == QtCore.Qt.ShiftModifier, evt.pos())
                
            elif evt.mimeData().hasText() and len(evt.mimeData().text()):
                # NOTE: 2019-08-10 00:33:00
                # just write at the console whatever text has been dropped
                if evt.proposedAction() in (QtCore.Qt.CopyAction, QtCore.Qt.MoveAction):
                    text = evt.mimeData().text()
                    #print("ScipyenConsole.dropEvent: text", text)
                    #print("ScipyenConsole.dropEvent: mimeData.formats()", evt.mimeData().formats())
                    echoing = not bool(evt.keyboardModifiers() & QtCore.Qt.ShiftModifier)
                    store = bool(evt.keyboardModifiers() & QtCore.Qt.ControlModifier)
                    
                    #print(echoing)
                    
                    # NOTE: 2019-08-13 11:08:14
                    # TODO: allow for running the code without writing it in console
                    # but store in history nevertheless (maybe?)
                    
                    if echoing:
                        # NOTE: 2019-08-13 11:03:52
                        # displays the text in the console to be edited
                        # to execute place cursor at the end of text and press
                        # ENTER
                        # executed statements are stored in python's command history
                        self.writeText(text)
                    
                    else:
                        # NOTE: 2019-08-13 11:04:26
                        # does NOT write to the console, does NOT store in history
                        wintitle = self.windowTitle()
                        self.setWindowTitle("%s #executing..." % wintitle)
                        self.ipkernel.shell.run_cell(text, store_history = False, silent=True, shell_futures=True)
                        self.setWindowTitle(wintitle)
                        
            else:
                # mime data formats contains text/plain but data is QByteArray
                # (which wraps a Python bytes object)
                if "text/plain" in evt.mimeData().formats():
                    #print("mime data text:\n", evt.mimeData().text())
                    text = evt.mimeData().text()
                    if len(text) == 0:
                        text = evt.mimeData().data("text/plain").data().decode()
                        
                    if len(text):
                        self.writeText(text)

            self.drop_cache=None
                
        evt.accept()
        
        
        
        #NOTE:
        #NOTE: Other considered options:
        #NOTE: 2017-03-21 22:41:53 connect this sigal to the _rerunCommand slot of ScipyenWindow:
        #NOTE: half-baked approach that does not actually
        #NOTE: paste the commands as input, but instead executes them directly
        #NOTE: FIXME NOT REALLY WHAT IS INTENDED
        #NOTE: TODO either use the paste mechanism of the ControlWidget superclass 
        #NOTE: (tricky, because that accesses private member of that superclass)
        #NOTE: TODO or completely customize the item model of the history tree such that 
        #NOTE: upon drag event, the items DATA (specifically the command string(s)) 
        #NOTE: are encoded as text mime format and thus decoded here
        #NOTE: TODO FIXME this last suggestion would leave me again with the issue
        #NOTE: of pasting them directly onto underlying text widget of the console, 
        #NOTE: which is a private member
        
        #print("dropEvent")
        #print("Event: ",evt)
        #print("proposed action: ",evt.proposedAction())
        #print("Event mime data formats: ", evt.mimeData().formats())
        #print("Event data: ", data, " ", repr(data))
        #print("Event source: ", repr(evt.source()))

    @safeWrapper
    def __write_text_in_console_buffer__(self, text):
        from textwrap import dedent
        # NOTE:2019-08-02 13:59:26
        # code below taken from console_widget module in qtconsole package
        if isinstance(text, str):
            self._keep_cursor_in_buffer()
            cursor = self._control.textCursor()
            self._insert_plain_text_into_buffer(cursor, dedent(text))
            
    @safeWrapper
    def writeText(self, text):
        """Writes a text in console buffer
        """
        if isinstance(text, str):
            self.__write_text_in_console_buffer__(text)
            
        elif isinstance(text, (tuple, list) and all([isinstance(s, str) for s in text])):
            self.__write_text_in_console_buffer__("\n".join(text))
        
    @safeWrapper
    def slot_clearConsole(self):
        self.ipkernel.shell.run_line_magic("clear", "", 2)

# TODO 2016-03-24 13:47:48 
# I quite like the stock Qt console of IPython that is launched by qtconsoleapp
# - it's a customized QMainWindow with a rich ipython widget as the actual "console"
#   with a lot of nice bells and whistles: magics listing, help, etc, but also
#   functionality that I don't want/need: tabbed consoles (with new or the same kernel),
#   possibility to restart/stop the current kernel
#
#   Therefore I'm deriving from it and override functions I find not necessary for picty
#
#   Actually it might be just damn simpler to generate my own console main window class
#
#   TODO
#class _PictConsole(ConsoleMainWindow):
    #pass

