import numbers, traceback, typing, functools, operator, warnings
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
                                    )

from core.datatypes import (
                            is_numeric, 
                            is_numeric_string,
                            quantity2scalar,
                            unit_quantity_from_name_or_symbol,
                            units_convertible,
                            )

from core.utilities import (reverse_mapping_lookup, unique, counter_suffix,)

from core.traitcontainers import DataBag

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

class CalibrationData(object):
    """:Superclass: for Axis and Channel calibrations.
    
    The sole purpose of these :classes: is to offer a way to notify changes in
    the calibration data. 
    
    Calibration parameters can be semantically inter-dependent, 
    e.g. axis type <-> axis units <-> (origin, resolution) <-> axis type key. 
    
    To avoid circular dependencies, manualy changing one parameter does NOT 
    automatically reassigns values to the others.
    
    NOTE that calibration parameters (as set up in here and derived :classes:)
    are only checked at initialization time.
    
    Changing these parameters on a 'live' object does NOT automatically
    reassign the other parameters because this can give rise to circular
    dependencies.
    
    Therefore, if a parameter is changed, the others may also have to be changed 
    manually to reflect the new calibration in a meaningful way.
    
    For example:
        1) adding channels to a NonChannel axis will NOT change the type
    of the axis to Channels.
    
        2) changing the type of a NonChannel axis to a Channels axis will NOT
        add channel calibration data - this has to be added manually - and the 
        reverse operation will NOT remove channel calibration data, if it exists.
        
        3) switching axis type will NOT change axis key, and vice-versa
    
    
    
    """
    parameters = ("units", "origin", "resolution")
    
    @classmethod
    def isCalibration(cls, x):
        return isinstance(x, cls) or (isinstance(x, dict) and all(k in x for k in cls.parameters))
        
    def __init__(self, *args, **kwargs):
        """
        Specifies units, origin & resolution either as:
        
        a) positional parameters:
            in this case, units, origin and resolution will be assigned ONCE, 
            ansd subsequent values will be ignored
            
        b) keyword parameters:
            can override the values assigned to units, origin and resolution in
            *args
            
        Var-positional parameters (*args):
        ==================================
        
        int, float, complex; assigns to origin, then resolution, in THIS order
        
        scalar numpy array: assigns ot origin then resolution, in THIS order
        
        scalar python Quantity: assigns to units, origin then resolution, in THIS
            order
            
            
        Var-keyword parameters (**kwargs)
        =================================
        units: python Quantity, or python qualtities.dimensionality.Dimensionality
        
        origin, resolution: int, float, complex, scalar numpy array or scalar 
            python Quantity.
            
            When a scalar python Quantity with units convertible to those of
            units' then it will be rescaled (if necessary) and its magnitude
            assigned ot origin or resolution, respectively.
            
        """
        # FIXME 2021-10-22 09:48:23
        # a DataBag here gets "sliced" in :subclasses: of CalibrationData
        # why ???
        #self._data_ = DataBag()
        self._data_ = Bunch()
        
        for param in self.__class__.parameters:
            self._data_[param] = None
            
        # allow ONE calibration-like dict or calibration data object
        if len(args) == 1 and AxisCalibrationData.isCalibration(args[0]):
            if isinstance(args[0], dict):
                kwargs = args[0]
                args.clear()
            elif isinstance(args[0], AxisCalibrationData):
                self._data_.update(args[0]._data_)
                return
            
        # cache channel calibration data structures in kwargs to ensure consistency
        channeldata = [(k, ChannelCalibrationData(v)) for k,v in kwargs.items() if ChannelCalibrationData.isCalibration(v)]
        
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
                    if not isSpecificAxisType(self._data_.type):
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
                        
            elif arg == np.nan:
                if not isinstance(self._data_.origin, (complex, float, int)) and self._data_.origin != np.nan:
                    self._data_.origin = arg
                    
                elif not isinstance(self._data_.resolution, (complex, float, int)) and self._data_.origin != np.nan:
                    self._data_.resolution = arg
                    
                elif self.__class__ == ChannelCalibrationData:
                    if not isinstance(self._data_.maximum, (complex, float, int)) and self._data_.maximum != np.nan:
                        self._data_.maximum = arg
                        
            elif isinstance(arg, vigra.AxisInfo):
                if self.__class__ == AxisCalibrationData:
                    self._data_.type = arg.typeFlags
                    self._data_.key = arg.key
                    self._data_.name = axisTypeName(self._data_.type)
                    
                
                # TODO parse description - check AxesCalibration.parse description
                
        axtype = kwargs.pop("type", None)
        
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
            
        axname = kwargs.pop("name", None)
        
        if self.__class__ == AxisCalibrationData:
            if isinstance(axname, str) and len(axname.strip()):
                self._data_.name = axname
            
            if not isinstance(self._data_.name, str) or len(self._data_.name.strip()) == 0:
                self._data_.name = axisTypeName(self._data_.type)
                
        chindex = kwargs.pop("index", None)
        
        if self.__class__ == ChannelCalibrationData:
            if isinstance(chindex, int) and chindex >= 0:
                self._data_.index = chindex
        
        units_ = kwargs.pop("units", None)
        
        if isinstance(units_, str):
            try:
                units_ = unit_quantity_from_name_or_symbol(units_)
            except:
                units_ = None
        
        if isinstance(units_, pq.dimensionality.Dimensionality):
            units_ = [k for k in units_.simplified][0]
        
        if isinstance(units_, pq.Quantity):
            self._data_.units = units_.units
        
        if not isinstance(self._data_.units, pq.Quantity):
            if self.__class__ == AxisCalibrationData:
                self._data_.units = axisTypeUnits(self._data_.type)
            elif self.__class__ == ChannelCalibrationData:
                self._data_.units = channel_unit
                
            else:
                self._data_.units = pq.dimensionless # (UnknownAxisType)
            
        origin_ = kwargs.pop("origin", None)
        minimum = kwargs.pop("minimum", None)
        
        origin_ = origin_ if origin_ is not None else minimum
        
        if isinstance(origin_, pq.Quantity):
            if not units_convertible(origin_.units, self._data_.units.units):
                raise TypeError(f"'origin (or minimum)' units {origin_.units} are incompatible with the specified units ({self._data_.units})")
                
            if origin_.units != self._data_.units.units:
                origin_ = origin_.rescale(self._data_.units.units)
                
            self._data_.origin = quantity2scalar(o)
            
        elif isinstance(origin_, (complex, float, int, np.ndarray)) or origin_ == np.nan:
            self._data_.origin = quantity2scalar(origin_)
            
        resoln  = kwargs.pop("resolution", None)
        
        if isinstance(resoln, pq.Quantity):
            if not units_convertible(resoln.units, self._data_.units.units):
                raise TypeError(f"'resolution' units {resoln.units} are incompatible with the specified units ({self._data_.units})")
                
            if resoln.units != self._data_.units.units:
                resoln = resoln.rescale(self._data_.units.units)
                
            self._data_.resolution = quantity2scalar(resoln)
        
        elif isinstance(resoln, (complex, int, float, np.ndarray)) or resoln == np.nan:
            self._data_.resolution = quantity2scalar(resoln)
        
        if self.__class__ == AxisCalibrationData:
            if self._data_.type & vigra.AxisType.Channels:
                # bring back channel calibration data if necessary
                for k, chcal in enumerate(channeldata):
                    # assign calibrations as they come;
                    # use their mapped names in kwargs as arguments
                    # later on, use their own channelname/channelindex fields as needed
                    self._data_[chcal[0]] = chcal[1]
                
        maxval = kwargs.pop("maximum", None)
        
        if self.__class__ == ChannelCalibrationData:
            if isinstance(maxval, pq.Quantity):
                if not units_convertible(maxval.units, self._data_.units.units):
                    raise TypeError(f"'maximum value' units {maxval.units} are incompatible with the specified units ({self._data_.units})")
                    
                if maxval.units != self._data_.units.units:
                    maxval = maxval.rescale(self._data_.units.units)
                    
                self._data_.maximum = quantity2scalar(maxval)
                
            elif isinstance(maxval, (complex, float, int, np.ndarray)) or maxval == np.nan:
                self._data_.min = quantity2scalar(maxval)
                
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
            self._data_.units = pq.dimensionless
            
        if not isinstance(self._data_.origin, (complex, float, int)):
            self._data_.origin = 0.
            
        if not isinstance(self._data_.resolution, (complex, float, int)):
            self._data_.resolution = 1.
            
    def __repr__(self):
        return pformat(self._data_)
        
    def __str__(self):
        return pformat(self._data_)
        
    @property
    def units(self) -> pq.Quantity:
        """Get/set the pysical units of measurement.
        WARNING: Setting this property will NOT adjust (rescale) the 'origin' 
        and 'resolution' - use self.rescale() for that.
        Issues a warning if the new units are NOT typical for the axis type.
        """
        return self._data_.units
    
    @units.setter
    def units(self, u:typing.Union[pq.Quantity, pq.dimensionality.Dimensionality, str]) -> None:
        if isinstance(u, pq.dimensionality.Dimensionality):
            new_units = [k for k in u.simplified][0]
            
        elif isinstance(u, str):
            new_units = unit_quantity_from_name_or_symbol(u)
            
        elif isinstance(u, pq.Quantity):
            new_units = u
                
        else:
            raise TypeError(f"Units expected to be a Python Quantity, Dimensionality, or str; got {type(u).__name__} instead")
        
        if hasattr(self, "type"):
            units_for_type = axisTypeUnits(self.type)
            axis_type_names = axisTypeStrings(self.type)
            if not units_convertible(new_units.units, units_for_type.units):
                warnings.warn(f"Assigning units {new_units} for a {axis_type_names} axis", RuntimeWarning, stacklevel=2)
                
        self._data_.units = new_units
        
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
            
        #_=self._data_.trait_values() # force traits refreshing
        
    @property
    def resolution(self):
        """Get/set the origin value
        """
        return self._data_.resolution
    
    @resolution.setter
    def resolution(self, val):
        if isinstance(val, (complex, float, int)):
            self._data_.resolution = val
            #self._data_["resolution"] = val
            
        elif isinstance(val, pq.Quantity):
            if not units_convertible(val.units, self.units.units):
                raise TypeError(f"Resolution units ({val.units}) incompatible with my units ({self.units.units})")
            
            if val.units != self.units.units:
                val = val.rescale(self.units.units)
                
            self._data_.resolution = quantity2scalar(val)
            #self._data_["resolution"] = quantity2scalar(val)
            
        elif isinstance(val, np.ndarray):
            self._data_.resolution = quantity2scalar(val)
            #self._data_["resolution"] = quantity2scalar(val)
            
        else:
            raise TypeError(f"Resolution expected a scalar int, float, complex, Python Quantity or numpy array; got {type(val).__name__} instead")
            
        #_=self._data_.trait_values() # force traits refreshing
        
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
    def name(self):
        return self._data_.name
    
    @name.setter
    def name(self, val:str):
        if isinstance(val, str) and len(val.strip()):
            self._data_.name = val
            #self._data_["name"] = val

        #_=self._data_.trait_values() # force traits refreshing
            
    @property
    def index(self):
        return self._data_.index
    
    @index.setter
    def index(self, val:int):
        if isinstance(val, int) and val >= 0:
            self._data_.index = val
            #self._data_["index"] = val
        
        #_=self._data_.trait_values() # force traits refreshing

class AxisCalibrationData(CalibrationData):
    """Atomic calibration data for an axis of a vigra.VigraArray.
    To be mapped to a vigra.AxisInfo key str in AxesCalibration, or to
    a key str with format "channel_X", in a parent AxisCalibrationData object
    for an axis of type Channels
    
    The axis calibration is uniquely determined by the axis type (vigra.AxisType
    flags), axis name, units (Python Quantity object), origin and resolution 
    (Python numeric scalars).
    
    In addition an axis of type Channels will also associate an AxisCalibrationData
    object for each of its channels.
    
    """
    parameters = CalibrationData.parameters + ("type", "name", "key")
    
    def __init__(self, *args, **kwargs):
        """
        Parameters:
        ===========
        
        Calibration parameters can be specified ONCE via var-positional parameters
        (*args) or var-keyword parameters (**kwargs), with the latter (if given)
        overriding the former.
        
        Parameters (in addition to those for CalibrationData):
        ======================================================
        
        axistype:vigra.AxisType or int = Flags that define the type of the axis
            (theoretically any combination of primitive vigra.AxisType flags 
            OR-ed together, although the only meanginful combinations are 
            between Frequency and one of Angle, Space, or Time)
            
            Optional, default is vigra.AxisType.UnknownAxisType
            
        axisname: a str = Short, yet descriptive enough string
            Optional, default is determined from the axistype parameter
            
        axisinfo: vigra.AxisInfo; optional default is None
            When specified, it will override axistype, axiskey, axisname and,
            if its description also contains origin  & resolution, these will
            also be overridden.
            
        units: a scalar Python quantities Quantity (can also be a UnitQuantity)
        
        origin, resolution: scalar floats, quantities, or numpy arrays of size 1
        
        [channel_X, ...] ChannelCalibrationData objects;
            when given, the axis type will forcibly set to vigra.AxisType.Channels
        
        """
        super().__init__(*args, **kwargs)

    @property
    def name(self):
        """Get/set the axis name
        """
        return self._data_.name
    
    @name.setter
    def name(self, val:str):
        #print(f"CalibrationData | {self.__class__.__name__}).name.setter _data_: {self._data_}")
        if isinstance(val, str) and len(val.strip()):
            self._data_["name"] = val
            #self._data_.name = val
            
        #print(f"CalibrationData | {self.__class__.__name__}).name.setter _data_: {self._data_}")
        #_=self._data_.trait_values() # force traits refreshing
            
    @property
    def key(self):
        """Get/set the axis type key
        """
        return self._data_.key
    
    @key.setter
    def key(self, val:str):
        #print(f"CalibrationData | {self.__class__.__name__}).key.setter _data_: {self._data_}")
        if isinstance(val, str) and len(val.strip()):
            self._data_["key"] = val
            #self._data_.key = val
        #print(f"CalibrationData | {self.__class__.__name__}).key.setter _data_: {self._data_}")
        
        #_=self._data_.trait_values() # force traits refreshing
            
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
            if val == vigra.AxisType.Channels:
                # switch to Channels: add channels
                if len(list(self.channels)) == 0:
                    channel = ChannelCalibrationData(channelindex = 0,
                                                     channelname = "channel_0")
                    
                    self._data_[f"channel_{channel.index}"] = channel
                    
            else:
                if len(list(self.channels)):
                    # switch AWAY FROM Channels:
                    # remove channels
                    chcals = [k for k in self._data_ if k.startswith("channel")]
                    
                    for k in chcals:
                        self._data_.pop(k, None)
                        
            self._data_.type = val
            self._data_.units = axisTypeUnits(val)
            self._data_.name = axisTypeName(val)
            self._data_.key = axisTypeSymbol(val)
            
    @property
    def channels(self):
        """Iterator through channel calibration data.
        
        Generates tuple(name, channel calibration data) where name is the name
        of this axis calibration field that is mapped to the channel calibration 
        data.
        
        The setter does nothing for a NonChannel axis.
        
        To add channels to an axis first make sure the axis type is Channels.
        """
        yield from ((k,v) for k,v in self._data_.items() if isinstance(v, ChannelCalibrationData))
        
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
        """Iterates through the channel calibraiton data
        """
        yield from (v for v in self._data_.values() if isinstance(v, ChannelCalibrationData))
        
    @channelCalibrations.setter
    def channelCalibrations(self, val:typing.Sequence[typing.Union[ChannelCalibrationData, dict]]):
        if not self.type & vigra.AxisType.Channels:
            return
        
        for k,v in enumerate(val):
            self._data_[f"channel_{k}"] = ChannelCalibrationData(v[1])
        
    @property
    def channelNames(self):
        """Yields channel names or nothing of there is no ChannelCalibrationData.
        NonChannel axes have no ChannelCalibrationData
        """
        yield from (ch.name for ch in self.channels)
        
    @property
    def channelIndices(self):
        """Yields channel indices or nothing of there is no ChannelCalibrationData.
        NonChannel axes have no ChannelCalibrationData
        """
        yield from (ch.index for ch in self.channelCalibrations)
        
    @property
    def nChannels(self):
        """Returns 0 for NonChannel axis or when there is no ChannelCalibrationData
        """
        return len(list(self.channelCalibrations))
        
    @property
    def calibrationString(self):
        """
        XML-formatted string with one of the following formats, depending on axis type:
        
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
                # output the dimensionality's string property, always simplified
                # if possible
                s = value.units.dimensionality.simplified.string
                
            elif param == "index":
                s = "%d" % value
                
            #elif param in ("origin", "resolution", "maximum", "minimum"):
                
            else: # ("origin", "resolution", "maximum", "minimum")
                s = "%f"%value
                
            ss.append(s)
            
            ss.append(f"</{param}>")
            
            return "".join(ss)

        strlist = ["<axis_calibration>"]
        
        for param in self.__class__.parameters:
            strlist.append(__gen_xml_element__(self, param))
            
        if self.type & vigra.AxisType.Channels:
            for ch in self.channels:
                strlist.append(f"<channel_{ch[0]}>" % ch[0])
                for p in ChannelCalibrationData.parameters:
                    strlist.append(__gen_xml_element__(ch[1], pp))
                strlist.append("f</channel_{ch[0]}>" % ch[0])
                
        strlist.append("</axis_calibration>")
        
        return "".join(strlist)
    
    def addChannelCalibration(self, val:ChannelCalibrationData,
                              name:typing.Optional[str] = None,
                              ensure_unique:bool=True):
        if not self.type & vigra.AxisType.Channels:
            return
        
        if not isinstance(val, ChannelCalibrationData):
            raise TypeError(f"Expecting a ChannelCalibrationData; got {type(val).__name__} instead")
        
        if ensure_unique:
            names = list(self.channelNames)
            indices = list(self.channelIndices)
            
            if val.name in names:
                val.name = counter_suffix(val.name, names)
                
            if val.index in indices:
                val.index = max(indices)+1
                
        if not isinstance(name, str) or len(name.strip()) == 0 or name in self.parameters:
            name = f"channel_{self.nChannels}"
            
        self._data_[name] = val
        
    def removeChannelCalibration(self, index:typing.Union[int, str]) -> typing.Union[ChannelCalibrationData]:
        """Removes ChannelCalibrationData for channel with specified index or name.
        
        Returns the ChannelCalibrationData, if found, else None
        """
        chcal = self.channelCalibration(index, True)
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
                
    def channelCalibration(self, index:typing.Union[int, str], full:bool=False):
        """Returns ChannelCalibrationData for a specific channel, or None
        Parameters:
        ==========
        index: str or int; 
            When a str, this is the channel name as in the ChannelCalibrationData
            'name' field
            When an int, this is the channel index as in the ChannelCalibrationData
            'index' field.
            
        full:bool, optional (default is False)
            When True, also returns the name this ChannelCalibrationData is 
            registered with, in this AxisCalibrationData
        
        Returns:
        ========
        A ChannelCalibrationData or tuple (str, ChannelCalibrationData) if 'full'
            is True
        
        Returns None for NonChannel axis or when there is no ChannelCalibrationData
        
        """
        if not self.type & vigra.AxisType.Channels:
            return
        
        if isinstance(index, int):
            what = "index"
            if full is True:
                chcal = [(k,v) for k,v in self._data_.items() if k.startswith("channel_") and isinstance(v, ChannelCalibrationData) and v.index == index]
            else:
                chcal = [v for k,v in self._data_.items() if k.startswith("channel_") and isinstance(v, ChannelCalibrationData) and v.index == index]
            
        elif isinstance(index, str):
            what = "name"
            if full is True:
                chcal = [(k,v) for k,v in self._data_.items() if k.startswith("channel_") and isinstance(v, ChannelCalibrationData) and v.name == index]
            else:
                chcal = [v for k,v in self._data_.items() if k.startswith("channel_") and isinstance(v, ChannelCalibrationData) and v.name == index]
            
        else:
            raise TypeError(f"Expecting a str or int; got {type(index).__name__} instead.")
            
        if len(chcal) > 1:
            warnings.warn(f"There is more than one channel with the same {what} ({index}).\nThe calibration for the first one will be returned", 
                        RuntimeWarning, 
                        stacklevel=2)
            
        if len(chcal):
            return chcal[0]
        
    def channelIndex(self, name:str) -> typing.Optional[int]:
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
        if not isinstance(name, str) or len(name.strip()) == 0:
            return 
        
        chcal = self.channelCalibration(name)
        if chcal is None:
            #warnings.warn(f"No channel {name} was found")
            return
        
        return chcal.index
        
    def setChannelIndex(self, name:str, val:int, 
                        ensure_unique:bool = True) -> None:
        """Sets the index of the channel with given name.
        
        Parameters:
        ==========
        name: str ;  the ChannelCalibrationData.index value for the channel
        val : str - if empty or contain only blanks it will be ignored
        ensure_unique: bool, optional (default is True)
            Avoid duplicate channel names. 
            
        Does nothing for a NonChannel axis
        """
        if not self.type & vigra.AxisType.Channels:
            return
        
        if isinstance(name, str) and len(name.strip()) == 0:
            return # avoid empty names
        
        if not isinstance(val, int):
            raise TypeError(f"index must be an int; got {type(val).__name__} instead")
        if val < 0:
            raise ValueError(f"index must be >= 0; got {val} instead")
        
        chcal = self.channelCalibration(name)
        
        if chcal is None:
            raise KeyError(f"No channel {name} was found")
        
        if ensure_unique:
            indices = unique(list(self.channelIndices))
            
            if val in indices:
                val = max(indices) + 1
                
            chcal.index = val
            
        else:
            chcal.index = val
        
    def chanelName(self, index:int) -> typing.Optional[str]:
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
        chcal = self.channelCalibration(index)
        if chcal is None:
            #warnings.warn(f"No channel {index} was found")
            return
        
        return chcal.name
        
    def setChannelName(self, index:int, val:str, 
                       ensure_unique:bool = True) -> None:
        """Sets the name of the channel with given index.
        
        Parameters:
        ==========
        index: int ;  the ChannelCalibrationData.index value for the channel
        val : str - if empty or contain only blanks it will be ignored
        ensure_unique: bool, optional (default is True)
            Avoid duplicate channel names. 
            
        Does nothing for a NonChannel axis.
        """
        if not self.type & vigra.AxisType.Channels:
            return
        
        if isinstance(val, str) and len(val.strip()): # avoid empty names
            chcal = self.channelCalibration(index)
            if chcal is None:
                raise KeyError(f"No channel {index} was found")
            
            if ensure_unique:
                names = unique(list(self.channelNames))
                
                new_val = counter_suffix(val, names)
                    
                chcal.name = new_val
                
            else:
                chcal.name = val
        
    def channelMinimum(self, index:typing.Union[int, str]) -> typing.Union[complex, float, int]:
        chcal = self.channelCalibration(index)
        if chcal is None:
            #warnings.warn(f"No channel {index} was found")
            return
        
        return chcal.minimum
        
    def setChannelMinimum(self, index:typing.Union[int, str], 
                          val:typing.Union[complex, float, int, np.ndarray]) -> None:
        if not self.type & vigra.AxisType.Channels:
            return
        
        chcal = self.channelCalibration(index)
        if chcal is None:
            raise KeyError(f"No channel {index} was found")
        
        chcal.minimum = val
        
    def channelMaximum(self, index:typing.Union[int, str]):
        chcal = self.channelCalibration(index)
        if chcal is None:
            #warnings.warn(f"No channel {index} was found")
            return
        
        return chcal.maximum
        
    def setChannelMaximum(self, index:typing.Union[int, str], 
                          val:typing.Union[complex, float, int, np.ndarray]) -> None:
        
        if not self.type & vigra.AxisType.Channels:
            return
        
        chcal = self.channelCalibration(index)
        if chcal is None:
            raise KeyError(f"No channel {index} was found")
        
        chcal.maximum = val
        
    def channelResolution(self, index:typing.Union[int, str]):
        chcal = self.channelCalibration(index)
        if chcal is None:
            #warnings.warn(f"No channel {index} was found")
            return
        
        return chcal.resolution
        
    def setChannelResolution(self, index:typing.Union[int, str], 
                             al:typing.Union[complex, float, int, np.ndarray]) -> None:
        if not self.type & vigra.AxisType.Channels:
            return
        
        chcal = self.channelCalibration(index)
        if chcal is None:
            raise KeyError(f"No channel {index} was found")
        
        chcal.resolution = val
        
    def channelUnits(self, index:typing.Union[int, str]) -> typing.Optional[pq.Quantity]:
        """Returns the units of the specified channel, or None if not found
        """
        chcal = self.channelCalibration(index)
        if chcal is None:
            #warnings.warn(f"No channel {index} was found")
            return
        
        return chcal.units
    
    def setChannelUnits(self, index:typing.Union[int, str], 
                        val:typing.Union[pq.Quantity, pq.dimensionality.Dimensionality, str]) -> None:
        chcal = self.channelCalibration(index)
        if chcal is None:
            raise KeyError(f"No channel {index} was found")
        
        chcal.units = units
        
    def calibrateAxis(self, axInfo:vigra.AxisInfo):
        """Embeds an XML-formatted string into axInfo's description
        """
        if not isinstance(axInfo, vigra.AxisInfo):
            raise TypeError("First argument must be a vigra.AxisInfo; got %s instead" % type(axInfo).__name__)
        
        if not axInfo.typeFlags & self.type:
            raise ValueError(f"The supplied AxisInfo with key {axInfo.key} has a different type ({axisTypeStrings(axInfo.typeFlags)}) than the one targeted by this calibration ({axisTypeStrings(self.type)})")
        
        calibration_string = self.calibrationString
            
        # check if there already is (are) any calibration string(s) in axInfo description
        # then replace them with a single xml-formatted calibration string
        # generated above
        # otherwise just append the calibration string to the description
        
        # 1) first, remove any name string
        name_start = axInfo.description.find("<name>")
        
        if name_start  > -1:
            name_stop = axInfo.description.find("</name>")
            
            if name_stop > -1:
                name_stop += len("</name>")
                
            else:
                name_stop = name_start + len("<name>")
                
            d = [axInfo.description[0:name_start].strip()]
            d.append(axInfo.description[name_stop:].strip())
            
            axInfo.description = " ".join(d)
        
        # 2) then find if there is a previous calibration string in the description
        calstr_start = axInfo.description.find("<axis_calibration>")
        
        if calstr_start > -1: # found previous calibration string
            calstr_end = axInfo.description.rfind("</axis_calibration>")
            
            if calstr_end > -1:
                calstr_end += len("</axis_calibration>")
                
            else:
                calstr_end  = calstr_start + len("<axis_calibration>")
                
            # remove previous calibration string
            # not interested in what is between these two (susbstring may contain rubbish)
            # because we're replacing it anyway
            # just keep the non-calibration contents of the axis info description 
            s1 = [axInfo.description[0:calstr_start].strip()]
            s1.append(axInfo.description[calstr_end:].strip())
            
            s1.append(self.calibrationString(axInfo.key))
            
        else: 
            s1 = [axInfo.description]
            s1.append(self.calibrationString(axInfo.key))
            
        axInfo.description = " ".join(s1)
        
        resolution = self.resolution
        
        channels = list(self(channels))
        
        if len(channels):
            resolution = channels[0].resolution
            
        axInfo.resolution = resolution if resolution != np.nan else 0.
        
        return axInfo # for convenience
    
    @staticmethod
    def parseCalibrationString(cal:typing.Optional[CalibrationData] = None, 
                               s:typing.Optional[typing.Union[str, vigra.AxisInfo]] = None,
                               check:bool=False) -> CalibrationData:
        """"""
        import xml.etree.ElementTree as ET
        
        def __eval_xml_element_text__(param, txt):
            if param == "units":
                value = unit_quantity_from_name_or_symbol(txt)
            elif param in ("key", "name"):
                value = txt
            elif param == "type":
                value = axisTypeFromString(txt)
            else: # ("index", "origin", "resolution", "minimum", "maximum")
                value = eval(txt)
                
            return value
        
        if isinstance(s, vigra.AxisInfo):
            s = s.description
            
        if not isinstance(s,str) or len(s.strip()) == 0:
            return
        
        if not isinstance(cal, AxisCalibrationData):
            cal = AxisCalibrationData()
        
        calibration_string = None
        
        # 1) find axis calibration string <axis_calibration> ... </axis_calibration>
        start = s.find("<axis_calibration>")
        
        if start > -1:
            stop  = s.find("</axis_calibration>")
            if stop > -1:
                stop += len("</axis_calibration>")
                calibration_string = s[start:stop]
        
        if isinstance(calibration_string, str) and len(calibration_string.strip()) > 0:
            # OK, now extract the relevant xml string
            try:
                main_calibration_element = ET.fromstring(calibration_string)
                
                # make sure we're OK
                if main_calibration_element.tag != "axis_calibration":
                    raise ValueError("Wrong element tag; was expecting 'axis_calibration', instead got %s" % element.tag)
                
                # see NOTE: 2021-10-09 23:58:58
                # xml.etree.ElementTree.Element.getchildren() is absent in Python 3.9.7
                #element_children = main_calibration_element.getchildren()
                # NOTE: getchildren() replaced with getXMLChildren():
                element_children = getXMLChildren(main_calibration_element) # getXMLChildren defined in xmlutils
                
                for child_element in element_children:
                    # these can be <children_X> tags (X is a 0-based index) or a <name> tag
                    # ignore everything else
                    if child_element.tag.lower() in AxisCalibrationData.parameters:
                        param = child_element.tag.lower()
                        txt = child_element.text
                        
                        if check:
                            #NOTE: 2021-10-22 13:41:45
                            #if needed, use below for more stringent checks
                            val = __eval_xml_element_text__(param, txt)
                            
                            if param == "type":
                                if self._data_.get(param, None) is not None:
                                    if not val & self._data_[param]:
                                        raise ValueError(f"Cannot set current axis type {axisTypeStrings(self._data_[param])} to {axisTypeStrings(val)}")
                                    
                            elif param =="key":
                                if self._data_.get(param, None) is not None and self._data_.get("type", None) is not None:
                                    axtype = self._data_["type"]
                                    if val != self._data_[param] and val != axisTypeSymbol(axtype):
                                        warnings.warn(f"Atypical axis key supplied ({val}) for a {axisTypeStrings(axtype)} axis")
                        else:
                            setattr(cal, param, __eval_xml_element_text__(param, txt))
                        
                                    
                    else:#if child_element.tag.lower().startswith("channel_"):
                        chcal = ChannelCalibrationData()
                        chcalname = child_element.tag.lower()
                        ch_children = getXMLChildren(child_element)
                        ch_tags = [c.tag for c in ch_children]
                        ch_cal_ok = False
                        if all (t in ChannelCalibrationData.parameters for t in ch_tags):
                            for param in ChannelCalibrationData.parameters:
                                if param in ch_tags:
                                    try:
                                        setattr(chcal, param, __eval_xml_element_text__(param, ch_children[ch_tags.index(param)].text))
                                        ch_cal_ok = True
                                    except:
                                        ch_cal_ok = False
                                        # ignore failures
                                        #traceback.print_exc()
                                        continue
                            if ch_cal_ok:
                                cal.addChannelCalibration(chcal, name=chcalname)
                        
                                
            except Exception as e:
                traceback.print_exc()
                print("cannot parse calibration string %s" % calibration_string)
                raise e
            
        return cal
            

class AxesCalibration(object):
    """Encapsulates calibration of a set of axes.
    
    Associates physical units (and names) to a vigra array axis persistently.
    
    An axes calibration for a VigraArray is uniquely determined by the axis type
    and the attributes 'name', 'units', 'origin', and 'resolution', for each 
    AxisInfo object attached to the VigraArray.
    
    In addition, for each channel in a Channel axis there is a set of 
    'name', 'units', 'origin' & 'resolution' parameters. This set is mapped to
    the channel index along the Channel axis.
    
    
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
        
    
    Usage:
    
    1) Preferred way: 
    ------------------
    Construct an AxesCalibration using a vigra.VigraArray or a
    vigra.AxisTags object.
    
    When the AxesCalibration object is constructed in this way it will keep a 
    reference to the VigraArray 'axistags' property or to the AxisTags object 
    passed to the constructor.
    
    The newly-created AxesCalibration object generates default values which can 
    then by atomically modified by calling one of the setXXX methods, 
    as explained below.
    
    The units, origin and resolution of an axis (or an individual channel in a 
    Channels axis) are set by the setUnits, setOrigin, setResolution methods.
    
    These methods require an axis "key" string or AxisInfo object to specify
    the axis for which the calibration is being modified. For Channel axes, 
    these methods also require the index of the channel for which the calibration
    is being modified.
    
    setAxisName() assigns a name to a specified axis; 
    
    setChannelName() assigns a name to an individual channel of a Channel axis
    which must exist in the AxesCalibration instance. NOTE that there can be at
    most ONE Channels axis in a VigraArray (and therefore also in an 
    AxesCalibration object).
    
    For convenience, methods to add or remove axes are provided. HOWEVER this risks
    breaking the axes bookkeeping by the vigra.VigraArray to which the axes belong.
    
    2) Construct an AxesCalibration using a vigra.AxisInfo object. 
    ---------------------------------------------------------------
    The units, origin, resolution and axisname can be passed as constructor 
    parameters, or assigned later. The axiskey and axistype parameters, 
    if passed to the constructor, will be ignored, their values being supplied 
    by the AxisInfo.
    
    When the AxesCalibration object is contructued using a vigra.AxisInfo object
    it looks for an XML-formatted string inside the AxisInfo object's 
    'description' property and the calibration data will be parsed from that 
    string (see the documentation for AxesCalibration.calibrationString() method).
    
    An "independent" AxisTags object will be constructed for this AxesCalibration 
    instance -- CAUTION: this will be uncoupled from any VigraArray and thus
    won't be of much use outside the AxesCalibration object.
    
    3) Construct an "anonymous" AxesCalibration
    --------------------------------------------
    This is achieved by passing the 'axiskey', 'axistype', 'units', 'origin', 
    'resolution' and 'axisname' parameters for a yet undefined axis.
    
    An "independent" AxisTags object will be constructed (see case 2, above) 
    containing a single AxisInfo object. Both the the AxisTags and its single 
    AxisInfo object will be uncoupled from any VigraArrays.
    
    Such AxesCalibration objects can be used as a "vehicle" to calibrate actual
    AxisInfo objects embedded in another VigraArray, provided they are compatible
    (and their key is found inside the calibration data).
    
    In all cases, for Channels axes only, the name, units, origin and resolution
    are accessed and set to the specified channel index (0-based integer).
    
    For non-channel axes, the name (axisname), units, origin and resolution
    are accessed (and set) by the axis key str.
    
    """

    relative_tolerance = 1e-4
    absolute_tolerance = 1e-4
    equal_nan = True
    
    parameters = ("axistype", "axisname", "origin", "resolution", "units")
    
    def __init__(self, data = None, 
                 axistype = None, axisname=None,
                 units = None, origin = None, resolution = None, channel = None, 
                 channelname = None):
        """
        Named parameters:
        ================
        
        data = None (default), a vigra.AxisTags object (typically asociated with 
                a vigra.VigraArray object), a vigra.AxisInfo object, 
                or a vigra.VigraArray object.
                
        axistype = None (default) or a vigra.AxisType enum flag (or a combination thereof);
                only used when axis is None, or a str (axiskey)
                
        axisname = None (default) or a str; only used when axis is None
        
        units = None (default) or python Quantity or UnitQuantity; only used when
            axis is None or a vigra.AxisInfo
            
        origin = None( default) or a scalar; only used when 
        
        """
        
        # NOTE: 2018-08-25 20:52:33
        # API revamp: 
        # 1) AxesCalibration stores a vigra.AxisTags object as a member -- 
        #   this CAN be serialized
        # 
        # 2) calibration is stored in a dictionary where the key is the axisinfo
        #   key (string) associated with that axis;
        #
        #   * under that tag key string, the axis calibration items are:
        #       "axisname", "axistype", "axiskey", "units", "origin", "resolution"
        #
        #   * for channel axes ONLY (tag key string "c"):
        #
        #       2.1) channel calibration items ("name", "units", "origin" and "resolution")
        #       are contained in a nested dictionary mapped to a 0-based integer 
        #       key (the channel "index") that is itself an item of the main 
        #       axis dictionary
        #
        #       2.2) axis calibration items "units", "origin" and "resolution"
        #       may be missing when the number of channels is > 1, or may have
        #       the same value as the channel calibration items for channel 0
        #
        #
        # 3) the AxesCalibration can thus contain calibration data for a collection
        #   of axes associated with a VigraArray object.
        #
        # 4) for an AxisInfo object to be "calibrated" (i.e., have an XML-formatted
        #   calibration string inserted in its "description" attribute) it needs to
        #   have its "key" attribute present in the main calibration dictionary of 
        #   this AxesCalibration object, and have the same typeFlags as the "axistype"
        #   item, even if the AxisInfo object is not part of the axistags collection
        #   stored within the AxesCalibration object.
        
        apiversion = (0,2)
        # NOTE: 2018-08-01 08:55:15
        # except for "units", all other values in this dictionary are PODs, 
        # not python quantities !!!
        #self._calibration_ = DataBag(allow_none=True)
        #self._calibration_ = dict()
        self._calibration_ = Bunch()
        
        # NOTE: 2018-09-11 16:01:09
        # allow overriding calibration with atomic elements, if specified 
        # (hence their default are set to None, but checked below against this if
        # data is not a VigraArray, AxisTags, AxisInfo, or str)
        if isinstance(data, vigra.VigraArray):
            self._axistags_ = data.axistags
            
            for axinfo in data.axistags:
                self._initialize_calibration_with_axis_(axinfo)
        
        elif isinstance(data, vigra.AxisTags):
            self._axistags_ = data
            
            for axinfo in data:
                self._initialize_calibration_with_axis_(axinfo)
                    
        elif isinstance(data, vigra.AxisInfo):
            # NOTE: 2018-08-27 11:48:32
            # construct AxesCalibration from the description attribute of data
            # using default values where necessary (see parseDescriptionString)
            # NOTE: calibration string may be wrong (from old API)
            # as a rule of thumb: rely on the axistags' properties to set relevant fields!
            #
            # NOTE: 2018-09-04 16:54:13
            # just make sure that we parse everything that's there, without assumptions
            # then set defaults for missing fields HERE
            self._axistags_ = vigra.AxisTags(data)
            
            self._initialize_calibration_with_axis_(data)
            
            #print("self._calibration_", self._calibration_)
            
            # NOTE: 2018-09-11 17:26:37
            # allow setting up atomic elements when constructing from a single AxisInfo object
            _, _axiscal = self._generate_atomic_calibration_dict_(axisname=axisname,
                                                                  units=units,
                                                                  origin=origin,
                                                                  resolution=resolution,
                                                                  channel=channel,
                                                                  channelname=channelname)
            
            self._calibration_[data.key].update(_axiscal)
                            
        elif isinstance(data, str):
            # construct from a calibration string
            if not AxesCalibration.hasCalibrationString(str):
                warnings.warn("The string parameter is not a proper calibration string")
                return # an empty AxesCalibration object
            
            cal = AxesCalibration.parseDescriptionString(data)
            
            key = cal.get("axiskey", "?") # rely on parsed calibration string
            
            if key not in axisTypeKeys:
                key = "?"
            
            self._calibration_[key] = dict()
            self._calibration_[key]["axiskey"] = key
            self._calibration_[key]["axisname"] = cal.get("axisname", axisTypeName(axisTypeKeys[Key]))
            self._calibration_[key]["axistype"] = cal.get("axistype", axisTypeKeys[key])
            
            if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
                channel_keys = [channel_index for channel_index in cal.keys() \
                                if isinstance(channel_index, int) and isinstance(cal[channel_index], dict)]
                
                if len(channel_keys) > 0:
                    for channel_index in channel_keys:
                        self._calibration_[key][channel_index] = dict()
                        
                        self._calibration_[key][channel_index]["name"] = cal[channel_index].get("name", None)
                        self._calibration_[key][channel_index]["units"] = cal[channel_index].get("units", pq.dimensionless)
                        self._calibration_[key][channel_index]["origin"] = cal[channel_index].get("origin", 0.0)
                        self._calibration_[key][channel_index]["resolution"] = cal[channel_index].get("resolution", 1.0)
                        
                else:
                    self._calibration_[key][0] = dict()
                    self._calibration_[key][0]["name"] = None
                    self._calibration_[key][0]["units"] = pq.dimensionless
                    self._calibration_[key][0]["origin"] = 0.0
                    self._calibration_[key][0]["resolution"] = 1.0
                    
            self._axistags_ = vigra.AxisTags(vigra.AxisInfo(key=key,
                                                              typeFlags = self._calibration_[key]["axistype"],
                                                              resolution = self._calibration_[key]["resolution"]))
            
            _, _axiscal = self._generate_atomic_calibration_dict_(axisname=axisname,
                                                                  units=units,
                                                                  origin=origin,
                                                                  resolution=resolution,
                                                                  channel=channel,
                                                                  channelname=channelname)
            
            #_, _axiscal = self._generate_atomic_calibration_dict_(initial_axis_cal=self._calibration_[data.key],
                                                                    #axisname=axisname,
                                                                    #units=units,
                                                                    #origin=origin,
                                                                    #resolution=resolution,
                                                                    #channel=channel,
                                                                    #channelname=channelname)
            
            self._calibration_[data.key].update(_axiscal)
                            
        else:
            # construct an AxesCalibration object from atomic elements supplied as arguments
            
            # NOTE: 2018-08-28 09:22:14
            # allow for units to be None, but then require that origin & resolution
            # are python Quantities with compatible units
            # otherwise, if units are Quantity or UnitQuantity accept origin & resolution
            # as floating point scalars OR Quantities but in the latter case raise exception
            # if their units are not compatible with those of "units" parameter
            if any(arg is None for arg in [axistype, axisname, units, origin, resolution]):
                raise TypeError("When data is None the following parameters must not be None: axistype, axisname, units, origin, resolution")
            
            _axistag, _axiscal = self._generate_atomic_calibration_dict_(axistype=axistype,
                                                                         axisname=axisname,
                                                                         units=units,
                                                                         origin=origin,
                                                                         resolution=resolution,
                                                                         channel=channel,
                                                                         channelname=channelname)
            
            self._axistags_ = _axistag
            self._calibration_[_axiscal["axiskey"]] = _axiscal
            
            ## NOTE: 2018-08-28 10:10:35
            ## figure out units/origin/resolution
            
        assert [ax.key in self._calibration_.keys() for ax in self._axistags_], "Mismatch between axistags keys and the keys in the calibration dictionary"
        
        # NOTE: 2018-09-05 11:16:00
        # this is likely to be redudant, but keep it so that we enforce upgrading
        # the axis calibrations in data generated with old API
        for ax in self._axistags_:
            self._axistags_[ax.key] = self.calibrateAxis(ax)
            
    def __iter__(self):
        yield from (k for k in self._calibration_.keys() if k in self._axistags_)
        
    def __contains__(self, item):
        return item in self._calibration_.keys()
    
    def __getitem__(self, key):
        if key not in self:
            raise KeyError(f"Axis key {key} not found")
        
        return self._calibration_[key]
            
    def _adapt_channel_index_spec_(self, axiskey, channel):
        if axiskey not in self._calibration_.keys():
            raise KeyError("Axis key %s not found" % axiskey)
        
        if channel not in self._calibration_[axiskey].keys():
            channel_indices = [k for k in self._calibration_[axiskey].keys() if isinstance(k, str) and k.startswith("channel_")]
            if len(channel_indices):
                if isinstance(channel, int):
                    if channel < 0 or channel >= len(channel_indices):
                        raise ValueError("Invalid channel index specified: %d" % channel)
                    #ch_ndx = f"channel_{channel}"
                    channel = channel_indices[channel]
                    
                elif isinstance(channel, str):
                    if is_numeric_string(channel) or not channel.startswith("channel_"):
                        ch_ndx = f"channel_{channel}"
                        
                    else:
                        ch_ndx = channel
                        
                    if ch_ndx not in channel_indices:
                        raise RuntimeError(f"No channel calibration data found for channel {channel}")
                
            else:
                raise RuntimeError(f"No channel calibration data found for channel {channel}")
            
        return channel
    
    def _channel_str(self, channel:typing.Union[str, int]) -> str:
        if isinstance(channel, int):
            return f"channel_{channel}"
        
        elif isinstance(channel, str):
            if is_numeric_string(channel) or not channel.startswith("channel_"):
                return f"channel_{channel}"
            
            return channel
        
        else:
            raise TypeError(f"'channel' expected an int or str; got {type(chanel).__name__} instead")
    
    def _generate_atomic_calibration_dict_(self,
                                             axistype:typing.Optional[typing.Union[vigra.AxisType, int]] = None,
                                             axisname:typing.Optional[str] = None,
                                             units:typing.Optional[pq.Quantity] = None, 
                                             origin:typing.Optional[float] = None, 
                                             resolution:typing.Optional[float] = None, 
                                             channel:typing.Optional[int] = None, 
                                             channelname:typing.Optional[str] = None) -> None:
        """Generates a calibration dictionary from atomic elements.
        
        Optionally the nested channel calibration dictionaries will also be generated
        
        This is to allow overriding atomic calibration elements when an axistags 
        or axisinfo or vigra array (with axistags) was passed to c'tor
        """
        result = DataBag(allow_none = True)
        
        # set up units
        if isinstance(units, pq.Quantity):
            units = units.units
            
        elif isinstance(units, str):
            try:
                units = pq.registry.unit_registry[units]
                
            except Exception as e:
                units = pixel_unit
                
        elif isinstance(units, pq.dimensionality.Dimensionality):
            units = [k for k in units.keys()][0]
                
        else: # anything else
            if isinstance(origin, pq.Quantity):
                units = origin.units
                
            elif isinstance(resolution, pq.Quantity):
                units = resolution.origin
                
            else:
                units = pixel_unit
                
        # set up origin
        if isinstance(origin, pq.Quantity):
            if not units_convertible(origin, units):
                raise TypeError(f"Origin units {origin.units} are incompatible with units {units}")
            
            if origin.units != units:
                origin = float(origin.rescale(units).magnitude.flatten()[0])
            
        elif isinstance(origin, numbers.Number):
            origin = float(origin)
            
        else:
            raise TypeError(f"Origin expected to be a Python Quantity or a number; got {type(origin).__name__} instead")
        
        # set up resolution
        if isinstance(resolution, pq.Quantity):
            if not units_convertible(resolution, units):
                raise TypeError(f"Resolution units {resolution.units} are incompatible with units {units}")
            
            if resolution.units != units:
                resolution = float(resolution.rescale(units).magnitude.flatten()[0])
            
        elif isinstance(resolution, numbers.Number):
            resolution = float(resolution)
        
        else:
            raise TypeError(f"Resolution expected to be a Python Quantity or a number; got {type(resolution).__name__} instead")
                
        # 4) set up axis type, name, and key
        if axistype is None:
            axiskey = "?"
            #axistype = result.get("axistype", None)
            
        elif isinstance(axistype, str): 
            # NOTE: 2018-08-27 23:56:50
            # axistype supplied as a string; this can be:
            # a) a valid axis info key string (1 or 2 characters) defined in __all_axis_tag_keys__
            # b) a descriptive string recognizable by axisTypeFromString
            #
            # we fall back on UnknownAxisType
            
            if axistype in axisTypeKeys: # check if axistype is supplied as an axis info key string
                axiskey = axistype
                axistype = axisTypeKeys[axiskey]
                
            else: # maybe axistype is supplied as a standard descriptive string
                axistype = axisTypeFromString(axistype) # also does reverse lookup
                
                axiskey = [k for k in axisTypeKeys.keys() if axisTypeKeys[k] == axistype]
                
                if len(axiskey):
                    axiskey = axiskey[0]
                    
                else:
                    axiskey = "?"
                    
        elif isinstance(axistype, (vigra.AxisType, int)):
            # NOTE: 2018-08-28 11:07:54
            # "reverse" lookup of axisTypeKeys
            axiskey = [k for k in axisTypeKeys.keys() if axisTypeKeys[k] == axistype]
            
            if len(axiskey):
                axiskey = axiskey[0]
                
            else:
                axiskey = "?"
                
        else:
            axiskey = "?"
                
        # 5) set up any channel calibration nested dicts
        
        # if axistype is unknown (the default) and a channel is specified then 
        # coerce Channels type and key;
        
        # channels will be ignored if axis has a specified type other than Channels
        if isinstance(channel, int):
            if channel < 0:
                raise ValueError("channel index must be an integer >= 0; got %d instead" % channel)
            
            if axistype is None or axistype & vigra.AxisType.UnknownAxisType:
                axistype = vigra.AxisType.Channels
                axiskey = "c"
                
            elif axistype & vigra.AxisType.Channels == 0:
                warnings.warn("Channel index will be ignored for axis of type %s" % axistype)
        
        if axiskey is not None:
            result["axiskey"]  = axiskey
            
        else:
            if "axiskey" not in result.keys():
                raise RuntimeError("axiskey missing from initial calibration and could not be determined")
            
        if isinstance(axisname, str):
            result["axisname"] = axisname
            
        elif axisname is None and "axisname" not in result.keys():
            result["axisname"] = axisTypeName(axistype)
            
        if axistype is not None:
            if axistype != axisTypeKeys[axiskey]:
                warnings.warn("Mismatch between axis type %s and axis type key %s" % (axisTypeName(axistype), axiskey), RuntimeWarning)
            
            result["axistype"]  = axistype
            
        else:
            if "axistype" not in result.keys():
                raise RuntimeError("axistype must be specified when absent from initial calibration dictionary")
            
        # 4) if there is a channel specified and axis is of type Channels, 
        # then units/origin/resolution go there
        # othwerwise they go to whole axis
        
        # NOTE: 2018-08-28 00:08:12
        # units, origin and resolution __init__ parameters are considered
        # to apply to the whole axis, unless a channel index is specified
        # in which case they are applied to the particular channel and NOT
        # to the whole axis; see also NOTE: 2018-08-28 09:15:57
        #
        # also see NOTE: 2018-08-28 09:22:14 for how we interpret the 
        # units/origin/resolution parameters
        if result["axistype"] & vigra.AxisType.Channels:
            if isinstance(channel, int):
                # NOTE: 2018-08-28 09:15:57
                # apply units, origin, resolution to the specified channel
                if channel < 0:
                    raise ValueError("channel index must be an integer >= 0; got %d instead" % channel)
                
                if channel not in result.keys():
                    # special case for a new channel
                    # NOTE: 2018-09-11 17:08:21
                    # check all are given if new channel
                    user_units = result.get("units", None)
                    user_origin = result.get("origin", None)
                    user_resolution = result.get("resolution", None)
                    
                    if any([v is None for v in (user_units, user_origin, user_resolution)]):
                        raise TypeError("units, origin or resolution must all be specified for a new channel")
                    
                    result[channel] = dict()
                    result[channel]["name"] = channelname # may be None
                    
                # back to general case
                if isinstance(channelname, str): 
                    # previously defined channel name won't be overwritten:
                    # if it already exists then if channelname is None will NOT
                    # raise error at NOTE: 2018-09-11 17:08:21
                    result[channel]["name"] = channelname # may be None
                
                if user_units is not None:
                    # previously defined channel units won't be overwritten:
                    # if already present then if user_units is None won't raise
                    # at NOTE: 2018-09-11 17:08:21
                    result[channel]["units"] = user_units
                    
                #else:
                    #is "units" not in result[channel]["units"] = arbitrary_unit
                
                if user_origin is not None:
                    # see comments for user_units & channelname
                    result[channel]["origin"] = user_origin
                    
                #else:
                    #result[channel]["origin"] = 
                
                if user_resolution is not None:
                    # see comments for user_origin & user_units & channelname
                    result[channel]["resolution"] = user_resolution
                
            nChannels = len([k for k in result.keys() if isinstance(k, int)])
            
            # for a single channel in a channel axis we allow the units/origin/resolution
            # to be duplicated in the main axis calibration i.e. without requiring
            # a channel specificiation
            if nChannels <= 1: # 0 or 1 channel
                if user_units is not None:
                    result["units"] = user_units
                    
                if user_origin is not None:
                    result["origin"] = user_origin
                    
                if user_resolution is not None:
                    result["resolution"] = user_resolution
                
            if nChannels  == 0:
                # generate a mandatory channel if axis is Channels
                if 0 not in result.keys():
                    # special case for a new channel with index 0
                    if any([v is None for v in (user_units, user_origin, user_resolution)]):
                        raise TypeError("units, origin and resolution must be specified")
                    # allow no channel name given 
                    
                    result[0] = dict()
                    result[0]["name"] = channelname # may be None
                    
                # back to general case:
                if isinstance(channelname, str):
                    # potentially override existing channel 0 definition
                    result[0]["name"] = channelname 
                
                if user_units is not None:
                    result[0]["units"] = user_units
                
                if user_origin is not None:
                    result[0]["origin"] = user_origin
                
                if user_resolution is not None:
                    result[0]["resolution"] = user_resolution
                
        else:
            # finally for non-channel axis store data in the main calibration dict
            if user_units is not None:
                result["units"] = user_units
                
            if user_origin is not None:
                result["origin"] = user_origin
                
            if user_resolution is not None:
                result["resolution"] = user_resolution
            
        #print(axiskey, axistype)
        axistag = vigra.AxisTags(vigra.AxisInfo(key = result["axiskey"], 
                                                typeFlags = result["axistype"],
                                                resolution = result["resolution"]))
        
        return axistag, result
        
    def _upgrade_API_(self):
        def _upgrade_attribute_(old_name, new_name, attr_type, default):
            needs_must = False
            if not hasattr(self, new_name):
                needs_must = True
                
            else:
                attribute = getattr(self, new_name)
                
                if not isinstance(attribute, attr_type):
                    needs_must = True
                    
            if needs_must:
                if hasattr(self, old_name):
                    old_attribute = getattr(self, old_name)
                    
                    if isinstance(old_attribute, attr_type):
                        setattr(self, new_name, old_attribute)
                        delattr(self, old_name)
                        
                    else:
                        setattr(self, new_name, default)
                        delattr(self, old_name)
                        
                else:
                    setattr(self, new_name, default)
                    
        if hasattr(self, "apiversion") and isinstance(self.apiversion, tuple) and len(self.apiversion)>=2 and all(isinstance(v, numbers.Number) for v in self.apiversion):
            vernum = self.apiversion[0] + self.apiversion[1]/10
            
            if vernum >= 0.2:
                return
            
        
        _upgrade_attribute_("__axistags__", "_axistags_", vigra.AxisTags, vigra.AxisTags())
        _upgrade_attribute_("__calibration__", "_calibration_", dict, dict())
        
        self.apiversion = (0, 2)
            
    def _initialize_calibration_with_axis_(self, axinfo):
        self._calibration_[axinfo.key] = DataBag(allow_none=True)
        #self._calibration_[axinfo.key] = dict()
        
        cal = AxesCalibration.parseDescriptionString(axinfo.description)
        
        #print("AxesCalibration._initialize_calibration_with_axis_(AxisInfo) cal:", cal)
        
        self._calibration_[axinfo.key]["axiskey"] = axinfo.key
        
        axisname = cal.get("axisname", axisTypeName(axinfo))
        
        if not isinstance(axisname, str) or len(axisname.strip()) == 0:
            axisname = axisTypeName(axinfo)

        self._calibration_[axinfo.key]["axisname"] = axisname
        
        #see NOTE: 2018-08-27 09:42:04
        # NOTE: override calibration string
        self._calibration_[axinfo.key]["axistype"] = axinfo.typeFlags 
        
        # see NOTE: 2018-08-27 11:43:30
        self._calibration_[axinfo.key]["units"]       = cal.get("units", pixel_unit)
        self._calibration_[axinfo.key]["origin"]      = cal.get("origin", 0.0)
        self._calibration_[axinfo.key]["resolution"]  = cal.get("resolution", 1.0)
        
        if axinfo.isChannel():
            channel_indices = [channel_ndx for channel_ndx in cal.keys() if isinstance(cal[channel_ndx], DataBag)]
            #channel_indices = [channel_ndx for channel_ndx in cal.keys() \
                                #if isinstance(channel_ndx, int) and isinstance(cal[channel_ndx], DataBag)]
            
            #print("AxesCalibration._initialize_calibration_with_axis_(AxisInfo) channel_indices:", channel_indices)
            
            if len(channel_indices):
                for k, channel_ndx in enumerate(channel_indices):
                    if isinstance(channel_ndx, int):
                        ch_ndx = f"channel_{channel_ndx}"
                    elif isinstance(channel_ndx, str):
                        if is_numeric_string(channel_ndx):
                            ch_ndx = f"channel_{channel_ndx}"
                        else:
                            if not channel_ndx.startswith("channel_"):
                                ch_ndx = f"channel_{channel_ndx}"
                            else:
                                ch_ndx = channel_ndx
                    else:
                        raise TypeError(f"channel_ndx must be a str or an int, got {type(channel_ndx).__name__} instead")

                    self._calibration_[axinfo.key][ch_ndx] = DataBag(allow_none=True)()
                    self._calibration_[axinfo.key][ch_ndx]["name"] = cal[channel_ndx].get("name", None)
                    self._calibration_[axinfo.key][ch_ndx]["units"] = cal[channel_ndx].get("units", arbitrary_unit)
                    self._calibration_[axinfo.key][ch_ndx]["origin"] = cal[channel_ndx].get("origin", 0.0)
                    self._calibration_[axinfo.key][ch_ndx]["resolution"] = cal[channel_ndx].get("resolution", 1.0)
                    
                    if len(channel_indices) == 1:
                        chanel_index = channel_indices[0]
                        # if one channel only, also copy this data to the main axis calibration dict
                        if isinstance(channel_index, int):
                            ch_ndx = f"channel_{channel_index}"
                        elif isinstance(channel_index, str):
                            if is_numeric_string(channel_index):
                                ch_ndx = f"channel_{channel_index}"
                            else:
                                if not channel_index.startswith("channel_"):
                                    ch_ndx = f"channel_{channel_index}"
                                else:
                                    ch_ndx = channel_index
                        else:
                            raise TypeError(f"channel_indices[0] must be int or str; got {type(channel_index).__name__} instead")
                        
                        self._calibration_[axinfo.key]["units"] = self._calibration_[axinfo.key][channel_index]["units"]
                        self._calibration_[axinfo.key]["origin"] = self._calibration_[axinfo.key][channel_index]["origin"]
                        self._calibration_[axinfo.key]["resolution"] = self._calibration_[axinfo.key][channel_index]["resolution"]
                    
            else:
                self._calibration_[axinfo.key]["channel_0"] = DataBag(allow_none=True)
                self._calibration_[axinfo.key]["channel_0"]["name"]        = None # string or None
                self._calibration_[axinfo.key]["channel_0"]["units"]       = arbitrary_unit # python UnitQuantity or None
                self._calibration_[axinfo.key]["channel_0"]["origin"]      = 0.0 # number or None
                self._calibration_[axinfo.key]["channel_0"]["resolution"]  = 1.0 # number or None
                        
    def is_same_as(self, other, key, channel = 0, ignore=None, 
                   rtol = relative_tolerance, 
                   atol =  absolute_tolerance, 
                   equal_nan = equal_nan):
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
                
                # NOTE: for a single channel per channel axis the channel index does not matter
                
                #if result:
                    #if self.channels > 1:
                        ## NOTE: 2018-08-01 17:49:15
                        ## perhaps one should make sure the channel indices are the same
                        #result &= all(channel in self.channelIndices for channel in other.channelIndices)
                        
                
                if result:
                    for chIndex in range(len(self.channelIndices(key))):
                        if not ignoreUnits:
                            channel_units_compatible = self.getUnits(key, self.channelIndices(key)[str(chIndex)]) == other.getUnits(key, other.channelIndices(key)[str(chIndex)])
                            #print(channel_units_compatible)
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
        
    def __repr__(self):
        result = list()
        result.append("%s:\n"             % self.__class__.__name__)
        
        for k, key in enumerate(self._calibration_.keys()):
            result.append("Axis %d:\n" % k)
            result.append("axisname: %s;\n"       % self.getAxisName(key))
            result.append("type: %s;\n"           % self.getAxisType(key))
            result.append("key: %s;\n"            % key)
            result.append("origin: %s;\n"         % self.getOrigin(key))
            result.append("resolution: %s;\n"     % self.getResolution(key))

            channels = [c for c in self._calibration_[key].keys() if isinstance(c, str) and c.startswith("channel_")]
            
            if len(channels):
                if len(channels) == 1:
                    result.append("1 channel:\n")
                else:
                    result.append("%d channels:\n" % len(channels))
            
                for c in channels:
                    chstring = [c]
                    #chstring = ["\tchannel %d:\n" % c]
                    chstring.append("\t\tname: %s,\n" % self.getChannelName(c))
                    chstring.append("\t\tunits: %s,\n" % self.getUnits(key, c))
                    chstring.append("\t\torigin: %s,\n" % self.getOrigin(key, c))
                    chstring.append("\t\tresolution: %s;\n" % self.getResolution(key, c))
                    
                    chstring = " ".join(chstring)
                    
                    result.append(chstring)
                
            result.append("\n")
        
        return " ".join(result)
    
    def _get_attribute_value_(self, attribute:str, key:str, channel:int=0):
        if not isinstance(attribute, str):
            raise TypeError("'attribute' parameter expected to be a str; got %s instead" % type(attribute).__name__)
        
        if not isinstance(key, str):
            raise TypeError("'key' parameter expected to be a str; got %s instead" % type(key).__name__)
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s is not calibrated by this object" % key)

        if not isinstance(channel, int):
            raise TypeError("'channel' parameter expected to be an int; got %s instead" % type(channel).__name__)
        
        if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
            channel = self._adapt_channel_index_spec_(key, channel)
            
            if attribute not in self._calibration_[key][channel].keys():
                raise KeyError("Unknown attribute %s for axis %s" % (attribute, self._calibration_[key]["axistype"]))
            
            return self._calibration_[key][channel][attribute]
        
        else:
            if attribute not in self._calibration_[key].keys():
                raise KeyError("Unknown attribute %s for axis %s" % (attribute, self._calibration_[key]["axistype"]))
            
            return self._calibration_[key][attribute]
    
    def _set_attribute_value_(self, attribute:str, value:object, key:str, channel:int=0):
        if not isinstance(attribute, str):
            raise TypeError("'attribute' parameter expected to be a str; got %s instead" % type(attribute).__name__)
        
        if not isinstance(key, str):
            raise TypeError("'key' parameter expected to be a str; got %s instead" % type(key).__name__)
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s is not calibrated by this object" % key)

        if not isinstance(channel, int):
            raise TypeError("'channel' parameter expected to be an int; got %s instead" % type(channel).__name__)
        
        if attribute == "axistype":
            warnings.warn("Axis type cannot be set in this way", RuntimeWarning)
            return 
        
        if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
            channel = self._adapt_channel_index_spec_(key, channel)
            if attribute not in self._calibration_[key][channel].keys():
                raise KeyError("Unknown attribute %s for axis %s" % (attribute, self._calibration_[key]["axistype"]))
            
            self._calibration_[key][channel][attribute] = value
            
        else:
            if attribute not in self._calibration_[key].keys():
                raise KeyError("Unknown attribute %s for axis %s" % (attribute, self._calibration_[key]["axistype"]))
            
            self._calibration_[key][attribute] = value
    
    
    def hasAxis(self, key):
        """Queries if the axis key is calibrated by this object
        """
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        return key in self._calibration_.keys()
    
    @property
    def hasChannelAxis(self):
        return any(value["axistype"] & vigra.AxisType.Channels for value in self._calibration_.values())
    
    #@property
    def channelIndicesAndNames(self):
        channelAxis = self.axistags[self.axistags.channelIndex]
        
        key = channelAxis.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s not found in this AxesCalibration" % key)
        
        if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
            return sorted([(item[0], item[1]["name"]) for item in self._calibration_[key].items() if isinstance(item[0],int)], key = lambda x:x[0])
        
        else:
            return [tuple()]
    
    #@property
    def channelIndices(self, key="c"):
        channelAxis = self.axistags[self.axistags.channelIndex]
        
        key = channelAxis.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s not found in this AxesCalibration" % key)
        
        if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
            return sorted([key for key in self._calibration_[key].keys() if isinstance(key, str) and key.startswith("channel_")])
        
        else:
            return []
    
    #@property
    def channelNames(self):
        channelAxis = self.axistags[self.axistags.channelIndex]
        
        key = channelAxis.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis key %s is not calibrated by this object" % key)
        
        channel_indices = self.channelIndices(key)
        
        if len(channel_indices):
            return [self._calibration_[key][c].get("name", None) for c in channel_indices]
        
    def numberOfChannels(self):
        channelAxis = self.axistags[self.axistags.channelIndex]
        
        key = channelAxis.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis key %s does not have calibration data" % key)
        
        if self._calibration_[key]["axistype"] & vigra.AxisType.Channels == 0:
            raise ValueError("Axis with key %s is not a Channels axis" % key)
        
        nChannels = [k for k in self._calibration_[key].keys() if isinstance(k, int)]
        
        if len(nChannels) == 0:
            return 1
        
        else:
            return len(nChannels)
        
    def getChannelName(self, channel_index):
        if self.axistags.channelIndex == len(self.axistags):
            raise KeyError("No channel axis exists in this calibration object")
        
        channelAxis = self.axistags[self.axistags.channelIndex]
        
        key = channelAxis.key
            
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Channel axis does not have calibration data")
        
        if isinstance(channel_index, int):
            ch_ndx = f"channel_{channel_index}"
        
        elif isinstance(channel_index, str):
            if is_numeric_string(channel_index) or not channel_index.startswith("channel_"):
                ch_ndx = f"channel_{channel_index}"
            else:
                ch_ndx = channel_index
                
        else:
            raise TypeError(f"'channel_index' expected an int or str; got {type(channel_inde).__name__} instead")
                
        
        channel_index = self._adapt_channel_index_spec_(key, ch_ndx)
        
        return self._calibration_[key][channel_index].get("name", None)
            
    def getAxisType(self, key):
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s not found in this AxesCalibration" % key)
        
        return self._calibration_[key].get("axistype", vigra.AxisType.UnknownAxisType)
    
    def getAxisName(self, key):
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s not found in this AxesCalibration" % key)
        
        return self._calibration_[key].get("axisname", None)
    
    def getCalibratedIntervalAsSlice(self, value, key, channel = 0):
        """Returns a slice object for a half-open interval of calibrated coordinates.
        
        Parameters:
        ==========
        value: tuple, list or numpy array with two elements representing a pair
                of start, stop (exclusive) interval values: [start, stop)
                
            the elements can be scalar floats, or python Quantities with the 
            same units as the axis specified by "key"; both elements must be the
            same Python data type.
        
        key: vigra.AxisInfo, a str (valid AxisInfo key string) or an int
            In either case the key should resolve to an axis info stored in this
            AxesCalibration object
            
        Returns:
        =======
        a slice object useful for slicing the axis given by "key"
        
        See also imageprocessing.imageIndexTuple
        
        """
        if isinstance(key, vigra.AxisInfo):
            if key not in self._axistags_:
                raise KeyError("AxisInfo with key %s not found" % key.key)
            key = key.key
            
        elif isinstance(key, int):
            axinfo = self._axistags_[key]
            key = axinfo.key
            
        elif not isinstance(key, str):
            raise TypeError("key expected to be a str (AxisInfo key), an int or an axisinfo")
            
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis %s not found in this AxesCalibration object" % key)
        
        if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
            
            if channel not in self._calibration_[key].keys():
                raise KeyError("Channel %d not found for axis %s with key %s" % (channel, self._calibration_[key]["axisname"], self._calibration_[key]["axiskey"]))
        
            myunits = self._calibration_[key][channel]["units"]
            
        else:
            myunits = self._calibration_[key]["units"]
        
        if isinstance(value, (tuple, list)):
            value = list(value)
            
            if len(value) != 2:
                raise TypeError("Expecting a sequence of two elements; got %d instead" % len(value))
            
            if all([isinstance(v, numbers.Real) for v in value]):       # convert sequence of two floats to a quantity array
                value = np.array(value) * myunits
                
            elif all([isinstance(v, pq.Quantity) for v in value]):      # convert sequence of two quantities to a quantity array
                if not all([units_convertible(v, myunits) for v in value]):
                    raise TypeError("Interval units not compatible with this axis units %s" % myunits)
                
                units = value[0].units
                
                if value[0].ndim != 1:
                    value[0] = value[0].flatten()
                
                if value[1].ndim != 1:
                    value[1] = value[1].flatten()
                    
                value = np.array([v.magnitude for v in value]) * units
                
        elif isinstance(value, pq.Quantity):                            # check it is already a quantity array
            if not units_convertible(value, myunits):
                raise TypeError("interval units %s are not compatible with this axis units %s" % (value.units, myunits))
            
            if value.size != 2:
                raise TypeError("When an array, 'value' must have two elements only; got %d instead" % value.size)
            
            value = value.flatten()
            
        elif isinstance(value, np.ndarray):                             # make it a quantity array
            if value.size != 2:
                raise TypeError("When an array, 'value' must have two elements only; got %d instead" % value.size)
            
            value = value.flatten() * myunits
            
        else:
            raise TypeError("Value expected to be a sequence or numpy array of two real scalars or Python Quantity objects; got %s instead" % type(value).__name__)
        
        start, stop = value / self.getResolution(key)
        
        return slice(int(start), int(stop))
    
    def setAxisName(self, value, key):
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s not found in this AxesCalibration" % key)
        
        if isinstance(value, (str, type(None))):
            self._calibration_[key]["axisname"] = value
            
        else:
            raise TypeError("axis name must be a str or None; got %s instead" % type(value).__name__)
        
    def getUnits(self, key:(str, vigra.AxisInfo), channel:int = 0):
        if isinstance(key, vigra.AxisInfo):
            key = key.key
            
        return self._get_attribute_value_("units", key, channel)
    
    def setUnits(self, value, key:(str, vigra.AxisInfo), channel:int=0):
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if not isinstance(value, (pq.Quantity, pq.unitquantity.UnitQuantity)):
            raise TypeError("Expecting a python Quantity or UnitQuantity; got %s instead" % type(value).__name__)

        self._set_attribute_value_("units", value, key, channel)

    def getDimensionlessOrigin(self, key, channel=0):
        if isinstance(key, vigra.AxisInfo):
            key = key.key
            
        return self._get_attribute_value_("origin", key, channel)
    
    def getOrigin(self, key, channel=0):
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s is not calibrated by this object" % key)
        
        if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
            channel = self._adapt_channel_index_spec_(key, channel)
            return self._calibration_[key][channel]["origin"] * self._calibration_[key][channel]["units"]
        
        return self._calibration_[key]["origin"] * self._calibration_[key]["units"]
    
    def setOrigin(self, value, key, channel=0):
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s not found in this AxesCalibration" % key)
        
        if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
            channel = self._adapt_channel_index_spec_(key, channel)
            
            myunits = self._calibration_[key][channel]["units"]
            
        else:
            myunits = self._calibration_[key]["units"]
        
        if isinstance(value, numbers.Number):
            if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
                self._calibration_[key][channel]["origin"] = value
                
            else:
                self._calibration_[key]["origin"] = value
            
        elif isinstance(value, pq.Quantity):
            if value.magnitude.size != 1:
                raise ValueError("origin must be a scalar quantity; got %s" % value)
            
            # NOTE: 2018-08-28 10:51:59
            # allow negative origins (offsets!)
            #if value.magnitude < 0:
                #raise ValueError("origin cannot be negative; got %s" % value)
            
            self_dim = pq.quantity.validate_dimensionality(myunits)
            
            origin_dim = pq.quantity.validate_dimensionality(value.units)
            
            if self_dim != origin_dim:
                try:
                    cf = pq.quantity.get_conversion_factor(origin_dim, self_dim)
                    
                except AssertionError:
                    raise ValueError("Cannot convert from %s to %s" % (origin_dim.dimensionality, self_dim.dimensionality))
                
                value *= cf
                
            if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
                self._calibration_[key][channel]["origin"] = value.magnitude.flatten()[0]
                
            else:
                self._calibration_[key]["origin"] = value.magnitude.flatten()[0]
            
        else:
            raise TypeError("origin expected to be a float; got %s instead" % type(value).__name__)
    
    def getResolution(self, key, channel=0):
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s not calibrated by this object" % key)
        
        if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
            channel = self._adapt_channel_index_spec_(key, channel)
            
            return self._calibration_[key][channel]["resolution"] * self._calibration_[key][channel]["units"]
        
        return self._calibration_[key]["resolution"] * self._calibration_[key]["units"]
    
    def getDimensionlessResolution(self, key, channel=0):
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        return self._get_attribute_value_("resolution", key, channel)
    
    def setResolution(self, value, key, channel=0):
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s not found in this AxesCalibration" % key)
        
        if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
            channel = self._adapt_channel_index_spec_(key, channel)
            
            myunits = self._calibration_[key][channel]["units"]
            
        else:
            myunits = self._calibration_[key]["units"]
            
        
        if isinstance(value, numbers.Number):
            if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
                self._calibration_[key][channel]["resolution"] = value
                
            else:
                self._calibration_[key]["resolution"] = value
            
        elif isinstance(value, pq.Quantity):
            if value.magnitude.size != 1:
                raise ValueError("resolution must be a scalar quantity; got %s" % value)
            
            self_dim = pq.quantity.validate_dimensionality(myunits)
            res_dim = pq.quantity.validate_dimensionality(value.units)
            
            if self_dim != res_dim:
                try:
                    cf = pq.quantity.get_conversion_factor(res_dim, self_dim)
                    
                except AssertionError:
                    raise ValueError("Cannot convert from %s to %s" % (res_dim.dimensionality, self_dim.dimensionality))
                
                value *= cf
                
            if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
                self._calibration_[key][channel]["resolution"] = value.magnitude.flatten()[0]
                
            else:
                self._calibration_[key]["resolution"] = value.magnitude.flatten()[0]
            
        else:
            raise TypeError("resolution expected to be a float or a python Quantity; got %s instead" % type(value).__name__)
        
    @property
    def axiskeys(self):
        """A list of axiskeys
        """
        yield from (k for k in self)
        #keys = [key for key in self._calibration_]
        
        #if any([k not in self._axistags_ for k in keys]):
            #raise RuntimeError("Mismatch between the axistags keys and calibration keys")
        
        #return keys
    
    @property
    def keys(self):
        """Aalias to self.axiskeys
        """
        yield from self.axiskeys
    
    @property
    def axistags(self):
        """Read-only
        """
        return self._axistags_
    
    #@property
    def typeFlags(self, key):
        """Read-only
        """
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s is not calibrated by this object" % key)
        
        return self._calibration_[key]["axistype"]
    
    def addAxis(self, axisInfo, index = None):
        """Register a new axis with this AxesCalibration object.
        
        If the axis already exists, raises a RuntimeError.
        
        The calibration values for the new axis can be atomically set using
        the setXXX methods
        
        By default a Channels axis will get a single channel (singleton axis).
        More channels can then be added using setChannelCalibration(), and calibration
        data for each channel can be modified using other setXXX methods
            
        WARNING: this function breaks axes bookkeeping by the VigraArray object
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
        
        if axisInfo.key in self.axistags.keys() or axisInfo.key in self._calibration_.keys():
            raise RuntimeError("Axis %s already exists" % axisInfo.key)
        
        if index is None:
            self.axistags.append(axInfo)
            
        elif isinstance(index, int):
            if index < 0:
                raise ValueError("index must be between 0 and %d, inclusive" % len(self.axistags))
            
            if index == len(self.axistags):
                self.axistags.append(axInfo)
                
            elif index < len(self.axistags):
                self.axistags.insert(axInfo)
                
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

        for axInfo in new_axes:
            self._initialize_calibration_with_axis_(axInfo)
            self.calibrateAxis(axInfo)
        
        obsolete_keys = [key for key in self._calibration_.keys() if key not in self._axistags_.keys()]
        
        for key in obsolete_keys:
            self._calibration_.pop(key, None)
                
    def calibrationString(self, key):
        """Generates an axis calibration string.
        
        Generates an axis calibration string to be included in the AxisInfo 
        'description' property for the axis with specified key (and channel index,
        for a Channels axis)

        Returns an xml string with one of the following formats, depending on axis type:
        
        1) For a non-channels axis:
        ----------------------------
        
        <axis_calibration>
            <axistype>int</axistype>
            <axiskey>str</axiskey>
            <axisname>str</axisname>
            <units>str0</units>
            <origin>float</origin>
            <resolution>float</resolution>
        </axis_calibration>
        
        2) for a channel axis:
        ----------------------------
        
        <axis_calibration>
            <axistype>int</axistype>
            <axiskey>str</axiskey>
            <axisname>str</axisname>
            <channelX>
                <name>str</name>
                <units>str0</units>
                <origin>float</origin>
                <resolution>float</resolution>
            </channelX>
            <channelY>
                <name>str</name>
                <units>str0</units>
                <origin>float</origin>
                <resolution>float</resolution>
            </channelY
        </axis_calibration>
        """
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("No calibration data for axis key %s" % key)
        
        strlist = ["<axis_calibration>"]
        
        strlist += xmlutils.composeStringListForXMLElement("axiskey", self._calibration_[key]["axiskey"])
        
        strlist += xmlutils.composeStringListForXMLElement("axisname", self._calibration_[key]["axisname"])
        
        strlist += xmlutils.composeStringListForXMLElement("axistype", "%s" % self._calibration_[key]["axistype"])
        
        if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
            channel_indices = [ch_key for ch_key in self._calibration_[key].keys() if isinstance(ch_key, int)]
            
            if len(channel_indices):
                for channel_index in channel_indices:
                    strlist.append("<channel%d>" % channel_index)
                    strlist.append("<name>")
                    strlist.append("%s" % self._calibration_[key][channel_index]["name"])
                    strlist.append("</name>")
                    
                    strlist.append("<units>")
                    strlist.append("%s" % self._calibration_[key][channel_index]["units"].__str__().split()[1].strip())
                    strlist.append("</units>")
                    
                    strlist.append("<origin>")
                    strlist.append(str(self._calibration_[key][channel_index]["origin"]))
                    strlist.append("</origin>")
                    
                    strlist.append("<resolution>")
                    strlist.append(str(self._calibration_[key][channel_index]["resolution"]))
                    strlist.append("</resolution>")
                    
                    strlist.append("</channel%d>" % channel_index)
                    
            else:
                strlist.append("<channel0>")
                
                strlist.append("<name>")
                strlist.append(self._calibration_[key]["axisname"])
                strlist.append("</name")
                
                strlist.append("<units>")
                strlist.append("%s" % self._calibration_[key]["units"].__str__().split()[1].strip())
                strlist.append("</units>")
                
                strlist.append("<origin>")
                strlist.append(str(self._calibration_[key]["origin"]))
                strlist.append("</origin>")
                
                strlist.append("<resolution>")
                strlist.append(str(self._calibration_[key]["resolution"]))
                strlist.append("</resolution>")
                
                strlist.append("</channel0>")
        
        strlist.append("<units>")
        strlist.append("%s" % self._calibration_[key]["units"].__str__().split()[1].strip())
        strlist.append("</units>")
        
        strlist.append("<origin>")
        strlist.append(str(self._calibration_[key]["origin"]))
        strlist.append("</origin>")
        
        strlist.append("<resolution>")
        strlist.append(str(self._calibration_[key]["resolution"]))
        strlist.append("</resolution>")
        
        strlist.append("</axis_calibration>")
        
        return ''.join(strlist)
    
    @staticmethod
    def parseCalibrationString(s):
        """Alias to AxesCalibration.parseDescriptionString(s)
        """
        return AxesCalibration.parseDescriptionString(s)

    @staticmethod
    def parseDescriptionString(s):
        """Parses a string for axis calibration information and name.
        
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
        
        A dictionary with keys: "units", "origin", "resolution", "name"
            and possibly "channelX" with X a 0-based integral index
            where each channelX key in turn maps to a dictionary 
            with the four key members ("units", "origin", "resolution", "name")
            
            All fields get default values if missing in the string parameter:
            
            units = dimensionless
            
            origin = 0.0
            
            resolution = 1.0
            
            axisname = None
            
        If the calibration string contains channels ("channelX" tags), the
        calibration data for each channel will be returned as a nested dictionary
        mapped to 0-based integer keys. The nested dictionary fields (same as
        above except for "name" instead of "axisname") will also get default
        values (as above) if missing from the string. 
        
        
            
        
        The values are:
            units: a pq.Quantity (or pq.UnitQuantity)
            origin: a float >= 0
            resolution: a float >= 0
            "name": None or a str == the axis' name
            
            channelX: a dictionary with keys: "units", "origin", "resolution", "name"
            with values as above (name is the channelX's name)
        
        """
        import quantities as pq # make quantities local
        import xml.etree.ElementTree as ET
        
        def _parse_calibration_set_(element, isChannel=False):
            """Looks for elements with the following tags: name, units, origin, resolution
            """
            
            result = AxisCalibrationData()
            #result = DataBag()
            #result = dict()
            
            # NOTE: 2021-10-09 23:58:58
            # xml.etree.ElementTree.Element.getchildren() is absent in Python 3.9.7
            #children = element.getchildren()
            children = getXMLChildren(element)
            
            children_tags = [c.tag for c in children]
            
            # NOTE: 2018-08-22 15:28:30
            # relax the stringency; give units, orgin, resolution and name default values
            
            u = None
            
            if "units" in children_tags:
                unit_element = children[children_tags.index("units")]
                u_ = unit_element.text
                
                if len(u_) > 0:
                    u = unit_quantity_from_name_or_symbol(u_)
                    
            if u is None: 
                # NOTE: default value depends on whether this is a channel axis 
                # or not. 
                # NOTE: both arbitrary_unit and pixel_unit are in fact derived
                # from pq.dimensionless
                if isChannel:
                    u = channel_unit
                
                else:
                    u = pq.dimensionless
                    
            result["units"] = u
                
            o = None
            
            if "origin" in children_tags:
                origin_element = children[children_tags.index("origin")]
                o_ = origin_element.text
                
                if len(o_) > 0:
                    try:
                        o = eval(o_)
                        
                    except Exception as err:
                        traceback.print_exc()
                        #print("".format(err))
                        #print("Unexpected error:", sys.exc_info()[0])
                        warnings.warn("String could not be evaluated to a number or None", RuntimeWarning)
                        # NOTE fall through and leave o as None
                    
            if o is None:
                o = 0.0
                
            result["origin"] = 0.0
            
            r = None
            
            if "resolution" in children_tags:
                
                resolution_element = children[children_tags.index("resolution")]
                r_ = resolution_element.text
            
                if len(r_) > 0:
                    try:
                        r = eval(r_)
                        
                    except Exception as err:
                        traceback.print_exc()
                        #print("".format(err))
                        #print("Unexpected error:", sys.exc_info()[0])
                        print("String could not be evaluated to a number or None")
                        # NOTE fall through and leave r as None
                        
                
            if r is None:
                r = 1.0
                
            result["resolution"] = r
                
            if "name" in children_tags:
                name_element = children[children_tags.index("name")]
                name = name_element.text
                if not isChannel:
                    warnings.warn("'name' child found in %s for a non-channel axis" % element.tag, RuntimeWarning)
                
            elif "axisname" in children_tags:
                name_element = children[children_tags.index("axisname")]
                name = element.text
                if isChannel:
                    warngins.warn("'axisname' child found in %s element for a channel axis" % element.tag, RuntimeWarning)
                
            else:
                name  = None
                
            if isChannel:
                result["name"] = name
                
            else:
                result["axisname"] = name
            
            #print("parseDescriptionString _parse_calibration_set_ result:", result)

            return result
                
        if not isinstance(s, str):
            raise TypeError("Expected a string; got a %s instead." % type(s).__name__)
        
        # NOTE: 2018-08-22 22:38:24
        # thesse are the minimum requirements
        # if axistype turn out to be Channels, then we don't need units/origin/resolution
        # unless there is only one channel !
        
        result = dict() # a dictionary containig calibration data for this axis
        
        calibration_string = None
        
        name_string = None
        
        axiskey = None
        
        axisname = None
        
        axistype = None
        
        axisunits = None
        
        axisorigin = None
        
        axisresolution = None
        
        channels_dict = dict()
                
        # 1) find axis calibration string <axis_calibration> ... </axis_calibration>
        start = s.find("<axis_calibration>")
        
        if start > -1:
            stop  = s.find("</axis_calibration>")
            if stop > -1:
                stop += len("</axis_calibration>")
                calibration_string = s[start:stop]
        
        #print("parseDescriptionString calibration_string: %s" % calibration_string)
        
        # 2) parse axis calibration string if found
        if isinstance(calibration_string, str) and len(calibration_string.strip()) > 0:
            # OK, now extract the relevant xml string
            try:
                main_calibration_element = ET.fromstring(calibration_string)
                
                # make sure we're OK
                if main_calibration_element.tag != "axis_calibration":
                    raise ValueError("Wrong element tag; was expecting 'axis_calibration', instead got %s" % element.tag)
                
                # see NOTE: 2021-10-09 23:58:58
                # xml.etree.ElementTree.Element.getchildren() is absent in Python 3.9.7
                #element_children = main_calibration_element.getchildren()
                # NOTE: getchildren() replaced with getXMLChildren():
                element_children = getXMLChildren(main_calibration_element) # getXMLChildren defined in xmlutils
                
                for child_element in element_children:
                    # these can be <children_X> tags (X is a 0-based index) or a <name> tag
                    # ignore everything else
                    if child_element.tag.lower().startswith("channel"):
                        # found a channel XML element => this is a channel axis
                        
                        # use "channel" as boundary for split
                        cx = child_element.tag.lower().split("channel")
                        
                        # there may be no channel number
                        if len(cx[1].strip()):
                            chindex = eval(cx[1].strip())
                            
                        else: # no channel number => assign channel index 0 by default
                            chindex = len(channels_dict)
                            
                        try:
                            value = _parse_calibration_set_(child_element, True)
                            channels_dict[chindex] = value
                            
                            if channels_dict[chindex]["units"] == pq.dimensionless:
                                channels_dict[chindex]["units"] = arbitrary_unit
                            
                        except Exception as e:
                            # ignore failures
                            continue
                        
                    elif child_element.tag.lower() == "axiskey":
                        axiskey = child_element.text
                        
                    elif child_element.tag.lower() == "axistype":
                        axistype = axisTypeFromString(child_element.text)
                    
                    elif child_element.tag.lower() in ("axisname", "name"):
                        axisname = child_element.text # axis name!
                        
                    elif child_element.tag.lower() == "units":
                        axisunits = unit_quantity_from_name_or_symbol(child_element.text)
                        
                    elif child_element.tag == "origin":
                        if len(child_element.text) == 0:
                            axisorigin = 0.0
                        
                        else:
                            try:
                                axisorigin = eval(child_element.text)
                                
                            except Exception as err:
                                traceback.print_exc()
                                #print("".format(err))
                                #print("Unexpected error:", sys.exc_info()[0])
                                warnings.warn("String could not be evaluated to a number or None", RuntimeWarning)
                                    
                                axisorigin = 0.0
                        
                    elif child_element.tag == "resolution":
                        if len(child_element.text) == 0:
                            axisresolution = 1.0
                            
                        else:
                            try:
                                axisresolution = eval(child_element.text)
                                
                            except Exception as err:
                                traceback.print_exc()
                                #print("".format(err))
                                #print("Unexpected error:", sys.exc_info()[0])
                                warnings.warn("String could not be evaluated to a number or None", RuntimeWarning)
                                
                                axisresolution = 1.0
                                
            except Exception as e:
                traceback.print_exc()
                print("cannot parse calibration string %s" % calibration_string)
                raise e
            
        # 3) find name string <name> ... </name> for data from old API
                
        start = s.find("<name>")
        
        if start  > -1:
            stop = s.find("</name>")
            
            if stop > -1:
                stop += len("</name>")
                name_string = s[start:stop]
        
        #print("parseDescriptionString Name string: %s" % name_string)
        
        # NOTE: 2018-08-22 15:13:32
        # old API has axis & channel names in a separate string
        if isinstance(name_string, str) and len(name_string.strip()):
            try:
                name_element = ET.fromstring(name_string)
                
                if name_element.tag != "name":
                    raise ValueError("Wrong element tag: expecting 'name', got %s instead" % name_element.tag)
                
                #NOTE: see NOTE: 2021-10-09 23:58:58
                #for child_element in name_element.getchildren():
                for child_element in getXMLChildren(name_element):
                    if child_element.tag.startswith("channel"):
                        # check for a name element then add it if not already in result
                        cx = child_element.tag.split("channel")
                        
                        if len(cx[1].strip()):
                            chindex = eval(cx[1].strip())
                            
                        else:
                            chindex = len(channels_dict)
                            
                        # use this as name in case construct is
                        #<name><channelX>xxx</channelX></name>
                        chname = child_element.text
                        
                        #print(chname)
                        
                        ch_calibration = _parse_calibration_set_(child_element, True)
                        
                        #print("ch_calibration", ch_calibration)
                        
                        if ch_calibration["name"] is None:
                            ch_calibration["name"] = chname
                        
                        if ch_calibration["units"] == pq.dimensionless:
                            ch_calibration["units"] = arbitrary_unit
                        
                        if chindex in channels_dict.keys():
                            warnings.warn("AxesCalibration.parseDescriptionString: channel calibration for channel %d defined between separate <name>...</name> tags will overwrite the one defined in the main axis calibration string" % chindex, RuntimeWarning)
                            channels_dict[chindex].update(ch_calibration)
                            
                        else:
                            channels_dict[chindex] = ch_calibration
                            
            except Exception as e:
                traceback.print_exc()
                print("could not parse name string %s" % name_string)
                raise e
                
        # 4) check for inconsistencies
        if axisunits is None:
            axisunits = pixel_unit
            
        if axisorigin is None:
            axisorigin = 0.0
            
        if axisresolution is None:
            axisresolution = 1.0
        
        axiskey = axisTypeSymbol(axistype)
        #if axistype == vigra.AxisType.UnknownAxisType and axiskey !=? :
            #axiskey = axisTypeKeys.get(axistype, "?")
                
        ## infer axistype from axiskey, check if is the same as axistype
        #typebykey = [k for k in axisTypeKeys if axisTypeKeys[k] == axistype]
        
        ##print(f"AxesCalibration.parseDescriptionString: axistype {axistype}")
        ##print(f"AxesCalibration.parseDescriptionString: typebykey {typebykey}")
        
        #if len(typebykey) == 0:
            #axiskey = "?"
            #axistype = vigra.AxisType.UnknownAxisType
            
        #else:
            #if axistype != typebykey:
                #axiskey = reverse_mapping_lookup(axisTypeKeys, axistype)
                ##axiskey = axisTypeKeys[axistype]
        
        # 5) finally, populate the result
        
        result["axisname"]  = axisname
        result["axiskey"]   = axiskey
        result["axistype"]  = axistype
        
        # NOTE: overridden in __init__!
        #if axistype & vigra.AxisType.Channels: 
        if len(channels_dict) == 0:
            # no channel defined for a Channel Axis
            result[0] = dict()
            result[0]["name"] = axisname
            
            # NOTE: overriden in __init__!
            #if axisunits == pq.dimensionless:
                #axisunits = arbitrary_unit
                
            result[0]["units"] = axisunits
            result[0]["origin"] = axisorigin
            result[0]["resolution"] = axisresolution
            
        else:
            for channel_index in channels_dict.keys():
                result[channel_index] = channels_dict[channel_index]
            
                
        # NOTE: overridden in __init__ to sort things out
        #else:
            #if axisunits == pq.dimensionless:
                #axisunits = pixel_unit
                
        result["units"]     = axisunits
        result["origin"]    = axisorigin
        result["resolution"]= axisresolution
            
        #print("parseDescriptionString result:", result)
        
        return result
        
    @staticmethod
    def hasNameString(s):
        if not isinstance(s, str):
            raise TypeError("expecting a str; got %s instead" % type(s).__name__)
        
        return "<name>" in s and "</name>" in s
    
    @staticmethod
    def hasCalibrationString(s):
        """Simple test for what MAY look like a calibration string.
        Does nothing more than saving some typing; in particular it DOES NOT verify
        that the calibration string is conformant.
        
        NOTE: Parameter checking is implicit
        
        """
        return "<axis_calibration>" in s and "</axis_calibration>" in s

    @staticmethod
    def isAxisCalibrated(axisinfo):
        """Syntactic shorthand for hasCalibrationString(axisinfo.description).
        
        NOTE: Parameter checking is implicit
        
        """
        return AxesCalibration.hasCalibrationString(axisinfo.description)
    
    @staticmethod
    def removeCalibrationData(axInfo):
        if not isinstance(axInfo, vigra.AxisInfo):
            raise TypeError("Expecting a vigra.AxisInfo object; got %s instead" % type(axInfo).__name__)

        axInfo.description = AxesCalibration.removeCalibrationFromString(axInfo.description)
        
        return axInfo
    
    @staticmethod
    def removeCalibrationFromString(s):
        """Returns a copy of the string with any calibration substrings removed.
        Convenience function to clean up AxisInfo description strings.
        
        NOTE: Parameter checking is implicit
        
        """
        
        if not isinstance(s, str):
            raise TypeError("Expecting a string; got %s instead" % type(s).__name__)
        
        name_start = s.find("<name>")
        
        if name_start  > -1:
            name_stop = s.find("</name>")
            
            if name_stop > -1:
                name_stop += len("</name>")
                
            else:
                name_stop = name_start + len("<name>")
                
            d = [s[0:name_start].strip()]
            d.append([s[name_stop:].strip()])
            
            s = " ".join(d)
        
        calstr_start = s.find("<axis_calibration>")
        
        if calstr_start > -1:
            calstr_end = s.rfind("</axis_calibration>")
            
            if calstr_end > -1:
                calstr_end += len("</axis_calibration>")
                
            else:
                calstr_end = calstr_start + len("<axis_calibration>")
                
            s1 = [s[0:calstr_start].strip()]
            
            s1.append(s[calstr_end:].strip())
            
            return " ".join(s1)
        
        else:
            return s

    def setChannelName(self, channel_index, value):
        """Sets the name for the given channel of an existing Channels axis in this calibration object.
        
        Raises KeyError if no Channel axis exists, or if channel_index is not found
        """
        if self.axistags.channelIndex == len(self.axistags):
            raise KeyError("No channel axis exists in this calibration object")
        
        #if isinstance(key, vigra.AxisInfo):
            #key = key.key
            
        channelAxis = self.axistags[self.axistags.channelIndex]
        
        key = channelAxis.key
            
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Channel axis %s does not have calibration data" % key)
        
        if isinstance(value, (str, type(None))):
            if channel_index in self._calibration_[key].keys():
                self._calibration_[key][channel_index]["name"] = value
                
            else:
                user_calibration = dict()
                user_calibration["name"] = value
                user_calibration["units"] = arbitrary_unit
                user_calibration["origin"] = 0.0
                user_calibration["resolution"] = 1.0
                self._calibration_[key][channel_index] = user_calibration
            
        else:
            raise TypeError("channel name must be a str or None; got %s instead" % type(value).__name__)
        
    def setChannelCalibration(self, channel_index, name=None, units=arbitrary_unit, origin=0.0, resolution=1.0):
        """Sets up channel calibration items (units, origin and resolution) for channel with specified index
        
        If channel_index does not yet exist, it is added to the channel axis calibration
        
        """
        if self.axistags.channelIndex == len(self.axistags):
            raise KeyError("No channel axis exists in this calibration object")
        
        channelAxis = self.axistags[self.axistags.channelIndex]
        
        key = channelAxis.key
            
        if not isinstance(channel_index, int):
            raise TypeError("new channel index expected to be an int; got %s instead" % type(channel_index).__name__)
        
        if channel_index < 0:
            raise ValueError("new channel index must be >= 0; got %s instead" % channel_index)
        
        if key not in self._calibration_.keys():
            raise RuntimeError("Channel axis does not have calibration data")
        
        user_calibration = dict()
        
        if isinstance(name, (str, type(None))):
            user_calibration["name"] = name
            
        else:
            raise TypeError("name expected to be a str or None; got %s instead" % type(name).__name__)
        
        if not isinstance(units, (pq.Quantity, pq.UnitQuantity)):
            raise TypeError("Channel units are expected ot be a python Quantity or UnitQuantity; got %s instead" % type(units).__name__)
        
        user_calibration["units"] = units
        
        if isinstance(origin, numbers.Number):
            user_calibration["origin"] = origin
        
        elif isinstance(origin, pq.Quantity):
            if origin.magnitude.size != 1:
                raise ValueError("origin must be a scalar Python Quantity; got %s instead" % origin)
            
            if user_calibration["units"] == pq.dimensionless:
                # allow origin to set units if not set by units
                user_calibration["units"] = origin.units
                
            else:
                # check origin and units are compatible
                mydims = pq.quantity.validate_dimensionality(user_calibration["units"])
                origindims = pq.quantity.validate_dimensionality(origin.units)
                
                if mydims != origindims:
                    try:
                        cf = pq.quantity.get_conversion_factor(origindims, mydims)
                        
                    except AssertionError:
                        raise ValueError("Cannot convert from origin units (%s) to %s" % (origindims.dimensionality, mydims.dimensionality))
                    
                    origin *= cf
                    
            user_calibration["origin"] = origin.magnitude.flatten()[0]
                
        else:
            raise TypeError("origin must be a float scalar or a scalar Python Quantity; got %s instead" % type(origin).__name__)
            
                
        if isinstance(resolution, numbers.Number):
            user_calibration["resolution"] = resolution #* user_calibration["units"]
            
        elif isinstance(resolution, pq.Quantity):
            if resolution.magnitude.size  != 1:
                raise ValueError("resolution must be a scalar quantity; got %s instead" % resolution)
            
            mydims = pq.quantity.validate_dimensionality(user_calibration["units"])
            resdims = pq.quantity.validate_dimensionality(resolution.units)
            
            if mydims != resdims:
                try:
                    cf = pq.quantity.get_conversion_factor(resdims, mydims)
                    
                except AssertionError:
                    raise ValueError("Cannot convert from resolution units (%s) to %s" % (resdims.dimensionality, mydims.dimensionality))
                
                resolution *= cf
                
            user_calibration["resolution"] = resolution.magnitude.flatten()[0]
            
        else:
            raise TypeError("resolution expected to be a scalar float or Python Quantity; got %s instead" % type(resolution).__name__)
            
        if channel_index in self._calibration_[key].keys():
            self._calibration_[key][channel_index].update(user_calibration)
            
        else:
            self._calibration_[key][channel_index] = user_calibration
        
    def removeChannelCalibration(self, channel_index):
        if self.axistags.channelIndex == len(self.axistags):
            raise KeyError("No channel axis exists in this calibration object")
        
        channelAxis = self.axistags[self.axistags.channelIndex]
        
        key = channelAxis.key
            
        if not isinstance(channel_index, int):
            raise TypeError("new channel index expected to be an int; got %s instead" % type(channel_index).__name__)
        
        channel_indices = [k for k in self._calibration_[key].keys() if isinstance(k, int)]
        
        if key not in self._calibration_.keys():
            raise KeyError("Channel axis has no calibration")
        
        if len(channel_indices) == 0:
            raise KeyError("No channel calibrations defined for axis %s with key %s" % (self._calibration_[key]["axisname"], self._calibration_[key]["axiskey"]))
        
        if channel_index not in self._calibration_[key].keys():
            if channel_index < 0 or channel_index >= len(channel_indices):
                raise KeyError("Channel %d not found for axis %s with key %s" % (channel_index, self._calibration_[key]["axisname"], self._calibration_[key]["axiskey"]))
                
            channel_index = channel_indices[channel_index]
            raise KeyError("Channel %d not found for the channel axis" % channel_index)
        
        del self._calibration_[key][channel_index]
        
    def rescaleUnits(self, value, key, channel=0):
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if isinstance(value, (pq.Quantity, pq.UnitQuantity)):
            try:
                origin = self.getOrigin(key, channel)
                origin.rescale(value)
                
            except AssertionError:
                raise ValueError("Cannot convert from current units (%s) to %s" % (self.getUnits(key, channel), value.units))
            
            try:
                resolution = self.getResolution(key, channel)
                resolution.rescale(value)
                
            except AssertionError:
                raise ValueError("Cannot convert from current units (%s) to %s" % (self.getUnits(key, channel), value.units))
            
            if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
                if channel not in self._calibration_[key].keys():
                    channel_indices = [k for k in self._calibration_[key].keys() is isinstance(k, int)]
                    if len(channel_indices) == 0:
                        raise RuntimeError("No channel calibration data found")
                    
                    if channel < 0 or channel >= len(channel_indices):
                        raise RuntimeError("No calibration data for channel %d" % channel)
                    
                    channel = channel_indices[channel]
                    
                self._calibration_[key][channel]["units"] = value.units
                self._calibration_[key][channel]["origin"] = origin.magnitude.flatten()[0]
                self._calibration_[key][channel]["resolution"] = resolution.flatten()[0]
                
            else:
                self._calibration_[key]["units"] = value.units
                self._calibration_[key]["origin"] = origin.magnitude.flatten()[0]
                self._calibration_[key]["resolution"] = resolution.flatten()[0]
                
        else:
            raise TypeError("Expecting a Python Quantity or UnitQuantity; got %s instead" % type(value).__name__)
        
    def calibrateAxes(self):
        """Attaches a calibration string to all axes registered with this object.
        """
        for ax in self._axistags_:
            self.calibrateAxis(ax)
        
    def calibrateAxis(self, axInfo):
        """Attaches a dimensional calibration to an AxisInfo object.
        
        Calibration is inserted as an xml-formatted string.
        (see AxesCalibration.calibrationString())
        
        The axInfo AxisInfo object does not need to be part of the axistags 
        collection calibrated by this AxesCalibration object i.e., "external" 
        (independent) AxisInfo objects can also get a calibration string in their 
        description attribute.
        
        The only PREREQUISITE is that the "key" and "typeFlags" attributes of the
        axInfo parameter MUST be mapped to calibration data in this AxesCalibration
        object.
        
        Positional parameters:
        ====================
        axInfo = a vigra.AxisInfo object
        
        Returns:
        ========
        
        A reference to the axInfo with modified description string containing 
        calibration information.
        
        What this function does:
        ========================
        The function creates an XML-formatted calibration string (see 
        AxesCalibration.calibrationString(key)) that will be inserted in the 
        description attribute of the axInfo parameter
            
        NOTE (1) If axInfo.description already contains a calibration string, it will 
        be replaced with a new calibration string. No dimensional analysis takes place.
        
        NOTE (2) The default value for the resolution in vigra.AxisInfo is 0.0, which 
        is not suitable. When axInfo.resolution == 0.0, and no resolution parameter
        is supplied, the function will set its value to 1.0; otherwise, resolution 
        will take the value provided in the axInfo.
        
        """
        if not isinstance(axInfo, vigra.AxisInfo):
            raise TypeError("First argument must be a vigra.AxisInfo; got %s instead" % type(axInfo).__name__)
        
        # check if an axistag like the one in axInfo is present in this calibration object
        # NOTE: this does NOT mean that axInfo is registered with this calibration object
        # but we need ot make sure we copy the calibration data across like axes
        if axInfo.key not in self._calibration_.keys() or axInfo.key not in self._axistags_:
            raise KeyError("No calibration data found for axis with key: %s and typeFlags: %s)" % (axInfo.key, axInfo.typeFlags))
            
        if axInfo.typeFlags != self._calibration_[axInfo.key]["axistype"]:
            raise ValueError("The AxisInfo parameter with key %s has a different type (%s) than the one for which calibrationd data exists (%s)" \
                            % (axInfo.key, axInfo.typeFlags, self._calibration_[axInfo.key]["axistype"]))
            
        calibration_string = self.calibrationString(axInfo.key)
        # check if there already is (are) any calibration string(s) in axInfo description
        # then replace them with a single xml-formatted calibration string
        # generated above
        # otherwise just append the calibration string to the description
        
        # 1) first, remove any name string
        name_start = axInfo.description.find("<name>")
        
        if name_start  > -1:
            name_stop = axInfo.description.find("</name>")
            
            if name_stop > -1:
                name_stop += len("</name>")
                
            else:
                name_stop = name_start + len("<name>")
                
            d = [axInfo.description[0:name_start].strip()]
            d.append(axInfo.description[name_stop:].strip())
            
            axInfo.description = " ".join(d)
        
        # 2) then find if there is a previous calibration string in the description
        calstr_start = axInfo.description.find("<axis_calibration>")
        
        if calstr_start > -1: # found previous calibration string
            calstr_end = axInfo.description.rfind("</axis_calibration>")
            
            if calstr_end > -1:
                calstr_end += len("</axis_calibration>")
                
            else:
                calstr_end  = calstr_start + len("<axis_calibration>")
                
            # remove previous calibration string
            # not interested in what is between these two (susbstring may contain rubbish)
            # because we're replacing it anyway
            # just keep the non-calibration contents of the axis info description 
            s1 = [axInfo.description[0:calstr_start].strip()]
            s1.append(axInfo.description[calstr_end:].strip())
            
            s1.append(self.calibrationString(axInfo.key))
            
        else: 
            s1 = [axInfo.description]
            s1.append(self.calibrationString(axInfo.key))
            
        axInfo.description = " ".join(s1)
        
        #print("calibrateAxis: %s" % axInfo.description)
        if not axInfo.isChannel():
            # also update the axis resolution -- but only if axis is not a channel axis
            # (channel resolution is set into <channelX> </channelX> tags)
            axInfo.resolution = self.getDimensionlessResolution(axInfo.key)
            
        else:
            # the resolution of the first channel should be acceptable in most cases
            axInfo.resolution = self.getDimensionlessResolution(axInfo.key, 0)
            
        return axInfo # for convenience
    
    def getCalibratedAxisLength(self, image, key, channel = 0):
        if isinstance(key, vigra.AxisInfo):
            return self.getCalibratedAxialDistance(image.shape[image.axistags.index(key.key)], key, channel)
            
        else:
            return self.getCalibratedAxialDistance(image.shape[image.axistags.index(key)], key, channel)
    
    def getDistanceInSamples(self, value, key, channel=0):
        """Conversion of a calibrated distance in number of samples along the axis.
        """
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis %s not found in this AxesCalibration object" % key)
        
        if isinstance(value, numbers.Real):
            if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
                if channel not in self._calibration_[key].keys():
                    raise KeyError("Channel %d not found for axis %s with key %s" % (channel, self._calibration_[key]["axisname"], self._calibration_[key]["axiskey"]))
                
                value *= self._calibration_[key][channel]["units"]
                
            else:
                value *= self._calibration_[key]["units"]
            
        elif not isinstance(value, pq.Quantity):
            raise TypeError("Expecting a python Quantity; got %s instead" % type(value).__name__)
        
        if value.size != 1:
            raise TypeError("Expecting a scalar quantity; got %s instead" % value.size)
        
        if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
            if channel not in self._calibration_[key].keys():
                raise KeyError("Channel %d not found for axis %s with key %s" % (channel, self._calibration_[key]["axisname"], self._calibration_[key]["axiskey"]))
            
            myunits = self._calibration_[key][channel]["units"]
            myresolution = self._calibration_[key][channel]["resolution"]
            
        else:
            myunits = self._calibration_[key]["units"]
            myresolution = self._calibration_[key]["resolution"]
        
        value_dim = pq.quantity.validate_dimensionality(value.units)
        self_dim  = pq.quantity.validate_dimensionality(myunits)
        
        if value_dim != self_dim:
            try:
                cf = pq.quantity.get_conversion_factor(self_dim, value_dim)
                
            except AssertionError:
                raise ValueError("Cannot compare the value's %s units with %s" % (value_dim.dimensionality, self._dim.dimensionality))
            
            value *= cf
            
        result = float((value / self.getDimensionlessResolution(key, channel)))
        
        return result
    
    def getCalibratedAxialDistance(self, value, key, channel=0):
        """Converts distance in sample along an axis into a calibrated distance in axis units
        """
        if not isinstance(value, numbers.Number):
            raise TypeError("expecting a scalar; got %s instead" % type(value).__name__)
        
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        return (value * self.getDimensionlessResolution(key, channel)) * self.getUnits(key, channel)
    
    def getCalibratedAxisCoordinate(self, value, key, channel=0):
        if not isinstance(value, numbers.Number):
            raise TypeError("expecting a scalar; got %s instead" % type(value).__name__)
        
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        return (value * self.getDimensionlessResolution(key, channel) + self.getDimensionlessOrigin(key, channel)) * self.getUnits(key, channel)
    
    def getCalibrationTuple(self, key, channel=0):
        """Returns (units, origin, resolution) tuple for axis with specified key.
        For Channels axis, returns the tuple for the specified channel.
        """
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if key not in self._calibration_.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s is not calibrated by this object" % key)
        
        if self._calibration_[key]["axistype"] & vigra.AxisType.Channels:
            if channel not in self._calibration_[key].keys():
                raise KeyError("Channel %d not found for axis %s with key %s" % (channel, self._calibration_[key]["axisname"], self._calibration_[key]["axiskey"]))
            
            return(self._calibration_[key][channel]["units"], self._calibration_[key][channel]["origin"], self._calibration_[key][channel]["resolution"])
        
        return(self._calibration_[key]["units"], self._calibration_[key]["origin"], self._calibration_[key]["resolution"])

        
        if isinstance(channel, int):
            if channel not in self._calibration_.keys():
                raise ValueError("channel %d has no calibration data" % channel)
            
            return ()
        
        elif channel is None:
            return (self.origin, self.resolution)
        
        else:
            raise TypeError("channel expected to be an int or None; got %s instead" % type(channel).__name__)
        
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

