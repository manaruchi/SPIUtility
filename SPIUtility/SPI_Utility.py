# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SPIUtility
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QDir
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QApplication, QMessageBox, QWidget, QTableWidgetItem
from datetime import datetime, date
# Initialize Qt resources from file resources.py
import resources
from osgeo import gdal, osr
import glob
import os
import numpy as np
import math
from scipy.stats import gamma
import csv


# Import the code for the dialog
from SPI_Utility_dialog import SPIUtilityDialog
from SPI_Utility_dialog2 import SPIUtilityDialog2
import os.path


class SPIUtility:
    """QGIS Plugin Implementation."""
    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'SPIUtility_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.dlg = SPIUtilityDialog()
        self.dlg2 = SPIUtilityDialog2()
        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&SPI Utility')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'SPIUtility')
        
        self.toolbar.setObjectName(u'SPIUtility')
        
        
        
        
    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SPIUtility', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        self.dlg = SPIUtilityDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToRasterMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/SPIUtility/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'SPI Utility for Raster...'),
            callback=self.run,
            parent=self.iface.mainWindow())
        
        self.add_action(
            icon_path,
            text=self.tr(u'SPI Utility for Point Data...'),
            callback=self.run2,
            parent=self.iface.mainWindow())
        
        self.dlg.pushButton.clicked.connect(self.select_output_file)
        self.dlg.pushButton_2.clicked.connect(self.checkdata)
        self.dlg.pushButton1.clicked.connect(self.getinput)
        self.dlg.pushButton.clicked.connect(self.getoutput)
        self.dlg.pushButton_4.clicked.connect(self.monthlycomp)
        self.dlg.pushButton_3.clicked.connect(self.calcspi)
        self.dlg.pushButton_5.clicked.connect(self.classify)
        self.dlg.pushButton_6.clicked.connect(self.getfilename)
        self.dlg.pushButton_7.clicked.connect(self.getfilename2)
        self.dlg.pushButton_9.clicked.connect(self.getinput1)
        self.dlg.pushButton_10.clicked.connect(self.getinput2)
        self.dlg.pushButton_8.clicked.connect(self.test)
        self.dlg.lineEdit_5.editingFinished.connect(self.getfilename_t)
        self.dlg.lineEdit.editingFinished.connect(self.getinput_tt)
        self.dlg2.pushButton_11.clicked.connect(self.getcsvfolder)
        self.dlg2.pushButton_12.clicked.connect(self.getoutput1)
        self.dlg2.pushButton_13.clicked.connect(self.checkcsv)
        self.dlg2.pushButton.clicked.connect(self.compositepoint)
        self.dlg2.pushButton_9.clicked.connect(self.compositefileinput)
        self.dlg2.pushButton_10.clicked.connect(self.pointspioutfol)
        self.dlg2.pushButton_3.clicked.connect(self.spipoint)
        
        self.dlg2.comboBox.currentIndexChanged.connect(self.loadspi)
        
    def checkleap(y):
        leapornot = 0
        if(y%4==0):
            leapornot = 1
            if(y%400==0):
                leapornot = 1
            elif(y%100==0):
                leapornot = 0
        else:
            leapornot = 0
        return leapornot
    
    def select_output_file(self):
        aa = self.dlg.lineEdit.text()
        self.dlg.lineEdit_2.setText(aa)


    def checkdata(self):
        self.dlg.pushButton_3.setEnabled(False)
        self.dlg.pushButton.setEnabled(False)
        self.dlg.pushButton1.setEnabled(False)
        self.dlg.pushButton_2.setEnabled(False)
        self.dlg.pushButton_4.setEnabled(False)
        self.dlg.pushButton_9.setEnabled(False)
        self.dlg.pushButton_10.setEnabled(False)
        self.dlg.pushButton_6.setEnabled(False)
        self.dlg.pushButton_7.setEnabled(False)
        self.dlg.pushButton_5.setEnabled(False)
        yearbegin = self.dlg.lineEdit_3.text()
        yearend = self.dlg.lineEdit_4.text()
        datadir = self.dlg.lineEdit.text()
        outputdir = self.dlg.lineEdit_2.text()
        if(yearbegin == "" or yearend =="" or datadir == "" or outputdir==""):
            self.dlg.textEdit.append("\nInput Precipitation Data directory, Output Precipitation Data Directory, Start Year and End Year field can not be left blank.\n")
        else:
            self.dlg.show()
            w = QWidget()
            messagee = 'The following parameters are selected. \nInput Directory : ' + str(datadir) + "\nOutput Data Directory : " + str(outputdir) + "\nStart Year : " + str(yearbegin) + "\nEnd Year : " + str(yearend) + '\n\nContine to check Data? '
            reply = QMessageBox.question(w, 'Continue?',messagee, QMessageBox.Yes, QMessageBox.No)
            self.dlg.show()
            if reply == QMessageBox.Yes:
                
                yearbegin = int(yearbegin)
                yearend = int(yearend)
                prog_c = 0.0
                inc_c = 100.0 / (yearend-yearbegin + 1)
                
                erroryear = list()
                errordate = list()
                fileslist = glob.glob(datadir + "/*.tif")
                if(os.path.exists(outputdir)==False):
                    os.mkdir(outputdir)
                #---------Check if Datadir, startyear and endyear are correct----------
                if(fileslist == []):
                    self.dlg.textEdit.append("\nInput precipitation directory not found or the directory has no precipitation data in it.\n")
                else:
                    if(yearbegin == 0 or yearend==0):
                        self.dlg.textEdit.append("\nStart year and End Year value is incorrect.\n")
                    else:
                        t1 = datetime.now()
                        self.dlg.textEdit.append("\nChecking the Data...\nStarted on : " + str(t1))
                        
                        
                        i = yearbegin
                        if(len(fileslist)>=(yearend-yearbegin+1)):
                            
                            while(i<=yearend):
                                filepath = fileslist[i-yearbegin]
                                cur_raster = gdal.Open(filepath)
                                
                                leapornot = 0
                                if(i%4==0):
                                    leapornot = 1
                                    if(i%400==0):
                                        leapornot = 1
                                    elif(i%100==0):
                                        leapornot = 0
                                else:
                                    leapornot = 0
                                
                                if(cur_raster is None):
                                    erroryear.append(str(i) + " : Precipitation data raster is missing")
                                else:
                                    if(leapornot==0):
                                        if(cur_raster.RasterCount!=365):
                                            errordate.append(str(i) + " : Incomplete Data. This raster must contain 365 bands")
                                        Arr = 0
                                        m=0
                                        while(m<365):
                                            band = cur_raster.GetRasterBand(m+1)
                                            Arr = band.ReadAsArray()
                                            if(Arr is None):
                                                self.dlg.textEdit.append("Error in Band " + str(m+1) + " in year "+str(i))
                                                
                                            band = 0
                                            m = m + 1
                                        
                                    else:
                                        Arr=0
                                        m=0
                                        while(m<366):
                                            band = cur_raster.GetRasterBand(m+1)
                                            Arr = band.ReadAsArray()
                                            if(Arr is None):
                                                self.dlg.textEdit.append("Error in Band " + str(m+1) + " in year "+str(i))
                                                
                                            band = 0
                                            m = m + 1
                                        if(cur_raster.RasterCount!=366):
                                            errordate.append(str(i) + " : Incomplete Data. This raster must contain 366 bands")
                                    
                                        
                                cur_raster = 0
                                QApplication.processEvents()
                                prog_c = prog_c + inc_c
                                
                                self.dlg.progressBar.setValue(prog_c)
                                QApplication.processEvents()
                                
                                i = i + 1
                            if(erroryear==[] and errordate==[]):
                                t2 = datetime.now()
                                delta = t2 - t1
                                
                                self.dlg.textEdit.append("\nComplete Data Available!!! \n\nClick on Generate Monthly Composite to generate the monthly precipitation composite from the data provided.\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                                self.dlg.pushButton_4.setEnabled(True)
                            else:
                                self.dlg.pushButton_4.setEnabled(False)
                                self.dlg.textEdit.append("\nData Missing!!! Please check the data.\n\nThe following errors are found : ")
                                for xx in erroryear:
                                    self.dlg.textEdit.append(xx)
                                for yy in errordate:
                                    self.dlg.textEdit.append(yy)
                                
                               
                        else:
                            self.dlg.pushButton_4.setEnabled(False)
                            self.dlg.textEdit.append("\nData Missing!!! Please check the data.\n\nThe following errors are found :\n\nThe range of years is greater than the input precipitation data.")
        
        self.dlg.progressBar.setValue(0)
        self.dlg.pushButton_3.setEnabled(True)
        self.dlg.pushButton.setEnabled(True)
        self.dlg.pushButton1.setEnabled(True)
        self.dlg.pushButton_2.setEnabled(True)
        self.dlg.pushButton_4.setEnabled(True)
        self.dlg.pushButton_9.setEnabled(True)
        self.dlg.pushButton_10.setEnabled(True)
        self.dlg.pushButton_6.setEnabled(True)
        self.dlg.pushButton_7.setEnabled(True)
        self.dlg.pushButton_5.setEnabled(True)
        

            
            
    def monthlycomp(self):
        self.dlg.pushButton_3.setEnabled(False)
        self.dlg.pushButton.setEnabled(False)
        self.dlg.pushButton1.setEnabled(False)
        self.dlg.pushButton_2.setEnabled(False)
        self.dlg.pushButton_4.setEnabled(False)
        self.dlg.pushButton_9.setEnabled(False)
        self.dlg.pushButton_10.setEnabled(False)
        self.dlg.pushButton_6.setEnabled(False)
        self.dlg.pushButton_7.setEnabled(False)
        self.dlg.pushButton_5.setEnabled(False)
        yearbegin = self.dlg.lineEdit_3.text()
        yearend = self.dlg.lineEdit_4.text()
        datadir = self.dlg.lineEdit.text()
        outdir_m = self.dlg.lineEdit_2.text()
        outdir = outdir_m + "/Composite"
        
        self.dlg.show()
        w = QWidget()
        messagee = 'Generate Monthly Composites?'
        reply = QMessageBox.question(w, 'Continue?',messagee, QMessageBox.Yes, QMessageBox.No)
        self.dlg.show()
        if reply == QMessageBox.Yes:
        
            if(os.path.exists(outdir)==False):
                os.mkdir(outdir)
            c = int(yearbegin)
            yearbegin = int(yearbegin)
            yearend = int(yearend)
            
            perinc = 100.0 / ((yearend - yearbegin) + 1) 
            progval = 0.0
            t1 = datetime.now()
            self.dlg.textEdit.append("\nGenerating Monthly Composites...\nStarted on : " + str(t1))
            
            while(c<=yearend):
                i = c
                i = int(i)
                checkleap = 0
                if(i%4==0):
                    checkleap = 1
                    if(i%400==0):
                        checkleap = 1
                    elif(i%100==0):
                        checkleap = 0
                else:
                    checkleap = 0
                m = 1
                filepath = str(datadir) + "/RF_" + str(i) + ".tif"
                cur_raster = gdal.Open(filepath)
                rasterArray = 0
                """For January"""
                while(m<=31):
                    band = cur_raster.GetRasterBand(m)
                    rasterArray = rasterArray + band.ReadAsArray()   
                    m = m + 1
                geotransform = cur_raster.GetGeoTransform()
                originX = geotransform[0]
                originY = geotransform[3]
                pixelw = geotransform[1]
                pixelh = geotransform[5]
                cols = cur_raster.RasterXSize
                rows = cur_raster.RasterYSize
                
                driver = gdal.GetDriverByName("GTiff")
                fn = str(outdir) + "/RF_" + str(i) + "_1.tif"
                outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                outRaster.GetRasterBand(1).WriteArray(rasterArray)
                outRasterSRS = osr.SpatialReference()
                outRasterSRS.ImportFromWkt(cur_raster.GetProjectionRef())
                outRaster.SetProjection(outRasterSRS.ExportToWkt())
                outRaster.FlushCache()
                
                    
                 
                
                
                """For February"""
                rasterArray = 0
                while(m<=(59+checkleap)):
                    band = cur_raster.GetRasterBand(m)
                    rasterArray = rasterArray + band.ReadAsArray()   
                    m = m + 1
                geotransform = cur_raster.GetGeoTransform()
                originX = geotransform[0]
                originY = geotransform[3]
                pixelw = geotransform[1]
                pixelh = geotransform[5]
                cols = cur_raster.RasterXSize
                rows = cur_raster.RasterYSize
                
                driver = gdal.GetDriverByName("GTiff")
                fn =  str(outdir) + "/RF_" + str(i) + "_2.tif"
                outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                outRaster.GetRasterBand(1).WriteArray(rasterArray)
                outRasterSRS = osr.SpatialReference()
                outRasterSRS.ImportFromWkt(cur_raster.GetProjectionRef())
                outRaster.SetProjection(outRasterSRS.ExportToWkt())
                outRaster.FlushCache()
                
                """For March"""
                rasterArray = 0
                enddate = m + 31
                while(m<enddate):
                    band = cur_raster.GetRasterBand(m)
                    rasterArray = rasterArray + band.ReadAsArray()   
                    m = m + 1
                geotransform = cur_raster.GetGeoTransform()
                originX = geotransform[0]
                originY = geotransform[3]
                pixelw = geotransform[1]
                pixelh = geotransform[5]
                cols = cur_raster.RasterXSize
                rows = cur_raster.RasterYSize
                
                driver = gdal.GetDriverByName("GTiff")
                fn = str(outdir) + "/RF_" + str(i) + "_3.tif"
                outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                outRaster.GetRasterBand(1).WriteArray(rasterArray)
                outRasterSRS = osr.SpatialReference()
                outRasterSRS.ImportFromWkt(cur_raster.GetProjectionRef())
                outRaster.SetProjection(outRasterSRS.ExportToWkt())
                outRaster.FlushCache()
                """For April"""
                rasterArray = 0
                enddate = m + 30
                while(m<enddate):
                    band = cur_raster.GetRasterBand(m)
                    rasterArray = rasterArray + band.ReadAsArray()   
                    m = m + 1
                geotransform = cur_raster.GetGeoTransform()
                originX = geotransform[0]
                originY = geotransform[3]
                pixelw = geotransform[1]
                pixelh = geotransform[5]
                cols = cur_raster.RasterXSize
                rows = cur_raster.RasterYSize
                
                driver = gdal.GetDriverByName("GTiff")
                fn = str(outdir) + "/RF_" + str(i) + "_4.tif"
                outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                outRaster.GetRasterBand(1).WriteArray(rasterArray)
                outRasterSRS = osr.SpatialReference()
                outRasterSRS.ImportFromWkt(cur_raster.GetProjectionRef())
                outRaster.SetProjection(outRasterSRS.ExportToWkt())
                outRaster.FlushCache()
                """For May"""
                rasterArray = 0
                enddate = m + 31
                while(m<enddate):
                    band = cur_raster.GetRasterBand(m)
                    rasterArray = rasterArray + band.ReadAsArray()   
                    m = m + 1
                geotransform = cur_raster.GetGeoTransform()
                originX = geotransform[0]
                originY = geotransform[3]
                pixelw = geotransform[1]
                pixelh = geotransform[5]
                cols = cur_raster.RasterXSize
                rows = cur_raster.RasterYSize
                
                driver = gdal.GetDriverByName("GTiff")
                fn = str(outdir) + "/RF_" + str(i) + "_5.tif"
                outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                outRaster.GetRasterBand(1).WriteArray(rasterArray)
                outRasterSRS = osr.SpatialReference()
                outRasterSRS.ImportFromWkt(cur_raster.GetProjectionRef())
                outRaster.SetProjection(outRasterSRS.ExportToWkt())
                outRaster.FlushCache()
                """For June"""
                rasterArray = 0
                enddate = m + 30
                while(m<enddate):
                    band = cur_raster.GetRasterBand(m)
                    rasterArray = rasterArray + band.ReadAsArray()   
                    m = m + 1
                geotransform = cur_raster.GetGeoTransform()
                originX = geotransform[0]
                originY = geotransform[3]
                pixelw = geotransform[1]
                pixelh = geotransform[5]
                cols = cur_raster.RasterXSize
                rows = cur_raster.RasterYSize
                
                driver = gdal.GetDriverByName("GTiff")
                fn = str(outdir) + "/RF_" + str(i) + "_6.tif"
                outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                outRaster.GetRasterBand(1).WriteArray(rasterArray)
                outRasterSRS = osr.SpatialReference()
                outRasterSRS.ImportFromWkt(cur_raster.GetProjectionRef())
                outRaster.SetProjection(outRasterSRS.ExportToWkt())
                outRaster.FlushCache()
                """For July"""
                rasterArray = 0
                enddate = m + 31
                while(m<enddate):
                    band = cur_raster.GetRasterBand(m)
                    rasterArray = rasterArray + band.ReadAsArray()   
                    m = m + 1
                geotransform = cur_raster.GetGeoTransform()
                originX = geotransform[0]
                originY = geotransform[3]
                pixelw = geotransform[1]
                pixelh = geotransform[5]
                cols = cur_raster.RasterXSize
                rows = cur_raster.RasterYSize
                
                driver = gdal.GetDriverByName("GTiff")
                fn = str(outdir) + "/RF_" + str(i) + "_7.tif"
                outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                outRaster.GetRasterBand(1).WriteArray(rasterArray)
                outRasterSRS = osr.SpatialReference()
                outRasterSRS.ImportFromWkt(cur_raster.GetProjectionRef())
                outRaster.SetProjection(outRasterSRS.ExportToWkt())
                outRaster.FlushCache()
                """For August"""
                rasterArray = 0
                enddate = m + 31
                while(m<enddate):
                    band = cur_raster.GetRasterBand(m)
                    rasterArray = rasterArray + band.ReadAsArray()   
                    m = m + 1
                geotransform = cur_raster.GetGeoTransform()
                originX = geotransform[0]
                originY = geotransform[3]
                pixelw = geotransform[1]
                pixelh = geotransform[5]
                cols = cur_raster.RasterXSize
                rows = cur_raster.RasterYSize
                
                driver = gdal.GetDriverByName("GTiff")
                fn = str(outdir) + "/RF_" + str(i) + "_8.tif"
                outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                outRaster.GetRasterBand(1).WriteArray(rasterArray)
                outRasterSRS = osr.SpatialReference()
                outRasterSRS.ImportFromWkt(cur_raster.GetProjectionRef())
                outRaster.SetProjection(outRasterSRS.ExportToWkt())
                outRaster.FlushCache()
                """For September"""
                rasterArray = 0
                enddate = m + 30
                while(m<enddate):
                    band = cur_raster.GetRasterBand(m)
                    rasterArray = rasterArray + band.ReadAsArray()   
                    m = m + 1
                geotransform = cur_raster.GetGeoTransform()
                originX = geotransform[0]
                originY = geotransform[3]
                pixelw = geotransform[1]
                pixelh = geotransform[5]
                cols = cur_raster.RasterXSize
                rows = cur_raster.RasterYSize
                
                driver = gdal.GetDriverByName("GTiff")
                fn =  str(outdir) + "/RF_" + str(i) + "_9.tif"
                outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                outRaster.GetRasterBand(1).WriteArray(rasterArray)
                outRasterSRS = osr.SpatialReference()
                outRasterSRS.ImportFromWkt(cur_raster.GetProjectionRef())
                outRaster.SetProjection(outRasterSRS.ExportToWkt())
                outRaster.FlushCache()
                """For October"""
                rasterArray = 0
                enddate = m + 31
                while(m<enddate):
                    band = cur_raster.GetRasterBand(m)
                    rasterArray = rasterArray + band.ReadAsArray()   
                    m = m + 1
                geotransform = cur_raster.GetGeoTransform()
                originX = geotransform[0]
                originY = geotransform[3]
                pixelw = geotransform[1]
                pixelh = geotransform[5]
                cols = cur_raster.RasterXSize
                rows = cur_raster.RasterYSize
                
                driver = gdal.GetDriverByName("GTiff")
                fn = str(outdir) + "/RF_" + str(i) + "_10.tif"
                outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                outRaster.GetRasterBand(1).WriteArray(rasterArray)
                outRasterSRS = osr.SpatialReference()
                outRasterSRS.ImportFromWkt(cur_raster.GetProjectionRef())
                outRaster.SetProjection(outRasterSRS.ExportToWkt())
                outRaster.FlushCache()
                """For November"""
                rasterArray = 0
                enddate = m + 30
                while(m<enddate):
                    band = cur_raster.GetRasterBand(m)
                    rasterArray = rasterArray + band.ReadAsArray()   
                    m = m + 1
                geotransform = cur_raster.GetGeoTransform()
                originX = geotransform[0]
                originY = geotransform[3]
                pixelw = geotransform[1]
                pixelh = geotransform[5]
                cols = cur_raster.RasterXSize
                rows = cur_raster.RasterYSize
                
                driver = gdal.GetDriverByName("GTiff")
                fn = str(outdir) + "/RF_" + str(i) + "_11.tif"
                outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                outRaster.GetRasterBand(1).WriteArray(rasterArray)
                outRasterSRS = osr.SpatialReference()
                outRasterSRS.ImportFromWkt(cur_raster.GetProjectionRef())
                outRaster.SetProjection(outRasterSRS.ExportToWkt())
                outRaster.FlushCache()
                """For December"""
                rasterArray = 0
                enddate = m + 31
                while(m<enddate):
                    band = cur_raster.GetRasterBand(m)
                    if(band is not None):
                        rasterArray = rasterArray + band.ReadAsArray()   
                    m = m + 1
                geotransform = cur_raster.GetGeoTransform()
                originX = geotransform[0]
                originY = geotransform[3]
                pixelw = geotransform[1]
                pixelh = geotransform[5]
                cols = cur_raster.RasterXSize
                rows = cur_raster.RasterYSize
                
                driver = gdal.GetDriverByName("GTiff")
                fn = str(outdir) + "/RF_" + str(i) + "_12.tif"
                outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                outRaster.GetRasterBand(1).WriteArray(rasterArray)
                outRasterSRS = osr.SpatialReference()
                outRasterSRS.ImportFromWkt(cur_raster.GetProjectionRef())
                outRaster.SetProjection(outRasterSRS.ExportToWkt())
                outRaster.FlushCache()
                
                QApplication.processEvents() 
                
                progval = progval + perinc
                
                self.dlg.progressBar.setValue(progval)
                QApplication.processEvents()
                c = c + 1
            
            
            #-------------------------------release the files
            outRaster = 0
            cur_raster = 0
            band = 0
            t2 = datetime.now()
            delta = t2 - t1
            self.dlg.textEdit.append("\n\nMonthly composites generated at\n" + str(outdir) +"\nFinished on : " + str(t2))
            hrs = delta.seconds // 3600
            mins = (delta.seconds - (3600*hrs)) // 60
            secs = delta.seconds - (3600 * hrs) - (60*mins)
            self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
            
            self.dlg.textEdit.append("\nProceed for generation of SPI.")
            self.dlg.label_6.setText("Data Status : Complete")
            if(os.path.exists(outdir_m + "/spivals")==False):
                os.mkdir(outdir_m + "/spivals")
        
        
        
        
        self.dlg.label_15.setText(datadir)
        self.dlg.label_16.setText(outdir_m)
        self.dlg.lineEdit_7.setText(str(outdir))
        self.dlg.lineEdit_8.setText(str(outdir_m))
        self.dlg.label_17.setText(str(yearbegin))
        self.dlg.label_18.setText(str(yearend))
        self.dlg.pushButton_3.setEnabled(True)
        self.dlg.progressBar.setValue(0)
        self.dlg.tabWidget.setCurrentIndex(1)
        self.dlg.pushButton_3.setEnabled(True)
        self.dlg.pushButton.setEnabled(True)
        self.dlg.pushButton1.setEnabled(True)
        self.dlg.pushButton_2.setEnabled(True)
        self.dlg.pushButton_4.setEnabled(False)
        self.dlg.pushButton_9.setEnabled(True)
        self.dlg.pushButton_10.setEnabled(True)
        self.dlg.pushButton_6.setEnabled(True)
        self.dlg.pushButton_7.setEnabled(True)
        self.dlg.pushButton_5.setEnabled(True)
    
    def calcspi(self):
        
        self.dlg.show()
        self.dlg.pushButton_3.setEnabled(False)
        self.dlg.pushButton.setEnabled(False)
        self.dlg.pushButton1.setEnabled(False)
        self.dlg.pushButton_2.setEnabled(False)
        self.dlg.pushButton_4.setEnabled(False)
        self.dlg.pushButton_9.setEnabled(False)
        self.dlg.pushButton_10.setEnabled(False)
        self.dlg.pushButton_6.setEnabled(False)
        self.dlg.pushButton_7.setEnabled(False)
        self.dlg.pushButton_5.setEnabled(False)
        
        ts_x = self.dlg.comboBox.currentText()
        if(ts_x == '1 month'):
            ts = 1
        elif(ts_x == '3 months'):
            ts = 3
        elif(ts_x == '4 months'):
            ts = 4
        elif(ts_x == '6 months'):
            ts = 6
        elif(ts_x == '9 months'):
            ts = 9
        elif(ts_x == '12 months'):
            ts = 12
        elif(ts_x == '24 months'):
            ts = 24
        elif(ts_x == '36 months'):
            ts = 36
            
        stm_x = self.dlg.comboBox_2.currentText()
        if(stm_x == 'January'):
            stm = 1
        elif(stm_x == 'February'):
            stm = 2
        elif(stm_x == 'March'):
            stm = 3
        elif(stm_x == 'April'):
            stm = 4
        elif(stm_x == 'May'):
            stm = 5
        elif(stm_x == 'June'):
            stm = 6
        elif(stm_x == 'July'):
            stm = 7
        elif(stm_x == 'August'):
            stm = 8
        elif(stm_x == 'September'):
            stm = 9
        elif(stm_x == 'October'):
            stm = 10
        elif(stm_x == 'November'):
            stm = 11
        elif(stm_x == 'December'):
            stm = 12
        
        enm_x = self.dlg.comboBox_3.currentText()
        if(enm_x == 'January'):
            enm = 1
        elif(enm_x == 'February'):
            enm = 2
        elif(enm_x == 'March'):
            enm = 3
        elif(enm_x == 'April'):
            enm = 4
        elif(enm_x == 'May'):
            enm = 5
        elif(enm_x == 'June'):
            enm = 6
        elif(enm_x == 'July'):
            enm = 7
        elif(enm_x == 'August'):
            enm = 8
        elif(enm_x == 'September'):
            enm = 9
        elif(enm_x == 'October'):
            enm = 10
        elif(enm_x == 'November'):
            enm = 11
        elif(enm_x == 'December'):
            enm = 12
        
        #Error flag------------------------------------------------------------
        is_err = 0
        errorlist = []
        #----------------------------------------------------------------------
        filedir = self.dlg.label_15.text()
        outdir = self.dlg.lineEdit_8.text()
        outdir_c = self.dlg.lineEdit_7.text()
        
        if(outdir_c == ""):
            is_err = 1
            errorlist.append("Monthly Composites Folder can not be left blank.")
        
        if(outdir == ""):
            is_err = 1
            errorlist.append("Output Folder can not be left blank.")
        
        if(os.path.exists(outdir)==False):
            is_err = 1
            errorlist.append("Output path does not exist.")
        
        flistcheck = glob.glob(outdir_c + "/*.tif")
        if(len(flistcheck)==0):
            is_err = 1
            errorlist.append("No files found in the input precipitation directory.")
            
        if(is_err==1):
            self.dlg.textEdit.append("The following errors are found.\n")
            ss = 0
            while(ss<len(errorlist)):
                self.dlg.textEdit.append(str(errorlist[ss]))
                ss = ss +1
            self.dlg.pushButton_3.setEnabled(True)
        else:
            self.dlg.show()
            w = QWidget()
            messagee = 'The following parameters are selected.' + '\nMonthly Composites Folder : ' + str(outdir_c) + '\nOutput Folder : ' + str(outdir) +'\nTimescale : ' + str(self.dlg.comboBox.currentText()) + "\nStart month : " + str(self.dlg.comboBox_2.currentText()) + "\nEnd month : " + str(self.dlg.comboBox_3.currentText()) + '\n\nGenerate SPI for the specified duration? '
            reply = QMessageBox.question(w, 'Continue?',messagee, QMessageBox.Yes, QMessageBox.No)
            self.dlg.show()
            if reply == QMessageBox.Yes:
                if(os.path.exists(outdir + "/spivals/")==False):
                    os.mkdir(outdir + "/spivals/")
                yearbegin = (self.dlg.label_17.text())
                yearend = (self.dlg.label_18.text())
                
                
                
                yearbegin = int(yearbegin)
                yearend = int(yearend)
                
                if(yearbegin == 0 or yearend ==0):
                    fileslistxx = glob.glob(outdir_c + "/*.tif")
                    firstfile = fileslistxx[0]
                    firstfilex = firstfile[len(outdir_c):]
                    yearbegin = firstfilex[4:8]
                    lastfile = fileslistxx[len(fileslistxx)-1]
                    lastfilex = lastfile[len(outdir_c):]
                    yearend = lastfilex[4:8]
                    
                    yearbegin = int(yearbegin)
                    yearend = int(yearend)
                
                monthsl = []
                
                stmc= stm
                enmc = enm
                
                if(stmc < enmc):
                    while(stmc<=enmc):
                        monthsl.append(stmc)
                        stmc = stmc + 1
                elif(stmc>enmc):
                    while(stmc<13):
                        monthsl.append(stmc)
                        stmc = stmc + 1
                    ss = 1
                    while(ss<=enmc):
                        monthsl.append(ss)
                        ss =ss + 1
                else:
                    monthsl.append(stmc)
                
                # M a s k  G e n e r a t i o n
                fileslist = glob.glob(outdir_c + "\*.tif")
                
                rasterinit = gdal.Open(fileslist[0])
                self.dlg.textEdit.append("\nMask Generation Started.\n")
                QApplication.processEvents()
                maskrow = rasterinit.RasterYSize
                maskcol = rasterinit.RasterXSize
                rasarr1 = rasterinit.ReadAsArray()
        
                mask = rasterinit.ReadAsArray()
                
                maskr = 0
                maskc = 0
                
                while(maskr < maskrow):
                    maskc = 0
                    while(maskc < maskcol):
                        if(rasarr1[maskr][maskc]<0):
                            
                            mask[maskr][maskc] = 0
                            prog_val = (maskr*maskc)/(maskrow*maskcol) * 100
                            self.dlg.progressBar.setValue(prog_val)
                            QApplication.processEvents()
                            
                        else:
                            
                            mask[maskr][maskc] = 1
                            prog_val = (maskr*maskc)/(maskrow*maskcol) * 100
                            self.dlg.progressBar.setValue(prog_val)
                            QApplication.processEvents()                
                        maskc = maskc + 1
                
                
                    maskr = maskr + 1
        
                maskgeotransform = rasterinit.GetGeoTransform()
                maskoriginX = maskgeotransform[0]
                maskoriginY = maskgeotransform[3]
                maskpixelw = maskgeotransform[1]
                maskpixelh = maskgeotransform[5]
                maskdriver = gdal.GetDriverByName("GTiff")
                maskfn = outdir + "\mask.tif"
                maskoutRaster = maskdriver.Create(maskfn, maskcol,maskrow, 1 , gdal.GDT_Float32,)
                maskoutRaster.SetGeoTransform((maskoriginX, maskpixelw, 0, maskoriginY, 0, maskpixelh))
                maskoutRaster.GetRasterBand(1).WriteArray(mask)
                maskoutRasterSRS = osr.SpatialReference()
                maskoutRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                maskoutRaster.SetProjection(maskoutRasterSRS.ExportToWkt())
                maskoutRaster.FlushCache()
                self.dlg.textEdit.append("Mask Generated !!!\n")
                QApplication.processEvents()
                cur_raster = 0
                
                if(ts==1): 
                    if(os.path.exists(outdir + "/spivals/1")==False):
                        os.mkdir(outdir + "/spivals/1")
                    xxx = 0
                    while(xxx<len(monthsl)):
                        self.dlg.progressBar.setValue(0)
                        QApplication.processEvents()
                        t1 = datetime.now()
                        self.dlg.textEdit.append("\n\n1 month SPI values for month " + str(monthsl[xxx]) + " started on " + str(t1) + "\n")
                        QApplication.processEvents()
                        if(os.path.exists(outdir + "/spivals/1/" + str(monthsl[xxx]))==False):
                               os.mkdir(outdir + "/spivals/1/" + str(monthsl[xxx]))
               
                        curmonth = monthsl[xxx]
                       
                        c0 = 2.515517
                        c1 = 0.802583
                        c2 = 0.010328
                        d1 = 1.4327888
                        d2 = 0.189269
                        d3 = 0.001308
                        showstatus = 1 #if status message is to be printed or not
                        finalvals = []
                        curyearwrite = yearbegin
                        
                        megaarr = []
                        xx = yearbegin
                        rasterinit = gdal.Open(fileslist[0])
                        geotransform = rasterinit.GetGeoTransform()
                        rows = rasterinit.RasterYSize
                        cols = rasterinit.RasterXSize
                        
                        
                        cur_add_arr = np.zeros((rows,cols))
                        while(xx<=yearend):
                            megaarr.append(cur_add_arr)
                            xx = xx + 1
                        megaarr = np.array(megaarr)
                        
                        cc = 0
                        rr = 0
                        pseudomat = []
                        while(rr<rows):
                            cc = 0
                            while(cc<cols):
                                pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                cc = cc + 1
                            rr = rr + 1
                        pseudomat = np.array(pseudomat)
                        
                        rcc = 0 
                        ccc = 0
                        proc_inc = 100.000 / ((rows-1) * (cols-1))
                        proc_val = 0
                        while(rcc<rows):
                            ccc = 0
                            while(ccc<cols):
                                QApplication.processEvents()
                                proc_val = proc_val + proc_inc
                                
                                QApplication.processEvents()
                                self.dlg.progressBar.setValue(proc_val)
                                QApplication.processEvents()
                                currow = int(rcc)
                                curcol = int(ccc)
                                noofzero = 0
                                yearcounter = yearbegin
                                
                                rfvals = []
                                rfvalsx = []
                                
                                while(yearcounter<=yearend):
                                    
                                    cur_array = []
                                    cur_raster = gdal.Open(str(outdir_c) + "/RF_" + str(yearcounter) + "_" + str(curmonth) + ".tif")
                                    cur_array = cur_raster.ReadAsArray()
                                    
                                    if(cur_array[currow,curcol]>0):
                                        rfvals.append(cur_array[currow,curcol])
                                        rfvalsx.append(cur_array[currow,curcol])
                                    else:
                                        rfvals.append(0.01)
                                        noofzero = noofzero + 1
                                    cur_raster = 0
                                    yearcounter = yearcounter + 1
                                    
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(rfvals)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                while(a<len(rfvals)):
                                    
                                    if(rfvals[a]>=0):
                                        
                                        curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    if(mask[currow][curcol]==1):
                                            megaarr[a][currow][curcol]  = spiv
                                    else:
                                            megaarr[a][currow][curcol]  = None
                                        
                                        
                                    
                                        
                                    a = a + 1
                                ccc = ccc + 1
                            rcc = rcc + 1
                        
                        zz = yearbegin
                        while(zz<=yearend):
                            
                            originX = geotransform[0]
                            originY = geotransform[3]
                            pixelw = geotransform[1]
                            pixelh = geotransform[5]
                            driver = gdal.GetDriverByName("GTiff")
                            fn = outdir + "/spivals/1/" + str(monthsl[xxx]) + "/SPI_" + str(zz) + "_" + str(curmonth) + ".tif"
                            outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                            outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                            outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                            outRasterSRS = osr.SpatialReference()
                            outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                            outRaster.SetProjection(outRasterSRS.ExportToWkt())
                            outRaster.FlushCache()
                            
                            outRaster = 0
                            zz = zz + 1
                        self.dlg.progressBar.setValue(0)
                        t2 = datetime.now()
                        delta = t2-t1
                        
                        self.dlg.textEdit.append("\n\n1 month SPI values for month " + str(monthsl[xxx]) + " generated at \n" + outdir + "\\spivals\\1\\" + str(monthsl[xxx]) + "\nFinished on : " + str(t2))
                        hrs = delta.seconds // 3600
                        mins = (delta.seconds - (3600*hrs)) // 60
                        secs = delta.seconds - (3600 * hrs) - (60*mins)
                        self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                        xxx =xxx+1        
                
                elif(ts==3):
                    if(os.path.exists(outdir + "/spivals/3")==False):
                        os.mkdir(outdir + "/spivals/3")
                    if(len(monthsl)<3):
                        self.dlg.textEdit.append("\n3 month SPI can not be calculated for the month range specified.\n")
                    else:
                        xxx = 0
                        while(xxx<(len(monthsl)-2)):
                            
                            if(monthsl[xxx] == 11):
                                
                                
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n3 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+2]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2]))==False):
                                       os.mkdir(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2]))
                                
                                if(os.path.exists(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "/Composite/RF_" + str(qwe) + "_" + str(qwe+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "/Composite/RF_" + str(yearcounter) + "_" + str(yearcounter+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            
                                            
                                            cur_array = (cur_array1) / 3
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "/SPI_" + str(zz) + "_" + str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n3 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+2])+ " generated at \n" + outdir + "\\spivals\\3\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                xxx =xxx+1      
                                
                                
                            elif(monthsl[xxx] == 12):
        
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n3 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+2]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2]))==False):
                                       os.mkdir(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2]))
                                
                                if(os.path.exists(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "/Composite/RF_" + str(qwe) + "_" + str(qwe+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "/Composite/RF_" + str(yearcounter) + "_" + str(yearcounter+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            
                                            
                                            cur_array = (cur_array1) / 3
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "/SPI_" + str(zz) + "_" + str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n3 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+2])+ " generated at \n" + outdir + "\\spivals\\3\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                                xxx =xxx+1                     
                            
                            else:
                                
                                
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n3 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+2]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2]))==False):
                                       os.mkdir(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2]))
                                
                                if(os.path.exists(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<=qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "/Composite/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<=yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "/Composite/RF_" + str(yearcounter) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            
                                            
                                            cur_array = (cur_array1) / 3
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<=yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/3/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "/SPI_" + str(zz) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n3 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+2])+ " generated at \n" + outdir + "\\spivals\\3\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "\nFInished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                                xxx =xxx+1       
                
                elif(ts==4):
                    if(os.path.exists(outdir + "/spivals/4")==False):
                        os.mkdir(outdir + "/spivals/4")
                    if(len(monthsl)<4):
                        self.dlg.textEdit.append("\n4 month SPI can not be calculated for the month range specified.\n")
                    else:
                        xxx = 0
                        
                        while(xxx<(len(monthsl)-3)):
                            
                            if(monthsl[xxx] == 10):
                                
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n4 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+3]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "_" +str(monthsl[xxx+3]))==False):
                                       os.mkdir(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2]) + "_" +str(monthsl[xxx+3]))
                                
                                if(os.path.exists(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "_" +str(monthsl[xxx+3])+ "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "_" +str(monthsl[xxx+3])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + "/Composite/RF_" + str(qwe) + "_" + str(qwe+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3])+ ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3])+ "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + "/Composite/RF_" + str(yearcounter) + "_" + str(yearcounter+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            
                                            
                                            cur_array = (cur_array1) / 4
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + "/SPI_" + str(zz) + "_" + str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3])+ ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n4 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+3])+ " generated at \n" + outdir + "\\spivals\\4\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2]) + "_" +str(monthsl[xxx+3])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                xxx = xxx + 1      
                                
                                
                                
                                
                                
                                
                                
                                
                                
                            elif(monthsl[xxx] == 11):
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n4 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+3]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "_" +str(monthsl[xxx+3]))==False):
                                       os.mkdir(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2]) + "_" +str(monthsl[xxx+3]))
                                
                                if(os.path.exists(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "_" +str(monthsl[xxx+3])+ "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "_" +str(monthsl[xxx+3])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + "/Composite/RF_" + str(qwe) + "_" + str(qwe+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3])+ ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3])+ "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + "/Composite/RF_" + str(yearcounter) + "_" + str(yearcounter+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            
                                            
                                            cur_array = (cur_array1) / 4
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + "/SPI_" + str(zz) + "_" + str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3])+ ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n4 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+3])+ " generated at \n" + outdir + "\\spivals\\4\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2]) + "_" +str(monthsl[xxx+3])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                xxx = xxx + 1      
                                     
                                
                                
                            elif(monthsl[xxx] == 12):
        
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n4 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+3]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "_" +str(monthsl[xxx+3]))==False):
                                       os.mkdir(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2]) + "_" +str(monthsl[xxx+3]))
                                
                                if(os.path.exists(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "_" +str(monthsl[xxx+3])+ "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "_" +str(monthsl[xxx+3])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + "/Composite/RF_" + str(qwe) + "_" + str(qwe+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3])+ ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3])+ "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + "/Composite/RF_" + str(yearcounter) + "_" + str(yearcounter+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            
                                            
                                            cur_array = (cur_array1) / 4
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + "/SPI_" + str(zz) + "_" + str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3])+ ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n4 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+3])+ " generated at \n" + outdir + "\\spivals\\4\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2]) + "_" +str(monthsl[xxx+3])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                xxx = xxx + 1       
                            
                            else:
                                
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n4 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+3]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]))==False):
                                       os.mkdir(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]))
                       
                                if(os.path.exists(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "_" + str(monthsl[xxx+3]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "_" + str(monthsl[xxx+3])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<=qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2])+ "_" + str(monthsl[xxx+3]) + "/Composite/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2])+ "_" + str(monthsl[xxx+3]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<=yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2])+ "_" + str(monthsl[xxx+3]) + "/Composite/RF_" + str(yearcounter) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 4
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<=yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/4/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2]) + "_" + str(monthsl[xxx+3]) + "/SPI_" + str(zz) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" + str(monthsl[xxx+2])+ "_" + str(monthsl[xxx+3]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n4 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+3])+ " generated at \n" + outdir + "\\spivals\\4\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+1]) + "_" +str(monthsl[xxx+2])+ "_" + str(monthsl[xxx+3])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1    
                                
        
                elif(ts==6):
                    if(os.path.exists(outdir + "/spivals/6")==False):
                        os.mkdir(outdir + "/spivals/6")
                    if(len(monthsl)<6):
                        self.dlg.textEdit.append("\n6 month SPI can not be calculated for the month range specified.\n")
                    else:
                        xxx = 0
                        while(xxx<(len(monthsl)-5)):
                            
                            if(monthsl[xxx] == 8):
        
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n6 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+5]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]))==False):
                                       os.mkdir(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]))
                       
                                if(os.path.exists(outdir + "/spivals/6/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+5]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/6/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + "/Composite/RF_" + str(qwe) + "_" +str(qwe+1) + "_" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/Composite/RF_" + str(yearcounter) + "_" + str(yearcounter+1) + "_" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 6
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/SPI_" + str(zz) +"_"+ str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n6 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+5])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+5])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1                         
                                
               
                                
                                
                            elif(monthsl[xxx] == 9):
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n6 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+5]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]))==False):
                                       os.mkdir(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]))
                       
                                if(os.path.exists(outdir + "/spivals/6/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+5]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/6/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + "/Composite/RF_" + str(qwe) + "_" +str(qwe+1) + "_" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/Composite/RF_" + str(yearcounter) + "_" + str(yearcounter+1) + "_" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 6
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/SPI_" + str(zz) +"_"+ str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n6 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+5])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+5])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1   
        
                            elif(monthsl[xxx] == 10):
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n6 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+5]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]))==False):
                                       os.mkdir(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]))
                       
                                if(os.path.exists(outdir + "/spivals/6/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+5]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/6/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + "/Composite/RF_" + str(qwe) + "_" +str(qwe+1) + "_" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/Composite/RF_" + str(yearcounter) + "_" + str(yearcounter+1) + "_" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 6
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/SPI_" + str(zz) +"_"+ str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n6 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+5])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+5])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1                       
        
                            elif(monthsl[xxx] == 11):
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n6 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+5]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]))==False):
                                       os.mkdir(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]))
                       
                                if(os.path.exists(outdir + "/spivals/6/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+5]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/6/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + "/Composite/RF_" + str(qwe) + "_" +str(qwe+1) + "_" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/Composite/RF_" + str(yearcounter) + "_" + str(yearcounter+1) + "_" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 6
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/SPI_" + str(zz) +"_"+ str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n6 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+5])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+5])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1 
        
                            elif(monthsl[xxx] == 12):
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n6 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+5]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]))==False):
                                       os.mkdir(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]))
                       
                                if(os.path.exists(outdir + "/spivals/6/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+5]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/6/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + "/Composite/RF_" + str(qwe) + "_" +str(qwe+1) + "_" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/Composite/RF_" + str(yearcounter) + "_" + str(yearcounter+1) + "_" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 6
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/SPI_" + str(zz) +"_"+ str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n6 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+5])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+5])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1   
                           
                            else:
                                
                                
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n6 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+5]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]))==False):
                                       os.mkdir(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]))
                       
                                if(os.path.exists(outdir + "/spivals/6/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+5]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<=qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/6/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + "/Composite/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<=yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/Composite/RF_" + str(yearcounter) + "_" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+5]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 6
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<=yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/6/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + "/SPI_" + str(zz) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+5]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n6 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+5])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+5])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1 
                                
                                
                                
                                
                                
                                
                                
                                
        
        
                elif(ts==9):
                    if(os.path.exists(outdir + "/spivals/9")==False):
                        os.mkdir(outdir + "/spivals/9")
                    if(len(monthsl)<9):
                        self.dlg.textEdit.append("\n9 month SPI can not be calculated for the month range specified.\n")
                    else:
                        xxx = 0
                        while(xxx<(len(monthsl)-8)):
                            
                            if(monthsl[xxx] == 5):
        
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))
                       
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+8]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array7 = []
                                    cur_raster7 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+6]) + ".tif")
                                    cur_array7 = cur_raster7.ReadAsArray()
                                    
                                    cur_array8 = []
                                    cur_raster8 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+7]) + ".tif")
                                    cur_array8 = cur_raster8.ReadAsArray()
                                    
                                    cur_array9 = []
                                    cur_raster9 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+8]) + ".tif")
                                    cur_array9 = cur_raster9.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6+ cur_array7+ cur_array8+ cur_array9)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + "/Composite/RF_" + str(qwe) + "_" + str(qwe+1) + "_"  + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/RF_" + str(yearcounter) + "_" +str(yearcounter+1) + "_"+ str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 9
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/SPI_" + str(zz) + "_" + str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1     
        
                            elif(monthsl[xxx] == 6):
        
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))
                       
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+8]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array7 = []
                                    cur_raster7 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+6]) + ".tif")
                                    cur_array7 = cur_raster7.ReadAsArray()
                                    
                                    cur_array8 = []
                                    cur_raster8 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+7]) + ".tif")
                                    cur_array8 = cur_raster8.ReadAsArray()
                                    
                                    cur_array9 = []
                                    cur_raster9 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+8]) + ".tif")
                                    cur_array9 = cur_raster9.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6+ cur_array7+ cur_array8+ cur_array9)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + "/Composite/RF_" + str(qwe) + "_" + str(qwe+1) + "_"  + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/RF_" + str(yearcounter) + "_" +str(yearcounter+1) + "_"+ str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 9
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/SPI_" + str(zz) + "_" + str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1
        
                            elif(monthsl[xxx] == 7):
        
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))
                       
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+8]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array7 = []
                                    cur_raster7 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+6]) + ".tif")
                                    cur_array7 = cur_raster7.ReadAsArray()
                                    
                                    cur_array8 = []
                                    cur_raster8 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+7]) + ".tif")
                                    cur_array8 = cur_raster8.ReadAsArray()
                                    
                                    cur_array9 = []
                                    cur_raster9 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+8]) + ".tif")
                                    cur_array9 = cur_raster9.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6+ cur_array7+ cur_array8+ cur_array9)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + "/Composite/RF_" + str(qwe) + "_" + str(qwe+1) + "_"  + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/RF_" + str(yearcounter) + "_" +str(yearcounter+1) + "_"+ str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 9
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/SPI_" + str(zz) + "_" + str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1
                           
                            elif(monthsl[xxx] == 8):
        
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))
                       
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+8]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array7 = []
                                    cur_raster7 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+6]) + ".tif")
                                    cur_array7 = cur_raster7.ReadAsArray()
                                    
                                    cur_array8 = []
                                    cur_raster8 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+7]) + ".tif")
                                    cur_array8 = cur_raster8.ReadAsArray()
                                    
                                    cur_array9 = []
                                    cur_raster9 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+8]) + ".tif")
                                    cur_array9 = cur_raster9.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6+ cur_array7+ cur_array8+ cur_array9)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + "/Composite/RF_" + str(qwe) + "_" + str(qwe+1) + "_"  + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/RF_" + str(yearcounter) + "_" +str(yearcounter+1) + "_"+ str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 9
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/SPI_" + str(zz) + "_" + str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1
                                
                            elif(monthsl[xxx] == 9):
        
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))
                       
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+8]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array7 = []
                                    cur_raster7 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+6]) + ".tif")
                                    cur_array7 = cur_raster7.ReadAsArray()
                                    
                                    cur_array8 = []
                                    cur_raster8 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+7]) + ".tif")
                                    cur_array8 = cur_raster8.ReadAsArray()
                                    
                                    cur_array9 = []
                                    cur_raster9 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+8]) + ".tif")
                                    cur_array9 = cur_raster9.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6+ cur_array7+ cur_array8+ cur_array9)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + "/Composite/RF_" + str(qwe) + "_" + str(qwe+1) + "_"  + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/RF_" + str(yearcounter) + "_" +str(yearcounter+1) + "_"+ str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 9
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/SPI_" + str(zz) + "_" + str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1                        
        
                            elif(monthsl[xxx] == 10):
        
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))
                       
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+8]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array7 = []
                                    cur_raster7 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+6]) + ".tif")
                                    cur_array7 = cur_raster7.ReadAsArray()
                                    
                                    cur_array8 = []
                                    cur_raster8 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+7]) + ".tif")
                                    cur_array8 = cur_raster8.ReadAsArray()
                                    
                                    cur_array9 = []
                                    cur_raster9 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+8]) + ".tif")
                                    cur_array9 = cur_raster9.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6+ cur_array7+ cur_array8+ cur_array9)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + "/Composite/RF_" + str(qwe) + "_" + str(qwe+1) + "_"  + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/RF_" + str(yearcounter) + "_" +str(yearcounter+1) + "_"+ str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 9
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/SPI_" + str(zz) + "_" + str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1
        
                            elif(monthsl[xxx] == 11):
        
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))
                       
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+8]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array7 = []
                                    cur_raster7 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+6]) + ".tif")
                                    cur_array7 = cur_raster7.ReadAsArray()
                                    
                                    cur_array8 = []
                                    cur_raster8 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+7]) + ".tif")
                                    cur_array8 = cur_raster8.ReadAsArray()
                                    
                                    cur_array9 = []
                                    cur_raster9 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+8]) + ".tif")
                                    cur_array9 = cur_raster9.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6+ cur_array7+ cur_array8+ cur_array9)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + "/Composite/RF_" + str(qwe) + "_" + str(qwe+1) + "_"  + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/RF_" + str(yearcounter) + "_" +str(yearcounter+1) + "_"+ str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 9
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/SPI_" + str(zz) + "_" + str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1
        
                            elif(monthsl[xxx] == 12):
                                
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))
                       
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+8]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array7 = []
                                    cur_raster7 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+6]) + ".tif")
                                    cur_array7 = cur_raster7.ReadAsArray()
                                    
                                    cur_array8 = []
                                    cur_raster8 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+7]) + ".tif")
                                    cur_array8 = cur_raster8.ReadAsArray()
                                    
                                    cur_array9 = []
                                    cur_raster9 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_" + str(monthsl[xxx+8]) + ".tif")
                                    cur_array9 = cur_raster9.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6+ cur_array7+ cur_array8+ cur_array9)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + "/Composite/RF_" + str(qwe) + "_" + str(qwe+1) + "_"  + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/RF_" + str(yearcounter) + "_" +str(yearcounter+1) + "_"+ str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 9
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/SPI_" + str(zz) + "_" + str(zz+1) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1 
                                
                                
                                
                                
                                
                                
        
                                
                                
                            else:
                                
                                self.dlg.progressBar.setValue(0)
                                QApplication.processEvents()
                                t1 = datetime.now()
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8]) + " started on : " + str(t1) + "\n")
                                QApplication.processEvents()
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]))
                       
                                if(os.path.exists(outdir + "/spivals/9/" + str(monthsl[xxx]) +  "_" + str(monthsl[xxx+8]) + "/Composite")==False):
                                       os.mkdir(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "/Composite")
                                      
                                #Generate Composite files
                                
                                proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                                proc_valq = 0
                                
                                qwe = yearbegin
                                qwe2 = yearend
                                self.dlg.textEdit.append("\nComposite Generation Started...")
                                while(qwe<=qwe2):
                                    
                                    cur_array1 = []
                                    cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + ".tif")
                                    
                                    cur_array1 = cur_raster1.ReadAsArray()
                                    
                                    cur_array2 = []
                                    cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+1]) + ".tif")
                                    cur_array2 = cur_raster2.ReadAsArray()
                                    
                                    cur_array3 = []
                                    cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+2]) + ".tif")
                                    cur_array3 = cur_raster3.ReadAsArray()
                                    
                                    cur_array4 = []
                                    cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+3]) + ".tif")
                                    cur_array4 = cur_raster4.ReadAsArray()
                                    
                                    cur_array5 = []
                                    cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+4]) + ".tif")
                                    cur_array5 = cur_raster5.ReadAsArray()
                                    
                                    cur_array6 = []
                                    cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+5]) + ".tif")
                                    cur_array6 = cur_raster6.ReadAsArray()
                                    
                                    cur_array7 = []
                                    cur_raster7 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+6]) + ".tif")
                                    cur_array7 = cur_raster7.ReadAsArray()
                                    
                                    cur_array8 = []
                                    cur_raster8 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+7]) + ".tif")
                                    cur_array8 = cur_raster8.ReadAsArray()
                                    
                                    cur_array9 = []
                                    cur_raster9 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_" + str(monthsl[xxx+8]) + ".tif")
                                    cur_array9 = cur_raster9.ReadAsArray()
                                    
                                    cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6+ cur_array7+ cur_array8+ cur_array9)
                                    
                                    geotransform = cur_raster1.GetGeoTransform()
                                    rows = rasterinit.RasterYSize
                                    cols = rasterinit.RasterXSize
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + "/Composite/RF_" + str(qwe) + "_" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(cur_array)
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    
                                    QApplication.processEvents()
                                    proc_valq = proc_valq + proginc_q
                                    
                                    QApplication.processEvents()
                                    self.dlg.progressBar.setValue(proc_valq)
                                    QApplication.processEvents()
                                    
                                    
                                
                                    
                                    qwe = qwe + 1
                       
                                
                                self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/" + "\n\nSPI calculation from the composites starts..." )
                                
                                
                                
                                
                                
                                
                                
                                
                                
                                self.dlg.progressBar.setValue(0)
                                curmonth = monthsl[xxx]
                               
                                c0 = 2.515517
                                c1 = 0.802583
                                c2 = 0.010328
                                d1 = 1.4327888
                                d2 = 0.189269
                                d3 = 0.001308
                                showstatus = 1 #if status message is to be printed or not
                                finalvals = []
                                curyearwrite = yearbegin
                                
                                megaarr = []
                                xx = yearbegin
                                rasterinit = gdal.Open(fileslist[0])
                                geotransform = rasterinit.GetGeoTransform()
                                rows = rasterinit.RasterYSize
                                cols = rasterinit.RasterXSize
                                
                                
                                cur_add_arr = np.zeros((rows,cols))
                                while(xx<=yearend):
                                    megaarr.append(cur_add_arr)
                                    xx = xx + 1
                                megaarr = np.array(megaarr)
                                
                                cc = 0
                                rr = 0
                                pseudomat = []
                                while(rr<rows):
                                    cc = 0
                                    while(cc<cols):
                                        pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                                        cc = cc + 1
                                    rr = rr + 1
                                pseudomat = np.array(pseudomat)
                                
                                rcc = 0 
                                ccc = 0
                                proc_inc = 100.000 / ((rows-1) * (cols-1))
                                proc_val = 0
                                while(rcc<rows):
                                    ccc = 0
                                    while(ccc<cols):
                                        QApplication.processEvents()
                                        proc_val = proc_val + proc_inc
                                        
                                        QApplication.processEvents()
                                        self.dlg.progressBar.setValue(proc_val)
                                        QApplication.processEvents()
                                        currow = int(rcc)
                                        curcol = int(ccc)
                                        noofzero = 0
                                        yearcounter = yearbegin
                                        
                                        rfvals = []
                                        rfvalsx = []
                                        
                                        while(yearcounter<=yearend):
                                            
                                            cur_array1 = []
                                            
                                            cur_raster1 = gdal.Open(outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/Composite/RF_" + str(yearcounter) + "_" + str(monthsl[xxx]) + "_"  + str(monthsl[xxx+8]) + ".tif")
                                            cur_array1 = cur_raster1.ReadAsArray()
                                            
                                            geotransform = cur_raster1.GetGeoTransform()
                                            
                                            
                                            cur_array = (cur_array1) / 9
                                            
                                            if(cur_array[currow,curcol]>0):
                                                rfvals.append(cur_array[currow,curcol])
                                                rfvalsx.append(cur_array[currow,curcol])
                                            else:
                                                rfvals.append(0.01)
                                                noofzero = noofzero + 1
                                            cur_raster = 0
                                            yearcounter = yearcounter + 1
                                            
                                        gammav = []
                                        t = []
                                        shapex = 0
                                        loc = 0
                                        scalex = 0
                                        
                                        shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                                        #Probability of Zero
                                        zeroprob = noofzero / len(rfvals)
                                        
                                        a = 0
                                        g = 0
                                        spiv = 0.0
                                        while(a<len(rfvals)):
                                            
                                            if(rfvals[a]>=0):
                                                
                                                curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                                gammav.append(curvale)
                                                if(curvale<=0.5):
                                                    g = (math.log(1/(curvale*curvale)))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                    
                                                else:
                                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                                    t.append(g)
                                                    
                                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                                
                                            if(mask[currow][curcol]==1):
                                                    megaarr[a][currow][curcol]  = spiv
                                            else:
                                                    megaarr[a][currow][curcol]  = None
                                                
                                                
                                            
                                                
                                            a = a + 1
                                        ccc = ccc + 1
                                    rcc = rcc + 1
                                
                                zz = yearbegin
                                while(zz<=yearend):
                                    
                                    originX = geotransform[0]
                                    originY = geotransform[3]
                                    pixelw = geotransform[1]
                                    pixelh = geotransform[5]
                                    driver = gdal.GetDriverByName("GTiff")
                                    fn = outdir + "/spivals/9/" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + "/SPI_" + str(zz) + "_" + str(monthsl[xxx]) + "_" + str(monthsl[xxx+8]) + ".tif"
                                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                                    outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                                    outRasterSRS = osr.SpatialReference()
                                    outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                                    outRaster.FlushCache()
                                    
                                    outRaster = 0
                                    zz = zz + 1
                                self.dlg.progressBar.setValue(0)
                                t2 = datetime.now()
                                delta = t2 - t1
                                self.dlg.textEdit.append("\n\n9 month SPI values for month " + str(monthsl[xxx]) + " to " + str(monthsl[xxx+8])+ " generated at \n" + outdir + "\\spivals\\6\\" +str(monthsl[xxx]) + "_" + str(monthsl[xxx+8])+ "\nFinished on : " + str(t2))
                                hrs = delta.seconds // 3600
                                mins = (delta.seconds - (3600*hrs)) // 60
                                secs = delta.seconds - (3600 * hrs) - (60*mins)
                                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
                        
                                
                                xxx =xxx+1 
                                
                                
                                
                                
                                
                                
                                
                                
                                          
        
                elif(ts==12):
                    
                    self.dlg.progressBar.setValue(0)
                    QApplication.processEvents()
                    t1 = datetime.now()
                    self.dlg.textEdit.append("\n\n12 month SPI values generation started on : " + str(t1) + "\n")
                    QApplication.processEvents()
                    if(os.path.exists(outdir + "/spivals/12") ==False):
                           os.mkdir(outdir + "/spivals/12/")
           
                    if(os.path.exists(outdir + "/spivals/12/Composite")==False):
                           os.mkdir(outdir + "/spivals/12/Composite")
                          
                    #Generate Composite files
                    
                    proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                    proc_valq = 0
                    
                    qwe = yearbegin
                    qwe2 = yearend
                    self.dlg.textEdit.append("\nComposite Generation Started...")
                    while(qwe<=qwe2):
                        
                        cur_array1 = []
                        cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_1.tif")
                        cur_array1 = cur_raster1.ReadAsArray()
                        
                        cur_array2 = []
                        cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_2.tif")
                        cur_array2 = cur_raster2.ReadAsArray()
                        
                        cur_array3 = []
                        cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_3.tif")
                        cur_array3 = cur_raster3.ReadAsArray()
                        
                        cur_array4 = []
                        cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_4.tif")
                        cur_array4 = cur_raster4.ReadAsArray()
                        
                        cur_array5 = []
                        cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_5.tif")
                        cur_array5 = cur_raster5.ReadAsArray()
                        
                        cur_array6 = []
                        cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_6.tif")
                        cur_array6 = cur_raster6.ReadAsArray()
                        
                        cur_array7 = []
                        cur_raster7 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_7.tif")
                        cur_array7 = cur_raster7.ReadAsArray()
                        
                        cur_array8 = []
                        cur_raster8 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_8.tif")
                        cur_array8 = cur_raster8.ReadAsArray()
                        
                        cur_array9 = []
                        cur_raster9 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_9.tif")
                        cur_array9 = cur_raster9.ReadAsArray()
                        
                        cur_array10 = []
                        cur_raster10 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_10.tif")
                        cur_array10 = cur_raster10.ReadAsArray()
                        
                        cur_array11 = []
                        cur_raster11 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_11.tif")
                        cur_array11 = cur_raster11.ReadAsArray()
                        
                        cur_array12 = []
                        cur_raster12 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_12.tif")
                        cur_array12 = cur_raster12.ReadAsArray()
                        
                        cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6 + cur_array7 + cur_array8 + cur_array9 + cur_array10 + cur_array11 + cur_array12)
                        
                        geotransform = cur_raster1.GetGeoTransform()
                        rows = rasterinit.RasterYSize
                        cols = rasterinit.RasterXSize
                        
                        originX = geotransform[0]
                        originY = geotransform[3]
                        pixelw = geotransform[1]
                        pixelh = geotransform[5]
                        driver = gdal.GetDriverByName("GTiff")
                        fn = outdir + "/spivals/12/Composite/RF_" + str(qwe) + ".tif"
                        outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                        outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                        outRaster.GetRasterBand(1).WriteArray(cur_array)
                        outRasterSRS = osr.SpatialReference()
                        outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                        outRaster.SetProjection(outRasterSRS.ExportToWkt())
                        outRaster.FlushCache()
                        
                        outRaster = 0
                        
                        QApplication.processEvents()
                        proc_valq = proc_valq + proginc_q
                        
                        QApplication.processEvents()
                        self.dlg.progressBar.setValue(proc_valq)
                        QApplication.processEvents()
                        
                        
                    
                        
                        qwe = qwe + 1
           
                    
                    self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/12/Composite/" + "\n\nSPI calculation from the composites starts..." )
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    self.dlg.progressBar.setValue(0)
                    
                   
                    c0 = 2.515517
                    c1 = 0.802583
                    c2 = 0.010328
                    d1 = 1.4327888
                    d2 = 0.189269
                    d3 = 0.001308
                    showstatus = 1 #if status message is to be printed or not
                    finalvals = []
                    curyearwrite = yearbegin
                    
                    megaarr = []
                    xx = yearbegin
                    rasterinit = gdal.Open(fileslist[0])
                    geotransform = rasterinit.GetGeoTransform()
                    rows = rasterinit.RasterYSize
                    cols = rasterinit.RasterXSize
                    
                    
                    cur_add_arr = np.zeros((rows,cols))
                    while(xx<=yearend):
                        megaarr.append(cur_add_arr)
                        xx = xx + 1
                    megaarr = np.array(megaarr)
                    
                    cc = 0
                    rr = 0
                    pseudomat = []
                    while(rr<rows):
                        cc = 0
                        while(cc<cols):
                            pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                            cc = cc + 1
                        rr = rr + 1
                    pseudomat = np.array(pseudomat)
                    
                    rcc = 0 
                    ccc = 0
                    proc_inc = 100.000 / ((rows-1) * (cols-1))
                    proc_val = 0
                    while(rcc<rows):
                        ccc = 0
                        while(ccc<cols):
                            QApplication.processEvents()
                            proc_val = proc_val + proc_inc
                            
                            QApplication.processEvents()
                            self.dlg.progressBar.setValue(proc_val)
                            QApplication.processEvents()
                            currow = int(rcc)
                            curcol = int(ccc)
                            noofzero = 0
                            yearcounter = yearbegin
                            
                            rfvals = []
                            rfvalsx = []
                            
                            while(yearcounter<=yearend):
                                
                                cur_array1 = []
                                
                                cur_raster1 = gdal.Open(outdir + "/spivals/12/Composite/RF_" + str(yearcounter) + ".tif")
                                cur_array1 = cur_raster1.ReadAsArray()
                                
                                geotransform = cur_raster1.GetGeoTransform()
                                
                                
                                cur_array = (cur_array1) / 12
                                
                                if(cur_array[currow,curcol]>0):
                                    rfvals.append(cur_array[currow,curcol])
                                    rfvalsx.append(cur_array[currow,curcol])
                                else:
                                    rfvals.append(0.01)
                                    noofzero = noofzero + 1
                                cur_raster = 0
                                yearcounter = yearcounter + 1
                                
                            gammav = []
                            t = []
                            shapex = 0
                            loc = 0
                            scalex = 0
                            
                            shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                            #Probability of Zero
                            zeroprob = noofzero / len(rfvals)
                            
                            a = 0
                            g = 0
                            spiv = 0.0
                            while(a<len(rfvals)):
                                
                                if(rfvals[a]>=0):
                                    
                                    curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                    curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                    gammav.append(curvale)
                                    if(curvale<=0.5):
                                        g = (math.log(1/(curvale*curvale)))**0.5
                                        t.append(g)
                                        
                                        spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    else:
                                        g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                        t.append(g)
                                        
                                        spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                    
                                if(mask[currow][curcol]==1):
                                        megaarr[a][currow][curcol]  = spiv
                                else:
                                        megaarr[a][currow][curcol]  = None
                                    
                                    
                                
                                    
                                a = a + 1
                            ccc = ccc + 1
                        rcc = rcc + 1
                    
                    zz = yearbegin
                    while(zz<=yearend):
                        
                        originX = geotransform[0]
                        originY = geotransform[3]
                        pixelw = geotransform[1]
                        pixelh = geotransform[5]
                        driver = gdal.GetDriverByName("GTiff")
                        fn = outdir + "/spivals/12/SPI_" + str(zz)  + ".tif"
                        outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                        outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                        outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                        outRasterSRS = osr.SpatialReference()
                        outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                        outRaster.SetProjection(outRasterSRS.ExportToWkt())
                        outRaster.FlushCache()
                        
                        outRaster = 0
                        zz = zz + 1
                    self.dlg.progressBar.setValue(0)
                    t2 = datetime.now()
                    delta = t2 - t1
                    self.dlg.textEdit.append("\n\n12 month SPI values generated at \n" + outdir + "\\spivals\\12\\" + "\nFinished on : " + str(t2))
                    hrs = delta.seconds // 3600
                    mins = (delta.seconds - (3600*hrs)) // 60
                    secs = delta.seconds - (3600 * hrs) - (60*mins)
                    self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
            
                    
                    
                    
                    
                    
                    
                    
                    
                elif(ts==24):   
                    self.dlg.progressBar.setValue(0)
                    QApplication.processEvents()
                    t1 = datetime.now()
                    self.dlg.textEdit.append("\n\n24 month SPI values generation started on : " + str(t1) + "\n")
                    QApplication.processEvents()
                    if(os.path.exists(outdir + "/spivals/24") ==False):
                           os.mkdir(outdir + "/spivals/24/")
           
                    if(os.path.exists(outdir + "/spivals/24/Composite")==False):
                           os.mkdir(outdir + "/spivals/24/Composite")
                          
                    #Generate Composite files
                    
                    proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                    proc_valq = 0
                    
                    qwe = yearbegin
                    qwe2 = yearend
                    self.dlg.textEdit.append("\nComposite Generation Started...")
                    while(qwe<qwe2):
                        
                        cur_array1 = []
                        cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_1.tif")
                        cur_array1 = cur_raster1.ReadAsArray()
                        
                        cur_array2 = []
                        cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_2.tif")
                        cur_array2 = cur_raster2.ReadAsArray()
                        
                        cur_array3 = []
                        cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_3.tif")
                        cur_array3 = cur_raster3.ReadAsArray()
                        
                        cur_array4 = []
                        cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_4.tif")
                        cur_array4 = cur_raster4.ReadAsArray()
                        
                        cur_array5 = []
                        cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_5.tif")
                        cur_array5 = cur_raster5.ReadAsArray()
                        
                        cur_array6 = []
                        cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_6.tif")
                        cur_array6 = cur_raster6.ReadAsArray()
                        
                        cur_array7 = []
                        cur_raster7 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_7.tif")
                        cur_array7 = cur_raster7.ReadAsArray()
                        
                        cur_array8 = []
                        cur_raster8 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_8.tif")
                        cur_array8 = cur_raster8.ReadAsArray()
                        
                        cur_array9 = []
                        cur_raster9 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_9.tif")
                        cur_array9 = cur_raster9.ReadAsArray()
                        
                        cur_array10 = []
                        cur_raster10 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_10.tif")
                        cur_array10 = cur_raster10.ReadAsArray()
                        
                        cur_array11 = []
                        cur_raster11 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_11.tif")
                        cur_array11 = cur_raster11.ReadAsArray()
                        
                        cur_array12 = []
                        cur_raster12 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_12.tif")
                        cur_array12 = cur_raster12.ReadAsArray()
                        
                        cur_array13 = []
                        cur_raster13 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_1.tif")
                        cur_array13 = cur_raster13.ReadAsArray()
                        
                        cur_array14 = []
                        cur_raster14 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_2.tif")
                        cur_array14 = cur_raster14.ReadAsArray()
                        
                        cur_array15 = []
                        cur_raster15 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_3.tif")
                        cur_array15 = cur_raster15.ReadAsArray()
                        
                        cur_array16 = []
                        cur_raster16 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_4.tif")
                        cur_array16 = cur_raster16.ReadAsArray()
                        
                        cur_array17 = []
                        cur_raster17 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_5.tif")
                        cur_array17 = cur_raster17.ReadAsArray()
                        
                        cur_array18 = []
                        cur_raster18 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_6.tif")
                        cur_array18 = cur_raster18.ReadAsArray()
                        
                        cur_array19= []
                        cur_raster19 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_7.tif")
                        cur_array19 = cur_raster19.ReadAsArray()
                        
                        cur_array20 = []
                        cur_raster20 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_8.tif")
                        cur_array20 = cur_raster20.ReadAsArray()
                        
                        cur_array21 = []
                        cur_raster21 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_9.tif")
                        cur_array21 = cur_raster21.ReadAsArray()
                        
                        cur_array22 = []
                        cur_raster22 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_10.tif")
                        cur_array22 = cur_raster22.ReadAsArray()
                        
                        cur_array23 = []
                        cur_raster23 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_11.tif")
                        cur_array23 = cur_raster23.ReadAsArray()
                        
                        cur_array24 = []
                        cur_raster24 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_12.tif")
                        cur_array24 = cur_raster24.ReadAsArray()
                        
                        cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6 + cur_array7 + cur_array8 + cur_array9 + cur_array10 + cur_array11 + cur_array12 + cur_array13 + cur_array14 + cur_array15 + cur_array16 + cur_array17 + cur_array18 + cur_array19 + cur_array20 + cur_array21 + cur_array22 + cur_array23 + cur_array24)
                        geotransform = cur_raster1.GetGeoTransform()
                        rows = rasterinit.RasterYSize
                        cols = rasterinit.RasterXSize
                        
                        originX = geotransform[0]
                        originY = geotransform[3]
                        pixelw = geotransform[1]
                        pixelh = geotransform[5]
                        driver = gdal.GetDriverByName("GTiff")
                        fn = outdir + "/spivals/24/Composite/RF_" + str(qwe) + "_" + str(qwe+1)+ ".tif"
                        outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                        outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                        outRaster.GetRasterBand(1).WriteArray(cur_array)
                        outRasterSRS = osr.SpatialReference()
                        outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                        outRaster.SetProjection(outRasterSRS.ExportToWkt())
                        outRaster.FlushCache()
                        
                        outRaster = 0
                        
                        QApplication.processEvents()
                        proc_valq = proc_valq + proginc_q
                        
                        QApplication.processEvents()
                        self.dlg.progressBar.setValue(proc_valq)
                        QApplication.processEvents()
                        
                        
                    
                        
                        qwe = qwe + 1
           
                    
                    self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/24/Composite/" + "\n\nSPI calculation from the composites starts..." )
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    self.dlg.progressBar.setValue(0)
                    
                   
                    c0 = 2.515517
                    c1 = 0.802583
                    c2 = 0.010328
                    d1 = 1.4327888
                    d2 = 0.189269
                    d3 = 0.001308
                    showstatus = 1 #if status message is to be printed or not
                    finalvals = []
                    curyearwrite = yearbegin
                    
                    megaarr = []
                    xx = yearbegin
                    rasterinit = gdal.Open(fileslist[0])
                    geotransform = rasterinit.GetGeoTransform()
                    rows = rasterinit.RasterYSize
                    cols = rasterinit.RasterXSize
                    
                    
                    cur_add_arr = np.zeros((rows,cols))
                    while(xx<=yearend):
                        megaarr.append(cur_add_arr)
                        xx = xx + 1
                    megaarr = np.array(megaarr)
                    
                    cc = 0
                    rr = 0
                    pseudomat = []
                    while(rr<rows):
                        cc = 0
                        while(cc<cols):
                            pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                            cc = cc + 1
                        rr = rr + 1
                    pseudomat = np.array(pseudomat)
                    
                    rcc = 0 
                    ccc = 0
                    proc_inc = 100.000 / ((rows-1) * (cols-1))
                    proc_val = 0
                    while(rcc<rows):
                        ccc = 0
                        while(ccc<cols):
                            QApplication.processEvents()
                            proc_val = proc_val + proc_inc
                            
                            QApplication.processEvents()
                            self.dlg.progressBar.setValue(proc_val)
                            QApplication.processEvents()
                            currow = int(rcc)
                            curcol = int(ccc)
                            noofzero = 0
                            yearcounter = yearbegin
                            
                            rfvals = []
                            rfvalsx = []
                            
                            while(yearcounter<yearend):
                                
                                cur_array1 = []
                                
                                cur_raster1 = gdal.Open(outdir + "/spivals/24/Composite/RF_" + str(yearcounter) + "_"  + str(yearcounter+1)+ ".tif")
                                cur_array1 = cur_raster1.ReadAsArray()
                                
                                geotransform = cur_raster1.GetGeoTransform()
                                
                                
                                cur_array = (cur_array1) / 24
                                
                                if(cur_array[currow,curcol]>0):
                                    rfvals.append(cur_array[currow,curcol])
                                    rfvalsx.append(cur_array[currow,curcol])
                                else:
                                    rfvals.append(0.01)
                                    noofzero = noofzero + 1
                                cur_raster = 0
                                yearcounter = yearcounter + 1
                                
                            gammav = []
                            t = []
                            shapex = 0
                            loc = 0
                            scalex = 0
                            
                            shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                            #Probability of Zero
                            zeroprob = noofzero / len(rfvals)
                            
                            a = 0
                            g = 0
                            spiv = 0.0
                            while(a<len(rfvals)):
                                
                                if(rfvals[a]>=0):
                                    
                                    curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                    curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                    gammav.append(curvale)
                                    if(curvale<=0.5):
                                        g = (math.log(1/(curvale*curvale)))**0.5
                                        t.append(g)
                                        
                                        spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    else:
                                        g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                        t.append(g)
                                        
                                        spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                    
                                if(mask[currow][curcol]==1):
                                        megaarr[a][currow][curcol]  = spiv
                                else:
                                        megaarr[a][currow][curcol]  = None
                                    
                                    
                                
                                    
                                a = a + 1
                            ccc = ccc + 1
                        rcc = rcc + 1
                    
                    zz = yearbegin
                    while(zz<=yearend):
                        
                        originX = geotransform[0]
                        originY = geotransform[3]
                        pixelw = geotransform[1]
                        pixelh = geotransform[5]
                        driver = gdal.GetDriverByName("GTiff")
                        fn = outdir + "/spivals/24/SPI_" + str(zz) + "_" + str(zz+1) + ".tif"
                        outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                        outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                        outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                        outRasterSRS = osr.SpatialReference()
                        outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                        outRaster.SetProjection(outRasterSRS.ExportToWkt())
                        outRaster.FlushCache()
                        
                        outRaster = 0
                        zz = zz + 1
                    self.dlg.progressBar.setValue(0)
                    t2 = datetime.now()
                    delta = t2 - t1
                    self.dlg.textEdit.append("\n\n24 month SPI values generated at \n" + outdir + "\\spivals\\24\\" + "\nFinished on : " + str(t2))
                    hrs = delta.seconds // 3600
                    mins = (delta.seconds - (3600*hrs)) // 60
                    secs = delta.seconds - (3600 * hrs) - (60*mins)
                    self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
            
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                elif(ts==36):   
                    self.dlg.progressBar.setValue(0)
                    QApplication.processEvents()
                    t1 = datetime.now()
                    self.dlg.textEdit.append("\n\n36 month SPI values generation started on : " + str(t1) + "\n")
                    QApplication.processEvents()
                    if(os.path.exists(outdir + "/spivals/36") ==False):
                           os.mkdir(outdir + "/spivals/36/")
           
                    if(os.path.exists(outdir + "/spivals/36/Composite")==False):
                           os.mkdir(outdir + "/spivals/36/Composite")
                          
                    #Generate Composite files
                    
                    proginc_q = 100.00 / (int(yearend)-int(yearbegin)) 
                    proc_valq = 0
                    
                    qwe = yearbegin
                    qwe2 = yearend
                    self.dlg.textEdit.append("\nComposite Generation Started...")
                    while(qwe<(qwe2-1)):
                        
                        cur_array1 = []
                        cur_raster1 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_1.tif")
                        cur_array1 = cur_raster1.ReadAsArray()
                        
                        cur_array2 = []
                        cur_raster2 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_2.tif")
                        cur_array2 = cur_raster2.ReadAsArray()
                        
                        cur_array3 = []
                        cur_raster3 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_3.tif")
                        cur_array3 = cur_raster3.ReadAsArray()
                        
                        cur_array4 = []
                        cur_raster4 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_4.tif")
                        cur_array4 = cur_raster4.ReadAsArray()
                        
                        cur_array5 = []
                        cur_raster5 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_5.tif")
                        cur_array5 = cur_raster5.ReadAsArray()
                        
                        cur_array6 = []
                        cur_raster6 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_6.tif")
                        cur_array6 = cur_raster6.ReadAsArray()
                        
                        cur_array7 = []
                        cur_raster7 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_7.tif")
                        cur_array7 = cur_raster7.ReadAsArray()
                        
                        cur_array8 = []
                        cur_raster8 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_8.tif")
                        cur_array8 = cur_raster8.ReadAsArray()
                        
                        cur_array9 = []
                        cur_raster9 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_9.tif")
                        cur_array9 = cur_raster9.ReadAsArray()
                        
                        cur_array10 = []
                        cur_raster10 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_10.tif")
                        cur_array10 = cur_raster10.ReadAsArray()
                        
                        cur_array11 = []
                        cur_raster11 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_11.tif")
                        cur_array11 = cur_raster11.ReadAsArray()
                        
                        cur_array12 = []
                        cur_raster12 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe) + "_12.tif")
                        cur_array12 = cur_raster12.ReadAsArray()
                        
                        cur_array13 = []
                        cur_raster13 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_1.tif")
                        cur_array13 = cur_raster13.ReadAsArray()
                        
                        cur_array14 = []
                        cur_raster14 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_2.tif")
                        cur_array14 = cur_raster14.ReadAsArray()
                        
                        cur_array15 = []
                        cur_raster15 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_3.tif")
                        cur_array15 = cur_raster15.ReadAsArray()
                        
                        cur_array16 = []
                        cur_raster16 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_4.tif")
                        cur_array16 = cur_raster16.ReadAsArray()
                        
                        cur_array17 = []
                        cur_raster17 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_5.tif")
                        cur_array17 = cur_raster17.ReadAsArray()
                        
                        cur_array18 = []
                        cur_raster18 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_6.tif")
                        cur_array18 = cur_raster18.ReadAsArray()
                        
                        cur_array19= []
                        cur_raster19 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_7.tif")
                        cur_array19 = cur_raster19.ReadAsArray()
                        
                        cur_array20 = []
                        cur_raster20 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_8.tif")
                        cur_array20 = cur_raster20.ReadAsArray()
                        
                        cur_array21 = []
                        cur_raster21 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_9.tif")
                        cur_array21 = cur_raster21.ReadAsArray()
                        
                        cur_array22 = []
                        cur_raster22 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_10.tif")
                        cur_array22 = cur_raster22.ReadAsArray()
                        
                        cur_array23 = []
                        cur_raster23 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_11.tif")
                        cur_array23 = cur_raster23.ReadAsArray()
                        
                        cur_array24 = []
                        cur_raster24 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+1) + "_12.tif")
                        cur_array24 = cur_raster24.ReadAsArray()
                        
                        cur_array25 = []
                        cur_raster25 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+2) + "_1.tif")
                        cur_array25 = cur_raster25.ReadAsArray()
                        
                        cur_array26 = []
                        cur_raster26 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+2) + "_2.tif")
                        cur_array26 = cur_raster26.ReadAsArray()
                        
                        cur_array27 = []
                        cur_raster27 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+2) + "_3.tif")
                        cur_array27 = cur_raster27.ReadAsArray()
                        
                        cur_array28 = []
                        cur_raster28 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+2) + "_4.tif")
                        cur_array28 = cur_raster28.ReadAsArray()
                        
                        cur_array29 = []
                        cur_raster29 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+2) + "_5.tif")
                        cur_array29= cur_raster29.ReadAsArray()
                        
                        cur_array30 = []
                        cur_raster30 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+2) + "_6.tif")
                        cur_array30 = cur_raster30.ReadAsArray()
                        
                        cur_array31 = []
                        cur_raster31 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+2) + "_7.tif")
                        cur_array31 = cur_raster31.ReadAsArray()
                        
                        cur_array32 = []
                        cur_raster32 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+2) + "_8.tif")
                        cur_array32 = cur_raster32.ReadAsArray()
                        
                        cur_array33 = []
                        cur_raster33 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+2) + "_9.tif")
                        cur_array33 = cur_raster33.ReadAsArray()
                        
                        cur_array34 = []
                        cur_raster34 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+2) + "_10.tif")
                        cur_array34 = cur_raster34.ReadAsArray()
                        
                        cur_array35 = []
                        cur_raster35 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+2) + "_11.tif")
                        cur_array35 = cur_raster35.ReadAsArray()
                        
                        cur_array36 = []
                        cur_raster36 = gdal.Open(str(outdir_c) + "/RF_" + str(qwe+2) + "_12.tif")
                        cur_array36 = cur_raster36.ReadAsArray()
                        
                        cur_array = (cur_array1 + cur_array2 + cur_array3 + cur_array4 + cur_array5 + cur_array6 + cur_array7 + cur_array8 + cur_array9 + cur_array10 + cur_array11 + cur_array12 + cur_array13 + cur_array14 + cur_array15 + cur_array16 + cur_array17 + cur_array18 + cur_array19 + cur_array20 + cur_array21 + cur_array22 + cur_array23 + cur_array24 + cur_array25 + cur_array26 + cur_array27 + cur_array28 + cur_array29 + cur_array30 + cur_array31 + cur_array32 + cur_array33 + cur_array34 + cur_array35 + cur_array36)
                                
                        
                        geotransform = cur_raster1.GetGeoTransform()
                        rows = rasterinit.RasterYSize
                        cols = rasterinit.RasterXSize
                        
                        originX = geotransform[0]
                        originY = geotransform[3]
                        pixelw = geotransform[1]
                        pixelh = geotransform[5]
                        driver = gdal.GetDriverByName("GTiff")
                        fn = outdir + "/spivals/36/Composite/RF_" + str(qwe) + "_" + str(qwe+1)+ "_" + str(qwe+2)+ ".tif"
                        outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                        outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                        outRaster.GetRasterBand(1).WriteArray(cur_array)
                        outRasterSRS = osr.SpatialReference()
                        outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                        outRaster.SetProjection(outRasterSRS.ExportToWkt())
                        outRaster.FlushCache()
                        
                        outRaster = 0
                        
                        QApplication.processEvents()
                        proc_valq = proc_valq + proginc_q
                        
                        QApplication.processEvents()
                        self.dlg.progressBar.setValue(proc_valq)
                        QApplication.processEvents()
                        
                        
                    
                        
                        qwe = qwe + 1
           
                    
                    self.dlg.textEdit.append("\nGenerated composites stored at " + str(outdir) + "/spivals/36/Composite/" + "\n\nSPI calculation from the composites starts..." )
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    self.dlg.progressBar.setValue(0)
                    
                   
                    c0 = 2.515517
                    c1 = 0.802583
                    c2 = 0.010328
                    d1 = 1.4327888
                    d2 = 0.189269
                    d3 = 0.001308
                    showstatus = 1 #if status message is to be printed or not
                    finalvals = []
                    curyearwrite = yearbegin
                    
                    megaarr = []
                    xx = yearbegin
                    rasterinit = gdal.Open(fileslist[0])
                    geotransform = rasterinit.GetGeoTransform()
                    rows = rasterinit.RasterYSize
                    cols = rasterinit.RasterXSize
                    
                    
                    cur_add_arr = np.zeros((rows,cols))
                    while(xx<=yearend):
                        megaarr.append(cur_add_arr)
                        xx = xx + 1
                    megaarr = np.array(megaarr)
                    
                    cc = 0
                    rr = 0
                    pseudomat = []
                    while(rr<rows):
                        cc = 0
                        while(cc<cols):
                            pseudomat.append(float(str(rr)+"."+str(cc)+"1"))
                            cc = cc + 1
                        rr = rr + 1
                    pseudomat = np.array(pseudomat)
                    
                    rcc = 0 
                    ccc = 0
                    proc_inc = 100.000 / ((rows-1) * (cols-1))
                    proc_val = 0
                    while(rcc<rows):
                        ccc = 0
                        while(ccc<cols):
                            QApplication.processEvents()
                            proc_val = proc_val + proc_inc
                            
                            QApplication.processEvents()
                            self.dlg.progressBar.setValue(proc_val)
                            QApplication.processEvents()
                            currow = int(rcc)
                            curcol = int(ccc)
                            noofzero = 0
                            yearcounter = yearbegin
                            
                            rfvals = []
                            rfvalsx = []
                            
                            while(yearcounter<(yearend-1)):
                                
                                cur_array1 = []
                                
                                cur_raster1 = gdal.Open(outdir + "/spivals/36/Composite/RF_" + str(yearcounter) + "_"  + str(yearcounter+1) + "_"  + str(yearcounter+2) + ".tif")
                                cur_array1 = cur_raster1.ReadAsArray()
                                
                                geotransform = cur_raster1.GetGeoTransform()
                                
                                
                                cur_array = (cur_array1) / 36
                                
                                if(cur_array[currow,curcol]>0):
                                    rfvals.append(cur_array[currow,curcol])
                                    rfvalsx.append(cur_array[currow,curcol])
                                else:
                                    rfvals.append(0.01)
                                    noofzero = noofzero + 1
                                cur_raster = 0
                                yearcounter = yearcounter + 1
                                
                            gammav = []
                            t = []
                            shapex = 0
                            loc = 0
                            scalex = 0
                            
                            shapex, loc, scalex = gamma.fit(rfvalsx, floc=0)
                            #Probability of Zero
                            zeroprob = noofzero / len(rfvals)
                            
                            a = 0
                            g = 0
                            spiv = 0.0
                            while(a<len(rfvals)):
                                
                                if(rfvals[a]>=0):
                                    
                                    curvale = gamma.cdf(rfvals[a],shapex, scale = scalex)
                                    curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                    gammav.append(curvale)
                                    if(curvale<=0.5):
                                        g = (math.log(1/(curvale*curvale)))**0.5
                                        t.append(g)
                                        
                                        spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    else:
                                        g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                        t.append(g)
                                        
                                        spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                    
                                if(mask[currow][curcol]==1):
                                        megaarr[a][currow][curcol]  = spiv
                                else:
                                        megaarr[a][currow][curcol]  = None
                                    
                                    
                                
                                    
                                a = a + 1
                            ccc = ccc + 1
                        rcc = rcc + 1
                    
                    zz = yearbegin
                    while(zz<=yearend):
                        
                        originX = geotransform[0]
                        originY = geotransform[3]
                        pixelw = geotransform[1]
                        pixelh = geotransform[5]
                        driver = gdal.GetDriverByName("GTiff")
                        fn = outdir + "/spivals/36/SPI_" + str(zz) + "_" + str(zz+1) + "_" + str(zz+2) + ".tif"
                        outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                        outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                        outRaster.GetRasterBand(1).WriteArray(megaarr[zz-yearbegin])
                        outRasterSRS = osr.SpatialReference()
                        outRasterSRS.ImportFromWkt(rasterinit.GetProjectionRef())
                        outRaster.SetProjection(outRasterSRS.ExportToWkt())
                        outRaster.FlushCache()
                        
                        outRaster = 0
                        zz = zz + 1
                    self.dlg.progressBar.setValue(0)
                    t2 = datetime.now()
                    delta = t2 - t1
                    self.dlg.textEdit.append("\n\n36 month SPI values generated at \n" + outdir + "\\spivals\\36\\" + "\nFinished on : " + str(t2))
                    hrs = delta.seconds // 3600
                    mins = (delta.seconds - (3600*hrs)) // 60
                    secs = delta.seconds - (3600 * hrs) - (60*mins)
                    self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
            
                    
                    
                    
                    
                    
                    
                    
                    
        self.dlg.pushButton_3.setEnabled(True)
        self.dlg.pushButton.setEnabled(True)
        self.dlg.pushButton1.setEnabled(True)
        self.dlg.pushButton_2.setEnabled(True)
        self.dlg.pushButton_4.setEnabled(False)
        self.dlg.pushButton_9.setEnabled(True)
        self.dlg.pushButton_10.setEnabled(True)
        self.dlg.pushButton_6.setEnabled(True)
        self.dlg.pushButton_7.setEnabled(True)
        self.dlg.pushButton_5.setEnabled(True)
         
    def getfilename2(self):
        dlgx = QFileDialog()
        dlgx.setFileMode(QFileDialog.Directory)
        
        
        if dlgx.exec_():
            filenames = dlgx.selectedFiles()
            self.dlg.lineEdit_6.setText(str(filenames[0]))

        outpath = self.dlg.lineEdit_6.text()
        if(os.path.exists(outpath)==False):
            self.dlg.textEdit.append("\nOutput folder not found.")
    
    def getfilename(self):
        dlgx = QFileDialog()
        dlgx.setFileMode(QFileDialog.Directory)
        
        
        if dlgx.exec_():
            filenames = dlgx.selectedFiles()
            self.dlg.lineEdit_5.setText(str(filenames[0]))

        filepath = self.dlg.lineEdit_5.text()
        fileslista = glob.glob(filepath + "\*.tif")
        spitext = fileslista[0][(len(filepath)+1):]
        spitext = spitext[:3]
        
        if(len(fileslista)==0):
            self.dlg.textEdit.append("\nNo supported files found in the directory!!!")
            
        elif(spitext!='SPI'):
            self.dlg.textEdit.append("\nInput files are not generated by this plugin.")
        
        else:
            self.dlg.comboBox_4.clear()
            self.dlg.comboBox_5.clear()
            #first files year count
            yearb = fileslista[0][(len(filepath)+1):]
            yeare = fileslista[len(fileslista)-1][(len(filepath)+1):]
            
            yearb = yearb[4:8]
            
            yeare = yeare[4:8]
            
            x = int(yearb)
            
            y = int(yeare)
            while(x<=y):
                self.dlg.comboBox_4.addItem(str(x))
                self.dlg.comboBox_5.addItem(str(x))
                x = x + 1
            
             
            self.dlg.pushButton_5.setEnabled(True)
    
    def getfilename_t(self):
        filepath = self.dlg.lineEdit_5.text()
        self.dlg.comboBox_4.clear()
        self.dlg.comboBox_5.clear()
        fileslista = glob.glob(filepath + "\*.tif")
        spitext = fileslista[0][(len(filepath)+1):]
        spitext = spitext[:3]
        
        if(len(fileslista)==0):
            self.dlg.textEdit.append("\nNo supported files found in the directory!!!")
            
        elif(spitext!='SPI'):
            self.dlg.textEdit.append("\nInput files are not generated by this plugin.")
        
        else:
            self.dlg.comboBox_4.clear()
            self.dlg.comboBox_5.clear()
            #first files year count
            yearb = fileslista[0][(len(filepath)+1):]
            yeare = fileslista[len(fileslista)-1][(len(filepath)+1):]
            
            yearb = yearb[4:8]
            
            yeare = yeare[4:8]
            
            x = int(yearb)
            
            y = int(yeare)
            while(x<=y):
                self.dlg.comboBox_4.addItem(str(x))
                self.dlg.comboBox_5.addItem(str(x))
                x = x + 1
            
            
            self.dlg.pushButton_5.setEnabled(True) 
    
    def classify(self):
        self.dlg.show()
        w = QWidget()
        messagee = 'Continue analysis with the provided parameters? '
        reply = QMessageBox.question(w, 'Continue?',messagee, QMessageBox.Yes, QMessageBox.No)
        self.dlg.show()
        if reply == QMessageBox.Yes:
        
            self.dlg.pushButton_3.setEnabled(False)
            self.dlg.pushButton.setEnabled(False)
            self.dlg.pushButton1.setEnabled(False)
            self.dlg.pushButton_2.setEnabled(False)
            self.dlg.pushButton_4.setEnabled(False)
            self.dlg.pushButton_9.setEnabled(False)
            self.dlg.pushButton_10.setEnabled(False)
            self.dlg.pushButton_6.setEnabled(False)
            self.dlg.pushButton_7.setEnabled(False)
            self.dlg.pushButton_5.setEnabled(False)
            currange = []
            ranges = []
            crows = self.dlg.tableWidget.rowCount()
            
            anyerror = 0
            xy = 0
            while(xy<crows):
                currange = []
                namev = self.dlg.tableWidget.item(xy, 0)
                lval = self.dlg.tableWidget.item(xy, 2)
                hval = self.dlg.tableWidget.item(xy, 1)
                if((namev is None) == False):
                    if(float(hval.text())>=float(lval.text())):
                        if(namev.text() != ''):
                            currange.append(float(hval.text()))
                            currange.append(float(lval.text()))
                            currange.append(namev.text())
                            ranges.append(currange)
                        
                    else:
                        
                        self.dlg.textEdit.append("Error in row : " + str(xy + 1) + " : Upper Limit should be greater than Lower Limit.")
                        anyerror = 1
                xy = xy + 1
                
            if(anyerror ==1):
                self.dlg.textEdit.append("\nOne or more errors are found. Can not Classify.")
            
            else:
                t1 = datetime.now()
                outpath = self.dlg.lineEdit_6.text()
                filepath = self.dlg.lineEdit_5.text()
                fileslistx = glob.glob(filepath + "\*.tif")
                
                
                
                anals = self.dlg.comboBox_4.currentIndex()
                anale = self.dlg.comboBox_5.currentIndex()
                
                fileslista = fileslistx[anals:(anale+1)]
                
                progval = 0.0
                proginc = 100.0 / (len(ranges) * 2)
                
                
                
                cur_raster = gdal.Open(fileslista[0])
                rows = cur_raster.RasterYSize
                cols = cur_raster.RasterXSize
                
                cur_raster = 0
                
                cat = 0
                while(cat<len(ranges)):
            
                    result = np.zeros((rows,cols))
                    result_cur = np.zeros((rows,cols))
                    a = 0
                    while(a<len(fileslista)):
                        result_cur = np.zeros((rows,cols))
                        cur_raster = gdal.Open(fileslista[a])
                        cur_array1 = cur_raster.ReadAsArray()
                        cur_arr = np.array(cur_array1)
                        
                        rows = cur_raster.RasterYSize
                        cols = cur_raster.RasterXSize
                        r = 0
                        c = 0
                        while(r<rows):
                            c = 0
                            while(c<cols):
                                
                                if((cur_arr[r][c]>=ranges[cat][1]) and (cur_arr[r][c]<=ranges[cat][0])):
                                    
                                    result_cur[r][c] = 1
                                    
                                else:
                                    
                                    result_cur[r][c] = 0
                                        
                                c = c + 1
                            r = r + 1
                        
                        
                        result = result + result_cur
                        
                        
                        cur_raster = 0
                        a = a + 1
                        
                    resultx = np.array(result)
                    prob = resultx / len(fileslista)
                    #result = np.where(result>=0, result, None)
                    
                    cur_raster = gdal.Open(fileslista[0])
                    geotransform = cur_raster.GetGeoTransform()
                    originX = geotransform[0]
                    originY = geotransform[3]
                    pixelw = geotransform[1]
                    pixelh = geotransform[5]
                    
                    driver = gdal.GetDriverByName("GTiff")
                    fn = outpath + "/c_" + str(ranges[cat][2]) + ".tif"
                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                    outRaster.GetRasterBand(1).WriteArray(result)
                    outRasterSRS = osr.SpatialReference()
                    outRasterSRS.ImportFromWkt(cur_raster.GetProjectionRef())
                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                    outRaster.FlushCache()
                    outRaster = 0
                    cur_raster = 0
                    self.dlg.textEdit.append("Count file " + str(fn) + " Generated!!!")
                    
                    progval = progval + proginc
                    self.dlg.progressBar.setValue(progval)
                    QApplication.processEvents()
                    
                    cur_raster = gdal.Open(fileslista[0])
                    geotransform = cur_raster.GetGeoTransform()
                    originX = geotransform[0]
                    originY = geotransform[3]
                    pixelw = geotransform[1]
                    pixelh = geotransform[5]
                    
                    driver = gdal.GetDriverByName("GTiff")
                    fn = outpath + "/p_" + str(ranges[cat][2]) + ".tif"
                    outRaster = driver.Create(fn, cols,rows, 1 , gdal.GDT_Float32,)
                    outRaster.SetGeoTransform((originX, pixelw, 0, originY, 0, pixelh))
                    outRaster.GetRasterBand(1).WriteArray(prob)
                    outRasterSRS = osr.SpatialReference()
                    outRasterSRS.ImportFromWkt(cur_raster.GetProjectionRef())
                    outRaster.SetProjection(outRasterSRS.ExportToWkt())
                    outRaster.FlushCache()
                    outRaster = 0
                    cur_raster = 0
                    self.dlg.textEdit.append("Probability file " + str(fn) + " Generated!!!")
                    
                    progval = progval + proginc
                    self.dlg.progressBar.setValue(progval)
                    QApplication.processEvents()
                    cat = cat + 1
                
                t2 = datetime.now()
                delta = t2 - t1
                hrs = delta.seconds // 3600
                mins = (delta.seconds - (3600*hrs)) // 60
                secs = delta.seconds - (3600 * hrs) - (60*mins)
                self.dlg.textEdit.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
            
                self.dlg.progressBar.setValue(0)
                QApplication.processEvents()
                self.dlg.pushButton_3.setEnabled(True)
                self.dlg.pushButton.setEnabled(True)
                self.dlg.pushButton1.setEnabled(True)
                self.dlg.pushButton_2.setEnabled(True)
                self.dlg.pushButton_4.setEnabled(False)
                self.dlg.pushButton_9.setEnabled(True)
                self.dlg.pushButton_10.setEnabled(True)
                self.dlg.pushButton_6.setEnabled(True)
                self.dlg.pushButton_7.setEnabled(True)
                self.dlg.pushButton_5.setEnabled(True)        
          
        
           
           
        
        
    def unload(self):
        
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&SPI Utility'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
    
    def getinput(self):
        
        dlgx = QFileDialog()
        dlgx.setFileMode(QFileDialog.Directory)
        
        
        if dlgx.exec_():
            filenames = dlgx.selectedFiles()
            self.dlg.lineEdit.setText(str(filenames[0]))
            
        fileslistq = glob.glob(str(filenames[0]) + "\*.tif")
        if(len(fileslistq)>0):
            aaaa = str(fileslistq[0])
            startyr_d = aaaa[-8:][0:4]
            aaab = str(fileslistq[len(fileslistq)-1])
            endyr_d = aaab[-8:][0:4]
           
        
        try:
            ww = int(startyr_d)
            tt = int(endyr_d)
            self.dlg.lineEdit_3.setText(str(startyr_d))
            self.dlg.lineEdit_4.setText(str(endyr_d))
        except:
            self.dlg.lineEdit_3.setText("")
            self.dlg.lineEdit_4.setText("")
    
    def getinput_tt(self):
        filenames = self.dlg.lineEdit.text()
        fileslistq = glob.glob(str(filenames) + "\*.tif")
        if(len(fileslistq)>0):
            aaaa = str(fileslistq[0])
            startyr_d = aaaa[-8:][0:4]
            aaab = str(fileslistq[len(fileslistq)-1])
            endyr_d = aaab[-8:][0:4]
           
        
        try:
            ww = int(startyr_d)
            tt = int(endyr_d)
            self.dlg.lineEdit_3.setText(str(startyr_d))
            self.dlg.lineEdit_4.setText(str(endyr_d))
        except:
            self.dlg.lineEdit_3.setText("")
            self.dlg.lineEdit_4.setText("")
        
        
    def getinput1(self):
        
        dlgx = QFileDialog()
        dlgx.setFileMode(QFileDialog.Directory)
        
        
        if dlgx.exec_():
            filenames = dlgx.selectedFiles()
            self.dlg.lineEdit_7.setText(str(filenames[0]))
    
    def getinput2(self):
        
        dlgx = QFileDialog()
        dlgx.setFileMode(QFileDialog.Directory)
        
        
        if dlgx.exec_():
            filenames = dlgx.selectedFiles()
            self.dlg.lineEdit_8.setText(str(filenames[0]))
            
        
    def getoutput(self):
        
        dlgx = QFileDialog()
        dlgx.setFileMode(QFileDialog.Directory)
        
        
        if dlgx.exec_():
            filenames = dlgx.selectedFiles()
            self.dlg.lineEdit_2.setText(str(filenames[0]))
    
    def getoutput1(self):
        
        dlgx = QFileDialog()
        dlgx.setFileMode(QFileDialog.Directory)
        
        
        if dlgx.exec_():
            filenames = dlgx.selectedFiles()
            self.dlg2.lineEdit_11.setText(str(filenames[0]))
            
    def getcsvfolder(self):
        dlgx = QFileDialog()
        dlgx.setFileMode(QFileDialog.AnyFile)
        dlgx.setFilter("CSV files (*.csv)")
        
        
        if dlgx.exec_():
            filenames = dlgx.selectedFiles()
            self.dlg2.lineEdit_10.setText(str(filenames[0]))
            
            
    def test(self):
        outdir = self.dlg.label_16.text()
        
        
        fileslist = glob.glob(outdir + "\Composite\*.tif")
        rasterinit = gdal.Open(fileslist[0])
                
        rows = rasterinit.RasterYSize
        cols = rasterinit.RasterXSize
                
                
                
        proc_inc = 100.0 / ((rows-1) * (cols-1))
        self.dlg.textEdit.append(str(proc_inc) + " " + str(rows) + " " + str(cols))
    
    def checkcsv(self):
        fields = []
        rows = []
        csvpath = self.dlg2.lineEdit_10.text()
        outpath = self.dlg2.lineEdit_11.text()
        errorx = 0
        if(csvpath == ""):
            errorx = 1
        if(outpath == ""):
            errorx = 1
        if(errorx == 0 ):
            self.dlg2.textEdit_1.append(str(csvpath))
            csvreader = open(csvpath)
            row = list(csvreader.readlines())
            self.dlg2.textEdit_1.append("CSV loaded. Total number of rows : " + str(len(row)))
            list_of_fields = row[0].split(",")
            no_of_fields = len(list_of_fields) - 1
            self.dlg2.textEdit_1.append("Number of points : " + str(no_of_fields))
            self.dlg2.label_8.setText(str(no_of_fields))
            self.dlg2.label_3.setText(csvpath)
            self.dlg2.label_4.setText(outpath)
            #-----Making List of values and putting them in a table tableWidget---------------------------------
            ss = 1
            fields.append("Date")
            while(ss<=no_of_fields):
                fields.append("Point " + str(ss))
                ss = ss + 1
            self.dlg2.tableWidget.setColumnCount(no_of_fields + 1)
            self.dlg2.tableWidget.setRowCount(len(row))
            self.dlg2.tableWidget.setHorizontalHeaderLabels(fields)
            roww = 0
            while(roww<len(row)):
                self.dlg2.tableWidget.setItem(roww, 0, QTableWidgetItem(row[roww].split(",")[0]))
                aa=1
                while(aa<=no_of_fields):
                    self.dlg2.tableWidget.setItem(roww, aa, QTableWidgetItem(row[roww].split(",")[aa]))
                    aa = aa + 1
                roww = roww + 1
            self.dlg2.pushButton.setEnabled(True)
            #------------------------------------------------------------
            
            
        else:
            
            self.dlg2.textEdit_1.append("Input CSV file and Output folder can not be empty!")
            
        
    
    
    def compositepoint(self):
        t1 = datetime.now()
        self.dlg2.pushButton_13.setEnabled(False)
        self.dlg2.pushButton_11.setEnabled(False)
        self.dlg2.pushButton_12.setEnabled(False)
        self.dlg2.pushButton.setEnabled(False)
        self.dlg2.pushButton_9.setEnabled(False)
        self.dlg2.pushButton_10.setEnabled(False)
        self.dlg2.pushButton_3.setEnabled(False)
        
        csvpath = self.dlg2.label_3.text()
        outpath = self.dlg2.label_4.text()
        
        csvreader = open(csvpath)
        row = list(csvreader.readlines())
        
        list_of_fields = row[0].split(",")
        no_of_fields = len(list_of_fields) - 1
        
        fields = []
        
        #-----Making List of values and putting them in a table tableWidget---------------------------------
        ss = 1
        fields.append("Date")
        while(ss<=no_of_fields):
            fields.append("Point " + str(ss))
            ss = ss + 1
            
        #------Check if all dates are available----------------------------------------
        
           
            
            
            
            
        #-----Monthly Composite--------------------------------------------------------
        
        #lets calc composite for the first point
        ss = 0
        colum = 1 #this will be iterated
        datex = []
        val=[]
        while(ss<len(row)):
            datex.append(row[ss].split(",")[0])
            val.append(row[ss].split(",")[colum]) 
            ss = ss + 1
        
        #get start and end date--------------------------------------------------------
        start_d = int(datex[0].split("-")[0])    
        start_m = int(datex[0].split("-")[1]) 
        start_y = int(datex[0].split("-")[2]) 
        
        end_d = int(datex[len(datex)-1].split("-")[0])    
        end_m = int(datex[len(datex)-1].split("-")[1]) 
        end_y = int(datex[len(datex)-1].split("-")[2]) 
        
        startdate = date(start_y, start_m, start_d)
        enddate = date(end_y, end_m, end_d)
        
        
        delta = enddate - startdate
        
        
        if(delta.days != len(row) - 1):
            self.dlg2.textEdit_1.append("\nIncomplete Data")
        else:
            self.dlg2.textEdit_1.append("\nComplete Data Available. Generating Composites...")
        
        
            #start getting composites------------------------------------------------------
            #get unique values of month-year
            prog_inc = 100.0/ ((end_y - start_y + 1) * 12)
            self.dlg2.progressBar_1.setValue(0)
            prog = 0
            x = start_y
            finalres = []
            while(x<=end_y):
                
                mc = 1
                while(mc<=12):
                    indexlist = []
                    vals = []
                    a = []
                    c = 0
                    while(c<len(datex)):
                        f = datex[c]
                        if(int(f.split("-")[1]) == int(mc) and int(f.split("-")[2])==int(x)):
                            a = []
                            indexlist.append(c)
                            y = 1
                            while(y<=no_of_fields):
                                if(row[c].split(",")[y][-1] == '\n'):
                                    
                                    a.append(float(row[c].split(",")[y][:len(row[c].split(",")[y])-1]))
                                else:
                                    
                                    a.append(float(row[c].split(",")[y]))
                                
                                y = y + 1
                            vals.append(a)
                        c = c + 1
                    sumv = vals[0]
                    sumv = np.array(sumv)
                    z = 1
                    while(z<len(vals)):
                        sumv = sumv + np.array(vals[z])
                        
                        z = z + 1
                        
                    tempvals = [str(mc)+"-"+str(x)]
                    for t in sumv:
                        tempvals.append(t)
                    
                    QApplication.processEvents()
                    finalres.append(tempvals)
                    prog = prog + prog_inc
                    self.dlg2.progressBar_1.setValue(prog)
                    QApplication.processEvents()
                    
                    
                    
                    
                    
                    
                    mc = mc + 1
                
                x =x + 1 
            
            rowcount = len(finalres)
            colcount = len(finalres[0])
            
            fieldx = ['Month']
            ccv = 1
            while(ccv<colcount):
                fieldx.append("Point " + str(ccv))
                ccv = ccv + 1
            self.dlg2.tableWidget_2.setColumnCount(colcount)
            self.dlg2.tableWidget_2.setRowCount(rowcount)
            self.dlg2.tableWidget_2.setHorizontalHeaderLabels(fieldx)
            outmonth = os.path.join(outpath, "Composite.csv")
            ff = open(outmonth, "w")
            ffc = 0
            while(ffc<len(finalres)):
                wstr = ""
                lp = 0
                while(lp<len(finalres[ffc])):
                    wstr = wstr + str(finalres[ffc][lp]) + ","
                    self.dlg2.tableWidget_2.setItem(ffc, lp, QTableWidgetItem(str(finalres[ffc][lp])))
                    lp = lp + 1
                ff.write(wstr[:len(wstr)-1] + "\n")
                ffc = ffc + 1
            ff.close()
            self.dlg2.progressBar_1.setValue(0)
            t2 = datetime.now()
            delta = t2 - t1
            hrs = delta.seconds // 3600
            mins = (delta.seconds - (3600*hrs)) // 60
            secs = delta.seconds - (3600 * hrs) - (60*mins)
            self.dlg2.textEdit_1.append("\nComposites Generated." +"\n")
            self.dlg2.textEdit_1.append("\nTime elapsed : " + str(hrs) + " hours " + str(mins)+ " minutes "+ str(secs) + " seconds" +"\n")
            self.dlg2.lineEdit_15.setText(str(outmonth))
            self.dlg2.lineEdit_16.setText(str(outpath))
            self.dlg2.tabWidget.setCurrentIndex(1)
            self.dlg2.label_9.setText(str(start_y))
            self.dlg2.label_10.setText(str(end_y))
            
            self.dlg2.label_13.setText(str(csvpath))
            self.dlg2.label_14.setText(str(outpath))
            self.dlg2.comboBox.addItem("Composite")
            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
            entry_is_there = False
            for c in AllItems:
                if(c=='Composite'):
                    entry_is_there = True
                else:
                    entry_is_there = False
            if(entry_is_there == False):
                self.dlg2.comboBox.addItem("Composite")
            
        
        
        self.dlg2.pushButton_13.setEnabled(True)
        self.dlg2.pushButton_11.setEnabled(True)
        self.dlg2.pushButton_12.setEnabled(True)
        self.dlg2.pushButton.setEnabled(True)
        self.dlg2.pushButton_9.setEnabled(True)
        self.dlg2.pushButton_10.setEnabled(True)
        self.dlg2.pushButton_3.setEnabled(True)
        
        
    def compositefileinput(self):
        dlgx = QFileDialog()
        dlgx.setFileMode(QFileDialog.AnyFile)
        dlgx.setFilter("CSV files (*.csv)")
        
        
        if dlgx.exec_():
            filenames = dlgx.selectedFiles()
            self.dlg2.lineEdit_15.setText(str(filenames[0]))
            
        csvf = open(str(filenames[0]), "r")
        vals = []
        for x in csvf:
            vals.append(x.split(","))
        fieldx = ["Month"]
        start_y = vals[0][0].split("-")[1]
        end_y = vals[len(vals)-1][0].split("-")[1]
        ss = 1
        while(ss<len(vals[0])):
            fieldx.append("Point " + str(ss))
            ss = ss + 1
        self.dlg2.tableWidget_2.setColumnCount(len(vals[0]))
        self.dlg2.tableWidget_2.setRowCount(len(vals))
        self.dlg2.tableWidget_2.setHorizontalHeaderLabels(fieldx)
        r = 0
        c = 0
        while(r<len(vals)):
            c = 0
            while(c<len(vals[0])):
                self.dlg2.tableWidget_2.setItem(r, c, QTableWidgetItem(str(vals[r][c])))
                c = c + 1
            r = r + 1
        csvf.close()
        self.dlg2.label_9.setText(str(start_y))
        self.dlg2.label_10.setText(str(end_y))
        self.dlg2.label_13.setText(str(filenames[0]))
        self.dlg2.comboBox.addItem('Composite')
        
        
    
    def pointspioutfol(self):
        dlgx = QFileDialog()
        dlgx.setFileMode(QFileDialog.Directory)
        
        
        if dlgx.exec_():
            filenames = dlgx.selectedFiles()
            self.dlg2.lineEdit_16.setText(str(filenames[0]))
    
    def spipoint(self):
        c0 = 2.515517
        c1 = 0.802583
        c2 = 0.010328
        d1 = 1.4327888
        d2 = 0.189269
        d3 = 0.001308
        err_flag = 0
        err_list = []
        compfile = self.dlg2.lineEdit_15.text()
        outfol = self.dlg2.lineEdit_16.text()
        self.dlg2.label_13.setText(str(compfile))
        self.dlg2.label_14.setText(str(outfol))
        
        
        
        if(compfile == ''):
            err_flag = 1
            err_list.append("Monthly Composite File is required. ")
        if(outfol == ''):
            err_flag = 1
            err_list.append("Output Folder is required. ")
        
        err_flag = 0  #CHANGE THIS----REMOVE THIS LINE
        
        if(err_flag == 1):
            self.dlg2.textEdit_1.append("\nThe following errors occured : \n")
            for errv in err_list:
                self.dlg2.textEdit_1.append(errv)
        else:
            ts_x = self.dlg2.comboBox_10.currentText()
            if(ts_x == '1 month'):
                ts = 1
            elif(ts_x == '3 months'):
                ts = 3
            elif(ts_x == '4 months'):
                ts = 4
            elif(ts_x == '6 months'):
                ts = 6
            elif(ts_x == '9 months'):
                ts = 9
            elif(ts_x == '12 months'):
                ts = 12
            elif(ts_x == '24 months'):
                ts = 24
            elif(ts_x == '36 months'):
                ts = 36
                
            stm_x = self.dlg2.comboBox_11.currentText()
            if(stm_x == 'January'):
                stm = 1
            elif(stm_x == 'February'):
                stm = 2
            elif(stm_x == 'March'):
                stm = 3
            elif(stm_x == 'April'):
                stm = 4
            elif(stm_x == 'May'):
                stm = 5
            elif(stm_x == 'June'):
                stm = 6
            elif(stm_x == 'July'):
                stm = 7
            elif(stm_x == 'August'):
                stm = 8
            elif(stm_x == 'September'):
                stm = 9
            elif(stm_x == 'October'):
                stm = 10
            elif(stm_x == 'November'):
                stm = 11
            elif(stm_x == 'December'):
                stm = 12
            
            enm_x = self.dlg2.comboBox_12.currentText()
            if(enm_x == 'January'):
                enm = 1
            elif(enm_x == 'February'):
                enm = 2
            elif(enm_x == 'March'):
                enm = 3
            elif(enm_x == 'April'):
                enm = 4
            elif(enm_x == 'May'):
                enm = 5
            elif(enm_x == 'June'):
                enm = 6
            elif(enm_x == 'July'):
                enm = 7
            elif(enm_x == 'August'):
                enm = 8
            elif(enm_x == 'September'):
                enm = 9
            elif(enm_x == 'October'):
                enm = 10
            elif(enm_x == 'November'):
                enm = 11
            elif(enm_x == 'December'):
                enm = 12
                
            
            
            monthsl = []
                
            stmc= stm
            enmc = enm
            
            if(stmc < enmc):
                while(stmc<=enmc):
                    monthsl.append(stmc)
                    stmc = stmc + 1
            elif(stmc>enmc):
                while(stmc<13):
                    monthsl.append(stmc)
                    stmc = stmc + 1
                ss = 1
                while(ss<=enmc):
                    monthsl.append(ss)
                    ss =ss + 1
            else:
                monthsl.append(stmc)
            
            
            
            
            #YEARS LIST
            start_y = self.dlg2.label_9.text()
            end_y = self.dlg2.label_10.text()
            years = []
            start_y = int(start_y)
            end_y = int(end_y)
            yc = start_y
            while(yc<=end_y):
                
                years.append(yc)
                yc = yc + 1
            
            #VALS LIST---------------------------------------------------------
            vals = []
            csvfnm = self.dlg2.lineEdit_15.text()
            
            csvfl = open(csvfnm,'r')
            
            for em in csvfl:
                vals.append(em.split(","))
                
            
            #------------------------------------------------------------------
            if(ts==1):
                u = 0
                while(u<len(monthsl)):
                    
                    self.dlg2.textEdit_1.append("\n1 month SPI generation for month " + str(monthsl[u]) + " started.")
                    #make list of all month values
                    curlist = []
                    for ee in vals:
                        if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                            curlist.append(ee)
                            
                    spilist = curlist
                    #THis just removes the new line feed in the end of each row
                    for xx in curlist:
                        lstcol = len(xx)-1
                        xx[lstcol]=xx[lstcol][:-2]
                        
                    
                    spicc = 1
                    while(spicc<=lstcol):  #replace 1 with lstcol
                        spi_li = []
                        for ttx in curlist:
                            spi_li.append(ttx[spicc])
                        
                        #Lets Calculate SPI
                        spi_wo_zero = []
                        for v in spi_li:
                            
                            if(float(v)>0):
                                spi_wo_zero.append(float(v))
                        
                        noofzero = len(spi_li) - len(spi_wo_zero)  
                        
                        
                        
                        gammav = []
                        t = []
                        shapex = 0
                        loc = 0
                        scalex = 0
                        
                        shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                        #Probability of Zero
                        zeroprob = noofzero / len(spi_li)
                        
                        a = 0
                        g = 0
                        spiv = 0.0
                        
                        prog_inc = 100.0/len(spi_li)
                        prog_val = 0
                        self.dlg2.progressBar_1.setValue(prog_val)
                        
                        while(a<len(spi_li)):
                            
                            if(spi_li[a]>=0):
                                
                                curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                gammav.append(curvale)
                                if(curvale<=0.5):
                                    g = (math.log(1/(curvale*curvale)))**0.5
                                    t.append(g)
                                    
                                    spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                    
                                else:
                                    g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                    t.append(g)
                                    
                                    spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                
                            
                            if(float(spilist[a][spicc])>0.0):
                                spilist[a][spicc] = spiv
                            else:
                                spilist[a][spicc] = 0.0
                            
                            prog_val = prog_val + prog_inc
                            self.dlg2.progressBar_1.setValue(prog_val)
                            QApplication.processEvents()
                            a = a + 1
                        
                        self.dlg2.progressBar_1.setValue(0)
                        spicc = spicc + 1   
                    
                    
                    
                    
                        
                    outcsv = os.path.join(outfol, "SPI_1_" + str(monthsl[u]) + ".csv")
                    outfll = open(outcsv, 'w')
                    
                    for qq in spilist:
                        qq[0] = qq[0].split("-")[1]
                        strw = ''
                        for ww in qq:
                            strw = strw + str(ww) + ","
                        strw = strw[:-1] + "\n"
                        outfll.write(strw)
                        
                    outfll.close()
                    AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                    entry_is_there = False
                    for c in AllItems:
                        if(c=="SPI_1_" + str(monthsl[u])):
                            entry_is_there = True
                        else:
                            entry_is_there = False
                    if(entry_is_there == False):
                        self.dlg2.comboBox.addItem("SPI_1_" + str(monthsl[u]))
                    
                    self.dlg2.textEdit_1.append("\n1 month SPI values for month " + str(monthsl[u]) + " has been generated at : " + str(outcsv))
                    u = u + 1
            
            
            elif(ts==3):
                if(len(monthsl)<3):
                    self.dlg2.textEdit_1.append("3 months SPI can not be calculated for the given time period.")
                else:
                    u = 0
                    while(u<len(monthsl)-2):
                        
                        if(monthsl[u]==11):
                            self.dlg2.textEdit_1.append("\n3 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+2]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[:-1]
                                spi2 = np.array(spi2)
                                spi3 = spi3[1:]
                                spi3 = np.array(spi3)
                                
                                spi_li = list((spi1 + spi2 + spi3)/3)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_3_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2])+ ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_3_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_3_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]))
                            
                            self.dlg2.textEdit_1.append("\n3 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+2]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                            
                        elif(monthsl[u]==12):
                            self.dlg2.textEdit_1.append("\n3 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+2]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[1:]
                                spi2 = np.array(spi2)
                                spi3 = spi3[1:]
                                spi3 = np.array(spi3)
                                
                                spi_li = list((spi1 + spi2 + spi3)/3)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_3_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2])+ ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_3_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_3_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]))
                            
                            self.dlg2.textEdit_1.append("\n3 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+2]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                            
                        else:
                            self.dlg2.textEdit_1.append("\n3 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+2]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                
                                spi1 = np.array(spi1)
                                
                                spi2 = np.array(spi2)
                                spi3 = np.array(spi3)
                                
                                spi_li = list((spi1 + spi2 + spi3)/3)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_3_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2])+ ".csv")
                            outfll = open(outcsv, 'w')
                            
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_3_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_3_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]))
                            
                            self.dlg2.textEdit_1.append("\n3 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+2]) + " has been generated at : " + str(outcsv))
                            u = u + 1    
            elif(ts==4):
                if(len(monthsl)<4):
                    self.dlg2.textEdit_1.append("4 months SPI can not be calculated for the given time period.")
                else:
                    u = 0
                    while(u<len(monthsl)-3):
                        if(monthsl[u]==10):
                            self.dlg2.textEdit_1.append("\n4 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+3]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[:-1]
                                spi2 = np.array(spi2)
                                spi3 = spi3[:-1]
                                spi3 = np.array(spi3)
                                spi4 = spi4[1:]
                                spi4 = np.array(spi4)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4)/4)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_4_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) + ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_4_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_4_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]))
                            
                            self.dlg2.textEdit_1.append("\n4 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+3]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                        elif(monthsl[u]==11):
                            self.dlg2.textEdit_1.append("\n4 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+3]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[:-1]
                                spi2 = np.array(spi2)
                                spi3 = spi3[1:]
                                spi3 = np.array(spi3)
                                spi4 = spi4[1:]
                                spi4 = np.array(spi4)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4)/4)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_4_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) + ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_4_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_4_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]))
                            
                            self.dlg2.textEdit_1.append("\n4 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+3]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                            
                        elif(monthsl[u]==12):
                            self.dlg2.textEdit_1.append("\n4 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+3]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[1:]
                                spi2 = np.array(spi2)
                                spi3 = spi3[1:]
                                spi3 = np.array(spi3)
                                spi4 = spi4[1:]
                                spi4 = np.array(spi4)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4)/4)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_4_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) + ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_4_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_4_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]))
                            
                            self.dlg2.textEdit_1.append("\n4 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+3]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                            
                        else:
                            self.dlg2.textEdit_1.append("\n4 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+3]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                
                                spi1 = np.array(spi1)
                                
                                spi2 = np.array(spi2)
                            
                                spi3 = np.array(spi3)
                                
                                spi4 = np.array(spi4)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4)/4)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_4_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) + ".csv")
                            outfll = open(outcsv, 'w')
                            
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_4_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_4_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]))
                            
                            self.dlg2.textEdit_1.append("\n4 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+3]) + " has been generated at : " + str(outcsv))
                            u = u + 1
            elif(ts==6):
                if(len(monthsl)<6):
                    self.dlg2.textEdit_1.append("6 months SPI can not be calculated for the given time period.")
                else:
                    u = 0
                    while(u<len(monthsl)-5):
                        if(monthsl[u]==8):
                            self.dlg2.textEdit_1.append("\n6 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+5]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[:-1]
                                spi2 = np.array(spi2)
                                spi3 = spi3[:-1]
                                spi3 = np.array(spi3)
                                spi4 = spi4[:-1]
                                spi4 = np.array(spi4)
                                spi5 = spi5[:-1]
                                spi5 = np.array(spi5)
                                spi6 = spi6[1:]
                                spi6 = np.array(spi6)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6)/6)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5]) + ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5]))
                            
                            self.dlg2.textEdit_1.append("\n6 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+5]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                        
                        elif(monthsl[u]==9):
                            self.dlg2.textEdit_1.append("\n6 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+5]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[:-1]
                                spi2 = np.array(spi2)
                                spi3 = spi3[:-1]
                                spi3 = np.array(spi3)
                                spi4 = spi4[:-1]
                                spi4 = np.array(spi4)
                                spi5 = spi5[1:]
                                spi5 = np.array(spi5)
                                spi6 = spi6[1:]
                                spi6 = np.array(spi6)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6)/6)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5]) + ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5]))
                            
                            self.dlg2.textEdit_1.append("\n6 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+5]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                        
                        elif(monthsl[u]==10):
                            self.dlg2.textEdit_1.append("\n6 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+5]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[:-1]
                                spi2 = np.array(spi2)
                                spi3 = spi3[:-1]
                                spi3 = np.array(spi3)
                                spi4 = spi4[1:]
                                spi4 = np.array(spi4)
                                spi5 = spi5[1:]
                                spi5 = np.array(spi5)
                                spi6 = spi6[1:]
                                spi6 = np.array(spi6)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6)/6)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5]) + ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5]))
                            
                            self.dlg2.textEdit_1.append("\n6 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+5]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                            
                        elif(monthsl[u]==11):
                            self.dlg2.textEdit_1.append("\n6 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+5]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[:-1]
                                spi2 = np.array(spi2)
                                spi3 = spi3[1:]
                                spi3 = np.array(spi3)
                                spi4 = spi4[1:]
                                spi4 = np.array(spi4)
                                spi5 = spi5[1:]
                                spi5 = np.array(spi5)
                                spi6 = spi6[1:]
                                spi6 = np.array(spi6)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6)/6)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5]) + ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5]))
                            
                            self.dlg2.textEdit_1.append("\n6 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+5]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                            
                        elif(monthsl[u]==12):
                            self.dlg2.textEdit_1.append("\n6 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+5]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[1:]
                                spi2 = np.array(spi2)
                                spi3 = spi3[1:]
                                spi3 = np.array(spi3)
                                spi4 = spi4[1:]
                                spi4 = np.array(spi4)
                                spi5 = spi5[1:]
                                spi5 = np.array(spi5)
                                spi6 = spi6[1:]
                                spi6 = np.array(spi6)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6)/6)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5]) + ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5]))
                            
                            self.dlg2.textEdit_1.append("\n6 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+5]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                            
                        else:
                            self.dlg2.textEdit_1.append("\n6 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+5]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                
                                spi1 = np.array(spi1)
                                
                                spi2 = np.array(spi2)
                                
                                spi3 = np.array(spi3)
                                
                                spi4 = np.array(spi4)
                                
                                spi5 = np.array(spi5)
                                
                                spi6 = np.array(spi6)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6)/6)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5]) + ".csv")
                            outfll = open(outcsv, 'w')
                            
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_6_" + str(monthsl[u]) + "_"+ str(monthsl[u+1]) +"_"+ str(monthsl[u+2]) +"_"+ str(monthsl[u+3]) +"_"+ str(monthsl[u+4])+"_"+ str(monthsl[u+5]))
                            
                            self.dlg2.textEdit_1.append("\n6 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+5]) + " has been generated at : " + str(outcsv))
                            u = u + 1
            elif(ts==9):
                if(len(monthsl)<9):
                    self.dlg2.textEdit_1.append("9 months SPI can not be calculated for the given time period.")
                else:
                    u = 0
                    while(u<len(monthsl)-8):
                        if(monthsl[u]==5):
                            self.dlg2.textEdit_1.append("\n9 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+8]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            curlist7 = []
                            curlist8 = []
                            curlist9 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+6]):
                                    curlist7.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+7]):
                                    curlist8.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+8]):
                                    curlist9.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist7:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist8:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist9:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                spi7 = []
                                spi8 = []
                                spi9 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                for spix in curlist7:
                                    try:
                                        spi7.append(float(spix[spicc]))
                                    except:
                                        spi7.append(0.0)
                                
                                for spix in curlist8:
                                    try:
                                        spi8.append(float(spix[spicc]))
                                    except:
                                        spi8.append(0.0)
                                
                                for spix in curlist9:
                                    try:
                                        spi9.append(float(spix[spicc]))
                                    except:
                                        spi9.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[:-1]
                                spi2 = np.array(spi2)
                                spi3 = spi3[:-1]
                                spi3 = np.array(spi3)
                                spi4 = spi4[:-1]
                                spi4 = np.array(spi4)
                                spi5 = spi5[:-1]
                                spi5 = np.array(spi5)
                                spi6 = spi6[:-1]
                                spi6 = np.array(spi6)
                                spi7 = spi7[:-1]
                                spi7 = np.array(spi7)
                                spi8 = spi8[:-1]
                                spi8 = np.array(spi8)
                                spi9 = spi9[1:]
                                spi9 = np.array(spi9)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6 + spi7 + spi8 + spi9)/9)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])+ ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8]))
                            
                            self.dlg2.textEdit_1.append("\n9 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+8]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                            
                        elif(monthsl[u]==6):
                            self.dlg2.textEdit_1.append("\n9 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+8]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            curlist7 = []
                            curlist8 = []
                            curlist9 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+6]):
                                    curlist7.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+7]):
                                    curlist8.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+8]):
                                    curlist9.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist7:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist8:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist9:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                spi7 = []
                                spi8 = []
                                spi9 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                for spix in curlist7:
                                    try:
                                        spi7.append(float(spix[spicc]))
                                    except:
                                        spi7.append(0.0)
                                
                                for spix in curlist8:
                                    try:
                                        spi8.append(float(spix[spicc]))
                                    except:
                                        spi8.append(0.0)
                                
                                for spix in curlist9:
                                    try:
                                        spi9.append(float(spix[spicc]))
                                    except:
                                        spi9.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[:-1]
                                spi2 = np.array(spi2)
                                spi3 = spi3[:-1]
                                spi3 = np.array(spi3)
                                spi4 = spi4[:-1]
                                spi4 = np.array(spi4)
                                spi5 = spi5[:-1]
                                spi5 = np.array(spi5)
                                spi6 = spi6[:-1]
                                spi6 = np.array(spi6)
                                spi7 = spi7[:-1]
                                spi7 = np.array(spi7)
                                spi8 = spi8[1:]
                                spi8 = np.array(spi8)
                                spi9 = spi9[1:]
                                spi9 = np.array(spi9)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6 + spi7 + spi8 + spi9)/9)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])+ ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8]))
                            
                            self.dlg2.textEdit_1.append("\n9 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+8]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                            
                        elif(monthsl[u]==7):
                            self.dlg2.textEdit_1.append("\n9 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+8]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            curlist7 = []
                            curlist8 = []
                            curlist9 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+6]):
                                    curlist7.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+7]):
                                    curlist8.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+8]):
                                    curlist9.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist7:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist8:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist9:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                spi7 = []
                                spi8 = []
                                spi9 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                for spix in curlist7:
                                    try:
                                        spi7.append(float(spix[spicc]))
                                    except:
                                        spi7.append(0.0)
                                
                                for spix in curlist8:
                                    try:
                                        spi8.append(float(spix[spicc]))
                                    except:
                                        spi8.append(0.0)
                                
                                for spix in curlist9:
                                    try:
                                        spi9.append(float(spix[spicc]))
                                    except:
                                        spi9.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[:-1]
                                spi2 = np.array(spi2)
                                spi3 = spi3[:-1]
                                spi3 = np.array(spi3)
                                spi4 = spi4[:-1]
                                spi4 = np.array(spi4)
                                spi5 = spi5[:-1]
                                spi5 = np.array(spi5)
                                spi6 = spi6[:-1]
                                spi6 = np.array(spi6)
                                spi7 = spi7[1:]
                                spi7 = np.array(spi7)
                                spi8 = spi8[1:]
                                spi8 = np.array(spi8)
                                spi9 = spi9[1:]
                                spi9 = np.array(spi9)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6 + spi7 + spi8 + spi9)/9)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])+ ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8]))
                            
                            self.dlg2.textEdit_1.append("\n9 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+8]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                            
                        elif(monthsl[u]==8):
                            self.dlg2.textEdit_1.append("\n9 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+8]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            curlist7 = []
                            curlist8 = []
                            curlist9 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+6]):
                                    curlist7.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+7]):
                                    curlist8.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+8]):
                                    curlist9.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist7:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist8:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist9:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                spi7 = []
                                spi8 = []
                                spi9 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                for spix in curlist7:
                                    try:
                                        spi7.append(float(spix[spicc]))
                                    except:
                                        spi7.append(0.0)
                                
                                for spix in curlist8:
                                    try:
                                        spi8.append(float(spix[spicc]))
                                    except:
                                        spi8.append(0.0)
                                
                                for spix in curlist9:
                                    try:
                                        spi9.append(float(spix[spicc]))
                                    except:
                                        spi9.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[:-1]
                                spi2 = np.array(spi2)
                                spi3 = spi3[:-1]
                                spi3 = np.array(spi3)
                                spi4 = spi4[:-1]
                                spi4 = np.array(spi4)
                                spi5 = spi5[:-1]
                                spi5 = np.array(spi5)
                                spi6 = spi6[1:]
                                spi6 = np.array(spi6)
                                spi7 = spi7[1:]
                                spi7 = np.array(spi7)
                                spi8 = spi8[1:]
                                spi8 = np.array(spi8)
                                spi9 = spi9[1:]
                                spi9 = np.array(spi9)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6 + spi7 + spi8 + spi9)/9)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])+ ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8]))
                            
                            self.dlg2.textEdit_1.append("\n9 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+8]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                            
                        
                        elif(monthsl[u]==9):
                            self.dlg2.textEdit_1.append("\n9 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+8]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            curlist7 = []
                            curlist8 = []
                            curlist9 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+6]):
                                    curlist7.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+7]):
                                    curlist8.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+8]):
                                    curlist9.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist7:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist8:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist9:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                spi7 = []
                                spi8 = []
                                spi9 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                for spix in curlist7:
                                    try:
                                        spi7.append(float(spix[spicc]))
                                    except:
                                        spi7.append(0.0)
                                
                                for spix in curlist8:
                                    try:
                                        spi8.append(float(spix[spicc]))
                                    except:
                                        spi8.append(0.0)
                                
                                for spix in curlist9:
                                    try:
                                        spi9.append(float(spix[spicc]))
                                    except:
                                        spi9.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[:-1]
                                spi2 = np.array(spi2)
                                spi3 = spi3[:-1]
                                spi3 = np.array(spi3)
                                spi4 = spi4[:-1]
                                spi4 = np.array(spi4)
                                spi5 = spi5[1:]
                                spi5 = np.array(spi5)
                                spi6 = spi6[1:]
                                spi6 = np.array(spi6)
                                spi7 = spi7[1:]
                                spi7 = np.array(spi7)
                                spi8 = spi8[1:]
                                spi8 = np.array(spi8)
                                spi9 = spi9[1:]
                                spi9 = np.array(spi9)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6 + spi7 + spi8 + spi9)/9)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])+ ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8]))
                            
                            self.dlg2.textEdit_1.append("\n9 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+8]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                        
                        elif(monthsl[u]==10):
                            self.dlg2.textEdit_1.append("\n9 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+8]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            curlist7 = []
                            curlist8 = []
                            curlist9 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+6]):
                                    curlist7.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+7]):
                                    curlist8.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+8]):
                                    curlist9.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist7:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist8:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist9:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                spi7 = []
                                spi8 = []
                                spi9 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                for spix in curlist7:
                                    try:
                                        spi7.append(float(spix[spicc]))
                                    except:
                                        spi7.append(0.0)
                                
                                for spix in curlist8:
                                    try:
                                        spi8.append(float(spix[spicc]))
                                    except:
                                        spi8.append(0.0)
                                
                                for spix in curlist9:
                                    try:
                                        spi9.append(float(spix[spicc]))
                                    except:
                                        spi9.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[:-1]
                                spi2 = np.array(spi2)
                                spi3 = spi3[:-1]
                                spi3 = np.array(spi3)
                                spi4 = spi4[1:]
                                spi4 = np.array(spi4)
                                spi5 = spi5[1:]
                                spi5 = np.array(spi5)
                                spi6 = spi6[1:]
                                spi6 = np.array(spi6)
                                spi7 = spi7[1:]
                                spi7 = np.array(spi7)
                                spi8 = spi8[1:]
                                spi8 = np.array(spi8)
                                spi9 = spi9[1:]
                                spi9 = np.array(spi9)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6 + spi7 + spi8 + spi9)/9)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])+ ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8]))
                            
                            self.dlg2.textEdit_1.append("\n9 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+8]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                            
                        elif(monthsl[u]==11):
                            self.dlg2.textEdit_1.append("\n9 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+8]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            curlist7 = []
                            curlist8 = []
                            curlist9 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+6]):
                                    curlist7.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+7]):
                                    curlist8.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+8]):
                                    curlist9.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist7:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist8:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist9:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                spi7 = []
                                spi8 = []
                                spi9 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                for spix in curlist7:
                                    try:
                                        spi7.append(float(spix[spicc]))
                                    except:
                                        spi7.append(0.0)
                                
                                for spix in curlist8:
                                    try:
                                        spi8.append(float(spix[spicc]))
                                    except:
                                        spi8.append(0.0)
                                
                                for spix in curlist9:
                                    try:
                                        spi9.append(float(spix[spicc]))
                                    except:
                                        spi9.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[:-1]
                                spi2 = np.array(spi2)
                                spi3 = spi3[1:]
                                spi3 = np.array(spi3)
                                spi4 = spi4[1:]
                                spi4 = np.array(spi4)
                                spi5 = spi5[1:]
                                spi5 = np.array(spi5)
                                spi6 = spi6[1:]
                                spi6 = np.array(spi6)
                                spi7 = spi7[1:]
                                spi7 = np.array(spi7)
                                spi8 = spi8[1:]
                                spi8 = np.array(spi8)
                                spi9 = spi9[1:]
                                spi9 = np.array(spi9)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6 + spi7 + spi8 + spi9)/9)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])+ ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8]))
                            
                            self.dlg2.textEdit_1.append("\n9 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+8]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                            
                        elif(monthsl[u]==12):
                            self.dlg2.textEdit_1.append("\n9 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+8]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            curlist7 = []
                            curlist8 = []
                            curlist9 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+6]):
                                    curlist7.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+7]):
                                    curlist8.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+8]):
                                    curlist9.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist7:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist8:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist9:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                spi7 = []
                                spi8 = []
                                spi9 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                for spix in curlist7:
                                    try:
                                        spi7.append(float(spix[spicc]))
                                    except:
                                        spi7.append(0.0)
                                
                                for spix in curlist8:
                                    try:
                                        spi8.append(float(spix[spicc]))
                                    except:
                                        spi8.append(0.0)
                                
                                for spix in curlist9:
                                    try:
                                        spi9.append(float(spix[spicc]))
                                    except:
                                        spi9.append(0.0)
                                
                                spi1 = spi1[:-1]
                                spi1 = np.array(spi1)
                                spi2 = spi2[1:]
                                spi2 = np.array(spi2)
                                spi3 = spi3[1:]
                                spi3 = np.array(spi3)
                                spi4 = spi4[1:]
                                spi4 = np.array(spi4)
                                spi5 = spi5[1:]
                                spi5 = np.array(spi5)
                                spi6 = spi6[1:]
                                spi6 = np.array(spi6)
                                spi7 = spi7[1:]
                                spi7 = np.array(spi7)
                                spi8 = spi8[1:]
                                spi8 = np.array(spi8)
                                spi9 = spi9[1:]
                                spi9 = np.array(spi9)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6 + spi7 + spi8 + spi9)/9)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                    
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])+ ".csv")
                            outfll = open(outcsv, 'w')
                            spilist = spilist[:-1]
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8]))
                            
                            self.dlg2.textEdit_1.append("\n9 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+8]) + " has been generated at : " + str(outcsv))
                            u = u + 1
                            
                        else:
                            self.dlg2.textEdit_1.append("\n9 month SPI generation for month " + str(monthsl[u]) + " to " + str(monthsl[u+8]) + " started.")
                            #make list of all month values
                            curlist = []
                            curlist1 = []
                            curlist2 = []
                            curlist3 = []
                            curlist4 = []
                            curlist5 = []
                            curlist6 = []
                            curlist7 = []
                            curlist8 = []
                            curlist9 = []
                            for ee in vals:
                                if(int(ee[0].split("-")[0]))==int(monthsl[u]):
                                    curlist1.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+1]):
                                    curlist2.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+2]):
                                    curlist3.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+3]):
                                    curlist4.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+4]):
                                    curlist5.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+5]):
                                    curlist6.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+6]):
                                    curlist7.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+7]):
                                    curlist8.append(ee)
                                elif(int(ee[0].split("-")[0]))==int(monthsl[u+8]):
                                    curlist9.append(ee)
                                    
                            
                                            
                            spilist = curlist1
                            for xx in curlist1:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist2:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist3:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            for xx in curlist4:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist5:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist6:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist7:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist8:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                            
                            for xx in curlist9:
                                lstcol = len(xx)-1
                                xx[lstcol]=xx[lstcol][:-2]
                                
                            spicc = 1
                            
                            
                            
                            
                            while(spicc<=lstcol):  #replace 1 with lstcol
                                spi_li = []
                                spi1 = []
                                spi2 = []
                                spi3 = []
                                spi4 = []
                                spi5 = []
                                spi6 = []
                                spi7 = []
                                spi8 = []
                                spi9 = []
                                
                                for spix in curlist1:
                                    
                                    try:
                                        spi1.append(float(spix[spicc]))
                                    except:
                                        spi1.append(0.0)
                                
                                
                                
                                for spix in curlist2:
                                    try:
                                        spi2.append(float(spix[spicc]))
                                    except:
                                        spi2.append(0.0)
                                
                                
                                for spix in curlist3:
                                    try:
                                        spi3.append(float(spix[spicc]))
                                    except:
                                        spi3.append(0.0)
                                
                                for spix in curlist4:
                                    try:
                                        spi4.append(float(spix[spicc]))
                                    except:
                                        spi4.append(0.0)
                                
                                for spix in curlist5:
                                    try:
                                        spi5.append(float(spix[spicc]))
                                    except:
                                        spi5.append(0.0)
                                
                                for spix in curlist6:
                                    try:
                                        spi6.append(float(spix[spicc]))
                                    except:
                                        spi6.append(0.0)
                                
                                for spix in curlist7:
                                    try:
                                        spi7.append(float(spix[spicc]))
                                    except:
                                        spi7.append(0.0)
                                
                                for spix in curlist8:
                                    try:
                                        spi8.append(float(spix[spicc]))
                                    except:
                                        spi8.append(0.0)
                                
                                for spix in curlist9:
                                    try:
                                        spi9.append(float(spix[spicc]))
                                    except:
                                        spi9.append(0.0)
                                
                                
                                spi1 = np.array(spi1)
                                
                                spi2 = np.array(spi2)
                                
                                spi3 = np.array(spi3)
                                
                                spi4 = np.array(spi4)
                                
                                spi5 = np.array(spi5)
                                
                                spi6 = np.array(spi6)
                                
                                spi7 = np.array(spi7)
                                
                                spi8 = np.array(spi8)
                                
                                spi9 = np.array(spi9)
                                
                                spi_li = list((spi1 + spi2 + spi3 + spi4 + spi5 + spi6 + spi7 + spi8 + spi9)/9)
                                
                                #Lets Calculate SPI
                                spi_wo_zero = []
                                for v in spi_li:
                                    
                                    if(float(v)>0):
                                        spi_wo_zero.append(float(v))
                                
                                noofzero = len(spi_li) - len(spi_wo_zero)  
                                
                                
                                
                                gammav = []
                                t = []
                                shapex = 0
                                loc = 0
                                scalex = 0
                                
                                shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                                #Probability of Zero
                                zeroprob = noofzero / len(spi_li)
                                
                                a = 0
                                g = 0
                                spiv = 0.0
                                
                                prog_inc = 100.0/len(spi_li)
                                prog_val = 0
                                self.dlg2.progressBar_1.setValue(prog_val)
                                
                                while(a<len(spi_li)):
                                    
                                    if(spi_li[a]>=0):
                                        
                                        curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                                        curvale = zeroprob + ((1.0-zeroprob)*curvale)
                                        gammav.append(curvale)
                                        if(curvale<=0.5):
                                            g = (math.log(1/(curvale*curvale)))**0.5
                                            t.append(g)
                                            
                                            spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                            
                                        else:
                                            g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                            t.append(g)
                                            
                                            spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                        
                                    
                                    
                                    try:
                                        saa = float(spilist[a][spicc])
                                    except:
                                        spilist[a][spicc] = 0.0
                                        
                                    if(float(spilist[a][spicc])>0.0):
                                        spilist[a][spicc] = spiv
                                    else:
                                        spilist[a][spicc] = 0.0
                                    
                                    prog_val = prog_val + prog_inc
                                    self.dlg2.progressBar_1.setValue(prog_val)
                                    QApplication.processEvents()
                                    a = a + 1
                                
                                self.dlg2.progressBar_1.setValue(0)
                                spicc = spicc + 1   
                            
                            
                            
                            
                                
                            outcsv = os.path.join(outfol, "SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])+ ".csv")
                            outfll = open(outcsv, 'w')
                            
                            for qq in spilist:
                                qq[0] = qq[0].split("-")[1]
                                strw = ''
                                for ww in qq:
                                    strw = strw + str(ww) + ","
                                strw = strw[:-1] + "\n"
                                outfll.write(strw)
                                
                            outfll.close()
                            AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                            entry_is_there = False
                            for c in AllItems:
                                if(c=="SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8])):
                                    entry_is_there = True
                                else:
                                    entry_is_there = False
                            if(entry_is_there == False):
                                self.dlg2.comboBox.addItem("SPI_9_" + str(monthsl[u]) + "_"+ str(monthsl[u+1])  + "_"+ str(monthsl[u+2]) + "_"+ str(monthsl[u+3]) + "_"+ str(monthsl[u+4]) + "_"+ str(monthsl[u+5]) + "_"+ str(monthsl[u+6]) + "_"+ str(monthsl[u+7]) + "_"+ str(monthsl[u+8]))
                            
                            self.dlg2.textEdit_1.append("\n9 month SPI values for month " + str(monthsl[u]) + " to " +str(monthsl[u+8]) + " has been generated at : " + str(outcsv))
                            u = u + 1
            elif(ts==12):
                self.dlg2.textEdit_1.append("\n12 month SPI generation started.")
                #make list of all month values
                curlist = []
                curlist1 = []
                curlist2 = []
                curlist3 = []
                curlist4 = []
                curlist5 = []
                curlist6 = []
                curlist7 = []
                curlist8 = []
                curlist9 = []
                curlist10 = []
                curlist11 = []
                curlist12 = []
                
                for ee in vals:
                    if(int(ee[0].split("-")[0])==1):
                        curlist1.append(ee)
                    elif(int(ee[0].split("-")[0])==2):
                        curlist2.append(ee)
                    elif(int(ee[0].split("-")[0])==3):
                        curlist3.append(ee)
                    elif(int(ee[0].split("-")[0])==4):
                        curlist4.append(ee)
                    elif(int(ee[0].split("-")[0])==5):
                        curlist5.append(ee)
                    elif(int(ee[0].split("-")[0])==6):
                        curlist6.append(ee)
                    elif(int(ee[0].split("-")[0])==7):
                        curlist7.append(ee)
                    elif(int(ee[0].split("-")[0])==8):
                        curlist8.append(ee)
                    elif(int(ee[0].split("-")[0])==9):
                        curlist9.append(ee)
                    elif(int(ee[0].split("-")[0])==10):
                        curlist10.append(ee)
                    elif(int(ee[0].split("-")[0])==11):
                        curlist11.append(ee)
                    elif(int(ee[0].split("-")[0])==12):
                        curlist12.append(ee)
                    
                        
                
                                
                spilist = curlist1
                for xx in curlist1:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist2:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                for xx in curlist3:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist4:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist5:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                for xx in curlist6:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist7:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist8:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                for xx in curlist9:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist10:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist11:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                for xx in curlist12:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                
                spicc = 1
                
                
                
                
                while(spicc<=lstcol):  #replace 1 with lstcol
                    spi_li = []
                    spi1 = []
                    spi2 = []
                    spi3 = []
                    spi4 = []
                    spi5 = []
                    spi6 = []
                    spi7 = []
                    spi8 = []
                    spi9 = []
                    spi10 = []
                    spi11 = []
                    spi12 = []
                    
                    for spix in curlist1:
                        
                        try:
                            spi1.append(float(spix[spicc]))
                        except:
                            spi1.append(0.0)
                    
                    
                    
                    for spix in curlist2:
                        try:
                            spi2.append(float(spix[spicc]))
                        except:
                            spi2.append(0.0)
                    
                    
                    for spix in curlist3:
                        try:
                            spi3.append(float(spix[spicc]))
                        except:
                            spi3.append(0.0)
                            
                    for spix in curlist4:
                        
                        try:
                            spi4.append(float(spix[spicc]))
                        except:
                            spi4.append(0.0)
                    
                    
                    
                    for spix in curlist5:
                        try:
                            spi5.append(float(spix[spicc]))
                        except:
                            spi5.append(0.0)
                    
                    
                    for spix in curlist6:
                        try:
                            spi6.append(float(spix[spicc]))
                        except:
                            spi6.append(0.0)
                            
                    for spix in curlist7:
                        
                        try:
                            spi7.append(float(spix[spicc]))
                        except:
                            spi7.append(0.0)
                    
                    
                    
                    for spix in curlist8:
                        try:
                            spi8.append(float(spix[spicc]))
                        except:
                            spi8.append(0.0)
                    
                    
                    for spix in curlist9:
                        try:
                            spi9.append(float(spix[spicc]))
                        except:
                            spi9.append(0.0)
                            
                    for spix in curlist10:
                        
                        try:
                            spi10.append(float(spix[spicc]))
                        except:
                            spi10.append(0.0)
                    
                    
                    
                    for spix in curlist11:
                        try:
                            spi11.append(float(spix[spicc]))
                        except:
                            spi11.append(0.0)
                    
                    
                    for spix in curlist12:
                        try:
                            spi12.append(float(spix[spicc]))
                        except:
                            spi12.append(0.0)
                    
                    
                    spi1 = np.array(spi1)
                    
                    spi2 = np.array(spi2)
                    
                    spi3 = np.array(spi3)
                    
                    spi4 = np.array(spi4)
                    
                    spi5 = np.array(spi5)
                    
                    spi6 = np.array(spi6)
                    
                    spi7 = np.array(spi7)
                    
                    spi8 = np.array(spi8)
                    
                    spi9 = np.array(spi9)
                    
                    spi10 = np.array(spi10)
                    
                    spi11 = np.array(spi11)
                    
                    spi12 = np.array(spi12)
                    
                    spi_li = list((spi1 + spi2 + spi3+spi4 + spi5 + spi6+spi7 + spi8 + spi9+spi10 + spi11 + spi12)/12)
                    
                    #Lets Calculate SPI
                    spi_wo_zero = []
                    for v in spi_li:
                        
                        if(float(v)>0):
                            spi_wo_zero.append(float(v))
                    
                    noofzero = len(spi_li) - len(spi_wo_zero)  
                    
                    
                    
                    gammav = []
                    t = []
                    shapex = 0
                    loc = 0
                    scalex = 0
                    
                    shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                    #Probability of Zero
                    zeroprob = noofzero / len(spi_li)
                    
                    a = 0
                    g = 0
                    spiv = 0.0
                    
                    prog_inc = 100.0/len(spi_li)
                    prog_val = 0
                    self.dlg2.progressBar_1.setValue(prog_val)
                    
                    while(a<len(spi_li)):
                        
                        if(spi_li[a]>=0):
                            
                            curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                            curvale = zeroprob + ((1.0-zeroprob)*curvale)
                            gammav.append(curvale)
                            if(curvale<=0.5):
                                g = (math.log(1/(curvale*curvale)))**0.5
                                t.append(g)
                                
                                spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                
                            else:
                                g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                t.append(g)
                                
                                spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                            
                        
                        try:
                            saa = float(spilist[a][spicc])
                        except:
                            spilist[a][spicc] = 0.0
                        
                        if(float(spilist[a][spicc])>0.0):
                            spilist[a][spicc] = spiv
                        else:
                            spilist[a][spicc] = 0.0
                        
                        prog_val = prog_val + prog_inc
                        self.dlg2.progressBar_1.setValue(prog_val)
                        QApplication.processEvents()
                        a = a + 1
                    
                    self.dlg2.progressBar_1.setValue(0)
                    spicc = spicc + 1   
                
                
                
                
                    
                outcsv = os.path.join(outfol, "SPI_12.csv")
                outfll = open(outcsv, 'w')
                
                for qq in spilist:
                    qq[0] = qq[0].split("-")[1]
                    strw = ''
                    for ww in qq:
                        strw = strw + str(ww) + ","
                    strw = strw[:-1] + "\n"
                    outfll.write(strw)
                    
                outfll.close()
                AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                entry_is_there = False
                for c in AllItems:
                    if(c=="SPI_12"):
                        entry_is_there = True
                    else:
                        entry_is_there = False
                if(entry_is_there == False):
                    self.dlg2.comboBox.addItem("SPI_12")
                
                self.dlg2.textEdit_1.append("\n12 month SPI values has been generated at : " + str(outcsv))
            
            elif(ts==24):
                self.dlg2.textEdit_1.append("\n24 month SPI generation started.")
                #make list of all month values
                curlist = []
                curlist1 = []
                curlist2 = []
                curlist3 = []
                curlist4 = []
                curlist5 = []
                curlist6 = []
                curlist7 = []
                curlist8 = []
                curlist9 = []
                curlist10 = []
                curlist11 = []
                curlist12 = []
                
                for ee in vals:
                    if(int(ee[0].split("-")[0])==1):
                        curlist1.append(ee)
                    elif(int(ee[0].split("-")[0])==2):
                        curlist2.append(ee)
                    elif(int(ee[0].split("-")[0])==3):
                        curlist3.append(ee)
                    elif(int(ee[0].split("-")[0])==4):
                        curlist4.append(ee)
                    elif(int(ee[0].split("-")[0])==5):
                        curlist5.append(ee)
                    elif(int(ee[0].split("-")[0])==6):
                        curlist6.append(ee)
                    elif(int(ee[0].split("-")[0])==7):
                        curlist7.append(ee)
                    elif(int(ee[0].split("-")[0])==8):
                        curlist8.append(ee)
                    elif(int(ee[0].split("-")[0])==9):
                        curlist9.append(ee)
                    elif(int(ee[0].split("-")[0])==10):
                        curlist10.append(ee)
                    elif(int(ee[0].split("-")[0])==11):
                        curlist11.append(ee)
                    elif(int(ee[0].split("-")[0])==12):
                        curlist12.append(ee)
                    
                        
                
                                
                spilist = curlist1
                for xx in curlist1:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist2:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                for xx in curlist3:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist4:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist5:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                for xx in curlist6:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist7:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist8:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                for xx in curlist9:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist10:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist11:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                for xx in curlist12:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                
                spicc = 1
                
                
                
                
                while(spicc<=lstcol):  #replace 1 with lstcol
                    spi_li = []
                    spi1 = []
                    spi2 = []
                    spi3 = []
                    spi4 = []
                    spi5 = []
                    spi6 = []
                    spi7 = []
                    spi8 = []
                    spi9 = []
                    spi10 = []
                    spi11 = []
                    spi12 = []
                    
                    for spix in curlist1:
                        
                        try:
                            spi1.append(float(spix[spicc]))
                        except:
                            spi1.append(0.0)
                    
                    
                    
                    for spix in curlist2:
                        try:
                            spi2.append(float(spix[spicc]))
                        except:
                            spi2.append(0.0)
                    
                    
                    for spix in curlist3:
                        try:
                            spi3.append(float(spix[spicc]))
                        except:
                            spi3.append(0.0)
                            
                    for spix in curlist4:
                        
                        try:
                            spi4.append(float(spix[spicc]))
                        except:
                            spi4.append(0.0)
                    
                    
                    
                    for spix in curlist5:
                        try:
                            spi5.append(float(spix[spicc]))
                        except:
                            spi5.append(0.0)
                    
                    
                    for spix in curlist6:
                        try:
                            spi6.append(float(spix[spicc]))
                        except:
                            spi6.append(0.0)
                            
                    for spix in curlist7:
                        
                        try:
                            spi7.append(float(spix[spicc]))
                        except:
                            spi7.append(0.0)
                    
                    
                    
                    for spix in curlist8:
                        try:
                            spi8.append(float(spix[spicc]))
                        except:
                            spi8.append(0.0)
                    
                    
                    for spix in curlist9:
                        try:
                            spi9.append(float(spix[spicc]))
                        except:
                            spi9.append(0.0)
                            
                    for spix in curlist10:
                        
                        try:
                            spi10.append(float(spix[spicc]))
                        except:
                            spi10.append(0.0)
                    
                    
                    
                    for spix in curlist11:
                        try:
                            spi11.append(float(spix[spicc]))
                        except:
                            spi11.append(0.0)
                    
                    
                    for spix in curlist12:
                        try:
                            spi12.append(float(spix[spicc]))
                        except:
                            spi12.append(0.0)
                    
                    spi1x = []
                    spi2x = []
                    spi3x = []
                    spi4x = []
                    spi5x = []
                    spi6x = []
                    spi7x = []
                    spi8x = []
                    spi9x = []
                    spi10x = []
                    spi11x = []
                    spi12x = []
                    
                    cc = 0
                    while(cc<(len(spi1)-1)):
                        spi1x.append(spi1[cc] + spi1[cc+1])
                        spi2x.append(spi2[cc] + spi2[cc+1])
                        spi3x.append(spi3[cc] + spi3[cc+1])
                        spi4x.append(spi4[cc] + spi4[cc+1])
                        spi5x.append(spi5[cc] + spi5[cc+1])
                        spi6x.append(spi6[cc] + spi6[cc+1])
                        spi7x.append(spi7[cc] + spi7[cc+1])
                        spi8x.append(spi8[cc] + spi8[cc+1])
                        spi9x.append(spi9[cc] + spi9[cc+1])
                        spi10x.append(spi10[cc] + spi10[cc+1])
                        spi11x.append(spi11[cc] + spi11[cc+1])
                        spi12x.append(spi12[cc] + spi12[cc+1])
                        cc = cc + 1
                    
                    
                    spi1x = np.array(spi1x)
                    
                    spi2x = np.array(spi2x)
                    
                    spi3x = np.array(spi3x)
                    
                    spi4x = np.array(spi4x)
                    
                    spi5x = np.array(spi5x)
                    
                    spi6x = np.array(spi6x)
                    
                    spi7x = np.array(spi7x)
                    
                    spi8x = np.array(spi8x)
                    
                    spi9x = np.array(spi9x)
                    
                    spi10x = np.array(spi10x)
                    
                    spi11x = np.array(spi11x)
                    
                    spi12x = np.array(spi12x)
                    
                    spi_li = list((spi1x + spi2x + spi3x+spi4x + spi5x + spi6x+spi7x + spi8x + spi9x+spi10x + spi11x + spi12x)/24)
                    
                    #Lets Calculate SPI
                    spi_wo_zero = []
                    for v in spi_li:
                        
                        if(float(v)>0):
                            spi_wo_zero.append(float(v))
                    
                    noofzero = len(spi_li) - len(spi_wo_zero)  
                    
                    
                    
                    gammav = []
                    t = []
                    shapex = 0
                    loc = 0
                    scalex = 0
                    
                    shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                    #Probability of Zero
                    zeroprob = noofzero / len(spi_li)
                    
                    a = 0
                    g = 0
                    spiv = 0.0
                    
                    prog_inc = 100.0/len(spi_li)
                    prog_val = 0
                    self.dlg2.progressBar_1.setValue(prog_val)
                    
                    while(a<len(spi_li)):
                        
                        if(spi_li[a]>=0):
                            
                            curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                            curvale = zeroprob + ((1.0-zeroprob)*curvale)
                            gammav.append(curvale)
                            if(curvale<=0.5):
                                g = (math.log(1/(curvale*curvale)))**0.5
                                t.append(g)
                                
                                spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                
                            else:
                                g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                t.append(g)
                                
                                spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                            
                        
                        try:
                            saa = float(spilist[a][spicc])
                        except:
                            spilist[a][spicc] = 0.0
                        
                        if(float(spilist[a][spicc])>0.0):
                            spilist[a][spicc] = spiv
                        else:
                            spilist[a][spicc] = 0.0
                        
                        prog_val = prog_val + prog_inc
                        self.dlg2.progressBar_1.setValue(prog_val)
                        QApplication.processEvents()
                        a = a + 1
                    
                    self.dlg2.progressBar_1.setValue(0)
                    spicc = spicc + 1   
                
                
                
                
                    
                outcsv = os.path.join(outfol, "SPI_24.csv")
                outfll = open(outcsv, 'w')
                
                for qq in spilist:
                    qq[0] = qq[0].split("-")[1]
                    strw = ''
                    for ww in qq:
                        strw = strw + str(ww) + ","
                    strw = strw[:-1] + "\n"
                    outfll.write(strw)
                    
                outfll.close()
                AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                entry_is_there = False
                for c in AllItems:
                    if(c=="SPI_24"):
                        entry_is_there = True
                    else:
                        entry_is_there = False
                if(entry_is_there == False):
                    self.dlg2.comboBox.addItem("SPI_24")
                
                self.dlg2.textEdit_1.append("\n24 month SPI values has been generated at : " + str(outcsv))
            elif(ts==36):
                self.dlg2.textEdit_1.append("\n36 month SPI generation started.")
                #make list of all month values
                curlist = []
                curlist1 = []
                curlist2 = []
                curlist3 = []
                curlist4 = []
                curlist5 = []
                curlist6 = []
                curlist7 = []
                curlist8 = []
                curlist9 = []
                curlist10 = []
                curlist11 = []
                curlist12 = []
                
                for ee in vals:
                    if(int(ee[0].split("-")[0])==1):
                        curlist1.append(ee)
                    elif(int(ee[0].split("-")[0])==2):
                        curlist2.append(ee)
                    elif(int(ee[0].split("-")[0])==3):
                        curlist3.append(ee)
                    elif(int(ee[0].split("-")[0])==4):
                        curlist4.append(ee)
                    elif(int(ee[0].split("-")[0])==5):
                        curlist5.append(ee)
                    elif(int(ee[0].split("-")[0])==6):
                        curlist6.append(ee)
                    elif(int(ee[0].split("-")[0])==7):
                        curlist7.append(ee)
                    elif(int(ee[0].split("-")[0])==8):
                        curlist8.append(ee)
                    elif(int(ee[0].split("-")[0])==9):
                        curlist9.append(ee)
                    elif(int(ee[0].split("-")[0])==10):
                        curlist10.append(ee)
                    elif(int(ee[0].split("-")[0])==11):
                        curlist11.append(ee)
                    elif(int(ee[0].split("-")[0])==12):
                        curlist12.append(ee)
                    
                        
                
                                
                spilist = curlist1
                for xx in curlist1:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist2:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                for xx in curlist3:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist4:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist5:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                for xx in curlist6:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist7:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist8:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                for xx in curlist9:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist10:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                
                for xx in curlist11:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                for xx in curlist12:
                    lstcol = len(xx)-1
                    xx[lstcol]=xx[lstcol][:-2]
                    
                
                spicc = 1
                
                
                
                
                while(spicc<=lstcol):  #replace 1 with lstcol
                    spi_li = []
                    spi1 = []
                    spi2 = []
                    spi3 = []
                    spi4 = []
                    spi5 = []
                    spi6 = []
                    spi7 = []
                    spi8 = []
                    spi9 = []
                    spi10 = []
                    spi11 = []
                    spi12 = []
                    
                    for spix in curlist1:
                        
                        try:
                            spi1.append(float(spix[spicc]))
                        except:
                            spi1.append(0.0)
                    
                    
                    
                    for spix in curlist2:
                        try:
                            spi2.append(float(spix[spicc]))
                        except:
                            spi2.append(0.0)
                    
                    
                    for spix in curlist3:
                        try:
                            spi3.append(float(spix[spicc]))
                        except:
                            spi3.append(0.0)
                            
                    for spix in curlist4:
                        
                        try:
                            spi4.append(float(spix[spicc]))
                        except:
                            spi4.append(0.0)
                    
                    
                    
                    for spix in curlist5:
                        try:
                            spi5.append(float(spix[spicc]))
                        except:
                            spi5.append(0.0)
                    
                    
                    for spix in curlist6:
                        try:
                            spi6.append(float(spix[spicc]))
                        except:
                            spi6.append(0.0)
                            
                    for spix in curlist7:
                        
                        try:
                            spi7.append(float(spix[spicc]))
                        except:
                            spi7.append(0.0)
                    
                    
                    
                    for spix in curlist8:
                        try:
                            spi8.append(float(spix[spicc]))
                        except:
                            spi8.append(0.0)
                    
                    
                    for spix in curlist9:
                        try:
                            spi9.append(float(spix[spicc]))
                        except:
                            spi9.append(0.0)
                            
                    for spix in curlist10:
                        
                        try:
                            spi10.append(float(spix[spicc]))
                        except:
                            spi10.append(0.0)
                    
                    
                    
                    for spix in curlist11:
                        try:
                            spi11.append(float(spix[spicc]))
                        except:
                            spi11.append(0.0)
                    
                    
                    for spix in curlist12:
                        try:
                            spi12.append(float(spix[spicc]))
                        except:
                            spi12.append(0.0)
                    
                    spi1x = []
                    spi2x = []
                    spi3x = []
                    spi4x = []
                    spi5x = []
                    spi6x = []
                    spi7x = []
                    spi8x = []
                    spi9x = []
                    spi10x = []
                    spi11x = []
                    spi12x = []
                    
                    cc = 0
                    while(cc<(len(spi1)-2)):
                        spi1x.append(spi1[cc] + spi1[cc+1] + spi1[cc+2])
                        spi2x.append(spi2[cc] + spi2[cc+1] + spi2[cc+2])
                        spi3x.append(spi3[cc] + spi3[cc+1] + spi3[cc+2])
                        spi4x.append(spi4[cc] + spi4[cc+1] + spi4[cc+2])
                        spi5x.append(spi5[cc] + spi5[cc+1] + spi5[cc+2])
                        spi6x.append(spi6[cc] + spi6[cc+1] + spi6[cc+2])
                        spi7x.append(spi7[cc] + spi7[cc+1] + spi7[cc+2])
                        spi8x.append(spi8[cc] + spi8[cc+1] + spi8[cc+2])
                        spi9x.append(spi9[cc] + spi9[cc+1] + spi9[cc+2])
                        spi10x.append(spi10[cc] + spi10[cc+1]  + spi10[cc+2])
                        spi11x.append(spi11[cc] + spi11[cc+1] + spi11[cc+2])
                        spi12x.append(spi12[cc] + spi12[cc+1] + spi12[cc+2])
                        cc = cc + 1
                    
                    
                    spi1x = np.array(spi1x)
                    
                    spi2x = np.array(spi2x)
                    
                    spi3x = np.array(spi3x)
                    
                    spi4x = np.array(spi4x)
                    
                    spi5x = np.array(spi5x)
                    
                    spi6x = np.array(spi6x)
                    
                    spi7x = np.array(spi7x)
                    
                    spi8x = np.array(spi8x)
                    
                    spi9x = np.array(spi9x)
                    
                    spi10x = np.array(spi10x)
                    
                    spi11x = np.array(spi11x)
                    
                    spi12x = np.array(spi12x)
                    
                    spi_li = list((spi1x + spi2x + spi3x+spi4x + spi5x + spi6x+spi7x + spi8x + spi9x+spi10x + spi11x + spi12x)/36)
                    
                    #Lets Calculate SPI
                    spi_wo_zero = []
                    for v in spi_li:
                        
                        if(float(v)>0):
                            spi_wo_zero.append(float(v))
                    
                    noofzero = len(spi_li) - len(spi_wo_zero)  
                    
                    
                    
                    gammav = []
                    t = []
                    shapex = 0
                    loc = 0
                    scalex = 0
                    
                    shapex, loc, scalex = gamma.fit(spi_wo_zero, floc=0)
                    #Probability of Zero
                    zeroprob = noofzero / len(spi_li)
                    
                    a = 0
                    g = 0
                    spiv = 0.0
                    
                    prog_inc = 100.0/len(spi_li)
                    prog_val = 0
                    self.dlg2.progressBar_1.setValue(prog_val)
                    
                    while(a<len(spi_li)):
                        
                        if(spi_li[a]>=0):
                            
                            curvale = gamma.cdf(float(spi_li[a]),shapex, scale = scalex)
                            curvale = zeroprob + ((1.0-zeroprob)*curvale)
                            gammav.append(curvale)
                            if(curvale<=0.5):
                                g = (math.log(1/(curvale*curvale)))**0.5
                                t.append(g)
                                
                                spiv = (-1)*(g-((c0 +c1 * g+ c2 *g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                                
                            else:
                                g = (math.log(1/((1-curvale)*(1-curvale))))**0.5
                                t.append(g)
                                
                                spiv = (g-((c0+c1*g+c2*g*g)/(1+d1*g+d2*g*g+d3*g*g*g)))
                            
                        
                        try:
                            saa = float(spilist[a][spicc])
                        except:
                            spilist[a][spicc] = 0.0
                        
                        if(float(spilist[a][spicc])>0.0):
                            spilist[a][spicc] = spiv
                        else:
                            spilist[a][spicc] = 0.0
                        
                        prog_val = prog_val + prog_inc
                        self.dlg2.progressBar_1.setValue(prog_val)
                        QApplication.processEvents()
                        a = a + 1
                    
                    self.dlg2.progressBar_1.setValue(0)
                    spicc = spicc + 1   
                
                
                
                
                    
                outcsv = os.path.join(outfol, "SPI_36.csv")
                outfll = open(outcsv, 'w')
                
                for qq in spilist:
                    qq[0] = qq[0].split("-")[1]
                    strw = ''
                    for ww in qq:
                        strw = strw + str(ww) + ","
                    strw = strw[:-1] + "\n"
                    outfll.write(strw)
                    
                outfll.close()
                AllItems = [self.dlg2.comboBox.itemText(i) for i in range(self.dlg2.comboBox.count())]
                entry_is_there = False
                for c in AllItems:
                    if(c=="SPI_36"):
                        entry_is_there = True
                    else:
                        entry_is_there = False
                if(entry_is_there == False):
                    self.dlg2.comboBox.addItem("SPI_36")
                
                self.dlg2.textEdit_1.append("\n36 month SPI values has been generated at : " + str(outcsv))
                
                            
    def loadspi(self):
        curt = self.dlg2.comboBox.currentText()
        
        
        
        
        
        if(curt=='Composite'):
            pathcsv = self.dlg2.label_13.text()
            csvf = open(str(pathcsv), "r")
            vals = []
            for x in csvf:
                vals.append(x.split(","))
            fieldx = ["Month"]
            ss = 1
            while(ss<len(vals[0])):
                fieldx.append("Point " + str(ss))
                ss = ss + 1
            self.dlg2.tableWidget_3.setColumnCount(len(vals[0]))
            self.dlg2.tableWidget_3.setRowCount(len(vals))
            self.dlg2.tableWidget_3.setHorizontalHeaderLabels(fieldx)
            r = 0
            c = 0
            while(r<len(vals)):
                c = 0
                while(c<len(vals[0])):
                    self.dlg2.tableWidget_3.setItem(r, c, QTableWidgetItem(str(vals[r][c])))
                    c = c + 1
                r = r + 1
            csvf.close()
        else:
            outpath = self.dlg2.label_14.text()
            filenm = curt + ".csv"
            pathcsv = os.path.join(outpath, filenm)
            csvf = open(str(pathcsv), "r")
            vals = []
            for x in csvf:
                vals.append(x.split(","))
            fieldx = ["Year"]
            ss = 1
            while(ss<len(vals[0])):
                fieldx.append("Point " + str(ss))
                ss = ss + 1
            self.dlg2.tableWidget_3.setColumnCount(len(vals[0]))
            self.dlg2.tableWidget_3.setRowCount(len(vals))
            self.dlg2.tableWidget_3.setHorizontalHeaderLabels(fieldx)
            r = 0
            c = 0
            while(r<len(vals)):
                c = 0
                while(c<len(vals[0])):
                    self.dlg2.tableWidget_3.setItem(r, c, QTableWidgetItem(str(vals[r][c])))
                    c = c + 1
                r = r + 1
            csvf.close()
            
    
    def run(self):
        
        
        # show the dialog
        self.dlg.show()
        
        
        
        # Run the dialog event loop
        #result = self.dlg.exec_()
        # See if OK was pressed
    
    def run2(self):
        self.dlg2.show()
"""        
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
"""