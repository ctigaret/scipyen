# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

""" Steps towards a unified frameworks for model fitting.

TODO/FIXME: This module is intended to supersede the models.py module (hopefully
not before too long). For now, it is only EXPERIMENTAL and UNDER DEVELOPMENT

DO NOT USE YET

The intention is to use ModelExpression objects instead of the functions in 
models.py. Until this is done, stick with models.py and curvefitting.py modules!

TODO: 2022-10-25 23:21:06
# implement fit(self) methods!!!

"""
from abc import (ABCMeta, ABC, abstractmethod)
import typing
import numbers
import traceback
import tokenize
from io import BytesIO
from contextlib import (contextmanager, ContextDecorator,)
import inspect
from inspect import getmro
from functools import (partial, wraps)
#import six
from traitlets import Bunch
from pprint import pprint
import numpy as np
import scipy
#import sympy as sp
#import sympy.parsing.sympy_parser as symparser
import quantities as pq
from scipy import cluster, optimize, signal, integrate #, where
import vigra
import neo
from core.traitcontainers import DataBag
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
from core.utilities import reverse_mapping_lookup

from core import models # we're still developing this one

#@contextmanager

class ModelExpression(object):
    """Class decorator to pass an expression to the model.
    
    Can use this instead of directly hardcoding the expression in the definition
    if the fit model ::class::.
    
    This is useful to dynamically create new FitModel ::classes:: 
    
    WARNING: Either way, the expression must be buit in terms of the parameter
    names built in the model ::class:: (without the 'self.' prefix)
    
    """
    def __init__(self, expression:str="", modules = (np, scipy, cluster, optimize, signal, integrate)):
        # NOTE: the decorator already receives a ::class:: object 
        self._expression_ = expression
        self._modules_ = modules
        
    def __call__(self, klass):
        """Decorates the ::class::
        """
        if not isinstance(self._expression_, str) or len(self._expression_.strip()) == 0:
            klass._model_expression_ = ""
            klass._sympexpr_ = None
            return klass
        
        if len(klass._parameter_names_) == 0:
            klass._model_expression_ = ""
            klass._sympexpr_ = None
            return klass
        
        klass._model_expression_ = self._expression_
        klass._call_expression_  = self._adapt_tokens_(klass)
        
        return klass
    
    def _adapt_tokens_(self, klass:type):
        ret = list()
        expr = klass._model_expression_
        
        for tokeninfo in tokenize.tokenize(BytesIO(expr.encode('utf-8')).readline):
            if tokeninfo.type == tokenize.NAME:
                if tokeninfo.string in klass._parameter_names_:
                    ret.extend([(tokenize.NAME, "self.%s" % tokeninfo.string)])
                else:
                    newtokstr = self._make_canon_(tokeninfo.string)
                    if tokeninfo.string == newtokstr:
                        ret.append(tokeninfo)
                    else:
                        ret.extend([(tokenize.NAME, newtokstr)])
                        
            else:
                ret.append(tokeninfo)
                        
        return tokenize.untokenize(ret).decode('utf-8')
    
    def _make_canon_(self, name:str):
        frame = inspect.currentframe()
        #print("globals in current frame:\n")
        #pprint(frame.f_globals)
        #print("locals in current frame:\n")
        #pprint(frame.f_locals)
        for m in self._modules_:
            if name in m.__dict__:
                # name is a member of module 'm'
                # now check if module 'm' is available here
                if m in frame.f_globals.values():
                    # 'm' i availbale => get the symbol under which it is bound
                    # in the f_globals
                    
                    # this is either a str, a tuple (when 'm' is bound to more
                    # than one symbol) or None when 'm' has not been imported
                    # here - in the latter case we do nothing
                    # TODO 2021-09-04 22:05:27 FIXME: try to import 'm' if not
                    # already imported
                    m_name = reverse_mapping_lookup(frame.f_globals, m)
                    
                    if isinstance(m_name, tuple):
                        # m_name is a tuple if 'm' is bound under several symbols
                        # get the first one
                        if len(m_name):
                            m_name = m_name[0]
                        else: # this should never occur
                            m_name = None
                        
                    if m_name is None:
                        continue # see TODO/FIXME above
                
            # first, try to find if m is in this :class: module namespace
            # as an alias
            
                return "%s.%s" % (m_name, name)

            
        return name

class FitModelMeta(type):
    """:Metaclass: that generates properties for the model parameters.
    Each model parameter gets three read/write properties named after the 
    parameter's name or suffixed with '_lb' or '_ub', respectively, for the
    initial value, lower and upper bound values.
    
    To be used with any :class: derived from FitModel, where a _parameter_names_
    attribute is defined as a tuple of strings (the names of the model's parameters)
    """
    def __new__(klass, name, bases, classdict):
        if name not in (c.__name__ for c in bases):
            if "_parameter_names_" in classdict:
                for paramname in classdict["_parameter_names_"]:
                    props = klass.make_param_properties(paramname, name)
                    classdict[paramname]           = props[0]
                    classdict["%s_lb" % paramname] = props[1]
                    classdict["%s_ub" % paramname] = props[2]
        
        return super().__new__(klass, name, bases, classdict)
        
    def __init__(klass, name, bases, classdict):
        super().__init__(name, bases, classdict)
        
    @staticmethod
    def make_param_properties(param, classname):
        def fget(instance):
            return instance.initial[param]
        
        def fset(instance, val):
            instance.initial[param] = val
            
        def fget_lower(instance):
            return instance.lower[param]
            
        def fset_lower(instance, val):
            instance.lower[param] = val
            
        def fget_upper(instance):
            return instance.upper[param]
            
        def fset_upper(instance, val):
            instance.upper[param] = val
            
        initial = property(fget=fget,       fset=fset,       doc = "Initial value of %s model parameter '%s'"     % (classname, param))
        lower   = property(fget=fget_lower, fset=fset_lower, doc = "Lower bound value of %s model parameter '%s'" % (classname, param))
        upper   = property(fget=fget_upper, fset=fset_upper, doc = "Upper bound value of %s model parameter '%s'" % (classname, param))
        
        return (initial, lower, upper)

class FitModel(metaclass=FitModelMeta):
    """Top parent :class: for all fit models
    
    To drive from it:
    1) define a new :class: with the body where AT LEAST the :class: attribute
        '_parameter_names_' is defined as a tuple of strings (the parameter names)
        
        See, for example, the ExponentialDecay :class: where '_parameter_names_'
        is: 
            ("offset", "a", "x0", "tau")
            
    2) decorate the new :class: with @ModelExpression parameterized with:
        * a str: the model expression containing the parameters named as in the
            '_parameter_names_' :class: attribute
            
            For example, in the case of ExponentialDecay this is:
            
                'a * exp(-(x-x0)/tau) + offset'
            
        * a list of imported modules where the functions used in the expression
            are defined.
            
            These modules must be accessible from the namespace where the new 
            :class: is defined.
            
            For the model classes defined in this module, by default this
            contains the following modules imported here:
            
            np, scipy, cluster, optimize, signal, integrate
            
            with 'np' an alias to numpy
    
    
    """
    _parameter_names_   = tuple()
    _default_initial_   = list()
    _default_lower_     = list()
    _default_upper_     = list()
    _model_expression_  = str()
    
    def __init__(self, **kwargs):
        self.initial = DataBag()
        self.lower   = DataBag()
        self.upper   = DataBag()
        # NOTE: 2021-09-02 15:06:03
        # override this in derived for a more sophisticated initialization
        for k, name in enumerate(self._parameter_names_):
            self.initial[name] = kwargs.get(name, self._default_initial_[k])
            self.lower[name]   = kwargs.get(name, self._default_lower_[k])
            self.upper[name]   = kwargs.get(name, self._default_upper_[k])
            

    #def __repr__(self):
        #pass
        

    def __call__(self, x):
        if isinstance(self._call_expression_, str) and len(self._call_expression_.strip()):
            #print(self._call_expression_)
            return eval(self._call_expression_)
    
    def fit(self, x):
        pass
    
    @property
    def expression(self):
        return str(self._model_expression_)
    
    @property
    def parameter_names(self):
        """Model parameter names wrapped in a tuple
        """
        return self._parameter_names_
    
    @property
    def defaults(self) -> Bunch:
        return Bunch(((name, Bunch(initial=self._default_initial_[k], lower=self._default_lower_[k], upper=self._default_upper_[k])) for k, name in enumerate(self._parameter_names_)))
    
    @property
    def parameters(self) -> Bunch:
        """Maps parameter names to initial, lower and upper bounds
        """
        return Bunch(((name, Bunch(initial=self.initial[name], lower=self.lower[name], upper=self.upper[name])) for k, name in enumerate(self._parameter_names_)))
    
    @parameters.setter
    def parameters(self, val=None, **kwargs):
        if isinstance(val, dict):
            for name in self._parameter_names_:
                p = val.get(name, None)
                if isinstance(p, dict):
                    if "initial" in p:
                        self.initial[name] = p["initial"]
                        
                    if "lower" in p:
                        self.lower[name] = p["lower"]
                        
                    if "upper" in p:
                        self.upper[name] = p["upper"]
                        
        elif isinstance(val, (tuple, list)):
            if all((isistance(v, numbers.Number) for v in val)):
                if len(val) == len(self._parameter_names_):
                    for k, name in enumerate(self._parameter_names_):
                        self.initial[name] = val[k]
                        
            elif all((isinstance(v, (tuple, list)) and len(v) == len(self._parameter_names_) for v in val)):
                for k in range(len(val)):
                    for i, name in enumerate(self._parameter_names_):
                        v = val[k][i]
                        if k == 0:
                            self.initial[name] = v
                                
                        elif k == 1:
                            self.lower[name] = v
                            
                        else:
                            self.upper[name] = v
                            
@ModelExpression('a * exp(-(x-x0)/tau) + offset')
class ExponentialDecay(FitModel):
    """Fit model :class: decorated with ModelExpression.
    
    """
    _parameter_names_   = ("offset", "a", "x0", "tau")
    _default_initial_   = (0., 1., 0., 0.1)
    _default_lower_     = tuple([None] * len(_parameter_names_))
    _default_upper_     = tuple([None] * len(_parameter_names_))
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
            
class ExponentialDecay2(FitModel):
    """Demonstrates defining a new fit model without a decorator.
    The attribute _model_expression_ needs to be harcoded in the definition
    """
    _parameter_names_   = ("offset", "a", "x0", "tau")
    _default_initial_   = (0., 1., 0., 0.1)
    _default_lower_     = tuple([None] * len(_parameter_names_))
    _default_upper_     = tuple([None] * len(_parameter_names_))
    _model_expression_  = 'a * exp(-(x-x0)/tau) + offset'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
            
    def __call__(self, x:np.ndarray):
        return self.a * np.exp(-(x-self.x0)/self.tau) + self.offset
    
    def fit(self, x):
        pass
    

# FIXME/TODO 2022-10-21 00:21:24
# do NOT delete from here to end just yet
# we may want to hang on to models.py (imported by this module) for backward
# compatibility

# def check_rise_decay_params(x):
#     """Returns the number of decay components for a exp-rise-multi-decay transient.
#     x = iterable with model parameters (see exp_rise_multi_decay())
#     """
#     if np.remainder(len(x)-3, 2) != 0:
#         raise ValueError("Unexpected number of elements in the parameters vector; must be 2n + 3 where n is the number of decay components; instead got %d elements" % len(parameters))
#     
#     return (len(x)-3) // 2
# 
# def generic_exp_decay(x, offset, scale, delay, decay):
#     """Realizes f(x) = scale * exp(-(x-delay)/decay) + offset
#     """
#     
#     return scale * np.exp(-(x-delay)/decay) + offset
# 
# def alphaFunction(x, parameters):
#     """
#     The Alpha function: a single exponential rise and decay, both with the same 
#     time-constant (τ):
#     
#     y = a + b⋅(x-x₀)⋅exp(-(x-x₀)/τ)/τ if x-x₀ >= 0 and a elsewhere
#     
#     where 
#         a  is the offset;
#     
#         b  is the scale;
#     
#         x₀ is the delay ("onset");
#     
#         τ  is the time constant
#     
#     
#     Parameters:
#     ===========
#     x: predictor (independent variable) - 1D numpy ndarray
#     
#     parameters: 1D numeric sequence (tuple, list, numpy array) with four 
#         elements a, b, x₀, τ
#     
#     Example: (run in Scipyen's console)
#     ========
#     
#     from core import models
#     
#     x = np.linspace(0.0,1.0, 1000);
#     
#     parameters = [0, -1, 0.05, 0.01];
#     
#     y = alphaFunction(x, parameters)
#     
#     plt.plot(x,y)
#     
#     """
#     
#     # make sure x is a 1D array (vector)
#     
#     x = x.flatten()
#     
#     # unpack parameters
#     a, b, x0, tau = parameters
#     
#     xt = (x-x0)/tau
#     
#     y = np.full_like(x, a)
#     
#     y[xt>=0] = a + b * xt[xt>=0] * np.exp(-xt[xt>=0])
#     
#     return y
#     
# def exp_rise_multi_decay(x, parameters, returnDecays = False):
#     """ Realization of a transient signal with a single exponential rise (r) and
#         n exponential decays (d1..dn), at an onset (delay) x0 and a given 
#         "DC" component (offset) o: 
# 
#         y = (1 - exp( -(x-x0)/r ) * ( a_0     * exp( -(x-x0)/d_0) + 
#                                       a_1     * exp( -(x-x0)/d_1) +
#                                       .                           +
#                                       .                           +
#                                       a_(n-1) * exp( -(x-x0)/d_(n-1) ) ) + o               (1)
# 
# 
#         where:
# 
#             x0        = onset (delay) of the transient; only makes sense when x0 >= 0
#             r         = rising phase time constant; 
#             a_0...a_(n-1)   = scale for each of the n decay components;
#             d_0...d_(n-1)   = time constant for each of the decay components;
#             o         = offset (`DC' component)
#             
#             
#     Arguments:
#             
#     x   =   the independent (predictor) data (represents the definition domain for 
#             the model function e.g., a time vector)
#             This is NOT a pyton quantity, just a 1D numpy array.
#             
#     parameters = 1D numeric sequence (tuple, list, numpy array) with minimum five elements 
#             such that len(parameters) satisfies 2 * n + 3 where n >=1 is the number of decays
#             in the model.
#             
#             ATTENTION: ORDER OF MODEL PARAMETERS:
#             
#             Model parameter values are interpreted to be given in the following order:
#             
#             a0, d0, <a1, d1, ...an, dn>, o, r, x0
#             
#             For each decay component there are two parameters: 
#             a (scale) and d (time constant).
#             
#             Decay components are given in order (scale0, decay0, scale1, decay1, etc)
#             and are followed by offset (o), rise time constant (r) and delay (x0).
#             
#             For example, [a0, sd0, a1, d1, o, r, x0] specifies a transient signal 
#             with two decay components, (a0, d0, a1, d1)
#             
#             The time constants (r, d_0, d_1, ...) and the delay x0 are considered to
#             be given in the same time units as x. The offset and scale parameters
#             are considered to be given in the units of the signal.
#             For code simplicity I do NOT use python quantities here, so appropriate scaling
#             must be applied to the parameters before passing them to this function.
#             
#     
#     Returns:
#     
#     y = the model curve
#     
#     yd = a list of model curves for each scaled decay component; it has as many curves
#         as there are 'a' and 'd' elements in parameters
#     
#     """
#     
#     # NOTE: call np.squeeze on the argument BEFORE passing it to this function !!!
#     
#     nDecays = check_rise_decay_params(parameters)
#     
#     if isinstance(x, numbers.Real):
#         # for using this function with scipy.integrate.quad, which evaluates the
#         # model function at a single point
#         #x = x - parameters[-1]
#         
#         if x < 0:
#             return 0
#         
#         y = 1 - np.exp(-x/parameters[-2])
#         
#         yd = list()
#         
#         for k in range(nDecays):
#             yd.append(parameters[2*k] * np.exp(1-x/parameters[2*k+1]))
#             
#         y += sum(yd)
#         
#         return y
#             
#         #if returnDecays:
#             #return y, yd
#             
#         #else:
#             #return y
#         
#     else:
#         if x.ndim > 1:
#             raise ValueError("Vector x must have exactly one dimension (i.e., a column vector)")
#         
#         x = x - parameters[-1] # apply the delay to the time domain
#         
#         y = np.zeros(x.shape)
#         
#         #print(y.shape)
#         
#         yd = np.tile(y[:,np.newaxis], (1,nDecays))
#         
#         
#         y[x>=0] = 1 - np.exp(-x[x>=0]/parameters[-2])
#         
#         for k in range(nDecays):
#             yd[x>=0, k] = parameters[2*k] * np.exp(1-x[x>=0]/parameters[2*k+1])
#             
#         y *= np.sum(yd,axis=1) 
#         y += parameters[-3]
#         
#         if returnDecays:
#             return y, yd
#         else:
#             return y
# 
# def compound_exp_rise_multi_decay(x, parameters, returnDecays = False):
#     """Compound transient signal -- linear sum of delayed single transient signals
#     Arguments:
#         x = 1D predictor vector
#         
#         parameters = a list of parameter sequences where each sequence is as 
#                     defined for the parameters argument of exp_rise_multi_decay
#         
#     Returns:
#         y   = realization of the compound signal model curve
#         yc  = list of individual transient models within the compound signal
#         ycd = list of individual decay components
#         
#         NOTE: for a single-component EPSCaT, y and yc contain the same data
#         
#     """
#     #print("parameters", parameters)
#     
#     # NOTE: 2017-12-26 00:06:38
#     # this is so that the function can be used with scipy.integrate.quad
#     if isinstance(x, numbers.Real):
#         y = 0
#         #print("parameters: ", parameters)
#         #print("x: ", x)
#         for p in parameters:
#             #print("p: ", p)
#             y += exp_rise_multi_decay(x, p)
#         
#         return y # NOTE: returns one scalar !!!
#     
#     else:
#         if x.ndim > 1:
#             raise ValueError("Vector x must have exactly one dimension (i.e., a column vector)")
#         
#         y = np.zeros(x.shape)
#         
#         yc = list()
#         
#         ycd = list()
#         
#         for p in parameters:
#             #print("p", p)
#             
#             (yc_, ycd_) = exp_rise_multi_decay(x, p, True)
# 
#             y += yc_
#             
#             yc.append(yc_)
#             
#             ycd.append(ycd_)
# 
#         if returnDecays:
#             return y, yc, ycd
#         
#         else:
#             return y, yc
#     
# def Markwardt_Nilius(x, g, e, h, s):
#     """Markwardt & Nilius model for voltage-gated Ca2+ channels I-V relationship
#     See Markwardt & Nilius (1988), J Physiol (London)
#     
#     Parameters:
#     ========== 
#     x   = column vector (np.array) with membrane voltage (Vm) data
#     
#     The model parameters are (real scalars, corresponding to units in parentheses):
#     
#     g  = slope conductance (nS)
#     
#     e  = extrapolated reversal potential (mV) of the current (from slope conductance)
#         i.e. same as Thevenin equivalent e.m.f.
#         
#     v  = Vm at half-maximal current activation (mV) (i.e. taken on the rising 
#         region of the I(V) curve)
#     
#     s  = slope parameter of Ca2+ channel activation (mV)
#     
#     Returns:
#     ======== 
#     
#     A column vector Im = f(Vm) were f is the Markwardt & Nilius model
#     
#     """
#     y = g * (x - e) / (1 + np.exp(-(x-h)/s))
#     
#     return y
# 
# def Xu_Lipscombe():
#     #Vm = membrane potential
#     #V0_5 = activation midpoint
#     #Erev = reversal potential
#     
#     #p1 = Ca2+ permability * [Ca2+]i * RT
#     #p2 = zF/RT with z = 2 valency
#     #F = Faraday constant
#     #R = gas constant
#     #T temperature in degK
#     #k = Boltzmann constant
#     
#     #I = p1 * p2**2 * Vm * (1 - exp(-(Vm-Erev * p2))/(1- exp(-(Vm * p2)))) / (1 + exp(-(Vm-V0_5)/k))
#     
#     pass
# 
# def Talbot_Sayer(x, a, b, c, x0, **kwargs):# t = 33 * pq.degC, o = 2.5 * pq.mM):
#     """
#     Talbot & Sayer model for voltage-gated Ca2+ channels I-V relationship.
#     
#     Boltzman squared, multiplied by Goldman-Hogdkin-Katz, 
#     see Talbot & Sayer 1996, J. Neurophysiol. 76(3):2120-2124
#     
#     Positional parameters:
#     =====================
#     
#     x   = 1D numpy array (vector): definition domain (e.g. membrane voltage)
#     
#     a   = real: initial value for Boltzman slope factor
#     
#     b   = real: initial scale value
#     
#     c   = real: initial value for internal Ca2+ concentration (in mM)
#     
#     x0  = real: initial value of onset ("shift")
#     
#     Var-keyword parameters 
#     ======================
#     
#     t   = python quantity: temperature in degrees Celsius (degC); default: 33 degC
#     
#     o   = python quantity: external Ca2+ concentration in mM; default: 2.5 mM
#     
#     Returns:
#     =======
#     A realization of the I-V model function in 
#     Talbot & Sayer 1996, J. Neurophysiol. 76(3):2120-2124
#     as a numpy vector
#     
#     
#     NOTE:
#     Do not use directly in curve fitting, as it expects more arguments
#     that the model parameters. The extra arguments are given as keyword
#     arguments. If used directly in fitting, then expected keyword arguments WILL
#     get their default values.
#     
#     """
#     from scipy import constants
#     
#     # default values
#     t_ = 33
#     o = 2.5 * pq.mM
#     
#     if len(kwargs) > 0:
#         if "t" in kwargs:
#             t = kwargs["t"]
#         
#             if isinstance(t, pq.Quantity) and t.dimensionality == (1*pq.degC).dimensionality:
#                 t_ = t.magnitude
#                 
#             elif isinstance(t, numbers.Real):
#                 t_ = t
#                 
#             else:
#                 raise TypeError("Was expecting 't' (temperature) as a real scalar or a python quantity in degC. got %s instead" % type(t).__name__)
#         
#         if "o" in kwargs:
#             o = kwargs["o"]
#             
#             if isinstance(o, numbers.Real):
#                 o *= pq.mM
#                 
#             else:
#                 if not isinstance(o, pq.Quantity) or o.dimensionality != (1*pq.mM).dimensionality:
#                     raise TypeError("Was expecting 'o' (external Ca2+ concentration) as a real scalar or a python quantity in mM; got %s instead" % type(o).__name__)
#             
#             
#     
#     T = constants.convert_temperature(t_, "Celsius", "Kelvin") * pq.degK
#     
#     F = constants.physical_constants["Faraday constant"][0] * pq.C/pq.mol
#     
#     R = constants.physical_constants["molar gas constant"][0] * pq.J/(pq.mol * pq.degK)
#     
#     k = F/(R*T) # NOTE: this is in C/J i.e. 1/V, because 1V  = 1J/C
#     
#     k = k.rescale(1/pq.mV) #  because x is in mV
#     
#     #print(k)
#     
#     #k = 0.0379
#     
#     # see Kay & Wong (1987) J. Physiol, 392:603-616
#     boltzman = 1 / (1 + np.exp(-a * k.magnitude * (x-x0)))**2
#     
#     ghkexp = np.exp(-2 * x * k.magnitude)
#     
#     # Goldman-Hogkin-Katz
#     ghk = x * b * (c - o.magnitude * ghkexp) / (1-ghkexp)
# 
#     return boltzman * ghk
# 
# def gaussianSum1D(x, *args, **kwargs):
#     """ Sum of shifted Gaussians in 1D.
#     
#     Implements:
#     
#         y = a0*exp(-((x-b0)/c0)^2) + a1*exp(-((x-b1)/c1)^2) + ...
#             ak*exp(-((x-bk)/ck)^2) + ...
#             an*exp(-((x-bn)/cn)^2) + d
#             
#         for a sum of shifted n+1 1D Gaussians on top of a common offset d
#     
#     Parameters:
#     ==========
#     
#     x = 1D numpy array: the domain of definition
#     
#     Var-positional parameters:
#     ==========================
#     
#     EXACTLY n * 3 + 1 elements: a0, b0, c0, ..., ak, bk, bk, ... an-1, bn-1, cn-1, d
#     
#     for n 1D Gaussian curves
#     
#     If packed in a sequence, it can be unpacked by assing it as a starred expression
#     in the function call.
#     
#     keyword parameters:
#     ===================
#     
#     components: bool, default False: 
#     
#                 when False, the function returns the compound Gaussian only, as 
#                             a numpy array ("column vector")
#             
#                 when True, the function returns a tuple containing the compound 
#                             Gaussian as above, and a matrix with each individual 
#                             Gaussian component in its columns
#     
#     """
#     #print("gaussianSum1D args: ", args)
#     
#     components = False
#     
#     if len(kwargs) and "components" in kwargs:
#         components = kwargs["components"]
#     
#     # NOTE: 2018-09-14 09:42:08
#     # find out how many gaussians are specified by the parameters
#     ngauss, rem = divmod(len(args), 3)
#     
#     if ngauss < 1 or rem != 1:
#         raise RuntimeError("There must be exactly n * 3 + 1; got %d instead" % len(args))
#     
#     #print(x.shape[0])
#     
#     #ygauss = np.full([x.shape[0], ngauss], 0)
#     ygauss = np.full([x.shape[0], ngauss], np.nan)
#     
#     #print("ygauss shape: ", ygauss.shape)
#     
#     for k in range(ngauss):
#         a, b, c = args[slice(k*3, k*3+3)]
#         ygauss[:,k] = a * np.exp(-((x-b)/c)**2)
#         
#     ret = np.nansum(ygauss, axis=1) + args[-1]
#     
#     #print("return shape: ", ret.shape)
#     
#     if components:
#         return ret, ygauss + args[-1]
#     
#     return ret
#     
#     
# def Frank_Fuortes(x, tau, x0):
#     """ Frank & Fuortes 1956 expression Irh/I = 1 - exp(-(t-t0)/tau)
#     
#     In the Frank & Fuortes 1956 paper, Irheo is a constant experimentally measured.
#     Use this to get the membrane time constant only.
#     
#     The original equation (1) is used for the determination of the 
#     membrane time-constant from strength-latency relationship.
#     
#     Irh/I = 1 - exp(-t/tau)                                         (1)
#     
#         where Irh (rheobase curent) is measured experimentally as the 
#         smallest I value where AP are fired.
#         
#     In practice, the following equation is used:
#     
#     Irh/I = 1 - exp(-(t-t0)/tau)                                    (2)
#         
#         where t0 is a small "delay" i.e., the smallest latency used in the 
#         experiment.
#         
#         This helps the fit as latency approaches 0.
#             
#     References:
#     
#     Frank & Fuortes (1956) Stimulation of spinal motoneurones with 
#     intracellular electrodes. J.Physiol. 134, 451-470
#     """
#     return 1-np.exp(-(x-x0)/tau)
#     #return 1-np.exp(-x/tau)
# 
# def Frank_Fuortes2(x, irh, tau, x0):
#     """ Implements 1/I = (1-exp(-t/tau)) / Irh 
#     
#     By rearranging the Frank & Fuortes 1956 equation
#     one can also get a fitted value for Irheobase 
#     
#     1/I = (1-exp(-t/tau)) / Irh                                     (2)
#     References:
#     
#     Frank & Fuortes (1956) Stimulation of spinal motoneurones with 
#     intracellular electrodes. J.Physiol. 134, 451-470
#     """
#     return (1-np.exp(-(x-x0)/tau)) / irh
#     #return (1-np.exp(-x/tau)) / irh
# 
#     
# 
