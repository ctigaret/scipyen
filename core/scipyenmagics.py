# -*- coding: utf-8 -*-
"""Defines magics for the Scipyen's internal IPython
"""
import os
import confuse
from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic,
                                needs_local_scope)

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
        
    @line_magic
    @needs_local_scope
    def remote_ipython(self, line, local_ns):
        pass
    
    @line_magic
    @needs_local_scope
    def remote_ipython(self, line, local_ns):
        pass
    
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
    def LSCaT(self, line, local_ns):
        from imaging import CaTanalysis
        if len(line.strip()):
            lsdata = local_ns.get(line, None)
            
        else:
            lsdata = None
            
        mw = local_ns.get("mainWindow", None)
        
        #if isinstance(mw, ScipyenWindow):
        if mw.__class__.__name__ == "ScipyenWindow":
            if lsdata is not None:
                lscatWindow = CaTanalysis.LSCaTWindow(lsdata, parent=mw, pWin=mw, win_title="LSCaT")
            else:
                lscatWindow = CaTanalysis.LSCaTWindow(parent=mw, pWin=mw, win_title="LSCaT")
            lscatWindow.show()
            
        #return line
