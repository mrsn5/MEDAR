from __future__ import print_function

import matplotlib.pyplot as plt
import SimpleITK as sitk
from volume_renderer import *
import cv2



vr = VolumeRenderer('data/fullbody1')
scan = vr.scans
x, y, z = scan.shape
scan = cv2.blur(scan, (7,7))
# print(scan.shape)
# norm = cv2.normalize(scan, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
# print(norm.shape)
# mask  = []
# for z in norm:
#     c = cv2.Canny(z, threshold1=8, threshold2=8)
#     m = cv2.morphologyEx(c, cv2.MORPH_CLOSE, np.ones((5,5), np.uint8))
#     mask.append(m)
# mask = np.array(mask, dtype=bool)
# np.save('data/morph', mask)
#
# rows, cols = 3, 3
# fig, ax = plt.subplots(rows, cols, figsize=[12, 12])
# N = len(mask)
# n = rows * cols
# for i in range(rows * cols):
#     ind = int(N * i / n)
#     ax[int(i / rows), int(i % rows)].set_title('slice %d' % ind)
#     ax[int(i / rows), int(i % rows)].imshow(mask[ind], cmap='gray')
#     ax[int(i / rows), int(i % rows)].axis('off')
# plt.show()

img_T1 = sitk.GetImageFromArray(scan)
img_T1_255 = sitk.Cast(sitk.RescaleIntensity(img_T1), sitk.sitkUInt8)
# img_T1 = sitk.CurvatureFlow(image1=img_T1, timeStep=0.125, numberOfIterations=10)

# for e in range(100):
# seed = (np.random.randint(0, x), np.random.randint(0, y), np.random.randint(0, z))[::-1]
seed = (250, 250, 104)
seg = sitk.Image(img_T1.GetSize(), sitk.sitkUInt8)
seg.CopyInformation(img_T1)
seg[seed] = 1
# seg = sitk.BinaryDilate(seg, 9)
v = img_T1[seed]
# print('e', e)
print('seed', seed)
print('v', v)

# -------------------
seg = sitk.ConnectedThreshold(image1=img_T1,
                              seedList=[seed],
                              lower=int(v-10),
                              upper=int(v+10),
                              replaceValue=1)

# -------------------
# feature_img = sitk.GradientMagnitudeRecursiveGaussian(img_T1, sigma=.5)
# speed_img = sitk.BoundedReciprocal(feature_img)
#
# fm_filter = sitk.FastMarchingBaseImageFilter()
# fm_filter.SetTrialPoints([seed])
# fm_filter.SetStoppingValue(1000)
# fm_img = fm_filter.Execute(speed_img)
# seg = sitk.Threshold(fm_img,
#                     lower=0.0,
#                     upper=fm_filter.GetStoppingValue(),
#                     outsideValue=fm_filter.GetStoppingValue()+1)

# -------------------
# seg = sitk.Image(img_T1.GetSize(), sitk.sitkUInt8)
# seg.CopyInformation(img_T1)
# seg[seed] = 1
# seg = sitk.BinaryDilate(seg, 3)
#
# stats = sitk.LabelStatisticsImageFilter()
# stats.Execute(img_T1, seg)
#
# factor = 3.5
# lower_threshold = stats.GetMean(1)-factor*stats.GetSigma(1)
# upper_threshold = stats.GetMean(1)+factor*stats.GetSigma(1)
# print(lower_threshold,upper_threshold)
#
# init_ls = sitk.SignedMaurerDistanceMap(seg, insideIsPositive=True, useImageSpacing=True)
#
# lsFilter = sitk.ThresholdSegmentationLevelSetImageFilter()
# lsFilter.SetLowerThreshold(lower_threshold)
# lsFilter.SetUpperThreshold(upper_threshold)
# lsFilter.SetMaximumRMSError(0.02)
# lsFilter.SetNumberOfIterations(1000)
# lsFilter.SetCurvatureScaling(.5)
# lsFilter.SetPropagationScaling(1)
# lsFilter.ReverseExpansionDirectionOn()
# ls = lsFilter.Execute(init_ls, sitk.Cast(img_T1, sitk.sitkFloat32))
# print(lsFilter)
#
# seg = ls
# -------------------

# seg = sitk.ConfidenceConnected(img_T1, seedList=[seed],
#                                     numberOfIterations=1,
#                                     multiplier=1,
#                                     initialNeighborhoodRadius=1,
#                                     replaceValue=1)

# -------------------
# r = sitk.LabelOverlay(img_T1_255, seg)
#
#
# nda = sitk.GetArrayFromImage(r)
s = sitk.GetArrayFromImage(seg)

kernel = np.ones((11,11),np.uint8)
s = cv2.morphologyEx(s, cv2.MORPH_CLOSE, kernel)

# s[s>50] = 1
# s = np.array(s, dtype=int)
print(np.min(s),np.max(s))

rows, cols = 5, 5
fig, ax = plt.subplots(rows, cols, figsize=[12, 12])
N = len(s)
n = rows * cols
for i in range(rows * cols):
    ind = int(N * i / n)
    ax[int(i / rows), int(i % rows)].set_title('slice %d' % ind)
    ax[int(i / rows), int(i % rows)].imshow(s[ind], cmap='gray')
    ax[int(i / rows), int(i % rows)].axis('off')
plt.show()




np.save('data/mask', s)
# seed (441, 194, 89) skin
# seed (72, 292, 163)
# seed (318, 150, 19) head