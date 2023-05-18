# -*- coding: utf-8 -*-
'''
utilities to enhance axis and axistags handling

    NOTE: vigra defines a set of standard axis type keys: ‘x’, ‘y’, ‘z’, ‘t’, 
    and ‘c’ and the combinations'fx','fy', and 'fz'. 
    
    This module extends this set with symbols for various combinations of 
    vigra.AxisType flags (see axisTypeSymbol function)

'''

#TODO: find a way to merge AxisSpecs class with datatypes.ScanData.axisquantities
#TODO: which is a collections.OrderedDict.
#TODO: One possibility is to re-define this class as being a mapping from axis 
#TODO: tag character (the key) to a tuple (n_samples, quantity), where quantity 
#TODO: is None for a non-calibrated axis

# 2016-12-11 00:34:19 change to mapping from tag character (the key) to AxesCalibration (the value)

#### BEGIN core python modules
from __future__ import print_function
import collections, operator, typing
from traitlets import Bunch
from functools import reduce
#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import vigra
#import signalviewer as sv
#import javabridge
#import bioformats
#### END 3rd party modules

#### BEGIN pict.core modules
import quantities as pq
from core.utilities import (reverse_mapping_lookup, unique,)

from core import quantities as cq
from core.quantities import (space_frequency_unit, 
                            angle_frequency_unit, 
                                    channel_unit, 
                                    arbitrary_unit,
                                    pixel_unit,
                                    units_convertible)

#### END pict.core modules

# NOTE: 2017-10-20 22:10:39
# I might (should?) get rid of this
#ALLOWED_AXISTAGS = (['x', 't'], 
                    #['x', 't', 'c'],
                    #['x', 'y', 't'],
                    #['x', 'y', 't', 'c'],
                    #['x', 'y', 'z', 't'],
                    #['x', 'y', 'z', 't', 'c'])

# a bit of extension to vigra defaults:
# KEY:          Type Flags:
#========================================
# a                 Angle
# c                 Channels
# e                 Edge
# f                 Frequency
# t                 Time
# x, y, z, n        Space
# fa                Frequency | Angle 
# fe                Frequency | Edge
# ft                Frequency | Time
# fx, fy, fz, fn    Frequency | Space
# ?                 Unknown
# nc                NonChannel
# ll                AllAxes


"""Maps vigra.AxisInfo keys (str, lower case) to vigra.AxisType flags
On its way to DEPRECATION
"""
standardAxisTypeKeys = Bunch({
    "a": vigra.AxisType.Angle,
    "c": vigra.AxisType.Channels,
    "e": vigra.AxisType.Edge,
    "f": vigra.AxisType.Frequency,
    "t": vigra.AxisType.Time,
    "s": vigra.AxisType.Space,
    "x": vigra.AxisType.Space,
    "y": vigra.AxisType.Space,
    "z": vigra.AxisType.Space,
    "fa": vigra.AxisType.Frequency | vigra.AxisType.Angle,
    "fe": vigra.AxisType.Frequency | vigra.AxisType.Edge,
    "ft": vigra.AxisType.Frequency | vigra.AxisType.Time,
    "fs": vigra.AxisType.Frequency | vigra.AxisType.Space,
    "fx": vigra.AxisType.Frequency | vigra.AxisType.Space,
    "fy": vigra.AxisType.Frequency | vigra.AxisType.Space,
    "fz": vigra.AxisType.Frequency | vigra.AxisType.Space,
    "?": vigra.AxisType.UnknownAxisType,
    "nc": vigra.AxisType.NonChannel,
    "ll": vigra.AxisType.AllAxes,
    }
    )

STANDARD_AXIS_TAGS_KEYS = tuple(k for k in standardAxisTypeKeys)

"""See docstring for axisTypeFromUnits for details.
"""
primitive_axis_type_units = {
    vigra.AxisType.UnknownAxisType: pq.dimensionless,
    vigra.AxisType.Channels: channel_unit,
    vigra.AxisType.Space: pq.m,
    vigra.AxisType.Edge: pixel_unit,
    vigra.AxisType.Angle: pq.radian,
    vigra.AxisType.Time: pq.s,
    vigra.AxisType.Frequency: pq.Hz,
    vigra.AxisType.NonChannel: pq.dimensionless,
    vigra.AxisType.AllAxes: pq.dimensionless,
    }

sortedAxisTypes = sorted(((k,v) for k,v in vigra.AxisType.values.items()), key=lambda x: x[0])

def getAxisTypeFlagsInt(axisinfo:typing.Union[vigra.AxisInfo, vigra.AxisType, int]) -> int:
    """Use this for the uniform treatment of argument which is AxisInfo, AxisType or int
    
    Also prevents 'impossible' axis type flag combinations such as 
    UnknownAxisType | Frequency | Edge
    
    but does alter meaningless combinations such as 
    Frequency | Edge, or Frequency | Space | Time
    
    """
    if isinstance(axisinfo, vigra.AxisInfo):
        return axisinfo.typeFlags.numerator
        
    if isinstance(axisinfo, vigra.AxisType):
        return axisinfo.numerator
        
    if isinstance(axisinfo, int):
        if axisinfo & vigra.AxisType.UnknownAxisType:
            return vigra.AxisType.UnknownAxisType
        
        if axisinfo in (vigra.AxisType.AllAxes, vigra.AxisType.NonChannel):
            return axisinfo
        
        test = list(v[1] for v in sortedAxisTypes if v[0] & axisinfo)
        
        if len(test) == 0:
            return vigra.AxisType.UnknownAxisType
        
        return axisinfo
        
    raise TypeError(f"Expecting a vigra.AxisType or vigra.AxisInfo; got {type(axisinfo).__name__} instead")

def axisTypeUnits(axisinfo:typing.Union[vigra.AxisInfo, vigra.AxisType, int]) -> pq.Quantity:
    """Returns a default Python Quantity based on the axisinfo parameter.
    
    Positional parameters:
    ======================
    axisinfo: a vigra.AxisInfo object, a vigra.AxisType object or an valid integer
        resulted from bitwise OR between vigra.AxisType objects.
    
    Returns:
    ========
    
    A python quantity object (quantities.Quantity) that provides a reasonable
    default given the type flags in axisinfo
    
    For unknown axis types, returns pixel_unit.
    
    Tries to mirror the rules set in axisTypeFromUnits
    
    CAUTION: These are recommended, and not fully enforced
    """
    
    typeint = getAxisTypeFlagsInt(axisinfo)
    
    if typeint in vigra.AxisType.values:
        return primitive_axis_type_units[typeint]
    
    typenames = axisTypeStrings(typeint)
    
    if len(typenames):
        if len(typenames) > 1:
            if "Frequency" in typenames:
                if len(typenames) > 2:
                    ## certainly NOT a meaningful combination
                    return pq.dimensionless
                
                if "Time" in typenames:
                    return pq.Hz # (1/pq.s)
                
                if "Space" in typenames:
                    return 1/pq.m
                
                if "Angle" in typenames:
                    return 1/pq.radian
                
                if "Edge" in typenames:
                    return 1/pixel_unit
                
                return pq.Hz
            
            # combinations of axis type flags that do not include frequency are
            # not meaningful
            return pq.dimensionless
        
        # almost surely we never land here
        return primitive_axis_type_units(typenames[0])
    
    return pq.dimensionless

def axisTypeFromUnits(u:typing.Union[pq.Quantity, pq.dimensionality.Dimensionality]) -> vigra.AxisType:
    """Return a vigra.AxisType flag given dimensionality units 'u'
    
    BY CONVENTION:
    
    Units                                       AxisType 
                                                (members of vigra.AxisType):
    ============================================================================
    pixel_unit                                  Edge
    
    pq.dimensionless                            UnkownAxisType
    
    Convertible to pq.meter                     Space
    
    Convertible to pq.second                    Time
    
    Convertible to pq.radian                    Angle
    
    Convertible to pq.Hz or 1/pq.s              Frequency or
                                                Time  | Frequency
    
    Convertible to 1/pq.meter                   Space | Frequency
    
    Convertible to 1/pq.radian                  Angle | Frequency
    
    Convertible to 1/pixel_unit                 Edge  | Frequency
    
    channel_unit                                Channels
    
    anything else, including arbitrary_unit     Channels (pixel intensities)
    ============================================================================

    CAUTION: These are recommended, and not fully enforced
    
    NOTE 
    
    1) Frequency is numerically distinct from, although semantically identical to, 
    Frequency | Time. Therefore, units convertible to pq.Hz will return the 
    latter.
    
    1.a) The Python quantities package also defined 'cycle' units, which are in
    fact derived from radians. So, using 'cycle' as units cannot distinguish 
    between a Frequency and an Angle axis (see next point).
    
    2) Angle can represent:
        * the phase component (as real numbers) of an imaginary data type (e.g. 
          the result of a Fourier transform). 
    
        * an angular physical measure (e.g. the 'angle' component of polar 
            coordinates, with the 'space' component being represented on an 
            orthogonal axis). 
            
            A suitable axis system for the Fourier transform of this data 
            would be (Angle | Frequency) x (Space | Frequency).
            
        Therefore, units convertibel to pq.radian will return Angle.
    
     3) Edge is a special type of axis for data resulting from VIGRA's edge 
     detection algorithms, and the custom datatypes.pixel_unit seems most 
     suitable for this purpose.
     
     There is nothing against taking a Fourier transform of this, either, so the
     corresponding axis type would be Edge | Frequency
    
     4) pq.dimensionless is reserved for UnkownAxisType.
     
     5) To distinguish a Channels axis from anything else, we use channel_unit
     (dimensionless) such that for a data set with n channels, the axis coordinate
     will be shown in "channel_unit" coordinates.
     
     Pixel intensities need their units too. Since they represent physical data
     (either measured or calculated) their units are either arbitrary_unit, or 
     any one of the available units, either primary or derived ('composite', 
     e.g. pq.m/pq.s for velocity).
     
     Therefore, WITH THE EXCEPTION OF THE UNITS MENTIONED AT POINTS (1)-(4), 
     passing any of these units as parameter to this function will return a
     Channels axis type, to flag the caller that such units are meant to be used
     for the pixel intensities.
     
    """
    # NOTE: 2021-11-27 17:13:56
    # casting of int to vigra.AxisType required to conform to what the C++
    # signature of vigra.AxisInfo.__init__ expects.
    if isinstance(u, pq.dimensionality.Dimensionality):
        u_simp = u.simplified
        if len(u_simp) == 1:
            u = [k for k in u_simp][0]
            
        else:
            u = functools.reduce(operator.mul, (i[0]**i[1] for i in u.items()))
        
    if isinstance(u, pq.Quantity):
        if u is pixel_unit:
            return vigra.AxisType.Edge
        
        elif u is pq.dimensionless:
            return vigra.AxisType.UnknownAxisType
        
        elif units_convertible(u.units, pq.m):
            return vigra.AxisType.Space
        
        elif units_convertible(u.units, pq.s):
            return vigra.AxisType.Time
        
        elif units_convertible(u.units, pq.radian):
            return vigra.AxisType.Angle
        
        elif units_convertible(u.units, pq.Hz):
            # this can/should be further distinguished to either Frequency, or 
            # Frequency | Time, in the caller code.
            # see  NOTE: 2021-11-27 17:13:56 for why we cast to vigra.AxisType
            return vigra.AxisType(vigra.AxisType.Frequency | vigra.AxisType.Time)
        
        elif units_convertible(u.units, 1/pq.m):
            return vigra.AxisType(vigra.AxisType.Frequency | vigra.AxisType.Space)
        
        elif units_convertible(u.units, 1/pq.radian):
            return vigra.AxisType(vigra.AxisType.Frequency | vigra.AxisType.Angle)
        
        elif units_convertible(u.units, 1/pixel_unit):
            return vigra.AxisType(vigra.AxisType.Frequency | vigra.AxisType.Edge)
        
        else: # anything else including chanel_unit
            # this needs to be further verifined in calling code
            return vigra.AxisType.Channels
        
    return vigra.AxisType.UnknownAxisType
        
    
#def axisTypeFromString(s:str) -> typing.Union[vigra.AxisType, int]:
def axisTypeFromString(s:str) -> vigra.AxisType:
    """Inverse lookup of axis type flags from descriptive string or axis info key.
    Performs the reverse of axisTypeName and the reverse mapping of standardAxisTypeKeys.
    
    CAUTION: These are recommended, and not fully enforced
    
    Parameters:
    -----------
    s:str Axis type key, name or description string that can be meaningfully 
        interpreted into an axis type flag
        
    Returns:
    --------
    vigra.AxisType flag 
    
    """
    # NOTE: 2021-11-27 17:25:14
    # Needs explicit cast of the result of OR-ed AxisType flags to vigra.AxisType
    # 
    # In Python, the OR operation casts the AxisType flag operands to int and 
    # the result is an int. This is not what the C++ signature of vigra.AxisInfo
    # constructor ('vigra.AxisInfo.__init__') expects. Not sure why Boost.Python
    # doesn't seem to take care of this, but to be safe we explicitly perform 
    # the cast back to AxisType
    # see also NOTE: 2021-11-27 17:13:56
    try:
        return evalAxisTypeExpression(s)
    
    except AttributeError:
        # deal with some humanly meaningful strings
        if s.lower() in ("channel", "channels", "c"):
            return vigra.AxisType.Channels
        
        elif s.lower() in ("width","height", "depth", "space", "spatial", "distance", "s", "x", "y", "z"):
            return vigra.AxisType.Space
        
        elif s.lower() in ("angular range", "angular", "angle", "a"):
            return vigra.AxisType.Angle
        
        elif s.lower() in ("time", "temporal", "duration", "t"):
            return vigra.AxisType.Time
        
        elif s.lower() in ("frequency", "frequency range", "f"):
            return vigra.AxisType.Frequency
        
        elif s.lower() in ("spatial frequency range", "spatial frequency", "spatial sampling", 
                           "fs", "fx", "fy", "fz", 
                           "sf", "xf", "yf", "xf"):
            return vigra.AxisType.Frequency | vigra.AxisType.Space
        
        elif s.lower() in ("temporal frequency range", "temporal frequency", "temporal sampling", 
                           "ft", "tf"):
            return vigra.AxisType.Frequency | vigra.AxisType.Time
        
        elif s.lower() in ("angular frequency range", "angular frequency", "angular sampling", "fa", "af"):
            return vigra.AxisType.Frequency | vigra.AxisType.Angle
        
        elif s.lower() in ("fe", "ef"):
            return vigra.AxisType.Frequency | vigra.AxisType.Edge
        
        elif s.lower() in ("edge", "e"):
            return vigra.AxisType.Edge
        
        elif s.lower() in ("unknownaxistype", "unknown axis type", "unknown type", "unknown", "size", "?", "u", "uk", "ut"):
            return vigra.AxisType.UnknownAxisType
        
        elif s.lower() in ("nonchannel", "non channel", "nc"):
            return vigra.AxisType.NonChannel
        
        elif s.lower() in ("allaxes", "all axes", "ll", "aa"):
            return vigra.AxisType.AllAxes
        
        else:
            # deal with less meaningful strings on the assumption that these are
            # concatenated symbols - this assumption may be wrong but then I can't
            # anticipate everything!
            # use with CAUTION - you have been WARNED
            typestr = unique(s.lower())
            types = list()
            if "a" in typestr:
                types.append(vigra.AxisType.Angle)
                
            if "c" in typestr:
                types.append(vigra.AxisType.Channels)
                
            if "e" in typestr:
                types.append(vigra.AxisType.Edge)
                
            if "f" in typestr:
                types.append(vigra.AxisType.Frequency)
                
            if "t" in typestr:
                types.append(vigra.AxisType.Time)
                
            if any(s_ in typestr for s_ in ("s", "x", "y", "z")):
                types.append(vigra.AxisType.Space)
                
            if any(s_ in typestr for s_ in ("?", "u")):
                vigra.AxisType.UnknownAxisType
                
            if "ll" in typestr:
                return vigra.AxisType.AllAxes
                
            if "nc" in typestr:
                return vigra.AxisType.NonChannel
                
            if len(types):
                return vigra.AxisType(reduce(operator.or_, types))
                
            return vigra.AxisType.UnknownAxisType
    
def axisTypeStrings(axisinfo:typing.Union[vigra.AxisInfo, vigra.AxisType, int, str],
                    as_expr:bool=False, single:bool=False) -> typing.Union[typing.List[str], str]:
    """Returns a literal representations of AxisType flags.
    
    Vigra axis type flags are primitive flags, e.g., vigra.AxisType.Space, or a
    combination of primitive flags 'OR-ed' together in a meaningful way, such as
    vigra.AxisType.Space | vigra.AxisType.Frequence.
        
    This function returns the literal names of the primitive AxisType flag
    associated with the axis, s a list.
    
    Optionally, the names are returned as a single str, 'joined' by a space
    (when 'single' is True) or by '|' ('as_expr' is True)
    
    WARNING: Although numerically possible, not all combinations of primitive
    AxisType flags is meaningful!
    
    Returns:
    ========
    
    When both 'as_expr' and 'single' are False (the default):
    
        For primitive type flags, returns a list of one string (e.g. ['Space'], 
        ['Time'], etc.)
        
        For type flags computed by OR-ed primitive type flags, the list contains the
        names primitive flags (e.g. ['Frequency', 'Space'], or ['Frequency', 'Time'],
        etc.)
        
    When 'single' is True, returns a single string where the strings otherwise 
        returned in a list are separated by ' ' (space).
        
    When as_expr is True, returns a single string where the strings otherwise 
        returned in a list are separated by '|' . In this case the returned 
        string can be 'transformed' back to a type flag by passing it to the
        evalAxisTypeExpression() function.
        
    
    Examples:
    =========
    in:  v = vigra.AxisType.Frequency | vigra.AxisType.Edge | vigra.AxisType.Space
    
    in:  v
    out: 50
    
    in:  s = axisTypeStrings(v)
    out: ['Edge' 'Frequency' 'Space']
    
    in:  s = axisTypeStrings(v, as_expr = True)
    
    in:  s
    out: 'Edge|Frequency|Space'
    
    The expression in `s` can be `eval`-ed with evalAxisTypeExpression:
    
    in:  evalAxisTypeExpression(s)
    out: 50
    
    in:  v == evalAxisTypeExpression(s)
    out: True
    
    """
    
    if isinstance(axisinfo, str):
        typeint = axisTypeFromString(axisinfo)
    else:
        typeint = getAxisTypeFlagsInt(axisinfo)
    
    if typeint in vigra.AxisType.values:
        return [vigra.AxisType.values[typeint].name]
    
    if typeint & vigra.AxisType.UnknownAxisType:
        return vigra.AxisType.UnknownAxisType
    
    primitives = (v[1].name for v in reversed(sortedAxisTypes) if v[0] & typeint)
    
    # NOTE: below, exclude AllAxes and NonChannels because they will always map
    return "|".join(list(primitives)[2:]) if as_expr else  " ".join(list(primitives[2:])) if single else list(primitives)[2:]

def evalAxisTypeExpression(x:str) -> vigra.AxisType:
    """Evaluates a string representation  of vigra.AxisType type flags.
    
    Parameters:
    ==========
    
    x:str a vigra.AxisType name or a string containing several vigra.AxisType
    names separated by '|' e.g. 'Frequency|Space' (all are case-sensitive)
    
    WARNING: Although numerically possible, not all combinations of primitive
    AxisType flags is meaningful!
    
    Returns:
    vigra.AxisType flag
    
    """
    return vigra.AxisType(eval("|".join([f"vigra.AxisType.{s}" for s in x.split("|")])))
    
def axisTypeName(axisinfo:typing.Union[vigra.AxisInfo, vigra.AxisType, int, str]) -> str:
    """Generates an axis name based on the axis info or axis type flag.
    
    Do NOT confuse with axisTypeStrings().
    
    Positional parameters:
    ======================
    
    axisinfo: a vigra.AxisInfo object, or a viga.AxisType object, or an int
        resulted from bitwise OR between vigra.AxisType objects.
    
    Returns:
    ========
    
    A generic description of the type flags contained in axisinfo.
    
    If axisinfo is a vigra.AxisInfo object for a spatial axis, then the function
    uses the "key" symbol in the axisinfo to provide a more specific string 
    (e.g.,"Width", or "Height", for space axis with keys "x" or "y", respectively).
    
    CAUTION: These are recommended, and not fully enforced
    """
    if isinstance(axisinfo, str):
        typeint =  axisTypeFromString(axisinfo)
    else:
        typeint = getAxisTypeFlagsInt(axisinfo)
    
    if typeint in vigra.AxisType.values:
        if isinstance(axisinfo, vigra.AxisInfo):
            infokey = axisinfo.key
        else:
            infokey = axisTypeSymbol(typeint)

        if isinstance(infokey, str):
            if "x" in infokey:
                return "Width"
            if "y" in infokey:
                return "Height"
            if "z" in infokey:
                return "Depth"
            
            return vigra.AxisType.values[typeint].name
        
        return vigra.AxisType.values[typeint].name
        
    return " ".join(reversed(axisTypeStrings(typeint)))
        
def axisTypeSymbol(axisinfo:typing.Union[vigra.AxisInfo, vigra.AxisType, int],
                          upper:bool = False) -> str:
    """Maps vigra.AxisInfo object to a default string symbol (or "key").
    
    Positional parameters:
    ======================
    
    axisinfo: a vigra.AxisInfo object.
    
    Keyword parameters:
    ===================
    
    upper:bool Optional, default is False: when True return upper case symbol.
    
    Returns:
    ========
    
    A string key corresponding to the type flags in axisinfo object (in upper case).
    

    CAUTION: These are recommended, and not fully enforced
    """
    if isinstance(axisinfo, vigra.AxisInfo):
        if axisinfo.key not in ("?", "nc", "ll"): # force checking these types
            return axisinfo.key
        
    typeint = getAxisTypeFlagsInt(axisinfo)
    
    if typeint in vigra.AxisType.values:
        if typeint == vigra.AxisType.UnknownAxisType:
            return '?'
        if typeint == vigra.AxisType.NonChannel:
            return "nc"
        if typeint == vigra.AxisType.AllAxes:
            return "ll"
        
        n = vigra.AxisType.values[typeint].name[0]
    
    else:
        names = ['?' if s =="UnknownAxisType" else 'll' if s == "AllAxes" else "nc" if s=="NonChannel" else s[0].lower() for s in reversed(axisTypeStrings(typeint))]
        n = "".join(names)
        
    return n.upper() if upper else n.lower()

def hasChannelAxis(data):
    if isinstance(data, vigra.VigraArray):
        return data.axistags.channelIndex < data.ndim
    
    elif isinstance(data, vigra.AxisTags):
        return data.channelIndex < len(data)
    
    else:
        raise TypeError("Expected a VigraArray or AxisTags object; instead, I've got a %s" % type(data).__name__)
    
def dimIter(data, key):
    """Iterator along the dimension of the given axis key for Vigra arrays.
    
    Rationale:
    ==========
    VigraArrays have channelIter, sliceIter, spaceIter and timeIter methods.
    While these generate iterators, respectively, along a channel, space, and time
    axis, they tend to be too specialized:
    
        sliceIter(key) iterates along a single spatial axis specified by key
        
        spaceIter iterates along _ALL_ spatial axes (AxisType.Space), taken 
            in the order they appear in axistags.
            
        timeIter does the same for ALL axis of type AxisType.Time
        
    On the other hand, except for channel axes, vigranumpy does not restrict
    the number of axes that an array can have.
    
    For example an array might have two time axes. For example, in linescan experiments
    that collect dynamic fluorescence data, one linescan series generates an image
    where 1st axis has AxisType.Space and the second axis has AxisType.Time.
    Several such linescans can be collected as a higher dimension array, where
    the third axis would alsobe a temporal axis (AxisType.Time).
    
    It would be helpful to have an iterator along the second time axis (i.e. across
    individual linescan images in the data set), but timeIter() would automatically
    iterate over _ALL_ time axes in the order they appear in axistags.
    
    The present function aims to fill this gap in functionality by generating an 
    iterator along any axis specified by its key, irrespective of its AxisType flag,
    and irrespective of how many such axes are present in the array.
    
    """
    
    if not isinstance(data, vigra.VigraArray):
        raise TypeError("First parameter expected to be a VigraArray; got %s instead" % (type(data).__name__))
    
    if not isinstance(key, str):
        raise TypeError("Second parameter expected to be a str; got %s instead" % (type(key).__name__))
    
    # NOTE: 2017-11-15 11:55:41
    # almost a direct copy of VigraArray.sliceIter(), but without restriction to
    # AxisType.Space
    
    if isinstance(key, str):
        i = data.axistags.index(key)
        
    elif isinstance(key, vigra.AxisInfo):
        i = data.axistags.index(key.key)
        
    else:
        raise TypeError("Expecting a vigra.AxisInfo object or a str with a vigra.AxisInfo key; got %s instead" % (type(key).__name__))
    
    if i < data.ndim: # axis found
        for k in range(data.shape[i]):
            yield data.bindAxis(i,k)
            
    else: # axis NOT found => yield the entire array, it being a single "slice" along the non-existent axis
        yield data
        
def dimEnum(data, key):
    """Generates a tuple (k, slice) along dimension with axistag "key".
    Simlar to dimIter, but in addition outputs the int index of the slice.
    See dimIter for more details.
    """
    if not isinstance(data, vigra.VigraArray):
        raise TypeError("First parameter expected to be a VigraArray; got %s instead" % (type(data).__name__))
    
    if not isinstance(key, str):
        raise TypeError("Second parameter expected to be a str; got %s instead" % (type(key).__name__))
    
    if isinstance(key, str):
        i = data.axistags.index(key)
    
    elif isinstance(key, vigra.AxisInfo):
        i = data.axistags.index(key.key)
        
    else:
        raise TypeError("Expecting a vigra.AxisInfo object or a str with a vigra.AxisInfo key; got %s instead" % (type(key).__name__))
    
    if i < data.ndim: # axis found
        for k in range(data.shape[i]):
            yield (k, data.bindAxis(i,k))
            
    else: # axis NOT found => yield the entire array, it being a single "slice" along the non-existent axis
        yield (0, data)
        
def getNonChannelDimensions(img):
    if not isinstance(img, vigra.VigraArray):
        raise TypeError("Expecting a VigraArray; got %s instead" % type(img).__name__)
    
    if img.channelIndex == img.ndim:
        return img.ndim
    
    else:
        return img.ndim-1 # VigraArray objects can have at most one channel axis!
        
#def _getTypeFlag_(value):
    #"""Needed because there is faulty translation of AxisType data structure between python & C++
    #TODO/FIXME Revisit this DEPRECATED
    #"""
    #if not isinstance(value, int):
        #raise TypeError("Expecting an int")
    
    #if value == vigra.AxisType.Channels.numerator:
        #return vigra.AxisType.Channels
    
    #elif value == vigra.AxisType.Space.numerator:
        #return vigra.AxisType.Space
    
    #elif value == vigra.AxisType.Angle.numerator:
        #return vigra.AxisType.Angle
    
    #elif value == vigra.AxisType.Time.numerator:
        #return vigra.AxisType.Time
    
    #elif value == vigra.AxisType.Frequency.numerator:
        #return vigra.AxisType.Frequency
    
    #elif value == vigra.AxisType.Frequency | vigra.AxisType.Space:
        #return vigra.AxisType.Frequency | vigra.AxisType.Space
    
    #elif value == vigra.AxisType.Frequency | vigra.AxisType.Time:
        #return vigra.AxisType.Frequency | vigra.AxisType.Time
    
    #elif value == vigra.AxisType.Frequency | vigra.AxisType.Angle:
        #return vigra.AxisType.Frequency | vigra.AxisType.Angle
    
    #elif value == vigra.AxisType.Edge.numerator:
        #return vigra.AxisType.Edge
    
    #elif value == vigra.AxisType.UnknownAxisType.numerator:
        #return vigra.AxisType.UnknownAxisType
    
    #elif value == vigra.AxisType.NonChannel.numerator:
        #return vigra.AxisType.NonChannel
    
    #elif value == vigra.AxisType.AllAxes.numerator:
        #return vigra.AxisType.AllAxes
    
    #else:
        #return vigra.AxisType.UnknownAxisType
    

def isValidAxisType(x:typing.Union[vigra.AxisType, int]):
    if isinstance(x, vigra.AxisType):
        return True
    
    if isinstance(x, int):
        if x not in vigra.AxisType.values:
            return len( list(v[1] for v in sortedAxisTypes if v[0] & x)) > 0
        return True
    
    return False

def isSpecificAxisType(x:typing.Union[vigra.AxisType, int, str]):
    if isinstance(x, str):
        x = axisTypeFromString(x)
        
    if isinstance(x, vigra.AxisType):
        return x not in (vigra.AxisType.NonChannel, vigra.AxisType.AllAxes)
    
    if isinstance(x, int):
        if not x in vigra.AxisType.values:
            return len(list(v[1] for v in sortedAxisTypes if v[0] & x))> 3
        
        # by condition above x is already in vigra.AxisType.values; we include
        # UnknownAxisType among specifc axis types
        return x <= 64 
    
    return False
        
        
        
    
    
