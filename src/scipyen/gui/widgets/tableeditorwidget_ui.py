# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tableeditorwidget.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QHeaderView,
    QSizePolicy, QSpacerItem, QToolButton, QWidget)

from gui.widgets.tabledataview import TableDataView

class Ui_TableEditorWidget(object):
    def setupUi(self, TableEditorWidget):
        if not TableEditorWidget.objectName():
            TableEditorWidget.setObjectName(u"TableEditorWidget")
        TableEditorWidget.resize(429, 174)
        self.gridLayout = QGridLayout(TableEditorWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.resizeColumnsToolButton = QToolButton(TableEditorWidget)
        self.resizeColumnsToolButton.setObjectName(u"resizeColumnsToolButton")
        icon = QIcon(QIcon.fromTheme(u"resizecol"))
        self.resizeColumnsToolButton.setIcon(icon)
        self.resizeColumnsToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.resizeColumnsToolButton)

        self.resizeRowsToolButton = QToolButton(TableEditorWidget)
        self.resizeRowsToolButton.setObjectName(u"resizeRowsToolButton")
        icon1 = QIcon(QIcon.fromTheme(u"resizerow"))
        self.resizeRowsToolButton.setIcon(icon1)
        self.resizeRowsToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.resizeRowsToolButton)

        self.prevSliceToolbutton = QToolButton(TableEditorWidget)
        self.prevSliceToolbutton.setObjectName(u"prevSliceToolbutton")
        icon2 = QIcon(QIcon.fromTheme(u"go-previous"))
        self.prevSliceToolbutton.setIcon(icon2)
        self.prevSliceToolbutton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.prevSliceToolbutton)

        self.nextSliceToolButton = QToolButton(TableEditorWidget)
        self.nextSliceToolButton.setObjectName(u"nextSliceToolButton")
        icon3 = QIcon(QIcon.fromTheme(u"go-next"))
        self.nextSliceToolButton.setIcon(icon3)
        self.nextSliceToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.nextSliceToolButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.setEditableToolButton = QToolButton(TableEditorWidget)
        self.setEditableToolButton.setObjectName(u"setEditableToolButton")
        icon4 = QIcon(QIcon.fromTheme(u"object-locked"))
        self.setEditableToolButton.setIcon(icon4)
        self.setEditableToolButton.setCheckable(True)
        self.setEditableToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.setEditableToolButton)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.tableView = TableDataView(TableEditorWidget)
        self.tableView.setObjectName(u"tableView")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.tableView.sizePolicy().hasHeightForWidth())
        self.tableView.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.tableView, 1, 0, 1, 1)


        self.retranslateUi(TableEditorWidget)

        QMetaObject.connectSlotsByName(TableEditorWidget)
    # setupUi

    def retranslateUi(self, TableEditorWidget):
        TableEditorWidget.setWindowTitle(QCoreApplication.translate("TableEditorWidget", u"Form", None))
#if QT_CONFIG(tooltip)
        self.resizeColumnsToolButton.setToolTip(QCoreApplication.translate("TableEditorWidget", u"Autoresize columns width to fit contents", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.resizeColumnsToolButton.setStatusTip(QCoreApplication.translate("TableEditorWidget", u"Autoresize columns width to fit contents", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.resizeColumnsToolButton.setWhatsThis(QCoreApplication.translate("TableEditorWidget", u"Autoresize columns width to fit contents", None))
#endif // QT_CONFIG(whatsthis)
        self.resizeColumnsToolButton.setText(QCoreApplication.translate("TableEditorWidget", u"Resize columns", None))
#if QT_CONFIG(tooltip)
        self.resizeRowsToolButton.setToolTip(QCoreApplication.translate("TableEditorWidget", u"Autoresize rows height to fit contents", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.resizeRowsToolButton.setStatusTip(QCoreApplication.translate("TableEditorWidget", u"Autoresize rows height to fit contents", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.resizeRowsToolButton.setWhatsThis(QCoreApplication.translate("TableEditorWidget", u"Autoresize rows height to fit contents", None))
#endif // QT_CONFIG(whatsthis)
        self.resizeRowsToolButton.setText(QCoreApplication.translate("TableEditorWidget", u"Resize rows", None))
#if QT_CONFIG(tooltip)
        self.prevSliceToolbutton.setToolTip(QCoreApplication.translate("TableEditorWidget", u"Previous frame of data", None))
#endif // QT_CONFIG(tooltip)
        self.prevSliceToolbutton.setText(QCoreApplication.translate("TableEditorWidget", u"Prev.", None))
#if QT_CONFIG(tooltip)
        self.nextSliceToolButton.setToolTip(QCoreApplication.translate("TableEditorWidget", u"Next frame of data", None))
#endif // QT_CONFIG(tooltip)
        self.nextSliceToolButton.setText(QCoreApplication.translate("TableEditorWidget", u"Next", None))
#if QT_CONFIG(tooltip)
        self.setEditableToolButton.setToolTip(QCoreApplication.translate("TableEditorWidget", u"Allow/Prevent Editing", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.setEditableToolButton.setStatusTip(QCoreApplication.translate("TableEditorWidget", u"Allow/Prevent Editing", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.setEditableToolButton.setWhatsThis(QCoreApplication.translate("TableEditorWidget", u"Allow/Prevent Editing", None))
#endif // QT_CONFIG(whatsthis)
        self.setEditableToolButton.setText(QCoreApplication.translate("TableEditorWidget", u"Edit", None))
    # retranslateUi

