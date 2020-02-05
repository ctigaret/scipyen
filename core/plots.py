"""Plot utitilies
"""
#### BEGIN core python modules
import numbers
#### END core python modules

#### BEGIN 3rd party modules
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.mlab as mlb
from matplotlib.axes import Axes as Axes
# NOTE: 2019-07-29 18:27:45
mpl.rcParams['backend']='Qt5Agg'
mpl.rcParams["savefig.format"] = "svg"
mpl.rcParams["xtick.direction"] = "in"
mpl.rcParams["ytick.direction"] = "in"
# see NOTE: 2019-07-29 18:25:30 in pict.py
mpl.use("Qt5Agg") 

import numpy as np
import quantities as pq
import vigra
import pandas as pd
import seaborn as sb
#### END 3rd party modules

#### BEGIN pict.core modules
from . import datatypes as dt
#### END pict.core modules

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

#def remove_na(arr):
    #"""Helper method for removing NA values from array-like.
    #NOTE: for ehatever reason, remove_na is not imported
    #Parameters
    #----------
    #arr : array-like
        #The array-like from which to remove NA values.

    #Returns
    #-------
    #clean_arr : array-like
        #The original array with NA values removed.

    #"""
    #return arr[pd.notnull(arr)]

class SB_CategoricalStatPlotter(sb.categorical._CategoricalStatPlotter):
    """Seaborn's CategoricalPlotter vriant allowing custom statistics.
    For now, accepts ci as "se" in adddition to Seaborn's options
    """
    
    def estimate_statistic(self, estimator, ci, n_boot):
        """Also accepts ci given as "se"
        """
        from seaborn import utils
        from seaborn.utils import remove_na
        from seaborn.algorithms import bootstrap
        
        if self.hue_names is None:
            statistic = []
            confint = []
        else:
            statistic = [[] for _ in self.plot_data]
            confint = [[] for _ in self.plot_data]

        for i, group_data in enumerate(self.plot_data):

            # Option 1: we have a single layer of grouping
            # --------------------------------------------

            if self.plot_hues is None:

                if self.plot_units is None:
                    stat_data = remove_na(group_data)
                    unit_data = None
                else:
                    unit_data = self.plot_units[i]
                    have = pd.notnull(np.c_[group_data, unit_data]).all(axis=1)
                    stat_data = group_data[have]
                    unit_data = unit_data[have]

                # Estimate a statistic from the vector of data
                if not stat_data.size:
                    statistic.append(np.nan)
                else:
                    statistic.append(estimator(stat_data))

                # Get a confidence interval for this estimate
                if ci is not None:

                    if stat_data.size < 2:
                        confint.append([np.nan, np.nan])
                        continue

                    if ci == "sd":

                        estimate = estimator(stat_data)
                        sd = np.std(stat_data)
                        confint.append((estimate - sd, estimate + sd))
                        
                    elif ci == "se":
                        
                        estimate = estimator(stat_data)
                        sd = np.std(stat_data)
                        se = sd / np.sqrt(stat_data.size - 1)
                        confint.append((estimate - se, estimate + se))

                    else:

                        boots = bootstrap(stat_data, func=estimator,
                                          n_boot=n_boot,
                                          units=unit_data)
                        confint.append(utils.ci(boots, ci))

            # Option 2: we are grouping by a hue layer
            # ----------------------------------------

            else:
                for j, hue_level in enumerate(self.hue_names):

                    if not self.plot_hues[i].size:
                        statistic[i].append(np.nan)
                        if ci is not None:
                            confint[i].append((np.nan, np.nan))
                        continue

                    hue_mask = self.plot_hues[i] == hue_level
                    if self.plot_units is None:
                        stat_data = remove_na(group_data[hue_mask])
                        unit_data = None
                    else:
                        group_units = self.plot_units[i]
                        have = pd.notnull(
                            np.c_[group_data, group_units]
                            ).all(axis=1)
                        stat_data = group_data[hue_mask & have]
                        unit_data = group_units[hue_mask & have]

                    # Estimate a statistic from the vector of data
                    if not stat_data.size:
                        statistic[i].append(np.nan)
                    else:
                        statistic[i].append(estimator(stat_data))

                    # Get a confidence interval for this estimate
                    if ci is not None:

                        if stat_data.size < 2:
                            confint[i].append([np.nan, np.nan])
                            continue

                        if ci == "sd":

                            estimate = estimator(stat_data)
                            sd = np.std(stat_data)
                            confint[i].append((estimate - sd, estimate + sd))
                            
                        elif ci == "se":
                            estimate = estimator(stat_data)
                            sd = np.std(stat_data)
                            se = sd/np.sqrt(stat_data.size -1)
                            confint[i].append((estimate - se, estimate + se))

                        else:

                            boots = bootstrap(stat_data, func=estimator,
                                              n_boot=n_boot,
                                              units=unit_data)
                            confint[i].append(utils.ci(boots, ci))

        # Save the resulting values for plotting
        self.statistic = np.array(statistic)
        self.confint = np.array(confint)
            
class SB_BarPlotter(SB_CategoricalStatPlotter):
    def __init__(self, x, y, hue, data, order, hue_order,
                 estimator, ci, n_boot, units,
                 orient, color, palette, saturation, errcolor,
                 errwidth, capsize, dodge):
        """Initialize the plotter."""
        self.establish_variables(x, y, hue, data, orient,
                                 order, hue_order, units)
        self.establish_colors(color, palette, saturation)
        self.estimate_statistic(estimator, ci, n_boot)

        self.dodge = dodge

        self.errcolor = errcolor
        self.errwidth = errwidth
        self.capsize = capsize

    def draw_bars(self, ax, kws):
        """Draw the bars onto `ax`."""
        # Get the right matplotlib function depending on the orientation
        barfunc = ax.bar if self.orient == "v" else ax.barh
        barpos = np.arange(len(self.statistic))

        if self.plot_hues is None:

            # Draw the bars
            barfunc(barpos, self.statistic, self.width,
                    color=self.colors, align="center", **kws)

            # Draw the confidence intervals
            errcolors = [self.errcolor] * len(barpos)
            self.draw_confints(ax,
                               barpos,
                               self.confint,
                               errcolors,
                               self.errwidth,
                               self.capsize)

        else:

            for j, hue_level in enumerate(self.hue_names):

                # Draw the bars
                offpos = barpos + self.hue_offsets[j]
                barfunc(offpos, self.statistic[:, j], self.nested_width,
                        color=self.colors[j], align="center",
                        label=hue_level, **kws)

                # Draw the confidence intervals
                if self.confint.size:
                    confint = self.confint[:, j]
                    errcolors = [self.errcolor] * len(offpos)
                    self.draw_confints(ax,
                                       offpos,
                                       confint,
                                       errcolors,
                                       self.errwidth,
                                       self.capsize)

    def plot(self, ax, bar_kws):
        """Make the plot."""
        self.draw_bars(ax, bar_kws)
        self.annotate_axes(ax)
        if self.orient == "h":
            ax.invert_yaxis()
   

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
    
    if ylabel is not None:
        ax.axis["yzero"].set_label(ylabel)
        
    if isinstance(legend, (tuple, list)) and len(legend) > 0 and len(legend) == len(lines):
        lines[0].set_label(legend[0])
        plt.legend(loc="best")
        
    elif isinstance(legend, str):
        lines[0].set_label(legend)
        plt.legend(loc= "best")

    fig.canvas.draw_idle()
    
    return lines, ax #, ax1


def plotVigraKernel1D(val, fig=None, label=None, xlabel=None, ylabel=None, newPlot = False, plotStyle="stem", **kwargs):
    if not isinstance(val, vigra.filters.Kernel1D):
        raise TypeError("A vigra Kernel1D was expected; got %s instead" % type(val).__name__)
    
    [x,y] = dt.vigraKernel1D_to_ndarray(val)
    
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
        #if isinstance(label, str):
            #cmd = "ax." + plotStyle + "(x, y, legend=label, **kwargs)"
        
        #else:
            
        ret = eval(cmd)
        
        #if isinstance(label, str):
            #plt.legend([label])
        
        
    else:
        ret = ax.stem(x,y, **kwargs)
        
    if isinstance(label, str):
        ret.set_label(label)
        plt.legend(loc="best")
        
            
    fig.canvas.draw_idle()
    
    return ret
        
    
def barplot_sb(x=None, y=None, hue=None, data=None, order=None, hue_order=None,
            estimator=np.mean, ci=95, n_boot=1000, units=None,
            orient=None, color=None, palette=None, saturation=.75,
            errcolor=".26", errwidth=None, capsize=None, dodge=True,
            ax=None, overlay_stripplot=True, **kwargs):
    """
    Arguments:
    ----------
    ci: in addition to the accepted values for seaborn.barplot, it can also be 
        the string "se"; in this case the function plots mean +/- standard error 
        of the mean
        
    Additional arguments for overlaid stripplot (defaults in parantheses):
    -----------
    strip_jitter (True or float value)
    strip_dodge (value of the dodge argument, for a nice overlay on the bar plot)
    strip_size (5)
    strip_linewidth (0)
    strip_color (the value of the color argument)
    strip_palette (the value of the palette argument)
    """
    
    plotter = SB_BarPlotter(x, y, hue, data, order, hue_order,
                          estimator, ci, n_boot, units,
                          orient, color, palette, saturation,
                          errcolor, errwidth, capsize, dodge)

    if ax is None:
        ax = plt.gca()
        
    if overlay_stripplot:
        strip_jitter = kwargs.pop("strip_jitter", True)
        strip_size = kwargs.pop("strip_size", 5)
        strip_dodge = kwargs.pop("strip_dodge", dodge)
        strip_edgecolor = kwargs.pop("strip_edgecolor", "gray")
        strip_color = kwargs.pop("strip_color", color)
        strip_palette = kwargs.pop("strip_palette", palette)
        strip_linewidth = kwargs.pop("strip_linewidth", 0)
        

    plotter.plot(ax, kwargs)
    
    if overlay_stripplot:
        sb.stripplot(x=x, y=y, hue=hue, data=data, order=order, hue_order = hue_order,
                     jitter=strip_jitter, dodge=strip_dodge, orient=orient,
                     edgecolor=strip_edgecolor, color=strip_color,palette=strip_palette,
                     size=strip_size, linewidth=strip_linewidth,
                     ax=ax, **kwargs)
    
    return ax

    
