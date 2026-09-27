# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'organismwidget.ui'
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
    QSizePolicy, QSpacerItem, QToolButton, QWidget)

from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget
from gui.widgets.small_widgets import LineEdit

class Ui_OrganismWidget(object):
    def setupUi(self, OrganismWidget):
        if not OrganismWidget.objectName():
            OrganismWidget.setObjectName(u"OrganismWidget")
        OrganismWidget.resize(357, 200)
        self.gridLayout_2 = QGridLayout(OrganismWidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.nameDescriptionWidget = NameDescriptionWidget(OrganismWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.nameDescriptionWidget.sizePolicy().hasHeightForWidth())
        self.nameDescriptionWidget.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.taxonDetailsToolButton = QToolButton(OrganismWidget)
        self.taxonDetailsToolButton.setObjectName(u"taxonDetailsToolButton")
        icon = QIcon(QIcon.fromTheme(u"view-list-tree"))
        self.taxonDetailsToolButton.setIcon(icon)
        self.taxonDetailsToolButton.setAutoRaise(True)

        self.gridLayout.addWidget(self.taxonDetailsToolButton, 0, 2, 1, 1)

        self.subSpeciesLineEdit = LineEdit(OrganismWidget)
        self.subSpeciesLineEdit.setObjectName(u"subSpeciesLineEdit")

        self.gridLayout.addWidget(self.subSpeciesLineEdit, 1, 1, 1, 1)

        self.taxonSpeciesLineEdit = LineEdit(OrganismWidget)
        self.taxonSpeciesLineEdit.setObjectName(u"taxonSpeciesLineEdit")

        self.gridLayout.addWidget(self.taxonSpeciesLineEdit, 0, 1, 1, 1)

        self.label_4 = QLabel(OrganismWidget)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_4, 3, 0, 1, 1)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_5 = QLabel(OrganismWidget)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_5.addWidget(self.label_5)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_5)

        self.toggleBiometricsToolButton = QToolButton(OrganismWidget)
        self.toggleBiometricsToolButton.setObjectName(u"toggleBiometricsToolButton")
        icon1 = QIcon(QIcon.fromTheme(u"document-properties"))
        self.toggleBiometricsToolButton.setIcon(icon1)
        self.toggleBiometricsToolButton.setCheckable(True)
        self.toggleBiometricsToolButton.setAutoRaise(True)

        self.horizontalLayout_5.addWidget(self.toggleBiometricsToolButton)


        self.gridLayout.addLayout(self.horizontalLayout_5, 4, 0, 1, 2)

        self.label_3 = QLabel(OrganismWidget)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)

        self.facilityIDLineEdit = LineEdit(OrganismWidget)
        self.facilityIDLineEdit.setObjectName(u"facilityIDLineEdit")

        self.gridLayout.addWidget(self.facilityIDLineEdit, 3, 1, 1, 1)

        self.label = QLabel(OrganismWidget)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.strainLineEdit = LineEdit(OrganismWidget)
        self.strainLineEdit.setObjectName(u"strainLineEdit")

        self.gridLayout.addWidget(self.strainLineEdit, 2, 1, 1, 1)

        self.label_2 = QLabel(OrganismWidget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)


        self.gridLayout_2.addLayout(self.gridLayout, 1, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label_4.setBuddy(self.facilityIDLineEdit)
        self.label_3.setBuddy(self.strainLineEdit)
        self.label.setBuddy(self.taxonSpeciesLineEdit)
        self.label_2.setBuddy(self.subSpeciesLineEdit)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(OrganismWidget)

        QMetaObject.connectSlotsByName(OrganismWidget)
    # setupUi

    def retranslateUi(self, OrganismWidget):
        OrganismWidget.setWindowTitle(QCoreApplication.translate("OrganismWidget", u"Form", None))
#if QT_CONFIG(tooltip)
        self.taxonDetailsToolButton.setToolTip(QCoreApplication.translate("OrganismWidget", u"Taxon Details", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.taxonDetailsToolButton.setStatusTip(QCoreApplication.translate("OrganismWidget", u"Taxon Details", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.taxonDetailsToolButton.setWhatsThis(QCoreApplication.translate("OrganismWidget", u"Taxon Details", None))
#endif // QT_CONFIG(whatsthis)
        self.taxonDetailsToolButton.setText(QCoreApplication.translate("OrganismWidget", u"Details", None))
#if QT_CONFIG(tooltip)
        self.label_4.setToolTip(QCoreApplication.translate("OrganismWidget", u"Facility ID", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.label_4.setStatusTip(QCoreApplication.translate("OrganismWidget", u"Facility ID", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.label_4.setWhatsThis(QCoreApplication.translate("OrganismWidget", u"Facility ID", None))
#endif // QT_CONFIG(whatsthis)
        self.label_4.setText(QCoreApplication.translate("OrganismWidget", u"ID: ", None))
        self.label_5.setText(QCoreApplication.translate("OrganismWidget", u"Biometrics: ", None))
#if QT_CONFIG(tooltip)
        self.toggleBiometricsToolButton.setToolTip(QCoreApplication.translate("OrganismWidget", u"Edit Biometrics", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.toggleBiometricsToolButton.setStatusTip(QCoreApplication.translate("OrganismWidget", u"Edit Biometrics", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.toggleBiometricsToolButton.setWhatsThis(QCoreApplication.translate("OrganismWidget", u"Edit Biometrics", None))
#endif // QT_CONFIG(whatsthis)
        self.toggleBiometricsToolButton.setText(QCoreApplication.translate("OrganismWidget", u"Biometrics", None))
        self.label_3.setText(QCoreApplication.translate("OrganismWidget", u"Strain: ", None))
#if QT_CONFIG(tooltip)
        self.facilityIDLineEdit.setToolTip(QCoreApplication.translate("OrganismWidget", u"Facility ID", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.facilityIDLineEdit.setStatusTip(QCoreApplication.translate("OrganismWidget", u"Facility ID", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.facilityIDLineEdit.setWhatsThis(QCoreApplication.translate("OrganismWidget", u"Facility ID", None))
#endif // QT_CONFIG(whatsthis)
        self.label.setText(QCoreApplication.translate("OrganismWidget", u"Taxon:", None))
        self.label_2.setText(QCoreApplication.translate("OrganismWidget", u"Subspecies: ", None))
    # retranslateUi

