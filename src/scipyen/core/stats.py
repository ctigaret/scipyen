# -*- coding: utf-8 -*-
# $Id: stats.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
Module with utilities for statistics
"""

import numbers, typing, warnings, traceback
from functools import partial
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from matplotlib.axes import Axes as Axes
import quantities as pq


def test_normality_skewtest_MC(x:np.ndarray, axis:int=0, /, 
                               plot:typing.Union[bool, Axes]=None,
                               **kwargs) -> float | np.ndarray:
    r"""Normality test based on the skewness of ``x`` using Monte Carlo simulations.

See `scipy.stats.monte_carlo_test <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.monte_carlo_test.html#scipy.stats.monte_carlo_test>`_
for details/

Parameters
==========
x: numpy ND array;
axis: array axis (if array is NOT 1D vector)
plot:boo | Axes, optional(dfault is None)
    When True, a PDF of the distribution in ``x`` will be plotted with the PDF
    of an standard normal distribution, in a new plot window & axes
    When an Axes object, the PDFs will be plotted on those axes.
    
    The None (default), no plots will be generated,

Var-keyword parameters
======================
These are passed to ``scipy.stats.monte_carlo_test`` function. Their default values
are as defined for ``scipy.stats.monte_carlo_test``

n_resamples:int — default = 9999
batch:int — default = None
alternative: str — {"two-sided", "less", "greater"}; default = "two-sided"

**NOTE** the following are ignored in ``kwargs``: 
``axis``, ``rsv``, ``vectorized``

Returns
=======
𝑝 value of the Monte Carlo test: the propability that the data distribution is
    drawn from a normal dstribution with mean 0
"""
    from plots.plots import plot_normal_pdf
    # remove var-keyword parameters that are alrady supplied or pre-set
    # 
    kwargs.pop("axis", None)        # already given as named parameter
    kwargs.pop("rsv", None)         # set to stats.norm.rsv, below as we only test for normality here
    kwargs.pop("vectorized", None)  # set to True, below as we are interested in 1D data
    title = kwargs.pop("title", "Skew Test — Normal Distribution")
    
    if isinstance(x, pq.Quantity):
        x = x.magnitude # strip away the units
        
    # axskwt = partial(stats.skewtest,axis=axis)
    statistic = lambda x, axis: stats.skewtest(x, axis=axis).statistic
    
    ret = stats.monte_carlo_test(x, stats.norm.rvs, statistic, vectorized = True, 
                                 axis = axis, **kwargs)
    
    if isinstance(plot, Axes):
        ax = plot
    elif isinstance(plot, bool) and plot:
        fig, ax = plt.subplots(figsize = (8,6))
    else:
        ax = None
        
    if ax:
        stats_val = np.linspace(-5, 5, 100)
        ax.clear()
        plot_normal_pdf(ax, stats_val, title = f"{title}: 𝒑 = {float(ret[0])}")
        ax.hist(ret.null_distribution, stats_val, density = True)
        ax.legend(['Normal distribution\n(Asymptotic approximation)',
                   f'Monte Carlo approximation\n{x.shape[0]} observations'])
        
    return ret.pvalue
        
