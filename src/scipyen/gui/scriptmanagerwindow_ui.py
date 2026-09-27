# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'scriptmanagerwindow.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QGridLayout, QHeaderView,
    QMainWindow, QMenu, QMenuBar, QSizePolicy,
    QStatusBar, QTableWidget, QTableWidgetItem, QWidget)

class Ui_ScriptManagerWindow(object):
    def setupUi(self, ScriptManagerWindow):
        if not ScriptManagerWindow.objectName():
            ScriptManagerWindow.setObjectName(u"ScriptManagerWindow")
        ScriptManagerWindow.resize(522, 351)
        ScriptManagerWindow.setAcceptDrops(True)
        self.centralwidget = QWidget(ScriptManagerWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.scriptsTable = QTableWidget(self.centralwidget)
        if (self.scriptsTable.columnCount() < 2):
            self.scriptsTable.setColumnCount(2)
        __qtablewidgetitem = QTableWidgetItem()
        self.scriptsTable.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.scriptsTable.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        self.scriptsTable.setObjectName(u"scriptsTable")
        self.scriptsTable.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.scriptsTable.setAcceptDrops(True)
        self.scriptsTable.setMidLineWidth(0)
        self.scriptsTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.scriptsTable.setDragDropOverwriteMode(False)
        self.scriptsTable.setAlternatingRowColors(True)
        self.scriptsTable.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.scriptsTable.setShowGrid(False)
        self.scriptsTable.setWordWrap(False)
        self.scriptsTable.setColumnCount(2)
        self.scriptsTable.horizontalHeader().setStretchLastSection(True)

        self.gridLayout.addWidget(self.scriptsTable, 0, 0, 1, 1)

        ScriptManagerWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(ScriptManagerWindow)
        self.statusbar.setObjectName(u"statusbar")
        ScriptManagerWindow.setStatusBar(self.statusbar)
        self.menuBar = QMenuBar(ScriptManagerWindow)
        self.menuBar.setObjectName(u"menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 522, 28))
        self.menuScripts = QMenu(self.menuBar)
        self.menuScripts.setObjectName(u"menuScripts")
        ScriptManagerWindow.setMenuBar(self.menuBar)

        self.menuBar.addAction(self.menuScripts.menuAction())

        self.retranslateUi(ScriptManagerWindow)

        QMetaObject.connectSlotsByName(ScriptManagerWindow)
    # setupUi

    def retranslateUi(self, ScriptManagerWindow):
        ScriptManagerWindow.setWindowTitle(QCoreApplication.translate("ScriptManagerWindow", u"MainWindow", None))
        ___qtablewidgetitem = self.scriptsTable.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("ScriptManagerWindow", u"Script", None))
        ___qtablewidgetitem1 = self.scriptsTable.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("ScriptManagerWindow", u"Path", None))
        self.menuScripts.setTitle(QCoreApplication.translate("ScriptManagerWindow", u"Scripts", None))
    # retranslateUi

