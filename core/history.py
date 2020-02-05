# -*- coding: utf-8 -*-
"""
NOTE: 2018-02-20 14:01:07
NOT used in pict!!!

hh = get_ipython().history_manager.search('*')

hh is a generator, the iteration on which yields a tuple
(session_no, line_no, line_contents)

this is in efect what %hist -g line magic does in jupyter (ipython)

This is what we need to call upon console initialization in pict

we then need to populate a tree model to be displayed in the console history
(to use a QTreeView widget)

alternatively we use a QTreeWidget -- uses a predefined tree model that we need
to populate -- seems easier to generate a hierarchical list as each node is a
session, whereas each leaf is a command input

"""
from __future__ import print_function

import io, threading

from IPython.core.magic_arguments import (argument, magic_arguments, parse_argstring)



class HistoryWatcher(object):
    def __init__(self, ip, pw):
        self.shell = ip
        self.consumer = pw
        self.lastCommand = None
        
    def post_execute(self):
        self.lastCommand



class HistoryConsoleKeeperThread(threading.Thread):
    daemon = True
    stop_now = False
    enabled = True
    
    def __init__(self, history_manager):
        """ history_manager is the one from IPython's InProcessInteractiveShell run by pict
        """
        super(HistoryConsoleKeeperThread, self).__init__(name="PICTHistoryConsoleKeeperThread")
        self.enabled = history_manager.enabled
        atexit.register(self.stop)
        
        
    def run(self):
        """
        Output input history to a stream
        """
        try:
        except Exception as e:
            print("Unexpected error in HistoryConsoleKeeperThread (%s)." % repr(e))


    def stop(self):
        self.stop_now = True
        self.history_manager.save_flag.set()
        self.join()
        
        
