## Standard Libraries ##
import sys
import os

## Numerical Libraries ##
import numpy as np

## Local Imports ##
cur_dir = os.path.dirname(__file__)
sys.path.insert(1,os.path.join(cur_dir))
sys.path.insert(1,os.path.join(cur_dir,'..','tools'))

import geometric_utilities as util
from mesh_class import Mesh


''' ======================================================================================================= '''
    ###                                        Filtering                                                ###
''' ======================================================================================================= '''


def pow(x):
    return 2.0**(x)


def gaussian_kernel(x, sigma):
    K  = np.exp(-0.5*(x/sigma)**2)
    return K


def product_manifold_kernel(gx, gy, ix, iy, sigma):
    Kx =  gaussian_kernel(gx, sigma)
    Ky =  gaussian_kernel(gy, sigma)
    K  =  Kx[:,ix].dot(Ky[:,iy].T)
    return K / K.max()


def product_manifold_kernel(gx, gy, ix, iy, sigma):
    Kx =  gaussian_kernel(gx, sigma)
    Ky =  gaussian_kernel(gy, sigma)
    K  =  Kx[:,ix].dot(Ky[:,iy].T)
    return K / K.max()


def product_manifold_filter_correspondence(assignment_functor, gx, gy, i, j, sigma = .13, gamma = 1, iterations = 1):
    for _ in range(iterations):
        P = product_manifold_kernel(gx, gy, i, j, sigma)
        i,j = assignment_functor(P)
        sigma *= gamma
    return i,j


def product_manifold_filter_assignment(assignment_functor, gx, gy, P, sigma = .13, gamma = 1, iterations = 1):
    i,j = assignment_functor(P)
    return product_manifold_filter_correspondence(assignment_functor, gx, gy, i, j, sigma, gamma, iterations)

''' ======================================================================================================= '''
    ###                                           End                                                   ###
''' ======================================================================================================= '''


if __name__ == '__main__':
    pass
