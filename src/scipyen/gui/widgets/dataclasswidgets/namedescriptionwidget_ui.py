# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'namedescriptionwidget.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QSizePolicy, QToolButton, QWidget)

from gui.widgets.small_widgets import LineEdit

class Ui_NameDescriptionWidget(object):
    def setupUi(self, NameDescriptionWidget):
        if not NameDescriptionWidget.objectName():
            NameDescriptionWidget.setObjectName(u"NameDescriptionWidget")
        NameDescriptionWidget.resize(357, 44)
        self.gridLayout = QGridLayout(NameDescriptionWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(NameDescriptionWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.nameLineEdit = LineEdit(NameDescriptionWidget)
        self.nameLineEdit.setObjectName(u"nameLineEdit")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.nameLineEdit.sizePolicy().hasHeightForWidth())
        self.nameLineEdit.setSizePolicy(sizePolicy)
        self.nameLineEdit.setClearButtonEnabled(True)

        self.horizontalLayout.addWidget(self.nameLineEdit)

        self.descriptionToolButton = QToolButton(NameDescriptionWidget)
        self.descriptionToolButton.setObjectName(u"descriptionToolButton")
        icon = QIcon(QIcon.fromTheme(u"description"))
        self.descriptionToolButton.setIcon(icon)
        self.descriptionToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.descriptionToolButton)

        self.viewDetailsToolButton = QToolButton(NameDescriptionWidget)
        self.viewDetailsToolButton.setObjectName(u"viewDetailsToolButton")
        icon1 = QIcon(QIcon.fromTheme(u"view-list-tree"))
        self.viewDetailsToolButton.setIcon(icon1)
        self.viewDetailsToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.viewDetailsToolButton)

        self.toggleParentEditorToolButton = QToolButton(NameDescriptionWidget)
        self.toggleParentEditorToolButton.setObjectName(u"toggleParentEditorToolButton")
        icon2 = QIcon(QIcon.fromTheme(u"user"))
        self.toggleParentEditorToolButton.setIcon(icon2)
        self.toggleParentEditorToolButton.setCheckable(True)
        self.toggleParentEditorToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.toggleParentEditorToolButton)

        self.replaceParentToolButton = QToolButton(NameDescriptionWidget)
        self.replaceParentToolButton.setObjectName(u"replaceParentToolButton")
        icon3 = QIcon(QIcon.fromTheme(u"system-switch-user"))
        self.replaceParentToolButton.setIcon(icon3)
        self.replaceParentToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.replaceParentToolButton)

        self.organismToolButton = QToolButton(NameDescriptionWidget)
        self.organismToolButton.setObjectName(u"organismToolButton")
        icon4 = QIcon(QIcon.fromTheme(u"document-properties"))
        self.organismToolButton.setIcon(icon4)
        self.organismToolButton.setCheckable(True)
        self.organismToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.organismToolButton)

        self.toggleDataExchangeWidgetToolButton = QToolButton(NameDescriptionWidget)
        self.toggleDataExchangeWidgetToolButton.setObjectName(u"toggleDataExchangeWidgetToolButton")
        icon5 = QIcon(QIcon.fromTheme(u"arrow-right-double"))
        self.toggleDataExchangeWidgetToolButton.setIcon(icon5)
        self.toggleDataExchangeWidgetToolButton.setCheckable(True)
        self.toggleDataExchangeWidgetToolButton.setAutoRaise(True)

        self.horizontalLayout.addWidget(self.toggleDataExchangeWidgetToolButton)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.nameLineEdit)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(NameDescriptionWidget)

        QMetaObject.connectSlotsByName(NameDescriptionWidget)
    # setupUi

    def retranslateUi(self, NameDescriptionWidget):
        NameDescriptionWidget.setWindowTitle(QCoreApplication.translate("NameDescriptionWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("NameDescriptionWidget", u"Name: ", None))
#if QT_CONFIG(tooltip)
        self.descriptionToolButton.setToolTip(QCoreApplication.translate("NameDescriptionWidget", u"Edit description", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.descriptionToolButton.setStatusTip(QCoreApplication.translate("NameDescriptionWidget", u"Edit description", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.descriptionToolButton.setWhatsThis(QCoreApplication.translate("NameDescriptionWidget", u"Edit description", None))
#endif // QT_CONFIG(whatsthis)
        self.descriptionToolButton.setText(QCoreApplication.translate("NameDescriptionWidget", u"Description", None))
        self.viewDetailsToolButton.setText(QCoreApplication.translate("NameDescriptionWidget", u"Details", None))
#if QT_CONFIG(tooltip)
        self.toggleParentEditorToolButton.setToolTip(QCoreApplication.translate("NameDescriptionWidget", u"Edit Parent Object", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.toggleParentEditorToolButton.setStatusTip(QCoreApplication.translate("NameDescriptionWidget", u"Edit Parent Object", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.toggleParentEditorToolButton.setWhatsThis(QCoreApplication.translate("NameDescriptionWidget", u"Edit Parent Object", None))
#endif // QT_CONFIG(whatsthis)
        self.toggleParentEditorToolButton.setText(QCoreApplication.translate("NameDescriptionWidget", u"Edit Parent", None))
        self.replaceParentToolButton.setText(QCoreApplication.translate("NameDescriptionWidget", u"Replace Parent", None))
#if QT_CONFIG(tooltip)
        self.organismToolButton.setToolTip(QCoreApplication.translate("NameDescriptionWidget", u"Edit Parent Organism", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.organismToolButton.setStatusTip(QCoreApplication.translate("NameDescriptionWidget", u"Edit Parent Organism", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.organismToolButton.setWhatsThis(QCoreApplication.translate("NameDescriptionWidget", u"Edit Parent Organism", None))
#endif // QT_CONFIG(whatsthis)
        self.organismToolButton.setText(QCoreApplication.translate("NameDescriptionWidget", u"Organism", None))
#if QT_CONFIG(tooltip)
        self.toggleDataExchangeWidgetToolButton.setToolTip(QCoreApplication.translate("NameDescriptionWidget", u"Data IO Actions", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.toggleDataExchangeWidgetToolButton.setStatusTip(QCoreApplication.translate("NameDescriptionWidget", u"Toggle Data IO Actions", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.toggleDataExchangeWidgetToolButton.setWhatsThis(QCoreApplication.translate("NameDescriptionWidget", u"Toggle Data IO Actions", None))
#endif // QT_CONFIG(whatsthis)
        self.toggleDataExchangeWidgetToolButton.setText(QCoreApplication.translate("NameDescriptionWidget", u"Data IO", None))
    # retranslateUi

