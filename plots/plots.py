# -*- coding: utf-8 -*-
"""Plot utitilies
Functions for plotting with matplotlib and seaborn
"""
#### BEGIN core python modules
import numbers, typing, warnings
from functools import partial
#### END core python modules

#### BEGIN 3rd party modules
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.mlab as mlb
from matplotlib.axes import Axes as Axes
# NOTE: 2019-07-29 18:27:45
mpl.rcParams['backend']='Qt5Agg'
mpl.rcParams["savefig.format"] = "svg"
mpl.rcParams["xtick.direction"] = "in"
mpl.rcParams["ytick.direction"] = "in"
mpl.rcParams["svg.fonttype"]="none"
# see NOTE: 2019-07-29 18:25:30 in pict.py
mpl.use("Qt5Agg") 
plt.rcParams['backend']='Qt5Agg'
plt.rcParams["savefig.format"] = "svg"
plt.rcParams["xtick.direction"] = "in"
plt.rcParams["ytick.direction"] = "in"
plt.rcParams["svg.fonttype"]="none"

import numpy as np
import pandas as pd
import neo
from scipy import stats
import quantities as pq
import vigra
#### END 3rd party modules

#### BEGIN pict.core modules
from core import datatypes as dt
from imaging import vigrautils as vu
from gui import (scipyen_colormaps, guiutils)
#### END pict.core modules

# from . import sb_plots
# import seaborn as sb

# TODO 2019-09-06 13:08:18
# set up a clever way to offer there plottign functions ans their arguments in 
# a gui dialog

mpl_plot_functions = dict()
# basic plotting
mpl_plot_functions["plot"]                  = Axes.plot
mpl_plot_functions["errorbar"]              = Axes.errorbar
mpl_plot_functions["scatter"]               = Axes.scatter
mpl_plot_functions["plot_date"]             = Axes.plot_date
mpl_plot_functions["step"]                  = Axes.step
mpl_plot_functions["loglog"]                = Axes.loglog
mpl_plot_functions["semilogx"]              = Axes.semilogx
mpl_plot_functions["semilogy"]              = Axes.semilogy
mpl_plot_functions["fill_between"]          = Axes.fill_between
mpl_plot_functions["fill_betweenx"]         = Axes.fill_betweenx
mpl_plot_functions["bar"]                   = Axes.bar
mpl_plot_functions["barh"]                  = Axes.barh
mpl_plot_functions["stem"]                  = Axes.stem
mpl_plot_functions["eventplot"]             = Axes.eventplot
mpl_plot_functions["pie"]                   = Axes.pie
mpl_plot_functions["stackplot"]             = Axes.stackplot
mpl_plot_functions["broken_barh"]           = Axes.broken_barh
mpl_plot_functions["vlines"]                = Axes.vlines
mpl_plot_functions["hlines"]                = Axes.hlines
mpl_plot_functions["fill"]                  = Axes.fill

# spectral
mpl_plot_functions["acorr"]                 = Axes.acorr
mpl_plot_functions["angle_spectrum"]        = Axes.angle_spectrum
mpl_plot_functions["cohere"]                = Axes.cohere
mpl_plot_functions["csd"]                   = Axes.csd
mpl_plot_functions["magnitude_spectrum"]    = Axes.magnitude_spectrum
mpl_plot_functions["phase_spectrum"]        = Axes.phase_spectrum
mpl_plot_functions["psd"]                   = Axes.psd
mpl_plot_functions["specgram"]              = Axes.specgram
mpl_plot_functions["xcorr"]                 = Axes.xcorr
        
# statistics
mpl_plot_functions["boxplot"]               = Axes.boxplot
mpl_plot_functions["violinplot"]            = Axes.violinplot
mpl_plot_functions["violin"]                = Axes.violin
mpl_plot_functions["bxp"]                   = Axes.bxp

# binned
mpl_plot_functions["hexbin"]                = Axes.hexbin
mpl_plot_functions["hist"]                  = Axes.hist
mpl_plot_functions["hist2d"]                = Axes.hist2d

# contours
mpl_plot_functions["clabel"]                = Axes.clabel
mpl_plot_functions["contour"]               = Axes.contour
mpl_plot_functions["contourf"]              = Axes.contourf

# array
mpl_plot_functions["imshow"]                = Axes.imshow
mpl_plot_functions["matshow"]               = Axes.matshow
mpl_plot_functions["pcolor"]                = Axes.pcolor
mpl_plot_functions["pcolorfast"]            = Axes.pcolorfast
mpl_plot_functions["pcolormesh"]            = Axes.pcolormesh
mpl_plot_functions["spy"]                   = Axes.spy

# unstructured triangles
mpl_plot_functions["tripcolor"]             = Axes.tripcolor
mpl_plot_functions["triplot"]               = Axes.triplot
mpl_plot_functions["tricontour"]            = Axes.tricontour
mpl_plot_functions["tricontourf"]           = Axes.tricontourf

# fields
mpl_plot_functions["barbs"]                 = Axes.barbs
mpl_plot_functions["quiver"]                = Axes.quiver
mpl_plot_functions["quiverkey"]             = Axes.quiverkey
mpl_plot_functions["streamplot"]            = Axes.streamplot



class IV2TimeScale(mpl.scale.ScaleBase):
    """For IV curves (IV ramps) this defines the linear function V(t)of the Vm 
    ramp, used to show a time axis in IV ramp plots.
    
    When plotting an IV ramp, Im is plotted as function of Vm (I(V)) whereas the
    time-course of the ramp is not shown.
    
    However, it is useful sometimes to know WHEN, during the ramp, a particular 
    I(V) occurs (e.g., for data selection purposes).The time domain is there 
    already, because both Im and Vm are AnalogSignals; it is just not shown by 
    the IV plot, by default.
    
    This class enables the use of an additional "x" axis oin the IV plot, to 
    indicate the time domain of the Vm ramp.
    
    DURING the Vm ramp:
    
    V(t) = a * (t - t0) + V0; 
    
    where:
        a = slope = dV/dt
        t0 = "onset" (or "delay")
        V0 = constant "offset"
        
    Given V(t) and V0, the V2time scaling function is
    
    t = t0 + (V-V0)/a
    
    And the inverse function is the linear V(t) as above.
    
    """
    
    name = "iv2time"
    
    def __init__(self, axis, **kwargs):
        """Receives keyword arguments via a call to "set_xscale".
        
        Additional keywords:
        
        slope: default 1 V/s
        V0   : default -80 mV
        t0   : default 0 s
        """
    
        mpl.scale.ScaleBase.__init__(self)
        
        slope  = kwargs.pop("slope", 1 * pq.V / pq.s)
        V0 = kwargs.pop("V0", -80 * pq.mV)
        t0 = kwargs.pop("t0", 0 * pq.s)
        
        self.slope = slope
        self.V0 = V0
        self.t0 = t0
        
        
    def get_transform(self):
        return self.V2TimeTransform(self.slope, self.V0, self.t0)
    
    # NOTE: 2017-09-18 09:28:03
    # definitely needed
    #
    def set_default_locators_and_formatters(self, axis):
        class TimeFormatter(mpl.ticker.Formatter):
            def __call__(self, x, pos = None):
                return "%s" % str(x)
            
        axis.set_major_locator(mpl.ticker.AutoLocator)
        #axis.set_major_locator(mpl.ticker.LinearLocator)
        axis.set_major_formatter(TimeFormatter)
        axis.set_minor_formatter(TimeFormatter)
        
    # NOTE: 2017-09-18 09:29:08
    # probably don't need this either
    #
    #def limit_range_for_scale(self, vmin, vmax, minpos):
        #pass
    
    
    
    class V2TimeTransform(mpl.transforms.Transform):
        input_dims = 1
        output_dims = 1
        is_separable = True
        
        def __init__(self, slope, V0, t0):
            mpl.transforms.Transform.__init__(self)
            
            self.slope = slope
            self.V0 = V0
            self.t0 = t0
            
        # contyemplate the use of masked arrays to keep the time values 
        # strictly within the RAMP region
        def transform_non_affine(self, a):
            """Returns the time when Vm equals a
            """
            
            return self.t0 + (a-self.V0)/self.slope
        
        def inverted(self):
            return IV2TimeScale.InvertedV2TimeTransform(self.slope, self.V0, self.t0)


    class InvertedV2TimeTransform(mpl.transforms.Transform):
        input_dims = 1
        output_dims = 1
        is_separable = True
        
        def __init__(self, slope, V0, t0):
            mpl.transforms.Transform.__init__(self)
            self.slope = slope
            self.V0 = V0
            self.t0 = t0
            
        def transform_non_affine(self, a):
            return self.slope * (a - self.t0) + self.V0; 
        
        def inverted(self):
            return IV2TimeScale.V2TimeTransform(self.slope, self.V0, self.t0)
        
mpl.scale.register_scale(IV2TimeScale)
    

def zeroCrossedAxes(fig, axisStyle, *args, **kwargs):
    """ Creates zero-crossing axes in a matplotlib figure
    
    Arguments:
    fig = a matplotlib.figure.Figure instance
    
    axisStyle =  style string (e.g. "->" or "-|>") or None 
        (type ax.axis["xzero"].set_axisline_style() for possible styles, and
         see mpl_toolkits.axisartist.axis_artist.AxisArtist)
         
    *args, **kwargs - see mpl_toolkits.axes_grid.axislines.SubplotZero
    
    Returns 
    An instance of matplotlib.axes._subplots.AxesZeroSubplot axes.
    
    These can be used to plot, e.g.:
    
    ax = zeroCrossedAxes(fig, 111)
    ax.plot(...)
    
    See also demo_axisline_style.py in matplotib axes_grid examples
    
    https://matplotlib.org/2.0.2/examples/axes_grid/index.html
    
    from which this was taken.
    
    """
    from mpl_toolkits.axisartist.axislines import SubplotZero
    from mpl_toolkits.axes_grid1 import host_subplot    
    import mpl_toolkits.axisartist as AA
    
    #ax = SubplotZero(fig, *args, **kwargs)
    #fig.add_subplot(ax)
    
    
    # NOTE: 2017-09-17 09:38:56
    # IT WORKS !
    ax = host_subplot(111, axes_class = AA.axislines.AxesZero)
    
    #ax2 = ax.twin()
    
    for direction in ["xzero", "yzero"]:
        ax.axis[direction].line.set_color("k")
        ax.axis[direction].set_axisline_style(axisStyle)
        ax.axis[direction].set_visible(True)

    for direction in ["left", "right", "bottom", "top"]:
        ax.axis[direction].set_visible(False)

    #for direction in ["xzero", "yzero", "left", "right", "bottom"]:
        #ax2.axis[direction].set_visible(False)

    return ax #, ax2
    

def plotZeroCrossedAxes(x, y, fig=None, xlabel="Vm", ylabel="Im", axisStyle="-|>", t_axis=True, newPlot = False, legend=[], **kwargs):
    """Plot y vs x as an IV plot (on zero-crossed axes).
    Arguments:
        x, y    = data to plot: must be numpy.ndarray vectors of similar lengths & shape
        
        fig     = instance of matplotlib.figure.Figure or an integer (figure number)
        
        xlabel  = str: label for X axis
        
        ylabel  = str: label for Y axis
        
        newPlot = boolean, optional (defult False); 
                    when True, old plot is removed;
                    when False, curve will be superimposed
                    
        legend = sequence of str, or empty (default); when non-empty, it must contain
                as many elements as columns in y; legend will be placed according 
                to the "best" location (see documentation for pyplot.legend())
                
                If this is not what is intended, then follow this steps:
                
                (1)
                    * specify the "label" parameter in kwargs (when y has ONE column), 
                    
                    OR
                
                    * use :artist:.set_label() on each of the resulted Line2D objects
                    (Returned by this function, see below)
                
                (2) Call pylot.legend(), or ax.lengend() where ax are the axes 
                returned by this function (see below). Failing that, one can 
                retrieve the axes from the current figure using fig.axes[0] and 
                continue from there.
                
        **kwargs = parameters passed directly to pyplot.plot() function
            
        Returns:
        
        lines = the list of Line2D artists generated by the plot
        ax    = the instance of AxesZeroSubplot used to plot the lines.
            
    """
    if fig is None:
        fig = plt.figure()
        
    elif isinstance(fig, numbers.Integral):
        fig = plt.figure(fig)
        
    elif isinstance(fig, mpl.figure.Figure):
        fig = plt.figure(fig.number)
        
    #print(fig)
    
    #print(newPlot)
    
    if newPlot:
        plt.clf()
        
    if len(fig.axes) > 0 and type(fig.axes[-1]).__name__ in ("AxesZeroSubplot", "AxesZeroHostAxesSubplot"): 
        ax = fig.axes[-1]
        for direction in ["xzero", "yzero"]:
            ax.axis[direction].set_axisline_style(axisStyle)
        
    else:
        ax = zeroCrossedAxes(fig, axisStyle, 111)
        
    lines = ax.plot(x,y, **kwargs) # always a list with one element
    
    if xlabel is not None:
        ax.axis["xzero"].set_label(xlabel)
        ax.axis["xzero"].line.set_color("k")
    
    if ylabel is not None:
        ax.axis["yzero"].set_label(ylabel)
        ax.axis["yzero"].line.set_color("k")
        
    if isinstance(legend, (tuple, list)) and len(legend) > 0 and len(legend) == len(lines):
        lines[0].set_label(legend[0])
        plt.legend(loc="best")
        
    elif isinstance(legend, str):
        lines[0].set_label(legend)
        plt.legend(loc= "best")

    fig.canvas.draw_idle()
    
    return lines, ax #, ax1


def plotNeoSignal(data, fig=None, label=None, newPlot=False, title = None,
                  xlabel=None, ylabel=None,
                  tick_direction="in", tick_length = 4.5, axes_offset=0,
                  despine=True, panel_size=None, **kwargs):
    """
    TODO: plot multiple signals overlaid, with legend
    """
    import neo
    if not isinstance(data, neo.core.basesignal.BaseSignal):
        raise TypeError("Expecting a subclass of neo.core.basesignal.BaseSignal; got %s instead" % type(data))
    
    x = data.times
    y = data.magnitude
    
    if fig is None:
        fig = plt.figure()
        
    elif isinstance(fig, numbers.Integral):
        fig = plt.figure(fig)
        
    elif isinstance(fig, mpl.figure.Figure):
        fig = plt.figure(fig.number)
        
    if newPlot:
        plt.clf()
        
    
    if label is None or (isinstance(label, str) and len(label.strip()) == 0):
        label = data.name
        
    if not isinstance(xlabel, str) or len(xlabel.strip()) == 0:
        xlabel = "Time (%s)" % x.dimensionality
    
    if not isinstance(ylabel, str) or len(ylabel.strip()) == 0:
        ylabel = "%s (%s)" % (data.name, data.dimensionality)
    
    
    if isinstance(label, str) and len(label.strip()):
        ret = plt.plot(x,y, label=label, **kwargs)
        plt.legend(loc="best")
    
    else:
        ret = plt.plot(x,y, **kwargs)
    
    ax = plt.gca()
    
    if despine:
        ax.spines.left.set_position(("outward", axes_offset))
        ax.spines.bottom.set_position(("outward", axes_offset))
        ax.spines.top.set_visible(False)
        ax.spines.right.set_visible(False)
        ax.yaxis.set_ticks_position("left")
        ax.xaxis.set_ticks_position("bottom")
        # sb.despine(ax = ax, offset = axes_offset)
    
    ax.tick_params("y", direction=tick_direction, length=tick_length, color="black")
        
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    
    if isinstance(title, str) and len(title.strip()):
        ax.set_title(title)
        
    fig.canvas.draw_idle()
        
    if isinstance(panel_size, (tuple, list)) and len(panel_size) ==2 and all([isinstance(v, numbers.Number) for v in panel_size]):
        fig.set_size_inches(panel_size)
    
    
def plotVigraKernel1D(val, fig=None, label=None, xlabel=None, ylabel=None, 
                      newPlot = False, plotStyle="stem", tick_direction="in", **kwargs):
    if not isinstance(val, vigra.filters.Kernel1D):
        raise TypeError("A vigra Kernel1D was expected; got %s instead" % type(val).__name__)
    
    [x,y] = vu.vK1D2array(val)
    
    if fig is None:
        fig = plt.figure()
        
    elif isinstance(fig, numbers.Integral):
        fig = plt.figure(fig)
        
    elif isinstance(fig, mpl.figure.Figure):
        fig = plt.figure(fig.number)
        
    if newPlot:
        plt.clf()
        
    ax = plt.gca()
    
    if isinstance(plotStyle, str):
        cmd = "ax." + plotStyle + "(x, y, **kwargs)"

        ret = eval(cmd)
        
    else:
        ret = ax.stem(x,y, **kwargs)
        
    if isinstance(label, str):
        ret.set_label(label)
        plt.legend(loc="best")
        
            
    fig.canvas.draw_idle()
    
    return ret

def plotVigraKernel(val, fig=None, label=None, xlabel=None, ylabel=None,
                      newPlot=False, plotStyle=None, tick_direction="in",
                      **kwargs):
    """
    Important kwargs:
    ----------------
    plotStyle: str: 
        for 1D kernels: any valid 1D plot command (e.g., "stem", which is also the
                    default for 1D kernels) 
                    
        for 2D kernels: "scatter", "image", or "matrix"
        
    interpolation None (default), or str as below; only for 2D kernels
        'none', 'antialiased', 'nearest', 'bilinear', 'bicubic', 'spline16', 
        'spline36', 'hanning', 'hamming', 'hermite', 'kaiser', 'quadric', 'catrom',
        'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos', 'blackman'.
    """
    if not isinstance(val, (vigra.filters.Kernel1D, vigra.filters.Kernel2D)):
        raise TypeError(f"A vigra Kernel (1D or 2D) was expected; got {type(val).__name__} instead")
    
    [x,y] = vu.kernel2array(val)
    
    if fig is None:
        fig = plt.figure()
        
    elif isinstance(fig, numbers.Integral):
        fig = plt.figure(fig)
        
    elif isinstance(fig, mpl.figure.Figure):
        fig = plt.figure(fig.number)
        
    if newPlot:
        plt.clf()
        
    ax = plt.gca()
    
    kwargs.pop("c", None)
    kwargs.pop("s", None)
    
    if isinstance(plotStyle, str):
        if isinstance(val, vigra.filters.Kernel2D):
            if not isinstance(x, list) or len(x) != 2:
                raise TypeError("Incompatible 'x' parameter for plotting a 2D kernel; expecting a meshgrid ")
            
            if plotStyle == "scatter":
                kwargs.pop("c", None)
                kwargs.pop("s", None)
                
                c = mpl.colors.Normalize(y.min(), y.max())(y).ravel()
                x_ = x[0].ravel()
                y_ = x[1].ravel()
                
                ret = ax.scatter(x_, y_, c=c, **kwargs)
                
            elif plotStyle == "image":
                #from matplotlib.image import NonUniformImage
                x_ = x[0][0,:]
                y_ = x[1][:,0]
                z = mpl.colors.Normalize(y.min(), y.max())(y)
                
                ret = ax.imshow(z, extent =  (x_.min(), x_.max(), y_.min(), y_.max()), **kwargs)
                
            elif plotStyle == "matrix":
                #from matplotlib.image import NonUniformImage
                x_ = x[0][0,:]
                y_ = x[1][:,0]
                z = mpl.colors.Normalize(y.min(), y.max())(y)
                
                ret = ax.matshow(z, extent =  (x_.min(), x_.max(), y_.min(), y_.max()), **kwargs)
                
            else:
                raise NotImplementedError(f"{plotStyle} not implemented for 2D kernels")
                
        else:
            cmd = "ax." + plotStyle + "(x, y, **kwargs)"

            ret = eval(cmd)
        
    else:
        if isinstance(val, vigra.filters.Kernel2D):
            if not isinstance(x, list) or len(x) != 2:
                raise TypeError("Incompatible 'x' parameter for plotting a 2D kernel; expecting a meshgrid ")
            
            kwargs.pop("c", None)
            kwargs.pop("s", None)
            
            c = mpl.colors.Normalize(y.min(), y.max())(y).ravel()
            x_ = x[0].ravel()
            y_ = x[1].ravel()
            
            ret = ax.scatter(x_, y_, c=c, **kwargs)
            
        else:
            ret = ax.stem(x, y, **kwargs)
            
    if isinstance(label, str):
        ret.set_label(label)
        plt.legend(loc="best")
        
            
    fig.canvas.draw_idle()
    
    return ret

        
        
    

# NOTE: 2022-04-16 20:11:11 
# from here on this is code from the matplotlib tutorial "origin and extend in imshow"
def index_to_coordinate(index, extent, origin):
    """Return the pixel center of an index."""
    left, right, bottom, top = extent

    hshift = 0.5 * np.sign(right - left)
    left, right = left + hshift, right - hshift
    vshift = 0.5 * np.sign(top - bottom)
    bottom, top = bottom + vshift, top - vshift

    if origin == 'upper':
        bottom, top = top, bottom

    return {
        "[0, 0]": (left, bottom),
        "[M', 0]": (left, top),
        "[0, N']": (right, bottom),
        "[M', N']": (right, top),
    }[index]


def get_index_label_pos(index, extent, origin, inverted_xindex):
    """
    Return the desired position and horizontal alignment of an index label.
    """
    if extent is None:
        extent = lookup_extent(origin)
    left, right, bottom, top = extent
    x, y = index_to_coordinate(index, extent, origin)

    is_x0 = index[-2:] == "0]"
    halign = 'left' if is_x0 ^ inverted_xindex else 'right'
    hshift = 0.5 * np.sign(left - right)
    x += hshift * (1 if is_x0 else -1)
    return x, y, halign


def get_color(index, data, cmap):
    """Return the data color of an index."""
    val = {
        "[0, 0]": data[0, 0],
        "[0, N']": data[0, -1],
        "[M', 0]": data[-1, 0],
        "[M', N']": data[-1, -1],
    }[index]
    return cmap(val / data.max())


def lookup_extent(origin):
    """Return extent for label positioning when not given explicitly."""
    if origin == 'lower':
        return (-0.5, 6.5, -0.5, 5.5)
    else:
        return (-0.5, 6.5, 5.5, -0.5)


def set_extent_None_text(ax):
    ax.text(3, 2.5, 'equals\nextent=None', size='large',
            ha='center', va='center', color='w')


def plot_imshow_with_labels(ax, data, extent, origin, xlim, ylim):
    """Actually run ``imshow()`` and add extent and index labels."""
    im = ax.imshow(data, origin=origin, extent=extent)

    # extent labels (left, right, bottom, top)
    left, right, bottom, top = im.get_extent()
    if xlim is None or top > bottom:
        upper_string, lower_string = 'top', 'bottom'
    else:
        upper_string, lower_string = 'bottom', 'top'
    if ylim is None or left < right:
        port_string, starboard_string = 'left', 'right'
        inverted_xindex = False
    else:
        port_string, starboard_string = 'right', 'left'
        inverted_xindex = True
    bbox_kwargs = {'fc': 'w', 'alpha': .75, 'boxstyle': "round4"}
    ann_kwargs = {'xycoords': 'axes fraction',
                  'textcoords': 'offset points',
                  'bbox': bbox_kwargs}
    ax.annotate(upper_string, xy=(.5, 1), xytext=(0, -1),
                ha='center', va='top', **ann_kwargs)
    ax.annotate(lower_string, xy=(.5, 0), xytext=(0, 1),
                ha='center', va='bottom', **ann_kwargs)
    ax.annotate(port_string, xy=(0, .5), xytext=(1, 0),
                ha='left', va='center', rotation=90,
                **ann_kwargs)
    ax.annotate(starboard_string, xy=(1, .5), xytext=(-1, 0),
                ha='right', va='center', rotation=-90,
                **ann_kwargs)
    ax.set_title('origin: {origin}'.format(origin=origin))

    # index labels
    for index in ["[0, 0]", "[0, N']", "[M', 0]", "[M', N']"]:
        tx, ty, halign = get_index_label_pos(index, extent, origin,
                                             inverted_xindex)
        facecolor = get_color(index, data, im.get_cmap())
        ax.text(tx, ty, index, color='white', ha=halign, va='center',
                bbox={'boxstyle': 'square', 'facecolor': facecolor})
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)


def generate_imshow_demo_grid(extents, xlim=None, ylim=None):
    N = len(extents)
    fig = plt.figure(tight_layout=True)
    fig.set_size_inches(6, N * (11.25) / 5)
    gs = GridSpec(N, 5, figure=fig)

    columns = {'label': [fig.add_subplot(gs[j, 0]) for j in range(N)],
               'upper': [fig.add_subplot(gs[j, 1:3]) for j in range(N)],
               'lower': [fig.add_subplot(gs[j, 3:5]) for j in range(N)]}
    x, y = np.ogrid[0:6, 0:7]
    data = x + y

    for origin in ['upper', 'lower']:
        for ax, extent in zip(columns[origin], extents):
            plot_imshow_with_labels(ax, data, extent, origin, xlim, ylim)

    columns['label'][0].set_title('extent=')
    for ax, extent in zip(columns['label'], extents):
        if extent is None:
            text = 'None'
        else:
            left, right, bottom, top = extent
            text = (f'left: {left:0.1f}\nright: {right:0.1f}\n'
                    f'bottom: {bottom:0.1f}\ntop: {top:0.1f}\n')
        ax.text(1., .5, text, transform=ax.transAxes, ha='right', va='center')
        ax.axis('off')
    return columns

def plot_Gantt(data, **kwargs):
    """
    Renders a Gantt chart plot.
    The data is organized in intervals (start, finish) with each interval being
    represented by a horizontal bar along a time axis, and is encapsulated in 
    either a neo.Epoch, or a pandas.DataFrame object
    
    Delegates to plot_Gantt_DF after converting the data to pandas DataFrame.
    
    Parameters:
    ===========
    data:neo Epoch, pandas DataFrame or sequence of such.
        WARNING: 
        When a sequence, all elements must ve of the same object type (i.e.
        NOT a mixture of neo.Epoch and pandas.DataFrame objects)!
    
        The function will call plot_Gantt_Epochs or plot_Gantt_DF accordingly,
    
        See the documentation for these functions for details.
    
    Named and var-named parameters (kwargs):
    ========================================
    
    fig: matplotib figure; optional, default is None
    
    height: int, float; height of the Gantt bars (optional, default is 20)
    
    y_interval: int, float: vertical spacing between bars (optional, default is 5)
    
    harmonize_ylims: bool; optional default is True;
        When True, all y axes get the same limits
    
    barcolors: a matplotib color specification or a sequence of such
    textcolor: a matplotib color specification or a sequence of such
    
    textpos: a str, one of "auto","top", "bottom", "above", "below", "inside"
    
    grid: bool, default is True
    
    staggered: bool; optional, default is True
        When True all intervals are plotted at increasing heights.
        When False, all intervalks are plotted at the same y coordinate.
        
        
    """
    # fig = kwargs.pop("fig", None)
    # height = kwargs.pop("height", 20)
    # y_interval = kwargs.pop("y_interval", 5)
    # harmonize_ylims = kwargs.pop("harmonize_ylims", True)
    # barcolors = kwargs.pop("barcolors", None)
    # textcolor = kwargs.pop("textcolor",None)
    # textpos = kwargs.pop("textpos", "auto")
    # grid = kwargs.pop("grid", True)
    # staggered = kwargs.pop("staggered", True)
    
    if isinstance(data, (tuple, list)):
        if all(isinstance(d, neo.Epoch) for d in data):
            func = plot_Gantt_Epochs
        
        elif all(isinstance(d, pd.DataFrame) for d in data):
            func = plot_Gantt_DF
        
        else:
            raise TypeError("Expecting a homogeneous sequence with all elements being either of neo.Epoch or pandas.DataFrame")
        
    elif isinstance(data, neo.Epoch):
        func = plot_Gantt_Epochs
    
    elif isinstance(data, pd.DataFrame):
        func = plot_Gantt_DF
    
    else:
        raise TypeError(f"Expecting a neo.Epoch, a pandas.DataFrame, or a homogeneous sequence with all elements being either of neo.Epoch or pandas.DataFrame; instead, got {type(data).__name__}")

    return func(data, **kwargs)

def plot_Gantt_Epochs(data:typing.Union[tuple, list, neo.Epoch], **kwargs):
    """
    Renders a Gantt chart plot.
    The data is organized in intervals (start, finish) with each interval being
    represented by a horizontal bar along a time axis, encapsulated in a neo
    Epoch.
    
    Delegates to plot_Gantt_DF after converting the data to pandas DataFrame.
    
    Parameters:
    ===========
    data:neo Epoch, or sequence of neo Epoch objects.
        The intervals are defined as t + d where t is each element in the Epoch
        'times' attribute, and d is an element in the Epoch's 'durations' attribute.
    
        The interval names are taken from the Epoch's 'labels' attribute.
    
        Each Epoch data is plotted is its own axis system, but all x axes are 
        shared.
    
    Named and var-named parameters (kwargs):
    ========================================
    
    fig: matplotib figure; optional, default is None
    
    height: int, float; height of the Gantt bars (optional, default is 20)
    
    y_interval: int, float: vertical spacing between bars (optional, default is 5)
    
    harmonize_ylims: bool; optional default is True;
        When True, all y axes get the same limits
    
    barcolors: a matplotib color specification or a sequence of such
    textcolor: a matplotib color specification or a sequence of such
    
    textpos: a str, one of "auto","top", "bottom", "above", "below", "inside"
    
    grid: bool, default is True
    
    staggered: bool; optional, default is True
        When True all intervals are plotted at increasing heights.
        When False, all intervalks are plotted at the same y coordinate.
        
        
    """
    from ephys import ephys
    
    # fig = kwargs.pop("fig", None)
    # height = kwargs.pop("height", 20)
    # y_interval = kwargs.pop("y_interval", 5)
    # harmonize_ylims = kwargs.pop("harmonize_ylims", True)
    # barcolors = kwargs.pop("barcolors", None)
    # textcolor = kwargs.pop("textcolor",None)
    # textpos = kwargs.pop("textpos", "auto")
    # grid = kwargs.pop("grid", True)
    # staggered = kwargs.pop("staggered", True)
    
    if isinstance(data, (tuple, list)):
        if len(data) == 0:
            warnings.warn("No data!")
            return
        
        if not all(isinstance(v, neo.Epoch) for v in data):
            raise TypeError("Expecting a sequence of neo.Epoch objects")
        
    elif isinstance(data, neo.Epoch):
        data = [data]
        
    else:
        raise TypeError(f"Expecting a neo.Epoch or a sequence (tuple, list of neo.Epoch objects; instead, got {type(data).__name__}")
                        
    kwargs["names"] = [epoch.name for epoch in data]
    data = [pd.DataFrame([dict(Task=i[2], Start=i[0], Finish=i[0]+i[1], Name = i[2] if isinstance(i[2], str) and len(i[2].strip()) else f"Interval {k}" ) for i in ephys.epoch2intervals(epoch)]) for k, epoch in enumerate(data)]
    
    return plot_Gantt_DF(data=data, **kwargs)


def plot_Gantt_DF(data:typing.Union[tuple, list, pd.DataFrame], **kwargs):
    """
    Renders a Gantt chart plot.
    The data is organized in intervals (start, finish) with each interval being
    represented by a horizontal bar along a time axis, encapsulated in a pandas
    DataFrame
    
    Parameters:
    ===========
    data: pandas DataFrame, or sequence of DataFrame objects.
        Each DataFrame must have the mandatory columns: "Start", "Finish", "Name"
        and each row represents an individual interval (plotted as a horizontal bar)
    
        Each DataFrame is plotted is its own axis system, but all x axes are shared
    
    Named and var-named parameters (kwargs):
    ========================================
    
    names: a str, sequence (tuple, or list) of str, or None;
        optional, default is None
    
    fig: matplotib figure; optional, default is None
    
    height: int, float; height of the Gantt bars (optional, default is 20)
    
    y_interval: int, float: vertical spacing between bars (optional, default is 5)
    
    harmonize_ylims: bool; optional default is True;
        When True, all y axes get the same limits
    
    barcolors: a matplotib color specification or a sequence of such
    textcolor: a matplotib color specification or a sequence of such
    
    textpos: a str, one of "auto","top", "bottom", "above", "below", "inside"
    
    grid: bool, default is True
    
    staggered: bool; optional, default is True
        When True all intervals are plotted at increasing heights.
        When False, all intervalks are plotted at the same y coordinate.
        
    """
    from matplotlib import transforms
    from matplotlib.transforms import (Bbox, TransformedBbox)
    names = kwargs.pop("names", None)
    fig = kwargs.pop("fig", None)
    height = kwargs.pop("height", 20)
    y_interval = kwargs.pop("y_interval", 5)
    harmonize_ylims = kwargs.pop("harmonize_ylims", True)
    barcolors = kwargs.pop("barcolors", None)
    textcolor = kwargs.pop("textcolor",None)
    textpos = kwargs.pop("textpos", "inside")
    grid = kwargs.pop("grid", True)
    staggered = kwargs.pop("staggered", True)
    
    if isinstance(data, (tuple, list)):
        if len(data) == 0:
            warnings.warn("No data!")
            return
        if not all(isinstance(v, pd.DataFrame) for v in data):
            raise TypeError("Expecting a sequence of pandas.DataFrame objects")
        
    elif isinstance(data, pd.DataFrame):
        data = [data]
        
    else:
        raise TypeError(f"Expecting a neo.Epoch or a sequence (tuple, list of pandas.DataFrame objects; instead, got {type(data).__name__}")

    _mandatory_DF_columns_ = ("Start", "Finish", "Name")

    if not all(all(s in d.columns for s in _mandatory_DF_columns_) for d in data):
        raise ValueError(f"DataFrame objects MUST contain the columns {_mandatory_DF_columns_}")
    
    if isinstance(names, (tuple, list)):
        if len(names) != len(data):
            raise ValueError(f"names: Expecting one str or a sequence of str with as {len(data)}")
        if not all(isinstance(v, str) for v in names):
            raise TypeError("names: Expecting a sequence of strings")
        
    elif isinstance(names,str):
        if len(names.strip()) == 0:
            names = [f"Epoch {k}" for k in range(len(data))]
        else:
            names = [names] * len(data)
            
    elif names is None:
        names = [f"Epoch {k}" for k in range(len(data))]
        
    else:
        raise ValueError(f"names: Expecting one str or a sequence of str with as {len(data)}")
    
    if barcolors is not None:
        barcolors = scipyen_colormaps.get_color4mpl(barcolors)
        
        if isinstance(barcolors, str):
            barcolors = [barcolors]

    if textcolor is not None:
        textcolor = scipyen_colormaps.get_color4mpl(textcolor)
        
    if not isinstance(textpos, str):
        textpos = "inside"
        
    elif textpos not in ("auto","top", "bottom", "above", "below", "inside"):
        textpos = "inside"
        
    if fig is None:
        fig = plt.figure()
        
    elif isinstance(fig, numbers.Integral):
        fig = plt.figure(fig)
        
    elif isinstance(fig, mpl.figure.Figure):
        fig = plt.figure(fig.number)

    plt.clf()
    
    
    for k in range(len(data)):
        epoch_axis=fig.add_subplot(len(data), 1, k+1)
        epoch_axis.grid(grid)
        epoch_df = data[k]
        nIntervals = epoch_df.shape[0]
        
        maxHeight = nIntervals * (height + y_interval)
        
        name = names[k]
            
        maxY = nIntervals * (height+y_interval)
        
        prevIntervalEnd = 0
        
        hasWarned = False
        
        for k, row in enumerate(epoch_df.index):
            text = epoch_df.loc[row, "Name"]
            bar_x = (epoch_df.loc[row, "Start"], epoch_df.loc[row, "Finish"])
            
            if k == 0:
                prevIntervalEnd = bar_x[1]
            
            if staggered:
                bar_y = (row*(height+y_interval), height)
            else:
                if bar_x[0] < prevIntervalEnd and not hasWarned:
                    warnings.warn("Intervals are overlapping; `staggered` should be set to True")
                    hasWarned = True
                bar_y = (1, height)
                
            if barcolors is not None:
                bh = epoch_axis.broken_barh([bar_x], bar_y, edgecolors= ("black",),
                                            label = text,
                                            facecolors=barcolors)
            else:
                bh = epoch_axis.broken_barh([bar_x], bar_y, edgecolors= ("black",),
                                            label=text)
                
            axes_facecolor = epoch_axis.get_facecolor()
            textonaxiscolor = scipyen_colormaps.auto_fg_color(axes_facecolor)
            
            if textcolor is None:
                bh_colors = bh.get_facecolors()
                if len(bh_colors):
                    textcolor = scipyen_colormaps.auto_fg_color(bh_colors[0])
                else:
                    textcolor = scipyen_colormaps.auto_fg_color(axes_facecolor)
            
            
            bh_paths = bh.get_paths()
            nPaths = len(bh_paths)
            
            for kp, p in enumerate(bh_paths):
                path_extents = p.get_extents()
                x0,y0,x1,y1 = (path_extents.x0, path_extents.y0, path_extents.x1, path_extents.y1)
                
                text_x = 0.5 * (x0 + x1)
                text_y = 0.5 * (y0 + y1)
                horizontalalignment="center"
                verticalalignment = "center"
                transform = epoch_axis.transAxes
                
                if textpos == "bottom": # plot at bottom of axis
                    text_y = 0
                    verticalalignment="bottom"
                    textcolor = textonaxiscolor
                    
                elif textpos == "above":
                    text_y = y1
                    verticalalignment="bottom"
                    textcolor = textonaxiscolor
                    
                elif textpos == "below":
                    text_y = y0
                    verticalalignment="top"
                    textcolor = textonaxiscolor
                    
                elif textpos == "top": # plot at top of axis
                    text_y = (maxHeight + textheight)*1.1
                    textcolor = textonaxiscolor
                    
                elif textpos == "auto":
                    if textwidth >= barwidth: # plot above the bar
                        text_y = y1
                        verticalalignment="top"
                        textcolor = textonaxiscolor
                        
                epoch_axis.text(text_x, text_y, text, color=textcolor,
                                horizontalalignment = horizontalalignment,
                                verticalalignment = verticalalignment)
                
            
        epoch_axis.set_ylabel(name)
        epoch_axis.set_ylim(0, maxY)
        
    if harmonize_ylims:
        maxY = max(ax.get_ylim()[1] for ax in fig.get_axes())
        for ax in fig.get_axes():
            ax.set_ylim(0, maxY)
            
    minX = min(ax.get_xlim()[0] for ax in fig.get_axes())
    maxX = max(ax.get_xlim()[1] for ax in fig.get_axes())
    
    for k, ax in enumerate(fig.get_axes()):
        ax.set_frame_on(False)
        ax.spines.left.set_visible(False)
        ax.spines.top.set_visible(False)
        ax.spines.right.set_visible(False)
        ax.yaxis.set_ticklabels([])
        
        if ax != fig.get_axes()[-1]:
            ax.xaxis.set_ticklabels([])
            ax.sharex(fig.get_axes()[-1])
        # ax.yaxis.set_ticks_position("none")
        if k < (len(fig.get_axes()) - 1):
            ax.spines.bottom.set_visible(False)
        else:
            ax.spines.bottom.set_visible(True)
            ax.set_xlabel("Time")
            ax.xaxis.set_ticks_position("bottom")
        # hide ticks
        ax.tick_params(color="none")
        ax.set_xlim(minX, maxX)
        if ax == fig.get_axes()[-1]:
            ax.spines.bottom.set_visible(True)
            ax.set_xlabel("Time")
            ax.xaxis.set_ticks_position("bottom")
            ax.xaxis.set_tick_params(color="black", labelcolor="black")
            
            
    fig.set_layout_engine("tight")
    return fig

def adjust_spines(ax, spines):
    # from matplotlib Spines examples
    for loc, spine in ax.spines.items():
        if loc in spines:
            spine.set_position(('outward', 10))  # outward by 10 points
        else:
            spine.set_color('none')  # don't draw spine

    # turn off ticks where there is no spine
    if 'left' in spines:
        ax.yaxis.set_ticks_position('left')
    else:
        # no yaxis ticks
        ax.yaxis.set_ticks([])

    if 'bottom' in spines:
        ax.xaxis.set_ticks_position('bottom')
    else:
        # no xaxis ticks
        ax.xaxis.set_ticks([])
