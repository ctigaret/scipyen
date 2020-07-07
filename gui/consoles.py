from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty

#### BEGIN ipython/jupyter modules
from qtconsole.rich_jupyter_widget import RichJupyterWidget # DIFFERENT from that in qtconsoleapp module !!!
#NOTE: 2017-03-21 01:09:05 inheritance chain ("<" means inherits from)
# RichJupyterWidget < RichIPythonWidget < JupyterWidget < FrontendWidget < (HistoryConsoleWidget, BaseFrontendMixin)
#in turn, FrontendWidget < ... < ConsoleWidget which implements underlying 
# Qt logic, including drag'n drop
#from qtconsole.mainwindow import MainWindow as ConsoleMainWindow


import jupyter_client

from qtconsole.inprocess import QtInProcessKernelManager

from IPython.utils.ipstruct import Struct as IPStruct

from IPython.core.history import HistoryAccessor

from IPython.lib.deepreload import reload as dreload

from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic,
                                needs_local_scope)

from IPython.display import set_matplotlib_formats

#### END ipython/jupyter modules

from core import prog
from core.prog import safeWrapper


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
    
    #def __init__(self, kernel_manager=None, mainWindow=None):
    def __init__(self, mainWindow=None):
        ''' ScipyenConsole constructor
        
        Using Qt5 gui by default
        NOTE:
        Since August 2016 -- using Jupyter/IPython 4.x and qtconsole
        
        '''
        super(RichJupyterWidget, self).__init__()
        
        #if isinstance(mainWindow, (ScipyenWindow, type(None))):
        if type(mainWindow).__name__ ==  "Scipyenwindow":
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
        winSize = self.settings.value("Console/Size", QtCore.QSize(600, 350))
        winPos = self.settings.value("Console/Position", QtCore.QPoint(0,0))
        fontFamily = self.settings.value("Console/FontFamily", self.defaultFixedFont.family())
        fontSize = int(self.settings.value("Console/FontPointSize", self.defaultFixedFont.pointSize()))
        fontStyle = int(self.settings.value("Console/FontStyle", self.defaultFixedFont.style()))
        fontWeight = int(self.settings.value("Console/FontWeight", self.defaultFixedFont.weight()))
        
        console_font = QtGui.QFont(fontFamily, fontSize, fontWeight, italic = fontStyle > 0)
        
        self.setFont(console_font)
        
        self._set_font(console_font)
        
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
        if isinstance(self.mainWindow, ScipyenWindow) and src is self.mainWindow.workspaceView:
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
            
        elif isinstance(self.mainWindow, ScipyenWindow) and src is self.mainWindow.historyTreeWidget:
            #print(evt.mimeData().hasText())
            #print(evt.mimeData().hasUrls())
            #print(evt.possibleActions())
            #print(evt.proposedAction())
            #print(evt.dropAction())
            
            #self.mainWindow.slot_pasteHistorySelection()
            # NOTE: 2019-08-10 00:29:27
            # do the above asynchronously
            self.historyItemsDropped.emit()
            
        elif isinstance(self.mainWindow, ScipyenWindow) and src is self.mainWindow.fileSystemTreeView:
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

