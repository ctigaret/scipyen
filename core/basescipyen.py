"""Base ancestor of Scipyen's data objects: AnalysisUnit, ScanData
"""
import functools
import quantities as pq
import neo
from core import quantities as cq

def getter(obj, name:str):
    return getattr(obj, f"_{name}_")
    #return object.__getattribute__(obj, f"_{name}_")

def setter(obj, name, value, val_type):# , reference = None):
    if not isinstance(value, val_type):
        raise TypeError(f"Expecting {val_type}; got {type(val).__name__} instead")
    #if isinstance(default, val_type):
        #if isinstance(val, pq.Quantity):
            
    setattr(obj, f"_{name}_", value)
    #object.__setattr__(obj, f"_{name}_", value)
    
#def descr_getter(obj, name:str):
    #descriptors = getattr(obj, "_descriptors_", None)
    #if not isinstance(descriptors, dict):
        #raise AttributeError(f"{type(obj).__name} does have a '_descriptors_' attribute")
    #if name not in descriptors:
        #raise KeyError(f"{type(obj).__name} '_decsriptors_' attribute does not contain  {name}")
    
    #return descriptors[name]

#def descr_getter(obi, name, value, val_type):
    #descriptors = getattr(obj, "_descriptors_", None)
    #if not isinstance(descriptors, dict):
        #raise AttributeError(f"{type(obj).__name} does have a '_descriptors_' attribute")
    #if not isinstance(value, val_type):
        #raise TypeError(f"Expecting {val_type}; got {type(val).__name__} instead")
    
    #obj._descriptors_[name] = value


class BaseBioData(neo.core.baseneo.BaseNeo):
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
                            ("biometric",   {"weight": 0*pq.g, 
                                             "height": 0*pq.m}),
                            ("procedure",   {"type": "NA",
                                             "name": "NA",
                                             "dose": 0*pq.g,
                                             "route": "NA",
                                             "schedule": neo.Epoch()}),
                            ("protocols",   list()),
                        )
    
    def __init__(self, name=None, description=None, file_origin=None, **kwargs):
        for attr in self._needed_attributes_:
            if isinstance(attr[1], type):
                val_type = attr[1]
                val = None
            else:
                val = attr[1]
                val_type = type(attr[1])
                
            setattr(self, f"_{attr[0]}_", kwargs.pop(attr[0], val))
            setattr(type(self), f"get_{attr[0]}", functools.partial(getter, name=attr[0]))
            setattr(type(self), f"set_{attr[0]}", functools.partial(setter, name=attr[0], val_type=val_type))
            setattr(type(self), attr[0], property(getattr(type(self), f"get_{attr[0]}"), getattr(type(self), f"set_{attr[0]}")))
            
        #self._descriptors_ = DataBag(mutable_types=True, allow_none=True)
        #self._descriptors_.update(kwargs)
        
        #for key, val in self._descriptors_.items():
            #if isinstance(val, type):
                #val_type = val,
                #val = None
            #else:
                #val_type = type(val)
                
            #setattr(type(self), f"get_{key}", functools.partial(descr_getter,name=key))
            #setattr(type(self), f"set_{key}", functools.partial(descr_setter,name=key, val_type=val_type))
            #setattr(type(self), key, property(getattr(type(self), f"set_{key}"), 
                                              #getattr(type(self), f"get_{key}")))
    
        
        super().__init__(name, description, file_origin, **kwargs)
    
        
    
