import pydicom as dicom
import os

import matplotlib.pyplot as plt
import pydicom as dicom
import scipy.ndimage
import vtk
from skimage import measure
from stl import mesh as M
from vtk.util import numpy_support
from helper import *


class VolumeRenderer:
    def __init__(self, scans_dir):
        self.scans_dir = scans_dir
        self.raw_scans = self.load_scans(scans_dir)[::-1]
        self.scans = self.get_pixels_hu(self.raw_scans)
        self.vtk_data = numpy_support.numpy_to_vtk(self.scans.ravel(), deep=True, array_type=vtk.VTK_FLOAT)

    def load_scans(self, scans_dir):
        slices = [dicom.read_file(scans_dir + '/' + s) for s in os.listdir(scans_dir)]
        slices.sort(key=lambda x: int(x.InstanceNumber))
        try:
            slice_thickness = np.abs(slices[0].ImagePositionPatient[2] - slices[1].ImagePositionPatient[2])
        except:
            slice_thickness = np.abs(slices[0].SliceLocation - slices[1].SliceLocation)

        for s in slices:
            s.SliceThickness = slice_thickness
        return slices

    def get_pixels_hu(self, scans):
        image = np.stack([s.pixel_array for s in scans])
        image = image.astype(np.int16)
        intercept = -1000
        slope = 1
        if slope != 1:
            image = slope * image.astype(np.float64)
            image = image.astype(np.int16)
        image += np.int16(intercept)
        return np.array(image, dtype=np.int16)

    def mask_scans(self, mask):
        mask = np.array(mask, dtype=bool)
        self.scans[~mask] = -1000

    def extract(self, alpha, beta):
        self.scans[alpha > self.scans] = -1000
        self.scans[beta < self.scans] = -1000

    def sample_view(self, rows=3, cols=3, start_with=0):
        fig, ax = plt.subplots(rows, cols, figsize=[12, 12])
        N = len(self.scans)
        n = rows * cols
        for i in range(rows * cols):
            ind = int(start_with + N * i / n)
            ax[int(i / rows), int(i % rows)].set_title('slice %d' % ind)
            ax[int(i / rows), int(i % rows)].imshow(self.scans[ind], cmap='gray')
            ax[int(i / rows), int(i % rows)].axis('off')
        plt.show()

    def histogram(self):
        plt.hist(self.scans.flatten(), bins=50, color='c')
        plt.xlabel("Hounsfield Units (HU)")
        plt.ylabel("Frequency")
        plt.show()

    def resample(self, new_spacing=[1, 1, 1]):
        print("Start resampling")
        # Determine current pixel spacing
        spacing = map(float, ([self.raw_scans[0].SliceThickness] + list(self.raw_scans[0].PixelSpacing)))
        spacing = np.array(list(spacing))
        if spacing[0] == 0.0:
            spacing[0] = spacing[1] * 2
        resize_factor = spacing / new_spacing
        new_real_shape = self.scans.shape * resize_factor
        new_shape = np.round(new_real_shape)
        real_resize_factor = new_shape / self.scans.shape
        new_spacing = spacing / real_resize_factor

        self.scans = scipy.ndimage.interpolation.zoom(self.scans, real_resize_factor)
        print(new_spacing) #

    def make_mesh(self, threshold=600, step_size=1):
        print("Transposing surface")
        p = self.scans.transpose(2, 1, 0)
        print("Calculating surface")
        self.verts, self.faces, self.norm, self.val = measure.marching_cubes_lewiner(p, threshold, step_size=step_size,
                                                                 allow_degenerate=True)

    def scale(self, size):
        if self.verts is None:
            self.make_mesh()
        matrix = scale_matrix(size)
        self.verts = transform(self.verts, matrix)

    def save(self, filename='model'):
        model = M.Mesh(np.zeros(self.faces.shape[0], dtype=M.Mesh.dtype))
        for i, f in enumerate(self.faces):
            for j in range(3):
                model.vectors[i][j] = self.verts[f[j], :]
        model.save('data/' + filename + '.stl')


if __name__ == "__main__":

    vr = VolumeRenderer('data/fullbody1')
    # vr.sample_view()
    # vr.histogram()
    print("Slice Thickness: %f" % vr.raw_scans[0].SliceThickness)
    print("Pixel Spacing (row, col): (%f, %f) " % (vr.raw_scans[0].PixelSpacing[0], vr.raw_scans[0].PixelSpacing[1]))
    scale = list(vr.raw_scans[0].PixelSpacing) + [vr.raw_scans[0].SliceThickness]
    print(scale)

    # №№№№№
    # vr.mask_scans(np.load('data/morph.npy'))
    vr.mask_scans(np.load('data/mask.npy'))
    # №№№№№
    # vr.extract(40, 60)
    #№№№№№

    vr.scans = blockwise_average_3D(vr.scans, (1, 1, 1))
    # vr.resample()
    np.save('data/inside', vr.scans)
    # vr.sample_view()
    print(vr.scans.shape)

    # vr.make_mesh(threshold=-300)
    # vr.scale(scale)
    # vr.save('models/fullbody1')
    print('done')

