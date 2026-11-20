# -*- coding: utf-8 -*-
"""
pyVCI.theme
Shared Navy / Gray / White / Black color palette for all pyVCI tool UIs.
Every pyVCI tool should import its colors from here instead of declaring
its own palette, so the whole tab looks and feels like one product
(same convention as the pyNBT extension's own lib/pyNBT/theme.py).
"""
from System.Windows.Media import Color, SolidColorBrush


def _c(r, g, b):
    return Color.FromRgb(r, g, b)


CLR_HEADER      = _c(30, 41, 59)      # Navy header background
CLR_HEADER_TEXT = _c(255, 255, 255)   # White text on navy
CLR_HEADER_SUB  = _c(203, 213, 225)   # Light gray subtitle text
CLR_ACCENT      = _c(30, 41, 59)      # Navy accent
CLR_APPLY       = _c(46, 125, 50)     # Green - primary Apply action button
CLR_APPLY_TEXT  = _c(255, 255, 255)
CLR_BG          = _c(248, 249, 250)   # Off-white window background
CLR_CARD        = _c(255, 255, 255)   # White card/panel background
CLR_BORDER      = _c(203, 213, 225)   # Gray border
CLR_FOOTER      = _c(241, 245, 249)   # Light gray footer background
CLR_TEXT        = _c(30, 30, 30)      # Near-black body text
CLR_MUTED       = _c(120, 120, 120)   # Muted gray secondary text
CLR_SUCCESS     = _c(56, 142, 60)     # Green - success rows
CLR_SKIP        = _c(158, 158, 158)   # Gray - skipped rows
CLR_ERROR       = _c(198, 40, 40)     # Red - failed rows

CLR_SUCCESS_BG  = _c(234, 246, 235)   # Light green - "will update" row tint
CLR_ERROR_BG    = _c(251, 234, 234)   # Light red - error row tint


def brush(color):
    return SolidColorBrush(color)


def text_color_for_bg(color):
    """Auto-pick white/black text so it stays readable on a given background."""
    brightness = (color.R * 299 + color.G * 587 + color.B * 114) / 1000.0
    return CLR_HEADER_TEXT if brightness < 140 else CLR_TEXT
