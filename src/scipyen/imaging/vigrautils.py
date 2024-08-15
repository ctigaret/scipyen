# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import typing
import collections.abc
from functools import singledispatch
from core.vigra_patches import vigra
import numpy as np
import quantities as pq
from .axiscalibration import (AxesCalibration, 
                              AxisCalibrationData,
                              ChannelCalibrationData,)
from imaging import axisutils
from imaging.axisutils import STANDARD_AXIS_TAGS_KEYS
from traitlets import Bunch

def imageIndexTuple(img, slicing=None, newAxis=None, newAxisDim=None):
    """Idiom for introducing a new axis in an image.
    
    Returns a tuple useful for indexing a VigraArray taking into account a new
    axis when given.
    
    Positional parameters:
    =====================
    img: a VigraArray object
    
    Named parameters:
    =================
    slicing: None (default), or a dictionary that maps keys (int, str, or 
                vigra.AxisInfo objects) to any one of a: 
                1) slice object over the axis coordinates to be included
                2) range object (will be converted to slice objects)
                3) integer (will be converted to slice objects)
                
                When not None, slicing is used to specify subregions
                of the exising axes in img that are to be included in the
                indexing object
                
                When slicing is None, the indexing object contains slice 
                objects corresponding to the full extent of the image axes
                
    newAxis: None (default), a str, or a vigra.AxisInfo object
    newAxisDim: None (default) or an int
    
    Returns:
    ========
    The indexing object: a list containing slice objects and if needed,
        an Ellipsis object and/or a new singleton axis providing an 
        AxisInfo object (see vigra.newaxis() for details).
        
        The slice objects cover the full extent of the existing axis in
        in the image "img", or the subregions specified in "slicing".
        
    The indexing object can be used directly to access data in the img.
        
    """
    if not isinstance(img, vigra.VigraArray):
        raise TypeError("First parameter expected to be a vigra array; got %s instead" % type(img).__name__)
    
    # default indexing object
    indexobj = [slice(img.shape[k]) for k in range(img.ndim)]
    
    if isinstance(slicing, dict):
        for k in slicing.keys():
            if not isinstance(k, (int, str, vigra.AxisInfo)):
                raise TypeError("slicing keys expected to be an int, str or vigra.AxisInfo object; got %s instead" % type(k).__name__)
                
            if isinstance(k, int):
                if k < 0 or k >= img.ndim:
                    raise ValueError("Illegal axis index %d; legal values are in the interval [0, %d)" % (k, img.ndim))
                
                if isinstance(slicing[k], range):
                    slc = slice(slicing[k].start, slicing[k].stop, slicing[k].step)
                    
                elif isinstance(slicing[k], int):
                    slc = slice(slicing[k])
                    
                elif isinstance(slicing[k], slice):
                    slc = slicing[k]
                    
                elif slicing[k] is None:
                    slc = slice(0,img.shape[k])
                    
                else:
                    raise TypeError("Expecting a slice object, or a range object, or an int, at index %d; got %s" % (k, type(slicing[k]).__name__))
                
                indexobj[k] = slc
                
            elif isinstance(k, str):
                if k not in img.axistags:
                    raise ValueError("Axis %s not found in the image" % k)
                
                ndx = img.axistags.index(k)
                
                if isinstance(slicing[k], range):
                    slc = slice(slicing[k].start, slicing[k].stop, slicing[k].step)
                    
                elif isinstance(slicing[k], int):
                    slc = slice(slicing[k])
                    
                elif isinstance(slicing[k], slice):
                    slc = slicing[k]
                    
                elif slicing[k] is None:
                    slc = slice(0,img.shape[ndx])
                    
                else:
                    raise TypeError("Expecting a slice object, or a range object, or an int, or None, at index %s; got %s" % (k, type(slicing[k]).__name__))
            
                indexobj[ndx] = slc
                
            elif isinstance(k, vigra.AxisInfo):
                if k.key not in img.axistags:
                    raise ValueError("AxisInfo with key %s not found in the image" % k.key)
                
                ndx = img.axistags.index(k.key)
                
                if isinstance(slicing[k], range):
                    slc = slice(slicing[k].start, slicing[k].stop, slicing[k].step)
                    
                elif isinstance(slicing[k], int):
                    slc = slice(slicing[k])
                    
                elif isinstance(slicing[k], slice):
                    slc = slicing[k]
                    
                elif slicing[k] is None:
                    slc = slice(0,img.shape[ndx])
                    
                else:
                    raise TypeError("Expecting a slice object, or a range object, or an int, at index %d; got %s" % (k, type(slicing[k]).__name__))
                
                indexobj[ndx] = slc
        
    elif slicing is not None:
        raise TypeError("slicing expected to be None or a dict; got %s instead" % type(slicing).__name__)
        
    
    if newAxis is None:
        return tuple(indexobj)
        
    else:
        if img.ndim == 5:
            raise ValueError("The image already has the maximum allowed number of dimensions (5); cannot add a new axis to it")
        
        if isinstance(newAxis, str):
            newAxis = vigra.AxisInfo(key=newAxis, 
                                     typeFlags=vigra.AxisType(axisTypeFromString(newAxis)),
                                     resolution=1.0,
                                     description=axisTypeName(newAxis))
            
        elif not isinstance(newAxis, vigra.AxisInfo):
            raise TypeError("newAxis parameter expected to be a vigra.AxisInfo object, or a vigra.AxisInfo key string, or None")
        
        if newAxis.isChannel() and img.axistags.channelIndex < img.ndim:
            raise ValueError("The image already has a channel axis; cannot add another one")
            
        if newAxisDim is None:
            if slicing is None:
                indexobj = [type(Ellipsis)(), vigra.newaxis(newAxis)]
                
            else:
                indexobj.append(vigra.newaxis(newAxis))
            
        elif isinstance(newAxisDim, int):
            if newAxisDim > img.ndim:
                raise ValueError("The new axis dimension cannot be larger than %d" % img.ndim)
            
            elif newAxisDim < 0:
                raise ValueError("The new axis dimension cannot be negative")
            
            elif newAxisDim == img.ndim:
                if slicing is None:
                    indexobj = [type(Ellipsis)(), vigra.newaxis(newAxis)]
                    
                else:
                    indexobj.append(vigra.newaxis(newAxis))
                
            elif newAxisDim == 0:
                if slicing is None:
                    indexobj = [vigra.newaxis(newAxis), type(Ellipsis)()]
                    
                else:
                    indexobj.insert(0, vigra.newaxis(newAxis))
                
            else:
                # indexobj has already been defined and its contents adjusted
                # according to slicing
                indexobj.insert(newAxisDim, vigra.newaxis(newAxis))
                
        else:
            raise TypeError("newAxisDim expected to be an int or None; got %s instead" % type(newAxisDim).__name__)
                
    return tuple(indexobj)
            
def insertAxis(img, axinfo, axdim):
    """Inserts an axis specified by axinfo, at dimension axdim, in image img.
    
    Returns a reference to img with a new axis inserted.
    
    """
    
    if not isinstance(img, vigra.VigraArray):
        raise TypeError("Expecting 'img' as a VigraArray; got %s instead" % type(img).__name__)
    
    if isinstance(axinfo, str):
        axinfo = vigra.AxisInfo(key=axinfo, 
                                typeFlags = vigra.AxisType(axisTypeFromString(axinfo)), 
                                resolution = 1.0, 
                                description = axisTypeName(axinfo))
        
    elif not isinstance(axinfo, vigra.AxisInfo):
        raise TypeError("Expecting 'axinfo' as an AxisInfo object or a str; got %s instead" % type(axinfo).__name__)
    
    if not isinstance(axdim, int):
        raise TypeError("Expecting 'axdim' as an int; got %s instead" & type(axdim).__name__)
    
    if axdim < 0 or axdim > img.ndim:
        raise ValueError("Illegal 'axdim' value (%d); expected to be in the closed interval [0, %d]" % (axdim, img.ndim))
    
    # avoid insertion of an extra channel axis
    if axinfo.isChannel() and img.channelIndex < img.ndim:
        raise ValueError("Image already has a channel axis")
    
    indexobj = imageIndexTuple(img, newAxis = axinfo, newAxisDim = axdim)
    
    return img[indexobj]
    
def padAxis(img, axis, pad_before, pad_after, value=None):
    """Pads an image along the specified axis by adding pixels at the beginning and at the end.
    
    Parameters:
    ===========
    
    img:    vigra.VigraArray
    
    axis:   int (valid axis index in the axistags property of img),  or
            vigra.AxisInfo object (must be present in img.axistags), or
            a str (a valid AxisInfo key tring, present in img.axistags)
            
    pad_before: int (number of samples to insert at the beginning of the axis)
    
    pad_after: int (number of samples to append to the axis)
    
    value: float (including np.nan) or None (in which case a number of samples
        equal to pad_before and pad_after will be prepended and appended, 
        respectively, to the axis, with values taken from the img without mirroring)
    
    
    
    """
    if not isinstance(img, vigra.VigraArray):
        raise TypeError("Expecting first parameter a VigraArray; got %s instead" % type(img).__name__)
    
    if isinstance(axis, int):
        if axis < 0 or axis >= img.ndim:
            raise ValueError("Axis index must be in the semi-open interval [0, %d)" % (img.ndim))
        
        axisindex = axis
        axisinfo = img.axistags[axisindex]
        
    elif isinstance(axis, str):
        if axis not in img.axistags:
            raise ValueError("axis %s not found in the image" % axis)
        
        axisindex = img.axistags.index(axis)
        axisinfo = img.axistags[axis]
        
    elif isinstance(axis, vigra.AxisInfo):
        if axis.key not in img.axistags:
            raise ValueError("axis %s not found in the image" % axis.key)
        
        axisindex = img.axistags.index(axis.key)
        axisinfo = axis
        
    if not isinstance(pad_before, int):
        raise TypeError("pad_before expected to be an int; git %s instead" % type(pad_before).__name__)
    
    if pad_before < 0:
        raise ValueError("pad_before must be >= 0; got %d instead" % pad_before)
        
    if not isinstance(pad_after, int):
        raise TypeError("pad_after expected to be an int; git %s instead" % type(pad_after).__name__)
    
    if pad_after < 0:
        raise ValueError("pad_after must be >= 0; got %d instead" % pad_after)
        
    new_shape = [s for s in img.shape]
    
    new_shape[axisindex] = new_shape[axisindex] + pad_before + pad_after
    
    src_index = [slice(k) for k in img.shape]
    
    dest_index = [slice(k) for k in new_shape]
    
    dest_index[axisindex] = slice(pad_before, pad_before + img.shape[axisindex])
    
    if isinstance(value, float):
        result = vigra.VigraArray(new_shape, axistags = img.axistags, init=True, value=value)
        
        result[tuple(dest_index)] = img[tuple(src_index)]
        
    elif value is None:
        result = vigra.VigraArray(new_shape, axistags = img.axistags, init=True, value=0.0)
        
        pre_index = [slice(k) for k in img.shape]
        pre_index[axisindex] = slice(pad_before)
        
        post_index = [slice(k) for k in img_shape]
        post_index[axisindex] = slice(img_shape[k]-pad_after, img_shape[k])
        
        dest_pre_index = [slice(k) for k in new_shape]
        dest_pre_index[axisindex] = slice(pad_before)
        
        dest_post_index = [slice(k) for k in new_shape]
        dest_post_index[axisinidex] = slice(new_shape[k]-pad_after, new_shape[k])
        
        result[tuple(dest_index)] = img[tuple(src_index)]
        
        result[tuple(dest_pre_index)]  = img[tuple(pre_index)]
        result[tuple(dest_post_index)] = img[tuple(post_index)]
        
        
    else:
        raise TypeError("value expected to be a float or None; gpt %s instead" % type(value).__name__)
    
    return result
        
def padToLargest(array0, array1, pad=0.0):
    """Brings the two arrays to a common shape, by padding with pad value.
    The shape is set to the larger of the array sizes in each dimension.
    
    Pads either array along its non-channel axes to bring them to the same shape.
    
    The new shape will be the maximum of the axes size across the two arrays.
    
    Positional parameters:
    ======================
    array0: vigra.VigraArray = the (first) array to re-shape
    array1: vigra.VigraArray = the (second) array to re-shape
    
        
        Both arrays must have identical numbers of dimensions. 
        When array1 is a sequence, it must reflect the shape of a (virtual)
        array with the same number of dimensions as array0
    
    
    Keyword parameters:
    =====================
    pad: float = the value used for padding (default is 0.0)
    
    Returns:
    ========
    When array0 and array1 are both VigraArray arrays, returns
    two arrays reshaped to the largest size along each dimension.
    
    Whe only array0 is a VigraArray, returns one array reshaped to the largest
    size between array0 shape and the corresponding value in array1.
    
    In both cases, reshaping is done through padding with pad value.
    
    If any of the arrays does not need to be reshaped, its original will be returned.
    
    
    """
    from core.axiscalibration import AxesCalibration

    if any([not isinstance(a, vigra.VigraArray) for a in (array0, array1)]):
        raise TypeError("Expecting two VigraArray objects; got %s  and %s instead" % (type(array0).__name__, type(array1).__name__))
    
    shape0 = [s for s in array0.shape]
    
    if array1.ndim != array0.ndim:
        raise ValueError("Both arrays must have the same number of dimensions; instead they have %d and %d" % (array0.ndim, array1.ndim))
    
    newshape = list()
    newtags = list()

    shape1 = [s for s in array1.shape]
    
    # verify that both arrays have identical axistags associated with the same 
    # dimensions: the axistags in the array with fewer dimensions must all be
    # found at the corresponding place in the other array's axistags.
    # NOTE: also check axis resolutions
    if array0.ndim > array1.ndim:
        for k, ax in enumerate(array1.axistags):
            if ax not in array0.axistags or array0.axistags.index(ax.key) != k:
                raise ValueError("AxisInfo %s of array1 is either absent from array0 or it is not at the same dimension (%d) in both arrays" % (ax.key, k))
            
            res0 = AxesCalibration(array0.axistags[k]).resolution
            res1 = AxesCalibration(array1.axistags[k]).resolution
            
            if res0 != res1:
                raise ValueError("%Axis %s at dimension %k has different resolutions in the arrays: %s vs %s.\n Resample first." % (ax.key, k, res0, res1))
            
            newtags.append(ax)
            
            newshape.append(max([shape0[k], shape1[k]]))
                
        for k in range(len(array1.axistags),len(array0.axistags)):
            ax = array0.axistags[k]
            
            newtags.append(ax)
        
            newshape.append(array0.shape[k])
            shape1.append(array0.shape[k])
                
    else:
        for k, ax in enumerate(array0.axistags):
            if ax not in array1.axistags or array1.axistags.index(ax.key) != k:
                raise ValueError("AxisInfo %s of array0 is either absent from array1 or it is not at the same dimension (%d) in both arrays" % (ax.key, k))
            
            res0 = AxesCalibration(array0.axistags[k]).resolution
            res1 = AxesCalibration(array1.axistags[k]).resolution
            
            if res0 != res1:
                raise ValueError("Axis %s at dimension %d has different resolutions in the arrays: %s vs %s.\n Resample first." % (ax.key, k, res0, res1))
            
            newtags.append(ax)
            
            newshape.append(max([shape0[k], shape1[k]]))
                
        for k in range(len(array0.axistags), len(array1.axistags)):
            ax = array1.axistags[k]
            
            newtags.append(ax)
        
            newshape.append(array1.shape[k])
            shape0.append(array1.shape[k])
            
    if any([s != newshape[k] for k, s in enumerate(shape0)]):
        shape = [newshape[k] for k in range(len(newshape))]
        
        axslices = list()
        for k, s in enumerate(array0.shape):
            axslices.append(slice(s))
        
        ret0 = vigra.VigraArray(shape, value = pad, axistags = vigra.AxisTags(*newtags))
        ret0[axslices] = array0
            
    else:
        ret0 = array0
            
    if any([s != newshape[k] for k, s in enumerate(shape1)]):
        shape = [newshape[k] for k in range(len(newshape))]
        
        axslices = list()
        for s in array1.shape:
            axslices.append(slice(s))
        
        ret1 = vigra.VigraArray(shape, value = pad, axistags = vigra.AxisTags(*newtags))
        ret1[axslices] = array1
            
    else:
        ret1 = array1
            
    return ret0, ret1
                
def slicingSequence(array, slicing):
    """Utility function that returns a sequence of slice objects for indexing into
    a VigraArray object.
    DEPRECATED: code now included in imageIndexTuple()
    
    Positional parameters:
    ======================
    array: vigra.VigraArray
    
    slicing: dict that maps keys (int, str, vigra.AxisInfo object) to any of:
                 
                 1) slice objects defining the axis coordinates to be kept.
                 
                 2) range objects (will be converted to slice objects)
                 
                 3) integers (will be converted to slice objects)
    
    """
    if not isinstance(array, vigra.VigraArray):
        raise TypeError("First argument expected to be a VigraArray; got %s instead" % type(array).__name__)
    
    if not isinstance(slicing, dict):
        raise TypeError("Second argument expected to be a dict; got %s instead" % type(slicing).__name__)
    
    # set up default slice list; this will return the entire array
    slices = [slice(s) for s in array.shape]
    
    for k in slicing.keys():
        if not isinstance(k, (int, str, vigra.AxisInfo)):
            raise TypeError("slicing keys expected to be an int, str or vigra.AxisInfo object; got %s instead" % type(k).__name__)
        
        if isinstance(k, int):
            if k < 0 or k >= array.ndim:
                raise ValueError("Illegal axis index %d; legal values are in the interval [0, %d)" % (k, array.ndim))
            
            if isinstance(slicing[k], range):
                slc = slice(slicing[k].start, slicing[k].stop, slicing[k].step)
                
            elif isinstance(slicing[k], int):
                slc = slice(slicing[k])
                
            elif isinstance(slicing[k], slice):
                slc = slicing[k]
                
            else:
                raise TypeError("Expecting a slice object, or a range object, or an int, at index %d; got %s" % (k, type(slicing[k]).__name__))
            
            slices[k] = slc
            
        elif isinstance(k, str):
            if k not in array.axistags:
                raise ValueError("Axis %s not found in the array" % k)
            
            ndx = array.axistags.index(k)
            
            if isinstance(slicing[k], range):
                slc = slice(slicing[k].start, slicing[k].stop, slicing[k].step)
                
            elif isinstance(slicing[k], int):
                slc = slice(slicing[k])
                
            elif isinstance(slicing[k], slice):
                slc = slicing[k]
                
            else:
                raise TypeError("Expecting a slice object, or a range object, or an int, at index %d; got %s" % (k, type(slicing[k]).__name__))
            
            slices[ndx] = slc
            
        elif isinstance(k, vigra.AxisInfo):
            if k.key not in array.axistags:
                raise ValueError("AxisInfo with key %s not found in the array" % k.key)
            
            ndx = array.axistags.index(k.key)
            
            if isinstance(slicing[k], range):
                slc = slice(slicing[k].start, slicing[k].stop, slicing[k].step)
                
            elif isinstance(slicing[k], int):
                slc = slice(slicing[k])
                
            elif isinstance(slicing[k], slice):
                slc = slicing[k]
                
            else:
                raise TypeError("Expecting a slice object, or a range object, or an int, at index %d; got %s" % (k, type(slicing[k]).__name__))
            
            slices[ndx] = slc
            
    return slices
        
def croppedView(array, axes_slices):
    """
    Returns a view of the array cropped according to axes_slices.
    
    Positional parameters:
    ======================
    array: VigraArray = array to be cropped
    
    axes_slices: dict that maps keys (int, str, vigra.AxisInfo object) to either
                 slice objects, range objects, or int, defining the axis coordinates 
                 to be kept (see imageIndexTuple() for details).
                 
                 or:
                 
                 sequence with as many slice objects as there are axes in the 
                 array (axes are taken in the given order);
                 
                 In both cases, the slices operate on indices within the given 
                 axes (i.e., the axes coordinates are in uncalibrated units).
    """
    
    if not isinstance(array, vigra.VigraArray):
        raise TypeError("First argument expected to be a VigraArray; got %s instead" % type(array).__name__)
    
    if not isinstance(axes_slices, (dict, tuple, list)):
        raise TypeError("Second argument expected to be a dict, a tuple, or a list; got %s instead" % type(axes_slices).__name__)
    
    if isinstance(axes_slices, (tuple, list)):
        if len(axes_slices) != array.ndim:
            raise ValueError("Length of axes_slices sequence (%d) is different from the array's dimensions (%d)" % (len(axes_slices), array.ndim))
        
        if all([isinstance(s, slice) for s in axes_slices]):
            slices = axes_slices
            
        elif all([isinstance(s, int) for s in axes_slices]):
            slices = [slice(s) for s in axes_slices]
        
    else:
        slices = imageIndexTuple(array, slicing=axes_slices)
            
    return array[slices]

def padToShape(array, shape, pad = np.nan, keep_axis=None):
    """Pads array axes such that its shape is the largest
    of array.shape and shape.
    
    FIXME: allow padding with replication
    
    Padding occurs at the end of the conflicting axis or axes.
    
    Positional parameters:
    ======================
    array: vigra.VigraArray = the (first) array to re-shape
    shape: sequence = the shape of a (virtual) second array with the same number
            of dimensions as array (len(shape) == array.ndim)
    
    Named parameters
    ================
    pad = value for padding (float or np.nan; default is 0.0)
    
    keep_axis: int or None (default) index of preserved axis
    
        When an int, no padding is applied to the axis with the given index, 
        which must be in the half-open interval [0, array.ndim)
    
    """
    if not isinstance(array, vigra.VigraArray):
        raise TypeError("padToShape: array was expected to be a VigraArray; got %s instead" % type(array).__name__)
    
    if not isinstance(shape, (tuple, list)) or any([not isinstance(a, int) for a in shape]):
        raise TypeError("padToShape: shape must be a sequence of int elements")
        #raise TypeError("shape must be a sequence of int elements; got %s instead" % str(shape))
    
    if len(shape) != array.ndim:
        raise ValueError("padToShape: When a sequence, array1 must correspond to %d dimensions; instead it has %d elements" % (array0.ndim, len(array1)))
    
    if isinstance(keep_axis, int):
        if keep_axis < 0 or keep_axis >= array.ndim:
            raise ValueError("Illegal keep_axis parameter: %d; should be between 0 and %d" % (keep_axis, array.ndim-1))
        
    elif keep_axis is not None:
        raise TypeError("keep_axis parameter extecpedt to be an int or None; got %s instead" % type(keep_axis).__name__)
    
    newshape = [max(s) for s in zip(array.shape, shape)]
    
    shape_diff = [s[0]-s[1] for s in zip(array.shape, shape)]
    
    if keep_axis is not None:
        newshape[keep_axis] = array.shape[keep_axis]
    
    #print("padToShape newshape", newshape)

    if any([s != array.shape[k] for k, s in enumerate(newshape)]):
        axslices = list()
        
        for s in array.shape:
            axslices.append(slice(s))
            
        if value is None:
            append_slices = list()
            
            for s in array.shape:
                append_slice.append(slice(d))
            
            ret = vigra.VigraArray(newshape, value = 0.0, axistags = vigra.AxisTags(*array.axistags))
            
            
            
        elif isinstance(value, float):
            ret = vigra.VigraArray(newshape, value = pad, axistags = vigra.AxisTags(*array.axistags))
        
        #print("axslices", axslices)
            
        ret[axslices] = array
    
        return ret
    
    else:
        return array
    
def resampleImage(target, src, axis=None, window=None):
    """Resamples target such that the axes' resolutions match those of the src.
    # TODO give user to force up-sampling from image with lower resolution to
    # image with higher resolution and vice-versa
    
    Does nothing if axes resolutions are identical.
    
    Positional parameters:
    ======================
    
    target: vigra.VigraArray to be resampled
    
    src: vigra.VigraArray whose axes' resolution is to be matched by target after resampling
    
    Named parameters:
    =================
    
    axis: None (default), or:
        (1) a vigra.AxisInfo from the target, or:
        (2) a str (vigra.AxisInfo key), or:
        (3) an int (axis index, 0-based), or:
        
        a sequence (tuple or list) of containing any of (1)-(3) types above
            
        When None, resampling will occur along all the non-channel axes in target
            with resolution different thatn that of the corresponding axes in src.
        
        When an AxisInfo object, the source (src) must also have an AxisInfo with
        identical typeFlags and key.
        
        The resampled axis can also be specified as a valid axis info key string,
        or the index of the axis in src.
        
        When a tuple, target will be resampled along the specified axes, if necessary.
        
        In either case, the specified axis must exist and be at the same index in 
        both src and target.
        
        NOTE: Channel axes are NOT supported
        
        NOTE: The value of the axis resolution is that contained in the calibration
        string embedded in the AxisInfo description attribute. Although AxisInfo
        objects also have their own resolution attribute, this is IGNORED here
        because the resolution attribute of the AxisInfo is only a float, not 
        a Python Quantity, and because it is possible that setting a calibration
        string in the AxisInfo description does not guarantee an update of the 
        AxisInfo's own resolution attribute.
        
        If the axis has no calibration information in its description attribute, 
        the default values are assumed (units: pixel_unit, resolution= 1 * pixel_unit)
        with pixel_units being a Python UnitQuantity defined in the datatypes module
        in the pict package.
    
    """
    from core.axiscalibration import AxesCalibration

    src_axes = list()
    tgt_axes = list()
    
    if not isinstance(src, vigra.VigraArray):
        raise TypeError("First argument expected to be a vigra.VigraArray; got %s instead" % type(src).__name__)
    
    if not isinstance(target, vigra.VigraArray):
        raise TypeError("Second argument expected to be a vigra.VigraArray; got %s instead" % type(target)._name__)
    
    src_axis_cals = AxesCalibration(src)
    tgt_axis_cals = AxesCalibration(target)
        
    if isinstance(axis, str):
        if axis not in src.axistags or axis not in target.axistags:
            raise ValueError("Neither images have an axis info with %s tag (or 'key')" % axis)
        
        if target.axistags.index(axis) != src.axistags.index(axis):
            raise RuntimeError("Axis %s is not associated with the same dimension in both arrays (%d in target and %d in src)" % (axis, target.axistags.index(axis), src.axistags.index(axis)))
        
        if target.axistags[axis].isChannel():
            raise RuntimeError("Resampling channel axes is not supported")
        
        if src_axis_cals.getDimensionlessResolution(src.axistags[axis]) != tgt_axis_cals.getDimensionlessResolution(target.axistags[axis]):
            src_axes.append(src.axistags[axis])
            tgt_axes.append(target.axistags[axis])
        
    elif isinstance(axis, vigra.AxisInfo):
        if axis not in src.axistags or axis not in target.axistags:
            raise ValueError("Specified axis (%s) must be present in both source and target image" % axis.key)
        
        if target.axistags.index(axis.key) != src.axistags.index(axis.key):
            raise RuntimeError("Axis %s is not at the same index in both images dimensions (%d in target and %d in src)" % axis.key, target.axistags.index(axis.key), src.axistags.index(axis.key))
        
        if target.axistags[axis.key].isChannel():
            raise RuntimeError("Resampling channel axes is not supported")
        
        if src_axis_cals.getDimensionlessResolution(axis) != tgt_axis_cals.getDimensionlessResolution(axis):
            src_axes.append(src.axistags[axis.key])
            tgt_axes.append(target.axistags[axis.key])
        
    elif isinstance(axis, int):
        if axis < 0:
            raise ValueError("A negative axis index was specified: %d" % axis)
        
        if axis >= src.ndim or axis >= target.ndim:
            raise ValueError("Specified axis index (%d) is outside the dimensions of the images (%d and %d)" % (axis, src.ndim, target.ndim))
        
        if target.axistags[axis].isChannel():
            raise RuntimeError("Resampling channel axes is not supported")
        
        if src_axis_cals.getDimensionlessResolution(src.axistags[axis].key) != tgt_axis_cals.getDimensionlessResolution(target.axistags[axis].key):
            src_axes.append(src.axistags[axis])
            tgt_axes.append(target.axistags[axis])
        
    elif isinstance(axis, (tuple, list)):
        for k, a in enumerate(axis):
            if isinstance(a, int):
                if a < 0 or a >= src.ndim or a >= target.ndim:
                    raise ValueError("Element %d in axis parameter specifies an illegal axis index (%d)" % (k, a))
                
                if target.axistags[a].isChannel():
                    raise RuntimeError("Resampling channel axes is not supported")
                    
                if src_axis_cals.getDimensionlessResolution(src.axistags[a].key) != tgt_axis_cals.getDimensionlessResolution(target.axistags[a].key):
                    src_axes.append(src.axistags[a])
                    tgt_axes.appenf(target.axistags[a])
                
            elif isinstance(a, str):
                if a not in src.axistags or a not in target.axistags:
                    raise ValueError("Element %d in axis parameter specifies an axis that does not exist in both arrays (%s)" % (k, a))
                
                if target.axistags.index(a) != src.axistags.index(a):
                    raise RuntimeError("Axis %s specified by element %d in axis parameter is not associated with the same dimension in both arrays: : %d in target and %d in source" % (a, k, target.axistags.index(a), src.axistags.index(a)))
                
                if target.axistags[a].isChannel():
                    raise RuntimeError("Resampling channel axes is not supported")
                
                if src_axis_cals.getDimensionlessResolution(a) != tgt_axis_cals.getDimensionlessResolution(a):
                    src_axes.append(src.axistags[a])
                    tgt_axes.append(target.axistags[a])
                
            elif isinstance(a, vigra.AxisInfo):
                if a not in target.axistags or a not in src.axistags:
                    raise ValueError("Element %d in axis parameter specifies an axis that does not exist in both arrays (%s)" % (k, a.key))
                
                if target.axistags.index(a.key) != src.axistags.index(a.key):
                    raise RuntimeError("Axis %s specified by element %d in axis parameters is not associated with the same dimension in both arrays: %d in target and %d in source" % (a.key, k, target.axistags.index(a.key), src.axistags.index(a.key)))
                
                if target.axistags[a.key].isChannel():
                    raise RuntimeError("Resampling channel axes is not supported")
                
                if src_axis_cals.getDimensionlessResolution(a.key) != tgt_axis_cals.getDimensionlessResolution(a.key):
                    src_axes.append(src.axistags[a.key])
                    tgt_axes.append(target.axistags[a.key])
                    
            else:
                raise TypeError("Element %d in axis parameters expected to be an int, str, or vigra.AxisInfo objects; got %s instead" % type(a).__name__)
                
    elif axis is None:
        # check and if needed resample all axes
        for ax in target.axistags:
            if not ax.isChannel():
                if tgt_axis_cals.getDimensionlessResolution(ax.key) != src_axis_cals.getDimensionlessResolution(ax.key):
                    tgt_axes.append(ax)
                    src_axes.append(src.axistags[ax.key])
            
            
    else:
        raise TypeError("Third argument expected to be a str (vigra,AxisInfo key), an int (axis index in axistags attribute), a vigra.AxisInfo object, a sequence containing any of these, or None; got %s instead" % type(axis).__name__)
    
    if len(tgt_axes) == 0:
        ret = target
        
    else:
        for k, ax in enumerate(tgt_axes):
            new_res = src_axis_cals.getDimensionlessResolution(src_axes[k].key)
            #print("%d: %s, new_res: %s; old_res: %s" % (k, ax.key, new_res, AxesCalibration(ax).resolution) )
            
            if k == 0:
                ret = resampleImageAxis(target, new_res, axis=ax, window=window)
                
            else:
                ret = resampleImageAxis(ret, new_res, axis=ax, window=window)

    return ret
    
def resampleImageAxis(image, new_res, axis=0, p=1000, window=None):
    """Resamples image along the specified axis, using scipy.signal.resample_poly
    
    Parameters:
    ==========
    
    image: vigra.VigraArray
    
    new_res: float scalar (dimensionless) or a Python Quantity: the new sampling 
            PERIOD
        
            When a Python Quantity, it must have the same units as in the axis's 
            calibration tuple (see datatypes.calibration() function).
            
            CAUTION: by default, uncalibrated axes are considered to have a sampling
                period ("resolution") of 1, dimensionless
            
    axis: int (default 0) or a vigra.AxisInfo object, or a str with a valid AxisInfo tag
    
        If an int, it must satisfy
            axis >= 0 and axis < image.ndim
            
        If an AxisInfo object or a tag str, it must exist in the image axistags
        
        If any of these condition are not satisfied, the function will raise ValueError.
    
    p = factor of precision (default 1000): power of 10 used to calculate up/down sampling:
        up = new_res * p / signal_sampling_rate
        down = p
        
    window = window function (see scipy.signal.get_window())
    
    """
    
    from scipy.signal import resample_poly as resample
    from scipy.signal import get_window as get_window
    from core.axiscalibration import AxesCalibration
    
    if not isinstance(image, vigra.VigraArray):
        raise TypeError("Expecting a vigra.VigraArray as first parameter; got %s instead" % type(image).__name__)
    
    if isinstance(axis, int):
        if axis < 0 or axis >= image.ndim:
            raise ValueError("Invalid axis specified (%d) for an image with %d dimensions" % (axis, image.ndim))
        
        axisinfo = image.axistags[axis]
        axisindex  = axis
        
    elif isinstance(axis, str):
        if axis not in image.axistags:
            raise ValueError("axis %s not found in image" % axis)
        
        axisinfo = image.axistags[axis]
        axisindex  = image.axistags.index(axis)

    elif isinstance(axis, vigra.AxisInfo):
        if axis not in image.axistags:
            raise ValueError("axis %s not found in image" % axis)
        
        axisinfo = axis
        axisindex  = image.axistags.index(axisinfo.key)
        
    else:
        raise TypeError("axis must be specified as an int or as a vigra.AxisInfo object; got %s instead" % type(axis).__name__)
    
    if axisinfo.isChannel():
        raise TypeError("Cannot resample a channel axis")
    
    image_cal = AxesCalibration(image)
    
    if image_cal[axisinfo].units == pq.dimensionless:
        warnings.warn("Resampling along a dimensionless axis")
        
    if image_cal[axisinfo].resolution == 1:
        warnings.warn("Resampling an axis with original resolution of %s" % image_cal[axisinfo].resolution)
        
    elif image_cal[axisinfo].resolution == 0:
        raise ValueError("Cannot resample an axis with zero resolution")
    
    #if image_cal.getUnits(axisinfo) == pq.dimensionless:
        #warnings.warn("Resampling along a dimensionless axis")
        
    #if image_cal.getDimensionlessResolution(axisinfo) == 1:
        #warnings.warn("Resampling an axis with original resolution of %s" % image_cal.getDimensionlessResolution(axisinfo) )
        
    #elif image_cal.getDimensionlessResolution(axisinfo) == 0:
        #raise ValueError("Cannot resample an axis with zero resolution")
    
    if isinstance(new_res, pq.Quantity):
        if new_res.size !=  1:
            raise TypeError("Expecting new_res a scalar; got a shaped array %s" % new_res)
        
        if new_res.units != image_cal[axisinfo].units:
            raise TypeError("New resolution has incompatible units with this axis calibration %s" % cal)
        
        new_res = new_res.magnitude
        
    #if isinstance(new_res, pq.Quantity):
        #if new_res.size !=  1:
            #raise TypeError("Expecting new_res a scalar; got a shaped array %s" % new_res)
        
        #if new_res.units != image_cal.getUnits(axisinfo):
            #raise TypeError("New resolution has incompatible units with this axis calibration %s" % cal)
        
        #new_res = new_res.magnitude
        
    elif not isinstance(new_res, numbers.Real):
        raise TypeError("Expecting new_res a scalar float or Python Quantity; got %s instead" % type(new_res).__name__)
    
    if new_res < 0:
        raise ValueError("New sampling rate (%s) must be strictly positive !" % new_res)
    
    if new_res > image_cal[axisinfo].resolution:
        dn = int(new_res/image_cal[axisinfo].resolution * p)
        up = p
        
    elif new_res < image_cal[axisinfo].resolution:
        up = int(image_cal[axisinfo].resolution/new_res * p)
        dn = p
        
    else:
        return image
    
    #if new_res > image_cal.getDimensionlessResolution(axisinfo):
        #dn = int(new_res/image_cal.getDimensionlessResolution(axisinfo) * p)
        #up = p
        
    #elif new_res < image_cal.getDimensionlessResolution(axisinfo):
        #up = int(image_cal.getDimensionlessResolution(axisinfo)/new_res * p)
        #dn = p
        
    #else:
        #return image
    
    #up = int(cal[2]/new_res * p)
    
    if window is None:
        window = ("kaiser", 0.5)
    
    ret = vigra.VigraArray(resample(image, up, dn, axis=axisindex, window = window), axistags=image.axistags)
    
    units = image_cal[axisinfo].units
    origin = image_cal[axisinfo].origin
    resolution = new_res
    
    image_cal[axisinfo].resolution = new_res
    
    #newCal = AxesCalibration(ret.axistags[axisindex],
                                #units = units, origin = origin, resolution = resolution, 
                                #axisname = dt.axisTypeName(ret.axistags[axisindex]),
                                #axistype = ret.axistags[axisindex].typeFlags)
    
    image_cal[axisinfo].calibrateAxis(axisinfo)
    
    #dt.calibrateAxis(ret.axistags[axisindex], (cal[0], cal[1], new_res))
    
    return ret

def concatenateImages(*images, **kwargs):
    """Concatenates a sequence of images along a specified axis.
    Wraps np.concatenate and assigns axistags to the result, if given.
    
    If specified, a new axis can also be added to the arrays.
    
    See "What this function does", below.
    
    Var-positional parameters:
    ==========================

    *images :   vigra.VigraArrays, or an iterable of vigra.VigraArrays 
                (to emulate the numpy.concatenate syntax)
        
                If there is only ONE VigraArray specified, it will be returned 
                unchanged, or with a new axis added (see below).
                
                Images must have identical number of dimensions and identical
                AxisInfo objects in their axistags properties, that is
                AxisInfo objects must have identical AxisType and calibration
                (including resolution) for the corresponding axes.
                
                In addition, images must have identical shapes except along the
                concatenation axis.
                

    Named parameters:
    ================

    axis    :   the concatenation axis, specified in one of the following ways:
                
        int = index of an existing axis (default is 0)
                
        str = a valid AxisInfo key for an existing axis, or for a new axis to be 
            added to all images at the next higher dimension
                
        AxisInfo object for an existing axis, or for a new axis to be added to 
        the images on their next higher dimension.
        
    ignore: None (default) a string ("units", "origin" or "resolution") or 
        a sequence of any of these strings (e.g. ["units", "origin", "resolution"]) 
        denoting parameters to ignore from the calibration of concatenation axis
        (see AxesCalibration.isclose() for details)
        
    Returns:
    ========
    
    A VigraArray produced by concatenating the images
    
    NOTE: 2018-07-31 23:47:17
    Inserting a new axis in a lower dimension can be performed by first inserting
    the axis in the images to be concatenated at the appropriate dimension, before
    calling this function. 
    
    This and other (possibly "fanciful") concatenations are really problem-dependent
    and thus beyond the scope of this function


What this function does:
========================

Concatenates VigraArray data; uses numpy.concatenate(...) behind the 
scenes.

Arrays are concatenated in two ways, explained here by examples:

    (1) SIMPLE CONCATENATIONS - 
    
    concatenates arrays along an existing axis
    
    Example 1: along the x axis: concatenation axis preexists
    
    prerequisites:
    
    all([img.ndim == images[0].ndim for img in images[1:]])
    
    all([img.axistags == images[0].axistags for img in images[1:]])
    
         __           __     __       __ __ __
        |  |         |  |   |  |     |  |  |  |
        |  |       + |  | + |  |  => |  |  |  | 
        |__|         |__|   |__|     |__|__|__|

    
    
    Example 2: along the y axis: concatenation axis preexists
    
    prerequisites - as above
                                      __
                                     |  |
                                     |  |
         __           __     __      |__|
        |  |         |  |   |  |     |  |
        |  |       + |  | + |  |  => |  |
        |__|         |__|   |__|     |__|
                                     |  |
                                     |  |
                                     |__|
    
    NOTE for Example 1 & 2: a new axis can always be specified, and it would be
    added to the result even if it was not used in the concatenation.
    
    Example 3: along a new axis: concatenation axis does not exist;
    
    prerequisites - as above, plus:
    
    concatenation axis must be specified as an AxisInfo object that does not 
    already exist in the image arrays being concatenated
        
         __           __     __       __ 
        |  |         |  |   |  |     |  |_
        |  |       + |  | + |  |  => |  | |_ 
        |__|         |__|   |__|     |__| | |
                                       |__| |
                                         |__|
    
    """
    #from .axiscalibration import AxesCalibration

    catAxis = 0
    
    ignore = None
    
    #asPictArray = False # set up below
    
    if len(kwargs) > 0:
        catAxis     = kwargs.pop("axis",     0)
        ignore      = kwargs.pop("ignore", None)
        
    # 1) check the "images" parameter:
    
    if len(images) == 1: # this is OK
        # trivial case of only one image; 
        # no concatenation made, but one can add a new axis
        
        # NOTE: 2018-09-07 14:31:26
        # VigraArray or PictArray?
        # if ALL are of the same type, then return that type
        # otherwise, is they are of mixed type then cast to PictArray
        # and return a PictArray
        #
        # what to return for a single image is then trivial
        #
        # however, for a sequence of images, NOTE that PictArray inherits from 
        # VigraArray hence:
        # isinstance(some_pict_array, vigra.VigraArray) is True
        #
        # therefore probe for PictArray first, then for VigraArray, in the case
        # of an image sequence
        #
        # also NOTE that if isinstance(data, datatypes.PictArray) is True then
        # isinstance(data, vigra.VigraArray) is also True
        #
        
        if isinstance(images[0], vigra.VigraArray):
            # there is only one image; nothing to concatenate here
            # just return a reference to images[0] image
            return images[0]
        
        elif isinstance(images[0],(tuple, list)):
            if not all([isinstance(i, vigra.VigraArray) for i in images[0]]):
                raise TypeError("Expecting a sequence of vigra arrays")
            
            images = images[0]
            
        else:
            raise TypeError("Expecting a vigra array, or a sequence of vigra arrays")
            
    # NOTE: 2017-10-21 00:05:12
    # by now, images should be a sequence of VigraArrays
    
    #print(images)
    
    # check image dimensions
    image_dims = [img.ndim for img in images]
    
    min_dims = min(image_dims)
    
    max_dims = max(image_dims)
    
    if max_dims != min_dims:
        raise ValueError("Cannot concatenate images with different dimensionalities")
    
    #axes_cals    = AxesCalibration(images[0])
    
    first_shape = images[0].shape

    # NOTE: 2018-09-05 22:47:20
    # figure out the identity of the concatenation axis:
    #
    # NOTE: a vigra.AxisInfo may be present in two different images; it DOES NOT
    # encapsulate the axis itself (equality test used for inclusion in an axistags
    # object does not probe the description property of the AxisInfo; by implication
    # it is oblivious to any calibration string contained therein)
    #
    # NOTE: in the first case (catAxis given as an int) the value must be valid
    # i.e. less than ndim
    #
    # To concatenate along an as yet unexisting  axis, use case (2) or (3)
    #   
    if isinstance(catAxis, int):
        # catAxis given as int (index into first image's axistags) =>
        # set this to catAxisNdx then set catAxis to be the axisinfo of the first image
        # with the index given by catAxis in first image axistags
        if catAxis < 0 or catAxis >= min_dims:
            raise ValueError("concatenation axis index must take values in the semi-open interval [0, %d); got %d instead" % (min_dims, catAxisNdx))
        
        catAxisNdx = catAxis
        
        if catAxisNdx < min_dims:
            catAxis = images[0].axistags[catAxisNdx]
            
    elif isinstance(catAxis, str):
        # catAxis given as a string (axis info key) => 
        # figure out which axis it points to use that as catAxis and set catAxisNdx 
        # to its index in the axistags of the first image
        if catAxis not in images[0].axistags:
            # create a new axis then add it to each of the images
            
            catAxisNdx = min_dims
            
            newaxis = vigra.AxisInfo(key = catAxis, 
                                     typeFlags = vigra.AxisType(axisTypeFromString(catAxis)),
                                     resolution=1.0,
                                     description = axisTypeName(catAxis))
            
            new_images = [insertAxis(img, newaxis, catAxisNdx) for img in images]
                
            catAxis = newaxis
                
            images = new_images
            
        else:
            catAxisNdx = images[0].axistags.index(catAxis)
            catAxis = images[0].axistags[catAxisNdx]
        
    elif isinstance(catAxis, vigra.AxisInfo):
        # catAxis given as vigra.AxisInfo object =>
        # set catAxisNdx to its index in first image's axistags
        if catAxis not in images[0].axistags:
            catAxisNdx = min_dims
            new_images = [insertAxis(img, catAxis, catAxisNdx) for img in images]
            
            images = new_images
            
        else:
            catAxisNdx = images[0].axistags.index(catAxis.key)
        
    else:
        raise TypeError("concatenation axis must be specified as an int, a str or a vigra.AxisInfo object; got %s instead" % type(catAxis).__name__)
        
    axistags    = images[0].axistags
    axcal       = AxesCalibration(images[0])
        
    # NOTE: 2018-09-05 23:32:14
    # check axistags, axis calibrations and array shapes
    # we allow for mismatches only for the concatenation axis, including ignoring
    # some or all of its calibration parameters (units, origin, resolution)
    for img in images[1:]:
        if img.axistags != axistags:
            raise ValueError("Cannot concatenate images with different AxisInfo objects")
        
        img_axcal = AxesCalibration(img)
        #print("img_axcal", img_axcal)
        #print("axistags", axistags)
        for key in img_axcal.keys():
            #print("key", key)
            if axistags[key] == catAxis:
                if not axcal[key].isclose(img_axcal[key], ignore=ignore):
                    if ignore is None:
                        raise RuntimeError("Cannot concatenate along the axis %s which has non-matching calibration across images" % key)
                    
                    else:
                        raise RuntimeError("Cannot concatenate along the axis %s which has non-matching calibration across images, ignoring %s" % (key, str(ignore)))
                
            else:
                if not axcal[key].isclose(img_axcal[key]):
                    print(f"axcal[{key}] {axcal[key]}")
                    print(f"img_axcal[{key}] {img_axcal[key]}")
                    raise RuntimeError("Cannot concatenate images with non-matching calibration for axis %s" % key)
                
        if not all(first_shape[s] == img.shape[s] for s in range(min_dims) if s != catAxisNdx):
            raise RuntimeError("Images must have identical shapes except along the concatenation axis")
            
    result = vigra.VigraArray(np.concatenate(images, axis=catAxisNdx), axistags = axistags)
    
    return result
    
    
def removeSlice(img, axis, ndx):
    """Removes a slice with index ndx, on the specified axis of image img
    """
    
    if not isinstance(img, vigra.VigraArray):
        raise TypeError("Expecting a vigra.VigraArray; got %s instead" % type(img).__name__)
    
    if isinstance(axis, vigra.AxisInfo):
        if axis not in img.axistags:
            raise ValueError("AxisInfo %s is not associated with this image" % axis.key)
        
        axinfo = axis
        axindex = img.axistags.index(axis.key)
        
    elif isinstance(axis, str):
        if axis not in img.axistags:
            raise ValueError("AxisInfo %s is not associated with this image" % axis)
        
        axinfo = img.axistags[axis]
        axindex = img.axistags.index(axis)
        
    elif isinstance(axis, int):
        if axis not in range(img.ndim):
            raise ValueError("Wring axis index (%d); expecting a value between 0 and %d" % (axis, img.ndim-1))
        
        axinfo = img.axistags[axis]
        axindex = axis
        
    else:
        raise TypeError("'axis' parameter expected to be a vigra.AxisInfo object or an int; got %s instead" % type(axis).__name__)
    
    if not isinstance(ndx, int):
        raise TypeError("'ndx' parameter expected to be an int; got %s instead" % type(ndx).__name__)
    
    if ndx < 0 or ndx >= img.shape[axindex]:
        raise ValueError("invalid 'ndx' parameter (%d); expecting a value between 0 and %d" % (ndx, img.shape[axindex]-1))
        
    slices_ndx = [slice(x) for x in img.shape]
    
    slices_ndx[axindex] = [x for x in range(*slice(ndx).indices(img.shape[axindex]))] + \
                          [x for x in range(*slice(ndx+1, img.shape[axindex]).indices(img.shape[axindex]))]
                      
    ret = img[tuple(slices_ndx)]
    
    ret.axistags = img.axistags
    
    return ret

def proposeLayout(img:vigra.VigraArray, 
                   userFrameAxis:typing.Optional[typing.Union[str, vigra.AxisInfo, int, 
                                                              typing.Sequence[typing.Union[str, vigra.AxisInfo, int]]]]=None,
                   timeVertical:bool = True,
                   indices:bool=False,
                   ) -> typing.Tuple[int, typing.Optional[typing.Union[vigra.AxisInfo, typing.List[vigra.AxisInfo]]], vigra.AxisInfo, vigra.AxisInfo, vigra.AxisInfo]:
    """Proposes a layout for frame-by-frame display and analysis of a VigraArray.
    
    Based on user-specified hints, suggests which array axes may be used:
        * to slice the array into meaningful 2D array views (data 'frames')
        * for the definition of a frame's width and height
        
    and proposes the number of frames in the array (array size along the 'frames'
    axis).
        
    Parameters:
    ===========
    img: N-dimensional VigraArray
    
    userFrameAxis: str, int, AxisInfo, or tuple/list of any of these
        This hints the possible axis or set of axes that may be used for slicing
        the array into meaningful 2D views ('frames')
        
    timeVertical: bool, optional, default is True
        When True, the time dimension (when present) is to be shown vertically
        
    indice:bool, optional, default is False
        When True, returns the index of the axes for the 'horizontal', 'vertical'
        and 'frames'.
        
        By default (False) the function returns vigra.AxisInfo objects for the
        above.
        
        WARNING: AxisInfo obejcts are NOT serializable; if the layout
        returned by this function is meant to be serialized (pikcled), or used 
        in an object intended to be serialized (pickled), then set:
        
        `indices=True` 
    
    Returns:
    ========
    A traitlets.Bunch with the following key/value pairs:
     
    nFrames:int -> the number of frames along the proposed "frame" axis
    
    All the others are vigra.AxisInfo objects, None, or tuple of vigra.AxisInfo
     
    horizontal:vigra.AxisInfo or int = the axis (or axis index) proposed
        for the frame 'width'.
    
        BY CONVENTION this is the first non-channel axis (usually, the 1st array
        dimension), which is also the innermost non-channel axis given by 
        img.innerNonChannelIndex property
        
    vertical:vigra.AxisInfo or int = the axis (or axis index) proposed
        for the frame 'height'.
    
    BY CONVENTION this is the 2nd non-channel axis (usually, the 2nd dimension)
        
    channels:vigra.AxisInfo or None, or int: as above, for the 'channels' 
        axis.
    
        The 'channels' axis is either the AxisInfo with type flags of 
        Channels, when it exists in img 'axistags' property, or None. When 
        returned as an int, the value equals the number of dimension in the array
        if there is no Channel axis.
        
        BY CONVENTION this is the axis of the highest dimension of the array 
        (possibly absent in 2D arrays, and missing in 1D arrays, where the data
        inherently represents a single 'channel').
        
        In VigraArray objects, the channel axis represents channels in a 'color'
        space (RGB, Luv, etc.) for the so-called 'multi-channel' or 'multi-band'
        images - this relates to the data type of the pixels. 
        
        NOTE 1: In Scipyen, a 'channel' can also represent a distinct recording
        channel of data from the same source (e.g. a fluorescence channel, DIC, 
        etc.), or the real or imaginary part of complex numbers (e.g., the
        result of a Fourier transform).
        
        BY CONVENTION, a single data recording channel is interpreted as being
        stored in a 'grayscale' image (a.k.a, a 'single-channel' or 'single-band'
        image or volume). 
        
        In Scipyen, data containing several 'data channels' defined as above 
        is stored in a sequence of grayscale VigraArray with the same shape and 
        similar axis tags. For display purposes, there is nothing to prevent 
        'merging' these channels into a single VigraArray, although it does not 
        always make good sense to do so (especially whenn there are more than
        four distinct data channels).
        
    frames: vigra.AxisInfo, None, tuple of AxisInfo or tuple of int
    
        When given, this is the AxisInfo along which the array can be 'sliced'
        in 'frames' defined for the purpose of display and/or analysis.
        
        BY CONVENTION for 3D arrays this is the 3rd non-channel axis (usually, 
        the 3rd dimension); for arrays with more than 4 dimensions and without a
        channels axis this is a tuple of axes (in increasing order).
        
     
    NOTE 2: the last two values need not be along the first and second axis, as 
    this depends on which axis is the channel axis (if it exists); by default, 
    in the VIGRA library the channel axis is typically on the outermost (highest)
    dimension, but that depends on the internal storage order for the pixel data
    in the array (a.k.a the VIGRA array's 'order' property).
    
    NOTE 3: Here 'width' and 'height' are loosely defined in relation to how
    image data should be displayed, and does not necessarily imply the 
    existence of a space domain for the data.
    
    For example, in an image containing a series of linescans, the horizontal
    axis usually corresponds to the space domain (a line scan'sweep') whereas 
    the vertical axis corresponds to sequence of successive linescan sweeps 
    (hence, the time domain). In this case, 'width' is defined in the spatial 
    domain, and 'height' is defined in the temporal domain (and therefore it
    would be more appropriately called 'duration'). Notwithstanding, I adopt the 
    more colloquial term 'height' to convey the meaning of a 'vertical' axis on 
    a 2D display.
    
    The semantics depends on the value of 'timeVertical' parameter which enables
    the display of the time domain vertically or horizontally, on a 2D display. 
    In the latter case, the 'horizontal' axis represents time (hence colloquially,
    the duration is 'width') whereas the 'vertical' axis represents space 
    (a.k.a 'height').
        
    NOTE 4: For a series of line scan sweeps acquired with a laser scanning 
    system, each sweep actually contains pixel data defined BOTH in space AND 
    time (the laser spot cannot illuminate several places at the same time!). 
    
    However, the duration of a single sweep (or line) is usually several orders
    of magnitude smaller than the duration of the entire sequence of lines
    (e.g., acquiring at 1000 lines/s  makes the duration of a single line scan
    roughly 1000 x smaller, taking into account the laser flyback time and the 
    settling time for the galvos at the end of the sweep).
    
    Furthermore, a single line scan sweep usually covers a wider (linear)
    region of the field of view, such that the measurement of the time-varying
    fluorescence signal of interest is restricted to one or several sub-regions
    of the line scan trajectory, corresponding to the structures of interest
    (e.g., spines on a dendrite).
    
    This means that the laser dwell time on these structures of interest is even
    smaller than the duration of the entire line scan sweep.
    
    For this reasons, the analysis of time-varying fluorescence (e.g. Ca2+
    transients) usually assumes that the pixel data in a single line scan sweep 
    through the structure of interest has been acquired instantaneously. This
    assumption allows the collapsing of the pixel intensities in a linescan
    sequence along its spatial dimension, to yield a 1D signal where each data 
    point is the collapsed fluorescence data acquired during a single line
    scan through the structure. The derived 1D signals are then analyzed
    taking the line frequency as the sampling frequency of the signal.
    
    This approach is generally acceptable for time-varying fluorescence 
    signals with time constants orders of magnitude longer than the laser 
    dwell time on the structure of interest.
    
    The assumption above breaks down when laser dwell time on the structure
    is significantly increased (e.g. to allow more photons to be collected). 
    In this case collapsing the pixel intensity data along the spatial domain
    may result in undersampling the signal in the time domain. Therefore one 
    may consider analysing the data recorded from the structure on a 
    pixel-by-pixel basis, in both space and time domains. The decision depends
    really on how close the laser dwell time on the structure is to the time 
    constant of the signal representing the underlying physical measure 
    (e.g., a change in Ca2+ concentration), and on the rate constants of the 
    fluorescence indicator itself.
    
    NOTE 5: A traitlets.Bunch is a dictionary taking str keys, which accepts
    attribute access to its members:
    
    The expression `bunch.item` has the same effect as the expression 
    `bunch["item"]` and both return the value mapped to 'item' in the bunch.
    

    Code logic:
    ==========
    
    A "frame" is a 2D slice view of a VigraArray. Arrays can be sliced along 
    any axis, including a channel axis. This function attempts to "guess"
    a reasonable axis along which the array can be sliced into meaningful 2D 
    frames.
    
    """
    if not isinstance(img, vigra.VigraArray):
        raise TypeError("Expecting a VigraArray; got %s instead" % (type(img).__name__))
    
    if not hasattr(img, "axistags"):
        raise TypeError("'img' does not contain axis information")
    
    if img.ndim == 0:
        raise TypeError("Expecting a VigraArray with at least 1 dimension")
    
    #bring userFrameAxis to a common denominator: an AxisInfo object, or None
    # this helps with checking if it is a Channel axis or not
    if isinstance(userFrameAxis, (vigra.AxisInfo, str)):
        if userFrameAxis not in img.axistags:
            # CAUTION equality testing for AxisInfo objects ONLY takes into
            # account the axis typeFlags and key
            raise ValueError("Axis %s not found in image" % userFrameAxis.key)
        
        if isinstance(userFrameAxis, str):
            userFrameAxis = img.axistags[userFrameAxis]
            
        if userFrameAxis.typeFlags & vigra.AxisType.Channels:
            raise TypeError("Channels axes cannot be used as frame axes")
        
    elif isinstance(userFrameAxis, int):
        if userFrameAxis < 0 or userFrameAxis >= img.ndim:
            raise ValueError("Axis index expected to be in the semi-open interval [0 .. %d); got %d instead" % (img.ndim, userFrameAxis))
        
        userFrameAxis = img.axistags[userFrameAxis]
        
        if userFrameAxis.typeFlags & vigra.AxisType.Channels:
            raise TypeError("Channels axes cannot be used as frame axes")
        
    elif isinstance(userFrameAxis, (tuple, list)):
        if all([isinstance(ax, (vigra.AxisInfo, str, int)) for ax in userFrameAxis]):
            try:
                frax = tuple(img.axistags[ax] if isinstance(ax, str, int) else ax for ax in userFrameAxis)
                
            except Exception as e:
                raise RuntimeError("Invalid frame axis specified") from e
                
            userFrameAxis = frax
            
        else:
            raise TypeError("user frame axis sequence expected to contain vigra.AxisInfo objects, str or int elements")
        
        if any (ax.typeFlags & vigra.AxisType.Channels for ax in userFrameAxis):
            raise TypeError("Channels axes cannot be used as frame axes")
        
    elif userFrameAxis is not None:
        #warnings.warn("Invalid user frame axes specification; will set it to None", RuntimeWarning)
        userFrameAxis = None
        
    xIndex = img.axistags.index("x")
    if xIndex == img.ndim:
        # try by axis typeflags
        spaceAxes = tuple(ax for ax in img.axistags if ax.typeflags & vigra.AxisType.Space)
    yIndex = img.axistags.index("y")
    zIndex = img.axistags.index("z")
    tIndex = img.axistags.index("t")
    cIndex = img.channelIndex
    
    # NOTE: 2021-12-02 10:20:07
    # It is easier (semantically, also) to work below with AxisInfo objects.
    # When indices is True, there will be additional function calls to
    # axistags.index() before returning, but I suppose the penalty is small ...
    frameAxisInfo       = None
    channelAxisInfo     = None
    horizontalAxisInfo  = None
    verticalAxisInfo    = None
    nFrames             = 0
    
    if img.ndim == 1:
        nFrames = 1

        if img.order == "C":
            verticalAxisInfo = img.axistags[0] # 'column' vector
            
        elif img.order  ==  "F":
            horizontalAxisInfo = img.axistags[0] # 'row' vector
            
        else: # "V"
            horizontalAxisInfo = img.axistags[0] # 'row' vector
        
    elif img.ndim == 2: # trivial case; the check above passed means that there is no channel axis
        # this has a 'virtual', singleton channel axis;
        #if userFrameAxis is not None:
            #warnings.warn("Ignoring userFrameAxis for a 2D array", RuntimeWarning)

        # NOTE: the interpretation of the axes is is dependent on the img 'order'
        # attribute; we use the axistags 'x' and 'y' or 't' to determine the 
        # horizontal ('x') and vertical ('y' or 't') dimensions; when neither of 
        # thesee axistags exist (their index equals img.ndim) we fallback on the 
        # generic heuristic of horizontal on 1st dimension and vertical on 2nd
        # 
        nFrames = 1
        
        horizontalAxisInfo  = img.axistags["x"] if xIndex < img.ndim else \
                              imt.axistags["t"] if tIndex < img.ndim and timeVertical is False else img.axistags[0]
        
        verticalAxisInfo    = img.axistags["y"] if yIndex < img.ndim else \
                              img.axistags["t"] if tIndex < img.ndim and timeVertical is True else img.axistags[1]
        
        
    elif img.ndim == 3:
        if cIndex == img.ndim: # no channel axis:
            if userFrameAxis is None:
                # first try AxisInfo with key "z", or a third AxisInfo with typeFlags & Space,
                # then AxisInfo with key "t", or an axisInfo with typeFlags & Time
                if zIndex < img.ndim:
                    frameAxisInfo = img.axistags[zIndex]
                    
                else:
                    spaceAxes = [ax for ax in img.axistags if ax.typeFlags & Space]
                    if len(spaceAxes) > 2:
                        frameAxisInfo = spaceAxes[2] 
                        
                    else:
                        if tIndex < img.ndim:
                            frameAxisInfo = img.axistags[tIndex]
                            
                        else:
                            frameAxisInfo = img.axistags[-1] # fall back to choosing the outermost axis as frame axis
                    
            else: # user-specified frameAxis - just check we're OK with it
                if isinstance(userFrameAxis, (list, tuple)):
                    if len(userFrameAxis) == 0:
                        raise TypeError("userFrameAxis sequence is empty")
                    
                    if any([not isinstance(ax, vigra.AxisInfo) for ax in userFrameAxis]):
                        raise TypeError("user frame axis sequence must contain only vigra.AxisInfo objects")
                    
                    frameAxisInfo = userFrameAxis[0]
                    
                elif not isinstance(userFrameAxis, vigra.AxisInfo):
                    raise TypeError("user frame axis must be either None, a vigra.AxisInfo, or a sequence of AxisInfo objects; got %s instead" % type(userFrameAxis).__name__)

                    frameAxisInfo = userFrameAxis
                
            # skip frame axis for width and height
            availableAxes = tuple(ax for ax in img.axistags if ax != frameAxisInfo and ax.typeFlags & vigra.AxisType.Channels == 0)
            
            horizontalAxisInfo  = img.axistags["x"] if xIndex < img.ndim and img.axistags["x"] in availableAxes else \
                                  img.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is False else \
                                  availableAxes[0]
                              
            verticalAxisInfo    = img.axistags["y"] if yIndex < img.ndim and img.axistags["y"] in availableAxes else \
                                  img.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is True else \
                                  availableAxes[1]
                
            nFrames = img.shape[img.axistags.index(frameAxisInfo.key)]
            
        else:
            # there is a channel axis therefore this is really a 2D data array
            # (even though, numerically it is represented by a 3D array);
            # hence it contains a single displayable frame
            channelAxisInfo = img.axistags[cIndex]
            
            #if userFrameAxis is not None:
                #warnings.warn("Ignoring userFrameAxis for a 3D array with channel axis (effectively a 2D image, possibly multi-band)", RuntimeWarning)
            
            nFrames = 1
            
            availableAxes = tuple(ax for ax in img.axistags if (ax.typeFlags & vigra.AxisType.Channels == 0))
            
            horizontalAxisInfo  = img.axistags["x"] if xIndex < img.ndim and img.axistags["x"] in availableAxes else \
                                  imt.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is False else \
                                  availableAxes[0]
                              
            verticalAxisInfo    = img.axistags["y"] if yIndex < img.ndim and img.axistags["y"] in availableAxes else \
                                  img.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is True else \
                                  availableAxes[1]
            
                
    elif img.ndim > 3:
        if cIndex == img.ndim:
            # no channel axis
                
            if userFrameAxis is None:
                spaceAxes = tuple(ax for ax in img.axistags if ax.typeFlags & Space)
                if len(spaceAxes) > 2:
                    putativeZaxes = tuple(ax for ax in spaceAxes if "z" in ax.key.lower())
                else:
                    putativeZaxes = tuple()
                    
                timeAxes  = tuple(ax for ax in img.axistags if ax.typeFlags & Time)
                
                framesAxisInfo = tuple(sorted(list(putativeZaxes + timeAxes),ley = lambda x: img.axistags.index(x)))
                
                # TODO 2021-11-27 22:08:30
                # figure out if there is an x, t, t1, ... or t, t1, t2, ... etc
                
                if len(frameAxisInfo) == 0:
                    # consider the first two axes as horiz/vert
                    frameAxisInfo = tuple(img.axistags[k] for k in range(2,img.ndim))
                
            else: # user-specified frame axes - must be a tuple for >3D
                if not isinstance(userFrameAxis, (list, tuple)):
                    raise TypeError("For arrays with more than three dimensions the frame axis must be a sequence of axis info objects")
                
                if any([not isinstance(ax, vigra.AxisInfo) for ax in userFrameAxis]):
                    raise TypeError("For arrays with more than three dimensions the frame axis must be a sequence of axis info objects")
                
                if len(userFrameAxis) != img.ndim-2:
                    raise TypeError(f"For a {img.ndim}-D array with no channel axis, the user frame axis sequence must contain {img.dim-2} AxisInfo objects; got {len(userFrameAxis)} instead")
                    
                frameAxisInfo = userFrameAxis
                
            availableAxes = tuple(ax for ax in img.axistags if ax not in frameAxisInfo and ax.typeFlags & vigra.AxisType.Channels == 0)
            
            horizontalAxisInfo  = img.axistags["x"] if xIndex < img.ndim and img.axistags["x"] in availableAxes else \
                                  img.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is False else \
                                  availableAxes[0]
                              
            verticalAxisInfo    = img.axistags["y"] if yIndex < img.ndim and img.axistags["y"] in availableAxes else \
                                  img.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is True else \
                                  availableAxes[1]
                              
        else:
            channelAxisInfo = img.axistags[cIndex]
            # there is a channel axis => an N-D array becomes an (N-1)-D data 'block'
            # with a channel axis
            nonChannelAxes = [ax for ax in img.axistags if (ax.typeFlags & vigra.AxisType.Channels == 0)]
            
            if userFrameAxis is None:
                # consider first two axes as horiz/vert
                frameAxisInfo = tuple(nonChannelAxes[k] for k in range(2, len(nonChannelAxes)))
                
            else:
                if isinstance(userFrameAxis, vigra.AxisInfo):
                    if img.ndim  > 4:
                        raise TypeError(f"For arrays with more than four dimensions useFrameAxis must be a sequence with at least {img.ndim-3} elements")
                    
                    userFrameAxis = [userFrameAxis]
                    
                elif isinstance(userFrameAxis, (list, tuple)):
                    if any([not isinstance(ax, vigra.AxisInfo) for ax in userFrameAxis]):
                        raise TypeError("user frame axis sequence must contain only axis info objects")
                    
                    if len(userFrameAxis) != img.ndim-3:
                        raise TypeError(f"For a {img.ndim}-D array with channel axis, the user frame axis sequence must contain {img.dim-3} AxisInfo objects; got {len(userFrameAxis)} instead")
                    
                frameAxisInfo = userFrameAxis

            availableAxes = [ax for ax in img.axistags if ax not in frameAxisInfo and ax.typeFlags & vigra.AxisType.Channels == 0]
            
            horizontalAxisInfo  = img.axistags["x"] if xIndex < img.ndim and img.axistags["x"] in availableAxes else \
                                  img.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is False else \
                                  availableAxes[0]
                              
            verticalAxisInfo    = img.axistags["y"] if yIndex < img.ndim and img.axistags["y"] in availableAxes else \
                                  img.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is True else \
                                  availableAxes[1]
                              
            
        # NOTE:this is WRONG
        #nFrames = sum([img.shape[img.axistags.index(ax.key)] for ax in frameAxisInfo])
        
        # NOTE: 2021-11-27 21:55:14 
        # this is OK but we don't use this anymore; return a tuple of frames along
        # each of the frame axes info
        #nFrames = np.prod([img.shape[img.axistags.index(ax.key)] for ax in frameAxisInfo])
        nFrames = tuple(img.shape[img.axistags.index(ax.key)] for ax in frameAxisInfo)
            
    #nFrames = tuple(img.shape[img.axistags.index(ax.key)] for ax in frameAxisInfo)
    
    if isinstance(frameAxisInfo, (tuple, list)) and len(frameAxisInfo) == 1:
        frameAxisInfo = frameAxisInfo[0]
        
    if isinstance(nFrames, (tuple, list)) and len(nFrames) == 1:
        nFrames = nFrames[0]
        
    horizontal = img.axistags.index(horizontalAxisInfo.key) if indices else horizontalAxisInfo
    vertical   = img.axistags.index(verticalAxisInfo.key) if indices else verticalAxisInfo
    channels   = img.ndim if channelAxisInfo is None else img.axistags.index(channelAxisInfo.key) if indices else channelAxisInfo
    
    if frameAxisInfo is None:
        frames = None
        #frames = img.ndim if indices else None
        
    elif isinstance(frameAxisInfo, tuple):
        frames = tuple(img.axistags.index(ax.key) if indices else ax for ax in frameAxisInfo)
        
    else:
        frames = img.axistags.index(frameAxisInfo.key) if indices else frameAxisInfo
    
        
    
    return Bunch({"nFrames":nFrames, 
                  "horizontalAxis":horizontal, 
                  "verticalAxis":vertical, 
                  "channelsAxis":channels,
                  "framesAxis":frames})

@singledispatch
def kernel2array(value:typing.Union[vigra.filters.Kernel1D, vigra.filters.Kernel2D], compact:bool=False):
    """
    Generates a numpy array with coordinates and values for the kernel's samples
    Parameters
    ----------
    value: Kernel1D or 2D
    compact:bool, default is False, see below for effects.
    
    Returns:
    -------
    for a 1D kernel of N samples:
        when compact is False:
            tuple (X, KRN) with:
                X: 1D numpy array with shape (N,) containing kernel coordinates
                    from kernel.left() to kernel.right()
                    ATTENTION:  THE ELEMENTS ARE NOT SAMPLE INDICES!
                
                KRN: 1D numpy array with shape (N,) containing the kernel sample values;
                
        when compact is True:
            2D numpy array with shape (N,2):
                column 0 : coordinates from kernel.left() to kernel.right()
                column 1 : kernel sample values
                
    for a 2D kernel (N x M samples):
        when compact is False:
            tuple (X, Y, KRN) with:
                X, Y: 2D numpy arrays with size (N,M) - these are
                    the meshgrid with the coordinates of kernel's samples, 
                    from kernel.lowerRight() to kernel.upperLeft()
                    
                KRN: 2D numy array with shape (N,M) - kernel sample values
                
        when compact is True:
            3D numy array with shape (N,M,3) where
            column 0: meshgrid X coordinates
            column 1: meshgrid Y coordinates
            column 2: kernel sample values
            
                
    In either case, the kernel's centre is at the centre (in the middle) of the
    the coordinate array(s).
    
    NOTE: To reconstruct from a compact array ('kernel_array'):
    -----------------------------------------------------------
    
    Pseudo-code:
    if kernel_array.ndim == 2 => Kernel1D, else Kernel2D
    
    Kernedl1D case:
    
    k1d         = vigra.filters.Kernel1D()
    left        = int(kernel_array[ 0, 0])
    right       = int(kernel_array[-1, 0])
    contents    = kernel_array[:, 0]
    k1d.initExplicitly(left, right, contents)
    
    Kernel2D case:
    
    k2d         = vigra.filters.Kernel2D()
    upperLeft   = (int(kernel_array[-1, 1, 0]), int(kernel_array[-1, -1, 1]))
    lowerRight  = (int(kernel_array[ 0, 0, 0]), int(kernel_array[ 0,  0, 1]))
    contents    = kernel_array[:, :, 2]
    k2d.initExplicitly(upperLeft, lowerRight, contents)
                
    """
    raise NotImplementedError(f"{type(value).__name__} objects are not supported")
    
@kernel2array.register(vigra.filters.Kernel1D)
def _(value, compact=False):
    """Returns a numpy.ndarray representation of a vigra.Kernel1D object
    Arguments: 
    "value" = vigra.Kernel1D object
    """
    x = np.atleast_1d(np.arange(value.left(), value.right()+1))
    y = np.array(list(value[t] for t in range(value.left(), value.right()+1)))
    
    if compact:
        return np.concatenate([x[:,np.newaxis], y[:,np.newaxis]], axis=1) # => 2D array
    
    return x, y

@kernel2array.register(vigra.filters.Kernel2D)
def _(value, compact=False):
    xx = np.linspace(value.lowerRight()[0], value.upperLeft()[0], value.width(), 
                     dtype=np.dtype(int))
    
    yy = np.linspace(value.lowerRight()[1], value.upperLeft()[1], value.height(),
                     dtype=np.dtype(int))
    
    x = np.meshgrid(xx,yy)
    
    y = np.full((value.height(), value.width()), np.nan)
    
    for kx, x_ in enumerate(xx): # from left to right
        for ky, y_ in enumerate(yy): # from top to bottom
            y[kx, ky] = value[x_, y_]
           
    if compact:
        return np.concatenate([x[0][:,:,np.newaxis], x[1][:,:,np.newaxis], y[:,:,np.newaxis]], axis=2) # => 3D array
            
    return x[0], x[1], y
    
def kernelfromarray(x):
    if isinstance(x, np.ndarray):# compact form
        if x.ndim == 2 and x.shape[1] == 2: # => Kernel1D
            left = int(x[0,0])
            right = int(x[-1,0])
            values = x[:,1]
            ret = vigra.filters.Kernel1D()
            ret.initExplicitly(left, right, values)
            return ret
        
        elif x.ndim == 3 and x.shape[2] == 3: # => Kernel2D
            upperLeft = (int(x[-1,-1,0]), int(x[-1,-1,1]))
            lowerRight = (int(x[0,0,0]), int(x[0,0,1]))
            values = x[:,:,2]
            ret = vigra.filters.Kernel2D()
            ret.initExplicitly(upperLeft, lowerRight, values)
            return ret
        
        else:
            raise ValueError(f"Incorrect argument dimensions or shape: {x.shape}")
            
    elif isinstance(x, (tuple, list)) and all(isinstance(x_, np.ndarray) and x_.ndim == 2 for x_ in x):
        if len(x) == 2: # => Kernel1D
            left = x[0][0,0]
            right = x[0][-1,0]
            values = x[1]
            ret = vigra.filters.Kernel1D()
            ret.initExplicitly(left, right, values)
            return ret
        
        elif len(x) == 3: # => Kernel2D
            upperLeft = (int(x[0][-1,1]), int(x[1][-1,-1]))
            lowerRight = (int(x[0][0,0]), int(x[1][0,0]))
            values = x[2]
            ret = vigra.filters.Kernel2D()
            ret.initExplicitly(upperLeft, lowerRight, values)
            return ret
        
        else:
            raise ValueError(f"Incorrect argument size {len(x)}")
            
    else:
        raise TypeError(f"Expecting a tuple or numpy array; got {type(x).__name__} instead")
        

def getCalibratedAxisSize(image, axis):
    """Returns a calibrated length for "axis" in "image" VigraArray, as a python Quantity
    
    If axisinfo is not calibrated (i.e. does not have a calibration string in its
    description attribute) then returns the size of the axis in pixel_unit.
    
    Parameters:
    ==========
    
    image: vigra.VigraArray
    
    axis: vigra.AxisInfo, axis info key string, or an integer; any of these must 
        point to an existing axis in the image
    
    """
    
    if isinstance(axis, int):
        axsize = image.shape[axis]
        axisinfo = image.axistags[axis]
        
    elif isinstance(axis, str):
        axsize = image.shape[image.axistags.index(axis)]
        axisinfo = image.axistags[axis]

    elif isinstance(axis, vigra.AxisInfo):
        axsize = image.shape[image.axistags.index(axis.key)]
        axisinfo = axis

    else:
        raise TypeError("axis expected to be an int, str or vigra.AxisInfo; got %s instead" % type(axis).__name__)
    
    axcal = AxisCalibrationData(axisinfo)
    
    # FIXME what to do when there are several channels?
    
    return axcal.calibratedDistance(axsize)

def nFrames(x:vigra.VigraArray, 
            frameAxis:typing.Optional[typing.Union[vigra.AxisInfo, str, int, collections.abc.Sequence[typing.Union[vigra.AxisInfo, str, int]]]]=None):
    if not isinstance(x, vigra.VigraArray):
        raise TypeError(f"Expecting a Vigra Array, got {type(x).__name__} instead")
    
    if frameAxis is None:
        #nFrames = proposeLayout(x)[0]
        nFrames = proposeLayout(x).nFrames
        if isinstance(nFrames, int):
            return nFrames
        
        elif isinstance(nFrames, collections.abc.Sequence):
            return np.prod(nFrames)
    
    if isinstance(frameAxis, (vigra.AxisInfo, str)):
        ndx = x.axistags.index(frameAxis.key)
        
    elif isinstance(frameAxis, int):
        ndx = frameAxis
        #ndx = x.axistags.index(frameAxis)
        
    elif isinstance(frameAxis, collections.abc.Sequence) and all(isinstance(v, (vigra.AxisInfo, str, int)) for v in frameAxis):
        ndx = tuple(x.axistags.index(v.key) if isinstance(v, vigra.AxisInfo) else x.axistags(v) if isinstance(v, str) else v for v in frameAxis )
        
    else:
        raise TypeError(f"frameAxis expected to be None, AxisInfo, str, int, or a sequence of these; got {typr(frameAxis).__name__} instead")
    
    if isinstance(ndx, int):
        return 1 if ndx == x.ndim else x.shape[ndx]
    
    elif isinstance(ndx, collections.abc.Sequence) and all(isinstance(i, int) for i in ndx):
        return np.prod(tuple(1 if idx == x.ndim else x.shape[idx] for idx in ndx))
    
    else:
        raise RuntimeError(f"Cannot determine the number of frames")
    
    

def specifyAxisTags(image, newtags, newshape=None, in_place=False):
    """Assigns a new AxisTags object to a VigraArray.
    Optionally, reshapes the data array and removes or inserts new axes
    if necessary.
    
    Positional parameters:
    ======================
    
    image: vigra.VigraArray
    
    newtags: a sequence (tuple or list) of maximum five axistag keys (str):
            "a", "c", "e", "f", "n", "x", "y", "z", "t", "?", "s", "l",
            "fa", "fe", "fn", "ft","fx", "fy", "fz"
            
            or:
                a string with comma-, space- or comma-space-separated keys
                    e.g. "x, y, z, t, c" or "x y z t c" or "x,y,z,t,c" 
                    
            or:
                a string with single-character keys (unsparated) 
                    e.g. "xyztc"
                    
            or:
                a sequence of vigra.AxisInfo objects
            
            or:
                a vigra.AxisTags object
            
            The length of the new tags may be greater than image.ndim only if
            a new shape is also specified (see below).
            
            In any case, the maximum length of new tags is 5.
            
    Named parameters:
    ==================
    newshape: None (default), or:
            a sequence (tuple or list) of new axes lengths (int), 
            axistag keys, or None, with the same number of elements as "newtags" 
            
            When an :int:, the element indicates the length of the axis indicated 
            by the corresponding tag element in the "newtags"
            
            When a tag key :string:, the axis at the corresponding position in 
            "newtags" will receive the length of the axis with _THIS_ tag key in 
            the "image"
            
            When :None:, the length of the axis at the corresponding index in "newtags"
            will be calculated from the lengths of the other axes and the 
            total number of samples of "image".
            
            There can at most one None element.
            
    in_place: boolean (default is False); 
            when False, the function returns a reshape copy of image, adorned
                with the new axistags
                
            when True, the "image" argument is modified directly (i.e. it gets
                the new axistags and the new shape) and the function returns a 
                reference to it
            
            
    """
    
 #   Signature: vigra.makeAxistags(spec, order=None, noChannels=None)
 #   Docstring:
 #   Create a new :class:`~vigra.AxisTags` object from the specification ``spec``.
 #   ``spec`` can be one of the following:
 #
 #   * an instance of the ``AxisTags`` class. In this case, the function creates
 #   a copy of ``spec``. If ``order`` is given, the resulting axistags are
 #   transposed to the desired order ('C', 'F', or 'V'). If ``noChannels=True``,
 #   the channel axis (if any) is dropped from the specification.
 #
 #   * a string or tuple of axis keys (e.g. ``'xyc'`` or ``('x', 'y', 'c')`` respectively)
 #   or a tuple of :class:`~vigra.AxisInfo` objects (e.g.
 #   ``(AxisInfo.x, AxisInfo.y, AxisInfo.c)``). The function then constructs a
 #   new ``AxisTags`` object from this specification. If ``order`` is given,
 #   the resulting axistags are transposed to the desired order ('C', 'F', or 'V').
 #   If ``noChannels=True``, the channel axis (if any) is dropped from the specification.
 #
 #   * an integer signifying the desired number of axes. In this case, the call (including
 #   optional arguments ``order`` and ``noChannels``) is forwarded to the function
 #   :meth:`~vigra.VigraArray.defaultAxistags`, whose output is returned.
 #   File:      /usr/lib64/python3.4/site-packages/vigra/arraytypes.py
 #   Type:      function
 
 # golden rule: number of samples must not change
    
    
    if not isinstance(image, vigra.VigraArray):
        raise TypeError("First argument must be a VigraArray; got %s instead." % (type(image).__name__))
    
    
    # newtags can be:
    # a sequence of AxisInfo keys (str)
    # a sequence of vigra.AxisInfo objects
    # a vigra.AxisTags object
    # a str containing space- or comma-separated keys
    if isinstance(newtags, (tuple, list)):
        if len(newtags) > image.ndims:
            if newshape is None:
                raise TypeError("When a new shape is not specified, new tags must not exceed the number of image dimensions (%d)" % image.ndim)
            
        if len(newtags) > 5:
            raise ValueError("Cannot specify more than 5 axis tags")
            
        if all([isinstance(tag, str) for tag in newtags]):
            tagslist = [vigra.AxisInfo(s, vigra.AxisType(axisTypeFromString[s])) for s in newtags]
            newTags = vigra.AxisTags(*tagslist)
            
        elif all([isinstance(tag, vigra.AxisInfo)]):
            newTags = vigra.AxisTags(newtags) # this c'tor supports a sequence of AxisInfo objects as a single argument
            
        else:
            raise TypeError("Expecting a sequence of str or vigra.AxisInfo objects")
        
    elif isinstance(newtags, vigra.AxisTags):
        newTags = newtags
        
    elif isinstance(newtags, str):
        if " " in newtags:
            a = newtags.split()         # "x, y, z" and "x y z" cases
            a = [c.strip(",") for c in a]
            
        elif "," in newtags:
            a = newtags.split(",")      # "x,y,z" case
            
        else:
            a = newtags
            
        for c in a:
            if c not in STANDARD_AXIS_TAGS_KEYS:
                raise ValueError("Invalid AxisInfo key: %s" % c)
            
        tagslist = [vigra.AxisInfo(c, vigra.AxisType(axisTypeFromString[c])) for c in a]
        newTags = vigra.AxisTags(*tagslist)
        
    else:
        raise TypeError("Expecting a sequence of str or vigra.AxisInfo objects, or a single vigra.AxisTags object; got a %s instead" % type(newtags).__name__)

    if newshape is not None:
        if isinstance(newshape, (tuple, list)):
            if len(newshape) != len(newTags):
                raise ValueError("Length of new shape must equal that of the new axis tags (%d)" % len(newTags))
            
            if all([isinstance(s, numbers.Integral) for s in newshape]):
                if np.prod(newshape) != image.size:
                    raise ValueError("When reshaping, the total number of elements in image must stay the same")
                
                newShape = newshape
                
            else:
                raise TypeError("New shape must contain numbers only")
            
        else:
            raise TypeError("New shape must be given as a tuple or list of numbers; got %s instead" % type(newshape).__name__)
        
    else: # no shape was specified: infer it from the length of new tags
        newShape = image.shape  # start with a default
                                # this applies to the case when newtags are as
                                #   many as image.ndim
                                # more new tags are prohibited by the earlier check
                                #   if you want to _ADD_ axes, you must also specify
                                #   a new shape
                                # case with fewer tags is dealt with next:
        if len(newTags) < image.ndim: # fewer tags, check if there are singleton axes to get rid of
            a = image.ndim - len(newTags)
            
            newShape = list(image.shape)
            
            for k in range(image.ndim-1, a, -1):
                if k >= len(newTags):
                    if image.shape[k] == 1:
                        del newShape[k]
                    else: # force specification of a tag for non-singleton dimensions
                        raise ValueError("Dimension %d is not singleton (has size %d), but does not have a new tag specified" % (k, image.shape[k]))
                        
    assert(np.prod(newShape) == image.size)
    
    
    if in_place:
        image.shape=newShape
        image.axistags=newTags
        
    else:
        # NOTE: reshape ALWAYS returns a copy of the source array
        image = image.reshape(newShape, axistags=newTags)
    
    return image

