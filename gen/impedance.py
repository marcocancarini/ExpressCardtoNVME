#!/usr/bin/env python3
"""2D quasi-static solver (finite differences) for coplanar differential pairs over a GND plane.

Cross-section: GND plane (B.Cu) | dielectric h, er | 2 traces (w, gap s) with side GND pour at distance g | solder mask | air.
Returns Zodd, Zdiff, Zeven, Zcm. Usage: gen/.venv/bin/python gen/impedance.py
"""
import numpy as np
from scipy.sparse.linalg import spsolve

C0 = 299792458.0
EPS0 = 8.854187817e-12


def solve(w, s, g, h=0.93, er=4.5, t=0.035, mask=0.015, er_mask=3.8, d=0.0125, side=2.5, air=2.5, eps_on=True):
    W = 2 * side + 2 * w + s                       # domain width (mm)
    nx, ny = int(round(W / d)) + 1, int(round((h + t + air) / d)) + 1
    xs = np.arange(nx) * d - W / 2
    ys = np.arange(ny) * d                         # y=0 GND plane
    # permittivity per cell (nx-1, ny-1)
    xc, yc = (xs[:-1] + xs[1:]) / 2, (ys[:-1] + ys[1:]) / 2
    X, Y = np.meshgrid(xc, yc, indexing="ij")
    eps = np.ones_like(X)
    if eps_on:
        eps[Y < h] = er
        eps[(Y >= h) & (Y < h + t + mask)] = er_mask  # mask (approximated as a uniform layer)
    # conductors on the nodes
    NX, NY = np.meshgrid(xs, ys, indexing="ij")
    cu = (NY >= h - 1e-9) & (NY <= h + t + 1e-9)
    x1, x2 = -(s / 2 + w), -s / 2
    p1 = cu & (NX >= x1 - 1e-9) & (NX <= x2 + 1e-9)
    p2 = cu & (NX >= s / 2 - 1e-9) & (NX <= s / 2 + w + 1e-9)
    gnd = (NY <= 1e-9) | (cu & ((NX <= x1 - g + 1e-9) | (NX >= s / 2 + w + g - 1e-9)))
    res = {}
    for mode, v2 in (("odd", -1.0), ("even", 1.0)):
        fixed = np.zeros((nx, ny), bool)
        V = np.zeros((nx, ny))
        fixed[gnd] = True
        fixed[p1] = True; V[p1] = 1.0
        fixed[p2] = True; V[p2] = v2
        idx = -np.ones((nx, ny), int)
        free = ~fixed
        n = free.sum()
        idx[free] = np.arange(n)
        # edge coefficients: mean eps of the adjacent cells (domain boundary = Neumann)
        ep = np.pad(eps, 1, constant_values=np.nan)          # (nx+1, ny+1), cell (i,j) -> ep[i+1,j+1]
        cE = np.nanmean(np.stack([ep[1:, :-1], ep[1:, 1:]]), axis=0)[:, :]   # edge towards i+1, node (i,j)
        cW = np.nanmean(np.stack([ep[:-1, :-1], ep[:-1, 1:]]), axis=0)
        cN = np.nanmean(np.stack([ep[:-1, 1:], ep[1:, 1:]]), axis=0)        # towards j+1
        cS = np.nanmean(np.stack([ep[:-1, :-1], ep[1:, :-1]]), axis=0)
        cE[-1, :] = 0; cW[0, :] = 0; cN[:, -1] = 0; cS[:, 0] = 0
        cE, cW, cN, cS = (np.nan_to_num(c) for c in (cE, cW, cN, cS))
        rows, cols, vals = [], [], []
        b = np.zeros(n)
        I, J = np.nonzero(free)
        k = idx[I, J]
        diag = cE[I, J] + cW[I, J] + cN[I, J] + cS[I, J]
        rows.append(k); cols.append(k); vals.append(diag)
        for c, di, dj in ((cE, 1, 0), (cW, -1, 0), (cN, 0, 1), (cS, 0, -1)):
            cc = c[I, J]
            ok = cc > 0
            ii, jj = I[ok] + di, J[ok] + dj
            kk, cc = k[ok], cc[ok]
            fx = fixed[ii, jj]
            np.add.at(b, kk[fx], cc[fx] * V[ii[fx], jj[fx]])
            rows.append(kk[~fx]); cols.append(idx[ii[~fx], jj[~fx]]); vals.append(-cc[~fx])
        from scipy.sparse import csr_matrix
        A = csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
        V[free] = spsolve(A, b)
        # energy per unit length -> capacitance (V=1 on each trace)
        Ex = (np.diff(V, axis=0)[:, :-1] + np.diff(V, axis=0)[:, 1:]) / 2 / (d * 1e-3)
        Ey = (np.diff(V, axis=1)[:-1, :] + np.diff(V, axis=1)[1:, :]) / 2 / (d * 1e-3)
        Wn = 0.5 * EPS0 * np.sum(eps * (Ex ** 2 + Ey ** 2)) * (d * 1e-3) ** 2
        res[mode] = Wn                                 # = mode C per trace (F/m)
    return res


def impedance(w, s, g, **kw):
    c = solve(w, s, g, **kw)
    ca = solve(w, s, g, eps_on=False, **kw)
    zo = 1 / (C0 * np.sqrt(c["odd"] * ca["odd"]))
    ze = 1 / (C0 * np.sqrt(c["even"] * ca["even"]))
    return zo, 2 * zo, ze, ze / 2


if __name__ == "__main__":
    import sys
    cases = [tuple(map(float, a.split(","))) for a in sys.argv[1:]] or [(0.3, 0.2, 0.25)]
    for w, s, g in cases:
        zo, zd, ze, zc = impedance(w, s, g)
        print(f"w={w:.3f} s={s:.3f} g={g:.3f}  Zodd={zo:5.1f}  Zdiff={zd:5.1f}  Zeven={ze:5.1f}  Zcm={zc:5.1f} ohm")
