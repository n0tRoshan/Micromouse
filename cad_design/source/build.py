"""Build Rev A: run checks, export STEP/STL/DXF, render views into assets/, write build_report.md.

Usage:  python3 build.py            (from cad/src)
"""
import itertools
import math
import os
import sys

import numpy as np
import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

import params as P
import micromouse as M
import render as R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, ".."))                 # cad_design/
ASSETS = os.path.normpath(os.path.join(HERE, "..", "..", "assets"))
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
    _, xd = skirt_area_centroid()
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


def export(parts):
    import shutil
    for d in ("step", "stl"):
        shutil.rmtree(os.path.join(OUT, d), ignore_errors=True)
    os.makedirs(os.path.join(OUT, "step"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "stl"), exist_ok=True)
    asm = cq.Assembly(name="micromouse_revA")
    for p in parts:
        asm.add(p.shape, name=p.name, color=cq.Color(*p.color))
    asm.save(os.path.join(OUT, "step", "micromouse_revA_assembly.step"))
    for p in parts:
        cq.exporters.export(p.shape, os.path.join(OUT, "step", f"{p.name}.step"))
        if p.printable or p.name == "plate":
            cq.exporters.export(p.shape, os.path.join(OUT, "stl", f"{p.name}.stl"),
                                tolerance=0.02, angularTolerance=0.1)
    # DXF of the plate outline for PCB edge cuts / laser cutting
    cq.exporters.export(M.plate().section(M.PLATE_Z0 + P.PLATE_T / 2),
                        os.path.join(OUT, "step", "plate_outline.dxf"))


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
        ax.set_title(f"Micromouse Rev A, {fname.replace('_', ' ')}", fontsize=10); R.save(fig, f"{rd}/{fname}.png")

    # exploded with labels
    fig, ax = R.plt.subplots(figsize=(10, 8))
    r, u, w = R.draw(ax, ms(True), 35, 25)
    for p in parts:
        if p.name.endswith("_R") or p.name in ("imu", "motor_driver", "fan_mosfet", "ir_receivers"):
            continue                                  # label one side only
        c = np.array(p.centroid()) + np.array(p.explode)
        px, py = c @ r, c @ u
        k = parts.index(p)
        ax.annotate(p.name, (px, py), xytext=(px + 22 * (1 if k % 2 else -1) - (30 if k % 2 == 0 else 0), py + 8 + 4 * (k % 3)), fontsize=7,
                    arrowprops=dict(arrowstyle="-", lw=0.5, color="0.3"),
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="0.6", lw=0.4))
    ax.set_title("Rev A exploded view", fontsize=10); R.save(fig, f"{rd}/exploded.png")

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
    ax.annotate("impeller", (-P.FAN_CENTER_X, M.SKIRT_Z1 + 3), xytext=(-P.FAN_CENTER_X - 30, -12), fontsize=7,
                arrowprops=dict(arrowstyle="-", lw=0.5))
    ax.annotate("skirt (suction pan)", (20, M.SKIRT_Z0), xytext=(15, -12), fontsize=7, arrowprops=dict(arrowstyle="-", lw=0.5))
    ax.annotate("fan motor", (-P.FAN_CENTER_X, 28), xytext=(-P.FAN_CENTER_X - 25, 42), fontsize=7,
                arrowprops=dict(arrowstyle="-", lw=0.5))
    ax.set_ylim(-16, 46)
    ax.set_title("Section on the centre line (front to the left): fan, skirt and frame", fontsize=10)
    R.save(fig, f"{rd}/section_fan.png")

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
    dyn = dynamics(mass, cg, P.FAN_DOWNFORCE_G)
    skirt_A, skirt_xc = skirt_area_centroid()
    dp_needed = P.FAN_DOWNFORCE_G / 1000 * G / (skirt_A * 1e-6)
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
         f'{dyn0["brake_grip_limit"]:.1f} m/s² (fan on, {P.FAN_DOWNFORCE_G:.0f} gf [A]: {dyn["brake_grip_limit"]:.1f} m/s²)'),
        ("Fan downforce acts within 10 mm of the axle (loads the wheels, not the skids)", abs(skirt_xc) <= 10,
         f"skirt centroid x = {skirt_xc:+.1f} mm"),
        ("Skirt clears the floor by > 0.5 mm step at both pitch extremes", skirt_min > P.FLOOR_STEP_MAX,
         f'nose down {dyn["skirt_gap_nose_down"]:.2f} mm, tail down {dyn["skirt_gap_tail_down"]:.2f} mm'),
        ("Body ground clearance ≥ 3 mm above the skirt line (floor steps ≤ 0.5 mm)", clear_floor >= 3,
         f"min {clear_floor:.1f} mm"),
        ("Spur gear tips ≥ 2 mm off the floor", gear_floor >= 2, f"{gear_floor:.1f} mm"),
        ("Rear skid gap > 0.5 mm floor step rule", P.REAR_SKID_GAP > P.FLOOR_STEP_MAX, f"{P.REAR_SKID_GAP} mm"),
        ("Tyre clears every body part by ≥ 0.8 mm", min_tire[2] >= 0.8,
         f"closest {min_tire[0]} to {min_tire[1]}: {min_tire[2]:.2f} mm"),
        ("All IR spots stay on the wall face (0-50 mm)", all(s["z_lo"] > 0 and s["z_hi"] < P.WALL_H for s in sens),
         ", ".join(f'{s["name"]} {s["z_lo"]:.0f}-{s["z_hi"]:.0f}' for s in sens)),
    ]

    export(parts)
    renders(parts, sens)

    with open(os.path.join(OUT, "build_report.md"), "w") as f:
        f.write("# Rev A build report (generated by cad_design/source/build.py, do not edit)\n\n")
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
        f.write("\n## Pitch and grip, fan on (quasi-static, tyre μ = 1.0 [A])\n\n")
        f.write(f"- Rests on: {dyn['rests_on']}\n- Nose lifts onto the rear skid above "
                f"{dyn['nose_lift_accel']:.1f} m/s² forward acceleration (harmless, 2-skid rocking)\n"
                f"- Braking grip limit with load transfer to the front skid: {dyn['brake_grip_limit']:.1f} m/s²\n"
                f"- Acceleration grip limit on the rear skid: {dyn['accel_grip_limit']:.1f} m/s²\n"
                f"- Total pitch range between skids: {dyn['pitch_range_deg']:.2f}°, "
                f"moves an IR spot {dyn['beam_shift_100mm']:.1f} mm at 100 mm\n")
        f.write(f"\n## Suction fan\n\n"
                f"- 0716 coreless [A] driving a {P.IMPELLER_D:.0f} mm, {P.IMPELLER_BLADES}-blade centrifugal impeller at x = {P.FAN_CENTER_X:.0f} mm\n"
                f"- Skirt (suction pan) area {skirt_A:.0f} mm², centroid x = {skirt_xc:+.1f} mm, {P.SKIRT_GAP} mm off the floor\n"
                f"- Design downforce {P.FAN_DOWNFORCE_G:.0f} gf [A] = {dyn['f']:.2f}x robot weight; needs {dp_needed:.0f} Pa under the pan\n"
                f"- Grip with fan: braking {dyn['brake_grip_limit']:.1f} m/s², accelerating {dyn['accel_grip_limit']:.1f} m/s² "
                f"(fan off: {dyn0['brake_grip_limit']:.1f} / {dyn0['accel_grip_limit']:.1f})\n"
                f"- Fan current {P.FAN_CURRENT_A} A [A], needs its own low-side MOSFET channel (the dual H-bridge is used by the wheels)\n")
        f.write("\n## IR geometry (mouse centred in a cell, walls on three sides)\n\n"
                "| Sensor | Mouth x, y | Yaw | Hits | Distance mm | Spot z range mm | No front wall: side wall hit |\n"
                "|---|---|---|---|---|---|---|\n")
        for s in sens:
            sd = (f"{s['side_dist']:.1f} mm, at x={s['side_hit_x']:.0f} (posts at x=±90)" if s["side_dist"] else "n/a")
            f.write(f"| {s['name']} | {s['x']:.1f}, {s['y']:.1f} | {s['yaw']:+.0f}° | {s['wall']} at x={s['hit'][0]:.0f} "
                    f"| {s['dist']:.1f} | {s['z_lo']:.1f} to {s['z_hi']:.1f} | {sd} |\n")
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
