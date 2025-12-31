# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r""" Collection of 1D and nD functions and helper functions, for use in model fitting.

WARNING: This module is on its way to deprecation, and it wil be superseded by
modelfitting.py in the (hopefully not too distant) future.

For now, stick with THIS module.

NOTE: 2025-05-08 10:39:04

Parametric models are defined by functions taking one independent variable, ``𝑥`` 
(the predictor) and a set of coefficients, and implement the mathematical expression
to generate a waveform (dependent variable ``𝑦``). The mathematical expression
describes the dependency of 𝑦 on 𝑥 and on the model coefficients.

There functions are named in a way suggestive of the parametric model they implement.

For example, an exponential decay is defined by:

    ``y = exp(-(x)/τ)``                                         (1)
    
    thus requiring a single coefficient: τ
    
A biased and scaled version of (1) is:
    
    ``y = α + β × exp(-(x)/τ)``                                 (2)
    
    thus requiring three coefficients: α (the additive bias), β (the multiplicative
    bias, or 'scale'), and τ
    
A biased, scaled and shifted version of (1) is:

    ``y = α + β × exp(-(x-x₀)/τ)``                                 (3)
    
    and requires an additional coefficient: x₀ (the shift)
    
    Here, the shift is useful when the exponential process begins at some point
    AFTER the start of the predictor 𝑥
    
    
ATTENTION: Please decorate all model functions with the modelfunction decorator.
This will help locating/accessing these functions easily from other Scipyen
components.
"""
import typing, types
import numbers
import neo
import numpy as np
import sympy
from sympy import abc as symabc
import quantities as pq
import pandas as pd
import dataclasses
from core import scipyen_quantities as scq
from core.datasignal import DataSignal
from core.prog import (scipywarn, signature_as_dict, decorator, timefunc)
from core import utilities

Real: typing.TypeAlias = typing.Union[int, float, np.int64, np.float64]
Complex: typing.TypeAlias = typing.Union[complex, np.complex128]

def check_independent_variable(x:typing.Union[Real, np.ndarray], ndim:typing.Optional[int]=None):
    if not isinstance(x, (Real, np.ndarray)):
        raise TypeError(f"Independent variable 'x' has unexpected type: {type(x).__name__}")
    
    if isinstance(x, pq.Quantity):
        units['x'] = x.units
        x = x.magnitude
        
    if isinstance(ndim, int):
        if ndim < 1:
            raise ValueError(f"'ndim' expected >=1; instead, got {ndim}")
        if ndim == 1:
            if isinstance(x, np.ndarray):
                x = x.flatten()
        elif ndim > 1:
            assert x.ndim == ndim, f"Expecting 'x' with {ndim} dimensions; instead got an array with {x.ndim} dimensions"
        
    return x

@decorator
def modelfunction(f:typing.Callable, /, 
                  nvars:int=1, 
                  title:typing.Optional[str] = None ,
                  coefficients:typing.Optional[typing.Sequence[str]]=None,
                  coefficient_units:typing.Optional[dict]=None,
                  expression:typing.Optional[typing.Union[sympy.Basic, str]] = None,
                  **kwargs):
    r"""Decorator to tag a function as a mathematical model function.
A mathematical model function realizes a function of one or more independent 
variables based on a mathematical expression and a set of independent parameters.

The function returns an nD array where 1 <= n <= nvars (see below)

By using this decorator, model functions can be identified as such, regardless 
of the module (in Scipyen's tree) where they are defined.

This decorator sets adorns a model function with the following attributes:

'nvars': number of independent variables (e.g. 1D or nD function)

'title': A descriptive name, not bound by Python's rules for symbol composition

'coefficients': tuple of coefficient symbols as they appear in the mathematical
    model; these parameters are "fixed" for a given model instance and are 
    responsible for generating a "family" of models from the same mathematical
    expresison.

    These coefficients are also the ones that are determined in curve fitting.

    Some of the models involve a variable number of components (factors or terms)
    defined by the same mathematical expresison. Their coefficient symbols are
    tagged with a "*" to indicate this. Each such "starred" coefficient is counted
    ONCE. 

    ATTENTION: Python syntax forbids the use of more than one var-positional
    parameter (e.g. *args) in a function call. This means that, for an actual 
    function call, the starred coefficients need to be lumped together in a single
    var-positional parameter; it is up to the function code to deal with the 
    contents of this parameter.

'starred_coefficients': tuple of starred coefficient symbols.

'expression': a LaTeX string, or a sympy expression construct (i.e., a sympy.Basic
    or subclass of it):
    • The LaTeX string MUST be given EITHER as a 'raw' string, OR a string with 
    the LaTeX  escape characters ('\') escaped (i.e. use '\\' everywhere LaTeX 
    expects a single '\'). WARNING: LaTeX assumes package amsmath is in use.
    • The sympy expresion is currently used just for inspection purposes; no
    computation is performed involving sympy expressions.

'coefficient_units' (see below)

NOTE: These attributes can be accessed from within the model function code by
    assigning the function object to a local variable (e.g., 'self'). In turn,
    the function object is accessed from the globals() namespace as the object
    bound to the name of the function. 

    For example, say you've defined a model function 'func' decorated with this
    wrapper:

    @modelfunction(coefficients = ("a", "b", "c", "d*"))
    def func(...):
        # inside the function, you can access the function object as present in 
        # the globals: 
        self = glopbals()['func']
        # which allows you to retrieve the coefficient names as defined in the 
        # wrapper
        self.coefficients

Parameters:
f: the decorated function
nvars: number of independent variables; this determines the general syntax of the 
    model function, e.g.:
    one independent variable (i.e., 1D model):  f(x,   /, *params)
    two independent variables (2D model):       f(x,y, /, *params)
    ⋮
    and so on...

    Optional; default is 1. WARNING: do NOT confuse with the number of model 
    coefficients!

title: A user-defined name; default is None, which results in a CamelCase name
    taken from the wrapped function.

coefficients: typing.Sequence[str] — names (symbols) for the parameters.
    These can usually be inferred from the function's signature via the 
    'inspect' module, which is what the function 'model_parameters(…)' in this
    module does. However, this can be tedious for model functions with a more 
    complex syntax; hence this attribute comes in handy.

    Optional default is None (which results in an empty tuple)

    Variadic coefficients are indicated by a * suffix ('starred' coefficients)
    NOTE: Even if the notation is similar to that of variadic function parameters
    ('*args') is NOT identical to that and does not havwe the same meaning; here
    the '*' comes after ther symbol and indicated that there must be AT LEAST one
    coefficient with that symbol, in the coefficients sequence.

expression: sympy expression construct or latex string (see above); optional, 
    default is None

    WARNING: beware of using sympy.sympify(…) function to convert a string 
    containing a mathematical expression to a sympy expression (sympy.Expr), or 
    importing all of sympy package in the namespace or the module where you defined
    the decorated model function:

    • Avoid calling sympy.init_session() or sympy.init_printing() unless you know 
    what you are doing. 

    • Avoid using sympy.sympify(…) when using unicode characters as symbols (e.g. 
    'α', 'β', etc). The recommended way is also to avoid 'latex' unicode characters

    Instead use one of the following approaches:
        1. use the latin spelling for greek characters, e.g.:
            sympy.Symbol("alpha") ↦ α 
            In particular use sympy.Symbol("beta") instead of sympy.beta which 
            means the Beta function...

        2. use trailing underscore ('_') then character for subscripts, e.g.:
            sympy.Symbol("lambda_0") ↦ λ₀
            sympy.Symbol("lambda_n") ↦ λₙ

        3. use trailing caret ('^') then character for superscripts, e.g.:
            sympy.Symbol("lambda^0") ↦ λ⁰
            sympy.Symbol("lambda^n") ↦ λⁿ

        4. use sympy.exp() instead of exp()

        5. use '*' for multiplication instead of ×, ⨱, or ⋅

        6. use sympy.functions.elementary.piecewise.Piecewise for dichotmous
            functions based on a condition.
            

    • The best practice is to import the sympy module as a whole, then create the
    expression directly (manually) using specific sympy components and arithmetic
    operators, and generating symbols on the fly.

    See alphaSynapse definition for an example.


coefficient_units: optional mapping of
    coefficient symbol:str ↦ physical unit: Quantity, UnitQuantity, or sequence 
                                            of such

    Default is None. 
    When given, this flags that some model coefficient have physical units;
    the keys are the names of the model coefficients as given by the 
    'coefficients' paramneter, described above.

    Since not all coefficients necessarily associate physical units, those that 
    do not may be omitted from this mapping. However, ATTENTION: the full sequence
    of coefficient names SHOULD be given in 'coefficients', as above. Coefficients
    that are omitted from 'coefficient_units' will by default get pq.dimensionless
    as physical unit.

    The safest practice is to associate these unitless coefficients with pq.dimensionless.

    Some models may accept coefficients with physical units that depend on the physical
    dimensionality of the dependent variable. For example, alphaSynapse — which 
    models a time-varying function of ANY dependent physical variable, whether it
    is current, voltage, fluorescence intensity, etc — takes an "offset" coefficient 
    (α) which by definition has the same units as the dependent variable.

    In such cases you have the option to specify None or dataclasses.MISSING in 
    lieu of Quantity objects. Since the actual physical dimensionality of the 
    dependent variable may be unknown before calling the model function, using 
    MISSING or None as dimensionality tag flags that the coefficient should receive
    the units of the dependent variable at runtime.


    WARNING: This does not mean that the decorated model function expects Quantities
    as values for the coefficient; it is up to the function what to do with its
    own call arguments

Var-positional parameters:
==========================
additional attributes to be set to the wrapped function.

NOTE for developers: this function defines a function decorator with optional
arguments; this is made possible by decorating this function with the prog.decorator
taken from PythonDecoratorLibrary, see
https://wiki.python.org/moin/PythonDecoratorLibrary#Creating_decorator_with_optional_arguments

"""
    import inspect
    from IPython.core import display_functions
    from core.strutils import render_latex
    from core.utilities import render_sympy
    from gui.guiutils import getScipyenConsoleShell
    
#     shell = getScipyenConsoleShell()
#     
#     print(f"shell: {shell}")
    
    def wrapper(f):
        setattr(f, "model_function", True)
        setattr(f, "nvars", nvars)
        if isinstance(coefficients, typing.Sequence) and len(coefficients) and all(isinstance(p, str) for p in coefficients):
            setattr(f, "coefficients", coefficients)
        else:
            setattr(f, "coefficients", tuple())
        
        starred = tuple(filter(lambda c: "*" in c, f.coefficients))
        setattr(f, "starred_coefficients", starred)
        
        setattr(f, "expression", expression)
        
        # ### BEGIN NOTE: 2025-12-26 14:50:30 various optins - do NOT delete; instead, keep for future reference
        #
        # def __display__(f):
        #     if isinstance(f.expression, str):
        #         return render_latex(f.expression)
        #     elif isinstance(f.expression, sympy.Basic):
        #         return render_sympy(f.expression)
        # setattr(f, "display", types.MethodType(__display__, f))
        
        # def __display_png__(f):
        #     if isinstance(f.expression, str):
        #         return render_latex(f.expression, out="bytes")
        #     elif isinstance(f.expression, sympy.Basic):
        #         return render_sympy(f.expression, out="bytes")
            
        
        # def __display_pretty__(f):
        #     return f"<{type(f).__name__} {f.__module__}.{f.__name__}{inspect.signature(f)}> at {hex(id(f))}"
        
        # def __display_all__(f):
        #     bundle = {"text/plain": f"<{type(f).__name__} {f.__module__}.{f.__name__}{inspect.signature(f)}> at {hex(id(f))}",
        #              "text/latex": sympy.latex(f.expression, mode="equation*") if isinstance(f.expression, sympy.Basic) else f.expression,
        #              "image/png": render_sympy(f.expression, out="bytes") if isinstance(f.expression, sympy.Basic) else render_latex(f.expression, out="bytes"),
        #               }
        #     # metadata = dict()
        #     # metadata = {"text/latex": sympy.latex(f.expression, mode="equation*") if isinstance(f.expression, sympy.Basic) else f.expression,
        #     #             "image/png": render_sympy(f.expression, out="bytes") if isinstance(f.expression, sympy.Basic) else render_latex(f.expression, out="bytes")
        #     #           }
        #     # bundle = {"text/latex": sympy.latex(f.expression, mode="equation*") if isinstance(f.expression, sympy.Basic) else f.expression,
        #     #           "text/plain": f"<{type(f).__name__} {f.__module__}.{f.__name__}{inspect.signature(f)}> at {hex(id(f))}"
        #     #     }
        #     metadata = {"text/plain": f"<{type(f).__name__} {f.__module__}.{f.__name__}{inspect.signature(f)}> at {hex(id(f))}"}
        #     display_functions.display(bundle, metadata=metadata, raw=True)
        
        # setattr(f, "_repr_png_", types.MethodType(__display_png__, f))
        # setattr(f, "_repr_pretty_", types.MethodType(__display_pretty__, f))
        # setattr(f, "_ipython_display_", types.MethodType(__display_all__, f))
        
        # NOTE: 2025-12-26 14:54:51
        # these two are now obsolete (and QtConsole woudl have overlooked them
        # anyway, because the implementatiopn of the special method '_ipython_display_',
        # below, takes over 😄)
        # setattr(f, "__str__", types.MethodType(__display_pretty__, f))
        # setattr(f, "__repr__", types.MethodType(__display_pretty__, f))
            
        #
        # ### END   NOTE: 2025-12-26 14:50:30 various optins - do NOT delete; instead, keep for future reference
        
        
        # NOTE: 2025-12-26 14:55:28
        # enable the display of the function call syntax (a.k.a quick help) AND
        # of the graphic (LaTeX) representation of its mathematical expression
        # in supporting frontends (currently, Scipyen's internal QtConsole)
        def __special_display__(f):
            from core import strutils
            shell = getScipyenConsoleShell()
            if isinstance(f.expression, sympy.Basic) or (isinstance(f.expression, str) and strutils.islatex(f.expression)):
                try:
                    img = render_sympy(f.expression, out="bytes") if isinstance(f.expression, sympy.Basic) else render_latex(f.expression, out="bytes")
                except:
                    img = None
                if isinstance(img, bytes):
                    shell.display_pub.publish(data={"text/plain": f"<{type(f).__name__} {f.__module__}.{f.__name__}{inspect.signature(f)}> at {hex(id(f))}\n\nImplements:\n"})
                    shell.display_pub.publish(data={"image/png": img})
                    return
            shell.display_pub.publish(data={"text/plain": f"<{type(f).__name__} {f.__module__}.{f.__name__}{inspect.signature(f)}> at {hex(id(f))}\n\n"})
            # else:
            #     shell.display_pub.publish(data={"text/plain": f"<{type(f).__name__} {f.__module__}.{f.__name__}{inspect.signature(f)}> at {hex(id(f))}\n\n"})
            
        setattr(f, "_ipython_display_", types.MethodType(__special_display__, f))
        
        if isinstance(coefficient_units, dict):
            check_value_type = lambda v: (isinstance(v, pq.Quantity) and v.size==1) or isinstance(v, (type(None), type(dataclasses.MISSING)))
            if len(coefficient_units) and all(isinstance(k, str) for k in coefficient_units.keys()):
                pnames = getattr(f, "coefficients", None)
                if pnames is None or isinstance(pnames, typing.Sequence) and len(pnames) == 0:
                    setattr(f, "coefficients", tuple(coefficient_units.keys()))
                    
                punits = dict(map(lambda p: (p, pq.dimensionless), pnames))
                
                for key, value in coefficient_units.items():
                    if key not in f.coefficients:
                        continue
                    
                    if (check_value_type(value)) or (isinstance(value, typing.Sequence) and all(check_value_type(v) for v in value)):
                        punits[key] = value
                        
                setattr(f, "coefficient_units", punits)
                
            else:
                pnames = getattr(f, "coefficients", None)
                if isinstance(pnames, typing.Sequence) and len(pnames) and all(isinstance(p, str) for p in pnames):
                    punits = dict(map(lambda p: (p, pq.dimensionless), pnames))
                    setattr(f, "coefficient_units", punits)
                    
        else:
            pnames = getattr(f, "coefficients", None)
            if isinstance(pnames, typing.Sequence) and len(pnames) and all(isinstance(p, str) for p in pnames):
                punits = dict(map(lambda p: (p, pq.dimensionless), pnames))
                setattr(f, "coefficient_units", punits)
                
        # add the title
        setattr(f, "title", title)
        # enforce a "title" attribute
        f_title = getattr(f, "title", None)
        
        if not isinstance(f_title, str) or len(f_title.strip()) == 0:
            setattr(f, "title", f.__name__[0].upper() + f.__name__[1:])
            
        # add other attributes from here **kwargs
        for key, value in kwargs.items():
            # print(f"modelfunction key {key} ↦ value {value}")
            setattr(f, key, value)
        
            
        return f
    
    return wrapper(f)
    # wf = wrapper(f)
    # setattr(wf, "self", f)
    # return wf

def check_unpack_model_coeffs(n:int, params:typing.Sequence[typing.Union[Real, np.ndarray]] | np.ndarray, 
                              *extras, strip_units:bool=True) -> tuple[float]:
    r"""Verifies and unpacks model coefficients, when supplied as a Sequence or vector
    Check that params and *extras amount to the required number of coefficients 
    specified in 'n'.
    When extra is a sequence fo floats, it weill be appended to the params.
    """
    import numpy as np
    # extra coefficients. 
    # when all expected coefficients are packed into the 'params' parameter, 
    # extras should be either empty, or contain only None objects
    iscoeff = lambda v: isinstance(v, (Real)) or (isinstance(v, np.ndarray) and v.size==1)
    extras = tuple(filter(lambda v: iscoeff(v), extras))
    # ensure extras contain scalar floats
    extras = tuple(map(lambda v:float(v) if isinstance(v, (np.ndarray, Real)) else v, extras))
    
    # NOTE: 2025-12-10 22:11:32
    # when a numpy array of floats is unpacked via tuple constructor, the 
    # result is a tuple of np.float64; these need to be cast to plain float
    # this is also the case for a Quantity array's 'magnitude' (which is the 
    # underlying float array without dimensionality, or physical units)
    if isinstance(params, np.ndarray) and params.dtype in (np.dtype('float64'), np.dtype("int64")):
        # coefficients packed as a numpy array, possibly a Quantity, and possibly
        # a singleton ("scalar")
        np = len(extras) + params.size
        assert np == n, f"Expecting {n} coefficients (packed or individual) but {np} were given"
        
        if isinstance(params, pq.Quantity):
            if strip_units:
                params = tuple(map(lambda v: float(v), params))
            else:
                params = tuple(params) # tuple of Quantity objects
        else:
            params = tuple(map(lambda v: float(v), params))
            
        return params + extras
            
    elif isinstance(params, typing.Sequence):
        # coefficients packed as a sequence (tuple, list, deque)
        np = len(params) + len(extras)
        assert np == n, f"Expecting {n} coefficients (packed or individual) but {np} were given"
        
        if all (isinstance(v, Real) for v in params):
            params = tuple(map(lambda v: float(v), params)) # casting float to float should bring no penalty
        
        elif all(isinstance(v, pq.Quantity) and v.size==1 and v.dtype==np.dtype("float64") for v in params):
            if strip_units:
                params = tuple(map(lambda v: float(v.magnitude), params))
            else:
                params = tuple(params) # tuple of Quantiy arrays each with one element !
        
        elif all(isinstance(v, np.ndarray) and v.size==1 and v.dtype==np.dtype("float64") for v in params):
            params = tuple(map(lambda v: float(v), params)) # otherwise we get a tuple of np.float64
            
        else:
            raise TypeError("Coefficients sequence contains invalid object types; expecting float, numpy.float64 or numpy arrays with size 1 and dtype 'float64'")
            
        return params + extras
    
    elif isinstance(params, Real):
        np = len(extras) + 1
        assert np == n, f"Expecting {n} coefficients (packed or individual) but {np} were given"
        return (params, ) + extras
    
    else:
        raise TypeError(f"Expecting a sequence of float scalars or a float numpy array with {n} elements; got {type(params).__name__} instead")
    

def check_rise_decay_params(x:typing.Sequence[Real]|np.ndarray) -> int:
    r"""Returns the number of decay components for a exp-rise-multi-decay transient.
    x = iterable with model parameters (see exponential_rise_multi_decays())
    """
    nx = len(x) if isinstance(x, typing.Sequence) else x.size
    if np.remainder(nx-3, 2) != 0:
        raise ValueError(f"Unexpected number of elements in the parameters vector; must be 2n + 3 where n is the number of decay components; instead got {nx} elements")
    
    return (nx-3) // 2

# @timefunc # uncomment this for testing 😄
@modelfunction(coefficients = ("α", "β0", "β1", "x0", "λ0", "λ1"),
               title="Biexponential",
               expression = sympy.Eq(sympy.Symbol("y"),
                                     sympy.Symbol("alpha")  + sympy.Symbol("beta_0") * sympy.exp(sympy.Symbol("lambda_0") * (sympy.Symbol("x")-sympy.Symbol("x_0"))) +
                                                              sympy.Symbol("beta_1") * sympy.exp(sympy.Symbol("lambda_1") * (sympy.Symbol("x")-sympy.Symbol("x_0")))
                                     ),
               )
def biexponential(x:typing.Union[np.ndarray, Real], 
                  α:Real|typing.Sequence[Real]|np.ndarray, /,
                  β0:typing.Optional[Real] = None,
                  β1:typing.Optional[Real] = None, 
                  x0:typing.Optional[Real] = None,
                  λ0:typing.Optional[Real] = None, 
                  λ1:typing.Optional[Real] = None,
                  ) -> np.ndarray | float:
    r"""Sum of two exponentials with shift and bias (multiplicative and additive)
    y = α + β0 × exp(λ0 × (x-x₀)) + β1 × exp(λ1 × (x-x₀))
    
    Parameters:
    ===========
    x: independent variable
    α: additive bias ("offset")
    β0, β1: multiplicative bias for each exponential
    λ0, λ1: exponential constants
    x0: shift (delay, or onset)
    
"""
    α, β0, β1, λ0, λ1, x0 = check_unpack_model_coeffs(6, α, β0, β1, λ0, λ1, x0)
    x = check_independent_variable(x)
    λ0x = np.multiply(λ0, np.subtract(x, x0))
    λ1x = np.multiply(λ1, np.subtract(x, x0))
    return np.add(np.add(np.multiply(β0, np.exp(λ0x)), np.multiply(β1, np.exp(λ1x))), α)
    
    # return β0 * np.exp(λ0 * x) + β1 * np.exp(λ1 * x)

# @timefunc # uncomment this for testing 😄
@modelfunction(coefficients = ("α", "β", "x0", "λ*"),
               title="ExponentialProduct",
               expression = sympy.Eq(sympy.Symbol("y"),
                                     sympy.functions.elementary.piecewise.Piecewise((sympy.Symbol("alpha") + sympy.Symbol("beta") * 
                                                                                        sympy.Product(sympy.exp((sympy.Symbol("x")-sympy.Symbol("x_0")) * sympy.Symbol("lambda_k")),
                                                                                                      (sympy.Symbol("k", integer=True), 0, sympy.Symbol("n", positive=True, integer=True)-1)),
                                                                                     sympy.Symbol("n") > 0))
                                     ),
               )
def exponential_product(x: np.ndarray | Real, 
                        α:typing.Sequence[Real] | Real | np.ndarray, /,
                        β:typing.Optional[Real] = None, 
                        x0:typing.Optional[Real] = None, 
                        *λ) -> np.ndarray | Real:
    r"""Product of several exponential decays, biased and shifted

    Realizes:
                ₙ₋₁
    y = α + β × Π  exp((x-x₀)λₖ) = α + β × exp((x-x₀)λᵪ)    , where:
                ᵏ⁼⁰

    • α is the additive bias (offset)
    • β is the multiplicative bias (scale)
    • λ is a sequence of floats with the individual rate constants, one for
        each exponential factor
    • λᵪ is the "combined" decay time constant: Σλₖ
    • 𝑛 = len(λ) is the number of exponentials in the product

    NOTE: For a product of TWO exponentials, intial coefficients used for fitting 
    can be generated analytically by the function guess_init_two_exp_prod(…) in 
    the core.curvefitting module

    
"""
    x = check_independent_variable(x)
    if isinstance(α, (typing.Sequence)) and len(α) == 3 or isinstance(α, np.ndarray) and α.size == 3:
        λ = (β, x0) + λ
        β = None
        x0 = None
    α, β, x0, *λ = check_unpack_model_coeffs(len(λ)+3, α, β, x0, *λ)
    
    # assert all(v > 0. for v in τ), "τ must be strictly positive"
    
    if len(λ) == 1:
        return exponential(x, α, β, x0, λ[0])
    else:
        # λ = np.sum(list(map(lambda v: 1/v, τ)))
        λc = np.sum(λ)
        xxλc = np.multiply(np.subtract(x, x0),λc)
        
        return np.add(α, np.multiply(β, np.exp(xxλc)))
    
# @timefunc # uncomment this for testing 😄
@modelfunction(coefficients = ("α", "β", "x0", "λ"),
                title="Exponential",
                expression = sympy.Eq(sympy.Symbol("y"),
                                      sympy.Symbol("alpha") + 
                                      sympy.Symbol("beta") * sympy.exp((sympy.Symbol("x")-sympy.Symbol("x_0")) * sympy.Symbol("lambda"))),
                )
def exponential(x:np.ndarray | Real, 
                α:typing.Sequence[Real] | np.ndarray | Real, /,
                β:typing.Optional[Real] = None, 
                x0:typing.Optional[Real] = None, 
                λ:typing.Optional[Real] = None) -> np.ndarray | Real:
    r"""Single exponential with bias and shift

    y = α + β × exp((x-x₀)λ)
    
    Parameters:
    ===========
    x: independent variable (e.g., time): 1D numpy array

    coefficients are given as floats in the following order:

    α (offset or additive bias, in units of "y"), 
    β (scale, or multiplicative bias; dimensionless), 
    x₀ (onset, delay or shift, in units of "x"), 
    λ (exponential constant; in (units of "x")⁻¹)

    NOTE: "rate" constant τ is the inverse of λ: τ = 1/λ

    """
    x = check_independent_variable(x)
    α, β, x0, λ = check_unpack_model_coeffs(4, α, β, x0, λ)
    return np.add(α, np.multiply(β, np.exp(np.multiply(np.subtract(x,x0), λ))))

# @timefunc # uncomment this for testing 😄
@modelfunction(coefficients = ("α", "β", "x0", "λ"),
               title="BoundedExponentialRise",
               expression = sympy.Eq(sympy.Symbol("y"),
                                     sympy.Symbol("alpha") +
                                     sympy.Symbol("beta") * (1 - sympy.exp(-1 * (sympy.Symbol("x")-sympy.Symbol("x_0"))*sympy.Symbol("lambda")))),
               # expression = sympy.Eq(sympy.Symbol("y"),
               #                       sympy.functions.elementary.piecewise.Piecewise((sympy.Symbol("alpha") +
               #                                                                       sympy.Symbol("beta") * (1 - sympy.exp(-1 * (sympy.Symbol("x")-sympy.Symbol("x_0"))*sympy.Symbol("lambda"))),
               #                                                                       sympy.Symbol("lambda") > 0))),
               )
def bounded_exponential_rise(x:np.ndarray | Real, 
                             α:typing.Sequence[Real]|np.ndarray, 
                             β:typing.Optional[Real] = None, 
                             x0:typing.Optional[Real] = None, 
                             λ:typing.Optional[Real] = None) -> np.ndarray | float:
    r"""Particular case of single exponential rise.

    Realizes α + β × [1 - exp((x-x₀)λ)] where λ < 0.

NOTE This is equivalent to the generic exponential

    α₁ + β₁ × exp((x-x₀)λ), 

    where:
        β₁ = -β
        α₁ = α - β₁
        and λ < 0

This means you can always use the exponential(…) model function with appropriate
values for α, β, and with appropriate value & sign of λ

    Parameters:
    ===========
    x: independent variable (e.g., time): 1D numpy array

    coefficients are given as floats in the following order:
    
    α (offset or additive bias, in units of "y"), 
    β (scale, or multiplicative bias; dimensionless), 
    x₀ (onset, delay or shift, in units of "x"), 
    λ (exponential constant; in (units of "x")⁻¹)

"""
    x = check_independent_variable(x)
    α, β, x0, λ = check_unpack_model_coeffs(4, α, β, x0, λ)
    # assert λ < -1., "For this particular model, λ must be < -1"
    
    xxλ = np.divide(np.subtract(x,x0), λ)
    return np.add(α, np.multiply(β, np.subtract(1, np.exp(xxλ))))
    
# @timefunc # uncomment this for testing 😄
@modelfunction(coefficients = ("α", "β", "x0", "τ"),
               title="AlphaSynapse",
               expression = sympy.Eq(sympy.Symbol("y"), 
                                     sympy.functions.elementary.piecewise.Piecewise((sympy.Symbol("alpha") + sympy.Symbol("beta") * (sympy.Symbol("x")-sympy.Symbol("x_0"))/sympy.Symbol("tau") * sympy.exp(-(sympy.Symbol("x")-sympy.Symbol("x_0") - sympy.Symbol("tau"))/sympy.Symbol("tau")),
                                                                                     sympy.Symbol("x")-sympy.Symbol("x_0") >= 0), 
                                                                                    (sympy.Symbol("alpha"), 
                                                                                     sympy.Symbol("x")-sympy.Symbol("x_0") < 0)))
               )
def alphaSynapse(x:np.ndarray | Real, α:typing.Union[typing.Sequence[Real],np.ndarray,Real], /,
                  β:typing.Optional[Real] = None, x0:typing.Optional[Real] = None,
                  τ:typing.Optional[Real] = None) -> np.ndarray | float:
    r"""
======================
AlphaSynapse function.
======================

Description:
============

A single exponential rise and decay, both with the same constant (τ):

Eq. 1
-----

$$f(x) = \\begin{cases} \\alpha + \\beta \\left(x - x_{0}\\right) e^{\\left(\\tau - x + x_{0}\\right) / \\tau} / \\tau & \\text{for}\\: x - x_{0} \\geq 0 \\\\\\alpha & \\text{otherwise} \\end{cases}$$

where:
    α  ↦ additive bias (offset); units of "y"

    β  ↦ multiplicative bias (scale); dimensionless

    x₀ ↦ shift (delay, or onset); units of "x"

    τ  ↦ the synaptic constant; units of "x"

See: Rall, W. Distinguishing theoretical synaptic potentials computed for 
different soma-dendritic distributions of synaptic input. J Neurophysiol 30(5),
1138–68, 1967.

The implementation follows that in NEURON simulation software
( M. L. Hines, N. T. Carnevale; The NEURON Simulation Environment. 
Neural Comput 1997; 9 (6): 1179–1209. 
doi: https://doi.org/10.1162/neco.1997.9.6.1179 ) :


| "a synaptic current with alpha function conductance defined by
| i = g * (v - e)      i(nanoamps), g(microsiemens);
| where:
|     g = 0 for t < onset and
|     g = gmax * (t - onset)/tau * exp(-(t - onset - tau)/tau) for t > onset
| this has the property that the maximum value is gmax and occurs at t = delay + tau."
 

Parameters:
===========
:x: Predictor (independent variable) - 1D numpy ndarray or float
:α, β, x0, τ: See above. When α is a sequence of scalars (1D array-like), it is 
    interpreted as containing the individual α, β, x0, τ coefficients 'packed' 
    in this sequence (some optimization functions expect this)
    
:parameters: 1D array-like: numeric sequence (tuple, list, numpy array) with four
    elements in the following order (see above for their meaning):


Returns:
========
1D numpy array (vector)

Example: 
========
(code to run in Scipyen's console)

.. code:: python

    from core import models

    x = np.linspace(0.0,1.0, 1000);

    α = 0.; β = -1.; x0 = 0.05; τ = 0.01;
    parameters = [α, β, x0, τ];

    # any of the statements below are equivalent:
    y = alphaSynapse(x, α, β, x0, τ)
    y = alphaSynapse(x, *parameters)
    y = alphaSynapse(x, parameters)

    plt.plot(x,y)

NOTE: 
=====
1. Rall 1967 uses the notation T for t - onset, and Tₚ for τ in the "alpha" function below:

Eq. 2
-----

$$f(T) = \\begin{cases} \\left( T / T_{p} \\right) \\times e^{\\left( 1 - T / T_{p} \\right)} & \\text{for}\\: T_{p} > 0 \\\\0 & \\text{otherwise} \\end{cases}$$

which has:†

• extremum (1.0) at T = Tₚ (i.e. t - onset = τ)
• value of 0.5 at t ∈ {≈ 0.23τ, ≈ 2.68τ}, hence:
• half-width (with at half of peak amplitude) ≈ 2.45τ
• area under the entire curve: 𝑒τ, where 𝑒 is Euler's number (Napier's constant)

2. The code in NEURON syn.mod does NOT include the additive bias α. I include α
for the case where the transient modelled by alphaSynapse takes place on top of
a constant signal (the "direct current", or "DC" component — this nomenclature
is not always appropriate e.g. when modelling the change in membrane potential
the "DC" component is rather some steady-state initial voltage V₀, such as the
resting membrane potential).

3. The β parameter here corresponds to the 𝑔ₘₐₓ in NEURON's code.
Whether β is a conductance (𝑔) or not depends on what are you use this function
for. NEURON's syn.mod calculates 𝑔 THEN converts it to a synaptic current 𝑖 
(see above); if you use this function to model a current, you might want to adjust
β accordingly (i.e. set it to YOUR 𝑔ₘₐₓ times the electromotive force 𝑣 - 𝑒).

4. The x0 parameter here corresponds to the 'onset' in NEURON (and Rall) code.

5. Finally, 'x' here corresponds to 𝑡 in NEURON's code. If follows that x0 and τ
have the same physical units as 'x'.

† At $f(x) = 0.5$
and noting $\\chi  = \\left(t - \\text{onset}\\right)/\\tau \\text{ for } \\tau > 0$
`Eq. 2` becomes
    
Eq. 3
-----

$$\\chi \\times e^{\\left(1-\\chi\\right)} = 0.5$$

It follows that 

$$\\chi = 0.5 \\times e^{\\left(\\chi - 1\\right)}$$

This is a transcendental equation which can be solved graphically by plotting, 
on the same axes, the curves

$$g(t) = \\chi$$
and
$$h(t) = e^{\\left(\\chi - 1\\right)} \\times 0.5$$
    
The intersections between the two curves are the solutions χ₀, χ₁ of `Eq. 3`
(you may want to plot the region of the curves where x <= 0.2, in order to
visualize the intersections).
    
Example:
    
.. code:: python

    x = np.linspace(0,1,int(1e5))
    τ = 0.05
    g = x/τ
    h = np.exp(xτ - 1.)/2.
    
    plt.plot(x[x <= 0.2], g[x <= 0.2], label="xτ")
    plt.plot(x[x <= 0.2], h[x <= 0.2], label="0.5 * exp(xτ-1)")
    
    # Locate these intersections on the 'x' axis 
    # NOTE: you may have to play with 'rtol' and 'atol'
    
    ndxx = np.where(np.isclose(g, h, rtol=1e-4, atol=1e-5))[0]
    -> array([ 1160, 13391, 13392]) # NOTE: because we're using discrete curves,
                                    # you won't get EXACT solutions!
                                            
    # And the solutions (in 'x') are:
    
    x[ndxx]
    -> array([0.0116, 0.1339, 0.1339])  
    
    # NOTE: the last two values ARE different but they SEEM identical due to the
    # display precision:
                                        
    with np.printoptions(precision=10, floatmode="fixed"):
        print(x[ndxx])
        
    -> [0.0116001160 0.1339113391 0.1339213392]

    # Finally, to express the solutions in terms of τ:
    
    σ = x[ndxx]/τ
    
    σ
    ->  array([0.232 , 2.6782, 2.6784])
    
    with np.printoptions(precision=10, floatmode="fixed"):
        print(σ)
        
    -> [0.2320023200 2.6782267823 2.6784267843]
    
    # Clearly, the first element is most likely one of the solutions in 'x'
    
    x_0 = float(σ[0])
    
    # The last two elements are very close, suggesting the "real" solution is
    # somewhere between them; we will approximate it with a linear interpolation
    # (i.e. the average of these two points, which are both on the 'x' axis)
    
    x_1 = float(σ[1:].mean())
    
    # So, the approximate solutions are (expressed as factors of τ)
    x_0
    -> 0.23200232002320023  ≈ 0.23τ

    x_1
    -> 2.678326783267832    ≈ 2.68τ
    
    # And the width at half-maximum:
    fwhm = x_1 - x_0
    fwhm
    -> 2.4463244632446317   ≈ 2.45τ

Finally, expressing `Eq. 2` in t:

Eq. 4
-----

$$f(t) = \\begin{cases} t/\\tau \\times e^{\\left(1-t/\\tau\\right)} & \\text{for}\\: \\tau > 0 \\\\0 & \\text{otherwise} \\end{cases}$$

the area under the curve is:

Eq. 5
-----
$$\\int_{0}^{\\infty} f(x)dx = e \\times \\tau \\qed$$
    
.. note:: The integral (`Eq. 5`) is divergent for τ < 0, and `Eq. 4` is
   undefined for τ = 0
                                    
    
CHANGELOG:
==========
Renamed from alphaFunction to alphaSynapse to avoid confusion, especially with
the mathematical Alpha Function (https://mathworld.wolfram.com/AlphaFunction.html)
    
"""
    # NOTE: Python currently does not support unicode
    # characters such as sub- or super-scripts, so please use 'x0', not 'x₀'
    # in the code
    
    self = globals()["alphaSynapse"]
    # print(f"nvars:{self.nvars}")
    # print(f"coeff  names: {self.coefficients}")
    
    # make sure x is a numpy array or a scalar
    x = check_independent_variable(x)
        
    # unpack parameters
    α, β, x0, τ = check_unpack_model_coeffs(4, α, β, x0, τ)
    # print(f"{α}")
    assert(τ > 0.), "Time constant MUST be strictly positive"
    
    def alpha(v):
        # NOTE: 2025-12-08 00:24:16
        # the original "alpha" function in NEURON's syn.mod is 
        #   v × exp(1-v),
        #   with:
        #       v = (x-onset)/tau
        #   (pretty similar to an exponential integral?)
        #   
        #   Let x₀ = onset
        #
        #   Then v × exp(1-v) is equivalent to:
        #       (x-x₀)/τ × exp(1-(x-x₀)/τ)      = 
        #       (x-x₀)/τ × exp((τ - x + x₀)/τ)  =
        #       (x-x₀)/τ × exp(-(x - x₀ - τ)/τ) ∎
        #
        # Here, the multiplicative bias β is gₘₐₓ in syn.mod; I also include an
        # additive bias α ("offset") to allow thus function to be applied to a
        # signal with DC component ≠ 0
        #
        #
        # NOTE: 2025-12-08 00:28:34 
        # using numpy builtin ufuncs here; 
        # they're OK with scalar floats too, but they could return a np.float64
        # therefore I need to cast back to float, see NOTE: 2025-12-08 00:29:32 
        return np.add(α, np.multiply(β, np.multiply(v, np.exp(np.subtract(1.,v)))))
    
    # NOTE: 2025-12-08 00:48:54 
    # DISCARD this option as is unefficient (frompyfunc returns PyObject and is
    # MUCH slower
    # # NOTE: 2025-12-08 00:23:08
    # # vectorized version used when x is a numpy array
    # valpha = np.frompyfunc(alpha, 1, 1) 
    
    xτ = np.divide(np.subtract(x,x0), τ)
    
    # NOTE: 2025-12-07 23:29:18
    # in NEURON's syn.mod there is an additional condition for returning 0., when v > 10. - 
    # probably to make sure that extremely small values from v × exp(1-v) truly vanish
    # I don't use that here
    #
    if isinstance(x, Real):
        # x is a scalar, all simple!
        # NOTE: 2025-12-08 00:29:32
        # casting to plain float, see NOTE: 2025-12-08 00:28:34 
        return float(alpha(xτ)) if xτ >=0 else α
    
    else:
        if x.size == 1:
            # no point in vectorizing on array with one element
            return alpha(xτ) if xτ >=0 else np.array([α])
    
        y = np.full_like(x, α)
        
        # using built-in ufuncs (a LOT more efficient !!!)
        # NOTE: 2025-12-13 12:04:38 
        # about the condition xτ >= 0:
        # This condition is amenable to the use of 'where' parameter in the call
        # syntax of numpy ufuncs (see numpy documentation). Bassically, it applies
        # the ufunc to any element of the arugment 'x' that statistfies the condition,
        # skipping the others (and therefore leaving the corresponding elements 
        # in the output array 'y' untouched, hence possibly undefined).
        #
        # HOWEVER, here, ufuncs are used by the alpha function def'ed above, while
        # the alpha function itself is NOT an ufunc; so rather that passing any 
        # data to alpha (and using 'where' in the ufunc calls in there, with the 
        # caveat above), I apply the alpha function directly to the elements of 
        # xτ that satisfy this condition (and store the output in the corresponding 
        # elements of 'y')
        y[xτ>=0] = alpha(xτ[xτ>=0]) 
        
        # NOTE: 2025-12-08 00:50:00 -> TOO SLOW !!!
        # valpha(xt, y, where = xt>=0, casting="unsafe")
            
        return y 

@modelfunction(coefficients = ("i", "n", "b"),
               title="NonStationaryFluctuationAnalysis")
def nsfa(x:np.ndarray | Real, i:Real|pq.Quantity|typing.Sequence[typing.Union[Real, pq.Quantity]], /, 
         n:typing.Optional[typing.Union[Real, pq.Quantity]] = None, 
         b:typing.Optional[typing.Union[Real, pq.Quantity]] = None) -> np.ndarray | float:
    r"""
        y = x * i - x²/N + b
    
    Parameters: i, N, b: unitary current (pA), number of channels, background current variance (pA²))
    
WARNING: do not pass quantities for the parameters, yet; just use floats
"""
    i, n, b = check_unpack_model_coeffs(3, i, n, b)
    x = check_independent_variable(x)
    
    return np.add(np.subtract(np.multiply(x, i), np.divide(np.power(x, 2), n)), b)
    
    # return x*i - x**2 / n + b
    
@modelfunction(coefficients = ("α", "β", "x0", "τ1", "τ2"),
               title = "ClementsBekkers97",
               expression = r"$y(x) = \begin{cases} \alpha + \beta \times \left(1 - e^{-\left(x-x_{0}\right) / \tau_{1}}\right) \times e^{-\left(x-x_{0}\right) / \tau_{2}} & \text{for}\: x - x_{0} \geq 0 \\\alpha & \text{otherwise} \end{cases}$",
)
def Clements_Bekkers_97(x:np.ndarray | Real,
                        α:typing.Union[Real, typing.Sequence[Real], np.ndarray], /, 
                        β:typing.Optional[Real|int] = None, 
                        x0:typing.Optional[Real] = None, 
                        τ1:typing.Optional[Real] = None, 
                        τ2:typing.Optional[Real] = None,
                        **kwargs) -> np.ndarray | Real:
    r"""
    Clements & Bekkers 1997 mEPSC waveform.

    Description:
    ============

    This is a product of two exponentials ("rise" and "decay", each with their 
    own time constant), with additive and mutiplicative bias:

    $y(x) = \\begin{cases} \\alpha + \\beta \\times \\left(1 - e^{-\\left(x-x_{0}\\right) / \\tau_{1}}\\right) \\times e^{-\\left(x-x_{0}\\right) / \\tau_{2}} & \\text{for}\\: x - x_{0} \\geq 0 \\\\\\alpha & \\text{otherwise} \\end{cases}$

    where:
        α           — the offset (additive bias; usually, 0.); units of "y"
    
        β           — the scale (multiplicative bias); dimensionless
    
        x₀          — the delay ("onset", or "shift"); units of "x"
    
        τ₁, τ₂ > 0. — the time constants, respectively, for the rise and decay phases
                        units of "x"
    
    Parameters:
    ============
    
    :x: predictor (independent variable e.g., time) - 1D numpy ndarray

    :α, β, x₀, τ₁ and τ₂: float scalars, where:
        α is considered in pA,
        β is dimensionless,
        x₀, τ₁ and τ₂ are considered to be given in s

        and τ₁ > 0 τ₂ > 0
    
    Var-keyword parameters:
    =======================
    
    :unit_amplitude: optional, default is False
        When True, return a waveform with baseline 0 and peak value +1 , using 
        the given time constants τ₁ and τ₂
    
    Returns:
    ========
    
    1D numpy array (vector)
    
    NOTE:
    =====
    
    • the extremum is (τ2/(τ1+τ2)) * np.pow(τ1, τ1/τ2)/np.pow(τ1+τ2, τ1/τ2)
        ∘ for α = 0., β = 1. 
        ∘ and occurs at x = τ1 × ln(τ2/τ1 +1) + x0
        (analytically determined as the solution of f′(x)dx = 0)
        So to get a curve spanning the interval [0., 1.] in 'y', the coefficient β
        should be 1/extremum (for α = 0.0) , but WARNING this 
        will also change the FWHM!
    • FWHM: x coordinates for full width at half-max need to be determined 
        graphically as the intersection between y(x) and the line y₁(x)=ymax/2
        (see e.g., documentation for alphaSynapse)
    • area under the curve:
             ∞   
             ∫f(x)dx = (β × τ2²)/(τ1+τ2), for α = 0, x0 = 0, and τ1, τ2 > 0
             0
    NOTE: the DURATION of the waveform is determined by the independent variable
    'x'
    
    """
    unit_amplitude = kwargs.pop("unit_amplitude", False)
    
    α, β, x0, τ1, τ2 = check_unpack_model_coeffs(5, α, β, x0, τ1, τ2)
    assert all(v >0. for v in (τ1, τ2))
    
    if unit_amplitude:
        β = get_CB_scale_for_unit_amplitude(τ1, τ2, β>0) 
    
    x = check_independent_variable(x)
    
    # print(f"Clements_Bekkers_97: α = {α}")
    
    xx = np.subtract(x, x0)
    
    if isinstance(x, Real):
        # NOTE: 2025-12-20 21:28:42
        # evaluation at a single point; also useful for scipy.integrate.quad
        # (WARNING when integrating — i.e. calculating the quadrature — set the additive bias α to 0.)
        xx = float(xx)
        return float(α + β * (1- np.exp(-xx/τ1))*np.exp(-xx/τ2)) if xx >= 0 else float(α)
    else:
        if x.size == 1:
            return np.array([float(α + β * (1- np.exp(-xx/τ1))*np.exp(-xx/τ2))]) if xx >= 0 else np.array([float(α)])
    
    decay = np.exp(np.divide(np.negative(xx[xx>=0]), τ2))
    rise  = np.subtract(1, np.exp(np.divide(np.negative(xx[xx>=0]), τ1)))
    y = np.full_like(x, α)
    y[xx>=0] = np.add(α, np.multiply(np.multiply(β, rise), decay))
    
    return y

def get_CB_scale_for_unit_amplitude(τ_rise:Real, τ_decay:Real, positive:bool=True):
    yₘ = (τ_decay/(τ_rise+τ_decay)) * np.pow(τ_rise, τ_rise/τ_decay)/np.pow(τ_rise+τ_decay, τ_rise/τ_decay)
    peak = 1. if positive else -1.
    return np.divide(peak, yₘ)
    
#     efunc       = lambda x, τ: np.exp(-x/τ)
#     risefunc    = lambda x, τ: 1-efunc(x,τ)
#     decayfunc   = efunc
#     
#     xₘ = -τ_rise * np.log(τ_rise/(τ_rise + τ_decay)) + x0
#     
#     yₘ = risefunc(xₘ, τ_rise) * decayfunc(xₘ, τ_decay)
#     peak = -1. if β < 0 else 1. if β > 0 else 0
#     
#     return np.divide(peak, yₘ)

@modelfunction(coefficients = ("α", "β0", "x0_0", "τ0_0", "τ0_1", "β1", "x0_1", "τ1_0", "τ1_1"))
def CBsum(x:np.ndarray | Real, α:Real | typing.Sequence[Real], /, 
          β0:typing.Optional[Real]=None, x0_0:typing.Optional[Real]=None,
          τ0_0:typing.Optional[Real]=None, τ0_1:typing.Optional[Real]=None, 
          β1:typing.Optional[Real]=None, x0_1:typing.Optional[Real]=None, 
          τ1_0:typing.Optional[Real]=None, τ1_1:typing.Optional[Real]=None) -> np.ndarray | float:
    r"""Realizes a sum of two Clements_Bekkers_97 functions, on x.
    
    Let 𝒙 a 1D domain vector:
    
        𝒚₀ = α + β₀ * (1 - exp(-(x-x₀₀)/τ₀₀)) ⋅ exp(-(x-x₀₀)/τ₁₀)
        𝒚₁ = 0 + β₁ * (1 - exp(-(x-x₀₀)/τ₀₁)) ⋅ exp(-(x-x₀₁)/τ₁₁)
    
    Then:
    
        𝒚 = 𝒚₀ + 𝒚₁
        
    Empyrical model that can be used for fitting a compound AHP/ADP waveform as 
    a sum of two "alphafunctions".

    Parameters:
    ===========
    
    x: 1D domain vector (typically, time)
    
    parameters: a sequence (tuple, list) of model parameters in the following
        order:
    
        α, β₀, x₀₀, τ₀₀, τ₁₀, β₁, x₀₁, τ₀₁, τ₁₁

    """
    x = check_independent_variable(x)
    # NOTE: 2025-11-05 21:31:42
    # allow passing all parameters packed in a sequence, so as to do away with 
    # the *_model version of this function
    α, β0, x0_0, t0_0, t0_1, β1, x0_1, t1_0, t1_1 = check_unpack_model_coeffs(9, α, β0, x0_0, t0_0, t0_1, β1, x0_1, t1_0, t1_1)

    y0 = Clements_Bekkers_97(x, α, β0, x0_0, τ0_0, τ0_1)
    
    y1 = Clements_Bekkers_97(x, 0., β1, x0_1, τ1_0, τ1_1)
    
    return np.add(y0, y1)
    
@modelfunction(coefficients = ("α", "x0", "ρ", "β*", "τ*"),
               title="ExponentialRiseMultiDecays")
def exponential_rise_multi_decays(x:np.ndarray|Real, 
                                  α:typing.Sequence[Real] | Real | np.ndarray, /,
                                  x0:typing.Optional[Real] = None,
                                  ρ:typing.Optional[Real] = None,
                                  *βτ:Real, 
                                  **kwargs) -> np.ndarray|Real:
    r"""Clements & Bekkers 1997 model with sum of exponential decays.

        y = α + (1 - exp( -(x-x₀)/ρ ) × ( β₀     × exp( -(x-x₀)/τ₀)     + 
                                          β₁     × exp( -(x-x₀)/τ₁)     +
                                          .                             +
                                          .                             +
                                          βₙ₋₁   × exp( -(x-x₀)/τₙ₋₁ ))      (1)


        where:

            α           = additive bias, or offset (`DC' component)
            x₀          = shift ('onset', 'delay') of the transient
            ρ           = rising phase time constant; 
            β₀...βₙ₋₁   = scale (multiplicative bias) for each decay component
            τ₀...τₙ₋₁   = time constant for each decay component
    
    Positional parameters:
    =====================
    
    x   =   the independent (predictor) data; represents the definition domain 
            for the model function e.g., a time vector, if modelling a time-
            varying process
            
    α           = additive bias, or offset (`DC' component); units of the result 
                signal

    x₀          = shift ('onset', 'delay') of the transient; units of "x"

    ρ           = rising phase time constant; (unitys of "x")⁻¹

    Var-positional parameter:
    =========================
    This is a sequence that packs together the coefficients βₖ and τₖ for the
        decay component k:
    βτ          = sequence of β₀, τ₀, β₁, τ₁, …, βₙ₋₁, τₙ₋₁
        where:
        n is the number of decays
        β₀...βₙ₋₁ are the scale (multiplicative bias); dimensionless
        τ₀...τₙ₋₁ are the decay time constant; (units of "x")⁻¹
        
    ATTENTION: ORDER OF MODEL COEFFICIENTS:
    
    For each decay component k there are two coefficients: 
    βₖ (scale) and τₖ (decay constant). These MUST be passed in the order (β,τ):
    
        β₀, τ₀, <β₁, τ₁, ...βₙ₋₁, τₙ₋₁>
    
    Thus the entire coefficients are passed in the following order:
    
    α, x0, ρ, β₀, τ₀, <β₁, τ₁, ...βₙ₋₁, τₙ₋₁>
    
    Returns:
    ========
    
    y = the model curve
    
    When returnDecays is True, also returns:
    
    yd = a 2D numpoy array of scaled decay components (as columns); 
        
    """
    returnDecays = kwargs.pop("returnDecays", False)
    
    x = check_independent_variable(x)
        
    if isinstance(α, (typing.Sequence, np.ndarray)):
        nα = len(α) if isinstance(α, typing.Sequence) else α.size
        if nα == 3:
            if ρ is not None:
                βτ = (ρ, ) + βτ
            ρ = None
            
            if x0 is not None:
                βτ = (x0,) + βτ
            x0 = None
            
        elif nα == 3:
            if x0 is not None:
                βτ = (x0,) + βτ
            x0 = None
                
    nβτ = len(βτ)

    ncoeffs = nα + nβτ
    assert (ncoeffs - 3) % 2 == 0, f"Unexpected number of coefficients ({ncoeffs}); must be 2n + 3 where n is the number of decay components"
        
    α, x0, ρ, *βτ = check_unpack_model_coeffs(ncoeffs, α, x0, ρ, *βτ)
    
    nDecays = len(βτ)//2
    
    xx = np.subtract(x, x0)
    
    if isinstance(x, Real):
        xx = float(xx)
        decays = list(map(lambda k: 0. if xx < 0 else βτ[2*k] * (np.exp(-xx/βτ[2*k+1])), range(nDecays)))
        ret = α if xx <= 0 else α + (1 - np.exp(-xx/ρ)) * sum(decays)
        if returnDecays:
            return ret, decays
        else:
            return ret
            
    else:
        if x.size == 1:
            yd = np.array(list(map(lambda k: 0. if xx < 0 else βτ[2*k] * (np.exp(-xx/βτ[2*k+1])), range(nDecays))))
            ret = np.array([α]) if xx < 0 else α + (1 - np.exp(-xx/ρ)) * decays.sum()
        
        else:
            y = np.full_like(x, 0.)
            yd = np.tile(y[:,np.newaxis], (1,nDecays))
            y[xx>=0] = np.subtract(1., np.exp(np.divide(np.negative(xx[xx>=0]), ρ))) # rise
            decays = list(map(lambda k: np.multiply(βτ[2*k], np.exp(np.divide(np.negative(xx[xx>=0]), βτ[2*k+1])) ), range(nDecays)))
            for k in range(nDecays):
                yd[xx>=0,k] = decays[k]
                
            y *= np.sum(yd, axis=1)
            y += α
        
        if returnDecays:
            return y, yd
        else:
            return y

@modelfunction(coefficients=("p*"),
               title="CompoundTransient")
def compound_transient(x:np.ndarray | Real,
                       func:typing.Callable, 
                       *coefficients:Real, 
                       returnDecays = False) -> np.ndarray | float:
    r"""Compound transients signal -- linear sum of delayed single transients
    Parameters:
        x       — 1D predictor vector
        func    — model function generating a single transientl; this MIUST be one
            of the model functions defined here (i.e. wrapped by model_function)
        
        coefficients = sequence of coefficients, in the order expected by 'func'
            There must be 𝒏 × 𝒎 coefficients, where 𝒏 is the number of single
            transients, and 𝒎 is the number of coefficients expected by 'func'.
        
    Returns:
        y   = realization of the compound signal model curve
        yc  = list of individual transient models within the compound signal
    
        When returnDecays is True, it also returns:
        ycd = list of individual decay components for each single transient
        
        NOTE: for a single-component transient, y and yc contain the same data
        
    """
    #print("parameters", parameters)
    
    x = check_independent_variable(x)
    
    assert is_modelfunction(func), f"Single transient function {func.__name__} must be a model function"
    
    singlecoeffs = func.coefficients
    
    
    if len(parameters) == 1 and isinstance(parameters[0], typing.Sequence):
        parameter = parameters[0]
    
    # NOTE: 2017-12-26 00:06:38
    # this is so that the function can be used with scipy.integrate.quad
    if isinstance(x, Real):
        y = 0
        #print("parameters: ", parameters)
        #print("x: ", x)
        for p in parameters:
            #print("p: ", p)
            y += exponential_rise_multi_decays(x, p)
        
        return y # NOTE: returns one scalar !!!
    
    else:
        if x.ndim > 1:
            raise ValueError("Vector x must have exactly one dimension (i.e., a column vector)")
        
        y = np.zeros(x.shape)
        
        yc = list()
        
        ycd = list()
        
        for p in parameters:
            #print("p", p)
            
            (yc_, ycd_) = exponential_rise_decays_product_biased_shifted_model(x, p, True)

            y += yc_
            
            yc.append(yc_)
            
            ycd.append(ycd_)

        if returnDecays:
            return y, yc, ycd
        
        else:
            return y, yc
        
@modelfunction(coefficients=("γ", "ϵ", "χ", "σ"),
               title="MarkwardtNilius88")
def Markwardt_Nilius(x:np.ndarray|Real, γ:typing.Sequence[Real]|Real|np.ndarray, /,
                     ϵ:typing.Optional[Real]=None, 
                     χ:typing.Optional[Real]=None, 
                     σ:typing.Optional[Real]=None) -> np.ndarray | float:
    r"""Markwardt & Nilius model for voltage-gated Ca2+ channels I-V relationship
    
    Implements:
    
            y = γ × (x - ϵ) / ( 1 + exp(-(x-χ)/σ))
    
    See Markwardt & Nilius (1988), J Physiol (London)
    
    Parameters:
    ========== 
    x   = column vector (np.array) with membrane voltage (Vm) data
    
    The model parameters are (real scalars, corresponding to units in parentheses):
    
    γ  = slope conductance (nS)
    
    ϵ  = extrapolated reversal potential (mV) of the current (from slope conductance)
        i.e. same as the Thevenin equivalent e.m.f.
        
    
    χ  = the "delay"
    
    σ  = slope parameter of Ca2+ channel activation (mV)
    
    Returns:
    ======== 
    
    A column vector Im = f(Vm) were f is the Markwardt & Nilius model
    
    """
    # v  = Vm at half-maximal current activation (mV) (i.e. taken on the rising 
    #     region of the I(V) curve)
    
    γ, ϵ, χ, σ = check_unpack_model_coeffs(4, γ)
        
    y = γ * (x - ϵ) / (1 + np.exp(-(x-χ)/σ))
    
    return y

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

@modelfunction(coefficients = ("a", "b", "c", "x0"),
               title="TalbotSayer96")
def Talbot_Sayer(x:typing.Union[Real, np.ndarray], a:typing.Union[Real, typing.Sequence[Real], np.ndarray], /,
                 b:typing.Optional[Real]=None, c:typing.Optional[Real]=None, 
                 x0:typing.Optional[Real]=None, **kwargs) -> np.ndarray | float:
    r"""
    Talbot & Sayer model for voltage-gated Ca2+ channels I-V relationship.
    
    Boltzman squared, multiplied by Goldman-Hogdkin-Katz, 
    see Talbot & Sayer 1996, J. Neurophysiol. 76(3):2120-2124
    
    Positional parameters:
    =====================
    
    x   = 1D numpy array (vector): definition domain (e.g. membrane voltage) ↦ Voltage units
    
    a   = real: initial value for Boltzman slope factor ↦ pq.dimensionless
    
    b   = real: initial scale value ↦ mV × mM / pA  = kg × mol/(m × s³ × A²)
                                                    = kg × mol/(m × s³ × C² × s⁻²)
    
    c   = real: initial value for internal Ca2+ concentration ↦ concentration units (typically, mM)
    
    x0  = real: initial value of onset ("shift") ↦ units of 'x' (i.e., Voltage)
    
    Var-keyword parameters 
    ======================
    
    t   = python quantity: temperature in degrees Celsius (degC); default: 33 degC
    
    o   = python quantity: external Ca²⁺ concentration, in mM; default: 2.5 mM
    
    Returns:
    =======
    A realization of the I-V model function in 
    Talbot & Sayer 1996, J. Neurophysiol. 76(3):2120-2124
    as a numpy vector
    
    
    NOTE:
    Do not use directly in curve fitting, as it expects more arguments
    that the model parameters. The extra arguments are given as keyword
    arguments. If used directly in fitting, then expected keyword arguments WILL
    get their default values.
    
    """
    # t = 33 * pq.degC, o = 2.5 * pq.mM):
    from scipy import constants
    
    # default values
    t_ = 33
    o = 2.5 * pq.mM
    
    if isinstance(a, typing.Sequence) and len(i) == 4 and all(isinstance(v, (Real, pq.Quantity)) for v in i):
        a, b, c, x0 = check_unpack_model_coeffs(a, 4)
    
    if len(kwargs) > 0:
        if "t" in kwargs:
            t = kwargs["t"]
        
            if isinstance(t, pq.Quantity) and t.dimensionality == (1*pq.degC).dimensionality:
                t_ = t.magnitude
                
            elif isinstance(t, Real):
                t_ = t
                
            else:
                raise TypeError("Was expecting 't' (temperature) as a real scalar or a python quantity in degC. got %s instead" % type(t).__name__)
        
        if "o" in kwargs:
            o = kwargs["o"]
            
            if isinstance(o, Real):
                o *= pq.mM
                
            else:
                if not isinstance(o, pq.Quantity) or o.dimensionality != (1*pq.mM).dimensionality:
                    raise TypeError("Was expecting 'o' (external Ca2+ concentration) as a real scalar or a python quantity in mM; got %s instead" % type(o).__name__)
            
            
    
    T = constants.convert_temperature(t_, "Celsius", "Kelvin") * pq.degK
    
    F = constants.physical_constants["Faraday constant"][0] * pq.C/pq.mol
    
    R = constants.physical_constants["molar gas constant"][0] * pq.J/(pq.mol * pq.degK)
    
    k = F/(R*T) # NOTE: this is in C/J i.e. 1/V, because 1V  = 1J/C
    
    k = k.rescale(1/pq.mV) #  because x is in mV
    
    #print(k)
    
    #k = 0.0379
    
    # see Kay & Wong (1987) J. Physiol, 392:603-616 ↦ Boltzmann eqn squared
    # NOTE: 2025-12-02 21:08:00
    # dimensional analysis:
    # k * (x-x0) = 1/V * V = dimensionless
    boltzmann = 1 / (1 + np.exp(-a * k.magnitude * (x-x0)))**2 # ↦ pq.dimensionless
    
    ghkexp = np.exp(-2 * x * k.magnitude) # ↦ pq.dimensionless (see NOTE: 2025-12-02 21:08:00)
    
    # Goldman-Hogkin-Katz current equation
    ghk = x * b * (c - o.magnitude * ghkexp) / (1-ghkexp)

    return boltzmann * ghk # ↦ Current units (typically, pA)

@modelfunction(coefficients = ("α*", "β*", "σ*", "δ"))
def gaussianSum1D(x:np.ndarray | Real, *args, **kwargs) -> np.ndarray | float:
    r""" Sum of shifted Gaussians in 1D.
    
    Implements:
    
        y = α₀   × exp(-((x-β₀)/σ₀)²) + 
            α₁   × exp(-((x-β₁)/σ₁)²) + 
            ⋮
            αₖ   × exp(-((x-βₖ)/σₖ)²) +
            ⋮
            αₙ₋₁ × exp(-((x-βₙ₋₁)/σₙ₋₁)²) + 
            δ
            
        for a sum of shifted n+1 1D Gaussians on top of a common offset δ
    
        Model parameters: 
        α₀ ⋯ αₙ₋₁ : scales for each Gaussian
        β₀ ⋯ βₙ₋₁ : shift of each Guassian on the 'x' axis
        σ₀ ⋯ σₙ₋₁ : "spread" of each Gaussian
        δ         : common offset in 'y' axis
        
    
    Parameters:
    ==========
    
    x = 1D numpy array: the domain of definition
    
    Var-positional parameters:
    ==========================
    
    EXACTLY n * 3 + 1 elements: α₀, β₀, σ₀, …, αₖ, βₖ, σₖ, ... αₙ₋₁, βₙ₋₁, σₙ₋₁, δ
    
    for n 1D Gaussian curves
    
    If packed in a sequence, it can be unpacked by passing it as a starred expression
    in the function call.
    
    keyword parameters:
    ===================
    
    components: bool, default False: 
    
                when False, the function returns the compound Gaussian only, as 
                            a numpy array ("column vector")
            
                when True, the function returns a tuple containing the compound 
                            Gaussian as above, and a matrix with each individual 
                            Gaussian component in its columns
    
    """
    #print("gaussianSum1D args: ", args)
    
    components = False
    
    if len(kwargs) and "components" in kwargs:
        components = kwargs["components"]
    
    # NOTE: 2018-09-14 09:42:08
    # find out how many gaussians are specified by the parameters
    ngauss, rem = divmod(len(args), 3)
    
    if ngauss < 1 or rem != 1:
        raise RuntimeError("There must be exactly n * 3 + 1; got %d instead" % len(args))
    
    #print(x.shape[0])
    
    #ygauss = np.full([x.shape[0], ngauss], 0)
    ygauss = np.full([x.shape[0], ngauss], np.nan)
    
    #print("ygauss shape: ", ygauss.shape)
    
    for k in range(ngauss):
        α, β, γ = args[slice(k*3, k*3+3)]
        ygauss[:,k] = α * np.exp(-((x-β)/γ)**2)
        
    ret = np.nansum(ygauss, axis=1) + args[-1]
    
    #print("return shape: ", ret.shape)
    
    if components:
        return ret, ygauss + args[-1]
    
    return ret
    
@modelfunction(coefficients=("τ", "x0"))
def Frank_Fuortes(x:np.ndarray | Real, 
                  τ:Real | typing.Sequence[Real], /,  
                  x0: typing.Optional[Real] = None) -> np.ndarray | float:
    r""" Frank & Fuortes 1956 expression Irh/I = 1 - exp(-(t-t0)/tau)
    
    In the Frank & Fuortes 1956 paper, Irheo is a constant experimentally measured.
    Use this to get the membrane time constant only.
    
    The original equation (1) is used for the determination of the 
    membrane time-constant from strength-latency relationship.
    
    Irh/I = 1 - exp(-t/tau)                                         (1)
    
        where Irh (rheobase curent) is measured experimentally as the 
        smallest I value where AP are fired.
        
    In practice, the following equation is used:
    
    Irh/I = 1 - exp(-(t-t0)/tau)                                    (2)
        
        where t0 is a small "delay" i.e., the smallest latency used in the 
        experiment.
        
        This helps the fit as latency approaches 0.
            
    References:
    
    Frank & Fuortes (1956) Stimulation of spinal motoneurones with 
    intracellular electrodes. J.Physiol. 134, 451-470
    """
    if isinstance(τ, typing.Sequence) and len(τ) == 2 and all(isinstance(v, float) for v in τ):
        τ, x0 = τ
        
    if not all(isinstance(v, float) for v in (τ, x0)):
        raise TypeError("Expecting a sequence of two float scalars or a comma-separated list of two scalars")

    return 1-np.exp(-(x-x0)/tau)

@modelfunction(coefficients=("irh", "τ", "x0"))
def Frank_Fuortes2(x:np.ndarray | Real, irh:typing.Sequence[Real] | Real, /,
                   τ:typing.Optional[Real] = None, 
                   x0: typing.Optional[Real] = None) -> np.ndarray | float:
    r""" Implements 1/I = (1-exp(-t/tau)) / Irh 
    
    By rearranging the Frank & Fuortes 1956 equation
    one can also get a fitted value for Irheobase 
    
    1/I = (1-exp(-t/τ)) / Irh                                     (2)
    
    where t = x - x0
    
    References:
    
    Frank & Fuortes (1956) Stimulation of spinal motoneurones with 
    intracellular electrodes. J.Physiol. 134, 451-470
    """
    if isinstance(irh, typing.Sequence) and len(irh) == 3 and all(isinstance(v, float) for v in irh):
        irh, τ, x0 = irh
        
    if not all(isinstance(v, float) for v in (irh, τ, x0)):
        raise TypeError("Expecting a sequence of three float scalars or a comma-separated list of three scalars")
    
    return (1-np.exp(-(x-x0)/τ)) / irh

@modelfunction(coefficients=("x0", "κ"),
               expression = sympy.Eq(sympy.Symbol("y"),
                                     sympy.functions.elementary.piecewise.Piecewise((1/(1+sympy.exp(-(sympy.Symbol("x")-sympy.Symbol("x_0"))/sympy.Symbol("kappa"))),
                                                                                     sympy.Symbol("activation")),
                                                                                    (1/(1+sympy.exp((sympy.Symbol("x")-sympy.Symbol("x_0"))/sympy.Symbol("kappa"))),
                                                                                     sympy.Symbol("inactivation")))),
               )
def Boltzmann(x:np.ndarray | Real, x0:typing.Sequence[Real] | Real, /,
              κ:typing.Optional[Real] = None,
              pos:bool=True) -> np.ndarray | float:
    r""" Boltzmann function — empirical description of voltage-gated ion channel kinetics

Realises y = 1/(1+exp(±(x₀ - x)/κ))

Parameters:
==========
x: float scalar (e.g., membrane voltage)

p: array-like, with two float elements: x₀ and κ (in THIS order)

pos: bool, optional (default is True) — the sign of the exponent:
    When True, the function uses a positive exponential argument (e.g. useful
    to fit an activation curve)

    When False, the exponential argument is negative (e.g., useful to fit an 
    inactivation curve)

Returns:
========
A scalar (e.g., membrane current)

Notes:
======

Boltzmann's equation is commonly used to describe the voltage-dependent gating
of voltage-gated ion channels:

    Activation:

    Iₘ = 1/(1+exp((V½ - Vₘ)/κ))                                 (1)

    Inactivation:

    Iₘ = 1/(1+exp(-(V½ - Vₘ)/κ))                                (2)

where:

Iₘ can be:
    ∘ the recorded membrane current at a range of Vₘ values, normalized to 
        the maximal recorded current value

    ∘ fractional open time (for recordings from a small number of channels, 
        see e.g., Magee & Johnston, JPhysiol, 1995) - by definition 
        normalized.

    ∘ chord or slope conductance normalized to maximal value, e.g., see
        Magee & Johnston 1995

    When all other channels are blocked, Iₘ is specific to the studied
    channels.

Vₘ is the membrane voltage

V½ is the "half-maximum" voltage - the voltage where ensemble channel 
current is half the maximum, or where half of the channels are active

κ is a "slope" factor; when fitting I-V (or G-V) relationships, κ usually is
𝒛𝑹𝑻/𝑭 (e.g., see Cui et al, 1997, J Gen Physiol), where:

𝒛  apparent gating charge [C]
𝑻  temperature [K]
𝑹  molar gas constant 8.31446261815324 [J K⁻¹ mol⁻¹]
𝑭  Faraday constant 96485.33212331001 [C mol⁻¹]

NOTE V½ and κ are often different for activation and inactivation

Let ξ = (V½ - Vₘ)/κ


Then:

(Vₘ-V½)/κ = -ξ

and:

1/(1+exp(-ξ)) = 1/(1+1/exp(ξ)) = exp(ξ)/(1+exp(ξ)) = exp(ξ) × 1/(1+exp(ξ))
|___________|                                                 |__________|
inactivation                                                   activation

(NOTE the change in sign of the exponential argument!)

When fitting experimental data, the fitted parameters are x₀ and κ.

The equation is also an empyrical model of the "gating" mechanism for 
voltage dependent channels Naᵥ and Kᵥ in the Hodgkin-Huxley formalism.
    
"""
    if isinstance(x0, typing.Sequence) and len(x0)==2 and all(isinstance(v, Real) for v in x0):
        x0, κ = z0
    
    # sign of ξ
    ξ = x0 - x if pos else x - x0
    ξ /= κ
    return 1/(1+np.exp(ξ))
    
@modelfunction(coefficients=("x0", ),
               expression = r"$\theta(x) = \begin{cases} 0 & \text{for}\: x = 0 \\1 & \text{for}\: x > 0 \end{cases}$",
               )
def Heaviside(x:np.ndarray|Real, 
              x0:typing.Union[Real, pq.Quantity], /, 
              α:bool=True) -> np.ndarray | float:
    r"""Heaviside (step) function.

    Description:
    =============
    
    Step transition between two levels (0 and 1) :

    r"$\theta(x) = \begin{cases} 0 & \text{for}\: x = 0 \\1 & \text{for}\: x > 0 \end{cases}$"
    
    Parameters:
    ===========
    x: domain vector
    x0: coordinate of the step change (in domain space)
    α: bool, default is True.
        Flag for the direction of step change:
        True (default) → 0 → 1 transition
        False ⇒ transition 1 → 0
        
    """
    from core.datatypes import is_vector
    if not is_vector(x):
        raise TypeError(f"Domain (x) is not a vector")
    
    if isinstance(x0, np.ndarray):
        if x0.size != 1:
            raise TypeError(f"x0 expected an array of size 1; got {x0.size} instead")
        
    elif not isinstance(x0, float):
        raise TypeError(f"x0 must be a scalar float or an array with size 1")
        
    # if all(isinstance(v, pq.Quantity) for v in (x, x0)):
    if isinstance(x, pq.Quantity):
        if isinstance(x0, pq.Quantity):
            if not scq.unitsConvertible(x,x0):
                raise TypeError(f"x and x0 have incompatible units")
            
            if x.units != x0.units:
                x0 = x0.rescale(x.units)
                
            x0 = x0.magnitude.flatten()[0]

        x = x.magnitude
                
    else:
        if isinstance(x0, pq.Quantity):
            warnings.warn(f"x0 is a quantity but the domain is not; will strip the units from x0")
            x0 = x0.magnitude.flatten()[0]
            
    x = x.flatten()
    
    xx = x - x0
    
    ν = 0. if α else 1.
    λ = 1. if α else 0.
    
    y = np.full_like(x, fill_value = ν)
    y[xx >= 0] = λ
    
    return y
    
@modelfunction(coefficients=("x0",),
               title="GenericHeaviside")
def Heaviside2(x:np.ndarray|Real, 
              x0:typing.Union[Real, pq.Quantity], 
              level0:Real=0., level1:Real=1.) -> np.ndarray | float:
    """Heaviside (step) function - general version
    
    Step transition from level0 to level1. by default the levels are
    0. and 1. (floats)
    
    Parameters:
    ===========
    x: domain vector
    x0: coordinate of the step change (in domain space)
    level0, level1:float; optional, defaults are 0 and 1, respectively
        The initial and the final level of the step function.
        
    """
    from core.datatypes import is_vector
    
    if not is_vector(x):
        raise TypeError(f"Domain (x) is not a vector")
    
    if isinstance(x0, np.ndarray):
        if x0.size != 1:
            raise TypeError(f"x0 expected an array of size 1; got {x0.size} instead")
        
    elif not isinstance(x0, float):
        raise TypeError(f"x0 must be a scalar float or an array with size 1")
        
    # if all(isinstance(v, pq.Quantity) for v in (x, x0)):
    if isinstance(x, pq.Quantity):
        if isinstance(x0, pq.Quantity):
            if not scq.unitsConvertible(x,x0):
                raise TypeError(f"x and x0 have incompatible units")
            
            if x.units != x0.units:
                x0 = x0.rescale(x.units)
                
            x0 = x0.magnitude.flatten()[0]

        x = x.magnitude
                
    else:
        if isinstance(x0, pq.Quantity):
            warnings.warn(f"x0 is a quantity but the domain is not; will strip the units from x0")
            x0 = x0.magnitude.flatten()[0]
            
    x = x.flatten()
    
    xx = x - x0
    
    y = np.full_like(x, fill_value = level0)
    y[xx >= 0] = level1
    
    return y
    
@modelfunction(coefficients = ("x0", "x1"),
               title="Boxcar")
def boxcar(x:np.ndarray | Real, x0:typing.Union[typing.Sequence[Real], Real], /, 
           x1:typing.Optional[Real]=None, up_first:bool=True) -> np.ndarray | float:
    r"""Boxcar function: 
Two successive Heaviside (step) functions of opposite directions"""
    # x0, x1 = p
    x0, x1 = check_unpack_model_coeffs(2, x0, x1)
    
    ud = [True, False] if up_first else [False, True]
    
    if x0 < x1:
        # print(f"x0 < x1 {x0 < x1}; up_first: {up_first}")
        # up then down
        return Heaviside(x, x0, ud[0]) * Heaviside(x, x1, ud[1])
        
    else:
        # print(f"x0 >= x1 {x0 >= x1}; up_first: {up_first}")
        # down then up
        return Heaviside(x, x0, ud[0]) * Heaviside(x, x1, ud[1])# if up_first else Heaviside(x, x1, False) + Heaviside(x, x0, True)

@modelfunction(coefficients = ("x0", "x1"),
               title="GenericBoxcar")
def boxcar2(x:np.ndarray | Real, x0:typing.Union[typing.Sequence[Real], Real, np.ndarray], /, 
            x1:typing.Optional[Real]=None,
            level0:Real=0., level1:Real=1.) -> np.ndarray | float:
    r"""Boxcar function:
Two successive Heaviside2 (step) functions (general versions) in opposite directions"""
    x0, x1 = check_unpack_model_coeffs(2, x0, x1)
    
    return Heaviside2(x, x0, level0, level1) + Heaviside2(x, x1, level1, level0)

@modelfunction(coefficients = ("x0", "y0", "x1", "y1"))
def ramp(x:typing.Union[Real, np.ndarray], x0:typing.Union[Real, np.ndarray, typing.Sequence[Real]], /, 
         y0:typing.Optional[Real]=None, x1:typing.Optional[Real]=None, y1:typing.Optional[Real]=None) -> np.ndarray | float:
    r"""Linear ramp from (x₀, y₀) to (x₁, y₁)
    defaults are  = (0., 0., 1., 1.))

Parameters:
===========

x: the domain vector (e.g. time vector) - numpy array
p: the parameters in the specific order: (x₀, y₀, x₁, y₁)

"""
    x0, y0, x1, y1 = check_unpack_model_coeffs(4, x0, y0, x1, y1)
    
    if isinstance(x, pq.Quantity):
        if isinstance(x0, pq.Quantity):
            if not scq.unitsConvertible(x,x0):
                raise TypeError(f"x and x0 have incompatible units")
            
            if x.units != x0.units:
                x0 = x0.rescale(x.units)
                
            x0 = x0.magnitude.flatten()[0]

        if isinstance(x1, pq.Quantity):
            if not scq.unitsConvertible(x,x1):
                raise TypeError(f"x and x1 have incompatible units")
            
            if x.units != x1.units:
                x1 = x1.rescale(x.units)
                
            x1 = x1.magnitude.flatten()[0]

        x = x.magnitude
                
    else:
        if isinstance(x0, pq.Quantity):
            warnings.warn(f"x0 is a quantity but the domain is not; will strip the units from x0")
            x0 = x0.magnitude.flatten()[0]
            
        if isinstance(x1, pq.Quantity):
            warnings.warn(f"x1 is a quantity but the domain is not; will strip the units from x0")
            x1 = x1.magnitude.flatten()[0]
            
    x = x.flatten()
    y = np.full_like(x, fill_value = y0)
    
    xx0 = x-x0
    xx1 = x-x1
    
    α = (y1-y0)/(x1-x0)
    
    y[xx1 >= 0] = y1
    y[xx0 < 0] = y0
    ndx = (xx0 >= 0) & (xx1 < 0)
    y[ndx] = α * xx0[ndx]
    
    return y
    
def model_parameter_names(func) -> list[str]:
    r"""WARNING: on its way to become DEPRECATED 
    Model functions should be defined using the @modelfunction decorator
    (see function modelfunction(…) in this module)
    """
    sig_dict = signature_as_dict(func)
    names = list()
    if len(sig_dict["positional"]) > 1:
        names.extend(list(sig_dict["positional"].keys())[1:])
        
    if len(sig_dict["named"]):
        names.extend(list(sig_dict["named"]))
        
    return names
        

def is_modelfunction(func:typing.Callable):
    if not isinstance(func, typing.Callable):
        return False
    
    return isinstance(getattr(func, "model_function", None), bool) and isinstance(getattr(func, "nvars", None), int)

def get_initial_coefficient_values(func:typing.Callable) -> pd.DataFrame | None:
    if not is_modelfunction(func):
        raise TypeError(f"{func} is not a model function")
    
    if len(func.coefficients) == 0:
        if func.n_coefficients <= 0:
            print(f"The the model function {func.__name__} (entitled {func.title}) has variadic coefficients.\n")
            print(f"You need to supply these values manually")

def make_initial_coeffs(names:typing.Sequence[str]| dict, /, 
                        initial:typing.Optional[typing.Sequence[float | pq.Quantity | np.ndarray | np.float64]] = None, 
                        lower:typing.Optional[typing.Sequence[float | pq.Quantity | np.ndarray | np.float64]] = None,
                        upper:typing.Optional[typing.Sequence[float | pq.Quantity | np.ndarray | np.float64]] = None, 
                        feasible:typing.Optional[typing.Optional[typing.Sequence[bool] | bool]] = None) -> pd.DataFrame | None:
    
    if isinstance(names, dict):
        # coeff_name ↦ Sequence(intial, lb, ub, keep_feasible)
        assert all(isinstance(v, typing.Sequence) and len(v) in (3,4) for v in names), f"Wrong coefficient specification: {names}"
        n_coeffs = len(names)
        coeff_names = list()
        ret = {"Initial Value": list(), "Lower Bound": list(), "Upper Bound": list(), "Keep Feasible": list()}
        for k,v in names.items():
            coeff_names.append(k)
            iv, lb, ub = v[:-1]
            kf = v[3] if len(v) == 4 else None
            ret["Initial Value"].append(iv)
            ret["Lower Bound"].append(lb)
            ret["Upper Bound"].append(ub)
            ret["Keep Feasible"].append(kf)
            
        setkf = tuple(filter(lambda v: isinstance(v, bool), ret["Keep Feasible"]))
        if len(setkf) not in (1, n_coeffs):
            raise ValueError(f"Either ALL {n_coeffs} coefficients or only one of them must specify keep feasible")
        
        if len(setkf) == 1:
            ret["Keep Feasible"] = list(map(lambda k: setkf[0], range(n_coeffs)))
            
        elif len(setkf) == 0:
            ret["Keep Feasible"] = list(map(lambda k: False, range(n_coeffs)))
            
        return pd.DataFrame(data = ret, index = coeff_names)
            
    if isinstance(names, typing.Sequence):
        ret = dict()
        assert len(names) > 0 and all(isinstance(v, str) for v in names), "'names' should contain strings"
        n_coeffs= len(names)
        
        assert isinstance(initial, typing.Sequence) and len(initial) == n_coeffs and all(isinstance(v, (float, np.ndarray, np.float64)) for v in initial), f"Incorrect specification of initial values: {initial}"
        assert isinstance(lower, typing.Sequence) and len(lower) == n_coeffs and all(isinstance(v, (float, np.ndarray, np.float64)) for v in lower), f"Incorrect specification of lower bounds: {lower}"
        assert isinstance(upper, typing.Sequence) and len(upper) == n_coeffs and all(isinstance(v, (float, np.ndarray, np.float64)) for v in upper), f"Incorrect specification of upper bounds: {upper}"
        
        if isinstance(feasible, bool):
            feasible = list(map(lambda k: feasible, range(n_coeffs)))
            
        elif isinstance(feasible, typing.Sequence):
            if not all(isinstance(v, bool) for v in feasible):
                raise TypeError("'feasible' should contain only bool values")
            if len(feasible) == 0:
                feasible = list(map(lambda k: False, range(n_coeffs)))
                
            elif len(feasible) == 1:
                feasible = list(map(lambda k: feasible[0], range(n_coeffs)))
                
            elif len(feasible) != n_coeffs:
                raise ValueError(f"Incorrect number of elements in 'feasible'; expecting {n_coeffs}, got {len(feasible)} instead.")
            
        elif isinstance(feasible, np.ndarray):
            assert feasible.size in (1, n_coeffs), f"Incorrect number of elements in 'feasible'; expecting {n_coeffs}, got {len(feasible)} instead."
            assert feasible.dtype == np.dtype("bool"), "'feasible' should be a bool array"
            if feasible.size == 1:
                feasible
        
    
