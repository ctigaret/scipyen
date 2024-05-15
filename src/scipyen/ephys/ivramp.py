# -*- coding: utf-8 -*-

#### BEGIN core python modules
import sys, traceback, inspect, numbers
import warnings
import os, pickle
import collections
from collections import OrderedDict
import itertools
#from builtins import property as _property, tuple as _tuple, list as _list
from operator import attrgetter, itemgetter, methodcaller

#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import pandas as pd
import quantities as pq
from scipy import optimize, cluster#, where

import matplotlib as mpl
import matplotlib.pyplot as plt

import neo

from qtpy import QtCore, QtGui, QtWidgets, QtXml
from qtpy.QtCore import Signal, Slot, Property
# from qtpy.QtCore import Signal, Slot, QEnum, Property
from qtpy.uic import loadUiType as __loadUiType__
# from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
# from PyQt5.QtCore import Signal, Slot, QEnum, Q_FLAGS, Property
# from PyQt5.uic import loadUiType as __loadUiType__

#### END 3rd party modules

#### BEGIN pict.core modules
import core.workspacefunctions as wf
import core.datatypes as datatypes
import core.signalprocessing as sigp
import core.curvefitting as crvf
import plots.plots as plots
import core.models as models
import core.strutils as strutils
import core.neoutils as neoutils
#from core.patchneo import *
#### END pict.core modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

#### BEGIN pict.gui modules
import gui.signalviewer as sv
#### END pict.gui modules

#### BEGIN pict.ephys modules
import ephys.ephys as ephys
#### END pict.ephys modules

# __module_path__ = os.path.abspath(os.path.dirname(__file__))

#_Ui_LTPWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__,"LTPGUI.ui"))


def macroscopic_conductance(v, i, **kwargs):
    """Calculates slope & chord conductances, Thevninf equivalent e.m.f and Erev.
    
    Parameters:
    -----------
    v = neo.AnalogSignal with Vm (in mV)
    i = neo.AnalogSignal with Im (in pA) -- inward current at Vm < 0
    
    Keyword parameters:
    ---------------------
    v_tol, i_tol: default to 1 mV and 1 pA, respectively
    
    Returns:
    --------
    A dict with the following keys:
    
    "g_slope"          = slope conductance
    "G_chord"          = chord conductance
    "emf"              = Thevenin emf
    "Erev"             = Erev
    "Ipeak"            = Ipeak
    "Ishort"           = I at short-circuit (at V = 0)
    "Ichord_intercept" = I interceot at chord conductance
    "Vpeak"            = V at peak I
    "VmHalfMaxAct"     = V at half-max activation
    "FWHM"             = Full-width of I(V) curve at half-max activation
    
    """
    from scipy.stats  import linregress
    from scipy.signal import argrelmin, argrelmax
    
    
    # set up default values
    v_tol = 1 * pq.mV
    i_tol = 1 * pq.pA
    
    # parse keyword parameters
    if "v_tol" in kwargs.keys():
        v_tol = kwargs["v_tol"]
        
        if isinstance(v_tol, numbers.Real):
            v_tol *= pq.mV
            
        elif isinstance(v_tol, pq.Quantity):
            if v_tol.dimensionality != (1*pq.mV).dimensionality:
                raise TypeError("v_tol must be a real scalar or a python Quantity with units of mV")
            
        else:
            raise TypeError("v_tol must be a real scalar or a python Quantity with units of mV")
        
    if "i_tol" in kwargs.keys():
        i_tol = kwargs["i_tol"]
        
        if isinstance(i_tol, numbers.Real):
            i_tol *= pq.pA
        
        elif isinstance(i_tol, pq.Quantity):
            if i_tol.dimensionality != (1*pq.pA).dimensionality:
                raise TypeError("i_tol must be a real scalar or a python Quantity with units of pA")
            
        else:
            raise TypeError("i_tol must be a real scalar or a python Quantity with units of pA")
    
        
    
    
    # calculates the slope conductance at short-circuit and the emf by interpolating:
    # I = f(V) around Vm = 0 +/- v_tol => 
    #   slope = g (slope conductance), 
    #   intercept = Isc (I at short circuit)
    #
    # then interpolate the inverse function V = f(I) around Vm = 0 +/- v_tol 
    #   intercept = emf (Thevenin equivalent e.m.f at Im ~ 0)
    #
    # both interpolations are done by linear regression on the first an last
    # samples in the interval correspondng to Vm == 0 +/- v_tol
    # (because the Vm array is a sampled analog signals, it may actually NEVER 
    # contain Vm == 0, just jumps around it); find the index of Vm values around 
    # zero and ue those to get the corresponding Im values.
    #
    # this works as long as Vm is monotonically increasing (which it is) and
    # only crosses the 0 value once (which it does)
    #
    # find Vshort-circuit (Vsc) i.e. Vm =  +/- v_tol
    v0_index = (v > (0 * pq.mV - v_tol)) & (v < (0 * pq.mV + v_tol))
    
    v0 = v.squeeze()[v0_index[:,0]] # Vm values near 0 (ths works because Vm is monotonically increasing)
    i_at_v0  = i.squeeze()[v0_index[:,0]] # Im data at Vm values "around" 0
    
    x = np.array([v0[0], v0[-1]])               # take first & last samples
    y = np.array([i_at_v0[0], i_at_v0[-1]])
    
    lreg1 = linregress(x, y) # linear regression on I = f(V)
    lreg2 = linregress(y, x) # linear regression on the inverse: V = f_1(I)
    
    g     = (lreg1.slope * pq.pA/pq.mV).rescale(pq.nS)           # slope conductance at I short circuit (at vm = 0)
    
    # Im at short circuit (at Vm = 0) is the Y intercept
    Isc = lreg1.intercept * pq.pA     
    
    # Thevenin equivalent electromotive force (e.m.f)
    emf = lreg2.intercept * pq.mV      # emf at Im = 0 for the linear I(V); this is the 
                                # X interept for the I = f(V), identical to the 
                                # Y intercept for the inverse V = f_1(I)
                                
    # get the chord conductance (linear regression between peak Im and empyrical 
    #   Vm at Im = 0 +/- i_tol)
    #
    # this are slightly more complicated here, because Im is NOT a monotonic 
    # function of Vm; furthermore Im may cross its zero several times (and not 
    # just because of noise - e.g. it is near zero, after leak-subtraction, when 
    # Vm is near rest or near Erev for K+)
    #
    # So we need to find the indices where Im is near zero (from both directions)
    # AND Vm > 0 i.e. in the region of I=f(V) where Im is monotonically increasing
    # (which happens when Vm > 0)
    
    I0_index = (i > (0*pq.pA - i_tol)) & (i < (0*pq.pA + i_tol)) & \
                (v > 0*pq.mV)
            
    i0 = i.squeeze()[I0_index[:,0]]
    v_at_i0 = v.squeeze()[I0_index[:,0]]
    
    # Im is bracketing zero
    x = np.array([i0[0], i0[-1]])               # take first & last samples
    
    # Vm where Im is bracketing zero
    y = np.array([v_at_i0[0], v_at_i0[-1]])
    
    # linear regression on the inverse: V = f_1(I)
    lreg3 = linregress(x,y) 
    
    # empyrical Erev = the intercept of V = f_1(I)
    Erev = lreg3.intercept * pq.mV 
    
    Ipeak = i.min()
    
    # find out Vm at Ipeak
    
    Vpeak = v[i.argmin(),0]
    
    #v_ipeak_index = (i > (Ipeak -i_tol)) & (i < (Ipeak + i_tol))
    
    ## Vm at peak Im
    #Vpeak = v.squeeze()[v_ipeak_index[:,0]].mean()
    
    # find out Vm at half-max activation
    
    v_at_i_half_max = v.squeeze()[(i <= Ipeak/2)[:,0]]
    
    Vhmax_act = v_at_i_half_max[0]
    
    # full width half-max of the I(V) curve
    FWHM = v_at_i_half_max[-1] - v_at_i_half_max[0]
    
    # calculate chord conductance between Ipeak and empyrical Erev
    # the function is I = f(V), "linear"
    x = [Vpeak, Erev]
    y = [Ipeak, 0*pq.pA]
    
    #G = ((0*pq.pA-Ipeak)/(Erev-Vpeak)).rescale(pq.nS)
    
    lreg4 = linregress(x, y)

    G = (lreg4.slope * pq.pA/pq.mV).rescale(pq.nS)
    
    IscG = (lreg4.intercept) * pq.pA #  intercept of the chord conductance line
    
    ret = OrderedDict()
    ret["G_chord"]      = G
    ret["g_slope"]      = g
    ret["Erev"]         = Erev
    ret["emf"]          = emf
    ret["VmHalfMaxAct"] = Vhmax_act
    ret["FWHM"]         = FWHM
    ret["Vpeak"]        = Vpeak
    ret["Ipeak"]        = Ipeak
    ret["Ishort"]       = Isc
    ret["Ichord_intercept"] = IscG
    
    return ret
    
def plot_conductance(x, g, intercept, **kwargs):
    plots.plotZeroCrossedAxes(x, x * g + intercept, **kwargs)


    
def fit_Markwardt_Nilius(Vm, Im, **kwargs): #g, Erev, Vhmax, slope):
    """Fits Markwardt & Nilius (1988) model to IV data.
    Model function is: ivca_Markwardt_Nilius()
    
    Positional parameters:
    ----------------------
    
    Vm, Im = column vectors with membrane volage and current (neo.AnalogSignals in mV and pA)
    
    Keyword parameters:
    -------------------
    g       = real scalar or python Quantity in nS: slope conductance
    
    Erev    = real scalar or python Quantity in mV: reversal potential
    
    Vhmax   = real scalar or python Quantity in mV: Vm at half-maximal activation
    
    slope   = real scalar: slope coefficient for Markwardt - Nilius model.
    
    Vmin, Vmax = min and max of the Vm domain for the fitted curve
        optional default None: when None, the fitted curve is generated over the
        values in Vm array
        
        When given they can be either scalars or python quantities in mV
            
    Returns:
    --------
    
    popt = a sequence of the fitted parameters (floating point scalars, 
        not converted to python Quantities):
        
        g, Erev, Vhmax, slope
    
    Ifit = fitted I(V) curve (neo.AnalogSignal)
    
    rsq  = coefficient of determination ("R squared") of the fit
    
    sse  = sum of squared errors between Ifit and Im
    
    perr = a sequence with errors in the fitted parameters
    
    NOTE:
    -----
    
    The free parameters fitted in this model are:
    
    g (slope conductance)
    
    Erev
    
    V0.5
    
    slope
    
    """
    
    if "g" in kwargs.keys():
        g = kwargs["g"]
        
        if not isinstance(g, pq.Quantity):
            g *= pq.nS
        
    else:
        g = 60 * pq.nS
        
    if "Erev" in kwargs.keys():
        Erev = kwargs["Erev"]
        
        if not isinstance(Erev, pq.Quantity):
            Erev *= pq.mV
            
    else:
        Erev = 30 * pq.mV
        
    if "Vhmax" in kwargs.keys():
        Vhmax = kwargs["Vhmax"]
        
        if not isinstance(Vhmax, pq.Quantity):
            Vhmax *= pq.mV
            
    else:
        Vhmax = -30 * pq.mV
        
    if "slope" in kwargs.keys():
        slope = kwargs["slope"]
        
    else:
        slope = 1
    
    if "Vmin" in kwargs.keys():
        Vmin = kwargs["Vmin"]
        
    else:
        Vmin = None
        
    if "Vmax" in kwargs.keys():
        Vmax = kwargs["Vmax"]
        
    else:
        Vmax = None
    
    model_func = models.Markwardt_Nilius
    
    popt, pcov = optimize.curve_fit(model_func, Vm.magnitude.squeeze(), Im.magnitude.squeeze(), [float(g), float(Erev), float(Vhmax), float(slope)])
    
    if Vmin is not None and Vmax is not None:
        if isinstance(Vmin, pq.Quantity):
            Vmin = Vmin.rescale(pq.mV).magnitude
            
        if isinstance(Vmax, pq.Quantity):
            Vmax = Vmax.rescale(pq.mV).magnitude
            
        Ifit = models.Markwardt_Nilius(np.linspace(Vmin, Vmax, num = Vm.squeeze().shape[0]), *popt)
        
    else:
        Ifit = models.Markwardt_Nilius(Vm.magnitude.squeeze(), *popt)
    
    sst = np.sum((Im.magnitude.squeeze() - np.mean(Im.magnitude.squeeze())) ** 2.) # total sum of squares
    
    ##NOTE: FYI
    #ssr = np.sum((Ifit - np.mean(Im)) ** 2.) # regression sum of squares (explained sum of squares)
    
    sse = np.sum((Ifit - Im.magnitude.squeeze()) ** 2.) # sum of squared residuals, or "errors" (residual sum of squares)
    
    rsq = 1- sse/sst # coefficient of determination
    
    # NOTE: 2017-08-28 19:05:36
    # alternatively this can be calculated:
    #ssxm, ssxym, ssyxm, ssym = np.cov(Im, Ifit, bias=True).flat
    
    #r_ = ssxym / np.sqrt(ssxm * ssym)
    
    #r_sq = r_ ** 2.
    
    perr = np.sqrt(np.diag(pcov)) # error in parameter estimates
    
    Ifit = neo.AnalogSignal(Ifit, units = Im.units, t_start = Im.t_start, \
                            sampling_period = Im.sampling_period, \
                            name ="Markwardt-Nilius fit of %s" % Im.name)
    
    return Ifit, popt, rsq, sst, sse, pcov, perr

def fit_Talbot_Sayer(vm, im, **kwargs):
    """
    Positional parameters:
    ----------------------
    
    vm  = AnalogSignal in mV
    im  = AnalogSignal in pA
    
    Keyword parameters:
    -------------------
    
    slope   = Boltzman slope factor (default = 2.5, dimensionless)
    
    scale   = proportionality constant (default = 50, dimensionless) 
    
    ca_in   = internal Ca2+ concentration: python Quantity in mM, or scalar (default = 0.05 mM) 
    
    V0_5    = Boltzman shift along the Vm axis, in mV (default = -30 mV)
    
    t       = temperature : python Quantity in degC or scalar (default = 33 degC)
    
    ca_out  = external Ca2+ concentration optional: python Quantity, in mM or scalar;
                (default = 2.5 mM)
    
    Vmin, Vmax = min and max of the Vm domain for the fitted curve
        optional default None: when None, the fitted curve is generated over the
        values in Vm array
        
        When given they can be either scalars or python quantities in mV
            
    Returns:
    ---------
    yfit, popt, rsq, sst, sse, pcov, perr
    
    yfit = AnalogSignal with the fitted Im data
    
    The following returned variables are also found in yfit.annotations attribute
    
    popt = sequence of four floating point scalars (not converted to python Quantities):
    
        Boltzman slope factor, 
        
        scale (I-V curve proportionality constant)
        
        ca_in : estimated internal Ca2+ concentration
        
        V0_5: shift of Boltzman along the Vm axis -- same as the Vm at half-max activation
    
    NOTE:
    -----
    
    The free parameters fitted in this model are:
    slope, scale, ca_in, and V0_5
    
    """
    
    # blue-sky guess for initial parameter values:
    
    if "slope" in kwargs.keys():
        slope   = kwargs["slope"]
        
    else:
        slope = 2.5
    
    if "scale" in kwargs.keys():
        scale  = kwargs["scale"]
        
    else:
        scale = 50
    
    if "ca_in" in kwargs.keys():
        ca_in  = kwargs["ca_in"]

        if not isinstance(ca_in, pq.Quantity):
            ca_in *= pq.mM
        
    else:
        ca_in = 0.05 * pq.mM
        
    if "V0_5" in kwargs.keys():
        V0_5  = kwargs["V0_5"]
        
        if not isinstance(V_5, pq.Quantity):
            V0_5 *= pq.mV
        
    else:
        V0_5 = -30 * pq.mV
    
    if "t" in kwargs.keys():
        t  = kwargs["t"]
        
        if not isinstance(t, pq.Quantity):
            t *= pq.degC
    
    else:
        t = 33 * pq.degC

    if "ca_out" in kwargs.keys():
        ca_out = kwargs["ca_out"]
        
        if not isinstance(ca_out, pq.Quantity):
            ca_out *= pq.mM

    else:
        ca_out = 2.5 * pq.mM
    
    if "Vmin" in kwargs.keys():
        Vmin = kwargs["Vmin"]
        
    else:
        Vmin = None
        
    if "Vmax" in kwargs.keys():
        Vmax = kwargs["Vmax"]
        
    else:
        Vmax = None
    
    model_func = models.Talbot_Sayer

    popt, pcov = optimize.curve_fit(lambda x, a, b, c, x0: model_func(x, a, b, c, x0, t = t, o = ca_out), \
                                    vm.magnitude.squeeze(), \
                                    im.magnitude.squeeze(), \
                                    [slope, scale, float(ca_in), float(V0_5)])
    
    if Vmin is not None and Vmax is not None:
        if isinstance(Vmin, pq.Quantity):
            Vmin = Vmin.rescale(pq.mV).magnitude
            
        if isinstance(Vmax, pq.Quantity):
            Vmax = Vmax.rescale(pq.mV).magnitude
            
        yfit = model_func(np.linspace(Vmin, Vmax, vm.squeeze().shape[0], endpoint=False), *popt, t=t, o=ca_out)
        
    else:
        yfit = model_func(vm.magnitude.squeeze(), *popt, t=t, o=ca_out)
    
    sst = np.sum( (im.magnitude.squeeze() - im.magnitude.mean()) ** 2.)
    
    sse = np.sum((yfit - im.magnitude.squeeze()) ** 2.)
    
    rsq = 1 - sse/sst
    
    perr= np.sqrt(np.diag(pcov))
    
    yfit = neo.AnalogSignal(yfit, units = im.units, t_start = im.t_start, \
                            sampling_period = im.sampling_period, \
                            name = "Talbot-Sayer fit of %s" % im.name)
    
    yfit.annotations["popt"] = popt
    yfit.annotations["rsq"] = rsq
    yfit.annotations["sst"] = sst
    yfit.annotations["sse"] = sse
    yfit.annotations["pcov"] = pcov
    yfit.annotations["perr"] = perr
    
    return yfit, popt, rsq, sst, sse, pcov, perr


def plotIVramp(block, segment=0, epoch=None, 
               ImSignal="Im_prim_1", VmSignal="Vm_sec_1", VmRest = None,
                **kwargs):
    
    """Plots an IV ramp experiment contained in the specified segment of a neo block data.
    
    The data is plotted in the current matplotlib figure (one will be created if none exists)
    
    Arguments:
    ==========
    
    block: neo.Block
    
    Keyword arguments:
    =================
    
    segment: valid segment index; optional, default is 0
    
    epoch: tuple of pq.s quantities (start, duration), neo.Epoch or None
            when None (the default), the block's segment is expected to contain
            an epoch named "IVRamp"; failing that, it will plot the entire segment's 
            data
    
    ImSignal: valid analogsignal index or name with Im data
    
    VmSignal: valid analogsignal index or name with Vm data
    
    VmRest: None (the default) or a python Quantity with the value of resting Vm
        (before the Vm ramp was applied)
    
    The following will be passed on to plots.plotZeroCrossedAxes() function:
    
    newPlot = False; if True then the current figure will be cleared first
    
    legend: None or a tuple or list of str
    
    xlabel, ylabel: None, or strings
    
    
    Returns:
    ========
    
    A tuple (lines, ax, ax1) with the line2d, main axis and time_axis artists.
    
    """
    if not isinstance(block,neo.Block):
        raise TypeError("Expected a neo.Block as first argument; got a %s instead" % (type(block).__name__))
    
    if isinstance(ImSignal, str):
        try:
            ImSignal = neoutils.get_index_of_named_signal(block.segments[0], ImSignal)
            
        except Exception as e:
            raise RuntimeError("%s signal not found" % ImSignal)
        
    if segment < 0 or segment > len(block.segments):
        raise ValueError("Invalid segment index: %d; expected an integer between 0 and %d" % (segment, len(block.segments)-1))
    
        
    if isinstance(VmSignal, str):
        try:
            VmSignal = neoutils.get_index_of_named_signal(block.segments[0], VmSignal)
            
        except Exception as e:
            raise RuntimeError("%s signal not found" % VmSignal)
        
    
    if isinstance(epoch, (tuple ,list)):
        t_start = epoch[0]
        t_stop = epoch[1]
        
        if not isinstance(t_start, pq.Quantity):
            t_start *= block.segments[segment].analogsignals[ImSignal].times.units
            
        else:
            if t_start.dimensionality != block.segments[segment].analogsignals[ImSignal].times.dimensionality:
                raise TypeError("Expecting of epoch start to be %s; got %s instead." % (str(block.segments[segment].analogsignals[ImSignal].times.dimensionality), str(t_start.dimensionality)))
            
        if not isinstance(t_stop, pq.Quantity):
            t_stop *= block.segments[segment].analogsignals[ImSignal].times.units
            
        else:
            if t_stop.dimensionality != block.segments[segment].analogsignals[ImSignal].times.dimensionality:
                raise TypeError("Expecting of epoch duration to be %s; got %s instead." % (str(block.segments[segment].analogsignals[ImSignal].times.dimensionality), str(t_stop.dimensionality)))
            
        #epoch = neo.Epoch(times = t_start, durations = t_stop-t_start name="IVRampEpoch")
            
    elif isinstance(epoch, neo.Epoch):
        if epoch.size > 1:
            raise ValueError("Expeting an epoch of size 1; instead got size %d" % epoch.size)
        
        t_start = epoch.times
        t_stop = epoch.times + epoch.durations
        
    elif epoch is None:
        if len(block.segments[segment].epochs) == 0:
            warnings.warn("specified epoch is None, and the block's segment has no epochs defined", stacklevel=2)
        
        for e in block.segments[segment].epochs:
            if e.name == "IVRamp":
                epoch = e
                break
            
        if epoch is None:
            t_start = block.segments[segment].t_start
            t_stop  = block.segments[segment].t_stop
            
        else:
            t_start = epoch.times
            t_stop = epoch.times + epoch.durations
                
    else:
        raise TypeError("epoch should be a neo.Epoch, or a tuple or list with start and stop times")
    
    if len(kwargs) == 0:
        kwargs = dict()
    
    if "legend" not in kwargs.keys():
        if block.name is None or len(block.name) == 0:
            if block.file_origin is None or len(block.file_origin) == 0:
                try:
                    cframe = inspect.getouterframes(inspect.currentframe())[1][0]
                    for (k,v) in cframe.f_globals.items():
                        if isinstance(v, neo.Block) and v == block:
                            name = k

                finally:
                    del(cframe)
                    
            else:
                name = block.file_origin
                
        else:
            name = block.name
            
        kwargs["legend"] = name

    if "xlabel" not in kwargs.keys():
        kwargs["xlabel"] = "%s (%s)" % (block.segments[segment].analogsignals[VmSignal].name, 
                                        block.segments[segment].analogsignals[VmSignal].dimensionality)
    
        
    if "ylabel" not in kwargs.keys():
        kwargs["ylabel"] = "%s (%s)" % (block.segments[segment].analogsignals[ImSignal].name, 
                                        block.segments[segment].analogsignals[ImSignal].dimensionality )
        
            
    if isinstance(VmRest, pq.Quantity):
        if t_start is None or t_stop is None:
            (lines, ax) = plots.plotZeroCrossedAxes(block.segments[segment].analogsignals[VmSignal].magnitude + VmRest,
                                                    block.segments[segment].analogsignals[ImSignal].magnitude, 
                                                    **kwargs)
            
        else:
            (lines, ax) = plots.plotZeroCrossedAxes(block.segments[segment].analogsignals[VmSignal].time_slice(t_start, t_stop).magnitude + VmRest, 
                                                    block.segments[segment].analogsignals[ImSignal].time_slice(t_start, t_stop).magnitude, 
                                                    **kwargs)
        
    else:
        if t_start is None or t_stop is None:
            (lines, ax) = plots.plotZeroCrossedAxes(block.segments[segment].analogsignals[VmSignal].magnitude, 
                                                    block.segments[segment].analogsignals[ImSignal].magnitude, 
                                                    **kwargs)
            
        else:
            (lines, ax) = plots.plotZeroCrossedAxes(block.segments[segment].analogsignals[VmSignal].time_slice(t_start, t_stop).magnitude, 
                                                    block.segments[segment].analogsignals[ImSignal].time_slice(t_start, t_stop).magnitude,
                                                    **kwargs)
    
    return (lines, ax)
    
    
def average_ivramps(epoch, *blocks, **kwargs):
    """Averages several blocks each containing IV curve data from Vm ramp 
    (voltage-clamp experiments).
    
    Arguments:
    ==========
    
        epoch: neo.Epoch object with:
                times = start time of the Vm ramp, and 
                durations = duration of the Vm ramp
                (all in pq.s).
                    
        
        *blocks: neo.Block objects with individual Vramp data; each object must
                contain at least one segment for which "epoch" defines  a valid 
                interval, and the segments must contain  at least two signals,
                one with leak-subtracted Im signal, the other with the membrane
                voltage (Vm) ramp signal, as specified in the Keyword arguments.
                
                See NOTES (1) and (2), below.
            
    Keyword arguments:
    ==================
    
        "V0":   holding membrane potential set "at the amplifier" i.e, the 
                membrane potential at the beginning of the voltage ramp 
                AS SET directly at the amplifier controls (optional, 
                default is -80 mV); see NOTE (3), below 
                
        "segment": = the index of the neo.Segment within each neo.Block,
                with relevant data (integral scalar; default is 0 i.e., the 
                first segment in each block); see NOTE (2) below
                
        "ImSignal": either an index for the leak-subtracted Im signal
            or a string with its name (default: "Im_prim_1");
                see NOTE (4) below.
            
        "VmSignal": either an index for the Vm signal, or a string with
                its name (default: "Vm_sec_1"); see NOTE (4) below.
            
        "RawImSignal": the index for the raw Im signal or a string with its
                name (default: "Im_prim_C"); see NOTE (4) below

            Note that these values cannot exceed the actual Vm range 
            (after adding V0). If both V0 and V1 are not None, then
            the curve regions between these two Vm values are returned.
            CAUTION: they may have different lengths for different runs!
            
        "name": str: the name of the resulting neo.Block (optional, default is None)
            
    Returns:
    =======
    A neo.Block with the averaged data from *blocks and containing the neo.Epoch
    corresponding to the actual IV ramp in the segment. 
    
    CAUTION: The value of V0 is added to the Vm analog signal in the result.
    
    If only one Block was passed to the function call, then it will be returned 
    with the modifications mentioned above.
    
    NOTES:
    =====
    
    NOTE (1) The blocks should be inspected first to make sure the epoch times
    fall within the segments' time base.
    
    NOTE (2) 
    Each block may contain more than one segment, where each segment may contain
    data obtained with Vm ramps at different rates, or different signal treatment
    (e.g. different leak-sutraction parameters)
    
    This function assumes that all blocks being averaged have the same number of 
    segments, but is oblivious to what each segment does. When applied to blocks 
    with multiple segments, the function will average every nth segment in each 
    block (given that "segment" argument is n).
    
    NOTE (3): CAUTION: The voltage ramp is generated by a command voltage 
    superposed (added to) the holding potential V0. The latter is usually set 
    directly through the amplifier controls. However, the acquisitoin software
    (e.g. Clampex) offers the option to set the holding potential through the 
    protocol configuration dialog, independently of the amplifier's control panel.
    When this happens the cells will be effectively held at V0 + the holding 
    potential preset in the protocol, unless V0 is set to zero directly at the 
    amplifier.
    
    The Vm analog signal in the abf file therefore contains the command voltage
    during the ramp PLUS the value of the holding potential AS SET in the protocol;
    it does NOT incorporate V0 as set at the amplifier.
    
    Unfortunately, the value of V0 as set "at the amplifier" is not saved by 
    Clampex in the file, so it needs to be specified here.

    NOTE (4) The segments in each block are expected to contain analog signals 
    for:
    
    a) the voltage ramp
    b) leak-subtracted current data
    c) raw membrane current data
    
    The names of these signals (channels) are saved with the abf file and with 
    the protocol, so make a note of these.
    
    See also:
    http://mdc.custhelp.com/app/ask/session/L2F2LzEvdGltZS8xNTAzNzU5MjQxL3NpZC91Mm96Yzdybg%3D%3D
    
    NOTE (4)
    """

        
    V0 = -80 * pq.mV
    
    segment = 0
    
    ImSignal = "Im_prim_1"
    
    VmSignal = "Vm_sec_1"
    
    RawImSignal = "Im_prim_C"
    
    name=None

    if len(kwargs)>0:
        if "V0" in kwargs.keys():
            V0 = kwargs["V0"]
        else:
            V0 = -80 * pq.mV
            
        if "segment" in kwargs.keys():
            segment = kwargs["segment"]
        else:
            segment = 0
            
        if "ImSignal" in kwargs.keys():
            ImSignal = kwargs["ImSignal"]
        else:
            ImSignal = "Im_prim_1"
            
        if "VmSignal" in kwargs.keys():
            VmSignal = kwargs["VmSignal"]
        else:
            VmSignal = "Vm_sec_1"
            
        if "RawImSignal" in kwargs.keys():
            RawImSignal = kwargs["RawImSignal"]
        else:
            RawImSignal = "Im_prim_C"
            
        if "name" in kwargs.keys():
            name = kwargs["name"]
    
    if len(blocks)> 1:
        ivrampBlock = ephys.average_blocks(*blocks, segment = segment, analog = [ImSignal,VmSignal, RawImSignal], name=name)
        
        if isinstance(VmSignal, str):
            VmSignalNdx = neoutils.get_index_of_named_signal(ivrampBlock.segments[0],VmSignal)
        else:
            VmSignalNdx = VmSignal
        
        if not isinstance(V0, pq.Quantity):
            V0 *= ivrampBlock.segments[0].analogsignals[VmSignalNdx].units
        
        ivrampBlock.segments[0].analogsignals[VmSignalNdx] += V0
        
        ivrampBlock.name = name
        
    else:
        name = blocks[0].name
        
        if name is None:
            cframe = inspect.getouterframes(inspect.currentframe())[1][0]
            try:
                for (k,v) in cframe.f_globals.items():
                    if not type(v).__name__ in ("module","type", "function", "builtin_function_or_method"):
                        if v is blocks[0] and not k.startswith("_"):
                            name = k
            finally:
                del(cframe)
                
        desc = "ivramp block"
        
        if blocks[0].description is not None:
            desc += " of %s" % blocks[0].description
            
        elif blocks[0].name is not None:
            desc += " of %s" % blocks[0].name
            
        ivrampBlock = neo.Block(name=name, description = desc)
        
        seg = neo.Segment(name = blocks[0].segments[segment].name, \
                            description = blocks[0].segments[segment].description)
                
        if isinstance(ImSignal, str):
            try:
                ImSignalNdx = neoutils.get_index_of_named_signal(blocks[0].segments[0], ImSignal)
            except Exception as e:
                raise RuntimeError("%s signal not found" % ImSignal)
            
        else:
            ImSignalNdx = ImSignal
            
        if isinstance(VmSignal, str):
            try:
                VmSignalNdx = neoutils.get_index_of_named_signal(blocks[0].segments[0], VmSignal)
            except Exception as e:
                raise RuntimeError("%s signal not found" % VmSignal)
        
        else:
            VmSignalNdx = VmSignal
        
        if isinstance(RawImSignal, str):
            try:
                RawImSignalNdx = neoutils.get_index_of_named_signal(blocks[0], RawImSignal)
            except Exception as e:
                raise RuntimeError("%s signal not found" % RawImSignal)
            
        else:
            RawImSignalNdx = RawImSignal
            
        seg.analogsignals.append(blocks[0].segments[segment].analogsignals[ImSignalNdx].copy())
        seg.analogsignals.append(blocks[0].segments[segment].analogsignals[VmSignalNdx].copy() + V0)
        seg.analogsignals.append(blocks[0].segments[segment].analogsignals[RawImSignalNdx].copy())
        
        
        ivrampBlock.append(seg)
        
    epoch.name = "IVRamp"
    
    ivrampBlock.segments[0].epochs.append(epoch)
    
    return ivrampBlock

def guessIVrampEpoch(data, duration=0.16 * pq.s, segment = 0, VmSignal="Vm_sec_1"):
    if isinstance(data, neo.Block):
        if isinstance(VmSignal, str):
            VmSignal = neoutils.get_index_of_named_signal(data.segments[segment], VmSignal)
            
        sig = data.segments[segment].analogsignals[VmSignal]
        
    elif isinstance(data, neo.Segment):
        if isinstance(VmSignal, str):
            VmSignal = neoutils.get_index_of_named_signal(data[segment])
            
        sig = data[segment].analogsignals[VmSignal]
        
    elif isinstance(data, neo.AnalogSignal):
        sig = data
        
    else:
        raise TypeError("Expecting an AnalogSignal, Segment, or Block; got %s instead" % type(data).__name__)
           
    rampEndTime = sig.times[np.argmax(sig)]
    rampStartTime = rampEndTime - duration
    
    return neo.Epoch(times = rampStartTime, durations = duration, labels="IVRamp", units = pq.s, name="IVRamp")
        
    
    
    
    
def IVRampAnalysis(data, **kwargs):
    """Performs analysis of I(V) curves in V-ramp experiments (in I-clamp).
    
    Positional parameters:
    ---------------------
    data = neo.Block with current-clamp I-V ramp experiment data organized in 
        segments (sweeps) and containing two mandatory analogsignals: membrane 
        voltage and membrane current. The actual ramp may occur within a region
        (epoch) of the signal.
        
        This may be an average of a series of Block objects (see average_ivramps).
        
    Keyword parameters:
    -------------------
    test = neo.Block as data; when present, then "data" block is considered the 
        "control", and peak normalization of the Im signal in "test" will be made
        against the peak Im in the "data" block.
        
        Typically "test" data would be generted by V ramp experiments in the 
        presence of a drug (or some other condition).
        
        Optional, default is None.
        
    subtract = neo.Block as data or test; when present, its membrane current 
        signal will be subtracted from data (and test if present) prior to 
        analysis.
        
        Optional, default is None.
        
    segment = int: segment index that must be valid for data, and also for test
        and subtract blocks when these are given.
        
        Optional: default is 0 (i.e. use the first segment in data, test and 
        subtract)
        
    epoch = neo.Epoch that defines the actual time interval sindide the segments, 
        where the Vm ramp has occurred; the times must be valid for all neo.Block
        objects passed to the function.
        
        The neo.Epoch object may define more than one time interval. When this
        happens, only the FIRST time interval is used.
        
        Alternatively, the epoch can be specified as a tuple or list of two 
        elements: (start_time, duration). Both values need to be real scalars
        or python quantities, in seconds. In either case they must be compatible
        with the time base in the data.
        
        Optional, default is None. When None, the data Block is expected to 
        contain an Epoch named "IVRamp" (this is taken care of automatically by 
        the average_ivramps function).
        
        If there are several epochs named "IVRamp", the first one is used
        
    ImSignal = valid index (int) or name (str) of the leak-subtracted current.
    
        Optional, default is "Im_prim_1"
    
    VmSignal = valid index (int) or name (str) of the membrane voltage current
    
        Optional, default is "Vm_sec_1"
        
    temperature = temperature as a real scalar or python quantity in degC units
    
        Optional, default is 33 degC
        
    externalCa = concentration of external Ca2+ (either real scalar or python quantity in mM units)
        
        Optional, default is 2.5 mM
        
    ivbase_start, ivbase_end = times (python quantities in s) of the Im baseline 
        used for normalization of the I(V) curve
        
        Optional, defaults are 0.12 and 0.13 s
        
    v_tol, i_tol ;  Vm and Im tolerance for detection of values about zero
    
        Optional; defaults are 1 * pq.mV and 10 * pq.pA, respectively.
        
    name = str (data set name)
    
        Optional, default is "" (the empty string)
        
    rs_shift: scalar or python Quantity (MOhm) for the Rs shift between control 
        and test (technically it should be zero)
        
        Optional, default is 0 * pq.MOhm
        
    integration = sequence of Vmin and Vmax for the I(V) integration
        optional, default is (Vm.min(), Erev)
        
    Vmin, Vmax  = scalars or python quantities (in mV) for the limits of the Vm
        domain for curve fitting.
        
        Optional, default is Vm.min() and calculated Erev.
        
    Returns:
    --------
    
    A neo.Block with analysis results organized in segments, as follows:
        segments[0] = analysis of the "data"
        segments[1] = analysis of the "test" (if given)
    
        In each segment, the annotations contain scalar values of the analysis result,
        whereas the analogsignals contain the I(V) curves, fitted I(V) curves and
        their peak-normalized versions.
    
        For the "test" data set (when given), the Im curves are normalized to 
        the peak value in "data" data set (which in this case is taken as "control")
        
    The annotations attribute of the result block contain the values of the 
    parameters passed to the function call (for the record).
        
    Side effects:
    ------------
    
    Generates two I(V) plots: one for raw and fitted curves, the other one for
    peak-normalized curves (raw and fitted).
    
    These plots can be exported to SVG files for further editing.
    
    NOTE: To plot selected I(V) curves, use plots.plotZeroCrossedAxes function
    with analog signls selected from the result.
    
    If "name" is given, then results are also written to a csv file in the 
    current directory, named after the value of "name".
    
    NOTE: Talbot & Sayer seems to be a better fit
        
    """
    
    from scipy.integrate import quad
    
    # define the defaults
    test        = None
    subtract    = None
    segment     = 0
    ImSignal    = "Im_prim_1"
    VmSignal    = "Vm_sec_1"
    epoch       = None
    t_start     = None
    t_stop      = None
    data_set_name = ""
    
    temperature = 33 * pq.degC
    externalCa  = 2.5* pq.mM
    
    # NOTE: 2017-10-06 15:55:01
    # used to calculate peak-normalized I-V curves
    ivbase_start = 0.12*pq.s
    ivbase_end   = 0.13*pq.s
    
    # NOTE: 2017-10-07 23:08:27
    # variables for calculating Im short-circuit (Isc), emf, Erev, slope conductance
    # (at Isc), chord coductance (at peak Im), V1/2
    
    v_tol = 1 * pq.mV
    i_tol = 10 * pq.pA
    
    rs_shift = 0 * pq.MOhm
    
    if not isinstance(data, neo.Block):
        raise TypeError("Expecting first argument to be a neo.Block object; got %s instead" % (type(data).__name__))
    
    # 1) parse & check var-keyword parameters
    keywords = ["test", "subtract", "segment", "epoch", "ImSignal", \
                "VmSignal", "temperature", "externalCa", "ivbase_start", "ivbase_end",\
                    "v_tol", "i_tol", "name", "rs_shift", "Vmin", "Vmax", "integration"]
    
    # ### BEGIN parse parameters
    # 1.1) parse arguments
    if len(kwargs) > 0:
        for k in kwargs.keys():
            if k not in keywords:
                raise ValueError("Unexpected keyword argument: %s" % k)
        
        if "integration" in kwargs.keys():
            integration = kwargs["integration"]
            
        else:
            integration = None
            
        if "test" in kwargs.keys():
            test = kwargs["test"]
            if not isinstance(test, (neo.Block, None)):
        
                raise TypeError("test was expected to be a neo.Block object, or None; got %s instead" % (type(test).__name__))
            
        if "subtract" in kwargs.keys():
            subtract = kwargs["subtract"]
            if not isinstance(subtract, (neo.Block, None)):
                raise TypeError("subtract was expected to be a neo.Blockobject, or None; got %s instead" % (type(subtract).__name__))
            
        if "segment" in kwargs.keys():
            segment = kwargs["segment"]
            
        if "ImSignal" in kwargs.keys():
            ImSignal = kwargs["ImSignal"]
            
        if "VmSignal" in kwargs.keys():
            VmSignal = kwargs["VmSignal"]
            
        if "epoch" in kwargs.keys():
            epoch = kwargs["epoch"]
            if not isinstance(epoch, (neo.Epoch, None, tuple, list)):
                raise TypeError("epoch ws expected to be a neo.Epoch, a tuple, a list, or None; got %s instead" % (type(epoch).__name__))
            
        if "temperature" in kwargs.keys():
            temperature = kwargs["temperature"]
            
            if isinstance(temperature, numbers.Real):
                temperature *= pq.degC
                
            elif isinstance(temperature, pq.Quantity):
                if temperature.dimensionality != (1*pq.degC).dimensionality:
                    raise TypeError("temperature was expected to be in degC units, got %s instead" % (temperature.dimensionality.__str__()))
                
            else:
                raise TypeError("temperature was expected to be in degC or a real scalar (undimensioned); got %s instead" % (type(temperature).__name__))
            
        if "externalCa" in kwargs.keys():
            externalCa = kwargs["externalCa"]
            
            if isinstance(externalCa, numbers.Real):
                externalCa *= pq.mM
                
            elif isinstance(externalCa, pq.Quantity):
                if externalCa.dimensionality != (1*pq.mM).dimensionality:
                    raise TypeError("External Ca2+ concentration was expected to be given in mM units; got %s instead" % (externalCa.dimensionality.__str__()))
                
            else:
                raise TypeError("external Ca2+ concentration was expected to be a python quantity in mM or a scalar real (undimensioned); got %s instead" % (type(externalCa).__name__))
            
            
        if "v_tol" in kwargs.keys():
            v_tol = kwargs["v_tol"]
            
            if isinstance(v_tol, numbers.Real):
                v_tol *= pq.mV
                
            elif isinstance(v_tol, pq.Quantity):
                if v_tol.dimensionality != (1*pq.mV).dimensionality:
                    raise TypeError("v_tol must be a real scalar or a python Quantity with units of mV")
                
            else:
                raise TypeError("v_tol must be a real scalar or a python Quantity with units of mV")
            
        if "i_tol" in kwargs.keys():
            i_tol = kwargs["i_tol"]
            
            if isinstance(i_tol, numbers.Real):
                i_tol *= pq.pA
            
            elif isinstance(i_tol, pq.Quantity):
                if i_tol.dimensionality != (1*pq.pA).dimensionality:
                    raise TypeError("i_tol must be a real scalar or a python Quantity with units of pA")
                
            else:
                raise TypeError("i_tol must be a real scalar or a python Quantity with units of pA")
            
        if "name" in kwargs.keys():
            data_set_name = kwargs["name"]
            
        else:
            data_set_name = ""
            
        if "rs_shift" in kwargs.keys():
            rs_shift = kwargs["rs_shift"]
            
            if isinstance(rs_shift, numbers.Real):
                rs_shift *= pq.MOhm
                
            elif isinstance(rs_shift, pq.Quantity):
                if rs_shift.dimensionality != (1*pq.MOhm).dimensionality:
                    raise TypeError("When rs_shift is given as a python quantity it should be in MOhm; %s was received instead" % rs_shift.dimensionality.string)
                
            else:
                raise TypeError("rs_shift must be a real scalar or a pyton Quantity in MOhm; got %s instead" % type(rs_shift).__name__)
            
        if "Vmin" in kwargs.keys():
            Vmin = kwargs["Vmin"]
            
        else:
            Vmin = None
            
        if "Vmax" in kwargs.keys():
            Vmax = kwargs["Vmax"]
            
        else:
            Vmax = None
            
    if segment >= len(data.segments) or segment < 0:
        raise ValueError("Invalid segment specified (%d); should be between %d and %d" % (segment, 0, len(data.segments)-1))
    
    if test is not None:
        if segment >= len(test.segments) or segment < 0:
            raise ValueError("Invalid segment specified (%d); should be between %d and %d" % (segment, 0, len(test.segments)-1))
        
    if subtract is not None:
        if segment >= len(subtract.segments) or segment < 0:
            raise ValueError("Invalid segment specified (%d); should be between %d and %d" % (segment, 0, len(subtract.segments)-1))
        

    if isinstance(ImSignal, str):
        try:
            ImSignal = neoutils.get_index_of_named_signal(data.segments[segment], ImSignal)
            
        except Exception as e:  
            raise ValueError("%s signal not found" % ImSignal)
        
    if isinstance(VmSignal, str):
        try:
            VmSignal = neoutils.get_index_of_named_signal(data.segments[segment], VmSignal)
            
        except Exception as e:
            raise ValueError("%s signal not found" % VmSignal)
        
    if test is not None:
        if ImSignal >= len(test.segments[segment].analogsignals):
            raise ValueError("Im signal index %d is invalid for the test block" % ImSignal)
        
        if VmSignal >= len(test.segments[segment].analogsignals):
            raise ValueError("Vm signal index %d is invalid for the test Block" % VmSignal)
    

    if subtract is not None:
        if ImSignal >= len(subtract.segments[segment].analogsignals):
            raise ValueError("Im signal index %d is invalid for the subtract block" % ImSignal)
        
        if VmSignal >= len(subtract.segments[segment].analogsignals):
            raise ValueError("Vm signal index %d i invalid for the subtract Block" % VmSignal)
    
    if epoch is None:
        # no epoch has been passed as parameter to the function call 
        # check for a suitable one in data's relevant segment
        if len(data.segments[segment].epochs) == 0:
            raise TypeError("No epoch has been speicfied and the first argument does not contain an epoch in segment %d" % (segment))
        
        ee = [e for e in data.segments[segment].epochs if e.name =="IVRamp"]
        
        if len(ee) == 0:
            raise TypeError("no epoch has been specified, and the first argument does not contain an epoch named 'IVRamp' in segment %d" % (segment))
        
        else:
            epoch = ee[0]
            
    if isinstance(epoch, (tuple, list)):
        t_start = epoch[0]
        duration = epoch[1]
        
        if isinstance(t_start, pq.Quantity):
            if t_start.dimensionality != (1*pq.s).dimensionality:
                raise TypeError("epoch start has wrong dimensionality (%s); expecting 's'" % (t_start.dimensionality.__str__()))
                
        elif isinstance(t_start, number.Real):
            t_start *= pq.s
            
        else:
            raise TypeError("epoch start was expected to be a real scalar or a python quantity in 's'; got %s instead" % (type(t_start).__name__))
        
        if isinstance(duration, pq.Quantity):
            if duration.dimensionality != (1*pq.s).dimensionality:
                raise TypeError("epoch duration has wrong dimensionality (%s); expecting 's'" % (t_start.dimensionality.__str__()))
                
        elif isinstance(duration, number.Real):
            duration *= pq.s
            
        else:
            raise TypeError("epoch duration was expected to be a real scalar or a python quantity in 's'; got %s instead" % (type(t_start).__name__))
        
        t_stop = t_start + duration
        
    elif isinstance(epoch, neo.Epoch):
        # check is there is only one time interval defined in epoch
        if epoch.times.size == 1:
            t_start = epoch.times
            
        elif epoch.times.size > 1: # more than one time interval; take the first
            t_start = epoch.times[0]
        
        else:
            raise ValueError("The epoch does not specify a start time! If no epoch has been passed to the function call then check epochs in segment %d of the first argument." % (segment))
            
        if epoch.durations.size == 1:
            t_stop = t_start + epoch.durations
            
        elif epoch.durations.size > 1:
            t_stop = t_start + epoch.durations[0]
            
        else:
            raise ValueError("The epoch does not specify a duration! If no epoch has been passed to the function call then check epochs in segment %d of the first argument." % (segment))
        
    # 1.2) check that t_start/t_stop are OK
    #       this would be redundant if epoch was retrieved from data, but 
    #       shouldn't slow things down
    
    if t_start < data.segments[segment].analogsignals[ImSignal].t_start:
        raise ValueError("The IV ramp cannot begin (%g) before data Im signal begins (%g)" % (t_start, data.segments[segment].analogsignals[ImSignal].t_start))
    
    if t_stop > data.segments[segment].analogsignals[ImSignal].t_stop:
        raise ValueError("The IV ramp cannot end (%g) after data Im signal ends (%g)" % (t_stop, data.segments[segment].analogsignals[ImSignal].t_stop))
    
    if test is not None:
        if t_start < test.segments[segment].analogsignals[ImSignal].t_start:
            raise ValueError("The IV ramp cannot begin (%g) before test Im signal begins (%g)" % (t_start, test.segments[segment].analogsignals[ImSignal].t_start))
        
        if t_stop > data.segments[segment].analogsignals[ImSignal].t_stop:
            raise ValueError("The IV ramp cannot end (%g) after test Im signal ends (%g)" % (t_stop, test.segments[segment].analogsignals[ImSignal].t_stop))
        
    
    if subtract is not None:
        if t_start < subtract.segments[segment].analogsignals[ImSignal].t_start:
            raise ValueError("The IV ramp cannot begin (%g) before subtracted Im signal begins (%g)" % (t_start, subtract.segments[segment].analogsignals[ImSignal].t_start))
        
        if t_stop > subtract.segments[segment].analogsignals[ImSignal].t_stop:
            raise ValueError("The IV ramp cannot end (%g) after subtracted Im signal ends (%g)" % (t_stop, subtract.segments[segment].analogsignals[ImSignal].t_stop))
        
    #### END parse parameters 
    
    #### BEGIN analysis
    # 2) finally do what we're here to do
    
    # 2.1) extract Im and Im regions corresponding to the Vm ramp, in Control
    #

    #### BEGIN Analysis of (control) data
    im_control = data.segments[segment].analogsignals[ImSignal].time_slice(t_start, t_stop)
    
    data_name = data.name
    
    # subtract ivramp is there is one specified
    if subtract is not None:
        im_control -= subtract.segments[segment].analogsignals[ImSignal].time_slice(t_start, t_stop)
        data_name = "%s with %s subtracted" % (data_name, subtract.name)
        data_set_name = "%s with %s subtracted" % (data_set_name, subtract.name)
    
    vm_control = data.segments[segment].analogsignals[VmSignal].time_slice(t_start, t_stop)
    
    # 2.1.1) peak-normalize it, store the peak Im current value
    i_min = im_control.time_slice(ivbase_start, ivbase_end).mean()
    
    im_control_peak = im_control.min()
    
    im_control_peak_normalized = ephys.peak_normalise_signal(im_control, i_min, im_control_peak)
    
    im_control_peak_normalized.name = "%s peak normalized" % im_control.name
    
    # 2.1.2) macroscopic analysis for conductance (slope & chord), Erev, emf, 
    # Vm at half-max activation, Vm at peak of I(V) curve, Im at short-circuit
    # etc
    control_macroscopic = macroscopic_conductance(vm_control, im_control, **kwargs)
    
    iv_fig = plt.figure()
    iv_norm_fig = plt.figure()
    
    iv_fig.show()
    iv_norm_fig.show()
    
    plots.plotZeroCrossedAxes(vm_control.magnitude, im_control.magnitude, fig=iv_fig, legend=[data_name], newPlot=True)
    
    plots.plotZeroCrossedAxes(vm_control.magnitude, im_control_peak_normalized.magnitude, ylabel="Im normalized", fig = iv_norm_fig, legend=[data_name], newPlot=True)
    
    # 2.1.3) fit the control I-V curve with the Talbot & Sayer model
    try:
        im_control_fit_TS, im_control_fit_TS_params, im_control_fit_TS_rsq, *_ = \
            fit_Talbot_Sayer(vm_control, im_control, t=temperature, ca_out = externalCa)
        
        im_control_fit_TS.name="Talbot-Sayer %s" % im_control.name
        
        im_control_fit_TS.description = "Talbot-Sayer fit for %s, %s" % (data_name, im_control.name)
        
        # also peak-normalize the fitted curve
        i_min = im_control_fit_TS.time_slice(ivbase_start, ivbase_end).mean()
        
        im_control_fit_TS_peak = im_control_fit_TS.min()
        
        im_control_fit_TS_peak_normalized = ephys.peak_normalise_signal(im_control_fit_TS, i_min, im_control_fit_TS_peak)
        
        im_control_fit_TS_peak_normalized.name = "%s peak normalized" % im_control_fit_TS.name
        
        plots.plotZeroCrossedAxes(vm_control.magnitude, im_control_fit_TS.magnitude, fig = iv_fig, legend=["%s Talbot & Sayer fit" % data_name])
        plots.plotZeroCrossedAxes(vm_control.magnitude, im_control_fit_TS_peak_normalized.magnitude, fig = iv_norm_fig, legend=["%s Talbot & Sayer fit peak-normalized" % data_name])
    
    except Exception as e:
        im_control_fit_TS = None
        traceback.print_exc()
        
        
    # 2.1.4) fit control I(V) with Markwardt & Nilius model
    try:
        im_control_fit_MN, im_control_fit_MN_params, im_control_fit_MN_rsq, *_ = \
            fit_Markwardt_Nilius(vm_control, im_control, \
                    g = control_macroscopic["g_slope"], \
                    Erev = control_macroscopic["emf"],\
                    Vhmax = control_macroscopic["VmHalfMaxAct"], \
                    slope = 1)
        
        im_control_fit_MN.name="Markwardt-Nilius %s" % im_control.name
        
        im_control_fit_MN.description = "Markwardt-Nilius fit for %s, %s" % (data_name, im_control.name)
        
        i_min = im_control_fit_MN.time_slice(ivbase_start, ivbase_end).mean()
        
        im_control_fit_MN_peak = im_control_fit_MN.min()
        
        im_control_fit_MN_peak_normalized = ephys.peak_normalise_signal(im_control_fit_MN, i_min, im_control_fit_MN_peak)
        
        im_control_fit_MN_peak_normalized.name = "%s peak normalized" % im_control_fit_MN.name
        
        plots.plotZeroCrossedAxes(vm_control.magnitude, im_control_fit_MN.magnitude, fig = iv_fig, legend=["%s Markwardt & Nilius fit" % data_name])
        
        plots.plotZeroCrossedAxes(vm_control.magnitude, im_control_fit_MN_peak_normalized.magnitude, fig = iv_norm_fig, legend=["%s Makwardt & Nilius fit peak-normalized" % data_name])
    
    except Exception as e:
        im_control_fit_MN = None
        traceback.print_exc()
    
    # 2.1.5) generate a new Block with the analogsignals generated so far -- 
    # NOTE: conveniently, these all have a common time base
    
    result = neo.Block()
    
    if data_set_name is not None and len(data_set_name) > 0:
        result.name = data_set_name
    
    else:
        result.name = "IV analysis"
    
    control_segment = neo.Segment(name="IV analysis result for %s" % data_name, index = 0)
    
    control_segment.analogsignals.append(im_control)
    control_segment.analogsignals.append(vm_control)
    control_segment.analogsignals.append(im_control_peak_normalized)
    
    control_segment.epochs.append(neo.Epoch(times=im_control.t_start, durations = im_control.duration.rescale(pq.s), name="IVRamp"))

    control_segment.annotate(PeakIm=im_control_peak, \
                            macroscopic=control_macroscopic)

    
    # NOTE: integrate fit curves for the Control condition (area under the curve
    # on the given Vm interval)
    # NOTE: Marwardt & Nilius fits: g slope, Erev and activation slope
    # NOTE: Talbot & Sayer fits: V half-max (on activation side), activation slope, 
    #                           scale and [Ca] in
    if integration is None:
        if control_macroscopic["Erev"] is None:
            int_c_limits = (float(vm_control.min()), float(vm_control.max()))
        else:
            int_c_limits = (float(vm_control.min()), float(control_macroscopic["Erev"]))
            
    else:
        if isinstance(integration[0], pq.Quantity) and integration[0].dimensionality == (1*pq.mV).dimensionality \
            and isinstance(integration[1], pq.Quantity) and integration[1].dimensionality == (1*pq.mV).dimensionality:
                int_c_limits = (float(integration[0].magnitude), float(integration[1].magnitude))
                
        elif all([isinstance(i, numbers.Real) for i in integration]):
            int_c_limits = (float(integration[0]), float(integration[1]))
            
        else:
            raise TypeError("Integration limits were expected to be real scalars or Quantities in mV")
            
    if im_control_fit_TS is not None:
        control_segment.analogsignals.append(im_control_fit_TS)
        control_segment.analogsignals.append(im_control_fit_TS_peak_normalized)
        
        control_TS = OrderedDict()
        
        control_TS["PeakImFit"]         = im_control_fit_TS_peak
        control_TS["activation_slope"]  = im_control_fit_TS_params[0]
        control_TS["scale"]             = im_control_fit_TS_params[1]
        control_TS["Ca_in"]             = im_control_fit_TS_params[2]
        control_TS["V0.5"]              = im_control_fit_TS_params[3]
        control_TS["rsq"]               = im_control_fit_TS_rsq
        
        # NOTE: integrate the Talbot & Sayer fit curve
        intg = quad(lambda x, a, b, c, x0: models.Talbot_Sayer(x, a, b, c, x0, t=temperature, o=externalCa), 
                    int_c_limits[0], int_c_limits[1], 
                    tuple(im_control_fit_TS_params))
        
        control_TS["integral"] = intg[0]
        control_TS["integral_error"] = intg[1]
        
        control_segment.annotations["Talbot_Sayer"] = control_TS
        
    else:
        control_TS = OrderedDict()
        
        control_TS["PeakImFit"]         = np.nan
        control_TS["activation_slope"]  = np.nan
        control_TS["scale"]             = np.nan
        control_TS["Ca_in"]             = np.nan
        control_TS["V0.5"]              = np.nan
        control_TS["rsq"]               = np.nan
        control_TS["integral"]          = np.nan
        control_TS["integral_error"]    = np.nan
        
    control_TS_df = pd.DataFrame(control_TS, index=pd.Index(["Control_TS"]))

    if im_control_fit_MN is not None:
        control_segment.analogsignals.append(im_control_fit_MN)
        control_segment.analogsignals.append(im_control_fit_MN_peak_normalized)
        
        control_MN = OrderedDict()
        control_MN["PeakImFit"]         = im_control_fit_MN_peak
        control_MN["g_slope"]           = im_control_fit_MN_params[0]
        control_MN["Erev"]              = im_control_fit_MN_params[1]
        control_MN["V0.5"]              = im_control_fit_MN_params[2]
        control_MN["activation_slope"]  = im_control_fit_MN_params[3]
        control_MN["rsq"]               = im_control_fit_MN_rsq
        
        # NOTE: integrate the Markwardt & Nilius fit curve
        intg = quad(models.Markwardt_Nilius, int_c_limits[0], int_c_limits[1], 
                    tuple(im_control_fit_MN_params))
        
        control_MN["integral"] = intg[0]
        
        control_MN["integral_error"] = intg[1]
        
        control_segment.annotations["Markwardt_Nilius"] = control_MN
        
    else:
        control_MN = OrderedDict()
        control_MN["PeakImFit"]         = np.nan
        control_MN["g_slope"]           = np.nan
        control_MN["Erev"]              = np.nan
        control_MN["V0.5"]              = np.nan
        control_MN["activation_slope"]  = np.nan
        control_MN["rsq"]               = np.nan
        control_MN["integral"]          = np.nan
        control_MN["integral_error"]    = np.nan
        
    control_MN_df = pd.DataFrame(control_MN, index=pd.Index(["Control_MN"]))

    result.segments.append(control_segment)
    
    #### END Analysis of (control) data
    
    #### BEGIN Analysis of test (drug) data
    # now, do the analysis for test (if test was passed)
    if test is not None:
        test_name = test.name
        
        im_test = test.segments[segment].analogsignals[ImSignal].time_slice(t_start, t_stop)
        
        if subtract is not None:
            im_test -= subtract.segments[segment].analogsignals[ImSignal].time_slice(t_start, t_stop)
            test_name = "%s with %s subtracted" % (test_name, subtract.name)
    
        vm_test = test.segments[segment].analogsignals[VmSignal].time_slice(t_start, t_stop)
        
        if rs_shift != 0 * pq.MOhm:
            vm_test = rs_comp(im_test, vm_test, rs_shift)
            
            if Vmin is None:
                Vmin = vm_control.min()
                
            if Vmax is None:
                Vmax = vm_control.max()
        
        i_min = im_control.time_slice(ivbase_start, ivbase_end).mean()
        
        # normalize current during test (i.e. drug) to peak control value => peak-normalized I(V) during drug
        # NOTE: this represents the fraction of current NOT blocked by the drug
        # NOTE: the fraction blocked by the drug would be 1 - this
        im_test_normalized_to_control_peak = ephys.peak_normalise_signal(im_test, i_min, im_control_peak)
        im_test_normalized_to_control_peak.name = "%s peak normalized to Control" % test_name
        
        # get the maximal value of peak-normalized drug I(V)
        # NOTE: this is the fraction of the peak current NOT blocked by the drug
        im_test_peak_normalized_to_control = im_test_normalized_to_control_peak.max()
        
        # calculate the drug-sensitive fraction i.e. how much the drug has blocked
        # NOTE: this is the difference between peak-normalized control I(V) and peak-normalized drug I(V)
        # NOTE: im_control_peak_normalized was calculated above
        im_test_sensitive_fraction = im_control_peak_normalized - im_test_normalized_to_control_peak
        
        # get the value of the drug-sensitive fraction pf peak (IV)  = 1 - im_test_peak_normalized_to_control:
        # NOTE: the (1 * ...) creates a quantity of 1 * signal units
        # NOTE: the results is a signal with one element (hence it has name and description attributes)
        im_test_peak_sensitive_fraction = (1*im_test_peak_normalized_to_control.units) - im_test_peak_normalized_to_control
        
        im_test_sensitive_fraction.name = "%s-sensitive" % test_name
        
        im_test_sensitive_fraction.description = "%s-sensitive fraction of %s" % (test_name, data_name)
        
        test_macroscopic = macroscopic_conductance(vm_test, im_test, **kwargs)
        test_macroscopic["IpeakNorm"] = im_test_peak_normalized_to_control
        test_macroscopic["%s-sensitive peak fraction" % test_name] = im_test_peak_sensitive_fraction
        
        plots.plotZeroCrossedAxes(vm_test.magnitude, im_test.magnitude, fig=iv_fig, legend=[test_name])
        
        plots.plotZeroCrossedAxes(vm_test.magnitude, im_test_normalized_to_control_peak.magnitude, fig=iv_norm_fig, legend=["%s normalized to %s peak" % (test_name, data_name)])
        
        
        # fit the test I-V curve with the Talbot & Sayer model
        try:
            # fit I(V) durinfg drug with Talbot & Sayer model
            im_test_fit_TS, im_test_fit_TS_params, im_test_fit_TS_rsq, *_ = fit_Talbot_Sayer(vm_test, im_test, t=temperature, ca_out = externalCa)
            
            im_test_fit_TS.name = "Talbot-Sayer %s" % test_name
            
            im_test_fit_TS_peak = im_test_fit_TS.min()
            
            im_test_fit_TS.description = "Talbot-Sayer of %s, %s" % (test_name, im_test.name)
            
            i_min = im_test_fit_TS.time_slice(ivbase_start, ivbase_end).mean()
            
            # normalize the fit to the max of control fit (peak-normalized fit)
            # NOTE: im_control_fit_TS_peak was calculated above
            # NOTE: this represents the fraction of I(V) fit cure NOT blocked by the drug
            # NOTE: the fraction blocked by the drug would be 1 - this
            im_test_fit_TS_normalized_to_control_peak = ephys.peak_normalise_signal(im_test_fit_TS, i_min, im_control_fit_TS_peak)
            
            im_test_fit_TS_normalized_to_control_peak.name = "%s peak normalized to fitted Control" % im_test_fit_TS.name
            
            # get the maximum value of the peak-normalized fit => the max I(V) fit NOT blocked
            im_test_fit_TS_peak_normalized_to_control = im_test_fit_TS_normalized_to_control_peak.max()
            
            # get the drug-sensitive fraction of the maximum of I(V) fit curve
            im_test_fit_TS_peak_normalized_sensitive_fraction = (1 * im_test_fit_TS_peak_normalized_to_control.units) - im_test_fit_TS_peak_normalized_to_control
            
            plots.plotZeroCrossedAxes(vm_test.magnitude, im_test_fit_TS.magnitude, fig=iv_fig, legend=["%s Talbot & Sayer fit" % test_name])
            
            plots.plotZeroCrossedAxes(vm_test.magnitude, im_test_fit_TS_normalized_to_control_peak.magnitude, fig=iv_norm_fig, legend=["%s Talbot & Sayer fit normalized to %s peak" % (test_name, data_name)])
        
        except Exception as e:
            im_test_fit_TS = None
            traceback.print_exc()
            
        # fit the test I-V curve with the Markwardt & Nilius model
        # NOTE: see NOTE annotations in the above block of code for Talbot & Sayer
        try:
            im_test_fit_MN, im_test_fit_MN_params, im_test_fit_MN_rsq, *_ = \
                fit_Markwardt_Nilius(vm_test, im_test, \
                    g = test_macroscopic["g_slope"], \
                    Erev = test_macroscopic["emf"], \
                    Vhmax = test_macroscopic["VmHalfMaxAct"], \
                    slope = 1)
        
            im_test_fit_MN.name = "Markwardt-Nilius %s" % test_name
            
            im_test_fit_MN.description = "Markwardt-Nilius fit of %s, %s" % (test_name, im_test.name)
            
            im_test_fit_MN_peak = im_test_fit_MN.min()
            
            i_min = im_test_fit_MN.time_slice(ivbase_start, ivbase_end).mean()
            
            im_test_fit_MN_normalized_to_control_peak = ephys.peak_normalise_signal(im_test_fit_MN, i_min, im_control_fit_MN_peak)
            
            im_test_fit_MN_normalized_to_control_peak.name = "%s peak normalized to fitted Control" % im_test_fit_MN.name
            
            im_test_fit_MN_peak_normalized_to_control = im_test_fit_MN_normalized_to_control_peak.max()
            
            im_test_fit_MN_peak_normalized_sensitive_fraction = (1 * im_test_fit_MN_peak_normalized_to_control.units) - im_test_fit_MN_peak_normalized_to_control
            
            plots.plotZeroCrossedAxes(vm_test.magnitude, im_test_fit_MN.magnitude, fig=iv_fig, legend=["%s Markwardt & Nilius fit" % test_name])
            
            plots.plotZeroCrossedAxes(vm_test.magnitude, im_test_fit_MN_normalized_to_control_peak.magnitude, fig=iv_norm_fig, legend=["%s Marwardt & Nilius fit normalized to %s peak" % (test_name, data_name)])
        
        except Exception as e:
            im_test_fit_MN = None
            traceback.print_exc()
            
        # NOTE: collect measurements and derived signals into a new segment
            
        #test_result  = neo.Block(name="IVRamp analysis for %s" % test.name)
        test_segment = neo.Segment(name="IV analysis result for %s" % test_name, index=0)
    
        i_min = im_test_fit_TS.time_slice(ivbase_start, ivbase_end).mean()
        
        test_segment.analogsignals.append(im_test)
        test_segment.analogsignals.append(vm_test)
        test_segment.analogsignals.append(im_test_normalized_to_control_peak)
        test_segment.analogsignals.append(im_test_sensitive_fraction)
        
        test_segment.annotate(macroscopic = test_macroscopic )
        
        test_segment.epochs.append(neo.Epoch(times = im_test.t_start, durations = im_test.duration.rescale(pq.s), name="IVRamp"))
        
        if integration is None: # perform integration (area under the curve)
            if test_macroscopic["Erev"] is None:
                int_t_limits = (float(vm_test.min()), float(vm_test.max()))
            else:
                int_t_limits = (float(vm_test.min()), float(test_macroscopic["Erev"]))
                
        else:
            if isinstance(integration[0], pq.Quantity) and integration[0].dimensionality == (1*pq.mV).dimensionality \
                and isinstance(integration[1], pq.Quantity) and integration[1].dimensionality == (1*pq.mV).dimensionality:
                    int_t_limits = (float(integration[0].magnitude), float(integration[1].magnitude))
                    
            elif all([isinstance(i, numbers.Real) for i in integration]):
                int_t_limits = (float(integration[0]), float(integration[1]))
                
            else:
                raise TypeError("Integration limits were expected to be real scalars or Quantities in mV")

        if im_test_fit_TS is not None:
            test_segment.analogsignals.append(im_test_fit_TS)
            test_segment.analogsignals.append(im_test_fit_TS_normalized_to_control_peak)
            
            test_TS = OrderedDict()
            test_TS["PeakImFit"]        = im_test_fit_TS_peak
            test_TS["activation_slope"] = im_test_fit_TS_params[0]
            test_TS["scale"]            = im_test_fit_TS_params[1]
            test_TS["Ca_in"]            = im_test_fit_TS_params[2]
            test_TS["V0.5"]             = im_test_fit_TS_params[3]
            test_TS["rsq"]              = im_test_fit_TS_rsq
            
            # NOTE: integrate the Talbot & Sayer fit for the drug I(V)
            intg = quad(lambda x, a, b, c, x0: models.Talbot_Sayer(x, a, b, c, x0, t=temperature, o = externalCa), 
                        int_t_limits[0], int_t_limits[1], 
                        tuple(im_test_fit_TS_params))
            
            test_TS["integral"] = intg[0]
            test_TS["integral_error"] = intg[1]
            
            # NOTE: if Control was fitted (which it should have) then calculate
            # drug-sensitive fraction of the fits
            if im_control_fit_TS is not None:
                # test-sensitive fraction on the fitted curves
                im_test_sensitive_fraction_fit_TS = im_control_fit_TS_peak_normalized - im_test_fit_TS_normalized_to_control_peak
                im_test_sensitive_fraction_fit_TS.name="%s-sensitive fraction" % test_name
                im_test_sensitive_fraction_fit_TS.description="%s-sensitive fraction, Talbot & Sayer fit" % test_name
                
                # NOTE: the drug-sensitive fraction of area under the fitted I(V) curve
                # is 1 - Inegral(test)/Integral(control)
                test_TS["%s-sensitive Integral" % test_name] = 1 - test_TS["integral"]/control_TS["integral"]
                
                # NOTE: done above
                test_TS["%s-sensitive peak fraction" % test_name] = im_test_fit_TS_peak_normalized_sensitive_fraction
                
                test_TS["PeakImFitNorm"] = im_test_fit_TS_peak_normalized_to_control
                
                test_segment.analogsignals.append(im_test_sensitive_fraction_fit_TS)
                
            else:
                test_TS["%s-sensitive Integral" % test_name] = np.nan
                
                test_TS["%s-sensitive peak fraction" % test_name] = np.nan
                
                test_TS["PeakImFitNorm"] = np.nan
                
                
            test_segment.annotations["Talbot_Sayer"] = test_TS
            
            
        else:
            test_TS = OrderedDict()
            test_TS["PeakImFit"]        = np.nan
            test_TS["activation_slope"] = np.nan
            test_TS["scale"]            = np.nan
            test_TS["Ca_in"]            = np.nan
            test_TS["V0.5"]             = np.nan
            test_TS["rsq"]              = np.nan
            test_TS["integral"]         = np.nan
            test_TS["integral_error"]   = np.nan
            test_TS["%s-sensitive Integral" % test_name] = np.nan
            test_TS["%s-sensitive peak fraction" % test_name] = np.nan
            test_TS["PeakImFitNorm"] = np.nan
            
        test_TS_df = pd.DataFrame(test_TS, index = pd.Index(["%s_TS" % test_name]))
            
            
        if im_test_fit_MN is not None:
            test_segment.analogsignals.append(im_test_fit_MN)
            test_segment.analogsignals.append(im_test_fit_MN_normalized_to_control_peak)
            
            test_MN = OrderedDict()
            test_MN["PeakImFit"]        = im_test_fit_MN_peak
            test_MN["g_slope"]          = im_test_fit_MN_params[0]
            test_MN["Erev"]             = im_test_fit_MN_params[1]
            test_MN["V0.5"]             = im_test_fit_MN_params[2]
            test_MN["activation_slope"] = im_test_fit_MN_params[3]
            test_MN["rsq"]              = im_test_fit_MN_rsq
            
            # NOTE: integrate the Markwadt & Nilius fit for the drug I(V)
            intg = quad(models.Markwardt_Nilius, int_t_limits[0], int_t_limits[1], 
                        tuple(im_test_fit_MN_params))
            
            test_MN["integral"] = intg[0]
            
            test_MN["integral_error"] = intg[1]
            
            if im_control_fit_MN is not None:
                # test-sensitive fraction on the fitted curves
                im_test_sensitive_fraction_fit_MN = im_control_fit_MN_peak_normalized - im_test_fit_MN_normalized_to_control_peak
                im_test_sensitive_fraction_fit_MN.name="%s-sensitive fraction" % test_name
                im_test_sensitive_fraction_fit_MN.description = "%s-sensitive fraction, Markwardt & Nilius fit" % test_name
                
                test_MN["%s-sensitive Integral" % test_name] = 1 - test_MN["integral"]/control_MN["integral"]
                
                test_MN["%s-sensitive peak fraction" % test_name] = im_test_fit_MN_peak_normalized_sensitive_fraction
                
                test_MN["PeakImFitNorm"] = im_test_fit_MN_peak_normalized_to_control
                
                test_segment.analogsignals.append(im_test_sensitive_fraction_fit_MN)
                
            else:
                test_MN["%s-sensitive Integral" % test_name] = np.nan
                test_MN["%s-sensitive peak fraction" % test_name] = np.nan
                test_MN["PeakImFitNorm"] = np.nan
                
            test_segment.annotations["Markwardt_Nilius"] = test_MN
            
        else:
            test_MN = OrderedDict()
            test_MN["PeakImFit"]        = np.nan
            test_MN["g_slope"]          = np.nan
            test_MN["Erev"]             = np.nan
            test_MN["V0.5"]             = np.nan
            test_MN["activation_slope"] = np.nan
            test_MN["rsq"]              = np.nan
            test_MN["%s-sensitive Integral" % test_name] = np.nan
            test_MN["%s-sensitive peak fraction" % test_name] = np.nan
            test_MN["PeakImFitNorm"] = np.nan
            
        test_MN_df = pd.DataFrame(test_MN, index = pd.Index(["%s_MN"%test_name]))
        
        result.segments.append(test_segment)
        
    else:
        test_TS = OrderedDict()
        test_TS["PeakImFit"]        = np.nan
        test_TS["activation_slope"] = np.nan
        test_TS["scale"]            = np.nan
        test_TS["Ca_in"]            = np.nan
        test_TS["V0.5"]             = np.nan
        test_TS["rsq"]              = np.nan
        test_TS["integral"]         = np.nan
        test_TS["integral_error"]   = np.nan
        test_TS["%s-sensitive Integral" % test_name] = np.nan
        test_TS["%s-sensitive peak fraction" % test_name] = np.nan
        test_TS["PeakImFitNorm"] = np.nan
        test_TS_df = pd.DataFrame(test_TS)
        
        test_MN = OrderedDict()
        test_MN["PeakImFit"]        = np.nan
        test_MN["g_slope"]          = np.nan
        test_MN["Erev"]             = np.nan
        test_MN["V0.5"]             = np.nan
        test_MN["activation_slope"] = np.nan
        test_MN["rsq"]              = np.nan
        test_MN["%s-sensitive Integral" % test_name] = np.nan
        test_MN["%s-sensitive peak fraction" % test_name] = np.nan
        test_MN["PeakImFitNorm"] = np.nan
        test_MN_df = pd.DataFrame(test_MN)
        
    #### END Analysis of test (drug) data
        
    block_annot = OrderedDict()
    
    block_annot["segment"]          = segment
    block_annot["ImSignal"]         = ImSignal
    block_annot["VmSignal"]         = VmSignal
    block_annot["RampEpochStart"]   = t_start
    block_annot["RampEpochEnd"]     = t_stop
    block_annot["temperature"]      = temperature
    block_annot["externalCa"]       = externalCa
    block_annot["ivbase_start"]     = ivbase_start
    block_annot["ivbase_end"]       = ivbase_end
    block_annot["v_tol"]            = v_tol
    block_annot["i_tol"]            = i_tol
    block_annot["rs_shift"]         = rs_shift
    #block_annot["control_Vmin_fit"] = 
    block_annot["control_int_start"]= int_c_limits[0]
    block_annot["control_int_end"]  = int_c_limits[1]
    block_annot["test_int_start"]   = int_t_limits[0]
    block_annot["test_int_end"]     = int_t_limits[1]
    
        
    result.annotations = block_annot
    
    # ### END analysis
    
    #if result.name is not None and len(result.name) > 0:
        #resultsToCsv(result)
        
    result_df = pd.concat([control_TS_df, test_TS_df, control_MN_df, test_MN_df])
    
    return result, result_df

def resultsToCsv(data, filebasename=None):
    import csv
    
    if filebasename is None:
        if data.name is not None and len(data.name) > 0:
            filebasename = strutils.str2symbol(data.name)
            
        else:
            cframe = inspect.getouterframes(inspect.currentframe())[1][0]
            
            try:
                for (k, v) in cframe.f_globals.items():
                    if not type(v).__name__ in ("module", "type", "function", "builtin_function_or_method"):
                        if v is data and not k.startswith("_"):
                            filebasename = strutils.str2symbol(k)
                            
            finally:
                del(cframe)
                filebasename = "data"
                
    else:
        filebasename = strutils.str2symbol(filebasename)
                
    (name,extn) = os.path.splitext(filebasename)
    
    if len(extn) == 0 or extn != ".csv":
        filename = filebasename + ".csv"
    else:
        filename=filebasename
        
    #print(extn)
    
    if len(data.segments) == 0:
        raise ValueError ("Nothing to save!")
    
    header = ["Data:", data.name]
    
    with open(filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter="\t")
        
        writer.writerow(header)
        
        for segment in data.segments:
            writer.writerow([segment.name])
            writer.writerow(["macroscopic analysis"])
            for k,v in segment.annotations["macroscopic"].items():
                if isinstance(v, pq.Quantity):
                    writer.writerow([k, v.magnitude, v.dimensionality.string])
                else:
                    writer.writerow([k,v])
                    
            writer.writerow([""])
            
            writer.writerow(["Markwardt & Nilius fit"])
            for k,v in segment.annotations["Markwardt_Nilius"].items():
                if isinstance(v, pq.Quantity):
                    writer.writerow([k, v.magnitude, v.dimensionality.string])
                else:
                    writer.writerow([k,v])
                
            writer.writerow([""])
            
            writer.writerow(["Talbot & Sayer fit"])
            for k,v in segment.annotations["Talbot_Sayer"].items():
                if isinstance(v, pq.Quantity):
                    writer.writerow([k, v.magnitude, v.dimensionality.string])
                else:
                    writer.writerow([k,v])
                
            writer.writerow([""])
            writer.writerow([""])
        
        writer.writerow(["Call parameters"])
        for k,v in data.annotations.items():
            if isinstance(v, pq.Quantity):
                writer.writerow([k, v.magnitude, v.dimensionality.string])
            else:
                writer.writerow([k,v])
    
        

def fit_Frank_Fuortes(lat, I, fitrheo=False, xstart = 0, xend = 0.1, npts = 100):
    """Performs the actual fit of the Frank & Fuortes 1956.
    See rheobase_latency for details.
    
    Arguments:
    ==========
    lat = data vector (1D numpy array) with latencies
    I   = data vector (1D numpy array) with injected current
    fitrheo (boolean, optional, default is False)
    xstart = initial value for the time domain of the fitted function
    xend   = end value for the time domain of the fitted function
    npts   = number of points in the fitted function
    
    Returns:
    =======
    Irh  = apparent rheobase
    fit_tau = membrane time constans (fitted)
    fit_rheobase = fitted rheobase
    popt = fitted parameters for the Frank & Fuortes equation
    rsq  = coefficient of determination of the fit
    sst  = total sum of squares
    sse  = sum of square residuals
    pcov = covariance matrix in the fitted parameters
    perr = standard deviations for the fitted prameter values
    ii   = the actual dependent variable see NOTE (2) in rheobase_latency documentation
    xx   = time domain of the fitted function
    yy   = the dependent variable of the fitted function
    
    """
    def _Frank_Fuortes(x, tau, x_):
        """In their 1956 paper, Irheo is a constant experimentally measured.
        Use this to get the membrane time constant only.
        """
        return 1-np.exp(-(x-x_)/tau)
        #return 1-np.exp(-x/tau)
    
    def _Frank_Fuortes2(x, irh, tau, x_):
        """By rearranging the _Frank_Fuortes equation
        one can also get a fitted value for Irheobase 
        """
        return (1-np.exp(-(x-x_)/tau)) / irh
        #return (1-np.exp(-x/tau)) / irh
    
    lat_ok = np.where(np.isfinite(lat))[0]
    
    delay = np.nanmin(lat)
    
    Irh = I[lat_ok[0]]

    decay = 0.1 # blue-sky initial guess
    
    if xstart is not None and xend is not None and npts is not None:
        xx = np.linspace(xstart, xend, npts)
    
    else:
        xx = None
    
    yy = None
    
    if fitrheo:
        
        ii = 1/I
        
        popt, pcov = optimize.curve_fit(_Frank_Fuortes2, \
                                        lat[lat_ok], 
                                        ii[lat_ok], \
                                        [Irh, decay, delay])
        
        yfit = _Frank_Fuortes2(lat[lat_ok], *popt)
        
        
        if xx is not None:
            yy = 1 / _Frank_Fuortes2(xx, *popt)
        
        fit_rheobase = popt[0]
        
        fit_tau = popt[1]
        
    else:
        ii = Irh/I
        
        popt, pcov = optimize.curve_fit(_Frank_Fuortes, \
                                        lat[lat_ok], \
                                        ii[lat_ok], \
                                        [decay, delay])
        
        yfit = _Frank_Fuortes(lat[lat_ok], *popt)
    
        if xx is not None:
            yy = 1 / _Frank_Fuortes(xx, *popt)
        
        fit_tau = popt[0]
        
        fit_rheobase = Irh
    
    sst = np.sum((ii[lat_ok] - ii[lat_ok].mean()) ** 2.)# total sum of squares

    sse = np.sum((yfit - ii[lat_ok]) ** 2.) # sum of squared residuals

    rsq = 1 - sse/sst # coeff of determination

    perr = np.sqrt(np.diag(pcov))
    
    return Irh, fit_tau, fit_rheobase, popt, rsq, sst, sse, pcov, perr, ii, xx, yy


def leak_comp(Im, base_start, base_end, copy=True):
    """Corrects leak subtraction (for unstable recordings)
    
    Arguments:
    =========
    
    Im AnalogSignal with Im data -- typically the time-slice containg the I(V) 
            during a ramp
            
    base_start, base_end: python Quantities (in units of "s") 
            indicating, respectively, the start and end of the 
            baseline (typically, for Ca2+ I-V curves, this is corresponding to
            -80 to -60 mV range)
            
    copy: boolean, optional default is True:
    
        when True, returns a copy of the Im with new leak subtraction
        when False, Im is modified IN PLACE
        
        
    Returns
    ========
    
    A copy of Im if copy is True, or the Im modified in place if copy is False.
    """
    
    Ioffset  = Im.time_slice(base_start, base_end).mean()
    
    if copy:
        return Im - Ioffset
    
    else:
        Im -= Ioffset
        
        return Im
        
def rs_comp(i0, v0, dR, copy=True):
    """Corrects Vm for change in Rm
    i0 = analogsignal in pA
    v0 = analogsignal in mV
    dR = change in Rs (in MOhm, i.e. pq.MOhm)
    
    copy : boolean optional, default is True
        
    Returns:
    
        a COPY of v0 if copy is True, else, v0 modified IN PLACE
        
    NOTE: see Marty & Neher 1995, Tight seal whole-cell recording, 
        in Signle-channel recording 2nd Ed.
    
    """
    if not isinstance(dR, pq.Quantity):
        dR *= pq.MOhm
        
    
    if copy:
        return v0 - (i0*dR).rescale(pq.mV)

    else:
        v0 -= (i0*dR).rescale(pq.mV)
        return v0
    

        
