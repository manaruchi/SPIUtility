# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SPIUtility
                                 A QGIS plugin
 Calculates and Analyses the Standardized Precipitation Index using IMD Precipitation Data
                             -------------------
        begin                : 2019-05-06
        copyright            : (C) 2019 by Manaruchi Mohapatra
        email                : spiutility@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load SPIUtility class from file SPIUtility.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """
    #
    from .SPI_Utility import SPIUtility
    return SPIUtility(iface)
