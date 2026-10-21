"""Parametric micromouse Rev A (initial build): every part is built from params.py.

build_parts() returns a list of Part records in assembly position.
Left-side parts are modelled at +y and mirrored for the right side.
"""
import math
from dataclasses import dataclass

import cadquery as cq

import params as P

# ------------------------------------------------------------ derived geometry
AXLE_Z = P.WHEEL_D / 2
HUB_Y1 = P.WHEEL_OUT_Y
HUB_Y0 = HUB_Y1 - P.HUB_W
GEAR_Y1 = HUB_Y0
GEAR_Y0 = GEAR_Y1 - P.GEAR_W
WALL_Y1 = GEAR_Y0 - P.GEAR_GAP                 # outer face of the bearing wall
WALL_Y0 = WALL_Y1 - P.WALL_T_FRAME
TRACK = HUB_Y0 + HUB_Y1                        # tyre centre to tyre centre
PINION_R = P.GEAR_MODULE * P.PINION_T / 2
SPUR_R = P.GEAR_MODULE * P.SPUR_T / 2
SPUR_OD_R = SPUR_R + P.GEAR_MODULE
CENTRE_DIST = PINION_R + SPUR_R
MOTOR_X = -CENTRE_DIST if P.MOTOR_BEHIND else CENTRE_DIST
MOTOR_Y1 = WALL_Y0 + 2.0                       # motor face sits 2 mm into the wall pocket
MOTOR_Y0 = MOTOR_Y1 - P.MOTOR_LEN
TUBE_R = P.MOTOR_D / 2 + P.MOTOR_FIT + P.MOTOR_TUBE_WALL
AXLE_Y0 = WALL_Y0 - P.AXLE_STICK               # axle sticks out inboard for the spacer, e-clip and magnet
AXLE_Y1 = HUB_Y1 - P.HUB_CB[1] - P.AXLE_END_RECESS   # axle end, just below the hub counterbore floor
MAG_Y0 = AXLE_Y0 - P.MAGNET[1]
ENC_CHIP_T = 0.9
ENC_CHIP_Y1 = MAG_Y0 - P.ENC_AIR_GAP
ENC_BOARD_Y1 = ENC_CHIP_Y1 - ENC_CHIP_T
ENC_BOARD_Y0 = ENC_BOARD_Y1 - P.ENC_BOARD[2]
RIB_T = 1.0
RIB_Y0 = ENC_BOARD_Y0 - RIB_T
PLATE_Z0 = round(AXLE_Z + TUBE_R + 0.2, 2)      # plate underside just clears the motor tubes
PLATE_Z1 = PLATE_Z0 + P.PLATE_T
SKIRT_Z0 = P.SKIRT_GAP
SKIRT_Z1 = P.SKIRT_GAP + P.SKIRT_T
IMP_Z0 = SKIRT_Z1 + 0.5
CHAMBER_TOP = IMP_Z0 + P.IMPELLER_H + 0.8
COVER_T = 1.2
FAN_MOTOR_Z0 = CHAMBER_TOP + COVER_T
SENS_Z = PLATE_Z1 + P.SENS_BLOCK_WALL + P.LED_BORE / 2   # IR beam height


@dataclass
class Part:
    name: str
    shape: cq.Workplane
    color: tuple
    material: str
    density: float = 0.0          # g/cm3; 0 = use fixed mass
    mass: float = 0.0
    printable: bool = False
    explode: tuple = (0, 0, 0)

    def volume(self):
        return self.shape.val().Volume()

    def grams(self):
        if self.density:
            fill = P.PRINT_FILL if self.printable else 1.0
            return self.volume() / 1000.0 * self.density * fill
        return self.mass

    def centroid(self):
        c = cq.Shape.centerOfMass(self.shape.val())
        return (c.x, c.y, c.z)


def _box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _ycyl(d, y0, y1, x=0.0, z=AXLE_Z):
    """Cylinder along +y from y0 to y1."""
    return cq.Workplane("XZ").circle(d / 2).extrude(-(y1 - y0)).translate((x, y0, z))


def _zcyl(d, z0, z1, x=0.0, y=0.0):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, y, z0))


def _both(wp):
    return wp.union(wp.mirror("XZ"))


# ------------------------------------------------------------ drive train (left side, mirrored)
def motor():
    m = _ycyl(P.MOTOR_D, MOTOR_Y0, MOTOR_Y1, x=MOTOR_X)
    return m.union(_ycyl(P.MOTOR_SHAFT_D, MOTOR_Y1, GEAR_Y1, x=MOTOR_X))


def pinion():
    """8T 0.5M brass pinion, modelled at its pitch circle."""
    return _ycyl(2 * PINION_R, GEAR_Y0, GEAR_Y1, x=MOTOR_X).cut(
        _ycyl(P.MOTOR_SHAFT_D, GEAR_Y0 - 1, GEAR_Y1 + 1, x=MOTOR_X))


def spur():
    """36T 0.5M spur glued to the hub's inner face, modelled at its pitch circle."""
    return _ycyl(2 * SPUR_R, GEAR_Y0, GEAR_Y1).cut(_ycyl(P.AXLE_D, GEAR_Y0 - 1, GEAR_Y1 + 1))


def _d_shaft(d, y0, y1, flat):
    """Round shaft along +y with a flat on top (D profile)."""
    return _ycyl(d, y0, y1).cut(_box(-d, d, y0 - 1, y1 + 1, AXLE_Z + d / 2 - flat, AXLE_Z + d))


def axle():
    """3 mm shaft: D-flat under the hub, M2 tapped hole in the outer end, e-clip groove at the inner end."""
    a = _ycyl(P.AXLE_D, AXLE_Y0, HUB_Y0).union(_d_shaft(P.AXLE_D, HUB_Y0, AXLE_Y1, P.AXLE_FLAT))
    a = a.cut(_ycyl(2.0, AXLE_Y1 - 4.0, AXLE_Y1 + 1))                       # M2 thread, modelled at 2.0
    gy = WALL_Y0 - P.SPACER[2]
    return a.cut(_ycyl(P.AXLE_D + 1, gy - P.ECLIP[1], gy).cut(_ycyl(2.3, gy - 1, gy + 1)))   # groove to 2.3


def axle_hw():
    """Inner spacer + e-clip (clamp the inner races from inside) and the outer shim (from outside)."""
    sid, sod, sl = P.SPACER
    sp = _ycyl(sod, WALL_Y0 - sl, WALL_Y0).cut(_ycyl(sid, WALL_Y0 - sl - 1, WALL_Y0 + 1))
    gy = WALL_Y0 - sl
    clip = _ycyl(P.ECLIP[0], gy - P.ECLIP[1], gy).cut(_ycyl(2.3, gy - 1, gy + 1))
    hid, hod, ht = P.SHIM
    shim = _ycyl(hod, WALL_Y1, WALL_Y1 + ht).cut(_ycyl(hid, WALL_Y1 - 1, WALL_Y1 + 1))
    return sp.union(clip).union(shim)


def hub_screw():
    """M2 x 4 screw and M2 washer in the hub counterbore, threaded into the axle end."""
    y0 = HUB_Y1 - P.HUB_CB[1]
    washer = _ycyl(5.0, y0, y0 + 0.3).cut(_ycyl(2.2, y0 - 1, y0 + 1))
    head = _ycyl(3.8, y0 + 0.3, y0 + 1.6)
    shank = _ycyl(2.0, AXLE_Y1 - 3.5, y0 + 0.3)
    return washer.union(head).union(shank)


def bearings():
    """Two MR63 bearings back to back in the wall bore."""
    b = None
    for k in range(2):
        y0 = WALL_Y0 + k * P.BEARING[2]
        r = _ycyl(P.BEARING[1], y0, y0 + P.BEARING[2]).cut(_ycyl(P.BEARING[0], y0 - 1, y0 + P.BEARING[2] + 1))
        b = r if b is None else b.union(r)
    return b


def hub():
    core_d = P.WHEEL_D - 2 * P.TIRE_T
    y0 = HUB_Y0 + (P.HUB_W - P.TIRE_W) / 2
    h = _ycyl(core_d, HUB_Y0, HUB_Y1)
    h = h.union(_ycyl(core_d + 2 * P.LIP_H, HUB_Y0, y0))
    h = h.union(_ycyl(core_d + 2 * P.LIP_H, y0 + P.TIRE_W, HUB_Y1))
    h = h.cut(_d_shaft(P.AXLE_D + 0.05, HUB_Y0 - 1, HUB_Y1 + 1, P.AXLE_FLAT))   # D bore drives the wheel
    h = h.cut(_ycyl(P.HUB_CB[0], HUB_Y1 - P.HUB_CB[1], HUB_Y1 + 1))               # washer + screw head
    for k in range(5):                                   # lightening holes
        a = 2 * math.pi * k / 5
        r = 5.6
        h = h.cut(_ycyl(2.8, HUB_Y0 + 1.2, HUB_Y1 + 0.1, x=r * math.cos(a), z=AXLE_Z + r * math.sin(a)))
    return h


def tire():
    y0 = HUB_Y0 + (P.HUB_W - P.TIRE_W) / 2
    core_d = P.WHEEL_D - 2 * P.TIRE_T
    return _ycyl(P.WHEEL_D, y0, y0 + P.TIRE_W).cut(_ycyl(core_d, y0, y0 + P.TIRE_W))


def magnet():
    return _ycyl(P.MAGNET[0], MAG_Y0, AXLE_Y0)


def encoder():
    """AS5047P breakout on the frame rib, chip facing the axle magnet."""
    bx, bz, bt = P.ENC_BOARD
    board = _box(-bx / 2, bx / 2, ENC_BOARD_Y0, ENC_BOARD_Y1, AXLE_Z - bz / 2, AXLE_Z + bz / 2)
    chip = _box(-2.5, 2.5, ENC_BOARD_Y1, ENC_CHIP_Y1, AXLE_Z - 2.5, AXLE_Z + 2.5)
    return board.union(chip)


# ------------------------------------------------------------ frame: one rigid printed part
def fan_housing_solid():
    od = P.HOUSING_ID + 2 * P.HOUSING_WALL
    return _zcyl(od, SKIRT_Z1, FAN_MOTOR_Z0, x=P.FAN_CENTER_X)


def frame():
    """Skirt floor + both bearing walls + motor tubes + encoder ribs + fan housing and motor collar + skid domes.
    Both axle bores are cut through both walls in one operation, so the wheels are coaxial by
    construction (fixes the drive-train alignment drift seen on 4WD mice and Decimus's printed mounts)."""
    x0, x1 = P.SKIRT_X
    f = _box(x0, x1, -P.SKIRT_HALF_Y, P.SKIRT_HALF_Y, SKIRT_Z0, SKIRT_Z1).edges("|Z").fillet(6)
    wx0, wx1 = P.WALL_X
    walls = _box(wx0, wx1, WALL_Y0, WALL_Y1, SKIRT_Z0, PLATE_Z0)
    tube = _ycyl(2 * TUBE_R, MOTOR_Y0, WALL_Y0 + 0.01, x=MOTOR_X)
    rib = _box(-P.ENC_BOARD[0] / 2 - 1, P.ENC_BOARD[0] / 2 + 1, RIB_Y0, ENC_BOARD_Y0, SKIRT_Z1, PLATE_Z0)
    f = f.union(_both(walls)).union(_both(tube)).union(_both(rib))
    if P.FAN:
        f = f.union(fan_housing_solid())
    # skid domes under the skirt
    for (sx, gap) in ((P.FRONT_SKID_X, P.FRONT_SKID_GAP), (P.REAR_SKID_X, P.REAR_SKID_GAP)):
        r = P.SKID_D / 2
        dome = cq.Workplane("XY").sphere(r).translate((sx, 0, gap + r)).intersect(
            _box(sx - r, sx + r, -r, r, gap, SKIRT_Z0 + 0.01))
        f = f.union(dome)
    # axle bores straight through both walls (one cut), motor bores, motor shaft holes
    f = f.cut(_ycyl(P.BEARING[1], -WALL_Y1 - 1, WALL_Y1 + 1).intersect(
        _both(_box(-10, 10, WALL_Y0 - 0.01, WALL_Y1 + 1, 0, 30))))
    f = f.cut(_both(_ycyl(P.MOTOR_D + 2 * P.MOTOR_FIT, MOTOR_Y0 - 1, MOTOR_Y1, x=MOTOR_X)))
    f = f.cut(_both(_ycyl(1.6, MOTOR_Y1 - 0.1, WALL_Y1 + 1, x=MOTOR_X)))
    # clamp slit along the top of each motor tube
    f = f.cut(_both(_box(MOTOR_X - 0.5, MOTOR_X + 0.5, MOTOR_Y0 - 1, WALL_Y0 - 0.5, AXLE_Z, PLATE_Z0 + 1)))
    if not P.FAN:
        return _insert_holes(f)
    # fan: chamber, inlet through the skirt, shaft hole in the cover, exhaust windows
    c = P.FAN_CENTER_X
    od = P.HOUSING_ID + 2 * P.HOUSING_WALL
    f = f.cut(_zcyl(P.HOUSING_ID, SKIRT_Z1 - 0.01, CHAMBER_TOP, x=c))
    f = f.cut(_zcyl(P.INLET_D, SKIRT_Z0 - 0.5, SKIRT_Z1 + 0.01, x=c))
    f = f.cut(_zcyl(3.0, CHAMBER_TOP - 0.01, FAN_MOTOR_Z0 + 0.01, x=c))
    # collar on the cover: the fan motor pushes in from above and is held by friction + a drop of glue
    f = f.union(_zcyl(P.FAN_MOTOR_D + 2.4, FAN_MOTOR_Z0, FAN_MOTOR_Z0 + 4.0, x=c).cut(
        _zcyl(P.FAN_MOTOR_D + 0.1, FAN_MOTOR_Z0 - 1, FAN_MOTOR_Z0 + 5, x=c)))
    for ang in (35, -35):                          # forward-sideways, clear of the motor tubes behind
        win = (_box(od / 2 - 2.5, od / 2 + 1, -4.5, 4.5, SKIRT_Z1 + 0.6, CHAMBER_TOP - 0.4)
               .rotate((0, 0, 0), (0, 0, 1), ang).translate((c, 0, 0)))
        f = f.cut(win)
    for ang in (90, -90):
        win = (_box(od / 2 - 2.5, od / 2 + 1, -4.5, 4.5, SKIRT_Z1 + 0.6, CHAMBER_TOP - 0.4)
               .rotate((0, 0, 0), (0, 0, 1), ang).translate((c, 0, 0)))
        f = f.cut(win)
    return _insert_holes(f)


def _insert_holes(f):
    # M2 heat-set insert holes in the wall tops
    for x in P.FRAME_SCREWS_X:
        for s in (1, -1):
            f = f.cut(_zcyl(P.INSERT_HOLE, PLATE_Z0 - 4.0, PLATE_Z0 + 0.1, x=x, y=s * (WALL_Y0 + WALL_Y1) / 2))
    return f


def impeller():
    """Open-eye centrifugal impeller: backplate on the motor side, radial blades face the inlet."""
    c = P.FAN_CENTER_X
    back_t = 0.8
    zb = IMP_Z0 + P.IMPELLER_H - back_t
    imp = _zcyl(P.IMPELLER_D, zb, zb + back_t, x=c)
    imp = imp.union(_zcyl(P.IMPELLER_HUB_D, IMP_Z0, zb + back_t, x=c))
    for k in range(P.IMPELLER_BLADES):
        blade = _box(P.IMPELLER_HUB_D / 2 - 0.2, P.IMPELLER_D / 2, -0.4, 0.4, IMP_Z0, zb + 0.01)
        imp = imp.union(blade.rotate((0, 0, 0), (0, 0, 1), 360.0 * k / P.IMPELLER_BLADES).translate((c, 0, 0)))
    return imp.cut(_zcyl(P.FAN_SHAFT_D, IMP_Z0 - 0.5, zb + 1, x=c))


def fan_motor():
    c = P.FAN_CENTER_X
    m = _zcyl(P.FAN_MOTOR_D, FAN_MOTOR_Z0, FAN_MOTOR_Z0 + P.FAN_MOTOR_LEN, x=c)
    return m.union(_zcyl(P.FAN_SHAFT_D, IMP_Z0 + 0.3, FAN_MOTOR_Z0, x=c))


# ------------------------------------------------------------ plate (PCB chassis)
def plate_outline():
    L = P.PLATE_FRONT - P.PLATE_REAR
    w = (cq.Workplane("XY").box(L, 2 * P.PLATE_HALF_W, P.PLATE_T, centered=(False, True, False))
         .translate((P.PLATE_REAR, 0, 0)))
    w = w.edges("|Z and >X").fillet(P.NOSE_FILLET)
    return w.edges("|Z and <X").fillet(P.TAIL_FILLET)


def sensor_block_holes():
    return [(P.PLATE_FRONT - 22, 22.0), (P.PLATE_FRONT - 22, -22.0)]


def holder_holes():
    return [(P.BATT_CX, P.BATT[1] / 2 + P.HOLDER_FIT + P.HOLDER_WALL + 2.0),
            (P.BATT_CX, -(P.BATT[1] / 2 + P.HOLDER_FIT + P.HOLDER_WALL + 2.0))]


def plate():
    p = plate_outline().translate((0, 0, PLATE_Z0))
    r = P.WHEEL_D / 2 + P.WELL_CLEAR
    y_in = WALL_Y1 - 0.5                           # wells also clear the spur gears
    p = p.cut(_both(_box(-r, r, y_in, 60, PLATE_Z0 - 1, PLATE_Z1 + 1)))
    holes = [(x, s * (WALL_Y0 + WALL_Y1) / 2) for x in P.FRAME_SCREWS_X for s in (1, -1)]
    holes += sensor_block_holes() + holder_holes()
    for (x, y) in holes:
        p = p.cut(_zcyl(2.3, PLATE_Z0 - 1, PLATE_Z1 + 1, x=x, y=y))
    # wire pass-throughs: encoder leads straight up from each board, motor leads up behind the battery
    sx, sy = P.ENC_SLOT
    ey = (ENC_BOARD_Y0 + ENC_CHIP_Y1) / 2
    p = p.cut(_both(_box(-sx / 2, sx / 2, ey - sy / 2, ey + sy / 2, PLATE_Z0 - 1, PLATE_Z1 + 1).edges("|Z").fillet(1.0)))
    mx, my, mcx = P.MOTOR_SLOT
    p = p.cut(_box(mcx - mx / 2, mcx + mx / 2, -my / 2, my / 2, PLATE_Z0 - 1, PLATE_Z1 + 1).edges("|Z").fillet(1.0))
    if not P.FAN:
        return p
    return p.cut(_zcyl(P.FAN_MOTOR_D + 0.4, PLATE_Z0 - 1, PLATE_Z1 + 1, x=P.FAN_CENTER_X))


def _sensor_bores():
    out = None
    for (_, x, y, yaw) in P.SENSORS:
        for off in (-P.PAIR_PITCH / 2, P.PAIR_PITCH / 2):
            c = (cq.Workplane("YZ").circle(P.LED_BORE / 2).extrude(P.SENS_BLOCK_DEPTH + 30)
                 .translate((-P.SENS_BLOCK_DEPTH, off, SENS_Z))
                 .rotate((0, 0, 0), (0, 0, 1), yaw).translate((x, y, 0)))
            out = c if out is None else out.union(c)
    return out


def sensor_block():
    """Black shroud that fixes every emitter/receiver angle and height, with an opaque septum
    between each emitter and its receiver."""
    z0, z1 = PLATE_Z1, SENS_Z + P.LED_BORE / 2 + P.SENS_BLOCK_WALL
    band = (plate_outline().translate((0, 0, z0)).faces(">Z").wires().toPending()
            .offset2D(-1.0).extrude(z1 - z0 - P.PLATE_T)).translate((0, 0, P.PLATE_T))
    band = band.intersect(_box(P.PLATE_FRONT - 28, P.PLATE_FRONT + 5, -60, 60, z0, z1))
    band = band.cut(_box(P.PLATE_FRONT - 40, P.PLATE_FRONT - 16, -19, 19, z0 - 1, z1 + 1).edges("|Z").fillet(3))
    band = band.cut(_sensor_bores())
    for (x, y) in sensor_block_holes():
        band = band.cut(_zcyl(2.3, z0 - 1, z1 + 1, x=x, y=y))
    return band


def leds():
    em, rx = None, None
    for (_, x, y, yaw) in P.SENSORS:
        for k, off in enumerate((-P.PAIR_PITCH / 2, P.PAIR_PITCH / 2)):
            c = (cq.Workplane("YZ").circle(P.LED_D / 2).extrude(4.6)
                 .translate((-P.SENS_BLOCK_DEPTH + 0.2, off, SENS_Z))
                 .rotate((0, 0, 0), (0, 0, 1), yaw).translate((x, y, 0)))
            if k == 0:
                em = c if em is None else em.union(c)
            else:
                rx = c if rx is None else rx.union(c)
    return em, rx


def battery_holder():
    """Two low rails and an end stop; the pack slides in from the left and a strap goes over it."""
    bx, by, _ = P.BATT
    f, w, h = P.HOLDER_FIT, P.HOLDER_WALL, P.HOLDER_H
    x0, x1 = P.BATT_CX - bx / 2 - f - w, P.BATT_CX + bx / 2 + f + w
    yh = by / 2 + f
    z0 = PLATE_Z1
    hld = _box(x0, x0 + w, -yh - w, yh, z0, z0 + h).union(_box(x1 - w, x1, -yh - w, yh, z0, z0 + h))
    hld = hld.union(_box(x0, x1, -yh - w, -yh, z0, z0 + h))
    for (x, y) in holder_holes():
        y_in = math.copysign(yh - 0.01, y)               # tab runs from the rail out to the screw
        hld = hld.union(_box(x - 3, x + 3, min(y_in, y + 3 * math.copysign(1, y)), max(y_in, y + 3 * math.copysign(1, y)),
                             z0, z0 + 1.5))
        hld = hld.cut(_zcyl(2.3, z0 - 1, z0 + 3, x=x, y=y))
    hld = hld.union(_box(x0, x0 + w + 2.5, yh, yh + 1.0, z0, z0 + 1.5))   # latch lip
    return hld


def battery():
    bx, by, bz = P.BATT
    return _box(P.BATT_CX - bx / 2, P.BATT_CX + bx / 2, -by / 2, by / 2, PLATE_Z1, PLATE_Z1 + bz).edges("|Y").fillet(1.5)


def bumper():
    """TPU band around the nose, below the IR beams."""
    z0 = PLATE_Z1 - P.BUMPER_H
    base = plate_outline().translate((0, 0, z0))
    outer = base.faces(">Z").wires().toPending().offset2D(P.BUMPER_T).extrude(-P.BUMPER_H).translate((0, 0, P.PLATE_T))
    inner = base.faces(">Z").wires().toPending().offset2D(0.0).extrude(-P.BUMPER_H - 1).translate((0, 0, P.PLATE_T + 0.5))
    band = outer.cut(inner)
    return band.intersect(_box(P.PLATE_FRONT - 30, P.PLATE_FRONT + 5, -60, 60, z0 - 1, z0 + P.BUMPER_H + 1))


def chip(spec):
    _, sx, sy, sz, cx, cy, _m = spec
    return _box(cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, PLATE_Z1, PLATE_Z1 + sz)


def build_parts():
    em, rx = leds()
    grey, brass, steel = (0.70, 0.70, 0.72), (0.85, 0.70, 0.30), (0.80, 0.80, 0.82)
    orange = (0.85, 0.45, 0.10)
    parts = [
        Part("frame", frame(), orange, "PETG, printed (one piece)", density=P.PETG_DENSITY, printable=True,
             explode=(0, 0, -35)),
        Part("plate", plate(), (0.10, 0.45, 0.20), "FR4 1.0 mm PCB (chassis)", density=P.FR4_DENSITY,
             explode=(0, 0, 30)),
    ]
    for side, s in (("L", 1), ("R", -1)):
        def m(wp):
            return wp if s > 0 else wp.mirror("XZ")
        parts += [
            Part(f"motor_{side}", m(motor()), grey, "8520 coreless", mass=P.MOTOR_MASS, explode=(0, s * 25, 0)),
            Part(f"pinion_{side}", m(pinion()), brass, "8T 0.5M brass", mass=0.15, explode=(0, s * 40, 0)),
            Part(f"spur_{side}", m(spur()), (0.95, 0.95, 0.95), "36T 0.5M nylon", mass=0.4, explode=(0, s * 48, 0)),
            Part(f"bearings_{side}", m(bearings()), steel, "2 x MR63ZZ", mass=2 * P.BEARING_MASS, explode=(0, s * 33, 0)),
            Part(f"axle_{side}", m(axle()), steel, "3 mm stainless shaft", density=7.9, explode=(0, s * 62, 0)),
            Part(f"axle_hw_{side}", m(axle_hw()), steel, "spacer, shim, e-clip", mass=P.AXLE_HW_MASS,
                 explode=(0, s * 18, -12)),
            Part(f"hub_screw_{side}", m(hub_screw()), (0.2, 0.2, 0.22), "M2 x 4 screw + washer",
                 mass=P.HUB_SCREW_MASS, explode=(0, s * 76, 0)),
            Part(f"hub_{side}", m(hub()), (0.95, 0.95, 0.95), "PETG, printed", density=P.PETG_DENSITY,
                 printable=True, explode=(0, s * 56, 0)),
            Part(f"tire_{side}", m(tire()), (0.12, 0.12, 0.12), "silicone/PU tyre", mass=0.6, explode=(0, s * 66, 0)),
            Part(f"magnet_{side}", m(magnet()), (0.6, 0.2, 0.2), "4x2 diametric magnet", mass=0.2,
                 explode=(0, s * 10, 0)),
            Part(f"encoder_{side}", m(encoder()), (0.15, 0.15, 0.45), "AS5047P breakout", mass=0.4,
                 explode=(0, s * 4, 20)),
        ]
    parts += [
        Part("impeller", impeller(), (0.95, 0.80, 0.15), "PETG/resin, printed", density=P.PETG_DENSITY,
             printable=True, explode=(0, 0, -55)),
        Part("fan_motor", fan_motor(), grey, "0716 coreless", mass=P.FAN_MOTOR_MASS, explode=(0, 0, 55)),
        Part("sensor_block", sensor_block(), (0.18, 0.18, 0.20), "black PETG, printed", density=P.PETG_DENSITY,
             printable=True, explode=(15, 0, 45)),
        Part("ir_emitters", em, (0.55, 0.65, 0.95), "SFH4550 x4", mass=4 * 0.25, explode=(15, 0, 45)),
        Part("ir_receivers", rx, (0.05, 0.05, 0.05), "TEFT4300 x4", mass=4 * 0.25, explode=(15, 0, 45)),
        Part("battery_holder", battery_holder(), orange, "PETG, printed", density=P.PETG_DENSITY,
             printable=True, explode=(-10, 0, 45)),
        Part("battery", battery(), (0.25, 0.35, 0.80), "2S LiPo", mass=P.BATT_MASS, explode=(-10, 60, 60)),
        Part("bumper", bumper(), (0.90, 0.20, 0.20), "TPU 95A, printed", density=P.TPU_DENSITY, printable=True,
             explode=(25, 0, 10)),
    ]
    if not P.FAN:
        parts = [p for p in parts if p.name not in ("impeller", "fan_motor")]
    for spec in P.CHIPS:
        parts.append(Part(spec[0], chip(spec), (0.08, 0.08, 0.08), "IC on PCB", mass=spec[6], explode=(0, 0, 35)))
    return parts
