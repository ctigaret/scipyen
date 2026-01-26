# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import sys, os, traceback, inspect, numbers, re
import typing, types
import xml.parsers.expat
import xml.etree
import xml.etree.ElementTree as ET # the default parsers in here are from xml.parsers.expat,
                                   # see documentation for xml.etree.ElementTree.XMLParser
import xml.dom
import xml.dom.minidom

import drawsvg as dws

from core import strutils, xmlutils
from core.prog import scipywarn, safewrapper

def overlaySVGs(*svgs):
    r"""Overlays multiple SVG documents
Var-positional parameters:
==========================

:svgs: At least **one** ``xml.dom.minidom.Document`` object containing an element with tag `svg`.

    .. note::
        Only the first `svg` element is used. (I suppose this is unique per document)

    .. warning::
        The `svg` tags must have the same `viewBox` attribute (i.e. x,y coordinates and width, height) in **all** SVG documents passed here.
"""
    scipywarn("Don't use yet!")
    return
    # NOTE:2026-01-26 14:55:39
    # very "direct" code, no checks on types etc
    assert all(xmlutils.is_svg(v)for v in svgs), "Expecting a sequence of SVG objects"

    assert len(svgs) > 1, "I need more than one SVG"

    try:
        baseSVG = svgs[0]
        x, y, w, h = list(map(lambda v: int(v), baseSVG.getElementsByTagName("svg")[0].getAttribute("viewBox").split()))

        for svg in svgs[1:]:
            x_,y_,w_,h_ = list(map(lambda v: int(v), svg.getElementsByTagName("svg"[0]).getAttribute("viewBox").split()))
            assert x_ == x and y_ == y and w_ == w and h_ ==h, "All SVGs must have the same viewbox"

    except:
        traceback.print_exc()

def drawOntoSvg(svg, *elements) -> xml.dom.minidom.Document:
    assert(xmlutils.is_svg(svg)), "Expecting an SVG document"
    if len(elements) == 0:
        return svg

    assert all(isinstance(e, dws.types.DrawingElement) for e in elements) ,"Expecting drawsvg.types.DrawingElement objects"
    xml_header = '<?xml version="1.0" encoding="UTF-8"?>'

    svgElement = svg.getElementsByTagName("svg")[0]
    x, y, w, h = list(map(lambda v: int(v), svgElement.getAttribute("viewBox").split()))

    svgStr = svg.toprettyxml()

    svg_start = re.compile(r"<svg (.+?)>", re.DOTALL | re.MULTILINE)
    svg_pattern = re.compile(r"<svg (.+?)>(.+?)</svg>", re.DOTALL | re.MULTILINE)

    m = re.findall(svg_start, svgStr)
    svg_header = m[0] # also contains the viewBox definition

    n = re.findall(svg_pattern, svgStr)
    originalSVGstring = n[0][1] # should contain the actual shapes w/o <svg></svg> tags

    d = dws.Drawing(w,h, id_prefix="edited")
    for e in elements:
        d.append(e)

    drawnSVGstring = d.as_svg()


    mm = re.findall(svg_pattern, drawnSVGstring)
    drawnSVGstring = mm[0][1]

    result = list()
    result.append(xml_header)
    result.append(f"<svg {svg_header}>")
    result.append(originalSVGstring)
    result.append(drawnSVGstring)
    result.append("</svg>")

    result = "\n".join(result)

    # print(f"drawOntoSvg -> result = \n{result}")

    return xml.dom.minidom.parseString(result)



