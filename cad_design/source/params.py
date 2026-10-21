"""Named parameters for the micromouse Rev A (initial build).

Units: mm, grams, degrees. Frame: x forward, y left, z up.
Origin: on the floor, directly below the wheel axle, on the robot's centre line.

Layout follows the APEC 2026 winners [C: APEC 2026 Micromouse Contest Report V2]:
2 coreless drive motors geared to the wheels (Decimus-5A, ZoroBot-A), AS5047P magnetic encoders on
the wheel axles running in bearings (KOGUMA-CHAN), one rigid frame (KOGUMA-CHAN), a suction fan on
the centre line (all top 3), 4 shrouded IR pairs (all top 3), 2S LiPo (Decimus-5A), thin PCB on top.
Nothing is carried over from the inherited Micromouse-main design.

Every value carries a tag: [C: source] confirmed, [A] assumed (re-check when the part is bought or
Phase 2/3 fixes it), [D] design choice (see docs/design_notes.md).
"""

# ---------------------------------------------------------------- maze (rules)
CELL = 180.0              # [C: APEC rules I.1, IEEE R2] cell pitch
WALL_T = 12.0             # [C: APEC rules I.1] wall thickness
WALL_H = 50.0             # [C: APEC rules I.1] wall height
PASSAGE = CELL - WALL_T   # 168 mm clear passage
FOOTPRINT_MAX = 250.0     # [C: APEC rules II.1] 25 x 25 cm
FLOOR_STEP_MAX = 0.5      # [C: APEC rules I.5] max floor step

# ---------------------------------------------------------------- wheels and axles
WHEEL_D = 24.0            # [C: KOGUMA-CHAN.Mk3 24 mm; Decimus-5A 22 mm, APEC 2026 report]
TIRE_T = 2.0              # [A] silicone/PU tyre radial thickness
TIRE_W = 6.0              # [D]
HUB_W = 7.7               # [D]
LIP_H = 0.75              # [D] lips stop the tyre walking off (Decimus tyre-shedding note)
LIP_W = 0.85              # [D]
WHEEL_OUT_Y = 37.0        # [D] outer face of each wheel: 74 mm wide, like Decimus-5A's 76 mm
AXLE_D = 3.0              # [D] steel shaft, turns with the wheel
BEARING = (3.0, 6.0, 2.5) # [C: MR63ZZ catalogue] bore, OD, width; two per wheel
BEARING_MASS = 0.3        # [A]
# Axle retention (Rev A.1). The inner races of both bearings are clamped between an outer shim and an inner
# spacer, so the axle has no end play and the encoder magnet sits at a fixed gap. The hub is held by one M2
# screw into the axle end and drives through a D-flat, so a wheel comes off without touching the encoder side.
AXLE_STICK = 3.0          # [D] axle length inboard of the wall: spacer 1.9 + e-clip 0.4 + 0.7 land beyond the groove
SPACER = (3.1, 4.0, 1.9)  # [A] inner spacer ID, OD, length. OD must stay inside the MR63ZZ shield bore: check with calipers
SHIM = (3.1, 4.0, 0.3)    # [A] outer shim between the spur and the outer bearing's inner race (fills GEAR_GAP)
ECLIP = (6.0, 0.4)        # [A] stainless e-clip for a 3 mm shaft (DIN 6799 type), OD, thickness; groove cut in the axle
AXLE_FLAT = 0.5           # [D] D-flat depth along the hub section; the hub bore matches it
HUB_CB = (5.4, 1.8)       # [D] counterbore in the hub's outer face for an M2 washer (OD 5) and screw head
AXLE_END_RECESS = 0.2     # [D] axle end sits below the counterbore floor so the washer clamps the hub, not the axle
HUB_SCREW_MASS = 0.20     # [A] M2 x 4 screw + washer, steel
AXLE_HW_MASS = 0.15       # [A] spacer + shim + e-clip per side

# ---------------------------------------------------------------- drive: coreless motor + spur gears
MOTOR_D = 8.5             # [A: 8520 coreless, as on Biscuit 2 and ZoroBot-A, APEC 2026 report]
MOTOR_LEN = 20.0          # [A]
MOTOR_MASS = 5.0          # [A]
MOTOR_SHAFT_D = 1.0       # [A]
GEAR_MODULE = 0.5         # [C: ZoroBot-A 0.5M, APEC 2026 report]
PINION_T = 8              # [C: ZoroBot-A 8T pinion]
SPUR_T = 36               # [D] 4.5:1. 36T keeps the spur 2.5 mm off the floor (40T would sit at 1.5 mm)
GEAR_W = 2.0              # [D]
GEAR_GAP = 0.3            # [D] wall face to gear face
MOTOR_BEHIND = True       # [D] motors sit behind the axle, so the centre stays free for the fan

# ---------------------------------------------------------------- encoders (magnetic, on the wheel axle)
MAGNET = (4.0, 2.0)       # [A] diametric magnet dia, thickness, glued to the axle's inner end
ENC_BOARD = (10.0, 10.0, 1.0)  # [A] AS5047P breakout (x, z, thickness)
ENC_AIR_GAP = 1.0         # [A] chip face to magnet. Datasheet asks for 35-70 mT at the die (ref. magnet 8x3 mm); our 4x2 magnet needs the AGC/MAG check in 6A

# ---------------------------------------------------------------- one-piece frame (bearing walls + motor tubes + skirt + fan housing)
WALL_T_FRAME = 5.0        # [D] = two MR63 bearings back to back
WALL_X = (-22.0, 10.0)    # [D] side-wall extent along x
MOTOR_TUBE_WALL = 1.0     # [D]
MOTOR_FIT = 0.05          # [D] per side; the tube has a top slit so it clamps
INSERT_HOLE = 3.2         # [C: M2 heat-set insert, typical 3.2 mm hole] in each wall top
FRAME_SCREWS_X = (-19.5, 6.5)  # [D] two per wall, clear of the motor tube and bearing bore

# ---------------------------------------------------------------- plate (thin PCB chassis on top of the frame)
PLATE_T = 1.0             # [D] thin FR4 like the winners (Cutting Through The Fog: 0.8 mm)
PLATE_FRONT = 55.0        # [D]
PLATE_REAR = -40.0        # [D]
PLATE_HALF_W = 35.5       # [D] plate + 1.5 mm bumper = 37 = tyre outer face, so the tyres set the 74 mm overall width
NOSE_FILLET = 18.0        # [D] round nose slides off posts
TAIL_FILLET = 10.0        # [D]
WELL_CLEAR = 1.0          # [D]
ENC_SLOT = (8.0, 3.0)     # [D] x, y slot in the plate above each encoder board for its 8 wires (ABI + SPI + power)
MOTOR_SLOT = (3.0, 10.0, -33.5)  # [D] x, y, centre x: slot behind the battery for both drive-motor leads
FR4_DENSITY = 1.85        # [C: FR4 typical]

# ---------------------------------------------------------------- suction fan, on the centre line
FAN_CENTER_X = 7.0        # [D] just ahead of the axle; the motor tubes sit behind it (1.2 mm clear)
FAN_MOTOR_D = 7.0         # [A: 0716 coreless, as on Theseus, APEC 2026 report]
FAN_MOTOR_LEN = 16.0      # [A]
FAN_MOTOR_MASS = 2.5      # [A]
FAN_SHAFT_D = 1.0         # [A]
IMPELLER_D = 20.0         # [D] open-eye centrifugal, 8 radial blades
IMPELLER_H = 4.5          # [D]
IMPELLER_BLADES = 8       # [D]
IMPELLER_HUB_D = 3.5      # [D]
HOUSING_ID = 22.0         # [D] 1 mm tip clearance
HOUSING_WALL = 1.2        # [D]
INLET_D = 11.0            # [D]
SKIRT_GAP = 1.3           # [D] skirt underside to floor; keeps > 0.6 mm when the tail drops onto its skid
SKIRT_T = 1.0             # [D]
SKIRT_X = (-36.0, 42.0)   # [D] the skirt is the frame floor and carries both skids
SKIRT_HALF_Y = 25.0       # [D] inside the spur gears
FAN_DOWNFORCE_G = 150.0   # [A] gram-force at working PWM; Decimus-5A reports > 2x mass. Scale test in 6A
FAN_CURRENT_A = 0.6       # [A] 0716 at 7.4 V, PWM-limited

# ---------------------------------------------------------------- skids: domes moulded into the skirt
SKID_D = 6.0              # [D] PTFE tape over a printed dome
FRONT_SKID_X = 40.0       # [D]
FRONT_SKID_GAP = 0.3      # [D] nose rests here (CG ahead of axle)
REAR_SKID_X = -34.0       # [D]
REAR_SKID_GAP = 0.6       # [D] > FLOOR_STEP_MAX

# ---------------------------------------------------------------- IR sensors (4 pairs, pulsed)
LED_D = 3.0               # [C: T-1 3 mm] SFH4550 emitter / TEFT4300 receiver (Decimus-5A)
LED_BORE = 3.2            # [D]
PAIR_PITCH = 4.6          # [D] septum = 1.4 mm
SENS_BLOCK_DEPTH = 12.0   # [D]
SENS_BLOCK_WALL = 1.2     # [D]
# (name, x, y, yaw deg, positive = left). x, y = bore mouth on the block's outer face
SENSORS = [
    ("FL", 54.0, 14.0, 0.0),     # [D] front pair, parallel to travel
    ("FR", 54.0, -14.0, 0.0),
    ("DL", 46.5, 31.5, 50.0),    # [D] diagonals far forward (Decimus 2 alignment-error fix)
    ("DR", 46.5, -31.5, -50.0),
]
IR_HALF_ANGLE = 12.0      # [A] shroud-limited cone

# ---------------------------------------------------------------- battery (2S LiPo) on the plate, behind the fan motor
BATT = (18.0, 44.0, 11.0) # [A] 2S 240 mAh (Decimus-5A uses 2S 240 mAh 25C): x, y, z
BATT_MASS = 15.0          # [A]
BATT_CX = -18.0           # [D] tuned so the CG lands 0-6 mm ahead of the axle
HOLDER_WALL = 1.2         # [D]
HOLDER_FIT = 0.4          # [D]
HOLDER_H = 5.0            # [D] rail height; a strap or tape goes over the top

# ---------------------------------------------------------------- electronics on the PCB (chip bodies only)
# (name, x size, y size, z size, centre x, centre y, mass)
CHIPS = [
    ("mcu", 10.0, 10.0, 1.6, 26.0, 0.0, 0.5),         # [A] STM32F405/F446 LQFP64 (all top 3 use STM32)
    ("imu", 3.0, 3.0, 1.0, 0.0, 0.0, 0.05),           # [D] LSM6DSR-class IMU on the turn centre
    ("motor_driver", 3.0, 3.0, 1.0, -3.0, 10.0, 0.05),  # [A] DRV8835 (Decimus-5A)
    ("fan_mosfet", 3.0, 3.0, 1.0, -3.0, -10.0, 0.05),   # [A] low-side MOSFET for the fan
]
COMPONENTS_MASS = 3.0     # [A] passives, regulator, connectors on the PCB, lumped
MISC_MASS = 3.0           # [A] wiring, screws, inserts

# ---------------------------------------------------------------- bumper
BUMPER_T = 1.5            # [D] TPU 95A band around the nose, below the IR beams
BUMPER_H = 5.0            # [D]

# ---------------------------------------------------------------- diagonal running (Rev A.1)
# Corridor between post corners on a 45° staircase: 2 x (CELL/2 - WALL_T/2)/sqrt(2) = 110.3 mm (geometry of APEC I.1)
DIAG_HEADING_ERR = 5.0    # [A] worst heading error while running diagonals (Phase 6E target is < 2°)
DIAG_LATERAL_ERR = 5.0    # [A] worst lateral offset from the diagonal centre line
DIAG_MIN_CLEAR = 5.0      # [D] required clearance to every post and wall with both errors applied
TURN45_R = (45.0, 60.0, 75.0, 90.0, 110.0)  # [D] 45° in/out turn radii to check
V90_R = (40.0, 50.0, 60.0, 75.0, 90.0)      # [D] diagonal-to-diagonal 90° (V90) turn radii to check
IR_RANGE = 180.0          # [A] longest distance at which a wall is still read reliably (Phase 6C measures it)

# ---------------------------------------------------------------- crash and stiffness (Rev A.1)
CRASH_SPEEDS = (1.0, 2.0) # [D] m/s: Phase 2 cruise start value and the stretch speed
BUMPER_STROKE = 1.0       # [A] TPU bumper crush before the plate edge takes load
SHOCK_G = 10.0            # [A] wheel load factor for a drop or a hard landing
M2_SHEAR_N = 870.0        # [C: ISO 3506 A2-70, Rm 700 MPa x 0.6 x 2.07 mm² stress area] per screw

# ---------------------------------------------------------------- print materials
PETG_DENSITY = 1.27       # [C: typical PETG]
TPU_DENSITY = 1.21        # [C: typical TPU 95A]
PRINT_FILL = 0.85         # [A] effective solid fraction for small parts
