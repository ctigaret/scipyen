# -*- coding: utf-8 -*-
'''
utilities to enhance axis and axistags handling
'''

#TODO: find a way to merge AxisSpecs class with datatypes.ScanData.axisquantities
#TODO: which is a collections.OrderedDict.
#TODO: One possibility is to re-define this class as being a mapping from axis 
#TODO: tag character (the key) to a tuple (n_samples, quantity), where quantity 
#TODO: is None for a non-calibrated axis

# 2016-12-11 00:34:19 change to mapping from tag character (the key) to AxisCalibration (the value)

#### BEGIN core python modules
from __future__ import print_function
import collections
#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import vigra
import quantities as pq
#import signalviewer as sv
#import javabridge
#import bioformats
#### END 3rd party modules

#### BEGIN pict.core modules
#from . import datatypes
#### END pict.core modules

# NOTE: 2017-10-20 22:10:39
# I might (should?) get rid of this
ALLOWED_AXISTAGS = (['x', 't'], 
                    ['x', 't', 'c'],
                    ['x', 'y', 't'],
                    ['x', 'y', 't', 'c'],
                    ['x', 'y', 'z', 't'],
                    ['x', 'y', 'z', 't', 'c'])

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
# s                 NonChannel
# l                 AllAxes
__standard_axis_tag_keys__ = ["x", "y", "z", "t", "c", "n", "e", "fx", "fy", "fz", "ft"]
__specific_axis_tag_keys__ = __standard_axis_tag_keys__  + ["a", "f", "ft", "fa"]
__all_axis_tag_keys__ = __specific_axis_tag_keys__ + ["?", "l"]

"""Maps vigra.AxisInfo keys (str, lower case) to vigra.AxisType flags
"""
axisTypeFlags = collections.defaultdict(lambda: vigra.AxisType.UnknownAxisType)
axisTypeFlags["a"]  = vigra.AxisType.Angle
axisTypeFlags["c"]  = vigra.AxisType.Channels
axisTypeFlags["e"]  = vigra.AxisType.Edge
axisTypeFlags["f"]  = vigra.AxisType.Frequency
axisTypeFlags["t"]  = vigra.AxisType.Time
axisTypeFlags["x"]  = vigra.AxisType.Space
axisTypeFlags["y"]  = vigra.AxisType.Space
axisTypeFlags["z"]  = vigra.AxisType.Space
axisTypeFlags["n"]  = vigra.AxisType.Space
axisTypeFlags["fa"] = vigra.AxisType.Frequency | vigra.AxisType.Angle
axisTypeFlags["fe"] = vigra.AxisType.Frequency | vigra.AxisType.Edge
axisTypeFlags["ft"] = vigra.AxisType.Frequency | vigra.AxisType.Time
axisTypeFlags["fx"] = vigra.AxisType.Frequency | vigra.AxisType.Space
axisTypeFlags["fy"] = vigra.AxisType.Frequency | vigra.AxisType.Space
axisTypeFlags["fz"] = vigra.AxisType.Frequency | vigra.AxisType.Space
axisTypeFlags["fn"] = vigra.AxisType.Frequency | vigra.AxisType.Space
axisTypeFlags["?"]  = vigra.AxisType.UnknownAxisType
axisTypeFlags["s"]  = vigra.AxisType.NonChannel
axisTypeFlags["l"]  = vigra.AxisType.AllAxes



def makeAxisSpec(tags, dims=None, **tagsizemap):
    '''
    Factory function
        Creates an axis specification object (AxisSpec) that 
        specifies the axis tags and its size. The (key, value) pairs in this object
        specify the sizes of the axes in a VigraArray, identified by character tags.
        
        See also vigranumpy documentation for the use of axis tags. Here, the 'tags'
        are only character symbols used to generate proper AxisTag objects associated 
        with vigra arrays.
        
        Parameters:
        
        tags:   A sequence (tuple or list) of valid single character axis tags,
                or a vigra.VigraArray object, or a collections.OrderedDict object,
                or None.
                
                When a sequence, valid elements are: "x", "y", "z", "c", and "t".
        
        dims:   None (default) or a sequence (tuple or list).
        
                Simply refers to the size (in samples) of each axis. NOTE: do 
                not confuse with any quantities associated with the axis (e.g. 
                space or time resolution, or physical dimension associated with 
                a particular channel).
        
                Can be None only iff 'tags' is a vigra.VigraArray object or a
                collections.OrderedDict object.
                
                When a sequence, elements of 'dims' can be scalar integral values, 
                single character axis tags, None, or a mixture these, representing 
                the values of the size for each of the axistags given in 'tags'. 
                
                A numeric element specifies the dimenson of the axis with the tag
                at the same index and this element, in the tags sequence.
                
                When an element is a valid tag character, it indicates that the 
                size of the axis with the specified tag is taken to be the size 
                of the axis with that tag in some pre-existing data (assuming that
                such pre-existing data contains an axis with that tag).
                
                In addition, 'dims' may contain at most one None element which 
                indicates that the size of the corresponding axis will have to
                be calculated given the total number of samples in the data and 
                the sizes of all the other axes.
                
                Valid values for 'dims' elements when it is a sequence are: 
                any integer > 0, x, y, z, c, t, and None
                
        tagsizemap: Key-Value pairs (up to five) with the axis tag (key) and size,
                used as an alternative to specifying axis tags and dimensions when
                tags and dims are both None.
                
        AxisSpecs objects where at least some of the values are strings, on where
        one of the values is None are so-called "incomplete" or "undetermined":
        they specify tags for axes for which the size has not been yet determined.
        
        This situation arises when the axis size is not known for all axes, when
        the object is created, but the unknown sizes can be determined at a later 
        time (see Examples (2) - (4), below).
        
        Example:
        
        # (1) calls AxisSpecs(tags, dims)
        
        axs = AxisSpec(('x','y','z','c'), (256,256,1,2))
        
        OrderedDict([('x', 256), ('y', 256), ('z', 1), ('c', 2)])
        
        (2) 
        
        axs = AxisSpec(('x','y','z','c'),('x','y','z',2))
        
        OrderedDict([('x', 'x'), ('y', 'y'), ('z', 'z'), ('c', 2)])
        
        here, the sizes of the 'x', 'y', and 'z' axes are taken from pre-existing data
        
        (3) assume one has loaded a vigra array from an image file
        
        data
        
        --> VigraArray(shape=(256, 1500, 2, 1), axistags=x y z c, dtype=float32, data=...)
        
        but the axistags are wrong; they should have been x y c z (i.e. the image is NOT 
        a stack of TWO FRAMES, but a single frame with TWO CHANNELS)
        
        
        axs = AxisSpec(('x','y','z','c'),('x','y',1,2))
        
        generates
        
        OrderedDict([('x', 'x'), ('y', 'y'), ('z', 1), ('c', 2)])
        
        which can be applied to the data by calling 'applyAxisSpec(data, axs)'
        
        (4)
        
        vigra array is loaded from multi-image tiff file as a stack:
        
        stackdata
        -->VigraArray(shape=(256, 256, 172, 1), axistags=x y z c, dtype=float32, data=...)
        
        in fact, the data is a Z-stack with two channels; to correct this use
        
        axs = AxisSpec(('x','y','z','c'),('x','y',None,2))
        
        
    '''
    if tags is not None:
        if dims is None:
            if isinstance(tags, vigra.VigraArray):
                dims = tags.shape
                mytags = tags.axistags.keys()
            elif isinstance(tags, collections.OrderedDict):
                dims = tags.values()
                mytags = tags.keys()
            else:
                raise TypeError("The dims argument can be None only if tags is a vigra.VigraArray or a collections.OrderedDict object")

        elif type(dims) is tuple or type(dims) is list:
        
            if type(tags) is not tuple and type(tags) is not list:
                raise TypeError('When both arguments are given, they must be either tuples or lists')
            
            if len(tags) > 5 or len(dims) > 5:
                raise ValueError('Both tags and dims must have at most five elements')
            
            if len(tags) != len(dims):
                raise ValueError('Both tags and dims must have the same number of elements')
            
            # check the tags argumment
            
            for k1 in tags:
                if type(k1) is not str or k1 not in __allowed_axis_tag_keys__:
                    raise ValueError('Incorrect axis tag key. Acceptable keys are %s' % __allowed_axis_tag_keys__)
                
            # check dims
            
            for v in dims:
                if type(v) is str:
                    if not v in __allowed_axis_tag_keys__:
                        raise ValueError('Axis size specification "%s" is not allowed. Allowed values are %s' % (v, __allowed_axis_tag_keys__))
                    else:
                        pass
                elif v is None or type(v) is int:
                    pass
                else:
                    raise TypeError('Unexpected value type (%s) in second argument' % type(v))
                
            testNone = np.where(np.equal(dims, None))[0]
            
            if len(testNone) > 1:
                raise ValueError('Second argument can contain at most one element which is None')
            
            mytags = tags
            
    else:
        
        if len(tagsizemap) == 0:
            raise SyntaxError("Keyword parameters are required when positional parameters are both None")
        
        elif len(tagsizemap) > 5:
            raise ValueError("Too many keyword parameters (maximum of 5)")
        
        mytags = tagsizemap.keys()
        dims   = tagsizemap.values()
        
        for k in tags:
            if type(k) is not str or k not in __allowed_axis_tag_keys__:
                raise ValueError('Incorrect axis tag key. Acceptable keys are %s' % __allowed_axis_tag_keys__)
            
        for k in dims:
            if type(v) is str:
                if not v in __allowed_axis_tag_keys__:
                    raise ValueError('Axis size specification "%s" is not allowed. Allowed values are %s' % (v, __allowed_axis_tag_keys__))
                else:
                    pass
            elif v is None or type(v) is int:
                pass
            else:
                raise TypeError('Unexpected value type (%s) in second argument' % type(v))
            
        testNone = np.where(np.equal(dims, None))[0]
        
        if len(testNone) > 1:
            raise ValueError('Second argument can contain at most one element which is None')
            
        
    return None # for now

def verifyAxisSpecs(newSpecs, oldSpecs):
    '''
    DEPRECATED
    
    Verifies axis specs in newSpecs for consistency given old axis specs in oldSpecs:
    
    * checks syntax for axis tag/dimension specifications
    
    * assigns axis sizes where necessary (e.g. where axis tag size in newSpecs are specified using
    an axis tag character or none)
    
    * and verifies that the newSpecs does not change the number or samples in data, 
      just its shape (and possibly, axis tags)
        
    Parameters:
    
    newSpecs:   collections.OrderedDict with axis tags/size specification (see makeAxisSpec)
    
    oldSpec:    collections.OrderedDict with axis tags/size specification taken from 
                pre-existing data
                
    Returns:
    
    newSpecs (for convenience)
        
    newSpecs are passed by reference, it being a dictionary, so any modifications
    will be seen from the caller of the function immediately, without a need to 
    assign the returned result to a new variable (which will only be a new reference
    to the original newSpecs, now modified by this function)
    
    If that is not what is intended, then pass a _DEEP_ copy to the function as in:
    
    newVal = verifyAxisSpecs(initialVal.copy(), testSpecs)
    
    '''
    if type(newSpecs) is not collections.OrderedDict:
        raise ValueError('First argument must be a collections.OrderedDict')
    
    if type(oldSpecs) is not collections.OrderedDict:
        raise ValueError('Second argument must be a collections.OrderedDict')
    
    if len(newSpecs) > 5 or len(oldSpecs) > 5:
        raise ValueError('Axis specs must have at most five elements')
    
            
    nSamples = np.prod(oldSpecs.values())
    
    for k1, k2 in zip(newSpecs.iterkeys(), oldSpecs.iterkeys()):
        if k1 not in 'xyczt' or k2 not in 'xyzct':
            raise ValueError('Incorrect axis specification key. Acceptable keys are "x", "y", "z", "c", "t"')
        
        if type(newSpecs[k1]) is str:
            if newSpecs[k1] in oldSpecs.keys():
                newSpecs[k1] = oldSpecs[newSpecs[k1]]
            else:
                raise ValueError("Value of axis spec in newSpecs not found in oldSpecs")
            
        elif type(newSpecs[k1]) is int or newSpecs[k1] is None:
            pass
        
        else:
            raise ValueError('Axis specification value must be a character, an int or None')
        
    noneAxis = np.where(np.equal(newSpecs.values(), None))[0]
    
    if len(noneAxis) > 1:
        raise ValueError("At most one axis dimension may be None ")
    
    elif len(noneAxis) == 1:
        okAxis = np.where(np.not_equal(newSpecs.values(), None))[0]
        okValues = np.asarray(newSpecs.values())[okAxis]
        newSpecs[newSpecs.keys()[noneAxis]] = nSamples / np.prod(okValues)
        
    if np.prod(newSpecs.values()) != nSamples:
        raise ValueError("New axis specification should not change the number of samples in the data")
    
    return newSpecs # 2016-03-15 14:05:43 for convenience

def tagKeysAsString(val):
    '''
    DEPRECATED
    Convenience function that collapses the axis tag keys in axis specification 
    dictionary 'val' into a string ('str') that can be used to specify axistags 
    for a VigraArray.
    
    Parameters: 
    
    val:        collections.OrderedDict with tag/size pairs (see makeAxisSpec)
    
    Returns
    
    A str object with the axis tag characters specified in 'val'
    
    '''
    if type(val) is not collections.OrderedDict:
        raise ValueError ('collections.OrderedDict expected')
    
    ret = str()
    
    for k in val.keys():
        ret += k
        
    return ret

def makeAxisSpec_old(tags, dims):
    '''
    DEPRECATED
    Creates an axis specification object (collections.OrderedDict) that 
    specifies the axis tags and its size. The (key, value) pairs in this object
    specify the sizes of the axes in a VigraArray, identified by character tags.
    
    See also vigranumpy documentation for the use of axis tags. Here, the 'tags'
    are only character symbols used to generate proper AxisTag objects associated 
    with vigra arrays.
    
    Parameters:
    
    tags:   A sequence of single character axis tags (see vigranumpy documentation)
            
            Valid keys are: x, y, z, c, t
    
    dims:   A sequence of scalar integral values, or of single character axis tags, 
            or a mixture of both, representing the values of the size for each of the 
            axistags given in 'tags'. 
            
            When given as character, it indicates that the size of the axis with 
            the corresponding tag is taken from the size of the axis with that tag
            in pre-existing data (assuming that ore-esiting data contains an axis 
            with that tag).
            
            In addition, dims may contain at most one None element which 
            symbolizes that the size of the axis with the corresponding tag will 
            be calculated given the total number of samples in the data and the sizes
            of all the other axes.
            
            Valid values are: any integer > 0, x, y, z, c, t, and None
    
    Example:
    
    (1)
    
    axs = makeAxisSpec(('x','y','z','c'), (256,256,1,2))
    
    OrderedDict([('x', 256), ('y', 256), ('z', 1), ('c', 2)])
    
    (2) 
    
    axs = makeAxisSpec(('x','y','z','c'),('x','y','z',2))
    
    OrderedDict([('x', 'x'), ('y', 'y'), ('z', 'z'), ('c', 2)])
    
    here, the sizes of the 'x', 'y', and 'z' axes are taken from pre-existing data
    
    (3) assume one has loaded a vigra array from an image file
    
    data
    
    --> VigraArray(shape=(256, 1500, 2, 1), axistags=x y z c, dtype=float32, data=...)
    
    but the axistags are wrong; they should have been x y c z (i.e. the image is NOT 
    a stack of TWO FRAMES, but a single frame with TWO CHANNELS)
    
    
    axs = pio.makeAxisSpec(('x','y','z','c'),('x','y',1,2))
    
    generates
    
    OrderedDict([('x', 'x'), ('y', 'y'), ('z', 1), ('c', 2)])
    
    which can be applied to the data by calling 'applyAxisSpec(data, axs)'
    
    (4)
    
    vigra array is loaded from multi-image tiff file as a stack:
    
    stackdata
    -->VigraArray(shape=(256, 256, 172, 1), axistags=x y z c, dtype=float32, data=...)
    
    in fact, the data is a Z-stack with two channels; to correct this:
    
    axs = makeAxisSpec(('x','y','z','c'),('x','y',None,2))
    
    
    See also applyAxisSpec
    
    '''
    if len(tags) != len(dims):
        raise ValueError('Both tags and dims must  have same number of elements')
    
    ret = collections.OrderedDict(zip(tags, dims))
    
    return ret

def applyAxisSpec(data, axisspec):
    '''
    DEPRECATED
    Apply axis specification (see makeAxisSpec) to the vigra array in data.
    This may result in a reshape of data.
    
    Parameters:
    
    data:       vigra.VigraArray
    
    axisspecs:  collections.OrderedDict (see makeAxisSpec_old)
    
    Returns
    
    A reference to data (with new axistags and possibly a new shape)
    
    NOTE: 
    
    Both data and axisspecs are passed by reference, therefore capturing the return
    value is a variable is not needed (it will in fact be just another reference to data).
    
    If that is not what is intended, then pass a _DEEP_ copy of data to this function:
    
    applyAxisSpec(data.copy(), axisspec)
    
    As a side effect, the second argument ('axisspec') might also be modified 
    (see verifyAxisSpecs). Again, is that is not what was intended, also pass a _DEEP_
    copy of it:
    
    applyAxisSpec(data.copy(), axisspec.copy())
    
    See also makeAxisSpec
    
    '''
    if not isinstance(data, vigra.VigraArray):
        raise ValueError('data must be a vigra array')
    
    if not isinstance(axisspec, collections.OrderedDict):
        raise ValueError('axisspec must be a collections.OrderedDict')
    
    dataAxisspec = collections.OrderedDict(zip(data.axistags.keys(), data.shape))
    
    verifyAxisSpecs(axisspec, dataAxisspec)
                
    data.shape = axisspec.values()
    data.axistags = vigra.VigraArray.defaultAxistags(tagKeysAsString(axisspec))
    
    return data # 2016-03-15 14:01:08 for convenience

def defaultAxisTypeUnits(axisinfo):
    """Returns a default Quantity based on the axisinfo parameter.
    
    Positional parameters:
    ======================
    axisinfo: a vigra.AxisInfo object, a vigra.AxisType object or an valid integer
        resulted from bitwise OR between vigra.AxisType objects.
    
    Returns:
    ========
    
    A python quantity object (quantities.Quantity) that provides a reasonable
    default given the type flags in axisinfo
    
    For unknown axis types, returns pixel_unit
    
    """
    if isinstance(axisinfo, vigra.AxisInfo):
        if axisinfo.typeFlags == vigra.AxisType.Channels.numerator:
            return pq.dimensionless
        
        elif axisinfo.typeFlags == vigra.AxisType.Space.numerator:
            return pq.m
        
        elif axisinfo.typeFlags == vigra.AxisType.Angle.numerator:
            return pq.radian
        
        elif axisinfo.typeFlags == vigra.AxisType.Time.numerator:
            return pq.s
        
        elif axisinfo.typeFlags == vigra.AxisType.Frequency.numerator:
            return pq.Hz
        
        elif axisinfo.typeFlags == vigra.AxisType.Frequency | vigra.AxisType.Space:
            return space_frequency_unit
        
        elif axisinfo.typeFlags == vigra.AxisType.Frequency | vigra.AxisType.Time:
            return pq.Hz
        
        elif axisinfo.typeFlags == vigra.AxisType.Frequency | vigra.AxisType.Angle:
            return angle_frequency_unit
        
        elif axisinfo.typeFlags == vigra.AxisType.Edge.numerator:
            return pq.dimensionless
        
        elif axisinfo.typeFlags == vigra.AxisType.UnknownAxisType.numerator:
            return pixel_unit
        
        elif axisinfo.typeFlags == vigra.AxisType.NonChannel.numerator:
            return pixel_unit
        
        elif axisinfo.typeFlags == vigra.AxisType.AllAxes.numerator:
            return pixel_unit
        
        else:
            return pixel_unit
    
    elif isinstance(axisinfo, (vigra.AxisType, int)):
        if axisinfo == vigra.AxisType.Channels.numerator:
            return pq.dimensionless
        
        elif axisinfo == vigra.AxisType.Space.numerator:
            return pq.m
        
        elif axisinfo == vigra.AxisType.Angle.numerator:
            return pq.radian
        
        elif axisinfo == vigra.AxisType.Time.numerator:
            return pq.s
        
        elif axisinfo == vigra.AxisType.Frequency.numerator:
            return pq.Hz
        
        elif axisinfo == vigra.AxisType.Frequency | vigra.AxisType.Space:
            return space_frequency_unit
        
        elif axisinfo == vigra.AxisType.Frequency | vigra.AxisType.Time:
            return pq.Hz
        
        elif axisinfo == vigra.AxisType.Frequency | vigra.AxisType.Angle:
            return angle_frequency_unit
        
        elif axisinfo == vigra.AxisType.Edge.numerator:
            return pq.dimensionless
        
        elif axisinfo == vigra.AxisType.UnknownAxisType.numerator:
            return pixel_unit
        
        elif axisinfo == vigra.AxisType.NonChannel.numerator:
            return pixel_unit
        
        elif axisinfo == vigra.AxisType.AllAxes.numerator:
            return pixel_unit
        
        else:
            return pixel_unit
        
    else:
        raise TypeError("AxisInfo object expected; instead got a %s" % type(axisinfo).__name__)
    
def axisTypeFromString(s):
    """Inverse lookup of axis type flags from descriptive string or axis info key.
    Performs the reverse of defaultAxisTypeName and the reverse mapping of axisTypeFlags.
    """
    if s.lower() in ("channel", "channels", "c"):
        return vigra.AxisType.Channels
    
    elif s.lower() in ("width","height", "depth", "space", "spatial", "distance",  "x", "y", "z", "n"):
        return vigra.AxisType.Space
    
    elif s.lower() in ("angular range", "angular", "angle", "a"):
        return vigra.AxisType.Angle
    
    elif s.lower() in ("time", "temporal", "duration", "t"):
        return vigra.AxisType.Time
    
    elif s.lower() in ("frequency", "frequency range", "f"):
        return vigra.AxisType.Frequency
    
    elif s.lower() in ("spatial frequency range", "spatial frequency", "spatial sampling", "fx", "fy", "fz", "fn"):
        return vigra.AxisType.Frequency | vigra.AxisType.Space
    
    elif s.lower() in ("temporal frequency range", "temporal frequency", "temporal sampling", "ft"):
        return vigra.AxisType.Frequency | vigra.AxisType.Time
    
    elif s.lower() in ("angular frequency range", "angular frequency", "angular sampling", "fa"):
        return vigra.AxisType.Frequency | vigra.AxisType.Angle
    
    elif s.lower() in ("fe"):
        return vigra.AxisType.Frequency | vigra.AxisType.Edge
    
    elif s.lower() in ("edge", "e"):
        return vigra.AxisType.Edge
    
    elif s.lower() in ("unknownaxistype", "unknown axis type", "unknown type", "unknown", "size", "?"):
        return vigra.AxisType.UnknownAxisType
    
    elif s.lower() in ("nonchannel", "non channel", "s"):
        return vigra.AxisType.NonChannel
    
    elif s.lower() in ("allaxes", "all axes", "l"):
        return vigra.AxisType.AllAxes
    
    else:
        return vigra.AxisType.UnknownAxisType
    

def defaultAxisTypeName(axisinfo):
    """Generates a default string description for the vigra.AxisInfo parameter.
    
    Positional parameters:
    ======================
    
    axisinfo: a vigra.AxisInfo object, or a viga.AxisType object, or a valid integer
        resulted from bitwise OR between vigra.AxisType objects.
    
    Returns:
    ========
    
    A generic description of the type flags contained in axisinfo.
    
    If axisinfo is a vigra.AxisInfo object for a spatial axis, then the function
    uses the "key" symbol in the axisinfo to provide a more specific string 
    (e.g.,"Width", or "Height", for space axis with keys "x" or "y", respectively).
    
    Note that "n" stads for the nth space axis, meaning really anything in the 
    space domain. In this case the function will return "Space".
    
    """
    if isinstance(axisinfo, vigra.AxisInfo):
        if axisinfo.typeFlags == vigra.AxisType.Channels.numerator:
            return "Channels"
        
        elif axisinfo.typeFlags == vigra.AxisType.Space.numerator:
            if axisinfo.key == "x":
                return "Width"
            elif axisinfo.key == "y":
                return "Height"
            elif axisinfo.key == "z":
                return "Depth"
            else:
                return "Space"
            
        elif axisinfo.typeFlags == vigra.AxisType.Angle.numerator:
            return "Angular Range"
        
        elif axisinfo.typeFlags == vigra.AxisType.Time.numerator:
            return "Duration"
        
        elif axisinfo.typeFlags == vigra.AxisType.Frequency.numerator:
            return "Frequency Range"
        
        elif axisinfo.typeFlags == vigra.AxisType.Frequency | vigra.AxisType.Space:
            return "Spatial Frequency Range"
        
        elif axisinfo.typeFlags == vigra.AxisType.Frequency | vigra.AxisType.Time:
            return "Temporal Frequency Range"
        
        elif axisinfo.typeFlags == vigra.AxisType.Frequency | vigra.AxisType.Angle:
            return "Angular Frequency Range"
        
        elif axisinfo.typeFlags == vigra.AxisType.Edge.numerator:
            return "Edge"
        
        elif axisinfo.typeFlags == vigra.AxisType.UnknownAxisType.numerator:
            return "Unknown"
        
        elif axisinfo.typeFlags == vigra.AxisType.NonChannel.numerator:
            return "NonChannel"
        
        elif axisinfo.typeFlags == vigra.AxisType.AllAxes.numerator:
            return "AllAxes"
        
        else:
            return "Size"
        
    elif isinstance(axisinfo, vigra.AxisType):
        # NOTE: 2018-05-01 21:46:14
        # code below works even if axisinfo is an int!
        if axisinfo == vigra.AxisType.Channels.numerator:
            return "Channels"
        
        elif axisinfo == vigra.AxisType.Space.numerator:
            return "Space"
        
        elif axisinfo == vigra.AxisType.Angle.numerator:
            return "Angular Range"
        
        elif axisinfo == vigra.AxisType.Time.numerator:
            return "Duration"
        
        elif axisinfo == vigra.AxisType.Frequency.numerator:
            return "Frequency Range"
        
        elif axisinfo == vigra.AxisType.Frequency | vigra.AxisType.Space:
            return "Spatial Frequency Range"
        
        elif axisinfo == vigra.AxisType.Frequency | vigra.AxisType.Time:
            return "Temporal Frequency Range"
        
        elif axisinfo == vigra.AxisType.Frequency | vigra.AxisType.Angle:
            return "Angular Frequency Range"
        
        elif axisinfo == vigra.AxisType.Edge.numerator:
            return "Edge"
        
        elif axisinfo == vigra.AxisType.UnknownAxisType.numerator:
            return "Size"
        
        elif axisinfo == vigra.AxisType.NonChannel.numerator:
            return "Size"
        
        elif axisinfo == vigra.AxisType.AllAxes.numerator:
            return "Size"
        
        else:
            return "Size"
        
        
    else:
        raise TypeError("vigra.AxisInfo or vigra.AxisType object expected; instead got a %s" % type(axisinfo).__name__)
        
    
def defaultAxisTypeSymbol(axisinfo):
    """Maps vigra.AxisInfo object to a default string symbol (or "key").
    
    Positional parameters:
    ======================
    
    axisinfo: a vigra.AxisInfo object.
    
    Returns:
    ========
    
    A string key corresponding to the type flags in axisinfo object (in upper case).
    """
    if not isinstance(axisinfo, vigra.AxisInfo):
        raise TypeError("AxisInfo object expected; instead got a %s" % type(axisinfo).__name__)

    if axisinfo.typeFlags == vigra.AxisType.Channels.numerator:
        return "C"
    
    elif axisinfo.typeFlags == vigra.AxisType.Space.numerator:
        if axisinfo.key == "x":
            return "X"
        
        elif axisinfo.key == "y":
            return "Y"
        
        elif axisinfo.key == "z":
            return "Z"
        
        else:
            return "S"
        
    elif axisinfo.typeFlags == vigra.AxisType.Angle.numerator:
        return "A"
    
    elif axisinfo.typeFlags == vigra.AxisType.Time.numerator:
        return "T"
    
    elif axisinfo.typeFlags == vigra.AxisType.Frequency.numerator:
        return "F"
    
    elif axisinfo.typeFlags == vigra.AxisType.Frequency | vigra.AxisType.Space:
        return "SF"
    
    elif axisinfo.typeFlags == vigra.AxisType.Frequency | vigra.AxisType.Time:
        return "TF"
    
    elif axisinfo.typeFlags == vigra.AxisType.Frequency | vigra.AxisType.Angle:
        return "AF"
    
    elif axisinfo.typeFlags == vigra.AxisType.Edge.numerator:
        return "E"
    
    elif axisinfo.typeFlags == vigra.AxisType.UnknownAxisType.numerator:
        return "?"
    
    elif axisinfo.typeFlags == vigra.AxisType.NonChannel.numerator:
        return "?"
    
    elif axisinfo.typeFlags == vigra.AxisType.AllAxes.numerator:
        return "?"
    
    else:
        return "?"
    
def hasNameString(s):
    return AxisCalibration.hasNameString(s)
    
def axisChannelName(axisinfo, channel):
    """
    Parameters:
    ===========
    axisinfo: vigra.AxisInfo object
    
    channel: int >=0 (0-based index of the channel)
    """
    return AxisCalibration(axisinfo).getChannelName(channel)

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
    return AxisCalibration(axisinfo).axisName
    
def isCalibrated(axisinfo):
    """Syntactic shorthand for hasCalibrationString(axisinfo.description).
    
    NOTE: Parameter checking is implicit
    
    """
    return AxisCalibration.isAxisCalibrated(axisinfo)

def calibration(axisinfo, asTuple=True):
    """Returns the calibration triplet (units, origin, resolution) of an axis.
    
    The tuple is obtained by parsing the calibration string contained in the
    description attribute of axisinfo, where axisinfo is a vigra.AxisInfo object.
    
    If axis is uncalibrated, the function returns (dimensionless, 0.0, 1.0) when
    axis is a channel axis or (pixel_unit, 0.0, 1.0) otherwise.
    
    NOTE: Parameter checking is implicit
    
    """
    result = AxisCalibration(axisinfo)
    
    if asTuple:
        return result.calibrationTuple()
    
    else:
        return result
    
def resolution(axisinfo):
    return AxisCalibration(axisinfo).resolution

def hasCalibrationString(s):
    """Simple test for what MAY look like a calibration string.
    Does nothing more than saving some typing; in particular it DOES NOT verify
    that the calibration string is conformant.
    
    NOTE: Parameter checking is implicit
    
    """
    return AxisCalibration.hasCalibrationString(s)

def removeCalibrationData(axInfo):
    return AxisCalibration.removeCalibrationData(axInfo)

def removeCalibrationFromString(s):
    """Returns a copy of the string with any calibration substrings removed.
    Convenience function to clean up AxisInfo description strings.
    
    NOTE: Parameter checking is implicit
    
    """
    
    return AxisCalibration.removeCalibrationFromString(s)
    
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
    
    axcal = AxisCalibration(units = units, origin = origin, resolution = resolution,
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
    return AxisCalibration.parseDescriptionString(s)

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
    
    axcal: AxisCalibration object
    
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
            
        axcal = AxisCalibration(units = c_[0], origin = c_[1], resolution = c_[2],
                                key = axInfo.key, axisname = defaultAxisTypeName(axInfo),
                                channel = channel, channelname=channelname)
            
    elif isinstance(cal, pq.Quantity):
        c_ = [cal.units, 0.0, resolution]
        
        axcal = AxisCalibration(units = c_[0], origin = c_[1], resolution = c_[2],
                                key = axInfo.key, axisname = defaultAxisTypeName(axInfo),
                                channel = channel, channelname=channelname)
            
    elif isinstance(cal, str):
        axcal = AxisCalibration(axisinfo=cal, channel=channel, channelname=channelname) # will raise ValueError if cal not conformant
        
    else:
        raise TypeError("Unexpected type (%s) for calibration argument." % type(cal).__name__)
        
    
    axcal.calibrateAxis(axInfo)
        
    return axInfo, axcal

def hasChannelAxis(data):
    if isinstance(data, vigra.VigraArray):
        return data.axistags.channelIndex < data.ndim
    
    elif isinstance(data, vigra.AxisTags):
        return data.channelIndex < len(data)
    
    else:
        raise TypeError("Expected a VigraArray or AxisTags object; instead, I've got a %s" % type(data).__name__)
    
def dimIter(data, key):
    """Generates an interator along the dimension of the given axis key.
    
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
        
def _getTypeFlag_(value):
    """Needed because there is faulty translation of AxisType data structure between python & C++
    """
    if not isinstance(value, int):
        raise TypeError("Expecting an int")
    
    if value == vigra.AxisType.Channels.numerator:
        return vigra.AxisType.Channels
    
    elif value == vigra.AxisType.Space.numerator:
        return vigra.AxisType.Space
    
    elif value == vigra.AxisType.Angle.numerator:
        return vigra.AxisType.Angle
    
    elif value == vigra.AxisType.Time.numerator:
        return vigra.AxisType.Time
    
    elif value == vigra.AxisType.Frequency.numerator:
        return vigra.AxisType.Frequency
    
    elif value == vigra.AxisType.Frequency | vigra.AxisType.Space:
        return vigra.AxisType.Frequency | vigra.AxisType.Space
    
    elif value == vigra.AxisType.Frequency | vigra.AxisType.Time:
        return vigra.AxisType.Frequency | vigra.AxisType.Time
    
    elif value == vigra.AxisType.Frequency | vigra.AxisType.Angle:
        return vigra.AxisType.Frequency | vigra.AxisType.Angle
    
    elif value == vigra.AxisType.Edge.numerator:
        return vigra.AxisType.Edge
    
    elif value == vigra.AxisType.UnknownAxisType.numerator:
        return vigra.AxisType.UnknownAxisType
    
    elif value == vigra.AxisType.NonChannel.numerator:
        return vigra.AxisType.NonChannel
    
    elif value == vigra.AxisType.AllAxes.numerator:
        return vigra.AxisType.AllAxes
    
    else:
        return vigra.AxisType.UnknownAxisType
        
