# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""

See https://stackoverflow.com/questions/65707027/how-to-display-icon-and-text-together-in-pyqt5-menubar

solution by https://stackoverflow.com/users/2001654/musicamante


"""

from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__


class MenuProxy(QtWidgets.QProxyStyle):
    menuHack = False
    alertShown = False

    def useMenuHack(self, element, opt, widget):
        if (element in (self.CT_MenuBarItem, self.CE_MenuBarItem) and
            isinstance(widget, QtWidgets.QMenuBar) and
            opt.icon and not opt.icon.isNull() and opt.text):
                if not self.alertShown:
                    if widget.isNativeMenuBar():
                        return False
                        # NOTE: 2024-09-27 22:31:42
                        # this warning is not needed
                        # this will probably not be shown...
                    #     print('WARNING: menubar items with icons and text not supported for native menu bars')
                    styleName = self.baseStyle().objectName()
                    # NOTE: 2024-09-27 22:32:39 TODO
                    # this warning likely not needed, either
                    # if not 'windows' in styleName and styleName != 'fusion':
                    #     return False
                        # print('WARNING: menubar items with icons and text not supported for "{}" style'.format(
                        #     styleName))
                    self.alertShown = True
                return True
        return False

    def sizeFromContents(self, content, opt, size, widget=None):
        if self.useMenuHack(content, opt, widget):
            # return a valid size that includes both the icon and the text
            alignment = (QtCore.Qt.AlignCenter | QtCore.Qt.TextShowMnemonic |
                QtCore.Qt.TextDontClip | QtCore.Qt.TextSingleLine)
            if not self.proxy().styleHint(self.SH_UnderlineShortcut, opt, widget):
                alignment |= QtCore.Qt.TextHideMnemonic

            width = (opt.fontMetrics.size(alignment, opt.text).width() +
                self.pixelMetric(self.PM_SmallIconSize) +
                self.pixelMetric(self.PM_LayoutLeftMargin) * 2)

            textOpt = QtWidgets.QStyleOptionMenuItem(opt)
            textOpt.icon = QtGui.QIcon()
            height = super().sizeFromContents(content, textOpt, size, widget).height()

            return QtCore.QSize(width, height)

        return super().sizeFromContents(content, opt, size, widget)

    def drawControl(self, ctl, opt, qp, widget=None):
        if self.useMenuHack(ctl, opt, widget):
            # create a new option with no icon to draw a menubar item; setting
            # the menuHack allows us to ensure that the icon size is taken into
            # account from the drawItemText function
            textOpt = QtWidgets.QStyleOptionMenuItem(opt)
            textOpt.icon = QtGui.QIcon()
            self.menuHack = True
            # super().drawControl(ctl, textOpt, qp, widget)
            self.drawControl(ctl, textOpt, qp, widget)
            self.menuHack = False

            # compute the rectangle for the icon and call the default 
            # implementation to draw it
            iconExtent = self.pixelMetric(self.PM_SmallIconSize)
            # margin = self.pixelMetric(self.PM_LayoutLeftMargin) / 2
            margin = self.pixelMetric(self.PM_LayoutLeftMargin)
            top = opt.rect.y() + (opt.rect.height() - iconExtent) / 2
            # iconRect = QtCore.QRect(opt.rect.x() + margin, top, iconExtent, iconExtent)
            iconRect = QtCore.QRect(int(opt.rect.x() + margin), int(top), int(iconExtent), int(iconExtent))
            pm = opt.icon.pixmap(widget.window().windowHandle(), 
                QtCore.QSize(iconExtent, iconExtent), 
                QtGui.QIcon.Normal if opt.state & self.State_Enabled else QtGui.QIcon.Disabled)
            self.drawItemPixmap(qp, iconRect, QtCore.Qt.AlignCenter, pm)
            return
        super().drawControl(ctl, opt, qp, widget)

    def drawItemText(self, qp, rect, alignment, palette, enabled, text, role=QtGui.QPalette.NoRole):
        if self.menuHack:
            margin = (self.pixelMetric(self.PM_SmallIconSize) + 
                self.pixelMetric(self.PM_LayoutLeftMargin))
            rect = rect.adjusted(margin, 0, 0, 0)
        super().drawItemText(qp, rect, alignment, palette, enabled, text, role)


# class Test(QtWidgets.QMainWindow):
#     def __init__(self):
#         super().__init__()
#         menu = self.menuBar().addMenu(QtGui.QIcon.fromTheme('document-new'), 'File')
#         menu.addAction(QtGui.QIcon.fromTheme('application-exit'), 'Quit')
#         self.menuBar().addMenu(QtGui.QIcon.fromTheme('edit-cut'), 'Edit')
# 
# 
# if __name__ == '__main__':
#     import sys
#     app = QtWidgets.QApplication(sys.argv)
#     app.setStyle(MenuProxy(QtWidgets.QStyleFactory.create('fusion')))
#     # or, for windows systems:
#     # app.setStyle(MenuProxy())
# 
#     test = Test()
#     test.show()
#     sys.exit(app.exec_())
