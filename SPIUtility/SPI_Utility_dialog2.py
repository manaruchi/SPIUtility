# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SPIUtilityDialog
                                 A QGIS plugin
 Calculates and Analyses the Standardized Precipitation Index using IMD Precipitation Data
                             -------------------
        begin                : 2019-05-06
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Manaruchi Mohapatra
        email                : spiutility@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'SPI_Utility_dialog_base2.ui'))


class SPIUtilityDialog2(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(SPIUtilityDialog2, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
