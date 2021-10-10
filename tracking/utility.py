""" feature extractor utility functions """

import numpy as np
import math

from numba.pycc import CC


SECTOR = 9
EPSLON = 1e-07

_cc = CC('utility')
_cc.verbose = True

@_cc.export('func1', '(f4[:,:,:], f4[:,:,:], f4[:], f4[:], f4[:,:], i4[:,:,:], i8,i8,i8)')
def func1(dx, dy, boundary_x, boundary_y, r, alfa, height, width, channels):
    for j in range(1, height - 1):
        for i in range(1, width - 1):
            c = 0
            x = dx[j, i, c]
            y = dy[j, i, c]
            r[j, i] = math.sqrt(x * x + y * y)

            for ch in range(1, channels):
                tx = dx[j, i, ch]
                ty = dy[j, i, ch]
                magnitude = math.sqrt(tx * tx + ty * ty)
                if(magnitude > r[j, i]):
                    r[j, i] = magnitude
                    c = ch
                    x = tx
                    y = ty

            mmax = boundary_x[0] * x + boundary_y[0] * y
            maxi = 0

            for kk in range(0, SECTOR):
                dotp = boundary_x[kk] * x + boundary_y[kk] * y
                if dotp > mmax:
                    mmax = dotp
                    maxi = kk
                elif -dotp > mmax:
                    mmax = -dotp
                    maxi = kk + SECTOR

            alfa[j, i, 0] = maxi % SECTOR
            alfa[j, i, 1] = maxi


@_cc.export('func2', '(f4[:], f4[:], f4[:], f4[:,:], i4[:,:,:], i4[:], f4[:,:], i8,i8,i8,i8,i8,i8,i8)')
def func2(mapp, boundary_x, boundary_y, r, alfa, nearest, w, k, height, width, size_x, size_y, p, string_size):
    for i in range(size_y):
        for j in range(size_x):
            for ii in range(k):
                for jj in range(k):
                    if (i * k + ii > 0) and (i * k + ii < height - 1) and (j * k + jj > 0) and (j * k + jj < width  - 1):
                        mapp[i * string_size + j * p + alfa[k * i + ii, j * k + jj, 0]] += r[k * i + ii, j * k + jj] * w[ii, 0] * w[jj, 0]
                        mapp[i * string_size + j * p + alfa[k * i + ii, j * k + jj, 1] + SECTOR] +=  r[k * i + ii, j * k + jj] * w[ii, 0] * w[jj, 0]
                        
                        if (i + nearest[ii] >= 0) and (i + nearest[ii] <= size_y - 1):
                            mapp[(i + nearest[ii]) * string_size + j * p + alfa[k * i + ii, j * k + jj, 0]] += r[k * i + ii, j * k + jj] * w[ii, 1] * w[jj, 0]
                            mapp[(i + nearest[ii]) * string_size + j * p + alfa[k * i + ii, j * k + jj, 1] + SECTOR] += r[k * i + ii, j * k + jj] * w[ii, 1] * w[jj, 0]
                        
                        if(j + nearest[jj] >= 0) and (j + nearest[jj] <= size_x - 1):
                            mapp[i * string_size + (j + nearest[jj]) * p + alfa[k * i + ii, j * k + jj, 0]] += r[k * i + ii, j * k + jj] * w[ii, 0] * w[jj, 1]
                            mapp[i * string_size + (j + nearest[jj]) * p + alfa[k * i + ii, j * k + jj, 1] + SECTOR] += r[k * i + ii, j * k + jj] * w[ii, 0] * w[jj, 1]
                        
                        if((i + nearest[ii] >= 0) and (i + nearest[ii] <= size_y - 1) and (j + nearest[jj] >= 0) and (j + nearest[jj] <= size_x - 1)):
                            mapp[(i + nearest[ii]) * string_size + (j + nearest[jj]) * p + alfa[k * i + ii, j * k + jj, 0]] += r[k * i + ii, j * k + jj] * w[ii, 1] * w[jj, 1]
                            mapp[(i + nearest[ii]) * string_size + (j + nearest[jj]) * p + alfa[k * i + ii, j * k + jj, 1] + SECTOR] += r[k * i + ii, j * k + jj] * w[ii, 1] * w[jj, 1]


@_cc.export('func3', '(f4[:], f4[:], f4[:], i8,i8,i8,i8,i8)')
def func3(new, part, mappmap, size_x, size_y, p, xp, pp):
    for i in range(1, size_y + 1):
        for j in range(1, size_x + 1):
            pos1 = i * (size_x + 2) * xp + j * xp
            pos2 = (i - 1) * size_x * pp + (j - 1) * pp

            value = math.sqrt(part[(i    ) * (size_x + 2) + (j    )] +
                                    part[(i    ) * (size_x + 2) + (j + 1)] +
                                    part[(i + 1) * (size_x + 2) + (j    )] +
                                    part[(i + 1) * (size_x + 2) + (j + 1)]) + EPSLON
            new[pos2: pos2 + p] = mappmap[pos1: pos1 + p] / value
            new[pos2 + 4 * p: pos2 + 6 * p] = mappmap[pos1 + p: pos1 + 3 * p] / value

            value = math.sqrt(part[(i    ) * (size_x + 2) + (j    )] +
                                part[(i    ) * (size_x + 2) + (j + 1)] +
                                part[(i - 1) * (size_x + 2) + (j    )] +
                                part[(i - 1) * (size_x + 2) + (j + 1)]) + EPSLON
            new[pos2 + p: pos2 + 2 * p] = mappmap[pos1: pos1 + p] / value
            new[pos2 + 6 * p: pos2 + 8 * p] = mappmap[pos1 + p: pos1 + 3 * p] / value

            value = math.sqrt(part[(i    ) * (size_x + 2) + (j    )] +
                                part[(i    ) * (size_x + 2) + (j - 1)] +
                                part[(i + 1) * (size_x + 2) + (j    )] +
                                part[(i + 1) * (size_x + 2) + (j - 1)]) + EPSLON
            new[pos2 + 2 * p: pos2 + 3 * p] = mappmap[pos1: pos1 + p] / value
            new[pos2 + 8 * p: pos2 + 10 * p] = mappmap[pos1 + p: pos1 + 3 * p] / value

            value = math.sqrt(part[(i    ) * (size_x + 2) + (j    )] +
                                part[(i    ) * (size_x + 2) + (j - 1)] +
                                part[(i - 1) * (size_x + 2) + (j    )] +
                                part[(i - 1) * (size_x + 2) + (j - 1)]) + EPSLON
            new[pos2 + 3 * p: pos2 + 4 * p] = mappmap[pos1: pos1 + p] / value
            new[pos2 + 10 * p: pos2 + 12 * p] = mappmap[pos1 + p: pos1 + 3 * p] / value


@_cc.export('func4', '(f4[:], f4[:], i8,i8,i8,i8,i8,i8,f8,f8)')
def func4(new, mappmap, p, size_x, size_y, pp, yp, xp, nx, ny):	
	for i in range(size_y):
		for j in range(size_x):
			pos1 = (i * size_x + j) * p
			pos2 = (i * size_x + j) * pp

			for jj in range(2 * xp):
				new[pos2 + jj] = np.sum(mappmap[pos1 + yp * xp + jj : pos1 + 3 * yp * xp + jj : 2 * xp]) * ny
			for jj in range(xp): 
				new[pos2 + 2 * xp + jj] = np.sum(mappmap[pos1 + jj : pos1 + jj + yp*xp : xp]) * ny
			for ii in range(yp): 
				new[pos2 + 3 * xp + ii] = np.sum(mappmap[pos1 + yp * xp + ii * xp * 2 : pos1 + yp * xp + ii * xp * 2 + 2 * xp]) * nx
				
	
	
if __name__ == "__main__":
    _cc.compile()