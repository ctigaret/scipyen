# -*- coding: utf-8 -*-

import sys, os
os.environ['QT_API'] = 'pyqt'

from IPython.qt.console.rich_ipython_widget import RichIPythonWidget
from IPython.qt.inprocess import QtInProcessKernelManager

#from PyQt4 import QtGui, QtCore

class EmbedIPython(RichIPythonWidget):
    def __init__(self,backend):
        super(RichIPythonWidget, self).__init__()
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        self.kernel = self.kernel_manager.kernel
        self.kernel.gui = backend
        #self.kernel.shell.push(kwarg)
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()


class EmbeddedIPython(object):
    #def __init__(self, backend='Qt'):
        #super(EmbeddedIPython,self).__init__()
        #self.init_ipkernel(backend)
        
    def init_ipkernel(self, backend):
        print("EmbeddedIPKernel::init_ipkernel('%s')" % backend)
        #self.console = EmbeddedIPKernel(backend)
        self.console = None
        self.wokspace=dict()
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        self.ipkernel = self.kernel_manager.kernel
        self.ipkernel.gui = backend
        #self.kernel.shell.push(kwarg)
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        self.workspace = self.ipkernel.shell.user_ns
        
    def init_qt_console(self, evt=None):
        if self.console is None:
            self.console = RichIPythonWidget()
            self.console.kernel_manager = self.kernel_manager
            self.console.kernel_client = self.kernel_client
            self.console.show()

    #def closeConsole(self, evt=None):
        #if self.console is not None:
            #self.console.close()
            #self.console=None
