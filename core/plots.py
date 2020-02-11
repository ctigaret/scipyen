# -*- coding: utf-8 -*-
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
mpl.rcParams["svg.fonttype"]="none"
# see NOTE: 2019-07-29 18:25:30 in pict.py
mpl.use("Qt5Agg") 
plt.rcParams['backend']='Qt5Agg'
plt.rcParams["savefig.format"] = "svg"
plt.rcParams["xtick.direction"] = "in"
plt.rcParams["ytick.direction"] = "in"
plt.rcParams["svg.fonttype"]="none"

import numpy as np
from scipy import stats
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
    
class SB_CategoricalPlotter(sb.categorical._CategoricalPlotter):
    def annotate_axes(self, ax, show_legend=True):
        """Add descriptive labels to an Axes object."""
        #print("SB_CategoricalPlotter.annotate_axes show_legend", show_legend)
        if self.orient == "v":
            xlabel, ylabel = self.group_label, self.value_label
        else:
            xlabel, ylabel = self.value_label, self.group_label

        if xlabel is not None:
            ax.set_xlabel(xlabel)
        if ylabel is not None:
            ax.set_ylabel(ylabel)

        if self.orient == "v":
            ax.set_xticks(np.arange(len(self.plot_data)))
            ax.set_xticklabels(self.group_names)
        else:
            ax.set_yticks(np.arange(len(self.plot_data)))
            ax.set_yticklabels(self.group_names)

        if self.orient == "v":
            ax.xaxis.grid(False)
            ax.set_xlim(-.5, len(self.plot_data) - .5, auto=None)
        else:
            ax.yaxis.grid(False)
            ax.set_ylim(-.5, len(self.plot_data) - .5, auto=None)

        if show_legend:
            if self.hue_names is not None:
                leg = ax.legend(loc="best")
                if self.hue_title is not None:
                    leg.set_title(self.hue_title)

                    # Set the title size a roundabout way to maintain
                    # compatibility with matplotlib 1.1
                    # TODO no longer needed
                    try:
                        #title_size = mpl.rcParams["axes.labelsize"] * .85
                        title_size = mpl.rcParams["axes.labelsize"]
                    except TypeError:  # labelsize is something like "large"
                        title_size = mpl.rcParams["axes.labelsize"]
                    prop = mpl.font_manager.FontProperties(size=title_size)
                    leg._legend_title_box._text.set_font_properties(prop)
    
    def add_legend_data(self, ax, color, label):
        """Add a dummy patch object so we can get legend data."""
        rect = plt.Rectangle([0, 0], 0, 0,
                             linewidth=self.linewidth / 2,
                             edgecolor=self.gray,
                             facecolor=color,
                             label=label)
        ax.add_patch(rect)

class SB_CategoricalStatPlotter(SB_CategoricalPlotter):
    """Seaborn's CategoricalPlotter vriant allowing custom statistics.
    For now, accepts ci as "se" in adddition to Seaborn's options
    """
    
    @property
    def nested_width(self):
        """A float with the width of plot elements when hue nesting is used."""
        if self.dodge:
            width = self.width / len(self.hue_names)
        else:
            width = self.width
        return width

    def draw_confints(self, ax, at_group, confint, colors,
                      errwidth=None, capsize=None, **kws):

        if errwidth is not None:
            kws.setdefault("lw", errwidth)
        else:
            kws.setdefault("lw", mpl.rcParams["lines.linewidth"] * 1.8)

        for at, (ci_low, ci_high), color in zip(at_group,
                                                confint,
                                                colors):
            if self.orient == "v":
                ax.plot([at, at], [ci_low, ci_high], color=color, **kws)
                if capsize is not None:
                    ax.plot([at - capsize / 2, at + capsize / 2],
                            [ci_low, ci_low], color=color, **kws)
                    ax.plot([at - capsize / 2, at + capsize / 2],
                            [ci_high, ci_high], color=color, **kws)
            else:
                ax.plot([ci_low, ci_high], [at, at], color=color, **kws)
                if capsize is not None:
                    ax.plot([ci_low, ci_low],
                            [at - capsize / 2, at + capsize / 2],
                            color=color, **kws)
                    ax.plot([ci_high, ci_high],
                            [at - capsize / 2, at + capsize / 2],
                            color=color, **kws)

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
        show_legend = bar_kws.pop("show_legend", True)
        #print("SB_BarPlotter.plot show_legend", show_legend)
        self.draw_bars(ax, bar_kws)
        self.annotate_axes(ax, show_legend=show_legend)
        if self.orient == "h":
            ax.invert_yaxis()

class SB_PointPlotter(SB_CategoricalStatPlotter):
    default_palette = "dark"

    """Show point estimates and confidence intervals with (joined) points."""
    def __init__(self, x, y, hue, data, order, hue_order,
                 estimator, ci, n_boot, units,
                 markers, linestyles, dodge, join, scale,
                 orient, color, palette, errwidth=None, capsize=None):
        from seaborn.external.six import string_types
        """Initialize the plotter."""
        self.establish_variables(x, y, hue, data, orient,
                                 order, hue_order, units)
        self.establish_colors(color, palette, 1)
        self.estimate_statistic(estimator, ci, n_boot)

        # Override the default palette for single-color plots
        if hue is None and color is None and palette is None:
            self.colors = [color_palette()[0]] * len(self.colors)

        # Don't join single-layer plots with different colors
        if hue is None and palette is not None:
            join = False

        # Use a good default for `dodge=True`
        if dodge is True and self.hue_names is not None:
            dodge = .025 * len(self.hue_names)

        # Make sure we have a marker for each hue level
        if isinstance(markers, string_types):
            markers = [markers] * len(self.colors)
        self.markers = markers

        # Make sure we have a line style for each hue level
        if isinstance(linestyles, string_types):
            linestyles = [linestyles] * len(self.colors)
        self.linestyles = linestyles

        # Set the other plot components
        self.dodge = dodge
        self.join = join
        self.scale = scale
        self.errwidth = errwidth
        self.capsize = capsize

    @property
    def hue_offsets(self):
        """Offsets relative to the center position for each hue level."""
        if self.dodge:
            offset = np.linspace(0, self.dodge, len(self.hue_names))
            offset -= offset.mean()
        else:
            offset = np.zeros(len(self.hue_names))
        return offset

    def draw_points(self, ax):
        """Draw the main data components of the plot."""
        from seaborn.utils import remove_na
        # Get the center positions on the categorical axis
        pointpos = np.arange(len(self.statistic))

        # Get the size of the plot elements
        lw = mpl.rcParams["lines.linewidth"] * 1.8 * self.scale
        mew = lw * .75
        markersize = np.pi * np.square(lw) * 2

        if self.plot_hues is None:

            # Draw lines joining each estimate point
            if self.join:
                color = self.colors[0]
                ls = self.linestyles[0]
                if self.orient == "h":
                    ax.plot(self.statistic, pointpos,
                            color=color, ls=ls, lw=lw)
                else:
                    ax.plot(pointpos, self.statistic,
                            color=color, ls=ls, lw=lw)

            # Draw the confidence intervals
            self.draw_confints(ax, pointpos, self.confint, self.colors,
                               self.errwidth, self.capsize)

            # Draw the estimate points
            marker = self.markers[0]
            hex_colors = [mpl.colors.rgb2hex(c) for c in self.colors]
            if self.orient == "h":
                x, y = self.statistic, pointpos
            else:
                x, y = pointpos, self.statistic
            ax.scatter(x, y,
                       linewidth=mew, marker=marker, s=markersize,
                       c=hex_colors, edgecolor=hex_colors)

        else:

            offsets = self.hue_offsets
            for j, hue_level in enumerate(self.hue_names):

                # Determine the values to plot for this level
                statistic = self.statistic[:, j]

                # Determine the position on the categorical and z axes
                offpos = pointpos + offsets[j]
                z = j + 1

                # Draw lines joining each estimate point
                if self.join:
                    color = self.colors[j]
                    ls = self.linestyles[j]
                    if self.orient == "h":
                        ax.plot(statistic, offpos, color=color,
                                zorder=z, ls=ls, lw=lw)
                    else:
                        ax.plot(offpos, statistic, color=color,
                                zorder=z, ls=ls, lw=lw)

                # Draw the confidence intervals
                if self.confint.size:
                    confint = self.confint[:, j]
                    errcolors = [self.colors[j]] * len(offpos)
                    self.draw_confints(ax, offpos, confint, errcolors,
                                       self.errwidth, self.capsize,
                                       zorder=z)

                # Draw the estimate points
                n_points = len(remove_na(offpos))
                marker = self.markers[j]
                hex_color = mpl.colors.rgb2hex(self.colors[j])
                if n_points:
                    point_colors = [hex_color for _ in range(n_points)]
                else:
                    point_colors = hex_color
                if self.orient == "h":
                    x, y = statistic, offpos
                else:
                    x, y = offpos, statistic
                if not len(remove_na(statistic)):
                    x, y = [], []
                ax.scatter(x, y, label=hue_level,
                           c=point_colors, edgecolor=point_colors,
                           linewidth=mew, marker=marker, s=markersize,
                           zorder=z)

    def plot(self, ax):
        """Make the plot."""
        self.draw_points(ax)
        self.annotate_axes(ax)
        if self.orient == "h":
            ax.invert_yaxis()

class SB_StripPlotter(sb.categorical._CategoricalScatterPlotter):
    """1-d scatterplot with categorical organization."""
    def __init__(self, x, y, hue, data, order, hue_order,
                 jitter, dodge, orient, color, palette):
        """Initialize the plotter."""
        self.establish_variables(x, y, hue, data, orient, order, hue_order)
        self.establish_colors(color, palette, 1)

        # Set object attributes
        self.dodge = dodge
        self.width = .8

        if jitter == 1:  # Use a good default for `jitter = True`
            jlim = 0.1
        else:
            jlim = float(jitter)
            
        if self.hue_names is not None and dodge:
            jlim /= len(self.hue_names)
            
        self.jitterer = stats.uniform(-jlim, jlim * 2).rvs
        
    @property
    def hue_offsets(self):
        """A list of center positions for plots when hue nesting is used."""
        n_levels = len(self.hue_names)
        if isinstance(self.dodge, bool) and self.dodge:
            each_width = self.width / n_levels
            offsets = np.linspace(0, self.width - each_width, n_levels)
            offsets -= offsets.mean()
            
        elif isinstance(self.dodge, float):
            each_width = (self.width / n_levels) * self.dodge
            offsets = np.linspace(0, self.width - each_width, n_levels)
            offsets -= offsets.mean()
            
        else:
            offsets = np.zeros(n_levels)

        return offsets


    def draw_stripplot(self, ax, kws):
        """Draw the points onto `ax`."""
        # Set the default zorder to 2.1, so that the points
        # will be drawn on top of line elements (like in a boxplot)
        for i, group_data in enumerate(self.plot_data):
            if self.plot_hues is None or not self.dodge:

                if self.hue_names is None:
                    hue_mask = np.ones(group_data.size, np.bool)
                else:
                    hue_mask = np.array([h in self.hue_names
                                         for h in self.plot_hues[i]], np.bool)
                    # Broken on older numpys
                    # hue_mask = np.in1d(self.plot_hues[i], self.hue_names)

                strip_data = group_data[hue_mask]

                # Plot the points in centered positions
                cat_pos = np.ones(strip_data.size) * i
                cat_pos += self.jitterer(len(strip_data))
                kws.update(c=self.point_colors[i][hue_mask])
                if self.orient == "v":
                    ax.scatter(cat_pos, strip_data, **kws)
                else:
                    ax.scatter(strip_data, cat_pos, **kws)

            else:
                offsets = self.hue_offsets
                for j, hue_level in enumerate(self.hue_names):
                    hue_mask = self.plot_hues[i] == hue_level
                    strip_data = group_data[hue_mask]

                    # Plot the points in centered positions
                    center = i + offsets[j]
                    cat_pos = np.ones(strip_data.size) * center
                    cat_pos += self.jitterer(len(strip_data))
                    kws.update(c=self.point_colors[i][hue_mask])
                    if self.orient == "v":
                        ax.scatter(cat_pos, strip_data, **kws)
                    else:
                        ax.scatter(strip_data, cat_pos, **kws)

    def plot(self, ax, kws, add_legend=True):
        """Make the plot."""
        self.draw_stripplot(ax, kws)
        if add_legend:
            self.add_legend_data(ax)
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
            errcolor="0", errwidth=None, capsize=None, dodge=True,
            ax=None, overlay_stripplot=True, axes_offset=0, despine=True,
            tick_direction="in", **kwargs):
    """
    Keyword arguments :
    ------------------
    ci: in addition to the accepted values for seaborn.barplot, it can also be 
        the string "se"; in this case the function plots mean +/- standard error 
        of the mean
        
    Additional keyword arguments for barplot:
    --------------
    show_legend (True)
        
    Additional keyword arguments controlling the appearance of the 
    overlaid stripplot. These are embedded in kwargs (default values in parantheses):
    -----------
    strip_jitter (True or float value)
    strip_dodge (value of the dodge argument, for a nice overlay on the bar plot)
    strip_size (5)
    strip_linewidth (0)
    strip_color (the value of the color argument)
    strip_palette (the value of the palette argument)
    strip_alpha
    strip_legend (False) When True, strip data will be added to the legend
    
    Additional keywords controlling the appearance of the bars, passed in kwargs - 
    these are effectively arguments passed directly to pyplot.bar()
    (default values in parantheses):
    --------------
    linewidth (0) - width of the bar edge (0 means no edge)
    edgecolor
    tick_label
    
    The following pyplot.bar arguments are NOT used/useful:
    ------------------------------------------------------
    ecolor, xerr, yerr, capsize, error_kw
    
    The following pyplot.bar arguments must NOT be specified in kwargs:
    ------------------------------------------------------------------
    color, orientation
    
    Returns:
    -------
    ax: plot axes -- see ax.bar? doe arguments controlling the appearance of the bars
    
    plotter: SB_BarPlotter instance:
        plotter.statistic: numpy array with the calculated statistics (e.g., mean)
        plotter.confint: numpy array with either the confidence intervals (float ci)
            or statistics +/- ci (ci is one of "sd" or "se")
    
    """
    
    plotter = SB_BarPlotter(x, y, hue, data, order, hue_order,
                          estimator, ci, n_boot, units,
                          orient, color, palette, saturation,
                          errcolor, errwidth, capsize, dodge)

    if ax is None:
        ax = plt.gca()
        
        
        
    strip_jitter = kwargs.pop("strip_jitter", True)
    strip_size = kwargs.pop("strip_size", 5)
    strip_dodge = kwargs.pop("strip_dodge", dodge)
    strip_edgecolor = kwargs.pop("strip_edgecolor", "gray")
    strip_color = kwargs.pop("strip_color", color)
    strip_palette = kwargs.pop("strip_palette", palette)
    strip_linewidth = kwargs.pop("strip_linewidth", 0)
    strip_alpha = kwargs.pop("strip_alpha", 1)
    strip_legend = kwargs.pop("strip_legend", False)
    strip_order = kwargs.pop("strip_order", None)  # to allow only for the bar legend

    # NOTE: 2020-02-05 23:59:27
    # plots the bars
    plotter.plot(ax, kwargs)
    
    # NOTE: 2020-02-05 23:59:54
    # remove edgecolor and linewidth from kwargs if present (used by plotter.plot) otherwise 
    # it gets specified twice in the call to stripplot
    kwargs.pop("edgecolor", None)
    kwargs.pop("linewidth", None)
    
    if overlay_stripplot:
        #sb.stripplot(x=x, y=y, hue=hue, data=data, order=order, hue_order = hue_order,
                     #jitter=strip_jitter, dodge=strip_dodge, orient=orient,
                     #edgecolor=strip_edgecolor, color=strip_color,palette=strip_palette,
                     #size=strip_size, linewidth=strip_linewidth, alpha=strip_alpha,
                     #ax=ax, **kwargs)
    
        kwargs["add_legend"] = strip_legend
        stripplot_sb(x=x, y=y, hue=hue, data=data, order=order, hue_order = hue_order,
                     jitter=strip_jitter, dodge=strip_dodge, orient=orient,
                     edgecolor=strip_edgecolor, color=strip_color,palette=strip_palette,
                     size=strip_size, linewidth=strip_linewidth, alpha=strip_alpha,
                     ax=ax, **kwargs)
    
    if despine:
        sb.despine(ax = ax, offset=axes_offset)
        
    ax.tick_params("y", direction="in")
        
    return ax, plotter

    
def catplot_sb(x=None, y=None, hue=None, data=None, row=None, col=None,
            col_wrap=None, estimator=np.mean, ci=95, n_boot=1000,
            units=None, order=None, hue_order=None, row_order=None,
            col_order=None, kind="strip", height=5, aspect=1,
            orient=None, color=None, palette=None, 
            errcolor="0", errwidth=None,  capsize=None, dodge=True, 
            overlay_stripplot=True, axes_offset=0,
            despine=True, tick_direction="in",
            legend=True, legend_out=True, sharex=True, sharey=True,
            margin_titles=False, facet_kws=None, dropna=False, **kwargs):
    """Seaborn catlpot adapted to accept se as ci and other arguments.
    
    Keyword arguments :
    ------------------
    ci: in addition to the accepted values for seaborn.barplot, it can also be 
        the string "se"; in this case the function plots mean +/- standard error 
        of the mean
        
    Additional keyword arguments controlling the appearance of the 
    overlaid stripplot. These are embedded in kwargs (default values in parantheses):
    -----------
    strip_jitter (True or float value)
    strip_dodge (value of the dodge argument, for a nice overlay on the bar plot)
    strip_size (5)
    strip_linewidth (0)
    strip_color (the value of the color argument)
    strip_palette (the value of the palette argument)
    strip_alpha
    
    Additional keywords controlling the appearance of the bars, embedded in kwargs - 
    these are effectively arguments passed directly to pyplot.bar()
    (default values in parantheses):
    --------------
    linewidth (None) - width of the bar edge (None or 0 means no edge)
    edgecolor (None) - any mpl style color
    tick_label
    
    Additional keywords controllinh the lines and markers for point plot, embedded in
    kwargs
    --------------
    markers ("o")
    linestyles ("-")
    scale (1)
    join  (True)
    
    """
    from seaborn import utils
    
    # Handle deprecations
    if "size" in kwargs:
        height = kwargs.pop("size")
        msg = ("The `size` paramter has been renamed to `height`; "
               "please update your code.")
        warnings.warn(msg, UserWarning)

    # Determine the plotting function
    try:
        plot_func = globals()[kind + "plot" + "_sb"]
        #print("plot_func: %s" % plot_func)
    except KeyError:
        supported_kinds="'bar', 'boxen', 'cat', 'count', 'point', 'strip', 'swarm'"
        err = "Plot kind '{0}' is not recognized. Supported kinds are: '{1}'".format(kind, supported_kinds)
        raise ValueError(err)

    # Alias the input variables to determine categorical order and palette
    # correctly in the case of a count plot
    if kind == "count":
        if x is None and y is not None:
            x_, y_, orient = y, y, "h"
        elif y is None and x is not None:
            x_, y_, orient = x, x, "v"
        else:
            raise ValueError("Either `x` or `y` must be None for count plots")
    else:
        x_, y_ = x, y

    # Determine the order for the whole dataset, which will be used in all
    # facets to ensure representation of all data in the final plot
    p = sb.categorical._CategoricalPlotter()
    p.establish_variables(x_, y_, hue, data, orient, order, hue_order)
    order = p.group_names
    hue_order = p.hue_names

    # Determine the palette to use
    # (FacetGrid will pass a value for ``color`` to the plotting function
    # so we need to define ``palette`` to get default behavior for the
    # categorical functions
    p.establish_colors(color, palette, 1)
    if kind != "point" or hue is not None:
        palette = p.colors

    # Determine keyword arguments for the facets
    facet_kws = {} if facet_kws is None else facet_kws
    facet_kws.update(
        data=data, row=row, col=col,
        row_order=row_order, col_order=col_order,
        col_wrap=col_wrap, height=height, aspect=aspect,
        sharex=sharex, sharey=sharey,
        legend_out=legend_out, margin_titles=margin_titles,
        dropna=dropna,
        )

    # Determine keyword arguments for the plotting function
    plot_kws = dict(
        order=order, hue_order=hue_order,  orient=orient, 
        color=color, palette=palette, dodge=dodge
        )
    plot_kws.update(kwargs)
    
    #print("plots.catplot_sb kind", kind)

    if kind in ["bar", "point"]:
        # NOTE: 2020-02-11 10:11:05
        # the strip_* arguments will be renamed within barplot_sb() and pointplot_sb()
        # then passed with their proper names to stripplot_sb()
        plot_kws.update(
            estimator=estimator, ci=ci, n_boot=n_boot, units=units,
            errcolor = errcolor, errwidth=errwidth, capsize=capsize, dodge=dodge,
            strip_jitter = kwargs.pop("strip_jitter", True),
            strip_size = kwargs.pop("strip_size",5),
            strip_dodge = kwargs.pop("strip_dodge", dodge),
            strip_edgecolor = kwargs.pop("strip_edgecolor", "gray"),
            strip_color = kwargs.pop("strip_color", color),
            strip_palette = kwargs.pop("strip_palette", palette),
            strip_linewidth = kwargs.pop("strip_linewidth", 0),
            strip_alpha = kwargs.pop("strip_alpha", 1),
            strip_order = kwargs.pop("strip_order", None),
            strip_legend = kwargs.pop("strip_legend", False)
            )
        
        if kind == "point":
            plot_kws.update(markers=kwargs.pop("markers", "o"), 
                            linestyles=kwargs.pop("linestyles", "-"),
                            join=kwargs.pop("join", True),
                            scale=kwargs.pop("scale", 1)
                            )
        
    elif kind in ["strip"]:
        # NOTE: 2020-02-11 10:13:03
        # unlike the case of barplot_sb and pointplot_sb,
        # the "strip_*" arguments are directly passed to stripplot_sb
        # therefore they must appropriately renamed here
        plot_kws.update(dodge = kwargs.pop("strip_dodge", dodge),
            jitter=kwargs.pop("strip_jitter", True),
            size=kwargs.pop("strip_size",5),
            edgecolor = kwargs.pop("strip_edgecolor", "gray"),
            color = kwargs.pop("strip_color", color),
            palette = kwargs.pop("strip_palette", palette),
            linewidth = kwargs.pop("strip_linewidth", 0),
            alpha = kwargs.pop("strip_alpha", 1),
            order = kwargs.pop("strip_order", None),
            add_legend = kwargs.pop("strip_legend", True)
            )


    # Initialize the facets
    g = sb.axisgrid.FacetGrid(**facet_kws)

    # Draw the plot onto the facets
    g.map_dataframe(plot_func, x, y, hue, **plot_kws)

    # Special case axis labels for a count type plot
    if kind == "count":
        if x is None:
            g.set_axis_labels(x_var="count")
        if y is None:
            g.set_axis_labels(y_var="count")

    if legend and (hue is not None) and (hue not in [x, row, col]):
        hue_order = list(map(utils.to_utf8, hue_order))
        g.add_legend(title=hue, label_order=hue_order)

    return g
   
def pointplot_sb(x=None, y=None, hue=None, data=None, order=None, hue_order=None,
              estimator=np.mean, ci=95, n_boot=1000, units=None,
              markers="o", linestyles="-", dodge=True, join=True, scale=1,
              orient=None, color=None, palette=None, saturation=.75,
              errcolor="0", errwidth=None, overlay_stripplot=True, despine=True,
              axes_offset=0, capsize=None, ax=None, **kwargs):
    """
    Keyword arguments :
    ------------------
    ci: in addition to the accepted values for seaborn.barplot, it can also be 
        the string "se"; in this case the function plots mean +/- standard error 
        of the mean
        
    Additional keyword arguments controlling the appearance of the 
    overlaid stripplot. These are embedded in kwargs (default values in parantheses):
    -----------
    strip_jitter (True or float value)
    strip_dodge (value of the dodge argument, for a nice overlay on the bar plot)
    strip_size (5)
    strip_linewidth (0)
    strip_color (the value of the color argument)
    strip_palette (the value of the palette argument)
    strip_alpha
    
    Additional keywords controlling the appearance of the bars, passed in kwargs - 
    these are effectively arguments passed directly to pyplot.bar()
    (default values in parantheses):
    --------------
    linewidth (0) - width of the bar edge (0 means no edge)
    edgecolor
    tick_label
    
    The following pyplot.bar arguments are NOT used/useful:
    ------------------------------------------------------
    ecolor, xerr, yerr, capsize, error_kw
    
    The following pyplot.bar arguments must NOT be specified in kwargs:
    ------------------------------------------------------------------
    color, orientation
    
    Returns:
    -------
    ax: plot axes -- see ax.bar? doe arguments controlling the appearance of the bars
    
    plotter: SB_BarPlotter instance:
        plotter.statistic: numpy array with the calculated statistics (e.g., mean)
        plotter.confint: numpy array with either the confidence intervals (float ci)
            or statistics +/- ci (ci is one of "sd" or "se")
    
    """
    plotter = SB_PointPlotter(x, y, hue, data, order, hue_order,
                            estimator, ci, n_boot, units,
                            markers, linestyles, dodge, join, scale,
                            orient, color, palette, errwidth, capsize)

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
        strip_alpha = kwargs.pop("strip_alpha", 1)
        
    plotter.plot(ax)

    # NOTE: 2020-02-05 23:59:54
    # remove edgecolor and linewidth from kwargs if present (used by plotter.plot) otherwise 
    # it gets specified twice in the call to stripplot
    kwargs.pop("edgecolor", None)
    kwargs.pop("linewidth", None)
    
    if overlay_stripplot:
        sb.stripplot(x=x, y=y, hue=hue, data=data, order=order, hue_order = hue_order,
                     jitter=strip_jitter, dodge=strip_dodge, orient=orient,
                     edgecolor=strip_edgecolor, color=strip_color,palette=strip_palette,
                     size=strip_size, linewidth=strip_linewidth, alpha=strip_alpha,
                     ax=ax, **kwargs)
        #stripplot_sb(x=x, y=y, hue=hue, data=data, order=order, hue_order = hue_order,
                     #jitter=strip_jitter, dodge=strip_dodge, orient=orient,
                     #edgecolor=strip_edgecolor, color=strip_color,palette=strip_palette,
                     #size=strip_size, linewidth=strip_linewidth, alpha=strip_alpha,
                     #ax=ax, **kwargs)
    
    if despine:
        sb.despine(ax = ax, offset=axes_offset)
        
    ax.tick_params("y", direction="in")
        
    return ax, plotter

def countplot_sb(x=None, y=None, hue=None, data=None, order=None, hue_order=None,
              orient=None, color=None, palette=None, saturation=.75,
              dodge=True, ax=None, **kwargs):

    estimator = len
    ci = None
    n_boot = 0
    units = None
    errcolor = None
    errwidth = None
    capsize = None

    if x is None and y is not None:
        orient = "h"
        x = y
    elif y is None and x is not None:
        orient = "v"
        y = x
    elif x is not None and y is not None:
        raise TypeError("Cannot pass values for both `x` and `y`")
    else:
        raise TypeError("Must pass values for either `x` or `y`")

    plotter = sb.categorical._BarPlotter(x, y, hue, data, order, hue_order,
                          estimator, ci, n_boot, units,
                          orient, color, palette, saturation,
                          errcolor, errwidth, capsize, dodge)

    plotter.value_label = "count"

    if ax is None:
        ax = plt.gca()

    plotter.plot(ax, kwargs)
    return ax

def boxenplot_sb(x=None, y=None, hue=None, data=None, order=None, hue_order=None,
              orient=None, color=None, palette=None, saturation=.75,
              width=.8, dodge=True, k_depth='proportion', linewidth=None,
              scale='exponential', outlier_prop=None, ax=None, **kwargs):

    plotter = sb.categorical._LVPlotter(x, y, hue, data, order, hue_order,
                         orient, color, palette, saturation,
                         width, dodge, k_depth, linewidth, scale,
                         outlier_prop)

    if ax is None:
        ax = plt.gca()

    plotter.plot(ax, kwargs)
    return ax

def stripplot_sb(x=None, y=None, hue=None, data=None, order=None, hue_order=None,
              jitter=True, dodge=False, orient=None, color=None, palette=None,
              size=5, edgecolor="gray", linewidth=0, ax=None, 
              alpha=1, **kwargs):
    """Adapted from seaborn.stripplot
    
    Additional keyword arguments:
    ----------------------------
    add_legend (True)
    """
    
    add_legend=kwargs.pop("add_legend", True)

    if "split" in kwargs:
        dodge = kwargs.pop("split")
        msg = "The `split` parameter has been renamed to `dodge`."
        warnings.warn(msg, UserWarning)

    #strip_jitter = kwargs.pop("strip_jitter", True)
    #strip_size = kwargs.pop("strip_size", 5)
    #strip_dodge = kwargs.pop("strip_dodge", dodge)
    #strip_edgecolor = kwargs.pop("strip_edgecolor", "gray")
    #strip_color = kwargs.pop("strip_color", color)
    #strip_palette = kwargs.pop("strip_palette", palette)
    #strip_linewidth = kwargs.pop("strip_linewidth", 0)
    #strip_alpha = kwargs.pop("strip_alpha", 1)
    #strip_legend = kwargs.pop("strip_legend", False)
        
    plotter = SB_StripPlotter(x, y, hue, data, order, hue_order,
                            jitter, dodge, orient, color, palette)
    if ax is None:
        ax = plt.gca()

    kwargs.setdefault("zorder", 3)
    size = kwargs.get("s", size)
    if linewidth is None:
        linewidth = size / 10
    if edgecolor == "gray":
        edgecolor = plotter.gray
    kwargs.update(dict(s=size ** 2,
                       edgecolor=edgecolor,
                       linewidth=linewidth))

    plotter.plot(ax, kwargs, add_legend=add_legend)
    return ax, plotter

def swarmplot_sb(x=None, y=None, hue=None, data=None, order=None, hue_order=None,
              dodge=False, orient=None, color=None, palette=None,
              size=5, edgecolor="gray", linewidth=0, ax=None, **kwargs):

    if "split" in kwargs:
        dodge = kwargs.pop("split")
        msg = "The `split` parameter has been renamed to `dodge`."
        warnings.warn(msg, UserWarning)

    plotter = sb.categorical._SwarmPlotter(x, y, hue, data, order, hue_order,
                            dodge, orient, color, palette)
    if ax is None:
        ax = plt.gca()

    kwargs.setdefault("zorder", 3)
    size = kwargs.get("s", size)
    if linewidth is None:
        linewidth = size / 10
    if edgecolor == "gray":
        edgecolor = plotter.gray
    kwargs.update(dict(s=size ** 2,
                       edgecolor=edgecolor,
                       linewidth=linewidth))

    plotter.plot(ax, kwargs)
    return ax

#def boxplot_sb(x=None, y=None, hue=None, data=None, order=None, hue_order=None,
            #orient=None, color=None, palette=None, saturation=.75,
            #width=.8, dodge=True, fliersize=5, linewidth=None,
            #whis=1.5, notch=False, ax=None, **kwargs):

    #plotter = _BoxPlotter(x, y, hue, data, order, hue_order,
                          #orient, color, palette, saturation,
                          #width, dodge, fliersize, linewidth)

    #if ax is None:
        #ax = plt.gca()
    #kwargs.update(dict(whis=whis, notch=notch))

    #plotter.plot(ax, kwargs)
    #return ax

