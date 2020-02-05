# -*- coding: utf-8 -*-
'''
utilities to enhance axis and axistags handling
2016-11-11 05:27:34 NOTE: code should be moved to datatypes
'''

#TODO: find a way to merge AxisSpecs class with datatypes.ScanData.axisquantities
#TODO: which is a collections.OrderedDict.
#TODO: One possibility is to re-define this class as being a mapping from axis 
#TODO: tag character (the key) to a tuple (n_samples, quantity), where quantity 
#TODO: is None for a non-calibrated axis

# 2016-12-11 00:34:19 change to mapping from tag character (the key) to AxisCalibration (the value)

#### BEGIN core python modules
from __future__ import print_function
#### END core python modules

#### BEGIN 3rd party modules
#import numpy as np
#import vigra
#import quantities as pq
#import signalviewer as sv
#import javabridge
#import bioformats
#### END 3rd party modules

#### BEGIN pict.core modules
from . import datatypes
#### END pict.core modules

#__allowed_axis_tag_keys__ = 'xyzct'

# DEPRECATED

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
            if isinstance(tags, datatypes.vigra.VigraArray):
                dims = tags.shape
                mytags = tags.axistags.keys()
            elif isinstance(tags, datatypes.collections.OrderedDict):
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
                if type(k1) is not str or k1 not in datatypes.__allowed_axis_tag_keys__:
                    raise ValueError('Incorrect axis tag key. Acceptable keys are %s' % datatypes.__allowed_axis_tag_keys__)
                
            # check dims
            
            for v in dims:
                if type(v) is str:
                    if not v in datatypes.__allowed_axis_tag_keys__:
                        raise ValueError('Axis size specification "%s" is not allowed. Allowed values are %s' % (v, datatypes.__allowed_axis_tag_keys__))
                    else:
                        pass
                elif v is None or type(v) is int:
                    pass
                else:
                    raise TypeError('Unexpected value type (%s) in second argument' % type(v))
                
            testNone = datatypes.np.where(datatypes.np.equal(dims, None))[0]
            
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
            if type(k) is not str or k not in datatypes.__allowed_axis_tag_keys__:
                raise ValueError('Incorrect axis tag key. Acceptable keys are %s' % datatypes.__allowed_axis_tag_keys__)
            
        for k in dims:
            if type(v) is str:
                if not v in datatypes.__allowed_axis_tag_keys__:
                    raise ValueError('Axis size specification "%s" is not allowed. Allowed values are %s' % (v, datatypes.__allowed_axis_tag_keys__))
                else:
                    pass
            elif v is None or type(v) is int:
                pass
            else:
                raise TypeError('Unexpected value type (%s) in second argument' % type(v))
            
        testNone = datatypes.np.where(datatypes.np.equal(dims, None))[0]
        
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

