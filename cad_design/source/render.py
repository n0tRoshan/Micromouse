"""Headless shaded renders (painter's algorithm) with matplotlib, no GPU or VTK needed."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection


def tessellate(shape, tol=0.05, max_edge=3.0):
    """Mesh a shape, then split long triangles so painter's depth sorting stays correct."""
    verts, tris = shape.val().tessellate(tol, 0.3)
    v = np.array([(p.x, p.y, p.z) for p in verts])
    p = v[np.array(tris)]                                  # (n,3,3) triangle soup
    if max_edge:
        for _ in range(8):
            e = np.max(np.linalg.norm(p - np.roll(p, 1, axis=1), axis=2), axis=1)
            big = e > max_edge
            if not big.any():
                break
            q = p[big]
            a, b, c = q[:, 0], q[:, 1], q[:, 2]
            ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
            new = np.concatenate([np.stack(t, 1) for t in ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca))])
            p = np.concatenate([p[~big], new])
    v = p.reshape(-1, 3)
    return v, np.arange(len(v)).reshape(-1, 3)


def view_matrix(azim, elev):
    """Rotation so the camera looks along -w; returns (right, up, toward-camera)."""
    a, e = np.radians(azim), np.radians(elev)
    w = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])   # toward camera
    up0 = np.array([0, 0, 1.0]) if abs(elev) < 89 else np.array([-np.cos(a), -np.sin(a), 0])
    r = np.cross(up0, w); r /= np.linalg.norm(r)
    u = np.cross(w, r)
    return r, u, w


def draw(ax, meshes, azim, elev, light=(0.4, 0.3, 0.85), edge=False):
    """meshes: list of (verts, tris, rgb, offset)."""
    r, u, w = view_matrix(azim, elev)
    L = np.array(light); L = L / np.linalg.norm(L)
    # light in camera frame so every view is lit the same way
    Lw = L[0] * r + L[1] * u + L[2] * w
    polys, cols, depth = [], [], []
    for v, t, rgb, off in meshes:
        vv = v + np.array(off)
        p = vv[t]                                     # (n,3,3)
        n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        nn = np.linalg.norm(n, axis=1); ok = nn > 1e-12
        p, n = p[ok], n[ok] / nn[ok, None]
        facing = n @ w
        keep = facing > -1e-6
        p, n = p[keep], n[keep]
        shade = 0.35 + 0.65 * np.clip(n @ Lw, 0, 1)
        c = np.clip(np.array(rgb)[None, :] * shade[:, None] + 0.04, 0, 1)
        xy = np.stack([p @ r, p @ u], axis=-1)
        polys.append(xy); cols.append(c); depth.append((p @ w).mean(axis=1))
    polys = np.concatenate(polys); cols = np.concatenate(cols); depth = np.concatenate(depth)
    order = np.argsort(depth)
    pc = PolyCollection(polys[order], facecolors=cols[order],
                        edgecolors=cols[order] if not edge else "k", linewidths=0.25)
    ax.add_collection(pc)
    allxy = polys.reshape(-1, 2)
    ax.set_xlim(allxy[:, 0].min() - 5, allxy[:, 0].max() + 5)
    ax.set_ylim(allxy[:, 1].min() - 5, allxy[:, 1].max() + 5)
    ax.set_aspect("equal"); ax.axis("off")
    return r, u, w


def save(fig, path):
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
