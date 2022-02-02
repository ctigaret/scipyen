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
from neuron import h, rxd, nrn # gui should be imported via Scipyen
from neuron.units import ms, mV

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
        self._sections_ = list()
        position = kwargs.pop("position", None)
        
        self._position = dict((k,0.) for k in ("x", "y", "z", "theta"))
        
        if isinstance(position, dict):
            # make sure mandatory fields are here
            for k in self._position:
                val = position.get(k, 0.)
                self._position[k] = val if isinstance(val, Real) else 0.
                
        name = kwargs.pop("name", None)
        nseg = kwargs.pop("nseg", self.default_nseg)
        
        if isinstance(nseg, int) and nseg > 0:
            if nseg % 2 == 0:
                nseg+=1
        else:
            nseg = self.default_nseg
            
        self._name = name if (isinstance(name, str) and len(name)) else self.__class__.__name__
        
        for secname, secdict in kwargs.items():
            # NOTE: 2022-01-30 17:00:26:
            # make sure we give this section a name
            sname = secdict.get("name", None) 
            if not isinstance(sname, str) or len(sname.strip()) == 0:
                secdict["name"] = secname
                
            self.addSection(**secdict)
        
        self._setup_morphology()
        
        h.define_shape()
        
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
        
    #def __del__(self):
        #"""Remove all pointers to sections that belong to this cell
        #"""
        #for section in self.all:
            #self.__dict__.__delitem__(section.name)
            #h.delete_section(sec=section)
        
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
        
        NOTE: 2021-02-09 11:59:02 required so that neuron._create_all_list()
        works
        
        See NOTE: 2021-02-09 11:58:19 and NOTE: 2021-02-09 11:41:02
        
        
        """
        print("PyNRNCell.all = ", value)
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
            
        
        NOTE: 2021-02-08 14:16:28
        By the way, there is nowhere a documented rule that a Python object MUST
        have an attribute of type list, and named 'all', but the neuron._create_all_list
        function (at module-level) relies on this...
        
        Which is really not a good OO pythonic way of doing things, IMHO
        
        """
        
        if value is None:# or (isinstance(value, (tuple, list, dict)) and len(value) == 0):
            self.clearSections()
            #return
            
        elif isinstance(value, (tuple, list)):
            if len(value) == 0:
                self.clearSections()
                
            elif all([isinstance(v, nrn.Section) for v in value]):
                print("PyNRNCell.sections(sequence)")
                for section in value:
                    secname = section.name().split(".")[-1]
                    print("secname %s = %s" % (secname, section))
                    setattr(self, secname, section)
                
        elif isinstance(value, dict):
            if len(value) == 0:
                self.clearSections()
                return 
            
            for secname, section in value.items():
                print("secname %s  = %s" % (secname, section))
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
        NOTE: 2021-02-09 11:41:02 fixed kernel crashing when calling
        Import3d_GUI.instantiate()
        This was due to Import3d_GUI.instantiate() calling the python
        method neuron._create_all_list() defined in 
        site-packages/neuron/__init__.py 
        
        Unfortunately, neuron._create_all_list() forces the 'all' attribute 
        onto the python object passed as argument to Import3d_GUI.instantiate().
        
        Not a nice thing to do, IMHO.
        
        In the case of PyNRNCell objects, 'all' is a (dynamic) property initially
        with read-only access (i.e. not settable). Therefore, _create_all_list()
        would raise an exception for it being to seta read-only property.
        
        Because the exception is raised by python code executed from within the 
        HOC interpreter top level, this would crash the python kernel.
        
        The fix consists in giving write access to this property, see
        
        NOTE: 2021-02-09 11:58:19 and self.all
        """
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
        swc_reader = h.Import3d_SWC_read()  # NOTE: 2021-02-09 16:50:26
                                            # template defined in read_swc.hoc
                                            # loaded (form hoc side) indirectly
                                            # through h.load_file("import3d.hoc")
        swc_reader.input(fname)
        #print("swc_reader.input(...)")
        swc_importer = h.Import3d_GUI(swc_reader, 0)    # see NOTE: 2021-02-09 16:50:26
                                                        # template defined in 
                                                        # import3d_gui.hoc
        #print("swc_importer")
        swc_importer.instantiate(self) # FIXME crashes the kernel FIXED 2021-02-09 17:22:05
        
    def addSection(self, name:str, L:Real, 
                   diam:typing.Union[Real, tuple, list], 
                   cm:typing.Optional[typing.Union[Real, tuple, list]]=None,
                   diam_interp: typing.Optional[typing.Union[tuple, list]]=None,
                   cm_interp: typing.Optional[typing.Union[tuple, list]]=None,
                   Ra:typing.Optional[Real]=None,
                   nseg:typing.Optional[int]=None,
                   freq:typing.Optional[Real]=None,
                   d_lambda:typing.Optional[Real]=None,
                   parent:typing.Optional[nrn.Section]=None,
                   parent_pos:typing.Optional[Real]=None,
                   orientation:typing.Optional[int]=None) -> typing.Optional[nrn.Section]:
        """Add a section to this cell.
        
        A cell must have at least one section - usually called "soma" but one is
        free to use any name as long as it is unique.
        
        This method creates a nrn.Section object (or uses an externally constructed
        one) then adds it to the cell; optionally, it connects the section to 
        an existing section of this cell (by default, the 0 end of the new section
        is connected to the 1 end of the parent section).
        
        The section's geometry is specified either as a stylized geometry
        (L and diam) or 
        
        A section has two categories of properties:
        ===========================================
        1. Section variables
        --------------------
        These are properties that apply to the section as a whole.
        All section variables listed below are used in this method:
        
            L   : length (um), 
            Ra  : cytoplasmic resistivity (Ohm x cm)
            nseg: discretization parameter i.e. number of "compartments" or "segments"
                    (dimensionless)
            
        2. Range variables
        ------------------
        Thes are continuous functions of position throughout the section. The 
        position is the normalized distance along the centroid of the section,
        a.k.a the "range" or "arc length", and varies linearly from 0 at one end
        to 1 at the other end.
            
            Used in this method:
            
            diam: diameter (um)
            cm  : specific membrane capacitance (uf/cm**2)
            
            Example of range variables NOT specified/used in this method:
            
            v   : membrane potential (mV)
            ina : sodium current (mA/cm**2)
            nai : internal sodium concentration (mM)
            n_hh: Hodgkin-Huxley potassium conductance gating variable (dimensionless)
            
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
        
        Parameters:
        -----------
        
        name: str
            The name of the new section.
            
            The section is created using the section variables length (L), 
            diameter (diam), cytoplasmic resistivity (Ra) and spatial 
            discretization (nseg) as specified below.
        
            The name must not be empty, and must be unique among the cell's 
            sections. If a section with this name already exists, the method 
            issues a warning and returns None.
        
            The name should abide by the python language rules for valid 
            identifiers i.e., it must only contain only alphanumeric and 
            underscore ('_') characters, and must not begin with a digit.
            
        L: float = The length of the section (considered as a cylinder)
        
            NOTE: This is a section variable.
        
        diam: float, or sequence of minimum two floats
            When a float, this is the (constant) diameter of the section 
            (considered as a right cylinder).
            
            When a sequence  of floats, the diameter of each segment in the 
            section will be piecewise linearly interpolated between the values
            given in diam. The interpolation occurs on the interval [0,1] by
            default, unless specified by 'diam_interp' (see below).
            
            WARNING: this will automatically generate a 3D geometry for the 
            section.
            
            NOTE: This is a range variable
            
        Named parameters:
        -----------------
        Ra:float = cytoplasmic resistivity (optional, default is None).
            When None, the section assumes the NEURON default of 35.4 Ohm * cm
            
            NOTE: This is a section variable
            
        cm: float, sequence (tuple, list) of float; optional; 
            When None, the section gets NEURON's default value of 1
            
            When a float scalar, it represents the membrane capacitance for the
            entire section.
            
            When a sequence of floats, this is used to interpolate it along the 
            x coordinates of the section; see also 'cm_interp', below
            
            NOTE: This is a range variable
            
        diam_interp: sequence of minimum two floats, or None
            When None, and diam is a sequence, the diameter of the section's
            compartments will be interpolated on [0,1] from diam[0] to diam[-1] 
            
            Otherwise, the following equality must be satisfied:
                    len(diam) == len(diam_interp)
            
        cm_interp: sequence of minimum two floats, or None
            When None and cm is a sequence, the membrane capacitance of the 
            section's compartments will be interpolated on [0,1] from 
            cm[0] to cm[-1].
            
            Otherwise, cm must be a sequence with 
                    len(cm) == len(cm_interp)
            
        nseg: int (optional, default is PyNRNCell.default_nseg = 51, or the value of
                    the subclass.default_nseg,if overridden)
                    
                Spatial discretization value.
                
                NOTE: This is a section variable
                    
        freq: float (optional, default is None)
            When specified, the discretization parameter is calculated according
            to the d_lambda rule.
            
            'freq' is the frequency for which the AC length constant (lambda_f) 
            is calculated in each compartment
            
            'nseg' is ignored in this case
                
            To change a section's nseg according to the d_lambda rule after the 
            section was created, use geomNseg(...) method.
            
            CAUTION: This requires that Ra and cm are supplied as float scalars.
            
        d_lambda: 
            
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
        if not isinstance(name, str):
            raise TypeError("Expecting a str for parameter 0; got %s instead" % type(name).__name__)
    
        if len(name.strip()) == 0:
            warnings.warn("Cannot accept empty section names")
            return
        
        if name in self.sections:
            warnings.warn("A section named %s already exists in %s" % (name, self.__repr__()))
            return
        
        # NOTE: 2021-02-05 23:01:47
        # this call adds the section to the global HOC interpreter h, making
        # the section visible when calling h.topology()
        #
        # 'section' is a nrn.Section object; also, it will be stored as an 
        # attribute to Cell
        
        section = h.Section(name=name, cell=self)
        
        # NOTE: 2022-01-30 17:07:10
        # Setting up the number of segments in the section can be done in two
        # ways:
        #
        # 1. specify nseg as an int (ideally, an odd number; NOTE although HOC 
        # does not enforce the use of odd number of segments, this is enforced
        # here).
        #
        # 2. use the d_lambda rule and the 'freq' parameter to set up nseg according
        # to the AC length constant(See the NEURON book)
        if isinstance(nseg, int):
            if nseg < 1:
                nseg = 1
            elif nseg % 2 == 0:
                nseg += 1
                
        elif isinstance(freq, Real):
            nseg = self.geomNseg(freq, d_lambda, section)
            
        else:
            nseg=self.default_nseg
            
        section.nseg=nseg
        
        section.L = L
        
        if isinstance(Ra, Real): # if not supplied, NEURON has its own default
            section.Ra = Ra
            
        if isinstance(diam, Real): # a constant diameter
            # just call simply this below; this applied diam to all segments of
            # 'section'
            section.diam = diam
                
        elif isinstance(diam, (tuple, list)):
            if not all([isinstance(v, Real) for v in diam]):
                raise TypeError("Expecting a sequence of scalars for diam")
            
            if len(diam) == 1:
                section.diam = diam[0]

            elif len(diam) >= 2:
                if isinstance(diam_interp, (tuple, list)):
                    if len(diam_interp) != len(diam):
                        raise ValueError("lengths of diam and diam_interp must be identical")
                    
                    if not all([isinstance(v, Real) for v in diam_interp]):
                        raise TypeError("diam_interp must contain Real scalars")
                    
                    if not all([ v>=0 and v <=1 for v in diam_interp]):
                        raise ValueError("diam_interp values mut be in the [0,1] interval")
                    
                    for segment in section:
                        segment.diam = np.interp(segment.x, diam_interp, diam)
                        
                elif diam_interp is None:
                    for segment in section.allseg(): # also iterates through ends
                        segment.diam = np.interp(segment.x, [0,1], diam)
                    
                else:
                    raise TypeError("diam_interp has unexpected type: %s" % type(diam_interp).__name__)
                        
            else:
                raise ValueError("diam cannot be an empty sequence")
            
        if isinstance(cm, Real):
            section.cm = cm
            
        elif isinstance(cm, (tuple, list)):
            if not all([isinstance(v, Real) for v in cm]):
                raise TypeError("Expecting a sequence of scalars for cm")
            
            if len(cm) == 1:
                section.cm = cm[0]
                
            elif len(cm) >= 2:
                if isinstance(cm_interp, (tuple, list)):
                    if len(cm_interp) != len(cm):
                        raise ValueError("cm and cm_interp must have identical length")
                    
                    if not all([isinstance(v, Real) for v in cm_interp]):
                        raise TypeError("cm_interp musst contain Real scalars")
                    
                    if not all([v >= 0 and v <=1 for v in cm_interp]):
                        raise ValueError("cm_interp values must all be in the interval [0,1]")
                    
                    for segment in section.allseg(): # also iterates through ends
                        segment.cm = np.interp(segment.x, [0,1], cm)
                        
                    
        if isinstance(freq, Real):
            # set up nseg according to the AC length constant
            self.geomNseg(freq, d_lambda, section)
    
        # NOTE: 2022-01-30 16:56:00
        # self gains 'name' as attribute bound to the section
        setattr(self, name, section)
        
        if isinstance(parent, nrn.Section) and parent.cell() is self \
            and parent in self.all and parent is not section:
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
        
        return section
    
    def geomNseg(self, section:nrn.Section, freq:Real, 
                 d_lambda:typing.Optional[Real]=None) -> int:
        """Applies nseg to a section according to the 'd_lambda' rule.
        The sections need to have a stylized morphology.
        
        Parameters:
        ===========
        section: nrn.Section. The section specified here must belong to this 
                cell (otherwise, raises KeyError)
                
        freq: Real: AC frequency for which nseg is to be calculated
        
        d_lambda: Real (optional, default is 0.1)
        
        """ 
        if not isinstance(d_lambda, Real):
            d_lambda = self.d_lambda
            # NOTE: can d_lambda be set individually for each section?
            
        if isinstance(section, nrn.Section):
            if section not in self.all:
                raise KeyError("Section %s not found in %s" % (section, self))
            
            return int( (section.L/(d_lambda * lambda_f(freq, section)) + 0.9) /2 ) * 2 + 1
            
        else:
            raise TypeError("Expecting a nrn.Section; got %s instead" % type(section).__name__)

    def getSection(self, name):
        if not isinstance(name, str):
            raise TypeError("Expecting a str; got %s instead" % type(name).__name__)
        
        ret = [(sn, s) for (sn, s) in self.sections.items() if sn.split(".")[-1] == name]
        
        if len(ret):
            if len(ret) > 1:
                raise RuntimeError("There are multiple sections with the same name %s" % name)
            
            return ret[0]
        
    def _setup_morphology(self, nseg:typing.Optional[int] = None):
        """To override in subclass
        """
        print("To add sections to this cell all its 'addSection(...)' method, or its 'loadMorphologySWC(swc_file_name)' method to load a neuron morphology from a SWC file.")
        #self.addSection(sec="soma", L=13, diam=13, Ra=100, nseg=nseg)
        #self.addSection(sec="dend", L=200, diam=1, Ra=100, nseg=nseg, parent = self.soma)
        #self.dend.connect(self.soma)
        
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
            
    def section3DPoints(self, section:typing.Union[nrn.Section, str]) -> typing.Optional[pd.DataFrame]:
        """Returns 3D shape parameters of the section (when defined).
        
        If section.n3d() == 0 returns None
        """
        
        if not section in self:
            return
        
        arr = np.array([(i, section.x3d(i), section.y3d(i), section.z3d(i), section.diam3d(i)) for i in range(section.n3d())])
        
        if arr.size:
            columns = ["Point", "x3d", "y3d", "z3d", "diam3d"]
            return pd.DataFrame(data=arr, columns = columns)
        
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
    if cell is None:
        for sec in h.allsec():
            h.delete_section(sec=sec)
            
    elif isinstance(cell, PyNRNCell):
        for sec in h.allsec():
            if sec in cell:
                cell.removeSection(sec)
                
    else:
        raise TypeError("Expecting a PyNRNCell or None; got %s instead" % type(cell).__name__)

def lambda_f(freq:Real, section:nrn.Section):
    """Calculate AC length constant (lambda_f) for a section.
    See https://neuron.yale.edu/neuron/static/docs/d_lambda/d_lambda.html
    
    The neuron function ;lambda_f is defined in share/nrn/lib/hoc/stdlib.hoc
    
    To determine the odd nseg value so that the segments of a secion are no
    longer than d_lambda times AC length constant at a given frequency, use the 
    formula
    
        nseg = int((L / (d_lambda * lambda_f(freq)) + 0.9) / 2) * 2 + 1
    
    where:
        L:float        = section.L
        d_lambda:float = usually 0.1
        freq:float     = frequency (see below)
    
    Parameters:
    ----------
    freq: Real  = Frequency for which the AC length constant is calculated.
    section: nrn.Section
        Make sure to specify section's diam, L, Ra and cm before calling this
        function.
    
    """
    if section.n3d() < 2:
        return 1e-5 * np.sqrt(section.diam / (4*np.pi*freq*section.Ra*section.cm))
        #return 1e-5 * np.sqrt(section.diam / (4*h.PI*freq*section.Ra*section.cm))
    
    else:
        x1 = section.arc3d(0)
        d1 = section.diam3d(0)
        lam = 0
        for i in range(1, section.n3d()):
            x2 = section.arc3d(i)
            d2 = section.diam3d(i)
            lam += (x2-x1) / np.sqrt(d1+d2)
            x1 = x2
            d1 = d2
            
        lam *= np.sqrt(2) * 1e-5 * np.sqrt(4*np.pi*freq*section.Ra*section(0.5).cm)
        #lam *= np.sqrt(2) * 1e-5 * np.sqrt(4*h.PI*freq*section.Ra*section(0.5).cm)
        
        return section.L/lam
    

__all__ = ["PyNRNCell", "BallAndStick", "remove_all_sections", "lambda_f"]
#__all__ = ["PyNRNCell", "BallAndStick", "Ring"]
