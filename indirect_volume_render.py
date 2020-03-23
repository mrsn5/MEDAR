import sys

from PyQt5 import Qt
from PyQt5.QtWidgets import QFileDialog, QAction, QLabel, QSlider
from qtpy import QtCore
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from volume_renderer import *


class MainWindow(Qt.QMainWindow):

    def readData(self, folder):
        self.folder = folder
        self.vr = VolumeRenderer(folder)
        self.scale = list(self.vr.raw_scans[0].PixelSpacing) + [self.vr.raw_scans[0].SliceThickness]

    def preprocess(self, newScale, extract, mask):
        if mask:
            self.vr.mask_scans(mask)
        if extract:
            self.vr.extract(extract)
        self.scans = blockwise_average_3D(self.vr.scans, newScale)

    def directVolumeRenader(self, newScale=(1,1,1), extract=None, mask=None):
        self.preprocess(newScale, extract, mask)

    def indirectVolumeRenader(self, threshold=-300, newScale=(1,1,1), extract=None, mask=None):
        self.preprocess(newScale, extract, mask)
        vr.make_mesh(threshold=threshold)
        vr.scale(self.scale)
        vr.save('models/model')
        print('saved')

    def initModel(self):
        self.ren.Clear()
        try:
            self.readData(str(QFileDialog.getExistingDirectory(self, "Select Directory")))
        except:
            return

        self.directVolumeRenader()

        [h, w, z] = self.scans.shape
        reader = vtk.vtkImageImport()
        data_string = self.scans.tostring()
        reader.CopyImportVoidPointer(data_string, len(data_string))
        reader.SetDataScalarTypeToDouble()
        reader.SetNumberOfScalarComponents(1)
        reader.SetDataExtent(0, z - 1, 0, w - 1, 0, h - 1)
        reader.SetWholeExtent(0, z - 1, 0, w - 1, 0, h - 1)

        sx, sy, sz = self.scale
        reader.SetDataSpacing(sx, sy, sz)

        volumeMapper = vtk.vtkGPUVolumeRayCastMapper()
        volumeMapper.SetInputConnection(reader.GetOutputPort())
        volumeMapper.SetBlendModeToComposite()

        self.volumeColor = vtk.vtkColorTransferFunction()
        self.volumeColor.AddRGBPoint(-1000, 0.00, 0.00, 0.00)
        self.volumeColor.AddRGBPoint(-600, 0.76, 0.41, 0.32)
        self.volumeColor.AddRGBPoint(-400, 0.76, 0.41, 0.32)
        self.volumeColor.AddRGBPoint(-100, 0.76, 0.65, 0.45)
        self.volumeColor.AddRGBPoint(-60, 0.76, 0.65, 0.45)
        self.volumeColor.AddRGBPoint(40, 0.40, 0.00, 0.00)
        self.volumeColor.AddRGBPoint(80, 0.60, 0.00, 0.00)
        self.volumeColor.AddRGBPoint(400, 1.00, 1.00, 0.90)
        self.volumeColor.AddRGBPoint(1000, 1.00, 1.00, 0.90)


        self.volumeGradientOpacity = vtk.vtkPiecewiseFunction()
        self.volumeGradientOpacity.AddPoint(0, 0.0)
        self.volumeGradientOpacity.AddPoint(90, 0.5)
        self.volumeGradientOpacity.AddPoint(100, 1.0)

        self.volumeProperty = vtk.vtkVolumeProperty()
        self.volumeProperty.SetColor(self.volumeColor)
        self.volumeProperty.SetScalarOpacity(self.volumeScalarOpacity)
        self.volumeProperty.SetGradientOpacity(self.volumeGradientOpacity)
        self.volumeProperty.SetInterpolationTypeToLinear()
        self.volumeProperty.ShadeOn()
        self.volumeProperty.SetAmbient(0.9)
        self.volumeProperty.SetDiffuse(0.6)
        self.volumeProperty.SetSpecular(0.2)

        self.volume = vtk.vtkVolume()
        self.volume.SetMapper(volumeMapper)
        self.volume.SetProperty(self.volumeProperty)

        camera = self.ren.GetActiveCamera()
        c = self.volume.GetCenter()
        camera.SetFocalPoint(c[0], c[1], c[2])
        camera.SetPosition(c[0] + 3000, c[1], c[2])
        camera.SetViewUp(0, 0, -1)

        outline = vtk.vtkOutlineFilter()
        outline.SetInputConnection(reader.GetOutputPort())
        outlineMapper = vtk.vtkPolyDataMapper()
        outlineMapper.SetInputConnection(outline.GetOutputPort())
        outlineActor = vtk.vtkActor()
        outlineActor.SetMapper(outlineMapper)

        self.ren.AddViewProp(self.volume)
        self.ren.AddActor(outlineActor)
        self.ren.AddVolume(self.volume)
        self.ren.SetBackground(0, 0, 0)


    def __init__(self, parent = None):
        Qt.QMainWindow.__init__(self, parent)
        self.initUI()
        self.initModelParams()


    def initModelParams(self):
        self.volumeScalarOpacity = vtk.vtkPiecewiseFunction()
        self.setOpacity(0.05)

    def initUI(self):
        self.frame = Qt.QFrame()
        self.vl = Qt.QHBoxLayout() # QVBoxLayout()

        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.vl.addWidget(self.vtkWidget)
        self.ren = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        # Panel
        self.panel = Qt.QFrame()
        self.panelLayout = Qt.QVBoxLayout()

        self.l1 = QLabel("Прозорість")
        self.panelLayout.addWidget(self.l1)

        self.sl = QSlider(QtCore.Qt.Horizontal)

        self.sl.setMinimum(1)
        self.sl.setMaximum(100)
        self.sl.setValue(5)
        self.sl.setTickPosition(QSlider.TicksBelow)
        self.sl.setTickInterval(10)

        self.panelLayout.addWidget(self.sl)
        self.sl.valueChanged.connect(self.opacityChanged)

        self.panel.setLayout(self.panelLayout)
        self.vl.addWidget(self.panel)
        self.panel.setFixedWidth(300)
        #####

        self.frame.setLayout(self.vl)
        self.setCentralWidget(self.frame)

        self.show()
        self.iren.Initialize()
        self.iren.Start()


        exitAct = QAction('Load', self)
        exitAct.setShortcut('Ctrl+O')
        exitAct.setStatusTip('Load images')
        exitAct.triggered.connect(self.initModel)

        self.statusBar()

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(exitAct)

    def opacityChanged(self):
        opacity = self.sl.value() / 100.0
        print(opacity)
        self.setOpacity(opacity)


    def setOpacity(self, opacity):
        print(opacity)
        self.volumeScalarOpacity.RemoveAllPoints()
        self.volumeScalarOpacity.AddPoint(-1000, 0)
        self.volumeScalarOpacity.AddPoint(-500, opacity)
        self.volumeScalarOpacity.AddPoint(1000, opacity)
        self.volumeScalarOpacity.AddPoint(1001, 0)

if __name__ == "__main__":
    app = Qt.QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())