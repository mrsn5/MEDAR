import sys

from PyQt5 import Qt
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QFileDialog, QAction, QLabel, QSlider, QPushButton, QLineEdit
from qtpy import QtCore
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from volume_renderer import *


class MainWindow(Qt.QMainWindow):

    def readData(self, folder):
        self.folder = folder
        self.vr = VolumeRenderer(folder)
        self.scale = list(self.vr.raw_scans[0].PixelSpacing) + [self.vr.raw_scans[0].SliceThickness]

    def preprocess(self, newScale, extract, mask, seed=None):
        if mask is not None:
            self.vr.mask_scans(mask)

        if extract is not None:
            a, b = extract
            self.vr.extract(a, b)

        if seed is not None:
            self.vr.segmentation(seed)

        if newScale is not None:
            self.scans = blockwise_average_3D(self.vr.scans, newScale)
        else:
            self.scans = blockwise_average_3D(self.vr.scans, (1, 1, 1))


    def directVolumeRenader(self, newScale=(1,1,1), extract=None, mask=None, seed=None):
        self.preprocess(newScale, extract, mask, seed)
        self.shape = self.scans.shape
        if self.l7 is not None:
            self.l7.setText("Зерно (x,y,z) [0-%d][0-%d][0-%d]" % self.shape[::-1])
        print('directVolumeRenader')

    def indirectVolumeRenader(self, threshold=-300, newScale=(2,2,2), extract=None, mask=None):
        self.preprocess(newScale, extract, mask)
        self.vr.make_mesh(threshold=threshold)
        self.vr.scale(self.scale)
        self.vr.save('model')
        print('saved')
        return 'data/model.stl'

    def initReader(self):
        [h, w, z] = self.scans.shape

        data_string = self.scans.tostring()
        self.reader.CopyImportVoidPointer(data_string, len(data_string))
        self.reader.SetDataScalarTypeToDouble()
        self.reader.SetNumberOfScalarComponents(1)
        self.reader.SetDataExtent(0, z - 1, 0, w - 1, 0, h - 1)
        self.reader.SetWholeExtent(0, z - 1, 0, w - 1, 0, h - 1)
        sx, sy, sz = self.scale
        self.reader.SetDataSpacing(sx, sy, sz)

        self.planes = vtk.vtkPlanes()
        def ClipVolumeRender(obj, event):
            obj.GetPlanes(self.planes)
            self.volumeMapper.SetClippingPlanes(self.planes)

        self.boxWidget.SetInputConnection(self.reader.GetOutputPort())
        self.boxWidget.PlaceWidget()
        self.boxWidget.InsideOutOn()
        self.boxWidget.AddObserver("InteractionEvent", ClipVolumeRender)
        outlineProperty = self.boxWidget.GetOutlineProperty()
        outlineProperty.SetRepresentationToWireframe()
        outlineProperty.SetAmbient(1.0)
        outlineProperty.SetAmbientColor(1, 1, 1)
        outlineProperty.SetLineWidth(3)

        selectedOutlineProperty = self.boxWidget.GetSelectedOutlineProperty()
        selectedOutlineProperty.SetRepresentationToWireframe()
        selectedOutlineProperty.SetAmbient(1.0)
        selectedOutlineProperty.SetAmbientColor(1, 0, 0)
        selectedOutlineProperty.SetLineWidth(3)


    def resetIndirectModel(self, thresh):
        self.ren.Clear()
        self.ren.RemoveAllViewProps()

        volumeMapper = vtk.vtkContourFilter()
        self.initReader()
        volumeMapper.SetInputConnection(self.reader.GetOutputPort())
        volumeMapper.SetValue(0, thresh)
        skinNormals = vtk.vtkPolyDataNormals()
        skinNormals.SetInputConnection(volumeMapper.GetOutputPort())
        skinNormals.SetFeatureAngle(60.0)
        skinMapper = vtk.vtkPolyDataMapper()
        skinMapper.SetInputConnection(skinNormals.GetOutputPort())
        skinMapper.ScalarVisibilityOff()
        skin = vtk.vtkActor()
        skin.SetMapper(skinMapper)

        # An outline provides context around the data.
        outlineData = vtk.vtkOutlineFilter()
        outlineData.SetInputConnection(self.reader.GetOutputPort())
        mapOutline = vtk.vtkPolyDataMapper()
        mapOutline.SetInputConnection(outlineData.GetOutputPort())
        outline = vtk.vtkActor()
        outline.SetMapper(mapOutline)
        outline.GetProperty().SetColor(0, 0, 0)

        camera = vtk.vtkCamera()
        camera.SetViewUp(0, 0, 1)
        camera.SetPosition(0, -1, 0)
        camera.SetFocalPoint(0, 0, 0)
        camera.ComputeViewPlaneNormal()

        self.ren.AddActor(outline)
        self.ren.AddActor(skin)

        self.ren.SetActiveCamera(camera)
        self.ren.ResetCamera()
        camera.Dolly(1.5)

        self.ren.SetBackground(0.2, 0.2, 0.2)
        self.ren.ResetCameraClippingRange()

        self.ren.Render()
        self.vtkWidget.update()

    def resetDirectModel(self):
        self.ren.Clear()
        self.ren.RemoveAllViewProps()


        self.volumeMapper = vtk.vtkGPUVolumeRayCastMapper()
        self.initReader()
        self.volumeMapper.SetInputConnection(self.reader.GetOutputPort())
        self.volumeMapper.SetBlendModeToComposite()

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


        self.volumeProperty.SetColor(self.volumeColor)
        self.volumeProperty.SetScalarOpacity(self.volumeScalarOpacity)
        self.volumeProperty.SetGradientOpacity(self.volumeGradientOpacity)
        self.volumeProperty.SetInterpolationTypeToLinear()
        self.volumeProperty.ShadeOn()
        self.volumeProperty.SetAmbient(self.ambient)
        self.volumeProperty.SetDiffuse(self.diffuse)
        self.volumeProperty.SetSpecular(self.specular)

        self.volume = vtk.vtkVolume()
        self.volume.SetMapper(self.volumeMapper)
        self.volume.SetProperty(self.volumeProperty)

        camera = self.ren.GetActiveCamera()
        c = self.volume.GetCenter()
        camera.SetFocalPoint(c[0], c[1], c[2])
        camera.SetPosition(c[0] + 3000, c[1], c[2])
        camera.SetViewUp(0, 0, 1)

        outline = vtk.vtkOutlineFilter()
        outline.SetInputConnection(self.reader.GetOutputPort())
        outlineMapper = vtk.vtkPolyDataMapper()
        outlineMapper.SetInputConnection(outline.GetOutputPort())
        outlineActor = vtk.vtkActor()
        outlineActor.SetMapper(outlineMapper)



        self.ren.AddViewProp(self.volume)
        self.ren.AddActor(outlineActor)
        self.ren.AddVolume(self.volume)
        self.ren.SetBackground(0.5, 0.5, 0.5)
        self.ren.Render()
        self.vtkWidget.update()

    def initModel(self):
        try:
            self.readData(str(QFileDialog.getExistingDirectory(self, "Select Directory")))
        except:
            return

        self.directVolumeRenader()
        self.resetDirectModel()

    def __init__(self, parent = None):
        Qt.QMainWindow.__init__(self, parent)
        self.initModelParams()
        self.initUI()



    def initModelParams(self):
        self.vr = None
        self.volumeScalarOpacity = vtk.vtkPiecewiseFunction()
        self.volumeProperty = vtk.vtkVolumeProperty()
        self.setOpacity(0.05)
        self.reader = vtk.vtkImageImport()
        self.ambient, self.diffuse, self.specular = 0.5,0.5,0.5
        self.shape = (0,0,0)

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
        self.panelLayout.setAlignment(QtCore.Qt.AlignTop)


        self.onlyInt = QIntValidator()
        self.isoThresh = QLineEdit()
        self.isoThresh.setValidator(self.onlyInt)
        self.panelLayout.addWidget(self.isoThresh)

        self.b3 = QPushButton("Згенерувати ізоповерхню")
        self.panelLayout.addWidget(self.b3)
        self.b3.clicked.connect(self.isosurface)

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

        self.l2 = QLabel("Мінімальне значення")
        self.panelLayout.addWidget(self.l2)
        self.s2 = QSlider(QtCore.Qt.Horizontal)
        self.s2.setMinimum(-1000)
        self.s2.setMaximum(1000)
        self.s2.setValue(-500)
        self.s2.setTickPosition(QSlider.TicksBelow)
        self.s2.setTickInterval(100)
        self.panelLayout.addWidget(self.s2)
        self.s2.valueChanged.connect(self.opacityChanged)

        self.l3 = QLabel("Максимальне значення")
        self.panelLayout.addWidget(self.l3)
        self.s3 = QSlider(QtCore.Qt.Horizontal)
        self.s3.setMinimum(-1000)
        self.s3.setMaximum(1000)
        self.s3.setValue(1000)
        self.s3.setTickPosition(QSlider.TicksBelow)
        self.s3.setTickInterval(100)
        self.panelLayout.addWidget(self.s3)
        self.s3.valueChanged.connect(self.opacityChanged)



        self.l4 = QLabel("Ambient")
        self.panelLayout.addWidget(self.l4)
        self.s4 = QSlider(QtCore.Qt.Horizontal)
        self.s4.setMinimum(0)
        self.s4.setMaximum(100)
        self.s4.setValue(50)
        self.s4.setTickPosition(QSlider.TicksBelow)
        self.s4.setTickInterval(10)
        self.panelLayout.addWidget(self.s4)
        self.s4.valueChanged.connect(self.sceneChanged)

        self.l5 = QLabel("Diffuse")
        self.panelLayout.addWidget(self.l5)
        self.s5 = QSlider(QtCore.Qt.Horizontal)
        self.s5.setMinimum(0)
        self.s5.setMaximum(100)
        self.s5.setValue(50)
        self.s5.setTickPosition(QSlider.TicksBelow)
        self.s5.setTickInterval(10)
        self.panelLayout.addWidget(self.s5)
        self.s5.valueChanged.connect(self.sceneChanged)

        self.l6 = QLabel("Specular")
        self.panelLayout.addWidget(self.l6)
        self.s6 = QSlider(QtCore.Qt.Horizontal)
        self.s6.setMinimum(0)
        self.s6.setMaximum(100)
        self.s6.setValue(50)
        self.s6.setTickPosition(QSlider.TicksBelow)
        self.s6.setTickInterval(10)
        self.panelLayout.addWidget(self.s6)
        self.s6.valueChanged.connect(self.sceneChanged)

        self.l7 = QLabel("Зерно (x,y,z) [0-%d][0-%d][0-%d]" % self.shape[::-1])
        self.panelLayout.addWidget(self.l7)
        #
        self.seedPanel = Qt.QFrame()
        self.seedPanelLayout = Qt.QHBoxLayout()

        self.xLineEdit = QLineEdit()
        self.xLineEdit.setValidator(self.onlyInt)
        self.seedPanelLayout.addWidget(self.xLineEdit)
        self.yLineEdit = QLineEdit()
        self.yLineEdit.setValidator(self.onlyInt)
        self.seedPanelLayout.addWidget(self.yLineEdit)
        self.zLineEdit = QLineEdit()
        self.zLineEdit.setValidator(self.onlyInt)
        self.seedPanelLayout.addWidget(self.zLineEdit)

        self.seedPanel.setLayout(self.seedPanelLayout)
        self.panelLayout.addWidget(self.seedPanel)
        #


        self.b1 = QPushButton("Зерно")
        self.panelLayout.addWidget(self.b1)
        self.b1.clicked.connect(self.seed)

        self.b2 = QPushButton("Збросити")
        self.panelLayout.addWidget(self.b2)
        self.b2.clicked.connect(self.reset)


        self.panel.setLayout(self.panelLayout)
        self.vl.addWidget(self.panel)
        self.panel.setFixedWidth(300)
        #####

        self.frame.setLayout(self.vl)
        self.setCentralWidget(self.frame)

        self.boxWidget = vtk.vtkBoxWidget()
        self.boxWidget.SetInteractor(self.iren)
        self.boxWidget.SetPlaceFactor(1.0)

        self.show()
        self.iren.Initialize()
        self.iren.Start()



        load = QAction('Load', self)
        load.setShortcut('Ctrl+O')
        load.setStatusTip('Load images')
        load.triggered.connect(self.initModel)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(load)

    def opacityChanged(self):
        opacity = self.sl.value() / 100.0
        minValue = self.s2.value()
        maxValue = self.s3.value()
        self.setOpacity(opacity, minValue, maxValue)
        self.vtkWidget.update()

    def sceneChanged(self):
        self.ambient = self.s4.value() / 100.0
        self.diffuse = self.s5.value() / 100.0
        self.specular = self.s6.value() / 100.0
        self.volumeProperty.SetAmbient(self.ambient)
        self.volumeProperty.SetDiffuse(self.diffuse)
        self.volumeProperty.SetSpecular(self.specular)
        self.vtkWidget.update()

    def setOpacity(self, opacity, minValue=-500, maxValue=1000):
        print(opacity, minValue, maxValue)
        self.volumeScalarOpacity.RemoveAllPoints()
        self.volumeScalarOpacity.AddPoint(-1001, 0)
        self.volumeScalarOpacity.AddPoint(minValue, 0)
        if minValue < maxValue:
            self.volumeScalarOpacity.AddPoint(minValue+1, opacity)
            self.volumeScalarOpacity.AddPoint(maxValue-1, opacity)
        self.volumeScalarOpacity.AddPoint(maxValue, 0)
        self.volumeScalarOpacity.AddPoint(1001, 0)

    def seed(self):
        lines = [self.xLineEdit.text(), self.yLineEdit.text(), self.zLineEdit.text()]
        s = [ 0 if l == "" else int(l) for l in lines]
        if self.vr is not None:
            self.readData(self.folder)
            self.directVolumeRenader(seed=s)
            self.resetDirectModel()

    def reset(self):
        if self.vr is not None:
            self.resetDirectModel()

    def isosurface(self):
        if self.vr is not None:
            thresh = self.isoThresh.text()
            thresh = 0 if thresh == "" else int(thresh)
            self.resetIndirectModel(thresh)

if __name__ == "__main__":
    app = Qt.QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())