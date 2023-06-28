#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May 10 14:05:54 2020

@author: cezar
"""

import json, csv
import plotnine as p9
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

from itertools import cycle

mpl_prop_cycle = plt.rcParams['axes.prop_cycle']
defaultLineColorsList = ["#000000"] + ["b", "r", "g", "c", "m", "y"]  + mpl_prop_cycle.by_key()['color']
defaultOverlaidLineColorList = [mpl.colors.to_rgba(c, alpha=0.5) for c in defaultLineColorsList]
color_cycle = cycle(defaultLineColorsList)

from neuron import h, rxd
from neuron.units import ms, mV

from pynrncell import *

#h.load_file("stdrun.hoc")
h.nrnmpi_init() # must happen before any use of the ParallelContext class
pc = h.ParallelContext()

class Ring:
    """A network of *N* ball-and-stick cells where cell n makes an
    excitatory synapse onto cell n + 1 and the last, Nth cell in the
    network projects to the first cell.
    """
    def __init__(self, N=5, stim_w=0.04, stim_t=9, stim_delay=1, syn_w=0.01, syn_delay=5, r=50, nseg=51):
        """
        :param N: Number of cells.
        :param stim_w: Weight of the stimulus
        :param stim_t: time of the stimulus (in ms)
        :param stim_delay: delay of the stimulus (in ms)
        :param syn_w: Synaptic weight
        :param syn_delay: Delay of the synapse
        :param r: radius of the network
        :param nseg: number of segments per each section (soma/dendrite) of the cell; default: 51
        """ 
        self._syn_w = syn_w
        self._syn_delay = syn_delay
        self._create_cells(N, r, nseg=nseg)
        self._connect_cells()
        # add stimulus
        self._netstim = h.NetStim()
        self._netstim.number = 1
        self._netstim.start = stim_t
        self._nc = h.NetCon(self._netstim, self.cells[0].syn)
        self._nc.delay = stim_delay
        self._nc.weight[0] = stim_w
    
    def _create_cells(self, N, r, nseg=51):
        """n = number of cells; r = circle radius
        """
        self.cells = []
        for i in range(N):
            theta = i * 2 * h.PI / N
            self.cells.append(BallAndStick(i, h.cos(theta) * r, h.sin(theta) * r, 0, theta, nseg=nseg))
    
    def _connect_cells(self):
        for source, target in zip(self.cells, self.cells[1:] + [self.cells[0]]):
            nc = h.NetCon(source.soma(0.5)._ref_v, target.syn, sec=source.soma)
            nc.weight[0] = self._syn_w
            nc.delay = self._syn_delay
            source._ncs.append(nc)        
        
    def set_nseg(self, value=51):
        """(Re)set the number of segments for the sections in each cell
        :param value: new number of segments (default is 51)
        """
        for cell in self.cells:
            for sec in cell.all:
                sec.nseg=value
            
#def neuron_plot_shape():
    #from neuron import gui
    #ps = h.PlotShape(True)
    #ps.show(0)
    
    
class Ring1:
    """A network of *N* ball-and-stick cells where cell n makes an
    excitatory synapse onto cell n + 1 and the last, Nth cell in the
    network projects to the first cell.
    """
    def __init__(self, N=5, stim_w=0.04, stim_t=9, stim_delay=1, syn_w=0.01, syn_delay=5, r=50, nseg=51):
        """
        :param N: Number of cells.
        :param stim_w: Weight of the stimulus
        :param stim_t: time of the stimulus (in ms)
        :param stim_delay: delay of the stimulus (in ms)
        :param syn_w: Synaptic weight
        :param syn_delay: Delay of the synapse
        :param r: radius of the network
        :param nseg: number of segments per each section (soma/dendrite) of the cell; default: 51
        """ 
        self._N = N
        self.set_gids() # assign gids to processors
        self._syn_w = syn_w
        self._syn_delay = syn_delay
        #self._create_cells(N, r, nseg=nseg)
        self._create_cells(r, nseg=nseg) # use self._N
        self._connect_cells()
        
        # add stimulus
        # the 0th cell only exists on one process... that's the only one that gets a netstim
        if pc.gid_exists(0):
            self._netstim = h.NetStim()
            self._netstim.number = 1
            self._netstim.start = stim_t
            #self._nc = h.NetCon(self._netstim, self.cells[0].syn)
            self._nc = h.NetCon(self._netstim, pc.gid2cell(0).syn)  # grab cell with gid==0 wherever it exists
            self._nc.delay = stim_delay
            self._nc.weight[0] = stim_w
        
    def set_gids(self):
        """Set the gidlist on this host.
        Each process specifies which cells it will simulate.
        """
        #### Round-robin counting.
        #### Each host has an id from 0 to pc.nhost() - 1:
        #### the pc.id()th process starts at pc.id() and skips by however many
        #### processes are running (pc.nhost).
        self.gidlist = list(range(pc.id(), self._N, pc.nhost()))
        for gid in self.gidlist:
            pc.set_gid2node(gid, pc.id())
    
     
    def _create_cells(self, r, nseg=51):
        """n = number of cells; r = circle radius
        """
        #### associate the cell gid with the NetCon _spike_detector. 
        #### This allows the _connect_cells to make connections based on gids 
        #### instead of objects, using pc.gid_connect.
        self.cells = []
        #for i in range(N):
        for i in self.gidlist:  # only create the cells that exist on this host
            theta = i * 2 * h.PI / self._N
            self.cells.append(BallAndStick(i, h.cos(theta) * r, h.sin(theta) * r, 0, theta, nseg=nseg))
            
        # associate the cell with this host and gid    
        for cell in self.cells:
            pc.cell(cell._gid, cell._spike_detector)
    
    def _connect_cells(self):
        # we now must use gids instead of objects
        for target in self.cells:
            source_gid = (target._gid - 1 + self._N) % self._N
            nc = pc.gid_connect(source_gid, target.syn)
            nc.weight[0] = self._syn_w
            nc.delay = self._syn_delay
            target._ncs.append(nc)
            
        #for source, target in zip(self.cells, self.cells[1:] + [self.cells[0]]):
            #nc = h.NetCon(source.soma(0.5)._ref_v, target.syn, sec=source.soma)
            #nc.weight[0] = self._syn_w
            #nc.delay = self._syn_delay
            #source._ncs.append(nc)        
        
    def set_nseg(self, value=51):
        """(Re)set the number of segments for the sections in each cell
        :param value: new number of segments (default is 51)
        """
        for cell in self.cells:
            for sec in cell.all:
                sec.nseg=value
            
def neuron_plot_shape():
    from neuron import gui
    ps = h.PlotShape(True)
    ps.show(0)
    

