# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import numpy as np
import pandas as pd # for DataFrame, Series etc
import seaborn as sb
from six import string_types
# from seaborn.external.six import string_types

class SB_CategoricalPlotter(sb.categorical._CategoricalPlotter):
    def categorical_order(self, values, order=None, skip=None):
        """Return a list of unique data values.

        Determine an ordered list of levels in ``values``.

        Parameters
        ----------
        values : list, array, Categorical, or Series
            Vector of "categorical" values
        
        order : list-like, optional
            Desired order of category levels to override the order determined
            from the ``values`` object.
            
        skip : str or sequence of str, or None (default)
            Name(s) of category(ies) to be skipped from plotting.
            
            NOTE: in Pandas DataFrame and Pandas Series, the category names are
            strings
            

        Returns
        -------
        order : list
            Ordered list of category levels not including null values.

        """
        if order is None:
            if hasattr(values, "categories"):
                if isinstance(skip, (tuple, list)):
                    order = [c for c in values.categories if c not in skip]
                    
                elif skip is None:
                    order = values.categories
                    
                else:
                    order = [c for c in values.categories if c != skip]
                    
            else:
                try:
                    if isinstance(skip, (tuple, list)):
                        order = [c for c in values.cat.categories if c not in skip]
                            
                    elif skip is None:
                        order = values.cat.categories
                        
                    else:
                        order = [c for c in values.cat.categories if c != skip]
                        
                except (TypeError, AttributeError):
                    try:
                        order = values.unique()
                    except AttributeError:
                        order = pd.unique(values)
                    try:
                        np.asarray(values).astype(np.float)
                        order = np.sort(order)
                    except (ValueError, TypeError):
                        order = order
            order = filter(pd.notnull, order)
            
        return list(order)

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

    def establish_variables(self, x=None, y=None, hue=None, data=None,
                            orient=None, order=None, hue_order=None,
                            skip = None, units=None):
        """Convert input specification into a common representation."""
        from seaborn._core import infer_orient
        # Option 1:
        # We are plotting a wide-form dataset
        # -----------------------------------
        if x is None and y is None:

            # Do a sanity check on the inputs
            if hue is not None:
                error = "Cannot use `hue` without `x` or `y`"
                raise ValueError(error)

            # No hue grouping with wide inputs
            plot_hues = None
            hue_title = None
            hue_names = None

            # No statistical units with wide inputs
            plot_units = None

            # We also won't get a axes labels here
            value_label = None
            group_label = None

            # Option 1a:
            # The input data is a Pandas DataFrame
            # ------------------------------------

            if isinstance(data, pd.DataFrame):

                # Order the data correctly
                if order is None:
                    order = []
                    # Reduce to just numeric columns
                    for col in data:
                        try:
                            data[col].astype(np.float)
                            order.append(col)
                        except ValueError:
                            pass
                plot_data = data[order]
                group_names = order
                group_label = data.columns.name

                # Convert to a list of arrays, the common representation
                iter_data = plot_data.iteritems()
                plot_data = [np.asarray(s, np.float) for k, s in iter_data]

            # Option 1b:
            # The input data is an array or list
            # ----------------------------------

            else:

                # We can't reorder the data
                if order is not None:
                    error = "Input data must be a pandas object to reorder"
                    raise ValueError(error)

                # The input data is an array
                if hasattr(data, "shape"):
                    if len(data.shape) == 1:
                        if np.isscalar(data[0]):
                            plot_data = [data]
                        else:
                            plot_data = list(data)
                    elif len(data.shape) == 2:
                        nr, nc = data.shape
                        if nr == 1 or nc == 1:
                            plot_data = [data.ravel()]
                        else:
                            plot_data = [data[:, i] for i in range(nc)]
                    else:
                        error = ("Input `data` can have no "
                                 "more than 2 dimensions")
                        raise ValueError(error)

                # Check if `data` is None to let us bail out here (for testing)
                elif data is None:
                    plot_data = [[]]

                # The input data is a flat list
                elif np.isscalar(data[0]):
                    plot_data = [data]

                # The input data is a nested list
                # This will catch some things that might fail later
                # but exhaustive checks are hard
                else:
                    plot_data = data

                # Convert to a list of arrays, the common representation
                plot_data = [np.asarray(d, np.float) for d in plot_data]

                # The group names will just be numeric indices
                group_names = list(range((len(plot_data))))

            # Figure out the plotting orientation
            orient = "h" if str(orient).startswith("h") else "v"

        # Option 2:
        # We are plotting a long-form dataset
        # -----------------------------------

        else:

            # See if we need to get variables from `data`
            if data is not None:
                x = data.get(x, x)
                y = data.get(y, y)
                hue = data.get(hue, hue)
                units = data.get(units, units)

            # Validate the inputs
            for var in [x, y, hue, units]:
                if isinstance(var, string_types):
                    err = "Could not interpret input '{}'".format(var)
                    raise ValueError(err)

            # Figure out the plotting orientation
            #orient = self.infer_orient(x, y, orient)
            orient = infer_orient(x, y, orient)

            # Option 2a:
            # We are plotting a single set of data
            # ------------------------------------
            if x is None or y is None:

                # Determine where the data are
                vals = y if x is None else x

                # Put them into the common representation
                plot_data = [np.asarray(vals)]

                # Get a label for the value axis
                if hasattr(vals, "name"):
                    value_label = vals.name
                else:
                    value_label = None

                # This plot will not have group labels or hue nesting
                groups = None
                group_label = None
                group_names = []
                plot_hues = None
                hue_names = None
                hue_title = None
                plot_units = None

            # Option 2b:
            # We are grouping the data values by another variable
            # ---------------------------------------------------
            else:

                # Determine which role each variable will play
                if orient == "v":
                    vals, groups = y, x
                else:
                    vals, groups = x, y

                # Get the categorical axis label
                group_label = None
                if hasattr(groups, "name"):
                    group_label = groups.name

                # Get the order on the categorical axis
                group_names = self.categorical_order(groups, order, skip)

                # Group the numeric data
                plot_data, value_label = self._group_longform(vals, groups,
                                                              group_names)

                # Now handle the hue levels for nested ordering
                if hue is None:
                    plot_hues = None
                    hue_title = None
                    hue_names = None
                else:

                    # Get the order of the hue levels
                    hue_names = self.categorical_order(hue, hue_order, skip)

                    # Group the hue data
                    plot_hues, hue_title = self._group_longform(hue, groups,
                                                                group_names)

                # Now handle the units for nested observations
                if units is None:
                    plot_units = None
                else:
                    plot_units, _ = self._group_longform(units, groups,
                                                         group_names)

        # Assign object attributes
        # ------------------------
        self.orient = orient
        self.plot_data = plot_data
        self.group_label = group_label
        self.value_label = value_label
        self.group_names = group_names
        self.plot_hues = plot_hues
        self.hue_title = hue_title
        self.hue_names = hue_names
        self.plot_units = plot_units

class SB_CategoricalStatPlotter(SB_CategoricalPlotter):
    """Seaborn's CategoricalPlotter variant allowing custom statistics.
    For now, accepts ci as "se" in adddition to Seaborn's options, which are:
    float, "sd" and None; float indicates the confidence interval, 95% by default
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
    def __init__(self, x, y, hue, data, order, hue_order, skip,
                 estimator, ci, n_boot, units,
                 orient, color, palette, saturation, errcolor,
                 errwidth, capsize, dodge, bar_width):
        """Initialize the plotter."""
        self.dodge              = dodge

        self.errcolor           = errcolor
        self.errwidth           = errwidth
        self.capsize            = capsize
        
        self.establish_variables(x, y, hue, data, orient,
                                 order, hue_order, skip, units)
        self.establish_colors(color, palette, saturation)
        self.estimate_statistic(estimator, ci, n_boot)
        
        if isinstance(bar_width, float):
            self.width = bar_width # the seaborn default is 0.8


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


# def stripplot_sb(x=None, y=None, hue=None, data=None, order=None, hue_order=None,
#               jitter=True, dodge=False, orient=None, color=None, palette=None,
#               size=5, edgecolor="gray", linewidth=0, ax=None, 
#               alpha=1, **kwargs):
#     """Adapted from seaborn.stripplot
#     
#     Additional keyword arguments:
#     ----------------------------
#     add_legend (True)
#     """
#     
#     add_legend=kwargs.pop("add_legend", True)
# 
#     if "split" in kwargs:
#         dodge = kwargs.pop("split")
#         msg = "The `split` parameter has been renamed to `dodge`."
#         warnings.warn(msg, UserWarning)
# 
#     #strip_jitter = kwargs.pop("strip_jitter", True)
#     #strip_size = kwargs.pop("strip_size", 5)
#     #strip_dodge = kwargs.pop("strip_dodge", dodge)
#     #strip_edgecolor = kwargs.pop("strip_edgecolor", "gray")
#     #strip_color = kwargs.pop("strip_color", color)
#     #strip_palette = kwargs.pop("strip_palette", palette)
#     #strip_linewidth = kwargs.pop("strip_linewidth", 0)
#     #strip_alpha = kwargs.pop("strip_alpha", 1)
#     #strip_legend = kwargs.pop("strip_legend", False)
#         
#     plotter = SB_StripPlotter(x, y, hue, data, order, hue_order,
#                             jitter, dodge, orient, color, palette)
#     if ax is None:
#         ax = plt.gca()
# 
#     kwargs.setdefault("zorder", 3)
#     size = kwargs.get("s", size)
#     if linewidth is None:
#         linewidth = size / 10
#     if edgecolor == "gray":
#         edgecolor = plotter.gray
#     kwargs.update(dict(s=size ** 2,
#                        edgecolor=edgecolor,
#                        linewidth=linewidth))
# 
#     plotter.plot(ax, kwargs, add_legend=add_legend)
#     return ax, plotter

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

def barplot_sb(*args, x=None, y=None, hue=None, data=None, order=None, 
               hue_order=None, skip=None, estimator=np.mean, ci=95, n_boot=1000,
               units=None, orient=None, color=None, palette=None, saturation=.75,
               errcolor="0", errwidth=None, capsize=None, dodge=True,
               ax=None, overlay_stripplot=True, axes_offset=0, despine=True,
               tick_direction="in", **kwargs):
    """
    Show point estimates and confidence intervals as rectangular bars.
    
    Modified verison of Seaborn barplot, that allows to:
    a) skip categories from the plot, when "order" is not specified
    b) include the possibility to use the SEM in addition to the confidence
        interval or SD, for errorbars.
        
    Keyword parameters:
    ================== 
    NOTE It is preferable that all parameters are passed as key=value pairs.
    
    x, y, hue: names of variables in "data", or vector data
        In particular, when "data" is a Pandas DataFrame, x, "y" and "hue" are
        column names such that:
        
        "x" is the name of the categorical, or categorical-like column, which 
            holds the independent variable ("predictor", or "experimental" variable)
            
            This variables can be seen as categorical even if it is NOT of Pandas
            Categorical type.
            
        "y" is the name of the column containing the dependent variable ("outcome"), 
            which is usually continuous, i.e. it can take any value from an interval
            
        "hue" is the name of the column containing an independent categorical 
            variable to be considered as a "factor" in the data (i.e. different 
            from the predictor)
            
        Categorical data in "x" and "hue" may be nominal, dichotomous, or ordinal.
        
        When "x" is ordinal, it is useful to specify the "order" parameter (see below)
        so that a relation between "x" and "y" becomes clear.
    
    data: DataFrame, array, list of arrays
    
    order, hue_order: lists of strings
        These are names of categories (a.k.a "levels" in R) found in data
        (when data is a DataFrame):
        
        order: category names in the DataFrame column holding the independent 
            variable "x"
        
        hue_order: category names in the DataFrame column holding the "hue"
        
        These parameters are useful when "x" and "hue" are ordinal variables.
    
    skip: a string or a sequence (tuple, list) of string. Optional (default is None).
        These are the names of categories (or "levels") in "x" NOT to be plotted.
        
        "x" is assumed to be categorical.
        
        Only used when "order" is not specified. Otherwise, "order" will select
        the categories to be plotted and "skip" is ignored.
        
    ci: in addition to the accepted values for seaborn.barplot, it can also be 
        the string "se"; in this case the function plots mean +/- standard error 
        of the mean
        
    For the other parameters, please see the documentation for seaborn.barplot():
    
    https://seaborn.pydata.org/generated/seaborn.barplot.html#seaborn.barplot
        
    Additional keyword parameters for barplot:
    --------------
    show_legend (True)
    bar_width (0.8) - NOTE: this is aliased to "width"; if both width and bar_width
            are supplied, bar_width takes precedence
        
    Additional keyword arguments controlling the appearance of the 
    overlaid stripplot. These are embedded in kwargs (default values in parantheses):
    NOTE: The stripplot contains the overlaid data points
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
    
    Additonal keyword parameters for Y axis:
    ----------------------------------------
    tick_length : float (default is 4.5)
    tick_direction : str (default is "in")
    
    Returns:
    -------
    ax: plot axes -- see ax.bar for arguments controlling the appearance of the bars
    
    plotter: SB_BarPlotter instance:
        plotter.statistic: numpy array with the calculated statistics (e.g., mean)
        plotter.confint: numpy array with either the confidence intervals (float ci)
            or statistics +/- ci (ci is one of "sd" or "se")
    
    """
    if not isinstance(data, (pd.DataFrame, dict)):
        return

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
    tick_length = kwargs.pop("tick_length", 4.5)
    tick_direction = kwargs.pop("tick_direction", "in")
    bar_width = kwargs.pop("bar_width", None)
    _width = kwargs.pop("width", None)
    
    if not isinstance(bar_width, float):
        if isinstance(_width, float):
            bar_width = _width
        else:
            bar_width = None
            
    else:
        bar_width = None
    
    plotter = SB_BarPlotter(x, y, hue, data, order, hue_order, skip,
                          estimator, ci, n_boot, units,
                          orient, color, palette, saturation,
                          errcolor, errwidth, capsize, dodge, bar_width)

    if ax is None:
        ax = plt.gca()
        
        
        

    # NOTE: 2020-02-05 23:59:27
    # plots the bars
    plotter.plot(ax, kwargs)
    
    # NOTE: 2020-02-05 23:59:54
    # remove edgecolor and linewidth from kwargs if present (used by plotter.plot) otherwise 
    # it gets specified twice in the call to stripplot
    kwargs.pop("edgecolor", None)
    kwargs.pop("linewidth", None)
    
    if overlay_stripplot: # NOTE: plot the data points
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
        
    ax.tick_params("y", direction=tick_direction, length=tick_length, color="black")
        
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
    ci: in addition to the accepted values for seaborn.barplot (95, "sd", or None),
        it can also be the string "se"; in this case the function plots mean 
        +/- standard error of the mean
        
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
