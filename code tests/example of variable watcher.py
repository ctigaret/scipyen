#"class" _WorkspaceWatcher(QtCore.QObject):
    #workspaceChanged = pyqtSignal(name="workspaceChanged")
    
    #def __init__(self, shell, hidden_vars=dict(), *args, **kwargs):
        #super(_WorkspaceWatcher, self).__init__(*args, **kwargs)
        
        #if not isinstance(shell, InProcessInteractiveShell):
            #raise TypeError("Expecting an InProcessInteractiveShell; got %s instead" % type(shell).__name__)
        
        #self.shell = shell
        #self.cached_vars = dict()
        #self.modified_vars = dict()
        #self.new_vars = dict()
        #self.deleted_vars = dict()
        #self.hidden_vars = hidden_vars
    
    #def reset(self):
        #if not isinstance(self.shell, InProcessInteractiveShell):
            #return

        #self.cached_vars = dict([item for item in self.shell.user_ns.items() if item[0] not in self.hidden_vars and not item[0].startswith("_")])
        #self.modified_vars.clear()
        #self.new_vars.clear()
        #self.deleted_vars.clear()
    
    
    #def pre_run_cell(self):#, info=None):
        #print("pre_run_cell")
        #if info is not None:
            #print("info:", info)
            #print('Cell code: "%s"' % info.raw_cell)

    #def post_run_cell(self):#, result=None):
        #print("post_run_cell")
        #if result is not None:
            #print("result", result)
            #print('Cell code: "%s"' % result.info.raw_cell)
            #if result.error_before_exec:
                #print('Error before execution: %s' % result.error_before_exec)
                
        #self.deleted_vars.update([item for item in self.cached_vars.items() if item[0] not in self.shell.user_ns])
        
        #for item in self.deleted_vars:
            #self.cached_vars.pop(item[0], None)
        
        #new_vars = [item for item in self.shell.user_ns.items() if item[0] not in self.cached_vars.keys() and item[0] not in self.hidden_vars and not item[0].startswith("_")]
        
        #self.new_vars.update(new_vars)
        
        #existing_vars = [item for item in self.shell.user_ns.items() if item in self.cached_vars.items()]
        
        #self.modified_vars.update([item for item in existing_vars if item[1] != self.cached_vars[item[0]]] )
        
        #self.workspaceChanged.emit()

    #def pre_execute(self):
        #"""Initialize dictionaries of modified/added/removed variables
        
        #This is done here in order to capture changes in workspace due to
        #code executed outside the console shell/ipkernel
        
        #This needs a call to self.reset() from client code
        #"""
        ##print("pre_execute")
        
        ## NOTE: 2018-10-07 08:54:08
        ## set up a clean slate
        
        ## 1) cache the variables currently present in user namespace of the shell,
        ##   that simultaneously satisfy the conditions:
        ##   a) are not registered as hidden by the pict framework
        ##   b) their namespace symbol does not begin with a _ 
        ##      (i.e. they are NOT an IPython hidden variable)
        ##self.cached_vars =  dict([item for item in self.shell.user_ns.items() if item[0] not in self.hidden_vars and not item[0].startswith("_")])
        #self.cached_vars.update([item for item in self.shell.user_ns.items() if item[0] not in self.hidden_vars and not item[0].startswith("_")])
        
        ## NOTE: remove items that have been deleted from workspace by code outside the kernel/shell
        
        ##deleted_items = [item for item in self.cached_vars.items() if item[0] not in self.shell.user_ns]
        
        ##for item in deleted_items:
            ##self.cached_vars.pop(item, None)
            
        ## NOTE: 2018-10-07 16:43:56
        ## capture here variables modified/added/removed by code executed outside the
        ## shell/ipkernel
        ##self.deleted_vars.update([item for item in self.cached_vars.items() if item[0] not in self.shell.user_ns])
        
        ##new_vars = [item for item in self.shell.user_ns.items() if item[0] not in self.cached_vars.keys() and item[0] not in self.hidden_vars and not item[0].startswith("_")]
        
        ##self.new_vars.update(new_vars)
        
        ##existing_vars = [item for item in self.shell.user_ns.items() if item[0] in self.cached_vars.keys() and item[1] != self.cached_vars[item[0]]]
        
        ##self.modified_vars.update([item for item in existing_vars if item[1] != self.cached_vars[item[0]]])
        
        ## 2) clean up & make room for modified, new an deleted variable dictionaries
        ##   to be populated in post_execute
        
        ##print("cached vars in pre_execute: ", self.cached_vars)
        
        ##self.modified_vars.clear()
        ##self.new_vars.clear()
        ##self.deleted_vars.clear()
        
    #def post_execute(self):
        
        ## NOTE: 2018-10-07 09:00:53
        ## find out what happened to the variables and populate the corresponding
        ## dictionaries
        
        ## 1) deleted variables -- present in cached vars but not in the user namespace anymore
        #self.deleted_vars.update([item for item in self.cached_vars.items() if item[0] not in self.shell.user_ns])
        
        ##print("deleted vars:", self.deleted_vars)
        
        #new_vars = [item for item in self.shell.user_ns.items() if item[0] not in self.cached_vars.keys() and item[0] not in self.hidden_vars and not item[0].startswith("_")]
        
        #self.new_vars.update(new_vars)
        
        ##print("new vars:", self.new_vars)
        
        #existing_vars = [item for item in self.shell.user_ns.items() if item[0] in self.cached_vars.keys() and item[1] != self.cached_vars[item[0]]]
        
        #self.modified_vars.update([item for item in existing_vars if item[1] != self.cached_vars[item[0]]])
        
        ##print("modified vars", self.modified_vars)
        
        #self.cached_vars.update(self.new_vars)
        #self.cached_vars.update(self.modified_vars)
        #for item in self.deleted_vars:
            #self.cached_vars.pop(item[0], None)
            
        ##print("updated cached vars:", self.cached_vars)
        
        ##if len(self.modified_vars) or len(self.new_vars) or len(self.deleted_vars):
            ##self.workspaceChanged.emit()
        #self.workspaceChanged.emit()
        ##self.reset()
