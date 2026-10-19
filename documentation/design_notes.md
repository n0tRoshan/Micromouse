# Rev A (initial build): design notes

Date: 2026-10-19 · Phase 4 (CAD) · Governing rules: APEC/IEEE classic micromouse, stricter value where they differ ([rules brief](../research/rules_brief.md))
Tags: **[C: source]** confirmed, **[A]** assumed, **[D]** design choice backed by the reasoning here.
Generated numbers (mass, CG, clearances, checks) live in [`cad_design/build_report.md`](../cad_design/build_report.md). Rerun `cad_design/source/build.py` after any parameter change.

Rev A copies its architecture from the APEC 2026 winners. Nothing is carried over from the earlier SRA-VJTI-style design (ESP32 devkit, ToF sensors, N20 motors, gear-coupled 4 wheels).

## 1. Reference designs studied

| Mouse (event) | Layout | What Rev A takes from it | Flaws its builder or the record reports |
|---|---|---|---|
| **Decimus-5A** (APEC 2026, 1st) [C: S4] | 4WD + fan, 76 x 97 mm, 115 g, Faulhaber 1717 coreless, 35:10 gears, 22 mm wheels, SFH4550/TEFT4300 x4, 2S 240 mAh | Coreless + spur drive, 4 shrouded IR pairs, 2S 240 mAh pack, ~76 mm width | "No crumple zones"; "faster runs require stronger parts" [C: S4] |
| **KOGUMA-CHAN.Mk3** (APEC 2026, 2nd) [C: S4] | 2WD + fan, 120 x 70 mm, 78 g, 24 mm wheels, AS5047P encoders in a bearing-holder unit, carbon frame | 2WD, 24 mm wheels, magnetic encoders on the wheel axle, one rigid frame instead of a PCB chassis | None reported |
| **PIGGY-ONE** (APEC 2026, 3rd) [C: S4] | 4WD + fan, 120 g, STM32F446, LSM6DSR | STM32 + LSM6DSR-class IMU | 66.6 s search run (costs score under the /30 rule) |
| **ZoroBot-A** (APEC 2026) [C: S4] | 8520 coreless, 8T:40T 0.5M gears, 2S 260 mAh | 8520 motor and 0.5M 8T pinion | None stated |
| **Biscuit 2** (APEC 2026) [C: S4] | 8520 coreless x3 (2 drive + fan), ~240 g downforce, AS5047P | Coreless fan motor; downforce ~3x mass is achievable at this size | None stated |
| **Theseus** (APEC 2026, did not run) [C: S4] | 4WD, 7 x 16 mm coreless fan motor | 0716 fan motor size | "Frequent, high-speed crashes" |
| **Decimus (2012 build)** [C: S15, S16] | Printed wheels and mounts | | Mounts "not really rigid enough"; uneven toe-in; hubs too small for bearings; wheels not trued; tyres may shed |
| **Decimus 2** [C: S17] | | | Diagonal sensors too far back: wall edge seen 124 mm into the cell, too late for a 1 g turn |
| **4WD mouse, micromouseonline** [C: S7] | 4WD | | All wheels skid in turns; 0.2 mm drive-train shift reverses drift; nose tipped at 9 m/s² braking |

## 2. Flaw-to-fix table

| # | Flaw seen | Rev A solution | Model | Verified by |
|---|---|---|---|---|
| F1 | 4WD turns skid all wheels unpredictably (S7) | **2WD** with the fan for grip, as on KOGUMA-CHAN | drive train | CG within 1 mm of the axle |
| F2 | Drive-train misalignment: 0.2 mm reverses drift; printed mounts flex (S7, S15) | **One-piece frame.** Both axle bores go through both walls in a single cut, so the wheels are coaxial by construction. Each axle runs in **two MR63 bearings** in a 5 mm wall | `frame`, `bearings_*` | Interference check; Phase 6A spin-down drift test |
| F3 | Hubs too small, tyres shedding, wheels not round (S15, S16) | Wheel turns with a steel axle on bearings (no plastic bore). Hub lips hold the tyre. Tyres are bought rings | `hub_*`, `axle_*`, `tire_*` | Runout check in 6A |
| F4 | Coreless motors are faster and lighter, but need a gear train | **8520 coreless + 8T:36T 0.5M spur (4.5:1)**, motors behind the axle so the centre line stays free for the fan. 36T rather than ZoroBot's 40T keeps the gear tips 2.5 mm off the floor | `motor_*`, `pinion_*`, `spur_*` | Gear floor-clearance check |
| F5 | Motor-shaft encoders read through gear backlash | **AS5047P magnetic encoders on the wheel axles** (KOGUMA-CHAN), with a magnet on each axle end and the chip 1 mm away on a frame rib | `magnet_*`, `encoder_*` | Phase 6A counts-per-rev test |
| F6 | Diagonal sensors too far back (S17) | Diagonal IR mouths 46.5 mm ahead of the axle at ±50°; front pair at the nose | `sensor_block` | `assets/sensor_in_cell.png` |
| F7 | IR crosstalk and calibration drift (brief §5) | Black printed shroud fixes angles and height, with a 1.4 mm septum per pair and 12 mm bores | `sensor_block` | Phase 6C |
| F8 | Beam spill onto the floor or red wall tops | Beam at z = 21.3 mm; every spot stays 9-34 mm up the 50 mm white face | `SENS_Z` | `assets/beam_vs_wall.png` |
| F9 | No crumple zone (S4) | TPU bumper band around the nose, below the beams | `bumper` | Phase 6J |
| F10 | CG far from the axle unloads the drive wheels; forward CG tipped a mouse at 9 m/s² (S7) | Battery behind the fan motor, sensor block ahead. CG +0.8 mm ahead of the axle, 16.2 mm high | layout | Build checks |
| F11 | Fan off-axis loads the skids instead of the wheels | **Fan on the centre line**, 7 mm ahead of the axle. The skirt (suction pan) is the frame floor, and its centroid sits 2.9 mm ahead of the axle | `frame`, `impeller`, `fan_motor` | Build check; `assets/section_fan.png` |
| F12 | Skirt dragging on 0.5 mm floor steps | Skirt 1.3 mm off the floor; worst pitch case still 0.66 mm. PTFE skid domes are moulded into the skirt | `SKIRT_*`, skids | Build check |
| F13 | Extra mounts and placeholders add mass and failure points | **11 part types**, each with a job: frame, plate, sensor block, bumper, battery holder, impeller, hubs, plus bought parts. No separate motor mounts, skid posts, fan brackets or adapter boards: the MCU, IMU and drivers are chips on the PCB | all | Mass 63.3 g ex battery |
| F14 | Oversized chassis hits walls (brief §5) | 96.5 x 77 mm, 45.5 mm per side in the passage; 61 mm swept radius turning in place | plate | Build check |

## 3. Assumptions

| ID | Assumption | Effect if wrong | Resolve in |
|---|---|---|---|
| C1 | 8520 coreless drive motors, 8.5 x 20 mm, 5 g, 1 mm shaft ≥ 5.3 mm long [A] | Tube bore, pinion reach | Phase 3; measure on arrival (6A) |
| C2 | 0716 coreless fan motor, 7 x 16 mm, 2.5 g, ~0.6 A at 7.4 V [A] | Collar bore, current budget | Phase 3 |
| C3 | Fan makes 150 gf (1.9x weight) at working PWM [A]; needs ~390 Pa under the pan | Grip with fan | Scale test with the fan on (6A) |
| C4 | 2S 240 mAh pack is 18 x 44 x 11 mm, 15 g [A] | Holder size; CG via `BATT_CX` | Phase 3 |
| C5 | Tyre μ = 1.0 on the maze floor [A] | Grip limits scale with μ | Tilt test (6A) |
| C6 | Shroud limits each IR cone to ±12° [A] | Spot heights | 6C |
| C7 | FDM printer, 0.4 mm nozzle, PETG and TPU [A] | Print notes below | Phase 0 |
| C8 | Gear motor and fan need 3 motor channels: DRV8835 (2) + a low-side MOSFET (fan) [A] | Electronics BOM | Phase 3 |

## 4. Manufacturing notes (FDM)

| Part | Material | Orientation | Notes |
|---|---|---|---|
| frame | PETG (PA-CF if available) | Skirt flat on the bed | 4 perimeters, 50 % gyroid. Ream both axle bores together with one 6 mm reamer passed through both walls. This keeps them coaxial. The skirt must come out flat because it sets the 1.3 mm floor gap |
| hub_L/R | PETG | Outer face down | 100 % infill, 3 mm bore reamed, glue to the axle |
| impeller | PETG or resin | Backplate down | Balance it on the motor before fitting |
| sensor_block | Matte black PETG | Flat | Drill bores to 3.2 mm if they sag |
| battery_holder | PETG | Flat | |
| bumper | TPU 95A | Flat | |
| plate | 1.0 mm FR4 PCB | | KiCad edge cut from `cad_design/step/plate_outline.dxf` |

Heat-set M2 inserts go in the four wall tops; there are no threads in plastic.

## 5. Assembly guide

1. Press the four M2 inserts into the frame's wall tops.
2. Press two MR63 bearings into each wall bore. Slide each axle in from outside, then glue its magnet on the inner end.
3. Glue a spur gear to each hub's inner face. Glue the hub onto the axle so the spur sits 0.3 mm off the wall, then fit the tyres between the lips.
4. Press the pinions onto the drive-motor shafts. Slide each motor into its tube from the centre until the pinion meshes with the spur. Check that the gears turn with a little backlash.
5. Fit the AS5047P boards on the ribs, chip facing the magnet with a 1 mm gap.
6. Push the impeller onto the fan motor shaft, then drop the motor into the collar from above. The impeller hangs 0.5 mm over the skirt.
7. Bolt the PCB onto the frame (4 x M2 x 4 into the inserts). The fan motor passes up through the PCB hole.
8. Seat the 8 LEDs in the sensor block, emitters outboard, and fit it with 2 x M2. Clip the bumper on.
9. Screw the battery holder down (2 x M2), slide the pack in from the left, and strap it.

## 6. Gate 4 status

| Item | Status | Evidence |
|---|---|---|
| Interference check passes | **PASS** (CAD) | `build_report.md` |
| Footprint and passage clearance in CAD | **PASS** | 96.5 x 77 mm, 45.5 mm per side |
| Footprint on the physical prototype | **FAIL (not built yet)** | Needs a print |
| CG within target | **PASS** (CAD, assumed masses) | +0.8 mm, 16.2 mm high |
| First fit needs only minor trimming | **FAIL (not built yet)** | Print the frame first |
| Serviceability by swapping battery, wheel, sensor | **FAIL (not built yet)** | Designed for it; needs a physical test |
| Parametric model, STEP/STL, drawings, exploded view, assembly guide | **PASS** | `cad_design/`, `assets/`, §5 |

## 7. Why the fan is in the initial build

The Phase 1 brief recommended proving reliability without a fan first. The owner chose to build it in from the start (2026-10-19): APEC/IEEE rules allow fans, and every APEC 2026 top-3 mouse used one. In testing, the speed stages run fan-off first, then repeat with the fan on, so each change is still one variable.

## 8. Rev B candidates

- Carbon or aluminium frame once the printed one is proven (KOGUMA-CHAN moved from PCB to carbon).
- Faulhaber 1717 drive motors if the budget allows (Decimus-5A).
- A 0.8 mm 4-layer PCB to save about 2 g.

## Sources

S4 APEC 2026 Micromouse Contest Report V2 https://apec-conf.org/wp-content/uploads/2026/05/APEC-2026-Micromouse-Contest-Report-V2.pdf ·
S7 https://micromouseonline.com/2013/02/24/four-wheel-micromouse-difficult-to-turn/ ·
S15 https://micromouseonline.com/2012/05/24/printed-wheels-complete-decimus-mechanicals/ ·
S16 https://micromouseonline.com/2014/05/25/travelling-bumpy-road-micromouse/ ·
S17 https://micromouseonline.com/2011/05/29/wall-sensor-alignment-error/ ·
S18 https://micromouseonline.com/2011/01/10/pointing-the-sensors/
