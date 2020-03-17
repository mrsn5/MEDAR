import vtk
from vtk.util.misc import vtkGetDataRoot

ren = vtk.vtkRenderer()
renWin = vtk.vtkRenderWindow()
renWin.AddRenderer(ren)
iren = vtk.vtkRenderWindowInteractor()
iren.SetRenderWindow(renWin)

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
volumeColor.AddRGBPoint(-600,  0.76, 0.41, 0.32)
volumeColor.AddRGBPoint(-400,  0.76, 0.41, 0.32)
volumeColor.AddRGBPoint(-100,  0.76, 0.65, 0.45)
volumeColor.AddRGBPoint(-60,   0.76, 0.65, 0.45)
volumeColor.AddRGBPoint(40,    0.40, 0.00, 0.00)
volumeColor.AddRGBPoint(80,    0.60, 0.00, 0.00)
volumeColor.AddRGBPoint(400,   1.00, 1.00, 0.90)
volumeColor.AddRGBPoint(1000,  1.00, 1.00, 0.90)

# The opacity transfer function is used to control the opacity
# of different tissue types.
volumeScalarOpacity = vtk.vtkPiecewiseFunction()
volumeScalarOpacity.AddPoint(-1001, 0)
volumeScalarOpacity.AddPoint(-1000, 0.05)
volumeScalarOpacity.AddPoint(1000,  0.05)
volumeScalarOpacity.AddPoint(1001,  0)

# The gradient opacity function is used to decrease the opacity
# in the "flat" regions of the volume while maintaining the opacity
# at the boundaries between tissue types.  The gradient is measured
# as the amount by which the intensity changes over unit distance.
# For most medical data, the unit distance is 1mm.
volumeGradientOpacity = vtk.vtkPiecewiseFunction()
volumeGradientOpacity.AddPoint(0,   0.0)
volumeGradientOpacity.AddPoint(90,  0.5)
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
volumeProperty.SetAmbient(0.4)
volumeProperty.SetDiffuse(0.6)
volumeProperty.SetSpecular(0.2)

# The vtkVolume is a vtkProp3D (like a vtkActor) and controls the position
# and orientation of the volume in world coordinates.
volume = vtk.vtkVolume()
volume.SetMapper(volumeMapper)
volume.SetProperty(volumeProperty)

# Finally, add the volume to the renderer
ren.AddViewProp(volume)

# Set up an initial view of the volume.  The focal point will be the
# center of the volume, and the camera position will be 400mm to the
# patient's left (which is our right).
camera =  ren.GetActiveCamera()
c = volume.GetCenter()
camera.SetFocalPoint(c[0], c[1], c[2])
camera.SetPosition(c[0] + 400, c[1], c[2])
camera.SetViewUp(0, 0, -1)

# Increase the size of the render window
renWin.SetSize(640, 480)

# Interact with the data.
iren.Initialize()
renWin.Render()
iren.Start()