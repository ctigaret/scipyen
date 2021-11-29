"""Base ancestor of Scipyen's data objects: AnalysisUnit, ScanData
"""
import functools, typing
import collections
import numpy as np
import quantities as pq
import neo
import vigra
from traitlets.utils.importstring import import_item
from core import quantities as cq
from core.triggerprotocols import TriggerProtocol
from core.quantities import units_convertible
from core.prog import ArgumentError, OneOf, TypeValidator, GenericValidator

#def __getter__(obj, name:str):
    #return getattr(obj, name)
    #return object.__getattribute__(obj, f"_{name}_")

#def __setter_old__(obj, value, name, checks, value_type, value_ndim, value_dtype, value_units):# , reference = None):
    #if checks is False: # no checks
        #setattr(obj, name, value)
        ##setattr(obj, name, value)
        #return
        
    ##TODO: refine for type, ndim, units, dtype (when checks is True)
    #if checks is True:
        #old_value = getattr(obj,name)
        
        #expected_value_type = value_type if isinstance(value_type, type) or (isinstance(value_type, tuple) and all(isinstance(x_, type) for x_ in value_type))  else type(old_value)
        
        #if not isinstance(value, expected_value_type):
            #raise TypeError(f"Expecting a {expected_value_type} type; got {type(value).__name__} instead")

        #if isinstance(old_value, np.ndarray):
            #expected_ndim = value_ndim if isnstance(value_ndim, int) else old_value.ndim
            
            #expected_dtype = value_dtype if isinstance(value_dtype, np.dtype) else old_value.dtype
            
            #if value.dtype != expected_dtype:
                #raise TypeError(f"Expecting an array with dtype {expected_value_dtype}; got {value.dtype} instead")
            
            #if isinstance(value_ndim, int):
                #if value.ndim != value_ndim:
                    #raise TypeError(f"Expecting an array with {value_ndim} dimensions; got {value.ndim} instead")
            
            #if isinstance(old_value, pq.Quantity):
                #expected_units = value_units.units if isinstance(value_units, pq.Quantity) else old_value.units
                #if not units_convertible(value, expected_units):
                    #raise TypeError("Incompatible units")
                
        #setattr(obj, name, value)
    
#def __setter__(obj, value, name, checks:typing.Optional[typing.Union[dict, bool]]=None):
    #print(f"__setter__ obj:  {type(obj).__name__}, name: {name}, value: {type(value).__name__}")
    #if checks is False: # no checks
        #setattr(obj, name, value)
        ##setattr(obj, name, value)
        #return
        
    ##TODO: refine for type, ndim, units, dtype (when checks is True)
    #if isinstance(checks, dict):
        #if len(checks) > 0:
            #old_value = getattr(obj,name)
            
            #if "value_type" in checks:
                #value_type = checks["value_type"]
                #expected_value_type = value_type if isinstance(value_type, type) or (isinstance(value_type, tuple) and all(isinstance(x_, type) for x_ in value_type))  else type(old_value)
                #if not isinstance(value, expected_value_type):
                    #raise TypeError(f"Expecting a {expected_value_type} type; got {type(value).__name__} instead")
                
            #if isinstance(old_value, np.ndarray):
                #if "value_ndim" in checks:
                    #value_ndim = checks["value_ndim"]
                    #expected_ndim = value_ndim if isinstance(value_ndim, int) else old_value.ndim
                    #if value.ndim != expected_ndim:
                        #raise TypeError(f"Expecting an array with {expected_ndim} dimensions; got {value.ndim} instead")
                    
                #if "value_dtype" in checks:
                    #value_dtype = checks["value_dtype"]
                    #expected_dtype = value_dtype if isinstance(value_dtype, np.dtype) else old_value.dtype
                    #if value.dtype != expected_dtype:
                        #raise TypeError(f"Expecting an array with dtype {expected_value_dtype}; got {value.dtype} instead")
                    
                
                #if isinstance(old_value, pq.Quantity):
                    #if "value_units" in checks:
                        #value_units = checks["value_units"]
                        #expected_units = value_units.units if isinstance(value_units, pq.Quantity) else old_value.units
                        #if not units_convertible(value, expected_units):
                            #raise TypeError("Incompatible units")
                        
            #if "predicate" in checks:
                #predicate = checks["predicate"]
                
                #if inspect.isfunction(predicate):
                    #if not predicate(value):
                        #raise ArgumentError(f"Cannot set {name} to {value}")
                
        #setattr(obj, name, value)
    
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
                
            antyhing else: this is the default value of the attribute, with
                type being set to type(x[1])
                
        x[2]: type or tuple of types, or int: 
            When a type or tuple of types, this is the explicit attribute type.
            When an int, and the type as parsed from x[1] is a numpy array, it
            is the number of dimensions;
            
        x[3]: int: the expected dimensionality of the attribute, when attribute is
            a numpy array (this includes VigarArray, python Quantity, neo data 
            objects)
            
            This MAY be 0, when the attribute is a numpy scalar, i.e. an array
            with ndim == 0, as in the following example:
            
            b = np.array([0.])[0]
            b.ndim
            --> 0
            
        x[4]: numpy.dtype or python Quantity
            When a dtype, it is the expected dtype of the array attribute
            
            When a Quantity it is the expected quantity of the attribute
            
        x[5]: python Quantity:
            The expected quantity of the attribute
            
        When the attribute is a numpy array, the default dtype is numpy.dtype(float)
        unless specified by the 4th element of 'x'
        
        When the attribute is a Python Quantity, the quantity must be specified
        as the last element of 'x'

        NOTE: The specification for the first three elemens of 'x' is intended 
            to cover the case of attribute definitions in BaseNeo objects.
            
        
    checks: dict, optional default is None
        When a, the following keys, when present, are used (and consequently
        overide some of the results from parsing of 'x' elements - please refer
        to the text above for their meaning):
        
        value_type - see x[1], x[2] above
        
        value_ndim - see x[3]

        value_dtype - see x[4], x[5]
        
        value_units - see x[5]
        
        predicate - an optional function that performs extensive checks on an
            attribute value, and returns a boolean.
            
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
    
    # (name, value or type, type or ndims, ndims or units, units)
    ret = dict(
        name = None,
        default_value = None,
        default_value_type = None,
        default_value_ndim = None,
        default_value_dtype = None,
        default_value_units = None,
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
                
        elif isinstance(x[1], tuple) and all(isinstance(x_, type) for x_ in x[1]):
            ret["default_value_type"] = x[1]
            
        else:
            ret["default_value"] = x[1]
            ret["default_value_type"] = type(x[1])
            
    if isinstance(ret["default_value_type"], type) and issubclass(ret["default_value_type"],np.ndarray):
        if len(x) < 2:
            raise ValueError("The dimensions of an array attribute must be specified")
        
    if len(x) > 2:
        if isinstance(x[2], type) or (isinstance(x[2], tuple) and all(isinstance(x_, type) for x in x[2])):
            if ret["default_value"] is not None:
                if not isinstance(ret["default_value"], x[2]):
                    raise ValueError(f"Type of the default value type {type(ret['default_value']).__name__} is different from the specified default value type {x[2]}")
            
            ret["default_value_type"] = tuple(set(x[2])) # make it unique
                
        elif issubclass(ret["default_value_type"],np.ndarray):
            if isinstance(x[2], int) and x[2] >= 0:
                ret["default_value_ndim"] = x[2]
                
            #else:
                #raise ValueError("The dimensions of an array attribute must be specified")
        
    if isinstance(ret["default_value_type"], type) and issubclass(ret["default_value_type"], np.ndarray):
        if len(x) > 3:
            if not isinstance(x[3], (np.dtype, pq.Quantity)):
                raise TypeError(f"4th element must be a dtype or Python Quantity; got {x[3]} instead")
    
            if not instance(x[3], np.dtype):
                ret["default_value_dtype"] = x[3]
                
            else:
                ret["default_value_dtype"] = np.dtype(float)
                ret["default_value_units"] = x[3]
                
        if isinstance(ret["default_value"], pq.Quantity):
            if len(x) > 4:
                if isinstance(x[4], pq.Quantity):
                    ret["default_value_units"] = x[4]
                else:
                    ret["default_value_units"] = pq.dimensionless
                    
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
                        )
    # NOTE: 2021-11-26 08:47:50 in the above:
    # subclasses MAY need to treat some of these attributes differently
    # (e.g., 'protocols' in AnalysisUnit and ScanData)
    
    @classmethod
    def _setup_descriptors_(cls):
        for attr in cls._needed_attributes_:
            attr_dict = __parse_attribute_specification__(attr)
            descriptor = GenericValidator(*attr_dict["args"], **attr_dict["kwargs"])
            descriptor.__set_name__(cls, attr_dict["name"])
            setattr(cls, attr_dict["name"], descriptor)
            
    @classmethod
    def _setup_descriptor_(cls, descr):
        descriptor = GenericValidator(*descr["args"], **descr["kwargs"])
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


