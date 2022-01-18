from gui import stylewidgets
import gui.painting_shared as paints
from gui.painting_shared import gradientLine, gradientCoordinates, scaleGradient, bound_point
bcombo = stylewidgets.BrushComboBox()
bcombo.show()
gr0 = bcombo._gradientDialog.gw._renderer.gradient
gr0
gc0 = bcombo._internalStyle
rect = bcombo._gradientDialog.gw._renderer.rect()
rect
gr1 = bcombo._gradientDialog.gw._renderer.gradient
gc1 = bcombo._internalStyle
gr2 = bcombo._gradientDialog.gw._renderer.gradient
gradientLine(gr1, rect)
gradientLine(gc0, rect)
gradientLine(gr0, rect)

