#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

WARNING: h.allsec() will enumerate sections both INSIDE your cell and outside 
of it!

Created on Sun May 10 14:05:54 2020

@author: cezar.tigaret@gmail.com TigaretC@cardiff.ac.uk


"""
import os, typing, warnings
from numbers import Number, Real
import numpy as np
import scipy as sp
import pandas as pd
#import matplotlib as mpl
#import matplotlib.pyplot as plt

# NOTE: 2021-01-14 11:47:24 The following import is OK:
# h object is global and gui imports but does not launch the NEURON gui 
# (based on InterViews library) unless the gui is not running
import neuron
from neuron import (h, rxd, nrn, sections) # gui should be imported via Scipyen
from neuron.units import (ms, mV, um)

__module_path__ = os.path.abspath(os.path.dirname(__file__))

# NOTE: 2021-02-07 17:26:22
# library functions for importing 3D morphology: located in share/nrn/lib/hoc/
# In particular, import3d.hoc 'xopen's share/nrn/lib/hoc/import3d/read_swc.hoc
# which declares the HOC template Import3d_SWC_read
# Here, a custom version is used
h.load_file(os.path.join(__module_path__, "my_import3d.hoc"))
#h.load_file("import3d.hoc")

class PyNRNCell(object):
    """Generic PyNRNCell ball-and-stick model
    """
    default_nseg = 51
    d_lambda = 0.1
    
    def __init__(self, gid:int, /, **kwargs):
        """
        Constructs a ball-and-stick neuron model.
        
        Positional-only parameters
        --------------------------
        gid: int - the ID of the cell
        
        Var-keyword parameters:
        -----------------------
        position: dict with the following str keys mapped to
            numeric scalars:
            'x':int, float, the x position; default is 0
            'y':int, float, the y position; default is 0 
            'z':int, float, the z position; default is 0 
            'theta':int, float, the rotation angle about the Z axis, in radian; 
                default is 0.
                
                NOTE: the Z axis is perpendicular to the screen plane.
            
        name: str: name of the cell; when missing, the new PyNRNCell instance will be 
            be named after its type name.
            
        nseg: None (default) or int > 0. 
            When None, all sections in the cell instance will get 51 segments.
            When an int, if is even it will be incremented by one (so that
            there are always an odd number of segments in each section).
            
            
        <any_name>: section definition data as a dict with keys:
            'name':str
            'L': Real scalar
            'diam': Real scalar, or iterable (tuple, list) of Real scalars
            'cm': Real scalar, or iterable (tuple, list) of Real scalars
            'diam_interp': Real scalar, or iterable (tuple, list) of Real scalars
            'cm_interp': Real scalar, or iterable (tuple, list) of Real scalars
            'Ra': Real scalar
            'freq': Real scalar
            'nseg': odd int > 0
            'd_lambda': Real scalar
            'parent': nrn.Section
            'parent_pos': Real scalar in the range (0,1); default is 1
            'orientation': Real scalar in the interval [0,1]; default is 0
            
        NOTE: The section name is the one specified in this dict's 'name' key;
        if this key is missing, then the section name is given by the value of
        <any_name>
            
        """
        self._gid = gid
        
        position = kwargs.pop("position", dict())
        self._position = dict((k, position.get(k,0.) if isinstance(position.get(k,0), Real) else 0.) for k in ("x", "y", "z", "theta"))
        
        name = kwargs.pop("name", None)
        self._name = name if (isinstance(name, str) and len(name.strip())) else self.__class__.__name__
        
        for secname, secdict in kwargs.items():
            # NOTE: 2022-01-30 17:00:26:
            # make sure we give this section a name
            sname = secdict.get("name", None) 
            if not isinstance(sname, str) or len(sname.strip()) == 0:
                secdict["name"] = secname
                
            self.addSection(**secdict)
        
        #self._setup_morphology()
        
        #h.define_shape()
        
        self._set_position(self._position["x"], self._position["y"], self._position["z"])
        self._rotate(self._position["theta"])
        
        self._shape_view = None
        
        ## NOTE: 2021-01-30 14:33:44 
        ## for plotting the stylized geometry of this cell
        #if self._position:
            #h.define_shape()
            #self._set_position(self._position["x"], self._position["y"], self._position["z"])
            #self._rotate(self._position["theta"])
        
        self._setup_biophysics()
        
        if len(self.all) == 0:
            print("The cell has no sections (e.g., soma, dendrites, axon, etc.).")
            print("To add sections to this cell call its 'addSection(...)' method, or its 'loadMorphologySWC(swc_file_name)' method to load a neuron morphology from a SWC file.")
            
        
    def __del__(self):
        """Remove all pointers to sections that belong to this cell
        """
        for section in self.all:
            #self.__dict__.__delitem__(section.name)
            h.delete_section(sec=section)
        
    def __repr__(self):
        return "{}[{}]".format(self._name, self._gid)
    
    #### BEGIN properties
    
    @property
    def x(self):
        if isinstance(self._position,dict):
            return self._position["x"]
        
        return 0
        
    @x.setter
    def x(self, value:Real):
        if isinstance(value, Real):
            if not isinstance(self._position, dict):
                self._position = {"x":value, "y":0, "z":0, "theta":0}
                
            else:
                self._position["x"] = value
                
            self._set_position(self._position["x"], self._position["y"], self._position["z"])
        
        else:
            raise TypeError("Expecting a Real value; got %s instead" % type(value).__name__)
        
    @property
    def y(self):
        if isinstance(self._position,dict):
            return self._position["y"]
        
        return 0
        
    @y.setter
    def y(self, value:Real):
        if isinstance(value, Real):
            if not isinstance(self._position, dict):
                self._position = {"x":0, "y":value, "z":0, "theta":0}
                
            else:
                self._position["y"] = value
                
            self._set_position(self._position["x"], self._position["y"], self._position["z"])
        
        else:
            raise TypeError("Expecting a Real value; got %s instead" % type(value).__name__)
        
    @property
    def z(self):
        if isinstance(self._position,dict):
            return self._position["z"]
        
        return 0
        
    @z.setter
    def z(self, value:Real):
        if isinstance(value, Real):
            if not isinstance(self._position, dict):
                self._position = {"x":0, "y":0, "z":value, "theta":0}
                
            else:
                self._position["z"] = value
                
            self._set_position(self._position["x"], self._position["y"], self._position["z"])
        
        else:
            raise TypeError("Expecting a Real value; got %s instead" % type(value).__name__)
        
    @property
    def theta(self):
        if self._position:
            return self._position["theta"]
        
        return 0
    
    @theta.setter
    def theta(self, value:Real):
        if isinstance(value, Real):
            if not self._position:
                self._position = {"x":0, "y":0, "z":0, "theta":value}
                
            else:
                self._position["theta"] = value
                
            self._rotate(self._position["theta"])
        
    @property
    def name(self):
        return self.__class__.__name__ if self._name is None else self._name
    
    @name.setter
    def name(self, value=None):
        if isinstance(value, str) and len(value):
            self._name = value
            
        else:
            self._name = self.__class__.__name__
            
    @property
    def all(self):
        return list(self.sections.values())
    
        # NOTE: 2021-01-17 15:35:40
        # that's very nice to demonstrate wholetree() function of a nrn.Section
        # but what if the cell hasn't got a soma (or the section that is supposed
        # to encapsulate the cell body is not called "soma")
        #
        # by the way, self.soma.wholetree and self.dend.wholetree() return the 
        # very same list of sections
        #soma = getattr(self, "soma", None)
        #if isinstance(soma, nrn.Section):
            #return soma.wholetree()
        
        # NOTE: 2021-01-17 15:37:08
        # First figure out is there are any sections in this object
        #sections = list(self.sections.values())
        
        #if len(sections):
            #return section[0].wholetree()
            
    @all.setter
    def all(self, value:typing.Optional[typing.Union[tuple, list]] = None):
        """Gives write acces to 'all' property
        """
        # NOTE: 2021-02-09 11:59:02 required so that neuron._create_all_list()
        # defined in site-packages/neuron/__init__.py works
        #
        # See NOTE: 2021-02-09 11:58:19 and NOTE: 2021-02-09 11:41:02
        # print("PyNRNCell.all = ", value)
        
        self.sections = value
        
    @property
    def nSections(self):
        """Number of sections in this cell model
        """
        return len(tuple(filter(lambda x: x if isinstance(x, nrn.Section) else (), self.__dict__.values())))
    
    @property
    def sections(self):
        """Dict of nrn.Section objects in this cell
        """
        return dict(filter(lambda x: x if isinstance(x[1], nrn.Section) else (), self.__dict__.items()))
    
    @sections.setter
    def sections(self, value:typing.Optional[typing.Union[tuple, list, dict]]=None):
        """Gives write access to sections property
        
        NOTE: 2021-02-09 11:58:19
        Required because neuron._create_all_list() sets this up.
        See NOTE: 2021-02-09 11:41:02
        
        neuron._create_all_list() is python code called from within the HOC
        procedure Import3d_GUI.instantiate()
        
        You read this right: given an instance of Import3d_GUI object in python,
        you can call its instantiate method, which executes HOC code, which in 
        turn executes python code (neuron._create_all_list()).
        
        Parameters:
        ===========
        value: tuple, list, dict or None (default)
            When None, or when len(value) is zero all sections are removed from
            this cell.
            
            Otherwise:
                * when a sequence (tuple, list), its elements must be instances of
                nrn.Section
                
                * when a dict, it must map str keys to nrn.Section instances; the
                keys must be valid python identifiers
            
        
        """
        
        if value is None:# or (isinstance(value, (tuple, list, dict)) and len(value) == 0):
            self.clearSections()
            #return
            
        elif isinstance(value, (tuple, list)):
            if len(value) == 0:
                self.clearSections()
                
            elif all([isinstance(v, nrn.Section) for v in value]):
                #print("PyNRNCell.sections(sequence)")
                for section in value:
                    secname = section.name().split(".")[-1]
                    #print("secname %s = %s" % (secname, section))
                    setattr(self, secname, section)
                
        elif isinstance(value, dict):
            if len(value) == 0:
                self.clearSections()
                return 
            
            for secname, section in value.items():
                #print("secname %s  = %s" % (secname, section))
                if isinstance(section, nrn.Section):
                    setattr(self, secname, section)
            
    
    @property
    def wholetree(self):
        """Really the same thing as self.all
        """
        return self.all[0].wholetree()
    
    #### END properties
    
    def clearSections(self):
        #print("clearSections")
        sections = self.all
        for sec in sections:
            self.removeSection(sec)
        #map(self.removeSection, (sec for sec in self.__dict__ if isinstance(self.__dict__[sec], nrn.Section)))
        #for section in self.__dict__.keys() if isinstance(self.__dict__[section], nrn.Section):
            #self.removeSection(section)
    
    def showInNeuronGUI(self, mode:int=0):
        """Plots the cell in a Neuron GUI Shape window.
        
        Parameters:
        mode: int, default is 0: mode parameter to Shape.show() 
        
        """
        if isinstance(mode, int):
            if mode not in range(3):
                raise ValueError("Mode expected to be 0, 1 or 2; got %d instead" % mode)
            
        else:
            raise TypeError(f"Expecting 'mode' an int in (0,1,2); got {type(mode).__name__} instead")
            
        if self._shape_view is None:
            self._shape_view = h.Shape()
        
        self._shape_view.show(mode)
        
    def removeSection(self, section:typing.Union[nrn.Section, str]):
        """Removes a section from this cell and from the HOC interpreter object
        """
        #print("removeSection")
        if not section in self:
            return
        
        if isinstance(section, str):
            secname = section
            section = getattr(self, section)
            
        elif isinstance(section, nrn.Section):
            secname = section.name().split(".")[-1]
            
        else:
            return
        
        if section in h.allsec():
            h.delete_section(section)
            
        delattr(self, secname)
        
    def loadMorphologySWC(self, fname:str=None):
        """
        See https://neuron.yale.edu/phpBB/viewtopic.php?f=13&t=4247
        """
        # NOTE: 2021-02-09 11:41:02 
        # Fixed kernel crashing when calling Import3d_GUI.instantiate().
        #
        # This was due to Import3d_GUI.instantiate() calling the python
        # method neuron._create_all_list() defined in site-packages/neuron/__init__.py 
        #
        # Unfortunately, neuron._create_all_list() forces the 'all' attribute 
        # onto the python object passed as argument to Import3d_GUI.instantiate().
        #
        # Not a nice thing to do, IMHO.
        #
        # In the case of PyNRNCell objects, 'all' is a dynamic (hence, read-only)
        # property. This will raise exception when calling the neuron's 
        # _create_all_list(). The python kernel crash seems to be generated by 
        # raising the exception by python code executed from the top level of the
        # HOC interpreter.
        
        # The fix consists in giving write access to this property, see
        # NOTE: 2021-02-09 11:58:19 and self.all
        if not isinstance(fname, str) or len(fname.strip()) == 0:
            # NOTE: 2021-02-09 16:10:56
            # should use NEURON's own GUI API here (i.e. written in HOC), albeit 
            # acessed from our (python) side
            fc = h.File()
            fc.chooser("", "Choose SWC file", "*.swc", "Open", "Cancel", os.getcwd())
            
            if fc.chooser():
                fname = fc.getname()
        
        if not os.path.isfile(fname):
            return
        
        #print("fname", fname)
        # NOTE: 2021-02-09 16:50:26
        # template is defined in read_swc.hoc; loaded (from hoc side) indirectly
        # through h.load_file("import3d.hoc")
        swc_reader = h.Import3d_SWC_read()  
        swc_reader.input(fname)
        swc_importer = h.Import3d_GUI(swc_reader, 0)    # see NOTE: 2021-02-09 16:50:26
                                                        # template defined in 
                                                        # import3d_gui.hoc
        swc_importer.instantiate(self)
        
        for sec in h.allsec():
            if sec.cell() is self:
                sname = sec.name().split(".")[-1].replace("[", "_").strip("]")
                setattr(self, sname, sec)
        
    #def addSection(self, name:str, L:Real, 
                   #/,
                   #nseg:typing.Optional[int]=None,
                   #diam:typing.Union[Real, tuple, list]= 1, 
                   #cm:typing.Optional[typing.Union[Real, tuple, list]]=None,
                   #diam_interp: typing.Optional[typing.Union[tuple, list]]=None,
                   #cm_interp: typing.Optional[typing.Union[tuple, list]]=None,
                   #Ra:typing.Optional[Real]=None,
                   #freq:typing.Optional[Real]=None,
                   #d_lambda:typing.Optional[Real]=None,
                   #parent:typing.Optional[nrn.Section]=None,
                   #parent_pos:typing.Optional[Real]=None,
                   #orientation:typing.Optional[int]=None) -> nrn.Section:
        #"""
        #cm: Real scalar, or a sequence (tuple, list) of Real scalars.
            #The membrane float, sequence (tuple, list) of float; optional; 
            #When None, the section gets NEURON's default value of 1
            
            #When a float scalar, it represents the membrane capacitance for the
            #entire section.
            
            #When a sequence of floats, this is used to interpolate it along the 
            #x coordinates of the section; see also 'cm_interp', below
            
            #NOTE: This is a range variable
            
        #cm_interp: sequence of minimum two floats, or None
            #When None and cm is a sequence, the membrane capacitance of the 
            #section's compartments will be interpolated on [0,1] from 
            #cm[0] to cm[-1].
            
            #Otherwise, cm must be a sequence with 
                    #len(cm) == len(cm_interp)
            #Used in this method:
            
            #diam: diameter (um)
            #cm  : specific membrane capacitance (uf/cm**2)
            
            #Example of range variables NOT specified/used in this method:
            
            #v   : membrane potential (mV)
            #ina : sodium current (mA/cm**2)
            #nai : internal sodium concentration (mM)
            #n_hh: Hodgkin-Huxley potassium conductance gating variable (dimensionless)
        #"""
                   
    #def addSection(self, name:str, /, 
                   #L:typing.Optional[Real]=None,
                   #nseg:typing.Optional[int] = None,
                   #diam:typing.Union[Real, tuple, list] = 1, 
                   #diam_interp: typing.Optional[typing.Union[tuple, list]]=None,
                   #Ra:typing.Optional[Real]=None,
                   #cm:typing.Optional[typing.Union[Real, tuple, list]]=None,
                   #cm_interp: typing.Optional[typing.Union[tuple, list]]=None,
                   #freq:typing.Optional[Real]=None,
                   #d_lambda:typing.Optional[Real]=None,
                   #parent:typing.Optional[nrn.Section]=None,
                   #parent_pos:typing.Optional[Real]=None,
                   #orientation:typing.Optional[int]=None) -> nrn.Section:
        
    def connectSections(self, section:nrn.Section, parent:nrn.Section, 
                        parent_pos:typing.Optional[Real]=None, 
                        orientation:typing.Optional[int]=None) -> None:
        
        if not isinstance(section, nrn.Section):
            raise TypeError(f"'section' expected to be a nrn.Section; got {type(section).__name__} instead")
        
        if section not in self or section.cell() is not self:
            raise ValueError(f"The specified section {section.name()} does not belong to this cell")
        
        if not isinstance(parent, nrn.Section):
            raise TypeError(f"'parent' expected to be a nrn.Section; got {type(parent).__name__} instead")
        
        if parent not in self or parent.cell() is not self:
            raise ValueError(f"The specified parent section {parent.name()} does not belong to this cell")
        
        if section is parent or section.same(parent):
            raise ValueError("Cannot connect a section to itself!")
        
        if isinstance(parent_pos, Real):
            if isinstance(orientation, int):
                if orientation not in (0,1):
                    raise ValueError("When specified, orientation must be 0 (zero) or 1 (one); got %d instead" % orientation)
                
                section.connect(parent(parent_pos), orientation)
                
            else:
                section.connect(parent(parent_pos))
                
        elif isinstance(orientation, int):
            if orientation not in (0,1):
                raise ValueError("When specified, orientation must be 0 (zero) or 1 (one); got %d instead" % orientation)

            section.connect(parent, orientation)

        else:
            section.connect(parent)
        
    def addSection(self, name:str, /, 
                   nseg:[int] = 1,
                   L:typing.Optional[Real]=None,
                   diam:typing.Union[Real, tuple, list] = 1) -> nrn.Section:
        """Add a section to this cell.
        
        The section is created using stylized geometry (L, nseg, diam) with
        'diam' being set the same across all 'nseg' discretization segments (or 
        compartments), then added as an instance attribute to the cell.
        
        Once created in this way, the section's geometry and discretization can
        be further refined by calling self.refineGeom(sec), ideally AFTER setting
        new values for the section's Ra and cm attributes (by default, the newly
        created section has the NEURON's default values for Ra: 35.4 and )
        
        A cell must have at least one section - usually called "soma" but one is
        free to use any name as long as it is unique.
        
        This method creates and returns a nrn.Section object (a "section"). The
        section is also assigned to an attribute of this PyNRNCell instance, 
        that is named after the section (hence section names must be unique).
        
        The newly created section can be connected to another existing section
        in this cell, which is identified by its name. By default, the 
        the 0 end of the new section is connected to the 1 end of the parent 
        section, but this can also be configured.
        
        The created section has a stylized geometry specified by the 'section'
        variables 'L' and 'nseg', and by the range variable 'diam' (see
        https://nrn.readthedocs.io/en/8.0.0/python/modelspec/programmatic/topology/geometry.html#geometry-geometry)
        
        The parameters represent 'section', 'range', or discretization variables 
        (see Chapter 5 in Hines & Carnevale The NEURON Book). 
        
        Briefly, 'section' variables have constant value for the entire section, 
        regardless of how many segments (or compartments) the section has. 
        
        In contrast, 'range' variables are continuous functions of position 
        throughout the section. The position is the normalized distance along 
        the centroid of the section, a.k.a the "range" or "arc length", and 
        varies linearly from 0 at one end to 1 at the other end.

        With the exception of 'Ra' and 'cm' which specify biophysical properties
        all other parameters relate to the geometry of the section, and its
        discretization.
        
        The section geometry can be specified in a stylized manner (as a chain 
        of cylindrical segments or compartments) based on the 'L', 'diam' and 
        'nseg' parameters, or via the '3D method' as a sequence of at least two 
        (x,y,z,diam) tuples.
        
        Positional-only parameters:
        ===========================
        name:str. The name of the section; it must be a valid Python identifier 
            and not present in this cell's sections.
            
        Named parameters:
        =================
        L: scalar (Real). Optional, default is 1. 
            Section length (in um); this is a section variable.
        
        nseg: int >= 1, ideally an odd value; optional, default is None. 
            The discretization parameter i.e., the number of 'segments' (or 
            'compartments') in the section; this is a section variable.
            
            To use PyNRNCell default value (51) pass PyNRNCell.default_nseg 
            explicitly, here.
            
        diam: one of:
            1) Real scalar > 0 : the diameter of the section (in µm); optional,
            the default is NEURON's default (500)
            
            In this case the section will have the same diameter along all its
            segments (considered as a right cylinder).
            
            2) a sequence (tuple, list) of two strictly positive Real scalars
            (i.e, > 0). The diameters of the section's segments at their 'x' 
            coordinate will be linearly interpolated between these two values.
            
            3) a nested sequence of pairs of Real scalars > 0; the number of 
            pairs must be equal to that of the section's 'nseg' variable. The 
            diameter of each segment will be interpolated between the values in 
            the pair, in the order given here.
            
            In this case the 'nseg' parameter MUST be given explicitly.
            
            NOTE: The diameters of the section's segments can be re-adjusted by
            interpolation once the section's nseg has been refined using the 
            d_lambda rule.
            
            In cases (2) and (3) the interpolation occurs on the interval [0., 1.]
            unless specified via the 'diam_interp' parameter, below.
            
        diam_interp: sequence or nested sequence that contains real scalars (at
            the deepest nesting level) and with shape that is identical to that 
            of 'diam' (cases 2 and 3, see above). The scalars must take values
            in the closed interval [0., 1.]
            
        Ra  : Real scalar >= 0. The cytoplasmic (axial) resistivity (Ohm·cm); 
            optional, default is 35.4 Ohm·cm; section variable.
            
        cm: Real scalar, or a sequence with structure similar to that of 'diam'
            (see above). Optional the default is None.
            
            The specific membrane capacitance (µF/cm²).
            
            When None, the section gets NEURON's default value of 1
            
            When a float scalar, it represents the membrane capacitance for the
            entire section.
            
            NOTE: As for diam, cm can be finely set by interpolation on each of
            the section's segments AFTER the section's 'nseg' value has been set
            here.
            
            NOTE: This is a range variable
            
        cm_interp: as diam_interp, above; used for interpolating the 'cm' for
            each segment in the section.
            
        * Discretization parameters:
        
        freq: float scalar (optional, default is None). The frequency (in Hz) 
            at which the section's AC length constant (λf) is calculated using 
            the 'lambda_f' function, defined in this module.
            
            This is used together with 'd_lambda' below, to calculate an 
            'optimal' discretization value (the section 'nseg' variable), only
            when 'nseg' parameter is not specified as a positive int.
            
            Here, 'optimal' means that the section segments are NOT longer than
            d_lambda × λf at the value of freq.
            
            When not specified (i.e. 'freq' is None), the NEURON's recommended 
            value of 100 Hz will be used.
            
            CAUTION: This calculation relies on the section's 'Ra' and 'cm' 
            properties. So, when neither Ra nor cm are specified, the NEURON's
            default values Ra = 35.4 and cm = 1 will be used. In particular,
            when 'cm' is specified as a float scalar, it will be used to
            calculate 'nseg'. This might appear to create a chicken-egg problem,
            as the 'cm' is a range variable (hence it MAY vary with the number
            of section compartments)
            
            To change a section's nseg according to the d_lambda rule AFTER the 
            section was created, use geomNseg(...) method.
            
        d_lambda: float scalar with values in [0., 1.]. The fraction of the AC
            length constant at 'freq' frequency (λf); (optional, default is None).
            
            This is used together with 'freq' (see above) to calculate an
            'optimal' discretization value (the section 'nseg' variable) , only 
            when 'nseg' is not specified as a positive int.
            
            When not specified (i.e. when d_lambda is None) the NEURON's 
            recommended value of 0.1 will be used.
            
        * Connectivity parameters:
                    
        parent: nrn.Section; optional (default is None)
            When present, the new section will be connected to 'parent'.
            Parent must be a section that already exists in the cell and must be
            a distinct object from the newly created section.
        
        parent_pos: float, between 0 and 1 (optional default is None).
            When specified, this indicates the parent's segment where the new 
            section will be connected.
            
            When None (default) the new section will be connected as the end (1)
            of the parent.
            
        orientation: float, between 0 and 1 (optional, default is 0)
            When specified, this indicates which segment of section is connected
            to the parent.
            
            When None (the default) the section's segment 0 will be connected.
            
        See also the documentation for the nrn.Section.connect(...) method.
        
        * * * 
            

        NOTE: This method calls h.Section(...) to create a HOC section.
        
        Sections created directly in h will optionally belong to a cell, if a 
        'cell' parameter was passsed to the constructor in h.
        
        In either case, once the section has been constructed, HOC does not allow
        setting or changing the cell to which the section belongs.
        
        Therefore, from the HOC interpreter's point of view, sections CANNOT BE 
        "RELOCATED" from a  cell to another, and CANNOT be "added" to a cell 
        AFTER they have been constructed.
        
        Currently, no mechanism is implemented to prevent forcefully setting a 
        random section as an attribute of the cell object. However, doing so will
        mess up the semantics of the model:
        
        * if a section belonging to a cell was "added" to another cell, HOC will
        still interpret the section as being as part of the original cell, which
        may lead to contrived models where a section of a cell is connected to 
        sections of another cell.
        
        * if a section with no cell (section.cell() is None -> True) was "added"
        to another cell, HOC would still interpret it as a section without a cell.
        
        NOTE: 2021-01-23 00:52:17
        In the stylized specification, the shape model used for a section is a 
        sequence of right circular cylinders of length, L/nseg, with diameter 
        given by the diam range variable at the center of each segment. 
        
        The area of a segment is:
        
                PI * diam * L / nseg (micron2) 
        
        and the half-segment axial resistance is:
        
                .01 * sec.Ra * (L / 2 / sec.nseg) / (PI * (seg.diam / 2)^2). 
                
        The .01 factor is necessary to convert ohm-cm micron/micron2 to MegOhms. 
        
        Ends of cylinders are not counted in the area and, in fact, the areas are
        very close to those of truncated cones as long as the diameter does not 
        change too much.
            
        """
        # TODO: 2022-02-04 22:58:22 methods for:
        # a) refining the section's 'nseg' using the d_lambda rule AFTER section creation
        # b) applying interpolated diam and cm, once the nseg has been set
        # FIXME: move the interpolation code out of this method -> let this 
        # method create a simple stylized section, then use new methods in (a) 
        # and (b) to refine.
        
        if not isinstance(name, str):
            raise TypeError(f"Expecting a str for 'name' parameter; got {type(name).__name__} instead")
    
        if len(name.strip()) == 0:
            raise ValueError("Cannot accept empty section names")
            return
        
        if name in self.sections:
            raise ValueError(f"A section named {name} already exists in {self.__repr__()}")
        
        if hasattr(self, name):
            item = "A section" if isinstance(getattr(self, name), nrn.Section) else "An attribute"
            raise ValueError(f"{item} named {name} already exists")
        
        # NOTE: 2021-02-05 23:01:47
        # This call adds the section to the global HOC interpreter h, making
        # the section visible when calling h.topology(); therefore if anything
        # So if anything goes wrong after the section's initialization we might
        # be left with a dangling reference
        #
        
        # NOTE: 2022-02-04 09:42:08
        # This will have the NEURON's default values for nseg (1), L (100.0),
        # diam (500.0), Ra (35.4) and cm (1.0); i.e., it will have a single
        # right cylinder compartment with the default diam, L, Ra and cm.
        section = h.Section(name=name, cell=self)
        #section = sections.ExtendedSection(name=name, cell=self)
        
        if isinstance(L, Real) and L > 0:
            section.L = L
        else:
            h.delete_section(sec=section)
            raise ValueError(f"'L' expected to be a strictly positive scalar; got {L} instead")
        
        if isinstance(diam, Real) and diam > 0:
            section.diam = diam
        else:
            h.delete_section(sec = section)
            raise ValueError(f"'diam' expected to be a strictly positive scalar; got {diam} instead")
                
        #if isinstance(Ra, float) and Ra > 0:
            #section.Ra = Ra
        #else:
            #raise ValueError(f"'L' expected to be a strictly positive scalar; got {L} instead")
            
        #if isinstance(cm, float) and cm > 0:
            ## if cm was given as a positive float scalar, use it to calculate
            ## nseg; else leave the section.cm as the NEURON's default of 1
            ## and interpolate later over nseg (if given)
            #section.cm = cm 
        #else:
            #raise ValueError(f"'cm' expected to be a strictly positive scalar; got {cm} instead")
            
        if isinstance(nseg, int) and nseg >= 1:
            # to use PyNRNCell default pass PyNRNCell.default_nseg explicitly
            section.nseg = nseg
        else:
            h.delete_section(sec=section)
            raise ValueError(f"'nseg' must be an int >= 1; got {nseg} instead")
            
        # NOTE: 2022-01-30 16:56:00
        # self gains 'name' as attribute bound to the section
        setattr(self, name, section)
        #h.define_shape()
        
        # NOTE: section.parentseg() returns the segment of the parent section to 
        # which this section is connected; to retrieve the parent section itself
        # call 'section.parentseg().sec'
        
        return section
        
        ## 2. OR use the d_lambda rule with 'freq' and 'd_lambda' parameters
        ## to calculate the AC length constant for given freq (λf, See The NEURON
        ## book), then calculate the 'optimal' nseg; reasonable values for freq
        ## is 100.
        #else:
            #if not isinstance(freq, Real) or freq <=  0:
                ## is 'freq' was given as positive float scalar then use it to
                ## calculate nseg; else use the NEURON's recommended value of
                ## 100  Hz
                #freq = 100.
                
            #if not isinstance(d_lambda, Real) or d_lambda <= 0:
                ## NOTE: 2022-02-04 11:28:02
                ## d_lambda = 0 will cause +Inf in lambda_f !
                #d_lambda = self.d_lambda # the default of 0.1
                
                
            ##print(f"section.n3d: {section.n3d()}; h.n3d: {h.n3d(sec=section)}")
                
            ## now, go ahead and calculate an 'optimal' nseg
            #nseg = geomNseg(section, freq, d_lambda)
            ##print(f"calculated nseg: {nseg}")
            #section.nseg = nseg
            
        
        ## set up section's diameter - this is a range variable, so we need 
        ## section.nseg to have been set already
        #if isinstance(diam, Real): # a constant diameter
            ## just call simply this below; this applies diam to all segments of
            ## 'section'
            #section.diam = diam
                
        #elif isinstance(diam, (tuple, list)):
            #if all(isinstance(v, Real) and v > 0 for v in diam):
                #if len(diam) != 2:
                    #raise ValueError(f"When a sequence of scalars, diam must have exactly two elements; got {len(diam)} elements instead")
                
                #if diam_interp is None:
                    #for segment in section.allseg(): # also iterates through ends
                        #segment.diam = np.interp(segment.x, [0., 1.], diam)
                        
                #elif isinstance(diam_interp, (tuple, list)):
                    #if len(diam_interp) != 2:
                        #raise ValueError(f"For a 'diam' sequence of two scalars, 'diam_interp', when not None, it must have two elements; got {len(diam_interp)} elements instead")
                    
                    #if all(isinstance(v, Real) and v >= 0 and v <= 1 for v in diam_interp):
                        #for segment in section.allseg(): # also iterates through ends
                            #segment.diam = np.interp(segment.x, diam_interp, diam)
                    #else:
                        #raise ValueError("For a 'diam' sequence of two scalars, 'diam_interp', when not None, it must have Real scalar elements")
                        
                #else:
                    #raise ValueError("Incorrect diam_interp sprcified; expecting None or a sequence of two Real")
                        
            #elif all(isinstance(v, (tuple, list)) and len(v) == 2 and all(isinstance(v_, Real) and v_ > 0 for v_ in v) for v in diam):
                #if len(diam) != section.nseg:
                    #raise ValueError(f"When 'diam' is given as a nested sequence, it must have as many elements as there are segments in the section ({section.nseg}); got {len(diam)} elements instead")
                
                #if diam_interp is None:
                    #for k, segment in enumerate(section.allseg()): # also iterates through ends
                        #segment.diam = np.interp(segment.x, [0., 1.], diam[k])
                        
                #elif isinstance(diam_interp, (tuple, list)):
                    #if len(diam_interp) != len(diam):
                        #raise ValueError(f"'diam_interp should have {len(diam)} elements; got {len(diam_interp)} elements instead")
                    
                    #if all(isinstance(v, (tuple, list)) and len(v) ==2 and all(isinstance(v_, Real) and v_ >= 0 and v_ <= 1 for v_ in v) for v in diam_interp):
                        #for k, segment in enumerate(section.allseg()):
                            #segment.diam = np.interp(seg.x, diap_interp[k], diam[k])
                        
                    #else:
                        #raise ValueError("When 'diam' is a nested sequence, 'diam_interp' should be a similar nested sequence of Real scalars")
                    
                #else:
                    #raise ValueError(f"Incorrect 'diam_interp' specification; expecting a sequence of {len(diam)} real scalar pairs")
                    
                    
        ## set up section's cm; note that if 'cm' was given as a scalar, it had
        ## already been assigned to section's cm; regardless of how nseg was 
        ## assigned, we need do nothing further; however, if 'cm' was passed as
        ## a sequence for interpolation, when we need to set it up now.
        #if isinstance(cm, (tuple, list)):
            #if not all([isinstance(v, Real) for v in cm]):
                #raise TypeError("Expecting a sequence of scalars for 'cm'")
            
            #if len(cm) < 2:
                #raise ValueError("When given as a sequence, 'cm' must have at least two elements")
              
            #if cm_interp is None:
                #for segment in section.allseg(): # also iterates through ends
                    #segment.cm = np.interp(segment.x, [0., 1.], cm)
                
            #elif isinstance(cm_interp, (tuple, list)):
                #if len(cm_interp) != len(cm):
                    #raise ValueError("lengths of 'cm' and 'cm_interp' sequences must be identical")
                
                #if not all([isinstance(v, Real) for v in cm_interp]):
                    #raise TypeError("'cm_interp' must contain Real scalars")
                
                #if not all([v >= 0 and v <=1 for v in cm_interp]):
                    #raise ValueError("'cm_interp' values must all be in the interval [0., 1.]")
                
                #for segment in section.allseg(): # also iterates through ends
                    #segment.cm = np.interp(segment.x, cm_interp, cm)
                    
            #else:
                #raise TypeError(f"'cm_interp' expected to be None, or a sequence (tuple, lits) of real scalars; got {type(cm_interp).__name__} instead.")
                        
                    
        # NOTE: 2022-02-04 16:34:20
        # Finally, deal with connectivity
    
    #def geomNseg(self, section:nrn.Section, freq:Real, 
                 #d_lambda:typing.Optional[Real]=None) -> int:
        #"""Calculates nseg according to d-lambda rule.
        
        #Parameters:
        #===========
        #section: nrn.Section. The section specified here must belong to this 
                #cell (otherwise, raises KeyError)
                
        #freq: Real: AC frequency for which nseg is to be calculated
        
        #d_lambda: Real (optional, default is 0.1). Values must be in the 
            #semi-open interval (0., 1.]
        
        #""" 
        #if not isinstance(section, nrn.Section):
            #raise TypeError("Expecting a nrn.Section; got %s instead" % type(section).__name__)
        
        #if section not in self.all:
            #raise KeyError("Section %s not found in %s" % (section, self))
        
        #if not isinstance(d_lambda, Real):
            #d_lambda = self.d_lambda
            
        #elif d_lambda <= 0 or d_lambda > 1:
            #raise ValueError(f"d_lambda expected to be a scalar real on the semi-open interval (0., 1.]; got {d_lambda} instead")
            
        #return geomNseg(section, freq, d_lambda)

    def getSection(self, name):
        if not isinstance(name, str):
            raise TypeError("Expecting a str; got %s instead" % type(name).__name__)
        
        ret = [(sn, s) for (sn, s) in self.sections.items() if sn.split(".")[-1] == name]
        
        if len(ret):
            if len(ret) > 1:
                raise RuntimeError("There are multiple sections with the same name %s" % name)
            
            return ret[0]
        
    #def _setup_morphology(self, nseg:typing.Optional[int] = None):
        #"""To override in subclass
        #"""
        #if len(self.all) == 0:
            #print("The cell has no sections (e.g., soma, dendrites, axon, etc.).")
            #print("To add sections to this cell call its 'addSection(...)' method, or its 'loadMorphologySWC(swc_file_name)' method to load a neuron morphology from a SWC file.")
            
    def _setup_biophysics(self):
        """To override in subclass
        """
        pass
    
    def __verify_section__(self, section:nrn.Section) -> bool:
        """Check argument is a nrn.Section and that belongs to this cell
        """
        if not isinstance(section, nrn.Section):
            warnings.warn("Expecting a nrn.Section; got %s instead" % type(section).__name__)
            return False
            #raise TypeError("Expecting a nrn.Section; got %s instead" % type(section).__name__)
        
        if section not in self.sections:
            secname = section.name().split(".")[-1]
            warnings.warn("%s is not present in this cell" % secname)
            return False
            #raise ValueError("%s is not present in this cell" % secname)
            
        return True
    
    def __contains__(self, section:typing.Union[nrn.Section, str]):
        """Implements the idiom "section in cell -> True/False "
        """
        if isinstance(section, str):
            return hasattr(self, section) and isinstance(getattr(self, section, None), nrn.Section)
        
        elif isinstance(section, nrn.Section):
            secname = section.name().split(".")[-1]
            return hasattr(self, secname) and isinstance(getattr(self, secname, None), nrn.Section)
        
        else:
            return False
        
    
    def _set_position(self, x, y, z):
        """Place cell at (x,y,z).
        This implies its sections have 3D points (n3d() != 0), which happens
        AFTER calling h.define_shape().
        """
        for section in self.all:
            for i in range(section.n3d()):
                section.pt3dchange(i,
                                   x - self._x + section.x3d(i),
                                   y - self._y + section.y3d(i),
                                   z - self._z + section.z3d(i),
                                   section.diam3d(i))
        self._x, self._y, self._z = x, y, z
        
    def _rotate(self, theta):
        """Rotate cell about the Z axis.
        This implies its sections have 3D points (n3d() != 0), which happens
        AFTER calling h.define_shape().
        """
        for section in self.all:
            for i in range(section.n3d()):
                x = section.x3d(i)
                y = section.y3d(i)
                c = h.cos(theta)
                s = h.sin(theta)
                xprime = x * c - y * s
                yprime = x * s + y * c
                section.pt3dchange(i, 
                                   xprime, 
                                   yprime, 
                                   section.x3d(i), 
                                   section.diam3d(i))
        
    
    def insertMechanism(self, section:nrn.Section, mechanism:str, **kwargs):
        if not self.__verify_section__(section):
            return 
        
        section.insert(mechanism)
        
        # NOTE: 2021-01-22 12:40:03
        # this is wrong: cannot assign to a function call
        
        #for segment in section:
            #for item in kwargs.items:
                #eval("segment.%s.%s"% (mechanism,item[0]))=item[1]
        
    def setRa(self, section:nrn.Section, value):
        if not self.__verify_section__(section):
            return 
        section.Ra = value
        
    def setCm(self, section:nrn.Section, value):
        if not self.__verify_section__(section):
            return 
        section.cm = value
        
    def setNseg(self, section: typing.Optional[nrn.Section]=None,
                value:typing.Optional[int]=None):
        """Set the number of compartments for a stylized section.
        
        Named parameters:
        ------------------
        
        section: a nrn.Section (optional, default is None)
            When None, the nseg attribute wil be (re)set for all sections in the
            cell.
            
            When section is a nrn.Section that is NOT found in this cell the 
            the function does nothing.
        
        value:int or None (default)
            When None, all sections get nseg attribute reset to the class default.
            This is the inherited one (PyNRNCell.default_nseg = 51) unless overridden
            in a subclass.
            
            It is recommended that sections shoudl have an odd number of segments
            (or compartments).
        
        """
        if not isinstance(value, int):
            value = self.default_nseg
            
        #else:
            #if value % 2 == 0:
                #value += 1
                
        if isinstance(section, nrn.Section) and section in self.all:
            section.nseg = value
            
        else:
            for section in self.all:
                section.nseg = value
    
    def segmentsStats(self, section:typing.Union[nrn.Section, str]) -> typing.Optional[pd.DataFrame]:
        """Returns the Diameter, Area and Axial resistance of each segment in the section.
        
        Parameters:
        ===========
        section: nrn.Section or str
            When a nrn.Section, it must be present in this cell.
            When a str it must be the valid name of a section defined in the cell.
            
        Returns:
        =========
        
        A pandas.DataFrame object with the following columns:
        
        Segment, Diam, Area, Ri
        
        NOTE: A segment of a section is a modelling compartment (hence the terms
        segment and compartment are synonyms)
        
        """
        if not section in self:
            return
        
        if isinstance(section, str) and hasattr(self, section):
            section = getattr(self, section)
            if not isinstance(section, nrn.Section):
                raise KeyError("%s has no section named %s" % (self, section.name))
            
        if isinstance(section, str) and hasattr(self, section):
            section = getattr(self, section)
            if not isinstance(section, nrn.Section):
                raise KeyError("%s has no section named %s" % (self, section.name))
            
        #columns = ["Segment x", "Segment diam (um)", "Segment area (um^2)", "Segment axial resistance (MOhm)"]
        if isinstance(section, str):
            section = getattr(self, section, None)
            if not isinstance(section, nrn.Section):
                raise KeyError("%s has no section named %s" % (self, section.name))
        columns = ["Segment", "Diam", "Area", "Ri"]
        
        arr = np.array([(seg.x, seg.diam, seg.area(), seg.ri()) for seg in section.allseg()])
        
        return pd.DataFrame(data=arr, columns = columns)
            
    def section3DPoints(self, section:typing.Union[nrn.Section, str],
                        asDataFrame:typing.Optional[bool]=False) -> typing.Optional[typing.Union[np.ndarray, pd.DataFrame]]:
        """Returns 3D shape parameters of the section (when defined).
        
        If section.n3d() == 0 returns None
        """
        
        if not section in self:
            return
        
        if isinstance(section, str):
            sec = getattr(self, section, None)
            if not sec:
                raise AttributeError(f"This cell has no section named {section}")
            
            section = sec
            
        elif isinstance(section, nrn.Section):
            if not section in self or section.cell() is not self:
                raise AttributeError(f"The section {section.name()} does not belong to this cell")
            
        else:
            raise TypeError(f"Expecting a nrn.Section or a str (name of existing section); got {type(section).__name__} instead")

        return section3DPoints(section, asDataFrame=asDataFrame)
        
class BallAndStick(PyNRNCell):
    def __init__(self, gid, **kwargs):
        if "name" not in kwargs:
            kwargs["name"] = "BallAndStick"
        super().__init__(gid, **kwargs)
        
    def _setup_morphology(self, nseg:typing.Optional[int]=1):
        self.soma = self.addSection(sec="soma", diam=13, L=13, Ra=100, nseg=nseg)
        self.dend = self.addSection(sec="dend", diam=1, L=200, Ra=100, nseg=nseg, parent=self.soma)
        
    def _setup_biophysics(self):
        for section in self.all:
            section.Ra = 100
            section.cm = 1
            
class Example3DCell(PyNRNCell):
    def __init__(self, gid, **kwargs):
        if "name" not in kwargs:
            kwargs["name"] = "BallAndStick"
        super().__init__(gid, **kwargs)
        
    def _setup_morphology(self, nseg=20):
        for name in ["a", "b", "c", "d", "e"]:
            if name == "a":
                self.addSection(name, L=100, nseg=nseg, diam = [10, 40])
            else:
                self.addSection(name, L=100, nseg=nseg, diam = [10, 40], parent="a")
    
            
def remove_sections(cell:typing.Optional[PyNRNCell]=None):
    """Removes sections from the HOC interpreter workspace.
    
    The "clean-up" can be limited to the sections of a PyNRNCell instance; 
    otherwise, all the sections are removed from the HOC workspace.
    
    
    
    """
    if cell is None:
        for sec in h.allsec():
            h.delete_section(sec=sec)
            
    elif isinstance(cell, PyNRNCell):
        for sec in h.allsec():
            if sec in cell:
                cell.removeSection(sec)
                
    else:
        raise TypeError(f"A PyNRNCell instance or None was expected; got {type(cell).__name__} instead")

def lambda_f(freq:Real, section:nrn.Section) -> float:
    """Calculates the section's AC length constant at a given frequency (λf).
    See https://neuron.yale.edu/neuron/static/docs/d_lambda/d_lambda.html
    
    The corresponding HOC function 'lambda_f' is supplied by NEURON in the file
    'share/nrn/lib/hoc/stdlib.hoc'
    
    To determine an nseg value such that the segments of a section are no longer
    than d_lambda × AC length constant at a given frequency 'freq', use the 
    formula:
    
        nseg = int((L / (d_lambda * lambda_f(freq)) + 0.999) / 2) * 2 + 1
    
    where:
        L: float        = section.L
        d_lambda: float = 0.1 (fraction of λ100)
        freq: float     = frequency (see below)
        
    WARNING: Requires that the section already has values assigned to 'Ra' (the 
    axial resistivity, in Ohm·cm) and 'cm' (specific membrane capacitance, in 
    µF/cm²)
    
    Parameters:
    ----------
    freq: Real  = Frequency for which the AC length constant is calculated.
    section: either a nrn.Section with L and homogeneous diam, Ra and cm, and
        defined 3D geometry (either h.define_shape() was called, or the section's
        geoometry was defined from vectors of x, y, z, d values from the outset)
    
    """
    if not isinstance(section, nrn.Section):
        raise TypeError(f"Expecting a nrn.Section for 'section'; got {type(section).__name__} instead")

    if section.cm == 0:
        return 1e10
    
    if section.n3d() < 2:
        return 1e5 * np.sqrt(section.diam / (4*np.pi*freq*section.Ra*section.cm))
    
    else:
        x1 = section.arc3d(0)
        d1 = section.diam3d(0)
        lam = 0
        for i in range(1, section.n3d()):
            if d1 == 0:
                raise RuntimeError(f"Diameter for the 3D point {i-1} of {section.name} is 0")
            x2 = section.arc3d(i)
            d2 = section.diam3d(i)
            lam += (x2-x1) / np.sqrt(d1+d2)
            x1 = x2
            d1 = d2
            
        lam *= np.sqrt(2) * 1e-5 * np.sqrt(4*np.pi*freq*section.Ra*section(0.5).cm)
        #lam *= np.sqrt(2) * 1e-5 * np.sqrt(4*h.PI*freq*section.Ra*section(0.5).cm)
        
        return section.L/lam
    
def geomNseg(section:nrn.Section, freq:Real=100, 
                d_lambda:typing.Optional[Real]=0.1) -> int:
    """Calculates nseg according to d-lambda rule.
    
    Parameters:
    ===========
    section: nrn.Section
        NOTE: The section must have a defined 3D shape for this to work; if the
        section was created using the stylized method (by specifying L and diam)
        then 
            
    freq: Real: AC frequency for which nseg is to be calculated
    
    d_lambda: Real (optional, default is 0.1)
    
    """ 
    if not isinstance(d_lambda, Real) or d_lambda <= 0 or d_lambda > 1:
        d_lambda = PyNRNCell.d_lambda
        
    if isinstance(section, nrn.Section):
        return int( (section.L/(d_lambda * lambda_f(freq, section)) + 0.999) /2 ) * 2 + 1
        
    else:
        raise TypeError("Expecting a nrn.Section; got %s instead" % type(section).__name__)

def setRaCm(section:nrn.Section, Ra:float=None, cm:float=None):
    """Sets the very basic biophysics for a section: Ra and cm.
    
    """
    if not isinstance(section, nrn.Section):
        raise TypeError(f"Expecting a nrn.Section for 'section'; got {type(section).__name__} instead")
    
    if isinstance(Ra, float):
        section.Ra = Ra
        
    if isinstance(cm, float):
        section.cm = cm
        
def stub3d(section:nrn.Section):
    """Equivalent of h.define_shape() for one section.
    While h.define_shape generates a 3D geometry for all sections in the HOC,
    this function emulates this behaviour for a single section. It is best called
    for an individual section AFTER the seciton has been constructed using the
    stylized geometry strategy (L, diam, nseg)
    
    """
    if not isinstance(section, nrn.Section):
        raise TypeError(f"Expecting a nrn.Section; got {type(section).__name__} instead")
    
    if section.n3d():
        raise ValueError(f"The section already has a 3D geometry, with {section.n3d()} 3D points")
    
    xvec = np.array([0, section.L/2, section.L])
    yvec = np.full_like(xvec, fill_value=0)
    zvec = np.full_like(xvec, fill_value=0)
    dvec = np.full_like(xvec, fill_value=section.diam)
    
    h.pt3dadd(h.Vector(xvec),h.Vector(yvec),h.Vector(zvec),h.Vector(dvec), sec=section)
    
    
def section3DPoints(section:nrn.Section,
                    asDataFrame:typing.Optional[bool]=False) -> typing.Optional[typing.Union[np.ndarray, pd.DataFrame]]:
    
    if not isinstance(section, nrn.Section):
        raise TypeError(f"Expecting a nrn.Section; got {type(section).__name__} instead")
    
    arr = np.array([(i, section.x3d(i), section.y3d(i), section.z3d(i), section.diam3d(i)) for i in range(section.n3d())])
    
    if asDataFrame and arr.size:
        columns = ["Point", "x3d", "y3d", "z3d", "diam3d"]
        return pd.DataFrame(data=arr, columns = columns)
    
    return arr
    
    
def sectionParent(section:nrn.Section) -> typing.Optional[typing.Union[nrn.Section, PyNRNCell]]:
    """Returns the parent section (if it exists) or the owner (if is exists).
    
    To retrieve the parent segment of the section (if it exists) just call
    section.parentseg()
    
    """
    if not isinstance(section, nrn.Section):
        raise TypeError(f"Expected a nrn.Section; got {type(section).__name__} instead")
    
    seg = section.parentseg()
    if seg:
        return seg.sec
    
    return section.cell()
    

__all__ = ["PyNRNCell", "BallAndStick", "remove_all_sections", "lambda_f", "geomNseg"]
#__all__ = ["PyNRNCell", "BallAndStick", "Ring"]
