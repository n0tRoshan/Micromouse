"""Build Rev A: run checks, export STEP/STL/DXF, render views into assets/, write build_report.md.

Usage:  python3 build.py            (from cad_design/source) full Rev A.1 with the suction fan
        python3 build.py --no-fan   fan-free variant, written to cad_design/no_fan/
"""
import itertools
import math
import os
import sys

if "--no-fan" in sys.argv:
    os.environ["MM_FAN"] = "0"

import numpy as np
import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

from shapely import affinity
from shapely.geometry import LineString, MultiPoint, Point, box as sbox
from shapely.ops import unary_union

import params as P
import micromouse as M
import render as R

HERE = os.path.dirname(os.path.abspath(__file__))
if P.FAN:
    OUT = os.path.normpath(os.path.join(HERE, ".."))                 # cad_design/
    ASSETS = os.path.normpath(os.path.join(HERE, "..", "..", "assets"))
    VARIANT, ASM_NAME = "Rev A.1 (with suction fan)", "micromouse_revA_assembly"
else:
    OUT = os.path.normpath(os.path.join(HERE, "..", "no_fan"))       # cad_design/no_fan/
    ASSETS = os.path.join(OUT, "assets")
    VARIANT, ASM_NAME = "Rev A.1 fan-free (initial build)", "micromouse_revA1_nofan_assembly"
DOWNFORCE_G = P.FAN_DOWNFORCE_G if P.FAN else 0.0
G = 9.81
MU_TIRE = 1.0      # [A] silicone on painted wood; Phase 6 measures it (tilt test)

# pairs that touch by design (shared faces or fits); anything else overlapping is a clash
DESIGNED_CONTACT = {}


def bbox(shape):
    b = shape.val().BoundingBox()
    return (b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax)


def overlap(b1, b2):
    return all(b1[i] < b2[i + 3] and b2[i] < b1[i + 3] for i in range(3))


def interference(parts):
    rows = []
    for a, b in itertools.combinations(parts, 2):
        if not overlap(bbox(a.shape), bbox(b.shape)):
            continue
        v = a.shape.intersect(b.shape).val().Volume()
        if v > 1e-3:
            why = DESIGNED_CONTACT.get(frozenset((a.name, b.name)))
            rows.append((a.name, b.name, v, why))
    return rows


def min_dist(a, b):
    d = BRepExtrema_DistShapeShape(a.shape.val().wrapped, b.shape.val().wrapped)
    d.Perform()
    return d.Value()


def mass_table(parts):
    rows, m, mx, my, mz = [], 0, 0, 0, 0
    for p in parts:
        g = p.grams(); c = p.centroid()
        rows.append((p.name, p.material, g, c))
        m += g; mx += g * c[0]; my += g * c[1]; mz += g * c[2]
    for name, g in (("PCB passives, regulator, connectors", P.COMPONENTS_MASS), ("wiring, screws, inserts", P.MISC_MASS)):
        c = (0.0, 0.0, M.PLATE_Z1)                      # lumped at the plate centre
        rows.append((name, "lumped [A]", g, c))
        m += g; mz += g * c[2]
    return rows, m, (mx / m, my / m, mz / m)


def sensor_geometry():
    """Mouse centred in a cell, heading +x, walls on all three sides."""
    half = P.PASSAGE / 2
    out = []
    for (name, x, y, yaw) in P.SENSORS:
        d = np.array([math.cos(math.radians(yaw)), math.sin(math.radians(yaw))])
        hits = []
        if d[0] > 1e-9:
            hits.append(((half - x) / d[0], "front wall"))
        if d[1] > 1e-9:
            hits.append(((half - y) / d[1], "left wall"))
        if d[1] < -1e-9:
            hits.append(((-half - y) / d[1], "right wall"))
        t, wall = min(hits)
        side = [h for h in hits if h[1] != "front wall"]
        st = side[0][0] if side else None
        hx, hy = x + t * d[0], y + t * d[1]
        spread = t * math.tan(math.radians(P.IR_HALF_ANGLE))
        out.append(dict(name=name, x=x, y=y, yaw=yaw, dist=t, wall=wall, hit=(hx, hy),
                        side_dist=st, side_hit_x=(x + st * d[0]) if st else None,
                        z_lo=M.SENS_Z - spread, z_hi=M.SENS_Z + spread))
    return out


def skirt_area_centroid():
    x0, x1 = P.SKIRT_X
    pan = M._box(x0, x1, -P.SKIRT_HALF_Y, P.SKIRT_HALF_Y, 0, 1).edges("|Z").fillet(6).cut(
        M._zcyl(P.INLET_D, -1, 2, x=P.FAN_CENTER_X))
    s = pan.section(0.5).val()
    c = cq.Shape.centerOfMass(s)
    return s.Area(), c.x


def dynamics(m_g, cg, fan_g=0.0):
    """Pitch and grip limits for a 2WD mouse on two skids (rigid body, quasi-static).
    fan_g: suction downforce in gram-force, acting at the skirt area centroid."""
    xc, _, h = cg
    xf, xr = P.FRONT_SKID_X, P.REAR_SKID_X
    xd = skirt_area_centroid()[1] if P.FAN else 0.0
    f = fan_g / m_g                       # downforce as a fraction of weight
    res = {"xd": xd, "f": f}
    res["rests_on"] = "front skid" if xc > 0 else "rear skid"
    # accel: inertial force at CG height pitches the nose up once it beats the forward moments
    res["nose_lift_accel"] = G * (xc + f * xd) / h if xc + f * xd > 0 else 0.0
    # braking on the front skid: N_skid = m (g xc + f g xd + a h) / xf ; mu (m g (1+f) - N_skid) >= m a
    res["brake_grip_limit"] = MU_TIRE * G * ((1 - xc / xf) + f * (1 - xd / xf)) / (1 + MU_TIRE * h / xf)
    # accel on the rear skid: N_rear = m (a h - g xc - f g xd) / |xr|
    res["accel_grip_limit"] = MU_TIRE * G * ((1 + xc / abs(xr)) + f * (1 + xd / abs(xr))) / (1 + MU_TIRE * h / abs(xr))
    res["pitch_range_deg"] = math.degrees(math.atan((P.FRONT_SKID_GAP + P.REAR_SKID_GAP) / (xf - xr)))
    res["beam_shift_100mm"] = 100 * math.tan(math.radians(res["pitch_range_deg"]))
    # worst skirt-to-floor gap: nose down on the front skid, or tail down on the rear skid
    x0, x1 = P.SKIRT_X
    res["skirt_gap_nose_down"] = P.SKIRT_GAP - x1 * P.FRONT_SKID_GAP / xf
    res["skirt_gap_tail_down"] = P.SKIRT_GAP - abs(x0) * P.REAR_SKID_GAP / abs(xr)
    return res


# ------------------------------------------------------------ diagonal running (Rev A.1)
def footprint(parts):
    """Top-view convex hull of the whole mouse (robot frame, origin under the axle centre)."""
    pts = np.vstack([R.tessellate(p.shape, 0.3, max_edge=0)[0][:, :2] for p in parts])
    return MultiPoint([tuple(q) for q in pts]).convex_hull


def fillet_path(wps, radius, step=2.0):
    """Axle-centre poses (x, y, heading) along a polyline whose corners are rounded with arcs of `radius`."""
    wps = [np.array(w, float) for w in wps]
    segs, start = [], wps[0]
    for i in range(1, len(wps) - 1):
        a, b, c = wps[i - 1], wps[i], wps[i + 1]
        u = (b - a) / np.linalg.norm(b - a); v = (c - b) / np.linalg.norm(c - b)
        turn = math.atan2(u[0] * v[1] - u[1] * v[0], u @ v)
        d = radius * math.tan(abs(turn) / 2)
        p1 = b - u * d
        n = np.array([-u[1], u[0]]) * math.copysign(1, turn)
        segs += [("L", start, p1), ("A", p1 + n * radius, math.atan2(u[1], u[0]), turn)]
        start = b + v * d
    segs.append(("L", start, wps[-1]))
    poses = []
    for sg in segs:
        if sg[0] == "L":
            a, b = sg[1], sg[2]; L = np.linalg.norm(b - a); h = math.atan2(b[1] - a[1], b[0] - a[0])
            poses += [(*(a + (b - a) * t / L), h) for t in np.arange(0, L, step)]
        else:
            _, ctr, h0, turn = sg
            n = max(2, int(abs(turn) * radius / step))
            for k in range(n + 1):
                h = h0 + turn * k / n
                ang = h - math.copysign(math.pi / 2, turn)
                poses.append((ctr[0] + radius * math.cos(ang), ctr[1] + radius * math.sin(ang), h))
    return poses


def maze_for(wps):
    """Walls and posts around the cells the polyline visits: every wall is closed except the ones it crosses."""
    C, T = P.CELL, P.WALL_T
    cells = []
    for a, b in zip(wps[:-1], wps[1:]):
        a, b = np.array(a, float), np.array(b, float)
        for t in np.linspace(0, 1, 600):
            q = a + (b - a) * t
            fx, fy = (q[0] / C) % 1, (q[1] / C) % 1
            if min(fx, 1 - fx) < 1e-6 or min(fy, 1 - fy) < 1e-6:
                continue
            c = (math.floor(q[0] / C), math.floor(q[1] / C))
            if not cells or cells[-1] != c:
                cells.append(c)
    opening = {frozenset(p) for p in zip(cells[:-1], cells[1:])}
    obs = []
    xs = [c[0] for c in cells]; ys = [c[1] for c in cells]
    for i in range(min(xs) - 1, max(xs) + 3):
        for j in range(min(ys) - 1, max(ys) + 3):
            obs.append(sbox(i * C - T / 2, j * C - T / 2, i * C + T / 2, j * C + T / 2))
    for k, (i, j) in enumerate(cells):
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if frozenset(((i, j), (i + di, j + dj))) in opening:
                continue
            if (k == 0 and (di, dj) == (-1, 0)) or (k == len(cells) - 1 and (di, dj) == (1, 0)):
                continue                                   # run-in and run-out stay open
            x0, y0 = (i + (di == 1)) * C, (j + (dj == 1)) * C
            obs.append(sbox(x0 - T / 2, j * C, x0 + T / 2, (j + 1) * C) if di else
                       sbox(i * C, y0 - T / 2, (i + 1) * C, y0 + T / 2))
    return unary_union(obs)


def clearance(hull, poses, obs, dlat=0.0, dhead=0.0):
    m = 1e9
    for (x, y, h) in poses:
        g = affinity.rotate(hull, h + math.radians(dhead), origin=(0, 0), use_radians=True)
        g = affinity.translate(g, x - math.sin(h) * dlat, y + math.cos(h) * dlat)
        m = min(m, g.distance(obs))
    return m


def worst_clearance(hull, poses, obs):
    e, h = P.DIAG_LATERAL_ERR, P.DIAG_HEADING_ERR
    return min(clearance(hull, poses, obs, a, b) for a in (-e, e) for b in (-h, h))


DIAG_STRAIGHT = [(-270, 90), (180, 90), (900, 810), (1350, 810)]   # straight, 45° in, 4 diagonal cells, 45° out
DIAG_V90 = [(-270, 90), (180, 90), (360, 270), (720, -90), (1170, -90)]   # 45° in, V90 right, 45° out


def diagonal(hull):
    out = {}
    corridor = 2 * (P.CELL / 2 - P.WALL_T) / math.sqrt(2)
    out["corridor"] = corridor
    for th in (0.0, P.DIAG_HEADING_ERR):
        g = affinity.rotate(hull, th, origin=(0, 0))
        out[f"proj_{th:g}"] = g.bounds[3] - g.bounds[1]
    obs = maze_for(DIAG_STRAIGHT)
    poses = [q for q in fillet_path(DIAG_STRAIGHT, 75.0) if 360 < q[0] < 720]      # middle of the diagonal
    out["straight_nom"] = clearance(hull, poses, obs)
    out["straight_worst"] = worst_clearance(hull, poses, obs)
    out["t45"] = [(r, clearance(hull, fillet_path(DIAG_STRAIGHT, r), obs),
                   worst_clearance(hull, fillet_path(DIAG_STRAIGHT, r), obs)) for r in P.TURN45_R]
    obs2 = maze_for(DIAG_V90)
    out["v90"] = []
    for r in P.V90_R:
        poses = fillet_path_mixed(DIAG_V90, (60.0, r, 60.0))
        out["v90"].append((r, clearance(hull, poses, obs2), worst_clearance(hull, poses, obs2)))
    # IR rays while running the diagonal: distance to the first wall or post for each sensor
    poses = [q for q in fillet_path(DIAG_STRAIGHT, 75.0) if 360 <= q[0] < 540]          # one 180 mm period
    edge = obs.boundary
    rays = {n: [] for (n, *_r) in P.SENSORS}
    for (x, y, h) in poses[::2]:
        for (n, sx, sy, yaw) in P.SENSORS:
            ox, oy = x + sx * math.cos(h) - sy * math.sin(h), y + sx * math.sin(h) + sy * math.cos(h)
            a = h + math.radians(yaw)
            ray = LineString([(ox, oy), (ox + 400 * math.cos(a), oy + 400 * math.sin(a))])
            hit = ray.intersection(edge)
            rays[n].append(min(Point(ox, oy).distance(g) for g in getattr(hit, "geoms", [hit])) if not hit.is_empty else 999)
    out["rays"] = {n: (min(v), max(v), sum(d <= P.IR_RANGE for d in v) / len(v)) for n, v in rays.items()}
    return out


def fillet_path_mixed(wps, radii, step=2.0):
    """Like fillet_path, one radius per corner."""
    poses, pts = [], [np.array(w, float) for w in wps]
    # build corner by corner: reuse fillet_path on 3-point windows and stitch at segment midpoints
    mids = [pts[0]] + [(pts[i] + pts[i + 1]) / 2 for i in range(1, len(pts) - 2)] + [pts[-1]]
    for i in range(1, len(pts) - 1):
        seg = fillet_path([mids[i - 1], pts[i], mids[i]], radii[i - 1], step)
        poses += seg
    return poses


# ------------------------------------------------------------ crash and stiffness (Rev A.1)
def crash(mass_g):
    m = mass_g / 1000
    rows = []
    for v in P.CRASH_SPEEDS:
        e = 0.5 * m * v * v
        f = e / (P.BUMPER_STROKE / 1000)                  # mean force over the bumper stroke
        rows.append((v, e, f, 4 * P.M2_SHEAR_N / f))      # 4 frame screws carry the plate
    # axle as a cantilever from the outer bearing face to the tyre centre
    L = (M.HUB_Y0 + M.HUB_Y1) / 2 - M.WALL_Y1
    I = math.pi * P.AXLE_D ** 4 / 64
    F = P.SHOCK_G * (mass_g + DOWNFORCE_G) / 1000 * G / 2
    defl = F * L ** 3 / (3 * 193000 * I)                  # E = 193 GPa stainless
    stress = F * L * (P.AXLE_D / 2) / I
    return rows, dict(L=L, F=F, defl_um=defl * 1000, stress=stress)


def export(parts):
    import shutil
    for d in ("step", "stl"):
        shutil.rmtree(os.path.join(OUT, d), ignore_errors=True)
    os.makedirs(os.path.join(OUT, "step"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "stl"), exist_ok=True)
    asm = cq.Assembly(name=ASM_NAME.replace("_assembly", ""))
    for p in parts:
        asm.add(p.shape, name=p.name, color=cq.Color(*p.color))
    asm.save(os.path.join(OUT, "step", f"{ASM_NAME}.step"))
    for p in parts:
        cq.exporters.export(p.shape, os.path.join(OUT, "step", f"{p.name}.step"))
        if p.printable or p.name == "plate":
            cq.exporters.export(p.shape, os.path.join(OUT, "stl", f"{p.name}.stl"),
                                tolerance=0.02, angularTolerance=0.1)
    # DXF of the plate outline for PCB edge cuts / laser cutting
    cq.exporters.export(M.plate().section(M.PLATE_Z0 + P.PLATE_T / 2),
                        os.path.join(OUT, "step", "plate_outline.dxf"))


def diagonal_figure(hull):
    """Top view: the mouse footprint along a 45° entry, a V90 turn and a 45° exit."""
    obs = maze_for(DIAG_V90)
    fig, ax = R.plt.subplots(figsize=(9, 6))
    for g in getattr(obs, "geoms", [obs]):
        x, y = g.exterior.xy; ax.fill(x, y, fc="0.85", ec="crimson", lw=0.5)
    poses = fillet_path_mixed(DIAG_V90, (60.0, 60.0, 60.0))
    xs = [q[0] for q in poses]; ys = [q[1] for q in poses]
    ax.plot(xs, ys, "k--", lw=0.6)
    for q in poses[::14]:
        g = affinity.translate(affinity.rotate(hull, q[2], origin=(0, 0), use_radians=True), q[0], q[1])
        x, y = g.exterior.xy; ax.plot(x, y, c="tab:blue", lw=0.6)
    ax.set_aspect("equal"); ax.set_xlim(-200, 1000); ax.set_ylim(-260, 420)
    ax.set_title("Rev A.1 footprint (74 x 96.5 mm) through a 45° entry, a V90 turn (R 60) and a 45° exit", fontsize=9)
    ax.set_xlabel("mm"); R.save(fig, os.path.join(ASSETS, "diagonal_clearance.png"))


def renders(parts, sens):
    rd = ASSETS; os.makedirs(rd, exist_ok=True)
    meshes = {p.name: R.tessellate(p.shape) for p in parts}
    col = {p.name: p.color for p in parts}

    def ms(explode=False):
        return [(meshes[n][0], meshes[n][1], col[n],
                 next(p.explode for p in parts if p.name == n) if explode else (0, 0, 0)) for n in meshes]

    # iso views
    for fname, az, el in (("iso_front_left", 35, 28), ("iso_rear_right", 215, 28), ("iso_below", 30, -35)):
        fig, ax = R.plt.subplots(figsize=(8, 6)); R.draw(ax, ms(), az, el)
        ax.set_title(f"Micromouse {VARIANT}, {fname.replace('_', ' ')}", fontsize=10); R.save(fig, f"{rd}/{fname}.png")

    # exploded with labels: one label per part type, pushed radially out from the picture centre
    fig, ax = R.plt.subplots(figsize=(11, 9))
    r, u, w = R.draw(ax, ms(True), 35, 25)
    skip = ("imu", "motor_driver", "fan_mosfet", "ir_receivers")
    lab = [p for p in parts if not p.name.endswith("_R") and p.name not in skip]
    pts = {p.name: np.array([(np.array(p.centroid()) + np.array(p.explode)) @ r,
                             (np.array(p.centroid()) + np.array(p.explode)) @ u]) for p in lab}
    ctr = np.mean(list(pts.values()), axis=0)
    xl, yl = ax.get_xlim(), ax.get_ylim()
    tx = {}
    for p in lab:
        q = pts[p.name]; d = q - ctr
        tx[p.name] = q + d / (np.linalg.norm(d) + 1e-9) * 38
    names = list(tx)
    for _ in range(300):                                  # push overlapping labels apart
        moved = False
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                dv = tx[a] - tx[b]
                if abs(dv[0]) < 34 and abs(dv[1]) < 7:
                    sgn = 1 if dv[1] >= 0 else -1
                    tx[a][1] += 0.8 * sgn; tx[b][1] -= 0.8 * sgn; moved = True
        if not moved:
            break
    for p in lab:
        nm = p.name[:-2] + " x2" if p.name.endswith("_L") else p.name
        ax.annotate(nm, pts[p.name], xytext=tx[p.name], fontsize=7, ha="center", va="center",
                    arrowprops=dict(arrowstyle="-", lw=0.5, color="0.3"),
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="0.6", lw=0.4))
    ax.set_xlim(xl[0] - 40, xl[1] + 40); ax.set_ylim(yl[0] - 20, yl[1] + 20)
    ax.set_title("Rev A.1 exploded view (left-side parts labelled; right side is the mirror image)", fontsize=10)
    R.save(fig, f"{rd}/exploded.png")

    # orthographic drawings with key dimensions
    def dim(ax, p1, p2, off, text, horiz=True):
        (x1, y1), (x2, y2) = p1, p2
        if horiz:
            yy = y1 + off
            ax.annotate("", (x1, yy), (x2, yy), arrowprops=dict(arrowstyle="<->", lw=0.6))
            ax.plot([x1, x1], [y1, yy], lw=0.3, c="0.4"); ax.plot([x2, x2], [y2, yy], lw=0.3, c="0.4")
            ax.text((x1 + x2) / 2, yy + 1.5, text, ha="center", fontsize=7)
        else:
            xx = x1 + off
            ax.annotate("", (xx, y1), (xx, y2), arrowprops=dict(arrowstyle="<->", lw=0.6))
            ax.plot([x1, xx], [y1, y1], lw=0.3, c="0.4"); ax.plot([x2, xx], [y2, y2], lw=0.3, c="0.4")
            ax.text(xx + 1.5, (y1 + y2) / 2, text, va="center", fontsize=7, rotation=90)

    allb = np.array([bbox(p.shape) for p in parts])
    xmin, ymin, zmin = allb[:, :3].min(axis=0); xmax, ymax, zmax = allb[:, 3:].max(axis=0)

    fig, ax = R.plt.subplots(figsize=(8, 7)); R.draw(ax, ms(), -90, 90)
    dim(ax, (xmin, ymin), (xmax, ymin), -12, f"length {xmax - xmin:.1f}")
    dim(ax, (xmax, ymin), (xmax, ymax), 12, f"width {ymax - ymin:.1f}", horiz=False)
    dim(ax, (0, -M.TRACK / 2), (0, M.TRACK / 2), -70, f"track {M.TRACK:.1f}", horiz=False)
    ax.plot([0, 0], [ymin - 5, ymax + 5], "k-.", lw=0.5); ax.text(1, ymax + 6, "axle", fontsize=7)
    for s in sens:
        d = np.array([math.cos(math.radians(s["yaw"])), math.sin(math.radians(s["yaw"]))])
        ax.plot([s["x"], s["x"] + 30 * d[0]], [s["y"], s["y"] + 30 * d[1]], c="crimson", lw=0.8)
        ax.text(s["x"] + 32 * d[0], s["y"] + 32 * d[1], f'{s["name"]} {s["yaw"]:+.0f}°', fontsize=7, color="crimson")
    ax.set_xlim(xmin - 25, xmax + 45); ax.set_ylim(ymin - 25, ymax + 25)
    ax.set_title("Top view (x forward). Dimensions in mm", fontsize=10); R.save(fig, f"{rd}/drawing_top.png")

    fig, ax = R.plt.subplots(figsize=(8, 4)); R.draw(ax, ms(), -90, 0)
    dim(ax, (xmax, 0), (xmax, zmax), 10, f"height {zmax:.1f}", horiz=False)
    dim(ax, (0, 0), (P.FRONT_SKID_X, 0), -8, f"axle to front skid {P.FRONT_SKID_X:.0f}")
    dim(ax, (P.REAR_SKID_X, 0), (0, 0), -8, f"rear skid {abs(P.REAR_SKID_X):.0f}")
    ax.axhline(0, c="k", lw=0.6); ax.axhline(P.WALL_H, c="crimson", lw=0.5, ls="--")
    ax.text(xmin, P.WALL_H + 1, "wall top 50 (red)", fontsize=7, color="crimson")
    ax.axhline(M.SENS_Z, c="crimson", lw=0.4, ls=":"); ax.text(xmin - 14, M.SENS_Z + 1, f"IR beam z={M.SENS_Z:.1f}", fontsize=7, ha="right")
    ax.set_xlim(xmin - 45, xmax + 25); ax.set_ylim(-18, P.WALL_H + 6)
    ax.set_title("Side view from right", fontsize=10); R.save(fig, f"{rd}/drawing_side.png")

    fig, ax = R.plt.subplots(figsize=(7, 4)); R.draw(ax, ms(), 0, 0)
    dim(ax, (ymin, zmax), (ymax, zmax), 6, f"overall {ymax - ymin:.1f}")
    dim(ax, (-M.TRACK / 2, 0), (M.TRACK / 2, 0), -8, f"track {M.TRACK:.1f}")
    ax.text(M.TRACK / 2 - 6, M.AXLE_Z + 14, f"wheel Ø{P.WHEEL_D:.0f}", fontsize=7)
    ax.axhline(0, c="k", lw=0.6); ax.set_ylim(-16, zmax + 14)
    ax.set_title("Front view", fontsize=10); R.save(fig, f"{rd}/drawing_front.png")

    # section at y = 0 showing the fan, skirt and frame
    cutbox = cq.Workplane("XY").box(400, 200, 200).translate((0, -100, 50))
    sec = []
    for p in parts:
        try:
            s = p.shape.intersect(cutbox)
            if s.val().Volume() > 1e-3:
                v, t = R.tessellate(s)
                sec.append((v, t, p.color, (0, 0, 0)))
        except Exception:
            pass
    fig, ax = R.plt.subplots(figsize=(9, 4.2)); R.draw(ax, sec, 90, 0)
    ax.axhline(0, c="k", lw=0.6)
    if P.FAN:
        ax.annotate("impeller", (-P.FAN_CENTER_X, M.SKIRT_Z1 + 3), xytext=(-P.FAN_CENTER_X - 30, -12), fontsize=7,
                    arrowprops=dict(arrowstyle="-", lw=0.5))
        ax.annotate("skirt (suction pan)", (20, M.SKIRT_Z0), xytext=(15, -12), fontsize=7, arrowprops=dict(arrowstyle="-", lw=0.5))
        ax.annotate("fan motor", (-P.FAN_CENTER_X, 28), xytext=(-P.FAN_CENTER_X - 25, 42), fontsize=7,
                    arrowprops=dict(arrowstyle="-", lw=0.5))
        title = "Section on the centre line (front to the left): fan, skirt and frame"
    else:
        ax.annotate(f"floor plate, {P.SKIRT_GAP} mm off the floor", (20, M.SKIRT_Z0), xytext=(15, -12), fontsize=7,
                    arrowprops=dict(arrowstyle="-", lw=0.5))
        title = "Section on the centre line (front to the left): fan-free frame"
    ax.set_ylim(-16, 46)
    ax.set_title(title, fontsize=10)
    R.save(fig, f"{rd}/{'section_fan' if P.FAN else 'section_centre'}.png")

    # sensor geometry in a cell
    fig, ax = R.plt.subplots(figsize=(7, 7)); R.draw(ax, ms(), -90, 90)
    h = P.PASSAGE / 2; c = P.CELL / 2
    for (x0, y0, x1, y1) in ((-c - 90, h, c + 90, h + P.WALL_T), (-c - 90, -h - P.WALL_T, c + 90, -h),
                             (h, -h, h + P.WALL_T, h)):
        ax.add_patch(R.plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fc="0.85", ec="crimson", lw=0.6))
    for px in (-c, c):
        for py in (-c, c):
            ax.add_patch(R.plt.Rectangle((px - 6, py - 6), 12, 12, fc="0.55"))
    for s in sens:
        ax.plot([s["x"], s["hit"][0]], [s["y"], s["hit"][1]], c="crimson", lw=0.8)
        ax.text(s["hit"][0] - 22, s["hit"][1] + (4 if s["hit"][1] > 0 else -8),
                f'{s["name"]} {s["dist"]:.0f} mm', fontsize=7, color="crimson")
    ax.plot(0, 0, "k+"); ax.set_xlim(-c - 20, c + 30); ax.set_ylim(-c - 20, c + 20)
    ax.set_title("Mouse centred in a cell: IR beam paths to walls", fontsize=10); R.save(fig, f"{rd}/sensor_in_cell.png")

    # beam cone vs wall face (side)
    fig, ax = R.plt.subplots(figsize=(7, 3.2))
    ta = math.tan(math.radians(P.IR_HALF_ANGLE))
    dd = np.linspace(0, 200, 50)
    ax.fill_between(dd, M.SENS_Z - dd * ta, M.SENS_Z + dd * ta, color="crimson", alpha=0.15, label=f"±{P.IR_HALF_ANGLE:.0f}° cone")
    ax.axhline(0, c="k"); ax.axhline(P.WALL_H, c="crimson", ls="--", lw=0.7)
    for s in sens:
        ax.axvline(s["dist"], c="0.4", lw=0.6, ls=":"); ax.text(s["dist"] + 1, 52, s["name"], fontsize=7)
    ax.set_xlabel("distance along beam to wall (mm)"); ax.set_ylabel("height (mm)")
    ax.set_ylim(-15, 60); ax.legend(fontsize=7, loc="lower left")
    ax.set_title("Beam spot stays on the white wall face (0-50 mm)", fontsize=10)
    R.save(fig, f"{rd}/beam_vs_wall.png")


def main():
    parts = M.build_parts()
    byname = {p.name: p for p in parts}
    clashes = interference(parts)
    real = [c for c in clashes if c[3] is None]
    rows, mass, cg = mass_table(parts)
    sens = sensor_geometry()
    dyn0 = dynamics(mass, cg, 0.0)
    dyn = dynamics(mass, cg, DOWNFORCE_G)
    skirt_A, skirt_xc = skirt_area_centroid() if P.FAN else (0.0, 0.0)
    dp_needed = DOWNFORCE_G / 1000 * G / (skirt_A * 1e-6) if P.FAN else 0.0
    skirt_min = min(dyn["skirt_gap_nose_down"], dyn["skirt_gap_tail_down"])
    allb = np.array([bbox(p.shape) for p in parts])
    xmin, ymin, zmin = allb[:, :3].min(axis=0); xmax, ymax, zmax = allb[:, 3:].max(axis=0)
    L, W = xmax - xmin, ymax - ymin
    # swept radius for a turn in place about the axle centre
    sweep = 0.0
    for p in parts:
        v, _ = R.tessellate(p.shape, 0.2, max_edge=0)
        sweep = max(sweep, np.hypot(v[:, 0], v[:, 1]).max())
    body = [p for p in parts if not p.name.startswith(("tire", "hub", "spur", "frame", "impeller", "fan_motor"))]  # fan parts sit inside the housing
    clear_floor = min(bbox(p.shape)[2] for p in body)
    gear_floor = M.AXLE_Z - M.SPUR_OD_R
    tire_clear = []
    for t in ("tire_L", "tire_R"):
        for o in ("plate", "frame", "bumper", "sensor_block", "battery_holder"):
            tire_clear.append((t, o, min_dist(byname[t], byname[o])))
    min_tire = min(tire_clear, key=lambda r: r[2])
    mass_ex_batt = mass - P.BATT_MASS
    hull = footprint(parts)
    dg = diagonal(hull)
    v90_ok = [r for r, n, w in dg["v90"] if w >= P.DIAG_MIN_CLEAR]
    t45_ok = all(w >= P.DIAG_MIN_CLEAR for r, n, w in dg["t45"])
    crash_rows, beam = crash(mass)

    checks = [
        ("No unplanned part interference", len(real) == 0,
         "none" if not real else "; ".join(f"{a} x {b} {v:.1f} mm³" for a, b, v, _ in real)),
        ("Footprint within 250 x 250 mm", L <= P.FOOTPRINT_MAX and W <= P.FOOTPRINT_MAX, f"{L:.1f} x {W:.1f} mm"),
        ("Width leaves ≥ 30 mm per side in the 168 mm passage", (P.PASSAGE - W) / 2 >= 30,
         f"{(P.PASSAGE - W) / 2:.1f} mm per side"),
        ("Turn in place fits a cell (swept radius ≤ 84 - 10 mm)", sweep <= P.PASSAGE / 2 - 10,
         f"swept radius {sweep:.1f} mm"),
        ("Mass excl. battery < 100 g (Phase 2 start target)", mass_ex_batt < 100,
         f"{mass_ex_batt:.1f} g (total {mass:.1f} g)"),
        ("CG ahead of axle by 0-6 mm (nose rests on front skid)", 0 <= cg[0] <= 6, f"x = {cg[0]:+.1f} mm"),
        ("CG centred laterally (|y| ≤ 1 mm)", abs(cg[1]) <= 1, f"y = {cg[1]:+.2f} mm"),
        ("CG low (z ≤ wheel diameter)", cg[2] <= P.WHEEL_D, f"z = {cg[2]:.1f} mm"),
        ("Braking grip limit ≥ 4 m/s² target, fan off", dyn0["brake_grip_limit"] >= 4,
         f'{dyn0["brake_grip_limit"]:.1f} m/s²' + (f' (fan on, {P.FAN_DOWNFORCE_G:.0f} gf [A]: {dyn["brake_grip_limit"]:.1f} m/s²)' if P.FAN else '')),
        ("Fan downforce acts within 10 mm of the axle (loads the wheels, not the skids)", abs(skirt_xc) <= 10,
         f"skirt centroid x = {skirt_xc:+.1f} mm"),
        ("Floor plate (skirt) clears the floor by > 0.5 mm step at both pitch extremes", skirt_min > P.FLOOR_STEP_MAX,
         f'nose down {dyn["skirt_gap_nose_down"]:.2f} mm, tail down {dyn["skirt_gap_tail_down"]:.2f} mm'),
        ("Body ground clearance ≥ 3 mm above the skirt line (floor steps ≤ 0.5 mm)", clear_floor >= 3,
         f"min {clear_floor:.1f} mm"),
        ("Spur gear tips ≥ 2 mm off the floor", gear_floor >= 2, f"{gear_floor:.1f} mm"),
        ("Rear skid gap > 0.5 mm floor step rule", P.REAR_SKID_GAP > P.FLOOR_STEP_MAX, f"{P.REAR_SKID_GAP} mm"),
        ("Tyre clears every body part by ≥ 0.8 mm", min_tire[2] >= 0.8,
         f"closest {min_tire[0]} to {min_tire[1]}: {min_tire[2]:.2f} mm"),
        (f"Diagonal straight: ≥ {P.DIAG_MIN_CLEAR:.0f} mm to every post with ±{P.DIAG_LATERAL_ERR:.0f} mm and ±{P.DIAG_HEADING_ERR:.0f}° error",
         dg["straight_worst"] >= P.DIAG_MIN_CLEAR,
         f'{dg["straight_worst"]:.1f} mm worst, {dg["straight_nom"]:.1f} mm centred (corridor {dg["corridor"]:.1f} mm)'),
        (f"45° turn in and out clears by ≥ {P.DIAG_MIN_CLEAR:.0f} mm with errors, every radius checked", t45_ok,
         ", ".join(f"R{r:.0f}: {w:.1f}" for r, n, w in dg["t45"])),
        (f"V90 turn clears by ≥ {P.DIAG_MIN_CLEAR:.0f} mm with errors at R = 50 mm", 50.0 in v90_ok,
         f"passes at R = {', '.join(f'{r:.0f}' for r in v90_ok) or 'none'} mm; keep firmware V90 radius ≤ {max(v90_ok or [0]):.0f} mm"),
        (f"Diagonal IR (DL, DR) sees a wall or post within {P.IR_RANGE:.0f} mm [A] over ≥ 80 % of a diagonal",
         all(dg["rays"][n][2] >= 0.8 for n in ("DL", "DR")),
         ", ".join(f"{n} {lo:.0f}-{hi:.0f} mm, {fr:.0%} in range" for n, (lo, hi, fr) in dg["rays"].items() if n[0] == "D")),
        ("Frontal crash at the stretch speed: 4 frame screws hold with ≥ 2x margin", crash_rows[-1][3] >= 2,
         f"{crash_rows[-1][0]:.1f} m/s: {crash_rows[-1][2]:.0f} N mean, margin {crash_rows[-1][3]:.1f}x"),
        ("Axle deflection at the tyre under a 10 g shock < 20 µm", beam["defl_um"] < 20,
         f'{beam["defl_um"]:.1f} µm, {beam["stress"]:.0f} MPa'),
        ("All IR spots stay on the wall face (0-50 mm)", all(s["z_lo"] > 0 and s["z_hi"] < P.WALL_H for s in sens),
         ", ".join(f'{s["name"]} {s["z_lo"]:.0f}-{s["z_hi"]:.0f}' for s in sens)),
    ]
    if not P.FAN:
        checks = [c for c in checks if not c[0].startswith("Fan downforce")]

    export(parts)
    renders(parts, sens)
    diagonal_figure(hull)

    with open(os.path.join(OUT, "build_report.md"), "w") as f:
        f.write(f"# {VARIANT} build report (generated by cad_design/source/build.py{'' if P.FAN else ' --no-fan'}, do not edit)\n\n")
        f.write("## Checks\n\n| Check | Result | Value |\n|---|---|---|\n")
        for n, ok, v in checks:
            f.write(f"| {n} | {'PASS' if ok else 'FAIL'} | {v} |\n")
        f.write("\n## Key dimensions\n\n")
        f.write(f"- Overall {L:.1f} (L) x {W:.1f} (W) x {zmax:.1f} (H) mm; track {M.TRACK:.1f} mm; "
                f"wheel Ø{P.WHEEL_D:.0f} mm\n- Plate (PCB) underside z = {M.PLATE_Z0:.1f} mm; IR beam z = {M.SENS_Z:.1f} mm\n")
        f.write("\n## Mass and CG (origin: floor under axle centre; x fwd, y left, z up)\n\n"
                "| Part | Material | Mass g | CG x | CG y | CG z |\n|---|---|---|---|---|---|\n")
        for n, mat, g, c in rows:
            f.write(f"| {n} | {mat} | {g:.2f} | {c[0]:.1f} | {c[1]:.1f} | {c[2]:.1f} |\n")
        f.write(f"| **Total** | | **{mass:.1f}** | **{cg[0]:+.1f}** | **{cg[1]:+.2f}** | **{cg[2]:.1f}** |\n")
        f.write("\nMasses of bought parts and the 85 % print fill are [A] until weighed (Phase 6A).\n")
        f.write(f"\n## Pitch and grip, {'fan on' if P.FAN else 'no fan'} (quasi-static, tyre μ = 1.0 [A])\n\n")
        f.write(f"- Rests on: {dyn['rests_on']}\n- Nose lifts onto the rear skid above "
                f"{dyn['nose_lift_accel']:.1f} m/s² forward acceleration (harmless, 2-skid rocking)\n"
                f"- Braking grip limit with load transfer to the front skid: {dyn['brake_grip_limit']:.1f} m/s²\n"
                f"- Acceleration grip limit on the rear skid: {dyn['accel_grip_limit']:.1f} m/s²\n"
                f"- Total pitch range between skids: {dyn['pitch_range_deg']:.2f}°, "
                f"moves an IR spot {dyn['beam_shift_100mm']:.1f} mm at 100 mm\n")
        if P.FAN:
            f.write(f"\n## Suction fan\n\n"
                    f"- 0716 coreless [A] driving a {P.IMPELLER_D:.0f} mm, {P.IMPELLER_BLADES}-blade centrifugal impeller at x = {P.FAN_CENTER_X:.0f} mm\n"
                    f"- Skirt (suction pan) area {skirt_A:.0f} mm², centroid x = {skirt_xc:+.1f} mm, {P.SKIRT_GAP} mm off the floor\n"
                    f"- Design downforce {P.FAN_DOWNFORCE_G:.0f} gf [A] = {dyn['f']:.2f}x robot weight; needs {dp_needed:.0f} Pa under the pan\n"
                    f"- Grip with fan: braking {dyn['brake_grip_limit']:.1f} m/s², accelerating {dyn['accel_grip_limit']:.1f} m/s² "
                    f"(fan off: {dyn0['brake_grip_limit']:.1f} / {dyn0['accel_grip_limit']:.1f})\n"
                    f"- Fan current {P.FAN_CURRENT_A} A [A], needs its own low-side MOSFET channel (the dual H-bridge is used by the wheels)\n")
        else:
            f.write("\n## Suction fan\n\nNot fitted in this variant (owner decision 2026-10-21). The PCB keeps the fan MOSFET footprint unpopulated; "
                    "build with `python3 build.py` (no flag) for the fan version.\n")
        f.write("\n## IR geometry (mouse centred in a cell, walls on three sides)\n\n"
                "| Sensor | Mouth x, y | Yaw | Hits | Distance mm | Spot z range mm | No front wall: side wall hit |\n"
                "|---|---|---|---|---|---|---|\n")
        for s in sens:
            sd = (f"{s['side_dist']:.1f} mm, at x={s['side_hit_x']:.0f} (posts at x=±90)" if s["side_dist"] else "n/a")
            f.write(f"| {s['name']} | {s['x']:.1f}, {s['y']:.1f} | {s['yaw']:+.0f}° | {s['wall']} at x={s['hit'][0]:.0f} "
                    f"| {s['dist']:.1f} | {s['z_lo']:.1f} to {s['z_hi']:.1f} | {sd} |\n")
        f.write("\n## Diagonal running (Rev A.1)\n\n"
                f"- Corridor between post corners on a 45° staircase: {dg['corridor']:.1f} mm "
                f"(= 2 x ({P.CELL:.0f}/2 - {P.WALL_T:.0f})/√2, from the APEC cell and post sizes)\n"
                f"- Mouse width across the corridor: {dg['proj_0']:.1f} mm square-on, {dg[f'proj_{P.DIAG_HEADING_ERR:g}']:.1f} mm at {P.DIAG_HEADING_ERR:.0f}° heading error\n"
                f"- Clearance on a diagonal straight: {dg['straight_nom']:.1f} mm per side centred; "
                f"{dg['straight_worst']:.1f} mm with ±{P.DIAG_LATERAL_ERR:.0f} mm and ±{P.DIAG_HEADING_ERR:.0f}° [A] applied together\n\n"
                "| Manoeuvre | Radius mm | Clearance centred mm | Clearance with errors mm |\n|---|---|---|---|\n")
        for r, n, w in dg["t45"]:
            f.write(f"| 45° in / out | {r:.0f} | {n:.1f} | {w:.1f} |\n")
        for r, n, w in dg["v90"]:
            f.write(f"| V90 (diagonal to diagonal) | {r:.0f} | {n:.1f} | {w:.1f} |\n")
        f.write("\nIR on a diagonal straight (distance to the first wall or post over one 180 mm period):\n\n"
                + "".join(f"- {n}: {lo:.0f} to {hi:.0f} mm, within {P.IR_RANGE:.0f} mm for {fr:.0%} of the period\n" if hi < 999 else
                          f"- {n}: looks along the corridor, no wall within 400 mm until the diagonal ends (used for the end wall)\n"
                          for n, (lo, hi, fr) in dg["rays"].items()))
        f.write("\n## Crash and stiffness (Rev A.1)\n\n| Speed m/s | Energy J | Mean bumper force N | 4 x M2 shear margin |\n|---|---|---|---|\n")
        for v, e, fo, mg in crash_rows:
            f.write(f"| {v:.1f} | {e:.3f} | {fo:.0f} | {mg:.1f}x |\n")
        f.write(f"\nBumper stroke {P.BUMPER_STROKE} mm [A]. Axle: {beam['L']:.1f} mm overhang from the outer bearing to the tyre centre, "
                f"{beam['F']:.1f} N per wheel at {P.SHOCK_G:.0f} g [A]{' with the fan on' if P.FAN else ''}: deflection {beam['defl_um']:.1f} µm, "
                f"bending stress {beam['stress']:.0f} MPa (stainless yield ≈ 200+ MPa).\n")
        f.write("\n## Interference check\n\n")
        if not clashes:
            f.write("No overlapping solids.\n")
        for a, b, v, why in clashes:
            f.write(f"- {a} x {b}: {v:.2f} mm³ — {why or 'CLASH'}\n")
        f.write("\n## Tyre clearances\n\n" + "".join(f"- {t} to {o}: {d:.2f} mm\n" for t, o, d in tire_clear))

    for n, ok, v in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {n}: {v}")
    print(f"mass {mass:.1f} g, CG {cg[0]:+.1f} {cg[1]:+.2f} {cg[2]:.1f}")
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
