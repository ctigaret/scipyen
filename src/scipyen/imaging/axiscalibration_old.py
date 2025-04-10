class CalibrationData(object):
    r"""Superclass for AxisCalibrationData and ChannelCalibrationData types.
    
    These classes offer a way to store calibration data in vigra.AxisInfo objects
    and optionally to notify code using this data to changes to field values.
    
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
    
    NOTE 2: CalibrationData for NonChannel axes assumes a linear (1st order) model
    
    
    """
    # NOTE: 2025-04-08 09:06:17
    # For an axis of type Channels, this should rely only on the list of channel
    # calibrations: for a channel axis (even if it is a "virtual" channel axis)
    # the only relevant data should be the ChannelCalibrationData member in the
    # AxisCalibrationData instance, even i it is just one (for a virtual channel);
    # the fields 'units', 'origin', and 'resolution' should return dataclasses.MISSING;
    
    parameters = ("units", "origin", "resolution")
    
    @classmethod
    def isCalibration(cls, x):
        return isinstance(x, cls) or (isinstance(x, dict) and all(k in x for k in cls.parameters))
        
    def __init__(self, *args, **kwargs):
        r"""Calibration data constructor.
        
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
        self.__class__      Copy constructor. 
    
                            The object will be fully initialized by the first 
                            parameter of this type and all other var-positional
                            and var-keyword parameters are ignored.
        
        vigra.AxisInfo      When self.__class__ is AxisCalibrationData:
        
                            Initialize this object from the parameter's 
                            'description' attribute, if it contains an
                            XML-formatted calibration substring, else determine
                            default values from the parameter's 'key' and 
                            'typeFlags' attributes. 
    
                            For a Channels axis, if the 'channels' keyword is given 
                            as an int value >= 1 then that many default ChannelCalibrationData
                            objects will be created for the axis. If the 'channels' 
                            keyword is a sequence of ChannelCalibrationData objects, 
                            then thesewill be used to populate the AxisCalibrationData for 
                            this Channels axis. Otherwise, it is assumed that the 
                            Channels axis has only one channel.
    
                            WARNING: it is the responsibility of the caller to 
                            ensure that the number of ChannelCalibrationData
                            objects or the int value of in "channels" matches the 
                            size of the array along the Channels axis.
                            
                            The object will be fully initialized by the first 
                            parameter of this type and all other var-positional
                            and var-keyword parameters are ignored, except for
                            the 'channels' keyword.
                            
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
        
        'type': vigra.AxisType, int (logical OR of vigra.AxisType flags), 
                or str
        
            When a `str` this can be a vigra.AxisInfo 'key' or a descriptive 
                string (see axisutils.axisTypeFromString() for details)
                
            This will set up the calibration's 'type' field and the derived
            fields 'key' 'name' and 'unts'
            
        'name': str -> calibration 'name' field
        
        'index': int -> only for ChannelCalibrationData; sets up 'index' field
        
        'units': str, Python quantities.Quantity, or 
                quantities.dimensionality.Dimensionality
                
        'origin', 'minimum', 'resolution', 'maximum -> scalars:
            Python Quantity or numpy array, int, cmplex, or float (including 
            np.nan, math.nan).
                                
            When these are a Quantity their 'units' attribute must be convertible
            to the 'units' field.
                
            These will set up the corresponding calibration fields (NOTE that
            'minimum' is an alias to 'origin'; 'maxium' is only used for 
            ChannelCalibrationData)
    
        "channels": int or sequence of ChannelCalibrationData, or None.
    
        """
        # FIXME 2021-10-22 09:48:23
        # a DataBag here gets "sliced" in :subclasses: of CalibrationData
        # why ???
        #self._data_ = DataBag()
        self._data_ = Bunch()
        
        self._relative_tolerance_ = 1e-4
        self._absolute_tolerance_ = 1e-4
        self._equal_nan_ = True
        
        # prepare the underlying Bunch mapping the calibration parameters to their
        # values (for now, these are set to None)
        for param in self.__class__.parameters:
            self._data_[param] = None
            
        # for one var-positional parameters, allow this to be ONE calibration-like
        # mapping or calibration data object
        if len(args) == 1 and AxisCalibrationData.isCalibration(args[0]):
            if isinstance(args[0], dict):
                kwargs = args[0]
                args = tuple()
            elif isinstance(args[0], AxisCalibrationData):
                self._data_.update(args[0]._data_)# copy c'tor
                return
            
        # get the channel specification, if any
        channels = kwargs.pop("channels", None)
        
        if isinstance(channels, int) and channels >= 1:
            channelData = list(map(lambda x: ChannelCalibrationData(0.0, 1.0, maximum=np.nan, name=f"channel_{x}"), range(channels)))
        elif isinstance(channels, (tuple, list, deque)) and all(isinstance(c, ChannelCalibrationData) for c in channels):
            channelData = channels
        else:
            channelData = tuple() # leave this empty because it indicates that
            # we're calibrating a NonChannel axis, when an arg is of type int
        
        # for c in channeldata:
        #     kwargs.pop(c[0], None)
        
        # now, just go ahead and use the remaining var-positional parameters in
        # args
        for arg in args:
            # below, whenever we set the axistype we also set the params derived
            # from it, if required: axisname, axiskey, units
            
            if isinstance(arg, self.__class__):
                # this is a copy c'tor based on the first element of args; 
                # everything after that is ignored
                # NOTE: 2025-04-08 15:00:25 FIXME
                # what if this is NOT the first arg?
                # in theory this should overwrite all members of self._data_ that have
                # been set up so far, so there shuold be no problem here
                self._data_.update(arg._data_) # DONE
                return
            
            if isinstance(arg, str):
                # args is a string; we may not know the axis type yet
                if self.__class__ == AxisCalibrationData:
                    # arg can be:
                    # • a string containing a calibration sub-string (XML-formatted)
                    # • a generic string from which the axis type can be deduced 
                    # • a valid axis 'key' string, 
                    #   inferred using the heuristics in axisutils.axisTypeFromString()
                    if "<axis_calibration>" in arg:
                        # arg looks like an XML-formatted calibration string; if
                        # true, then this should also determine the axis type &
                        # everything else, therefore we overwrite whatever was
                        # set in self._data_ and return 
                        try:
                            cal_str_start_stop = AxisCalibrationData.findCalibrationString(arg)
                            cal = AxisCalibrationData.fromCalibrationString(arg[cal_str_start_stop[0]:cal_str_start_stop[1]])   
                            self._data_.update(cal._data_)
                            return
                        except:
                            raise ValueError(f"str argument is an ambiguous calibration string")
                        
                    elif not isElementaryAxisType(self._data_.type):
                        # FIXME: 2025-04-08 16:42:22 when has this been set?
                        # arg is a generic string
                        # we need to update self._data_ bit by bit
                        # CAUTION: is self._data_.type was already set, this 
                        # will overwrite it
                        self._data_.type = axisTypeFromString(arg)
                        
                        # # just to be clear: if var-keyword parameters contain
                        # # channel calibration data, then we force this to be
                        # # a calibration for a Channels axis, in case self._data_.type
                        # # was set to an incorrect value by axisTypeFromString
                        # if len(channeldata):
                        #     self._data_.type = vigra.AxisType.Channels
                        
                        if isElementaryAxisType(self._data_.type):
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
                        self._data_.units = unitQuantityFromNameOrSymbol(arg)
                    except:
                        pass # let the next args deal with it
                    
            elif isinstance(arg, vigra.AxisType):
                if self.__class__ == AxisCalibrationData:
                    if not isElementaryAxisType(self._data_.type):
                        self._data_.type = arg
                        
                        # if len(channeldata):
                        #     self._data_.type = vigra.AxisType.Channels
                        
                        if not isinstance(self._data_.name, str) or len(self._data_.name.strip()) == 0:
                            self._data_.name = axisTypeName(self._data_.type)
                            
                        if not isinstance(self._data_.key, str) or len(self._data_.key.strip()) == 0:
                            self._data_.key = axisTypeSymbol(self._data_.type)
                        
                        if not isinstance(self._data_.units, pq.Quantity):
                            self._data_.units = axisTypeUnits(self._data_.type)
                    
            elif isinstance(arg, int):
                if self.__class__ == AxisCalibrationData:
                    if not isElementaryAxisType(self._data_.type):
                        if isElementaryAxisType(arg): 
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
                                    
                        if isElementaryAxisType(self._data_.type):
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
                    if not unitsConvertible(self._data_.units.units, arg.units):
                        raise TypeError(f"'origin' units {arg.units} are incompatible with the specified units ({self._data_.units})")
                    
                    if arg.units != self._data_.units.units:
                        arg = arg.rescale(self._data_.units.units)
                        
                    self._data_.origin = quantity2scalar(arg)
                    
                elif not isinstance(self._data_.resolution, (complex, float, int)):
                    if not unitsConvertible(self._data_.units.units, arg.units):
                        raise TypeError(f"'origin' units {arg.units} are incompatible with the specified units ({self._data_.units})")
                    
                    if arg.units != self._data_.units.units:
                        arg = arg.rescale(self._data_.units.units)
                        
                    self._data_.resolution = quantity2scalar(arg)
                    
                elif self.__class__ == ChannelCalibrationData:
                    if not isinstance(self._data_.maximum, (complex, float, int)):
                        if not unitsConvertible(self._data_.units.units, arg.units):
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
                # the MOST common use!
                # ---------------------
                # will use calibration string embedded in the AxisInfo.description
                # if found;
                # the values of the AsisInfo's typeFlags & key attributes take
                # precedence over the calibration string if the latter is not
                # conforming
                # in either case the AxisInfo's description will NOT be updated;
                # this MUST be done separately i.e. by calling calibrateAxis or
                # calibrateAxes
                
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
                        # bring back channel calibrations if appropriate
                        # NOTE: 2025-04-08 21:58:50
                        # for a Channels axis we do NOT store units, origin and
                        # resolution for this axis anymore; instead, we store the
                        # the ChannelCalibrationData for each channnel, as 
                        # an attribute named after the channel; 
                        #
                        # if the channel axis is virtual, the we set the "virtual"
                        # flag to True in the ChannelCalibrationData
                        #
                        # A "virtual" channel axis is one where the index of the
                        # channel axis equals the number of dimensions of the array
                        if self._data_.type & vigra.AxisType.Channels:
                            # FIXME 2025-04-08 22:12:38
                            # what if more channels are given, than they actually exist?
                            # in the axis? that's up to the caller to ensure 
                            # no mismatch
                            #
                            # it is also up to the caller to make sure the units
                            # are OK.
                            if len(channelData):
                                for chcal in channelData:
                                    self._data_[chcal.name] = chcal
                                    
                            else:
                                chcal = ChannelCalibrationData(0.0, 1.0, maximum=np.nan, name="channel_0"), 
                                self._data_[chcal.name] = chcal
                                
                        else:
                            self._data_.units = axisTypeUnits(self._data_.type)
                            self._data_.origin = axorigin
                            self._data_.resolution = 1. if arg.resolution == 0. else arg.resolution
                        
                    else:
                        cal = AxisCalibrationData.fromCalibrationString(arg.description[cal_str_start_stop[0]:cal_str_start_stop[1]])

                        self._data_.update(cal._data_)
                        self._data_.key = arg.key
                        
                    return # only allow one AxisInfo argument
                
                else:
                    raise TypeError(f"AxisInfo parameters are accepted only for the initialization of AxisCalibrationData")
                
            elif isinstance(arg, dict) and self.__class__.isCalibration(arg):
                # form a calibration dict
                self._data_.update(arg)
                return # accept only one calibration dict
                    
        axtype = kwargs.pop("type", None)
        if axtype is not None:
            if self.__class__ == AxisCalibrationData:
                if isElementaryAxisType(axtype):
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
                    units_ = unitQuantityFromNameOrSymbol(units_)
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
                if not unitsConvertible(origin_.units, self._data_.units.units):
                    raise TypeError(f"'origin (or minimum)' units {origin_.units} are incompatible with the specified units ({self._data_.units})")
                    
                if origin_.units != self._data_.units.units:
                    origin_ = origin_.rescale(self._data_.units.units)
                    
                self._data_.origin = quantity2scalar(o)
                
            elif isinstance(origin_, (complex, float, int, np.ndarray)) or origin_ in (math.nan, np.nan):
                self._data_.origin = quantity2scalar(origin_)
            
        resoln  = kwargs.pop("resolution", None)
        if resoln is not None:
            if isinstance(resoln, pq.Quantity):
                if not unitsConvertible(resoln.units, self._data_.units.units):
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
                    if not unitsConvertible(maxval.units, self._data_.units.units):
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
            if not isElementaryAxisType(self._data_.type):
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
        r"""Membership test for channel calibration data
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
            ret &= unitsConvertible(self.units, other.units)
            
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
                    oth_p = list(getattr(other, p).rescale(self.units) for p in ("calibratedOrigin", "calibratedResolution", "calibratedMaximum") if hasattr(self, p))
                    # oth_p = list(v.rescale(getattr(other, p), self.units) for p in ("calibratedOrigin", "calibratedResolution", "calibratedMaximum") if hasattr(self, p))
                    
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
        r"""Get/set the pysical units of measurement.
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
            u = unitQuantityFromNameOrSymbol(u)
            
        if not isinstance(u, pq.Quantity):
            raise TypeError(f"Units expected to be a Python Quantity, Dimensionality, or str; got {type(u).__name__} instead")
        
        if hasattr(self, "type"):
            units_for_type = axisTypeUnits(self.type)
            if not unitsConvertible(u.units, units_for_type.units):
                axis_type_names = "|".join(axisTypeStrings(self.type))
                warnings.warn(f"Assigning units {u} for a {axis_type_names} axis", RuntimeWarning, stacklevel=2)
                
        self._data_.units = u.units
        
    def rescale(self, u:typing.Union[pq.Quantity, pq.dimensionality.Dimensionality, str]) -> None:
        r"""Rescale units, origin and resolution for new units.
        
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
        r"""Get/set the origin value
        """
        return self._data_.origin
    
    @origin.setter
    def origin(self, val):
        if isinstance(val, (complex, float, int)):
            self._data_.origin = val
            
        elif isinstance(val, pq.Quantity):
            if not unitsConvertible(val.units, self.units.units):
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
        r"""Origin as Python Quantity
        """
        return self.origin * self.units.units
        
    @property
    def resolution(self):
        r"""Get/set the origin value
        """
        return self._data_.resolution
    
    @resolution.setter
    def resolution(self, val):
        if isinstance(val, (complex, float, int)):
            self._data_.resolution = val
            
        elif isinstance(val, pq.Quantity):
            if not unitsConvertible(val.units, self.units.units):
                raise TypeError(f"New resolution units ({val.units}) are incompatible with my units ({self.units.units})")
            
            if val.units != self.units.units:
                val = val.rescale(self.units.units)
                
            self._data_.resolution = quantity2scalar(val)
            
        elif isinstance(val, np.ndarray):
            self._data_.resolution = quantity2scalar(val)
            
        else:
            raise TypeError(f"Resolution expected a scalar int, float, complex, Python Quantity or numpy array; got {type(val).__name__} instead")
            
    @property
    def calibratedResolution(self):
        r"""Resolution as Python Quantity
        """
        return self.resolution * self.units.units
        
    @property
    def calibrationTuple(self):
        r"""Returns a tuple of quantities (unit, origin, resolution)
        """
        if self.__class__ == ChannelCalibrationData:
            return (self.units.units, self.calibratedOrigin, self.calibratedResolution, self.calibratedMaximum)
            
        return (self.units.units, self.calibratedOrigin, self.calibratedResolution)
    
    @property
    def data(self):
        r"""Returns the calibration data as a dict
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
        r"""Distance from origin in axis units
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
        r"""Returns the number of samples for the calibrated distance from origin.
        """
        if not isinstance(value, pq.Quantity):
            raise TypeError(f"Expecting a Quantity; got {type(value).__name__} instead")
        
        if value(size) != 1:
            raise TypeError(f"Expecting a scalar Quantity; instead, got a {value.size}-sized Quantity")
        
        if not unitsConvertible(value.units, self.units.units):
            raise TypeError(f"Cannot convert between {value.units} and {self.units}")
        
        value_dim = pq.quantity.validate_dimensionality(value.units)
        my_dim = pq.quantity.validate_dimensionality(self.units)
        
        if value_dim != my_dim:
            cf = pq.quantity.get_conversion_factor(my_dim, value_dim)
            value *= cf
            
        return math.ceil(value / self.resolution)
        #return int(np.rint(value / self.resolution))
    
class ChannelCalibrationData(CalibrationData):
    r"""Encapsulates calibration data for pixel INTENSITIES in a given channel.
    
    Do not confuse with the calibration of a Channels axis itself.
    
    """
    parameters = CalibrationData.parameters + ("name", "index", "maximum")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    @property
    def minimum(self):
        r"""Get/set minimum calibration value.
        This is the same as origin.
        """
        return self.origin
    
    @minimum.setter
    def minimum(self, val):
        self.origin = val
        
    @property
    def maximum(self):
        r"""Get/set the maximum calibration value
        """
        return self._data_.maximum
    
    @maximum.setter
    def maximum(self, val):
        if isinstance(val, (complex, float, int)):
            self._data_.maximum = val
            
        elif isinstance(val, pq.Quantity):
            if not unitsConvertible(val.units, self.units.units):
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
        r"""Index of channel where this calibration applies"""
        return self._data_.index
    
    @index.setter
    def index(self, val:int):
        if isinstance(val, int) and val >= 0:
            self._data_.index = val
            
    @property
    def channels(self):
        r"""Returns a tuple ('name', 'calibration') where
        • 'name' is this object's name attribute
        • 'calibration' is this object itself
        
        NOTE: The setter of this property expects a ChannelCalibrationData object
        or sequence of ChannelCalibrationData objects, with just one element
        
        """
        return (self.name, self)

    # def channels(self, val:typing.Sequence[typing.Tuple[str, typing.Union[ChannelCalibrationData, dict]]]):
    @channels.setter
    def channels(self, val:typing.Union[typing.Self, typing.Sequence[typing.Union[typing.Self, dict]]]):
        if isinstance(val, self.__class__):
            for param in self.parameters:
                setattr(self, param, getattr(val, param))
        
        elif isinstance(val, typing.Sequence) and all(isinstance(v, typing.Self) for v in val):
            if len(val) > 1:
                scipywarn(f"Too many arguments ({len(val)}); only the first one will be used")
                
            for param in self.parameters:
                setattr(self, param, getattr(val[0], param))
            


class AxisCalibrationData(CalibrationData):
    r"""Atomic calibration data for an axis of a vigra.VigraArray.
    
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
    the newly created AxisCalibrationData object.
    
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
        r"""Get/set the axis name
        """
        return self._data_.name
    
    @name.setter
    def name(self, val:str):
        if isinstance(val, str) and len(val.strip()):
            self._data_["name"] = val
            #self._data_.name = val
            
    @property
    def key(self):
        r"""Get/set the axis type key
        """
        return self._data_.key
    
    @key.setter
    def key(self, val:str):
        if isinstance(val, str) and len(val.strip()):
            self._data_["key"] = val
            #self._data_.key = val
            
    @property
    def type(self):
        r"""Get/set the axis type flags
        WARNING: Setting this property will modify the other properties:
        'units', 'name', 'key', 'origin', and 'resolution'
        
        """
        return self._data_.type
    
    @type.setter
    def type(self, val:typing.Union[vigra.AxisType, int, str]):
        if isinstance(val, str):
            val = axisTypeFromString(val)
            
        if not isElementaryAxisType(val):
            raise TypeError(f"Incompatible axis type {val}")
        
        if val != self._data_.type:
            if val != vigra.AxisType.Channels and self._data_.type == vigra.AxisType.Channels:
                for c in self.channels:
                    self._data_.pop(c[0], None)

            self._data_.type = val
            self._data_.units = axisTypeUnits(val)
            self._data_.name = axisTypeName(val)
            self._data_.key = axisTypeSymbol(val)
            
    @property
    def channels(self) -> tuple:
        r"""Alias to channelCalibrations property"""
        return self.channelCalibrations
            
#     @property
#     def channels(self):
#         r"""Returns a tuple of tuples with (name, ChannelCalibrationData) 
#         
#         In each tuple, the elements represent the symbol and the channel 
#         calibration mapped to it, for non-virtual channels only, in this 
#         AxisCalibrationData object.
#         
#         The symbol is not necessarily the name of the channel.
#         
#         VigraArray objects always have at least one channel. When the array
#         lacks a defined Channels axis, the data itself constitutes a single 
#         channel corresponding to a virtual Channels axis of size 1.
#         
#         Hence, the calibration data for a Channels axis will report either:
#         
#         * at least one calibration data for 'real' channels
#         
#         or:
#         
#         * one calibration data with default parameters for a 'virtual' channel.
#         
#         This property reports only the calibrations for 'real' channels, hence
#         it may be an empty list.
#         
#         This behaviour is different from that of the `channelCalibrations`
#         property where a virtual channel calibration is returned when no 'real'
#         channel calibration data exists.
#         
#         For AxisCalibrationData corresponding to a non-Channels axis this 
#         property is always an empty list.
#         
#         The setter expects a sequence of tuples (a,b) with:
#         `a`:str = the field name that will be mapped to the ChannelCalibrationData
#         `b`: ChannelCalibrationData or dict that can be used to construct a 
#             ChannelCalibrationData
#             
#         The setter has no effect for a NonChannel axis
#         """
#         return tuple((k,v) for k,v in self._data_.items() if isinstance(v, ChannelCalibrationData))
        
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
    def channelCalibrations(self) -> tuple:
        r"""A tuple of channel calibrations.
        
        This is empty when the axis type is not 'Channels'.
        
        NOTE: A VigraArray may not have an axis of type 'Channels'. For those 
        that  DO have one, this axis might be a 'singleton' axis (i.e., an axis 
        with just one element, representing the domain that contains the set of 
        data values, NOT their coordinates).
        
        The setter of this property expects a sequence of ChannelCalibrationData
        objects, with at least as many elements as there are channels in the array.
        
        For an array WITHOUT a Channels axis, this sequence should contain a single
        ChannelCalibrationData object; setting this property will results in the
        insertion of a singleton Channels axis at the highest index.
        
        For arrays WITH a channels axis, passing a sequence with fewer 
        ChannelCalibrationData objects than the size of this axis will raise an 
        exception. If the sequence has more elements that the size of the Channels
        axis, the excess calibration objects will be ignored.
        
        
        """
        # NOTE: 2025-04-08 14:39:08
        # don't return channel names anymore, just the ChannelCalibrationData
        # ('name' is a member of ChannelCalibrationData)
        ret = tuple(filter(lambda x: isinstance(x, ChannelCalibrationData), self._data_.items()))
        # ret = tuple((k,v) for k, v in self._data_.items() if isinstance(v, ChannelCalibrationData))
        #ret = list((k,v) for v in self._data_.items() if isinstance(v, ChannelCalibrationData))
        
        if len(ret) == 0 and self.type == vigra.AxisType.Channels:
            # DO return one virtual channel calibration for arrays without
            # channels axis, but flag it as such
            cal = ChannelCalibrationData(virtual=True)
            cal.name = "virtual_channel_0"
            # return (cal.name, cal)
            return (cal, )
        
        return ret
        
    @channelCalibrations.setter
    def channelCalibrations(self, val:typing.Sequence[typing.Tuple[str, typing.Union[ChannelCalibrationData, dict]]]):
        if not self.type & vigra.AxisType.Channels:
            return
        
        self.channels = val
        
    @property
    def channelNames(self):
        r"""A tuple of channel names, from their calibration data.
        These include the virtual channel (if it exists).
        
        This list is empty if the AxisCalibrationData corresponds to a 
        non-Channels axis.
        """
        return tuple(ch[1].name for ch in self.channelCalibrations)
        
    @property
    def channelIndices(self):
        r"""A tuple of channel indices, from their calibration data.
        These include the virtual channel (if it exists).
        
        This list is empty if the AxisCalibrationData corresponds to a 
        non-Channels axis.
        """
        return tuple(ch[1].index for ch in self.channelCalibrations)
        
    @property
    def nChannels(self) -> int:
        r"""Number of data channel along the axis.
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
        r"""
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
                # NOTE: 2025-04-08 14:39:48
                # see NOTE: 2025-04-08 14:39:08
                # if "virtual" not in ch[0]:
                if not ch.virtual:
                    strlist.append(f"<{ch.name}>")
                    # strlist.append(f"<{ch[0]}>")
                    for p in sorted(ChannelCalibrationData.parameters):
                        # strlist.append(__gen_xml_element__(ch[1], p))
                        # NOTE: 2025-04-08 14:39:48
                        # see NOTE: 2025-04-08 14:39:08
                        strlist.append(__gen_xml_element__(ch, p))
                    strlist.append(f"</{ch.name}>")
                    # strlist.append(f"</{ch[0]}>")
                
        strlist.append("</axis_calibration>")
        
        return "".join(strlist)
    
    @property
    def axisInfo(self):
        r"""Dynamically generated vigra.AxisInfo object
        """
        
        return vigra.AxisInfo(key = standardAxisTypeKeys[self.key], typeFlags = self.type, resolution=self.resolution, description=self.calibrationString)
        # return vigra.AxisInfo(key = vigra.AxisType(self.key), typeFlags = self.type, resolution=self.resolution, description=self.calibrationString)
        
    
    def addChannelCalibration(self, val:ChannelCalibrationData, 
                              name:typing.Optional[str]=None,
                              index:typing.Optional[int]=None):
        r"""Add/set ChannelCalibrationData
        
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
            
        # print(f"name: {name}; index: {index}")
            
        # if name in self and isinstance(self[name], ChannelCalibrationData):
        #     oldCal = self.getChannelCalibration(name)
        #     scipywarn(f"Overwriting the channel calibration data mapped to {name} in this {self.__class__.__name__} instance ({oldCal}) with {val}")
        #     # raise ArgumentError(f"This {self.__class__.__name__} instance already contains a Channel calibration data mapped to {name}")
        # 
        # if index in self:
        #     oldCal = self.getChannelCalibration(index)
        #     scipywarn(f"Overwriting the channel calibration data with index {index} in this {self.__class__.__name__} instance ({oldCal}) with {val}")
            # raise ArgumentError(f"This {self.__class__.__name__} instance already contains a Channel calibration data with index {index}")
        
        if index != val.index:
            val.index = index
            
        self._data_[name] = val
        
    def removeChannelCalibration(self, index:typing.Union[int, str]) -> typing.Union[ChannelCalibrationData]:
        r"""Removes ChannelCalibrationData for channel with specified index or name.
        
        Returns the ChannelCalibrationData, if found, else None.
        
        """
        chcal = self.getChannelCalibration(index, True)
        if chcal is None:
            return
        
        return self._data_.pop(chcal[0], None)
    
    def reindexChannels(self, index:typing.Optional[dict]=None) -> None:
        r"""Reindexes the channels
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
        r"""Yields ChannelCalibrationData sorted by chanel index, name or field.
        
        by_index: bool or str
            When bool: if True, sort by index; else sort by name
            
            When by_index is a str, it indicates the field name to sort.
            
            CAUTION: When sorting by units, all chanels must have unist with the
            same dimensionalities, or convertible to each other.
            
        """
        yield from sorted(self.channels, key = lambda x: x.by_index if instance(by_index, str) else x.index if by_index is True else x.name)
        
    def clearChannels(self):
        r"""Removes all ChannelCalibrationData associated with this object.
        """
        if not self.type & vigra.AxisType.Channels:
            return
        
        for (k,c) in self.channels:
            self._data_.pop(k, None)
                
    def getChannelCalibration(self, index:typing.Optional[typing.Union[int, str]]=None, 
                              full:typing.Optional[bool]=False,
                              physical:bool=True) -> typing.Optional[typing.Union[list, ChannelCalibrationData]]:
        r"""ChannelCalibrationData for a single channel.
        
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
        
        physical: bool, optional (default is True)
            When True (the default) then 'index', when an int, is interpreted as
            the index of the channel along the dimension of the Channels axis
            (0-based), a.k.a the 𝑝ℎ𝑦𝑠𝑖𝑐𝑎𝑙 index. WARNING: this may be different
            from the value assigned to the 'index' attribute of the channel!
        
            When False, the 'index', when an int, is taken to represent the 
            𝑙𝑜𝑔𝑖𝑐𝑎𝑙 index of the channel (i.e. the value of its 'index' attribute).
            WARNING: This may NOT the the same as the actual channel index along
            the Channels axis dimension !
        
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
        if self.type != vigra.AxisType.Channels:
            scipywarn("Not a channel axis")
            return
        
        if len(self.channelCalibrations) == 0:
            cal = ChannelCalibrationData()
            cal.name = "virtual_channel_0"
            if full:
                return (cal.name, cal) # a tuple (channel name, channel calibration)
            return cal
        
        if index is None:
            if full:
                return self.channelCalibrations[0] # a tuple (channel name, channel calibration)
            return self.channelCalibrations[0][1] # the first available channel calibration
            
        if isinstance(index, int):
            what = "index"
            
        elif isinstance(index, str):
            what = "name"
            
        else:
            raise TypeError(f"Expecting a str, int or None; got {type(index).__name__} instead.")
        
        # NOTE: 2022-01-07 00:12:54
        # 1) search by calibration name or index
        
        if isinstance(index, int) and physical:
            chcal = self.channels[index]
        else:
            # index is either a logical channel index (int) or a channel name (str)
            chcals = list(filter(lambda x: getattr(x[1], what, None) == index, self.channels))
            
            if len(chcals) == 0:
                if what == "name":
                    chcals = list(filter(lambda x: x[0]==name, self.channels))
                    
            if len(chcals) > 1:
                scipywarn(f"There is more than one channel with the same {what} ({index}).\nThe calibration for the first one will be returned", 
                            RuntimeWarning, 
                            stacklevel=2)
            elif len(chcals) == 0:
                raise ValueError(f"No channel was found for logical index or name '{index}'")
            
            chcal = chcals[0]
                
            
        # print(f"AxisCalibrationData.getChannelCalibration: chcal = {chcal}")
            
        if len(chcal):
            if full:
                return chcal
        
            else:
                return chcal[1]
            
    def getChannelIndex(self, name:str) -> typing.Optional[int]:
        r"""Returns the index of the channel with given name.
        
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
        r"""Sets the index of the channel with given name.
        
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
        r"""Returns the name of the channel with given index.
        
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
        r"""Sets the name of the channel with given index.
        
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
        r"""Returns the units of the specified channel, or None if not found
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
        r"""Associates calibration values with a vigra.AxisInfo object.
        
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
        r"""Returns the coordinates (start & stop) of an XML-formatted calibration
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
        r"""Embeds calibration sub-string in 's' into a vigra.AxisInfo object.
        
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
        r"""AxisCalibrationData factory using a calibration string.
        
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
                value = unitQuantityFromNameOrSymbol(txt)
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
            

