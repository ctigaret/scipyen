# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Module for image processing routines
"""

#__all__ = ["pureDenoise", "binomialFilter1D", "gaussianFilter1D"]

#### BEGIN core python modules
import os, sys, traceback, warnings, numbers
import typing
from collections import deque
#### END core python modules

#### BEGIN 3rd party modules
import imreg_dft as ird
import numpy as np
import quantities as pq
from scipy import optimize
from core.vigra_patches import vigra
import neo
#### END 3rd party modules

#### BEGIN pict.core modules
from core import (tiwt, datatypes  , strutils, curvefitting as crvf,)
from gui import pictgui as pgui
from gui import planargraphics as pgr

from imaging.axisutils import (axisTypeFromString,
                               axisTypeName, 
                               axisTypeSymbol,
                               axisTypeUnits)

from imaging.axiscalibration import (AxesCalibration, 
                                     AxisCalibrationData, 
                                     ChannelCalibrationData, 
                                     CalibrationData)

from core.datasignal import DataSignal

#from .patchneo import neo
#### END pict.core modules

def getProfile(img, coordinates:typing.Optional[typing.Union[pgui.PlanarGraphics, typing.Sequence[typing.Sequence]]]=None, 
               order:int=1) -> DataSignal:
    """Retrieves interpolated pixel values at a collection of (X,Y coordinates.

    The (X,Y) coordinates (in the image dimension space) are floating point values, 
    and do not necesarily fall on a pixel coordinates pairs. For this reason, 
    the function uses a spline interpolation (in the image data domain) to get
    an interpolated pixel VALUE at any given coordinates pair.

    The spline interpolation is calculated uwing vigra.SplineImageView family of
    functors, which supports a spline order from 1 to 5.


    """
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
    
    if isinstance(coordinates, pgui.PlanarGraphics):
        # NOTE: 2024-08-22 09:37:53 new algorithm:
        # 1) treat the object as a 1D function y = f(x)
        # 2) for linear and curve planargraphics call their curveLength() method
        #   (which implictly uses the approach stated at point (1) above)
        # 3) for path objects (most cases)
        # 3.1) composed entirely of linear elements (move, line):
        #   these MIGHT need interpolation: e.g. a line (path) is composed of two 
        #       elements (Move and Line) therefore I need a set of intermediate 
        #       coordinates between these points — I apply the principle stated
        #       at point (1) above, and use linear interpolation
        #   the potential problem is with a polyline path where the number of 
        #   segments is very large —
        
        if isinstance(coordinates, pgui.Path):
            if all([isinstance(c, pgr.LinearElements) for c in coordinates]):
                # NOTE: pgui.Path inherits from list so this checks True for pgui.Path objects, too
                # BUG: 2024-08-21 16:34:54 FIXME
                # the below could return only two points -- we need to interpolate
                # the coordinates!
                
                # NOTE: 2024-08-21 21:37:42
                # here, `coordinates` may be a line (two points) or a polyline (> 2 points)
                #
                # we want to interpolate BETWEEN these points; to keep things simple,
                # we use linear interpolation
                #
                # this produces two numpy arrays, respectively, with the x and y cordinates
                # of the roi's points
                # roi_x, roi_y = map(lambda x: np.array(x), zip(*[(p.x, p.y) for p in coordinates]))
                
                # the total length (in pixels) of the line or polyline is the sum of
                # the length of each segment; in turn the length of each segment is the Euclidean
                # distance between its end points
                #
                # ATTENTION: do NOT confuse with the Euclidean distance between roi_x, roi_y
                # vectors !!! That one applies to 𝑵-dimensional vectors, which roi_x, roi_y are NOT!
                
                density = coordinates.density
                
                if np.isclose(density, 1., atol=1e-1):
                    # there are approximately as many points as "pixels" in the Path obj
                    # ⇒ no need to interpolate
                    domain, values = map(lambda x: np.array(x), zip(*[(p.x, spl(p.x, p.y)) for p in coordinates]))
                
                else:
                    if density < 1:
                        # need linear interpolation across the points
                        pass
                
            
            else:
                if any(isinstance(c, pgui.CurveElements) for c in coordinates):
                    raise TypeError("Curvilinear path elements are not supported")
                
                else:
                    raise TypeError("Unexpected coordinates type (%s)" % (type(coordinates).__name__))
                
    elif isinstance(coordinates, (list, tuple, deque)) and all([isinstance(c, (tuple, list)) and len(c)==2 for c in coordinates]):
        return np.array([spl(c[0], c[1]) for c in coordinates])

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
    
    if threshold < 0.:
        threshold = 0.
        
    if alpha <= 0.:
        alpha = 1.
        
    if beta < 0.:
        beta = 0.
        
    if sigma2 < 0.:
        sigma2 = 0.
    
    # NOTE: 2017-11-17 22:07:24 this operates on non-calibrated pixel values!
    # i.e. does not take into account existing channel axis calibration
    # also, the result is a copy of the filtered data: the non-channel axis 
    # calibrations do not propagate 
    
    # FIXME 2017-12-04 17:18:51
    # this is where dest will now become a new array and the reference to dest 
    # parameter will be lost
    image = (image.dropChannelAxis()-beta)/alpha
    
    if alpha != 1.:
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
    
    if image.ndim <= 3:
        if image.axistags.axisTypeCount(vigra.AxisType.NonChannel) != 2:
            raise TypeError("Expecting a VigraArray with two non-channel dimensions")
    
    else:
        raise TypeError("Expecting a VigraArray with two non-channel dimensions")
        
    flt = vigra.filters.gaussianKernel(sigma, window)
    
    # NOTE: 2017-11-17 22:07:24 this operates on non-calibrated pixel values!
    # i.e. does not take into account existing channel axis calibration
    # also, the result is a copy of the filtered data: the non-channel axis 
    # calibrations do not propagate 
    dest = vigra.VigraArray(image)
    vigra.filters.convolve(image, flt, dest)
    return dest
    
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

# TODO: 2021-11-28 13:11:06 move to vigrautils
# TODO: 2021-11-28 13:10:42 move to vigrautils
# TODO: 2021-11-28 13:10:48 move to vigrautils

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
    
def fftshift(img:vigra.VigraArray):
    return vigra.VigraArray(np.fft.fftshift(img), img.dtype, "V", axistags = img.axistags)


    
