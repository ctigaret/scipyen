# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


"""Provides two IPython (Jupyter) Qt-based consoles for the Scipyen application.

1) An "internal" Jupyter qt console, running an in-process IPython kernel for 
dat-to-day use.

2) An "external" Jupyter qt console running an external (or "remote") 
IPython kernel.

The main reason for the latter is the ability to run NEURON simulator (with its
python bindings) without it bringing down the whole Scipyen app upon quitting
NEURON from its Gui.

As things stand (2020-07-10 15:29:33) quitting the NEURON from the Gui crashes
the (I)python kernel under which the NEURON Gui has been launched. If this
were to happen inside the Scipyen's console (which is using an in-process kernel)
this would also crash the Scipyen application.

If NEURON Gui were to be launched inside an "external" kernel (i.e., running as 
a separate process) the Scipyen app would remain alive beyond the lifetime of 
the external kernel.

A very convenient solution is therefore to employ a JupyterQtConsoleApp-like 
console that uses Scipyen's own Qt Gui event loop, to connect to a remote 
ipython kernel running NEURON/python.

Currently I have implemented this solution in the External Jupyter Console (a 
modifed verison of JupyterQtConsoleApp). This inherits from JupyerApp and 
JupyterConsoleApp, uses qtconsole code logic for the Qt gui and insulates the
remote kernel crash (which can then be restared for a plain new session).

A (rather contorted) communcations protocol between the remote kernel namespace
and Scipyen's in-process ipython kernel namespace (a.k.a the 'User workspace'
displayed in the Workspace viewer in Scipyen's main window) allows user-triggered
copy of variables between the two namespaces and provides a mechanism to salvage
some of the lost variables across kill - restart cycles.

"""
import os
import signal
import json
import sys, typing, traceback, itertools, subprocess, asyncio
# BEGIN NOTE: 2022-03-05 16:07:04 For execute_request
import inspect, time
# from ipykernel.jsonutil import json_clean
# END
from functools import partial, partialmethod
from collections import OrderedDict
from warnings import warn


from qtpy import (QtCore, QtGui, QtWidgets, )
from qtpy.QtCore import (Signal, Slot, )

#### BEGIN ipython/jupyter modules
from traitlets.config.application import boolean_flag
from traitlets.config.application import catch_config_error
from traitlets import (
    Dict, Unicode, CBool, Any, Bunch, HasTraits, Instance, Int,
)
from ipykernel.inprocess.ipkernel import InProcessKernel
from ipykernel.inprocess.socket import DummySocket
from jupyter_core.paths import jupyter_runtime_dir
from jupyter_core.application import JupyterApp, base_flags, base_aliases

from jupyter_client.session import Message
from jupyter_client.localinterfaces import is_local_ip
from jupyter_client.consoleapp import (
        JupyterConsoleApp, app_aliases, app_flags,
    )

from qtconsole.svg import save_svg, svg_to_clipboard, svg_to_image

from tornado import ioloop
from tornado.queues import Queue

import zmq

# from qtpy import sip as sip
# import sip

from pygments import styles as pstyles
from pygments.token import Token
from pygments.style import Style    

from qtconsole import styles as styles
from qtconsole import __version__

from qtconsole.frontend_widget import FrontendWidget
from qtconsole.jupyter_widget import JupyterWidget # for use in the External Console
#NOTE: 2017-03-21 01:09:05 inheritance chain ("<" means inherits from)
# RichJupyterWidget < JupyterWidget < FrontendWidget < (HistoryConsoleWidget, BaseFrontendMixin)
# in turn, FrontendWidget < ... < ConsoleWidget which implements underlying Qt
# logic, including drag'n drop
from qtconsole.rich_jupyter_widget import RichJupyterWidget 

from qtconsole.inprocess import QtInProcessKernelManager # for the Scipyen's internal console
from qtconsole.mainwindow import (MainWindow, background,)
from qtconsole.client import QtKernelClient
from qtconsole.manager import QtKernelManager

#### END ipython/jupyter modules
import pkg_resources

#from core import prog
from core.prog import safeWrapper
from core.extipyutils_client import (init_commands, execute, ForeignCall,
                                    nrn_ipython_initialization_cmd,)
from core.strutils import str2symbol

from core.scipyen_config import (markConfigurable, ScipyenConfigurable,
                                 saveWindowSettings, loadWindowSettings,)

from gui.workspacegui import WorkspaceGuiMixin
from gui import scipyen_console_styles
from gui.scipyen_console_styles import *
# from gui.kepler_dark_console_pygment_style import KeplerDark

from gui.guiutils import (get_font_style, get_font_weight,)

if sys.version_info.minor < 11:
    from core import scipyen_inprocess_3_10
    from core.scipyen_inprocess_3_10 import ScipyenInProcessKernel
else:
    ScipyenInProcessKernel = InProcessKernel

#makeConfigurable = WorkspaceGuiMixin.makeConfigurable

if os.environ["QT_API"] in ("pyqt5", "pyside2"):
    consoleLayoutDirection = OrderedDict(sorted(( (name,val) for name, val in vars(QtCore.Qt).items() if isinstance(val, QtCore.Qt.LayoutDirection) ) , 
                                                key = lambda x: x[1]))
else:
    consoleLayoutDirection = OrderedDict(sorted(( (name,val) for name, val in QtCore.Qt.LayoutDirection._member_map_.items()) ,
                                                key = lambda x: x[1].value))

defaultFixedFont = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)

flags = dict(base_flags)
# qt_flags = {
#     'plain' : ({'JupyterQtConsoleApp' : {'plain' : True}},
#             "Disable rich text support."),
# }
qt_flags = dict()
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

def change_error_display_for_style(style:typing.Union[str, Style]):
    # https://stackoverflow.com/questions/70766518/how-to-change-ipython-error-highlighting-color
    
    # TODO: 2024-09-20 12:56:07
    # match tb highlight in ultratb to a specification in the style itself.
    #
    # (for now, it;s just replacing the ugly ansi yellow with the ansi red)
    if isinstance(style, str):
        style = styles.get_style_by_name(style)

    try:
        from IPython.core import ultratb
        ultratb.VerboseTB._tb_highlight = "bg:ansired"
    except Exception:
        print("Error patching background color for tracebacks, they'll be the ugly default instead")


# JUPYTER_PYGMENT_STYLES = list(pstyles.get_all_styles())
# 
# PYGMENT_STYLES = sorted(JUPYTER_PYGMENT_STYLES + StyleNames)

# def available_pygments():
#     # NOTE: 2020-12-22 21:35:30
#     # jupyter_qtconsole_colorschemes has entry points in pygments.styles
#     return list(pstyles.get_all_styles())
# 
# def get_available_syntax_styles():
#     return sorted(list(pstyles.get_all_styles()))
# 
# def get_style_colors(stylename:str) -> dict:
#     if stylename == "KeplerDark":
#         # use my own
#         # TODO: 2024-09-19 15:24:37 
#         # give possibility of 
#         # future additional custom schemes to be packaged with Scipyen
#         style = KeplerDark
#         fgcolor = style.style_for_token(Token.Text)['color'] or ''
#         if len(fgcolor) in (3,6):
#             # could be 'abcdef' or 'ace' hex, which needs '#' prefix
#             try:
#                 int(fgcolor, 16)
#             except TypeError:
#                 pass
#             else:
#                 fgcolor = "#"+fgcolor
# 
#         return dict(
#             bgcolor = style.background_color,
#             select = style.highlight_color,
#             fgcolor = fgcolor
#         )
#     
#     else:
#         return pstyles.get_colors(stylename)
    

#current_syntax_styles = get_available_syntax_styles()

#class ScipyenDummySocket(DummySocket):
    #""" A dummy socket implementing (part of) the zmq.Socket interface. """

    #def getsockopt(self, *args, **kwargs):
        #pass
        ##return subprocess.DEVNULL
    
# class ScipyenInProcessKernel(InProcessKernel):
#     """Workaround the following exception when using InProcessKernel (see below).
#     
#     Traceback (most recent call last):
#     File "/home/.../scipyenv39/lib64/python3.9/site-packages/tornado/ioloop.py", line 741, in _run_callback
#         ret = callback()
#     File "/home/.../scipyenv39/lib/python3.9/site-packages/ipykernel/kernelbase.py", line 419, in enter_eventloop
#         schedule_next()
#     File "/home/.../scipyenv39/lib/python3.9/site-packages/ipykernel/kernelbase.py", line 416, in schedule_next
#         self.io_loop.call_later(0.001, advance_eventloop)
#     AttributeError: 'InProcessKernel' object has no attribute 'io_loop'
#     
#     See also https://github.com/ipython/ipykernel/issues/319
#     
#     (NOTE: This DOES NOT crash the kernel):
#     ERROR:tornado.application:Exception in callback 
#     functools.partial(<bound method Kernel.enter_eventloop of <ipykernel.inprocess.ipkernel.InProcessKernel object at 0x7f0b6abe5730>>)
#     
#     It turns out that all we need is to set eventloop to None so that tornado
#     "stays put".
#     
#     NOTE: 2022-03-05 16:36:35
#     In addition, ScipyenInProcessKernel also overrides execute_request to await 
#     for the _abort_queues instead of calling them directly, see below, at
#     NOTE: 2022-03-05 16:04:03
#     
#     (It is funny that this happens in Scipyen, because this warning does not
#     appear in jupyter qtconsole launched in the same virtual Python environment
#     as Scipyen (Python 3.10.2), and I don't think this has anything to do with 
#     setting eventloop to None)
# 
#     """
#     eventloop = None
#     
#     def __init__(self, **traits):
#         super().__init__(**traits)
#         
#     @asyncio.coroutine
#     def _abort_queues(self):
#         yield
#     
#     async def execute_request(self, stream, ident, parent):
#         """handle an execute_request
#         
#         Overrides ipykernel.inprocess.ipkernel.InProcessKernel which in turn
#         calls ipykernel.kernelbase.Kernel.execute_request, to fix the issue below
#         
#         NOTE: 2022-03-05 16:04:03
#         
#         In the InProcessKernel _abort_queues is a coroutine and not a method 
#         (function); this raises the RuntimeWarning: 
#         coroutine 'InProcessKernel._abort_queues' was never awaited.
#         
#         """
# 
#         with self._redirected_io(): # NOTE: 2022-03-14 22:12:02 this is ESSENTIAL!!!
#             try:
#                 content = parent['content']
#                 code = content['code']
#                 silent = content['silent']
#                 store_history = content.get('store_history', not silent)
#                 user_expressions = content.get('user_expressions', {})
#                 allow_stdin = content.get('allow_stdin', False)
#             except Exception:
#                 self.log.error("Got bad msg: ")
#                 self.log.error("%s", parent)
#                 return
# 
#             stop_on_error = content.get('stop_on_error', True)
# 
#             metadata = self.init_metadata(parent)
# 
#             # Re-broadcast our input for the benefit of listening clients, and
#             # start computing output
#             if not silent:
#                 self.execution_count += 1
#                 self._publish_execute_input(code, parent, self.execution_count)
# 
#             reply_content = self.do_execute(
#                 code, silent, store_history,
#                 user_expressions, allow_stdin,
#             )
#             if inspect.isawaitable(reply_content):
#                 reply_content = await reply_content
# 
#             # Flush output before sending the reply.
#             sys.stdout.flush()
#             sys.stderr.flush()
#             # FIXME: on rare occasions, the flush doesn't seem to make it to the
#             # clients... This seems to mitigate the problem, but we definitely need
#             # to better understand what's going on.
#             if self._execute_sleep:
#                 time.sleep(self._execute_sleep)
# 
#             # Send the reply.
#             reply_content = json_clean(reply_content)
#             metadata = self.finish_metadata(parent, metadata, reply_content)
# 
#             reply_msg = self.session.send(stream, 'execute_reply',
#                                         reply_content, parent, metadata=metadata,
#                                         ident=ident)
# 
#             self.log.debug("%s", reply_msg)
# 
#             if not silent and reply_msg['content']['status'] == 'error' and stop_on_error:
#                 # NOTE: 2022-03-05 16:04:10 
#                 # this apparently fixes the issue at NOTE: 2022-03-05 16:04:03
#                 await self._abort_queues() 

class ScipyenInProcessKernelManager(QtInProcessKernelManager):
    """Starts our own custom ScipyenInProcessKernel
    
    Workaround for a bug (?) in InProcessKernel API.
    
    See ScipyenInProcessKernel docstring.
    
    """
    client_class = 'qtconsole.inprocess.QtInProcessKernelClient'
    
    def start_kernel(self, **kwds):
        self.kernel = ScipyenInProcessKernel(parent=self, session=self.session)

class ConsoleWidget(RichJupyterWidget, ScipyenConfigurable):
    """
    """
    # NOTE: This is , ultimately, a qtconsole.frontend_widget.FrontentWidget
    def __init__(self, *args, **kw):
        super(RichJupyterWidget, self).__init__(*args, **kw)
        self._console_pygment = ""
        self._console_colors = ""
        self.available_colors = ("nocolor", "linux", "lightbg")
        self.scrollbar_positions = Bunch({QtCore.Qt.LeftToRight: "right",
                                           QtCore.Qt.RightToLeft: "left"})
        self.clear_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL | QtCore.Qt.SHIFT | QtCore.Qt.Key_K), self)
        # self.clear_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_K), self)
        
        self.clear_shortcut.activated.connect(self.slot_clearConsole)
        
        self.reset_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL | QtCore.Qt.SHIFT | QtCore.Qt.ALT | QtCore.Qt.Key_K), self)
        # self.reset_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.ALT + QtCore.Qt.Key_K), self)
        self.reset_shortcut.activated.connect(self.slot_resetConsole)
#         
#         self.kind = "plain"
#         self.custom_page_control = QtWidgets.QPlainTextEdit()
        self.kind = "rich"
        self.custom_page_control = QtWidgets.QTextEdit()
        
        if not hasattr(self, "_name_to_svg_map"):
            self._name_to_svg_map = dict()

        ScipyenConfigurable.__init__(self)
        
    def _flush_pending_stream(self):
        """ Flush out pending text into the widget.
        NOTE: 2022-03-14 21:47:39 CMT
        Fixes crashes with long list display until the qtconsole 5.3.0 comes to
        life
        """
        text = self._pending_insert_text
        self._pending_insert_text = []
        buffer_size = self._control.document().maximumBlockCount()
        if buffer_size > 0:
            text = self._get_last_lines_from_list(text, buffer_size)
        text = ''.join(text)
        t = time.time()
        self._insert_plain_text(self._get_end_cursor(), text, flush=True)
        # Set the flush interval to equal the maximum time to update text.
        self._pending_text_flush_interval.setInterval(max(100,
                                                 int(time.time()-t)*1000)) # see NOTE: 2022-03-14 21:47:39 CMT

    def clear_last_input(self):
        """Clears the current block of input NOT executed.
        Removes the last input block which has not been sent for execution.
        Useful to remove any commands typed at the console, but not yet executed,
        when an independent execution request is made (e.g. during launch of a script
        from Scipyen's script manager).
        Without this, the input line would still show the input text giving the 
        false impression that the text had been executed (run)
        """
        cursor = self._control.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QtGui.QTextCursor.StartOfLine,
                            QtGui.QTextCursor.MoveAnchor)
        cursor.movePosition(QtGui.QTextCursor.EndOfBlock,
                            QtGui.QTextCursor.KeepAnchor)
        cursor.insertText('')
        cursor.endEditBlock()
        
    
    @safeWrapper
    @Slot()
    def slot_clearConsole(self):
        self.clear()
        # cursor = self._control.textCursor()
        # cursor.beginEditBlock()
        # cursor.insertText('\n')
        # cursor.endEditBlock()
        
        
    @safeWrapper
    @Slot()
    def slot_resetConsole(self):
        self.reset(clear=True)
        
    @property
    def scrollBarPosition(self):
        return self._control.layoutDirection()
        
    @markConfigurable("ScrollBarPosition", "qt")
    @scrollBarPosition.setter
    def scrollBarPosition(self, value:typing.Union[int, str, QtCore.Qt.LayoutDirection]):
        if isinstance(value, str):
            if value.lower().strip() in ("right", "r"):
                value = QtCore.Qt.LeftToRight
                
            elif value.lower().strip() in ("left", "l"):
                value = QtCore.Qt.RightToLeft
                
            elif value in consoleLayoutDirection:
                value = consoleLayoutDirection[value]
                
            else:
                try:
                    value = int(value)
                    
                except:
                    value = QtCore.Qt.LayoutDirectionAuto
                
        if isinstance(value, int):
            if value not in (QtCore.Qt.LeftToRight, QtCore.Qt.RightToLeft):
                value = QtCore.Qt.LayoutDirectionAuto
                
        elif not isinstance(value, QtCore.Qt.LayoutDirection):
            value = QtCore.Qt.LayoutDirectionAuto

        try:
            # FIXME: 2024-05-02 13:09:28 BUG
            # In PyQt6 (via qtpy) this throws 
            # argument 1 has unexpected type 'LayoutDirection'
            self._control.setLayoutDirection(value)
            self.custom_page_control.setLayoutDirection(value) # doesn't work !?
        except:
            try:
                val = QtCore.Qt.LayoutDirection(value.value)
                self._control.setLayoutDirection(val)
                self.custom_page_control.setLayoutDirection(val) # doesn't work !?
            except:
                traceback.print_exc()
                
        # finally:
        #     traceback.print_exc()
            
    def guiSetScrollBack(self):
        value, ok = QtWidgets.QInputDialog.getInt(self, "Scrollback size (lines)", "Number of scrollback lines (-1 for unlimited)",
                                             value = self.scrollBackSize, min = -1)
        if ok:
            self.scrollBackSize = value
        
    @property
    def scrollBackSize(self):
        return self.buffer_size
    
    @markConfigurable("Scrollback", "qt")
    @scrollBackSize.setter
    def scrollBackSize(self, value:int):
        self.buffer_size = value
        
    @property
    def fontFamily(self):
        return self.font.family()
    
    @markConfigurable("FontFamily", "qt")
    @fontFamily.setter
    def fontFamily(self, val:str):
        font = self.font
        font.setFamily(val)
        self.font = font
        
    @property
    def fontSize(self):
        return self.font.pointSize()
    
    @markConfigurable("FontPointSize", "qt")
    @fontSize.setter
    def fontSize(self, val:int):
        font = self.font
        font.setPointSize(int(val))
        self.font = font
        
    @property
    def fontStyle(self):
        return self.font.style()
        
    @markConfigurable("FontStyle", "qt")
    @fontStyle.setter
    def fontStyle(self, val:typing.Union[int, QtGui.QFont.Style, str]):
        style = get_font_style(val) 
        font  = self.font
        # print(f"{self.__class__.__name__}.fontStyle.setter: current font: {font.family()}; wants style: {style}")
        # FIXME 2024-05-02 13:10:31 BUG
        # in PyQt6 (via qtpy) this throws
        try:
            font.setStyle(QtGui.QFont.Style(style))
        except:
            # print(f"{self.__class__.__name__}.fontStyle.setter style value {style.value}")
            try:
                font.setStyle(QtGui.QFont.Style(style.value))
            except:
                traceback.print_exc()
        # finally:
        #     traceback.print_exc()
        self.font = font
        
    @property
    def fontWeight(self):
        return self.font.weight()
    
    @markConfigurable("FontWeight", "qt")
    @fontWeight.setter
    def fontWeight(self, val:typing.Union[int, QtGui.QFont.Weight, str]):
        weight = get_font_weight(val)
        font = self.font
        font.setWeight(weight)
        self.font = font
        
    @property
    def consoleColors(self):
        return self._console_colors
    
    @markConfigurable("ConsoleColors", "qt")
    @consoleColors.setter
    def consoleColors(self, val:str):
        #print("colors.setter val %s" % val)
        style = self._console_pygment
        
        self.set_pygment(style, val)
        
    # def _create_page_control(self): # doesn't work!
    #     """Overrides the method in qtconsole.ConsoleWidget
    # Keeps the scrollbar position consistent with the terminal console.
    # """
    #     control = super()._create_page_control()
    #     sbPos = self.scrollBarPosition
    #     control.setLayoutDirection(sbPos)
    #     return control
        
    def _set_console_colors(self, colors):
        """Used as a slot for colors menu actions
        """
        self.consoleColors = colors

    # @Slot(str)
    # def _slot_setConsoleColors(self, colors:str):
    #     # NOTE: 2024-09-20 09:51:43 duplicates the above
    #     self.consoleColors = colors
        
    def _set_sb_pos(self, val):# slot for menu action
        """Used as slot for ScrollBarPosition menu actions
        """
        # see sb_menu in _supplement_view_menu_
        self.scrollBarPosition = val
        
    def _set_syntax_style(self, val): # slot for menu action
        """Used as slot for Syntax style menu action
        """
        # print(f"{self.__class__.__name__}._set_syntax_style({val})")
        self.syntaxStyle = val

    # @Slot(str)
    # def _slot_setSyntaxStyle(self, stylename:str):
    #     # NOTE: 2024-09-20 09:50:44 duplicate of the above
    #     self.syntaxStyle = stylename
        
    @property
    def syntaxStyle(self):
        """Name of the syntax highlight pygment (str)
        """
        # update from syntax_style set up via jupyter/pygments mechanism?
        # self._console_pygment = self.syntax_style
        return self._console_pygment
    
    @markConfigurable("SyntaxStyle", "qt")
    @syntaxStyle.setter
    def syntaxStyle(self, style:str):
        colors = self._console_colors
        self.set_pygment(style, colors)
        
    @property
    def isTopLevel(self):
        """Overrides WorkspaceGuiMixin.isToplevel; always True for ScipyenConsole.
        This is because console inherits from RichJupyterWidget where 'parent'
        is a traitlets.Instance property, and for ScipyenConsole is None.
        """
        return True
    

    def _save_settings_(self):
        gname, pfx = saveWindowSettings(self.qsettings, self)#, group_name=self.__class__.__name__)

    #def _load_settings_(self):
        ## located in $HOME/.config/Scipyen/Scipyen.conf
        #gname, pfx = loadWindowSettings(self.qsettings, self)#, group_name=self.__class__.__name__)

    def set_pygment_new(self, scheme:typing.Optional[str]="", colors:typing.Optional[str]=None):
        """Sets up style sheet for console colors and syntax highlighting style.
        
        The console widget (a RichJupyterWidget) takes:
        a) a style specified in a style sheet - used for the general appearance of the console 
        (background and Prmopt colors, etc)
        b) a color syntax highlight scheme - used for syntax highlighting
        
        
        This allows bypassing any style/colors specified in 
        $HOME/.jupyter/jupyter_qtconsole_config.py
        
        and usually retrieved by the app's method config()
        
        Parameter:
        -------------
        
        scheme: str (optional, default is the empty string) - name of available 
                syntax style (pygment).
                
                For a list of available pygment names, see
                
                available_pygments() in this module
                
                When empty or None, reverts to the defaults as set by the jupyter 
                configuration file.
                
        colors: str (optional, default is None) console color set. 
            There are, by defult, three color sets:
            'light' or 'lightbg', 
            'dark' or 'linux',
            'nocolor'
            
        """
        # TODO/FIXME: 2023-06-04 10:23:24
        # figure out how the ?/?? system works, and apply better terminal colors
        #   for dark backgrounds, to it; in fact, apply the curren terminal colors
        #   to the displayed help text as well 
        #   also, figure out how to alter the placement
        #   of the scrollbar when the console is showing the message from ?/??
        #   system -> check out _create_page_control in qtconsole/console_widget.py
        # might have to look at the page and console submodules in IPython/jupyter
        # but requires deep digging into their code
        # import pkg_resources
        #print("ConsoleWidget.set_pygment scheme:", scheme, "colors:", colors)
        if scheme is None or (isinstance(scheme, str) and len(scheme.strip()) == 0):
            self.set_default_style()
            #self._control.style = self._initial_style
            #self.style_sheet = self._initial_style_sheet
            return
        
        # NOTE: 2020-12-23 11:15:50
        # code below is modified from qtconsoleapp module, plus my comments;
        # find the value for colors: there are three color sets for prompts:
        # 1. light or lightbg (i.e. colors suitable for schemes with light background)
        # 2. dark or linux (i.e colors suitable for schemes with dark background)
        # 3. nocolor - for black and white scheme
        #else:
            #colors=None
            
        sheet = None
        
        # NOTE: 2024-09-19 16:21:02 temporary FIX
        if scheme == "KeplerDark":
            scheme = "native"
            
        # if scheme in available_pygments():
        if scheme in PYGMENT_STYLES:
            #print("found %s scheme" % scheme)
            # rules of thumb:
            #
            # 1. the syntax highlighting scheme is set by setting the console 
            # (RichJupyterWidget) 'syntax_style' attribute to scheme. 
            #
            # 2. the style sheet gives the widget colors ("style") - so we always 
            #   need a style sheet, and we "pygment" the console by setting its
            #   'style_sheet' attribute. NOTE that schemes do not always provide
            #   prompt styling colors, therefore we need to set up a style sheet 
            #   dynamically based on the colors guessed according to whether the
            #   scheme is a "dark" one or not.
            #
            # NOTE: the approach described above is the one used in qtconsole
            #
            if scheme == "KeplerDark":
                # use my own - TODO: 2024-09-19 15:24:37 give possibility of 
                # future additional custom schemes to be packaged with Scipyen
                stylecolors = get_style_colors(scheme)
                sheet = styles.default_dark_style_template%stylecolors
                colors = "linux"
                
            else:
                if isinstance(colors, str) and len(colors.strip()): # force colors irrespective of scheme
                    colors=colors.lower()
                    if colors in ('lightbg', 'light'):
                        colors='lightbg'
                    elif colors in ('dark', 'linux'):
                        colors='linux'
                    else:
                        colors='nocolor'
                
                else: # (colors is "" or anything else)
                    # make an informed choice of colors, according to whether the scheme
                    # is bright (light) or dark
                    if scheme=='bw':
                        colors='nocolor'
                    elif styles.dark_style(scheme):
                        colors='linux'
                    else:
                        colors='lightbg'
                try:
                    sheetfile = pkg_resources.resource_filename("jupyter_qtconsole_colorschemes", "%s.css" % scheme)
                    if os.path.isfile(sheetfile):
                        with open(sheetfile) as f:
                            sheet = f.read()
                except:
                    # revert to built-in schemes
                    sheet = styles.sheet_from_template(scheme, colors)
                      
            if sheet:
                # also need to call notifiers - this is the order in which they
                # are called in qtconsoleapp module ('JupyterConsoleApp.init_colors')
                # not sure whether it makes a difference but stick to it for now
                self.syntax_style = scheme
                self.style_sheet = sheet
                self._syntax_style_changed()
                self._style_sheet_changed()
                
                # remember these changes - to save them in _save_settings_()
                self._console_pygment = scheme
                self._console_colors = colors
                
                if self.kernel_client:
                    self._execute(f"colors {colors}", True)
                            #self.reset(clear=True)
                            #self.kernel_client.execute("colors %s"% colors, True)
                        
                        # NOTE: 2021-01-08 14:23:14
                        # These two will affect all Jupyter console apps in Scipyen that
                        # will be launched AFTER the internal console has been initiated. 
                        # These include the ExternalIPython.
                        #JupyterWidget.style_sheet = sheet
                        #JupyterWidget.syntax_style = scheme
                        

    def set_pygment(self, scheme:typing.Optional[str]="", colors:typing.Optional[str]=None):
        """Sets up style sheet for console colors and syntax highlighting style.
        
        The console widget (a RichJupyterWidget) takes:
        a) a style specified in a style sheet - used for the general appearance of the console 
        (background and ormopt colors, etc)
        b) a color syntax highlight scheme - used for syntax highlighting
        
        
        This allows bypassing any style/colors specified in 
        ~./jupyter/jupyter_qtconsole_config.py
        
        Parameter:
        -------------
        
        scheme: str (optional, default is the empty string) - name of available 
                syntax style (pygment).
                
                For a list of available pygment names, see
                
                available_pygments() in this module
                
                When empty or None, reverts to the defaults as set by the jupyter 
                configuration file.
                
        colors: str (optional, default is None) console color set. 
            There are, by defult, three color sets:
            'light' or 'lightbg', 
            'dark' or 'linux',
            'nocolor'
            
        """
        
        # print(f"{self.__class__.__name__}.set_pygment(scheme: {scheme}, colors: {colors})")
        
        import pkg_resources
        #print("console.set_pygment scheme:", scheme, "colors:", colors)
        # if scheme is None or (isinstance(scheme, str) and len(scheme.strip()) == 0) \
        #     or scheme not in PYGMENT_STYLES:
        #     self.set_default_style()
        #     #self._control.style = self._initial_style
        #     #self.style_sheet = self._initial_style_sheet
        #     return
        
#         if scheme in StyleNames: # custom styles from scipyen_console_styles
#             # NOTE: 82024-09-20 10:20:21
#             # this bypasses the traitlet oberver mechanism in JupyterWidget
#             # because the Scipyen's custom styles are not registered with
#             # pygments (TODO)
#             mystyle = getattr(scipyen_console_styles, scheme)
#             
#             isDark = styles.dark_color(mystyle.background_color)
#             
#             style_sheet_template = styles.default_dark_style_template if isDark else styles.default_light_style_template
#             style_sheet = style_sheet_template%scipyen_console_styles.get_style_colors(mystyle.name)
# 
#             syntax_style = style_sheet if isDark else styles.default_light_syntax_style
#             
#             # self.style_sheet = style_sheet # observed traitlet in JupyterWidget
#             # calls next lines automatically, but we bypass that directly because
#             # our style is NOT registered with the pygments
#             self.setStyleSheet(style_sheet)
#             if self._control is not None:
#                 self._control.document().setDefaultStyleSheet(style_sheet)
#                 
#             if self._page_control is not None:
#                 self._page_control.document().setDefaultStyleSheet(style_sheet)
#                 
#             if self._highlighter is not None:
#                 self._highlighter.set_style(mystyle)
#                 # BUG: 2024-09-20 10:26:28 FIXME
#                 # this one also relies on style being registered with pygments
#                 # self._ansi_processor.set_background_color(syntax_style)
#                 
#                 self._ansi_processor.default_color_map = self._ansi_processor.darkbg_color_map.copy()
#                 if not isDark:
#                     for i in range(8):
#                         self._ansi_processor.default_color_map[i + 8] = self._ansi_processor.default_color_map[i]
# 
#                     # ...and replace white with black.
#                     self._ansi_processor.default_color_map[7] = self._ansi_processor.default_color_map[15] = 'black'
# 
#                 # Update the current color map with the new defaults.
#                 self._ansi_processor.color_map.update(self._ansi_processor.default_color_map)
#                     
#                 
# 
#             self._console_pygment = mystyle.name
#             self._console_colors = mystyle.name if isDark else styles.default_light_syntax_style # which is 'default'
#             return
        
        # NOTE: 2020-12-23 11:15:50
        # code below is modified from qtconsoleapp module, plus my comments;
        # find the value for colors: there are three color sets for prompts:
        # 1. light or lightbg (i.e. colors suitable for schemes with light background)
        # 2. dark or linux (i.e colors suitable for schemes with dark background)
        # 3. nocolor - for black and white scheme
        if isinstance(colors, str) and len(colors.strip()): # force colors irrespective of scheme
            colors=colors.lower()
            if colors in ('lightbg', 'light'):
                colors='lightbg'
            elif colors in ('dark', 'linux'):
                colors='linux'
            else:
                colors='nocolor'
        
        else: # (colors is "" or anything else)
            # make an informed choice of colors, according to whether the scheme
            # is bright (light) or dark
            if scheme=='bw':
                colors='nocolor'
            elif styles.dark_style(scheme):
                colors='linux'
            else:
                colors='lightbg'
        #else:
            #colors=None
            
        # if scheme in scipyen_console_styles.available_pygments():
        if scheme in PYGMENT_STYLES:
            #print("found %s scheme" % scheme)
            # rules of thumb:
            #
            # 1. the syntax highlighting scheme is set by setting the console 
            # (RichJupyterWidget) 'syntax_style' attribute to scheme. 
            #
            # 2. the style sheet gives the widget colors ("style") - so we always 
            #   need a style sheet, and we "pygment" the console by setting its
            #   'style_sheet' attribute. NOTE that schemes do not always provide
            #   prompt styling colors, therefore we need to set up a style sheet 
            #   dynamically based on the colors guessed according to whether the
            #   scheme is a "dark" one or not.
            #
            try:
                sheetfile = pkg_resources.resource_filename("jupyter_qtconsole_colorschemes", "%s.css" % scheme)
                
                if os.path.isfile(sheetfile):
                    with open(sheetfile) as f:
                        sheet = f.read()
                        
                else:
                    #print("no style sheet found for %s" % scheme)
                    sheet = styles.sheet_from_template(scheme, colors)
                    
                change_error_display_for_style(scheme)
                    
                self.style_sheet = sheet
                self.syntax_style = scheme
                # also need to call notifiers - this is the order in which they
                # are called in qtconsoleapp module ('JupyterConsoleApp.init_colors')
                # not sure whether it makes a difference but stick to it for now
                self._syntax_style_changed()
                self._style_sheet_changed()
                
                # remember these changes - to save them in _save_settings_()
                self._console_pygment = scheme
                self._console_colors = colors
                
                # NOTE: 2021-01-08 14:23:14
                # These two will affect all Jupyter console apps in Scipyen that
                # will be launched AFTER the internal console has been initiated. 
                # These include the ExternalIPython.
                #JupyterWidget.style_sheet = sheet
                #JupyterWidget.syntax_style = scheme
                
            except:
                traceback.print_exc()
                #pass
            
            # not needed (for now)
            #style = pstyles.get_style_by_name(scheme)
            #try:
                ##self.syntax_style=scheme
                #self._control.style = style
                #self._highlighter.set_style (scheme)
                #self._custom_syntax_style = style
                #self._syntax_style_changed()
            #except:
                #traceback.print_exc()
                #pass
 
class ExternalConsoleWindow(MainWindow, WorkspaceGuiMixin):
    """Inherits qtconsole.mainwindow.MainWindow with a few added perks.
    """
    # NOTE 2020-07-08 23:24:47
    # not all of these will be useful in the long term
    # TODO get rid of junk
    sig_shell_msg_received = Signal(object)
    sig_shell_msg_exec_reply_content = Signal(object)
    sig_shell_msg_krnl_info_reply_content = Signal(object)
    sig_kernel_count_changed = Signal(int)
    sig_kernel_started_channels = Signal(dict)
    sig_kernel_stopped_channels = Signal(dict)
    sig_kernel_restart = Signal(dict)
    sig_kernel_disconnect = Signal(dict)
    #sig_will_close = Signal()
    
    # NOTE: 2021-08-29 19:09:24
    # all widget factories currently generate a RichJupyterWidget
    def __init__(self, app, consoleapp, confirm_exit=True, new_frontend_factory=None, slave_frontend_factory=None, connection_frontend_factory=None, new_frontend_orphan_kernel_factory=None):
        """
    """
    # ExternalIPython.new_frontend_master → new_frontend_factory
    # ExternalIPython.new_frontend_slave → slave_frontend_factory
    # ExternalIPython.new_frontend_connection → connection_frontend_factory
    # ExternalIPython.new_frontend_master_with_orphan_kernel → new_frontend_orphan_kernel_factory

        super().__init__(app, confirm_exit = confirm_exit,
                         new_frontend_factory = new_frontend_factory,
                         slave_frontend_factory = slave_frontend_factory,
                         connection_frontend_factory=connection_frontend_factory)
        
        WorkspaceGuiMixin.__init__(self, parent=None)
        self.new_frontend_orphan_kernel_factory = new_frontend_orphan_kernel_factory
        
        # NOTE: 2021-01-23 21:10:03
        # some important widget attributes:
        #
        # kernel_client: a reference to a kernel client (always) which among 
        #   other things holds a reference to the connection file;
        #   This connection file is unique for every running kernel (and kernel manager)
        #
        # kernel_manager: a reference to a kernel manager ONLY for "master" widgets
        #       i.e. which manage the kernels on their own, AND for those "slave"
        #       widgets connected to a kernel started by the console.
        #       ATTENTION: this is None for "slave" widgets connected to external
        #       kernels (i.e. "remote" kernels, e.g. started by jupyter notebook
        #       event if on the same local machine)
        #
        # _may_close: True if this is a "master" frontend; False otherwise
        # _existing: False or empty string if this a "master" frontend; 
        #           otherwise, this is True for a "slave" frontend created from 
        #           the console menu, or a non-empty string if launched with 
        #           "--existing" (in which case _existing is the connection file
        #           name)
        
        # NOTE 2020-07-09 00:41:55
        # no menu bar or tab bar at this time!
        self.defaultFixedFont = defaultFixedFont
        self._layout_direction_ = QtCore.Qt.LeftToRight
        
        #self._initial_style = self.style()
        #self._initial_style_sheet = self.style_sheet
        
        self._console_pygment=""
        self._console_colors=""
        
        self.qsettings = QtCore.QSettings()
        # NOTE: Whis won;t have any effect here because during __init__ there's
        # no widget (RichJupyterWidget) yet
        
        # NOTE: 2021-01-23 21:15:52 
        # this is the parent (running) Scipyen application, not
        # the ExternalIPython! - this is another 
        # difference from the jupyter qtconsole
        self.app = app 
        
        # NOTE: 2021-01-30 14:26:37
        # THIS is the ExternalIPython app
        self.consoleapp = consoleapp 

        icon = QtGui.QIcon.fromTheme("JupyterQtConsole")
        self.setWindowIcon(icon)
        self.setAcceptDrops(True) # TODO 2021-08-30 10:28:19 FIXME
        
        # NOTE: 2021-01-24 14:31:09
        # maps connection file (str) to a dict which in turn maps keys to
        # session dictionaries as follows:
        # "master": a session dictionary:
        #               "client_session_ID": str,
        #               "manager_session_ID": str,
        #               "tab_name": str
        #
        #           or None
        #
        # "slaves": list of session dictionaries as for master, or the empty list
        #
        # "name":   str - the name of the kernel workspace, used in Scipyen's 
        #                   workspace model
        #
        # This mapping should easily lend itself to managing frontends (either
        #   "master", or "slave": "internal slave" or "external slave"):
        #
        #   A locally managed kernel is one started from within ExternalIPython
        # and all its frontends (the master and the slaves if any) will use the 
        # same connection file. In this case, the connection dictionary will
        # contain a master session dictionary and a possibly empty list of slave
        # session dictionaries. The slave frontends are "internal" and their 
        # session dictionaries are collected in the "slaves" list of the 
        # connection dictionary.
        #
        #   Frontends conneted to a kernel started (and managed) by an independent
        # (a.k.a 'remote') process are always slaves; the "master" key in the 
        # connection dctionary maps to None (i.e., there is no master session 
        # dictionary), and there is at least one slave session dictionary in the
        # "slaves" list.
        #
        # See comments in add_tab_with_frontend() for details about these three
        #   types of frontends
        # 
        # NOTE: 2021-01-24 21:59:19 Briefly:
        # * kernels launched from within the ExternalIPython have a master frontend
        # and possibly one or more slave frontends
        # * kernels launched externally have No master frontend (i.e. "master" is None)
        # and at least one slave frontend
        self._connections_ = dict()
        
        self._cached_connections_ = dict()
        
        # NOTE: 2021-08-30 10:42:57
        # Needed for window geometry & position, etc
        self._load_settings_()
        
    def _widget(self):
        """Consistent retrieval of console widget - for look and feel settings
        """
        widget = self.active_frontend
        if widget is None:
            if self.tab_widget.count():
                widget = self.tab_widget.widget(0)
                
            else:
                widget = None
                
        return widget
        
        
    def _supplement_file_menu_(self):
        """To be called separately after calling self.__init__(...).
        This is because _init__() does not initialize the menus: we don't get 
        a menu until after self.init_menu_bar()
        So it is up to the user of the ExternalConsoleWindow instance to take care
        of that - see ExternalIPython.init_qt_elements
        """
        self.new_nrn_kernel_tab_act = QtWidgets.QAction("New Tab with New &Kernel + NEURON",
            self,
            shortcut="Ctrl+K",
            triggered=self.create_neuron_tab
            )
        
        self.insert_menu_action(self.file_menu, self.new_nrn_kernel_tab_act, self.slave_kernel_tab_act)

    def _supplement_kernel_menu_(self):
        """To be called separately after calling self.__init__().
        This is because _init__() does not initialize the menus: we don't get 
        a menu until after self.init_menu_bar()
        So it is up to the user of the ExternalConsoleWindow instance to take care
        of that - see ExternalIPython.init_qt_elements()
        """
        ctrl = "Meta" if sys.platform == 'darwin' else "Ctrl"
        kernel_menu_separators = [a for a in self.kernel_menu.actions() if a.isSeparator()]
        
        self.initialize_neuron_act = QtWidgets.QAction("S&tart NEURON in current Kernel",
                                                       self,
                                                       shortcut=ctrl+"N",
                                                       triggered=self.start_neuron_in_current_tab
                                                       )
        
        if len(kernel_menu_separators):
            self.insert_menu_action(self.kernel_menu,
                                    self.initialize_neuron_act,
                                    kernel_menu_separators[0])

        else:
            self.add_menu_action(self.kernel_menu, self.initialize_neuron_act)
            
    def _supplement_view_menu_(self):
        ctrl = "Meta" if sys.platform == 'darwin' else "Ctrl"
        
        self.syntax_style_menu.clear()
        
        style_group = QtWidgets.QActionGroup(self)
        
        actions = [QtWidgets.QAction("{}".format(s), self, triggered = partial(self._set_syntax_style, s)) for s in PYGMENT_STYLES]
        
        for action in actions:
            action.setCheckable(True)
            style_group.addAction(action)
            self.syntax_style_menu.addAction(action)
            if action.text() == self.active_frontend.syntaxStyle:
                action.setChecked(True)
                self.syntax_style_menu.setDefaultAction(action)
       
        
        self.colors_menu = self.view_menu.addMenu("Console colors")
        colors_group = QtWidgets.QActionGroup(self)
        for c in self.active_frontend.available_colors:
            action = QtWidgets.QAction("{}".format(c), self,
                                       triggered = partial(self._set_syntax_style, c))
            # action = QtWidgets.QAction("{}".format(c), self,
            #                            triggered = lambda v, val=c:
            #                                self._set_syntax_style(colors=val))
            # action = QtWidgets.QAction("{}".format(c), self,
            #                            triggered = lambda v, val=c:
            #                                self.active_frontend._set_syntax_style(colors=val))
            action.setCheckable(True)
            colors_group.addAction(action)
            self.colors_menu.addAction(action)
            if c == self.active_frontend.syntaxStyle:
                action.setChecked(True)
                self.colors_menu.setDefaultAction(action)
                
        scrollbar_pos = ("left", "right")
        self.sb_menu = self.view_menu.addMenu("Scrollbar position")
        sb_group = QtWidgets.QActionGroup(self)
        for s in self.active_frontend.scrollbar_positions.values():
            action = QtWidgets.QAction("{}".format(s), self,
                                       triggered = lambda v, val = s:
                                           self.active_frontend._set_sb_pos(val=val))
            action.setCheckable(True)
            sb_group.addAction(action)
            self.sb_menu.addAction(action)
            
            if s == self.active_frontend.scrollbar_positions[self.active_frontend.scrollBarPosition]:
                action.setChecked(True)
                self.sb_menu.setDefaultAction(action)
            
        self.choose_font_act = QtWidgets.QAction("Font", self, shortcut=ctrl+"F",
                                                 triggered = self.choose_font)
        
        self.add_menu_action(self.view_menu, self.choose_font_act)
        
    def choose_font(self):
        currentFont = self.consoleFont
        selectedFont, ok = QtWidgets.QFontDialog.getFont(currentFont, self)
        if ok:
            self.active_frontend.font = selectedFont
            
        
    def _load_settings_(self):
        #print("ExternalConsoleWindow._load_settings_()")
        # located in $HOME/.config/Scipyen/Scipyen.conf
        loadWindowSettings(self.qsettings, self)#, group_name=self.__class__.__name__)
        
    @property
    def consoleFont(self):
        # so that is doesn't override QMainWindow.font()
        if self.active_frontend:
            return self.active_frontend.font
        else:
            return self.defaultFixedFont
    
    @consoleFont.setter
    def consoleFont(self, val:QtGui.QFont):
        self.active_frontend.font = val
                
    @property
    def isTopLevel(self):
        """Overrides WorkspaceGuiMixin.isToplevel; always True for ScipyenConsole.
        This is because console inherits from RichJupyterWidget where 'parent'
        is a traitlets.Instance property, and for ScipyenConsole is None.
        """
        return True

    @safeWrapper
    def _save_settings_(self):
        #print("ExternalConsoleWindow._save_settings_")
        saveWindowSettings(self.qsettings, self)#, group_name=self.__class__.__name__)
            
    @safeWrapper
    def _save_tab_settings_(self, widget):
        return
        ndx = self.tab_widget.indexOf(widget)
        if ndx < 0:
            return
        
        pfx = self.tab_widget.tabText(ndx).replace(" ", "_")
        
        #font = widget.font
        #self.qsettings.beginGroup(self.__class__.__name__)
        #self.qsettings.setValue("FontFamily", font.family())
        #self.qsettings.setValue("FontPointSize", font.pointSize())
        #self.qsettings.setValue("FontStyle", font.style())
        #self.qsettings.setValue("FontWeight", font.weight())
        #self.qsettings.setValue("ScrollBarPosition", self.getScrollBarPosition(widget))
        #self.qsettings.endGroup()
        
    def create_tab_with_existing_kernel(self, code=None, **kwargs):
        """create a new frontend attached to an external kernel in a new tab"""
        if sys.platform == "win32":
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}
        connection_file, file_type = QtWidgets.QFileDialog.getOpenFileName(self,
                                                     "Connect to Existing Kernel",
                                                     jupyter_runtime_dir(),
                                                     "Connection file (*.json)",
                                                     **kw)
        if not connection_file:
            return False
        
        #print("ExternalConsoleWindow.create_tab_with_existing_kernel connection_file", connection_file)
        
        widget = self.connection_frontend_factory(connection_file)
        # NOTE 2021-01-23 17:32:50
        # the risk here is that one can have several (slaves) console tabs 
        # connected to the same remote kernel; but they will be named differently
        #name = "external {}".format(self.next_external_kernel_id)
        if widget:
            self.add_tab_with_frontend(widget)#, name=name)
            self.sig_kernel_count_changed.emit(self._kernel_counter + self._external_kernel_counter)
            if widget.kernel_client and isinstance(code, str) and len(code.strip()):
                widget.kernel_client.execute(code=code, **kwargs)
                
            return True
        
        return False
        #return widget.kernel_client
        
    def create_new_tab_with_orphan_kernel(self, km, kc):
        widget=self.new_frontend_orphan_kernel_factory(km, kc)
        if widget:
            self.add_tab_with_frontend(widget)
            if hasattr(widget, "_set_console_colors"):
                widget._set_syntax_style(self._console_colors)
            if hasattr(widget, "_set_syntax_style"):
                widget._set_syntax_style(self._console_pygment)
            return True
        return False
        
    def create_tab_with_current_kernel(self):
        """create a new frontend attached to the same kernel as the current tab"""
        current_widget = self.tab_widget.currentWidget()
        current_widget_index = self.tab_widget.indexOf(current_widget)
        current_widget_name = self.tab_widget.tabText(current_widget_index)
        widget = self.slave_frontend_factory(current_widget)
        if hasattr(widget, "_set_console_colors"):
            widget._set_syntax_style(self._console_colors)
        if hasattr(widget, "_set_syntax_style"):
            widget._set_syntax_style(self._console_pygment)
        self.add_tab_with_frontend(widget)

    def create_tab_with_new_frontend(self, code=None, **kwargs):
        """create a new frontend and attach it to a new tab
        calls ExternalIPython.new_frontend_master, with its own, newly-created
        kernel manager, kernel client and connection file
        """
        widget = self.new_frontend_factory() # this is ExternalIPython.new_frontend_master()
        if widget:
            self.add_tab_with_frontend(widget)
            if widget.kernel_client and isinstance(code, str) and len(code.strip()):
                widget.kernel_client.execute(code=code, **kwargs)
            
            if hasattr(widget, "_set_console_colors"):
                widget._set_syntax_style(self._console_colors)
            if hasattr(widget, "_set_syntax_style"):
                widget._set_syntax_style(self._console_pygment)
                
            return True
        return False
            

    def create_neuron_tab(self):
        return self.create_tab_with_new_frontend(code=nrn_ipython_initialization_cmd,
                                          silent=True,
                                          store_history=False)
        
    def start_neuron_in_current_tab(self):
        #print("ExternalConsoleWindow.start_neuron_in_current_tab")
        self.active_frontend.kernel_client.execute(code=nrn_ipython_initialization_cmd,
                                                   silent=True,
                                                   store_history=False)
        
    def insert_menu_action(self, menu, action, before, defer_shortcut=False):
        """Inserts action to menu before "before", as well adds it to self

        So that when the menu bar is invisible, its actions are still available.

        If defer_shortcut is True, set the shortcut context to widget-only,
        where it will avoid conflict with shortcuts already bound to the
        widgets themselves.
        """
        menu.insertAction(before, action)
        self.addAction(action)

        if defer_shortcut:
            action.setShortcutContext(QtCore.Qt.WidgetShortcut)
            
    def find_widget_with_kernel_manager(self, km, as_widget_list:bool=True, 
                                        alive_only:bool=False, master_only:bool = False):
        """Find the frontends with the specified kernel manager.
        
        For a given kernel manager there is onyl one "master" frontend (the 
        frontends that launched the kernel) and zero or more "slaves"
        (frontends that connect to the kernel launched by the "master")
        
        Parameters:
        -----------
        km = kernel manager 
        
        as_widget_list: bool (optional default is True)
            When true, returns a list of frontends (only one is master, if found;
            the others, if they exist, are slaves)
            
            When False, returns a list of indices of the frontend found, in the
            console window's tab bar.
            
            
        alive_only: bool (optional, default is False) ; looks up the widget for
            alive kernel mangers only
            
        Returns:
        -------
        
        A list of frontend widgets (RichJupyterWidget) that work with the specified
        (live) kernel manager , or a list in ondices of the frontend widgets in
        the console window's tab bar.
        
        
        """
        
        if alive_only and not km.is_alive():
            return []
        #if not km.is_alive():
            #return
        
        
        widget_list = [self.tab_widget.widget(i) for i in range(self.tab_widget.count())]
        
        filtered_widget_list = [widget for widget in widget_list if
                                widget.kernel_manager.connection_file == km.connection_file]
        
        if as_widget_list:
            return filtered_widget_list
        
        else:
            return [self.tab_widget.indexOf(w) for w in filtered_widget_list]
        
    def find_widget_with_kernel_client(self, kc, as_widget_list:bool=True, alive_only=False):
        """Find the frontends with the specified kernel client.
        
        For a given kernel manager there is only one "master" frontend (the 
        frontends that launched the kernel) and zero or more "slaves"
        (frontends that connect to the kernel launched by the "master")
        
        Parameters:
        -----------
        km = kernel client for which is_alive() returns True
        
        as_widget_list: bool (optional default is True)
            When true, returns a list of frontends (only one is master, if found;
            the others, if they exist, are slaves)
            
            When False, returns a list of indices of the frontend found, in the
            console window's tab bar.
            
            
        Returns:
        -------
        
        A list of frontend widgets (RichJupyterWidget) that work with the specified
        (live) kernel manager , or a list in ondices of the frontend widgets in
        the console window's tab bar.
        
        
        """
        
        if alive_only and not kc.is_alive():
            return []
        
        widget_list = [self.tab_widget.widget(i) for i in range(self.tab_widget.count())]
        
        filtered_widget_list = [widget for widget in widget_list if
                                widget.kernel_client.connection_file == kc.connection_file]
        
        if as_widget_list:
            return filtered_widget_list
        else:
            return [self.tab_widget.indexOf(w) for w in filtered_widget_list]
        
    def find_widget_for_client_sessionID(self, sessionID:str, as_widget_list:bool=True, alive_only:bool=True):
        widget_list = [self.tab_widget.widget(i) for i in range(self.tab_widget.count())]
        
        if alive_only:
            filtered_widget_list = [widget for widget in widget_list if
                                    widget.kernel_client.is_alive() and \
                                    widget.kernel_client.session.session == sessionID]
            
        else:
            filtered_widget_list = [widget for widget in widget_list if \
                                    widget.kernel_client.session.session == sessionID]
        
        if as_widget_list:
            return filtered_widget_list
        
        else:
            return [self.tab_widget.indexOf(w) for w in filtered_widget_list]
        
    def find_widgets_for_manager_sessionID(self, sessionID:str, as_widget_list:bool=True, alive_only:bool=True):
        widget_list = [self.tab_widget.widget(i) for i in range(self.tab_widget.count())]
        
        if alive_only:
            filtered_widget_list = [widget for widget in widget_list if
                                    widget.kernel_manager.is_alive() and \
                                    widget.kernel_manager.session.session == sessionID]
            
        else:
            filtered_widget_list = [widget for widget in widget_list if \
                                    widget.kernel_manager.session.session == sessionID]
        
        if as_widget_list:
            return filtered_widget_list
        
        else:
            return [self.tab_widget.indexOf(w) for w in filtered_widget_list]
        
    def find_widgets_for_connection_file(self, connection_file:str, as_widget_list:bool=True, alive_only=True):
        widget_list = [self.tab_widget.widget(i) for i in range(self.tab_widget.count())]
        
        if alive_only:
            filtered_widget_list = [widget for widget in widget_list if
                                    widget.kernel_client.is_alive() and \
                                    widget.kernel_client.connection_file == connection_file]
            
        else:
            filtered_widget_list = [widget for widget in widget_list if \
                                    widget.kernel_client.connection_file == connection_file]
            
        if as_widget_list:
            return filtered_widget_list
        
        else:
            return [self.tab_widget.indexOf(w) for w in filtered_widget_list]
        
    def find_tab_title(self, widget:RichJupyterWidget):
        ndx = self.tab_widget.indexOf(widget)
        
        if ndx >=0 :
            return self.tab_widget.tabText(ndx)
        
    def is_master_frontend(self, widget):
        return hasattr(widget, "_may_close") and widget._may_close and (not widget._existing)
        
    def get_workspace_name_for_client_session_ID(self, sessionID:str):
        def __get_wname__(cdict, sid):
            return cdict["name"] if ((cdict["master"] and cdict["master"]["client_session_ID"] == sid) or (sid in [sd["client_session_ID"] for sd in cdict["slaves"]])) else None
        
        ret = [n for n in [__get_wname__(d, sessionID) for d in self._connections_.values()] if n]
        
        if len(ret):
            return ret[0]
        
    def check_workspace(self, ns_name:str):
        """Checks if the workspace name ns_name is registered
        
        Parameters:
        ns_name: str; 
            OBSOLETE (CAUTION): All underscores ('_') will be replaced with spaces (' ')
            
            This is to reverse the convention of replacing spaces (' ') with
            underscores ('_') in string variables. In turn, this convention is 
            necessary in order to properly interpret the shell channel messages 
            received from the kernel.
            
            See also:
            
            ScipyenWindow._slot_ext_krn_shell_chnl_msg_recvd
            extipyutils_client.cmds_get_foreign_data_props
            extipyutils_client.cmds_get_foreign_data_props2
            extipyutils_client.cmd_foreign_namespace_listing
            extipyutils_client.cmd_foreign_shell_ns_listing
            
        """
        return ns_name in (d["name"] for d in self._connections_.values())
    
    def get_connection_filename_for_workspace(self, ns_name):
        cfiles = [cfile for cfile, d in self._connections_.items() if d["name"] == ns_name]
        
        if len(cfiles):
            return cfiles[0]
        
    def get_connection_dict_for_workspace(self, ns_name):
        cdicts = [d for d in self._connections_.values() if d["name"] == ns_name]

        if len(cdicts):
            return cdicts[0]
    
    def is_local_workspace(self, ns_name):
        cdict = self.get_connection_dict_for_workspace(ns_name)
        return cdict and isinstance(cdict["master"], dict) # definitely a locally managed kernel
        
    @safeWrapper
    def get_frontend(self, ndx):
        #print("ExternalConsoleWindow.get_frontend ndx =", ndx)
        if isinstance(ndx, int): # index of tab
            tab_titles = [self.tab_widget.tabText(k) for k in range(self.tab_widget.count())]
            #print("ExternalConsoleWindow: tab title",tab_titles[ndx])
            return self.tab_widget.widget(ndx)
        
        elif isinstance(ndx, str): # title of tab, name of connection file, or client session ID
            tab_titles = [self.tab_widget.tabText(k) for k in range(self.tab_widget.count())]
            
            if ndx in tab_titles:
                return self.tab_widget.widget(tab_titles.index(ndx))
            
            else:
                if len(self._connections_) == 0:
                    return
                
                tab_name = None
                
                if ndx in self._connections_.keys(): # ndx is a connection file name
                    # return tab name of the master frontend if exists, or the first
                    # available slave frontend
                    cinfo = self._connections_[ndx]
                    if isinstance(cinfo["master"], dict):
                        tab_name = cinfo["master"]["tab_name"]
                        
                    elif len(cinfo["slaves"]):
                        tab_name = cinfo["slaves"][0]["tab_name"]
                        
                else: 
                    # ndx might be a workspce name or a client session ID 
                    # (the latter option is specific to the frontend)
                    cinfo = [d for d in self._connections_.values() if d["name"] == ndx]
                    if len(cinfo): # ndx IS a workspace name
                        # ndx is a workspace name => again, return the master 
                        # frontend if available else the first available slave
                        # frontend, else None
                        cinfo = cinfo[0]
                        if isinstance(cinfo["master"], dict):
                            tab_name = cinfo["master"]["tab_name"]
                        elif len(cinfo["slaves"]):
                            tab_name = cinfo["slaves"][0]["tab_name"]
                            
                    else: # check if ndx is a client session ID
                        master_cinfos = [d for d in self._connections_.values() 
                                         if isinstance(d["master"], dict) and d["master"]["client_session_ID"] == ndx]
                        if len(master_cinfos):
                            # ndx is a master client session ID
                            tab_name = master_cinfos[0]["master"]["tab_name"]
                            
                        else:
                            slave_cinfos = [s for s in itertools.chain.from_iterable([d["slaves"] for d in self._connections_.values() 
                                                                                      if len(d["slaves"])])
                                            if s["client_session_ID"] == ndx]
                        
                            if len(slave_cinfos):
                                # ndx ios a slave client session ID
                                tab_name = slave_cinfos[0]["tab_name"]

                if tab_name:
                    #print("ExternalConsoleWindow: tab_name", tab_name)
                    return self.tab_widget.widget(tab_titles.index(tab_name))
        else:
            raise TypeError("Expecting an int or a str; got %s instead" % type(ndx.__name__))
        
    @safeWrapper
    def prefix_tab_title(self, prefix, ndx):
        """Prepends prefix to the tab title for tabs with indices in ndx.
        Parameters:
        ----------
        prefix: str - the prefix
        ndx: int -  the index of the tab in the tab widget.
        
        The function does nothing if prefix is empty or is not in the tab's title.
        A prefix string containing only spaces or tab characters is considered
        empty in this context.
        """
        if len(prefix.strip()) == 0:
            return
        
        old_title = self.tab_widget.tabText(ndx)
        
        if prefix not in old_title:
            new_title= "%s%s" % (prefix, old_title)
            self.tab_widget.setTabText(ndx, new_title)
            
    @safeWrapper
    def unprefix_tab_title(self, prefix, ndx):
        """Removes prefix from the tab title for tabs with indices in ndx.
        Parameters:
        ----------
        prefix: str - the prefix
        ndx: int - the index of the tab in the tab widget.
        
        The function does nothing if prefix is empty or is not in the tab's title
        A prefix string containing only spaces or tab characters is considered
        empty in this context.
        """
        if len(prefix.strip()) == 0:
            return
        
        #print(prefix)

        old_title = self.tab_widget.tabText(ndx)
        if prefix in old_title:
            new_title = old_title.replace(prefix, "")
            self.tab_widget.setTabText(ndx, new_title)
            return new_title
        
        return old_title
    
    @property
    def syntaxStyle(self):
        return self._console_pygment
    
    @markConfigurable("SyntaxStyle", "qt")
    @syntaxStyle.setter
    def syntaxStyle(self, style:str):
        self._console_pygment = style
        if hasattr(self, "active_frontend") and isinstance(self.active_frontend, ConsoleWidget):
            self.active_frontend._set_syntax_style(style)
        # colors = self._console_colors
        
    def _set_syntax_style(self, style):
        self.syntaxStyle = style

    @property
    def consoleColors(self):
        return self._console_colors
    
    @markConfigurable("ConsoleColors", "qt")
    @consoleColors.setter
    def consoleColors(self, val:str):
        self._console_colors = val
        if hasattr(self, "active_frontend") and isinstance(self.active_frontend, ConsoleWidget):
            self.active_frontend._set_console_colors(val)
        
    def _set_console_colors(self, val:str):
        self.consoleColors = val
        
    def add_tab_with_frontend(self, frontend, name=None):
        """ Insert a tab with a given frontend in the tab bar, and give it a name

        """
        # NOTE: frontend is the "widget" 
        
        # NOTE: 2021-01-24 22:13:46 "master" frontend
        # A "master" frontend has kernel manager and kernel client; both
        # operate via the same connection file, with the same sessionID:
        #   manager.session.session == client.session.session -> True
        # 
        #   in addition, a "master" frontend has:
        #   _may_close = True
        #   _existing = False (or "")
        #
        # "Master" frontends are created when either:
        #   * the console has been launched without passing "existing" parameter
        #   * a new tab with new kernel has been created <- this is linked from
        #       Scipyen
        
        # NOTE: 2021-01-24 22:14:21 "slave" frontend
        # A "slave" frontend can communicate with either:
        #   1) an "internal" kernel started from with the console (e.g. when 
        #       console was launched without "existing" parameter) - this "internal
        #       slave" frontend is created by activating the File menu item 
        #       "New Tab With Same Kernel"
        #
        #   2) an "external" kernel started in a separate process (e.g. by a 
        #       jupyter notebook) - an "external" slave frontend is created in
        #       two cases:
        #   
        #   2.1) an "existing" parameter was passed on console launch => the only
        #       frontend is a slave to the "external" kernel ("external slave")
        #
        #   2.2) the File menu item "New Tab with Exising Kernel" was activated
        #
        #   An "internal" slave has both a kernel manager and a kernel client:
        #   
        #   * The kernel manager of an "interval" slave is the same as the kernel
        #   manager of the frontend that launched the kernel in question
        #   (therefore, both the internal slave and the master have the same 
        #   manager session ID)
        #
        #   * The kernel client is specific to each frontend (therefore both the 
        #   slave's kernel client and the cliet's session ID are different from
        #   those of the master frontend that started the kernel in question).
        #
        #   The "external" slave frontends DO NOT HAVE KERNEL MANAGER! This means
        #   that a "slave" frontend's kernel manager is None. They only have a
        #   kernel client (and obviously, manager_session_ID is None)
        #   
        #   In addition, a "slave" frontend has:
        #   _may_close = False
        #   _existing = True
        #
        # has a kernel client and a kernel manager ONLY IF 
        
        external_slave = False
        
        # NOTE: 2021-01-24 21:43:28
        # the connection file is UNIQUE to the kernel client/manager
        cfile = frontend.kernel_client.connection_file 
        
        # NOTE: 2021-01-24 21:43:47
        # but the client sesion ID is unique to the kernel_client
        # all frontends have a kernel client
        client_session_ID = frontend.kernel_client.session.session
        
        # NOTE: 2021-01-24 22:33:09
        # on the other hand, manager session ID is the same for master and their
        # "internal" slave frontends, but is None for "external" slave frontends
        # (see  NOTE: 2021-01-24 22:13:46 "master" frontend
        #  and  NOTE: 2021-01-24 22:14:21 "slave" frontend)
        manager_session_ID = None
        
        if frontend.kernel_manager is not None:
            # only master and internal slave frontends have a kernel manager
            # (slaves have a reference to the master's kernel manager)
            manager_session_ID = frontend.kernel_manager.session.session
            
        session_dict = {"client_session_ID": client_session_ID,
                        "manager_session_ID": manager_session_ID,
                        "tab_name": ""}
        
        n_internal_kernels = len([d["master"] for d in self._connections_.values() if d["master"] is not None])
        n_external_kernels = len([d["master"] for d in self._connections_.values() if d["master"] is None])
        
        if self.is_master_frontend(frontend):
            # NOTE: 2021-01-24 14:36:38
            # by definition a master frontend ALWAYS starts its own kernel with
            # a new connection file; therefore this implicitly guarantees that
            # the new connection file name is NOT registered with the self._connections_
            # dictionary
            if cfile not in self._connections_.keys():
                # a "master" frontend is by defition connected to an internal
                # kernel
                kname = "kernel %d" % n_internal_kernels
                
                # NOTE: 2021-01-24 21:47:15
                # distinguish between kernel name (but not the one in the connection file,
                # which may be empty) and the tab's name
                
                # in this case, name is both the name of the frontend tab and
                # the name under which we register this connection
                if not isinstance(name, str) or len(name.strip()) == 0:
                    session_dict["tab_name"] = kname # name of the tab
                    
                    name = kname
                    
                else:
                    session_dict["tab_name"] = name
                    
                self._connections_[cfile] = {"master": session_dict,
                                             "slaves": list(),
                                             "name": kname}
                
            else:
                # technically this shouldn't happen
                raise RuntimeError("A connection file %s has already been registered" % cfile)
                        
        else: # slave frontend
            # NOTE: 2021-01-24 21:25:12
            # check if connection file is already registered here
            if cfile in self._connections_:
                # connection file already registered => this may be an "internal"
                # slave or an "external" one
                ndx_slave = len(self._connections_[cfile]["slaves"])
                
                if isinstance(self._connections_[cfile]["master"], dict):
                    # this is an "internal" slave frontend so it should have
                    # the same manager session ID as its master - just make
                    # sure of this, here
                    
                    # NOTE: 2021-01-25 19:35:51 this checks that the slave is
                    # indeed a slave to its master
                    assert(session_dict["manager_session_ID"] == self._connections_[cfile]["master"]["manager_session_ID"])
                    
                else:
                    external_slave = True

                
                if not isinstance(name, str) or len(name.strip()) == 0:
                    name = "%s (slave %d)" % (self._connections_[cfile]["name"], ndx_slave)
                    
                else:
                    name = "%s (%s)" % (self._connections_[cfile]["name"], name)
                    
                session_dict["tab_name"] = name
                        
                self._connections_[cfile]["slaves"].append(session_dict)
                
            else:
                # in this case the kernel has been launched by an external 
                # process (e.g. jupyter notebook); therefore we set up its 
                # dictionary, but there will be no master
                external_slave = True
                kname = "external %d" % n_external_kernels
                
                if not isinstance(name, str) or len(name.strip()) == 0:
                    name = "%s (slave 0)" % kname
                    
                else:
                    name = "%s (%s)" % (kname, name)
                    
                session_dict["tab_name"] = name
                
                self._connections_[cfile] = {"master":None, 
                                             "slaves":[session_dict],
                                             "name": kname}
                
        # NOTE 2020-07-08 21:24:28
        # set our own font
        #frontend.font = self._console_font_
        
        #print("adding tab for widget", name)
        self.tab_widget.addTab(frontend, name)
        self.update_tab_bar_visibility()
        self.make_frontend_visible(frontend)
        
        # NOTE 2020-07-08 21:24:45
        # Mechanism for capturing kernel messages via the shell channel.
        # In the Qt console framework these communication channels with the (remote)
        # kernel are Qt objects (QtZMQSocketChannel). In particular, the channels
        # emit Qt signals that contain the actual kernel message
        # 
        # The kernel client here is a QtKernelClient inherits from 
        #   jupyter_client.threaded.ThreadedKernelClient
        # and emits:
        #   started_channels and stopped_channels Qt signals
        #
        # In addition, it (re)defines:
        #    iopub_channel_class = Type(QtZMQSocketChannel) # iopub channel
        #    shell_channel_class = Type(QtZMQSocketChannel) # shell channel
        #    stdin_channel_class = Type(QtZMQSocketChannel) # stdin channel
        #    hb_channel_class = Type(QtHBChannel)           # heartbeat channel
        #
        # where QtZMQSocketChannel is a jupyter_client.threaded.ThreadedZMQSocketChannel
        #   that is capable of emitting message_received Qt signal
        #
        # The channels used by the client for commnication with the kernel are:
        # 
        # client.shell_channel -- connected via the client.shell_port
        # client.stdin_channel -- connected via the client.stdin_port
        # client.iopub_channel -- connected via the client.iopub_port
        # client.hb_channel    -- connected via the client.hb_port
        #
        # 
        frontend.kernel_client.started_channels.connect(self.slot_kernel_client_started_channels)
        frontend.kernel_client.stopped_channels.connect(self.slot_kernel_client_stopped_channels)
        ########frontend.kernel_client.iopub_channel.
        
        frontend.kernel_client.shell_channel.message_received.connect(self.slot_kernel_shell_chnl_msg_recvd)
        
        if frontend.kernel_manager:
            frontend.kernel_manager.kernel_restarted.connect(self.slot_kernel_restarted)
        
        frontend.exit_requested.connect(self.close_tab)
        
        if external_slave:
            # force listing of user_ns in remote kernel for our display purposes
            frontend.kernel_client.shell_channel.send(frontend.kernel_client.session.msg("kernel_info_request"))
            
        #self._load_settings_()

    def closeEvent(self, event):
        """ Forward the close event to every tabs contained by the windows
        """
        self._save_settings_()
        if self.tab_widget.count() == 0:
            #print("no tabs")
            # no tabs, just close
            #self.sig_will_close.emit()
            self._kernel_counter = 0
            self._external_kernel_counter = 0
            if self.consoleapp.kernel_manager is not None:
                try:
                    if hasattr(self.consoleapp.kernel_manager, "is_alive") and self.consoleapp.kernel_manager.is_alive():
                        self.consoleapp.kernel_manager.shutdown_kernel(now=True, restart=False)
                except Exception as e:
                    traceback.print_exc()
            event.accept()
            return
        
        # Do Not loop on the widget count as it will change while closing
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
            pixmap = QtGui.QPixmap(self.windowIcon().pixmap(QtCore.QSize(64,64)))
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
                self.close_tab(widget)
            event.accept()
            
    def close_tab(self, current_tab):
        """ Called when you need to try to close a tab.

        It takes the number of the tab to be closed as argument, or a reference
        to the widget inside this tab
        """

        # let's be sure "tab" and "closing widget" are respectively the index
        # of the tab to close and a reference to the frontend to close
        
        if type(current_tab) is not int :
            current_tab = self.tab_widget.indexOf(current_tab)
        closing_widget=self.tab_widget.widget(current_tab)
        tab_name = self.tab_widget.tabText(current_tab)
        #print("ExternalConsole.close_tab %s" % tab_name)


        # when trying to be closed, widget might re-send a request to be
        # closed again, but will be deleted when event will be processed. So
        # need to check that widget still exists and skip if not. One example
        # of this is when 'exit' is sent in a slave tab. 'exit' will be
        # re-sent by this function on the master widget, which ask all slave
        # widgets to exit
        if closing_widget is None:
            return
        
        #closing_widget._save_settings_()
        closing_widget.saveSettings() # inherited from ScipyenConfigurable

        #print("closing widget _keep_kernel_on_exit =", None if not hasattr(closing_widget,"_keep_kernel_on_exit") else closing_widget._keep_kernel_on_exit)
        #print("closing widget _hidden =", None if not hasattr(closing_widget,"_hidden") else closing_widget._hidden)
        #print("closing widget _existing =", None if not hasattr(closing_widget,"_existing") else closing_widget._existing)
        #print("closing widget _may_close =", None if not hasattr(closing_widget,"_may_close") else closing_widget._may_close)
        #print("closing widget _confirm_exit =", None if not hasattr(closing_widget,"_confirm_exit") else closing_widget._confirm_exit)
        
        #get a list of all slave widgets on the same kernel.
        slave_tabs = self.find_slave_widgets(closing_widget)
        
        cfile = closing_widget.kernel_client.connection_file
        
        client_session_ID = closing_widget.kernel_client.session.session

        keepkernel = None #Use the prompt by default
        
        # "_keep_kernel_on_exit" is set by exit magic, see qtconsole.frontend_widget._process_execute_error()
        # 
        if hasattr(closing_widget,'_keep_kernel_on_exit'):
            # NOTE: 2021-01-26 23:00:34
            # This branch is executed ONLY IF _keep_kernel_on_exit is set AND IF
            # closing_widget is a slave frontend.
            #
            # I.e., The clause below is executed when "exit" is typed in the 
            # frontend cli, but NOT when the frontend is closed from the GUI 
            # (e.g. by clicking the close button)
            
            # It basically checks if this is an internal slave frontend
            #
            # When closing_widget is a slave frontend, this will ALSO SHUTDOWN 
            # the kernel ONLY IF there is a master frontend here (i.e. when the
            # kernel has been started from this console app)
            keepkernel = closing_widget._keep_kernel_on_exit
            # If signal sent by exit magic (_keep_kernel_on_exit, exist and not None)
            # we set local slave tabs._hidden to True to avoid prompting for kernel
            # restart when they get the signal. and then "forward" the 'exit'
            # to the main window
            if keepkernel is not None:
                for tab in slave_tabs:
                    tab._hidden = True
                    
                if closing_widget in slave_tabs:
                    #print("closing widget is a slave frontend where 'exit' was typed ")
                    try :
                        # NOTE: 2021-01-26 17:22:32
                        # this also closes the master tab and the kernel
                        # TODO 2021-01-26 17:21:47
                        # is there a workaround to just close the slave tab
                        # and not shutdown the kernel, when typing "exit" in a
                        # slave tab?
                        # The "exit" command is packed in a message sent by the
                        # client to the kernel which will the exit; we would have
                        # to ALTER the behaviour of the frontend and/or the client
                        # to determine if the "exit" command has been issues in
                        # a slave frontend,.
                        # Then, if the "exit" command came from a slave frontend
                        # it should be intercepted and diverted to closing only
                        # the frontend while leaving the kernel alive.
                        #
                        # something like "exit -k"?
                        #
                        # The way I see it right now, current code offer this
                        # behaviour only when the slave frontend is closed from
                        # the GUI and not by typing exit in the slave frontend 
                        # cli
                        
                        
                        # NOTE: 2021-01-26 23:23:27 original code
                        # this will call close_tab on master frontend
                        # but will raise AttributeError when a master frontend
                        # was not found (e.g. in the case of external kernels)
                        
                        master = self.find_master_tab(closing_widget)
                        print("master", master)
                        
                        self.find_master_tab(closing_widget).execute('exit') 
                        
                    except AttributeError:
                        self.log.info("Master already closed or not local, closing only current tab")
                        # NOTE: 2021-01-26 17:24:14
                        # this just removes the current widget (i.e. the widget at
                        # index 'current_tab' in tab_widget), given that the 
                        # current widget is a "slave"
                        if closing_widget.kernel_client.is_alive():
                            background(closing_widget.kernel_client.stop_channels)
                            
                        self.tab_widget.removeTab(current_tab) # this is still a slave
                        
                    self.update_tab_bar_visibility()
                    
                    self.remove_connection(cfile, client_session_ID)
                    return
                    
        # NOTE: 2021-01-26 23:00:00
        # if keepkernel is None here, the code follows through !!!
        
        #print("keepkernel", keepkernel)
        
        # NOTE: 2021-01-26 23:42:04
        # at this point, the frontend can still be either a master, or a slave

        kernel_client = closing_widget.kernel_client
        kernel_manager = closing_widget.kernel_manager

        # NOTE: 2021-01-27 19:40:15
        # however, a slave frontend started on an exisintg (remote) kernel
        # has _confirm_exit True!
        if keepkernel is None and not closing_widget._confirm_exit:
            # NOTE: a slave frontend has _confirm_exit False
            # don't prompt, just terminate the kernel if we own it
            # or leave it alone if we don't
            # NOTE: 2021-01-27 19:58:28
            # the clause is satisfied for "external" slave frontends created in 
            # an already running external console app, and the remote kernel has
            # been remotely closed shut
            keepkernel = closing_widget._existing   # if True or a string then 
                                                    # this is a slave frontend
            
        #print("keepkernel", keepkernel)
        
        # NOTE: 2021-01-27 20:01:47
        # below, call stop_channels as early as possible to avoid kernel client
        # warning that kernel has died
        if keepkernel is None: #show prompt this can still be a master frontend
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
                    pixmap = QtGui.QPixmap(self.windowIcon().pixmap(QtCore.QSize(64,64)))
                    box.setIconPixmap(pixmap)
                    reply = box.exec_()
                    if reply == 1: # close All
                        
                        self.remove_connection(cfile, client_session_ID)
                        
                        for slave in slave_tabs:
                            background(slave.kernel_client.stop_channels)
                            self.tab_widget.removeTab(self.tab_widget.indexOf(slave))
                            
                        kernel_manager.shutdown_kernel()
                        
                        self.tab_widget.removeTab(current_tab)
                        background(kernel_client.stop_channels)
                        
                    elif reply == 0: # close Console
                        if not closing_widget._existing:
                            # Have kernel: don't quit, just close the tab
                            self.remove_connection(cfile, client_session_ID)
                                        
                            closing_widget.execute("exit True")
                            
                        self.tab_widget.removeTab(current_tab)
                        background(kernel_client.stop_channels)
                else:
                    # NOTE: 2021-01-27 19:48:09
                    # _may_close is False in a slave frontend launched with an 
                    # external (remote) kernel e.g. one started by jupyter notebook
                    # 
                    reply = QtWidgets.QMessageBox.question(self, title,
                        "Are you sure you want to close this Console?"+
                        "\nThe Kernel and other Consoles will remain active.",
                        okay|cancel,
                        defaultButton=okay
                        )
                    if reply == okay:
                        self.remove_connection(cfile, client_session_ID)
                        self.tab_widget.removeTab(current_tab)
                        background(kernel_client.stop_channels)

        elif keepkernel: #close console but leave kernel running (no prompt)
            background(kernel_client.stop_channels)
            self.remove_connection(cfile, client_session_ID)
            self.tab_widget.removeTab(current_tab)
            
        else: # close console and kernel (no prompt)
            # NOTE: 2021-01-27 19:43:08
            # here, keepkernel resolves to False, yet it is NOT NONE
            if kernel_client and kernel_client.channels_running:
                for slave in slave_tabs:
                    background(slave.kernel_client.stop_channels)
                    self.tab_widget.removeTab(self.tab_widget.indexOf(slave))
                    
                if kernel_manager:
                    kernel_manager.shutdown_kernel()
                    
                background(kernel_client.stop_channels)

            self.remove_connection(cfile, client_session_ID)
                        
            self.tab_widget.removeTab(current_tab)
            
        self.update_tab_bar_visibility()
        
    def remove_connection(self, cfile, sessionID, slaves_only=False):
        if cfile in self._connections_:
            workspace_name = self._connections_[cfile]["name"]
            
            slave_fe_dicts = [d for d in self._connections_[cfile]["slaves"] if d["client_session_ID"]==sessionID]
            for slave_fe_dict in slave_fe_dicts:
                self._connections_[cfile]["slaves"].remove(slave_fe_dict)
                
            if not slaves_only:
                session_dict = {"connection_file": cfile,
                                "master": self._connections_[cfile]["master"],
                                "name": self._connections_[cfile]["name"]}
                
                # print(f"{self.__class__.__name__}.remove_connection: session_dict =", session_dict)
                
                if isinstance(self._connections_[cfile]["master"], dict) and self._connections_[cfile]["master"]["client_session_ID"] == sessionID:
                    # locally managed kernel
                    self._connections_[cfile]["master"] = None

                if len(self._connections_[cfile]["slaves"]) == 0 and self._connections_[cfile]["master"] is None:
                    self._connections_.pop(cfile)
                    self.sig_kernel_disconnect.emit(session_dict)
                    
    def close_tab_original(self, current_tab):
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
            # see qtconsole.frontend_widget where the magic is interpreted
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
                        # NOTE: 2021-01-26 17:22:32
                        # this also closes the master tab and the kernel
                        # TODO 2021-01-26 17:21:47
                        # is there a workaround to just close the slave tab
                        # and not shutdown the kernel, when typing "exit" in a
                        # slave tab?
                        self.find_master_tab(closing_widget).execute('exit')
                    except AttributeError:
                        self.log.info("Master already closed or not local, closing only current tab")
                        # NOTE: 2021-01-26 17:24:14
                        # this just removes the current widget (i.e. the widget at
                        # index 'current_tab' in tab_widget), given that the 
                        # current widget is a "slave"
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
                    pixmap = QtGui.QPixmap(self.windowIcon().pixmap(QtCore.QSize(64,64)))
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

    @Slot()
    @safeWrapper
    def slot_kernel_client_started_channels(self):
        """Not in use
        """
        kc = self.sender()
        if kc.connection_file in self._connections_:
            self.sig_kernel_started_channels.emit(self._connections_[kc.connection_file])
        
    @Slot()
    @safeWrapper
    def slot_kernel_client_stopped_channels(self):
        """Not in use
        """
        kc = self.sender()
        if kc.connection_file in self._connections_:
            self.sig_kernel_stopped_channels.emit(self._connections_[kc.connection_file])
        
    @Slot()
    @safeWrapper
    def slot_kernel_restarted(self):
        """Re-sets the tag title after a kernel restart.
        
        """
        # used specifically for NEURON tabs, where quitting NEURON GUI crashes the
        # kernel (and the manager restarts it)
        km = self.sender() # this is a kernel manager
        
        if km.connection_file in self._connections_:
            km_widgets = self.find_widget_with_kernel_manager(km, as_widget_list=True)
            
            if len(km_widgets):
                for widget in km_widgets:
                    if self.is_master_frontend(widget):
                        self.consoleapp._scipyen_init_exec_(widget.kernel_client)
                    
                self.sig_kernel_restart.emit(self._connections_[km.connection_file])
        
    @safeWrapper
    @Slot(object)
    def slot_kernel_shell_chnl_msg_recvd(self, msg):
        #print(msg)
        #message = Message(msg)
        header = msg["header"]
        msg_type = header["msg_type"]
        #print("msg_id:", header["msg_id"], "session: ", header["session"])
        # ATTENTION
        # msg["header"]["session"] is the session ID of the remote kernel!
        # the session of the client is in msg["parent_header"]["session"]
        
        sessionID = msg["parent_header"]["session"]
        
        #print("slot_kernel_shell_chnl_msg_recvd \nsender =", self.sender())
        
        #print("ExternalConsoleWindow.\n\tsessionID =", sessionID)
        
        # sessionID is stored in frontend.kernel_client.session.session
        # the client session ID is unique for every client (and thus, frontend)
        frontends = self.find_widget_for_client_sessionID(sessionID)
        
        if len(frontends) == 0:
            return
        
        elif len(frontends) > 1:
            raise RuntimeError("Too many frontends with the same session ID")
        
        cfile = frontends[0].kernel_client.connection_file
        
        if cfile not in self._connections_:
            return
        
        connection_info = self._connections_[cfile]
        
        msg["workspace_name"] = connection_info["name"]
        msg["connection_file"] = cfile
        #msg["client_session_ID"] = frontends[0].kernel_client.session.session
        
        #print("ExternalConsoleWindow.slot_kernel_shell_chnl_msg_recvd\n\tsession ID =", sessionID,
              #"\n\tfrontend client session is session ID", frontends[0].kernel_client.session.session == sessionID,
              #"\n\ttab =", self.tab_widget.tabText(self.tab_widget.indexOf(frontends[0])),
              #"\n\tworkspace =", msg["workspace_name"],
              #"\n")
        
        self.sig_shell_msg_received.emit(msg)
        
    @property
    def connections(self):
        return self._connections_
        
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
    name = 'Scypien Console for External IPython'
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
        # NOTE: 2021-01-23 22:33:57 force ConsoleWidget
        #self.widget_factory = ConsoleWidget
        if new:
            self.widget_factory = JupyterWidget
        else:
            self.widget_factory = RichJupyterWidget

    # the factory for creating a widget
    #widget_factory = Any(RichJupyterWidget)
    widget_factory = Any(ConsoleWidget)

    def parse_command_line(self, argv=None):
        super().parse_command_line(argv)
        self.build_kernel_argv(self.extra_args)

    def new_frontend_master_with_orphan_kernel(self, km, kc):
        """When user closed a tab but chose to leave the kernel alone.
        
        The orphan kernel is still running and its client stil has got a
        reference somewhere - why not re-use them !?
        
        NOTE: to be used when the console hasn't got any more tabs; the kernel
        will be considered as a "master" and the new frontend, a "master" 
        frontend
        
        """
        if km.connection_file != kc.connection_file:
            raise ValueError("Both the kernel manager and client shoud have the same connection file; cinstead, I've got for manager: %s ; for client: %s" % (km.connection_file, kc.connection_file))
        
        if km.ip != kc.ip:
            raise ValueError("Both the kernel manager and client must have same ip address; instead the manager has %s and the client has %s" % (km.ip, kc.ip))

        is_local = km.ip == "127.0.0.1"
        
        widget = self.widget_factory(config=self.config,
                                     local_kernel=is_local)
        
        # NOTE: 2021-08-30 10:33:06
        # ### BEGIN
        # Load defaults from $HOME/.jupyter/jupyter_qtconsole_config.py
        # then override with settings in $HOME/.config/Scipyen/Scipyen.conf
        self.init_colors(widget)
        #self.init_layout(widget)
        widget._load_settings_()
        # ### END

        widget.kernel_manager = km
        widget.kernel_client = kc
        widget._existing = False # consider this as a "master" case
        widget._may_close = True
        widget._confirm_exit = self.confirm_exit
        widget._display_banner = self.display_banner
        return widget
        

    def new_frontend_master(self):
        """ Create and return new frontend attached to new kernel, launched on localhost.
        This is NOT called upon ExternalIPython.launch(). 
        
        Instead, ExternalIPython.launch() executes the following:
        * create an instance of a jupyter app (in this case, ExternalIPython)
        * initializes the app
            - initialize the ancestors
            - initialize Qt elements --> this does the same as new_frontend_master
                the lands on add_tab_with_frontend()
            - initialize signal for clean shutdown on SIGINT and starts a QTimer
        * starts the app
        """
        kernel_manager = self.kernel_manager_class(
                                connection_file=self._new_connection_file(),
                                parent=self,
                                autorestart=True,
        )
        # start the kernel
        kwargs = {}
        # FIXME: remove special treatment of IPython kernels
        #if self.kernel_manager.ipykernel:
        if kernel_manager.ipykernel:
            kwargs['extra_arguments'] = self.kernel_argv
        kernel_manager.start_kernel(**kwargs)
        # NOTE: 2021-09-21 14:22:58
        # This is NOT an inprocess kernel!
        # see https://github.com/ipython/ipykernel/issues/319
        # comment by sdh4
        # https://github.com/ipython/ipykernel/issues/319#issuecomment-661951992
        #if not hasattr(kernel_manager.kernel, "io_loop"):
            #print("try and fix io_loop")
            #import ipykernel.kernelbase
            #ipykernel.kernelbase.Kernel.start(kernel_manager.kernel)
        kernel_manager.client_factory = self.kernel_client_class
        kernel_client = kernel_manager.client()
        kernel_client.start_channels(shell=True, iopub=True)
        widget = self.widget_factory(config=self.config,
                                     local_kernel=True) # a RichJupyterWidget
        # NOTE: 2021-08-30 10:33:06
        # ### BEGIN
        # Load defaults from $HOME/.jupyter/jupyter_qtconsole_config.py
        # then override with settings in $HOME/.config/Scipyen/Scipyen.conf
        self.init_colors(widget)
        #self.init_layout(widget)
        #widget._load_settings_()
        widget.loadSettings() # inherited from ScipyenConfigurable
        # ### END
        
        widget.kernel_manager = kernel_manager
        widget.kernel_client = kernel_client
        widget._existing = False
        widget._may_close = True
        widget._confirm_exit = self.confirm_exit
        widget._display_banner = self.display_banner
        self._scipyen_init_exec_(widget.kernel_client)
        #print("ExternalIPython.new_frontend_master: connection_file =", kernel_client.connection_file)
        return widget

    def new_frontend_connection(self, connection_file):
        """Create and return a new frontend attached to an existing remote kernel.
        A remote kernel is one created by a jupyter app in a separate process.
        
        'Remote' here means that the kernel was started by another jupyter app
        (e.g. notebook) and the frontend will connect via a connection file 
        set up by the app that launched the kernel, even if all takes place on
        the same local machine.
        
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
        # NOTE: 2021-08-30 10:33:06
        # ### BEGIN
        # Load defaults from $HOME/.jupyter/jupyter_qtconsole_config.py
        # then override with settings in $HOME/.config/Scipyen/Scipyen.conf
        self.init_colors(widget)
        #self.init_layout(widget)
        #widget._load_settings_()
        # ### END
        
        widget._existing = True
        widget._may_close = False
        widget._confirm_exit = False
        widget._display_banner = self.display_banner
        widget.kernel_client = kernel_client
        widget.kernel_manager = None
        self._scipyen_init_exec_(widget.kernel_client)
        #print("ExternalIPython.new_frontend_connection: connection_file =", connection_file)
        return widget

    def new_frontend_slave(self, current_widget):
        """Create and return a new frontend attached to an existing local kernel.

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
        # NOTE: 2021-08-30 10:33:06
        # ### BEGIN
        # Load defaults from $HOME/.jupyter/jupyter_qtconsole_config.py
        # then override with settings in $HOME/.config/Scipyen/Scipyen.conf
        self.init_colors(widget)
        #self.init_layout(widget)
        widget._load_settings_()
        # ### END

        widget._existing = True
        widget._may_close = False
        widget._confirm_exit = False
        widget._display_banner = self.display_banner
        widget.kernel_client = kernel_client
        widget.kernel_manager = current_widget.kernel_manager
        #print("ExternalIPython.new_frontend_slave: connection_file =", kernel_client.connection_file)
        return widget
    
    #def init_layout(self, widget=None): # don't remove yet
        #"""Apply scrollbar position saved in settings ('ExternalConsole/ScrollBarPosition')
        #"""
        #if widget and getattr(widget, "_control", None):
            #widget._control.setLayoutDirection(self.window.scrollBarPosition)
            ##widget._control.setLayoutDirection(self.window.getScrollBarPosition())
    
    def init_qt_elements(self):
        # Create the widget.
        base_path = os.path.abspath(os.path.dirname(__file__))
        
        ip = self.ip
        local_kernel = (not self.existing) or is_local_ip(ip)

        self.window = ExternalConsoleWindow(self.app, self, 
                                confirm_exit=self.confirm_exit,
                                new_frontend_factory=self.new_frontend_master,
                                slave_frontend_factory=self.new_frontend_slave,
                                connection_frontend_factory=self.new_frontend_connection,
                                new_frontend_orphan_kernel_factory=self.new_frontend_master_with_orphan_kernel,
                                )
        self.widget = self.widget_factory(config=self.config,
                                        local_kernel=local_kernel)
        
        # NOTE: 2021-08-30 10:33:06
        # ### BEGIN
        # Load defaults from $HOME/.jupyter/jupyter_qtconsole_config.py
        # then override with settings in $HOME/.config/Scipyen/Scipyen.conf
        self.init_colors(self.widget)
        #self.init_layout(self.widget)
        # ### END
        
        self.widget._existing = self.existing
        self.widget._may_close = not self.existing
        self.widget._confirm_exit = self.confirm_exit
        self.widget._display_banner = self.display_banner

        self.widget.kernel_manager = self.kernel_manager
        self.widget.kernel_client = self.kernel_client
        
        
        self.window.log = self.log
        self.window.add_tab_with_frontend(self.widget)
        
        self.window._load_settings_()
        # NOTE: 2021-08-31 17:59:24
        # MUST be called here when both kernel client & manager are running
        # in the widget!
        try:
            #self.widget._load_settings_()
            self.widget.loadSettings() # inherited from ScipyenConfigurable
        except:
            traceback.print_exc()
        
        self.window.init_menu_bar()
        self.window._supplement_file_menu_()
        self.window._supplement_kernel_menu_()
        self.window._supplement_view_menu_()
        
        
        # NOTE 2020-07-09 01:05:35
        # run general kernel intialization python commands here, as this function
        # does not call new_frontend_master(...)
        
        # NOTE 2020-07-11 11:51:36
        # these two are equivalent; use the first one as more direct, whereas the
        # second one is more generic, allowing the use of any valid kernel client
        self._scipyen_init_exec_(self.widget.kernel_client)
        
        #print("ExternalIPython.init_qt_elements connection_file =", self.widget.kernel_client.connection_file)

        # Ignore on OSX, where there is always a menu bar
        if sys.platform != 'darwin' and self.hide_menubar:
            self.window.menuBar().setVisible(False)

        self.window.setWindowTitle('External Scipyen Console')
        
        
    def _scipyen_init_exec_(self, client):
        client.execute(code="\n".join(init_commands), silent=True, store_history=False)

    def init_colors(self, widget):
        """Configure the coloring of the widget"""
        #Note: This will be dramatically simplified when colors
        # are removed from the backend.

        #print("ExternalIPython.init_colors(%s)" % widget)
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
            
        #widget._load_settings_()
        widget.loadSettings() # inherited from ScipyenConfigurable


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
        # ORIGINAL: self.init_qt_app()
        # We use the currently running QApplication (which is Scipyen started by
        # scipyen.main())
        self.app = QtWidgets.QApplication.instance() # this is the Scipyen app!
        
        # NOTE: 2021-01-15 14:51:38
        # this one (JupyterApp.initialize) parses argv and sets up the 
        # configuration framework including parsing sys.argv
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
                
        # NOTE: 2021-01-15 14:50:05
        # this will automatically start a new IPython kernel:
        # initializes:
        #   connection file
        #   ssh channel
        #   kernel manager
        #   kernel client
        JupyterConsoleApp.initialize(self, argv)
        
        self.init_qt_elements()
        
        self.init_signal()

    def start(self):
        super().start()

        # draw the window
        if self.maximize:
            self.window.showMaximized()
        else:
            self.window.show()
            
        self.window._load_settings_()
        self.window.raise_()

        # Start the application main loop.
        #self.app.exec_() # Don't use here! we already have a GUI (Qt) event loop

    @classmethod
    def launch(cls, argv=None, existing:typing.Optional[str]=None, **kwargs):
        
        # NOTE: 2023-07-15 21:33:52
        # the launch_instance mechanism in jupyter and qtconsole does not return
        # an instance of this python "app"
        #scipyenvdir = os.getenv("CONDA_PREFIX")
        #if scipyenvdir is not None:
            #if argv is None:
                #argv=["-Xfrozen_modules=off"]
            #elif isinstance(argv, tuple):
                #if len(argv) == 0:
                    #argv=("-Xfrozen_modules=off", )
                #else:
                    #aa = list(argv)
                    #aa.append(" -Xfrozen_modules=off")
                    #argv = tuple(aa)

            #elif isinstance(argv, list):
                #if len(argv) == 0:
                    #argv=["-Xfrozen_modules=off"]
                #else:
                    #argv.append(" -Xfrozen_modules=off")




        # NOTE: 2021-08-29 21:49:44
        # Do NOT confuse this with Scipyen app (self.app)
        # In fact it is a reference to ExternalIPython, which is returned below
        app = cls.instance(**kwargs) # 
        # TODO 2021-01-15 15:39:44
        # allow launching with an external kernel
        if isinstance(existing, str) and len(existing.strip()):
            app.existing = existing
            
        app.initialize(argv)
        app.start()

        return app
    
    #### BEGIN some useful properties
    
    @property
    def active_kernel_manager(self):
        """The kernel manager of the active frontend.
        This may be different from self.kernel_manager which is only set once
        (and hence is the kernel manager of the first frontend of the console)
        """
        return self.window.active_frontend.kernel_manager if self.window.active_frontend else None
    
    @property
    def active_kernel_client(self):
        """The kernel client of the active frontend.
        This may be different from self.kernel_client which is only set once
        (and hence is the kernel client of the first frontend of the console)
        """
        return self.window.active_frontend.kernel_client if self.window.active_frontend else None
    
    @property
    def active_manager_session(self):
        """The kernel manager session of the active frontend.
        This may be different from self.session which is only set once
        (and hence is the session of the first frontend of the console)
        """
        return self.window.active_frontend.kernel_manager.session if self.window.active_frontend else None
    
    @property
    def active_client_session(self):
        """Kernel client session of the active frontend.
        The manager and client session are different objects.
        """
        return self.window.active_frontend.kernel_client.session if self.window.active_frontend else None
    
    @property
    def scrollBarPosition(self):
        """Exposes the console window's scrollBarPosition for convenience
        """
        return self.window.scrollBarPosition
        #return self.window.getScrollBarPosition()
    
    @scrollBarPosition.setter
    def scrollBarPosition(self, value):
        self.window.scrollBarPosition = value
        #self.window.setScrollBarPosition(value)
    
    #### END some useful properties
    
    @safeWrapper
    def execute(self, *code:typing.Union[str, dict, tuple, list, ForeignCall], 
                where : typing.Optional[typing.Union[int, str, RichJupyterWidget, QtKernelClient]]=None, 
                redirect:typing.Optional[dict]=None, **kwargs):
        """Execute code asynchronously, in a kernel.
        By default, code is executed in the kernel behind the active frontend.
        
        Revamped version of the kernel client execute() where "code" can be 
        a dict carrying all the parameters expected by the "legacy" execute()
        method of the kernel client.
        
        Parameters:
        -----------
        code: str, dict, ForeignCall, or sequence of these (mixing allowed)
            When a str, it contains the executed code, possibly empty.
            
            When a dict, it must contain the following keys:
                "code" : str (default "")
                "silent": bool (default True)
                "store_history": bool (default False)
                "user_expressions" : dict (default {})
                
                These are 'unfolded' to parameters expected by the "legacy" 
                execute() method of the lerel client
                
        where: QtKernelClient, RichJupyterWidget, int, str (optional, default 
            is None) = Where to execute the code.
            
            When None (default), the code is executed by the active frontend's 
            kernel  client.
            
            Otherwise, it allows to specifiy a kernel client to execute the code,
            either directly (i.e passing the kernel client here), indirectly
            by passing its frontend (RichJupyterWidget) or by looking it up 
            using the tab's index (int) or name (str).
            
            If where is the special string "all" (lowercase) then the command
            will be executed in all running kernels.
            
        redirect: dict (optional, default is None)
            TODO not used
            
        **kwargs: additional keyword arguments to kernel_client.execute() as 
                detailed below.
                
                ATTENTION These may override contents of the code, if code is
                a ForeignCall object
                
                
        Documentation of method 'execute' in module jupyter_client.client:

        execute(code, silent=False, store_history=True, user_expressions=None,
                allow_stdin=None, stop_on_error=True) 
                
            method of qtconsole.client.QtKernelClient instance
            
            Execute code in the kernel.
            
            Parameters
            ----------
            code : str
                A string of code in the kernel's language.
            
            silent : bool, optional (default False)
                If set, the kernel will execute the code as quietly possible, and
                will force store_history to be False.
            
            store_history : bool, optional (default True)
                If set, the kernel will store command history.  This is forced
                to be False if silent is True.
            
            user_expressions : dict, optional
                A dict mapping names to expressions to be evaluated in the user's
                dict. The expression values are returned as strings formatted using
                :func:`repr`.
                
                This is needed to get return values into Scipyen's workspace
            
            allow_stdin : bool, optional (default self.allow_stdin)
                Flag for whether the kernel can send stdin requests to frontends.
            
                Some frontends (e.g. the Notebook) do not support stdin requests.
                If raw_input is called from code executed from such a frontend, a
                StdinNotImplementedError will be raised.
            
            stop_on_error: bool, optional (default True)
                Flag whether to abort the execution queue, if an exception is encountered.
            
            Returns
            -------
            The msg_id of the message sent.

        
        Raises:
        -------
        
        TypeError
            If the where parameter is not an int, str, RichJupyterWidget or 
                QtKernelClient
                
            If the code does not resolve to a str or a dict, or a tuple of these
                (mixing is allowed)
                
        ValueError
            If the where parameter (int or str) does not resolve to an existing
            frontend in this console.
        
        Returns:
        -------
        a str or list of str with the msg_id for the message(s) sent
        
        
            
        """
        # see NOTE 2020-07-11 11:51:36
        #execute(self.window.active_frontend.kernel_client, code=code, **kwargs)
        
        # ATTENTION 
        # DO NOT confuse frontend.execute() with frontend.kernel_client.execute()
        #
        # Here we need the latter: frontend.kernel_client.execute()!
        #
        # For the former, see RichJupyterWidget.execute()
        
        
        def _exec_call_(call, kc, **kwargs):
            # kc is the kernel client
            # allow kwargs to override named parameters but protect against 
            # overriding the execution code; 
            # NOTE user_expressions are still vulnerable to this
            kwargs.pop("code", None) # make sure code is not overwritten by kwargs
            if isinstance(call, ForeignCall):
                if len(kwargs):
                    call2 = call.copy()
                    call2.update(kwargs)
                    return kc.execute(*call2()) # -> str
                
                return kc.execute(*call()) # -> str
            
            elif isinstance(call, dict):
                # one call expression as a dict
                call.update(kwargs)
                return kc.execute(**call) # -> return a str
                
            elif isinstance(call, (tuple, list)):
                # a sequence of call expressions - all must be dict or str (mixing allowed) 
                # -> return a list of str (msg_id of the messages sent)
                
                ret = []
                
                for expr in call:
                    if isinstance(expr, ForeignCall):
                        if len(kwargs):
                            expr2 = expr.copy()
                            expr2.update(kwargs)
                            ret.append(kc.execute(*expr2())) 
                        else:
                            ret.append(kc.execute(*expr())) 

                    elif isinstance(expr, dict):
                        # allows overriding by named parameters in kwargs
                        # "code" is protected against this
                        expr.update(kwargs)
                        ret.append(kc.execute(**expr)) 
                        
                    elif isinstance(expr, str):
                        # just the code was given - we need the kwargs here unless
                        # we're relying on the default
                        ret.append(kc.execute(expr, **kwargs))
                    else:
                        raise TypeError("call must be a str or a dict")
                    
                return ret # list of str
        
            elif isinstance(call, str):
                # a command string -> fall-through to the end "return fe.execute(...)"
                return kc.execute(call, **kwargs)
                
                # NOTE: fall-through to the end "return fe.execute(...)" -> return a str

            else:
                raise TypeError("code expected to be a str, dict, or a sequence of dict; got %s instead" % type(code).__name__)
                
        client = None
        
        if where is None:
            frontend = self.window.active_frontend
            if frontend is None:
                return
            
            client = self.window.active_frontend.kernel_client
            
        # identify and check the "where" parameter
        elif isinstance(where, RichJupyterWidget):
            client = where.kernel_client
            
        elif isinstance(where, int):
            frontend = self.window.get_frontend(where)
            if frontend is None:
                return
            
            client = frontend.kernel_client
            
        elif isinstance(where, str):
            if where == "all":
                frontends = [self.window.get_frontend(k) for k in self.window.tab_widget.count()]
                clients = [f.kernel_client for f in frontends]
                
                if len(clients):
                    if len(code) == 1:
                        return [_exec_call_(code[0], c_, **kwargs) for c_ in clients]
                    
                    else:
                        ret = []
                        for client in clients:
                            c_ret = []
                            for call in code:
                                res = _exec_call_(call, client, **kwargs)
                                if isinstance(res, str):
                                    c_ret.append(res)
                                elif isinstance(res, list):
                                    c_ret += res
                            if len(c_ret):
                                ret += c_ret
                        return ret
                    
            else:
                frontend = self.window.get_frontend(where)
                
                if frontend:
                    client = frontend.kernel_client
                
        elif isinstance(where, QtKernelClient):
            client = where
            
        else:
            raise TypeError("'where' parameter expected to be a QtKernelClient, RichJupyterWidget, int, str or None; got %s instead" % type(where).__name__)
        
        if client is None:
            return
        
        # check workspace name
        wname = self.window.get_workspace_name_for_client_session_ID(client.session.session)
        #print("workspace name", wname)
            
        if len(code) == 1:
            # one element in *code sequence - this may be a str, dict, or a sequence of dicts
            # accordingly returns an int or a list of ints
            return _exec_call_(code[0], client, **kwargs)# -> return str or list of str

        else:
            ret = []
            for call in code:
                res = _exec_call_(call, client, **kwargs)
                
                if isinstance(res, str):
                    ret.append(res)
                    
                elif isinstance(res, list):
                    ret += res
                    
            return ret
                    
    def get_connection_file(self):
        fcall = ForeignCall(user_expressions={"connection_file":"get_connection_file()"})
        self.execute(fcall)
        
    def get_connection_info(self):
        fcall = ForeignCall(user_expressions={"connection_info":"get_connection_info()"})
        self.execute(fcall)
        
    #def frontend_execute(self, frontend, **kwargs) -> bool:
        #"""Delegates to frontend.execute() method.
        
        #ATTENTION 
        #DO NOT confuse frontend.execute() with frontend.kernel_client.execute().
        #fronted.execute() is actually qtconsole.ConsoleWidget.execute()
        #although they both end up doing the same thing?
        
        #Here we use the former, see RichJupyterWidget.execute(); to execute code
        #by calling kernel_client.execute() and allow
        
        
        #Parameters:
        
        #-----------
        #frontend: RichJupyterWidget, int or str, or None.
            #int = the index of the frontend's tab in the tab bar of the console
                    #window
                    
            #str = the title of the frontend's tab, in the console window
            
            #RichJupyterWidget: the frontend itself (it may belong to another
            #console)
            
            
            #When None, this is set to the active frontend. Otherwise, code is 
            #executed in the specified frontend, or in the frontend at the 
            #specified index in the console's tab bar, or at the tab with the 
            #specified title
            
        #**kwargs: additional keyword arguments passed directly to 
            #frontend.execute, as follows:
            
            #source : str, optional

                #The source to execute. If not specified, the input buffer will be
                #used. If specified and 'hidden' is False, the input buffer will be
                #replaced with the source before execution.

            #hidden : bool, optional (default False)

                #If set, no output will be shown and the prompt will not be modified.
                #In other words, it will be completely invisible to the user that
                #an execution has occurred.

            #interactive : bool, optional (default False)

                #Whether the console is to treat the source as having been manually
                #entered by the user. The effect of this parameter depends on the
                #subclass implementation.

        #Raises
        #------
        #RuntimeError
            #If incomplete input is given and 'hidden' is True. In this case,
            #it is not possible to prompt for more input.
            
        #ValueError
            #If the specified frontend index or name was not found
            
        #TypeError
            #If the specified frontend is neither an int, str or RichJupyterWidget

        #Returns
        #-------
        #A boolean indicating whether the source was executed.        
        #"""
        ## TODO factorize this with self.execute()
        #if frontend is None:
            #frontend = self.window.active_frontend
            
        #elif isinstance(frontend, (int, str)):
            #frontend = self.window.get_frontend(frontend)
            
        #elif not isinstance(frontend, RichJupyterWidget):
            #raise TypeError("frontend expected to be a RichJupyterWidget, int or str; got %s instead" % type(frontend).__name__)
        
        #if frontend is None:
            #raise ValueError("Frontend %s not found" % frontend)
        
        #return frontend.execute(**kwargs)

# NOTE: use Jupyter (IPython >= 4.x and qtconsole / qt5 by default)
class ScipyenConsoleWidget(ConsoleWidget):
    """Console widget with an in-process kernel manager.
    Uses an in-process kernel generated and managed by QtInProcessKernelManager.
    """
    historyItemsDropped = Signal()
    workspaceItemsDropped = Signal()
    fileSystemItemsDropped = Signal()
    #workspaceItemsDropped = Signal(bool)
    loadUrls = Signal(object, bool, QtCore.QPoint)
    pythonFileReceived = Signal(str, QtCore.QPoint)
    
    def __init__(self, *args, **kwargs):
        ''' ScipyenConsole constructor
        
        Using Qt5 gui by default
        NOTE:
        Since August 2016 -- using Jupyter/IPython 4.x and qtconsole
        
        Changelog (most recent first):
        -------------------------------
        NOTE 2020-07-07 12:32:40
        ALWAYS uses the in-proces Qt kernel manager
        
        NOTE 2021-10-06 13:52:58
        Use a customized InProcessKernel, see
        ScipyenInProcessKernelManager and ScipyenInProcessKernel
        for details
        
        '''
        self.mainWindow = kwargs.pop("mainWindow", None)
        super().__init__(*args, **kwargs)

        self.kernel_manager = ScipyenInProcessKernelManager() # what if gui is NOT Qt?
        self.kernel_manager.start_kernel()
        self.kernel_manager.kernel.eventloop = None
        self.ipkernel = self.kernel_manager.kernel
        self.ipkernel.gui = "qt"
        
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
        
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        
        # NOTE: 2019-08-07 16:34:58
        # enforce qt5 backend for matplotlib
        # see NOTE: 2019-08-07 16:34:23 
        self.ipkernel.shell.run_line_magic("matplotlib", "qt5")
        
        self.drop_cache=None
        
        self.defaultFixedFont = defaultFixedFont
        
        # NOTE: 2021-07-18 10:17:26 - FIXME bug or feature?
        # the line below won't have effect unless the RichJupyterWidget is visible
        # e.g. after calling show()
        #self.set_pygment(self._console_pygment) 
        
    def _is_complete(self, source, interactive=True):
        # NOTE: 2021-09-21 16:41:04
        # from qtconsole.inprocess.QtInProcessRichJupyterWidget
        shell = self.kernel_manager.kernel.shell
        status, indent_spaces = \
            shell.input_transformer_manager.check_complete(source)
        if indent_spaces is None:
            indent = ''
        else:
            indent = ' ' * indent_spaces
            
        return status != 'incomplete', indent
    
    def closeEvent(self, evt):
        self.saveSettings() # inherited from ScipyenConfigurable via WorkspaceGuiMixin
        evt.accept()
        
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
        src = evt.source()
        
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
        if type(self.mainWindow).__name__ == "ScipyenWindow" and src is self.mainWindow.workspaceView:
            self.workspaceItemsDropped.emit()
            
        elif type(self.mainWindow).__name__ == "ScipyenWindow" and src is self.mainWindow.historyTreeWidget:
            self.historyItemsDropped.emit()
            
        elif type(self.mainWindow).__name__ == "ScipyenWindow" and src is self.mainWindow.fileSystemTreeView:
            # NOTE: 2019-08-10 00:54:40
            # TODO: load data from disk
            self.fileSystemItemsDropped.emit()
                
        else:
            #NOTE: 2019-08-02 13:35:52
            # allow dropping text in the console 
            # useful for drag&drop python code directly from a python source file
            # opened in a text editor (that also supports drag&drop)
            # event source is from outside the Pict application (i.e. it is None)
            
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
                    echoing = not bool(evt.keyboardModifiers() & QtCore.Qt.ShiftModifier)
                    store = bool(evt.keyboardModifiers() & QtCore.Qt.ControlModifier)
                    
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
                        self.ipkernel.shell.run_cell(text, store_history = store, silent=True, shell_futures=True)
                        self.setWindowTitle(wintitle)
                        
            else:
                # mime data formats contains text/plain but data is QByteArray
                # (which wraps a Python bytes object)
                if "text/plain" in evt.mimeData().formats():
                    text = evt.mimeData().text()
                    if len(text) == 0:
                        text = evt.mimeData().data("text/plain").data().decode()
                        
                    if len(text):
                        self.writeText(text)

            self.drop_cache=None
                
        evt.accept()
        
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
    def writeText(self, text:typing.Union[str, typing.List[str], typing.Tuple[tuple]]):
        """Writes a text in console buffer
        """
        if isinstance(text, str):
            self.__write_text_in_console_buffer__(text)
            
        elif isinstance(text, (tuple, list) and all([isinstance(s, str) for s in text])):
            self.__write_text_in_console_buffer__("\n".join(text))
            
    def _format_text_selection(self, text):
        # code below from qtconsole.frontend_widget.FrontendWidget
        if len(text.strip()):
            first_line_selection, *remaining_lines = text.splitlines()

            # Get preceding text
            cursor = self._control.textCursor()
            cursor.setPosition(cursor.selectionStart())
            cursor.setPosition(cursor.block().position(),
                                QtGui.QTextCursor.KeepAnchor)
            preceding_text = cursor.selection().toPlainText()

            def remove_prompts(line):
                """Remove all prompts from line."""
                line = self._highlighter.transform_classic_prompt(line)
                return self._highlighter.transform_ipy_prompt(line)

            # Get first line promp len
            first_line = preceding_text + first_line_selection
            len_with_prompt = len(first_line)
            first_line = remove_prompts(first_line)
            prompt_len = len_with_prompt - len(first_line)

            # Remove not selected part
            if prompt_len < len(preceding_text):
                first_line = first_line[len(preceding_text) - prompt_len:]

            # Remove partial prompt last line
            if len(remaining_lines) > 0 and remaining_lines[-1]:
                cursor = self._control.textCursor()
                cursor.setPosition(cursor.selectionEnd())
                block = cursor.block()
                start_pos = block.position()
                length = block.length()
                cursor.setPosition(start_pos)
                cursor.setPosition(start_pos + length - 1,
                                    QtGui.QTextCursor.KeepAnchor)
                last_line_full = cursor.selection().toPlainText()
                prompt_len = (
                    len(last_line_full)
                    - len(remove_prompts(last_line_full)))
                if len(remaining_lines[-1]) < prompt_len:
                    # This is a partial prompt
                    remaining_lines[-1] = ""

            # Remove prompts for other lines.
            remaining_lines = map(remove_prompts, remaining_lines)
            text = '\n'.join([first_line, *remaining_lines])

            # Needed to prevent errors when copying the prompt.
            # See issue 264
            try:
                was_newline = text[-1] == '\n'
            except IndexError:
                was_newline = False
            if was_newline:  # user doesn't need newline
                text = text[:-1]
                
        return text

#     def set_pygment_new(self, scheme:typing.Optional[str]="", colors:typing.Optional[str]=None):
#         """Sets up style sheet for console colors and syntax highlighting style.
#         
#         The console widget (a RichJupyterWidget) takes:
#         a) a style specified in a style sheet - used for the general appearance of the console 
#         (background and Prmopt colors, etc)
#         b) a color syntax highlight scheme - used for syntax highlighting
#         
#         
#         This allows bypassing any style/colors specified in 
#         $HOME/.jupyter/jupyter_qtconsole_config.py
#         
#         and usually retrieved by the app's method config()
#         
#         Parameter:
#         -------------
#         
#         scheme: str (optional, default is the empty string) - name of available 
#                 syntax style (pygment).
#                 
#                 For a list of available pygment names, see
#                 
#                 available_pygments() in this module
#                 
#                 When empty or None, reverts to the defaults as set by the jupyter 
#                 configuration file.
#                 
#         colors: str (optional, default is None) console color set. 
#             There are, by defult, three color sets:
#             'light' or 'lightbg', 
#             'dark' or 'linux',
#             'nocolor'
#             
#         """
#         # TODO/FIXME: 2023-06-04 10:23:24
#         # figure out how the ?/?? system works, and apply better terminal colors
#         #   for dark backgrounds, to it; in fact, apply the curren terminal colors
#         #   to the displayed help text as well 
#         #   also, figure out how to alter the placement
#         #   of the scrollbar when the console is showing the message from ?/??
#         #   system -> check out _create_page_control in qtconsole/console_widget.py
#         # might have to look at the page and console submodules in IPython/jupyter
#         # but requires deep digging into their code
#         # import pkg_resources
#         #print("ConsoleWidget.set_pygment scheme:", scheme, "colors:", colors)
#         if scheme is None or (isinstance(scheme, str) and len(scheme.strip()) == 0):
#             self.set_default_style()
#             #self._control.style = self._initial_style
#             #self.style_sheet = self._initial_style_sheet
#             return
#         
#         # NOTE: 2020-12-23 11:15:50
#         # code below is modified from qtconsoleapp module, plus my comments;
#         # find the value for colors: there are three color sets for prompts:
#         # 1. light or lightbg (i.e. colors suitable for schemes with light background)
#         # 2. dark or linux (i.e colors suitable for schemes with dark background)
#         # 3. nocolor - for black and white scheme
#         #else:
#             #colors=None
#             
#         sheet = None
#         
#         # NOTE: 2024-09-19 16:21:02 temporary FIX
#         if scheme == "KeplerDark":
#             scheme = "native"
#             
#         # if scheme in available_pygments():
#         if scheme in PYGMENT_STYLES:
#             #print("found %s scheme" % scheme)
#             # rules of thumb:
#             #
#             # 1. the syntax highlighting scheme is set by setting the console 
#             # (RichJupyterWidget) 'syntax_style' attribute to scheme. 
#             #
#             # 2. the style sheet gives the widget colors ("style") - so we always 
#             #   need a style sheet, and we "pygment" the console by setting its
#             #   'style_sheet' attribute. NOTE that schemes do not always provide
#             #   prompt styling colors, therefore we need to set up a style sheet 
#             #   dynamically based on the colors guessed according to whether the
#             #   scheme is a "dark" one or not.
#             #
#             # NOTE: the approach described above is the one used in qtconsole
#             #
#             if scheme == "KeplerDark":
#                 # use my own - TODO: 2024-09-19 15:24:37 give possibility of 
#                 # future additional custom schemes to be packaged with Scipyen
#                 stylecolors = get_style_colors(scheme)
#                 sheet = styles.default_dark_style_template%stylecolors
#                 colors = "linux"
#                 
#             else:
#                 if isinstance(colors, str) and len(colors.strip()): # force colors irrespective of scheme
#                     colors=colors.lower()
#                     if colors in ('lightbg', 'light'):
#                         colors='lightbg'
#                     elif colors in ('dark', 'linux'):
#                         colors='linux'
#                     else:
#                         colors='nocolor'
#                 
#                 else: # (colors is "" or anything else)
#                     # make an informed choice of colors, according to whether the scheme
#                     # is bright (light) or dark
#                     if scheme=='bw':
#                         colors='nocolor'
#                     elif styles.dark_style(scheme):
#                         colors='linux'
#                     else:
#                         colors='lightbg'
#                 try:
#                     sheetfile = pkg_resources.resource_filename("jupyter_qtconsole_colorschemes", "%s.css" % scheme)
#                     if os.path.isfile(sheetfile):
#                         with open(sheetfile) as f:
#                             sheet = f.read()
#                 except:
#                     # revert to built-in schemes
#                     sheet = styles.sheet_from_template(scheme, colors)
#                       
#             if sheet:
#                 # also need to call notifiers - this is the order in which they
#                 # are called in qtconsoleapp module ('JupyterConsoleApp.init_colors')
#                 # not sure whether it makes a difference but stick to it for now
#                 self.syntax_style = scheme
#                 self.style_sheet = sheet
#                 self._syntax_style_changed()
#                 self._style_sheet_changed()
#                 
#                 # remember these changes - to save them in _save_settings_()
#                 self._console_pygment = scheme
#                 self._console_colors = colors
#                 
#                 if self.kernel_client:
#                     self._execute(f"colors {colors}", True)
#                             #self.reset(clear=True)
#                             #self.kernel_client.execute("colors %s"% colors, True)
#                         
#                         # NOTE: 2021-01-08 14:23:14
#                         # These two will affect all Jupyter console apps in Scipyen that
#                         # will be launched AFTER the internal console has been initiated. 
#                         # These include the ExternalIPython.
#                         #JupyterWidget.style_sheet = sheet
#                         #JupyterWidget.syntax_style = scheme
                        
#     def set_pygment(self, scheme:typing.Optional[str]="", colors:typing.Optional[str]=None):
#         """Sets up style sheet for console colors and syntax highlighting style.
#         
#         The console widget (a RichJupyterWidget) takes:
#         a) a style specified in a style sheet - used for the general appearance of the console 
#         (background and ormopt colors, etc)
#         b) a color syntax highlight scheme - used for syntax highlighting
#         
#         
#         This allows bypassing any style/colors specified in 
#         ~./jupyter/jupyter_qtconsole_config.py
#         
#         Parameter:
#         -------------
#         
#         scheme: str (optional, default is the empty string) - name of available 
#                 syntax style (pygment).
#                 
#                 For a list of available pygment names, see
#                 
#                 available_pygments() in this module
#                 
#                 When empty or None, reverts to the defaults as set by the jupyter 
#                 configuration file.
#                 
#         colors: str (optional, default is None) console color set. 
#             There are, by defult, three color sets:
#             'light' or 'lightbg', 
#             'dark' or 'linux',
#             'nocolor'
#             
#         """
#         import pkg_resources
#         #print("console.set_pygment scheme:", scheme, "colors:", colors)
#         if scheme is None or (isinstance(scheme, str) and len(scheme.strip()) == 0):
#             self.set_default_style()
#             #self._control.style = self._initial_style
#             #self.style_sheet = self._initial_style_sheet
#             return
#         
#         # NOTE: 2020-12-23 11:15:50
#         # code below is modified from qtconsoleapp module, plus my comments;
#         # find the value for colors: there are three color sets for prompts:
#         # 1. light or lightbg (i.e. colors suitable for schemes with light background)
#         # 2. dark or linux (i.e colors suitable for schemes with dark background)
#         # 3. nocolor - for black and white scheme
#         if isinstance(colors, str) and len(colors.strip()): # force colors irrespective of scheme
#             colors=colors.lower()
#             if colors in ('lightbg', 'light'):
#                 colors='lightbg'
#             elif colors in ('dark', 'linux'):
#                 colors='linux'
#             else:
#                 colors='nocolor'
#         
#         else: # (colors is "" or anything else)
#             # make an informed choice of colors, according to whether the scheme
#             # is bright (light) or dark
#             if scheme=='bw':
#                 colors='nocolor'
#             elif styles.dark_style(scheme):
#                 colors='linux'
#             else:
#                 colors='lightbg'
#         #else:
#             #colors=None
#             
#         if scheme in available_pygments():
#             #print("found %s scheme" % scheme)
#             # rules of thumb:
#             #
#             # 1. the syntax highlighting scheme is set by setting the console 
#             # (RichJupyterWidget) 'syntax_style' attribute to scheme. 
#             #
#             # 2. the style sheet gives the widget colors ("style") - so we always 
#             #   need a style sheet, and we "pygment" the console by setting its
#             #   'style_sheet' attribute. NOTE that schemes do not always provide
#             #   prompt styling colors, therefore we need to set up a style sheet 
#             #   dynamically based on the colors guessed according to whether the
#             #   scheme is a "dark" one or not.
#             #
#             try:
#                 sheetfile = pkg_resources.resource_filename("jupyter_qtconsole_colorschemes", "%s.css" % scheme)
#                 
#                 if os.path.isfile(sheetfile):
#                     with open(sheetfile) as f:
#                         sheet = f.read()
#                         
#                 else:
#                     #print("no style sheet found for %s" % scheme)
#                     sheet = styles.sheet_from_template(scheme, colors)
#                     #if colors:
#                         #sheet = styles.sheet_from_template(scheme, colors)
#                     #else:
#                         #sheet = styles.sheet_from_template(scheme)
#                     
#                 self.style_sheet = sheet
#                 self.syntax_style = scheme
#                 # also need to call notifiers - this is the order in which they
#                 # are called in qtconsoleapp module ('JupyterConsoleApp.init_colors')
#                 # not sure whether it makes a difference but stick to it for now
#                 self._syntax_style_changed()
#                 self._style_sheet_changed()
#                 
#                 # remember these changes - to save them in _save_settings_()
#                 self._console_pygment = scheme
#                 self._console_colors = colors
#                 #self._custom_style_sheet = sheet
#                 #self._custom_syntax_scheme = scheme
#                 
#                 # NOTE: 2021-01-08 14:23:14
#                 # These two will affect all Jupyter console apps in Scipyen that
#                 # will be launched AFTER the internal console has been initiated. 
#                 # These include the ExternalIPython.
#                 #JupyterWidget.style_sheet = sheet
#                 #JupyterWidget.syntax_style = scheme
#                 
#             except:
#                 traceback.print_exc()
#                 #pass
#             
#             # not needed (for now)
#             #style = pstyles.get_style_by_name(scheme)
#             #try:
#                 ##self.syntax_style=scheme
#                 #self._control.style = style
#                 #self._highlighter.set_style (scheme)
#                 #self._custom_syntax_style = style
#                 #self._syntax_style_changed()
#             #except:
#                 #traceback.print_exc()
#                 #pass
            
class ScipyenConsole(QtWidgets.QMainWindow, WorkspaceGuiMixin):
    # NOTE: 2023-09-27 12:55:24 TODO
    # to implements julia-style propgress indicators;
    # see/adapt qtconsole.console_widget code -> in ScipyenConsoleWidget
    historyItemsDropped = Signal()
    workspaceItemsDropped = Signal()
    fileSystemItemsDropped = Signal()
    loadUrls = Signal(object, bool, QtCore.QPoint)
    pythonFileReceived = Signal(str, QtCore.QPoint)
    executed = Signal()
    
    def __init__(self, parent=None, **kwargs):
        scipyenWindow = kwargs.pop("scipyenWindow", None) # take this out for below...
        super().__init__(parent=parent, **kwargs) # initializes QtWidgets.QMainWindow
        kwargs["scipyenWindow"] = scipyenWindow # ... then place back in kwargs for WorkspaceGuiMixin
        WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs) # initializes WorkspaceGuiMixin
        self.consoleWidget = ScipyenConsoleWidget(mainWindow=self._scipyenWindow_) # from WorkspaceGuiMixin
        # self.consoleWidget = ScipyenConsoleWidget(mainWindow=parent)
        self.consoleWidget.setAcceptDrops(True)
        self.setCentralWidget(self.consoleWidget)
        
        self.consoleWidget.historyItemsDropped.connect(self.historyItemsDropped)
        self.consoleWidget.workspaceItemsDropped.connect(self.workspaceItemsDropped)
        self.consoleWidget.fileSystemItemsDropped.connect(self.fileSystemItemsDropped)

        self.consoleWidget.loadUrls.connect(self.loadUrls)
        self.consoleWidget.pythonFileReceived.connect(self.pythonFileReceived)
        self.consoleWidget.executed.connect(self.executed)
        self.consoleWidget.loadSettings() # inherited from ScipyenConfigurable
        self.widget = self.consoleWidget
        self.active_frontend = self.consoleWidget
        # WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs) # initializes WorkspaceGuiMixin
        self._configureUI_()
        self.loadSettings()
        
    def _configureUI_(self):
        ctrl = "Meta" if sys.platform == 'darwin' else "Ctrl"
        menuBar = self.menuBar()
        self.file_menu = menuBar.addMenu("File")
        
        self.saveToFile = self.file_menu.addAction(QtGui.QIcon.fromTheme("document-save"),
                                                    "Save contents to file")
        
        self.saveToFile.triggered.connect(self._slot_saveToFile)
        
        self.saveRawToFile = self.file_menu.addAction(QtGui.QIcon.fromTheme("document-save"),
                                                        "Save contents (raw) to file")
        
        self.saveRawToFile.triggered.connect(self._slot_saveRawToFile)
        
        self.saveFormattedToFile = self.file_menu.addAction(QtGui.QIcon.fromTheme("document-save-as"),
                                                            "Save formatted contents to file")
        
        self.saveFormattedToFile.triggered.connect(self.consoleWidget.export_html) # slot inherited from qtconsole.ConsoleWidget
        
        self.saveSelectionToFile = self.file_menu.addAction(QtGui.QIcon.fromTheme("document-save"),
                                                            "Save selection to file")
        
        self.saveSelectionToFile.triggered.connect(self._slot_saveSelectionToFile)
        
        self.saveRawSelectionToFile = self.file_menu.addAction(QtGui.QIcon.fromTheme("document-save"),
                                                                "Save selection (raw) to file")
        
        self.saveRawSelectionToFile.triggered.connect(self._slot_saveRawSelectionToFile)
        
        self.settings_menu = menuBar.addMenu(QtGui.QIcon.fromTheme("settings-configure"), "Settings")
        
        self.listMagicsAction = self.file_menu.addAction(QtGui.QIcon.fromTheme("view-list-text"),"List magics")

        self.listMagicsAction.triggered.connect(self._slot_listMagics)
        
        available_syntax_styles = scipyen_console_styles.get_available_syntax_styles() # defined in this module
        
        # if len(available_syntax_styles):
        if len(PYGMENT_STYLES):
            self.syntax_style_menu = self.settings_menu.addMenu("Syntax Style")
            
            style_group = QtWidgets.QActionGroup(self)
            
            actions = [QtWidgets.QAction("{}".format(s), self, triggered = partial(self.active_frontend._set_syntax_style, s)) for s in PYGMENT_STYLES]
            
            for action in actions:
                action.setCheckable(True)
                style_group.addAction(action)
                self.syntax_style_menu.addAction(action)
                if action.text() == self.active_frontend.syntaxStyle:
                    action.setChecked(True)
                    self.syntax_style_menu.setDefaultAction(action)
            # for style in available_syntax_styles:
#             for style in PYGMENT_STYLES:
#                 print(f"{self.__class__.__name__}._configureUI_ adding menu item for pygment {style}")
#                 action = QtWidgets.QAction("{}".format(style), self,
#                                        triggered=lambda v:
#                                            self.active_frontend._set_syntax_style(val=style))
#                                            # self.active_frontend._slot_setSyntaxStyle(style))
#         
#                 action.setCheckable(True)
#                 style_group.addAction(action)
#                 self.syntax_style_menu.addAction(action)
#                 if style == self.active_frontend.syntaxStyle:
#                     action.setChecked(True)
#                     self.syntax_style_menu.setDefaultAction(action)

        self.colors_menu = self.settings_menu.addMenu("Console Colors")
        colors_group = QtWidgets.QActionGroup(self)
        for c in self.active_frontend.available_colors:
            action = QtWidgets.QAction("{}".format(c), self,
                                       triggered = lambda:
                                           self.active_frontend._set_console_colors(c))
            action.setCheckable(True)
            colors_group.addAction(action)
            self.colors_menu.addAction(action)
            if c == self.active_frontend.consoleColors:
                action.setChecked(True)
                self.colors_menu.setDefaultAction(action)
        
        scrollbar_pos = ("left", "right")
        self.sb_menu = self.settings_menu.addMenu("Scrollbar Position")
        sb_group = QtWidgets.QActionGroup(self)
        for s in self.active_frontend.scrollbar_positions.values():
            action = QtWidgets.QAction("{}".format(s), self,
                                       triggered = lambda v, val = s:
                                           self.active_frontend._set_sb_pos(val=val))
            action.setCheckable(True)
            sb_group.addAction(action)
            self.sb_menu.addAction(action)
            
            if s == self.active_frontend.scrollbar_positions[self.active_frontend.scrollBarPosition]:
                action.setChecked(True)
                self.sb_menu.setDefaultAction(action)

        self.choose_font_act = QtWidgets.QAction("Console Font", self, shortcut=ctrl+"F",
                                                 triggered = self.choose_font)
        
        self.settings_menu.addAction(self.choose_font_act)
        self.addAction(self.choose_font_act)
        
        self.set_console_scrollbackAction = QtWidgets.QAction("Console scroll back",
                                                              self, shortcut=ctrl+"L",
                                                              triggered = self.set_scrollBack)
        
        self.settings_menu.addAction(self.set_console_scrollbackAction)
        self.addAction(self.set_console_scrollbackAction)
        
    @Slot()
    def _slot_listMagics(self):
        self.ipkernel.shell.run_cell("%lsmagic")
            
            
    @Slot()
    def _slot_saveToFile(self):
        self.consoleWidget.select_all_smart() # inherited from qtconsole.ConsoleWidget
        text = self.consoleWidget._format_text_selection(self.consoleWidget._control.textCursor().selection().toPlainText())
        if len(text.strip()):
            self._saveToFile(text, mode="python")
        
    @Slot()
    def _slot_saveRawToFile(self):
        self.consoleWidget.select_document() # inherited from qtconsole.ConsoleWidget
        text = self.consoleWidget._control.toPlainText()
        if len(text.strip()):
            self._saveToFile(text, mode="raw")
                
    @Slot()
    def _slot_saveRawSelectionToFile(self):
        c = self.consoleWidget._get_cursor()
        text = c.selectedText()
        if len(test.strip()):
            self._savetoFile(text, mode="raw")
        
        
    @Slot()
    def _slot_saveSelectionToFile(self):
        c = self.consoleWidget._get_cursor()
        text = self.consoleWidget._format_text_selection(c.selection().toPlainText())
        if len(text.strip()):
            self._saveToFile(text, mode="python")
    
    
    def _saveToFile(self, text, mode="python"):
        from iolib import pictio as pio
        if not isinstance(mode, str) or len(mode.strip()) == 0:
            mode = "python"
            
        if mode.lower() == "raw":
            fileflt = ";;".join(["Text files (*.txt)", "All Files (*.*)"])
        elif mode.lower() == "html/xml":
            fileflt = ";;".join(["HTML file (*.htm*)", "XML file (*.xml)", "All Files (*.*)"])
        else:
            fileflt = ";;".join(["Python source file (*.py)", "All Files (*.*)"])
        if len(text.strip()):
            filename, filefilter = self.chooseFile("Save buffer to file",
                                                   fileFilter = fileflt,
                                                   single=True,
                                                   save=True)
            
            if isinstance(filename, str) and len(filename.strip()):
                pio.saveText(text, filename)
        
    def loadSettings(self):
        self.consoleWidget.loadSettings() # inherited from ScipyenConfigurable
        super(WorkspaceGuiMixin, self).loadSettings()
        
    def saveSettings(self):
        self.consoleWidget.saveSettings() # inherited from ScipyenConfigurable
        super(WorkspaceGuiMixin, self).saveSettings()
        
    def set_scrollBack(self):
        if self.active_frontend and hasattr(self.active_frontend, "guiSetScrollBack"):
            self.active_frontend.guiSetScrollBack()
        
    def choose_font(self):
        currentFont = self.consoleFont
        selectedFont, ok = QtWidgets.QFontDialog.getFont(currentFont, self)
        if ok:
            self.active_frontend.font = selectedFont
        
    def closeEvent(self,evt):
        self.saveSettings()
        evt.accept()
    
    def paste(self, *args, **kwargs):
        self.consoleWidget.paste(*args, **kwargs)
        
    def execute(self, *args, **kwargs):
        self.consoleWidget.execute(*args, **kwargs)
        
    def writeText(self, text):
        self.consoleWidget.writeText(text)
        
    @property
    def ipkernel(self):
        """The IPython kernel runnin in this console"""
        return self.consoleWidget.ipkernel
        
    @property
    def stdout(self):
        """The standard output stream of the kernel running in this console"""
        return self.ipkernel.stdout
    
    @property
    def shell(self):
        """The interactive shell running in this console"""
        return self.ipkernel.shell

    @property
    def consoleFont(self):
        # so that is doesn't override QMainWindow.font()
        if self.active_frontend:
            return self.active_frontend.font
        else:
            return self.defaultFixedFont
    
    @consoleFont.setter
    def consoleFont(self, val:QtGui.QFont):
        self.active_frontend.font = val

    @property
    def kernel_manager(self):
        return self.consoleWidget.kernel_manager
    
    @property
    def consoleScrollBack(self):
        if self.active_frontend:
            return self.active_frontend.scrollBackSize
        
    @consoleScrollBack.setter
    def consoleScrollBack(self, val:int):
        if self.active_frontend:
            self.active_frontend.scrollBackSize = val
        
        
