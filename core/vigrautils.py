import vigra
import numpy as np
import quantities as pq
from core.axiscalibration import AxisCalibration

def getFrameLayout(img, userFrameAxis=None):
    """Parses a vigra array to identify a reasonable axis defining "frames".
    
    A frame is a 2D array or array view.
    
    Parameters:
    ===========
    img: a VigraArray
    
    Returns:
    ========
    A tuple (nFrames:int, frameAxisInfo:vigra.AxisInfo, widthAxisInfo:vigra.AxisInfo, heightAxisInfo:vigra.AxisInfo)
    where:
     
    nFrames:int = the number of putative frames along the "frame" axis
     
    frameAxisInfo:vigra.AxisInfo = the AxisInfo along which the array will can
        be "sliced" into frames to be duisplayed individually
        NOTE: this may be None, a vigra.AxisInfo or a sequence of 
        vigra.AxisInfo objects for arrays with more than 3 dimensions (to enable
        iteration across nested frames)
     
    widthAxisInfo:vigra.AxisInfo = the axis for the image "width" : the first 
        non-channel axis (which is also the innermost non-channel axis given by 
        img.innerNonChannelIndex property)
        
    heightAxisInfo:vigra.AxisInfo = the axis of the image "height" : the 2nd dimension (second non-channel axis)
     
     NOTE the last two values need not be along the first and second axis, as this
     depends on which axis is the channel axis (if it exists); by default, in vigra 
     library the channel axis is typically the outermost one, but that depends on
     the internal storage order (order of axes) for the pixel data in the array
    
    Code logic:
    ==========
    
    A "frame" is a 2D slice view of a VigraArray. Arrays can be sliced along 
    any axis, including a channel axis. This function attempts to "guess"
    a reasonable axis along which the array can be sliced into 2D frames.
    
    NOTE: 2018-09-14 23:14:38
    give up on "separateChannels" thing -- useless; for arrays with > 4 dimensions
    we "flatten" the outermost nonchannel axes, thus setting the frames on the first 
    two axes
    
    """
    if not isinstance(img, vigra.VigraArray):
        raise TypeError("Expecting a VigraArray; got %s instead" % (type(img).__name__))
    
    if not hasattr(img, "axistags"):
        raise TypeError("Argument does not have axis information")
    
    if img.ndim == 0:
        raise TypeError("Expecting a VigraArray with at least 1 dimension")
    
    #if img.axistags.axisTypeCount(vigra.AxisType.NonChannel) < 2:
        #raise TypeError("Expecting at least two non-channel axes; got %d instead" % (img.axistags.axisTypeCount(vigra.AxisType.NonChannel)))
    
    #bring userFrameAxis to a common denominator: an AxisInfo object, or None
    if isinstance(userFrameAxis, (vigra.AxisInfo, str)):
        if userFrameAxis not in img.axistags:
            # CAUTION equality testing for AxisInfo objects ONLY  takes into
            # account the axis typeFlags and key
            raise ValueError("Axis %s not found in image" % userFrameAxis.key)
        
        if isinstance(userFrameAxis, str):
            userFrameAxis = img.axistags[userFrameAxis]
        
    elif isinstance(userFrameAxis, int):
        if userFrameAxis < 0 or userFrameAxis >= ndim:
            raise ValueError("Axis index expected to be in the semi-open interval [0 .. %d); got %d instead" % (img.ndim, userFrameAxis))
        
        userFrameAxis = img.axistags[userFrameAxis]
        
    elif isinstance(userFrameAxis, (tuple, list)):
        if all([isinstance(ax, (vigra.AxisInfo, str, int)) for ax in userFrameAxis]):
            try:
                frax = [img.axistags[ax] if isinstance(ax, str, int) else ax for ax in userFrameAxis]
                
            except Exception as e:
                raise RuntimeError("Invalid frame axis specified") from e
                
            userFrameAxis = frax
            
        else:
            raise TypeError("user frame axis sequence expected to contain vigra.AxisInfo objects, str or int elements")
        
        if any ([ax.typeFlags & vigra.AxisType.Channels for ax in userFrameAxis]):
            raise TypeError("Channels axes cannot be used as frame axes")
        
    elif userFrameAxis is not None:
        warnings.warn("Invalid user frame axes specification; will set it to None", RuntimeWarning)
        userFrameAxis = None
        
    #if isinstance(userFrameAxis, vigra.AxisInfo) and userFrameAxis.typeFlags & vigra.AxisType.Channels:
        #raise TypeError("Cannot use a Channels axis as frame axis")
    
    xIndex = img.axistags.index("x")
    yIndex = img.axistags.index("y")
    zIndex = img.axistags.index("z")
    tIndex = img.axistags.index("t")
    #cIndex = img.axistags.index("c")
    cIndex = img.channelIndex
    
    if img.ndim == 1:
        frameAxisInfo = None
        nFrames = 1

        if img.order == "C":
            heightAxisInfo = img.axistags[0]
            widthAxisInfo = None
            channelAxisInfo = None
            
        elif img.order  ==  "F":
            widthAxisInfo = img.axistags[0]
            heightAxisInfo = None
            channelAxisInfo = None
            
        else:
            widthAxisInfo = img.axistags[0]
            heightAxisInfo = None
            channelAxisInfo = img.axistags[0]
        
    elif img.ndim == 2: # trivial case; the check above passed means that there is no channel axis
        if userFrameAxis is not None:
            warnings.warn("Ignoring userFrameAxis for a 2D array", RuntimeWarning)
            
        frameAxisInfo = None
        nFrames = 1
        # NOTE: 2019-11-26 10:31:55
        # "x" or "y" may not be present e.g. in a Fourier transform so by default
        # we take:
        widthAxisInfo = img.axistags[0] 
        heightAxisInfo = img.axistags[1]
        
    elif img.ndim == 3:
        if cIndex == img.ndim: 
            # no channel axis:
            if userFrameAxis is None:
                frameAxisInfo = img.axistags[-1] # choose the outermost axis as frame axis
                widthAxisInfo = img.axistags[0]
                heightAxisInfo = img.axistags[1]
                
                
            else:
                if isinstance(userFrameAxis, (list, tuple)):
                    if len(userFrameAxis) != 1:
                        raise TypeError("for 3D arrays the user frame axis sequence must contain only one element; got %d instead" % len(userFrameAxis))
                    
                    if any([not isinstance(ax, vigra.AxisInfo) for ax in userFrameAxis]):
                        raise TypeError("user frame axis sequence must contain only vigra.AxisInfo objects")
                    
                    userFrameAxis = userFrameAxis[0]
                    
                elif not isinstance(userFrameAxis, vigra.AxisInfo):
                    raise TypeError("user frame axis must be either None, a vigra.AxisInfo, or a sequence of AxisInfo objects; got %s instead" % type(userFrameAxis).__name__)

                frameAxisInfo = userFrameAxis
                
                # skip frame axis for width and height
                nonFrameAxes = [ax for ax in img.axistags if ax != frameAxisInfo and ax.typeFlags & vigra.AxisType.Channels == 0]
                
                if len(nonFrameAxes) != 2:
                    raise RuntimeError("Cannot figure out which axes make a displayable frame")
                    
                widthAxisInfo = nonFrameAxes[0]
                heightAxisInfo = nonFrameAxes[1]
                
            nFrames = img.shape[img.axistags.index(frameAxisInfo.key)]
            
        else:
            # there is a channel axis therefore this is a 2D image hence 
            # a single displayable frame
            
            if userFrameAxis is not None:
                warnings.warn("Ignoring userFrameAxis for a 3D array with channel axis (effectively a 2D image, possibly multi-band)", RuntimeWarning)
            
            frameAxisInfo = None     # then set this as frameAxis; override parameter to view(...)
            nFrames = 1
            
            nonChannelAxes = [ax for ax in img.axistags if (ax.typeFlags & vigra.AxisType.Channels == 0)]
            
            widthAxisInfo = img.axistags[nonChannelAxes[0].key]
            heightAxisInfo = img.axistags[nonChannelAxes[1].key]
                
    elif img.ndim > 3:
        if cIndex == img.ndim:
            # no channel axis => "flatten" the two outermost axes
            if userFrameAxis is None:
                frameAxisInfo = [img.axistags[k] for k in range(2,img.ndim)]
                
                widthAxisInfo = img.axistags[0]
                heightAxisInfo = img.axistags[1]
                
            else:
                if not isinstance(userFrameAxis, (list, tuple)):
                    raise TypeError("For arrays with more than three dimensions the frame axis must be a sequence of axis info objects")
                
                if any([not isinstance(ax, vigra.AxisInfo) for ax in userFrameAxis]):
                    raise TypeError("For arrays with more than three dimensions the frame axis must be a sequence of axis info objects")
                
                if img.ndim == 4:
                    if len(userFrameAxis) != 2:
                        raise TypeError("for a 4D array with no channel axis, user frame axis sequence must contain two AxisInfo objects; got %d instead" % len(userFrameAxis))
                    
                elif img.ndim == 5:
                    if len(userFrameAxis) != 3:
                        raise TypeError("for a 5D array with no channel axis, user frame axis sequence must contain two AxisInfo objects; got %d instead" % len(userFrameAxis))
                
                frameAxisInfo = userFrameAxis
                
                nonFrameAxes = [ax for ax in img.axistags if ax not in frameAxisInfo and ax.typeFlags & vigra.AxisType.Channels == 0]
                
                if len(nonFrameAxes) != 2:
                    raise RuntimeError("Cannot figure out which axes make a displayable frame")
                
                widthAxisInfo = nonFrameAxes[0]
                heightAxisInfo = nonFrameAxes[1]
            
        else:
            # there is a channel axis => a 4D array becomes a 3D image with channel axis
            # => userFrameAxis CAN be a single AxisInfo object or a sequence with one element
            # and a 5D array becomes a 4D image with channel axis
            # => userFrameAxis MUST be a sequence with two elements
            if userFrameAxis is None:
                nonChannelAxes = [ax for ax in img.axistags if (ax.typeFlags & vigra.AxisType.Channels == 0)]
                
                frameAxisInfo = [nonChannelAxes[k] for k in range(2, len(nonChannelAxes))]
                
                widthAxisInfo = nonChannelAxes[0]
                heightAxisInfo = nonChannelAxes[1]
                
            else:
                if isinstance(userFrameAxis, (list, tuple)):
                    if any([not isinstance(ax, vigra.AxisInfo) for ax in userFrameAxis]):
                        raise TypeError("user frame axis sequence must contain only axis info objects")
                    
                    if img.ndim == 4:
                        if len(userFrameAxis) == 1:
                            userFrameAxis = userFrameAxis[0]
                            
                        else:
                            raise TypeError("for a 4D array with channel axis, user frame axis must be a sequence with one AxisInfo object or just an AxisInfo object; got a sequence with %d AxisInfo objects" % len(userFrameAxis))
                        
                    elif img.ndim == 5:
                        if len(userFrameAxis) != 2:
                            raise TypeError("for a 5D array with channel axis, user frame axis must be a sequence of TWO AxisInfo object; got %d instead" % len(userFrameAxis))
                        
                elif isinstance(userFrameAxis, vigra.AxisInfo):
                    if img.ndim == 5:
                        raise TypeError("for a 5D array with channel axis, user frame axis must be a sequence of TWO AxisInfo object; got %d instead" % len(userFrameAxis))

                if not isinstance(userFrameAxis, (list, tuple)):
                    raise TypeError("For arrays with more than three dimensions the frame axis must be a sequence of axis info objects")
                
                frameAxisInfo = userFrameAxis
                
                nonFrameAxes = [ax for ax in img.axistags if ax not in frameAxisInfo and ax.typeFlags & vigra.AxisType.Channels == 0]
            
                if len(nonFrameAxes) != 2:
                    raise RuntimeError("Cannot figure out which axes make a displayable frame")
                
                widthAxisInfo = nonFrameAxes[0]
                heightAxisInfo = nonFrameAxes[1]
                
        # NOTE:țhis is WRONG
        #nFrames = sum([img.shape[img.axistags.index(ax.key)] for ax in frameAxisInfo])
        
        # NOTE: this is OK
        nFrames = np.prod([img.shape[img.axistags.index(ax.key)] for ax in frameAxisInfo])
            
    else:
        raise TypeError("Expecting a vigra array with dimensionality in the closed interval [2 .. 5]")
    
    if isinstance(frameAxisInfo, (tuple, list)) and len(frameAxisInfo) == 1:
        frameAxisInfo = frameAxisInfo[0]
    
    return nFrames, frameAxisInfo, widthAxisInfo, heightAxisInfo

def vigraKernel1D_to_ndarray(value):
    """Returns a numpy.ndarray representation of a vigra.Kernel1D object
    Arguments: 
    "value" = vigra.Kernel1D object
    """
    x = np.arange(value.left(), value.right()+1)
    y = []
    
    for t in range(value.left(), value.right()+1):
        y.append(value[t])
    
    y = np.array(y)
    y.shape = (value.size(), 1)
    
    return x, y

def getCalibratedAxisSize(image, axis):
    """Returns a calibrated length for "axis" in "image" VigraArray, as a python Quantity
    
    If axisinfo is not calibrated (i.e. does not have a calibration string in its
    description attribute) then returns the size of the axis in pixel_unit.
    
    Parameters:
    ==========
    
    image: vigra.VigraArray
    
    axis: vigra.AxisInfo, axis info key string, or an integer; any of these must 
        point to an existing axis in the image
    
    NOTE: Parameter type checking is implicit
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
    
    axcal = AxisCalibration(axisinfo)
    
    # FIXME what to do when there are several channels?
    
    return axcal.getCalibratedAxialDistance(axsize, axisinfo.key)

def getAxisResolution(axisinfo):
    """Returns the resolution of the axisinfo object as a Python Quantity.
    """
    if not isinstance(axisinfo, vigra.AxisInfo):
        raise TypeError("Expecting a vigra.AxisInfo object; got %s instead" % type(axisinfo).__name__)
    
    axcal = AxisCalibration(axisinfo)
    
    # FIXME what to do when there are several channels?
    
    return axcal.getResolution(axisinfo.key)
    
def getAxisOrigin(axisinfo):
    """Returns the axis origin as a Python Quantity
    """
    if not isinstance(axisinfo. vigra.AxisInfo):
        raise TypeError("Expecting a vigra.AxisInfo object; got %s instead" % type(axisinfo).__name__)
    
    # FIXME what to do when there are several channels?
    
    axcal = AxisCalibration(axisinfo)
    
    return axcal.getOrigin(axisinfo.key)
    
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
            tagslist = [vigra.AxisInfo(s, axisTypeFlags[s]) for s in newtags]
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
            if c not in __all_axis_tag_keys__:
                raise ValueError("Invalid AxisInfo key: %s" % c)
            
        tagslist = [vigra.AxisInfo(c, axisTypeFlags[c]) for c in a]
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

