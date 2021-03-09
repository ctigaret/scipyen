"""
Module for image processing routines
"""

#__all__ = ["pureDenoise", "binomialFilter1D", "gaussianFilter1D"]

#### BEGIN core python modules
import os, sys, traceback, warnings, numbers
#### END core python modules

#### BEGIN 3rd party modules
import imreg_dft as ird
import numpy as np
import quantities as pq
from scipy import optimize
import vigra
import neo
#### END 3rd party modules

#### BEGIN pict.core modules
from core import (tiwt, datatypes as dt, strutils, curvefitting as crvf,)

from imaging.axisutils import axisTypeFlags

#from .patchneo import neo
#### END pict.core modules

def getProfile(img, coordinates, order=3):
    import pictgui as pgui
    if not isinstance(img, vigra.VigraArray):
        raise TypeError("Expecting a 2D VigraArray; got %s instead" % (type(img).__name__))
    
    if img.ndim != 2:
        if img.ndim == 3:
            if img.channelIndex >= img.ndim:
                raise TypeError("Expecting a 2D VigraArray, or a 3D VigraArray with a channel axis; got a %d-dimensions array instead" % (img.ndim))
            
            elif img.channels > 1:
                raise TypeError("Expecting a single-band VigraArray")
    
    if not isinstance(order, int):
        raise TypeError("Spline order expected to be an int; got %s instead" % (type(order).__name__))
    
    elif order < 0 or order > 5:
        raise ValueError("Invalid spline order specified (%d); must be between 0 and 5" % (order))

    interpolators = (vigra.sampling.SplineImageView0, vigra.sampling.SplineImageView1, \
                    vigra.sampling.SplineImageView2, vigra.sampling.SplineImageView3, \
                    vigra.sampling.SplineImageView4, vigra.sampling.SplineImageView5)
    
    spl = interpolators[order](img)
    
    if isinstance(coordinates, (tuple, list, pgui.Path)):
        if all([isinstance(c, (tuple, list)) and len(c)==2 for c in coordinates]):
            return np.array([spl(c[0], c[1]) for c in coordinates])
            
        elif all([isinstance(c, (pgui.Move, pgui.Line)) for c in coordinates]):
            # NOTE: pgui.Path inherits from list so this checks True for pgui.Path objects, too
            return np.array([spl(p.x, p.y) for p in coordinates])
        
        else:
            if any(isinstance(c, pgui.CurveElements) for c in coordinates):
                raise TypeError("Curvilinear path elements are not supported")
            
            else:
                raise TypeError("Unexpected coordinates type (%s)" % (type(coordinates).__name__))
            
    elif coordinates is None:
        return np.full((1,1), np.nan)
        
    else:
        raise TypeError("Unexpected coordinates type (%s)" % (type(coordinates).__name__))
        

def pureDenoise(image, levels=0, threshold=0, alpha=1, beta=0, sigma2=0):
    #print("pureDenoise levels",levels,"thr", threshold, "a", alpha, "b", beta, "s2", sigma2)
    if not isinstance(image, vigra.VigraArray):
        raise TypeError("~Expecting a VigraArray; got %s instead" % type(image).__name__)
    
    if image.ndim != 2:
        if image.channelIndex == image.ndim:
            raise TypeError("Expecting a 2D VigraArray; got %d dimensions instead" % image.ndim)
            
    elif image.channelIndex < 2:
        raise TypeError("Expecting a VigraArray without channel axis")
    
    # TODO:
    # implement auto detection of nLevels 
    # implement noise parameter estimation (using vigra library, mean-variance)
    
    if levels<=0:
        pass # TODO implement auto detection of nLevels 
    
    if threshold < 0:
        threshold = 0
        
    if alpha <=0:
        alpha = 1
        
    if beta <0:
        beta = 0
        
    if sigma2 < 0:
        sigma2 = 0
    
    # NOTE: 2017-11-17 22:07:24 this operates on non-calibrated pixel values!
    # i.e. does not take into account existing channel axis calibration
    # also, the result is a copy of the filtered data: the non-channel axis 
    # calibrations do not propagate 
    
    # FIXME 2017-12-04 17:18:51
    # this is where dest will now become a new array and the reference to dest 
    # parameter will be lost
    image = (image.dropChannelAxis()-beta)/alpha
    
    if alpha != 1:
        sigma2 = sigma2/(alpha**2)
            
    dest = tiwt.fft_purelet(image, levels, sigma2=sigma2, thr=threshold).insertChannelAxis() * alpha + beta
    
    return dest

def binomialFilter1D(image, radius):
    """Image convolution with a 1D binomial kernel or norm 1.0.
    
    Kernel window size is 2*radius +1
    
    Convolution is performed separately on both X and Y axes.
    """
    if not isinstance(image, vigra.VigraArray):
        raise TypeError("Expecting a VigraArray; got %s instead" % type(image).__name__)
    
    if image.ndim <=3:
        if image.axistags.axisTypeCount(vigra.AxisType.NonChannel) != 2:
            raise TypeError("Expecting a VigraArray with two non-channel dimensions")
    
    else:
        raise TypeError("Expecting a VigraArray with two non-channel dimensions")
        
    flt = vigra.filters.binomialKernel(radius)
    
    # NOTE: 2017-11-17 22:07:24 this operates on non-calibrated pixel values!
    # i.e. does not take into account existing channel axis calibration
    # also, the result is a copy of the filtered data: the non-channel axis 
    # calibrations do not propagate 
    
    dest = vigra.VigraArray(image)
    
    vigra.filters.convolve(image, flt, dest)
    
    return dest
    
def gaussianFilter1D(image, sigma, window=0.0):
    """Image convolution with a 1D Gaussian kernel of norm 1.0.
    
    NOTE: when window is 0.0, the filter has a radius of 3 * sigma; otherwise, 
    its radius is window * sigma
    
    Convolution is performed separately on both X and Y axes.
    """
    if not isinstance(image, vigra.VigraArray):
        raise TypeError("Expecting a VigraArray; got %s instead" % type(image).__name__)
    
    if image.ndim <=3:
        if image.axistags.axisTypeCount(vigra.AxisType.NonChannel) != 2:
            raise TypeError("Expecting a VigraArray with two non-channel dimensions")
    
    else:
        raise TypeError("Expecting a VigraArray with two non-channel dimensions")
        
    flt = vigra.filters.gaussianKernel(scale, window)
    
    # NOTE: 2017-11-17 22:07:24 this operates on non-calibrated pixel values!
    # i.e. does not take into account existing channel axis calibration
    # also, the result is a copy of the filtered data: the non-channel axis 
    # calibrations do not propagate 
    dest = vigra.VigraArray(image)
    vigra.filters.convolve(image, flt, dest)
    return dest
    
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
    from core.axiscalibration import AxisCalibration

    src_axes = list()
    tgt_axes = list()
    
    if not isinstance(src, vigra.VigraArray):
        raise TypeError("First argument expected to be a vigra.VigraArray; got %s instead" % type(src).__name__)
    
    if not isinstance(target, vigra.VigraArray):
        raise TypeError("Second argument expected to be a vigra.VigraArray; got %s instead" % type(target)._name__)
    
    src_axis_cals = AxisCalibration(src)
    tgt_axis_cals = AxisCalibration(target)
        
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
            #print("%d: %s, new_res: %s; old_res: %s" % (k, ax.key, new_res, AxisCalibration(ax).resolution) )
            
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
    from core.axiscalibration import AxisCalibration
    
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
    
    image_cal = AxisCalibration(image)
    
    if image_cal.getUnits(axisinfo) == pq.dimensionless:
        warnings.warn("Resampling along a dimensionless axis")
        
    if image_cal.getDimensionlessResolution(axisinfo) == 1:
        warnings.warn("Resampling an axis with original resolution of %s" % image_cal.getDimensionlessResolution(axisinfo) )
        
    elif image_cal.getDimensionlessResolution(axisinfo) == 0:
        raise ValueError("Cannot resample an axis with zero resolution")
    
    if isinstance(new_res, pq.Quantity):
        if new_res.size !=  1:
            raise TypeError("Expecting new_res a scalar; got a shaped array %s" % new_res)
        
        if new_res.units != image_cal.getUnits(axisinfo):
            raise TypeError("New resolution has incompatible units with this axis calibration %s" % cal)
        
        new_res = new_res.magnitude
        
    elif not isinstance(new_res, numbers.Real):
        raise TypeError("Expecting new_res a scalar float or Python Quantity; got %s instead" % type(new_res).__name__)
    
    if new_res < 0:
        raise ValueError("New sampling rate (%s) must be strictly positive !" % new_res)
    
    if new_res > image_cal.getDimensionlessResolution(axisinfo):
        dn = int(new_res/image_cal.getDimensionlessResolution(axisinfo) * p)
        up = p
        
    elif new_res < image_cal.getDimensionlessResolution(axisinfo):
        up = int(image_cal.getDimensionlessResolution(axisinfo)/new_res * p)
        dn = p
        
    else:
        return image
    
    #up = int(cal[2]/new_res * p)
    
    if window is None:
        window = ("kaiser", 0.5)
    
    ret = vigra.VigraArray(resample(image, up, dn, axis=axisindex, window = window), axistags=image.axistags)
    
    units = image_cal.getUnits(axisinfo)
    origin = image_cal.getDimensionlessOrigin(axisinfo)
    resolution = new_res
    
    image_cal.setResolution(new_res, axisinfo)
    
    #newCal = AxisCalibration(ret.axistags[axisindex],
                                #units = units, origin = origin, resolution = resolution, 
                                #axisname = dt.defaultAxisTypeName(ret.axistags[axisindex]),
                                #axistype = ret.axistags[axisindex].typeFlags)
    
    #print("newCal", image_cal)
    
    image_cal.calibrateAxis(ret.axistags[axisindex])
    
    #dt.calibrateAxis(ret.axistags[axisindex], (cal[0], cal[1], new_res))
    
    return ret

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
    from core.axiscalibration import AxisCalibration

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
            
            res0 = AxisCalibration(array0.axistags[k]).resolution
            res1 = AxisCalibration(array1.axistags[k]).resolution
            
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
            
            res0 = AxisCalibration(array0.axistags[k]).resolution
            res1 = AxisCalibration(array1.axistags[k]).resolution
            
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
                
def imageSimilarity(img0, img1, **kwargs):
    """Delegates to imreg_dft.similarity on two vigra.VigraArray objects.
    
    From imreg_dft.similarity documentation:
    ========================================
    Return similarity transformed image im1 and transformation parameters.
    Transformation parameters are: isotropic scale factor, rotation angle (in
    degrees), and translation vector.

    A similarity transformation is an affine transformation with isotropic
    scale and without shear.

    Positional parameters:
    =====================
    img0, img1: vigra.VigraArray objects:
    
        img0: the first (template) image
        img1: the second (subject) image
        
        NOTE: both are expected to be 2D arrays or array views (i.e. with two
            non-channel axes and either without, or with a singleton channel axis)
            
            If both are >2D arrays, then similarity will be calculated for each
            corresponding 2D slice (taken along the 3rd and more slices)
            
        NOTE: both arrays must have the same shape (this implied they have the 
        same number of dimensions)
            
        
    Keyword parameters: (passed directly to imreg_dft; the documentation below 
    is copied from there)
    ===================
    numiter (int): How many times to iterate when determining scale and
        rotation; default = 1
    order (int): Order of approximation (when doing transformations). 1 =
        linear, 3 = cubic etc.; default = 3
    filter_pcorr (int): Radius of a spectrum filter for translation
        detection; default = 0
    exponent (float or 'inf'): The exponent value used during processing.
        Refer to the docs for a thorough explanation. Generally, pass "inf"
        when feeling conservative. Otherwise, experiment, values below 5
        are not even supposed to work.
        default = "inf"
    constraints (dict or None): Specify preference of seeked values.
        Pass None (default) for no constraints, otherwise pass a dict with
        keys ``angle``, ``scale``, ``tx`` and/or ``ty`` (i.e. you can pass
        all, some of them or none of them, all is fine). The value of a key
        is supposed to be a mutable 2-tuple (e.g. a list), where the first
        value is related to the constraint center and the second one to
        softness of the constraint (the higher is the number,
        the more soft a constraint is).

        More specifically, constraints may be regarded as weights
        in form of a shifted Gaussian curve.
        However, for precise meaning of keys and values,
        see the documentation section :ref:`constraints`.
        Names of dictionary keys map to names of command-line arguments.

        default is None
        
    reports (?) default is None
    
    Returns:
    =========
        dict: Contains following keys: ``scale``, ``angle``, ``tvec`` (Y, X),
        ``success`` and ``timg`` (the transformed subject image)
        
        Unlike imreg_dft.similarity, "timg" is a vigra.VigraArray

    See documentation of imreg_dft.similarity for details from imreg_dft
    
    NOTE: imreg_dft
        Copyright (c) 2014-?, Matěj Týč
        Copyright (c) 2011-2014, Christoph Gohlke
        Copyright (c) 2011-2014, The Regents of the University of California
    
    """
    
    if any([not isinstance(a, vigra.VigraArray) for a in (img0, img1)]):
        raise TypeError("Expecting two VigraArray objects; got %s and %s instead." % (type(img0).__name__, type(img1).__name__))
    
    if img0.ndim != img1.ndim:
        raise ValueError("Expecting VigraArray objects with the same number of dimensions; got %s and %s instead." % (img0.ndim, img1.ndim))
    
    if any([s[0] != s[1] for s in zip(img0.shape, img1.shape)]):
        raise ValueError("Images have different shapes: %s and %s" % (str(img0.shape), str(img1.shape)))
    
    if img0.ndim < 2:
        raise ValueError("Expecting VigraArray objects with at least two dimensions")
    
    ret = list()
    
    #ret = vigra.VigraArray(img0.shape, value = 0.0, axistags = vigra.AxisTags(*img0.axistags))
    
    if im0.ndim > 2:
        for k in range(img0.shape[-1]):
            src0 = img0.bindAxis(img0.axistags[-1], k)
            src1 = img1.bindAxis(img1.axistags[-1], k)
            
            ret.append(imageSimilarity(src0, src1, **kwargs))
            
    else:
        src0 = np.array(img0)
        
    return ret

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
        
def insertAxis(img, axinfo, axdim):
    """Inserts an axis specified by axinfo, at dimension axdim, in image img.
    
    Returns a copy of img with a new axis inserted.
    
    """
    
    if not isinstance(img, vigra.VigraArray):
        raise TypeError("Expecting 'img' as a VigraArray; got %s instead" % type(img).__name__)
    
    if isinstance(axinfo, str):
        axinfo = vigra.AxisInfo(key=axinfo, typeFlags = axisTypeFlags[axinfo], 
                                resolution = 1.0, 
                                description = dt.defaultAxisTypeName(axisTypeFlags[axinfo]))
        
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
    
            
def imageIndexTuple(img, slicing=None, newAxis=None, newAxisDim=None):
    """Idiom for introducing a new axis in an image.
    
    Returns a tuple useful for indexing a VigraArray taking into account a new axis.
    
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
                
                ndx = array.axistags.index(k.key)
                
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
                                     typeFlags=axisTypeFlags[newAxis],
                                     resolution=1.0,
                                     description=dt.defaultAxisTypeName(axisTypeFlags[newAxis]))
            
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

    axis    :   the concatenation axis, specified as one of the following types:
                
        int = index of an existing axis (default is 0)
                
        str = a valid AxisInfo key for an existing axis or for a new axis to be 
            added all images at the next higher dimension
                
        AxisInfo object for an existing axis, or for a newaxis (to be added to 
        the images on their next higher dimension)
        
    
        
    ignore: None (default) a string ("units", "origin" or "resolution") or 
        a sequence of any of these strings (e.g. ["units", "origin", "resolution"]) 
        denoting parameters to ignore from the calibration of concatenation axis
        (see AxisCalibration.is_same_as() for details)
        
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
    from .axiscalibration import AxisCalibration

    catAxis = 0
    
    ignore = None
    
    #asPictArray = False # set up below
    
    if len(kwargs) > 0:
        catAxis     = kwargs.pop("axis",     0)
        ignore      = kwargs.pop("ignore", None)
        
    # 1) check the "images" parameter:
    #print("concatenateImages: %d images" % len(images))
    
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
            #
            # just return a reference to images[0] image
            return images[0]
        
        elif isinstance(images[0],(tuple, list)):
            if not all([isinstance(i, vigra.VigraArray) for i in images[0]]):
                raise TypeError("Expecting a sequence of vigra arrays")
            
            images = images[0]
            
        else:
            raise TypeError("Expecting a vigra array, or a sequence of vigra arrays")
            
        #elif isinstance(images[0],(tuple, list)):
            #if all ([isinstance(i, dt.PictArray) for i in images[0]]):
                #images = images[0]
                #asPictArray = True # return PictArray type
                
            #elif any([isinstance(i, dt.PictArray) for i in images[0]]):
                ## implies mixed sequence of PictArray and VigraArray objects
                ## cast the VigraArray instances into PictArray
                #data = list()
                
                #for image in images[0]:
                    #if isinstance(image, vigra.VigraArray):
                        #data.append(dt.PictArray(image))
                        
                    #else:
                        #data.append(image)
                        
                #images = data
                
                #asPictArray = True # return PictArray type
                
            #elif all([isinstance(i, vigra.VigraArray) for i in images[0]]):
                ## implies none are PictArrays (as this has been already probed above)
                #images = images[0]
                
                #asPictArray = False # return VigraArray type
            
        #else:
            #raise TypeError("A vigra.VigraArray, datatypes.PictArray or a sequence (tuple or list) of vigra.VigraArray or datatypes.PictArray objects was expected")


    # NOTE: 2017-10-21 00:05:12
    # by now, images should be a sequence of VigraArrays
    
    
    #print(images)
    
    # check image dimensions
    image_dims = [img.ndim for img in images]
    
    min_dims = min(image_dims)
    
    max_dims = max(image_dims)
    
    if max_dims != min_dims:
        raise ValueError("Cannot concatenate images with different dimensionalities")
    
    axistags    = images[0].axistags
    
    axiscals    = AxisCalibration(images[0])
    
    #if isinstance(images[0], dt.PictArray):
        #axiscals = images[0].axiscalibration
        
    #else:
        #axiscals    = AxisCalibration(images[0])
        
    first_shape = images[0].shape

    # NOTE: 2018-09-05 22:47:20
    # sort out the identity of the concatenation axis:
    #
    # 1) catAxis given as int (index into first image axistags) =>
    #    set this to catAxisNdx then set catAxis to the axisinfo of the first image
    #    with the index given by catAxis in first image axistags
    # 2) catAxis given as a string (axis info key) => 
    #   figure out which axis it points to use that as catAxis and set catAxisNdx 
    #   to its index in the axistags of the first image
    # 3) catAxis given as vigra.AxisInfo object =>
    #   set catAxisNdx to its index in first image's axistags
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
        if catAxis < 0 or catAxis >= min_dims:
            raise ValueError("concatenation axis index must take values in the semi-open interval [0, %d); got %d instead" % (min_dims, catAxisNdx))
        
        catAxisNdx = catAxis
        
        if catAxisNdx < min_dims:
            catAxis = images[0].axistags[catAxisNdx]
            
    elif isinstance(catAxis, str):
        if catAxis not in images[0].axistags:
            # create a new axis then add it to each of the images
            new_images = list()
            
            catAxisNdx = min_dims
            
            newaxis = vigra.AxisInfo(key = catAxis, typeFlags = axisTypeFlags[catAxis],
                                     resolution=1.0,
                                     description = dt.defaultAxisTypeName(axisTypeFlags[catAxis]))
            for img in images:
                new_images.append(insertAxis(img, newaxis, catAxisNdx))
                
            catAxis = newaxis
                
            images = new_images
            
            axistags = images[0].axistags
            
            axiscals = AxisCalibration(images[0])

            #if isinstance(images[0], dt.PictArray):
                #axiscals = images[0].axiscalibration
                
            #else:
                #axiscals = AxisCalibration(images[0])
            
        else:
            catAxisNdx = axistags.index(catAxis)
            catAxis = axistags[catAxisNdx]
        
    elif isinstance(catAxis, vigra.AxisInfo):
        if catAxis not in images[0].axistags:
            new_images = list()
            catAxisNdx = min_dims
            
            for img in images:
                new_images.append(insertAxis(img, catAxis, catAxisNdx))
        
            images = new_images
            
            axistags = images[0].axistags
            
            axiscals = AxisCalibration(images[0])
            
            #if isinstance(images[0], dt.PictArray):
                #axiscals = images[0].axiscalibration
                
            #else:
                #axiscals = AxisCalibration(images[0])
            
        else:
            catAxisNdx = axistags.index(catAxis.key)
        
    else:
        raise TypeError("concatenation axis must be specified as an int, a str or a vigra.AxisInfo object; got %s instead" % type(catAxis).__name__)
        
        
    #if any([isinstance(img, dt.PictArray) for img in images]):
        #asPictArray = True
        
    # NOTE: 2018-09-05 23:32:14
    # check axistags, axis calibrations and array shapes
    # we allow for mismatches only for the concatenation axis, including ignoring
    # some or all of its calibration parameters (units, origin, resolution)
    for img in images[1:]:
        if img.axistags != axistags:
            raise ValueError("Cannot concatenate images with different AxisInfo objects")
        
        imgaxiscals = AxisCalibration(img)
        
        #if isinstance(img, dt.PictArray):
            #imgaxiscals = img.axiscalibration
            
        #else:
            #imgaxiscals = AxisCalibration(img)
        
        for key in imgaxiscals.keys:
            if axistags[key] == catAxis:
                if not axiscals.is_same_as(imgaxiscals, key, ignore=ignore):
                    if ignore is None:
                        raise RuntimeError("Cannot concatenate along the axis %s which has non-matching calibration across images" % key)
                    
                    else:
                        raise RuntimeError("Cannot concatenate along the axis %s which has non-matching calibration across images, ignoring %s" % (key, str(ignore)))
                
            else:
                if not axiscals.is_same_as(imgaxiscals, key, ignore=None):
                    raise RuntimeError("Cannot concatenate images with non-matching calibration for axis %s" % key)
                
        if not all(first_shape[s] == img.shape[s] for s in range(min_dims) if s != catAxisNdx):
            raise RuntimeError("Images must have identical shapes except along the concatenation axis")
            
    result = vigra.VigraArray(np.concatenate(images, axis=catAxisNdx), axistags = axistags)
    
    # save these for later
    axistags = result.axistags
    axiscals = AxisCalibration(axistags)
    
    #print("concatenate images")
            
    for axiskey in axiscals.keys:
        axiscals.calibrateAxis(result.axistags[axiskey])

    #if asPictArray:
        #result = dt.PictArray(np.concatenate(images, axis=catAxisNdx),
                              #axistags = axistags)
        
        #result.axiscalibration = axiscals
        
    #else:
        #result = vigra.VigraArray(np.concatenate(images, axis=catAxisNdx), axistags = axistags)
        
        ## save these for later
        #axistags = result.axistags
        #axiscals = AxisCalibration(axistags)
        
        ##print("concatenate images")
                
        #for axiskey in axiscals.keys:
            #axiscals.calibrateAxis(result.axistags[axiskey])
    
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
    
def sliceFilter():
    """ TODO 2019-11-14 09:49:22 place CaTanalysis filtering code here
    aims:
    1) make this more generic i.e. 
        1.1) allow the user to select the "slicing" axis along which
            a 2D view is created by using bindAxis()
        1.2) allow double-binding: i.e. let the user select slices for a given
            channel, then create a 2D slice view on that channel e.g. by calling bindAxis("c", channel_index).bindAxis(slice_axis, slice_index)
        
    2) make it suitable for wrapping in a multithreaded: e.g callable from QtConcurrent.run()
    """
    pass
    
    
