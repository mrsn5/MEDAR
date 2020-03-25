from __future__ import print_function

import matplotlib.pyplot as plt
import SimpleITK as sitk
from volume_renderer import *
import cv2


class Segmentator:
    def __init__(self, model, blur=True):
        if blur:
            self.model = cv2.blur(model, (11, 11))
        else:
            self.model = model
        self.sitkModel = sitk.GetImageFromArray(self.model)
        print(self.sitkModel.GetSize())

    def regionGrow(self, seed, close=True):
        seg = sitk.Image(self.sitkModel.GetSize(), sitk.sitkUInt8)
        seg.CopyInformation(self.sitkModel)
        seg[seed] = 1
        v = self.sitkModel[seed]
        seg = sitk.ConnectedThreshold(image1=self.sitkModel,
                                      seedList=[seed],
                                      lower=int(v - 10),
                                      upper=int(v + 10),
                                      replaceValue=1)
        s = sitk.GetArrayFromImage(seg)
        if close:
            kernel = np.ones((11, 11), np.uint8)
            s = cv2.morphologyEx(s, cv2.MORPH_CLOSE, kernel)
        return np.array(s, dtype=bool)


if __name__ == "__main__":

    vr = VolumeRenderer('data/brain1')
    s = vr.scans
    print(np.min(s), np.max(s))
    s = vr.segmentation([200,200,100])
    view_sample(s)
