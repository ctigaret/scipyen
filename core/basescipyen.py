"""Base ancestor of Scipyen's data objects: AnalysisUnit, ScanData
"""
import functools, typing
import collections
from datetime import datetime, date, time, timedelta
import numpy as np
import quantities as pq
import neo
import vigra
from traitlets.utils.importstring import import_item
from core import quantities as cq
from core.triggerprotocols import TriggerProtocol
from core.quantities import units_convertible
from core.prog import ArgumentError, OneOf, TypeValidator, GenericValidator

def __parse_attribute_specification__(x:tuple) -> dict:
    """
    x: tuple with 1 to 6 elements:
        x[0]: str, name of the attribute
        
        x[1]: str, type, tuple of types or anyhing else
            when a :str: is if first tested for a dotted type name ; if a dotted
                type name this is interpreted as the type of the attribute's
                value; otherwise it is taken as the default value of a str-type 
                attribute;
                
            when a type or tuple of types: this is the default value type of the
                attribute, and the default value is the default constructor if 
                it takes no parameters, else None
                
            when a tuple:
                this can be a tuple of types, or objects; in the former case, 
                these are acceptable type of the of the attribute; in the latter,
                the type of objects indicate the acceotabke types of the 
                attribute, AND the fuirst of the obejcts in the tuple also 
                represent the default value of the attribute
                
            antyhing else: this is the default value of the attribute, and its
                type is the acceptable type of the attribute
                
        x[2]: type or tuple of types
            When a type or tuple of types, this is the explicit type expected
            for the attribute.
        
            When attribute type as determined from x[1] is numpy ndarray, 
            Python Quantity or VigraArray:
            x[2] can be:
            tuple of np.dtype objects: allowed array dtypes
            tuple of int:   allowed shape (number of dimensions is deduced)
            int:            allowed number of dimensions
            dtype:          allowed array dtype
            pq.Quantity:    allowed units (when type is python Quantity)
                            NOTE: this is not strict: unit matching is based on
                            the convertibility between attribute' value and the
                            specified units
            str:            array order (for VigraArrays)
            
            NOTE: to avoid further confusions, dtypes must be specified directly    
                and a str will not be interpreted as dtype 'kind'
            
        x[3]-x[7]: as x[2] for numpy arrays
            NOTE: duplicate specifications will be ignored
            
        NOTE: For objects of any type OTHER than numpy ndarray, only the first
        three elements are sufficient
        

        NOTE: The specification for the first three elements of 'x' is intended 
            to cover the case of attribute definitions in BaseNeo objects.
            
        
    Returns:
    --------
    dict with the following key/values:
    
        name:str,
        default_value: Python object,
        default_value_type: Python type or tuple of types
        default_value_ndim: int or None,
        default_value_dtype: numpy dtype object or None,
        default_value_units: Python Quantity object or None
        
    NOTE: 
    default_value is None when either:
        * it was specified as None (in x[1])
        * default_value_type is a type that cannot be instantiated without 
            arguments
        * default_value_type is a tuple of types
    """
    def __check_array_attribute__(rt, param):
        if rt["default_value"] is not None:
            if not isinstance(rt["default_value"], np.ndarray):
                raise ValueError(f"Type of the default value type {type(rt['default_value']).__name__} is not a numpy ndarray")
            
        if isinstance(param, collections.abc.Sequence):
            if all(isinstance(x_, np.dtype) for x_ in param):
                if rt["default_value_dtype"] is None:
                    if isinstance(rt["default_value"], np.ndarray):
                        if rt["default_value"].dtype not in tuple(param):
                            raise ValueError(f"dtype of the default value type ({type(rt['default_value']).dtype}) is not in {param}")
                            
                    rt["default_value_dtype"] = tuple(param)
    
            elif all(isinstance(x_, int) for x_ in param):
                if rt["default_value_shape"] is None or rt["default_value_ndim"] is None:
                    if isinstance(rt["default_value"], np.ndarray):
                        if rt["default_value"].shape != tuple(param):
                            raise ValueError(f"Default value has wrong shape ({rt['default_value'].shape}); expecting {param}")

                rt["default_value_shape"] = tuple(param)
                rt["default_value_ndim"] = len( rt["default_value_shape"])
                
        elif isinstance(param, np.dtype):
            if rt["default_value_dtype"] is None:
                if isinstance(rt["default_value"], np.ndarray):
                    if rt["default_value"].dtype != param and rt["default_value"].dtype.kind != param.kind:
                        raise ValueError(f"Wrong dtype of the default value ({rt['default_value'].dtype}); expecting {param}")
                rt["default_value_dtype"] = param
    
        elif isinstance(param, int):
            if rt["default_value_ndim"] is None:
                if isinstance(rt["default_value"], np.ndarray):
                    if rt["default_value"].ndim != param:
                        raise ValueError(f"Wrong dimensions for the default value ({rt['default_value'].ndim}); expecting {param}")
                
                rt["default_value_ndim"] = param

        if issubclass(rt["default_value_type"], vigra.VigraArray):
            if rt["default_value"] is not None and not isinstance(rt["default_value"], vigra.VigraArray):
                raise TypeError(f"Wrong default value type ({type(rt['default_value']).__name__}; expecting a vigra.VigraArray")
                                
            if isinstance(param, str):
                if rt["default_array_order"] is None:
                    if isinstance(rt["default_value"], vigra.VigraArray):
                        if rt["default_value"].order != param:
                            raise ValueError(f"Default value has wrong array order ({rt['default_value'].order}); expecting {param} ")
                        
                    rt["default_array_order"] = param
                                        
            elif isinstance(param, vigra.AxisTags):
                if rt["default_axistags"] is None:
                    if isinstance(rt["default_value"], vigra.VigraArray):
                        if rt["default_value"].axistags != param:
                            raise ValueError(f"Default value has wrong axistags ({rt['default_value'].axistags}); expecting {param} ")
                        
                    rt["default_axistags"] = param
                
        if issubclass(rt["default_value_type"], pq.Quantity):
            if rt["default_value"] is not None and not isinstance(rt["default_value"], pq.Quantity):
                raise TypeError(f"Wrong default value type ({type(rt['default_value']).__name__}; expecting a Python Quantity")
                            
            if isinstance(param, pq.Quantity):
                if rt["default_value_ndim"] is None:
                    if not units_convertible(rt["default_value"].units, param.units):
                        raise ValueError(f"Default value has wrong units ({rt['default_value'].units}); expecting {param} ")
                    
                rt["default_value_units"] = param
                
        
    # (name, value or type, type or ndims, ndims or units, units)
    ret = dict(
        name = None,
        default_value = None,
        default_value_type = None,
        default_value_ndim = None,
        default_value_dtype = None,
        default_value_shape = None,
        default_value_units = None,
        default_array_order = None,
        default_axistags    = None,
        )
    
    if len(x):
        ret["name"] = x[0]
        
    if len(x) > 1:
        if isinstance(x[1], str):
            try:
                val_type = import_item(x[1])
            except:
                ret["default_value"] = x[1]
                ret["default_value_type"] = str
                
        elif isinstance(x[1], type):
            ret["default_value_type"] = x[1]
            try:
                ret["default_value"] = x[1]()
            except:
                pass
                
        elif isinstance(x[1], tuple):
            if all(isinstance(x_, type) for x_ in x[1]):
                ret["default_value_type"] = x[1]
            else:
                ret["default_value_type"] = tuple(type(x_) for x_ in x[1])
                ret["default_value"] = x[0]
            
        else:
            ret["default_value"] = x[1]
            ret["default_value_type"] = type(x[1])
      
    if len(x) > 2: # by now, the default_value_type should be established, if it is None (or type(None))
        if ret["default_value_type"] in (None, type(None)) or not issubclass(ret["default_value_type"], np.ndarray):
            if isinstance(x[2], collections.abc.Sequence):
                if all(isinstance(x_, type) for x_ in x[2]):
                    if ret["default_value"] is not None:
                        if not isinstance(ret["default_value"], tuple(set(x[2]))):
                            raise ValueError(f"Type of the default value type {type(ret['default_value']).__name__} is different from the specified default value type {x[2]}")
                    
                    ret["default_value_type"] = tuple(set(x[2])) # make it unique
                    
            elif isinstance(x[2], type):
                if ret["default_value"] is not None:
                    if not isinstance(ret["default_value"], x[2]):
                        raise ValueError(f"Type of the default value type {type(ret['default_value']).__name__} is different from the specified default value type {x[2]}")

                ret["default_value_type"] = x[2]
                
        else:
            __check_array_attribute__(ret, x[2])
            
        if len(x) > 3:
            for x_ in x[3:]:
                __check_array_attribute__(ret, x_)
                    
    # NOTE: 2021-11-29 17:27:07
    # generate arguments for a GenericValidator
    type_dict = dict()
    args = list()
    kwargs = dict()
    
    if isinstance(ret["default_value_type"], type) and all(ret[k] is None for k in ("default_value_ndim", "default_value_dtype", "default_value_units")) or \
        (isinstance(ret["default_value_type"], collections.abc.Sequence) and all(isinstance(v_, type) for v_ in ret["default_value_type"])):
        
        args.append(ret["default_value_type"])
    
    else:
        type_dict = dict()
        if ret["default_value_ndim"] is not None:
            type_dict["ndim"] = ret["default_value_ndim"]
            
        if isinstance(ret["default_value_dtype"], np.dtype):
            type_dict["dtype"] = ret["default_value_dtype"]
            
        if isinstance(ret["default_value_units"], pq.Quantity):
            type_dict["units"] = ret["default_value_units"]
            
        args.append(type_dict)
            
    result = {"name":ret["name"], "value": ret["default_value"], "args":tuple(args), "kwargs": kwargs}
    
    return result

        
class BaseScipyenData(neo.core.baseneo.BaseNeo):
    """Simple repository for the minimally-required, common attributes.
    
    These attributes are : 
    ----------------------------------------------------------------------------
    sourceID: str the ID of the entity source of the data (and ID of a culture
        dish, etc...), 
        
    cell: str, the ID of the cell, or "NA" (not available); optional, default is 
        None (resulting in a "NA value")
        ""
    genotype: str, one of "WT, "HET" or "KO", "+/+", "-/-", "+/-" or a more complex
        and informative genotype notation  
        default is None 
        
    age: scalar python Quantity (with units of time, or convertible to SI time units)
        optional, default is None)
            e.g., 15 pq.div or 20 * pq.pnd (postnatal day), or 16 * pq.emd (embryonic day)
        
    gender: str: one of "F", "M", "NA"; optional, default is None
    
    biometric: dict; optional, default is None
        When a dict it may contain:
            'weight' -> python Quantity of mass units; optional, default is None
            
            'height' -> python Quantity of length units; optional, default is None
            
            ... any other useful biometric with value that can be stored as a 
                short litral description, or a python Quantity, if numeric
            
    procedure: dict; optional, default is None
        When a dict it may contain:
            'type' -> str e.g., "treatment", "surgery", "rotarod", etc informative
                enough to allow data classification later
                
            'name' -> str e.g., the name of the drug, or of the procedure
            
            'dose' -> scalar python Quantity with units of substance (or mass, 
                e.g., g or moles),  density or concentration (i.e. mass/volume)
                or mass/mass (numerically dimensionless after simplification) -
                when it makes sense, e.g. for drug treatments, or None
            
            'route'-> str: how the procedure was administrered (when it makes 
                sense, such as drug treatment, e.g. i.v., i.p., p.o, i.c., 
                perfusion, etc) - should be informative enough to allow data
                classification later
                
            'schedule' -> neo.Epoch: the schedule of treatment, e.g.
                times & duration of drug admninstation or procedure application
                
    protocols: list of TriggerProtocol (for electrophysiology/imaging data)
    
    descriptors: dict with any other descriptors
                
    NOTE: For many of these attributes the values do not yet follow a standard.
    """
    # attr name, type, or default (in whch case type is inferred from default)
    # when 2nd is a type, the default value is set to None
    _needed_attributes_ = (
                            ("sourceID",    "NA"),
                            ("cell",        "NA"),
                            ("genotype",    "NA"),
                            ("gender",      "NA"),
                            ("age",         0*pq.s),
                            ("biometric_weight", 0*pq.g), 
                            ("biometric_height", 0*pq.m),
                            ("procedure_type", "NA"),
                            ("procedure_name", "NA"),
                            ("procedure_dose", 0*pq.g),
                            ("procedure_route", "NA"),
                            ("procedure_schedule", neo.Epoch()),
                            ("protocols",   list()),
                            ("file_datetime", datetime),
                            ("rec_datetime", datetime),
                        )
    # NOTE: 2021-11-26 08:47:50 in the above:
    # subclasses MAY need to treat some of these attributes differently
    # (e.g., 'protocols' in AnalysisUnit and ScanData)
    
    #@classmethod
    #def _setup_descriptors_(cls):
        #for attr in cls._needed_attributes_:
            #attr_dict = __parse_attribute_specification__(attr)
            #descriptor = GenericValidator(*attr_dict["args"], **attr_dict["kwargs"])
            #descriptor.allow_none = True
            #descriptor.__set_name__(cls, attr_dict["name"])
            #setattr(cls, attr_dict["name"], descriptor)
            
    @classmethod
    def _setup_descriptor_(cls, descr):
        descriptor = GenericValidator(*descr["args"], **descr["kwargs"])
        descriptor.allow_none = True
        descriptor.__set_name__(cls, descr["name"])
        setattr(cls, descr["name"], descriptor)
        
    def __init__(self, name=None, description=None, file_origin=None, **kwargs):
        #type(self)._setup_descriptors_()
        for attr in self._needed_attributes_:
            attr_dict = __parse_attribute_specification__(attr)
            proposed_value = kwargs.pop(attr[0], attr_dict["value"])
            type(self)._setup_descriptor_(attr_dict)
            setattr(self, attr_dict["name"], proposed_value)
            
        super().__init__(name=name, description=description, file_origin=file_origin, **kwargs)
        
    @property
    def sourceID(self) -> str:
        return self._sourceID_
    
    @sourceID.getter
    def sourceID(self, value:str):
        if not isinstance(value, str) or len(value.strip()) == 0:
            value = "NA"
        self._sourceID_ = value
    
    @property
    def genotype(self) -> str:
        return self._genotype_
    
    @genotype.getter
    def genotype(self, value:str):
        if not isinstance(value, str) or len(value.strip()) == 0:
            value = "NA"
        self._genotype_ = value
    
    @property
    def protocols(self):
        """A list of TriggerProtocol objects (references)
        """
        return getattr(self, "_protocols_", list())
    
    @protocols.setter
    def protocols(self, value):
        if isinstance(value, TriggerProtocol):
            self._protocols_ = [value]
            
        elif isinstance(value, (tuple, list)) and all([isinstance(p, TriggerProtocol) for p in value]):
            self._protocols_[:] = value #  a reference !
            
            self._protocols_.sort(key=lambda x: x.segmentIndices()[0])
            
        else:
            raise TypeError("Expecting a TriggerProtocol, or a sequence of TriggerProtocol objects; got %s instead" % type(value).__name__)
        
        
    def __attr_str__(self):
        for a in self._needed_attributes_:
            result.append(f"{a[0]}: {getattr(self, a[0], None)}")
            
        return "\n".join(result)


