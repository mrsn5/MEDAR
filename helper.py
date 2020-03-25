import numpy as np
from math import cos, sin
import matplotlib.pyplot as plt

def rotation_matrix(v, alpha):
    v = np.array(v)
    v = v / np.linalg.norm(v)
    a, b, c = v
    K = 1 - cos(alpha)
    return np.array([
        [a * a * K + cos(alpha), a * b * K - c * sin(alpha), a * c * K + b * sin(alpha), 0],
        [a * b * K + c * sin(alpha), b * b * K + cos(alpha), b * c * K - a * sin(alpha), 0],
        [a * c * K - b * sin(alpha), b * c * K + a * sin(alpha), c * c * K + cos(alpha), 0],
        [0, 0, 0, 1]
    ])


def translation_matrix(t):
    x, y, z = t
    return np.array([
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1]
    ])


def scale_matrix(s, origin=[0, 0, 0]):
    x, y, z = s
    x0, y0, z0 = origin
    return np.array([
        [x, 0, 0, x0 * (1 - x)],
        [0, y, 0, y0 * (1 - y)],
        [0, 0, z, z0 * (1 - z)],
        [0, 0, 0, 1]
    ])


def transform(verts, matrix):
    new_verts = []
    matrix = np.array(matrix)
    for v in verts:
        v = np.append(v, np.array([1]))
        nv = matrix.dot(np.array(v).T)[:-1].tolist()
        new_verts.append(nv)
    return np.array(new_verts)


def blockwise_average_3D(A, S):
    m, n, r = np.array(A.shape) // S
    return A.reshape(m, S[0], n, S[1], r, S[2]).mean((1, 3, 5))


def view_sample(model):
    rows, cols = 5, 5
    fig, ax = plt.subplots(rows, cols, figsize=[12, 12])
    N = len(model)
    n = rows * cols
    for i in range(rows * cols):
        ind = int(N * i / n)
        ax[int(i / rows), int(i % rows)].set_title('зріз %d' % ind)
        ax[int(i / rows), int(i % rows)].imshow(model[ind], cmap='gray')
        ax[int(i / rows), int(i % rows)].axis('off')
    plt.show()
