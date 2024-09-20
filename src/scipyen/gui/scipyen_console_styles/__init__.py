# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
    # SPDX-License-Identifier: GPL-3.0-or-later
    # SPDX-License-Identifier: LGPL-2.1-or-later
    
"""
"""

import inspect

from pygments import styles as pstyles
from pygments.token import Token

from .keplerdark import KeplerDark

StyleNames = ["KeplerDark"]

def available_pygments():
    # NOTE: 2020-12-22 21:35:30
    # jupyter_qtconsole_colorschemes has entry points in pygments.styles
    return list(pstyles.get_all_styles())

def get_available_syntax_styles():
    return sorted(list(pstyles.get_all_styles()))

def get_style_colors(stylename:str) -> dict:
    if stylename in StyleNames:
        # use my own
        # TODO: 2024-09-19 15:24:37 
        # give possibility of 
        # future additional custom schemes to be packaged with Scipyen
        frame_record = inspect.getouterframes(inspect.currentframe())[0]
        style = frame_record[0].f_globals.get(stylename, None)
        if style is None:
            raise RuntimeError(f"No class found for {stylename} style")
        fgcolor = style.style_for_token(Token.Text)['color'] or ''
        if len(fgcolor) in (3,6):
            # could be 'abcdef' or 'ace' hex, which needs '#' prefix
            try:
                int(fgcolor, 16)
            except TypeError:
                pass
            else:
                fgcolor = "#"+fgcolor

        return dict(
            bgcolor = style.background_color,
            select  = style.highlight_color,
            fgcolor = fgcolor
        )
    
    else:
        return pstyles.get_colors(stylename)
    
JUPYTER_PYGMENT_STYLES = list(pstyles.get_all_styles())

# PYGMENT_STYLES = sorted(JUPYTER_PYGMENT_STYLES + StyleNames)
PYGMENT_STYLES = sorted(JUPYTER_PYGMENT_STYLES)

__all__ = StyleNames + ["StyleNames", "JUPYTER_PYGMENT_STYLES", "PYGMENT_STYLES"]
