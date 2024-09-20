# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar C. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-License-Identifier: GPL-3.0-or-later

# WARNING: when creating a new style make sure the style's `name` attribute is
# identical to the class name (case-sensitive!)
    
from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Token, Whitespace
 
from pygments import styles as pstyles

# from pygments.styles.native import NativeStyle

class KeplerDark(Style):
    name = "KeplerDark"
    
    background_color = '#232627'
    # highlight_color = '#404040'
    highlight_color = '#384f29'
    line_number_color = '#aaaaaa'
    
    styles = {
        # Token:              '#d0d0d0',
        Token:              '#eeeeee',
        # Token:              '#ffff00',
        # Whitespace:         '#666666',
        Whitespace:         '#232627',

        Comment:            'italic #ababab',
        Comment.Preproc:    'noitalic bold #ff3a3a',
        # Comment.Special:    'noitalic bold #e50808 bg:#520000',
        Comment.Special:    'noitalic bold #e50808 bg:#920000',

        Keyword:            'bold #6ebf26',
        Keyword.Pseudo:     'nobold',
        Operator.Word:      'bold #6ebf26',

        String:             '#ed9d13',
        String.Other:       '#ffa500',

        Number:             '#51b2fd',

        Name.Builtin:       '#2fbccd',
        Name.Variable:      '#40ffff',
        Name.Constant:      '#40ffff',
        Name.Class:         'underline #71adff',
        Name.Function:      '#71adff',
        Name.Namespace:     'underline #71adff',
        Name.Exception:     '#bbbbbb',
        Name.Tag:           'bold #6ebf26',
        Name.Attribute:     '#bbbbbb',
        Name.Decorator:     '#ffa500',

        Generic.Heading:    'bold #ffffff',
        Generic.Subheading: 'underline #ffffff',
        Generic.Deleted:    '#ff3a3a',
        Generic.Inserted:   '#589819',
        Generic.Error:      '#ff3a3a',
        Generic.Emph:       'italic',
        Generic.Strong:     'bold',
        Generic.EmphStrong: 'bold italic',
        # Generic.Prompt:     '#aaaaaa',
        Generic.Prompt:     '#cccccc',
        # Generic.Output:     '#cccccc',
        Generic.Output:     '#eeeeee',
        Generic.Traceback:  '#ff3a3a',

        Error:              'bg:#2d1e1e #a61717'
        # Error:              'bg:#e3d2d2 #a61717'
        # Error:              '#a61717'
    }

# pstyles.STYLES[KeplerDark.name] = (KeplerDark.__module__, KeplerDark.__name__, ())
