## Python imports
import os
import sys
import math
from typing import List

## Numerical
import numpy as np
from   scipy.sparse.linalg import spsolve, eigsh
from scipy.sparse import csr_matrix, lil_matrix, diags
## Mesh and Graphics
import igl

# Local imports

import geometric_utilities as util


''' ================================================================================= '''
    ##################           Mesh Class Definition             ##################
''' ================================================================================= '''


class Mesh:

    ### ================================================ ###
    '''                 Start of Class                   '''
    ### ================================================ ###

    def __init__(self, v, f = np.array([]), g = np.array([]), k = 100, type = ''):
        self.__v  =  v
        self.__f  =  f
        self.__g  =  g
        self.__k  =  k
        self.__l  =  np.array([])
        self.__mass  =  np.array([])
        self.__normals  =  np.array([])
        self.__eigen    =  [np.array([]) for _ in range(2)]
        self.__scalars  =  {}
        self.__type  =  type


    def __getitem__(self, idx):
        if ( idx.size == self.N() ):
            v,f = util.reorder_mesh(self.v, self.f, idx)
        else:
            v = self.v[idx]
            f = np.array([])

        g = np.array([]) if (self.__g.size == 0) else self.g[idx][:,idx]
        evals,evecs = self.eigen
        res =  Mesh(v, f, g = g, k = self.k, type = self.type)
        for fn in self.scalars:
            res.scalars[fn] = self.scalars[fn][idx].copy()
        return res


    def copy(self):
        res = Mesh(v = self.__v.copy(), f = self.__f.copy(), g = self.__g.copy(), k = self.__k, type = self.__type)
        res.mass  = self.__mass.copy()
        res.normals = self.__normals.copy()
        res.eigen = [e.copy() for e in self.__eigen]
        for fn in self.scalars:
            res.scalars[fn] = self.scalars[fn].copy()
        return res


    ### ================================================ ###
    '''                     Properties                   '''
    ### ================================================ ###

    def area(self):
        return util.area(self.v, self.f)

    def N(self):
        return self.__v.shape[0]

    ### ================================================ ###
    '''                 Getters and Setters              '''
    ### ================================================ ###

    @property
    def v(self):
        return self.__v

    @v.setter
    def v(self, v):
        self.__v = v

    @property
    def f(self):
        return self.__f

    @f.setter
    def f(self, f):
        self.__f = f

    @property
    def type(self):
        return self.__type

    @property
    def scalars(self):
        return self.__scalars

    @scalars.setter
    def scalars(self, scalars):
        self.__scalars = scalars

    @property
    def k(self):
        return self.__k

    @k.setter
    def k(self, k):
        self.__eigen = [e[...,:k] for e in self.__eigen] if (k<=self.__k) else [np.array([]) for _ in range(2)]
        self.__k = k

    @property
    def g(self):
        if (self.__g.size == 0):
            if (self.N() <= 500):
                self.__g = util.geodesicMatrix(self.v, self.f)
            else:
                _,v,f,_,i = util.vedo_decimate(self.v, self.f, N = 500)
                g         = util.geodesicMatrix(v,f)
                self.__g  = util.extrapolate_geodesic_matrix(v, self.v, g, f)
        return self.__g

    @g.setter
    def g(self, g):
        self.__g = g

    @property
    def gaussian(self):
        if (self.__gaussian.size == 0):
            self.__gaussian = util.gaussianCurvature(self.v, self.f)
        return self.__gaussian

    @gaussian.setter
    def gaussian(self, gaussian):
        self.__gaussian = gaussian

    @property
    def normals(self):
        if (self.__normals.size == 0):
            self.__normals = igl.per_vertex_normals(self.__v, self.__f, weighting = 0)
        return self.__normals

    @normals.setter
    def normals(self, normals):
        self.__normals = normals

    @property
    def eigen(self):
        if any([e.size == 0 for e in self.__eigen]):
            self.__eigen = util.laplace_eigen_decomposition(self.l, self.mass, self.k)
        return self.__eigen

    @eigen.setter
    def eigen(self, eigen):
        self.__eigen = eigen

    @property
    def mass(self):
        if (self.__mass.size == 0):
            self.__mass = igl.massmatrix(self.__v, self.__f, igl.MASSMATRIX_TYPE_VORONOI)
        return self.__mass

    @mass.setter
    def mass(self, mass):
        self.__mass = mass

    @property
    def l(self):
        if (self.__l.size == 0):
            self.__l = igl.cotmatrix(self.v, self.f)
        return self.__l

    @l.setter
    def l(self, l):
        self.__l = l


    ### ================================================ ###
    '''                Scalar Conversion                 '''
    ### ================================================ ###


    def pointwise_2_vector(self, scalar, k = -1):
        evecs = self.mass @ self.eigen[-1]
        if 0 < k:
            evecs = evecs[:,:k]
        return evecs.T @ scalar

    def vector_2_pointwise(self, vector):
        _,evecs = self.eigen
        k = vector.shape[0]
        return evecs[:,:k] @ vector

    def filter(self, scalar, k=-1):
        s = self.pointwise_2_vector(scalar,k)
        return self.vector_2_pointwise(s)

    def filter_array(self, array, k=-1):
        array = self.filter(array, k=k)
        return self.filter(array.T, k=k).T

    def dirac_deltas(self, i, k = -1):
        x = np.zeros((self.N(), i.size))
        j = np.arange(i.size)
        x[i,j] = 1
        return self.pointwise_2_vector(x,k)

    ### ================================================ ###
    '''                    Resampling                    '''
    ### ================================================ ###

    def decimate(self, N = None, frac = None):
        v,f = [x.copy() for x in (self.v,self.f)]
        _,v,f,_,idx = util.vedo_decimate(v, f, N = N, frac = frac) #igl.decimate(self.v, self.f, target)
        g = np.array([]) if (self.__g.size == 0) else self.g[idx][:,idx].copy()
        res =  Mesh(v, f, g = g, k = self.k, type = self.type)
        for fn in self.scalars:
            res.scalars[fn] = self.scalars[fn][idx].copy()
        return res, idx

    def upsample(self, target):
        v,f = [x.copy() for x in (self.v,self.f)]
        idx: np.ndarray
        while (v.shape[0] < target):
            v,f,idx = util.vedo_subdivide(v, f)
        g = util.extrapolate_geodesic_matrix(self.v, v, self.g, self.f)
        res = Mesh(v,f, g=g, k=self.k, type=self.type)
        return res,idx

    ### ================================================ ###
    '''                Inplace Modifiers                 '''
    ### ================================================ ###

    def scale(self, factor):
        self.__v *= factor
        return self

    def rotate(self, R):
        self.__v =  self.v @ R
        return self

    def shift(self, dx, dy, dz):
        self.__v += np.array([dx,dy,dz], dtype = self.__v.dtype)
        return self

    def centre(self):
        self.__v -= np.mean(self.v, axis = 0)
        return self

    def normalise(self):
        norm = np.sqrt(self.area())
        self.__v /= norm
        self.__g /= norm
        return self

    ### ================================================ ###
    '''                     Display                      '''
    ### ================================================ ###


    def display(self, **kwargs):
        import vedo as vp
        msh = self.vedo()

        if 'scalar' in kwargs:
            s = kwargs['scalar']
            if isinstance(s, np.ndarray):
                msh.addPointArray(s,'scalar')
            elif s in self.scalars:
                msh.addPointArray(self.scalars[s],'scalar')
            else:
                raise ValueError("Argument not recognised.")
            msh.addScalarBar()

        actors = [msh]

        if 'i' in kwargs:
            i   = kwargs['i']
            #c   = ['r', 'g', 'b', 'k', 'y', 'cyan']
            sph = vp.shapes.Spheres(self.v[i], r = .01)
            actors.append(sph)

        fig = None
        if not 'fig' in kwargs:
            fig = vp.plotter.Plotter()
        else:
            fig = kwargs['fig']

        fig.add(actors)
        fig.show()

    def vedo(self, c=None):
        import vedo as vp
        return vp.Mesh([self.v,self.f], c=c)


    def write(self, fn, method = 'vedo'):
        ret = False
        if method == 'igl':
            ret = igl.write_triangle_mesh(fn, self.v, self.f)
        else:
            self.vedo().write(fn)
            ret = True
        return ret


    ### ================================================ ###
    '''                  End of Class                    '''
    ### ================================================ ###




''' ================================================================================= '''
    ##################                  Utilities                  ##################
''' ================================================================================= '''










''' ================================================================================= '''
    ##################               end of script                 ##################
''' ================================================================================= '''
