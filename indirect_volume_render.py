import sys
import vtk
from PyQt5 import QtCore, QtGui
from PyQt5 import Qt

from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

class MainWindow(Qt.QMainWindow):

    def __init__(self, parent = None):
        Qt.QMainWindow.__init__(self, parent)

        self.frame = Qt.QFrame()
        self.vl = Qt.QVBoxLayout()
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.vl.addWidget(self.vtkWidget)

        self.ren = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        reader = vtk.vtkDICOMImageReader()
        reader.SetDirectoryName('data/fullbody1')
        reader.Update()

        # The volume will be displayed by ray-cast alpha compositing.
        # A ray-cast mapper is needed to do the ray-casting, and a
        # compositing function is needed to do the compositing along the ray.
        volumeMapper = vtk.vtkGPUVolumeRayCastMapper()
        volumeMapper.SetInputConnection(reader.GetOutputPort())
        volumeMapper.SetBlendModeToComposite()

        # The color transfer function maps voxel intensities to colors.
        # It is modality-specific, and often anatomy-specific as well.
        # The goal is to one color for flesh (between 500 and 1000)
        # and another color for bone (1150 and over).
        volumeColor = vtk.vtkColorTransferFunction()
        volumeColor.AddRGBPoint(-1000, 0.00, 0.00, 0.00)
        volumeColor.AddRGBPoint(-600, 0.76, 0.41, 0.32)
        volumeColor.AddRGBPoint(-400, 0.76, 0.41, 0.32)
        volumeColor.AddRGBPoint(-100, 0.76, 0.65, 0.45)
        volumeColor.AddRGBPoint(-60, 0.76, 0.65, 0.45)
        volumeColor.AddRGBPoint(40, 0.40, 0.00, 0.00)
        volumeColor.AddRGBPoint(80, 0.60, 0.00, 0.00)
        volumeColor.AddRGBPoint(400, 1.00, 1.00, 0.90)
        volumeColor.AddRGBPoint(1000, 1.00, 1.00, 0.90)

        # The opacity transfer function is used to control the opacity
        # of different tissue types.
        volumeScalarOpacity = vtk.vtkPiecewiseFunction()
        volumeScalarOpacity.AddPoint(-1001, 0)
        volumeScalarOpacity.AddPoint(-1000, 0.05)
        volumeScalarOpacity.AddPoint(1000, 0.05)
        volumeScalarOpacity.AddPoint(1001, 0)

        # The gradient opacity function is used to decrease the opacity
        # in the "flat" regions of the volume while maintaining the opacity
        # at the boundaries between tissue types.  The gradient is measured
        # as the amount by which the intensity changes over unit distance.
        # For most medical data, the unit distance is 1mm.
        volumeGradientOpacity = vtk.vtkPiecewiseFunction()
        volumeGradientOpacity.AddPoint(0, 0.0)
        volumeGradientOpacity.AddPoint(90, 0.5)
        volumeGradientOpacity.AddPoint(100, 1.0)

        # The VolumeProperty attaches the color and opacity functions to the
        # volume, and sets other volume properties.  The interpolation should
        # be set to linear to do a high-quality rendering.  The ShadeOn option
        # turns on directional lighting, which will usually enhance the
        # appearance of the volume and make it look more "3D".  However,
        # the quality of the shading depends on how accurately the gradient
        # of the volume can be calculated, and for noisy data the gradient
        # estimation will be very poor.  The impact of the shading can be
        # decreased by increasing the Ambient coefficient while decreasing
        # the Diffuse and Specular coefficient.  To increase the impact
        # of shading, decrease the Ambient and increase the Diffuse and Specular.
        volumeProperty = vtk.vtkVolumeProperty()
        volumeProperty.SetColor(volumeColor)
        volumeProperty.SetScalarOpacity(volumeScalarOpacity)
        volumeProperty.SetGradientOpacity(volumeGradientOpacity)
        volumeProperty.SetInterpolationTypeToLinear()
        volumeProperty.ShadeOn()
        volumeProperty.SetAmbient(0.9)
        volumeProperty.SetDiffuse(0.6)
        volumeProperty.SetSpecular(0.2)

        # The vtkVolume is a vtkProp3D (like a vtkActor) and controls the position
        # and orientation of the volume in world coordinates.
        volume = vtk.vtkVolume()
        volume.SetMapper(volumeMapper)
        volume.SetProperty(volumeProperty)

        self.ren.AddViewProp(volume)

        camera = self.ren.GetActiveCamera()
        c = volume.GetCenter()
        camera.SetFocalPoint(c[0], c[1], c[2])
        camera.SetPosition(c[0] + 3000, c[1], c[2])
        camera.SetViewUp(0, 0, -1)




        outline = vtk.vtkOutlineFilter()
        outline.SetInputConnection(reader.GetOutputPort())
        outlineMapper = vtk.vtkPolyDataMapper()
        outlineMapper.SetInputConnection(outline.GetOutputPort())
        outlineActor = vtk.vtkActor()
        outlineActor.SetMapper(outlineMapper)

        boxWidget = vtk.vtkBoxWidget()
        boxWidget.SetInteractor(self.vtkWidget)
        boxWidget.SetPlaceFactor(1.0)

        # Add the actors to the renderer, set the background and size
        self.ren.AddActor(outlineActor)
        self.ren.AddVolume(volume)

        self.ren.SetBackground(0, 0, 0)

        # When interaction starts, the requested frame rate is increased.
        def StartInteraction(obj, event):
            global renWin
            renWin.SetDesiredUpdateRate(10)

        # When interaction ends, the requested frame rate is decreased to
        # normal levels. This causes a full resolution render to occur.
        def EndInteraction(obj, event):
            global renWin
            renWin.SetDesiredUpdateRate(0.001)

        # The implicit function vtkPlanes is used in conjunction with the
        # volume ray cast mapper to limit which portion of the volume is
        # volume rendered.
        planes = vtk.vtkPlanes()

        def ClipVolumeRender(obj, event):
            global planes, volumeMapper
            obj.GetPlanes(planes)
            volumeMapper.SetClippingPlanes(planes)

        # Place the interactor initially. The output of the reader is used to
        # place the box widget.
        boxWidget.SetInputConnection(reader.GetOutputPort())
        boxWidget.PlaceWidget()
        boxWidget.InsideOutOn()
        boxWidget.AddObserver("StartInteractionEvent", StartInteraction)
        boxWidget.AddObserver("InteractionEvent", ClipVolumeRender)
        boxWidget.AddObserver("EndInteractionEvent", EndInteraction)

        outlineProperty = boxWidget.GetOutlineProperty()
        outlineProperty.SetRepresentationToWireframe()
        outlineProperty.SetAmbient(1.0)
        outlineProperty.SetAmbientColor(1, 1, 1)
        outlineProperty.SetLineWidth(3)

        selectedOutlineProperty = boxWidget.GetSelectedOutlineProperty()
        selectedOutlineProperty.SetRepresentationToWireframe()
        selectedOutlineProperty.SetAmbient(1.0)
        selectedOutlineProperty.SetAmbientColor(1, 0, 0)
        selectedOutlineProperty.SetLineWidth(3)






        self.frame.setLayout(self.vl)
        self.setCentralWidget(self.frame)

        self.show()
        self.iren.Initialize()
        self.iren.Start()


if __name__ == "__main__":
    app = Qt.QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())