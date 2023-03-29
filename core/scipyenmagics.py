# -*- coding: utf-8 -*-
"""Defines magics for the Scipyen's internal IPython
"""
import os, warnings, keyword
import confuse
from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic,
                                needs_local_scope)

from core import strutils

@magics_class
class ScipyenMagics(Magics):
    @line_magic
    @needs_local_scope
    def exit(self, line, local_ns):
        """%exit line magic
        """
        #if "mainWindow" in local_ns and isinstance(local_ns["mainWindow"], ScipyenWindow):
        if "mainWindow" in local_ns and local_ns["mainWindow"].__class__.__name__ == "ScipyenWindow":
            local_ns["mainWindow"].slot_Quit()
            
        #return line
    
    @line_magic
    @needs_local_scope
    def quit(self, line, local_ns):
        """%exit line magic
        """
        #if "mainWindow" in local_ns and isinstance(local_ns["mainWindow"], ScipyenWindow):
        if "mainWindow" in local_ns and local_ns["mainWindow"].__class__.__name__ == "ScipyenWindow":
            local_ns["mainWindow"].slot_Quit()
            
        #return line
    
    @line_magic
    @needs_local_scope
    def external_ipython(self, line, local_ns):
        """%external_ipython magic launches a separate Jupyter Qt Console process
        """
        
        #if "mainWindow" in local_ns and isinstance(local_ns["mainWindow"], ScipyenWindow):
        if "mainWindow" in local_ns and local_ns["mainWindow"].__class__.__name__ == "ScipyenWindow":
            local_ns["mainWindow"]._init_ExternalIPython_()
            
        #return line
    
    @line_magic
    @needs_local_scope
    def neuron_ipython(self, line, local_ns):
        """%neuron_ipython magic launches a separate NEURON Python process
        """
        
        #if "mainWindow" in local_ns and isinstance(local_ns["mainWindow"], ScipyenWindow):
        if "mainWindow" in local_ns and local_ns["mainWindow"].__class__.__name__ == "ScipyenWindow":
            local_ns["mainWindow"]._init_ExternalIPython_(new="neuron")
            
        #return line
        
#     @line_magic
#     @needs_local_scope
#     def remote_ipython(self, line, local_ns):
#         pass
#     
#     @line_magic
#     @needs_local_scope
#     def remote_ipython(self, line, local_ns):
#         pass
    
    @line_magic
    @needs_local_scope
    def scipyendir(self, line, local_ns):
        scipyen_settings = local_ns.get("scipyen_settings", None)
        ret = ""
        if isinstance(scipyen_settings, confuse.Configuration):
            defsrc = [s for s in scipyen_settings.sources if s.default]
            if len(defsrc):
                ret = os.path.dirname(defsrc[0].filename)
                
        if len(ret.strip()) == 0:
            mw = local_ns.get("mainWindow", None)
            if mw.__class__.__name__ == "ScipyenWindow":
                ret = mw._scipyendir_
                
        return ret
                
    @line_magic
    @needs_local_scope
    def appdir(self, line, local_ns):
        return self.scipyendir(line, local_ns)
    
    @line_magic
    @needs_local_scope
    def workspace(self, line, local_ns):
        """%workspace magic returns a reference to the user namespace
        
        Alternative function to use in your own codes: 
            core.workspacefunctions.user_workspace()
        
        """
        return local_ns
    
    @line_magic
    @needs_local_scope
    def scipyen_debug(self, line, local_ns):
        """Turn on/off debugging messages in Scipyen code
        
        Calls:
        scipyen_debug => toggles scipyen debugging
        
        scipyen_debug "on", or scipyen_debug True -> turns debugging ON
        
        scipyen_debug "off", or scipyen_debug False -> turns debugging OFF
        
        any other argument turns debugging OFF
        
        For a programmatic way to access/set SCIPYEN_DEBUG, see
        workspacefunctions.debug_scipyen()
        
        Returns:
        -------
        The new value of SCIPYEN_DEBUG in the user workspace
        
        """
        if len(line.strip()):
            if line.strip().lower() in ("on", "true", "off", "false"):
                val = True if line.strip().lower() in ("on", "true") else False
            
            else:
                val = False
                
            return debug_scipyen(val)
        
        else:
            val = user_workspace().get("SCIPYEN_DEBUG", False)
            return debug_scipyen(not val)
            
    @line_magic
    @needs_local_scope
    def clear(self, line, local_ns):
        """Overrides zmq interactive shell 'clear' line magic
        This is because in Scipyen with Python 3.10 'clear' clears the system 
        console, NOT Scipyen's console.
        """
        console = local_ns.get("console", None)
        if console.__class__.__name__ == 'ScipyenConsole':
            console.centralWidget().clear()

    @line_magic
    @needs_local_scope
    def view(self, line, local_ns):
        """View the variable named in `line` using appropriate Scipyen viewers.
        
        Parameters:
        ==========
        `line`: a str containing either:
        
            • one token - a valid variable name (symbol) - the variable will be
                viewed in an appropriate synpien viewer; if no instance of viewer
                is available one will be created; otherwise, an existing viewer
                is used.
        
            • several comma- or space-separated tokens, where all tokens are 
                valid Python symbols, with either:
        
                ∘ all being variable names (in which case, all variables are 
                viewed in separate instances of their default viewer types)
        
                    Each of these variables will be viewed in a new instance of
                their default viewer type
        
                ∘ all but the last token are variable names, and the last token
                if a supported viewer _TYPE_ (i.e. class name).
        
                    Each of the variables will be viewed in a new instance of 
                the specified viewer type (or a warning will be printed if the
                specified viewer type is not appropriate for the given variable)
        
                ∘ all but the last token are variable names and the last token
                    is '?' - in this case the macro will print a table of 
                    viewer type names for each variable name specified in the line
        
        WARNING: Entering '?' by itself (not immediately after the magic name) 
            will raise an error.
        
        """
        from gui.mainwindow import VTH
        mw = local_ns.get("mainWindow", None)
        # check if line has tokens
        sep = " "
        
        if " " in line:
            sep = " "
            
        elif "," in line:
            sep = ","
            
        elif keyword.iskeyword(line) or line != strutils.str2symbol(line):
            raise ValueError(f"This magic does not accept keyword or invalid variable names")
            
        if mw.__class__.__name__ != "ScipyenWindow":
            return 
        
        tokens = [s.strip(" ,") for s in line.split(sep)]
        
        # print(f"tokens = {tokens}")
        
        if len(tokens) == 0:
            token = tokens[0]
            
            mw.showVariable(token, newWindow=False)
            return
                
        else:
            viewerTypes = list(k for k in mw.viewers)
            viewers = list(k.__name__ for k in viewerTypes)
            
            viewerType = None # will trigger the use of the default viewer type
            
            if tokens[-1] == '?':
                if len(tokens) > 2:
                    msg = ["Variable name:\tRecomended viewer type(s):",
                        "==============\t=========================="]
                    for token in tokens[0:-1]:
                        obj = mw.workspace.get(token, None)
                        if obj is None:
                            continue
                        supportedViewerSpecs = list(h[0] for h in VTH.get_handler_spec(obj))
                        msg.append(f"{token}:")
                        for vt in supportedViewerSpecs:
                            msg.append(f"\t{vt.__name__}")
                            
                    print("\n".join(msg))
                    return
                else:
                    token = tokens[0]
                    obj = mw.workspace.get(token, None)
                    msg = ["Choose viewer:"]
                    if obj is None:
                        return
                    supportedViewerSpecs = list(enumerate((h[0], h[1]) for h in VTH.get_handler_spec(obj)))
                    ndx, viewerTypeAndNames = zip(*supportedViewerSpecs)
                    viewerTypes, viewerTypeNames  = zip(*viewerTypeAndNames)
                    ndx = [f"{v}" for v in ndx]
                    msg.extend([f"{vt[0]} {vt[1][1]}" for vt in supportedViewerSpecs])
                    msg.append("")
                    ret = input("\n".join(msg))
                    
                    if ret in ndx:
                        viewerType = viewerTypes[int(ret)]
                        
                    elif ret in viewerTypeNames:
                        typendx = viewerTypeNames.index(ret)
                        viewerType = viewerTypes[typendx]
                        
                        
                    else:
                        viewerType = None
                        
                    if viewerType is not None:
                        mw.showVariable(token, viewerType = viewerType)
                        return
                    else:
                        return
            
            # check is last token is a viewer type
            elif tokens[-1] in viewers:
                viewTypeNdx = viewers.index(tokens[-1])
                viewerType = viewerTypes[viewTypeNdx]
                
                tokens = tokens[0:-1]
                
            for token in tokens:
                if keyword.iskeyword(token) or token != strutils.str2symbol(token):
                    warnings.warn(f"This magic does not accept keyword or invalid variable names")
                    continue
                
                obj = mw.workspace.get(token, None)
                
                if obj is None:
                    continue
                
                handlers = VTH.get_handler_spec(obj)
                
                if viewerType is not None:
                    if viewerType not in list(h[0] for h in handlers):
                        warnings.warn(f"{viewerType.__name__} viewer does not support object {token} of type {type(obj).__name__}")
                        continue
                    
                    mw.showVariable(token, newWindow=True, viewerType = viewerType)
                    
                else:
                    mw.showVariable(token, newWindow=True)
                
                
    @line_magic
    @needs_local_scope
    def newView(self, line, local_ns):
        mw = local_ns.get("mainWindow", None)
        if mw.__class__.__name__ == "ScipyenWindow":
            mw.showVariable(line)
                
        # return line
            
        
       
