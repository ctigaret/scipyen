import numbers, operator, math
import inspect, functools, itertools, traceback, typing, warnings
from collections import deque
from collections.abc import Sequence
from pprint import (pprint, pformat)
import h5py
import vigra 
import numpy as np
import quantities as pq
from traitlets import Bunch

from core import datatypes, xmlutils
from core.xmlutils import getChildren as getXMLChildren
from core import quantities as cq
from core.quantities import (arbitrary_unit, 
                            space_frequency_unit,
                            angle_frequency_unit,
                            channel_unit,
                            pixel_unit,
                            quantity2scalar,
                            unit_quantity_from_name_or_symbol,
                            units_convertible,
                            )

from core.datatypes import (is_numeric, is_numeric_string,
                            RELATIVE_TOLERANCE, ABSOLUTE_TOLERANCE, EQUAL_NAN)

from core.utilities import (reverse_mapping_lookup, unique, counter_suffix,
                            isclose, all_or_all_not)

from core.traitcontainers import DataBag

from core.prog import ArgumentError

from .axisutils import (axisTypeName, 
                        axisTypeSymbol, 
                        axisTypeUnits,
                        axisTypeFromString,
                        axisTypeStrings,
                        axisTypeFromUnits,
                        evalAxisTypeExpression,
                        sortedAxisTypes,
                        isValidAxisType,
                        isSpecificAxisType,
                        )

AxisCalibrationDataType = typing.TypeVar("AxisCalibrationData")

class CalibrationData(object):
    """:Superclass: for Axis and Channel calibrations.
    
    The sole purpose of these :classes: is to offer a way to store calibration
    data ('fields') in vigra.AxisInfo objects and optionally to notify code using
    this data to changes to field values.
    
    Calibration fields can be semantically inter-dependent, 
    e.g. axis type <-> axis units <-> (origin, resolution) <-> axis type key. 
    
    To avoid circular dependencies, manualy changing one field in a live 
    CalibrationData object does NOT automatically reassigns values to the other
    fields.
    
    Therefore, if a parameter is changed AFTER initialization, the other fields 
    may have to be changed manually to reflect the new calibration in a meaningful
    way.
    
    For example:
        1) adding channels to a NonChannel axis will NOT change the type
    of the axis to Channels.
    
        2) changing the type of a NonChannel axis to a Channels axis will NOT
        add channel calibration data - this has to be added manually - and the 
        reverse operation will NOT remove channel calibration data, if it exists.
        
        3) switching axis type will NOT change axis key, and vice-versa
    
    NOTE 1: calibration fields (as set up in here and derived :classes:)
    are only checked at initialization time.
    
    NOTE 2: CalibrationData assumes a linear (1st order) model
    
    
    """
    parameters = ("units", "origin", "resolution")
    
    @classmethod
    def isCalibration(cls, x):
        return isinstance(x, cls) or (isinstance(x, dict) and all(k in x for k in cls.parameters))
        
    def __init__(self, *args, **kwargs):
        """Calibration data constructor.
        
        Initializes an object of :class: CalibrationData or one of its 
        :subclasses: : AxisCalibrationData, ChannelCalibrationData.
        
        The calibration fields are initialized from var-positional parameters by
        'cascading assignment' (see 'Var-positional parameters' below) and/or 
        from var-keyword parameters.
        
        The latter can override field values set up by the former.
        
        Any calibration field NOT initialized by var-positional or var-keyword
        parameters will get a default value.
        
        Called without ANY parameters the constructor initializes an instance of
        CalibrationData (or AxisCalibrationData or ChannelCalibrationData) with
        default field values:
        
        CalibrationData:
        {'origin': 0.0,
         'resolution': 1.0,
         'units': Dimensionless('dimensionless', 1.0 * dimensionless)}
        
        AxisCalibrationData:
        {'key': '?',
         'name': 'UnknownAxisType',
         'origin': 0.0,
         'resolution': 1.0,
         'type': vigra.vigranumpycore.AxisType.UnknownAxisType,
         'units': Dimensionless('dimensionless', 1.0 * dimensionless)}
        
        ChannelCalibrationData:
        {'index': 0,
         'maximum': nan,
         'name': 'channel',
         'origin': 0.0,
         'resolution': 1.0,
         'units': UnitQuantity('arbitrary unit', 1.0 * dimensionless, 'a.u.')}
         
        NOTE: A default AxisCalibrationData for a Channels axis need not contain
        actual ChannelCalibrationData  - a 'virtual channel' calibration with
        default values will be generated when needed.
         
        Var-positional parameters (*args) and cascading assignment of fields:
        ====================================================================
        
        *args is a (possibly empty) sequence of parameters (comma-separated)
        where each parameter can be of one of the following types:
        
        1) CalibrationData or a :subclass:  AxisCalibrationData, ChannelCalibrationData
            
        2) vigra.AxisInfo, 
        
        3) vigra.AxisType
        
        4) a mapping (dict) with key/value pairs appropriate for this object type
        
        5) int, 
        
        6) complex, 
        
        7) float (including the values numpy.nan and math.nan)
        
        8) str
        
        9) Python Quantity, 
        
        10) Python quantities.dimensionality.Dimensionality
        
        11) numpy array
        
        The object will be fully initialized by the first var-positional 
        parameter that satisfies the conditions below and all other var-positional 
        and var-keyword parameters will be ignored:
        a) parameter is of the same type as the object initialized (copy constructor)
        b) parameter is a vigra.AxisInfo
        c) parameter is a mapping with appropriate key/value pairs
        d) parameter is a str containing an XML-formatted calibration string
        
        When the parameter is a vigra.AxisInfo, axis calibration data will NOT
        be embedded in its 'description' attribute.
        
        With the exception of var-positional parameters described above, all
        other var-positional parameters may be specified more than once. These 
        will be used to assign values for the calibration fields for which the 
        parameter type is appropriate, ONLY IF the corresponding field had not 
        been already set by previous parameters ('cascading assignment'). 
        
        The field order for this 'cascading assignment' is given below:
        
        Parameter type:     Action:                                   
        ------------------------------------------------------------------------
        Same as             Copy constructor. 
        self.__class__      The object will be fully initialized by the first 
                            parameter of this type and all other var-positional
                            and var-keyword parameters are ignored.
        
        vigra.AxisInfo      When self.__class__ is AxisCalibrationData:
        
                            Initialize this object from the parameter's 
                            'description' attribute, if it contains an
                            XML-formatted calibration substring, else determine
                            default values from the parameter's 'key' and 
                            'typeFlags' attributes.
                            
                            The object will be fully initialized by the first 
                            parameter of this type and all other var-positional
                            and var-keyword parameters are ignored.
                            
        dict                Calibration fields set up from the key/value pairs
                            if appropriate (verified by CalibrationData.isCalibration).
                            
                            The object will be fully initialized by the first 
                            parameter of this type and all other var-positional
                            and var-keyword parameters are ignored.
                            
        str                 When self.__class__ is AxisCalibrationData:
        
                            If parameter contains an XML-formatted substring,
                            it will be parsed to intialize the AxisCalibrationData
                            obj. In this case, the object will be fully initialized
                            by the first  parameter of this type and all other 
                            var-positional and var-keyword parameters are ignored.
                            
                            Any other str: determine and set 'type' and dependent
                            fields 'key', 'name', 'units', then assign to 'name'.

                            NOTE: if channel calibrations are passed in **kwargs 
                            (see below) then force 'type' to be Channels and set
                            the dependent fields accordingly.
                            
                            Then determine and set 'units'.
                            
        vigra.AxisType      When self.__class__ is AxisCalibrationData:
        
                            If 'type' not set, then determine and set 'type' 
                            and dependent fields 'key', 'name', 'units'.                         
                                                                                 
                            NOTE: if channel calibrations are passed in **kwargs 
                            (see below) then force 'type' to be Channels and set
                            the dependent fields accordingly.
                            
                            This parameter is ignored when self.__class__ is 
                            any another CalibrationData :(sub)class:
                                                    
        int                 When self.__class__ is AxisCalibrationData:
        
                            If 'type' is not set, interpret this as a typeFlags
                            to set 'type' and dependent fields 'key', 'units' &
                            'name'.
                            
                            NOTE: if channel calibrations are passed in **kwargs 
                            (see below) then force 'type' to be Channels and set
                            the dependent fields accordingly.
                            
                            Then assign to 'index' then 'maximum' if self is a
                            ChannelCalibrationData.
                            
                            Then assign to 'origin', then 'resolution'.
                            
        Python Quantity     Assign to 'units', 'origin', then 'resolution' (then 
                            'maximum', for ChannelCalibrationData)
                            
        numpy array         Assign to 'origin' then 'resolution', (then 'maximum'
                            for ChannelCalibrationData)
                            
        Python quantities.dimensionality.Dimensionality
                            Assign to 'units'
                            
        float, complex      Assign to 'origin' then 'resolution' (then 'maximum'
                            for ChannelCalibrationData)
                            
        np.nan, math.nan    Assign to 'origin' then 'resolution' (then 'maximum'
                            for ChannelCalibrationData)
                            
        ------------------------------------------------------------------------
                            
        Var-keyword parameters:
        =======================
            These are used to override the values assigned to calibration fields
            by the var-positional parameters above (is given) or assign these 
            fields directly.
            
        The valid keyword literals and value types are:
        
        'type': `vigra.AxisType`, `int` (logical OR of `vigra.AxisType` flags), 
                or `str`
        
            When a `str` this can be a vigra.AxisInfo 'key' or a descriptive 
                string (see axisutils.axisTypeFromString() for details)
                
            This will set up the calibration's 'type' field and the derived
            fields 'key' 'name' and 'unts'
            
        'name': str -> calibration 'name' field
        
        'index': int -> only for ChannelCalibrationData; sets up 'index' field
        
        'units': `str`, `Python quantities.Quantity`, or 
                `quantities.dimensionality.Dimensionality`
                
        'origin', 'minimum', 'resolution', 'maximum -> scalars:
            Python Quantity or numpy array, int, cmplex, or float (including 
            np.nan, math.nan).
                                
            When these are a Quantity their 'units' attribute must be convertible
            to the 'units' field.
                
            These will set up the corresponding calibration fields (NOTE that
            'minimum' is an alias to 'origin'; 'maxium' is only used for 
            ChannelCalibrationData)
        
        """
        # FIXME 2021-10-22 09:48:23
        # a DataBag here gets "sliced" in :subclasses: of CalibrationData
        # why ???
        #self._data_ = DataBag()
        self._data_ = Bunch()
        
        self._relative_tolerance_ = 1e-4
        self._absolute_tolerance_ = 1e-4
        self._equal_nan_ = True
        
        for param in self.__class__.parameters:
            self._data_[param] = None
            
        # allow ONE calibration-like dict or calibration data object
        if len(args) == 1 and AxisCalibrationData.isCalibration(args[0]):
            if isinstance(args[0], dict):
                kwargs = args[0]
                args = tuple()
            elif isinstance(args[0], AxisCalibrationData):
                self._data_.update(args[0]._data_)
                return
            
        # cache channel calibration data structures in kwargs to ensure consistency
        channeldata = [(k, ChannelCalibrationData(v)) for k,v in kwargs.items() if ChannelCalibrationData.isCalibration(v) and k not in self.__class__.parameters]
        
        for c[0] in channeldata:
            kwargs.pop(k, None)
        
        for arg in args:
            # below, whenever we set the axistype we also set the params derived
            # from it, if required: axisname, axiskey, units
            
            if isinstance(arg, self.__class__):
                # copy c'tor
                self._data_.update(arg._data_) # DONE
                return
            
            if isinstance(arg, str):
                if self.__class__ == AxisCalibrationData:
                    # arg can be a 'key' string, a string containing a
                    # calibration sub-string (XML-formatted) or a general 
                    # string from whcih the axis type can be deduced using the
                    # heuristics in axisutils.axisTypeFromString()
                    if "<axis_calibration>" in arg:
                        try:
                            cal_str_start_stop = AxisCalibrationData.findCalibrationString(arg)
                            cal = AxisCalibrationData.fromCalibrationString(arg[cal_str_start_stop[0]:cal_str_start_stop[1]])   
                            self._data_.update(cal._data_)
                            return
                        except:
                            raise ValueError(f"str argument is an ambiguous calibration string")
                        
                    elif not isSpecificAxisType(self._data_.type):
                        self._data_.type = axisTypeFromString(arg)
                        
                        if len(channeldata):
                            self._data_.type = vigra.AxisType.Channels
                        
                        if isSpecificAxisType(self._data_.type):
                            if not isinstance(self._data_.name, str) or len(self._data_.name.strip()) == 0:
                                self._data_.name = axisTypeName(self._data_.type)
                                
                            if not isinstance(self._data_.key, str) or len(self._data_.key.strip()) == 0:
                                self._data_.key = axisTypeSymbol(self._data_.type)
                                
                            if not isinstance(self._data_.units, pq.Quantity):
                                self._data_.units = axisTypeUnits(self._data_.type)
                                
                    elif not isinstance(self._data_.name, str) or len(self._data_.name.strip()) == 0:
                        self._data_.name = arg
                        
                if not isinstance(self._data_.units, pq.Quantity):
                    try:
                        self._data_.units = unit_quantity_from_name_or_symbol(arg)
                    except:
                        pass # let the next args deal with it
                    
            elif isinstance(arg, vigra.AxisType):
                if self.__class__ == AxisCalibrationData:
                    if not isSpecificAxisType(self._data_.type):
                        self._data_.type = arg
                        
                        if len(channeldata):
                            self._data_.type = vigra.AxisType.Channels
                        
                        if not isinstance(self._data_.name, str) or len(self._data_.name.strip()) == 0:
                            self._data_.name = axisTypeName(self._data_.type)
                            
                        if not isinstance(self._data_.key, str) or len(self._data_.key.strip()) == 0:
                            self._data_.key = axisTypeSymbol(self._data_.type)
                        
                        if not isinstance(self._data_.units, pq.Quantity):
                            self._data_.units = axisTypeUnits(self._data_.type)
                    
            elif isinstance(arg, int):
                if self.__class__ == AxisCalibrationData:
                    if not isSpecificAxisType(self._data_.type):
                        if isSpecificAxisType(arg): 
                            if arg == vigra.AxisType.UnknownAxisType:
                                self._data_.type = vigra.AxisType.UnknownAxisType
                            elif arg == vigra.AxisType.AllAxes:
                                self._data_.type = vigra.AxisType.AllAxes
                            elif arg == vigra.AxisType.NonChannel:
                                self._data_.type = vigra.AxisType.NonChannel
                            else:
                                test = list(v[1] for v in sortedAxisTypes if v[0] & arg)[2:]
                                if len(test):
                                    self._data_.type = functools.reduce(operator.or_, test)
                                    
                        if len(channeldata):
                            self._data_.type = vigra.AxisType.Channels
                                
                        if isSpecificAxisType(self._data_.type):
                            if not isinstance(self._data_.name, str) or len(self._data_.name.strip()) == 0:
                                self._data_.name = axisTypeName(self._data_.type)
                                
                            if not isinstance(self._data_.key, str) or len(self._data_.key.strip()) == 0:
                                self._data_.key = axisTypeSymbol(self._data_.type)
                                
                            if not isinstance(self._data_.units, pq.Quantity):
                                self._data_.units = axisTypeUnits(self._data_.type)
                                
                if self.__class__ == ChannelCalibrationData:
                    if not isinstance(self._data_.index, int) and arg >= 0:
                        self._data_.index = arg
                        
                    elif not isinstance(self._data_.maximum, (complex, float, int)):
                        self._data_.maximum = arg
                            
                if not isinstance(self._data_.origin, (complex, float, int)):
                    self._data_.origin = quantity2scalar(arg)
                    
                elif not isinstance(self._data_.resolution, (complex, float, int)):
                    self._data_.resolution = quantity2scalar(arg)
                
            elif isinstance(arg, pq.Quantity):
                if not isinstance(self._data_.units, pq.Quantity):
                    self._data_.units = arg.units
                    
                if not isinstance(self._data_.origin, (complex, float, int)):
                    if not units_convertible(self._data_.units.units, arg.units):
                        raise TypeError(f"'origin' units {arg.units} are incompatible with the specified units ({self._data_.units})")
                    
                    if arg.units != self._data_.units.units:
                        arg = arg.rescale(self._data_.units.units)
                        
                    self._data_.origin = quantity2scalar(arg)
                    
                elif not isinstance(self._data_.resolution, (complex, float, int)):
                    if not units_convertible(self._data_.units.units, arg.units):
                        raise TypeError(f"'origin' units {arg.units} are incompatible with the specified units ({self._data_.units})")
                    
                    if arg.units != self._data_.units.units:
                        arg = arg.rescale(self._data_.units.units)
                        
                    self._data_.resolution = quantity2scalar(arg)
                    
                elif self.__class__ == ChannelCalibrationData:
                    if not isinstance(self._data_.maximum, (complex, float, int)):
                        if not units_convertible(self._data_.units.units, arg.units):
                            raise TypeError(f"'max value' units {arg.units} are incompatible with the specified units ({self._data_.units})")
                        
                        if arg.units != self._data_.units.units:
                            arg.rescale(self._data_.units.units)
                            
                        self._data_.maximum = quantity2scalar(arg)
                    
            elif isinstance(arg, np.ndarray):
                if not isinstance(self._data_.origin, (complex, float, int)):
                    self._data_.origin = quantity2scalar(arg)
                    
                elif not isinstance(self._data_.resolution, (complex, float, int)):
                    self._data_.resolution = quantity2scalar(arg)
                
                elif self.__class__ == ChannelCalibrationData:
                    if not isinstance(self._data_.maximum, (complex, float, int)):
                        self._data_.maximum = quantity2scalar(arg)
                    
            elif isinstance(arg, pq.dimensionality.Dimensionality):
                if not isinstance(self._data_.units, pq.Quantity):
                    self._data_.units = [k for k in arg.simplified][0]
                
            elif isinstance(arg, (float, complex)):
                if not isinstance(self._data_.origin, (complex, float, int)):
                    self._data_.origin = arg
                    
                elif not isinstance(self._data_.resolution, (complex, float, int)):
                    self._data_.resolution = arg
                    
                elif self.__class__ == ChannelCalibrationData:
                    if not isinstance(self._data_.maximum, (complex, float, int)):
                        self._data_.maximum = arg
                        
            elif arg in (np.nan, math.nan):
                if not isinstance(self._data_.origin, (complex, float, int)) and self._data_.origin != np.nan:
                    self._data_.origin = arg
                    
                elif not isinstance(self._data_.resolution, (complex, float, int)) and self._data_.origin != np.nan:
                    self._data_.resolution = arg
                    
                elif self.__class__ == ChannelCalibrationData:
                    if not isinstance(self._data_.maximum, (complex, float, int)) and self._data_.maximum != np.nan:
                        self._data_.maximum = arg
                        
            elif isinstance(arg, vigra.AxisInfo):
                # will use calibration string embedded in the AxisInfo.description
                # if found;
                # the values of the AsisInfo's typeFlags & key attributes take
                # precedence over the calibration string if the latter is not
                # conforming
                # in either case the AxisInfo's description will NOT be updated;
                # this MUST be done separately
                
                if self.__class__ == AxisCalibrationData:
                    axtype = arg.typeFlags
                    axkey = arg.key
                    axres = 1. if arg.resolution == 0 else arg.resolution
                    axorigin = 0.0
                    
                    cal_str_start_stop = AxisCalibrationData.findCalibrationString(arg.description)
                    
                    if cal_str_start_stop is None:
                        self._data_.type = axtype
                        self._data_.key = axkey
                        self._data_.name = axisTypeName(self._data_.type)
                        self._data_.units = axisTypeUnits(self._data_.type)
                        self._data_.origin = 0.
                        self._data_.resolution = 1. if arg.resolution == 0. else arg.resolution
                        # bring back channel calibrations if appropriate
                        if self._data_.type & vigra.AxisType.Channels:
                            for k, chcal in enumerate(channeldata):
                                self._data_[chcal[0]] = chcal[1]
                        
                    else:
                        cal = AxisCalibrationData.fromCalibrationString(arg.description[cal_str_start_stop[0]:cal_str_start_stop[1]])

                        self._data_.update(cal._data_)
                        self._data_.key = arg.key
                        
                    return # only allow one AxisInfo argument
                
                else:
                    raise TypeError(f"AxisInfo parameters accepted only for the initialization of AxisCalibrationData")
                
            elif isinstance(arg, dict) and self.__class__.isCalibration(arg):
                # form a calibration dict
                self._data_.update(arg)
                return # accept only one calibration dict
                    
        axtype = kwargs.pop("type", None)
        if axtype is not None:
            if self.__class__ == AxisCalibrationData:
                if isSpecificAxisType(axtype):
                    self._data_.type = axtype
                
                if isinstance(self._data_.type, str):
                    self._data_.type = axisTypeFromString(self._data_.type)
                    
                if not isinstance(self._data_.type, (vigra.AxisType, int)) or not any(self._data_.type & x for x in vigra.AxisType.values):
                    self._data_.type = vigra.AxisType.UnknownAxisType
                
                if len(channeldata):
                    self._data_.type = vigra.AxisType.Channels
                
                if self._data_.key is None:
                    self._data_.key = axisTypeSymbol(self._data_.type, False)
                    
        axkey = kwargs.pop("key", None) # allow specific overriding of the key field
        if isinstance(axkey, str) and len(axkey.strip()):
            # WARNING Thsi is NOT checked
            self._data_.key = axkey
            
        axname = kwargs.pop("name", None)
        if axname is not None:
            #if self.__class__ == AxisCalibrationData:
            if isinstance(axname, str) and len(axname.strip()):
                self._data_.name = axname
            
            if not isinstance(self._data_.name, str) or len(self._data_.name.strip()) == 0:
                if hasattr(self._data_, "type"):
                    self._data_.name = axisTypeName(self._data_.type)
                
        chindex = kwargs.pop("index", None)
        if isinstance(chindex, int):
            if self.__class__ == ChannelCalibrationData:
                if isinstance(chindex, int) and chindex >= 0:
                    self._data_.index = chindex
            
        units_ = kwargs.pop("units", None)
        if units_ is not None:
            if isinstance(units_, str):
                try:
                    units_ = unit_quantity_from_name_or_symbol(units_)
                except:
                    units_ = None
            
            if isinstance(units_, pq.dimensionality.Dimensionality):
                units_ = [k for k in units_.simplified][0]
            
            if isinstance(units_, pq.Quantity):
                self._data_.units = units_.units
            
        origin_ = kwargs.pop("origin", None)
        minimum = kwargs.pop("minimum", None)
        
        origin_ = origin_ if origin_ is not None else minimum
        if origin_ is not None:
            if isinstance(origin_, pq.Quantity):
                if not units_convertible(origin_.units, self._data_.units.units):
                    raise TypeError(f"'origin (or minimum)' units {origin_.units} are incompatible with the specified units ({self._data_.units})")
                    
                if origin_.units != self._data_.units.units:
                    origin_ = origin_.rescale(self._data_.units.units)
                    
                self._data_.origin = quantity2scalar(o)
                
            elif isinstance(origin_, (complex, float, int, np.ndarray)) or origin_ in (math.nan, np.nan):
                self._data_.origin = quantity2scalar(origin_)
            
        resoln  = kwargs.pop("resolution", None)
        if resoln is not None:
            if isinstance(resoln, pq.Quantity):
                if not units_convertible(resoln.units, self._data_.units.units):
                    raise TypeError(f"'resolution' units {resoln.units} are incompatible with the specified units ({self._data_.units})")
                    
                if resoln.units != self._data_.units.units:
                    resoln = resoln.rescale(self._data_.units.units)
                    
                self._data_.resolution = quantity2scalar(resoln)
        
            elif isinstance(resoln, (complex, int, float, np.ndarray)) or resoln == np.nan:
                self._data_.resolution = quantity2scalar(resoln)
        
        maxval = kwargs.pop("maximum", None)
        if maxval is not None:
            if self.__class__ == ChannelCalibrationData:
                if isinstance(maxval, pq.Quantity):
                    if not units_convertible(maxval.units, self._data_.units.units):
                        raise TypeError(f"'maximum value' units {maxval.units} are incompatible with the specified units ({self._data_.units})")
                        
                    if maxval.units != self._data_.units.units:
                        maxval = maxval.rescale(self._data_.units.units)
                        
                    self._data_.maximum = quantity2scalar(maxval)
                    
                elif isinstance(maxval, (complex, float, int, np.ndarray)) or maxval == np.nan:
                    self._data_.maximum = quantity2scalar(maxval)
                
        # bring back channel calibration data if necessary and appropriate
        if self.__class__ == AxisCalibrationData:
            if self._data_.type and (self._data_.type & vigra.AxisType.Channels):
                for k, chcal in enumerate(channeldata):
                    # assign calibrations as they come;
                    # use their mapped names in kwargs as arguments
                    # later on, use their own channelname/channelindex fields as needed
                    self._data_[chcal[0]] = chcal[1]
                
        # finally, set up defaults if anything was missed
        if self.__class__ == AxisCalibrationData:
            if not isSpecificAxisType(self._data_.type):
                self._data_.type = vigra.AxisType.UnknownAxisType
                
            if not isinstance(self._data_.name, str) or len(self._data_.name.strip()) == 0:
                self._data_.name = axisTypeName(self._data_.type)
                
            if not isinstance(self._data_.key, str) or len(self._data_.key.strip()) == 0:
                self._data_.key = axisTypeSymbol(self._data_.type)
                
        if self.__class__ == ChannelCalibrationData:
            if not isinstance(self._data_.index, int) or self._data_.index < 0:
                self._data_.index = 0
                
            if not isinstance(self._data_.maximum, (complex, float, int)) and self._data_.maximum != np.nan:
                self._data_.maximum = np.nan
                
            if not isinstance(self._data_.name, str) or len(self._data_.name.strip()) == 0:
                self._data_.name = "channel"
                
        if not isinstance(self._data_.units, pq.Quantity):
            if self.__class__ == AxisCalibrationData:
                self._data_.units = axisTypeUnits(self._data_.type)
                
            elif self.__class__ == ChannelCalibrationData:
                # NOTE: ChannelCalibrationData has no 'type' field
                self._data_.units = pq.arbitrary_unit
                
            else:
                self._data_.units = pq.dimensionless # (UnknownAxisType)
            
        if not isinstance(self._data_.origin, (complex, float, int)):
            self._data_.origin = 0.
            
        if not isinstance(self._data_.resolution, (complex, float, int)):
            self._data_.resolution = 1.
            
    def __str__(self):
        od = dict((k, dict(v._data_) if isinstance(v, CalibrationData) else v) for (k,v) in self._data_.items())
        return pformat(od)
        #return pformat(self._data_)
        
    def _repr_pretty_(self, p, cycle):
        p.text(f"{self.__class__.__name__}:")
        p.breakable()
        od = dict((k, dict(v._data_) if isinstance(v, CalibrationData) else v) for (k,v) in self._data_.items())
        p.pretty(od)
        p.text("\n")
        
    def __contains__(self, item:str):
        """Membership test for channel calibration data
        Parameters:
        ==========
        item: str, int, or ChannelCalibrationData
            When a str, checks for the existence of a ChannelCalibrationData
                mapped to a symbol (str) == item.
                
            When an int, checks for the existence of a ChannelCalibrationData with
                index == item.
                
            When a ChanelCalibrationData object, checks if it exists in this 
            AxisCalibationData object.
            
        Returns:
        ========
        True if item is a symbol mapped to a ChannelCalibrationData, or item is
        a ChannelCalibrationData contained in this AxisCalibrationData object.
        
        WARNING: Returns False when:
        1) This AxisCalibrationData does not relate to a Channels axis;
        
        2) This AxisCalibrationData relates to a virtual Channels axis (i.e., 
        without any instances of ChannelCalibrationData)
        
        """
        
        if isinstance(item, str) and item not in self.parameters:
            return item in self._data_
        
        elif isinstance(item,int) and self.type & vigra.AxisType.Channels:
            return item in list(c[1].index for c in self.channels)
        
        elif isinstance(item, ChannelCalibrationData):
            return item in self._data_.values()
        
        return False
    
    def __eq__(self, other):
        ret = other.__class__ == self.__class__
        
        if ret:
            ret &= all(getattr(self, p, None) == getattr(other, p, None) for p in self.__class__.parameters)
            
        if ret:
            ret &= getattr(self, "nChannels", 0) == getattr(other, "nChannels", 0)
            
        if ret: 
            ret &= all(c[0] == c[1] for c in zip(getattr(self, "channels"), getattr(other, "channels")))
            
        return ret
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def isclose(self, other, 
                rtol = RELATIVE_TOLERANCE, 
                atol = ABSOLUTE_TOLERANCE,
                equal_nan = EQUAL_NAN,
                use_math=True,
                ignore:typing.Optional[typing.Union[str, tuple, list]] = None):
        
        if ignore is not None:
            if all(v not in ignore for v in ('units', 'origin','resolution','maximum')):
                ignore = None
        
        if rtol is None:
            rtol = self.rtol
            
        if atol is None:
            atol = self.atol
        
        ret = other.__class__ == self.__class__
        
        if ret and (ignore is None or "units" not in ignore):
            ret &= units_convertible(self.units, other.units)
            
        if ignore is not None and "units" in ignore:
            if isinstance(ignore, str):
                ignore = ignore.replace("units", "")
                if len(ignore.strip()) == 0:
                    ignore = None
                    
            elif isinstance(ignore, (tuple, list)):
                ignore = list(s for s in ignore if s != "units")
                if len(ignore)==0:
                    ignore = None
                    
        if ret:
            if ignore is None:
                cal_p = list(getattr(self, p) for p in ("calibratedOrigin", "calibratedResolution", "calibratedMaximum") if hasattr(self, p))
                
                if self.units != other.units:
                    oth_p = list(v.rescale(getattr(other, p), self.units) for p in ("calibratedOrigin", "calibratedResolution", "calibratedMaximum") if hasattr(self, p))
                    
                else:
                    oth_p = list(getattr(other, p) for p in ("calibratedOrigin", "calibratedResolution", "calibratedMaximum") if hasattr(self, p))
                    
            else:
                cal_p = list(getattr(self, p) for p in ("calibratedOrigin", "calibratedResolution", "calibratedMaximum") if p not in ignore and hasattr(self, p))
                oth_p = list(getattr(other, p) for p in ("calibratedOrigin", "calibratedResolution", "calibratedMaximum") if p not in ignore and hasattr(other, p))
                         
                    
            ret &= len(cal_p) == len(oth_p) and all(isclose(p[0], p[1], rtol=rtol, atol=atol, equal_nan=equal_nan, use_math=use_math) for p in zip(cal_p, oth_p))
            
        return ret
    
    @property
    def rtol(self):
        return self._relative_tolerance_
    
    @rtol.setter
    def rtol(self, val:float):
        if not isinstance(val, float):
            raise TypeError(f"Expected a float, got {type(val).__name__} instead")
        
        self._relative_tolerance_ = val
        
    @property
    def atol(self):
        return self._absolute_tolerance_
    
    @atol.setter
    def atol(self, val:float):
        if not isinstance(val, float):
            raise TypeError(f"Expected a float, got {type(val).__name__} instead")
        
        if val < 0.:
            raise ValueError(f"Ablsoute tolerance must be >= 0.; got {val} instead")
        
        self._absolute_tolerance_ = val
        
    @property
    def units(self) -> pq.Quantity:
        """Get/set the pysical units of measurement.
        WARNING: Setting this property will NOT adjust (rescale) the 'origin' 
        and 'resolution' - use self.rescale() for that.
        Issues a warning if the new units are NOT typical for the axis type.
        """
        return self._data_.units if isinstance(self._data_.units, pq.UnitQuantity) else self._data_.units.units
    
    @units.setter
    def units(self, u:typing.Union[pq.Quantity, pq.dimensionality.Dimensionality, str]) -> None:
        if isinstance(u, pq.dimensionality.Dimensionality):
            u = pq.quantity.validate_dimensionality(u.simplified)
            
        if isinstance(u, str):
            u = unit_quantity_from_name_or_symbol(u)
            
        if not isinstance(u, pq.Quantity):
            raise TypeError(f"Units expected to be a Python Quantity, Dimensionality, or str; got {type(u).__name__} instead")
        
        if hasattr(self, "type"):
            units_for_type = axisTypeUnits(self.type)
            if not units_convertible(u.units, units_for_type.units):
                axis_type_names = "|".join(axisTypeStrings(self.type))
                warnings.warn(f"Assigning units {u} for a {axis_type_names} axis", RuntimeWarning, stacklevel=2)
                
        self._data_.units = u.units
        
    def rescale(self, u:typing.Union[pq.Quantity, pq.dimensionality.Dimensionality, str]) -> None:
        """Rescale units, origin and resolution for new units.
        
        New units must be convertible to the current units.
        """
        o = self.origin * self.units
        r = self.resolution * self.units
        new_o = o.rescale(u)
        new_r = r.rescale(u)
        self.units = self.units.rescale(u)
        self.origin = quantity2scalar(new_o)
        self.resolution = quantity2scalar(new_r)
    
    @property
    def origin(self):
        """Get/set the origin value
        """
        return self._data_.origin
    
    @origin.setter
    def origin(self, val):
        if isinstance(val, (complex, float, int)):
            self._data_.origin = val
            
        elif isinstance(val, pq.Quantity):
            if not units_convertible(val.units, self.units.units):
                raise TypeError(f"Origin units ({val.units}) incompatible with my units ({self.units.units})")
            
            if val.units != self.units.units:
                val = val.rescale(self.units.units)
                
            self._data_.origin = quantity2scalar(val)
            
        elif isinstance(val, np.ndarray):
            self._data_.origin = quantity2scalar(val)
            
        else:
            raise TypeError(f"Origin expected a scalar int, float, complex, Python Quantity or numpy array; got {type(val).__name__} instead")
            
    @property
    def calibratedOrigin(self):
        """Origin as Python Quantity
        """
        return self.origin * self.units.units
        
    @property
    def resolution(self):
        """Get/set the origin value
        """
        return self._data_.resolution
    
    @resolution.setter
    def resolution(self, val):
        if isinstance(val, (complex, float, int)):
            self._data_.resolution = val
            
        elif isinstance(val, pq.Quantity):
            if not units_convertible(val.units, self.units.units):
                raise TypeError(f"Resolution units ({val.units}) incompatible with my units ({self.units.units})")
            
            if val.units != self.units.units:
                val = val.rescale(self.units.units)
                
            self._data_.resolution = quantity2scalar(val)
            
        elif isinstance(val, np.ndarray):
            self._data_.resolution = quantity2scalar(val)
            
        else:
            raise TypeError(f"Resolution expected a scalar int, float, complex, Python Quantity or numpy array; got {type(val).__name__} instead")
            
    @property
    def calibratedResolution(self):
        """Resolution as Python Quantity
        """
        return self.resolution * self.units.units
        
    @property
    def calibrationTuple(self):
        """Returns a tuple of quantities (unit, origin, resolution)
        """
        if self.__class__ == ChannelCalibrationData:
            return (self.units.units, self.calibratedOrigin, self.calibratedResolution, self.calibratedMaximum)
            
        return (self.units.units, self.calibratedOrigin, self.calibratedResolution)
    
    @property
    def data(self):
        """Returns the calibration data as a dict
        """
        ret = dict(self._data_)
        
        if hasattr(self, "type") and self.type & vigra.AxisType.Channels:
            ret.update(dict((c[0], c[1].data) for c in self.channels))
            
        return ret
    
    def calibratedCoordinate(self, value):
        if not isinstance(value, numbers.Number):
            raise TypeError("expecting a scalar; got %s instead" % type(value).__name__)
        
        return (value * self.resolution + self.origin) * self.units.units
        
        #if isinstance(key, vigra.AxisInfo):
            #key = key.key
        #return (value * self.getDimensionlessResolution(key, channel) + self.getDimensionlessOrigin(key, channel)) * self.getUnits(key, channel)
    
    def calibratedDistance(self, value:numbers.Number):
        """Distance from origin in axis units
        value: distance from origin in samples
        """
        
        if not isinstance(value, numbers.Number):
            raise TypeError(f"Expecting a number.Number; got {type(value).__name__} instead")
        
        return value * self.resolution * self.units
    
    def calibratedMeasure(self, value:numbers.Number):
        if not isinstance(value, numbers.Number):
            raise TypeError(f"Expecting a numbers.Number; got {type(value).__name__} instead")
        
        return (self.origin + value * self.resolution) * self.units
    
    def sampleDistance(self, value:pq.Quantity):
        """Returns the number of samples for the calibrated distance from origin.
        """
        if not isinstance(value, pq.Quantity):
            raise TypeError(f"Expecting a Quantity; got {type(value).__name__} instead")
        
        if value(size) != 1:
            raise TypeError(f"Expecting a scalar Quantity; instead, got a {value.size}-sized Quantity")
        
        if not units_convertible(value.units, self.units.units):
            raise TypeError(f"Cannot convert between {value.units} and {self.units}")
        
        value_dim = pq.quantity.validate_dimensionality(value.units)
        my_dim = pq.quantity.validate_dimensionality(self.units)
        
        if value_dim != my_dim:
            cf = pq.quantity.get_conversion_factor(my_dim, value_dim)
            value *= cf
            
        return math.ceil(value / self.resolution)
        #return int(np.rint(value / self.resolution))
    
class ChannelCalibrationData(CalibrationData):
    """Encapsulates calibration data for pixel INTENSITIES in a given channel.
    
    Do not confuse with the calibration of a Channels axis itself.
    
    """
    parameters = CalibrationData.parameters + ("name","index", "maximum")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    @property
    def minimum(self):
        """Get/set minimum calibration value.
        This is the same as origin.
        """
        return self.origin
    
    @minimum.setter
    def minimum(self, val):
        self.origin = val
        
    @property
    def maximum(self):
        """Get/set the maximum calibration value
        """
        return self._data_.maximum
    
    @maximum.setter
    def maximum(self, val):
        if isinstance(val, (complex, float, int)):
            self._data_.maximum = val
            
        elif isinstance(val, pq.Quantity):
            if not units_convertible(val.units, self.units.units):
                raise TypeError(f"Maximum value units ({val.units}) incompatible with my units ({self.units.units})")
            
            if val.units != self.units.units:
                val = val.rescale(self.units.units)
                
            self._data_.maximum = quantity2scalar(val)
            
        elif isinstance(val, np.ndarray):
            self._data_.maximum = quantity2scalar(val)
            
        else:
            raise TypeError(f"Maximum value was expected as a scalar int, float, complex, Python Quantity or numpy array; got {type(val).__name__} instead")
        
    @property
    def calibratedMaximum(self):
        return self.maximum * self.units
            
    @property
    def name(self):
        return self._data_.name
    
    @name.setter
    def name(self, val:str):
        if isinstance(val, str) and len(val.strip()):
            self._data_.name = val
            
    @property
    def index(self):
        return self._data_.index
    
    @index.setter
    def index(self, val:int):
        if isinstance(val, int) and val >= 0:
            self._data_.index = val

class AxisCalibrationData(CalibrationData):
    """Atomic calibration data for an axis of a vigra.VigraArray.
    
    To be mapped to a vigra.AxisInfo key str in AxesCalibration, or to
    a key str with format "channel_X", in a parent AxisCalibrationData object
    for an axis of type Channels.
    
    The axis calibration is uniquely determined by the axis type (vigra.AxisType
    flags), axis name, units (Python Quantity object), origin and resolution 
    (Python numeric scalars).
    
    In addition an axis of type Channels will also associate an AxisCalibrationData
    object for each of its channels.
    
    NOTE: an AxisCalibrationData can be constructed by passing a vigra.AxisInfo
    object as sole parameter. However, the AxisInfo object will NOT be stored in 
    the newly create AxisCalibrationData object.
    
    """
    parameters = CalibrationData.parameters + ("type", "name", "key")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def __getitem__(self, key):
        if not isinstance(key, str):
            raise TypeError(f"Expecting a str; got {type(key).__name__} instead")
        
        if key in self._data_:
            return self._data_[key]
        
        raise KeyError(f"key {key} not found")
    
    def __setitem__(self, key, val):
        if not isinstance(key, str):
            raise TypeError(f"Expecting a str; got {type(key).__name__} instead")
        
        if key in self._data_:
            setattr(self, key, val)

    @property
    def name(self):
        """Get/set the axis name
        """
        return self._data_.name
    
    @name.setter
    def name(self, val:str):
        if isinstance(val, str) and len(val.strip()):
            self._data_["name"] = val
            #self._data_.name = val
            
    @property
    def key(self):
        """Get/set the axis type key
        """
        return self._data_.key
    
    @key.setter
    def key(self, val:str):
        if isinstance(val, str) and len(val.strip()):
            self._data_["key"] = val
            #self._data_.key = val
            
    @property
    def type(self):
        """Get/set the axis type flags
        WARNING: Setting this property will modify the other properties:
        'units', 'name', 'key', 'origin', and 'resolution'
        
        """
        return self._data_.type
    
    @type.setter
    def type(self, val:typing.Union[vigra.AxisType, int, str]):
        if isinstance(val, str):
            val = axisTypeFromString(val)
            
        if not isSpecificAxisType(val):
            raise TypeError(f"Incompatible axis type {val}")
        
        if val != self._data_.type:
            if val != vigra.AxisType.Channels and self._data_.type == vigra.AxisType.Channels:
                for c in self.channels:
                    self._data_.pop(c[0], None)
                #if len(list(self.channels)):
                    ## switch AWAY FROM Channels:
                    ## remove channels
                    #chcals = [k for k in self._data_ if k.startswith("channel")]
                    
                    #for k in chcals:
                        #self._data_.pop(k, None)
                        
            self._data_.type = val
            self._data_.units = axisTypeUnits(val)
            self._data_.name = axisTypeName(val)
            self._data_.key = axisTypeSymbol(val)
            
    @property
    def channels(self):
        """Returns a tuple of tuples with (name, ChannelCalibrationData) 
        
        WARNING: Excludes calibration data for virtual channel.
        
        In each tuple, the elements represent the symbol and the channel 
        calibration mapped to it, for non-virtual channels only, in this 
        AxisCalibrationData object.
        
        The symbol is not necessarily the name of the channel.
        
        VigraArray objects always have at least one channel. When the array
        lacks a defined Channels axis, the data itself constitutes a single 
        channel corresponding to a virtual Channels axis of size 1.
        
        Hence, the calibration data for a Channels axis will report either:
        
        * at least one calibration data for 'real' channels
        
        or:
        
        * one calibration data with default parameters for a 'virtual' channel.
        
        This property reports only the calibrations for 'real' channels, hence
        it may be an empty list.
        
        This behaviour is different from that of the `channelCalibrations`
        property where a virtual channel calibration is returned when no 'real'
        channel calibration data exists.
        
        For AxisCalibrationData corresponding to a non-Channels axis this 
        property is always an empty list.
        
        The setter expects a sequence of tuples (a,b) with:
        `a`:str = the field name that will be mapped to the ChannelCalibrationData
        `b`: ChannelCalibrationData or dict that can be used to construct a 
            ChannelCalibrationData
            
        The setter has no effect for a NonChannel axis
        """
        return tuple((k,v) for k,v in self._data_.items() if isinstance(v, ChannelCalibrationData))
        
    @channels.setter
    def channels(self, val:typing.Sequence[typing.Tuple[str, typing.Union[ChannelCalibrationData, dict]]]):
        if not self.type & vigra.AxisType.Channels:
            return
        
        for k,v in enumerate(val):
            if ChannelCalibrationData.isCalibration(v[1]):
                if isinstance(v[0], str) and len(v[0].strip()) and v[0] not in self.parameters:
                    field = v[0]
                else:
                    field = f"channel_{k}"
                    
                self._data_[field] = ChannelCalibrationData(v[1])
                
    @property
    def channelCalibrations(self):
        """A list of tuples (symbol, channel calibration).
        
        These INCLUDE the virtual channel when calibrations for real channels do
        not exist; hence,, for a channels-type axis, this property is always a 
        non-empty list. 
        
        To get the actual ('real') channel calibrations see `self.channels` 
        property.
        
        The setter of this property expects a tuple (str, ChannelCalibrationData)
        as for the `channels` property setter (it actualy delegates to the
        latter).
        """
        ret = tuple((k,v) for k, v in self._data_.items() if isinstance(v, ChannelCalibrationData))
        #ret = list((k,v) for v in self._data_.items() if isinstance(v, ChannelCalibrationData))
        
        if len(ret) == 0 and self.type == vigra.AxisType.Channels:
            cal = ChannelCalibrationData()
            cal.name = "virtual_channel_0"
            return (cal.name, cal)
        
        return ret
        
    @channelCalibrations.setter
    def channelCalibrations(self, val:typing.Sequence[typing.Tuple[str, typing.Union[ChannelCalibrationData, dict]]]):
        if not self.type & vigra.AxisType.Channels:
            return
        
        self.channels = val
        
    @property
    def channelNames(self):
        """A tuple of channel names, from their calibration data.
        These include the virtual channel (if it exists).
        
        This list is empty if the AxisCalibrationData corresponds to a 
        non-Channels axis.
        """
        return tuple(ch[1].name for ch in self.channelCalibrations)
        
    @property
    def channelIndices(self):
        """A tuple of channel indices, from their calibration data.
        These include the virtual channel (if it exists).
        
        This list is empty if the AxisCalibrationData corresponds to a 
        non-Channels axis.
        """
        return tuple(ch[1].index for ch in self.channelCalibrations)
        
    @property
    def nChannels(self) -> int:
        """Number of data channel along the axis.
        This is:
        0 for a non-Channels axis
        1 for a virtual Channels axis (VIGRA Arrays always have at least one
            channel even if there is no Channels axis)
        n >= 1 for a Channels axis with n channels (i.e. the array size along
            the Channels axis)
        To get the actual of channel calibrations (i.e. for non-virtual channels)
        use the `channels` property.
        
        
        """
        return len(self.channelCalibrations)
        
    @property
    def calibrationString(self):
        """
        An XML-formatted string with one of the following formats, depending on
        whether the axis is a Channels axis or not:
        
        1) For a non-channels axis:
        ----------------------------
        
        <axis_calibration>
            <type>int</type>
            <key>str</key>
            <name>str</name>
            <units>str</units>
            <origin>float</origin>
            <resolution>float</resolution>
        </axis_calibration>
        
        2) for a channel axis:
        ----------------------------
        
        <axis_calibration>
            <type>int</type>
            <key>str</key>
            <name>str</name>
            <channel_0>
                <index>int</index>
                <name>str</name>
                <units>str</units>
                <minimum>float|complex|int</minimum>
                <maximum>float|complex|int</maximum>
                <resolution>float</resolution>
            </channel_0>
            <channel_1>
                <index>int</index>
                <name>str</name>
                <units>str</units>
                <minimum>float|complex|int</minimum>
                <maximum>float|complex|int</maximum>
                <resolution>float</resolution>
            </channel_1>
            ... etc ...
        </axis_calibration>
        
        """
        
        def __gen_xml_element__(obj, param):
            value = getattr(obj._data_, param, None)
            
            ss = [f"<{param}>"]
            
            if isinstance(value, str): # ("name", "key")
                s = value
                
            elif param == "type":
              s = "|".join(axisTypeStrings(value))
            
            elif param == "units":
                # output the dimensionality's string property
                s = value.units.dimensionality.string
                
            elif param == "index":
                s = "%d" % value
                
            #elif param in ("origin", "resolution", "maximum", "minimum"):
                
            else: # ("origin", "resolution", "maximum", "minimum")
                s = "%f"%value
                
            ss.append(s)
            
            ss.append(f"</{param}>")
            
            return "".join(ss)

        strlist = ["<axis_calibration>"]
        
        for param in sorted(self.__class__.parameters):
            strlist.append(__gen_xml_element__(self, param))
            
        if self.type & vigra.AxisType.Channels:
            for ch in self.channels:
                # NOTE: 2021-11-08 11:35:19
                # only append channel info if there are channel calibrations
                if "virtual" not in ch[0]:
                    strlist.append(f"<{ch[0]}>")
                    for p in sorted(ChannelCalibrationData.parameters):
                        strlist.append(__gen_xml_element__(ch[1], p))
                    strlist.append(f"</{ch[0]}>")
                
        strlist.append("</axis_calibration>")
        
        return "".join(strlist)
    
    @property
    def axisInfo(self):
        """Dynamically generated vigra.AxisInfo object
        """
        
        return vigra.AxisInfo(key = vigra.AxisType(self.key), typeFlags = self.type, resolution=self.resolution, description=self.calibrationString)
        
    
    def addChannelCalibration(self, val:ChannelCalibrationData, 
                              name:typing.Optional[str]=None,
                              index:typing.Optional[int]=None):
        """Add/set ChannelCalibrationData
        
        NOTE: name is the name under which this channel calibration is stored
        in self.channelCalibrations (i.e. the 'key'). WARNING This is not
        necessarily the name of the channel (i.e., it is not necessarily the same
        as the 'name' field in the channel calibration data).
        
        WARNING: Raises an exception if this AxisCalibrationData instance already
        contains a ChannelCalibrationData mapped to the specified name, or with 
        the specified index.
        
        This is deliberate, to avoid overwriting ChannelCalibrationData objects
        already contained here.
        
        To modify a specific ChannelCalibrationData, access it using the symbol
        it is mapped to, its name, or its index.
        
        """
        if not self.type & vigra.AxisType.Channels:
            return
        
        if isinstance(val, str) and isinstance(name, ChannelCalibrationData):
            calname = val
            val = name
            name = calname
            if len(name.strip()) == 0:
                name = None
            
        if not isinstance(val, ChannelCalibrationData):
            raise TypeError(f"Expecting a ChannelCalibrationData; got {type(val).__name__} instead")
        
        name = name or val.name
        
        index = index or val.index
        
        if name in self.parameters:
            name = f"channel_{name}"
            
        if name in self and isinstance(self[name], ChannelCalibrationData):
            raise ArgumentError(f"This {self.__class__.__name__} instance already contains a Channel calibration data mapped to {name}")

        if index in self:
            raise ArgumentError(f"This {self.__class__.__name__} instance already contains a Channel calibration data with index {index}")
        
        if index != val.index:
            val.index = index
            
        self._data_[name] = val
        
    def removeChannelCalibration(self, index:typing.Union[int, str]) -> typing.Union[ChannelCalibrationData]:
        """Removes ChannelCalibrationData for channel with specified index or name.
        
        Returns the ChannelCalibrationData, if found, else None.
        
        """
        chcal = self.getChannelCalibration(index, True)
        if chcal is None:
            return
        
        return self._data_.pop(chcal[0], None)
    
    def reindexChannels(self, index:typing.Optional[dict]=None) -> None:
        """Reindexes the channels
        Does nothing for a NonChannel axis or without ChannelCalibrationData.
        
        Parameters:
        ==========
        
        index:dict (optional, default is None) - reindexing map
        
            When None, the channel indices are assigned to increasing order from
            0, in the order of their ChannelCalibrationData
            
            When a dict this maps int keys (old index) to int values (new index).
            
            WARNING: The values in the reindexing map must be >= 0 and unique
        
        """
        
        if not self.type & vigra.AxisType.Channels or len(list(self.channels)) == 0:
            return
        
        if isinstance(index, dict):
            if not all(all(isinstance(i, int) for i in (k,v)) for k,v in index.items()):
                raise TypeError("Reindexing map must have int keys and values")
            
            if any(v < 0 for v in index.values()):
                raise ValueError("Reindexing map cannot have negative values")
            
            old_indices = list(k for k in index) # these are unique by default
            new_indices = list(unique(v for v in index.values()))
            
            if len(new_indices) < len(old_indices):
                raise TypeError("The reindexing map contains duplicate values")
            
            for chcal in self.channels:
                if chcal.index in index:
                    chcal.index = index[chcal]
                    
        else:
            for k, chcal in enumerate(self.channels):
                chcal.index = k
                
    def sortedChannels(self, by_index:typing.Union[bool,str]=True):
        """Yields ChannelCalibrationData sorted by chanel index, name or field.
        
        by_index: bool or str
            When bool: if True, sort by index; else sort by name
            
            When by_index is a str, it indicates the field name to sort.
            
            CAUTION: When sorting by units, all chanels must have unist with the
            same dimensionalities, or convertible to each other.
            
        """
        yield from sorted(self.channels, key = lambda x: x.by_index if instance(by_index, str) else x.index if by_index is True else x.name)
        
    def clearChannels(self):
        """Removes all ChannelCalibrationData associated with this object.
        """
        if not self.type & vigra.AxisType.Channels:
            return
        
        for (k,c) in self.channels:
            self._data_.pop(k, None)
                
    def getChannelCalibration(self, index:typing.Optional[typing.Union[int, str]]=None, full:typing.Optional[bool]=False) -> typing.Optional[typing.Union[list, ChannelCalibrationData]]:
        """ChannelCalibrationData for a single channel.
        
        Parameters:
        ==========
        index: str or int; optional default is None.
            When a str, this is the channel name as in the ChannelCalibrationData
            'name' field, if it exists; failing that, 'name' will be matched 
            against the symbols mapped to ChannelCalibrationData in this 
            AxisCalibrationData object.
            
            When an int, this is the channel index as in the ChannelCalibrationData
            'index' field.
            
            When None, this will return the first available channel calibration
            data, if any, in the insertion order of the symbols to which channel
            calibration data are bound, in this AxisCalibrationData object.
            
        full:bool, optional (default is False)
            When True, also returns the name (symbol) to which the 
            ChannelCalibrationData objects is bound, in this AxisCalibrationData
            
            For a virtual channels axis (see below) the name (symbol) is set to 
            "virtual_channel_0"
        
        Returns:
        ========
        A ChannelCalibrationData or tuple (str, ChannelCalibrationData) if 'full'
            is True

        WARNING: For a virtual channels axis the calibration data is a default
        one, created dynamically; subsequent changes to the returned channel
        calibration data will not be stored in this AxisCalibrationData object,
        unless the channel calibration data is explicitly added to this object.
        
        Returns None for non-Channels axis, or when no channel calibration data
        was found using the supplied index value.
        
        """
        if not self.type & vigra.AxisType.Channels:
            return
        
        if len(self.channelCalibrations) == 0:
            cal = ChannelCalibrationData()
            cal.name = "virtual_channel_0"
            if full:
                return (cal.name, cal)
            return cal
        
        if index is None:
            if full:
                return self.channelCalibrations[0]
            return self.channelCalibrations[0][1]
            
        if isinstance(index, int):
            what = "index"
            
        elif isinstance(index, str):
            what = "name"
            
        else:
            raise TypeError(f"Expecting a str, int or None; got {type(index).__name__} instead.")
        
        # NOTE: 2022-01-07 00:12:54
        # 1) search by calibration name or index
        chcal = list(filter(lambda x: getattr(x[1], what, None) == index, self.channels))
        
        if len(chcal) == 0:
            if what == "name":
                chcal = list(filter(lambda x: x[0]==name, self.channels))
                
        if len(chcal) > 1:
            warnings.warn(f"There is more than one channel with the same {what} ({index}).\nThe calibration for the first one will be returned", 
                        RuntimeWarning, 
                        stacklevel=2)
            chcal = chcal[0]
            
        #print(f"AxisCalibrationData.getChannelCalibration: chcal = {chcal}")
            
        if len(chcal):
            if full:
                return chcal
        
            else:
                return chcal[0]
            
    def getChannelIndex(self, name:str) -> typing.Optional[int]:
        """Returns the index of the channel with given name.
        
        Parameters:
        ==========
        
        name: str; must not be empty or contain only blanks
        
        The comparison is made against ChannelCalibrationData.name
        
        Returns:
        ========
        
        int: the value of ChannelCalibrationData.index where 
                ChannelCalibrationData.name is name, or None if not found
                
        Returns None for NonChannel axis or when specified channel was not found
        
        """
        if not self.type & vigra.AxisType.Channels:
            return
        
        if not isinstance(name, str) or len(name.strip()) == 0:
            return 
        
        chcal = self.getChannelCalibration(name)
        return chcal.index
        
    def setChannelIndex(self, name:str, val:int) -> None:
        """Sets the index of the channel with given name.
        
        Parameters:
        ==========
        name: str ;  the ChannelCalibrationData name for the channel
        val : int - if empty or contain only blanks it will be ignored
            
        Does nothing for a NonChannel axis
        """
        if not self.type & vigra.AxisType.Channels:
            return
        
        if name not in self:
            raise IndexError(f"This {self.__class__.__name__} instance does not have a channel calibration named {name} or mapped to {name}")
        
        if not isinstance(val, int):
            raise TypeError(f"index must be an int; got {type(val).__name__} instead")
        
        if val < 0:
            raise ValueError(f"index must be >= 0; got {val} instead")
        
        chcal = self.getChannelCalibration(name)
        isvirtual = "virtual" in chcal.name
        chcal.index = val
            
        if isvirtual:
            chcal.name = "channel_0"
            self.addChannelCalibration(chcal, chcal.name)
            
    def getChannelName(self, index:int) -> typing.Optional[str]:
        """Returns the name of the channel with given index.
        
        Parameters:
        ==========
        index: int ;  the ChannelCalibrationData.index value for the channel
        
        Returns:
        ========
        str: the value of ChannelCalibrationData.name where 
                ChannelCalibrationData.index is index, 
                
        Returns None for NonChannel axis or when specified channel was not found
        
        """
        if self.type == vigra.AxisType.Channels:
            chcal = self.getChannelCalibration(index)
            return chcal.name
        
    def setChannelName(self, index:int, val:str) -> None: # ensure_unique:bool = True) -> None:
        """Sets the name of the channel with given index.
        
        Parameters:
        ==========
        index: int ;  the ChannelCalibrationData.index value for the channel
            WARNING This is NOT necessarily the running index of the channel in
            the associated image
            
        val : str - ignored if empty or containing only blanks
        ensure_unique: bool, optional (default is True)
            Avoid duplicate channel names. 
            
        Does nothing for a NonChannel axis.
        """
        if not self.type & vigra.AxisType.Channels:
            return
        
        if isinstance(val, str) and len(val.strip()): # avoid empty names
            chcal = self.getChannelCalibration(index)
            if chcal is None:
                return
            isvirtual = "virtual" in chcal.name
            chcal.name = val
            if isvirtual: # a virtual channel calibration -> make it a real one
                self.addChannelCalibration(chcal, chcal.name)
            
    def getChannelMinimum(self, index:typing.Union[int, str]) -> typing.Union[complex, float, int]:
        if not self.type & vigra.AxisType.Channels:
            return
        
        chcal = self.getChannelCalibration(index)
        
        return chcal.minimum
        
    def setChannelMinimum(self, index:typing.Union[int, str], 
                          val:typing.Union[complex, float, int, np.ndarray]) -> None:
        if not self.type & vigra.AxisType.Channels:
            return
        
        chcal = self.getChannelCalibration(index)
        chcal.minimum = val
        if "virtual" in chcal.name:
            chcal.name = "channel_0"
            self.addChannelCalibration(chcal, "channel_0")
        
        
    def getChannelMaximum(self, index:typing.Union[int, str]):
        if not self.type & vigra.AxisType.Channels:
            return
        chcal = self.getChannelCalibration(index)
        
        return chcal.maximum
        
    def setChannelMaximum(self, index:typing.Union[int, str], 
                          val:typing.Union[complex, float, int, np.ndarray]) -> None:
        
        if not self.type & vigra.AxisType.Channels:
            return
        
        chcal = self.getChannelCalibration(index)
        isvirtual = "virtual" in chcal.name
        chcal.maximum = val
        if isvirtual:
            chcal.name = "channel_0"
            self.addChannelCalibration(chcal, chcal.name)
        
    def getChannelResolution(self, index:typing.Union[int, str]):
        chcal = self.getChannelCalibration(index)
        if "virtual" in chcal.name:
            chcal.name = "channel_0"
            self.addChannelCalibration(chcal, "channel_0")

        return chcal.resolution
        
    def setChannelResolution(self, index:typing.Union[int, str], 
                             al:typing.Union[complex, float, int, np.ndarray]) -> None:
        if not self.type & vigra.AxisType.Channels:
            return
        
        chcal = self.getChannelCalibration(index)
        isvirtual = "virtual" in chcal.name
        chcal.resolution = val
        if isvirtual:
            chcal.name = "channel_0"
            self.addChannelCalibration(chcal, chcal.name)
        
        
    def getChannelUnits(self, index:typing.Union[int, str]) -> typing.Optional[pq.Quantity]:
        """Returns the units of the specified channel, or None if not found
        """
        chcal = self.getChannelCalibration(index)
        if chcal is None:
            #warnings.warn(f"No channel {index} was found")
            return
        
        return chcal.units
    
    def setChannelUnits(self, index:typing.Union[int, str], 
                        val:typing.Union[pq.Quantity, pq.dimensionality.Dimensionality, str]) -> None:
        if not self.type & vigra.AxisType.Channels:
            return
        
        chcal = self.getChannelCalibration(index)
        isvirtual = "virtual" in chcal.name
        chcal.units = val
        
        if isvirtual:
            chcal.name = "channel_0"
            self.addChannelCalibration(chcal, chcal.name)
        
    def calibrateAxis(self, axinfo:typing.Optional[vigra.AxisInfo]=None) -> None:
        """Associates calibration values with a vigra.AxisInfo object.
        
        This method does the following:
        
        1) If the 'type' and 'key' properties of the calibration data are 
        identical, respectively, to the 'typeFlags' and 'key' attributes of the 
        AxisInfo object:
        
            * assigns the value of the calibration data 'resolution' property to
            the 'resolution' attribute of the AxisInfo obejct,
            
            * embeds the calibration string of this calibration data in the 
            'description' attribute of the AxisInfo object.
            
            
        2) If the AxisInfo 'typeFlags' or 'key' are different, respectively, to
        this calibration 'type' and 'key' properties:
        
            * creates a NEW AxisInfo object with 'typeFlags', 'key', 'resolution'
            and 'description' attributes set according to this calibration data.
            
        3) If axinfo object is None, creates a new vigra.AxisInfo object 
        according to this calibration values and returns it.
        
        Returns:
        ========
        An updated (possibly, new) vigra.AxisInfo object.
        
        NOTE 1:
        For a vigra.AxisInfo object, the attributes 'typeFlags' and 'key' are
        immutable. The only read/write attributes of an AxisInfo object are
        'resolution' (float) and 'description' (str).
        
        NOTE 2:
        A) The returned object is a reference to the vigra.AxisInfo 'axinfo'
        parameter ONLY when the 'typeFlags' and 'key' attributes of 'axinfo' are
        are identical, respectively, to the 'type' and 'key' properties of this
        AxisCalibrationData object.
        
        B) In all other cases the method returns a NEW vigra.AxisInfo object.
        
        This means that the following expression (where 'axcal' is an 
        AxisCalibrationData object, and 'img' is a vigra.VigraArray):
        
            `axcal.calibrateAxis(img.axistags[0])`
        
        will ONLY change img.axistags[0] when 'axcal' has identical 'type' and 
        'key' as img.axistasg[0]
        
        The workaround for the case when 'axcal' would change the axis type 
        flags and/or key is:
        
            `img.axistags[0] = axcal.calibrateAxis(img.axistags[0])`
            
        NOTE 3:
        Changes to the VigraArray.axistags are persistent throughout the 
        life-time of the VigraArray object.
        
        However, the axistags are NOT saved alongside the VigraArray (image) 
        data when the target file format is a common one (such as TIFF, PNG, 
        JPEG, etc). The only formats that support persistent axis calibration 
        data (and supported in Scipyen) are HDF5 files (see vigra.impex module
        and Scipyen's core.iolib.h5io module).
            
        """
        if axinfo is None:
            return vigra.AxisInfo(key=self.key, 
                                  typeFlags=self.type,
                                  resolution=self.resolution,
                                  description=self.calibrationString)
        
        if not isinstance(axinfo, vigra.AxisInfo):
            raise TypeError(f"'axinfo' expected to be a vigra.AxisInfo object; got {type(axinfo).__name__} instead")
        
        if axinfo.typeFlags != self.type or axinfo.key != self.key:
            return vigra.AxisInfo(key = self.key, typeFlags = vigra.AxisType(self.type), resolution=self.resolution, description=self.calibrationString)
            
        axinfo = self._embedCalibrationString_(self.calibrationString, axinfo)
        axinfo.resolution = self.resolution
        return axinfo
    
    @staticmethod
    def findCalibrationString(s:str):
        """Returns the coordinates (start & stop) of an XML-formatted calibration
        sub-string of 's' or None if 's' does not contain an XML-formatted 
        calibration sub-string.
        
        """
        start = s.find("<axis_calibration>")
        if start > -1:
            stop = s.rfind("</axis_calibration>") 
            if stop > -1:
                stop += len("</axis_calibration>")
            else:
                stop = start + len("<axis_calibration>")
            return (start, stop)
        
    @staticmethod
    def fromAxisInfoDescription(axinfo:vigra.AxisInfo) -> AxisCalibrationDataType:
        if not isinstance(axinfo, vigra.AxisInfo):
            raise TypeError(f"'axinfo' expected to be a vigra.AxisInfo object; got {type(axinfo).__name__} instead ")
        
        cal_str_start_stop = AxisCalibrationData.findCalibrationString(axinfo.description)
        if cal_str_start_stop is None:
            return AxisCalibrationData(axinfo)
        else:
            cal_str = axinfo.description[cal_str_start_stop[0]:cal_str_start_stop[1]]
            return AxisCalibrationData.fromCalibrationString(cal_str)
        
        
    @staticmethod
    def removeCalibrationString(s:str) -> str:
        start_stop = AxisCalibrationData.findCalibrationString(s)
        
        while start_stop is not None:
            s = s[0:start_stop[0]] + s[start_stop[1]:]
            start_stop = AxisCalibrationData.findCalibrationString(s)
            
        return s
    
    @staticmethod
    def _embedCalibrationString_(s:str, axinfo:vigra.AxisInfo):
        """Embeds calibration sub-string in 's' into a vigra.AxisInfo object.
        
        Does nothing if 's' does not contain an XML-format calibration string.
        
        WARNING, CAUTION: This method does NOT check if the calibration string
        has appropriate values given the typeflags of the axinfo Object.
        
        Parameters:
        ===========
        s:str - should contain an XML-formatted calibration sub-string; otherwise
            the method has no effect
        
        axinfo: vigra.AxisInfo object; the calibration (sub) string in 's' will be
            embedded in the axinfo's 'description' attribute
        
        Returns:
        ========
        vigra.AxisInfo: this is a reference to the vigra.AxisInfo object passed
            as the 'axinfo' parameter
        
        """
        if not isinstance(s, str):
            raise TypeError(f"Expecting a str; got {type(s).__name__} instead")
            
        if not isinstance(axinfo, vigra.AxisInfo):
            raise TypeError(f"Expecting a vigra.AxisInfo object; got {type(axinfo).__name__} instead")

        
        start_stop = AxisCalibrationData.findCalibrationString(s)
        
        if start_stop is None:
            return
        
        cal_str = s[start_stop[0]:start_stop[1]]
        
        description = AxisCalibrationData.removeCalibrationString(axinfo.description)
        
        description += f" {cal_str}"
        
        axinfo.description = description
        
        return axinfo # for convenience
            
    
    @staticmethod
    def fromCalibrationString(s:str) -> AxisCalibrationDataType:
        """AxisCalibrationData factory using a calibration string.
        
        For the structure of an XML-formatted calibration string see the
        documentaiton for the AxisCalibrationData.calibrationString property.
        
        Parameters:
        ==========
        
        s: str = XML-formatted calibration string (see documentation for
        AxisCalibrationData.calibrationString property)
        
        Returns:
        ========
        An AxisCalibrationData instance. 
            This either a reference to the AxisCalibrationData object passed as
            the 'cal' parameter, or a new AxisCalibrationData object, otherwise.
            
            When 's' is a string containing an XML-formatted calibration string 
            (see AxisCalibrationData.calibrationString()), the returned value
            (and 'cal', if passed) will be updated with the calibration values
            parsed from the string in 's'. Otherwise, the returned value is the
            original value of 'cal' (if 'cal' is an AxisCalibrationData object) 
            or a new, 'default' AxisCalibrationData object (as for an axis with 
            type flags UnknownAxisType).
        
        """
        import xml.etree.ElementTree as ET
        
        def __eval_xml_element_text__(param, txt):
            if param == "units":
                value = unit_quantity_from_name_or_symbol(txt)
            elif param in ("key", "name"):
                value = txt
            elif param == "type":
                value = axisTypeFromString(txt)
            else: # ("index", "origin", "resolution", "minimum", "maximum")
                if "nan" in txt:
                    value = np.nan
                else:
                    value = eval(txt)
                
            return value
        
        cal = AxisCalibrationData()
        
        if not isinstance(s,str) or len(s.strip()) == 0 or not s.startswith("<axis_calibration>") or not s.endswith("</axis_calibration>"):
            raise ValueError("This is not an axis calibration string")
            
        # OK, now extract the relevant xml string
        try:
            cal_xml_element = ET.fromstring(s)
            
            # make sure we're OK
            if cal_xml_element.tag != "axis_calibration":
                raise ValueError("Wrong element tag; was expecting 'axis_calibration', instead got %s" % element.tag)
            
            # see NOTE: 2021-10-09 23:58:58
            # xml.etree.ElementTree.Element.getchildren() is absent in Python 3.9.7
            element_children = getXMLChildren(cal_xml_element) # getXMLChildren defined in xmlutils
            
            for child_element in element_children:
                # these can be <children_X> tags (X is a 0-based index) or a <name> tag
                # ignore everything else
                if child_element.tag.lower() in AxisCalibrationData.parameters:
                    param = child_element.tag.lower()
                    txt = child_element.text
                    setattr(cal, param, __eval_xml_element_text__(param, txt))
                    
                else:
                    chcaldict = dict() # = ChannelCalibrationData()
                    chcalname = child_element.tag.lower()
                    ch_children = getXMLChildren(child_element)
                    ch_tags = dict((c.tag, c.text) for c in ch_children)
                    for param in ChannelCalibrationData.parameters:
                        if param in ch_tags:
                            value = __eval_xml_element_text__(param, ch_tags[param])
                            chcaldict[param] = value
                            
                    if len(chcaldict):
                        chcal = ChannelCalibrationData(**chcaldict)
                        cal.addChannelCalibration(chcal, name=chcal.name)
                            
        except Exception as e:
            traceback.print_exc()
            print("cannot parse calibration string %s" % calibration_string)
            raise e
            
        return cal
            

class AxesCalibration(object):
    """Encapsulates calibration of a set of axes.
    
    Associates physical units (and names) to a vigra array axis.
    
    An axes calibration for a VigraArray is uniquely determined by the axis type
    and the attributes 'name', 'units', 'origin', and 'resolution', for each 
    AxisInfo object attached to the VigraArray.
    
    VigraArray axes calibrations are encapsulated in AxisCalibrationData objects.
    
    In addition, for the calirbation for a Channels axis contains
    ChannelCalibrationData for each channel defined along the axis.
    
    Quick reminder on vigra.AxisTags, vigra.AxisInfo, and vigra.AxisType objects:
    ----------------------------------------------------------------------------
    
    AxisTags: describes the axis properties AND ordering in a VigraArray
        * constructed from a sequence of AxisInfo objects
        * minimal iterable interface 
            e.g. let data.axistags an AxisTags object:
            
            `(a for a in data.axistags)` iterates through the AxisInfo objects in 
                the AxisTags object)
            
            `data.axistags[k]` with `k` an `int` OR a `str`
                when `k` is an `int` AND `0 <= k < len(data.axistags)` or `0 <= k < data.ndim`
                    returns the k_th AxisInfo object
                    
                when `k` is a `str` AND is a KEY of an AxisInfo objects contained
                in the `data.axistags`
                    returns the AxisInfo object with `key == k`
                    
            `data.axistags.index(k)`
                where `k` is a `str`:
                    returns the `int` index of the AxisInfo with `key == k`
                    
                if an AxisInfo object with `key == k` is NOT found, returns 
                `data.ndim`
            
    AxisInfo: describes a SINGLE axis.
        Relevant attributes (dot access):
        
        `key`: `str` - values are from the standard set prescribed by vigranumpy,
            and enhanced by Scipyen in `imaging.axisutils.axisTypeflags`
        
        `resolution`: `float`
        `description`: `str`
        
        Read-only:
        `typeFlags`: vigra.AxisType
        
    AxisType: enum type encoding the type of the axis described by an AxisInfo.
    
    """

    def __init__(self, *args):
        """
        Var-positional parameters:
        ==========================
        *args = a vigra.VigraArray, a vigra.AxisTags, up to to five 
                vigra.AxisInfo, XML-formatted calibration strings or 
                AxisCalibrationData objects.
                
        NOTE: 
        The AxisInfo objects used in the AxesCalibraiton's initialization WILL
        NOT gain a calibration string in their `description` attribute (i.e., 
        the AxisInfo will not be automatically 'calibrated').
            
        The user of the AxesCalibration object must call its 'calibrateAxes()'
        method in order to embed an XML-formatted calibration string into
        the AxisInfo `description` attribute.
        
        
        """
        
        self.relative_tolerance = RELATIVE_TOLERANCE
        self.absolute_tolerance = ABSOLUTE_TOLERANCE
        self.equal_nan = EQUAL_NAN
        
        # NOTE 2021-10-25 10:27:54
        # keep this as a LIST - this to allow several axes with the same 
        # typeFlags (and key).
        self._calibration_ = list()
        
        if len(args) == 1 and isinstance(args[0], (tuple, list , deque)):
            args = args[0]
        
        if len(args):
            if isinstance(args[0], vigra.VigraArray):
                self._axistags_ = args[0].axistags
                
                self._calibration_ = [AxisCalibrationData(axinfo) for axinfo in args[0].axistags]
                
                #set up channel calibrations with default values:
                if args[0].channelIndex != args[0].ndim: # real channel axis exists
                    chax_index = args[0].axistags.index("c")
                    # Make sure we don't overwrite existing channel calibrations
                    if len(self._calibration_[chax_index].channels) < args[0].channels:
                        for k in range(len(self._calibration_[chax_index].channels), args[0].channels):
                            self._calibration_[chax_index].addChannelCalibration(ChannelCalibrationData(name=f"channel_{k}", index=k), name=f"channel_{k}")
                    elif len(self._calibration_[chax_index].channels) > args[0].channels:
                        extra = list()
                        for k in range(args[0].channels, len(self._calibration_[chax_index].channels)):
                            extra.append(self._calibration_[chax_index].channels[k])
                            
                        for k,c in extra:
                            self._calibration_[chax_index]._data_.pop(k, None)
                
                return

            elif isinstance(args[0], vigra.AxisTags):
                self._axistags_ = args[0]
                
                self._calibration_ = [AxisCalibrationData(axinfo) for axinfo in args[0]]
            
                # the AxisInfo objects MUST be calibrated maunally (the
                # AxisCalibrationData c'tor does NOT do this automatically)
                #for k, axinfo in enumerate(self._axistags_):
                    #self._calibration_[k].calibrateAxis(axinfo)
                    
                return
            
            elif isinstance(args[0], int):
                # NOTE: 2021-10-25 10:25:39
                # here we use the strategy in vigra.AxisTags constructor: an int
                # indicates HOW MANY axes are there, and therefore NOT an axis 
                # type flag
                if args[0] <= 0:
                    raise ValueError(f"Cannot create an AxesCalibration object for {args[0]} axes")
                
                self._axistags_ = vigra.AxisTags(args[0])
                
                self._calibration_ = [AxisCalibrationData(axinfo) for axinfo in self._axistags_]
                
                # the AxisInfo objects MUST be calibrated maunally (the
                # AxisCalibrationData c'tor does NOT do this automatically)
                #for k, axinfo in enumerate(self._axistags_):
                    #self._calibration_[k].calibrateAxis(axinfo)
                    
                return
                    
            else:
                # NOTE: 2021-10-25 10:44:30
                # The vigra.AxisTags constructor takes up to five individual 
                # AxisInfo objects (as a comma-separated sequence of parameters), 
                # a sequence of AxisInfo objects, an int, or no parameter. 
                #
                # The last three cases allow the creation of axistags for arrays
                # of arbitrary number of dimensions (the no-parameter case 
                # creates an empty array to which AxisInfo objects can be
                # appended).
                #
                self._axistags_ = vigra.AxisTags()
                for k, arg in enumerate(args):
                    if isinstance(arg, vigra.AxisInfo):
                        cal = AxisCalibrationData(arg)
                        #cal.calibrateAxis(arg) # MUST calibrate AxisInfo manually
                        self._axistags_.append(arg)
                        self._calibration_.append(cal)
                                        
                    elif isinstance(arg, str):
                        try:
                            cal = AxisCalibrationData(arg)
                        except:
                            cal = AxisCalibrationData() #  create default UnknownAxisType
                            
                        #self._axistags_.append(cal.axisInfo) 
                        self._calibration_.append(cal)
                        
                    elif isinstance(arg, AxisCalibrationData):
                        #self._axistags_.append(arg.axisInfo) 
                        self._calibration_.append(arg)
                        
                    else:
                        if k == 0:
                            raise TypeError(f"Expecting a vigra.VigraArray, vigra.AxisTags, vigra.AxisInfo, str, int, AxisCalibrationData or a sequence of these; got {type(arg).__name} instead")
                        else:
                            raise TypeError(f"{k}th argument is not a vigra.AxisInfo, str or AxisCalibrationData")
                        

        if not self.__check_cal_axinfo__():
            raise RuntimeError("Axis calibration data is inconsistent with axis info objects")
        
    def __check_cal_axinfo__(self):
        ret = len(self._axistags_) == len(self._calibration_)
        
        if ret:
            ret &= all(cal.key in self._axistags_ for cal in self._calibration_)
            
        if ret:
            calkeys = (cal.key for cal in self._calibration_)
            ret &= all(axinfo.key in calkeys for axinfo in self._axistags_)
            
        return ret
        
    def __iter__(self):
        """Iterates through the AxisCalibrationData objects contained within self
        """
        yield from (cal for cal in self._calibration_ if cal.key in self._axistags_)
        #yield from (cal.key for cal in self._calibration_ if cal.key in self._axistags_)
        
    def __contains__(self, item):
        """Membership test.
        item: CalibrationData, str (calibration key or name), or type flag 
            (int or vigra.AxisType)
        """
        if isinstance(item, str):
            return any(item in (getattr(cal, "key", None), getattr(cal, "name", None)) for cal in self._calibration_)
        
        elif isinstance(item, (int, vigra.AxisType)):
            return item in (getattr(cal, "type", None) for cal in self._calibration_)
        
        elif isinstance(item, CalibrationData):
            return item in self._calibration_
        
        return False
     
    def __getitem__(self, index:typing.Union[int, slice, range, str, vigra.AxisInfo]) -> typing.Union[AxisCalibrationData, typing.List[AxisCalibrationData]]:
        """Indexed access to the AxisCalibrationData for an axis.
        
        Parameters:
        ===========
        index:
                int, slice, range => return the AxisCalibrationData at index
                
                str: axis key or name
                    returns the first AxisCalibrationData found, having
                    name == index; failing that, returns the first 
                    AxisCalibrationData found, having key == index; when this
                    also fails raises IndexError
                    
                    If key is "c" and there is no Channel axis calibration, 
                    returns  a default AxisCalibrationData("c") with 
                    ChannelCalibrationData for the 'virtual' channel 0
                    
                    This behaviour emulates that of vigra.AxisTags.
                    
        NOTE
        A VigraArray (and by extension, an AxesCalibration object) can 
        theoretically contain several axes with the same key.
            
        To obtain ALL the axes with a given key,  use the idiom:
        
            `[cal for cal in axcal.calibrations if cal.key == key]`
        
        where `axcal` is an AxesCalibration object.
            
        """
        if isinstance(index, vigra.AxisInfo):
            index = index.key # a str
            
        if isinstance(index, (int, slice, range)):
            return self._calibration_[index] # raises IndexError if inappropriate
        
        elif isinstance(index, str):
            if index in self:
                ret = [cal for cal in self._calibration_ if index in (cal.name, cal.key)]
                if len(ret):
                    return ret[0]
                
                raise IndexError(f"Calibration for axis {index} not found")
                    
            elif index =="c": # Channels axis - not found in condition above so it's virtual
                return AxisCalibrationData("c")
            
            else:
                raise IndexError(f"Calibration for axis {index} not found")
            
    def __setitem__(self, index, obj):
        """Indexed setter.
        index: int
        obj: AxisCalibrationData object 
        """

        if isinstance(index, int):
            if not isinstance(obj, AxisCalibrationData):
                raise TypeError(f"Expecting an AxisCalibrationData object; got {type(obj).__name__} instead")

            self._calibration_[item] = obj # raises corresponding exception for list API
            self._axistags_[item] = obj.axisInfo
            
        else:
            raise TypeError(f"Index must eb an int; got {type(index).__name} instead")
        
    def __len__(self):
        return len(self._calibration_)
    
    def index(self, item:typing.Union[int, str]):
        """
        item: AxisCalibrationData, or str (key or name)
            When a str, returns the first AxisCalibrationData with key == index
            
            When item is 'c' returns the number of axes when no Channels axis exists
        """
        if isinstance(item, AxisCalibrationData):
            return self._calibration_.index(item) # raises appropriate exception for list API
        
        elif isinstance(item, str):
            ret = [k for k, c in enumerate(self._calibration_) if c.key == item ]
            if len(ret):
                return ret[0]
            else:
                if item == "c":
                    return len(self)
                raise KeyError(f"AxisCalibrationData for axis {item} not found")
            
    def isclose(self, other, key, channel = 0, ignore=None, 
                   rtol = RELATIVE_TOLERANCE, 
                   atol =  ABSOLUTE_TOLERANCE, 
                   equal_nan = EQUAL_NAN):
        """Compares calibration items between two axes, each calibrated by two AxesCalibration objects.
        
        AxesCalibration objects are considered similar if:
        1) the underlying axes are of the same type
        
        2) they have compatible units (meaning that their units can be easily 
            converted to each other)
            
        3) have numerically close origins and resolutions, whereby "numerically
            close" means their floating point values are within a prescribed 
            tolerance (see numpy.isclose(...) for details)
            
        4) for channel axes, clauses (2) and (3) hold for each channel
        
        These criteria can be relaxed using the "skip" parameter (see below)
        
        The description and name are deliberately NOT compared, as they are not
        considered unique determinants of the calibration.
        
        To compare objects using standard python semantics use the "==" binary operator
        
        Positional parameter:
        =====================
        
        other: AxesCalibration object
        
        Named parameters:
        =================
        
        ignore (default is None): What (if any) calibration properties may be ignored.
            Acceptable values are None or one of the following string keywords:
            "origin"
            "resolution"
            "units"
             or the sequence with any of these keywords
            
            
            
        rtol, atol, equal_nan: passed directly to numpy.isclose(...); See numpy.isclose(...) for details
        
        
        
        """
        
        if not isinstance(other, AxesCalibration):
            raise TypeError("Expecting an AxesCalibration object; got %s instead" % type(other).__name__)
        
        if isinstance(key, vigra.AxisInfo):
            key = key.key
            
        if not self.hasAxis(key):
            raise KeyError("Axis key %s not found in this object" % key)
        
        if not other.hasAxis(key):
            raise KeyError("Axis key %s not found in the object compared against" % key)
        
        if not self.axistags[key].compatible(other.axistags[key]):
            raise ValueError("The two axes are not type-compatible, although they have the same key")
        
        ignoreOrigin=False
        ignoreResolution=False
        ignoreUnits = False
        
        if isinstance(ignore, str) and ignore.lower() in ["units", "origin", "resolution"]:
            if ignore.lower() == "origin":
                ignoreOrigin = True
                
            elif ignore.lower() == "resolution":
                ignoreResolution = True
                
            elif ignore.lower() == "units":
                ignoreUnits = True
            
        elif isinstance(ignore, (tuple, list)) and all([isinstance(s, str) for s in ignore]):
            sk = [s.lower() for s in ignore]
            
            if "origin" in sk:
                ignoreOrigin = True
                
            if "resolution" in sk:
                ignoreResolution = True
                
            if "units" in sk:
                ignoreUnits = True
        
        result = self.getAxisType(key) == other.getAxisType(key)
        
        if result and not ignoreUnits:
            units_compatible = other.getUnits(key) == self.getUnits(key)
            
            if not units_compatible:
                self_dim    = pq.quantity.validate_dimensionality(self.getUnits(key))
                
                other_dim   = pq.quantity.validate_dimensionality(other.getUnits(key))
                
                if self_dim != other_dim:
                    try:
                        cf = pq.quantity.get_conversion_factor(other_dim, self_dim)
                        units_compatible = True
                        
                    except AssertionError:
                        units_compatible = False
                        
                else:
                    units_compatible = True
                    
            result &= units_compatible
        
        if result and not ignoreOrigin:
            result &= np.isclose(self.getDimensionlessOrigin(key), other.getDimensionlessOrigin(key), 
                                 rtol=rtol, atol=atol, equal_nan=equal_nan)
            
        if result and not ignoreResolution:
            result &= np.isclose(self.getDimensionlessResolution(key), other.getDimensionlessResolution(key),
                                 rtol=rtol, atol=atol, equal_nan=equal_nan)
            
        if result:
            if self.getAxisType(key) & vigra.AxisType.Channels > 0:
                result &= self.numberOfChannels() == other.numberOfChannels() # check if they have the same number of channels
                
                if result:
                    for chIndex in range(len(self.channelIndices(key))):
                        if not ignoreUnits:
                            channel_units_compatible = self.getUnits(key, self.channelIndices(key)[str(chIndex)]) == other.getUnits(key, other.channelIndices(key)[str(chIndex)])
                            if not channel_units_compatible:
                                self_dim = pq.quantity.validate_dimensionality(self.getUnits(key, self.channelIndices(key)[chIndex]))
                                other_dim = pq.quantity.validate_dimensionality(other.getUnits(key, other.channelIndices(key)[chIndex]))
                                
                                if self_dim != other_dim:
                                    try:
                                        cf = pq.quantity.get_conversion_factor(other_dim, self_dim)
                                        channel_units_compatible = True
                                        
                                    except AssertionError:
                                        channel_units_compatible = False
                                        
                                else:
                                    channel_units_compatible = True
                                    
                            result &= channel_units_compatible
                        
                        if result and not ignoreOrigin:
                            result &= np.isclose(self.getDimensionlessOrigin(key, self.channelIndices(key)[chIndex]),
                                                other.getDimensionlessOrigin(key, other.channelIndices(key)[chIndex]),
                                                rtol=rtol, atol=atol, equal_nan=equal_nan)
                            
                        if result and not ignoreResolution:
                            result &= np.isclose(self.getDimensionlessResolution(key, self.channelIndices(key)[chIndex]),
                                                other.getDimensionlessResolution(key, other.channelIndices(key)[chIndex]),
                                                rtol=rtol, atol=atol, equal_nan=equal_nan)
                                
        return result
    
    def __str__(self):
        repr_str = self.__repr__().split()
        return "\n".join([f"{self.__repr__()} with {len(self._calibration_)} axes:"] + [cal.__str__() for cal in self._calibration_])
    
    def _repr_pretty_(self, p, cycle):
        p.text(f"{self.__class__.__name__} with {len(self._calibration_)} axes:")
        p.breakable()
        for cal in self._calibration_:
            p.pretty(cal)
        
    def hasAxis(self, key):
        """Queries if the axis key is calibrated by this object
        """
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        return key in self.axiskeys and key in self._axistags_
    
    @property
    def axiskeys(self):
        """A list of axiskeys
        """
        yield from (cal.key for cal in self._calibration_)
    
    #@property
    def keys(self):
        """Alias to self.axiskeys
        """
        yield from self.axiskeys
    
    @property
    def axistags(self):
        """Read-only
        """
        return self._axistags_
    
    @property
    def channels(self):
        return len(self["c"].channels)
    
    @property
    def calibrations(self):
        return self._calibration_
    
    #@property
    def values(self):
        yield from (cal for cal in self)
        
    def items(self):
        yield from ((cal.key, cal) for cal in self)
    
    #@property
    def typeFlags(self, key):
        """Read-only
        """
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if key not in self.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s is not calibrated by this object" % key)
        
        return self[key]["type"]
    
    def addAxis(self, axisInfo, index = None):
        """Register a new axis with this AxesCalibration object.
        
        The calibration values for the new axis can be atomically set using
        the setXXX methods
        
        By default a Channels axis will get a single channel (singleton axis).
        More channels can then be added using setChannelCalibration(), and calibration
        data for each channel can be modified using other setXXX methods
            
        FIXME/WARNING: this function breaks axes bookkeeping by the VigraArray object
        that owns the axistags!!!
        
        Parameters:
        ===========
        axisInfo: vigra.AxisInfo object
        
        Named parameters:
        ================
        index: int or None (default) index of the axis
            when an int, it must be in the closed interval
            [0, len(self.axistags)]
        
        """
        if not isinstance(axisInfo, vigra.AxisInfo):
            raise TypeError("Expecting an AxisInfo object; got %s instead" % type(axisInfo).__name__)
        
        cal = AxisCalibrationData(axInfo)
        axInfo = cal.calibrateAxis(axInfo)
        
        if index is None:
            self._axistags_.append(axInfo)
            self._calibration_.append(cal)
            
        elif isinstance(index, int):
            if index < 0:
                raise ValueError("index must be between 0 and %d, inclusive" % len(self.axistags))
            
            if index == len(self.axistags):
                self._axistags_.append(axInfo)
                self._calibration_.append(cal)
                
            elif index < len(self.axistags):
                self._axistags_.insert(index, axInfo)
                self._calibration_.insert(index, cal)
                
                
        # parse calibration string from axisInfo, it if exists
        self._initialize_calibration_with_axis_(axInfo)
        
    def writeHDF5(self, filenameOrGroup:typing.Union[str, h5py.Group],
                  pathInFile:typing.Optional[str] = "axis_calibrations",
                  mode:typing.Optional[str]="a"):
        from iolib.h5io import get_file_group_child
        
        file, group, childname = get_file_group_child(filenameOrGroup, pathInFile, mode)
        
        axcalgroup = group.create_group(childname)
        
        for k in self:
            caldict = self[k]
            
            axcal_dataset = axcalgroup.create_dataset(caldict.axiskey, data=[caldict.origin, caldict.resolution])
            axcal_dataset.attrs["axis_type"] = axisTypeStrings(caldict["axistype"])
            
    def removeAxis(self, axis):
        """Removes the axis and its associated calibration data
        
        Raises KeyError is axis is not found
        
        WARNING: this function breaks axes bookkeeping by the VigraArray object
        that owns the axistags!!!
        
        Parameters:
        ==========
        axis: str or vigra.AxisInfo; when a str, it must be a valid AxisInfo key.
        """
        if isinstance(axis, vigra.AxisInfo):
            key = axis.key
            if axis not in self._axistags_:
                raise KeyError("Axis %s not found" % key)
            
        elif isinstance(axis, str):
            key = axis
            if key not in self._axistags_.keys():
                raise KeyError("Axis %s not found" % key)
                
            axis = self._axistags_[key]
            
        if key not in self._calibration_.keys():
            raise KeyError("Axis %s has no calibration data" % key)
                
                
        self._calibration_.pop(key, None)
        del(self._axistags_[key])
        
    def synchronize(self):
        """Synchronizes the axis calibration data.
        
        Updates the AxesCalibration values using the axistags instance contained
        within this AxesCalibration object.
        
        This should be called after calling any VigraArray methods that change 
        the axes layout (inserting or removing an axis, e.g. by creating a lesser
        dimension view, etc). Such methods modify the axistags reference contained
        in this object.
        
        The axistags take priority in the following cases: 
        
        1) if, as a result of Vigra library functions, the axistags have GAINED 
        a new axis, this new axis will get default calibration values which can 
        be later modified individually, by calling one of the setXXX() methods
        of the AxesCalibration object.
        
            NOTE: a Channels axis will get calibration data for channel 0; 
            calibration data for more channels can be added manually, by calling 
            setChannelCalibration().
        
        2) if the axistags have LOST an axis, its calibration data will be removed
        
        """
        new_axes = [axInfo for axInfo in self._axistags_ if axInfo.key not in self._calibration_.keys()]
        obsolete_keys = [key for key in self._calibration_.keys() if key not in self._axistags_.keys()]

        for axInfo in new_axes:
            #self._initialize_calibration_with_axis_(axInfo)
            self.calibrateAxis(axInfo)
        
        for key in obsolete_keys:
            self._calibration_.pop(key, None)
                
        
    def calibrateAxes(self):
        """Attaches a calibration string to all axes registered with this object.
        """
        for k, ax in enumerate(self._axistags_):
            self._calibration_[k].calibrateAxis(ax)
            
def hasNameString(s):
    return AxesCalibration.hasNameString(s)
    
def axisChannelName(axisinfo, channel):
    """
    Parameters:
    ===========
    axisinfo: vigra.AxisInfo object
    
    channel: int >=0 (0-based index of the channel)
    """
    return AxesCalibration(axisinfo).getChannelName(channel)

def axisName(axisinfo):
    """Returns the axis name stored in the axis description.
    
    Parameters:
    ===========
    axisinfo: vigra.AxisInfo
    
    Returns:
    =======
    
    A two-elements tuple: (names, indices), where:
    
        names = a list of str
    
        indices = a list of int. 
        
    When axisinfo.isChannel() is True the list of names contains the channel
    names, and the list of indices contains the corresponding channel index.
    
    When axisinfo.isChannel() is False the list of names has only one element
    which is the name of the axis, and the list of indices is empty.
    
    When axisinfo does not have a name XML-formatted string in its description,
    both lists are empty.
    
    It is not guaranteed that the number of channel names equals the size
    of the axis with this axisinfo. If this is required, then it should be 
    checked outside this function.
    
    """
    return AxesCalibration(axisinfo).axisName
    
def isCalibrated(axisinfo):
    """Syntactic shorthand for hasCalibrationString(axisinfo.description).
    
    NOTE: Parameter checking is implicit
    
    """
    return AxesCalibration.isAxisCalibrated(axisinfo)

def calibration(axisinfo, asTuple=True):
    """Returns the calibration triplet (units, origin, resolution) of an axis.
    
    The tuple is obtained by parsing the calibration string contained in the
    description attribute of axisinfo, where axisinfo is a vigra.AxisInfo object.
    
    If axis is uncalibrated, the function returns (dimensionless, 0.0, 1.0) when
    axis is a channel axis or (pixel_unit, 0.0, 1.0) otherwise.
    
    NOTE: Parameter checking is implicit
    
    """
    if isinstance(axisinfo, vigra.AxisInfo):
        return 
    result = AxesCalibration(axisinfo)
    
    if asTuple:
        return result.calibrationTuple()
    
    else:
        return result
    
def resolution(axisinfo):
    return AxesCalibration(axisinfo).resolution

def hasCalibrationString(s):
    """Simple test for what MAY look like a calibration string.
    Does nothing more than saving some typing; in particular it DOES NOT verify
    that the calibration string is conformant.
    
    NOTE: Parameter checking is implicit
    
    """
    return AxesCalibration.hasCalibrationString(s)

def removeCalibrationData(axInfo):
    return AxesCalibration.removeCalibrationData(axInfo)

def removeCalibrationFromString(s):
    """Returns a copy of the string with any calibration substrings removed.
    Convenience function to clean up AxisInfo description strings.
    
    NOTE: Parameter checking is implicit
    
    """
    
    return AxesCalibration.removeCalibrationFromString(s)
    
def calibrationString(units=pq.dimensionless, origin=0.0, resolution=1.0, channel = None):
    """Generates an axis calibration string from an units, origin and resolution
    
    Positional kewyord parameters:
    
    "units": python quantities Quantity (default is dimensionless)
    
    "origin": float, default is 0.0
    
    "resolution": float, default is 1.0
    
    "channel": integer or None (default); only used for channel axisinfo objects 
    (see below)
    
    Returns an xml string with the following format:
    
    <axis_calibration>
        <units>str0</units>
        <origin>str1</origin>
        <resolution>str2</resolution>
    </axis_calibration>
    
    where:
    
    str0 = string representation of the unit quantity such that it can be passed to
            python' eval() built-in function and, given appropriate namespace or 
            globals dict, return the unit quantity object.
    
    str1, str2 = string representations that can be evaluated to Real scalars, 
        for origin and resolution, respectively.
        
    NOTE 2018-04-29 11:31:04: 
    Channel axes can have more than one channel. Therefore, a calibration
    string will contain an extra (intermediate) node level for the channel index
    (indices are 0-based). 
    
    the channel parameters must then be an integer >= 0
    
    <axis_calibration>
        <channel0>
            <units>str0</units>
            <origin>str1</origin>
            <resolution>str2</resolution>
        </channel0>
        
        <channel1>
            <units> ... </units>
            <origin> ... </origin>
            <resolution> ... </resolution>
        </channel1>
        
        ... etc...
        
    </axis_calibration>
    
    For backward compatibility, channel axes are allowed to contain the old-style
    calibration string (without channel elements) which implies this calibration 
    applies to ALL channels in the data.
    
    
    """
    
    axcal = AxesCalibration(units = units, origin = origin, resolution = resolution,
                            channel = channel)
    
    return axcal.calibrationString(includeChannelCalibration = channel is not None)
    

def parseDescriptionString(s):
    """Performs the reverse operation to calibrationString.
    
    Positional parameters:
    ======================

    s = an XML - formatted string (as returned by calibrationString), or a 
        free-form string _CONTAINING_ an XML - formatted string as returned 
        by calibrationString.
        
    The function tries to detect whether the argument string 's' contains a
    "calibration string" with the format as returned by calibrationString 
    then parses that substring to return a (unit,origin) tuple.
    
    If such a (sub)string is not found, the function returns the default 
    values of (dimensionless, 0.0). If found, the (sub)string must be 
    correctly formatted (i.e. start/end tags must exist) otherwise the 
    function raises ValueError.
    
    Returns :
    =========
    
    A tuple (python Quantity, real_scalar, real_scalar) containing respectively,
    the unit, origin and resolution. 
    
    Raises ValueError if a calibration string is not found in s
    
    """
    return AxesCalibration.parseDescriptionString(s)

def calibrateAxis(axInfo, cal, channel=None, channelname=None):
    """Attaches a dimensional calibration to an AxisInfo object.
    Calibration is inserted as an xml-formatted string.
    (see calibrationString)
    
    Positional parameters:
    ====================
    axInfo = a vigra.AxisInfo object
    
    cal = tuple, list, a python Quantity, or a calibration string
            
        When "cal" is a tuple or list it can contain up to three items:
        
        (Quantity, float, float): units, origin, resolution
    
        (Quantity, float): units, origin (defaut resolution set to 1.0 or what 
            the axInfo provides)
    
        (Quantity,): units; default origin and resolution set to 0.0 and 1.0
        
        When "cal" is a Quantity, the function behaves as above.
        
        When "cal" is a string, it will be checked if it contains an XML-formatted
        calibration string. If found, such a (sub-) string will be inserted in 
        the description attribute of the AxisInfo object (see below).
        
    Named parameters:
    =================
    channel None (default) or a non-negative integer.
        Used only when axInfo.isChannel() is True, in which case it specifies
        to which channel th calibration applies.
        
    Returns:
    ========
    axInfo, axcal
    
    axInfo: A reference to the axInfo with modified description string containing calibration
    information.
    
    axcal: AxesCalibration object
    
    What this function does:
    ========================
    The function creates an XML-formatted calibration string (see 
    calibrationString()) that will be inserted in the description attribute 
    of the axInfo parameter
        
    NOTE (1) If axInfo.description already contains a calibration string, it will 
    be replaced with a new calibration string. No dimensional analysis takes place.
    
    NOTE (2) The default value for the resolution in vigra.AxisInfo is 0.0, which 
    is not suitable. When axInfo.resolution == 0.0, and no resolution parameter
    is supplied, the function will set its value to 1.0; otherwise, resolution 
    will take the value provided in the axInfo.
    
    Technically, resolution values should be strictly positive. However, this
    is NOT enforced.
    
    """
    # set default resolution value if not specified
    resolution = 1.0 if axInfo.resolution == 0 else axInfo.resolution 
    
    if isinstance(cal, (tuple, list)):
        if not isinstance(cal[0], pq.Quantity):
            raise TypeError("First element in a calibration tuple must be a Quantity")
        
        if len(cal) == 1: # (units)
            c_ = (cal[0], 0.0, resolution)
            
        elif len(cal) == 2: # (units, origin)
            c_ = (cal[0], cal[1], resolution)
            
        elif len(cal) == 3: # (units, origin, resolution)
            c_ = [c for c in cal] # if cal is a tuple it isimmutable so we build up a temporary list here
            
            # NOTE also write to the resolution attribute of the axis info object
            resolution = c_[2]
            
        axcal = AxesCalibration(units = c_[0], origin = c_[1], resolution = c_[2],
                                key = axInfo.key, axisname = axisTypeName(axInfo),
                                channel = channel, channelname=channelname)
            
    elif isinstance(cal, pq.Quantity):
        c_ = [cal.units, 0.0, resolution]
        
        axcal = AxesCalibration(units = c_[0], origin = c_[1], resolution = c_[2],
                                key = axInfo.key, axisname = axisTypeName(axInfo),
                                channel = channel, channelname=channelname)
            
            

    elif isinstance(cal, str):
        axcal = AxesCalibration(axisinfo=cal, channel=channel, channelname=channelname) # will raise ValueError if cal not conformant
        
    else:
        raise TypeError("Unexpected type (%s) for calibration argument." % type(cal).__name__)
        
    
    axcal.calibrateAxis(axInfo)
        
    return axInfo, axcal

def getAxisResolution(axisinfo):
    """Returns the resolution of the axisinfo object as a Python Quantity.
    """
    if not isinstance(axisinfo, vigra.AxisInfo):
        raise TypeError("Expecting a vigra.AxisInfo object; got %s instead" % type(axisinfo).__name__)
    
    axcal = AxesCalibration(axisinfo)
    
    # FIXME what to do when there are several channels?
    
    return axcal.getResolution(axisinfo.key)
    
def getAxisOrigin(axisinfo):
    """Returns the axis origin as a Python Quantity
    """
    if not isinstance(axisinfo. vigra.AxisInfo):
        raise TypeError("Expecting a vigra.AxisInfo object; got %s instead" % type(axisinfo).__name__)
    
    # FIXME what to do when there are several channels?
    
    axcal = AxesCalibration(axisinfo)
    
    return axcal.getOrigin(axisinfo.key)
    
# NOTE: for old pickles
AxisCalibration = AxisCalibrationData
